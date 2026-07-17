"""P5 Phase 0 — 챔피언 원장 배선 (게이트런 per-trade CSV → 정규화 JSONL 원장).

조건식을 생성하지 않는다. OOS 통과 챔피언(rr8_12 계보 등)의 게이트런 거래
CSV들을 명시 경로로 받아 레코드를 정규화·중복제거해 연구용 원장(JSONL)으로
영속한다. 이후 Phase 1(진입 증류)·Phase 2(최적 청산)의 유일한 입력이 된다.

실측 근거 (2026-07-05, 추정 없음 — 전부 파일 실물 확인):
  - 게이트런 CSV 위치·명명: `backtest/csv/stock_bt_<전략명>_<YYYYMMDDHHMMSS>.csv`
      wt-dev 실물 6,458개, 챔피언 계보 `stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_*.csv`.
  - 스키마: utf-8-sig, 37컬럼 = 기본 14 + B_* 14 + S_* 5 + R_* 4.
      `backtest/back_static.py:24-36`(TRADE_RESULT_{B,S,R}_COLUMNS)과 동일 순서.
  - CSV에 **전략명·종목코드 컬럼이 없다**: 전략명은 파일명에서만, 종목 식별은
    `종목명`뿐이다. 따라서 identity 의 종목코드 필드는 종목코드 부재 시 종목명을
    폴백으로 채운다(폴백 사실은 종목명 컬럼 보존으로 추적 가능).
  - `매수시간`은 tick 엔진 14자리(YYYYMMDDHHMMSS)와 min 엔진 12자리(YYYYMMDDHHMM)
    가 혼재한다(둘 다 실물 확인). 12자리는 초 '00'을 덧붙여 6자리 시각으로 정규화.
  - R_MFE/R_MAE 존재(값 예: 6.84/-0.96). `ai_strategy_loop/autopsy/analyze.py`
    의 B_COLUMNS(:33)·B_TO_STOM_VAR(:40) 및 trade_ledger.py 의 S/R 컬럼과 대조
    테스트(tests/unit/test_alpha_distill.py)로 드리프트를 봉쇄한다.

identity(중복 판정 키) = (전략명, 종목코드, 진입일자, 진입시각) 4-튜플.
  - 같은 전략의 게이트런 재실행 CSV들에서 동일 거래가 재등장하는 것이 중복의
    정의다. 추가매수는 엔진이 1행으로 접으므로(추가매수시간 컬럼) 4-튜플로 충분.
  - 알려진 한계: min 엔진 12자리 매수시간은 분 해상도라, 동일 분 내 재진입
    거래(이론상)와 tick/min 혼합 스캔의 동일 거래는 구분/병합하지 못한다.
    Phase 0 범위에서는 tick 게이트런(14자리)만 원장 대상으로 쓰는 것을 권장.

규율: 자동 글롭·자동 실행 없음(scan_csvs 는 명시 경로 인자만), 원본 CSV 는
읽기 전용, 표준 라이브러리만 사용, print 금지(logging), 입력 불변.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# 원장 레코드 스키마 버전 — 레코드마다 저장된다.
LEDGER_SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# 게이트런 per-trade CSV 실측 37컬럼 (2026-07-05 실물 헤더 그대로 봉인).
#   원천: backtest/back_static.py TRADE_RESULT_{B,S,R}_COLUMNS + 기본 14컬럼.
#   대조 테스트가 analyze.py/trade_ledger.py 상수와의 일치를 검증한다.
# ---------------------------------------------------------------------------
GATE_CSV_BASE_COLUMNS: Tuple[str, ...] = (
    "종목명", "시가총액", "매수시간", "매도시간", "보유시간",
    "매수가", "매도가", "매수금액", "매도금액", "수익률",
    "수익금", "수익금합계", "매도조건", "추가매수시간",
)
GATE_CSV_B_COLUMNS: Tuple[str, ...] = (
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가",
)
GATE_CSV_S_COLUMNS: Tuple[str, ...] = (
    "S_현재가", "S_등락율", "S_체결강도", "S_매수총잔량", "S_매도총잔량",
)
GATE_CSV_R_COLUMNS: Tuple[str, ...] = (
    "R_매수후최고수익률", "R_매수후최저수익률", "R_MFE", "R_MAE",
)
GATE_CSV_COLUMNS: Tuple[str, ...] = (
    GATE_CSV_BASE_COLUMNS
    + GATE_CSV_B_COLUMNS
    + GATE_CSV_S_COLUMNS
    + GATE_CSV_R_COLUMNS
)

# 필수 필드와 identity — 계약(레인 H 지시문) 그대로 봉인.
BUY_TIME_COLUMN = "매수시간"
RETURN_COLUMN = "수익률"
IDENTITY_FIELDS: Tuple[str, ...] = ("전략명", "종목코드", "진입일자", "진입시각")

# 있으면 통과(passthrough)하는 컬럼 — 문자형은 원문 보존(매도조건은 절
# 어트리뷰션 파싱용이라 선행 공백까지 유지), 수치형은 float 강제.
TEXT_PASSTHROUGH_COLUMNS: Tuple[str, ...] = (
    "종목명", "시가총액", "매도조건", "추가매수시간",
)
NUMERIC_PASSTHROUGH_COLUMNS: Tuple[str, ...] = (
    ("매수시간", "매도시간", "보유시간", "매수가", "매도가",
     "매수금액", "매도금액", "수익금", "수익금합계")
    + GATE_CSV_B_COLUMNS
    + GATE_CSV_S_COLUMNS
    + GATE_CSV_R_COLUMNS
)

# 파일명 → 전략명 파생 규칙: 'stock_bt_' 접두 제거 + 말미 '_<14자리 타임스탬프>' 제거.
_STOCK_BT_PREFIX = "stock_bt_"
_TRAILING_TS_RE = re.compile(r"_\d{14}$")

PathLike = Union[str, Path]

__all__ = [
    "LEDGER_SCHEMA_VERSION",
    "GATE_CSV_BASE_COLUMNS",
    "GATE_CSV_B_COLUMNS",
    "GATE_CSV_S_COLUMNS",
    "GATE_CSV_R_COLUMNS",
    "GATE_CSV_COLUMNS",
    "IDENTITY_FIELDS",
    "TEXT_PASSTHROUGH_COLUMNS",
    "NUMERIC_PASSTHROUGH_COLUMNS",
    "strategy_from_csv_name",
    "normalize_trade_row",
    "identity",
    "dedup_records",
    "write_ledger",
    "read_ledger",
    "scan_csvs",
]


# ---------------------------------------------------------------------------
# 값 정규화 헬퍼 — 전부 순수 함수, 입력 불변.
# ---------------------------------------------------------------------------
def _is_missing(value: object) -> bool:
    """스칼라 결측 판정 (None / NaN / 공백뿐인 문자열)."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _to_float(value: object) -> Optional[float]:
    """수치 강제 → float 또는 None (bool/비유한값/강제 불가 값도 None)."""
    if _is_missing(value) or isinstance(value, bool):
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _digits_of(value: object) -> Optional[str]:
    """정수형 시각 값 → 숫자 문자열 (선행 0 은 str 입력에서만 보존 가능)."""
    if _is_missing(value) or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value) or value != int(value):
            return None
        return str(int(value))
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text if text.isdigit() else None


