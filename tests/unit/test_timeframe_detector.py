"""전략-타임프레임 자동 매칭 모듈 테스트."""
import os
import sqlite3
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.timeframe_detector import (
    detect_from_db,
    detect_timeframe,
    validate_timeframe_match,
)


# ============================================================
# Helpers
# ============================================================

class _Config:
    """테스트용 최소 config 객체."""
    def __init__(self, buy_strategy: str, is_tick: bool, sell_strategy: str = ''):
        self.buy_strategy = buy_strategy
        self.sell_strategy = sell_strategy
        self.is_tick = is_tick


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def strategy_db(tmp_path):
    """테스트용 strategy.db (stockbuy 테이블)."""
    db = str(tmp_path / 'strategy.db')
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE stockbuy ([index] TEXT PRIMARY KEY, 전략코드 TEXT)")
    con.execute("CREATE TABLE stocksell ([index] TEXT PRIMARY KEY, 전략코드 TEXT)")
    con.execute("INSERT INTO stockbuy VALUES ('Min_Code_Strategy', '분봉시간 = 5')")
    con.execute("INSERT INTO stockbuy VALUES ('Tick_Code_Strategy', '틱 기반 로직')")
    con.execute("INSERT INTO stockbuy VALUES ('Code_Only_Min', '분봉 이동평균')")
    con.execute("INSERT INTO stockbuy VALUES ('Unknown_Strategy', 'x = 1 + 2')")
    con.commit()
    con.close()
    return db


# ============================================================
# TestDetectTimeframe
# ============================================================

class TestDetectTimeframe:
    """detect_timeframe — 이름/코드 기반 타임프레임 감지."""

    def test_detect_min_prefix(self):
        """Min_ 접두사 → 'min'."""
        assert detect_timeframe('Min_B_Study') == 'min'

    def test_detect_tick_prefix(self):
        """Tick_ 접두사 → 'tick'."""
        assert detect_timeframe('Tick_B_Test') == 'tick'

    def test_detect_from_code_min(self):
        """이름 unknown + 코드에 '분봉시간' → 'min'."""
        assert detect_timeframe('SomeStrategy', '분봉시간 = 3') == 'min'

    def test_detect_from_code_tick(self):
        """이름 unknown + 코드에 '틱' → 'tick'."""
        assert detect_timeframe('SomeStrategy', '틱 기반 전략') == 'tick'

    def test_detect_unknown(self):
        """이름/코드 모두 판별 불가 → 'unknown'."""
        assert detect_timeframe('GenericStrategy', 'x = 1 + 2') == 'unknown'

    def test_detect_unknown_no_code(self):
        """코드 없이 이름만으로 판별 불가 → 'unknown'."""
        assert detect_timeframe('GenericStrategy') == 'unknown'

    def test_detect_case_insensitive(self):
        """소문자 min_ 접두사도 'min'으로 감지한다."""
        assert detect_timeframe('min_b_test') == 'min'

    def test_detect_case_insensitive_tick(self):
        """소문자 tick_ 접두사도 'tick'으로 감지한다."""
        assert detect_timeframe('tick_b_test') == 'tick'

    def test_detect_mixed_case_prefix(self):
        """혼합 대소문자 MIN_ → 'min'으로 감지한다."""
        assert detect_timeframe('MIN_Strategy') == 'min'

    def test_name_takes_priority_over_code(self):
        """이름에서 감지되면 코드 내용과 무관하게 이름 결과를 반환한다."""
        # Min_ 이름인데 코드에 '틱'이 있어도 이름 우선
        assert detect_timeframe('Min_X', '틱 전략') == 'min'

    def test_code_keyword_분봉(self):
        """코드에 '분봉' 키워드(분봉시간 없이)도 'min'으로 감지한다."""
        assert detect_timeframe('SomeStrategy', '분봉 이동평균') == 'min'


# ============================================================
# TestValidateTimeframeMatch
# ============================================================

