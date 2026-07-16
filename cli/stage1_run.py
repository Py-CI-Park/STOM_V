"""stage1_run -- Stage-1 봉인(sealed) 시행(trial) 실행기 (G005).

이 모듈은 ``cli.wide_seed_trial_planner.TrialSpecV1`` 하나를 받아 공식 CLI
엔트리포인트(``stom_backtest.py``)를 서브프로세스로 호출해 buy/sell 페어를
전체 가용 히스토리에 대해 실행하고, ``TestedCellLedgerV1`` 이벤트
(``executed``/``failed``)를 append-only 원장에 기록한다.

공식 진입점을 그대로 서브프로세스로 호출하는 이유는
``ai_strategy_loop/controller/loop.py:run_backtest_for`` 와 동일하다 --
Windows에서 in-process ``cli.runner.run_backtest``(multiprocessing spawn)를
호출하면 자식 프로세스가 무거운 ``__main__`` 재import + matplotlib GUI
초기화로 멈추는 문제가 있다. 이 모듈은 백테스트 수학을 재구현하지 않고,
검증된 CLI 프로토콜(큐/argv/프로세스 계약)만 그대로 재사용한다.

절대 하지 않는 것:
  - 백테스트 수학 재구현(공식 엔진 서브프로세스 호출만 수행).
  - 운영 ``_database/`` 쓰기 -- 쓰기 가능한 모든 DB(setting/backtest/strategy)는
    worktree-local 또는 격리 경로로 봉인(seal)하고, 시세 DB 디렉터리(``data_dir``)는
    읽기 전용으로만 사용한다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from cli.wide_seed_trial_planner import (
    TestedCellLedgerV1,
    TrialSpecV1,
    append_ledger_entry,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STOM_BACKTEST_ENTRYPOINT = REPO_ROOT / "stom_backtest.py"

#: lane -> ``--timeframe`` 매핑. Stage-1은 min lane만 실행하지만 계약을
#: 명시적으로 남기기 위해 두 lane을 모두 나열한다.
LANE_TIMEFRAMES: dict[str, str] = {"tick": "tick", "min": "min"}

#: 기본 병렬 엔진 프로세스 수 -- 저장소 기본값(``cli/config.py``)과 동일.
DEFAULT_ENGINE_COUNT = 4

#: 기본 타임아웃(초) -- 전체 히스토리 단일 실행을 위해 넉넉히 잡는다.
DEFAULT_TIMEOUT_SEC = 7200

#: 쓰기 가능 경로가 실수로 가리켜서는 안 되는 보호된 경로 세그먼트.
_FORBIDDEN_PATH_SEGMENTS = ("_database",)

#: 12-cell 분해에 필요한 필수 per-trade CSV 컬럼.
REQUIRED_TRADE_COLUMNS: tuple[str, ...] = ("매수시간", "시가총액")

# ---------------------------------------------------------------------------
# warm-session(웜세션) 모드 상수 (G005 slice B) -- 검증된 배치 러너 경로.
#
# ``run_trial``(위)은 ``stom_backtest.py``를 매 시행마다 서브프로세스로 새로
# spawn한다(cold, engines=4). 전체유니버스(``종목코드별 분류``) min-lane 시행은
# 이 경로에서 엔진 데이터로딩이 수렴하지 못했다(g005_min_run_log.txt 참고).
#
# ``run_trial_warm``은 그 대신 실제 tick-lane 전체유니버스 캠페인
# (.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py +
# ai_strategy_loop.scripts.claude_candidate_batch_eval)이 증명한 경로를 그대로
# 재사용한다: ``cli.warm_session.WarmBacktestSession``이 엔진을 병렬 spawn하고
# 데이터를 1회만 로딩한 뒤(prepare), 전략만 바꿔가며 반복 실행(run)한다. 엔진
# 수도 4개가 아니라 32개(``bt_warm_engine_count`` 기본값)라 전체유니버스
# 종목코드 집합을 32분할해 엔진당 데이터량이 8배 작아진다.
# ---------------------------------------------------------------------------

#: warm 세션 기본 엔진 수 -- ``ai_strategy_loop/config.py:bt_warm_engine_count`` 기본값과 동일.
DEFAULT_WARM_ENGINE_COUNT = 32

#: min lane warm 스코프 장중 윈도우 시작(HHMMSS).
DEFAULT_WARM_MIN_START_TIME = 90000

#: min lane warm 스코프 장중 윈도우 종료(HHMMSS) -- ``WSEED_V1_Min`` 12-leaf가
#: 09:00~14:00(``cli.wide_seed_v1.MIN_WINDOWS``) 전체를 요구하므로, min-lane
#: 기본값(92800=09:28)이 아니라 풀세션(``bt_min_universe_end_time`` 기본값)까지 연다.
DEFAULT_WARM_MIN_END_TIME = 151900

#: 격리된 warm 배치 러너 wrapper 스크립트 -- 운영 ``ai_strategy_loop/state/loop_runs.db``를
#: 절대 건드리지 않도록 ``ai_strategy_loop.controller.state`` 경로를 monkeypatch한다
#: (``.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py``와 동일 패턴).
WARM_BATCH_EVAL_WRAPPER = REPO_ROOT / "artifacts" / "ultragoal-condtree" / "g005_run_min_warm_wrapper.py"

#: warm wrapper가 격리하는 상태 디렉터리/파일 -- wrapper 스크립트가 이 상수들을 그대로
#: import해 ``ai_strategy_loop.controller.state``의 모듈 전역을 덮어쓴다.
WARM_STATE_DIR = REPO_ROOT / "artifacts" / "ultragoal-condtree" / "g005_warm_state"
WARM_RUNS_SQLITE = WARM_STATE_DIR / "g005-min-warm-loop-runs.sqlite"
WARM_SNAPSHOT_DIR = WARM_STATE_DIR / "g005-min-warm-snapshots"
WARM_CURRENT_STATE_FILE = WARM_STATE_DIR / "g005-min-warm-current-state.json"
WARM_STOP_FLAG_FILE = WARM_STATE_DIR / "g005-min-warm-STOP"


# ---------------------------------------------------------------------------
# 순수 헬퍼 -- I/O 없음, 단위 테스트 대상.
# ---------------------------------------------------------------------------


def _reject_forbidden_write_target(path: Path | str) -> None:
    """``path`` 에 ``_database`` 세그먼트가 포함되어 있으면 거부한다.

    쓰기 가능 DB(setting/backtest) 경로가 실수로 운영 ``_database/`` 를
    가리키는 사고를 사전에 차단한다.
    """

    normalized = str(Path(path)).replace("\\", "/").split("/")
    for segment in _FORBIDDEN_PATH_SEGMENTS:
        if segment in normalized:
            raise ValueError(
                f"쓰기 대상 경로 {path!r} 는 보호된 세그먼트 {segment!r} 를 "
                "포함하므로 거부합니다 (시세 DB는 읽기 전용이어야 합니다)."
            )


def build_sealed_env(
    *,
    data_dir: str | Path,
    strategy_db: str | Path,
    writable_dir: str | Path,
    base_env: Optional[dict] = None,
) -> dict:
    """서브프로세스에 전달할 env 딕셔너리를 봉인(seal)한다 -- 순수 함수.

    - ``data_dir``     : 읽기전용 시세 DB 디렉터리(``stock_min_back.db`` 위치).
      이 함수는 해당 디렉터리에 아무것도 쓰지 않으며, 오직 ``STOM_CLI_DB_STOCK_BACK_MIN``
      환경변수로 읽기 경로만 지정한다.
    - ``strategy_db``  : 격리된 전략 DB 경로(예: ``ai_strategy_loop/state/loop_strategies.db``).
    - ``writable_dir`` : ``setting.db``/``backtest.db`` 등 쓰기용 DB를 둘
      worktree-local 디렉터리. ``_database`` 세그먼트를 포함하면 거부한다.
    """

    _reject_forbidden_write_target(writable_dir)
    _reject_forbidden_write_target(strategy_db)

    data_dir = Path(data_dir)
    writable_dir = Path(writable_dir)

    env = dict(base_env if base_env is not None else os.environ)
    env["STOM_ALLOW_MINIMAL_SETTING"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # 시세(읽기 전용) -- min lane만 다루므로 STOM_CLI_DB_STOCK_BACK_MIN만 override한다.
    env["STOM_CLI_DB_STOCK_BACK_MIN"] = str(data_dir / "stock_min_back.db")
    # 쓰기 가능 DB -- 모두 worktree-local/격리 경로로 봉인.
    env["STOM_CLI_DB_STRATEGY"] = str(strategy_db)
    env["STOM_CLI_DB_SETTING"] = str(writable_dir / "stage1_setting.db")
    env["STOM_CLI_DB_BACKTEST"] = str(writable_dir / "stage1_backtest.db")
    return env


def build_command(
    spec: TrialSpecV1,
    *,
    start_date: int,
    end_date: int,
    engine_count: int = DEFAULT_ENGINE_COUNT,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> list[str]:
    """공식 CLI 진입점(``stom_backtest.py``) 호출 인자 리스트를 조립한다 -- 순수 함수."""

    if spec.lane not in LANE_TIMEFRAMES:
        raise ValueError(f"알 수 없는 lane {spec.lane!r} 입니다.")

    return [
        sys.executable,
        str(STOM_BACKTEST_ENTRYPOINT),
        "--buy", spec.buy_name,
        "--sell", spec.sell_name,
        "--start", str(start_date),
        "--end", str(end_date),
        "--timeframe", LANE_TIMEFRAMES[spec.lane],
        "--engines", str(engine_count),
        "--timeout", str(timeout),
        "--format", "json",
        "--quiet",
    ]


def _ledger_record(event: str, spec: TrialSpecV1, detail: dict[str, Any]) -> TestedCellLedgerV1:
    """원장 이벤트 1건(``executed``/``failed``)을 순수하게 조립한다.

    ``spec_hash`` 는 계획기(``wide_seed_trial_planner``) 관례와 동일하게
    ``spec.trial_id`` 값을 그대로 사용한다(``g004_tested_cell_ledger.jsonl`` 참고).
    """

    return TestedCellLedgerV1(
        event=event,
        trial_id=spec.trial_id,
        spec_hash=spec.trial_id,
        detail=dict(detail),
    )


def _parse_cli_json(stdout: str) -> dict:
    """CLI ``--format json`` stdout에서 결과 JSON 문서를 파싱한다.

    ``ai_strategy_loop/controller/loop.py:_parse_cli_json`` 과 동일 로직 --
    stdout 전체가 JSON이 아닐 경우(경고 등 섞임) 첫 ``{`` ~ 마지막 ``}`` 구간을
    다시 시도한다.
    """

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


def _summarize_csv(csv_path: str) -> dict[str, Any]:
    """per-trade CSV를 읽어 컬럼/거래수/필수 컬럼 존재 여부를 요약한다."""

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    columns = list(df.columns)
    missing_required = [c for c in REQUIRED_TRADE_COLUMNS if c not in columns]
    distinct_symbols: Optional[int] = None
    if "종목코드" in columns:
        distinct_symbols = int(df["종목코드"].nunique())
    return {
        "trade_count": int(len(df)),
        "columns": columns,
        "missing_required_columns": missing_required,
        "distinct_symbols": distinct_symbols,
    }


# ---------------------------------------------------------------------------
# run_trial -- 실제 서브프로세스 실행(I/O 있음). 단위 테스트 대상 아님.
# ---------------------------------------------------------------------------


def run_trial(
    spec: TrialSpecV1,
    *,
    data_dir: str | Path,
    ledger_path: str | Path,
    start_date: int,
    end_date: int,
    strategy_db: Optional[str | Path] = None,
    writable_dir: Optional[str | Path] = None,
    engine_count: int = DEFAULT_ENGINE_COUNT,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    dry: bool = False,
) -> dict[str, Any]:
    """``spec`` 1건을 공식 CLI로 실행하고 결과 dict를 반환하며 원장에 기록한다.

    반환값: ``{status, csv_path, trade_count, elapsed}`` (+ 성공 시 ``columns``,
    ``distinct_symbols``; 실패 시 ``message``).

    ``dry=True`` 이면 커맨드/env만 조립하고 실제 서브프로세스는 실행하지 않으며
    원장에도 기록하지 않는다(하네스 자체 점검용).
    """

    strategy_db = Path(strategy_db) if strategy_db is not None else (
        REPO_ROOT / "ai_strategy_loop" / "state" / "loop_strategies.db"
    )
    writable_dir = Path(writable_dir) if writable_dir is not None else (REPO_ROOT / "backtest" / "temp")
    writable_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_command(
        spec, start_date=start_date, end_date=end_date,
        engine_count=engine_count, timeout=timeout,
    )
    env = build_sealed_env(data_dir=data_dir, strategy_db=strategy_db, writable_dir=writable_dir)

    if dry:
        return {
            "status": "dry_run",
            "command": cmd,
            "env_keys": sorted(k for k in env if k.startswith("STOM_")),
            "csv_path": None,
            "trade_count": 0,
            "elapsed": 0.0,
        }

    # 백테 엔진이 DB_STRATEGY에서 formula 테이블을 읽으므로(빈 테이블이라도)
    # 없으면 BackTest child가 데드락(타임아웃)한다 -- bootstrap과 동일 가드.
    import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415 -- 지연 import(순환 회피)

    bootstrap.ensure_loop_db_engine_compat(str(strategy_db))

    start_ts = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env,
            capture_output=True, text=True,
            timeout=timeout + 60,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_ts
        detail = {"reason": f"subprocess timeout > {timeout + 60}s", "command": cmd}
        append_ledger_entry(ledger_path, _ledger_record("failed", spec, detail))
        return {
            "status": "failed", "message": detail["reason"],
            "csv_path": None, "trade_count": 0, "elapsed": elapsed,
        }
    except Exception as exc:  # noqa: BLE001 -- 서브프로세스 기동 실패도 실패 결과로 표준화.
        elapsed = time.time() - start_ts
        detail = {"reason": f"subprocess spawn failed: {exc}", "command": cmd}
        append_ledger_entry(ledger_path, _ledger_record("failed", spec, detail))
        return {
            "status": "failed", "message": detail["reason"],
            "csv_path": None, "trade_count": 0, "elapsed": elapsed,
        }

    elapsed = time.time() - start_ts
    payload = _parse_cli_json(proc.stdout)
    status = payload.get("status")
    csv_path = payload.get("csv_path")
    message = payload.get("message")

    if proc.returncode != 0 or status != "success" or not csv_path:
        detail = {
            "exit_code": proc.returncode,
            "status": status,
            "message": message,
            "last_checkpoint": payload.get("last_checkpoint"),
            "stdout_tail": proc.stdout[-2000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
            "command": cmd,
        }
        append_ledger_entry(ledger_path, _ledger_record("failed", spec, detail))
        return {
            "status": "failed",
            "message": message or "backtest completed without success",
            "csv_path": csv_path,
            "trade_count": 0,
            "elapsed": elapsed,
            "raw": payload,
        }

    summary = _summarize_csv(csv_path)
    detail = {
        "csv_path": csv_path,
        "trade_count": summary["trade_count"],
        "elapsed_sec": elapsed,
        "columns": summary["columns"],
        "distinct_symbols": summary["distinct_symbols"],
        "start_date": start_date,
        "end_date": end_date,
    }
    append_ledger_entry(ledger_path, _ledger_record("executed", spec, detail))

    return {
        "status": "success",
        "csv_path": csv_path,
        "trade_count": summary["trade_count"],
        "elapsed": elapsed,
        "columns": summary["columns"],
        "distinct_symbols": summary["distinct_symbols"],
        "missing_required_columns": summary["missing_required_columns"],
    }


# ---------------------------------------------------------------------------
# warm-session 순수 헬퍼 -- I/O 없음, 단위 테스트 대상.
# ---------------------------------------------------------------------------


def build_warm_pairs_payload(spec: TrialSpecV1) -> list[dict[str, str]]:
    """``claude_candidate_batch_eval --pairs-json`` 계약(list[{label,buy,sell}])을 조립한다 -- 순수 함수."""

    return [{"label": spec.trial_id, "buy": spec.buy_name, "sell": spec.sell_name}]


def build_warm_config_payload(
    *,
    start_date: int,
    end_date: int,
    engine_count: int = DEFAULT_WARM_ENGINE_COUNT,
    start_time: int = DEFAULT_WARM_MIN_START_TIME,
    end_time: int = DEFAULT_WARM_MIN_END_TIME,
    avg_time: int = 30,
    betting: str = "5",
    data_load_timeout: int = 3600,
    run_timeout: int = 3600,
) -> dict[str, Any]:
    """웜세션 배치 러너 ``--config-json`` 계약(``LoopConfig`` dict)을 조립한다 -- 순수 함수.

    ``bt_timeframe='min'`` + ``full_session_enabled=True`` 조합이면
    ``ai_strategy_loop/controller/loop.py:_build_warm_btconfig`` 가 장중 윈도우 종료를
    ``bt_universe_end_time``(기본 92800=09:28) 대신 ``end_time``(``bt_min_universe_end_time``)
    까지 연다 -- ``WSEED_V1_Min`` 12-leaf가 09:00~14:00 전체를 요구하므로 필수다.
    """

    return {
        "provider": "gpt_auth",
        "bt_timeframe": "min",
        "bt_full_start": start_date,
        "bt_full_end": end_date,
        "bt_warm_engine_count": engine_count,
        "bt_universe_start_time": start_time,
        "full_session_enabled": True,
        "bt_min_universe_end_time": end_time,
        "bt_betting": betting,
        "bt_avg_time": avg_time,
        "bt_timeout": data_load_timeout,
        "bt_warm_run_timeout": run_timeout,
        "max_generations": 1,
        "autopsy_enabled": False,
    }


def build_warm_command(
    *,
    pairs_json_path: str | Path,
    config_json_path: str | Path,
    run_id: str,
    wrapper_path: str | Path = WARM_BATCH_EVAL_WRAPPER,
    fail_fast_timeout: bool = True,
) -> list[str]:
    """격리된 웜세션 배치 러너(``WARM_BATCH_EVAL_WRAPPER``) 호출 인자 리스트를 조립한다 -- 순수 함수.

    ``fail_fast_timeout=True``(기본)이면 ``--fail-fast-timeout``을 붙여 단일 trial
    실행 중 timeout이 나면 엔진 복구(reset+reload) 비용을 지불하지 않고 즉시
    error row를 기록하게 한다(1회성 시행에는 복구 비용이 낭비이므로).
    """

    cmd = [
        sys.executable, str(wrapper_path),
        "--pairs-json", str(pairs_json_path),
        "--config-json", str(config_json_path),
        "--run-id", run_id,
    ]
    if fail_fast_timeout:
        cmd.append("--fail-fast-timeout")
    return cmd


def _read_warm_generation(runs_db_path: str | Path, run_id: str, gen_no: int = 0) -> Optional[dict[str, Any]]:
    """격리된 warm ``loop_runs.db``(``generations`` 테이블)에서 세대 1건을 읽는다."""

    import sqlite3

    if not Path(runs_db_path).exists():
        return None
    con = sqlite3.connect(str(runs_db_path))
    try:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM generations WHERE run_id = ? AND gen_no = ?",
            (run_id, gen_no),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        con.close()


# ---------------------------------------------------------------------------
# run_trial_warm -- 웜세션 배치 러너 서브프로세스 실행(I/O 있음). 단위 테스트 대상 아님.
# ---------------------------------------------------------------------------


def run_trial_warm(
    spec: TrialSpecV1,
    *,
    data_dir: str | Path,
    ledger_path: str | Path,
    start_date: int,
    end_date: int,
    strategy_db: Optional[str | Path] = None,
    writable_dir: Optional[str | Path] = None,
    engine_count: int = DEFAULT_WARM_ENGINE_COUNT,
    start_time: int = DEFAULT_WARM_MIN_START_TIME,
    end_time: int = DEFAULT_WARM_MIN_END_TIME,
    avg_time: int = 30,
    betting: str = "5",
    data_load_timeout: int = 3600,
    run_timeout: int = 3600,
    subprocess_timeout: Optional[int] = None,
    dry: bool = False,
) -> dict[str, Any]:
    """``spec`` 1건을 웜세션(``WarmBacktestSession``) 배치 러너로 실행하고 원장에 기록한다.

    ``run_trial``(cold, ``stom_backtest.py`` 서브프로세스, engines=4)과 달리 이 함수는
    ``ai_strategy_loop.scripts.claude_candidate_batch_eval``(``cli.warm_session.WarmBacktestSession``,
    engines=``DEFAULT_WARM_ENGINE_COUNT``)을 호출한다 -- 실제 tick-lane 전체유니버스
    캠페인(post-Q4 r8 lowcap OOS)이 증명한 경로와 동일한 메커니즘이다.

    반환값: ``{status, csv_path, trade_count, elapsed}`` (+ 성공 시 ``columns``,
    ``distinct_symbols``; 실패 시 ``message``).

    ``dry=True`` 이면 커맨드/env/pairs·config payload만 조립하고 실제 서브프로세스는
    실행하지 않으며 원장에도 기록하지 않는다(하네스 자체 점검용).
    """

    strategy_db = Path(strategy_db) if strategy_db is not None else (
        REPO_ROOT / "ai_strategy_loop" / "state" / "loop_strategies.db"
    )
    writable_dir = Path(writable_dir) if writable_dir is not None else (REPO_ROOT / "backtest" / "temp")
    writable_dir.mkdir(parents=True, exist_ok=True)

    run_id = f"{spec.trial_id}_warm"
    pairs_path = writable_dir / f"{run_id}_pairs.json"
    config_path = writable_dir / f"{run_id}_config.json"
    pairs_payload = build_warm_pairs_payload(spec)
    config_payload = build_warm_config_payload(
        start_date=start_date, end_date=end_date, engine_count=engine_count,
        start_time=start_time, end_time=end_time, avg_time=avg_time, betting=betting,
        data_load_timeout=data_load_timeout, run_timeout=run_timeout,
    )

    cmd = build_warm_command(pairs_json_path=pairs_path, config_json_path=config_path, run_id=run_id)
    env = build_sealed_env(data_dir=data_dir, strategy_db=strategy_db, writable_dir=writable_dir)

    if dry:
        return {
            "status": "dry_run",
            "command": cmd,
            "env_keys": sorted(k for k in env if k.startswith("STOM_")),
            "pairs": pairs_payload,
            "config": config_payload,
            "csv_path": None,
            "trade_count": 0,
            "elapsed": 0.0,
        }

    pairs_path.write_text(json.dumps(pairs_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 백테 엔진이 DB_STRATEGY에서 formula 테이블을 읽으므로(빈 테이블이라도)
    # 없으면 BackTest child가 데드락(타임아웃)한다 -- run_trial과 동일 가드.
    import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415 -- 지연 import(순환 회피)

    bootstrap.ensure_loop_db_engine_compat(str(strategy_db))

    proc_timeout = subprocess_timeout or (data_load_timeout + run_timeout + 300)
    start_ts = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(REPO_ROOT), env=env,
            capture_output=True, text=True,
            timeout=proc_timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_ts
        detail = {"reason": f"warm batch subprocess timeout > {proc_timeout}s", "command": cmd}
        append_ledger_entry(ledger_path, _ledger_record("failed", spec, detail))
        return {
            "status": "failed", "message": detail["reason"],
            "csv_path": None, "trade_count": 0, "elapsed": elapsed,
        }
    except Exception as exc:  # noqa: BLE001 -- 서브프로세스 기동 실패도 실패 결과로 표준화.
        elapsed = time.time() - start_ts
        detail = {"reason": f"warm batch subprocess spawn failed: {exc}", "command": cmd}
        append_ledger_entry(ledger_path, _ledger_record("failed", spec, detail))
        return {
            "status": "failed", "message": detail["reason"],
            "csv_path": None, "trade_count": 0, "elapsed": elapsed,
        }

    elapsed = time.time() - start_ts
    generation = _read_warm_generation(WARM_RUNS_SQLITE, run_id)
    csv_path = generation.get("csv_path") if generation else None

    if proc.returncode != 0 or not generation or generation.get("status") != "ok" or not csv_path:
        detail = {
            "exit_code": proc.returncode,
            "generation": generation,
            "stdout_tail": proc.stdout[-4000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-4000:] if proc.stderr else "",
            "command": cmd,
        }
        append_ledger_entry(ledger_path, _ledger_record("failed", spec, detail))
        return {
            "status": "failed",
            "message": (generation or {}).get("reason") or "warm batch completed without success",
            "csv_path": csv_path,
            "trade_count": 0,
            "elapsed": elapsed,
            "raw": generation,
        }

    summary = _summarize_csv(csv_path)
    detail = {
        "csv_path": csv_path,
        "trade_count": summary["trade_count"],
        "elapsed_sec": elapsed,
        "columns": summary["columns"],
        "distinct_symbols": summary["distinct_symbols"],
        "start_date": start_date,
        "end_date": end_date,
        "mechanism": "warm_session",
    }
    append_ledger_entry(ledger_path, _ledger_record("executed", spec, detail))

    return {
        "status": "success",
        "csv_path": csv_path,
        "trade_count": summary["trade_count"],
        "elapsed": elapsed,
        "columns": summary["columns"],
        "distinct_symbols": summary["distinct_symbols"],
        "missing_required_columns": summary["missing_required_columns"],
    }
