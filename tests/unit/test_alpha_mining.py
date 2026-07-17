"""alpha_lab.mining 단위 테스트 — P1 규칙 채굴 (알파 랩 레인 A 모듈 4).

검증(계약):
- mine_rules(양성 대조 필수): '체결강도' 축 임계 이상 양성률 3배를 심은 합성
  데이터에서 그 축을 분할하는 리프를 회수하고 lift >= 1.5.
- 전체 리프 전수 반환: 서브셋별 support 합 = 표본수(분할), 저lift 리프 포함
  — 리프 수가 곧 n_trials 후보 수(정직 합산).
- min_samples_leaf 준수, 리프 dict 스키마, seed 재현성(같은 입력 → 같은 목록),
  feature_subsets 분할(subset_id·서브셋 밖 피처 금지), 입력 검증.
- evaluate_leaves: {ci_low, ci_high, p, fdr_survivor} 부착(원본 불변·새 dict),
  심은 리프 p 작음 + FDR 생존 + ci_low > 1, 규칙 마스크와 support 일치.
- adopt: lift/support/FDR/전 연도 lift 동시 게이트(연도 마스크 2개 스모크),
  한 연도만 신호인 리프는 per_year_lift_gt에 걸려 탈락, 미평가 리프 거부.

테스트 파라미터는 축소 주입(min_samples_leaf=50, n_boot=200) — 운영 기본값
(2000/1000)은 함수 기본 인자로 봉인되어 있고 여기서는 계약만 검증한다.
"""
from __future__ import annotations

import numpy as np
import pytest

from alpha_lab.mining import adopt, evaluate_leaves, mine_rules

FEATURES = ["등락율", "체결강도", "잔량불균형"]
STRENGTH_COL = 1
THRESHOLD = 150.0
N_DAYS = 40
PER_DAY = 200
LEAF_KEYS = {"rule", "support", "positives", "lift", "subset_id", "leaf_id"}
EVAL_KEYS = {"ci_low", "ci_high", "p", "fdr_survivor"}


def _planted(seed: int = 7, signal_days: int | None = None):
    """'체결강도'>150(표본의 ~25%)에서 양성률 3배(0.30 vs 0.10) 합성 데이터.

    signal_days가 주어지면 앞쪽 그 일수에만 신호를 심는다(연도 게이트 검증용).
    반환: X(float32, 3피처), y(int8 0/1), day_ids(int, 일 블록).
    """
    rng = np.random.default_rng(seed)
    n = N_DAYS * PER_DAY
    day_ids = np.repeat(np.arange(N_DAYS), PER_DAY)
    strength = rng.uniform(0.0, 200.0, n)
    X = np.column_stack(
        [rng.normal(0.0, 1.0, n), strength, rng.uniform(-1.0, 1.0, n)]
    ).astype(np.float32)
    hot = strength > THRESHOLD
    if signal_days is not None:
        hot = hot & (day_ids < signal_days)
    y = (rng.random(n) < np.where(hot, 0.30, 0.10)).astype(np.int8)
    return X, y, day_ids


def _year_masks(day_ids: np.ndarray) -> dict:
    """앞 절반 일 = 2023, 뒤 절반 일 = 2024 표본 마스크."""
    half = N_DAYS // 2
    return {2023: day_ids < half, 2024: day_ids >= half}


def _strength_leaves(leaves):
    """'체결강도' > (100~200) 조건을 포함하는 리프들(심은 신호 회수 후보)."""
    return [
        leaf
        for leaf in leaves
        if any(
            name == "체결강도" and op == ">" and 100.0 < thr < 200.0
            for name, op, thr in leaf["rule"]
        )
    ]


# ------------------------------------------------------------------ mine_rules


