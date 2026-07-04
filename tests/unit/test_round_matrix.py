"""T3.4 라운드 교차비교 매트릭스 단위 테스트.

핵심 검증:
  - build_round_comparison_matrix: 합성 라운드 결과에서 후보×지표
    (profit/MDD/trades/win_rate/슬리피지 tick2/랭크/레인/변이축) 수치와
    부모 대비 delta(변이 귀속), baseline 대비 개선 후보 수가 정확하다.
  - render_matrix_md: 사람용 Markdown 렌더 (랭크순 정렬, 미확보 '-').
  - research_loop opt-in 배선: round_matrix_enabled=False(기본)면 결과
    스키마 불변(round_matrix 키 없음), True면 JSON+md 아티팩트 저장 후
    결과에는 경로+요약(개선 후보 수)만 additive로 남는다(본문 비영속).
  - 저장 실패/디렉터리 미해결은 진행을 막지 않고 error만 기록한다.
"""

from dataclasses import asdict, fields
import json
import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from cli import research_loop  # noqa: E402
from cli.research_compare import (  # noqa: E402
    ROUND_MATRIX_AUTHORITY,
    ROUND_MATRIX_SCHEMA_VERSION,
    build_round_comparison_matrix,
    render_matrix_md,
)
from cli.research_loop import ResearchLoopConfig, run_research_iteration  # noqa: E402

PARENT_BUY_CODE = "if 현재가 > 시가 and 거래대금 > 10000:\n    self.Buy()"
PARENT_SELL_CODE = "if 수익률 < -1:\n    self.Sell()"
CREATED_AT = "2026-07-02T09:00:00"


# ------------------------------------------------------ synthetic round


def _candidate(name, **overrides):
    candidate = {
        'strategy_name': name,
        'status': 'ok',
        'rank': None,
        'selected_as_best': False,
        'research_lane': 'repair',
        'mutation_axis': 'turnover_min 1.5 -> 3.0',
        'mutation_param': 'turnover_min',
        'mutation_from': 1.5,
        'mutation_to': 3.0,
        'comparison': {
            'baseline_summary': {
                'trade_count': 10,
                'win_rate': 0.5,
                'total_profit': 1000000.0,
            },
            'candidate_summary': {
                'trade_count': 8,
                'win_rate': 0.625,
                'total_profit': 1500000.0,
            },
        },
        'candidate_result': {'status': 'success', 'metrics': {'mdd': 7.5}},
        'promotion': {'status': 'ok', 'passed': True, 'score': 2.0},
    }
    candidate.update(overrides)
    return candidate


def _round_result(candidates, *, name='MatrixRound', baseline_metrics=None):
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'strategy_name': name,
        'baseline_result': {
            'status': 'success',
            'metrics': {'mdd': 5.0} if baseline_metrics is None else baseline_metrics,
        },
        'candidates': candidates,
    }


# ------------------------------------------------------ matrix numbers


def test_matrix_numeric_cells_and_improved_count():
    winner = _candidate('cand_1', rank=1, selected_as_best=True)
    loser = _candidate(
        'cand_2',
        rank=2,
        research_lane='discovery',
        comparison={
            'baseline_summary': {'trade_count': 10, 'win_rate': 0.5, 'total_profit': 1000000.0},
            'candidate_summary': {'trade_count': 12, 'win_rate': 0.25, 'total_profit': 800000.0},
        },
        candidate_result={'status': 'success', 'metrics': {'mdd': 9.0}},
        promotion={'status': 'ok', 'passed': False, 'score': -1.0},
    )
    matrix = build_round_comparison_matrix(_round_result([winner, loser]))

    assert matrix['schema_version'] == ROUND_MATRIX_SCHEMA_VERSION
    assert matrix['authority'] == ROUND_MATRIX_AUTHORITY
    assert matrix['strategy_name'] == 'MatrixRound'
    assert matrix['candidate_count'] == 2
    assert matrix['evaluated_count'] == 2
    assert matrix['improved_over_baseline_count'] == 1
    assert matrix['baseline'] == {
        'profit': 1000000.0,
        'mdd': 5.0,
        'trade_count': 10.0,
        'win_rate': 0.5,
    }

    row_1, row_2 = matrix['rows']
    assert row_1['candidate_id'] == 'cand_1'
    assert row_1['rank'] == 1
    assert row_1['selected_as_best'] is True
    assert row_1['lane'] == 'repair'
    assert row_1['metrics'] == {
        'profit': 1500000.0,
        'mdd': 7.5,
        'trade_count': 8.0,
        'win_rate': 0.625,
        'slippage_tick2_profit': None,
        'slippage_tick2_retention': None,
    }
    assert row_1['delta_vs_parent'] == {
        'delta_profit': 500000.0,
        'delta_mdd': 2.5,
        'delta_trades': -2.0,
        'delta_win_rate': 0.125,
    }
    assert row_1['promotion_passed'] is True
    assert row_1['improved_over_baseline'] is True

    assert row_2['candidate_id'] == 'cand_2'
    assert row_2['lane'] == 'discovery'
    assert row_2['delta_vs_parent']['delta_profit'] == -200000.0
    assert row_2['delta_vs_parent']['delta_mdd'] == 4.0
    assert row_2['promotion_passed'] is False
    assert row_2['improved_over_baseline'] is False


