"""Stage 4: 서브커맨드 통합 테스트 — formula, strategy 서브커맨드."""
import json
import os
import sys
import sqlite3
from unittest.mock import patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from cli.subcommands import create_subcommand_parser, handle_subcommand  # noqa: E402


def test_discovery_research_parser_accepts_existing_strategy_inputs():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearch01',
        '--input', 'baseline.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--timeframe', 'min',
        '--run-candidate',
    ])
    assert args.discovery_action == 'research'
    assert args.name == 'AutoResearch01'
    assert args.input_file == 'baseline.csv'
    assert args.base_buy_strategy == 'BaseBuy'
    assert args.sell == 'BaseSell'
    assert args.timeframe == 'min'
    assert args.run_candidate is True


def test_discovery_research_parser_accepts_missing_input():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearch01',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
    ])
    assert args.discovery_action == 'research'
    assert args.name == 'AutoResearch01'
    assert args.input_file is None
    assert args.base_buy_strategy == 'BaseBuy'
    assert args.sell == 'BaseSell'
    assert args.top_n == 1
    assert args.run_candidate is False


def test_discovery_research_handler_calls_controller(capsys):
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearch01'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearch01',
            '--input', 'baseline.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--timeframe', 'min',
        ])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'AutoResearch01' in out
    kwargs = mock.call_args.args[0]
    assert kwargs['name'] == 'AutoResearch01'
    assert kwargs['baseline_csv'] == 'baseline.csv'
    assert kwargs['base_buy_strategy'] == 'BaseBuy'
    assert kwargs['sell_strategy'] == 'BaseSell'
    assert kwargs['start_date'] == 20250101
    assert kwargs['end_date'] == 20250131
    assert kwargs['is_tick'] is False
    assert kwargs['engine_count'] == 4
    assert kwargs['top_n'] == 1
    assert kwargs['run_candidate'] is False


def test_discovery_research_handler_accepts_missing_input():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearch01'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearch01',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidate',
        ])
    assert exit_code == 0
    kwargs = mock.call_args.args[0]
    assert kwargs['baseline_csv'] is None
    assert kwargs['base_buy_strategy'] == 'BaseBuy'
    assert kwargs['sell_strategy'] == 'BaseSell'
    assert kwargs['start_date'] == 20250101
    assert kwargs['end_date'] == 20250131
    assert kwargs['is_tick'] is True
    assert kwargs['engine_count'] == 4
    assert kwargs['top_n'] == 1
    assert kwargs['run_candidate'] is True


def test_discovery_research_parser_accepts_candidate_runtime_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearchRuntime',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidate',
        '--candidate-start', '20250102',
        '--candidate-end', '20250103',
        '--candidate-timeout', '300',
        '--candidate-plan-only',
        '--keep-failed-candidate',
    ])

    assert args.candidate_start == 20250102
    assert args.candidate_end == 20250103
    assert args.candidate_timeout == 300
    assert args.candidate_plan_only is True
    assert args.keep_failed_candidate is True


def test_discovery_research_parser_accepts_iteration_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearchIteration',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidates',
        '--candidate-count', '5',
        '--candidate-name-prefix', 'ResearchBatch',
        '--cleanup-best-candidate',
        '--keep-loser-candidates',
    ])

    assert args.run_candidates is True
    assert args.candidate_count == 5
    assert args.candidate_name_prefix == 'ResearchBatch'
    assert args.cleanup_best_candidate is True
    assert args.keep_loser_candidates is True


def test_discovery_research_parser_accepts_retention_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'RetentionResearch',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidates',
        '--min-estimated-retention', '0.5',
        '--no-retention-fallback',
        '--no-retention-penalty',
        '--candidate-pool-multiplier', '4',
    ])

    assert args.min_estimated_retention == 0.5
    assert args.allow_retention_fallback is False
    assert args.use_retention_penalty is False
    assert args.candidate_pool_multiplier == 4


def test_discovery_research_parser_accepts_score_reference_csv():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'ScoreReferenceResearch',
        '--input', 'cand003.csv',
        '--score-reference-csv', 'wide.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidates',
    ])

    assert args.score_reference_csv == 'wide.csv'


def test_discovery_research_parser_rejects_conflicting_candidate_modes():
    parser = create_subcommand_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            'discovery', 'research',
            'AutoResearchConflict',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidate',
            '--run-candidates',
        ])


