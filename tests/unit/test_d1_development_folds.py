from ai_strategy_loop.labeling.run_d1_development_folds import _bayesian, fold_success


def _metrics(**updates):
    values = {
        "trade_count": 30,
        "total_profit_pct": 1.0,
        "avg_profit_pct": 0.1,
        "mdd_pct": 5.0,
    }
    values.update(updates)
    return values


def test_fold_success_requires_all_preregistered_boundaries():
    assert fold_success("success", _metrics()) is True
    assert fold_success("error", _metrics()) is False
    assert fold_success("success", _metrics(trade_count=19)) is False
    assert fold_success("success", _metrics(total_profit_pct=0)) is False
    assert fold_success("success", _metrics(avg_profit_pct=0)) is False
    assert fold_success("success", _metrics(mdd_pct=15.01)) is False


def test_bayesian_fold_receipt_never_grants_adoption():
    result = _bayesian(3, 0)
    assert result["successes"] == 3
    assert result["failures"] == 0
    assert result["decision"] == "CONTINUE"
    assert result["probability_above_rope"] < 0.95
    assert result["can_adopt"] is False
