"""백파인더 원리 headless 재현 — 미래 N틱 상승 전 진입 셋업 피처분포 채굴(분석 전용·생성 시드 전용).

KR: STOM 백파인더(backtest/backfinder.py + ui/set_text.py:639)는 GUI 전용 lookahead
    라벨러다 — 각 틱 i에서 미래 [i+1, i+탐색틱수] 고가가 현재가 대비 탐색등락율(%) 이상
    오르면 그 틱을 "오를 종목의 진입 셋업"으로 보고 진입직전 피처를 기록한다(기본 300틱/10%,
    positive-only). 이 모듈은 그 원리를 **headless·순수**로 재현하되 negative 샘플을 추가해,
    raw tick DB(ai_strategy_loop/state/tick_subset.db 또는 _database/stock_tick_back.db; 종목
    테이블에 54컬럼이 직접 저장 — 엔진 prep 불필요)에서 tick 09:00~09:30 구간의 **'오를 종목의
    진입 셋업 피처분포'**를 데이터구동으로 채굴한다. 시간대(5분)×시총 세그먼트별로 승자 피처의
    분위경계(q25/q50/q75)와 **precision=winner_rate(positive/total, negative 결합)**·lift를
    산출하고, 선택적으로 winners q25~q75를 band_compiler의 BandSpec 시드 후보 또는 NL 시드
    가이드로 환류한다.

    **분석/생성-시드 전용**: 하드게이트(compute_fitness)·적합도 스코어·엔진·backtest_graph·GUI
    백파인더 배선을 일절 건드리지 않는다(원리만 재현). 라벨링 윈도우는 cli/research_segments의
    FINE_TIME_BUCKETS(09:00~09:30 5분)·시총 버킷을, 통계는 autopsy/analyze의 _pooled_std를,
    환류는 brain/band_compiler의 BandSpec을 그대로 재사용한다.

    **caveat(필수·밴드 설계 §9 위험6)**: lookahead/survivorship 편향 + forward 라벨이 '고가
    도달'이라 실 체결가/슬리피지와 괴리한다. 따라서 이 출력은 **생성 시드 전용**(최종 전략 아님)이며
    holdout/다년 OOS 검증을 반드시 거쳐야 한다.

EN: STOM's BackFinder (backtest/backfinder.py + ui/set_text.py:639) is a GUI-only
    lookahead labeler: for each tick i it checks whether the future [i+1, i+탐색틱수] high
    rises >= 탐색등락율(%) over the current price, and if so records the pre-entry features as
    a "setup of a stock about to rise" (default 300 ticks / 10%, positive-only). This module
    reproduces that principle **headless and pure**, adding negative samples, to mine the
    distribution of pre-entry setup features for would-be winners from the raw tick DB (the
    per-stock tables already hold 54 columns directly — no engine prep needed) over the tick
    09:00~09:30 window. Per time-zone(5min)×market-cap segment it emits the winners' feature
    quantile bounds (q25/q50/q75) plus precision=winner_rate (positive/total, negatives
    folded in) and lift, and optionally feeds winners' q25~q75 back as band_compiler BandSpec
    seed candidates or NL seed guidance.

    ANALYSIS / GENERATION-SEED ONLY — it never touches the hard gate (compute_fitness),
    fitness scoring, the engine, backtest_graph, or the GUI BackFinder wiring (principle
    reproduced, not wired). Reuses cli/research_segments buckets, autopsy/analyze._pooled_std,
    and brain/band_compiler.BandSpec.

    CAVEAT (required, band design §9 risk6): lookahead/survivorship bias plus a forward label
    of "the high was reached" diverges from real fill price / slippage. So this output is
    GENERATION-SEED ONLY (not a final strategy) and MUST be validated on holdout / multi-year
    OOS. Pure and side-effect-free (bad DB / missing table / missing day → graceful empty).
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from cli.research_segments import (
    DEFAULT_MARKET_CAP_BUCKETS,
    FINE_TIME_BUCKETS,
    _assign_bucket,
    _normalize_market_cap_values,
)

# autopsy/analyze.py의 합동표준편차 헬퍼를 그대로 재사용한다(중복 구현 회피 — 부검·피처중요도와
#   동일 통계). negative 결합 분포에서 effect size를 보고 싶을 때 쓴다.
from ai_strategy_loop.autopsy.analyze import _pooled_std  # noqa: F401  (재사용 가능 헬퍼)

# 환류용 밴드 표현(brain/band_compiler P0). winners q25~q75 → BandSpec 시드 후보.
from ai_strategy_loop.brain.band_compiler import BandSpec

# raw tick 종목 테이블에 직접 저장된 컬럼들(엔진 prep 불필요). index=YYYYMMDDHHMMSS 정수.
INDEX_COLUMN = "index"
PRICE_COLUMN = "현재가"

# 진입 셋업 피처(진입직전 피처분포 채굴 대상). raw 54컬럼 중 의미있는 진입 신호 + 시분초(라벨링용).
DEFAULT_FEATURE_COLS: Tuple[str, ...] = (
    "등락율",
    "체결강도",
    "당일거래대금",
    "시가총액",
    "회전율",
    "초당거래대금",
    "고저평균대비등락율",
    "시분초",
)

# 시총 라벨링이 읽는 원천 컬럼(raw 종목 테이블). research_segments 버킷과 동일 단위로 정규화한다.
MARKET_CAP_COLUMN = "시가총액"

# 라벨링 실패 라벨. _assign_bucket이 범위밖에 부여하는 기본값 — 세그먼트에서 제외.
_UNCLASSIFIED = "미분류"

# backfinder 시드 기본값(ui/set_text.py:627-628). 탐색틱수=300, 탐색등락율=10.
DEFAULT_LOOKAHEAD_TICKS = 300
DEFAULT_THRESHOLD_PCT = 10.0

# tick 09:00~09:30 시초 구간(HHMMSS 정수). 백파인더 채굴 기본 윈도우.
DEFAULT_TIME_LO = 90000
DEFAULT_TIME_HI = 93000

# 파생 라벨 컬럼명(레이블러가 df에 덧붙인다 — 입력 피처와 충돌 없음).
FORWARD_RETURN_COLUMN = "forward_return_pct"
IS_WINNER_COLUMN = "is_winner"
_TIME_SEGMENT_COLUMN = "_time_segment"
_MARKET_CAP_SEGMENT_COLUMN = "_market_cap_segment"
_SECONDS_COLUMN = "시분초"


def _hhmmss_from_index(index_series: pd.Series) -> pd.Series:
    """index(YYYYMMDDHHMMSS 정수)의 끝 6자리(HHMMSS)를 정수로 추출한다(무예외).

    index % 1_000_000 = 시분초. 비수치/결측은 NaN으로 둔다(이후 시간 필터에서 자연 제외).
    """
    numeric = pd.to_numeric(index_series, errors="coerce")
    return numeric.mod(1_000_000)


def label_forward_winners(
    df: pd.DataFrame,
    *,
    lookahead_ticks: int = DEFAULT_LOOKAHEAD_TICKS,
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    price_col: str = PRICE_COLUMN,
) -> pd.DataFrame:
    """각 틱 i에 미래 [i+1, i+lookahead] 고가 대비 상승률·승자 라벨을 부여한다(벡터화·순수·무예외).

    백파인더 원리(ui/set_text.py:639): ``탐색범위고가 = arry[i+1:i+1+탐색틱수, '현재가'].max()``,
    ``현재가대비고가등락율 = (탐색범위고가/현재가 - 1)*100``, ``is_winner = 그게 threshold 이상``.
    GUI는 positive-only지만 우리는 negative(미달)도 남겨 precision/lift를 낼 수 있게 한다.

    끝부분(미래 틱 부족: 마지막 lookahead개)은 forward 고가가 정의되지 않으므로
    forward_return_pct=NaN·is_winner=NaN(<NA>)으로 둔다(라벨 불가 행 제외용).

    무예외 계약: price_col 부재·빈 df·전부 비수치·lookahead<=0은 라벨 컬럼만 NaN으로
    덧붙여 돌려준다(원본 행 보존, 예외 없음).

    Args:
        df: 한 종목·시간순 정렬된 tick DataFrame(현재가 컬럼 보유 권장).
        lookahead_ticks: 미래 탐색 틱 수(기본 300, ui/set_text.py 시드값).
        threshold_pct: 승자 판정 상승률 임계(%, 기본 10.0).
        price_col: 현재가 컬럼명(기본 '현재가').

    Returns:
        입력 df의 복사본에 forward_return_pct(float)·is_winner(nullable bool)를 덧붙인 df.
    """
    out = df.copy()
    n = len(out)
    nan_floats = pd.Series([float("nan")] * n, index=out.index, dtype="float64")
    if n == 0 or price_col not in out.columns:
        out[FORWARD_RETURN_COLUMN] = nan_floats
        out[IS_WINNER_COLUMN] = pd.Series([pd.NA] * n, index=out.index, dtype="boolean")
        return out

    price = pd.to_numeric(out[price_col], errors="coerce").to_numpy(dtype="float64")

    look = int(lookahead_ticks)
    if look <= 0:
        out[FORWARD_RETURN_COLUMN] = nan_floats
        out[IS_WINNER_COLUMN] = pd.Series([pd.NA] * n, index=out.index, dtype="boolean")
        return out

    # 미래 [i+1, i+look] 현재가 max를 i마다 구한다 — 역방향 슬라이딩 max(끝→앞).
    #   future_max[i] = max(price[i+1 : i+1+look]). 미래가 부족한 끝 행(마지막 look개)은 NaN.
    values = [float("nan")] * n
    for i in range(n - 1):
        end = i + 1 + look
        if end > n:
            # 미래 틱 부족(끝부분) → 라벨 불가(NaN 유지).
            continue
        cur = price[i]
        if cur != cur or cur <= 0:  # NaN/0 가드(NaN != NaN).
            continue
        window = price[i + 1: end]
        window_max = float(window.max()) if window.size else float("nan")
        if window_max != window_max:
            continue
        values[i] = round((window_max / cur - 1.0) * 100.0, 4)

    forward_pct = pd.Series(values, index=out.index, dtype="float64")
    out[FORWARD_RETURN_COLUMN] = forward_pct
    # is_winner: forward_pct >= threshold (NaN은 <NA> 유지 → 라벨 불가 행 제외용).
    is_winner = (forward_pct >= float(threshold_pct))
    is_winner = is_winner.mask(forward_pct.isna(), other=pd.NA).astype("boolean")
    out[IS_WINNER_COLUMN] = is_winner
    return out


def _load_stock_day(
    con: sqlite3.Connection,
    code: str,
    day: int,
    *,
    time_lo: int,
    time_hi: int,
) -> Optional[pd.DataFrame]:
    """tick DB에서 한 종목·하루치(시분초 time_lo~time_hi) raw 틱을 시간순으로 로드한다(무예외).

    종목 테이블명 = 종목코드. index의 앞8자리=날짜(==day), 끝6자리=시분초로 필터한다.
    테이블/날짜/시간대에 데이터가 없으면 None(graceful). index 오름차순 정렬(시간순 보장).
    """
    lo = int(day) * 1_000_000 + int(time_lo)
    hi = int(day) * 1_000_000 + int(time_hi)
    try:
        # 종목 테이블명은 종목코드 그대로(예 '066970'). index 범위로 하루+시간대 필터.
        query = (
            f'SELECT * FROM "{code}" '
            f'WHERE "{INDEX_COLUMN}" >= ? AND "{INDEX_COLUMN}" < ? '
            f'ORDER BY "{INDEX_COLUMN}" ASC'
        )
        frame = pd.read_sql(query, con, params=(lo, hi))
    except Exception:  # noqa: BLE001 - 없는 테이블/읽기 실패는 그 종목·날만 건너뜀(무예외).
        return None
    if frame is None or len(frame) == 0:
        return None
    return frame


def mine_tick_window(
    db_path: str,
    codes: Sequence[str],
    days: Sequence[int],
    *,
    time_lo: int = DEFAULT_TIME_LO,
    time_hi: int = DEFAULT_TIME_HI,
    lookahead_ticks: int = DEFAULT_LOOKAHEAD_TICKS,
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    feature_cols: Sequence[str] = DEFAULT_FEATURE_COLS,
) -> Dict[str, Any]:
    """tick DB의 종목×날짜를 시초 윈도우에서 라벨링해 진입 셋업 피처를 수집한다(순수·무예외).

    각 (종목, 날짜)에 대해 _load_stock_day로 [time_lo, time_hi) 틱을 시간순 로드하고,
    label_forward_winners로 forward_return_pct·is_winner를 부여한 뒤, 라벨 가능 행(끝부분
    제외)의 진입 피처(feature_cols) + forward_return_pct + is_winner + 종목/날짜를 모은다.
    승자(is_winner=True)와 전체(라벨 가능 행 모두)를 함께 돌려줘 negative 결합 분포 산출이
    가능하게 한다.

    각 종목의 시초 윈도우는 그 종목 그날 시간순 슬라이스 안에서만 lookahead를 본다(종목·날짜
    경계 넘어 미래를 섞지 않는다 — leak 방지). 시분초 컬럼이 없으면 index에서 파생한다.

    무예외 계약: 없는 DB·없는 종목 테이블·없는 날짜·빈 윈도우는 그 조각만 건너뛴다. 어떤
    입력에도 예외를 던지지 않는다.

    Args:
        db_path: tick DB 경로(state/tick_subset.db 또는 _database/stock_tick_back.db).
        codes: 종목코드 리스트(테이블명).
        days: YYYYMMDD 정수 날짜 리스트.
        time_lo, time_hi: 시초 윈도우 HHMMSS 정수 경계([lo, hi), 기본 09:00~09:30).
        lookahead_ticks: 미래 탐색 틱 수(기본 300).
        threshold_pct: 승자 임계 상승률(%, 기본 10.0).
        feature_cols: 수집할 진입 셋업 피처 컬럼(기본 DEFAULT_FEATURE_COLS).

    Returns:
        {
          "all": labeled DataFrame(라벨 가능 행 전체: 피처 + forward_return_pct + is_winner
                  + _code + _day + 시분초),  # 비면 빈 DataFrame.
          "winners": all[is_winner==True] 부분집합,
          "rows": int(len(all)),
          "winner_count": int(승자 수),
          "codes_loaded": int(데이터를 실제로 읽은 (종목,날짜) 수),
        }
    """
    feature_cols = tuple(feature_cols)
    empty = pd.DataFrame()
    try:
        con = sqlite3.connect(db_path)
    except Exception:  # noqa: BLE001 - 없는/잘못된 DB는 빈 결과(무예외).
        return {"all": empty, "winners": empty, "rows": 0, "winner_count": 0, "codes_loaded": 0}

    collected: List[pd.DataFrame] = []
    codes_loaded = 0
    try:
        for code in codes or []:
            for day in days or []:
                frame = _load_stock_day(con, str(code), int(day), time_lo=time_lo, time_hi=time_hi)
                if frame is None:
                    continue
                codes_loaded += 1
                labeled = label_forward_winners(
                    frame,
                    lookahead_ticks=lookahead_ticks,
                    threshold_pct=threshold_pct,
                    price_col=PRICE_COLUMN,
                )
                # 라벨 가능 행만(끝부분 NaN 제외).
                labelable = labeled[labeled[IS_WINNER_COLUMN].notna()].copy()
                if len(labelable) == 0:
                    continue
                # 시분초 컬럼 보강(라벨링 세그먼트용) — 없으면 index에서 파생.
                if _SECONDS_COLUMN not in labelable.columns:
                    labelable[_SECONDS_COLUMN] = _hhmmss_from_index(labelable[INDEX_COLUMN])
                # 수집 컬럼 = 피처 + 라벨 + 시총(세그먼트) + 메타.
                keep = list(dict.fromkeys(
                    list(feature_cols)
                    + [MARKET_CAP_COLUMN, _SECONDS_COLUMN,
                       FORWARD_RETURN_COLUMN, IS_WINNER_COLUMN]
                ))
                keep = [c for c in keep if c in labelable.columns]
                sub = labelable[keep].copy()
                sub["_code"] = str(code)
                sub["_day"] = int(day)
                collected.append(sub)
    finally:
        con.close()

    if not collected:
        return {"all": empty, "winners": empty, "rows": 0, "winner_count": 0,
                "codes_loaded": codes_loaded}

    all_df = pd.concat(collected, ignore_index=True, sort=False)
    winners = all_df[all_df[IS_WINNER_COLUMN] == True].copy()  # noqa: E712 - nullable bool 명시 비교
    return {
        "all": all_df,
        "winners": winners,
        "rows": int(len(all_df)),
        "winner_count": int(len(winners)),
        "codes_loaded": codes_loaded,
    }


def _add_segments(df: pd.DataFrame, *, fine_time: bool) -> pd.DataFrame:
    """라벨 df에 시간대(5분)·시총 세그먼트 라벨을 덧붙인다(research_segments 버킷 재사용·무예외).

    시간대는 시분초(없으면 index 파생)로 FINE_TIME_BUCKETS(fine_time=True, 09:00~09:30 5분) 또는
    DEFAULT 시초 30분으로 라벨링하고, 시총은 시가총액을 research_segments와 동일 단위로 정규화해
    DEFAULT_MARKET_CAP_BUCKETS로 라벨링한다. 원본 불변(복사).
    """
    out = df.copy()
    buckets = FINE_TIME_BUCKETS if fine_time else (
        ("장초반", DEFAULT_TIME_LO, DEFAULT_TIME_HI),
    )
    # 시간 세그먼트.
    if _SECONDS_COLUMN in out.columns:
        secs = pd.to_numeric(out[_SECONDS_COLUMN], errors="coerce").fillna(0)
    elif INDEX_COLUMN in out.columns:
        secs = _hhmmss_from_index(out[INDEX_COLUMN]).fillna(0)
    else:
        secs = pd.Series([0] * len(out), index=out.index)
    out[_TIME_SEGMENT_COLUMN] = [_assign_bucket(float(v), buckets) for v in secs]
    # 시총 세그먼트(research_segments와 동일 정규화).
    if MARKET_CAP_COLUMN in out.columns:
        normalized = _normalize_market_cap_values(out[MARKET_CAP_COLUMN])
        out[_MARKET_CAP_SEGMENT_COLUMN] = [
            _assign_bucket(float(v), DEFAULT_MARKET_CAP_BUCKETS) if pd.notna(v) else _UNCLASSIFIED
            for v in normalized
        ]
    else:
        out[_MARKET_CAP_SEGMENT_COLUMN] = _UNCLASSIFIED
    return out


def winning_setup_distribution(
    df_labeled: pd.DataFrame,
    feature_cols: Sequence[str] = DEFAULT_FEATURE_COLS,
    *,
    fine_time: bool = True,
    min_count: int = 30,
) -> List[Dict[str, Any]]:
    """시간대×시총 세그먼트별 승자 진입 피처분포(q25/q50/q75)·precision·lift를 산출한다(순수·무예외).

    각 (시간대, 시총) 세그먼트 셀에서:
      - winners(is_winner=True)의 각 피처 분위경계 q25/q50/q75 (진입 셋업 분포),
      - precision = winner_rate = winners / total (negative 결합 — 우연 신호 배제),
      - lift = winner_rate / base_rate (전체 풀 승률 대비 그 셀의 상대 승률),
      - count(셀 전체 라벨 행)·winner_count.
    min_count 미만(표본하한)·'미분류' 셀은 우연변수 제거를 위해 건너뛴다. winners가 0이면
    분위는 산출 못 하나(분위 None) precision/lift는 여전히 보고한다.

    무예외 계약: is_winner 컬럼 부재·빈 df·전부 미분류는 빈 리스트([])로 흡수한다. 어떤
    입력에도 예외를 던지지 않는다(분석/생성-시드 보조 경로).

    Args:
        df_labeled: mine_tick_window의 'all' DataFrame(is_winner·시총·시분초·피처 보유).
        feature_cols: 분포를 낼 진입 피처(기본 DEFAULT_FEATURE_COLS).
        fine_time: True면 09:00~09:30 5분 셀, False면 시초 30분 한 칸.
        min_count: 한 세그먼트 셀이 보고되려면 필요한 최소 라벨 행 수(기본 30).

    Returns:
        [
          {
            "time_segment": str, "market_cap_segment": str,
            "count": int, "winner_count": int,
            "winner_rate": float,           # precision = winners/total.
            "lift": float|None,             # winner_rate / base_rate (base 0이면 None).
            "features": {feat: {"q25": float, "q50": float, "q75": float, "n": int}|None, ...},
          }, ...
        ]  # winner_rate 내림차순. 불가 → [].
    """
    if df_labeled is None or len(df_labeled) == 0 or IS_WINNER_COLUMN not in df_labeled.columns:
        return []

    feature_cols = tuple(feature_cols)
    labeled = _add_segments(df_labeled, fine_time=fine_time)

    is_win_all = labeled[IS_WINNER_COLUMN] == True  # noqa: E712
    base_total = int(is_win_all.notna().sum()) if hasattr(is_win_all, "notna") else len(labeled)
    base_winners = int(is_win_all.sum())
    base_rate = (base_winners / base_total) if base_total > 0 else 0.0

    results: List[Dict[str, Any]] = []
    grouped = labeled.groupby([_TIME_SEGMENT_COLUMN, _MARKET_CAP_SEGMENT_COLUMN], dropna=False)
    for seg_key, group in grouped:
        # seg_key = (시간대, 시총) 복합 키. ty가 groupby 키를 Hashable로만 보므로 인덱싱으로 접근.
        time_label = str(seg_key[0])
        mcap_label = str(seg_key[1])
        if time_label == _UNCLASSIFIED or mcap_label == _UNCLASSIFIED:
            continue
        count = int(len(group))
        if count < min_count:
            continue
        is_win = group[IS_WINNER_COLUMN] == True  # noqa: E712
        winner_count = int(is_win.sum())
        winner_rate = (winner_count / count) if count > 0 else 0.0
        lift = (winner_rate / base_rate) if base_rate > 1e-12 else None

        winners = group[is_win]
        features: Dict[str, Any] = {}
        for col in feature_cols:
            if col not in winners.columns:
                features[col] = None
                continue
            vals = pd.to_numeric(winners[col], errors="coerce").dropna()
            if len(vals) < 4:
                features[col] = None
                continue
            features[col] = {
                "q25": float(vals.quantile(0.25)),
                "q50": float(vals.quantile(0.50)),
                "q75": float(vals.quantile(0.75)),
                "n": int(len(vals)),
            }

        results.append({
            "time_segment": time_label,
            "market_cap_segment": mcap_label,
            "count": count,
            "winner_count": winner_count,
            "winner_rate": float(winner_rate),
            "lift": lift,
            "features": features,
        })

    results.sort(key=lambda r: r["winner_rate"], reverse=True)
    return results


# band_compiler 변수명 → BandSpec var(엔진 변수). 시분초는 시간 분기로 따로 처리하므로 제외.
_FEATURE_TO_BAND_VAR: Dict[str, str] = {
    "등락율": "등락율",
    "체결강도": "체결강도",
    "당일거래대금": "당일거래대금",
    "시가총액": "시가총액",
    "회전율": "회전율",
    "초당거래대금": "초당거래대금",
    "고저평균대비등락율": "고저평균대비등락율",
}


def to_band_seeds(
    distribution: List[Dict[str, Any]],
    *,
    min_lift: float = 1.0,
) -> List[Dict[str, Any]]:
    """승자 셋업 분포의 winners q25~q75를 band_compiler BandSpec 시드 후보로 환류한다(순수·무예외).

    각 세그먼트 셀(lift >= min_lift)에서 분위가 산출된 피처마다 ``q25 <= var < q75`` 형태의
    BandSpec(op='between_le', lo=q25, hi=q75)를 만든다 — winners 분포 중앙 50%를 진입 밴드
    후보로 본다. 시분초는 시간 분기 전용이라 BandSpec으로 만들지 않는다. 동시에 사람이 읽는 NL
    시드 가이드(생성 프롬프트/few_shot 환류용)도 함께 돌려준다.

    **이 출력은 생성 시드 전용이다**(lookahead/survivorship 편향). 최종 전략이 아니며 holdout/
    다년 OOS 검증 필수.

    무예외 계약: 빈 분포·분위 없음·매핑 없는 피처는 그 조각만 건너뛴다. 어떤 입력에도 예외를
    던지지 않는다.

    Args:
        distribution: winning_setup_distribution의 출력.
        min_lift: 시드로 환류할 최소 lift(기본 1.0 = base 대비 승률 우위 셀만).

    Returns:
        [
          {
            "time_segment": str, "market_cap_segment": str,
            "winner_rate": float, "lift": float|None,
            "band_specs": [BandSpec, ...],   # winners q25~q75 (between_le).
            "nl_guide": str,                 # NL 시드 가이드(생성 프롬프트용).
          }, ...
        ]  # 불가 → [].
    """
    if not distribution:
        return []

    seeds: List[Dict[str, Any]] = []
    for cell in distribution:
        lift = cell.get("lift")
        if lift is None or lift < float(min_lift):
            continue
        features = cell.get("features") or {}
        band_specs: List[BandSpec] = []
        nl_parts: List[str] = []
        for feat, stats in features.items():
            if stats is None:
                continue
            band_var = _FEATURE_TO_BAND_VAR.get(feat)
            if band_var is None:
                continue
            lo = float(stats["q25"])
            hi = float(stats["q75"])
            if hi <= lo:
                # 분위 무너짐(상수/거의-상수 피처) → 밴드 정의 불가.
                continue
            band_specs.append(BandSpec(var=band_var, op="between_le", lo=lo, hi=hi))
            nl_parts.append(f"{band_var} {lo:g}~{hi:g}")
        if not band_specs:
            continue
        nl_guide = (
            f"[{cell.get('time_segment')}·{cell.get('market_cap_segment')}] "
            f"승률 {cell.get('winner_rate', 0.0):.1%}"
            + (f" (lift {lift:.2f})" if lift is not None else "")
            + " 진입 셋업: " + ", ".join(nl_parts)
        )
        seeds.append({
            "time_segment": cell.get("time_segment"),
            "market_cap_segment": cell.get("market_cap_segment"),
            "winner_rate": cell.get("winner_rate"),
            "lift": lift,
            "band_specs": band_specs,
            "nl_guide": nl_guide,
        })
    return seeds
