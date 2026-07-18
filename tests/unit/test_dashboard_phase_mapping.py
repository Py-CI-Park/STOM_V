"""R8 — 대시보드 LIVE 격차(3대 갭) 프론트 구조/매핑 검증.

프론트는 브라우저 내 React+Babel(빌드 없음)이라 런타임 단위테스트가 어렵다. 대신
phase 매핑처럼 순수한 로직은 JSX에 박힌 매핑 객체(LIVE_PHASE_INDEX)를 정적으로
파싱해 **영어 backend phase → 4단계 인덱스** 정규화가 올바른지 검증하고, 활성 설정
패널/품질지표 컬럼 같은 구조 계약은 문자열 존재로 회귀를 막는다.

검증:
  - phase-detail.jsx: LIVE_PHASE_INDEX 영/한 정규화 맵(backend 영어 phase가 올바른
    4단계 인덱스로 점등) + phaseIndex 순수 함수 노출.
  - panels.jsx: ActiveConfigPanel(active_config 소비) + CurrentGenPanel 영어 phase 색.
  - table.jsx: Calmar/R²/동시보유(품질지표) 컬럼.
  - app.jsx: ActiveConfigPanel 렌더 통합.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _parse_live_phase_index(src: str) -> dict:
    """phase-detail.jsx의 LIVE_PHASE_INDEX 객체 리터럴을 {phase: int}로 파싱한다.

    JS 객체 리터럴(`const LIVE_PHASE_INDEX = { key: N, ... };`)에서 `이름: 숫자` 쌍을
    정규식으로 추출한다(주석 제거 후). 런타임 JS 없이 매핑 내용을 검증하기 위함.
    """
    start = src.find("const LIVE_PHASE_INDEX")
    assert start != -1, "LIVE_PHASE_INDEX 정의가 없습니다"
    brace_open = src.find("{", start)
    brace_close = src.find("};", brace_open)
    body = src[brace_open + 1:brace_close]
    # 라인 주석 제거.
    body = re.sub(r"//.*", "", body)
    pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(\d+)", body)
    return {k: int(v) for k, v in pairs}


class TestLivePhaseIndexMap:
    """backend 영어 phase → 4단계 인덱스 정규화 맵 검증."""

    def test_map_present_and_exposed(self):
        src = _read("phase-detail.jsx")
        assert "const LIVE_PHASE_INDEX" in src
        # phaseIndex 순수 함수 + 맵을 window에 노출(테스트/검증 공용).
        tail = src[src.rfind("Object.assign(window"):]
        assert "phaseIndex" in tail
        assert "LIVE_PHASE_INDEX" in tail

    def test_all_backend_phases_mapped_to_correct_step(self):
        # 4단계: 0생성/준비, 1백테, 2채점, 3부검·완료.
        m = _parse_live_phase_index(_read("phase-detail.jsx"))
        # 생성/준비(백테 이전) → 0.
        assert m["loop_start"] == 0
        assert m["warm_prepare_start"] == 0
        assert m["warm_prepare_done"] == 0
        assert m["ga_init"] == 0
        # 백테스트 → 1.
        assert m["backtest_start"] == 1
        assert m["ga_evaluate_start"] == 1
        # 채점(백테 종료) → 2.
        assert m["backtest_end"] == 2
        # 부검/세대 완료/전체 완료 → 3.
        assert m["generation_done"] == 3
        assert m["ga_generation_done"] == 3
        assert m["complete"] == 3

    def test_map_indices_within_four_steps(self):
        m = _parse_live_phase_index(_read("phase-detail.jsx"))
        assert m, "맵이 비어 있습니다"
        for phase, idx in m.items():
            assert 0 <= idx <= 3, f"{phase} 인덱스 {idx} 범위 밖(0..3)"

    def test_loop_publishes_only_mapped_phases(self):
        # 회귀 방지: loop.py/ga.py가 발행하는 영어 phase가 전부 맵에 있어야 LIVE
        #   타임라인이 점등된다(단계 외 stopping은 의도적으로 -1이므로 제외).
        m = _parse_live_phase_index(_read("phase-detail.jsx"))
        loop_src = (PROJECT_ROOT / "ai_strategy_loop" / "controller" / "loop.py").read_text(encoding="utf-8")
        ga_src = (PROJECT_ROOT / "ai_strategy_loop" / "controller" / "ga.py").read_text(encoding="utf-8")
        published = set(re.findall(r'phase="([a-z_]+)"', loop_src + ga_src))
        # stopping은 단계 외(미점등 의도) → 매핑 불필요.
        published.discard("stopping")
        missing = published - set(m.keys())
        assert not missing, f"맵에 없는 backend phase: {missing}"

    def test_korean_demo_phases_still_recognized(self):
        # 데모(한국어 PHASES 키)도 계속 인식해야 한다(둘 다 동작).
        src = _read("phase-detail.jsx")
        # phaseIndex가 PHASES(한국어)를 먼저 찾고, 실패 시 LIVE_PHASE_INDEX로 폴백.
        pf = src[src.find("function phaseIndex("):]
        assert "PHASES.findIndex" in pf
        assert "LIVE_PHASE_INDEX" in pf


class TestBackendPhaseStepMap:
    """backend _PHASE_STEP(5단계 ProcessFlowPanel용) — 발행 phase 전수 매핑 회귀 가드.

    프론트 LIVE_PHASE_INDEX 가드(test_loop_publishes_only_mapped_phases)와 대칭. loop.py/
    ga.py가 발행하는 영어 phase가 전부 _PHASE_STEP 키에 있어야 current_step이 점등된다.
    """

    def test_all_published_phases_in_backend_map(self):
        from ai_strategy_loop.controller.loop import _PHASE_STEP
        loop_src = (PROJECT_ROOT / "ai_strategy_loop" / "controller" / "loop.py").read_text(encoding="utf-8")
        ga_src = (PROJECT_ROOT / "ai_strategy_loop" / "controller" / "ga.py").read_text(encoding="utf-8")
        published = set(re.findall(r'phase="([a-z_]+)"', loop_src + ga_src))
        missing = published - set(_PHASE_STEP.keys())
        assert not missing, f"_PHASE_STEP에 없는 backend phase: {missing}"

    def test_backend_map_indices_within_five_steps(self):
        from ai_strategy_loop.controller.loop import _PHASE_STEP
        for phase, idx in _PHASE_STEP.items():
            assert -1 <= idx <= 4, f"{phase} 인덱스 {idx} 범위 밖(-1..4)"


class TestActiveConfigPanel:
    """R8 — 활성 설정/토글 패널(LoopState.active_config 소비) 구조 계약."""

    def test_panel_defined_and_exposed(self):
        # P5.9 분해 — 정의는 panels-config.jsx, window 재노출은 panels.jsx(배럴)이 유지.
        defn = _read("panels-config.jsx")
        assert "function ActiveConfigPanel(" in defn
        barrel = _read("panels.jsx")
        tail = barrel[barrel.rfind("Object.assign(window"):]
        assert "ActiveConfigPanel" in tail

    def test_panel_consumes_active_config(self):
        src = _read("panels-config.jsx")
        assert "active_config" in src
        # 켜진 토글 강조용 toggles 메타를 사용한다.
        acp = src[src.find("function ActiveConfigPanel("):]
        assert "toggles" in acp

    def test_app_wires_active_config_panel(self):
        src = _read("app.jsx")
        assert "<ActiveConfigPanel state={state}" in src

    def test_current_gen_panel_colors_live_phases(self):
        # CurrentGenPanel phaseColor 맵에 backend 영어 phase가 매핑돼야 한다(LIVE 색 표시).
        # P5.9 분해 — CurrentGenPanel 본문은 panels-config.jsx.
        src = _read("panels-config.jsx")
        cg = src[src.find("function CurrentGenPanel("):]
        for live_phase in ("backtest_start", "backtest_end", "generation_done", "complete"):
            assert f'"{live_phase}"' in cg, f"CurrentGenPanel 색 맵에 {live_phase} 누락"


class TestEngineProgressPanel:
    """P2 — P1 진행률/엔진 상태 계약을 프론트가 소비하는지 정적 검증."""

    def test_engine_panel_consumes_progress_and_engine_state(self):
        src = _read("engine.jsx")
        panel = src[src.find("function EnginePanel("):]

        assert "backtest_progress" in panel
        assert "engine_state" in panel
        assert "effective_engine_count" in panel
        assert "Progress Source" in panel
        assert "progress_source" in panel
        assert "timeout_deadline_epoch" in panel
        assert "bt_warm_run_timeout" in panel
        assert "counter unavailable" in panel
        assert "gen = generation" in panel
        assert 'evolutionMode === "ga"' in panel

    def test_live_pending_has_clear_label(self):
        src = _read("phase-detail.jsx")

        assert "Live data pending" in src
        assert "fresh live snapshot" in src


class TestGenerationsTableQualityColumns:
    """R8 — 세대 테이블 품질지표 컬럼(Calmar/R²/동시보유)."""

    def test_table_has_calmar_and_r2_columns(self):
        src = _read("table.jsx")
        assert ">Calmar<" in src
        assert ">R²<" in src
        # 세대 행이 g.calmar / g.uptrend_r2를 렌더해야 한다.
        assert "g.calmar" in src
        assert "g.uptrend_r2" in src

    def test_table_has_dispersion_column(self):
        src = _read("table.jsx")
        assert ">동시보유<" in src
        assert "g.max_hold_count" in src

    def test_table_flags_sparse_hold_suspicion(self):
        src = _read("table.jsx")
        assert "sparseHoldSuspicious" in src
        assert "Sparse hold warning" in src
        assert "human corridor 6-12" in src

    def test_table_colspan_matches_header_count(self):
        # 빈 행 colSpan이 헤더 th 개수와 일치해야 한다(컬럼 추가 시 회귀 방지).
        src = _read("table.jsx")
        thead = src[src.find("<thead>"):src.find("</thead>")]
        # `<th ` / `<th>` 만 센다(`<thead>` 태그가 substring으로 끼지 않도록 정규식 경계).
        th_count = len(re.findall(r"<th[\s>]", thead))
        m = re.search(r'colSpan="(\d+)"', src)
        assert m is not None, "colSpan 없음"
        assert int(m.group(1)) == th_count, \
            f"colSpan {m.group(1)} != th 개수 {th_count}"


def test_phase_timeline_surfaces_failure_stop_and_block_states():
    """UXR-P5 — PhaseTimeline이 error/blocked/stopping/complete를 은폐하지 않고 명시(§10-9)."""
    src = _read("phase-detail.jsx")
    start = src.find("function PhaseTimeline(")
    assert start != -1, "PhaseTimeline 정의가 없습니다"
    end = src.find("PHASE DETAIL PANEL", start)
    body = src[start:end if end != -1 else start + 4000]
    # 상태 판별(running 외 error/blocked/stopping 을 명시적으로 다룬다).
    for token in ('"error"', '"blocked"', '"stopping"'):
        assert token in body, f"PhaseTimeline이 {token} 상태를 다루지 않습니다"
    # 실패 단계 표시 + 사유 배너 + 상태 라벨.
    assert "failedIdx" in body, "실패 단계 인덱스(failedIdx) 처리 없음"
    assert "isFailed" in body, "단계 실패 표시(isFailed) 없음"
    assert "phase-status-banner" in body, "사유 배너(phase-status-banner) 없음"
    for label in ("실패 · 중단됨", "차단됨", "정지 중"):
        assert label in body, f"상태 라벨 누락: {label}"
def test_v5_live_situation_mapping_runtime_covers_terminal_and_reconnect_states():
    """V5.1 sealed mapping uses phase/current_step/status without publisher-side changes."""
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        return
    src = _read("v4-research.jsx")
    start = src.index("const V4_LIVE_STEP_KEYS")
    end = src.index("function _v4EvidenceState", start)
    helper = src[start:end]
    script = """
