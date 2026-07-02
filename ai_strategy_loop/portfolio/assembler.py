"""포트폴리오 조립기 (T5.2) — 니치 후보 결합 분석 + 명예의 전당 상대 지표.

연구 레인 전용 advisory 도구다. 승격/export/게이트 흐름을 실행하지 않으며,
순수 함수만 제공한다(입력 불변 — 원본 dict/DataFrame 을 절대 변경하지 않는다).

입력 계약 (정찰 확정 사항):
  - 일별 손익 시계열: ``{YYYYMMDD(str|int): 일손익(float, 원)}``. per-trade
    한국어 컬럼 거래행(trade_ledger 정본: 매수시간 YYYYMMDDHHMM(SS) 앞 8자리
    → 거래일, 수익금 → 손익)에서 :func:`daily_pnl_from_trades` 로 파생 가능하다.
  - 시간밴드: seeds.lattice.TimeBand 와 동일 의미의 HHMMSS 반열림 구간
    ``[start, end)`` — mapping({start, end, label?}) 또는 2-원소 시퀀스.
  - 벤치마크: dashboard/reference_strategies.json (19 인간 우수 전략,
    portfolio_multi_position 측정계 산물) — 비교는
    measurement_frame.assert_hall_of_fame_comparable 경유 advisory 로만 한다.

정직성 규칙 (추측 금지):
  - 상관은 공통 거래일 교집합 기준. 교집합 < min_overlap_days(기본 20)면
    correlation=None + status='insufficient_overlap' 로 공시한다.
  - 상관 캡 초과 제외는 반드시 exclusions 레코드로 남긴다(조용한 탈락 금지).
  - 계산 불가 지표(MDD%, 일평균 거래 등)는 None + metric_notes 사유를 병기한다.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from ai_strategy_loop.fitness.measurement_frame import (
    FRAME_PORTFOLIO_MULTI_POSITION,
    annotate_frame,
    assert_hall_of_fame_comparable,
)

__all__ = [
    "PORTFOLIO_ASSEMBLER_SCHEMA_VERSION",
    "DEFAULT_MIN_OVERLAP_DAYS",
    "STATUS_OK",
    "STATUS_INSUFFICIENT_OVERLAP",
    "STATUS_ZERO_VARIANCE",
    "combine_candidates",
    "compare_to_benchmark",
    "daily_pnl_from_trades",
    "load_reference_strategies",
]

PORTFOLIO_ASSEMBLER_SCHEMA_VERSION = 1

# 거래행 정본 컬럼 (autopsy/trade_ledger.py 계약과 동일 의미 — 읽기 전용 재선언).
BUY_TIME_COLUMN = "매수시간"
PROFIT_COLUMN = "수익금"

# 상관 표본 하한 — 공통 거래일 교집합이 이보다 작으면 상관을 추측하지 않는다.
DEFAULT_MIN_OVERLAP_DAYS = 20

STATUS_OK = "ok"
STATUS_INSUFFICIENT_OVERLAP = "insufficient_overlap"
STATUS_ZERO_VARIANCE = "zero_variance"

_REFERENCE_FILENAME = "reference_strategies.json"
_DEFAULT_REFERENCE_PATH = (
    Path(__file__).resolve().parent.parent / "dashboard" / _REFERENCE_FILENAME
)


# ---------------------------------------------------------------------------
# 공통 헬퍼 (순수 함수)
# ---------------------------------------------------------------------------

def _finite_float(value: Any) -> Optional[float]:
    """유한 float 로 강제 변환한다(불가/비유한이면 None — 추측 금지)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalize_day(value: Any) -> Optional[str]:
    """일자 키를 YYYYMMDD 8자리 문자열로 정규화한다(불가면 None)."""
    if value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        value = int(value)
    text = str(value).strip()
    if len(text) != 8 or not text.isdigit():
        return None
    return text


