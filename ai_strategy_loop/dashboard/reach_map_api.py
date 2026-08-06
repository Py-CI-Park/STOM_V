"""도달 지도 API (QSP10 P4) — 페이지 22~24 데이터 공급자.

권위: 전부 **탐색용(관측)**이다. 라벨 지도 위의 추정이며 자본 경로(동시보유·잔량)를
반영하지 못한다 — 공식 판정은 엔진 실측과 검증 사다리에서만 한다.

성능 계약: 집행 우주 뷰를 프로세스 메모리에 1회 적재하고, 이후 슬라이더 질의는
numpy 마스크로 처리한다(목표 1초 이내).
"""

from __future__ import annotations

import glob
import json
import os
import time
from typing import Annotated, Final

import pandas as pd
from fastapi import APIRouter
from pydantic import Field, StringConstraints, field_validator

from ai_strategy_loop.dashboard.trade_path_api_models import FrozenPayload
from ai_strategy_loop.labeling.cube import build_cube
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.universe import apply_universe, cluster_load, expectancy

reach_map_router = APIRouter()

_LABEL_ROOT: Final = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_LANE_DIRS: Final = {"tick": "design_v2", "min": "min_design_v2"}
_WARMUP: Final = {"tick": 60, "min": 60}
_MAX_CLAUSES: Final = 8
_view_cache: dict[str, pd.DataFrame] = {}
_candidates_path: Final = os.path.join(_LABEL_ROOT, "_reach_candidates.jsonl")

LaneName = Annotated[str, StringConstraints(pattern="^(tick|min)$")]


def _load_view(lane: str) -> pd.DataFrame | None:
    """집행 우주 뷰 — 프로세스 수명 동안 1회 적재(슬라이더 응답 1초 계약의 근거)."""
    if lane in _view_cache:
        return _view_cache[lane]
    directory = os.path.join(_LABEL_ROOT, _LANE_DIRS[lane])
    files = sorted(glob.glob(os.path.join(directory, "day=*.parquet")))
    if not files:
        return None
    frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    view = apply_universe(frame, warmup=_WARMUP[lane])
    _view_cache[lane] = view
    return view


class ClauseFilter(FrozenPayload):
    variable: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    operator: Annotated[str, StringConstraints(pattern="^(>|>=|<|<=)$")]
    value: float


