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
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple  # noqa: E402

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
from ai_strategy_loop.controller.telemetry import (  # noqa: E402
    TelemetryRing,
    event_type_for_stage,
    telemetry_log_line,
)

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
    from ai_strategy_loop.controller.condition_discovery import effective_condition_discovery_runtime_config  # noqa: PLC0415

    config = effective_condition_discovery_runtime_config(config)
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
            "--start-time", str(config.bt_universe_start_time),
            "--end-time", str(config.bt_universe_end_time),
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
            "--start-time", str(config.bt_universe_start_time),
            "--end-time", str(config.bt_universe_end_time),
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
    from ai_strategy_loop.controller.condition_discovery import effective_condition_discovery_runtime_config  # noqa: PLC0415

    config = effective_condition_discovery_runtime_config(config)
    # min 타임프레임 + full_session_enabled일 때만 장중 윈도우를 풀세션까지 연다.
    #   OFF(기본) 또는 tick → bt_universe_end_time(92800) = 기존과 byte-identical.
    #   tick은 데이터 09:30 캡이라 토글과 무관하게 항상 bt_universe_end_time.
    if config.bt_timeframe != "tick" and getattr(config, "full_session_enabled", False):
        warm_end_time = config.bt_min_universe_end_time
    else:
        warm_end_time = config.bt_universe_end_time
    return BacktestConfig(
        buy_strategy="",
        sell_strategy="",
        start_date=config.bt_full_start,
        end_date=config.bt_full_end,
        start_time=config.bt_universe_start_time,
        end_time=warm_end_time,
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

def _warm_session_page_data(*, prepare: Optional[dict] = None, last_run: Optional[dict] = None) -> Dict[str, Any]:
    """warm prepare/run timing metadata를 dashboard page_data용으로 안전하게 투영한다."""
    payload: Dict[str, Any] = {}
    if isinstance(prepare, dict):
        timing = prepare.get("timing")
        if isinstance(timing, dict):
            prepare_timing = dict(timing)
            payload["prepare"] = prepare_timing
            if "prepare_elapsed" in prepare_timing:
                payload["prepare_elapsed_sec"] = prepare_timing["prepare_elapsed"]
            for key in ("engine_count", "back_count"):
                if key in prepare_timing:
                    payload.setdefault(key, prepare_timing[key])
    if isinstance(last_run, dict):
        timing = last_run.get("timing")
        if isinstance(timing, dict):
            run_timing = dict(timing)
            payload["last_run"] = run_timing
            if "run_elapsed" in run_timing:
                payload["last_run_elapsed_sec"] = run_timing["run_elapsed"]
                payload["run_elapsed_sec"] = run_timing["run_elapsed"]
            for key in ("engine_count", "back_count", "timeout_count", "recovery_attempts", "status"):
                if key in run_timing:
                    payload[key] = run_timing[key]
    return {"warm_session": payload} if payload else {}

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
        feedback = summarize(result, config)
        # R2(2026-06-11) — 반사실 필터 환류(토글, 기본 OFF). 직전 백테 CSV에서
        #   "강화 필터를 걸었다면"을 백테 0회로 평가해, 총손익이 깎이지 않는 필터만
        #   손익 영향 숫자와 함께 매수 피드백에 덧붙인다(방향+숫자+증거 — G1·G2 해소).
        #   실패/제안 없음은 조용히 기존 피드백만 반환(흡수 — byte-동일 하위호환).
        if getattr(config, "counterfactual_feedback_enabled", False):
            try:
                from ai_strategy_loop.fitness.counterfactual import (  # noqa: PLC0415
                    feedback_lines,
                    suggest_filters,
                )
                cf_lines = feedback_lines(suggest_filters(abs_csv, top_k=3))
                if cf_lines:
                    feedback = (feedback or "") + "\n" + "\n".join(cf_lines)
            except Exception:  # noqa: BLE001 - 보조 환류 실패가 부검을 막지 않게.
                pass
        return feedback

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

def _condition_pattern_cards_from_examples(kind: str, examples: Optional[list]) -> list:
    """Convert read-only few-shot examples into anti-copy pattern cards."""

    if not examples:
        return []
    from ai_strategy_loop.controller.condition_discovery_feedback import build_pattern_card  # noqa: PLC0415

    cards = []
    for idx, code in enumerate(examples[:5], start=1):
        compact = str(code or "").strip()
        if not compact:
            continue
        cards.append(build_pattern_card(
            card_id=f"{kind}-pattern-{idx}",
            source_label="seed_db:few_shot",
            side=kind,
            expression=compact,
            pattern_summary="human DB composition grammar sample; thresholds stripped",
            variable_families=["human_db", "composition", kind],
            composition_tags=["few_shot", "anti_copy"],
        ))
    return cards

def _condition_pattern_cards_for_config(config: LoopConfig) -> list:
    """Build read-only human DB pattern cards when seed-db few-shot is active."""

    if not getattr(config, "few_shot_enabled", False):
        return []
    if getattr(config, "few_shot_source", "passing") != "seed_db":
        return []
    try:
        from ai_strategy_loop.brain.exemplar_pool import select_exemplars  # noqa: PLC0415

        k = max(0, min(int(getattr(config, "few_shot_k", 3) or 0), 5))
        if k <= 0:
            return []
        cards = []
        for kind in ("buy", "sell"):
            examples = select_exemplars(
                kind=kind,
                timeframe=getattr(config, "bt_timeframe", "min"),
                k=k,
                source="seed_db",
            )
            cards.extend(_condition_pattern_cards_from_examples(kind, examples))
        return cards
    except Exception as exc:  # noqa: BLE001 - page-data helper must not block loop.
        logger.info("pattern card page_data build 실패(무시): %s", exc)
        return []
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
                   freeze_buy: bool = False,
                   prev_judged_hypotheses: Optional[list] = None,
                   segment_avoid_lines: Optional[list] = None,
                   state: Optional[LoopState] = None) -> Dict[str, Any]:
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
        prev_judged_hypotheses: 직전 세대에서 판정된(judged) 가정 목록(P2b-1). 주어지면
            side별 환류 문자열(format_hypothesis_feedback)을 만들어 buy/sell 생성 프롬프트에
            주입한다 — 특히 **기각** 가정을 강조해 빗나간 방향 반복을 막는다. 호출부는
            토글 ON일 때만 이 인자를 채운다(OFF면 None이라 미주입=byte-identical). None이면
            generate_strategy에 hypothesis_feedback=None이 가 byte-동일하다(하위호환).
        segment_avoid_lines: 직전/best 세대 세그먼트 분석에서 추출한 '패배 구간' avoid 라인
            리스트(T4 반복 정제 폐루프). 주어지면 매수(buy) generate_strategy로 전달돼 매수
            프롬프트에 avoid 가이드로 주입된다(build_messages가 kind=='buy'일 때만 반영 —
            매도 무영향). 호출부가 토글(segment_feedback_enabled) ON일 때만 채운다. None/빈
            리스트면 generate_strategy에 None이 가 byte-동일하다(하위호환).
        state: 프롬프트 영속화(P1c)용 LoopState. config.prompt_logging_enabled가
            True이고 state가 주어졌을 때만, 각 generate_strategy 호출에 on_prompt
            콜백을 연결해 LLM 호출별 프롬프트를 prompts 테이블에 기록한다. None이거나
            토글 OFF면 콜백을 만들지 않아 생성 경로가 byte-identical 하다(하위호환).

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

    # 프롬프트 영속화(P1c) — 토글 ON + state 보유 시에만 콜백을 만든다. OFF/state=None이면
    #   on_prompt=None으로 두어 generate_strategy 동작이 byte-identical 하다(하위호환).
    #   콜백은 generator가 넘긴 레코드 dict를 state.record_prompt 인자로 매핑한다.
    on_prompt = None
    if getattr(config, "prompt_logging_enabled", False) and state is not None:
        def on_prompt(rec):
            u = rec.get("usage") or {}
            state.record_prompt(
                run_id, gen_no, rec["kind"], rec["attempt"],
                system_text=rec.get("system_text", ""),
                user_text=rec.get("user_text", ""),
                injected_features=rec.get("injected_features"),
                prior_error=rec.get("prior_error"),
                model=rec.get("model"),
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                total_tokens=u.get("total_tokens", 0),
                response_text=rec.get("response_text", ""),
            )

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
        # P2b-1 가정 환류: 직전 세대 판정 가정을 side별 환류 문자열로 만들어 주입한다.
        #   prev_judged_hypotheses는 호출부가 토글 ON일 때만 채운다(OFF면 None →
        #   hypothesis_feedback=None → byte-identical). 산출 실패는 흡수(학습 보조 경로).
        hyp_feedback: Optional[str] = None
        if prev_judged_hypotheses:
            try:
                from ai_strategy_loop.autopsy import format_hypothesis_feedback  # noqa: PLC0415

                hyp_feedback = format_hypothesis_feedback(prev_judged_hypotheses, kind) or None
            except Exception as exc:  # noqa: BLE001 - 환류 산출 실패는 루프를 막지 않음.
                logger.info("가정 환류 산출 실패(무시): %s", exc)
                hyp_feedback = None
        # few-shot 우수 전략 샘플 주입(#67): 토글 ON일 때만 검증된 통과/인간 study 전략을
        #   K개 골라 생성 프롬프트에 주입한다(변수조합·필터 게이팅 구조 학습). select_exemplars는
        #   무예외(실패 시 빈 리스트)라 루프를 막지 않고, 빈 리스트면 build_messages가 미주입해
        #   동작이 byte-identical 하다(하위호환). OFF(기본)면 select_exemplars를 호출조차 안 한다.
        few_shot: Optional[list] = None
        pattern_cards: Optional[list] = None
        if getattr(config, "few_shot_enabled", False):
            from ai_strategy_loop.brain.exemplar_pool import select_exemplars  # noqa: PLC0415

            few_shot = select_exemplars(
                kind=kind,
                timeframe=config.bt_timeframe,
                k=getattr(config, "few_shot_k", 3),
                source=getattr(config, "few_shot_source", "passing"),
            ) or None
            if getattr(config, "few_shot_source", "passing") == "seed_db":
                pattern_cards = _condition_pattern_cards_from_examples(kind, few_shot)
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
            # 청산 효율 환류 — build_messages가 kind=='sell'일 때만 edge_ratio 부검 발견
            #   (손실 MAE가 승리 대비 ~2.6배 깊음·최고익 ~20%만 실현) 환류 블록을 매도
            #   프롬프트에 추가하므로 매수 경로엔 무영향. 기본 OFF면 byte-동일(하위호환).
            exit_edge_feedback_enabled=getattr(config, "exit_edge_feedback_enabled", False),
            # Phase C-3 시간 분산 넛지 — build_messages가 kind=='buy'일 때만 시초 분산
            #   가이드를 추가하므로 매도 경로엔 무영향. 기본 OFF면 프롬프트 byte-동일.
            encourage_time_dispersion=getattr(config, "encourage_time_dispersion", False),
            # 생성 품질 (A) 필터 범주 게이트 — generate_strategy는 kind=='buy'일 때만
            #   범주 수 검증+프롬프트 가이드를 적용하므로 매도 경로엔 무영향. 기본 OFF면
            #   동작 byte-동일(하위호환).
            require_filter_gates=getattr(config, "require_filter_gates", False),
            # T3 무의미한 시간창(no-op) 게이트 — generate_strategy는 kind=='buy'일 때만
            #   no-op(전범위=시간 무게이트)을 reject한다(좁은 창은 통과). 매도 경로엔 무영향.
            #   getattr 기본 False라 구버전 config도 무영향(byte-동일).
            require_meaningful_time_window=getattr(config, "require_meaningful_time_window", False),
            # 생성 분류축 유도(매수) — build_messages가 kind=='buy'일 때만 분류축 블록을
            #   추가하므로 매도 경로엔 무영향. getattr 기본 False라 구버전 config도 무영향.
            classification_generation_enabled=getattr(config, "classification_generation_enabled", False),
            time_cap_bucket_generation_enabled=getattr(config, "time_cap_bucket_generation_enabled", False),
            time_cap_bucket_end_time=getattr(config, "time_cap_bucket_end_time", 92000),
            sparse_positive_prompt_enabled=getattr(config, "sparse_positive_prompt_enabled", False),
            # 계산예산 지침/가드(2026-06-10 원인3) — 프롬프트 지침은 buy/sell 분기 지침을
            #   build_messages가 kind별로 적용하고, PRE-SAVE 가드는 generate_strategy가
            #   kind=='sell'일 때만 적용한다. getattr 기본 False/8이라 구버전 config도
            #   무영향(byte-동일, 하위호환).
            exec_budget_prompt_enabled=getattr(config, "exec_budget_prompt_enabled", False),
            sell_exec_budget_guard_enabled=getattr(config, "sell_exec_budget_guard_enabled", False),
            sell_max_window_calls=getattr(config, "sell_max_window_calls", 8),
            pattern_cards=pattern_cards,
            # v5.0 리포트 원리 어휘 주입 — build_messages가 kind별 어휘 블록을 추가한다.
            #   getattr 기본 False라 구버전 config도 무영향(byte-동일, 하위호환).
            report_principles_enabled=getattr(config, "report_principles_enabled", False),
            min_filter_categories=getattr(config, "min_filter_categories", 5),
            # P2b-1 가정 환류 — prev_judged_hypotheses가 없으면(토글 OFF/직전 미판정)
            #   None이라 build_messages가 미주입해 동작 byte-identical(하위호환).
            hypothesis_feedback=hyp_feedback,
            # few-shot 우수 전략 샘플(#67) — few_shot_enabled OFF(기본)면 위에서 None이라
            #   build_messages가 미주입해 동작 byte-identical(하위호환).
            few_shot_examples=few_shot,
            # T4 반복 정제 폐루프 — 직전/best 세대 패배 구간 avoid 라인. build_messages가
            #   kind=='buy'일 때만 반영하므로 매도 경로엔 무영향. 매수에만 전달해 sell
            #   호출 시그니처를 byte-identical 보존한다. 토글 OFF면 호출부가 None을 넘겨
            #   build_messages가 미주입(byte-동일).
            segment_avoid_lines=(segment_avoid_lines if kind == "buy" else None),
            # 프롬프트 영속화(P1c) — 토글 OFF/state=None이면 None이라 무영향(byte-identical).
            #   buy/sell 두 호출 모두 같은 콜백을 받는다(kind는 레코드에 담긴다).
            on_prompt=on_prompt,
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

