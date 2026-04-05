"""Stage 3: strategy_loader — AST 분석 + headless 인스턴스화 테스트."""
import os
import sqlite3
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.strategy_loader import (
    check_v251_compat,
    extract_function_calls,
    extract_var_refs,
    load_strategy_from_db,
    validate_strategy_code,
)


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def strategy_db(tmp_path):
    """테스트용 strategy.db (stockbuy, stocksell 테이블)."""
    db = str(tmp_path / 'strategy.db')
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE stockbuy ([index] TEXT PRIMARY KEY, 전략코드 TEXT)")
    con.execute("CREATE TABLE stocksell ([index] TEXT PRIMARY KEY, 전략코드 TEXT)")
    con.execute("INSERT INTO stockbuy VALUES ('TestBuy', '매수 = self.vars[0] > self.vars[1]')")
    con.execute("INSERT INTO stocksell VALUES ('TestSell', '매도 = self.RSI(14) > 70')")
    con.commit()
    con.close()
    return db


# ============================================================
# TestExtractVarRefs
# ============================================================

class TestExtractVarRefs:
    """extract_var_refs — self.vars[N] 인덱스 추출."""

    def test_basic_single_ref(self):
        """단일 self.vars[0] 참조를 추출한다."""
        code = '매수 = self.vars[0] > 100'
        result = extract_var_refs(code)
        assert result == [0]

    def test_multiple_refs(self):
        """여러 self.vars[N] 참조를 정렬된 고유 목록으로 반환한다."""
        code = '매수 = self.vars[0] > self.vars[2] and self.vars[1] < 50'
        result = extract_var_refs(code)
        assert result == [0, 1, 2]

    def test_duplicate_refs_deduplicated(self):
        """중복 인덱스는 한 번만 반환한다."""
        code = 'x = self.vars[3] + self.vars[3]'
        result = extract_var_refs(code)
        assert result == [3]

    def test_no_refs(self):
        """self.vars 참조가 없으면 빈 목록을 반환한다."""
        code = '매수 = True'
        result = extract_var_refs(code)
        assert result == []

    def test_syntax_error_returns_empty(self):
        """구문 오류 코드에서 빈 목록을 반환한다."""
        result = extract_var_refs('if True print()')
        assert result == []

    def test_returns_sorted_list(self):
        """반환 목록은 오름차순 정렬이어야 한다."""
        code = 'x = self.vars[5] + self.vars[1] + self.vars[3]'
        result = extract_var_refs(code)
        assert result == sorted(result)

    def test_nested_expression(self):
        """중첩 표현식 내부의 self.vars[N]도 추출한다."""
        code = '매수 = (self.vars[0] + self.vars[4]) / 2 > self.vars[2]'
        result = extract_var_refs(code)
        assert 0 in result
        assert 4 in result
        assert 2 in result


# ============================================================
# TestExtractFunctionCalls
# ============================================================

class TestExtractFunctionCalls:
    """extract_function_calls — self.메서드() 이름 추출."""

    def test_basic_call(self):
        """단일 self.RSI() 호출을 추출한다."""
        code = '매도 = self.RSI(14) > 70'
        result = extract_function_calls(code)
        assert 'RSI' in result

    def test_multiple_calls(self):
        """여러 self.메서드() 호출을 모두 추출한다."""
        code = 'x = self.이동평균(5) + self.RSI(14)'
        result = extract_function_calls(code)
        assert '이동평균' in result
        assert 'RSI' in result

    def test_no_calls(self):
        """self.메서드() 호출이 없으면 빈 목록을 반환한다."""
        code = '매수 = True'
        result = extract_function_calls(code)
        assert result == []

    def test_syntax_error_returns_empty(self):
        """구문 오류 코드에서 빈 목록을 반환한다."""
        result = extract_function_calls('if True print()')
        assert result == []

    def test_returns_list(self):
        """결과 타입은 list여야 한다."""
        result = extract_function_calls('매수 = self.MACD(12, 26)')
        assert isinstance(result, list)


# ============================================================
# TestValidateStrategyCode
# ============================================================

class TestValidateStrategyCode:
    """validate_strategy_code — 종합 검증."""

    def test_valid_code_returns_ok(self):
        """유효한 코드는 status='ok'를 반환한다."""
        result = validate_strategy_code('매수 = self.vars[0] > 100')
        assert result['status'] == 'ok'

    def test_valid_code_includes_var_refs(self):
        """ok 결과에 var_refs가 포함된다."""
        result = validate_strategy_code('매수 = self.vars[0] > self.vars[1]')
        assert result['var_refs'] == [0, 1]

    def test_valid_code_includes_functions(self):
        """ok 결과에 functions가 포함된다."""
        result = validate_strategy_code('매도 = self.RSI(14) > 70')
        assert 'RSI' in result['functions']

    def test_valid_code_includes_warnings(self):
        """ok 결과에 warnings 리스트가 포함된다."""
        result = validate_strategy_code('매수 = True')
        assert 'warnings' in result
        assert isinstance(result['warnings'], list)

    def test_syntax_error_returns_error(self):
        """구문 오류 코드는 status='error'를 반환한다."""
        result = validate_strategy_code('if True print()')
        assert result['status'] == 'error'
        assert 'message' in result

    def test_empty_code_returns_error(self):
        """빈 문자열은 status='error'를 반환한다."""
        result = validate_strategy_code('')
        assert result['status'] == 'error'

    def test_error_result_has_empty_lists(self):
        """error 결과에서 var_refs, functions, warnings는 빈 목록이다."""
        result = validate_strategy_code('')
        assert result['var_refs'] == []
        assert result['functions'] == []
        assert result['warnings'] == []

    def test_deprecated_pattern_adds_warning(self):
        """deprecated 패턴이 있으면 warnings에 추가된다."""
        result = validate_strategy_code('고가미갱신지속틱수()')
        assert result['status'] == 'ok'
        assert len(result['warnings']) > 0


