"""alpha_lab.dataset.parity — 파생 18항 엔진 패리티 게이트 (v3 P1).

사전등록 우선순위 (a) 채택: backengine이 쓰는 utility.static.add_rolling_data
를 read-only import해 '같은 df'에 적용한 엔진 산출값과, alpha_lab의 미러
재계산(alpha_lab.dataset.derived.compute_derived_tick)을 스팟 대조한다.
엔진 백테스트 실행 0회 — 함수 단위 재적용만 수행한다.

엔진 입력 미러(실측):
- 쿼리: backtest/back_static.py:114-126 GetBackloadCodeQuery(is_tick=True)
  — "SELECT * FROM '{code}' WHERE (`index` >= day*1e6+start AND
  `index` <= day*1e6+end)" (ORDER BY 없음 — rowid 순서 그대로, 엔진 동일).
- 창: 공식 프로파일 bt_universe_start_time=90000 / end_time=93000
  (train-config.json → ai_strategy_loop/controller/loop.py:303
  --start-time → cli/config.py start_time/end_time →
  backtest/backengine_base.py:351-359 data_load).
- 로딩: 엔진과 동일하게 pd.read_sql(backengine_base.py:354) — 단 연결은
  read-only URI 전용(_database는 공유 junction, 쓰기 금지).

일치 판정: 상대오차 1e-9 허용 — a==b 또는 |a-b| <= rel_tol*max(|a|,|b|)
(양쪽 NaN도 일치로 본다 — nan_to_num 경로에서는 발생하지 않음).
"""
from __future__ import annotations

import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.dataset.derived import (
    AVG_WINDOW_FROZEN,
    DERIVED_TICK_FEATURES,
    FORMULA_REFS,
    compute_derived_tick,
    engine_column_name,
)

__all__ = [
    "OFFICIAL_END_TIME",
    "OFFICIAL_START_TIME",
    "PASS_THRESHOLD_PCT",
    "REL_TOL",
    "build_annex_payload",
    "compare_columns",
    "engine_reference",
    "load_engine_input",
    "pick_codes",
    "run_parity",
]

logger = logging.getLogger(__name__)

# 공식 warm64 프로파일 창(train-config.json bt_universe_start/end_time).
OFFICIAL_START_TIME = 90000
OFFICIAL_END_TIME = 93000

# 사전등록 게이트: 상대오차 1e-9, 피처별 일치율 >= 99.9%만 통과.
REL_TOL = 1e-9
PASS_THRESHOLD_PCT = 99.9

_CODE_RE = re.compile(r"^\d{6}$")


def _connect_ro(db_path) -> sqlite3.Connection:
    """read-only URI 연결 강제(alpha_lab.dataset.reader.connect_ro와 동일 규율)."""
    posix = Path(db_path).as_posix()
    return sqlite3.connect(f"file:{posix}?mode=ro", uri=True)


def load_engine_input(
    db_path,
    code: str,
    day: int,
    start_time: int = OFFICIAL_START_TIME,
    end_time: int = OFFICIAL_END_TIME,
) -> pd.DataFrame:
    """엔진 DataLoad와 동일 형태의 단일일 입력 df를 read-only로 만든다.

    backtest/back_static.py:114-126 GetBackloadCodeQuery(is_tick=True,
    days=[day]) 미러 + backengine_base.py:354 pd.read_sql 미러.
    """
    code_text = str(code)
    if not _CODE_RE.fullmatch(code_text):
        raise ValueError(f"6자리 종목코드가 아님: {code_text!r}")
    sindex = int(day) * 1_000_000 + int(start_time)
    eindex = int(day) * 1_000_000 + int(end_time)
    query = (
        f"SELECT * FROM '{code_text}' "
        f"WHERE (`index` >= {sindex} AND `index` <= {eindex})"
    )
    with closing(_connect_ro(db_path)) as conn:
        return pd.read_sql(query, conn)


def pick_codes(
    db_path,
    day: int,
    k: int = 4,
    start_time: int = OFFICIAL_START_TIME,
    end_time: int = OFFICIAL_END_TIME,
) -> List[str]:
    """일 DB에서 표본 종목 k개를 결정적으로 고른다 — 창 내 행수 상위,
    동수는 코드 오름차순."""
    sindex = int(day) * 1_000_000 + int(start_time)
    eindex = int(day) * 1_000_000 + int(end_time)
    ranked: List[Tuple[int, str]] = []
    with closing(_connect_ro(db_path)) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        codes = [name for (name,) in cursor if _CODE_RE.fullmatch(name)]
        for code in codes:
            (count,) = conn.execute(
                f'SELECT COUNT(*) FROM "{code}" '
                f'WHERE "index" >= ? AND "index" <= ?',
                (sindex, eindex),
            ).fetchone()
            if count > 0:
                ranked.append((int(count), code))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [code for _, code in ranked[: int(k)]]


