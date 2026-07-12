"""R1 포렌식 — t=T 영향 모집단·표본 하한 자격·time_stop 도움/해악 map·kill-1.

봉인 근거: 2026-07-12_d5r_conditional_exit_preregistration.md §5·§6·§10.1.

엔진 0회 — pipeline.evaluate_trades 레코드(현직·t=T 상태·후보 패치)만 소비한다.
kill-1(레짐 위장): time_stop 도움/해악이 보유상태로 분리 안 되고 순수 연도
효과로만 설명되면 발동. 여기서는 (best_T, sp_T) 상태 격자 × 연도 분해로
"저활력 셀 절단 이득 > 승자 셀 절단 이득"이 두 연도 모두 성립하는지로 판정한다.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

__all__ = [
    "BEST_BINS",
    "family_a_population",
    "family_b_population",
    "help_hurt_map",
    "kill1_verdict",
    "lower_bound_table",
]

logger = logging.getLogger(__name__)

# 상태 격자 best_T 경계 — 후보 x 문턱(1.0/1.5)·트레일 arm(3.0)에 정렬.
BEST_BINS: Tuple[Tuple[str, float, float], ...] = (
    ("best<1.0", 0.0, 1.0),
    ("1.0<=best<1.5", 1.0, 1.5),
    ("1.5<=best<3.0", 1.5, 3.0),
    ("best>=3.0", 3.0, float("inf")),
)


def _yr_counts(records: Sequence[Mapping]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for r in records:
        out[r["year"]] = out.get(r["year"], 0) + 1
    return dict(sorted(out.items()))


def family_b_population(
    deduped: Sequence[Mapping], T: int, x: float, y: float
) -> List[dict]:
    """§5 측정 시점 규칙: held≥T ∧ best_T<x ∧ sp_T<y (t=T 상태 정의)."""
    out = []
    for r in deduped:
        cell = r["per_T"][T]
        if cell["held"] == 1 and cell["best_T"] < x and cell["sp_T"] < y:
            out.append(r)
    return out


def family_a_population(deduped: Sequence[Mapping]) -> List[dict]:
    """Family A 자연 모집단 = 현직 트레일링 절(절5)로 청산된 거래."""
    return [r for r in deduped if r["inc_cond"] == 5]


def lower_bound_table(
    deduped: Sequence[Mapping], candidates: Sequence, *,
    b_min: int = 150, b_min_year: int = 40, a_min: int = 100, a_min_year: int = 30,
) -> List[dict]:
    """후보별 표본 하한 자격(§5.1 하드 백스톱) — 미달 셀 = inconclusive(kill-2)."""
    rows: List[dict] = []
    for p in candidates:
        if p.family == "B":
            pop = family_b_population(deduped, int(p.T), float(p.x), float(p.y))
            yc = _yr_counts(pop)
            qualifies = (len(pop) >= b_min and yc.get(2022, 0) >= b_min_year
                         and yc.get(2023, 0) >= b_min_year)
            need = f"pop>={b_min} ∧ 연>={b_min_year}"
        else:  # Family A
            pop = family_a_population(deduped)
            yc = _yr_counts(pop)
            qualifies = (len(pop) >= a_min and yc.get(2022, 0) >= a_min_year
                         and yc.get(2023, 0) >= a_min_year)
            need = f"pop>={a_min} ∧ 연>={a_min_year}"
        rows.append({
            "candidate": p.label, "family": p.family,
            "population_def": "held≥T ∧ best_T<x ∧ sp_T<y" if p.family == "B"
            else "inc_cond==5(trailing)",
            "n_pop": len(pop), "n_2022": yc.get(2022, 0), "n_2023": yc.get(2023, 0),
            "backstop": need, "qualifies": bool(qualifies),
            "verdict": "qualified" if qualifies else "inconclusive(kill-2)",
        })
    return rows


def _best_bin(best_T: float) -> str:
    for name, lo, hi in BEST_BINS:
        if lo <= best_T < hi:
            return name
    return BEST_BINS[-1][0]


def help_hurt_map(deduped: Sequence[Mapping], Ts: Sequence[int]) -> Dict[int, dict]:
    """T별 보유≥T 모집단을 (best_T bin × sp_T 부호) 격자로 분해 — 연도별 절단이득.

    절단이득 = cut_pct − inc_pct (양수=현직보다 절단이 이득). 각 셀에 전체·연도별
    n·평균 절단이득·평균 잔여EV(=inc_pct−cut_pct, 보유 지속의 기대이득)를 담는다.
    """
    out: Dict[int, dict] = {}
    for T in Ts:
        held = [r for r in deduped if r["per_T"][T]["held"] == 1]
        cells: Dict[Tuple[str, str], dict] = {}
        for r in held:
            c = r["per_T"][T]
            if not np.isfinite(c["cut_pct"]):
                continue
            benefit = float(c["cut_pct"]) - float(r["inc_pct"])
            key = (_best_bin(float(c["best_T"])), "sp<0" if c["sp_T"] < 0 else "sp>=0")
            bucket = cells.setdefault(key, {"all": [], 2022: [], 2023: []})
            bucket["all"].append(benefit)
            bucket[r["year"]].append(benefit)
        grid = []
        for (bb, ss), b in sorted(cells.items()):
            grid.append({
                "best_bin": bb, "sp_sign": ss,
                "n": len(b["all"]),
                "n_2022": len(b[2022]), "n_2023": len(b[2023]),
                "mean_cut_benefit": round(float(np.mean(b["all"])), 4) if b["all"] else None,
                "mean_benefit_2022": round(float(np.mean(b[2022])), 4) if b[2022] else None,
                "mean_benefit_2023": round(float(np.mean(b[2023])), 4) if b[2023] else None,
            })
        out[T] = {"n_held": len(held), "grid": grid}
    return out


def kill1_verdict(
    deduped: Sequence[Mapping], Ts: Sequence[int], *,
    low_best: float = 1.5, win_best: float = 3.0,
) -> dict:
    """kill-1 판정 — 절단 도움/해악이 보유상태로 분리되는가(vs 순수 연도).

    저활력 셀 = best_T<low_best ∧ sp_T<0. 승자 셀 = best_T>=win_best.
    분리 성립(kill-1 미발동) 조건: 저활력 절단이득 > 승자 절단이득 이 **두 연도
    모두** 성립(상태 의존이 연도 내에서 재현). 어느 연도라도 위배 → 순수 연도
    효과 배제 불가 = kill-1 발동. 대표 T 는 모든 T 에서 검사하고 종합한다.
    """
    per_T: Dict[int, dict] = {}
    separating_T: List[int] = []
    fragile_T: List[int] = []
    for T in Ts:
        held = [r for r in deduped if r["per_T"][T]["held"] == 1
                and np.isfinite(r["per_T"][T]["cut_pct"])]

        def bucket(pred):
            vals = {2022: [], 2023: []}
            for r in held:
                c = r["per_T"][T]
                if pred(c):
                    vals[r["year"]].append(float(c["cut_pct"]) - float(r["inc_pct"]))
            return vals

        low = bucket(lambda c: c["best_T"] < low_best and c["sp_T"] < 0)
        win = bucket(lambda c: c["best_T"] >= win_best)
        rec = {"T": T}
        sep_years = []
        for yr in (2022, 2023):
            lv = float(np.mean(low[yr])) if low[yr] else float("nan")
            wv = float(np.mean(win[yr])) if win[yr] else float("nan")
            rec[f"low_benefit_{yr}"] = round(lv, 4) if np.isfinite(lv) else None
            rec[f"win_benefit_{yr}"] = round(wv, 4) if np.isfinite(wv) else None
            rec[f"n_low_{yr}"] = len(low[yr])
            rec[f"n_win_{yr}"] = len(win[yr])
            # 분리: 저활력 이득>0 이면서 승자 이득보다 큼(승자 표본 없으면 이득>0로 완화).
            if np.isfinite(lv) and lv > 0 and (not np.isfinite(wv) or lv > wv):
                sep_years.append(True)
            else:
                sep_years.append(False)
        rec["separates_both_years"] = bool(all(sep_years))
        (separating_T if rec["separates_both_years"] else fragile_T).append(int(T))
        per_T[T] = rec
    # kill-1(즉시 종료) = 어느 T 에서도 상태-강건 분리가 없음(레짐으로만 설명).
    # 어느 한 T 라도 두 연도 분리 성립하면 순수 레짐 아님 → 미발동. 단 분리 실패
    # T(2023 부호 반전)는 레짐-취약으로 별도 표기(장기 T 후보의 연도 비일관성).
    kill1_fires = len(separating_T) == 0
    return {
        "kill1_fires": bool(kill1_fires),
        "criterion": ("저활력(best_T<1.5 ∧ sp_T<0) 절단이득 > 승자(best_T>=3.0) "
                      "절단이득 이 2022·2023 모두 성립하면 상태-강건 분리. 어느 T "
                      "라도 성립하면 순수 레짐 아님(kill-1 미발동); 실패 T 는 레짐-취약."),
        "state_robust_T": separating_T,
        "regime_fragile_T": fragile_T,
        "per_T": per_T,
    }
