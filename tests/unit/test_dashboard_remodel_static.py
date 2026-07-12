from __future__ import annotations

from pathlib import Path
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402



REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_reviewed_remodel_bundle_is_present() -> None:
    required = [
        "index.html",
        "styles/theme.css",
        "remodel-bootstrap.js",
        "src/data.js",
        "src/app.js",
        "data/stom-dummy-data.json",
        "CODEX_AGENT_BRIEF.md",
        "docs/TAB_CHECKLIST.md",
    ]
    for rel in required:
        assert (REMODEL / rel).is_file(), rel

def test_reviewed_remodel_route_is_served_by_dashboard_app() -> None:
    from ai_strategy_loop.dashboard.app import create_app

    client = authorized_dashboard_client(create_app())
    response = client.get("/ui/remodel/")
    assert response.status_code == 200
    assert "STOM AI · 조건식 AI 연구 대시보드" in response.text
    assert "rel=\"icon\"" in response.text

    script = client.get("/ui/remodel/src/app.js")
    assert script.status_code == 200
    assert "mapLoopState" in script.text


def test_reviewed_remodel_preserves_dashboard_information_architecture() -> None:
    app = _text(REMODEL / "src/app.js")
    for label in [
        "조건식 AI",
        "백테스트",
        "차트 리플레이",
        "프로세스",
        "히스토리",
        "연구실",
        "분석 워크벤치",
        "결정 감사",
        "Strategy Inspector",
        "Human Confirm",
        "Append-Only",
    ]:
        assert label in app

def test_reviewed_remodel_has_g003_adapter_controller_seams() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "const RemodelAdapters = {",
        "window.RemodelAdapters = RemodelAdapters",
        "const PageControllers = {",
        "window.PageControllers = PageControllers",
        "getViewModel: RemodelAdapters.overview",
        "getViewModel: RemodelAdapters.process",
        "getViewModel: RemodelAdapters.history",
        "getViewModel: RemodelAdapters.lab",
        "getViewModel: RemodelAdapters.workbench",
        "getViewModel: RemodelAdapters.audit",
        "PageControllers[state.sub] || PageControllers.overview",
    ]:
        assert marker in app

    for page_id, label in [
        ("overview", "조건식 AI"),
        ("process", "프로세스"),
        ("history", "히스토리"),
        ("lab", "연구실"),
        ("workbench", "분석 워크벤치"),
        ("audit", "결정 감사"),
    ]:
        assert f"id: '{page_id}'" in app
        assert f"label: '{label}'" in app


def test_reviewed_remodel_g003_provenance_and_live_payload_state() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "latestLoopPayload: null",
        "latestRunsPayload: null",
        "state.latestLoopPayload = payload",
        "state.latestRunsPayload = runsPayload",
        "reference fixture/static data",
        "demo fixture/static data",
        "backend-derived live payload",
        "backend loading/fallback with fixture baseline",
        "mode: modeLabel",
        "isReference:",
        "isLive:",
        "backendUrl:",
        "livePayloadStatus:",
        "provenanceCue(vm)",
        "source: ${escapeHtml(vm.source)}",
        "mode: ${escapeHtml(vm.mode)}",
        "Live payload",
        "Fixture/static",
        "Loading/fallback",
    ]:
        assert marker in app

    for renderer in [
        "function renderOverview(vm = RemodelAdapters.overview())",
        "function renderProcess(vm = RemodelAdapters.process())",
        "function renderHistory(vm = RemodelAdapters.history())",
        "function renderLab(vm = RemodelAdapters.lab())",
        "function renderWorkbench(vm = RemodelAdapters.workbench())",
        "function renderAudit(vm = RemodelAdapters.audit())",
    ]:
        assert renderer in app

