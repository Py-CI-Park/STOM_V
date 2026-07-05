"""alpha_lab.mcl.features — 봉인 동결표(F1~F11) 측정 구현 단위 테스트.

합성 rows 로 봉인식·윈도우 규칙(최소 관측/earliest 대체/latest 해석)·순간형
결측 규칙을 검증한다. DB 접근 0회.
"""
from __future__ import annotations

import math

import pytest

from alpha_lab.events.detectors import ts_shift
from alpha_lab.mcl.features import (
    N_SEALED_COMBOS,
    compute_features,
    feature_key,
    min_window_obs,
    sealed_feature_specs,
)

T0 = 20240102090100  # 09:01:00


def _sec(back: int) -> int:
    """t0 - back 초 (분 롤오버 정확 — 정수 뺄셈 금지)."""
    return ts_shift(T0, -back)


def _row(**overrides):
    base = {
        "현재가": 10000.0, "매도호가1": 10010.0, "매수호가1": 10000.0,
        "초당매수수량": 30.0, "초당매도수량": 10.0,
        "초당매수금액": 300.0, "초당매도금액": 100.0,
        "매수총잔량": 700.0, "매도총잔량": 300.0,
        "매수잔량1": 50.0, "매도잔량1": 40.0,
        "매도잔량2": 10.0, "매도잔량3": 10.0, "매도잔량4": 10.0, "매도잔량5": 10.0,
        "체결강도": 120.0, "라운드피겨위5호가이내": 1.0, "VI가격": 9500.0,
    }
    base.update(overrides)
    return base


def _mini_table():
    """봉인표 축약형 — sealed_feature_specs 입력 계약과 동일 필드."""
    table = []
    for fid in ("F1", "F2", "F3", "F4", "F5", "F9", "F11"):
        for w in (5, 10, 30):
            table.append({"id": fid, "kind": "windowed", "window_sec": w, "name": fid})
    for fid in ("F6", "F7", "F8", "F10"):
        table.append({"id": fid, "kind": "instant", "window_sec": None, "name": fid})
    return table


@pytest.fixture()
def specs():
    return sealed_feature_specs(_mini_table())


def test_sealed_specs_count_and_keys(specs):
    assert len(specs) == N_SEALED_COMBOS == 25
    assert specs[0]["key"] == "F1_w5"
    assert specs[-1]["key"] == "F10"
    assert feature_key("F3", 10) == "F3_w10"
    assert feature_key("F7", None) == "F7"


def test_sealed_specs_rejects_unknown_id():
    bad = _mini_table() + [
        {"id": "F99", "kind": "windowed", "window_sec": 5, "name": "x"}
    ]
    with pytest.raises(ValueError):
        sealed_feature_specs(bad)


def test_min_window_obs_rule():
    assert min_window_obs(5) == 3   # ceil(5/2)=3
    assert min_window_obs(10) == 5
    assert min_window_obs(30) == 15
    assert min_window_obs(2) == 2   # max(2, ...) 바닥.


def test_windowed_values_full_window(specs):
    rows = {_sec(back): _row() for back in range(0, 5)}  # 090056..090100 연속 5초.
    feats = compute_features(rows, T0, specs)
    # F1_w5: (150-50)/max(200,1) = 0.5 (동일 행 5개 합산).
    assert feats["F1_w5"] == pytest.approx(0.5)
    assert feats["F2_w5"] == pytest.approx(0.5)
    # F3_w5: (700-300)/1000 = 0.4.
    assert feats["F3_w5"] == pytest.approx(0.4)
    # F4_w5: 변화 없음 → 0. F9_w5: 차분 0. F11_w5: max=40, (40-40)/40=0.
    assert feats["F4_w5"] == pytest.approx(0.0)
    assert feats["F9_w5"] == pytest.approx(0.0)
    assert feats["F11_w5"] == pytest.approx(0.0)
    # F5_w5: 150 / max(mean(매도잔량1)=40,1) = 3.75.
    assert feats["F5_w5"] == pytest.approx(3.75)
    # 순간형.
    assert feats["F6"] == pytest.approx(90.0 / 1000.0)
    assert feats["F7"] == pytest.approx(10.0 / 10000.0)
    assert feats["F8"] == pytest.approx(1.0)
    assert feats["F10"] == pytest.approx(10000.0 / 9500.0 - 1.0)


def test_windowed_earliest_latest_substitution(specs):
    # w=5 에서 관측 3초(090056, 090058, 090100)만 존재 — 최소 관측(3) 충족.
    rows = {
        _sec(4): _row(매수잔량1=10.0, 매도잔량1=80.0, 체결강도=100.0),
        _sec(2): _row(),
        T0: _row(매수잔량1=70.0, 매도잔량1=20.0, 체결강도=130.0,
                 매수총잔량=800.0, 매도총잔량=200.0),
    }
    feats = compute_features(rows, T0, specs)
    # F4: [(70-10) - (20-80)] / max(800+200,1) = 120/1000.
    assert feats["F4_w5"] == pytest.approx(0.12)
    # F9: 130 - 100 = 30 (earliest 대체 규칙).
    assert feats["F9_w5"] == pytest.approx(30.0)
    # 관측 2초뿐인 w=5 는 NaN(최소 3 미달).
    rows2 = {_sec(4): _row(), T0: _row()}
    feats2 = compute_features(rows2, T0, specs)
    assert math.isnan(feats2["F1_w5"])


def test_f11_spoof_proxy_and_vi_zero(specs):
    rows = {
        _sec(2): _row(매도잔량2=500.0, 매도잔량3=500.0, 매도잔량4=0.0, 매도잔량5=0.0),
        _sec(1): _row(),
        T0: _row(VI가격=0.0),
    }
    feats = compute_features(rows, T0, specs)
    # far: t0-2 = 1000, 그 외 40 → max=1000, latest=40 → (1000-40)/1000.
    assert feats["F11_w5"] == pytest.approx(0.96)
    assert feats["F10"] == pytest.approx(0.0)  # VI가격<=0 → 0.0 (봉인식).


def test_instant_missing_t0_row_is_nan(specs):
    rows = {_sec(1): _row(), _sec(2): _row(), _sec(3): _row()}  # t0 행 결측.
    feats = compute_features(rows, T0, specs)
    assert math.isnan(feats["F6"])
    assert math.isnan(feats["F8"])
    # 윈도우형은 관측 3초로 계산 가능(w=5 최소 3).
    assert not math.isnan(feats["F1_w5"])


def test_time_rollover_window_collection(specs):
    # t0 = 09:00:02 — w=5 창은 08:59:58~09:00:02 를 덮지만 09:00:01 이후만 존재.
    t0 = 20240102090002
    rows = {20240102090001: _row(), 20240102090002: _row()}
    feats = compute_features(rows, t0, specs)
    assert math.isnan(feats["F1_w5"])  # 관측 2 < 3 — 정직 결측.
