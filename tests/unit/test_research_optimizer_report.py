from cli.research_optimizer_report import (
    render_optimizer_summary_markdown,
    write_optimizer_report,
)


def _result():
    return {
        'status': 'ok',
        'run_id': 'WideV2Run',
        'stop_reason': 'max_rounds_reached',
        'failed_round': None,
        'failure_phase': None,
        'failure_message': None,
        'requested_candidate_count': None,
        'selected_candidate_count': None,
        'completed_round_count': 2,
        'initial_seed': {
            'base_buy_strategy': 'WideV1Final_B_20260425',
            'source_baseline': 'WideV1Final_B_20260425',
            'seed_candidate': 'WideV1Final_B_20260425',
            'seed_expression': 'A > 0',
            'iteration_v2_mode': 'best_feature_mix_v5',
            'iteration_v2_primary_feature': 'B_primary',
            'iteration_v2_trade_amount_feature': 'B_trade_amount',
        },
        'rounds': [
            {
                'round_index': 1,
                'status': 'ok',
                'phase': 'candidates_evaluated',
                'source_candidate': 'WideV1Final_B_20260425',
                'round_best_candidate': {
                    'strategy_name': 'R1__cand001',
                    'expression': 'A > 1',
                },
            },
            {
                'round_index': 2,
                'status': 'ok',
                'phase': 'candidates_evaluated',
                'source_candidate': 'R1__cand001',
                'round_best_candidate': {
                    'strategy_name': 'R2__cand001',
                    'expression': 'A > 2',
                },
            },
        ],
        'leaderboard': [
            {
                'round_index': 1,
                'candidate_index': 1,
                'strategy_name': 'R1__cand001',
                'adjusted_score': 1.0,
                'promotion_score': 1.0,
                'promotion_passed': True,
                'selected_as_global_best': False,
            },
            {
                'round_index': 2,
                'candidate_index': 1,
                'strategy_name': 'R2__cand001',
                'adjusted_score': 2.0,
                'promotion_score': 2.0,
                'promotion_passed': True,
                'selected_as_global_best': True,
            },
        ],
        'final_best_candidate': {
            'round_index': 2,
            'candidate_index': 1,
            'strategy_name': 'R2__cand001',
            'expression': 'A > 2',
            'adjusted_score': 2.0,
        },
        'wfo_candidate': {
            'strategy_name': 'R2__cand001',
            'expression': 'A > 2',
            'source_round': 2,
            'source_candidate': 'R1__cand001',
            'reason_selected': 'global_best_leaderboard_entry',
            'next_command': '$writing-plans WideV2Run optimizer winner R2__cand001 WFO handoff plan 작성',
        },
    }


def test_render_optimizer_summary_markdown_contains_required_sections():
    markdown = render_optimizer_summary_markdown(_result())

    assert '# Wide v2 optimizer summary' in markdown
    assert '## Run configuration' in markdown
    assert '## Initial baseline' in markdown
    assert '## Round count' in markdown
    assert '## Round summary' in markdown
    assert '## Round best candidates' in markdown
    assert '## Global leaderboard' in markdown
    assert '## Stop reason' in markdown
    assert '## Final best candidate' in markdown
    assert '## WFO handoff' in markdown
    assert 'WFO was not run inside the optimizer loop.' in markdown
    assert 'The final candidate is a WFO candidate, not a live-trading approval.' in markdown
    assert 'round-by-round summary' in markdown
    assert 'final_best_candidate' in markdown
    assert 'WFO handoff candidate' in markdown
    assert 'next command for WFO validation plan' in markdown
    assert 'R2__cand001' in markdown


def test_render_optimizer_summary_markdown_includes_initial_seed_metadata():
    markdown = render_optimizer_summary_markdown(_result())

    assert 'WideV1Final_B_20260425' in markdown
    assert '- base_buy_strategy=WideV1Final_B_20260425' in markdown
    assert '- seed_expression=A > 0' in markdown
    assert '- iteration_v2_trade_amount_feature=B_trade_amount' in markdown
    assert '## Initial baseline' in markdown
    assert '- source_baseline=WideV1Final_B_20260425' in markdown


