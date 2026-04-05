"""US-402: 전략 DSL headless 평가 + 호환성 검사기 테스트."""
import json
import os
import sqlite3
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def strategy_db(tmp_path):
    """테스트용 strategy.db 생성 (stockbuy, stocksell 테이블)."""
    db_path = str(tmp_path / 'strategy.db')
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE stockbuy (`index` TEXT PRIMARY KEY, 전략코드 TEXT)")
    con.execute("CREATE TABLE stocksell (`index` TEXT PRIMARY KEY, 전략코드 TEXT)")
    con.execute("INSERT INTO stockbuy VALUES ('TestBuy', '매수 = True')")
    con.execute("INSERT INTO stocksell VALUES ('TestSell', '매도 = True')")
    con.commit()
    con.close()
    return db_path


# ============================================================
# US-402: strategy evaluate (headless 실행)
# ============================================================

class TestStrategyEvaluate:
    """strategy evaluate → headless 전략 실행."""

    def test_evaluate_returns_result_dict(self, strategy_db):
        """evaluate는 status 키가 있는 dict를 반환해야 한다."""
        from cli.strategy import evaluate_strategy
        result = evaluate_strategy(strategy_db, 'TestBuy', 'buy')
        assert isinstance(result, dict)
        assert 'status' in result

    def test_evaluate_existing_strategy(self, strategy_db):
        """존재하는 전략 → 성공 또는 코드 반환."""
        from cli.strategy import evaluate_strategy
        result = evaluate_strategy(strategy_db, 'TestBuy', 'buy')
        assert result['status'] == 'ok'
        assert 'code' in result

    def test_evaluate_nonexistent_strategy(self, strategy_db):
        """존재하지 않는 전략 → 에러."""
        from cli.strategy import evaluate_strategy
        result = evaluate_strategy(strategy_db, 'NonExistent', 'buy')
        assert result['status'] == 'error'

    def test_evaluate_sell_strategy(self, strategy_db):
        """매도 전략도 평가 가능해야 한다."""
        from cli.strategy import evaluate_strategy
        result = evaluate_strategy(strategy_db, 'TestSell', 'sell')
        assert result['status'] == 'ok'

    def test_evaluate_invalid_type(self, strategy_db):
        """유효하지 않은 전략 유형 → 에러."""
        from cli.strategy import evaluate_strategy
        result = evaluate_strategy(strategy_db, 'TestBuy', 'invalid')
        assert result['status'] == 'error'


# ============================================================
# US-402: strategy validate --v251-compat (호환성 검사)
# ============================================================

class TestStrategyValidate:
    """strategy validate → V2.51 문법 변경 감지."""

    def test_validate_clean_code(self):
        """정상 코드 → 호환성 문제 없음."""
        from cli.strategy import validate_strategy
        result = validate_strategy('매수 = True')
        assert result['status'] == 'ok'
        assert len(result.get('warnings', [])) == 0

    def test_validate_syntax_error(self):
        """구문 오류가 있는 코드 → 에러."""
        from cli.strategy import validate_strategy
        result = validate_strategy('if True print()')
        assert result['status'] == 'error'

    def test_validate_v251_deprecated_function(self):
        """V2.51에서 변경된 함수 사용 감지."""
        from cli.strategy import validate_strategy
        # 고가미갱신지속틱수() 등 V2.51에서 변경된 함수명 패턴 감지
        code = '고가미갱신지속틱수()'
        result = validate_strategy(code, v251_compat=True)
        assert len(result.get('warnings', [])) > 0

    def test_validate_empty_code(self):
        """빈 코드 → 에러."""
        from cli.strategy import validate_strategy
        result = validate_strategy('')
        assert result['status'] == 'error'

    def test_validate_returns_warnings_list(self):
        """결과에 warnings 리스트가 포함되어야 한다."""
        from cli.strategy import validate_strategy
        result = validate_strategy('매수 = True')
        assert 'warnings' in result
        assert isinstance(result['warnings'], list)
