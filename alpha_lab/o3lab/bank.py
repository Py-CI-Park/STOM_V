"""O-3 돌파 온셋 은행 그릇 — v2 스키마 + variant 컬럼 자체 정의 (봉인본 §11·§14-F5).

F5 봉인(F6 발견 반영): 신규 `o3_breakout_onset_bank.parquet`(공유 v2 union 금지).
근거 = `onset_bank_v2.py` 는 breakout 을 선-provision(ONSET_TYPES)했으나 **variant
컬럼이 없고**, DH⊆P300⊆P20 포함관계로 같은 (day,code,t0)를 변형들이 공유 → 공유
은행 직적재 시 변형 라벨 소실·허위 중복키 충돌. 따라서 O-3 은행은:
- v2 계보 4컬럼(onset_type='breakout'·exit_label='L3_RR8_12'·source_seal=본 문서·
  audit_tag='RR8_12-conditional') + **variant 컬럼** + h300 보조 + gap_b(서술).
- **dedup 키 = (day, code, t0, variant)** — 변형 공유 (day,code,t0) 허용.

공유 모듈 드리프트 방지(§14 주의): 스키마·계약을 여기서 **자체 정의**하며
`onset_bank_v2.py` 를 import·수정하지 않는다. append 계약은 판정만·쓰기 없음.
"""
from __future__ import annotations

import logging
from pathlib import Path
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional

import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "AUDIT_TAG",
    "BANK_SCHEMA",
    "DEDUP_KEYS",
    "EXIT_LABEL",
    "ONSET_TYPE",
    "SOURCE_SEAL",
    "append_contract",
    "stamp_lineage",
    "write_bank",
]

# ── 계보 상수(전 행 고정 — §9 딱지·창-지위 원장 정합) ────────────────────────
ONSET_TYPE = "breakout"
EXIT_LABEL = "L3_RR8_12"
SOURCE_SEAL = "2026-07-12_o3_breakout_onset_preregistration.md"
AUDIT_TAG = "RR8_12-conditional"

# ── dedup 키(F5 봉인) — 변형이 같은 (day,code,t0)를 공유할 수 있으므로 variant 포함 ──
DEDUP_KEYS = ("day", "code", "t0", "variant")

# ── 은행 v2+variant 스키마(정준 dtype 문자열 — 자체 정의, onset_bank_v2 미참조) ──
BANK_SCHEMA: Mapping[str, str] = MappingProxyType({
    # v1 식별 + 축 + L3(onset_l3_bank 계열과 동형).
    "code": "string", "day": "int32", "off": "int16", "t0": "int64",
    "year": "int16", "variant": "string",
    "updown_q": "int8", "mktcap_b": "int8", "time_b": "int8", "gap_b": "int8",
    "l3_net": "float64", "l3_labeled": "bool", "l3_clause": "int16", "l3_exit": "int64",
    # h300 보조(§5 병기, 채택 조건 아님).
    "h300_net": "float64", "h300_valid": "bool",
    # v2 계보 4컬럼(전부 필수·비공백).
    "onset_type": "string", "exit_label": "string",
    "source_seal": "string", "audit_tag": "string",
})


def stamp_lineage(df: pd.DataFrame) -> pd.DataFrame:
    """소비 프레임에 v2 계보 4컬럼을 상수로 찍고 BANK_SCHEMA 컬럼 순서로 정렬."""
    out = df.assign(onset_type=ONSET_TYPE, exit_label=EXIT_LABEL,
                    source_seal=SOURCE_SEAL, audit_tag=AUDIT_TAG)
    cols = [c for c in BANK_SCHEMA if c in out.columns]
    return out[cols].copy()


