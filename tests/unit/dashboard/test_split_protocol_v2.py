"""평가 프로토콜 v2 계약 — 연속 1회 런 + CSV 날짜 분할(G-0d).

핵심:
  - `official-pair` 에 period 를 주면 그 기간 거래만 비교한다.
  - `promotion-gate` 2-job 모드는 **같은 job 한 쌍**을 기간으로 갈라 판정한다.
  - 두 구간 합계 = 전체(검산). 어긋나면 분할이 구간을 빠뜨린 것이다.
  - 기존 4-job 모드는 그대로 동작한다(회귀 방어).
"""

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

DESIGN_PERIOD = {"t_start": 20240304, "t_end": 20250822}
HOLDOUT_PERIOD = {"t_start": 20250825, "t_end": 20260227}


def _write(path: Path, rows: list[tuple[str, str, int]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        for name, buy_time, profit in rows:
            writer.writerow({
                "종목명": name, "매수시간": buy_time,
                "매도시간": buy_time[:8] + "091000", "보유시간": "60",
                "매수가": "1000", "매도가": "1000",
                "매수금액": "1000000", "매도금액": str(1_000_000 + profit),
                "수익률": "0.0", "수익금": str(profit),
                "매도조건": "손절", "추가매수시간": "[]",
            })


class _Manager:
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


# 연속 1회 런: 설계 구간 3건 + 홀드아웃 구간 2건 = 전체 5건.
_BASE_ROWS = [
    ("A", "20240401090000", -30_000),   # 설계
    ("B", "20240402090000", -20_000),   # 설계
    ("C", "20250801090000", -10_000),   # 설계
    ("D", "20250901090000", -40_000),   # 홀드아웃
    ("E", "20251001090000", +10_000),   # 홀드아웃
]
# 후보: 설계 1건(A) · 홀드아웃 1건(D) 을 잘라낸다 → 양 구간 모두 건당 개선.
_CANDIDATE_ROWS = [
    ("B", "20240402090000", -20_000),
    ("C", "20250801090000", -10_000),
    ("E", "20251001090000", +10_000),
]
# 나쁜 후보: 설계만 개선하고 홀드아웃은 악화한다.
_OVERFIT_ROWS = [
    ("B", "20240402090000", -20_000),
    ("C", "20250801090000", -10_000),
    ("D", "20250901090000", -90_000),
    ("E", "20251001090000", +10_000),
]


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    spec = {"timeframe": "tick", "start": 20240304, "end": 20260227,
            "divid_mode": "종목코드별 분류", "one_code": None, "back_db_override": None}
    paths = {
        "base": tmp_path / "base.csv",
        "cand": tmp_path / "cand.csv",
        "overfit": tmp_path / "overfit.csv",
    }
    _write(paths["base"], _BASE_ROWS)
    _write(paths["cand"], _CANDIDATE_ROWS)
    _write(paths["overfit"], _OVERFIT_ROWS)
    specs = {
        "base": {**spec, "buy": "매수기준", "sell": "매도기준"},
        "cand": {**spec, "buy": "매수후보", "sell": "매도기준"},
        "overfit": {**spec, "buy": "과최적후보", "sell": "매도기준"},
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


# --------------------------------------------------------------------------- period

def test_official_pair_without_period_covers_the_whole_run(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    pair = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "cand", "axis": "buy",
    }).json()
    assert pair["available"] is True
    assert pair["pair"]["baseline_trade_count"] == 5
    assert pair["pair"]["candidate_trade_count"] == 3


def test_official_pair_with_period_limits_to_that_window(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    design = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "cand", "axis": "buy",
        "period": DESIGN_PERIOD,
    }).json()
    assert design["available"] is True
    assert design["pair"]["baseline_trade_count"] == 3     # A·B·C
    assert design["pair"]["candidate_trade_count"] == 2    # B·C
    assert design["period"] == DESIGN_PERIOD


def test_two_windows_sum_to_the_whole_run(monkeypatch, tmp_path):
    """검산 — 분할이 거래를 빠뜨리거나 중복 세면 안 된다."""
    client = _client(monkeypatch, tmp_path)

    def counts(period):
        body = client.post("/bt/trade-path/official-pair", json={
            "baseline_job_id": "base", "candidate_job_id": "cand",
            "axis": "buy", **({"period": period} if period else {}),
        }).json()["pair"]
        return body["baseline_trade_count"], body["candidate_trade_count"]

    whole = counts(None)
    design = counts(DESIGN_PERIOD)
    holdout = counts(HOLDOUT_PERIOD)
    assert (design[0] + holdout[0], design[1] + holdout[1]) == whole


def test_period_outside_the_run_yields_empty_not_error(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "base", "candidate_job_id": "cand", "axis": "buy",
        "period": {"t_start": 20300101, "t_end": 20301231},
    }).json()
    assert body["available"] is True
    assert body["pair"]["baseline_trade_count"] == 0
    assert body["pair"]["matched_count"] == 0


