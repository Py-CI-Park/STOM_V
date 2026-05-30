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
    # 일평균거래횟수(거래수/거래일수). 빈도 게이트의 주 기준값을 노출한다. 기본 0.0
    #   (맨 끝 배치)이라 직접 FitnessResult를 만드는 호출부/테스트 더블도 그대로
    #   동작한다(하위호환). compute_fitness는 metrics에서 산출해 채운다.
    daily_avg_trades: float = 0.0


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
    # 일평균거래횟수(거래수/거래일수). 빈도 게이트의 주 기준값. 기본 0.0(맨 끝
    #   배치)이라 기존 호출부/테스트 더블 하위호환을 보장한다.
    daily_avg_trades: float = 0.0
    # P7 — 이 graded를 산출한 우승/선택 목표('risk_adjusted'|'profit'|'balanced').
    #   로그·page_data에서 어떤 공식으로 통과 분기를 매겼는지 드러낸다. 기본
    #   'risk_adjusted'로 두어 기존 호출부 하위호환을 보장한다(맨 끝 배치).
    objective: str = "risk_adjusted"
    # 청산 품질(exit-quality) 항 [0,1] + 원시 구성요소. give-back/payoff 부검 신호를
    #   게이트-실패 분기의 선택 그래디언트에 가산한다. metrics에 청산품질 키가 없거나
    #   exit_quality_enabled=False면 무영향(이 필드는 기본값으로 채워져 하위호환 보장).
    #   기본값(맨 끝 배치)이라 직접 GradedResult를 만드는 테스트 더블도 그대로 동작한다.
    exit_quality_term: float = 1.0
    payoff_ratio: float = 0.0
    give_back_rate: float = 0.0
    # 다종목 분산(dispersion) 항 [0,1] + 원시 동시보유 종목 수. 보고서 우수전략의
    #   고빈도는 다종목 분산 진입에서 오므로, 동시보유(max_hold_count)가 클수록
    #   게이트-실패 분기의 선택 그래디언트를 끌어올린다(exit_quality_term과 동일 방식).
    #   metrics에 max_hold_count가 없거나 dispersion_enabled=False면 무영향(이 필드는
    #   기본값으로 채워져 하위호환 보장). 기본값(맨 끝 배치)이라 직접 GradedResult를
    #   만드는 테스트 더블도 그대로 동작한다.
    dispersion_term: float = 1.0
    max_hold_count: float = 0.0


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


