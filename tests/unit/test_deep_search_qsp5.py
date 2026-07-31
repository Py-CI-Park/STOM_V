# -*- coding: utf-8 -*-
"""QSP5 — 다중 폴드 검증(folds) + 깊이 탐색 엔진(deep_search) 테스트."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_strategy_loop.autopsy import folds
from ai_strategy_loop.revision import deep_search
from ai_strategy_loop.revision.hier_ast import parse_leaves

SEED = Path("docs/research/quant_scoring_pipeline/seed_drafts/QSP2_T_ANCH_900_920_B.py")
CODE = SEED.read_text(encoding="utf-8")
LEAF = ("시분초<90200", "시가총액<3000")


def _rows(year, n, pnl, tovr, gang=100.0, day="0407"):
    return [{
        "종목명": "X", "시가총액": 1000, "매수시간": f"{year}{day}09{i % 2:02d}05",
        "수익률": 1.0 if pnl > 0 else -1.0, "수익금": pnl,
        "B_현재가": 10000, "B_등락율": 5.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
        "B_당일거래대금": 100, "B_시가총액": 1000, "B_체결강도": gang + i * 1e-3,
        "B_전일동시간비": 1.0, "B_회전율": tovr + i * 1e-3,
    } for i in range(n)]


# ---------------------------------------------------------------- folds
def test_fold_report_requires_repeat_not_significance():
    """모든 해에서 흑자면 통과 — 표본이 작아도 '반복 재현'이 증거."""
    df = pd.DataFrame(_rows(2022, 30, +1000, 5.0) + _rows(2023, 30, +900, 5.0)
                      + _rows(2024, 30, +800, 5.0))
    rep = folds.fold_report(df)
    assert rep["passed"], rep
    assert rep["n_eff"] == 3 and rep["pos"] == 3


def test_fold_report_rejects_single_year_carry():
    """한 해만 크게 벌고 나머지가 적자면 기각 — 특정 국면 산물."""
    df = pd.DataFrame(_rows(2022, 30, +5000, 5.0) + _rows(2023, 30, -400, 5.0)
                      + _rows(2024, 30, -400, 5.0))
    rep = folds.fold_report(df)
    assert not rep["passed"] and "흑자 폴드 비율" in rep["reason"]


def test_fold_report_needs_two_effective_folds():
    df = pd.DataFrame(_rows(2022, 30, +1000, 5.0))
    rep = folds.fold_report(df)
    assert not rep["passed"] and "유효 폴드 부족" in rep["reason"]


# ---------------------------------------------------------- deep_search
def test_deep_apply_and_verify_multi_clause():
    spec = {"action": "add_filter_deep", "leaf": list(LEAF), "leaf_label": "B1×S",
            "clauses": [
                {"kind": "side", "feature": "B_회전율", "var": "회전율", "op": ">", "t": 3.2},
                {"kind": "band", "feature": "B_체결강도", "var": "체결강도", "lo": 80.0, "hi": 140.0},
            ]}
    new_code, reason = deep_search.apply_deep(spec, CODE)
    assert new_code, reason
    ok, why = deep_search.verify_deep(spec, CODE, new_code)
    assert ok, why
    h = parse_leaves(new_code)
    idents = [c.ident for c in h.leaves[LEAF]]
    assert idents[-2] == "회전율>?" and idents[-1] == "?<체결강도<=?", idents


def test_deep_verify_rejects_out_of_scope_edit():
    spec = {"leaf": list(LEAF), "clauses": [
        {"kind": "side", "feature": "B_회전율", "var": "회전율", "op": ">", "t": 3.2}]}
    new_code, _ = deep_search.apply_deep(spec, CODE)
    tampered = new_code.replace("당일거래대금 > 300", "당일거래대금 > 500", 1)
    assert tampered != new_code
    ok, why = deep_search.verify_deep(spec, CODE, tampered)
    assert not ok, why


def test_deep_search_requires_holdout_payment(tmp_path):
    """깊이당 지불 — 설계만 좋아지는 확장은 채택되지 않는다."""
    # 설계: 회전율 높은 구간이 흑자. 홀드아웃: 같은 구간이 적자(설계 전용 신호).
    design = _rows(2022, 40, +5000, 9.0) + _rows(2023, 40, +5000, 9.0) \
        + _rows(2022, 60, -3000, 1.0, day="0408") + _rows(2023, 60, -3000, 1.0, day="0408")
    hold = _rows(2025, 40, -4000, 9.0) + _rows(2025, 60, -3000, 1.0, day="0408")
    d = tmp_path / "d.csv"; h = tmp_path / "h.csv"
    pd.DataFrame(design).to_csv(d, index=False, encoding="utf-8-sig")
    pd.DataFrame(hold).to_csv(h, index=False, encoding="utf-8-sig")
    specs = deep_search.propose_deep(str(d), str(h), CODE, top_k=3, timeframe="tick")
    assert specs == [], "표본외가 나빠지는 확장은 제안되면 안 된다"


def test_deep_search_accepts_both_window_pocket(tmp_path):
    """설계·표본외 모두 좋아지고 폴드도 반복되면 채택."""
    # 리프 전체는 적자여야 탐색 대상이 된다(승 80×6천 < 패 120×5천).
    design = (_rows(2022, 40, +6000, 9.0) + _rows(2023, 40, +6000, 9.0)
              + _rows(2022, 60, -5000, 1.0, day="0408") + _rows(2023, 60, -5000, 1.0, day="0408"))
    hold = _rows(2025, 70, +5000, 9.0) + _rows(2025, 90, -5000, 1.0, day="0408")
    d = tmp_path / "d.csv"; h = tmp_path / "h.csv"
    pd.DataFrame(design).to_csv(d, index=False, encoding="utf-8-sig")
    pd.DataFrame(hold).to_csv(h, index=False, encoding="utf-8-sig")
    specs = deep_search.propose_deep(str(d), str(h), CODE, top_k=3, timeframe="tick")
    assert specs, "양쪽 창 흑자 주머니는 제안돼야 한다"
    sp = specs[0]
    assert sp["action"] == "add_filter_deep" and sp["depth"] >= 1
    ev = sp["evidence"]
    assert ev["kept_per_trade_design"] > 0 and ev["kept_per_trade_holdout"] > 0
    new_code, reason = deep_search.apply_deep(sp, CODE)
    assert new_code, reason
    ok, why = deep_search.verify_deep(sp, CODE, new_code)
    assert ok, why