def test_discovery_research_handler_passes_candidate_runtime_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearchRuntime'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearchRuntime',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--candidate-start', '20250102',
            '--candidate-end', '20250103',
            '--candidate-timeout', '300',
            '--candidate-plan-only',
            '--keep-failed-candidate',
        ])

    assert exit_code == 0
    payload = mock.call_args.args[0]
    assert payload['candidate_start_date'] == 20250102
    assert payload['candidate_end_date'] == 20250103
    assert payload['candidate_timeout'] == 300
    assert payload['candidate_plan_only'] is True
    assert payload['keep_failed_candidate'] is True


def test_discovery_research_handler_passes_iteration_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'phase': 'candidates_evaluated'}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearchIteration',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidates',
            '--candidate-count', '5',
            '--candidate-name-prefix', 'ResearchBatch',
            '--cleanup-best-candidate',
            '--keep-loser-candidates',
        ])

    payload = mock.call_args.args[0]
    assert exit_code == 0
    assert payload['run_candidates'] is True
    assert payload['candidate_count'] == 5
    assert payload['candidate_name_prefix'] == 'ResearchBatch'
    assert payload['cleanup_best_candidate'] is True
    assert payload['keep_loser_candidates'] is True


def test_discovery_research_handler_passes_retention_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'RetentionResearch',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidates',
            '--min-estimated-retention', '0.5',
            '--no-retention-fallback',
            '--no-retention-penalty',
            '--candidate-pool-multiplier', '4',
        ])

    payload = mock.call_args.args[0]
    assert exit_code == 0
    assert payload['min_estimated_retention'] == 0.5
    assert payload['allow_retention_fallback'] is False
    assert payload['use_retention_penalty'] is False
    assert payload['candidate_pool_multiplier'] == 4


def test_discovery_research_handler_passes_score_reference_csv():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'ScoreReferenceResearch',
            '--input', 'cand003.csv',
            '--score-reference-csv', 'wide.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidates',
        ])

    payload = mock.call_args.args[0]
    assert exit_code == 0
    assert payload['score_reference_csv'] == 'wide.csv'