# 일평균거래횟수가 metrics에 있는지 판정하는 sentinel. None이면 '키 없음'
#   (구 데이터/테스트) → 절대 거래수(min_trades) 게이트로 폴백한다.
def _resolve_daily_avg_trades(metrics: dict) -> Optional[float]:
    """metrics에서 일평균거래횟수를 꺼낸다(없으면 None).

    None은 '루프가 아직 일평균을 산출하지 않은 구 데이터/테스트'를 뜻하며,
    호출부는 이때 절대 거래수(min_trades) 게이트로 폴백한다(하위호환).
    값이 있으면(0.0 포함) float로 반환한다.
    """
    raw = metrics.get("daily_avg_trades", None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _frequency_gate_failed(
    daily_avg_trades: Optional[float],
    min_daily_trades: float,
    trade_count: int,
    min_trades: int,
) -> Optional[str]:
    """거래 빈도 게이트 판정 — 실패면 사유 문자열, 통과면 None.

    주 기준은 **일평균거래횟수**다(daily_avg_trades >= min_daily_trades). 일일
    시스템 트레이딩 기준 2~3일에 1회 이상(>=0.5)이 정상 빈도이며, 절대 거래수
    (min_trades)는 1년 기준이면 너무 희소해 잘못된 수렴을 유발했다.

    하위호환: daily_avg_trades가 None이면(구 데이터/테스트 — 일평균 미산출)
    기존 절대 거래수 게이트(trade_count >= min_trades)로 폴백한다.
    """
    if daily_avg_trades is None:
        # 폴백: 절대 거래수 게이트(기존 동작).
        if trade_count < min_trades:
            return f"trade_count {trade_count} < min_trades {min_trades}"
        return None
    # 주 경로: 일평균거래횟수 게이트.
    if daily_avg_trades < min_daily_trades:
        return (
            f"daily_avg_trades {daily_avg_trades:.4g} "
            f"< min_daily_trades {min_daily_trades:.4g}"
        )
    return None


def _tpi_gate_failed(metrics: dict, config) -> Optional[str]:
    """매매성능지수(tpi) 게이트 판정 — 실패면 사유 문자열, 통과/무영향이면 None.

    옵션·토글·하위호환이다:
      - config.tpi_gate_enabled가 False(기본)면 항상 None(게이트 불변).
      - enabled여도 metrics에 tpi 키가 없으면 None(구 데이터/cold 경로 하위호환).
      - enabled이고 tpi가 있으면 tpi >= tpi_gate를 요구한다. 미달이면 사유 반환.

    우수전략 보고서 기준 winner 판정의 핵심(tpi>=1.25)을 하드게이트에 AND로 더한다.
    빈도·MDD·흑자 검사 다음의 마지막 AND 절로만 쓰여, OFF에서는 기존 동작과 같다.
    """
    if not bool(getattr(config, "tpi_gate_enabled", False)):
        return None
    raw = metrics.get("tpi", None)
    if raw is None:
        return None  # 하위호환: tpi 키 없으면 무영향.
    try:
        tpi = float(raw)
    except (TypeError, ValueError):
        return None
    tpi_gate = float(getattr(config, "tpi_gate", 0.0) or 0.0)
    if tpi < tpi_gate:
        return f"tpi {tpi:.4g} < tpi_gate {tpi_gate:.4g}"
    return None


def compute_fitness(metrics: dict, equity_series: Sequence[float], config) -> FitnessResult:
    """metrics dict + 누적수익 곡선 + config로 복합 적합도를 계산한다.

    composite = calmar x uptrend_r2 x gate
    gate = 1 if (빈도 게이트 통과 AND mdd <= mdd_cap AND total_profit > 0
                 [AND tpi >= tpi_gate, tpi_gate_enabled일 때만]) else 0
      - 빈도 게이트(주 기준): daily_avg_trades >= min_daily_trades.
      - daily_avg_trades가 metrics에 없으면 trade_count >= min_trades로 폴백(하위호환).
      - tpi 게이트(옵션): config.tpi_gate_enabled=True이고 metrics에 tpi가 있을 때만
        tpi >= tpi_gate를 마지막 AND 절로 요구한다. 기본 OFF면 게이트 불변(하위호환).
    """
    cagr = float(metrics.get("cagr", 0.0) or 0.0)
    mdd = float(metrics.get("mdd_pct", 0.0) or 0.0)
    trade_count = int(metrics.get("trade_count", 0) or 0)
    total_profit = float(metrics.get("total_profit_krw", 0) or 0)
    daily_avg_trades = _resolve_daily_avg_trades(metrics)

    calmar = compute_calmar(cagr, mdd)
    uptrend_r2 = compute_uptrend_r2(equity_series)

    # gate 판정 (실패 사유를 첫 위반 기준으로 기록).
    min_trades = int(getattr(config, "min_trades", 0))
    min_daily_trades = float(getattr(config, "min_daily_trades", 0.0) or 0.0)
    mdd_cap = float(getattr(config, "mdd_cap", float("inf")))

    reason = "ok"
    gate_passed = True
    freq_fail = _frequency_gate_failed(
        daily_avg_trades, min_daily_trades, trade_count, min_trades
    )
    if freq_fail is not None:
        gate_passed = False
        reason = freq_fail
    elif abs(mdd) > mdd_cap:
        gate_passed = False
        reason = f"mdd {abs(mdd):.4g} > mdd_cap {mdd_cap:.4g}"
    elif total_profit <= 0.0:
        gate_passed = False
        reason = f"total_profit {total_profit:.4g} <= 0"
    else:
        # tpi 게이트(옵션·토글·하위호환). enabled=False(기본)거나 metrics에 tpi가
        #   없으면 None → 게이트 불변. 마지막 AND 절이라 OFF에서 byte-동일하다.
        tpi_fail = _tpi_gate_failed(metrics, config)
        if tpi_fail is not None:
            gate_passed = False
            reason = tpi_fail

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
        daily_avg_trades=(daily_avg_trades if daily_avg_trades is not None else 0.0),
    )


