"""cli/output.py 단위 테스트.

format_result(), format_json(), format_text() 동작을 검증한다.
BacktestResult dataclass는 제거되어 존재하지 않는다.
"""
import sys
import os
import json

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.output import format_result, format_json, format_text


# ============================================================
# format_result() 라우팅 테스트
# ============================================================

class TestFormatResult:
    """format_result()가 fmt 인자에 따라 올바른 포매터로 라우팅하는지 검증."""

    def test_format_result_json_returns_valid_json(self, sample_result_success):
        """format_result(result, 'json') → json.loads()로 파싱 가능한 문자열을 반환한다."""
        output = format_result(sample_result_success, 'json')
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_format_result_text_returns_string(self, sample_result_success):
        """format_result(result, 'text') → str 타입을 반환한다."""
        output = format_result(sample_result_success, 'text')
        assert isinstance(output, str)

    def test_format_result_default_fmt_is_json(self, sample_result_success):
        """fmt 기본값은 'json'이다."""
        output_default = format_result(sample_result_success)
        output_explicit = format_result(sample_result_success, 'json')
        assert output_default == output_explicit

    def test_format_result_unknown_fmt_falls_back_to_text(self, sample_result_success):
        """fmt='csv' 처럼 알 수 없는 값은 format_text()로 폴백한다."""
        output = format_result(sample_result_success, 'csv')
        assert 'STOM Backtest Result' in output


def test_format_json_error_preserves_engine_data_loading_diagnostics():
    result = {
        'status': 'error',
        'message': 'engine data loading timed out',
        'engine_data_loading': {
            'expected_count': 2,
            'received_count': 1,
            'missing_count': 1,
            'timeout_seconds': 60,
            'received_lengths': [3],
        },
        'checkpoint_status': 'error',
        'last_checkpoint': 'engine_data_response_timeout',
        'elapsed_seconds': 60.123,
        'checkpoints': [
            {
                'name': 'engine_data_response_timeout',
                'elapsed_seconds': 60.123,
                'detail': {'missing_count': 1},
            },
        ],
        'cleanup_status': 'process_killed',
        'csv_path': None,
    }

    parsed = json.loads(format_json(result))

    assert parsed['engine_data_loading'] == result['engine_data_loading']
    assert parsed['checkpoint_status'] == 'error'
    assert parsed['last_checkpoint'] == 'engine_data_response_timeout'
    assert parsed['elapsed_seconds'] == pytest.approx(60.123)
    assert parsed['checkpoints'] == result['checkpoints']
    assert parsed['cleanup_status'] == 'process_killed'
    assert parsed['csv_path'] is None


def test_error_json_preserves_backtest_child_diagnostics():
    result = {
        'status': 'error',
        'message': 'backtest completed without metrics',
        'backtest_child_diagnostics': {
            'stock_back_db_path': 'stock_tick_back.db',
            'moneytop_query_status': 'error',
            'moneytop_error': 'no such table: moneytop',
        },
    }

    parsed = json.loads(format_json(result))

    assert parsed['status'] == 'error'
    assert parsed['backtest_child_diagnostics']['moneytop_query_status'] == 'error'
    assert 'moneytop' in parsed['backtest_child_diagnostics']['moneytop_error']


def test_error_json_preserves_backtest_process_diagnostics():
    result = {
        'status': 'error',
        'message': '백테스트 시간 초과 (300초)',
        'backtest_process_diagnostics': {
            'event_count': 2,
            'last_checkpoint': 'backtest_child_waiting_mq_first',
            'last_by_source': {
                'BackTest': 'backtest_child_waiting_mq_first',
                'Total': 'total_info_received',
            },
            'events': [
                {'source': 'BackTest', 'checkpoint': 'backtest_child_started', 'detail': {}},
                {'source': 'BackTest', 'checkpoint': 'backtest_child_waiting_mq_first', 'detail': {}},
            ],
        },
    }

    parsed = json.loads(format_json(result))

    assert parsed['status'] == 'error'
    assert parsed['backtest_process_diagnostics']['event_count'] == 2
    assert (
        parsed['backtest_process_diagnostics']['last_by_source']['BackTest']
        == 'backtest_child_waiting_mq_first'
    )