def test_matrix_resolves_production_mdd_pct_key():
    # 실 컨트롤러 run metrics 는 'mdd_pct'(cli/runner.py) 키를 쓴다 —
    # 합성 키('mdd')만 조회하면 실 런에서 MDD 셀이 전부 미확보(None)가 된다.
    candidate = _candidate(
        'cand_prod',
        rank=1,
        candidate_result={'status': 'success', 'metrics': {'mdd_pct': 7.5}},
    )
    matrix = build_round_comparison_matrix(
        _round_result([candidate], baseline_metrics={'mdd_pct': 5.0})
    )

    assert matrix['baseline']['mdd'] == 5.0
    row = matrix['rows'][0]
    assert row['metrics']['mdd'] == 7.5
    assert row['delta_vs_parent']['delta_mdd'] == 2.5


def test_matrix_mutation_attribution():
    candidate = _candidate('cand_axis', rank=1)
    matrix = build_round_comparison_matrix(_round_result([candidate]))
    mutation = matrix['rows'][0]['mutation']
    assert mutation == {
        'axis': 'turnover_min 1.5 -> 3.0',
        'param': 'turnover_min',
        'from_value': 1.5,
        'to_value': 3.0,
    }


def test_matrix_mutation_axis_nested_container_lookup():
    candidate = _candidate(
        'cand_nested',
        rank=1,
        mutation_axis=None,
        mutation_param=None,
        research_contract={'mutation_axis': 'nested-axis', 'mutation_param': 'nested-param'},
    )
    matrix = build_round_comparison_matrix(_round_result([candidate]))
    mutation = matrix['rows'][0]['mutation']
    assert mutation['axis'] == 'nested-axis'
    assert mutation['param'] == 'nested-param'


def test_matrix_slippage_tick2_optional():
    with_slippage = _candidate(
        'cand_slip',
        rank=1,
        slippage_profiles={
            'schema_version': 1,
            'authority': 'advisory_only',
            'profiles': {
                'tick0': {'tick': 0, 'total_profit': 1500000.0, 'profit_retention_ratio': 1.0},
                'tick2': {'tick': 2, 'total_profit': 1200000.0, 'profit_retention_ratio': 0.8},
            },
        },
    )
    without_slippage = _candidate('cand_plain', rank=2)
    matrix = build_round_comparison_matrix(_round_result([with_slippage, without_slippage]))

    assert matrix['rows'][0]['metrics']['slippage_tick2_profit'] == 1200000.0
    assert matrix['rows'][0]['metrics']['slippage_tick2_retention'] == 0.8
    assert matrix['rows'][1]['metrics']['slippage_tick2_profit'] is None
    assert matrix['rows'][1]['metrics']['slippage_tick2_retention'] is None