def _clamp01(x: float) -> float:
    """x를 [0,1] 구간으로 자른다."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _undertrade_factor(trade_count: int, min_trades: int) -> float:
    """거래수가 min_trades 미달일 때 graded에 곱하는 [0,1] 페널티 계수(폴백 경로).

    overtrade_term(과다 감점)과 대칭으로, '과소 거래(2~26건 같은 붕괴)'를 강하게
    억제한다. P8 정체 원인: 루프가 MDD를 낮추려 거래를 극단적으로 줄여도
    profit_term/mdd_term이 높아 graded가 유지됐다. trades_term(선형, mean의 1/4)
    만으로는 약해서, 이 계수를 graded에 **추가로 곱해** 과소거래를 dominant하게
    누른다.

    공식: 거래>=min_trades면 1.0(무벌점). 미만이면 (trade_count/min_trades)**2 —
      제곱이라 2건 같은 극단(min 30 기준 (2/30)**2≈0.0044)을 선형(0.067)보다 훨씬
      강하게 억제한다. 거래가 min에 가까울수록 1.0에 수렴한다.

    min_trades<=0이면 페널티 비활성(1.0) — overtrade_softcap<=0과 동일한 컨벤션.

    이 함수는 daily_avg_trades가 없는 폴백 경로(구 데이터/테스트)에서만 쓰인다.
    일평균이 있으면 _undertrade_factor_daily(일평균 기준)를 쓴다.
    """
    if min_trades <= 0:
        return 1.0
    if trade_count >= min_trades:
        return 1.0
    ratio = trade_count / min_trades
    return _clamp01(ratio * ratio)


def _undertrade_factor_daily(daily_avg_trades: float, min_daily_trades: float) -> float:
    """일평균거래횟수가 min_daily_trades 미달일 때 graded에 곱하는 [0,1] 페널티 계수.

    _undertrade_factor의 일평균 버전이다. 빈도 게이트의 주 기준(일평균)에 맞춰
    과소 빈도 전략(일평균<하한)을 (비율)**2 로 강하게 억제한다.

    공식: 일평균>=min_daily_trades면 1.0(무벌점). 미만이면
      (daily_avg_trades/min_daily_trades)**2. 하한에 가까울수록 1.0에 수렴한다.

    min_daily_trades<=0이면 페널티 비활성(1.0) — min_trades<=0과 동일한 컨벤션.
    """
    if min_daily_trades <= 0.0:
        return 1.0
    if daily_avg_trades >= min_daily_trades:
        return 1.0
    ratio = daily_avg_trades / min_daily_trades
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


def _exit_quality_term(
    payoff_ratio: Optional[float],
    give_back_rate: Optional[float],
    payoff_target: float,
    give_back_weight: float,
) -> Optional[float]:
    """청산 품질 신호(payoff_ratio/give_back_rate)를 [0,1] 단일 항으로 합친다.

    부검 근거: 손실의 대부분이 give-back이고 payoff ratio 붕괴가 적자 원인이라,
    청산이 좋을수록(payoff↑, give-back↓) 1에 근접하는 가산 신호를 만든다.

    - payoff_comp  = clamp01(payoff_ratio / payoff_target)  (payoff_ratio 있을 때)
    - giveback_comp= clamp01(1.0 - give_back_rate)          (give_back_rate 있을 때)
    - 둘 다 있으면: payoff_comp*(1-w) + giveback_comp*w  (w=give_back_weight)
    - payoff만 있으면: payoff_comp
    - 둘 다 없으면: None (다운스트림에서 무영향 처리).

    payoff_target<=0이면 안전한 기본(1.1)으로 폴백한다.
    """
    if payoff_ratio is None and give_back_rate is None:
        return None
    if payoff_target <= 0.0:
        payoff_target = 1.1
    w = _clamp01(give_back_weight)

    payoff_comp = None
    if payoff_ratio is not None:
        payoff_comp = _clamp01(payoff_ratio / payoff_target)
    giveback_comp = None
    if give_back_rate is not None:
        giveback_comp = _clamp01(1.0 - give_back_rate)

    if payoff_comp is not None and giveback_comp is not None:
        return payoff_comp * (1.0 - w) + giveback_comp * w
    if payoff_comp is not None:
        return payoff_comp
    # payoff 없이 give-back만 있는 경우(이론상): give-back 신호만 사용.
    return giveback_comp


def _dispersion_term(
    max_hold_count: Optional[float],
    min_hold_symbols: float,
) -> Optional[float]:
    """동시보유 종목 수(max_hold_count)를 [0,1] 분산 보상 항으로 변환한다.

    데이터 근거: 보고서 우수전략의 고빈도(일평균10~23)는 한 종목 다발 진입이
    아니라 여러 종목에 1~2회씩 분산된 진입에서 온다(흑자 gen0이 24종목에 1회씩
    완전 분산). 동시보유 종목 수가 보고서 하한(6~12)에 가까울수록 1에 근접하는
    가산 신호를 만들어, 게이트-실패 분기의 선택 그래디언트가 다종목 분산을
    보상하게 한다.

    공식: clamp01(max_hold_count / min_hold_symbols). min_hold_symbols 이상이면
      1.0에 포화한다(6 이상이면 충분히 분산된 것으로 본다).

    - max_hold_count가 None이면(metrics에 키 없음) None 반환 → 다운스트림 무영향.
    - min_hold_symbols<=0이면 안전한 기본(6.0)으로 폴백한다.

    NOTE: max_hold_count는 '최대 동시보유(peak concurrency)'로 '서로 다른 종목에
    걸쳐 분산됐는지'의 1차 근사(proxy)이며 soft 신호다. 정밀 분산지표(distinct-symbol
    count per day 등)는 향후 per-trade CSV 파싱이 준비될 때 도입한다.
    """
    if max_hold_count is None:
        return None
    if min_hold_symbols <= 0.0:
        min_hold_symbols = 6.0
    return _clamp01(max_hold_count / min_hold_symbols)


def compute_graded_fitness(
    metrics: dict,
    equity_series: Sequence[float],
    config,
    *,
    dispersion_enabled: bool = False,
    min_hold_symbols: float = 6.0,
) -> GradedResult:
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
    # 동시보유 종목 수(다종목 분산 신호). metrics에 키가 없으면 None → 분산 보상
    #   무영향(하위호환). dispersion_enabled=True이고 값이 있을 때만 게이트-실패
    #   분기에 가산한다.
    max_hold_count_raw = metrics.get("max_hold_count", None)
    daily_avg_trades_raw = _resolve_daily_avg_trades(metrics)
    # graded/페널티 노출용 일평균(None이면 0.0). 게이트 분기 판정은 raw(None)로 한다.
    daily_avg_trades = daily_avg_trades_raw if daily_avg_trades_raw is not None else 0.0

    uptrend_r2 = compute_uptrend_r2(equity_series)

    min_trades = int(getattr(config, "min_trades", 0) or 0)
    min_daily_trades = float(getattr(config, "min_daily_trades", 0.0) or 0.0)
    mdd_cap = float(getattr(config, "mdd_cap", float("inf")))

    # 하드 게이트 재사용 — 졸업/우승 판정과 동일한 기준.
    hard = compute_fitness(metrics, equity_series, config)

    # --- 제약별 근접도(closeness) 항 [0,1] ---
    # 빈도 근접도(trades_term): 주 기준은 **일평균거래횟수**(daily/min_daily).
    #   일평균이 metrics에 있으면 그 기준으로, 없으면(구 데이터/테스트) 절대 거래수
    #   (trade_count/min_trades)로 폴백한다(하위호환).
    if daily_avg_trades_raw is not None:
        if min_daily_trades > 0.0:
            trades_term = _clamp01(daily_avg_trades / min_daily_trades)
        else:
            trades_term = 1.0
    elif min_trades > 0:
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

    # 청산 품질(exit-quality) 소프트 항. metrics에 payoff_ratio/give_back_rate가
    #   주입돼 있으면(loop._score_outcome이 per-trade CSV에서 산출) give-back/payoff
    #   부검 신호를 게이트-실패 분기의 선택 그래디언트에 가산한다. 키가 없거나
    #   exit_quality_enabled=False면 term=None → 기존 4항 평균 그대로(하위호환).
    exit_quality_enabled = bool(getattr(config, "exit_quality_enabled", True))
    payoff_target = float(getattr(config, "payoff_target", 1.1) or 1.1)
    give_back_weight = float(getattr(config, "give_back_weight", 0.5) or 0.0)
    payoff_ratio_raw = metrics.get("payoff_ratio", None)
    give_back_rate_raw = metrics.get("give_back_rate", None)
    payoff_ratio_val = None
    give_back_rate_val = None
    if exit_quality_enabled:
        if payoff_ratio_raw is not None:
            try:
                payoff_ratio_val = float(payoff_ratio_raw)
            except (TypeError, ValueError):
                payoff_ratio_val = None
        if give_back_rate_raw is not None:
            try:
                give_back_rate_val = float(give_back_rate_raw)
            except (TypeError, ValueError):
                give_back_rate_val = None
    exit_quality_term = _exit_quality_term(
        payoff_ratio_val, give_back_rate_val, payoff_target, give_back_weight
    )

    # 다종목 분산(dispersion) 소프트 항. dispersion_enabled=True이고 metrics에
    #   max_hold_count가 있을 때만 동시보유(max_hold_count/min_hold_symbols) 보상을
    #   산출한다. OFF거나 키가 없으면 term=None → 기존 base 평균 그대로(하위호환,
    #   graded byte-동일). exit_quality_term과 완전히 동일한 방식이다.
    max_hold_count_val = None
    if dispersion_enabled and max_hold_count_raw is not None:
        try:
            max_hold_count_val = float(max_hold_count_raw)
        except (TypeError, ValueError):
            max_hold_count_val = None
    dispersion_term = _dispersion_term(max_hold_count_val, min_hold_symbols)

    # P7 — 우승/선택 목표. gate-passed 분기의 그래디언트만 바꾼다(실패 분기 불변).
    #   기본 'risk_adjusted'면 기존 1.0+composite 그대로(하위호환).
    objective = str(getattr(config, "winner_objective", "risk_adjusted") or "risk_adjusted")

    if hard.gate_passed:
        composite = hard.score  # calmar x uptrend_r2 x 1
        if objective in ("multi", "uptrend"):
            # 다목적('multi') 및 우상향('uptrend')은 _gate_passed_term에 추가 키워드가
            #   필요하다. 'multi'는 calmar/uptrend_r2/daily_avg_trades/payoff 4항을 모두
            #   쓰고, 'uptrend'는 uptrend_r2만 쓴다(나머지는 _gate_passed_term이 무시).
            #   calmar/uptrend_r2/daily_avg_trades는 이미 함수 내 산출값을 쓰고,
            #   payoff_ratio는 metrics에서 직접 꺼낸다(없으면 None → payoff 항 제외).
            #   'uptrend'에서도 payoff_for_multi를 계산해 넘기지만 반환에 안 쓰여 무해하다.
            #   그 외 objective(risk_adjusted/profit/balanced)는 이 값들을 넘기지 않으므로
            #   기존 호출과 byte-동일하다(하위호환).
            # NOTE: 다목적 payoff 항은 exit_quality_enabled 토글과 독립적이다 —
            #   위 payoff_ratio_val은 청산품질 기능 게이트(enabled=False면 None)이지만,
            #   여기서는 metrics의 raw payoff를 직접 써서 토글과 무관하게 평가한다(의도적).
            payoff_for_multi = None
            payoff_raw = metrics.get("payoff_ratio", None)
            if payoff_raw is not None:
                try:
                    payoff_for_multi = float(payoff_raw)
                except (TypeError, ValueError):
                    payoff_for_multi = None
            graded = 1.0 + _gate_passed_term(
                objective, composite, profit_term, config,
                calmar=hard.calmar,
                uptrend_r2=uptrend_r2,
                daily_avg_trades=daily_avg_trades,
                payoff_ratio=payoff_for_multi,
            )
        else:
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
        #   - undertrade_factor: 빈도<하한이면 (비율)**2로 추가 감점한다(주 기준은
        #     일평균: (daily/min_daily)**2). 일평균이 없으면(구 데이터/테스트) 절대
        #     거래수((trade/min)**2)로 폴백한다(하위호환). P8 정체(거래 붕괴)를 억제 —
        #     trades_term이 mean의 1/4라 약했던 과소거래 신호를 곱셈으로 dominant하게
        #     만든다(overtrade_term과 대칭).
        #   세 항 모두 [0,1]이므로 graded ∈ [0,1) 단조성 유지.
        # 청산 품질 항이 있으면 base 평균에 5번째 항으로 가산한다(부검 신호 선택압력).
        #   None이면(키 없음/비활성) 기존 4항 평균 그대로 — 하위호환.
        # 분산 항(dispersion_term)도 동일 방식으로, 있으면 base 평균에 추가 항으로
        #   가산한다(다종목 분산 선택압력). None이면(OFF/키 없음) 무영향(하위호환).
        base_terms = (trades_term, mdd_term, uptrend_term, overtrade_term)
        if exit_quality_term is not None:
            base_terms = base_terms + (exit_quality_term,)
        if dispersion_term is not None:
            base_terms = base_terms + (dispersion_term,)
        base = sum(base_terms) / len(base_terms)
        if daily_avg_trades_raw is not None:
            undertrade_factor = _undertrade_factor_daily(daily_avg_trades, min_daily_trades)
        else:
            undertrade_factor = _undertrade_factor(trade_count, min_trades)
        graded = profit_term * base * undertrade_factor
        gate_distance = _gate_distance_text(
            trade_count, min_trades, mdd, mdd_cap, total_profit, softcap,
            daily_avg_trades=daily_avg_trades_raw, min_daily_trades=min_daily_trades,
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
        daily_avg_trades=daily_avg_trades,
        exit_quality_term=(exit_quality_term if exit_quality_term is not None else 1.0),
        payoff_ratio=(payoff_ratio_val if payoff_ratio_val is not None else 0.0),
        give_back_rate=(give_back_rate_val if give_back_rate_val is not None else 0.0),
        dispersion_term=(dispersion_term if dispersion_term is not None else 1.0),
        max_hold_count=(max_hold_count_val if max_hold_count_val is not None else 0.0),
    )


def _multi_objective_term(
    calmar: Optional[float],
    uptrend_r2: Optional[float],
    daily_avg_trades: Optional[float],
    payoff_ratio: Optional[float],
    config,
) -> float:
    """다목적(winner_objective='multi') 가산항 — calmar·R²·빈도·payoff의 [0,1] 동일가중 평균.

    4레버 ①: '고빈도이면서 위험조정 좋은' 게이트통과 세대를 winner/refine 방향으로
    우대한다. profit 단일 obj가 시드만 뽑아 다양성이 죽는 문제를 4항 정규화 결합으로
    푼다. 단순·동일가중이다.

    각 항을 config의 정규화 상수로 [0,1]로 누른 뒤 평균한다:
      - calmar 항      : clamp01(calmar / multi_calmar_norm)
      - r² 항          : clamp01(uptrend_r2)             (이미 [0,1])
      - 빈도 항        : clamp01(daily_avg_trades / multi_daily_target)
      - payoff 항      : clamp01((payoff_ratio-1.0) / (multi_payoff_norm-1.0))

    None-제외 평균(_exit_quality_term의 None-제외 패턴 모방): 어떤 항의 원시 값이 None이면
    (그 신호를 못 받았다는 뜻 — 예: per-trade CSV 없어 payoff None) 그 항은 평균에서 제외한다.
    유효한 항이 하나도 없으면 0.0을 돌려 graded=1.0(통과>실패 불변식 유지)으로 둔다.

    반환은 [0,1]이라 graded=1.0+term≥1.0이 보장돼 "통과>실패" 불변식이 유지된다.
    """
    calmar_norm = float(getattr(config, "multi_calmar_norm", 30.0) or 30.0)
    payoff_norm = float(getattr(config, "multi_payoff_norm", 1.3) or 1.3)
    daily_target = float(getattr(config, "multi_daily_target", 10.0) or 10.0)
    if calmar_norm <= 0.0:
        calmar_norm = 30.0
    if daily_target <= 0.0:
        daily_target = 10.0
    # payoff 분모는 (norm-1.0). norm<=1.0이면 분모가 0/음수라 안전한 기본(1.3)으로 폴백.
    if payoff_norm <= 1.0:
        payoff_norm = 1.3

    comps = []
    if calmar is not None:
        comps.append(_clamp01(calmar / calmar_norm))
    if uptrend_r2 is not None:
        comps.append(_clamp01(uptrend_r2))
    if daily_avg_trades is not None:
        comps.append(_clamp01(daily_avg_trades / daily_target))
    if payoff_ratio is not None:
        comps.append(_clamp01((payoff_ratio - 1.0) / (payoff_norm - 1.0)))

    if not comps:
        return 0.0
    return sum(comps) / len(comps)


def _gate_passed_term(
    objective: str,
    composite: float,
    profit_term: float,
    config,
    *,
    calmar: Optional[float] = None,
    uptrend_r2: Optional[float] = None,
    daily_avg_trades: Optional[float] = None,
    payoff_ratio: Optional[float] = None,
) -> float:
    """게이트 통과 전략의 graded 가산항(=graded-1.0)을 목표별로 만든다.

    - 'risk_adjusted'(기본): composite(Calmar×R²) 그대로 — 위험조정 우수일수록 ↑.
    - 'profit'             : profit_term(정규화 수익 로지스틱) — 수익 클수록 ↑.
    - 'balanced'           : composite×(1-w) + profit_term×w 블렌드(w=profit_weight).
    - 'multi'              : calmar·R²·빈도·payoff의 [0,1] 동일가중 평균(_multi_objective_term).
    - 'uptrend'            : composite×R² — 누적수익 곡선의 우상향(평활도, uptrend_r2)에
                            가중. composite(=Calmar×R²)에 R²를 한 번 더 곱해 "장기 우상향"을
                            winner/선택 주 기준으로 삼는다(보고서 우수전략의 정의적 특성).

    'multi'/'uptrend'를 제외한 분기는 calmar/uptrend_r2/daily_avg_trades/payoff_ratio 키워드를
    전혀 보지 않으므로, 그 값들을 넘기지 않는 **기존 호출부는 동작이 완전히 동일**하다
    (하위호환). 'multi'일 때만 그 값들(기본 None은 항 제외)로 다목적 평균을 만들고,
    'uptrend'일 때만 uptrend_r2(기본 None→0.0)를 추가로 곱한다.

    어느 목표든 비음수라 graded≥1.0이 보장돼 "통과>실패" 불변식이 유지된다
    (composite≥0, profit_term∈[0,1], multi term∈[0,1], R²∈[0,1] → composite×R²≥0).
    알 수 없는 값은 risk_adjusted로 폴백한다.
    """
    if objective == "profit":
        return profit_term
    if objective == "balanced":
        w = float(getattr(config, "profit_weight", 0.5) or 0.0)
        w = _clamp01(w)
        return composite * (1.0 - w) + profit_term * w
    if objective == "multi":
        return _multi_objective_term(
            calmar, uptrend_r2, daily_avg_trades, payoff_ratio, config
        )
    if objective == "uptrend":
        # 우상향 추세 강조: composite(calmar×r²)에 r²를 한 번 더 곱해 곡선 평활도(우상향)에 가중.
        #   composite≥0, r²∈[0,1] → 반환≥0이라 graded≥1.0 불변식 유지.
        return composite * _clamp01(uptrend_r2 if uptrend_r2 is not None else 0.0)
    # 'risk_adjusted' 및 알 수 없는 값 폴백.
    return composite


def _gate_distance_text(
    trade_count: int,
    min_trades: int,
    mdd: float,
    mdd_cap: float,
    total_profit: float,
    overtrade_softcap: int = 0,
    *,
    daily_avg_trades: Optional[float] = None,
    min_daily_trades: float = 0.0,
) -> str:
    """게이트 실패의 '얼마나 멀리 떨어졌는지'를 사람이 읽을 수 있게 요약한다.

    예: "일평균 0.3/0.5회(부족); MDD 48 is 1.9x cap(25); profit negative".
    피드백/로그에서 다음 세대가 무엇을 좁혀야 하는지 가늠하는 데 쓴다.
    overtrade_softcap>0이고 거래수가 이를 초과하면 과매매 단서도 덧붙인다.

    빈도 단서: 일평균(daily_avg_trades)이 주어지면 일평균 하한(min_daily_trades)
    미달을 표기한다. 일평균이 없으면(구 데이터/테스트) 절대 거래수 미달로 폴백한다.
    """
    parts = []
    if daily_avg_trades is not None:
        if min_daily_trades > 0.0 and daily_avg_trades < min_daily_trades:
            parts.append(
                f"일평균 {daily_avg_trades:.2g}/{min_daily_trades:.2g}회(부족)"
            )
    elif min_trades > 0 and trade_count < min_trades:
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


def load_exit_quality_from_csv(csv_path: str, mfe_giveback_threshold: float = 1.5) -> dict:
    """per-trade CSV에서 청산 품질(exit-quality) 지표를 읽어 dict로 반환한다.

    부검 근거(1년치 확증): 손실의 70~88%가 give-back이다 — 평가익(MFE)을 2.4~2.9%
    찍고도 청산 로직이 못 잡아 -2.3~-3%로 토해내며 마감한다. 그 결과 payoff ratio
    (평균이익/평균손실)가 1.20→0.61로 붕괴해 적자가 났다. 진입 피처는 승패를
    예측하지 못하고 **청산이 승패를 결정**함이 데이터로 확인됐다. 이 함수는 그
    두 신호(payoff_ratio, give_back_rate)를 per-trade 컬럼에서 직접 산출해
    선택 압력(적합도)과 프롬프트로 환류할 수 있게 한다.

    컬럼:
      - '수익률'  : per-trade 수익률(%). 양수=이익거래, 음수/0=손실거래.
      - 'R_MFE'   : 보유 중 최대유리편의(maximum favorable excursion, %).

    인코딩은 utf-8-sig (BOM 포함 가능), 기존 load_equity_series_from_csv와 동일하게
    csv.DictReader로 컬럼명 직접 접근한다. 빈/결측 행은 skip한다.

    Args:
        csv_path: per-trade 결과 CSV 경로.
        mfe_giveback_threshold: give-back으로 간주할 R_MFE 하한(%). 이 이상 평가익을
            냈는데도 손실(ret<=0)로 마감한 거래를 give-back으로 센다. 기본 1.5%.

    Returns:
        dict. '수익률' 컬럼이 없으면 {} (하위호환 — 다운스트림 무영향).
        파싱 가능한 거래가 0건이어도 {} 반환.
        그 외:
          {'payoff_ratio': float}
            - payoff_ratio = mean(이익 ret) / abs(mean(손실 ret)).
            - 손실거래 0건이면 999.0으로 cap(전부 이익 = 우수).
            - 이익거래 0건이면 0.0.
          (+ 'R_MFE' 컬럼이 있을 때만) {'give_back_rate': float}
            - give_back_rate = (R_MFE>=threshold 이고 ret<=0 인 거래 수)
                               / max(손실거래 수, 1). [0,1].
            - 'R_MFE' 컬럼이 없으면 이 키는 생략한다.
    """
    rets: list = []
    mfes: list = []
    have_ret_col = False
    have_mfe_col = False
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        if "수익률" not in fieldnames:
            return {}  # 하위호환: per-trade 수익률 컬럼이 없으면 무영향.
        have_ret_col = True
        have_mfe_col = "R_MFE" in fieldnames
        for row in reader:
            raw_ret = row.get("수익률", "")
            if raw_ret is None or str(raw_ret).strip() == "":
                continue  # 빈/결측 수익률 행은 skip.
            try:
                ret = float(raw_ret)
            except (TypeError, ValueError):
                continue
            mfe = None
            if have_mfe_col:
                raw_mfe = row.get("R_MFE", "")
                if raw_mfe is not None and str(raw_mfe).strip() != "":
                    try:
                        mfe = float(raw_mfe)
                    except (TypeError, ValueError):
                        mfe = None
            rets.append(ret)
            mfes.append(mfe)

    if not have_ret_col or not rets:
        return {}

    wins = [r for r in rets if r > 0.0]
    losses = [r for r in rets if r <= 0.0]

    # payoff_ratio = 평균이익 / abs(평균손실).
    if not losses:
        payoff_ratio = 999.0  # 손실거래 0건 = 전부 이익 → 우수(큰 양수로 cap).
    elif not wins:
        payoff_ratio = 0.0  # 이익거래 0건 = 전멸.
    else:
        mean_win = sum(wins) / len(wins)
        mean_loss = sum(losses) / len(losses)
        denom = abs(mean_loss)
        payoff_ratio = (mean_win / denom) if denom > 0.0 else 999.0

    result: dict = {"payoff_ratio": float(payoff_ratio)}

    # give_back_rate는 R_MFE 컬럼이 있을 때만 산출한다.
    if have_mfe_col:
        loss_count = len(losses)
        giveback_count = 0
        for ret, mfe in zip(rets, mfes):
            if mfe is None:
                continue
            if mfe >= mfe_giveback_threshold and ret <= 0.0:
                giveback_count += 1
        give_back_rate = giveback_count / max(loss_count, 1)
        result["give_back_rate"] = float(_clamp01(give_back_rate))

    return result
