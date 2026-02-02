"""
STOM CLI Main Entry Point
==========================

Click-based CLI 인터페이스 메인 진입점.
"""

import click
from cli.commands import strategy, data, backtest


@click.group()
@click.version_option(version='2.36.U1.5', prog_name='STOM')
def main():
    """
    STOM - System Trading Open Machine

    PyQt5 GUI 없이 STOM을 CLI로 제어합니다.
    """
    pass


# 서브커맨드 등록
main.add_command(strategy.strategy)
main.add_command(data.data)
main.add_command(backtest.backtest)


if __name__ == '__main__':
    main()
