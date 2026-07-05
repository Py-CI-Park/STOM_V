"""P3 챔피언 거래 tick 재조인 — 종목명→코드 해석 + 일 단위 재라벨·피처.

봉인 근거(p3_preregistration_v1.json slot_definitions.종목코드):
게이트런 CSV 에는 종목코드가 없어 원장 identity 의 종목코드 필드는 종목명
원문이다. 재조인 단계에서 종목명→6자리 코드 매핑을 수행하고, 해당 거래일
tick DB 에 그 코드 테이블이 실재하는지로 최종 검증한다. 매핑·테이블 부재는
정직 제외(사유 카운트 + 제외 목록).

매핑 사전 원천(Phase 0 확정 — 봉인 후보 '엔진 dict_cn 원천 테이블' 채택):
  primary  = _database/stock_tick_back.db :: stockinfo (index=코드, 종목명)
             — ui/ui_backtest_engine.py 가 dict_cn 을 만드는 바로 그 테이블.
  fallback = _database/code_info.db :: stockinfo (동일 스키마 — 이름 개정
             구제용, 사용 시 method='fallback' 로 카운트).
  code_literal = 종목명 원문이 6자리 숫자이고 알려진 코드와 일치하는 경우
             (드문 데이터 이상 구제 — method 카운트로 추적).

라벨은 alpha_lab.mcl.screening.relabel_trades/relabel_trade(§3.2 A안)만 사용,
피처는 alpha_lab.mcl.features(봉인 동결표)만 사용 — 통계 재구현 없음.
tick DB 접근은 dataset.reader.connect_ro(file:...?mode=ro) 전용.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from alpha_lab.dataset.reader import connect_ro, load_stock_rows
from alpha_lab.distill.ledger_wiring import identity
from alpha_lab.mcl.features import compute_features
from alpha_lab.mcl.screening import relabel_trade, relabel_trades

__all__ = [
    "EXCLUSION_REASONS_MAPPING",
    "load_stockinfo_map",
    "rejoin_day",
    "resolve_code",
]

logger = logging.getLogger(__name__)

_CODE_RE = re.compile(r"^\d{6}$")

# 매핑 단계 제외 사유(재라벨 단계 사유는 screening.relabel_trade 계약 참조).
EXCLUSION_REASONS_MAPPING: Tuple[str, ...] = (
    "day_db_missing", "unmapped", "no_day_table", "ambiguous_day_table",
)


def load_stockinfo_map(db_path) -> Tuple[Dict[str, List[str]], FrozenSet[str]]:
    """stockinfo 테이블(ro) → ({종목명: [6자리 코드 오름차순]}, 코드 전집합).

    같은 종목명이 여러 코드로 존재하면 전부 후보로 보존한다(해소는 거래일
    테이블 실재 검증에서 — resolve_code). 6자리가 아닌 index 는 무시한다.
    """
    conn = connect_ro(db_path)
    try:
        name_map: Dict[str, List[str]] = {}
        codes: set = set()
        cursor = conn.execute('SELECT "index", "종목명" FROM stockinfo')
        for code_value, name_value in cursor:
            code = str(code_value).strip()
            name = str(name_value).strip() if name_value is not None else ""
            if not _CODE_RE.fullmatch(code) or not name:
                continue
            codes.add(code)
            bucket = name_map.setdefault(name, [])
            if code not in bucket:
                bucket.append(code)
        for bucket in name_map.values():
            bucket.sort()
        logger.info(
            "stockinfo 매핑 적재 %s: names=%d codes=%d", db_path,
            len(name_map), len(codes),
        )
        return name_map, frozenset(codes)
    finally:
        conn.close()


def resolve_code(
    name: str,
    day_tables: FrozenSet[str],
    *,
    primary: Mapping[str, Sequence[str]],
    primary_codes: FrozenSet[str],
    fallback: Optional[Mapping[str, Sequence[str]]] = None,
    fallback_codes: FrozenSet[str] = frozenset(),
) -> Tuple[Optional[str], str]:
    """종목명 → (6자리 코드 | None, method|제외사유).

    후보 산출: primary → fallback → code_literal(종목명 자체가 알려진 6자리
    코드). 최종 검증: 후보 중 그 거래일 DB 에 테이블이 실재하는 코드가
    정확히 1개일 때만 해석 성공. 0개='no_day_table', 2개 이상=
    'ambiguous_day_table', 후보 자체 없음='unmapped' (전부 정직 제외 사유).
    """
    candidates = list(primary.get(name, ()))
    method = "primary"
    if not candidates and fallback is not None:
        candidates = list(fallback.get(name, ()))
        method = "fallback"
    if not candidates and _CODE_RE.fullmatch(name) \
            and (name in primary_codes or name in fallback_codes):
        candidates = [name]
        method = "code_literal"
    if not candidates:
        return None, "unmapped"
    with_table = [c for c in candidates if c in day_tables]
    if not with_table:
        return None, "no_day_table"
    if len(with_table) > 1:
        return None, "ambiguous_day_table"
    return with_table[0], method


def _day_tables(conn) -> FrozenSet[str]:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    return frozenset(name for (name,) in cursor if _CODE_RE.fullmatch(name))


def _exclusion(rec: Mapping, reason: str, code: Optional[str] = None) -> dict:
    strategy, name, day, hms = identity(rec)
    entry = {
        "전략명": strategy, "종목코드": name, "진입일자": day,
        "진입시각": hms, "reason": reason,
    }
    if code is not None:
        entry["code6"] = code
    return entry


def _bump(counter: Dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def rejoin_day(
    db_path,
    day: str,
    records: Sequence[Mapping],
    *,
    primary: Mapping[str, Sequence[str]],
    primary_codes: FrozenSet[str],
    fallback: Optional[Mapping[str, Sequence[str]]],
    fallback_codes: FrozenSet[str],
    specs: Sequence[Mapping],
    horizons: Sequence[int],
) -> Tuple[List[dict], List[dict], Dict[str, Dict[str, int]]]:
    """거래일 1일 재조인 — (채택 표본, 제외 목록, {resolution, relabel} 카운트).

    표본 = relabel_trades 반환 dict(strategy/code/day/t0 + 라벨 6종)에
    code6(해석 코드)·features(봉인 25조합, 결측 NaN)를 부가한 새 dict.
    제외 목록 항목은 identity 4-튜플 + reason(매핑 단계 또는 재라벨 사유).
    """
    resolution: Dict[str, int] = {}
    relabel_counts: Dict[str, int] = {}
    exclusions: List[dict] = []
    if not Path(db_path).exists():
        for rec in records:
            _bump(resolution, "day_db_missing")
            exclusions.append(_exclusion(rec, "day_db_missing"))
        logger.warning("일 DB 부재 %s — %d건 정직 제외", db_path, len(records))
        return [], exclusions, {"resolution": resolution, "relabel": relabel_counts}

    conn = connect_ro(db_path)
    try:
        tables = _day_tables(conn)
        resolved_records: List[Mapping] = []
        code_of: Dict[str, str] = {}
        for rec in records:
            name = identity(rec)[1]
            if name in code_of:
                _bump(resolution, "resolved_dup_name")
                resolved_records.append(rec)
                continue
            code, method = resolve_code(
                name, tables,
                primary=primary, primary_codes=primary_codes,
                fallback=fallback, fallback_codes=fallback_codes,
            )
            if code is None:
                _bump(resolution, method)
                exclusions.append(_exclusion(rec, method))
                continue
            code_of[name] = code
            _bump(resolution, method)
            resolved_records.append(rec)

        rows_map = {
            (day, name): load_stock_rows(conn, code)
            for name, code in code_of.items()
        }
        samples, relabel_counts = relabel_trades(
            resolved_records, rows_map, horizons=horizons
        )
        adopted = {
            (s["strategy"], s["code"], str(s["day"]), f"{s['t0']:014d}"[8:])
            for s in samples
        }
        for rec in resolved_records:
            strategy, name, rec_day, hms = identity(rec)
            if (strategy, name, rec_day, hms) in adopted:
                continue
            _, reason = relabel_trade(
                rows_map.get((rec_day, name)), int(rec_day + hms),
                horizons=horizons,
            )
            exclusions.append(_exclusion(rec, reason, code_of.get(name)))

        enriched = [
            {
                **sample,
                "code6": code_of[sample["code"]],
                "features": compute_features(
                    rows_map[(day, sample["code"])], int(sample["t0"]), specs
                ),
            }
            for sample in samples
        ]
        return enriched, exclusions, {
            "resolution": resolution, "relabel": relabel_counts,
        }
    finally:
        conn.close()