class SliderQuery(FrozenPayload):
    lane: LaneName = "tick"
    tp_pct: float = Field(default=2.0, gt=0, le=30)
    sl_pct: float = Field(default=1.0, gt=0, le=30)
    clauses: tuple[ClauseFilter, ...] = Field(default=(), max_length=_MAX_CLAUSES)
    time_start: int | None = Field(default=None, ge=0, le=235959)
    time_end: int | None = Field(default=None, ge=0, le=235959)

    @field_validator("clauses", mode="before")
    @classmethod
    def _tuple_clauses(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class CandidateSave(FrozenPayload):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
    query: SliderQuery
    metrics: dict
    note: Annotated[str, StringConstraints(max_length=500)] = ""


def _barrier_columns(tp_pct: float, sl_pct: float) -> tuple[str, str] | None:
    """배리어 그리드는 사전 고정 — 임의 값은 라벨이 없으므로 거부한다."""
    up, down = f"hit_up_{int(tp_pct)}", f"hit_dn_{int(sl_pct)}"
    if float(tp_pct) != int(tp_pct) or float(sl_pct) != int(sl_pct):
        return None
    return up, down


@reach_map_router.get("/bt/map/universe")
def universe_status(lane: LaneName = "tick") -> dict:
    """지도 적재 상태 — 화면 진입 시 '데이터 있음/없음'을 명확히 보여준다."""
    view = _load_view(lane)
    if view is None:
        return {"available": False, "lane": lane,
                "message": f"라벨 v2 가 없습니다. build_labels --lane {lane} 를 먼저 실행하세요."}
    return {
        "available": True, "lane": lane, "rows": int(len(view)),
        "universe_version": view.attrs.get("universe_version"),
        "warmup": view.attrs.get("warmup"),
        "days": int(view["일자"].nunique()),
        "design": list(LANES[lane].design),
        "variables": [c for c in view.columns if view[c].dtype.kind == "f"],
        "authority": "exploratory",
    }


@reach_map_router.post("/bt/map/slider")
def slider_query(payload: SliderQuery) -> dict:
    """슬라이더 질의 — 조건 필터링 후 배리어 기대값·군집도. 엔진 실행 없음."""
    view = _load_view(payload.lane)
    if view is None:
        return {"available": False, "message": "라벨 v2 없음"}
    columns = _barrier_columns(payload.tp_pct, payload.sl_pct)
    if columns is None or columns[0] not in view.columns or columns[1] not in view.columns:
        return {"available": False,
                "message": f"배리어 라벨이 없습니다: TP{payload.tp_pct}/SL{payload.sl_pct} "
                           "(사전 고정 그리드만 지원)"}
    started = time.time()
    mask = pd.Series(True, index=view.index)
    for clause in payload.clauses:
        if clause.variable not in view.columns:
            return {"available": False, "message": f"알 수 없는 변수: {clause.variable}"}
        column = view[clause.variable]
        if clause.operator == ">":
            mask &= column > clause.value
        elif clause.operator == ">=":
            mask &= column >= clause.value
        elif clause.operator == "<":
            mask &= column < clause.value
        else:
            mask &= column <= clause.value
    if payload.time_start is not None:
        mask &= view["시분초"] >= payload.time_start
    if payload.time_end is not None:
        mask &= view["시분초"] <= payload.time_end

    subset = view.loc[mask]
    lane = LANES[payload.lane]
    stats = expectancy(subset, tp_pct=payload.tp_pct, sl_pct=payload.sl_pct,
                       tp=columns[0], sl=columns[1], horizon=lane.barrier_horizon,
                       timeout_label=f"frA_{lane.path_window}")
    return {
        "available": True, "authority": "exploratory",
        "rows": int(len(subset)), "days": int(subset["일자"].nunique()) if len(subset) else 0,
        "per_day": float(len(subset) / max(view["일자"].nunique(), 1)),
        "metrics": stats,
        "cluster": cluster_load(subset),
        "elapsed_ms": int((time.time() - started) * 1000),
    }


@reach_map_router.get("/bt/map/cube")
def cube(lane: LaneName = "tick", variable: str = "", tp_pct: float = 2.0,
         sl_pct: float = 1.0, buckets: int = 20) -> dict:
    """변수 분위별 배리어 성적 — 페이지 22 히트맵/막대의 원천. 전 칸 표본수 포함."""
    view = _load_view(lane)
    if view is None or not variable or variable not in view.columns:
        return {"available": False, "message": "라벨 v2 또는 변수 없음"}
    columns = _barrier_columns(tp_pct, sl_pct)
    if columns is None or columns[0] not in view.columns:
        return {"available": False, "message": "배리어 라벨 없음"}
    spec = LANES[lane]
    table = build_cube(view, variables=[variable], tp_pct=tp_pct, sl_pct=sl_pct,
                       tp=columns[0], sl=columns[1], horizon=spec.barrier_horizon,
                       timeout_label=f"frA_{spec.path_window}",
                       buckets=max(2, min(int(buckets), 100)))
    return {"available": True, "authority": "exploratory", "variable": variable,
            "rule": f"TP{tp_pct}/SL{sl_pct}",
            "cells": json.loads(table.to_json(orient="records"))}


@reach_map_router.post("/bt/map/candidate")
def save_candidate(payload: CandidateSave) -> dict:
    """후보 저장 — 근거(질의 조건·지표)를 계보로 남긴다. 채택이 아니라 기록이다."""
    os.makedirs(os.path.dirname(_candidates_path), exist_ok=True)
    record = {"name": payload.name, "query": payload.query.model_dump(),
              "metrics": payload.metrics, "note": payload.note,
              "authority": "exploratory"}
    with open(_candidates_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=float) + "\n")
    return {"status": "ok", "saved": payload.name, "path": os.path.abspath(_candidates_path)}


@reach_map_router.get("/bt/map/candidates")
def list_candidates() -> dict:
    if not os.path.exists(_candidates_path):
        return {"candidates": []}
    with open(_candidates_path, encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return {"candidates": rows, "count": len(rows)}