def test_reviewed_remodel_g003_interactive_chart_primitives() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for marker in [
        "let chartRegistry = {};",
        "function registerChart(meta)",
        "function datumLabel(meta, index)",
        "function chartProvenance(opts = {})",
        "function chartStateBadges(opts = {}, diagnostics = {})",
        "function seriesDiagnostics(seriesList)",
        "class=\"chart-svg interactive-chart",
        "class=\"candle-chart interactive-chart",
        "data-chart-id=\"",
        "data-chart-count=\"",
        "data-legend-index=\"",
        "class=\"chart-active-datum\"",
        "function attachChartEvents()",
        "const setLegendHighlight = (seriesIndex) =>",
        "series-highlighted",
        "series-dimmed",
        "mousemove",
        "ArrowLeft",
        "ArrowRight",
        "Home",
        "End",
        "run_id=",
        "freshness=",
        "malformed=",
        "fixture fallback · backend not driving chart",
        "source: isLiveBackendMode ? 'fixture fallback · sim probe not driving chart' : 'reference replay fixture'",
    ]:
        assert marker in app

    for marker in [
        ".chart-tooltip",
        ".chart-tooltip.visible",
        ".chart-active-datum",
        ".chart-empty",
        ".chart-state-badges",
        ".chart-state-badge.warn",
        ".chart-crosshair-line",
        ".series-highlighted",
        ".series-dimmed",
        ".legend-item.active",
        ".candle-chart.interactive-chart",
    ]:
        assert marker in theme


def test_reviewed_remodel_g004_process_payload_cockpit() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")
    data = _text(REMODEL / "src/data.js")

    for marker in [
        "function adaptProcessFromLoopPayload(payload = {})",
        "backend /status process monitor",
        "const neutralPhase = /idle|stop|stopped|pause|paused|error|failed|unknown|none/.test(currentPhaseRaw);",
        "status: row.status === 'PENDING' ? 'PENDING' : 'UNKNOWN'",
        "state.processSelectedRunId = el.value; render();",
        "function normalizeProcessPayload(processData = {}, vm = {})",
        "function renderProcessStateStrip(model)",
        "function renderProcessRequiredFields(model)",
        "data-process-state=",
        "data-process-required=",
        "data-process-run-selector",
        "data-source-key=\"nodes\"",
        "data-source-key=\"queue\"",
        "data-source-key=\"workers\"",
        "data-source-key=\"contracts\"",
        "data-action=\"process-node\"",
        "data-process-drilldown",
        "Queue",
        "Workers",
        "Route Boundary Contract",
        "payload pending/fallback",
        "reference/demo honest fixture · not live",
        "openProcessNodeModal",
    ]:
        assert marker in app

    for marker in [
        ".process-state-strip",
        ".process-required-grid",
        ".process-required.bad",
        ".process-run-card",
        ".flow-node:focus",
        ".process-drilldown",
    ]:
        assert marker in theme

    for marker in [
        "\"runs\"",
        "\"queue\"",
        "\"workers\"",
        "\"contracts\"",
        "\"requiredFields\"",
        "\"selectedNodeId\"",
    ]:
        assert marker in data


def test_reviewed_remodel_has_live_backend_bridge_without_new_export_path() -> None:
    app = _text(REMODEL / "src/app.js")
    for marker in ["/health", "/status", "/runs", "/ws", "mapLoopState", "connectStateSocket"]:
        assert marker in app
    assert "refreshBackend().then(ok => { if (ok) connectStateSocket(); })" in app
    assert "백엔드 미연결 · 정적 프리뷰" in app
    assert "final_approval" not in app
    assert "자동 프로덕션 Export" not in app


def test_reviewed_remodel_fail_closed_mode_gate_markers() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "function detectRemodelMode()",
        "normalized === 'reference'",
        "DEMO_MODE_ALIASES",
        "'demo', 'fixture', 'static', '1', 'true'",
        "const isReferenceMode = remodelMode === 'reference'",
        "const isDemoMode = remodelMode === 'demo'",
        "const isLiveBackendMode = remodelMode === 'live'",
        "window.__STOM_REMODEL_MODE__",
        "window.__STOM_REMODEL_REFERENCE__",
    ]:
        assert marker in app


def test_reviewed_remodel_reference_and_demo_guard_side_effects() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "if (!isLiveBackendMode) return null;",
        "if (!isLiveBackendMode) return;",
        "if (!isLiveBackendMode) return Promise.reject(new Error('Backend disabled outside live mode'))",
        "if (!isLiveBackendMode) return Promise.resolve(false);",
        "if (!isLiveBackendMode) return;",
        "if (isReferenceMode) return;",
        "if (isDemoMode)",
        "if (isLiveBackendMode) reconnectBackend();",
        "if (isLiveBackendMode) state.runStatus = 'running';",
        "if (isLiveBackendMode) state.runStatus = 'stopping';",
        "writeStoredBaseUrl(state.baseUrl)",
        "new WebSocket(url)",
        "fetch(backendUrl(path)",
        "setTimeout(connectStateSocket, 3000)",
    ]:
        assert marker in app

    assert "localStorage.getItem('stom_remodel_base_url')" in app
    assert "localStorage.setItem('stom_remodel_base_url', value)" in app
    assert "Math.random" not in app
    assert "deterministicLineageValue" in app

