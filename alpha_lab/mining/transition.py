"""규칙 전이 샘플러 — FALSE→TRUE 전이(onset) 추출 + 전이 기준 EV 재측정 (v3 P1).

RC-2(그리드 표본 ≠ 엔진 발화 프로필) 처방: 엔진 조건식은 상태가 참인 구간
동안 연속 발화하지만 진입 기회의 단위는 '거짓→참 전이(onset)'다. 본 모듈은
종목-일 시계열 안에서 규칙 마스크의 onset만 추출하고, 그 시점 라벨로
EV·95% CI·일평균 전이율을 재측정한다
(preregistration_v3.json 봉인 50d3d38a — sampling.transition_recheck,
adoption_ev.transition_rate_per_day=[5,60]).

재사용 규율(중복 구현 금지):
- ndarray+리프 dict 마스크 재구성은 alpha_lab.mining.stats.rule_mask.
- EV/CI/p는 alpha_lab.stats_common.day_block_bootstrap(stat='mean').

입력 전제: 표본이 (일, 종목) 시리즈별로 '연속 블록'이고 시리즈 안에서 시간
오름차순이어야 한다 — dataset 캐시(load_shards: 일 샤드 순 → 종목 순 →
t0 순)가 이 배치를 그대로 만족한다. 시리즈 비연속은 ValueError로 거부하고,
시리즈 경계에서는 이전 상태를 이월하지 않는다(첫 행 TRUE = 새 onset).
"""
from __future__ import annotations

import logging
from typing import Dict, Mapping, Sequence, Tuple, Union

import numpy as np

from alpha_lab.mining.stats import rule_mask
from alpha_lab.stats_common import day_block_bootstrap

__all__ = [
    "TRANSITION_RATE_BUDGET",
    "extract_transitions",
    "measure_transition_ev",
    "series_ids_from",
    "state_mask",
    "transition_mask",
]

logger = logging.getLogger(__name__)

# preregistration_v3.adoption_ev.transition_rate_per_day 봉인값 — 일평균
# 전이(발화 기회) 예산 [하한, 상한].
TRANSITION_RATE_BUDGET: Tuple[float, float] = (5.0, 60.0)

_OPS = ("<=", ">")

RowsOrX = Union[np.ndarray, Sequence[Mapping[str, object]]]
Rule = Union[Mapping[str, object], Sequence[Tuple[object, str, float]]]


def series_ids_from(dates, codes) -> np.ndarray:
    """(date, code) 쌍 → 'YYYYMMDD:code' 시리즈 키 배열 (종목-일 경계 식별).

    캐시 배열(date int32, code '<U6')을 그대로 받아 transition_mask /
    extract_transitions의 series_ids로 쓸 수 있게 한다.
    """
    date_str = np.asarray(dates).astype(str)
    code_str = np.asarray(codes).astype(str)
    if date_str.shape != code_str.shape or date_str.ndim != 1:
        raise ValueError("dates/codes는 같은 길이의 1차원이어야 한다")
    return np.char.add(np.char.add(date_str, ":"), code_str)


def _clause_op_mask(values: np.ndarray, op: str, thr: float) -> np.ndarray:
    if op not in _OPS:
        raise ValueError(f"지원하지 않는 연산자: {op!r} (허용: {_OPS})")
    return (values <= thr) if op == "<=" else (values > thr)


def _rows_clause_mask(
    rows: Sequence[Mapping[str, object]],
    clauses: Sequence[Tuple[object, str, float]],
) -> np.ndarray:
    mask = np.ones(len(rows), dtype=bool)
    for name, op, thr in clauses:
        try:
            values = np.asarray(
                [float(row[name]) for row in rows], dtype=np.float64
            )
        except KeyError as exc:
            raise ValueError(f"행에 절 피처 {name!r}가 없다") from exc
        mask &= _clause_op_mask(values, op, float(thr))
    return mask


def _ndarray_clause_mask(
    X: np.ndarray, clauses: Sequence[Tuple[object, str, float]]
) -> np.ndarray:
    mask = np.ones(X.shape[0], dtype=bool)
    for col, op, thr in clauses:
        if isinstance(col, str):
            raise ValueError(
                "ndarray 입력의 절 목록은 정수 열 인덱스여야 한다 — "
                "피처명 절은 리프 dict(rule_cols) 또는 rows(dict) 입력을 쓰라"
            )
        mask &= _clause_op_mask(X[:, int(col)], op, float(thr))
    return mask


def state_mask(rows_or_X: RowsOrX, rule: Rule) -> np.ndarray:
    """규칙 conjunction의 상태(TRUE/FALSE) bool 마스크.

    - X(ndarray 2차원) + 리프 dict(rule/rule_cols): mining.stats.rule_mask
      재사용 — evaluate_leaves와 동일한 float32 의미론으로 캐스팅한다.
    - X(ndarray) + 절 목록 [(열 인덱스, '<='|'>', thr)].
    - rows(Mapping 시퀀스) + 절 목록 [(피처명, op, thr)] 또는 리프 dict
      (리프의 rule 피처명으로 평가).
    """
    if isinstance(rows_or_X, np.ndarray):
        X = np.asarray(rows_or_X, dtype=np.float32)
        if X.ndim != 2:
            raise ValueError(f"X는 2차원 배열이어야 한다: shape={X.shape}")
        if isinstance(rule, Mapping):
            return rule_mask(X, dict(rule))
        return _ndarray_clause_mask(X, list(rule))
    rows = list(rows_or_X)
    clauses = list(rule["rule"]) if isinstance(rule, Mapping) else list(rule)
    return _rows_clause_mask(rows, clauses)


