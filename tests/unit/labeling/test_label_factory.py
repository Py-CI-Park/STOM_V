"""QSP9 M-0 라벨 공장 — 합성 tick DB 로 라벨 명세(실행계획 v2 §3)를 검증한다.

함정 대응 검증: 체결 가정(호가 기반 A/현재가 기반 B), 스테일 초, 상한가·VI 플래그,
horizon 사전 고정·세션 절단, 라벨 2족(고정 h + MFE/MAE), 진입창 09:20 컷.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.label_factory import build_day_labels


DAY = 20250403


def _row(hhmmss: int, price: float, *, ask: float | None = None, bid: float | None = None,
         rate: float = 5.0, tv: float = 10.0, vi: float = 0.0, high: float | None = None,
         low: float | None = None) -> dict:
    """한 초 스냅샷. ask/bid 미지정이면 현재가 ±1호가(10원)."""
    return {
        "index": DAY * 1_000_000 + hhmmss,
        "현재가": price, "시가": 1000.0, "고가": high if high is not None else price,
        "저가": low if low is not None else 1000.0, "등락율": rate,
        "당일거래대금": 100.0, "체결강도": 100.0, "초당매수수량": 10.0, "초당매도수량": 5.0,
        "거래대금증감": 0.0, "전일비": 1.0, "회전율": 1.0, "전일동시간비": 1.0,
        "시가총액": 2000.0, "라운드피겨위5호가이내": 0.0, "VI해제시간": 0.0,
        "VI가격": vi, "VI호가단위": 10.0, "초당거래대금": tv,
        "고저평균대비등락율": 1.0, "저가대비고가등락율": 1.0,
        "초당매수금액": 1.0, "초당매도금액": 1.0,
        "당일매수금액": 1.0, "최고매수금액": 1.0, "최고매수가격": price,
        "당일매도금액": 1.0, "최고매도금액": 1.0, "최고매도가격": price,
        **{f"매도호가{i}": (ask if ask is not None else price + 10.0) + 10.0 * (i - 1) for i in range(1, 6)},
        **{f"매수호가{i}": (bid if bid is not None else price - 10.0) - 10.0 * (i - 1) for i in range(1, 6)},
        **{f"매도잔량{i}": 100.0 for i in range(1, 6)},
        **{f"매수잔량{i}": 100.0 for i in range(1, 6)},
        "매도총잔량": 500.0, "매수총잔량": 500.0, "매도수5호가잔량합": 400.0, "관심종목": 1.0,
    }


def _make_db(path: Path, rows: list[dict], code: str = "005930") -> str:
    con = sqlite3.connect(path)
    pd.DataFrame(rows).to_sql(code, con, index=False)
    pd.DataFrame({"index": [DAY * 1_000_000 + 90001], "거래대금순위": [code]}).to_sql("moneytop", con, index=False)
    con.close()
    return str(path)


def _flat_minutes(start_hhmmss: int, minutes: int, price: float = 1000.0) -> list[dict]:
    """초 단위 연속 스냅샷 (분 경계를 넘는 sod 산술 검증용)."""
    rows = []
    h, m, s = start_hhmmss // 10000, (start_hhmmss // 100) % 100, start_hhmmss % 100
    sod = h * 3600 + m * 60 + s
    for k in range(minutes * 60):
        t = sod + k
        rows.append(_row(t // 3600 * 10000 + (t % 3600) // 60 * 100 + t % 60, price))
    return rows


def test_fixed_horizon_return_uses_declared_costs_and_both_price_bases(tmp_path: Path) -> None:
    # Given: 60초 뒤 현재가가 1000 → 1100 으로 오르는 경로 (호가는 현재가 ±10).
    rows = _flat_minutes(90000, 1)
    rows += [_row(90100 + i, 1100.0) for i in range(0, 40)]
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    first = out[out["시분초"] == 90000].iloc[0]
    # Then: B(현재가 기반) = 1100*(1-out) / (1000*(1+in)) - 1
    expect_b = (1100.0 * (1 - spec.COST_OUT)) / (1000.0 * (1 + spec.COST_IN)) - 1
    assert first["frB_60"] == pytest.approx(expect_b * 100, abs=1e-6)
    # A(호가 기반)는 매도호가1(1010)에 사서 매수호가1(1090)에 판다 — B 보다 항상 불리.
    expect_a = (1090.0 * (1 - spec.COST_OUT)) / (1010.0 * (1 + spec.COST_IN)) - 1
    assert first["frA_60"] == pytest.approx(expect_a * 100, abs=1e-6)
    assert first["frA_60"] < first["frB_60"]


def test_stale_forward_price_is_rejected(tmp_path: Path) -> None:
    # Given: 09:00~09:01 데이터 뒤 큰 수집 공백, 09:10 에 재등장.
    rows = _flat_minutes(90000, 1) + [_row(91000, 1200.0)]
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    first = out[out["시분초"] == 90000].iloc[0]
    # Then: t+120=09:02 시점 가격은 60초 전 관측(스테일) → 라벨 무효.
    assert pd.isna(first["frB_120"])


def test_horizons_are_capped_at_forced_exit_and_data_end(tmp_path: Path) -> None:
    # Given: 09:19:00~09:20:59 만 존재 (마지막 관측 09:20:59).
    rows = _flat_minutes(91900, 2)
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    row_1919 = out[out["시분초"] == 91900].iloc[0]
    # Then: h=300 은 09:24 지만 데이터가 09:20:59 에 끝난다 → NaN. h=60 은 유효.
    assert pd.isna(row_1919["frB_300"])
    assert not pd.isna(row_1919["frB_60"])
    # 진입창은 09:20:00 까지 — 09:20:01 이후 행은 진입 후보가 아니다.
    assert out["시분초"].max() <= spec.ENTRY_END


def test_close_label_uses_last_price_and_flags_truncation(tmp_path: Path) -> None:
    # Given: 09:00~09:05 에서 수집 종료 (09:28 훨씬 전).
    rows = _flat_minutes(90000, 5)
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    first = out[out["시분초"] == 90000].iloc[0]
    assert not pd.isna(first["frB_close"])
    assert first["close_truncated"] == 1  # 09:28 이전에 잘림


def test_mfe_mae_are_forward_window_shape_labels(tmp_path: Path) -> None:
    # Given: 진입 후 +3% 까지 갔다가 -2% 로 끝나는 경로.
    rows = [_row(90000 + i, 1000.0) for i in range(3)]
    rows += [_row(90003 + i, 1030.0) for i in range(3)]     # MFE 구간
    rows += [_row(90010 + i, 980.0) for i in range(60)]     # MAE 구간
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    first = out[out["시분초"] == 90000].iloc[0]
    assert first["mfe_300"] == pytest.approx(3.0, abs=0.01)
    assert first["mae_300"] == pytest.approx(-2.0, abs=0.01)


def test_exclusion_flags_no_trade_limit_up_vi(tmp_path: Path) -> None:
    # 주의: HHMMSS 를 정수 덧셈으로 만들면 초=60~99 인 가짜 시각이 생긴다(명세의 시각 산술 함정).
    filler = [r for r in _flat_minutes(90010, 3)]
    rows = [
        _row(90000, 1000.0, tv=0.0),                      # 체결 없는 초
        _row(90001, 1000.0, rate=29.4),                   # 상한가 근접
        _row(90002, 1000.0, vi=1030.0),                   # VI가격-5호가(980) 이상 → 근접
        _row(90003, 1000.0),                              # 정상
    ] + filler
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    by = {int(r["시분초"]): r for _, r in out.iterrows()}
    assert by[90000]["flag_no_trade"] == 1
    assert by[90001]["flag_limit_up"] == 1
    assert by[90002]["flag_vi_near"] == 1
    assert by[90003][["flag_no_trade", "flag_limit_up", "flag_vi_near"]].sum() == 0


def test_derived_features_match_902905_formulas(tmp_path: Path) -> None:
    rows = _flat_minutes(90000, 3)
    db = _make_db(tmp_path / "tick.db", rows)

    out = build_day_labels(db, day=DAY)

    first = out.iloc[0]
    전일종가 = 1000.0 / (1 + 5.0 / 100)
    assert first["시가등락율"] == pytest.approx((1000.0 - 전일종가) / 전일종가 * 100, abs=1e-6)
    assert first["시가대비등락율"] == pytest.approx(0.0, abs=1e-9)
    assert first["초당순매수금액"] == pytest.approx((10.0 - 5.0) * 1000.0 / 1_000_000, abs=1e-9)
    assert first["spread_pct"] == pytest.approx((1010.0 - 990.0) / 1000.0 * 100, abs=1e-6)
    assert first["분"] == 0  # 09:00 분 버킷


def test_moneytop_is_skipped_and_output_has_identity_columns(tmp_path: Path) -> None:
    rows = _flat_minutes(90000, 2)
    db = _make_db(tmp_path / "tick.db", rows, code="900310")

    out = build_day_labels(db, day=DAY)

    assert set(out["종목코드"]) == {"900310"}
    assert set(out["일자"]) == {DAY}
    # moneytop 이 종목으로 새지 않았다.
    assert "moneytop" not in set(out["종목코드"])
