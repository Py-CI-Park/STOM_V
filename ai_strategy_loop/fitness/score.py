"""복합 적합도 계산 (RV2-3).

  composite = compute_calmar(cagr, mdd) x compute_uptrend_r2(equity) x gate

metrics dict 키는 cli/runner.py `_extract_metrics`가 산출하는 이름을 그대로 쓴다:
  - cagr             : 연간예상수익률 (CAGR, %)
  - mdd_pct          : 최대낙폭률 (MDD, %, 양수)
  - trade_count      : 거래횟수
  - total_profit_krw : 수익금합계 (총수익, 원)

엔진의 CAGR/MDD를 재사용한다 — 여기서 다시 계산하지 않는다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Optional, Sequence

# MDD가 사실상 0인지 판정하는 epsilon (% 단위).
_MDD_EPSILON = 1e-9
# MDD≈0 이고 수익이 양(+)일 때 Calmar에 부여하는 상한값 (∞ 회피).
_CALMAR_CAP = 1e6


@dataclass
class FitnessResult:
    """복합 적합도 계산 결과 + 구성요소.

    score        : 최종 복합 점수 (calmar x uptrend_r2 x gate)
    calmar       : CAGR/MDD
    uptrend_r2   : 누적수익 곡선의 직선회귀 R² (0..1)
    gate_passed  : gate 통과 여부 (False면 score=0)
    reason       : gate 실패 사유(통과 시 "ok")
    cagr/mdd/trade_count/total_profit : 판정에 쓴 원시 구성요소
    """

    score: float
    calmar: float
    uptrend_r2: float
    gate_passed: bool
    reason: str
    cagr: float
    mdd: float
    trade_count: int
    total_profit: float


@dataclass
class GradedResult:
    """등급화 적합도(선택 그래디언트) 계산 결과 + 구성요소.

    하드 게이트(compute_fitness)는 졸업/우승 기준으로 그대로 유지하고, 이 점수는
    **선택(selection)** 전용이다. 게이트를 통과하지 못한 전략들 사이에서도
    "통과에 더 가까운" 전략이 더 높은 점수를 받도록 0..1 범위의 부드러운
    그래디언트를 만든다.

    graded:
      - 게이트 통과: 1.0 + composite  → 항상 1.0 이상 (실패 전략 전부보다 위).
      - 게이트 실패: [0, 1) 범위. 각 제약 "근접도"의 평균(combiner=mean).
        통과에 가까울수록 1에 근접한다.

    구성요소(게이트 실패 시 의미를 가진다):
      trades_term  : min(trade_count / min_trades, 1.0)
      mdd_term     : 1.0 if mdd<=cap else clamp(cap / mdd, 0, 1)
      profit_term  : 손익 로지스틱 — 손실<0 → ~0, 손익분기 → ~0.5, 이익>0 → ~1
      uptrend_term : uptrend_r2 (이미 [0,1])
      composite    : 게이트 통과 시의 calmar x uptrend_r2 (FitnessResult.score 와 동일)
      gate_distance: 게이트 실패 사유를 사람이 읽을 수 있게 요약한 문자열.
    """

    graded: float
    gate_passed: bool
    composite: float
    trades_term: float
    mdd_term: float
    profit_term: float
    uptrend_term: float
    gate_distance: str
    # 원시 구성요소 (피드백/로그용).
    cagr: float
    mdd: float
    trade_count: int
    total_profit: float
    uptrend_r2: float


def compute_uptrend_r2(equity_series: Sequence[float]) -> float:
    """누적수익 곡선을 우상향 직선에 회귀했을 때의 결정계수 R² (0..1).

    x = 거래 인덱스 0..n-1, y = 누적수익. 꾸준히 우상향하는 곡선일수록 1에 가깝고,
    한 번에 튀는(spiky) 곡선은 낮다. 점이 2개 미만이거나 분산이 0이면 0.
    """
    n = len(equity_series)
    if n < 2:
        return 0.0

    xs = list(range(n))
    ys = [float(v) for v in equity_series]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0.0 or var_y <= 0.0:
        # x 분산 0은 불가(인덱스라 항상 증가)하지만, y 분산 0(평평한 곡선)이면 R²=0.
        return 0.0

    cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    # 단순 선형회귀의 R² = corr(x, y)^2 = cov^2 / (var_x * var_y).
    r2 = (cov_xy * cov_xy) / (var_x * var_y)

    # 부동소수 오차로 1을 살짝 넘거나 음수가 되는 경우를 [0,1]로 clamp.
    if r2 < 0.0:
        return 0.0
    if r2 > 1.0:
        return 1.0
    return r2


def compute_calmar(cagr: float, mdd: float) -> float:
    """Calmar 비율 = CAGR ÷ MDD. MDD≈0을 안전하게 처리한다.

    - MDD <= epsilon 이고 CAGR > 0  -> 상한값(_CALMAR_CAP) (낙폭 없이 상승 = 매우 좋음)
    - MDD <= epsilon 이고 CAGR <= 0 -> 0.0 (상승도 없으면 보상 없음)
    - 그 외                          -> CAGR / abs(MDD)

    MDD는 % 단위 양수로 들어온다고 가정하되, 음수로 들어와도 abs로 방어한다.
    """
    mdd_abs = abs(mdd)
    if mdd_abs <= _MDD_EPSILON:
        return _CALMAR_CAP if cagr > 0.0 else 0.0
    return cagr / mdd_abs


def compute_fitness(metrics: dict, equity_series: Sequence[float], config) -> FitnessResult:
    """metrics dict + 누적수익 곡선 + config로 복합 적합도를 계산한다.

    composite = calmar x uptrend_r2 x gate
    gate = 1 if (trade_count >= min_trades AND mdd <= mdd_cap AND total_profit > 0) else 0
    """
    cagr = float(metrics.get("cagr", 0.0) or 0.0)
    mdd = float(metrics.get("mdd_pct", 0.0) or 0.0)
    trade_count = int(metrics.get("trade_count", 0) or 0)
    total_profit = float(metrics.get("total_profit_krw", 0) or 0)

    calmar = compute_calmar(cagr, mdd)
    uptrend_r2 = compute_uptrend_r2(equity_series)

    # gate 판정 (실패 사유를 첫 위반 기준으로 기록).
    min_trades = int(getattr(config, "min_trades", 0))
    mdd_cap = float(getattr(config, "mdd_cap", float("inf")))

    reason = "ok"
    gate_passed = True
    if trade_count < min_trades:
        gate_passed = False
        reason = f"trade_count {trade_count} < min_trades {min_trades}"
    elif abs(mdd) > mdd_cap:
        gate_passed = False
        reason = f"mdd {abs(mdd):.4g} > mdd_cap {mdd_cap:.4g}"
    elif total_profit <= 0.0:
        gate_passed = False
        reason = f"total_profit {total_profit:.4g} <= 0"

    gate = 1.0 if gate_passed else 0.0
    score = calmar * uptrend_r2 * gate

    return FitnessResult(
        score=score,
        calmar=calmar,
        uptrend_r2=uptrend_r2,
        gate_passed=gate_passed,
        reason=reason,
        cagr=cagr,
        mdd=mdd,
        trade_count=trade_count,
        total_profit=total_profit,
    )


def _clamp01(x: float) -> float:
    """x를 [0,1] 구간으로 자른다."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _profit_term(total_profit: float, scale: float) -> float:
    """총손익을 [0,1] 단조 증가 척도로 변환한다 (로지스틱).

    - 큰 손실      → ~0
    - 손익분기(0) → 0.5  (logistic(0) = 0.5)
    - 큰 이익      → ~1

    scale은 손익을 정규화하는 기준 규모(원). 0/음수면 안전한 기본값으로 폴백한다.
    total_profit / scale 을 로지스틱에 통과시킨다. 단조 증가이며 모든 입력에서
    [0,1]을 벗어나지 않는다.
    """
    import math  # noqa: PLC0415

    if scale <= 0.0:
        scale = 1.0
    z = total_profit / scale
    # overflow 가드: 큰 음수 z에서 exp(-z)가 발산하므로 clamp.
    if z < -50.0:
        return 0.0
    if z > 50.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def compute_graded_fitness(metrics: dict, equity_series: Sequence[float], config) -> GradedResult:
    """하드 게이트를 제거하지 않고 **선택 그래디언트**를 주는 등급화 적합도.

    하드 게이트(compute_fitness)는 졸업/우승 기준으로 그대로 둔다. 이 함수는
    루프가 매 세대 best를 고르고 진행 방향을 잡는 데 쓰는 0..∞ 스칼라를 만든다.

      게이트 통과: graded = 1.0 + composite   (composite = calmar x uptrend_r2)
                   → 어떤 실패 전략(graded < 1.0)보다도 항상 위에 랭크된다.
      게이트 실패: graded = mean(trades_term, mdd_term, profit_term, uptrend_term)
                   → [0,1) 범위. 각 제약에 "얼마나 가까운지"의 평균이라
                     통과에 가까운 전략일수록 높다 (= 부드러운 선택 그래디언트).

    combiner로 product가 아닌 mean을 쓰는 이유: 한 제약이 0이어도(예: uptrend_r2=0)
    나머지 근접도가 살아남아 그래디언트가 평평해지지 않는다(product면 항 하나가
    0이면 전체가 0이 되어 변별이 사라진다).
    """
    cagr = float(metrics.get("cagr", 0.0) or 0.0)
    mdd = abs(float(metrics.get("mdd_pct", 0.0) or 0.0))
    trade_count = int(metrics.get("trade_count", 0) or 0)
    total_profit = float(metrics.get("total_profit_krw", 0) or 0)

    uptrend_r2 = compute_uptrend_r2(equity_series)

    min_trades = int(getattr(config, "min_trades", 0) or 0)
    mdd_cap = float(getattr(config, "mdd_cap", float("inf")))

    # 하드 게이트 재사용 — 졸업/우승 판정과 동일한 기준.
    hard = compute_fitness(metrics, equity_series, config)

    # --- 제약별 근접도(closeness) 항 [0,1] ---
    if min_trades > 0:
        trades_term = _clamp01(trade_count / min_trades)
    else:
        trades_term = 1.0

    if mdd <= mdd_cap:
        mdd_term = 1.0
    elif mdd <= 0.0:
        mdd_term = 1.0  # mdd≈0은 cap 이하로 본다 (0 나눗셈 회피).
    else:
        mdd_term = _clamp01(mdd_cap / mdd)

    # profit_term: 요구 자본(seed/required) 규모로 손익을 정규화. config에 없으면
    #   안전한 기본 스케일(백만원)로 폴백 — 부호 방향(손실<0.5<이익)만 보존하면 된다.
    profit_scale = float(
        getattr(config, "profit_scale_krw", None)
        or getattr(config, "seed_capital_krw", None)
        or 1_000_000.0
    )
    profit_term = _profit_term(total_profit, profit_scale)

    uptrend_term = _clamp01(uptrend_r2)

    if hard.gate_passed:
        composite = hard.score  # calmar x uptrend_r2 x 1
        graded = 1.0 + composite
        gate_distance = "ok (gate passed)"
    else:
        composite = 0.0
        terms = (trades_term, mdd_term, profit_term, uptrend_term)
        graded = sum(terms) / len(terms)
        gate_distance = _gate_distance_text(
            trade_count, min_trades, mdd, mdd_cap, total_profit
        )

    return GradedResult(
        graded=graded,
        gate_passed=hard.gate_passed,
        composite=composite,
        trades_term=trades_term,
        mdd_term=mdd_term,
        profit_term=profit_term,
        uptrend_term=uptrend_term,
        gate_distance=gate_distance,
        cagr=cagr,
        mdd=mdd,
        trade_count=trade_count,
        total_profit=total_profit,
        uptrend_r2=uptrend_r2,
    )


