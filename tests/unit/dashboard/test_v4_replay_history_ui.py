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
    assert "onSelectedResearchIdChange={selectGovernedResearch}" in source
    assert "legacy run/gen archive selection" in source
    assert "<ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} showRunCompare={false} />" in source
    assert "<ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} selectedResearchId={selectedResearchId} onSelectResearch={selectGovernedResearch} />" in source
    assert "<AuditDecisionTrace baseUrl={baseUrl} selectedResearchId={selectedResearchId} onSelectResearch={selectGovernedResearch} showDecisionLedger={false} />" in source
    assert "<VerdictPanel baseUrl={baseUrl} onNavigate={onNavigate} />" in source
    assert "style={{" in source
    assert "아카이브/Compare 탐색만 읽기 전용" in source
    assert "Append-only 결정 기록은 쓰기 예외" in source


def test_history_keeps_restricted_analysis_and_single_compare_and_decision_owners() -> None:
    history = _read("v4-history.jsx")
    records = _read("research-records-panel.jsx")
    audit = _read("v4-audit.jsx")
    lab = _read("rl-panel.jsx")

    assert "function V4History({ baseUrl, wsStatus, runId, onNavigate })" in history
    assert 'import { ResearchLabPanel } from "./rl-panel.jsx";' in history
    assert 'import { ResearchProPanel } from "./research-pro.jsx";' not in history
    assert "ResearchProPanel" not in history
    assert 'enabledTabIds={["edge", "feature", "correlation", "combos"]}' in history
    assert "showOpsStatus={false}" in history
    assert "showWorkbenchLink={false}" in history
    assert 'const analysisRunId = typeof selectedResearchId === "string" && /^loop_run:\\S+$/.test(selectedResearchId)' in history
    assert 'selectedResearchId.slice("loop_run:".length) : "";' in history
    assert 'Governed analysis run: {analysisRunId || "unavailable · loop_run:<nonempty> research selection이 필요합니다."}' in history
    assert "campaign 또는 미선택은 분석 run을 제공하지 않습니다." in history
    assert "runId={analysisRunId}" in history
    assert "Archive run context:" not in history
    assert "runId={runId}" in history
    assert '<RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />' in history
    assert history.count("RunComparePanel") == 2
    assert "function ResearchRecordsPanel({ baseUrl, wsStatus, selectedResearchId, onSelectResearch, showRunCompare = true })" in records
    assert "{showRunCompare && (" in records
    assert "<_RpRunCompare" in records
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
    assert 'role="button"' not in tree
    assert 'aria-selected={active}' not in tree
    assert '<button' in tree
    assert 'aria-pressed={active}' in tree
    assert 'typeof row.evaluation_status === "string" ? row.evaluation_status : "unknown"' in tree
    assert '{ key: "evaluation_status", label: "상태", numeric: false }' in tree
    assert "payload.root" not in records
    assert "selected.evaluation_status" not in records
    assert 'aria-label="연구 근거 목적지 상태"' in tree
    for state in ("complete", "partial", "missing", "conflict"):
        assert state in tree
    assert "generationRef = useRef_hct({ index: 0, detail: 0 })" in tree
    assert 'selection_generation=" + encodeURIComponent(String(selectionGeneration))' in tree
    assert "payload.research_id !== selectedId" in tree
    assert "payload.section !== section" in tree
    assert "String(payload.selection_generation) !== String(generation)" in tree
    assert 'typeof payload.available !== "boolean"' in tree
    assert "_hctResearchEnvelope" in tree
    assert "_hctDestinationEnvelope" in tree
    assert 'hasOwn("owner")' in tree
    assert 'hasOwn("join_key")' in tree
    assert "typeof value.owner !== \"string\"" in tree
    assert "typeof value.owner_status !== \"string\"" in tree
    assert "typeof value.join_key !== \"string\"" in tree
    assert "typeof value.join_status !== \"string\"" in tree
    assert "identity.provenance_owner" in tree
    assert "identity.redaction" in tree
    assert "identity.byte_identical.values" in tree
    assert "JSON.stringify(byteValues, null, 2)" in tree
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
    assert viz.count("requestsRef = useRef_hv({ rows: null })") == 2
    assert "campaigns: null" not in viz
    assert "runs: null" not in viz
    assert "item.legacy_research_id === selectedResearchId || item.typed_research_id === selectedResearchId" in viz
    assert 'payload.section === "evaluations"' in viz
    assert "payload.available === true" in viz
    assert "String(payload.selection_generation) === selectionGeneration" in viz
    assert "_hvIsAbort(error, controller)" in viz
    assert "History detail page ceiling exceeded" in viz
    assert "page >= MAX_PAGES" in viz
    assert 'selected.startsWith("campaign:")' in viz
    assert 'selected.startsWith("loop_run:")' in viz
    assert "CellHeatmap requires campaign:<id>" in viz
    assert "HoldoutFunnel requires loop_run:<id>" in viz
    assert "setRows([]);" in viz
    index = _read("research-index.jsx")
    assert "const requestsRef = useRef_rrp({ records: null, runs: null, detail: null });" in records
    assert "const generationRef = useRef_rrp({ records: 0, runs: 0, detail: 0 });" in records
    assert 'const baseIdentity = (isDemo ? "demo:" : "live:") + (baseUrl || "");' in records
    assert "baseIdentityRef.current !== requestBase" in records
    assert "Malformed research records response" in records
    assert "Malformed shared runs response" in records
    assert "fetchRunsShared(baseUrl, { timeoutMs: 6000, signal: controller.signal })" in records
    assert "setPayload(null);" in records
    assert "setRunList([]);" in records
    assert "localStorage.setItem" not in records
    assert 'window.location.href = "/ui/backtest";' in records

    assert "const requestsRef = useRef_rix({ index: null, detail: null });" in index
    assert "const generationRef = useRef_rix({ index: 0, detail: 0 });" in index
    assert 'const baseIdentity = (isDemo ? "demo:" : "live:") + base;' in index
    assert "baseIdentityRef.current !== requestBase" in index
    assert "Malformed research index response" in index
    assert "Malformed research index detail response" in index
    assert "setRecords([]);" in index
    assert "setErrors([]);" in index
    assert "setSelectedId(\"\");" in index
    assert "controller.abort()" in index
