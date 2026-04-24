#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_RUNTIME_PATH = Path(
    r'C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json'
)
DEFAULT_WIDE_REFERENCE_CSV = Path(
    r'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
)
DEFAULT_CONTROL_CSV = Path(
    r'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
)
DEFAULT_OUTPUT = PROJECT_ROOT / 'docs' / 'research' / 'condition_research' / 'pilot_logs' / (
    '2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md'
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Analyze wide v1/v3 runtime results and write the v4 decision markdown report.',
    )
    parser.add_argument('--runtime-path', type=Path, default=DEFAULT_RUNTIME_PATH)
    parser.add_argument('--wide-reference-csv', type=Path, default=DEFAULT_WIDE_REFERENCE_CSV)
    parser.add_argument('--control-csv', type=Path, default=DEFAULT_CONTROL_CSV)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    from cli.research_v3_decision import write_v3_decision_report

    args = build_parser().parse_args(argv)
    analysis = write_v3_decision_report(
        runtime_path=args.runtime_path,
        wide_reference_csv=args.wide_reference_csv,
        control_csv=args.control_csv,
        output_path=args.output,
    )
    print(f"decision={analysis['decision']}")
    print(f"next_command={analysis['next_command']}")
    print(f'wrote={args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
