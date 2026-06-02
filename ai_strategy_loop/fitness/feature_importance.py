"""세그먼트별 승리-변수 피처 중요도(단변량 Cohen's d + 분위 승률) — 분석 전용(엔진/하드게이트/스코어/생성 무영향).

KR: 각 진입 피처(결과 CSV의 B_* 컬럼: 예 B_체결강도·B_등락율·B_당일거래대금·B_회전율·
    B_거래대금증감·B_시가총액·B_전일동시간비·B_매수총잔량·B_매도총잔량)가 승리거래(수익률>0)와
    패배거래(수익률<=0)를 **얼마나 잘 가르나**, 그리고 그게 **세그먼트(시총 등급 / 시간대)마다
    어떻게 다른가**를 산출한다. 측정은 단변량이다: 표준화 평균차(Cohen's d, autopsy/analyze의
    합동표준편차 _pooled_std 재사용)와 피처 상/하위 사분위 거래의 승률 차이. 기존 부검
    (autopsy/analyze.py)은 **전역(GLOBAL) 단변량** Cohen's d만 내므로, **세그먼트별 풀링** 뷰가
    빠진 조각이었다 — 시드 5년 풀 오프라인 실측은 세그먼트별 신호 차이를 보였다(예 초소형에서
    거래대금증감 d≈0.47·체결강도 d≈-0.30, 소형에서는 약해지거나 뒤집힘). 라벨링은
    cli/research_segments(시총 단위 자동 추론·09:00~ 시간 버킷)를, 로딩은 cli/_utils를 그대로
    재사용한다. "어느 시간대×시총에서 어느 진입변수가 승패를 가르나"라는 질문에 답한다.
    **분석/리포트 전용**: 하드게이트·적합도 스코어·생성(brain)·winner/graded·generation에 일절
    관여하지 않으며, 루프 hot path에서 읽히지 않는다. 대시보드 엔드포인트(/feature_importance)와
    오프라인 분석에서만 소비한다. 순수·무예외(잘못된 입력 → []).

EN: For each entry feature (B_* columns in the trade CSV, e.g. B_체결강도, B_등락율,
    B_당일거래대금, B_회전율, B_거래대금증감, B_시가총액, B_전일동시간비, B_매수총잔량,
    B_매도총잔량) this measures **how strongly it separates WINNERS (수익률>0) from LOSERS
    (수익률<=0)** — and **how that differs BY SEGMENT (market-cap tier / time-zone)**. The
    measure is univariate: a standardized mean difference (Cohen's d, reusing the pooled
    std `_pooled_std` from autopsy/analyze) plus the win-rate gap between the feature's top
    and bottom quartiles. The existing autopsy (autopsy/analyze.py) only emits the
    **GLOBAL univariate** Cohen's d, so the **per-segment-pooled** view was the gap — an
    offline run on the seed's 5-year pool showed segment-specific signals (e.g. in 초소형
    거래대금증감 d≈0.47, 체결강도 d≈-0.30; in 소형 these flip/weaken). Labeling reuses
    cli/research_segments (auto market-cap unit inference, 09:00- time buckets); loading
    reuses cli/_utils. It answers "어느 시간대×시총에서 어느 진입변수가 승패를 가르나"
    (which entry variable splits win/loss in which time-zone × market-cap). ANALYSIS ONLY —
    it never touches the hard gate, fitness scoring, generation, winner/graded, or
    generations, and is not read on the loop hot path. Consumed only by the dashboard
    endpoint (/feature_importance) and offline analysis. Pure and side-effect-free
    (bad input → []).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from cli._utils import ensure_dataframe as _ensure_dataframe
from cli.research_segments import (
    DEFAULT_TIME_BUCKETS,
    FINE_TIME_BUCKETS,
    add_change_segment,
    add_market_cap_segment,
    add_time_segment,
)

# autopsy/analyze.py의 합동표준편차 헬퍼를 그대로 재사용한다(중복 구현 회피 — 부검 변별
#   통계와 동일한 ddof-가중 pooled std). 두 표본 < 2면 0.0을 돌려 0 나눗셈을 가드한다.
from ai_strategy_loop.autopsy.analyze import _pooled_std

# 결과 CSV의 수익률 컬럼(utf-8-sig·Korean). 승패 분할 기준.
_RETURN_COLUMN = "수익률"

# 라벨링 실패 행. add_*_segment가 컬럼 부재/범위밖에 부여하는 기본 라벨 — 세그먼트에서 제외.
_UNCLASSIFIED = "미분류"


def _cohens_d(win_vals: pd.Series, lose_vals: pd.Series) -> float:
    """승/패 두 그룹 값의 표준화 평균차(Cohen's d). 합동표준편차로 나눈다(0 가드).

    d = (mean_win - mean_lose) / pooled_std. pooled_std는 autopsy/analyze의 _pooled_std
    (ddof-가중 합동표준편차)를 재사용한다. 합동표준편차가 ~0(모든 값 동일·표본 부족)이면
    변별력 0으로 본다(0 나눗셈 가드). 어떤 입력에도 예외를 던지지 않는다.
    """
    if win_vals is None or lose_vals is None:
        return 0.0
    if len(win_vals) < 2 or len(lose_vals) < 2:
        return 0.0
    pooled = _pooled_std(win_vals, lose_vals)
    if pooled <= 1e-12:
        return 0.0
    return float((float(win_vals.mean()) - float(lose_vals.mean())) / pooled)


def _quartile_win_rate(feature: pd.Series, is_win: pd.Series, top: bool) -> Optional[float]:
    """피처의 상위(top=True)/하위(top=False) 사분위 거래의 승률을 돌려준다(불가하면 None).

    피처 값으로 25%/75% 분위를 구해 top quartile(>=q75) 또는 bottom quartile(<=q25)에
    드는 거래만 골라 그 부분집합의 승률(수익률>0 비율)을 낸다. 유효값 부족·분위 동일
    (q25==q75, 상수 피처)·해당 분위 거래 0건이면 None(무예외).
    """
    valid = feature.dropna()
    if len(valid) < 4:
        return None
    q25 = float(valid.quantile(0.25))
    q75 = float(valid.quantile(0.75))
    if q75 <= q25:
        # 상수/거의-상수 피처: 사분위가 무너지면 분위 승률을 정의할 수 없다.
        return None
    if top:
        mask = feature >= q75
    else:
        mask = feature <= q25
    mask = mask & feature.notna()
    sub = is_win[mask]
    if len(sub) == 0:
        return None
    return float(sub.mean())


def compute_feature_importance(df: pd.DataFrame, min_per_group: int = 10) -> List[Dict[str, Any]]:
    """거래 DataFrame에서 B_* 진입 피처별 승/패 변별력(Cohen's d + 분위 승률)을 랭킹한다(순수·무예외).

    수익률>0(win) / <=0(lose)로 거래를 가른 뒤, df에 존재하는 수치형 B_* 컬럼을 자동
    수집한다. 각 피처에 대해 **양 그룹 모두** 비결측 유효값이 min_per_group개 이상일 때만
    cohens_d·mean_win·mean_lose·win_rate_top_q(상위 사분위 거래 승률)·win_rate_bot_q
    (하위 사분위 거래 승률)·n(유효 win+lose 수)을 산출한다. 전부-0/상수(합동표준편차 ~0)
    피처는 건너뛴다. abs(cohens_d) 내림차순 정렬한 리스트를 돌려준다.

    무예외 계약: 수익률 컬럼 부재·B_* 부재·전부 비수치·빈 df는 빈 리스트([])로 흡수한다.
    어떤 입력에도 예외를 던지지 않는다(분석/리포트 보조 경로).

    Args:
        df: 거래 DataFrame('수익률' + B_* 진입 피처 보유 권장).
        min_per_group: 한 피처가 보고되려면 win·lose **각** 그룹에 필요한 최소 유효값 수(기본 10).

    Returns:
        [
          {
            "feature": str,            # B_* 컬럼명.
            "cohens_d": float,         # (mean_win - mean_lose) / pooled_std.
            "mean_win": float,         # 승리 거래의 피처 평균.
            "mean_lose": float,        # 패배 거래의 피처 평균.
            "win_rate_top_q": float|None,  # 피처 상위 사분위 거래의 승률.
            "win_rate_bot_q": float|None,  # 피처 하위 사분위 거래의 승률.
            "n": int,                  # 유효 win+lose 거래 수.
          },
          ...
        ]  # abs(cohens_d) 내림차순. 분석 불가 → [].
    """
    if df is None or len(df) == 0 or _RETURN_COLUMN not in df.columns:
        return []

    returns = pd.to_numeric(df[_RETURN_COLUMN], errors="coerce")
    is_win = returns > 0  # 결측(NaN)은 비교에서 False → lose 쪽으로 가지 않게 아래서 마스킹.
    has_return = returns.notna()

    # df에 존재하는 수치형 B_* 컬럼 자동 수집(접두 'B_').
    feature_cols = [c for c in df.columns if isinstance(c, str) and c.startswith("B_")]
    if not feature_cols:
        return []

    ranked: List[Dict[str, Any]] = []
    for col in feature_cols:
        vals = pd.to_numeric(df[col], errors="coerce")
        # 수익률 유효 거래만 대상(승패가 정의돼야 분할 가능).
        col_valid = vals.notna() & has_return
        win_vals = vals[col_valid & is_win].dropna()
        lose_vals = vals[col_valid & (~is_win)].dropna()
        if len(win_vals) < min_per_group or len(lose_vals) < min_per_group:
            continue

        d = _cohens_d(win_vals, lose_vals)
        if d == 0.0:
            # 합동표준편차 ~0(전부-0/상수 피처) → 변별력 없음, 건너뛴다.
            continue

        # 분위 승률: 수익률 유효 거래에 한해 피처 사분위로 승률 분리(상수면 None).
        feat_for_q = vals[has_return]
        win_for_q = is_win[has_return]
        win_rate_top_q = _quartile_win_rate(feat_for_q, win_for_q, top=True)
        win_rate_bot_q = _quartile_win_rate(feat_for_q, win_for_q, top=False)

        ranked.append({
            "feature": col,
            "cohens_d": d,
            "mean_win": float(win_vals.mean()),
            "mean_lose": float(lose_vals.mean()),
            "win_rate_top_q": win_rate_top_q,
            "win_rate_bot_q": win_rate_bot_q,
            "n": int(len(win_vals) + len(lose_vals)),
        })

    # abs(cohens_d) 내림차순(가장 잘 가른 피처 먼저).
    ranked.sort(key=lambda r: abs(r["cohens_d"]), reverse=True)
    return ranked


def feature_importance_by_segment(
    df: pd.DataFrame,
    axis: str = "market_cap",
    fine_time: bool = False,
    min_per_group: int = 10,
    min_cell: int = 20,
) -> Dict[str, List[Dict[str, Any]]]:
    """거래 DataFrame을 시총 또는 시간대 세그먼트로 쪼개 셀별 피처 중요도를 산출한다(순수·무예외).

    라벨링은 add_market_cap_segment(add_time_segment(...))로 cli/research_segments를 그대로
    재사용한다(시총 단위 자동 추론, fine_time이면 5분 시초 셀). axis='market_cap'이면
    `_market_cap_segment`로, axis='time'이면 `_time_segment`로 그룹핑한다. 거래 수 >= min_cell
    셀에만 compute_feature_importance를 돌리고, '미분류' 셀은 건너뛴다.

    무예외 계약: 라벨 컬럼 부재·빈 df·잘못된 axis는 빈 dict({})로 흡수한다. 어떤 입력에도
    예외를 던지지 않는다.

    Args:
        df: 거래 DataFrame('수익률' + 라벨링용 B_시분초/B_시가총액 보유 권장).
        axis: 'market_cap'(시총 등급) 또는 'time'(시간대). 그 외 값은 빈 dict.
        fine_time: axis='time'에서 True면 FINE_TIME_BUCKETS(5분 시초), 기본 False면
            DEFAULT_TIME_BUCKETS(30분 coarse). (시간 라벨링은 항상 수행 — 시총축이어도 무해.)
        min_per_group: compute_feature_importance에 전달(피처당 win/lose 각 최소 유효값).
        min_cell: 한 세그먼트 셀이 분석되려면 필요한 최소 거래 수(기본 20).

    Returns:
        {segment_label: [ranked features], ...}  # '미분류'·저빈도 셀 제외. 불가 → {}.
    """
    if df is None or len(df) == 0:
        return {}

    buckets = FINE_TIME_BUCKETS if fine_time else DEFAULT_TIME_BUCKETS
    # add_*_segment는 내부에서 normalize_trade_frame으로 복사하므로 원본 df 불변.
    labeled = add_change_segment(add_market_cap_segment(add_time_segment(df, buckets=buckets)))

    if axis == "market_cap":
        seg_column = "_market_cap_segment"
    elif axis == "time":
        seg_column = "_time_segment"
    elif axis == "change":
        seg_column = "_change_segment"
    else:
        return {}

    if seg_column not in labeled.columns:
        return {}

    result: Dict[str, List[Dict[str, Any]]] = {}
    for seg, group in labeled.groupby(seg_column, dropna=False):
        label = str(seg)
        if label == _UNCLASSIFIED or len(group) < min_cell:
            continue
        ranked = compute_feature_importance(group, min_per_group=min_per_group)
        if ranked:
            result[label] = ranked
    return result


def feature_importance_from_csvs(
    csv_paths: List[str],
    axis: str = "market_cap",
    fine_time: bool = False,
    min_per_group: int = 10,
    min_cell: int = 20,
) -> Dict[str, Any]:
    """여러 결과 CSV를 한데 모아(pool) 전역 + 세그먼트별 피처 중요도를 산출한다(순수·무예외).

    "단일 백테가 아니라 누적된 전체 거래 풀에서 어느 진입변수가 승패를 가르나"의 진입점이다.
    각 CSV를 pandas 기본 로더(BOM 자동 제거)로 읽어(없거나 읽기 실패한 경로는 무예외로 건너뜀)
    세로로 concat한 뒤, 풀 전체에 compute_feature_importance(global)와
    feature_importance_by_segment(by_segment)를 돌린다(추가 백테 0회).

    무예외 계약: 파일 없음·빈 파일·읽기 실패는 그 경로만 건너뛴다. 어떤 입력에도 예외를
    던지지 않는다.

    Args:
        csv_paths: per-trade 결과 CSV 경로 리스트(절대/REPO_ROOT 기준 상대 모두 가능 —
            호출부가 해석해 절대경로로 넘기는 것을 권장).
        axis: 세그먼트 축 'market_cap'(기본), 'time', 또는 'change'(등락률).
        fine_time: axis='time'에서 True면 5분 시초 셀로 세분(기본 False=30분 coarse).
        min_per_group: 피처당 win/lose 각 최소 유효값 수(기본 10).
        min_cell: 세그먼트 셀 최소 거래 수(기본 20).

    Returns:
        풀이 비면 {"insufficient": True, "pooled_trades": 0}.
        그 외:
          {
            "sources": <로드 성공한 CSV 수>,
            "pooled_trades": <풀 전체 거래 수>,
            "axis": <세그먼트 축>,
            "fine_time": <bool>,
            "global": compute_feature_importance(pooled),
            "by_segment": feature_importance_by_segment(pooled, axis, fine_time),
          }
    """
    frames: List[pd.DataFrame] = []
    for path in csv_paths or []:
        if not path:
            continue
        try:
            frame = _ensure_dataframe(path)
        except Exception:  # noqa: BLE001 - 파일 없음/빈 파일/읽기 실패는 그 경로만 건너뜀(무예외).
            continue
        if frame is not None and len(frame) > 0:
            frames.append(frame)

    if not frames:
        return {"insufficient": True, "pooled_trades": 0}

    pooled = pd.concat(frames, ignore_index=True, sort=False)
    if len(pooled) == 0:
        return {"insufficient": True, "pooled_trades": 0}

    return {
        "sources": len(frames),
        "pooled_trades": int(len(pooled)),
        "axis": axis,
        "fine_time": bool(fine_time),
        "global": compute_feature_importance(pooled, min_per_group=min_per_group),
        "by_segment": feature_importance_by_segment(
            pooled, axis=axis, fine_time=fine_time,
            min_per_group=min_per_group, min_cell=min_cell,
        ),
    }
