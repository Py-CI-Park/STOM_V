"""US-005 Phase 2b — 루프 오케스트레이터 (헤드리스 진화 루프).

`run_loop(config, ...)` 가 한 run을 끝까지 돌린다:

  start/resume run (state)
    → [provider=gpt_auth면 프록시 inject+start, finally에서 stop+clear]
    → 각 세대 (종료 전까지):
        a. buy+sell 전략 생성 (brain.generate_strategy, timeframe=config.bt_timeframe)
           → namespaced 이름 AILOOP_<run>_g<gen>_buy/sell 로 루프 DB에 저장.
           (gen-0: seed_* 주어지면 생성 대신 seed를 그대로 평가.)
        b. ensure_loop_db_engine_compat()  (formula 빈 테이블 보장 — 데드락 차단)
        c. BOUNDED 백테스트 1회 (검증된 단일 종목 스코프).
        d. ROBUSTNESS BACKSTOP: 백테스트가 예외/타임아웃/status!=success/
           csv_path 없음 이면 그 세대를 score=0, gate_passed=False로 기록하고
           **다음 세대로 계속**. 루프는 절대 크래시/행 하지 않는다.
        e. 성공 시: equity 로드 → compute_fitness → record + update_best.
        f. (autopsy hook) autopsy_fn이 있으면 csv로 다음 세대 프롬프트 피드백 생성.
        g. 종료 판정.
    → 요약 dict 반환.

엔트리포인트(`__main__`)는 Windows spawn 안전을 위해 `if __name__=='__main__':`
아래에 둔다. 백테스트는 e2e_smoke와 동일하게 검증된 CLI 진입점
(stom_backtest.py)을 서브프로세스로 호출한다 — in-process run_backtest는
Windows에서 multiprocessing(spawn) 자식이 무거운 __main__ 재import +
matplotlib GUI 초기화로 멈추는 문제가 있어서다.
"""

from __future__ import annotations

# (1) bootstrap을 가장 먼저 — cli.* / utility.* import 전에 env 격리.
import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402

import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import deque  # noqa: E402
from typing import Any, Callable, Deque, Dict, List, Optional  # noqa: E402

from ai_strategy_loop.config import LoopConfig  # noqa: E402
from cli.config import BacktestConfig  # noqa: E402
from cli.warm_session import WarmBacktestSession  # noqa: E402
from ai_strategy_loop.controller.history import (  # noqa: E402
    GenRecord,
    build_history_summary,
)
from ai_strategy_loop.controller.runlock import (  # noqa: E402
    acquire_run_lock,
    release_run_lock,
)
from ai_strategy_loop.controller.state import (  # noqa: E402
    LoopState,
    clear_stop_flag,
    publish_loop_state,
    stop_requested,
    to_loop_state,
)
from ai_strategy_loop.controller.termination import should_terminate  # noqa: E402

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIN_DB = os.path.join(REPO_ROOT, "_database", "stock_min_back.db")
TICK_DB = os.path.join(REPO_ROOT, "_database", "stock_tick_back.db")


# =====================================================================
# 백테스트 실행 (검증된 서브프로세스 경로) — robustness backstop의 대상.
# =====================================================================
class BacktestOutcome:
    """백테스트 1회의 정규화 결과.

    ok=True 이면 status=='success' + csv_path 존재 + metrics 보유.
    실패(예외/타임아웃/비성공/CSV없음)는 ok=False + reason 으로 표준화한다.
    """

    def __init__(self, ok: bool, status: str, csv_path: Optional[str],
                 metrics: Optional[dict], reason: str):
        self.ok = ok
        self.status = status
        self.csv_path = csv_path
        self.metrics = metrics
        self.reason = reason


def _select_single_stock(timeframe: str, window_days: int):
    """BOUNDED 단일 종목 스코프를 timeframe에 맞춰 자동 선택한다.

    e2e_smoke._select_single_stock 과 동일 로직 (moneytop 등장일 ∩ 종목 보유일
    교집합에서 앞쪽 window_days). 엔진/CLI는 건드리지 않는다.

    반환: (one_code, start_yyyymmdd, end_yyyymmdd, day_count)
    """
    import sqlite3  # noqa: PLC0415

    is_tick = timeframe == "tick"
    db_path = TICK_DB if is_tick else MIN_DB
    day_div = 1_000_000 if is_tick else 10_000

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(moneytop)")
        cols = [r[1] for r in cur.fetchall()]
        val_col = cols[1]
        cur.execute(f'SELECT "index", "{val_col}" FROM moneytop')
        rows = cur.fetchall()

        code_days: dict = {}
        for idx, text in rows:
            if not text:
                continue
            day = int(idx) // day_div
            for c in str(text).split(";"):
                c = c.strip()
                if c:
                    code_days.setdefault(c, set()).add(day)

        if not code_days:
            raise RuntimeError(f"{db_path} moneytop에서 종목을 추출하지 못했습니다")

        best_code = max(code_days, key=lambda c: len(code_days[c]))
        try:
            own_days = {
                r[0] for r in cur.execute(
                    f'SELECT DISTINCT "index" / {day_div} FROM "{best_code}"'
                ).fetchall()
            }
        except sqlite3.OperationalError:
            own_days = code_days[best_code]
        common = sorted(code_days[best_code] & own_days)
    finally:
        con.close()

    if len(common) < window_days:
        raise RuntimeError(
            f"최상위 종목 {best_code}의 (moneytop ∩ own) 거래일이 "
            f"{len(common)}개 < {window_days} (timeframe={timeframe})"
        )
    window = common[:window_days]
    return best_code, window[0], window[-1], len(window)


def _default_subset_db(timeframe: str = "min") -> str:
    """small_universe 기본 subset DB 경로 (config.bt_subset_db가 None일 때).

    timeframe='tick'이면 state/tick_subset.db, 그 외(min)는 state/min_subset.db.
    기본 min이라 미지정 호출은 기존 동작과 동일(하위호환).
    """
    name = "tick_subset.db" if timeframe == "tick" else "min_subset.db"
    return os.path.join(REPO_ROOT, "ai_strategy_loop", "state", name)


def _select_universe_window(
    subset_db: str, window_days: int, timeframe: str = "min",
    select_mode: str = "earliest",
):
    """subset DB의 moneytop에서 백테 날짜 윈도우(window_days 거래일)를 산출한다.

    subset DB의 moneytop은 N개 종목만 담은 curated 테이블이다. 그 등장 일자
    (YYYYMMDD)들을 모아 정렬한 뒤 window_days 일을 윈도우로 잡는다.
    one_code는 쓰지 않는다('종목코드별 분류'가 moneytop의 모든 코드를 로딩).

    select_mode:
      'earliest' — 기본·하위호환. 앞쪽 window_days 일(가장 이른 구간).
      'richest'  — moneytop coverage(그 날 담긴 코드 수) 합이 최대인 연속 window_days
                   구간. 활성 종목이 가장 많은 구간을 골라 신호를 풍부하게 한다.
                   동률이면 더 이른 구간(작은 시작 인덱스)을 선택(결정론).

    timeframe별 일자 추출 제수: min=10_000(YYYYMMDDHHMM 12자리),
    tick=1_000_000(YYYYMMDDHHMMSS 14자리). 기본 min이라 미지정 호출은
    기존 동작과 동일(하위호환).

    반환: (start_yyyymmdd, end_yyyymmdd, day_count).
    """
    import sqlite3  # noqa: PLC0415

    day_div = 1_000_000 if timeframe == "tick" else 10_000
    con = sqlite3.connect(f"file:{subset_db}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(moneytop)")
        cols = [r[1] for r in cur.fetchall()]
        if len(cols) < 2:
            raise RuntimeError("subset moneytop에 값 컬럼이 없습니다")
        valcol = cols[1]  # 거래대금순위(;-구분 코드 리스트) — coverage 산출용.
        # 일자별 coverage(=그 날 moneytop에 담긴 코드 수)를 집계한다.
        #   같은 날 여러 행이 있으면 최대값을 쓴다(보통 하루 1행).
        day_cov: dict[int, int] = {}
        for idx, text in cur.execute(f'SELECT "index","{valcol}" FROM moneytop'):
            day = int(idx) // day_div
            cnt = len([c for c in str(text).split(";") if c.strip()]) if text else 0
            if cnt > day_cov.get(day, 0):
                day_cov[day] = cnt
            else:
                day_cov.setdefault(day, cnt)
    finally:
        con.close()

    days = sorted(day_cov)
    if len(days) < window_days:
        raise RuntimeError(
            f"subset moneytop 거래일 {len(days)}개 < window_days {window_days}"
        )
    if select_mode == "richest":
        # 정렬일 기준 연속 window_days 슬라이스 중 coverage 합 최대(동률=이른 구간).
        best_i, best_sum = 0, -1
        for i in range(len(days) - window_days + 1):
            s = sum(day_cov[d] for d in days[i:i + window_days])
            if s > best_sum:
                best_sum, best_i = s, i
        window = days[best_i:best_i + window_days]
    else:  # 'earliest' (기본·하위호환): 앞쪽 window_days 일.
        window = days[:window_days]
    return window[0], window[-1], len(window)


