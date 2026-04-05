"""cli/config.py 단위 테스트.

대상: parse_args, validate, list_strategies, load_from_json, _valid_date, BacktestConfig
"""
import json
import os
import sqlite3
import sys

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.config import (
    BacktestConfig,
    _valid_date,
    list_strategies,
    load_from_json,
    parse_args,
    validate,
)


# ============================================================
# BacktestConfig 기본값 테스트
# ============================================================

class TestBacktestConfigDefaults:
    """BacktestConfig 인스턴스가 문서화된 기본값을 갖는지 검증."""

    def test_timeout_default_is_3600(self):
        """timeout 기본값은 3600초(1시간)이어야 한다."""
        config = BacktestConfig()
        assert config.timeout == 3600

    def test_one_code_default_is_empty_string(self):
        """one_code 기본값은 빈 문자열이어야 한다."""
        config = BacktestConfig()
        assert config.one_code == ''

    def test_buy_strategy_default_is_empty_string(self):
        """buy_strategy 기본값은 빈 문자열이어야 한다."""
        config = BacktestConfig()
        assert config.buy_strategy == ''

    def test_sell_strategy_default_is_empty_string(self):
        """sell_strategy 기본값은 빈 문자열이어야 한다."""
        config = BacktestConfig()
        assert config.sell_strategy == ''

    def test_start_date_default_is_zero(self):
        """start_date 기본값은 0이어야 한다."""
        config = BacktestConfig()
        assert config.start_date == 0

    def test_end_date_default_is_zero(self):
        """end_date 기본값은 0이어야 한다."""
        config = BacktestConfig()
        assert config.end_date == 0

    def test_is_tick_default_is_true(self):
        """is_tick 기본값은 True이어야 한다."""
        config = BacktestConfig()
        assert config.is_tick is True

    def test_engine_count_default_is_4(self):
        """engine_count 기본값은 4이어야 한다."""
        config = BacktestConfig()
        assert config.engine_count == 4

    def test_output_format_default_is_json(self):
        """output_format 기본값은 'json'이어야 한다."""
        config = BacktestConfig()
        assert config.output_format == 'json'

    def test_output_file_default_is_none(self):
        """output_file 기본값은 None이어야 한다."""
        config = BacktestConfig()
        assert config.output_file is None


# ============================================================
# _valid_date 테스트
# ============================================================

class TestValidDate:
    """_valid_date()가 YYYYMMDD 정수 날짜를 올바르게 검증하는지 확인."""

    def test_returns_true_for_valid_date_20250115(self):
        """20250115는 유효한 날짜이므로 True를 반환해야 한다."""
        assert _valid_date(20250115) is True

    def test_returns_true_for_valid_date_start_of_year(self):
        """20250101은 유효한 날짜이므로 True를 반환해야 한다."""
        assert _valid_date(20250101) is True

    def test_returns_true_for_valid_date_end_of_year(self):
        """20251231은 유효한 날짜이므로 True를 반환해야 한다."""
        assert _valid_date(20251231) is True

    def test_returns_false_for_invalid_month_13(self):
        """20251301은 13월이므로 False를 반환해야 한다."""
        assert _valid_date(20251301) is False

    def test_returns_false_for_invalid_day_32(self):
        """20250132는 32일이므로 False를 반환해야 한다."""
        assert _valid_date(20250132) is False

    def test_returns_false_for_8_digit_nonsense(self):
        """99999999는 유효하지 않은 날짜이므로 False를 반환해야 한다."""
        assert _valid_date(99999999) is False

    def test_returns_false_for_zero(self):
        """0은 YYYYMMDD 형식이 아니므로 False를 반환해야 한다."""
        assert _valid_date(0) is False

    def test_returns_true_for_leap_day_in_leap_year(self):
        """20240229는 윤년의 유효한 날짜이므로 True를 반환해야 한다."""
        assert _valid_date(20240229) is True

    def test_returns_false_for_leap_day_in_non_leap_year(self):
        """20250229는 윤년이 아닌 해의 날짜이므로 False를 반환해야 한다."""
        assert _valid_date(20250229) is False


# ============================================================
# parse_args 테스트
# ============================================================

