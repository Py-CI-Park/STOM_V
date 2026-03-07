"""Stage 4: 서브커맨드 통합 테스트 — formula, strategy 서브커맨드."""
import json
import os
import sys
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from cli.subcommands import create_subcommand_parser, handle_subcommand


# ============================================================
# Helpers
# ============================================================

def _make_formula_db(path):
    """테스트용 formula 테이블 생성."""
    con = sqlite3.connect(path)
    con.execute('''CREATE TABLE formula (
        수식명 TEXT, 체크유무 INTEGER, 팩터명 TEXT,
        표시형태 TEXT, 색상 TEXT, 크기 REAL, 라인타입 INTEGER, 수식코드 TEXT
    )''')
    con.execute("INSERT INTO formula VALUES ('수식A', 1, '현재가', '선:일반', 'red', 1.0, 1, 'self.line=1')")
    con.commit()
    con.close()


def _make_strategy_db(path):
    """테스트용 stockbuy/stocksell 테이블 생성."""
    con = sqlite3.connect(path)
    con.execute('''CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)''')
    con.execute("INSERT INTO stockbuy VALUES ('TestBuy', 'self.buy=1')")
    con.execute('''CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)''')
    con.execute("INSERT INTO stocksell VALUES ('TestSell', 'self.sell=1')")
    con.commit()
    con.close()


# ============================================================
# TestFormulaSubcommand
# ============================================================

