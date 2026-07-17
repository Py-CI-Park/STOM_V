"""alpha_lab.events 단위 테스트 — detectors(E1~E5)/outcomes (알파 랩 P2).

검증 대상(봉인 규약 — 2026-07-05 설계서 §4):
- E1~E5 합성 시나리오 감지: 유효 전이만 발화, 경계값, 창 한정, 1→0 전이.
- refractory: 사건족별 독립 120초/종목, 120초 미만 재발 무시(정확 120초 허용).
- 인과성: t 이후 행 변조가 t까지의 사건을 바꾸지 못한다(접두 불변성 포함).
- outcomes: 진입 (t_e+1) 매도호가1 / 지평 매수호가1 청산 — labels의
  adverse_fill·net_rate 재사용(P1 동일 비용 모형), 정직 제외 전수.
- stratify 층화 키(시총×시간밴드×등락율), min_n 셀 필터, 일 블록 부트스트랩
  EV·CI·p·BH-FDR, 플라시보 2종(random_time_matched/shift_plus_60) 파이프.
- 실DB 스모크(존재 시): 20240103 1일 E1 검출 수 >= 0.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alpha_lab.dataset.labels import adverse_fill, net_rate
from alpha_lab.dataset.reader import connect_ro, load_stock_rows
from alpha_lab.events import (
    EVENT_FAMILIES,
    REFRACTORY_SEC,
    SURGE_K,
    aggregate_cells,
    attach_cells,
    compare_with_placebo,
    detect_events,
    measure_event_outcomes,
    random_time_matched,
    shift_plus_60,
    stratify,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DB = REPO_ROOT / "_database" / "stock_tick_20240103.db"
DATE = "20240103"
DAY = int(DATE)


def _ts_at(seconds_from_0900: int) -> int:
    """09:00:00 기준 +초 오프셋의 int YYYYMMDDHHMMSS (datetime 롤오버 정확)."""
    base = datetime.strptime(DATE + "090000", "%Y%m%d%H%M%S")
    return int((base + timedelta(seconds=seconds_from_0900)).strftime("%Y%m%d%H%M%S"))


def _ts(hh: int, mm: int, ss: int) -> int:
    return int(f"{DATE}{hh:02d}{mm:02d}{ss:02d}")


def _row(**overrides) -> dict:
    """감지기 입력 기본 행 — 전 사건족 무발화 기준선.

    등락율 -1.0 → 갭% ≈ -1% < 0 (E4 비발화), 고가 평탄(E2 비발화),
    초당거래대금 0(E1 재개·E3 비발화), 라운드피겨 0(E5 비발화).
    """
    row = {
        "현재가": 10000.0, "시가": 10000.0, "고가": 10000.0, "저가": 9900.0,
        "등락율": -1.0, "시가총액": 800.0,
        "초당거래대금": 0.0, "당일거래대금": 0.0,
        "VI해제시간": 0.0, "라운드피겨위5호가이내": 0.0,
        "매도호가1": 10010.0, "매수호가1": 10000.0,
    }
    row.update(overrides)
    return row


def _hand_net(buy_fill: float, sell_fill: float) -> float:
    """테스트 독립 수기 net_rate — 봉인 공식 그대로."""
    buy_cost = buy_fill * (1.0 + 0.00015)
    return (sell_fill * (1.0 - 0.0018 - 0.00015) - buy_cost) / buy_cost


# ------------------------------------------------------------ detectors --


def test_sealed_detector_constants():
    assert EVENT_FAMILIES == ("E1", "E2", "E3", "E4", "E5")
    assert REFRACTORY_SEC == 120
    assert SURGE_K == 10.0


def test_e1_fires_on_valid_transition_then_first_resume_row():
    vi_new = float(f"{DAY}090045")
    rows = [
        (_ts_at(40), _row()),                                    # 기준선 VI=0.0
        (_ts_at(45), _row(VI해제시간=vi_new)),                    # 유효 전이 → 후보(거래 0)
        (_ts_at(46), _row(VI해제시간=vi_new)),                    # 여전히 0 → 대기
        (_ts_at(47), _row(VI해제시간=vi_new, 초당거래대금=5.0)),   # 첫 >0 → 발화
        (_ts_at(48), _row(VI해제시간=vi_new, 초당거래대금=5.0)),   # 재발화 없음
    ]
    assert detect_events(rows, day=DAY) == [{"event": "E1", "t0": _ts_at(47)}]


def test_e1_fires_same_second_when_trading_resumes_immediately():
    vi_new = float(f"{DAY}090150")
    rows = [
        (_ts_at(100), _row()),
        (_ts_at(110), _row(VI해제시간=vi_new, 초당거래대금=3.0)),  # 전이 행 자체가 재개 행
    ]
    assert detect_events(rows, day=DAY) == [{"event": "E1", "t0": _ts_at(110)}]


def test_e1_ignores_prevday_preopen_boundary_and_first_row_values():
    prev_day = float("20240102130000")
    pre_open = float(f"{DAY}085900")
    at_open = float(f"{DAY}090000")  # 시각>090000 아님(경계) → 비발화
    rows = [
        (_ts_at(40), _row(초당거래대금=5.0)),
        (_ts_at(41), _row(VI해제시간=prev_day, 초당거래대금=5.0)),  # 전일값 전이
        (_ts_at(42), _row(VI해제시간=pre_open, 초당거래대금=5.0)),  # 개장 전 값 전이
        (_ts_at(43), _row(VI해제시간=at_open, 초당거래대금=5.0)),   # 090000 경계 전이
    ]
    assert detect_events(rows, day=DAY) == []
    # 첫 관측행이 이미 당일 유효값 — '직전 관측과 달라짐'이 아니므로 비발화.
    first_valid = [(_ts_at(50), _row(VI해제시간=float(f"{DAY}090049"), 초당거래대금=5.0))]
    assert detect_events(first_valid, day=DAY) == []


def test_e2_fires_only_on_running_high_break_with_price_at_high():
    rows = [
        (_ts_at(40), _row(고가=10000.0, 현재가=10000.0)),  # 첫 행 — 직전 관측 없음
        (_ts_at(41), _row(고가=10050.0, 현재가=10050.0)),  # 갱신 + 현재가>=고가 → 발화
        (_ts_at(42), _row(고가=10050.0, 현재가=10050.0)),  # 갱신 아님
        (_ts_at(43), _row(고가=10100.0, 현재가=10090.0)),  # 갱신이지만 현재가<고가
    ]
    assert detect_events(rows, day=DAY) == [{"event": "E2", "t0": _ts_at(41)}]


def test_e3_surge_threshold_boundary():
    # s=90: 문턱 = 10 × max(900/90, 1) = 100 → 99.9 비발화.
    # s=100: 문턱 = 10 × max(1000/100, 1) = 100 → 100.0(경계 포함) 발화.
    rows = [
        (_ts_at(90), _row(당일거래대금=900.0, 초당거래대금=99.9)),
        (_ts_at(100), _row(당일거래대금=1000.0, 초당거래대금=100.0)),
    ]
    assert detect_events(rows, day=DAY) == [{"event": "E3", "t0": _ts_at(100)}]


def test_e3_floor_baseline_when_turnover_tiny():
    # 당일거래대금 0 → 기준선 바닥 1 → 문턱 10.
    rows = [
        (_ts_at(200), _row(당일거래대금=0.0, 초당거래대금=9.9)),
        (_ts_at(330), _row(당일거래대금=0.0, 초당거래대금=10.0)),
    ]
    assert detect_events(rows, day=DAY) == [{"event": "E3", "t0": _ts_at(330)}]


def test_e4_gap_up_fires_once_at_first_in_window_row():
    # 등락율 +2% → 전일종가 10000, 시가 10200 → 갭 +2%.
    gap = dict(현재가=10200.0, 시가=10200.0, 고가=10200.0, 등락율=2.0)
    rows = [
        (_ts_at(0), _row(**gap)),   # 09:00:00 — 창 밖(첫 관측행: 전일종가 봉인)
        (_ts_at(1), _row(**gap)),   # 창 안 첫 행 → 발화
        (_ts_at(2), _row(**gap)),   # 종목당 1회 — 재발화 없음
        (_ts_at(30), _row(**gap)),
    ]
    assert detect_events(rows, day=DAY) == [{"event": "E4", "t0": _ts_at(1)}]


def test_e4_zero_gap_fires_and_negative_gap_never():
    zero = dict(현재가=10000.0, 시가=10000.0, 등락율=0.0)  # 전일종가 10000 → 갭 0%
    rows = [(_ts_at(1), _row(**zero)), (_ts_at(2), _row(**zero))]
    assert detect_events(rows, day=DAY) == [{"event": "E4", "t0": _ts_at(1)}]
    neg = dict(현재가=10200.0, 시가=9900.0, 등락율=2.0)    # 전일종가 10000 → 갭 -1%
    rows_neg = [(_ts_at(1), _row(**neg)), (_ts_at(15), _row(**neg))]
    assert detect_events(rows_neg, day=DAY) == []


def test_e4_window_limits():
    gap = dict(현재가=10200.0, 시가=10200.0, 고가=10200.0, 등락율=2.0)
    # 첫 관측이 09:00:31 — 창 경과 → 영원히 비발화.
    late = [(_ts_at(31), _row(**gap)), (_ts_at(40), _row(**gap))]
    assert detect_events(late, day=DAY) == []
    # 09:00:30은 창 경계 포함.
    edge = [(_ts_at(30), _row(**gap))]
    assert detect_events(edge, day=DAY) == [{"event": "E4", "t0": _ts_at(30)}]


def test_e5_round_figure_exit_transition_only():
    rows = [
        (_ts_at(40), _row(라운드피겨위5호가이내=1.0)),   # 첫 행 — 직전 관측 없음
        (_ts_at(41), _row(라운드피겨위5호가이내=0.0)),   # 1→0 → 발화
        (_ts_at(42), _row(라운드피겨위5호가이내=0.0)),   # 0→0 비발화
        (_ts_at(43), _row(라운드피겨위5호가이내=1.0)),   # 0→1 비발화
        (_ts_at(160), _row(라운드피겨위5호가이내=1.0)),
        (_ts_at(165), _row(라운드피겨위5호가이내=0.0)),  # 직전 '관측' 1→0, +124초 → 발화
    ]
    assert detect_events(rows, day=DAY) == [
        {"event": "E5", "t0": _ts_at(41)},
        {"event": "E5", "t0": _ts_at(165)},
    ]


def test_refractory_per_family_and_exact_120s_boundary():
    def brk(price):
        return dict(고가=price, 현재가=price)

    rows = [
        (_ts_at(40), _row()),
        (_ts_at(41), _row(**brk(10050.0))),   # E2 발화
        (_ts_at(100), _row(**brk(10100.0))),  # +59초 → 억제(불응기 리셋 없음)
        (_ts_at(120), _row(고가=10100.0, 현재가=10090.0, 라운드피겨위5호가이내=1.0)),
        (_ts_at(125), _row(고가=10100.0, 현재가=10090.0, 라운드피겨위5호가이내=0.0)),  # E5 독립 발화
        (_ts_at(161), _row(**brk(10150.0))),  # E2 최초 발화 대비 정확 120초 → 허용
    ]
    assert detect_events(rows, day=DAY) == [
        {"event": "E2", "t0": _ts_at(41)},
        {"event": "E5", "t0": _ts_at(125)},
        {"event": "E2", "t0": _ts_at(161)},
    ]
    relaxed = detect_events(rows, day=DAY, refractory_sec=10)
    assert [e for e in relaxed if e["event"] == "E2"] == [
        {"event": "E2", "t0": _ts_at(41)},
        {"event": "E2", "t0": _ts_at(100)},
        {"event": "E2", "t0": _ts_at(161)},
    ]


def _causal_base_rows() -> list:
    """E2@45 → E1 후보 50/발화 60 → E3@100 시나리오 (s=31..140)."""
    rows = []
    for s in range(31, 141):
        over = {}
        if s == 45:
            over.update(고가=10050.0, 현재가=10050.0)
        elif s >= 46:
            over.update(고가=10050.0)
        if s >= 50:
            over["VI해제시간"] = float(f"{DAY}090049")
        if s == 60:
            over["초당거래대금"] = 5.0
        if s == 100:
            over["초당거래대금"] = 15.0
        rows.append((_ts_at(s), _row(**over)))
    return rows


def test_causality_future_rows_never_change_past_events():
    base_events = detect_events(_causal_base_rows(), day=DAY)
    assert base_events == [
        {"event": "E2", "t0": _ts_at(45)},
        {"event": "E1", "t0": _ts_at(60)},
        {"event": "E3", "t0": _ts_at(100)},
    ]
    # t> cut 행 전면 변조(거래대금 서지 주입) — cut까지의 사건은 불변이어야 한다.
    cut = _ts_at(70)
    mutant = [
        (t, dict(row, 초당거래대금=500.0) if t > cut else row)
        for t, row in _causal_base_rows()
    ]
    mutant_events = detect_events(mutant, day=DAY)
    assert mutant_events != base_events                     # 미래는 실제로 달라졌고
    assert [e for e in base_events if e["t0"] <= cut] == \
        [e for e in mutant_events if e["t0"] <= cut]        # 과거는 불변이다
    # 접두 불변성: 임의 접두 감지 == 전체 감지의 t0<=접두끝 필터.
    rows = _causal_base_rows()
    for k in (1, 40, 75, len(rows)):
        last_t0 = rows[k - 1][0]
        assert detect_events(rows[:k], day=DAY) == \
            [e for e in base_events if e["t0"] <= last_t0]


def test_detect_events_rejects_unsorted_input():
    rows = [(_ts_at(50), _row()), (_ts_at(49), _row())]
    with pytest.raises(ValueError):
        detect_events(rows, day=DAY)


# ------------------------------------------------------------- outcomes --


def test_measure_event_outcomes_costs_and_honest_exclusions():
    t_e = _ts_at(40)
    pairs = {
        t_e: _row(),
        _ts_at(41): _row(매도호가1=10000.0),
        _ts_at(100): _row(매수호가1=10500.0),
        _ts_at(220): _row(매수호가1=10050.0),
        _ts_at(340): _row(매수호가1=10200.0),
    }
    rows = {ts: dict(r, index=ts) for ts, r in pairs.items()}
    events = [{"event": "E2", "t0": t_e}]
    samples = measure_event_outcomes(events, rows, day=DAY, code="123456")
    assert len(samples) == 1
    s = samples[0]
    assert (s["event"], s["day"], s["code"], s["t0"]) == ("E2", DAY, "123456", t_e)
    assert s["row"] is rows[t_e]
    for h, bid in ((60, 10500.0), (180, 10050.0), (300, 10200.0)):
        assert s["net"][h] == pytest.approx(
            net_rate(*adverse_fill(10000.0, bid)), abs=1e-12)
    assert s["net"][60] == pytest.approx(_hand_net(10020.0, 10480.0), abs=1e-12)
    assert s["net"][60] > 0.0 > s["net"][180]

    def measured(rows_variant):
        return measure_event_outcomes(events, rows_variant, day=DAY, code="123456")

    assert measured({t: r for t, r in rows.items() if t != _ts_at(41)}) == []   # entry 결측
    zero_ask = dict(rows)
    zero_ask[_ts_at(41)] = dict(rows[_ts_at(41)], 매도호가1=0.0)
    assert measured(zero_ask) == []                                             # ask<=0
    assert measured({t: r for t, r in rows.items() if t != _ts_at(220)}) == []  # 지평 결측
    assert measured({t: r for t, r in rows.items() if t != t_e}) == []          # 사건행 결측


def test_measure_event_outcomes_minute_rollover():
    t_e = _ts_at(59)  # 09:00:59 — +1초/+61초가 분 경계를 넘는다.
    rows = {
        t_e: dict(_row(), index=t_e),
        _ts_at(60): dict(_row(매도호가1=10000.0), index=_ts_at(60)),
        _ts_at(120): dict(_row(매수호가1=10500.0), index=_ts_at(120)),
    }
    out = measure_event_outcomes(
        [{"event": "E5", "t0": t_e}], rows, day=DAY, code="000001", horizons=(61,))
    assert len(out) == 1
    assert out[0]["net"][61] == pytest.approx(
        net_rate(*adverse_fill(10000.0, 10500.0)), abs=1e-12)


def test_stratify_cell_key_axes_and_boundaries():
    caps = [500.0, 1000.0, 3000.0]
    chgs = [3.0, 10.0]

    def key(cap, hh, mm, ss, chg):
        row = {"index": _ts(hh, mm, ss), "시가총액": cap, "등락율": chg}
        return stratify(row, cap_bins_억=caps, band_minutes=5, chg_bins_pct=chgs)

    assert key(1500.0, 9, 7, 30, 5.0) == "cap2|t1|chg1"
    assert key(499.9, 9, 0, 1, 2.9) == "cap0|t0|chg0"
    assert key(500.0, 9, 4, 59, 3.0) == "cap1|t0|chg1"      # 빈 경계값 → 상위 빈
    assert key(5000.0, 9, 29, 59, 25.0) == "cap3|t5|chg2"   # 최상단 빈, 마지막 밴드
    assert key(800.0, 9, 5, 0, -2.0) == "cap1|t1|chg0"      # 09:05:00 → 밴드 1
    with pytest.raises(ValueError):
        stratify({"index": _ts(9, 1, 0)}, cap_bins_억=[1000.0, 500.0],
                 chg_bins_pct=chgs)  # 비정렬 빈 거부


def test_attach_cells_immutably_swaps_row_for_cell():
    row = {"index": _ts(9, 7, 30), "시가총액": 1500.0, "등락율": 5.0}
    sample = {"event": "E2", "day": DAY, "code": "123456", "t0": row["index"],
              "row": row, "net": {60: 0.01, 180: 0.0, 300: -0.01}}
    out = attach_cells([sample], cap_bins_억=[500.0, 1000.0, 3000.0],
                       chg_bins_pct=[3.0, 10.0])
    assert out[0]["cell"] == "cap2|t1|chg1"
    assert "row" not in out[0] and out[0]["net"] == sample["net"]
    assert "cell" not in sample and sample["row"] is row  # 원본 불변


def test_aggregate_cells_min_n_bootstrap_ev_and_fdr():
    """양성 대조 겸용 — 심어둔 EV(+0.02)가 셀 통계로 정확 회수돼야 한다."""
    def sample(day, cell, net60, net300):
        return {"event": "E2", "day": day, "code": "123456", "t0": _ts_at(40),
                "cell": cell, "net": {60: net60, 300: net300}}

    good = [sample(d, "cap1|t0|chg1", 0.02, -0.01)
            for d in (20240101, 20240102, 20240103, 20240104, 20240105)]
    thin = [sample(20240101, "cap0|t0|chg0", 0.05, 0.05) for _ in range(2)]
    rows = aggregate_cells(good + thin, min_n=3, n_boot=64, seed=11)
    keys = {(r["event"], r["cell"], r["horizon"]) for r in rows}
    assert keys == {("E2", "cap1|t0|chg1", 60), ("E2", "cap1|t0|chg1", 300)}
    by_h = {r["horizon"]: r for r in rows}
    assert by_h[60]["n"] == 5
    assert by_h[60]["ev"] == pytest.approx(0.02, abs=1e-12)
    assert by_h[60]["ci_low"] == pytest.approx(0.02)
    assert by_h[60]["ci_high"] == pytest.approx(0.02)
    assert by_h[60]["p"] == 0.0 and by_h[60]["fdr_pass"] is True
    assert by_h[300]["ev"] == pytest.approx(-0.01, abs=1e-12)
    assert by_h[300]["p"] == 1.0 and by_h[300]["fdr_pass"] is False
    assert aggregate_cells(good, min_n=6) == []                       # min_n 필터
    assert aggregate_cells(good + thin, min_n=3, n_boot=64, seed=11) == rows  # 결정성


def test_random_time_matched_deterministic_and_disjoint():
    rows = {_ts_at(s): dict(_row(), index=_ts_at(s)) for s in range(31, 61)}
    events = [{"event": "E2", "t0": _ts_at(40)}, {"event": "E3", "t0": _ts_at(50)}]
    p1 = random_time_matched(events, rows, seed=7)
    assert p1 == random_time_matched(events, rows, seed=7)  # 같은 seed → 재현
    assert [e["event"] for e in p1] == ["E2", "E3"]         # 사건족 보존
    ts = [e["t0"] for e in p1]
    assert len(set(ts)) == 2
    for t in ts:
        assert t in rows and t not in {_ts_at(40), _ts_at(50)}  # 사건 아닌 관측 초
    # 후보 부족: 사건 초뿐이면 빈 목록, 후보 1개면 1건만.
    assert random_time_matched(events, {_ts_at(40): rows[_ts_at(40)]}, seed=1) == []
    one = {_ts_at(40): rows[_ts_at(40)], _ts_at(41): rows[_ts_at(41)]}
    assert random_time_matched(events, one, seed=1) == [{"event": "E2", "t0": _ts_at(41)}]


def test_shift_plus_60_rollover_and_immutability():
    events = [{"event": "E1", "t0": int(f"{DAY}090059")},
              {"event": "E5", "t0": int(f"{DAY}092930")}]
    assert shift_plus_60(events) == [
        {"event": "E1", "t0": int(f"{DAY}090159")},
        {"event": "E5", "t0": int(f"{DAY}093030")},
    ]
    assert events[0]["t0"] == int(f"{DAY}090059")  # 원본 불변


def test_compare_with_placebo_merges_and_marks_missing_as_nan():
    real = [
        {"event": "E2", "cell": "cap1|t0|chg1", "horizon": 60, "n": 250,
         "ev": 0.004, "ci_low": 0.001, "ci_high": 0.007, "p": 0.01, "fdr_pass": True},
        {"event": "E2", "cell": "cap1|t0|chg1", "horizon": 300, "n": 250,
         "ev": 0.002, "ci_low": -0.001, "ci_high": 0.005, "p": 0.2, "fdr_pass": False},
    ]
    placebo_random = [{"event": "E2", "cell": "cap1|t0|chg1", "horizon": 60, "ev": 0.0001}]
    placebo_shift = [
        {"event": "E2", "cell": "cap1|t0|chg1", "horizon": 60, "ev": -0.0002},
        {"event": "E2", "cell": "cap1|t0|chg1", "horizon": 300, "ev": 0.0003},
    ]
    merged = compare_with_placebo(real, placebo_random, placebo_shift)
    assert merged[0]["cell"] == "cap1|t0|chg1" and merged[0]["ev"] == pytest.approx(0.004)
    assert merged[0]["placebo_ev_random"] == pytest.approx(0.0001)
    assert merged[0]["placebo_ev_shift"] == pytest.approx(-0.0002)
    assert math.isnan(merged[1]["placebo_ev_random"])  # 플라시보 셀 부재 → nan
    assert merged[1]["placebo_ev_shift"] == pytest.approx(0.0003)
    assert "placebo_ev_random" not in real[0]          # 원본 불변


def test_event_study_pipeline_end_to_end_with_double_placebo():
    """동일 파이프 원칙: 실사건·플라시보 2종이 같은 측정 경로를 지난다."""
    pairs = {}
    for s in range(31, 402):
        over = {}
        if s == 40:
            over.update(고가=10050.0, 현재가=10050.0)
        elif s > 40:
            over.update(고가=10050.0)
        pairs[_ts_at(s)] = _row(**over)
    rows = {ts: dict(r, index=ts) for ts, r in pairs.items()}
    events = detect_events(sorted(rows.items()), day=DAY)
    assert events == [{"event": "E2", "t0": _ts_at(40)}]

    bins = dict(cap_bins_억=[500.0, 1000.0], chg_bins_pct=[0.0])

    def pipe(evts):
        measured = measure_event_outcomes(evts, rows, day=DAY, code="123456")
        return aggregate_cells(attach_cells(measured, **bins),
                               min_n=1, n_boot=32, seed=3)

    real = pipe(events)
    merged = compare_with_placebo(
        real,
        pipe(random_time_matched(events, rows, seed=5)),
        pipe(shift_plus_60(events)),
    )
    assert len(real) == 3 and len(merged) == 3  # 지평 60/180/300 셀 행
    for row in merged:
        assert {"cell", "ev", "placebo_ev_random", "placebo_ev_shift"} <= set(row)
    # 시프트 플라시보(+60초)는 같은 셀에서 측정 가능해야 한다(평탄 시장 → 동일 EV).
    by_h = {r["horizon"]: r for r in merged}
    assert by_h[60]["placebo_ev_shift"] == pytest.approx(by_h[60]["ev"], abs=1e-12)


# --------------------------------------------------------- real DB smoke --


@pytest.mark.skipif(not REAL_DB.exists(), reason="_database/stock_tick_20240103.db 없음")
def test_real_db_e1_detection_smoke():
    conn = connect_ro(REAL_DB)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cursor if re.fullmatch(r"\d{6}", n)][:3]
        assert codes, "종목 테이블 0개 — DB 계약 확인 필요"
        e1_total = 0
        for code in codes:
            rows = load_stock_rows(conn, code)
            events = detect_events(sorted(rows.items()), day=DAY)
            assert all(e["event"] in EVENT_FAMILIES for e in events)
            t0s = [e["t0"] for e in events]
            assert t0s == sorted(t0s)
            assert all(int(f"{DAY}000000") <= t <= int(f"{DAY}235959") for t in t0s)
            e1_total += sum(1 for e in events if e["event"] == "E1")
    finally:
        conn.close()
    assert e1_total >= 0