class TestParseArgs:
    """parse_args()가 CLI 인수를 올바르게 파싱하는지 검증."""

    def test_help_raises_system_exit(self):
        """--help 인수는 SystemExit을 발생시켜야 한다."""
        with pytest.raises(SystemExit):
            parse_args(['--help'])

    def test_list_strategies_returns_none(self, monkeypatch, tmp_strategy_db):
        """--list-strategies 인수는 전략 목록을 출력하고 None을 반환해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['전략A'], 'stocksell': ['전략B']})
        result = parse_args(['--list-strategies'])
        assert result is None

    def test_list_strategies_parse_error_when_strategy_lookup_fails(self, monkeypatch, capsys):
        """--list-strategies 경로에서 전략 조회 실패는 parser.error(SystemExit)로 처리해야 한다."""
        import cli.config as config_mod

        def _raise():
            raise RuntimeError('strategy lookup failed')

        monkeypatch.setattr(config_mod, 'list_strategies', _raise)

        with pytest.raises(SystemExit):
            parse_args(['--list-strategies'])

        captured = capsys.readouterr()
        assert 'strategy lookup failed' in captured.err

    def test_normal_args_returns_backtest_config(self):
        """유효한 --buy, --sell, --start, --end 인수는 BacktestConfig를 반환해야 한다."""
        config = parse_args([
            '--buy', '매수전략A',
            '--sell', '매도전략B',
            '--start', '20250101',
            '--end', '20250131',
        ])
        assert isinstance(config, BacktestConfig)
        assert config.buy_strategy == '매수전략A'
        assert config.sell_strategy == '매도전략B'
        assert config.start_date == 20250101
        assert config.end_date == 20250131

    def test_config_file_arg_loads_json(self, tmp_path):
        """--config FILE 인수는 JSON 파일에서 설정을 로드해야 한다."""
        cfg_file = tmp_path / 'cfg.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'JSON매수',
            'sell_strategy': 'JSON매도',
            'start_date': 20250201,
            'end_date': 20250228,
        }), encoding='utf-8')

        config = parse_args(['--config', str(cfg_file)])
        assert isinstance(config, BacktestConfig)
        assert config.buy_strategy == 'JSON매수'

    def test_timeout_arg_is_parsed(self):
        """--timeout 인수가 BacktestConfig.timeout에 반영되어야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
            '--timeout', '120',
        ])
        assert config.timeout == 120

    def test_timeout_default_when_omitted(self):
        """--timeout을 생략하면 기본값 3600이 설정되어야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
        ])
        assert config.timeout == 3600

    def test_one_code_arg_is_parsed(self):
        """--one-code 인수가 BacktestConfig.one_code에 반영되어야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
            '--one-code', 'A005930',
        ])
        assert config.one_code == 'A005930'

    def test_one_code_default_when_omitted(self):
        """--one-code를 생략하면 빈 문자열이 설정되어야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
        ])
        assert config.one_code == ''

    def test_timeframe_tick_sets_is_tick_true(self):
        """--timeframe tick은 is_tick=True를 설정해야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
            '--timeframe', 'tick',
        ])
        assert config.is_tick is True

    def test_timeframe_min_sets_is_tick_false(self):
        """--timeframe min은 is_tick=False를 설정해야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
            '--timeframe', 'min',
        ])
        assert config.is_tick is False

    def test_output_format_text(self):
        """--format text는 output_format='text'를 설정해야 한다."""
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
            '--format', 'text',
        ])
        assert config.output_format == 'text'

    def test_output_file_is_set(self, tmp_path):
        """--output FILE은 output_file 필드에 경로를 설정해야 한다."""
        out_file = str(tmp_path / 'result.json')
        config = parse_args([
            '--buy', 'A', '--sell', 'B',
            '--start', '20250101', '--end', '20250131',
            '--output', out_file,
        ])
        assert config.output_file == out_file


# ============================================================
# validate 테스트
# ============================================================

class TestValidate:
    """validate()가 BacktestConfig의 오류를 올바르게 감지하는지 검증."""

    def _make_valid_config(self):
        """모든 필수 필드가 채워진 최소 유효 설정을 반환한다."""
        return BacktestConfig(
            buy_strategy='매수전략',
            sell_strategy='매도전략',
            start_date=20250101,
            end_date=20250131,
        )

    def test_empty_buy_strategy_produces_error(self, monkeypatch):
        """buy_strategy가 빈 문자열이면 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': [], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.buy_strategy = ''
        errors = validate(config)
        assert any('매수 전략' in e and '지정되지 않았습니다' in e for e in errors)

    def test_empty_sell_strategy_produces_error(self, monkeypatch):
        """sell_strategy가 빈 문자열이면 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': []})
        config = self._make_valid_config()
        config.sell_strategy = ''
        errors = validate(config)
        assert any('매도 전략' in e and '지정되지 않았습니다' in e for e in errors)

    def test_start_date_greater_than_end_date_produces_error(self, monkeypatch):
        """start_date가 end_date보다 크면 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.start_date = 20250201
        config.end_date = 20250101
        errors = validate(config)
        assert any('시작일자' in e and '종료일자' in e for e in errors)

    def test_invalid_start_date_20251301_produces_error(self, monkeypatch):
        """start_date=20251301은 유효하지 않은 날짜이므로 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.start_date = 20251301
        errors = validate(config)
        assert any('시작일자' in e and '유효한 날짜가 아닙니다' in e for e in errors)

    def test_invalid_end_date_produces_error(self, monkeypatch):
        """end_date=20251301은 유효하지 않은 날짜이므로 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.end_date = 20251301
        errors = validate(config)
        assert any('종료일자' in e and '유효한 날짜가 아닙니다' in e for e in errors)

    def test_valid_config_with_known_strategies_returns_empty_errors(
            self, monkeypatch, tmp_strategy_db):
        """전략이 DB에 존재하고 날짜가 유효하면 오류 목록이 비어야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['테스트매수전략'],
                                     'stocksell': ['테스트매도전략']})
        config = BacktestConfig(
            buy_strategy='테스트매수전략',
            sell_strategy='테스트매도전략',
            start_date=20250101,
            end_date=20250131,
        )
        errors = validate(config)
        assert errors == []

    def test_buy_strategy_not_in_db_produces_error(self, monkeypatch):
        """buy_strategy가 DB에 없으면 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['다른전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        errors = validate(config)
        assert any("strategy.db에 없습니다" in e for e in errors)

    def test_sell_strategy_not_in_db_produces_error(self, monkeypatch):
        """sell_strategy가 DB에 없으면 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['다른전략']})
        config = self._make_valid_config()
        errors = validate(config)
        assert any("strategy.db에 없습니다" in e for e in errors)

    def test_missing_db_produces_graceful_error_message(self, monkeypatch):
        """list_strategies()가 예외를 던지면 DB 읽기 실패 메시지가 오류에 포함되어야 한다."""
        import cli.config as config_mod

        def _raise():
            raise OSError('DB 없음')

        monkeypatch.setattr(config_mod, 'list_strategies', _raise)
        config = self._make_valid_config()
        errors = validate(config)
        assert any('strategy.db 읽기 실패' in e for e in errors)

    def test_engine_count_zero_produces_error(self, monkeypatch):
        """engine_count=0이면 오류 메시지를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.engine_count = 0
        errors = validate(config)
        assert any('엔진 수' in e for e in errors)

    def test_zero_start_date_produces_missing_error(self, monkeypatch):
        """start_date=0이면 '지정되지 않았습니다' 오류를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.start_date = 0
        errors = validate(config)
        assert any('시작일자' in e and '지정되지 않았습니다' in e for e in errors)

    def test_zero_end_date_produces_missing_error(self, monkeypatch):
        """end_date=0이면 '지정되지 않았습니다' 오류를 포함해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'list_strategies',
                            lambda: {'stockbuy': ['매수전략'], 'stocksell': ['매도전략']})
        config = self._make_valid_config()
        config.end_date = 0
        errors = validate(config)
        assert any('종료일자' in e and '지정되지 않았습니다' in e for e in errors)


