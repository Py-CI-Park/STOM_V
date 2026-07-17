"""O-4 측정 착수 게이트 — 무결성 지문 + 신규 비트 패리티 + 포함관계 sanity (봉인본 §5.2·§6·§14-F7).

순서(§6 순서 봉인의 게이트 층):
  1. check_reused_integrity — 은행(0b6268e0)·d1 비트(4df57b77) 지문 대조(pair_gate 재사용).
  2. check_o4_key_integrity — o4_candidate_bits 의 (code,day,off,t0) 키-집합이 d1 비트와 일치
     (행수 863,446·유일·전 키 매칭). 온셋 경로 결정론 재도출의 정합 검증.
  3. o4_parity_gate — 온셋 100건 × 신규 5비트를 엔진 exec(스칼라) 경로 값과 100% 대조
     (D1 P3 방식 — clause_lab.gate._scalar_namespace 재사용). 벡터 술어 전사 오류 차단.
  4. inclusion_sanity — 재도출 F4 격자의 단조 포함(0.50 ⊆ 0.35 ⊆ 0.22 ⊆ bit_37[0.2],
     bit_38[0.3] ∈ [0.35 ⊆ · ⊆ 0.22]) — 임계-단조성 위반 시 산출 결함.

원본 tick DB read-only. 엔진 백테 0회. L3 컬럼 미접촉(자기채점 차단 — 게이트는 비트만).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from alpha_lab.clause_lab.gate import _scalar_namespace, sample_onset_namespace
from alpha_lab.clause_lab.pair_gate import EXPECTED_ROWS, check_integrity
from alpha_lab.o4lab.bits import BIT_COLUMNS, KEY_COLUMNS, new_bit_masks
from alpha_lab.o4lab.grammar import NEW_BITS

logger = logging.getLogger(__name__)

__all__ = [
    "PARITY_SAMPLE",
    "check_o4_key_integrity",
    "check_reused_integrity",
    "inclusion_sanity",
    "o4_parity_gate",
    "run_gates",
]

PARITY_SAMPLE = 100          # §6 P3 방식 온셋 표본수(신규 비트 전사 대조).
SEED = 20260714              # §14-F12.

# 포함관계 sanity: 재도출 F4 격자 vs d1 원-임계 비트(단조 — mult ↑ ⟹ 만족 집합 ⊆).
#   f > g (배수) ⟹ {초당매수수량 > 매도총잔량*f} ⊆ {초당매수수량 > 매도총잔량*g} (매도총잔량 ≥ 0).
_F4_ORDER = [
    ("o4_qty_050", 0.50), ("o4_qty_035", 0.35), ("bit_38", 0.30),
    ("o4_qty_022", 0.22), ("bit_37", 0.20),
]


def check_reused_integrity(bank_path, bits_path) -> Dict[str, object]:
    """재사용 자산(은행·d1 비트) 지문 대조 — pair_gate.check_integrity 그대로(§4-1 미러)."""
    return check_integrity(bank_path, bits_path)


def check_o4_key_integrity(o4_bits_path, d1_bits_path) -> Dict[str, object]:
    """o4 신규 비트의 키-집합이 d1 비트와 일치하는지 검증(온셋 재도출 정합).

    행수·스키마·(code,day,off,t0) 유일성 + 전 키 정확 일치(정렬 후 배열 동등). L3 미접촉.
    """
    o4 = pd.read_parquet(o4_bits_path, columns=list(KEY_COLUMNS) + list(BIT_COLUMNS))
    d1 = pd.read_parquet(d1_bits_path, columns=list(KEY_COLUMNS))
    schema_ok = tuple(pq.ParquetFile(str(o4_bits_path)).schema.names) == (
        tuple(KEY_COLUMNS) + tuple(BIT_COLUMNS))
    rows_ok = int(o4.shape[0]) == EXPECTED_ROWS == int(d1.shape[0])
    n_dup = int(o4.duplicated(subset=list(KEY_COLUMNS)).sum())

    def _key_arr(df):
        return (df["code"].astype(str) + "|" + df["day"].astype(str) + "|"
                + df["off"].astype(str) + "|" + df["t0"].astype(str)).to_numpy()

    o4k = np.sort(_key_arr(o4))
    d1k = np.sort(_key_arr(d1))
    keys_match = bool(o4k.shape == d1k.shape and np.array_equal(o4k, d1k))
    return {
        "kind": "o4_key_integrity",
        "n_o4": int(o4.shape[0]), "n_d1": int(d1.shape[0]),
        "expected_rows": EXPECTED_ROWS, "rows_match": bool(rows_ok),
        "schema_match": bool(schema_ok), "n_key_dup": n_dup,
        "keys_match": keys_match,
        "pass": bool(rows_ok and schema_ok and n_dup == 0 and keys_match),
    }


def o4_parity_gate(db_dir, days: Sequence[str], *, sample: int = PARITY_SAMPLE,
                   seed: int = SEED) -> Dict[str, object]:
    """신규 5비트 벡터 술어 vs 엔진 exec(스칼라) 100% 일치(§6 P3 방식).

    스칼라 경로는 NEW_BITS 원문식을 온셋별 exec(엔진 미러 네임스페이스). 벡터 = new_bit_masks.
    """
    onset_ns, _window = sample_onset_namespace(db_dir, days, max(sample, 300))
    total = int(onset_ns["현재가"].shape[0])
    n = int(min(sample, total))
    rng = np.random.default_rng(seed)
    sel = (np.sort(rng.choice(total, size=n, replace=False))
           if total > n else np.arange(total))
    masks = new_bit_masks(onset_ns)
    per_bit: Dict[str, int] = {b: 0 for b in BIT_COLUMNS}
    mism: List[dict] = []
    for i in sel.tolist():
        g = _scalar_namespace(onset_ns, i)
        for b in BIT_COLUMNS:
            ref = bool(eval(NEW_BITS[b], {"__builtins__": {}}, g))
            vec = bool(masks[b][i])
            if ref == vec:
                per_bit[b] += 1
            elif len(mism) < 20:
                mism.append({"onset_row": int(i), "bit": b,
                             "raw": NEW_BITS[b], "vec": vec, "scalar": ref})
    n_eval = len(sel)
    agree = sum(per_bit.values())
    n_pairs = n_eval * len(BIT_COLUMNS)
    return {
        "kind": "o4_new_bit_parity",
        "n_onsets": n_eval, "n_bits": len(BIT_COLUMNS), "n_pairs": n_pairs,
        "n_agree": agree, "agreement_pct": (100.0 * agree / n_pairs) if n_pairs else 0.0,
        "n_mismatch": n_pairs - agree, "per_bit_agree": per_bit,
        "mismatches": mism, "pass": bool(n_pairs > 0 and agree == n_pairs),
    }


def inclusion_sanity(o4_bits_path, d1_bits_path) -> Dict[str, object]:
    """재도출 F4 격자의 단조 포함(0.50 ⊆ 0.35 ⊆ bit_38[0.3] ⊆ 0.22 ⊆ bit_37[0.2]).

    배수 ↑ ⟹ 만족 온셋 집합 ⊆ (매도총잔량 ≥ 0 전제). 위반 카운트 0 이어야 통과.
    L3 미접촉(비트 컬럼만). 은행/d1 비트 위치 조인 대신 키 병합(정합 보증).
    """
    o4 = pd.read_parquet(o4_bits_path,
                         columns=list(KEY_COLUMNS) + ["o4_qty_022", "o4_qty_035", "o4_qty_050"])
    d1 = pd.read_parquet(d1_bits_path, columns=list(KEY_COLUMNS) + ["bit_37", "bit_38"])
    merged = o4.merge(d1, on=list(KEY_COLUMNS), how="inner")
    if merged.shape[0] != o4.shape[0]:
        return {"kind": "o4_inclusion_sanity", "pass": False,
                "reason": f"키 병합 손실(o4={o4.shape[0]} merged={merged.shape[0]})"}
    col = {name: merged[name].to_numpy().astype(bool) for name, _ in _F4_ORDER}
    checks: List[dict] = []
    all_ok = True
    for i in range(len(_F4_ORDER) - 1):
        (hi_name, hi_m), (lo_name, lo_m) = _F4_ORDER[i], _F4_ORDER[i + 1]
        # hi_m > lo_m ⟹ {hi} ⊆ {lo}: 위반 = hi 만족인데 lo 미만족.
        viol = int((col[hi_name] & ~col[lo_name]).sum())
        ok = viol == 0
        all_ok = all_ok and ok
        checks.append({"subset": hi_name, "superset": lo_name,
                       "subset_mult": hi_m, "superset_mult": lo_m,
                       "n_violation": viol, "pass": ok})
    return {"kind": "o4_inclusion_sanity", "n_onsets": int(merged.shape[0]),
            "checks": checks, "pass": bool(all_ok)}


def run_gates(bank_path, d1_bits_path, o4_bits_path, db_dir, days: Sequence[str]
              ) -> Dict[str, object]:
    """전 게이트 순서 실행 → 종합 리포트. 하나라도 실패면 gate_pass=False(judge 진입 금지)."""
    integ = check_reused_integrity(bank_path, d1_bits_path)
    key = check_o4_key_integrity(o4_bits_path, d1_bits_path)
    parity = o4_parity_gate(db_dir, days)
    incl = inclusion_sanity(o4_bits_path, d1_bits_path)
    gate_pass = bool(integ.get("all_match") and key["pass"]
                     and parity["pass"] and incl["pass"])
    return {
        "kind": "o4_gate_report",
        "reused_integrity": integ, "o4_key_integrity": key,
        "new_bit_parity": parity, "inclusion_sanity": incl,
        "gate_pass": gate_pass,
    }
