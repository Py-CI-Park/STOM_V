"""M11 (2026-06-12) — 레짐 분해 advisory (advisory 전용, 판정·게이트 미사용).

exit2 청산 구조가 2022 레짐에서 강하고 2026 레짐에서 죽는 현상처럼,
후보의 손익이 특정 시장 레짐에 편중됐는지를 자동 공시한다.
판정·선택기 로직과 완전히 분리된 순수 함수 모음이며,
대시보드(app.py) 연결은 리드가 수행한다.

레짐 2단계(active / contracted) 이유
  v0에서 3단계 이상을 도입하면 임계값이 늘어나 과세분화(over-labeling) 위험이
  생기고, 중앙값 1개로 사전선언 가능한 최소 규칙이 무너진다. 먼저 2단계로
  편중 존재 여부를 확인한 뒤, 필요 시 v1에서 임계를 추가한다.
"""
from __future__ import annotations

import statistics
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# 1. 집계
# ---------------------------------------------------------------------------

def monthly_aggregate(
    daily_metrics: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """일별 시장 지표 dict를 월(YYYYMM) 평균으로 집계한다.

    Args:
        daily_metrics: {YYYYMMDD: {metric_name: float, ...}, ...}

    Returns:
        {YYYYMM: {metric_name: float, ...}}  — 각 지표는 해당 월의 산술 평균.
        빈 입력은 빈 dict 반환.

    Example:
        >>> d = {"20220101": {"turnover": 100.0}, "20220115": {"turnover": 200.0}}
        >>> monthly_aggregate(d)
        {'202201': {'turnover': 150.0}}
    """
    buckets: Dict[str, Dict[str, list]] = {}
    for day_key, metrics in daily_metrics.items():
        month_key = str(day_key)[:6]  # 앞 6자리 = YYYYMM
        if month_key not in buckets:
            buckets[month_key] = {}
        for metric, value in metrics.items():
            buckets[month_key].setdefault(metric, []).append(float(value))

    return {
        month: {metric: statistics.mean(values) for metric, values in metric_map.items()}
        for month, metric_map in sorted(buckets.items())
    }


# ---------------------------------------------------------------------------
# 2. 레짐 라벨링
# ---------------------------------------------------------------------------

def label_regimes(
    monthly: Dict[str, Dict[str, float]],
    *,
    metric: str = "turnover",
    threshold: Optional[float] = None,
) -> Dict[str, str]:
    """월별 지표값을 2단계 레짐 라벨("active" / "contracted")로 변환한다.

    Args:
        monthly:   {YYYYMM: {metric_name: float, ...}}
        metric:    레짐 판단에 사용할 지표명 (기본: "turnover").
        threshold: None이면 전체 월의 해당 metric 중앙값을 임계로 사용.
                   명시하면 해당 값을 그대로 사용.

    Returns:
        {YYYYMM: "active" | "contracted"}
        — metric이 없는 월은 결과에서 제외(누락 은폐 방지 — 호출자가 확인 가능).

    v0 단순 2단계 이유:
        임계값을 늘리면 과세분화 위험이 생기고, 중앙값 1개로 사전선언 가능한
        최소 규칙이 무너진다. v1 이후 필요 시 추가한다.
    """
    values = {
        month: data[metric]
        for month, data in monthly.items()
        if metric in data
    }
    if not values:
        return {}

    cutoff: float
    if threshold is None:
        cutoff = statistics.median(list(values.values()))
    else:
        cutoff = float(threshold)

    return {
        month: "active" if val >= cutoff else "contracted"
        for month, val in sorted(values.items())
    }


# ---------------------------------------------------------------------------
# 3. 레짐별 손익 분해
# ---------------------------------------------------------------------------

def regime_breakdown(
    daily_pnl: Dict[str, float],
    regime_by_month: Dict[str, str],
) -> dict:
    """일별 손익을 레짐으로 귀속해 편중 지표를 반환한다.

    Args:
        daily_pnl:       {YYYYMMDD: pnl_float}
        regime_by_month: {YYYYMM: "active" | "contracted" | ...}

    Returns:
        {
          "active":      {"profit": float, "days": int, "months": set[str]},
          "contracted":  {"profit": float, "days": int, "months": set[str]},
          "unlabeled":   {"profit": float, "days": int, "months": set[str]},
          "concentration": float,   # 한 레짐 이익 비중(이익 합 기준, 0~1)
          "warning": str | None,    # 비중 > 0.8이면 경고 문자열, 아니면 None
        }

        - "unlabeled": regime_by_month에 라벨이 없는 월의 손익(누락 은폐 금지).
        - concentration: 전체 이익(양수 pnl 합) 중 가장 큰 레짐의 비중.
          이익 합이 0 이하면 0.0.
        - warning: 비중 > 0.8이면 "레짐 편중 — 한 레짐 의존 후보", 아니면 None.
    """
    buckets: Dict[str, Dict] = {}

    for day_key, pnl in daily_pnl.items():
        month_key = str(day_key)[:6]
        regime = regime_by_month.get(month_key, "unlabeled")
        if regime not in buckets:
            buckets[regime] = {"profit": 0.0, "days": 0, "months": set()}
        buckets[regime]["profit"] += float(pnl)
        buckets[regime]["days"] += 1
        buckets[regime]["months"].add(month_key)

    # 표준 키 보장 (결과 소비자가 KeyError 없이 접근 가능)
    for key in ("active", "contracted", "unlabeled"):
        if key not in buckets:
            buckets[key] = {"profit": 0.0, "days": 0, "months": set()}

    # concentration — 이익(양수 pnl 합) 기준
    regime_profits = {
        regime: data["profit"]
        for regime, data in buckets.items()
        if regime != "unlabeled"
    }
    total_positive = sum(p for p in regime_profits.values() if p > 0)
    if total_positive <= 0:
        concentration = 0.0
    else:
        max_positive = max((p for p in regime_profits.values() if p > 0), default=0.0)
        concentration = max_positive / total_positive

    warning: Optional[str] = None
    if concentration > 0.8:
        warning = "레짐 편중 — 한 레짐 의존 후보"

    return {
        **buckets,
        "concentration": round(concentration, 4),
        "warning": warning,
    }


# ---------------------------------------------------------------------------
# 4. moneytop DB 로더 (선택적, sqlite 커넥션 주입형)
# ---------------------------------------------------------------------------

def load_daily_turnover_from_moneytop(
    con,
    *,
    turnover_columns: list,
    table_name: str = "moneytop",
) -> Dict[str, float]:
    """moneytop sqlite 테이블에서 일별 거래대금 합계를 반환한다.

    Args:
        con:              sqlite3 커넥션 (주입형 — DB 직접 오픈 금지).
        turnover_columns: 합산할 컬럼명 목록. 하드코딩 금지 — 호출자가 지정.
        table_name:       대상 테이블명 (기본: "moneytop").

    Returns:
        {YYYYMMDD: float}  — 해당 날의 turnover_columns 합계.

    스키마 확인 예시 (docstring용, 실행하지 않음):
        cursor = con.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        # [index] 컬럼은 YYYYMMDDHHMMSS 타임스탬프 형식.
        # 앞 8자리로 일자 그룹핑 → 거래대금류 컬럼 합산.

    Note:
        [index] 컬럼 앞 8자리를 YYYYMMDD로 취급해 일자별로 그룹핑한다.
        turnover_columns에 없는 컬럼은 자동으로 무시된다.
    """
    cursor = con.execute(f"PRAGMA table_info({table_name})")  # noqa: S608
    available = {row[1] for row in cursor.fetchall()}

    valid_cols = [c for c in turnover_columns if c in available]
    if not valid_cols:
        return {}

    col_expr = " + ".join(f'COALESCE("{c}", 0)' for c in valid_cols)
    rows = con.execute(
        f'SELECT "[index]", {col_expr} FROM "{table_name}"'  # noqa: S608
    ).fetchall()

    daily: Dict[str, list] = {}
    for ts, val in rows:
        day_key = str(ts)[:8]
        daily.setdefault(day_key, []).append(float(val) if val is not None else 0.0)

    return {day: sum(vals) for day, vals in sorted(daily.items())}
