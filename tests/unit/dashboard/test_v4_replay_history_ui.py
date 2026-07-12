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
    assert "<ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} />" in source
    assert "<ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} />" in source
    assert "style={{" not in source
