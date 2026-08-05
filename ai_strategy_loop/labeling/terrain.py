"""M-1 시초 지형도 — 라벨 parquet 를 분×상태 지도로 집계한다.

산출은 전부 **관측(진단) 권위**다. 여기서 조건식을 만들지 않는다 — 어디가 밝은지 보여줄 뿐.
모든 칸에 표본수를 병기한다(UI 원칙 1: 표본 없는 밝은 칸은 함정).
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

_LABEL_DIR = os.path.join(os.path.dirname(__file__), "..", "state", "labels", "design")
_USABLE_FLAGS = ("flag_no_trade", "flag_limit_up", "flag_vi_near")

#: 지형도 기본 라벨 — QA-1 로 엔진 정합이 확인된 A(호가) 기준.
PRIMARY_LABEL = "frA_300"


def load_usable(columns: list[str], *, limit_days: int | None = None) -> pd.DataFrame:
    """사용 가능(플래그 0) 행만 적재. columns 에 라벨·플래그는 자동 포함."""
    need = list(dict.fromkeys([*columns, PRIMARY_LABEL, *_USABLE_FLAGS]))
    files = sorted(glob.glob(os.path.join(_LABEL_DIR, "day=*.parquet")))
    if limit_days:
        files = files[:limit_days]
    frames = [pd.read_parquet(path, columns=need) for path in files]
    merged = pd.concat(frames, ignore_index=True)
    usable = merged[merged[list(_USABLE_FLAGS)].sum(axis=1) == 0]
    return usable.drop(columns=list(_USABLE_FLAGS))


def minute_profile(frame: pd.DataFrame, label: str = PRIMARY_LABEL) -> pd.DataFrame:
    """분(09:00=0 … 09:20=20)별 E[라벨]·표본수·MFE/MAE — 지형도의 1열."""
    rows = frame[frame[label].notna()]
    grouped = rows.groupby("분").agg(
        표본수=(label, "size"),
        평균=(label, "mean"),
        중앙값=(label, "median"),
        양수비율=(label, lambda s: float((s > 0).mean())),
        mfe평균=("mfe_300", "mean"),
        mae평균=("mae_300", "mean"),
    )
    return grouped.reset_index()


def quantile_grid(frame: pd.DataFrame, variable: str, *, label: str = PRIMARY_LABEL,
                  buckets: int = 10) -> pd.DataFrame:
    """변수 분위 × E[라벨] — 임계는 이 격자 경계 위에서만 고른다(규율)."""
    rows = frame[frame[label].notna() & frame[variable].notna()]
    deciles, edges = pd.qcut(rows[variable], buckets, labels=False,
                             duplicates="drop", retbins=True)
    grouped = rows.groupby(deciles).agg(표본수=(label, "size"), 평균=(label, "mean"))
    grouped["하한"] = edges[:-1][: len(grouped)]
    grouped["상한"] = edges[1:][: len(grouped)]
    return grouped.reset_index(names="분위")


def facet_heatmap(frame: pd.DataFrame, var_x: str, var_y: str, facet: str | None = None,
                  *, label: str = PRIMARY_LABEL, buckets: int = 10,
                  facet_bins: int = 3) -> dict:
    """2D 히트맵(+선택 파셋) — 사람용 3D 는 3D 서피스가 아니라 파셋 소격자다."""
    cols = [var_x, var_y] + ([facet] if facet else [])
    rows = frame[frame[label].notna()].dropna(subset=cols)
    qx = pd.qcut(rows[var_x], buckets, labels=False, duplicates="drop")
    qy = pd.qcut(rows[var_y], buckets, labels=False, duplicates="drop")
    facets = (pd.qcut(rows[facet], facet_bins, labels=False, duplicates="drop")
              if facet else pd.Series(0, index=rows.index))
    grouped = rows.groupby([facets, qx, qy])[label].agg(["size", "mean"])
    payload: dict = {"var_x": var_x, "var_y": var_y, "facet": facet, "label": label, "cells": []}
    for (f, x, y), row in grouped.iterrows():
        payload["cells"].append({
            "facet": int(f), "x": int(x), "y": int(y),
            "n": int(row["size"]), "mean": round(float(row["mean"]), 4),
        })
    return payload
