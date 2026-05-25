"""US-005 Phase 2b — 루프 상태 영속 (SQLite WAL + JSON 스냅샷).

`ai_strategy_loop/state/loop_runs.db`를 WAL 모드로 열어 run/generation을
기록한다. WAL을 쓰는 이유: 헤드리스 루프가 한 세대를 쓰는 동안 별도 프로세스
(모니터/대시보드 등)가 락 에러 없이 동시에 읽을 수 있어야 하기 때문이다.

세대마다 JSON 스냅샷을 `ai_strategy_loop/state/snapshots/`에 떨군다 — DB가
깨져도 사람이 읽을 수 있는 진행 기록을 남기기 위한 단순 안전장치다.

resume 계약: 같은 run_id를 다시 열면 마지막 완료 세대 다음부터 이어간다.
세대 번호는 절대 중복되지 않는다(같은 (run_id, gen_no)는 UPSERT).
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 패키지 루트 (.../ai_strategy_loop)
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_STATE_DIR = _PACKAGE_DIR / "state"
_SNAPSHOT_DIR = _STATE_DIR / "snapshots"
LOOP_RUNS_DB = _STATE_DIR / "loop_runs.db"

# US-007 — 루프↔대시보드 라이브 상태 파일 + 정지 플래그 파일.
#   current_state.json : 루프가 매 세대/백테스트 시점에 atomic write 하는
#                        LoopState 스냅샷(contract.py). 대시보드가 폴링/푸시한다.
#   STOP               : 대시보드가 쓰는 정지 플래그. 루프가 세대 시작 전 확인.
CURRENT_STATE_FILE = _STATE_DIR / "current_state.json"
STOP_FLAG_FILE = _STATE_DIR / "STOP"


def _now() -> float:
    return time.time()


class LoopState:
    """루프 run/generation 영속 저장소 (WAL SQLite + JSON 스냅샷).

    하나의 LoopState 인스턴스는 하나의 DB 파일 연결을 소유한다. 기본 경로는
    LOOP_RUNS_DB이며, 테스트는 tmp 경로를 주입할 수 있다.
    """

    def __init__(self, db_path: Optional[str] = None, snapshot_dir: Optional[str] = None):
        self.db_path = str(db_path or LOOP_RUNS_DB)
        self.snapshot_dir = str(snapshot_dir or _SNAPSHOT_DIR)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.snapshot_dir).mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: 프록시/엔진이 별도 스레드를 쓰더라도 동일
        #   연결을 안전하게 재사용(루프는 단일 스레드 순차 기록이라 경합 없음).
        self._con = sqlite3.connect(self.db_path, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        # WAL 모드 — 동시 reader 비차단. journal_mode는 영구 설정이다.
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    # ------------------------------------------------------------------
    # 스키마
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        self._con.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                started_at  REAL,
                config_json TEXT,
                status      TEXT,
                best_gen    INTEGER,
                best_score  REAL,
                finished_at REAL
            );
            CREATE TABLE IF NOT EXISTS generations (
                run_id      TEXT,
                gen_no      INTEGER,
                buy_name    TEXT,
                sell_name   TEXT,
                status      TEXT,
                score       REAL,
                calmar      REAL,
                uptrend_r2  REAL,
                gate_passed INTEGER,
                reason      TEXT,
                csv_path    TEXT,
                trade_count INTEGER,
                mdd         REAL,
                profit      REAL,
                strategy_gist TEXT,
                created_at  REAL,
                PRIMARY KEY (run_id, gen_no)
            );
            """
        )
        self._con.commit()

    # ------------------------------------------------------------------
    # run 라이프사이클
    # ------------------------------------------------------------------
    def start_run(self, config: Any, run_id: Optional[str] = None) -> str:
        """새 run을 시작하고 run_id를 반환한다.

        run_id 미지정 시 타임스탬프 기반으로 생성한다. config는 to_dict()가
        있으면 그것을, 없으면 dict로 직렬화한다.
        """
        rid = run_id or f"run_{int(_now())}"
        config_json = json.dumps(_config_to_dict(config), ensure_ascii=False)
        self._con.execute(
            "INSERT OR REPLACE INTO runs "
            "(run_id, started_at, config_json, status, best_gen, best_score, finished_at) "
            "VALUES (?, ?, ?, 'running', NULL, NULL, NULL)",
            (rid, _now(), config_json),
        )
        self._con.commit()
        return rid

    def resume_or_start(self, config: Any, run_id: Optional[str] = None) -> str:
        """run_id가 이미 있으면 재개(상태 running 복원), 없으면 새로 시작한다.

        재개 시 config_json은 기존 값을 보존한다(원래 실행 설정 유지).
        """
        if run_id is not None:
            row = self._con.execute(
                "SELECT run_id FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is not None:
                self._con.execute(
                    "UPDATE runs SET status = 'running', finished_at = NULL WHERE run_id = ?",
                    (run_id,),
                )
                self._con.commit()
                return run_id
        return self.start_run(config, run_id=run_id)

    def record_generation(
        self,
        run_id: str,
        gen_no: int,
        *,
        buy_name: str,
        sell_name: str,
        status: str,
        score: float,
        calmar: float = 0.0,
        uptrend_r2: float = 0.0,
        gate_passed: bool = False,
        reason: str = "",
        csv_path: Optional[str] = None,
        trade_count: int = 0,
        mdd: float = 0.0,
        profit: float = 0.0,
        strategy_gist: str = "",
    ) -> None:
        """한 세대 결과를 기록한다 (UPSERT — 세대 번호 중복 없음).

        기록 직후 JSON 스냅샷을 남긴다. mdd/profit/strategy_gist는 대시보드
        세대 행(GenerationInfo)이 그대로 표시하는 값이라 함께 영속한다.
        """
        self._con.execute(
            "INSERT OR REPLACE INTO generations "
            "(run_id, gen_no, buy_name, sell_name, status, score, calmar, uptrend_r2, "
            " gate_passed, reason, csv_path, trade_count, mdd, profit, strategy_gist, "
            " created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id, gen_no, buy_name, sell_name, status, float(score),
                float(calmar), float(uptrend_r2), 1 if gate_passed else 0,
                reason, csv_path, int(trade_count),
                float(mdd), float(profit), strategy_gist, _now(),
            ),
        )
        self._con.commit()
        self._write_snapshot(run_id, gen_no, {
            "run_id": run_id,
            "gen_no": gen_no,
            "buy_name": buy_name,
            "sell_name": sell_name,
            "status": status,
            "score": float(score),
            "calmar": float(calmar),
            "uptrend_r2": float(uptrend_r2),
            "gate_passed": bool(gate_passed),
            "reason": reason,
            "csv_path": csv_path,
            "trade_count": int(trade_count),
            "mdd": float(mdd),
            "profit": float(profit),
            "strategy_gist": strategy_gist,
        })

    def update_best(self, run_id: str, best_gen: int, best_score: float) -> None:
        """run의 best_gen/best_score를 갱신한다 (더 높은 점수일 때만)."""
        row = self._con.execute(
            "SELECT best_score FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        current = row["best_score"] if row is not None else None
        if current is None or float(best_score) > float(current):
            self._con.execute(
                "UPDATE runs SET best_gen = ?, best_score = ? WHERE run_id = ?",
                (int(best_gen), float(best_score), run_id),
            )
            self._con.commit()

    def finish_run(self, run_id: str, status: str = "complete") -> None:
        """run을 종료 상태로 마킹한다."""
        self._con.execute(
            "UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?",
            (status, _now(), run_id),
        )
        self._con.commit()

    # ------------------------------------------------------------------
    # 조회 / resume 보조
    # ------------------------------------------------------------------
    def get_last_completed_gen(self, run_id: str) -> int:
        """기록된 마지막 세대 번호를 반환한다. 없으면 -1.

        resume는 이 값 + 1 부터 이어간다.
        """
        row = self._con.execute(
            "SELECT MAX(gen_no) AS m FROM generations WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None or row["m"] is None:
            return -1
        return int(row["m"])

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        row = self._con.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def get_generations(self, run_id: str) -> list:
        rows = self._con.execute(
            "SELECT * FROM generations WHERE run_id = ? ORDER BY gen_no", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_cumulative_generation_count(self, run_id: str) -> int:
        """이 run에 기록된 총 세대 수 (cost-cap 판정에 사용)."""
        row = self._con.execute(
            "SELECT COUNT(*) AS c FROM generations WHERE run_id = ?", (run_id,)
        ).fetchone()
        return int(row["c"]) if row is not None else 0

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------
    def _write_snapshot(self, run_id: str, gen_no: int, payload: Dict[str, Any]) -> None:
        path = Path(self.snapshot_dir) / f"{run_id}_g{gen_no}.json"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        except OSError:
            # 스냅샷은 안전장치일 뿐 — 실패해도 DB 기록은 유효하므로 무시.
            pass

    def close(self) -> None:
        try:
            self._con.close()
        except sqlite3.Error:
            pass


def _config_to_dict(config: Any) -> Dict[str, Any]:
    """config를 직렬화 가능한 dict로 변환한다 (to_dict 우선, 아니면 dict/그대로)."""
    if config is None:
        return {}
    to_dict = getattr(config, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(config, dict):
        return config
    return {"repr": repr(config)}


# =====================================================================
# US-007 — 라이브 상태 발행 (current_state.json) + 정지 플래그 (STOP).
#   루프(서브프로세스)와 대시보드(FastAPI)를 잇는 파일 기반 seam이다.
#   계약 스키마는 controller/contract.py: LoopState (pydantic) 참조.
# =====================================================================
def publish_loop_state(state: Any, path: Optional[str] = None) -> None:
    """LoopState(contract) 스냅샷을 current_state.json에 ATOMIC write 한다.

    같은 디렉토리에 `.tmp`로 쓰고 os.replace로 교체해 부분 쓰기(half-written
    JSON)를 폴링 reader가 읽는 것을 막는다. state는 contract.LoopState
    (model_dump_json/ .dict()) 또는 이미 직렬화된 dict 둘 다 받는다.

    발행 실패는 루프를 막지 않는다(라이브 상태는 가시화 보조이지 정확성
    필수 경로가 아니다) — 예외를 흡수한다.
    """
    target = Path(path or CURRENT_STATE_FILE)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # pydantic v2(model_dump_json) → v1(json) → dict 순으로 직렬화.
        dump = getattr(state, "model_dump_json", None)
        if callable(dump):
            text = dump()
        elif hasattr(state, "json") and callable(state.json):
            text = state.json()
        else:
            text = json.dumps(state, ensure_ascii=False)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, target)
    except OSError:
        # 라이브 상태 발행은 안전장치일 뿐 — 실패해도 루프는 계속한다.
        pass


def read_current_state(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """current_state.json을 dict로 읽는다. 없거나 손상이면 None.

    대시보드 GET /status / WS push가 사용한다.
    """
    target = Path(path or CURRENT_STATE_FILE)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def clear_current_state(path: Optional[str] = None) -> None:
    """current_state.json을 제거한다 (idle 복원용)."""
    target = Path(path or CURRENT_STATE_FILE)
    try:
        target.unlink()
    except OSError:
        pass


def set_stop_flag(path: Optional[str] = None) -> str:
    """정지 플래그 파일을 쓴다 (대시보드 stop 제어). 경로를 반환한다.

    루프는 매 세대 시작 전 stop_requested()로 이 파일을 확인한다.
    """
    target = Path(path or STOP_FLAG_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(time.time()), encoding="utf-8")
    return str(target)


def stop_requested(path: Optional[str] = None) -> bool:
    """정지 플래그가 존재하는지 확인한다 (루프가 매 세대 시작 전 호출)."""
    return Path(path or STOP_FLAG_FILE).exists()


def clear_stop_flag(path: Optional[str] = None) -> None:
    """정지 플래그를 제거한다 (루프 시작 시 / 종료 시 cleanup)."""
    try:
        Path(path or STOP_FLAG_FILE).unlink()
    except OSError:
        pass


def to_loop_state(
    summary: Dict[str, Any],
    generations: List[Dict[str, Any]],
    *,
    config: Any = None,
    status: str = "running",
    current_gen: int = -1,
    latest: Optional[Dict[str, Any]] = None,
    cumulative_tokens: int = 0,
) -> Any:
    """루프 요약 + 세대 기록을 contract.LoopState로 빌드한다.

    summary는 run_loop가 반환하는 dict(run_id, best_*, winner_* 등) 형태,
    generations는 LoopState(SQLite).get_generations(run_id) 행 형태를 받는다.
    config는 LoopConfig(provider/bt_timeframe/max_generations) — 없으면 기본값.

    contract.LoopState(pydantic) 인스턴스를 반환한다. publish_loop_state로
    바로 발행 가능하다.
    """
    from ai_strategy_loop.controller import contract as C  # noqa: PLC0415

    provider = str(getattr(config, "provider", "") or "")
    bt_timeframe = str(getattr(config, "bt_timeframe", "") or "")
    max_gen = int(getattr(config, "max_generations", 0) or summary.get("max_generations", 0) or 0)

    best = C.BestInfo(
        gen=int(summary.get("best_gen", -1) if summary.get("best_gen") is not None else -1),
        graded_score=summary.get("best_score"),
        gate_passed=False,  # best는 graded 선택 — 게이트 통과 여부는 행에서 보강.
        buy_name=summary.get("best_buy"),
        sell_name=summary.get("best_sell"),
    )

    winner = None
    if summary.get("winner_gen", -1) is not None and int(summary.get("winner_gen", -1)) >= 0:
        winner = C.WinnerInfo(
            gen=int(summary["winner_gen"]),
            score=summary.get("winner_score"),
            buy_name=summary.get("winner_buy"),
            sell_name=summary.get("winner_sell"),
        )

    # best 세대의 gate_passed를 generations 행에서 보강.
    gen_rows: List[Any] = []
    for g in generations:
        gate_passed = bool(g.get("gate_passed"))
        if int(g.get("gen_no", -1)) == best.gen:
            best.gate_passed = gate_passed
        gen_rows.append(C.GenerationInfo(
            gen_no=int(g.get("gen_no", -1)),
            status=str(g.get("status", "")),
            graded_score=float(g.get("score", 0.0) or 0.0),
            gate_passed=gate_passed,
            gate_reason=str(g.get("reason", "") or ""),
            trade_count=int(g.get("trade_count", 0) or 0),
            mdd=float(g.get("mdd", 0.0) or 0.0),
            profit=float(g.get("profit", 0.0) or 0.0),
            strategy_gist=str(g.get("strategy_gist", "") or ""),
        ))

    latest_info = C.LatestInfo(
        phase=str((latest or {}).get("phase", "")),
        last_checkpoint=str((latest or {}).get("last_checkpoint", "")),
        message=str((latest or {}).get("message", "")),
    )

    return C.LoopState(
        run_id=summary.get("run_id"),
        status=status,
        current_gen=current_gen,
        max_generations=max_gen,
        provider=provider,
        bt_timeframe=bt_timeframe,
        best=best,
        winner=winner,
        generations=gen_rows,
        latest=latest_info,
        cumulative=C.CumulativeInfo(
            tokens=int(cumulative_tokens),
            cost_or_count=len(gen_rows),
        ),
        updated_at=time.time(),
    )
