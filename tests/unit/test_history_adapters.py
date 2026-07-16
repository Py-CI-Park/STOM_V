"""G002 -- CampaignAdapter/LoopRunAdapter 단위 테스트 (condition_history_v1 read model).

검증:
  - CampaignAdapter: research_records fixture(tmp evidence dir)를 그대로 읽어
    ResearchNode(source_kind="campaign")로 매핑하고, 아티팩트 참조에 절대경로가
    없으며, validate_research_node가 통과한다.
  - LoopRunAdapter: tmp sqlite(LoopState)에 parent_gen 계보가 있는 2세대를
    심어 ResearchNode(source_kind="loop_run")로 매핑하고, 계보 parent link가
    label에 그대로 보존되며, DB가 없으면 예외 없이 state_unavailable을 낸다.

합성 데이터만 사용(백테/루프 실행 없음). 두 어댑터 모두 read-only이므로
DB/evidence 원본을 변형하지 않는다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard.history_adapters import (  # noqa: E402
    CampaignAdapter,
    LoopRunAdapter,
)
from cli.condition_history_schema import (  # noqa: E402
    COVERAGE_STATUSES,
    EVALUATION_STATUSES,
    validate_research_node,
)


def _write_campaign(root: Path, name: str = "campaign_alpha") -> None:
    """research_records.py 테스트 관례와 동일한 fixture(summary+jsonl)를 만든다."""
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}_summary.json").write_text(
        json.dumps({"best_overall": {"label": "alpha", "profit": 1200, "mdd": 3.4}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / f"{name}.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event": "cand", "label": "alpha", "profit": 1200, "mdd": 3.4, "trades": 8, "gate": True}),
                json.dumps({"event": "cand", "label": "beta", "profit": 0, "mdd": 0.0, "trades": 0, "gate": False}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class TestCampaignAdapter:
    def test_build_research_node_maps_candidates_and_strips_absolute_paths(self, tmp_path: Path) -> None:
        evidence = tmp_path / "evidence"
        _write_campaign(evidence, "campaign_alpha")

        adapter = CampaignAdapter(evidence_root=evidence)
        result = adapter.build_research_node("campaign_alpha")

        assert result["available"] is True
        assert result["reason"] is None
        research = result["research"]
        assert research is not None
        assert research["research_id"] == "campaign:campaign_alpha"
        assert research["label"] == "campaign_alpha"
        assert research["coverage_status"] in COVERAGE_STATUSES

        stage = research["stages"][0]
        assert stage["research_id"] == research["research_id"]
        labels = {c["label"] for c in stage["conditions"]}
        assert labels == {"alpha", "beta"}

        by_label = {c["label"]: c for c in stage["conditions"]}
        alpha_eval = by_label["alpha"]["evaluations"][0]
        assert alpha_eval["status"] == "success"
        assert alpha_eval["metrics"]["profit"] == 1200
        assert alpha_eval["condition_id"] == by_label["alpha"]["condition_id"]

        beta_eval = by_label["beta"]["evaluations"][0]
        assert beta_eval["status"] == "no_trades"

        # 스키마 자체 구조 검증(중복 id/고아 parent/알 수 없는 상태 없음).
        assert validate_research_node(research) == []

        # 아티팩트 참조는 상대(파일명)만 -- 절대경로가 어디에도 없다.
        artifact_refs = result["artifact_refs"]
        assert artifact_refs is not None
        flat_values = json.dumps(artifact_refs, ensure_ascii=False)
        assert str(evidence) not in flat_values
        assert not os.path.isabs(artifact_refs.get("summary") or "")

    def test_build_research_node_missing_campaign_is_typed_not_exception(self, tmp_path: Path) -> None:
        evidence = tmp_path / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)

        adapter = CampaignAdapter(evidence_root=evidence)
        result = adapter.build_research_node("does_not_exist")

        assert result["available"] is False
        assert result["reason"] == "missing_campaign"
        assert result["research"] is None
        assert result["artifact_refs"] is None


def _seed_two_generations(db_path: Path, snapshot_dir: Path, run_id: str) -> None:
    """parent_gen 계보가 있는 2세대(gen0 부모 <- gen1 자식)를 tmp sqlite에 심는다."""
    state = LoopState(db_path=str(db_path), snapshot_dir=str(snapshot_dir))
    try:
        state.start_run(LoopConfig(), run_id=run_id)
        state.record_generation(
            run_id, 0,
            buy_name=f"AILOOP_{run_id}_g0_buy", sell_name=f"AILOOP_{run_id}_g0_sell",
            status="ok", score=1.0, gate_passed=True,
            trade_count=40, mdd=15.0, profit=100000.0, total_profit_pct=10.0,
            daily_avg_trades=1.2,
        )
        state.record_generation(
            run_id, 1,
            buy_name=f"AILOOP_{run_id}_g1_buy", sell_name=f"AILOOP_{run_id}_g1_sell",
            status="ok", score=1.4, gate_passed=True,
            trade_count=30, mdd=10.0, profit=150000.0, total_profit_pct=15.0,
            daily_avg_trades=1.0,
            parent_gen=0, diff_from_parent="gen0 대비: graded +0.4",
            hypotheses_json=json.dumps([{"claim": "진입 강화", "verdict": "accepted"}]),
        )
    finally:
        state.close()


class TestLoopRunAdapter:
    def test_build_research_node_maps_lineage_and_metrics(self, tmp_path: Path) -> None:
        db_path = tmp_path / "loop_runs.db"
        snap_dir = tmp_path / "snapshots"
        run_id = "runA"
        _seed_two_generations(db_path, snap_dir, run_id)

        adapter = LoopRunAdapter(db_path=str(db_path))
        result = adapter.build_research_node(run_id)

        assert result["available"] is True
        assert result["reason"] is None
        research = result["research"]
        assert research is not None
        assert research["research_id"] == f"loop_run:{run_id}"
        assert validate_research_node(research) == []

        stage = research["stages"][0]
        conditions = {c["condition_id"]: c for c in stage["conditions"]}
        gen0_id = f"cond:{run_id}:gen0"
        gen1_id = f"cond:{run_id}:gen1"
        assert set(conditions) == {gen0_id, gen1_id}

        gen0_label = json.loads(conditions[gen0_id]["label"])
        assert gen0_label["gen_no"] == 0
        assert gen0_label["parent_gen"] is None
        assert gen0_label["parent_condition_id"] is None
        assert gen0_label["hypotheses_present"] is False
        assert gen0_label["code_lookup_status"] == "name_only"

        gen1_label = json.loads(conditions[gen1_id]["label"])
        assert gen1_label["gen_no"] == 1
        assert gen1_label["parent_gen"] == 0
        # 계보 parent link -- gen1의 부모 조건 id는 gen0의 condition_id와 일치.
        assert gen1_label["parent_condition_id"] == gen0_id
        assert gen1_label["hypotheses_present"] is True

        gen1_eval = conditions[gen1_id]["evaluations"][0]
        assert gen1_eval["status"] in EVALUATION_STATUSES
        assert gen1_eval["metrics"]["trade_count"] == 30.0
        assert gen1_eval["metrics"]["mdd"] == 10.0
        assert gen1_eval["metrics"]["profit"] == 150000.0
        assert gen1_eval["metrics"]["total_profit_pct"] == 15.0
        assert gen1_eval["metrics"]["daily_avg_trades"] == 1.0

    def test_build_research_node_missing_db_is_typed_not_exception(self, tmp_path: Path) -> None:
        db_path = tmp_path / "does_not_exist" / "loop_runs.db"

        adapter = LoopRunAdapter(db_path=str(db_path))
        result = adapter.build_research_node("any_run")

        assert result["available"] is False
        assert result["reason"] == "state_unavailable"
        assert result["research"] is None

    def test_build_research_node_missing_run_in_existing_db_is_typed(self, tmp_path: Path) -> None:
        db_path = tmp_path / "loop_runs.db"
        snap_dir = tmp_path / "snapshots"
        _seed_two_generations(db_path, snap_dir, "runB")

        adapter = LoopRunAdapter(db_path=str(db_path))
        result = adapter.build_research_node("no_such_run")

        assert result["available"] is False
        assert result["reason"] == "missing_run"
        assert result["research"] is None
