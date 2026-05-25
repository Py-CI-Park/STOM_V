"""US-003 E2E smoke — BOUNDED 단일 종목 백테스트로 전체 파이프라인 증명.

배경:
  이전 시도는 풀 유니버스(1379 종목) 백테스트를 돌려 ~1시간 타임아웃이
  났다. 엔진은 정상이고 풀 유니버스가 느릴 뿐이다. 그래서 이 스크립트는
  LoopConfig의 BOUNDED 스코프(`bt_scope='single_stock'`)를 사용해
  '한종목 로딩' 분봉 백테스트 1회를 수초~저분 단위로 끝낸다.

흐름 (모두 `if __name__ == '__main__':` 가드 아래 — Windows spawn 안전):
  1) bootstrap 먼저 import (env-before-import 격리; 루프 DB 선택) +
     ensure_loop_db_engine_compat() 로 formula 빈 테이블 보장 (데드락 근본원인 #1).
  2) 이미 저장된 AILOOP_min_buy / AILOOP_min_sell 사용 (없으면 실 provider로
     timeframe='min' 1 buy + 1 sell 재생성 — 변수 스코프 가드로 NameError-데드락
     (근본원인 #2) 차단).
  3) min DB(stock_min_back.db moneytop)에서 유동성 높은 단일 종목 +
     충분한 분봉 윈도우를 자동 산출 (runner의 code_days 로직 복제).
  4) runner.run_backtest(cfg) 직접 호출 — divid_mode='한종목 로딩',
     engine_count=1, is_tick=False, timeout=300.
  5) status/checkpoint/CSV/거래수/메트릭 + wall-clock 출력.

실행:
    python -m ai_strategy_loop.scripts.e2e_smoke
"""

from __future__ import annotations

# (1) bootstrap을 가장 먼저 — cli.* / utility.* import 전에 env 격리.
import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402

import json  # noqa: E402
import os  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

from ai_strategy_loop.config import LoopConfig  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIN_DB = os.path.join(REPO_ROOT, "_database", "stock_min_back.db")
TICK_DB = os.path.join(REPO_ROOT, "_database", "stock_tick_back.db")

# MIN 타임프레임 전용 스모크 전략 이름 (타임프레임 인지 생성 경로 검증용).
BUY_NAME = "AILOOP_min_buy"
SELL_NAME = "AILOOP_min_sell"


def _strategies_exist() -> bool:
    """루프 DB에 buy/sell 스모크 전략이 둘 다 있는지 확인."""
    db = str(bootstrap.LOOP_DB_STRATEGY)
    if not os.path.isfile(db):
        return False
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        cur.execute("SELECT `index` FROM stockbuy")
        buys = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT `index` FROM stocksell")
        sells = {r[0] for r in cur.fetchall()}
    finally:
        con.close()
    return BUY_NAME in buys and SELL_NAME in sells


