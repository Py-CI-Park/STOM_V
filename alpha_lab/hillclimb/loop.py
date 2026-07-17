"""결정론 힐클라임 루프 — 시드 1개: 기준선 평가 → 이웃탐색 → 첫 수락 즉시 이동 →

재탐색, 예산 소진/로컬 최적/이동 소진 시 종료(조기중단).

전략은 "첫 개선"(first-improvement) 방식이다 — generate_moves()가 낸 결정론
순서대로 이웃을 평가하다 첫 수락에서 즉시 그 이웃으로 옮기고 그 지점에서
이웃을 다시 생성한다(라운드 전체를 다 평가하는 "최선 개선"보다 예산 효율적 —
시드당 예산이 20회로 빠듯하다). 한 라운드를 완주했는데 수락이 0건이면 로컬
최적으로 보고 종료한다.

엔진 평가는 evaluate_fn(rule) -> Metrics로 호출측이 주입한다 — 실전은
alpha_lab.hillclimb.engine_eval의 실배선, 단위테스트는 mock을 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Sequence

from alpha_lab.hillclimb.mutator import Metrics, Rule, accept, generate_moves

__all__ = [
    "DEFAULT_PER_SEED_MAX",
    "TRAIN_GATE_DAILY_MIN",
    "TRAIN_GATE_MDD_MAX",
    "SeedResult",
    "run_seed_hillclimb",
    "train_gate_pass",
]

EvaluateFn = Callable[[Rule], Metrics]

DEFAULT_PER_SEED_MAX = 20

# P3 train 게이트(봉인 preregistration_v3.json gates_p4 상위 절 "train 게이트"):
# 흑자 ∧ 일평균>=0.3 ∧ MDD<=35.
TRAIN_GATE_MDD_MAX = 35.0
TRAIN_GATE_DAILY_MIN = 0.3


@dataclass(frozen=True)
class SeedResult:
    """시드 1개의 힐클라임 종료 상태 — 재현 가능한 전체 이력 포함."""

    seed_name: str
    initial_rule: Rule
    best_rule: Rule
    best_metrics: Metrics
    trials_used: int
    stopped_reason: str  # "budget_exhausted" | "converged_local_optimum" | "no_moves"
    history: List[dict] = field(default_factory=list)


def _better(a: Metrics, b: Metrics) -> bool:
    """a가 b보다 "보고용 최선"인지 — profit_pct 우선, 동률이면 calmar 우선."""
    if a.status != "ok":
        return False
    if b.status != "ok":
        return True
    if a.profit_pct != b.profit_pct:
        return a.profit_pct > b.profit_pct
    return a.calmar > b.calmar


def run_seed_hillclimb(
    seed_name: str,
    initial_rule: Rule,
    evaluate_fn: EvaluateFn,
    distributions: Mapping,
    whitelist: Sequence[str],
    *,
    per_seed_max: int = DEFAULT_PER_SEED_MAX,
    max_add_candidates: int = 4,
) -> SeedResult:
    """시드 1개의 결정론 힐클라임을 실행한다.

    evaluate_fn 호출 횟수(=trials_used)는 항상 per_seed_max 이하다(baseline
    1회 포함). 같은 규칙을 이번 실행 중 이미 평가했으면 재호출하지 않고 캐시된
    결과를 재사용한다(예산 절약 — 임계 이동이 경계 포화로 기존 규칙과 우연히
    같아지는 경우 등).
    """
    if per_seed_max < 1:
        raise ValueError(f"per_seed_max는 1 이상이어야 한다: {per_seed_max!r}")

    history: List[dict] = []
    evaluated: Dict[Rule, Metrics] = {}

    trials = 0
    baseline = evaluate_fn(initial_rule)
    trials += 1
    evaluated[initial_rule] = baseline
    history.append(
        {"trial": trials, "kind": "baseline", "desc": "seed 원문",
         "rule": initial_rule, "metrics": baseline, "accepted": True}
    )

    current_rule, current_metrics = initial_rule, baseline
    best_rule, best_metrics = initial_rule, baseline
    stopped_reason = "budget_exhausted"

    while trials < per_seed_max:
        moves = generate_moves(current_rule, whitelist, distributions, max_add_candidates)
        if not moves:
            stopped_reason = "no_moves"
            break
        accepted_this_round = False
        budget_hit_mid_round = False
        for move in moves:
            if trials >= per_seed_max:
                budget_hit_mid_round = True
                break
            if move.rule in evaluated:
                continue  # 이미 평가한 규칙 — 예산 소모 없이 스킵.
            cand_metrics = evaluate_fn(move.rule)
            trials += 1
            evaluated[move.rule] = cand_metrics
            ok = accept(current_metrics, cand_metrics)
            history.append(
                {"trial": trials, "kind": move.kind, "desc": move.desc,
                 "rule": move.rule, "metrics": cand_metrics, "accepted": ok}
            )
            if ok:
                current_rule, current_metrics = move.rule, cand_metrics
                if _better(cand_metrics, best_metrics):
                    best_rule, best_metrics = move.rule, cand_metrics
                accepted_this_round = True
                break
        if accepted_this_round:
            continue  # 새 current에서 이웃을 다시 생성(라운드 재시작).
        if budget_hit_mid_round:
            stopped_reason = "budget_exhausted"
        else:
            stopped_reason = "converged_local_optimum"
        break

    return SeedResult(
        seed_name=seed_name,
        initial_rule=initial_rule,
        best_rule=best_rule,
        best_metrics=best_metrics,
        trials_used=trials,
        stopped_reason=stopped_reason,
        history=history,
    )


def train_gate_pass(
    metrics: Metrics,
    *,
    mdd_max: float = TRAIN_GATE_MDD_MAX,
    daily_min: float = TRAIN_GATE_DAILY_MIN,
) -> bool:
    """P3 train 게이트(봉인): 흑자(profit_pct>0) ∧ 일평균>=daily_min ∧ MDD<=mdd_max."""
    if metrics.status != "ok":
        return False
    return (
        metrics.profit_pct > 0
        and metrics.daily_avg_trades >= daily_min
        and metrics.mdd <= mdd_max
    )