class TestValidateTimeframeMatch:
    """validate_timeframe_match — config와 전략 타임프레임 일치 검증."""

    def test_validate_match_ok(self):
        """Min 전략 + is_tick=False → ok."""
        config = _Config('Min_B_Study', is_tick=False)
        result = validate_timeframe_match(config)
        assert result == {'status': 'ok'}

    def test_validate_mismatch_min_tick(self):
        """Min 전략 + is_tick=True → error."""
        config = _Config('Min_B_Study', is_tick=True)
        result = validate_timeframe_match(config)
        assert result['status'] == 'error'
        assert 'Min_B_Study' in result['message']
        assert '--timeframe min' in result['message']

    def test_validate_mismatch_tick_min(self):
        """Tick 전략 + is_tick=False → error."""
        config = _Config('Tick_B_Test', is_tick=False)
        result = validate_timeframe_match(config)
        assert result['status'] == 'error'
        assert 'Tick_B_Test' in result['message']
        assert '--timeframe tick' in result['message']

    def test_validate_tick_tick_ok(self):
        """Tick 전략 + is_tick=True → ok."""
        config = _Config('Tick_B_Test', is_tick=True)
        result = validate_timeframe_match(config)
        assert result == {'status': 'ok'}

    def test_validate_unknown_ok(self):
        """unknown 전략은 항상 ok."""
        config = _Config('GenericStrategy', is_tick=True)
        result = validate_timeframe_match(config)
        assert result == {'status': 'ok'}

    def test_validate_unknown_ok_min_mode(self):
        """unknown 전략은 is_tick=False에서도 ok."""
        config = _Config('GenericStrategy', is_tick=False)
        result = validate_timeframe_match(config)
        assert result == {'status': 'ok'}

    def test_validate_with_code_min_mismatch(self):
        """이름으로 판별 불가, 코드에 '분봉시간' + is_tick=True → error."""
        config = _Config('SomeStrategy', is_tick=True)
        result = validate_timeframe_match(config, strategy_code='분봉시간 = 5')
        assert result['status'] == 'error'
        assert '--timeframe min' in result['message']

    def test_validate_with_code_tick_mismatch(self):
        """이름으로 판별 불가, 코드에 '틱' + is_tick=False → error."""
        config = _Config('SomeStrategy', is_tick=False)
        result = validate_timeframe_match(config, strategy_code='틱 기반')
        assert result['status'] == 'error'
        assert '--timeframe tick' in result['message']

    def test_validate_sell_strategy_mismatch(self):
        """매도 전략이 Tick_ 이고 is_tick=False이면 error."""
        config = _Config('GenericStrategy', is_tick=False, sell_strategy='Tick_S_Test')
        result = validate_timeframe_match(config)
        assert result['status'] == 'error'
        assert 'Tick_S_Test' in result['message']

    def test_validate_sell_strategy_match_ok(self):
        """매수/매도 모두 분봉 전략이고 is_tick=False이면 ok."""
        config = _Config('Min_B_Test', is_tick=False, sell_strategy='Min_S_Test')
        result = validate_timeframe_match(config)
        assert result == {'status': 'ok'}

    def test_validate_sell_detected_from_db(self, strategy_db):
        """매도 전략 이름이 ambiguous여도 DB 코드로 tick/min을 감지한다."""
        con = sqlite3.connect(strategy_db)
        con.execute("INSERT INTO stocksell VALUES ('AmbiguousSell', '틱 기반 매도')")
        con.commit()
        con.close()
        config = _Config('Min_B_Test', is_tick=False, sell_strategy='AmbiguousSell')
        result = validate_timeframe_match(config, db_path=strategy_db)
        assert result['status'] == 'error'
        assert '--timeframe tick' in result['message']


# ============================================================
# TestDetectFromDb
# ============================================================

class TestDetectFromDb:
    """detect_from_db — DB에서 코드 읽어 타임프레임 감지."""

    def test_detect_from_db_min_by_name(self, strategy_db):
        """이름이 Min_ 접두사인 전략 → 'min'."""
        result = detect_from_db(strategy_db, 'Min_Code_Strategy', 'buy')
        assert result == 'min'

    def test_detect_from_db_tick_by_name(self, strategy_db):
        """이름이 Tick_ 접두사인 전략 → 'tick'."""
        result = detect_from_db(strategy_db, 'Tick_Code_Strategy', 'buy')
        assert result == 'tick'

    def test_detect_from_db_min_by_code(self, strategy_db):
        """이름 판별 불가, DB 코드에 '분봉' → 'min'."""
        result = detect_from_db(strategy_db, 'Code_Only_Min', 'buy')
        assert result == 'min'

    def test_detect_from_db_unknown(self, strategy_db):
        """판별 불가 전략 → 'unknown'."""
        result = detect_from_db(strategy_db, 'Unknown_Strategy', 'buy')
        assert result == 'unknown'

    def test_detect_from_db_missing_strategy(self, strategy_db):
        """DB에 없는 전략 이름 → 'unknown'."""
        result = detect_from_db(strategy_db, 'NonExistent', 'buy')
        assert result == 'unknown'

    def test_detect_from_db_invalid_path(self):
        """잘못된 DB 경로 → 'unknown' (예외 없음)."""
        result = detect_from_db('/nonexistent/strategy.db', 'AnyName', 'buy')
        assert result == 'unknown'
