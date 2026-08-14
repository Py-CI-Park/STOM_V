"""R2-1 공식 pair 축(axis) 계약 — 매도 축은 진입 고정, 매수 축은 진입 변화를 전제한다."""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import trade_path_jobs, trade_path_official_api
from ai_strategy_loop.dashboard.research_sidecar import ResearchSidecar
from ai_strategy_loop.dashboard.trade_path_api import trade_path_router
from ai_strategy_loop.dashboard.trade_path_jobs import TradePathCoordinator
from ai_strategy_loop.dashboard.trade_path_ledger import TradePathLedger


_FIELDS = ["종목명", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
           "매수금액", "매도금액", "수익률", "수익금", "매도조건", "추가매수시간"]


def _write(path: Path, rows: list[tuple[str, str, int]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        for name, buy_time, profit in rows:
            writer.writerow({
                "종목명": name, "매수시간": buy_time, "매도시간": "20250102091000",
                "보유시간": "60", "매수가": "1000", "매도가": "1000",
                "매수금액": "1000000", "매도금액": str(1_000_000 + profit),
                "수익률": "0.0", "수익금": str(profit),
                "매도조건": "손절", "추가매수시간": "[]",
            })


class _Manager:
    """buy/sell 이 서로 다른 조합을 만들어 축 판정을 검사한다."""

    def __init__(self, specs: dict[str, dict], paths: dict[str, Path]) -> None:
        self._specs, self._paths = specs, paths

    def get(self, job_id: str, log_tail: int = 0):
        del log_tail
        if job_id not in self._specs:
            return {"available": False}
        return {"available": True, "status": "success",
                "csv_path": str(self._paths[job_id]), "spec": self._specs[job_id]}

    def result_csv_path(self, job_id: str):
        path = self._paths.get(job_id)
        return str(path) if path is not None else None


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    base_spec = {"timeframe": "min", "start": 20250102, "end": 20250102,
                 "divid_mode": "종목코드별 분류", "one_code": None, "back_db_override": None}
    # 기준선 3거래 / 매수축 후보: 필터로 1건 제거(2거래) · 매도식 동일
    # 매도축 후보: 진입 동일(3거래) · 매도식만 변경
    paths = {
        "base": tmp_path / "base.csv",
        "buy_cand": tmp_path / "buy.csv",
        "sell_cand": tmp_path / "sell.csv",
        "design_base": tmp_path / "design_base.csv",
        "design_cand": tmp_path / "design_cand.csv",
        "oos_base": tmp_path / "oos_base.csv",
        "oos_cand": tmp_path / "oos_cand.csv",
    }
    _write(paths["base"], [("A", "20250102090000", -30_000),
                           ("B", "20250102090100", -20_000),
                           ("C", "20250102090200", +10_000)])
    _write(paths["buy_cand"], [("B", "20250102090100", -20_000),
                               ("C", "20250102090200", +10_000)])
    _write(paths["sell_cand"], [("A", "20250102090000", -10_000),
                                ("B", "20250102090100", -20_000),
                                ("C", "20250102090200", +10_000)])
    _write(paths["design_base"], [("A", "20250102090000", -30_000),
                                  ("B", "20250102090100", -20_000)])
    _write(paths["design_cand"], [("B", "20250102090100", -20_000)])
    _write(paths["oos_base"], [("D", "20250103090000", -40_000),
                               ("E", "20250103090100", +10_000)])
    _write(paths["oos_cand"], [("E", "20250103090100", +10_000)])
    specs = {
        "base": {**base_spec, "buy": "매수기준", "sell": "매도기준"},
        "buy_cand": {**base_spec, "buy": "매수필터후보", "sell": "매도기준"},
        "sell_cand": {**base_spec, "buy": "매수기준", "sell": "매도후보"},
        "design_base": {**base_spec, "buy": "매수기준", "sell": "매도기준"},
        "design_cand": {**base_spec, "buy": "매수필터후보", "sell": "매도기준"},
        "oos_base": {**base_spec, "start": 20250103, "end": 20250103,
                     "buy": "매수기준", "sell": "매도기준"},
        "oos_cand": {**base_spec, "start": 20250103, "end": 20250103,
                     "buy": "매수필터후보", "sell": "매도기준"},
    }
    manager = _Manager(specs, paths)
    monkeypatch.setattr(
        trade_path_jobs, "_COORDINATOR",
        TradePathCoordinator(ledger=TradePathLedger(tmp_path / "l.jsonl"),
                             sidecar=ResearchSidecar(tmp_path / "s.db")),
    )
    monkeypatch.setattr(trade_path_official_api, "get_job_manager", lambda: manager)
    app = FastAPI()
    app.include_router(trade_path_router)
    return TestClient(app)


def _official_pairs(client: TestClient) -> list[dict[str, object]]:
    return client.get("/bt/trade-path/history").json()["official_pairs"]


def _calibration_records(client: TestClient) -> list[dict[str, object]]:
    return client.get("/bt/trade-path/calibration?lane=min").json()["records"]


def test_sell_axis_still_requires_identical_buy_condition(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    # 매도 축인데 매수식이 다르면 여전히 차단(진입 고정 전제가 깨짐).
    blocked = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "buy_cand", "axis": "sell",
    }).json()
    assert blocked["available"] is False
    assert "buy_condition" in blocked["mismatches"]

    # 매도식만 다른 정상 pair 는 통과.
    ok = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "sell_cand", "axis": "sell",
    }).json()
    assert ok["available"] is True
    assert ok["pair"]["axis"] == "sell"
    assert ok["pair"]["matched_count"] == 3


