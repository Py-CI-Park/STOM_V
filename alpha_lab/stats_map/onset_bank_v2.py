"""온셋×출구 은행 v2 스키마 그릇 — WBS v3 P2 (적재는 각 연구의 봉인에 종속).

v1 은행(`onset_l3_bank.parquet`, 서지 온셋 863,446건, L3=RR8_12 출구,
d1 사전등록 §13-F1 승인 산출물)은 "서지 온셋 × RR8_12 출구" 단일 조합 전제였다.
v2 는 후속 연구(O-3 돌파 온셋, D5 D9 전이 온셋, min 오버레이)가 **각자의 봉인
이후** 같은 은행에 합류할 수 있도록 계보 컬럼 4개를 추가한 일반화 스키마다:

- ``onset_type``  : 온셋 유형(``surge``/``breakout``/``d9_transition``) — 닫힌 집합.
- ``exit_label``  : 출구 라벨 계보(예: ``L3_RR8_12``) — 열린 집합(봉인 문서가 정의).
- ``source_seal`` : 적재 근거 사전등록(봉인 문서) 파일명 — 행 단위 계보 추적.
- ``audit_tag``   : 지위 딱지(예: ``RR8_12-conditional``/``audit-grade``) —
  대시보드 워터마크·해석 한계 강제용(감사 구속 A11).

이 모듈은 **그릇만** 정의한다. 실물 적재/변환은 하지 않는다:
- ``migrate_v1_to_v2`` 는 기본 ``dry_run=True`` 로 행수·스키마 검증 영수증 dict 만
  반환한다(전량 로드 없이 parquet 스키마·메타데이터만 판독). ``dry_run=False``
  실행은 해당 연구의 봉인 문서가 존재할 때만 쓰며, 기존 파일 덮어쓰기를 거부한다.
- ``append_contract`` 는 새 온셋 배치를 붙이기 **전**의 검증 계약이다(스키마
  일치·창 범위·(day, code, t0) 중복 키 검출) — 판정만 하고 아무것도 쓰지 않는다.
- ``MIN_OVERLAY_SCHEMA`` 는 min DB 오버레이의 최소 골격 스텁(정의만)이다.

규율: 원본 parquet 는 read-only. known 창 데이터 측정 없음(이 모듈은 측정 없음).
"""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

__all__ = [
    "BANK_V1_SCHEMA",
    "BANK_V2_NEW_COLUMNS",
    "BANK_V2_SCHEMA",
    "KNOWN_AUDIT_TAGS",
    "KNOWN_EXIT_LABELS",
    "MIN_OVERLAY_REQUIRED_AUDIT_TAG",
    "MIN_OVERLAY_SCHEMA",
    "ONSET_TYPES",
    "append_contract",
    "migrate_v1_to_v2",
    "read_parquet_schema_map",
]

# ── 온셋 유형(닫힌 집합) — 계획 §3 "지도 추가 적재" 3계보 ──────────────────────
#   surge         : L1 서지 온셋(2.0×·쿨다운 30초) — v1 은행의 원 계보(D1 §5).
#   breakout      : 돌파 온셋 — O-3 사전등록 봉인 후에만 적재.
#   d9_transition : D9 전이 온셋 — D5 사전등록 봉인 후에만 적재.
ONSET_TYPES: Tuple[str, ...] = ("surge", "breakout", "d9_transition")