def _regenerate_strategies(timeframe: str) -> None:
    """스모크 전략이 없을 때만 실 provider로 1 buy + 1 sell 재생성.

    timeframe 인지로 생성한다: prompt가 해당 계열 변수만 쓰도록 지시하고,
    generator의 변수 스코프 가드가 타임프레임에 없는 변수를 백테 이전에 거부한다.
    토큰/키는 절대 출력하지 않는다 (provider/proxy가 내부적으로 마스킹).
    """
    from ai_strategy_loop.brain import generate_strategy
    from ai_strategy_loop.brain.token_check import DedupTracker
    from ai_strategy_loop.provider.factory import make_provider
    from ai_strategy_loop.provider.chatgpt_oauth import (
        clear_env,
        inject_env,
        start_proxy_sync,
        stop_proxy_sync,
    )

    print(f"[E2E] 스모크 전략 없음 → 실 provider로 1 buy + 1 sell 재생성 "
          f"(timeframe={timeframe})")
    # 스모크 힌트: 단일 종목 짧은 윈도우에서 실제로 거래가 발생하도록(B_* 부검 경로
    #   검증) 느슨한 전략을 요청한다. autopsy_feedback 슬롯을 재사용해 코어 프롬프트는
    #   건드리지 않는다 (실 루프 품질에 영향 없음).
    smoke_hint = {
        "buy": (
            "스모크 검증용이다. 단일 종목 짧은 윈도우에서도 실제 매수가 자주 발생하도록 "
            "조건을 최소화하라(2~3개 이내). 예: 등락율/체결강도 하한 같은 느슨한 진입 1~2개만 "
            "두고 나머지는 생략한다. 지나치게 많은 and 조건은 거래를 0건으로 만들어 금지한다."
        ),
        "sell": (
            "스모크 검증용이다. 보유 종목이 빠르게 청산되도록 느슨한 청산 조건(예: 수익률 익절/"
            "손절 임계 1~2개)만 둔다. 조건을 최소화해 실제 매도가 발생하게 하라."
        ),
    }
    inject_env()
    if not start_proxy_sync():
        clear_env()
        raise RuntimeError("gpt_auth 프록시 시작 실패 (재생성 불가)")
    try:
        cfg = LoopConfig()
        provider = make_provider(cfg)
        dedup = DedupTracker(k=5)
        db = str(bootstrap.LOOP_DB_STRATEGY)
        for gubun, name in (("buy", BUY_NAME), ("sell", SELL_NAME)):
            res = generate_strategy(
                provider, gubun, name, db,
                timeframe=timeframe, retry_max=3, dedup=dedup,
                autopsy_feedback=smoke_hint[gubun],
            )
            print(f"[E2E] regen {gubun}: status={res.get('status')} "
                  f"attempts={res.get('attempts')}")
            if res.get("status") != "ok":
                raise RuntimeError(f"{gubun} 전략 재생성 실패: {res.get('reason')}")
            # 생성된 코드 + 스코프 통과 사실을 출력 (검증 가시성).
            print(f"[E2E] --- 생성된 {gubun} 전략 ({timeframe}, 스코프 통과) ---")
            print(res.get("code"))
            print(f"[E2E] --- /{gubun} ---")
    finally:
        stop_proxy_sync()
        clear_env()


def _select_single_stock(timeframe: str, window_days: int):
    """BOUNDED 단일 종목 스코프를 timeframe에 맞춰 자동 선택한다.

    runner.run_backtest 의 code_days 로직을 복제한다. timeframe에 따라
    데이터 소스 DB와 일자 추출 방식이 다르다:
      - tick: stock_tick_back.db, index = YYYYMMDDHHMMSS → 일자 = idx // 1_000_000
      - min : stock_min_back.db,  index = YYYYMMDDHHMM   → 일자 = idx // 10_000

    moneytop에서 가장 많은 거래일에 등장하는(=유동성 높은) 종목을 고르고,
    그 종목의 moneytop 등장일 ∩ 종목 자체 테이블 보유일 교집합에서 앞쪽
    `window_days` 일을 윈도우로 잡는다.

    교집합을 쓰는 이유: moneytop 등장일과 종목의 실제 데이터 보유일이
    어긋나면 엔진이 데이터 없는 날에 멈출 수 있어서다. 또한 1일 윈도우는
    집계 프로토콜이 멈추는 경향이 있어 `window_days`(기본 5)로 하한을 둔다.

    반환: (one_code, start_yyyymmdd, end_yyyymmdd, day_count_in_window)
    """
    is_tick = timeframe == "tick"
    db_path = TICK_DB if is_tick else MIN_DB
    day_div = 1_000_000 if is_tick else 10_000

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        # moneytop 값 컬럼명은 인코딩 이슈가 있어 위치(2번째 컬럼)로 접근.
        cur.execute("PRAGMA table_info(moneytop)")
        cols = [r[1] for r in cur.fetchall()]
        val_col = cols[1]  # ['index', '<거래대금순위>']
        cur.execute(f'SELECT "index", "{val_col}" FROM moneytop')
        rows = cur.fetchall()

        # code -> set of distinct days
        code_days: dict[str, set] = {}
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

        # 가장 많은 거래일에 등장하는 종목 = 가장 유동성 높은 후보.
        best_code = max(code_days, key=lambda c: len(code_days[c]))

        # 종목 자체 테이블의 보유일과 교집합.
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


