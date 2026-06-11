"""US-007 — AI strategy loop 대시보드 FastAPI 백엔드.

엔드포인트:
  - GET  /health       → {status, contract_version}
  - GET  /status       → 현재 LoopState (current_state.json 또는 idle 기본값)
  - GET  /config/spec  → config_field_specs (GUI 폼 렌더용)
  - WS   /ws           → 연결 시 현재 LoopState 송신 후 current_state.json
                         변경을 폴링(~1s)해 push. 인바운드 제어 메시지 수신:
                           {"action":"start","config":{...}}
                           {"action":"stop"}
                           {"action":"final_approval", ...}

제어 구현:
  - start          : 루프를 서브프로세스로 기동 (STOP 플래그 선제거).
  - stop           : STOP 플래그 파일을 쓴다 (루프가 세대 시작 전 관측).
  - final_approval : export_winner(...) 호출 (사람 승인 live-deploy 게이트).

CORS는 모두 허용 — Claude Design 프론트엔드가 별도 origin에서 서빙된다.

라이브 상태 seam은 controller/contract.py(LoopState) + controller/state.py
(publish/read/stop helpers)에 정의되어 있다.
"""

from __future__ import annotations

# bootstrap을 가장 먼저 — cli.*/utility.* import 전 env 격리 (export 경로용).
import ai_strategy_loop.bootstrap  # noqa: E402,F401

import asyncio  # noqa: E402
import difflib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.progress_contract import (  # noqa: E402
    build_backtest_progress,
    build_engine_state,
)
from ai_strategy_loop.dashboard.research_api import router as research_router  # noqa: E402
from ai_strategy_loop.fitness.research_criteria import normalize_research_oos_mode, research_mode_payload  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 프론트엔드(Claude Design 산출물) 정적 자산 디렉토리. 모듈 위치 기준 절대 경로로
#   해석해 CWD와 무관하게 동작한다. 이 디렉토리를 /ui 하위에 마운트해 같은 origin에서
#   서빙한다(REST/WS API와 동일 출처 → CORS 우회 + 단일 진입점).
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

# 폴링 주기(초) — current_state.json 변경 감지 → WS push.
_POLL_INTERVAL = 1.0

# 대시보드는 로컬 전용(서버는 127.0.0.1 바인드)이다. CORS를 와일드카드로 열면
#   임의 origin 페이지가 사용자의 로컬 대시보드 API를 호출할 수 있으므로
#   명시적 localhost allowlist로 제한한다(allow_credentials=False 유지).
_DASHBOARD_PORT = 8770
_ALLOWED_ORIGINS = [
    f"http://localhost:{_DASHBOARD_PORT}",
    f"http://127.0.0.1:{_DASHBOARD_PORT}",
    "http://localhost",
    "http://127.0.0.1",
]
_PROMPT_HEAD_CHARS = 240


class LoopProcessManager:
    """루프 서브프로세스 핸들을 in-process로 관리하는 단순 매니저.

    한 번에 하나의 루프만 추적한다(MVP). start는 STOP 플래그를 먼저 지우고
    `python -m ai_strategy_loop.controller.loop --config-json <...>` 를 띄운다.
    """

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """루프를 서브프로세스로 기동한다. 이미 running이면 거부.

        P6 — 대시보드가 추적하는 자식(is_running)뿐 아니라, **cross-process 락**도
        확인한다. LoopProcessManager는 이 대시보드 인스턴스 한정 보호라, 다른
        진입점(CLI 또는 다른 대시보드 프로세스)이 이미 루프를 돌리는 경우를 못 본다.
        runlock.is_locked()로 그 경우까지 막아 같은 state/DB 동시 쓰기를 차단한다.
        실제 락 획득/해제는 자식 run_loop가 소유한다(여기선 사전 거부만).
        """
        if self.is_running():
            return {"status": "error", "message": "loop already running"}

        # cross-process 락: 살아있는 다른 루프(CLI/타 GUI)가 보유 중이면 거부.
        from ai_strategy_loop.controller.runlock import is_locked  # noqa: PLC0415

        if is_locked():
            return {
                "status": "error",
                "message": "다른 루프가 실행 중입니다(cross-process 락 보유). 동시 실행 차단.",
            }

        # 설정 검증 (CLI=GUI 동일 경로). 잘못된 값이면 여기서 막는다.
        try:
            cfg = config_from_dict(config_dict)
        except ValueError as exc:
            return {"status": "error", "message": f"invalid config: {exc}"}

        # 기동 전 잔여 STOP 플래그 제거 (즉시 정지 방지).
        S.clear_stop_flag()

        env = dict(os.environ)
        env.setdefault("STOM_ALLOW_MINIMAL_SETTING", "1")
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable, "-m", "ai_strategy_loop.controller.loop",
            "--config-json", json.dumps(cfg.to_dict(), ensure_ascii=False),
        ]
        self._proc = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env)
        return {"status": "ok", "pid": self._proc.pid}

    def stop(self, *, grace: float = 10.0) -> Dict[str, Any]:
        """STOP 플래그를 써서 깔끔한 종료를 요청하고, 안 멈추면 강제 종료한다.

        1) STOP 플래그를 쓴다(루프가 세대 시작 전 관측 → 깔끔히 종료).
        2) grace 동안 자식이 스스로 끝나길 기다린다.
        3) 여전히 살아 있으면 hard_stop()으로 terminate→kill→reap 해서
           오펀 백테스트를 남기지 않는다.
        """
        path = S.set_stop_flag()
        reaped = self.hard_stop(grace=grace)
        return {"status": "ok", "stop_flag": path, "reaped": reaped}

    def hard_stop(self, *, grace: float = 10.0) -> bool:
        """실행 중인 자식을 terminate→(grace 대기)→kill→wait 로 강제 회수한다.

        오펀 방지: 서버 종료/강제 정지 시 자식 백테스트가 남지 않도록 반드시
        wait()으로 좀비를 reap 한다. 추적 중인 자식이 없거나 이미 종료됐으면
        조용히 False를 반환한다(회수할 것 없음). 회수했으면 True.
        """
        proc = self._proc
        if proc is None:
            return False
        if proc.poll() is not None:
            self._proc = None
            return False
        try:
            proc.terminate()
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except OSError:
            # 이미 죽었거나 회수 불가 — 그래도 핸들은 비워 다음 start를 허용한다.
            pass
        self._proc = None
        return True


def _current_state_payload() -> Dict[str, Any]:
    """current_state.json을 읽어 dict로 반환 (없으면 idle 기본값)."""
    raw = S.read_current_state()
    if raw is not None:
        try:
            return _with_observability_defaults(C.LoopState.model_validate(raw).model_dump())
        except ValidationError:
            return raw
    return C.idle_state().model_dump()


