"""strategy_generator — 전략 코드 자동 생성 모듈 테스트."""
import os
import sqlite3
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.strategy_generator import (
    create_and_save,
    delete_strategy_from_db,
    generate_buy_strategy,
    generate_buy_filter_strategy,
    generate_sell_strategy,
    save_strategy_to_db,
)
from cli.strategy_loader import validate_strategy_code


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def strategy_db(tmp_path):
    """테스트용 strategy.db (stockbuy, stocksell 테이블)."""
    db = str(tmp_path / 'strategy.db')
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.commit()
    con.close()
    return db


# ============================================================
# TestGenerateBuyStrategy
# ============================================================

class TestGenerateBuyStrategy:
    """generate_buy_strategy — 분봉 매수 전략 생성."""

    def test_generate_buy_simple(self):
        """단일 조건 매수 전략을 생성한다."""
        result = generate_buy_strategy('단순매수', ['self.vars[0] > self.vars[1]'])
        assert result['status'] == 'ok'
        assert result['name'] == '단순매수'
        assert result['type'] == 'buy'
        assert 'self.vars[0] > self.vars[1]' in result['code']

    def test_generate_buy_multiple_conditions(self):
        """다중 조건이 AND로 결합된 매수 전략을 생성한다."""
        conditions = [
            'self.vars[0] > self.vars[1]',
            'self.현재가() > 10000',
            'self.vars[2] < 80',
        ]
        result = generate_buy_strategy('복합매수', conditions)
        assert result['status'] == 'ok'
        # 세 조건이 모두 코드에 포함되어야 한다
        for cond in conditions:
            assert cond in result['code']
        # and 로 결합되어야 한다
        assert 'and' in result['code']

    def test_generate_buy_empty_conditions(self):
        """빈 조건 리스트는 에러를 반환한다."""
        result = generate_buy_strategy('빈조건', [])
        assert result['status'] == 'error'
        assert '매수 조건이 비어있습니다.' in result['message']

    def test_generate_buy_code_header(self):
        """생성된 코드에 전략 이름과 생성일 헤더가 포함된다."""
        result = generate_buy_strategy('헤더테스트', ['self.vars[0] > 0'])
        assert result['status'] == 'ok'
        assert '헤더테스트' in result['code']
        assert '생성일' in result['code']
        assert '자동 생성 분봉 매수 전략' in result['code']

    def test_generate_buy_filter_strategy_inserts_filters_before_final_buy(self):
        """기존 매수 전략의 최종 매수 실행 직전에 자동 필터가 삽입되어야 한다."""
        base_code = (
            '# 기존 전략\n'
            '매수 = True\n'
            'if 관심종목 != 1:\n'
            '    매수 = False\n'
            'if 매수:\n'
            '    self.Buy()\n'
        )
        result = generate_buy_filter_strategy('필터결합', base_code, ['등락율 <= 2', '시분초 < 100000'])

        assert result['status'] == 'ok'
        assert result['type'] == 'buy'
        assert '# 기존 전략' in result['code']
        assert 'if 매수:\n    if 등락율 <= 2:\n        매수 = False' in result['code']
        assert 'if 매수:\n    if 시분초 < 100000:\n        매수 = False' in result['code']
        assert result['code'].rfind('if 매수:\n    self.Buy()') > result['code'].find('등락율 <= 2')

    def test_generate_buy_filter_strategy_errors_when_final_buy_marker_missing(self):
        """최종 self.Buy() 진입 지점을 찾지 못하면 에러를 반환해야 한다."""
        base_code = '매수 = True\nif 관심종목 != 1:\n    매수 = False\n'
        result = generate_buy_filter_strategy('필터결합오류', base_code, ['등락율 <= 2'])
        assert result['status'] == 'error'
        assert 'self.Buy' in result['message']


# ============================================================
# TestGenerateSellStrategy
# ============================================================