# ── v1 실측 스키마 (2026-07-12 pq.read_schema 실측, 863,446행) ────────────────
# 실물: code=large_string, l3_net=double — 정준화 규칙(string 계열→"string",
# double→"float64")을 거친 값으로 봉인한다. 컬럼 구성·순서는
# clause_lab.bank.BANK_COLUMNS(은행 생산자)와 동일하다.
BANK_V1_SCHEMA: Mapping[str, str] = MappingProxyType({
    "code": "string",        # 종목코드 6자리
    "day": "int32",          # yyyymmdd
    "off": "int16",          # 09:00 기준 초 오프셋
    "t0": "int64",           # 온셋 시각 index(yyyymmddHHMMSS)
    "year": "int16",         # 연도(2022/2023 발견창)
    "updown_q": "int8",      # 등락율 분위 버킷
    "mktcap_b": "int8",      # 시가총액 버킷
    "time_b": "int8",        # 시간대 버킷
    "l3_net": "float64",     # L3 반사실 실현 순손익(%)
    "l3_labeled": "bool",    # 라벨 성립 여부
    "l3_clause": "int16",    # 청산 분기 번호
    "l3_exit": "int64",      # 청산 시각 index(-1=미성립)
})

# ── v2 신규 컬럼 4개 — 전부 필수(빈 값 금지) ─────────────────────────────────
BANK_V2_NEW_COLUMNS: Mapping[str, str] = MappingProxyType({
    "onset_type": "string",   # ONSET_TYPES 중 하나
    "exit_label": "string",   # 예: 'L3_RR8_12'
    "source_seal": "string",  # 봉인(사전등록) 문서 파일명
    "audit_tag": "string",    # 예: 'RR8_12-conditional' | 'audit-grade'
})

BANK_V2_SCHEMA: Mapping[str, str] = MappingProxyType(
    {**BANK_V1_SCHEMA, **BANK_V2_NEW_COLUMNS})

# 참고용(열린 집합 — 새 값은 해당 봉인 문서가 정의하며 여기 등재는 사후 목록화).
KNOWN_EXIT_LABELS: Tuple[str, ...] = ("L3_RR8_12",)
KNOWN_AUDIT_TAGS: Tuple[str, ...] = ("RR8_12-conditional", "audit-grade")

# ── min DB 오버레이 스키마 스텁 — 정의만(계획 §3 ③) ──────────────────────────
# min 계열 산출물은 프로브 판정상 audit-grade 전용이다(자동 veto·성능 주장 금지).
# 따라서 audit_tag 컬럼이 필수이며 값은 MIN_OVERLAY_REQUIRED_AUDIT_TAG 로 고정한다.
# 측정 컬럼(min_* 접두)은 각 연구의 사전등록이 추가 정의한다 — 이 스텁은 조인 키와
# 필수 딱지 골격만 봉인한다.
MIN_OVERLAY_SCHEMA: Mapping[str, str] = MappingProxyType({
    "code": "string",         # 은행 v2 조인 키
    "day": "int32",           # 은행 v2 조인 키(yyyymmdd)
    "t0": "int64",            # 은행 v2 조인 키(온셋 시각 index)
    "audit_tag": "string",    # 필수 — 'audit-grade' 고정
    "source_seal": "string",  # 필수 — 산출 근거 봉인 문서 파일명
})
MIN_OVERLAY_REQUIRED_AUDIT_TAG: str = "audit-grade"

_DUP_LIST_CAP = 20  # 영수증에 나열하는 중복/충돌 키 상한(전체 수는 별도 계수)

DayLike = Union[int, str]
KeySource = Union[pd.DataFrame, Iterable[Tuple[object, object, object]]]


# ── 스키마 판독·대조 유틸 ────────────────────────────────────────────────────
def _normalize_arrow_type(t: pa.DataType) -> str:
    """pyarrow 타입 → 정준 dtype 문자열(string/large_string 동일 취급)."""
    if pa.types.is_string(t) or pa.types.is_large_string(t):
        return "string"
    if pa.types.is_float64(t):
        return "float64"
    return str(t)  # int8/int16/int32/int64/bool 등은 이름 그대로


def read_parquet_schema_map(path) -> Dict[str, str]:
    """parquet 의 {컬럼: 정준 dtype} 지도 — 스키마만 판독(전량 로드 금지)."""
    schema = pq.read_schema(str(path))
    return {f.name: _normalize_arrow_type(f.type) for f in schema}


