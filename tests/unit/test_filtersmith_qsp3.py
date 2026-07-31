# -*- coding: utf-8 -*-
"""QSP3 P2 — add_filter 제안·적용·검증 + feature_map 테스트."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_strategy_loop.revision import filtersmith
from ai_strategy_loop.revision.hier_ast import parse_leaves

SEED = Path("docs/research/quant_scoring_pipeline/seed_drafts/QSP2_T_ANCH_900_920_B.py")
CODE = SEED.read_text(encoding="utf-8")
LEAF = ("시분초<90200", "시가총액<3000")
SPEC = {"action": "add_filter", "leaf": list(LEAF), "leaf_label": "B1_900_902×S_3000미만",
        "feature": "B_회전율", "runtime_var": "회전율", "op": ">", "threshold": 3.1,
        "est_delta_design": 1.0, "est_delta_holdout": 1.0}


def test_apply_and_verify_filter_roundtrip():
    new_code, reason = filtersmith.apply_filter(SPEC, CODE)
    assert new_code, reason
    ok, why = filtersmith.verify_filter(SPEC, CODE, new_code)
    assert ok, why
    h = parse_leaves(new_code)
    assert h.leaves[LEAF][-1].ident == "회전율>?"
    # 기존 절 수 +1, 다른 리프 무변화.
    old_h = parse_leaves(CODE)
    assert len(h.leaves[LEAF]) == len(old_h.leaves[LEAF]) + 1
    other = ("시분초<90200", "3000<=시가총액<5000")
    assert [c.ident for c in h.leaves[other]] == [c.ident for c in old_h.leaves[other]]


def test_verify_filter_rejects_out_of_scope_change():
    new_code, _ = filtersmith.apply_filter(SPEC, CODE)
    tampered = new_code.replace("0.5 <= 등락율 <= 22.0", "0.5 <= 등락율 <= 44.0", 1)
    assert tampered != new_code
    ok, why = filtersmith.verify_filter(SPEC, CODE, tampered)
    assert not ok, why  # 라인 diff 가드 또는 리프 대조 어느 쪽이든 거부되면 된다.


def _rows(cap, win, n, tovr, pnl, hhmmss="090105"):
    return [{
        "종목명": f"X{cap}", "시가총액": cap, "매수시간": f"20250407{hhmmss}",
        "수익률": 1.0 if win else -1.0, "수익금": pnl,
        "B_현재가": 10000, "B_등락율": 5.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
        "B_당일거래대금": 100, "B_시가총액": cap, "B_체결강도": 100,
        "B_전일동시간비": 1.0, "B_회전율": tovr + n * 1e-3,
    } for n in range(n)]


def test_propose_filters_finds_separating_variable(tmp_path):
    # B1×소형 리프: 승자 회전율~10, 패자~1 — '회전율 > t' 필터가 양쪽 창 모두 이득.
    design = _rows(1000, True, 40, 10.0, +1000) + _rows(1000, False, 40, 1.0, -2000)
    hold = _rows(1000, True, 40, 10.0, +800) + _rows(1000, False, 40, 1.0, -1800)
    d = tmp_path / "d.csv"; h = tmp_path / "h.csv"
    pd.DataFrame(design).to_csv(d, index=False, encoding="utf-8-sig")
    pd.DataFrame(hold).to_csv(h, index=False, encoding="utf-8-sig")
    specs = filtersmith.propose_filters(str(d), str(h), CODE, top_k=3, timeframe="tick")
    assert specs, "분리 변수를 찾아야 한다"
    sp = specs[0]
    assert sp["action"] == "add_filter" and sp["runtime_var"] == "회전율"
    assert sp["est_delta_design"] > 0 and sp["est_delta_holdout"] > 0
    assert sp["evidence"]["removed_frac"] <= filtersmith.MAX_REMOVED_FRAC
    # 적용→검증 폐루프.
    new_code, reason = filtersmith.apply_filter(sp, CODE)
    assert new_code, reason
    ok, why = filtersmith.verify_filter(sp, CODE, new_code)
    assert ok, why


def test_feature_map_grid_and_loss_regions(tmp_path):
    from ai_strategy_loop.autopsy import feature_map as fm
    design = _rows(1000, True, 40, 10.0, +1000) + _rows(1000, False, 40, 1.0, -2000)
    d = tmp_path / "d.csv"
    pd.DataFrame(design).to_csv(d, index=False, encoding="utf-8-sig")
    g = fm.grid(str(d), "B_회전율", bins=4)
    assert g["cells"] and abs(sum(c["pnl"] for c in g["cells"]) - g["total_pnl"]) < 1e-6
    g2 = fm.grid(str(d), "B_회전율", "B_체결강도", bins=3)
    assert all(c["y_bin"] is not None for c in g2["cells"])
    regions = fm.loss_regions(str(d), bins=4, top=5)
    assert regions and regions[0]["pnl"] < 0
    assert any(r["feature"] == "B_회전율" for r in regions)


def test_gugan_function_variables_are_excluded():
    """감사1호 BUG-Q1 — 구간함수형 이름(런타임에서 함수)은 필터 변수로 금지."""
    for f in ("B_체결강도평균", "B_등락율각도", "B_당일거래대금각도",
              "B_초당거래대금평균", "B_누적초당매수수량", "B_RSI"):
        assert filtersmith._runtime_var(f) is None, f
    assert filtersmith._runtime_var("B_회전율") == "회전율"
    assert filtersmith._runtime_var("B_매수총잔량") == "매수총잔량"


def test_negative_threshold_filter_roundtrip():
    """감사1호 BUG-Q2 — 음수 임계 필터도 apply→verify 폐루프가 성립해야 한다."""
    sp = dict(SPEC, feature="B_거래대금증감", runtime_var="거래대금증감", threshold=-3.5)
    new_code, reason = filtersmith.apply_filter(sp, CODE)
    assert new_code, reason
    ok, why = filtersmith.verify_filter(sp, CODE, new_code)
    assert ok, why


def test_verify_filter_rejects_extra_line_change():
    """감사1호 BUG-Q4 — 삽입 2줄 외의 어떤 라인 변경도 거부(리프 본문·공통 그물)."""
    new_code, _ = filtersmith.apply_filter(SPEC, CODE)
    tampered = new_code.replace("당일거래대금 > 300", "당일거래대금 > 500", 1)  # 공통 그물.
    assert tampered != new_code
    ok, why = filtersmith.verify_filter(SPEC, CODE, tampered)
    assert not ok, "공통 그물 변조가 통과되면 안 된다"


def test_gugan_blocklist_covers_all_captured_function_columns():
    """감사2 A12 — 금지 목록 드리프트 방지: 엔진 정본(gugan_factors)을 AST 로 추출해,
    캡처 컬럼(B_*) 중 구간함수 이름과 겹치는 것 전부가 _GUGAN_FUNCS 에 있어야 한다.
    캡처 컬럼이 추가되면(additive 설계) 이 테스트가 자동으로 드리프트를 잡는다."""
    import ast
    src = open("backtest/back_code_test.py", encoding="utf-8").read()
    tree = ast.parse(src)
    gugan = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if getattr(t, "id", "") == "gugan_factors":
                    gugan = {ast.literal_eval(e) for e in node.value.elts}
    assert gugan, "엔진 정본 gugan_factors 를 찾지 못함"
    from backtest.back_static import TRADE_RESULT_B_COLUMNS
    captured_vars = {c[2:] for c in TRADE_RESULT_B_COLUMNS}
    overlap = captured_vars & gugan
    missing = overlap - filtersmith._GUGAN_FUNCS
    assert not missing, f"금지 목록 누락(BUG-Q1 재발 위험): {missing}"


def test_loss_regions_has_no_nan_bin(tmp_path):
    """감사2 B8 — NaN 값은 'nan' 구간으로 집계되면 안 된다."""
    import math
    from ai_strategy_loop.autopsy import feature_map as fm
    rows = _rows(1000, False, 40, 1.0, -2000)
    for i, r in enumerate(rows):
        if i % 2 == 0:
            r["B_회전율"] = math.nan
    d = tmp_path / "d.csv"
    pd.DataFrame(rows).to_csv(d, index=False, encoding="utf-8-sig")
    regions = fm.loss_regions(str(d), bins=3, top=20)
    assert all(r["bin"].lower() != "nan" for r in regions), regions


def test_rescue_filter_beats_removal_cap(tmp_path):
    """사용자 지적 실증 — 손실 리프 안에 '양쪽 창 흑자' 부분집합이 있으면,
    제거율 상한(60%)에 막히지 않고 구제(rescue) 후보로 살아나야 한다."""
    # 리프 전체는 큰 손실이지만, 회전율 상위 20% 만 남기면 양쪽 창 모두 흑자.
    # 20% 만 우량(회전율 높음) — 나머지를 걸러내면 제거율 80% 로 캡을 넘는다.
    design = _rows(1000, True, 80, 9.0, +40_000) + _rows(1000, False, 320, 1.0, -12_000)
    hold = _rows(1000, True, 80, 9.0, +30_000) + _rows(1000, False, 320, 1.0, -10_000)
    d = tmp_path / "d.csv"; h = tmp_path / "h.csv"
    pd.DataFrame(design).to_csv(d, index=False, encoding="utf-8-sig")
    pd.DataFrame(hold).to_csv(h, index=False, encoding="utf-8-sig")
    specs = filtersmith.propose_filters(str(d), str(h), CODE, top_k=3, timeframe="tick")
    assert specs, "구제 가능한 리프에서 후보가 나와야 한다"
    sp = specs[0]
    assert sp.get("rescue") is True, sp["change"]
    ev = sp["evidence"]
    assert ev["removed_frac"] > filtersmith.MAX_REMOVED_FRAC, "캡을 넘는 선별이어야 의미 있다"
    assert ev["kept_pnl_design"] > 0 and ev["kept_pnl_holdout"] > 0
    assert ev["kept_per_trade_design"] > 0 and ev["kept_per_trade_holdout"] > 0