def _parse_cli_json(stdout: str) -> dict:
    """CLI --format json stdout에서 결과 JSON 문서를 파싱한다 (e2e_smoke와 동일)."""
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def run_backtest_for(config: LoopConfig, buy_name: str, sell_name: str) -> BacktestOutcome:
    """주어진 buy/sell 이름으로 BOUNDED 백테스트 1회를 실행한다.

    검증된 CLI 진입점(stom_backtest.py)을 서브프로세스로 호출한다. 이 함수는
    robustness 테스트가 monkeypatch 하는 단일 후크다.

    예외를 던지지 않고 항상 BacktestOutcome을 반환한다(여기서 1차 방어).
    """
    env = dict(os.environ)
    env["STOM_ALLOW_MINIMAL_SETTING"] = "1"
    env["STOM_CLI_DB_STRATEGY"] = str(bootstrap.LOOP_DB_STRATEGY)
    env["PYTHONUNBUFFERED"] = "1"

    if config.bt_scope == "small_universe":
        # 소형 다변화 유니버스: curated subset back-DB(N개 종목) + '종목코드별 분류'.
        #   subset의 moneytop이 N개만 담으므로 엔진 무수정으로 그 N개 위에서 백테한다.
        #   one_code는 쓰지 않는다. 날짜 윈도우는 subset moneytop에서 산출한다.
        #   DB 접근/선택 실패도 "절대 raise 안 함" 계약대로 실패 outcome으로 표준화.
        # timeframe-aware: tick이면 tick_subset.db + STOM_CLI_DB_STOCK_BACK_TICK +
        #   --timeframe tick + tick day-index(1_000_000). min은 기존 경로 그대로(불변).
        is_tick = config.bt_timeframe == "tick"
        subset_db = config.bt_subset_db or _default_subset_db(config.bt_timeframe)
        if not os.path.isfile(subset_db):
            return BacktestOutcome(
                False, "error", None, None,
                f"subset DB 없음: {subset_db} (build_subset_db.py 먼저 실행)",
            )
        window_days = config.bt_window_days_universe
        bt_start = config.bt_start
        bt_end = config.bt_end
        if not (bt_start and bt_end):
            try:
                bt_start, bt_end, _ = _select_universe_window(
                    subset_db, window_days, config.bt_timeframe,
                    getattr(config, "bt_window_select", "earliest"),
                )
            except Exception as exc:  # noqa: BLE001 - 선택 실패도 outcome으로 표준화.
                return BacktestOutcome(
                    False, "error", None, None,
                    f"universe window selection failed: {exc}",
                )
        # 백테 서브프로세스가 subset DB를 back-DB로 쓰도록 오버라이드.
        #   tick은 STOM_CLI_DB_STOCK_BACK_TICK, min은 STOM_CLI_DB_STOCK_BACK_MIN.
        #   (runner.py가 config.is_tick으로 TICK/MIN 경로를 고르므로 일치시킨다.)
        if is_tick:
            env["STOM_CLI_DB_STOCK_BACK_TICK"] = str(subset_db)
        else:
            env["STOM_CLI_DB_STOCK_BACK_MIN"] = str(subset_db)
        cmd = [
            sys.executable,
            os.path.join(REPO_ROOT, "stom_backtest.py"),
            "--buy", buy_name,
            "--sell", sell_name,
            "--start", str(bt_start),
            "--end", str(bt_end),
            "--timeframe", config.bt_timeframe,  # subset back-DB의 타임프레임.
            "--divid-mode", "종목코드별 분류",  # moneytop의 모든(=N개) 코드 로딩.
            "--engines", str(config.bt_engine_count),
            "--timeout", str(config.bt_timeout),
            "--format", "json",
            "--quiet",
        ]
    else:
        # single_stock (MVP fast): '한종목 로딩' 단일 종목 + 짧은 윈도우 (기존 경로).
        bt_one = config.bt_one_code
        bt_start = config.bt_start
        bt_end = config.bt_end
        if not (bt_one and bt_start and bt_end):
            # 종목 자동 선택은 DB 접근(없는 파일/빈 moneytop 등)으로 raise할 수 있다.
            #   run_backtest_for는 "절대 raise 안 함" 계약이므로 여기서 흡수해
            #   구체 사유를 담은 실패 outcome으로 표준화한다.
            try:
                bt_one, bt_start, bt_end, _ = _select_single_stock(
                    timeframe=config.bt_timeframe, window_days=config.bt_window_days
                )
            except Exception as exc:  # noqa: BLE001 - DB/선택 실패도 outcome으로 표준화.
                return BacktestOutcome(
                    False, "error", None, None, f"stock selection failed: {exc}"
                )

        cmd = [
            sys.executable,
            os.path.join(REPO_ROOT, "stom_backtest.py"),
            "--buy", buy_name,
            "--sell", sell_name,
            "--start", str(bt_start),
            "--end", str(bt_end),
            "--timeframe", config.bt_timeframe,
            "--divid-mode", "한종목 로딩",
            "--one-code", str(bt_one),
            "--engines", str(config.bt_engine_count),
            "--timeout", str(config.bt_timeout),
            "--format", "json",
            "--quiet",
        ]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, env=env,
            capture_output=True, text=True,
            timeout=config.bt_timeout + 60,
        )
    except subprocess.TimeoutExpired:
        return BacktestOutcome(False, "timeout", None, None,
                               f"backtest timeout (>{config.bt_timeout + 60}s)")
    except Exception as exc:  # noqa: BLE001 - 서브프로세스 기동 실패 등 모든 예외 흡수.
        return BacktestOutcome(False, "error", None, None, f"backtest spawn failed: {exc}")

    payload = _parse_cli_json(proc.stdout)
    status = payload.get("status")
    csv_path = payload.get("csv_path")
    metrics = payload.get("metrics")

    if proc.returncode != 0 or status != "success" or not csv_path:
        # 구체 실패 원인을 보존한다: CLI --format json은 error 결과에
        #   message(예: 'backtest completed without metrics')와 last_checkpoint를
        #   포함한다(cli/output.py ERROR_DIAGNOSTIC_FIELDS). 이를 reason에 접합해야
        #   다음 세대가 no_trades / runtime_error 를 구분해 학습할 수 있다.
        message = payload.get("message")
        last_checkpoint = payload.get("last_checkpoint")
        detail_parts = [f"exit={proc.returncode}", f"status={status}"]
        if message:
            detail_parts.append(f"message={message}")
        if last_checkpoint:
            detail_parts.append(f"last_checkpoint={last_checkpoint}")
        detail_parts.append(f"csv={'yes' if csv_path else 'no'}")
        return BacktestOutcome(
            False, str(status), csv_path, metrics,
            "backtest non-success: " + " ".join(detail_parts),
        )
    return BacktestOutcome(True, "success", csv_path, metrics, "ok")


# =====================================================================
# warm 엔진 모드 (전체유니버스 웜풀 세션) — cold subprocess 경로의 대안.
# =====================================================================
def _build_warm_btconfig(config: LoopConfig) -> BacktestConfig:
    """warm 모드용 BacktestConfig를 LoopConfig의 warm 필드에서 조립한다.

    buy/sell는 빈 문자열로 둔다(run마다 WarmBacktestSession.run에 지정).
    스코프는 전체유니버스('종목코드별 분류') + 사용자 검증 baseline 파라미터다.
    """
    return BacktestConfig(
        buy_strategy="",
        sell_strategy="",
        start_date=config.bt_full_start,
        end_date=config.bt_full_end,
        start_time=config.bt_universe_start_time,
        end_time=config.bt_universe_end_time,
        avg_time=config.bt_avg_time,
        engine_count=config.bt_warm_engine_count,
        is_tick=(config.bt_timeframe == "tick"),
        betting=config.bt_betting,
        divid_mode="종목코드별 분류",
        # BacktestConfig.timeout은 **데이터로딩**(prepare/_send_engine_data/재로딩) 전용이다.
        #   prepare는 전체유니버스 32엔진 데이터 로딩(~80-180초)이 필요하므로 충분히 높게
        #   둔다(>=600). per-run fail-fast 컷은 별도 bt_warm_run_timeout(120)으로 처리한다.
        #   여기를 짧게 두면 재로딩이 잘려 엔진 복구가 실패한다.
        timeout=max(getattr(config, "bt_timeout", 600), 600),
        verbose=False,
    )


def _warm_to_outcome(result: dict) -> BacktestOutcome:
    """WarmBacktestSession.run의 result dict를 BacktestOutcome으로 정규화한다.

    run_backtest_for와 동일한 계약(ok=True면 status=='success' + csv_path + metrics).
    실패는 result의 message/status로 구체 사유를 reason에 보존한다.
    """
    result = result or {}
    status = result.get("status", "error")
    csv_path = result.get("csv_path")
    metrics = result.get("metrics")
    ok = bool(status == "success" and csv_path and metrics)
    if ok:
        return BacktestOutcome(True, "success", csv_path, metrics, "ok")
    message = result.get("message")
    detail_parts = [f"status={status}"]
    if message:
        detail_parts.append(f"message={message}")
    detail_parts.append(f"csv={'yes' if csv_path else 'no'}")
    return BacktestOutcome(
        False, str(status), csv_path, metrics,
        "warm backtest non-success: " + " ".join(detail_parts),
    )


# =====================================================================
# 부검 피드백 (US-006 Phase 3) — csv_path → 다음 세대 NL 피드백.
# =====================================================================
def _default_autopsy_fn(config: LoopConfig) -> Callable[[str], Optional[str]]:
    """csv_path를 받아 다음 세대 프롬프트용 **진입(BUY)** 부검 피드백을 만드는 기본 훅.

    analyze_trades(working-window 진입 변별 통계) → summarize(NL 가이드).
    부검 실패/예외는 run_loop의 autopsy hook에서 흡수되므로 여기선 예외를
    던져도 안전하나, csv 자체 문제는 깔끔히 None을 반환한다.
    """
    from ai_strategy_loop.autopsy import analyze_trades, summarize  # noqa: PLC0415

    min_trades = int(getattr(config, "min_trades", 10) or 10)

    def _fn(csv_path: str) -> Optional[str]:
        if not csv_path:
            return None
        abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
        result = analyze_trades(abs_csv, min_trades=min_trades)
        return summarize(result, config)

    return _fn


def _default_exit_autopsy_fn(config: LoopConfig) -> Callable[[str], Optional[str]]:
    """csv_path를 받아 다음 세대 **매도(SELL)** 전략용 청산 부검 피드백을 만드는 훅.

    analyze_exits(give-back/MAE depth/보유시간/매도규칙) → summarize_exits(NL 가이드).
    PROFITABILITY 신호의 핵심: 손익을 가르는 매도 측을 직접 겨냥한다.
    """
    from ai_strategy_loop.autopsy import analyze_exits, summarize_exits  # noqa: PLC0415

    min_trades = int(getattr(config, "min_trades", 10) or 10)

    def _fn(csv_path: str) -> Optional[str]:
        if not csv_path:
            return None
        abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
        result = analyze_exits(abs_csv, min_trades=min_trades)
        return summarize_exits(result, config)

    return _fn


def _default_segment_autopsy_fn(
    config: LoopConfig,
) -> Callable[[str], Optional[Any]]:
    """csv_path를 받아 세그먼트 강화 부검(SegmentAutopsyResult)을 만드는 훅(P1).

    analyze_segments(시총·시간대 cross-tab + 구체 임계값) 결과를 그대로 돌려준다.
    NL 피드백(summarize_segments)과 LIVE page_data(to_page_data) 양쪽에 쓰이므로
    여기선 결과 객체만 만들고, 합성/직렬화는 호출부(_build_feedback)가 한다.
    부검 실패/예외는 _build_feedback에서 흡수되므로 안전하다.
    """
    from ai_strategy_loop.autopsy import analyze_segments  # noqa: PLC0415

    min_trades = int(getattr(config, "min_trades", 10) or 10)
    # Phase C-2: 5분 시초 시간대 세분 토글. 기본 OFF면 fine_time=False라 세그먼트
    #   결과가 기존과 byte-동일하다(하위호환).
    fine_time = bool(getattr(config, "segment_fine_time", False))

    def _fn(csv_path: str):
        if not csv_path:
            return None
        abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
        return analyze_segments(abs_csv, min_trades=min_trades, fine_time=fine_time)

    return _fn


def _backtest_error_feedback(reason: str, config: LoopConfig) -> str:
    """백테스트 실패 세대에 줄 '구체 원인을 겨냥한' 다음 세대 피드백.

    outcome.reason(가능하면 runner의 message+last_checkpoint 포함)을 분류해,
    0거래면 '완화하라', 런타임 오류면 '그 오류를 피하라' 등 actionable 한국어
    가이드를 낸다(맹목 변이 차단). 항상 비어 있지 않은 문자열.
    """
    from ai_strategy_loop.autopsy import backtest_error_feedback  # noqa: PLC0415

    min_trades = int(getattr(config, "min_trades", 10) or 10)
    return backtest_error_feedback(reason, min_trades=min_trades)


