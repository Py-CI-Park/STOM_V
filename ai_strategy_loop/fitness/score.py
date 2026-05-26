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
      - 게이트 실패: [0, 1) 범위. profit_term * mean(나머지 4항 근접도) *
        undertrade_factor. profit을 곱셈 게이트로 분리해 손실 전략이 낮은 MDD만으로
        수익 전략을 이기지 못하게 하고, undertrade_factor((trade/min)**2)로 거래가
        min_trades 미달인 전략(거래 붕괴)을 강하게 억제한다. 통과에 가까울수록
        (특히 수익이고 거래수가 충분할수록) 1에 근접한다.

    구성요소(게이트 실패 시 의미를 가진다):
      trades_term    : min(trade_count / min_trades, 1.0)
      mdd_term       : 1.0 if mdd<=cap else clamp(cap / mdd, 0, 1)
      profit_term    : 손익 척도(부호보존 log 압축+로지스틱) — 손실<0 → ~0(적자
                       범위 전체에서 변별 유지), 손익분기 → 0.5, 이익>0 → ~1
      uptrend_term   : uptrend_r2 (이미 [0,1])
      overtrade_term : 과매매 감점. 거래수<=softcap이면 1.0, 초과하면
                       clamp(softcap / trade_count, 0, 1) (과매매일수록 작아짐).
                       softcap<=0이면 항상 1.0(페널티 비활성).
      composite      : 게이트 통과 시의 calmar x uptrend_r2 (FitnessResult.score 와 동일)
      gate_distance  : 게이트 실패 사유를 사람이 읽을 수 있게 요약한 문자열.
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
    # 과매매 감점 항 [0,1]. 기본 1.0(페널티 없음) — 직접 GradedResult를 만드는
    #   테스트 더블 등 호출부 하위호환을 위해 기본값을 둔다(맨 끝 배치).
    #   실제 compute_graded_fitness는 항상 명시적으로 채운다.
    overtrade_term: float = 1.0
    # P7 — 이 graded를 산출한 우승/선택 목표('risk_adjusted'|'profit'|'balanced').
    #   로그·page_data에서 어떤 공식으로 통과 분기를 매겼는지 드러낸다. 기본
    #   'risk_adjusted'로 두어 기존 호출부 하위호환을 보장한다(맨 끝 배치).
    objective: str = "risk_adjusted"


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


def _undertrade_factor(trade_count: int, min_trades: int) -> float:
    """거래수가 min_trades 미달일 때 graded에 곱하는 [0,1] 페널티 계수.

    overtrade_term(과다 감점)과 대칭으로, '과소 거래(2~26건 같은 붕괴)'를 강하게
    억제한다. P8 정체 원인: 루프가 MDD를 낮추려 거래를 극단적으로 줄여도
    profit_term/mdd_term이 높아 graded가 유지됐다. trades_term(선형, mean의 1/4)
    만으로는 약해서, 이 계수를 graded에 **추가로 곱해** 과소거래를 dominant하게
    누른다.

    공식: 거래>=min_trades면 1.0(무벌점). 미만이면 (trade_count/min_trades)**2 —
      제곱이라 2건 같은 극단(min 30 기준 (2/30)**2≈0.0044)을 선형(0.067)보다 훨씬
      강하게 억제한다. 거래가 min에 가까울수록 1.0에 수렴한다.

    min_trades<=0이면 페널티 비활성(1.0) — overtrade_softcap<=0과 동일한 컨벤션.
    """
    if min_trades <= 0:
        return 1.0
    if trade_count >= min_trades:
        return 1.0
    ratio = trade_count / min_trades
    return _clamp01(ratio * ratio)


