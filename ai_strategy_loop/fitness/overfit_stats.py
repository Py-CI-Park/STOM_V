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


# ---------------------------------------------------------------------------
# R3 (2026-06-11) — 블록 부트스트랩 몬테카를로 (일별 손익, 레짐 군집 보존)
# ---------------------------------------------------------------------------
# 배경: GUI 백테스트의 MC(back_static_numba.bootstrap_test)는 거래 수익률 iid 추출이라
#   레짐 군집·시퀀스 위험을 지운다 — 6/2 캠페인의 in-sample iid MC(P=77.9%)가 OOS에서
#   무너진 전례가 기록돼 있다(6/5 검토 §4.3). 여기서는 **일별 손익을 블록(기본 5거래일)
#   단위로 재추출**해 군집을 보존하고, iid 거래 추출로는 불가능한 **MDD(낙폭금액) 분포**를
#   함께 산출한다. 분석/동결 advisory 전용 — 게이트·선택·생성에 관여하지 않는다.

def _max_drawdown_amount(cumulative: np.ndarray) -> float:
    """누적 손익 곡선의 최대 낙폭 금액(양수)을 반환한다."""
    peak = np.maximum.accumulate(cumulative)
    return float(np.max(peak - cumulative)) if cumulative.size else 0.0


def block_bootstrap_daily(
    daily_pnl: Sequence[float],
    *,
    n_boot: int = 2000,
    block_len: int = 5,
    seed: int = 20260611,
    fan_points: int = 40,
) -> Optional[Dict[str, object]]:
    """일별 손익의 블록 부트스트랩 분포(총손익·MDD·수익확률 + 팬차트 분위 경로).

    Args:
        daily_pnl: 일별 손익(원) 시퀀스(거래일 순서 보존 — 블록이 군집을 보존한다).
        n_boot: 재추출 횟수.
        block_len: 블록 길이(거래일). 기본 5(1주).
        seed: 결정론 시드(재현성 — 같은 입력이면 같은 advisory).
        fan_points: 팬차트용 누적 경로 다운샘플 포인트 수.

    Returns:
        {profit_mean, profit_p05, profit_p50, profit_p95, p_positive,
         mdd_p50, mdd_p95, n_days, n_boot, block_len,
         fan: {x(0..1 비율), p05, p25, p50, p75, p95 각 누적경로}}
        입력 부족(<block_len*4일)이면 None (advisory — 판정을 막지 않는다).
    """
    arr = np.asarray(list(daily_pnl), dtype=float)
    T = arr.size
    if T < block_len * 4 or n_boot < 100:
        return None

    rng = np.random.default_rng(seed)
    n_blocks_needed = int(math.ceil(T / block_len))
    max_start = T - block_len
    starts = rng.integers(0, max_start + 1, size=(n_boot, n_blocks_needed))

    totals = np.empty(n_boot)
    mdds = np.empty(n_boot)
    # 팬차트: 누적 경로를 fan_points 지점으로 다운샘플해 분위수 밴드를 만든다.
    idx = np.linspace(0, T - 1, num=min(fan_points, T)).astype(int)
    paths = np.empty((n_boot, idx.size))
    for i in range(n_boot):
        sample = np.concatenate(
            [arr[s:s + block_len] for s in starts[i]]
        )[:T]
        cum = np.cumsum(sample)
        totals[i] = cum[-1]
        mdds[i] = _max_drawdown_amount(cum)
        paths[i] = cum[idx]

    fan = {
        "x": [round(float(v) / max(T - 1, 1), 4) for v in idx],
        "p05": np.percentile(paths, 5, axis=0).round(0).tolist(),
        "p25": np.percentile(paths, 25, axis=0).round(0).tolist(),
        "p50": np.percentile(paths, 50, axis=0).round(0).tolist(),
        "p75": np.percentile(paths, 75, axis=0).round(0).tolist(),
        "p95": np.percentile(paths, 95, axis=0).round(0).tolist(),
    }
    return {
        "profit_mean": float(totals.mean()),
        "profit_p05": float(np.percentile(totals, 5)),
        "profit_p50": float(np.percentile(totals, 50)),
        "profit_p95": float(np.percentile(totals, 95)),
        "p_positive": float((totals > 0).mean()),
        "mdd_p50": float(np.percentile(mdds, 50)),
        "mdd_p95": float(np.percentile(mdds, 95)),
        "n_days": int(T),
        "n_boot": int(n_boot),
        "block_len": int(block_len),
        "seed": int(seed),
        "fan": fan,
        "note": "block bootstrap on daily P&L — preserves regime clustering; advisory only",
    }


# ---------------------------------------------------------------------------
# R7 (2026-06-11) — 후보 간 일별 손익 상관 (포트폴리오/앙상블 재료)
# ---------------------------------------------------------------------------