def test_format_json_error_omits_absent_diagnostic_fields(sample_result_error):
    parsed = json.loads(format_json(sample_result_error))

    assert 'engine_data_loading' not in parsed
    assert 'checkpoint_status' not in parsed
    assert 'checkpoints' not in parsed


def test_format_json_success_preserves_csv_and_checkpoint_diagnostics(sample_result_success):
    sample_result_success.update({
        'csv_path': 'backtest/csv/result.csv',
        'checkpoint_status': 'success',
        'last_checkpoint': 'csv_detected',
        'elapsed_seconds': 12.345,
        'checkpoints': [
            {
                'name': 'csv_detected',
                'elapsed_seconds': 12.345,
                'detail': {'csv_path': 'backtest/csv/result.csv'},
            },
        ],
        'cleanup_status': 'not_needed',
    })

    parsed = json.loads(format_json(sample_result_success))

    assert parsed['csv_path'] == 'backtest/csv/result.csv'
    assert parsed['checkpoint_status'] == 'success'
    assert parsed['last_checkpoint'] == 'csv_detected'
    assert parsed['elapsed_seconds'] == pytest.approx(12.345)
    assert parsed['checkpoints'] == sample_result_success['checkpoints']
    assert parsed['cleanup_status'] == 'not_needed'


# ============================================================
# format_json() — 성공 결과
# ============================================================

