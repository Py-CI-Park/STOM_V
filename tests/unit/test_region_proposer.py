"""G-0b 구간 제거 후보 생성기 계약 테스트.

핵심 규율(핸드오프 §4):
  - 설계·홀드아웃 양쪽 손실 구간만, 고립 1칸 금지, 임계는 분위 격자 위에서만.
  - 누적 유지율 40% 하한 · 1세대 ≤25%p · 이후 ≤12%p.
  - 제거율은 절 share 의 합이 아니라 **합집합 실측**이어야 한다.
  - intent gate: 삽입한 절 외에는 기준선과 diff 0.
"""

from __future__ import annotations

import pytest

from ai_strategy_loop.autopsy import loss_profile as lp
from ai_strategy_loop.revision import region_proposer as rp


BASE_CODE = """매수 = True

if not (관심종목 == 1):
    매수 = False
elif 시분초 < 120000:
    if not (등락율 > 1.0):
        매수 = False
    else:
        self.Buy()
"""


def _samples(rows):
    return [
        lp.Sample(values=values, pnl=pnl, date=20240304)
        for values, pnl in rows
    ]


def _interval(column="B_등락율", variable="등락율", low=None, high=None):
    return rp.Interval(column=column, variable=variable, low=low, high=high)


# --------------------------------------------------------------------------- 표현식

def test_open_low_interval_renders_as_upper_bound():
    assert rp.render_interval(_interval(high=3.5)) == "등락율 <= 3.5"


def test_open_high_interval_renders_as_lower_bound():
    assert rp.render_interval(_interval(low=8.0)) == "등락율 > 8"


def test_closed_interval_renders_as_range():
    assert rp.render_interval(_interval(low=3.5, high=8.0)) == "3.5 < 등락율 <= 8"


def test_large_integer_threshold_is_not_written_in_scientific_notation():
    """`%g` 는 유효숫자 6자리로 잘라 실제 계산값과 다른 임계를 만든다."""
    rendered = rp.render_interval(_interval("B_거래대금증감", "거래대금증감", low=-10933200000.0))
    assert "e" not in rendered
    assert rendered == "거래대금증감 > -10933200000"


def test_multi_band_renders_as_or():
    clause = rp.RegionClause(
        kind="multi_band", card_id="multi_band_00",
        terms=((_interval(high=1.0),), (_interval(low=4.0, high=7.0),)),
        source="테스트", design_share=0.2, holdout_share=0.2,
        design_per_trade=-9000.0, holdout_per_trade=-8000.0,
    )
    assert clause.expression == "(등락율 <= 1) or (4 < 등락율 <= 7)"


def test_pocket_renders_as_and():
    clause = rp.RegionClause(
        kind="pocket_2d", card_id="pocket_00",
        terms=((_interval(low=11.32), _interval("B_체결강도", "체결강도", high=61.86)),),
        source="테스트", design_share=0.01, holdout_share=0.01,
        design_per_trade=-10349.0, holdout_per_trade=-9451.0,
    )
    assert clause.expression == "(등락율 > 11.32) and (체결강도 <= 61.86)"


# --------------------------------------------------------------------------- 코드 삽입

def test_derive_inserts_one_elif_pair_per_clause():
    clauses = (
        rp.RegionClause(kind="single", card_id="c1", terms=((_interval(high=1.0),),),
                        source="s", design_share=0.1, holdout_share=0.1,
                        design_per_trade=-9000.0, holdout_per_trade=-8000.0),
        rp.RegionClause(kind="single", card_id="c2",
                        terms=((_interval("B_체결강도", "체결강도", low=300.0),),),
                        source="s", design_share=0.1, holdout_share=0.1,
                        design_per_trade=-9000.0, holdout_per_trade=-8000.0),
    )
    code = rp.derive_region_code(BASE_CODE, clauses)
    assert code.count(rp.MARKER) == 2
    assert len(code.splitlines()) == len(BASE_CODE.splitlines()) + 4
    rp.validate_region_code(code=code, base_code=BASE_CODE, clauses=clauses)


def test_intent_gate_rejects_body_change():
    clauses = (rp.RegionClause(kind="single", card_id="c1", terms=((_interval(high=1.0),),),
                               source="s", design_share=0.1, holdout_share=0.1,
                               design_per_trade=-9000.0, holdout_per_trade=-8000.0),)
    code = rp.derive_region_code(BASE_CODE, clauses).replace("등락율 > 1.0", "등락율 > 2.0")
    with pytest.raises(rp.RegionValidationError, match="baseline_body_changed"):
        rp.validate_region_code(code=code, base_code=BASE_CODE, clauses=clauses)