def test_mine_rules_recovers_planted_strength_split():
    """양성 대조: 심은 '체결강도' 축 분할 리프를 회수하고 lift >= 1.5."""
    X, y, _ = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=3, min_samples_leaf=50, seed=20260705)
    hits = _strength_leaves(leaves)
    assert hits, "심은 체결강도 축을 분할하는 리프가 없다"
    assert max(leaf["lift"] for leaf in hits) >= 1.5


def test_mine_rules_returns_all_leaves_for_n_trials():
    """전수 반환: support가 표본을 분할(합=n)하고 저lift 리프도 포함된다."""
    X, y, _ = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=3, min_samples_leaf=50, seed=20260705)
    assert len(leaves) >= 2
    assert sum(leaf["support"] for leaf in leaves) == X.shape[0]
    assert sum(leaf["positives"] for leaf in leaves) == int((y == 1).sum())
    assert any(leaf["lift"] < 1.0 for leaf in leaves), "양성 리프만 반환되면 n_trials 과소계상"


def test_mine_rules_respects_min_samples_leaf_and_schema():
    X, y, _ = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=4, min_samples_leaf=50, seed=1)
    seen = set()
    for leaf in leaves:
        assert LEAF_KEYS <= set(leaf)
        assert leaf["support"] >= 50
        assert 0 <= leaf["positives"] <= leaf["support"]
        assert isinstance(leaf["lift"], float)
        for name, op, thr in leaf["rule"]:
            assert name in FEATURES
            assert op in ("<=", ">")
            assert isinstance(thr, float)
        assert len(leaf["rule_cols"]) == len(leaf["rule"])
        key = (leaf["subset_id"], leaf["leaf_id"])
        assert key not in seen, "subset 내 leaf_id 중복"
        seen.add(key)


def test_mine_rules_seed_reproducible():
    X, y, _ = _planted()
    kwargs = dict(max_depth=3, min_samples_leaf=50, seed=20260705)
    assert mine_rules(X, y, FEATURES, **kwargs) == mine_rules(X, y, FEATURES, **kwargs)


def test_mine_rules_feature_subsets_partition_and_ids():
    """서브셋별 트리: subset_id 부여, 서브셋 밖 피처 사용 금지, 각각 표본 분할."""
    X, y, _ = _planted()
    subsets = [[0, 1], [2]]
    leaves = mine_rules(
        X, y, FEATURES, max_depth=2, min_samples_leaf=50, seed=3, feature_subsets=subsets
    )
    assert {leaf["subset_id"] for leaf in leaves} == {0, 1}
    for leaf in leaves:
        allowed = {FEATURES[c] for c in subsets[leaf["subset_id"]]}
        assert {name for name, _, _ in leaf["rule"]} <= allowed
    for sid in (0, 1):
        sub_total = sum(l["support"] for l in leaves if l["subset_id"] == sid)
        assert sub_total == X.shape[0]
    assert _strength_leaves([l for l in leaves if l["subset_id"] == 0])


def test_mine_rules_input_validation():
    X, y, _ = _planted()
    with pytest.raises(ValueError):
        mine_rules(X, y[:-1], FEATURES, min_samples_leaf=50)
    with pytest.raises(ValueError):
        mine_rules(X, y, FEATURES[:2], min_samples_leaf=50)
    with pytest.raises(ValueError):
        mine_rules(X, y, FEATURES, min_samples_leaf=50, feature_subsets=[[]])
    with pytest.raises(ValueError):
        mine_rules(X, y, FEATURES, min_samples_leaf=50, feature_subsets=[[0, 9]])
    with pytest.raises(ValueError):
        mine_rules(X, y, FEATURES, min_samples_leaf=0)


# ------------------------------------------------------------- evaluate_leaves


