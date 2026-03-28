"""US-008: formula 서브커맨드 JSON 출력 통일 테스트."""
import subprocess
import sys
import os
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable


class TestFormulaListJson:
    def test_list_returns_json_array(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'formula', 'list'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

class TestFormulaTestJson:
    def test_test_valid_code_returns_json(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'formula', 'test', 'x = 1 + 2'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert 'status' in data

    def test_test_invalid_code_returns_json_error(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'formula', 'test', 'def ((('],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert data['status'] == 'error'


class TestFormulaAddDeleteJson:
    def test_add_returns_json(self):
        """formula add는 성공/실패 모두 JSON을 반환한다."""
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'formula', 'add', '__test_cli_temp__',
             '--code', 'x=1'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert 'status' in data  # ok 또는 error (DB 스키마 인코딩 이슈 가능)

        if data['status'] == 'ok':
            # cleanup
            subprocess.run(
                [PYTHON, STOM_BACKTEST, 'formula', 'delete', '__test_cli_temp__'],
                capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)

    def test_delete_returns_json(self):
        """formula delete는 JSON을 반환한다."""
        # add first
        subprocess.run(
            [PYTHON, STOM_BACKTEST, 'formula', 'add', '__test_cli_del__',
             '--code', 'x = 1'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        # delete
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'formula', 'delete', '__test_cli_del__'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT)
        data = json.loads(result.stdout)
        assert 'status' in data