def test_matrix_unevaluated_candidate_not_counted_and_missing_values_are_none():
    failed = _candidate(
        'cand_failed',
        status='error',
        comparison={},
        candidate_result=None,
        promotion=None,
    )
    matrix = build_round_comparison_matrix(
        {
            'strategy_name': 'MatrixRound',
            'baseline_result': None,
            'candidates': [failed, 'not-a-dict'],
        }
    )
    assert matrix['candidate_count'] == 1
    assert matrix['evaluated_count'] == 0
    assert matrix['improved_over_baseline_count'] == 0
    row = matrix['rows'][0]
    assert row['evaluated'] is False
    assert row['improved_over_baseline'] is False
    assert row['metrics']['profit'] is None
    assert row['delta_vs_parent'] == {
        'delta_profit': None,
        'delta_mdd': None,
        'delta_trades': None,
        'delta_win_rate': None,
    }
    # baseline_result/비교 요약이 전무하면 baseline 블록도 미확보(None).
    assert matrix['baseline'] == {'profit': None, 'mdd': None, 'trade_count': None, 'win_rate': None}


def test_matrix_empty_round_result_is_safe():
    matrix = build_round_comparison_matrix({})
    assert matrix['candidate_count'] == 0
    assert matrix['evaluated_count'] == 0
    assert matrix['improved_over_baseline_count'] == 0
    assert matrix['rows'] == []


# ------------------------------------------------------ markdown render


def test_render_matrix_md_orders_by_rank_and_formats_missing_as_dash():
    unranked = _candidate('cand_unranked', status='error', rank=None, comparison={}, candidate_result=None)
    second = _candidate(
        'cand_second',
        rank=2,
        comparison={
            'baseline_summary': {'trade_count': 10, 'win_rate': 0.5, 'total_profit': 1000000.0},
            'candidate_summary': {'trade_count': 12, 'win_rate': 0.25, 'total_profit': 800000.0},
        },
    )
    best = _candidate('cand_best', rank=1, selected_as_best=True)
    matrix = build_round_comparison_matrix(_round_result([unranked, second, best]))
    rendered = render_matrix_md(matrix)

    assert rendered.startswith('# 라운드 교차비교 매트릭스: MatrixRound')
    assert '- baseline 대비 개선 후보 수: 1' in rendered
    assert '- 후보 수: 3 (평가 완료 2)' in rendered
    assert 'baseline: profit=1000000' in rendered
    assert '**cand_best**' in rendered
    assert rendered.endswith('\n')

    lines = rendered.splitlines()
    table_rows = [line for line in lines if line.startswith('| ') and '후보' not in line and '---' not in line]
    assert len(table_rows) == 3
    # 랭크순 정렬: rank 1 → rank 2 → 무랭크(실패 후보)는 마지막.
    assert 'cand_best' in table_rows[0]
    assert 'cand_second' in table_rows[1]
    assert 'cand_unranked' in table_rows[2]
    # 실패 후보의 미확보 지표는 '-' 렌더.
    assert '| - |' in table_rows[2]


def test_render_matrix_md_tolerates_non_dict_input():
    rendered = render_matrix_md(None)
    assert rendered.startswith('# 라운드 교차비교 매트릭스: (unnamed)')


# ------------------------------------------------------ config fields


def test_research_loop_config_round_matrix_fields_default_off():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'round_matrix_enabled' in names
    assert 'round_matrix_output_dir' in names

    config = ResearchLoopConfig()
    assert config.round_matrix_enabled is False
    assert config.round_matrix_output_dir == ''

    snapshot = asdict(config)
    assert snapshot['round_matrix_enabled'] is False
    assert snapshot['round_matrix_output_dir'] == ''


# ------------------------------------------------------ artifact writer


def test_write_round_matrix_artifacts_off_returns_none():
    payload = _round_result([_candidate('cand_1', rank=1, selected_as_best=True)])
    assert research_loop._write_round_matrix_artifacts(ResearchLoopConfig(), payload) is None