def test_history_detail_envelopes_fail_closed_and_preserve_unavailable_contract() -> None:
    tree = _read("history-condition-tree.jsx")
    records = _read("research-records-panel.jsx")
    viz = _read("history-viz.jsx")

    assert 'return _hctUnavailable("malformed_history_research_envelope")' in tree
    assert "History detail unavailable: {sections.research.reason}" in tree
    assert "{sections.research.conflict &&" in tree
    assert "research.available !== true" in tree
    assert 'throw new Error("Malformed history detail section envelope")' in tree
    assert "function _rrpDetailEnvelope(payload, activeCampaign)" in records
    assert 'return _rrpUnavailable("malformed_research_record_detail_envelope")' in records
    assert "Research record unavailable: {detail.reason}" in records
    assert "detail.available === true" in records
    assert "rows.find(r => r.name === activeCampaign)" not in records
    assert "payload.root" not in records
    assert "History detail page ceiling exceeded" in viz
def test_history_status_disclosures_and_ab_evidence_fail_closed() -> None:
    tree = _read("history-condition-tree.jsx")
    viz = _read("history-viz.jsx")

    for status in ("unavailable", "not_run", "partial", "unknown"):
        assert f'status === "{status}"' in tree
    assert 'className="badge ok">success</span>' in tree
    assert 'return <span className="badge err" title={row.reason || ""}>unknown:' in tree
    assert 'aria-expanded={stageOpen}' in tree
    assert 'aria-controls={"hct-stage-" + stage.stage_id}' in tree
    assert 'id={"hct-stage-" + stage.stage_id}' in tree
    assert 'aria-expanded={condOpen}' in tree
    assert 'aria-controls={"hct-condition-" + cond.condition_id}' in tree
    assert 'id={"hct-condition-" + cond.condition_id}' in tree
    assert '<div style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }} onClick={() => toggleStage' not in tree

    assert "function _hvUnavailable(reason, conflict)" in viz
    assert "payload.available !== true || !Array.isArray(payload.rows)" in viz
    assert "error.historyUnavailable = _hvUnavailable(" in viz
    assert "A/B evidence unavailable: {side.reason}" in viz
    assert "side.available === true && side.rows.length === 0" in viz
    assert "A/B evidence unavailable: ${payload.reason ||" in viz
def test_history_tree_validates_source_coverage_and_exposes_all_cursors() -> None:
    tree = _read("history-condition-tree.jsx")

    assert "function _hctCoverageSource(value)" in tree
    assert "function _hctIndexEnvelope(payload, generation)" in tree
    assert "String(payload.selection_generation) !== String(generation)" in tree
    assert "!_hctCoverageSource(payload.coverage.campaign)" in tree
    assert "!_hctCoverageSource(payload.coverage.loop_run)" in tree
    assert '(value.available === false && !value.reason)' in tree
    assert 'throw new Error("Malformed history index envelope")' in tree
    assert 'aria-label="History index source coverage"' in tree
    assert 'const state = source.available ? "available" : "unavailable";' in tree
    assert 'const reason = source.available ? "" : `: ${source.reason}`;' in tree

    assert '["complete", "partial", "missing", "conflict", "unavailable"]' in tree
    assert 'state === "unavailable" ? "err"' in tree
    assert 'const reason = value && typeof value.reason === "string" && value.reason ? `: ${value.reason}` : "";' in tree

    for section in ("stages", "conditions", "evaluations"):
        assert f'sections.{section} && sections.{section}.next_cursor' in tree
        assert f'loadSection("{section}", sections.{section}.next_cursor)' in tree
    assert 'aria-label="Load more stages"' in tree
    assert 'aria-label="Load more conditions"' in tree
def test_history_evaluation_sort_headers_are_keyboard_accessible_and_dates_are_safe() -> None:
    tree = _read("history-condition-tree.jsx")

    # Native buttons preserve focus and provide Enter/Space activation for numeric sorts.
    sort_header = tree[tree.index("aria-sort="):tree.index("</th>", tree.index("aria-sort="))]
    assert 'aria-sort={col.numeric ? (sortKey === col.key ? (sortDir === "asc" ? "ascending" : "descending") : "none") : undefined}' in sort_header
    assert "<button" in sort_header
    assert 'type="button"' in sort_header
    assert 'onClick={() => toggleSort(col.key)}' in sort_header
    assert 'onClick={() => col.numeric && toggleSort(col.key)}' not in tree

    # The index API emits ISO-8601 strings; numeric Unix epochs remain supported.
    assert 'new Date(value)' in tree
    assert 'new Date(ts * 1000)' in tree
    assert 'new Date(epoch * 1000)' in tree

    # Invalid dates render the explicit fallback rather than leaking "Invalid Date".
    assert 'return date && !Number.isNaN(date.getTime()) ? date.toLocaleString() : "-";' in tree
    assert 'new Date(Number(ts) * 1000).toLocaleString()' not in tree
