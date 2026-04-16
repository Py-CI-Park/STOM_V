"""Report rendering for segment strategy research."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


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
        'baseline_summary': comparison.get('baseline_summary', {}),
        'candidate_summary': comparison.get('candidate_summary', {}),
        'excluded_summary': comparison.get('excluded_summary', {}),
        'new_summary': comparison.get('new_summary', {}),
        'promotion': result.get('promotion'),
    }


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
        f"- expression: `{report.get('candidate_expression')}`",
        f"- reason: {report.get('candidate_reason')}",
        '',
        '## Trade Set Comparison',
    ]
    counts = report.get('trade_counts') or {}
    for key in ('baseline', 'candidate', 'common', 'excluded', 'new'):
        lines.append(f"- {key}: {counts.get(key, 0)}")

    lines.extend(['', '## Baseline vs Candidate'])
    for label, summary_key in (('baseline', 'baseline_summary'), ('candidate', 'candidate_summary')):
        summary = report.get(summary_key) or {}
        lines.append(f"- {label}_avg_return: {summary.get('avg_return')}")
        lines.append(f"- {label}_win_rate: {summary.get('win_rate')}")

    lines.extend(['', '## Excluded Trades'])
    excluded = report.get('excluded_summary') or {}
    lines.append(f"- avg_return: {excluded.get('avg_return')}")
    lines.append(f"- win_rate: {excluded.get('win_rate')}")

    lines.extend(['', '## New Trades'])
    new = report.get('new_summary') or {}
    lines.append(f"- avg_return: {new.get('avg_return')}")
    lines.append(f"- win_rate: {new.get('win_rate')}")

    lines.extend(['', '## Promotion'])
    promotion = report.get('promotion') or {}
    lines.append(f"- passed: {promotion.get('passed')}")
    lines.append(f"- score: {promotion.get('score')}")
    for reason in promotion.get('reasons', []):
        lines.append(f"- reason: {reason}")
    return '\n'.join(lines)


def save_research_report_json(report: dict, path: str) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return {'status': 'ok', 'path': path}


def save_research_report_markdown(report: dict, path: str) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(render_research_report_markdown(report), encoding='utf-8')
    return {'status': 'ok', 'path': path}