def _iter_trade_rows(trades: Any) -> Iterable[Mapping[str, Any]]:
    """거래행 입력(DataFrame | Mapping 시퀀스)을 행 mapping 이터러블로 통일한다."""
    if trades is None:
        return []
    if hasattr(trades, "to_dict") and hasattr(trades, "columns"):
        return trades.to_dict(orient="records")  # pandas DataFrame (원본 불변)
    return trades


def daily_pnl_from_trades(trades: Any) -> Dict[str, Any]:
    """per-trade 한국어 컬럼 거래행에서 일별 손익 시계열과 거래 통계를 파생한다.

    매수시간(YYYYMMDDHHMM(SS)) 앞 8자리 → 거래일(YYYYMMDD), 수익금 → 손익.
    trade_ledger._derive_trade_dates 와 동일 의미의 파생이다(읽기 전용 재구현).

    Args:
        trades: pandas DataFrame 또는 행 mapping 시퀀스. 각 행에
            ``매수시간``/``수익금`` 컬럼이 있어야 집계에 포함된다.

    Returns:
        {
          "daily_pnl": {YYYYMMDD: 일손익 합(float)},
          "n_trades": 집계된 거래수, "n_wins": 수익금>0 거래수,
          "dropped_rows": 파싱 불가로 제외된 행수(정직 공시),
        }

    Raises:
        ValueError: 집계 가능한 행이 하나도 없을 때(빈 시계열 추측 금지).
    """
    daily: Dict[str, float] = {}
    n_trades = 0
    n_wins = 0
    dropped = 0
    for row in _iter_trade_rows(trades):
        if not isinstance(row, Mapping):
            dropped += 1
            continue
        buy_time = _finite_float(row.get(BUY_TIME_COLUMN))
        profit = _finite_float(row.get(PROFIT_COLUMN))
        day = None
        if buy_time is not None:
            text = str(int(buy_time))
            day = _normalize_day(text[:8]) if len(text) >= 8 else None
        if day is None or profit is None:
            dropped += 1
            continue
        daily[day] = daily.get(day, 0.0) + profit
        n_trades += 1
        if profit > 0:
            n_wins += 1
    if n_trades == 0:
        raise ValueError(
            "daily_pnl_from_trades: 집계 가능한 거래행이 없습니다 "
            f"(dropped_rows={dropped}) — 매수시간/수익금 컬럼을 확인하세요."
        )
    return {
        "daily_pnl": daily,
        "n_trades": n_trades,
        "n_wins": n_wins,
        "dropped_rows": dropped,
    }


