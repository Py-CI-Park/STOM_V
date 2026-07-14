"""부검 세그먼트 강화 — 단변량 부검(analyze.py) 위에 세그먼트 cross-tab +
데이터구동 임계값을 얹는 **얇은 통합 레이어**.

기존 부검(analyze.py)은 단변량이다: 진입 B_* Cohen's-d, 청산 MFE/MAE/매도규칙.
여기서는 "어디서·왜 손실인지"를 정밀화하려고 두 분석기를 **재사용(wrap)**한다.

재사용(재발명 금지):
  - `cli/research_segments.py`
      add_time_segment / add_market_cap_segment : 데이터구동 라벨링(시총 단위 자동 추론).
      analyze_single_axis_segments              : 한 축(시총/시간대)별 손익·승률·MFE/MAE.
      analyze_two_axis_segments                 : 시총×시간대 cross-tab join.
  - `cli/analyzer.py`
      generate_quantile_candidates : 분위수 경계 = **구체 임계값**(하드코드 밴드 아님).
      analyze_ttest_candidates     : t검정(Benjamini-Hochberg FDR 보정)으로 변별 변수 임계값.

이 레이어가 새로 더하는 것은 **누락분뿐**이다:
  (1) 위 분석기 호출을 한 status 계약으로 묶고(analyze.py 스타일 — 무예외),
  (2) "손실 집중 세그먼트" 선별 + NL framing에 쓸 요약 dict로 정리한다.

analyze.py 계약을 그대로 따른다: 데이터 모양 문제(0건/컬럼없음/min미만)는 절대
예외를 던지지 않고 status로 반환한다. 단, 부검은 working/train 거래에서만 돌아야
하므로 is_holdout=True 면 ValueError 를 던진다(analyze.py와 동일).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from cli import analyzer as _analyzer
from cli import research_segments as _seg
from cli._utils import ensure_dataframe as _ensure_dataframe

from .analyze import (
    B_TO_STOM_VAR,
    DEFAULT_MIN_TRADES,
    RETURN_COLUMN,
    STATUS_INSUFFICIENT,
    STATUS_OK,
)

# 세그먼트 통계의 신뢰 최소 표본. analyzer/research_segments 기본(30)은
#   working-window(수십 거래)엔 과해 한 세그먼트도 안 잡힐 수 있다 → 작게.
DEFAULT_SEGMENT_MIN_SAMPLES = 5

# NL 피드백/요약에 실을 상위 세그먼트·임계값 개수(토큰 폭증 방지).
TOP_SEGMENTS = 3
TOP_THRESHOLDS = 3

# 분위수 후보 분할 수. working-window 거래 수가 적어 10분위는 과하므로 작게.
DEFAULT_QUANTILES = 4


@dataclass
class SegmentStat:
    """한 세그먼트(시총밴드 또는 시간대, 또는 둘의 교차)의 손익 요약."""

    label: str            # 사람이 읽는 세그먼트 이름(예: "소형", "장초반", "장초반×소형").
    axis: str             # 'market_cap' | 'time' | 'cross'.
    count: int
    avg_return: float
    win_rate: float
    avg_mae: float        # 평균 최저수익률(손절 깊이 프록시).
    total_profit: float
    return_diff: float    # 전체 평균 대비 초과 수익(<0 이면 손실 집중).


@dataclass
class ThresholdStat:
    """한 변별 변수의 **구체 임계값**(데이터구동) — 어디를 자르면 손실이 몰리는가."""

    feature: str          # B_* 컬럼.
    stom_var: str         # 매핑된 STOM 진입 변수(요약 가이드용).
    operator: str         # '<=' | '>=' | '>' | 'between'.
    threshold: Optional[float]   # 단일 경계(분위수/중앙값). between이면 None.
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    count: int
    mean_return: float    # 그 구간의 평균 수익률(손실 집중 구간이면 음수).
    win_rate: float
    source: str           # 'quantile' | 'ttest'.


@dataclass
class SegmentAutopsyResult:
    """세그먼트 강화 부검 1회 결과.

    status:
      - 'ok'                  : 세그먼트/임계값 산출됨.
      - 'insufficient_trades' : 거래 0건 또는 min_trades 미만(세그먼트 무의미).
    """

    trade_count: int
    overall_avg_return: float = 0.0
    overall_win_rate: float = 0.0
    market_cap_segments: List[SegmentStat] = field(default_factory=list)
    time_segments: List[SegmentStat] = field(default_factory=list)
    cross_segments: List[SegmentStat] = field(default_factory=list)
    thresholds: List[ThresholdStat] = field(default_factory=list)
    status: str = STATUS_OK
    note: str = ""
    min_trades: int = DEFAULT_MIN_TRADES


# =====================================================================
# Phase C-1 — 연도-분할 cross-tab + cross-year 일관성(stable cells).
# =====================================================================
@dataclass
class YearSegments:
    """한 연도의 세그먼트 통계(단축 시총축 + 시간×시총 교차축)."""

    year: int
    trade_count: int
    market_cap_segments: List[SegmentStat] = field(default_factory=list)
    cross_segments: List[SegmentStat] = field(default_factory=list)


@dataclass
class StableCell:
    """연도를 가로질러 return_diff 부호가 일관된 세그먼트 셀(레짐-강건 특성).

    direction:
      - 'avoid'  : 모든 등장 연도에서 return_diff < 0 (꾸준한 underperformer).
      - 'prefer' : 모든 등장 연도에서 return_diff > 0 (꾸준한 edge).
    """

    label: str                       # 세그먼트 이름(예: "대형", "장초반×대형").
    axis: str                        # 'market_cap' | 'cross'.
    direction: str                   # 'avoid' | 'prefer'.
    years_present: List[int] = field(default_factory=list)
    per_year_return_diff: List[float] = field(default_factory=list)
    mean_return_diff: float = 0.0


@dataclass
class MultiYearSegmentResult:
    """연도-분할 세그먼트 부검 1회 결과(Phase C-1).

    status:
      - 'ok'                  : >=1개 연도에서 세그먼트 산출됨.
      - 'insufficient_trades' : 사용 가능한 연도 그룹이 없음(연도 컬럼 없음/표본 미달).
    """

    trade_count: int
    years: List[YearSegments] = field(default_factory=list)
    stable_cells: List[StableCell] = field(default_factory=list)
    status: str = STATUS_OK
    note: str = ""
    min_trades_per_year: int = 20


def _to_segment_stat(item: Dict[str, Any], axis: str, *, cross: bool = False) -> SegmentStat:
    """research_segments 결과 dict 한 행을 SegmentStat으로 정규화한다."""
    if cross:
        label = f"{item.get('first_segment')}×{item.get('second_segment')}"
    else:
        label = str(item.get("segment"))
    return SegmentStat(
        label=label,
        axis=axis,
        count=int(item.get("count", 0)),
        avg_return=float(item.get("avg_return", 0.0)),
        win_rate=float(item.get("win_rate", 0.0)),
        avg_mae=float(item.get("avg_mae", 0.0)),
        total_profit=float(item.get("total_profit", 0.0)),
        return_diff=float(item.get("return_diff", 0.0)),
    )


def _to_threshold_stat(candidate: Dict[str, Any]) -> ThresholdStat:
    """analyzer 후보 dict 한 행을 ThresholdStat으로 정규화한다."""
    feature = str(candidate.get("feature", ""))
    return ThresholdStat(
        feature=feature,
        stom_var=B_TO_STOM_VAR.get(feature, feature),
        operator=str(candidate.get("operator", "")),
        threshold=candidate.get("threshold"),
        lower_bound=candidate.get("lower_bound"),
        upper_bound=candidate.get("upper_bound"),
        count=int(candidate.get("count", 0)),
        mean_return=float(candidate.get("mean_return", 0.0)),
        win_rate=float(candidate.get("win_rate", 0.0)),
        source=str(candidate.get("source", "")),
    )


def analyze_segments(
    csv_path: str,
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    segment_min_samples: int = DEFAULT_SEGMENT_MIN_SAMPLES,
    quantiles: int = DEFAULT_QUANTILES,
    is_holdout: bool = False,
    fine_time: bool = False,
) -> SegmentAutopsyResult:
    """거래 CSV를 읽어 세그먼트 cross-tab + 구체 임계값을 산출한다.

    단변량 부검(analyze_trades/analyze_exits)과 **합성**되어 쓰인다:
    이 함수는 "어느 시총 밴드·시간대에서 손실이 집중되는가"(세그먼트)와
    "어느 변수의 어느 값 구간이 손실인가"(임계값)를 더해준다.

    Args:
        csv_path: 백테스트 결과 CSV(utf-8-sig, 거래당 1행, '수익률' 컬럼 보유).
        min_trades: 통계 산출 최소 거래 수(미만이면 insufficient_trades).
        segment_min_samples: 한 세그먼트가 보고되려면 필요한 최소 거래 수.
        quantiles: 분위수 임계값 후보 분할 수.
        is_holdout: True면 ValueError(부검은 working/train 거래에서만, RV2-4/A5).
        fine_time: True면 시간대 세그먼트를 5분 시초 셀(FINE_TIME_BUCKETS)로
            세분한다. 기본 False면 기존 30분 coarse 버킷이라 세그먼트 결과가
            byte-동일하다(하위호환).

    Returns:
        SegmentAutopsyResult. 데이터 모양 문제는 예외가 아니라 status로 표현한다.

    Raises:
        ValueError: is_holdout=True 일 때.
    """
    if is_holdout:
        raise ValueError(
            "autopsy must run on working/train trades only — holdout 거래로는 부검 금지 (RV2-4/A5)"
        )

    # CSV 로드(빈 파일/없는 파일도 insufficient로 표준화).
    try:
        df = _ensure_dataframe(csv_path)
    except pd.errors.EmptyDataError:
        return SegmentAutopsyResult(
            trade_count=0, status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note="CSV가 비어 있다 — 거래 0건.",
        )
    except Exception as exc:  # noqa: BLE001 - 읽기 실패도 insufficient로 표준화.
        return SegmentAutopsyResult(
            trade_count=0, status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"CSV 읽기 실패: {exc}",
        )

    if RETURN_COLUMN not in df.columns:
        return SegmentAutopsyResult(
            trade_count=int(len(df)), status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"수익률 컬럼('{RETURN_COLUMN}')이 없어 세그먼트 분석 불가.",
        )

    returns = pd.to_numeric(df[RETURN_COLUMN], errors="coerce")
    df = df.loc[returns.notna()].reset_index(drop=True)
    trade_count = int(len(df))

    if trade_count < max(min_trades, 1):
        return SegmentAutopsyResult(
            trade_count=trade_count, status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"거래 {trade_count}건 < 최소 {min_trades}건 — 세그먼트 통계가 무의미하다.",
        )

    overall = _analyzer._overall_metrics(df, RETURN_COLUMN)

    # --- (a)(b) 세그먼트 cross-tab: 시총밴드 / 시간대 / 교차 (research_segments 재사용) ---
    #   라벨링은 add_*_segment가 데이터구동(시총 단위 자동 추론)으로 처리한다.
    #   fine_time이면 시간대 버킷을 5분 시초 셀로 세분한다(기본 OFF=30분 coarse).
    #   analyze_*_segments가 add_time_segment(buckets=...)로 시간대를 재유도하므로
    #   time_buckets만 넘기면 된다(기본값 = byte-동일).
    time_buckets = _seg.FINE_TIME_BUCKETS if fine_time else _seg.DEFAULT_TIME_BUCKETS
    labeled = _seg.add_market_cap_segment(_seg.add_time_segment(df, buckets=time_buckets))

    mcap_raw = _seg.analyze_single_axis_segments(
        labeled, segment_column="_market_cap_segment", min_samples=segment_min_samples,
        time_buckets=time_buckets,
    )
    time_raw = _seg.analyze_single_axis_segments(
        labeled, segment_column="_time_segment", min_samples=segment_min_samples,
        time_buckets=time_buckets,
    )
    cross_raw = _seg.analyze_two_axis_segments(
        labeled, first="_time_segment", second="_market_cap_segment",
        min_samples=segment_min_samples, time_buckets=time_buckets,
    )

    # 미분류 세그먼트는 버린다(라벨링 실패 행 — 가이드에 노이즈).
    market_cap_segments = [
        _to_segment_stat(it, "market_cap") for it in mcap_raw if it.get("segment") != "미분류"
    ]
    time_segments = [
        _to_segment_stat(it, "time") for it in time_raw if it.get("segment") != "미분류"
    ]
    cross_segments = [
        _to_segment_stat(it, "cross", cross=True)
        for it in cross_raw
        if it.get("first_segment") != "미분류" and it.get("second_segment") != "미분류"
    ]

    # --- (c) 구체 임계값: 분위수 경계 + t검정(BH보정) (analyzer 재사용) ---
    #   working-window라 표본이 작으니 분위수/t검정 min_samples도 세그먼트 기준에 맞춘다.
    feature_columns = _analyzer.get_feature_columns(df)
    quantile_cands = _analyzer.generate_quantile_candidates(
        df, feature_columns=feature_columns, return_col=RETURN_COLUMN,
        min_samples=segment_min_samples, quantiles=quantiles,
    )
    ttest_cands = _analyzer.analyze_ttest_candidates(
        df, feature_columns=feature_columns, return_col=RETURN_COLUMN,
        min_samples=segment_min_samples,
    )
    # 두 임계값 후보를 score 내림차순으로 합쳐 상위만 취한다(손실 집중 구간 우선).
    merged = sorted(
        list(quantile_cands) + list(ttest_cands),
        key=lambda c: float(c.get("score", 0.0)), reverse=True,
    )
    thresholds = [_to_threshold_stat(c) for c in merged[:TOP_THRESHOLDS]]

    note = (
        f"거래 {trade_count}건 — 시총 {len(market_cap_segments)}밴드 / "
        f"시간대 {len(time_segments)}구간 / 교차 {len(cross_segments)} / "
        f"임계값 {len(thresholds)}개."
    )
    return SegmentAutopsyResult(
        trade_count=trade_count,
        overall_avg_return=float(overall.get("mean_return", 0.0)),
        overall_win_rate=float(overall.get("win_rate", 0.0)),
        market_cap_segments=market_cap_segments,
        time_segments=time_segments,
        cross_segments=cross_segments,
        thresholds=thresholds,
        status=STATUS_OK,
        note=note,
        min_trades=min_trades,
    )


# =====================================================================
# Phase C-1 — 연도-분할 cross-tab + cross-year 일관성.
# =====================================================================
# stable cell로 인정하려면 등장해야 하는 최소 (qualifying) 연도 수.
#   단일년 귀속(과적합)을 stable로 오인하지 않기 위한 하한.
_STABLE_MIN_YEARS = 2

# page_data "연도교차 안정 특성"에 실을 상위 stable cell 수(토큰 폭증 방지).
TOP_STABLE_CELLS = 5

# 연도 도출에 시도할 날짜 컬럼 우선순위(YYYYMMDD... 접두 4자리 = 연도).
_YEAR_SOURCE_FALLBACKS = ("매수시간",)


def _derive_year_series(df: pd.DataFrame, year_column: str) -> Optional[pd.Series]:
    """거래별 연도(int) 시리즈를 도출한다.

    year_column(기본 '매도시간')을 우선 쓰고, 없으면 '매수시간'으로 폴백한다.
    값은 YYYYMMDD... 형태라 앞 4자리를 연도로 본다. 사용 가능한 날짜 컬럼이
    전혀 없으면 None(호출부가 status-flagged 빈 결과 반환).
    """
    candidates = [year_column] + [c for c in _YEAR_SOURCE_FALLBACKS if c != year_column]
    for col in candidates:
        if col not in df.columns:
            continue
        raw = df[col].astype(str).str.strip()
        # 앞 4자리 숫자 추출(YYYY). 4자리 미만/비숫자는 NaN.
        years = pd.to_numeric(raw.str.slice(0, 4), errors="coerce")
        if years.notna().any():
            return years
    return None


def analyze_segments_by_year(
    csv_path: str,
    *,
    min_trades_per_year: int = 20,
    segment_min_samples: int = DEFAULT_SEGMENT_MIN_SAMPLES,
    is_holdout: bool = False,
    year_column: str = "매도시간",
    fine_time: bool = False,
) -> MultiYearSegmentResult:
    """거래 CSV를 연도별로 쪼개 시총/시간×시총 세그먼트를 산출하고,
    연도를 가로질러 return_diff 부호가 일관된 셀(stable cells)을 가려낸다(Phase C-1).

    경험적 발견(2023~25): 대형/초대형 시총 코호트가 매년 worst(음의 return_diff)였다 —
    단일년 과적합이 아니라 cross-year 안정적 underperformance. 이 함수는 그런
    레짐-강건 특성을 'avoid'(매년 음수)/'prefer'(매년 양수)로 표면화한다.

    Args:
        csv_path: 백테스트 결과 CSV(거래당 1행, '수익률' + 날짜 컬럼 보유).
        min_trades_per_year: 한 연도가 평가에 포함되려면 필요한 최소 거래 수.
        segment_min_samples: 한 세그먼트 셀이 보고되려면 필요한 최소 거래 수.
        is_holdout: True면 ValueError(부검은 working/train 거래에서만, RV2-4/A5).
        year_column: 연도 도출 우선 컬럼(기본 '매도시간'). 없으면 '매수시간' 폴백.
        fine_time: True면 시간축을 5분 시초 셀(FINE_TIME_BUCKETS)로 세분(기본 OFF).

    Returns:
        MultiYearSegmentResult. 데이터 모양 문제는 예외가 아니라 status로 표현한다.

    Raises:
        ValueError: is_holdout=True 일 때(analyze_segments와 동일 계약).
    """
    if is_holdout:
        raise ValueError(
            "autopsy must run on working/train trades only — holdout 거래로는 부검 금지 (RV2-4/A5)"
        )

    try:
        df = _ensure_dataframe(csv_path)
    except pd.errors.EmptyDataError:
        return MultiYearSegmentResult(
            trade_count=0, status=STATUS_INSUFFICIENT,
            min_trades_per_year=min_trades_per_year, note="CSV가 비어 있다 — 거래 0건.",
        )
    except Exception as exc:  # noqa: BLE001 - 읽기 실패도 insufficient로 표준화.
        return MultiYearSegmentResult(
            trade_count=0, status=STATUS_INSUFFICIENT,
            min_trades_per_year=min_trades_per_year, note=f"CSV 읽기 실패: {exc}",
        )

    if RETURN_COLUMN not in df.columns:
        return MultiYearSegmentResult(
            trade_count=int(len(df)), status=STATUS_INSUFFICIENT,
            min_trades_per_year=min_trades_per_year,
            note=f"수익률 컬럼('{RETURN_COLUMN}')이 없어 연도-분할 분석 불가.",
        )

    returns = pd.to_numeric(df[RETURN_COLUMN], errors="coerce")
    df = df.loc[returns.notna()].reset_index(drop=True)
    trade_count = int(len(df))

    year_series = _derive_year_series(df, year_column)
    if year_series is None:
        return MultiYearSegmentResult(
            trade_count=trade_count, status=STATUS_INSUFFICIENT,
            min_trades_per_year=min_trades_per_year,
            note=f"연도 도출용 날짜 컬럼('{year_column}'/'매수시간')이 없어 연도-분할 불가.",
        )

    df = df.assign(_year=year_series)
    df = df.loc[df["_year"].notna()].reset_index(drop=True)

    time_buckets = _seg.FINE_TIME_BUCKETS if fine_time else _seg.DEFAULT_TIME_BUCKETS

    years: List[YearSegments] = []
    for year_value, df_year in df.groupby("_year", dropna=True):
        if len(df_year) < max(min_trades_per_year, 1):
            continue
        labeled = _seg.add_market_cap_segment(
            _seg.add_time_segment(df_year, buckets=time_buckets)
        )
        mcap_raw = _seg.analyze_single_axis_segments(
            labeled, segment_column="_market_cap_segment",
            min_samples=segment_min_samples, time_buckets=time_buckets,
        )
        cross_raw = _seg.analyze_two_axis_segments(
            labeled, first="_time_segment", second="_market_cap_segment",
            min_samples=segment_min_samples, time_buckets=time_buckets,
        )
        mcap_segs = [
            _to_segment_stat(it, "market_cap")
            for it in mcap_raw if it.get("segment") != "미분류"
        ]
        cross_segs = [
            _to_segment_stat(it, "cross", cross=True)
            for it in cross_raw
            if it.get("first_segment") != "미분류" and it.get("second_segment") != "미분류"
        ]
        years.append(YearSegments(
            year=int(year_value),
            trade_count=int(len(df_year)),
            market_cap_segments=mcap_segs,
            cross_segments=cross_segs,
        ))

    if not years:
        return MultiYearSegmentResult(
            trade_count=trade_count, status=STATUS_INSUFFICIENT,
            min_trades_per_year=min_trades_per_year,
            note=f"연도당 최소 {min_trades_per_year}건을 만족하는 연도 그룹이 없다.",
        )

    stable_cells = _find_stable_cells(years)

    note = (
        f"거래 {trade_count}건 / 평가연도 {len(years)}개 "
        f"({', '.join(str(y.year) for y in years)}) / "
        f"안정셀 {len(stable_cells)}개."
    )
    return MultiYearSegmentResult(
        trade_count=trade_count,
        years=years,
        stable_cells=stable_cells,
        status=STATUS_OK,
        note=note,
        min_trades_per_year=min_trades_per_year,
    )


def _find_stable_cells(years: List[YearSegments]) -> List[StableCell]:
    """연도별 세그먼트에서 cross-year 일관 셀(stable cells)을 가려낸다.

    한 셀(label+axis)이 >= _STABLE_MIN_YEARS개 연도에 등장하고, 등장한 모든
    연도에서 return_diff 부호가 동일(전부 <0=avoid, 전부 >0=prefer)이면 stable로
    본다. |mean_return_diff| 내림차순 상위만 노출한다(작게 유지).
    """
    # (axis, label) -> {year: return_diff}. 같은 연도 중복 라벨은 마지막 값으로 덮음
    #   (단축/교차 축은 라벨이 유일하므로 충돌 없음).
    accum: Dict[tuple, Dict[int, float]] = {}
    for ys in years:
        for seg in list(ys.market_cap_segments) + list(ys.cross_segments):
            key = (seg.axis, seg.label)
            accum.setdefault(key, {})[ys.year] = seg.return_diff

    stable: List[StableCell] = []
    for (axis, label), per_year in accum.items():
        if len(per_year) < _STABLE_MIN_YEARS:
            continue
        diffs = list(per_year.values())
        # 모든 연도에서 음수 → avoid, 모든 연도에서 양수 → prefer. 0 또는 부호혼재면 제외.
        if all(d < 0 for d in diffs):
            direction = "avoid"
        elif all(d > 0 for d in diffs):
            direction = "prefer"
        else:
            continue
        years_present = sorted(per_year.keys())
        ordered_diffs = [per_year[y] for y in years_present]
        mean_diff = sum(ordered_diffs) / len(ordered_diffs)
        stable.append(StableCell(
            label=label,
            axis=axis,
            direction=direction,
            years_present=years_present,
            per_year_return_diff=ordered_diffs,
            mean_return_diff=mean_diff,
        ))

    stable.sort(key=lambda c: abs(c.mean_return_diff), reverse=True)
    return stable[:TOP_STABLE_CELLS]


def multiyear_to_page_data(result: MultiYearSegmentResult) -> Dict[str, Any]:
    """MultiYearSegmentResult를 "연도교차 안정 특성" JSON-safe 섹션으로 직렬화한다.

    stable_cells(상위 ~5)를 {label, axis, direction, years_present,
    per_year_return_diff, mean_return_diff}로 작게 노출한다. analyze_segments의
    to_page_data와 독립적이며 기존 page_data["autopsy"] 동작에 영향을 주지 않는다.
    """
    def _cell_row(c: StableCell) -> Dict[str, Any]:
        return {
            "label": c.label,
            "axis": c.axis,
            "direction": c.direction,
            "years_present": list(c.years_present),
            "per_year_return_diff": [round(float(d), 4) for d in c.per_year_return_diff],
            "mean_return_diff": round(float(c.mean_return_diff), 4),
        }

    return {
        "status": result.status,
        "trade_count": result.trade_count,
        "years": [int(y.year) for y in result.years],
        "stable_cells": [_cell_row(c) for c in result.stable_cells],
        "note": result.note,
    }


def to_page_data(result: SegmentAutopsyResult, *, top: int = TOP_SEGMENTS) -> Dict[str, Any]:
    """SegmentAutopsyResult를 대시보드 LIVE 패널용 요약 dict로 직렬화한다.

    contract v2 page_data["autopsy"]에 실린다. JSON-직렬화 가능한 기본 타입만 담는다.
    가장 손실 집중인 세그먼트(return_diff 오름차순 = 음수 먼저) 상위 top개만 노출해
    페이로드를 작게 유지한다.
    """
    def _seg_row(s: SegmentStat) -> Dict[str, Any]:
        return {
            "label": s.label,
            "count": s.count,
            "avg_return": round(s.avg_return, 4),
            "win_rate": round(s.win_rate, 4),
            "avg_mae": round(s.avg_mae, 4),
            "return_diff": round(s.return_diff, 4),
        }

    def _thr_row(t: ThresholdStat) -> Dict[str, Any]:
        return {
            "feature": t.feature,
            "stom_var": t.stom_var,
            "operator": t.operator,
            "threshold": None if t.threshold is None else round(float(t.threshold), 4),
            "lower_bound": None if t.lower_bound is None else round(float(t.lower_bound), 4),
            "upper_bound": None if t.upper_bound is None else round(float(t.upper_bound), 4),
            "count": t.count,
            "mean_return": round(t.mean_return, 4),
            "win_rate": round(t.win_rate, 4),
            "source": t.source,
        }

    # 손실 집중(return_diff 가장 낮은) 순으로 정렬해 상위만.
    worst_mcap = sorted(result.market_cap_segments, key=lambda s: s.return_diff)[:top]
    worst_time = sorted(result.time_segments, key=lambda s: s.return_diff)[:top]
    worst_cross = sorted(result.cross_segments, key=lambda s: s.return_diff)[:top]

    return {
        "status": result.status,
        "trade_count": result.trade_count,
        "overall_avg_return": round(result.overall_avg_return, 4),
        "overall_win_rate": round(result.overall_win_rate, 4),
        "market_cap_segments": [_seg_row(s) for s in worst_mcap],
        "time_segments": [_seg_row(s) for s in worst_time],
        "cross_segments": [_seg_row(s) for s in worst_cross],
        "thresholds": [_thr_row(t) for t in result.thresholds],
        "note": result.note,
    }


# ---------------------------------------------------------------------------
# DR-05 — AnalysisCardV3 서술 섹션 어댑터. to_page_data(대시보드) 를 그대로
#   재사용하고 스키마 라벨만 덧붙인다(재구현 금지, 가법 전용). 세그먼트 발견은
#   그 자체로 행동 지시가 아니다 — build_analysis_card_v3 의 게이트를 거쳐야만
#   actionable_directives 로 승격될 수 있다(여기서는 candidate_findings 로
#   넘길 원재료만 만든다).
# ---------------------------------------------------------------------------

SEGMENT_CARD_SECTION_SCHEMA_V3 = "segment_card_section_v3"


def to_card_section_v3(result: SegmentAutopsyResult, *, top: int = TOP_SEGMENTS) -> Dict[str, Any]:
    """SegmentAutopsyResult를 AnalysisCardV3.segment_findings 항목 dict로 만든다.

    to_page_data 를 그대로 재사용해 라벨(schema)만 덧붙인다 — 별도 판정 로직
    없음(순수 서술). 게이트/directive 승격은 analysis_card_v3 의 책임이다.
    """
    page_data = to_page_data(result, top=top)
    return {"schema": SEGMENT_CARD_SECTION_SCHEMA_V3, **page_data}
