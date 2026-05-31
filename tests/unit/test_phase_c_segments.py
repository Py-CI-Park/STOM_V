"""Phase C 단위 테스트 (네트워크/실백테스트/실LLM 없음).

검증:
  C-1: analyze_segments_by_year — 연도-분할 cross-tab + cross-year 안정성.
    - 대형주가 매년 worst(음의 return_diff)면 'avoid' stable cell로 플래그된다.
    - 단일년만 등장하거나 부호가 뒤집히는 셀은 stable로 잡히지 않는다.
    - is_holdout=True → ValueError (analyze_segments와 동일 계약).
    - 날짜 컬럼 없음 → insufficient_trades status(무예외).
  C-2: FINE_TIME_BUCKETS 5분 세분 + 기본 byte-동일.
    - add_time_segment(df, buckets=FINE_TIME_BUCKETS)가 시초 거래에 5분 라벨을 단다.
    - add_time_segment(df) 기본은 30분 coarse 라벨 그대로(불변).
    - analyze_segments(csv, fine_time=False)의 time_segments 라벨 == 기본 세그먼트
      (byte-동일), fine_time=True는 5분 라벨을 낸다.
  C-3: build_messages/generate_strategy 시간 분산 넛지 주입.
    - encourage_time_dispersion=True(buy)면 분산 가이드가 메시지에 들어가고,
      =False면 들어가지 않는다(byte-동일). 매도(sell)에는 무영향.
"""

import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy import (  # noqa: E402
    analyze_segments,
    analyze_segments_by_year,
    multiyear_to_page_data,
)
from ai_strategy_loop.autopsy.analyze import STATUS_INSUFFICIENT, STATUS_OK  # noqa: E402
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from cli.research_segments import (  # noqa: E402
    DEFAULT_TIME_BUCKETS,
    FINE_TIME_BUCKETS,
    add_time_segment,
)

B_COLS = [
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가",
]


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


# =====================================================================
# C-1 — 연도-분할 cross-year 안정성.
# =====================================================================
def _make_multiyear_rows():
    """2023~2025 3년, 대형주가 매년 worst(음의 return_diff)인 합성 데이터.

    각 연도에서:
      - 소형주(시총 1500억) → 양의 수익(+2.0). 그 해 평균보다 위 → 양의 return_diff.
      - 대형주(시총 12000억) → 음의 수익(-2.0). 그 해 평균보다 아래 → 음의 return_diff.
    이 부호가 3년 내내 동일하므로 대형은 'avoid', 소형은 'prefer' stable cell이 된다.
    각 (연도×밴드) 25건 = 연도당 50건(min_trades_per_year=20 충족).
    매도시간을 연도 컬럼으로 쓴다(YYYYMMDD...).
    """
    rows = []
    for year in (2023, 2024, 2025):
        for i in range(50):
            big = i < 25  # 앞 25개=대형(손실), 뒤 25개=소형(수익).
            row = {
                "수익률": -2.0 if big else 2.0,
                "수익금": -2000.0 if big else 2000.0,
                "R_MFE": 0.2 if big else 2.5,
                "R_MAE": -2.8 if big else -0.2,
                "보유시간": 30 if big else 12,
                "매도조건": "손절" if big else "익절",
                # 연도 도출용. 매수시간/매도시간 둘 다 같은 해로 둔다.
                "매수시간": int(f"{year}0102093000"),
                "매도시간": int(f"{year}0102093500"),
            }
            for c in B_COLS:
                if c == "B_시분초":
                    row[c] = 90200  # 모두 09:02 — 시간축은 degenerate(시드와 동일).
                elif c == "B_시가총액":
                    row[c] = 12000 if big else 1500
                else:
                    row[c] = 50.0 + (i % 7)
            rows.append(row)
    return rows


def test_by_year_flags_large_cap_as_stable_avoid(tmp_path):
    csv = _write_csv(tmp_path / "multiyear.csv", _make_multiyear_rows())
    result = analyze_segments_by_year(csv, min_trades_per_year=20, segment_min_samples=5)

    assert result.status == STATUS_OK
    # 3년 모두 평가 연도로 잡혀야 한다.
    assert sorted(y.year for y in result.years) == [2023, 2024, 2025]

    by_label = {(c.axis, c.label): c for c in result.stable_cells}
    # 대형주 시총 밴드가 cross-year 'avoid'로 표면화돼야 한다.
    assert ("market_cap", "대형") in by_label
    big_cell = by_label[("market_cap", "대형")]
    assert big_cell.direction == "avoid"
    assert sorted(big_cell.years_present) == [2023, 2024, 2025]
    assert len(big_cell.per_year_return_diff) == 3
    assert all(d < 0 for d in big_cell.per_year_return_diff)
    assert big_cell.mean_return_diff < 0

    # 소형주는 매년 양수 → 'prefer'.
    assert ("market_cap", "소형") in by_label
    assert by_label[("market_cap", "소형")].direction == "prefer"


