/*
  STOM AI · 조건식 AI 연구 대시보드
  Offline-first frontend prototype. No external libraries. No live order/broker/account controls.
*/
(function () {
  const DATA = window.STOM_DATA;
  const DEFAULT_BACKEND_BASE = (window.location && window.location.origin && window.location.origin.startsWith('http'))
    ? window.location.origin
    : 'http://127.0.0.1:8770';
  const DEMO_MODE_ALIASES = new Set(['demo', 'fixture', 'static', '1', 'true']);
  function detectRemodelMode() {
    const search = (window.location && window.location.search) || '';
    const demoValue = new URLSearchParams(search).get('demo');
    const normalized = String(demoValue || '').trim().toLowerCase();
    if (normalized === 'reference') return 'reference';
    if (DEMO_MODE_ALIASES.has(normalized)) return 'demo';
    return 'live';
  }
  const remodelMode = detectRemodelMode();
  const isReferenceMode = remodelMode === 'reference';
  const isDemoMode = remodelMode === 'demo';
  const isLiveBackendMode = remodelMode === 'live';
  window.__STOM_REMODEL_MODE__ = remodelMode;
  window.__STOM_REMODEL_REFERENCE__ = isReferenceMode;
  window.__STOM_REMODEL_LIVE_BACKEND__ = isLiveBackendMode;
  function readQueryBackendBase() {
    if (!isLiveBackendMode) return null;
    try {
      const value = new URLSearchParams((window.location && window.location.search) || '').get('backend');
      if (!value) return null;
      const parsed = new URL(value);
      if (!['http:', 'https:'].includes(parsed.protocol)) return null;
      if (!['127.0.0.1', 'localhost', '[::1]', '::1'].includes(parsed.hostname)) return null;
      return parsed.origin;
    } catch (_) { return null; }
  }
  function readStoredBaseUrl() {
    if (!isLiveBackendMode) return null;
    try { return localStorage.getItem('stom_remodel_base_url'); } catch (_) { return null; }
  }
  function writeStoredBaseUrl(value) {
    if (!isLiveBackendMode) return;
    try { localStorage.setItem('stom_remodel_base_url', value); } catch (_) {}
  }
  function modeBackendBase() {
    if (isReferenceMode || isDemoMode) return DATA.shell.backendUrl || DEFAULT_BACKEND_BASE;
    return readQueryBackendBase() || readStoredBaseUrl() || DEFAULT_BACKEND_BASE;
  }
  if (isReferenceMode) {
    DATA.shell.restHealth = 'INERT';
    DATA.shell.websocket = '정적 fixture';
    DATA.shell.runStatus = 'reference';
  }
  if (isDemoMode) {
    DATA.shell.restHealth = 'DEMO';
    DATA.shell.websocket = '정적 fixture';
    DATA.shell.runStatus = DATA.shell.runStatus || 'demo';
  }
  let stateSocket = null;
  let reconnectTimer = null;
  const app = document.getElementById('app');
  const modalRoot = document.getElementById('modal-root');
  const modeLabel = isReferenceMode ? 'REFERENCE' : isDemoMode ? 'DEMO' : 'LIVE';
  const state = {
    primary: 'condition',
    sub: 'overview',
    runStatus: DATA.shell.runStatus,
    liveMode: 'LIVE',
    codeTab: 'buy',
    baseUrl: modeBackendBase(),
    latestLoopPayload: null,
    latestRunsPayload: null,
    conditionDetailEvidence: {},
    conditionDetailPayloads: {},
    conditionDetailProbeStarted: false,
    conditionDetailProbeComplete: false,
    decisionAuditEvidence: {},
    decisionAuditPayloads: {},
    decisionAuditProbeStarted: false,
    decisionAuditProbeComplete: false,
    lastDecisionRecordStatus: null,
    processSelectedRunId: null,
  };
  const RemodelStatusVocabulary = [
    'reference',
    'demo',
    'live',
    'empty',
    'loading',
    'error',
    'stale',
    'requires-confirmation',
  ];
  const RemodelModuleMap = [
    { module: 'core/mode', owner: 'mode guard', surface: 'detectRemodelMode/readQueryBackendBase/modeBackendBase', nextUse: 'shared reference/demo/live behavior' },
    { module: 'core/api', owner: 'backend bridge', surface: 'backendUrl/fetchJson/fetchText', nextUse: 'safe REST reads and explicit mutation gates' },
    { module: 'core/state', owner: 'shell state', surface: 'state/PageControllers/routeToState', nextUse: 'cross-workflow handoff context' },
    { module: 'components/status', owner: 'status UI', surface: 'badge/provenanceCue/compactSafetyStrip', nextUse: 'empty/loading/error/stale/requires-confirmation states' },
    { module: 'components/layout', owner: 'layout UI', surface: 'panel/taskFrame/evidenceDrawer/table/chart', nextUse: 'consistent dense operational pages' },
    { module: 'pages/backtest', owner: 'BacktestAdapter', surface: 'BacktestContracts/renderBacktest', nextUse: 'V2 backtest preflight, run, job, result parity' },
    { module: 'pages/replay', owner: 'ReplayAdapter', surface: 'ReplayContracts/renderReplay', nextUse: 'V2 chart replay preflight, websocket, timeline parity' },
    { module: 'pages/condition-ai', owner: 'RemodelAdapters', surface: 'overview/lab/workbench renderers', nextUse: 'strategy code, diff, prompt, context, analytics APIs' },
    { module: 'pages/audit', owner: 'RemodelAdapters', surface: 'audit renderer/append-only cues', nextUse: 'decisions and record_decision append-only flow' },
  ];
  window.RemodelStatusVocabulary = RemodelStatusVocabulary;
  window.RemodelModuleMap = RemodelModuleMap;
  const ConditionDetailContracts = [
    { id: 'strategy-code', label: 'Strategy code', endpoint: '/strategy_code?run=&gen=', owner: 'ConditionDetailAdapter.strategyCode', emptyState: 'missing run/gen returns empty buy_code/sell_code', responseKeys: ['buy_code', 'sell_code', 'buy_name', 'sell_name'] },
    { id: 'strategy-diff', label: 'Previous diff', endpoint: '/strategy_diff?run_id=&gen_no=&base_gen=previous', owner: 'ConditionDetailAdapter.strategyDiff', emptyState: 'missing run/gen returns empty diff arrays', responseKeys: ['buy_diff', 'sell_diff', 'diff_status', 'reason'] },
    { id: 'prompts', label: 'Prompt timeline', endpoint: '/prompts?run_id=&gen_no=', owner: 'ConditionDetailAdapter.prompts', emptyState: 'no prompt rows is a valid empty inspector state', responseKeys: ['prompts', 'reason'] },
    { id: 'ai-context-pack', label: 'AI context pack', endpoint: '/ai_context_pack?run_id=&gen_no=', owner: 'ConditionDetailAdapter.aiContextPack', emptyState: 'missing context renders bounded read-only summary', responseKeys: ['context', 'items', 'reason'] },
    { id: 'backtest-detail', label: 'Backtest detail', endpoint: '/backtest_detail?run_id=&gen_no=', owner: 'ConditionDetailAdapter.backtestDetail', emptyState: 'missing result renders empty daily/cumulative/drawdown arrays', responseKeys: ['daily', 'cumulative', 'drawdown', 'summary'] },
  ];
  const BacktestContracts = [
    { id: 'bt-health', method: 'GET', endpoint: '/bt/health', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe read on Backtest page load', livePath: '/bt/health', safeAuto: true },
    { id: 'bt-strategies-buy', method: 'GET', endpoint: '/bt/strategies?kind=buy', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe read on Backtest page load', livePath: '/bt/strategies?kind=buy', safeAuto: true },
    { id: 'bt-strategies-sell', method: 'GET', endpoint: '/bt/strategies?kind=sell', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe read on Backtest page load', livePath: '/bt/strategies?kind=sell', safeAuto: true },
    { id: 'bt-strategy-detail', method: 'GET', endpoint: '/bt/strategy?kind=&name=', owner: 'BacktestAdapter.strategyDetailEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only after a strategy name is discovered', safeAuto: 'conditional' },
    { id: 'bt-strategy-validate', method: 'POST', endpoint: '/bt/strategy/validate', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Validation accepts user-authored strategy text; manual gate required.' },
    { id: 'bt-strategy-save', method: 'POST', endpoint: '/bt/strategy', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Mutates strategy storage; never auto-run from remodel load.' },
    { id: 'bt-strategy-delete', method: 'POST', endpoint: '/bt/strategy/delete', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Deletes strategy storage; destructive and manual-gated.' },
    { id: 'bt-extract-vars', method: 'POST', endpoint: '/bt/extract_vars', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Reads submitted code body; user action only, no automatic payload fabrication.' },
    { id: 'bt-legacy-self-vars', method: 'GET', endpoint: '/bt/legacy/self_vars?kind=&name=', owner: 'BacktestAdapter.strategyDetailEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only after a strategy name is discovered', safeAuto: 'conditional' },
    { id: 'bt-backfinder-preflight', method: 'GET', endpoint: '/bt/backfinder/preflight?kind=&name=', owner: 'BacktestAdapter.strategyDetailEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only after a strategy name is discovered', safeAuto: 'conditional' },
    { id: 'bt-data-range', method: 'GET', endpoint: '/bt/data_range', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe read on Backtest page load', livePath: '/bt/data_range', safeAuto: true },
    { id: 'bt-run', method: 'POST', endpoint: '/bt/run', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Starts a backtest job; run creation must be explicit.' },
    { id: 'bt-jobs', method: 'GET', endpoint: '/bt/jobs', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe read on Backtest page load', livePath: '/bt/jobs', safeAuto: true },
    { id: 'bt-job', method: 'GET', endpoint: '/bt/job?job_id=', owner: 'BacktestAdapter.jobEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only when an existing job_id is available', safeAuto: 'conditional' },
    { id: 'bt-job-cancel', method: 'POST', endpoint: '/bt/job/cancel', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Cancels active work; destructive and manual-gated.' },
    { id: 'bt-job-meta', method: 'POST', endpoint: '/bt/job/meta', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Mutates job metadata; not auto-invoked.' },
    { id: 'bt-ws-job', method: 'GET', endpoint: '/bt/ws_job?job_id=', owner: 'Manual live observer action', modeBehavior: 'reference/demo inert fixture · live WS/read stream not opened automatically', reason: 'WebSocket/job stream is live-only and user-gated to avoid hidden long-lived connections.' },
    { id: 'bt-result-demo', method: 'GET', endpoint: '/bt/result?job_id=__demo__', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe demo read on Backtest page load', livePath: '/bt/result?job_id=__demo__', safeAuto: true },
    { id: 'bt-evo-gens', method: 'GET', endpoint: '/bt/evo_gens?run_id=', owner: 'BacktestAdapter.jobEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only when an existing run_id is available', safeAuto: 'conditional' },
    { id: 'bt-montecarlo-demo', method: 'GET', endpoint: '/bt/analysis/montecarlo?job_id=__demo__&n=2000', owner: 'BacktestAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe demo analysis read on Backtest page load', livePath: '/bt/analysis/montecarlo?job_id=__demo__&n=2000', safeAuto: true },
    { id: 'bt-compare', method: 'GET', endpoint: '/bt/compare?job_a=&job_b=', owner: 'BacktestAdapter.jobEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only when two existing job ids are available', safeAuto: 'conditional' },
    { id: 'bt-overlay', method: 'GET', endpoint: '/bt/overlay?job_ids=', owner: 'BacktestAdapter.jobEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only when existing job ids are available', safeAuto: 'conditional' },
    { id: 'bt-portfolio', method: 'POST', endpoint: '/bt/portfolio', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live not auto-invoked', reason: 'Portfolio construction is a mutating/action endpoint; manual gate required.' },
    { id: 'bt-report', method: 'GET', endpoint: '/bt/report?job_id=', owner: 'BacktestAdapter.jobEvidence', modeBehavior: 'reference/demo inert fixture · live optional read only when an existing job_id is available', safeAuto: 'conditional' }
  ];
  const INERT_BACKTEST_STATUS = 'reference/demo inert · no fetch, no WebSocket, no extra localStorage';
  state.backtestContractEvidence = {};
  state.backtestProbeStarted = false;
  state.backtestProbeComplete = false;
  state.backtestExistingJobIds = [];
  state.backtestExistingRunIds = [];

  const ReplayContracts = [
    { id: 'sim-health', kind: 'REST endpoint', method: 'GET', endpoint: '/sim/health', owner: 'ReplayAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe read on Chart Replay page load', livePath: '/sim/health', safeAuto: true },
    { id: 'sim-days-min', kind: 'REST endpoint', method: 'GET', endpoint: '/sim/days?src=min|tick', owner: 'ReplayAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe min-days read on Chart Replay page load', livePath: '/sim/days?src=min', safeAuto: true },
    { id: 'sim-demo-latest', kind: 'REST endpoint', method: 'GET', endpoint: '/sim/demo?src=min&mode=latest', owner: 'ReplayAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe demo discovery read on Chart Replay page load', livePath: '/sim/demo?src=min&mode=latest', safeAuto: true },
    { id: 'sim-stocks', kind: 'REST endpoint', method: 'GET', endpoint: '/sim/stocks?date=&src=', owner: 'ReplayAdapter.discoveryEvidence', modeBehavior: 'reference/demo inert fixture · live conditional read only after demo date is discovered', safeAuto: 'conditional' },
    { id: 'bt-replay-strategies-buy', kind: 'REST endpoint', method: 'GET', endpoint: '/bt/strategies?kind=buy', owner: 'ReplayAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe buy strategy read on Chart Replay page load', livePath: '/bt/strategies?kind=buy', safeAuto: true },
    { id: 'bt-replay-strategies-sell', kind: 'REST endpoint', method: 'GET', endpoint: '/bt/strategies?kind=sell', owner: 'ReplayAdapter.readOnlyProbe', modeBehavior: 'reference/demo inert fixture · live safe sell strategy read on Chart Replay page load', livePath: '/bt/strategies?kind=sell', safeAuto: true },
    { id: 'sim-signals', kind: 'REST endpoint', method: 'GET', endpoint: '/sim/signals?date=&src=&code=&buy=&sell=', owner: 'ReplayAdapter.discoveryEvidence', modeBehavior: 'reference/demo inert fixture · live conditional read only after demo date/code and buy/sell names are discovered', safeAuto: 'conditional' },
    { id: 'sim-ws', kind: 'WS endpoint', method: 'WS', endpoint: '/sim/ws', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live-only WebSocket never auto-opened; user-gated manual start', reason: 'Long-lived replay stream must not auto-open from page load.' },
    { id: 'ws-action-start', kind: 'WS action', method: 'ACTION', endpoint: 'start', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live user-gated /sim/ws action', reason: 'Starts a replay stream; explicit user action required.' },
    { id: 'ws-action-pause', kind: 'WS action', method: 'ACTION', endpoint: 'pause', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live user-gated /sim/ws action', reason: 'Pauses an existing replay stream only after manual connection.' },
    { id: 'ws-action-resume', kind: 'WS action', method: 'ACTION', endpoint: 'resume', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live user-gated /sim/ws action', reason: 'Resumes an existing replay stream only after manual connection.' },
    { id: 'ws-action-speed', kind: 'WS action', method: 'ACTION', endpoint: 'speed', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live user-gated /sim/ws action', reason: 'Changes replay speed on a manual session only.' },
    { id: 'ws-action-seek', kind: 'WS action', method: 'ACTION', endpoint: 'seek', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live user-gated /sim/ws action', reason: 'Moves replay cursor on a manual session only.' },
    { id: 'ws-action-stop', kind: 'WS action', method: 'ACTION', endpoint: 'stop', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture · live user-gated /sim/ws action', reason: 'Stops a manual replay session; no hidden stream control.' },
    { id: 'ws-message-meta', kind: 'WS message', method: 'MESSAGE', endpoint: 'meta', owner: 'ReplayAdapter.protocolMatrix', modeBehavior: 'reference/demo inert fixture · live protocol message documented; no fake stream success', reason: 'Server metadata frame expected after manual /sim/ws start.' },
    { id: 'ws-message-bars', kind: 'WS message', method: 'MESSAGE', endpoint: 'bars', owner: 'ReplayAdapter.protocolMatrix', modeBehavior: 'reference/demo inert fixture · live protocol message documented; no fake stream success', reason: 'Bar batch frame expected during manual replay.' },
    { id: 'ws-message-history', kind: 'WS message', method: 'MESSAGE', endpoint: 'history', owner: 'ReplayAdapter.protocolMatrix', modeBehavior: 'reference/demo inert fixture · live protocol message documented; no fake stream success', reason: 'History/bootstrap frame expected during manual replay.' },
    { id: 'ws-message-done', kind: 'WS message', method: 'MESSAGE', endpoint: 'done', owner: 'ReplayAdapter.protocolMatrix', modeBehavior: 'reference/demo inert fixture · live protocol message documented; no fake stream success', reason: 'Terminal completion frame for manual replay.' },
    { id: 'ws-message-error', kind: 'WS message', method: 'MESSAGE', endpoint: 'error', owner: 'ReplayAdapter.protocolMatrix', modeBehavior: 'reference/demo inert fixture · live protocol message documented; no fake stream success', reason: 'Visible recovery path: show server error, keep chart fixture, and allow manual retry.' }
  ];
  const INERT_REPLAY_STATUS = 'reference/demo inert · no fetch, no /sim/ws, no extra localStorage beyond G002 baseline';
  state.replayContractEvidence = {};
  state.replayProbeStarted = false;
  state.replayProbeComplete = false;
  state.replayDiscoveredDate = '';
  state.replayDiscoveredCode = '';
  state.replayDiscoveredBuy = '';
  state.replayDiscoveredSell = '';
  const routeToState = {
    condition: ['condition', 'overview'],
    evolution: ['condition', 'overview'],
    process: ['condition', 'process'],
    history: ['condition', 'history'],
    records: ['condition', 'history'],
    lab: ['condition', 'lab'],
    workbench: ['condition', 'workbench'],
    audit: ['condition', 'audit'],
    verdict: ['condition', 'audit'],
    backtest: ['backtest', 'overview'],
    bt: ['backtest', 'overview'],
    replay: ['replay', 'overview'],
    simulation: ['replay', 'overview'],
    'chart-replay': ['replay', 'overview'],
  };
  const conditionRouteBySub = {
    overview: 'condition',
    process: 'process',
    history: 'history',
    lab: 'lab',
    workbench: 'workbench',
    audit: 'audit',
  };

  function applyRouteFromLocation() {
    const path = (window.location && window.location.pathname) || '';
    const leaf = decodeURIComponent(path.replace(/\/+$/, '').split('/').pop() || 'condition');
    const mapped = routeToState[leaf] || routeToState.condition;
    state.primary = mapped[0];
    state.sub = mapped[1] || 'overview';
  }

  function remodelPathForState() {
    const leaf = state.primary === 'backtest'
      ? 'backtest'
      : state.primary === 'replay'
        ? 'chart-replay'
        : (conditionRouteBySub[state.sub] || 'condition');
    return `/ui/remodel/${leaf}`;
  }

  function pushRouteFromState() {
    if (!window.history || !window.location) return;
    const nextPath = remodelPathForState();
    if (window.location.pathname !== nextPath) {
      window.history.pushState({ primary: state.primary, sub: state.sub }, '', nextPath + window.location.search);
    }
  }

  applyRouteFromLocation();
  window.addEventListener('popstate', () => { applyRouteFromLocation(); render(); });

  const primaryTabs = [
    { id: 'condition', label: '조건식 AI' },
    { id: 'backtest', label: '백테스트' },
    { id: 'replay', label: '차트 리플레이' }
  ];
  const subTabs = [
    { id: 'overview', label: '조건식 AI' },
    { id: 'process', label: '프로세스' },
    { id: 'history', label: '히스토리' },
    { id: 'lab', label: '연구실' },
    { id: 'workbench', label: '분석 워크벤치' },
    { id: 'audit', label: '결정 감사' }
  ];
  const REMODEL_WORKFLOW_STEPS = [
    { id: 'overview', label: 'Overview', route: '/ui/remodel/condition', primary: 'condition', sub: 'overview', tone: 'blue' },
    { id: 'condition', label: 'Condition AI', route: '/ui/remodel/workbench', primary: 'condition', sub: 'workbench', tone: 'violet' },
    { id: 'backtest', label: 'Backtest', route: '/ui/remodel/backtest', primary: 'backtest', sub: 'overview', tone: 'green' },
    { id: 'replay', label: 'Chart Replay', route: '/ui/remodel/chart-replay', primary: 'replay', sub: 'overview', tone: 'cyan' },
    { id: 'audit', label: 'Audit/Decision', route: '/ui/remodel/audit', primary: 'condition', sub: 'audit', tone: 'amber' },
    { id: 'settings', label: 'Settings', route: 'settings-modal', primary: 'settings', sub: 'settings', tone: 'blue', action: 'settings' },
  ];

  const colors = ['var(--green-2)', 'var(--blue)', 'var(--violet)', 'var(--amber)', 'var(--red)', 'var(--cyan)', 'var(--orange)'];

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m]));
  }
  function cls(status) {
    const s = String(status).toLowerCase();
    if (s.includes('pass') || s.includes('통과') || s.includes('완료') || s.includes('up') || s.includes('ok') || s.includes('healthy')) return 'green';
    if (s.includes('reject') || s.includes('실패') || s.includes('거부') || s.includes('error') || s.includes('손실')) return 'red';
    if (s.includes('run') || s.includes('진행') || s.includes('대기') || s.includes('보완') || s.includes('hold')) return 'amber';
    if (s.includes('winner') || s.includes('우승')) return 'violet';
    return 'blue';
  }
  function badge(label, type = '') {
    return `<span class="badge ${type || cls(label)}"><span class="dot ${type || cls(label)}"></span>${escapeHtml(label)}</span>`;
  }
  function btn(label, className = '', attrs = '') {
    return `<button class="btn ${className}" ${attrs}>${label}</button>`;
  }
  function manualGateAttrs(kind = 'manual-action') {
    if (isLiveBackendMode) return `data-manual-gate="${kind}" title="Human-gated manual action; never runs on page load"`;
    return `data-manual-gate="${kind}" data-inert-control="true" disabled aria-disabled="true" title="Reference/demo mode is static and inert; no backend request is sent"`;
  }
  function manualBtn(label, className = '', attrs = '', kind = 'manual-action') {
    return btn(label, className, `${attrs} ${manualGateAttrs(kind)}`.trim());
  }
  function metricCard(label, value, desc = '', tone = '') {
    return `<div class="panel kpi-card"><div class="kpi-label"><span>${escapeHtml(label)}</span></div><div class="card-value ${tone}">${escapeHtml(value)}</div>${desc ? `<div class="kpi-desc">${escapeHtml(desc)}</div>` : ''}</div>`;
  }
  function panel(title, body, opts = {}) {
    const sub = opts.sub ? `<span class="panel-title-sub">${opts.sub}</span>` : '';
    const action = opts.action || '';
    return `<section class="panel ${opts.className || ''}"><div class="panel-header"><span>${title}${sub ? ' ' + sub : ''}</span>${action}</div><div class="panel-body">${body}</div></section>`;
  }
  function infoList(rows) {
    return `<div class="info-list">${rows.map(r => `<div class="info-row"><span class="label">${escapeHtml(r[0])}</span><span class="value ${r[2] || ''}">${escapeHtml(r[1])}</span></div>`).join('')}</div>`;
  }
  const UX_PAGE_KEY_ALIASES = {
    chart_replay: 'replay',
  };
  function functionalStateStrip(pageId, config = {}) {
    const uxKey = UX_PAGE_KEY_ALIASES[pageId] || pageId;
    const pageStates = UX_PAGE_STATES[uxKey] || [];
    const configState = String(config.state || '').toLowerCase();
    const tokens = RemodelStatusVocabulary.map(status => {
      const active = status === remodelMode || configState.includes(status) || (status === 'requires-confirmation' && String(config.risk || '').toLowerCase().includes('manual-gated'));
      return `<span class="state-token ${active ? 'active' : ''}" data-state-token="${escapeHtml(status)}">${escapeHtml(status)}</span>`;
    }).join('');
    const chips = pageStates.slice(0, 5).map(item => `<span class="page-state-chip">${escapeHtml(item)}</span>`).join('');
    return `<div class="functional-state-strip" data-functional-state-strip="${escapeHtml(pageId)}" data-state-vocabulary="${escapeHtml(RemodelStatusVocabulary.join('|'))}"><div class="state-token-row">${tokens}</div><div class="page-state-row">${chips}</div></div>`;
  }
  function workflowStepForState() {
    if (state.primary === 'backtest') return 'backtest';
    if (state.primary === 'replay') return 'replay';
    if (state.sub === 'audit') return 'audit';
    if (state.sub === 'overview') return 'overview';
    return 'condition';
  }
  function currentWorkflowContext(input = {}) {
    const detail = conditionDetailContext(input);
    const decisionPayload = state.decisionAuditPayloads.decisions || {};
    const latestDecision = (firstArray(decisionPayload, ['decisions', 'items', 'rows'])[0] || (DATA.audit.ledger || [])[0] || {});
    const selected = detail.selected || {};
    const strategy = String(input.strategy || selected.buy_name || selected.buy || DATA.overview.activeStrategy.name || BACKTEST_PREFLIGHT_DEFAULTS.buy || '').trim();
    const date = String(input.date || REPLAY_PREFLIGHT_DEFAULTS.date || '20250516').trim();
    const code = String(input.code || REPLAY_PREFLIGHT_DEFAULTS.code || ((DATA.replay.stocks || [])[0] || {}).code || '').trim();
    const decision = String(input.decision || latestDecision.verdict || latestDecision.decision || 'hold').trim();
    return {
      run_id: String(input.run_id ?? input.runId ?? detail.run_id ?? DATA.shell.runId ?? '').trim(),
      gen_no: intOrDefault(input.gen_no ?? input.genNo ?? detail.gen_no, -1),
      strategy,
      date,
      code,
      decision,
      workflow_step: workflowStepForState(),
      ready: Boolean(detail.run_id && strategy),
    };
  }
  function renderSharedContextStrip(context = currentWorkflowContext()) {
    const runGen = `${context.run_id || 'missing'} / gen ${context.gen_no >= 0 ? context.gen_no : 'missing'}`;
    const symbolDate = `${context.code || 'symbol'} / ${context.date || 'date'}`;
    return `<div class="shared-context-strip" data-shared-context-strip data-workflow-context="${escapeHtml(context.workflow_step)}">
      <span class="context-chip" data-context-run-gen><b>run/gen</b><span>${escapeHtml(runGen)}</span></span>
      <span class="context-chip" data-context-strategy><b>strategy</b><span>${escapeHtml(context.strategy || 'missing')}</span></span>
      <span class="context-chip" data-context-symbol-date><b>symbol/date</b><span>${escapeHtml(symbolDate)}</span></span>
      <span class="context-chip" data-context-decision><b>decision</b><span>${escapeHtml(context.decision || 'hold')}</span></span>
    </div>`;
  }
  function renderWorkflowRail() {
    const active = workflowStepForState();
    return `<nav class="workflow-rail" data-workflow-rail aria-label="V3 workflow">
      ${REMODEL_WORKFLOW_STEPS.map((step, index) => {
        const isActive = active === step.id;
        const attrs = step.action === 'settings'
          ? 'data-workflow-action="settings"'
          : `data-workflow-primary="${escapeHtml(step.primary)}" data-workflow-sub="${escapeHtml(step.sub || 'overview')}" data-workflow-route="${escapeHtml(step.route)}"`;
        return `<button class="workflow-step ${isActive ? 'active' : ''}" data-workflow-step="${escapeHtml(step.id)}" ${attrs} aria-current="${isActive ? 'step' : 'false'}">
          <span>${index + 1}</span><b>${escapeHtml(step.label)}</b><small>${escapeHtml(step.route)}</small>
        </button>`;
      }).join('')}
    </nav>`;
  }
  window.RemodelWorkflowUX = {
    steps: REMODEL_WORKFLOW_STEPS,
    workflowStepForState,
    currentWorkflowContext,
    renderWorkflowRail,
    renderSharedContextStrip,
  };
  function taskFrame(pageId, config) {
    const fields = [
      ['purpose', config.purpose],
      ['state', config.state],
      ['primary-action', config.primaryAction],
      ['risk', config.risk],
      ['mode', `${modeLabel} · ${isLiveBackendMode ? 'live safe-read' : 'reference/demo inert'}`],
    ];
    const action = config.actionKind
      ? manualBtn(config.actionLabel || config.primaryAction, 'primary small', `data-ux-primary-action="${escapeHtml(config.actionKind)}"`, config.actionKind)
      : '';
    return `<section class="panel task-frame" data-ux-task-header="${escapeHtml(pageId)}">
      <div class="task-frame-copy">
        <span class="badge blue">Task-first V3</span>
        <h2>${escapeHtml(config.title)}</h2>
        <p>${escapeHtml(config.summary)}</p>
        ${functionalStateStrip(pageId, config)}
      </div>
      <div class="task-frame-fields">
        ${fields.map(([key, value]) => `<div class="task-field" data-ux-field="${escapeHtml(key)}"><span>${escapeHtml(key)}</span><b>${escapeHtml(value)}</b></div>`).join('')}
      </div>
      ${action ? `<div class="task-frame-action" data-primary-action-slot>${action}</div>` : ''}
    </section>`;
  }
  function compactSafetyStrip(pageId, notes = []) {
    const items = [
      ['No Live Order', '실거래 주문 없음'],
      ['No Broker Login', '브로커 로그인 없음'],
      ['No Account Trading', '계좌/자산 연동 없음'],
      ['Research Only', '연구 전용'],
      ['Human Approval Gate', '수동 승인 게이트'],
      ['Append-Only Audit', '불변 감사'],
    ];
    const noteHtml = notes.length ? `<span class="compact-safety-note">${notes.map(escapeHtml).join(' · ')}</span>` : '';
    return `<div class="compact-safety-strip" data-safety-boundary="${escapeHtml(pageId)}">
      ${items.map(([label, desc]) => `<span class="compact-safety-item"><b>${escapeHtml(label)}</b><small>${escapeHtml(desc)}</small></span>`).join('')}
      ${noteHtml}
    </div>`;
  }
  function evidenceDrawer(pageId, summary, body) {
    return `<details class="evidence-drawer" data-ux-evidence-drawer="${escapeHtml(pageId)}">
      <summary><span>${escapeHtml(summary)}</span>${badge('contract markers preserved', 'blue')}</summary>
      <div class="evidence-drawer-body" data-contract-marker="${escapeHtml(pageId)}-contract-evidence">${body}</div>
    </details>`;
  }
  function readonlyCodeEditor(label, code, attrs = '') {
    return `<label class="condition-editor-label"><span>${escapeHtml(label)}</span><textarea class="condition-code-editor" readonly aria-readonly="true" spellcheck="false" ${attrs}>${escapeHtml(code)}</textarea></label>`;
  }

  function livePayloadLabel(kind) {
    if (kind === 'runs') return state.latestRunsPayload ? 'runs payload stored' : 'runs pending/fallback';
    return state.latestLoopPayload ? 'loop payload stored' : 'loop pending/fallback';
  }

  function provenanceFor(pageId, label, data, summary = {}) {
    const hasLoop = !!state.latestLoopPayload;
    const hasRuns = !!state.latestRunsPayload;
    const liveEvidence = pageId === 'history' ? hasRuns : hasLoop;
    const referenceSource = isReferenceMode ? 'reference fixture/static data' : 'demo fixture/static data';
    const source = isLiveBackendMode
      ? (liveEvidence ? 'backend-derived live payload' : 'backend loading/fallback with fixture baseline')
      : referenceSource;
    return {
      pageId,
      label,
      source,
      mode: modeLabel,
      isReference: isReferenceMode,
      isDemo: isDemoMode,
      isFixture: isReferenceMode || isDemoMode,
      isLive: isLiveBackendMode && liveEvidence,
      backendUrl: state.baseUrl || DATA.shell.backendUrl || DEFAULT_BACKEND_BASE,
      livePayloadStatus: livePayloadLabel(pageId === 'history' ? 'runs' : 'loop'),
      runsStatus: livePayloadLabel('runs'),
      data,
      summary
    };
  }

  function adaptProcessFromLoopPayload(payload = {}) {
    const fixture = DATA.process || {};
    const gens = Array.isArray(payload.generations) ? payload.generations : [];
    const latest = payload.latest || {};
    const maxGen = Math.max(1, numberOr(payload.max_generations, gens.length || 1));
    const currentGen = Math.max(0, numberOr(payload.current_gen, gens.length ? gens[gens.length - 1].gen_no : 0));
    const passCount = gens.filter(g => g && g.gate_passed).length;
    const failedCount = gens.filter(g => g && g.gate_passed === false).length;
    const progress = Math.max(0, Math.min(1, currentGen / maxGen));
    const currentPhaseRaw = String(latest.phase || payload.status || 'generation').toLowerCase();
    const neutralPhase = /idle|stop|stopped|pause|paused|error|failed|unknown|none/.test(currentPhaseRaw);
    const completePhase = /done|complete|completed/.test(currentPhaseRaw);
    const phaseIndex = neutralPhase ? 0 : completePhase ? 6 : currentPhaseRaw.includes('back') ? 2 : currentPhaseRaw.includes('score') || currentPhaseRaw.includes('rank') ? 3 : currentPhaseRaw.includes('auto') || currentPhaseRaw.includes('analysis') ? 4 : currentPhaseRaw.includes('repeat') ? 5 : 1;
    const statusFor = index => phaseIndex <= 0 ? '대기' : index < phaseIndex ? '완료' : index === phaseIndex ? '진행 중' : '대기';
    const now = new Date().toISOString();
    const message = latest.message || payload.message || payload.status || 'backend /status payload received';
    const runId = payload.run_id || DATA.shell.runId || 'live-status-run';
    return {
      kpis: [
        ['현재 세대', `${currentGen} / ${maxGen}`],
        ['진행률', `${Math.round(progress * 1000) / 10}%`],
        ['게이트 통과', String(passCount)],
        ['실패/거부', String(failedCount)],
        ['전략 수', String(gens.length)],
        ['상태', payload.status || 'live'],
        ['프로바이더', payload.provider || DATA.shell.provider || 'backend'],
        ['TF', payload.bt_timeframe || DATA.shell.timeframe || '—']
      ],
      nodes: [
        { id: 1, title: 'Generation', status: statusFor(1), desc: 'backend /status generations', time: latest.generation_elapsed || 'live', items: gens.length },
        { id: 2, title: 'Backtest', status: statusFor(2), desc: 'latest checkpoint validation', time: latest.backtest_elapsed || 'live', items: latest.backtest_count || gens.length },
        { id: 3, title: 'Scoring', status: statusFor(3), desc: 'gate and score aggregation', time: latest.scoring_elapsed || 'live', items: passCount },
        { id: 4, title: 'Autopsy', status: statusFor(4), desc: 'risk/autopsy monitor', time: latest.autopsy_elapsed || 'live', items: latest.autopsy_count || failedCount },
        { id: 5, title: 'Repeat', status: statusFor(5), desc: 'next generation scheduling', time: latest.repeat_eta || 'pending', items: Math.max(0, maxGen - currentGen) }
      ],
      logs: [
        `${now} INFO [Process] ${message}`,
        `${now} INFO [Process] run_id=${runId}`,
        `${now} INFO [Process] current_gen=${currentGen} max_gen=${maxGen}`,
        `${now} INFO [Process] gate_passed=${passCount} failed=${failedCount}`,
        `${now} INFO [Process] provider=${payload.provider || DATA.shell.provider || 'unknown'} tf=${payload.bt_timeframe || DATA.shell.timeframe || 'unknown'}`
      ],
      runs: [
        { id: runId, status: String(payload.status || 'LIVE').toUpperCase(), phase: latest.phase || payload.status || 'live', progress, updatedAt: now, source: 'backend /status process monitor' }
      ],
      queue: [
        { name: 'generation', queued: Math.max(0, maxGen - currentGen), running: statusFor(1) === '진행 중' ? 1 : 0, done: currentGen, error: 0 },
        { name: 'backtest', queued: 0, running: statusFor(2) === '진행 중' ? 1 : 0, done: gens.length, error: 0 },
        { name: 'autopsy', queued: failedCount, running: statusFor(4) === '진행 중' ? 1 : 0, done: passCount, error: failedCount }
      ],
      workers: [
        { id: 'loop-status', node: latest.phase || 'Loop', status: payload.status || 'live', heartbeat: now.slice(11, 19), item: runId },
        { id: 'generation-cache', node: 'Generation', status: gens.length ? 'ready' : 'waiting', heartbeat: now.slice(11, 19), item: `${gens.length} gens` },
        { id: 'gate-counter', node: 'Scoring', status: passCount ? 'ready' : 'waiting', heartbeat: now.slice(11, 19), item: `${passCount} passed` }
      ],
      contracts: Array.isArray(payload.contracts) && payload.contracts.length ? payload.contracts : (fixture.contracts || []).map(row => ({ ...row, status: row.status === 'PENDING' ? 'PENDING' : 'UNKNOWN' })),
      requiredFields: fixture.requiredFields || ['kpis', 'nodes', 'logs', 'runs', 'queue', 'workers', 'contracts'],
      selectedNodeId: phaseIndex > 0 && phaseIndex <= 5 ? phaseIndex : 1
    };
  }
  const RemodelAdapters = {
    overview() {
      const o = DATA.overview;
      return provenanceFor('overview', '조건식 AI', o, {
        generation: o.live && o.live.generation,
        strategyCount: o.generations ? o.generations.length : 0,
        gatePassed: o.live && o.live.gate,
        activeStrategy: o.activeStrategy && o.activeStrategy.id
      });
    },
    process() {
      const p = isLiveBackendMode && state.latestLoopPayload ? adaptProcessFromLoopPayload(state.latestLoopPayload) : DATA.process;
      return provenanceFor('process', '프로세스', p, {
        nodeCount: p.nodes ? p.nodes.length : 0,
        activeNodes: p.nodes ? p.nodes.filter(n => n.status === '진행 중').length : 0,
        logCount: p.logs ? p.logs.length : 0
      });
    },
    history() {
      const h = DATA.history;
      return provenanceFor('history', '히스토리', h, {
        runCount: h.runs ? h.runs.length : 0,
        researchRecordCount: h.researchRecords ? h.researchRecords.length : 0,
        sourceRuns: state.latestRunsPayload ? 'backend /runs' : 'fixture archive'
      });
    },
    lab() {
      const l = DATA.lab;
      return provenanceFor('lab', '연구실', l, {
        variableCount: l.importance ? l.importance.length : 0,
        comboCount: l.combos ? l.combos.length : 0,
        holdoutReturn: l.holdout && l.holdout.return
      });
    },
    workbench() {
      const w = DATA.workbench;
      return provenanceFor('workbench', '분석 워크벤치', w, {
        candidateCount: w.candidates ? w.candidates.length : 0,
        selectedCandidate: w.candidates && w.candidates.find(c => c.selected) ? w.candidates.find(c => c.selected).id : '—',
        evidenceCount: w.evidence ? w.evidence.length : 0
      });
    },
    audit() {
      const a = DATA.audit;
      return provenanceFor('audit', '결정 감사', a, {
        decisionCount: a.ledger ? a.ledger.length : 0,
        checklistCount: a.checklist ? a.checklist.length : 0,
        appendOnly: true
      });
    }
  };
  window.RemodelAdapters = RemodelAdapters;

  function provenanceCue(vm) {
    const summary = Object.entries(vm.summary || {})
      .filter(([, value]) => value !== undefined && value !== null)
      .slice(0, 3)
      .map(([key, value]) => `${key}: ${value}`)
      .join(' · ');
    return `<div class="notice provenance-cue"><span><b>${escapeHtml(vm.label)} provenance</b> · source: ${escapeHtml(vm.source)} · mode: ${escapeHtml(vm.mode)} · backend: ${escapeHtml(vm.backendUrl)} · ${escapeHtml(vm.livePayloadStatus)}</span>${badge(vm.isLive ? 'Live payload' : vm.isFixture ? 'Fixture/static' : 'Loading/fallback', vm.isLive ? 'green' : 'amber')}${summary ? `<span class="muted">${escapeHtml(summary)}</span>` : ''}</div>`;
  }

  const PageControllers = {
    overview: { id: 'overview', label: '조건식 AI', getViewModel: RemodelAdapters.overview, render: () => renderOverview(RemodelAdapters.overview()) },
    process: { id: 'process', label: '프로세스', getViewModel: RemodelAdapters.process, render: () => renderProcess(RemodelAdapters.process()) },
    history: { id: 'history', label: '히스토리', getViewModel: RemodelAdapters.history, render: () => renderHistory(RemodelAdapters.history()) },
    lab: { id: 'lab', label: '연구실', getViewModel: RemodelAdapters.lab, render: () => renderLab(RemodelAdapters.lab()) },
    workbench: { id: 'workbench', label: '분석 워크벤치', getViewModel: RemodelAdapters.workbench, render: () => renderWorkbench(RemodelAdapters.workbench()) },
    audit: { id: 'audit', label: '결정 감사', getViewModel: RemodelAdapters.audit, render: () => renderAudit(RemodelAdapters.audit()) }
  };
  window.PageControllers = PageControllers;

  let chartSeq = 0;
  let chartRegistry = {};
  function normalize(values) {
    const all = values.flat().filter(v => typeof v === 'number' && Number.isFinite(v));
    let min = Math.min(...all), max = Math.max(...all);
    if (!Number.isFinite(min) || !Number.isFinite(max)) { min = 0; max = 1; }
    if (min === max) { min -= 1; max += 1; }
    return { min, max };
  }
  function chartValue(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) return 'n/a';
    const abs = Math.abs(value);
    if (abs >= 100) return value.toFixed(0);
    if (abs >= 10) return value.toFixed(2);
    return value.toFixed(3);
  }
  function seriesDiagnostics(seriesList) {
    return (seriesList || []).reduce((acc, item) => {
      const values = Array.isArray(item) ? item : (item && Array.isArray(item.values) ? item.values : []);
      values.forEach(value => {
        acc.total += 1;
        if (!Number.isFinite(Number(value))) acc.malformed += 1;
      });
      return acc;
    }, { total: 0, malformed: 0 });
  }
  function chartProvenance(opts = {}) {
    const source = opts.source || (isReferenceMode ? 'reference fixture' : isDemoMode ? 'demo fixture' : 'fixture fallback · backend not driving chart');
    const freshness = opts.freshness || (isReferenceMode ? 'reference-static' : isDemoMode ? 'demo-static' : 'stale-fixture-fallback');
    const status = opts.status || (freshness.includes('stale') || source.includes('fallback') ? 'STALE/FALLBACK' : 'CURRENT');
    return {
      source,
      freshness,
      status,
      runId: opts.runId || DATA.shell.runId || 'run_id unavailable',
    };
  }
  function chartStateBadges(opts = {}, diagnostics = {}) {
    const provenance = chartProvenance(opts);
    const malformed = diagnostics.malformed || 0;
    return `<div class="chart-state-badges" aria-label="chart provenance"><span class="chart-state-badge ${provenance.status.includes('STALE') ? 'warn' : 'ok'}">status=${escapeHtml(provenance.status)}</span><span class="chart-state-badge">run_id=${escapeHtml(provenance.runId)}</span><span class="chart-state-badge">freshness=${escapeHtml(provenance.freshness)}</span><span class="chart-state-badge ${malformed ? 'warn' : 'ok'}">malformed=${malformed}</span></div>`;
  }
  function datumLabel(meta, index) {
    const labels = meta.labels || [];
    const label = labels[index] || `#${index + 1}`;
    const parts = meta.series.map(s => `${s.name}: ${chartValue(s.values[index])}`);
    const malformed = meta.malformedCount ? ` · malformed=${meta.malformedCount}` : '';
    return `${meta.title} · ${label} · ${parts.join(' · ')} · source=${meta.source} · run_id=${meta.runId || 'run_id unavailable'} · freshness=${meta.freshness || 'unknown'} · status=${meta.status || 'unknown'}${malformed}`;
  }
  function registerChart(meta) {
    const id = `remodel-chart-${++chartSeq}`;
    chartRegistry[id] = meta;
    return id;
  }
  function lineSvg(seriesInput, opts = {}) {
    const h = opts.height || 128, w = opts.width || 420, pad = 18;
    const input = Array.isArray(seriesInput) ? seriesInput : [];
    const rawSeries = Array.isArray(input[0]) || typeof input[0] === 'number'
      ? [{ name: opts.name || 'Series', values: input }]
      : input;
    const diagnostics = seriesDiagnostics(rawSeries);
    const provenance = chartProvenance(opts);
    const series = rawSeries.map((s, idx) => ({
      name: s.name || `Series ${idx + 1}`,
      color: s.color || colors[idx % colors.length],
      values: (s.values || []).map(v => Number(v)).filter(v => Number.isFinite(v)),
    })).filter(s => s.values.length);
    if (!series.length) {
      return `<div class="chart-empty" role="status">데이터 없음 · source=${escapeHtml(provenance.source)} · run_id=${escapeHtml(provenance.runId)} · freshness=${escapeHtml(provenance.freshness)} · status=${escapeHtml(provenance.status)} · malformed=${diagnostics.malformed}</div>`;
    }
    const { min, max } = normalize(series.map(s => s.values));
    const count = Math.max(...series.map(s => s.values.length));
    const x = (i, n) => pad + (n <= 1 ? 0 : i * (w - pad * 2) / (n - 1));
    const y = v => h - pad - ((v - min) / (max - min)) * (h - pad * 2);
    const labels = opts.labels || Array.from({ length: count }, (_, i) => `T+${i + 1}`);
    const chartId = registerChart({
      kind: 'line',
      title: opts.title || opts.name || 'Chart',
      ...provenance,
      malformedCount: diagnostics.malformed,
      min,
      max,
      labels,
      series,
    });
    const grid = [0, .25, .5, .75, 1].map(t => {
      const gy = pad + t * (h - pad * 2);
      const gv = max - (max - min) * t;
      return `<line x1="${pad}" y1="${gy}" x2="${w - pad}" y2="${gy}" stroke="rgba(142,164,181,.16)" stroke-width="1"/><text x="${pad + 2}" y="${gy - 3}" fill="rgba(142,164,181,.55)" font-size="9">${chartValue(gv)}</text>`;
    }).join('');
    const zero = min < 0 && max > 0 ? `<line x1="${pad}" y1="${y(0)}" x2="${w - pad}" y2="${y(0)}" stroke="rgba(245,181,68,.35)"/>` : '';
    const polys = series.map((s, seriesIndex) => {
      const pts = s.values.map((v, i) => `${x(i, s.values.length).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
      const dots = s.values.map((v, i) => `<circle class="chart-hit-dot" data-series-index="${seriesIndex}" cx="${x(i, s.values.length).toFixed(1)}" cy="${y(v).toFixed(1)}" r="2.8" fill="${s.color}" data-index="${i}" data-series="${escapeHtml(s.name)}"><title>${escapeHtml(`${s.name} · ${labels[i] || `#${i + 1}`} · ${chartValue(v)}`)}</title></circle>`).join('');
      return `<polyline class="chart-series-line" data-series-index="${seriesIndex}" points="${pts}" fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>${dots}`;
    }).join('');
    const label = datumLabel(chartRegistry[chartId], count - 1);
    return `<svg class="chart-svg interactive-chart ${opts.tall ? 'tall' : ''}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" tabindex="0" role="img" aria-label="${escapeHtml(label)}" data-chart-id="${chartId}" data-chart-count="${count}" data-chart-status="${escapeHtml(provenance.status)}" data-chart-malformed="${diagnostics.malformed}"><title>${escapeHtml(label)}</title>${grid}${zero}<line class="chart-crosshair-line" x1="${w - pad}" x2="${w - pad}" y1="${pad}" y2="${h - pad}"/>${polys}</svg>`;
  }
  function sparkline(values) {
    return `<div class="kpi-spark">${lineSvg(values, { height: 34, width: 180, title: 'KPI sparkline', source: 'compact KPI series', freshness: 'compact-current', status: 'CURRENT' })}</div>`;
  }
  function chart(title, series, opts = {}) {
    const input = Array.isArray(series) ? series : [];
    const seriesList = Array.isArray(input[0]) || typeof input[0] === 'number' ? [{ name: title, values: input }] : input;
    const diagnostics = seriesDiagnostics(seriesList);
    const latest = seriesList.map(s => `${s.name || title} ${chartValue((s.values || [])[Math.max(0, (s.values || []).length - 1)])}`).join(' · ');
    const legend = Array.isArray(input[0]) || typeof input[0] === 'number' ? '' : `<div class="legend" aria-label="${escapeHtml(title)} legend">${input.map((s, i) => `<span class="legend-item" tabindex="0" role="button" data-legend-index="${i}" aria-label="highlight ${escapeHtml(s.name)}"><span class="legend-swatch" style="background:${s.color || colors[i % colors.length]}"></span>${escapeHtml(s.name)}</span>`).join('')}</div>`;
    return `<div class="chart-box ${opts.small ? 'sm' : ''}" data-chart-box data-ux-chart><div class="chart-title" data-chart-title><span>${escapeHtml(title)}</span>${opts.value ? `<span class="${opts.tone || 'green'} mono">${escapeHtml(opts.value)}</span>` : ''}</div>${chartStateBadges(opts, diagnostics)}${lineSvg(series, { ...opts, title })}<div class="chart-active-datum" data-chart-active-value aria-live="polite">${escapeHtml(`latest · ${latest}`)}</div>${legend}</div>`;
  }
  function barLineChart(title, bars, opts = {}) {
    const h = opts.height || 128, w = opts.width || 420, pad = 18;
    const rawBars = Array.isArray(bars) ? bars : [];
    const diagnostics = seriesDiagnostics([{ name: title, values: rawBars }]);
    const provenance = chartProvenance(opts);
    const cleanBars = rawBars.map(v => Number(v)).filter(v => Number.isFinite(v));
    if (!cleanBars.length) {
      return `<div class="chart-box"><div class="chart-title"><span>${escapeHtml(title)}</span></div>${chartStateBadges(opts, diagnostics)}<div class="chart-empty" role="status">데이터 없음 · source=${escapeHtml(provenance.source)} · run_id=${escapeHtml(provenance.runId)} · freshness=${escapeHtml(provenance.freshness)} · status=${escapeHtml(provenance.status)} · malformed=${diagnostics.malformed}</div></div>`;
    }
    const cumulative = [];
    cleanBars.reduce((a, b, i) => (cumulative[i] = +(a + b).toFixed(2), a + b), 0);
    const { min, max } = normalize([cleanBars, cumulative]);
    const x = (i) => pad + i * (w - pad * 2) / cleanBars.length;
    const bw = Math.max(2, (w - pad * 2) / cleanBars.length * 0.55);
    const y = v => h - pad - ((v - min) / (max - min)) * (h - pad * 2);
    const zeroY = y(0);
    const chartId = registerChart({
      kind: 'bar-line',
      title,
      ...provenance,
      malformedCount: diagnostics.malformed,
      min,
      max,
      labels: cleanBars.map((_, i) => `T+${i + 1}`),
      series: [
        { name: 'Daily Profit', values: cleanBars, color: 'var(--green)' },
        { name: 'Cumulative', values: cumulative, color: 'var(--cyan)' },
      ],
    });
    const rects = cleanBars.map((v, i) => `<rect class="chart-bar" data-series-index="0" x="${x(i)}" y="${Math.min(zeroY, y(v))}" width="${bw}" height="${Math.abs(zeroY - y(v))}" fill="${v >= 0 ? 'var(--green)' : 'var(--red)'}" opacity=".75"><title>${escapeHtml(`Daily Profit · T+${i + 1} · ${chartValue(v)}`)}</title></rect>`).join('');
    const pts = cumulative.map((v, i) => `${x(i) + bw / 2},${y(v)}`).join(' ');
    const label = datumLabel(chartRegistry[chartId], cleanBars.length - 1);
    return `<div class="chart-box" data-chart-box><div class="chart-title"><span>${escapeHtml(title)}</span>${opts.value ? `<span class="green mono">${escapeHtml(opts.value)}</span>` : ''}</div>${chartStateBadges(opts, diagnostics)}<svg class="chart-svg interactive-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" tabindex="0" role="img" aria-label="${escapeHtml(label)}" data-chart-id="${chartId}" data-chart-count="${cleanBars.length}" data-chart-status="${escapeHtml(provenance.status)}" data-chart-malformed="${diagnostics.malformed}"><title>${escapeHtml(label)}</title><line x1="${pad}" y1="${zeroY}" x2="${w - pad}" y2="${zeroY}" stroke="rgba(142,164,181,.25)"/><line class="chart-crosshair-line" x1="${w - pad}" x2="${w - pad}" y1="${pad}" y2="${h - pad}"/>${rects}<polyline class="chart-series-line" data-series-index="1" points="${pts}" fill="none" stroke="var(--cyan)" stroke-width="2.2"/></svg><div class="chart-active-datum" aria-live="polite">${escapeHtml(`latest · ${label}`)}</div><div class="legend" aria-label="${escapeHtml(title)} legend"><span class="legend-item" tabindex="0" role="button" data-legend-index="0" aria-label="highlight Daily Profit"><span class="legend-swatch" style="background:var(--green)"></span>Daily Profit</span><span class="legend-item" tabindex="0" role="button" data-legend-index="1" aria-label="highlight Cumulative"><span class="legend-swatch" style="background:var(--cyan)"></span>Cumulative</span></div></div>`;
  }
  function attachChartEvents() {
    document.querySelectorAll('.interactive-chart[data-chart-id]').forEach(svg => {
      const meta = chartRegistry[svg.dataset.chartId];
      if (!meta) return;
      const box = svg.closest('[data-chart-box]') || svg.parentElement;
      let tip = box.querySelector('.chart-tooltip');
      if (!tip) {
        tip = document.createElement('div');
        tip.className = 'chart-tooltip';
        tip.setAttribute('role', 'status');
        box.appendChild(tip);
      }
      const active = box.querySelector('.chart-active-datum');
      const legendItems = [...box.querySelectorAll('.legend-item[data-legend-index]')];
      let lockedLegend = null;
      const setLegendHighlight = (seriesIndex) => {
        const selected = seriesIndex == null ? null : Number(seriesIndex);
        if (selected == null || !Number.isFinite(selected)) {
          delete svg.dataset.highlightSeries;
        } else {
          svg.dataset.highlightSeries = String(selected);
        }
        svg.querySelectorAll('[data-series-index]').forEach(el => {
          const matches = selected != null && Number(el.getAttribute('data-series-index')) === selected;
          el.classList.toggle('series-highlighted', matches);
          el.classList.toggle('series-dimmed', selected != null && !matches);
        });
        legendItems.forEach(item => {
          const matches = selected != null && Number(item.dataset.legendIndex) === selected;
          item.classList.toggle('active', matches);
          item.setAttribute('aria-pressed', matches ? 'true' : 'false');
        });
        if (active && selected != null) {
          const name = meta.series[selected] ? meta.series[selected].name : `Series ${selected + 1}`;
          active.textContent = `legend highlight · ${name} · ${datumLabel(meta, Number(svg.dataset.activeIndex || svg.dataset.chartCount || 1) - 1)}`;
        }
      };
      legendItems.forEach(item => {
        const index = Number(item.dataset.legendIndex);
        item.setAttribute('aria-pressed', 'false');
        item.addEventListener('mouseenter', () => setLegendHighlight(index));
        item.addEventListener('focus', () => setLegendHighlight(index));
        item.addEventListener('mouseleave', () => { if (lockedLegend == null) setLegendHighlight(null); });
        item.addEventListener('blur', () => { if (lockedLegend == null) setLegendHighlight(null); });
        item.addEventListener('click', () => {
          lockedLegend = lockedLegend === index ? null : index;
          setLegendHighlight(lockedLegend);
        });
        item.addEventListener('keydown', event => {
          if (!['Enter', ' '].includes(event.key)) return;
          event.preventDefault();
          item.click();
        });
      });
      const setIndex = (idx, clientX) => {
        const count = Number(svg.dataset.chartCount || meta.series[0].values.length || 1);
        const safeIdx = Math.max(0, Math.min(count - 1, idx));
        svg.dataset.activeIndex = String(safeIdx);
        const label = datumLabel(meta, safeIdx);
        const rect = svg.getBoundingClientRect();
        const xPos = clientX ? Math.max(0, Math.min(rect.width, clientX - rect.left)) : rect.width * (count <= 1 ? 0 : safeIdx / (count - 1));
        svg.style.setProperty('--chart-crosshair-x', `${xPos}px`);
        tip.textContent = label;
        tip.style.left = `${Math.min(Math.max(12, xPos + 10), Math.max(12, rect.width - 260))}px`;
        tip.classList.add('visible');
        if (active) active.textContent = label;
        svg.setAttribute('aria-label', label);
        if (svg.dataset.highlightSeries) setLegendHighlight(Number(svg.dataset.highlightSeries));
      };
      svg.addEventListener('mousemove', event => {
        const rect = svg.getBoundingClientRect();
        const count = Number(svg.dataset.chartCount || meta.series[0].values.length || 1);
        const ratio = rect.width <= 0 ? 0 : (event.clientX - rect.left) / rect.width;
        setIndex(Math.round(ratio * (count - 1)), event.clientX);
      });
      svg.addEventListener('mouseleave', () => { tip.classList.remove('visible'); });
      svg.addEventListener('focus', () => setIndex(Number(svg.dataset.activeIndex || svg.dataset.chartCount || 1) - 1));
      svg.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const count = Number(svg.dataset.chartCount || meta.series[0].values.length || 1);
        const current = Number(svg.dataset.activeIndex || count - 1);
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? count - 1 : current + (event.key === 'ArrowRight' ? 1 : -1);
        setIndex(next);
      });
    });
  }
  function heatmap(rows, cols, values, opts = {}) {
    const mode = opts.mode || 'edge';
    const color = v => {
      if (mode === 'corr') {
        const t = (v + 1) / 2;
        const hue = t < .5 ? 210 : 6;
        const sat = 70;
        const light = 17 + Math.abs(t - .5) * 75;
        return `hsl(${hue} ${sat}% ${light}%)`;
      }
      if (mode === 'return') {
        const hue = v >= 0 ? 145 : 2;
        const light = 17 + Math.min(Math.abs(v) / 3, 1) * 42;
        return `hsl(${hue} 58% ${light}%)`;
      }
      const hue = 230 - v * 190;
      const light = 18 + v * 45;
      return `hsl(${hue} 78% ${light}%)`;
    };
    const gridCols = `minmax(54px, .8fr) repeat(${cols.length}, minmax(0, 1fr))`;
    const flatValues = values.flat().map(v => Number(v)).filter(v => Number.isFinite(v));
    const minValue = flatValues.length ? Math.min(...flatValues) : 0;
    const maxValue = flatValues.length ? Math.max(...flatValues) : 0;
    let html = `<div class="heatmap" data-ux-heatmap data-heatmap-scale="${escapeHtml(`${chartValue(minValue)} → ${chartValue(maxValue)}`)}" style="grid-template-columns:${gridCols}"><div class="heat-label" data-heatmap-axis-y>axis</div>${cols.map(c => `<div class="heat-label" data-heatmap-axis-x>${escapeHtml(c)}</div>`).join('')}`;
    rows.forEach((r, i) => {
      html += `<div class="heat-label" data-heatmap-axis-y>${escapeHtml(r)}</div>`;
      cols.forEach((c, j) => {
        const v = values[i][j];
        html += `<div class="heat-cell" data-heatmap-cell title="${escapeHtml(r)} · ${escapeHtml(c)} · ${v}" style="background:${color(v)}">${opts.hideValues ? '' : escapeHtml(v)}</div>`;
      });
    });
    html += '</div>';
    return html;
  }
  function table(columns, rows, opts = {}) {
    return `<div class="table-wrap"><table><thead><tr>${columns.map(c => `<th>${escapeHtml(c.label || c)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${columns.map(c => {
      const key = c.key || c;
      let val = typeof c.render === 'function' ? c.render(row) : row[key];
      return `<td>${val ?? ''}</td>`;
    }).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function codeBox(code) {
    return `<pre class="code-box">${escapeHtml(code)}</pre>`;
  }
  function miniTabs(labels, active) {
    return `<div class="inspector-tabs">${labels.map(l => `<span class="tab-mini ${l === active ? 'active' : ''}">${escapeHtml(l)}</span>`).join('')}</div>`;
  }

  function renderShell() {
    const s = DATA.shell;
    const runTone = cls(state.runStatus);
    const primary = primaryTabs.map(t => `<button class="tab-btn ${state.primary === t.id ? 'active' : ''}" data-primary="${t.id}">${t.label}</button>`).join('');
    const sub = state.primary === 'condition' ? subTabs.map(t => `<button class="tab-btn sub ${state.sub === t.id ? 'active' : ''}" data-sub="${t.id}">${t.label}</button>`).join('') : '';
    app.innerHTML = `
      <header class="topbar">
        <div class="brand"><div class="brand-mark">✺</div><div class="brand-title">${s.title}</div></div>
        <div class="header-controls">
          <div class="control-group"><span class="control-label">Backend Base URL</span><input class="url-input" value="${escapeHtml(state.baseUrl || s.backendUrl)}" ${isLiveBackendMode ? '' : 'readonly'} /></div>
          ${btn('재연결', 'small', `data-action="reconnect" ${isLiveBackendMode ? '' : 'disabled'}`)}
          ${badge(modeLabel + ' mode', isLiveBackendMode ? 'green' : 'amber')}
          ${badge('REST ' + s.restHealth, cls(s.restHealth))}
          ${badge('WebSocket ' + s.websocket, cls(s.websocket))}
          ${badge('Run Status ' + state.runStatus, runTone)}
          <button class="btn small ghost" data-action="theme">테마 ◐</button>
        </div>
        <div class="header-right">
          ${badge('경계선 내 조건식 엔진 · 연구 전용', 'amber')}
          ${badge('Route Owner ' + s.routeOwner, 'blue')}
          ${badge('Boundary local-only', 'violet')}
        </div>
      </header>
      <div class="boundary-strip">
        <span>Route Owner <b>${s.routeOwner}</b></span><span>Boundary <b>${s.boundary}</b></span><span>Env <b>dev</b></span><span>Mode <b>${modeLabel}</b></span><span>Contract <b>${s.contract}</b></span><span>Approval <b>Human Gate Required</b></span><span>Audit <b>Append-Only</b></span>
      </div>
      ${renderWorkflowRail()}
      ${renderSharedContextStrip()}
      <nav class="nav-row">${primary}<div class="shell-run">
        <button class="btn small ${state.liveMode === 'LIVE' ? 'primary' : ''}" data-live="LIVE">LIVE</button><button class="btn small ${state.liveMode === 'ARCHIVE' ? 'blue' : ''}" data-live="ARCHIVE">ARCHIVE</button>
        <span class="progress-wrap"><span class="muted">${s.generationText}</span><span class="progress"><span style="width:${s.generationProgress}%"></span></span><span class="mono green">${s.generationProgress}%</span></span>
        ${badge('Provider ' + s.provider, 'blue')}${badge('TF ' + s.timeframe, 'blue')}${badge('run_id ' + s.runId, 'blue')}
        ${manualBtn('⚙ 설정', 'small', 'data-action="settings"', 'settings')}${manualBtn('Start ▶', 'primary small', 'data-action="start"', 'loop-start')}${manualBtn('Stop ■', 'danger small', 'data-action="stop"', 'loop-stop')}
      </div></nav>
      ${sub ? `<nav class="subnav-row">${sub}</nav>` : ''}
      <main id="page" class="main-area"></main>
    `;
    attachShellEvents();
  }
  function attachShellEvents() {
    document.querySelectorAll('[data-primary]').forEach(el => el.addEventListener('click', () => { state.primary = el.dataset.primary; if (state.primary === 'condition' && !state.sub) state.sub = 'overview'; pushRouteFromState(); render(); }));
    document.querySelectorAll('[data-sub]').forEach(el => el.addEventListener('click', () => { state.sub = el.dataset.sub; pushRouteFromState(); render(); }));
    document.querySelectorAll('[data-workflow-primary]').forEach(el => el.addEventListener('click', () => {
      state.primary = el.dataset.workflowPrimary;
      state.sub = el.dataset.workflowSub || (state.primary === 'condition' ? 'overview' : state.sub);
      pushRouteFromState();
      render();
    }));
    document.querySelectorAll('[data-workflow-action="settings"]').forEach(el => el.addEventListener('click', openSettingsModal));
    document.querySelectorAll('[data-live]').forEach(el => el.addEventListener('click', () => { state.liveMode = el.dataset.live; render(); }));
    document.querySelectorAll('.url-input').forEach(el => el.addEventListener('change', () => {
      if (!isLiveBackendMode) {
        el.value = state.baseUrl || DATA.shell.backendUrl || DEFAULT_BACKEND_BASE;
        return;
      }
      state.baseUrl = String(el.value || DEFAULT_BACKEND_BASE).replace(/\/+$/, '');
      DATA.shell.backendUrl = state.baseUrl;
      writeStoredBaseUrl(state.baseUrl);
      reconnectBackend();
    }));
    document.querySelectorAll('[data-action="theme"]').forEach(el => el.addEventListener('click', () => { document.documentElement.classList.toggle('light'); }));
    document.querySelectorAll('[data-action="settings"]').forEach(el => el.addEventListener('click', openSettingsModal));
    document.querySelectorAll('[data-action="reconnect"]').forEach(el => el.addEventListener('click', reconnectBackend));
    document.querySelectorAll('[data-action="start"]').forEach(el => el.addEventListener('click', () => { sendControl({ action: 'start', config: {} }); if (isLiveBackendMode) state.runStatus = 'running'; render(); }));
    document.querySelectorAll('[data-action="stop"]').forEach(el => el.addEventListener('click', () => { sendControl({ action: 'stop' }); if (isLiveBackendMode) state.runStatus = 'stopping'; render(); }));
  }

  function render() {
    renderShell();
    const page = document.getElementById('page');
    chartRegistry = {};
    const controller = state.primary === 'condition' ? (PageControllers[state.sub] || PageControllers.overview) : null;
    const renderer = state.primary === 'backtest' ? renderBacktest : state.primary === 'replay' ? renderReplay : controller.render;
    page.innerHTML = renderer();
    attachPageEvents();
  }

  function backendUrl(path) {
    const base = String(state.baseUrl || DEFAULT_BACKEND_BASE).replace(/\/+$/, '');
    return base + path;
  }

  function wsUrl(path) {
    try {
      const u = new URL(backendUrl(path));
      u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
      return u.toString();
    } catch (e) {
      return null;
    }
  }

  function deterministicLineageValue(index, base, step, modulo) {
    return base + ((index * step) % modulo);
  }

  function fetchJson(path, timeoutMs = 4000) {
    if (!isLiveBackendMode) return Promise.reject(new Error('Backend disabled outside live mode'));
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    return fetch(backendUrl(path), { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
      .finally(() => clearTimeout(timer));
  }
  function fetchText(path, timeoutMs = 4000) {
    if (!isLiveBackendMode) return Promise.reject(new Error('Backend disabled outside live mode'));
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    return fetch(backendUrl(path), { signal: controller.signal })
      .then(r => r.ok ? r.text() : Promise.reject(new Error('HTTP ' + r.status)))
      .finally(() => clearTimeout(timer));
  }
  function summarizePayload(payload) {
    if (Array.isArray(payload)) return `${payload.length} rows`;
    if (!payload || typeof payload !== 'object') return payload == null ? 'empty response' : typeof payload;
    const keys = Object.keys(payload);
    if (Array.isArray(payload.jobs)) return `${payload.jobs.length} jobs`;
    if (Array.isArray(payload.strategies)) return `${payload.strategies.length} strategies`;
    if (Array.isArray(payload.results)) return `${payload.results.length} results`;
    if (payload.status) return `status ${payload.status}`;
    return keys.length ? keys.slice(0, 4).join(', ') : 'object response';
  }

  function firstArray(payload, keys) {
    if (Array.isArray(payload)) return payload;
    if (!payload || typeof payload !== 'object') return [];
    for (const key of keys) {
      if (Array.isArray(payload[key])) return payload[key];
    }
    return [];
  }

  function firstNamedStrategy(payload) {
    const rows = firstArray(payload, ['strategies', 'items', 'rows']);
    const row = rows.find(x => x && (x.name || x.strategy_name || x.id));
    return row ? (row.name || row.strategy_name || row.id) : '';
  }

  function firstJobIds(payload) {
    return firstArray(payload, ['jobs', 'items', 'rows'])
      .map(x => x && (x.job_id || x.id))
      .filter(Boolean)
      .slice(0, 3);
  }

  function firstRunIds(payload) {
    return firstArray(payload, ['jobs', 'items', 'rows'])
      .map(x => x && (x.run_id || x.runId))
      .filter(Boolean)
      .slice(0, 3);
  }

  function conditionDetailContext(input = {}) {
    const payload = input.payload || state.latestLoopPayload || {};
    const overview = DATA.overview || {};
    const generations = Array.isArray(input.generations)
      ? input.generations
      : Array.isArray(payload.generations)
        ? payload.generations
        : (overview.generations || []);
    const selected = input.generation || generations.find(row => row && (row.selected || row.gate_passed === true || row.gate_passed === '통과')) || generations[0] || {};
    const hasRunInput = Object.prototype.hasOwnProperty.call(input, 'run_id') || Object.prototype.hasOwnProperty.call(input, 'runId');
    const hasGenInput = Object.prototype.hasOwnProperty.call(input, 'gen_no') || Object.prototype.hasOwnProperty.call(input, 'genNo') || Object.prototype.hasOwnProperty.call(input, 'gen');
    const runId = String(hasRunInput ? (input.run_id ?? input.runId ?? '') : (payload.run_id || overview.run_id || DATA.shell.runId || '')).trim();
    const genNo = intOrDefault(hasGenInput ? (input.gen_no ?? input.genNo ?? input.gen) : (selected.gen_no ?? selected.gen ?? -1), -1);
    const status = !runId ? 'missing-run' : genNo < 0 ? 'missing-gen' : 'ready';
    return {
      run_id: runId,
      gen_no: genNo,
      selected,
      status,
      ready: status === 'ready',
      reason: status === 'ready' ? 'read-only detail APIs can be requested' : 'Missing run/gen returns an empty state, not a broken inspector.',
    };
  }

  function conditionDetailEndpoint(contract, context) {
    const ctx = context || conditionDetailContext();
    const run = encodeURIComponent(ctx.run_id || '');
    const gen = encodeURIComponent(String(ctx.gen_no ?? -1));
    if (!contract) return '';
    if (contract.id === 'strategy-code') return `/strategy_code?run=${run}&gen=${gen}`;
    if (contract.id === 'strategy-diff') return `/strategy_diff?run_id=${run}&gen_no=${gen}&base_gen=previous`;
    if (contract.id === 'prompts') return `/prompts?run_id=${run}&gen_no=${gen}`;
    if (contract.id === 'ai-context-pack') return `/ai_context_pack?run_id=${run}&gen_no=${gen}`;
    if (contract.id === 'backtest-detail') return `/backtest_detail?run_id=${run}&gen_no=${gen}`;
    return contract.endpoint || '';
  }

  function markConditionDetailEvidence(id, status, detail, payload = null) {
    state.conditionDetailEvidence[id] = { status, detail };
    if (payload) state.conditionDetailPayloads[id] = payload;
  }

  function conditionDetailPayloadSummary(contract, payload) {
    if (!payload || typeof payload !== 'object') return 'empty response';
    if (contract.id === 'strategy-code') {
      const buyLines = String(payload.buy_code || '').split('\n').filter(Boolean).length;
      const sellLines = String(payload.sell_code || '').split('\n').filter(Boolean).length;
      return `${buyLines} buy lines · ${sellLines} sell lines · ${payload.code_status || 'available'}`;
    }
    if (contract.id === 'strategy-diff') return `${firstArray(payload, ['buy_diff']).length} buy diff · ${firstArray(payload, ['sell_diff']).length} sell diff · ${payload.diff_status || payload.reason || 'available'}`;
    if (contract.id === 'prompts') return `${firstArray(payload, ['prompts', 'items', 'rows']).length} prompts · ${payload.reason || 'available'}`;
    if (contract.id === 'backtest-detail') return `${firstArray(payload, ['daily']).length} daily · ${firstArray(payload, ['cumulative']).length} cumulative · ${firstArray(payload, ['drawdown']).length} drawdown`;
    return summarizePayload(payload);
  }

  function renderConditionDetailSurface(context = conditionDetailContext()) {
    const selectorRows = [
      ['run_id', context.run_id || 'missing'],
      ['gen_no', String(context.gen_no)],
      ['status', context.status, context.ready ? 'green' : 'amber'],
      ['mode', modeLabel],
    ];
    const apiAttrs = {
      'strategy-code': 'data-condition-detail-api="/strategy_code?run=&gen="',
      'strategy-diff': 'data-condition-detail-api="/strategy_diff?run_id=&gen_no=&base_gen=previous"',
      prompts: 'data-condition-detail-api="/prompts?run_id=&gen_no="',
      'ai-context-pack': 'data-condition-detail-api="/ai_context_pack?run_id=&gen_no="',
      'backtest-detail': 'data-condition-detail-api="/backtest_detail?run_id=&gen_no="',
    };
    const cards = ConditionDetailContracts.map(contract => {
      const ev = state.conditionDetailEvidence[contract.id] || {};
      const payload = state.conditionDetailPayloads[contract.id] || {};
      const endpoint = conditionDetailEndpoint(contract, context);
      const detail = ev.detail || (context.ready ? 'Ready for live safe GET; reference/demo remains inert.' : contract.emptyState);
      const empty = !context.ready || ev.status === 'EMPTY' || ev.status === 'NOT-USED' || ev.status === 'INERT';
      return `<div class="condition-detail-card" ${apiAttrs[contract.id] || ''} data-condition-detail-id="${escapeHtml(contract.id)}">
        <div class="panel-header"><span>${escapeHtml(contract.label)}</span>${badge(ev.status || (isLiveBackendMode ? 'PENDING' : 'INERT'), cls(ev.status || 'hold'))}</div>
        <div class="muted">${escapeHtml(contract.endpoint)}</div>
        <div class="${empty ? 'condition-detail-empty' : ''}" ${empty ? 'data-condition-detail-empty' : ''}>${escapeHtml(detail)}</div>
        <div class="muted">${escapeHtml(endpoint)}</div>
        ${contract.id === 'strategy-code' ? codeBox(String(payload.buy_code || DATA.strategyCode.buy || '').split('\n').slice(0, 8).join('\n')) : ''}
      </div>`;
    }).join('');
    return `<section class="condition-detail-surface" data-condition-detail-surface data-condition-detail-context="${escapeHtml(context.status)}">
      <div class="panel-header"><span>Condition AI detail APIs</span>${badge('read-only', 'blue')}</div>
      <div class="notice">Strategy code / diff / prompt / context / backtest detail are read-only.</div>
      <div class="notice warn">Missing run/gen returns an empty state, not a broken inspector.</div>
      <div class="condition-detail-grid">
        <div class="condition-detail-card" data-condition-run-gen-selector>${infoList(selectorRows)}</div>
        ${cards}
      </div>
    </section>`;
  }

  const ConditionDetailAdapter = {
    contracts: ConditionDetailContracts,
    ensurePageEvidence() {
      const context = conditionDetailContext();
      if (!isLiveBackendMode) {
        ConditionDetailContracts.forEach(contract => markConditionDetailEvidence(contract.id, 'INERT', 'reference/demo inert · no fetch; detail API contract is shown with fixture baseline'));
        state.conditionDetailProbeComplete = true;
        return Promise.resolve(false);
      }
      if (state.conditionDetailProbeStarted) return Promise.resolve(true);
      state.conditionDetailProbeStarted = true;
      if (!context.ready) {
        ConditionDetailContracts.forEach(contract => markConditionDetailEvidence(contract.id, 'EMPTY', context.reason));
        state.conditionDetailProbeComplete = true;
        return Promise.resolve(false);
      }
      ConditionDetailContracts.forEach(contract => markConditionDetailEvidence(contract.id, 'PENDING', 'live safe GET queued'));
      return Promise.all(ConditionDetailContracts.map(contract =>
        fetchJson(conditionDetailEndpoint(contract, context), 5000)
          .then(payload => markConditionDetailEvidence(contract.id, 'LIVE OK', conditionDetailPayloadSummary(contract, payload), payload))
          .catch(e => markConditionDetailEvidence(contract.id, 'LIVE ERROR', e.message || 'request failed'))
      )).then(() => {
        state.conditionDetailProbeComplete = true;
        render();
        return true;
      });
    },
  };

  window.ConditionDetailSurface = {
    contracts: ConditionDetailContracts,
    context: conditionDetailContext,
    endpoint: conditionDetailEndpoint,
    render: renderConditionDetailSurface,
  };

  const ANALYTICS_HANDOFF_ENDPOINTS = Object.freeze([
    { id: 'edge-ratio', label: 'Edge Ratio', endpoint: '/edge_ratio?run_ids=', state: 'read-only run analysis' },
    { id: 'feature-importance', label: 'Feature Importance', endpoint: '/feature_importance?run_id=&gen_no=', state: 'read-only factor ranking' },
    { id: 'variable-correlation', label: 'Variable Correlation', endpoint: '/variable_correlation?run_id=&gen_no=', state: 'read-only factor relationship' },
  ]);

  function analyticsHandoffContext(input = {}) {
    const detail = conditionDetailContext(input);
    const selected = detail.selected || {};
    const buy = String(input.buy || selected.buy_name || selected.buy || DATA.overview.activeStrategy.name || BACKTEST_PREFLIGHT_DEFAULTS.buy || '').trim();
    const sell = String(input.sell || selected.sell_name || selected.sell || BACKTEST_PREFLIGHT_DEFAULTS.sell || '').trim();
    const date = String(input.date || REPLAY_PREFLIGHT_DEFAULTS.date || '').trim();
    const code = String(input.code || REPLAY_PREFLIGHT_DEFAULTS.code || '').trim();
    const jobId = String(input.job_id || input.jobId || 'J10235').trim();
    const ctx = {
      run_id: detail.run_id,
      gen_no: detail.gen_no,
      buy,
      sell,
      date,
      code,
      job_id: jobId,
      ready: detail.ready && Boolean(buy && sell),
      source_status: detail.status,
    };
    ctx.disabledReason = ctx.ready ? '' : 'Incomplete context disables handoff actions.';
    return ctx;
  }

  function buildConditionToBacktestHandoff(context = analyticsHandoffContext()) {
    return {
      route: '/ui/remodel/backtest',
      run_id: context.run_id,
      gen_no: context.gen_no,
      payload: buildBacktestRunPayload({
        buy: context.buy,
        sell: context.sell,
        mode: 'backtest',
      }),
      prefillOnly: true,
      disabledReason: context.ready ? '' : 'Incomplete context disables handoff actions.',
    };
  }

  function buildBacktestToReplayHandoff(input = {}) {
    const date = String(input.date || REPLAY_PREFLIGHT_DEFAULTS.date || '').trim();
    const code = String(input.code || REPLAY_PREFLIGHT_DEFAULTS.code || '').trim();
    const buy = String(input.buy || REPLAY_PREFLIGHT_DEFAULTS.buy || '').trim();
    const sell = String(input.sell || REPLAY_PREFLIGHT_DEFAULTS.sell || '').trim();
    const ready = Boolean(date && code && buy && sell);
    return {
      route: '/ui/remodel/chart-replay',
      job_id: String(input.job_id || input.jobId || 'J10235').trim(),
      payload: buildReplayStartPayload({ date, code, codes: code ? [code] : [], buy, sell }),
      prefillOnly: true,
      disabledReason: ready ? '' : 'Incomplete context disables handoff actions.',
    };
  }

  function validateAnalyticsHandoff(context = analyticsHandoffContext()) {
    const reasons = [];
    if (!context.run_id) reasons.push('run_id required');
    if (Number(context.gen_no) < 0) reasons.push('gen_no required');
    if (!context.buy || !context.sell) reasons.push('buy/sell strategy required');
    return {
      ok: reasons.length === 0,
      reasons,
      disabledReason: reasons.length ? 'Incomplete context disables handoff actions.' : '',
    };
  }

  function renderAnalyticsHandoffSurface(context = analyticsHandoffContext()) {
    const validation = validateAnalyticsHandoff(context);
    const conditionHandoff = buildConditionToBacktestHandoff(context);
    const replayHandoff = buildBacktestToReplayHandoff({
      job_id: context.job_id,
      date: context.date,
      code: context.code,
      buy: context.buy,
      sell: context.sell,
    });
    const endpointAttrs = {
      'edge-ratio': 'data-analytics-endpoint="/edge_ratio?run_ids="',
      'feature-importance': 'data-analytics-endpoint="/feature_importance?run_id=&gen_no="',
      'variable-correlation': 'data-analytics-endpoint="/variable_correlation?run_id=&gen_no="',
    };
    const endpointCards = ANALYTICS_HANDOFF_ENDPOINTS.map(item => `<div class="analytics-handoff-card" ${endpointAttrs[item.id]}>
      <b>${escapeHtml(item.label)}</b>
      <span>${escapeHtml(item.endpoint)}</span>
      <small>${escapeHtml(item.state)}</small>
    </div>`).join('');
    return `<section class="analytics-handoff-surface" data-analytics-handoff-surface>
      <div class="panel-header"><span>Analytics and workflow handoff</span>${badge('prefill only', 'violet')}</div>
      <div class="notice">No auto-run; handoff only pre-fills the next workflow.</div>
      <div class="notice warn" data-handoff-disabled-reason="${escapeHtml(validation.disabledReason || 'ready')}">${escapeHtml(validation.disabledReason || 'Ready: route/payload preview only.')}</div>
      <div class="analytics-endpoint-grid">${endpointCards}</div>
      <div class="analytics-handoff-grid">
        <div class="analytics-handoff-card" data-condition-to-backtest-handoff data-handoff-route="/ui/remodel/backtest">
          <b>Condition AI → Backtest</b>
          <span>${escapeHtml(conditionHandoff.route)}</span>
          <pre class="preflight-code">${escapeHtml(JSON.stringify(conditionHandoff.payload, null, 2))}</pre>
        </div>
        <div class="analytics-handoff-card" data-backtest-to-replay-handoff data-handoff-route="/ui/remodel/chart-replay">
          <b>Backtest Result → Chart Replay</b>
          <span>${escapeHtml(replayHandoff.route)}</span>
          <pre class="preflight-code">${escapeHtml(JSON.stringify(replayHandoff.payload, null, 2))}</pre>
        </div>
      </div>
    </section>`;
  }

  window.AnalyticsHandoffSurface = {
    endpoints: ANALYTICS_HANDOFF_ENDPOINTS,
    context: analyticsHandoffContext,
    conditionToBacktest: buildConditionToBacktestHandoff,
    backtestToReplay: buildBacktestToReplayHandoff,
    validate: validateAnalyticsHandoff,
    render: renderAnalyticsHandoffSurface,
  };

  const DecisionAuditContracts = [
    { id: 'decisions', method: 'GET', endpoint: '/decisions', owner: 'DecisionAuditAdapter.readOnlyLedger', modeBehavior: 'reference/demo inert fixture - live safe GET on Audit page load', safeAuto: true },
    { id: 'record-decision', method: 'POST', endpoint: '/record_decision', owner: 'Manual researcher action', modeBehavior: 'reference/demo inert fixture - live only after explicit confirm', reason: 'Append-only decision record; no export, broker, order, or approval websocket side effect.' },
  ];

  const DECISION_VERDICTS = ['promote', 'complement', 'hold', 'reject'];

  function decisionAuditDraftContext(input = {}) {
    const handoff = analyticsHandoffContext(input);
    const verdict = String(input.verdict || 'hold').trim().toLowerCase();
    const strategy = String(input.strategy || handoff.buy || DATA.overview.activeStrategy.name || '').trim();
    const note = String(input.note || `run_id=${handoff.run_id || 'missing'} gen_no=${handoff.gen_no} strategy=${strategy || 'missing'} requires additional OOS validation`).trim();
    const context = {
      run_id: String(input.run_id ?? input.runId ?? handoff.run_id ?? '').trim(),
      gen_no: intOrDefault(input.gen_no ?? input.genNo ?? handoff.gen_no, -1),
      strategy,
      verdict,
      note,
      evidence: [
        '/strategy_code?run=&gen=',
        '/backtest_detail?run_id=&gen_no=',
        '/decisions',
      ],
      latest_decision_count: Number((state.decisionAuditPayloads.decisions || {}).count || 0),
    };
    const missing = [];
    if (!context.run_id) missing.push('run_id');
    if (context.gen_no < 0) missing.push('gen_no');
    if (!context.strategy) missing.push('strategy');
    context.status = missing.length ? 'missing-context' : 'ready';
    context.ready = missing.length === 0;
    context.missing = missing;
    context.disabledReason = context.ready ? '' : `Missing ${missing.join(', ')} blocks record_decision.`;
    return context;
  }

  function buildRecordDecisionPayload(draft = decisionAuditDraftContext()) {
    const normalized = String(draft.verdict || '').trim().toLowerCase();
    const contextNote = `run_id=${draft.run_id || 'missing'} gen_no=${draft.gen_no} strategy=${draft.strategy || 'missing'}`;
    const note = String(draft.note || '').includes('run_id=')
      ? String(draft.note || '').trim()
      : `${String(draft.note || '').trim()} | ${contextNote}`.trim();
    return {
      verdict: DECISION_VERDICTS.includes(normalized) ? normalized : '',
      note,
    };
  }

  function validateRecordDecisionPayload(payload) {
    const errors = [];
    const verdict = String((payload || {}).verdict || '').trim().toLowerCase();
    const note = String((payload || {}).note || '').trim();
    if (!DECISION_VERDICTS.includes(verdict)) errors.push('verdict must be promote, complement, hold, or reject');
    if (note.length < 8) errors.push('note is required');
    if (!note.includes('run_id=') || !note.includes('gen_no=') || !note.includes('strategy=')) errors.push('context note is required');
    return {
      ok: errors.length === 0,
      errors,
      disabledReason: errors.length ? errors.join('; ') : '',
    };
  }

  function markDecisionAuditEvidence(id, status, detail, payload = null) {
    state.decisionAuditEvidence[id] = { status, detail };
    if (payload) state.decisionAuditPayloads[id] = payload;
  }

  function decisionRowsFromPayload(payload) {
    const rows = firstArray(payload, ['decisions', 'items', 'rows']);
    return rows.slice(0, 4).map(row => ({
      verdict: row.verdict || row.decision || 'hold',
      note: row.note || 'no note',
      ts: row.ts || row.time || '',
    }));
  }

  function recordDecisionAfterConfirm(payload, confirmFn = window.confirm) {
    const validation = validateRecordDecisionPayload(payload);
    if (!validation.ok) {
      state.lastDecisionRecordStatus = { status: 'validation-error', detail: validation.disabledReason };
      return Promise.resolve(state.lastDecisionRecordStatus);
    }
    const approved = typeof confirmFn === 'function'
      ? confirmFn('Append-only record only; this does not export or place orders.')
      : false;
    if (!approved) {
      state.lastDecisionRecordStatus = { status: 'cancelled', detail: 'Manual confirmation cancelled.' };
      return Promise.resolve(state.lastDecisionRecordStatus);
    }
    if (!isLiveBackendMode) {
      state.lastDecisionRecordStatus = { status: 'inert', detail: 'Reference/demo mode never posts record_decision.' };
      return Promise.resolve(state.lastDecisionRecordStatus);
    }
    state.lastDecisionRecordStatus = { status: 'posting', detail: 'POST /record_decision queued after manual confirm.' };
    return fetch(backendUrl('/record_decision'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
      .then(out => {
        state.lastDecisionRecordStatus = { status: out.status || 'ok', detail: summarizePayload(out) };
        state.decisionAuditProbeStarted = false;
        return DecisionAuditAdapter.ensurePageEvidence().then(() => state.lastDecisionRecordStatus);
      })
      .catch(e => {
        state.lastDecisionRecordStatus = { status: 'record-failed', detail: e.message || 'record_decision failed' };
        return state.lastDecisionRecordStatus;
      });
  }

  function renderDecisionAuditSurface(draft = decisionAuditDraftContext()) {
    const payload = buildRecordDecisionPayload(draft);
    const validation = validateRecordDecisionPayload(payload);
    const decisionList = state.decisionAuditPayloads.decisions || {};
    const recordStatus = state.lastDecisionRecordStatus || { status: 'idle', detail: 'Record failure, duplicate context, missing context, and validation errors stay visible.' };
    const contractCards = DecisionAuditContracts.map(contract => {
      const ev = state.decisionAuditEvidence[contract.id] || {};
      const attrs = contract.id === 'decisions'
        ? 'data-decisions-endpoint="/decisions"'
        : 'data-record-decision-endpoint="/record_decision" data-record-decision-gate="manual-confirm-required"';
      return `<div class="decision-draft-card" ${attrs} data-decision-contract="${escapeHtml(contract.id)}">
        <div class="panel-header"><span>${escapeHtml(contract.method)} ${escapeHtml(contract.endpoint)}</span>${badge(ev.status || (isLiveBackendMode ? 'PENDING' : 'INERT'), cls(ev.status || 'hold'))}</div>
        <div class="muted">${escapeHtml(contract.modeBehavior)}</div>
        <div class="muted">${escapeHtml(ev.detail || contract.reason || 'safe read-only decision ledger')}</div>
      </div>`;
    }).join('');
    const rows = decisionRowsFromPayload(decisionList);
    const history = rows.length
      ? rows.map(row => `<div class="decision-draft-card"><b>${escapeHtml(row.verdict)}</b><span>${escapeHtml(row.note)}</span><small>${escapeHtml(row.ts)}</small></div>`).join('')
      : '<div class="decision-draft-card" data-decision-empty-state>No decision rows yet; /decisions empty state is valid.</div>';
    return `<section class="decision-audit-surface" data-decision-audit-surface data-approval-boundary="separate-route">
      <div class="panel-header"><span>Decision audit contracts</span>${badge(draft.status, draft.ready ? 'green' : 'amber')}</div>
      <div class="notice">Append-only record only; this does not export or place orders.</div>
      <div class="notice warn">final approval remains separate from /record_decision.</div>
      <div class="notice warn" data-record-decision-disabled-reason="${escapeHtml(draft.disabledReason || validation.disabledReason || 'ready')}">Missing verdict/note/context blocks record_decision. ${escapeHtml(draft.disabledReason || validation.disabledReason || 'Ready after manual confirm.')}</div>
      <div class="decision-contract-grid">${contractCards}</div>
      <div class="decision-context-grid">
        <div class="decision-draft-card">${infoList([['run_id', draft.run_id || 'missing'], ['gen_no', String(draft.gen_no)], ['strategy', draft.strategy || 'missing'], ['history_count', String(draft.latest_decision_count)]])}</div>
        <div class="decision-draft-card" data-record-decision-payload="${escapeHtml(JSON.stringify(payload))}">
          <b>record_decision payload preview</b>
          <pre class="preflight-code">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
        </div>
        <div class="decision-boundary-card">
          <b>Approval boundary</b>
          <span>record_decision writes audit history only. Export approval, websocket approval, broker login, and orders stay outside this route.</span>
          ${badge(recordStatus.status, cls(recordStatus.status))}
          <small>${escapeHtml(recordStatus.detail)}</small>
        </div>
      </div>
      <div class="decision-record-grid">${history}</div>
      ${manualBtn('Confirm append-only decision record', 'primary', `data-record-decision-confirm data-record-decision-payload="${escapeHtml(JSON.stringify(payload))}" data-record-decision-disabled-reason="${escapeHtml(validation.disabledReason || '')}"`, 'record-decision-confirm')}
    </section>`;
  }

  const DecisionAuditAdapter = {
    contracts: DecisionAuditContracts,
    ensurePageEvidence() {
      if (!isLiveBackendMode) {
        DecisionAuditContracts.forEach(contract => markDecisionAuditEvidence(contract.id, 'INERT', contract.id === 'decisions' ? 'reference/demo inert - no /decisions fetch' : 'manual-gated - no POST in reference/demo'));
        state.decisionAuditProbeComplete = true;
        return Promise.resolve(false);
      }
      if (state.decisionAuditProbeStarted) return Promise.resolve(true);
      state.decisionAuditProbeStarted = true;
      markDecisionAuditEvidence('decisions', 'PENDING', 'live safe GET queued');
      markDecisionAuditEvidence('record-decision', 'MANUAL-GATED', 'POST /record_decision waits for explicit confirm.');
      return fetchJson('/decisions', 5000)
        .then(payload => markDecisionAuditEvidence('decisions', 'LIVE OK', `${Number(payload.count || 0)} decisions`, payload))
        .catch(e => markDecisionAuditEvidence('decisions', 'LIVE ERROR', e.message || 'request failed'))
        .then(() => {
          state.decisionAuditProbeComplete = true;
          render();
          return true;
        });
    },
  };

  window.DecisionAuditSurface = {
    contracts: DecisionAuditContracts,
    draftContext: decisionAuditDraftContext,
    buildPayload: buildRecordDecisionPayload,
    validatePayload: validateRecordDecisionPayload,
    recordAfterConfirm: recordDecisionAfterConfirm,
    render: renderDecisionAuditSurface,
  };

  function scheduleRenderForEvidence() {
    if (state.evidenceRenderScheduled) return;
    state.evidenceRenderScheduled = true;
    setTimeout(() => {
      state.evidenceRenderScheduled = false;
      render();
    }, 0);
  }

  function markBacktestEvidence(id, status, detail) {
    state.backtestContractEvidence[id] = { status, detail };
    if (isLiveBackendMode && state.primary === 'backtest') scheduleRenderForEvidence();
  }

  const BACKTEST_PREFLIGHT_DEFAULTS = Object.freeze({
    buy: 'BreakOut_v2',
    sell: 'BreakOut_Exit_v1',
    start: '20220101',
    end: '20250516',
    timeframe: 'min',
    engines: 8,
    mode: 'backtest',
    param_space: '',
    train_window_days: 60,
    test_window_days: 20,
    step_days: 5,
    sweep_action: 'param',
    sweep_spec: [{ name: 'fastLen', min: 10, max: 40, step: 5 }],
    sweep_params: '',
    window_days: 20,
    opt_method: 'grid',
    opt_objective: 'tpi',
  });

  function intOrDefault(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function buildBacktestRunPayload(form = {}) {
    const merged = Object.assign({}, BACKTEST_PREFLIGHT_DEFAULTS, form || {});
    const mode = String(merged.mode || 'backtest').trim() || 'backtest';
    const payload = {
      buy: String(merged.buy || '').trim(),
      sell: String(merged.sell || '').trim(),
      start: intOrDefault(merged.start, 0),
      end: intOrDefault(merged.end, 0),
      timeframe: String(merged.timeframe || 'min').trim() || 'min',
      engines: intOrDefault(merged.engines, 4),
      mode,
    };
    if (mode === 'optimize') {
      payload.param_space = String(merged.param_space || '').trim();
      payload.opt_method = String(merged.opt_method || 'grid').trim() || 'grid';
      payload.opt_objective = String(merged.opt_objective || 'tpi').trim() || 'tpi';
    } else if (mode === 'wfo') {
      payload.train_window_days = intOrDefault(merged.train_window_days, 0);
      payload.test_window_days = intOrDefault(merged.test_window_days, 0);
      payload.step_days = intOrDefault(merged.step_days, 0);
      payload.opt_method = String(merged.opt_method || 'grid').trim() || 'grid';
      payload.opt_objective = String(merged.opt_objective || 'tpi').trim() || 'tpi';
      if (String(merged.param_space || '').trim()) payload.param_space = String(merged.param_space).trim();
    } else if (mode === 'sweep') {
      payload.sweep_action = String(merged.sweep_action || 'param').trim() || 'param';
      if (payload.sweep_action === 'rolling') {
        payload.window_days = intOrDefault(merged.window_days, 0);
        payload.step_days = intOrDefault(merged.step_days, 0);
      } else if (String(merged.sweep_params || '').trim()) {
        payload.sweep_params = String(merged.sweep_params).trim();
      } else {
        payload.sweep_spec = Array.isArray(merged.sweep_spec)
          ? merged.sweep_spec
              .filter(row => row && String(row.name || '').trim())
              .map(row => ({
                name: String(row.name).trim(),
                min: Number(row.min),
                max: Number(row.max),
                step: Number(row.step),
              }))
          : [];
      }
    }
    return payload;
  }

  function validateBacktestRunPayload(payload) {
    const reasons = [];
    if (!payload || !payload.buy || !payload.sell) reasons.push('buy/sell strategy names are required');
    if (!/^\d{8}$/.test(String(payload && payload.start))) reasons.push('start must be YYYYMMDD');
    if (!/^\d{8}$/.test(String(payload && payload.end))) reasons.push('end must be YYYYMMDD');
    if (payload && payload.start && payload.end && Number(payload.end) < Number(payload.start)) reasons.push('end must be on or after start');
    if (payload && Number(payload.engines) < 1) reasons.push('engines must be >= 1');
    if (payload && payload.mode === 'optimize' && !payload.param_space) reasons.push('optimize requires param_space');
    if (payload && payload.mode === 'wfo' && (Number(payload.train_window_days) < 1 || Number(payload.test_window_days) < 1)) reasons.push('wfo requires train/test windows');
    if (payload && payload.mode === 'sweep') {
      if (payload.sweep_action === 'rolling' && (Number(payload.window_days) < 1 || Number(payload.step_days) < 1)) reasons.push('rolling sweep requires window_days and step_days');
      if (payload.sweep_action !== 'rolling' && !payload.sweep_params && (!Array.isArray(payload.sweep_spec) || !payload.sweep_spec.length)) reasons.push('param sweep requires sweep_spec or sweep_params');
      const badSweepRow = Array.isArray(payload.sweep_spec)
        ? payload.sweep_spec.find(row => !Number.isFinite(row.min) || !Number.isFinite(row.max) || !Number.isFinite(row.step))
        : null;
      if (badSweepRow) reasons.push(`sweep variable ${badSweepRow.name} needs numeric min/max/step`);
    }
    return {
      ok: reasons.length === 0,
      reasons,
      disabledReason: reasons.join(' · '),
      summary: reasons.length ? 'Invalid preflight blocks /bt/run before confirm.' : 'Payload matches V2 /bt/run shape.',
      confirmRequired: true,
    };
  }

  function renderBacktestPreflightPanel() {
    const payload = buildBacktestRunPayload();
    const validation = validateBacktestRunPayload(payload);
    const modeText = isLiveBackendMode
      ? 'Live mode requires a manual confirm before POST /bt/run.'
      : 'Reference/demo preflight only; /bt/run is not called.';
    const disabledReason = validation.ok
      ? (isLiveBackendMode ? 'Manual confirmation required before request.' : 'Reference/demo mode keeps POST inert.')
      : validation.disabledReason;
    return `<div class="backtest-preflight-panel" data-backtest-run-payload-shape="buy|sell|start|end|timeframe|engines|mode">
      <div class="preflight-grid">
        <div data-backtest-validation-summary="${escapeHtml(validation.summary)}">
          ${badge(validation.ok ? 'PREFLIGHT PASS' : 'PREFLIGHT BLOCKED', validation.ok ? 'green' : 'red')}
          <p>${escapeHtml(modeText)}</p>
          <p class="muted">${escapeHtml(validation.summary)}</p>
        </div>
        <div data-backtest-disabled-reason="${escapeHtml(disabledReason)}">
          <b>Disabled reason</b>
          <p>${escapeHtml(disabledReason)}</p>
        </div>
      </div>
      <pre class="preflight-code" data-backtest-preflight-payload>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
      <div class="bt-action-row" data-backtest-confirm-gate="manual-required">
        ${manualBtn('Confirm gated /bt/run payload', 'primary small', '', 'bt-run-preview')}
        <span class="muted">${escapeHtml(modeText)}</span>
      </div>
    </div>`;
  }

  window.BacktestPreflight = {
    defaults: BACKTEST_PREFLIGHT_DEFAULTS,
    buildRunPayload: buildBacktestRunPayload,
    validateRunPayload: validateBacktestRunPayload,
  };

  const BACKTEST_JOB_STATES = Object.freeze([
    'idle',
    'pending',
    'running',
    'success',
    'error',
    'cancelled',
    'missing-job',
    'unknown-job',
    'ws-closed',
    'terminal',
  ]);

  function normalizeBacktestJobMessage(message = {}) {
    const jobId = String(message.job_id || message.jobId || '').trim();
    if (message.error) {
      const status = jobId ? 'unknown-job' : 'missing-job';
      return {
        job_id: jobId,
        status,
        phase: 'error',
        progress: 0,
        terminal: true,
        message: String(message.error || ''),
        log_tail: [],
      };
    }
    const rawStatus = String(message.status || 'idle').trim() || 'idle';
    const status = rawStatus === 'failed' ? 'error' : rawStatus === 'canceled' ? 'cancelled' : rawStatus;
    const terminal = Boolean(message.terminal) || ['success', 'error', 'cancelled'].includes(status);
    const progress = Math.max(0, Math.min(1, Number(message.progress || (terminal ? 1 : 0))));
    return {
      job_id: jobId,
      status: BACKTEST_JOB_STATES.includes(status) ? status : 'error',
      phase: String(message.phase || (terminal ? 'done' : status)),
      progress,
      terminal,
      message: String(message.message || ''),
      elapsed: Number(message.elapsed || 0),
      log_tail: Array.isArray(message.log_tail) ? message.log_tail : [],
    };
  }

  function backtestJobWsPath(jobId) {
    return `/bt/ws_job?job_id=${encodeURIComponent(String(jobId || '').trim())}`;
  }

  function renderBacktestJobProgressPanel() {
    const running = normalizeBacktestJobMessage({
      job_id: 'J10235',
      status: 'running',
      progress: 0.634,
      phase: 'running',
      elapsed: 78,
      log_tail: ['prepare strategies', 'load bars', 'running engine shard 3/8'],
    });
    const terminal = normalizeBacktestJobMessage({
      job_id: 'J10234',
      status: 'success',
      progress: 1,
      phase: 'done',
      terminal: true,
      message: 'result ready',
    });
    const missing = normalizeBacktestJobMessage({ error: 'job_id is required' });
    const unknown = normalizeBacktestJobMessage({ job_id: 'nope', error: 'job_id not found' });
    const percent = Math.round(running.progress * 1000) / 10;
    return `<div class="backtest-job-progress" data-backtest-job-progress data-backtest-ws-path="/bt/ws_job?job_id=J10235">
      <div class="job-state-grid">
        <div>
          ${badge(running.status, 'blue')}
          <b>${escapeHtml(running.job_id)}</b>
          <p>WebSocket observer is manual-gated; no stream opens on page load.</p>
        </div>
        <div data-backtest-terminal-state="${escapeHtml(terminal.status)}">
          ${badge(terminal.terminal ? 'terminal' : terminal.status, terminal.terminal ? 'green' : 'amber')}
          <p>Result fetch waits for terminal job evidence.</p>
        </div>
        <div data-backtest-job-error="missing-job">${badge(missing.status, 'red')}<p>${escapeHtml(missing.message)}</p></div>
        <div data-backtest-job-error="unknown-job">${badge(unknown.status, 'red')}<p>${escapeHtml(unknown.message)}</p></div>
      </div>
      <div class="progress"><span style="width:${percent}%"></span></div>
      <div class="job-log-tail">${running.log_tail.map(escapeHtml).join(' · ')}</div>
    </div>`;
  }

  window.BacktestJobProgress = {
    states: BACKTEST_JOB_STATES,
    normalizeMessage: normalizeBacktestJobMessage,
    jobWsPath: backtestJobWsPath,
  };

  const BACKTEST_ANALYSIS_SURFACES = Object.freeze([
    { id: 'result', label: 'Result summary', endpoint: '/bt/result?job_id=__demo__', state: 'safe demo read' },
    { id: 'summary', label: 'Summary metrics', endpoint: '/bt/analysis/summary?job_id=', state: 'completed job required' },
    { id: 'equity', label: 'Equity curve', endpoint: '/bt/analysis/equity?job_id=', state: 'completed job required' },
    { id: 'distribution', label: 'PnL distribution', endpoint: '/bt/analysis/distribution?job_id=', state: 'completed job required' },
    { id: 'heatmap', label: 'Time heatmap', endpoint: '/bt/analysis/heatmap?job_id=', state: 'completed job required' },
    { id: 'underwater', label: 'Underwater', endpoint: '/bt/analysis/underwater?job_id=', state: 'completed job required' },
    { id: 'insights', label: 'Insights', endpoint: '/bt/analysis/insights?job_id=', state: 'completed job required' },
    { id: 'mae-mfe', label: 'MAE/MFE', endpoint: '/bt/analysis/mae_mfe?job_id=', state: 'completed job required' },
    { id: 'exit-reasons', label: 'Exit reasons', endpoint: '/bt/analysis/exit_reasons?job_id=', state: 'completed job required' },
    { id: 'montecarlo', label: 'Monte Carlo', endpoint: '/bt/analysis/montecarlo?job_id=', state: 'completed job required' },
    { id: 'orderflow', label: 'Orderflow', endpoint: '/bt/analysis/orderflow?job_id=', state: 'completed job required' },
    { id: 'gui-parity', label: 'GUI parity', endpoint: '/bt/analysis/gui_parity?job_id=', state: 'completed job required' },
    { id: 'compare', label: 'Compare', endpoint: '/bt/compare?job_a=&job_b=', state: 'two completed jobs required' },
    { id: 'overlay', label: 'Overlay', endpoint: '/bt/overlay?job_ids=', state: 'two to four completed jobs required' },
    { id: 'report', label: 'HTML report', endpoint: '/bt/report?job_id=', state: 'completed job required' },
  ]);

  function renderBacktestAnalysisSurface() {
    const items = BACKTEST_ANALYSIS_SURFACES.map(surface => `<div class="analysis-surface-item" data-backtest-analysis-surface="${escapeHtml(surface.id)}">
      <b>${escapeHtml(surface.label)}</b>
      <span>${escapeHtml(surface.endpoint)}</span>
      <small>${escapeHtml(surface.state)}</small>
    </div>`).join('');
    return `<div class="backtest-analysis-surface">
      <div class="notice" data-backtest-result-empty>No completed job selected; analysis calls remain disabled.</div>
      <div class="notice warn" data-backtest-compare-disabled-reason="Need two completed job ids before compare.">Need two completed job ids before compare.</div>
      <div class="notice" data-backtest-report-state="disabled">Report opens only for existing completed job evidence.</div>
      <div class="analysis-surface-grid">${items}</div>
    </div>`;
  }

  window.BacktestAnalysisSurface = {
    surfaces: BACKTEST_ANALYSIS_SURFACES,
    render: renderBacktestAnalysisSurface,
  };

  function firstReplayDateCode(payload) {
    const rows = firstArray(payload, ['demos', 'items', 'rows', 'stocks', 'codes']);
    const row = rows.find(x => x && (x.date || x.day || x.trading_day || x.code || x.stock_code)) || {};
    const date = payload && typeof payload === 'object'
      ? (payload.date || payload.day || payload.trading_day || row.date || row.day || row.trading_day || '')
      : '';
    const code = payload && typeof payload === 'object'
      ? (payload.code || payload.stock_code || payload.symbol || row.code || row.stock_code || row.symbol || '')
      : '';
    return { date, code };
  }

  function markReplayEvidence(id, status, detail) {
    state.replayContractEvidence[id] = { status, detail };
  }

  const REPLAY_PREFLIGHT_DEFAULTS = Object.freeze({
    src: 'min',
    date: '20250516',
    code: '005930',
    codes: ['005930'],
    speed: 1,
    agg_sec: 10,
    buy: 'BreakOut_v2',
    sell: 'BreakOut_Exit_v1',
  });

  function buildReplayStartPayload(form = {}) {
    const merged = Object.assign({}, REPLAY_PREFLIGHT_DEFAULTS, form || {});
    const explicitCodes = Array.isArray(merged.codes)
      ? merged.codes.map(code => String(code || '').trim()).filter(Boolean)
      : [];
    const fallbackCode = String(merged.code || '').trim();
    const codes = explicitCodes.length ? explicitCodes : (fallbackCode ? [fallbackCode] : []);
    return {
      action: 'start',
      date: intOrDefault(merged.date, 0),
      src: String(merged.src || 'min').trim() || 'min',
      codes,
      speed: Number(merged.speed || 1),
      agg_sec: intOrDefault(merged.agg_sec, 10),
      buy: String(merged.buy || '').trim(),
      sell: String(merged.sell || '').trim(),
    };
  }

  function validateReplayStartPayload(payload) {
    const reasons = [];
    if (!payload || !/^\d{8}$/.test(String(payload.date))) reasons.push('date must be YYYYMMDD');
    if (!payload || !Array.isArray(payload.codes) || !payload.codes.length) reasons.push('code selection is required');
    if (!payload || !['min', 'tick'].includes(String(payload.src || ''))) reasons.push('src must be min or tick');
    if (!payload || Number(payload.speed) <= 0) reasons.push('speed must be positive');
    if (!payload || Number(payload.agg_sec) < 1) reasons.push('agg_sec must be >= 1');
    if (!payload || !payload.buy || !payload.sell) reasons.push('buy/sell strategy names are required');
    return {
      ok: reasons.length === 0,
      reasons,
      disabledReason: reasons.join(' · '),
      summary: reasons.length ? 'Missing date/code blocks /sim/ws start before confirm.' : 'Replay start payload matches V2 /sim/ws action shape.',
      confirmRequired: true,
    };
  }

  function renderReplayPreflightPanel() {
    const payload = buildReplayStartPayload();
    const validation = validateReplayStartPayload(payload);
    const modeText = isLiveBackendMode
      ? 'Live mode requires manual /sim/ws start confirmation.'
      : 'Reference/demo replay preflight only; /sim/ws is not opened.';
    const disabledReason = validation.ok
      ? (isLiveBackendMode ? 'Manual confirmation required before WebSocket start.' : 'Reference/demo mode keeps /sim/ws inert.')
      : validation.disabledReason;
    return `<div class="replay-preflight-panel" data-replay-start-payload-shape="action|date|src|codes|speed|agg_sec|buy|sell">
      <div class="replay-preflight-grid" data-replay-dataset-selector>
        <div>${badge(validation.ok ? 'DATASET READY' : 'DATASET BLOCKED', validation.ok ? 'green' : 'red')}<p>${escapeHtml(validation.summary)}</p></div>
        <div data-replay-disabled-reason="${escapeHtml(disabledReason)}"><b>Disabled reason</b><p>${escapeHtml(disabledReason)}</p></div>
      </div>
      <pre class="preflight-code" data-replay-preflight-payload>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
      <div class="bt-action-row" data-replay-start-gate="manual-required">
        ${manualBtn('Confirm gated /sim/ws start', 'primary small', '', 'sim-start')}
        <span class="muted">${escapeHtml(modeText)}</span>
      </div>
    </div>`;
  }

  window.ReplayPreflight = {
    defaults: REPLAY_PREFLIGHT_DEFAULTS,
    buildStartPayload: buildReplayStartPayload,
    validateStartPayload: validateReplayStartPayload,
  };

  const REPLAY_PLAYBACK_STATES = Object.freeze([
    'idle',
    'ready',
    'playing',
    'paused',
    'seeking',
    'done',
    'error',
    'over-limit',
  ]);

  function replayWsActionPayload(action, patch = {}) {
    const kind = String(action || '').trim();
    if (kind === 'start') return buildReplayStartPayload(patch);
    if (kind === 'pause' || kind === 'resume' || kind === 'stop') return { action: kind };
    if (kind === 'speed') return { action: 'speed', value: Number(patch.value || patch.speed || 1) };
    if (kind === 'seek') return { action: 'seek', t: intOrDefault(patch.t || patch.cursor || 0, 0) };
    return { action: kind || 'unknown' };
  }

  function normalizeReplayWsMessage(message = {}) {
    const kind = String(message.type || message.kind || message.action || '').trim() || (message.error ? 'error' : 'unknown');
    if (kind === 'error' || message.error) {
      const text = String(message.error || message.message || '');
      return {
        kind: 'error',
        state: /limit/i.test(text) ? 'over-limit' : 'error',
        terminal: false,
        message: text || 'Replay WebSocket error',
      };
    }
    if (kind === 'done') return { kind, state: 'done', terminal: true, bars: 0, message: 'Replay completed' };
    if (kind === 'meta') return { kind, state: 'playing', terminal: false, bars_total: Number(message.bars_total || 0), codes: message.codes || [] };
    if (kind === 'bars' || kind === 'history') return { kind, state: 'playing', terminal: false, bars: firstArray(message, ['items', 'bars', 'history']).length };
    return { kind, state: REPLAY_PLAYBACK_STATES.includes(kind) ? kind : 'ready', terminal: false };
  }

  function renderReplayPlaybackControls() {
    const actions = [
      ['start', 'Start', 'data-replay-ws-action="start"'],
      ['pause', 'Pause', 'data-replay-ws-action="pause"'],
      ['resume', 'Resume', 'data-replay-ws-action="resume"'],
      ['speed', 'Speed x2', 'data-replay-ws-action="speed"'],
      ['seek', 'Seek 093000', 'data-replay-ws-action="seek"'],
      ['stop', 'Stop', 'data-replay-ws-action="stop"'],
    ];
    const actionButtons = actions.map(([action, label, attrs]) => manualBtn(label, 'small', attrs, `sim-${action}`)).join('');
    const messages = [
      normalizeReplayWsMessage({ type: 'meta', codes: ['005930'], bars_total: 4200 }),
      normalizeReplayWsMessage({ type: 'bars', items: [{ t: 93000 }, { t: 93001 }] }),
      normalizeReplayWsMessage({ type: 'history', history: [{ t: 92500 }] }),
      normalizeReplayWsMessage({ type: 'done' }),
      normalizeReplayWsMessage({ type: 'error', error: 'over session limit' }),
    ];
    const messageItems = messages.map(item => `<div class="replay-message-chip" data-replay-ws-message-kind="${escapeHtml(item.kind)}">
      <b>${escapeHtml(item.kind)}</b><span>${escapeHtml(item.state)}</span>
    </div>`).join('');
    return `<div class="replay-playback-controls" data-replay-playback-controls>
      <div class="notice">Playback controls build /sim/ws messages only after manual start.</div>
      <div class="bt-action-row">${actionButtons}</div>
      <div class="replay-message-grid">${messageItems}</div>
      <div class="notice danger">Over session limit remains visible as error state.</div>
    </div>`;
  }

  window.ReplayPlayback = {
    states: REPLAY_PLAYBACK_STATES,
    actionPayload: replayWsActionPayload,
    normalizeMessage: normalizeReplayWsMessage,
  };

  const REPLAY_TIMELINE_EMPTY_TEXT = 'No signal/trade data for selected replay cursor.';

  function replayTimelineCursor(payload = {}) {
    const bars = firstArray(payload, ['bars', 'items', 'history']);
    const signals = firstArray(payload, ['signals', 'signalLog', 'signal_log']);
    const trades = firstArray(payload, ['trades', 'fills', 'orders']);
    const positions = firstArray(payload, ['positions', 'positionRows']);
    const logs = firstArray(payload, ['logs', 'events']);
    const maxIndex = Math.max(0, bars.length - 1);
    const requestedIndex = payload.selectedIndex ?? payload.index ?? payload.cursor ?? maxIndex;
    const selectedIndex = Math.max(0, Math.min(maxIndex, intOrDefault(requestedIndex, maxIndex)));
    const selectedBar = bars[selectedIndex] || bars[maxIndex] || {};
    const firstSignal = signals[0] || {};
    const selectedTime = String(payload.selectedTime || selectedBar.time || selectedBar.t || firstSignal.time || 'n/a');
    const selectedCode = String(payload.selectedCode || selectedBar.code || selectedBar.stock || firstSignal.stock || payload.code || '');
    return {
      bars,
      signals,
      trades,
      positions,
      logs,
      selectedIndex,
      selectedTime,
      selectedCode,
      selectedBar,
      hasSignals: signals.length > 0,
      hasTrades: trades.length > 0,
      emptyText: REPLAY_TIMELINE_EMPTY_TEXT,
    };
  }

  function replayTimelineHandoffContext(input = {}) {
    const codeFromList = Array.isArray(input.codes) && input.codes.length ? input.codes[0] : '';
    const date = String(input.date || input.day || input.trading_day || REPLAY_PREFLIGHT_DEFAULTS.date || '').trim();
    const code = String(input.code || input.stock_code || input.symbol || codeFromList || REPLAY_PREFLIGHT_DEFAULTS.code || '').trim();
    const buy = String(input.buy || input.buy_name || input.buyStrategy || input.strategy || REPLAY_PREFLIGHT_DEFAULTS.buy || '').trim();
    const sell = String(input.sell || input.sell_name || input.sellStrategy || REPLAY_PREFLIGHT_DEFAULTS.sell || '').trim();
    const src = String(input.src || input.timeframe || REPLAY_PREFLIGHT_DEFAULTS.src || 'min').trim() || 'min';
    const prefillReady = Boolean(date && code && buy && sell);
    return {
      source: 'bt-result-localStorage-event',
      date,
      code,
      buy,
      sell,
      src,
      selectedIndex: intOrDefault(input.selectedIndex ?? input.cursor ?? 0, 0),
      prefillReady,
      reason: prefillReady ? 'Backtest result handoff can prefill replay preflight.' : 'Need date, code, buy, and sell before replay prefill.',
    };
  }

  function replayTimelineEventText(row = {}, fallbackTime = 'n/a') {
    const time = row.time || row.t || row.buy_hms || row.sell_hms || fallbackTime;
    const label = row.signal || row.action || row.side || row.status || row.reason || row.message || row.kind || 'event';
    const price = row.price || row.c || row.close || row.buy_price || row.sell_price || '';
    return `${time} · ${label}${price ? ` · ${price}` : ''}`;
  }

  function renderReplayTimelineSurface(data = {}, selectedStock = {}) {
    const cursor = replayTimelineCursor(data);
    const handoff = replayTimelineHandoffContext(data.handoff || {
      date: REPLAY_PREFLIGHT_DEFAULTS.date,
      code: cursor.selectedCode || selectedStock.code,
      buy: REPLAY_PREFLIGHT_DEFAULTS.buy,
      sell: REPLAY_PREFLIGHT_DEFAULTS.sell,
      src: REPLAY_PREFLIGHT_DEFAULTS.src,
      selectedIndex: cursor.selectedIndex,
    });
    const cursorPct = cursor.bars.length > 1 ? Math.round(cursor.selectedIndex / (cursor.bars.length - 1) * 1000) / 10 : 0;
    const signalItems = cursor.signals.length
      ? cursor.signals.slice(0, 5).map(row => `<div class="replay-event-item" data-replay-event-kind="signal"><b>${escapeHtml(row.signal || 'SIGNAL')}</b><span>${escapeHtml(replayTimelineEventText(row, cursor.selectedTime))}</span></div>`).join('')
      : `<div class="replay-empty-state" data-replay-empty-signals data-replay-event-kind="signal">${escapeHtml(REPLAY_TIMELINE_EMPTY_TEXT)}</div>`;
    const tradeItems = cursor.trades.length
      ? cursor.trades.slice(0, 5).map(row => `<div class="replay-event-item" data-replay-event-kind="trade"><b>${escapeHtml(row.side || row.action || 'TRADE')}</b><span>${escapeHtml(replayTimelineEventText(row, cursor.selectedTime))}</span></div>`).join('')
      : `<div class="replay-empty-state" data-replay-empty-trades data-replay-event-kind="trade">${escapeHtml(REPLAY_TIMELINE_EMPTY_TEXT)}</div>`;
    const positionItems = cursor.positions.length
      ? cursor.positions.slice(0, 4).map(row => `<div class="replay-event-item" data-replay-event-kind="position"><b>${escapeHtml(row.code || cursor.selectedCode || 'POSITION')}</b><span>${escapeHtml(row.qty || row.size || row.status || 'position snapshot')}</span></div>`).join('')
      : `<div class="replay-empty-state" data-replay-event-kind="position">No open position snapshot for selected cursor.</div>`;
    const logItems = cursor.logs.length
      ? cursor.logs.slice(0, 4).map(row => `<div class="replay-event-item" data-replay-event-kind="log"><b>LOG</b><span>${escapeHtml(typeof row === 'string' ? row : replayTimelineEventText(row, cursor.selectedTime))}</span></div>`).join('')
      : `<div class="replay-empty-state" data-replay-event-kind="log">No replay log event at this cursor.</div>`;
    return `<section class="replay-timeline-surface" data-replay-timeline-surface data-replay-cursor-source="shared">
      <div class="panel-header"><span>Replay cursor timeline · signals/trades/positions/logs</span>${badge('shared cursor', 'blue')}</div>
      <div class="replay-timeline" data-replay-timeline role="slider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${cursorPct}"><span style="width:${cursorPct}%"></span></div>
      <div class="replay-detail-grid">
        <div class="replay-selected-detail" data-replay-selected-detail>
          ${infoList([['selectedIndex', String(cursor.selectedIndex)], ['selectedTime', cursor.selectedTime], ['selectedCode', cursor.selectedCode || selectedStock.code || 'n/a'], ['bars', String(cursor.bars.length)], ['signals', String(cursor.signals.length)], ['trades', String(cursor.trades.length)]])}
        </div>
        <div class="replay-handoff-card" data-replay-backtest-handoff data-replay-handoff-source="bt-result-localStorage-event" data-replay-prefill-ready="${handoff.prefillReady ? 'true' : 'false'}">
          <b>Backtest result handoff prefill</b>
          <span>${escapeHtml(handoff.reason)}</span>
          ${infoList([['date', handoff.date], ['code', handoff.code], ['buy', handoff.buy], ['sell', handoff.sell], ['src', handoff.src]])}
        </div>
      </div>
      <div class="replay-event-timeline">
        <div>${signalItems}</div>
        <div>${tradeItems}</div>
        <div>${positionItems}</div>
        <div>${logItems}</div>
      </div>
    </section>`;
  }

  window.ReplayTimeline = {
    emptyText: REPLAY_TIMELINE_EMPTY_TEXT,
    normalizeCursor: replayTimelineCursor,
    handoffContext: replayTimelineHandoffContext,
    render: renderReplayTimelineSurface,
  };

  const BacktestAdapter = {
    contracts: BacktestContracts,
    inertReason: INERT_BACKTEST_STATUS,
    ensurePageEvidence() {
      if (!isLiveBackendMode) {
        BacktestContracts.forEach(c => markBacktestEvidence(c.id, 'INERT', INERT_BACKTEST_STATUS));
        state.backtestProbeComplete = true;
        return Promise.resolve(false);
      }
      if (state.backtestProbeStarted) return Promise.resolve(true);
      state.backtestProbeStarted = true;
      BacktestContracts.forEach(c => {
        if (c.method === 'POST') {
          markBacktestEvidence(c.id, 'MANUAL-GATED', c.reason || 'Mutating endpoint is never auto-invoked.');
        } else if (c.safeAuto === true) {
          markBacktestEvidence(c.id, 'PENDING', 'live read probe queued');
        } else {
          markBacktestEvidence(c.id, 'NOT-USED', c.reason || 'Needs existing strategy/job context; no automatic call without evidence key.');
        }
      });
      const reads = BacktestContracts.filter(c => c.safeAuto === true && c.livePath).map(c =>
        fetchJson(c.livePath, 5000)
          .then(payload => {
            markBacktestEvidence(c.id, 'LIVE OK', summarizePayload(payload));
            if (c.id === 'bt-jobs') {
              state.backtestExistingJobIds = firstJobIds(payload);
              state.backtestExistingRunIds = firstRunIds(payload);
            }
            if (c.id === 'bt-strategies-buy') {
              const name = firstNamedStrategy(payload);
              if (name) return BacktestAdapter.fetchStrategyContext('buy', name);
            }
            if (c.id === 'bt-strategies-sell') {
              const name = firstNamedStrategy(payload);
              if (name) return BacktestAdapter.fetchStrategyContext('sell', name);
            }
          })
          .catch(e => markBacktestEvidence(c.id, 'LIVE ERROR', e.message || 'request failed'))
      );
      return Promise.all(reads).then(() => BacktestAdapter.fetchJobContext()).then(() => {
        state.backtestProbeComplete = true;
        render();
        return true;
      });
    },
    fetchStrategyContext(kind, name) {
      if (!isLiveBackendMode || !kind || !name) return Promise.resolve(false);
      const q = `kind=${encodeURIComponent(kind)}&name=${encodeURIComponent(name)}`;
      return Promise.all([
        fetchJson(`/bt/strategy?${q}`, 5000).then(p => markBacktestEvidence('bt-strategy-detail', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-strategy-detail', 'LIVE ERROR', e.message || 'request failed')),
        fetchJson(`/bt/legacy/self_vars?${q}`, 5000).then(p => markBacktestEvidence('bt-legacy-self-vars', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-legacy-self-vars', 'LIVE ERROR', e.message || 'request failed')),
        fetchJson(`/bt/backfinder/preflight?${q}`, 5000).then(p => markBacktestEvidence('bt-backfinder-preflight', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-backfinder-preflight', 'LIVE ERROR', e.message || 'request failed'))
      ]);
    },
    fetchJobContext() {
      if (!isLiveBackendMode) return Promise.resolve(false);
      const ids = state.backtestExistingJobIds || [];
      const runIds = state.backtestExistingRunIds || [];
      const jobReads = [];
      if (!ids.length) {
        ['bt-job', 'bt-report', 'bt-overlay', 'bt-compare'].forEach(id => markBacktestEvidence(id, 'NOT-USED', 'No existing job_id returned by /bt/jobs.'));
      } else {
        const jobId = encodeURIComponent(ids[0]);
        jobReads.push(fetchJson(`/bt/job?job_id=${jobId}`, 5000).then(p => markBacktestEvidence('bt-job', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-job', 'LIVE ERROR', e.message || 'request failed')));
        jobReads.push(fetchText(`/bt/report?job_id=${jobId}`, 5000).then(text => markBacktestEvidence('bt-report', 'LIVE OK', `HTML report ${text.length} chars`)).catch(e => markBacktestEvidence('bt-report', 'LIVE ERROR', e.message || 'request failed')));
        jobReads.push(fetchJson(`/bt/overlay?job_ids=${ids.map(encodeURIComponent).join(',')}`, 5000).then(p => markBacktestEvidence('bt-overlay', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-overlay', 'LIVE ERROR', e.message || 'request failed')));
        if (ids.length >= 2) {
          jobReads.push(fetchJson(`/bt/compare?job_a=${encodeURIComponent(ids[0])}&job_b=${encodeURIComponent(ids[1])}`, 5000).then(p => markBacktestEvidence('bt-compare', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-compare', 'LIVE ERROR', e.message || 'request failed')));
        } else {
          markBacktestEvidence('bt-compare', 'NOT-USED', 'Need two existing job ids; /bt/jobs returned fewer than two.');
        }
      }
      if (runIds.length) {
        jobReads.push(fetchJson(`/bt/evo_gens?run_id=${encodeURIComponent(runIds[0])}`, 5000).then(p => markBacktestEvidence('bt-evo-gens', 'LIVE OK', summarizePayload(p))).catch(e => markBacktestEvidence('bt-evo-gens', 'LIVE ERROR', e.message || 'request failed')));
      } else {
        markBacktestEvidence('bt-evo-gens', 'NOT-USED', 'No existing run_id returned by /bt/jobs.');
      }
      return Promise.all(jobReads).then(() => true);
    }
  };
  window.BacktestContracts = BacktestContracts;
  window.BacktestAdapter = BacktestAdapter;
  const ReplayAdapter = {
    contracts: ReplayContracts,
    inertReason: INERT_REPLAY_STATUS,
    ensurePageEvidence() {
      if (!isLiveBackendMode) {
        ReplayContracts.forEach(c => markReplayEvidence(c.id, 'INERT', INERT_REPLAY_STATUS));
        state.replayProbeComplete = true;
        return Promise.resolve(false);
      }
      if (state.replayProbeStarted) return Promise.resolve(true);
      state.replayProbeStarted = true;
      ReplayContracts.forEach(c => {
        if (c.safeAuto === true) {
          markReplayEvidence(c.id, 'PENDING', 'live read probe queued');
        } else if (c.method === 'WS' || c.method === 'ACTION' || c.method === 'MESSAGE') {
          markReplayEvidence(c.id, 'USER-GATED', c.reason || '/sim/ws protocol is live-only and never auto-opened.');
        } else {
          markReplayEvidence(c.id, 'NOT-USED', c.reason || 'Needs demo date/code or strategy names; no fake success without discovered keys.');
        }
      });
      const reads = ReplayContracts.filter(c => c.safeAuto === true && c.livePath).map(c =>
        fetchJson(c.livePath, 5000)
          .then(payload => {
            markReplayEvidence(c.id, 'LIVE OK', summarizePayload(payload));
            if (c.id === 'sim-demo-latest') {
              const discovered = firstReplayDateCode(payload);
              state.replayDiscoveredDate = discovered.date || state.replayDiscoveredDate;
              state.replayDiscoveredCode = discovered.code || state.replayDiscoveredCode;
            }
            if (c.id === 'bt-replay-strategies-buy') state.replayDiscoveredBuy = firstNamedStrategy(payload) || state.replayDiscoveredBuy;
            if (c.id === 'bt-replay-strategies-sell') state.replayDiscoveredSell = firstNamedStrategy(payload) || state.replayDiscoveredSell;
          })
          .catch(e => markReplayEvidence(c.id, 'LIVE ERROR', e.message || 'request failed'))
      );
      return Promise.all(reads).then(() => ReplayAdapter.fetchReplayContext()).then(() => {
        state.replayProbeComplete = true;
        render();
        return true;
      });
    },
    fetchReplayContext() {
      if (!isLiveBackendMode) return Promise.resolve(false);
      const date = state.replayDiscoveredDate;
      const code = state.replayDiscoveredCode;
      const buy = state.replayDiscoveredBuy;
      const sell = state.replayDiscoveredSell;
      const reads = [];
      if (date) {
        reads.push(fetchJson(`/sim/stocks?date=${encodeURIComponent(date)}&src=min`, 5000).then(p => markReplayEvidence('sim-stocks', 'LIVE OK', summarizePayload(p))).catch(e => markReplayEvidence('sim-stocks', 'LIVE ERROR', e.message || 'request failed')));
      } else {
        markReplayEvidence('sim-stocks', 'NOT-USED', 'No date returned by /sim/demo?src=min&mode=latest.');
      }
      if (date && code && buy && sell) {
        reads.push(fetchJson(`/sim/signals?date=${encodeURIComponent(date)}&src=min&code=${encodeURIComponent(code)}&buy=${encodeURIComponent(buy)}&sell=${encodeURIComponent(sell)}`, 5000).then(p => markReplayEvidence('sim-signals', 'LIVE OK', summarizePayload(p))).catch(e => markReplayEvidence('sim-signals', 'LIVE ERROR', e.message || 'request failed')));
      } else {
        markReplayEvidence('sim-signals', 'NOT-USED', 'Need date, code, buy strategy, and sell strategy from live discovery before probing signals.');
      }
      return Promise.all(reads).then(() => true);
    }
  };
  window.ReplayContracts = ReplayContracts;
  window.ReplayAdapter = ReplayAdapter;

  function numberOr(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function money(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return String(value ?? '—');
    return (n >= 0 ? '+' : '') + Math.round(n).toLocaleString('ko-KR');
  }

  function pctValue(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return String(value ?? '—');
    return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
  }

  function mapLoopState(payload) {
    if (!payload || typeof payload !== 'object') return;
    state.latestLoopPayload = payload;
    const shell = DATA.shell;
    const gens = Array.isArray(payload.generations) ? payload.generations : [];
    const maxGen = Math.max(1, numberOr(payload.max_generations, gens.length || 1));
    const currentGen = Math.max(0, numberOr(payload.current_gen, gens.length ? gens[gens.length - 1].gen_no : 0));
    const progress = maxGen > 0 ? Math.max(0, Math.min(100, currentGen / maxGen * 100)) : 0;
    shell.restHealth = 'UP';
    shell.runStatus = payload.status || shell.runStatus;
    shell.provider = payload.provider || shell.provider;
    shell.timeframe = payload.bt_timeframe || shell.timeframe;
    shell.runId = payload.run_id || shell.runId || '—';
    shell.generationProgress = progress.toFixed(1);
    shell.generationText = `Gen ${currentGen} / 목표 ${maxGen}`;
    shell.backendUrl = state.baseUrl;
    state.runStatus = payload.status || state.runStatus;

    const latest = payload.latest || {};
    const overview = DATA.overview;
    overview.live.generation = currentGen;
    overview.live.phase = latest.phase || payload.status || overview.live.phase;
    overview.live.checkpoint = latest.last_checkpoint || latest.checkpoint || overview.live.checkpoint;
    overview.live.message = latest.message || overview.live.message;
    overview.live.strategies = `${gens.length} / ${maxGen}`;
    overview.live.gate = String(gens.filter(g => g && g.gate_passed).length);

    const best = payload.best || {};
    const winner = payload.winner || null;
    const last = gens.length ? gens[gens.length - 1] : null;
    const active = winner || best || last || {};
    overview.activeStrategy.id = active.buy_name || active.buyName || active.name || `GEN-${active.gen ?? active.gen_no ?? currentGen}`;
    overview.activeStrategy.name = active.buy_name || active.buyName || active.strategy_gist || overview.activeStrategy.name;
    overview.activeStrategy.score = active.graded_score ?? active.score ?? overview.activeStrategy.score;
    overview.activeStrategy.gate = active.gate_passed ? '통과' : '대기';
    overview.activeStrategy.profit = last ? money(last.profit) : overview.activeStrategy.profit;
    overview.activeStrategy.mdd = last && last.mdd != null ? pctValue(-Math.abs(numberOr(last.mdd))) : overview.activeStrategy.mdd;
    overview.activeStrategy.trades = last && last.trade_count != null ? last.trade_count : overview.activeStrategy.trades;
    overview.winner = winner;
    overview.best = best;

    if (gens.length) {
      overview.generations = gens.slice().reverse().map(g => ({
        gen: g.gen_no,
        status: g.status || 'ok',
        graded_score: typeof g.graded_score === 'number' ? g.graded_score.toFixed(3) : (g.graded_score ?? '—'),
        gate_passed: g.gate_passed ? '통과' : '실패',
        gate_reason: g.gate_reason || '—',
        trade_count: g.trade_count ?? 0,
        daily_avg_trades: g.daily_avg_trades ?? '—',
        MDD: g.mdd == null ? '—' : pctValue(-Math.abs(numberOr(g.mdd))),
        profit: g.profit == null ? '—' : money(g.profit),
        strategy_gist: g.strategy_gist || '—',
        buy_name: g.buy_name || '',
        sell_name: g.sell_name || ''
      }));
      const byGen = gens.slice().sort((a, b) => numberOr(a.gen_no) - numberOr(b.gen_no));
      overview.fitness = byGen.map(g => numberOr(g.graded_score));
      overview.profitTrend = byGen.map(g => numberOr(g.profit));
      overview.quality = byGen.map(g => g.gate_passed ? 1 : Math.max(0, numberOr(g.graded_score)));
    }
  }

  function mapRuns(runsPayload) {
    state.latestRunsPayload = runsPayload;
    const rows = Array.isArray(runsPayload && runsPayload.runs) ? runsPayload.runs : [];
    if (!rows.length || !DATA.history) return;
    DATA.history.runs = rows.slice(0, 40).map(r => ({
      run_id: r.run_id || '—',
      campaign: r.label || r.status || '—',
      strategy: r.winner_buy_name || r.best_label || r.label || '—',
      tf: r.bt_timeframe || '—',
      provider: r.provider || '—',
      status: r.status || 'complete',
      gate: numberOr(r.gate_passed_count) > 0 ? '통과' : '대기',
      score: r.best_graded != null ? Number(r.best_graded).toFixed(3) : '—',
      pf: r.profit_factor || '—',
      mdd: r.mdd != null ? pctValue(-Math.abs(numberOr(r.mdd))) : '—',
      pnl: r.profit != null ? money(r.profit) : '—',
      label: r.label || '',
      created: r.started_at ? new Date(numberOr(r.started_at) * 1000).toLocaleString('ko-KR') : '—'
    }));
  }

  function applyBackendError(message) {
    DATA.shell.restHealth = 'FALLBACK';
    DATA.shell.websocket = message || '데모';
  }

  function refreshBackend() {
    if (!isLiveBackendMode) return Promise.resolve(false);
    DATA.shell.backendUrl = state.baseUrl;
    return fetchJson('/health', 3000)
      .then(h => {
        DATA.shell.restHealth = (h && h.status) || 'UP';
        return Promise.all([
          fetchJson('/status', 5000).then(status => { mapLoopState(status); }),
          fetchJson('/runs', 5000).then(mapRuns).catch(() => {})
        ]);
      })
      .then(() => { render(); return true; })
      .catch(e => {
        applyBackendError('백엔드 미연결 · 정적 프리뷰');
        if (stateSocket) {
          try { stateSocket.onclose = null; stateSocket.close(); } catch (_) {}
          stateSocket = null;
        }
        render();
        return false;
      });
  }

  function connectStateSocket() {
    if (!isLiveBackendMode) return;
    if (stateSocket) {
      try { stateSocket.onclose = null; stateSocket.close(); } catch (e) {}
      stateSocket = null;
    }
    const url = wsUrl('/ws');
    if (!url) return;
    try {
      stateSocket = new WebSocket(url);
    } catch (e) {
      DATA.shell.websocket = '연결 실패';
      return;
    }
    stateSocket.onopen = () => { DATA.shell.websocket = '연결됨'; render(); };
    stateSocket.onmessage = ev => {
      try { mapLoopState(JSON.parse(ev.data)); DATA.shell.websocket = '연결됨'; render(); } catch (e) {}
    };
    stateSocket.onerror = () => { DATA.shell.websocket = '오류'; render(); };
    stateSocket.onclose = () => {
      DATA.shell.websocket = '재연결 대기';
      render();
      clearTimeout(reconnectTimer);
      if (isLiveBackendMode) reconnectTimer = setTimeout(connectStateSocket, 3000);
    };
  }

  function reconnectBackend() {
    if (!isLiveBackendMode) return Promise.resolve(false);
    clearTimeout(reconnectTimer);
    return refreshBackend().then(ok => { if (ok) connectStateSocket(); });
  }

  function sendControl(message) {
    if (isReferenceMode) return;
    if (isDemoMode) {
      DATA.shell.websocket = '데모 모드 · 제어 비활성';
      return;
    }
    if (stateSocket && stateSocket.readyState === WebSocket.OPEN) {
      try { stateSocket.send(JSON.stringify(message)); return; } catch (e) {}
    }
    // Prototype fallback: keep the visual state responsive without inventing a hidden export path.
    if (message.action === 'start') DATA.shell.websocket = '제어 대기';
    if (message.action === 'stop') DATA.shell.websocket = '정지 요청 대기';
  }

  function renderOverview(vm = RemodelAdapters.overview()) {
    const o = vm.data;
    ConditionDetailAdapter.ensurePageEvidence();
    const conditionDetailSurface = renderConditionDetailSurface(conditionDetailContext());
    const analyticsHandoffSurface = renderAnalyticsHandoffSurface(analyticsHandoffContext());
    const liveRows = [['Phase', o.live.phase, 'amber'], ['Checkpoint', o.live.checkpoint], ['Message', o.live.message], ['Elapsed', o.live.elapsed], ['ETA', o.live.eta], ['생성 전략', o.live.strategies], ['게이트 통과', o.live.gate, 'green']];
    const activeRows = [['ID', o.activeStrategy.id], ['Name', o.activeStrategy.name], ['Grade', o.activeStrategy.grade, 'amber'], ['Score', o.activeStrategy.score, 'green'], ['Profit', o.activeStrategy.profit, 'green'], ['MDD', o.activeStrategy.mdd, 'red'], ['Trades', o.activeStrategy.trades]];
    const genColumns = [
      { key: 'gen', label: 'gen' },
      { key: 'status', label: 'status', render: r => badge(r.status, cls(r.status)) },
      { key: 'graded_score', label: 'graded_score' },
      { key: 'gate_passed', label: 'gate_passed', render: r => r.gate_passed === '통과' ? '<span class="green">✓ 통과</span>' : r.gate_passed === '실패' ? '<span class="red">✕ 실패</span>' : '—' },
      { key: 'gate_reason', label: 'gate_reason' },
      { key: 'trade_count', label: 'trade_count' },
      { key: 'daily_avg_trades', label: 'daily_avg_trades' },
      { key: 'MDD', label: 'MDD', render: r => `<span class="${String(r.MDD).includes('-') ? 'red' : ''}">${r.MDD}</span>` },
      { key: 'profit', label: 'profit', render: r => `<span class="green">${r.profit}</span>` },
      { key: 'strategy_gist', label: 'strategy_gist' },
      { key: 'actions', label: 'actions', render: () => '<span class="row-action" data-action="inspector">코드</span><span class="row-action">백테스트</span>' }
    ];
    const hofCols = ['rank','type','name','profit','mdd','sharpe','pf','score'].map(k => ({ key:k, label:k }));
    const conditionPrimary = `<section class="condition-primary-canvas panel" data-ux-primary-canvas="condition">
      <div class="condition-hero-grid">
        <div class="condition-run-card">
          <div class="step-kicker">Current generation</div>
          <h3>현재 세대 라이브 상태</h3>
          ${infoList(liveRows)}
          <div class="progress"><span style="width:${DATA.shell.generationProgress || 68.5}%"></span></div>
        </div>
        <div class="condition-candidate-card">
          <div class="step-kicker">BEST candidate</div>
          <h3>BEST · MeanRev_Adaptive_v9</h3>
          ${infoList(activeRows)}
          <div class="bt-action-row">${manualBtn('Strategy Inspector', 'small blue', 'data-action="inspector"', 'condition-inspector')}${manualBtn('Human Approval Export 검토', 'small violet', 'data-action="approval"', 'condition-export-gate')}</div>
        </div>
      </div>
      <div class="condition-chart-grid">
        ${panel('Fitness Score 추이 · primary', chart('Fitness Score 추이', o.fitness, { value: '0.812 ↑ 0.032', tall: true }))}
        ${panel('Profit / Equity Evidence', chart('Profit Equity Overlay', [{name:'Profit',values:o.profitTrend},{name:'Equity',values:o.equitySeries[0]?.values || o.profitTrend}], { tall: true, value:'+18.742%' }))}
        ${panel('백테스트 상세 · risk path', barLineChart('백테스트 상세', o.dailyBars, {height:190, value:'+22.13%' }))}
      </div>
      ${conditionDetailSurface}
      ${analyticsHandoffSurface}
      <div class="notice warn"><span>Export와 Audit는 분리됩니다 · Human Approval Gate 전까지 연구 산출물 대기</span>${badge('Append-Only Audit', 'amber')}</div>
    </section>`;
    return `
      ${taskFrame('condition', {
        title: '조건식 AI · 현재 세대와 BEST 후보를 먼저 판단하는 V3',
        summary: '작은 카드보다 현재 세대, 후보 품질, 큰 증거 차트, Human-gated export 상태를 먼저 보여줍니다.',
        purpose: '현재 세대 · 후보 품질 · provenance · gated export 검토',
        state: `${modeLabel} · run ${DATA.shell.runId}`,
        primaryAction: 'BEST 후보 검사와 승인 대기 확인',
        risk: 'no live order · human-gated export · append-only audit',
        actionKind: 'condition-primary-review',
        actionLabel: 'BEST 후보 검사'
      })}
      ${compactSafetyStrip('condition', ['Export is human-gated', 'Audit is append-only', 'research-only candidate review'])}
      ${conditionPrimary}
      ${provenanceCue(vm)}
      <div class="notice"><span>ⓘ Export Preview: Gen 136 스냅샷은 Human Gate 승인 전까지 내보내기 대기 상태입니다.</span><span>${manualBtn('승인 상태 보기','small blue', '', 'condition-export-preview')}</span></div>
      ${renderUxSweepPanel('condition', '5 charts + heatmap')}
      <div class="overview-layout" style="margin-top:10px">
        <aside class="side-stack">
          ${panel('1. 코어 헬스', infoList([['CPU','18.5%','green'],['MEM','42.3%','amber'],['DISK','31.2%'],['GPU','12.1%'],['WS','128 msg/s','green'],['REST','36 req/s','green']]))}
          ${panel('2. 히스토리 요약', infoList([['총 세대','137'],['총 전략','5,480'],['게이트 통과','812','green'],['우승','7','violet'],['아카이브','42']]))}
          ${panel('3. 성과 스냅샷', infoList([['총 순이익','+18.742%','green'],['승률(트레이드)','54.21%'],['샤프','1.36'],['칼마','1.12'],['MDD','-12.34%','red']]))}
          ${panel('4. 게이트 통과율', `<div class="card-value green">41.8%</div>${sparkline(DATA.history.passRate.slice(0,20))}`)}
          ${panel('명예 인스펙터', `<select style="width:100%; margin-bottom:8px"><option>S136-0321 (MeanRev_Adaptive_v9)</option></select>${codeBox(DATA.strategyCode.buy.split('\n').slice(0,6).join('\n'))}`)}
        </aside>
        <section class="overview-main">
          <div class="grid overview-top">
            ${panel('현재 세대 라이브 상태', infoList(liveRows), { action: badge('LIVE','green') })}
            ${panel('활성 전략 (현재 평가 중)', infoList(activeRows), { action: btn('인스펙터', 'small blue', 'data-action="inspector"') })}
            ${panel('프로세스 / 페이즈 타임라인', `<div class="phase-strip">${['탐색','평가','필터/게이트','교차/변이','검증/보강'].map((p,i)=>`<div class="phase-step ${i<2?'done':i===2?'active':''}"><div class="num">Phase ${i+1}</div><div class="label">${p}</div><div class="status">${i<2?'완료':i===2?'진행 중':'대기'}</div></div>`).join('')}</div>`) }
            ${panel('현재 페이즈 상세', infoList([['Phase 3','필터/게이트','amber'],['진행도','64%','green'],['소요','00:18:22'],['예상','00:10:28'],['완료','51 / 80']]))}
          </div>
          <div class="grid cols-5">
            ${panel('연구 기준 (Research Criteria)', `<ul>${o.researchCriteria.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>`) }
            ${panel('용어 사전 (Glossary)', infoList(o.glossary))}
            ${panel('Active Config', infoList([['데이터 소스','OHLCV (KRX + NYSE)'],['기간','2015-01-01 ~ 2024-12-31'],['수수료','0.015%'],['슬리피지','0.005%'],['초기 자본','100,000,000 KRW']]))}
            ${panel('Engine Summary', infoList([['AI 엔진','STOM-AI Engine v2.3.1'],['모델','gpt-4o-mini'],['전략 생성','Top-K 64'],['평가 워커','16 / 16'],['GPU','12.1%']]))}
            ${panel('Cost / Tokens', infoList([['총 비용','$214.317'],['이번 세대','$1.842'],['입력 토큰','1.28M'],['출력 토큰','0.49M'],['캐시 적중률','48.2%']]))}
          </div>
          <div class="grid cols-5">
            ${panel('Fitness Score 추이', chart('Fitness Score 추이', o.fitness, { value: '0.812 ↑ 0.032' }))}
            ${panel('Profit 추이', chart('Profit 추이', o.profitTrend, { value: '+18.742%' }))}
            ${panel('Equity Overlay (Top 5)', chart('Equity Overlay (Top 5)', o.equitySeries))}
            ${panel('백테스트 상세', barLineChart('백테스트 상세', o.dailyBars, { value: '+22.13%' }))}
            ${panel('GUI Parity / 품질', `<div class="grid cols-2">${heatmap(['시간대','요일'], ['09','10','11','12','13','14'], [[.21,.34,.62,.44,.31,.2],[.18,.42,.51,.33,.48,.27]], {hideValues:true})}</div>${chart('Quality Trend', o.quality, { small:true, value:'0.78' })}`)}
          </div>
          ${panel('세대 테이블 (Generation Table)', table(genColumns, o.generations))}
          <div class="grid cols-3">
            ${panel('Hall of Fame (상위 전략 비교)', table(hofCols, o.hof))}
            ${panel('Generation Analytics', `${chart('다중 지표 진화 추이', [{name:'Graded',values:o.fitness},{name:'Profit',values:o.profitTrend},{name:'Quality',values:o.quality}], {small:true})}<div class="grid cols-2" style="margin-top:8px">${metricCard('Top Gen','Gen 136','score 0.821','green')}${metricCard('Workbench','전달 가능','선택 후보 분석','blue')}</div>`)}
            ${panel('BEST / WINNER + Approval', renderWinnerApproval(), { className:'winner-card' })}
          </div>
          ${panel('전략 인스펙터 (Strategy Inspector) 미리보기', renderInspectorInline())}
        </section>
        <aside class="side-stack">
          ${panel('지원 분석 패널', `<div class="tile-grid">${o.analysisTiles.map(t=>`<div class="tile"><div class="muted">${escapeHtml(t.title)}</div><div class="tile-value ${t.title.includes('Autopsy')?'amber':t.title.includes('Holdout')?'green':'blue'}">${escapeHtml(t.value)}</div><div class="muted">${escapeHtml(t.desc)}</div></div>`).join('')}</div>`) }
          ${panel('Feedback / Autopsy', `<div class="notice danger">실패 원인: MDD 과다 · 거래 집중 구간 취약</div><ul><li>변동성 필터 추가</li><li>ATR 기반 손절 도입</li><li>포지션 스케일 조정</li></ul><div class="card-value red">0.42 / 1.00</div>`) }
          ${panel('Contract (Local Backend)', infoList([['REST','http://127.0.0.1:9200'],['WebSocket','ws://127.0.0.1:8765/ws'],['Data','Read-only'],['Export','Human Gate Required']]))}
        </aside>
      </div>
      ${renderSafetyFooter()}
    `;
  }

  function renderWinnerApproval() {
    return `<div class="grid cols-2">
      <div><div class="badge violet">WINNER</div><h3>S136-0321<br/>MeanRev_Adaptive_v9</h3>${infoList([['세대','136 | A Grade'],['Sharpe','1.28','green'],['수익률','+22.13%','green'],['MDD','-9.84%','red'],['PF','1.87'],['거래수','412']])}${btn('우승 후보 승인', 'violet', 'data-action="approval"')}</div>
      <div><div class="notice warn">승인 전 내보내기 불가</div><label class="muted">Buy 조건식 명<input id="approval-buy" value="MeanRev_Adaptive_v9_BUY" /></label><label class="muted">Sell 조건식 명<input id="approval-sell" value="MeanRev_Adaptive_v9_SELL" /></label><label style="display:flex;gap:8px;margin-top:8px"><input type="checkbox" id="approval-check" /> 명시적으로 승인합니다.</label>${btn('승인 및 내보내기', 'violet', 'data-action="approval"')}</div>
    </div>`;
  }
  function renderInspectorInline() {
    return `<div class="inspector-inline"><div>${miniTabs(['Buy Code','Sell Code','Previous Diff','Prompt Timeline','AI Context','Current Code'], 'Buy Code')}${codeBox(DATA.strategyCode.buy)}</div><div>${infoList([['전략 ID','S136-0321'],['문법 검사','정상','green'],['라인','1-28 / 28'],['복사 옵션','전체/코드/변수']])}<div style="margin-top:10px; display:grid; gap:8px">${btn('복사','small blue')}${btn('높이 확장','small')}${btn('전체 인스펙터 열기','small violet','data-action="inspector"')}</div></div></div>`;
  }
  function renderSafetyFooter() {
    const items = [ ['🚫','실거래/주문 기능 없음','No Live Order'], ['🚫','브로커 로그인 없음','No Broker Login'], ['🚫','계좌/자산 연동 없음','No Account Trading'], ['🛡','연구 전용','Research Only'], ['🔐','Human Approval Gate','승인 후 Export'], ['🧾','Append-Only Audit','불변 감사 로그'] ];
    return `<footer class="safety-footer">${items.map(i=>`<div class="safety-card"><span class="safety-icon ${i[0]==='🚫'?'red':'green'}">${i[0]}</span><div><b>${i[1]}</b><div class="muted">${i[2]}</div></div></div>`).join('')}</footer>`;
  }
  const UX_PAGE_STATES = {
    condition: ['empty generation table', 'loading live loop', 'stale fallback', 'malformed generation row', 'network error banner'],
    process: ['empty nodes/logs', 'loading process payload', 'stale /status', 'malformed process field', 'network error with fixture retained'],
    history: ['no run records', 'loading archive', 'stale archive snapshot', 'malformed run row', 'compare unavailable'],
    lab: ['no experiment output', 'loading research pack', 'stale factor snapshot', 'malformed heatmap cell', 'validation failure'],
    workbench: ['no selected candidate', 'loading evidence pack', 'stale candidate score', 'malformed metric', 'review queue blocked'],
    audit: ['no decision rows', 'loading ledger', 'stale hash chain', 'malformed ledger row', 'note validation error'],
    backtest: ['no jobs/results', 'loading safe GET probes', 'stale result fixture', 'malformed metric row', 'manual POST rejected'],
    replay: ['no bars/signals', 'loading safe REST probes', 'stale replay fixture', 'malformed candle', '/sim/ws manual retry error'],
  };
  const UX_PAGE_WORKFLOWS = {
    condition: 'inspect generation → compare charts → review winner → human-gated export',
    process: 'select run → inspect node → verify logs/queues/workers/contracts',
    history: 'filter archive → select run → compare result detail → request gated export',
    lab: 'read criteria → inspect factor heatmap → validate combinations → package context',
    workbench: 'select candidate → compare exposure/performance → hand off to review queue',
    audit: 'review evidence → choose decision → require note → append-only ledger record',
    backtest: 'select strategy/data → edit buy/sell conditions → validate → gated-run → analyze',
    replay: 'select historical replay → inspect OHLCV/crosshair → user-gated /sim/ws controls',
  };
  function renderUxSweepPanel(pageId, chartCount = 'interactive') {
    const states = UX_PAGE_STATES[pageId] || [];
    const namedStates = ['Empty', 'Loading', 'Stale', 'Malformed', 'Error'].map((label, index) => `${label}: ${states[index] || 'not applicable'}`);
    const workflow = UX_PAGE_WORKFLOWS[pageId] || 'documented workflow';
    const rows = [
      ['Layout', 'responsive grid · no horizontal overflow target'],
      ['Charts', `${chartCount} · tooltip/crosshair/focus or accessible equivalent`],
      ['States', namedStates.join(' · ')],
      ['Workflow', workflow],
      ['Provenance', `${modeLabel} · ${isLiveBackendMode ? 'live safe-read, manual actions gated' : 'reference/demo fixture, inert actions disabled'}`],
      ['Accessibility', 'keyboard focus · aria-live active datum · non-hover values visible'],
    ];
    return `<section class="panel ux-sweep-panel" data-ux-page="${escapeHtml(pageId)}" data-testid="ux-sweep-${escapeHtml(pageId)}">
      <div class="panel-header"><span>G006 UX/UI sweep · ${escapeHtml(pageId)}</span>${badge('layout/interaction/state proof','violet')}</div>
      <div class="panel-body">
        <div class="ux-sweep-grid">${rows.map(row => `<div class="ux-sweep-item"><b>${escapeHtml(row[0])}</b><span>${escapeHtml(row[1])}</span></div>`).join('')}</div>
      </div>
    </section>`;
  }

  function normalizeProcessPayload(processData = {}, vm = {}) {
    const required = processData.requiredFields || ['kpis', 'nodes', 'logs', 'runs', 'queue', 'workers', 'contracts'];
    const missing = required.filter(key => !Array.isArray(processData[key]));
    const malformed = [];
    const nodes = Array.isArray(processData.nodes) ? processData.nodes : [];
    const logs = Array.isArray(processData.logs) ? processData.logs : [];
    const runs = Array.isArray(processData.runs) ? processData.runs : [];
    const queue = Array.isArray(processData.queue) ? processData.queue : [];
    const workers = Array.isArray(processData.workers) ? processData.workers : [];
    const contracts = Array.isArray(processData.contracts) ? processData.contracts : [];
    nodes.forEach((node, index) => {
      ['id', 'title', 'status'].forEach(key => {
        if (node == null || node[key] === undefined || node[key] === '') malformed.push(`nodes[${index}].${key}`);
      });
    });
    const selectedRun = state.processSelectedRunId ? runs.find(run => String(run.id) === String(state.processSelectedRunId)) : null;
    const currentRun = selectedRun || runs.find(run => String(run.status || '').toUpperCase() === 'RUNNING') || runs[0] || {
      id: 'process-run-unavailable',
      status: missing.includes('runs') ? 'EMPTY' : 'UNKNOWN',
      phase: nodes.find(n => n.status === '진행 중')?.title || 'unknown',
      progress: 0,
      updatedAt: 'n/a',
      source: vm.source || 'fallback',
    };
    const source = vm.isLive ? 'backend-derived process payload' : vm.isFixture ? 'reference fixture/static process payload' : 'backend loading/fallback with fixture baseline';
    const stateLabel = missing.length ? 'MALFORMED' : !runs.length || !nodes.length ? 'EMPTY' : vm.isLive ? 'LIVE' : 'REFERENCE/DEMO';
    return { required, missing, malformed, nodes, logs, runs, queue, workers, contracts, currentRun, source, stateLabel };
  }
  function renderProcessStateStrip(model) {
    const stale = model.stateLabel === 'REFERENCE/DEMO' ? 'reference/demo honest fixture · not live' : model.stateLabel === 'LIVE' ? 'live payload' : 'requires payload repair';
    return `<div class="process-state-strip" data-process-step="state" data-process-state="${escapeHtml(model.stateLabel)}"><span>${badge(`state ${model.stateLabel}`, model.stateLabel === 'LIVE' ? 'green' : model.stateLabel === 'MALFORMED' ? 'red' : 'amber')}</span><span>source=${escapeHtml(model.source)}</span><span>run_id=${escapeHtml(model.currentRun.id)}</span><span>phase=${escapeHtml(model.currentRun.phase || 'unknown')}</span><span>freshness=${escapeHtml(model.currentRun.updatedAt || 'n/a')}</span><span>stale=${escapeHtml(stale)}</span><span>missing=${model.missing.length}</span><span>malformed=${model.malformed.length}</span></div>`;
  }
  function renderProcessRequiredFields(model) {
    return `<div class="process-required-grid">${model.required.map(key => {
      const ok = !model.missing.includes(key);
      return `<div class="process-required ${ok ? 'ok' : 'bad'}" data-process-required="${escapeHtml(key)}"><b>${escapeHtml(key)}</b><span>${ok ? 'payload ok' : 'missing'}</span></div>`;
    }).join('')}</div>`;
  }
  function renderProcess(vm = RemodelAdapters.process()) {
    const p = vm.data || {};
    const model = normalizeProcessPayload(p, vm);
    const runPhase = String(model.currentRun.phase || '').toLowerCase();
    const currentNode = model.nodes.find(n => String(n.title || '').toLowerCase() === runPhase) || model.nodes.find(n => n.id === p.selectedNodeId) || model.nodes.find(n => n.status === '진행 중') || model.nodes[0] || {};
    const runOptions = model.runs.map(run => `<option value="${escapeHtml(run.id)}" ${run.id === model.currentRun.id ? 'selected' : ''}>${escapeHtml(run.id)} · ${escapeHtml(run.status)} · ${escapeHtml(run.phase)}</option>`).join('');
    const side = panel('실행 선택 (Run Selector)', `<select class="process-run-selector" data-process-step="select" data-process-run-selector style="width:100%">${runOptions || '<option>process-run-unavailable</option>'}</select><div class="process-run-card" data-source-key="runs"><b>${escapeHtml(model.currentRun.status)}</b><span>${Math.round(Number(model.currentRun.progress || 0) * 100)}%</span><div class="progress"><span style="width:${Math.round(Number(model.currentRun.progress || 0) * 100)}%"></span></div><small>${escapeHtml(model.currentRun.source || model.source)}</small></div>`) + panel('프로세스 메뉴', ['프로세스 맵','실행 목록','노드 카탈로그','경계 계약','큐/워커','상태/오류'].map((x,i)=>`<div class="info-row"><span>${i===0?'▣':'□'} ${x}</span></div>`).join('')) + panel('안전 & 거버넌스', `<div class="info-list"><div>⚠ 연구 전용</div><div>🚫 실거래 연동 없음</div><div>🛡 Human Approval Gate</div><div>🧾 Append-Only Audit</div><div>🔌 로컬 REST + WebSocket · read-only monitor</div></div>`);
    const nodeCount = Math.max(1, model.nodes.length);
    const map = `<div class="process-map" data-process-step="map" data-source-key="nodes">${model.nodes.map((n,i)=>`<button type="button" class="flow-node ${n.status==='진행 중'?'active':n.status==='완료'?'done':'wait'}" data-action="process-node" data-process-node="${escapeHtml(n.id)}" data-node-status="${escapeHtml(n.status)}" style="left:${55+i*Math.max(150, Math.floor(820 / nodeCount))}px;top:${i===3?88:112}px"><div class="badge ${cls(n.status)}">${escapeHtml(n.id)} ${escapeHtml(n.status)}</div><h3>${escapeHtml(n.title)}</h3><div class="muted">${escapeHtml(n.desc)}</div><div class="info-row"><span>items</span><span>${escapeHtml(n.items)}</span></div><div class="info-row"><span>time</span><span>${escapeHtml(n.time)}</span></div></button>`).join('')}${model.nodes.slice(0, -1).map((_,i)=>`<div class="flow-line ${model.nodes[i+1]?.status==='진행 중'?'active':''}" style="left:${230+i*Math.max(150, Math.floor(820 / nodeCount))}px;width:90px"></div>`).join('')}<div class="loop-line"></div></div>`;
    const nodeCards = model.nodes.map(n=>`<div class="tile" data-process-node-card="${escapeHtml(n.id)}"><b>${escapeHtml(n.id)}. ${escapeHtml(n.title)}</b><p class="muted">${escapeHtml(n.desc)} · ${escapeHtml(n.status)}</p><div class="progress"><span style="width:${n.status === '완료' ? 100 : n.status === '진행 중' ? 64 : 8}%"></span></div></div>`).join('') || `<div class="chart-empty" role="status">노드 데이터 없음 · required nodes missing</div>`;
    const logPanel = model.logs.length ? `<div class="code-box" data-process-step="logs" data-source-key="logs">${model.logs.map(escapeHtml).join('\n')}</div>` : `<div class="chart-empty" data-process-step="logs" role="status">로그 없음 · logs empty</div>`;
    const queueRows = model.queue.map(row => ({ ...row, status: Number(row.error || 0) ? 'ERROR' : Number(row.running || 0) ? 'RUNNING' : 'IDLE' }));
    const workerRows = model.workers.map(row => ({ ...row, statusBadge: badge(row.status, cls(row.status)) }));
    const contractRows = model.contracts.map(row => ({ ...row, statusBadge: badge(row.status, cls(row.status)) }));
    return `${taskFrame('process', { title: '프로세스 · payload-driven cockpit을 유지한 V3', summary: '실행 선택 → 현재 상태 → 노드 drilldown → 로그/큐/워커를 먼저 보여주고 계약 세부는 evidence drawer로 접습니다.', purpose: 'Run selector · Process map · Node drilldown · Queue/Workers · Contracts', state: `${model.stateLabel} · ${model.currentRun.id}`, primaryAction: '현재 노드와 큐 상태 확인', risk: 'read-only monitor · no broker/order mutation', actionKind: 'process-node-review', actionLabel: '현재 노드 보기' })}${compactSafetyStrip('process', ['Process monitor is read-only', 'Route contracts are evidence-only', 'No live order/broker action'])}<div class="process-layout process-task-layout"><aside class="side-stack">${side}</aside><section class="grid native-process-page" data-ux-primary-canvas="process">
      ${provenanceCue(vm)}
      ${renderUxSweepPanel('process', 'process map + 0/optional charts')}
      ${renderProcessStateStrip(model)}
      ${renderProcessRequiredFields(model)}
      <div class="grid cols-8" data-source-key="kpis">${(p.kpis || []).map(k=>metricCard(k[0],k[1])).join('') || metricCard('payload','empty','kpis missing','red')}</div>
      <div class="process-trend-grid" data-process-step="trend">
        ${panel('Generation / Backtest / Scoring 처리량 추세', chart('Generation Backtest Scoring 처리량', [{name:'Generation',values:DATA.history.runsOverTime},{name:'Backtest',values:DATA.backtest.equity.map(v=>Math.max(0, v * 0.45))},{name:'Scoring',values:DATA.workbench.ic.map(v=>Math.abs(v) * 1000)}], {tall:true, value:`${model.currentRun.phase || 'process'} · ${model.stateLabel}`}))}
        ${panel('현재 단계 KPI 해석', infoList([['Generation', '후보 생성 상태'], ['Backtest', '검증 큐 처리량'], ['Scoring', 'fitness 계산 흐름'], ['drilldown', currentNode.title || 'none']]))}
      </div>
      ${panel('프로세스 맵 (payload-driven)', map, { action: btn('노드 JSON 보기','small blue','data-action="process-node"') })}
      <div class="grid cols-3">
        ${panel('현재 상태 / Node Drilldown', `<div class="process-drilldown" data-process-drilldown data-selected-node="${escapeHtml(currentNode.id || 'none')}">${infoList([['Node', currentNode.title || 'none'],['Status', currentNode.status || 'EMPTY', cls(currentNode.status)],['Items', currentNode.items ?? 'n/a'],['Time', currentNode.time || 'n/a'],['Required fields', `${model.required.length - model.missing.length}/${model.required.length}`]])}</div>`)}
        ${panel('단계 설명', nodeCards)}
        ${panel('라이브 로그 / Error State', logPanel)}
      </div>
      <div class="grid cols-3">
        ${panel('큐 상태 (Queue)', `<div data-process-step="queue" data-source-key="queue">${table([{key:'name',label:'큐'},{key:'queued',label:'대기'},{key:'running',label:'실행'},{key:'done',label:'완료'},{key:'error',label:'오류'},{key:'status',label:'상태',render:r=>badge(r.status,cls(r.status))}], queueRows)}</div>`, { sub: 'payload: queue' })}
        ${panel('워커 상태 (Workers)', `<div data-process-step="workers" data-source-key="workers">${table([{key:'id',label:'워커'},{key:'node',label:'노드'},{key:'statusBadge',label:'상태'},{key:'heartbeat',label:'Heartbeat'},{key:'item',label:'Item'}], workerRows)}</div>`, { sub: 'payload: workers' })}
        ${panel('경계 계약 (Route Boundary Contract)', `<div data-process-step="contracts" data-source-key="contracts">${table([{key:'route',label:'경로'},{key:'required',label:'필수 필드'},{key:'statusBadge',label:'상태'},{key:'sla',label:'SLA'}], contractRows)}</div>`, { sub: 'payload: contracts' })}
      </div>
      ${evidenceDrawer('process', 'Process evidence / route contract drawer 열기', `<div class="grid cols-3">${panel('상태 매트릭스', infoList([['loading','payload pending/fallback'],['empty', model.nodes.length && model.logs.length ? 'not active' : 'visible'],['stale', model.stateLabel === 'REFERENCE/DEMO' ? 'fixture honestly labeled' : 'live read'],['error', model.malformed.length ? model.malformed.join(', ') : '0'],['malformed', String(model.malformed.length)]]))}${panel('실행 메타데이터', infoList([['run_id', model.currentRun.id],['status', model.currentRun.status, cls(model.currentRun.status)],['phase', model.currentRun.phase || 'unknown'],['source', model.currentRun.source || model.source],['backend', vm.backendUrl]]))}${panel('설정 미리보기', `<div class="form-grid"><label>동시 실행 워커<input value="${model.workers.length || 0}" readonly /></label><label>큐 총 대기<input value="${model.queue.reduce((a,b)=>a+Number(b.queued||0),0)}" readonly /></label><label>캐시 TTL<select disabled><option>read-only</option></select></label><label>반복 루프<select disabled><option>Repeat</option></select></label></div>`)}</div>`)}
    </section></div>${renderSafetyFooter()}`;
  }

  function renderHistory(vm = RemodelAdapters.history()) {
    const h = vm.data;
    const selectedRun = h.runs[0] || {};
    const compareRun = h.runs[1] || selectedRun;
    const columns = [
      {key:'run_id',label:'런 ID'},
      {key:'campaign',label:'캠페인'},
      {key:'strategy',label:'전략명'},
      {key:'status',label:'상태',render:r=>badge(r.status,cls(r.status))},
      {key:'gate',label:'게이트',render:r=>badge(r.gate,cls(r.gate))},
      {key:'score',label:'스코어'},
      {key:'pf',label:'PF'},
      {key:'mdd',label:'MDD'},
      {key:'pnl',label:'1D PnL%'},
      {key:'created',label:'생성일'}
    ];
    const historyPrimary = `<section class="history-primary-canvas panel" data-ux-primary-canvas="history">
      <div class="history-flow-grid">
        <section class="history-step-card" data-history-step="find">
          <span class="step-kicker">1. Find</span>
          <h3>Run/gen archive 검색</h3>
          <input value="${escapeHtml(selectedRun.campaign || 'CMPN_TrendBreak_001')}" aria-label="history search" readonly />
          <div class="bt-action-row">${manualBtn('필터 저장', 'small blue', 'data-history-step="find"', 'history-filter-save')}${manualBtn('Compare 후보 고정', 'small violet', 'data-history-step="compare"', 'history-pin-compare')}</div>
        </section>
        <section class="history-step-card" data-history-step="inspect">
          <span class="step-kicker">2. Inspect</span>
          <h3>ResultDetail · ${escapeHtml(selectedRun.run_id || 'RUN_20250520_094015')}</h3>
          ${infoList([['Strategy', selectedRun.strategy || 'STOM_TREND_BRK_V3'],['Gate', selectedRun.gate || 'PASS', cls(selectedRun.gate)],['Score', selectedRun.score || '0.82'],['PF', selectedRun.pf || '1.87'],['MDD', selectedRun.mdd || '-8.4%','red'],['PnL', selectedRun.pnl || '+1.24%','green']])}
        </section>
        <section class="history-step-card" data-history-step="lineage">
          <span class="step-kicker">3. Lineage</span>
          <h3>Lineage / Research Records</h3>
          <div class="tile"><b>${escapeHtml(selectedRun.campaign || 'CMPN_TrendBreak_001')}</b><div class="muted">docs/update_log · registry · Research Records 연결</div></div>
          <div class="tile"><b>GEN_20250520_093812</b><div class="muted">부모 RUN ${escapeHtml(compareRun.run_id || 'RUN_20250519_151012')} · mutation 4</div></div>
        </section>
      </div>
      <div class="history-compare-canvas" data-history-step="compare">
        <div class="history-compare-header">
          <div><span class="badge violet">Primary Compare</span><h3>Compare · Equity / PnL / Lineage를 한 화면에서 비교</h3></div>
          <div class="history-compare-pair"><b>${escapeHtml(selectedRun.run_id || 'RUN_A')}</b><span>vs</span><b>${escapeHtml(compareRun.run_id || 'RUN_B')}</b></div>
        </div>
        <div class="history-chart-grid">
          ${panel('Equity vs Benchmark · ResultDetail', chart('Equity vs Benchmark', [{name:'Equity',values:DATA.backtest.equity},{name:'Benchmark',values:DATA.backtest.equity.map(v=>v*.6)}], {tall:true, value:'+18.72%'}))}
          ${panel('PnL / Pass Rate', chart('PnL Pass Rate', [{name:'PnL',values:h.runsOverTime},{name:'PassRate',values:h.passRate}], {tall:true, value:'34.1%'}))}
          ${panel('Research Records', h.researchRecords.slice(0,4).map(r=>`<div class="tile"><b>${escapeHtml(r.time)} · ${escapeHtml(r.type)}</b><div class="muted">${escapeHtml(r.note)}</div>${badge(r.tag,'blue')}</div>`).join(''))}
        </div>
      </div>
    </section>`;
    return `
      ${taskFrame('history', {
        title: '히스토리 · 찾기/상세/비교/Lineage가 한 흐름인 V3',
        summary: '기록 테이블과 작은 비교 카드 과밀을 줄이고, 선택 RUN의 ResultDetail과 Compare canvas를 먼저 보여줍니다.',
        purpose: 'Run archive · ResultDetail · Compare · Research Records · Lineage',
        state: `${modeLabel} · ${h.runs.length} archived runs`,
        primaryAction: 'RUN 선택 후 Compare 확인',
        risk: 'read-only history · export remains human-gated',
        actionKind: 'history-compare-review',
        actionLabel: 'Compare 보기'
      })}
      ${compactSafetyStrip('history', ['History is read-only', 'Export request remains human-gated', 'Lineage/provenance visible'])}
      <div class="history-task-layout">
        <aside class="side-stack history-side-compact">${panel('히스토리 요약', `<div class="grid cols-2">${h.summary.map(s=>metricCard(s[0],s[1],s[2])).join('')}</div>`)}${panel('라인리지 검색', ['CMPN_TrendBreak_001','CMPN_MR_Momentum_004','CMPN_QualityCore_002'].map((x,i)=>`<div class="tile"><b>${x}</b><div class="muted">RUN ${deterministicLineageValue(i, 60, 17, 80)} · GEN ${deterministicLineageValue(i, 260, 43, 300)}</div></div>`).join(''))}</aside>
        <section class="grid history-main-stack">
          ${provenanceCue(vm)}
          ${renderUxSweepPanel('history', 'primary compare charts')}
          ${historyPrimary}
          ${panel('실행/생성 히스토리 · Run & Generation History · compact archive', table(columns, h.runs), {action: `${manualBtn('비교 하기','small violet','data-history-step="compare"', 'history-compare-action')} ${manualBtn('내보내기 요청','small','data-history-step="export"', 'history-export-request')}`})}
          ${evidenceDrawer('history', 'History evidence / lineage metadata 열기', `<div class="grid cols-3">${panel('상태 매트릭스', infoList([['Empty','no run records'],['Loading','loading archive'],['Stale','stale archive snapshot'],['Malformed','malformed run row'],['Error','compare unavailable']]))}${panel('Lineage contract', infoList([['Campaign', selectedRun.campaign || 'CMPN_TrendBreak_001'],['Docs','docs/update_log'],['Registry','CARRY_FORWARD'],['Research Records','visible']]))}${panel('Safety', infoList([['Mode', modeLabel],['Export','Human Gate Required'],['Audit','Append-Only']]))}</div>`)}
        </section>
      </div>${renderSafetyFooter()}`;
  }

  function renderLab(vm = RemodelAdapters.lab()) {
    const l = vm.data;
    const selectedRow = l.heatRows[1] || l.heatRows[0] || 'Ret 20D';
    const selectedCol = l.heatCols[2] || l.heatCols[0] || 'mom_20';
    const selectedValue = ((l.edgeValues[1] || l.edgeValues[0] || [])[2] ?? (l.edgeValues[0] || [])[0] ?? 0);
    const selectedNarrative = `${selectedRow} × ${selectedCol} Edge Ratio ${selectedValue} · 상위 조합 검토 대상 · Holdout ${l.holdout.return}`;
    const topFactors = l.importance.slice(0, 6);
    const side = panel('연구 흐름 요약', infoList([
      ['1 Criteria', 'Edge Ratio · IC · Holdout'],
      ['2 Primary heatmap', '값/축/범례 먼저 확인'],
      ['3 Importance', topFactors[0]?.[0] || 'mom_20'],
      ['4 Validation', `Holdout ${l.holdout.return}`],
      ['5 Context', `${l.combos.length} combos packaged`],
    ])) + panel('정체/큐 compact', `<div class="notice warn">LAB-2025-05-21-008 정체 12m · stale factor snapshot은 라벨링</div>${infoList([['대기','5'],['Freeze strong','12 (18.8%)'],['Freeze weak','27 (42.2%)']])}`);
    const labPrimary = `<section class="lab-primary-canvas panel" data-ux-primary-canvas="lab">
      <div class="lab-primary-header">
        <div>
          <span class="badge blue">Primary factor canvas</span>
          <h3>연구실 · Edge Ratio 히트맵을 크게 보고 선택 셀 의미를 바로 해석</h3>
          <p class="muted">V2보다 큰 히트맵, 셀 값, 축, 범례, 선택 셀 narrative, Holdout 검증을 한 흐름에 배치합니다.</p>
        </div>
        <div class="lab-selected-cell" data-lab-selected-cell>
          <span class="step-kicker">selected cell</span>
          <b>${escapeHtml(selectedRow)} × ${escapeHtml(selectedCol)}</b>
          <span class="green mono">${escapeHtml(selectedValue)}</span>
        </div>
      </div>
      <div class="lab-analysis-grid">
        <section class="lab-step-card lab-heatmap-card" data-lab-step="heatmap">
          <div class="panel-header"><span>1. 탐색 히트맵 · Edge Ratio</span>${badge('values visible', 'green')}</div>
          <div class="panel-body">
            ${heatmap(l.heatRows,l.heatCols,l.edgeValues,{mode:'edge'})}
            <div class="heatmap-narrative" data-heatmap-selected-narrative>${escapeHtml(selectedNarrative)}</div>
            <div class="heatmap-scale-legend" data-heatmap-legend><span>low edge</span><span></span><span>high edge</span></div>
          </div>
        </section>
        <section class="lab-step-card" data-lab-step="importance">
          <div class="panel-header"><span>2. 변수 중요도</span>${badge('Permutation', 'blue')}</div>
          <div class="panel-body">${topFactors.map((r,i)=>`<div class="bar-row lab-bar-row"><span>${i+1}. ${escapeHtml(r[0])}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.min(r[1]/2.31*100,100)}%"></div></div><span class="mono">${escapeHtml(r[1])}</span></div>`).join('')}</div>
        </section>
        <section class="lab-step-card" data-lab-step="holdout">
          <div class="panel-header"><span>3. Holdout 검증</span>${badge('검증', 'green')}</div>
          <div class="panel-body">${infoList([['Cum.Return',l.holdout.return,'green'],['Ann.Return',l.holdout.ann,'green'],['Sharpe',l.holdout.sharpe],['Max DD',l.holdout.mdd,'red'],['Hit Ratio',l.holdout.hit],['Trades',l.holdout.trades]])}${chart('누적 수익률', DATA.backtest.equity, {tall:true, value:l.holdout.return})}</div>
        </section>
      </div>
    </section>`;
    return `
      ${taskFrame('lab', {
        title: '연구실 · 히트맵과 검증을 먼저 읽는 V3',
        summary: '값 없는 색상 블록과 작은 카드 과밀을 줄이고, 선택 셀 의미와 Holdout 검증을 첫 작업 영역에 배치합니다.',
        purpose: 'Edge Ratio 히트맵 · 변수 중요도 · 상관관계 · Holdout 검증',
        state: `${modeLabel} · ${l.importance.length} variables · ${l.combos.length} combos`,
        primaryAction: '선택 셀 해석과 검증 요약 확인',
        risk: 'research-only · no export · no live order',
        actionKind: 'lab-cell-review',
        actionLabel: '선택 셀 확인'
      })}
      ${compactSafetyStrip('lab', ['Lab output is research-only', 'Context pack export is inert/manual', 'No live trading decision'])}
      <div class="lab-task-layout">
        <aside class="side-stack lab-side-compact">${side}</aside>
        <section class="grid lab-main-stack">
          ${provenanceCue(vm)}
          ${renderUxSweepPanel('lab', 'large heatmap + importance/holdout charts')}
          ${labPrimary}
          <div class="lab-secondary-grid">
            ${panel('상관관계 히트맵 (Pearson)', `${heatmap(l.corrLabels,l.corrLabels,l.corr,{mode:'corr'})}<div class="heatmap-narrative">상관관계도 값 표시 · hover title · 축 라벨 유지</div>`)}
            ${panel('변수 조합 후보', l.combos.map((c,i)=>`<div class="tile"><b>${i+1}. ${escapeHtml(c)}</b><div class="muted">Edge Ratio ${(0.412-i*0.026).toFixed(3)} · 승률 ${(61.7-i*.9).toFixed(1)}%</div>${badge('검증 통과','green')}</div>`).join(''))}
            ${panel('AI 컨텍스트 팩', `<ul><li>데이터 스냅샷 1,842일 / 350종목</li><li>상위 80 변수 메타와 선택 셀 narrative</li><li>히트맵/상관관계 이미지</li><li>상위 조합 20개 · Holdout 검증</li></ul>${manualBtn('컨텍스트 팩 내보내기 (ZIP)', 'small blue', 'data-lab-step="context"', 'lab-context-pack')}`)}
          </div>
          ${evidenceDrawer('lab', 'Lab evidence / UX proof / heatmap metadata 열기', `<div class="grid cols-3">${panel('상태 매트릭스', infoList([['Empty','no experiment output'],['Loading','loading research pack'],['Stale','stale factor snapshot'],['Malformed','malformed heatmap cell'],['Error','validation failure']]))}${panel('프로세스 오버레이 / Glossary', infoList([['Edge Ratio','정보 우위 지표'],['IC','스코어/수익률 상관'],['Holdout','분리 기간 검증']]))}${panel('시각적 품질', `${chart('Ret 20D vs Score 밀도', DATA.workbench.ic, {small:true, value:'R² 0.071'})}<div class="notice warn">투자 자문 아님 · 실제 투자 사용 불가</div>`)}</div>`)}
        </section>
      </div>${renderSafetyFooter()}`;
  }

  function renderWorkbench(vm = RemodelAdapters.workbench()) {
    const w = vm.data;
    const selected = w.candidates.find(c => c.selected) || w.candidates[0] || {};
    const runnerUp = w.candidates.find(c => c.id !== selected.id) || w.candidates[1] || selected;
    const exposureRows = [
      {item:'상관계수',kospi:0.58,mkt:0.41,size:-0.23,value:0.32,mom:0.37},
      {item:'베타(회귀)',kospi:0.62,mkt:0.41,size:-0.21,value:0.28,mom:0.36},
      {item:'노출 Z-score',kospi:0.41,mkt:0.32,size:-0.18,value:0.29,mom:0.33}
    ];
    const workbenchPrimary = `<section class="workbench-primary-canvas panel" data-ux-primary-canvas="workbench">
      <div class="workbench-funnel-grid">
        <section class="workbench-step-card" data-workbench-step="select">
          <span class="step-kicker">1. Select</span>
          <h3>Hall of Fame 워크벤치 후보 선택</h3>
          <div class="candidate-strip workbench-candidate-strip">${w.candidates.map((c,i)=>`<button type="button" class="candidate-card ${c.selected?'selected':''}" data-workbench-candidate="${escapeHtml(c.id)}"><div class="badge ${c.selected?'violet':'blue'}">#${i+1} ${escapeHtml(c.id)}</div><div class="card-value ${c.selected?'violet':'green'}">${escapeHtml(c.score)}</div>${infoList([['IC',c.ic],['Ann.Ret',c.ann,'green'],['Sharpe',c.sharpe]])}</button>`).join('')}</div>
        </section>
        <section class="workbench-step-card selected-candidate-card" data-workbench-step="compare">
          <span class="step-kicker">2. Compare</span>
          <h3>선택 후보 · ${escapeHtml(selected.id || 'G-0018')}</h3>
          ${infoList([['Score', selected.score || '0.91','green'],['IC', selected.ic || '0.18'],['Ann.Ret', selected.ann || '29.6%','green'],['Sharpe', selected.sharpe || '1.74'],['Runner-up', runnerUp.id || 'G-0009']])}
          <div class="bt-action-row">${manualBtn('History Compare', 'small violet', 'data-workbench-step="compare"', 'workbench-history-compare')}${manualBtn('Backtest Result Review', 'small blue', 'data-workbench-step="evidence"', 'workbench-backtest-review')}</div>
        </section>
        <section class="workbench-step-card" data-workbench-step="handoff">
          <span class="step-kicker">3. Review handoff</span>
          <h3>리뷰 큐 handoff</h3>
          <div class="tile">1 후보 확정 ✓</div>
          <div class="tile">2 리뷰 큐 등록 대기 · manual gate</div>
          <div class="notice warn">본 워크벤치는 승인/내보내기 권한이 없습니다.</div>
        </section>
      </div>
      <div class="workbench-compare-grid">
        ${panel('후보 상세 분석 · 누적 수익률 primary', chart('누적 수익률', w.equity, {tall:true, value:'+29.6%'}))}
        ${panel('IC 시계열 · evidence', chart('IC 시계열', w.ic, {tall:true, value:'IC 0.18'}))}
        ${panel('성과 히트맵 (연도 × 월)', `${heatmap(w.monthlyHeatRows,w.monthlyHeatCols,w.monthlyHeat,{mode:'return'})}<div class="heatmap-narrative">월별 성과 값 표시 · 선택 후보의 계절성/레짐 점검</div>`)}
      </div>
    </section>`;
    return `
      ${taskFrame('workbench', {
        title: '분석 워크벤치 · 후보 선택과 리뷰 handoff가 먼저 보이는 V3',
        summary: '카드 과밀을 줄이고 Hall of Fame 후보 선택 → 비교 → 리뷰 큐 handoff를 한 primary canvas로 묶습니다.',
        purpose: 'Hall of Fame 후보 · evidence compare · History Compare · Backtest Result Review · 리뷰 큐',
        state: `${modeLabel} · selected ${selected.id || 'G-0018'}`,
        primaryAction: '후보 비교 후 리뷰 큐 전달',
        risk: 'analysis-only · no approval/export authority',
        actionKind: 'workbench-review-handoff',
        actionLabel: '리뷰 handoff 확인'
      })}
      ${compactSafetyStrip('workbench', ['Workbench cannot export', 'Review queue is manual-gated', 'Research-only candidate analysis'])}
      <div class="workbench-task-layout">
        <aside class="side-stack workbench-side-compact">${panel('분석 컨텍스트', infoList([['Active Run','127'],['Generation','G-0018'],['History Compare','ready'],['Backtest Result Review','ready'],['리뷰 대기','3']]))}${panel('증거 노트', w.evidence.map(x=>`<div class="tile">${escapeHtml(x)}</div>`).join(''))}</aside>
        <section class="grid workbench-main-stack">
          ${provenanceCue(vm)}
          ${renderUxSweepPanel('workbench', 'primary compare charts + heatmap')}
          ${workbenchPrimary}
          <div class="workbench-secondary-grid">
            ${panel('핵심 성과 지표', `<div class="grid cols-6">${[['Ann.Ret','29.6%'],['Vol','17.0%'],['Sharpe','1.74'],['Sortino','2.63'],['Max DD','-15.6%'],['Win Rate','57.8%']].map(x=>metricCard(x[0],x[1], '', x[1].startsWith('-')?'red':'green')).join('')}</div>`)}
            ${panel('상관/노출 요약', table([{key:'item',label:'항목'},{key:'kospi',label:'KOSPI'},{key:'mkt',label:'MKT-BM'},{key:'size',label:'SIZE'},{key:'value',label:'VALUE'},{key:'mom',label:'MOMENTUM'}], exposureRows))}
          </div>
          ${evidenceDrawer('workbench', 'Workbench evidence / candidate handoff metadata 열기', `<div class="grid cols-3">${panel('상태 매트릭스', infoList([['Empty','no selected candidate'],['Loading','loading evidence pack'],['Stale','stale candidate score'],['Malformed','malformed metric'],['Error','review queue blocked']]))}${panel('Handoff contract', infoList([['Candidate', selected.id || 'G-0018'],['Review Queue','manual-gated'],['Approval','not allowed here'],['Export','not allowed here']]))}${panel('리뷰 큐', ['G-0018','G-0009','G-0012'].map(x=>`<div class="tile"><b>${x}</b><div class="muted">리뷰 대기 · 우선순위 높음</div></div>`).join(''))}</div>`)}
        </section>
      </div>${renderSafetyFooter()}`;
  }

  function renderAudit(vm = RemodelAdapters.audit()) {
    const a = vm.data;
    DecisionAuditAdapter.ensurePageEvidence();
    const decisionAuditSurface = renderDecisionAuditSurface(decisionAuditDraftContext());
    const oosCols = [{key:'window',label:'Window'},{key:'period',label:'기간'},{key:'diff',label:'Sharpe Diff'},{key:'low',label:'95% CI Low'},{key:'high',label:'95% CI High'},{key:'p',label:'p-value'},{key:'result',label:'결론',render:r=>badge(r.result,cls(r.result))}];
    const ledgerCols = [{key:'decision_id',label:'Decision ID'},{key:'time',label:'결정일시'},{key:'decision',label:'결정',render:r=>badge(r.decision,cls(r.decision))},{key:'strategy',label:'전략ID'},{key:'note',label:'요약 노트'},{key:'user',label:'결정자'},{key:'role',label:'역할'},{key:'links',label:'증거 링크'},{key:'hash',label:'레코드 해시'},{key:'verified',label:'검증',render:r=>`<span class="green">✓ ${r.verified}</span>`}];
    const latestDecision = a.ledger[0] || {};
    const decisionOptions = ['PROMOTE','COMPLEMENT','HOLD','REJECT'];
    const side = panel('감사 compact navigation', ['Decision state','OOS evidence','Human Decision','Append-Only Ledger'].map((x,i)=>`<div class="tile"><b>${i+1}. ${x}</b><div>${sparkline(DATA.history.runsOverTime.slice(i,i+12))}</div></div>`).join('')) + panel('감사 상태', infoList([['결정 대기','1건','amber'],['이상','0건','green'],['해시 체인','OK','green'],['WORM 보존','7년']]));
    const decisionFunnel = `<section class="audit-primary-canvas panel" data-ux-primary-canvas="audit">
      <div class="audit-funnel-grid">
        <section class="audit-step-card" data-audit-step="evidence">
          <span class="step-kicker">1. Evidence</span>
          <h3>OOS 성과 차이 · Sharpe spark</h3>
          ${chart('OOS Sharpe 비교', DATA.backtest.equity, {tall:true, value:'Sharpe +0.34'})}
          <div class="notice">OOS W3 보완 필요 · Evidence는 Decision과 분리됩니다.</div>
        </section>
        <section class="audit-step-card" data-audit-step="decision">
          <span class="step-kicker">2. Human Decision</span>
          <h3>결정 입력 · PROMOTE / HOLD / REJECT</h3>
          <div class="audit-decision-options">${decisionOptions.map(x=>`<label class="tile"><input type="radio" name="decision" ${x === 'HOLD' ? 'checked' : ''} /> <b class="${cls(x)}">${x}</b><div class="muted">${x==='PROMOTE'?'정식 전략 추출 후보':x==='COMPLEMENT'?'보완 후 재검토':x==='HOLD'?'추가 OOS 검증 필요':'추출 비권고'}</div></label>`).join('')}</div>
          <label class="muted">결정 노트 (필수)<textarea placeholder="근거 및 보완 사항을 구체적으로 입력하세요."></textarea></label>
          ${manualBtn('결정 제출 (Append-Only 기록)', 'primary', 'data-audit-step="decision"', 'audit-decision-submit')}
        </section>
        <section class="audit-step-card" data-audit-step="ledger">
          <span class="step-kicker">3. Append-Only Ledger</span>
          <h3>최근 결정 · ${escapeHtml(latestDecision.decision_id || 'AUDIT-20250521-001')}</h3>
          ${infoList([['Decision', latestDecision.decision || 'HOLD', cls(latestDecision.decision || 'HOLD')],['Strategy', latestDecision.strategy || 'strat_20250521_v6'],['Verified', latestDecision.verified || 'hash-ok','green'],['User', latestDecision.user || 'kim.research']])}
          <div class="notice warn">Append-Only Ledger · 최종 전략 추출(Export) 승인과 결정 감사(Decision Audit)는 별개입니다.</div>
        </section>
      </div>
      ${decisionAuditSurface}
      <div class="audit-oos-ledger-grid">
        ${panel('PROMOTE 체크리스트', `<div class="info-list">${a.checklist.map((x,i)=>`<div class="info-row"><span>${x}</span><span class="${i===9?'amber':'green'}">${i===9?'검토 필요':'통과'}</span></div>`).join('')}</div><div class="notice warn">체크 완료: 9/10 · 최종 권고: 보완 필요</div>`, { className: 'audit-checklist-card' })}
        ${panel('결정 히스토리 (Append-Only Ledger)', table(ledgerCols, a.ledger), { action: manualBtn('내보내기 CSV 요청','small','data-audit-step="ledger-export"', 'audit-ledger-export') })}
      </div>
    </section>`;
    return `
      ${taskFrame('audit', {
        title: '결정 감사 · Decision funnel과 Append-Only Ledger가 먼저 보이는 V3',
        summary: '감사 전용 화면은 유지하되 OOS evidence → Human Decision → Ledger를 한 primary canvas로 묶고, 보조 증거는 drawer로 접습니다.',
        purpose: 'OOS evidence · PROMOTE checklist · Human Decision · Append-Only Ledger',
        state: `${modeLabel} · ${vm.isFixture ? 'dev/reference' : 'live/read-only'} · ${a.ledger.length} ledger rows`,
        primaryAction: 'OOS 근거 확인 후 Human Decision 기록',
        risk: 'audit-only · no export approval · append-only record',
        actionKind: 'audit-decision-review',
        actionLabel: '결정 상태 확인'
      })}
      ${compactSafetyStrip('audit', ['Audit records decisions only', 'Export approval is separate', 'Append-Only Ledger remains visible'])}
      <div class="audit-task-layout">
        <aside class="side-stack audit-side-compact">${side}</aside>
        <section class="grid audit-main-stack">
          ${provenanceCue(vm)}
          ${renderUxSweepPanel('audit', 'OOS chart + decision funnel')}
          <div class="notice warn"><b>최종 전략 추출(Export) 승인과 결정 감사(Decision Audit)는 별개입니다.</b><span>Evidence → Validation → Human Decision 과정을 Append-Only 불변 원장으로 기록합니다.</span><span class="muted">reference baseline dev/reference · current env ${vm.isFixture ? 'dev/reference' : 'live/read-only'}</span>${badge('Append-Only Ledger','amber')}</div>
          <div class="grid cols-6">${a.summary.map(s=>metricCard(s[0],s[1],s[2], String(s[1]).includes('APPEND')?'green':'' )).join('')}</div>
          ${decisionFunnel}
          ${evidenceDrawer('audit', 'Audit evidence / OOS tables / ledger metadata 열기', `<div class="grid cols-3">${panel('OOS 성과 차이 신뢰구간', table(oosCols, a.oosRows) + chart('OOS Sharpe spark', DATA.backtest.equity, {small:true}))}${panel('알림 & 요약 / 레짐 분해', `<div class="notice warn">경고 2 · 정보 8 · OOS W3 보완 필요</div>${table([{key:'regime',label:'레짐'},{key:'weight',label:'비중'},{key:'v6',label:'Sharpe V6'},{key:'m4',label:'Sharpe M4'},{key:'diff',label:'Diff'}],[{regime:'Trend-Strong',weight:'28%',v6:1.76,m4:1.41,diff:0.35},{regime:'Sideways',weight:'25%',v6:.72,m4:.79,diff:-.07},{regime:'High-Vol',weight:'15%',v6:.41,m4:.62,diff:-.21}])}`)}${panel('감사 메타데이터', infoList([['페이지','결정 감사'],['버전','UI 2.2.0'],['환경','dev/reference'],['사용자','kim.research'],['불변 원장','ON','green'],['해시 체인','OK','green'],['WORM 보존','7년']]))}</div>`)}
        </section>
      </div>${renderSafetyFooter()}`;
  }

  function renderBacktestContractMatrix() {
    const columns = [
      { key: 'endpoint', label: 'Endpoint' },
      { key: 'method', label: 'Method', render: r => badge(r.method, r.method === 'GET' ? 'blue' : 'amber') },
      { key: 'modeBehavior', label: 'Mode behavior' },
      { key: 'evidence', label: 'Live evidence/status', render: r => {
        const ev = state.backtestContractEvidence[r.id] || {};
        return `${badge(ev.status || (isLiveBackendMode ? 'PENDING' : 'INERT'), cls(ev.status || 'hold'))}<div class="muted">${escapeHtml(ev.detail || (isLiveBackendMode ? 'awaiting BacktestAdapter evidence' : INERT_BACKTEST_STATUS))}</div>`;
      } },
      { key: 'owner', label: 'Action owner / reason', render: r => `<b>${escapeHtml(r.owner)}</b><div class="muted">${escapeHtml(r.reason || (r.safeAuto === true ? 'safe read-only GET auto-probe in live mode only' : 'conditional read; no fake success without IDs'))}</div>` }
    ];
    const modeNote = isLiveBackendMode
      ? 'LIVE mode: BacktestAdapter may call safe GET/read endpoints only; mutating POST endpoints stay manual-gated/not-auto-invoked.'
      : `${modeLabel} mode: ${INERT_BACKTEST_STATUS}. Matrix is fixture/static only.`;
    const liveErrorCount = Object.values(state.backtestContractEvidence).filter(ev => ev && ev.status === 'LIVE ERROR').length;
    const errorNotice = liveErrorCount
      ? `<div class="notice danger" data-backtest-live-error-summary><b>LIVE ERROR</b><span>${liveErrorCount} safe-read endpoint(s) failed; fixture charts remain labeled and no mock success is substituted.</span></div>`
      : '';
    return panel('Backtest API Contract Matrix', `<div class="notice"><span>${escapeHtml(modeNote)}</span>${badge(state.backtestProbeComplete ? 'Evidence settled' : isLiveBackendMode ? 'Live probe pending' : 'Fixture inert', state.backtestProbeComplete ? 'green' : 'amber')}</div>${errorNotice}${table(columns, BacktestContracts)}`);
  }
  function renderBacktestLiveProbeBanner() {
    if (!isLiveBackendMode) return '';
    const evidence = Object.values(state.backtestContractEvidence);
    const errorCount = evidence.filter(ev => ev && ev.status === 'LIVE ERROR').length;
    const pendingCount = evidence.filter(ev => ev && ev.status === 'PENDING').length;
    if (errorCount) {
      return `<div class="notice danger" data-backtest-live-probe-status><b>LIVE ERROR</b><span>${errorCount} safe-read endpoint(s) failed against ${escapeHtml(state.baseUrl)}. Fixture charts remain labeled; no mock success is substituted.</span></div>`;
    }
    return `<div class="notice warn" data-backtest-live-probe-status><b>Live probe pending</b><span>${pendingCount || BacktestContracts.filter(c => c.safeAuto === true).length} safe-read endpoint(s) are being checked; mutating POST endpoints remain manual-gated.</span></div>`;
  }
  function renderBacktest() {
    const b = DATA.backtest;
    BacktestAdapter.ensurePageEvidence();
    const modeBadge = isLiveBackendMode ? badge('LIVE read adapter', 'green') : badge('Reference/demo inert', 'amber');
    const controlDisabled = isLiveBackendMode ? '' : ' disabled aria-disabled="true" data-inert-control="true"';
    const buyCode = '//@version=5\nindicator("BreakOut_v2 - Long Entry", overlay=true)\nfastLen = input.int(20, "Fast Length")\nslowLen = input.int(60, "Slow Length")\natr = ta.atr(14)\nlongCond = ta.crossover(ta.sma(close, fastLen), ta.sma(close, slowLen))\nvolumeGate = volume > ta.sma(volume, 20) * 1.15\nentry = longCond and volumeGate';
    const sellCode = '//@version=5\nindicator("BreakOut_v2 - Exit", overlay=true)\ntrailAtr = ta.atr(14) * 1.8\ntrailStop = ta.highest(high, 10) - trailAtr\nprofitLock = close < ta.sma(close, 20)\nexitCond = close < trailStop or profitLock';
    const paramForm = `
      <div class="form-grid backtest-select-grid">
        <label>매수 전략<select${controlDisabled}><option>BreakOut_v2 (v1.4)</option></select></label>
        <label>매도 전략<select${controlDisabled}><option>BreakOut_Exit_v1 (v1.2)</option></select></label>
        <label>시작일<input value="2022-01-01"${controlDisabled} /></label>
        <label>종료일<input value="2025-05-16"${controlDisabled} /></label>
        <label>Timeframe<select${controlDisabled}><option>1분(1m)</option><option>Tick</option></select></label>
        <label>Engine Count<input value="8 (Auto)"${controlDisabled} /></label>
      </div>`;
    const validationRows = [
      ['Validation', 'PASS · syntax/local vars resolved', 'green'],
      ['Manual Gate', isLiveBackendMode ? '대기 · user action required' : 'INERT · reference/demo disabled', 'amber'],
      ['Run Preview', '#10235 BreakOut_v2 · 1m · 10,000,000 bars'],
      ['Result Path', 'validate → gated run → analyze → evidence drawer'],
    ];
    const metricsGrid = Object.entries(b.metrics).map(([key, value]) => metricCard(key.toUpperCase(), value, key === 'mdd' ? 'drawdown guard' : '', String(value).startsWith('-') ? 'red' : 'green')).join('');
    const editorBody = `<div class="condition-editor-grid">${readonlyCodeEditor('매수 조건식 · Long Entry', buyCode, 'data-backtest-condition="buy"')}${readonlyCodeEditor('매도 조건식 · Exit/Short', sellCode, 'data-backtest-condition="sell"')}</div>`;
    const analyzeBody = `<div class="backtest-analysis-grid">${panel('주요 지표', `<div class="grid cols-4">${metricsGrid}</div>`)}${panel('에쿼티 곡선 · primary result', chart('에쿼티 곡선', b.equity, {value:'+23.41%', tall:true}))}${panel('포지션/최근 거래', `<div class="backtest-position-split"><span class="green">롱 78.4%</span><span class="red">숏 21.6%</span></div><ul><li>LONG Exit +0.68%</li><li>LONG Entry</li><li>LONG Exit -0.21%</li></ul>`)}</div>`;
    const recent = table([{key:'id',label:'ID'},{key:'name',label:'전략명'},{key:'status',label:'상태',render:r=>badge(r.status,cls(r.status))},{key:'profit',label:'수익률'}], b.recent);
    const evidence = `${renderBacktestContractMatrix()}${renderUxSweepPanel('backtest', 'equity + report comparison charts')}${panel('최근 백테스트 / 안전 GET 증거', recent)}${panel('스윕 / self.vars 빌더', `${manualBtn('+ 파라미터 추가','small', '', 'bt-vars-add')}${manualBtn('self.vars 파싱','small blue', '', 'bt-vars-parse')}<div class="notice">추출된 변수 (0) · 변수가 없습니다.</div>`)}${panel('진행 중인 작업 로그', `<div class="info-row"><b>#10235 BreakOut_v2 백테스트 (1m)</b><span>${badge(isLiveBackendMode ? '사용자 게이트 대기' : 'INERT fixture','amber')}</span></div><div class="progress"><span style="width:63.4%"></span></div><div class="code-box">${b.logs.map(escapeHtml).join('\n')}</div>`)}`;
    return `<div class="backtest-task-layout">
      ${taskFrame('backtest', {
        title: '백테스트 · 조건식 편집과 검증을 먼저 보여주는 V3',
        summary: 'V2의 큰 조건식 편집 장점을 계승하고, 안전/계약 증거는 접힌 drawer로 내려 작업 흐름을 방해하지 않습니다.',
        purpose: '조건식 선택·편집·검증·수동 실행·결과 분석',
        state: isLiveBackendMode ? 'LIVE READ-ONLY MODE · safe-read live backend · manual actions only' : 'DEMO / REFERENCE INERT MODE · reference/demo inert · no backend mutation',
        primaryAction: '조건식 검증 후 수동 실행 검토',
        risk: 'no live order · no page-load POST · manual-gated /bt/*',
        actionKind: 'bt-task-primary-validate',
        actionLabel: '검증 상태 확인'
      })}
      ${compactSafetyStrip('backtest', ['/bt/* mutating endpoints are not auto-invoked', 'manual-gated and never page-load triggered'])}
      ${renderBacktestLiveProbeBanner()}
      <div class="notice compact-feature-map" data-backtest-required-text="legacy-v2-compare">지원 흐름: 실행 파라미터 · 최적화 · WFO · 스윕 · 조건식 편집 · 결과 분석 · 독립 HTML 보고서</div>
      <section class="backtest-primary-canvas panel" data-ux-primary-canvas="backtest">
        <div class="backtest-step-grid">
          <div class="backtest-step-card" data-backtest-step="select">
            <div class="step-kicker">1 Select</div>
            <h3>전략과 데이터 범위</h3>
            ${paramForm}
            <div class="bt-action-row">${manualBtn('설정 저장','small blue', '', 'bt-settings-save')}${modeBadge}</div>
          </div>
          <div class="backtest-step-card validation-card" data-backtest-step="validate">
            <div class="step-kicker">3 Validate</div>
            <h3>검증 상태</h3>
            <div data-backtest-validation-status>${infoList(validationRows)}</div>
            <div class="bt-action-row">${manualBtn('검증','small blue', '', 'bt-strategy-validate')}${manualBtn('변수 추출','small', '', 'bt-extract-vars')}</div>
          </div>
        </div>
        <div class="backtest-editor-panel" data-backtest-step="edit">
          <div class="step-kicker">2 Edit</div>
          <h3>매수/매도 조건식 · V2보다 큰 1차 작업 영역</h3>
          ${editorBody}
          <div class="bt-action-row">${manualBtn('저장','small primary', '', 'bt-strategy-save')}${manualBtn('삭제','small danger', '', 'bt-strategy-delete')}<span class="muted">저장/삭제는 human-gated · reference/demo에서는 inert</span></div>
        </div>
        <div class="backtest-run-analysis">
          <section class="panel gated-run-card" data-backtest-step="gated-run">
            <div class="panel-header"><span>4 Gated Run Preview</span>${badge(isLiveBackendMode ? 'manual live action' : 'Reference/demo inert', 'amber')}</div>
            <div class="panel-body">
              ${renderBacktestPreflightPanel()}
              ${renderBacktestJobProgressPanel()}
              ${infoList([['Job','#10235 BreakOut_v2'],['Progress','63.4%'],['Bars','6,342,112 / 10,000,000'],['Gate','수동 실행 전 대기','amber']])}
              <div class="progress amber"><span style="width:63.4%"></span></div>
              <div class="bt-action-row">${manualBtn('백테스트 실행 검토','primary', '', 'bt-run-preview')}${manualBtn('작업 취소','danger', '', 'bt-job-cancel')}</div>
            </div>
          </section>
          <section data-backtest-step="analyze">${renderBacktestAnalysisSurface()}${analyzeBody}</section>
        </div>
      </section>
      ${evidenceDrawer('backtest', 'Backtest API Contract Matrix / UX proof / 안전 GET 증거 열기', evidence)}
    </div>${renderSafetyFooter()}`;
  }

  function renderReplayContractMatrix() {
    const columns = [
      { key: 'endpoint', label: 'Endpoint / action / message' },
      { key: 'method', label: 'Method / type', render: r => badge(`${r.method} · ${r.kind}`, r.method === 'GET' ? 'blue' : r.method === 'WS' ? 'violet' : 'amber') },
      { key: 'modeBehavior', label: 'Mode behavior' },
      { key: 'evidence', label: 'Live evidence/status', render: r => {
        const ev = state.replayContractEvidence[r.id] || {};
        return `${badge(ev.status || (isLiveBackendMode ? 'PENDING' : 'INERT'), cls(ev.status || 'hold'))}<div class="muted">${escapeHtml(ev.detail || (isLiveBackendMode ? 'awaiting ReplayAdapter evidence; failures stay visible with retry/manual recovery' : INERT_REPLAY_STATUS))}</div>`;
      } },
      { key: 'owner', label: 'Owner / reason / recovery', render: r => `<b>${escapeHtml(r.owner)}</b><div class="muted">${escapeHtml(r.reason || (r.safeAuto === true ? 'safe read-only GET auto-probe in live mode only' : 'conditional or protocol contract; do not fake success'))}</div>` }
    ];
    const modeNote = isLiveBackendMode
      ? 'LIVE mode: ReplayAdapter probes safe REST reads only; /sim/ws stays user-gated/manual and exposes start, pause, resume, speed, seek, stop plus meta, bars, history, done, error protocol.'
      : `${modeLabel} mode: ${INERT_REPLAY_STATUS}. Replay API/WS Contract Matrix is fixture/static only.`;
    return panel('Replay API/WS Contract Matrix', `<div class="notice"><span>${escapeHtml(modeNote)}</span>${badge(state.replayProbeComplete ? 'Evidence settled' : isLiveBackendMode ? 'Live probe pending' : 'Fixture inert', state.replayProbeComplete ? 'green' : 'amber')}</div>${table(columns, ReplayContracts)}`);
  }
  function renderReplay() {
    const r = DATA.replay;
    const stockCols = [{key:'code',label:'코드'},{key:'name',label:'종목명'},{key:'price',label:'최근가'},{key:'change',label:'변동률'}];
    const signalCols = [{key:'time',label:'시간'},{key:'stock',label:'종목'},{key:'signal',label:'신호',render:x=>badge(x.signal,x.signal==='BUY'?'green':'red')},{key:'strategy',label:'전략'},{key:'price',label:'가격'},{key:'qty',label:'수량'},{key:'reason',label:'사유'}];
    ReplayAdapter.ensurePageEvidence();
    const modeBadge = isLiveBackendMode ? badge('LIVE read adapter', 'green') : badge('Reference/demo inert', 'amber');
    const controlDisabled = isLiveBackendMode ? '' : ' disabled aria-disabled="true" data-inert-control="true"';
    const selectedStock = r.stocks[0] || { code: '000000', name: '선택 없음', price: 0, change: '0%', candles: [] };
    const selectedSignal = r.signalLog[0] || { time: 'n/a', stock: selectedStock.code, signal: 'WAIT', strategy: 'none', price: '-', reason: 'no signal' };
    const selectedBarTime = selectedSignal.time || selectedStock.candles?.[Math.max(0, (selectedStock.candles || []).length - 1)]?.t || 'n/a';
    const selectedBarPrice = selectedSignal.price || String(selectedStock.price.toLocaleString());
    const replayControls = ['▶ 재생','Ⅱ 일시정지','▶ 재개','1x','5x','20x','60x','seek','■ 정지'].map((x,i)=>manualBtn(x, i===0 ? 'primary' : i===8 ? 'danger' : 'small', '', `sim-playback-${i}`)).join('');
    const simGateButtons = ['start','pause','resume','speed','seek','stop'].map(x=>manualBtn(x,'small', '', `sim-ws-${x}`)).join('');
    const instantReplay = manualBtn('즉시 시작','primary', '', 'sim-start');
    const sourceStep = `<div class="replay-field-grid">
      <label data-replay-step="source">데이터 소스<select${controlDisabled}><option>STOM Tick DB (Local)</option><option>분봉 DB (Local)</option></select></label>
      <label>거래일<select${controlDisabled}><option>2025-05-27</option><option>2025-05-26</option></select></label>
      <label>종목<select${controlDisabled}><option>${escapeHtml(selectedStock.code)} ${escapeHtml(selectedStock.name)}</option></select></label>
      <label data-replay-step="strategy">전략<select${controlDisabled}><option>STOM_AI_MOMENTUM_V1 / EXIT_V1</option></select></label>
    </div>`;
    const previewStep = `<div data-replay-step="preview">${infoList([['선택 종목', `${selectedStock.code} ${selectedStock.name}`],['최근가', selectedStock.price.toLocaleString()],['변동률', selectedStock.change, String(selectedStock.change).startsWith('+') ? 'green' : 'red'],['프리뷰 bars', `${(selectedStock.candles || []).length} candle`],['신호', `${selectedSignal.signal} · ${selectedSignal.time}`, cls(selectedSignal.signal)]])}</div>`;
    const quickStart = `<div class="replay-quick-start" data-replay-quick-start>
      <span class="muted">빠른 시작</span>
      ${manualBtn('최근 거래일', 'small blue', 'data-replay-quick="recent"', 'replay-quick-recent')}
      ${manualBtn('최대 상승일', 'small blue', 'data-replay-quick="max-rise"', 'replay-quick-max-rise')}
      ${manualBtn('내가 선택하기', 'small', 'data-replay-quick="custom"', 'replay-quick-custom')}
    </div>`;
    const playback = `<div class="replay-playback-sticky" data-replay-playback-sticky data-replay-step="manual-start">
      <div class="panel-header"><span>재생 컨트롤 · /sim/ws 수동 게이트 · sticky timeline</span>${badge('/sim/ws manual gate', 'amber')}</div>
      <div class="replay-controls">${instantReplay}${replayControls}</div>
      <div class="replay-timeline" role="slider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="21"><span style="width:21.21%"></span></div>
      <div class="muted">Timeline 09:00:00 → 15:30:00 · cursor 10:23:18 · /sim/ws는 manual user-gated; never auto-opened; 사용자 수동 시작만 허용</div>
    </div>`;
    const selectedBar = `<div class="selected-bar-card" data-replay-selected-bar>
      <b>선택 bar · ${escapeHtml(selectedStock.code)} ${escapeHtml(selectedStock.name)}</b>
      <div class="grid cols-4">${metricCard('time', selectedBarTime)}${metricCard('close', selectedBarPrice, '', 'green')}${metricCard('signal', selectedSignal.signal, '', cls(selectedSignal.signal))}${metricCard('reason', selectedSignal.reason || 'manual inspect')}</div>
      <p class="muted">차트 hover/keyboard focus 없이도 선택 봉과 신호 로그가 같은 문맥으로 보입니다.</p>
    </div>`;
    const replayBars = selectedStock.candles || [];
    const replayCursorIndex = Math.max(0, replayBars.findIndex(c => String(c.time || c.t || '') === String(selectedBarTime)));
    const replayTimelineSurface = renderReplayTimelineSurface({
      bars: replayBars,
      signals: r.signalLog || [],
      trades: r.trades || [],
      positions: r.positions || [],
      logs: r.logs || [`cursor ${selectedBarTime} · ${selectedStock.code} · shared chart/log/detail state`],
      selectedIndex: replayCursorIndex,
      selectedTime: selectedBarTime,
      selectedCode: selectedStock.code,
      handoff: {
        date: REPLAY_PREFLIGHT_DEFAULTS.date,
        code: selectedStock.code,
        buy: REPLAY_PREFLIGHT_DEFAULTS.buy,
        sell: REPLAY_PREFLIGHT_DEFAULTS.sell,
        src: REPLAY_PREFLIGHT_DEFAULTS.src,
        selectedIndex: replayCursorIndex,
      },
    }, selectedStock);
    const mainCanvas = `<section class="replay-primary-canvas panel" data-ux-primary-canvas="chart_replay">
      ${renderReplayPreflightPanel()}
      ${renderReplayPlaybackControls()}
      <div class="replay-first-row">
        <div class="replay-picker-card" data-replay-step="source">
          <div class="step-kicker">1 Source / Date / Symbol / Strategy</div>
          <h3>V2처럼 바로 고르는 리플레이 시작점</h3>
          ${sourceStep}
          ${quickStart}
          ${previewStep}
        </div>
        <div class="replay-market-card">
          <div class="step-kicker">시장 미니맵</div>
          ${heatmap(['전기전자','금융','서비스','운수장비'], ['A','B','C','D','E'], [[.2,.5,.7,.3,.4],[.1,.8,.4,.5,.3],[.9,.2,.5,.6,.1],[.3,.7,.2,.4,.8]], {hideValues:false})}
          <div class="heatmap-narrative" data-heatmap-selected-narrative>선택 셀: 전기전자/B · 강도 0.50 · 시장 미니맵은 색상과 숫자를 함께 제공해 해석 가능한 참고 정보입니다.</div>
        </div>
      </div>
      ${playback}
      ${replayTimelineSurface}
      <div class="replay-investigation-grid" data-replay-step="investigate">
        <div class="primary-candle-card">
          <div class="panel-header"><span>실시간 리플레이 차트 · candle primary canvas</span>${modeBadge}</div>
          ${candleSvg(selectedStock.candles, selectedStock)}
          ${selectedBar}
        </div>
        <div class="signal-log-card" data-replay-signal-log>
          <div class="panel-header"><span>전략 신호 로그 · synchronized</span>${badge('signal log', 'blue')}</div>
          ${table(signalCols, r.signalLog)}
        </div>
      </div>
    </section>`;
    const evidence = `${renderReplayContractMatrix()}${renderUxSweepPanel('replay', 'primary candle chart + signal log + market heatmap')}${panel('사용 가능 일자 / 종목 원장', `<div class="grid cols-7">${Array.from({length:23},(_,i)=>`<span class="tile" style="min-height:28px;text-align:center;padding:4px">${i+1}</span>`).join('')}</div>${table(stockCols, r.stocks)}`)}${panel('17 /sim/ws 수동 게이트', infoList([['연결 상태','미연결 · user-gated','amber'],['프로토콜','WS /sim/ws'],['자동 오픈','금지'],['지원 액션','start · pause · resume · speed · seek · stop'],['수신 메시지','meta · bars · history · done · error'],['복구','error 표시 후 fixture 차트 유지 · 수동 재시도']]) + `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">${simGateButtons}</div><div class="notice warn">/sim/ws is live-only and manual; ReplayAdapter never calls new WebSocket for this stream on page load.</div>`)}${panel('세션 노트 / 오류 복구', `<ul><li>모멘텀 전략 리플레이 학습 세션</li><li>1초 집계 기반 신호 검증</li><li>리플레이 전용</li></ul><div class="notice danger">데이터 경고는 차트 아래에 보존하고 fixture 차트를 fake-success로 덮지 않습니다.</div><div class="notice warn">Live probe failure recovery: surface LIVE ERROR, preserve static replay chart, allow manual retry without fake success.</div>`)}`;
    return `<div class="replay-task-layout">
      ${taskFrame('chart_replay', {
        title: '차트 리플레이 · 선택에서 재생까지 바로 이어지는 V3',
        summary: 'V2의 빠른 시작·날짜·종목·재생·타임라인 흐름을 계승하고, API/WS 계약 증거는 접힌 drawer로 내립니다.',
        purpose: '데이터 소스·거래일·종목·전략 선택 후 신호를 조사',
        state: isLiveBackendMode ? 'LIVE READ-ONLY REPLAY MODE · safe REST reads only' : 'DEMO / REFERENCE REPLAY INERT MODE · static replay fixture',
        primaryAction: '수동 재생 준비와 신호 로그 조사',
        risk: 'no live order · no auto /sim/ws · user-gated playback',
        actionKind: 'replay-manual-start',
        actionLabel: '수동 재생 준비'
      })}
      ${compactSafetyStrip('chart_replay', ['Replay is historical only', '/sim/ws never auto-opens', 'manual-gated playback actions only'])}
      ${mainCanvas}
      ${evidenceDrawer('chart_replay', 'Replay API/WS Contract Matrix / UX proof / safe REST evidence 열기', evidence)}
    </div>${renderSafetyFooter()}`;
  }

  function candleSvg(candles, stock) {
    const w=520,h=230,pad=22;
    const rawCandles = Array.isArray(candles) ? candles : [];
    const diagnostics = rawCandles.reduce((acc, c) => {
      acc.total += 1;
      if (!c || !Number.isFinite(Number(c.o)) || !Number.isFinite(Number(c.h)) || !Number.isFinite(Number(c.l)) || !Number.isFinite(Number(c.c))) acc.malformed += 1;
      return acc;
    }, { total: 0, malformed: 0 });
    const provenance = chartProvenance({
      source: isLiveBackendMode ? 'fixture fallback · sim probe not driving chart' : 'reference replay fixture',
      freshness: isLiveBackendMode ? 'stale-replay-fixture-fallback' : 'reference-replay-static',
    });
    const cleanCandles = rawCandles.filter(c => c && Number.isFinite(Number(c.o)) && Number.isFinite(Number(c.h)) && Number.isFinite(Number(c.l)) && Number.isFinite(Number(c.c)));
    if (!cleanCandles.length) {
      return `<div class="chart-box candle-box" data-chart-box data-ux-chart><div class="chart-title" data-chart-title><span>${escapeHtml(stock.code)} ${escapeHtml(stock.name)}</span></div>${chartStateBadges(provenance, diagnostics)}<div class="chart-empty" role="status">캔들 데이터 없음 · source=${escapeHtml(provenance.source)} · run_id=${escapeHtml(provenance.runId)} · freshness=${escapeHtml(provenance.freshness)} · status=${escapeHtml(provenance.status)} · malformed=${diagnostics.malformed}</div></div>`;
    }
    const lows=cleanCandles.map(c=>Number(c.l)), highs=cleanCandles.map(c=>Number(c.h));
    const closes=cleanCandles.map(c=>Number(c.c));
    const min=Math.min(...lows), max=Math.max(...highs), range=max-min || 1;
    const x=(i)=>pad+(cleanCandles.length <= 1 ? 0 : i*(w-pad*2)/(cleanCandles.length-1));
    const y=(v)=>h-pad-(v-min)/range*(h-pad*2);
    const bw=Math.max(3,(w-pad*2)/cleanCandles.length*.55);
    const chartId = registerChart({
      kind: 'candlestick',
      title: `리플레이 차트 ${stock.code}`,
      ...provenance,
      malformedCount: diagnostics.malformed,
      min,
      max,
      labels: cleanCandles.map((c, i) => c.time || c.t || `bar-${i + 1}`),
      series: [{ name: 'Close', values: closes, color: 'var(--cyan)' }],
    });
    const grid=[0,.25,.5,.75,1].map(t=>`<line x1="${pad}" y1="${pad+t*(h-pad*2)}" x2="${w-pad}" y2="${pad+t*(h-pad*2)}" stroke="rgba(142,164,181,.14)"/>`).join('');
    const items=cleanCandles.map((c,i)=>{
      const open=Number(c.o), close=Number(c.c), high=Number(c.h), low=Number(c.l);
      const up=close>=open, col=up?'var(--green)':'var(--red)';
      const yy=Math.min(y(open),y(close));
      const hh=Math.max(2,Math.abs(y(open)-y(close)));
      const signal=c.signal==='BUY'?`<polygon class="chart-candle" data-series-index="0" points="${x(i)},${y(low)+10} ${x(i)-5},${y(low)+18} ${x(i)+5},${y(low)+18}" fill="var(--green)"/>`:c.signal==='SELL'?`<polygon class="chart-candle" data-series-index="0" points="${x(i)},${y(high)-10} ${x(i)-5},${y(high)-18} ${x(i)+5},${y(high)-18}" fill="var(--red)"/>`:'';
      const title = `${stock.code} ${stock.name} · ${c.time || c.t || `bar-${i+1}`} · O ${chartValue(open)} H ${chartValue(high)} L ${chartValue(low)} C ${chartValue(close)}${c.signal ? ` · ${c.signal}` : ''}`;
      return `<line class="chart-candle" data-series-index="0" x1="${x(i)}" y1="${y(high)}" x2="${x(i)}" y2="${y(low)}" stroke="${col}"/><rect class="chart-candle" data-series-index="0" x="${x(i)-bw/2}" y="${yy}" width="${bw}" height="${hh}" fill="${col}" opacity=".82"><title>${escapeHtml(title)}</title></rect>${signal}`;
    }).join('');
    const label = datumLabel(chartRegistry[chartId], cleanCandles.length - 1);
    return `<div class="chart-box candle-box" data-chart-box data-ux-chart><div class="chart-title" data-chart-title><span>${escapeHtml(stock.code)} ${escapeHtml(stock.name)}</span></div>${chartStateBadges(provenance, diagnostics)}<svg class="candle-chart interactive-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" tabindex="0" role="img" aria-label="${escapeHtml(label)}" data-chart-id="${chartId}" data-chart-count="${cleanCandles.length}" data-chart-status="${escapeHtml(provenance.status)}" data-chart-malformed="${diagnostics.malformed}"><title>${escapeHtml(label)}</title>${grid}<line class="chart-crosshair-line" x1="${w-pad}" x2="${w-pad}" y1="${pad}" y2="${h-pad}"/>${items}<text x="${pad}" y="18" fill="var(--text)" font-size="12">${escapeHtml(stock.code)} ${escapeHtml(stock.name)}</text></svg><div class="chart-active-datum" data-chart-active-value aria-live="polite">${escapeHtml(`latest · ${label}`)}</div></div>`;
  }

  function attachPageEvents() {
    document.querySelectorAll('[data-action="inspector"]').forEach(el => el.addEventListener('click', openInspectorModal));
    document.querySelectorAll('[data-action="approval"]').forEach(el => el.addEventListener('click', openApprovalModal));
    document.querySelectorAll('[data-action="process-node"]').forEach(el => el.addEventListener('click', () => openProcessNodeModal(el.dataset.processNode)));
    document.querySelectorAll('[data-process-run-selector]').forEach(el => el.addEventListener('change', () => { state.processSelectedRunId = el.value; render(); }));
    document.querySelectorAll('[data-record-decision-confirm]').forEach(el => el.addEventListener('click', () => {
      let payload = {};
      try { payload = JSON.parse(el.dataset.recordDecisionPayload || '{}'); } catch (_) { payload = {}; }
      recordDecisionAfterConfirm(payload).then(() => render());
    }));
    attachChartEvents();
  }
  function openSettingsModal() {
    openModal('설정 모달 미리보기', `<div class="notice">목표/제약 · 평가 스코프 · 엔진 리소스 · 과적합 가드 · AI · GPT 5.5 xhigh auth test</div><div class="grid cols-3" style="margin-top:10px">${['목표/제약','평가 스코프','엔진 리소스','과적합 가드','AI','GPT 5.5 xhigh auth test'].map((g,i)=>panel(g, `<label>활성화<input type="checkbox" checked /></label><label>값<input value="${['Sharpe Max','OOS + Holdout','16 workers','MDD ≤ 25%','Provider STOM AI','xhigh token 검증'][i]}" /></label>`)).join('')}</div>`, 'wide');
  }
  function openInspectorModal() {
    openModal('Strategy Inspector · S136-0321', `${miniTabs(['Buy Code','Sell Code','Previous Diff','Prompt Timeline','AI Context','Current Code'],'Buy Code')}<div class="inspector-inline"><div>${codeBox(DATA.strategyCode.buy + '\n\n' + DATA.strategyCode.sell)}</div><div>${infoList([['언어','STOM (Korean)'],['문법 검사','정상','green'],['AI Context','복사 가능'],['Prompt Timeline','28 steps'],['Previous Diff','+14 / -6']])}<div style="display:grid;gap:8px;margin-top:10px">${btn('복사','blue')} ${btn('높이 확장','')} ${btn('AI Context 복사','violet')}</div></div></div>`, 'wide');
  }
  function openProcessNodeModal(nodeId) {
    const vm = RemodelAdapters.process();
    const model = normalizeProcessPayload(vm.data, vm);
    const node = model.nodes.find(n => String(n.id) === String(nodeId)) || model.nodes.find(n => n.status === '진행 중') || model.nodes[0] || {};
    openModal(`Process Node · ${node.title || 'unknown'}`, `${infoList([['node_id', node.id || 'none'],['title', node.title || 'none'],['status', node.status || 'EMPTY', cls(node.status)],['items', node.items ?? 'n/a'],['time', node.time || 'n/a'],['desc', node.desc || 'n/a'],['payload_source', model.source],['malformed', String(model.malformed.length)]])}<hr/>${renderProcessRequiredFields(model)}`, 'wide');
  }
  function openApprovalModal() {
    openModal('Winner 승인 / Export · Human Confirm', `<div class="notice warn">최종 전략 Export는 인간 승인 후에만 가능합니다. Decision Audit과 분리되어 있으며 실거래 실행이 아닙니다.</div><div class="form-grid" style="margin-top:12px"><label>Buy 전략명<input value="MeanRev_Adaptive_v9_BUY" maxlength="60" /></label><label>Sell 전략명<input value="MeanRev_Adaptive_v9_SELL" maxlength="60" /></label></div><label class="muted">승인 코멘트<textarea placeholder="승인 근거 및 연구 목적을 작성하세요."></textarea></label><label style="display:flex;gap:8px;margin:10px 0"><input type="checkbox" /> 위 전략을 연구 산출물로 Export하는 것에 명시적으로 동의합니다.</label><div>${btn('승인 및 Export (Human Confirm)','violet')} ${btn('취소','')}</div>`, 'wide');
  }
  function openModal(title, body) {
    modalRoot.innerHTML = `<div class="modal-backdrop open"><div class="modal"><div class="modal-header"><span>${escapeHtml(title)}</span><button class="btn small" data-modal-close>닫기</button></div><div class="modal-body">${body}</div></div></div>`;
    modalRoot.querySelector('[data-modal-close]').addEventListener('click', closeModal);
    modalRoot.querySelector('.modal-backdrop').addEventListener('click', e => { if (e.target.classList.contains('modal-backdrop')) closeModal(); });
  }
  function closeModal() { modalRoot.innerHTML = ''; }

  render();
  if (isLiveBackendMode) reconnectBackend();
})();
