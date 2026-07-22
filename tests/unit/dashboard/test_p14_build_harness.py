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
    fmt = _read(WEBUI_BUILD / "src" / "format.ts")
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
    fmt = _read(WEBUI_BUILD / "src" / "format.ts")
    for token in DUAL_TOKENS:
        assert token in conn, f"connection.jsx 에 판정함수 토큰 누락: {token!r}"
        assert token in fmt, f"format.mjs 에 판정함수 토큰 누락(드리프트?): {token!r}"


def test_chart_axisticks_dedup_to_bundle() -> None:
    """14.3: chart 패밀리 순수 헬퍼 _axisTicks 가 빌드 번들 단일 출처로 이전됨.
    P5.4: chart.jsx(1,742줄)는 chart-primitives/chart-equity/chart-backtest-detail/
    chart-hall-of-fame + 배럴로 분해됨. _axisTicks 를 실제 쓰는 차트(ProfitChart·
    BacktestDetailChart)는 chart-equity·chart-backtest-detail 로 이동했으므로 window
    별칭도 그 sub-file 에 산다. de-dup 불변식(정의 없음 + window 별칭 사용)은 유지."""
    chart_family = (
        "chart.jsx", "chart-primitives.jsx", "chart-equity.jsx",
        "chart-backtest-detail.jsx", "chart-hall-of-fame.jsx",
    )
    fmt = _read(WEBUI_BUILD / "src" / "format.ts")
    bundle = _read(FRONTEND / "bundle" / "stom-ui.js")
    # 정의는 format.mjs(정본)·번들에만, chart 패밀리에서는 제거 + window 별칭.
    assert "export function _axisTicks" in fmt, "format.mjs(정본)에 _axisTicks 없음."
    assert "_axisTicks" in bundle, "번들에 _axisTicks 노출 없음 — 재빌드 필요."
    srcs = {name: _read(FRONTEND / name) for name in chart_family}
    for name, src in srcs.items():
        assert "function _axisTicks(" not in src, f"{name} 에 _axisTicks 정의가 남아있음(de-dup 위반)."
    # window 별칭은 _axisTicks 를 실제 쓰는 sub-file(들)에 존재해야 한다.
    alias = "const _axisTicks = window._axisTicks"
    assert any(alias in src for src in srcs.values()), \
        "chart 패밀리 어디에도 _axisTicks window 별칭이 없음."


def test_all_entrypoints_loading_deduped_jsx_also_load_bundle() -> None:
    """de-dup 후 connection.jsx/chart.jsx(+P3: backtest-charts/simulation-charts/sim-live-chart)는
    번들 전역(window.fmt*·_axisTicks·_priceTick·_hmsTimeLabel)에 의존한다. 그 .jsx 를 로드하는
    모든 HTML 엔트리는 bundle/stom-ui.js 도 로드해야 한다(누락 시 전역 미정의)."""
    deduped = ("connection.jsx", "chart.jsx",
               "backtest-charts.jsx", "simulation-charts.jsx", "sim-live-chart.jsx")
    missing = []
    for html in FRONTEND.glob("*.html"):
        src = _read(html)
        if any(j in src for j in deduped) and "bundle/stom-ui.js" not in src:
            missing.append(html.name)
    assert not missing, f"번들 미로드 엔트리(de-dup 전역 깨짐): {missing}"


