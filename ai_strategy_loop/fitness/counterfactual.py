"""반사실(counterfactual) 필터 분석 — 백테스트 0회 가설 검증 (R2, 2026-06-11).

이미 생성된 per-trade CSV에서 "진입 조건을 추가로 **강화**했다면 어떤 거래가 남았고
손익이 어땠나"를 직접 계산한다. 강화 후 남는 거래는 원 거래의 부분집합이므로 추가
백테스트 없이 정확하다(완화 방향은 새 거래를 알 수 없어 불가 — 백테 필요).

실증(2026-06-11, 시드 train 307건, docs/update_log/2026-06-11_analysis_feedback_process_review.md §4):
'시가총액<=2100' 상한 = 거래 20% 감소·총손익 106%(잘린 62건 순손실 -512,238)·
2025 쇠퇴 구간 +38만→+167만(4.4배). '회전율>=5'(총손익 44%)는 수 초에 기각.
탐색 단가를 백테/LLM 세대 단위에서 CSV 연산 단위로 낮추는 것이 목적이다.

정직성 경계: 같은 데이터에서 임계를 뽑아 같은 데이터에 적용한 **인샘플 advisory**다.
채택 후보는 반드시 기존 규율(스모크→train→동결→고정 OOS)로 검증한다.
분석 전용 — 엔진/하드게이트/스코어/winner/생성 hot path에 일절 관여하지 않는다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

import pandas as pd

_OUTCOME_PCT = "수익률"
_OUTCOME_KRW = "수익금"
_BUYTIME = "매수시간"

# 제안 생성 시 후보 임계로 쓸 승자 분위수(보수→공격 순).
_TIGHTEN_OPS = {True: ">=", False: "<="}  # smd>0(승자가 큼) → 하한, smd<0 → 상한.


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """단일 강화 필터: `feature op threshold` (op는 '>=' 또는 '<=')."""

    feature: str
    op: str
    threshold: float

    def as_text(self) -> str:
        return f"{self.feature} {self.op} {self.threshold:,.4g}"


@dataclass(frozen=True, slots=True)
class YearSlice:
    year: str
    base_trades: int
    base_profit: float
    kept_trades: int
    kept_profit: float


@dataclass(frozen=True, slots=True)
class CounterfactualResult:
    filters: tuple
    base_trades: int
    base_profit: float
    base_win_rate: float
    kept_trades: int
    kept_profit: float
    kept_win_rate: float
    cut_trades: int
    cut_net_profit: float
    profit_ratio: float  # kept_profit / base_profit (base<=0이면 0)
    yearly: tuple = field(default_factory=tuple)


def _load(df_or_csv: Union[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    try:
        if isinstance(df_or_csv, pd.DataFrame):
            df = df_or_csv
        else:
            df = pd.read_csv(df_or_csv, encoding="utf-8-sig")
        if _OUTCOME_PCT not in df.columns or _OUTCOME_KRW not in df.columns:
            return None
        return df
    except Exception:  # noqa: BLE001 - 분석 전용: 어떤 실패도 None.
        return None


def _mask(df: pd.DataFrame, spec: FilterSpec) -> Optional[pd.Series]:
    if spec.feature not in df.columns or spec.op not in (">=", "<="):
        return None
    vals = pd.to_numeric(df[spec.feature], errors="coerce")
    if spec.op == ">=":
        return vals >= spec.threshold
    return vals <= spec.threshold


def evaluate_filters(
    df_or_csv: Union[str, pd.DataFrame],
    filters: Sequence[FilterSpec],
) -> Optional[CounterfactualResult]:
    """필터(AND 결합)를 반사실 적용해 잔존/절단 거래의 손익을 계산한다.

    Returns:
        CounterfactualResult 또는 입력/컬럼 문제 시 None (graceful).
    """
    df = _load(df_or_csv)
    if df is None or len(df) == 0 or not filters:
        return None

    combined = pd.Series(True, index=df.index)
    for spec in filters:
        m = _mask(df, spec)
        if m is None:
            return None
        combined &= m.fillna(False)

    kept = df[combined]
    cut = df[~combined]
    base_profit = float(df[_OUTCOME_KRW].sum())
    kept_profit = float(kept[_OUTCOME_KRW].sum())

    yearly: List[YearSlice] = []
    if _BUYTIME in df.columns:
        years = df[_BUYTIME].astype(str).str[:4]
        for year in sorted(years.unique()):
            in_year = years == year
            yearly.append(YearSlice(
                year=str(year),
                base_trades=int(in_year.sum()),
                base_profit=float(df[in_year][_OUTCOME_KRW].sum()),
                kept_trades=int((in_year & combined).sum()),
                kept_profit=float(df[in_year & combined][_OUTCOME_KRW].sum()),
            ))

    return CounterfactualResult(
        filters=tuple(filters),
        base_trades=int(len(df)),
        base_profit=base_profit,
        base_win_rate=float((df[_OUTCOME_PCT] > 0).mean()),
        kept_trades=int(len(kept)),
        kept_profit=kept_profit,
        kept_win_rate=float((kept[_OUTCOME_PCT] > 0).mean()) if len(kept) else 0.0,
        cut_trades=int(len(cut)),
        cut_net_profit=float(cut[_OUTCOME_KRW].sum()),
        profit_ratio=(kept_profit / base_profit) if base_profit > 0 else 0.0,
        yearly=tuple(yearly),
    )


def suggest_filters(
    csv_path: str,
    *,
    top_k: int = 3,
    min_profit_ratio: float = 1.0,
    min_kept_trades: int = 20,
    max_candidates_per_feature: int = 2,
) -> List[Dict[str, Any]]:
    """부검 변별 변수 + 승자 분위수로 강화 필터 후보를 만들고 반사실 평가로 선별한다.

    방향 인지: Cohen's d(smd)>0(승자가 큼)이면 하한(>=, 승자 Q25→Q50),
    smd<0이면 상한(<=, 승자 Q75→Q50). **총손익이 깎이지 않는(min_profit_ratio 이상)**
    필터만 채택 — 2026-06-11 실증에서 승률만 보고 고르면 순흑자 거래를 자르는
    함정(전일동시간비>=900: 승률↑·손익 72%)이 확인됐기 때문이다.

    Returns:
        JSON-safe dict 리스트(손익 비율 내림차순, 최대 top_k). 실패/부족 시 [].
    """
    try:
        from ai_strategy_loop.autopsy.analyze import analyze_trades  # noqa: PLC0415

        result = analyze_trades(csv_path)
        if result.status != "ok" or not result.discriminators:
            return []
        df = _load(csv_path)
        if df is None:
            return []

        suggestions: List[Dict[str, Any]] = []
        for d in result.discriminators[:6]:
            lower = d.std_mean_diff > 0
            op = _TIGHTEN_OPS[lower]
            qs = [d.win_q25, d.win_q50] if lower else [d.win_q75, d.win_q50]
            seen = set()
            count = 0
            for q in qs:
                if q is None or q in seen or count >= max_candidates_per_feature:
                    continue
                seen.add(q)
                count += 1
                spec = FilterSpec(feature=d.column, op=op, threshold=float(q))
                cf = evaluate_filters(df, [spec])
                if cf is None:
                    continue
                if cf.profit_ratio < min_profit_ratio or cf.kept_trades < min_kept_trades:
                    continue
                recent = cf.yearly[-1] if cf.yearly else None
                suggestions.append({
                    "filter": spec.as_text(),
                    "feature": d.column,
                    "op": op,
                    "threshold": float(q),
                    "smd": float(d.std_mean_diff),
                    "base_trades": cf.base_trades,
                    "kept_trades": cf.kept_trades,
                    "profit_ratio": round(cf.profit_ratio, 4),
                    "base_profit": cf.base_profit,
                    "kept_profit": cf.kept_profit,
                    "cut_net_profit": cf.cut_net_profit,
                    "kept_win_rate": round(cf.kept_win_rate, 4),
                    "base_win_rate": round(cf.base_win_rate, 4),
                    "recent_year": (
                        {
                            "year": recent.year,
                            "base_profit": recent.base_profit,
                            "kept_profit": recent.kept_profit,
                        } if recent is not None else None
                    ),
                })
        suggestions.sort(key=lambda s: (-s["profit_ratio"], -s["kept_profit"]))
        return suggestions[:top_k]
    except Exception:  # noqa: BLE001 - 분석 전용: 어떤 실패도 빈 리스트.
        return []


def feedback_lines(suggestions: Sequence[Dict[str, Any]], *, max_lines: int = 3) -> List[str]:
    """검증된 필터 제안을 다음 세대 매수 프롬프트용 NL 라인으로 변환한다(R2②, R5 통합).

    각 라인에 손익 영향(반사실)과 승률 근거를 함께 담아 "숫자 있는" 신호를 만든다.
    빈 입력이면 [] — 호출부가 미주입(byte-동일)하게 한다.
    """
    lines: List[str] = []
    for s in list(suggestions)[:max_lines]:
        recent = s.get("recent_year") or {}
        recent_txt = ""
        if recent:
            recent_txt = (
                f", 최근연도({recent['year']}) 손익 {recent['base_profit']:,.0f}"
                f"→{recent['kept_profit']:,.0f}"
            )
        lines.append(
            f"- 반사실 검증된 필터 후보: `{s['filter']}` — 직전 백테에 적용 시 거래 "
            f"{s['base_trades']}→{s['kept_trades']}건, 총손익 {s['profit_ratio']:.0%}"
            f"(잘린 거래 순손익 {s['cut_net_profit']:,.0f}), 승률 "
            f"{s['base_win_rate']:.0%}→{s['kept_win_rate']:.0%}{recent_txt}."
        )
    if lines:
        lines.insert(0, "직전 백테 반사실 필터 분석(인샘플 advisory — 임계는 근처 라운드 값으로 보정해 적용하라):")
    return lines


def suggestions_payload(csv_path: str, *, top_k: int = 5) -> Dict[str, Any]:
    """대시보드용 JSON payload(제안 + 기본 통계). 실패는 빈 구조(무예외)."""
    out: Dict[str, Any] = {"suggestions": [], "count": 0}
    try:
        out["suggestions"] = suggest_filters(csv_path, top_k=top_k)
        out["count"] = len(out["suggestions"])
    except Exception:  # noqa: BLE001
        pass
    return out


def result_as_dict(result: CounterfactualResult) -> Dict[str, Any]:
    """CounterfactualResult를 JSON-safe dict로 변환한다."""
    payload = asdict(result)
    payload["filters"] = [f.as_text() for f in result.filters]
    return payload
