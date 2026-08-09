# -*- coding: utf-8 -*-
"""S7 계약 테스트 — 챔피언 진입 조건의 절 단위 해부도.

계약:
  1. **등가성** — 절을 전부 AND 한 결과는 원본 마스크(`_mask_902 | _mask_905`)와
     완전히 같다. 다르면 해부도가 다른 전략을 재고 있는 것이다.
  2. 구조 절(시간 창)은 뺄 수 없다 — 빼면 두 분기가 겹친다.
  3. 절을 빼면 진입이 **늘거나 같다**. 줄어들면 AND 사슬을 잘못 푼 것이다.
  4. 절 이름에 분기 접두가 있으므로 한 분기의 절을 빼도 다른 분기는 그대로다.
  5. 참조 열 목록은 소스에서 뽑는다 — 손으로 나열하면 빠진다(실측 전례 있음).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling import champion_clauses as cc
from ai_strategy_loop.labeling.verify_human_strategy import _mask_902, _mask_905

COLUMNS = (
    "시분초", "현재가", "등락율", "고저평균대비등락율", "라운드피겨위5호가이내",
    "시가총액", "시가등락율", "시가대비등락율", "초당순매수금액", "일중위치",
    "전일비", "전일동시간비", "회전율", "당일거래대금", "초당거래대금배율_30",
    "매수흐름_매도잔량비", "잔량비", "체결강도", "초당거래대금직전비",
)


@pytest.fixture(scope="module")
def universe():
    """무작위 우주 — 임계 주변에 넓게 퍼뜨려 모든 절이 실제로 물리게 한다."""
    rng = np.random.default_rng(20260809)
    n = 40_000
    return pd.DataFrame({
        "시분초": rng.integers(90000, 90600, n),
        "현재가": rng.integers(500, 60000, n).astype(float),
        "등락율": rng.uniform(-3, 20, n),
        "고저평균대비등락율": rng.uniform(-2, 2, n),
        "라운드피겨위5호가이내": rng.integers(0, 2, n),
        "시가총액": rng.uniform(200, 6000, n),
        "시가등락율": rng.uniform(-2, 10, n),
        "시가대비등락율": rng.uniform(-2, 10, n),
        "초당순매수금액": rng.uniform(-50, 1500, n),
        "일중위치": rng.uniform(0, 1, n),
        "전일비": rng.uniform(-1, 20, n),
        "전일동시간비": rng.uniform(-1, 20, n),
        "회전율": rng.uniform(0, 8, n),
        "당일거래대금": rng.uniform(50, 20000, n),
        "초당거래대금배율_30": rng.uniform(0, 8, n),
        "매수흐름_매도잔량비": rng.uniform(0, 1.5, n),
        "잔량비": rng.uniform(0, 3, n),
        "체결강도": rng.uniform(0, 400, n),
        "초당거래대금직전비": rng.uniform(0, 4, n),
    })


# ---------------------------------------------------------------------------
# 등가성 — 가장 중요한 계약
# ---------------------------------------------------------------------------

def test_clause_decomposition_equals_the_original_mask(universe):
    """★ 해부도가 원본과 다르면 그 뒤의 모든 측정이 다른 전략의 것이다."""
    original = (_mask_902(universe) | _mask_905(universe)).to_numpy()
    decomposed = cc.champion_mask(universe).to_numpy()
    assert np.array_equal(original, decomposed)
    assert original.sum() > 0, "우주가 아무것도 안 걸린다 — 테스트가 무의미하다"


@pytest.mark.parametrize("branch,original", [("902", _mask_902), ("905", _mask_905)])
def test_each_branch_matches_its_original(universe, branch, original):
    assert np.array_equal(cc.branch_mask(universe, branch).to_numpy(),
                          original(universe).to_numpy())


# ---------------------------------------------------------------------------
# 제거 의미
# ---------------------------------------------------------------------------

def test_structural_clauses_cannot_be_dropped(universe):
    """★ 시간 창을 빼면 두 분기가 겹쳐 챔피언이 아닌 것을 재게 된다."""
    for key in ("902_창", "905_창"):
        with pytest.raises(ValueError, match="구조 절"):
            cc.champion_mask(universe, drop=key)


def test_unknown_clause_is_refused(universe):
    with pytest.raises(KeyError):
        cc.champion_mask(universe, drop="없는절")


@pytest.mark.parametrize("key", cc.DROPPABLE)
def test_dropping_a_clause_never_reduces_entries(universe, key):
    """★ AND 사슬에서 하나를 빼면 진입은 늘거나 같다. 줄면 분해가 틀린 것이다."""
    base = int(cc.champion_mask(universe).sum())
    loosened = int(cc.champion_mask(universe, drop=key).sum())
    assert loosened >= base, f"{key}: {loosened} < {base}"


@pytest.mark.parametrize("key", cc.DROPPABLE)
def test_every_droppable_clause_actually_filters_something(universe, key):
    """모든 절이 이 우주에서 실제로 무언가를 막는다 — 죽은 절이 없는지 확인.

    전체 접합(AND 34개)에 대한 **한계 효과**로 재지 않는다: 나머지 33개가 이미
    거의 전부를 막아서, 절 하나를 빼도 진입이 그대로인 것이 정상이다. 그것은
    절이 죽었다는 뜻이 아니라 접합이 빡빡하다는 뜻이다(실측 진입 0.433건/일).
    여기서 재는 것은 "이 절 자체가 어떤 행을 거부하는가"다.
    """
    rejected = int((~cc.clause_by_key(key).predicate(universe)).sum())
    assert rejected > 0, f"{key} 가 이 우주에서 아무 행도 거부하지 않는다"


def test_dropping_one_branch_clause_leaves_the_other_untouched(universe):
    """분기 접두 덕분에 902 절을 빼도 905 분기는 그대로다."""
    before = cc.branch_mask(universe, "905").to_numpy()
    cc.champion_mask(universe, drop="902_회전율")
    assert np.array_equal(cc.branch_mask(universe, "905", drop="902_회전율").to_numpy(),
                          before)


# ---------------------------------------------------------------------------
# 해부도 자체
# ---------------------------------------------------------------------------

def test_required_columns_are_extracted_from_source():
    """손으로 나열하면 빠진다 — 실측 전례가 있다(고저평균대비등락율 누락)."""
    assert cc.required_columns() == set(COLUMNS)


def test_both_branches_are_fully_described():
    rows = cc.summary()
    assert len(rows) == cc.clause_count() == 34
    assert sum(1 for r in rows if not r["droppable"]) == 2      # 시간 창 둘
    assert len(cc.DROPPABLE) == 32
    assert all(r["label"] for r in rows)                        # 사람 말이 비면 화면이 빈다


def test_clause_keys_are_unique():
    keys = [r["key"] for r in cc.summary()]
    assert len(keys) == len(set(keys))
