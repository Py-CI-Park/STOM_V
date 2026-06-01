"""백테스트 결과 CSV → 시계열(누적수익곡선·일별손익·낙폭) 파서 (O2).

백테 결과의 누적 수익곡선/일별손익/낙폭 시계열은 현재 거래 CSV 파일에만 있어
CSV가 지워지면 영구 소실된다(P1b 감사). 이 모듈은 **추가 백테 없이** 디스크에
이미 있는 per-trade 결과 CSV 하나를 읽어 그 시계열을 DB로 다운샘플 영속할 수
있는 순수 dict 구조로 변환한다(controller/state.record_equity_curve가 INSERT).

설계 원칙(불변식):
  - 엔진/하드게이트/backtest 무수정. 읽기 전용(이미 있는 CSV만 파싱).
  - 신규 파싱 로직 최소화 — 이미 검증된 fitness 프리미티브를 재사용한다:
      * fitness.holdout._read_holdout_rows  : (거래일, 수익금) 행 추출(utf-8-sig).
    낙폭은 누적수익(원)이 0을 교차하면 %가 발산하므로(엔진 equity-MDD%와 다른 척도),
    고점 대비 절대 반납액(원, ≥0)으로 영속한다. 엔진 MDD%는 generations.mdd에 이미 있다.
  - CSV가 없거나 파싱 실패/빈 행이면 빈 구조(daily=[])를 반환한다(무예외). 토글
    OFF / 파싱 실패가 루프를 막지 않도록(학습 보조 경로).

거래일 키: per-trade CSV의 '매도시간'(YYYYMMDDHHMMSS) 앞 8자리(YYYYMMDD).
  (_read_holdout_rows가 이 슬라이싱을 이미 수행해 (거래일, 수익금) 튜플을 준다.)

후속(O1 대시보드 BacktestDetailChart)가 이 같은 파서를 재사용한다.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def _parse_betting_to_krw(betting) -> Optional[float]:
    """bt_betting(종목당 배팅, 백만원 단위 문자열 '5'=500만원)을 원(KRW)으로 해석한다.

    config.bt_betting은 BacktestConfig.betting과 동일한 표현(백만원 단위)이다.
    예: '5' → 5,000,000원. 파싱 불가/0 이하면 None(=cum_pct 산출 생략).
    초기자본 베이스가 불확실하면 None을 돌려 cum_pct를 빼는 보수적 처리를 한다.
    """
    if betting is None:
        return None
    try:
        millions = float(str(betting).strip())
    except (TypeError, ValueError):
        return None
    if millions <= 0.0:
        return None
    return millions * 1_000_000.0


def _downsample_indices(n: int, limit: int) -> List[int]:
    """길이 n 시퀀스에서 균등 추림한 인덱스(마지막 보존)를 오름차순으로 돌려준다.

    n<=limit 또는 limit<=0이면 [0..n-1] 전체. 그 외에는 limit-1개를 [0, n-1]
    구간에서 균등 간격으로 고르고 마지막 인덱스(n-1)를 항상 포함한다(곡선 끝값
    보존). 중복 인덱스는 제거하고 정렬한다.
    """
    if n <= 0:
        return []
    if limit <= 0 or n <= limit:
        return list(range(n))
    # limit개를 [0, n-1]에 균등 배치(마지막은 항상 n-1). round로 가까운 인덱스 선택.
    picks = set()
    for k in range(limit):
        idx = round(k * (n - 1) / (limit - 1))
        picks.add(int(idx))
    picks.add(n - 1)
    return sorted(picks)


def parse_backtest_series(
    csv_path: str,
    *,
    betting=None,
    downsample: int = 400,
) -> Dict[str, object]:
    """per-trade 결과 CSV를 거래일 단위 시계열(daily/cumulative/drawdown/summary)로 변환한다.

    추가 백테 없이 디스크의 CSV 한 파일만 읽는다. 거래일(매도시간 앞 8자리)로
    groupby해 일별손익과 누적수익을 만들고, 누적곡선의 running-peak 낙폭률을 계산한다.

    Args:
        csv_path: per-trade 백테 결과 CSV 경로(매도시간/수익금 컬럼 보유, utf-8-sig).
        betting: 종목당 배팅(config.bt_betting; 백만원 단위 '5'=500만원). 주어지고
            파싱 가능하면 cum_pct(누적수익 / 초기자본 × 100)를 함께 산출한다. None이거나
            파싱 불가면 cum_pct는 None(생략)으로 둔다.
        downsample: 거래일 수가 이 값을 초과하면 균등 추림(마지막 보존)한다. <=0이면
            추림 없음.

    Returns:
        dict:
          {
            "daily": [{"date": int, "daily_pnl": float, "profit": float(이익만 +합),
                       "loss": float(손실만 -합), "net": float}, ...],   # 거래일 groupby
            "cumulative": [{"date": int, "cum_profit": float,
                            "cum_pct": float|None}, ...],                # 거래일 마지막 누적
            "drawdown": [{"date": int, "drawdown": float(원, ≥0)}, ...], # 고점 대비 반납액(원)
            "summary": {"trade_count": int, "final_profit": float,
                        "max_drawdown": float(원), "n_days": int},
          }
        CSV가 없거나 컬럼 누락/빈 행/파싱 실패면 빈 구조(daily=[]·summary 0)로 무예외 반환.
    """
    # 프리미티브 재사용: (거래일, 수익금) 행 추출.
    from ai_strategy_loop.fitness.holdout import _read_holdout_rows  # noqa: PLC0415

    empty: Dict[str, object] = {
        "daily": [],
        "cumulative": [],
        "drawdown": [],
        "summary": {
            "trade_count": 0,
            "final_profit": 0.0,
            "max_drawdown": 0.0,
            "n_days": 0,
        },
    }

    if not csv_path:
        return empty

    try:
        rows = _read_holdout_rows(csv_path)  # [(day:int, profit:float), ...] 거래 순서.
    except Exception:  # noqa: BLE001 - CSV 없음/컬럼 누락/IO 실패는 빈 구조로 흡수(무예외).
        return empty

    if not rows:
        return empty

    trade_count = len(rows)

    # 거래일 groupby: 등장 순서를 보존(거래일이 CSV에서 시간순이라 가정하되, 명시적
    #   순서 리스트로 정렬해 cum/drawdown 산출을 결정론적으로 만든다).
    day_order: List[int] = []
    by_day: Dict[int, Dict[str, float]] = {}
    for day, profit in rows:
        agg = by_day.get(day)
        if agg is None:
            agg = {"daily_pnl": 0.0, "profit": 0.0, "loss": 0.0}
            by_day[day] = agg
            day_order.append(day)
        agg["daily_pnl"] += profit
        if profit > 0.0:
            agg["profit"] += profit
        elif profit < 0.0:
            agg["loss"] += profit  # 손실은 음수 합(부호 보존).

    # 거래일을 오름차순으로 정렬해 누적/낙폭을 시간순으로 산출한다(결정론).
    sorted_days = sorted(day_order)

    betting_krw = _parse_betting_to_krw(betting)

    daily: List[Dict[str, float]] = []
    cumulative: List[Dict[str, object]] = []
    drawdown: List[Dict[str, float]] = []

    running = 0.0
    cum_series: List[float] = []  # 거래일 마지막 누적값(낙폭률 계산용).
    for day in sorted_days:
        agg = by_day[day]
        daily.append({
            "date": int(day),
            "daily_pnl": float(agg["daily_pnl"]),
            "profit": float(agg["profit"]),
            "loss": float(agg["loss"]),
            "net": float(agg["daily_pnl"]),  # net == daily_pnl(이익+손실 합), 명시 보존.
        })
        running += agg["daily_pnl"]
        cum_series.append(running)
        cum_pct = (running / betting_krw * 100.0) if betting_krw is not None else None
        cumulative.append({
            "date": int(day),
            "cum_profit": float(running),
            "cum_pct": (None if cum_pct is None else float(cum_pct)),
        })

    # drawdown: 누적이익 고점 대비 **절대 반납액(원, 항상 ≥0)**.
    #   누적수익(수익금합계, 원)은 0을 교차할 수 있어 '고점 대비 %'(=_equity_mdd_pct)는
    #   고점이 작을 때 발산한다(예: 고점 +5만 후 −10만 → 300%). 그건 엔진의 equity 기준
    #   MDD%와 다른 척도라 오도적이다. 그래서 여기선 고점 대비 절대 반납액(원)을 영속한다
    #   — 항상 ≥0, 발산 없음, '언제 얼마(원)를 토해냈나' 분석에 명확. 엔진 equity 기준
    #   MDD%(%)는 generations.mdd 스칼라에 이미 있다(여기서 중복/대체하지 않는다).
    peak = float("-inf")
    for day, cum in zip(sorted_days, cum_series):
        if cum > peak:
            peak = cum
        gb = (peak - cum) if peak != float("-inf") else 0.0
        drawdown.append({"date": int(day), "drawdown": float(max(0.0, gb))})

    # summary는 추림 전 전체 곡선 기준으로 산출한다(다운샘플은 표현용일 뿐).
    final_profit = float(cum_series[-1]) if cum_series else 0.0
    max_drawdown = max((d["drawdown"] for d in drawdown), default=0.0)  # 최대 반납액(원).
    n_days = len(sorted_days)

    # 거래일 수가 downsample을 초과하면 세 시계열을 동일 인덱스로 균등 추림(마지막 보존).
    keep = _downsample_indices(n_days, downsample)
    if len(keep) != n_days:
        daily = [daily[i] for i in keep]
        cumulative = [cumulative[i] for i in keep]
        drawdown = [drawdown[i] for i in keep]

    return {
        "daily": daily,
        "cumulative": cumulative,
        "drawdown": drawdown,
        "summary": {
            "trade_count": int(trade_count),
            "final_profit": final_profit,
            "max_drawdown": float(max_drawdown),
            "n_days": int(n_days),
        },
    }