def test_reviewed_remodel_g004_backtest_adapter_contract_matrix() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "const BacktestContracts = [",
        "const BacktestAdapter = {",
        "window.BacktestContracts = BacktestContracts",
        "window.BacktestAdapter = BacktestAdapter",
        "renderBacktestContractMatrix()",
        "Backtest API Contract Matrix",
        "BacktestAdapter.ensurePageEvidence()",
        "INERT_BACKTEST_STATUS",
    ]:
        assert marker in app

    for endpoint in [
        "/bt/health",
        "/bt/strategies?kind=buy",
        "/bt/strategies?kind=sell",
        "/bt/strategy?kind=&name=",
        "/bt/strategy/validate",
        "/bt/strategy",
        "/bt/strategy/delete",
        "/bt/extract_vars",
        "/bt/legacy/self_vars?kind=&name=",
        "/bt/backfinder/preflight?kind=&name=",
        "/bt/data_range",
        "/bt/run",
        "/bt/jobs",
        "/bt/job?job_id=",
        "/bt/job/cancel",
        "/bt/job/meta",
        "/bt/ws_job?job_id=",
        "/bt/result?job_id=__demo__",
        "/bt/evo_gens?run_id=",
        "/bt/analysis/montecarlo?job_id=__demo__&n=2000",
        "/bt/compare?job_a=&job_b=",
        "/bt/overlay?job_ids=",
        "/bt/portfolio",
        "/bt/report?job_id=",
    ]:
        assert endpoint in app


def test_reviewed_remodel_g004_backtest_reference_demo_are_inert() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "reference/demo inert · no fetch, no WebSocket, no extra localStorage",
        "if (!isLiveBackendMode) {",
        "BacktestContracts.forEach(c => markBacktestEvidence(c.id, 'INERT', INERT_BACKTEST_STATUS))",
        "Matrix is fixture/static only",
        "DEMO / REFERENCE INERT MODE",
    ]:
        assert marker in app

    assert "new WebSocket(`/bt/ws_job" not in app
    assert "new WebSocket(backendUrl('/bt/ws_job" not in app
    for forbidden in [
        'data-action="bt-run"',
        'data-action="bt-strategy-save"',
        'data-action="bt-strategy-delete"',
        'data-action="bt-job-cancel"',
        'data-action="bt-portfolio"',
        "fetchJson('/bt/run'",
        "fetchJson('/bt/strategy'",
        "fetchJson('/bt/job/cancel'",
        "fetchJson('/bt/portfolio'",
    ]:
        assert forbidden not in app


def test_reviewed_remodel_g004_backtest_live_reads_and_mutation_gates() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "livePath: '/bt/health'",
        "livePath: '/bt/strategies?kind=buy'",
        "livePath: '/bt/strategies?kind=sell'",
        "livePath: '/bt/jobs'",
        "livePath: '/bt/data_range'",
        "livePath: '/bt/result?job_id=__demo__'",
        "livePath: '/bt/analysis/montecarlo?job_id=__demo__&n=2000'",
        "fetchJson(`/bt/job?job_id=${jobId}`, 5000)",
        "function fetchText(path, timeoutMs = 4000)",
        "fetchText(`/bt/report?job_id=${jobId}`, 5000)",
        "fetchJson(`/bt/overlay?job_ids=${ids.map(encodeURIComponent).join(',')}`, 5000)",
        "fetchJson(`/bt/evo_gens?run_id=${encodeURIComponent(runIds[0])}`, 5000)",
        "fetchJson(`/bt/compare?job_a=${encodeURIComponent(ids[0])}&job_b=${encodeURIComponent(ids[1])}`, 5000)",
        "No existing job_id returned by /bt/jobs.",
        "No existing run_id returned by /bt/jobs.",
    ]:
        assert marker in app

    for reason in [
        "Mutates strategy storage; never auto-run from remodel load.",
        "Deletes strategy storage; destructive and manual-gated.",
        "Starts a backtest job; run creation must be explicit.",
        "Cancels active work; destructive and manual-gated.",
        "Mutates job metadata; not auto-invoked.",
        "Portfolio construction is a mutating/action endpoint; manual gate required.",
        "WebSocket/job stream is live-only and user-gated to avoid hidden long-lived connections.",
        "MANUAL-GATED",
        "mutating POST endpoints stay manual-gated/not-auto-invoked",
    ]:
        assert reason in app