def test_write_round_matrix_artifacts_creates_json_and_md(tmp_path):
    output_dir = tmp_path / 'artifacts'
    config = ResearchLoopConfig(
        name='Matrix Round/1',
        round_matrix_enabled=True,
        round_matrix_output_dir=str(output_dir),
    )
    payload = _round_result(
        [
            _candidate('cand_1', rank=1, selected_as_best=True),
            _candidate(
                'cand_2',
                rank=2,
                comparison={
                    'baseline_summary': {'trade_count': 10, 'win_rate': 0.5, 'total_profit': 1000000.0},
                    'candidate_summary': {'trade_count': 12, 'win_rate': 0.25, 'total_profit': 800000.0},
                },
            ),
        ],
        name='Matrix Round/1',
    )
    summary = research_loop._write_round_matrix_artifacts(config, payload)

    assert summary['status'] == 'written'
    assert summary['error'] == ''
    assert summary['candidate_count'] == 2
    assert summary['improved_over_baseline_count'] == 1
    assert summary['authority'] == 'research_observability_only'
    # 요약에는 매트릭스 본문이 없다(경로+수치만).
    assert 'rows' not in summary

    json_path = output_dir / 'Matrix_Round_1_round_matrix.json'
    md_path = output_dir / 'Matrix_Round_1_round_matrix.md'
    assert summary['json_path'] == str(json_path)
    assert summary['md_path'] == str(md_path)
    assert json_path.is_file()
    assert md_path.is_file()

    saved = json.loads(json_path.read_text(encoding='utf-8'))
    assert saved['schema_version'] == ROUND_MATRIX_SCHEMA_VERSION
    assert saved['improved_over_baseline_count'] == 1
    assert [row['candidate_id'] for row in saved['rows']] == ['cand_1', 'cand_2']
    assert md_path.read_text(encoding='utf-8').startswith('# 라운드 교차비교 매트릭스')


def test_write_round_matrix_artifacts_falls_back_to_runtime_output_dir(tmp_path):
    runtime_path = tmp_path / 'run' / 'runtime.json'
    config = ResearchLoopConfig(
        name='RuntimeFallback',
        round_matrix_enabled=True,
        runtime_output_path=str(runtime_path),
    )
    payload = _round_result([_candidate('cand_1', rank=1, selected_as_best=True)])
    summary = research_loop._write_round_matrix_artifacts(config, payload)

    assert summary['status'] == 'written'
    assert (tmp_path / 'run' / 'RuntimeFallback_round_matrix.json').is_file()
    assert (tmp_path / 'run' / 'RuntimeFallback_round_matrix.md').is_file()


def test_write_round_matrix_artifacts_skips_when_no_output_dir_resolvable():
    config = ResearchLoopConfig(round_matrix_enabled=True)
    payload = _round_result([_candidate('cand_1', rank=1)])
    summary = research_loop._write_round_matrix_artifacts(config, payload)

    assert summary['status'] == 'skipped'
    assert summary['error'] == 'round_matrix_output_dir_unresolved'
    assert summary['json_path'] == ''
    assert summary['md_path'] == ''


def test_write_round_matrix_artifacts_write_error_is_nonblocking(tmp_path):
    blocker = tmp_path / 'blocked'
    blocker.write_text('not a directory', encoding='utf-8')
    config = ResearchLoopConfig(
        name='Blocked',
        round_matrix_enabled=True,
        round_matrix_output_dir=str(blocker),
    )
    payload = _round_result([_candidate('cand_1', rank=1)])
    summary = research_loop._write_round_matrix_artifacts(config, payload)

    assert summary['status'] == 'error'
    assert summary['error'].startswith('round_matrix_write_error:')


# ------------------------------------------------- iteration wiring


class DummyController:
    def __init__(self, baseline_csv=None, metrics=None):
        self.baseline_csv = baseline_csv
        self.metrics = metrics or {}
        self.runs = []

    def run(self, config_dict):
        self.runs.append(config_dict)
        result = {'status': 'success', 'metrics': dict(self.metrics)}
        if self.baseline_csv is not None:
            result['csv_path'] = self.baseline_csv
        return result


def _write_trade_csv(path):
    pd.DataFrame([
        {
            '종목명': 'A',
            '매수시간': 202501010900,
            '매도시간': 202501010910,
            '매수가': 1000,
            '수익률': -1.0,
            '수익금': -1000,
            'R_MFE': 0.2,
            'R_MAE': -2.0,
        },
    ]).to_csv(path, index=False, encoding='utf-8-sig')


def _config(**overrides):
    base = dict(
        name='RoundMatrixWiring',
        base_buy_strategy='BaseBuy',
        sell_strategy='BaseSell',
        is_tick=False,
        run_candidate=False,
        run_candidates=True,
        candidate_count=4,
        condition_discovery_process='process-research',
        condition_discovery_preset='research',
    )
    base.update(overrides)
    return ResearchLoopConfig(**base)


def _fallback_expression_result(count=4):
    return {
        'status': 'ok',
        'expressions': ['체결강도 < 90', '등락율 < 5', '거래대금 > 1000', '회전율 > 1'][:count],
        'selected_candidates': [
            {'source': 'quantile', 'feature': f'B_f{index}'} for index in range(count)
        ],
        'candidate_count': count,
    }


