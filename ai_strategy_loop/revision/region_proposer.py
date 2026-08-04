"""손실 구간 제거 후보 생성기(G-0b) — 형태·포켓을 사람 문법 절로 바꾼다.

무엇을 하는가:
  `loss_profile` 이 찾은 **확인된 손실 구간**(1D 최악 구간, 2D 포켓)을 STOM 조건식의
  제거 절로 바꾸고, 한 세대 후보 = 제거 절 **1~4개 묶음**으로 구성한다.

왜 묶음인가:
  절 하나만 추가하면 개선이 한 번에 끝난다. 구조해석 최적화처럼 "처음에 크게, 뒤로
  갈수록 작게" 수렴시키려면 세대마다 여러 축을 동시에 잘라야 한다. 다만 무한정
  자르면 표본이 붕괴하므로 제거 예산이 세대 수를 결정한다(설계서 §5.3).

계약:
  - 임계는 `loss_profile` 이 설계 구간에서 산출한 **분위 경계 위에서만** 온다.
    여기서 임의로 미세조정하지 않는다.
  - 홀드아웃에서 확인되지 않은(`confirmed=False`) 구간과 진단 전용 변수는 제외한다.
  - 런타임 표현은 `buy_filter_proposer.RUNTIME_EXPRESSION` 화이트리스트로 fail-closed.
  - 제거율은 절 share 의 **합이 아니라 합집합 실측**이다(겹치면 과대계상된다).
  - 산출은 **자문(advisory) 권위**다. 여기 유지율·개선 추정치는 재유입을 반영하지
    못하므로 순위용이며, 판정은 공식 pair/gate 가 한다.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Final, Mapping, Sequence

from ai_strategy_loop.autopsy.loss_profile import Pocket, Sample, VariableProfile
from ai_strategy_loop.revision.buy_filter_proposer import (
    ANCHOR, RUNTIME_EXPRESSION, _round_threshold,
)


MARKER: Final = "ADD_REGION G"
CUMULATIVE_FLOOR: Final = 0.40
FIRST_GENERATION_BUDGET: Final = 0.25
LATER_GENERATION_BUDGET: Final = 0.12
MAX_CLAUSES: Final = 4
_FORBIDDEN: Final = ("R_", "S_", "F_", "미래", "oracle")


class RegionValidationError(ValueError):
    """생성된 제거 절이 연구 계약을 위반했다."""


@dataclass(frozen=True, slots=True)
class Interval:
    """반열린 구간 `(low, high]` — 사람 문법 `lo < A <= hi` 와 같은 규약."""

    column: str
    variable: str
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True, slots=True)
class RegionClause:
    kind: str
    card_id: str
    terms: tuple[tuple[Interval, ...], ...]   # 바깥 OR, 안쪽 AND
    source: str
    design_share: float
    holdout_share: float
    design_per_trade: float
    holdout_per_trade: float

    @property
    def expression(self) -> str:
        return render_terms(self.terms)

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            interval.column for group in self.terms for interval in group
        ))


@dataclass(frozen=True, slots=True)
class RegionCandidate:
    candidate_id: str
    title: str
    clauses: tuple[RegionClause, ...]
    stom_code: str
    design_retention: float
    holdout_retention: float
    design_removed_pnl: float
    holdout_removed_pnl: float
    design_per_trade_before: float
    design_per_trade_after: float
    holdout_per_trade_before: float
    holdout_per_trade_after: float
    budget: str
    intent_gate: str = "pass"
    authority: str = "advisory"
    caveat: str = (
        "제거 시뮬레이션 추정입니다. 자금이 풀려 다른 종목으로 재유입되는 효과를 "
        "반영하지 못하므로 순위용이며, 판정은 공식 pair/gate 가 합니다."
    )


# --------------------------------------------------------------------------- 표현식

def _fmt(value: float) -> str:
    """임계값 표기. 큰 정수를 `%g` 로 찍으면 `-1.09332e+10` 처럼 유효숫자 6자리로
    **잘려서 실제 계산값과 달라진다** — 정수는 정수 그대로 쓴다."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def render_interval(interval: Interval) -> str:
    if interval.low is None and interval.high is None:
        raise RegionValidationError("interval_unbounded")
    if interval.low is None:
        return f"{interval.variable} <= {_fmt(interval.high)}"      # type: ignore[arg-type]
    if interval.high is None:
        return f"{interval.variable} > {_fmt(interval.low)}"
    return f"{_fmt(interval.low)} < {interval.variable} <= {_fmt(interval.high)}"