def test_intent_gate_rejects_unknown_runtime_variable():
    clause = rp.RegionClause(
        kind="single", card_id="c1",
        terms=((_interval("B_없는변수", "없는변수", high=1.0),),),
        source="s", design_share=0.1, holdout_share=0.1,
        design_per_trade=-9000.0, holdout_per_trade=-8000.0,
    )
    code = rp.derive_region_code(BASE_CODE, (clause,))
    with pytest.raises(rp.RegionValidationError, match="unknown_runtime_variable"):
        rp.validate_region_code(code=code, base_code=BASE_CODE, clauses=(clause,))


def test_missing_anchor_is_reported_not_guessed():
    with pytest.raises(rp.RegionValidationError, match="anchor_not_found"):
        rp.derive_region_code("매수 = True\n", ())


# tick 레인 실제 기준선(ResearchTest_Tick_B_090000_092800_Wide_20260419) 모양 —
# 계층 앵커가 없는 **평탄 elif 체인**이다.
FLAT_BASE_CODE = """매수 = True

if 관심종목 != 1:
    매수 = False
elif not (0 < 현재가 <= 50000):
    매수 = False
elif not (90000 <= 시분초 <= 92800):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False

if 매수:
    self.Buy()
"""


def test_flat_elif_chain_baseline_appends_to_the_chain():
    """tick 기준선에는 `elif 시분초 < 120000:` 앵커가 없다 — 체인 끝에 덧붙인다."""
    clauses = (rp.RegionClause(kind="single", card_id="c1", terms=((_interval(high=1.0),),),
                               source="s", design_share=0.1, holdout_share=0.1,
                               design_per_trade=-9000.0, holdout_per_trade=-8000.0),)
    code = rp.derive_region_code(FLAT_BASE_CODE, clauses)
    lines = code.splitlines()
    marker_index = next(i for i, line in enumerate(lines) if rp.MARKER in line)
    # 마지막 기준선 분기(라운드피겨) 바로 뒤, `if 매수:` 앞이어야 한다.
    assert lines[marker_index - 1].strip() == "매수 = False"
    assert lines[marker_index - 2].strip() == "elif 라운드피겨위5호가이내:"
    assert "if 매수:" in "\n".join(lines[marker_index + 2:])
    assert lines[marker_index].startswith("elif ")   # 같은 체인 = 들여쓰기 0
    rp.validate_region_code(code=code, base_code=FLAT_BASE_CODE, clauses=clauses)


def test_flat_chain_code_still_parses_as_python():
    clauses = (rp.RegionClause(kind="range", card_id="c1",
                               terms=((_interval(low=3.0, high=8.0),),),
                               source="s", design_share=0.1, holdout_share=0.1,
                               design_per_trade=-9000.0, holdout_per_trade=-8000.0),)
    code = rp.derive_region_code(FLAT_BASE_CODE, clauses)
    import ast as _ast
    _ast.parse(code)     # SyntaxError 면 실패


# --------------------------------------------------------------------------- 합집합 유지율

def test_retention_uses_union_not_sum_of_shares():
    """겹치는 두 절의 제거율은 더하면 과대계상된다 — 합집합으로 세야 한다."""
    rows = [({"B_등락율": value, "B_체결강도": value}, -100.0) for value in range(100)]
    samples = _samples(rows)
    overlapping = (
        rp.RegionClause(kind="single", card_id="c1", terms=((_interval(high=30.0),),),
                        source="s", design_share=0.31, holdout_share=0.31,
                        design_per_trade=-1.0, holdout_per_trade=-1.0),
        rp.RegionClause(kind="single", card_id="c2", terms=((_interval(high=20.0),),),
                        source="s", design_share=0.21, holdout_share=0.21,
                        design_per_trade=-1.0, holdout_per_trade=-1.0),
    )
    kept, removed_pnl = rp.apply_clauses(samples, overlapping)
    # 31% + 21% = 52% 가 아니라 합집합 31% 만 사라진다.
    assert len(kept) == 69


