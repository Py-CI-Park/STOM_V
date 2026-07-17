"""advisory: 조건식 밴드 오버레이 — 등락율/시총/시간대 밴드를 지도 칸에 사상.

사전등록 §6 advisory(게이트 아님, 보고만): 인간 전당 밴드를 지도에 오버레이해
전당 밴드 칸의 상대 EV를 보고한다.

정직한 한계 공시:
  W2 인간 전당 19종은 익명 벤치마크(reference_strategies.json — 성과지표만,
  조건식 코드 없음)이며 strategy.db에 실재하지 않는다. 그들에 대해 원장이 기록한
  유일한 공통 밴드는 '거래 09:00~09:30'뿐(등락율/시총 필터 미기록)이라 전 시간대
  버킷을 덮는 비차별 밴드다. 따라서 파싱 가능한 대체 오버레이로 strategy.db에
  실재하는 챔피언 계보(ALP_V4 4종 + 902/905 시드)의 조건식 밴드를 파싱해 오버레이
  한다. 주의: 이 조건식들의 등락율 게이트는 넓고(1~15%), 실제 진입 집중(q2/q3)은
  복합 모멘텀 하위필터에서 나오므로 단일축 밴드로는 완전 포착되지 않는다 — 정밀한
  진입 사상은 champion 게이트(실거래 사상)가 담당한다.

원본 read-only, 엔진 0회.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from alpha_lab.stats_map import champion, config

# 파생 등락율(시가등락율·시가대비등락율·고저평균대비등락율)은 제외하고 순수 등락율만.
_UD = re.compile(r"(?<![가-힣])등락율\s*(<=|<|>=|>)\s*(-?[\d.]+)")
_UD_RANGE = re.compile(r"(-?[\d.]+)\s*(<=|<)\s*등락율\s*(<=|<)\s*(-?[\d.]+)")
_MC = re.compile(r"(?<![가-힣])시가총액\s*(<=|<|>=|>)\s*([\d.]+)")
_SB = re.compile(r"시분초\s*(<=|<|>=|>)\s*(\d+)")
_SB_RANGE = re.compile(r"(\d+)\s*(<=|<)\s*시분초\s*(<=|<)\s*(\d+)")


def parse_bands(code: str) -> Dict[str, object]:
    """전략코드 → {updown:(lo,hi), mktcap:(lo,hi), sibun:(lo,hi)} 관측 밴드.

    조건식 전반의 순수 등락율/시가총액/시분초 수치 비교를 모아 하한·상한 envelope를
    만든다(하위필터·VI·상대조건은 미포착 — 느슨한 상위집합). 미검출은 None.
    """
    ud = _envelope(code, _UD, _UD_RANGE)
    mc = _envelope(code, _MC, None)
    sb = _envelope(code, _SB, _SB_RANGE)
    return {"updown": ud, "mktcap": mc, "sibun": sb}


def _envelope(code, single, rng) -> Optional[Tuple[float, float]]:
    """단일/범위 비교를 모아 (min_lower, max_upper). 검출 없으면 None."""
    los: List[float] = []
    his: List[float] = []
    for op, val in single.findall(code):
        v = float(val)
        (his if op in ("<", "<=") else los).append(v)
    if rng is not None:
        for lo, _o1, _o2, hi in rng.findall(code):
            los.append(float(lo))
            his.append(float(hi))
    if not los and not his:
        return None
    return (min(los) if los else float("-inf"),
            max(his) if his else float("inf"))


def band_cells(bands: Dict[str, object], *, three_axis: bool
               ) -> List[Tuple[int, int, int]]:
    """관측 밴드 → 겹치는 지도 칸 좌표 목록(2축이면 mktcap=-1)."""
    tbs = _time_buckets(bands["sibun"])
    uqs = _updown_quartiles(bands["updown"])
    mcs = _mktcap_bands(bands["mktcap"]) if three_axis else [-1]
    return [(tb, uq, mc) for tb in tbs for uq in uqs for mc in mcs]


def _time_buckets(sibun: Optional[Tuple[float, float]]) -> List[int]:
    """시분초 밴드(HHMMSS) → 겹치는 5분 버킷 인덱스 0..5(미검출=전 버킷)."""
    if sibun is None:
        return list(range(len(config.TIME_BUCKETS)))
    lo, hi = sibun
    out = []
    for i, hhmm in enumerate(config.TIME_BUCKETS):
        b_lo = hhmm * 100                      # 버킷 시작 HHMM00 (예: 90000).
        b_hi = hhmm * 100 + 459                # 버킷 끝 HHMM+4:59 (예: 90459).
        if not (hi < b_lo or lo > b_hi):
            out.append(i)
    return out or list(range(len(config.TIME_BUCKETS)))


def _updown_quartiles(ud: Optional[Tuple[float, float]]) -> List[int]:
    """등락율 밴드 → 겹치는 4분위 인덱스(미검출=전 분위)."""
    if ud is None:
        return [0, 1, 2, 3]
    lo, hi = ud
    edges = [float("-inf")] + list(config.UPDOWN_EDGES) + [float("inf")]
    out = []
    for q in range(4):
        q_lo, q_hi = edges[q], edges[q + 1]
        if not (hi <= q_lo or lo >= q_hi):
            out.append(q)
    return out or [0, 1, 2, 3]


def _mktcap_bands(mc: Optional[Tuple[float, float]]) -> List[int]:
    """시가총액 밴드(억) → 겹치는 3구간 인덱스(미검출=전 구간)."""
    if mc is None:
        return [0, 1, 2]
    lo, hi = mc
    edges = [float("-inf")] + list(config.MKTCAP_EDGES) + [float("inf")]
    out = []
    for b in range(3):
        b_lo, b_hi = edges[b], edges[b + 1]
        if not (hi <= b_lo or lo >= b_hi):
            out.append(b)
    return out or [0, 1, 2]


def band_relative_ev(cells: Dict[Tuple[int, int, int], Dict[str, object]],
                     band: List[Tuple[int, int, int]]) -> Dict[str, object]:
    """밴드 칸의 n-가중 pooled EV vs 전체 pooled EV(상대 우위)."""
    in_band = {k: cells[k] for k in band if k in cells}
    pooled_all = champion.pooled_mean_net(cells)
    pooled_band = champion.pooled_mean_net(in_band)
    adv = (pooled_band - pooled_all) if (pooled_band is not None
                                         and pooled_all is not None) else None
    return {"n_band_cells": len(in_band), "pooled_all": pooled_all,
            "pooled_band": pooled_band, "band_advantage": adv}


def overlay(db_path, strategy_names: List[str], strategy_db) -> Dict[str, object]:
    """전략별 조건식 밴드 + 지도 상대 EV(L0/L1, 2축) — advisory 집계."""
    conn = sqlite3.connect(
        f"file:{Path(strategy_db).as_posix()}?mode=ro", uri=True)
    try:
        codes = {}
        for nm in strategy_names:
            row = conn.execute(
                'SELECT 전략코드 FROM stockbuy WHERE "index"=?', (nm,)).fetchone()
            if row and row[0]:
                codes[nm] = row[0]
    finally:
        conn.close()
    l0 = champion.read_cells(db_path, "cells_l0", config.AXIS_TIME_UD, 300)
    l1 = champion.read_cells(db_path, "cells_l1", config.AXIS_TIME_UD, 300)
    out: List[Dict[str, object]] = []
    for nm, code in codes.items():
        bands = parse_bands(code)
        band = band_cells(bands, three_axis=False)
        out.append({
            "strategy": nm, "bands": _band_repr(bands),
            "l0": band_relative_ev(l0, band),
            "l1": band_relative_ev(l1, band),
        })
    return {
        "note": "human_hall_19 lack parseable condition code (benchmark outside "
                "strategy.db; only common band 09:00-09:30). Overlaid instead: "
                "parseable champion+seed condition bands. 등락율 gate is broad; "
                "true q2/q3 concentration is compound-filter driven (see champion gate).",
        "strategies": out,
    }


def _band_repr(bands: Dict[str, object]) -> Dict[str, object]:
    """밴드 튜플을 JSON 친화 표현으로(inf → null 방향 표기)."""
    def rep(t):
        if t is None:
            return None
        lo, hi = t
        return [None if lo == float("-inf") else lo,
                None if hi == float("inf") else hi]
    return {k: rep(v) for k, v in bands.items()}
