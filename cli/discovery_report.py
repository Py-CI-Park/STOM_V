"""자동 조건식 탐색 결과 리포트 생성기 (library-only)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def build_discovery_report(result: dict, strategy_name: str | None = None) -> dict:
    strategy_name = strategy_name or (
        (result.get('strategy_result') or {}).get('name')
        or (result.get('temporary_strategy') or {}).get('name')
    )
    report = {
        'created_at': datetime.now().isoformat(),
        'strategy_name': strategy_name,
        'status': result.get('status'),
        'promoted': result.get('promoted'),
        'promotion_preset': ((result.get('promotion_evaluation') or {}).get('preset')
                             or ((result.get('promotion_evaluation') or {}).get('criteria') or {}).get('preset')),
        'candidate_count': ((result.get('expression_result') or {}).get('candidate_count')
                            or (result.get('strategy_flow') or {}).get('expression_result', {}).get('candidate_count')),
        'feature_whitelist': result.get('feature_whitelist')
            or (result.get('strategy_flow') or {}).get('feature_whitelist'),
        'top_ml_features': ((result.get('ml_analysis_result') or {}).get('top_features')
                            or ((result.get('strategy_flow') or {}).get('ml_analysis_result') or {}).get('top_features')
                            or [])[:5],
        'promotion_evaluation': result.get('promotion_evaluation'),
        'walk_forward_summary': (result.get('walk_forward') or {}).get('summary'),
        'strategy_result': result.get('strategy_result') or (result.get('strategy_flow') or {}).get('strategy_result'),
        'saved_code': result.get('saved_code'),
        'expressions': ((result.get('expression_result') or {}).get('expressions')
                        or ((result.get('strategy_flow') or {}).get('expression_result') or {}).get('expressions')
                        or []),
        'auto_relax_history': result.get('auto_relax_history')
            or (result.get('strategy_flow') or {}).get('auto_relax_history')
            or [],
        'criteria_mode': result.get('criteria_mode')
            or ((result.get('promotion_evaluation') or {}).get('criteria_mode')),
        'pipeline_timing': result.get('pipeline_timing'),
        'analysis_rounds_log': ((result.get('phase_b') or {}).get('rounds_log')
                                or result.get('rounds_log')
                                or []),
    }
    return report


def render_discovery_report_markdown(report: dict) -> str:
    lines = [
        f"# 자동 조건식 탐색 리포트: {report.get('strategy_name') or 'unknown'}",
        '',
        f"- created_at: {report.get('created_at')}",
        f"- status: {report.get('status')}",
        f"- promoted: {report.get('promoted')}",
        f"- promotion_preset: {report.get('promotion_preset')}",
        f"- criteria_mode: {report.get('criteria_mode') or 'unknown'}",
        f"- candidate_count: {report.get('candidate_count')}",
        '',
        '## Walk-Forward Summary',
    ]

    wf_summary = report.get('walk_forward_summary') or {}
    if wf_summary:
        for key, value in wf_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append('- none')

    lines.extend(['', '## Promotion Evaluation'])
    evaluation = report.get('promotion_evaluation') or {}
    if evaluation:
        lines.append(f"- passed: {evaluation.get('passed')}")
        for reason in evaluation.get('reasons', []):
            lines.append(f"- reason: {reason}")
        criteria = evaluation.get('criteria') or {}
        if criteria:
            lines.append('- criteria:')
            for key, value in criteria.items():
                lines.append(f"  - {key}: {value}")
    else:
        lines.append('- none')

    lines.extend(['', '## ML Top Features'])
    top_features = report.get('top_ml_features') or []
    if top_features:
        for item in top_features:
            lines.append(f"- {item.get('feature')}: {item.get('importance')}")
    else:
        lines.append('- none')

    lines.extend(['', '## Feature Whitelist'])
    whitelist = report.get('feature_whitelist') or []
    if whitelist:
        for feature in whitelist:
            lines.append(f"- {feature}")
    else:
        lines.append('- none')

    lines.extend(['', '## Candidate Expressions'])
    expressions = report.get('expressions') or []
    if expressions:
        for expression in expressions:
            lines.append(f"- `{expression}`")
    else:
        lines.append('- none')

    lines.extend(['', '## Pipeline Timing'])
    timing = report.get('pipeline_timing') or {}
    if timing:
        lines.append('| Phase | Duration (s) |')
        lines.append('|-------|-------------|')
        lines.append(f"| A: Backtest | {timing.get('phase_a', '-')} |")
        lines.append(f"| B: Analysis | {timing.get('phase_b', '-')} |")
        lines.append(f"| C: WFO+Promote | {timing.get('phase_c', '-')} |")
        lines.append(f"| **Total** | **{timing.get('total', '-')}** |")
    else:
        lines.append('- none')

    lines.extend(['', '## Analysis Rounds Log'])
    rounds_log = report.get('analysis_rounds_log') or []
    if rounds_log:
        lines.append('| Round | alpha | min_samples | quantiles | top_n | candidates | status |')
        lines.append('|-------|-------|-------------|-----------|-------|------------|--------|')
        for r in rounds_log:
            lines.append(
                f"| {r.get('round', '-')} | {r.get('alpha', '-')} | {r.get('min_samples', '-')} "
                f"| {r.get('quantiles', '-')} | {r.get('top_n', '-')} | {r.get('candidate_count', '-')} "
                f"| {r.get('status', '-')} |"
            )
    else:
        lines.append('- none')

    lines.extend(['', '## Auto-Relax History'])
    auto_relax_history = report.get('auto_relax_history') or []
    if auto_relax_history:
        for item in auto_relax_history:
            lines.append(f"- step: {item.get('step')}")
            lines.append(f"  - top_n: {item.get('top_n')}")
            lines.append(f"  - zero_trade_rounds: {item.get('zero_trade_rounds')}")
            lines.append(f"  - total_rounds: {item.get('total_rounds')}")
    else:
        lines.append('- none')

    return '\n'.join(lines)


def build_cross_timeframe_report(batch_result: dict) -> dict:
    """동일 전략의 tick/min 결과를 짝지어 비교한다.

    Args:
        batch_result: run_batch()가 반환한 결과 dict.

    Returns:
        {'pairs': [{'buy_strategy': str, 'tick': summary|None, 'min': summary|None,
                     'winner': 'tick'|'min'|'tie'|'none'}, ...],
         'tick_promoted': int, 'min_promoted': int}
    """
    results = batch_result.get('results', [])

    # 전략별 그룹화
    strategy_map: dict[str, dict] = {}
    for r in results:
        key = r.get('buy_strategy', '')
        tf = r.get('_timeframe') or ('tick' if r.get('is_tick', True) else 'min')
        if key not in strategy_map:
            strategy_map[key] = {}
        strategy_map[key][tf] = r

    pairs = []
    tick_promoted = 0
    min_promoted = 0

    for strategy, tf_map in strategy_map.items():
        tick_r = tf_map.get('tick')
        min_r = tf_map.get('min')

        tick_ok = tick_r and tick_r.get('promoted', False)
        min_ok = min_r and min_r.get('promoted', False)

        if tick_ok:
            tick_promoted += 1
        if min_ok:
            min_promoted += 1

        if tick_ok and min_ok:
            # 둘 다 승격: pipeline_duration으로 비교
            t_dur = tick_r.get('pipeline_duration') or float('inf')
            m_dur = min_r.get('pipeline_duration') or float('inf')
            winner = 'tick' if t_dur <= m_dur else 'min'
        elif tick_ok:
            winner = 'tick'
        elif min_ok:
            winner = 'min'
        else:
            winner = 'none'

        pairs.append({
            'buy_strategy': strategy,
            'tick': tick_r,
            'min': min_r,
            'winner': winner,
        })

    return {
        'pairs': pairs,
        'tick_promoted': tick_promoted,
        'min_promoted': min_promoted,
    }


def render_cross_timeframe_markdown(report: dict) -> str:
    """크로스 타임프레임 비교 Markdown 테이블."""
    lines = [
        '# Cross-Timeframe Comparison',
        '',
        f"- tick promoted: {report.get('tick_promoted', 0)}",
        f"- min promoted: {report.get('min_promoted', 0)}",
        '',
        '| Strategy | Tick Status | Min Status | Winner |',
        '|----------|------------|------------|--------|',
    ]

    for pair in report.get('pairs', []):
        tick = pair.get('tick') or {}
        min_r = pair.get('min') or {}
        tick_status = 'promoted' if tick.get('promoted') else tick.get('status', '-')
        min_status = 'promoted' if min_r.get('promoted') else min_r.get('status', '-')
        lines.append(
            f"| {pair.get('buy_strategy', '-')} "
            f"| {tick_status} | {min_status} | {pair.get('winner', '-')} |"
        )

    return '\n'.join(lines)


def save_discovery_report_json(report: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}


def save_discovery_report_markdown(report: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(render_discovery_report_markdown(report), encoding='utf-8')
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}