def _backtest_error_history_line(reason: str) -> str:
    """실패 세대가 누적 이력에 남길 구체 사유 라인(공백 라인 방지)."""
    from ai_strategy_loop.autopsy import backtest_error_history_line  # noqa: PLC0415

    return backtest_error_history_line(reason)


# =====================================================================
# 전략 생성 (한 세대 = buy 1 + sell 1).
# =====================================================================
def _generate_pair(provider, config: LoopConfig, run_id: str, gen_no: int,
                   autopsy_feedback: Optional[str],
                   history_summary: Optional[str] = None,
                   sell_feedback: Optional[str] = None,
                   base_buy_code: Optional[str] = None,
                   base_sell_code: Optional[str] = None,
                   meta_seed: Optional[str] = None,
                   freeze_buy: bool = False) -> Dict[str, Any]:
    """이 세대의 buy + sell 전략을 생성/저장한다.

    Args:
        autopsy_feedback: **진입(BUY)** 측 피드백(진입 변별 변수 + 게이트 거리).
            buy 전략 생성에 쓰인다.
        sell_feedback: **매도(SELL)** 측 청산 피드백(give-back/손절/보유시간/매도규칙).
            None이면 buy 측 autopsy_feedback을 sell에도 그대로 쓴다(하위호환).
        base_buy_code: seed-and-refine 출발점(매수). 주어지면 buy 생성이 이 코드를
            점진 개선한다. None이면 fresh 생성.
        base_sell_code: seed-and-refine 출발점(매도). 주어지면 sell 생성이 이 코드를
            점진 개선한다. None이면 fresh 생성.
        freeze_buy: 타깃 처방 — True면 매수(진입)를 동결한다. base_buy_code를
            **LLM 호출 없이** buy_name으로 그대로 DB에 복제 저장하고(토큰 0),
            매도(청산)만 generate_strategy로 재생성한다. 거래수·빈도·수익을
            보존한 채 청산만 탐색해 MDD를 깎는 게 목적이다. base_buy_code가
            None이면 무시하고 기존대로 buy도 생성한다(안전 폴백). 또한 freeze_buy면
            sell 피드백 앞에 청산-전용 개선 지시를 한 줄 결합한다(원본 변형 안 함).
            기본 False(하위호환).

    Returns:
        {"status": "ok", "buy_name", "sell_name", "tokens"} 또는
        {"status": "error", "reason"}.
    """
    from ai_strategy_loop.brain import generate_strategy  # noqa: PLC0415
    from ai_strategy_loop.brain.token_check import DedupTracker  # noqa: PLC0415

    db = str(bootstrap.LOOP_DB_STRATEGY)
    buy_name = f"AILOOP_{run_id}_g{gen_no}_buy"
    sell_name = f"AILOOP_{run_id}_g{gen_no}_sell"
    dedup = DedupTracker(k=5)

    # 타깃 처방: base_buy_code가 있을 때만 매수 동결을 발동한다(없으면 안전 폴백).
    do_freeze_buy = bool(freeze_buy and base_buy_code)

    # 매도 전략엔 청산 부검 피드백을 준다(없으면 buy 피드백으로 폴백 = 하위호환).
    sell_fb = sell_feedback if sell_feedback is not None else autopsy_feedback
    # 매수 동결 시 매도 프롬프트에 청산-전용 개선 지시를 결합한다. 원본 sell_fb를
    #   변형하지 않고 새 문자열로 합친다(불변성).
    if do_freeze_buy:
        freeze_directive = (
            "매수(진입)는 고정·검증됐다. 거래수를 바꾸지 말고 청산(매도)만 개선해 "
            "MDD를 낮춰라 — 익절(상방 포착)은 유지하고 give-back/손절만 강화하라."
        )
        sell_fb = (
            f"{freeze_directive}\n\n{sell_fb}" if sell_fb else freeze_directive
        )

    tokens = 0
    for kind, name in (("buy", buy_name), ("sell", sell_name)):
        # 타깃 처방: 매수 동결이면 base_buy_code를 LLM 호출 없이 그대로 복제 저장한다
        #   (generator의 save 함수 재사용). 토큰 0. 매도만 아래에서 generate_strategy.
        if kind == "buy" and do_freeze_buy:
            from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415

            saved = save_strategy_to_db(db, buy_name, base_buy_code, "buy")
            if saved.get("status") != "ok":
                return {"status": "error",
                        "reason": f"buy 동결 저장 실패: {saved.get('message')}"}
            continue

        feedback = sell_fb if kind == "sell" else autopsy_feedback
        # kind별 출발점 코드(있으면 점진 개선, 없으면 fresh 생성).
        base_code = base_sell_code if kind == "sell" else base_buy_code
        res = generate_strategy(
            provider, kind, name, db,
            timeframe=config.bt_timeframe,
            base_code=base_code,
            autopsy_feedback=feedback,
            history_summary=history_summary,
            meta_seed=meta_seed,
            retry_max=config.max_retries + 1,
            dedup=dedup,
            # Track B 분산매매 토글 — build_messages는 kind=='buy'일 때만 적용하므로
            #   매도 경로엔 무영향(기본값과 동일 동작). 기본 OFF면 프롬프트 byte-동일.
            dispersion_prompt_enabled=config.dispersion_prompt_enabled,
            target_daily_trades=getattr(config, "target_daily_trades", None),
            # Track B 2차 거래대금 유동성 게이트 — generate_strategy는 kind=='buy'일
            #   때만 적용하므로 매도 경로엔 무영향. 기본 OFF면 동작 byte-동일(하위호환).
            require_liquidity_gate=getattr(config, "require_liquidity_gate", False),
            # Track B 3차 MDD 제어 강화 — build_messages가 kind=='sell'일 때만 MDD 억제
            #   블록을 매도 프롬프트에 추가하므로 매수 경로엔 무영향. 기본 OFF면 byte-동일.
            mdd_control_enabled=getattr(config, "mdd_control_enabled", False),
            # Phase C-3 시간 분산 넛지 — build_messages가 kind=='buy'일 때만 시초 분산
            #   가이드를 추가하므로 매도 경로엔 무영향. 기본 OFF면 프롬프트 byte-동일.
            encourage_time_dispersion=getattr(config, "encourage_time_dispersion", False),
        )
        if res.get("status") != "ok":
            return {"status": "error", "reason": f"{kind} 생성 실패: {res.get('reason')}"}
        usage = res.get("usage") or {}
        tokens += int(usage.get("total_tokens", 0) or 0)

    return {"status": "ok", "buy_name": buy_name, "sell_name": sell_name, "tokens": tokens}


# =====================================================================
# US-007 — 라이브 상태 발행 헬퍼 (current_state.json).
# =====================================================================
# 프로세스 플로우 패널 — phase → 5단계 인덱스 맵.
#   -1=없음/완료, 0=생성, 1=백테, 2=채점, 3=부검, 4=반복(세대완료 후 다음 루프).
#   (프론트 phase-detail.jsx의 LIVE_PHASE_INDEX는 PhaseTimeline/폴백용 별개의 4단계 맵 —
#    의도적으로 다른 인덱스 공간이다. 두 맵 모두 test_dashboard_phase_mapping.py가 가드.)
# =====================================================================
_PHASE_STEP: Dict[str, int] = {
    # 생성 단계.
    "generate_start": 0,
    "generate_done": 0,
    # warm 준비/loop 시작은 생성 전 준비라 생성 단계로 묶는다.
    "warm_prepare_start": 0,
    "warm_prepare_done": 0,
    "loop_start": 0,
    # 백테 단계.
    "backtest_start": 1,
    "backtest_end": 1,
    # 채점 단계.
    "score_start": 2,
    "score_done": 2,
    # 부검 단계.
    "autopsy_start": 3,
    "autopsy_done": 3,
    # 반복(세대 완료 후 다음 세대 루프 진입 직전).
    "generation_done": 4,
    # GA 경로(run_ga_loop) phase — 힐클라임과 동일 5단계로 매핑.
    "ga_init": 0,            # 초기 population 생성 = 생성.
    "ga_evaluate_start": 1,  # population 평가(백테 실행) = 백테.
    "ga_generation_done": 4, # 세대 완료 = 반복.
    # 완료/정지는 활성 단계 없음.
    "complete": -1,
    "stopping": -1,
}


# =====================================================================
def _publish_live(
    st: LoopState,
    rid: str,
    config: LoopConfig,
    *,
    status: str,
    current_gen: int,
    cumulative_tokens: int,
    phase: str = "",
    last_checkpoint: str = "",
    message: str = "",
    best_gen: int = -1,
    best_score: Optional[float] = None,
    best_buy: Optional[str] = None,
    best_sell: Optional[str] = None,
    winner_gen: int = -1,
    winner_score: Optional[float] = None,
    winner_buy: Optional[str] = None,
    winner_sell: Optional[str] = None,
    page_data: Optional[Dict[str, Any]] = None,
    _log_buf: Optional[Deque[str]] = None,
) -> None:
    """현재 루프 진행 상태를 contract.LoopState로 만들어 current_state.json에 발행.

    DB(generations)에서 세대 행을 읽어 to_loop_state로 빌드한다. 발행 실패는
    publish_loop_state 내부에서 흡수되므로 루프를 막지 않는다. DB 조회 자체가
    실패해도(닫힌 DB 등) 라이브 가시화 보조이므로 조용히 건너뛴다.

    page_data는 contract v2 패스스루(후속 페이지가 자기 데이터를 실어보냄). None이면
    빈 dict로 발행돼 기존 호출부(page_data 무인자)는 v1과 동일하게 동작한다(하위호환).

    _log_buf는 run_loop이 생성한 run-scoped deque(maxlen=50). None이면(GA/테스트) 빈 로그.
    """
    # 로그 버퍼에 이 이벤트 한 줄을 추가한다(버퍼가 없으면 조용히 건너뜀).
    if _log_buf is not None and phase:
        _log_buf.append(f"[{phase}] {message}" if message else f"[{phase}]")

    try:
        gens = st.get_generations(rid)
    except Exception:  # noqa: BLE001 - 라이브 발행은 정확성 경로가 아니다.
        return
    summary = {
        "run_id": rid,
        "best_gen": best_gen,
        "best_score": best_score,
        "best_buy": best_buy,
        "best_sell": best_sell,
        "winner_gen": winner_gen,
        "winner_score": winner_score,
        "winner_buy": winner_buy,
        "winner_sell": winner_sell,
    }
    current_step = _PHASE_STEP.get(phase, -1)
    snapshot = to_loop_state(
        summary, gens, config=config, status=status, current_gen=current_gen,
        latest={
            "phase": phase,
            "last_checkpoint": last_checkpoint,
            "message": message,
            "recent_logs": list(_log_buf) if _log_buf is not None else [],
            "current_step": current_step,
        },
        cumulative_tokens=cumulative_tokens,
        page_data=page_data,
    )
    publish_loop_state(snapshot)