# #64 — 이산 단계 인덱스(0~4) → step_timings 키(안정적 단계명). 단계가 끝날 때 그 단계의
#   경과초를 이 키로 step_timings에 기록한다(프론트 완료 배지가 같은 키로 조회). 인덱스를
#   직접 쓰지 않고 이름을 쓰는 이유: 프론트 FLOW_STEPS 배지가 사람이 읽는 이름으로 매핑하기 쉽고,
#   reframe/GA 등 phase 베이스가 달라도 동일 단계명으로 안정되게 누적되기 때문이다.
_STEP_NAME_BY_INDEX: Dict[int, str] = {
    0: "generate",
    1: "backtest",
    2: "score",
    3: "autopsy",
    4: "iterate",
}


def _phase_step_name(phase: str) -> Optional[str]:
    """phase 문자열 → step_timings 키(이산 단계명). 매핑 외(complete/stopping/-1)는 None.

    순수 함수(테스트 가능). _PHASE_STEP로 이산 인덱스를 얻고 _STEP_NAME_BY_INDEX로
    이름을 돌려준다. 활성 단계가 아닌 phase(-1: complete/stopping/미지정)는 None이라
    호출부가 단계 경과초를 기록하지 않는다(완료/정지는 단계 타이밍 없음).
    """
    idx = _PHASE_STEP.get(phase, -1)
    if idx < 0:
        return None
    return _STEP_NAME_BY_INDEX.get(idx)


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
    _timing: Optional[Dict[str, Any]] = None,
    _telemetry_buf: Optional[TelemetryRing] = None,
) -> None:
    """현재 루프 진행 상태를 contract.LoopState로 만들어 current_state.json에 발행.

    DB(generations)에서 세대 행을 읽어 to_loop_state로 빌드한다. 발행 실패는
    publish_loop_state 내부에서 흡수되므로 루프를 막지 않는다. DB 조회 자체가
    실패해도(닫힌 DB 등) 라이브 가시화 보조이므로 조용히 건너뛴다.

    page_data는 contract v2 패스스루(후속 페이지가 자기 데이터를 실어보냄). None이면
    빈 dict로 발행돼 기존 호출부(page_data 무인자)는 v1과 동일하게 동작한다(하위호환).

    _log_buf는 run_loop이 생성한 run-scoped deque(maxlen=50). None이면(GA/테스트) 빈 로그.

    #64 — _timing은 run_loop이 소유하는 mutable 진행시간 컨텍스트 dict(키: phase_t0,
    gen_t0, timings). None이면(GA/테스트) 진행시간 미발행(phase_started_at/gen_started_at=0.0,
    step_timings={})이라 프론트가 경과 표시를 생략한다(하위호환·byte-동일 발행). 이 함수가
    phase 경계 타이밍을 한 곳에서 관리한다:
      - *_start/loop_start/warm_prepare_start/ga_*: 그 단계의 phase_t0를 now로 리셋.
      - generate_start: 세대 시작이므로 gen_t0도 now로 리셋(세대 경과 기준).
      - *_done/*_end: 그 단계의 경과초(now - phase_t0)를 step_timings[단계명]에 누적.
    이 발행 필드는 LIVE 관찰용이며 graded/하드게이트/DB 영속에 무관하다(엔진/compute_fitness
    무수정). time.time() 사용은 런타임 코드라 허용(결정론 테스트는 monkeypatch).
    """
    # 로그 버퍼에 이 이벤트 한 줄을 추가한다(버퍼가 없으면 조용히 건너뜀).
    if _log_buf is not None and phase:
        _log_buf.append(f"[{phase}] {message}" if message else f"[{phase}]")
    telemetry_events: List[Dict[str, Any]] = []
    if _telemetry_buf is None and isinstance(_timing, dict):
        candidate = _timing.get("telemetry_buf")
        if isinstance(candidate, TelemetryRing):
            _telemetry_buf = candidate
    if _telemetry_buf is not None and phase:
        event_type = event_type_for_stage(phase, status=status)
        if event_type is not None:
            try:
                event = _telemetry_buf.append(
                    event_type,
                    run_id=rid,
                    gen_no=current_gen,
                    seed="",
                    stage=phase,
                    message=message,
                    source="ai_evolution_loop",
                    trace_id=f"{rid}:{current_gen}:{phase}",
                )
                if _log_buf is not None:
                    _log_buf.append(telemetry_log_line(event))
            except ValueError:
                pass
        telemetry_events = _telemetry_buf.snapshot()

    # #64 — phase 경계 진행시간 갱신(컨텍스트가 있을 때만). 발행 보조 경로라 실패해도
    #   루프를 막지 않으므로 try로 감싼다(시계 이상/타입 오류 흡수).
    phase_started_at = 0.0
    gen_started_at = 0.0
    step_timings: Dict[str, float] = {}
    if _timing is not None:
        try:
            now = time.time()
            step_name = _phase_step_name(phase)
            is_start = phase.endswith("_start") or phase in ("loop_start", "ga_init")
            is_end = phase.endswith("_done") or phase.endswith("_end")
            # 세대 시작(generate_start/ga_init)이면 세대 경과 기준 시각도 리셋한다.
            if phase in ("generate_start", "ga_init"):
                _timing["gen_t0"] = now
            # 활성 단계 *_start류면 그 단계 시작 시각을 리셋한다(미지정 phase는 건드리지 않음).
            if is_start and step_name is not None:
                _timing["phase_t0"] = now
            # *_done/*_end면 그 단계의 경과초를 누적 기록(phase_t0가 잡혀 있을 때만).
            if is_end and step_name is not None:
                p0 = float(_timing.get("phase_t0", 0.0) or 0.0)
                if p0 > 0.0:
                    _timing.setdefault("timings", {})[step_name] = max(0.0, now - p0)
            phase_started_at = float(_timing.get("phase_t0", 0.0) or 0.0)
            gen_started_at = float(_timing.get("gen_t0", 0.0) or 0.0)
            step_timings = dict(_timing.get("timings", {}) or {})
        except Exception:  # noqa: BLE001 - 진행시간은 가시화 보조, 발행을 막지 않는다.
            phase_started_at = 0.0
            gen_started_at = 0.0
            step_timings = {}

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
    page_data_payload = dict(page_data or {})
    # Condition-discovery governance is sticky across phase publishes. Without this,
    # generation_done can show policy/score/evidence and the next phase publish can erase it
    # by omitting page_data. Keep the projection additive and failure-safe. Also repair
    # partial caller-supplied governance payloads so condition_discovery cannot suppress
    # the advisory score or feedback sections.
    condition_section_keys = ("condition_discovery", "advisory_scores", "condition_feedback")
    if any(key not in page_data_payload for key in condition_section_keys):
        try:
            page_data_payload = _build_condition_discovery_page_sections(st, rid, config, page_data_payload)
        except Exception as exc:  # noqa: BLE001 - dashboard projection must fail closed.
            reason = str(exc)
            logger.info("condition discovery page_data publish 실패(상태 발행): %s", reason)
            page_data_payload.setdefault("condition_discovery", {
                "schema_version": 1,
                "status": "error",
                "reason": reason,
                "authority": "condition_discovery_projection_failed_no_promotion_authority",
            })
            page_data_payload.setdefault("advisory_scores", {
                "schema_version": 1,
                "status": "error",
                "reason": reason,
                "authority_guard": {
                    "score_can_promote": False,
                    "score_can_export": False,
                    "score_can_select_winner": False,
                },
            })
            page_data_payload.setdefault("condition_feedback", {
                "schema_version": 1,
                "status": "error",
                "reason": reason,
                "pattern_cards": {"status": "unavailable", "items": []},
            })
    current_step = _PHASE_STEP.get(phase, -1)
    snapshot = to_loop_state(
        summary, gens, config=config, status=status, current_gen=current_gen,
        latest={
            "phase": phase,
            "last_checkpoint": last_checkpoint,
            "message": message,
            "recent_logs": list(_log_buf) if _log_buf is not None else [],
            "current_step": current_step,
            # #64 — LIVE 진행시간 발행필드. 단계/세대 시작 epoch + 단계별 누적 소요초.
            #   기본 0.0/빈 dict면 프론트가 경과 표시를 생략한다(구 상태/미발행 안전).
            "phase_started_at": phase_started_at,
            "gen_started_at": gen_started_at,
            "step_timings": dict(step_timings or {}),
            "telemetry_events": telemetry_events,
        },
        cumulative_tokens=cumulative_tokens,
        page_data=page_data_payload,
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
    from ai_strategy_loop.controller.condition_discovery import effective_condition_discovery_runtime_config  # noqa: PLC0415

    config = effective_condition_discovery_runtime_config(config)
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
    # T4 반복 정제 폐루프: 직전 세대 백테 세그먼트 분석에서 추출한 '패배 구간' avoid
    #   라인. 다음 세대 매수 프롬프트로 환류해 불필요 구간을 줄이며 재생성하게 한다.
    #   토글(segment_feedback_enabled) OFF면 항상 None이라 산출·주입이 전혀 안 일어난다
    #   (byte-동일). 백테 실패 세대(CSV 없음)는 None으로 비워 오래된 가이드를 안 남긴다.
    next_segment_avoid_lines: Optional[list] = None
    # P2a 가정 루프: 직전 세대 피드백이 '이 다음 세대'를 겨냥해 세운 가정 목록.
    #   다음 세대에서 그 세대의 부모 대비 델타로 채택/기각해 hypotheses_json으로 영속한다.
    #   토글 OFF면 항상 None이라 가정 방출·판정·저장이 전혀 안 일어난다(byte-동일).
    next_hypotheses: Optional[list] = None
    # P2b-1 가정 환류: 직전 세대에서 판정된(judged) 가정 목록. 이번 세대 생성
    #   프롬프트로 환류해(format_hypothesis_feedback) "빗나간 방향 반복 금지"를 알린다.
    #   1세대 지연은 본질적(G용 가정은 G 자신이 판정하므로 G 생성 시점엔 미판정) — 가장
    #   최근 judged를 쓴다. 토글 OFF면 항상 None이라 환류가 안 일어난다(byte-동일).
    prev_judged_hypotheses: Optional[list] = None
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
    # #64 — run-scoped 진행시간 컨텍스트(_publish_live가 phase 경계에서 갱신·발행).
    #   phase_t0=현재 단계 시작 epoch, gen_t0=현재 세대 시작 epoch, timings={단계명: 소요초}.
    #   run마다 새로 생성해 세션 간 누수를 막는다(_live_log_buf와 동형). 발행 보조라 graded/DB 무관.
    _timing: Dict[str, Any] = {
        "phase_t0": 0.0,
        "gen_t0": 0.0,
        "timings": {},
        "telemetry_buf": TelemetryRing(),
    }

    # warm 엔진 모드: 전체유니버스 엔진/데이터를 1회 prepare하고 세대마다 run()만 호출한다.
    #   prepare 실패(데이터 부재 등)는 cold(run_backtest_for) 경로로 자동 폴백한다.
    #   cold 모드면 warm_session은 None으로 두어 기존 subprocess 경로를 그대로 탄다.
    #   (cumulative_tokens 등 상태 변수 초기화 뒤에 둔다 — _publish_live가 참조.)
    warm_session = None
    warm_prepare_result = None
    if getattr(config, "bt_engine_mode", "warm") == "warm":
        _publish_live(st, rid, config, status="running", current_gen=start_gen,
                      cumulative_tokens=cumulative_tokens, phase="warm_prepare_start",
                      message="warm session prepare 시작 (전체유니버스 엔진/데이터 로딩)",
                      _log_buf=_live_log_buf, _timing=_timing)
        warm_session = WarmBacktestSession(_build_warm_btconfig(config))
        prep = warm_session.prepare()
        warm_prepare_result = prep
        if prep.get("status") != "ok":
            print(f"[LOOP] warm prepare 실패 → cold 폴백: {prep.get('message')}", flush=True)
            warm_session = None
        else:
            back_count = prep.get("back_count")
            print(f"[LOOP] warm prepare 완료 (back_count={back_count})", flush=True)
            _publish_live(st, rid, config, status="running", current_gen=start_gen,
                          cumulative_tokens=cumulative_tokens, phase="warm_prepare_done",
                          message=f"warm session 준비 완료 (back_count={back_count})",
                          page_data=_warm_session_page_data(prepare=prep),
                          _log_buf=_live_log_buf, _timing=_timing)

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
                  _log_buf=_live_log_buf, _timing=_timing)

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
                              _log_buf=_live_log_buf, _timing=_timing)
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
                          _log_buf=_live_log_buf, _timing=_timing)
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
                # P2b-1 가정 환류: 토글 ON일 때만 직전 세대 판정 가정(prev_judged_hypotheses)을
                #   _generate_pair로 넘겨 side별 환류 문자열을 생성 프롬프트에 주입한다.
                #   OFF(기본)면 키를 넣지 않아 _generate_pair 호출 시그니처가 기존과
                #   byte-identical 하다(P1c state 배선과 동일 — monkeypatch 테스트 보호).
                if (getattr(config, "hypothesis_tracking_enabled", False)
                        and prev_judged_hypotheses):
                    gen_kwargs["prev_judged_hypotheses"] = prev_judged_hypotheses
                # T4 반복 정제 폐루프: 토글 ON + 직전 세대에서 패배 구간 avoid 라인을
                #   확보했을 때만 _generate_pair로 넘겨 매수 프롬프트에 환류한다. OFF(기본)
                #   거나 라인이 비면 키를 넣지 않아 _generate_pair 호출 시그니처가 기존과
                #   byte-identical 하다(다른 토글 배선과 동일 — monkeypatch 테스트 보호).
                if (getattr(config, "segment_feedback_enabled", False)
                        and next_segment_avoid_lines):
                    gen_kwargs["segment_avoid_lines"] = next_segment_avoid_lines
                # 프롬프트 영속화(P1c): 토글 ON일 때만 state를 _generate_pair로 넘겨
                #   프롬프트 로깅 콜백을 활성화한다. OFF(기본)면 state 키를 넣지 않아
                #   _generate_pair 호출 시그니처가 기존과 byte-identical 하다(하위호환).
                if getattr(config, "prompt_logging_enabled", False):
                    gen_kwargs["state"] = st
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
                              _log_buf=_live_log_buf, _timing=_timing)
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
                          _log_buf=_live_log_buf, _timing=_timing)
            t0 = time.time()
            try:
                if warm_session is not None:
                    # warm: 살아있는 엔진에 전략만 바꿔 백테 1회 (세대당 ~60초).
                    #   per-run fail-fast 타임아웃(bt_warm_run_timeout=120)을 전달한다.
                    #   over-firing 전략은 120초에 컷되고 리셋+재로딩 후 다음 run으로 넘어간다.
                    #   이 인자는 BackTest join에만 쓰이며, 데이터로딩(BacktestConfig.timeout)은
                    #   _build_warm_btconfig에서 별도로 높게 유지되므로 재로딩이 잘리지 않는다.
                    warm_run_result = warm_session.run(
                        buy_name, sell_name, timeout=config.bt_warm_run_timeout
                    )
                    outcome = _warm_to_outcome(warm_run_result)
                else:
                    # cold: 세대마다 stom_backtest.py 서브프로세스 (폴백/기존 경로).
                    outcome = run_backtest_for(config, buy_name, sell_name)
                    warm_run_result = None
            except Exception as exc:  # noqa: BLE001 - 어떤 예외든 흡수, 루프 유지.
                outcome = BacktestOutcome(
                    False, "error", None, None, f"backtest raised: {exc}"
                )
                warm_run_result = None
            bt_elapsed = time.time() - t0
            # US-007 — 백테스트 종료 라이브 발행.
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="backtest_end",
                          message=f"backtest end gen {gen_no} status={outcome.status}",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          page_data=_warm_session_page_data(
                              prepare=warm_prepare_result, last_run=warm_run_result
                          ),
                          _log_buf=_live_log_buf, _timing=_timing)
            print(f"[LOOP] backtest status={outcome.status} "
                  f"elapsed={bt_elapsed:.1f}s reason={outcome.reason}", flush=True)

            if not outcome.ok:
                # 실패 세대: score=0, 계속. 단, '왜' 실패했는지를 구체적으로 분류해
                #   다음 세대 피드백 + 이력에 남긴다(맹목 변이 차단).
                err_history_line = _backtest_error_history_line(outcome.reason)
                # D3(2026-06-10): error 행 reason에 경과시간을 병기해 대시보드에서
                #   타임아웃(계산예산) 문제를 즉시 식별하게 한다. error 행은 선택기에서
                #   status!='ok'로 이미 제외되므로 reason 장식이 버킷 판정을 깨지 않는다
                #   (ok 행의 reason 원문 보존 계약과 구분 — tests/unit/test_record_reason_contract.py).
                st.record_generation(
                    rid, gen_no,
                    buy_name=buy_name, sell_name=sell_name,
                    status="error", score=0.0, gate_passed=False,
                    reason=f"backtest failed/timeout: {outcome.reason} (elapsed {bt_elapsed:.0f}s)",
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
                # P2a — 실패 세대(0거래/크래시)는 게이트 분석할 metrics가 없어 가정을
                #   세우지 않는다. carry를 비워 다음 세대가 빈/오래된 가정을 판정하지
                #   않게 한다(토글 OFF면 어차피 항상 None).
                next_hypotheses = None
                # T4 — 실패 세대는 CSV가 없어 세그먼트 분석이 불가하다. avoid 가이드를
                #   비워 다음 세대가 오래된 패배 구간 가이드를 환류받지 않게 한다(토글
                #   OFF면 어차피 항상 None).
                next_segment_avoid_lines = None
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
                          _log_buf=_live_log_buf, _timing=_timing)
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
            # P3 계보 + P1b 숫자 델타: 부모(parent_gen) 행을 1회 읽어 변경 요약(NL,
            #   diff_from_parent)과 숫자 델타(d_graded..d_uptrend_r2)를 함께 만든다.
            #   NL은 기존 포맷과 byte-identical, 숫자 델타는 SQL 집계(AVG/ORDER BY)용이다.
            #   코드 전문은 복제 저장하지 않는다(lineage.diff_generations가 namespaced 재조회).
            diff_from_parent, parent_deltas = _build_parent_diff_and_deltas(
                st, rid, parent_gen_for_record,
                graded=graded.graded, mdd=graded.mdd, trade_count=fit.trade_count,
                profit=graded.total_profit, daily_avg_trades=fit.daily_avg_trades,
                calmar=fit.calmar, uptrend_r2=fit.uptrend_r2,
            )
            _pd = parent_deltas or {}
            # P2a 가정 판정·영속: 토글 ON이고 직전 세대가 '이 세대용'으로 세운 가정
            #   (next_hypotheses)이 있으면, 이 세대의 부모 대비 델타(parent_deltas)로
            #   채택/기각해 hypotheses_json으로 직렬화한다(추가 백테 없음). 부모 없는 세대
            #   (parent_deltas None)는 adjudicate가 전부 inconclusive로 매기되, 가정이
            #   없으면 None=NULL이라 기존과 동일하다. 산출 실패는 흡수(학습 보조 경로).
            #   토글 OFF면 next_hypotheses가 항상 None이라 hypotheses_json=None(byte-동일).
            #   P2b-1: judged 리스트를 prev_judged_hypotheses에 보관해 다음 세대 생성
            #   프롬프트로 환류한다(format_hypothesis_feedback). 토글 OFF면 (None, None).
            hypotheses_json, prev_judged_hypotheses = _adjudicate_and_serialize(
                config, next_hypotheses, parent_deltas
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
                # P1b — 부모 대비 숫자 델타(부모 없으면 _pd가 빈 dict → None=NULL).
                d_graded=_pd.get("d_graded"),
                d_mdd=_pd.get("d_mdd"),
                d_trades=_pd.get("d_trades"),
                d_profit=_pd.get("d_profit"),
                d_daily_trades=_pd.get("d_daily_trades"),
                d_calmar=_pd.get("d_calmar"),
                d_uptrend_r2=_pd.get("d_uptrend_r2"),
                # P2a — 직전 가정+이 세대 델타로 매긴 판정(토글 OFF면 None=NULL).
                hypotheses_json=hypotheses_json,
            )
            # O2 — 백테 시계열(누적수익곡선·일별손익·낙폭) 영속화. 토글 ON이고 결과
            #   CSV가 있을 때만, 이미 디스크에 있는 CSV를 파싱(추가 백테 0회)해
            #   equity_points에 다운샘플 영속한다. **파싱은 여기서(호출부) 하고 state엔
            #   파싱된 series만 넘긴다**(state가 fitness를 import하지 않도록 레이어 분리).
            #   토글 OFF면 전혀 호출하지 않아 동작이 byte-동일하다(하위호환). 파싱/영속
            #   실패는 흡수한다(학습 보조 경로 — 루프를 막지 않는다).
            if getattr(config, "equity_points_enabled", False) and outcome.csv_path:
                try:
                    from ai_strategy_loop.fitness.equity_series import parse_backtest_series  # noqa: PLC0415
                    eq_csv = (outcome.csv_path if os.path.isabs(outcome.csv_path)
                              else os.path.join(REPO_ROOT, outcome.csv_path))
                    eq_series = parse_backtest_series(
                        eq_csv, betting=getattr(config, "bt_betting", None)
                    )
                    st.record_equity_curve(rid, gen_no, eq_series)
                except Exception as eq_err:  # noqa: BLE001 - 시계열 영속 실패는 흡수.
                    print(f"[LOOP] equity_points 영속 실패(무시): {eq_err}", flush=True)
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
                          _log_buf=_live_log_buf, _timing=_timing)

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
                          _log_buf=_live_log_buf, _timing=_timing)
            next_autopsy_feedback, next_sell_feedback, last_autopsy_page_data = _build_feedback(
                config, outcome, fit, graded,
                effective_autopsy_fn, effective_exit_autopsy_fn,
                effective_segment_autopsy_fn,
            )
            # T4 반복 정제 폐루프: 토글 ON일 때만 이 세대의 결과 CSV에서 '패배 구간'
            #   avoid 라인을 산출해 다음 세대 매수 프롬프트로 환류한다. 산출은 순수·무예외
            #   (build_segment_avoid_lines가 데이터 없음/부족/읽기 실패를 빈 리스트로 흡수).
            #   OFF(기본)면 헬퍼를 호출조차 안 해 None을 유지(byte-동일). 실패는 흡수한다.
            next_segment_avoid_lines = _build_segment_avoid(config, outcome)
            # P2a 가정 방출: 부검 NL과 동일 인자(게이트 통과/MDD/손익/거래수)로 이 세대가
            #   '다음 세대용'으로 세우는 가정을 만든다. is_refine은 다음 세대가 부모를 갖는지
            #   (현재 best가 출발점이 되는지)로 본다. 토글 OFF면 None이라 가정이 carry되지
            #   않아 다음 세대 hypotheses_json=None(byte-동일). 산출 실패는 흡수한다.
            next_hypotheses = _build_next_hypotheses(config, fit, graded, is_refine=(best_gen >= 0))
            _publish_live(st, rid, config, status="running", current_gen=gen_no,
                          cumulative_tokens=cumulative_tokens, phase="autopsy_done",
                          message=f"gen {gen_no} 부검 완료",
                          best_gen=best_gen, best_score=best_score,
                          best_buy=best_buy, best_sell=best_sell,
                          winner_gen=winner_gen, winner_score=winner_score,
                          winner_buy=winner_buy, winner_sell=winner_sell,
                          _log_buf=_live_log_buf, _timing=_timing)

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
                          _log_buf=_live_log_buf, _timing=_timing)

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
                      _log_buf=_live_log_buf, _timing=_timing)
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


