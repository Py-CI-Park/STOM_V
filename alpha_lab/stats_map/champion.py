"""W4-2b 챔피언 칸 게이트 — ALP_V4 실거래 진입점을 지도 칸에 사상.

사전등록 §6 W4-2b: ALP_V4 4종의 발견창(<=2023-12-31) 진입 시점을 (시간대·등락율
분위·시총 구간) 칸에 사상하고, 그 칸들의 L1 mean_net(h300)이 L1 전체 평균보다
우위인지 >=3/4 챔피언에서 확인(지도가 실존 엣지를 볼 수 있는가). 원본 read-only,
엔진 백테 0회.

진입 시점의 등락율·시총은 챔피언 per-trade 원장의 B_등락율/B_시가총액(엔진이
체결 순간 tick 피드에서 기록한 스냅샷 = 그 초 tick DB 값과 동치)을 쓰고, 시간대
버킷은 매수시간에서 얻는다(맵 t0 프레임 정합 위해 체결오프셋−1). tick DB 대조
스팟체크는 gate 러너가 별도로 수행한다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from alpha_lab.stats_map import axes, config

_HMS_MOD = 1_000_000
_DAY_BASE_SEC = 9 * 3600            # 09:00:00 기준 오프셋 변환.
_DISCOVERY_END = 20231231          # 발견창 종료(포함).


def _entry_offset(hhmmss: int) -> int:
    """int HHMMSS → 09:00:00 기준 초 오프셋(창 밖이면 음수/초과)."""
    h, m, s = hhmmss // 10000, (hhmmss // 100) % 100, hhmmss % 100
    return h * 3600 + m * 60 + s - _DAY_BASE_SEC


def load_champion_trades(csv_path, discovery_end: int = _DISCOVERY_END
                         ) -> Dict[str, object]:
    """챔피언 per-trade CSV → 발견창·창내 진입의 칸 좌표 배열 + 커버리지.

    반환: {name, arrays{day,t0_off,time_b,updown_q,mktcap_b,updown,mktcap},
           coverage{total, discovery, in_window, mapped, ...}}.
    """
    df = pd.read_csv(csv_path, encoding="utf-8")
    total = len(df)
    bt = df["매수시간"].astype("int64").to_numpy()
    day = (bt // _HMS_MOD).astype(np.int64)
    hms = (bt % _HMS_MOD).astype(np.int64)
    fill_off = np.array([_entry_offset(int(v)) for v in hms], dtype=np.int64)
    t0_off = fill_off - 1                       # 맵 t0 = 체결−1s.
    in_disc = day <= discovery_end
    in_win = (t0_off >= config.GRID_START_OFFSET) & (t0_off < config.WINDOW_SECONDS)
    keep = in_disc & in_win
    updown = df["B_등락율"].to_numpy(dtype=np.float64)
    mktcap = df["B_시가총액"].to_numpy(dtype=np.float64)
    arrays = {
        "day": day[keep], "t0_off": t0_off[keep],
        "time_b": axes.time_bucket_offset(t0_off[keep]).astype(np.int64),
        "updown_q": axes.updown_quartile(updown[keep]).astype(np.int64),
        "mktcap_b": axes.mktcap_bucket(mktcap[keep]).astype(np.int64),
        "updown": updown[keep], "mktcap": mktcap[keep],
    }
    coverage = {
        "total": int(total), "discovery": int(in_disc.sum()),
        "in_window_of_discovery": int(keep.sum()),
        "outside_window": int((in_disc & ~in_win).sum()),
        "after_discovery": int((~in_disc).sum()),
    }
    return {"arrays": arrays, "coverage": coverage}


def cell_distribution(arrays: Dict[str, np.ndarray], *, three_axis: bool
                      ) -> Dict[Tuple[int, int, int], int]:
    """진입 배열 → 칸별 거래수. 2축이면 mktcap_b=-1로 표기."""
    tb, uq = arrays["time_b"], arrays["updown_q"]
    mc = arrays["mktcap_b"] if three_axis else np.full(tb.size, -1)
    out: Dict[Tuple[int, int, int], int] = {}
    for key in zip(tb.tolist(), uq.tolist(), mc.tolist()):
        out[key] = out.get(key, 0) + 1
    return out


def read_cells(db_path, table: str, axis_set: str, h: int
               ) -> Dict[Tuple[int, int, int], Dict[str, object]]:
    """stats_map.db 셀 테이블 → {(time_b,updown_q,mktcap_b): row}. read-only."""
    conn = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            f"SELECT * FROM {table} WHERE axis_set=? AND h=?", (axis_set, h))
        out: Dict[Tuple[int, int, int], Dict[str, object]] = {}
        for r in cur:
            out[(r["time_b"], r["updown_q"], r["mktcap_b"])] = dict(r)
        return out
    finally:
        conn.close()


def pooled_mean_net(cells: Dict[Tuple[int, int, int], Dict[str, object]]
                    ) -> Optional[float]:
    """판정 가능 셀의 n-가중 pooled mean_net(전체 평균) — report.pooled_mean_net 동형."""
    num = den = 0.0
    for row in cells.values():
        if _judged(row):
            num += float(row["mean_net"]) * int(row["n"])
            den += int(row["n"])
    return num / den if den > 0 else None


def _judged(row: Dict[str, object]) -> bool:
    return bool(row["n"]) and not row["insufficient"] and row["mean_net"] is not None


def champion_cell_ev(dist: Dict[Tuple[int, int, int], int],
                     cells: Dict[Tuple[int, int, int], Dict[str, object]]
                     ) -> Dict[str, object]:
    """거래가중 셀 EV(occupied 칸의 mean_net) + 커버리지 + 칸별 상세."""
    num = den = 0.0
    covered = uncovered = 0
    detail: List[Dict[str, object]] = []
    for key, cnt in sorted(dist.items(), key=lambda kv: -kv[1]):
        row = cells.get(key)
        judged = row is not None and _judged(row)
        mn = float(row["mean_net"]) if judged else None
        n = int(row["n"]) if row is not None and row["n"] else 0
        if judged:
            num += mn * cnt
            den += cnt
            covered += cnt
        else:
            uncovered += cnt
        detail.append({"cell": list(key), "trades": int(cnt),
                       "cell_mean_net": mn, "cell_n": n, "judged": judged})
    total = covered + uncovered
    return {
        "cell_ev": (num / den) if den > 0 else None,
        "trades_total": int(total), "trades_covered": int(covered),
        "coverage_pct": round(100.0 * covered / total, 2) if total else 0.0,
        "cells": detail,
    }


def gate_one(name: str, trades: Dict[str, object], db_path
             ) -> Dict[str, object]:
    """한 챔피언의 L1/L0 칸 EV vs 전체 평균 + 통과 판정(L1 기준)."""
    arrays = trades["arrays"]
    dist2 = cell_distribution(arrays, three_axis=False)
    dist3 = cell_distribution(arrays, three_axis=True)
    l1 = read_cells(db_path, "cells_l1", config.AXIS_TIME_UD, 300)
    l0 = read_cells(db_path, "cells_l0", config.AXIS_TIME_UD, 300)
    l1_3 = read_cells(db_path, "cells_l1", config.AXIS_TIME_MC_UD, 300)
    pooled_l1 = pooled_mean_net(l1)
    pooled_l0 = pooled_mean_net(l0)
    champ_l1 = champion_cell_ev(dist2, l1)
    champ_l0 = champion_cell_ev(dist2, l0)
    champ_l1_3 = champion_cell_ev(dist3, l1_3)
    passed = (champ_l1["cell_ev"] is not None and pooled_l1 is not None
              and champ_l1["cell_ev"] > pooled_l1)
    return {
        "champion": name, "coverage": trades["coverage"],
        "pooled_l1_mean_net": pooled_l1, "pooled_l0_mean_net": pooled_l0,
        "champ_l1_cell_ev": champ_l1["cell_ev"],
        "champ_l0_cell_ev": champ_l0["cell_ev"],
        "champ_l1_3axis_cell_ev": champ_l1_3["cell_ev"],
        "l1_coverage_pct": champ_l1["coverage_pct"],
        "l1_advantage": (champ_l1["cell_ev"] - pooled_l1)
        if (champ_l1["cell_ev"] is not None and pooled_l1 is not None) else None,
        "passed": bool(passed),
        "l1_cells_2axis": champ_l1["cells"],
        "l0_cells_2axis": champ_l0["cells"],
    }


def run_gate(csv_by_champion: Dict[str, object], db_path
             ) -> Dict[str, object]:
    """4종 챔피언 게이트 집계 — >=3/4 통과 필요."""
    results = []
    for name, csv_path in csv_by_champion.items():
        trades = load_champion_trades(csv_path)
        results.append(gate_one(name, trades, db_path))
    n_pass = sum(int(r["passed"]) for r in results)
    return {
        "n_champions": len(results), "n_pass_l1": n_pass,
        "gate_passed": n_pass >= 3,
        "threshold": "L1 occupied-cell EV(h300) > pooled L1 mean_net; >=3/4 champions",
        "champions": results,
    }
