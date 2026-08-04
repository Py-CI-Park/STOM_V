"""G-0c 손실 영역 API 계약 — 페이지 17~21 의 데이터 공급자.

규율:
  - 프로파일·포켓은 진단(diagnostic), 후보·시뮬레이터는 자문(advisory) 권위다.
  - 시뮬레이터 응답에는 **재유입 미반영** 고지가 반드시 붙는다.
  - 분할은 lane_manifest 의 split_boundary 를 기본값으로 쓴다.
  - 두 구간 합계 = 전체(검산)를 split-diagnostics 가 보고한다.
"""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import loss_region_api
from ai_strategy_loop.dashboard.trade_path_api import trade_path_router


_FIELDS = ["종목명", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
           "매수금액", "매도금액", "수익률", "수익금",
           "B_등락율", "B_체결강도", "B_회전율", "B_시분초", "매도조건", "추가매수시간"]

SPLIT = 20250825


def _rows() -> list[dict[str, str]]:
    """설계 1,200건 + 홀드아웃 600건. 등락율 상위 구간에 손실을 몰아둔다."""
    out: list[dict[str, str]] = []
    for index in range(1800):
        design = index < 1200
        date = "20240401" if design else "20250901"
        bucket = index % 10
        profit = -9000 if bucket >= 8 else -500
        out.append({
            "종목명": f"종목{index}", "매수시간": f"{date}09{index % 60:02d}00",
            "매도시간": f"{date}091000", "보유시간": "60",
            "매수가": "1000", "매도가": "1000",
            "매수금액": "1000000", "매도금액": str(1_000_000 + profit),
            "수익률": "0.0", "수익금": str(profit),
            "B_등락율": f"{bucket}.5", "B_체결강도": f"{(index % 7) * 20 + 10}",
            "B_회전율": f"{(index % 5) + 0.5}", "B_시분초": f"9{index % 60:02d}00",
            "매도조건": "손절", "추가매수시간": "[]",
        })
    return out


class _Manager:
    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, job_id: str, log_tail: int = 0):
        del log_tail
        if job_id != "run1":
            return {"available": False}
        return {"available": True, "status": "success", "csv_path": str(self._path),
                "spec": {"timeframe": "tick", "start": 20240304, "end": 20260227,
                         "buy": "매수기준", "sell": "매도기준"}}

    def result_csv_path(self, job_id: str):
        return str(self._path) if job_id == "run1" else None


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    path = tmp_path / "run.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(_rows())
    monkeypatch.setattr(loss_region_api, "get_job_manager", lambda: _Manager(path))
    monkeypatch.setattr(
        loss_region_api, "baseline_code",
        lambda lane, kind: (
            "매수 = True\n\nif 관심종목 != 1:\n    매수 = False\n"
            "elif not (0 < 등락율 <= 25):\n    매수 = False\n\nif 매수:\n    self.Buy()\n"
        ),
    )
    loss_region_api.clear_run_cache()
    app = FastAPI()
    app.include_router(trade_path_router)
    return TestClient(app)


# --------------------------------------------------------------------------- 17 프로파일

