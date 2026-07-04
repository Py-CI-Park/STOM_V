"""시드 격자 열거기(T1.1+T1.2) 단위 테스트.

검증:
  - enumerate_cells: 축 곱(2×6×4×3=144)·결정론 순서·cell_id 유일성.
  - tick 셀 시간창이 09:00~09:30 내 5분 버킷 6개인지.
  - min 셀이 로드맵 6밴드(09·10·11·13·14시·14:30+, 12시 없음, entry_end<=144500)인지.
  - 전 셀 × 전 패밀리 생성 코드: compile 통과 + 금지 토큰 부재 + 변수 스코프 통과
    + validate_strategy ok.
  - sha 결정성 (같은 입력 → byte-identical 코드·sha).
  - 파라미터 범위 검증 (범위 밖/미지 키 거부).
  - momentum_breakout high_mult: 사구간(>1.0) 없는 상한 1.0 + 완화 기본값(<1.0).
  - 기각 확정 계열(F03/F04/F10/F18) 미등록.
  - 패밀리 JSON 로드 (load_pattern_families) + 로드 패밀리로 시드 빌드
    + buy 파라미터명의 sell 예약 키 충돌 거부.

실DB/백테 미사용: 순수 함수만 검사한다.
"""

import hashlib
import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.token_check import check_tokens  # noqa: E402
from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: E402
from ai_strategy_loop.seeds import (  # noqa: E402
    CAP_TIERS,
    MIN_BANDS,
    REGIMES,
    TICK_BANDS,
    LatticeConfig,
    build_seed,
    default_pattern_families,
    enumerate_cells,
    load_pattern_families,
)
from cli.strategy import validate_strategy  # noqa: E402


# --------------------------------------------------------------------------
# 셀 열거
# --------------------------------------------------------------------------
def test_enumerate_cells_axis_product():
    """셀 수 = lane 2 × band 6 × cap 4 × regime 3 = 144, cell_id 유일."""
    cells = enumerate_cells()
    assert len(cells) == 2 * 6 * 4 * 3 == 144
    assert len({c.cell_id for c in cells}) == 144
    assert sum(1 for c in cells if c.lane == "tick") == 72
    assert sum(1 for c in cells if c.lane == "min") == 72


def test_enumerate_cells_deterministic_order():
    """같은 config 두 번 열거 → 동일 순서·동일 id 시퀀스."""
    a = [c.cell_id for c in enumerate_cells()]
    b = [c.cell_id for c in enumerate_cells(LatticeConfig())]
    assert a == b


def test_enumerate_cells_rejects_unknown_lane():
    """알 수 없는 lane 은 거부."""
    with pytest.raises(ValueError):
        enumerate_cells(LatticeConfig(lanes=("hour",)))


def test_tick_bands_within_open_window():
    """tick 시간밴드 = 09:00~09:30 내 5분 버킷 6개 (DB 커버리지 실측)."""
    expected = [
        (90000, 90500), (90500, 91000), (91000, 91500),
        (91500, 92000), (92000, 92500), (92500, 93000),
    ]
    assert [(b.start, b.end) for b in TICK_BANDS] == expected
    tick_cells = [c for c in enumerate_cells() if c.lane == "tick"]
    for c in tick_cells:
        assert 90000 <= c.band.start < c.band.end <= 93000
    assert len({(c.band.start, c.band.end) for c in tick_cells}) == 6


def test_min_bands_match_roadmap_six():
    """min 시간밴드 = 로드맵 M1 6밴드 (12시 없음, 마지막 밴드 entry_end<=144500)."""
    expected = [
        (90000, 100000), (100000, 110000), (110000, 120000),
        (130000, 140000), (140000, 143000), (143000, 144500),
    ]
    assert [(b.start, b.end) for b in MIN_BANDS] == expected
    # 12시 점심 밴드 부재: 어떤 밴드도 [120000, 130000) 와 겹치지 않는다.
    for b in MIN_BANDS:
        assert b.end <= 120000 or b.start >= 130000, b
    assert max(b.end for b in MIN_BANDS) <= 144500
    min_cells = [c for c in enumerate_cells() if c.lane == "min"]
    assert len({(c.band.start, c.band.end) for c in min_cells}) == 6


def test_axis_definitions():
    """cap 4단계(무결 경계 연속) / regime 3구간(등락율 도메인 내)."""
    assert [t.name for t in CAP_TIERS] == ["small", "midsmall", "midlarge", "large"]
    assert CAP_TIERS[0].hi == CAP_TIERS[1].lo == 1500.0
    assert CAP_TIERS[1].hi == CAP_TIERS[2].lo == 3000.0
    assert CAP_TIERS[2].hi == CAP_TIERS[3].lo == 10000.0
    assert [r.name for r in REGIMES] == ["low", "mid", "high"]
    for r in REGIMES:
        assert -30.0 < r.lo < r.hi < 30.0


