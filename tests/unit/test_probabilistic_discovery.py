from ai_strategy_loop.revision.probabilistic_discovery import (
    FAMILIES,
    propose_discovery_batch,
    render_candidate_source,
)


def test_discovery_batch_is_deterministic_and_budgeted():
    first = propose_discovery_batch(seed=17, budget=12)
    second = propose_discovery_batch(seed=17, budget=12)
    assert len(first.candidates) == 12
    assert [item.source_sha256 for item in first.candidates] == [
        item.source_sha256 for item in second.candidates
    ]
    assert first.can_adopt is False


def test_every_candidate_passes_execution_contract_and_has_no_oos_claim():
    batch = propose_discovery_batch(seed=20260814, budget=12)
    assert all(item.execution_ok for item in batch.candidates)
    assert all(item.execution_reasons == () for item in batch.candidates)
    assert all(item.can_adopt is False for item in batch.candidates)
    assert all(item.oos_claim == "none" for item in batch.candidates)


def test_qmc_batch_covers_all_declared_structure_families():
    batch = propose_discovery_batch(seed=20260814, budget=12)
    assert {item.family for item in batch.candidates} == set(FAMILIES)


def test_rendered_sources_define_vi_guard_before_use():
    batch = propose_discovery_batch(seed=20260814, budget=12)
    for item in batch.candidates:
        assert item.source.index("VI아래5호가 =") < item.source.index(
            "현재가 < VI아래5호가"
        )
        assert item.source.rstrip().endswith("self.Buy()")


def test_family_rendering_is_structurally_distinct():
    common = {
        "cap_max": 2000,
        "time_end": 91000,
        "strength": 120.0,
        "money_multiple": 2.0,
        "pressure_ratio": 1.2,
        "rate_low": 1.0,
        "rate_width": 8.0,
        "mid_rate": 0.5,
        "turnover": 1.0,
    }
    sources = {family: render_candidate_source(family, common) for family in FAMILIES}
    assert "초당거래대금평균(30)" in sources["FLOW_SURGE"]
    assert "매수총잔량 >= 매도총잔량" in sources["BOOK_IMBALANCE"]
    assert "고저평균대비등락율" in sources["MOMENTUM_QUALITY"]
    assert len(set(sources.values())) == 3


def test_unknown_family_is_rejected():
    try:
        render_candidate_source("UNKNOWN", {})
    except ValueError as exc:
        assert "unknown family" in str(exc)
    else:
        raise AssertionError("unknown family must fail")