def test_loss_profile_returns_variable_shapes(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get("/bt/trade-path/loss-profile?job_id=run1&lane=tick").json()
    assert body["available"] is True
    assert body["authority"] == "diagnostic"
    assert body["split"] == SPLIT
    names = {item["variable"] for item in body["profiles"]}
    assert "B_등락율" in names
    profile = next(item for item in body["profiles"] if item["variable"] == "B_등락율")
    assert profile["shape"] in {
        "monotone_up", "monotone_down", "tail_high", "tail_low",
        "valley", "multi_band", "flat",
    }
    assert "pareto" in body


def test_loss_profile_uses_manifest_split_by_default(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    default = client.get("/bt/trade-path/loss-profile?job_id=run1&lane=tick").json()
    explicit = client.get(
        f"/bt/trade-path/loss-profile?job_id=run1&lane=tick&split={SPLIT}"
    ).json()
    assert default["split"] == explicit["split"] == SPLIT
    assert default["design_rows"] == explicit["design_rows"] == 1200
    assert default["holdout_rows"] == 600


def test_loss_profile_missing_job_is_reported_not_raised(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get("/bt/trade-path/loss-profile?job_id=nope&lane=tick").json()
    assert body["available"] is False
    assert body["reason"] == "backtest_result_missing"


def test_unknown_lane_is_rejected(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get("/bt/trade-path/loss-profile?job_id=run1&lane=hour").json()
    assert body["available"] is False
    assert body["reason"] == "unknown_lane"


# --------------------------------------------------------------------------- 18 포켓

def test_loss_pockets_returns_fdr_filtered_cells(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get(
        "/bt/trade-path/loss-pockets?job_id=run1&lane=tick"
        "&variables=B_등락율,B_체결강도,B_회전율"
    ).json()
    assert body["available"] is True
    assert body["authority"] == "diagnostic"
    assert isinstance(body["pockets"], list)
    for pocket in body["pockets"]:
        assert pocket["max_q"] <= 0.10
        assert pocket["cells"] >= 2


def test_loss_pockets_reports_zero_without_pretending(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get(
        "/bt/trade-path/loss-pockets?job_id=run1&lane=tick&variables=B_시분초"
    ).json()
    # 변수 1개로는 쌍이 없다 — 0건이 정상이고 이유를 밝힌다.
    assert body["available"] is True
    assert body["pockets"] == []
    assert body["reason"] == "no_eligible_pair"


# --------------------------------------------------------------------------- 19 시뮬레이터

def test_removal_simulate_reports_retention_and_code(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.post("/bt/trade-path/removal-simulate", json={
        "job_id": "run1", "lane": "tick",
        "clauses": [{"terms": [[{"column": "B_등락율", "low": 7.0, "high": None}]]}],
    }).json()
    assert body["available"] is True
    assert body["authority"] == "advisory"
    assert 0.0 < body["design_retention"] < 1.0
    assert body["design_per_trade_after"] > body["design_per_trade_before"]
    assert "재유입" in body["caveat"]
    assert "ADD_REGION G" in body["stom_code"]


def test_removal_simulate_rejects_unknown_column(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.post("/bt/trade-path/removal-simulate", json={
        "job_id": "run1", "lane": "tick",
        "clauses": [{"terms": [[{"column": "B_없는변수", "low": 1.0, "high": None}]]}],
    }).json()
    assert body["available"] is False
    assert body["reason"] == "unknown_runtime_variable"


def test_removal_simulate_needs_at_least_one_clause(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    response = client.post("/bt/trade-path/removal-simulate", json={
        "job_id": "run1", "lane": "tick", "clauses": [],
    })
    assert response.status_code == 422


# --------------------------------------------------------------------------- 후보

def test_region_candidates_returns_bundles_with_budget(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.post("/bt/trade-path/region-candidates", json={
        "job_id": "run1", "lane": "tick", "generation": 1,
    }).json()
    assert body["available"] is True
    assert body["authority"] == "advisory"
    assert isinstance(body["candidates"], list)
    for candidate in body["candidates"]:
        assert candidate["budget"] == "ok"
        assert candidate["intent_gate"] == "pass"
        assert 1 <= len(candidate["clauses"]) <= 4
        for clause in candidate["clauses"]:
            # expression 은 @property 라 asdict 에 안 담긴다 — 빠지면 화면이 빈 칸이 된다.
            assert clause["expression"], clause
            assert clause["columns"]
            assert clause["source"]
    assert "skipped" in body


def test_region_candidates_can_build_on_a_named_baseline(monkeypatch, tmp_path):
    """2세대 이후 기준선은 직전 세대 채택 후보다 — manifest 기준선이 아니다."""
    client = _client(monkeypatch, tmp_path)
    # 세대 2 기준선 = 세대 1 후보(절이 이미 하나 붙어 있다).
    gen1_code = (
        "매수 = True\n\n"
        "if 관심종목 != 1:\n    매수 = False\n"
        "elif not (0 < 등락율 <= 25):\n    매수 = False\n"
        "elif 등락율 > 20:\n    매수 = False\n\n"
        "if 매수:\n    self.Buy()\n"
    )
    seen = {}

    def _fake_strategy_code(name, kind):
        seen["name"] = name
        return gen1_code

    monkeypatch.setattr(loss_region_api, "strategy_code", _fake_strategy_code)
    body = client.post("/bt/trade-path/region-candidates", json={
        "job_id": "run1", "lane": "tick", "generation": 2,
        "prior_retention": 0.88, "baseline_strategy": "QSP7_G1_tick_4절_20260804",
    }).json()
    assert body["available"] is True
    assert body["baseline_strategy"] == "QSP7_G1_tick_4절_20260804"
    assert seen["name"] == "QSP7_G1_tick_4절_20260804"


def test_missing_named_baseline_is_reported_distinctly(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(loss_region_api, "strategy_code", lambda name, kind: "")
    body = client.post("/bt/trade-path/region-candidates", json={
        "job_id": "run1", "lane": "tick", "generation": 2,
        "baseline_strategy": "없는전략",
    }).json()
    assert body["available"] is False
    assert body["reason"] == "baseline_strategy_missing"


# --------------------------------------------------------------------------- 21 분할 진단

def test_split_diagnostics_reconciles_the_two_windows(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get("/bt/trade-path/split-diagnostics?job_id=run1&lane=tick").json()
    assert body["available"] is True
    assert body["authority"] == "official"
    assert body["split"] == SPLIT
    design, holdout = body["design"], body["holdout"]
    assert design["trades"] == 1200
    assert holdout["trades"] == 600
    assert design["trades"] + holdout["trades"] == body["whole"]["trades"]
    assert body["reconciled"] is True
    assert "자본" in body["caveat"]      # 연속 런 경고


# --------------------------------------------------------------------------- 20 세대

def test_generations_returns_empty_history_gracefully(monkeypatch, tmp_path):
    """이력이 없을 때의 응답 — 실제 운영 이력 파일에 의존하면 안 된다(격리)."""
    from ai_strategy_loop.revision import generation_runner as gr

    monkeypatch.setattr(gr, "_path", lambda: tmp_path / "no_generations.jsonl")
    client = _client(monkeypatch, tmp_path)
    body = client.get("/bt/trade-path/generations?lane=tick").json()
    assert body["available"] is True
    assert body["generations"] == []
    assert body["verdict"] == "not_started"


# --------------------------------------------------------------------------- 보안

def test_mutating_routes_require_safe_backtest_capability():
    from ai_strategy_loop.dashboard.security_capabilities import (
        Capability, HTTP_CAPABILITIES,
    )
    for route in ("/bt/trade-path/removal-simulate", "/bt/trade-path/region-candidates"):
        assert HTTP_CAPABILITIES[("POST", route)] is Capability.SAFE_BACKTEST