def _fetch_parent_row(
    st: LoopState,
    rid: str,
    parent_gen: Optional[int],
) -> Optional[Dict[str, Any]]:
    """부모(parent_gen) 세대 행을 DB에서 1회 조회한다(없으면 None).

    P3 NL diff와 P1b 숫자 델타가 같은 부모 행을 공유해 DB 읽기를 한 번으로 묶는다.
    parent_gen None/<0(루트 세대)이거나 조회 실패면 None을 돌려 호출부가 diff/델타를
    건너뛴다(루프를 막지 않음). get_generations는 행 전체(score/mdd/trade_count/profit/
    calmar/uptrend_r2/daily_avg_trades 포함)를 반환한다.
    """
    if parent_gen is None or parent_gen < 0:
        return None
    try:
        rows = {int(g.get("gen_no", -1)): g for g in st.get_generations(rid)}
    except Exception:  # noqa: BLE001 - 조회 실패는 diff 없이 진행(루프를 막지 않음).
        return None
    return rows.get(int(parent_gen))


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
    parent = _fetch_parent_row(st, rid, parent_gen)
    if parent is None:
        return None
    return _format_parent_diff_nl(parent, parent_gen, graded, mdd, trade_count, profit)


def _format_parent_diff_nl(
    parent: Dict[str, Any],
    parent_gen: Optional[int],
    graded: float,
    mdd: float,
    trade_count: int,
    profit: float,
) -> str:
    """부모 행 + 현재 지표로 NL diff 한 줄을 만든다(_build_parent_diff와 동일 포맷).

    포맷은 기존과 byte-identical이어야 한다(대시보드/메타가 의존). 분리한 이유는
    P1b 숫자 델타 함수가 같은 부모 행을 재사용하면서 NL도 한 번에 만들기 위해서다.
    """

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


