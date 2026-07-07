"""레짐-적응 챔피언 앙상블 조립기 (알파 랩 v4, R1 단일 적응형 바닥 + R2 앙상블 조립).

봉인 근거(preregistration_v4.json, sha 87821aaa...): adaptive.lookback=2,
ensemble_variants_sealed = {a_static_equal, b_adaptive_sum, c_regime_rotation}.
설계: docs/research/condition_research/plans/2026-07-07_alpha_lab_v4_regime_ensemble_design.md
(R1: 각 챔피언 단일 적응형 바닥. R2: 발견창에서만 파라미터 확정 후 봉인).

재사용(재구현 금지): ai_strategy_loop.fitness.adaptive_timing.apply_adaptive_timing —
각 챔피언의 FLAT/유지 판정은 이 함수가 전담한다. 이 모듈은 그 위에 **여러 챔피언을
어떻게 합치는가**(등가중/적응형합산/레짐로테이션)만 새로 정의한다.

MDD 관례: risk_adjusted_metrics의 peak-drawdown 알고리즘은
ai_strategy_loop.fitness.adaptive_timing._equity_mdd 및
ai_strategy_loop.fitness.equity_series.parse_backtest_series의 drawdown과 동일
관례(누적곡선 running-peak 대비 최대 반납액, 원, 발산 없는 절대값)다 — 독립
재구현이지만 tests/unit/test_alpha_ensemble.py가 _equity_mdd와 byte-동일함을
교차검증한다(신규 척도 도입 아님).

설계 원칙:
  - 순수 함수만 — 엔진 호출·파일 I/O·난수 없음(결정론, 오프라인 R1/R2 요구사항).
  - 모든 앙상블 함수는 (label, monthly_seq) 튜플 목록을 입력받는다 — 라벨은
    regime_rotation의 매월 선택 감사(auditability)에 쓰인다.
  - 가중 방식은 static_equal·adaptive_sum이 **동일**(1/N)하다 — 타이밍 오버레이의
    순수 효과만 격리해 비교하기 위해 가중 스킴을 고정한다(a와 b는 타이밍 on/off만
    다르다). regime_rotation은 매월 1개 챔피언에 전액(가중 1.0) 배정하는 별도 전략.
  - 워밍업(트레일링 판단 근거 부족: i < max(1, lookback))은 apply_adaptive_timing의
    동일 관례를 따른다 — regime_rotation은 그 기간 등가중 대체(라벨 "EQUAL_WARMUP")로
    "아직 판단하지 않음"을 표현한다.
  - 동률(트레일링 합 정확히 같음)은 champion_series 순서상 먼저 나온 챔피언이 이긴다
    (무작위 없음, 결정론 요구사항).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from ai_strategy_loop.fitness.adaptive_timing import apply_adaptive_timing

__all__ = [
    "RiskMetrics",
    "risk_adjusted_metrics",
    "align_monthly_series",
    "static_equal",
    "adaptive_sum",
    "regime_rotation",
]


@dataclass(frozen=True)
class RiskMetrics:
    """월별 손익 시퀀스 하나의 위험조정 요약 — (누적수익, MDD, calmar).

    MDD는 누적곡선의 running-peak 대비 최대 반납액(원, ≥0) — 모듈 docstring의 관례.
    calmar = profit/mdd(mdd==0이면 0.0 — adaptive_timing_report.raw_ratio/timed_ratio와
    동일한 0-나눗셈 가드).
    """

    profit: float
    mdd: float
    calmar: float


def risk_adjusted_metrics(monthly_values: Sequence[float]) -> RiskMetrics:
    """월별 손익 시퀀스 → RiskMetrics(누적수익, MDD, calmar).

    running-peak 낙폭: 누적합을 따라가며 peak 대비 최대 반납액을 MDD로 삼는다
    (adaptive_timing._equity_mdd와 동일 관례 — tests에서 교차검증). 빈 시퀀스는
    전부 0.0(무예외).
    """
    cum = 0.0
    peak = 0.0
    mdd = 0.0
    for v in monthly_values:
        cum += float(v)
        if cum > peak:
            peak = cum
        give_back = peak - cum
        if give_back > mdd:
            mdd = give_back
    calmar = (cum / mdd) if mdd else 0.0
    return RiskMetrics(profit=float(cum), mdd=float(mdd), calmar=float(calmar))


def align_monthly_series(
    champions: Sequence[Tuple[str, Sequence[Tuple[str, float]]]]
) -> Tuple[List[str], List[Tuple[str, List[float]]]]:
    """[(label, [(ym, pnl), ...]), ...] → (공통 월 라벨 리스트, [(label, [pnl...]), ...]).

    전 챔피언의 월 라벨 시퀀스가 정확히 동일해야 한다(같은 발견창에서 같은 기간
    백테한 월별 시계열이라는 전제 — v4_characterization.json은 전 챔피언 34개월
    202203~202412로 동일함을 이미 확인). 다르면 ValueError(무음 오정렬 방지 —
    시스템 경계 입력 검증).
    """
    if not champions:
        raise ValueError("champions가 비어 있습니다 — 최소 1개 챔피언 필요")
    label0, months0 = champions[0]
    ym_labels = [ym for ym, _ in months0]
    aligned: List[Tuple[str, List[float]]] = [(label0, [float(v) for _, v in months0])]
    for label, months in champions[1:]:
        this_labels = [ym for ym, _ in months]
        if this_labels != ym_labels:
            raise ValueError(
                f"월 라벨 불일치: {label0}={ym_labels} vs {label}={this_labels}"
            )
        aligned.append((label, [float(v) for _, v in months]))
    return ym_labels, aligned


def _validate_aligned(champion_series: Sequence[Tuple[str, Sequence[float]]]) -> int:
    """(label, seq) 목록이 1개 이상·전부 동일 길이인지 검증 후 길이를 반환한다.

    시스템 경계 입력 검증: 빈 목록·길이 불일치는 ValueError(조용한 월 오정렬 방지).
    """
    if not champion_series:
        raise ValueError("champion_series가 비어 있습니다 — 최소 1개 챔피언 필요")
    lengths = {len(seq) for _, seq in champion_series}
    if len(lengths) != 1:
        detail = {label: len(seq) for label, seq in champion_series}
        raise ValueError(f"챔피언 시퀀스 길이 불일치(월 정렬 필요): {detail}")
    return lengths.pop()


def static_equal(champion_series: Sequence[Tuple[str, Sequence[float]]]) -> List[float]:
    """(a) 정적 등가중 앙상블 — 매월 N개 챔피언 원본(always-on) 손익의 1/N 평균.

    "등가중": weight_i = 1/N(합계 1) — 단일 챔피언과 동일한 총자본을 N개로 나눠
    분산 투자했다고 가정했을 때의 손익(스케일 정합 — 단일 챔피언 always-on의 절대
    수익과 직접 비교 가능하게 만드는 선택. adaptive_sum과 동일 가중 스킴).
    """
    n = _validate_aligned(champion_series)
    weight = 1.0 / len(champion_series)
    return [sum(seq[i] for _, seq in champion_series) * weight for i in range(n)]


def adaptive_sum(
    champion_series: Sequence[Tuple[str, Sequence[float]]], lookback: int
) -> List[float]:
    """(b) 적응형 앙상블 — 각 챔피언에 독립적으로 apply_adaptive_timing 적용 후 등가중 합산.

    각 챔피언의 FLAT 판정은 **자기 자신의 과거(직전 lookback개월) 손익 합**만 본다
    (다른 챔피언 상태를 참조하지 않음 — 챔피언별 인과적 독립 판단, apply_adaptive_timing
    재사용·재구현 아님). 가중은 static_equal과 동일(1/N) — 가중 스킴을 고정해 "타이밍
    오버레이의 순수 효과"만 격리해서 (a)와 비교할 수 있게 한다.
    """
    n = _validate_aligned(champion_series)
    weight = 1.0 / len(champion_series)
    timed = [apply_adaptive_timing(list(seq), lookback) for _, seq in champion_series]
    return [sum(seq[i] for seq in timed) * weight for i in range(n)]


def regime_rotation(
    champion_series: Sequence[Tuple[str, Sequence[float]]], lookback: int
) -> Tuple[List[float], List[str]]:
    """(c) 레짐-로테이션 — 매월 직전 lookback개월 손익 합이 최고인 챔피언 1개 택1(전액 배정).

    워밍업(i < max(1, lookback), apply_adaptive_timing과 동일 관례): 아직 트레일링
    판단 근거가 없으므로 static_equal(등가중 평균)로 대체한다(라벨 "EQUAL_WARMUP").

    그 외(i >= warmup): trailing_sum = sum(seq[max(0, i-lookback):i]) 최댓값 챔피언의
    그 달 **원본**(always-on) 손익을 그대로 채택한다(동률이면 champion_series 순서상
    먼저 나온 챔피언 — 결정론, 무작위 없음). i 시점 판단은 seq[:i]만 참조하므로
    미래를 보지 않는다(인과적 — tests의 no_lookahead로 검증).

    Returns:
        (손익 시퀀스, 매월 선택된 라벨 시퀀스) — 라벨은 감사/재현성 목적
        (어느 달 누가 뽑혔는지 추적).
    """
    n = _validate_aligned(champion_series)
    warmup = max(1, lookback)
    labels = [label for label, _ in champion_series]
    seqs = [list(seq) for _, seq in champion_series]

    equal_blend = static_equal(champion_series)

    out: List[float] = []
    picks: List[str] = []
    for i in range(n):
        if i < warmup:
            out.append(equal_blend[i])
            picks.append("EQUAL_WARMUP")
            continue
        best_idx = 0
        best_sum = None
        for idx, seq in enumerate(seqs):
            trailing = sum(seq[max(0, i - lookback):i])
            if best_sum is None or trailing > best_sum:
                best_sum = trailing
                best_idx = idx
        out.append(seqs[best_idx][i])
        picks.append(labels[best_idx])
    return out, picks
