"""cli/wide_seed_v1.py 계약 테스트 (G004).

DB/네트워크 접근 없이 순수 stdlib(+tmp sqlite fixture)만 사용해:
동결 코드 상수의 컴파일/토큰 통과, LEAF_CELLS 24셀 경계 정합성,
register_seeds의 격리 DB 저장과 `_database` 경로 거부,
export_seed_texts의 한글 명명 파일 생성을 검증한다.
"""

from __future__ import annotations

import sqlite3

import pytest

from cli.wide_seed_v1 import (
    CAP_BANDS,
    LEAF_CELLS,
    MIN_WINDOWS,
    SEED_NAMES,
    TICK_WINDOWS,
    WIDE_MIN_BUY_CODE,
    WIDE_MIN_SELL_CODE,
    WIDE_TICK_BUY_CODE,
    WIDE_TICK_SELL_CODE,
    export_seed_texts,
    register_seeds,
    syntax_check,
)

# ---------------------------------------------------------------------------
# SEED_NAMES
# ---------------------------------------------------------------------------


def test_seed_names_exact():
    assert SEED_NAMES == {
        "tick_buy": "WSEED_V1_Tick_B",
        "tick_sell": "WSEED_V1_Tick_S",
        "min_buy": "WSEED_V1_Min_B",
        "min_sell": "WSEED_V1_Min_S",
    }


# ---------------------------------------------------------------------------
# 코드 상수 -- compile + syntax_check(zero errors)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [WIDE_TICK_BUY_CODE, WIDE_TICK_SELL_CODE, WIDE_MIN_BUY_CODE, WIDE_MIN_SELL_CODE],
)
def test_codes_compile_and_pass_syntax_check(code):
    compile(code, "<seed>", "exec")  # SyntaxError면 즉시 실패
    assert syntax_check(code) == []


def test_syntax_check_reports_syntax_error():
    errors = syntax_check("if True\n    pass\n")
    assert errors
    assert "SyntaxError" in errors[0]


# ---------------------------------------------------------------------------
# 매수 코드 -- 12 leaf, 경계, lane 변수 scope
# ---------------------------------------------------------------------------


def test_tick_buy_has_exactly_12_leaves_and_uses_tick_amount_vars():
    assert WIDE_TICK_BUY_CODE.count("매수 = True") == 12
    assert WIDE_TICK_BUY_CODE.count("초당거래대금평균(20)") == 12
    assert "분당거래대금" not in WIDE_TICK_BUY_CODE
    assert WIDE_TICK_BUY_CODE.startswith("매수 = False\n")
    assert WIDE_TICK_BUY_CODE.rstrip().endswith("self.Buy()")


def test_min_buy_has_exactly_12_leaves_and_uses_min_amount_vars():
    assert WIDE_MIN_BUY_CODE.count("매수 = True") == 12
    assert WIDE_MIN_BUY_CODE.count("분당거래대금평균(20)") == 12
    assert "초당거래대금" not in WIDE_MIN_BUY_CODE
    assert WIDE_MIN_BUY_CODE.startswith("매수 = False\n")
    assert WIDE_MIN_BUY_CODE.rstrip().endswith("self.Buy()")


def test_tick_buy_window_gates_match_frozen_axis():
    for lo, hi in TICK_WINDOWS:
        assert f"{lo} <= 시분초 < {hi}" in WIDE_TICK_BUY_CODE


def test_min_buy_window_gates_match_frozen_axis():
    for lo, hi in MIN_WINDOWS:
        assert f"{lo} <= 시분초 < {hi}" in WIDE_MIN_BUY_CODE


def test_cap_gates_present_in_both_buy_codes():
    expected = [
        "0 < 시가총액 < 3000",
        "3000 <= 시가총액 < 6000",
        "6000 <= 시가총액 < 10000",
        "시가총액 >= 10000",
    ]
    for code in (WIDE_TICK_BUY_CODE, WIDE_MIN_BUY_CODE):
        for cond in expected:
            assert cond in code


# ---------------------------------------------------------------------------
# 매도 코드 -- 동결 exit 값 정확히 일치
# ---------------------------------------------------------------------------


def test_tick_sell_exact_exit_values():
    assert "시분초 >= 93000" in WIDE_TICK_SELL_CODE
    assert "수익률 <= -3.0" in WIDE_TICK_SELL_CODE
    assert "수익률 >= 5.0" in WIDE_TICK_SELL_CODE
    assert "보유시간 >= 300" in WIDE_TICK_SELL_CODE
    assert WIDE_TICK_SELL_CODE.rstrip().endswith("self.Sell()")