def _build_parent_diff_and_deltas(
    st: LoopState,
    rid: str,
    parent_gen: Optional[int],
    *,
    graded: float,
    mdd: float,
    trade_count: int,
    profit: float,
    daily_avg_trades: float,
    calmar: float,
    uptrend_r2: float,
) -> Tuple[Optional[str], Optional[Dict[str, float]]]:
    """부모 행을 1회 조회해 NL diff(P3)와 숫자 델타(P1b)를 함께 만든다.

    부모가 없으면(루트 세대/조회 실패) (None, None). NL 문자열은 기존 포맷과
    byte-identical(_format_parent_diff_nl). 숫자 델타는 NL과 같은 값의 숫자형으로
    SQL 집계(AVG/ORDER BY)를 가능케 한다. graded는 부모 'score' 컬럼과 비교(NL과
    동일). 부모 값은 float(parent.get(키) or 0)로 안전 폴백한다.

    호출부는 NL diff와 7개 델타를 한 번의 DB 읽기로 얻는다(NL과 델타를 별도 함수로
    따로 부르면 get_generations가 두 번 실행되는 것을 회피).
    """
    parent = _fetch_parent_row(st, rid, parent_gen)
    if parent is None:
        return None, None
    nl = _format_parent_diff_nl(parent, parent_gen, graded, mdd, trade_count, profit)
    p_graded = float(parent.get("score", 0.0) or 0.0)
    p_mdd = float(parent.get("mdd", 0.0) or 0.0)
    p_trades = float(parent.get("trade_count", 0) or 0)
    p_profit = float(parent.get("profit", 0.0) or 0.0)
    p_daily = float(parent.get("daily_avg_trades", 0.0) or 0.0)
    p_calmar = float(parent.get("calmar", 0.0) or 0.0)
    p_uptrend = float(parent.get("uptrend_r2", 0.0) or 0.0)
    deltas = {
        "d_graded": graded - p_graded,
        "d_mdd": mdd - p_mdd,
        "d_trades": float(trade_count) - p_trades,
        "d_profit": profit - p_profit,
        "d_daily_trades": daily_avg_trades - p_daily,
        "d_calmar": calmar - p_calmar,
        "d_uptrend_r2": uptrend_r2 - p_uptrend,
    }
    return nl, deltas


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