def engine_reference(
    df: pd.DataFrame, avg: int = AVG_WINDOW_FROZEN
) -> pd.DataFrame:
    """엔진 함수를 같은 df 사본에 적용해 파생 18항 기준값을 얻는다.

    utility.static.add_rolling_data는 df를 제자리 변형하며 마지막에
    np.nan_to_num(np.array(df))를 반환한다(utility/static.py:78-132).
    반환 배열에서 입력 컬럼 수 이후의 18열을 정식명으로 재명명해 돌려준다.
    import는 호출 시점에만 수행(read-only 사용 — 엔진 코드 무수정).
    """
    from utility.static import add_rolling_data  # 지연 import(무거운 의존)

    eng_df = df.copy()
    n_input = eng_df.shape[1]
    # backengine_base.py:359와 동일 호출형: (df, market_gubun=1, is_tick=True, avg_list)
    arry = add_rolling_data(eng_df, 1, True, [int(avg)])
    appended = list(eng_df.columns[n_input:])
    expected = [engine_column_name(name, avg) for name in DERIVED_TICK_FEATURES]
    if appended != expected:
        raise RuntimeError(
            f"엔진 추가 컬럼 불일치 — 기대 {expected} vs 실측 {appended}"
        )
    if arry.shape[1] != n_input + len(expected):
        raise RuntimeError(
            f"엔진 배열 열수 불일치: {arry.shape[1]} != {n_input}+{len(expected)}"
        )
    return pd.DataFrame(
        arry[:, n_input:], columns=list(DERIVED_TICK_FEATURES), index=df.index
    )


def compare_columns(
    mine: pd.DataFrame, ref: pd.DataFrame, rel_tol: float = REL_TOL
) -> Dict[str, dict]:
    """피처별 일치 통계 — {name: {n, n_agree, agreement_pct, max_rel_err}}.

    일치: a==b(양쪽 NaN 포함) 또는 |a-b| <= rel_tol*max(|a|,|b|).
    max_rel_err는 유한 불일치 쌍의 |a-b|/max(|a|,|b|) 최댓값(없으면 0.0).
    """
    if list(mine.columns) != list(ref.columns):
        raise ValueError("비교 컬럼 불일치 — 정식명 18항 순서가 같아야 한다")
    if len(mine) != len(ref):
        raise ValueError(f"행수 불일치: {len(mine)} != {len(ref)}")
    out: Dict[str, dict] = {}
    for name in mine.columns:
        a = mine[name].to_numpy(dtype="float64")
        b = ref[name].to_numpy(dtype="float64")
        both_nan = np.isnan(a) & np.isnan(b)
        diff = np.abs(a - b)
        scale = np.maximum(np.abs(a), np.abs(b))
        with np.errstate(invalid="ignore", divide="ignore"):
            rel = np.where(scale > 0.0, diff / scale, 0.0)
        agree = both_nan | (a == b) | (diff <= rel_tol * scale)
        n = int(a.shape[0])
        n_agree = int(np.count_nonzero(agree))
        finite_bad = (~agree) & np.isfinite(rel)
        max_rel = float(rel[finite_bad].max()) if finite_bad.any() else 0.0
        out[name] = {
            "n": n,
            "n_agree": n_agree,
            "agreement_pct": (100.0 * n_agree / n) if n else 0.0,
            "max_rel_err": max_rel,
        }
    return out


