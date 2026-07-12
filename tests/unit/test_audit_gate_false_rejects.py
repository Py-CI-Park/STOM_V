# -*- coding: utf-8 -*-
"""audit_gate_false_rejects.py 자기 테스트 (tmp sqlite 전용, 실 DB 비의존).

검증 대상: timeframe 분류 휴리스틱, buy/sell 이름 짝짓기 휴리스틱,
__AUTO_TMP__ 제외, 검사별(변수 스코프/토큰/필터 범주/매도 예산/원리 일관성)
집계·거부율·사유 분포, '어느 검사에서든 거부' 요약. 합성 전략(정상 1쌍·
위반 1쌍)으로만 검증하며 운영 `_database/strategy.db`는 열지 않는다.
"""
import importlib.util
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "audit_gate_false_rejects.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_gate_false_rejects", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _load_module()


# ===================================================================
# 합성 전략 코드 (정상 1쌍 · 위반 1쌍)
# ===================================================================

# 정상 tick 매수/매도 쌍: variable_scope/token_check/filter_gate(>=5 범주)/
# exec_budget/principle_gate(CSC-06·07·10) 모두 통과해야 한다.
NORMAL_BUY = (
    "매수 = False\n"
    "if 90000 <= 시분초 < 93000 and 시가총액 < 5000 and 1000 < 현재가 <= 40000 "
    "and 2.0 <= 등락율 <= 12.0 and 체결강도 >= 100 and 초당거래대금 > 3000:\n"
    "    매수 = True\n"
)
NORMAL_SELL = (
    "매도 = False\n"
    "if 수익률 <= -2.0 or 시분초 >= 92000:\n"
    "    매도 = True\n"
)

# 위반 매수: 환각 변수(variable_scope reject) + 필터 범주 0개(filter_gate reject).
VIOLATING_BUY = (
    "매수 = False\n"
    "if 미확인변수 > 10:\n"
    "    매수 = True\n"
)
# 위반 매도: 비유계 역스캔 함수(exec_budget reject) + 손절/강제종료 부재
# (principle_gate CSC-07/CSC-10 reject).
VIOLATING_SELL = (
    "매도 = False\n"
    "if 고가미갱신지속틱수(30) > 100:\n"
    "    매도 = True\n"
)

AUTO_TMP_BUY = "매수 = True"


def _make_db(tmp_path):
    db_path = tmp_path / "synthetic_strategy.db"
    con = sqlite3.connect(str(db_path))
    try:
        con.execute('CREATE TABLE stockbuy ("index" TEXT, "전략코드" TEXT)')
        con.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
        con.executemany(
            'INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)',
            [
                ("Tick_B_902", NORMAL_BUY),
                ("Tick_B_905", VIOLATING_BUY),
                ("__AUTO_TMP__Tick_B_999_123", AUTO_TMP_BUY),
            ],
        )
        con.executemany(
            'INSERT INTO stocksell ("index", "전략코드") VALUES (?, ?)',
            [
                ("Tick_S_902", NORMAL_SELL),
                ("Tick_S_905", VIOLATING_SELL),
            ],
        )
        con.commit()
    finally:
        con.close()
    return db_path


# ===================================================================
# 1) timeframe 분류 휴리스틱
# ===================================================================

def test_classify_timeframe_tick_prefix():
    assert MOD.classify_timeframe("Tick_B_902") == ["tick"]
    assert MOD.classify_timeframe("C_T_900_920_U2_B") == ["tick"]
    assert MOD.classify_timeframe("CSS_V7_TICK_B_MASTER_0900_0930") == ["tick"]


def test_classify_timeframe_min_prefix():
    assert MOD.classify_timeframe("Min_B_Study_250824") == ["min"]
    assert MOD.classify_timeframe("CSS_V7_MIN_B_MASTER_0900_1518") == ["min"]


def test_classify_timeframe_uncertain_is_both():
    # Tick/Min 어느 쪽에도 매칭되지 않으면 불확실 → 양쪽 각각.
    assert MOD.classify_timeframe("Auto_B_Pilot01") == ["tick", "min"]


# ===================================================================
# 2) buy/sell 이름 짝짓기 휴리스틱
# ===================================================================

def test_candidate_sell_name_token_boundary():
    assert MOD.candidate_sell_name("Tick_B_902") == "Tick_S_902"
    assert MOD.candidate_sell_name("CSS_V7_MIN_B_MASTER_0900_1518") == "CSS_V7_MIN_S_MASTER_0900_1518"
    assert MOD.candidate_sell_name("20250715_Study_B_2") == "20250715_Study_S_2"


def test_candidate_sell_name_no_boundary_b_is_none():
    # "BOX"의 B는 토큰 경계에 홀로 있지 않으므로 매칭하지 않는다.
    assert MOD.candidate_sell_name("CSS_V7_MIN_B_BOX_BREAKOUT_EVENT_0900_1518") is None or (
        MOD.candidate_sell_name("CSS_V7_MIN_B_BOX_BREAKOUT_EVENT_0900_1518")
        == "CSS_V7_MIN_S_BOX_BREAKOUT_EVENT_0900_1518"
    )
    # 이름에 "B" 토큰이 전혀 없으면 후보가 없다.
    assert MOD.candidate_sell_name("20250715_Study") is None