# --------------------------------------------------------------------------
# 전 셀 × 전 패밀리 코드 생성 가드
# --------------------------------------------------------------------------
def test_all_seeds_compile_tokens_scope_validate():
    """144셀 × 4패밀리 전수: compile·금지토큰·변수스코프·validate_strategy 통과."""
    families = default_pattern_families()
    n_built = 0
    for cell in enumerate_cells():
        for fam in families.values():
            rec = build_seed(cell, fam)
            n_built += 1
            for kind, code in (("buy", rec.buy_code), ("sell", rec.sell_code)):
                compile(code, "<seed>", "exec")  # 구문 (build_seed 도 이미 강제)
                ok, reason = check_tokens(code)
                assert ok, f"{rec.cell_id}/{rec.family} {kind}: {reason}"
                ok, offending = check_variable_scope(code, cell.lane, kind=kind)
                assert ok, f"{rec.cell_id}/{rec.family} {kind} 스코프 위반: {offending}"
                assert validate_strategy(code)["status"] == "ok"
            # 엔진 정규형 관용구 확인.
            assert rec.buy_code.startswith("매수 = True")
            assert rec.buy_code.endswith("if 매수:\n    self.Buy()")
            assert rec.sell_code.startswith("매도 = False")
            assert rec.sell_code.endswith("if 매도:\n    self.Sell()")
            # 시간밴드 게이트가 코드에 존재.
            assert f"{cell.band.start} <= 시분초 < {cell.band.end}" in rec.buy_code
    assert n_built == 144 * 4


def test_lane_specific_fragments_used():
    """volume_surge: tick 셀은 초당*, min 셀은 분당* 조각을 쓴다."""
    cells = enumerate_cells()
    tick_cell = next(c for c in cells if c.lane == "tick")
    min_cell = next(c for c in cells if c.lane == "min")
    tick_rec = build_seed(tick_cell, "volume_surge")
    min_rec = build_seed(min_cell, "volume_surge")
    assert "초당거래대금평균" in tick_rec.buy_code and "분당" not in tick_rec.buy_code
    assert "분당거래대금평균" in min_rec.buy_code and "초당" not in min_rec.buy_code


def test_sell_force_exit_per_lane():
    """sell 강제청산: tick=92900(장 09:30 내), min=145900(로드맵 청산 규약)."""
    cells = enumerate_cells()
    tick_rec = build_seed(next(c for c in cells if c.lane == "tick"), "momentum_breakout")
    min_rec = build_seed(next(c for c in cells if c.lane == "min"), "momentum_breakout")
    assert "시분초 >= 92900" in tick_rec.sell_code
    assert "시분초 >= 145900" in min_rec.sell_code


# --------------------------------------------------------------------------
# sha 결정성
# --------------------------------------------------------------------------
def test_sha_determinism_and_correctness():
    """같은 입력 두 번 빌드 → 동일 코드·동일 sha, sha 는 코드 utf-8 sha256."""
    cell = enumerate_cells()[0]
    a = build_seed(cell, "momentum_breakout", params={"high_mult": 0.99})
    b = build_seed(cell, "momentum_breakout", params={"high_mult": 0.99})
    assert (a.buy_code, a.sell_code) == (b.buy_code, b.sell_code)
    assert (a.buy_sha256, a.sell_sha256) == (b.buy_sha256, b.sell_sha256)
    assert a.buy_sha256 == hashlib.sha256(a.buy_code.encode("utf-8")).hexdigest()
    assert a.sell_sha256 == hashlib.sha256(a.sell_code.encode("utf-8")).hexdigest()
    # 파라미터가 다르면 buy 코드·sha 도 달라진다.
    c = build_seed(cell, "momentum_breakout", params={"high_mult": 0.985})
    assert c.buy_sha256 != a.buy_sha256


def test_param_validation():
    """범위 밖/정수 위반/미지 키 파라미터는 거부."""
    cell = enumerate_cells()[0]
    with pytest.raises(ValueError):
        build_seed(cell, "momentum_breakout", params={"high_mult": 2.0})  # 범위 밖
    with pytest.raises(ValueError):
        # 현재가 > 고가 불가 → 1.0 초과는 충족 불가 사구간 (범위에서 제외됨).
        build_seed(cell, "momentum_breakout", params={"high_mult": 1.01})
    with pytest.raises(ValueError):
        build_seed(cell, "volume_surge", params={"avg_win": 30.5})  # 정수 스펙 위반
    with pytest.raises(ValueError):
        build_seed(cell, "momentum_breakout", params={"nope": 1.0})  # 미지 키
    with pytest.raises(ValueError):
        build_seed(cell, "no_such_family")  # 미등록 패밀리


