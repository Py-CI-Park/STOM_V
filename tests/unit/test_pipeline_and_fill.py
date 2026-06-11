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
    pending_stages,
)


class TestPipelineCheckpoint:
    def test_done_stages_skipped(self) -> None:
        state = {"sweep": "done", "theta_star": "done"}
        assert pending_stages(state) == ["reeval", "freeze", "oos2022", "oos2026"]

    def test_failed_stage_reruns(self) -> None:
        state = {"sweep": "done", "theta_star": "failed rc=2"}
        assert pending_stages(state)[0] == "theta_star"

    def test_from_stage_forces_rerun_of_suffix(self) -> None:
        state = {s: "done" for s in STAGES}
        assert pending_stages(state, from_stage="freeze") == ["freeze", "oos2022", "oos2026"]
        with pytest.raises(ValueError):
            pending_stages(state, from_stage="nope")

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
