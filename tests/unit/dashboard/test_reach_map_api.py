"""QSP10 P4 — 도달 지도 API 계약: 권위 배지·표본수·사전 고정 배리어·저장 계보."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.dashboard import reach_map_api as api


NO_HIT = 600


@pytest.fixture
def loaded_view(monkeypatch) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    n = 5_000
    frame = pd.DataFrame({
        "일자": rng.choice([20240304, 20240305, 20240306], n),
        "종목코드": rng.choice(["000010", "000020"], n),
        "시분초": rng.choice([90100, 90500, 91500], n),
        "경과": 120,
        "관심종목": 1.0,
        "현재가": rng.uniform(1500, 40000, n),
        "spread_pct": rng.uniform(0.0, 0.9, n),
        "체결강도": rng.uniform(0, 300, n),
        "hit_up_2": rng.choice([50, 200, NO_HIT], n),
        "hit_dn_1": rng.choice([80, 300, NO_HIT], n),
        "frA_300": rng.normal(-0.4, 1.0, n),
    })
    view = api.apply_universe(frame, warmup=60)
    monkeypatch.setitem(api._view_cache, "tick", view)
    return view


def test_universe_status_reports_rows_and_authority(loaded_view) -> None:
    payload = api.universe_status(lane="tick")
    assert payload["available"] is True
    assert payload["rows"] == len(loaded_view)
    assert payload["authority"] == "exploratory"   # 공식 아님을 항상 표기
    assert payload["universe_version"]


def test_slider_query_returns_metrics_cluster_and_latency(loaded_view) -> None:
    query = api.SliderQuery(lane="tick", tp_pct=2.0, sl_pct=1.0,
                            clauses=[{"variable": "체결강도", "operator": ">", "value": 150.0}])
    result = api.slider_query(query)

    assert result["available"] is True
    assert result["rows"] < len(loaded_view)          # 필터가 실제로 걸렸다
    assert set(result["metrics"]) >= {"win_rate", "expectancy_pct", "breakeven_win_rate"}
    assert result["cluster"]["days"] > 0              # 자본 경로 경고 지표 동반
    assert result["elapsed_ms"] >= 0
    assert result["authority"] == "exploratory"


def test_slider_rejects_barrier_outside_fixed_grid(loaded_view) -> None:
    # 사전 고정 그리드에 없는 배리어는 라벨이 없으므로 거부 (사후 임계 선택 방지).
    result = api.slider_query(api.SliderQuery(lane="tick", tp_pct=2.5, sl_pct=1.0))
    assert result["available"] is False
    assert "배리어" in result["message"]


def test_slider_rejects_unknown_variable(loaded_view) -> None:
    query = api.SliderQuery(clauses=[{"variable": "없는변수", "operator": ">", "value": 1.0}])
    assert api.slider_query(query)["available"] is False


def test_cube_cells_carry_sample_counts(loaded_view) -> None:
    payload = api.cube(lane="tick", variable="체결강도", buckets=5)
    assert payload["available"] is True
    assert len(payload["cells"]) == 5
    assert all(cell["n"] > 0 for cell in payload["cells"])
    assert all("하한" in cell and "상한" in cell for cell in payload["cells"])


def test_candidate_save_records_lineage(loaded_view, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "_candidates_path", str(tmp_path / "cand.jsonl"))
    query = api.SliderQuery(clauses=[{"variable": "체결강도", "operator": ">", "value": 150.0}])
    saved = api.save_candidate(api.CandidateSave(name="QSP10_T1", query=query,
                                                 metrics={"expectancy_pct": 0.1}))
    assert saved["status"] == "ok"

    listed = api.list_candidates()
    assert listed["count"] == 1
    row = listed["candidates"][0]
    assert row["name"] == "QSP10_T1"
    assert row["query"]["clauses"][0]["variable"] == "체결강도"   # 근거 계보 보존
    assert row["authority"] == "exploratory"


def test_missing_labels_reports_actionable_message(monkeypatch) -> None:
    monkeypatch.setattr(api, "_view_cache", {})
    monkeypatch.setitem(api._LANE_DIRS, "min", "no_such_dir")
    payload = api.universe_status(lane="min")
    assert payload["available"] is False
    assert "build_labels" in payload["message"]      # 다음 조치가 화면에 보인다