def _clean_text(value: object) -> Optional[str]:
    """문자 passthrough — 원문 보존(매도조건의 선행 공백 유지), 결측은 None."""
    if _is_missing(value):
        return None
    return str(value)


def _identity_text(value: object) -> Optional[str]:
    """identity 용 문자 필드 — 양끝 공백 제거, 빈 값은 None."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None


def _parse_entry_fields(row: Mapping) -> Optional[Tuple[str, str]]:
    """진입 (일자 8자리, 시각 6자리) 파생.

    1순위: 매수시간 — 14자리(YYYYMMDDHHMMSS, tick) 또는 12자리(YYYYMMDDHHMM,
    min → 초 '00' 부여). 존재하되 자릿수 불량이면 그 행은 의심 데이터로 drop.
    2순위(매수시간 부재 시): 이미 정규화된 진입일자(8)/진입시각(6) 직접 필드
    — read_ledger 재수입 경로. 그 외 형식은 전부 None(drop).
    """
    digits = _digits_of(row.get(BUY_TIME_COLUMN))
    if digits is not None:
        if len(digits) == 14:
            return digits[:8], digits[8:]
        if len(digits) == 12:
            return digits[:8], digits[8:] + "00"
        return None
    day = _digits_of(row.get("진입일자"))
    hms = _digits_of(row.get("진입시각"))
    if day is None or hms is None or len(day) != 8 or len(hms) != 6:
        return None
    return day, hms


# ---------------------------------------------------------------------------
# 공개 API.
# ---------------------------------------------------------------------------
def strategy_from_csv_name(name: str) -> str:
    """per-trade CSV 파일명 → 전략명.

    실측 명명 규약 `stock_bt_<전략명>_<YYYYMMDDHHMMSS>.csv` 에서 접두와 말미
    타임스탬프만 벗긴다(전략명 내부의 밑줄은 건드리지 않는다 — 결정론).
    규약을 벗어난 이름은 stem 자체를 반환한다.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("csv_name_required")
    stem = Path(name.strip()).stem
    body = stem[len(_STOCK_BT_PREFIX):] if stem.startswith(_STOCK_BT_PREFIX) else stem
    trimmed = _TRAILING_TS_RE.sub("", body)
    return trimmed or stem