# ============================================================
# TestCheckV251Compat
# ============================================================

class TestCheckV251Compat:
    """check_v251_compat — V2.51 deprecated 패턴 감지."""

    def test_clean_code_no_warnings(self):
        """deprecated 패턴이 없으면 빈 목록을 반환한다."""
        result = check_v251_compat('매수 = self.vars[0] > 100')
        assert result == []

    def test_detects_고가미갱신지속틱수(self):
        result = check_v251_compat('x = 고가미갱신지속틱수()')
        assert any('고가미갱신지속틱수' in w for w in result)

    def test_detects_저가미갱신지속틱수(self):
        result = check_v251_compat('x = 저가미갱신지속틱수()')
        assert any('저가미갱신지속틱수' in w for w in result)

    def test_detects_매도수5호가잔량합(self):
        result = check_v251_compat('x = 매도수5호가잔량합()')
        assert any('매도수5호가잔량합' in w for w in result)

    def test_detects_누적초당매도수수량(self):
        result = check_v251_compat('x = 누적초당매도수수량()')
        assert any('누적초당매도수수량' in w for w in result)

    def test_detects_누적분당매도수수량(self):
        result = check_v251_compat('x = 누적분당매도수수량()')
        assert any('누적분당매도수수량' in w for w in result)

    def test_multiple_warnings(self):
        """여러 deprecated 패턴이 있으면 각각 경고를 반환한다."""
        code = '고가미갱신지속틱수() + 저가미갱신지속틱수()'
        result = check_v251_compat(code)
        assert len(result) >= 2

    def test_returns_list(self):
        """결과 타입은 list여야 한다."""
        result = check_v251_compat('매수 = True')
        assert isinstance(result, list)


# ============================================================
# TestLoadStrategyFromDb
# ============================================================

class TestLoadStrategyFromDb:
    """load_strategy_from_db — DB 읽기 + 종합 검증."""

    def test_existing_buy_strategy(self, strategy_db):
        """존재하는 매수 전략을 읽어 ok를 반환한다."""
        result = load_strategy_from_db(strategy_db, 'TestBuy', 'buy')
        assert result['status'] == 'ok'
        assert result['code'] == '매수 = self.vars[0] > self.vars[1]'
        assert result['name'] == 'TestBuy'
        assert result['type'] == 'buy'

    def test_existing_sell_strategy(self, strategy_db):
        """존재하는 매도 전략을 읽어 ok를 반환한다."""
        result = load_strategy_from_db(strategy_db, 'TestSell', 'sell')
        assert result['status'] == 'ok'
        assert 'RSI' in result['functions']

    def test_buy_strategy_var_refs(self, strategy_db):
        """매수 전략의 var_refs가 올바르게 추출된다."""
        result = load_strategy_from_db(strategy_db, 'TestBuy', 'buy')
        assert result['var_refs'] == [0, 1]

    def test_missing_strategy_returns_error(self, strategy_db):
        """존재하지 않는 전략 이름 → status='error'."""
        result = load_strategy_from_db(strategy_db, 'NonExistent', 'buy')
        assert result['status'] == 'error'
        assert 'message' in result

    def test_invalid_type_returns_error(self, strategy_db):
        """유효하지 않은 strategy_type → status='error'."""
        result = load_strategy_from_db(strategy_db, 'TestBuy', 'invalid')
        assert result['status'] == 'error'

    def test_invalid_db_path_returns_error(self):
        """존재하지 않는 DB 경로 → status='error'."""
        result = load_strategy_from_db('/nonexistent/path/strategy.db', 'TestBuy', 'buy')
        assert result['status'] == 'error'

    def test_result_has_required_keys(self, strategy_db):
        """ok 결과에 필수 키가 모두 포함된다."""
        result = load_strategy_from_db(strategy_db, 'TestBuy', 'buy')
        for key in ('status', 'code', 'name', 'type', 'var_refs', 'functions', 'warnings'):
            assert key in result, f"'{key}' 키가 결과에 없습니다."

    def test_error_result_has_meta_keys(self, strategy_db):
        """error 결과에도 name, type, var_refs, functions, warnings 키가 있다."""
        result = load_strategy_from_db(strategy_db, 'NonExistent', 'buy')
        for key in ('name', 'type', 'var_refs', 'functions', 'warnings'):
            assert key in result