def _normalize_pandas_dtype(dtype) -> str:
    """pandas dtype → 정준 dtype 문자열(object/str/string 계열→"string").

    pandas 3 계열은 문자열 컬럼을 'str'(StringDtype)로 표기하므로 함께 정준화한다.
    """
    name = str(dtype)
    if name in ("object", "str") or name.startswith(("string", "large_string")):
        return "string"
    return name


def _diff_schema(actual: Mapping[str, str],
                 expected: Mapping[str, str]) -> Dict[str, List]:
    """실측 vs 기대 스키마 차이 — 누락·잉여·dtype 불일치(순서는 비교 안 함)."""
    missing = [c for c in expected if c not in actual]
    unexpected = [c for c in actual if c not in expected]
    dtype_mismatch = [
        {"column": c, "expected": expected[c], "actual": actual[c]}
        for c in expected if c in actual and actual[c] != expected[c]
    ]
    return {"missing": missing, "unexpected": unexpected,
            "dtype_mismatch": dtype_mismatch}


def _validate_v2_labels(onset_type: str, exit_label: str,
                        source_seal: str, audit_tag: str) -> None:
    """신규 4컬럼 상수값 사전 검증 — 위반 시 ValueError(그릇 오염 차단)."""
    if onset_type not in ONSET_TYPES:
        raise ValueError(
            f"onset_type={onset_type!r} 는 허용 집합 {ONSET_TYPES} 밖이다")
    for name, value in (("exit_label", exit_label),
                        ("source_seal", source_seal),
                        ("audit_tag", audit_tag)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} 는 비어 있지 않은 문자열이어야 한다: {value!r}")


# ── v1 → v2 마이그레이션 (기본 dry_run — 실물 생성 없음) ─────────────────────
def migrate_v1_to_v2(src, dst, *, source_seal: str, onset_type: str = "surge",
                     exit_label: str = "L3_RR8_12",
                     audit_tag: str = "RR8_12-conditional",
                     dry_run: bool = True) -> Dict[str, object]:
    """v1 은행 → v2 마이그레이션 — 신규 4컬럼 추가만, 기존 컬럼 값 불변.

    dry_run=True(기본): 어떤 파일도 만들지 않고 src 의 행수·스키마를 검증한
    영수증 dict 만 반환한다(pq 메타데이터만 판독 — 전량 로드 없음).
    dry_run=False: v1 스키마 완전 일치일 때만 dst 를 새로 쓴다(기존 dst 덮어쓰기
    거부). 이 경로는 해당 연구의 봉인 문서(source_seal)가 존재할 때만 쓴다.
    """
    _validate_v2_labels(onset_type, exit_label, source_seal, audit_tag)
    src_p, dst_p = Path(src), Path(dst)
    if not src_p.is_file():
        raise FileNotFoundError(f"v1 은행 파일 없음: {src_p}")
    actual = read_parquet_schema_map(src_p)
    n_rows = int(pq.ParquetFile(str(src_p)).metadata.num_rows)
    diff = _diff_schema(actual, BANK_V1_SCHEMA)
    schema_ok = not (diff["missing"] or diff["unexpected"] or diff["dtype_mismatch"])
    receipt: Dict[str, object] = {
        "mode": "dry_run" if dry_run else "migrate",
        "src": str(src_p), "dst": str(dst_p),
        "n_rows_src": n_rows, "n_columns_src": len(actual),
        "v1_schema_ok": schema_ok, "schema_diff": diff,
        "order_match": list(actual) == list(BANK_V1_SCHEMA),
        "v2_columns": list(BANK_V2_SCHEMA),
        "new_column_values": {"onset_type": onset_type, "exit_label": exit_label,
                              "source_seal": source_seal, "audit_tag": audit_tag},
        "dst_exists": dst_p.exists(), "created": False,
    }
    if dry_run:
        return receipt
    if not schema_ok:
        raise ValueError(f"v1 스키마 불일치 — 마이그레이션 거부: {diff}")
    if dst_p.exists():
        raise FileExistsError(f"dst 가 이미 존재 — 덮어쓰기 금지: {dst_p}")
    frame = pd.read_parquet(src_p)
    out = frame.assign(onset_type=onset_type, exit_label=exit_label,
                       source_seal=source_seal, audit_tag=audit_tag)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dst_p, index=False)
    receipt.update(created=True, n_rows_written=int(out.shape[0]))
    return receipt