def test_reviewed_remodel_g005_replay_adapter_contract_matrix() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "const ReplayContracts = [",
        "const ReplayAdapter = {",
        "window.ReplayContracts = ReplayContracts",
        "window.ReplayAdapter = ReplayAdapter",
        "renderReplayContractMatrix()",
        "Replay API/WS Contract Matrix",
        "ReplayAdapter.ensurePageEvidence()",
        "INERT_REPLAY_STATUS",
    ]:
        assert marker in app

    for contract in [
        "/sim/health",
        "/sim/days?src=min|tick",
        "/sim/demo?src=min&mode=latest",
        "/sim/stocks?date=&src=",
        "/bt/strategies?kind=buy",
        "/bt/strategies?kind=sell",
        "/sim/signals?date=&src=&code=&buy=&sell=",
        "/sim/ws",
        "start",
        "pause",
        "resume",
        "speed",
        "seek",
        "stop",
        "meta",
        "bars",
        "history",
        "done",
        "error",
    ]:
        assert contract in app


def test_reviewed_remodel_g005_replay_reference_demo_are_inert() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "reference/demo inert · no fetch, no /sim/ws, no extra localStorage beyond G002 baseline",
        "ReplayContracts.forEach(c => markReplayEvidence(c.id, 'INERT', INERT_REPLAY_STATUS))",
        "Replay API/WS Contract Matrix is fixture/static only",
        "DEMO / REFERENCE REPLAY INERT MODE",
        "Reference/demo inert",
        "DATA.shell.restHealth = 'INERT';",
        "DATA.shell.websocket = '정적 fixture';",
        "DATA.shell.runStatus = 'reference';",
        "data-inert-control=\"true\" disabled aria-disabled=\"true\"",
        "manualBtn('즉시 시작','primary', '', 'sim-start')",
    ]:
        assert marker in app

    assert "new WebSocket(`/sim/ws" not in app
    assert "new WebSocket(backendUrl('/sim/ws" not in app
    for forbidden in [
        'data-action="sim-ws-start"',
        'data-action="replay-live-order"',
        'data-action="broker-login"',
        "연결됨','green'],['프로토콜','WebSocket'],['서버','stom-ws.local:8081",
    ]:
        assert forbidden not in app


def test_reviewed_remodel_g005_replay_live_reads_and_ws_user_gate() -> None:
    app = _text(REMODEL / "src/app.js")

    for marker in [
        "livePath: '/sim/health'",
        "livePath: '/sim/days?src=min'",
        "livePath: '/sim/demo?src=min&mode=latest'",
        "livePath: '/bt/strategies?kind=buy'",
        "livePath: '/bt/strategies?kind=sell'",
        "fetchJson(`/sim/stocks?date=${encodeURIComponent(date)}&src=min`, 5000)",
        "fetchJson(`/sim/signals?date=${encodeURIComponent(date)}&src=min&code=${encodeURIComponent(code)}&buy=${encodeURIComponent(buy)}&sell=${encodeURIComponent(sell)}`, 5000)",
        "No date returned by /sim/demo?src=min&mode=latest.",
        "Need date, code, buy strategy, and sell strategy from live discovery before probing signals.",
        "LIVE mode: ReplayAdapter probes safe REST reads only; /sim/ws stays user-gated/manual",
        "USER-GATED",
        "/sim/ws is live-only and manual; ReplayAdapter never calls new WebSocket for this stream on page load.",
        "function readQueryBackendBase()",
        "new URLSearchParams((window.location && window.location.search) || '').get('backend')",
        "readQueryBackendBase() || readStoredBaseUrl() || DEFAULT_BACKEND_BASE",
        "data-manual-gate=\"${kind}\" title=\"Human-gated manual action; never runs on page load\"",
    ]:
        assert marker in app

    for recovery in [
        "Visible recovery path: show server error, keep chart fixture, and allow manual retry.",
        "awaiting ReplayAdapter evidence; failures stay visible with retry/manual recovery",
        "Live probe failure recovery: surface LIVE ERROR, preserve static replay chart, allow manual retry without fake success.",
        "Long-lived replay stream must not auto-open from page load.",
    ]:
        assert recovery in app