def test_discovery_research_parser_accepts_iteration_v2_options():
    parser = create_subcommand_parser()

    args = parser.parse_args([
        'discovery', 'research', 'V2Run',
        '--input', 'baseline.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20251231',
        '--run-candidates',
        '--iteration-v2-mode', 'best_feature_mix',
        '--iteration-v2-best-candidate', 'WideV1RetentionCand5_20260422__cand003',
        '--iteration-v2-best-expression', '66.999 <= 시가총액 < 2_580',
        '--iteration-v2-primary-feature', 'B_시가총액',
        '--iteration-v2-secondary-features', 'B_체결강도,B_등락율',
        '--no-iteration-v2-secondary-only',
        '--iteration-v2-max-secondary-only', '0',
        '--iteration-v2-duplicate-retention-tolerance', '0.03',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix'
    assert args.iteration_v2_best_candidate == 'WideV1RetentionCand5_20260422__cand003'
    assert args.iteration_v2_best_expression == '66.999 <= 시가총액 < 2_580'
    assert args.iteration_v2_primary_feature == 'B_시가총액'
    assert args.iteration_v2_secondary_features == 'B_체결강도,B_등락율'
    assert args.iteration_v2_include_secondary_only is False
    assert args.iteration_v2_max_secondary_only == 0
    assert args.iteration_v2_duplicate_retention_tolerance == 0.03


def test_discovery_research_handler_passes_iteration_v2_options():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        result = handle_subcommand([
            'discovery', 'research', 'V2Run',
            '--input', 'baseline.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20251231',
            '--run-candidates',
            '--iteration-v2-mode', 'best_feature_mix',
            '--iteration-v2-best-candidate', 'cand003',
            '--iteration-v2-best-expression', '66.999 <= 시가총액 < 2_580',
            '--iteration-v2-primary-feature', 'B_시가총액',
            '--iteration-v2-secondary-features', 'B_체결강도,B_등락율',
        ])

    payload = mock.call_args.args[0]
    assert result == 0
    assert payload['iteration_v2_mode'] == 'best_feature_mix'
    assert payload['iteration_v2_best_candidate'] == 'cand003'
    assert payload['iteration_v2_best_expression'] == '66.999 <= 시가총액 < 2_580'
    assert payload['iteration_v2_primary_feature'] == 'B_시가총액'
    assert payload['iteration_v2_secondary_features'] == 'B_체결강도,B_등락율'


def test_discovery_research_parser_accepts_iteration_v2_mode_v3():
    parser = create_subcommand_parser()

    args = parser.parse_args([
        'discovery',
        'research',
        'WideV1IterationV3_20260423',
        '--input',
        'cand005.csv',
        '--score-reference-csv',
        'wide.csv',
        '--base-buy-strategy',
        'WideV1IterationV2_20260423__cand005',
        '--sell',
        'ResearchTest_Tick_S_090000_092800_Wide_20260419',
        '--start',
        '20250101',
        '--end',
        '20251231',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v3',
        '--iteration-v2-best-candidate',
        'WideV1IterationV2_20260423__cand005',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix_v3'
    assert args.candidate_count == 10
    assert args.score_reference_csv == 'wide.csv'


def test_discovery_research_handler_passes_iteration_v2_mode_v3():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        code = handle_subcommand([
            'discovery',
            'research',
            'WideV1IterationV3_20260423',
            '--input',
            'cand005.csv',
            '--score-reference-csv',
            'wide.csv',
            '--base-buy-strategy',
            'WideV1IterationV2_20260423__cand005',
            '--sell',
            'ResearchTest_Tick_S_090000_092800_Wide_20260419',
            '--start',
            '20250101',
            '--end',
            '20251231',
            '--run-candidates',
            '--candidate-count',
            '10',
            '--iteration-v2-mode',
            'best_feature_mix_v3',
            '--iteration-v2-best-candidate',
            'WideV1IterationV2_20260423__cand005',
            '--iteration-v2-best-expression',
            '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
            '--iteration-v2-secondary-features',
            'B_체결강도,B_등락율,B_당일거래대금',
        ])

    payload = mock.call_args.args[0]
    assert code == 0
    assert payload['iteration_v2_mode'] == 'best_feature_mix_v3'
    assert payload['candidate_count'] == 10
    assert payload['score_reference_csv'] == 'wide.csv'


def test_discovery_research_parser_accepts_iteration_v2_mode_v4():
    parser = create_subcommand_parser()

    args = parser.parse_args([
        'discovery',
        'research',
        'WideV1IterationV4_20260424',
        '--input',
        'cand005.csv',
        '--base-buy-strategy',
        'WideV1IterationV2_20260423__cand005',
        '--sell',
        'ResearchTest_Tick_S_090000_092800_Wide_20260419',
        '--start',
        '20250101',
        '--end',
        '20251231',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v4',
        '--iteration-v2-best-candidate',
        'WideV1IterationV2_20260423__cand005',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix_v4'
    assert args.candidate_count == 10


def test_discovery_research_handler_passes_iteration_v2_mode_v4():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        code = handle_subcommand([
            'discovery',
            'research',
            'WideV1IterationV4_20260424',
            '--input',
            'cand005.csv',
            '--base-buy-strategy',
            'WideV1IterationV2_20260423__cand005',
            '--sell',
            'ResearchTest_Tick_S_090000_092800_Wide_20260419',
            '--start',
            '20250101',
            '--end',
            '20251231',
            '--run-candidates',
            '--candidate-count',
            '10',
            '--iteration-v2-mode',
            'best_feature_mix_v4',
            '--iteration-v2-best-candidate',
            'WideV1IterationV2_20260423__cand005',
            '--iteration-v2-best-expression',
            '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
        ])

    payload = mock.call_args.args[0]
    assert code == 0
    assert payload['iteration_v2_mode'] == 'best_feature_mix_v4'
    assert payload['candidate_count'] == 10


def test_discovery_research_parser_accepts_iteration_v2_mode_v5():
    parser = create_subcommand_parser()

    args = parser.parse_args([
        'discovery',
        'research',
        'WideV1IterationV5_20260424',
        '--input',
        'cand005.csv',
        '--base-buy-strategy',
        'WideV1IterationV4_20260424__cand001',
        '--sell',
        'ResearchTest_Tick_S_090000_092800_Wide_20260419',
        '--start',
        '20250101',
        '--end',
        '20251231',
        '--run-candidates',
        '--candidate-count',
        '10',
        '--iteration-v2-mode',
        'best_feature_mix_v5',
        '--iteration-v2-best-candidate',
        'WideV1IterationV4_20260424__cand001',
        '--iteration-v2-best-expression',
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
    ])

    assert args.iteration_v2_mode == 'best_feature_mix_v5'
    assert args.candidate_count == 10


def test_discovery_research_handler_passes_iteration_v2_mode_v5():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        code = handle_subcommand([
            'discovery',
            'research',
            'WideV1IterationV5_20260424',
            '--input',
            'cand005.csv',
            '--base-buy-strategy',
            'WideV1IterationV4_20260424__cand001',
            '--sell',
            'ResearchTest_Tick_S_090000_092800_Wide_20260419',
            '--start',
            '20250101',
            '--end',
            '20251231',
            '--run-candidates',
            '--candidate-count',
            '10',
            '--iteration-v2-mode',
            'best_feature_mix_v5',
            '--iteration-v2-best-candidate',
            'WideV1IterationV4_20260424__cand001',
            '--iteration-v2-best-expression',
            '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
        ])

    payload = mock.call_args.args[0]
    assert code == 0
    assert payload['iteration_v2_mode'] == 'best_feature_mix_v5'
    assert payload['candidate_count'] == 10


def test_discovery_research_handler_returns_nonzero_on_error_status():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'error'}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearch01',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
        ])
    assert exit_code == 1


def test_discovery_research_parser_rejects_wfo_options():
    parser = create_subcommand_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            'discovery', 'research',
            'AutoResearchWfo',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-wfo',
        ])


def test_discovery_research_handler_payload_has_no_wfo_keys():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearch01'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearch01',
            '--input', 'baseline.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
        ])

    assert exit_code == 0
    payload = mock.call_args.args[0]
    assert 'run_wfo' not in payload
    assert 'train_window_days' not in payload
    assert 'param_space' not in payload


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
             patch('cli.formula.add_formula', return_value=err_result):
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

    def test_strategy_list_returns_json_error_when_lookup_fails(self):
        captured = []
        with patch('cli.config.list_strategies', side_effect=RuntimeError('strategy lookup failed')), \
             patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['strategy', 'list'])
        assert code == 1
        data = json.loads(captured[0])
        assert data == {'status': 'error', 'message': 'strategy lookup failed'}

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