# =====================================================================
# 메인 오케스트레이터.
# =====================================================================
def run_loop(
    config: LoopConfig,
    *,
    seed_buy: Optional[str] = None,
    seed_sell: Optional[str] = None,
    autopsy_fn: Optional[Callable[[str], Optional[str]]] = None,
    run_id: Optional[str] = None,
    state: Optional[LoopState] = None,
) -> Dict[str, Any]:
    """헤드리스 진화 루프를 끝까지 돌리고 요약을 반환한다.

    Args:
        config: LoopConfig (bt_*, max_generations, target_score, cost_cap_* 포함).
        seed_buy/seed_sell: gen-0에서 생성 대신 평가할 기존 전략 이름(루프 DB).
        autopsy_fn: csv_path를 받아 다음 세대 프롬프트용 피드백 문자열을 만드는
            훅. None이고 config.autopsy_enabled가 True면 US-006 기본 부검 훅
            (_default_autopsy_fn: working-window 거래 통계 → NL 피드백)을 자동 사용.
            명시 autopsy_fn이 항상 우선. 둘 다 비활성이면 US-005 경로와 동일.
        run_id: 지정 시 resume.
        state: 테스트가 주입할 LoopState (None이면 기본 경로로 생성).

    Returns:
        {run_id, generations, best_gen, best_score, best_buy, best_sell, stop_reason}.
    """
    # P6 — cross-process single-writer 락 획득. CLI/GUI 어느 진입점이든 같은
    #   current_state.json/loop_runs.db에 쓰므로, 살아있는 다른 루프가 락을 잡고
    #   있으면 즉시 거부한다(동시 쓰기 차단). stale 락(크래시 잔존)은 runlock이
    #   회수한다. 테스트가 LoopState를 주입(state!=None)하는 경우는 격리 환경이므로
    #   락을 건너뛴다(운영 lockfile 미접촉 + 동시성 단위테스트 독립 보장).
    lock_acquired = False
    if state is None:
        lock_res = acquire_run_lock()
        if lock_res.get("status") != "ok":
            return {
                "run_id": run_id,
                "generations": 0,
                "best_gen": -1, "best_score": None, "best_buy": None, "best_sell": None,
                "winner_gen": -1, "winner_score": None,
                "winner_buy": None, "winner_sell": None,
                "stop_reason": "lock_busy",
                "error": lock_res.get("message"),
                "holder_pid": lock_res.get("holder_pid"),
            }
        lock_acquired = True

    st = state or LoopState()
    owns_state = state is None

    # 부검 피드백 훅 결정 (US-006): 명시 autopsy_fn이 우선, 없으면 config 플래그로
    #   기본 훅을 켠다. None이면(둘 다 비활성) US-005 경로와 동일하게 동작한다.
    effective_autopsy_fn = autopsy_fn
    if effective_autopsy_fn is None and getattr(config, "autopsy_enabled", False):
        effective_autopsy_fn = _default_autopsy_fn(config)

    # 매도(SELL) 측 청산 부검 훅: 명시 autopsy_fn이 주어지면 그것을 진입/청산 양쪽에
    #   쓰던 기존 계약을 유지하기 위해 sell 측엔 별도 훅을 만들지 않는다(autopsy_fn이
    #   곧 buy 피드백). autopsy_fn 미지정 + autopsy_enabled면 청산 부검 기본 훅을 켠다.
    effective_exit_autopsy_fn: Optional[Callable[[str], Optional[str]]] = None
    if autopsy_fn is None and getattr(config, "autopsy_enabled", False):
        effective_exit_autopsy_fn = _default_exit_autopsy_fn(config)

    # 세그먼트 강화 부검 훅(P1): 명시 autopsy_fn이 없고 autopsy_enabled면 켠다.
    #   세그먼트 NL 피드백을 진입/청산 양쪽에 합성하고, 요약 dict를 page_data로 발행한다.
    effective_segment_autopsy_fn: Optional[Callable[[str], Optional[Any]]] = None
    if autopsy_fn is None and getattr(config, "autopsy_enabled", False):
        effective_segment_autopsy_fn = _default_segment_autopsy_fn(config)

    # P4 메타 환류: meta_seed_enabled가 ON이면 run 시작 시 1회 메타 인사이트를
    #   로드해 NL 가이드(meta_seed)를 만든다. 기본 OFF면 None(주입 안 함=하위호환).
    #   load/build 실패는 학습 보조이므로 흡수한다(루프를 막지 않음).
    meta_seed_text: Optional[str] = None
    if getattr(config, "meta_seed_enabled", False):
        meta_seed_text = _load_meta_seed()

    rid = st.resume_or_start(config, run_id=run_id)
    start_gen = st.get_last_completed_gen(rid) + 1

    # provider 준비 (gpt_auth면 프록시 기동).
    provider, proxy_active = _make_provider_with_proxy(config)

    # best는 GRADED 점수로 선택한다(선택 그래디언트). winner/졸업은 하드 게이트
    #   통과 전략에서만 갱신한다(graduation 기준은 하드 게이트 유지).
    best_gen = -1
    best_score = None  # = best graded score
    best_buy = None
    best_sell = None
    winner_gen = -1     # 하드 게이트를 통과한 최고 세대 (졸업/export 후보).
    winner_buy = None
    winner_sell = None
    winner_score = None  # 통과 세대의 winner 점수(목표별: composite|수익|블렌드).
    # P7 — winner 비교용 정렬 키(목표별; 'profit'은 동률 시 MDD 낮은 것 우선).
    #   winner_score(발행용 스칼라)와 분리해, profit 동률 tie-break를 정확히 한다.
    winner_key = None
    stop_reason = "continue"
    cumulative_tokens = 0
    next_autopsy_feedback: Optional[str] = None   # 진입(BUY) 측 다음 세대 피드백.
    next_sell_feedback: Optional[str] = None      # 매도(SELL) 측 다음 세대 청산 피드백.
    last_autopsy_page_data: Optional[Dict[str, Any]] = None  # LIVE 부검 패널용 세그먼트 요약.
    last_holdout_verdict: Optional[Any] = None  # P5 — 직전 세대 holdout 졸업검사 결과(토글 ON일 때만).
    # seed-and-refine: gen1+가 출발점으로 삼을 현재 best 전략 코드(hill-climb).
    #   gen0 seed 평가 후 시드 코드로 채워지고, best가 갱신될 때마다 새 best 코드로
    #   갱신된다. None이면 그 세대는 fresh 생성(첫 출발점 미확보 시 정상).
    base_buy_code: Optional[str] = None
    base_sell_code: Optional[str] = None
    # 타깃 처방: 현재 best가 **MDD만 부족**(빈도·수익 통과)한 실패인지 여부.
    #   best가 갱신될 때마다 재계산한다. True면 다음 세대에서 매수를 동결하고
    #   매도(청산)만 재생성해 MDD를 깎는다(freeze_buy_on_mdd_only 토글 ON일 때).
    best_is_mdd_only: bool = False
    history_records: list = []  # CONVERGENCE — 누적 GenRecord.
    summary: Optional[Dict[str, Any]] = None
    # 프로세스 플로우 패널용 run-scoped 로그 버퍼.
    #   run_loop 호출마다 새로 생성해 세션 간 누수를 방지한다(모듈 전역 금지).
    _live_log_buf: Deque[str] = deque(maxlen=50)

    # warm 엔진 모드: 전체유니버스 엔진/데이터를 1회 prepare하고 세대마다 run()만 호출한다.
    #   prepare 실패(데이터 부재 등)는 cold(run_backtest_for) 경로로 자동 폴백한다.
    #   cold 모드면 warm_session은 None으로 두어 기존 subprocess 경로를 그대로 탄다.
    #   (cumulative_tokens 등 상태 변수 초기화 뒤에 둔다 — _publish_live가 참조.)
    warm_session = None
    if getattr(config, "bt_engine_mode", "warm") == "warm":
        _publish_live(st, rid, config, status="running", current_gen=start_gen,
                      cumulative_tokens=cumulative_tokens, phase="warm_prepare_start",
                      message="warm session prepare 시작 (전체유니버스 엔진/데이터 로딩)",
                      _log_buf=_live_log_buf)
        warm_session = WarmBacktestSession(_build_warm_btconfig(config))
        prep = warm_session.prepare()
        if prep.get("status") != "ok":
            print(f"[LOOP] warm prepare 실패 → cold 폴백: {prep.get('message')}", flush=True)
            warm_session = None
        else:
            back_count = prep.get("back_count")
            print(f"[LOOP] warm prepare 완료 (back_count={back_count})", flush=True)
            _publish_live(st, rid, config, status="running", current_gen=start_gen,
                          cumulative_tokens=cumulative_tokens, phase="warm_prepare_done",
                          message=f"warm session 준비 완료 (back_count={back_count})",
                          _log_buf=_live_log_buf)

    # resume 시 기존 best(graded) 복원.
    existing = st.get_run(rid)
    if existing is not None and existing.get("best_score") is not None:
        best_score = float(existing["best_score"])
        best_gen = int(existing["best_gen"]) if existing.get("best_gen") is not None else -1

    # US-007 — 루프 시작 시 잔여 정지 플래그 제거(이전 run 잔재 방지).
    clear_stop_flag()
    # 초기 idle→running 라이브 발행.
    _publish_live(st, rid, config, status="running", current_gen=start_gen,
                  cumulative_tokens=cumulative_tokens, phase="loop_start",
                  message="loop started",
                  _log_buf=_live_log_buf)

    try:
        # --- P2 GA 단일 분기 ---
        #   evolution_mode=='ga'면 population 기반 진화 루프(controller/ga.run_ga_loop)에
        #   위임하고 그 요약을 그대로 반환한다. warm_session/provider/state 생명주기는
        #   이 함수가 소유하므로 finally(close/proxy/clear/state.close)는 공통으로 탄다.
        #   hillclimb 경로(아래 while)는 절대 건드리지 않는다(자기완결 격리).
        if getattr(config, "evolution_mode", "hillclimb") == "ga":
            from ai_strategy_loop.controller.ga import run_ga_loop  # noqa: PLC0415

            summary = run_ga_loop(
                config, warm_session, provider, st, rid,
                seed_buy=seed_buy, seed_sell=seed_sell,
            )
            return summary

        gen_no = start_gen
        while True:
            # --- US-007 정지 플래그 (세대 시작 전 깔끔히 종료) ---
            if stop_requested():
                stop_reason = "stop_requested"
                _publish_live(st, rid, config, status="stopping", current_gen=gen_no,
                              cumulative_tokens=cumulative_tokens, phase="stopping",
                              message="stop flag observed; finishing cleanly",
                              best_gen=best_gen, best_score=best_score,
                              best_buy=best_buy, best_sell=best_sell,
                              winner_gen=winner_gen, winner_score=winner_score,
                              winner_buy=winner_buy, winner_sell=winner_sell,
                              _log_buf=_live_log_buf)
                break

            # --- 종료 판정 (세대 시작 전) ---
            # target_score(졸업 조기 종료)는 하드 게이트를 통과한 winner의 점수로만
            #   판정한다(graded로 졸업하지 않는다). max-gen/cost-cap은 그대로.
            stop, reason = should_terminate(
                {
                    "best_score": winner_score,
                    "gen_count": st.get_cumulative_generation_count(rid),
                    "tokens": cumulative_tokens,
                },
                config,
            )
            if stop:
                stop_reason = reason
                break

            print(f"\n[LOOP] === generation {gen_no} (run={rid}) ===", flush=True)

            # --- a. 전략 확보 (생성 또는 seed) ---
            # P3 계보: 이 세대가 어느 세대를 개선했는지(parent_gen). refine 모드에서
            #   현재 best의 출발 코드를 받아 개선하면 그 best_gen이 부모다. seed/fresh
            #   (출발점 없음)면 None(루트 세대)으로 기록한다.
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="generate_start",
                          message=f"gen {gen_no} 전략 생성 시작",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)
            parent_gen_for_record: Optional[int] = None
            use_seed = gen_no == 0 and seed_buy and seed_sell
            if use_seed:
                buy_name = seed_buy
                sell_name = seed_sell
                print(f"[LOOP] seed 사용: buy={buy_name} sell={sell_name}", flush=True)
                # seed-and-refine: 시드가 곧 첫 출발점이다. 시드 코드를 base로 채워
                #   gen1+가 이 코드를 점진 개선(hill-climb)하게 한다.
                if getattr(config, "bt_refine_from_best", False):
                    base_buy_code = _read_strategy_code(seed_buy, "buy")
                    base_sell_code = _read_strategy_code(seed_sell, "sell")
            else:
                # CONVERGENCE — 누적 이력 요약을 매 세대 만들어 함께 전달한다.
                history_summary = build_history_summary(history_records)
                # seed-and-refine: refine 모드면 현재 best 코드를 출발점으로 전달한다.
                #   base가 아직 None이면(첫 생성 등) fresh 생성으로 자연 폴백한다.
                refine = getattr(config, "bt_refine_from_best", False)
                gen_kwargs: Dict[str, Any] = {
                    "history_summary": history_summary,
                    "sell_feedback": next_sell_feedback,
                }
                # P4 메타 환류: 토글 ON으로 가이드가 만들어졌을 때만 전달한다(기본 OFF면
                #   키 자체를 넣지 않아 기존 동작/계약과 완전히 동일하다 — 하위호환).
                if meta_seed_text:
                    gen_kwargs["meta_seed"] = meta_seed_text
                if refine and base_buy_code is not None:
                    gen_kwargs["base_buy_code"] = base_buy_code
                    # 출발 코드가 곧 현재 best의 코드이므로 best_gen이 부모다.
                    if best_gen >= 0:
                        parent_gen_for_record = best_gen
                if refine and base_sell_code is not None:
                    gen_kwargs["base_sell_code"] = base_sell_code
                    if best_gen >= 0 and parent_gen_for_record is None:
                        parent_gen_for_record = best_gen
                # 타깃 처방: best가 MDD만 부족하면 매수를 동결하고 청산만 재생성한다
                #   (refine 모드 + base_buy_code 확보 + 토글 ON일 때만). gen_kwargs에
                #   넣으면 _generate_pair로 자동 전달된다.
                if (refine and base_buy_code is not None and best_is_mdd_only
                        and getattr(config, "freeze_buy_on_mdd_only", True)):
                    gen_kwargs["freeze_buy"] = True
                    print(f"[LOOP] freeze_buy=ON (best gen{best_gen} MDD-only: "
                          f"매수 동결·매도만 재생성)", flush=True)
                gen_res = _generate_pair(
                    provider, config, rid, gen_no, next_autopsy_feedback,
                    **gen_kwargs,
                )
                if gen_res.get("status") != "ok":
                    # 생성 실패도 robustness: 이 세대 score=0으로 기록 후 다음으로.
                    reason_g = f"generation failed: {gen_res.get('reason')}"
                    print(f"[LOOP] {reason_g}", flush=True)
                    st.record_generation(
                        rid, gen_no,
                        buy_name=f"AILOOP_{rid}_g{gen_no}_buy",
                        sell_name=f"AILOOP_{rid}_g{gen_no}_sell",
                        status="error", score=0.0, gate_passed=False, reason=reason_g,
                    )
                    gen_no += 1
                    continue
                buy_name = gen_res["buy_name"]
                sell_name = gen_res["sell_name"]
                cumulative_tokens += int(gen_res.get("tokens", 0) or 0)
                print(f"[LOOP] generated buy={buy_name} sell={sell_name} "
                      f"(cum_tokens={cumulative_tokens})", flush=True)
                _publish_live(st, rid, config, status="running", current_gen=gen_no,
                              cumulative_tokens=cumulative_tokens, phase="generate_done",
                              message=f"gen {gen_no} 전략 생성 완료: buy={buy_name}",
                              best_gen=best_gen, best_score=best_score,
                              best_buy=best_buy, best_sell=best_sell,
                              winner_gen=winner_gen, winner_score=winner_score,
                              winner_buy=winner_buy, winner_sell=winner_sell,
                              _log_buf=_live_log_buf)
                _print_strategy_head(buy_name)

            # --- b. 엔진 호환 보장 (formula 빈 테이블) ---
            bootstrap.ensure_loop_db_engine_compat()

            # --- c+d. BOUNDED 백테스트 + ROBUSTNESS BACKSTOP ---
            # US-007 — 백테스트 시작 라이브 발행.
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="backtest_start",
                          message=f"backtest start gen {gen_no}",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)
            t0 = time.time()
            try:
                if warm_session is not None:
                    # warm: 살아있는 엔진에 전략만 바꿔 백테 1회 (세대당 ~60초).
                    #   per-run fail-fast 타임아웃(bt_warm_run_timeout=120)을 전달한다.
                    #   over-firing 전략은 120초에 컷되고 리셋+재로딩 후 다음 run으로 넘어간다.
                    #   이 인자는 BackTest join에만 쓰이며, 데이터로딩(BacktestConfig.timeout)은
                    #   _build_warm_btconfig에서 별도로 높게 유지되므로 재로딩이 잘리지 않는다.
                    outcome = _warm_to_outcome(
                        warm_session.run(buy_name, sell_name,
                                         timeout=config.bt_warm_run_timeout)
                    )
                else:
                    # cold: 세대마다 stom_backtest.py 서브프로세스 (폴백/기존 경로).
                    outcome = run_backtest_for(config, buy_name, sell_name)
            except Exception as exc:  # noqa: BLE001 - 어떤 예외든 흡수, 루프 유지.
                outcome = BacktestOutcome(
                    False, "error", None, None, f"backtest raised: {exc}"
                )
            bt_elapsed = time.time() - t0
            # US-007 — 백테스트 종료 라이브 발행.
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="backtest_end",
                          message=f"backtest end gen {gen_no} status={outcome.status}",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)
            print(f"[LOOP] backtest status={outcome.status} "
                  f"elapsed={bt_elapsed:.1f}s reason={outcome.reason}", flush=True)

            if not outcome.ok:
                # 실패 세대: score=0, 계속. 단, '왜' 실패했는지를 구체적으로 분류해
                #   다음 세대 피드백 + 이력에 남긴다(맹목 변이 차단).
                err_history_line = _backtest_error_history_line(outcome.reason)
                st.record_generation(
                    rid, gen_no,
                    buy_name=buy_name, sell_name=sell_name,
                    status="error", score=0.0, gate_passed=False,
                    reason=f"backtest failed/timeout: {outcome.reason}",
                    csv_path=outcome.csv_path,
                )
                # 이력에 구체 실패 사유를 기록(CONVERGENCE — 회귀 회피 신호).
                history_records.append(GenRecord(
                    gen_no=gen_no, graded_score=0.0, gate_passed=False,
                    gate_reason=err_history_line, trade_count=0,
                    mdd=0.0, profit=0.0, gist=_strategy_gist(buy_name),
                ))
                # 다음 세대엔 '구체 원인'을 겨냥한 피드백(0거래면 완화, 런타임 오류면
                #   그 오류를 피하라 등) + 누적 이력을 함께 전달한다.
                #   실패(거래 0건/크래시)는 CSV가 없어 청산 부검을 못 하므로, 동일한
                #   원인 피드백을 매도 측에도 전달한다(특히 0거래면 진입 완화가 핵심).
                if effective_autopsy_fn is not None or effective_exit_autopsy_fn is not None:
                    err_fb = _backtest_error_feedback(outcome.reason, config)
                    next_autopsy_feedback = err_fb
                    next_sell_feedback = err_fb
                gen_no += 1
                continue

            # --- e. fitness (하드 게이트 + graded 선택 점수) ---
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="score_start",
                          message=f"gen {gen_no} 채점 시작",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)
            fit, graded, fit_err = _score_outcome(outcome, config)
            if fit is None:
                st.record_generation(
                    rid, gen_no,
                    buy_name=buy_name, sell_name=sell_name,
                    status="error", score=0.0, gate_passed=False,
                    reason=f"fitness failed: {fit_err}", csv_path=outcome.csv_path,
                )
                gen_no += 1
                continue

            # DB의 score 컬럼에는 GRADED 점수를 저장한다(루프가 best를 graded로
            #   선택/리포트하므로). 하드 게이트 통과/사유는 별도 컬럼에 보존된다.
            # mdd/profit/gist도 함께 기록해 대시보드 세대 행이 실값을 표시한다.
            gen_gist = _strategy_gist(buy_name)
            # P3 계보: 부모(parent_gen) 대비 지표 변경 요약(diff_from_parent)을 만든다.
            #   부모 행을 DB에서 읽어 graded/MDD/거래/수익 델타를 한 줄 NL로 압축한다.
            #   코드 전문은 복제 저장하지 않는다(lineage.diff_generations가 namespaced 재조회).
            diff_from_parent = _build_parent_diff(
                st, rid, parent_gen_for_record,
                graded.graded, graded.mdd, fit.trade_count, graded.total_profit,
            )
            # P10 — 수익률(%)은 graded(GradedResult)에 없고 엔진 metrics에만 있다
            #   (total_profit_pct = '수익률합계'). profit(원)과 별개로 발행해 대시보드
            #   세대 이력/차트가 수익률을 표시한다. metrics 누락 시 0.0 폴백(무예외).
            total_profit_pct = float((outcome.metrics or {}).get("total_profit_pct", 0.0) or 0.0)
            st.record_generation(
                rid, gen_no,
                buy_name=buy_name, sell_name=sell_name,
                status="ok", score=graded.graded, calmar=fit.calmar,
                uptrend_r2=fit.uptrend_r2, gate_passed=fit.gate_passed,
                reason=fit.reason, csv_path=outcome.csv_path,
                trade_count=fit.trade_count,
                daily_avg_trades=fit.daily_avg_trades,
                mdd=graded.mdd, profit=graded.total_profit,
                total_profit_pct=total_profit_pct,
                strategy_gist=gen_gist,
                parent_gen=parent_gen_for_record,
                diff_from_parent=diff_from_parent,
                payoff_ratio=graded.payoff_ratio,
                give_back_rate=graded.give_back_rate,
                dispersion_term=graded.dispersion_term,
                max_hold_count=graded.max_hold_count,
            )
            print(f"[LOOP] graded={graded.graded:.6g} hard_composite={fit.score:.6g} "
                  f"calmar={fit.calmar:.4g} r2={fit.uptrend_r2:.4g} "
                  f"gate={fit.gate_passed} reason={fit.reason} "
                  f"mdd={graded.mdd:.4g} profit={graded.total_profit:,.0f} "
                  f"trades={fit.trade_count} gate_distance={graded.gate_distance}",
                  flush=True)
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="score_done",
                          message=(f"gen {gen_no} 채점 완료: gate={'pass' if fit.gate_passed else 'fail'}"
                                   f" graded={graded.graded:.4g}"),
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)

            # 이력 기록(CONVERGENCE).
            history_records.append(GenRecord(
                gen_no=gen_no, graded_score=graded.graded,
                gate_passed=fit.gate_passed, gate_reason=graded.gate_distance,
                trade_count=fit.trade_count, mdd=graded.mdd,
                profit=graded.total_profit, gist=gen_gist,
            ))

            # best는 GRADED 점수로 선택한다(선택 그래디언트).
            if best_score is None or graded.graded > best_score:
                best_score = graded.graded
                best_gen = gen_no
                best_buy = buy_name
                best_sell = sell_name
                st.update_best(rid, best_gen, best_score)
                # 타깃 처방: 이 best가 **MDD만 부족**(빈도ok + 수익>0 + mdd>cap)한
                #   실패인지 계산한다. True면 다음 세대 매수를 동결하고 청산만 탐색한다.
                #   (시드=gen0도 best가 되며 여기서 계산된다.)
                best_is_mdd_only = (
                    (not fit.gate_passed)
                    and (float(getattr(fit, "daily_avg_trades", 0.0))
                         >= float(getattr(config, "min_daily_trades", 0.0) or 0.0))
                    and (float(fit.total_profit) > 0.0)
                    and (abs(float(fit.mdd))
                         > float(getattr(config, "mdd_cap", float("inf"))))
                )
                # seed-and-refine hill-climb: 더 좋은 전략이 나오면 그 코드를
                #   다음 세대의 새 출발점으로 삼는다(refine 모드일 때만).
                if getattr(config, "bt_refine_from_best", False):
                    new_buy_code = _read_strategy_code(buy_name, "buy")
                    new_sell_code = _read_strategy_code(sell_name, "sell")
                    if new_buy_code is not None:
                        base_buy_code = new_buy_code
                    if new_sell_code is not None:
                        base_sell_code = new_sell_code

            # P5 — 과적합 방어(holdout 졸업검사). 토글 ON이면 train 게이트를 통과한
            #   후보를 결과 CSV의 holdout 거래일 슬라이스로도 게이트 판정한다(추가 백테
            #   없음). holdout 미통과면 winner 갱신을 스킵한다(best=graded는 위에서 이미
            #   갱신됐으므로 진행은 막지 않는다). 토글 OFF(기본)면 verdict=None이라
            #   아래 winner 조건이 기존과 완전히 동일하게 동작한다(하위호환).
            last_holdout_verdict = None
            holdout_ok = True
            if getattr(config, "graduation_holdout", False) and fit.gate_passed:
                last_holdout_verdict = _compute_holdout_verdict(outcome, config)
                holdout_ok = bool(last_holdout_verdict and last_holdout_verdict.passed)
                hv = last_holdout_verdict
                print(f"[LOOP] holdout gate: passed={hv.passed} status={hv.status} "
                      f"trades={hv.trade_count} mdd={hv.mdd_pct:.4g} "
                      f"profit={hv.total_profit:,.0f} reason={hv.reason}", flush=True)

            # winner/졸업은 하드 게이트 통과 전략에서만 갱신(graduation 기준 유지).
            #   토글 ON이면 holdout 게이트도 통과(holdout_ok)해야 winner로 인정한다.
            #   P7 — 목표별 비교 키로 갱신한다('profit'은 수익 최대·동률 시 MDD 낮은 것;
            #   risk_adjusted/balanced는 스칼라 점수). 기본 risk_adjusted는 fit.score
            #   단일 비교라 기존 동작과 동일하다(하위호환).
            if fit.gate_passed and holdout_ok:
                cand_key = _winner_compare_key(fit, graded, config)
                if winner_key is None or cand_key > winner_key:
                    winner_key = cand_key
                    winner_score = _winner_score_value(fit, graded, config)
                    winner_gen = gen_no
                    winner_buy = buy_name
                    winner_sell = sell_name

            # --- f. 다음 세대 피드백: 진입(BUY) = 게이트-거리 + 진입 변별 변수,
            #        매도(SELL) = 게이트-거리 + 청산(give-back/손절/보유/매도규칙) ---
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="autopsy_start",
                          message=f"gen {gen_no} 부검 시작",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)
            next_autopsy_feedback, next_sell_feedback, last_autopsy_page_data = _build_feedback(
                config, outcome, fit, graded,
                effective_autopsy_fn, effective_exit_autopsy_fn,
                effective_segment_autopsy_fn,
            )
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="autopsy_done",
                          message=f"gen {gen_no} 부검 완료",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf)

            # US-007 — 세대 완료 라이브 발행 (generations 갱신 반영).
            #   P1: 세그먼트 부검 요약을 page_data["autopsy"]로 실어 LIVE 패널에 발행.
            #   P3/P4: 계보(lineage) + 메타(meta) 요약도 같은 page_data에 합쳐 발행.
            page_data = _build_live_page_data(
                st, rid, config, last_autopsy_page_data,
                holdout_verdict=last_holdout_verdict,
            )
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="generation_done",
                          message=f"generation {gen_no} recorded",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          page_data=page_data,
                          _log_buf=_live_log_buf)

            gen_no += 1

        st.finish_run(rid, status="complete")
        # P4 — run 종료 시 누적 메타 인사이트를 재집계·영속한다(state 닫기 전).
        #   다음 run의 _load_meta_seed가 최신 인사이트를 환류한다. 실패는 흡수.
        _refresh_meta_insights(st)
        # US-007 — 최종 complete 라이브 발행 (state 닫기 전, DB 조회 가능 시점).
        _publish_live(st, rid, config, status="complete", current_gen=gen_no,
                      cumulative_tokens=cumulative_tokens, phase="complete",
                      message=f"loop complete: {stop_reason}",
                      best_gen=best_gen, best_score=best_score,
                      best_buy=best_buy, best_sell=best_sell,
                      winner_gen=winner_gen, winner_score=winner_score,
                      winner_buy=winner_buy, winner_sell=winner_sell,
                      _log_buf=_live_log_buf)
        # 요약은 state를 닫기(finally) 전에 구성한다 — 닫힌 DB에서 조회하면
        #   sqlite3.ProgrammingError(Cannot operate on a closed database)가 난다.
        summary = {
            "run_id": rid,
            "generations": st.get_cumulative_generation_count(rid),
            "best_gen": best_gen,
            "best_score": best_score,  # GRADED 최고 점수.
            "best_buy": best_buy,
            "best_sell": best_sell,
            # 졸업/우승(하드 게이트 통과). winner_gen=-1이면 통과 세대 없음.
            "winner_gen": winner_gen,
            "winner_score": winner_score,
            "winner_buy": winner_buy,
            "winner_sell": winner_sell,
            "stop_reason": stop_reason,
        }
    finally:
        # warm 세션 정리(엔진/서브토탈/공유메모리) — 프록시/state 정리보다 먼저.
        if warm_session is not None:
            try:
                warm_session.close()
            except Exception:  # noqa: BLE001 - 세션 정리 실패는 종료를 막지 않음.
                pass
        # US-007 — 정지 플래그는 run 종료 시 항상 cleanup (다음 run 오염 방지).
        clear_stop_flag()
        if proxy_active:
            _stop_proxy()
        if owns_state:
            st.close()
        # P6 — 우리가 잡은 단일 writer 락을 해제한다(다음 루프 진입 허용).
        if lock_acquired:
            release_run_lock()

    # summary는 정상 경로(try 끝)에서 state 닫기 전에 구성된다. 예외가
    #   while 루프를 빠져나가 전파된 경우 summary가 None일 수 있는데, 그땐
    #   close 이후라 DB 조회가 불가하므로 메모리에 들고 있던 값으로 폴백한다.
    if summary is None:
        summary = {
            "run_id": rid,
            "generations": gen_no,
            "best_gen": best_gen,
            "best_score": best_score,
            "best_buy": best_buy,
            "best_sell": best_sell,
            "winner_gen": winner_gen,
            "winner_score": winner_score,
            "winner_buy": winner_buy,
            "winner_sell": winner_sell,
            "stop_reason": stop_reason,
        }
    return summary


