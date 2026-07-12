"""D5-R 조건부 청산 사전등록 실행 — R1 포렌식 → L3 게이트 → R3 리플레이 triage.

봉인 근거: docs/research/condition_research/plans/
2026-07-12_d5r_conditional_exit_preregistration.md (커밋 ac5ca448).

실행(엔진 백테 0회, tick DB read-only):
    STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d5r_triage.py

산출: research_runs/alpha_restart_20260710/{d5r_triage_report.md,
d5r_triage_summary.json} + n_trials_ledger.jsonl 에 type-b 8행 append.
2024/2025 창 미접촉(이 계열엔 전부 known), 매수식·원장 원본 무변경, git 커밋 없음.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_lab.exitlab_r.forensics import (  # noqa: E402
    help_hurt_map, kill1_verdict, lower_bound_table,
)
from alpha_lab.exitlab_r.pipeline import (  # noqa: E402
    CANDIDATES, T_GRID, build_ctx_cache_getter, dedup_representative,
    evaluate_trades, load_family_trades,
)
from alpha_lab.exitlab_r.triage import run_l3_gate, run_r3_candidate  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("d5r")

BACK_DB = str(_REPO / "_database" / "stock_tick_back.db")
CODE_INFO = str(_REPO / "_database" / "code_info.db")
OUT_DIR = _REPO / "docs/research/condition_research/research_runs/alpha_restart_20260710"
ADOPT_FLOOR = {"A": 0.20, "B": 0.10}   # §7 채택 하한(A 상향 +0.20%p).
WINDOW = "2022-03-23~2023-12-31(발견 가용)"
SERIES = "D5-R"
SESSION = "alpha-restart-d5r"


def run() -> dict:
    trades, load_rep = load_family_trades(BACK_DB, CODE_INFO, root=str(_REPO))
    get_ctx, close = build_ctx_cache_getter(BACK_DB)
    try:
        records = evaluate_trades(trades, get_ctx)
        ok = [r for r in records if r.get("status") == "ok"]
        deduped = dedup_representative(ok)
        # R1.
        lb = lower_bound_table(deduped, CANDIDATES)
        hh = help_hurt_map(deduped, T_GRID)
        k1 = kill1_verdict(deduped, T_GRID)
        # L3 게이트(패치 순수 vs 벡터).
        l3 = run_l3_gate(ok, get_ctx, CANDIDATES)
        # R3 진단(후보별).
        lb_by_cand = {row["candidate"]: row for row in lb}
        r3 = []
        for p in CANDIDATES:
            res = run_r3_candidate(
                p, deduped, ok, adopt_floor=ADOPT_FLOOR[p.family],
            )
            qualifies = lb_by_cand[p.label]["qualifies"]
            res["backstop_qualifies"] = bool(qualifies)
            res["regime_fragile"] = bool(
                p.family == "B" and int(p.T) in k1["regime_fragile_T"]
            )
            # 최종 판정: 하한 미달이면 무조건 inconclusive(kill-2, §5.1); 통과 전제
            # 진단은 diagnostic_class. kill-1 은 전역 미발동(§R1)이나 레짐-취약 T 병기.
            if k1["kill1_fires"]:
                res["final_verdict"] = "reject(kill-1: 전역 레짐 위장)"
            elif not qualifies:
                res["final_verdict"] = "inconclusive(kill-2: 표본 하한 미달)"
            else:
                res["final_verdict"] = {
                    "pass_if_qualified": "pass", "weak_signal": "weak_signal",
                    "reject": "reject",
                }[res["diagnostic_class"]]
            r3.append(res)
    finally:
        close()

    n_qual = sum(1 for row in lb if row["qualifies"])
    best = max((c for c in r3 if c["mean_dnet_pp"] is not None),
               key=lambda c: c["mean_dnet_pp"], default=None)
    summary = {
        "kind": "d5r_conditional_exit_triage",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "preregistration": "2026-07-12_d5r_conditional_exit_preregistration.md (ac5ca448)",
        "window": WINDOW,
        "objective": "총수익 상향(give-back 회수) — 판정량 Δnet=net(패치)−net(현직)",
        "champion_base": "RR8_12 (sell sha 8ef01e0e)",
        "load_report": load_rep,
        "population": {
            "family_accepted_rows": len(ok), "deduped_unique": len(deduped),
            "dedup_key": "(진입일자, code6, 진입시각)",
            "note": "GPTAUTH_G8 제외(별개 매도식·영향거래 0, §7); RR8_21 86건 foreign(0.7 트레일 변형) 제외",
        },
        "R1_lower_bound": lb,
        "R1_help_hurt_map": hh,
        "R1_kill1": k1,
        "L3_repro_gate": l3,
        "R3_triage": r3,
        "headline": {
            "n_candidates": len(CANDIDATES),
            "n_backstop_qualified": n_qual,
            "kill1_fires": k1["kill1_fires"],
            "l3_gate_pass": l3["gate_pass"],
            "best_candidate": best["candidate"] if best else None,
            "best_mean_dnet_pp": best["mean_dnet_pp"] if best else None,
            "best_ci_low_pp": best["ci_low_pp"] if best else None,
            "any_pass": any(c["final_verdict"] == "pass" for c in r3),
        },
    }
    return summary


def write_ledger_rows(summary: dict) -> int:
    """type-b 8행 append — 후보 단위(FDR 분모 8). 원장 무변경(추가만)."""
    path = OUT_DIR / "n_trials_ledger.jsonl"
    ts = datetime.now().isoformat()
    lines = []
    lb = {r["candidate"]: r for r in summary["R1_lower_bound"]}
    for c in summary["R3_triage"]:
        lab = c["candidate"]
        b = lb[lab]
        ov = ""
        if c["overlap"] and c["overlap"]["overlap_rate"] is not None:
            ov = f", 겹침률 {c['overlap']['overlap_rate']}(≤0.50={c['overlap']['le_0.50']})"
        target = (f"D5-R {lab}({'Family '+c['family']}) 조건부 청산 반사실 채택 검정 — "
                  f"영향거래 평균 Δnet≥{c['adopt_floor']}%p ∧ 일자블록 CI하한>0 ∧ 가문/연도 일관성 "
                  f"(사전등록 §7, 후보 단위 type-b)")
        result = (f"{c['final_verdict']} — 하한자격 {b['verdict']}(pop {b['n_pop']}: "
                  f"2022={b['n_2022']}/2023={b['n_2023']}, 백스톱 {b['backstop']}); "
                  f"진단 평균Δnet {c['mean_dnet_pp']}%p, CI[{c['ci_low_pp']},{c['ci_high_pp']}], "
                  f"MDE {c['mde_pp']}%p, 합산Δ {c['sum_dwon_krw']}원, "
                  f"연도부호 {c['year_direction'][2022]['sign']}/{c['year_direction'][2023]['sign']}, "
                  f"가문 {c['family_consistency']['agree']}/3{ov}; "
                  f"kill1={summary['R1_kill1']['kill1_fires']}, L3 pass={summary['L3_repro_gate']['gate_pass']}")
        lines.append(json.dumps({
            "ts": ts, "series": SERIES, "window": WINDOW,
            "trial_type": "b(오프라인 봉인 판정)", "target": target,
            "result": result, "session": SESSION,
        }, ensure_ascii=False))
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        for ln in lines:
            fh.write(ln + "\n")
    return len(lines)


def main() -> None:
    summary = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "d5r_triage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    from scripts.d5r_report import render_report  # 지연 import(보고 렌더 분리).
    (OUT_DIR / "d5r_triage_report.md").write_text(
        render_report(summary), encoding="utf-8"
    )
    n = write_ledger_rows(summary)
    h = summary["headline"]
    logger.warning(
        "D5-R done: qualified=%d/%d kill1=%s L3pass=%s best=%s(Δnet=%s) ledger+%d",
        h["n_backstop_qualified"], h["n_candidates"], h["kill1_fires"],
        h["l3_gate_pass"], h["best_candidate"], h["best_mean_dnet_pp"], n,
    )
    print(json.dumps(h, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