class TestFormatJsonSuccess:
    """format_json()이 성공 결과를 올바른 구조의 JSON으로 직렬화하는지 검증."""

    def test_status_is_success(self, sample_result_success):
        """status 필드가 'success'여야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        assert parsed['status'] == 'success'

    def test_metrics_key_present(self, sample_result_success):
        """최상위에 'metrics' 키가 있어야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        assert 'metrics' in parsed

    def test_bootstrap_key_present(self, sample_result_success):
        """최상위에 'bootstrap' 키가 있어야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        assert 'bootstrap' in parsed

    def test_config_key_present(self, sample_result_success):
        """최상위에 'config' 키가 있어야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        assert 'config' in parsed

    def test_timestamp_key_present(self, sample_result_success):
        """최상위에 'timestamp' 키가 있어야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        assert 'timestamp' in parsed

    def test_metrics_values_match_fixture(self, sample_result_success):
        """metrics 필드 값이 fixture 값과 일치해야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        m = parsed['metrics']
        assert m['trade_count'] == 150
        assert m['win_rate'] == pytest.approx(55.3)
        assert m['avg_profit_pct'] == pytest.approx(0.82)
        assert m['total_profit_pct'] == pytest.approx(12.5)
        assert m['total_profit_krw'] == 1250000
        assert m['cagr'] == pytest.approx(15.2)
        assert m['mdd_pct'] == pytest.approx(-8.3)
        assert m['tpi'] == pytest.approx(1.45)
        assert m['seed_capital'] == pytest.approx(10000000.0)
        assert m['max_hold_count'] == 5
        assert m['avg_hold_time'] == pytest.approx(35.2)
        assert m['day_count'] == 22

    def test_bootstrap_values_match_fixture(self, sample_result_success):
        """bootstrap avg/ci_lower/ci_upper 값이 fixture와 일치해야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        b = parsed['bootstrap']
        assert b['avg_return'] == pytest.approx(12.1)
        assert b['ci_lower'] == pytest.approx(5.3)
        assert b['ci_upper'] == pytest.approx(19.8)

    def test_config_values_match_fixture(self, sample_result_success):
        """config 필드 값이 fixture 값과 일치해야 한다."""
        parsed = json.loads(format_json(sample_result_success))
        c = parsed['config']
        assert c['buy_strategy'] == '테스트매수전략'
        assert c['sell_strategy'] == '테스트매도전략'
        assert c['start_date'] == '20250101'
        assert c['end_date'] == '20250131'

    def test_output_is_parseable_by_json_loads(self, sample_result_success):
        """format_json() 반환값을 json.loads()로 파싱해도 예외가 발생하지 않는다."""
        raw = format_json(sample_result_success)
        parsed = json.loads(raw)
        assert parsed is not None


# ============================================================
# format_json() — 에러 결과
# ============================================================

class TestFormatJsonError:
    """format_json()이 에러 결과를 올바른 구조의 JSON으로 직렬화하는지 검증."""

    def test_status_is_error(self, sample_result_error):
        """status 필드가 'error'여야 한다."""
        parsed = json.loads(format_json(sample_result_error))
        assert parsed['status'] == 'error'

    def test_message_field_present(self, sample_result_error):
        """'message' 키가 있어야 한다."""
        parsed = json.loads(format_json(sample_result_error))
        assert 'message' in parsed

    def test_message_value_matches_fixture(self, sample_result_error):
        """message 값이 fixture의 에러 메시지와 일치해야 한다."""
        parsed = json.loads(format_json(sample_result_error))
        assert parsed['message'] == '매수 전략이 DB에 없습니다.'

    def test_timestamp_present_on_error(self, sample_result_error):
        """에러 결과에도 timestamp 키가 있어야 한다."""
        parsed = json.loads(format_json(sample_result_error))
        assert 'timestamp' in parsed

    def test_no_metrics_key_on_error(self, sample_result_error):
        """에러 결과에는 'metrics' 키가 없어야 한다."""
        parsed = json.loads(format_json(sample_result_error))
        assert 'metrics' not in parsed

    def test_error_output_is_parseable_by_json_loads(self, sample_result_error):
        """에러 결과도 json.loads()로 파싱 가능해야 한다."""
        raw = format_json(sample_result_error)
        parsed = json.loads(raw)
        assert parsed['status'] == 'error'


# ============================================================
# format_json() — 빈/None metrics 기본값
# ============================================================

class TestFormatJsonDefaults:
    """metrics 또는 config가 비어있거나 None일 때 기본값 0이 사용되는지 검증."""

    def test_none_metrics_defaults_to_zero_trade_count(self):
        """metrics=None → trade_count 기본값이 0이어야 한다."""
        result = {'status': 'success', 'metrics': None, 'config': None}
        parsed = json.loads(format_json(result))
        assert parsed['metrics']['trade_count'] == 0

    def test_none_metrics_defaults_to_zero_win_rate(self):
        """metrics=None → win_rate 기본값이 0.0이어야 한다."""
        result = {'status': 'success', 'metrics': None, 'config': None}
        parsed = json.loads(format_json(result))
        assert parsed['metrics']['win_rate'] == pytest.approx(0.0)

    def test_empty_metrics_defaults_to_zero_cagr(self):
        """metrics={} → cagr 기본값이 0.0이어야 한다."""
        result = {'status': 'success', 'metrics': {}, 'config': {}}
        parsed = json.loads(format_json(result))
        assert parsed['metrics']['cagr'] == pytest.approx(0.0)

    def test_empty_metrics_bootstrap_defaults_to_zero(self):
        """metrics={} → bootstrap avg/ci_lower/ci_upper 기본값이 0.0이어야 한다."""
        result = {'status': 'success', 'metrics': {}, 'config': {}}
        parsed = json.loads(format_json(result))
        b = parsed['bootstrap']
        assert b['avg_return'] == pytest.approx(0.0)
        assert b['ci_lower'] == pytest.approx(0.0)
        assert b['ci_upper'] == pytest.approx(0.0)

    def test_none_config_defaults_to_empty_strings(self):
        """config=None → buy_strategy / sell_strategy / start_date / end_date 가 빈 문자열이어야 한다."""
        result = {'status': 'success', 'metrics': {}, 'config': None}
        parsed = json.loads(format_json(result))
        c = parsed['config']
        assert c['buy_strategy'] == ''
        assert c['sell_strategy'] == ''
        assert c['start_date'] == ''
        assert c['end_date'] == ''

    def test_partial_metrics_missing_keys_default_to_zero(self):
        """일부 metrics 키만 있을 때 나머지는 기본값 0이어야 한다."""
        result = {
            'status': 'success',
            'metrics': {'trade_count': 10},
            'config': {},
        }
        parsed = json.loads(format_json(result))
        assert parsed['metrics']['trade_count'] == 10
        assert parsed['metrics']['win_rate'] == pytest.approx(0.0)
        assert parsed['metrics']['mdd_pct'] == pytest.approx(0.0)


# ============================================================
# format_text() — 성공 결과
# ============================================================

class TestFormatTextSuccess:
    """format_text()가 성공 결과를 한국어 레이블이 포함된 텍스트로 포매팅하는지 검증."""

    def test_contains_header(self, sample_result_success):
        """출력에 'STOM Backtest Result' 헤더가 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert 'STOM Backtest Result' in output

    def test_contains_trade_count_label(self, sample_result_success):
        """출력에 '매매횟수' 레이블이 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert '매매횟수' in output

    def test_contains_win_rate_label(self, sample_result_success):
        """출력에 '승률' 레이블이 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert '승률' in output

    def test_contains_cagr_label(self, sample_result_success):
        """출력에 'CAGR' 레이블이 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert 'CAGR' in output

    def test_contains_mdd_label(self, sample_result_success):
        """출력에 'MDD' 레이블이 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert 'MDD' in output

    def test_contains_tpi_label(self, sample_result_success):
        """출력에 'TPI' 레이블이 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert 'TPI' in output

    def test_contains_bootstrap_label(self, sample_result_success):
        """출력에 'Bootstrap' 레이블이 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert 'Bootstrap' in output

    def test_trade_count_value_rendered(self, sample_result_success):
        """trade_count 값 150이 출력 문자열에 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert '150' in output

    def test_win_rate_value_rendered(self, sample_result_success):
        """win_rate 값 55.30이 출력 문자열에 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert '55.30' in output

    def test_separator_lines_present(self, sample_result_success):
        """구분선('==='와 '---')이 출력에 포함되어야 한다."""
        output = format_text(sample_result_success)
        assert '=' * 10 in output
        assert '-' * 10 in output