def render_terms(terms: Sequence[Sequence[Interval]]) -> str:
    groups = []
    for group in terms:
        rendered = [render_interval(interval) for interval in group]
        groups.append(" and ".join(f"({item})" for item in rendered)
                      if len(rendered) > 1 else rendered[0])
    if len(groups) == 1:
        return groups[0]
    return " or ".join(f"({item})" for item in groups)


def _matches(values: Mapping[str, float], interval: Interval) -> bool:
    value = values.get(interval.column)
    if value is None:
        return False
    if interval.low is not None and value <= interval.low:
        return False
    if interval.high is not None and value > interval.high:
        return False
    return True


def _dropped(sample: Sample, clauses: Sequence[RegionClause]) -> bool:
    for clause in clauses:
        for group in clause.terms:
            if all(_matches(sample.values, interval) for interval in group):
                return True
    return False


def apply_clauses(
    samples: Sequence[Sample], clauses: Sequence[RegionClause],
) -> tuple[tuple[Sample, ...], float]:
    """절 묶음을 적용해 남는 표본과 **제거된 손익 합**을 돌려준다(합집합 기준)."""
    kept: list[Sample] = []
    removed = 0.0
    for sample in samples:
        if _dropped(sample, clauses):
            removed += sample.pnl
        else:
            kept.append(sample)
    return tuple(kept), round(removed, 2)


# --------------------------------------------------------------------------- 코드 삽입

def insertion_point(lines: Sequence[str]) -> tuple[int, str]:
    """제거 절을 넣을 줄 번호와 들여쓰기.

    기준선 매수식은 레인마다 모양이 다르다 — 추정하지 않고 두 모양을 명시적으로 다룬다.

    1. **계층형**(min 레인, `Min_B_Study_*`): 시간밴드 분기 `elif 시분초 < 120000:` 앞에
       넣어 계층을 보존한다(R2 와 동일).
    2. **평탄 체인**(tick 레인, `ResearchTest_Tick_B_..._Wide`): 앵커가 없다. 최상위
       elif 체인의 **마지막 분기 뒤**에 같은 체인의 분기로 덧붙인다. 모든 분기가
       `매수 = False` 로 끝나므로 체인 순서는 제거 결과를 바꾸지 않는다.
    """
    for index, line in enumerate(lines):
        if line.strip() == ANCHOR:
            return index, " " * (len(line) - len(line.lstrip()))
    # 최상위 **elif** 만 본다. 매수식 끝의 `if 매수:` 는 별개 문장이라 체인이 아니다.
    last = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("elif ") and stripped.endswith(":") and not line[:1].isspace():
            last = index
    if last is None:
        raise RegionValidationError("anchor_not_found")
    end = last + 1
    while end < len(lines) and lines[end].strip() and lines[end][:1].isspace():
        end += 1
    return end, ""


def derive_region_code(base_code: str, clauses: Sequence[RegionClause]) -> str:
    """기준선 매수식에 제거 절들을 삽입한다(레인별 모양은 insertion_point 가 판정)."""
    lines = base_code.splitlines()
    anchor, indent = insertion_point(lines)
    inserted: list[str] = []
    for order, clause in enumerate(clauses, start=1):
        inserted.append(f"{indent}elif {clause.expression}:  # {MARKER}-{order}")
        inserted.append(f"{indent}    매수 = False")
    return "\n".join(lines[:anchor] + inserted + lines[anchor:])