def _latest_generation_row(st: LoopState, rid: str) -> Optional[Dict[str, Any]]:
    """Return latest generation row for dashboard-only page_data assembly."""

    try:
        rows = st.get_generations(rid)
    except Exception as exc:  # noqa: BLE001 - dashboard projection must not stop the loop.
        logger.info("condition discovery latest generation 조회 실패(무시): %s", exc)
        return None
    return dict(rows[-1]) if rows else None


def _count_prompt_records(st: LoopState, rid: str, gen_no: int) -> Optional[int]:
    try:
        return sum(1 for row in st.get_prompts(rid) if int(row.get("gen_no", -1)) == int(gen_no))
    except Exception as exc:  # noqa: BLE001 - status page evidence only.
        logger.info("condition discovery prompt count 조회 실패(무시): %s", exc)
        return None


def _count_equity_points(st: LoopState, rid: str, gen_no: int) -> Optional[int]:
    try:
        return len(st.get_equity_points(rid, gen_no))
    except Exception as exc:  # noqa: BLE001 - status page evidence only.
        logger.info("condition discovery equity count 조회 실패(무시): %s", exc)
        return None


def _evidence_status(present: bool, unavailable: bool = False) -> str:
    if unavailable:
        return "unavailable"
    return "present" if present else "missing"


