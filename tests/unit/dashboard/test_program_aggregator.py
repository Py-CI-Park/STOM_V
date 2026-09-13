"""ANA-07 — program fold/control aggregator + A/B 거래 분해 시험."""

from __future__ import annotations

import pytest

from ai_strategy_loop.dashboard import program_aggregator as pa
from tests.unit.dashboard.test_metric_definitions import _client


MANIFEST = pa.ProgramManifest(
    program_id="prog-1",
    candidate_ids=("c1", "c2"),
    folds=("f1", "f2"),
    controls=("ctrl-random",),
    families={"fam-a": ("h1", "h2")},
)


def _cells(*statuses):
    folds = ("f1", "f2")
    cands = ("c1", "c2")
    return [
        pa.CellResult(candidate_id=c, fold=f, status=s)
        for (c, f), s in zip(
            ((c, f) for c in cands for f in folds), statuses
        )
    ]


def test_completion_matrix_complete():
    m = pa.completion_matrix(MANIFEST, _cells(
        pa.CELL_OBSERVED, pa.CELL_OBSERVED, pa.CELL_OBSERVED, pa.CELL_NO_TRADES,
    ))
    assert m["program_complete"] is True
    assert m["matrix"]["c2"]["f2"] == "NO_TRADES"


def test_missing_fold_blocks_program_complete():
    cells = _cells(pa.CELL_OBSERVED, pa.CELL_OBSERVED, pa.CELL_OBSERVED)
    m = pa.completion_matrix(MANIFEST, cells)
    assert m["program_complete"] is False
    assert m["missing_cells"] == ["c2×f2"]
    assert m["matrix"]["c2"]["f2"] == "MISSING"  # 0/PASS 대체 아님.


def test_no_trades_is_not_synthesized_as_zero():
    m = pa.completion_matrix(MANIFEST, _cells(
        pa.CELL_NO_TRADES, pa.CELL_NO_TRADES, pa.CELL_NO_TRADES, pa.CELL_NO_TRADES,
    ))
    assert m["program_complete"] is True
    for row in m["matrix"].values():
        assert all(v == "NO_TRADES" for v in row.values())


def test_trade_decomposition():
    a = [{"name": "AAA", "buy_time": "1"}, {"name": "BBB", "buy_time": "2"}]
    b = [{"name": "BBB", "buy_time": "2"}, {"name": "CCC", "buy_time": "3"}]
    d = pa.decompose_trades(a, b)
    assert d["common"] == ["BBB|2"]
    assert d["removed"] == ["AAA|1"]
    assert d["new"] == ["CCC|3"]
    assert (d["n_common"], d["n_removed"], d["n_new"]) == (1, 1, 1)


def test_ab_eligibility_uses_admission_state():
    ok = {"admitted": True}
    bad = {"admitted": False, "reason": "partial"}
    assert pa.ab_eligible(ok, ok)["eligible"] is True
    res = pa.ab_eligible(ok, bad)
    assert res["eligible"] is False and res["reasons"] == ["b_not_admitted"]
    assert pa.ab_eligible(ok, None)["reasons"] == ["b_unresolved"]


def test_multiplicity_requires_method_receipts():
    hyps = [{"hypothesis_id": "h1", "family": "fam-a", "q": 0.03,
             "q_method": "bh_fdr"}]
    ledger = pa.multiplicity_ledger(MANIFEST, hyps)
    assert ledger["by_family"]["fam-a"] == 1
    assert ledger["entries"][0]["receipt"]["q_method"] == "bh_fdr"


def test_multiplicity_rejects_q_without_method():
    with pytest.raises(pa.AggregatorError) as ei:
        pa.multiplicity_ledger(MANIFEST, [{"hypothesis_id": "h1",
                                           "family": "fam-a", "q": 0.03}])
    assert ei.value.code == "q_without_method_receipt"


def test_multiplicity_rejects_unknown_family():
    with pytest.raises(pa.AggregatorError) as ei:
        pa.multiplicity_ledger(MANIFEST, [{"hypothesis_id": "h9",
                                           "family": "fam-z"}])
    assert ei.value.code == "hypothesis_family_not_in_manifest"


def test_pnl_selection_requires_authority():
    cells = _cells(*([pa.CELL_OBSERVED] * 4))
    m = pa.completion_matrix(MANIFEST, cells)
    with pytest.raises(pa.AggregatorError) as ei:
        pa.program_decision(MANIFEST, m, authority="FEASIBILITY",
                            pnl_ranked=["c1"])
    assert ei.value.code == "pnl_selection_requires_authority"
    ok = pa.program_decision(MANIFEST, m, authority="REVIEW_APPROVED",
                             pnl_ranked=["c1"])
    assert ok["complete"] is True and ok["selected"] == ["c1"]


def test_incomplete_program_decision():
    m = pa.completion_matrix(MANIFEST, _cells(pa.CELL_OBSERVED))
    d = pa.program_decision(MANIFEST, m, authority="FEASIBILITY")
    assert d["complete"] is False
    assert d["next_gate"] == "complete_all_folds"


def test_compare_carries_trade_decomposition_when_both_admitted(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        res = client.get("/bt/compare", params={"job_a": "a1", "job_b": "b2"}).json()
    assert res["eligibility"]["eligible"] is True
    dec = res["trade_decomposition"]
    assert dec["key_basis"] == "symbol|entry_ts"
    assert dec["n_a"] == 1 and dec["n_b"] == 1
    assert dec["n_common"] + dec["n_removed"] == 1


def test_compare_blocked_side_skips_decomposition(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, status="error") as client:
        res = client.get("/bt/compare", params={"job_a": "a1", "job_b": "b2"}).json()
    assert "trade_decomposition" not in res