# --------------------------------------------------------------------------- 2-job gate

def test_two_job_gate_adopts_when_both_windows_improve(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    gate = client.post("/bt/trade-path/promotion-gate", json={
        "baseline_job_id": "base", "candidate_job_id": "cand", "axis": "buy",
        "design_period": DESIGN_PERIOD, "holdout_period": HOLDOUT_PERIOD,
    }).json()
    assert gate["mode"] == "2job_split"
    assert gate["blockers"] == [], gate["blockers"]
    assert gate["verdict"] == "adoptable"
    assert gate["split_reconciled"] is True
    # v2 는 "OOS" 가 아니라 "홀드아웃" 이라 부른다.
    assert "holdout" in gate


def test_two_job_gate_blocks_design_only_improvement(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    gate = client.post("/bt/trade-path/promotion-gate", json={
        "baseline_job_id": "base", "candidate_job_id": "overfit", "axis": "buy",
        "design_period": DESIGN_PERIOD, "holdout_period": HOLDOUT_PERIOD,
    }).json()
    assert gate["verdict"] == "blocked"
    assert any("holdout" in blocker for blocker in gate["blockers"]), gate["blockers"]


def test_two_job_gate_rejects_overlapping_windows(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    gate = client.post("/bt/trade-path/promotion-gate", json={
        "baseline_job_id": "base", "candidate_job_id": "cand", "axis": "buy",
        "design_period": {"t_start": 20240304, "t_end": 20251001},
        "holdout_period": HOLDOUT_PERIOD,
    }).json()
    assert gate["verdict"] == "blocked"
    assert "design_holdout_period_overlap" in gate["blockers"]


def test_two_job_gate_reports_per_trade_edge_for_buy_axis(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    gate = client.post("/bt/trade-path/promotion-gate", json={
        "baseline_job_id": "base", "candidate_job_id": "cand", "axis": "buy",
        "design_period": DESIGN_PERIOD, "holdout_period": HOLDOUT_PERIOD,
    }).json()
    assert gate["design_per_trade_delta"] > 0
    assert gate["holdout_per_trade_delta"] > 0
    assert gate["design_trade_ratio"] is not None


def test_mixed_mode_request_is_rejected(monkeypatch, tmp_path):
    """4-job 필드와 2-job 필드를 섞으면 어떤 판정인지 모호하다 — 거부한다."""
    client = _client(monkeypatch, tmp_path)
    response = client.post("/bt/trade-path/promotion-gate", json={
        "baseline_job_id": "base", "candidate_job_id": "cand",
        "design_baseline_job_id": "base", "design_candidate_job_id": "cand",
        "axis": "buy",
    })
    assert response.status_code == 422


# --------------------------------------------------------------------------- 4-job 회귀

def test_four_job_mode_still_works(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    gate = client.post("/bt/trade-path/promotion-gate", json={
        "design_baseline_job_id": "base", "design_candidate_job_id": "cand",
        "oos_baseline_job_id": "base", "oos_candidate_job_id": "cand",
        "axis": "buy",
    }).json()
    assert gate["mode"] == "4job_independent"
    # 같은 job 을 양쪽에 쓰면 기간이 겹쳐 차단되는 기존 동작 유지.
    assert "design_oos_period_overlap" in gate["blockers"]
    assert "design" in gate and "oos" in gate
