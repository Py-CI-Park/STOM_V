"""D1 2절 교호작용 — 산출물 조립·렌더 (봉인본 §9·§11·§14-F3).

Legacy n_trials ledger writes are retired; report and analysis APIs remain read-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Mapping


__all__ = [
    "CONTAMINATION_LABEL", "LegacyEvidenceWriteBlockedError",
    "build_gate_report", "build_summary", "render_report",
]

class LegacyEvidenceWriteBlockedError(RuntimeError):
    """Raised when retired D1-pair evidence-writing compatibility API is called."""


CONTAMINATION_LABEL = (
    "본 결과의 절 집합(RR8_12 매수식)은 2024 선정창을 포함해 튜닝된 역사적 산물이다"
    "(창-지위 원장 §2 v4 계열). 발견되는 절 효과는 이 시드 계보"
    "(rr8_12_turnover_min_902_1.5, buy_sha 348c5181…)에 조건부인 진단이며, (a) 새 전략 "
    "성능 주장이 아니고, (b) 절의 보편적 유효성 주장이 아니며, (c) 다른 출구를 쓰면 지도가 "
    "달라진다(L3는 RR8_12 출구 조건부). 교호작용 효과 I도 동일하게 이 계보·이 출구에 "
    "조건부다 — 시너지 짝을 원-임계 그대로 신규 조건식에 이식하는 것은 금지되며(과적합 "
    "계승), O-4 승격은 별도 트랙의 임계 재도출·재검정을 거친다."
)
_PREREG = "2026-07-12_d1_pairwise_interaction_preregistration.md (e1c12697)"


def build_gate_report(integrity: Mapping, qualification: Mapping) -> Dict[str, object]:
    """무결성 + 자격 게이트 → gate_report.json 페이로드(L3 접촉 전 산출)."""
    return {
        "kind": "d1_pairwise_gate_report",
        "generated": datetime.now(timezone.utc).isoformat(),
        "preregistration": _PREREG,
        "integrity": dict(integrity),
        "qualification": dict(qualification),
        "contamination_label": CONTAMINATION_LABEL,
    }


def build_summary(judgment: Mapping, gate: Mapping,
                  reproduction: Mapping) -> Dict[str, object]:
    """짝별 정본 + 게이트·재현 메타 → interaction_summary.json 페이로드."""
    return {
        "kind": "d1_pairwise_interaction_summary",
        "generated": datetime.now(timezone.utc).isoformat(),
        "preregistration": _PREREG,
        "window": "2022-03-23~2023-12-31 (발견창, 측정창=2개 연도)",
        "seed": judgment["per_pair"][next(iter(judgment["per_pair"]))]["seed"]
        if judgment["per_pair"] else None,
        "reproduction_gate": dict(reproduction),
        "qualification": {
            "n_pairs_total": gate["qualification"]["n_pairs_total"],
            "n_qualified": gate["qualification"]["n_qualified"],
            "fdr_denominator": gate["qualification"]["fdr_denominator"],
            "qualified_pairs": gate["qualification"]["qualified_pairs"],
        },
        "judgment": judgment,
        "contamination_label": CONTAMINATION_LABEL,
    }


def _fmt(v, nd=4):
    return "—" if v is None else f"{v:+.{nd}f}"


def _sgn(s):
    return {1: "+", -1: "−", 0: "·"}.get(s, "·")


def render_report(summary: Mapping, *, smoke: bool = False) -> str:
    """interaction_summary → 판정표·족-짝·미검출 열거·딱지 리포트(md)."""
    j = summary["judgment"]
    per = j["per_pair"]
    q = summary["qualification"]
    L: List[str] = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if smoke else ""
    A(f"# D1 2절 교호작용 — 측정 리포트{tag}")
    A("")
    A(f"> 사전등록 봉인본: `{summary['preregistration']}` · 측정창 {summary['window']} · "
      f"seed {summary.get('seed')} · 엔진 백테 0회 · 원본 read-only")
    A("")
    A("## 0. 결론 먼저")
    A("")
    verdict = ("**kill-1 — 검정한 2절 짝에서 초가산 구조 미검출**" if j["kill1_no_interaction_detected"]
               else f"**시너지 {len(j['synergy_pairs'])}짝 · 간섭 {len(j['interference_pairs'])}짝**")
    A(f"{verdict}. 자격 짝 {q['n_qualified']}개(전체 39 중)를 2×2 DiD로 검정 — "
      f"|I| ≥ 0.10%p · BH-FDR q=0.10(분모 {j['fdr_denominator']}) · 일자블록 CI 부호 일정 · "
      f"연도 동부호 동시 적용. 족-짝 계상: 시너지 족 {j['n_synergy_families']} · "
      f"간섭 족 {j['n_interference_families']}(상한 {j['family_pair_cap']}).")
    A("")
    if j["kill1_no_interaction_detected"]:
        A("§10 kill-1(서술 한정): 이는 **\"검정한 2절 짝에서 ±0.10%p 이상의 교호작용 미검출\"**"
          "이지 \"조합 엣지 부재\"가 아니다. 미검출 짝(표본 희소·검출력 부족)을 아래 열거하며, "
          "VI 상대가·잔량비 족 축은 애초에 판정 불가였음을 명기한다. 3절 이상 구조는 본 검정의 "
          "시야 밖(후속 별도 봉인).")
        A("")
    # 판정표(자격 짝).
    A("## 1. 판정표 (자격 짝)")
    A("")
    A("| 짝 | 족-짝 | μ00/01/10/11 | Δ_A | Δ_B | Δ_AB | I(%p) | 일자블록 CI | 연도(22/23) | "
      "양측p | FDR | MDE | 분류 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in per:
        r = per[k]
        yi = r["year_I"]
        mu = "/".join(_fmt(m, 3).lstrip("+") if m is not None else "—" for m in r["mu_pp"])
        A(f"| {k} | {r['family_pair']} | {mu} | {_fmt(r['delta_A_pp'])} | "
          f"{_fmt(r['delta_B_pp'])} | {_fmt(r['delta_AB_pp'])} | {_fmt(r['I_pp'])} | "
          f"[{_fmt(r['ci_low_pp'])}, {_fmt(r['ci_high_pp'])}] | "
          f"{_sgn(yi[2022]['sign'])}{_sgn(yi[2023]['sign'])} | {r['p_two_sided']:.4f} | "
          f"{'생존' if r['fdr_survive'] else '—'} | {_fmt(r['mde_pp'])} | {r['classification']} |")
    A("")
    # 미검출 열거(§10 kill-1 서술 의무).
    A("## 2. 미검출 열거 (§10 서술 한정 — '효과 없음' 아님)")
    A("")
    gate_pairs = summary["qualification"]
    qualified = set(gate_pairs["qualified_pairs"])
    A(f"- **표본 희소(자격 미달, 분모 제외)**: 전체 39짝 − 자격 {len(qualified)}짝 = "
      f"**{39 - len(qualified)}짝** — 게이트 계수표(gate_report.json)에 셀 계수와 함께 전량 열거. "
      "특히 VI 상대가(#10)·잔량비(#29·#31) 족 축은 산술 확정 판정 불가(§5.2).")
    A(f"- **검출력 부족(자격·비유의·MDE>0.10%p)**: {j['undetected_power_pairs'] or '없음'} "
      "— \"효과 없음\" 주장 금지(검정은 수행됨).")
    A(f"- **무검출·가산 적합(MDE≤0.10%p)**: {j['no_detect_additive_pairs'] or '없음'} "
      "— \"±0.10%p 이상 교호작용 없음(검출력 충분)\" 주장 가능.")
    A(f"- **약대역(보고만)**: {j['weak_signal_pairs'] or '없음'}")
    A("")
    A(f"- **sanity anchor(§10)**: 전 짝 |I|<0.005%p 완전 평탄 = {j['sanity_anchor_tripped']} "
      + ("→ **파이프라인 결함 의심, 짝 1개 100행 손계산 대조 필수**"
         if j["sanity_anchor_tripped"] else "(미발동)"))
    A("")
    A(f"> **딱지(강제 인쇄, §9)**: {CONTAMINATION_LABEL}")
    A("")
    A("*엔진 백테 0회 · 원본 DB read-only · 신규 비트 산출 0 · 2024/2025 미접촉(경로상 0). "
      "전 짝 무검출 시 해석은 §2·§10대로 \"검정한 2절 짝에서 초가산 구조 미검출\"이지 "
      "\"조합 엣지 부재\"가 아니다.*")
    return "\n".join(L) + "\n"


def append_n_trials(*_args, **_kwargs) -> None:
    """Retired compatibility shim; legacy D1-pair ledger writes are prohibited."""
    raise LegacyEvidenceWriteBlockedError(
        "legacy-evidence-write-blocked: D1-pair legacy ledger writes are retired; "
        "use the authenticated v2 evidence chain"
    )