# ── append 계약 — 후속 연구가 새 온셋을 붙이기 전의 검증(쓰기 없음) ──────────
def _as_day(value: DayLike, name: str) -> int:
    """yyyymmdd 정수/문자열 → int. 형식 위반은 ValueError."""
    try:
        day = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 는 yyyymmdd 여야 한다: {value!r}") from exc
    if not 19000101 <= day <= 29991231:
        raise ValueError(f"{name} 가 yyyymmdd 범위 밖이다: {day}")
    return day


def _check_schema_df(df: pd.DataFrame) -> List[Dict[str, object]]:
    """배치 스키마 검사 — v2 전 컬럼 존재·잉여 없음·dtype 정합."""
    violations: List[Dict[str, object]] = []
    if df.shape[0] == 0:
        violations.append({"check": "schema", "kind": "empty_batch"})
    actual = {c: _normalize_pandas_dtype(df[c].dtype) for c in df.columns}
    diff = _diff_schema(actual, BANK_V2_SCHEMA)
    if diff["missing"]:
        violations.append({"check": "schema", "kind": "missing_column",
                           "columns": diff["missing"]})
    if diff["unexpected"]:
        violations.append({"check": "schema", "kind": "unexpected_column",
                           "columns": diff["unexpected"]})
    if diff["dtype_mismatch"]:
        violations.append({"check": "schema", "kind": "dtype_mismatch",
                           "entries": diff["dtype_mismatch"]})
    return violations


def _check_label_values(df: pd.DataFrame,
                        expected_onset_type: str) -> List[Dict[str, object]]:
    """신규 4컬럼 값 검사 — onset_type 일치·필수 3컬럼 비공백 문자열."""
    violations: List[Dict[str, object]] = []
    if "onset_type" in df.columns and df.shape[0] > 0:
        vals = df["onset_type"]
        bad = ~(vals == expected_onset_type)
        if bool(bad.any()):
            observed = sorted({str(v) for v in vals[bad].dropna().unique()})
            violations.append({
                "check": "labels", "kind": "onset_type_mismatch",
                "expected": expected_onset_type, "n_bad": int(bad.sum()),
                "observed": observed[:_DUP_LIST_CAP]})
    for col in ("exit_label", "source_seal", "audit_tag"):
        if col not in df.columns or df.shape[0] == 0:
            continue  # 컬럼 부재는 스키마 검사가 이미 위반으로 계상
        ok = df[col].map(lambda v: isinstance(v, str) and bool(v.strip()))
        n_bad = int((~ok).sum())
        if n_bad:
            violations.append({"check": "labels", "kind": "empty_required",
                               "column": col, "n_bad": n_bad})
    return violations


def _check_window(df: pd.DataFrame, window_start: int,
                  window_end: int) -> List[Dict[str, object]]:
    """창 범위 검사 — day 가 [window_start, window_end] 안인지."""
    if "day" not in df.columns or df.shape[0] == 0:
        return []
    days = pd.to_numeric(df["day"], errors="coerce")
    bad = days.isna() | (days < window_start) | (days > window_end)
    if not bool(bad.any()):
        return []
    valid = days[~days.isna()]
    return [{
        "check": "window", "kind": "day_out_of_range",
        "n_bad": int(bad.sum()), "window": [window_start, window_end],
        "day_min": int(valid.min()) if len(valid) else None,
        "day_max": int(valid.max()) if len(valid) else None,
    }]