def test_evaluate_leaves_attaches_stats_without_mutating_input():
    X, y, day_ids = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    before = [dict(leaf) for leaf in leaves]
    evaluated = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    assert leaves == before, "원본 리프가 변형됐다(불변성 위반)"
    assert len(evaluated) == len(leaves)
    for ev, src in zip(evaluated, leaves):
        assert EVAL_KEYS <= set(ev)
        assert {k: ev[k] for k in LEAF_KEYS} == {k: src[k] for k in LEAF_KEYS}
        assert 0.0 <= ev["p"] <= 1.0
        assert ev["ci_low"] <= ev["ci_high"]
        assert isinstance(ev["fdr_survivor"], bool)
        assert len(ev["_idx"]) == ev["support"], "규칙 마스크와 apply() support 불일치"


def test_evaluate_leaves_planted_leaf_significant_and_fdr_survives():
    X, y, day_ids = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    evaluated = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    hits = _strength_leaves(evaluated)
    assert hits
    top = max(hits, key=lambda leaf: leaf["lift"])
    assert top["p"] <= 0.01
    assert top["ci_low"] > 1.0
    assert top["fdr_survivor"] is True


def test_evaluate_leaves_seed_reproducible():
    X, y, day_ids = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    ev1 = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    ev2 = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    for a, b in zip(ev1, ev2):
        assert (a["ci_low"], a["ci_high"], a["p"], a["fdr_survivor"]) == (
            b["ci_low"], b["ci_high"], b["p"], b["fdr_survivor"]
        )


# ----------------------------------------------------------------------- adopt


def test_adopt_smoke_with_two_year_masks():
    """스모크: 심은 리프는 채택, 반대쪽(저lift) 리프는 탈락 — 연도 마스크 2개."""
    X, y, day_ids = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    evaluated = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    adopted = adopt(
        evaluated,
        lift_min=1.5,
        support_min=50,
        per_year_masks=_year_masks(day_ids),
        per_year_lift_gt=1.0,
    )
    assert len(adopted) == 1
    winner = adopted[0]
    assert _strength_leaves([winner])
    assert set(winner["per_year_lift"]) == {2023, 2024}
    assert all(v > 1.0 for v in winner["per_year_lift"].values())


@pytest.mark.parametrize(
    "gate", [dict(lift_min=10.0), dict(support_min=10**9), dict(per_year_lift_gt=5.0)]
)
def test_adopt_each_gate_can_reject_everything(gate):
    X, y, day_ids = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    evaluated = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    kwargs = dict(lift_min=1.5, support_min=50, per_year_lift_gt=1.0)
    kwargs.update(gate)
    assert adopt(evaluated, per_year_masks=_year_masks(day_ids), **kwargs) == []


def test_adopt_requires_all_years_simultaneously():
    """한 연도(앞 절반 일)에만 신호를 심으면 전역 lift는 통과해도 탈락한다."""
    X, y, day_ids = _planted(seed=13, signal_days=N_DAYS // 2)
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    evaluated = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    top = max(_strength_leaves(evaluated), key=lambda leaf: leaf["lift"])
    assert top["lift"] >= 1.5, "전역 lift 게이트는 통과하는 전제가 깨졌다"
    masks = _year_masks(day_ids)
    strict = adopt(
        evaluated, lift_min=1.5, support_min=50, per_year_masks=masks, per_year_lift_gt=1.5
    )
    assert strict == [], "2024년 무신호인데 동시 충족 게이트를 통과했다"
    loose = adopt(
        evaluated, lift_min=1.5, support_min=50, per_year_masks=masks, per_year_lift_gt=0.5
    )
    assert [l["leaf_id"] for l in loose] == [top["leaf_id"]]


def test_adopt_rejects_unevaluated_leaves_and_empty_masks():
    X, y, day_ids = _planted()
    leaves = mine_rules(X, y, FEATURES, max_depth=1, min_samples_leaf=50, seed=5)
    with pytest.raises(ValueError):
        adopt(leaves, per_year_masks=_year_masks(day_ids))
    evaluated = evaluate_leaves(leaves, X, y, day_ids, n_boot=200, seed=11, q=0.05)
    with pytest.raises(ValueError):
        adopt(evaluated, per_year_masks={})
