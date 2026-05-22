#!/usr/bin/env python
"""STOM 공식 CLI 진입점.

서브커맨드:
- 기본 백테스트 실행
- formula / strategy / discovery 서브커맨드
- optimize / sweep / wfo / tune / db 서브커맨드
- setting / report / runtime-preflight 서브커맨드
"""
import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli._safe_io import configure_safe_output
from cli.config import parse_args, validate
from cli.output import format_result

# Exit code constants
EXIT_SUCCESS = 0
EXIT_ARG_ERROR = 1
EXIT_EXEC_ERROR = 2
EXIT_TIMEOUT = 3


def _configure_matplotlib_headless():
    """가능한 경우 matplotlib를 headless 모드로 전환한다.

    CLI의 가벼운 경로(`--help`, `--list-strategies`, `formula/strategy --help`)에서는
    matplotlib 자체가 필요 없으므로 ImportError를 무시한다.
    """
    try:
        import matplotlib
    except ImportError:
        return False

    matplotlib.use('agg')  # headless 백엔드 — GUI 없이 그래프 생성
    return True


SUBCOMMANDS = (
    'formula', 'strategy', 'discovery',
    'optimize', 'sweep', 'wfo', 'tune', 'db',
    'setting', 'report', 'runtime-preflight',
    'ai-controller',
)


def main():
    configure_safe_output()

    # 서브커맨드 감지
    if len(sys.argv) > 1 and sys.argv[1] in SUBCOMMANDS:
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

    # 전략-타임프레임 자동 검증 (US-501)
    try:
        from cli.timeframe_detector import validate_timeframe_match
        tf_check = validate_timeframe_match(config)
        if tf_check['status'] != 'ok':
            print(f"ERROR: {tf_check['message']}", file=sys.stderr)
            return EXIT_ARG_ERROR
    except ImportError:
        pass

    _configure_matplotlib_headless()
    try:
        from cli.runner import run_backtest
        result = run_backtest(config)
    except SystemExit as exc:
        code = exc.code
        # Runtime imports sometimes abort with bare sys.exit().
        # For the CLI entrypoint, unexpected aborts are execution errors.
        if code in (None, 0):
            return EXIT_EXEC_ERROR
        if isinstance(code, int):
            return code
        return EXIT_EXEC_ERROR
    output = format_result(result, config.output_format)

    if config.output_file:
        with open(config.output_file, 'w', encoding='utf-8') as f:
            f.write(output)
    else:
        print(output)

    if result.get('status') == 'success':
        return EXIT_SUCCESS
    msg = result.get('message', '')
    if (
        result.get('engine_data_loading') is not None
        or result.get('last_checkpoint') == 'engine_data_response_timeout'
        or result.get('checkpoint_status') == 'timeout'
    ):
        return EXIT_TIMEOUT
    if '시간 초과' in msg or 'timeout' in msg.lower():
        return EXIT_TIMEOUT
    return EXIT_EXEC_ERROR


if __name__ == '__main__':
    sys.exit(main())
