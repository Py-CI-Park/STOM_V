from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_research_records_panel_contract() -> None:
    src = _front("research-records-panel.jsx")

    assert "function ResearchRecordsPanel(" in src
    assert '"/research_records"' in src
    assert '"/research_records/detail?campaign="' in src
    assert "selectedCampaign" in src
    assert "Object.assign(window, { ResearchRecordsPanel })" in src
    assert "export { ResearchRecordsPanel }" in src


def test_evolution_gui_parity_panel_contract() -> None:
    src = _front("evolution-gui-parity-panel.jsx")

    assert "function EvolutionGuiParityPanel(" in src
    assert '"/evolution_gui_parity?run_id="' in src
    assert "BtGuiParitySection" in src
    assert "externalSelGen" in src
    assert "Object.assign(window, { EvolutionGuiParityPanel })" in src
    assert "export { EvolutionGuiParityPanel }" in src


def test_app_mounts_new_evolution_panels() -> None:
    src = _front("app.jsx")

    assert 'from "./research-records-panel.jsx"' in src
    assert 'from "./evolution-gui-parity-panel.jsx"' in src
    assert "<ResearchRecordsPanel" in src
    assert "<EvolutionGuiParityPanel" in src

    detail = src.find("<BacktestDetailChart")
    parity = src.find("<EvolutionGuiParityPanel")
    assert detail != -1 and parity != -1
    assert detail < parity
    assert "externalSelGen={selectedDetailGen}" in src[parity: parity + 240]