def test_momentum_breakout_high_mult_no_dead_zone():
    """high_mult 상한 <= 1.0 (현재가 > 고가 불가 — 사구간 금지), 기본값은 완화점(<1.0)."""
    fam = default_pattern_families()["momentum_breakout"]
    spec = next(s for s in fam.params if s.name == "high_mult")
    assert spec.hi <= 1.0  # 고가는 당일 고가(현재 tick 포함) — 1.0 초과는 충족 불가
    assert spec.lo <= spec.default < spec.hi  # 완화 규약: 기본값 != 최엄격점(상한)


def test_excluded_families_not_registered():
    """기각 확정 계열(F03 눌림회복/F04 매도흡수/F10 대형주추세/F18 재진입) 미등록."""
    names = set(default_pattern_families())
    assert names == {"momentum_breakout", "volume_surge", "strength_surge", "prevday_active"}
    for banned in ("눌림", "흡수", "재진입", "pullback", "absorption", "reentry", "retest"):
        assert not any(banned in n for n in names)


# --------------------------------------------------------------------------
# 패밀리 JSON 로드
# --------------------------------------------------------------------------
def _write_family_json(tmp_path, families):
    p = tmp_path / "families.json"
    p.write_text(
        json.dumps({"schema": "seed_lattice_pattern_families_v1", "families": families},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return p


def test_load_pattern_families_and_build(tmp_path):
    """JSON 패밀리 로드 → 불변 병합 → 로드 패밀리로 시드 빌드까지 통과."""
    p = _write_family_json(tmp_path, [
        {
            "name": "json_strength_relax",
            "description": "외부 공급 예시 (chart_sulsa 공급 형식)",
            "lanes": ["tick", "min"],
            "buy_fragments": {"common": ["체결강도 >= {s_min}"]},
            "params": [{"name": "s_min", "default": 105.0, "min": 100.0, "max": 200.0}],
            "sell_overrides": {"take_profit": 4.0},
        },
    ])
    loaded = load_pattern_families(p)
    assert set(loaded) == {"json_strength_relax"}
    fam = loaded["json_strength_relax"]
    assert fam.source == str(p)
    assert fam.params[0].default == 105.0

    merged = {**default_pattern_families(), **loaded}
    assert len(merged) == 5

    cell = enumerate_cells()[0]
    rec = build_seed(cell, "json_strength_relax", families=merged)
    assert "체결강도 >= 105.0" in rec.buy_code
    assert "수익률 >= 4.0" in rec.sell_code  # sell_overrides 반영
    ok, _ = check_tokens(rec.buy_code)
    assert ok
    ok, offending = check_variable_scope(rec.buy_code, cell.lane, kind="buy")
    assert ok, offending


def test_load_pattern_families_rejects_bad_schema(tmp_path):
    """이름 누락/미지 lane/기본값 범위 밖 JSON 은 거부."""
    with pytest.raises(ValueError):
        load_pattern_families(_write_family_json(tmp_path, [
            {"lanes": ["tick"], "buy_fragments": {"common": ["체결강도 >= 100"]}},
        ]))
    with pytest.raises(ValueError):
        load_pattern_families(_write_family_json(tmp_path, [
            {"name": "x", "lanes": ["hour"], "buy_fragments": {"common": ["체결강도 >= 100"]}},
        ]))
    with pytest.raises(ValueError):
        load_pattern_families(_write_family_json(tmp_path, [
            {"name": "x", "lanes": ["tick"], "buy_fragments": {"common": ["체결강도 >= {s}"]},
             "params": [{"name": "s", "default": 999.0, "min": 0.0, "max": 10.0}]},
        ]))


def test_load_pattern_families_rejects_sell_key_param(tmp_path):
    """buy 파라미터 이름이 sell 예약 키(take_profit 등)와 충돌하면 로드 시점 거부."""
    with pytest.raises(ValueError):
        load_pattern_families(_write_family_json(tmp_path, [
            {"name": "x", "lanes": ["tick"],
             "buy_fragments": {"common": ["수익률근사 >= {take_profit}"]},
             "params": [{"name": "take_profit", "default": 1.0,
                         "min": 0.5, "max": 2.0}]},
        ]))


def test_loaded_family_forbidden_fragment_blocked(tmp_path):
    """외부 조각에 금지 토큰이 있으면 build_seed 가 시드를 내지 않는다."""
    p = _write_family_json(tmp_path, [
        {"name": "evil", "lanes": ["tick"],
         "buy_fragments": {"common": ["eval('1') > 0"]}, "params": []},
    ])
    loaded = load_pattern_families(p)  # 로더는 형식만 본다
    cell = next(c for c in enumerate_cells() if c.lane == "tick")
    with pytest.raises(ValueError):
        build_seed(cell, "evil", families=loaded)
