"""
STOM CLI Main Entry Point
==========================

Click-based CLI 인터페이스 메인 진입점.
"""

import click
from cli.commands import strategy, data, backtest, trade, monitor, optimize, db
from cli.version import PROG_NAME, VERSION


@click.group()
@click.version_option(version=VERSION, prog_name=PROG_NAME)
def main():
    """
    STOM - System Trading Open Machine

    PyQt5 GUI 없이 STOM을 CLI로 제어합니다.

    주요 명령어:
    - strategy: 전략 관리 (list, show, export, save, delete)
    - data: 데이터 조회 (trades, summary, export)
    - backtest: 백테스트 실행 (run, list, status, cancel)
    - trade: 트레이딩 제어 (start, stop, status)
    - positions: 포지션 관리 (list, close)
    - orders: 주문 관리 (list, cancel)
    - monitor: 실시간 모니터링 (live, pnl, positions)
    - optimize: 최적화 (grid, bayesian, ga, walkforward, backfinder)
    - db: 데이터베이스 관리 (create, append, delete, info, vacuum, backup)
    """
    pass


# 서브커맨드 등록
main.add_command(strategy.strategy)
main.add_command(data.data)
main.add_command(backtest.backtest)
main.add_command(trade.trade)
main.add_command(trade.positions)
main.add_command(trade.orders)
main.add_command(monitor.monitor)
main.add_command(optimize.optimize)
main.add_command(db.db)


if __name__ == '__main__':
    main()
