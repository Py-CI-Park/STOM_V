#!/usr/bin/env python
from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportUnknownVariableType=none, reportUnusedCallResult=none

import argparse
from pathlib import Path
import sys
from typing import Any, TypeAlias, cast


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT = PROJECT_ROOT / 'docs' / 'research' / 'condition_research' / 'pilot_logs' / (
    '2026-04-24_wide_v1_v5_actual_rowset_selection.md'
)

PROCEED_TO_PROMOTE_WFO_PLAN = 'PROCEED_TO_PROMOTE_WFO_PLAN'
HOLD_V5_RUNTIME_FAILURE = 'HOLD_V5_RUNTIME_FAILURE'
HOLD_V5_ACTUAL_ROW_SET_SHORTFALL = 'HOLD_V5_ACTUAL_ROW_SET_SHORTFALL'

NEXT_COMMANDS = {
    PROCEED_TO_PROMOTE_WFO_PLAN: '$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성',
    HOLD_V5_RUNTIME_FAILURE: '$brainstorming Wide v1 v5 runtime failure recovery 설계',
    HOLD_V5_ACTUAL_ROW_SET_SHORTFALL: '$brainstorming Wide v1 v6 actual row-set generation expansion 설계',
}

JsonDict: TypeAlias = dict[str, Any]


def _as_dict(value: object) -> JsonDict:
    return cast(JsonDict, value) if isinstance(value, dict) else {}


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(value)
        except (OverflowError, ValueError):
            return default
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _is_runtime_ok(runtime: JsonDict) -> bool:
    return runtime.get('status') in {'ok', 'success'}


def decide_v5_actual_rowset(runtime: JsonDict) -> JsonDict:
    actual_selection = _as_dict(runtime.get('actual_rowset_selection'))
    iteration_v5 = _as_dict(runtime.get('iteration_v5'))
    requested_count = _safe_int(
        actual_selection.get('requested_count'),
        default=_safe_int(iteration_v5.get('requested_count')),
    )
    selected_count = _safe_int(actual_selection.get('selected_count'))
    row_set_identity_status = str(actual_selection.get('row_set_identity_status') or '')

    if not _is_runtime_ok(runtime):
        decision = HOLD_V5_RUNTIME_FAILURE
    elif (
        actual_selection.get('status') == 'ok'
        and row_set_identity_status == 'all_distinct'
        and selected_count >= requested_count
    ):
        decision = PROCEED_TO_PROMOTE_WFO_PLAN
    else:
        decision = HOLD_V5_ACTUAL_ROW_SET_SHORTFALL

    return {
        'decision': decision,
        'next_command': NEXT_COMMANDS[decision],
        'runtime_status': runtime.get('status'),
        'runtime_phase': runtime.get('phase'),
        'actual_rowset_selection': actual_selection,
        'row_set_identity_status': row_set_identity_status or None,
        'requested_count': requested_count,
        'selected_count': selected_count,
        'executed_count': _safe_int(actual_selection.get('executed_count')),
        'actual_group_count': _safe_int(actual_selection.get('actual_group_count')),
        'duplicate_actual_rowset_count': _safe_int(actual_selection.get('duplicate_actual_rowset_count')),
    }


def render_v5_actual_rowset_markdown(analysis: JsonDict, *, runtime_path: Path) -> str:
    lines = [
        '# Wide v1 v5 actual row-set selection',
        '',
        f"- decision={analysis.get('decision')}",
        f"- next_command={analysis.get('next_command')}",
        f"- runtime_path={runtime_path}",
        f"- runtime_status={analysis.get('runtime_status')}",
        f"- runtime_phase={analysis.get('runtime_phase')}",
        f"- row_set_identity_status={analysis.get('row_set_identity_status')}",
        f"- requested_count={analysis.get('requested_count')}",
        f"- selected_count={analysis.get('selected_count')}",
        f"- executed_count={analysis.get('executed_count')}",
        f"- actual_group_count={analysis.get('actual_group_count')}",
        f"- duplicate_actual_rowset_count={analysis.get('duplicate_actual_rowset_count')}",
    ]
    return '\n'.join(lines) + '\n'


def write_v5_actual_rowset_report(*, runtime_path: Path, output_path: Path) -> JsonDict:
    from cli.research_v3_decision import read_runtime_json

    runtime = cast(JsonDict, read_runtime_json(runtime_path))
    analysis = decide_v5_actual_rowset(runtime)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_v5_actual_rowset_markdown(analysis, runtime_path=runtime_path),
        encoding='utf-8',
    )
    return analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Analyze Wide v1 v5 actual row-set representative selection from a runtime artifact.',
    )
    _ = parser.add_argument('--runtime-path', type=Path, required=True)
    _ = parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime_path = cast(Path, args.runtime_path)
    output_path = cast(Path, args.output)
    analysis = write_v5_actual_rowset_report(
        runtime_path=runtime_path,
        output_path=output_path,
    )
    print(f"decision={analysis['decision']}")
    print(f"next_command={analysis['next_command']}")
    print(f"row_set_identity_status={analysis.get('row_set_identity_status')}")
    print(f"selected_count={analysis.get('selected_count')}")
    print(f"requested_count={analysis.get('requested_count')}")
    print(f'wrote={output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