class TestDiscoverySubcommand:

    def test_discovery_analyze_ok(self):
        mock_result = {'status': 'ok', 'recommended_candidates': []}
        with patch('cli.ai_controller.AIBacktestController.analyze_results', return_value=mock_result), \
             patch('builtins.print') as mock_print:
            code = handle_subcommand(['discovery', 'analyze', '--input', 'result.csv'])
        assert code == 0
        mock_print.assert_called_once()

    def test_discovery_ml_analyze_ok(self):
        mock_result = {'status': 'ok', 'top_features': []}
        with patch('cli.ai_controller.AIBacktestController.analyze_results_ml', return_value=mock_result), \
             patch('builtins.print') as mock_print:
            code = handle_subcommand(['discovery', 'ml-analyze', '--input', 'result.csv'])
        assert code == 0
        mock_print.assert_called_once()

    def test_discovery_generate_ok(self):
        mock_result = {'status': 'ok', 'candidate_count': 2, 'code': 'if B_등락율 <= 2: 매수 = False'}
        with patch('cli.ai_controller.AIBacktestController.generate_conditions', return_value=mock_result) as mock_gen, \
             patch('builtins.print') as mock_print:
            code = handle_subcommand([
                'discovery', 'generate', '--input', 'result.csv', '--top-n', '2',
                '--ml-feature-limit', '1', '--ml-top-n', '3', '--ml-n-splits', '2', '--ml-weight', '0.5'
            ])
        assert code == 0
        _, kwargs = mock_gen.call_args
        assert kwargs['ml_feature_limit'] == 1
        assert kwargs['ml_weight'] == 0.5
        mock_print.assert_called_once()

    def test_discovery_create_strategy_ok(self):
        mock_result = {'status': 'ok', 'strategy_result': {'status': 'ok', 'action': 'created'}}
        with patch('cli.ai_controller.AIBacktestController.create_strategy_from_analysis', return_value=mock_result) as mock_create, \
             patch('builtins.print') as mock_print:
            code = handle_subcommand([
                'discovery', 'create-strategy', 'Auto_B', '--input', 'result.csv',
                '--ml-feature-limit', '1', '--ml-weight', '0.5'
            ])
        assert code == 0
        _, kwargs = mock_create.call_args
        assert kwargs['ml_feature_limit'] == 1
        assert kwargs['ml_weight'] == 0.5
        mock_print.assert_called_once()

    def test_discovery_promote_returns_nonzero_when_not_promoted(self):
        mock_result = {'status': 'ok', 'promoted': False}
        with patch('cli.ai_controller.AIBacktestController.discover_and_promote_strategy', return_value=mock_result), \
             patch('builtins.print') as mock_print:
            code = handle_subcommand([
                'discovery', 'promote', 'Auto_B',
                '--input', 'result.csv',
                '--sell', 'BaseSell',
                '--start', '20240101',
                '--end', '20240630',
                '--train-window-days', '60',
                '--test-window-days', '20',
            ])
        assert code == 1
        mock_print.assert_called_once()

    def test_discovery_promote_ok(self):
        mock_result = {'status': 'ok', 'promoted': True}
        with patch('cli.ai_controller.AIBacktestController.discover_and_promote_strategy', return_value=mock_result) as mock_promote, \
             patch('builtins.print') as mock_print:
            code = handle_subcommand([
                'discovery', 'promote', 'Auto_B',
                '--input', 'result.csv',
                '--sell', 'BaseSell',
                '--start', '20240101',
                '--end', '20240630',
                '--train-window-days', '60',
                '--test-window-days', '20',
                '--ml-feature-limit', '1',
                '--ml-weight', '0.5',
                '--promotion-preset', 'conservative',
                '--report-json', 'report.json',
                '--report-md', 'report.md',
            ])
        assert code == 0
        _, kwargs = mock_promote.call_args
        dc = kwargs['discovery_config']
        assert dc.ml.feature_limit == 1
        assert dc.ml.weight == 0.5
        assert dc.promotion.preset == 'conservative'
        assert dc.output.report_json_path == 'report.json'
        assert dc.output.report_md_path == 'report.md'
        assert dc.promotion.auto_relax is False
        assert dc.promotion.criteria is not None
        mock_print.assert_called_once()

    def test_discovery_promote_with_auto_relax_and_base_buy_strategy(self):
        mock_result = {'status': 'ok', 'promoted': True}
        with patch('cli.ai_controller.AIBacktestController.discover_and_promote_strategy', return_value=mock_result) as mock_promote, \
             patch('builtins.print'):
            code = handle_subcommand([
                'discovery', 'promote', 'Auto_B',
                '--input', 'result.csv',
                '--sell', 'BaseSell',
                '--start', '20240101',
                '--end', '20240630',
                '--train-window-days', '60',
                '--test-window-days', '20',
                '--auto-relax',
                '--max-relax-steps', '5',
                '--base-buy-strategy', 'Min_B_Study_251227',
                '--promotion-preset', 'aggressive',
            ])
        assert code == 0
        _, kwargs = mock_promote.call_args
        dc = kwargs['discovery_config']
        assert dc.promotion.auto_relax is True
        assert dc.promotion.max_relax_steps == 5
        assert dc.promotion.criteria is None
        assert dc.promotion.preset == 'aggressive'
        assert kwargs['config_dict']['base_buy_strategy'] == 'Min_B_Study_251227'


