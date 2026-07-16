"""G003 -- /history/index, /history/detail 라우터 단위 테스트.

``fastapi.testclient.TestClient``로 ``history_router``만 담은 최소 FastAPI
앱을 띄워 검증한다:

  - limit>100 -> 422
  - 커서 왕복(roundtrip)
  - 손상된 커서 -> 400
  - stale 시그니처(데이터 변경 후 옛 커서 재사용) -> 409
  - q(대소문자 무관 부분일치) 필터
  - detail evaluations 섹션 페이지네이션 총합 = flat_rows 전체 개수
  - 알 수 없는 research_id -> typed available=False(예외 없음)
  - 루프런 경로: tmp sqlite(LoopState) 2세대 시딩

캠페인 fixture는 ``tests/unit/test_history_adapters.py``의 관례(summary+jsonl)를
그대로 재사용한다. 절대경로 유출 가드도 함께 검증한다(json.dumps 결과에
``:\\``/``C:/`` 패턴이 없어야 한다).
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
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard import history_api  # noqa: E402
from cli.condition_history_schema import flat_rows  # noqa: E402


def _write_campaign(root: Path, name: str = "campaign_alpha") -> None:
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


def _seed_two_generations(db_path: Path, snapshot_dir: Path, run_id: str) -> None:
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
        )
    finally:
        state.close()


@pytest.fixture()
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(history_api.history_router)
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def campaign_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    evidence = tmp_path / "evidence"
    _write_campaign(evidence, "campaign_alpha")
    monkeypatch.setattr(history_api, "EVIDENCE_ROOT", evidence)
    # loop_run 소스는 존재하지 않는 tmp 경로로 고정해 캠페인 전용 테스트를 격리한다.
    monkeypatch.setattr(history_api, "LOOP_RUNS_DB", tmp_path / "no_such" / "loop_runs.db")
    return evidence


@pytest.fixture()
def loop_run_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_path = tmp_path / "loop_runs.db"
    _seed_two_generations(db_path, tmp_path / "snapshots", "runA")
    monkeypatch.setattr(history_api, "LOOP_RUNS_DB", db_path)
    monkeypatch.setattr(history_api, "EVIDENCE_ROOT", tmp_path / "no_such_evidence")
    return "runA"


# ---------------------------------------------------------------------------
# /history/index
# ---------------------------------------------------------------------------


class TestHistoryIndex:
    def test_limit_over_max_is_422(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get("/history/index", params={"limit": 101})
        assert resp.status_code == 422

    def test_cursor_roundtrip_covers_all_items(self, client: TestClient, campaign_env: Path) -> None:
        first = client.get("/history/index", params={"limit": 1}).json()
        assert len(first["items"]) == 1
        assert first["total"] == 1
        assert first["next_cursor"] is None  # 캠페인 1건뿐이라 다음 페이지 없음.

        # 다음 페이지가 있는 상황을 만들기 위해 캠페인을 하나 더 추가한다.
        _write_campaign(campaign_env, "campaign_beta")
        first = client.get("/history/index", params={"limit": 1}).json()
        assert first["total"] == 2
        assert first["next_cursor"] is not None

        second = client.get("/history/index", params={"limit": 1, "cursor": first["next_cursor"]}).json()
        assert second["next_cursor"] is None
        ids = {item["research_id"] for item in first["items"]} | {item["research_id"] for item in second["items"]}
        assert ids == {"campaign:campaign_alpha", "campaign:campaign_beta"}

    def test_corrupted_cursor_is_400(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get("/history/index", params={"cursor": "not-valid-base64!!"})
        assert resp.status_code == 400

    def test_stale_signature_is_409(self, client: TestClient, campaign_env: Path) -> None:
        _write_campaign(campaign_env, "campaign_beta")
        first = client.get("/history/index", params={"limit": 1}).json()
        assert first["next_cursor"] is not None

        # 데이터가 바뀌면(캠페인 추가) 정렬된 id 시퀀스가 바뀌어 옛 커서는 stale.
        _write_campaign(campaign_env, "campaign_gamma")
        resp = client.get("/history/index", params={"limit": 1, "cursor": first["next_cursor"]})
        assert resp.status_code == 409

    def test_q_filters_by_casefold_substring(self, client: TestClient, campaign_env: Path) -> None:
        _write_campaign(campaign_env, "campaign_beta")
        resp = client.get("/history/index", params={"q": "ALPHA"}).json()
        assert resp["total"] == 1
        assert resp["items"][0]["research_id"] == "campaign:campaign_alpha"

    def test_no_absolute_paths_leak(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get("/history/index")
        text = json.dumps(resp.json(), ensure_ascii=False)
        assert ":\\" not in text
        assert "C:/" not in text

    def test_loop_run_items_are_listed(self, client: TestClient, loop_run_env: str) -> None:
        resp = client.get("/history/index", params={"source_kind": "loop_run"}).json()
        assert resp["total"] == 1
        item = resp["items"][0]
        assert item["research_id"] == f"loop_run:{loop_run_env}"
        assert item["source_kind"] == "loop_run"
        assert item["counts"] == {"stages": 1, "conditions": 2, "evaluations": 2}


# ---------------------------------------------------------------------------
# /history/detail
# ---------------------------------------------------------------------------


class TestHistoryDetail:
    def test_unknown_research_id_is_typed_available_false(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get(
            "/history/detail",
            params={"research_id": "campaign:does_not_exist", "section": "research"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is False
        assert isinstance(body["reason"], str) and body["reason"]
        assert body["research_id"] == "campaign:does_not_exist"

    def test_malformed_research_id_is_typed_available_false(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get(
            "/history/detail",
            params={"research_id": "not_a_valid_id", "section": "research"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is False
        assert body["reason"] == "invalid_research_id"

    def test_limit_over_max_is_422(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get(
            "/history/detail",
            params={"research_id": "campaign:campaign_alpha", "section": "evaluations", "limit": 101},
        )
        assert resp.status_code == 422

    def test_unknown_section_is_422(self, client: TestClient, campaign_env: Path) -> None:
        resp = client.get(
            "/history/detail",
            params={"research_id": "campaign:campaign_alpha", "section": "bogus"},
        )
        assert resp.status_code == 422

    def test_evaluations_pagination_sums_to_total(self, client: TestClient, loop_run_env: str) -> None:
        research_id = f"loop_run:{loop_run_env}"
        collected: list[dict] = []
        cursor = None
        for _ in range(10):
            params = {"research_id": research_id, "section": "evaluations", "limit": 1}
            if cursor:
                params["cursor"] = cursor
            body = client.get("/history/detail", params=params).json()
            assert body["available"] is True
            collected.extend(body["rows"])
            cursor = body["next_cursor"]
            if cursor is None:
                break
        assert cursor is None
        assert len(collected) == 2

        # loop_run 원본 트리와 직접 비교 -- flat_rows 전체 개수와 정확히 일치.
        from ai_strategy_loop.dashboard.history_adapters import LoopRunAdapter

        adapter = LoopRunAdapter(db_path=str(history_api.LOOP_RUNS_DB))
        research = adapter.build_research_node(loop_run_env)["research"]
        assert len(collected) == len(flat_rows(research))
        assert {row["evaluation_id"] for row in collected} == {row["evaluation_id"] for row in flat_rows(research)}

    def test_corrupted_cursor_is_400(self, client: TestClient, loop_run_env: str) -> None:
        resp = client.get(
            "/history/detail",
            params={
                "research_id": f"loop_run:{loop_run_env}",
                "section": "evaluations",
                "cursor": "%%%not-base64%%%",
            },
        )
        assert resp.status_code == 400

    def test_stale_cursor_is_409_after_new_generation(self, client: TestClient, loop_run_env: str) -> None:
        research_id = f"loop_run:{loop_run_env}"
        first = client.get(
            "/history/detail",
            params={"research_id": research_id, "section": "evaluations", "limit": 1},
        ).json()
        assert first["next_cursor"] is not None

        # 새 세대를 추가해 evaluation id 시퀀스를 바꾼다 -> 이전 커서는 stale.
        state = LoopState(db_path=str(history_api.LOOP_RUNS_DB))
        try:
            state.record_generation(
                loop_run_env, 2,
                buy_name=f"AILOOP_{loop_run_env}_g2_buy", sell_name=f"AILOOP_{loop_run_env}_g2_sell",
                status="ok", score=1.6, gate_passed=True,
                trade_count=25, mdd=9.0, profit=160000.0, total_profit_pct=16.0,
                daily_avg_trades=0.9, parent_gen=1,
            )
        finally:
            state.close()

        resp = client.get(
            "/history/detail",
            params={"research_id": research_id, "section": "evaluations", "cursor": first["next_cursor"]},
        )
        assert resp.status_code == 409

    def test_research_section_returns_node_summary(self, client: TestClient, loop_run_env: str) -> None:
        resp = client.get(
            "/history/detail",
            params={"research_id": f"loop_run:{loop_run_env}", "section": "research"},
        ).json()
        assert resp["available"] is True
        assert resp["node"]["research_id"] == f"loop_run:{loop_run_env}"
        assert resp["node"]["counts"] == {"stages": 1, "conditions": 2, "evaluations": 2}
        assert resp["rows"] is None
        assert resp["next_cursor"] is None

    def test_stages_and_conditions_sections(self, client: TestClient, loop_run_env: str) -> None:
        research_id = f"loop_run:{loop_run_env}"
        stages = client.get(
            "/history/detail", params={"research_id": research_id, "section": "stages"}
        ).json()
        assert stages["available"] is True
        assert len(stages["rows"]) == 1
        assert stages["rows"][0]["condition_count"] == 2

        conditions = client.get(
            "/history/detail", params={"research_id": research_id, "section": "conditions"}
        ).json()
        assert len(conditions["rows"]) == 2
        assert {row["evaluation_count"] for row in conditions["rows"]} == {1}

    def test_no_absolute_paths_leak(self, client: TestClient, loop_run_env: str) -> None:
        resp = client.get(
            "/history/detail",
            params={"research_id": f"loop_run:{loop_run_env}", "section": "evaluations"},
        )
        text = json.dumps(resp.json(), ensure_ascii=False)
        assert ":\\" not in text
        assert "C:/" not in text