def _patch_common(monkeypatch):
    analysis = {
        'status': 'ok',
        'recommended_candidates': [{'feature': 'B_체결강도'}],
        'created_at': CREATED_AT,
    }
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *a, **k: dict(analysis))

    def fake_load(db_path, name, strategy_type):
        codes = {'BaseBuy': PARENT_BUY_CODE, 'BaseSell': PARENT_SELL_CODE}
        if name in codes:
            return {'status': 'ok', 'code': codes[name], 'name': name}
        return {'status': 'error', 'message': 'strategy not found', 'name': name}

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)

    def fake_annotate(candidates, *a, **k):
        return [
            {
                **candidate,
                'retention_estimate': {'estimated_retention': 1.0},
                'retention_filter_passed': True,
                'retention_fallback_used': False,
            }
            for candidate in candidates
        ]

    monkeypatch.setattr(research_loop, 'annotate_candidate_retention', fake_annotate)
    monkeypatch.setattr(
        research_loop,
        'select_retention_aware_candidates',
        lambda candidates, **k: (candidates, {'status': 'ok', 'selected_count': len(candidates)}),
    )
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *a, **k: {'status': 'ok'},
    )
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda *a, **k: _fallback_expression_result(),
    )


def _install_fake_execute(monkeypatch, executed_specs):
    comparison = {
        'baseline_summary': {'trade_count': 10, 'win_rate': 0.5, 'total_profit': 1000000.0},
        'candidate_summary': {'trade_count': 8, 'win_rate': 0.625, 'total_profit': 1500000.0},
        'trade_count_retention': 0.8,
    }

    def fake_execute(config, spec, controller, baseline_csv):
        executed_specs.append(dict(spec))
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            **{key: spec[key] for key in research_loop._RESEARCH_METADATA_KEYS if key in spec},
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': baseline_csv,
            'candidate_result': {'status': 'success', 'metrics': {'mdd': 7.5, 'trade_count': 8}},
            'comparison': {
                key: (dict(value) if isinstance(value, dict) else value)
                for key, value in comparison.items()
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': 2.0},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)


def test_iteration_round_matrix_off_keeps_result_schema(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    executed = []
    _install_fake_execute(monkeypatch, executed)

    result = run_research_iteration(
        _config(baseline_csv=str(baseline)),
        DummyController(),
    )

    assert result['status'] == 'ok'
    # opt-in OFF(기본): additive 키 자체가 없어야 한다(스키마 불변).
    assert 'round_matrix' not in result
    assert not list(tmp_path.glob('**/*_round_matrix.*'))


def test_iteration_round_matrix_writes_artifacts_and_keeps_summary_only(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    executed = []
    _install_fake_execute(monkeypatch, executed)
    output_dir = tmp_path / 'matrix'

    result = run_research_iteration(
        _config(
            baseline_csv=str(baseline),
            round_matrix_enabled=True,
            round_matrix_output_dir=str(output_dir),
        ),
        DummyController(),
    )

    assert result['status'] == 'ok'
    summary = result['round_matrix']
    assert summary['status'] == 'written'
    assert summary['candidate_count'] == 4
    # 모든 후보의 comparison delta_profit(+500000)이 양수 → 전원 개선.
    assert summary['improved_over_baseline_count'] == 4
    assert 'rows' not in summary  # 본문 비영속 — 경로+요약만.

    json_path = output_dir / 'RoundMatrixWiring_round_matrix.json'
    md_path = output_dir / 'RoundMatrixWiring_round_matrix.md'
    assert summary['json_path'] == str(json_path)
    assert summary['md_path'] == str(md_path)

    saved = json.loads(json_path.read_text(encoding='utf-8'))
    assert saved['candidate_count'] == 4
    assert saved['improved_over_baseline_count'] == 4
    assert {row['lane'] for row in saved['rows']} == {'repair', 'discovery'}
    best_rows = [row for row in saved['rows'] if row['selected_as_best']]
    assert len(best_rows) == 1
    assert best_rows[0]['rank'] == 1
    assert md_path.read_text(encoding='utf-8').startswith('# 라운드 교차비교 매트릭스')
