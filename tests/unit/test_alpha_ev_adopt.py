"""alpha_lab.mining.ev_adopt 단위 테스트 — 봉인 adoption_ev 게이트 (v3 P1).

검증(계약 — preregistration_v3.adoption_ev 봉인 50d3d38a):
- 양성 대조: 심어둔 양EV 포켓 리프가 adopted=True로 회수(ev·ci_low>0,
  fdr_survivor, 전 연도 EV>0) — 널 리프는 탈락.
- 게이트 각인(축별 단독 검증): support_min 미달만으로 탈락, 한 연도 EV<=0
  만으로 탈락(다른 게이트는 전부 통과인 채), 음EV 포켓은 primary에서 탈락.
- FDR 경계: 반환 fdr_survivor가 stats_common.bh_fdr(p, q) 재계산과 정확히
  동치(재구현 금지 검증) + p=0 리프는 임의의 q>0에서 생존(BH 경계 성질).
- 수치 동치: ev/ci/p가 day_block_bootstrap(stat='mean', seed+i) 직접 호출과
  동일 — 리프 i 시드 관례는 evaluate_leaves와 같은 seed+i.
- 원본 불변(새 dict 반환)·필수 키·입력 검증(per_year_masks 필수, 길이,
  rule_cols 없는 리프 거부, 빈 리프 목록 → []).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from alpha_lab.mining.ev_adopt import adopt_by_ev
from alpha_lab.mining.stats import rule_mask
from alpha_lab.stats_common import bh_fdr, day_block_bootstrap

N_DAYS = 40
PER_DAY = 100
POCKET_THR = 0.7  # x0 > 0.7 → 표본의 ~30% (support ≈ 1200 ≥ 봉인 1000)

RESULT_KEYS = {
    "ev", "ci_low", "ci_high", "p", "per_year_ev", "fdr_survivor",
    "adopted", "support_eval",
}


def _pocket_data(
    seed: int = 11,
    pocket_ev_2023: float = 1.0,
    pocket_ev_2024: float = 1.0,
    out_ev: float = -1.0,
):
    """x0 > POCKET_THR 포켓에 연도별 평균 EV를 심은 합성 데이터.

    반환: X(float32 2열), y_net(float64 %), day_ids, per_year_masks.
    앞 절반 일 = 2023, 뒤 절반 일 = 2024.
    """
    rng = np.random.default_rng(seed)
    n = N_DAYS * PER_DAY
    day_ids = np.repeat(np.arange(N_DAYS), PER_DAY)
    year_2023 = day_ids < (N_DAYS // 2)
    x0 = rng.uniform(0.0, 1.0, n)
    X = np.column_stack([x0, rng.uniform(-1.0, 1.0, n)]).astype(np.float32)
    pocket = x0 > POCKET_THR
    noise = 0.05 * rng.standard_normal(n)
    y = np.full(n, out_ev) + noise
    y[pocket & year_2023] = pocket_ev_2023 + noise[pocket & year_2023]
    y[pocket & ~year_2023] = pocket_ev_2024 + noise[pocket & ~year_2023]
    per_year_masks = {2023: year_2023, 2024: ~year_2023}
    return X, y, day_ids, per_year_masks


POCKET_LEAF = {"rule": [("x0", ">", POCKET_THR)], "rule_cols": [0]}
NULL_LEAF = {"rule": [("x1", ">", 0.0)], "rule_cols": [1]}  # EV ≈ 기저(음수)


# --------------------------------------------------------------- 양성 대조


def test_adopt_by_ev_recovers_planted_positive_pocket():
    """양성 대조(봉인 기본 인자): 심은 포켓 채택, 널 리프 탈락."""
    X, y, day_ids, per_year_masks = _pocket_data()
    results = adopt_by_ev(
        [POCKET_LEAF, NULL_LEAF], X, y, day_ids, per_year_masks=per_year_masks
    )
    assert len(results) == 2
    pocket, null = results
    assert RESULT_KEYS <= set(pocket)
    assert pocket["adopted"] is True
    assert pocket["ev"] > 0.5
    assert pocket["ci_low"] > 0.0
    assert pocket["p"] == 0.0
    assert pocket["fdr_survivor"] is True
    assert pocket["support_eval"] >= 1000
    assert set(pocket["per_year_ev"]) == {2023, 2024}
    assert all(v > 0.0 for v in pocket["per_year_ev"].values())
    assert null["adopted"] is False
    assert null["ev"] < 0.0
    # 원본 리프 불변(새 dict 반환).
    assert "ev" not in POCKET_LEAF and "adopted" not in NULL_LEAF


def test_adopt_by_ev_negative_pocket_fails_primary():
    """음EV 포켓: ci_low<=0·p 큼 → adopted=False (primary 게이트)."""
    X, y, day_ids, per_year_masks = _pocket_data(
        pocket_ev_2023=-0.5, pocket_ev_2024=-0.5
    )
    (result,) = adopt_by_ev(
        [POCKET_LEAF], X, y, day_ids, n_boot=400, per_year_masks=per_year_masks
    )
    assert result["ev"] < 0.0
    assert not (result["ci_low"] > 0.0)
    assert result["p"] >= 0.5
    assert result["adopted"] is False


# ------------------------------------------------------------- 게이트 각인


def test_adopt_by_ev_support_min_gate_alone_rejects():
    """support_min만 미달(다른 게이트 전부 통과) → 탈락."""
    X, y, day_ids, per_year_masks = _pocket_data()
    results = adopt_by_ev(
        [POCKET_LEAF], X, y, day_ids, n_boot=400,
        support_min=10 ** 6, per_year_masks=per_year_masks,
    )
    (result,) = results
    assert result["ci_low"] > 0.0 and result["fdr_survivor"] is True
    assert all(v > 0.0 for v in result["per_year_ev"].values())
    assert result["support_eval"] < 10 ** 6
    assert result["adopted"] is False


def test_adopt_by_ev_per_year_gate_alone_rejects():
    """전체 EV CI_low>0인데 2024 EV<=0 → per_year 게이트 단독 탈락."""
    X, y, day_ids, per_year_masks = _pocket_data(
        pocket_ev_2023=2.0, pocket_ev_2024=-0.2
    )
    (result,) = adopt_by_ev(
        [POCKET_LEAF], X, y, day_ids, n_boot=400, per_year_masks=per_year_masks
    )
    assert result["ci_low"] > 0.0 and result["fdr_survivor"] is True
    assert result["support_eval"] >= 1000
    assert result["per_year_ev"][2023] > 0.0
    assert result["per_year_ev"][2024] < 0.0
    assert result["adopted"] is False


def test_adopt_by_ev_empty_year_support_is_nan_and_rejected():
    """포켓 표본이 없는 연도의 per_year_ev는 nan → 보수적 탈락."""
    X, y, day_ids, _ = _pocket_data()
    empty_year = {2023: np.ones(y.shape[0], dtype=bool),
                  2024: np.zeros(y.shape[0], dtype=bool)}
    (result,) = adopt_by_ev(
        [POCKET_LEAF], X, y, day_ids, n_boot=200, per_year_masks=empty_year
    )
    assert math.isnan(result["per_year_ev"][2024])
    assert result["adopted"] is False


# ---------------------------------------------------------------- FDR 경계


def test_adopt_by_ev_fdr_mask_matches_bh_fdr_exactly():
    """fdr_survivor는 반환 p 벡터의 bh_fdr(p, q) 재계산과 정확히 동치."""
    X, y, day_ids, per_year_masks = _pocket_data()
    leaves = [
        POCKET_LEAF,
        NULL_LEAF,
        {"rule": [("x1", "<=", 0.0)], "rule_cols": [1]},
        {"rule": [("x0", "<=", 0.3)], "rule_cols": [0]},
    ]
    for q in (0.05, 0.5):
        results = adopt_by_ev(
            leaves, X, y, day_ids, n_boot=300, fdr_q=q,
            per_year_masks=per_year_masks,
        )
        expected = bh_fdr([r["p"] for r in results], q)
        assert [r["fdr_survivor"] for r in results] == expected.tolist()


def test_adopt_by_ev_fdr_boundary_zero_p_survives_tiny_q():
    """BH 경계 성질: p=0 리프는 q가 아무리 작아도 생존, 널 리프는 전멸."""
    X, y, day_ids, per_year_masks = _pocket_data()
    results = adopt_by_ev(
        [POCKET_LEAF, NULL_LEAF], X, y, day_ids, n_boot=300,
        fdr_q=1e-12, per_year_masks=per_year_masks,
    )
    pocket, null = results
    assert pocket["p"] == 0.0
    assert pocket["fdr_survivor"] is True
    assert null["fdr_survivor"] is False


# ---------------------------------------------------------------- 수치 동치


def test_adopt_by_ev_matches_direct_bootstrap_seed_plus_i():
    """리프 i의 ev/ci/p == day_block_bootstrap(mask_i, seed+i) 직접 호출."""
    X, y, day_ids, per_year_masks = _pocket_data()
    leaves = [POCKET_LEAF, NULL_LEAF]
    results = adopt_by_ev(
        leaves, X, y, day_ids, n_boot=250, seed=777,
        per_year_masks=per_year_masks,
    )
    for i, (leaf, result) in enumerate(zip(leaves, results)):
        mask = rule_mask(X.astype(np.float32), leaf)
        direct = day_block_bootstrap(
            day_ids, y, mask, n_boot=250, seed=777 + i, stat="mean"
        )
        assert result["ev"] == direct["point"]
        assert result["ci_low"] == direct["ci_low"]
        assert result["ci_high"] == direct["ci_high"]
        assert result["p"] == direct["p_one_sided"]
        assert result["support_eval"] == int(mask.sum())
        # per_year_ev 산식: 연도∩리프 표본의 y_net 평균.
        for year, ym in per_year_masks.items():
            sub = mask & np.asarray(ym, dtype=bool)
            assert result["per_year_ev"][year] == pytest.approx(
                float(y[sub].mean())
            )


# ---------------------------------------------------------------- 입력 검증


def test_adopt_by_ev_validations():
    X, y, day_ids, per_year_masks = _pocket_data()
    with pytest.raises(ValueError):
        adopt_by_ev([POCKET_LEAF], X, y, day_ids, per_year_masks={})
    bad_year = {2023: np.ones(3, dtype=bool)}
    with pytest.raises(ValueError):
        adopt_by_ev(
            [POCKET_LEAF], X, y, day_ids, n_boot=10, per_year_masks=bad_year
        )
    with pytest.raises(ValueError):
        adopt_by_ev(
            [{"rule": [("x0", ">", 0.5)]}], X, y, day_ids, n_boot=10,
            per_year_masks=per_year_masks,
        )  # rule_cols 없는 리프 — mine_rules 산출물이 아니다
    with pytest.raises(ValueError):
        adopt_by_ev(
            [POCKET_LEAF], X, y[:-1], day_ids, n_boot=10,
            per_year_masks=per_year_masks,
        )
    assert adopt_by_ev(
        [], X, y, day_ids, n_boot=10, per_year_masks=per_year_masks
    ) == []
