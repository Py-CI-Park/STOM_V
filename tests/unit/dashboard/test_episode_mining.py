"""ANA-06 — episode/cohort mining foundation 시험."""

from __future__ import annotations

import random

import pytest

from ai_strategy_loop.dashboard import episode_mining as em


def _t(key: str, symbol: str, entry: int, exit_: int | None = None,
       pnl: float = 0.0, candidate: str = "cand-a") -> em.TradeFact:
    return em.TradeFact(
        trade_key=key, source_sha256="s" * 8, symbol=symbol,
        entry_ts=entry, exit_ts=exit_ if exit_ is not None else entry + 600,
        pnl_krw=pnl, candidate=candidate,
    )


BASE = 20250407090000  # YYYYMMDDhhmmss


def test_episode_groups_repeated_triggers():
    trades = [
        _t("k1", "AAA", BASE),
        _t("k2", "AAA", BASE + 120),          # 2분 뒤 — 같은 episode
        _t("k3", "AAA", BASE + 200_000),      # 하루+ 이상 — reset 후 새 episode
        _t("k4", "BBB", BASE + 60),
    ]
    eps = em.build_episodes(trades, reset_gap_seconds=86_400)
    assert len(eps) == 3
    aaa_eps = [e for e in eps if e.symbol == "AAA"]
    assert [e.trigger_count for e in sorted(aaa_eps, key=lambda e: e.onset_ts)] == [2, 1]
    # 선택된 trade key 는 onset(첫 발화).
    assert sorted(aaa_eps, key=lambda e: e.onset_ts)[0].selected_trade_key == "k1"


def test_episode_deterministic_under_shuffle():
    trades = [
        _t("k1", "AAA", BASE), _t("k2", "AAA", BASE + 120),
        _t("k3", "BBB", BASE + 60), _t("k4", "AAA", BASE + 300_000),
        _t("k5", "CCC", BASE), _t("k6", "BBB", BASE + 500_000),
    ]
    ref = em.build_episodes(trades)
    for seed in range(5):
        shuffled = list(trades)
        random.Random(seed).shuffle(shuffled)
        assert em.build_episodes(shuffled) == ref


def test_no_duplicate_onset_same_candidate_symbol():
    trades = [_t("k1", "AAA", BASE), _t("k2", "AAA", BASE + 10)]
    eps = em.build_episodes(trades)
    onsets = {(e.candidate, e.symbol, e.onset_ts) for e in eps}
    assert len(onsets) == len(eps) == 1


def test_typed_failures():
    with pytest.raises(em.EpisodeMiningError) as ei:
        em.build_episodes([_t("k1", "", BASE)])
    assert ei.value.code == "missing_symbol"
    with pytest.raises(em.EpisodeMiningError) as ei:
        em.build_episodes([_t("k1", "AAA", BASE, exit_=BASE - 1)])
    assert ei.value.code == "timestamp_reversal"


def test_stage_f_projection_is_outcome_free():
    eps = em.build_episodes([
        _t("k1", "AAA", BASE, pnl=100.0), _t("k2", "AAA", BASE + 200_000, pnl=-5.0),
    ])
    rows = em.stage_f_projection(eps)
    assert em.projection_is_outcome_free(rows)
    for r in rows:
        assert set(r) <= set(em.STAGE_F_FIELDS)
        assert "pnl" not in r and "pnl_krw" not in r
    # previous_triggered 계보: 같은 candidate 의 두 번째 episode 는 1.
    assert rows[1]["previous_triggered"] == 1


def test_missingness_profile():
    rows = [
        {"a": 1.0, "b": None, "c": 0.0},
        {"a": 2.0, "b": "", "c": 0.0},
    ]
    prof = em.missingness_profile(rows, ["a", "b", "c"])
    assert prof["a"]["coverage"] == 1.0
    assert prof["b"]["missing"] == 2
    assert prof["c"]["zero_only"] is True


def test_cohort_census_concentration():
    eps = em.build_episodes([
        _t("k1", "AAA", BASE), _t("k2", "AAA", BASE + 200_000),
        _t("k3", "BBB", BASE),
    ])
    census = em.cohort_census(eps)
    assert census["n_episodes"] == 3
    assert census["by_symbol"]["AAA"] == 2
    assert 0 < census["max_symbol_share"] <= 1.0


def test_matched_random_control_deterministic():
    eps = em.build_episodes([
        _t(f"k{i}", "AAA", BASE + i * 200_000) for i in range(6)
    ])
    c1 = em.matched_random_control(eps, seed=42, n=3)
    c2 = em.matched_random_control(eps, seed=42, n=3)
    assert c1 == c2
    assert len(c1["episode_ids"]) == 3
    assert c1["receipt"]["seed"] == 42
    # 다른 seed → 다른 선택(극단적 동일 확률은 무시).
    c3 = em.matched_random_control(eps, seed=7, n=3)
    assert c3["episode_ids"] != c1["episode_ids"]


def test_fdr_bh_monotone():
    res = em.fdr_bh([0.001, 0.01, 0.04, 0.2, 0.5])
    qs = [r["q"] for r in res]
    assert qs[0] <= qs[1] <= qs[2] <= qs[3] <= qs[4]
    assert res[0]["rejected"] is True
    assert res[4]["rejected"] is False


def test_finding_roles_separate_discovery_and_confirmation():
    f = em.Finding(finding_id="f1", analysis_hash="h", axis="day",
                   effect=0.5, ci=(0.1, 0.9), q=0.03, role="discovery")
    assert f.role == "discovery" and f.status == "candidate"
