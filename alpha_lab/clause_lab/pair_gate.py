"""D1 2절 교호작용 — 무결성·자격 게이트 + D1 재현 대조 (봉인본 §4·§5·§4-3).

측정 착수 게이트(순서 고정, §14 운영 봉인):
  1. check_integrity — 은행·비트 parquet의 sha256·행수·스키마를 §4 봉인 지문과 대조.
     불일치 시 재검증 경로만 명시(자동 재검증 안 함 — 메인 판단).
  2. qualification_gate — **비트 11열 + 연도만으로** 짝 39의 4셀 계수(pooled·연도별)를
     산출해 자격 짝을 확정한다. **L3 컬럼 접촉 금지**(자기채점 차단 §5.1) — bank 미접촉.
  3. d1_reproduction_check — 판정 직전, 11절 주변 Δ(만족−미만족 L3 평균)를 재계산해
     D1 summary(소수 6자리)와 대조. >1e-6%p 면 중단(kill-3, §4-3). L3 접촉 — judge 단계.

짝 봉인(§3.2·§14-F1): 압력 P={1,4,10,37,38} × 가드 G={5,15,16,17,29,31} = 30 +
압력×압력 C(5,2)−{37,38} = 9 → **39짝**. 극성은 비트 저장 극성(만족=1) 그대로.
원본 read-only. 엔진 백테 0회. 신규 비트 산출 0(비트 행렬 재사용만).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import logging
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from alpha_lab.clause_lab.clauses import spec_by_num

logger = logging.getLogger(__name__)

__all__ = [
    "BANK_SHA256", "BITS_SHA256", "CELL_FLOOR_POOLED", "CELL_FLOOR_YEAR",
    "EXPECTED_ROWS", "FAMILY_PAIR_CAP", "GUARD", "PAIRS", "PRESSURE",
    "USED_CLAUSES", "YEARS",
    "check_integrity", "d1_reproduction_check", "family_pair_key",
    "four_cell_counts", "pair_id", "qualification_gate",
]

# §4 봉인 지문(2026-07-12 실측 — bit-identical 승계 근거).
BANK_SHA256 = "0b6268e0eff8e73831539aba8ff83b8a02608405269732a33c78565c3bfa22fd"
BITS_SHA256 = "4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56"
EXPECTED_ROWS = 863446
_BANK_SCHEMA = ("code", "day", "off", "t0", "year", "updown_q", "mktcap_b",
                "time_b", "l3_net", "l3_labeled", "l3_clause", "l3_exit")
_BITS_KEYS = ("code", "day", "off", "t0")

# §3.2 짝 족보 봉인.
PRESSURE: Tuple[int, ...] = (1, 4, 10, 37, 38)     # D1 load-bearing 압력 절.
GUARD: Tuple[int, ...] = (5, 15, 16, 17, 29, 31)   # D1 역생산 선정 가드 절.
_STRUCTURAL_EXCLUDE = frozenset({37, 38})          # §14-F1 — (¬37∧38) 구조적 공집합.
USED_CLAUSES: Tuple[int, ...] = PRESSURE + GUARD   # 비트 11열.

# §5.1·§14-F2 셀 하한.
CELL_FLOOR_POOLED = 2000
CELL_FLOOR_YEAR = 400
YEARS: Tuple[int, ...] = (2022, 2023)
FAMILY_PAIR_CAP = 22                               # §8 족-짝 상한.


def _build_pairs() -> Tuple[Tuple[int, int, str], ...]:
    """39짝 = 압력×가드 30 + 압력×압력 9(#37×#38 구조적 제외). (a, b, kind)."""
    out: List[Tuple[int, int, str]] = []
    for p in PRESSURE:
        for g in GUARD:
            out.append((p, g, "PxG"))
    for a, b in itertools.combinations(PRESSURE, 2):
        if frozenset({a, b}) == _STRUCTURAL_EXCLUDE:
            continue
        out.append((a, b, "PxP"))
    return tuple(out)


PAIRS: Tuple[Tuple[int, int, str], ...] = _build_pairs()


def pair_id(a: int, b: int) -> str:
    """짝 식별자 — 절 번호 정렬(대칭 I라 순서 무관, 표기만 고정)."""
    lo, hi = sorted((int(a), int(b)))
    return f"{lo}x{hi}"


def family_pair_key(a: int, b: int) -> str:
    """족-짝 키(§8) — 두 절의 밑변수 족 정렬 결합(근접 중복 인플레 차단)."""
    fa, fb = spec_by_num(a).family, spec_by_num(b).family
    return " × ".join(sorted((fa, fb)))


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_integrity(bank_path, bits_path) -> Dict[str, object]:
    """§4-1 지문 대조 — sha256·행수·스키마 vs 봉인값. 불일치 시 재검증 경로만 명시.

    read-only(파일 바이트 해시 + parquet 스키마 메타). 계수·L3 접촉 0.
    """
    def _one(path, exp_sha, exp_rows, exp_schema):
        p = Path(path)
        if not p.exists():
            return {"exists": False, "match": False, "note": "파일 부재"}
        meta = pq.ParquetFile(str(p))
        schema = tuple(meta.schema.names)
        rows = int(meta.metadata.num_rows)
        sha = _sha256(p)
        sha_ok, rows_ok = sha == exp_sha, rows == exp_rows
        schema_ok = tuple(schema) == tuple(exp_schema)
        return {
            "exists": True, "sha256": sha, "sha_match": sha_ok,
            "n_rows": rows, "rows_match": rows_ok,
            "schema": list(schema), "schema_match": schema_ok,
            "match": bool(sha_ok and rows_ok and schema_ok),
        }

    bits_schema = tuple(_BITS_KEYS) + tuple(f"bit_{n}" for n in range(1, 40))
    bank = _one(bank_path, BANK_SHA256, EXPECTED_ROWS, _BANK_SCHEMA)
    bits = _one(bits_path, BITS_SHA256, EXPECTED_ROWS, bits_schema)
    all_match = bool(bank.get("match") and bits.get("match"))
    result = {
        "kind": "d1_pairwise_integrity",
        "bank": bank, "bits": bits, "all_match": all_match,
        "expected": {"bank_sha256": BANK_SHA256, "bits_sha256": BITS_SHA256,
                     "n_rows": EXPECTED_ROWS},
    }
    if not all_match:
        result["reverify_path"] = (
            "지문 불일치 — 재사용 금지. §4-2 재검증 경로: ① 은행 = Jul-11 v2a npz "
            "대비 결정론 전수 대조(437일, off·L3 불일치 0) ② 비트 = P3 재현 게이트 "
            "재실행(온셋 100×39절 vs 엔진 exec 100%). 미달 시 kill-3. (자동 재검증은 "
            "메인 판단 — 본 게이트는 지문 대조까지만.)"
        )
    return result


def four_cell_counts(
    bit_a: np.ndarray, bit_b: np.ndarray, year: np.ndarray,
) -> Dict[str, np.ndarray]:
    """짝의 4셀(00·01·10·11) 계수 — pooled·연도별. cell = a*2 + b."""
    cell = bit_a.astype(np.int64) * 2 + bit_b.astype(np.int64)
    pooled = np.bincount(cell, minlength=4)
    per_year = {yr: np.bincount(cell[year == yr], minlength=4) for yr in YEARS}
    return {"pooled": pooled, "per_year": per_year}


def _qualify_pair(counts: Mapping[str, object]) -> Tuple[bool, str]:
    """4셀 계수 → (자격, 사유). 구조적 공집합·표본 희소 구분."""
    pooled = np.asarray(counts["pooled"])
    if int(pooled.min()) == 0:
        return False, "structural_empty"    # 4셀 중 하나가 정의역상 0.
    if pooled.min() < CELL_FLOOR_POOLED:
        return False, "sparse_pooled"
    for yr in YEARS:
        if np.asarray(counts["per_year"][yr]).min() < CELL_FLOOR_YEAR:
            return False, f"sparse_year_{yr}"
    return True, "qualified"


def qualification_gate(bits_path) -> Dict[str, object]:
    """§5 자격 게이트 — 비트 11열 + 연도만으로 짝 39의 4셀 계수·자격 확정.

    **L3 컬럼(l3_net·l3_labeled)을 읽지 않는다** — bits parquet 의 비트·day 만 읽는다
    (자기채점 차단). 자격 확정 후 분모 변경 금지(§5.1). 계수는 은행 전체 온셋 기준.
    """
    cols = ["day"] + [f"bit_{n}" for n in USED_CLAUSES]
    df = pd.read_parquet(bits_path, columns=cols)
    # 방어 assert — L3 파생 컬럼이 실수로 로드되지 않았음을 보증.
    forbidden = {"l3_net", "l3_labeled", "l3_clause", "l3_exit"}
    assert not (forbidden & set(df.columns)), "자격 게이트가 L3 컬럼을 읽었다(§5.1 위반)"
    year = (df["day"].to_numpy() // 10000).astype(np.int64)
    bits = {n: df[f"bit_{n}"].to_numpy().astype(bool) for n in USED_CLAUSES}

    per_pair: Dict[str, object] = {}
    qualified: List[str] = []
    for a, b, kind in PAIRS:
        counts = four_cell_counts(bits[a], bits[b], year)
        ok, reason = _qualify_pair(counts)
        pid = pair_id(a, b)
        per_pair[pid] = {
            "a": a, "b": b, "kind": kind, "family_pair": family_pair_key(a, b),
            "pooled": [int(x) for x in counts["pooled"]],
            "year_2022": [int(x) for x in counts["per_year"][2022]],
            "year_2023": [int(x) for x in counts["per_year"][2023]],
            "qualified": ok, "reason": reason,
            "cell_order": "00,01,10,11 (a*2+b)",
        }
        if ok:
            qualified.append(pid)
    return {
        "kind": "d1_pairwise_qualification",
        "n_pairs_total": len(PAIRS),
        "n_qualified": len(qualified),
        "fdr_denominator": len(qualified),
        "qualified_pairs": qualified,
        "cell_floor_pooled": CELL_FLOOR_POOLED,
        "cell_floor_year": CELL_FLOOR_YEAR,
        "per_pair": per_pair,
        "note": ("계수는 bits parquet 전체 온셋(863,446) 기준 — §5.1 'bits+연도만'. "
                 "판정(judge)은 l3_labeled 862,932에서 수행(차 514는 하한 여유 내)."),
    }


def d1_reproduction_check(
    bank_path, bits_path, d1_summary_path,
    *, tol: float = 1e-6,
) -> Dict[str, object]:
    """§4-3 — 11절 주변 Δ(만족−미만족 L3 평균 %p)를 D1 summary(6자리)와 대조.

    >tol 이면 pass=False(kill-3 — 파이프라인 결함 의심). 이 단계는 L3 를 읽으므로
    judge 단계(자격 확정 후)에서만 호출한다.
    """
    bank = pd.read_parquet(
        bank_path, columns=["code", "day", "off", "t0", "l3_net", "l3_labeled"])
    bit_cols = [f"bit_{n}" for n in USED_CLAUSES]
    bits = pd.read_parquet(bits_path, columns=list(_BITS_KEYS) + bit_cols)
    if bank.shape[0] != bits.shape[0]:
        raise ValueError("은행/비트 행수 불일치 — 위치 조인 불가(kill-3)")
    for k in _BITS_KEYS:
        if not np.array_equal(bank[k].to_numpy(), bits[k].to_numpy()):
            raise ValueError(f"은행/비트 조인 키 '{k}' 위치 불일치(kill-3)")

    labeled = bank["l3_labeled"].to_numpy().astype(bool)
    net_pp = bank["l3_net"].to_numpy(dtype=np.float64)[labeled] * 100.0
    d1 = json.loads(Path(d1_summary_path).read_text(encoding="utf-8"))
    per = d1["judgment"]["per_clause"]

    results: Dict[int, object] = {}
    max_err = 0.0
    for n in USED_CLAUSES:
        bit = bits[f"bit_{n}"].to_numpy().astype(bool)[labeled]
        delta = float(net_pp[bit].mean() - net_pp[~bit].mean())
        d1_delta = float(per[str(n)]["delta_pp"])
        err = abs(delta - d1_delta)
        max_err = max(max_err, err)
        results[n] = {"recomputed_delta_pp": round(delta, 8),
                      "d1_delta_pp": d1_delta, "abs_err": err}
    return {
        "kind": "d1_pairwise_reproduction",
        "n_labeled": int(labeled.sum()),
        "tol": tol, "max_abs_err": max_err,
        "pass": bool(max_err <= tol),
        "per_clause": results,
    }
