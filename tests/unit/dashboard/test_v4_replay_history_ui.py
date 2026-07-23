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
    replay = _read("sim-tab-root.jsx")
    assert 'if (active || status !== "playing") return;' in replay
    assert '_wsSend({ action: "pause" });' in replay


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
    assert "<ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} onSelectCampaign={onSelectCampaign} />" in source
    assert "<ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate}" in source
    assert "preferredResearchId={selResearch && selResearch.researchId}" in source
    assert "style={{" not in source
def test_history_compare_and_condition_tree_are_immediately_usable() -> None:
    history = _read("v4-history.jsx")
    compare = _read("run-compare.jsx")
    tree = _read("history-condition-tree.jsx")
    records = _read("research-records-panel.jsx")

    assert '<details className="evo-group" open' in history
    assert 'import { BtResultArea } from "./backtest-charts.jsx";' in history
    assert 'key={`${selectedAnalysis.run_id}:${selectedAnalysis.gen_no}`}' in history
    assert 'evoSource={selectedAnalysis}' in history
    assert "<_HistoryStrategyCode" in history
    assert '"/strategy_code?run="' in history
    assert history.count('className="rp-code-block"') == 2
    assert "stom_history_evo_pending" in history
    assert "stom:history-evo-select" in history
    assert "분석 닫기" in history
    assert "호환되지" in history

    assert "onSelectAnalysis" in compare
    assert "분석 보기" in compare
    assert "run-compare-viewport" in compare
    assert "run-compare-sticky-header" in compare
    assert "is-selected" in compare

    assert "history-condition-index-viewport" in tree
    assert "history-condition-sticky-header" in tree
    assert "history-condition-detail-viewport" in tree
    assert 'loadSection("stages", null);' in tree
    assert "Research ID" in tree
    assert "Series / Pair" in tree
    assert "Gate count" in tree

    assert "research-records-list-viewport" in records
    assert "research-records-selected-detail" in records
    assert "Research date" in records
    assert "Artifacts" in records


def test_history_condition_tree_uses_keyboard_operable_controls() -> None:
    tree = _read("history-condition-tree.jsx")
    css = _read("v4.css")

    assert 'className="history-condition-row-button"' in tree
    assert tree.count('className="history-condition-toggle" aria-expanded=') == 2
    assert 'className="history-condition-sort"' in tree
    assert '<tr key={row.research_id} style={{' in tree
    assert '.history-condition-toggle:focus-visible' in css
def test_history_iteration_analysis_uses_loaded_fields_and_accessible_alternatives() -> None:
    history = _read("v4-history.jsx")
    css = _read("v4.css")

    assert 'const HISTORY_RESULT_LAYOUT_KEY = "stom_v511_result_layout"' in history
    assert '["auto", "wide", "balanced", "dense"]' in history
    assert 'role="radiogroup" aria-label="History 결과 레이아웃"' in history
    assert "window.localStorage.setItem(HISTORY_RESULT_LAYOUT_KEY, mode)" in history
    assert "generation_rows: _historyGenerationRows(selection)" in history
    assert '["graded_score", "score"]' in history
    assert '["mdd", "max_drawdown"]' in history
    assert "반복 분석 사용 불가" in history
    assert "실패 사유 사용 불가" in history
    assert "점수 회귀:" in history
    assert "반복 분석 텍스트 대안" in history
    assert 'role="img" aria-label="로드된 세대 점수 추세"' in history
    assert 'role="img" aria-label="로드된 점수와 MDD 산점도"' in history
    assert ".v4-history-iteration-table" in css
    assert ".v4-history-layout-wide" in css
