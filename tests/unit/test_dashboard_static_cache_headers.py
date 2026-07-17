"""정적 자산 캐시 헤더 계약.

크롬 '매 로드 느림'의 주원인이던 Cache-Control 부재를 회귀 방지한다.
지문(?v=<hash>)이 붙은 .js/.css 는 far-future immutable 캐시를, 지문 없는 요청과
.html 은 no-store 를 받아야 한다. 셸 HTML(핸들러 no-store 서빙)과 정합을 유지한다.
"""

from __future__ import annotations

from tests.unit.security_test_client import authorized_dashboard_client


def _client():
    from ai_strategy_loop.dashboard.app import create_app

    return authorized_dashboard_client(create_app())


def test_fingerprinted_bundle_is_immutable_cached() -> None:
    client = _client()
    r = client.get("/ui/bundle/app.js", params={"v": "deadbeef"})
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "immutable" in cc
    assert "max-age=31536000" in cc


def test_fingerprinted_css_is_immutable_cached() -> None:
    client = _client()
    r = client.get("/ui/styles.css", params={"v": "20260624u002"})
    assert r.status_code == 200
    assert "immutable" in r.headers.get("cache-control", "")


def test_unfingerprinted_asset_is_no_store() -> None:
    # §3.4: 지문 없는 .js 요청은 immutable 금지 + no-store 명시(내용 주소화 안 됨 → 장기 캐시 위험).
    client = _client()
    r = client.get("/ui/bundle/app.js")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "immutable" not in cc
    assert "no-store" in cc


def test_static_html_direct_fetch_is_no_store() -> None:
    # /ui/v4.html 직접 정적 요청(?v= 없음)도 no-store 로 셸 HTML 캐시 오염을 막는다.
    client = _client()
    r = client.get("/ui/v4.html")
    assert r.status_code == 200
    assert "no-store" in r.headers.get("cache-control", "")


def test_canonical_shell_html_route_is_no_store() -> None:
    # 정본 셸 라우트(/ui/)는 핸들러가 직접 no-store 로 서빙한다(캐시 시 stale 셸 위험).
    client = _client()
    r = client.get("/ui/", follow_redirects=False)
    assert r.status_code == 200
    assert "no-store" in r.headers.get("cache-control", "")
