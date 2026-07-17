"""D5-R historical conditional-exit triage.

This module retains read-only forensic/L3/R3 analysis only.  The former raw v1
``n_trials_ledger.jsonl`` append was retired: D5-R has no authority to write a
trial ledger, and this command emits its computed headline to stdout without
creating or modifying report artifacts.
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
ADOPT_FLOOR = {"A": 0.20, "B": 0.10}   # §7 채택 하한(A 상향 +0.20%p).
WINDOW = "2022-03-23~2023-12-31(발견 가용)"


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




def main() -> None:
    summary = run()
    h = summary["headline"]
    logger.warning(
        "D5-R historical triage: qualified=%d/%d kill1=%s L3pass=%s best=%s(Δnet=%s)",
        h["n_backstop_qualified"],
        h["n_candidates"],
        h["kill1_fires"],
        h["l3_gate_pass"],
        h["best_candidate"],
        h["best_mean_dnet_pp"],
    )
    print(json.dumps(h, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