# ============================================================
# list_strategies 테스트
# ============================================================

class TestListStrategies:
    """list_strategies()가 strategy.db에서 전략 이름을 올바르게 읽는지 검증."""

    def test_returns_stockbuy_names_from_real_test_db(
            self, monkeypatch, tmp_strategy_db):
        """tmp_strategy_db의 stockbuy 테이블에서 전략 이름을 반환해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', tmp_strategy_db)

        result = list_strategies()
        assert '테스트매수전략' in result['stockbuy']

    def test_returns_stocksell_names_from_real_test_db(
            self, monkeypatch, tmp_strategy_db):
        """tmp_strategy_db의 stocksell 테이블에서 전략 이름을 반환해야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', tmp_strategy_db)

        result = list_strategies()
        assert '테스트매도전략' in result['stocksell']

    def test_returns_dict_with_both_keys(self, monkeypatch, tmp_strategy_db):
        """반환 값은 'stockbuy'와 'stocksell' 키를 모두 가져야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', tmp_strategy_db)

        result = list_strategies()
        assert 'stockbuy' in result
        assert 'stocksell' in result

    def test_returns_lists_for_both_keys(self, monkeypatch, tmp_strategy_db):
        """stockbuy와 stocksell 값은 list 타입이어야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', tmp_strategy_db)

        result = list_strategies()
        assert isinstance(result['stockbuy'], list)
        assert isinstance(result['stocksell'], list)

    def test_raises_when_strategy_db_read_fails(self, monkeypatch, tmp_path):
        """strategy DB 조회나 스키마 확인이 실패하면 예외를 전파해야 한다."""
        import cli.config as config_mod
        broken_path = str(tmp_path / 'broken_strategy.db')
        sqlite3.connect(broken_path).close()
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', broken_path)

        with pytest.raises(sqlite3.Error):
            list_strategies()

    def test_returns_exactly_one_buy_strategy_in_test_db(
            self, monkeypatch, tmp_strategy_db):
        """tmp_strategy_db의 stockbuy 테이블에는 정확히 1개의 전략이 있어야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', tmp_strategy_db)

        result = list_strategies()
        assert len(result['stockbuy']) == 1

    def test_returns_exactly_one_sell_strategy_in_test_db(
            self, monkeypatch, tmp_strategy_db):
        """tmp_strategy_db의 stocksell 테이블에는 정확히 1개의 전략이 있어야 한다."""
        import cli.config as config_mod
        monkeypatch.setattr(config_mod, 'DB_STRATEGY', tmp_strategy_db)

        result = list_strategies()
        assert len(result['stocksell']) == 1


# ============================================================
# load_from_json 테스트
# ============================================================

class TestLoadFromJson:
    """load_from_json()이 JSON 설정 파일을 올바르게 BacktestConfig로 로드하는지 검증."""

    def test_loads_buy_and_sell_strategy_from_valid_json(self, tmp_path):
        """유효한 JSON 파일에서 buy_strategy와 sell_strategy를 읽어야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'JSON매수전략',
            'sell_strategy': 'JSON매도전략',
            'start_date': 20250101,
            'end_date': 20250131,
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert config.buy_strategy == 'JSON매수전략'
        assert config.sell_strategy == 'JSON매도전략'

    def test_loads_dates_from_valid_json(self, tmp_path):
        """유효한 JSON 파일에서 start_date와 end_date를 읽어야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250201,
            'end_date': 20250228,
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert config.start_date == 20250201
        assert config.end_date == 20250228

    def test_returns_backtest_config_instance(self, tmp_path):
        """load_from_json()은 BacktestConfig 인스턴스를 반환해야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert isinstance(config, BacktestConfig)

    def test_timeframe_tick_sets_is_tick_true(self, tmp_path):
        """JSON에 timeframe='tick'이면 is_tick=True로 설정되어야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'timeframe': 'tick',
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert config.is_tick is True

    def test_timeframe_min_sets_is_tick_false(self, tmp_path):
        """JSON에 timeframe='min'이면 is_tick=False로 설정되어야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'timeframe': 'min',
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert config.is_tick is False

    def test_timeframe_key_is_consumed_not_passed_to_dataclass(self, tmp_path):
        """timeframe 키는 소비되어 BacktestConfig 생성자에 전달되지 않아야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'timeframe': 'tick',
        }), encoding='utf-8')

        # timeframe이 BacktestConfig 생성자에 전달되면 TypeError가 발생한다.
        # 오류 없이 반환되면 올바르게 소비된 것이다.
        config = load_from_json(str(cfg_file))
        assert isinstance(config, BacktestConfig)

    def test_json_with_unknown_keys_ignored_gracefully(self, tmp_path):
        """알 수 없는 키가 포함된 JSON은 무시되고 정상 로드되어야 한다 (US-303)."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'unknown_key_xyz': 'some_value',
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert config.buy_strategy == 'A'
        assert not hasattr(config, 'unknown_key_xyz')

    def test_optional_fields_are_loaded_from_json(self, tmp_path):
        """JSON에 선택 필드가 포함되면 BacktestConfig에 반영되어야 한다."""
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'timeout': 7200,
            'one_code': 'A005930',
            'engine_count': 2,
        }), encoding='utf-8')

        config = load_from_json(str(cfg_file))
        assert config.timeout == 7200
        assert config.one_code == 'A005930'
        assert config.engine_count == 2

    def test_missing_file_raises_file_not_found_error(self, tmp_path):
        """존재하지 않는 파일 경로를 주면 FileNotFoundError를 발생시켜야 한다."""
        missing = str(tmp_path / 'does_not_exist.json')
        with pytest.raises(FileNotFoundError):
            load_from_json(missing)
