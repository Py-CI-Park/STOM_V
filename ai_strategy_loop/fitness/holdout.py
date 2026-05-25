"""Holdout 날짜 분할 (RV2-4).

단일 train/holdout 분할 토글. 기본 OFF.

- OFF: holdout_* = None, train = 전체 윈도우 (루프는 전체 working 윈도우로 채점).
- ON : 윈도우 끝에서 최근 holdout_recent_days 만큼을 holdout으로 떼어 둔다.
       train = 나머지 앞부분. 졸업하려면 holdout에서도 gate를 통과해야 한다(점수는
       iteration에서 제외) — 단, gate 적용/점수 배선은 US-005 몫이고 여기서는
       분할 경계와 토글만 제공한다.

MVP 단순화: holdout 경계는 **달력일(calendar days)** 산술로 계산한다. 거래일
캘린더(moneytop trading-day list)를 끌어오면 충실하지만, 분할 토글 단위 테스트에
거래일 DB 의존을 들이는 비용이 커서 MVP에서는 달력일을 쓴다. 분할은 거래일 경계가
아니라 날짜 경계만 정의하므로(실제 trade 필터링은 백테스트 스코프가 처리) 달력일
근사로 충분하다. 더 높은 충실도가 필요하면 이후 단계에서 거래일 리스트로 교체한다.

날짜 표현: YYYYMMDD 정수 (BacktestConfig.start_date/end_date 및 LoopConfig.bt_*와 동일).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class HoldoutSplit:
    """train/holdout 날짜 경계 (모두 YYYYMMDD 정수).

    holdout 비활성(OFF) 시 holdout_start/holdout_end는 None이고
    train_start/train_end는 전체 입력 윈도우와 동일하다.
    """

    train_start: int
    train_end: int
    holdout_start: Optional[int]
    holdout_end: Optional[int]


def _to_date(yyyymmdd: int) -> date:
    s = int(yyyymmdd)
    return date(s // 10000, (s // 100) % 100, s % 100)


def _to_int(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def split_window(
    start_date: int,
    end_date: int,
    enabled: bool,
    holdout_recent_days: int,
) -> HoldoutSplit:
    """[start_date, end_date] 윈도우를 train/holdout으로 분할한다.

    enabled=False 이면 분할하지 않고 전체를 train으로 둔다.
    enabled=True 이면 끝에서 holdout_recent_days(달력일)를 holdout으로 떼어,
      - holdout = [end_date - (N-1)일, end_date]
      - train   = [start_date, holdout_start - 1일]
    holdout이 윈도우 전체를 삼키거나(N이 윈도우보다 큼) N<=0이면 분할이 무의미하므로
    OFF와 동일하게(전체 train) 처리한다 — gate 자체가 거절을 책임진다.
    """
    if not enabled or holdout_recent_days <= 0:
        return HoldoutSplit(
            train_start=int(start_date),
            train_end=int(end_date),
            holdout_start=None,
            holdout_end=None,
        )

    start_d = _to_date(start_date)
    end_d = _to_date(end_date)

    # holdout = 마지막 N일 (end 포함). N일이므로 시작은 end-(N-1).
    holdout_start_d = end_d - timedelta(days=holdout_recent_days - 1)

    # holdout이 윈도우 시작 이하로 내려가면(=전체를 삼킴) 분할 불가 -> 전체 train.
    if holdout_start_d <= start_d:
        return HoldoutSplit(
            train_start=int(start_date),
            train_end=int(end_date),
            holdout_start=None,
            holdout_end=None,
        )

    train_end_d = holdout_start_d - timedelta(days=1)

    return HoldoutSplit(
        train_start=_to_int(start_d),
        train_end=_to_int(train_end_d),
        holdout_start=_to_int(holdout_start_d),
        holdout_end=_to_int(end_d),
    )
