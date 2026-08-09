# -*- coding: utf-8 -*-
"""S7-b 계약 테스트 — 진입 후보의 원장 적재.

계약:
  1. **진입 후보는 PASS 를 받을 수 없다.** 원장의 PASS 는 "챔피언 이상 + 통계 확정"인데
     진입이 다르면 짝지은 검정을 쓸 수 없어 확정 수단이 없다. 상한은 PROMISING 이다.
     이 구분이 흐려지면 원장의 "승격 0종"이라는 핵심 정보가 무의미해진다.
  2. 게이트를 못 넘은 후보도 남긴다 — "이건 이미 해 봤다"가 원장의 값이다.
  3. 짝지은 필드는 비운다 — 없는 것을 0 으로 채우면 있는 것처럼 읽힌다.
  4. 게이트는 셋(거래 증가·건당·자본)을 **전부** 넘어야 통과다.
"""
from __future__ import annotations

import pytest

from ai_strategy_loop.controller import strategy_ledger as sl
from ai_strategy_loop.labeling import run_entry_relax as rr

BASE = {"trade_count": 361, "avg_profit_pct": 0.67, "total_profit_pct": 241.16}


def _report(*outcomes):
    return {"lane": "tick", "design": [20220323, 20250822],
            "champion_buy": "Tick_B_902_905", "baseline_sell": "Tick_S_902_905",
            "outcomes": list(outcomes)}


def _outcome(name, trades, per_trade, total, **kw):
    engine = {"trade_count": trades, "avg_profit_pct": per_trade,
              "total_profit_pct": total, "seed_capital": 1_004_275,
              "win_rate": 50.0, "total_profit_krw": 1, "cagr": 1.0,
              "mdd_pct": 1.0, "tpi": 1.0, "avg_hold_time": 400.0,
              "max_hold_count": 1}
    engine.update(kw)
    return {"name": name, "buy": name, "sell": "Tick_S_902_905",
            "job_id": "job1", "engine": engine, "gate": rr._gate(BASE, engine)}


# ---------------------------------------------------------------------------
# 게이트
# ---------------------------------------------------------------------------

def test_gate_needs_all_three():
    """★ 빈도를 위해 기대값을 팔지 않는다 — 셋 다 넘어야 한다."""
    good = rr._gate(BASE, {"trade_count": 378, "avg_profit_pct": 0.68, "total_profit_pct": 253.34})
    assert good["pass"] is True and good["trade_gain"] == 17

    # 거래는 늘었는데 건당이 떨어졌다
    assert rr._gate(BASE, {"trade_count": 489, "avg_profit_pct": 0.40,
                           "total_profit_pct": 97.79})["pass"] is False
    # 건당은 같은데 거래가 안 늘었다
    assert rr._gate(BASE, {"trade_count": 361, "avg_profit_pct": 0.67,
                           "total_profit_pct": 241.16})["pass"] is False
    # 건당·거래는 좋은데 자본 대비가 미달
    assert rr._gate(BASE, {"trade_count": 400, "avg_profit_pct": 0.70,
                           "total_profit_pct": 200.0})["pass"] is False


def test_gate_treats_missing_metrics_as_failure():
    assert rr._gate(BASE, {"trade_count": 400, "avg_profit_pct": None,
                           "total_profit_pct": 300.0})["pass"] is False


# ---------------------------------------------------------------------------
# 원장 적재
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "ledger.db")
    monkeypatch.setattr(sl, "_DEFAULT_DB", path)
    return path


def test_entry_candidate_never_gets_pass(db):
    """★ 통계 확정 수단이 없으므로 PROMISING 이 상한이다."""
    rr.sync_ledger(_report(_outcome("W7_B_RELAX_905_전일비", 378, 0.68, 253.34)))
    rows = sl.latest_per_candidate(db_path=db)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "PROMISING"
    assert rows[0]["family"] == "entry"
    assert sl.summary(db_path=db)["promoted"] == 0


