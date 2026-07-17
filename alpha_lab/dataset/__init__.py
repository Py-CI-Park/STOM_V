"""alpha_lab.dataset — tick 일 DB 표본·라벨 빌더 (research-only, read-only).

공개 API:
- schema: RAW_FEATURES/DERIVED_FEATURES/ALL_FEATURES(25)/LABEL_COLUMNS/META_COLUMNS,
  derive(row), as_float(value).
- labels: krx_tick_size/adverse_fill/net_rate(비용 모형 —
  ai_strategy_loop/fitness/slippage_profiles.py 정합), l1_label, l2_triple_barrier.
- reader: list_day_dbs, connect_ro(mode=ro 강제), moneytop_universe,
  load_stock_rows, stream_samples.
"""
from alpha_lab.dataset.labels import (
    ADVERSE_TICKS,
    FEE_RATE,
    L1_NET_THRESHOLD,
    SL_RATE,
    TAX_RATE,
    TIMEOUT_SEC,
    TP_RATE,
    adverse_fill,
    krx_tick_size,
    l1_label,
    l2_triple_barrier,
    net_rate,
    tick_size_below,
)
from alpha_lab.dataset.reader import (
    connect_ro,
    list_day_dbs,
    load_stock_rows,
    moneytop_universe,
    stream_samples,
)
from alpha_lab.dataset.schema import (
    ALL_FEATURES,
    DERIVED_FEATURES,
    LABEL_COLUMNS,
    META_COLUMNS,
    RAW_FEATURES,
    as_float,
    derive,
)

__all__ = [
    "ADVERSE_TICKS",
    "ALL_FEATURES",
    "DERIVED_FEATURES",
    "FEE_RATE",
    "L1_NET_THRESHOLD",
    "LABEL_COLUMNS",
    "META_COLUMNS",
    "RAW_FEATURES",
    "SL_RATE",
    "TAX_RATE",
    "TIMEOUT_SEC",
    "TP_RATE",
    "adverse_fill",
    "as_float",
    "connect_ro",
    "derive",
    "krx_tick_size",
    "l1_label",
    "l2_triple_barrier",
    "list_day_dbs",
    "load_stock_rows",
    "moneytop_universe",
    "net_rate",
    "stream_samples",
    "tick_size_below",
]