class TestFormulaSubcommand:

    def test_formula_list_returns_json(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db), \
             patch('cli.formula.DB_STRATEGY', db, create=True):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['formula', 'list'])
        assert code == 0
        data = json.loads(captured[0])
        assert isinstance(data, list)
        assert data[0]['name'] == '수식A'

    def test_formula_add_ok(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['formula', 'add', '새수식', '--code', 'self.x=1'])
        assert code == 0
        data = json.loads(captured[0])
        assert data['status'] == 'ok'

    def test_formula_add_error_propagates(self, tmp_path):
        """add_formula가 error를 반환하면 exit code 1."""
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        err_result = {'status': 'error', 'message': '수식코드가 비어있습니다.'}
        with patch('cli.subcommands.DB_STRATEGY', db), \
             patch('cli.formula.add_formula', return_value=err_result) as mock_add:
            with patch('builtins.print'):
                code = handle_subcommand(['formula', 'add', '이름', '--code', ''])
        assert code == 1

    def test_formula_test_valid_code(self, tmp_path):
        captured = []
        with patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['formula', 'test', 'self.line = 1'])
        assert code == 0
        data = json.loads(captured[0])
        assert data['status'] == 'ok'

    def test_formula_test_invalid_syntax(self, tmp_path):
        captured = []
        with patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['formula', 'test', 'def (broken'])
        assert code == 1
        data = json.loads(captured[0])
        assert data['status'] == 'error'

    def test_formula_delete_existing(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['formula', 'delete', '수식A'])
        assert code == 0
        data = json.loads(captured[0])
        assert data['status'] == 'ok'

    def test_formula_delete_nonexistent_warning(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['formula', 'delete', '없는수식'])
        # warning은 status=='warning' -> ok가 아니므로 exit code 1
        assert code == 1
        data = json.loads(captured[0])
        assert data['status'] == 'warning'

    def test_formula_export_creates_file(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        out_file = str(tmp_path / 'formulas.json')
        with patch('cli.subcommands.DB_STRATEGY', db):
            with patch('builtins.print'):
                code = handle_subcommand(['formula', 'export', '--output', out_file])
        assert code == 0
        assert os.path.exists(out_file)
        with open(out_file, encoding='utf-8') as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_formula_import_from_file(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        import_data = [
            {'name': '가져온수식', 'code': 'self.x=2', 'factor': '현재가',
             'display_type': '선:일반', 'color': 'blue', 'size': 1.0, 'line_type': 1}
        ]
        in_file = str(tmp_path / 'import.json')
        with open(in_file, 'w', encoding='utf-8') as f:
            json.dump(import_data, f, ensure_ascii=False)

        captured = []
        with patch('cli.subcommands.DB_STRATEGY', db), \
             patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['formula', 'import', '--input', in_file])
        assert code == 0
        data = json.loads(captured[0])
        assert data['status'] == 'ok'
        assert data['imported'] == 1

    def test_formula_import_partial_failure_returns_nonzero(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        import_data = [
            {'name': '정상수식', 'code': 'self.x=2'},
            {'name': '실패수식', 'code': ''},
        ]
        in_file = str(tmp_path / 'partial.json')
        with open(in_file, 'w', encoding='utf-8') as f:
            json.dump(import_data, f, ensure_ascii=False)

        captured = []
        with patch('cli.subcommands.DB_STRATEGY', db), \
             patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['formula', 'import', '--input', in_file])
        assert code == 1
        data = json.loads(captured[0])
        assert data['status'] == 'partial'
        assert data['imported'] == 1
        assert len(data['failed']) == 1

    def test_formula_export_count_in_output(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_formula_db(db)
        out_file = str(tmp_path / 'out.json')
        captured = []
        with patch('cli.subcommands.DB_STRATEGY', db), \
             patch('builtins.print', side_effect=lambda s: captured.append(s)):
            handle_subcommand(['formula', 'export', '--output', out_file])
        result = json.loads(captured[0])
        assert result['count'] == 1
        assert result['path'] == out_file


# ============================================================
# TestStrategySubcommand
# ============================================================

class TestStrategySubcommand:

    def test_strategy_list_returns_json(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_strategy_db(db)
        with patch('cli.config.DB_STRATEGY', db), \
             patch('cli.subcommands.DB_STRATEGY', db):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['strategy', 'list'])
        assert code == 0
        data = json.loads(captured[0])
        assert 'stockbuy' in data
        assert 'stocksell' in data

    def test_strategy_validate_ok(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_strategy_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['strategy', 'validate', 'TestBuy', '--type', 'buy'])
        assert code == 0
        data = json.loads(captured[0])
        assert data['status'] == 'ok'
        assert data['strategy_name'] == 'TestBuy'
        assert data['strategy_type'] == 'buy'

    def test_strategy_validate_not_found(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_strategy_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            with patch('builtins.print'):
                code = handle_subcommand(['strategy', 'validate', '없는전략', '--type', 'buy'])
        assert code == 1

    def test_strategy_validate_v251_compat_flag(self, tmp_path):
        """--v251-compat 플래그가 validate_strategy에 전달된다."""
        db = str(tmp_path / 'strategy.db')
        _make_strategy_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db), \
             patch('cli.strategy.validate_strategy', return_value={'status': 'ok', 'warnings': [], 'message': 'ok'}) as mock_val:
            with patch('builtins.print'):
                handle_subcommand(['strategy', 'validate', 'TestBuy', '--type', 'buy', '--v251-compat'])
        mock_val.assert_called_once()
        _, kwargs = mock_val.call_args
        assert kwargs.get('v251_compat') is True

    def test_strategy_analyze_ok(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_strategy_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            captured = []
            with patch('builtins.print', side_effect=lambda s: captured.append(s)):
                code = handle_subcommand(['strategy', 'analyze', 'TestBuy', '--type', 'buy'])
        assert code == 0
        data = json.loads(captured[0])
        assert data['status'] == 'ok'
        assert 'var_refs' in data
        assert 'functions' in data

    def test_strategy_analyze_not_found(self, tmp_path):
        db = str(tmp_path / 'strategy.db')
        _make_strategy_db(db)
        with patch('cli.subcommands.DB_STRATEGY', db):
            with patch('builtins.print'):
                code = handle_subcommand(['strategy', 'analyze', '없는전략', '--type', 'sell'])
        assert code == 1


# ============================================================
# TestSubcommandDetection — stom_backtest.py main() routing
# ============================================================

class TestSubcommandDetection:

    def test_formula_detected_in_main(self):
        """sys.argv[1]=='formula' 이면 handle_subcommand가 호출된다."""
        with patch('sys.argv', ['stom_backtest.py', 'formula', 'list']), \
             patch('cli.subcommands.handle_subcommand', return_value=0) as mock_handler:
            import importlib
            import stom_backtest
            importlib.reload(stom_backtest)  # 모듈 재로드로 import 보장
            result = stom_backtest.main()
        mock_handler.assert_called_once_with(['formula', 'list'])
        assert result == 0

    def test_strategy_detected_in_main(self):
        """sys.argv[1]=='strategy' 이면 handle_subcommand가 호출된다."""
        with patch('sys.argv', ['stom_backtest.py', 'strategy', 'list']), \
             patch('cli.subcommands.handle_subcommand', return_value=0) as mock_handler:
            import importlib
            import stom_backtest
            result = stom_backtest.main()
        mock_handler.assert_called_once_with(['strategy', 'list'])
        assert result == 0

    def test_no_subcommand_falls_through_to_parse_args(self):
        """서브커맨드 없이 --dry-run 호출 시 기존 parse_args 경로를 통과한다."""
        with patch('sys.argv', ['stom_backtest.py', '--dry-run',
                                '--buy', 'B', '--sell', 'S',
                                '--start', '20250101', '--end', '20250131']), \
             patch('cli.config.list_strategies', return_value={'stockbuy': ['B'], 'stocksell': ['S']}), \
             patch('builtins.print'):
            import stom_backtest
            result = stom_backtest.main()
        assert result == 0  # dry_run -> EXIT_SUCCESS

    def test_no_argv_falls_through(self):
        """sys.argv에 서브커맨드가 없으면 handle_subcommand를 호출하지 않는다."""
        with patch('sys.argv', ['stom_backtest.py']), \
             patch('cli.subcommands.handle_subcommand') as mock_handler, \
             patch('cli.config.parse_args', return_value=None):
            import stom_backtest
            stom_backtest.main()
        mock_handler.assert_not_called()


# ============================================================
# TestParserStructure
# ============================================================

class TestParserStructure:

    def test_formula_list_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['formula', 'list'])
        assert parsed.command == 'formula'
        assert parsed.formula_action == 'list'

    def test_formula_add_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['formula', 'add', 'MyFormula', '--code', 'x=1'])
        assert parsed.name == 'MyFormula'
        assert parsed.code == 'x=1'
        assert parsed.factor == '현재가'
        assert parsed.size == 1.0

    def test_formula_test_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['formula', 'test', 'self.x=1'])
        assert parsed.formula_action == 'test'
        assert parsed.code == 'self.x=1'

    def test_formula_delete_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['formula', 'delete', '수식명'])
        assert parsed.formula_action == 'delete'
        assert parsed.name == '수식명'

    def test_formula_export_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['formula', 'export', '--output', 'out.json'])
        assert parsed.formula_action == 'export'
        assert parsed.output == 'out.json'

    def test_formula_import_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['formula', 'import', '--input', 'in.json'])
        assert parsed.formula_action == 'import'
        assert parsed.input_file == 'in.json'

    def test_strategy_validate_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['strategy', 'validate', 'MyBuy', '--type', 'buy', '--v251-compat'])
        assert parsed.strategy_action == 'validate'
        assert parsed.name == 'MyBuy'
        assert parsed.type == 'buy'
        assert parsed.v251_compat is True

    def test_strategy_analyze_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['strategy', 'analyze', 'MySell', '--type', 'sell'])
        assert parsed.strategy_action == 'analyze'
        assert parsed.name == 'MySell'
        assert parsed.type == 'sell'