def test_reviewed_remodel_route_preserves_reference_query() -> None:
    app = _text(REMODEL / "src/app.js")

    assert "nextPath + window.location.search" in app
    assert "?demo=reference" not in app

def test_reviewed_remodel_safety_cues_and_forbidden_controls() -> None:
    app = _text(REMODEL / "src/app.js")
    for cue in [
        "실거래/주문 기능 없음",
        "브로커 로그인 없음",
        "계좌/자산 연동 없음",
        "Human Approval Gate",
        "Append-Only Audit",
        "연구 전용",
        "Strategy Inspector",
        "Winner 승인 / Export · Human Confirm",
        "Append-Only Ledger",
    ]:
        assert cue in app

    forbidden_control_patterns = [
        'data-action="live-order"',
        'data-action="broker-login"',
        'data-action="account-trade"',
        "주문 실행",
        "계좌 로그인",
        "브로커 로그인 버튼",
    ]
    for pattern in forbidden_control_patterns:
        assert pattern not in app


def test_reviewed_remodel_zip_prototype_is_the_active_entrypoint() -> None:
    index = _text(REMODEL / "index.html")
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    assert "/ui/remodel/styles/theme.css?v=20260628canonical" in index
    assert "/ui/remodel/src/data.js?v=20260628canonical" in index
    assert "/ui/remodel/src/app.js?v=20260628canonical" in index
    assert "/ui/bundle/app.js" not in index
    assert "remodel-production-shell" not in index

    for marker in ["routeToState", "pushRouteFromState", "chart-replay", "backtest", "workbench", "audit"]:
        assert marker in app
    assert ".app-shell" in theme
    assert ".overview-layout" in theme

def test_reviewed_remodel_g006_eight_page_ux_sweep_panels() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for page_id in [
        "condition",
        "process",
        "history",
        "lab",
        "workbench",
        "audit",
        "backtest",
        "replay",
    ]:
        assert f"data-testid=\"ux-sweep-${{escapeHtml(pageId)}}\"" in app
        assert page_id in app

    for marker in [
        "const UX_PAGE_STATES = {",
        "const UX_PAGE_WORKFLOWS = {",
        "function renderUxSweepPanel(pageId",
        "empty generation table",
        "loading live loop",
        "stale fallback",
        "malformed candle",
        "/sim/ws manual retry error",
        "responsive grid · no horizontal overflow target",
        "tooltip/crosshair/focus or accessible equivalent",
        "renderUxSweepPanel('condition'",
        "renderUxSweepPanel('process'",
        "renderUxSweepPanel('history'",
        "renderUxSweepPanel('lab'",
        "renderUxSweepPanel('workbench'",
        "renderUxSweepPanel('audit'",
        "renderUxSweepPanel('backtest'",
        "renderUxSweepPanel('replay'",
    ]:
        assert marker in app

    for css_marker in [
        ".ux-sweep-panel",
        ".ux-sweep-grid",
        ".ux-sweep-item",
        "@media (max-width: 1280px)",
        "@media (max-width: 760px)",
    ]:
        assert css_marker in theme

def test_reviewed_remodel_g002_shared_ia_and_backtest_task_flow() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for marker in [
        "function taskFrame(pageId, config)",
        "function compactSafetyStrip(pageId",
        "function evidenceDrawer(pageId",
        "data-ux-task-header=\"${escapeHtml(pageId)}\"",
        "data-ux-primary-canvas=\"backtest\"",
        "data-ux-evidence-drawer=\"${escapeHtml(pageId)}\"",
        "data-safety-boundary=\"${escapeHtml(pageId)}\"",
        "data-contract-marker=\"${escapeHtml(pageId)}-contract-evidence\"",
        "readonlyCodeEditor('매수 조건식 · Long Entry'",
        "readonlyCodeEditor('매도 조건식 · Exit/Short'",
        "data-backtest-step=\"select\"",
        "data-backtest-step=\"edit\"",
        "data-backtest-step=\"validate\"",
        "data-backtest-step=\"gated-run\"",
        "data-backtest-step=\"analyze\"",
        "data-backtest-validation-status",
        "Backtest API Contract Matrix / UX proof / 안전 GET 증거 열기",
        "V2의 큰 조건식 편집 장점을 계승",
        "/bt/* mutating endpoints are not auto-invoked",
        "지원 흐름: 실행 파라미터 · 최적화 · WFO · 스윕 · 조건식 편집 · 결과 분석 · 독립 HTML 보고서",
    ]:
        assert marker in app

    for marker in [
        ".task-frame",
        ".compact-safety-strip",
        ".evidence-drawer",
        ".backtest-task-layout",
        ".backtest-primary-canvas",
        ".condition-code-editor",
        ".backtest-analysis-grid .chart-svg.tall",
    ]:
        assert marker in theme

