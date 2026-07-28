import re
from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[3] / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _v4s_preference_keys() -> set[str]:
    """설정 탭이 스스로 선언한 허용 키(V4S_PREFERENCES)를 소스에서 읽는다.

    테스트가 목록을 따로 들고 있으면 소스와 어긋나므로, 선언을 단일 출처로 삼는다.
    """
    settings = _source("v4-settings.jsx")
    block = settings.split("const V4S_PREFERENCES = {", 1)[1].split("};", 1)[0]
    return set(re.findall(r'"([^"]+)"', block))


_V4S_ALLOWED_PREFERENCE_KEYS = (_v4s_preference_keys(),)


def test_frontend_log_ring_redacts_before_bounded_storage() -> None:
    shell = _source("dashboard-v4-shell.jsx")
    assert "const redact =" in shell
    assert "__stomFeLog" in shell
    assert "buf.length > capacity" in shell
    push_body = shell.split("const push =", 1)[1].split(";", 1)[0]
    assert "redact(" in push_body
    for marker in ("authorization", "bearer", "cookie", "api", "token"):
        assert marker in shell.lower()


def test_settings_logs_are_manual_bounded_read_only_and_exportable() -> None:
    settings = _source("v4-settings.jsx")
    assert '"/debug/logs?lines=200"' in settings
    assert "서버 로그 수동 새로고침" in settings
    assert 'value="browser"' in settings and 'value="server"' in settings
    assert "redact" in settings.lower()
    assert "navigator.clipboard" in settings
    assert "Blob" in settings
    # v5.13.2 — 설정 탭은 원칙적으로 읽기 전용이나, 사용자 지시로 GPT 로그인(POST) 이
    #   추가됐다. 허용 POST 는 gpt_auth 계열 2개뿐이며 그 외 POST 는 여전히 금지한다.
    post_targets = re.findall(r'fetch\(\(baseUrl \|\| ""\) \+ "([^"]+)",\s*\{ method: "POST"', settings)
    assert set(post_targets) <= {"/gpt_auth/login_start", "/gpt_auth/test"}, post_targets
    assert settings.count('method: "POST"') == len(post_targets)
    assert "new WebSocket" not in settings
    # v5.13.2 — "설정 탭은 저장소에 아무것도 쓰지 않는다"에서 "허용 목록 키에만 쓴다"로
    #   계약을 좁힌다. 사용자 지시로 테마·차트 높이를 설정 탭에서 고르게 됐고, 이는
    #   상단 테마 버튼이 이미 쓰던 것과 같은 클라이언트 표시 설정이다. 보호해야 할 것은
    #   '진단 로그/연구 데이터를 저장소에 남기지 않는 것'이므로 키를 직접 검사한다.
    written_keys = set(re.findall(r'localStorage\.setItem\(\s*"([^"]+)"', settings))
    allowed = {key for keys in _V4S_ALLOWED_PREFERENCE_KEYS for key in keys}
    assert written_keys <= allowed, written_keys
    # 저장은 리터럴 키로만 한다(변수 키 = 임의 키 저장 경로가 열린 것).
    assert settings.count("localStorage.setItem") == len(
        re.findall(r'localStorage\.setItem\(\s*"', settings))
def test_settings_probes_query_filter_and_scoped_layout_reset_are_source_bound() -> None:
    settings = _source("v4-settings.jsx")
    css = _source("v4.css")

    # v5.11.3 — 제목은 우리말이 정본이고 원어는 보조 표기로만 남는다.
    assert "버전 · 기능 확인" in settings
    assert "Release / Capability" in settings
    assert '"/health"' in settings
    assert "_v4sCapabilityRows(manifest, health)" in settings
    assert "기능 확인 불가" in settings
    assert "const [logQuery, setLogQuery]" in settings
    assert 'type="search"' in settings
    assert "normalizedQuery" in settings
    assert "includes(normalizedQuery)" in settings
    assert 'link.download = "stom-dashboard-redacted-logs.txt"' in settings
    assert '"stom_v511_result_layout"' in settings
    assert "resetKeys.forEach(key => window.localStorage.removeItem(key))" in settings
    assert "localStorage.clear" not in settings
    assert ".v4s-probe-grid" in css
    assert ".v4s-log-table" in css
