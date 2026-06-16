"""P3 통합 계약 테스트 — 공유 tick/format 헬퍼를 빌드 번들(format.ts→stom-ui.js) 단일 출처로 이전.

ralplan 계획 P3(2026-06-14). 순수 Python(소스 grep) — node/esbuild 비의존(P0.5 skip 클러스터 밖).

범위(field-diff 게이트 통과분만):
  · _btAxisTicks(backtest-charts) → window._axisTicks 별칭(번들 _axisTicks 와 로직 동일).
  · _simPriceTick/_slcPriceTick → window._priceTick, _simTimeLabel/_slcTimeLabel → window._hmsTimeLabel
    (슈퍼셋 가드 = sim-live-chart 판본). 픽셀 중립(유한/비널 실데이터 동일).
  · 번들(stom-ui.js)·format.ts 가 새 헬퍼를 노출, 소비 .jsx 는 별칭만.

field-diff 로 이연/제외(이 PR 범위 아님 — Design Pass 픽셀 재베이스라인 필요 또는 비-중복):
  · Hall of Fame(HallOfFamePanel vs _RpHallOfFame): 컬럼·CSS·기능(정렬/필터/갤러리 vs 펼침/워크벤치)
    이 본질적으로 달라 병합 시 렌더 변경 → 이연.
  · process-flow PIPELINE(_RL_PIPELINE vs RP_PIPELINE): 7단계 교육 문구가 전부 달라 단일화 시 표시
    문구 변경(콘텐츠/픽셀) → 계획의 "if equal hoist" 조건 불충족 → 이연.
  · freeze_verdict 요약(_ValidationPanel vs VerdictPanel): fontSize/색/고유블록(OOS-CI vs walkforward)
    이 달라 단일 스타일 강제 시 픽셀 변경 → 이연.
  · _btMoneyTick 계열: 만단위 반올림/로케일이 달라(toFixed vs Math.round) 리터럴 중복 아님 → 제외.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"
WEBUI_BUILD = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "webui-build"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _readf(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# ============================================================ 번들 단일 출처
class TestSharedHelpersInBundle:
    def test_format_ts_exports_new_helpers(self) -> None:
        fmt = _read(WEBUI_BUILD / "src" / "format.ts")
        assert "export function _priceTick(" in fmt
        assert "export function _hmsTimeLabel(" in fmt
        # window 노출에 포함.
        assert "_priceTick" in fmt and "_hmsTimeLabel" in fmt
        tail = fmt[fmt.rfind("Object.assign(window"):]
        assert "_priceTick" in tail and "_hmsTimeLabel" in tail

    def test_bundle_exposes_new_helpers(self) -> None:
        """stom-ui.js(빌드 산출물)에 새 헬퍼가 노출됨 — 재빌드 필요(누락 시 전역 미정의)."""
        bundle = _read(FRONTEND / "bundle" / "stom-ui.js")
        assert "_priceTick" in bundle, "번들에 _priceTick 미노출 — 재빌드 필요."
        assert "_hmsTimeLabel" in bundle, "번들에 _hmsTimeLabel 미노출 — 재빌드 필요."


# ============================================================ 소비처 별칭(중복 제거)
class TestConsumersAliasNotRedefine:
    def test_bt_axisticks_deduped(self) -> None:
        # P5.1 분해 — _btAxisTicks 별칭은 backtest-charts.jsx(배럴)에서 bt-chart-utils.jsx 로 이동.
        src = _readf("bt-chart-utils.jsx")
        assert "function _btAxisTicks(" not in src, "bt-chart-utils 에 _btAxisTicks 정의 잔존(de-dup 위반)."
        assert "const _btAxisTicks = window._axisTicks" in src

    def test_sim_charts_tick_helpers_deduped(self) -> None:
        # P5.3 분해 — _simPriceTick/_simTimeLabel 별칭은 simulation-charts.jsx(배럴)에서 sim-chart-utils.jsx 로 이동.
        src = _readf("sim-chart-utils.jsx")
        assert "function _simPriceTick(" not in src
        assert "function _simTimeLabel(" not in src
        assert "const _simPriceTick = window._priceTick" in src
        assert "const _simTimeLabel = window._hmsTimeLabel" in src

    def test_sim_live_chart_tick_helpers_deduped(self) -> None:
        src = _readf("sim-live-chart.jsx")
        assert "function _slcPriceTick(" not in src
        assert "function _slcTimeLabel(" not in src
        assert "const _slcPriceTick = window._priceTick" in src
        assert "const _slcTimeLabel = window._hmsTimeLabel" in src

    def test_no_bare_duplicate_tick_function_defs_remain(self) -> None:
        """이전된 헬퍼의 bare function 정의가 어느 .jsx 에도 남아있지 않다(단일 출처)."""
        names = ("_btAxisTicks", "_simPriceTick", "_simTimeLabel", "_slcPriceTick", "_slcTimeLabel")
        for f in FRONTEND.glob("*.jsx"):
            src = f.read_text(encoding="utf-8")
            for nm in names:
                assert f"function {nm}(" not in src, f"{f.name} 에 function {nm}( 잔존(de-dup 위반)."


# ============================================================ field-diff 이연 회귀 가드
class TestDeferredConsolidationsUntouched:
    """이연 대상은 P3 에서 손대지 않는다(병합이 픽셀/콘텐츠를 바꾸므로 Design Pass 로 이연)."""

    def test_hall_of_fame_components_still_separate(self) -> None:
        # P5.4: chart.jsx(1,742줄) 분해로 HallOfFamePanel 은 chart-hall-of-fame.jsx 로
        #   이동(byte-identical, field-diff DEFER 결정 유지). 두 컴포넌트가 여전히 별개로
        #   존재(병합 안 됨)한다는 불변식은 그대로 — 단지 정의 파일만 옮겨졌다.
        assert "function HallOfFamePanel(" in _readf("chart-hall-of-fame.jsx")
        # P5.7: research-pro.jsx(1,045줄) 분해로 _RpHallOfFame 은 rp-heatmap.jsx 로 이동
        #   (별개 유지 불변식 그대로 — 정의 파일만 옮겨졌다).
        assert "function _RpHallOfFame(" in _readf("rp-heatmap.jsx")

    def test_pipeline_consolidated_to_format_ts(self) -> None:
        # 프로그램 P4(2026-06-14): PIPELINE 이연 해소 — _RL_PIPELINE/RP_PIPELINE 로컬 사본 삭제,
        #   format.ts 의 정본 window.STOM_PIPELINE 단일 출처로 통합(field-diff: RP 가 RL 슈퍼셋).
        fmt = _read(WEBUI_BUILD / "src" / "format.ts")
        assert "export const STOM_PIPELINE" in fmt
        assert "STOM_PIPELINE" in fmt[fmt.rfind("Object.assign(window"):]   # window 노출.
        # 로컬 사본 최상위 선언 제거(중복 출처 0). P5.6 분해: 프로세스 오버레이는 rl-panel.jsx 로,
        #   P5.7 분해: research-pro 의 오버레이는 rp-heatmap.jsx 로 이동.
        assert "const _RL_PIPELINE = [" not in _readf("rl-panel.jsx")
        assert "const RP_PIPELINE = [" not in _readf("rp-heatmap.jsx")
        # 두 소비처가 정본을 참조(research-lab 의 PIPELINE 소비는 rl-panel.jsx, research-pro 는 rp-heatmap.jsx).
        assert "window.STOM_PIPELINE" in _readf("rl-panel.jsx")
        assert "window.STOM_PIPELINE" in _readf("rp-heatmap.jsx")
