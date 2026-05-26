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

P5/M5 (graduation holdout):
  추가 백테 없이 winner(졸업) 후보의 결과 CSV를 거래일로 분할해 holdout 구간에서도
  하드 게이트를 통과하는지 검사한다(compute_holdout_verdict). 전체유니버스 백테 1회의
  CSV에 train+holdout 거래가 모두 들어있으므로, CSV의 매도시간(거래일)으로 슬라이스해
  holdout 메트릭을 자기완결적으로 재구성한다.

  NOTE(후속): WFO(cli/wfo.py) 기반 walk-forward OOS 검증은 이번 P5 범위에서 제외한다.
  WFO가 loop_runs.db winner에 도는지 legacy backtest_history.db 경로인지 DB 경계가
  불확실하기 때문이다(M5와 동일한 DB 경계 질문). holdout 졸업검사는 그 경계와 무관하게
  결과 CSV만으로 동작한다. WFO OOS 배선은 DB 경계 확인 후 후속 작업으로 남긴다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


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


# =====================================================================
# 결과 CSV 거래일 분할 → holdout 졸업검사 (P5/M5).
# =====================================================================
# 결과 CSV 컬럼명 (backtest/back_static.py 결과 헤더와 동일).
#   - 매도시간: 거래 청산 시각 'YYYYMMDDHHMM'. 앞 8자리가 거래일(YYYYMMDD).
#               이 컬럼으로 거래를 거래일 기준 train/holdout으로 가른다.
#   - 수익금  : 거래당 실현 손익(원). holdout 슬라이스의 누적곡선/총수익을
#               이 컬럼만으로 재구성한다(수익금합계는 전체 누적이라 슬라이스엔 부적합).
_SELL_TIME_COLUMN = "매도시간"
_PROFIT_COLUMN = "수익금"


@dataclass
class HoldoutVerdict:
    """holdout 졸업검사 1회 결과.

    추가 백테 없이 기존 결과 CSV를 거래일로 분할해 holdout 구간만으로 게이트를
    판정한 결과다. winner(졸업) 후보가 train뿐 아니라 holdout에서도 게이트를
    통과했는지를 나타낸다.

    status:
      - 'ok'             : holdout 거래로 게이트 판정을 수행했다(passed 의미 있음).
      - 'insufficient'   : holdout 거래가 부족(min_trades 미만)해 판정 불가 →
                           보수적으로 passed=False(미졸업). winner 갱신을 막는다.
      - 'no_holdout'     : 윈도우가 너무 짧거나 holdout 일자가 없어 분할 불가 →
                           passed=False(미졸업). 토글 ON인데 holdout이 없으면
                           졸업 근거가 없으므로 보수적으로 막는다.
      - 'error'          : CSV 파싱/컬럼 누락 등 → passed=False.

    page_data(LIVE)와 winner 배선(loop.py) 양쪽에서 쓰인다.
    """

    passed: bool
    status: str
    trade_count: int            # holdout 구간 거래 수.
    total_profit: float         # holdout 구간 총 실현 손익(원).
    mdd_pct: float              # holdout 누적손익 곡선의 최대낙폭률(%, 양수).
    reason: str                 # 게이트 판정 사유(통과 시 "ok").
    holdout_days: List[int] = field(default_factory=list)  # holdout 거래일(YYYYMMDD).
    train_trade_count: int = 0  # 참고: train 구간 거래 수.


def _equity_mdd_pct(equity: List[float]) -> float:
    """누적손익 곡선의 최대낙폭률(%, 양수)을 peak 기준으로 계산한다.

    엔진의 계좌 MDD(필요자금 기준)는 슬라이스만으로 복원할 수 없으므로, holdout
    게이트는 **누적 실현손익 곡선의 peak-to-trough 낙폭**을 % 로 쓴다(자기완결).
    peak가 0/음수일 때(아직 이익 고점이 없음)는 0으로 둔다 — 분모가 없어 비율을
    정의할 수 없고, '이익 고점 대비 반납'이라는 MDD 의미상 보수적으로 0이 맞다.
    """
    peak = float("-inf")
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        if peak > 0.0:
            dd = (peak - v) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _read_holdout_rows(csv_path: str):
    """결과 CSV를 읽어 (거래일, 수익금) 튜플 리스트를 거래 순서대로 돌려준다.

    매도시간/수익금 둘 중 하나라도 비거나 파싱 불가한 행은 건너뛴다. 컬럼이 아예
    없으면 KeyError. 인코딩은 utf-8-sig (BOM 가능).
    """
    rows: List = []  # (day:int, profit:float)
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        if _SELL_TIME_COLUMN not in fields or _PROFIT_COLUMN not in fields:
            raise KeyError(
                f"CSV에 '{_SELL_TIME_COLUMN}'/'{_PROFIT_COLUMN}' 컬럼이 없습니다: {csv_path}"
            )
        for row in reader:
            raw_t = str(row.get(_SELL_TIME_COLUMN, "") or "").strip()
            raw_p = row.get(_PROFIT_COLUMN, "")
            if len(raw_t) < 8 or raw_p is None or str(raw_p).strip() == "":
                continue
            try:
                day = int(raw_t[:8])
                profit = float(raw_p)
            except (ValueError, TypeError):
                continue
            rows.append((day, profit))
    return rows


