"""alpha_lab.bridge — 연구 산출 조건식의 전략 DB 브리지 (INSERT-only).

registrar: 'ALP_' 접두 강제 + 실쓰기 전 파일 백업 + 동명 스킵(멱등) 등록기.
receipts: 등록 provenance 영수증 JSONL 원장(append-only).
실 전략 DB 접근은 오케스트레이터 판단하에 registrar를 통해서만 이뤄지며,
기존 행 UPDATE/DELETE는 어떤 경로로도 수행하지 않는다.
"""

from alpha_lab.bridge.receipts import (
    ALLOWED_SOURCE_KINDS,
    append_receipt,
    read_receipts,
)
from alpha_lab.bridge.registrar import NAME_PREFIX, register_conditions

__all__ = [
    "ALLOWED_SOURCE_KINDS",
    "NAME_PREFIX",
    "append_receipt",
    "read_receipts",
    "register_conditions",
]
