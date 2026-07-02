"""T0.2 슬리피지 다중 프로파일(tick0/1/2/3) advisory 단위 테스트.

합성 per-trade 결과행/CSV(한국어 컬럼, utf-8-sig)로
ai_strategy_loop/fitness/slippage_profiles.py 계약과
cli/research_ranking.py advisory 병기, cli/research_loop.py opt-in 배선,
controller/condition_discovery.py 승격 slippage hard gate 판정(순수 함수)을 검증한다.
DB/엔진/런타임 접근 없음 — 순수 파일/행 기반.
"""
from __future__ import annotations

import csv
import json
import math

import pytest

from ai_strategy_loop.controller.condition_discovery import (
    evaluate_slippage_gate,
    preset_policy,
)
from ai_strategy_loop.fitness.slippage_profiles import (
    DEFAULT_SLIPPAGE_TICKS,
    compute_slippage_profiles,
    krx_tick_size,
    slippage_profiles_from_csv,
)
from cli.research_loop import ResearchLoopConfig, _candidate_slippage_fields
from cli.research_ranking import _rank_candidate_results

_COLUMNS = ["종목명", "매수시간", "매도시간", "매수가", "매도가", "매수금액", "매도금액", "수익률", "수익금"]


def _write_csv(path, rows):
    """합성 결과 CSV를 utf-8-sig(BOM)로 기록한다 — 실제 결과 파일 인코딩과 동일."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _trade(buy_price, sell_price, qty, *, sell_day="20250102", name="테스트"):
    """합성 정합 행: 수익금=총스프레드×수량(세전), 매수금액으로 수량이 정확 역산된다."""
    profit = (sell_price - buy_price) * qty
    return {
        "종목명": name,
        "매수시간": f"{sell_day}090000",
        "매도시간": f"{sell_day}100000",
        "매수가": buy_price,
        "매도가": sell_price,
        "매수금액": buy_price * qty,
        "매도금액": sell_price * qty,
        "수익률": round((sell_price / buy_price - 1) * 100, 2),
        "수익금": profit,
    }


def _net_trade(buy_price, sell_price, qty, *, sell_day="20250102", name="테스트"):
    """실전 결과 CSV와 동일한 세후 순수익금 행(utility/static.py GetKiwoomPgSgSp 모델).

    매도금액은 실제 결과 파일처럼 세금/수수료 차감 후 평가금액(pg)이며
    수익금 = 매도금액 - 매수금액 관계가 정확히 성립한다.
    """
    bg = buy_price * qty
    cg = sell_price * qty
    texs = int(cg * 0.0018)
    bfee = int(bg * 0.00015 / 10) * 10
    sfee = int(cg * 0.00015 / 10) * 10
    pg = int(cg - texs - bfee - sfee)
    return {
        "종목명": name,
        "매수시간": f"{sell_day}090000",
        "매도시간": f"{sell_day}100000",
        "매수가": buy_price,
        "매도가": sell_price,
        "매수금액": bg,
        "매도금액": pg,
        "수익률": round((pg / bg - 1) * 100, 2),
        "수익금": pg - bg,
    }


# ── (a) krx_tick_size 경계값 (재수출 계약) ───────────────────────────────


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (1999, 1.0),
        (2000, 5.0),
        (4999, 5.0),
        (5000, 10.0),
        (19999, 10.0),
        (20000, 50.0),
        (49999, 50.0),
        (50000, 100.0),
        (199999, 100.0),
        (200000, 500.0),
        (499999, 500.0),
        (500000, 1000.0),
    ],
)
def test_krx_tick_size_boundaries(price, expected):
    assert krx_tick_size(price) == expected


# ── (b) tick0 == 원본 총수익 + 매수 +n틱/매도 -n틱 방향 부호 ─────────────


def test_tick0_matches_base_and_direction_signs():
    rows = [_trade(10000, 10500, 10)]  # 수익 5000, 틱 10원, 틱당 비용 (10+10)×10=200.
    report = compute_slippage_profiles(rows)

    assert report["ticks"] == list(DEFAULT_SLIPPAGE_TICKS)
    assert report["trade_count"] == 1
    assert report["base_total_profit"] == pytest.approx(5000.0)

    tick0 = report["profiles"]["tick0"]
    assert tick0["total_profit"] == pytest.approx(5000.0)
    assert tick0["profit_delta"] == pytest.approx(0.0)
    assert tick0["per_trade_adjustment"] == pytest.approx(0.0)
    assert tick0["profit_retention_ratio"] == pytest.approx(1.0)
    assert tick0["profit_positive"] is True

    # 매수 +1틱(10010)·매도 -1틱(10490) → (10490-10010)×10 = 4800.
    tick1 = report["profiles"]["tick1"]
    assert tick1["total_profit"] == pytest.approx(4800.0)
    assert tick1["profit_delta"] == pytest.approx(-200.0)  # 항상 불리(<=0) 방향.
    assert tick1["per_trade_adjustment"] == pytest.approx(-200.0)
    assert tick1["profit_retention_ratio"] == pytest.approx(0.96)

    # 선형성: tick3 = base - 3×틱당비용.
    assert report["profiles"]["tick3"]["total_profit"] == pytest.approx(5000.0 - 3 * 200.0)


# ── (c) 틱 증가 → 손익 단조 비증가 ───────────────────────────────────────


def test_profit_monotonically_non_increasing_with_ticks():
    rows = [
        _trade(10000, 10500, 10),
        _trade(3000, 3200, 50),
        _trade(250000, 260000, 2),
    ]
    report = compute_slippage_profiles(rows, ticks=(0, 1, 2, 3))
    totals = [report["profiles"][f"tick{n}"]["total_profit"] for n in (0, 1, 2, 3)]
    for prev, cur in zip(totals, totals[1:]):
        assert cur < prev  # 모든 거래 수량>0 → 엄격 단조감소.


# ── (d) MDD: 일별 재집계 가능할 때만 계산, 불가하면 None ─────────────────


def test_mdd_amount_uses_daily_curve_when_days_available():
    rows = [
        _trade(10000, 10500, 10, sell_day="20250102"),   # +5000 → cum 5000 (peak)
        _trade(10000, 9700, 10, sell_day="20250103"),    # -3000 → cum 2000
        _trade(10000, 9900, 10, sell_day="20250106"),    # -1000 → cum 1000 (dd 4000)
        _trade(10000, 10200, 10, sell_day="20250107"),   # +2000 → cum 3000
    ]
    report = compute_slippage_profiles(rows, ticks=(0,))
    assert report["profiles"]["tick0"]["mdd_amount"] == pytest.approx(4000.0)


def test_mdd_amount_is_none_without_sell_day():
    row = _trade(10000, 10500, 10)
    row.pop("매도시간")  # 거래일 미상 → 일별 재집계 불가(추측 금지).
    report = compute_slippage_profiles([row])
    assert report["trade_count"] == 1  # 손익 재계산 자체는 가능해 skip하지 않는다.
    for entry in report["profiles"].values():
        assert entry["mdd_amount"] is None
    # 빈 입력도 MDD 정의 불가 → None.
    empty = compute_slippage_profiles([])
    assert empty["trade_count"] == 0
    assert empty["profiles"]["tick0"]["mdd_amount"] is None
    assert empty["profiles"]["tick0"]["profit_retention_ratio"] is None  # base<=0.


# ── (e) 수량 역산 불가/모순 행 → skipped 정직 공시 ──────────────────────


def test_unrecoverable_rows_counted_as_skipped():
    good = _trade(10000, 10500, 10)
    # 매도가==매수가 + 수익금<0: 수수료 역전 한계 거래 — 순스프레드 역산으로 유지된다.
    fee_flipped_flat = dict(_trade(10000, 10000, 0), **{"수익금": -500})
    # 수익금 부호가 순손익 모델과 정반대(큰 손실 스프레드 + 양수 수익금) → 모순 행 skip.
    sign_conflict = dict(_trade(10000, 9000, 1), **{"수익금": 500})
    # 매도가==매수가 + 수익금==0 + 수량 단서 없음 → 역산 수량 0 → skip.
    flat_zero = dict(
        _trade(10000, 10000, 0), **{"수익금": 0, "매수금액": "", "매도금액": ""}
    )
    broken = {"매수가": "없음", "매도가": 10000, "수익금": 100}  # 파싱 실패.

    report = compute_slippage_profiles(
        [good, fee_flipped_flat, sign_conflict, flat_zero, broken]
    )
    assert report["trade_count"] == 2  # good + 수수료 역전 flat 거래.
    assert report["skipped_trades"] == 3
    assert report["profiles"]["tick0"]["total_profit"] == pytest.approx(
        good["수익금"] + fee_flipped_flat["수익금"]
    )


# ── (e2) 수량 역산 정밀화: 세후 순수익금 + 매수금액 우선 (관대 편향 제거) ─


def test_quantity_from_buy_amount_is_exact_for_net_profit_rows():
    # 실전형 행: 매수 10000/매도 10100/수량 10 → 세후 순수익금 799(총차익 1000 아님).
    row = _net_trade(10000, 10100, 10)
    assert row["수익금"] == 799
    report = compute_slippage_profiles([row])
    assert report["trade_count"] == 1
    assert report["base_total_profit"] == pytest.approx(799.0)
    # 종전 총스프레드 역산은 수량을 7.99로 과소 추정해 틱 페널티를 ~20% 낮췄다.
    # 매수금액/매수가 = 정확 수량 10 → tick1 페널티 = (10+10)×10 = 200.
    tick1 = report["profiles"]["tick1"]
    assert tick1["profit_delta"] == pytest.approx(-200.0)
    assert tick1["total_profit"] == pytest.approx(599.0)


def test_quantity_backcalc_without_amount_uses_net_spread():
    row = _net_trade(10000, 10100, 10)
    row.pop("매수금액")
    row.pop("매도금액")
    report = compute_slippage_profiles([row])
    assert report["trade_count"] == 1
    # 순스프레드 역산: 수량 ~= 10 (정수 절사 오차만 허용) → 페널티 ~= -200.
    assert report["profiles"]["tick1"]["profit_delta"] == pytest.approx(-200.0, rel=0.02)


def test_fee_flipped_marginal_trades_are_retained():
    # 매수가==매도가 → 세금/수수료만큼 손실(-200). 종전 구현은 이 행을 버려
    # 슬리피지에 가장 취약한 한계 거래가 게이트 증거에서 빠졌다.
    row = _net_trade(10000, 10000, 10)
    assert row["수익금"] == -200
    report = compute_slippage_profiles([row])
    assert report["trade_count"] == 1
    assert report["skipped_trades"] == 0
    assert report["profiles"]["tick1"]["total_profit"] == pytest.approx(-400.0)


def test_band_edge_tick_stepping_is_not_linear():
    # 매수 1999 +2틱: 1999→2000(1원 밴드)→2005(5원 밴드) = +6원 (선형 +2원 아님).
    # 매도 2100 -2틱: 2100→2095→2090 = -10원.
    row = _net_trade(1999, 2100, 100)
    report = compute_slippage_profiles([row], ticks=(0, 2))
    assert report["trade_count"] == 1
    assert report["profiles"]["tick2"]["profit_delta"] == pytest.approx(-(6 + 10) * 100.0)


# ── (f) CSV 경로 + JSON 직렬화 안전성 ────────────────────────────────────


def test_profiles_from_csv_matches_rows_and_is_json_safe(tmp_path):
    rows = [
        _trade(10000, 10500, 10, sell_day="20250102"),
        _trade(50000, 49000, 5, sell_day="20250103"),  # 손실 거래(수량>0 역산 가능).
    ]
    path = tmp_path / "trades.csv"
    _write_csv(path, rows)

    report = slippage_profiles_from_csv(str(path))
    expected = compute_slippage_profiles(rows)
    assert report["csv_path"] == str(path)
    assert {k: v for k, v in report.items() if k != "csv_path"} == expected

    text = json.dumps(report, ensure_ascii=False)  # 비유한수 있으면 여기서 실패.
    assert "NaN" not in text and "Infinity" not in text
    for entry in report["profiles"].values():
        for key in ("total_profit", "profit_delta"):
            assert math.isfinite(entry[key])

    # CSV 없음 → 무예외 trade_count=0 report(호출부를 막지 않는다).
    missing = slippage_profiles_from_csv(str(tmp_path / "no_such.csv"))
    assert missing["trade_count"] == 0
    assert missing["profiles"]["tick0"]["total_profit"] == 0.0


def test_csv_missing_required_column_reports_all_rows_skipped(tmp_path):
    # 필수 컬럼('매수가') 결측 스키마 불량 CSV: 전 행 skipped로 정직 공시 —
    # 진짜 빈 결과(trade_count=0, skipped=0)와 구분된다.
    path = tmp_path / "broken_schema.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["종목명", "매도가", "수익금"])
        writer.writeheader()
        writer.writerow({"종목명": "가", "매도가": 10000, "수익금": 100})
        writer.writerow({"종목명": "나", "매도가": 20000, "수익금": -50})

    report = slippage_profiles_from_csv(str(path))
    assert report["trade_count"] == 0
    assert report["skipped_trades"] == 2


def test_csv_without_sell_time_column_matches_rows_api(tmp_path):
    # '매도시간' 컬럼이 없어도 손익 재계산은 가능(MDD만 None) —
    # rows API(compute_slippage_profiles)와 동일 결과를 보장한다(경로 간 불일치 금지).
    row = _trade(10000, 10500, 10)
    row.pop("매도시간")
    columns = [c for c in _COLUMNS if c != "매도시간"]
    path = tmp_path / "no_sell_time.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerow(row)

    report = slippage_profiles_from_csv(str(path))
    expected = compute_slippage_profiles([row])
    assert report["trade_count"] == 1
    assert report["skipped_trades"] == 0
    assert report["profiles"]["tick0"]["mdd_amount"] is None
    assert {k: v for k, v in report.items() if k != "csv_path"} == expected


# ── (g) ranking advisory 병기: 순서 불변 + additive 필드 ─────────────────


def _ranked_candidate(index, promotion_score, *, slippage=None):
    item = {
        "index": index,
        "status": "ok",
        "promotion": {"passed": True, "score": promotion_score},
        "comparison": {
            "candidate_summary": {
                "trade_count": 10,
                "date_concentration": 0.5,
                "symbol_concentration": 0.5,
            },
            "trade_count_retention": 0.9,
        },
    }
    if slippage is not None:
        item["slippage_profiles"] = slippage
    return item


def test_ranking_keeps_order_and_adds_advisory_slippage_fields():
    slippage = compute_slippage_profiles([_trade(10000, 10500, 10)])
    without = [_ranked_candidate(1, 50.0), _ranked_candidate(2, 80.0)]
    with_slip = [
        _ranked_candidate(1, 50.0, slippage=slippage),
        _ranked_candidate(2, 80.0),
    ]

    ranked_without, best_without = _rank_candidate_results(without)
    ranked_with, best_with = _rank_candidate_results(with_slip)

    # 순서 로직 불변: slippage 병기 여부와 무관하게 동일 순위.
    assert [c["index"] for c in sorted(ranked_without, key=lambda c: c["rank"])] == [2, 1]
    assert [(c["index"], c["rank"]) for c in ranked_with] == [
        (c["index"], c["rank"]) for c in ranked_without
    ]
    assert best_with["index"] == best_without["index"] == 2

    annotated = next(c for c in ranked_with if c["index"] == 1)
    assert annotated["rank_score"]["slippage_profiles"] == slippage
    assert annotated["rank_score"]["slippage_profiles_authority"] == "advisory_only"
    # 병기하지 않은 후보의 rank_score 스키마는 기존과 동일(additive 보장).
    plain = next(c for c in ranked_with if c["index"] == 2)
    assert "slippage_profiles" not in plain["rank_score"]
    assert "adjusted_score" not in annotated["rank_score"]  # 순위 영향 필드 미기록.


# ── (h) 승격 slippage hard gate: 설정 필드 + 순수 판정 함수 ──────────────


def test_promotion_preset_declares_slippage_gate_profile():
    assert preset_policy("promotion").slippage_gate_profile == "tick2"
    assert preset_policy("fast").slippage_gate_profile == ""
    assert preset_policy("research").slippage_gate_profile == ""
    payload = preset_policy("promotion").to_dict()
    assert payload["slippage_gate_profile"] == "tick2"


def test_slippage_gate_passes_when_gate_profile_profit_positive():
    profitable = compute_slippage_profiles([_trade(10000, 10500, 10)])
    verdict = evaluate_slippage_gate("promotion", profitable)
    assert verdict["enabled"] is True
    assert verdict["gate_profile"] == "tick2"
    assert verdict["passed"] is True
    assert verdict["reason"] == "slippage_profile_profit_positive"
    assert verdict["profile_total_profit"] == pytest.approx(
        profitable["profiles"]["tick2"]["total_profit"]
    )


def test_slippage_gate_fails_when_gate_profile_profit_not_positive():
    # 세후 순수익 100원짜리 한계 거래(수량 10): tick2 페널티 (20+20)×10=400
    # → 100-400 = -300 → 게이트 실패.
    marginal = compute_slippage_profiles([_net_trade(10000, 10030, 10)])
    assert marginal["profiles"]["tick2"]["total_profit"] < 0.0
    verdict = evaluate_slippage_gate("promotion", marginal)
    assert verdict["passed"] is False
    assert verdict["reason"] == "slippage_profile_profit_not_positive"


@pytest.mark.parametrize(
    ("profiles", "reason"),
    [
        (None, "slippage_profiles_missing"),
        ({}, "slippage_profiles_missing"),
        ({"profiles": {"tick0": {"total_profit": 1.0}}}, "slippage_gate_profile_missing"),
        ({"profiles": {"tick2": {"total_profit": None}}}, "slippage_profile_total_profit_invalid"),
    ],
)
def test_slippage_gate_fails_closed_on_missing_or_invalid_evidence(profiles, reason):
    verdict = evaluate_slippage_gate("promotion", profiles)
    assert verdict["passed"] is False  # hard gate — 부재/불량 evidence는 통과 실패.
    assert verdict["reason"] == reason


def test_slippage_gate_not_configured_for_non_promotion_presets():
    profitable = compute_slippage_profiles([_trade(10000, 10500, 10)])
    for preset in ("fast", "research"):
        verdict = evaluate_slippage_gate(preset, profitable)
        assert verdict["enabled"] is False
        assert verdict["passed"] is None
        assert verdict["reason"] == "slippage_gate_not_configured"


def test_slippage_gate_accepts_bare_profile_mapping():
    verdict = evaluate_slippage_gate("promotion", {"tick2": {"total_profit": 5.0}})
    assert verdict["passed"] is True


# ── (i) research_loop opt-in 배선: 기본 OFF, 켜면 additive ───────────────


def test_research_loop_slippage_fields_default_off(tmp_path):
    path = tmp_path / "trades.csv"
    _write_csv(path, [_trade(10000, 10500, 10)])
    config = ResearchLoopConfig()
    assert config.slippage_profiles_enabled is False  # 기본 OFF(하위호환).
    assert _candidate_slippage_fields(config, str(path)) == {}


def test_research_loop_slippage_fields_opt_in(tmp_path):
    path = tmp_path / "trades.csv"
    _write_csv(path, [_trade(10000, 10500, 10), _trade(3000, 3100, 100)])
    config = ResearchLoopConfig(slippage_profiles_enabled=True)

    fields = _candidate_slippage_fields(config, str(path))
    report = fields["slippage_profiles"]
    assert report["trade_count"] == 2
    assert report["csv_path"] == str(path)
    assert set(report["profiles"]) == {"tick0", "tick1", "tick2", "tick3"}
    assert report["authority"] == "advisory_only"

    # CSV 경로 부재/무존재도 평가를 막지 않는다.
    assert _candidate_slippage_fields(config, None) == {}
    missing = _candidate_slippage_fields(config, str(tmp_path / "no_such.csv"))
    assert missing["slippage_profiles"]["trade_count"] == 0
