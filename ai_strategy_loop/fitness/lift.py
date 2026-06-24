"""P5 포렌식 — in-sample per-strategy Lift·EV(기대값) 산출 순수 모듈(분석 전용·무영향).

KR: 한 전략(혹은 한 결과 CSV)의 거래분포에서 **거래당 기대수익률(EV)**과 **lift**(기준
    승률 대비 상대 승률)·**payoff**(평균이익/|평균손실|)를 산출한다. 포렌식 강화(P5):
    "이 전략이 우연이 아니라 구조적 우위를 가지는가"를 in-sample에서 빠르게 가늠하는
    보조 지표다. edge_ratio(MFE/MAE)·backfinder_principle(precision/lift)와 같은
    분석 패밀리에 속하며, autopsy/analyze의 '수익률' 컬럼 규약을 그대로 따른다.

    **분석/리포트 전용**: 하드게이트(compute_fitness)·적합도 스코어·생성(brain)·
    winner/graded·generation에 일절 관여하지 않으며, 루프 hot path에서 읽히지 않는다.
    in-sample 지표라 lift>1·EV>0이어도 최종 전략 보증이 아니다 — holdout/다년 OOS
    검증을 반드시 거쳐야 한다(과적합 caveat). 순수·무예외.

    무예외 계약: 수익률 컬럼 부재·빈 입력·읽기 실패·전부 단일클래스는 graceful(해당
    필드 None/0). 반환 dict는 항상 'status'('ok'|'insufficient')를 담는다. 어떤 입력에도
    예외를 던지지 않는다.

EN: Computes per-trade expected value (EV), lift (win rate vs. a baseline), and payoff
    (avg win / |avg loss|) from a strategy's (or one result CSV's) trade distribution.
    Forensic helper (P5) for gauging in-sample whether a strategy has a structural edge
    rather than luck. Same analysis family as edge_ratio / backfinder_principle, reusing
    autopsy/analyze's '수익률' column convention. ANALYSIS ONLY — never touches the hard
    gate, fitness scoring, generation, winner/graded, or generations. Being in-sample,
    lift>1 / EV>0 is NOT a final-strategy guarantee — must be validated on holdout /
    multi-year OOS. Pure and side-effect-free (bad input → graceful None/0, never raises).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

# autopsy/analyze.py와 동일한 수익률 컬럼 규약(>0=이익, <=0=손실).
_RETURN_COLUMN = "수익률"

# 한 세그먼트 셀이 보고되려면 필요한 최소 거래 수(작은 셀의 잡음 통계 배제).
DEFAULT_MIN_SAMPLES = 5

# 라벨링 실패 행. add_*_segment가 컬럼 부재/범위밖에 부여하는 기본 라벨 — 세그먼트에서 제외.
_UNCLASSIFIED = "미분류"


def _load_returns(df_or_path: Any) -> Optional[pd.Series]:
    """입력(DataFrame 또는 CSV 경로)에서 '수익률' 수치 시리즈를 추출한다(BOM 자동제거·무예외).

    DataFrame이면 그대로 쓰고, 그 외(경로/문자열)는 utf-8-sig로 읽어 BOM을 제거한다.
    '수익률' 컬럼 부재·읽기 실패·빈 입력·전부 비수치는 None을 돌려 호출부가
    'insufficient'로 흡수하게 한다. 어떤 입력에도 예외를 던지지 않는다.
    """
    df = _ensure_frame(df_or_path)
    if df is None or _RETURN_COLUMN not in df.columns:
        return None
    values = pd.to_numeric(df[_RETURN_COLUMN], errors="coerce").dropna()
    if values.empty:
        return None
    return values


def _ensure_frame(df_or_path: Any) -> Optional[pd.DataFrame]:
    """입력을 DataFrame으로 정규화한다(DataFrame→그대로, 경로→utf-8-sig 로드·무예외).

    BOM 자동 제거(encoding='utf-8-sig')는 결과 CSV(Korean·utf-8-sig) 규약을 따른다.
    파일 없음/빈 파일/읽기 실패는 None으로 흡수한다(무예외).
    """
    if isinstance(df_or_path, pd.DataFrame):
        return df_or_path
    try:
        frame = pd.read_csv(df_or_path, encoding="utf-8-sig")
    except Exception:  # noqa: BLE001 - 파일 없음/빈 파일/읽기 실패는 graceful None(무예외).
        return None
    if frame is None or len(frame) == 0:
        return None
    return frame


def _metrics_from_returns(
    returns: pd.Series, baseline_win_rate: float
) -> Dict[str, Any]:
    """수치 수익률 시리즈에서 win_rate·avg_win/loss·payoff·ev·lift를 산출한다(순수).

    단일 클래스(전부 승자 또는 전부 패자)는 없는 쪽 평균을 None으로 두되, EV는 존재하는
    쪽 가중합으로 계속 산출한다(없는 쪽 기여=0). payoff는 양쪽 평균이 모두 있고
    |avg_loss|>0일 때만 산출. lift는 baseline<=0이면 None.
    """
    n = int(returns.shape[0])
    win_mask = returns > 0
    wins = returns[win_mask]
    losses = returns[~win_mask]  # 0 포함(<=0=손실 규약).

    win_rate = float(win_mask.mean())
    loss_rate = 1.0 - win_rate

    avg_win: Optional[float] = float(wins.mean()) if not wins.empty else None
    avg_loss: Optional[float] = float(losses.mean()) if not losses.empty else None

    # payoff = avg_win / |avg_loss| (양쪽 평균 존재 + |avg_loss|>0).
    payoff: Optional[float] = None
    if avg_win is not None and avg_loss is not None and abs(avg_loss) > 0:
        payoff = avg_win / abs(avg_loss)

    # ev = win_rate*avg_win + loss_rate*avg_loss (없는 쪽 기여=0).
    ev = (win_rate * avg_win if avg_win is not None else 0.0) + (
        loss_rate * avg_loss if avg_loss is not None else 0.0
    )

    # lift = win_rate / baseline (baseline<=0이면 None — 0 나눗셈/무의미).
    lift: Optional[float] = (
        win_rate / baseline_win_rate if baseline_win_rate > 0 else None
    )

    return {
        "status": "ok",
        "n": n,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff": payoff,
        "ev": float(ev),
        "lift": lift,
    }


def _insufficient() -> Dict[str, Any]:
    """입력 부족(빈/컬럼부재/읽기실패) 시의 graceful 반환 dict."""
    return {
        "status": "insufficient",
        "n": 0,
        "win_rate": None,
        "avg_win": None,
        "avg_loss": None,
        "payoff": None,
        "ev": None,
        "lift": None,
    }


def compute_lift_ev(
    df_or_path: Any, *, baseline_win_rate: float = 0.5
) -> Dict[str, Any]:
    """per-trade 분포에서 EV(거래당 기대수익률)·lift·payoff를 산출한다(순수·무예외).

    in-sample 포렌식 보조 지표: 한 전략(또는 결과 CSV)이 우연이 아니라 구조적 우위를
    가지는지 빠르게 가늠한다. 수익률 컬럼='수익률'(>0=이익, <=0=손실). EV는 거래당
    기대수익률 = win_rate*avg_win + (1-win_rate)*avg_loss. lift는 기준승률 대비 상대
    승률(baseline<=0이면 None). payoff는 평균이익/|평균손실|.

    무예외 계약: 수익률 컬럼 부재·빈 입력·읽기 실패는 status='insufficient'로 흡수한다.
    전부 단일클래스(승자만/패자만)는 status='ok'이되 없는 쪽 평균·payoff를 None으로
    둔다(EV는 존재하는 쪽 가중합으로 계속 산출). 어떤 입력에도 예외를 던지지 않는다.

    **in-sample 주의**: lift>1·EV>0이어도 최종 전략 보증이 아니다 — holdout/다년 OOS 필수.

    Args:
        df_or_path: per-trade DataFrame 또는 결과 CSV 경로(utf-8-sig BOM 자동 제거).
        baseline_win_rate: lift 분모가 되는 기준 승률(기본 0.5 = 동전던지기). <=0이면
            lift=None(0 나눗셈/무의미).

    Returns:
        {
          "status": "ok" | "insufficient",
          "n": int,                  # 유효 거래 수.
          "win_rate": float|None,    # 수익률 > 0 비율(insufficient면 None).
          "avg_win": float|None,     # 수익 거래 평균 수익률(%), 승자 없으면 None.
          "avg_loss": float|None,    # 손실 거래 평균 수익률(%, 음수), 패자 없으면 None.
          "payoff": float|None,      # avg_win / |avg_loss| (한쪽만 있거나 |avg_loss|=0 → None).
          "ev": float|None,          # 거래당 기대수익률(insufficient면 None).
          "lift": float|None,        # win_rate / baseline_win_rate (baseline<=0 → None).
        }
    """
    returns = _load_returns(df_or_path)
    if returns is None:
        return _insufficient()
    return _metrics_from_returns(returns, float(baseline_win_rate))


# ---------------------------------------------------------------------------
# (선택) 세그먼트별 EV/lift — feature_importance_by_segment 패턴
# ---------------------------------------------------------------------------

# axis → research_segments 라벨 컬럼/부여 함수 매핑.
_AXIS_SEGMENT_COLUMN = {
    "market_cap": "_market_cap_segment",
    "time": "_time_segment",
    "change": "_change_segment",
}


def _labeled_frame(df: pd.DataFrame, axis: str) -> Optional[pd.DataFrame]:
    """df에 axis에 해당하는 세그먼트 라벨을 부여한다(research_segments 재사용·무예외).

    add_*_segment는 내부에서 복사하므로 원본 df는 불변. import/라벨링 실패는 None으로
    흡수한다(무예외). 알 수 없는 axis도 None.
    """
    try:
        from cli.research_segments import (
            add_change_segment,
            add_market_cap_segment,
            add_time_segment,
        )
    except Exception:  # noqa: BLE001 - import 실패는 graceful None(무예외).
        return None

    try:
        if axis == "market_cap":
            return add_market_cap_segment(df)
        if axis == "time":
            return add_time_segment(df)
        if axis == "change":
            return add_change_segment(df)
    except Exception:  # noqa: BLE001 - 라벨링 실패는 graceful None(무예외).
        return None
    return None


def lift_ev_by_segment(
    df_or_path: Any,
    *,
    axis: str = "market_cap",
    baseline_win_rate: float = 0.5,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> Dict[str, Any]:
    """거래 분포를 axis(시총/시간대/등락률) 세그먼트로 쪼개 셀별 EV/lift를 산출한다(순수·무예외).

    각 세그먼트 셀에서 compute_lift_ev와 동일한 EV/lift/payoff를 산출한다. lift의 기준은
    풀 전체 승률이 아니라 호출부가 준 baseline_win_rate를 그대로 쓴다(compute_lift_ev와
    동일 규약 — 셀 간 비교 일관성). '미분류' 셀과 거래 수 < min_samples 셀은 잡음 배제로
    건너뛴다. 셀 리스트는 ev 오름차순(손실 집중 먼저) 정렬.

    무예외 계약: 수익률 컬럼 부재·빈 입력·읽기 실패·라벨링 실패는 status='insufficient'·
    segments=[]로 흡수한다. 어떤 입력에도 예외를 던지지 않는다.

    Args:
        df_or_path: per-trade DataFrame 또는 결과 CSV 경로(BOM 자동 제거).
        axis: 세그먼트 축('market_cap'|'time'|'change'). 기본 'market_cap'.
        baseline_win_rate: 각 셀 lift의 기준 승률(기본 0.5).
        min_samples: 한 셀이 보고되려면 필요한 최소 거래 수(기본 5).

    Returns:
        {
          "status": "ok" | "insufficient",
          "axis": str,
          "segments": [
            {"label": str, "n": int, "win_rate": float, "avg_win": float|None,
             "avg_loss": float|None, "payoff": float|None, "ev": float, "lift": float|None},
            ...
          ],  # ev 오름차순. 불가/빈 → [].
        }
    """
    df = _ensure_frame(df_or_path)
    if df is None or _RETURN_COLUMN not in df.columns:
        return {"status": "insufficient", "axis": axis, "segments": []}

    # 수익률 유효성 사전 체크(전부 비수치/빈 → insufficient).
    if _load_returns(df) is None:
        return {"status": "insufficient", "axis": axis, "segments": []}

    seg_col = _AXIS_SEGMENT_COLUMN.get(axis)
    labeled = _labeled_frame(df, axis)
    if labeled is None or seg_col is None or seg_col not in labeled.columns:
        return {"status": "insufficient", "axis": axis, "segments": []}

    base = float(baseline_win_rate)
    segments: List[Dict[str, Any]] = []
    for seg, group in labeled.groupby(seg_col, dropna=False):
        label = str(seg)
        if label == _UNCLASSIFIED:
            continue
        cell_returns = pd.to_numeric(group[_RETURN_COLUMN], errors="coerce").dropna()
        if cell_returns.shape[0] < min_samples:
            continue
        m = _metrics_from_returns(cell_returns, base)
        segments.append({
            "label": label,
            "n": m["n"],
            "win_rate": m["win_rate"],
            "avg_win": m["avg_win"],
            "avg_loss": m["avg_loss"],
            "payoff": m["payoff"],
            "ev": m["ev"],
            "lift": m["lift"],
        })

    if not segments:
        return {"status": "insufficient", "axis": axis, "segments": []}

    # ev 오름차순(손실 집중 셀 먼저)으로 정렬해 가독성↑.
    segments.sort(key=lambda r: r["ev"])
    return {"status": "ok", "axis": axis, "segments": segments}
