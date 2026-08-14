from collections import Counter

from ai_strategy_loop.revision.probabilistic_discovery_d2 import (
    FAMILIES,
    propose_d2_batch,
    render_d2_source,
)


def test_d2_batch_has_exact_budget_per_family():
    batch = propose_d2_batch(seed=20260815, per_family_budget=4)
    assert batch.budget == 16
    assert Counter(item.family for item in batch.candidates) == Counter({
        family: 4 for family in FAMILIES
    })
    assert batch.can_adopt is False
    assert set(batch.qmc_receipts_by_family) == set(FAMILIES)
    assert all(
        receipt.seed == 20260815 + index
        for index, receipt in enumerate(
            batch.qmc_receipts_by_family[family] for family in FAMILIES
        )
    )


def test_d2_batch_is_deterministic_and_all_sources_pass_execution_contract():
    first = propose_d2_batch(seed=20260815, per_family_budget=4)
    second = propose_d2_batch(seed=20260815, per_family_budget=4)
    assert [item.source_sha256 for item in first.candidates] == [
        item.source_sha256 for item in second.candidates
    ]
    assert all(item.execution_ok for item in first.candidates)
    assert all(item.execution_reasons == () for item in first.candidates)
    assert all(item.oos_claim == "none" for item in first.candidates)


def test_d2_families_use_distinct_composite_runtime_functions():
    batch = propose_d2_batch(seed=20260815, per_family_budget=4)
    samples = {family: next(item.source for item in batch.candidates if item.family == family) for family in FAMILIES}
    assert "변동성급증및구간최고가갱신" in samples["VOL_EXPANSION_BREAKOUT"]
    assert "호가상승압력및매수수량급증" in samples["BOOK_PERSISTENCE"]
    assert "거래대금급증및가격급등" in samples["DELAYED_FLOW_RESPONSE"]
    assert "거래대금급증및구간최고가갱신" in samples["SPARSE_CONFIRMED_BREAKOUT"]
    assert len(set(samples.values())) == 4


def test_d2_renderer_rejects_unknown_family():
    try:
        render_d2_source("UNKNOWN", {})
    except ValueError as exc:
        assert "unknown D2 family" in str(exc)
    else:
        raise AssertionError("unknown family must fail")