def test_buy_axis_allows_changed_entries_but_locks_the_sell_side(
    monkeypatch, tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)

    # 매수 축: 진입이 달라지는 것이 정상 — 차단하지 않는다.
    pair = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "buy_cand", "axis": "buy",
    }).json()
    assert pair["available"] is True, pair
    body = pair["pair"]
    assert body["axis"] == "buy"
    assert body["baseline_only_count"] == 1      # 필터로 제거된 진입
    assert body["candidate_only_count"] == 0
    assert body["baseline_trade_count"] == 3
    assert body["candidate_trade_count"] == 2
    # 총손익: -40,000 → -10,000 (개선), 건당: -13,333 → -5,000 (개선)
    assert body["delta_profit_krw"] == 30_000
    assert body["delta_per_trade_krw"] > 0

    # 매수 축이라도 매도식이 다르면 한 라운드 두 축이므로 차단.
    two_axis = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "sell_cand", "candidate_job_id": "buy_cand", "axis": "buy",
    }).json()
    assert two_axis["available"] is False
    assert "sell_condition" in two_axis["mismatches"]


def test_promotion_gate_blocks_edge_free_and_collapsed_trade_counts(
    monkeypatch, tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)

    gate = client.post("/bt/trade-path/promotion-gate", json={
        "design_baseline_job_id": "base", "design_candidate_job_id": "buy_cand",
        "oos_baseline_job_id": "base", "oos_candidate_job_id": "buy_cand",
        "axis": "buy",
    }).json()

    # 같은 job 을 설계/OOS 로 쓰면 기간이 겹치므로 차단되어야 한다(회귀 방어).
    assert gate["verdict"] == "blocked"
    assert "design_oos_period_overlap" in gate["blockers"]
    # 매수 축 게이트는 건당 엣지와 거래수 지표를 함께 보고한다.
    assert gate["axis"] == "buy"
    assert "design_per_trade_delta" in gate
    assert "design_trade_ratio" in gate


def test_blocked_promotion_gate_does_not_append_official_history(
    monkeypatch, tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)
    client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "sell_cand", "axis": "sell",
    })
    before = _official_pairs(client)
    assert len(before) == 1

    gate = client.post("/bt/trade-path/promotion-gate", json={
        "design_baseline_job_id": "base", "design_candidate_job_id": "buy_cand",
        "oos_baseline_job_id": "base", "oos_candidate_job_id": "buy_cand",
        "axis": "buy",
    }).json()

    assert gate["verdict"] == "blocked"
    assert _official_pairs(client) == before


def test_promotion_gate_persists_one_explicit_aggregate_receipt(
    monkeypatch, tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)
    for role, job_id in (("design", "design_cand"), ("oos", "oos_cand")):
        client.post("/bt/trade-path/candidate-runs", json={
            "candidate_id": f"candidate-{role}",
            "lane": "min",
            "role": role,
            "job_id": job_id,
            "sell_name": "매도기준",
            "axis": "buy",
            "buy_name": "매수필터후보",
        })
    body = {
        "design_baseline_job_id": "design_base",
        "design_candidate_job_id": "design_cand",
        "oos_baseline_job_id": "oos_base",
        "oos_candidate_job_id": "oos_cand",
        "axis": "buy",
    }

    read_gate = client.post("/bt/trade-path/promotion-gate", json=body).json()
    assert read_gate["verdict"] == "adoptable"
    assert _official_pairs(client) == []
    assert _calibration_records(client) == []

    persisted_gate = client.post(
        "/bt/trade-path/promotion-gate?persist=true", json=body,
    ).json()
    assert persisted_gate["verdict"] == "adoptable"
    receipts = _official_pairs(client)
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["receipt_type"] == "promotion_gate"
    assert receipt["gate"]["mode"] == "4job_independent"
    assert receipt["gate"]["baseline_job_ids"] == "design_base+oos_base"
    assert receipt["gate"]["candidate_job_ids"] == "design_cand+oos_cand"
    assert receipt["pair"]["receipt_type"] == "promotion_gate"
    assert receipt["pair"]["delta_profit_krw"] == 70_000
    assert receipt["pair"]["baseline_trade_count"] == 4
    assert receipt["pair"]["candidate_trade_count"] == 2
    assert _calibration_records(client) == []