def validate_region_code(
    *, code: str, base_code: str, clauses: Sequence[RegionClause],
) -> None:
    """intent gate — 요청한 제거 절들만 정확히 추가됐는지 기계 판정한다."""
    expressions = [clause.expression for clause in clauses]
    for expression in expressions:
        if any(token in expression for token in _FORBIDDEN):
            raise RegionValidationError("future_label_leakage")
    base_lines = base_code.splitlines()
    new_lines = code.splitlines()
    if len(new_lines) != len(base_lines) + 2 * len(clauses):
        raise RegionValidationError("unexpected_line_count")
    marked = [index for index, line in enumerate(new_lines) if MARKER in line]
    if len(marked) != len(clauses):
        raise RegionValidationError("diff_not_region_clauses")
    for index in marked:
        if index + 1 >= len(new_lines) or new_lines[index + 1].strip() != "매수 = False":
            raise RegionValidationError("diff_not_region_clauses")
        if not new_lines[index].lstrip().startswith("elif "):
            raise RegionValidationError("diff_not_region_clauses")
    drop = set(marked) | {index + 1 for index in marked}
    stripped = [line for index, line in enumerate(new_lines) if index not in drop]
    if stripped != base_lines:
        raise RegionValidationError("baseline_body_changed")
    allowed = {expr.split("(")[0] for expr in RUNTIME_EXPRESSION.values()}
    for expression in expressions:
        try:
            tree = ast.parse(f"if {expression}:\n    pass\n")
        except SyntaxError as exc:
            raise RegionValidationError(f"clause_syntax:{exc}") from exc
        names = {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store)
        }
        unknown = names - allowed
        if unknown:
            raise RegionValidationError(f"unknown_runtime_variable:{sorted(unknown)}")


# --------------------------------------------------------------------------- 예산

def budget_verdict(
    *, generation: int, retention: float, prior_retention: float,
    holdout_retention: float | None = None,
) -> str:
    """세대 한도와 누적 40% 하한 — 낮은 쪽(설계/홀드아웃)으로 판정한다."""
    effective = retention if holdout_retention is None else min(retention, holdout_retention)
    allowance = FIRST_GENERATION_BUDGET if generation <= 1 else LATER_GENERATION_BUDGET
    if 1.0 - effective > allowance + 1e-9:
        return "exceeded"
    if prior_retention * effective < CUMULATIVE_FLOOR - 1e-9:
        return "exceeded"
    return "ok"


# --------------------------------------------------------------------------- 절 생성

def _threshold(column: str, value: float | None) -> float | None:
    return None if value is None else _round_threshold(column, value)


def clause_from_profile(profile: VariableProfile) -> RegionClause | None:
    """1D 최악 구간(다중 밴드면 자격 있는 구간 전부) → 제거 절."""
    span = profile.worst_span
    if span is None or not profile.confirmed or not profile.proposable:
        return None
    variable = RUNTIME_EXPRESSION.get(profile.variable)
    if variable is None:
        return None
    runs = [run for run in profile.bad_runs if run[1] - run[0] + 1 >= 2]
    if profile.shape != "multi_band" or len(runs) < 2:
        runs = [(span.from_bucket, span.to_bucket)]
    terms: list[tuple[Interval, ...]] = []
    for start, end in runs:
        low = profile.edges[start - 2] if start >= 2 else None
        high = profile.edges[end - 1] if end <= len(profile.edges) else None
        if low is None and high is None:
            continue
        terms.append((Interval(
            column=profile.variable, variable=variable,
            low=_threshold(profile.variable, low),
            high=_threshold(profile.variable, high),
        ),))
    if not terms:
        return None
    kind = "multi_band" if len(terms) > 1 else (
        "range" if terms[0][0].low is not None and terms[0][0].high is not None else "single"
    )
    return RegionClause(
        kind=kind, card_id=f"{kind}_{profile.variable}", terms=tuple(terms),
        source=(
            f"{profile.variable} 형태 {profile.shape} · 설계 건당 "
            f"{span.design_per_trade:,.0f}(전체 {profile.design_overall:,.0f}) · "
            f"홀드 건당 {span.holdout_per_trade:,.0f}(전체 {profile.holdout_overall:,.0f})"
        ),
        design_share=span.design_share, holdout_share=span.holdout_share,
        design_per_trade=span.design_per_trade, holdout_per_trade=span.holdout_per_trade,
    )