def test_app_bundle_is_single_entry_graph() -> None:
    """PR-6 FLIP(Story 5b): 기본 빌드 모델이 esbuild bundle 로 전환됨 — bundle/app.js 는 단일
    엔트리 그래프(per-module-scope ESM)다. concat 마커가 아니라 BUNDLE 불변식으로 빌드-모델 회귀를
    가드한다. (이 가드의 보호 의도는 동일: 빌드-모델이 퇴행하면 실패해야 한다.)

    FLIP 이전(이 테스트의 옛 버전)은 26개 concat 마커(`==== X.jsx ====`)와 appSources==26 을
    단언했다. 기본=concat 이었기 때문. 이제 기본=bundle 이므로:
      - manifest model == "bundle" (concat 모델로 되돌아가면 실패)
      - app.js 에 concat 마커(`==== `)가 없다(단일 엔트리 그래프; 파일-경계 concat 아님)
      - 두 번째 React 가 번들되지 않았다(alias-to-shim, require("react")/센티넬 없음)
      - 풀 앱이다(엔트리 무결성: ReactDOM.createRoot 마운트 + 핵심 컴포넌트 존재)
    """
    manifest = json.loads((FRONTEND / "bundle" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("model") == "bundle", (
        f"빌드 모델 회귀: 기본은 bundle 이어야 함(현재 model={manifest.get('model')!r}). "
        "concat 으로 되돌아갔다면 STOM_LEGACY_CONCAT 폴백이 기본으로 새어든 것."
    )

    app_js = (FRONTEND / "bundle" / "app.js").read_text(encoding="utf-8")
    # 단일 엔트리 그래프: 파일-경계 concat 마커가 없어야 한다(있으면 concat 모델로 회귀).
    assert "==== " not in app_js, (
        "bundle/app.js 에 concat 마커(`==== `)가 있음 — 빌드가 concat 모델로 회귀했다."
    )
    # alias-to-shim 단일 React: require("react") / 두 번째 React 센티넬이 없어야 한다.
    assert 'require("react")' not in app_js, "bundle/app.js 에 require(\"react\") 존재(단일 React 위반)."
    assert "react.development" not in app_js, "bundle/app.js 에 두 번째 React 센티넬(react.development) 존재."
    assert "__SECRET_INTERNALS" not in app_js, "bundle/app.js 에 두 번째 React 복사본이 번들됨."
    # 엔트리 무결성: 풀 앱 + 마운트 코드. (concat 의 26-마커 완전성 가드를 대체.)
    assert "ReactDOM.createRoot" in app_js, "app.js 에 마운트 코드(ReactDOM.createRoot)가 없습니다."
    for sym in ("function App", "LabPage", "ProPage", "VerdictPanel", "ResearchIndexPage"):
        assert sym in app_js, f"app.js 에 핵심 컴포넌트 {sym!r} 누락(풀 앱 아님 — 재빌드 필요)."
    # manifest 가 bundle 모델 메타(엔트리 + 외부화 전역)를 기록.
    assert manifest.get("entry", "").endswith(".js"), "manifest 에 bundle entry 경로 누락."
    assert "externalizedGlobals" in manifest, "manifest 에 externalizedGlobals(react→window.React) 누락."


def test_content_hash_cache_consistency() -> None:
    """14.5: ?v= 는 content-hash(자동). 매니페스트·실제파일해시·HTML ?v= 가 모두 일치해야 한다.

    소스를 고치고 재빌드를 깜빡하면(stale 번들 또는 stale ?v=) 즉시 실패한다 → 수동 캐시 bump 폐지.
    """
    bundle = FRONTEND / "bundle"
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))

    def _h8(name: str) -> str:
        # 줄끝 정규화(CRLF→LF) 후 해시: 빌드는 LF로 산출/해시하지만 git autocrlf=true 워크트리는
        #   체크아웃 시 CRLF로 변환될 수 있다(예: wt-dev). content-hash 는 줄끝 인코딩이 아니라
        #   내용의 함수여야 하므로 정규화해 worktree 간 일관성을 보장한다(.gitattributes 가 LF 고정도 병행).
        raw = (bundle / name).read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(raw).hexdigest()[:8]

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
    v4_css_raw = (FRONTEND / "v4.css").read_bytes().replace(b"\r\n", b"\n")
    v4_css_v = hashlib.sha256(v4_css_raw).hexdigest()[:8]
    assert manifest["styles"]["v4.css"]["v"] == v4_css_v
    v4_html = _read(FRONTEND / "v4.html")
    assert f"/ui/v4.css?v={v4_css_v}" in v4_html, "v4.html v4.css ?v= 가 content-hash 와 불일치(stale)."
    # CSS is not inside the JS manifest, but every served HTML entry must carry the same explicit
    # cache pin so a styles.css edit cannot leave one route stale.
    style_pins = {}
    for entry in ("index.html", "lab.html", "pro.html", "verdict.html", "STOM AI Dashboard.html"):
        html = _read(FRONTEND / entry)
        marker = '/ui/styles.css?v='
        assert marker in html, f"{entry} styles.css cache pin missing."
        style_pins[entry] = html.split(marker, 1)[1].split('"', 1)[0]
    assert len(set(style_pins.values())) == 1, f"styles.css cache pins diverged: {style_pins}"
    # 번들을 로드하는 다른 엔트리(lab/pro)도 stom-ui ?v= 일치.
    for entry in ("lab.html", "pro.html"):
        html = _read(FRONTEND / entry)
        assert f"bundle/stom-ui.js?v={stom_v}" in html, f"{entry} stom-ui ?v= 불일치(stale)."

    # PR-6 FLIP: 기본 manifest 가 bundle 모델로 전환됨 → appSources(concat 전용) 대신 model=="bundle"
    #   single-entry-graph 메타를 단언한다. content-hash 일관성(위)은 모델 무관(두 경로 공통 post-build).
    assert manifest.get("model") == "bundle", (
        f"기본 빌드 모델은 bundle 이어야 함(현재 {manifest.get('model')!r})."
    )
    assert manifest.get("entry", "").endswith(".js"), "bundle manifest 에 entry 경로 누락."
    assert "appSources" not in manifest, (
        "bundle manifest 에 concat 전용 appSources 가 남아있음 — 빌드-모델 회귀."
    )


def test_throwaway_poc_retired() -> None:
    """14.0 일회용 PoC(frontend/poc/, webui-build/index.html)는 폐기되었다."""
    assert not (FRONTEND / "poc").exists(), "14.0 throwaway frontend/poc/ 가 남아 있습니다."
    assert not (WEBUI_BUILD / "index.html").exists(), "14.0 PoC 페이지(webui-build/index.html)가 남아 있습니다."