# =====================================================================
# P3 연구 파이프라인 / P4 메타분석 — 환류·계보·발행 헬퍼.
# =====================================================================
def _load_meta_seed() -> Optional[str]:
    """영속된 메타 인사이트를 로드해 생성 프롬프트 주입 가이드(meta_seed)를 만든다.

    P4 환류 진입점. meta_insights.json이 없거나(첫 run) 신호가 없으면 None을
    돌려 주입을 건너뛴다(하위호환). load/build 실패는 흡수한다(학습 보조 경로).
    """
    try:
        from ai_strategy_loop.meta import build_meta_seed_text, load_meta_insights  # noqa: PLC0415

        insights = load_meta_insights()
        return build_meta_seed_text(insights)
    except Exception as exc:  # noqa: BLE001 - 메타 환류는 정확성 경로가 아니다.
        logger.info("메타 시드 로드 실패(무시): %s", exc)
        return None


def _build_parent_diff(
    st: LoopState,
    rid: str,
    parent_gen: Optional[int],
    graded: float,
    mdd: float,
    trade_count: int,
    profit: float,
) -> Optional[str]:
    """부모(parent_gen) 대비 이 세대의 지표 변경을 한 줄 NL로 요약한다(P3).

    부모가 없으면(루트 세대) None. 부모 행을 DB에서 읽어 graded/MDD/거래/수익
    델타를 압축한다. 코드 전문 비교는 lineage.diff_generations(namespaced 재조회)가
    on-demand로 한다 — 여기선 지표 변경 요약만 영속한다(복제 저장 회피).
    """
    if parent_gen is None or parent_gen < 0:
        return None
    try:
        rows = {int(g.get("gen_no", -1)): g for g in st.get_generations(rid)}
    except Exception:  # noqa: BLE001 - 조회 실패는 diff 없이 진행(루프를 막지 않음).
        return None
    parent = rows.get(int(parent_gen))
    if parent is None:
        return None

    def _delta(cur: float, prev: float) -> str:
        d = cur - prev
        sign = "+" if d >= 0 else ""
        return f"{sign}{d:.4g}"

    p_graded = float(parent.get("score", 0.0) or 0.0)
    p_mdd = float(parent.get("mdd", 0.0) or 0.0)
    p_trades = int(parent.get("trade_count", 0) or 0)
    p_profit = float(parent.get("profit", 0.0) or 0.0)
    return (
        f"gen{parent_gen} 대비: graded {_delta(graded, p_graded)} "
        f"MDD {_delta(mdd, p_mdd)} 거래 {_delta(trade_count, p_trades)} "
        f"손익 {_delta(profit, p_profit)}"
    )