def _mdd_money_from_daily(daily_values: Sequence[float]) -> float:
    """일별 손익 시퀀스의 누적 곡선 MDD(금액, ≥0)를 반환한다.

    누적 손익은 원금 기준선 0 에서 출발하므로 peak 초기값을 0 으로 둔다
    (첫날부터 손실이면 그 낙폭도 MDD 로 센다 — fitness.portfolio.mdd_money 의
    curve[0] 초기화와 의도적으로 다른, 손익 시계열 전용 규약).
    """
    peak = 0.0
    total = 0.0
    max_dd = 0.0
    for value in daily_values:
        total += value
        if total > peak:
            peak = total
        drawdown = peak - total
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Tuple[Optional[float], str]:
    """공통 표본 위 피어슨 상관 (값, status). 무분산이면 (None, zero_variance)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = 0.0
    var_x = 0.0
    var_y = 0.0
    for x, y in zip(xs, ys):
        dx = x - mean_x
        dy = y - mean_y
        cov += dx * dy
        var_x += dx * dx
        var_y += dy * dy
    if var_x <= 0.0 or var_y <= 0.0:
        return None, STATUS_ZERO_VARIANCE
    value = cov / math.sqrt(var_x * var_y)
    return max(-1.0, min(1.0, value)), STATUS_OK


# ---------------------------------------------------------------------------
# 후보 정규화
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Candidate:
    """정규화된 니치 후보(내부 표현 — 불변)."""

    name: str
    daily_pnl: Dict[str, float]
    meta: Dict[str, Any]
    n_trades: Optional[int]
    n_wins: Optional[int]
    band_seconds: Optional[Tuple[int, int]]
    band_label: Optional[str]
    total_profit: float = field(default=0.0)
    mdd_money: float = field(default=0.0)


def _hhmmss_to_seconds(value: Any) -> Optional[int]:
    """HHMMSS 정수/문자열을 자정 기준 초로 변환한다(불가면 None)."""
    number = _finite_float(value)
    if number is None or number < 0:
        return None
    raw = int(number)
    hour, minute, second = raw // 10000, (raw // 100) % 100, raw % 100
    if hour >= 24 or minute >= 60 or second >= 60:
        return None
    return hour * 3600 + minute * 60 + second


def _parse_time_band(meta: Mapping[str, Any]) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
    """meta.time_band 를 (초 구간, 라벨) 로 파싱한다(없거나 불량이면 (None, None))."""
    band = meta.get("time_band")
    label: Optional[str] = None
    if isinstance(band, Mapping):
        start, end = band.get("start"), band.get("end")
        raw_label = band.get("label")
        label = str(raw_label) if raw_label is not None else None
    elif isinstance(band, Sequence) and not isinstance(band, (str, bytes)) and len(band) == 2:
        start, end = band[0], band[1]
    else:
        return None, None
    start_sec = _hhmmss_to_seconds(start)
    end_sec = _hhmmss_to_seconds(end)
    if start_sec is None or end_sec is None or start_sec >= end_sec:
        return None, None
    return (start_sec, end_sec), label


def _normalize_candidate(raw: Mapping[str, Any]) -> _Candidate:
    """입력 후보 dict 하나를 검증/정규화한다(계약 위반은 ValueError)."""
    if not isinstance(raw, Mapping):
        raise ValueError(f"candidate 는 mapping 이어야 합니다: {type(raw).__name__}")
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ValueError("candidate.name 은 비어 있을 수 없습니다.")

    meta = dict(raw.get("meta") or {})
    n_trades: Optional[int] = None
    n_wins: Optional[int] = None

    if raw.get("daily_pnl") is not None:
        source = raw["daily_pnl"]
        if not isinstance(source, Mapping) or not source:
            raise ValueError(f"candidate[{name}].daily_pnl 은 비어있지 않은 mapping 이어야 합니다.")
        daily: Dict[str, float] = {}
        for key, value in source.items():
            day = _normalize_day(key)
            profit = _finite_float(value)
            if day is None or profit is None:
                raise ValueError(
                    f"candidate[{name}].daily_pnl 항목 불량: {key!r} -> {value!r} "
                    "(YYYYMMDD 키와 유한 손익만 허용)"
                )
            daily[day] = profit
        raw_trades = raw.get("n_trades")
        raw_wins = raw.get("n_wins")
        if raw_trades is not None and raw_wins is not None:
            n_trades, n_wins = int(raw_trades), int(raw_wins)
    elif raw.get("trades") is not None:
        derived = daily_pnl_from_trades(raw["trades"])
        daily = derived["daily_pnl"]
        n_trades = derived["n_trades"]
        n_wins = derived["n_wins"]
    else:
        raise ValueError(f"candidate[{name}] 은 daily_pnl 또는 trades 중 하나가 필요합니다.")

    band_seconds, band_label = _parse_time_band(meta)
    days_sorted = sorted(daily)
    values = [daily[d] for d in days_sorted]
    return _Candidate(
        name=name,
        daily_pnl=daily,
        meta=meta,
        n_trades=n_trades,
        n_wins=n_wins,
        band_seconds=band_seconds,
        band_label=band_label,
        total_profit=sum(values),
        mdd_money=_mdd_money_from_daily(values),
    )


def _normalize_candidates(candidates: Sequence[Mapping[str, Any]]) -> List[_Candidate]:
    if not candidates:
        raise ValueError("candidates 가 비어 있습니다 — 최소 1개 후보가 필요합니다.")
    normalized = [_normalize_candidate(raw) for raw in candidates]
    names = [c.name for c in normalized]
    if len(set(names)) != len(names):
        raise ValueError(f"candidate.name 중복 금지: {names}")
    return normalized


# ---------------------------------------------------------------------------
# 상관행렬 (공통 거래일 교집합 기준)
# ---------------------------------------------------------------------------

def _pairwise_correlations(
    cands: Sequence[_Candidate],
    min_overlap_days: int,
) -> Dict[str, Any]:
    """모든 후보쌍의 일별 손익 상관을 공통 거래일 교집합 기준으로 계산한다."""
    labels = [c.name for c in cands]
    n = len(cands)
    matrix: List[List[Optional[float]]] = [
        [1.0 if i == j else None for j in range(n)] for i in range(n)
    ]
    pairs: List[Dict[str, Any]] = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = cands[i], cands[j]
            common = sorted(set(a.daily_pnl) & set(b.daily_pnl))
            n_overlap = len(common)
            if n_overlap < min_overlap_days:
                corr: Optional[float] = None
                status = STATUS_INSUFFICIENT_OVERLAP
            else:
                corr, status = _pearson(
                    [a.daily_pnl[d] for d in common],
                    [b.daily_pnl[d] for d in common],
                )
            matrix[i][j] = matrix[j][i] = corr
            pairs.append({
                "a": a.name,
                "b": b.name,
                "correlation": None if corr is None else round(corr, 6),
                "n_overlap_days": n_overlap,
                "status": status,
            })
    return {
        "basis": "common_day_intersection",
        "min_overlap_days": min_overlap_days,
        "labels": labels,
        "matrix": [
            [None if v is None else round(v, 6) for v in row] for row in matrix
        ],
        "pairs": pairs,
    }


def _apply_correlation_cap(
    cands: Sequence[_Candidate],
    pairs: Sequence[Mapping[str, Any]],
    correlation_cap: float,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """상관 캡 초과 쌍에서 성과 낮은 쪽을 반복 제외한다(제외 사유 기록 필수).

    - 캡 판정은 부호 있는 상관 > cap (양의 상관 = 중복 리스크; 음의 상관은
      분산 효과라 제외하지 않는다).
    - insufficient_overlap / zero_variance 쌍은 절대 제외 근거로 쓰지 않는다
      (추측 금지 — 표본 부족으로 후보를 탈락시키지 않는다).
    - 성과 열위 = total_profit 낮은 쪽 → 동률이면 mdd_money 큰 쪽 → 동률이면
      이름 사전순 뒤쪽(결정론).
    """
    by_name = {c.name: c for c in cands}
    selected = [c.name for c in cands]
    exclusions: List[Dict[str, Any]] = []
    while True:
        active = set(selected)
        violating = [
            p for p in pairs
            if p["status"] == STATUS_OK
            and p["correlation"] is not None
            and p["correlation"] > correlation_cap
            and p["a"] in active
            and p["b"] in active
        ]
        if not violating:
            return selected, exclusions
        worst = max(violating, key=lambda p: (p["correlation"], p["a"], p["b"]))
        cand_a, cand_b = by_name[worst["a"]], by_name[worst["b"]]
        rank_a = (cand_a.total_profit, -cand_a.mdd_money, cand_a.name)
        rank_b = (cand_b.total_profit, -cand_b.mdd_money, cand_b.name)
        loser, kept = (cand_a, cand_b) if rank_a < rank_b else (cand_b, cand_a)
        selected = [name for name in selected if name != loser.name]
        exclusions.append({
            "name": loser.name,
            "reason": "correlation_cap_exceeded",
            "paired_with": kept.name,
            "kept": kept.name,
            "correlation": worst["correlation"],
            "correlation_cap": correlation_cap,
            "exclusion_rule": "lower_total_profit_then_higher_mdd",
            "loser_total_profit": round(loser.total_profit, 6),
            "kept_total_profit": round(kept.total_profit, 6),
        })


# ---------------------------------------------------------------------------
# 시간밴드 상보성
# ---------------------------------------------------------------------------

def _band_complementarity(cands: Sequence[_Candidate]) -> Dict[str, Any]:
    """선택 후보들의 시간밴드 상보성 점수 = 1 - 평균 쌍별 Jaccard 중첩도.

    1.0 = 완전 상보(중첩 없음), 0.0 = 전원 동일 밴드. 밴드 미표기 후보가
    있으면 score=None + missing 명단(추측 금지), 후보 1개면 단독 상태 공시.
    """
    missing = [c.name for c in cands if c.band_seconds is None]
    if missing:
        return {"score": None, "status": "missing_time_band", "missing": missing, "pairs": []}
    if len(cands) < 2:
        return {"score": None, "status": "single_candidate", "missing": [], "pairs": []}
    pair_rows: List[Dict[str, Any]] = []
    overlaps: List[float] = []
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a_start, a_end = cands[i].band_seconds  # type: ignore[misc]
            b_start, b_end = cands[j].band_seconds  # type: ignore[misc]
            inter = max(0, min(a_end, b_end) - max(a_start, b_start))
            union = (a_end - a_start) + (b_end - b_start) - inter
            ratio = inter / union if union > 0 else 0.0
            overlaps.append(ratio)
            pair_rows.append({
                "a": cands[i].name,
                "b": cands[j].name,
                "overlap_ratio": round(ratio, 6),
            })
    score = 1.0 - (sum(overlaps) / len(overlaps))
    return {
        "score": round(score, 6),
        "status": STATUS_OK,
        "missing": [],
        "pairs": pair_rows,
        "definition": "1 - mean pairwise Jaccard overlap of [start,end) HHMMSS bands",
    }


# ---------------------------------------------------------------------------
# 결합 곡선 → 포트폴리오 지표
# ---------------------------------------------------------------------------

def _resolve_weights(
    weights: Union[str, Mapping[str, float]],
    all_names: Sequence[str],
) -> Dict[str, float]:
    """가중 계약을 확정한다. 'equal' = 후보별 동일 명목 가중 1.0(합산).

    1/N 정규화는 금액 지표(profit/MDD 원)를 1/N 로 축소해 '동시 운용 합산'
    이라는 물리적 결합 의미를 왜곡하므로 쓰지 않는다(의도적 사전선언 —
    fitness.portfolio v0 의 1/N 분산 진단과는 목적이 다른 별도 규약).
    """
    if weights == "equal":
        return {name: 1.0 for name in all_names}
    if isinstance(weights, Mapping):
        resolved: Dict[str, float] = {}
        unknown = sorted(set(weights) - set(all_names))
        if unknown:
            raise ValueError(f"weights 에 미지 후보명이 있습니다: {unknown}")
        for name in all_names:
            value = _finite_float(weights.get(name))
            if value is None or value <= 0:
                raise ValueError(f"weights[{name}] 은 양의 유한 수여야 합니다: {weights.get(name)!r}")
            resolved[name] = value
        return resolved
    raise ValueError(f"weights 는 'equal' 또는 {{후보명: 가중치}} mapping 만 허용: {weights!r}")


def _portfolio_metrics(
    selected: Sequence[_Candidate],
    weight_map: Mapping[str, float],
    capital_base: Optional[float],
) -> Dict[str, Any]:
    """선택 후보 결합 일별 곡선에서 포트폴리오 지표를 계산한다(불가 지표는 정직 공시)."""
    all_days = sorted({day for cand in selected for day in cand.daily_pnl})
    daily_values = [
        sum(weight_map[c.name] * c.daily_pnl.get(day, 0.0) for c in selected)
        for day in all_days
    ]
    cum: List[float] = []
    running = 0.0
    for value in daily_values:
        running += value
        cum.append(running)
    total_profit = cum[-1] if cum else 0.0
    mdd_money = _mdd_money_from_daily(daily_values)
    n_days = len(all_days)
    positive_days = sum(1 for v in daily_values if v > 0)

    metric_notes: Dict[str, str] = {}
    mdd_pct: Optional[float] = None
    total_return_pct: Optional[float] = None
    if capital_base is not None:
        mdd_pct = mdd_money / capital_base * 100.0
        total_return_pct = total_profit / capital_base * 100.0
    else:
        metric_notes["mdd_pct"] = "missing_capital_base"
        metric_notes["total_return_pct"] = "missing_capital_base"

    daily_avg_trades: Optional[float] = None
    win_rate_pct: Optional[float] = None
    if all(c.n_trades is not None and c.n_wins is not None for c in selected):
        total_trades = sum(int(c.n_trades) for c in selected)  # type: ignore[arg-type]
        total_wins = sum(int(c.n_wins) for c in selected)  # type: ignore[arg-type]
        if n_days > 0:
            daily_avg_trades = total_trades / n_days
        if total_trades > 0:
            win_rate_pct = total_wins / total_trades * 100.0
        else:
            metric_notes["win_rate_pct"] = "no_trades"
    else:
        metric_notes["daily_avg_trades"] = "trade_stats_unavailable"
        metric_notes["win_rate_pct"] = "trade_stats_unavailable"

    metrics = {
        "names": [c.name for c in selected],
        "n_candidates": len(selected),
        "weights": {c.name: weight_map[c.name] for c in selected},
        "n_days": n_days,
        "total_profit": round(total_profit, 6),
        "mdd_money": round(mdd_money, 6),
        "mdd_pct": None if mdd_pct is None else round(mdd_pct, 6),
        "capital_base": capital_base,
        "total_return_pct": None if total_return_pct is None else round(total_return_pct, 6),
        "daily_avg_trades": None if daily_avg_trades is None else round(daily_avg_trades, 6),
        "win_rate_pct": None if win_rate_pct is None else round(win_rate_pct, 6),
        "positive_day_ratio": round(positive_days / n_days, 6) if n_days else None,
        "daily_curve": {
            "days": all_days,
            "daily": [round(v, 6) for v in daily_values],
            "cum": [round(v, 6) for v in cum],
        },
        "metric_notes": metric_notes,
    }
    return annotate_frame(metrics, FRAME_PORTFOLIO_MULTI_POSITION)


# ---------------------------------------------------------------------------
# 공개: 결합
# ---------------------------------------------------------------------------

def combine_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    correlation_cap: float = 0.5,
    weights: Union[str, Mapping[str, float]] = "equal",
    min_overlap_days: int = DEFAULT_MIN_OVERLAP_DAYS,
    capital_base: Optional[float] = None,
) -> Dict[str, Any]:
    """니치 후보들을 포트폴리오로 결합 분석한다(advisory 전용 — 실행 없음).

    Args:
        candidates: 후보 mapping 시퀀스. 각 후보는 ``name`` 필수 +
            ``daily_pnl``({YYYYMMDD: 손익}) 또는 ``trades``(한국어 컬럼 거래행)
            중 하나 필수. 선택: ``meta``(time_band/buy_sha256 등),
            ``n_trades``/``n_wins``(daily_pnl 직접 공급 시 거래 통계).
        correlation_cap: 부호 있는 쌍별 상관이 이 값을 초과하면 성과 낮은
            쪽을 제외한다(제외 사유는 exclusions 에 기록 — 조용한 탈락 금지).
        weights: 'equal'(후보별 동일 명목 가중 1.0 합산) 또는 {이름: 가중치}.
        min_overlap_days: 상관 계산 최소 공통 거래일 수. 미달 쌍은
            correlation=None + 'insufficient_overlap'(추측 금지, 제외 근거 불사용).
        capital_base: MDD%/수익률% 환산용 운영금(원). 미지정이면 % 지표는
            None + metric_notes 사유 공시.

    Returns:
        measurement_frame=portfolio_multi_position 라벨이 부여된 결과 dict:
        candidates(후보 요약)/correlation(행렬+쌍 status)/exclusions/
        selected/complementarity(시간밴드 상보성)/portfolio(결합 지표).

    Raises:
        ValueError: 입력 계약 위반(빈 후보, 이름 중복, 시계열 불량, 가중 불량 등).
    """
    if capital_base is not None:
        capital_base = _finite_float(capital_base)
        if capital_base is None or capital_base <= 0:
            raise ValueError("capital_base 는 양의 유한 수여야 합니다.")
    cap = _finite_float(correlation_cap)
    if cap is None:
        raise ValueError(f"correlation_cap 이 유한 수가 아닙니다: {correlation_cap!r}")
    if min_overlap_days < 2:
        raise ValueError("min_overlap_days 는 2 이상이어야 합니다.")

    cands = _normalize_candidates(candidates)
    all_names = [c.name for c in cands]
    weight_map = _resolve_weights(weights, all_names)

    correlation = _pairwise_correlations(cands, min_overlap_days)
    selected_names, exclusions = _apply_correlation_cap(cands, correlation["pairs"], cap)
    selected = [c for c in cands if c.name in set(selected_names)]

    result = {
        "schema_version": PORTFOLIO_ASSEMBLER_SCHEMA_VERSION,
        "authority": "advisory_only",
        "inputs": {
            "correlation_cap": cap,
            "weights": "equal" if weights == "equal" else dict(weights),
            "min_overlap_days": min_overlap_days,
            "capital_base": capital_base,
            "n_candidates": len(cands),
        },
        "candidates": [
            {
                "name": c.name,
                "n_days": len(c.daily_pnl),
                "total_profit": round(c.total_profit, 6),
                "mdd_money": round(c.mdd_money, 6),
                "n_trades": c.n_trades,
                "n_wins": c.n_wins,
                "time_band": c.band_label
                if c.band_label is not None
                else (list(c.band_seconds) if c.band_seconds else None),
                "buy_sha256": c.meta.get("buy_sha256"),
            }
            for c in cands
        ],
        "correlation": correlation,
        "exclusions": exclusions,
        "selected": [c.name for c in selected],
        "complementarity": _band_complementarity(selected),
        "portfolio": _portfolio_metrics(selected, weight_map, capital_base),
    }
    return annotate_frame(result, FRAME_PORTFOLIO_MULTI_POSITION)


# ---------------------------------------------------------------------------
# 공개: 명예의 전당 벤치마크 비교
# ---------------------------------------------------------------------------

def load_reference_strategies(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """reference_strategies.json (19 인간 우수 전략)을 로드한다.

    Raises:
        FileNotFoundError: 파일이 없을 때(정직 에러 — 빈 벤치마크 추측 금지).
        ValueError: strategies 목록이 없거나 비어 있을 때.
    """
    target = Path(path) if path is not None else _DEFAULT_REFERENCE_PATH
    if not target.is_file():
        raise FileNotFoundError(
            f"reference_strategies.json 없음: {target} — 명예의 전당 벤치마크 파일이 필요합니다."
        )
    with open(target, encoding="utf-8") as handle:
        payload = json.load(handle)
    strategies = payload.get("strategies") if isinstance(payload, Mapping) else None
    if not isinstance(strategies, list) or not strategies:
        raise ValueError(f"reference_strategies.json 에 strategies 목록이 없습니다: {target}")
    return dict(payload)


def _safe_ratio(numerator: Any, denominator: Any) -> Optional[float]:
    """둘 다 유한하고 분모≠0 일 때만 비율(아니면 None — 추측 금지)."""
    num = _finite_float(numerator)
    den = _finite_float(denominator)
    if num is None or den is None or den == 0.0:
        return None
    return num / den


def _benchmark_row(portfolio: Mapping[str, Any], reference: Mapping[str, Any]) -> Dict[str, Any]:
    """단일 벤치마크 전략 대비 상대 지표 한 행을 만든다(불가 지표는 missing 공시)."""
    port_return = portfolio.get("total_return_pct")
    port_mdd_pct = portfolio.get("mdd_pct")
    ref_return = reference.get("total_return_pct")
    ref_mdd_pct = reference.get("mdd_pct")

    profit_multiple_krw = _safe_ratio(portfolio.get("total_profit"), reference.get("profit_krw"))
    return_multiple = _safe_ratio(port_return, ref_return)
    mdd_pct_ratio = _safe_ratio(port_mdd_pct, ref_mdd_pct)
    port_tpi = _safe_ratio(port_return, port_mdd_pct)
    ref_tpi = _safe_ratio(ref_return, ref_mdd_pct)
    tpi_like_ratio = _safe_ratio(port_tpi, ref_tpi)

    row = {
        "reference_id": reference.get("id"),
        "profit_multiple_krw": profit_multiple_krw,
        "return_multiple": return_multiple,
        "mdd_pct_ratio": mdd_pct_ratio,
        "portfolio_return_per_mdd": port_tpi,
        "reference_return_per_mdd": ref_tpi,
        "tpi_like_ratio": tpi_like_ratio,
        "daily_avg_trades_ratio": _safe_ratio(
            portfolio.get("daily_avg_trades"), reference.get("daily_avg_trades")
        ),
        "win_rate_ratio": _safe_ratio(
            portfolio.get("win_rate_pct"), reference.get("win_rate_pct")
        ),
    }
    row["missing_inputs"] = sorted(
        key for key, value in row.items() if key != "reference_id" and value is None
    )
    for key, value in list(row.items()):
        if isinstance(value, float):
            row[key] = round(value, 6)
    return row


def compare_to_benchmark(
    portfolio_metrics: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> Dict[str, Any]:
    """포트폴리오 지표를 명예의 전당 벤치마크와 advisory 비교한다.

    measurement_frame.assert_hall_of_fame_comparable 판정을 반드시 경유하며,
    프레임 경고는 예외 없이 결과의 ``frame_warning`` 으로 전파한다(advisory —
    비교 자체를 막지 않되 경고를 병기한다).

    Args:
        portfolio_metrics: combine_candidates 결과의 ``portfolio`` dict
            (measurement_frame 라벨 포함 권장 — 없으면 경고 전파).
        reference: load_reference_strategies 결과(strategies 목록 포함) 또는
            단일 벤치마크 전략 dict.

    Returns:
        {schema_version, authority, frame_warning, reference_count, rows,
         summary(중앙값 배율)} — 계산 불가 지표는 행별 missing_inputs 로 공시.

    Raises:
        ValueError: reference 가 mapping 이 아니거나 비교 가능한 전략이 없을 때.
    """
    if not isinstance(reference, Mapping):
        raise ValueError(f"reference 는 mapping 이어야 합니다: {type(reference).__name__}")
    frame_warning = assert_hall_of_fame_comparable(portfolio_metrics)

    raw_strategies = reference.get("strategies")
    if isinstance(raw_strategies, list):
        strategies = [row for row in raw_strategies if isinstance(row, Mapping)]
    else:
        strategies = [reference]
    if not strategies:
        raise ValueError("reference 에 비교 가능한 전략이 없습니다.")

    rows = [_benchmark_row(portfolio_metrics, ref_row) for ref_row in strategies]

    def _median(key: str) -> Optional[float]:
        values = sorted(v for v in (row.get(key) for row in rows) if v is not None)
        if not values:
            return None
        mid = len(values) // 2
        if len(values) % 2 == 1:
            return round(values[mid], 6)
        return round((values[mid - 1] + values[mid]) / 2.0, 6)

    return {
        "schema_version": PORTFOLIO_ASSEMBLER_SCHEMA_VERSION,
        "authority": "advisory_only",
        "frame_warning": frame_warning,
        "reference_kind": (reference.get("_meta") or {}).get("kind")
        if isinstance(reference.get("_meta"), Mapping)
        else None,
        "reference_count": len(rows),
        "rows": rows,
        "summary": {
            "median_profit_multiple_krw": _median("profit_multiple_krw"),
            "median_return_multiple": _median("return_multiple"),
            "median_mdd_pct_ratio": _median("mdd_pct_ratio"),
            "median_tpi_like_ratio": _median("tpi_like_ratio"),
        },
    }