def _run_backtest_subprocess(loop: LoopConfig, one_code: str, start: int, end: int):
    """검증된 CLI 진입점(stom_backtest.py)을 서브프로세스로 호출한다.

    in-process로 runner.run_backtest를 직접 호출하면 Windows에서
    multiprocessing(spawn) 자식이 __main__(e2e 모듈)을 무겁게 재import하고,
    matplotlib GUI 백엔드 초기화로 엔진이 멈추는 문제가 있다. stom_backtest.py는
    headless(agg) 사전설정 + 가벼운 __main__을 갖춘 검증된 경로이므로,
    BOUNDED 단일 종목 스코프를 그 CLI에 그대로 전달한다.

    timeout/divid-mode/one-code를 명시해 풀 유니버스 회피를 보장한다.
    """
    env = dict(os.environ)
    env["STOM_ALLOW_MINIMAL_SETTING"] = "1"
    env["STOM_CLI_DB_STRATEGY"] = str(bootstrap.LOOP_DB_STRATEGY)
    # 자식 프로세스 출력 즉시 flush (관찰 가능).
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable,
        os.path.join(REPO_ROOT, "stom_backtest.py"),
        "--buy", BUY_NAME,
        "--sell", SELL_NAME,
        "--start", str(start),
        "--end", str(end),
        "--timeframe", loop.bt_timeframe,        # 'min'
        "--divid-mode", "한종목 로딩",            # 단일 종목 = BOUNDED
        "--one-code", one_code,
        "--engines", str(loop.bt_engine_count),  # 1
        "--timeout", str(loop.bt_timeout),       # 300
        "--format", "json",
        "--quiet",
    ]
    print("[E2E] backtest cmd:", " ".join(cmd), flush=True)
    # 자식 timeout보다 약간 여유를 두고 부모 watchdog.
    return subprocess.run(
        cmd, cwd=REPO_ROOT, env=env,
        capture_output=True, text=True,
        timeout=loop.bt_timeout + 60,
    )


