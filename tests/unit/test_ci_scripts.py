"""CI 스크립트 단위 테스트 — scripts/pre_commit_check.py."""

from __future__ import annotations

import os
import sys
import textwrap
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so scripts/ is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import pre_commit_check as pcc


# ===========================================================================
# TestCheckSyntax
# ===========================================================================

class TestCheckSyntax:
    """check_syntax() — 유효한 파일과 구문 오류 파일 검사."""

    def test_valid_file_returns_ok(self, tmp_path):
        """문법이 올바른 .py 파일은 status='ok'를 반환해야 한다."""
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("x = 1 + 1\n", encoding="utf-8")

        result = pcc.check_syntax([str(valid_file)])

        assert result["status"] == "ok"
        assert result["errors"] == []

    def test_syntax_error_file_returns_failed(self, tmp_path):
        """구문 오류가 있는 파일은 status='failed'와 에러 메시지를 반환해야 한다."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(\n", encoding="utf-8")

        result = pcc.check_syntax([str(bad_file)])

        assert result["status"] == "failed"
        assert len(result["errors"]) >= 1
        assert "bad.py" in result["errors"][0]

    def test_missing_file_is_skipped(self, tmp_path):
        """존재하지 않는 파일은 에러 없이 건너뛰어야 한다."""
        result = pcc.check_syntax([str(tmp_path / "nonexistent.py")])

        assert result["status"] == "ok"
        assert result["errors"] == []

    def test_multiple_files_all_valid(self, tmp_path):
        """여러 파일이 모두 유효하면 status='ok'이어야 한다."""
        files = []
        for i in range(3):
            f = tmp_path / f"mod{i}.py"
            f.write_text(f"VAR_{i} = {i}\n", encoding="utf-8")
            files.append(str(f))

        result = pcc.check_syntax(files)

        assert result["status"] == "ok"
        assert result["errors"] == []


# ===========================================================================
# TestCheckNoSecrets
# ===========================================================================

class TestCheckNoSecrets:
    """check_no_secrets() — 시크릿 없는 파일과 시크릿이 있는 파일 검사."""

    def test_clean_file_returns_ok(self, tmp_path):
        """시크릿이 없는 파일은 status='ok'를 반환해야 한다."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text(
            "import os\napi_url = 'https://example.com'\n",
            encoding="utf-8",
        )

        result = pcc.check_no_secrets([str(clean_file)])

        assert result["status"] == "ok"
        assert result["warnings"] == []

    def test_file_with_hardcoded_api_key_returns_failed(self, tmp_path):
        """하드코딩된 api_key가 있는 파일은 status='failed'를 반환해야 한다."""
        secret_file = tmp_path / "secret.py"
        secret_file.write_text(
            'api_key = "sk-abc123xyz"\n',
            encoding="utf-8",
        )

        result = pcc.check_no_secrets([str(secret_file)])

        assert result["status"] == "failed"
        assert len(result["warnings"]) >= 1

    def test_file_with_password_literal_returns_failed(self, tmp_path):
        """하드코딩된 password가 있는 파일은 경고를 반환해야 한다."""
        secret_file = tmp_path / "auth.py"
        secret_file.write_text(
            "password = 'supersecret'\n",
            encoding="utf-8",
        )

        result = pcc.check_no_secrets([str(secret_file)])

        assert result["status"] == "failed"
        assert any("password" in w.lower() or "secret" in w.lower()
                   for w in result["warnings"])

    def test_env_var_usage_is_clean(self, tmp_path):
        """os.environ을 사용하는 파일은 경고 없이 통과해야 한다."""
        env_file = tmp_path / "config.py"
        env_file.write_text(
            "import os\napi_key = os.environ.get('API_KEY')\n",
            encoding="utf-8",
        )

        result = pcc.check_no_secrets([str(env_file)])

        assert result["status"] == "ok"


# ===========================================================================
# TestCheckNoPrintDebug
# ===========================================================================