def test_failed_candidates_are_kept(db):
    rr.sync_ledger(_report(
        _outcome("relax_a", 489, 0.40, 97.79),
        _outcome("relax_b", 378, 0.68, 253.34),
    ))
    verdicts = {r["sell_name"]: r["verdict"] for r in sl.latest_per_candidate(db_path=db)}
    assert verdicts == {"relax_a": "REJECT", "relax_b": "PROMISING"}


def test_paired_fields_stay_empty(db):
    """★ 없는 것을 0 으로 채우면 '차이 0' 으로 읽힌다."""
    rr.sync_ledger(_report(_outcome("relax_a", 378, 0.68, 253.34)))
    row = sl.latest_per_candidate(db_path=db)[0]
    for key in ("paired_pairs", "paired_mean_diff_pct", "paired_ci_low",
                "paired_ci_high", "paired_significant", "paired_required"):
        assert row[key] is None, key


def test_reason_records_which_gate_failed(db):
    rr.sync_ledger(_report(_outcome("relax_a", 489, 0.40, 97.79)))
    reason = sl.latest_per_candidate(db_path=db)[0]["verdict_reason"]
    assert "거래 +128" in reason and "건당 미달" in reason and "자본 미달" in reason


def test_baseline_link_is_recorded(db):
    rr.sync_ledger(_report(_outcome("relax_a", 378, 0.68, 253.34)))
    row = sl.latest_per_candidate(db_path=db)[0]
    assert row["baseline_id"] == "Tick_B_902_905::Tick_S_902_905"


# ---------------------------------------------------------------------------
# 기준선 해소 — W6 실패(축 불일치)의 교정
# ---------------------------------------------------------------------------

CHAMP_SELL = rr.CHAMPION_SELL
B3_SELL = "W4_S_TRAIL_5_2"


def _engine_report():
    """확장 구간 실측 리포트의 모양 — 기준선 팔 + 도전자 팔들."""
    return {
        "design": [20220323, 20250822],
        "champion_buy": "Tick_B_902_905", "baseline_sell": CHAMP_SELL,
        "baseline_metrics": {"trade_count": 361, "avg_profit_pct": 0.67,
                             "total_profit_pct": 241.16},
        "outcomes": [
            {"arm": "baseline", "sell": CHAMP_SELL, "job_id": "champ",
             "engine": {"trade_count": 361, "avg_profit_pct": 0.67,
                        "total_profit_pct": 241.16}},
            {"arm": "challenger_3", "sell": B3_SELL, "job_id": "b3",
             "engine": {"trade_count": 352, "avg_profit_pct": 1.06,
                        "total_profit_pct": 185.66}},
        ],
    }


def test_champion_sell_resolves_to_the_champion_pair():
    metrics, arm = rr.resolve_baseline(_engine_report(), CHAMP_SELL)
    assert metrics["total_profit_pct"] == 241.16
    assert arm["job_id"] == "champ"


def test_b3_sell_resolves_to_the_b3_arm_not_the_champion():
    """★ W6 실패의 교정 — 매도가 B3 면 기준선도 B3 여야 한다.

    챔피언 기준선(241.16%)으로 재면 B3 청산 후보는 전부 떨어진다(B3 자체가
    185.66%). 그러면 진입 절의 효과가 아니라 청산 차이를 재는 셈이다.
    """
    metrics, arm = rr.resolve_baseline(_engine_report(), B3_SELL)
    assert metrics["total_profit_pct"] == 185.66
    assert metrics["avg_profit_pct"] == 1.06
    assert arm["job_id"] == "b3"


def test_unmeasured_sell_refuses_with_the_available_list():
    """없는 매도식으로 조용히 챔피언 기준선을 쓰지 않는다."""
    with pytest.raises(SystemExit) as err:
        rr.resolve_baseline(_engine_report(), "W4_S_TRAIL_9_9")
    assert "W4_S_TRAIL_5_2" in str(err.value)      # 가능한 목록을 알려 준다


def test_arm_without_trades_is_refused():
    report = _engine_report()
    report["outcomes"][1]["engine"]["trade_count"] = 0
    with pytest.raises(SystemExit):
        rr.resolve_baseline(report, B3_SELL)