def _dup_key_violations(df: pd.DataFrame) -> List[Dict[str, object]]:
    """(day,code,t0,variant) 중복 검사 — 배치 내부(구조적 0 이어야 함)."""
    keys = list(DEDUP_KEYS)
    if any(c not in df.columns for c in keys) or df.shape[0] == 0:
        return []
    dup_mask = df.duplicated(subset=keys, keep=False)
    if not bool(dup_mask.any()):
        return []
    sample = (df.loc[dup_mask, keys]
              .drop_duplicates().head(20)
              .itertuples(index=False, name=None))
    return [{"check": "dup_key", "kind": "duplicate_in_batch",
             "n_bad": int(dup_mask.sum()), "keys": [tuple(k) for k in sample]}]


def _schema_violations(df: pd.DataFrame) -> List[Dict[str, object]]:
    """스키마 컬럼 존재 검사(dtype 는 write_bank 가 캐스팅으로 보장)."""
    missing = [c for c in BANK_SCHEMA if c not in df.columns]
    return [{"check": "schema", "kind": "missing_column", "columns": missing}] \
        if missing else []


def _lineage_violations(df: pd.DataFrame) -> List[Dict[str, object]]:
    """계보 4컬럼 값 검사 — 상수 일치·비공백."""
    out: List[Dict[str, object]] = []
    expect = {"onset_type": ONSET_TYPE, "exit_label": EXIT_LABEL,
              "source_seal": SOURCE_SEAL, "audit_tag": AUDIT_TAG}
    for col, val in expect.items():
        if col in df.columns and df.shape[0] and bool((df[col] != val).any()):
            out.append({"check": "lineage", "kind": "value_mismatch",
                        "column": col, "expected": val})
    return out


def append_contract(df: pd.DataFrame, window_start: int, window_end: int
                    ) -> Dict[str, object]:
    """돌파 온셋 배치를 은행에 붙이기 전 검증 계약 — 판정만, 쓰기 없음.

    ① 스키마 컬럼 존재 ② 계보 4컬럼 상수 ③ (day,code,t0,variant) 중복
    ④ 창 범위(day ∈ [window_start, window_end]). 위반 있으면 적재 금지.
    """
    violations: List[Dict[str, object]] = []
    violations += _schema_violations(df)
    violations += _lineage_violations(df)
    violations += _dup_key_violations(df)
    if "day" in df.columns and df.shape[0]:
        days = pd.to_numeric(df["day"], errors="coerce")
        bad = days.isna() | (days < window_start) | (days > window_end)
        if bool(bad.any()):
            violations.append({"check": "window", "kind": "day_out_of_range",
                               "n_bad": int(bad.sum()),
                               "window": [int(window_start), int(window_end)]})
    return {
        "ok": not violations,
        "n_rows": int(df.shape[0]),
        "dedup_keys": list(DEDUP_KEYS),
        "violations": violations,
    }


def write_bank(df: pd.DataFrame, bank_path,
               *, window: Optional[tuple] = None) -> Dict[str, object]:
    """계보 stamp + dtype 캐스팅 + append 계약 통과 시 parquet 기록(F5 그릇).

    window 지정 시 append_contract 창 검사 포함. 계약 위반이면 쓰지 않고 receipt 반환.
    """
    stamped = stamp_lineage(df)
    ws, we = (window if window is not None else (0, 99999999))
    contract = append_contract(stamped, ws, we)
    receipt: Dict[str, object] = {
        "bank_path": str(bank_path), "n_rows": int(stamped.shape[0]),
        "onset_type": ONSET_TYPE, "exit_label": EXIT_LABEL,
        "source_seal": SOURCE_SEAL, "audit_tag": AUDIT_TAG,
        "dedup_keys": list(DEDUP_KEYS), "contract": contract, "written": False,
    }
    if not contract["ok"]:
        logger.warning("o3 bank 계약 위반 — 미기록: %s", contract["violations"])
        return receipt
    for col, dtype in BANK_SCHEMA.items():
        if dtype == "string":
            stamped[col] = stamped[col].astype("string")
        elif dtype == "bool":
            stamped[col] = stamped[col].astype(bool)
        else:
            stamped[col] = stamped[col].astype(dtype)
    Path(bank_path).parent.mkdir(parents=True, exist_ok=True)
    stamped.to_parquet(bank_path, index=False)
    receipt["written"] = True
    return receipt