class TestDbSubcommand:

    def test_db_check_json_returns_error_when_tick_diagnostic_errors(self):
        fake_diag = {
            'status': 'error',
            'path': 'tick.db',
            'size_bytes': 123,
            'table_count': 0,
            'is_symlink': False,
            'message': 'SQLite inspection failed: malformed database',
        }
        captured = []
        with patch('cli.data_bridge.check_tick_db', return_value=fake_diag), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=123), \
             patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['db', 'check', '--format', 'json'])
        assert code == 1
        data = json.loads(captured[0])
        assert data['status'] == 'error'
        assert data['databases']['stock_tick_back']['detail'] == fake_diag

    def test_db_check_text_marks_tick_db_as_error_and_prints_message(self):
        fake_diag = {
            'status': 'error',
            'path': 'tick.db',
            'size_bytes': 123,
            'table_count': 0,
            'is_symlink': False,
            'message': 'SQLite inspection failed: malformed database',
        }
        captured = []
        with patch('cli.data_bridge.check_tick_db', return_value=fake_diag), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=123), \
             patch('builtins.print', side_effect=lambda s: captured.append(s)):
            code = handle_subcommand(['db', 'check', '--format', 'text'])
        assert code == 1
        stock_tick_lines = [line for line in captured if 'stock_tick_back' in line]
        assert stock_tick_lines
        assert 'ERROR' in stock_tick_lines[0]
        assert any('malformed database' in line for line in captured)


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
            import stom_backtest
            result = stom_backtest.main()
        mock_handler.assert_called_once_with(['strategy', 'list'])
        assert result == 0

    def test_discovery_detected_in_main(self):
        """sys.argv[1]=='discovery' 이면 handle_subcommand가 호출된다."""
        with patch('sys.argv', ['stom_backtest.py', 'discovery', 'analyze', '--input', 'result.csv']), \
             patch('cli.subcommands.handle_subcommand', return_value=0) as mock_handler:
            import stom_backtest
            result = stom_backtest.main()
        mock_handler.assert_called_once_with(['discovery', 'analyze', '--input', 'result.csv'])
        assert result == 0

    def test_runtime_preflight_detected_in_main(self):
        with patch('sys.argv', ['stom_backtest.py', 'runtime-preflight',
                                '--buy', 'BuyWide', '--sell', 'SellWide',
                                '--start', '20250101', '--end', '20251231']), \
             patch('cli.subcommands.handle_subcommand', return_value=0) as mock_handler:
            import stom_backtest
            result = stom_backtest.main()
        mock_handler.assert_called_once_with(['runtime-preflight',
                                              '--buy', 'BuyWide', '--sell', 'SellWide',
                                              '--start', '20250101', '--end', '20251231'])
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

    def test_discovery_analyze_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args(['discovery', 'analyze', '--input', 'result.csv', '--quantiles', '4'])
        assert parsed.command == 'discovery'
        assert parsed.discovery_action == 'analyze'
        assert parsed.input_file == 'result.csv'
        assert parsed.quantiles == 4

    def test_discovery_promote_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args([
            'discovery', 'promote', 'Auto_B',
            '--input', 'result.csv',
            '--sell', 'BaseSell',
            '--start', '20240101',
            '--end', '20240630',
            '--train-window-days', '60',
            '--test-window-days', '20',
            '--param-space-json', '{"avg_time":[60,120]}',
            '--ml-feature-limit', '1',
            '--ml-weight', '0.5',
            '--promotion-preset', 'aggressive',
            '--report-json', 'report.json',
            '--report-md', 'report.md',
        ])
        assert parsed.command == 'discovery'
        assert parsed.discovery_action == 'promote'
        assert parsed.name == 'Auto_B'
        assert parsed.input_file == 'result.csv'
        assert parsed.param_space_json == '{"avg_time":[60,120]}'
        assert parsed.ml_feature_limit == 1
        assert parsed.ml_weight == 0.5
        assert parsed.promotion_preset == 'aggressive'
        assert parsed.report_json == 'report.json'
        assert parsed.report_md == 'report.md'
        assert parsed.auto_relax is False
        assert parsed.max_relax_steps == 3
        assert parsed.base_buy_strategy is None

    def test_discovery_promote_auto_relax_parsed(self):
        parser = create_subcommand_parser()
        parsed = parser.parse_args([
            'discovery', 'promote', 'Auto_B',
            '--input', 'result.csv',
            '--sell', 'BaseSell',
            '--start', '20240101',
            '--end', '20240630',
            '--train-window-days', '60',
            '--test-window-days', '20',
            '--auto-relax',
            '--max-relax-steps', '5',
            '--base-buy-strategy', 'Min_B_Study_251227',
        ])
        assert parsed.auto_relax is True
        assert parsed.max_relax_steps == 5
        assert parsed.base_buy_strategy == 'Min_B_Study_251227'


