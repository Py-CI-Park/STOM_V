"""W3 production JSX source-graph gate contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
WEBUI = ROOT / "ai_strategy_loop" / "dashboard" / "webui-build"
CHECKER = WEBUI / "runtime-jsx-check.mjs"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required for the runtime JSX gate")
    return node


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_node(), str(CHECKER), *args],
        cwd=WEBUI,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def test_runtime_jsx_gate_compiles_the_real_production_graph() -> None:
    """Given production sources, when checked, then the reachable JSX graph is transformed."""
    result = _run("--json")

    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["status"] == "pass"
    assert report["entry"] == "src/track-z-entry.pilot.js"
    assert report["jsx_files"] >= 80
    assert report["graph_hash"]
    assert report["emitted_bytes"] > 0


def test_runtime_jsx_gate_fails_on_an_unresolved_real_graph_import(tmp_path: Path) -> None:
    """Given a broken graph, when checked, then an unresolved import is a nonzero failure."""
    entry = tmp_path / "entry.jsx"
    entry.write_text('import "./missing.jsx";\nexport const View = () => <div />;\n', encoding="utf-8")

    result = _run("--json", "--entry", str(entry))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert any("missing.jsx" in item for item in report["diagnostics"])


def test_runtime_jsx_gate_fails_on_invalid_jsx_syntax(tmp_path: Path) -> None:
    """Given invalid JSX, when checked, then transform diagnostics cannot falsely green."""
    entry = tmp_path / "entry.jsx"
    entry.write_text("export const View = () => <div>;\n", encoding="utf-8")

    result = _run("--json", "--entry", str(entry))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["diagnostics"]


def test_runtime_jsx_gate_hash_changes_without_stale_cache(tmp_path: Path) -> None:
    """Given changed JSX, when rechecked, then output reflects current bytes rather than cache."""
    entry = tmp_path / "entry.jsx"
    entry.write_text('export const View = () => <div data-version="one" />;\n', encoding="utf-8")
    first = _run("--json", "--entry", str(entry))
    entry.write_text('export const View = () => <div data-version="two" />;\n', encoding="utf-8")
    second = _run("--json", "--entry", str(entry))

    assert first.returncode == second.returncode == 0
    first_report = json.loads(first.stdout)
    second_report = json.loads(second.stdout)
    assert first_report["graph_hash"] != second_report["graph_hash"]


def test_harness_attributes_jsdom_virtual_console_errors() -> None:
    """Given a jsdom runtime error, when harness probes it, then exit zero is forbidden."""
    result = subprocess.run(
        [_node(), "track-z-harness.mjs", "--probe-jsdom-error"],
        cwd=WEBUI,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )

    assert result.returncode == 1, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["pass"] is False
    assert report["errorCount"] == 1
    assert "fault-injected jsdom error" in report["errors"][0]


def test_npm_safety_scripts_invoke_the_runtime_jsx_gate() -> None:
    """Given npm safety entrypoints, when inspected, then none can falsely green without JSX."""
    package = json.loads((WEBUI / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert scripts["runtime-jsx"] == "node runtime-jsx-check.mjs"
    for name in ("typecheck", "build", "harness"):
        assert "runtime-jsx" in scripts[name], f"npm run {name} bypasses the production JSX gate"