def _with_observability_defaults(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fill dashboard-only observability fields for legacy current_state snapshots."""
    latest = payload.get("latest")
    if not isinstance(latest, dict):
        return payload

    active_config_raw = payload.get("active_config")
    active_config = dict(active_config_raw) if isinstance(active_config_raw, dict) else {}
    try:
        config = config_from_dict(active_config)
    except ValueError:
        config = config_from_dict({})

    status = str(payload.get("status") or "")
    current_gen = int(payload.get("current_gen") or -1)
    max_generations = int(payload.get("max_generations") or 0)
    phase = str(latest.get("phase") or "")
    bt_timeframe = str(payload.get("bt_timeframe") or getattr(config, "bt_timeframe", "") or "")

    latest["backtest_progress"] = build_backtest_progress(
        config=config,
        latest=latest,
        status=status,
        current_gen=current_gen,
        max_generations=max_generations,
        phase=phase,
        phase_started_at=float(latest.get("phase_started_at") or 0.0),
        bt_timeframe=bt_timeframe,
        now=time.time(),
    )
    latest["engine_state"] = build_engine_state(
        config=config,
        latest=latest,
        active_config=active_config,
        status=status,
        current_gen=current_gen,
        phase=phase,
    )
    return payload


def _runs_payload(run_ids: Optional[list]) -> Dict[str, Any]:
    """loop_runs.db를 열어 run 비교 요약을 만든다(읽기 전용, 무예외).

    lineage.compare_runs를 호출하고 LoopState 연결을 반드시 닫는다. DB 부재/조회
    실패는 빈 목록으로 표준화한다(대시보드 콘솔이 깨지지 않게).
    """
    from ai_strategy_loop.controller.lineage import compare_runs  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        result = compare_runs(st, run_ids)
        _attach_run_labels(result)
        return result
    except Exception as exc:  # noqa: BLE001 - run 비교 조회 실패는 빈 목록으로.
        return {"runs": [], "count": 0, "error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass


def _attach_run_labels(result: Dict[str, Any]) -> None:
    """D5 — run 목록에 대표 라벨(strategy_gist)을 덧붙인다(읽기 전용·무예외).

    배치 평가 run(예: cldgen_*)은 세대 라벨(BASE_SEED/C7_SEEDPLUS …)이 정체성이다.
    run별 첫 비어있지 않은 gist를 label로, 고유 gist 목록(최대 8)을 labels로 노출한다.
    실패는 조용히 무시한다(라벨은 장식 — 기존 응답 키 불변).
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    runs = result.get("runs") if isinstance(result, dict) else None
    if not runs:
        return
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        try:
            rows = con.execute(
                "SELECT run_id, strategy_gist FROM generations"
                " WHERE strategy_gist IS NOT NULL AND strategy_gist != ''"
                " ORDER BY gen_no"
            ).fetchall()
        finally:
            con.close()
        first_gist: Dict[str, str] = {}
        gists: Dict[str, list] = {}
        for rid, gist in rows:
            first_gist.setdefault(rid, gist)
            bucket = gists.setdefault(rid, [])
            if gist not in bucket:
                bucket.append(gist)
        for row in runs:
            rid = row.get("run_id")
            if rid in first_gist:
                row["label"] = first_gist[rid]
                row["labels"] = gists[rid][:8]
    except Exception:  # noqa: BLE001 - 라벨 실패해도 목록은 그대로.
        return


def _row_for_gen(run_id: str, gen_no: int) -> Optional[Dict[str, Any]]:
    """run/gen 한 행(csv_path 포함)을 dict로 읽는다(읽기 전용, 실패 None)."""
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            row = con.execute(
                "SELECT gen_no, status, score, gate_passed, reason, profit,"
                " total_profit_pct, mdd, trade_count, daily_avg_trades, payoff_ratio,"
                " max_hold_count, buy_name, sell_name, csv_path, strategy_gist"
                " FROM generations WHERE run_id=? AND gen_no=?",
                (run_id, int(gen_no)),
            ).fetchone()
        finally:
            con.close()
        return dict(row) if row is not None else None
    except Exception:  # noqa: BLE001
        return None


def _yearly_detail_from_csv(csv_path: str) -> list:
    """per-trade CSV에서 연도별 {year, trades, profit, win_rate}를 만든다(graceful)."""
    try:
        import pandas as pd  # noqa: PLC0415

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "매수시간" not in df.columns or "수익금" not in df.columns:
            return []
        years = df["매수시간"].astype(str).str[:4]
        result = []
        for year, group in df.groupby(years):
            profits = group["수익금"].astype(float)
            wins = (group["수익률"].astype(float) > 0) if "수익률" in df.columns else (profits > 0)
            result.append({
                "year": str(year),
                "trades": int(len(group)),
                "profit": float(profits.sum()),
                "win_rate": round(float(wins.mean()), 4),
            })
        return result
    except Exception:  # noqa: BLE001
        return []


def _run_yearly_payload(run_id: str) -> Dict[str, Any]:
    """D1 — run의 세대별 연도 분해(거래수·손익·승률)를 만든다(읽기 전용·무예외).

    근거(2026-06-10 원인5): 시드 알파의 연도별 쇠퇴(+4.88M→+3.37M→+0.38M→2026 적자)는
    합계만 봐서는 보이지 않는다. generations.csv_path의 per-trade CSV(매수시간·수익금·
    수익률)를 연도로 집계한다 — 추가 백테 0회. CSV 부재/파싱 실패는 빈 분해로 표준화.
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    out: Dict[str, Any] = {"run_id": run_id, "generations": [], "count": 0}
    if not run_id:
        return out
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT gen_no, status, buy_name, strategy_gist, csv_path, profit,"
                " trade_count FROM generations WHERE run_id=? ORDER BY gen_no",
                (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out

    for row in rows:
        d = dict(row)
        entry: Dict[str, Any] = {
            "gen_no": d["gen_no"],
            "buy_name": d.get("buy_name"),
            "label": d.get("strategy_gist") or "",
            "status": d.get("status"),
            "total_profit": d.get("profit"),
            "trade_count": d.get("trade_count"),
            "years": _yearly_detail_from_csv(d.get("csv_path") or "") if d.get("csv_path") else [],
        }
        out["generations"].append(entry)
    out["count"] = len(out["generations"])
    return out


def _autopsy_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """D2 — 세대 CSV에 공식 부검(진입/청산)을 적용해 NL 요약을 반환한다(읽기 전용·무예외).

    autopsy.analyze_trades/analyze_exits + summarize — 루프가 프롬프트 환류로만 쓰던
    분석을 사람이 대시보드에서 직접 본다("왜 졌는지"). 실패/부족은 status로 표준화.
    """
    out: Dict[str, Any] = {
        "run_id": run_id, "gen_no": gen_no,
        "entry_summary": "", "exit_summary": "", "status": "unavailable",
    }
    row = _row_for_gen(run_id, gen_no)
    if row is None:
        return out
    out["buy_name"] = row.get("buy_name")
    out["label"] = row.get("strategy_gist") or ""
    csv_path = row.get("csv_path") or ""
    if not csv_path:
        out["status"] = "no_csv"
        return out
    try:
        from ai_strategy_loop.autopsy.analyze import analyze_exits, analyze_trades  # noqa: PLC0415
        from ai_strategy_loop.autopsy.summarize import summarize, summarize_exits  # noqa: PLC0415

        entry = analyze_trades(csv_path)
        exits = analyze_exits(csv_path)
        out["entry_summary"] = summarize(entry) or ""
        out["exit_summary"] = summarize_exits(exits) or ""
        out["entry_status"] = getattr(entry, "status", "")
        out["exit_status"] = getattr(exits, "status", "")
        out["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def _selector_preview_payload(run_id: str, selector: str) -> Dict[str, Any]:
    """D4 — run 행에 선택기를 진단 적용해 동결 가능 후보를 미리 본다(읽기 전용·무예외).

    근거(2026-06-10 원인1): 기준-목표 비정합(시드조차 탈락)을 눈으로 확인하는 도구.
    sparse_positive_v1 | seed_relative_v1 지원. 베이스라인(BASE_*)은 후보에서 출처
    기준으로 제외하되 seed_relative의 시드 프로파일로 쓴다. **진단 전용 — 아무것도
    쓰지 않으며 동결 아티팩트가 아니다.**
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    out: Dict[str, Any] = {
        "run_id": run_id, "selector": selector or "sparse_positive_v1",
        "diagnostic_only": True, "selected": False, "eligible": [], "rejected": [],
    }
    if not run_id:
        return out
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT gen_no, status, score, gate_passed, reason, profit,"
                " total_profit_pct, mdd, trade_count, daily_avg_trades, payoff_ratio,"
                " max_hold_count, buy_name, sell_name, csv_path, strategy_gist"
                " FROM generations WHERE run_id=? ORDER BY gen_no",
                (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out

    try:
        from ai_strategy_loop.controller.candidate_selection import (  # noqa: PLC0415
            SeedProfile,
            parse_candidate_generation,
            select_seed_relative_v1,
            select_sparse_positive_v1,
        )

        candidates, labels = [], {}
        seed_profile = None
        for r in rows:
            d = dict(r)
            gist = d.pop("strategy_gist", "") or ""
            labels[int(d.get("gen_no") or 0)] = gist
            d["gate_passed"] = bool(d.get("gate_passed"))
            for k in ("payoff_ratio", "max_hold_count", "profit", "mdd",
                      "daily_avg_trades", "score"):
                if d.get(k) is None:
                    d[k] = 0.0
            if d.get("csv_path") is None:
                d["csv_path"] = ""
            if gist == "BASE_SEED" and seed_profile is None and d.get("status") == "ok":
                seed_profile = SeedProfile(
                    mdd=float(d["mdd"]), trade_count=int(d["trade_count"]),
                    profit=float(d["profit"]), source=f"BASE_SEED of {run_id}",
                )
            if gist.startswith("BASE_"):
                continue
            candidates.append(parse_candidate_generation(d))

        if (selector or "") == "seed_relative_v1":
            res = select_seed_relative_v1(
                candidates, run_id=run_id, config_path="", config_hash="",
                seed_profile=seed_profile, diagnostic_only=True,
            )
            out["selector"] = "seed_relative_v1"
            out["mdd_limit"] = res.mdd_limit
            out["seed_profile"] = (
                {"mdd": seed_profile.mdd, "trade_count": seed_profile.trade_count}
                if seed_profile else None
            )
        else:
            out["selector"] = "sparse_positive_v1"
            res = select_sparse_positive_v1(
                candidates, run_id=run_id, config_path="", config_hash="",
                diagnostic_only=True,
            )
        out["selected"] = bool(res.selected)
        if res.selected_candidate is not None:
            c = res.selected_candidate
            out["selected_candidate"] = {
                "gen_no": c.gen_no, "label": labels.get(c.gen_no, ""),
                "buy_name": c.buy_name, "sell_name": c.sell_name,
                "profit": c.profit, "mdd": c.mdd, "trade_count": c.trade_count,
                "payoff_ratio": c.payoff_ratio,
            }
        out["eligible"] = [
            {"gen_no": e.gen_no, "label": labels.get(e.gen_no, "")}
            for e in res.eligible_candidates
        ]
        out["rejected"] = [
            {"gen_no": rj.gen_no, "label": labels.get(rj.gen_no, ""),
             "reasons": list(rj.reasons)}
            for rj in res.rejected_candidates
        ]
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    return out


def _generation_durations_payload(run_id: Optional[str] = None) -> Dict[str, Any]:
    """세대별 소요초를 인접 created_at 차분으로 산출한다(#64, 읽기 전용·무예외).

    generations.created_at은 각 세대 *종료* 시각(record_generation 시 _now())이 영속된다.
    따라서 gen[i] 소요 = created_at[i] - created_at[i-1]. 첫 세대(i=0)는 이전 세대가 없으니
    runs.started_at(run 시작 시각)으로 보정해 created_at[0] - started_at를 쓴다. 이 방식은
    추가 백테 0회이고, LIVE 발행이 없던 과거 run(예: reframe1)에도 retroactive하게 작동한다
    (DB에 이미 created_at/started_at가 있으므로).

    run_id가 주어지면 그 run만, 없으면 모든 run을 산출한다. DB 부재/조회 실패/이상치는
    빈 목록·None으로 표준화한다(무예외 — 대시보드가 깨지지 않게). 음수 차(시계 역행/UPSERT
    재기록)는 None으로 둔다(잘못된 소요 표시 방지).

    반환: {"durations": [{"run_id","gen_no","duration_sec","created_at","status"}], "count": N}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        all_gens = st.get_all_generations()
        runs = {r.get("run_id"): r for r in st.list_runs()}
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답.
        return {"durations": [], "count": 0}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # run별로 gen_no 순 그룹핑(인접 차분을 같은 run 안에서만 계산).
    by_run: Dict[str, list] = {}
    for g in all_gens:
        rid = g.get("run_id")
        if run_id and rid != run_id:
            continue
        by_run.setdefault(rid, []).append(g)

    run_context: Dict[str, Dict[str, Any]] = {}
    for rid, row in runs.items():
        cfg_json = (row or {}).get("config_json")
        cfg: Dict[str, Any] = {}
        if cfg_json:
            try:
                parsed = json.loads(str(cfg_json))
                if isinstance(parsed, dict):
                    cfg = parsed
            except (ValueError, TypeError):
                cfg = {}
        run_context[rid] = {
            "period": _period_string_from_config(cfg_json),
            "timeframe": cfg.get("bt_timeframe"),
        }

    durations: list = []
    for rid, gens in by_run.items():
        gens_sorted = sorted(gens, key=lambda g: int(g.get("gen_no", 0) or 0))
        started_at = (runs.get(rid) or {}).get("started_at")
        prev_created = float(started_at) if started_at is not None else None
        for g in gens_sorted:
            created = g.get("created_at")
            duration_sec: Optional[float] = None
            if created is not None and prev_created is not None:
                delta = float(created) - float(prev_created)
                # 음수(시계 역행/재기록)는 None으로 — 잘못된 소요 표시 방지.
                duration_sec = delta if delta >= 0.0 else None
            # gen_no는 0이 유효값이므로 `or -1`(0을 falsy로 떨구는 버그) 금지 — None만 -1.
            _gen_no = g.get("gen_no")
            durations.append({
                "run_id": rid,
                "gen_no": (-1 if _gen_no is None else int(_gen_no)),
                "duration_sec": duration_sec,
                "created_at": (None if created is None else float(created)),
                "status": str(g.get("status", "") or ""),
                **run_context.get(rid, {}),
            })
            if created is not None:
                prev_created = float(created)

    return {"durations": durations, "count": len(durations)}


def _equity_curves_payload(
    cap: int = 200, downsample: int = 200, run_id: Optional[str] = None
) -> Dict[str, Any]:
    """loop_runs.db의 세대 equity curve를 읽어 반환한다(읽기 전용, 무예외).

    run_id가 주어지면 그 run의 세대만 반환한다 — 전체 이력에는 과발화 폭망 곡선
    (±수십억)이 섞여 있어, 그것까지 한 차트에 그리면 정상 곡선이 y스케일에 압착돼
    0선에 한 줄처럼 뭉개진다. 현재 보고 있는 run만 보내면 스케일이 정상화된다.
    run_id 미지정이면 전체(하위호환).

    각 세대의 csv_path로 load_equity_series_from_csv를 호출해 수익금합계 시계열을
    얻는다. 곡선이 많으면 최근 cap 개로 제한하고, 곡선당 포인트는 downsample 개로
    줄인다. CSV 없거나 파싱 실패한 세대는 건너뛴다. DB 없으면 빈 응답(무예외).

    반환: {"curves": [{"run_id","gen_no","gate_passed","final_pct","equity":[...]}], "count": N}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.score import load_equity_series_from_csv  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        all_gens = st.get_all_generations()
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답.
        return {"curves": [], "count": 0}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # created_at 내림차순(최신 우선).
    sorted_gens = sorted(all_gens, key=lambda g: g.get("created_at") or 0, reverse=True)
    # run_id가 주어지면 해당 run만(현재 보고 있는 run의 곡선만 정상 스케일로 표시).
    if run_id:
        sorted_gens = [g for g in sorted_gens if g.get("run_id") == run_id]
    candidates = sorted_gens[:cap]

    curves = []
    for g in candidates:
        csv_path = g.get("csv_path")
        if not csv_path:
            continue
        try:
            equity_raw = load_equity_series_from_csv(str(csv_path))
        except Exception:  # noqa: BLE001 - CSV 없거나 파싱 실패는 skip.
            continue
        if not equity_raw:
            continue
        # 다운샘플: 포인트 수가 downsample 초과면 균등 간격으로 추려 payload 축소.
        if len(equity_raw) > downsample:
            step = len(equity_raw) / downsample
            equity_ds = [equity_raw[int(i * step)] for i in range(downsample)]
            equity_ds.append(equity_raw[-1])  # 마지막 값 보존.
        else:
            equity_ds = equity_raw
        curves.append({
            "run_id": g.get("run_id", ""),
            "gen_no": int(g.get("gen_no", -1)),
            "gate_passed": bool(g.get("gate_passed")),
            "final_pct": float(g.get("total_profit_pct") or 0.0),
            "equity": [float(v) for v in equity_ds],
        })

    return {"curves": curves, "count": len(curves)}


_REFERENCE_STRATEGIES_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "reference_strategies.json"
)

# 인간 reference 결과 스크린샷 디렉토리(REPO_ROOT 기준). 읽기 전용으로 /reference_img에
#   StaticFiles 마운트하고, /reference_screenshots가 이 디렉토리의 이미지 파일명을 나열한다.
#   이 디렉토리만 노출하며(다른 디렉토리 노출 금지) 디렉토리가 없으면 마운트를 스킵한다.
_REFERENCE_SCREENSHOTS_DIR = os.path.join(REPO_ROOT, "docs", "reference", "STOM_Good_Results")

# 갤러리에 표시할 이미지 확장자. 결과 스크린샷은 .png 17장이 정본이다. 같은 #1의
#   .jpg/.jpeg 중복 포맷 변환본은 동일 화면이라 갤러리 노이즈가 되므로 .png만 노출한다
#   (StaticFiles 마운트 자체는 디렉토리 전체를 읽기 전용 서빙하므로 직접 URL 접근엔 영향 없음).
_SCREENSHOT_EXTS = (".png",)


def _reference_screenshots() -> list:
    """인간 reference 결과 스크린샷 파일명 목록을 반환한다(읽기 전용, 무예외).

    _REFERENCE_SCREENSHOTS_DIR의 최상위(서브디렉토리 미탐색) .png 결과 스크린샷만 나열한다.
    분석용 파생 크롭/줌(언더스코어 `_`로 시작하는 보조 파일: `_zoom_*`, `_crops` 등)은
    실제 결과 스크린샷이 아니므로 제외한다. #1의 .jpg/.jpeg 중복 포맷본도 .png 정본과
    같은 화면이라 제외해(확장자 화이트리스트=.png) 갤러리가 결과 화면 17장만 브라우징하게 한다.
    파일명만(경로 제외) 정렬해 돌려준다 — 프론트가 baseUrl+'/reference_img/'+filename으로
    StaticFiles에서 직접 가져온다. 디렉토리 부재/조회 실패는 빈 목록으로 표준화한다(무예외).
    """
    try:
        entries = os.listdir(_REFERENCE_SCREENSHOTS_DIR)
    except OSError:
        return []
    out = []
    for name in entries:
        if name.startswith("_"):
            continue  # 분석용 파생 크롭/줌(보조 파일) 제외 — 결과 스크린샷만.
        if not name.lower().endswith(_SCREENSHOT_EXTS):
            continue
        try:
            full = os.path.join(_REFERENCE_SCREENSHOTS_DIR, name)
            if not os.path.isfile(full):
                continue  # 서브디렉토리(_crops 등)는 제외.
        except OSError:
            continue
        out.append(name)
    return sorted(out)


def _load_reference_strategies() -> list:
    """reference_strategies.json을 읽어 인간 벤치마크 목록을 반환한다(읽기 전용, 무예외).

    파일은 이 모듈 기준 dashboard/reference_strategies.json. 파일 부재/JSON 파싱
    실패는 빈 목록으로 표준화한다(대시보드가 빈 상태를 표시). 각 항목을 명예의
    전당 공통 스키마(label·total_return_krw·total_return_pct·annual_return_pct·
    mdd_pct·payoff·trades·daily_avg_trades·max_holdings·operating_capital_krw·
    kind='human')로 매핑한다.
    """
    try:
        with open(_REFERENCE_STRATEGIES_JSON, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError, TypeError):
        return []

    strategies = (raw or {}).get("strategies") or []
    out: list = []
    for s in strategies:
        if not isinstance(s, dict):
            continue
        out.append({
            "kind": "human",
            "label": str(s.get("id") or ""),
            "period": s.get("period"),
            "days": s.get("days"),
            "operating_capital_krw": s.get("operating_capital_krw"),
            "total_return_krw": s.get("profit_krw"),
            "total_return_pct": s.get("total_return_pct"),
            "annual_return_pct": s.get("annual_return_pct"),
            "annual_unreliable": False,
            "mdd_pct": s.get("mdd_pct"),
            "payoff": s.get("payoff"),
            "trades": s.get("trades"),
            "daily_avg_trades": s.get("daily_avg_trades"),
            "max_holdings": s.get("max_holdings"),
            "win_rate_pct": s.get("win_rate_pct"),
        })
    return out


def _window_years_from_config(config_json: Optional[str]) -> Optional[float]:
    """runs.config_json의 bt_full_start/bt_full_end(YYYYMMDD 정수)에서 창 길이(년)를 구한다.

    (date(end) − date(start)).days / 365.25. 파싱 실패/필드 부재/비정상 값은 None
    으로 표준화한다(연평균을 산출하지 못함 → 호출부가 None 처리). 무예외.
    """
    from datetime import date  # noqa: PLC0415

    if not config_json:
        return None
    try:
        cfg = json.loads(config_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):  # 비-dict JSON(리스트/스칼라) → None(무예외 보장).
        return None
    start_i = cfg.get("bt_full_start")
    end_i = cfg.get("bt_full_end")
    if start_i is None or end_i is None:
        return None
    try:
        si, ei = int(start_i), int(end_i)
        start = date(si // 10000, (si // 100) % 100, si % 100)
        end = date(ei // 10000, (ei // 100) % 100, ei % 100)
    except (ValueError, TypeError):
        return None
    days = (end - start).days
    if days <= 0:
        return None
    return days / 365.25


def _period_string_from_config(config_json: Optional[str]) -> Optional[str]:
    """runs.config_json의 bt_full_start/end(YYYYMMDD 정수)를 'YYYY-MM-DD ~ YYYY-MM-DD'로 포맷한다.

    명예의 전당 '백테 기간' 컬럼용. 인간 전략은 reference_strategies.json의 period 문자열을
    그대로 쓰고, AI 전략은 이 헬퍼로 run 창에서 동일 포맷의 기간 문자열을 만든다.
    파싱 실패/필드 부재/비정상 값(end<=start)은 None으로 표준화한다(컬럼이 '—' 표시). 무예외.
    """
    from datetime import date  # noqa: PLC0415

    if not config_json:
        return None
    try:
        cfg = json.loads(config_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):  # 비-dict JSON(리스트/스칼라) → None(무예외 보장).
        return None
    start_i = cfg.get("bt_full_start")
    end_i = cfg.get("bt_full_end")
    if start_i is None or end_i is None:
        return None
    try:
        si, ei = int(start_i), int(end_i)
        start = date(si // 10000, (si // 100) % 100, si % 100)
        end = date(ei // 10000, (ei // 100) % 100, ei % 100)
    except (ValueError, TypeError):
        return None
    if (end - start).days <= 0:
        return None
    return f"{start.isoformat()} ~ {end.isoformat()}"


def _hall_of_fame_payload(ai_limit: int = 30) -> Dict[str, Any]:
    """명예의 전당 payload: 인간 벤치마크 + AI 생성 통합(읽기 전용, 무예외).

    인간: reference_strategies.json을 로드한다(파일 없으면 빈 목록).
    AI: loop_runs.db에서 gate_passed=1 AND profit>0 세대를 조회해 워크플로 확정
        산식으로 매핑한다(추가 백테 0회).
          - operating_capital_krw = profit / total_profit_pct × 100
            (total_profit_pct는 '운영금 대비 수익률합계'. ≤0이면 그 행 제외).
          - total_return_krw = profit (수익금합계, 원).
          - total_return_pct = total_profit_pct (이미 DB; profit/운영금×100).
          - annual_return_pct = total_return_pct / window_years (단리).
            window_years는 runs.config_json의 bt_full_start/end에서 산출. <0.25면
            annual_unreliable=true(짧은 창 연환산 과대) + 연평균은 그대로 계산.
            window를 못 구하면 annual_return_pct=None.
        graded(score) 내림차순 상위 ai_limit.

    LoopState 무예외·close() 패턴은 _equity_curves_payload/_runs_payload와 동일.
    DB/JSON 부재는 빈 목록(무예외).

    반환: {"human": [...], "ai": [...]}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    human = _load_reference_strategies()

    st: Optional[LoopState] = None
    all_gens: list = []
    run_window_cache: Dict[str, Optional[float]] = {}
    run_period_cache: Dict[str, Optional[str]] = {}
    try:
        st = LoopState()
        all_gens = st.get_all_generations()
        # 각 run의 창 길이(년)·기간 문자열을 한 번씩 조회해 캐시한다(연평균·백테기간 산출용).
        run_ids = {str(g.get("run_id") or "") for g in all_gens if g.get("run_id")}
        for rid in run_ids:
            run_row = st.get_run(rid)
            cfg_json = run_row.get("config_json") if run_row else None
            run_window_cache[rid] = _window_years_from_config(cfg_json)
            run_period_cache[rid] = _period_string_from_config(cfg_json)
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 AI 빈 목록(무예외).
        return {"human": human, "ai": []}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    ai: list = []
    for g in all_gens:
        if not bool(g.get("gate_passed")):
            continue
        profit = g.get("profit")
        total_pct = g.get("total_profit_pct")
        if profit is None or total_pct is None:
            continue
        try:
            profit_f = float(profit)
            total_pct_f = float(total_pct)
        except (ValueError, TypeError):
            continue
        # 흑자(profit>0) + 수익률합계>0(운영금 역산 가능)인 세대만.
        if profit_f <= 0 or total_pct_f <= 0:
            continue

        # 운영금 역산: profit / total_profit_pct × 100 (total_profit_pct=운영금대비%).
        operating_capital = profit_f / total_pct_f * 100.0

        run_id = str(g.get("run_id") or "")
        gen_no = int(g.get("gen_no", -1))
        window_years = run_window_cache.get(run_id)
        period_str = run_period_cache.get(run_id)
        if window_years and window_years > 0:
            annual_pct = total_pct_f / window_years
            annual_unreliable = window_years < 0.25
        else:
            annual_pct = None
            annual_unreliable = False

        # 시드(Tick_902 등 비-AILOOP, 주로 gen0)는 인간이 튜닝한 출발점이고, AILOOP_*만
        #   AI가 직접 생성한 전략이다. 사용자가 "AI가 직접 한것"과 인간 시드를 구분해 보도록
        #   kind를 나눈다('ai' vs 'seed'). 둘 다 loop_runs.db 출처라 ai 목록에 함께 담는다.
        buy_name_str = str(g.get("buy_name") or "")
        # 시드 = 명명된 비-AILOOP 전략(보통 Tick_902 등 인간 튜닝 gen0). AILOOP_* = AI 생성.
        #   빈 이름은 시드로 확정할 수 없으므로 'ai'로 둔다(시드/AI 구분 정직성).
        kind = "seed" if (buy_name_str and not buy_name_str.startswith("AILOOP")) else "ai"
        ai.append({
            "kind": kind,
            "run_id": run_id,
            "gen_no": gen_no,
            "label": f"{run_id}/g{gen_no}",
            "period": period_str,
            "buy_name": g.get("buy_name"),
            "score": (float(g.get("score")) if g.get("score") is not None else None),
            "operating_capital_krw": operating_capital,
            "total_return_krw": profit_f,
            "total_return_pct": total_pct_f,
            "annual_return_pct": annual_pct,
            "annual_unreliable": annual_unreliable,
            "mdd_pct": (float(g.get("mdd")) if g.get("mdd") is not None else None),
            "calmar": (float(g.get("calmar")) if g.get("calmar") is not None else None),
            "payoff": (float(g.get("payoff_ratio")) if g.get("payoff_ratio") is not None else None),
            "trades": (int(g.get("trade_count")) if g.get("trade_count") is not None else None),
            "daily_avg_trades": (
                float(g.get("daily_avg_trades")) if g.get("daily_avg_trades") is not None else None
            ),
            "max_hold_count": (
                float(g.get("max_hold_count")) if g.get("max_hold_count") is not None else None
            ),
        })

    # graded(score) 내림차순 상위 ai_limit.
    ai.sort(key=lambda r: (
        (r.get("score") if r.get("score") is not None else -1e18),
        r.get("run_id") or "", r.get("gen_no") or 0,
    ), reverse=True)  # score 동률 시 (run_id, gen_no)로 결정론적 순서(cap 경계 안정).
    ai = ai[: max(0, int(ai_limit))]

    return {"human": human, "ai": ai}


def _strategy_code_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """루프 DB에서 한 세대의 매수/매도 전략 코드를 조회한다(읽기 전용, 무예외).

    P10 — 대시보드 코드 뷰어가 fetch 한다. 세대 행(generations)의 실제 buy_name/
    sell_name을 먼저 읽어(시드 세대는 seed 이름, 일반 세대는 AILOOP_<run>_g<gen>_*),
    그 이름으로 loop.py의 _read_strategy_code(stockbuy/stocksell의 "전략코드")를
    재사용해 코드를 가져온다. 행이 없으면 namespaced 기본 이름으로 폴백한다.

    조회 실패/미존재는 빈 문자열로 표준화한다(대시보드가 "코드가 없습니다"를 표시).
    """
    from ai_strategy_loop.controller.loop import _read_strategy_code  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    buy_name = f"AILOOP_{run_id}_g{gen_no}_buy"
    sell_name = f"AILOOP_{run_id}_g{gen_no}_sell"
    generation_found = False
    # 세대 행에서 실제 전략 이름을 읽는다(시드 세대는 seed 이름일 수 있음).
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for row in st.get_generations(run_id):
            if int(row.get("gen_no", -1)) == int(gen_no):
                generation_found = True
                buy_name = row.get("buy_name") or buy_name
                sell_name = row.get("sell_name") or sell_name
                break
    except Exception:  # noqa: BLE001 - 행 조회 실패는 namespaced 기본 이름으로 폴백.
        pass
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    buy_code = _read_strategy_code(buy_name, "buy") or ""
    sell_code = _read_strategy_code(sell_name, "sell") or ""
    code_status = "ok"
    reason: Optional[str] = None
    if not buy_code and not sell_code:
        if not generation_found:
            code_status = "missing_generation"
            reason = "missing_generation"
        else:
            code_status = "empty_code"
            reason = "empty_code"
    return {
        "ok": True,
        "run_id": run_id,
        "gen": int(gen_no),
        "gen_no": int(gen_no),
        "buy_name": buy_name,
        "sell_name": sell_name,
        "buy_code": buy_code,
        "sell_code": sell_code,
        "code_status": code_status,
        "reason": reason,
    }


def _prompt_row_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 행을 해시/메타데이터 + 제한된 user head로 변환한다."""
    user_text = str(row.get("user_text") or "")
    features_raw = row.get("injected_features")
    injected_features = None
    if features_raw:
        try:
            injected_features = json.loads(str(features_raw))
        except (ValueError, TypeError):
            injected_features = None
    return {
        "prompt_id": row.get("prompt_id"),
        "run_id": row.get("run_id"),
        "gen_no": row.get("gen_no"),
        "kind": row.get("kind"),
        "attempt": row.get("attempt"),
        "system_sha": row.get("system_sha"),
        "user_sha": row.get("user_sha"),
        "user_text_head": user_text[:_PROMPT_HEAD_CHARS],
        "user_text_len": len(user_text),
        "injected_features": injected_features,
        "prior_error": row.get("prior_error"),
        "model": row.get("model"),
        "prompt_tokens": row.get("prompt_tokens"),
        "completion_tokens": row.get("completion_tokens"),
        "total_tokens": row.get("total_tokens"),
        "response_sha": row.get("response_sha"),
        "created_at": row.get("created_at"),
    }


def _prompts_payload(run_id: Optional[str], gen_no: Optional[int] = None) -> Dict[str, Any]:
    """저장된 프롬프트를 조회한다. 전문 대신 head/hash만 반환한다."""
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required", "prompts": []}
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        rows = st.get_prompts(run_id)
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc), "run_id": run_id, "gen_no": gen_no, "prompts": []}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if gen_no is not None:
        rows = [row for row in rows if int(row.get("gen_no", -1)) == int(gen_no)]
    prompts = [_prompt_row_payload(row) for row in rows]
    reason = None if prompts else "prompt_logging_not_enabled_or_no_records"
    return {"run_id": run_id, "gen_no": gen_no, "prompts": prompts, "reason": reason}


def _diff_lines(base_code: str, code: str, base_name: str, name: str) -> List[str]:
    """매수/매도 전략 코드 두 버전의 unified diff line 배열을 만든다."""
    if not base_code and not code:
        return []
    return list(difflib.unified_diff(
        (base_code or "").splitlines(),
        (code or "").splitlines(),
        fromfile=base_name or "base",
        tofile=name or "current",
        lineterm="",
    ))


def _parse_base_gen(gen_no: int, base_gen: str) -> Optional[int]:
    """base_gen 쿼리를 해석한다. gen0의 previous는 base 없음."""
    if base_gen == "previous":
        return int(gen_no) - 1 if int(gen_no) > 0 else None
    try:
        return int(base_gen)
    except (TypeError, ValueError):
        return None


def _strategy_diff_payload(
    run_id: Optional[str], gen_no: int, base_gen: str = "previous"
) -> Dict[str, Any]:
    """현재 세대와 base 세대의 매수/매도 코드와 diff를 반환한다."""
    if not run_id:
        return {"error": "run_id required", "prompts": []}

    current = _strategy_code_payload(run_id, int(gen_no))
    base_no = _parse_base_gen(int(gen_no), str(base_gen))
    prompts = _prompts_payload(run_id, int(gen_no)).get("prompts", [])
    current_status = str(current.get("code_status") or "")
    if current_status == "missing_generation":
        return {
            "ok": True,
            "run_id": run_id,
            "gen_no": int(gen_no),
            "buy_name": current.get("buy_name"),
            "sell_name": current.get("sell_name"),
            "buy_code": current.get("buy_code", ""),
            "sell_code": current.get("sell_code", ""),
            "base_gen": base_no,
            "base_buy_name": None,
            "base_sell_name": None,
            "base_buy_code": "",
            "base_sell_code": "",
            "buy_diff": [],
            "sell_diff": [],
            "prompts": prompts,
            "diff_status": "missing_generation",
            "reason": "missing_generation",
        }
    if base_no is None:
        return {
            "ok": True,
            "run_id": run_id,
            "gen_no": int(gen_no),
            "buy_name": current.get("buy_name"),
            "sell_name": current.get("sell_name"),
            "buy_code": current.get("buy_code", ""),
            "sell_code": current.get("sell_code", ""),
            "base_gen": None,
            "base_buy_name": None,
            "base_sell_name": None,
            "base_buy_code": "",
            "base_sell_code": "",
            "buy_diff": [],
            "sell_diff": [],
            "prompts": prompts,
            "diff_status": "no_previous_generation",
            "reason": "no_previous_generation",
        }

    base = _strategy_code_payload(run_id, int(base_no))
    base_status = str(base.get("code_status") or "")
    diff_status = "ok"
    reason: Optional[str] = None
    if current_status == "empty_code" or base_status == "empty_code":
        diff_status = "empty_code"
        reason = "empty_code"
    elif base_status == "missing_generation":
        diff_status = "missing_generation"
        reason = "missing_generation"
    return {
        "ok": True,
        "run_id": run_id,
        "gen_no": int(gen_no),
        "buy_name": current.get("buy_name"),
        "sell_name": current.get("sell_name"),
        "buy_code": current.get("buy_code", ""),
        "sell_code": current.get("sell_code", ""),
        "base_gen": int(base_no),
        "base_buy_name": base.get("buy_name"),
        "base_sell_name": base.get("sell_name"),
        "base_buy_code": base.get("buy_code", ""),
        "base_sell_code": base.get("sell_code", ""),
        "buy_diff": _diff_lines(
            str(base.get("buy_code") or ""),
            str(current.get("buy_code") or ""),
            str(base.get("buy_name") or ""),
            str(current.get("buy_name") or ""),
        ),
        "sell_diff": _diff_lines(
            str(base.get("sell_code") or ""),
            str(current.get("sell_code") or ""),
            str(base.get("sell_name") or ""),
            str(current.get("sell_name") or ""),
        ),
        "prompts": prompts,
        "diff_status": diff_status,
        "reason": reason,
    }


def _p5_verdict_note() -> str:
    """Return the latest honest OOS verdict note without exposing arbitrary files."""
    path = os.path.join(
        REPO_ROOT, ".omo", "evidence", "tick-oos-validation-20260603", "p5-decision-card.md"
    )
    try:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return "Previous OOS verdict unavailable; do not infer promotion."
    if "Final Verdict: REJECT_CANDIDATE" in text:
        return "Final Verdict: REJECT_CANDIDATE; prior candidate remains rejected."
    return "Previous OOS verdict file exists but no promotion verdict was found."


def _ai_context_pack_payload(run_id: Optional[str], gen_no: Optional[int] = None) -> Dict[str, Any]:
    """Build a deterministic, copyable research-state pack for an external AI agent.

    This is read-only and intentionally excludes prompt bodies, code bodies, secrets,
    environment values, production DB paths, and any network call.
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required"}

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        run_row = st.get_run(run_id)
        gens = st.get_generations(run_id)
        prompt_rows = st.get_prompts(run_id)
    except Exception as exc:  # noqa: BLE001 - context pack must be non-crashing.
        return {"error": str(exc), "run_id": run_id}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not gens:
        return {"error": "run_not_found_or_empty", "run_id": run_id}

    def _row_gen_no(row: Dict[str, Any]) -> int:
        try:
            return int(row.get("gen_no", -1))
        except (TypeError, ValueError):
            return -1

    selected_gen = int(gen_no) if gen_no is not None and int(gen_no) >= 0 else _row_gen_no(gens[-1])
    gen = next((g for g in gens if _row_gen_no(g) == selected_gen), gens[-1])
    cfg_json = (run_row or {}).get("config_json")
    cfg: Dict[str, Any] = {}
    if cfg_json:
        try:
            cfg = json.loads(str(cfg_json))
        except (ValueError, TypeError):
            cfg = {}
    period = _period_string_from_config(cfg_json)
    timeframe = cfg.get("bt_timeframe")
    gen_no_out = _row_gen_no(gen)
    gen_prompts = [p for p in prompt_rows if _row_gen_no(p) == gen_no_out]
    best = max(gens, key=lambda row: float(row.get("score", 0.0) or 0.0))
    winners = [g for g in gens if bool(g.get("gate_passed"))]
    winner = max(winners, key=lambda row: float(row.get("score", 0.0) or 0.0)) if winners else None
    strategy_names = {"buy": gen.get("buy_name"), "sell": gen.get("sell_name")}

    def _prompt_features(row: Dict[str, Any]) -> Dict[str, Any]:
        raw = row.get("injected_features")
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    prompt_feature_rows = [_prompt_features(p) for p in gen_prompts]
    first_features = next((f for f in prompt_feature_rows if f), {})
    context_pack = {
        "guide_context": {
            "source": "utility/ai_agent/system_prompt/v1",
            "prompt_count": len(gen_prompts),
            "prompt_logging_enabled": bool(cfg.get("prompt_logging_enabled")),
            "injected": first_features.get("guide_context"),
        },
        "diff_context": {
            "selected_gen_no": gen_no_out,
            "comparison_base_gen_no": gen_no_out - 1 if gen_no_out > 0 else None,
            "has_current_strategy_names": bool(strategy_names["buy"] or strategy_names["sell"]),
            "injected": first_features.get("diff_context"),
        },
        "analysis_context": {
            "best_gen_no": int(best.get("gen_no", -1) or -1),
            "winner_gen_no": (
                None if winner is None else int(winner.get("gen_no", -1) or -1)
            ),
            "score": gen.get("score"),
            "profit": gen.get("profit"),
            "injected": first_features.get("analysis_context"),
        },
        "correlation_context": {
            "source_route": "/variable_correlation",
            "per_trade_csv_available": bool(gen.get("csv_path")),
            "injected": first_features.get("correlation_context"),
        },
    }

    forbidden_actions = [
        "Do not approve, deploy, or write production strategy storage from this context.",
        "Do not place live orders or advance V3K gates.",
        "Do not claim human-level or seed-superior performance without fresh OOS evidence.",
    ]
    verdict_note = _p5_verdict_note()
    analysis = {
        "edge_ratio": "available via /edge_ratio when per-trade CSVs exist",
        "feature_importance": "available via /feature_importance when per-trade CSVs exist",
        "variable_correlation": "available via /variable_correlation when per-trade CSVs exist",
        "wiki": "available via /research_docs and /research_doc",
    }
    summary_lines = [
        "STOM AI condition research state",
        f"run_id: {run_id}",
        f"gen_no: {gen_no_out}",
        f"timeframe: {timeframe or '-'}",
        f"period: {period or '-'}",
        f"strategy_buy: {strategy_names['buy'] or '-'}",
        f"strategy_sell: {strategy_names['sell'] or '-'}",
        f"graded_score: {gen.get('score')}",
        f"profit: {gen.get('profit')}",
        f"return_pct: {gen.get('total_profit_pct')}",
        f"prompt_count: {len(gen_prompts)}",
        f"verdict: {verdict_note}",
        "forbidden: " + " | ".join(forbidden_actions),
    ]
    return {
        "run_id": run_id,
        "gen_no": gen_no_out,
        "timeframe": timeframe,
        "period": period,
        "config": {
            "provider": cfg.get("provider"),
            "bt_timeframe": cfg.get("bt_timeframe"),
            "bt_full_start": cfg.get("bt_full_start"),
            "bt_full_end": cfg.get("bt_full_end"),
            "bt_universe_start_time": cfg.get("bt_universe_start_time"),
            "bt_universe_end_time": cfg.get("bt_universe_end_time"),
        },
        "latest_logs": {
            "run_status": (run_row or {}).get("status"),
            "started_at": (run_row or {}).get("started_at"),
            "finished_at": (run_row or {}).get("finished_at"),
            "generation_count": len(gens),
        },
        "best": {
            "gen_no": int(best.get("gen_no", -1) or -1),
            "graded_score": best.get("score"),
            "profit": best.get("profit"),
        },
        "winner": (
            None if winner is None else {
                "gen_no": int(winner.get("gen_no", -1) or -1),
                "graded_score": winner.get("score"),
                "profit": winner.get("profit"),
            }
        ),
        "strategy_names": strategy_names,
        "prompt_count": len(gen_prompts),
        "context_pack": context_pack,
        "analysis": analysis,
        "verdict_note": verdict_note,
        "verdict_refs": [
            ".omo/evidence/tick-oos-validation-20260603/p5-decision-card.md",
            ".omo/evidence/tick-research-dashboard-upgrade-20260603/",
        ],
        "forbidden_actions": forbidden_actions,
        "summary_text": "\n".join(summary_lines),
    }


def _run_state_payload(run_id: str) -> Dict[str, Any]:
    """과거(또는 현재) run의 전체 LoopState payload를 DB에서 재구성한다(읽기 전용·무예외).

    #65 P0 — run 셀렉터용. 대시보드 라이브 상태(current_state.json)는 한 번에 하나의
    run만 보여주고, 에이전트 테스트가 합성 run('segrun')을 그 파일에 쓰면 화면이 오염된다.
    이 엔드포인트는 loop_runs.db의 runs+generations에서 임의 run을 통째로 재구성하므로,
    사용자가 라이브 오염과 무관하게 실제 run(reframe1 등)을 골라 브라우징할 수 있다.

    재구성:
      - generations 행을 읽어 summary(best/winner)를 만든다.
          best   = graded(score) 최고 세대.
          winner = 하드게이트 통과 세대 중 score 최고(없으면 None).
        이는 lineage._summarize_run의 우승 선택 규칙과 동일하나, to_loop_state가
        소비하는 평탄 키(best_gen/best_score/best_buy/best_sell, winner_*)로 만든다.
      - runs.config_json에서 LoopConfig를 복원해 provider/bt_timeframe/active_config를 채운다.
      - to_loop_state(summary, gens, config=cfg, status='complete', current_gen=len-1)로 빌드.
    status='complete'는 과거 run의 정적 스냅샷이라는 의미다(라이브 진행이 아님).

    DB 부재/없는 run/조회 실패는 idle_state로 표준화한다(무예외 — 대시보드가 빈 상태 표시).
    엔진/하드게이트/CSV 무수정. 추가 백테 0회(DB 조회만).
    """
    from ai_strategy_loop.config import LoopConfig  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState, to_loop_state  # noqa: PLC0415

    if not run_id:
        return C.idle_state().model_dump()

    st: Optional[LoopState] = None
    run_row: Optional[Dict[str, Any]] = None
    gens: list = []
    try:
        st = LoopState()
        run_row = st.get_run(run_id)
        gens = st.get_generations(run_id)
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 idle(무예외).
        return C.idle_state().model_dump()
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # 없는 run(행도 세대도 없음) → idle(무예외 계약).
    if run_row is None and not gens:
        return C.idle_state().model_dump()

    # config_json에서 LoopConfig 복원(provider/bt_timeframe/active_config 채움). 실패는 None.
    cfg: Any = None
    cfg_json = (run_row or {}).get("config_json")
    if cfg_json:
        try:
            cfg = LoopConfig.from_dict(json.loads(cfg_json))
        except (ValueError, TypeError):
            cfg = None

    # best = graded(score) 최고 세대(점수 None은 제외). 동률은 gen_no 큰 쪽(최신).
    best_row: Optional[Dict[str, Any]] = None
    for g in gens:
        if g.get("score") is None:
            continue
        if best_row is None or float(g.get("score") or 0.0) >= float(best_row.get("score") or 0.0):
            best_row = g
    # winner = 하드게이트 통과 세대 중 score 최고(없으면 None). 동률은 gen_no 큰 쪽.
    winner_row: Optional[Dict[str, Any]] = None
    for g in gens:
        if not bool(g.get("gate_passed")):
            continue
        if winner_row is None or float(g.get("score") or 0.0) >= float(winner_row.get("score") or 0.0):
            winner_row = g

    summary: Dict[str, Any] = {
        "run_id": run_id,
        "best_gen": (int(best_row.get("gen_no", -1)) if best_row is not None else -1),
        "best_score": (float(best_row.get("score")) if best_row and best_row.get("score") is not None else None),
        "best_buy": (best_row.get("buy_name") if best_row is not None else None),
        "best_sell": (best_row.get("sell_name") if best_row is not None else None),
        "winner_gen": (int(winner_row.get("gen_no", -1)) if winner_row is not None else -1),
        "winner_score": (
            float(winner_row.get("score")) if winner_row and winner_row.get("score") is not None else None
        ),
        "winner_buy": (winner_row.get("buy_name") if winner_row is not None else None),
        "winner_sell": (winner_row.get("sell_name") if winner_row is not None else None),
    }

    try:
        snapshot = to_loop_state(
            summary, gens, config=cfg, status="complete",
            current_gen=(len(gens) - 1 if gens else -1),
        )
        return snapshot.model_dump()
    except Exception:  # noqa: BLE001 - 빌드 실패도 idle로 표준화(무예외 계약).
        return C.idle_state().model_dump()


def _backtest_detail_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """한 세대의 백테 상세 시계열(일별손익·누적수익·낙폭)을 반환한다(읽기 전용, 무예외).

    O1 — 대시보드 BacktestDetailChart가 fetch 한다. 일반 STOM 백테가 만드는 2-그래프
    (일별손익 막대 + 누적수익곡선)를 헤드리스 루프 결과로 재현한다. 엔진 PNG 생성은
    꺼져 있으나(cli/runner.py) per-trade 거래 CSV는 항상 생성되므로, 이미 있는 그 CSV
    하나를 O2의 parse_backtest_series로 시계열 변환한다(추가 백테 0회).

    세대 행(generations)에서 (run_id, gen_no)의 csv_path·gate_passed·daily_avg_trades를
    조회하고, 그 run의 config_json에서 bt_betting을 뽑아 누적%(cum_pct) 산출에 쓴다.
    csv_path가 상대경로면 REPO_ROOT 기준으로 해석해 서버 CWD와 무관하게 동작한다.

    csv 없음/파싱 실패/없는 세대는 빈 시계열(daily=[]·summary 0)로 표준화한다(무예외).

    반환:
      {"run_id","gen_no","gate_passed",
       "daily":[{date,daily_pnl,profit,loss,net}...],
       "cumulative":[{date,cum_profit,cum_pct}...],
       "drawdown":[{date,drawdown}...],
       "holdings":[{t_index,count}...],   # 동시보유 종목수(이벤트/시각축, STOM fig2 상단 대응)
       "summary":{trade_count,final_profit,max_drawdown,n_days,peak_holdings}}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.equity_series import parse_backtest_series  # noqa: PLC0415

    empty_series: Dict[str, Any] = {
        "daily": [],
        "cumulative": [],
        "drawdown": [],
        "holdings": [],
        "summary": {
            "trade_count": 0,
            "final_profit": 0.0,
            "max_drawdown": 0.0,
            "n_days": 0,
            "peak_holdings": 0,
        },
    }

    # 세대 행에서 csv_path·gate_passed 조회 + run config_json에서 bt_betting 추출.
    csv_path: Optional[str] = None
    gate_passed = False
    betting = None
    found = False
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for row in st.get_generations(run_id):
            if int(row.get("gen_no", -1)) == int(gen_no):
                csv_path = row.get("csv_path")
                gate_passed = bool(row.get("gate_passed"))
                found = True
                break
        # bt_betting은 runs.config_json(JSON 문자열)에서 뽑는다(cum_pct 산출용).
        if found:
            run_row = st.get_run(run_id)
            if run_row is not None:
                try:
                    cfg = json.loads(run_row.get("config_json") or "{}")
                    betting = cfg.get("bt_betting")
                except (ValueError, TypeError):
                    betting = None
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답(무예외).
        return {"run_id": run_id, "gen_no": int(gen_no), "gate_passed": False, **empty_series}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not found or not csv_path:
        # 없는 (run,gen) 또는 csv_path 없는 세대 → 빈 시계열(무예외).
        return {"run_id": run_id, "gen_no": int(gen_no), "gate_passed": gate_passed, **empty_series}

    # 상대경로면 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작). 파서는 실패 시 빈 구조.
    resolved = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    series = parse_backtest_series(resolved, betting=betting)
    return {
        "run_id": run_id,
        "gen_no": int(gen_no),
        "gate_passed": gate_passed,
        "daily": series.get("daily", []),
        "cumulative": series.get("cumulative", []),
        "drawdown": series.get("drawdown", []),
        "holdings": series.get("holdings", []),
        "summary": series.get("summary", empty_series["summary"]),
    }


def _adaptive_timing_payload(run_id: Optional[str], lookback: int) -> Dict[str, Any]:
    """run의 gen0(또는 첫 gate_passed) 전략 CSV에 적응형 타이밍 리포트를 적용한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성 무영향) 오버레이다. loop_runs.db의 generations에서
    그 run의 gen0(가장 낮은 gen_no) 행 csv_path를 찾아 adaptive_timing_report를 돌려준다.
    gen0에 csv_path가 없으면 첫 gate_passed=1 세대의 csv_path로 폴백한다(_backtest_detail
    payload와 동일한 LoopState DB 경로/무예외 패턴).

    run_id 미지정/없는 run/csv_path 없음/파싱 실패는 {"error": ...}로 표준화한다(무예외).
    상대경로 csv_path는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.adaptive_timing import adaptive_timing_report  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required"}

    csv_path: Optional[str] = None
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        rows = st.get_generations(run_id)  # gen_no 오름차순.
        if not rows:
            return {"error": f"no generations for run_id={run_id!r}"}
        # gen0(가장 낮은 gen_no)의 csv_path 우선. 없으면 첫 gate_passed 세대로 폴백.
        first = rows[0]
        csv_path = first.get("csv_path")
        if not csv_path:
            for row in rows:
                if bool(row.get("gate_passed")) and row.get("csv_path"):
                    csv_path = row.get("csv_path")
                    break
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not csv_path:
        return {"error": f"no csv_path for run_id={run_id!r}"}

    resolved = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    try:
        report = adaptive_timing_report(resolved, lookback)
    except Exception as exc:  # noqa: BLE001 - 리포트 산출 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"run_id": run_id, "lookback": lookback, **report}


def _edge_ratio_payload(
    run_id: Optional[str], run_ids: Optional[str], fine_time: bool,
    gen_no: Optional[int] = None,
) -> Dict[str, Any]:
    """run(들)의 세대 결과 CSV를 풀링해 MFE/MAE 엣지비율 + 파노라마 세그먼트를 반환한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성/winner 무영향). loop_runs.db의 generations에서
    csv_path를 모은다:
      - run_ids(쉼표구분) 주면 그 모든 run의 **모든 세대** csv_path를 모은다(파노라마 풀).
      - 아니면 run_id 단일 run의 모든 세대 csv_path를 모은다.
    경로는 path로 dedupe하고, 상대경로는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    모은 CSV를 edge_report_from_csvs로 풀링 집계한다(추가 백테 0회).

    run 식별자 미지정/없는 run/세대 없음/조회 실패/풀 비음은 {"error": ...} 또는
    edge_report_from_csvs의 insufficient 결과로 표준화한다(무예외).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.edge_ratio import edge_report_from_csvs  # noqa: PLC0415

    # run_ids(쉼표구분) 우선, 없으면 run_id 단일. 둘 다 없으면 error.
    if run_ids:
        target_runs = [s.strip() for s in run_ids.split(",") if s.strip()]
    elif run_id:
        target_runs = [run_id]
    else:
        target_runs = []
    if not target_runs:
        return {"error": "run_id or run_ids required"}

    # generations에서 모든 세대 csv_path를 모은다(gate-passed 한정 아님 — 풀을 풍부하게).
    #   경로는 등장 순서를 보존하며 path로 dedupe한다.
    seen: set = set()
    raw_paths: List[str] = []
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for rid in target_runs:
            for row in st.get_generations(rid):  # gen_no 오름차순.
                # R4(2026-06-11) — gen_no 지정 시 그 세대만(G3: 이질 전략 혼합 풀링 방지).
                if gen_no is not None and int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                cp = row.get("csv_path")
                if cp and cp not in seen:
                    seen.add(cp)
                    raw_paths.append(str(cp))
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not raw_paths:
        return {"error": f"no csv_path for runs={target_runs!r}"}

    # 상대경로는 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작).
    resolved = [
        p if os.path.isabs(p) else os.path.join(REPO_ROOT, p) for p in raw_paths
    ]
    try:
        report = edge_report_from_csvs(resolved, fine_time=fine_time)
    except Exception as exc:  # noqa: BLE001 - 풀링 집계 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"runs": target_runs, "fine_time": bool(fine_time),
            "gen_no": gen_no, **report}


def _feature_importance_payload(
    run_id: Optional[str], run_ids: Optional[str], axis: str, fine_time: bool,
    gen_no: Optional[int] = None,
) -> Dict[str, Any]:
    """run(들)의 세대 결과 CSV를 풀링해 세그먼트별 승리-변수 피처 중요도를 반환한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성/winner 무영향). loop_runs.db의 generations에서
    csv_path를 모은다:
      - run_ids(쉼표구분) 주면 그 모든 run의 **모든 세대** csv_path를 모은다(파노라마 풀).
      - 아니면 run_id 단일 run의 모든 세대 csv_path를 모은다.
    경로는 path로 dedupe하고, 상대경로는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    모은 CSV를 feature_importance_from_csvs로 풀링 집계한다(추가 백테 0회). 각 B_* 진입
    피처가 승/패를 가르는 정도(Cohen's d + 분위 승률)를 전역·세그먼트(시총 또는 시간대)별로 낸다.

    run 식별자 미지정/없는 run/세대 없음/조회 실패/풀 비음은 {"error": ...} 또는
    feature_importance_from_csvs의 insufficient 결과로 표준화한다(무예외).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.feature_importance import (  # noqa: PLC0415
        feature_importance_from_csvs,
    )

    # run_ids(쉼표구분) 우선, 없으면 run_id 단일. 둘 다 없으면 error.
    if run_ids:
        target_runs = [s.strip() for s in run_ids.split(",") if s.strip()]
    elif run_id:
        target_runs = [run_id]
    else:
        target_runs = []
    if not target_runs:
        return {"error": "run_id or run_ids required"}

    # generations에서 모든 세대 csv_path를 모은다(gate-passed 한정 아님 — 풀을 풍부하게).
    #   경로는 등장 순서를 보존하며 path로 dedupe한다.
    seen: set = set()
    raw_paths: List[str] = []
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for rid in target_runs:
            for row in st.get_generations(rid):  # gen_no 오름차순.
                # R4(2026-06-11) — gen_no 지정 시 그 세대만(G3: 이질 전략 혼합 풀링 방지).
                if gen_no is not None and int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                cp = row.get("csv_path")
                if cp and cp not in seen:
                    seen.add(cp)
                    raw_paths.append(str(cp))
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not raw_paths:
        return {"error": f"no csv_path for runs={target_runs!r}"}

    # 상대경로는 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작).
    resolved = [
        p if os.path.isabs(p) else os.path.join(REPO_ROOT, p) for p in raw_paths
    ]
    try:
        report = feature_importance_from_csvs(resolved, axis=axis, fine_time=fine_time)
    except Exception as exc:  # noqa: BLE001 - 풀링 집계 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"runs": target_runs, "gen_no": gen_no, **report}


def _variable_correlation_payload(
    run_id: Optional[str], run_ids: Optional[str], method: str,
    gen_no: Optional[int] = None,
) -> Dict[str, Any]:
    """run(들)의 세대 결과 CSV를 풀링해 B_* 변수 상관도를 반환한다(읽기 전용, 무예외)."""
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.correlation import (  # noqa: PLC0415
        variable_correlation_from_csvs,
    )

    if run_ids:
        target_runs = [s.strip() for s in run_ids.split(",") if s.strip()]
    elif run_id:
        target_runs = [run_id]
    else:
        target_runs = []
    if not target_runs:
        return {"error": "run_id or run_ids required"}

    seen: set = set()
    raw_paths: List[str] = []
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for rid in target_runs:
            for row in st.get_generations(rid):
                # R4(2026-06-11) — gen_no 지정 시 그 세대만(G3: 이질 전략 혼합 풀링 방지).
                if gen_no is not None and int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                cp = row.get("csv_path")
                if cp and cp not in seen:
                    seen.add(cp)
                    raw_paths.append(str(cp))
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not raw_paths:
        return {"error": f"no csv_path for runs={target_runs!r}"}

    resolved = [
        p if os.path.isabs(p) else os.path.join(REPO_ROOT, p) for p in raw_paths
    ]
    try:
        report = variable_correlation_from_csvs(resolved, method=method)
    except Exception as exc:  # noqa: BLE001 - 풀링 집계 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"runs": target_runs, "gen_no": gen_no, **report}


def create_app() -> FastAPI:
    """대시보드 FastAPI 앱을 생성한다 (테스트가 TestClient로 감싼다)."""
    manager = LoopProcessManager()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        # 서버 수명 동안 매니저를 보유하고, 종료 시 추적 중인 루프 자식을
        #   강제 회수한다(오펀 백테스트 방지).
        yield
        manager.hard_stop()

    app = FastAPI(
        title="STOM AI Strategy Loop Dashboard", version="1.0", lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.loop_manager = manager
    app.include_router(research_router)

    @app.get("/")
    def root() -> RedirectResponse:
        # 단일 진입점: 루트로 들어오면 정적 대시보드(/ui/)로 보낸다.
        return RedirectResponse(url="/ui/")

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "contract_version": C.CONTRACT_VERSION}

    @app.get("/status")
    def status() -> Dict[str, Any]:
        return _current_state_payload()

    @app.get("/config/spec")
    def config_spec() -> Dict[str, Any]:
        return {"contract_version": C.CONTRACT_VERSION, "fields": config_field_specs()}

    @app.get("/research_criteria")
    def research_criteria(mode: Optional[str] = None) -> Dict[str, Any]:
        active_mode = normalize_research_oos_mode(mode)
        return {"contract_version": C.CONTRACT_VERSION, **research_mode_payload(active_mode)}

    @app.get("/equity_curves")
    def equity_curves(run_id: Optional[str] = None) -> Dict[str, Any]:
        """세대별 누적수익 시계열(equity curve)을 반환한다(읽기 전용, 무예외).

        run_id 주면 그 run의 세대만(현재 run 정상 스케일), 없으면 전체(하위호환).
        최근 200 세대까지 조회하며, 세대당 포인트는 최대 200개로 다운샘플한다.
        CSV 없거나 파싱 실패한 세대는 건너뛴다. DB 없으면 빈 배열(무예외).
        """
        return _equity_curves_payload(run_id=run_id)

    @app.get("/hall_of_fame")
    def hall_of_fame() -> Dict[str, Any]:
        """명예의 전당: 인간 벤치마크 + AI 생성 통합 목록을 반환한다(읽기 전용, 무예외).

        인간은 reference_strategies.json(19전략), AI는 loop_runs.db의 gate_passed=1·
        흑자 세대를 운영금 역산·연평균 산식으로 매핑해 graded 상위 30개를 돌려준다.
        JSON/DB가 없으면 빈 목록(무예외 계약 — 대시보드가 빈 상태를 표시).
        """
        return _hall_of_fame_payload()

    @app.get("/reference_screenshots")
    def reference_screenshots() -> Dict[str, Any]:
        """인간 reference 결과 스크린샷 파일명 목록을 반환한다(갤러리 fetch용, 읽기 전용, 무예외).

        docs/reference/STOM_Good_Results의 최상위 이미지 파일명만 나열한다(분석용 파생
        크롭/줌은 제외). 프론트가 각 파일명을 baseUrl+'/reference_img/'+filename으로
        StaticFiles에서 직접 가져온다. 디렉토리 부재/조회 실패는 빈 목록(무예외 계약).
        """
        files = _reference_screenshots()
        return {"screenshots": files, "count": len(files)}

    @app.get("/runs")
    def runs() -> Dict[str, Any]:
        """loop_runs.db의 모든 run 요약을 반환한다(run 비교 콘솔 목록).

        lineage.compare_runs(run_ids=None)로 전 run을 요약한다. DB가 없거나
        조회 실패면 빈 목록을 돌려 대시보드가 깨지지 않게 한다(무예외 계약).
        """
        return _runs_payload(None)

    @app.get("/run_state")
    def run_state(run_id: str = "") -> Dict[str, Any]:
        """과거(또는 현재) run의 전체 LoopState payload를 DB에서 재구성해 반환한다(#65 run 셀렉터).

        쿼리: ?run_id=<run_id>. loop_runs.db의 runs+generations에서 그 run을 통째로
        재구성한다(세대표·best/winner·코드뷰어가 그 run을 소비). 라이브 상태가 합성 run으로
        오염돼도 사용자가 실제 run을 골라 본다. run_id 미지정/없는 run/조회 실패는 idle
        상태로 표준화한다(무예외 — 대시보드가 빈 상태 표시). 읽기 전용·추가 백테 0회.
        """
        return _run_state_payload(run_id)

    @app.get("/generation_durations")
    def generation_durations(run_id: Optional[str] = None) -> Dict[str, Any]:
        """세대별 소요초(인접 created_at 차분)를 반환한다(#64 과거 run retroactive).

        쿼리: ?run_id=<run_id>(선택). 없으면 전체 run. LIVE 발행이 없던 과거 run에도
        DB의 created_at/started_at로 산출되므로 사용자가 지금 바로 세대 소요를 본다.
        DB 없거나 조회 실패면 빈 목록(무예외).
        """
        return _generation_durations_payload(run_id)

    @app.get("/run_yearly")
    def run_yearly(run_id: str = "") -> Dict[str, Any]:
        """D1 — run의 세대별 연도 분해(거래·손익·승률)를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>. 근거(2026-06-10 원인5): 연도별 쇠퇴는 합계로는 안 보인다.
        per-trade CSV를 연 단위로 집계한다(추가 백테 0회). CSV 없으면 빈 분해.
        """
        return _run_yearly_payload(run_id)

    @app.get("/autopsy")
    def autopsy(run_id: str = "", gen_no: int = 0) -> Dict[str, Any]:
        """D2 — 세대 결과 CSV의 공식 부검(진입/청산) NL 요약을 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&gen_no=<n>. 루프 프롬프트 환류로만 쓰이던 부검을 사람이
        직접 본다(손실군집·MFE 반납·손실집중 매도규칙). CSV 없으면 status=no_csv.
        """
        return _autopsy_payload(run_id, gen_no)

    @app.get("/selector_preview")
    def selector_preview(run_id: str = "", selector: str = "sparse_positive_v1") -> Dict[str, Any]:
        """D4 — run 행에 선택기를 진단 적용한 미리보기를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&selector=sparse_positive_v1|seed_relative_v1.
        근거(2026-06-10 원인1): 기준-목표 비정합을 눈으로 확인한다. **진단 전용** —
        동결 아티팩트를 쓰지 않으며 OOS-blind 동결 절차를 대체하지 않는다.
        """
        return _selector_preview_payload(run_id, selector)

    @app.get("/counterfactual")
    def counterfactual(run_id: str = "", gen_no: int = 0, top_k: int = 5) -> Dict[str, Any]:
        """R2(2026-06-11) — 세대 CSV의 반사실 필터 제안을 반환한다(백테 0회, 읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&gen_no=<n>&top_k=<k>. 부검 변별 변수+승자 분위수로 강화 필터
        후보를 만들고 "총손익이 깎이지 않는" 것만 손익 영향·연도별 분해와 함께 반환한다.
        **인샘플 advisory** — 채택 후보는 스모크→train→동결→OOS 규율로 검증해야 한다.
        """
        out: Dict[str, Any] = {"run_id": run_id, "gen_no": gen_no,
                               "suggestions": [], "count": 0, "status": "unavailable"}
        row = _row_for_gen(run_id, gen_no)
        if row is None:
            return out
        out["label"] = row.get("strategy_gist") or ""
        csv_path = row.get("csv_path") or ""
        if not csv_path:
            out["status"] = "no_csv"
            return out
        try:
            from ai_strategy_loop.fitness.counterfactual import suggestions_payload  # noqa: PLC0415

            abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
            payload = suggestions_payload(abs_csv, top_k=top_k)
            out.update(payload)
            out["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["status"] = "error"
            out["error"] = str(exc)
        return out

    @app.get("/freeze_mc")
    def freeze_mc(run_id: str = "", gen_no: int = 0,
                  n_boot: int = 2000, block_len: int = 5) -> Dict[str, Any]:
        """R3(2026-06-11) — 세대 일별 손익의 블록 부트스트랩 MC를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=&gen_no=&n_boot=&block_len=. GUI 백테스트 MC(거래 iid 추출)의
        헤드리스 대응물 — 단 일별 손익 **블록** 재추출로 레짐 군집을 보존하고 MDD(낙폭금액)
        분포까지 산출한다(6/2 in-sample iid MC의 OOS 전이 실패 교훈 반영). advisory 전용.
        """
        out: Dict[str, Any] = {"run_id": run_id, "gen_no": gen_no, "status": "unavailable"}
        row = _row_for_gen(run_id, gen_no)
        if row is None:
            return out
        out["label"] = row.get("strategy_gist") or ""
        csv_path = row.get("csv_path") or ""
        if not csv_path:
            out["status"] = "no_csv"
            return out
        try:
            from ai_strategy_loop.fitness.overfit_stats import (  # noqa: PLC0415
                block_bootstrap_daily,
                daily_pnl_series,
            )

            abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
            series = daily_pnl_series(abs_csv)
            if not series:
                out["status"] = "no_daily_series"
                return out
            mc = block_bootstrap_daily(
                list(series.values()), n_boot=min(int(n_boot), 10000),
                block_len=max(int(block_len), 1),
            )
            if mc is None:
                out["status"] = "insufficient_days"
                out["n_days"] = len(series)
                return out
            out["mc"] = mc
            out["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["status"] = "error"
            out["error"] = str(exc)
        return out

    @app.get("/tmap_map")
    def tmap_map(run_id: str = "") -> Dict[str, Any]:
        """TMAP G3(2026-06-11) — 스윕 run의 경향성 지도를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<tmap_sweep run_id>. 변수별 응답 곡선·고원(중심/폭/평균손익)·
        절벽·plateau_score + 베이스라인. TMAP 라벨 행이 없으면 count=0(graceful).
        피크가 아닌 고원을 고르는 것이 계약 — advisory 전용.
        """
        try:
            from ai_strategy_loop.tmap.tendency import summarize_tendency  # noqa: PLC0415

            return summarize_tendency(run_id)
        except Exception as exc:  # noqa: BLE001
            return {"run_id": run_id, "baseline": None, "params": {},
                    "count": 0, "error": str(exc)}

    @app.get("/portfolio_preview")
    def portfolio_preview(run_id: str = "", gens: str = "",
                          max_size: int = 4, corr_cap: float = 0.5) -> Dict[str, Any]:
        """TMAP G5(2026-06-11) — 세대들의 일별손익 저상관 결합 미리보기(읽기 전용·무예외).

        쿼리: ?run_id=&gens=<0,1,2>(비우면 status=ok 전 세대)&max_size=&corr_cap=.
        일별손익 합산 근사(동시보유 자본 제약 무시 — 낙관 편향, note에 명시) —
        채택 조합은 실백테 확인이 계약. advisory 전용.
        """
        import sqlite3  # noqa: PLC0415

        from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

        out: Dict[str, Any] = {"run_id": run_id, "selection": [], "steps": [],
                               "combined": None, "status": "unavailable"}
        if not run_id:
            return out
        try:
            con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
            con.row_factory = sqlite3.Row
            try:
                rows = con.execute(
                    "SELECT gen_no, status, strategy_gist, buy_name, csv_path"
                    " FROM generations WHERE run_id=? ORDER BY gen_no",
                    (run_id,),
                ).fetchall()
            finally:
                con.close()
            wanted = {int(g) for g in gens.split(",") if g.strip()} if gens.strip() else None
            from ai_strategy_loop.fitness.overfit_stats import daily_pnl_series  # noqa: PLC0415
            from ai_strategy_loop.tmap.portfolio import greedy_portfolio  # noqa: PLC0415

            series = {}
            for r in rows:
                d = dict(r)
                if d.get("status") != "ok" or not d.get("csv_path"):
                    continue
                if wanted is not None and int(d["gen_no"]) not in wanted:
                    continue
                csv_path = d["csv_path"]
                abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
                s = daily_pnl_series(abs_csv)
                if s:
                    label = d.get("strategy_gist") or d.get("buy_name") or f"gen{d['gen_no']}"
                    series[f"gen{d['gen_no']}:{label}"] = s
            if len(series) < 1:
                out["status"] = "no_series"
                return out
            result = greedy_portfolio(series, max_size=max_size, corr_cap=corr_cap)
            out.update(result)
            out["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["status"] = "error"
            out["error"] = str(exc)
        return out

    @app.get("/runs/compare")
    def runs_compare(ids: str = "") -> Dict[str, Any]:
        """지정한 run id들을 지표/우승전략으로 비교한다(loop_runs.db 직접).

        ids는 쉼표로 구분한 run_id 목록(예: `?ids=run_a,run_b`). 비면 전체 run.
        """
        id_list = [s.strip() for s in ids.split(",") if s.strip()] or None
        return _runs_payload(id_list)

    @app.get("/strategy_code")
    def strategy_code(run: str = "", gen: int = -1) -> Dict[str, Any]:
        """한 세대의 매수/매도 전략 코드를 반환한다(코드 뷰어 fetch용).

        쿼리: ?run=<run_id>&gen=<n>. 루프 DB(STOM_CLI_DB_STRATEGY)의
        stockbuy/stocksell에서 그 세대의 코드를 조회해 {buy_code, sell_code}를
        돌려준다. run 미지정/조회 실패/없는 gen은 빈 코드 문자열로 표준화한다
        (무예외 — 대시보드가 "코드가 없습니다"를 표시).
        """
        if not run or gen < 0:
            reason = "missing_run" if not run else "missing_generation"
            return {
                "ok": True,
                "run_id": run, "gen": gen,
                "gen_no": gen,
                "buy_name": "", "sell_name": "", "buy_code": "", "sell_code": "",
                "code_status": reason,
                "reason": reason,
            }
        return _strategy_code_payload(run, gen)

    @app.get("/prompts")
    def prompts(run_id: Optional[str] = None, gen_no: Optional[int] = None) -> Dict[str, Any]:
        """저장된 프롬프트 메타데이터와 bounded text head를 반환한다(읽기 전용)."""
        return _prompts_payload(run_id, gen_no)

    @app.get("/strategy_diff")
    def strategy_diff(run_id: Optional[str] = None, gen_no: int = -1,
                      base_gen: str = "previous") -> Dict[str, Any]:
        """현재 세대와 이전/base 세대의 매수·매도 전략 코드 diff를 반환한다."""
        if not run_id:
            return {
                "ok": True,
                "run_id": run_id,
                "gen_no": int(gen_no),
                "buy_name": "",
                "sell_name": "",
                "buy_code": "",
                "sell_code": "",
                "base_gen": None,
                "base_buy_name": None,
                "base_sell_name": None,
                "base_buy_code": "",
                "base_sell_code": "",
                "buy_diff": [],
                "sell_diff": [],
                "prompts": [],
                "diff_status": "missing_run",
                "reason": "missing_run",
            }
        if int(gen_no) < 0:
            return {
                "ok": True,
                "run_id": run_id,
                "gen_no": int(gen_no),
                "buy_name": "",
                "sell_name": "",
                "buy_code": "",
                "sell_code": "",
                "base_gen": None,
                "base_buy_name": None,
                "base_sell_name": None,
                "base_buy_code": "",
                "base_sell_code": "",
                "buy_diff": [],
                "sell_diff": [],
                "prompts": [],
                "diff_status": "missing_generation",
                "reason": "missing_generation",
            }
        return _strategy_diff_payload(run_id, int(gen_no), base_gen)

    @app.get("/ai_context_pack")
    def ai_context_pack(run_id: Optional[str] = None, gen_no: Optional[int] = None) -> Dict[str, Any]:
        """현재 연구 상태를 외부 AI에게 전달할 수 있는 read-only context pack으로 반환한다."""
        return _ai_context_pack_payload(run_id, gen_no)

    @app.get("/backtest_detail")
    def backtest_detail(run_id: str = "", gen_no: int = -1) -> Dict[str, Any]:
        """한 세대의 백테 상세 시계열(일별손익·누적수익·낙폭)을 반환한다(차트 fetch용).

        쿼리: ?run_id=<run_id>&gen_no=<n>. 그 세대의 per-trade 결과 CSV를
        parse_backtest_series로 일별손익+누적곡선+낙폭으로 변환해 돌려준다(추가 백테 0회).
        run_id 미지정/없는 gen/CSV 없음/파싱 실패는 빈 시계열로 표준화한다(무예외 —
        대시보드가 빈 상태 패널을 표시).
        """
        if not run_id or gen_no < 0:
            return {
                "run_id": run_id, "gen_no": gen_no, "gate_passed": False,
                "daily": [], "cumulative": [], "drawdown": [],
                "summary": {
                    "trade_count": 0, "final_profit": 0.0,
                    "max_drawdown": 0.0, "n_days": 0,
                },
            }
        return _backtest_detail_payload(run_id, gen_no)

    @app.get("/adaptive_timing")
    def adaptive_timing(run_id: Optional[str] = None, lookback: int = 2) -> Dict[str, Any]:
        """run의 gen0(또는 첫 gate_passed) 전략 결과 CSV에 적응형 레짐-타이밍 리포트를 돌린다.

        쿼리: ?run_id=<run_id>&lookback=<n>. 분석 전용(엔진/하드게이트/스코어 무영향)
        오버레이로, always-on 대비 위험조정(수익/MDD)을 비교한다(추가 백테 0회). run_id
        미지정/없는 run/CSV 없음/파싱 실패는 {"error": ...}로 표준화한다(읽기 전용·무예외).
        """
        return _adaptive_timing_payload(run_id, lookback)

    @app.get("/edge_ratio")
    def edge_ratio(run_id: Optional[str] = None, run_ids: Optional[str] = None,
                   fine_time: bool = False,
                   gen_no: Optional[int] = None) -> Dict[str, Any]:
        """run(들)의 세대 결과 CSV를 풀링해 MFE/MAE 엣지비율 + 시간대×시총 파노라마 세그먼트를 반환한다.

        쿼리: ?run_ids=<a,b,c>(파노라마 다중 run 풀) 또는 ?run_id=<run_id>(단일 run 풀),
        &fine_time=<bool>(5분 시초 세분). 미사용이던 R_MFE/R_MAE 신호로 엣지비율(평균MFE/평균|MAE|)을
        산출하고, 누적된 전체 거래를 시총·시간대·등락률·교차로 쪼개 본다(분석 전용·엔진/하드게이트/스코어
        무영향·추가 백테 0회). segments 응답에 "change" 키 포함(B_등락율 없으면 빈 리스트).
        run 식별자 미지정/없는 run/CSV 없음은 {"error": ...} 또는
        insufficient로 표준화한다(읽기 전용·무예외).
        """
        return _edge_ratio_payload(run_id, run_ids, fine_time, gen_no=gen_no)

    @app.get("/feature_importance")
    def feature_importance(run_id: Optional[str] = None, run_ids: Optional[str] = None,
                           axis: str = "market_cap", fine_time: bool = False) -> Dict[str, Any]:
        """run(들)의 세대 결과 CSV를 풀링해 세그먼트별 승리-변수 피처 중요도를 반환한다.

        쿼리: ?run_ids=<a,b,c>(파노라마 다중 run 풀) 또는 ?run_id=<run_id>(단일 run 풀),
        &axis=<market_cap|time|change>(세그먼트 축), &fine_time=<bool>(시간축 5분 시초 세분). 각 B_*
        진입 피처가 승리거래(수익률>0)와 패배거래를 가르는 정도를 표준화 평균차(Cohen's d)와
        상/하위 사분위 승률로 산출하고, 전역 풀과 세그먼트(시총 등급·시간대·등락률)별로 나눠
        "어느 시간대×시총×등락률에서 어느 진입변수가 승패를 가르나"에 답한다(분석 전용·엔진/하드게이트/
        스코어 무영향·추가 백테 0회). run 식별자 미지정/없는 run/CSV 없음은 {"error": ...} 또는
        insufficient로 표준화한다(읽기 전용·무예외).
        """
        return _feature_importance_payload(run_id, run_ids, axis, fine_time, gen_no=gen_no)

    @app.get("/variable_correlation")
    def variable_correlation(run_id: Optional[str] = None, run_ids: Optional[str] = None,
                             method: str = "pearson",
                             gen_no: Optional[int] = None) -> Dict[str, Any]:
        """run(들)의 세대 결과 CSV를 풀링해 변수별 outcome/feature 상관도를 반환한다.

        쿼리: ?run_ids=<a,b,c> 또는 ?run_id=<run_id>, &method=<pearson|spearman>.
        B_* 진입 변수만 분석하며, outcome은 수익률 컬럼이다. 분석 전용·읽기 전용으로
        엔진/하드게이트/스코어/생성/winner/export에는 영향이 없다.
        """
        return _variable_correlation_payload(run_id, run_ids, method, gen_no=gen_no)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        # 연결 즉시 현재 상태 송신.
        last_sent = _current_state_payload()
        await websocket.send_json(last_sent)

        async def _pusher() -> None:
            """current_state.json 변경을 폴링해 변경 시에만 push."""
            nonlocal last_sent
            while True:
                await asyncio.sleep(_POLL_INTERVAL)
                payload = _current_state_payload()
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_json(payload)

        push_task = asyncio.create_task(_pusher())
        try:
            while True:
                # 인바운드 제어 메시지 수신.
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    await websocket.send_json({"status": "error", "message": "invalid JSON"})
                    continue
                result = _handle_control(msg, manager)
                await websocket.send_json(result)
        except WebSocketDisconnect:
            pass
        finally:
            push_task.cancel()

    # 인간 reference 결과 스크린샷을 /reference_img 하위에 읽기 전용으로 마운트한다.
    #   StaticFiles는 GET/HEAD만 처리(쓰기 불가)하고, 노출 대상은 STOM_Good_Results
    #   디렉토리 단 하나뿐이다(다른 디렉토리 노출 금지). 디렉토리가 없으면 마운트를
    #   스킵해 API만으로도 기동되게 한다(무예외). 갤러리는 /reference_screenshots로 받은
    #   파일명을 baseUrl+'/reference_img/'+filename 으로 직접 가져온다.
    if os.path.isdir(_REFERENCE_SCREENSHOTS_DIR):
        app.mount(
            "/reference_img",
            StaticFiles(directory=_REFERENCE_SCREENSHOTS_DIR),
            name="reference_img",
        )

    # 정적 프론트엔드 마운트는 모든 API 라우트(/health, /status, /config/spec, /ws, /)
    #   등록 이후에 한다. /ui 하위 경로에 마운트하므로 위 API 라우트와 WS를 가리지
    #   않는다(StaticFiles는 /ui/* 만 처리). html=True 로 /ui/ 가 index.html을 서빙.
    #   .jsx 는 StaticFiles 기본 content-type으로 서빙되며 브라우저 fetch+Babel 변환에
    #   문제 없다. 프론트엔드 디렉토리가 없으면 API만으로도 기동되도록 가드한다.
    if os.path.isdir(_FRONTEND_DIR):
        app.mount("/ui", StaticFiles(directory=_FRONTEND_DIR, html=True), name="ui")

    return app


def _handle_control(msg: Dict[str, Any], manager: LoopProcessManager) -> Dict[str, Any]:
    """인바운드 제어 메시지를 처리한다 (start | stop | final_approval).

    제어 결과 dict를 반환한다(클라이언트로 에코). 어떤 예외도 흡수해 WS를
    끊지 않는다.
    """
    action = (msg or {}).get("action")
    try:
        if action == "start":
            return {"action": "start", **manager.start(msg.get("config") or {})}
        if action == "stop":
            return {"action": "stop", **manager.stop()}
        if action == "final_approval":
            return {"action": "final_approval", **_do_final_approval(msg)}
        return {"status": "error", "message": f"unknown action: {action!r}"}
    except Exception as exc:  # noqa: BLE001 - 제어 실패는 WS를 끊지 않는다.
        return {"status": "error", "action": action, "message": str(exc)}


def _do_final_approval(msg: Dict[str, Any]) -> Dict[str, Any]:
    """final_approval — 우승 전략을 운영 strategy.db로 export (사람 승인 게이트).

    필요 키: buy_name, sell_name (루프 DB 내 namespaced 우승 이름),
             user_buy, user_sell (운영 DB에 저장할 사람이 정한 이름).

    보안: export 목적지는 클라이언트가 고를 수 없다. 메시지에 dest_strategy_db가
    들어와도 무시하고 항상 export.PRODUCTION_STRATEGY_DB(결정론적 운영 경로)로만
    내보낸다(임의 경로 쓰기 방지).
    """
    from ai_strategy_loop.controller.export import (  # noqa: PLC0415
        PRODUCTION_STRATEGY_DB,
        export_winner,
    )

    buy_name = msg.get("buy_name")
    sell_name = msg.get("sell_name")
    user_buy = msg.get("user_buy")
    user_sell = msg.get("user_sell")
    if not (buy_name and sell_name and user_buy and user_sell):
        return {
            "status": "error",
            "message": "final_approval requires buy_name, sell_name, user_buy, user_sell",
        }
    # 클라이언트 제공 dest_strategy_db는 의도적으로 무시한다 — 항상 운영 경로.
    return export_winner(
        buy_name, sell_name, str(PRODUCTION_STRATEGY_DB), user_buy, user_sell,
    )


# 모듈 레벨 app — uvicorn `ai_strategy_loop.dashboard.app:app` 로도 띄울 수 있다.
app = create_app()
