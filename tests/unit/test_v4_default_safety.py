"""V4 기본(/ui) 안전·경계 계약 — 검토 §3.2.

기본 사용자 화면을 V4 graph-first 로 승격했으므로, legacy 보존 검증과 별개로
V4 정본 런타임의 안전 경계(실거래/브로커 없음, HUMAN GATE, append-only 감사)와
금지 자동호출 DOM 부재를 정본 셸·번들에서 직접 단정한다.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit.security_test_client import authorized_dashboard_client

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "ai_strategy_loop" / "dashboard" / "frontend"


def _client():
    from ai_strategy_loop.dashboard.app import create_app

    return authorized_dashboard_client(create_app())


def test_ui_default_serves_v4_shell_bundle() -> None:
    # d84012e3 — 정본 진입점은 / 하나로 통합됐다. 구 주소(/ui/)는 아래 테스트에서
    #   쿼리 보존 307 로 따로 단언한다(북마크 보존 계약).
    client = _client()
    for path in ["/", "/ui/evolution", "/ui/backtest"]:
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 200, path
        assert r.headers["x-stom-dashboard-version"] == "v4-ops", path
        assert "/ui/bundle/app.js" in r.text, path


def test_legacy_ui_entry_redirects_to_canonical_root() -> None:
    """구 진입점 보존 계약 — /ui/ 는 쿼리를 보존한 채 / 로 307."""
    client = _client()
    r = client.get("/ui/?tab=backtest", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"].startswith("/")
    assert "tab=backtest" in r.headers["location"]


def test_v4_shell_declares_safety_boundary_strip() -> None:
    # V4 정본 셸 소스에 안전 경계 strip 이 선언돼 있어야 한다.
    src = (FRONTEND / "dashboard-v4-shell.jsx").read_text(encoding="utf-8")
    for marker in ("실거래 없음", "브로커 없음", "HUMAN GATE", "APPEND-ONLY 감사"):
        assert marker in src, marker


def test_v4_bundle_carries_safety_markers() -> None:
    # esbuild 는 한글을 \uXXXX 로 escape 하므로 번들에서는 ASCII 마커로 확인한다.
    bundle = (FRONTEND / "bundle" / "app.js").read_text(encoding="utf-8")
    assert "HUMAN GATE" in bundle
    assert "v4-sfx" in bundle


def test_v4_tree_has_no_forbidden_auto_invocation_dom() -> None:
    # V4 셸·탭·번들 어디에도 자동 실행되는 실거래/브로커/계좌 액션 DOM 이 없어야 한다.
    forbidden = ('data-action="live-order"', 'data-action="broker-login"', 'data-action="account-trade"')
    targets = list(FRONTEND.glob("v4-*.jsx")) + [
        FRONTEND / "dashboard-v4-shell.jsx",
        FRONTEND / "bundle" / "app.js",
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"{path.name}: {marker}"


def test_v4_default_html_is_no_store() -> None:
    # 정본 셸 HTML 은 stale 셸 방지를 위해 no-store 여야 한다(§3.4 와 정합).
    client = _client()
    r = client.get("/ui/", follow_redirects=False)
    assert "no-store" in r.headers.get("cache-control", "")