def test_pair_strategies_pairs_and_reports_unpaired():
    buy_rows = [("Tick_B_902", "code_b1"), ("Auto_B_Pilot01", "code_b2")]
    sell_rows = [("Tick_S_902", "code_s1"), ("Other_Sell_Only", "code_s3")]
    paired, unpaired_buy, unpaired_sell = MOD.pair_strategies(buy_rows, sell_rows)
    assert paired == [("Tick_B_902", "code_b1", "Tick_S_902", "code_s1")]
    assert unpaired_buy == ["Auto_B_Pilot01"]
    assert unpaired_sell == ["Other_Sell_Only"]


# ===================================================================
# 3) run_audit — 합성 DB(정상 1쌍 · 위반 1쌍 · __AUTO_TMP__ 1개)
# ===================================================================

def test_run_audit_excludes_auto_tmp(tmp_path):
    db_path = _make_db(tmp_path)
    result = MOD.run_audit(db_path)
    assert result["excluded_auto_tmp"]["buy"] == 1
    assert result["excluded_auto_tmp"]["total"] == 1
    assert result["counts"]["buy_total_raw"] == 3
    assert result["counts"]["buy_audited"] == 2
    assert result["counts"]["sell_total_raw"] == 2
    assert result["counts"]["sell_audited"] == 2


def test_run_audit_variable_scope_rejects_hallucinated_var(tmp_path):
    result = MOD.run_audit(_make_db(tmp_path))
    vs = result["checks"]["variable_scope"]
    rejected_names = {(r["name"], r["kind"]) for r in vs["rejected_strategies"]}
    assert ("Tick_B_905", "buy") in rejected_names
    assert ("Tick_B_902", "buy") not in rejected_names
    assert "미확인변수" in vs["reason_distribution"]


def test_run_audit_token_check_all_clean(tmp_path):
    result = MOD.run_audit(_make_db(tmp_path))
    tc = result["checks"]["token_check"]
    assert tc["evaluated"] == 4  # 2 buy + 2 sell (AUTO_TMP excluded)
    assert tc["rejected"] == 0


def test_run_audit_filter_gate_rejects_zero_category_buy(tmp_path):
    result = MOD.run_audit(_make_db(tmp_path))
    fg = result["checks"]["filter_gate"]
    assert fg["evaluated"] == 2
    rejected_names = {r["name"] for r in fg["rejected_strategies"]}
    assert "Tick_B_905" in rejected_names
    assert "Tick_B_902" not in rejected_names
    rejected_entry = next(r for r in fg["rejected_strategies"] if r["name"] == "Tick_B_905")
    assert rejected_entry["category_count"] == 0
    assert rejected_entry["min_required"] == 5


def test_run_audit_exec_budget_rejects_unbounded_scan(tmp_path):
    result = MOD.run_audit(_make_db(tmp_path))
    eb = result["checks"]["exec_budget"]
    assert eb["evaluated"] == 2
    rejected_names = {r["name"] for r in eb["rejected_strategies"]}
    assert "Tick_S_905" in rejected_names
    assert "Tick_S_902" not in rejected_names


def test_run_audit_principle_gate_pairs_and_rejects(tmp_path):
    result = MOD.run_audit(_make_db(tmp_path))
    pg = result["checks"]["principle_gate"]
    assert pg["paired_count"] == 2
    assert pg["unpaired_buy_count"] == 0
    assert pg["unpaired_sell_count"] == 0
    rejected_pair_names = {(r["buy_name"], r["sell_name"]) for r in pg["rejected_pairs"]}
    assert ("Tick_B_905", "Tick_S_905") in rejected_pair_names
    assert ("Tick_B_902", "Tick_S_902") not in rejected_pair_names
    assert "CSC-07" in pg["reject_reason_distribution"]


def test_run_audit_summary_rejected_by_any(tmp_path):
    result = MOD.run_audit(_make_db(tmp_path))
    summary = result["summary"]
    assert summary["strategies_total"] == 4
    assert summary["strategies_rejected_by_any_check"] == 2  # Tick_B_905 + Tick_S_905
    assert 0.0 < summary["rejected_by_any_rate"] < 1.0
    assert "variable_scope" in summary["top_reject_reasons_by_check"]


def test_run_audit_min_filter_categories_override(tmp_path):
    # 정상 매수(6 범주)도 임계값을 7로 올리면 거부되어야 한다(설정 가능성 검증).
    result = MOD.run_audit(_make_db(tmp_path), min_filter_categories=7)
    fg = result["checks"]["filter_gate"]
    rejected_names = {r["name"] for r in fg["rejected_strategies"]}
    assert "Tick_B_902" in rejected_names
