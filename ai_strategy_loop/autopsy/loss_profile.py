"""손실 영역 형태 프로파일러(G-0a) — 어느 변수의 어느 구간이 지속 손실인가.

계약:
  - 10분위 경계는 **설계 구간에서만** 산출한다. 홀드아웃에는 같은 경계를 그대로
    적용한다(경계 재산출은 홀드아웃 누출이다).
  - 형태 판정 순서: flat 가드 → multi_band → valley → tail_* → monotone_* → flat.
    **multi_band 를 valley 보다 먼저** 검사한다. 설계서 §2.3a: 초안이 반대 순서라
    체결강도를 valley 로 오분류했고 표본밖 개선을 +682 → +310 으로 놓칠 뻔했다.
    (flat 은 가드이자 폴백이다. 스프레드가 노이즈 수준이면 어떤 형태도 의미가 없어
     먼저 걸러야 뒤 판정이 노이즈를 형태로 오인하지 않는다.)
  - 제거 후보 구간은 **인접 2칸 이상 연속**만 인정한다(규율 2). 양끝이라도 예외는 없다.
  - 설계에서 지목한 최악 구간이 홀드아웃에서도 나쁘고 하위 40% 안이면 `confirmed`,
    아니면 `unstable` — 후보에서 제외한다.
  - 2D 포켓은 Welch t + BH-FDR(q≤0.10) 통과 + 인접 연속 + 직사각형 근사 낭비 30% 이하만.
  - 이 모듈의 산출은 **진단(diagnostic) 권위**다. 채택 판정은 공식 pair/gate 가 한다.
    제거 시뮬레이션 추정치는 재유입을 반영하지 못하므로 순위용으로만 쓴다.
"""

from __future__ import annotations

import bisect
import csv
import math
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ai_strategy_loop.autopsy.recovery_insight import bh_fdr


BUCKETS = 10
MIN_RUN = 2                    # 규율 2 — 고립 1칸 금지
MIN_POCKET_CELLS = 2
FDR_ALPHA = 0.10
PNL_COLUMN = "수익금"
BUY_TIME_COLUMN = "매수시간"

_SHAPE_RHO = 0.6               # 단조 판정 Spearman 임계
_FLAT_RATIO = 0.10             # 스프레드 < |전체 건당| × 10% → flat
_TAIL_SIGMA = 1.0              # 꼬리 판정 — 전체 σ 배수
_TAIL_MIDDLE_RATIO = 0.5       # 중간(D3~D8)이 전체보다 이만큼 평탄해야 꼬리
_HOLDOUT_WORST_PCT = 0.40      # 홀드아웃 하위 40% 안이어야 confirmed
_RECT_WASTE_CAP = 0.30         # 직사각형 근사 낭비 상한
_PAIR_CORR_CAP = 0.6           # |r| 이상이면 같은 축으로 보고 2D 조합에서 제외
_MIN_TOTAL_FACTOR = 4          # 전체 표본 하한 = max(200, min_bucket × 4)
_DERIVED_PROPOSABLE = ("시분초",)   # 매수시간에서 유도 — 매수 시점에 확정된 값


# --------------------------------------------------------------------------- 모델

@dataclass(frozen=True, slots=True)
class Sample:
    """한 거래 — 변수값 묶음과 비용 후 손익."""

    values: Mapping[str, float]
    pnl: float
    date: int = 0


@dataclass(frozen=True, slots=True)
class Bucket:
    bucket: int                # 1..10
    n: int
    pnl: float
    per_trade: float
    low: float | None          # 하한 경계(1분위는 None = 열린 구간)
    high: float | None         # 상한 경계(10분위는 None)
    insufficient: bool


@dataclass(frozen=True, slots=True)
class WorstSpan:
    from_bucket: int
    to_bucket: int
    low: float | None
    high: float | None
    design_n: int
    design_pnl: float
    design_per_trade: float
    holdout_n: int
    holdout_pnl: float
    holdout_per_trade: float
    design_share: float        # 설계 거래 중 이 구간 비중 = 제거율 추정
    holdout_share: float
    contiguous: bool


@dataclass(frozen=True, slots=True)
class VariableProfile:
    variable: str
    shape: str
    confirmed: bool
    reason: str
    proposable: bool           # 조건식 입력으로 쓸 수 있는가(진단 전용과 구분)
    spread: float
    design_overall: float
    holdout_overall: float
    edges: tuple[float, ...]
    design: tuple[Bucket, ...]
    holdout: tuple[Bucket, ...]
    bad_runs: tuple[tuple[int, int], ...]
    worst_span: WorstSpan | None


