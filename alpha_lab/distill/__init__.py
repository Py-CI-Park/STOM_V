"""alpha_lab.distill — P5 챔피언 증류 서브패키지 (research-only).

Phase 0(현 단계): 게이트런 per-trade CSV → 정규화 JSONL 챔피언 원장 배선.
Phase 1(진입 증류)·Phase 2(최적 청산 — 엔진 검증 창에서)의 유일한 입력을
이 원장으로 고정한다. 조건식 생성·엔진 기동·자동 글롭은 이 패키지 밖의 일이다.
"""

from alpha_lab.distill.ledger_wiring import (
    GATE_CSV_B_COLUMNS,
    GATE_CSV_BASE_COLUMNS,
    GATE_CSV_COLUMNS,
    GATE_CSV_R_COLUMNS,
    GATE_CSV_S_COLUMNS,
    IDENTITY_FIELDS,
    LEDGER_SCHEMA_VERSION,
    dedup_records,
    identity,
    normalize_trade_row,
    read_ledger,
    scan_csvs,
    strategy_from_csv_name,
    write_ledger,
)

__all__ = [
    "LEDGER_SCHEMA_VERSION",
    "GATE_CSV_BASE_COLUMNS",
    "GATE_CSV_B_COLUMNS",
    "GATE_CSV_S_COLUMNS",
    "GATE_CSV_R_COLUMNS",
    "GATE_CSV_COLUMNS",
    "IDENTITY_FIELDS",
    "strategy_from_csv_name",
    "normalize_trade_row",
    "identity",
    "dedup_records",
    "write_ledger",
    "read_ledger",
    "scan_csvs",
]
