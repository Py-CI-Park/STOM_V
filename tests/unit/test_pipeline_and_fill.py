"""C2(M7)·C8(N1) — 파이프라인 체크포인트·체결가능성 테스트 (2026-06-11).

C2 계약: done 단계 스킵 / --from-stage 강제 재실행 / 미지 단계 ValueError /
단계 명령은 기존 공식 도구만 호출(새 평가 로직 0).
C8 계약: R_매수후최저수익률>=0 = 추격 체결 의존 / 컬럼 부재 None / advisory.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.fill_feasibility import fill_fragility  # noqa: E402
from ai_strategy_loop.scripts.research_pipeline import (  # noqa: E402
    STAGES,
    build_stage_command,
    build_stages,
    pending_stages,
)


class TestPipelineCheckpoint:
    def test_done_stages_skipped(self) -> None:
        state = {"sweep": "done", "theta_star": "done"}
        assert pending_stages(state) == [
            "reeval", "freeze", "oos2022", "oos2026", "placebo", "slippage"]

    def test_failed_stage_reruns(self) -> None:
        state = {"sweep": "done", "theta_star": "failed rc=2"}
        assert pending_stages(state)[0] == "theta_star"

    def test_from_stage_forces_rerun_of_suffix(self) -> None:
        state = {s: "done" for s in STAGES}
        assert pending_stages(state, from_stage="freeze") == [
            "freeze", "oos2022", "oos2026", "placebo", "slippage"]
        with pytest.raises(ValueError):
            pending_stages(state, from_stage="nope")

    def test_placebo_pairs_naming_convention(self) -> None:
        """P-B — gen_placebo_strategy 명명 규약(S0은 무접미)과 정합해야 한다."""
        from ai_strategy_loop.scripts.research_pipeline import placebo_pairs

        pairs = placebo_pairs("PLB_X", "CAND_S", rates=(2, 5), shifts=(0, 1))
        assert len(pairs) == 4
        assert pairs[0] == {"label": "PLACEBO R2 S0", "buy": "PLB_X_R2_B", "sell": "CAND_S"}
        assert pairs[1]["buy"] == "PLB_X_R2_S1_B"  # shift>0은 _S{n} 접미.
        assert all(p["sell"] == "CAND_S" for p in pairs)  # 동일 매도(대조 변인 통제).

    def test_stage_commands_call_official_tools_only(self) -> None:
        kw = {"template": "seed_902905", "config_json": "cfg.json", "prefix": "p1"}
        sweep = build_stage_command("sweep", **kw, params="cap_max")
        assert "ai_strategy_loop.scripts.tmap_sweep" in sweep
        assert "--resume" in sweep  # 자체 재개 가능 단계.
        assert "--params" in sweep
        reeval = build_stage_command("reeval", **kw)
        assert "ai_strategy_loop.scripts.claude_candidate_batch_eval" in reeval
        assert any("p1_reeval" in str(c) for c in reeval)
        freeze = build_stage_command("freeze", **kw)
        assert any("select_and_freeze.py" in str(c) for c in freeze)
        assert any("--trial-runs=p1_sweep" in str(c) for c in freeze)  # N5 연동.
        assert build_stage_command("oos2026", **kw) is None  # oos2022가 함께 처리.

    def test_no_wf_windows_gives_8_stages(self) -> None:
        """V4 — --wf-windows 없을 때 기존 8단계 불변(하위 호환)."""
        assert build_stages("") == list(STAGES)
        assert len(build_stages("")) == 8
        # pending_stages도 8단계만 반환.
        assert pending_stages({}) == list(STAGES)
        assert "walkforward" not in pending_stages({})

    def test_wf_windows_gives_9_stages_walkforward_last(self) -> None:
        """V4 — --wf-windows 주어지면 9단계·walkforward가 마지막."""
        stages = build_stages("20230101-20231231:20240101-20240630")
        assert len(stages) == 9
        assert stages[-1] == "walkforward"
        # pending_stages도 동일하게 9번째로 반환.
        pending = pending_stages({}, wf_windows="20230101-20231231:20240101-20240630")
        assert len(pending) == 9
        assert pending[-1] == "walkforward"

    def test_build_stage_command_walkforward(self) -> None:
        """V4 — build_stage_command('walkforward') 명령 구성 검증."""
        kw = {"template": "seed_902905", "config_json": "cfg.json", "prefix": "p1"}
        wf_spec = "20230101-20231231:20240101-20240630"
        cmd = build_stage_command("walkforward", **kw, params="cap_max",
                                  wf_windows=wf_spec)
        assert cmd is not None
        assert "ai_strategy_loop.scripts.tmap_walkforward" in cmd
        assert "--run-prefix" in cmd
        assert any("p1_wf" in str(c) for c in cmd)  # run-prefix 전달.
        assert "--windows" in cmd
        assert wf_spec in cmd  # windows 값 전달.
        assert "--params" in cmd and "cap_max" in cmd  # params 전달.
        assert "--out" in cmd
        assert any("p1_wf_aggregate.json" in str(c) for c in cmd)

    def test_from_stage_walkforward_forces_rerun(self) -> None:
        """V4 — --from-stage walkforward 강제 재실행: done 상태여도 재포함."""
        wf_spec = "20230101-20231231:20240101-20240630"
        state = {s: "done" for s in STAGES} | {"walkforward": "done"}
        pending = pending_stages(state, from_stage="walkforward",
                                 wf_windows=wf_spec)
        assert pending == ["walkforward"]
        # wf_windows 없이 from_stage="walkforward"는 ValueError.
        with pytest.raises(ValueError):
            pending_stages(state, from_stage="walkforward", wf_windows="")


class TestMorningReport:
    """P-C(2026-06-12) — 아침 보고 합성: 절 단위 생략·핵심 섹션 계약."""

    def test_compose_full_sections(self) -> None:
        from ai_strategy_loop.scripts.gen_morning_report import compose_report

        text = compose_report(
            verdict={"promote_checklist": [{"item": "V3", "status": "pass", "detail": "ok"}],
                     "alerts": ["얇은 마진"], "lines": ["동결 후보: genX"]},
            niche={"runs": [{"run_id": "tmapA", "status": "complete",
                             "baseline": {"profit": 1000.0, "mdd": 5.0},
                             "top_slot": {"param": "cap", "center": 2500},
                             "corr_vs_frozen": 0.18}]},
            ops={"recent": [{"run_id": "r1", "gens": 7, "best_profit": 123.0}]},
            decisions={"decisions": []},
            now_label="2026-06-12 07:00",
        )
        assert "PROMOTE 체크리스트" in text and "✅" in text
        assert "⚠️ 얇은 마진" in text
        assert "tmapA" in text and "0.18" in text
        assert "V6 결정 대기" in text  # 결정 없음 → 대기 안내.

    def test_compose_graceful_on_empty(self) -> None:
        from ai_strategy_loop.scripts.gen_morning_report import compose_report

        text = compose_report(None, None, None, None, now_label="x")
        assert "아침 자동 보고" in text
        assert "운용 결정 이력" in text  # 결정 절은 항상 존재(대기 안내 포함).


class TestBatchLiveState:
    """E3(2026-06-11) — 배치 라이브 상태 발행: 계약 호환·실패 흡수."""

    def test_publish_and_read_roundtrip_contract_compatible(self, tmp_path) -> None:
        from ai_strategy_loop.config import LoopConfig
        from ai_strategy_loop.controller import contract as C
        from ai_strategy_loop.controller.state import (
            LoopState,
            publish_batch_state,
            read_current_state,
        )

        # G-1 — 추이 차트 재료: run의 기존 세대들이 generations[]로 함께 발행된다.
        db = str(tmp_path / "loop_runs.db")
        st = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        st.start_run(LoopConfig(), run_id="runB")
        for i, profit in enumerate([100_000.0, 250_000.0]):
            st.record_generation(
                "runB", i, buy_name=f"B{i}", sell_name=f"S{i}", status="ok",
                score=0.5 + i, gate_passed=True, reason="ok", profit=profit,
                mdd=5.0, trade_count=10, payoff_ratio=1.2,
                strategy_gist=f"TMAP x={i}",
            )
        st.close()

        p = str(tmp_path / "current_state.json")
        publish_batch_state("runB", 3, 10, label="TMAP x=1",
                            message="스윕 4/10 평가 중", path=p, db_path=db,
                            engine={"back_count": 2285})
        d = read_current_state(p)
        assert d["run_id"] == "runB"
        assert d["current_gen"] == 3 and d["max_generations"] == 10
        assert d["latest"]["strategy_gist"] == "TMAP x=1"
        assert d["latest"]["engine_state"] == {"back_count": 2285}
        assert d["status"] == "running"
        assert len(d["generations"]) == 2  # 추이 차트가 그릴 세대 배열.
        assert d["generations"][1]["profit"] == 250_000.0
        assert d["generations"][1]["graded_score"] == 1.5
        C.LoopState(**d)  # 계약 검증 통과 — 상단 라이브 영역이 그대로 소비 가능.

    def test_publish_failure_is_absorbed(self) -> None:
        from ai_strategy_loop.controller.state import publish_batch_state

        # 쓸 수 없는 경로여도 예외가 새어나오면 안 된다(배치를 막지 않는 계약).
        publish_batch_state("runB", 0, 1, path="Z:\\no_such_dir\\x\\state.json")


class TestFillFragility:
    @staticmethod
    def _csv(path: Path, rows) -> str:
        """rows: (수익금, 매수후최저수익률)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["종목명", "수익금", "R_매수후최저수익률"])
            w.writeheader()
            for profit, low in rows:
                w.writerow({"종목명": "T", "수익금": profit, "R_매수후최저수익률": low})
        return str(path)

    def test_fragile_share_computed(self, tmp_path) -> None:
        # 2건은 매수가 이하 재방문 없음(추격 의존, +800) / 2건은 재방문(+200).
        p = self._csv(tmp_path / "a.csv", [
            (500, 0.0), (300, 0.2), (300, -0.5), (-100, -1.0),
        ])
        out = fill_fragility(p)
        assert out["fragile_trades"] == 2
        assert out["fragile_trade_ratio"] == 0.5
        assert out["fragile_profit"] == 800.0
        assert out["fragile_profit_share"] == 0.8  # 800/1000 — 체결 낙관 의존 80%.
        assert out["robust_profit"] == 200.0

    def test_graceful_on_missing_column_or_file(self, tmp_path) -> None:
        bad = tmp_path / "bad.csv"
        bad.write_text("종목명,수익금\nT,1\n", encoding="utf-8-sig")
        assert fill_fragility(str(bad)) is None
        assert fill_fragility(str(tmp_path / "none.csv")) is None
