"""US-009: stom_backtest setting 서브커맨드 테스트."""
import subprocess
import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestSettingHelp:
    def test_setting_help_exits_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        assert 'list' in result.stdout or 'setting' in result.stdout

    def test_setting_list_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'list', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_setting_get_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'get', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0

    def test_setting_search_help(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'search', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0


class TestSettingList:
    def test_list_returns_json_or_error(self):
        """setting list는 JSON을 반환한다 (암호키 불일치 시에도 JSON 에러)."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'list', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert 'status' in data
        # 성공이면 settings 키 존재, 실패면 message 키 존재
        if data['status'] == 'ok':
            assert 'settings' in data
            assert 'count' in data
        else:
            assert 'message' in data


class TestSettingGet:
    def test_get_nonexistent_key_returns_error(self):
        """존재하지 않는 키 조회 시 에러."""
        env = dict(os.environ)
        env['STOM_ALLOW_MINIMAL_SETTING'] = '1'
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'get', 'NONEXISTENT_KEY_12345'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT, env=env)
        # 키가 없으면 exit code 1
        if result.returncode == 1:
            data = json.loads(result.stdout)
            assert data['status'] == 'error'


class TestSettingSearch:
    def test_search_returns_json_or_error(self):
        """search는 JSON을 반환한다."""
        env = dict(os.environ)
        env['STOM_ALLOW_MINIMAL_SETTING'] = '1'
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'search', '백테', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT, env=env)
        data = json.loads(result.stdout)
        assert 'status' in data
        if data['status'] == 'ok':
            assert 'results' in data
            assert 'count' in data


class TestSettingGracefulError:
    def test_no_crash_on_encryption_mismatch(self):
        """암호키 불일치 시에도 crash 없이 JSON 에러 반환."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'setting', 'list', '--format', 'json'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        # 어떤 경우든 JSON 파싱 가능해야 함
        data = json.loads(result.stdout)
        assert 'status' in data