def test_runtime_preflight_parser_accepts_tick_inputs():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'runtime-preflight',
        '--buy', 'BuyWide',
        '--sell', 'SellWide',
        '--start', '20250101',
        '--end', '20251231',
        '--timeframe', 'tick',
        '--avg-time', '30',
        '--start-time', '90000',
        '--end-time', '92800',
        '--engines', '32',
        '--timeout', '900',
    ])

    assert args.command == 'runtime-preflight'
    assert args.buy == 'BuyWide'
    assert args.sell == 'SellWide'
    assert args.timeframe == 'tick'
    assert args.avg_time == '30'
    assert args.engines == 32
    assert args.timeout == 900


def test_runtime_preflight_handler_outputs_json(capsys):
    with patch('cli.runtime_preflight.run_runtime_preflight') as mock:
        mock.return_value = {
            'status': 'ok',
            'message': 'runtime preflight passed',
            'failed_checks': [],
            'runtime_profile': {'strategy_db_path': 'strategy.db'},
            'strategies': {},
            'config': {},
        }
        exit_code = handle_subcommand([
            'runtime-preflight',
            '--buy', 'BuyWide',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
            '--timeframe', 'tick',
            '--avg-time', '30',
            '--start-time', '90000',
            '--end-time', '92800',
            '--engines', '32',
            '--timeout', '900',
        ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['status'] == 'ok'
    config = mock.call_args.args[0]
    assert config.buy_strategy == 'BuyWide'
    assert config.sell_strategy == 'SellWide'
    assert config.start_date == 20250101
    assert config.end_date == 20251231
    assert config.is_tick is True
    assert config.avg_time == 30
    assert config.engine_count == 32
    assert config.timeout == 900


def test_runtime_preflight_handler_returns_error_code_on_failed_preflight(capsys):
    with patch('cli.runtime_preflight.run_runtime_preflight') as mock:
        mock.return_value = {
            'status': 'error',
            'message': 'runtime preflight failed',
            'failed_checks': ['buy_strategy'],
            'runtime_profile': {},
            'strategies': {},
            'config': {},
        }
        exit_code = handle_subcommand([
            'runtime-preflight',
            '--buy', 'BrokenBuy',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
        ])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['failed_checks'] == ['buy_strategy']


def test_runtime_preflight_handler_normalizes_multiple_avg_times(capsys):
    with patch('cli.runtime_preflight.run_runtime_preflight') as mock:
        mock.return_value = {
            'status': 'ok',
            'message': 'runtime preflight passed',
            'failed_checks': [],
            'runtime_profile': {},
            'strategies': {},
            'config': {},
        }
        exit_code = handle_subcommand([
            'runtime-preflight',
            '--buy', 'BuyWide',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
            '--avg-time', '60,120',
        ])

    assert exit_code == 0
    json.loads(capsys.readouterr().out)
    config = mock.call_args.args[0]
    assert config.avg_time == [60, 120]


def test_runtime_preflight_handler_returns_json_for_invalid_avg_time(capsys):
    exit_code = handle_subcommand([
        'runtime-preflight',
        '--buy', 'BuyWide',
        '--sell', 'SellWide',
        '--start', '20250101',
        '--end', '20251231',
        '--avg-time', 'abc',
    ])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['status'] == 'error'
    assert 'config' in payload['failed_checks']
    assert any('avg_time' in error for error in payload['validation_errors'])


def test_runtime_preflight_parser_constrains_divid_mode():
    parser = create_subcommand_parser()
    valid = parser.parse_args([
        'runtime-preflight',
        '--buy', 'BuyWide',
        '--sell', 'SellWide',
        '--start', '20250101',
        '--end', '20251231',
        '--divid-mode', '일자별 분류',
    ])
    assert valid.divid_mode == '일자별 분류'

    with pytest.raises(SystemExit):
        parser.parse_args([
            'runtime-preflight',
            '--buy', 'BuyWide',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
            '--divid-mode', 'invalid',
        ])


def test_runtime_preflight_handler_passes_optional_runtime_args(capsys):
    with patch('cli.runtime_preflight.run_runtime_preflight') as mock:
        mock.return_value = {
            'status': 'ok',
            'message': 'runtime preflight passed',
            'failed_checks': [],
            'runtime_profile': {},
            'strategies': {},
            'config': {},
        }
        exit_code = handle_subcommand([
            'runtime-preflight',
            '--buy', 'BuyWide',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
            '--timeframe', 'min',
            '--oms',
            '--blacklist',
            '--back-club',
            '--divid-mode', '한종목 로딩',
            '--one-code', 'A005930',
        ])

    assert exit_code == 0
    json.loads(capsys.readouterr().out)
    config = mock.call_args.args[0]
    assert config.is_tick is False
    assert config.oms is True
    assert config.blacklist is True
    assert config.back_club is True
    assert config.divid_mode == '한종목 로딩'
    assert config.one_code == 'A005930'