class TestGenerateSellStrategy:
    """generate_sell_strategy — 분봉 매도 전략 생성."""

    def test_generate_sell_strategy(self):
        """매도 전략을 생성하고 type='sell'을 반환한다."""
        result = generate_sell_strategy('단순매도', ['self.vars[0] < self.vars[1]'])
        assert result['status'] == 'ok'
        assert result['type'] == 'sell'
        assert 'self.vars[0] < self.vars[1]' in result['code']
        assert '자동 생성 분봉 매도 전략' in result['code']

    def test_generate_sell_empty_conditions(self):
        """빈 조건 리스트는 에러를 반환한다."""
        result = generate_sell_strategy('빈매도', [])
        assert result['status'] == 'error'
        assert '매도 조건이 비어있습니다.' in result['message']

    def test_generate_sell_multiple_conditions(self):
        """다중 조건 매도 전략도 AND로 결합된다."""
        conditions = ['self.RSI(14) > 70', 'self.vars[0] < 0']
        result = generate_sell_strategy('복합매도', conditions)
        assert result['status'] == 'ok'
        assert 'and' in result['code']


# ============================================================
# TestGeneratedCodeQuality
# ============================================================

class TestGeneratedCodeQuality:
    """생성된 코드의 컴파일 가능성 및 검증 통과 여부."""

    def test_generated_code_compiles(self):
        """generate_buy_strategy가 반환한 코드는 compile()을 통과한다."""
        result = generate_buy_strategy('컴파일테스트', ['self.vars[0] > 100'])
        assert result['status'] == 'ok'
        # compile이 예외를 던지지 않아야 한다
        compile(result['code'], '<strategy>', 'exec')

    def test_generated_code_validates(self):
        """generate_buy_strategy가 반환한 코드는 validate_strategy_code()를 통과한다."""
        result = generate_buy_strategy('검증테스트', ['self.vars[0] > self.vars[1]'])
        assert result['status'] == 'ok'
        validation = validate_strategy_code(result['code'])
        assert validation['status'] == 'ok'

    def test_invalid_condition_syntax(self):
        """구문 오류가 있는 조건은 에러를 반환한다."""
        # 유효하지 않은 Python 표현식
        result = generate_buy_strategy('오류전략', ['if True print()'])
        assert result['status'] == 'error'
        assert '구문 오류' in result['message']

    def test_sell_generated_code_compiles(self):
        """generate_sell_strategy가 반환한 코드도 compile()을 통과한다."""
        result = generate_sell_strategy('매도컴파일', ['self.RSI(14) > 70'])
        assert result['status'] == 'ok'
        compile(result['code'], '<strategy>', 'exec')


# ============================================================
# TestSaveStrategyToDb
# ============================================================

class TestSaveStrategyToDb:
    """save_strategy_to_db — DB 저장."""

    def test_save_to_db(self, strategy_db):
        """매수 전략을 DB에 저장하고 ok를 반환한다."""
        result = save_strategy_to_db(strategy_db, '새전략', 'if True:\n    pass', 'buy')
        assert result['status'] == 'ok'
        assert result['name'] == '새전략'
        assert result['action'] == 'created'

    def test_save_update_existing(self, strategy_db):
        """이미 존재하는 전략은 UPDATE하고 action='updated'를 반환한다."""
        save_strategy_to_db(strategy_db, '기존전략', 'if True:\n    pass', 'buy')
        result = save_strategy_to_db(strategy_db, '기존전략', 'if False:\n    pass', 'buy')
        assert result['status'] == 'ok'
        assert result['action'] == 'updated'

        # DB에서 실제로 업데이트되었는지 확인
        con = sqlite3.connect(strategy_db)
        row = con.execute('SELECT 전략코드 FROM stockbuy WHERE "index" = ?', ('기존전략',)).fetchone()
        con.close()
        assert row is not None
        assert 'False' in row[0]

    def test_save_sell_strategy(self, strategy_db):
        """매도 전략을 stocksell 테이블에 저장한다."""
        result = save_strategy_to_db(strategy_db, '매도저장', 'if True:\n    pass', 'sell')
        assert result['status'] == 'ok'
        assert result['action'] == 'created'

        con = sqlite3.connect(strategy_db)
        row = con.execute('SELECT 전략코드 FROM stocksell WHERE "index" = ?', ('매도저장',)).fetchone()
        con.close()
        assert row is not None

    def test_save_invalid_type(self, strategy_db):
        """유효하지 않은 strategy_type은 에러를 반환한다."""
        result = save_strategy_to_db(strategy_db, '잘못된타입', 'pass', 'invalid')
        assert result['status'] == 'error'


