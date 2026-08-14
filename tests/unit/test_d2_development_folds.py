from ai_strategy_loop.labeling.run_d2_development_folds import candidate_verdict, fold_success


def _metrics(profit=1.0, krw=1000, mdd=5.0, trades=30, avg=0.1):
    return {
        "trade_count": trades,
        "total_profit_pct": profit,
        "total_profit_krw": krw,
        "avg_profit_pct": avg,
        "mdd_pct": mdd,
    }


def _row(success=True, **metrics):
    values = _metrics(**metrics)
    return {
        "status": "success",
        "metrics": values,
        "fold_success": success,
    }


def test_fold_success_uses_preregistered_boundaries():
    assert fold_success("success", _metrics()) is True
    assert fold_success("error", _metrics()) is False
    assert fold_success("success", _metrics(trades=19)) is False
    assert fold_success("success", _metrics(profit=0)) is False
    assert fold_success("success", _metrics(avg=0)) is False
    assert fold_success("success", _metrics(mdd=15.1)) is False


def test_candidate_verdict_requires_four_of_six_and_positive_aggregate():
    rows = [_row(True) for _ in range(4)] + [_row(False, profit=-1, krw=-500) for _ in range(2)]
    verdict = candidate_verdict(rows)
    assert verdict["successful_folds"] == 4
    assert verdict["robust"] is True
    assert verdict["verdict"] == "DEVELOPMENT_RULE_PASS"
    assert verdict["posterior_underpowered"] is True
    assert verdict["bayesian"]["can_adopt"] is False


def test_candidate_verdict_rejects_negative_aggregate_or_high_mdd():
    negative = [_row(True, krw=100) for _ in range(4)] + [_row(False, profit=-1, krw=-1000) for _ in range(2)]
    assert candidate_verdict(negative)["robust"] is False
    high_mdd = [_row(True) for _ in range(4)] + [_row(False, mdd=16) for _ in range(2)]
    assert candidate_verdict(high_mdd)["robust"] is False