const map = new Function(process.argv[2] + '; return v4LiveSituation;')();
const summary = state => map(state).steps.map(step => step.state);
console.log(JSON.stringify({
  idle: summary({ status: 'idle', latest: {} }),
  running: summary({ status: 'running', latest: { phase: 'backtest_start', step_timings: { generate: 1 } } }),
  complete: summary({ status: 'complete', latest: { phase: 'complete' } }),
  completeActive: map({ status: 'complete', latest: { phase: 'generate_start' } }).active,
  stopping: summary({ status: 'stopping', latest: { phase: 'backtest_start' } }),
  error: summary({ status: 'error', latest: { phase: 'score_start', error: 'bad' } }),
  legacy: map({ status: 'running', latest: {} }).legacy,
  reconnect: summary({ status: 'reconnecting', latest: { current_step: 1 } }),
  completeWithError: summary({ status: 'error', latest: { phase: 'complete' } }),
  completeWithStopping: summary({ status: 'stopping', latest: { phase: 'complete' } }),
  completedStepWithReconnect: summary({ status: 'reconnecting', latest: { current_step: 4 } }),
  latestFailureOverridesStateComplete: summary({ status: 'complete', latest: { status: 'failed', phase: 'complete' } }),
}));
"""
    result = subprocess.run([node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "idle": ["pending", "pending", "pending", "pending"],
        "running": ["success", "active", "pending", "pending"],
        "complete": ["success", "success", "success", "success"],
        "completeActive": 3,
        "stopping": ["success", "retry", "pending", "pending"],
        "error": ["success", "success", "failure", "pending"],
        "legacy": True,
        "reconnect": ["success", "retry", "pending", "pending"],
        "completeWithError": ["success", "success", "success", "failure"],
        "completeWithStopping": ["success", "success", "success", "retry"],
        "completedStepWithReconnect": ["success", "success", "success", "retry"],
        "latestFailureOverridesStateComplete": ["success", "success", "success", "failure"],
    }


def test_v5_live_mapping_seals_required_existing_fields():
    src = _read("v4-research.jsx")
    mapper = src[src.index("function v4LiveSituation"):src.index("function _v4EvidenceState")]
    for field in ("latest.phase", "current_step", "phase_started_at", "step_timings", "backtest_progress", "engine_state"):
        assert field in mapper or field in src, f"sealed mapping/board misses {field}"