def compute_holdout_verdict(csv_path: str, config) -> HoldoutVerdict:
    """결과 CSV를 거래일로 train/holdout 분할해 holdout 게이트를 판정한다 (P5/M5).

    **추가 백테 없이** 전체유니버스 백테 1회의 CSV(train+holdout 거래가 다 들어있음)
    를 거래일 기준으로 쪼갠다. holdout = 윈도우의 **최근 holdout_recent_days 거래일**
    (달력일이 아니라 CSV에 실제 등장한 distinct 거래일을 센다 — 거래가 없는 날은
    holdout 일수에서 빠지므로 거래일 근사가 더 정확하다).

    holdout 구간 거래만으로 메트릭(거래수/총손익/누적손익 MDD)을 재구성해
    compute_fitness 와 동일한 하드 게이트(trade_count>=min_trades AND mdd<=mdd_cap
    AND profit>0)로 판정한다.

    Args:
        csv_path: 백테스트 결과 CSV(거래당 1행, 매도시간/수익금 컬럼 보유).
        config: LoopConfig (holdout_recent_days, min_trades, mdd_cap 사용).

    Returns:
        HoldoutVerdict. CSV/데이터 문제는 예외가 아니라 status 로 표현하고
        passed=False(보수적 미졸업)로 둔다.
    """
    # score 모듈 게이트를 재사용해 train/holdout 판정 기준을 완전히 일치시킨다.
    from ai_strategy_loop.fitness.score import compute_fitness  # noqa: PLC0415

    holdout_days_n = int(getattr(config, "holdout_recent_days", 30) or 0)
    min_trades = int(getattr(config, "min_trades", 0) or 0)

    try:
        rows = _read_holdout_rows(csv_path)
    except Exception as exc:  # noqa: BLE001 - CSV 문제는 미졸업으로 흡수.
        return HoldoutVerdict(
            passed=False, status="error", trade_count=0, total_profit=0.0,
            mdd_pct=0.0, reason=f"holdout CSV 분할 실패: {exc}",
        )

    if not rows or holdout_days_n <= 0:
        # 거래가 없거나 holdout 일수가 0 이하 → 분할 무의미. 보수적 미졸업.
        return HoldoutVerdict(
            passed=False, status="no_holdout", trade_count=0, total_profit=0.0,
            mdd_pct=0.0, reason="holdout 분할 불가(거래 없음 또는 holdout_recent_days<=0)",
        )

    # 윈도우에 등장한 distinct 거래일 → 최근 N개를 holdout 일자로 잡는다.
    distinct_days = sorted({d for d, _ in rows})
    # holdout이 윈도우 전체를 삼키면(train이 남지 않으면) 분할 무의미 → 미졸업.
    if len(distinct_days) <= holdout_days_n:
        return HoldoutVerdict(
            passed=False, status="no_holdout",
            trade_count=0, total_profit=0.0, mdd_pct=0.0,
            reason=(
                f"holdout 분할 불가: 거래일 {len(distinct_days)}개 <= "
                f"holdout_recent_days {holdout_days_n} (train 구간 없음)"
            ),
        )

    holdout_day_set = set(distinct_days[-holdout_days_n:])
    holdout_profits = [p for d, p in rows if d in holdout_day_set]
    train_count = len(rows) - len(holdout_profits)

    # holdout 누적 실현손익 곡선(슬라이스 자체 cumsum) + 총손익.
    equity: List[float] = []
    running = 0.0
    for p in holdout_profits:
        running += p
        equity.append(running)
    total_profit = running
    trade_count = len(holdout_profits)

    sorted_holdout_days = sorted(holdout_day_set)

    # holdout 거래가 min_trades 미만이면 통계가 빈약해 신뢰할 수 없다 →
    #   보수적으로 미졸업(졸업검사 통과시키지 않는다). best=graded는 호출부에서
    #   그대로 두므로 진행 자체는 막지 않는다.
    if trade_count < max(min_trades, 1):
        return HoldoutVerdict(
            passed=False, status="insufficient",
            trade_count=trade_count, total_profit=total_profit,
            mdd_pct=_equity_mdd_pct(equity),
            reason=f"holdout 거래 {trade_count} < min_trades {min_trades} (판정 불가)",
            holdout_days=sorted_holdout_days, train_trade_count=train_count,
        )

    mdd_pct = _equity_mdd_pct(equity)
    holdout_metrics = {
        "cagr": 0.0,  # 슬라이스 CAGR은 게이트에 쓰지 않는다(게이트는 거래수/MDD/손익).
        "mdd_pct": mdd_pct,
        "trade_count": trade_count,
        "total_profit_krw": total_profit,
    }
    # train 게이트와 동일한 compute_fitness 게이트로 holdout을 판정한다.
    fit = compute_fitness(holdout_metrics, equity, config)
    return HoldoutVerdict(
        passed=bool(fit.gate_passed), status="ok",
        trade_count=trade_count, total_profit=total_profit, mdd_pct=mdd_pct,
        reason=fit.reason,
        holdout_days=sorted_holdout_days, train_trade_count=train_count,
    )


def holdout_verdict_to_page_data(verdict: Optional["HoldoutVerdict"]) -> dict:
    """HoldoutVerdict를 LIVE page_data['holdout'] 직렬화 dict로 변환한다.

    None이면 토글 OFF/미평가를 의미하는 status='off' 를 돌려준다(프론트가 배지를
    숨기거나 'holdout OFF'로 표시). 모든 값은 JSON 직렬화 가능한 원시형이다.
    """
    if verdict is None:
        return {"status": "off", "passed": None}
    return {
        "status": verdict.status,
        "passed": verdict.passed,
        "trade_count": verdict.trade_count,
        "total_profit": verdict.total_profit,
        "mdd_pct": verdict.mdd_pct,
        "reason": verdict.reason,
        "holdout_days": list(verdict.holdout_days),
        "train_trade_count": verdict.train_trade_count,
    }