def _gate_distance_text(
    trade_count: int, min_trades: int, mdd: float, mdd_cap: float, total_profit: float
) -> str:
    """게이트 실패의 '얼마나 멀리 떨어졌는지'를 사람이 읽을 수 있게 요약한다.

    예: "거래 5/30건; MDD 48 is 1.9x cap(25); profit negative".
    피드백/로그에서 다음 세대가 무엇을 좁혀야 하는지 가늠하는 데 쓴다.
    """
    parts = []
    if min_trades > 0 and trade_count < min_trades:
        parts.append(f"거래 {trade_count}/{min_trades}건(부족)")
    if mdd_cap not in (float("inf"),) and mdd > mdd_cap and mdd_cap > 0:
        parts.append(f"MDD {mdd:.4g} is {mdd / mdd_cap:.2g}x cap({mdd_cap:.4g})")
    if total_profit < 0:
        parts.append("profit negative")
    elif total_profit == 0:
        parts.append("profit breakeven(0)")
    if not parts:
        return "gate failed"
    return "; ".join(parts)


def load_equity_series_from_csv(csv_path: str) -> list:
    """백테스트 결과 CSV에서 누적수익 컬럼(`수익금합계`)을 거래 순서대로 읽는다.

    인코딩은 utf-8-sig (BOM 포함 가능). 컬럼이 없으면 KeyError.
    """
    equity = []
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "수익금합계" not in reader.fieldnames:
            raise KeyError(f"CSV에 '수익금합계' 컬럼이 없습니다: {csv_path}")
        for row in reader:
            raw = row.get("수익금합계", "")
            if raw is None or str(raw).strip() == "":
                continue
            equity.append(float(raw))
    return equity
