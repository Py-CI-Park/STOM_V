"""Phase14.1 — 정식 빌드 하네스(Vite lib) + 코이그지스턴스 회귀 가드.

검증 대상:
  - frontend/bundle/stom-ui.js: Vite lib 번들이 커밋되어 있고(런타임 npm-free),
    window.fmt* 공개 이름과 핵심 로직(U+2212 부호·ko-KR 로케일·STATUS_KR 한글)을 담는다.
  - index.html: 위 번들을 ESM 모듈(type="module")로 로드한다(운영 경로 진입).
  - 코이그지스턴스 락스텝: 14.1 동안 connection.jsx(babel 폴백)와 webui-build/src/format.mjs
    (빌드 소스)는 동일 포매터 구현을 양쪽에 유지해야 한다. 어느 한쪽만 바뀌면 즉시 실패시켜
    드리프트를 막는다. de-dup(connection.jsx에서 제거)은 14.2에서 수행한다.

  주의: 번들 파일명은 14.1에서 고정(stom-ui.js, 수동 ?v= 캐시). content-hash 자동화는 14.5.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DASH = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard"
FRONTEND = DASH / "frontend"
WEBUI_BUILD = DASH / "webui-build"

# 14.1 시점 포매터 공개 계약(window 전역 + ESM export 이름).
FORMATTER_NAMES = [
    "fmtScore", "fmtPct", "fmtMoney", "fmtInt", "fmtTime",
    "STATUS_KR", "isDemoSource", "livePanelPending",
]

# connection.jsx ↔ format.mjs 양쪽에 동일하게 존재해야 하는 구현 특성 토큰(드리프트 가드).
#   함수 본문은 바이트 동일이므로 어떤 본문 토큰이든 양쪽에서 매치되어야 한다.
LOCKSTEP_TOKENS = [
    'typeof v === "number" ? v.toFixed(3)',          # fmtScore
    '.toFixed(2)}%',                                   # fmtPct
    'v > 0 ? "+" : v < 0 ? "−"',                # fmtMoney 부호(U+2212 MINUS)
    'toLocaleString("ko-KR") + "원"',            # fmtMoney 통화(원)
    'toLocaleTimeString("ko-KR", { hour12: false })', # fmtTime
    'stopping: "정지중"',                # STATUS_KR
    'wsStatus === "demo"',                            # isDemoSource
    'buy_code_partial',                              # livePanelPending
]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_bundle_artifact_committed_and_complete() -> None:
    """빌드 번들이 커밋되어 있고 window 공개 계약 + 핵심 로직을 담는다."""
    bundle = FRONTEND / "bundle" / "stom-ui.js"
    assert bundle.exists(), "frontend/bundle/stom-ui.js 가 없습니다(빌드 산출물 커밋 필요)."
    src = _read(bundle)
    # 공개 이름 전수 노출(Object.assign(window, {...})).
    for name in FORMATTER_NAMES:
        assert name in src, f"번들에 {name} 노출이 없습니다."
    # 핵심 로직 보존(미니파이돼도 리터럴은 유지).
    assert "Object.assign" in src and "window" in src, "window 전역 세팅 부작용이 사라졌습니다."
    assert "ko-KR" in src, "ko-KR 로케일이 사라졌습니다."
    assert "−" in src, "fmtMoney 음수 부호(U+2212)가 사라졌습니다."
    assert "정지중" in src, "STATUS_KR 한글(정지중)이 사라졌습니다."
    # 번들 신선도(부분 가드): 미니파이돼도 보존되는 메서드명/속성명으로 각 포매터 존재 확인.
    #   format.mjs 를 고치고 재빌드를 깜빡한 stale 번들을 일부 잡는다(완전 자동화는 14.5 content-hash).
    assert "toLocaleTimeString" in src, "fmtTime(번들)이 누락됐습니다 — 재빌드 필요."
    assert "toFixed" in src, "fmtScore/fmtPct(번들)이 누락됐습니다 — 재빌드 필요."
    assert "buy_code_partial" in src, "livePanelPending(번들)이 누락됐습니다 — 재빌드 필요."


def test_index_html_loads_bundle_as_module() -> None:
    """index.html 이 번들을 ESM 모듈로 로드해 운영 경로에 진입시킨다."""
    html = _read(FRONTEND / "index.html")
    assert 'type="module"' in html, "index.html 에 ESM 모듈 스크립트가 없습니다."
    assert "bundle/stom-ui.js" in html, "index.html 이 bundle/stom-ui.js 를 로드하지 않습니다."
    # 폴백 양립: connection.jsx(babel)도 여전히 로드되어야 한다(14.1은 de-dup 아님).
    assert "connection.jsx" in html, "connection.jsx(babel 폴백) 로드가 사라졌습니다(14.1은 양립 유지)."


def test_formatter_lockstep_connection_vs_build_source() -> None:
    """코이그지스턴스: connection.jsx 와 webui-build/src/format.mjs 가 동일 포매터 구현을 양쪽에 유지."""
    conn = _read(FRONTEND / "connection.jsx")
    fmt = _read(WEBUI_BUILD / "src" / "format.mjs")
    for token in LOCKSTEP_TOKENS:
        assert token in conn, f"connection.jsx 에 포매터 토큰 누락: {token!r}"
        assert token in fmt, f"format.mjs 에 포매터 토큰 누락(드리프트?): {token!r}"
    # 공개 이름도 양쪽에 존재.
    for name in FORMATTER_NAMES:
        assert name in conn, f"connection.jsx 에 {name} 없음."
        assert name in fmt, f"format.mjs 에 {name} 없음."


def test_throwaway_poc_retired() -> None:
    """14.0 일회용 PoC(frontend/poc/, webui-build/index.html)는 14.1에서 폐기되었다."""
    assert not (FRONTEND / "poc").exists(), "14.0 throwaway frontend/poc/ 가 남아 있습니다."
    assert not (WEBUI_BUILD / "index.html").exists(), "14.0 PoC 페이지(webui-build/index.html)가 남아 있습니다."
