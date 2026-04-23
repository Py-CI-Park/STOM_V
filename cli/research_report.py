"""Report rendering for segment strategy research."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path


SUMMARY_METRIC_LABELS = {
    'avg_return': '평균 수익률',
    'win_rate': '승률',
    'total_profit': '총손익',
    'avg_mae': '평균 MAE',
    'profit_factor': '프로핏 팩터',
    'date_concentration': '일자 집중도',
    'symbol_concentration': '종목 집중도',
}


def build_research_report(result: dict, strategy_name: str | None = None) -> dict:
    """Build a stable report dict from a research-loop result."""
    comparison = result.get('comparison') or {}
    candidate = result.get('candidate') or {}
    return {
        'created_at': datetime.now().isoformat(),
        'strategy_name': strategy_name or result.get('strategy_name'),
        'status': result.get('status'),
        'baseline_csv': result.get('baseline_csv'),
        'candidate_csv': result.get('candidate_csv'),
        'phase': result.get('phase'),
        'candidate_expression': candidate.get('expression'),
        'candidate_reason': candidate.get('reason'),
        'trade_counts': comparison.get('counts', {}),
        'trade_count_retention': comparison.get('trade_count_retention'),
        'trade_count_expansion': comparison.get('trade_count_expansion'),
        'baseline_summary': comparison.get('baseline_summary', {}),
        'candidate_summary': comparison.get('candidate_summary', {}),
        'excluded_summary': comparison.get('excluded_summary', {}),
        'new_summary': comparison.get('new_summary', {}),
        'promotion': result.get('promotion'),
        'candidate_plan': result.get('candidate_plan'),
        'cleanup': result.get('cleanup'),
        'iteration_plan': result.get('iteration_plan'),
        'iteration_v2': result.get('iteration_v2'),
        'retention_selection': result.get('retention_selection'),
        'candidates': result.get('candidates'),
        'best_candidate': result.get('best_candidate'),
        'cleanup_summary': result.get('cleanup_summary'),
    }


def _append_summary_metrics(lines: list[str], summary: dict) -> None:
    for key, korean_label in SUMMARY_METRIC_LABELS.items():
        if key in summary:
            lines.append(f"- {key} ({korean_label}): {summary.get(key)}")


def _normalize_json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    return value


def _format_markdown_value(value) -> str:
    if value is None:
        return ''
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _candidate_trade_count(candidate: dict):
    comparison = candidate.get('comparison') or {}
    counts = comparison.get('counts') or {}
    rank_score = candidate.get('rank_score') or {}
    return counts.get('candidate', rank_score.get('trade_count'))


def _candidate_retention(candidate: dict):
    comparison = candidate.get('comparison') or {}
    rank_score = candidate.get('rank_score') or {}
    return comparison.get('trade_count_retention', rank_score.get('trade_count_retention'))


def _candidate_label(candidate: dict):
    return candidate.get('strategy_name') or candidate.get('candidate') or candidate.get('index')


def _candidate_estimated_retention(candidate: dict):
    estimate = candidate.get('retention_estimate') or {}
    return estimate.get('estimated_retention')


def _candidate_cleanup_label(candidate: dict) -> str:
    cleanup = candidate.get('cleanup') or {}
    parts = [
        cleanup.get('reason'),
        cleanup.get('action'),
        cleanup.get('status'),
    ]
    return ', '.join(str(part) for part in parts if part is not None)


def _append_retention_sections(lines: list[str], report: dict) -> None:
    retention_selection = report.get('retention_selection') or {}
    candidates = report.get('candidates') or []

    if not (retention_selection or candidates):
        return

    lines.extend(['', '## Retention-Aware Candidate Selection'])
    if retention_selection:
        lines.append("- retention_selection summary:")
        for key in (
            'pool_count',
            'selected_count',
            'passed_count',
            'fallback_count',
            'min_estimated_retention',
        ):
            if key in retention_selection:
                lines.append(f"- {key}: {retention_selection.get(key)}")
    else:
        lines.append("- retention_selection: none")

    lines.extend([
        '',
        '| candidate | expression | estimated_retention | passed | fallback |',
        '| --- | --- | --- | --- | --- |',
    ])
    if candidates:
        for candidate in candidates:
            row = [
                _candidate_label(candidate),
                candidate.get('expression'),
                _candidate_estimated_retention(candidate),
                candidate.get('retention_filter_passed'),
                candidate.get('retention_fallback_used'),
            ]
            lines.append('| ' + ' | '.join(_format_markdown_value(value) for value in row) + ' |')
    else:
        lines.append('|  |  |  |  |  |')

    lines.extend([
        '',
        '## Retention-Penalized Ranking',
        '| rank | strategy | score | retention | penalty | adjusted_score |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    if candidates:
        for candidate in candidates:
            rank_score = candidate.get('rank_score') or {}
            promotion = candidate.get('promotion') or {}
            row = [
                candidate.get('rank'),
                candidate.get('strategy_name'),
                rank_score.get('promotion_score', promotion.get('score')),
                rank_score.get('trade_count_retention', _candidate_retention(candidate)),
                rank_score.get('retention_penalty'),
                rank_score.get('adjusted_score'),
            ]
            lines.append('| ' + ' | '.join(_format_markdown_value(value) for value in row) + ' |')
    else:
        lines.append('|  |  |  |  |  |  |')


def _append_iteration_v2_section(lines: list[str], report: dict) -> None:
    iteration_v2 = report.get('iteration_v2') or {}
    if not iteration_v2 or iteration_v2.get('status') == 'disabled':
        return

    lines.extend(['', '## Iteration Loop v2 Candidate Generation'])
    for key in (
        'status',
        'mode',
        'primary_feature',
        'secondary_features',
        'candidate_count',
    ):
        lines.append(f"- {key}: {iteration_v2.get(key)}")
    type_counts = iteration_v2.get('type_counts') or {}
    if type_counts:
        lines.append('- type_counts:')
        for key, value in type_counts.items():
            lines.append(f"  - {key}: {value}")


def _append_candidate_iteration_sections(lines: list[str], report: dict) -> None:
    iteration_plan = report.get('iteration_plan') or {}
    retention_selection = report.get('retention_selection') or {}
    candidates = report.get('candidates') or []
    best_candidate = report.get('best_candidate') or {}
    cleanup_summary = report.get('cleanup_summary') or {}

    if not (iteration_plan or retention_selection or candidates):
        return

    lines.extend(['', '## Candidate Iteration'])
    lines.append(f"- phase: {report.get('phase')}")
    if iteration_plan:
        for key in (
            'candidate_count',
            'effective_top_n',
            'candidate_name_prefix',
            'candidate_start_date',
            'candidate_end_date',
            'candidate_timeout',
            'cleanup_best_candidate',
            'keep_loser_candidates',
            'keep_failed_candidate',
        ):
            if key in iteration_plan:
                lines.append(f"- {key}: {iteration_plan.get(key)}")
    else:
        lines.append("- iteration_plan: none")
    if best_candidate:
        lines.append(f"- best_candidate: {best_candidate.get('strategy_name')}")
        lines.append(f"- best_expression: `{best_candidate.get('expression')}`")

    lines.extend([
        '',
        '## Candidate Ranking',
        '| rank | strategy | expression | status | passed | score | trade_count | retention | cleanup |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    if candidates:
        for candidate in candidates:
            promotion = candidate.get('promotion') or {}
            row = [
                candidate.get('rank'),
                candidate.get('strategy_name'),
                candidate.get('expression'),
                candidate.get('status'),
                promotion.get('passed'),
                promotion.get('score'),
                _candidate_trade_count(candidate),
                _candidate_retention(candidate),
                _candidate_cleanup_label(candidate),
            ]
            lines.append('| ' + ' | '.join(_format_markdown_value(value) for value in row) + ' |')
    else:
        lines.append('|  |  |  |  |  |  |  |  |  |')

    _append_retention_sections(lines, report)

    lines.extend(['', '## Cleanup Summary'])
    if cleanup_summary:
        for key in ('attempted_count', 'deleted_count', 'kept_count', 'failed_count'):
            if key in cleanup_summary:
                lines.append(f"- {key}: {cleanup_summary.get(key)}")
        for item in cleanup_summary.get('items') or []:
            item = item or {}
            strategy_name = item.get('strategy_name')
            reason = item.get('reason')
            status = item.get('status')
            action = item.get('action')
            lines.append(
                f"- {strategy_name}: reason={reason}, status={status}, action={action}"
            )
    else:
        lines.append("- none")


def render_research_report_markdown(report: dict) -> str:
    """Render a research report as Korean Markdown."""
    lines = [
        f"# 조건식 연구 리포트: {report.get('strategy_name') or 'unknown'}",
        '',
        f"- created_at: {report.get('created_at')}",
        f"- status: {report.get('status')}",
        f"- baseline_csv: {report.get('baseline_csv')}",
        f"- candidate_csv: {report.get('candidate_csv')}",
        '',
        '## Candidate',
        f"- 후보 조건식: `{report.get('candidate_expression')}`",
        f"- expression: `{report.get('candidate_expression')}`",
        f"- 후보 사유: {report.get('candidate_reason')}",
        f"- reason: {report.get('candidate_reason')}",
    ]
    lines.extend(['', '## Candidate Runtime'])
    candidate_plan = report.get('candidate_plan') or {}
    cleanup = report.get('cleanup') or {}
    if candidate_plan:
        lines.append(f"- 후보 백테스트 실행 여부: {candidate_plan.get('will_run_backtest')}")
        lines.append(f"- 후보 백테스트 시작일: {candidate_plan.get('candidate_start_date')}")
        lines.append(f"- 후보 백테스트 종료일: {candidate_plan.get('candidate_end_date')}")
        lines.append(f"- candidate_timeout: {candidate_plan.get('candidate_timeout')}")
        lines.append(f"- 후보 전략 저장 여부: {candidate_plan.get('will_save_strategy')}")
        if 'keep_failed_candidate' in candidate_plan:
            lines.append(f"- keep_failed_candidate: {candidate_plan.get('keep_failed_candidate')}")
    else:
        lines.append("- none")
    if cleanup:
        lines.append(f"- cleanup attempted: {cleanup.get('attempted')}")
        if cleanup.get('strategy_name'):
            lines.append(f"- cleanup strategy_name: {cleanup.get('strategy_name')}")
        if cleanup.get('reason'):
            lines.append(f"- cleanup reason: {cleanup.get('reason')}")
        if cleanup.get('status') is not None:
            lines.append(f"- cleanup status: {cleanup.get('status')}")
        if cleanup.get('action') is not None:
            lines.append(f"- cleanup action: {cleanup.get('action')}")
        if cleanup.get('message'):
            lines.append(f"- cleanup message: {cleanup.get('message')}")

    _append_candidate_iteration_sections(lines, report)
    _append_iteration_v2_section(lines, report)

    lines.extend([
        '',
        '## Trade Set Comparison',
        '- 거래 수: 기준/후보/공통/제외/신규 거래 집합 비교',
    ])
    counts = report.get('trade_counts') or {}
    count_labels = {
        'baseline': '기준 거래',
        'candidate': '후보 거래',
        'common': '공통 거래',
        'excluded': '제외 거래',
        'new': '신규 거래',
    }
    for key, korean_label in count_labels.items():
        lines.append(f"- {key} ({korean_label}): {counts.get(key, 0)}")
    if report.get('trade_count_retention') is not None:
        lines.append(f"- trade_count_retention (거래 유지율): {report.get('trade_count_retention')}")
    if report.get('trade_count_expansion') is not None:
        lines.append(f"- trade_count_expansion (신규 거래 비율): {report.get('trade_count_expansion')}")

    lines.extend(['', '## Baseline vs Candidate'])
    for label, summary_key in (('baseline', 'baseline_summary'), ('candidate', 'candidate_summary')):
        summary = report.get(summary_key) or {}
        lines.append(f"- {label} summary:")
        lines.append(f"- {label}_avg_return: {summary.get('avg_return')}")
        lines.append(f"- {label}_win_rate: {summary.get('win_rate')}")
        _append_summary_metrics(lines, summary)

    lines.extend(['', '## Excluded Trades'])
    excluded = report.get('excluded_summary') or {}
    lines.append('- 제외 거래: 기준 전략에는 있었지만 후보 전략에서 제거된 거래')
    lines.append(f"- avg_return: {excluded.get('avg_return')}")
    lines.append(f"- win_rate: {excluded.get('win_rate')}")
    _append_summary_metrics(lines, excluded)

    lines.extend(['', '## New Trades'])
    new = report.get('new_summary') or {}
    lines.append('- 신규 거래: 후보 전략에서 새로 발생한 거래')
    lines.append(f"- avg_return: {new.get('avg_return')}")
    lines.append(f"- win_rate: {new.get('win_rate')}")
    _append_summary_metrics(lines, new)

    lines.extend(['', '## Promotion'])
    promotion = report.get('promotion') or {}
    lines.append('- 승격 평가: 후보 조건의 채택 가능성과 필수 게이트 통과 여부')
    lines.append(f"- passed: {promotion.get('passed')}")
    lines.append(f"- score: {promotion.get('score')}")
    for reason in promotion.get('reasons') or []:
        lines.append(f"- reason: {reason}")
    deltas = promotion.get('deltas') or {}
    if deltas:
        lines.append('- promotion_deltas (승격 델타):')
        for key, value in deltas.items():
            lines.append(f"  - {key}: {value}")
    gates = promotion.get('gates') or {}
    if gates:
        lines.append('- promotion_gates (승격 게이트):')
        for key, value in gates.items():
            lines.append(f"  - {key}: {value}")

    return '\n'.join(lines)


def save_research_report_json(report: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        safe_report = _normalize_json_value(report)
        payload = json.dumps(safe_report, allow_nan=False, ensure_ascii=False, indent=2, default=str)
        Path(path).write_text(payload, encoding='utf-8')
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}


def save_research_report_markdown(report: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(render_research_report_markdown(report), encoding='utf-8')
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}
