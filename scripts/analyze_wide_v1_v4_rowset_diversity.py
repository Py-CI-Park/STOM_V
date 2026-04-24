#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import cast


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT = PROJECT_ROOT / 'docs' / 'research' / 'condition_research' / 'pilot_logs' / (
    '2026-04-24_wide_v1_v4_rowset_diversity.md'
)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('--top-n must be a positive integer') from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError('--top-n must be a positive integer')
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Analyze Wide v1 v4 actual candidate row-set diversity from a runtime artifact.',
    )
    _ = parser.add_argument('--runtime-path', type=Path, required=True)
    _ = parser.add_argument('--runtime-root', type=Path, required=True)
    _ = parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    _ = parser.add_argument('--top-n', type=positive_int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    from cli.research_v3_tiebreak import write_v3_tie_break_report

    args = build_parser().parse_args(argv)
    runtime_path = cast(Path, args.runtime_path)
    runtime_root = cast(Path, args.runtime_root)
    output_path = cast(Path, args.output)
    top_n = cast(int, args.top_n)
    analysis = cast(dict[str, object], write_v3_tie_break_report(
        runtime_path=runtime_path,
        runtime_root=runtime_root,
        output_path=output_path,
        top_n=top_n,
    ))
    row_set_gate_value = analysis.get('row_set_gate')
    row_set_gate = cast(dict[str, object], row_set_gate_value) if isinstance(row_set_gate_value, dict) else {}
    print(f"decision={analysis['decision']}")
    print(f"next_command={analysis['next_command']}")
    print(f"row_set_identity_status={row_set_gate.get('status')}")
    print(f"group_count={row_set_gate.get('group_count')}")
    print(f'wrote={output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
