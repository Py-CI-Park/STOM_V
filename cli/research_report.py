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
        '',
        '## Trade Set Comparison',
        '- 거래 수: 기준/후보/공통/제외/신규 거래 집합 비교',
    ]
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