@dataclass(frozen=True, slots=True)
class Pocket:
    pair: tuple[str, str]
    cells: int
    cell_list: tuple[tuple[int, int], ...]
    x_from: int
    x_to: int
    y_from: int
    y_to: int
    x_low: float | None
    x_high: float | None
    y_low: float | None
    y_high: float | None
    design_n: int
    design_pnl: float
    design_per_trade: float
    holdout_n: int
    holdout_pnl: float
    holdout_per_trade: float
    design_share: float
    holdout_share: float
    rect_waste: float
    max_q: float


# --------------------------------------------------------------------------- 수치 유틸

def _number(value: object) -> float | None:
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def quantile_edges(values: Sequence[float], buckets: int = BUCKETS) -> tuple[float, ...]:
    """분위 경계 `buckets - 1` 개. 호출자는 **설계 값만** 넘겨야 한다."""
    ordered = sorted(values)
    size = len(ordered)
    if size < buckets:
        return ()
    return tuple(ordered[min(size - 1, index * size // buckets)] for index in range(1, buckets))


def _bucket_index(value: float, edges: Sequence[float]) -> int:
    """`(edges[k-2], edges[k-1]]` 반열린 구간 — 사람 문법 `lo < A <= hi` 와 같은 규약."""
    return bisect.bisect_left(edges, value) + 1


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        last = position
        while last + 1 < len(order) and values[order[last + 1]] == values[order[position]]:
            last += 1
        average = (position + last) / 2 + 1
        for index in range(position, last + 1):
            ranks[order[index]] = average
        position = last + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    size = len(xs)
    if size < 2:
        return 0.0
    mean_x, mean_y = _mean(xs), _mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    dev_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    dev_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if dev_x == 0 or dev_y == 0:
        return 0.0
    return numerator / (dev_x * dev_y)


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    return _pearson(_ranks(xs), _ranks(ys))


def _welch_p_stats(
    n1: int, mean1: float, var1: float, n2: int, mean2: float, var2: float,
) -> float:
    """요약통계만으로 Welch t 양측 p — 칸마다 리스트를 만들지 않기 위함(정규 근사)."""
    if n1 < 2 or n2 < 2:
        return 1.0
    se = math.sqrt(max(0.0, var1) / n1 + max(0.0, var2) / n2)
    if se <= 0:
        return 1.0
    z = abs(mean1 - mean2) / se
    return max(0.0, min(1.0, math.erfc(z / math.sqrt(2))))


def _runs(flags: Mapping[int, bool], buckets: Sequence[int]) -> tuple[tuple[int, int], ...]:
    """True 인 분위의 **연속 구간** 목록. 표본 부족 분위는 연속을 끊는다."""
    out: list[tuple[int, int]] = []
    start: int | None = None
    previous: int | None = None
    for bucket in buckets:
        if flags.get(bucket):
            if start is None or previous is None or bucket != previous + 1:
                if start is not None and previous is not None:
                    out.append((start, previous))
                start = bucket
            previous = bucket
        else:
            if start is not None and previous is not None:
                out.append((start, previous))
            start = previous = None
    if start is not None and previous is not None:
        out.append((start, previous))
    return tuple(out)


def rectangle_waste(cells: Iterable[tuple[int, int]]) -> float:
    """포켓을 직사각형으로 근사할 때 끌려 들어오는 '나쁘지 않은 칸' 비율."""
    listed = list(cells)
    if not listed:
        return 1.0
    rows = [row for row, _ in listed]
    cols = [col for _, col in listed]
    area = (max(rows) - min(rows) + 1) * (max(cols) - min(cols) + 1)
    return 0.0 if area <= 0 else max(0.0, 1.0 - len(listed) / area)


def pareto_front(
    items: Sequence[Mapping[str, object]], *, removal_key: str, gain_key: str,
) -> tuple[Mapping[str, object], ...]:
    """제거율은 작을수록, 건당 개선은 클수록 좋다 — 비지배 집합만 남긴다."""
    def dominated(candidate: Mapping[str, object]) -> bool:
        removal = float(candidate[removal_key])          # type: ignore[arg-type]
        gain = float(candidate[gain_key])                # type: ignore[arg-type]
        for other in items:
            if other is candidate:
                continue
            other_removal = float(other[removal_key])    # type: ignore[arg-type]
            other_gain = float(other[gain_key])          # type: ignore[arg-type]
            better_or_equal = other_removal <= removal and other_gain >= gain
            strictly = other_removal < removal or other_gain > gain
            if better_or_equal and strictly:
                return True
        return False

    survivors = [item for item in items if not dominated(item)]
    return tuple(sorted(survivors, key=lambda item: float(item[removal_key])))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- 형태 판정

def classify_shape(
    per_trade: Mapping[int, float], overall: float,
) -> tuple[str, tuple[tuple[int, int], ...]]:
    """설계 곡선의 형태와 '전체 평균보다 나쁜' 연속 구간 목록.

    판정 순서는 모듈 docstring 참조 — multi_band 가 valley 보다 앞이다.
    """
    buckets = sorted(per_trade)
    if len(buckets) < 6:
        return "flat", ()
    values = [per_trade[bucket] for bucket in buckets]
    spread = max(values) - min(values)
    if spread < max(abs(overall) * _FLAT_RATIO, 1e-9):
        return "flat", ()

    bad = {bucket: per_trade[bucket] < overall for bucket in buckets}
    runs = _runs(bad, buckets)
    sigma = _stdev(values)
    actionable = [run for run in runs if run[1] - run[0] + 1 >= MIN_RUN]

    # 1) multi_band — 나쁜 분위가 2개 이상 비연속 구간으로 분리(설계서 §4.1).
    #    제거할 수 있는 구간(길이 ≥ MIN_RUN)이 하나도 없으면 노이즈 흩어짐이므로 넘긴다.
    if len(runs) >= 2 and actionable:
        return "multi_band", runs

    # 2) valley — 중앙부 한 구간만 나쁘고 양끝 2분위가 모두 평균보다 좋다.
    if len(runs) == 1:
        start, end = runs[0]
        interior = start >= 3 and end <= BUCKETS - 2
        ends_good = all(
            per_trade.get(bucket, overall) > overall
            for bucket in (buckets[0], buckets[1], buckets[-2], buckets[-1])
        )
        if interior and ends_good:
            return "valley", runs

    # 3) 꼬리 — 한쪽 끝 2분위만 급락하고 중간(D3~D8)은 평탄하다.
    middle = [per_trade[bucket] for bucket in buckets if 3 <= bucket <= BUCKETS - 2]
    middle_flat = _stdev(middle) <= _TAIL_MIDDLE_RATIO * sigma if middle else False
    if middle_flat and sigma > 0:
        high_tail = [per_trade[bucket] for bucket in buckets[-2:]]
        low_tail = [per_trade[bucket] for bucket in buckets[:2]]
        rest_high = [per_trade[bucket] for bucket in buckets[:-2]]
        rest_low = [per_trade[bucket] for bucket in buckets[2:]]
        if rest_high and _mean(high_tail) <= _mean(rest_high) - _TAIL_SIGMA * sigma:
            return "tail_high", runs
        if rest_low and _mean(low_tail) <= _mean(rest_low) - _TAIL_SIGMA * sigma:
            return "tail_low", runs

    # 4) 단조
    rho = _spearman([float(bucket) for bucket in buckets], values)
    if rho >= _SHAPE_RHO:
        return "monotone_up", runs
    if rho <= -_SHAPE_RHO:
        return "monotone_down", runs

    return "flat", runs


# --------------------------------------------------------------------------- 프로파일

def _bucket_stats(
    values: Sequence[float], pnls: Sequence[float], edges: Sequence[float], min_bucket: int,
) -> tuple[list[Bucket], float, int]:
    totals: dict[int, list[float]] = {bucket: [0.0, 0.0] for bucket in range(1, BUCKETS + 1)}
    for value, pnl in zip(values, pnls):
        entry = totals[_bucket_index(value, edges)]
        entry[0] += 1
        entry[1] += pnl
    out: list[Bucket] = []
    for bucket in range(1, BUCKETS + 1):
        count, total = totals[bucket]
        out.append(
            Bucket(
                bucket=bucket,
                n=int(count),
                pnl=round(total, 2),
                per_trade=round(total / count, 2) if count else 0.0,
                low=edges[bucket - 2] if bucket >= 2 else None,
                high=edges[bucket - 1] if bucket <= BUCKETS - 1 else None,
                insufficient=count < min_bucket,
            )
        )
    total_n = len(pnls)
    overall = sum(pnls) / total_n if total_n else 0.0
    return out, overall, total_n


def _span_stats(
    buckets: Sequence[Bucket], start: int, end: int, total_n: int,
) -> tuple[int, float, float, float]:
    picked = [bucket for bucket in buckets if start <= bucket.bucket <= end]
    count = sum(bucket.n for bucket in picked)
    total = sum(bucket.pnl for bucket in picked)
    per_trade = round(total / count, 2) if count else 0.0
    share = round(count / total_n, 4) if total_n else 0.0
    return count, round(total, 2), per_trade, share


def _profile_series(
    *,
    variable: str,
    design_values: Sequence[float],
    design_pnls: Sequence[float],
    holdout_values: Sequence[float],
    holdout_pnls: Sequence[float],
    min_bucket: int,
) -> VariableProfile:
    edges = quantile_edges(design_values)
    if not edges:
        return VariableProfile(
            variable=variable, shape="flat", confirmed=False, reason="insufficient_buckets",
            proposable=is_proposable(variable),
            spread=0.0, design_overall=0.0, holdout_overall=0.0, edges=(),
            design=(), holdout=(), bad_runs=(), worst_span=None,
        )
    design_buckets, design_overall, design_n = _bucket_stats(
        design_values, design_pnls, edges, min_bucket,
    )
    holdout_buckets, holdout_overall, holdout_n = _bucket_stats(
        holdout_values, holdout_pnls, edges, min_bucket,
    )
    usable = {
        bucket.bucket: bucket.per_trade
        for bucket in design_buckets if not bucket.insufficient
    }
    spread = round(max(usable.values()) - min(usable.values()), 2) if usable else 0.0
    shape, runs = classify_shape(usable, design_overall)

    base = dict(
        variable=variable, shape=shape, spread=spread, proposable=is_proposable(variable),
        design_overall=round(design_overall, 2), holdout_overall=round(holdout_overall, 2),
        edges=edges, design=tuple(design_buckets), holdout=tuple(holdout_buckets),
        bad_runs=runs,
    )
    # 스프레드가 노이즈 수준이면 runs 가 비어 여기서 끝난다. 반대로 형태를 못 붙였더라도
    # 실제 연속 손실 구간이 있으면 버리지 않는다 — 형태 이름이 아니라 구간이 자산이다.
    if not runs:
        return VariableProfile(confirmed=False, reason="flat", worst_span=None, **base)

    qualifying = [run for run in runs if run[1] - run[0] + 1 >= MIN_RUN]
    if not qualifying:
        return VariableProfile(
            confirmed=False, reason="no_contiguous_run", worst_span=None, **base,
        )

    def design_edge(run: tuple[int, int]) -> float:
        return _span_stats(design_buckets, run[0], run[1], design_n)[2]

    start, end = min(qualifying, key=design_edge)
    d_count, d_total, d_per, d_share = _span_stats(design_buckets, start, end, design_n)
    h_count, h_total, h_per, h_share = _span_stats(holdout_buckets, start, end, holdout_n)
    span = WorstSpan(
        from_bucket=start, to_bucket=end,
        low=edges[start - 2] if start >= 2 else None,
        high=edges[end - 1] if end <= BUCKETS - 1 else None,
        design_n=d_count, design_pnl=d_total, design_per_trade=d_per,
        holdout_n=h_count, holdout_pnl=h_total, holdout_per_trade=h_per,
        design_share=d_share, holdout_share=h_share, contiguous=True,
    )

    confirmed, reason = _confirm(span, holdout_buckets, holdout_overall, min_bucket)
    return VariableProfile(confirmed=confirmed, reason=reason, worst_span=span, **base)


def _confirm(
    span: WorstSpan, holdout_buckets: Sequence[Bucket], holdout_overall: float, min_bucket: int,
) -> tuple[bool, str]:
    """홀드아웃에서도 나쁘고, 하위 40% 안에 들어야 confirmed."""
    if span.holdout_n < min_bucket:
        return False, "holdout_sample_too_small"
    if span.holdout_per_trade >= holdout_overall:
        return False, "holdout_not_bad"
    usable = sorted(
        bucket.per_trade for bucket in holdout_buckets if not bucket.insufficient
    )
    if not usable:
        return False, "holdout_sample_too_small"
    cutoff = usable[max(0, math.ceil(len(usable) * _HOLDOUT_WORST_PCT) - 1)]
    if span.holdout_per_trade > cutoff:
        return False, "holdout_rank_too_high"
    return True, ""


def profile_variable(
    *,
    variable: str,
    design: Sequence[Sample],
    holdout: Sequence[Sample],
    min_bucket: int = 100,
) -> VariableProfile:
    """단일 변수 프로파일 — 테스트·소량 분석용 진입점."""
    design_pairs = [
        (number, sample.pnl) for sample in design
        if (number := _number(sample.values.get(variable))) is not None
    ]
    holdout_pairs = [
        (number, sample.pnl) for sample in holdout
        if (number := _number(sample.values.get(variable))) is not None
    ]
    return _profile_series(
        variable=variable,
        design_values=[value for value, _ in design_pairs],
        design_pnls=[pnl for _, pnl in design_pairs],
        holdout_values=[value for value, _ in holdout_pairs],
        holdout_pnls=[pnl for _, pnl in holdout_pairs],
        min_bucket=min_bucket,
    )


# --------------------------------------------------------------------------- 2D 포켓

@dataclass(frozen=True, slots=True)
class _PairGrid:
    """한 쌍의 격자 — FDR 보정 전 후보 칸과 그 칸의 p값."""

    pair: tuple[str, str]
    x_edges: tuple[float, ...]
    y_edges: tuple[float, ...]
    design_cells: dict[tuple[int, int], list[float]]
    holdout_cells: dict[tuple[int, int], list[float]]
    design_n: int
    holdout_n: int
    candidates: dict[tuple[int, int], float] = field(default_factory=dict)


def _pair_grid(
    *,
    pair: tuple[str, str],
    design: tuple[list[float], list[float], list[float]],
    holdout: tuple[list[float], list[float], list[float]],
    min_cell: int,
) -> _PairGrid | None:
    """설계 경계로 10×10 격자를 만들고 '양쪽 손실' 후보 칸의 Welch p 를 계산한다."""
    dx, dy, dp = design
    hx, hy, hp = holdout
    x_edges = quantile_edges(dx)
    y_edges = quantile_edges(dy)
    if not x_edges or not y_edges:
        return None

    def grid(xs, ys, ps):
        cells: dict[tuple[int, int], list[float]] = {}
        for x, y, pnl in zip(xs, ys, ps):
            key = (_bucket_index(x, x_edges), _bucket_index(y, y_edges))
            entry = cells.setdefault(key, [0.0, 0.0, 0.0])
            entry[0] += 1
            entry[1] += pnl
            entry[2] += pnl * pnl
        return cells

    design_cells = grid(dx, dy, dp)
    holdout_cells = grid(hx, hy, hp)
    design_n = len(dp)
    holdout_n = len(hp)
    if design_n == 0 or holdout_n == 0:
        return None
    design_sum = sum(dp)
    design_sq = sum(value * value for value in dp)
    design_overall = design_sum / design_n
    holdout_overall = sum(hp) / holdout_n

    survivors: dict[tuple[int, int], float] = {}
    for key, (count, total, square) in design_cells.items():
        h_entry = holdout_cells.get(key)
        if count < min_cell or h_entry is None or h_entry[0] < min_cell:
            continue
        cell_mean = total / count
        if cell_mean >= design_overall:
            continue
        if h_entry[1] / h_entry[0] >= holdout_overall:
            continue
        rest_n = design_n - int(count)
        if rest_n < 2:
            continue
        rest_mean = (design_sum - total) / rest_n
        rest_var = max(0.0, (design_sq - square) / rest_n - rest_mean ** 2) * rest_n / (rest_n - 1)
        cell_var = max(0.0, square / count - cell_mean ** 2) * count / (count - 1)
        survivors[key] = _welch_p_stats(
            int(count), cell_mean, cell_var, rest_n, rest_mean, rest_var,
        )
    return _PairGrid(
        pair=pair, x_edges=x_edges, y_edges=y_edges,
        design_cells=design_cells, holdout_cells=holdout_cells,
        design_n=design_n, holdout_n=holdout_n, candidates=survivors,
    )


def _build_pockets(grid: _PairGrid, qvalues: Mapping[tuple[int, int], float]) -> list[Pocket]:
    """FDR 통과 칸만으로 연결 성분을 만들고 연속성·직사각형 규율을 적용한다."""
    passing = {key for key, q in qvalues.items() if q <= FDR_ALPHA}
    out: list[Pocket] = []
    for component in _components(passing):
        if len(component) < MIN_POCKET_CELLS:
            continue
        waste = rectangle_waste(component)
        if waste > _RECT_WASTE_CAP:
            continue
        rows = [row for row, _ in component]
        cols = [col for _, col in component]
        d_count = sum(grid.design_cells[key][0] for key in component)
        d_total = sum(grid.design_cells[key][1] for key in component)
        h_count = sum(grid.holdout_cells[key][0] for key in component)
        h_total = sum(grid.holdout_cells[key][1] for key in component)
        out.append(
            Pocket(
                pair=grid.pair,
                cells=len(component),
                cell_list=tuple(sorted(component)),
                x_from=min(rows), x_to=max(rows), y_from=min(cols), y_to=max(cols),
                x_low=grid.x_edges[min(rows) - 2] if min(rows) >= 2 else None,
                x_high=grid.x_edges[max(rows) - 1] if max(rows) <= BUCKETS - 1 else None,
                y_low=grid.y_edges[min(cols) - 2] if min(cols) >= 2 else None,
                y_high=grid.y_edges[max(cols) - 1] if max(cols) <= BUCKETS - 1 else None,
                design_n=int(d_count), design_pnl=round(d_total, 2),
                design_per_trade=round(d_total / d_count, 2) if d_count else 0.0,
                holdout_n=int(h_count), holdout_pnl=round(h_total, 2),
                holdout_per_trade=round(h_total / h_count, 2) if h_count else 0.0,
                design_share=round(d_count / grid.design_n, 4),
                holdout_share=round(h_count / grid.holdout_n, 4),
                rect_waste=round(waste, 4),
                max_q=round(max(qvalues[key] for key in component), 6),
            )
        )
    return out


def _components(cells: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """상하좌우 4-이웃 연결 성분."""
    remaining = set(cells)
    out: list[list[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        group = [seed]
        queue = deque([seed])
        while queue:
            row, col = queue.popleft()
            for neighbour in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if neighbour in remaining:
                    remaining.discard(neighbour)
                    group.append(neighbour)
                    queue.append(neighbour)
        out.append(group)
    return out


def pocket_scan(
    *,
    design: Sequence[Sample],
    holdout: Sequence[Sample],
    variables: Sequence[str],
    min_cell: int = 50,
    max_pairs: int = 15,
) -> tuple[Pocket, ...]:
    """상관이 낮은 변수 쌍의 10×10 격자에서 지속 손실 포켓을 찾는다.

    다중비교 보정은 **스캔 전체(모든 쌍의 모든 칸)** 에 대해 한 번에 적용한다.
    """
    columns: dict[str, list[float]] = {}
    for name in variables:
        columns[name] = []
    design_rows: list[tuple[dict[str, float], float]] = []
    holdout_rows: list[tuple[dict[str, float], float]] = []
    for source, target in ((design, design_rows), (holdout, holdout_rows)):
        for sample in source:
            picked: dict[str, float] = {}
            for name in variables:
                number = _number(sample.values.get(name))
                if number is None:
                    break
                picked[name] = number
            else:
                target.append((picked, sample.pnl))
    if not design_rows or not holdout_rows:
        return ()

    pairs: list[tuple[str, str]] = []
    for left_index, left in enumerate(variables):
        for right in variables[left_index + 1:]:
            xs = [row[left] for row, _ in design_rows]
            ys = [row[right] for row, _ in design_rows]
            if abs(_pearson(xs, ys)) >= _PAIR_CORR_CAP:
                continue
            pairs.append((left, right))
    pairs = pairs[:max_pairs]

    grids: list[_PairGrid] = []
    for pair in pairs:
        left, right = pair
        grid = _pair_grid(
            pair=pair,
            design=(
                [row[left] for row, _ in design_rows],
                [row[right] for row, _ in design_rows],
                [pnl for _, pnl in design_rows],
            ),
            holdout=(
                [row[left] for row, _ in holdout_rows],
                [row[right] for row, _ in holdout_rows],
                [pnl for _, pnl in holdout_rows],
            ),
            min_cell=min_cell,
        )
        if grid is not None and grid.candidates:
            grids.append(grid)
    if not grids:
        return ()

    # 다중비교 보정은 스캔 전체(모든 쌍의 모든 후보 칸)에 한 번에 — 그리고 **연결 성분보다
    # 먼저** 적용한다. 뒤로 미루면 유의하지 않은 칸이 포켓에 딸려 들어온다.
    keys = [(index, key) for index, grid in enumerate(grids) for key in grid.candidates]
    qvalues = bh_fdr([grids[index].candidates[key] for index, key in keys])
    per_grid: list[dict[tuple[int, int], float]] = [{} for _ in grids]
    for (index, key), q in zip(keys, qvalues):
        per_grid[index][key] = q

    out: list[Pocket] = []
    for grid, mapping in zip(grids, per_grid):
        out.extend(_build_pockets(grid, mapping))
    return tuple(sorted(out, key=lambda item: item.design_pnl))


# --------------------------------------------------------------------------- CSV 진입점

@dataclass(frozen=True, slots=True)
class RunColumns:
    """공식 CSV 한 개를 열 단위로 읽어둔 것 — 분할·프로파일·포켓이 공유한다."""

    columns: dict[str, list[float | None]]
    pnls: list[float]
    dates: list[int]
    pool: list[str]


def _read_run(csv_path: Path, variables: Sequence[str] | None) -> RunColumns:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)
    pool = list(variables) if variables else _default_variables(fieldnames)
    columns: dict[str, list[float | None]] = {name: [] for name in pool}
    pnls: list[float] = []
    dates: list[int] = []
    for row in rows:
        pnl = _number(row.get(PNL_COLUMN))
        if pnl is None:
            continue
        pnls.append(pnl)
        dates.append(_buy_date(row.get(BUY_TIME_COLUMN)))
        for name in pool:
            columns[name].append(_derive(row, name))
    return RunColumns(columns=columns, pnls=pnls, dates=dates, pool=pool)


def _buy_date(value: object) -> int:
    text = str(value or "").strip()
    return int(text[:8]) if len(text) >= 8 and text[:8].isdigit() else 0


def split_run(run: RunColumns, split: int) -> tuple[RunColumns, RunColumns]:
    """연속 1회 런을 매수일 기준으로 설계/홀드아웃으로 나눈다(경계일은 홀드아웃).

    평가 프로토콜 v2 의 핵심 — 백테스트를 두 번 돌리지 않는다.
    """
    design_index = [index for index, date in enumerate(run.dates) if date < split]
    holdout_index = [index for index, date in enumerate(run.dates) if date >= split]

    def pick(indices: list[int]) -> RunColumns:
        return RunColumns(
            columns={
                name: [values[index] for index in indices]
                for name, values in run.columns.items()
            },
            pnls=[run.pnls[index] for index in indices],
            dates=[run.dates[index] for index in indices],
            pool=list(run.pool),
        )

    return pick(design_index), pick(holdout_index)


def samples_from(run: RunColumns, variables: Sequence[str]) -> list[Sample]:
    """열 묶음 → Sample 목록. 지정 변수 중 하나라도 결측이면 그 거래는 뺀다."""
    out: list[Sample] = []
    for index, pnl in enumerate(run.pnls):
        values: dict[str, float] = {}
        for name in variables:
            value = run.columns.get(name, [])[index] if name in run.columns else None
            if value is None:
                break
            values[name] = value
        else:
            out.append(Sample(values=values, pnl=pnl, date=run.dates[index]))
    return out


def _read_columns(
    csv_path: Path, variables: Sequence[str] | None,
) -> tuple[dict[str, list[float | None]], list[float], list[str]]:
    run = _read_run(csv_path, variables)
    return run.columns, run.pnls, run.pool


def is_proposable(variable: str) -> bool:
    """조건식 입력으로 제안해도 되는 변수인가.

    `B_*` 는 매수 신호 시점 스냅샷이라 안전하다. 거래기록 원열(`시가총액` 등)은 같은 이름의
    `B_` 열과 값이 다르다 — 매수 시점 확정값이라는 보장이 없으므로 **진단 전용**으로 둔다.
    (`S_*`/`R_*` 는 사후 정보라 애초에 변수 풀에 넣지 않는다.)
    최종 런타임 표현 가능 여부는 G-0b 생성기의 화이트리스트가 판정한다.
    """
    return variable.startswith("B_") or variable in _DERIVED_PROPOSABLE


def _default_variables(fieldnames: Sequence[str]) -> list[str]:
    """B_* 전수 + 시가총액 + 매수시간 파생 시분초 — 사후 정보(R_*/S_*)는 넣지 않는다."""
    pool = [name for name in fieldnames if name.startswith("B_")]
    if "시가총액" in fieldnames:
        pool.append("시가총액")
    # B_시분초 가 있으면 파생 시분초는 같은 축의 중복이다 — 없을 때만 만든다.
    if BUY_TIME_COLUMN in fieldnames and "B_시분초" not in fieldnames:
        pool.append("시분초")
    return pool


def _derive(row: Mapping[str, str], name: str) -> float | None:
    if name == "시분초":
        text = str(row.get(BUY_TIME_COLUMN) or "").strip()
        if len(text) == 14:
            return _number(text[8:])
        if len(text) == 12:
            return _number(text[8:] + "00")
        return None
    return _number(row.get(name))


def profile_payload(
    *,
    design_csv: Path,
    holdout_csv: Path,
    variables: Sequence[str] | None = None,
    min_bucket: int | None = None,
    top: int = 40,
) -> dict[str, object]:
    """공식 CSV 두 개 → 변수별 손실 프로파일(진단 권위)."""
    design = _read_run(design_csv, variables)
    holdout = _read_run(holdout_csv, design.pool)
    return profile_payload_from_runs(
        design=design, holdout=holdout, min_bucket=min_bucket, top=top,
    )


def profile_payload_split(
    *,
    csv_path: Path,
    split: int,
    variables: Sequence[str] | None = None,
    min_bucket: int | None = None,
    top: int = 40,
) -> dict[str, object]:
    """평가 프로토콜 v2 — 연속 1회 런 CSV 하나를 날짜로 나눠 프로파일한다."""
    design, holdout = split_run(_read_run(csv_path, variables), split)
    payload = profile_payload_from_runs(
        design=design, holdout=holdout, min_bucket=min_bucket, top=top,
    )
    payload["split"] = split
    return payload


def profile_payload_from_runs(
    *,
    design: RunColumns,
    holdout: RunColumns,
    min_bucket: int | None = None,
    top: int = 40,
) -> dict[str, object]:
    design_columns, design_pnls, pool = design.columns, design.pnls, design.pool
    holdout_columns, holdout_pnls = holdout.columns, holdout.pnls
    resolved = min_bucket or max(100, int(len(design_pnls) * 0.005))
    minimum_total = max(200, resolved * _MIN_TOTAL_FACTOR)
    if len(design_pnls) < minimum_total or len(holdout_pnls) < minimum_total:
        return {
            "available": False,
            "authority": "diagnostic",
            "reason": "sample_too_small",
            "design_rows": len(design_pnls),
            "holdout_rows": len(holdout_pnls),
            "minimum_total": minimum_total,
        }

    profiles: list[VariableProfile] = []
    for name in pool:
        design_pairs = [
            (value, pnl) for value, pnl in zip(design_columns[name], design_pnls)
            if value is not None
        ]
        holdout_pairs = [
            (value, pnl) for value, pnl in zip(holdout_columns.get(name, []), holdout_pnls)
            if value is not None
        ]
        if len(design_pairs) < minimum_total or not holdout_pairs:
            continue
        profiles.append(
            _profile_series(
                variable=name,
                design_values=[value for value, _ in design_pairs],
                design_pnls=[pnl for _, pnl in design_pairs],
                holdout_values=[value for value, _ in holdout_pairs],
                holdout_pnls=[pnl for _, pnl in holdout_pairs],
                min_bucket=resolved,
            )
        )
    profiles.sort(key=lambda item: item.spread, reverse=True)
    confirmed = [
        item for item in profiles
        if item.confirmed and item.worst_span and item.proposable
    ]
    front = pareto_front(
        [
            {
                "variable": item.variable,
                "removal": item.worst_span.design_share,      # type: ignore[union-attr]
                "gain": item.design_overall - item.worst_span.design_per_trade,  # type: ignore[union-attr]
            }
            for item in confirmed
        ],
        removal_key="removal", gain_key="gain",
    )
    return {
        "available": True,
        "authority": "diagnostic",
        "design_rows": len(design_pnls),
        "holdout_rows": len(holdout_pnls),
        "min_bucket": resolved,
        "tested": len(profiles),
        "confirmed_count": sum(1 for item in profiles if item.confirmed and item.worst_span),
        "proposable_count": len(confirmed),
        "profiles": [asdict(item) for item in profiles[:top]],
        "pareto": list(front),
        "guard": (
            "관찰 통계입니다. 제거 추정치는 재유입을 반영하지 않으므로 순위용이며, "
            "채택 판정은 공식 pair/gate 가 합니다."
        ),
    }
