from pathlib import Path


FRONTEND = Path("ai_strategy_loop/dashboard/frontend")


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_replay_exposes_primary_journey_and_market_time_contract() -> None:
    # Given: the keep-alive Replay wrapper from W2-A.
    source = _read("v4-replay.jsx")

    # When: an analyst enters Replay.
    # Then: the control journey, connection feedback, and honest time basis are named.
    assert 'aria-labelledby="v4-replay-journey-title"' in source
    assert 'aria-live="polite"' in source
    assert "연결 · 데이터 선택" in source
    assert "재생 · 일시정지" in source
    assert "정확 탐색 · 배속" in source
    assert "실제 시장 시각과 프레임 타임스탬프" in source


def test_replay_preserves_w2a_activation_boundary() -> None:
    # Given: W2-A passes an explicit active flag through this wrapper.
    source = _read("v4-replay.jsx")

    # When: the UI semantics are strengthened.
    # Then: the keep-alive child still receives the fail-closed activation value.
    assert "function V4Replay({ baseUrl, wsStatus, active })" in source
    assert "<SimulationTab baseUrl={baseUrl} wsStatus={wsStatus} active={active} />" in source
    assert "style={{" not in source


def test_history_names_archive_summary_compare_and_stale_states() -> None:
    # Given: History owns the canonical records and index components.
    source = _read("v4-history.jsx")

    # When: records are loading, unavailable, or disconnected.
    # Then: regions and freshness remain explicit without a silent live fallback.
    assert 'aria-labelledby="v4-history-journey-title"' in source
    assert 'aria-labelledby="v4-history-archive-title"' in source
    assert 'aria-labelledby="v4-history-index-title"' in source
    assert 'data-region="scroll"' in source
    assert 'aria-live="polite"' in source
    assert "아카이브 선택" in source
    assert "요약 확인" in source
    assert "Compare" in source
    assert "마지막 응답일 수 있습니다" in source
    assert "selectedResearchId" in source
    assert "onSelectResearch={selectResearch}" in source
    assert "legacy run/gen archive selection" in source
    assert "<ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} selectedResearchId={selectedResearchId} onSelectResearch={selectResearch} />" in source
    assert "<ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} selectedResearchId={selectedResearchId} onSelectResearch={selectResearch} />" in source
    assert "<AuditDecisionTrace baseUrl={baseUrl} selectedResearchId={selectedResearchId} onSelectResearch={selectResearch} showDecisionLedger={false} />" in source
    assert "<VerdictPanel baseUrl={baseUrl} onNavigate={onNavigate} />" in source
    assert "style={{" in source
    assert "아카이브/Compare 탐색만 읽기 전용" in source
    assert "Append-only 결정 기록은 쓰기 예외" in source


def test_history_keeps_restricted_analysis_and_single_compare_and_decision_owners() -> None:
    history = _read("v4-history.jsx")
    audit = _read("v4-audit.jsx")
    lab = _read("rl-panel.jsx")

    assert "function V4History({ baseUrl, wsStatus, runId, onNavigate })" in history
    assert 'import { ResearchLabPanel } from "./rl-panel.jsx";' in history
    assert 'import { ResearchProPanel } from "./research-pro.jsx";' not in history
    assert "ResearchProPanel" not in history
    assert 'enabledTabIds={["edge", "feature", "correlation", "combos"]}' in history
    assert "showOpsStatus={false}" in history
    assert "showWorkbenchLink={false}" in history
    assert "campaign ID에서 run ID를 추정하지 않습니다." in history
    assert '<RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />' in history
    assert history.count("RunComparePanel") == 2
    assert '<ResearchWikiPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />' in history
    assert "/edge_ratio" not in history
    assert "/hall_of_fame" not in history
    assert "/decisions" not in history
    assert "function AuditDecisionTrace({ baseUrl, selectedResearchId, onSelectResearch, showDecisionLedger = true })" in audit
    assert "if (!showDecisionLedger) return undefined;" in audit
    assert "if (!showDecisionLedger) return null;" in audit
    assert "}, [baseUrl, showDecisionLedger]);" in audit
    assert audit.count('fetch(base + "/decisions"') == 1
    assert audit.index("if (!showDecisionLedger) return undefined;") < audit.index('fetch(base + "/decisions"')
    assert audit.index("if (!showDecisionLedger) return null;") < audit.index('<section className="panel v4-audit-trace"')
    assert "disableDecisions" not in audit
    assert "<AuditDecisionTrace baseUrl={baseUrl} selectedResearchId={selectedResearchId} onSelectResearch={onSelectResearch} />" in audit
    assert "enabledTabIds" in lab
    assert "showOpsStatus = true" in lab
    assert "showWorkbenchLink = true" in lab
    assert "if (!showOpsStatus || !baseUrl) return undefined;" in lab