def test_by_year_does_not_flag_flipping_or_single_year(tmp_path):
    """부호가 연도마다 뒤집히는 셀, 단일년만 등장하는 셀은 stable로 잡히지 않는다."""
    rows = []
    # 중형주(시총 5000억): 2023 양수, 2024 음수 → 부호 혼재 → stable 아님.
    for year, sign in ((2023, 1.0), (2024, -1.0)):
        for i in range(40):
            big = i < 20
            rows.append({
                "수익률": (-sign * 2.0) if big else (sign * 2.0),
                "수익금": (-sign * 2000.0) if big else (sign * 2000.0),
                "R_MFE": 1.0, "R_MAE": -1.0, "보유시간": 20,
                "매도조건": "x",
                "매수시간": int(f"{year}0102093000"),
                "매도시간": int(f"{year}0102093500"),
                **{c: (5000 if (c == "B_시가총액" and big) else
                       (1500 if c == "B_시가총액" else
                        (90200 if c == "B_시분초" else 50.0)))
                   for c in B_COLS},
            })
    # 초소형주(시총 500억): 2025년에만 등장 → 단일년 → stable 아님.
    for i in range(40):
        big = i < 20
        rows.append({
            "수익률": -2.0 if big else 2.0,
            "수익금": -2000.0 if big else 2000.0,
            "R_MFE": 1.0, "R_MAE": -1.0, "보유시간": 20, "매도조건": "x",
            "매수시간": 202506020930000,
            "매도시간": int("202506020935"),
            **{c: (500 if (c == "B_시가총액" and big) else
                   (1500 if c == "B_시가총액" else
                    (90200 if c == "B_시분초" else 50.0)))
               for c in B_COLS},
        })
    csv = _write_csv(tmp_path / "flip.csv", rows)
    result = analyze_segments_by_year(csv, min_trades_per_year=20, segment_min_samples=5)

    assert result.status == STATUS_OK
    labels = {(c.axis, c.label) for c in result.stable_cells}
    # 중형(부호 혼재)·초소형(단일년)은 stable로 잡히면 안 된다.
    assert ("market_cap", "중형") not in labels
    assert ("market_cap", "초소형") not in labels


def test_by_year_holdout_raises(tmp_path):
    csv = _write_csv(tmp_path / "h.csv", _make_multiyear_rows())
    with pytest.raises(ValueError):
        analyze_segments_by_year(csv, is_holdout=True)


def test_by_year_missing_date_column_status(tmp_path):
    """연도 도출용 날짜 컬럼이 전혀 없으면 크래시가 아니라 status로 표현한다."""
    rows = []
    for i in range(40):
        rows.append({
            "수익률": 1.0 if i % 2 else -1.0,
            "수익금": 100.0,
            **{c: (1500 if c == "B_시가총액" else (90200 if c == "B_시분초" else 50.0))
               for c in B_COLS},
        })
    csv = _write_csv(tmp_path / "nodate.csv", rows)
    result = analyze_segments_by_year(csv, min_trades_per_year=20)
    assert result.status == STATUS_INSUFFICIENT
    assert result.stable_cells == []
    assert result.years == []


def test_by_year_falls_back_to_buy_time(tmp_path):
    """year_column(매도시간)이 없으면 매수시간으로 폴백한다."""
    rows = []
    for year in (2023, 2024):
        for i in range(40):
            big = i < 20
            rows.append({
                "수익률": -2.0 if big else 2.0,
                "수익금": -2000.0 if big else 2000.0,
                "R_MFE": 1.0, "R_MAE": -1.0, "보유시간": 20, "매도조건": "x",
                "매수시간": int(f"{year}0102093000"),  # 매도시간 없음.
                **{c: (12000 if (c == "B_시가총액" and big) else
                       (1500 if c == "B_시가총액" else
                        (90200 if c == "B_시분초" else 50.0)))
                   for c in B_COLS},
            })
    csv = _write_csv(tmp_path / "buyonly.csv", rows)
    result = analyze_segments_by_year(csv, min_trades_per_year=20, segment_min_samples=5)
    assert result.status == STATUS_OK
    assert sorted(y.year for y in result.years) == [2023, 2024]


def test_multiyear_to_page_data_json_safe(tmp_path):
    csv = _write_csv(tmp_path / "p.csv", _make_multiyear_rows())
    result = analyze_segments_by_year(csv, min_trades_per_year=20, segment_min_samples=5)
    page = multiyear_to_page_data(result)
    import json

    json.dumps(page)  # 직렬화 가능해야 한다.
    assert page["status"] == STATUS_OK
    assert set(page["years"]) == {2023, 2024, 2025}
    assert len(page["stable_cells"]) <= 5
    for cell in page["stable_cells"]:
        assert set(cell.keys()) == {
            "label", "axis", "direction", "years_present",
            "per_year_return_diff", "mean_return_diff",
        }