def normalize_trade_row(row: Mapping, *, source: str) -> Optional[dict]:
    """게이트런 거래행 1개 → 정규화 원장 레코드 (데이터 불량은 None 으로 drop).

    필수: 전략명(행에 없으면 source), 종목코드(없으면 종목명 폴백 — 실측상
    CSV에 종목코드 컬럼이 없다), 진입일자/진입시각(매수시간 파생), 수익률.
    B_*/S_*/R_MFE/R_MAE 등은 있으면 통과. ValueError 는 계약 위반
    (row 가 Mapping 이 아님 / source 공백)에만 던진다.
    """
    if not isinstance(row, Mapping):
        raise ValueError("row_must_be_mapping")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source_required")
    source_tag = source.strip()

    strategy = _identity_text(row.get("전략명")) or source_tag
    code = _identity_text(row.get("종목코드")) or _identity_text(row.get("종목명"))
    if code is None:
        return None
    entry = _parse_entry_fields(row)
    if entry is None:
        return None
    return_value = _to_float(row.get(RETURN_COLUMN))
    if return_value is None:
        return None

    record: Dict[str, object] = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "source": source_tag,
        "전략명": strategy,
        "종목코드": code,
        "진입일자": entry[0],
        "진입시각": entry[1],
        RETURN_COLUMN: return_value,
    }
    for column in TEXT_PASSTHROUGH_COLUMNS:
        text = _clean_text(row.get(column))
        if text is not None:
            record[column] = text
    for column in NUMERIC_PASSTHROUGH_COLUMNS:
        value = _to_float(row.get(column))
        if value is not None:
            record[column] = value
    return record


def identity(rec: Mapping) -> Tuple[str, str, str, str]:
    """레코드 identity 4-튜플 (전략명, 종목코드, 진입일자, 진입시각).

    필수 필드 결측은 정규화를 거치지 않은 레코드 → 계약 위반(ValueError).
    """
    if not isinstance(rec, Mapping):
        raise ValueError("record_must_be_mapping")
    values: List[str] = []
    for field in IDENTITY_FIELDS:
        value = rec.get(field)
        if _is_missing(value):
            raise ValueError(f"record_missing_identity_field: {field}")
        values.append(str(value))
    return (values[0], values[1], values[2], values[3])


def dedup_records(records: Iterable[Mapping]) -> Tuple[List[dict], int]:
    """identity 기준 중복 제거 — (고유 레코드 새 리스트, 중복 수).

    first-wins: 최초 등장 레코드를 유지하고 이후 동일 identity 는 전부
    중복으로 센다. 입력은 변형하지 않으며 반환 레코드는 얕은 복사본이다.
    """
    unique: List[dict] = []
    seen: set = set()
    dup_count = 0
    for rec in records:
        key = identity(rec)
        if key in seen:
            dup_count += 1
            continue
        seen.add(key)
        unique.append(dict(rec))
    return unique, dup_count


def write_ledger(records: Iterable[Mapping], out_path: PathLike) -> int:
    """레코드들을 JSONL 로 영속 (한 줄 = 한 레코드, utf-8, 키 순서 보존).

    부모 디렉토리는 생성한다. 반환값은 기록한 레코드 수. 직렬화 전에 전 행을
    검증하므로 중간 실패로 부분 파일이 남지 않는다(전량 직렬화 후 일괄 기록).
    """
    path = Path(out_path)
    lines: List[str] = []
    for rec in records:
        if not isinstance(rec, Mapping):
            raise ValueError("record_must_be_mapping")
        lines.append(
            json.dumps(dict(rec), ensure_ascii=False, separators=(",", ":"))
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for line in lines:
            handle.write(line + "\n")
    logger.info("ledger_written path=%s records=%d", path, len(lines))
    return len(lines)


def read_ledger(path: PathLike) -> List[dict]:
    """JSONL 원장 → 레코드 리스트 (빈 줄 무시, 불량 줄은 줄 번호와 함께 실패)."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"ledger_not_found: {resolved}")
    records: List[dict] = []
    with open(resolved, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"ledger_line_invalid_json: path={resolved} line={line_no}"
                ) from exc
    return records


def scan_csvs(paths: Sequence[PathLike]) -> Tuple[List[dict], dict]:
    """명시된 게이트런 CSV 경로들만 스캔 → (정규화 레코드, 스캔 리포트).

    자동 글롭·자동 실행 없음 — 호출자가 경로를 전부 명시해야 하며, 없는
    경로는 즉시 FileNotFoundError(호출측 버그). 각 파일의 source(전략명)는
    파일명에서 파생한다(strategy_from_csv_name). 중복 제거는 이 함수의 일이
    아니다 — dedup_records 를 이어서 호출하라(단계 분리로 리포트가 정직해짐).
    """
    if isinstance(paths, (str, bytes, Path)) or not isinstance(paths, Sequence):
        raise ValueError("paths_must_be_sequence_of_paths")
    records: List[dict] = []
    files: List[dict] = []
    total_rows = total_kept = 0
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"csv_not_found: {path}")
        source = strategy_from_csv_name(path.name)
        rows = kept = 0
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows += 1
                rec = normalize_trade_row(row, source=source)
                if rec is None:
                    continue
                kept += 1
                records.append(rec)
        files.append({
            "path": str(path), "source": source,
            "rows": rows, "kept": kept, "dropped": rows - kept,
        })
        total_rows += rows
        total_kept += kept
        logger.info(
            "csv_scanned path=%s source=%s rows=%d kept=%d", path, source, rows, kept
        )
    report = {
        "files": files,
        "total_rows": total_rows,
        "kept": total_kept,
        "dropped": total_rows - total_kept,
    }
    return records, report