def test_reviewed_remodel_g003_chart_replay_task_flow() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for marker in [
        "taskFrame('chart_replay'",
        "data-ux-primary-canvas=\"chart_replay\"",
        "compactSafetyStrip('chart_replay'",
        "evidenceDrawer('chart_replay'",
        "data-replay-step=\"source\"",
        "data-replay-step=\"strategy\"",
        "data-replay-step=\"preview\"",
        "data-replay-step=\"manual-start\"",
        "data-replay-step=\"investigate\"",
        "data-replay-quick-start",
        "최근 거래일",
        "최대 상승일",
        "data-replay-playback-sticky",
        "data-replay-selected-bar",
        "data-replay-signal-log",
        "Replay API/WS Contract Matrix / UX proof / safe REST evidence 열기",
        "V2의 빠른 시작·날짜·종목·재생·타임라인 흐름",
        "/sim/ws never auto-opens",
        "data-heatmap-selected-narrative",
        "data-ux-heatmap",
        "data-heatmap-cell",
    ]:
        assert marker in app

    for marker in [
        ".replay-task-layout",
        ".replay-primary-canvas",
        ".replay-playback-sticky",
        ".replay-investigation-grid",
        ".replay-quick-start",
        ".primary-candle-card .candle-chart",
        ".heatmap-narrative",
    ]:
        assert marker in theme
def test_reviewed_remodel_g004_lab_condition_task_flow() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for marker in [
        "taskFrame('condition'",
        "data-ux-primary-canvas=\"condition\"",
        "compactSafetyStrip('condition'",
        "condition-primary-canvas",
        "조건식 AI · 현재 세대와 BEST 후보를 먼저 판단하는 V3",
        "Export와 Audit는 분리됩니다",
        "taskFrame('lab'",
        "data-ux-primary-canvas=\"lab\"",
        "compactSafetyStrip('lab'",
        "evidenceDrawer('lab'",
        "data-lab-step=\"heatmap\"",
        "data-lab-step=\"importance\"",
        "data-lab-step=\"holdout\"",
        "data-lab-selected-cell",
        "data-heatmap-selected-narrative",
        "data-heatmap-legend",
        "상관관계도 값 표시",
        "Lab evidence / UX proof / heatmap metadata 열기",
    ]:
        assert marker in app

    for marker in [
        ".condition-primary-canvas",
        ".condition-hero-grid",
        ".condition-chart-grid",
        ".lab-task-layout",
        ".lab-primary-canvas",
        ".lab-analysis-grid",
        ".lab-heatmap-card .heat-cell",
        ".heatmap-scale-legend",
        ".lab-secondary-grid",
    ]:
        assert marker in theme
def test_reviewed_remodel_g005_workbench_history_task_flow() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for marker in [
        "taskFrame('history'",
        "data-ux-primary-canvas=\"history\"",
        "compactSafetyStrip('history'",
        "evidenceDrawer('history'",
        "data-history-step=\"find\"",
        "data-history-step=\"inspect\"",
        "data-history-step=\"compare\"",
        "data-history-step=\"lineage\"",
        "히스토리 · 찾기/상세/비교/Lineage가 한 흐름인 V3",
        "ResultDetail",
        "Research Records",
        "taskFrame('workbench'",
        "data-ux-primary-canvas=\"workbench\"",
        "compactSafetyStrip('workbench'",
        "evidenceDrawer('workbench'",
        "data-workbench-step=\"select\"",
        "data-workbench-step=\"compare\"",
        "data-workbench-step=\"handoff\"",
        "data-workbench-candidate=",
        "History Compare",
        "Backtest Result Review",
        "Workbench evidence / candidate handoff metadata 열기",
    ]:
        assert marker in app

    for marker in [
        ".history-task-layout",
        ".history-primary-canvas",
        ".history-flow-grid",
        ".history-chart-grid",
        ".workbench-task-layout",
        ".workbench-primary-canvas",
        ".workbench-funnel-grid",
        ".workbench-compare-grid",
        ".workbench-secondary-grid",
    ]:
        assert marker in theme