def _existing_key_set(existing_keys: Optional[KeySource]) -> Optional[set]:
    """기존 은행 키 소스(DataFrame 또는 (day,code,t0) 튜플들) → set."""
    if existing_keys is None:
        return None
    if isinstance(existing_keys, pd.DataFrame):
        cols = ["day", "code", "t0"]
        missing = [c for c in cols if c not in existing_keys.columns]
        if missing:
            raise ValueError(f"existing_keys DataFrame 에 키 컬럼 부재: {missing}")
        return set(existing_keys[cols].itertuples(index=False, name=None))
    return {tuple(k) for k in existing_keys}


def _check_dup_keys(df: pd.DataFrame,
                    existing: Optional[set]) -> List[Dict[str, object]]:
    """(day, code, t0) 중복 검사 — 배치 내부 + (지정 시) 기존 은행과의 충돌."""
    keys = ["day", "code", "t0"]
    if any(c not in df.columns for c in keys) or df.shape[0] == 0:
        return []  # 키 컬럼 부재는 스키마 검사가 위반으로 계상
    violations: List[Dict[str, object]] = []
    tuples = [(int(d), str(c), int(t)) for d, c, t
              in df[keys].itertuples(index=False, name=None)]
    dup_mask = df.duplicated(subset=keys, keep=False)
    if bool(dup_mask.any()):
        dups = sorted({t for t, m in zip(tuples, dup_mask) if m})
        violations.append({"check": "dup_key", "kind": "duplicate_in_batch",
                           "n_bad": int(dup_mask.sum()),
                           "keys": dups[:_DUP_LIST_CAP]})
    if existing is not None:
        hits = sorted({t for t in tuples if t in existing})
        if hits:
            violations.append({"check": "dup_key", "kind": "collision_with_bank",
                               "n_bad": len(hits),
                               "keys": hits[:_DUP_LIST_CAP]})
    return violations


def append_contract(df: pd.DataFrame, expected_onset_type: str,
                    window_start: DayLike, window_end: DayLike, *,
                    existing_keys: Optional[KeySource] = None
                    ) -> Dict[str, object]:
    """새 온셋 배치를 v2 은행에 붙이기 전의 검증 계약 — 판정만, 쓰기 없음.

    검사 3계열: ① 스키마 일치(BANK_V2_SCHEMA 전 컬럼·dtype·신규 4컬럼 유효값)
    ② 창 범위(day ∈ [window_start, window_end], yyyymmdd — 봉인 문서의 창)
    ③ (day, code, t0) 중복 키(배치 내부 + existing_keys 지정 시 기존 은행 충돌).

    반환 dict: ok(전 검사 통과 여부)·violations(위반 목록)·n_rows 등. 위반이
    있으면 적재하지 않는 것이 계약이다(적재 자체는 각 연구의 봉인에 종속).
    """
    if expected_onset_type not in ONSET_TYPES:
        raise ValueError(
            f"expected_onset_type={expected_onset_type!r} 는 {ONSET_TYPES} 밖이다")
    ws, we = _as_day(window_start, "window_start"), _as_day(window_end, "window_end")
    if ws > we:
        raise ValueError(f"창 역전: window_start={ws} > window_end={we}")
    violations: List[Dict[str, object]] = []
    violations += _check_schema_df(df)
    violations += _check_label_values(df, expected_onset_type)
    violations += _check_window(df, ws, we)
    violations += _check_dup_keys(df, _existing_key_set(existing_keys))
    failed = {v["check"] for v in violations}
    return {
        "ok": not violations,
        "n_rows": int(df.shape[0]),
        "expected_onset_type": expected_onset_type,
        "window": [ws, we],
        "checks": {name: name not in failed
                   for name in ("schema", "labels", "window", "dup_key")},
        "violations": violations,
    }