def _condition_discovery_evidence(
    latest_gen: Optional[Dict[str, Any]],
    *,
    prompt_records: Optional[int],
    equity_points: Optional[int],
) -> Dict[str, str]:
    """Build CSV/trade/equity/prompt/validation evidence state from existing run records."""

    if latest_gen is None:
        return {
            "csv": "missing",
            "trades": "missing",
            "equity": "unavailable" if equity_points is None else "missing",
            "prompt": "unavailable" if prompt_records is None else "missing",
            "validation": "missing",
        }

    status = str(latest_gen.get("status", "") or "").strip().lower()
    trade_count = int(latest_gen.get("trade_count", 0) or 0)
    return {
        "csv": _evidence_status(bool(latest_gen.get("csv_path"))),
        "trades": _evidence_status(trade_count > 0),
        "equity": _evidence_status((equity_points or 0) > 0, unavailable=equity_points is None),
        "prompt": _evidence_status((prompt_records or 0) > 0, unavailable=prompt_records is None),
        "validation": "failed" if status in {"error", "failed"} else _evidence_status(bool(status)),
    }


def _quality_features_for_condition(latest_gen: Optional[Dict[str, Any]], config: LoopConfig) -> Dict[str, Any]:
    """Derive safe, prompt-quality score inputs without reading strategy bodies or DB truth."""

    if latest_gen is None:
        return {"syntax_valid": False, "forbidden_token_count": 1, "variable_categories": []}

    status = str(latest_gen.get("status", "") or "").strip().lower()
    gist = str(latest_gen.get("strategy_gist", "") or "")
    categories: List[str] = []
    category_markers = (
        ("time", ("시분초", "시간", "분봉", "tick")),
        ("liquidity", ("거래대금", "거래량", "체결금액")),
        ("orderflow", ("체결강도", "호가", "매수잔량", "매도잔량")),
        ("return", ("등락", "수익률", "변동률")),
        ("trend", ("이평", "이동평균", "추세", "돌파")),
    )
    for name, markers in category_markers:
        if any(marker in gist for marker in markers):
            categories.append(name)

    timeframe = str(getattr(config, "bt_timeframe", "") or "").lower()
    market_niche = "opening_tick_research" if timeframe == "tick" else "min_full_session_research"
    return {
        "syntax_valid": status not in {"error", "failed"},
        "forbidden_token_count": 0 if status not in {"error", "failed"} else 1,
        "variable_categories": categories,
        "composition_patterns": [],
        "market_niche": market_niche,
        "always_true_flags": [],
        "execution_cost_risk": "low",
        "window_call_count": 0,
        "max_window_calls": getattr(config, "sell_max_window_calls", 8),
        "exit_structure": {},
    }