class TestCheckNoPrintDebug:
    """check_no_print_debug() — cli/ 파일 내 print() 검사."""

    def _make_cli_file(self, tmp_path, name: str, content: str) -> str:
        """cli/ 하위에 파일을 만들어 절대 경로를 반환한다."""
        cli_dir = tmp_path / "cli"
        cli_dir.mkdir(exist_ok=True)
        f = cli_dir / name
        f.write_text(content, encoding="utf-8")
        return str(f)

    def test_clean_cli_file_returns_ok(self, tmp_path):
        """print()가 없는 cli/ 파일은 status='ok'를 반환해야 한다."""
        path = self._make_cli_file(
            tmp_path, "module.py",
            "def process(x):\n    return x * 2\n",
        )

        result = pcc.check_no_print_debug([path])

        assert result["status"] == "ok"
        assert result["warnings"] == []

    def test_cli_file_with_print_returns_failed(self, tmp_path):
        """print()가 있는 cli/ 파일은 status='failed'를 반환해야 한다."""
        path = self._make_cli_file(
            tmp_path, "runner.py",
            "def run():\n    print('debug value')\n    return True\n",
        )

        result = pcc.check_no_print_debug([path])

        assert result["status"] == "failed"
        assert len(result["warnings"]) >= 1

    def test_test_file_is_excluded(self, tmp_path):
        """test_ 로 시작하는 파일의 print()는 무시되어야 한다."""
        path = self._make_cli_file(
            tmp_path, "test_runner.py",
            "def test_something():\n    print('debug in test')\n",
        )

        result = pcc.check_no_print_debug([path])

        assert result["status"] == "ok"

    def test_non_cli_file_is_excluded(self, tmp_path):
        """cli/ 경로가 아닌 파일은 검사 대상에서 제외되어야 한다."""
        other_dir = tmp_path / "utility"
        other_dir.mkdir()
        f = other_dir / "helper.py"
        f.write_text("print('utility debug')\n", encoding="utf-8")

        result = pcc.check_no_print_debug([str(f)])

        assert result["status"] == "ok"


# ===========================================================================
# TestRunQuickTests
# ===========================================================================

class TestRunQuickTests:
    """run_quick_tests() — subprocess 모킹으로 반환 형식 검증."""

    def _make_completed_process(self, returncode: int, stdout: str = "") -> MagicMock:
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = stdout
        mock.stderr = ""
        return mock

    @patch("pre_commit_check.subprocess.run")
    def test_returns_ok_when_pytest_exits_zero(self, mock_run):
        """pytest가 0으로 종료되면 status='ok'를 반환해야 한다."""
        mock_run.return_value = self._make_completed_process(
            0, "5 passed in 0.12s\n"
        )

        result = pcc.run_quick_tests()

        assert result["status"] == "ok"
        assert isinstance(result["total"], int)
        assert isinstance(result["passed"], int)
        assert isinstance(result["failed"], int)
        assert isinstance(result["duration_sec"], float)

    @patch("pre_commit_check.subprocess.run")
    def test_returns_failed_when_pytest_exits_nonzero(self, mock_run):
        """pytest가 비-0으로 종료되면 status='failed'를 반환해야 한다."""
        mock_run.return_value = self._make_completed_process(
            1, "2 passed, 1 failed in 0.30s\n"
        )

        result = pcc.run_quick_tests()

        assert result["status"] == "failed"

    @patch("pre_commit_check.subprocess.run")
    def test_result_has_required_keys(self, mock_run):
        """반환 딕셔너리는 필수 키를 모두 포함해야 한다."""
        mock_run.return_value = self._make_completed_process(0, "3 passed in 0.05s\n")

        result = pcc.run_quick_tests()

        required_keys = {"status", "total", "passed", "failed", "duration_sec"}
        assert required_keys.issubset(result.keys())

    @patch("pre_commit_check.subprocess.run")
    def test_passed_count_parsed_from_output(self, mock_run):
        """stdout에서 passed 수를 올바르게 파싱해야 한다."""
        mock_run.return_value = self._make_completed_process(
            0, "7 passed in 0.22s\n"
        )

        result = pcc.run_quick_tests()

        assert result["passed"] == 7
        assert result["failed"] == 0
        assert result["total"] == 7