def daily_correlation_matrix(
    series_by_label: Dict[str, Dict[str, float]],
) -> Optional[Dict[str, object]]:
    """후보들의 일별 손익 상관 행렬(피어슨). 앙상블/보완(1안) 설계 재료.

    낮은 상관의 흑자 후보 조합이 포트폴리오 MDD를 낮춘다(분모 효과 — B2 감사 참조).
    입력이 2후보 미만이거나 정렬 실패면 None (advisory).
    """
    if len(series_by_label) < 2:
        return None
    try:
        _days, labels, matrix = align_daily_matrix(series_by_label)
        if matrix.shape[0] < 10:
            return None
        with np.errstate(invalid="ignore"):
            corr = np.corrcoef(matrix.T)
        corr = np.nan_to_num(corr, nan=0.0)
        return {
            "labels": labels,
            "n_days": int(matrix.shape[0]),
            "matrix": [[round(float(v), 4) for v in row] for row in corr],
        }
    except Exception:  # noqa: BLE001 - advisory.
        return None


# ---------------------------------------------------------------------------
# N2 (2026-06-11) — 후보 풀 독립성 진단: 유효 독립 후보 수
# ---------------------------------------------------------------------------

def effective_independent_count(corr: Dict[str, object]) -> Optional[Dict[str, object]]:
    """후보 풀의 '유효 독립 후보 수' N_eff = N / (1 + (N-1)·ρ̄) (advisory).

    1-D 템플릿 변형들은 거의 같은 거래를 공유해 일별 손익 상관이 높다(쌍둥이 풀).
    CSCV(PBO)는 후보들이 함께 오르내리면 IS/OOS 분할에서도 같은 순위를 유지해
    과적합 확률을 과소평가한다. 평균 쌍별 상관 ρ̄(음수는 0으로 클램프 — 보수적)로
    유효 표본수를 병기하고, ρ̄>0.7이면 PBO 신뢰도 경고를 단다. 판정 미사용.
    """
    try:
        matrix = corr.get("matrix")
        labels = corr.get("labels") or []
        n = len(labels)
        if not matrix or n < 2:
            return None
        off = [float(matrix[i][j]) for i in range(n) for j in range(n) if i < j]
        rho = max(0.0, sum(off) / len(off))
        n_eff = n / (1.0 + (n - 1) * rho) if rho < 1.0 else 1.0
        out: Dict[str, object] = {
            "n_candidates": n,
            "mean_pairwise_correlation": round(rho, 4),
            "effective_independent_candidates": round(n_eff, 2),
        }
        if rho > 0.7:
            out["pbo_reliability_warning"] = (
                f"후보 풀 평균 상관 {rho:.2f} > 0.7 — 후보들이 사실상 쌍둥이라"
                f" PBO가 과적합을 과소평가할 수 있음(유효 독립 후보 ≈ {n_eff:.1f})"
            )
        return out
    except Exception:  # noqa: BLE001 - advisory.
        return None


# ---------------------------------------------------------------------------
# P3 (2026-06-11) — 누적 손익곡선의 '우상향 품질' 지표
# ---------------------------------------------------------------------------

def curve_shape_metrics(daily: Dict[str, float]) -> Optional[Dict[str, object]]:
    """사람이 우상향 '그림'으로 시드를 고르던 직관의 정량화 (advisory 전용).

    같은 총수익이라도 "한 달에 다 벌고 멈춘 곡선"과 "꾸준히 오르는 곡선"을
    구분한다. 선택 판정에는 쓰지 않는다 — 매끈한 과거 곡선은 곡선적합으로
    만들기 쉽기 때문(검토 문서 §3 경고). 근거 병기·동순위 참고용.

    - uptrend_r2: 누적곡선 vs 거래일 인덱스 선형 R²(기울기 음수면 0).
    - max_stagnation_days: 신고점 미갱신 최장 거래일 수("오래 멈추지 않는다").
    - monthly_positive_ratio: 흑자 월 비율("특정 달 운빨이 아니다").
    - mdd_amount: 일별 누적 기준 최대 낙폭 금액("깊게 꺼지지 않는다").
    입력 10거래일 미만이면 None.
    """
    if not daily or len(daily) < 10:
        return None
    try:
        days = sorted(daily)
        vals = np.asarray([float(daily[d]) for d in days], dtype=float)
        cum = np.cumsum(vals)
        if float(np.std(cum)) < 1e-9:
            r2 = 0.0
        else:
            x = np.arange(len(cum), dtype=float)
            slope = float(np.polyfit(x, cum, 1)[0])
            corr = float(np.corrcoef(x, cum)[0, 1])
            r2 = corr ** 2 if slope > 0 else 0.0
        peak = np.maximum.accumulate(cum)
        stagnation, current = 0, 0
        for c, p in zip(cum, peak):
            current = current + 1 if c < p else 0
            stagnation = max(stagnation, current)
        monthly: Dict[str, float] = {}
        for d, v in zip(days, vals):
            key = str(d)[:6]
            monthly[key] = monthly.get(key, 0.0) + float(v)
        positive_months = sum(1 for v in monthly.values() if v > 0)
        return {
            "uptrend_r2": round(float(r2), 4),
            "max_stagnation_days": int(stagnation),
            "monthly_positive_ratio": round(positive_months / max(len(monthly), 1), 4),
            "n_months": len(monthly),
            "mdd_amount": round(_max_drawdown_amount(cum), 2),
        }
    except Exception:  # noqa: BLE001 - advisory.
        return None
