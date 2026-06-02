"""MFE/MAE 엣지비율 + 다(多)-run 풀링 파노라마 세그먼트 — 분석 전용(엔진/하드게이트/스코어/생성 무영향).

KR: 결과 CSV에는 거래당 R_MFE(최대 유리편차 %)·R_MAE(최대 불리편차 %, 음수)가 기록되지만
    적합도(compute_fitness)에서 **현재 전혀 쓰이지 않는다**(감사 항목 #1). 이 모듈은 그
    미사용 신호로 **엣지비율(edge ratio = 평균 MFE / 평균 |MAE|)**과 보조 지표
    (MFE 포착률·승/패 trade의 평균 역행 깊이)를 산출한다. 또한 단일 백테가 아니라
    **여러 run의 거래를 한데 모아(pool)** 시간대×시가총액으로 쪼개 보는 파노라마
    세그먼트 뷰를 제공한다 — "누적된 전체 DB를 시간대·시총별로 보라"는 요구에 답한다.
    라벨링은 cli/research_segments(시총 단위 자동 추론·09:00~ 시간 버킷)을 그대로 재사용한다.
    **이 모듈은 분석/리포트 전용이다**: 하드게이트·적합도 스코어·생성(brain)·winner/graded·
    generation에 일절 관여하지 않으며, 루프 hot path에서 읽히지 않는다. 대시보드
    엔드포인트(/edge_ratio)와 오프라인 분석에서만 소비한다. 순수·무예외.

EN: Result CSVs record per-trade R_MFE (max favorable excursion %) and R_MAE (max
    adverse excursion %, negative), yet fitness (compute_fitness) **never uses them**
    today (audit item #1). This module turns that unused signal into an **edge ratio
    (mean MFE / mean |MAE|)** plus helpers (capture rate of the favorable excursion;
    how deep winners vs. losers go against us). It also offers a panoramic segment view
    that **pools trades across multiple runs** (time-zone × market-cap), answering the
    request to "analyze the FULL accumulated DB by time-zone and market-cap, not just
    one backtest". Labeling reuses cli/research_segments (auto unit-inference for market
    cap, 09:00- time buckets). ANALYSIS ONLY — it never touches the hard gate, fitness
    scoring, generation, winner/graded, or generations. Consumed only by the dashboard
    endpoint (/edge_ratio) and offline analysis. Pure and side-effect-free.
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

# 결과 CSV 컬럼명(utf-8-sig·Korean). 우선 R_MFE/R_MAE를, 없으면 R_매수후최고/최저수익률로 폴백.
_RETURN_COLUMN = "수익률"
_PROFIT_COLUMN = "수익금"
_MFE_PRIMARY = "R_MFE"
_MAE_PRIMARY = "R_MAE"
_MFE_FALLBACK = "R_매수후최고수익률"
_MAE_FALLBACK = "R_매수후최저수익률"

# 한 세그먼트 셀이 보고되려면 필요한 최소 거래 수(작은 셀의 잡음 통계 배제).
DEFAULT_MIN_SAMPLES = 5

# 라벨링 실패 행. add_*_segment가 컬럼 부재/범위밖에 부여하는 기본 라벨 — 세그먼트에서 제외.
_UNCLASSIFIED = "미분류"


def _numeric_series(df: pd.DataFrame, column: str) -> Optional[pd.Series]:
    """df[column]을 수치로 강제하고 NaN을 드롭한 시리즈를 돌려준다(없으면 None).

    pd.to_numeric(errors='coerce')로 비수치는 NaN→드롭한다. 컬럼이 없거나 유효값이
    전혀 없으면 None을 돌려 호출부가 "그 지표 산출 불가(None)"로 처리하게 한다.
    """
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    return values


def compute_edge_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """거래 DataFrame에서 엣지비율 + 보조 지표를 산출한다(순수·무예외).

    엣지비율(edge_ratio) = 평균 MFE / 평균 |MAE|. >1이면 평균적으로 유리편차가 불리편차보다
    크다(좋은 진입 타이밍의 신호). MFE/MAE 컬럼은 R_MFE/R_MAE 우선, 없으면
    R_매수후최고수익률/R_매수후최저수익률로 폴백한다. 둘 다 없으면 mfe/mae/edge 관련
    필드는 None으로 두되 count/win_rate/avg_return은 여전히 돌려준다(부분 분석 허용).

    무예외 계약: 컬럼 부재·전부 비수치는 해당 지표만 None으로 흡수한다. 어떤 입력에도
    예외를 던지지 않는다(분석/리포트 보조 경로).

    Returns:
        {
          "count": int,                  # '수익률' 유효 거래 수.
          "win_rate": float,             # 수익률 > 0 비율(유효 수익률 없으면 0.0).
          "avg_return": float,           # 평균 수익률(%).
          "total_profit": float|None,    # '수익금' 합(컬럼 없으면 None).
          "mean_mfe": float|None,        # 평균 MFE(%).
          "mean_mae": float|None,        # 평균 |MAE|(절대값, %).
          "edge_ratio": float|None,      # mean_mfe / mean_mae (mean_mae<=0 → None).
          "mae_efficiency": float|None,  # avg_return / mean_mfe (유리편차 포착률, mean_mfe<=0 → None).
          "mean_mae_losers": float|None, # 손실 거래(수익률<=0)의 평균 |MAE|.
          "mean_mae_winners": float|None,# 이익 거래(수익률>0)의 평균 |MAE|.
        }
    """
    # --- count / win_rate / avg_return (수익률 기반, 항상 시도) ---
    returns = _numeric_series(df, _RETURN_COLUMN)
    if returns is None:
        count = 0
        win_rate = 0.0
        avg_return = 0.0
    else:
        count = int(returns.shape[0])
        win_rate = float((returns > 0).mean())
        avg_return = float(returns.mean())

    # --- total_profit (수익금 합, 컬럼 없으면 None) ---
    profit = _numeric_series(df, _PROFIT_COLUMN)
    total_profit: Optional[float] = None if profit is None else float(profit.sum())

    # --- MFE/MAE: R_MFE/R_MAE 우선, 없으면 R_매수후최고/최저수익률 폴백 ---
    mfe_col = _MFE_PRIMARY if _MFE_PRIMARY in df.columns else (
        _MFE_FALLBACK if _MFE_FALLBACK in df.columns else None
    )
    mae_col = _MAE_PRIMARY if _MAE_PRIMARY in df.columns else (
        _MAE_FALLBACK if _MAE_FALLBACK in df.columns else None
    )

    mean_mfe: Optional[float] = None
    mean_mae: Optional[float] = None
    edge_ratio: Optional[float] = None
    mae_efficiency: Optional[float] = None
    mean_mae_losers: Optional[float] = None
    mean_mae_winners: Optional[float] = None

    if mfe_col is not None:
        mfe = _numeric_series(df, mfe_col)
        if mfe is not None:
            mean_mfe = float(mfe.mean())

    if mae_col is not None:
        # MAE는 음수(불리편차)라 절대값으로 깊이를 본다. 폴백 R_매수후최저수익률도 음수.
        mae_raw = pd.to_numeric(df[mae_col], errors="coerce")
        mae_abs = mae_raw.abs().dropna()
        if not mae_abs.empty:
            mean_mae = float(mae_abs.mean())

        # 승/패 trade별 평균 역행 깊이 — '이익 거래는 얕게, 손실 거래는 깊게 역행하나' 분리.
        if _RETURN_COLUMN in df.columns:
            ret_for_split = pd.to_numeric(df[_RETURN_COLUMN], errors="coerce")
            losers = mae_abs[ret_for_split.reindex(mae_abs.index) <= 0]
            winners = mae_abs[ret_for_split.reindex(mae_abs.index) > 0]
            if not losers.empty:
                mean_mae_losers = float(losers.mean())
            if not winners.empty:
                mean_mae_winners = float(winners.mean())

    # edge_ratio = mean_mfe / mean_mae (mean_mae<=0이면 0 나눗셈/무의미 → None).
    if mean_mfe is not None and mean_mae is not None and mean_mae > 0:
        edge_ratio = mean_mfe / mean_mae
    # mae_efficiency = avg_return / mean_mfe (유리편차 중 실제 포착한 비율, mean_mfe<=0 → None).
    if mean_mfe is not None and mean_mfe > 0:
        mae_efficiency = avg_return / mean_mfe

    return {
        "count": count,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "total_profit": total_profit,
        "mean_mfe": mean_mfe,
        "mean_mae": mean_mae,
        "edge_ratio": edge_ratio,
        "mae_efficiency": mae_efficiency,
        "mean_mae_losers": mean_mae_losers,
        "mean_mae_winners": mean_mae_winners,
    }


def _cell_row(label: str, sub: pd.DataFrame) -> Dict[str, Any]:
    """한 세그먼트 셀의 subframe에 compute_edge_metrics를 돌려 간결한 행 dict로 만든다."""
    m = compute_edge_metrics(sub)
    return {
        "label": label,
        "count": m["count"],
        "win_rate": m["win_rate"],
        "avg_return": m["avg_return"],
        "edge_ratio": m["edge_ratio"],
        "mean_mae": m["mean_mae"],
        "total_profit": m["total_profit"],
    }


def edge_by_segment(df: pd.DataFrame, fine_time: bool = False, min_samples: int = DEFAULT_MIN_SAMPLES) -> Dict[str, Any]:
    """거래 DataFrame을 시총·시간대·등락률·교차(시간×시총)로 쪼개 셀별 엣지 지표를 산출한다(순수·무예외).

    라벨링은 add_market_cap_segment(add_time_segment(...))로 cli/research_segments를
    그대로 재사용한다(시총 단위 자동 추론, fine_time이면 5분 시초 셀). '미분류' 셀과
    거래 수 < min_samples 셀은 건너뛴다(잡음 배제). B_등락율 컬럼이 없으면 change 축은
    빈 리스트를 돌려 기존 축에 영향 없다(graceful).

    Args:
        df: 거래 DataFrame('수익률' + 라벨링용 B_시분초/B_시가총액/B_등락율 보유 권장).
        fine_time: True면 시간축을 FINE_TIME_BUCKETS(5분 시초)로, 기본 False면
            DEFAULT_TIME_BUCKETS(30분 coarse)로 라벨링한다.
        min_samples: 한 셀이 보고되려면 필요한 최소 거래 수(기본 5).

    Returns:
        {
          "market_cap": [{label, count, win_rate, avg_return, edge_ratio, mean_mae, total_profit}, ...],
          "time":       [...],   # 시간대 셀.
          "change":     [...],   # 등락률 셀.
          "cross":      [...],   # label = "{time}×{mcap}".
        }
        각 리스트는 avg_return 오름차순(손실 집중 먼저) 정렬.
    """
    buckets = FINE_TIME_BUCKETS if fine_time else DEFAULT_TIME_BUCKETS
    # add_*_segment는 내부에서 normalize_trade_frame으로 복사하므로 원본 df 불변.
    labeled = add_change_segment(add_market_cap_segment(add_time_segment(df, buckets=buckets)))

    mcap_rows: List[Dict[str, Any]] = []
    time_rows: List[Dict[str, Any]] = []
    change_rows: List[Dict[str, Any]] = []
    cross_rows: List[Dict[str, Any]] = []

    if "_market_cap_segment" in labeled.columns:
        for seg, group in labeled.groupby("_market_cap_segment", dropna=False):
            label = str(seg)
            if label == _UNCLASSIFIED or len(group) < min_samples:
                continue
            mcap_rows.append(_cell_row(label, group))

    if "_time_segment" in labeled.columns:
        for seg, group in labeled.groupby("_time_segment", dropna=False):
            label = str(seg)
            if label == _UNCLASSIFIED or len(group) < min_samples:
                continue
            time_rows.append(_cell_row(label, group))

    if "_change_segment" in labeled.columns:
        for seg, group in labeled.groupby("_change_segment", dropna=False):
            label = str(seg)
            if label == _UNCLASSIFIED or len(group) < min_samples:
                continue
            change_rows.append(_cell_row(label, group))

    if "_time_segment" in labeled.columns and "_market_cap_segment" in labeled.columns:
        for (t_seg, m_seg), group in labeled.groupby(
            ["_time_segment", "_market_cap_segment"], dropna=False
        ):
            t_label, m_label = str(t_seg), str(m_seg)
            if t_label == _UNCLASSIFIED or m_label == _UNCLASSIFIED or len(group) < min_samples:
                continue
            cross_rows.append(_cell_row(f"{t_label}×{m_label}", group))

    # avg_return 오름차순(손실 집중 셀 먼저)으로 정렬해 가독성↑.
    mcap_rows.sort(key=lambda r: r["avg_return"])
    time_rows.sort(key=lambda r: r["avg_return"])
    change_rows.sort(key=lambda r: r["avg_return"])
    cross_rows.sort(key=lambda r: r["avg_return"])

    return {"market_cap": mcap_rows, "time": time_rows, "change": change_rows, "cross": cross_rows}


def edge_report_from_csvs(
    csv_paths: List[str], fine_time: bool = False, min_samples: int = DEFAULT_MIN_SAMPLES
) -> Dict[str, Any]:
    """여러 결과 CSV를 한데 모아(pool) 전역 엣지 지표 + 파노라마 세그먼트를 산출한다(순수·무예외).

    "단일 백테가 아니라 누적된 전체 DB를 시간대·시총별로 보라"는 요구의 진입점이다.
    각 CSV를 pandas 기본 로더(BOM 자동 제거)로 읽어(없거나 읽기 실패한 경로는 무예외로 건너뜀)
    세로로 concat한 뒤, 풀 전체에 compute_edge_metrics(global)와 edge_by_segment(세그먼트)를
    돌린다.

    무예외 계약: 파일 없음·빈 파일·읽기 실패는 그 경로만 건너뛴다. 어떤 입력에도 예외를
    던지지 않는다.

    Args:
        csv_paths: per-trade 결과 CSV 경로 리스트(절대/REPO_ROOT 기준 상대 모두 가능 —
            호출부가 해석해 절대경로로 넘기는 것을 권장).
        fine_time: True면 세그먼트 시간축을 5분 시초 셀로 세분(기본 False=30분 coarse).
        min_samples: 세그먼트 셀 최소 거래 수(기본 5).

    Returns:
        풀이 비면 {"insufficient": True, "pooled_trades": 0}.
        그 외:
          {
            "sources": <로드 성공한 CSV 수>,
            "pooled_trades": <풀 전체 거래 수>,
            "global": compute_edge_metrics(pooled),
            "segments": edge_by_segment(pooled, fine_time),
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
        "global": compute_edge_metrics(pooled),
        "segments": edge_by_segment(pooled, fine_time=fine_time, min_samples=min_samples),
    }