def clause_from_pocket(pocket: Pocket) -> RegionClause | None:
    """2D 포켓 → 두 변수 AND 제거 절."""
    left, right = pocket.pair
    left_variable = RUNTIME_EXPRESSION.get(left)
    right_variable = RUNTIME_EXPRESSION.get(right)
    if left_variable is None or right_variable is None:
        return None
    group = (
        Interval(column=left, variable=left_variable,
                 low=_threshold(left, pocket.x_low), high=_threshold(left, pocket.x_high)),
        Interval(column=right, variable=right_variable,
                 low=_threshold(right, pocket.y_low), high=_threshold(right, pocket.y_high)),
    )
    if any(interval.low is None and interval.high is None for interval in group):
        return None
    return RegionClause(
        kind="pocket_2d", card_id=f"pocket_{left}_{right}", terms=(group,),
        source=(
            f"2D 포켓 {left}×{right} · 칸 {pocket.cells} · q≤{pocket.max_q:.3f} · "
            f"설계 건당 {pocket.design_per_trade:,.0f} · 홀드 건당 {pocket.holdout_per_trade:,.0f}"
        ),
        design_share=pocket.design_share, holdout_share=pocket.holdout_share,
        design_per_trade=pocket.design_per_trade, holdout_per_trade=pocket.holdout_per_trade,
    )


# --------------------------------------------------------------------------- 후보 구성

def _per_trade(samples: Sequence[Sample]) -> float:
    return round(sum(sample.pnl for sample in samples) / len(samples), 2) if samples else 0.0


def _build(
    *, candidate_id: str, clauses: Sequence[RegionClause], base_code: str,
    design: Sequence[Sample], holdout: Sequence[Sample], generation: int,
    prior_retention: float,
) -> RegionCandidate | None:
    code = derive_region_code(base_code, clauses)
    try:
        validate_region_code(code=code, base_code=base_code, clauses=clauses)
    except RegionValidationError:
        return None
    design_kept, design_removed = apply_clauses(design, clauses)
    holdout_kept, holdout_removed = apply_clauses(holdout, clauses)
    design_retention = round(len(design_kept) / len(design), 4) if design else 0.0
    holdout_retention = round(len(holdout_kept) / len(holdout), 4) if holdout else 0.0
    return RegionCandidate(
        candidate_id=candidate_id,
        title=" + ".join(clause.expression for clause in clauses),
        clauses=tuple(clauses),
        stom_code=code,
        design_retention=design_retention,
        holdout_retention=holdout_retention,
        design_removed_pnl=design_removed,
        holdout_removed_pnl=holdout_removed,
        design_per_trade_before=_per_trade(design),
        design_per_trade_after=_per_trade(design_kept),
        holdout_per_trade_before=_per_trade(holdout),
        holdout_per_trade_after=_per_trade(holdout_kept),
        budget=budget_verdict(
            generation=generation, retention=design_retention,
            prior_retention=prior_retention, holdout_retention=holdout_retention,
        ),
    )


def _mask(samples: Sequence[Sample], clause: RegionClause) -> set[int]:
    return {index for index, sample in enumerate(samples) if _dropped(sample, (clause,))}


def _after(
    total: float, count: int, pnls: Sequence[float], removed: set[int],
) -> tuple[float, float]:
    """제거 후 (건당손익, 유지율)."""
    kept = count - len(removed)
    if kept <= 0:
        return 0.0, 0.0
    return (total - sum(pnls[index] for index in removed)) / kept, kept / count