def run_parity(
    db_dir,
    days: Sequence[int],
    codes_per_day: int = 4,
    avg: int = AVG_WINDOW_FROZEN,
    rel_tol: float = REL_TOL,
    start_time: int = OFFICIAL_START_TIME,
    end_time: int = OFFICIAL_END_TIME,
) -> dict:
    """표본 (일 x 종목) 전체에 대해 패리티를 측정해 집계 결과를 반환한다.

    반환: {"per_feature": {name: {n, n_agree, agreement_pct, max_rel_err}},
           "samples": [{"day", "code", "rows"}...], "rows_total": int,
           "codes": {day(str): [code...]}}.
    """
    per_feature: Dict[str, dict] = {
        name: {"n": 0, "n_agree": 0, "max_rel_err": 0.0}
        for name in DERIVED_TICK_FEATURES
    }
    samples: List[dict] = []
    codes_by_day: Dict[str, List[str]] = {}
    for day in days:
        db_path = Path(db_dir) / f"stock_tick_{int(day)}.db"
        if not db_path.exists():
            raise FileNotFoundError(f"일 DB 없음: {db_path}")
        codes = pick_codes(db_path, day, codes_per_day, start_time, end_time)
        codes_by_day[str(int(day))] = codes
        for code in codes:
            df = load_engine_input(db_path, code, day, start_time, end_time)
            mine = compute_derived_tick(df, avg)
            ref = engine_reference(df, avg)
            stats = compare_columns(mine, ref, rel_tol)
            for name, stat in stats.items():
                acc = per_feature[name]
                acc["n"] += stat["n"]
                acc["n_agree"] += stat["n_agree"]
                acc["max_rel_err"] = max(acc["max_rel_err"], stat["max_rel_err"])
            rows = len(df)
            samples.append({"day": int(day), "code": code, "rows": rows})
            logger.info("parity: day=%s code=%s rows=%d", day, code, rows)
    for name, acc in per_feature.items():
        acc["agreement_pct"] = (
            (100.0 * acc["n_agree"] / acc["n"]) if acc["n"] else 0.0
        )
    return {
        "per_feature": per_feature,
        "samples": samples,
        "rows_total": int(sum(item["rows"] for item in samples)),
        "codes": codes_by_day,
    }


def build_annex_payload(
    result: dict,
    *,
    avg: int = AVG_WINDOW_FROZEN,
    rel_tol: float = REL_TOL,
    pass_threshold_pct: float = PASS_THRESHOLD_PCT,
    method_extra: dict | None = None,
) -> dict:
    """run_parity 결과 → v3_feature_annex 봉인 payload(결정적 구성).

    passed_features: 일치율 >= pass_threshold_pct(99.9)만,
    DERIVED_TICK_FEATURES 순서. failed_features: 나머지 + 사유.
    """
    passed: List[dict] = []
    failed: List[dict] = []
    for name in DERIVED_TICK_FEATURES:
        stat = result["per_feature"][name]
        pct = round(float(stat["agreement_pct"]), 6)
        if pct >= pass_threshold_pct:
            passed.append(
                {
                    "name": name,
                    "agreement_pct": pct,
                    "formula_ref": FORMULA_REFS[name],
                }
            )
        else:
            failed.append(
                {
                    "name": name,
                    "agreement_pct": pct,
                    "사유": (
                        f"일치율 {pct} < {pass_threshold_pct} "
                        f"(불일치 {stat['n'] - stat['n_agree']}/{stat['n']}행, "
                        f"max_rel_err {stat['max_rel_err']:.3e})"
                    ),
                }
            )
    method = {
        "approach": (
            "(a) utility.static.add_rolling_data(utility/static.py:78-132) "
            "read-only import — 동일 df 재적용 스팟 대조(엔진 백테 0회)"
        ),
        "engine_call": f"add_rolling_data(df, 1, True, [{int(avg)}])",
        "input_mirror": (
            "backtest/back_static.py:114-126 GetBackloadCodeQuery(is_tick=True) "
            "단일일 SELECT * (ORDER BY 없음) + pd.read_sql"
        ),
        "db": "_database/stock_tick_YYYYMMDD.db (mode=ro URI)",
        "window_hhmmss": [OFFICIAL_START_TIME, OFFICIAL_END_TIME],
        "avg_frozen": int(avg),
        "rel_tol": rel_tol,
        "pass_rule": f"agreement_pct >= {pass_threshold_pct}",
        "codes": result["codes"],
        "code_selection": "창 내 행수 상위 k(동수는 코드 오름차순) — 결정적",
        "samples": result["samples"],
        "rows_total": result["rows_total"],
        "derived_count_note": (
            "preregistration_v3 표기는 derived_19이나 엔진 add_rolling_data가 "
            "stock tick(market=1)에서 추가하는 컬럼은 실측 18개"
            "(np.array 72열 - 저장 54열). 18항 전수를 게이트에 상정."
        ),
    }
    if method_extra:
        method.update(method_extra)
    return {
        "passed_features": passed,
        "failed_features": failed,
        "method": method,
    }
