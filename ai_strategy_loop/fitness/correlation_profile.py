"""Research-only profiling helpers for variable-correlation output."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Final, List, Optional

import pandas as pd

from cli.research_segments import (
    DEFAULT_TIME_BUCKETS,
    add_market_cap_segment,
    add_time_segment,
)

_UNCLASSIFIED: Final = "미분류"
_YEAR_COLUMNS: Final = ("일자", "날짜", "매수일자", "체결일자", "date", "Date", "datetime")
_RECENCY_WEIGHTS: Final = {"2023": 1.0, "2024": 1.25, "2025": 1.5}


def _json_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def _histogram(values: pd.Series, bins: int = 8) -> List[Dict[str, Any]]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return []
    lower = float(clean.min())
    upper = float(clean.max())
    if lower == upper:
        return [{"lower": lower, "upper": upper, "count": int(len(clean))}]
    width = (upper - lower) / max(1, bins)
    out: List[Dict[str, Any]] = []
    for index in range(bins):
        lo = lower + width * index
        hi = upper if index == bins - 1 else lower + width * (index + 1)
        if index == bins - 1:
            count = int(((clean >= lo) & (clean <= hi)).sum())
        else:
            count = int(((clean >= lo) & (clean < hi)).sum())
        out.append({"lower": lo, "upper": hi, "count": count})
    return out


def _win_loss(values: pd.Series, returns: pd.Series) -> Dict[str, Any]:
    valid = values.notna() & returns.notna()
    win = values[valid & (returns > 0)]
    lose = values[valid & (returns <= 0)]
    mean_win = _json_float(win.mean()) if len(win) else None
    mean_lose = _json_float(lose.mean()) if len(lose) else None
    median_win = _json_float(win.median()) if len(win) else None
    median_lose = _json_float(lose.median()) if len(lose) else None
    return {
        "win_count": int(len(win)),
        "loss_count": int(len(lose)),
        "mean_win": mean_win,
        "mean_loss": mean_lose,
        "median_win": median_win,
        "median_loss": median_lose,
        "mean_delta": None if mean_win is None or mean_lose is None else mean_win - mean_lose,
        "median_delta": None if median_win is None or median_lose is None else median_win - median_lose,
    }


def _feature_summary(df: pd.DataFrame, feature: str, returns: pd.Series) -> Dict[str, Any]:
    values = _numeric(df, feature)
    clean = values.dropna()
    return {
        "feature": feature,
        "count": int(len(clean)),
        "min": _json_float(clean.min()) if len(clean) else None,
        "q25": _json_float(clean.quantile(0.25)) if len(clean) else None,
        "median": _json_float(clean.median()) if len(clean) else None,
        "q75": _json_float(clean.quantile(0.75)) if len(clean) else None,
        "max": _json_float(clean.max()) if len(clean) else None,
        "mean": _json_float(clean.mean()) if len(clean) else None,
        "std": _json_float(clean.std()) if len(clean) > 1 else None,
        "histogram": _histogram(values),
        "win_loss": _win_loss(values, returns),
    }


def _ordered_features(features: List[str], outcome_rows: List[Dict[str, Any]]) -> List[str]:
    strength = {
        str(row.get("feature")): abs(float(row.get("correlation")))
        for row in outcome_rows
        if row.get("correlation") is not None
    }
    return sorted(features, key=lambda feature: (-strength.get(feature, -1.0), feature))


def _extract_year(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(int(value)) if isinstance(value, (int, float)) else str(value)
    match = re.search(r"(19\d{2}|20\d{2})", text)
    if not match:
        return None
    return match.group(1)


def _with_year_bucket(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    years: Optional[pd.Series] = None
    for column in _YEAR_COLUMNS:
        if column not in out.columns:
            continue
        parsed = out[column].map(_extract_year)
        if parsed.notna().any():
            years = parsed
            break
    out["_year_segment"] = years.fillna(_UNCLASSIFIED) if years is not None else _UNCLASSIFIED
    return out


def _segment_rows(
    df: pd.DataFrame,
    label_column: str,
    features: List[str],
    outcome_column: str,
    min_samples: int,
) -> List[Dict[str, Any]]:
    if label_column not in df.columns:
        return []
    rows: List[Dict[str, Any]] = []
    for label, group in df.groupby(label_column, dropna=False):
        text_label = str(label)
        if text_label == _UNCLASSIFIED:
            continue
        returns = _numeric(group, outcome_column).dropna()
        if len(returns) < min_samples:
            continue
        feature_ranges = [
            _feature_summary(group, feature, _numeric(group, outcome_column))
            for feature in features[:3]
            if feature in group.columns
        ]
        rows.append({
            "label": text_label,
            "sample_count": int(len(returns)),
            "avg_return": _json_float(returns.mean()),
            "win_rate": _json_float((returns > 0).mean()),
            "feature_ranges": feature_ranges,
        })
    return sorted(rows, key=lambda row: (-int(row["sample_count"]), str(row["label"])))


def _interaction_candidates(
    outcome_rows: List[Dict[str, Any]],
    matrix_rows: List[Dict[str, Any]],
    top_n: int,
) -> List[Dict[str, Any]]:
    outcome = {
        str(row["feature"]): row
        for row in outcome_rows
        if row.get("correlation") is not None and row.get("feature")
    }
    ordered = sorted(
        outcome,
        key=lambda feature: -abs(float(outcome[feature]["correlation"])),
    )[: max(6, top_n * 2)]
    matrix = {
        tuple(sorted((str(row.get("feature_a")), str(row.get("feature_b"))))): row
        for row in matrix_rows
    }
    candidates: List[Dict[str, Any]] = []
    for i, feature_a in enumerate(ordered):
        for feature_b in ordered[i + 1:]:
            pair = matrix.get(tuple(sorted((feature_a, feature_b))), {})
            corr = _json_float(pair.get("correlation"))
            collinearity = abs(corr) if corr is not None else 0.0
            strength = (
                abs(float(outcome[feature_a]["correlation"]))
                + abs(float(outcome[feature_b]["correlation"]))
            ) / 2.0
            score = strength * max(0.0, 1.0 - collinearity)
            candidates.append({
                "feature_a": feature_a,
                "feature_b": feature_b,
                "correlation": corr,
                "research_score": score,
                "sample_count": int(pair.get("n") or min(outcome[feature_a].get("n", 0), outcome[feature_b].get("n", 0))),
                "reason": "high_outcome_low_collinearity",
            })
    return sorted(candidates, key=lambda row: (-float(row["research_score"]), row["feature_a"], row["feature_b"]))[:top_n]


def _recency_research(year_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    weighted_sum = 0.0
    weight_count = 0.0
    for row in year_rows:
        label = str(row.get("label"))
        weight = _RECENCY_WEIGHTS.get(label)
        avg_return = row.get("avg_return")
        sample_count = row.get("sample_count")
        if weight is None or avg_return is None or not isinstance(sample_count, int):
            continue
        weighted_sum += float(avg_return) * weight * sample_count
        weight_count += weight * sample_count
    return {
        "research_only": True,
        "score_label": "research_score_not_promotion",
        "weights": dict(_RECENCY_WEIGHTS),
        "oos_excluded_years": [2022, 2026],
        "sample_count": int(weight_count),
        "research_score": None if weight_count <= 0 else weighted_sum / weight_count,
    }


def build_correlation_research_profile(
    df: pd.DataFrame,
    features: List[str],
    outcome_column: str,
    outcome_rows: List[Dict[str, Any]],
    matrix_rows: List[Dict[str, Any]],
    min_samples: int,
    top_n: int,
    row_limit: int,
    input_rows: int,
    truncated: bool,
) -> Dict[str, Any]:
    """Build read-only range, segment, recency, and interaction metadata."""
    returns = _numeric(df, outcome_column)
    ordered = _ordered_features(features, outcome_rows)
    profile_features = ordered[: min(top_n, 20)]
    labeled = _with_year_bucket(add_market_cap_segment(add_time_segment(df, buckets=DEFAULT_TIME_BUCKETS)))
    year_rows = _segment_rows(labeled, "_year_segment", profile_features, outcome_column, min_samples)
    return {
        "source": "pooled_trade_csv",
        "input_rows": int(input_rows),
        "sample_count": int(returns.dropna().shape[0]),
        "row_limit": int(row_limit),
        "truncated": bool(truncated),
        "range_summaries": [
            _feature_summary(df, feature, returns)
            for feature in profile_features
            if feature in df.columns
        ],
        "segment_summaries": {
            "time": _segment_rows(labeled, "_time_segment", profile_features, outcome_column, min_samples),
            "market_cap": _segment_rows(labeled, "_market_cap_segment", profile_features, outcome_column, min_samples),
            "year": year_rows,
        },
        "interaction_candidates": _interaction_candidates(outcome_rows, matrix_rows, top_n),
        "recency_research": _recency_research(year_rows),
    }