def test_apply_clauses_reports_removed_pnl():
    samples = _samples([({"B_등락율": 1.0}, -500.0), ({"B_등락율": 9.0}, 300.0)])
    clause = rp.RegionClause(kind="single", card_id="c1", terms=((_interval(high=2.0),),),
                             source="s", design_share=0.5, holdout_share=0.5,
                             design_per_trade=-500.0, holdout_per_trade=-500.0)
    kept, removed = rp.apply_clauses(samples, (clause,))
    assert len(kept) == 1
    assert removed == -500.0


# --------------------------------------------------------------------------- 예산

@pytest.mark.parametrize(
    ("generation", "retention", "expected"),
    [
        (1, 0.80, "ok"),            # 20%p 소모 — 1세대 한도 25%p 이내
        (1, 0.70, "exceeded"),      # 30%p 소모 — 1세대 한도 초과
        (2, 0.90, "ok"),            # 10%p — 2세대 한도 12%p 이내
        (2, 0.80, "exceeded"),      # 20%p — 2세대 한도 초과
    ],
)
def test_generation_budget_limits(generation, retention, expected):
    assert rp.budget_verdict(
        generation=generation, retention=retention, prior_retention=1.0,
    ) == expected


def test_cumulative_floor_blocks_even_within_generation_limit():
    """세대 한도는 지켜도 누적 40% 하한을 깨면 차단한다."""
    assert rp.budget_verdict(
        generation=3, retention=0.90, prior_retention=0.43,
    ) == "exceeded"


def test_lower_of_design_and_holdout_retention_decides():
    assert rp.budget_verdict(
        generation=1, retention=0.80, prior_retention=1.0, holdout_retention=0.60,
    ) == "exceeded"


# --------------------------------------------------------------------------- 통합 제안

_EDGES = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)


def _profile(
    variable, from_bucket=4, to_bucket=8, *,
    confirmed=True, proposable=True, shape="monotone_down", per_trade=-9000.0,
):
    """제거 구간은 **분위 번호**로 정한다 — 임계는 edges 에서만 나온다(규율 3)."""
    low = _EDGES[from_bucket - 2] if from_bucket >= 2 else None
    high = _EDGES[to_bucket - 1] if to_bucket <= len(_EDGES) else None
    span = lp.WorstSpan(
        from_bucket=from_bucket, to_bucket=to_bucket, low=low, high=high,
        design_n=100, design_pnl=-900000.0, design_per_trade=per_trade,
        holdout_n=50, holdout_pnl=-400000.0, holdout_per_trade=per_trade + 1000.0,
        design_share=0.2, holdout_share=0.2, contiguous=True,
    )
    return lp.VariableProfile(
        variable=variable, shape=shape, confirmed=confirmed, reason="",
        proposable=proposable, spread=2000.0,
        design_overall=-5000.0, holdout_overall=-4800.0, edges=_EDGES,
        design=(), holdout=(), bad_runs=((from_bucket, to_bucket),), worst_span=span,
    )


def test_propose_skips_unconfirmed_and_non_proposable():
    profiles = (
        _profile("B_등락율", confirmed=False),
        _profile("시가총액", proposable=False),
    )
    samples = _samples([({"B_등락율": 5.0, "시가총액": 5.0}, -100.0)] * 200)
    candidates, skipped = rp.propose_regions(
        profiles=profiles, pockets=(), design=samples, holdout=samples,
        base_code=BASE_CODE, generation=1,
    )
    assert candidates == ()
    reasons = {item["reason"] for item in skipped}
    assert "홀드아웃 미확인" in reasons
    assert "조건식 입력 불가(진단 전용)" in reasons


def test_propose_builds_bundles_and_reports_retention():
    profiles = (_profile("B_등락율", 8, 9),)
    # 제거 대상 구간(값 8·9)에 손실이 몰려 있어야 건당 개선이 실제로 생긴다.
    rows = [
        ({"B_등락율": float(value % 10)}, -900.0 if value % 10 >= 8 else -100.0)
        for value in range(1000)
    ]
    samples = _samples(rows)
    candidates, _ = rp.propose_regions(
        profiles=profiles, pockets=(), design=samples, holdout=samples,
        base_code=BASE_CODE, generation=1,
    )
    assert candidates
    best = candidates[0]
    assert best.authority == "advisory"
    assert best.intent_gate == "pass"
    # (7, 9] 제거 → 값 8,9 가 사라진다 → 유지율 0.8 (1세대 예산 25%p 이내)
    assert best.design_retention == pytest.approx(0.8, abs=0.01)
    assert best.budget == "ok"


