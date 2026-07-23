from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[3] / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


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
    assert 'method: "POST"' not in settings
    assert "new WebSocket" not in settings
    assert "localStorage.setItem" not in settings
