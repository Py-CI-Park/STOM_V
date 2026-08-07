"""P0b 실백테 검증 (통합표식) — 서브스텝0 결정론 + 새 후보 흑/적 판정.

엔진 무수정 — claude_candidate_batch_eval 헤드리스 재사용. smoke-2025q1-e32.
1) known-good(THETA θ*) 2회 재백테 → 결정론 판정 + PASS
2) 야간 no-go 후보 1회 재백테 → REFUSE
"""
import sys
from pathlib import Path

REPO = Path(r"C:\System_Trading\STOM\STOM_V.wt-dev")
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap  # noqa
from ai_strategy_loop.tmap.template import load_template, render
from ai_strategy_loop.tmap.refine_gate import gate_candidate

CFG = str(REPO / ".omo/evidence/tmap-walkforward/smoke-2025q1-e32-config.json")

print("=== P0b 실백테 검증 시작 (smoke-2025q1-e32) ===", flush=True)

# 1) known-good = THETA θ* (cap2500·take9·trail4) — 결정론(2회) + PASS 기대
t = load_template("seed_902905")
buy, sell = render(t, {"cap_max": 2500, "take_hard": 9, "trail_start": 4})
print("[1] known-good THETA θ* 재백테 2회 (결정론 검증)...", flush=True)
r_good = gate_candidate(buy, sell, CFG, label="p0b_knowngood_theta",
                        in_sample_lift=2_100_000.0, repeats=2)
print(f"[1] KNOWN-GOOD passed={r_good['passed']} profit={r_good['profit']} "
      f"deterministic={r_good['deterministic']} profits={r_good['profits']}", flush=True)
print(f"    reason: {r_good['reason']}", flush=True)

# 2) post-hoc-negative = 야간 no-go 후보(기본값 홍수형) — REFUSE 기대
t2 = load_template("llmgen_multiband_open_small_late_mid_reignite")
buy2, sell2 = render(t2)
print("[2] 야간 no-go 후보 재백테 1회 (REFUSE 검증)...", flush=True)
r_bad = gate_candidate(buy2, sell2, CFG, label="p0b_neg_cand",
                       in_sample_lift=100_000.0, repeats=1)
print(f"[2] POST-HOC-NEG passed={r_bad['passed']} profit={r_bad['profit']}", flush=True)
print(f"    reason: {r_bad['reason']}", flush=True)

# 판정 종합
ok = (r_good["passed"] is True) and (r_bad["passed"] is False) and (r_good["profit"] is not None)
print("\n=== P0b 검증 결과 ===", flush=True)
print(f"known-good PASS: {r_good['passed']} | post-hoc-neg REFUSE: {not r_bad['passed']} | "
      f"결정론: {r_good['deterministic']}", flush=True)
print(f"P0b 충분조건(해금게이트): {'★PASS' if ok else 'FAIL'}", flush=True)