def _parse_cli_json(stdout: str) -> dict:
    """CLI --format json stdout에서 결과 JSON 문서를 파싱한다.

    CLI는 결과를 여러 줄 pretty JSON 한 문서로 낸다. 전체 stdout을 우선 그대로
    파싱하고(잡음 없는 경우), 실패하면 가장 바깥 중괄호 블록을 떼어 파싱한다.
    어느 경로로도 실패하면 빈 dict를 돌려준다 (호출자가 FAIL 처리).
    """
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 잡음이 섞인 경우: 첫 '{' ~ 마지막 '}' 블록만 떼어 파싱.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def main() -> int:
    print("[E2E] loop DB:", bootstrap.LOOP_DB_STRATEGY)
    print("[E2E] STOM_CLI_DB_STRATEGY:", os.environ.get("STOM_CLI_DB_STRATEGY"))

    loop = LoopConfig()  # bt_* 기본값: single_stock / min / engine=1 / timeout
    print("[E2E] bt_timeframe:", loop.bt_timeframe)

    # (1b) 루프 DB 엔진 호환 보장 — formula 빈 테이블이 없으면 엔진이 데드락한다.
    #   백테스트 **이전**에 반드시 호출 (데드락 근본원인 #1 차단).
    bootstrap.ensure_loop_db_engine_compat()
    print("[E2E] ensure_loop_db_engine_compat() OK (formula 테이블 보장)")

    # (2) 전략 확보 (timeframe 인지 생성).
    if _strategies_exist():
        print(f"[E2E] 기존 스모크 전략 사용: {BUY_NAME} / {SELL_NAME}")
    else:
        _regenerate_strategies(loop.bt_timeframe)
        if not _strategies_exist():
            print("[E2E] FAIL: 재생성 후에도 전략이 없습니다")
            return 2

    # (3) BOUNDED 단일 종목 스코프 자동 선택.
    one_code = loop.bt_one_code
    start = loop.bt_start
    end = loop.bt_end
    if not (one_code and start and end):
        one_code, start, end, day_count = _select_single_stock(
            timeframe=loop.bt_timeframe, window_days=loop.bt_window_days
        )
    else:
        day_count = None

    print("\n[E2E] === BOUNDED SCOPE ===")
    print(json.dumps({
        "bt_scope": loop.bt_scope,
        "bt_timeframe": loop.bt_timeframe,
        "divid_mode": "한종목 로딩",
        "one_code": one_code,
        "start": start,
        "end": end,
        "window_day_count": day_count,
        "engine_count": loop.bt_engine_count,
        "timeout": loop.bt_timeout,
    }, ensure_ascii=False))

    # (4) 검증된 CLI 진입점으로 BOUNDED 백테스트 1회 (서브프로세스).
    t0 = time.time()
    proc = _run_backtest_subprocess(loop, one_code, start, end)
    elapsed = time.time() - t0

    print(f"\n[E2E] backtest exit code: {proc.returncode}", flush=True)
    print("----- stdout (tail) -----")
    print("\n".join(proc.stdout.splitlines()[-30:]))
    if proc.stderr.strip():
        print("----- stderr (tail) -----")
        print("\n".join(proc.stderr.splitlines()[-15:]))

    # (5) 결과 JSON 파싱.
    #   CLI --format json은 결과를 **여러 줄 pretty JSON 한 문서**로 출력한다
    #   (status/metrics/csv_path/checkpoints 등 top-level 키). 그래서 줄 단위가 아니라
    #   stdout에서 가장 바깥 {..} 블록 전체를 떼어 한 번에 파싱한다.
    payload = _parse_cli_json(proc.stdout)

    status = payload.get("status")
    csv_path = payload.get("csv_path")
    metrics = payload.get("metrics")
    checkpoint = payload.get("checkpoint_reached") or payload.get("last_checkpoint")

    print("\n[E2E] === RESULT ===")
    print(f"[E2E] status         : {status}")
    print(f"[E2E] message        : {payload.get('message')}")
    print(f"[E2E] checkpoint     : {checkpoint}")
    print(f"[E2E] wall-clock     : {elapsed:.1f}s (timeout={loop.bt_timeout}s)")
    print(f"[E2E] csv_path       : {csv_path}")

    trade_count = None
    if metrics:
        trade_count = metrics.get("trade_count")
        print("[E2E] metrics        :", json.dumps({
            "trade_count": metrics.get("trade_count"),
            "win_rate": metrics.get("win_rate"),
            "total_profit_pct": metrics.get("total_profit_pct"),
            "tpi": metrics.get("tpi"),
            "mdd_pct": metrics.get("mdd_pct"),
        }, ensure_ascii=False))
    else:
        print("[E2E] metrics        : (none)")

    csv_ok = False
    if csv_path:
        abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
        csv_ok = os.path.isfile(abs_csv)
        print(f"[E2E] CSV exists     : {csv_ok} ({abs_csv})")
    else:
        print("[E2E] WARN: csv_path 없음")

    # PASS 기준: exit 0 + status success + CSV 산출 (거래수 0도 fallback 허용).
    ok = (proc.returncode == 0) and (status == "success") and csv_ok
    print(f"\n[E2E] trade_count    : {trade_count}")
    print(f"[E2E] RESULT         : {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
