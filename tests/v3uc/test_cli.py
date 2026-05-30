"""v3uc_cli.py 단위 테스트.

argparse 라우팅, subcommand 디스패치, dry-run 안전성, exit code 전파, --confirm
가드(실수 차단)를 검증한다. 실 subprocess 호출은 모두 monkeypatch로 격리.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "v3uc_cli.py"


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("v3uc_cli", str(_SCRIPT))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------- parser 라우팅 -------------------------


def test_parser_status(mod) -> None:
    args = mod.build_parser().parse_args(["status"])
    assert args.cmd == "status"


def test_parser_db_scan(mod) -> None:
    args = mod.build_parser().parse_args(["db", "scan"])
    assert args.cmd == "db"
    assert args.db_action == "scan"


def test_parser_db_migrate_requires_what(mod) -> None:
    with pytest.raises(SystemExit):
        mod.build_parser().parse_args(["db", "migrate"])  # what 필수


def test_parser_db_migrate_valid(mod) -> None:
    args = mod.build_parser().parse_args([
        "db", "migrate", "strategy", "--target", "coin", "--confirm",
    ])
    assert args.what == "strategy"
    assert args.target == "coin"
    assert args.confirm is True


def test_parser_ingest_requires_version(mod) -> None:
    with pytest.raises(SystemExit):
        mod.build_parser().parse_args(["ingest"])  # --version 필수


def test_parser_dry_run_global(mod) -> None:
    args = mod.build_parser().parse_args(["--dry-run", "status"])
    assert args.dry_run is True


# ------------------------- subcommand 디스패치 -------------------------


def test_main_status_dispatches(mod, monkeypatch, capsys, tmp_path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, *, cwd, dry=False, env_extra=None):
        calls.append(list(cmd))
        return 0

    monkeypatch.setattr(mod, "_run", fake_run)
    rc = mod.main(["--workspace", str(tmp_path), "status"])
    assert rc == 0
    # git log 2회 호출 보장 (V3U + 3U_C)
    git_calls = [c for c in calls if c[:2] == ["git", "-C"]]
    assert len(git_calls) >= 2


def test_main_db_scan_no_database_dir_returns_0(mod, monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(mod, "_run", lambda *a, **kw: 0)
    rc = mod.main(["--workspace", str(tmp_path), "db", "scan"])
    out = capsys.readouterr().out
    # _database 없음 → graceful
    assert rc == 0
    assert "없음" in out or "scan" in out.lower()


def test_main_db_migrate_blocks_without_confirm(mod, capsys, tmp_path) -> None:
    rc = mod.main(["--workspace", str(tmp_path), "db", "migrate", "all"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "--confirm" in out


def test_main_db_migrate_allows_dry_run_without_confirm(mod, monkeypatch, tmp_path) -> None:
    captured_cmds: list[list[str]] = []
    monkeypatch.setattr(mod, "_run", lambda cmd, **kw: captured_cmds.append(list(cmd)) or 0)
    # _database 디렉토리 + strategy.db 생성 (실 실행 안 하므로 빈 파일이어도 OK)
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    (db_dir / "strategy.db").touch()
    rc = mod.main([
        "--workspace", str(tmp_path), "--dry-run",
        "db", "migrate", "all",
    ])
    # --dry-run 이면 --confirm 없이도 통과
    assert rc == 0
    # 한 번 이상 _run 호출됨 (strategy + pk 도구)
    assert len(captured_cmds) >= 1


def test_main_test_subcommand(mod, monkeypatch, tmp_path, capsys) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(mod, "_run", lambda cmd, **kw: calls.append(list(cmd)) or 0)
    # V3U tests 디렉토리 위장
    v3u_tests = tmp_path / "tests" / "v3u"
    v3u_tests.mkdir(parents=True)
    rc = mod.main(["--workspace", str(tmp_path), "test"])
    assert rc == 0
    # pytest 호출 발생
    pytest_calls = [c for c in calls if "pytest" in c]
    assert pytest_calls, f"pytest 호출 없음: {calls}"


def test_main_ingest_requires_version_or_errors(mod, monkeypatch, tmp_path, capsys) -> None:
    # --version 누락 시 argparse가 SystemExit
    with pytest.raises(SystemExit):
        mod.main(["ingest"])


def test_main_ingest_dispatches_with_version(mod, monkeypatch, tmp_path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(mod, "_run", lambda cmd, **kw: calls.append(list(cmd)) or 0)
    rc = mod.main([
        "--workspace", str(tmp_path),
        "ingest", "--version", "V3.99", "--dry-run",
    ])
    assert rc == 0
    # v3uc_ingest_pipeline.py 호출 + --version V3.99 + --dry-run 전파
    assert any("v3uc_ingest_pipeline.py" in c for cmd in calls for c in cmd)
    assert any("V3.99" in c for cmd in calls for c in cmd)
    assert any("--dry-run" in c for cmd in calls for c in cmd)


def test_main_gui_missing_stom_returns_2(mod, tmp_path, capsys) -> None:
    rc = mod.main(["--workspace", str(tmp_path), "gui"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "stom.py 미발견" in out


def test_main_gui_offscreen_sets_env(mod, monkeypatch, tmp_path) -> None:
    (tmp_path / "stom.py").touch()
    captured_env: dict[str, str] = {}

    def fake_run(cmd, *, cwd, dry=False, env_extra=None):
        if env_extra:
            captured_env.update(env_extra)
        return 0

    monkeypatch.setattr(mod, "_run", fake_run)
    rc = mod.main(["--workspace", str(tmp_path), "gui", "--offscreen"])
    assert rc == 0
    assert captured_env.get("QT_QPA_PLATFORM") == "offscreen"


def test_main_verify_missing_script_returns_2(mod, tmp_path, capsys, monkeypatch) -> None:
    # 3U_C 자체 verify_v3u_pyd_gui_contract.py 파일을 임시로 보이지 않게 만들지 않는다
    # (실제 보존되어야 하므로). 대신 workspace에 verifier 없음 + 3U_C에도 없는 상황 시뮬을 위해
    # _resolve_script가 가짜 경로 반환하도록 monkeypatch
    monkeypatch.setattr(mod, "_resolve_script", lambda n: tmp_path / "nonexistent" / n)
    rc = mod.main(["--workspace", str(tmp_path), "verify"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "미발견" in out
