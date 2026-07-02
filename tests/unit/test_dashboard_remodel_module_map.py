from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL_APP = (
    REPO
    / "ai_strategy_loop"
    / "dashboard"
    / "frontend"
    / "remodel"
    / "src"
    / "app.js"
)


def test_remodel_declares_functional_module_map() -> None:
    # Given: the V3 remodel frontend still ships as a reviewed single-file bundle.
    app = REMODEL_APP.read_text(encoding="utf-8")

    # When/Then: the bundle exposes a stable map for the next functional parity work.
    for marker in [
        "const RemodelStatusVocabulary = [",
        "const RemodelModuleMap = [",
        "window.RemodelStatusVocabulary = RemodelStatusVocabulary",
        "window.RemodelModuleMap = RemodelModuleMap",
        "module: 'core/mode'",
        "module: 'core/api'",
        "module: 'core/state'",
        "module: 'components/status'",
        "module: 'components/layout'",
        "module: 'pages/backtest'",
        "module: 'pages/replay'",
        "module: 'pages/condition-ai'",
        "module: 'pages/audit'",
        "owner: 'BacktestAdapter'",
        "owner: 'ReplayAdapter'",
        "owner: 'RemodelAdapters'",
        "'requires-confirmation'",
    ]:
        assert marker in app