def test_reviewed_remodel_g006_process_audit_task_flow() -> None:
    app = _text(REMODEL / "src/app.js")
    theme = _text(REMODEL / "styles/theme.css")

    for marker in [
        "taskFrame('process'",
        "data-ux-primary-canvas=\"process\"",
        "compactSafetyStrip('process'",
        "evidenceDrawer('process'",
        "data-process-step=\"select\"",
        "data-process-step=\"state\"",
        "data-process-step=\"map\"",
        "data-process-step=\"logs\"",
        "data-process-step=\"queue\"",
        "data-process-step=\"trend\"",
        "Process evidence / route contract drawer 열기",
        "taskFrame('audit'",
        "data-ux-primary-canvas=\"audit\"",
        "compactSafetyStrip('audit'",
        "evidenceDrawer('audit'",
        "data-audit-step=\"evidence\"",
        "data-audit-step=\"decision\"",
        "data-audit-step=\"ledger\"",
        "결정 감사 · Decision funnel과 Append-Only Ledger가 먼저 보이는 V3",
        "OOS 성과 차이 · Sharpe spark",
        "Audit evidence / OOS tables / ledger metadata 열기",
    ]:
        assert marker in app

    for marker in [
        ".process-task-layout",
        ".process-trend-grid",
        ".audit-task-layout",
        ".audit-primary-canvas",
        ".audit-funnel-grid",
        ".audit-step-card",
        ".audit-decision-options",
        ".audit-oos-ledger-grid",
    ]:
        assert marker in theme
def test_reviewed_remodel_g006_visual_gate_script_contract() -> None:
    script_path = REPO / "scripts" / "verify_dashboard_remodel_visual_gate.py"
    assert script_path.is_file()

    script = _text(script_path)

    for route_id in [
        "01_condition_ai_overview",
        "02_process",
        "03_history",
        "04_lab",
        "05_workbench",
        "06_decision_audit",
        "07_backtest",
        "08_chart_replay",
    ]:
        assert route_id in script
    assert 'f"{case.id}.png"' in script

    for route in [
        "/ui/remodel/condition?demo=reference",
        "/ui/remodel/process?demo=reference",
        "/ui/remodel/history?demo=reference",
        "/ui/remodel/lab?demo=reference",
        "/ui/remodel/workbench?demo=reference",
        "/ui/remodel/audit?demo=reference",
        "/ui/remodel/backtest?demo=reference",
        "/ui/remodel/chart-replay?demo=reference",
    ]:
        assert route in script

    for artifact in [
        "visual-gate-manifest.json",
        "scorecard.json",
        "side-by-side-contact-sheet.png",
        "source-safety-scan.json",
        "dom-safety-scan.json",
        "modal-coverage.json",
        "api-live-evidence.json",
    ]:
        assert artifact in script

    for marker in [
        "--min-page-score",
        "--min-average-score",
        "95.0",
        "97.0",
        "below_min_page_score",
        "below_min_average_score",
        "missing_required_safety_text",
        "forbidden_source_marker_present",
        "blank_or_unreadable_screenshot",
        "browser_console_errors",
        "browser_page_errors",
    ]:
        assert marker in script

    for safety_marker in [
        "No Live Order",
        "No Broker Login",
        "No Account Trading",
        "Research Only",
        "Human Approval Gate",
        "Append-Only Audit",
        'data-action="broker-login"',
        'data-action="replay-live-order"',
        "/sim/ws",
        "/bt/ws_job",
    ]:
        assert safety_marker in script

    for modal_marker in [
        "openSettingsModal",
        "openInspectorModal",
        "openApprovalModal",
        'data-action="settings"',
        'data-action="inspector"',
        'data-action="approval"',
        "modal_coverage_from_source_and_dom",
    ]:
        assert modal_marker in script

    for scoring_marker in [
        "pixelSimilarity",
        "rmseSimilarity",
        "histogramCosine",
        "dhashSimilarity",
        "edgeIoU",
        "weightedVisualParityScore",
        "totalCorrectedScore",
    ]:
        assert scoring_marker in script
