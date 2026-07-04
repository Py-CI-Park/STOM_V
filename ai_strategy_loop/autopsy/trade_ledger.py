"""T2.5 거래 원장(Trade Ledger) — 후보별 전체 거래행 + 진입 컨텍스트(B_*) 영속 저장.

후보 identity 는 (run_id, candidate_id, buy_sha256, sell_sha256) 4-튜플이다.
저장 백엔드는 자동 감지한다:
  - pyarrow 가 설치되어 있으면 parquet (후보별 파일 1개 + 결정론 manifest JSON).
  - 없으면 sqlite3 (표준 라이브러리, 단일 DB 파일) — 외부 의존성 추가 금지 계약.

계약:
  - append_trades(meta, trades_df) : 원본 df 를 절대 변형하지 않고(불변성) 정본
    스키마(LEDGER_COLUMNS)로 정규화해 저장한다. 원천에 없는 컬럼(R_MFE/R_MAE 포함)은
    결측(None) 허용 — MFE/MAE 계산 로직은 이 모듈 범위 밖이다.
  - load_trades(filters)          : meta 필드 필터(run_id/candidate_id/…)로 조회.
  - cohort_compare(a, b)          : 동일 거래일(trade_date, 매수시간 앞 8자리) 교집합
    에서 양측 거래수/손익을 비교한 dict 를 반환한다. 데이터 모양 문제(빈 후보,
    공통 거래일 없음)는 예외 없이 status 필드로 보고한다(autopsy 관례).
  - 모든 행에 schema_version 필드를 포함하고, 컬럼 순서·정렬·직렬화는 결정론적이다.

ValueError 는 계약 위반에만 던진다: meta 필수 필드 누락, 미지 필터 키,
정본 컬럼이 하나도 없는 비어있지 않은 df.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from .analyze import B_COLUMNS, MAE_COLUMN, MFE_COLUMN, RETURN_COLUMN

# 원장 스키마 버전 — 행마다 저장되고 cohort_compare 결과에도 포함된다.
TRADE_LEDGER_SCHEMA_VERSION = 1

# 거래일 파생 원본 컬럼: 매수시간(YYYYMMDDHHMM(SS)) 앞 8자리 → 거래일 정수.
#   cli/research_metrics.py 의 _trade_date 파생과 동일 의미.
BUY_TIME_COLUMN = "매수시간"
PROFIT_COLUMN = "수익금"

# 청산 스냅샷(S_*) / 거래당 결과(R_*) 컬럼 — backtest/back_static.py 와 동일 순서.
S_COLUMNS: Tuple[str, ...] = (
    "S_현재가", "S_등락율", "S_체결강도", "S_매수총잔량", "S_매도총잔량",
)
R_COLUMNS: Tuple[str, ...] = (MFE_COLUMN, MAE_COLUMN, "R_MFE", "R_MAE")

# 문자형 정본 컬럼(그 외 정본 컬럼은 전부 수치형으로 강제 저장).
TEXT_TRADE_COLUMNS: Tuple[str, ...] = (
    "종목코드", "종목명", "시가총액", "매도조건", "추가매수시간",
)

# 정본 거래행 컬럼 순서 — GetResultDataframe(df_tsg) 컬럼 순서를 따른다.
#   원천 df 에 없는 컬럼은 결측(None)으로 채워 스키마를 고정한다(결정론 직렬화).
LEDGER_COLUMNS: Tuple[str, ...] = (
    "종목코드", "종목명", "시가총액", "매수시간", "매도시간", "보유시간",
    "매수가", "매도가", "매수금액", "매도금액", "수익률", "수익금", "수익금합계",
    "매도조건", "추가매수시간",
    *B_COLUMNS,
    *S_COLUMNS,
    *R_COLUMNS,
)

_TEXT_SET = frozenset(TEXT_TRADE_COLUMNS)
NUMERIC_TRADE_COLUMNS: Tuple[str, ...] = tuple(
    c for c in LEDGER_COLUMNS if c not in _TEXT_SET
)
_NUMERIC_SET = frozenset(NUMERIC_TRADE_COLUMNS)

# meta 필터로 허용되는 키 == 후보 identity 4-튜플.
META_FILTER_KEYS: Tuple[str, ...] = (
    "run_id", "candidate_id", "buy_sha256", "sell_sha256",
)
META_COLUMNS: Tuple[str, ...] = ("schema_version",) + META_FILTER_KEYS
DATE_COLUMN = "trade_date"

# 저장 프레임 전체 컬럼 순서(결정론) = meta + 거래일 + 정본 거래행.
FULL_COLUMNS: Tuple[str, ...] = META_COLUMNS + (DATE_COLUMN,) + LEDGER_COLUMNS

# cohort_compare status 코드 — 데이터 모양 문제는 무예외로 status 반환(autopsy 관례).
COMPARE_STATUS_OK = "ok"
COMPARE_STATUS_EMPTY = "empty_candidate"
COMPARE_STATUS_NO_COMMON = "no_common_dates"

_SQLITE_FILENAME = "trade_ledger.sqlite3"
_PARQUET_DIRNAME = "parquet"
_MANIFEST_FILENAME = "trade_ledger_manifest.json"

__all__ = [
    "TRADE_LEDGER_SCHEMA_VERSION",
    "LEDGER_COLUMNS",
    "NUMERIC_TRADE_COLUMNS",
    "TEXT_TRADE_COLUMNS",
    "META_FILTER_KEYS",
    "FULL_COLUMNS",
    "DATE_COLUMN",
    "COMPARE_STATUS_OK",
    "COMPARE_STATUS_EMPTY",
    "COMPARE_STATUS_NO_COMMON",
    "TradeLedgerMeta",
    "TradeLedger",
    "frame_to_records",
]


@dataclass(frozen=True)
class TradeLedgerMeta:
    """후보 identity — 원장에 저장되는 모든 행의 meta 필드.

    run_id/candidate_id 는 필수(공백 불가). buy/sell sha256 은 문자열 강제
    (조건식이 없는 쪽은 빈 문자열 허용 — identity 는 여전히 4-튜플).
    """

    run_id: str
    candidate_id: str
    buy_sha256: str = ""
    sell_sha256: str = ""

    def __post_init__(self) -> None:
        for name in ("run_id", "candidate_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"meta_field_required: {name}")
        for name in ("buy_sha256", "sell_sha256"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"meta_field_must_be_str: {name}")

    def as_dict(self) -> Dict[str, str]:
        """META_FILTER_KEYS 순서 고정 dict (결정론 직렬화용)."""
        return {key: getattr(self, key) for key in META_FILTER_KEYS}


# ---------------------------------------------------------------------
# 공용 헬퍼 — 값 정규화 / 프레임 구성 (전부 순수 함수, 입력 불변).
# ---------------------------------------------------------------------
def _parquet_available() -> bool:
    """pyarrow 설치 여부 — parquet 백엔드 자동 감지."""
    try:
        import pyarrow  # noqa: F401
    except Exception:
        return False
    return True


def _is_missing(value: object) -> bool:
    """스칼라 결측 판정 (None / NaN / pd.NA)."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _to_float(value: object) -> Optional[float]:
    """수치형 정본 컬럼 값 → float 또는 None (강제 불가 값도 None)."""
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_text(value: object) -> Optional[str]:
    """문자형 정본 컬럼 값 → str 또는 None."""
    if _is_missing(value):
        return None
    return str(value)


