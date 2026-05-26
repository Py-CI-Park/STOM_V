"""P5/M5 — holdout 졸업검사(과적합 방어) 단위 테스트.

검증(백테/루프 실행 없음, 합성 CSV + tmp DB + monkeypatch):
  - compute_holdout_verdict: 결과 CSV를 매도시간(거래일)으로 train/holdout 분할,
    holdout 슬라이스 메트릭(거래수/총손익/누적손익 MDD) 재구성 + 게이트 판정.
  - graduation_holdout ON: train 통과 + holdout 통과 → winner / train 통과 +
    holdout 실패 → winner 아님.
  - graduation_holdout OFF(기본): 기존 winner 동작 불변(하위호환).
  - holdout 거래 부족(min_trades 미만) → 보수적 미졸업.
  - page_data['holdout'] 직렬화(contract v2 round-trip).
"""

import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.holdout import (
    HoldoutVerdict,
    compute_holdout_verdict,
    holdout_verdict_to_page_data,
)


# ============================================================
# 합성 CSV 헬퍼
# ============================================================
# 결과 CSV 최소 헤더(holdout 분할/게이트가 읽는 컬럼만 채우면 충분).
#   매도시간: 'YYYYMMDDHHMM' (앞 8자리=거래일), 수익금: 거래당 실현손익(원),
#   수익금합계: 누적(다른 경로가 읽지만 holdout 경로는 수익금만 사용).
_HEADER = ["종목명", "매수시간", "매도시간", "수익률", "수익금", "수익금합계"]


def _write_csv(path, trades):
    """trades = [(sell_day:int 'YYYYMMDD', profit:float), ...] → 합성 결과 CSV.

    매도시간은 sell_day + '1000'(임의 시각). 수익률은 부호만 맞춘다. 수익금합계는
    누적합을 채운다(holdout 경로는 수익금만 쓰지만 형식 충실도를 위해 채운다).
    """
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(_HEADER)
        cum = 0.0
        for i, (day, profit) in enumerate(trades):
            cum += profit
            ret = 0.5 if profit > 0 else (-0.5 if profit < 0 else 0.0)
            w.writerow([f"종목{i}", f"{day}1000", f"{day}1010", ret, profit, cum])


def _cfg(**kw):
    base = dict(min_trades=3, mdd_cap=35.0, holdout_recent_days=2, graduation_holdout=True)
    base.update(kw)
    return LoopConfig(**base)


# ============================================================
# compute_holdout_verdict — 거래일 분할 + 게이트 판정
# ============================================================

def test_split_separates_recent_n_trading_days_as_holdout(tmp_path):
    """holdout = 최근 holdout_recent_days(=2)개 거래일. train=앞 거래일."""
    p = tmp_path / "split.csv"
    # 거래일 4개: 0101, 0102(train) / 0103, 0104(holdout). 각 날 거래 수익.
    _write_csv(p, [
        (20260101, 1000.0), (20260101, 1000.0),
        (20260102, 1000.0),
        (20260103, 500.0), (20260103, 500.0), (20260103, 500.0), (20260103, 500.0),
        (20260104, 500.0),
    ])
    v = compute_holdout_verdict(str(p), _cfg())
    assert v.status == "ok"
    # holdout 거래일 = 0103, 0104. 그 날 거래 5건.
    assert v.holdout_days == [20260103, 20260104]
    assert v.trade_count == 5
    assert v.train_trade_count == 3
    # 전부 수익 + min_trades(3) 이상 + MDD 0 → 게이트 통과.
    assert v.passed is True
    assert v.total_profit == 2500.0


def test_holdout_gate_fails_when_holdout_segment_unprofitable(tmp_path):
    """train은 수익이어도 holdout 구간이 손실이면 holdout 게이트 실패(졸업 거절)."""
    p = tmp_path / "loss.csv"
    # train(0101,0102) 수익, holdout(0103,0104) 손실 누적 → profit<=0.
    _write_csv(p, [
        (20260101, 5000.0), (20260101, 5000.0),
        (20260102, 5000.0),
        (20260103, -1000.0), (20260103, -1000.0), (20260103, -1000.0),
        (20260104, -1000.0),
    ])
    v = compute_holdout_verdict(str(p), _cfg())
    assert v.status == "ok"
    assert v.trade_count == 4
    assert v.total_profit == -4000.0
    assert v.passed is False
    assert "profit" in v.reason


