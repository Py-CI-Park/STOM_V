"""Phase14.1~14.2 — 정식 빌드 하네스(Vite lib) + de-dup 회귀 가드.

검증 대상:
  - frontend/bundle/stom-ui.js: Vite lib 번들이 커밋되어 있고(런타임 npm-free),
    window.fmt* 공개 이름과 핵심 로직(U+2212 부호·ko-KR 로케일·STATUS_KR 한글)을 담는다.
  - index.html: 위 번들을 ESM 모듈(type="module")로 로드한다(운영 경로 진입).
  - 14.2 de-dup: 디스플레이 포매터(fmtScore/fmtPct/fmtMoney/fmtInt/fmtTime/STATUS_KR) 구현은
    이제 빌드 번들(소스 format.mjs)이 단일 출처. connection.jsx 는 정의를 제거하고 window 별칭만
    둔다. 어느 한쪽이 어긋나면(번들에서 사라지거나 connection.jsx 에 본문이 되살아나면) 실패.
  - 판정 함수(isDemoSource/livePanelPending)는 아직 connection.jsx 정의 유지(번들도 동일 제공) —
    내부 의존 때문에 후속 단계에서 통합. 양쪽 존재를 단정한다.

  주의: 번들 파일명은 고정(stom-ui.js, 수동 ?v= 캐시). content-hash 자동화는 14.5.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DASH = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard"
FRONTEND = DASH / "frontend"
WEBUI_BUILD = DASH / "webui-build"

# 포매터 공개 계약(window 전역 + ESM export 이름).
FORMATTER_NAMES = [
    "fmtScore", "fmtPct", "fmtMoney", "fmtInt", "fmtTime",
    "STATUS_KR", "isDemoSource", "livePanelPending",
]

# 14.2 de-dup 대상 디스플레이 포매터의 구현 본문 토큰.
#   → format.mjs(정본)에는 존재, connection.jsx(소비처)에서는 제거되어야 한다.
# 토큰은 포매터 본문에만 나타나는 고유형(데모 코드 생성기 문자열과의 오탐 회피: v. 접두·: "—" 앵커).
DEDUP_BODY_TOKENS = [
    'v.toFixed(3) : "—"',                              # fmtScore
    'v.toFixed(2)}%',                                  # fmtPct
    'typeof v === "number" ? v.toLocaleString("ko-KR")',  # fmtInt(번들 정본 전용; fmtMoney는 Math.abs(v))
    'v > 0 ? "+" : v < 0 ? "−"',                 # fmtMoney 부호(U+2212 MINUS)
    'Math.abs(v).toLocaleString("ko-KR")',             # fmtMoney 통화
    'toLocaleTimeString("ko-KR", { hour12: false })',  # fmtTime
    'stopping: "정지중"',                 # STATUS_KR
]

# 아직 connection.jsx ↔ format.mjs 양쪽에 존재해야 하는 판정 함수 토큰(드리프트 가드).
DUAL_TOKENS = [
    'wsStatus === "demo"',     # isDemoSource
    'buy_code_partial',        # livePanelPending
]

# connection.jsx 가 번들 전역을 끌어쓰는 별칭(de-dup 후 본문 대신 존재해야 함).
ALIAS_TOKENS = [
    "window.fmtScore", "window.fmtPct", "window.fmtMoney",
    "window.fmtInt", "window.fmtTime", "window.STATUS_KR",
]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_bundle_artifact_committed_and_complete() -> None:
    """빌드 번들이 커밋되어 있고 window 공개 계약 + 핵심 로직을 담는다."""
    bundle = FRONTEND / "bundle" / "stom-ui.js"
    assert bundle.exists(), "frontend/bundle/stom-ui.js 가 없습니다(빌드 산출물 커밋 필요)."
    src = _read(bundle)
    for name in FORMATTER_NAMES:
        assert name in src, f"번들에 {name} 노출이 없습니다."
    assert "Object.assign" in src and "window" in src, "window 전역 세팅 부작용이 사라졌습니다."
    assert "ko-KR" in src, "ko-KR 로케일이 사라졌습니다."
    assert "−" in src, "fmtMoney 음수 부호(U+2212)가 사라졌습니다."
    assert "정지중" in src, "STATUS_KR 한글(정지중)이 사라졌습니다."
    # 번들 신선도(부분 가드): 미니파이돼도 보존되는 메서드명/속성명으로 각 포매터 존재 확인.
    assert "toLocaleTimeString" in src, "fmtTime(번들)이 누락됐습니다 — 재빌드 필요."
    assert "toFixed" in src, "fmtScore/fmtPct(번들)이 누락됐습니다 — 재빌드 필요."
    assert "buy_code_partial" in src, "livePanelPending(번들)이 누락됐습니다 — 재빌드 필요."


def test_index_html_loads_bundle_as_module() -> None:
    """index.html 이 stom-ui(ESM 모듈) + 컴파일 번들 app.js(defer)를 로드하고, 런타임 babel 은 없다(14.4)."""
    html = _read(FRONTEND / "index.html")
    assert 'type="module"' in html, "index.html 에 ESM 모듈 스크립트가 없습니다."
    assert "bundle/stom-ui.js" in html, "index.html 이 bundle/stom-ui.js 를 로드하지 않습니다."
    # Phase14.4: 운영 컴포넌트는 단일 컴파일 번들 app.js(defer)로 로드.
    assert "bundle/app.js" in html, "index.html 이 bundle/app.js 를 로드하지 않습니다."
    # 런타임 babel 제거: text/babel 스크립트도 vendor-babel 도 없어야 한다.
    assert 'type="text/babel"' not in html, "index.html 에 런타임 babel 스크립트가 남아있습니다(14.4 위반)."
    assert "vendor-babel.js" not in html, "index.html 에 vendor-babel.js 가 남아있습니다(14.4 위반)."


def test_formatter_dedup_implementation_single_source() -> None:
    """14.2 de-dup: 포매터 구현은 format.mjs(정본)에만. connection.jsx 는 본문 제거 + window 별칭."""
    conn = _read(FRONTEND / "connection.jsx")
    fmt = _read(WEBUI_BUILD / "src" / "format.mjs")
    for token in DEDUP_BODY_TOKENS:
        assert token in fmt, f"format.mjs(정본)에 포매터 본문 누락: {token!r}"
        assert token not in conn, f"connection.jsx 에 포매터 본문이 되살아났습니다(de-dup 위반): {token!r}"
    # connection.jsx 는 번들 전역 별칭으로 바인딩만 유지(bare-식별자 소비처 해소).
    for alias in ALIAS_TOKENS:
        assert alias in conn, f"connection.jsx 에 번들 별칭 누락: {alias!r}"
    # 공개 이름은 여전히 양쪽에 존재(별칭/정의 형태로).
    for name in FORMATTER_NAMES:
        assert name in conn, f"connection.jsx 에 {name} 없음."
        assert name in fmt, f"format.mjs 에 {name} 없음."


def test_judgment_fns_still_dual() -> None:
    """판정 함수(isDemoSource/livePanelPending)는 아직 connection.jsx ↔ format.mjs 양쪽 유지."""
    conn = _read(FRONTEND / "connection.jsx")
    fmt = _read(WEBUI_BUILD / "src" / "format.mjs")
    for token in DUAL_TOKENS:
        assert token in conn, f"connection.jsx 에 판정함수 토큰 누락: {token!r}"
        assert token in fmt, f"format.mjs 에 판정함수 토큰 누락(드리프트?): {token!r}"


def test_chart_axisticks_dedup_to_bundle() -> None:
    """14.3: chart.jsx 순수 헬퍼 _axisTicks 가 빌드 번들 단일 출처로 이전됨."""
    chart = _read(FRONTEND / "chart.jsx")
    fmt = _read(WEBUI_BUILD / "src" / "format.mjs")
    bundle = _read(FRONTEND / "bundle" / "stom-ui.js")
    # 정의는 format.mjs(정본)·번들에만, chart.jsx 에서는 제거 + window 별칭.
    assert "export function _axisTicks" in fmt, "format.mjs(정본)에 _axisTicks 없음."
    assert "_axisTicks" in bundle, "번들에 _axisTicks 노출 없음 — 재빌드 필요."
    assert "function _axisTicks(" not in chart, "chart.jsx 에 _axisTicks 정의가 남아있음(de-dup 위반)."
    assert "const _axisTicks = window._axisTicks" in chart, "chart.jsx 에 _axisTicks window 별칭 없음."


def test_all_entrypoints_loading_deduped_jsx_also_load_bundle() -> None:
    """de-dup 후 connection.jsx/chart.jsx 는 번들 전역(window.fmt*·_axisTicks)에 의존한다.
    그 .jsx 를 로드하는 모든 HTML 엔트리는 bundle/stom-ui.js 도 로드해야 한다(누락 시 전역 미정의)."""
    deduped = ("connection.jsx", "chart.jsx")
    missing = []
    for html in FRONTEND.glob("*.html"):
        src = _read(html)
        if any(j in src for j in deduped) and "bundle/stom-ui.js" not in src:
            missing.append(html.name)
    assert not missing, f"번들 미로드 엔트리(de-dup 전역 깨짐): {missing}"


def test_app_bundle_contains_all_ordered_sources() -> None:
    """14.4: bundle/app.js 가 build-app.mjs ORDER 의 26개 .jsx 를 전부 마커로 포함(누락/stale 가드).

    build-app.mjs 의 ORDER 배열을 직접 파싱해 산출물 app.js 와 대조한다. 새 .jsx 를 ORDER 에
    추가하고 재빌드를 깜빡하면(또는 파일 누락) 실패한다. (완전 byte 동일 검증은 14.5 content-hash.)
    """
    build_src = (WEBUI_BUILD / "build-app.mjs").read_text(encoding="utf-8")
    m = re.search(r"const ORDER = \[(.*?)\];", build_src, re.DOTALL)
    assert m, "build-app.mjs 에서 ORDER 배열을 찾지 못했습니다."
    order = re.findall(r'"([^"]+\.jsx)"', m.group(1))
    assert len(order) >= 20, f"ORDER 파싱 비정상(개수 {len(order)})."

    app_js = (FRONTEND / "bundle" / "app.js").read_text(encoding="utf-8")
    missing = [f for f in order if f"==== {f} ====" not in app_js]
    assert not missing, f"app.js 에 누락된 소스(재빌드 필요): {missing}"
    # 마지막 엔트리(app.jsx)는 ReactDOM 마운트를 포함해야 한다(엔트리 무결성).
    assert order[-1] == "app.jsx"
    assert "ReactDOM.createRoot" in app_js, "app.js 에 마운트 코드(ReactDOM.createRoot)가 없습니다."


def test_content_hash_cache_consistency() -> None:
    """14.5: ?v= 는 content-hash(자동). 매니페스트·실제파일해시·HTML ?v= 가 모두 일치해야 한다.

    소스를 고치고 재빌드를 깜빡하면(stale 번들 또는 stale ?v=) 즉시 실패한다 → 수동 캐시 bump 폐지.
    """
    bundle = FRONTEND / "bundle"
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))

    def _h8(name: str) -> str:
        return hashlib.sha256((bundle / name).read_bytes()).hexdigest()[:8]

    for name in ("app.js", "stom-ui.js"):
        actual = _h8(name)
        assert manifest["bundles"][name]["v"] == actual, (
            f"manifest {name} 해시 불일치(재빌드 필요): manifest={manifest['bundles'][name]['v']} actual={actual}"
        )

    app_v = manifest["bundles"]["app.js"]["v"]
    stom_v = manifest["bundles"]["stom-ui.js"]["v"]
    index = _read(FRONTEND / "index.html")
    assert f"bundle/app.js?v={app_v}" in index, "index.html app.js ?v= 가 content-hash 와 불일치(stale)."
    assert f"bundle/stom-ui.js?v={stom_v}" in index, "index.html stom-ui.js ?v= 가 content-hash 와 불일치(stale)."
    # 번들을 로드하는 다른 엔트리(lab/pro)도 stom-ui ?v= 일치.
    for entry in ("lab.html", "pro.html"):
        html = _read(FRONTEND / entry)
        assert f"bundle/stom-ui.js?v={stom_v}" in html, f"{entry} stom-ui ?v= 불일치(stale)."

    # 매니페스트 appSources 는 build-app.mjs ORDER 와 동일(완전성).
    assert manifest["appSources"][-1] == "app.jsx"
    assert len(manifest["appSources"]) == 26


def test_throwaway_poc_retired() -> None:
    """14.0 일회용 PoC(frontend/poc/, webui-build/index.html)는 폐기되었다."""
    assert not (FRONTEND / "poc").exists(), "14.0 throwaway frontend/poc/ 가 남아 있습니다."
    assert not (WEBUI_BUILD / "index.html").exists(), "14.0 PoC 페이지(webui-build/index.html)가 남아 있습니다."