def _round6(value: Optional[float]) -> Optional[float]:
    """비교 리포트용 반올림(6자리) — int/None 은 그대로."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return round(float(value), 6)


def _derive_trade_dates(series: pd.Series) -> List[Optional[int]]:
    """매수시간(YYYYMMDDHHMM(SS)) → 앞 8자리 거래일 정수 리스트 (파싱 불가는 None)."""
    numeric = pd.to_numeric(series, errors="coerce")
    dates: List[Optional[int]] = []
    for value in numeric.tolist():
        if _is_missing(value):
            dates.append(None)
            continue
        text = str(int(value))
        dates.append(int(text[:8]) if len(text) >= 8 else None)
    return dates


def _finalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """저장/조회 공용 타입 고정 — 컬럼 순서와 dtype 을 결정론적으로 맞춘다."""
    out = frame.reindex(columns=list(FULL_COLUMNS)).copy()
    out["schema_version"] = pd.to_numeric(
        out["schema_version"], errors="coerce"
    ).astype("int64")
    out[DATE_COLUMN] = pd.to_numeric(out[DATE_COLUMN], errors="coerce").astype("Int64")
    for column in NUMERIC_TRADE_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce").astype("float64")
    return out


def _empty_ledger_frame() -> pd.DataFrame:
    """행 0개, 정본 스키마 고정 프레임."""
    return _finalize_frame(pd.DataFrame({c: [] for c in FULL_COLUMNS}))


def _build_frame(meta: TradeLedgerMeta, trades_df: pd.DataFrame) -> pd.DataFrame:
    """원천 거래 df → 정본 저장 프레임 (원천 df 는 절대 변형하지 않는다)."""
    row_count = len(trades_df)
    data: Dict[str, list] = {
        "schema_version": [TRADE_LEDGER_SCHEMA_VERSION] * row_count,
        "run_id": [meta.run_id] * row_count,
        "candidate_id": [meta.candidate_id] * row_count,
        "buy_sha256": [meta.buy_sha256] * row_count,
        "sell_sha256": [meta.sell_sha256] * row_count,
    }
    if BUY_TIME_COLUMN in trades_df.columns:
        data[DATE_COLUMN] = _derive_trade_dates(trades_df[BUY_TIME_COLUMN])
    else:
        data[DATE_COLUMN] = [None] * row_count
    for column in LEDGER_COLUMNS:
        if column in trades_df.columns:
            values = trades_df[column].tolist()
            if column in _NUMERIC_SET:
                data[column] = [_to_float(v) for v in values]
            else:
                data[column] = [_to_text(v) for v in values]
        else:
            data[column] = [None] * row_count
    return _finalize_frame(pd.DataFrame(data, columns=list(FULL_COLUMNS)))


def frame_to_records(frame: pd.DataFrame) -> List[Dict[str, object]]:
    """저장 프레임 → JSON-안전 레코드 리스트 (컬럼 순서 고정, NaN→None, 결정론)."""
    records: List[Dict[str, object]] = []
    for position in range(len(frame)):
        record: Dict[str, object] = {}
        for column in FULL_COLUMNS:
            value = frame[column].iloc[position]
            if _is_missing(value):
                record[column] = None
            elif column == "schema_version" or column == DATE_COLUMN:
                record[column] = int(value)
            elif column in _NUMERIC_SET:
                record[column] = float(value)
            else:
                record[column] = str(value)
        records.append(record)
    return records


def _validate_filters(filters: Optional[Mapping]) -> Dict[str, str]:
    """필터 검증 — 미지 키/비문자 값은 계약 위반(ValueError)."""
    if filters is None:
        return {}
    if not isinstance(filters, Mapping):
        raise ValueError("filters_must_be_mapping")
    resolved: Dict[str, str] = {}
    for key in META_FILTER_KEYS:
        if key not in filters:
            continue
        value = filters[key]
        if not isinstance(value, str) or not value:
            raise ValueError(f"filter_value_must_be_str: {key}")
        resolved[key] = value
    unknown = sorted(set(filters) - set(META_FILTER_KEYS))
    if unknown:
        raise ValueError(f"unknown_filter_keys: {', '.join(unknown)}")
    return resolved


def _coerce_meta(meta: Union[TradeLedgerMeta, Mapping]) -> TradeLedgerMeta:
    """TradeLedgerMeta 또는 Mapping → 검증된 TradeLedgerMeta (여분 키는 무시)."""
    if isinstance(meta, TradeLedgerMeta):
        return meta
    if isinstance(meta, Mapping):
        return TradeLedgerMeta(
            run_id=meta.get("run_id", ""),
            candidate_id=meta.get("candidate_id", ""),
            buy_sha256=meta.get("buy_sha256", ""),
            sell_sha256=meta.get("sell_sha256", ""),
        )
    raise ValueError("meta_must_be_meta_or_mapping")


# ---------------------------------------------------------------------
# sqlite 백엔드 (표준 라이브러리) — pyarrow 부재 시 기본 경로.
# ---------------------------------------------------------------------
def _quote(name: str) -> str:
    """식별자 인용 — 한글 컬럼명 안전 처리 (값 바인딩은 전부 ? 파라미터)."""
    return '"' + name.replace('"', '""') + '"'


class _SqliteBackend:
    """단일 DB 파일(trades 테이블), rowid 순서 = 삽입 순서(결정론 조회)."""

    name = "sqlite"

    def __init__(self, root: Path) -> None:
        self._path = root / _SQLITE_FILENAME
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path))

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, TRADE_LEDGER_SCHEMA_VERSION):
                raise ValueError(f"ledger_schema_version_mismatch: {version}")
            column_defs = ['"schema_version" INTEGER NOT NULL']
            column_defs += [f"{_quote(k)} TEXT NOT NULL" for k in META_FILTER_KEYS]
            column_defs.append(f"{_quote(DATE_COLUMN)} INTEGER")
            for column in LEDGER_COLUMNS:
                kind = "REAL" if column in _NUMERIC_SET else "TEXT"
                column_defs.append(f"{_quote(column)} {kind}")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS trades (" + ", ".join(column_defs) + ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_meta"
                " ON trades (run_id, candidate_id)"
            )
            conn.execute(f"PRAGMA user_version = {TRADE_LEDGER_SCHEMA_VERSION}")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _frame_to_rows(frame: pd.DataFrame) -> List[tuple]:
        """타입 고정 프레임 → sqlite 바인딩 가능한 순수 파이썬 튜플 리스트."""
        columns: List[list] = []
        for column in FULL_COLUMNS:
            values = frame[column].tolist()
            if column == "schema_version":
                columns.append([int(v) for v in values])
            elif column in META_FILTER_KEYS:
                columns.append([str(v) for v in values])
            elif column == DATE_COLUMN:
                columns.append([None if pd.isna(v) else int(v) for v in values])
            elif column in _NUMERIC_SET:
                columns.append([None if _is_missing(v) else float(v) for v in values])
            else:
                columns.append([None if _is_missing(v) else str(v) for v in values])
        return list(zip(*columns))

    def append(self, meta_dict: Dict[str, str], frame: pd.DataFrame) -> None:
        placeholders = ", ".join(["?"] * len(FULL_COLUMNS))
        column_sql = ", ".join(_quote(c) for c in FULL_COLUMNS)
        sql = f"INSERT INTO trades ({column_sql}) VALUES ({placeholders})"
        conn = self._connect()
        try:
            conn.executemany(sql, self._frame_to_rows(frame))
            conn.commit()
        finally:
            conn.close()

    def load(self, filters: Dict[str, str]) -> pd.DataFrame:
        column_sql = ", ".join(_quote(c) for c in FULL_COLUMNS)
        sql = f"SELECT {column_sql} FROM trades"
        params: List[str] = []
        clauses: List[str] = []
        for key in META_FILTER_KEYS:
            if key in filters:
                clauses.append(f"{_quote(key)} = ?")
                params.append(filters[key])
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY rowid"
        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        if not rows:
            return _empty_ledger_frame()
        return _finalize_frame(pd.DataFrame(rows, columns=list(FULL_COLUMNS)))

    def list_keys(self) -> List[Dict[str, str]]:
        key_sql = ", ".join(_quote(k) for k in META_FILTER_KEYS)
        sql = f"SELECT DISTINCT {key_sql} FROM trades ORDER BY {key_sql}"
        conn = self._connect()
        try:
            rows = conn.execute(sql).fetchall()
        finally:
            conn.close()
        return [dict(zip(META_FILTER_KEYS, row)) for row in rows]


# ---------------------------------------------------------------------
# parquet 백엔드 (pyarrow 존재 시) — 후보별 파일 1개 + 결정론 manifest JSON.
# ---------------------------------------------------------------------
class _ParquetBackend:
    """후보 4-튜플 sha256 다이제스트를 파일명으로 사용 → 파일 배치도 결정론."""

    name = "parquet"

    def __init__(self, root: Path) -> None:
        self._dir = root / _PARQUET_DIRNAME
        self._dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = root / _MANIFEST_FILENAME

    @staticmethod
    def _key_digest(meta_dict: Dict[str, str]) -> str:
        raw = "\n".join(meta_dict[key] for key in META_FILTER_KEYS)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def _load_manifest(self) -> Dict[str, Dict[str, str]]:
        if not self._manifest_path.exists():
            return {}
        with open(self._manifest_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_manifest(self, manifest: Dict[str, Dict[str, str]]) -> None:
        # 결정론 직렬화: 키 정렬 + 고정 구분자.
        text = json.dumps(manifest, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":"))
        with open(self._manifest_path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def append(self, meta_dict: Dict[str, str], frame: pd.DataFrame) -> None:
        digest = self._key_digest(meta_dict)
        path = self._dir / f"{digest}.parquet"
        if path.exists():
            existing = _finalize_frame(pd.read_parquet(path))
            frame = _finalize_frame(
                pd.concat([existing, frame], ignore_index=True)
            )
        frame.to_parquet(path, index=False)
        manifest = self._load_manifest()
        entry = {key: meta_dict[key] for key in META_FILTER_KEYS}
        entry["file"] = path.name
        manifest = {**manifest, digest: entry}
        self._save_manifest(manifest)

    def load(self, filters: Dict[str, str]) -> pd.DataFrame:
        manifest = self._load_manifest()
        frames: List[pd.DataFrame] = []
        for digest in sorted(manifest):
            entry = manifest[digest]
            if any(entry.get(k) != v for k, v in filters.items()):
                continue
            path = self._dir / entry["file"]
            if path.exists():
                frames.append(pd.read_parquet(path))
        if not frames:
            return _empty_ledger_frame()
        return _finalize_frame(pd.concat(frames, ignore_index=True))

    def list_keys(self) -> List[Dict[str, str]]:
        manifest = self._load_manifest()
        keys = [
            {key: entry[key] for key in META_FILTER_KEYS}
            for entry in manifest.values()
        ]
        return sorted(keys, key=lambda e: tuple(e[k] for k in META_FILTER_KEYS))


def _resolve_backend_name(backend: str) -> str:
    """'auto' → pyarrow 유무로 결정. 명시 지정은 가용성 검증."""
    if backend == "auto":
        return "parquet" if _parquet_available() else "sqlite"
    if backend == "parquet":
        if not _parquet_available():
            raise ValueError("parquet_backend_requires_pyarrow")
        return "parquet"
    if backend == "sqlite":
        return "sqlite"
    raise ValueError(f"unknown_backend: {backend}")


# ---------------------------------------------------------------------
# 원장 본체.
# ---------------------------------------------------------------------
class TradeLedger:
    """후보별 거래행 영속 원장 (백엔드 자동 감지, API 는 백엔드 무관 동일)."""

    def __init__(self, root_dir: Union[str, Path], *, backend: str = "auto") -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        name = _resolve_backend_name(backend)
        if name == "parquet":
            self._backend: Union[_ParquetBackend, _SqliteBackend] = (
                _ParquetBackend(self._root)
            )
        else:
            self._backend = _SqliteBackend(self._root)

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def append_trades(
        self,
        meta: Union[TradeLedgerMeta, Mapping],
        trades_df: pd.DataFrame,
    ) -> int:
        """거래행 저장 — 저장된 행 수 반환. 빈 df 는 0 반환(쓰기 없음)."""
        resolved = _coerce_meta(meta)
        if not isinstance(trades_df, pd.DataFrame):
            raise ValueError("trades_df_must_be_dataframe")
        if len(trades_df) == 0:
            return 0
        overlap = set(trades_df.columns) & set(LEDGER_COLUMNS)
        if not overlap:
            # 정본 컬럼이 전무한 df 는 호출측 버그 — 조용히 None 행을 쌓지 않는다.
            raise ValueError("no_ledger_columns_in_trades_df")
        frame = _build_frame(resolved, trades_df)
        self._backend.append(resolved.as_dict(), frame)
        return len(frame)

    def load_trades(self, filters: Optional[Mapping] = None) -> pd.DataFrame:
        """meta 필터 조회 — 항상 FULL_COLUMNS 스키마의 새 프레임 반환."""
        return self._backend.load(_validate_filters(filters))

    def list_candidates(self) -> List[Dict[str, str]]:
        """저장된 후보 identity 목록 (4-튜플 기준 정렬, 결정론)."""
        return self._backend.list_keys()

    def cohort_compare(
        self,
        candidate_a: Union[str, Mapping, TradeLedgerMeta],
        candidate_b: Union[str, Mapping, TradeLedgerMeta],
    ) -> Dict[str, object]:
        """동일 거래일 교집합에서 두 후보의 거래수/손익 비교 dict.

        status: 'ok' | 'empty_candidate'(한쪽 이상 거래 0건) | 'no_common_dates'.
        모든 통계는 교집합 거래일로 제한한 뒤 계산한다(공정 비교).
        """
        filter_a = self._resolve_candidate(candidate_a)
        filter_b = self._resolve_candidate(candidate_b)
        frame_a = self.load_trades(filter_a)
        frame_b = self.load_trades(filter_b)

        dates_a = set(frame_a[DATE_COLUMN].dropna().astype("int64").tolist())
        dates_b = set(frame_b[DATE_COLUMN].dropna().astype("int64").tolist())
        common_dates = sorted(dates_a & dates_b)

        if len(frame_a) == 0 or len(frame_b) == 0:
            status = COMPARE_STATUS_EMPTY
        elif not common_dates:
            status = COMPARE_STATUS_NO_COMMON
        else:
            status = COMPARE_STATUS_OK

        common_a = frame_a[frame_a[DATE_COLUMN].isin(common_dates)]
        common_b = frame_b[frame_b[DATE_COLUMN].isin(common_dates)]
        stats_a = _stats_raw(common_a)
        stats_b = _stats_raw(common_b)

        return {
            "schema_version": TRADE_LEDGER_SCHEMA_VERSION,
            "status": status,
            "candidate_a": filter_a,
            "candidate_b": filter_b,
            "total_rows_a": int(len(frame_a)),
            "total_rows_b": int(len(frame_b)),
            "common_dates": [int(d) for d in common_dates],
            "a_only_date_count": len(dates_a - dates_b),
            "b_only_date_count": len(dates_b - dates_a),
            "a": {k: _round6(v) for k, v in stats_a.items()},
            "b": {k: _round6(v) for k, v in stats_b.items()},
            "delta": _delta_stats(stats_a, stats_b),
            "per_date": _per_date_rows(common_dates, common_a, common_b),
        }

    @staticmethod
    def _resolve_candidate(
        candidate: Union[str, Mapping, TradeLedgerMeta],
    ) -> Dict[str, str]:
        """후보 지정 → 결정론 필터 dict (str=candidate_id, Meta=4-튜플 전체)."""
        if isinstance(candidate, str):
            if not candidate:
                raise ValueError("candidate_id_required")
            return {"candidate_id": candidate}
        if isinstance(candidate, TradeLedgerMeta):
            return candidate.as_dict()
        if isinstance(candidate, Mapping):
            resolved = _validate_filters(candidate)
            if not resolved:
                raise ValueError("candidate_filter_empty")
            return resolved
        raise ValueError("candidate_must_be_str_or_mapping")


def _stats_raw(frame: pd.DataFrame) -> Dict[str, Optional[float]]:
    """한쪽 후보의 원시 통계(반올림 전). 승패 기준: 수익률 > 0 (analyze.py 동일)."""
    if len(frame) == 0:
        return {
            "trade_count": 0,
            "total_profit": 0.0,
            "avg_return": None,
            "win_rate": None,
        }
    returns = frame[RETURN_COLUMN].dropna()
    profits = frame[PROFIT_COLUMN].dropna()
    return {
        "trade_count": int(len(frame)),
        "total_profit": float(profits.sum()) if len(profits) else 0.0,
        "avg_return": float(returns.mean()) if len(returns) else None,
        "win_rate": float((returns > 0).mean()) if len(returns) else None,
    }


def _delta_stats(
    stats_a: Dict[str, Optional[float]],
    stats_b: Dict[str, Optional[float]],
) -> Dict[str, Optional[float]]:
    """a - b 델타 (어느 쪽이든 None 이면 None, 반올림 적용)."""
    delta: Dict[str, Optional[float]] = {}
    for key in ("trade_count", "total_profit", "avg_return", "win_rate"):
        value_a = stats_a[key]
        value_b = stats_b[key]
        if value_a is None or value_b is None:
            delta[key] = None
        else:
            delta[key] = _round6(value_a - value_b)
    return delta


def _per_date_rows(
    common_dates: List[int],
    common_a: pd.DataFrame,
    common_b: pd.DataFrame,
) -> List[Dict[str, object]]:
    """교집합 거래일별 양측 거래수/손익 (거래일 오름차순, 결정론)."""
    rows: List[Dict[str, object]] = []
    for date in common_dates:
        sub_a = common_a[common_a[DATE_COLUMN] == date]
        sub_b = common_b[common_b[DATE_COLUMN] == date]
        rows.append({
            "date": int(date),
            "a_trades": int(len(sub_a)),
            "a_profit": _round6(float(sub_a[PROFIT_COLUMN].dropna().sum())),
            "b_trades": int(len(sub_b)),
            "b_profit": _round6(float(sub_b[PROFIT_COLUMN].dropna().sum())),
        })
    return rows
