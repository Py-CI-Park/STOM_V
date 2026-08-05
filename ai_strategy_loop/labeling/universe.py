"""QSP10 P2 — 집행 우주 뷰와 배리어 기대값 (모든 분석의 유일한 입구).

규율(QSP10 §4): 어떤 분석도 원본 라벨을 직접 읽지 않는다. `apply_universe` 를 통과한
뷰만 쓴다 — 순위권 밖·워밍업 전 신호는 **실제로 살 수 없어서** 지도에 신기루를 만든다
(QSP9 C1 부검: P1 엣지의 93%가 이 영역이었다).
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec

#: 필터 정의가 바뀌면 올린다 — 큐브·리포트에 스탬프로 남는다.
UNIVERSE_VERSION: Final = "u1"

PRICE_FLOOR: Final = 1000.0
PRICE_CAP: Final = 50000.0
SPREAD_CAP: Final = 1.0          # %
DEFAULT_WARMUP: Final = 60       # tick 초 / min 분 — 엔진 워밍업 실측값

ROUND_TRIP_COST_PCT: Final = (spec.COST_IN + spec.COST_OUT) * 100


def apply_universe(frame: pd.DataFrame, *, warmup: int = DEFAULT_WARMUP) -> pd.DataFrame:
    """집행 우주 필터 — 순위권·워밍업·가격밴드·스프레드."""
    mask = pd.Series(True, index=frame.index)
    if "관심종목" in frame:
        mask &= frame["관심종목"] == 1
    if "경과" in frame:
        mask &= frame["경과"] >= warmup
    if "현재가" in frame:
        mask &= (frame["현재가"] > PRICE_FLOOR) & (frame["현재가"] <= PRICE_CAP)
    if "spread_pct" in frame:
        mask &= frame["spread_pct"] <= SPREAD_CAP
    for flag in ("flag_no_trade", "flag_limit_up", "flag_vi_near"):
        if flag in frame:
            mask &= frame[flag] == 0
    view = frame.loc[mask].copy()
    view.attrs["universe_version"] = UNIVERSE_VERSION
    view.attrs["warmup"] = warmup
    return view


def barrier_outcome(frame: pd.DataFrame, *, tp: str, sl: str, horizon: int) -> pd.Series:
    """익절/손절 중 **먼저 닿은 쪽**. 둘 다 미도달이면 시간종료 — 미상은 없다."""
    tp_time, sl_time = frame[tp].to_numpy(), frame[sl].to_numpy()
    result = np.where(tp_time < sl_time, "win", np.where(sl_time < tp_time, "loss", "timeout"))
    # 동시(같은 초) 도달은 보수적으로 손절 처리 — 실전에서 최악을 가정한다.
    both = (tp_time == sl_time) & (tp_time < horizon)
    result = np.where(both, "loss", result)
    return pd.Series(result, index=frame.index)


def expectancy(frame: pd.DataFrame, *, tp_pct: float, sl_pct: float, tp: str, sl: str,
               horizon: int, timeout_label: str) -> dict:
    """(TP, SL, T) 청산 규칙의 기대값 — 비용 차감 후 %/건."""
    if frame.empty:
        return {"n": 0, "win_rate": float("nan"), "expectancy_pct": float("nan"),
                "breakeven_win_rate": float("nan"), "payoff": float("nan"),
                "win_n": 0, "loss_n": 0, "timeout_n": 0}
    outcome = barrier_outcome(frame, tp=tp, sl=sl, horizon=horizon)
    win_n = int((outcome == "win").sum())
    loss_n = int((outcome == "loss").sum())
    timeout_rows = frame.loc[outcome == "timeout", timeout_label]
    timeout_n = int(len(timeout_rows))

    win_ret = tp_pct - ROUND_TRIP_COST_PCT
    loss_ret = -(sl_pct + ROUND_TRIP_COST_PCT)
    timeout_sum = float(timeout_rows.fillna(0.0).sum())   # 이미 비용 차감된 라벨
    total = win_n * win_ret + loss_n * loss_ret + timeout_sum
    decided = win_n + loss_n
    return {
        "n": int(len(frame)),
        "win_n": win_n, "loss_n": loss_n, "timeout_n": timeout_n,
        "win_rate": (win_n / decided) if decided else float("nan"),
        "expectancy_pct": total / len(frame),
        "breakeven_win_rate": (sl_pct + ROUND_TRIP_COST_PCT) / (win_ret + sl_pct + ROUND_TRIP_COST_PCT),
        "payoff": win_ret / abs(loss_ret),
    }


def cluster_load(frame: pd.DataFrame) -> dict:
    """동시신호 군집도 — 자본 경로 의존성(설계서 §4.1)의 사전 경고 지표.

    같은 (일자, 시각)에 신호가 여러 개면 자본·동시보유 한도 때문에 일부는
    실제로 체결되지 않는다. 이 값이 클수록 지도 추정과 엔진 실측이 벌어진다.
    """
    if frame.empty:
        return {"mean_simultaneous": float("nan"), "max_simultaneous": 0,
                "signals_per_day": 0.0, "days": 0}
    sizes = frame.groupby(["일자", "시분초"]).size()
    days = int(frame["일자"].nunique())
    return {
        "mean_simultaneous": float(sizes.mean()),
        "max_simultaneous": int(sizes.max()),
        "signals_per_day": float(len(frame) / days),
        "days": days,
    }
