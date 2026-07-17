"""온셋 시점 절-평가 네임스페이스 구성 — 엔진 파생 재사용·단독일 창(사전등록 §6 P1).

한 (종목, 일)의 09:00:00~09:30:00 관측 행을 엔진과 같은 순서(rowid; GetBackload
CodeQuery SELECT * WHERE index in [90000,93000], ORDER BY 없음)로 올려:
- 저장 21컬럼: 온셋 행에서 직접 판독.
- 시분초 = index % 1_000_000 (engine backengine_kiwoom_tick.py:26).
- 파생 4항(avg=30): alpha_lab.dataset.derived.compute_derived_tick(parity.py 검증)
  의 당일거래대금각도/초당거래대금평균/누적초당매수수량/누적초당매도수량 을 온셋 행에서 판독.
  초당거래대금평균30 은 엔진 _초당거래대금평균 의 int() 래핑을 미러(np.trunc).
- 초당거래대금N1 = 직전 관측 행 초당거래대금(_Parameter_Previous, indexn-1; 첫 행 0).
그 뒤 clauses.build_local_definitions 로 로컬 정의 5종을 붙인다.

파생 창 규약(단독일): 봉인 v2a/L3 인프라(pilot_v2.day_context_from_rows,
parity.run_parity)와 동일하게 파생을 단독일 창에서만 계산한다(멀티데이 concat 미적용).
이는 L3 은행과 파생 컨벤션을 일치시켜 A/B 조인의 정합을 보장한다.

원본 tick DB 접근은 read-only URI 전용. 엔진 백테 0회.
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.clause_lab.clauses import NAMESPACE_SYMBOLS, build_local_definitions
from alpha_lab.dataset.derived import compute_derived_tick
from alpha_lab.dataset.schema import as_float

__all__ = [
    "STORED_CLAUSE_COLUMNS",
    "DERIVED_CLAUSE_MAP",
    "build_onset_namespace",
    "load_window_frame",
]

WINDOW_START_HMS = 90000
WINDOW_END_HMS = 93000

# 절이 직접 판독하는 저장 컬럼(setting_base list_stock_tick[1:54] 중 사용분).
STORED_CLAUSE_COLUMNS: Tuple[str, ...] = (
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "전일비", "회전율", "전일동시간비", "시가총액",
    "라운드피겨위5호가이내", "VI가격", "VI호가단위", "초당거래대금",
    "고저평균대비등락율", "매도총잔량", "매수총잔량", "관심종목",
)

# 매수식 사용 파생 4항: 네임스페이스 키 → compute_derived_tick 정식명.
DERIVED_CLAUSE_MAP: Dict[str, str] = {
    "당일거래대금각도30": "당일거래대금각도",
    "초당거래대금평균30": "초당거래대금평균",
    "누적초당매수수량30": "누적초당매수수량",
    "누적초당매도수량30": "누적초당매도수량",
}


def load_window_frame(
    conn, code: str, day: int,
    start_hms: int = WINDOW_START_HMS, end_hms: int = WINDOW_END_HMS,
) -> Optional[Tuple[np.ndarray, pd.DataFrame]]:
    """한 (종목,일) 창을 엔진 순서(rowid)로 올린다 → (index 배열 int64, df).

    엔진 GetBackloadCodeQuery(is_tick) 미러(SELECT * WHERE index in [.,.], ORDER BY
    없음). 행 없으면 None. index 단조증가는 assert(rowid==시간순 전제, 위반 시 중단).
    """
    sindex = int(day) * 1_000_000 + int(start_hms)
    eindex = int(day) * 1_000_000 + int(end_hms)
    df = pd.read_sql(
        f"SELECT * FROM \"{code}\" WHERE (`index` >= {sindex} AND `index` <= {eindex})",
        conn,
    )
    if df.empty:
        return None
    idx = df["index"].to_numpy(dtype=np.int64)
    if not np.all(np.diff(idx) > 0):
        raise ValueError(f"index 비단조(rowid≠시간순): code={code} day={day}")
    return idx, df


def build_onset_namespace(
    idx: np.ndarray, df: pd.DataFrame, onset_indices: Sequence[int],
) -> Dict[str, np.ndarray]:
    """창 프레임 + 온셋 index 목록 → 온셋별 절-평가 네임스페이스(심볼→배열).

    onset_indices 는 이 창 안에 존재하는 int YYYYMMDDHHMMSS 여야 한다(부재 시 ValueError).
    파생 4항은 창 전체에 compute_derived_tick 을 1회 적용한 뒤 온셋 행을 판독한다.
    """
    onset_int = np.asarray(onset_indices, dtype=np.int64)
    pos = np.searchsorted(idx, onset_int)
    if pos.size and (pos.max() >= idx.size or np.any(idx[pos] != onset_int)):
        raise ValueError("온셋 index 가 창 프레임에 없음(정합 위반)")

    ns: Dict[str, np.ndarray] = {}
    # 저장 컬럼(as_float 미러 — NULL→0.0, 엔진 nan_to_num 규약).
    for name in STORED_CLAUSE_COLUMNS:
        col = (df[name].to_numpy() if name in df.columns
               else np.zeros(idx.size, dtype=object))
        full = np.array([as_float(v) for v in col], dtype=np.float64)
        ns[name] = full[pos]
    # 시분초 = index % 1_000_000.
    ns["시분초"] = (onset_int % 1_000_000).astype(np.int64)
    # 파생 4항(avg=30) — 단독일 창에 compute_derived_tick, 온셋 행 판독.
    derived = compute_derived_tick(df, nan_to_num=True)
    for key, formal in DERIVED_CLAUSE_MAP.items():
        vals = derived[formal].to_numpy(dtype=np.float64)[pos]
        if key == "초당거래대금평균30":
            vals = np.trunc(vals)  # 엔진 _초당거래대금평균 int() 미러(round0→정수).
        ns[key] = vals
    # 초당거래대금N1 = 직전 관측 행 초당거래대금(첫 행 0).
    amt = (df["초당거래대금"].to_numpy(dtype=np.float64)
           if "초당거래대금" in df.columns else np.zeros(idx.size))
    prevN1 = np.where(pos >= 1, amt[np.clip(pos - 1, 0, idx.size - 1)], 0.0)
    ns["초당거래대금N1"] = prevN1
    # 로컬 정의 5종.
    build_local_definitions(ns)
    # 계약 확인: 모든 네임스페이스 심볼 존재.
    missing = [s for s in NAMESPACE_SYMBOLS if s not in ns]
    if missing:
        raise RuntimeError(f"네임스페이스 심볼 누락: {missing}")
    return ns
