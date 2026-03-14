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
