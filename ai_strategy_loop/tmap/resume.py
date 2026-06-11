"""TMAP 스윕 중단 재개(--resume) 판정 — G2 보조 (2026-06-11).

W1 본 스윕(56포인트, ~2시간)이 gen14에서 프로세스 중단으로 멈춘 사건이 계기다.
스윕은 state.py의 (run_id, gen_no) UPSERT 계약 위에서 돌므로, 같은 run_id를
다시 열어 기존 ok 세대는 건너뛰고 error/누락 세대만 재평가하면 안전하게
이어갈 수 있다. 라벨(strategy_gist)이 불일치하면 — 템플릿/포인트 정의가
바뀐 경우 — 스킵하지 않고 재평가한다(보수적 기본값, UPSERT라 재기록 안전).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def resume_done_map(state: Any, run_id: str) -> Dict[int, Dict[str, Any]]:
    """run에 이미 기록된 ok 세대를 {gen_no: row}로 반환한다(스킵 후보)."""
    return {
        int(row["gen_no"]): row
        for row in state.get_generations(run_id)
        if row.get("status") == "ok"
    }


def resume_row(
    done: Dict[int, Dict[str, Any]], gen_no: int, label: str
) -> Optional[Dict[str, Any]]:
    """같은 gen_no에 같은 라벨의 ok 기록이 있을 때만 그 row를 반환한다.

    None이면 호출자가 그 포인트를 (재)평가해야 한다. error 세대는
    resume_done_map에서 이미 제외되므로 자동으로 재시도 대상이 된다.
    """
    row = done.get(gen_no)
    if row is not None and row.get("strategy_gist") == label:
        return row
    return None
