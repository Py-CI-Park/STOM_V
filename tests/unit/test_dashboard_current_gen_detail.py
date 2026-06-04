"""Static regression tests for generation row actions."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_generation_table_passes_full_row_to_code_viewer_and_gen_to_detail() -> None:
    src = _read_front("table.jsx")

    assert "onViewCode && onViewCode(g)" in src
    assert "onSelectDetail && onSelectDetail(g.gen_no)" in src


def test_app_wires_generation_actions_to_code_modal_and_detail_chart() -> None:
    src = _read_front("app.jsx")

    assert "const [codeViewGen, setCodeViewGen]" in src
    assert "const [selectedDetailGen, setSelectedDetailGen]" in src
    assert "onViewCode={(g) => setCodeViewGen(g)}" in src
    assert "onSelectDetail={(genNo) => setSelectedDetailGen(genNo)}" in src
    assert "externalSelGen={selectedDetailGen}" in src
    assert "generation={codeViewGen}" in src
    assert "runId={state.run_id}" in src
    assert "baseUrl={baseUrl}" in src
