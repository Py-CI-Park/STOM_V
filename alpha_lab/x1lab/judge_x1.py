"""X1 판정 — 후보별 연도별 C1~C4 + 집계 (봉인본 §7·§14-F2·F3·F4).

기준 A = 챔피언(매수 원본 + 매도 원본) — B1 A_2022/A_2023 재사용.
변형 B = 절 삭제 매수식 + 매도 원본. 판정(전 조건 동시 충족 = X1 후보):

  C1 총수익 부호  : Δ = 총수익(B) − 총수익(A) > 0 (연도별) ∧ 양년 동방향(+).
  C2 거래수 상한  : N_B ≤ N_A × 4 (+300% 초과 = 식붕괴 kill). 하한 없음(삭제=증가).
  C3 MDD 허용    : MDD_B ≤ MDD_A × 1.5 ∧ MDD_B ≤ 15.0 (AND — §14-F3 보수화).
  C4 무오류      : A·B status == "success".

분류: x1_candidate(전 연도 C1~C4) / formula_collapse(C2 위반) / rejected(그 외).
엔진 0회(판정은 metrics json 소비만). B1 ab_judge.py 미러 + 삭제 방향 반전.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Tuple

__all__ = [
    "MDD_ABS_CAP", "MDD_MULT", "TRADE_MULT_CAP", "YEARS",
    "judge_all", "judge_candidate", "judge_year", "render_report",
]

YEARS: Tuple[int, ...] = (2022, 2023)
TRADE_MULT_CAP = 4.0     # C2: N_B ≤ N_A × 4 (+300% 상한, §14-F2).
MDD_MULT = 1.5           # C3: MDD_B ≤ MDD_A × 1.5 (§14-F3).
MDD_ABS_CAP = 15.0       # C3: MDD_B ≤ 15% 절대 캡 (AND, §14-F3).

_TAGS = [
    "① 성능 주장 아님·최종 심판: 엔진 Δ총수익은 발견창(2022-2023) 반사실 진단. "
    "X1 후보 승격은 U-4 감독형 소액 실전(2024/2025 blind 부재 — 실전이 유일 미래 검증).",
    "② 계보·출구 조건부: 절·임계는 2024 선정창을 본 챔피언 계보(buy_sha 348c5181…)의 "
    "역사적 산물. 매도식은 원본 8ef01e0e 고정(변형 무관 대조).",
    "③ 오프라인 방향은 가설: D1 역생산 Δ는 삭제 방향 가설의 근거일 뿐, mean_unsat(유입 EV "
    "아님)·프레임·상호작용 때문에 판정 근거가 아니다 — 판정은 엔진 총수익만.",
    "④ 유입 희소 정직 기술: DROP29/31은 미만족(유입 상한) 3,687/2,122로 희소 — Δ≈0(무효과) "
    "판정도 확정 지식(삭제 무해·무익)이며 개선 실증이 아니다.",
]


def _num(m: Optional[Mapping], key: str) -> Optional[float]:
    """metrics dict 에서 key 추출 — {metrics:{...}} 래핑/평면 둘 다 허용."""
    if m is None:
        return None
    src = m.get("metrics") if isinstance(m.get("metrics"), Mapping) else m
    v = src.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _status(m: Optional[Mapping]) -> Optional[str]:
    if m is None:
        return None
    return m.get("status")


def judge_year(candidate: str, year: int, A: Optional[Mapping],
               B: Optional[Mapping]) -> Dict[str, object]:
    """후보·연도 1셀 판정 — C1~C4 각각 + 셀 verdict."""
    pA, pB = _num(A, "total_profit_krw"), _num(B, "total_profit_krw")
    nA, nB = _num(A, "trade_count"), _num(B, "trade_count")
    mA, mB = _num(A, "mdd_pct"), _num(B, "mdd_pct")
    sA, sB = _status(A), _status(B)

    missing = [k for k, v in (("A", A), ("B", B)) if v is None]
    dprofit = (pB - pA) if (pA is not None and pB is not None) else None

    c1 = dprofit is not None and dprofit > 0
    c2 = (nA is not None and nB is not None and nA > 0 and nB <= nA * TRADE_MULT_CAP)
    c3 = (mA is not None and mB is not None
          and mB <= mA * MDD_MULT and mB <= MDD_ABS_CAP)
    c4 = (sA == "success" and sB == "success")
    collapse = (nA is not None and nB is not None and nA > 0
                and nB > nA * TRADE_MULT_CAP)

    return {
        "candidate": candidate, "year": year, "missing": missing,
        "profit_A": pA, "profit_B": pB, "dprofit_krw": dprofit,
        "trades_A": nA, "trades_B": nB,
        "trade_ratio": (nB / nA) if (nA and nB is not None) else None,
        "mdd_A": mA, "mdd_B": mB, "status_A": sA, "status_B": sB,
        "c1_profit_positive": bool(c1),
        "c2_trade_cap": bool(c2),
        "c3_mdd_ok": bool(c3),
        "c4_error_free": bool(c4),
        "formula_collapse": bool(collapse),
        "cell_pass": bool(c1 and c2 and c3 and c4),
    }


def judge_candidate(candidate: str, A_by_year: Mapping[int, Mapping],
                    B_by_year: Mapping[int, Optional[Mapping]]) -> Dict[str, object]:
    """후보 1종 — 연도별 셀 + 집계(ΣΔ·양년 동방향) + 분류."""
    cells = {yr: judge_year(candidate, yr, A_by_year.get(yr), B_by_year.get(yr))
             for yr in YEARS}
    dprofits = [cells[yr]["dprofit_krw"] for yr in YEARS]
    have_all = all(d is not None for d in dprofits)
    sum_dprofit = sum(d for d in dprofits if d is not None) if have_all else None
    both_year_positive = have_all and all(d > 0 for d in dprofits)
    all_cells_pass = all(cells[yr]["cell_pass"] for yr in YEARS)
    any_collapse = any(cells[yr]["formula_collapse"] for yr in YEARS)

    if any_collapse:
        classification = "formula_collapse"
    elif all_cells_pass and both_year_positive:
        classification = "x1_candidate"
    else:
        classification = "rejected"

    return {
        "candidate": candidate,
        "cells": cells,
        "sum_dprofit_krw": sum_dprofit,
        "both_year_positive": bool(both_year_positive),
        "all_cells_pass": bool(all_cells_pass),
        "classification": classification,
    }


def judge_all(A_by_year: Mapping[int, Mapping],
              B_by_year_by_cand: Mapping[str, Mapping[int, Optional[Mapping]]],
              *, preregistration: str = "2026-07-17_x1_buy_clause_drop_ab_preregistration.md (cb8a9d6a)",
              variant_sha: Optional[Mapping[str, str]] = None,
              smoke: bool = False) -> Dict[str, object]:
    """전 후보 판정 + 결론(X1 후보 유무 → kill-1 대칭 지식)."""
    per = {c: judge_candidate(c, A_by_year, B_by_year_by_cand.get(c, {}))
           for c in B_by_year_by_cand}
    x1 = [c for c, r in per.items() if r["classification"] == "x1_candidate"]
    collapse = [c for c, r in per.items() if r["classification"] == "formula_collapse"]
    rejected = [c for c, r in per.items() if r["classification"] == "rejected"]
    return {
        "kind": "x1_buy_clause_drop_ab_judgment",
        "preregistration": preregistration,
        "baseline_reused": "B1 A_2022/A_2023 (챔피언 매수+매도 원본)",
        "variant_sha256": dict(variant_sha) if variant_sha else {},
        "criteria": {"C1": "Δ총수익>0 양년동방향", "C2": f"N_B≤N_A×{TRADE_MULT_CAP:g}",
                     "C3": f"MDD_B≤MDD_A×{MDD_MULT:g} ∧ ≤{MDD_ABS_CAP:g}%",
                     "C4": "A·B success"},
        "per_candidate": per,
        "x1_candidates": x1,
        "formula_collapse": collapse,
        "rejected": rejected,
        "n_x1_candidates": len(x1),
        # §10-1: 전 후보 미충족 = "매수측도 절 단위 삭제로 개선 안 됨"(매도식 D1과 대칭).
        "kill1_no_x1_candidate": bool(len(x1) == 0),
        "tags": _TAGS,
        "smoke": bool(smoke),
    }


def _fmt_krw(v) -> str:
    return "—" if v is None else f"{v:+,.0f}"


def _pf(b) -> str:
    return "PASS" if b else "FAIL"


def render_report(summary: Mapping[str, object]) -> str:
    L: List[str] = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if summary.get("smoke") else ""
    A(f"# X1 매수식 역생산 절 삭제 엔진 A/B 판정 리포트{tag}")
    A("")
    A(f"> 사전등록: `{summary['preregistration']}` · 기준 A = {summary['baseline_reused']} · "
      "엔진 매도 원본 8ef01e0e 고정 · 2024/2025 미접촉")
    A("")
    A("## 0. 결론 먼저")
    A("")
    if summary.get("smoke"):
        A("> 스모크 — 파이프라인 검증용, 판정 아님.")
        A("")
    n_x1 = summary["n_x1_candidates"]
    if n_x1:
        A(f"**X1 후보 {n_x1}건 발견**: {summary['x1_candidates']} — 삭제로 총수익 개선 "
          "∧ MDD 비악화 ∧ 거래수 상한 이내. U-4 감독형 소액 실전 대상(별도 승인).")
    else:
        A("**X1 후보 0건** — 4후보 전부 미충족. §10-1대로 \"매수측도 절 단위 삭제로 "
          "개선 안 됨\" 확정. 매도식 D1(뺄 것 없음)과 합쳐 **입·출구 모두 절 단위 국소 "
          "최적 — 개선은 추가·조합뿐** 대칭 확정 지식.")
    if summary["formula_collapse"]:
        A(f"- 식붕괴(거래수 >×{TRADE_MULT_CAP:g}): {summary['formula_collapse']}")
    A("")
    A("## 1. 후보별 판정표 (연도별 C1~C4 + 집계)")
    A("")
    A("| 후보 | 연도 | 총수익 A | 총수익 B | Δ총수익 | 거래 A→B(배) | MDD A→B | C1 | C2 | C3 | C4 | 셀 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    per = summary["per_candidate"]
    for c in per:
        r = per[c]
        for yr in YEARS:
            e = r["cells"][yr]
            ratio = f"{e['trades_A']:.0f}→{e['trades_B']:.0f}" if e["trades_A"] is not None and e["trades_B"] is not None else "—"
            rmul = f"(×{e['trade_ratio']:.2f})" if e["trade_ratio"] is not None else ""
            mdd = f"{e['mdd_A']:.2f}→{e['mdd_B']:.2f}" if e["mdd_A"] is not None and e["mdd_B"] is not None else "—"
            A(f"| {c} | {yr} | {_fmt_krw(e['profit_A'])} | {_fmt_krw(e['profit_B'])} | "
              f"{_fmt_krw(e['dprofit_krw'])} | {ratio}{rmul} | {mdd} | "
              f"{_pf(e['c1_profit_positive'])} | {_pf(e['c2_trade_cap'])} | "
              f"{_pf(e['c3_mdd_ok'])} | {_pf(e['c4_error_free'])} | "
              f"{'PASS' if e['cell_pass'] else '—'} |")
        A(f"| **{c}** | 집계 | | | **{_fmt_krw(r['sum_dprofit_krw'])}** | | | "
          f"양년+={r['both_year_positive']} | | | | **{r['classification']}** |")
    A("")
    A("## 2. 딱지 (강제 인쇄 — §9)")
    A("")
    for t in summary["tags"]:
        A(f"- {t}")
    A("")
    A("*엔진 A/B = 발견창(2022-2023) · 기준 A 재사용(추가 엔진 0) · scratch DB(실 DB 미접촉) · "
      "git 커밋 없음 · X1 후보 승격 = U-4 감독형 소액 실전.*")
    return "\n".join(L) + "\n"
