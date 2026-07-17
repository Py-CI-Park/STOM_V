"""실엔진 배선 헬퍼 — 설정/등록 항목 조립 + loop_runs.db 결과 판독(순수 함수).

여기 함수들은 파일 I/O(설정 JSON 읽기, sqlite 판독)는 하되 엔진을 직접
기동하지 않는다 — subprocess 기동·strategy.db 등록 오케스트레이션은 실행
스크립트(alpha_lab/hillclimb 밖, 연구 산출물)가 이 헬퍼들을 조합해 담당한다.
이렇게 나누면 단위테스트가 임시 sqlite/JSON으로 엔진 없이 전 경로를 검증할
수 있다.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from alpha_lab.hillclimb.mutator import Metrics

__all__ = [
    "build_pairs_json",
    "build_train_config",
    "metrics_from_generation_row",
    "read_generation_metrics",
    "registration_item",
]

PathLike = Union[str, Path]

# gates_p4.oos_sealed(preregistration_v3.json, sha 50d3d38a): "2025-01 ~ 2026-02"
# 는 P4 전용 봉인창 — P3 train 평가에서 절대 사용 금지. train 상한을 그 직전
# 월(2024-12-31)로 고정한다.
TRAIN_WINDOW_START = 20220323
TRAIN_WINDOW_END = 20241231


def build_train_config(
    base_config_path: PathLike,
    *,
    bt_full_start: int = TRAIN_WINDOW_START,
    bt_full_end: int = TRAIN_WINDOW_END,
) -> Dict:
    """공식 warm64 프로파일(base_config_path)을 읽어 train 창만 덮어쓴 설정을 만든다.

    seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json
    을 그대로 읽어(변형 금지 원본) bt_full_start/bt_full_end만 바꾼다 —
    alpha_lab_20260705/exitchk_config_tick_warm64_y2023_20260706.json과 동일한
    "base_config + changed_fields_only" 관례.
    """
    base = json.loads(Path(base_config_path).read_text(encoding="utf-8"))
    config = dict(base)
    config["bt_full_start"] = int(bt_full_start)
    config["bt_full_end"] = int(bt_full_end)
    config["_derived"] = {
        "schema": "alpha_lab_v3_hillclimb_train_window_config_v1",
        "base_config": str(base_config_path),
        "changed_fields_only": ["bt_full_start", "bt_full_end"],
        "window_basis": (
            "preregistration_v3.json gates_p4.oos_sealed(2025-01~2026-02) "
            "직전까지 — P3 train은 OOS 봉인창을 침범하지 않는다"
        ),
    }
    return config


def build_pairs_json(items: Sequence[Tuple[str, str, str]]) -> List[Dict[str, str]]:
    """(label, buy_name, sell_name) 시퀀스 → claude_candidate_batch_eval pairs.json 페이로드."""
    return [{"label": label, "buy": buy, "sell": sell} for label, buy, sell in items]


def registration_item(name: str, buy_statement: str, sell_expr: str, meta: Optional[dict] = None) -> Dict:
    """alpha_lab.bridge.registrar.register_conditions items 원소 1건을 조립한다.

    name은 'ALP_' 접두 강제(레지스트라 계약과 동일 — 여기서도 사전 검증해
    등록 직전이 아니라 조립 시점에 오타를 잡는다).
    """
    if not name.startswith("ALP_"):
        raise ValueError(f"이름은 'ALP_' 접두가 강제된다: {name!r}")
    if not buy_statement or not buy_statement.strip():
        raise ValueError("buy_statement가 비어있다")
    if not sell_expr or not sell_expr.strip():
        raise ValueError("sell_expr이 비어있다")
    return {"name": name, "buy_expr": buy_statement, "sell_expr": sell_expr, "meta": meta or {}}


def metrics_from_generation_row(row: Mapping) -> Metrics:
    """loop_runs.db generations 1행(dict-like) → Metrics.

    row가 아예 없는 경우(등록/실행 실패로 세대가 기록되지 못함)는 호출측이
    별도 처리한다 — 이 함수는 존재하는 행의 매핑만 담당(status 누락 시
    "error"로 정직 폴백).
    """
    def _f(key: str) -> float:
        val = row.get(key)
        return float(val) if val is not None else 0.0

    return Metrics(
        status=str(row.get("status") or "error"),
        profit_pct=_f("total_profit_pct"),
        mdd=_f("mdd"),
        calmar=_f("calmar"),
        trade_count=int(row.get("trade_count") or 0),
        daily_avg_trades=_f("daily_avg_trades"),
        gate_passed=bool(row.get("gate_passed") or False),
        reason=str(row.get("reason") or ""),
    )


def read_generation_metrics(loop_runs_db: PathLike, run_id: str, gen_no: int) -> Optional[Metrics]:
    """loop_runs.db(read-only)에서 (run_id, gen_no) 행 하나를 읽어 Metrics로 변환.

    행이 없으면 None(호출측이 "세대 미기록"으로 별도 처리 — no_trades/error와
    구분되는 정직한 부재 신호).
    """
    uri = Path(loop_runs_db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT * FROM generations WHERE run_id = ? AND gen_no = ?",
            (run_id, gen_no),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    return metrics_from_generation_row(dict(row))
