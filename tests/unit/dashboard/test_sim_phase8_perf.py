"""Phase8 — 라이브 차트 rAF 성능 계약(소스). 사용자 신고: 시뮬 진행 시 컴퓨터 전체 랙.

원인: SimLiveChart 의 rAF 루프가 애니메이션/가시성과 무관하게 60fps 로 캔버스 전체를
영구 재드로우 — live 가 기본 엔진(최대 10개) + Phase6.1 keep-alive(다른 탭 전환 시 언마운트
없이 display:none) 조합으로, 숨겨진 시뮬 탭의 차트들이 영구히 60fps 재드로우 → 전체 랙.

수정 계약(이 테스트가 박제):
  - 가시성 게이트: wrap.offsetParent 가 없으면(숨김) 그리지 않는다.
  - 더티 게이트: dirty(데이터/지표/hover/리사이즈) 또는 진행 중 애니메이션일 때만 그린다.
  - 프레임레이트 캡: _SLC_MIN_FRAME_MS 간격 미만이면 스킵.
  - 변경 지점들이 markDirty() 로 더티를 표시한다.
실측 증거(런 로그): 재생@240x ≈26 redraws/s(35fps 캡 이하), 숨김 0 redraws/s.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _src() -> str:
    return (FRONTEND / "sim-live-chart.jsx").read_text(encoding="utf-8")


def test_raf_visibility_gate_on_offset_parent():
    """숨김(다른 탭 keep-alive display:none) 시 offsetParent 가 null → 재드로우 스킵."""
    src = _src()
    assert "offsetParent" in src, "가시성 게이트(offsetParent) 부재 — 숨김 시 영구 재드로우 위험"


def test_raf_dirty_and_animation_gated():
    """더티/애니메이션 게이트 — 유휴 시 재드로우 0."""
    src = _src()
    assert "dirtyRef" in src
    assert "markDirty" in src
    # 유휴 조기 반환(더티도 애니도 아니면 그리지 않음).
    assert "!dirtyRef.current && !animating" in src


def test_raf_frame_rate_cap_present():
    """프레임레이트 캡(_SLC_MIN_FRAME_MS) — 다수 차트 활성 재생 CPU 포화 방지."""
    src = _src()
    assert "_SLC_MIN_FRAME_MS" in src
    assert "lastDrawTs" in src


def test_dirty_marked_on_data_indicator_hover_resize():
    """변경 지점이 더티를 표시 — bars/indicators/hover/리사이즈."""
    src = _src()
    # 데이터 배치·지표 토글·hover·리사이즈에서 markDirty 호출.
    assert "markDirty();   // 새 배치" in src or "markDirty();" in src
    assert "ResizeObserver" in src
    assert "markDirty()" in src


def test_phase4_render_budget_is_render_only_and_preserves_full_store():
    utils = (FRONTEND / "sim-tab-utils.jsx").read_text(encoding="utf-8")
    root = (FRONTEND / "sim-tab-root.jsx").read_text(encoding="utf-8")

    assert "function _simRenderBudget" in utils
    assert "function _simRenderBars" in utils
    assert "return arr.length > n ? arr.slice(arr.length - n) : arr" in utils

    assert "const barsByCode = useMemo_sim(() => ({ ...barsRef.current }), [barsVersion]);" in root
    assert "renderBarsByCode" in root
    assert "barsByCode={renderBarsByCode}" in root
    assert "const fullBars = barsByCode[code] || [];" in root
    assert "bars: renderedBars" in root
    assert "fullBarCount: fullBars.length" in root
    assert "SimIndicatorTable codes={codes} barsByCode={barsByCode}" in root
    assert "SimVariableWatch codes={codes} barsByCode={barsByCode}" in root
    assert "signalErr" in root
    assert "신호 로드 실패" in root
    assert "리플레이 프레임 해석 실패" in root
    assert "리플레이 프로토콜 오류" in root
