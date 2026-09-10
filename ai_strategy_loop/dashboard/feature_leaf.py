"""Leaf projections reuse the existing numerical owners on a checked snapshot."""

from __future__ import annotations

# Existing pandas owner retained by explicit project requirements; no stack migration.
import pandas as pd

from ai_strategy_loop.autopsy import label_dataset as labels
from ai_strategy_loop.dashboard.feature_context import (
    FeatureContext,
    FeatureResponse,
    FeatureStatus,
    blocked_feature,
)
from ai_strategy_loop.dashboard.feature_snapshot import (
    SnapshotFrameError,
    snapshot_dataset,
)
from ai_strategy_loop.dashboard.trade_csv_models import QualityModel


class LeafSample(QualityModel):
    name: str
    buy_time: str
    pct: float
    krw: float


def leaf_result(context: FeatureContext) -> FeatureResponse:
    payload = FeatureResponse(
        {
            **context.envelope().root,
            "timeframe": "unknown",
            "n": None,
            "leaf_matrix": None,
            "features": None,
            "leaf_samples": None,
            "derived": None,
            "excluded": None,
        }
    )
    snapshot = context.source.checked.snapshot
    if not context.source.analysis_ready or snapshot is None:
        return payload
    try:
        dataset = snapshot_dataset(snapshot)
        samples = {}
        for leaf, indices in dataset.df.groupby("leaf").groups.items():
            sub = (
                dataset.df.loc[indices]
                .assign(
                    _pct=lambda frame: pd.to_numeric(frame["수익률"], errors="coerce"),
                )
                .dropna(subset=["_pct"])
            )
            picked = pd.concat([sub.nsmallest(4, "_pct"), sub.nlargest(4, "_pct")])
            samples[str(leaf)] = [
                LeafSample.model_validate(
                    {
                        "name": str(row.get("종목명", "")),
                        "buy_time": str(row.get("매수시간", "")),
                        "pct": row["_pct"],
                        "krw": row.get("수익금", 0) or 0,
                    }
                ).model_dump()
                for _, row in picked.iterrows()
            ]
        return FeatureResponse.model_validate(
            {
                **payload.root,
                "timeframe": dataset.timeframe,
                "n": len(dataset.df),
                "leaf_matrix": labels.leaf_matrix(dataset),
                "features": labels.feature_discrimination(dataset)[:12],
                "leaf_samples": samples,
                "derived": dataset.derived,
                "excluded": dataset.excluded,
            }
        ).finite()
    except SnapshotFrameError as exc:
        return blocked_feature(payload, FeatureStatus.PROCESSING_ERROR, str(exc))
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
    ) as exc:
        return blocked_feature(
            payload,
            FeatureStatus.PROCESSING_ERROR,
            f"리프 분석을 완료하지 못했습니다 ({type(exc).__name__}).",
        )