def _profit_term(total_profit: float, scale: float) -> float:
    """총손익을 [0,1] 단조 증가 척도로 변환한다 (부호보존 log 압축 + 로지스틱).

    - 큰 손실      → ~0 (단, 적자 범위 전체에서 변별 가능 — 포화 완화)
    - 손익분기(0) → 0.5  (logistic(0) = 0.5)
    - 큰 이익      → ~1

    왜 log 압축인가:
      기존 선형 z = profit/scale 로지스틱은 scale≈1백만원이라 −99M·−12.4억 모두
      z≪0으로 0에 포화돼, 큰 적자끼리(−12억 vs −1억)를 전혀 구별하지 못했다
      (적자 영역 그래디언트 결함). 부호보존 log로 z를 압축하면
        z = sign(p)·log1p(|p|/scale)
      손익이 자릿수(orders of magnitude)로 멀어질수록 천천히 변해, 광대역
      적자(−12억~0)에서도 단조 변별이 살아난다. log1p는 |p|≪scale에서 거의
      선형(소액 손익의 의미 보존)이고, |p|≫scale에서 로그로 압축된다.

    scale은 손익을 정규화하는 기준 규모(원). 0/음수면 안전한 기본값으로 폴백한다.
    단조 증가이며 모든 입력에서 [0,1]을 벗어나지 않는다(흑자>0.5>적자 유지).
    """
    import math  # noqa: PLC0415

    if scale <= 0.0:
        scale = 1.0
    # 부호보존 log 압축: |p|/scale을 log1p로 눌러 광대역 적자/흑자를 변별.
    #   p=0이면 z=0 → 로지스틱(0)=0.5(손익분기 보존).
    sign = math.copysign(1.0, total_profit) if total_profit != 0.0 else 0.0
    z = sign * math.log1p(abs(total_profit) / scale)
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

      게이트 통과: graded = 1.0 + term(objective)   (term≥0 → graded≥1.0)
                   → 어떤 실패 전략(graded < 1.0)보다도 항상 위에 랭크된다.
                   term은 config.winner_objective로 결정한다(_gate_passed_term):
                     'risk_adjusted'(기본) = composite(calmar×R²)  ← 하위호환,
                     'profit'             = profit_term(정규화 수익 로지스틱),
                     'balanced'           = composite·(1-w)+profit_term·w (w=profit_weight).
      게이트 실패: base = mean(trades_term, mdd_term, uptrend_term, overtrade_term)
                   graded = profit_term * base * undertrade_factor
                   → [0,1) 범위. profit을 '곱셈 게이트'로 분리해, 손실 전략이
                     낮은 MDD만으로 수익 전략을 이기지 못하게 하고,
                     undertrade_factor((trade/min)**2)로 거래수<min_trades(거래 붕괴)
                     를 추가 억제한다. (수익+거래충분이면 base 보존, 손실/과소거래면
                     강하게 눌린다.)

    base의 combiner로 product가 아닌 mean을 쓰는 이유: 한 제약이 0이어도
    (예: uptrend_r2=0) 나머지 근접도가 살아남아 그래디언트가 평평해지지 않는다
    (product면 항 하나가 0이면 전체가 0이 되어 변별이 사라진다). profit만은
    수익/손실 방향이 결정적이라 평균에 섞지 않고 곱셈으로 분리한다.
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

    # overtrade_term: 과매매(거래수 과다) 감점. softcap 이하면 1.0(무벌점),
    #   초과하면 softcap/trade_count로 부드럽게 감점한다(거래가 많을수록 작아짐).
    #   softcap<=0이면 페널티 비활성(기존 동작과 동일).
    softcap = int(getattr(config, "overtrade_softcap", 0) or 0)
    if softcap <= 0 or trade_count <= softcap:
        overtrade_term = 1.0
    else:
        overtrade_term = _clamp01(softcap / trade_count)

    # P7 — 우승/선택 목표. gate-passed 분기의 그래디언트만 바꾼다(실패 분기 불변).
    #   기본 'risk_adjusted'면 기존 1.0+composite 그대로(하위호환).
    objective = str(getattr(config, "winner_objective", "risk_adjusted") or "risk_adjusted")

    if hard.gate_passed:
        composite = hard.score  # calmar x uptrend_r2 x 1
        graded = 1.0 + _gate_passed_term(objective, composite, profit_term, config)
        gate_distance = "ok (gate passed)"
    else:
        composite = 0.0
        # profit을 '곱셈 게이트'로 분리한다(수익 신호가 평균에 묻히는 문제 해결).
        #   base = profit 제외 4항 평균(거래수/MDD/우상향/과매매 근접도).
        #   graded = profit_term * base * undertrade_factor 로 결합한다.
        #   - 손실(profit_term<0.5)이면 graded가 강하게 눌려, 낮은 MDD만으로는
        #     수익 전략을 이길 수 없다.
        #   - 수익(profit_term>0.5)이면 base가 대체로 보존된다.
        #   - undertrade_factor: 거래<min_trades면 (trade/min)**2로 추가 감점한다.
        #     P8 정체(거래 2~26건 붕괴)를 억제 — trades_term이 mean의 1/4라 약했던
        #     과소거래 신호를 곱셈으로 dominant하게 만든다(overtrade_term과 대칭).
        #   세 항 모두 [0,1]이므로 graded ∈ [0,1) 단조성 유지.
        base_terms = (trades_term, mdd_term, uptrend_term, overtrade_term)
        base = sum(base_terms) / len(base_terms)
        undertrade_factor = _undertrade_factor(trade_count, min_trades)
        graded = profit_term * base * undertrade_factor
        gate_distance = _gate_distance_text(
            trade_count, min_trades, mdd, mdd_cap, total_profit, softcap
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
        overtrade_term=overtrade_term,
        objective=objective,
    )


def _gate_passed_term(objective: str, composite: float, profit_term: float, config) -> float:
    """게이트 통과 전략의 graded 가산항(=graded-1.0)을 목표별로 만든다.

    - 'risk_adjusted'(기본): composite(Calmar×R²) 그대로 — 위험조정 우수일수록 ↑.
    - 'profit'             : profit_term(정규화 수익 로지스틱) — 수익 클수록 ↑.
    - 'balanced'           : composite×(1-w) + profit_term×w 블렌드(w=profit_weight).

    어느 목표든 비음수라 graded≥1.0이 보장돼 "통과>실패" 불변식이 유지된다
    (composite≥0, profit_term∈[0,1]). 알 수 없는 값은 risk_adjusted로 폴백한다.
    """
    if objective == "profit":
        return profit_term
    if objective == "balanced":
        w = float(getattr(config, "profit_weight", 0.5) or 0.0)
        w = _clamp01(w)
        return composite * (1.0 - w) + profit_term * w
    # 'risk_adjusted' 및 알 수 없는 값 폴백.
    return composite


def _gate_distance_text(
    trade_count: int,
    min_trades: int,
    mdd: float,
    mdd_cap: float,
    total_profit: float,
    overtrade_softcap: int = 0,
) -> str:
    """게이트 실패의 '얼마나 멀리 떨어졌는지'를 사람이 읽을 수 있게 요약한다.

    예: "거래 5/30건; MDD 48 is 1.9x cap(25); profit negative".
    피드백/로그에서 다음 세대가 무엇을 좁혀야 하는지 가늠하는 데 쓴다.
    overtrade_softcap>0이고 거래수가 이를 초과하면 과매매 단서도 덧붙인다.
    """
    parts = []
    if min_trades > 0 and trade_count < min_trades:
        parts.append(f"거래 {trade_count}/{min_trades}건(부족)")
    if overtrade_softcap > 0 and trade_count > overtrade_softcap:
        parts.append(f"거래 {trade_count} 과다(>softcap {overtrade_softcap})")
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