def _build_condition_discovery_page_sections(
    st: LoopState,
    rid: str,
    config: LoopConfig,
    page_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Attach condition-discovery sections to LIVE page_data."""

    from ai_strategy_loop.controller.advisory_scores import build_advisory_score_payload  # noqa: PLC0415
    from ai_strategy_loop.controller.condition_discovery import merge_condition_discovery_page_data, normalize_condition_discovery_preset  # noqa: PLC0415
    from ai_strategy_loop.controller.condition_discovery_feedback import build_feedback_page_data  # noqa: PLC0415

    latest_gen = _latest_generation_row(st, rid)
    gen_no = int(latest_gen.get("gen_no", -1) if latest_gen else -1)
    prompt_records = _count_prompt_records(st, rid, gen_no) if gen_no >= 0 else 0
    equity_points = _count_equity_points(st, rid, gen_no) if gen_no >= 0 else 0
    evidence = _condition_discovery_evidence(
        latest_gen,
        prompt_records=prompt_records,
        equity_points=equity_points,
    )
    merged = merge_condition_discovery_page_data(page_data, config, evidence=evidence)
    preset = normalize_condition_discovery_preset(getattr(config, "condition_discovery_preset", "fast"))

    metrics = dict(latest_gen or {})
    metrics["total_profit"] = metrics.get("profit")
    metrics["mdd_pct"] = metrics.get("mdd")
    metrics["total_profit_pct"] = metrics.get("total_profit_pct")
    hard_gate_passed = bool(latest_gen.get("gate_passed")) if latest_gen else False
    mdd_cap = float(merged["condition_discovery"]["hard_gates"]["mdd"]["cap"])
    min_daily_trades = float(merged["condition_discovery"]["hard_gates"]["minimum_daily_trades"]["value"])
    merged["advisory_scores"] = build_advisory_score_payload(
        metrics=metrics,
        quality_features=_quality_features_for_condition(latest_gen, config),
        evidence=evidence,
        preset=preset,
        hard_gate_passed=hard_gate_passed,
        human_approved=False,
        mdd_cap=mdd_cap,
        min_daily_trades=min_daily_trades,
    )

    hypotheses = []
    if latest_gen and latest_gen.get("hypotheses_json"):
        try:
            parsed = json.loads(str(latest_gen.get("hypotheses_json")))
            if isinstance(parsed, list):
                hypotheses = parsed
        except (TypeError, ValueError):
            hypotheses = []
    pattern_cards = _condition_pattern_cards_for_config(config)
    merged["condition_feedback"] = build_feedback_page_data(
        config,
        prompt_records=prompt_records,
        equity_points=equity_points,
        hypotheses=hypotheses,
        pattern_cards=pattern_cards,
    )
    merged["condition_feedback"]["source"] = "live_loop_page_data"
    return merged


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


def _build_segment_avoid(config, outcome) -> Optional[list]:
    """T4 반복 정제 폐루프 — 이 세대 결과 CSV에서 '패배 구간' avoid 라인을 산출한다(토글 ON일 때만).

    build_segment_avoid_lines(순수·무예외)를 호출해 결과 CSV를 시간대×시총×등락률×교차
    셀로 쪼개고, 패배 셀(표본 충분 + 적자/저승률)을 매수 프롬프트용 한국어 avoid 라인으로
    만든다. 다음 세대 매수 프롬프트로 환류해 루프가 불필요 구간을 줄이며 재생성하게 한다.

    토글(segment_feedback_enabled) OFF면 헬퍼를 호출조차 안 해 None을 돌린다(byte-동일).
    CSV 없음/데이터 부족/읽기 실패는 빈 리스트로 흡수되며, 빈 리스트는 None으로 정규화해
    호출부가 gen_kwargs에 키를 넣지 않게 한다(byte-identical). 산출 실패도 흡수한다.

    fine_time은 세그먼트 부검(_default_segment_autopsy_fn)과 동일하게 segment_fine_time
    토글을 따른다(시간축 정합). min_count는 config.segment_feedback_min_count.

    반환: List[str](패배 구간 avoid 라인) 또는 None(토글 OFF/CSV 없음/빈 결과/실패).
    """
    if not getattr(config, "segment_feedback_enabled", False):
        return None
    csv_path = getattr(outcome, "csv_path", None)
    if not csv_path:
        return None
    try:
        from ai_strategy_loop.brain.segment_feedback import (  # noqa: PLC0415
            build_segment_avoid_lines,
        )

        abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
        lines = build_segment_avoid_lines(
            abs_csv,
            min_count=int(getattr(config, "segment_feedback_min_count", 8) or 8),
            fine_time=bool(getattr(config, "segment_fine_time", False)),
        )
        return lines or None
    except Exception as exc:  # noqa: BLE001 - 환류 산출 실패는 루프를 막지 않음(학습 보조 경로).
        logger.info("세그먼트 avoid 환류 산출 실패(무시): %s", exc)
        return None


# =====================================================================
# 가정(Hypothesis) 루프 코어 (P2a) — 방출(emit) + 판정·직렬화(adjudicate).
#   _build_feedback의 NL 반환은 절대 건드리지 않고(byte-동일), 가정은 별도 경로로
#   다룬다. 두 함수 모두 토글 OFF면 즉시 None을 돌려 기존 동작과 완전히 동일하다.
# =====================================================================
def _build_next_hypotheses(config, fit, graded, *, is_refine: bool):
    """이 세대 결과로 '다음 세대용' 가정 목록을 세운다(토글 ON일 때만).

    gate_failure_directive(부검 NL)와 동일 인자(gate_passed/mdd/mdd_cap/total_profit/
    trade_count/min_trades)로 build_hypotheses를 호출해, 부검 NL과 가정이 항상 같은
    원인에서 출발하게 한다. 토글 OFF면 None을 돌려 carry가 비어 다음 세대
    hypotheses_json=None(byte-동일). 산출 실패는 흡수한다(학습 보조 경로).

    반환: List[Hypothesis] 또는 None(토글 OFF/빈 목록/실패).
    """
    if not getattr(config, "hypothesis_tracking_enabled", False):
        return None
    try:
        from ai_strategy_loop.autopsy import build_hypotheses  # noqa: PLC0415

        hyps = build_hypotheses(
            gate_passed=fit.gate_passed,
            mdd=graded.mdd,
            mdd_cap=float(getattr(config, "mdd_cap", 0.0) or 0.0),
            total_profit=graded.total_profit,
            trade_count=fit.trade_count,
            min_trades=int(getattr(config, "min_trades", 0) or 0),
            is_refine=is_refine,
        )
        return hyps or None
    except Exception as exc:  # noqa: BLE001 - 가정 산출 실패는 루프를 막지 않음.
        logger.info("가정 산출 실패(무시): %s", exc)
        return None


def _adjudicate_and_serialize(config, next_hypotheses, parent_deltas):
    """직전 세대가 세운 가정을 이 세대의 부모 대비 델타로 채택/기각해 JSON+판정목록으로 만든다.

    토글 OFF거나 가정이 없으면(부모 없는 세대/실패 세대) (None, None)을 돌려
    hypotheses_json=NULL(byte-동일). parent_deltas는 _build_parent_diff_and_deltas가
    만든 dict(없으면 None) — adjudicate가 None을 받으면 전부 inconclusive로 매긴다
    (추가 백테 없음). 판정/직렬화 실패는 흡수한다(학습 보조 경로).

    P2b-1: judged 리스트도 함께 돌려준다 — 호출부가 prev_judged_hypotheses에 보관해
    다음 세대 생성 프롬프트로 환류(format_hypothesis_feedback)한다. JSON 문자열은
    record_generation 영속용(기존), judged 리스트는 프롬프트 환류용이다.

    반환: (json_str 또는 None, judged 리스트 또는 None).
    """
    if not getattr(config, "hypothesis_tracking_enabled", False):
        return None, None
    if not next_hypotheses:
        return None, None
    try:
        from ai_strategy_loop.autopsy import adjudicate  # noqa: PLC0415

        judged = adjudicate(next_hypotheses, parent_deltas)
        if not judged:
            return None, None
        json_str = json.dumps([h.to_dict() for h in judged], ensure_ascii=False)
        return json_str, judged
    except Exception as exc:  # noqa: BLE001 - 가정 판정/직렬화 실패는 루프를 막지 않음.
        logger.info("가정 판정/직렬화 실패(무시): %s", exc)
        return None, None


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
    from ai_strategy_loop.controller.condition_discovery import effective_condition_discovery_runtime_config  # noqa: PLC0415

    config = effective_condition_discovery_runtime_config(config)
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