# ============================================================
# format_text() — 에러 결과
# ============================================================

class TestFormatTextError:
    """format_text()가 에러 결과를 'ERROR: ...' 형식으로 반환하는지 검증."""

    def test_returns_error_prefix(self, sample_result_error):
        """에러 결과는 'ERROR: '로 시작해야 한다."""
        output = format_text(sample_result_error)
        assert output.startswith('ERROR:')

    def test_error_message_included(self, sample_result_error):
        """에러 메시지 내용이 출력에 포함되어야 한다."""
        output = format_text(sample_result_error)
        assert '매수 전략이 DB에 없습니다.' in output

    def test_error_output_is_single_line(self, sample_result_error):
        """에러 출력은 단일 라인 문자열이어야 한다 (헤더/구분선 없음)."""
        output = format_text(sample_result_error)
        assert '\n' not in output

    def test_error_without_message_uses_default(self):
        """message 키가 없는 에러 결과는 'Unknown error' 기본값을 사용한다."""
        result = {'status': 'error'}
        output = format_text(result)
        assert 'Unknown error' in output


# ============================================================
# format_text() — 빈/None metrics 기본값
# ============================================================

class TestFormatTextDefaults:
    """metrics가 None 또는 빈 dict일 때 format_text()가 기본값 0으로 렌더링하는지 검증."""

    def test_none_metrics_does_not_raise(self):
        """metrics=None → format_text()가 예외 없이 실행되어야 한다."""
        result = {'status': 'success', 'metrics': None}
        output = format_text(result)
        assert 'STOM Backtest Result' in output

    def test_none_metrics_renders_zero_trade_count(self):
        """metrics=None → trade_count가 0으로 렌더링되어야 한다."""
        result = {'status': 'success', 'metrics': None}
        output = format_text(result)
        assert '0' in output

    def test_empty_metrics_does_not_raise(self):
        """metrics={} → format_text()가 예외 없이 실행되어야 한다."""
        result = {'status': 'success', 'metrics': {}}
        output = format_text(result)
        assert 'STOM Backtest Result' in output