# ============================================================
# TestDeleteStrategyFromDb
# ============================================================

class TestDeleteStrategyFromDb:
    """delete_strategy_from_db — DB 삭제."""

    def test_delete_from_db(self, strategy_db):
        """존재하는 전략을 삭제하고 action='deleted'를 반환한다."""
        save_strategy_to_db(strategy_db, '삭제대상', 'if True:\n    pass', 'buy')
        result = delete_strategy_from_db(strategy_db, '삭제대상', 'buy')
        assert result['status'] == 'ok'
        assert result['action'] == 'deleted'

        # DB에서 실제로 삭제되었는지 확인
        con = sqlite3.connect(strategy_db)
        row = con.execute('SELECT 1 FROM stockbuy WHERE "index" = ?', ('삭제대상',)).fetchone()
        con.close()
        assert row is None

    def test_delete_nonexistent(self, strategy_db):
        """존재하지 않는 전략을 삭제하면 에러를 반환한다."""
        result = delete_strategy_from_db(strategy_db, '없는전략', 'buy')
        assert result['status'] == 'error'
        assert '전략을 찾을 수 없습니다.' in result['message']

    def test_delete_sell_strategy(self, strategy_db):
        """매도 전략도 정상적으로 삭제된다."""
        save_strategy_to_db(strategy_db, '매도삭제', 'if True:\n    pass', 'sell')
        result = delete_strategy_from_db(strategy_db, '매도삭제', 'sell')
        assert result['status'] == 'ok'
        assert result['action'] == 'deleted'


# ============================================================
# TestCreateAndSave
# ============================================================

class TestCreateAndSave:
    """create_and_save — 생성+검증+저장 통합."""

    def test_create_and_save_integration(self, strategy_db):
        """생성, 검증, 저장이 통합으로 성공한다."""
        result = create_and_save(
            strategy_db,
            '통합전략',
            ['self.vars[0] > self.vars[1]'],
            'buy',
        )
        assert result['status'] == 'ok'
        assert result['action'] in ('created', 'updated')

        # DB에 실제로 저장되었는지 확인
        con = sqlite3.connect(strategy_db)
        row = con.execute('SELECT 전략코드 FROM stockbuy WHERE "index" = ?', ('통합전략',)).fetchone()
        con.close()
        assert row is not None
        assert 'self.vars[0] > self.vars[1]' in row[0]

    def test_create_and_save_empty_conditions_no_db_write(self, strategy_db):
        """빈 조건은 에러를 반환하고 DB에 저장하지 않는다."""
        result = create_and_save(strategy_db, '빈통합', [], 'buy')
        assert result['status'] == 'error'

        con = sqlite3.connect(strategy_db)
        row = con.execute('SELECT 1 FROM stockbuy WHERE "index" = ?', ('빈통합',)).fetchone()
        con.close()
        assert row is None

    def test_create_and_save_sell(self, strategy_db):
        """매도 전략도 통합 생성+저장이 성공한다."""
        result = create_and_save(
            strategy_db,
            '통합매도',
            ['self.RSI(14) > 70'],
            'sell',
        )
        assert result['status'] == 'ok'
