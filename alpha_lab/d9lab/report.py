"""D9 산출물 렌더 — R1/R3 마크다운 리포트 + n_trials 원장 append (봉인본 §11·§14-9).

강제 딱지(§9): known-오염(L3=RR8_12 출구 조건부, 청산 레버 2024 known) + 잔여 불확실성
(클램프·결측 초·2개 연도 얇음). R3 판정표는 결론 먼저·쉬운 설명 병기.
n_trials 는 측정 완료 시 3건(type-b, 분모 3 고정) append(§14-9, 선계상 없음).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Mapping

from alpha_lab.discipline import ledger

__all__ = ["CONTAMINATION_LABEL", "append_n_trials", "render_r1_report", "render_r3_report"]

CONTAMINATION_LABEL = (
    "본 결과의 채점 라벨(L3)은 챔피언 RR8_12 출구(sell_sha 8ef01e0e…, 청산 레버·v4 계열)로 "
    "팔았을 때의 실현 손익이며, 이 출구 계열은 2024·2025가 known 이다. 따라서 발견되는 전이 "
    "온셋 EV 구조는 (a) 이 출구 렌즈에서의 진단이지 보편 진입 신호가 아니고, (b) 다른 출구를 "
    "쓰면 지도가 달라지며, (c) moneytop 유니버스 구성 자체는 시장이 결정한 것이라 외적 타당성 "
    "주장은 하지 않는다. 잔여 불확실성: 관심종목N(60) 클램프(미관측 온셋 별도 bin), 결측 초 "
    "(60틱 > 60초), 발견창 2개 연도뿐(얇음)."
)


def _fmt(v, nd=4):
    return "—" if v is None else f"{v:+.{nd}f}"


def render_r1_report(summary: Mapping[str, object], *, smoke: bool = False) -> str:
    """R1 summary → 패리티·재현·겹침·서브모집단·하한 리포트(md)."""
    c = summary["consolidate"]
    ov = summary["overlap"]
    rep = summary["reproduction_gate"]
    L: List[str] = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if smoke else ""
    A(f"# D5 · D9 전이 온셋 R1 추출 리포트{tag}")
    A("")
    A(f"> 사전등록: `{summary['preregistration']}` · 측정 일수 {summary['days_measured']} · "
      f"엔진 백테 0회 · 원본 read-only")
    A("")
    A("## 0. 게이트 요약 (결론 먼저)")
    A("")
    A(f"- **패리티 게이트(§14-7)**: 저장 플래그 vs GT 일치 {c['parity_n_match']:,}/{c['parity_n_rows']:,} "
      f"= {_pct(c['parity_match_pct'])} → gate_pass={c['parity_gate_pass']} "
      f"{'(≥99.9% — R3 진입 허용)' if c['parity_gate_pass'] else '(<99.9% — R3 진입 금지 정지 규칙)'}")
    A(f"- **재현 게이트(§4.2)**: 순수/벡터 L3 일치 = reproduction_pass={rep.get('reproduction_pass')}")
    A(f"- **겹침 게이트(§8, ±30 pooled)**: {_pct(ov.get('primary_pooled_rate'))} (상한 0.50) → "
      f"gate_pass={ov.get('gate_pass')}")
    A("")
    A("## 1. 서브모집단 센서스 (관측가능·라벨)")
    A("")
    A(f"- 전이 온셋 총 {c['n_onsets']:,} · 관측가능(≥60) {c['n_observable']:,} "
      f"(신규 {c['n_new_obs']:,} · 재진입 {c['n_reentry_obs']:,}) · L3 라벨 {c['n_labeled_obs']:,}")
    A("")
    A("| 서브모집단 | n(관측·라벨) | 2022 | 2023 | 하한(총/연) | 하한통과 |")
    A("|---|---|---|---|---|---|")
    for name in ("new", "reentry", "pooled"):
        f = c["floors"][name]
        A(f"| {name} | {f['n']:,} | {f['n_2022']:,} | {f['n_2023']:,} | "
          f"{f['floor_total']}/{f['floor_year']} | {f['floor_pass']} |")
    A("")
    A("## 2. 겹침률 (window별 × 서브모집단, §14-2)")
    A("")
    A("| window(±초) | pooled | new | reentry |")
    A("|---|---|---|---|")
    for w in ("0", "30", "60"):
        pw = ov["per_window"].get(w, {})
        A(f"| {w} | {_pct(_rate(pw, 'pooled'))} | {_pct(_rate(pw, 'new'))} | "
          f"{_pct(_rate(pw, 'reentry'))} |")
    A("")
    A(f"> **딱지(강제 인쇄, §9)**: {CONTAMINATION_LABEL}")
    A("")
    A("*엔진 백테 0회 · 원본 DB read-only · git 커밋 없음 · 2024/2025 미접촉. "
      "산출: d9_transition_bank.parquet(git 제외 파티션, onset_l3_bank 원본 불변).*")
    return "\n".join(L) + "\n"


def render_r3_report(result: Mapping[str, object], *, smoke: bool = False) -> str:
    """R3 result → 서브모집단 Δ 판정표 리포트(md)."""
    L: List[str] = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if smoke else ""
    A(f"# D5 · D9 전이 온셋 R3 대조 리포트{tag}")
    A("")
    A(f"> 사전등록: `{result['preregistration']}` · 엔진 백테 0회")
    A("")
    A("## 0. 결론 먼저")
    A("")
    if not result["proceed_to_judgment"]:
        A(f"**판정 정지** — {result.get('halt_reason')}. "
          "패리티/겹침 게이트가 판정 진입을 막았다(§10 kill-3·§14-7).")
        A("")
        A(f"- 패리티 게이트 통과: {result['parity_gate_pass']}")
        A(f"- 겹침 게이트 통과: {result['overlap']['gate_pass']} "
          f"(±30 pooled {_pct(result['overlap'].get('primary_pooled_rate'))})")
        return "\n".join(L) + "\n"
    j = result["judgment"]
    verdict = ("**kill-4 — 서지 대비 구별 EV 없음(정직 종결)**" if j["kill4_no_distinct"]
               else f"**구별 EV 서브모집단 {j['n_distinct']}개**: {j['distinct_subpops']}")
    A(f"{verdict}. 3개 서브모집단(신규진입·재진입·pooled)을 서지 기준선 대비 "
      f"효과크기 하한 +0.10%p · 일자블록 차 CI(n_boot 400) · BH-FDR q=0.10(분모 3 고정) · "
      f"연도 동부호로 판정.")
    A("")
    if smoke:
        A("> 스모크 관통 — 위 수치는 파이프라인 검증용이며 판정이 아니다(발견창 1일, "
          "일자블록 부트스트랩 축소).")
        A("")
    A("## 1. 판정표")
    A("")
    A("| 서브모집단 | n(전이) | mean전이 | mean서지 | Δ(%p) | 일자블록 CI | 연도부호(22/23) | "
      "양측p | FDR | MDE(%p) | 하한 | 분류 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in j["subpops"]:
        r = j["per_subpop"][name]
        yd = r["year_delta"]
        yr = f"{_sgn(yd[2022]['sign'])}{_sgn(yd[2023]['sign'])}"
        A(f"| {name} | {r['n_transition']:,} | {_fmt(r['mean_transition_pp'])} | "
          f"{_fmt(r['mean_surge_pp'])} | {_fmt(r['delta_pp'])} | "
          f"[{_fmt(r['ci_low_pp'])}, {_fmt(r['ci_high_pp'])}] | {yr} | "
          f"{r['p_two_sided']:.4f} | {'생존' if r['fdr_survive'] else '—'} | "
          f"{_fmt(r['mde_pp'])} | {'통과' if r['floor_pass'] else '미달'} | {r['classification']} |")
    A("")
    A(f"- **겹침률(±30 pooled)**: {_pct(result['overlap'].get('primary_pooled_rate'))} "
      f"(≤0.50 통과 — 구별 모집단)")
    A(f"- **sanity anchor(§14)**: 전 서브모집단 |Δ|<0.02%p = {j['sanity_anchor_tripped']} "
      + ("→ **파이프라인 결함 의심, 수동 스팟 10건 필수**" if j["sanity_anchor_tripped"] else "(미발동)"))
    A("")
    A(f"> **딱지(강제 인쇄, §9)**: {CONTAMINATION_LABEL}")
    A("")
    A("*엔진 백테 0회 · 원본 read-only · git 커밋 없음. 구별 EV 0 = '서지 대비 구별 없음'이자 "
      "'가장 깨끗한 미채굴 축의 정직 종결'이지 'moneytop 전이 무의미'가 아니다(L3 조건부).*")
    return "\n".join(L) + "\n"


def append_n_trials(
    ledger_path, result: Mapping[str, object], *,
    session: str = "alpha-restart-d5-d9", window: str = "2022-03-23~2023-12-31(발견창)",
) -> int:
    """서브모집단 3건 series D5_D9 type-b append(분모 3 고정, §14-9 — 측정 완료 시).

    판정 정지(게이트 미통과) 시 append 0(선계상 없음).
    """
    if not result.get("proceed_to_judgment") or result.get("judgment") is None:
        return 0
    j = result["judgment"]
    ts = datetime.now(timezone.utc).isoformat()
    rows: List[dict] = []
    for name in j["subpops"]:
        r = j["per_subpop"][name]
        rows.append({
            "ts": ts, "series": "D5_D9", "window": window,
            "trial_type": "b(오프라인 봉인 판정)",
            "target": (f"D9 전이 온셋 {name} vs 서지 기준선 L3 평균 Δ ≥+0.10%p ∧ "
                       "일자블록 CI 0배제 ∧ BH-FDR(분모3) ∧ 연도 동부호 (사전등록 §7, type-b)"),
            "result": (f"{r['classification']} — Δ {_fmt(r['delta_pp'])}%p, "
                       f"CI[{_fmt(r['ci_low_pp'])},{_fmt(r['ci_high_pp'])}], "
                       f"양측p {r['p_two_sided']:.4f}, FDR생존 {r['fdr_survive']}, "
                       f"MDE {_fmt(r['mde_pp'])}%p, 하한 {r['floor_pass']}, n {r['n_transition']}"),
            "session": session,
        })
    for row in rows:
        ledger.append_trial(**row, path=ledger_path)
    return len(rows)


def _pct(v) -> str:
    return "—" if v is None or (isinstance(v, float) and v != v) else f"{v * 100:.4f}%"


def _rate(pw: Mapping[str, object], name: str):
    d = pw.get(name)
    return d.get("rate") if isinstance(d, Mapping) else None


def _sgn(s) -> str:
    return {1: "+", -1: "−", 0: "·"}.get(s, "·")