def transition_mask(mask, series_ids=None) -> np.ndarray:
    """상태 마스크 → FALSE→TRUE 전이(onset) bool 마스크.

    시리즈 첫 행은 이전 상태가 없으므로 TRUE면 onset이다. series_ids가
    주어지면 시리즈 경계에서 이전 상태를 이월하지 않으며, 같은 시리즈가
    흩어져 있으면(비연속) ValueError — (일, 종목) 그룹 연속 정렬이 전제다.
    """
    state = np.asarray(mask, dtype=bool)
    if state.ndim != 1:
        raise ValueError(f"mask는 1차원이어야 한다: shape={state.shape}")
    if state.size == 0:
        return np.zeros(0, dtype=bool)
    starts = np.zeros(state.shape[0], dtype=bool)
    starts[0] = True
    if series_ids is not None:
        sid = np.asarray(series_ids)
        if sid.ndim != 1 or sid.shape[0] != state.shape[0]:
            raise ValueError(
                f"series_ids 길이({sid.shape})가 mask({state.shape})와 다르다"
            )
        changed = sid[1:] != sid[:-1]
        starts[1:] = changed
        n_runs = int(changed.sum()) + 1
        n_unique = int(np.unique(sid).size)
        if n_runs != n_unique:
            raise ValueError(
                "series_ids가 비연속이다(같은 시리즈가 흩어져 있음) — "
                "(일, 종목) 그룹 연속 정렬 후 호출하라"
            )
    prev = np.empty_like(state)
    prev[0] = False
    prev[1:] = state[:-1]
    prev[starts] = False  # 시리즈 첫 행: 이전 상태 이월 금지.
    return state & ~prev


def extract_transitions(
    rows_or_X: RowsOrX, rule: Rule, *, series_ids=None
) -> np.ndarray:
    """규칙의 FALSE→TRUE 전이 시점 인덱스(int64, 오름차순)를 추출한다.

    입력 형태·시리즈 경계 규칙은 state_mask/transition_mask 계약을 따른다.
    반환 인덱스는 rows_or_X 행 축 기준이다(라벨·day_ids와 같은 축).
    """
    onsets = transition_mask(state_mask(rows_or_X, rule), series_ids)
    return np.flatnonzero(onsets)


def _validate_measure_inputs(
    n: int, y: np.ndarray, day_ids: np.ndarray
) -> None:
    if y.ndim != 1 or day_ids.ndim != 1:
        raise ValueError("y/day_ids는 1차원 배열이어야 한다")
    if y.shape[0] != n or day_ids.shape[0] != n:
        raise ValueError(
            f"y({y.shape[0]})/day_ids({day_ids.shape[0]}) 길이가 표본수({n})와 다르다"
        )


def measure_transition_ev(
    rows_or_X: RowsOrX,
    rule: Rule,
    y,
    day_ids,
    *,
    series_ids=None,
    n_boot: int = 1000,
    seed: int = 20260707,
    rate_budget: Union[Tuple[float, float], None] = TRANSITION_RATE_BUDGET,
) -> Dict[str, object]:
    """전이(onset) 시점만으로 일평균 전이율·EV·95% CI·p를 재측정한다.

    EV/CI/p는 stats_common.day_block_bootstrap(stat='mean')을 onset 마스크로
    호출한 값(일중 상관 보존). 일평균 전이율 = 전이수 / 전체 고유 일수
    (전이 0인 날도 분모에 포함 — 발화 예산의 정직한 분모). rate_budget
    (기본 봉인 [5,60])이 None이 아니면 rate_in_budget 판정을 포함한다.

    반환 키: n, n_state_true, n_transitions, n_days, transitions_per_day,
    ev, ci_low, ci_high, p, rate_budget, rate_in_budget, n_boot, seed.
    여러 후보를 측정할 때 시드는 호출측이 후보별로 분리하라(예: seed+i —
    ev_adopt.adopt_by_ev와 같은 관례).
    """
    state = state_mask(rows_or_X, rule)
    y_arr = np.asarray(y, dtype=np.float64)
    day_arr = np.asarray(day_ids)
    _validate_measure_inputs(int(state.shape[0]), y_arr, day_arr)
    onsets = transition_mask(state, series_ids)
    boot = day_block_bootstrap(
        day_arr, y_arr, onsets, n_boot=n_boot, seed=seed, stat="mean"
    )
    n_days = int(np.unique(day_arr).size)
    n_transitions = int(onsets.sum())
    rate = (n_transitions / n_days) if n_days else float("nan")
    if rate_budget is None:
        budget_list = None
        in_budget = None
    else:
        low, high = (float(rate_budget[0]), float(rate_budget[1]))
        budget_list = [low, high]
        in_budget = bool(np.isfinite(rate) and low <= rate <= high)
    result: Dict[str, object] = {
        "n": int(state.shape[0]),
        "n_state_true": int(state.sum()),
        "n_transitions": n_transitions,
        "n_days": n_days,
        "transitions_per_day": float(rate),
        "ev": float(boot["point"]),
        "ci_low": float(boot["ci_low"]),
        "ci_high": float(boot["ci_high"]),
        "p": float(boot["p_one_sided"]),
        "rate_budget": budget_list,
        "rate_in_budget": in_budget,
        "n_boot": int(n_boot),
        "seed": int(seed),
    }
    logger.info(
        "measure_transition_ev n=%d state=%d onsets=%d days=%d rate=%.3f "
        "ev=%.6f ci=[%.6f, %.6f] p=%.4f in_budget=%s",
        result["n"], result["n_state_true"], n_transitions, n_days, rate,
        result["ev"], result["ci_low"], result["ci_high"], result["p"],
        in_budget,
    )
    return result