# =====================================================================
# C-2 — 5분 시초 세분 + 기본 byte-동일.
# =====================================================================
def _make_early_time_rows():
    """시초 5분 셀에 걸치는 거래 + 시총 라벨."""
    times = [90100, 90600, 91100, 91600, 92100, 100000]  # 5분 셀 5개 + 오전 1개.
    rows = []
    for t in times:
        rows.append({
            "수익률": 1.0, "수익금": 100.0,
            "B_시분초": t, "B_시가총액": 1500,
        })
    return rows


def test_fine_buckets_produce_5min_labels():
    df = pd.DataFrame(_make_early_time_rows())
    fine = add_time_segment(df, buckets=FINE_TIME_BUCKETS)
    labels = list(fine["_time_segment"])
    # 시초 거래는 5분 셀, 10:00 거래는 coarse '오전'.
    assert labels == ["0900-0905", "0905-0910", "0910-0915", "0915-0920", "0920+", "오전"]


def test_default_buckets_unchanged():
    df = pd.DataFrame(_make_early_time_rows())
    coarse = add_time_segment(df)  # 기본 = DEFAULT_TIME_BUCKETS.
    coarse_explicit = add_time_segment(df, buckets=DEFAULT_TIME_BUCKETS)
    # 기본 호출과 명시 DEFAULT 호출이 동일하고, 시초는 전부 coarse '장초반'.
    assert list(coarse["_time_segment"]) == list(coarse_explicit["_time_segment"])
    assert list(coarse["_time_segment"]) == ["장초반"] * 5 + ["오전"]


def _make_segmented_rows_for_fine():
    """장초반 5분 셀 2개에 손익이 걸리는 합성 데이터(각 셀 >= 5건)."""
    rows = []
    # 09:01 셀 25건(손실, 소형) + 09:06 셀 25건(수익, 소형).
    for i in range(50):
        early = i < 25
        rows.append({
            "수익률": -1.0 if early else 1.0,
            "수익금": -1000.0 if early else 1000.0,
            "R_MFE": 0.3 if early else 2.0,
            "R_MAE": -2.5 if early else -0.2,
            "보유시간": 30, "매도조건": "x",
            "매수시간": 202501010901 if early else 202501010906,
            "B_시분초": 90100 if early else 90600,
            "B_시가총액": 1500,
            **{c: 50.0 for c in B_COLS if c not in ("B_시분초", "B_시가총액")},
        })
    return rows


def test_analyze_segments_fine_time_default_byte_identical(tmp_path):
    """fine_time=False는 기존 동작과 동일(coarse 장초반), True는 5분 라벨을 낸다."""
    csv = _write_csv(tmp_path / "seg.csv", _make_segmented_rows_for_fine())

    default_res = analyze_segments(csv, min_trades=10)
    explicit_false = analyze_segments(csv, min_trades=10, fine_time=False)
    fine_res = analyze_segments(csv, min_trades=10, fine_time=True)

    default_time_labels = sorted(s.label for s in default_res.time_segments)
    false_time_labels = sorted(s.label for s in explicit_false.time_segments)
    fine_time_labels = sorted(s.label for s in fine_res.time_segments)

    # 기본 호출 == fine_time=False (byte-동일 세그먼트).
    assert default_time_labels == false_time_labels
    # coarse는 두 거래 모두 '장초반' 한 칸으로 뭉친다.
    assert default_time_labels == ["장초반"]
    # fine은 09:01/09:06을 5분 셀 2개로 가른다.
    assert fine_time_labels == ["0900-0905", "0905-0910"]


# =====================================================================
# C-3 — 생성 시간 분산 넛지 주입.
# =====================================================================
def _buy_user_text(**kw):
    msgs = build_messages("buy", **kw)
    assert msgs[0]["role"] == "system"
    return msgs[1]["content"]


_DISPERSION_MARK = "09:00~09:20 구간에 분산"


def test_dispersion_nudge_injected_when_enabled():
    text = _buy_user_text(encourage_time_dispersion=True)
    assert _DISPERSION_MARK in text


def test_dispersion_nudge_absent_by_default():
    text_default = _buy_user_text()
    text_false = _buy_user_text(encourage_time_dispersion=False)
    assert _DISPERSION_MARK not in text_default
    # byte-동일: 기본 호출과 명시 False 호출이 동일한 user 메시지.
    assert text_default == text_false


def test_dispersion_nudge_no_effect_on_sell():
    """매도(sell) 경로엔 시간 분산 넛지가 영향 없다(byte-동일)."""
    sell_default = build_messages("sell")[1]["content"]
    sell_toggled = build_messages("sell", encourage_time_dispersion=True)[1]["content"]
    assert _DISPERSION_MARK not in sell_toggled
    assert sell_default == sell_toggled
