from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

import pytest


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"
WEBUI = ROOT / "ai_strategy_loop" / "dashboard" / "webui-build"


class _BindingResult(TypedDict):
    listenerCount: int
    handled: int


class _CleanupResult(TypedDict):
    listenerCount: int


class _StatePayload(TypedDict):
    run_id: str
    status: str


class _ResolvedState(TypedDict):
    mode: str
    displayState: _StatePayload | None
    error: str
    loading: bool


class _HarnessResult(TypedDict):
    inactive: _BindingResult
    active: _BindingResult
    cleanup: _CleanupResult
    nestedEditable: bool
    plainEditable: bool
    archiveFailure: _ResolvedState
    archiveLoading: _ResolvedState
    archiveReady: _ResolvedState
    validTimestamp: int | None
    malformedTimestamp: int | None
    repeatedListenerCount: int


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_replay_remains_mounted_and_hidden_after_first_visit() -> None:
    # Given: the V4 shell source on the unchanged baseline.
    source = _read("dashboard-v4-shell.jsx")

    # When: the keep-alive render path is inspected.
    replay_mount = source.split("{/* Replay keep-alive", 1)[1].split("{activeTab === \"replay\" ? null", 1)[0]

    # Then: visitation gates mounting while activeTab only gates visibility.
    assert "replayVisited &&" in replay_mount
    assert 'display: activeTab === "replay" ? undefined : "none"' in replay_mount
    assert "setReplayVisited(true)" in source


def _run_helper_harness() -> _HarnessResult:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    helper = FRONTEND / "replay-lifecycle.jsx"
    script = r"""
const fs = require("fs");
const source = fs.readFileSync(process.argv[2], "utf8").replace(/^export\s*\{[^}]*\}\s*;?\s*$/gm, "");
const api = new Function(source + "; return {_bindReplayKeydown, _isReplayEditableTarget, _resolveReplayDisplayState, _exactReplayTimestamp};")();
const listeners = new Set();
const target = {
  addEventListener(type, fn) { if (type === "keydown") listeners.add(fn); },
  removeEventListener(type, fn) { if (type === "keydown") listeners.delete(fn); },
  dispatch(event) { for (const fn of [...listeners]) fn(event); },
};
let handled = 0;
const inactiveCleanup = api._bindReplayKeydown(false, target, () => { handled += 1; });
target.dispatch({ key: "ArrowRight" });
const inactive = { listenerCount: listeners.size, handled };
inactiveCleanup();
const activeCleanup = api._bindReplayKeydown(true, target, () => { handled += 1; });
target.dispatch({ key: "ArrowRight" });
const active = { listenerCount: listeners.size, handled };
activeCleanup();
const cleanup = { listenerCount: listeners.size };
for (let i = 0; i < 3; i += 1) {
  const dispose = api._bindReplayKeydown(true, target, () => { handled += 1; });
  dispose();
}
const repeatedListenerCount = listeners.size;
const nestedEditable = { tagName: "SPAN", isContentEditable: false, closest: (q) => q.includes("contenteditable") ? {} : null };
const plain = { tagName: "DIV", isContentEditable: false, closest: () => null };
const live = { run_id: "live-1", status: "running" };
const archiveFailure = api._resolveReplayDisplayState("archive-1", null, "HTTP 500", live);
const archiveLoading = api._resolveReplayDisplayState("archive-1", null, "", live);
const archiveReady = api._resolveReplayDisplayState("archive-1", { run_id: "archive-1", status: "completed" }, "", live);
console.log(JSON.stringify({ inactive, active, cleanup,
  nestedEditable: api._isReplayEditableTarget(nestedEditable),
  plainEditable: api._isReplayEditableTarget(plain),
  archiveFailure, archiveLoading, archiveReady,
  validTimestamp: api._exactReplayTimestamp(130000),
  malformedTimestamp: api._exactReplayTimestamp(126099), repeatedListenerCount }));
"""
    result = subprocess.run(
        [node, "-", str(helper)],
        input=script,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_hidden_replay_is_inert_and_receives_active_prop() -> None:
    # Given: the keep-alive Replay shell and wrapper.
    shell = _read("dashboard-v4-shell.jsx")
    replay = _read("v4-replay.jsx")

    # When: the hidden panel and prop chain are inspected.
    replay_mount = shell.split("{/* Replay keep-alive", 1)[1].split("{activeTab === \"replay\" ? null", 1)[0]

    # Then: hidden content is inert/ARIA-hidden and active reaches SimulationTab.
    assert 'aria-hidden={activeTab !== "replay"}' in replay_mount
    assert 'inert={activeTab === "replay" ? undefined : ""}' in replay_mount
    assert 'active={activeTab === "replay"}' in replay_mount
    assert "function V4Replay({ baseUrl, wsStatus, active })" in replay
    assert "<SimulationTab baseUrl={baseUrl} wsStatus={wsStatus} active={active}" in replay


def test_keyboard_binding_runtime_is_active_only_and_editable_safe() -> None:
    # Given: a real Node runtime loading the frontend lifecycle helper.
    data = _run_helper_harness()

    # When/Then: inactive mounts register nothing; active mounts dispatch once and clean up.
    assert data["inactive"] == {"listenerCount": 0, "handled": 0}
    assert data["active"] == {"listenerCount": 1, "handled": 1}
    assert data["cleanup"] == {"listenerCount": 0}
    assert data["repeatedListenerCount"] == 0
    assert data["nestedEditable"] is True
    assert data["plainEditable"] is False


def test_archive_failure_runtime_is_fail_closed_from_live_state() -> None:
    # Given: archive selection with live state present in the helper runtime.
    data = _run_helper_harness()

    # When/Then: failure/loading do not expose live payload under archive mode.
    failure = data["archiveFailure"]
    loading = data["archiveLoading"]
    ready = data["archiveReady"]
    assert failure["mode"] == "archive" and failure["displayState"] is None
    assert failure["error"] == "HTTP 500"
    assert loading["mode"] == "archive" and loading["displayState"] is None
    assert loading["loading"] is True
    ready_state = ready["displayState"]
    assert ready_state is not None
    assert ready_state["run_id"] == "archive-1"


def test_shell_renders_located_archive_error_without_live_fallback() -> None:
    # Given: a selected archive whose fetch may fail.
    source = _read("dashboard-v4-shell.jsx")

    # When/Then: explicit error state is rendered and display state is helper-resolved.
    assert "archiveLoadError" in source
    assert "_resolveReplayDisplayState" in source
    assert 'role="alert"' in source
    assert "아카이브 run 로드 실패" in source
    assert "(selectedRun && fetchedRunState) ? fetchedRunState : liveState" not in source


def test_seek_uses_exact_index_or_timestamp_without_hhmmss_arithmetic() -> None:
    # Given: Replay progress and signal seek paths.
    source = _read("sim-tab-root.jsx")

    # When/Then: slider intent is exact index, signal intent is exact timestamp.
    assert '_wsSend({ action: "seek_index", index: idx })' in source
    assert '_wsSend({ action: "seek", t: timestamp })' in source
    assert "approxT" not in source
    assert "hms - range[0]" not in source
    assert "range[1] - range[0]" not in source
    data = _run_helper_harness()
    assert data["validTimestamp"] == 130000
    assert data["malformedTimestamp"] is None