def _refresh_meta_insights(st: LoopState) -> None:
    """누적 generations(여러 run)에서 메타 인사이트를 재집계해 영속한다(P4).

    run 종료 시 1회 호출. 다음 run의 _load_meta_seed가 이 파일을 읽어 환류한다.
    집계/저장 실패는 흡수한다(학습 보조 경로 — 루프 종료를 막지 않는다).
    """
    try:
        from ai_strategy_loop.meta import aggregate_meta_insights, save_meta_insights  # noqa: PLC0415

        all_gens = st.get_all_generations()
        insights = aggregate_meta_insights(all_gens)
        save_meta_insights(insights)
    except Exception as exc:  # noqa: BLE001 - 메타 재집계는 정확성 경로가 아니다.
        logger.info("메타 인사이트 재집계 실패(무시): %s", exc)


def _build_live_page_data(
    st: LoopState,
    rid: str,
    config: LoopConfig,
    autopsy_page_data: Optional[Dict[str, Any]],
    holdout_verdict: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """세대 완료 시 LIVE 발행할 page_data를 조립한다(autopsy + lineage + meta + holdout).

    - autopsy(P1): 세그먼트 부검 요약(인자로 받음). 없으면 생략.
    - lineage(P3): 현재 run의 계보 요약(lineage.to_page_data). 조회 실패는 생략.
    - meta(P4): 누적 메타 인사이트 요약(있으면). 영속 파일이 없으면 생략.
    - holdout(P5): holdout 졸업검사 결과(토글 ON일 때만 verdict가 주어짐).
      graduation_holdout=ON 인데 verdict가 None이면(이 세대가 train 게이트 미통과 등)
      status='off' 배지로 발행한다. 토글 OFF면 holdout 섹션을 아예 넣지 않는다(하위호환).

    각 섹션 산출 실패는 흡수한다(LIVE 발행은 정확성 경로가 아니다). 아무 섹션도
    없으면 None을 돌려 기존 호출부(page_data 무발행)와 동일하게 동작한다.
    """
    page_data: Dict[str, Any] = {}
    if autopsy_page_data:
        page_data["autopsy"] = autopsy_page_data

    # P5 holdout 졸업검사 배지: 토글 ON일 때만 섹션을 실어 보낸다(OFF면 무발행=하위호환).
    if getattr(config, "graduation_holdout", False):
        try:
            from ai_strategy_loop.fitness import holdout_verdict_to_page_data  # noqa: PLC0415

            page_data["holdout"] = holdout_verdict_to_page_data(holdout_verdict)
        except Exception as exc:  # noqa: BLE001 - holdout 배지 산출 실패는 생략 가능.
            logger.info("holdout page_data 실패(무시): %s", exc)

    # P3 계보 요약.
    try:
        from ai_strategy_loop.controller import lineage as _lineage  # noqa: PLC0415

        page_data["lineage"] = _lineage.to_page_data(st, rid)
    except Exception as exc:  # noqa: BLE001 - 계보 발행은 보조이므로 생략 가능.
        logger.info("lineage page_data 실패(무시): %s", exc)

    # P4 메타 인사이트 요약(영속 파일이 있을 때만 — 없으면 status empty 생략).
    try:
        from ai_strategy_loop.meta import load_meta_insights  # noqa: PLC0415
        from ai_strategy_loop.meta.seed import to_page_data as _meta_page_data  # noqa: PLC0415

        insights = load_meta_insights()
        if insights is not None:
            page_data["meta"] = _meta_page_data(insights)
    except Exception as exc:  # noqa: BLE001 - 메타 발행은 보조이므로 생략 가능.
        logger.info("meta page_data 실패(무시): %s", exc)

    return page_data or None


def _build_feedback(config, outcome, fit, graded,
                    effective_autopsy_fn, effective_exit_autopsy_fn=None,
                    effective_segment_autopsy_fn=None):
    """다음 세대 피드백을 진입(BUY)/매도(SELL) 두 갈래로 조립한다.

    공통: 게이트 실패면 그 원인(MDD/손익/거래수)을 직접 겨냥하는 지시문을 앞에 붙인다.
      - BUY 피드백 = 게이트 지시 + 진입 부검(win/loss B_* 변별) + 세그먼트 부검.
      - SELL 피드백 = 게이트 지시 + 청산 부검(give-back/손절/보유시간/매도규칙) + 세그먼트 부검.

    세그먼트 부검(P1)은 "어느 시총·시간대에서 손실이 집중되고 어느 변수의 어느
    구간이 손실인지"를 구체 임계값과 함께 더해 진입/청산 양쪽에 합성한다. 또한
    세그먼트 요약 dict(to_page_data)를 LIVE 부검 패널용으로 함께 돌려준다.

    부검 실패는 루프를 막지 않는다(예외 흡수). 합성 피드백은 토큰 회귀 게이트
    (cap_feedback)로 절대 문자 상한을 적용한다.

    Returns:
        (buy_feedback, sell_feedback, autopsy_page_data) —
        피드백은 각각 str 또는 None, page_data는 dict 또는 None.
    """
    from ai_strategy_loop.autopsy import (  # noqa: PLC0415
        cap_feedback,
        gate_failure_directive,
        summarize_segments,
        to_page_data,
    )

    directive = gate_failure_directive(
        gate_passed=fit.gate_passed,
        gate_reason=graded.gate_distance,
        mdd=graded.mdd,
        mdd_cap=float(getattr(config, "mdd_cap", 0.0) or 0.0),
        total_profit=graded.total_profit,
        trade_count=fit.trade_count,
        min_trades=int(getattr(config, "min_trades", 0) or 0),
    )

    def _run_autopsy(fn, label):
        if fn is None or not outcome.csv_path:
            return None
        try:
            return fn(outcome.csv_path)
        except Exception as exc:  # noqa: BLE001 - 부검 실패는 루프를 막지 않음.
            logger.info("%s 실패(무시): %s", label, exc)
            return None

    # 세그먼트 부검(P1): 결과 객체 1회 산출 → NL 피드백 + LIVE page_data 양쪽에 재사용.
    segment_result = _run_autopsy(effective_segment_autopsy_fn, "segment autopsy_fn")
    segment_fb = None
    autopsy_page_data = None
    if segment_result is not None:
        try:
            segment_fb = summarize_segments(segment_result, config) or None
            autopsy_page_data = to_page_data(segment_result)
        except Exception as exc:  # noqa: BLE001 - 요약/직렬화 실패는 루프를 막지 않음.
            logger.info("segment summarize/to_page_data 실패(무시): %s", exc)

    buy_parts = [directive] if directive else []
    buy_autopsy = _run_autopsy(effective_autopsy_fn, "buy autopsy_fn")
    if buy_autopsy:
        buy_parts.append(buy_autopsy)
    if segment_fb:
        buy_parts.append(segment_fb)

    sell_parts = [directive] if directive else []
    sell_autopsy = _run_autopsy(effective_exit_autopsy_fn, "exit autopsy_fn")
    if sell_autopsy:
        sell_parts.append(sell_autopsy)
    if segment_fb:
        sell_parts.append(segment_fb)

    buy_fb = cap_feedback("\n\n".join(buy_parts)) if buy_parts else None
    sell_fb = cap_feedback("\n\n".join(sell_parts)) if sell_parts else None
    return buy_fb, sell_fb, autopsy_page_data


def _winner_score_value(fit, graded, config: LoopConfig) -> float:
    """P7 — winner(졸업) 점수 스칼라를 목표별로 만든다(요약/발행에 실리는 값).

    - 'risk_adjusted'(기본): 하드 composite fit.score (기존 동작 — 하위호환).
    - 'profit'             : total_profit(절대수익). 클수록 좋은 winner.
    - 'balanced'           : composite·(1-w)+profit_term·w 블렌드(graded.objective와 동일 공식).
    - 'uptrend'            : uptrend_r2(누적수익 곡선 우상향 R²). 클수록 우상향 winner.
    - 'multiyear'          : graded.graded(=1.0 + composite×다년 전구간 우상향 stability_term).
                            가장 강한 다년-우상향 전략(우상향 R² × 위험조정 규모)이 winner.
                            (stability_term 단독이 아니라 전체 graded를 써서, 균등하지만
                            약한 전략이 강하지만 덜 균등한 전략을 이기지 못하게 한다.)

    알 수 없는 목표는 risk_adjusted로 폴백한다.
    """
    objective = str(getattr(config, "winner_objective", "risk_adjusted") or "risk_adjusted")
    if objective == "profit":
        return float(graded.total_profit)
    if objective == "balanced":
        from ai_strategy_loop.fitness.score import _gate_passed_term  # noqa: PLC0415

        return float(_gate_passed_term("balanced", fit.score, graded.profit_term, config))
    if objective == "uptrend":
        return float(fit.uptrend_r2)
    if objective == "multiyear":
        return float(graded.graded)
    return float(fit.score)


def _winner_compare_key(fit, graded, config: LoopConfig):
    """winner 비교용 정렬 키(클수록 우수). 'profit'은 동률 시 MDD 낮은 것을 우선한다.

    - 'profit': (total_profit, -mdd) — 수익 최대, 동률이면 MDD 낮은 쪽.
    - 'uptrend': (uptrend_r2, score) — R² 최대, 동률이면 composite(Calmar×R²) 높은 쪽.
    - 'multiyear': (graded,) — 가장 강한 다년-우상향 전략(graded=1.0+composite×전구간
      우상향 stability_term)이 winner. stability_term 단독이 아니라 전체 graded를 써서
      '균등하지만 약한' 전략이 '강하지만 덜 균등한' 전략을 이기지 못하게 한다.
    - 그 외   : (score,) — 스칼라 단일 비교(risk_adjusted/balanced).
    """
    objective = str(getattr(config, "winner_objective", "risk_adjusted") or "risk_adjusted")
    if objective == "profit":
        return (float(graded.total_profit), -float(graded.mdd))
    if objective == "uptrend":
        return (float(fit.uptrend_r2), float(fit.score))
    if objective == "multiyear":
        return (float(graded.graded),)
    return (_winner_score_value(fit, graded, config),)


def _score_outcome(outcome: BacktestOutcome, config: LoopConfig):
    """성공한 백테스트 결과를 fitness(하드 게이트) + graded(선택)로 환산한다.

    반환: (fit, graded, err). 실패 시 (None, None, err).
    하드 게이트 fit은 졸업/우승 판정에, graded는 best 선택/방향에 쓴다.
    """
    from ai_strategy_loop.fitness import (  # noqa: PLC0415
        compute_fitness,
        compute_graded_fitness,
        load_equity_series_from_csv,
        load_exit_quality_from_csv,
    )

    csv_path = outcome.csv_path
    abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    try:
        equity = load_equity_series_from_csv(abs_csv)
    except Exception as exc:  # noqa: BLE001 - CSV 파싱 실패는 score=0 처리.
        return None, None, f"equity load 실패: {exc}"
    # 청산 품질(payoff_ratio/give_back_rate)을 per-trade CSV에서 산출해 metrics에
    #   merge한다. 실패해도(컬럼 없음/파싱 오류) score는 그대로 진행한다(빈 dict 폴백).
    #   원본 outcome.metrics는 변형하지 않고 복사본에 merge한다(불변성).
    mfe_threshold = float(getattr(config, "give_back_mfe_threshold", 1.5) or 1.5)
    try:
        exit_quality = load_exit_quality_from_csv(abs_csv, mfe_threshold)
    except Exception:  # noqa: BLE001 - 청산품질 산출 실패는 score에 영향 없이 흡수.
        exit_quality = {}
    merged_metrics = dict(outcome.metrics or {})
    merged_metrics.update(exit_quality)
    # 다종목 분산 보상은 동시보유(max_hold_count)를 쓴다. outcome.metrics는
    #   cli.runner._extract_metrics가 'max_hold_count'(최대보유종목수)를 항상 포함하므로
    #   merged_metrics에도 들어 있다. 누락된 더블/구 데이터면 compute_graded_fitness가
    #   None 처리(무영향)한다(하위호환).
    # 다년 안정성(② 다년 학습): winner_objective='multiyear'일 때만 결과 CSV를 연도별로
    #   쪼개 cross-year stability_term을 산출한다(다른 objective면 zero-cost — 평가 안 함).
    #   산출 실패(CSV 없음/유효연도 부족/파싱 오류)는 None→중립(score에 무영향)으로 흡수한다.
    multiyear_stability = None
    if str(getattr(config, "winner_objective", "") or "") == "multiyear":
        try:
            from ai_strategy_loop.fitness import compute_multiyear_stability  # noqa: PLC0415

            _stab = compute_multiyear_stability(abs_csv, config)
            multiyear_stability = _stab.stability_term if _stab is not None else None
        except Exception:  # noqa: BLE001 - 다년 산출 실패는 score에 영향 없이 흡수(None→중립).
            multiyear_stability = None
    try:
        fit = compute_fitness(merged_metrics, equity, config)
        graded = compute_graded_fitness(
            merged_metrics, equity, config,
            dispersion_enabled=config.dispersion_enabled,
            min_hold_symbols=config.min_hold_symbols,
            multiyear_stability=multiyear_stability,
        )
    except Exception as exc:  # noqa: BLE001
        return None, None, f"compute_fitness 실패: {exc}"
    return fit, graded, None


def _compute_holdout_verdict(outcome: BacktestOutcome, config: LoopConfig):
    """P5 — 결과 CSV를 holdout 거래일로 분할해 졸업검사(holdout 게이트)를 판정한다.

    추가 백테 없이 outcome.csv_path 한 파일을 거래일 기준 train/holdout으로 쪼갠다.
    csv_path가 없거나 산출이 실패하면 보수적 미졸업(passed=False) verdict를 돌려
    winner 갱신을 막는다(루프 자체는 막지 않는다).
    """
    from ai_strategy_loop.fitness import (  # noqa: PLC0415
        HoldoutVerdict,
        compute_holdout_verdict,
    )

    csv_path = outcome.csv_path
    if not csv_path:
        return HoldoutVerdict(
            passed=False, status="error", trade_count=0, total_profit=0.0,
            mdd_pct=0.0, reason="holdout 판정 불가: csv_path 없음",
        )
    abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    try:
        return compute_holdout_verdict(abs_csv, config)
    except Exception as exc:  # noqa: BLE001 - holdout 산출 실패는 미졸업으로 흡수.
        return HoldoutVerdict(
            passed=False, status="error", trade_count=0, total_profit=0.0,
            mdd_pct=0.0, reason=f"holdout 판정 예외: {exc}",
        )


def _read_strategy_code(name: str, kind: str) -> Optional[str]:
    """루프 DB에서 전략의 전체 코드를 읽는다 (seed-and-refine 출발점용).

    kind=='buy'면 stockbuy, kind=='sell'면 stocksell 테이블의 "전략코드" 컬럼에서
    name(=index)의 전체 코드를 읽어 반환한다. _strategy_gist의 컬럼 탐지 패턴을
    재사용한다("전략코드" 우선, 없으면 위치 cols[1] 폴백). 실패하면 None을 돌려
    호출자가 fresh 생성으로 자연 폴백하게 한다(루프를 막지 않음).

    Args:
        name: 전략 이름 (DB index 컬럼). None/빈문자열이면 None 반환.
        kind: 'buy' | 'sell'. 테이블 선택.

    Returns:
        전체 전략 코드 문자열, 또는 조회 실패/미존재 시 None.
    """
    import sqlite3  # noqa: PLC0415

    if not name or kind not in ("buy", "sell"):
        return None
    table = "stockbuy" if kind == "buy" else "stocksell"
    db = str(bootstrap.LOOP_DB_STRATEGY)
    try:
        con = sqlite3.connect(db)
        try:
            cur = con.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            # named "전략코드" 우선, 없을 때만 위치 cols[1] 폴백 (_strategy_gist 패턴).
            code_col = "전략코드" if "전략코드" in cols else (cols[1] if len(cols) >= 2 else "전략코드")
            row = cur.execute(
                f'SELECT "{code_col}" FROM {table} WHERE "index" = ?', (name,)
            ).fetchone()
        finally:
            con.close()
    except Exception:  # noqa: BLE001 - 조회 실패는 None 폴백(fresh 생성).
        return None
    if not row or not row[0]:
        return None
    return str(row[0])


def _strategy_gist(name: str, max_len: int = 90) -> str:
    """루프 DB에서 전략 코드의 핵심 진입 조건 한 줄을 뽑는다 (이력 gist용).

    주석/상태초기화/실행문을 건너뛰고 첫 조건 분기(if ...) 한 줄을 요약한다.
    실패하면 빈 문자열(이력은 gist 없이도 동작).
    """
    import sqlite3  # noqa: PLC0415

    db = str(bootstrap.LOOP_DB_STRATEGY)
    try:
        con = sqlite3.connect(db)
        try:
            cur = con.cursor()
            cur.execute('PRAGMA table_info(stockbuy)')
            cols = [r[1] for r in cur.fetchall()]
            # named "전략코드" 우선, 없을 때만 위치 cols[1] 폴백.
            code_col = "전략코드" if "전략코드" in cols else (cols[1] if len(cols) >= 2 else "전략코드")
            row = cur.execute(
                f'SELECT "{code_col}" FROM stockbuy WHERE "index" = ?', (name,)
            ).fetchone()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return ""
    if not row or not row[0]:
        return ""
    for raw in str(row[0]).splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("if ") or (" and " in ln) or (" or " in ln) or (">" in ln) or ("<" in ln):
            return ln[:max_len]
    return ""


def _print_strategy_head(name: str, lines: int = 6) -> None:
    """루프 DB에서 전략 코드 앞부분 몇 줄을 출력한다 (검증 가시성)."""
    import sqlite3  # noqa: PLC0415

    db = str(bootstrap.LOOP_DB_STRATEGY)
    try:
        con = sqlite3.connect(db)
        try:
            cur = con.cursor()
            cur.execute('PRAGMA table_info(stockbuy)')
            cols = [r[1] for r in cur.fetchall()]
            # named "전략코드" 우선, 없을 때만 위치 cols[1] 폴백.
            code_col = "전략코드" if "전략코드" in cols else (cols[1] if len(cols) >= 2 else "전략코드")
            row = cur.execute(
                f'SELECT "{code_col}" FROM stockbuy WHERE "index" = ?', (name,)
            ).fetchone()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return
    if not row:
        return
    code = (row[0] or "").splitlines()
    print(f"[LOOP] --- {name} (first {lines} lines) ---", flush=True)
    for ln in code[:lines]:
        print(f"    {ln}", flush=True)
    print(f"[LOOP] --- /{name} ---", flush=True)


# =====================================================================
# provider + 프록시 생명주기.
# =====================================================================
def _make_provider_with_proxy(config: LoopConfig):
    """provider를 만들고 gpt_auth면 프록시를 기동한다.

    Returns:
        (provider, proxy_active: bool). proxy_active면 finally에서 _stop_proxy().
    """
    from ai_strategy_loop.provider.factory import make_provider  # noqa: PLC0415

    proxy_active = False
    if getattr(config, "provider", None) == "gpt_auth":
        from ai_strategy_loop.provider.chatgpt_oauth import (  # noqa: PLC0415
            inject_env,
            start_proxy_sync,
            clear_env,
        )
        inject_env()
        if not start_proxy_sync():
            clear_env()
            raise RuntimeError("gpt_auth 프록시 시작 실패")
        proxy_active = True
    return make_provider(config), proxy_active


def _stop_proxy() -> None:
    from ai_strategy_loop.provider.chatgpt_oauth import (  # noqa: PLC0415
        stop_proxy_sync,
        clear_env,
    )
    try:
        stop_proxy_sync()
    finally:
        clear_env()


# =====================================================================
# CLI (dry-run).
# =====================================================================
def _main(argv=None) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        prog="ai_strategy_loop.controller.loop",
        description="STOM AI strategy loop — 헤드리스 진화 루프 (US-005 Phase 2b)",
    )
    parser.add_argument("--max-gen", type=int, default=3,
                        help="생성 세대 수 상한 (default: 3, dry-run용)")
    parser.add_argument("--provider", type=str, default="gpt_auth",
                        choices=["gpt_auth", "openrouter", "codex_proxy"],
                        help="LLM provider (default: gpt_auth)")
    parser.add_argument("--run-id", type=str, default=None,
                        help="resume할 run_id (미지정 시 새 run)")
    # US-007 — 대시보드(GUI)가 start 제어로 전달하는 전체 설정 JSON.
    #   CLI=GUI 계약: 같은 LoopConfig를 launch_config.config_from_dict로 만든다.
    #   --config-json은 JSON 문자열 또는 JSON 파일 경로 둘 다 받는다.
    parser.add_argument("--config-json", type=str, default=None,
                        help="LoopConfig dict의 JSON 문자열 또는 .json 파일 경로 "
                             "(GUI start 제어가 전달; 지정 시 --provider/--max-gen 무시)")
    args = parser.parse_args(argv)

    if args.config_json:
        from ai_strategy_loop.launch_config import config_from_dict  # noqa: PLC0415

        raw = args.config_json
        if os.path.isfile(raw):
            with open(raw, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = json.loads(raw)
        config = config_from_dict(data)
    else:
        config = LoopConfig(provider=args.provider, max_generations=args.max_gen)

    print("[LOOP] loop DB        :", bootstrap.LOOP_DB_STRATEGY, flush=True)
    print("[LOOP] provider       :", config.provider, flush=True)
    print("[LOOP] max_generations:", config.max_generations, flush=True)
    print("[LOOP] bt_timeframe   :", config.bt_timeframe, flush=True)
    print("[LOOP] bt_engine_mode :", config.bt_engine_mode, flush=True)

    t0 = time.time()
    # seed-and-refine: config에 seed가 있으면 gen0 출발점으로 전달한다
    #   (현재 _main은 seed를 안 넘겨 무시되던 것을 배선).
    summary = run_loop(
        config, run_id=args.run_id,
        seed_buy=getattr(config, "seed_buy", None),
        seed_sell=getattr(config, "seed_sell", None),
    )
    elapsed = time.time() - t0

    print("\n[LOOP] === SUMMARY ===", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"[LOOP] wall-clock: {elapsed:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