def test_budget_blocks_clauses_instead_of_emitting_exceeded_bundles():
    """예산을 넘는 절은 후보에 담지 않고 제외 사유로 보고한다."""
    profiles = (_profile("B_등락율", 1, 8),)   # 하위 8분위 제거 = 90% 삭제
    rows = [({"B_등락율": float(value % 10)}, -100.0) for value in range(1000)]
    samples = _samples(rows)
    candidates, skipped = rp.propose_regions(
        profiles=profiles, pockets=(), design=samples, holdout=samples,
        base_code=BASE_CODE, generation=1,
    )
    assert candidates == ()
    assert any("제거 예산 초과" in item["reason"] for item in skipped)


def test_worst_density_clause_is_ranked_first_not_the_biggest_cut():
    """거래 2%짜리 -10,000원 포켓이 거래 40%짜리 -6,000원 절보다 먼저 온다."""
    pocket = lp.Pocket(
        pair=("B_등락율", "B_체결강도"), cells=2, cell_list=((10, 1), (10, 2)),
        x_from=10, x_to=10, y_from=1, y_to=2,
        x_low=8.5, x_high=None, y_low=None, y_high=61.86,
        design_n=20, design_pnl=-200000.0, design_per_trade=-10000.0,
        holdout_n=20, holdout_pnl=-200000.0, holdout_per_trade=-10000.0,
        design_share=0.02, holdout_share=0.02, rect_waste=0.0, max_q=0.02,
    )
    profiles = (_profile("B_회전율"),)
    rows = [
        ({"B_등락율": 9.0, "B_체결강도": 30.0, "B_회전율": 5.0}, -10000.0)
        if value < 20 else
        ({"B_등락율": 2.0, "B_체결강도": 200.0, "B_회전율": float(value % 10)}, -100.0)
        for value in range(1000)
    ]
    samples = _samples(rows)
    candidates, _ = rp.propose_regions(
        profiles=profiles, pockets=(pocket,), design=samples, holdout=samples,
        base_code=BASE_CODE, generation=1,
    )
    assert candidates
    assert candidates[0].clauses[0].kind == "pocket_2d"


def test_propose_caps_clause_count():
    profiles = tuple(
        _profile(name, 8, 9)
        for name in ("B_등락율", "B_체결강도", "B_회전율", "B_전일비", "B_현재가", "B_고가")
    )
    names = ("B_등락율", "B_체결강도", "B_회전율", "B_전일비", "B_현재가", "B_고가")
    rows = [
        ({name: float(value % 10) for name in names},
         -900.0 if value % 10 >= 8 else -100.0)
        for value in range(1000)
    ]
    samples = _samples(rows)
    candidates, _ = rp.propose_regions(
        profiles=profiles, pockets=(), design=samples, holdout=samples,
        base_code=BASE_CODE, generation=1, max_clauses=4,
    )
    assert candidates
    assert all(len(candidate.clauses) <= 4 for candidate in candidates)


def test_pocket_becomes_a_two_variable_clause():
    pocket = lp.Pocket(
        pair=("B_등락율", "B_체결강도"), cells=2, cell_list=((10, 1), (10, 2)),
        x_from=10, x_to=10, y_from=1, y_to=2,
        x_low=11.32, x_high=None, y_low=None, y_high=61.86,
        design_n=500, design_pnl=-5000000.0, design_per_trade=-10349.0,
        holdout_n=120, holdout_pnl=-1100000.0, holdout_per_trade=-9451.0,
        design_share=0.0085, holdout_share=0.009, rect_waste=0.0, max_q=0.023,
    )
    samples = _samples(
        [({"B_등락율": 20.0, "B_체결강도": 30.0}, -10000.0)] * 20
        + [({"B_등락율": 2.0, "B_체결강도": 200.0}, 100.0)] * 980
    )
    candidates, _ = rp.propose_regions(
        profiles=(), pockets=(pocket,), design=samples, holdout=samples,
        base_code=BASE_CODE, generation=1,
    )
    assert candidates
    clause = candidates[0].clauses[0]
    assert clause.kind == "pocket_2d"
    assert clause.expression == "(등락율 > 11.32) and (체결강도 <= 61.86)"
    assert candidates[0].design_retention == pytest.approx(0.98, abs=0.001)
