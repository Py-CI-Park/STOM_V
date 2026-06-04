"""Variable correlation analysis over per-trade CSVs.

This module is analysis-only. It reads already-produced trade CSVs and never
feeds the loop scorer, hard gate, strategy generator, winner export, or engine.
Only numeric ``B_*`` entry variables are considered as features; result and
diagnostic columns are excluded except for the outcome column ``수익률``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Final, List, Optional

import pandas as pd

from cli._utils import ensure_dataframe as _ensure_dataframe

_OUTCOME_COLUMN: Final = "수익률"
_FEATURE_PREFIX: Final = "B_"
_SUPPORTED_METHODS: Final = {"pearson", "spearman"}


def _json_float(value: Any) -> Optional[float]:
    """Return a finite JSON-safe float or None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _feature_columns(df: pd.DataFrame) -> List[str]:
    """Return deterministic B_* feature columns only."""
    return sorted(
        str(column)
        for column in df.columns
        if isinstance(column, str) and column.startswith(_FEATURE_PREFIX)
    )


def _pair_correlation(
    left: pd.Series,
    right: pd.Series,
    method: str,
    min_samples: int,
) -> tuple[int, Optional[float]]:
    """Compute a pairwise correlation with sample and constant-column guards."""
    paired = pd.DataFrame({
        "left": pd.to_numeric(left, errors="coerce"),
        "right": pd.to_numeric(right, errors="coerce"),
    }).dropna()
    n = int(len(paired))
    if n < min_samples:
        return n, None
    if paired["left"].nunique(dropna=True) < 2 or paired["right"].nunique(dropna=True) < 2:
        return n, None
    return n, _json_float(paired["left"].corr(paired["right"], method=method))


def _sort_correlation_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort rows by absolute signal strength, keeping None values last."""
    return sorted(
        rows,
        key=lambda row: (
            -float(row["abs_correlation"]) if row.get("abs_correlation") is not None else 1.0,
            str(row.get("feature", row.get("feature_a", ""))),
            str(row.get("feature_b", "")),
        ),
    )


def compute_variable_correlation(
    df: pd.DataFrame,
    method: str = "pearson",
    min_samples: int = 3,
    top_n: int = 20,
) -> Dict[str, Any]:
    """Compute outcome and feature-to-feature correlations for numeric B_* columns.

    Returns an insufficient payload instead of raising when the frame lacks the
    outcome column, has too few valid outcome rows, or has no B_* features.
    """
    if method not in _SUPPORTED_METHODS:
        return {"error": "method must be pearson or spearman", "method": method}
    if df is None or len(df) == 0:
        return {"insufficient": True, "pooled_trades": 0}
    if _OUTCOME_COLUMN not in df.columns:
        return {
            "insufficient": True,
            "pooled_trades": int(len(df)),
            "reason": "missing_outcome_column",
        }

    returns = pd.to_numeric(df[_OUTCOME_COLUMN], errors="coerce")
    valid_returns = returns.dropna()
    pooled_trades = int(len(valid_returns))
    if pooled_trades < min_samples:
        return {
            "insufficient": True,
            "pooled_trades": pooled_trades,
            "reason": "too_few_outcome_rows",
        }

    features = _feature_columns(df)
    if not features:
        return {
            "insufficient": True,
            "pooled_trades": pooled_trades,
            "reason": "missing_b_features",
        }

    outcome_rows: List[Dict[str, Any]] = []
    for feature in features:
        n, corr = _pair_correlation(returns, df[feature], method, min_samples)
        outcome_rows.append({
            "feature": feature,
            "correlation": corr,
            "abs_correlation": None if corr is None else abs(corr),
            "n": n,
        })

    matrix_rows: List[Dict[str, Any]] = []
    for index, feature_a in enumerate(features):
        for feature_b in features[index + 1:]:
            n, corr = _pair_correlation(df[feature_a], df[feature_b], method, min_samples)
            matrix_rows.append({
                "feature_a": feature_a,
                "feature_b": feature_b,
                "correlation": corr,
                "abs_correlation": None if corr is None else abs(corr),
                "n": n,
            })

    sorted_outcome = _sort_correlation_rows(outcome_rows)
    sorted_matrix = _sort_correlation_rows(matrix_rows)
    top_pairs = [row for row in sorted_matrix if row["correlation"] is not None][:top_n]

    return {
        "method": method,
        "pooled_trades": pooled_trades,
        "feature_count": len(features),
        "features": features,
        "outcome": _OUTCOME_COLUMN,
        "outcome_correlations": sorted_outcome,
        "feature_matrix": sorted_matrix,
        "top_pairs": top_pairs,
    }


def variable_correlation_from_csvs(
    csv_paths: List[str],
    method: str = "pearson",
    min_samples: int = 3,
    top_n: int = 20,
) -> Dict[str, Any]:
    """Pool readable trade CSVs and run variable correlation analysis."""
    frames: List[pd.DataFrame] = []
    for path in csv_paths or []:
        if not path:
            continue
        try:
            frame = _ensure_dataframe(path)
        except Exception:  # noqa: BLE001 - unreadable CSVs are skipped like peer modules.
            continue
        if frame is not None and len(frame) > 0:
            frames.append(frame)

    if not frames:
        return {"insufficient": True, "pooled_trades": 0}

    pooled = pd.concat(frames, ignore_index=True, sort=False)
    if len(pooled) == 0:
        return {"insufficient": True, "pooled_trades": 0}

    report = compute_variable_correlation(
        pooled,
        method=method,
        min_samples=min_samples,
        top_n=top_n,
    )
    return {"sources": len(frames), **report}