def test_render_optimizer_summary_markdown_includes_explicit_design_spec_labels():
    result = _result()
    markdown = render_optimizer_summary_markdown(result)

    assert '## Round count' in markdown
    assert '- completed_round_count=2' in markdown
    assert '## Round best candidates' in markdown
    assert 'R1__cand001' in markdown
    assert 'R2__cand001' in markdown
    assert '## Global leaderboard top candidates' in markdown
    assert '## Stop reason' in markdown
    assert '- stop_reason=max_rounds_reached' in markdown
    assert '- failed_round=' in markdown
    assert '- failure_phase=' in markdown
    assert '- failure_message=' in markdown
    assert '## WFO handoff' in markdown
    assert f"- next_command={result['wfo_candidate']['next_command']}" in markdown


def test_render_optimizer_summary_markdown_escapes_pipes_and_flattens_newlines():
    result = _result()
    result['initial_seed']['base_buy_strategy'] = 'Base|Line\nTwo'
    result['initial_seed']['seed_candidate'] = 'Seed|Candidate\nTwo'
    result['initial_seed']['seed_expression'] = 'Seed|Expr\nTwo'
    result['rounds'][0]['source_candidate'] = 'Round|Source\nTwo'
    result['rounds'][0]['round_best_candidate']['strategy_name'] = 'Round|Best\nTwo'
    result['rounds'][0]['round_best_candidate']['expression'] = 'Expr|Value\nTwo'
    result['leaderboard'][0]['strategy_name'] = 'Lead|Entry\nTwo'
    result['final_best_candidate']['expression'] = 'Final|Expr\nTwo'
    result['wfo_candidate']['next_command'] = 'plan|cmd\nnext'

    markdown = render_optimizer_summary_markdown(result)

    assert 'Base\\|Line Two' in markdown
    assert 'Seed\\|Candidate Two' in markdown
    assert 'Seed\\|Expr Two' in markdown
    assert 'Round\\|Source Two' in markdown
    assert 'Round\\|Best Two' in markdown
    assert 'Expr\\|Value Two' in markdown
    assert 'Lead\\|Entry Two' in markdown
    assert 'Final\\|Expr Two' in markdown
    assert 'plan\\|cmd next' in markdown
    assert 'Base|Line\nTwo' not in markdown
    assert 'Final|Expr\nTwo' not in markdown
    assert '## Global leaderboard top candidates' in markdown
    assert '## Round best candidates' in markdown


def test_render_optimizer_summary_markdown_includes_v5_recovery_metadata():
    result = _result()
    result.update({
        'initial_v4_candidate_count': 0,
        'recovery_attempted': True,
        'recovery_reason': 'v4_candidate_pool_empty',
        'recovery_family_counts': {
            'recovered_trade_feature': 1,
            'auto_secondary_feature': 2,
        },
        'final_candidate_pool_count': 3,
        'eligible_count': 2,
        'execution_count': 2,
        'planned_execution_count': 4,
    })

    markdown = render_optimizer_summary_markdown(result)

    assert '## V5 recovery' in markdown
    assert '- initial_v4_candidate_count=0' in markdown
    assert '- recovery_attempted=True' in markdown
    assert '- recovery_reason=v4_candidate_pool_empty' in markdown
    assert 'recovered_trade_feature' in markdown
    assert '- final_candidate_pool_count=3' in markdown
    assert '- eligible_count=2' in markdown
    assert '- execution_count=2' in markdown
    assert '- planned_execution_count=4' in markdown


def test_write_optimizer_report_creates_parent_directories(tmp_path):
    report_path = tmp_path / 'nested' / 'wide_v2_summary.md'

    written = write_optimizer_report(_result(), str(report_path))

    assert written == str(report_path)
    assert report_path.read_text(encoding='utf-8').startswith('# Wide v2 optimizer summary')
