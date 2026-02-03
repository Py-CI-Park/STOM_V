"""
STOM CLI Runners
================

헤드리스 실행기 모듈들.

참고: 러너들은 backtester/stock/coin 모듈에 의존하며,
      해당 모듈들은 레지스트리 접근이 필요할 수 있습니다.
      따라서 명시적으로 import할 때만 로드됩니다.
"""

__all__ = ["HeadlessBacktestRunner", "HeadlessTradeRunner", "HeadlessOptimizeRunner"]


def __getattr__(name):
    """지연 로딩을 위한 __getattr__ 구현"""
    if name == "HeadlessBacktestRunner":
        from .backtest_runner import HeadlessBacktestRunner
        return HeadlessBacktestRunner
    if name == "HeadlessTradeRunner":
        from .trade_runner import HeadlessTradeRunner
        return HeadlessTradeRunner
    if name == "HeadlessOptimizeRunner":
        from .optimize_runner import HeadlessOptimizeRunner
        return HeadlessOptimizeRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