def test_min_sell_exact_exit_values():
    assert "시분초 >= 145900" in WIDE_MIN_SELL_CODE
    assert "수익률 <= -4.0" in WIDE_MIN_SELL_CODE
    assert "수익률 >= 6.0" in WIDE_MIN_SELL_CODE
    assert "보유시간 >= 60" in WIDE_MIN_SELL_CODE
    assert WIDE_MIN_SELL_CODE.rstrip().endswith("self.Sell()")


# ---------------------------------------------------------------------------
# LEAF_CELLS -- 24개, lane별 12개, 경계값 정확 일치
# ---------------------------------------------------------------------------


def test_leaf_cells_count_and_keys():
    assert len(LEAF_CELLS) == 24
    expected_keys = {"lane", "window_label", "window_lo", "window_hi", "cap_lo", "cap_hi", "ordinal"}
    for cell in LEAF_CELLS:
        assert set(cell.keys()) == expected_keys


def test_leaf_cells_lane_counts_and_ordinals():
    tick_cells = [c for c in LEAF_CELLS if c["lane"] == "tick"]
    min_cells = [c for c in LEAF_CELLS if c["lane"] == "min"]
    assert len(tick_cells) == 12
    assert len(min_cells) == 12
    assert [c["ordinal"] for c in tick_cells] == list(range(12))
    assert [c["ordinal"] for c in min_cells] == list(range(12))


def test_leaf_cells_windows_match_frozen_axis():
    tick_windows_seen = sorted({(c["window_lo"], c["window_hi"]) for c in LEAF_CELLS if c["lane"] == "tick"})
    min_windows_seen = sorted({(c["window_lo"], c["window_hi"]) for c in LEAF_CELLS if c["lane"] == "min"})
    assert tick_windows_seen == sorted(TICK_WINDOWS)
    assert min_windows_seen == sorted(MIN_WINDOWS)


def test_leaf_cells_cap_bands_match_frozen_axis():
    for lane in ("tick", "min"):
        cap_pairs = [(c["cap_lo"], c["cap_hi"]) for c in LEAF_CELLS if c["lane"] == lane][:4]
        assert cap_pairs == list(CAP_BANDS)


# ---------------------------------------------------------------------------
# register_seeds -- 격리 DB 저장 + `_database` 경로 거부
# ---------------------------------------------------------------------------


def test_register_seeds_writes_4_rows_into_tmp_sqlite(tmp_path):
    db_path = tmp_path / "loop_strategies.db"
    con = sqlite3.connect(str(db_path))
    con.execute('CREATE TABLE IF NOT EXISTS stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.commit()
    con.close()

    result = register_seeds(str(db_path))

    assert set(result.keys()) == {"tick_buy", "tick_sell", "min_buy", "min_sell"}
    for key, row in result.items():
        assert row["status"] == "ok", row
        assert row["action"] == "created"

    con = sqlite3.connect(str(db_path))
    buy_rows = con.execute('SELECT "index" FROM stockbuy ORDER BY "index"').fetchall()
    sell_rows = con.execute('SELECT "index" FROM stocksell ORDER BY "index"').fetchall()
    con.close()

    assert {r[0] for r in buy_rows} == {SEED_NAMES["tick_buy"], SEED_NAMES["min_buy"]}
    assert {r[0] for r in sell_rows} == {SEED_NAMES["tick_sell"], SEED_NAMES["min_sell"]}


def test_register_seeds_rejects_production_database_path(tmp_path):
    bad_path = tmp_path / "_database" / "strategy.db"
    with pytest.raises(ValueError, match="_database"):
        register_seeds(str(bad_path))


def test_register_seeds_rejects_database_path_anywhere_in_string(tmp_path):
    bad_path = tmp_path / "nested" / "_database" / "loop.db"
    with pytest.raises(ValueError):
        register_seeds(str(bad_path))


# ---------------------------------------------------------------------------
# export_seed_texts -- 한글 명명 리뷰용 텍스트 파일 4개
# ---------------------------------------------------------------------------


def test_export_seed_texts_writes_4_files(tmp_path):
    out_dir = tmp_path / "seed_texts"
    written = export_seed_texts(out_dir)

    assert len(written) == 4
    for path in written:
        assert path.exists()
        assert path.parent == out_dir
        assert path.name.startswith("와이드시드V1_")
        assert path.name.endswith(".txt")
        text = path.read_text(encoding="utf-8")
        assert ("매수" in path.name) or ("매도" in path.name)
        assert "self.Buy()" in text or "self.Sell()" in text

    names = {p.name for p in written}
    assert any("tick_매수" in n for n in names)
    assert any("tick_매도" in n for n in names)
    assert any("min_매수" in n for n in names)
    assert any("min_매도" in n for n in names)
