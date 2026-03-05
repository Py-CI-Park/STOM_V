#!/usr/bin/env python
"""STOM CLI Backtest Runner"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.config import parse_args, validate
from cli.runner import run_backtest
from cli.output import format_result


def main():
    config = parse_args()
    if config is None:
        return 0

    errors = validate(config)
    if errors:
        for e in errors:
            print(f'ERROR: {e}', file=sys.stderr)
        return 1

    result = run_backtest(config)
    output = format_result(result, config.output_format)

    if config.output_file:
        with open(config.output_file, 'w', encoding='utf-8') as f:
            f.write(output)
    else:
        print(output)

    return 0 if result.get('status') == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
