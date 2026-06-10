"""과적합 측정 advisory (C1/N1): PBO(CSCV) + Deflated Sharpe Ratio.

근거: 2026-06-02 분석능력 감사가 "PBO/CSCV=핵심 실패모드의 정답 진단, Deflated
Sharpe=우승자 상향편의 보정"으로 최우선 권고했으나 미구현 상태였다(6/5 검토 N1).
2026-06-10 근본 원인 보고서 §8 C1로 승인됨.

설계 원칙:
  - **분석 전용** — 하드게이트(compute_fitness)/graded/생성 경로를 일절 건드리지
    않는다. PBO는 '후보 집단'의 교차검증 통계라 세대 단위 graded에 끼우면 의미가
    왜곡된다(§8 스펙의 'graded 가산항' 표현 대신 동결 시점 advisory로 구현 —
    의도적 일탈, 사유 보고서에 기록).
  - 소비처: select_and_freeze(동결 아티팩트) + 결정 카드의 PBO/DSR 실측치.
  - numpy 외 의존 없음(정규 CDF는 math.erf).

용어:
  PBO  = Probability of Backtest Overfitting (CSCV; Bailey et al. 2015).
         IS 최우수 후보가 OOS에서 하위 절반에 떨어질 확률. 낮을수록 좋다.
  DSR  = Deflated Sharpe Ratio (Bailey & López de Prado 2014).
         n_trials번 시도 중 최고를 골랐다는 선택 편의를 보정한 PSR. 0.95+면
         "우연 최고가 아닐" 확신이 높다.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Euler–Mascheroni 상수 (E[max] 근사식).
_EULER_GAMMA = 0.5772156649015329


# ---------------------------------------------------------------------------
# 일별 손익 시계열 (결과 CSV → PBO 입력)
# ---------------------------------------------------------------------------

def daily_pnl_series(csv_path: str) -> Optional[Dict[str, float]]:
    """결과 CSV(거래당 1행)에서 일별 수익금 합계를 만든다.

    `매도시간`(YYYYMMDDHHMMSS) 앞 8자리를 일자로, `수익금`을 손익으로 쓴다.
    실패는 None으로 흡수한다(advisory 전용 — 어떤 판정도 막지 않는다).
    """
    try:
        import pandas as pd  # noqa: PLC0415

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "매도시간" not in df.columns or "수익금" not in df.columns:
            return None
        days = df["매도시간"].astype(str).str[:8]
        grouped = df.groupby(days)["수익금"].sum()
        return {str(day): float(total) for day, total in grouped.items()}
    except Exception:
        return None


def align_daily_matrix(
    series_by_label: Dict[str, Dict[str, float]],
) -> Tuple[List[str], List[str], np.ndarray]:
    """라벨별 일별 손익 dict들을 (일자 합집합 × 후보) 행렬로 정렬한다.

    거래 없는 날은 0 손익으로 본다(전략이 그 날 시장에 있었으나 진입 안 함).
    Returns: (dates, labels, T×N 행렬).
    """
    labels = sorted(series_by_label.keys())
    all_days = sorted({d for s in series_by_label.values() for d in s})
    matrix = np.zeros((len(all_days), len(labels)), dtype=float)
    for j, label in enumerate(labels):
        series = series_by_label[label]
        for i, day in enumerate(all_days):
            matrix[i, j] = series.get(day, 0.0)
    return all_days, labels, matrix


# ---------------------------------------------------------------------------
# PBO via CSCV
# ---------------------------------------------------------------------------

def _metric(block: np.ndarray) -> np.ndarray:
    """후보별 성과 척도 — 평균/표준편차(샤프형). 무변동 후보는 평균만."""
    mean = block.mean(axis=0)
    std = block.std(axis=0, ddof=1)
    out = np.where(std > 0, mean / np.where(std > 0, std, 1.0), mean)
    return out


def pbo_cscv(
    matrix: np.ndarray,
    *,
    n_blocks: int = 8,
    max_combinations: int = 500,
) -> Optional[Dict[str, object]]:
    """CSCV로 PBO를 추정한다.

    Args:
        matrix: T×N (기간×후보) 손익 행렬. N>=2, 유효 블록 분할 가능해야 한다.
        n_blocks: 짝수 블록 수 S. 모든 C(S, S/2) 조합에서 IS/OOS를 구성한다.
        max_combinations: 조합 수 상한(계산량 가드).

    Returns:
        {pbo, n_combinations, n_candidates, n_periods, median_logit, is_best_oos_mean_rank}
        또는 입력 부족 시 None (advisory — 판정을 막지 않는다).
    """
    if matrix.ndim != 2:
        return None
    T, N = matrix.shape
    if N < 2 or n_blocks < 2 or n_blocks % 2 != 0:
        return None
    if T < n_blocks * 2:  # 블록당 최소 2개 기간
        return None

    blocks = np.array_split(np.arange(T), n_blocks)
    combos = list(combinations(range(n_blocks), n_blocks // 2))
    if len(combos) > max_combinations:
        combos = combos[:max_combinations]

    logits: List[float] = []
    oos_ranks: List[float] = []
    for train_ids in combos:
        train_rows = np.concatenate([blocks[i] for i in train_ids])
        test_rows = np.concatenate(
            [blocks[i] for i in range(n_blocks) if i not in train_ids]
        )
        is_perf = _metric(matrix[train_rows])
        oos_perf = _metric(matrix[test_rows])
        best = int(np.argmax(is_perf))
        # OOS 상대 순위 ω ∈ (0,1): 1에 가까울수록 OOS에서도 상위.
        rank = (oos_perf < oos_perf[best]).sum() + 0.5 * (
            (oos_perf == oos_perf[best]).sum() - 1
        )
        omega = (rank + 0.5) / N
        omega = min(max(omega, 1e-6), 1 - 1e-6)
        logits.append(math.log(omega / (1.0 - omega)))
        oos_ranks.append(omega)

    logits_arr = np.array(logits)
    return {
        "pbo": float((logits_arr <= 0).mean()),
        "n_combinations": len(combos),
        "n_candidates": int(N),
        "n_periods": int(T),
        "median_logit": float(np.median(logits_arr)),
        "is_best_oos_mean_rank": float(np.mean(oos_ranks)),
    }


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """표준정규 분위수(이분법 — scipy 의존 회피, advisory 정밀도면 충분)."""
    p = min(max(p, 1e-12), 1 - 1e-12)
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def expected_max_sharpe(n_trials: int, var_sharpe: float) -> float:
    """n_trials개 무정보 시도 중 관측될 최대 샤프의 기대값(선택 편의 기준선)."""
    if n_trials <= 1:
        return 0.0
    sd = math.sqrt(max(var_sharpe, 1e-12))
    z1 = _norm_ppf(1.0 - 1.0 / n_trials)
    z2 = _norm_ppf(1.0 - 1.0 / (n_trials * math.e))
    return sd * ((1.0 - _EULER_GAMMA) * z1 + _EULER_GAMMA * z2)


def deflated_sharpe_ratio(
    returns: Sequence[float],
    *,
    n_trials: int,
) -> Optional[Dict[str, float]]:
    """일별 손익 시계열의 DSR을 구한다.

    SR_hat(기간 단위) 대비, n_trials 시도 중 최고를 골랐을 때의 기대 최대 샤프
    SR0을 기준선으로 한 PSR을 반환한다. DSR >= 0.95면 선택 편의를 보정해도
    유의하다고 본다(관례적 컷 — advisory).
    """
    arr = np.asarray(list(returns), dtype=float)
    T = arr.size
    if T < 20:
        return None
    std = arr.std(ddof=1)
    if std <= 0:
        return None
    sr_hat = float(arr.mean() / std)
    centered = (arr - arr.mean()) / std
    skew = float((centered**3).mean())
    kurt = float((centered**4).mean())
    var_sr = (1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat**2) / max(T - 1, 1)
    sr0 = expected_max_sharpe(max(int(n_trials), 1), 1.0 / max(T - 1, 1))
    denom = math.sqrt(max(1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat**2, 1e-12))
    z = (sr_hat - sr0) * math.sqrt(max(T - 1, 1)) / denom
    return {
        "sharpe_hat": sr_hat,
        "expected_max_sharpe_null": float(sr0),
        "dsr": float(_norm_cdf(z)),
        "n_periods": float(T),
        "n_trials": float(n_trials),
        "skew": skew,
        "kurtosis": kurt,
        "var_sharpe": float(var_sr),
    }
