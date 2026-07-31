"""다차원 수익률 맵(QSP3 P2/P4) — 변수 선택형 구간 손익 집계.

사용자 방법론: "백테스트 결과 바탕으로 여러 변수별 수익률과의 관계도 맵 —
여러 조건 구분을 가지고 수익률의 분포를 최대한 많은 요소로 시각화".

grid(): X(×Y) 변수 분위 구간별 {거래수, 손익 합, 평균수익률, 승률} — 대시보드
탐색기의 데이터원. loss_regions(): 전 변수 1D 스캔으로 손실 집중 구간 랭킹 —
"어떤 매수 특징이 크게 잃는가"의 자동 후보 목록(제거/필터의 입력).
순수 함수 — I/O 는 CSV 읽기뿐, 상태 없음.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from ai_strategy_loop.autopsy.label_dataset import enrich

_META = {"수익률", "수익금"}


def _load(csv_path: str) -> pd.DataFrame:
    return enrich(pd.read_csv(csv_path, encoding="utf-8-sig")).df


def _numeric_features(df: pd.DataFrame) -> List[str]:
    out = []
    for c in df.columns:
        if not (c.startswith("B_") or c.startswith("D_")) or c in _META:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() >= 30 and float(s.std() or 0) > 0:
            out.append(c)
    return out


def _bin_series(s: pd.Series, bins: int) -> pd.Series:
    """분위 구간 라벨(경계 실값 표기). 동값 지배 변수는 구간 병합 허용(duplicates drop)."""
    try:
        return pd.qcut(s, q=bins, duplicates="drop").astype(str)
    except (ValueError, IndexError):
        return pd.Series(["전체"] * len(s), index=s.index)


def grid(csv_path: str, x: str, y: Optional[str] = None, *, bins: int = 5) -> Dict[str, Any]:
    """X(×Y) 구간별 손익 집계 — 탐색기 히트맵 데이터."""
    df = _load(csv_path)
    if x not in df.columns or (y and y not in df.columns):
        return {"error": f"변수 없음: {x if x not in df.columns else y}", "cells": []}
    pnl = pd.to_numeric(df["수익금"], errors="coerce").fillna(0)
    ret = pd.to_numeric(df["수익률"], errors="coerce")
    gx = _bin_series(pd.to_numeric(df[x], errors="coerce"), bins)
    keys = [gx] if not y else [gx, _bin_series(pd.to_numeric(df[y], errors="coerce"), bins)]
    g = pd.DataFrame({"pnl": pnl, "ret": ret, "win": (ret > 0).astype(int)}).groupby(keys, observed=True)
    cells = []
    for k, sub in g:
        kx, ky = (k, None) if not y else k
        cells.append({"x_bin": str(kx), "y_bin": (None if ky is None else str(ky)),
                      "n": int(len(sub)), "pnl": float(sub["pnl"].sum()),
                      "mean_ret": float(sub["ret"].mean()),
                      "win_rate": float(sub["win"].mean())})
    return {"x": x, "y": y, "bins": bins, "total_pnl": float(pnl.sum()),
            "n": int(len(df)), "cells": cells}


def loss_regions(csv_path: str, *, bins: int = 5, top: int = 20) -> List[Dict[str, Any]]:
    """전 변수 1D 스캔 — 손실 합이 큰 (변수, 구간) 랭킹. '이 특징 = 손실' 후보."""
    df = _load(csv_path)
    pnl = pd.to_numeric(df["수익금"], errors="coerce").fillna(0)
    rows: List[Dict[str, Any]] = []
    for f in _numeric_features(df):
        b = _bin_series(pd.to_numeric(df[f], errors="coerce"), bins)
        agg = pd.DataFrame({"pnl": pnl}).groupby(b, observed=True)["pnl"].agg(["sum", "size"])
        for interval, r in agg.iterrows():
            if r["sum"] < 0:
                rows.append({"feature": f, "bin": str(interval),
                             "n": int(r["size"]), "pnl": float(r["sum"])})
    rows.sort(key=lambda r: r["pnl"])
    return rows[:top]