def _greedy_select(
    *,
    clauses: Sequence[RegionClause],
    design: Sequence[Sample],
    holdout: Sequence[Sample],
    generation: int,
    prior_retention: float,
    max_clauses: int,
) -> tuple[list[RegionClause], list[dict[str, str]]]:
    """예산 안에서 **건당 개선이 가장 큰 절부터** 고른다.

    손실 밀도 순으로만 고르면 거래 0.8% 짜리 미세 포켓이 슬롯 4개를 다 먹고 25%p 예산의
    3%만 쓴다 — 안전하지만 세대당 개선이 거의 없다. 반대로 제거량 순으로만 고르면
    표본이 무너진다. 그래서 매 단계 **실제 결과 건당손익**을 재서 최선을 고른다.
    설계·홀드아웃 **양쪽에서 개선**하지 못하는 절은 담지 않는다.
    """
    if not design or not holdout:
        return [], []
    design_pnls = [sample.pnl for sample in design]
    holdout_pnls = [sample.pnl for sample in holdout]
    design_total, holdout_total = sum(design_pnls), sum(holdout_pnls)
    design_base = design_total / len(design)
    holdout_base = holdout_total / len(holdout)
    design_masks = [_mask(design, clause) for clause in clauses]
    holdout_masks = [_mask(holdout, clause) for clause in clauses]

    selected: list[RegionClause] = []
    rejected: list[dict[str, str]] = []
    chosen: set[int] = set()
    design_removed: set[int] = set()
    holdout_removed: set[int] = set()
    current_design, current_holdout = design_base, holdout_base
    blocked: dict[int, str] = {}

    while len(selected) < max_clauses:
        best: tuple[float, int] | None = None
        for index, clause in enumerate(clauses):
            if index in chosen or index in blocked:
                continue
            trial_design = design_removed | design_masks[index]
            trial_holdout = holdout_removed | holdout_masks[index]
            design_after, design_retention = _after(
                design_total, len(design), design_pnls, trial_design,
            )
            holdout_after, holdout_retention = _after(
                holdout_total, len(holdout), holdout_pnls, trial_holdout,
            )
            if budget_verdict(
                generation=generation, retention=design_retention,
                prior_retention=prior_retention, holdout_retention=holdout_retention,
            ) != "ok":
                blocked[index] = (
                    f"제거 예산 초과 — 누적 유지율 설계 {design_retention:.1%} / "
                    f"홀드 {holdout_retention:.1%}"
                )
                continue
            if design_after <= current_design or holdout_after <= current_holdout:
                blocked[index] = "설계·홀드아웃 동반 개선 아님"
                continue
            gain = min(design_after - current_design, holdout_after - current_holdout)
            if best is None or gain > best[0]:
                best = (gain, index)
        if best is None:
            break
        _, index = best
        chosen.add(index)
        selected.append(clauses[index])
        design_removed |= design_masks[index]
        holdout_removed |= holdout_masks[index]
        current_design, _ = _after(design_total, len(design), design_pnls, design_removed)
        current_holdout, _ = _after(holdout_total, len(holdout), holdout_pnls, holdout_removed)
        blocked.clear()          # 조합이 바뀌면 이전 판정은 무효다 — 다시 잰다.

    rejected.extend(
        {"item": clauses[index].expression, "reason": reason}
        for index, reason in blocked.items()
    )
    return selected, rejected


def propose_regions(
    *,
    profiles: Sequence[VariableProfile],
    pockets: Sequence[Pocket],
    design: Sequence[Sample],
    holdout: Sequence[Sample],
    base_code: str,
    generation: int = 1,
    prior_retention: float = 1.0,
    max_clauses: int = MAX_CLAUSES,
    top: int = 4,
) -> tuple[tuple[RegionCandidate, ...], tuple[dict[str, str], ...]]:
    """확인된 손실 구간들 → 제거 절 묶음 후보. 반환 (후보, 제외 사유)."""
    skipped: list[dict[str, str]] = []
    clauses: list[RegionClause] = []
    for profile in profiles:
        if not profile.proposable:
            skipped.append({"item": profile.variable, "reason": "조건식 입력 불가(진단 전용)"})
            continue
        if not profile.confirmed:
            skipped.append({"item": profile.variable, "reason": "홀드아웃 미확인"})
            continue
        clause = clause_from_profile(profile)
        if clause is None:
            skipped.append({"item": profile.variable, "reason": "런타임 표현 미확인 — 추정하지 않음"})
            continue
        clauses.append(clause)
    for pocket in pockets:
        clause = clause_from_pocket(pocket)
        if clause is None:
            skipped.append({
                "item": f"{pocket.pair[0]}×{pocket.pair[1]}",
                "reason": "런타임 표현 미확인 — 추정하지 않음",
            })
            continue
        clauses.append(clause)
    if not clauses:
        return (), tuple(skipped)

    selected, rejected = _greedy_select(
        clauses=clauses, design=design, holdout=holdout,
        generation=generation, prior_retention=prior_retention, max_clauses=max_clauses,
    )
    skipped.extend(rejected)
    if not selected:
        return (), tuple(skipped)

    candidates: list[RegionCandidate] = []
    for size in range(1, len(selected) + 1):
        built = _build(
            candidate_id=f"G{generation}_{size}절",
            clauses=selected[:size], base_code=base_code,
            design=design, holdout=holdout,
            generation=generation, prior_retention=prior_retention,
        )
        if built is None:
            skipped.append({"item": f"{size}절 묶음", "reason": "intent gate 실패"})
            continue
        candidates.append(built)
        if len(candidates) >= top:
            break
    return tuple(candidates), tuple(skipped)