def test_history_governed_panels_have_controlled_identity_and_abort_guards() -> None:
    tree = _read("history-condition-tree.jsx")
    records = _read("research-records-panel.jsx")
    viz = _read("history-viz.jsx")

    assert "function HistoryConditionTreePanel({ baseUrl, wsStatus, selectedResearchId, onSelectedResearchIdChange })" in tree
    assert "const selectedId = selectedResearchId || \"\";" in tree
    assert "new AbortController()" in tree
    assert "generation !== generationRef.current" in tree
    assert "controller.abort()" in tree
    assert "aria-pressed={active}" in tree
    assert "aria-selected={active}" not in tree
    assert 'role="button"' in tree
    assert 'e.key === "Enter" || e.key === " "' in tree
    assert "row.evaluation_status ||" in tree
    assert '{ key: "evaluation_status", label: "상태", numeric: false }' in tree
    assert 'source={(payload && payload.root) || "-"}' in records
    assert "root={(payload && payload.root)" not in records
    assert 'aria-label="연구 근거 목적지 상태"' in tree
    for state in ("complete", "partial", "missing", "conflict"):
        assert state in tree
    assert "generationRef = useRef_hct({ index: 0, detail: 0 })" in tree
    assert 'selection_generation=" + encodeURIComponent(String(selectionGeneration))' in tree
    assert "payload.research_id !== selectedId || payload.section !== section" in tree
    assert "String(payload.selection_generation) !== String(generation)" in tree
    assert "node: payload.node || null" in tree
    assert "identity.provenance_owner" in tree
    assert "identity.redaction" in tree
    assert "identity.byte_identical" in tree
    assert '["conditions", "evaluations"' in tree
    assert "const provenance = research.provenance" not in tree
    assert "_hctCompactValue" in tree

    assert "function AbPairCompareView({ baseUrl, wsStatus, selectedResearchId })" in viz
    assert "function CellHeatmap({ baseUrl, wsStatus, selectedResearchId })" in viz
    assert "function HoldoutFunnel({ baseUrl, wsStatus, selectedResearchId })" in viz
    assert "setSelected(prev => prev ||" not in viz
    assert "선택 연구 없음 · 히트맵 근거 missing" in viz
    assert "선택 연구 없음 · 홀드아웃 근거 missing" in viz
    assert "function _hvFetchJson(url, signal)" in viz
    assert "function _hvFetchAllPages(url, signal, validatePage)" in viz
    assert "_hvFetchJson(pageUrl, signal)" in viz
    assert "History detail response identity mismatch" in viz
    assert "requestsRef = useRef_hv({ pairs: null, legacy: null, typed: null })" in viz
    assert "requestsRef = useRef_hv({ campaigns: null, rows: null })" in viz
    assert "requestsRef = useRef_hv({ runs: null, rows: null })" in viz
    assert "item.legacy_research_id === selectedResearchId || item.typed_research_id === selectedResearchId" in viz
    assert 'payload.section === "evaluations"' in viz
    assert "String(payload.selection_generation) === selectionGeneration" in viz
    assert "_hvIsAbort(error, controller)" in viz
    assert "setRows([]);" in viz
