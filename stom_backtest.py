#!/usr/bin/env python
"""STOM CLI Backtest Runner"""
import sys
import json
import os
import matplotlib
matplotlib.use('agg')  # headless 백엔드 — GUI 없이 그래프 생성

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.config import parse_args, validate
from cli.runner import run_backtest
from cli.output import format_result

# Exit code constants
EXIT_SUCCESS = 0
EXIT_ARG_ERROR = 1
EXIT_EXEC_ERROR = 2
EXIT_TIMEOUT = 3


def main():
    # 서브커맨드 감지 (formula, strategy)
    if len(sys.argv) > 1 and sys.argv[1] in ('formula', 'strategy'):
        from cli.subcommands import handle_subcommand
        return handle_subcommand(sys.argv[1:])

    # 기존 백테스트 로직 (하위 호환 유지)
    config = parse_args()
    if config is None:
        return EXIT_SUCCESS

    if config.dry_run:
        summary = {
            "status": "dry-run",
            "buy_strategy": config.buy_strategy,
            "sell_strategy": config.sell_strategy,
            "start_date": config.start_date,
            "end_date": config.end_date,
            "engine_count": config.engine_count,
            "is_tick": config.is_tick,
            "dry_run": True,
        }
        print(json.dumps(summary, ensure_ascii=False))
        return EXIT_SUCCESS

    errors = validate(config)
    if errors:
        for e in errors:
            print(f'ERROR: {e}', file=sys.stderr)
        return EXIT_ARG_ERROR

    result = run_backtest(config)
    output = format_result(result, config.output_format)

    if config.output_file:
        with open(config.output_file, 'w', encoding='utf-8') as f:
            f.write(output)
    else:
        print(output)

    if result.get('status') == 'success':
        return EXIT_SUCCESS
    msg = result.get('message', '')
    if '시간 초과' in msg or 'timeout' in msg.lower():
        return EXIT_TIMEOUT
    return EXIT_EXEC_ERROR


if __name__ == '__main__':
    sys.exit(main())
