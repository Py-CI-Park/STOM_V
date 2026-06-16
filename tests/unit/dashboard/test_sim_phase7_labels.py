"""Phase7 Req 1 — 시뮬 엔진/지표/보기 라벨 가독성 계약 (WCAG 대비비, 비브라우저 오라클).

사용자 신고: 엔진/지표 라벨이 잘 안 보임. 원인 = 라벨이 `var(--ink-3)`(가장 흐린 색)·10px.
수정 = `var(--ink-1)` 11px 600. 이 테스트는 (a) 소스에서 ink-1/굵기 적용·ink-3 부재를 확인하고
(b) styles.css 토큰 hex 로 WCAG 대비비를 직접 계산해 AA(4.5:1) 통과를 검증한다(브라우저 불필요).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rel_luminance(rgb):
    def _lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(hex1: str, hex2: str) -> float:
    l1 = _rel_luminance(_hex_to_rgb(hex1))
    l2 = _rel_luminance(_hex_to_rgb(hex2))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _token_hex(css: str, name: str) -> str:
    """styles.css 의 :root(다크 테마, 첫 정의) 토큰 hex 를 읽는다."""
    m = re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})", css)
    assert m, f"token {name} not found"
    return m.group(1)


def test_sim_viewbar_labels_use_legible_ink1_not_ink3():
    """엔진/지표/보기 라벨이 var(--ink-1)·fontWeight 600 을 쓰고 var(--ink-3) 을 쓰지 않는다."""
    # P5.5 분해 — 라벨 스타일 상수(_SIM_VIEWBAR_LABEL)는 sim-tab-utils.jsx, SimViewBar 마크업은 sim-tab-controls.jsx.
    src = (FRONTEND / "sim-tab-controls.jsx").read_text(encoding="utf-8")
    # Phase7 Track B 가 도입한 라벨 스타일 상수/속성.
    assert "var(--ink-1)" in src
    # _SIM_VIEWBAR_LABEL 정의(var(--ink-1)·fontWeight:600)는 utils 에 있다.
    utils = (FRONTEND / "sim-tab-utils.jsx").read_text(encoding="utf-8")
    assert "fontWeight" in utils and "600" in utils
    # SimViewBar 라벨 묶음(엔진/지표/보기)이 한 곳에서 ink-1 스타일을 공유한다.
    assert "엔진" in src and "지표" in src and "보기" in src


def test_ink1_passes_wcag_aa_and_ink3_failed():
    """토큰 hex 로 대비비를 직접 계산 — ink-1 은 AA(4.5:1) 통과, ink-3 은 미달(수정 정당성)."""
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    bg1 = _token_hex(css, "--bg-1")
    ink1 = _token_hex(css, "--ink-1")
    ink3 = _token_hex(css, "--ink-3")
    c_ink1 = _contrast(ink1, bg1)
    c_ink3 = _contrast(ink3, bg1)
    assert c_ink1 >= 4.5, f"--ink-1 대비비 {c_ink1:.2f} < 4.5 (AA 미달)"
    # 신고 원인 박제 — 옛 라벨 색(ink-3)은 본문 대비 기준 미달이었다.
    assert c_ink3 < 4.5, f"--ink-3 대비비 {c_ink3:.2f} — 회귀 가드"