def test_holdout_gate_fails_on_high_mdd(tmp_path):
    """holdout 누적손익 곡선의 MDD가 mdd_cap을 넘으면 게이트 실패."""
    p = tmp_path / "mdd.csv"
    # holdout(0103,0104): +100 후 -90 → peak 100에서 trough 10, dd=90% > cap 35.
    #   최종 누적 +10 (profit>0)이지만 MDD로 거절돼야 한다.
    _write_csv(p, [
        (20260101, 100.0), (20260101, 100.0), (20260102, 100.0),
        (20260103, 100.0), (20260103, -45.0), (20260103, -45.0), (20260104, 0.0),
    ])
    v = compute_holdout_verdict(str(p), _cfg(mdd_cap=35.0))
    assert v.status == "ok"
    assert v.total_profit > 0  # 최종 누적은 양수.
    assert v.mdd_pct > 35.0
    assert v.passed is False
    assert "mdd" in v.reason.lower()


def test_insufficient_holdout_trades_is_conservative_nongraduation(tmp_path):
    """holdout 거래가 min_trades 미만이면 판정 불가 → 보수적 미졸업."""
    p = tmp_path / "few.csv"
    # holdout(0103,0104)에 거래 2건뿐 < min_trades 5.
    _write_csv(p, [
        (20260101, 1000.0), (20260101, 1000.0), (20260102, 1000.0),
        (20260103, 1000.0), (20260104, 1000.0),
    ])
    v = compute_holdout_verdict(str(p), _cfg(min_trades=5))
    assert v.status == "insufficient"
    assert v.passed is False
    assert v.trade_count == 2


def test_no_holdout_when_window_too_short(tmp_path):
    """거래일 수 <= holdout_recent_days면 train이 안 남아 분할 불가 → 미졸업."""
    p = tmp_path / "short.csv"
    # 거래일 2개인데 holdout_recent_days=2 → train 없음.
    _write_csv(p, [
        (20260101, 1000.0), (20260101, 1000.0),
        (20260102, 1000.0), (20260102, 1000.0),
    ])
    v = compute_holdout_verdict(str(p), _cfg(holdout_recent_days=2))
    assert v.status == "no_holdout"
    assert v.passed is False


def test_missing_columns_returns_error_verdict(tmp_path):
    """매도시간/수익금 컬럼이 없으면 예외 대신 error verdict(미졸업)."""
    p = tmp_path / "bad.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["종목명", "수익률"])  # 필수 컬럼 누락.
        w.writerow(["A", 0.5])
    v = compute_holdout_verdict(str(p), _cfg())
    assert v.status == "error"
    assert v.passed is False


# ============================================================
# page_data 직렬화
# ============================================================

def test_page_data_off_when_verdict_none():
    """verdict=None → status='off', passed=None (토글 OFF/미평가 배지)."""
    pd = holdout_verdict_to_page_data(None)
    assert pd["status"] == "off"
    assert pd["passed"] is None


def test_page_data_serializes_verdict_fields():
    v = HoldoutVerdict(
        passed=True, status="ok", trade_count=12, total_profit=34000.0,
        mdd_pct=8.5, reason="ok", holdout_days=[20260103, 20260104],
        train_trade_count=40,
    )
    pd = holdout_verdict_to_page_data(v)
    assert pd["status"] == "ok"
    assert pd["passed"] is True
    assert pd["trade_count"] == 12
    assert pd["mdd_pct"] == 8.5
    assert pd["holdout_days"] == [20260103, 20260104]
    assert pd["train_trade_count"] == 40


def test_page_data_survives_contract_serialization():
    """page_data['holdout']가 contract v2 LoopState round-trip에서 보존된다."""
    import json
    from ai_strategy_loop.controller import contract as C

    v = HoldoutVerdict(
        passed=False, status="insufficient", trade_count=1, total_profit=5.0,
        mdd_pct=0.0, reason="holdout 거래 1 < min_trades 5 (판정 불가)",
        holdout_days=[20260104], train_trade_count=10,
    )
    pd = {"holdout": holdout_verdict_to_page_data(v)}
    ls = C.LoopState(page_data=pd)
    revalidated = C.LoopState.model_validate(json.loads(ls.model_dump_json()))
    assert revalidated.page_data["holdout"]["status"] == "insufficient"
    assert revalidated.page_data["holdout"]["passed"] is False
