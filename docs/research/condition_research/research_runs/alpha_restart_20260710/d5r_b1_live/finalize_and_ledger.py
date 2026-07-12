# -*- coding: utf-8 -*-
"""엔진 A/B 최종 판정 + n_trials_ledger.jsonl type-a 4행 기록(런당 1행).

사용: python finalize_and_ledger.py <ab_runs_dir> [--write]
 --write 없으면 드라이런(행만 출력). --write면 실 ledger append.
 4행 = A_2022, B_2022, A_2023, B_2023 (각 1 엔진런 = type-a 1회, §11 예산 계상).
 B행은 대응 A 대비 Δ·kill-5 기준을 병기. B_2023행에 등록 결정 병기.
"""
import sys, io, json, os
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

d = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
LEDGER = r"C:\System_Trading\STOM\STOM_V.wt-alpha\docs\research\condition_research\research_runs\alpha_restart_20260710\n_trials_ledger.jsonl"
WINDOW = "2022-03-23~2023-12-31(발견 가용)"
SESSION = "alpha-restart-d5r-b1-live-migration"
PROFILE = "betting5/avg30/09:00-09:28/tick/engines8/scratch-strategy.db(실 DB 미접촉)"

def load(name):
    p = os.path.join(d, name)
    if not os.path.exists(p): return None
    with open(p, "r", encoding="utf-8") as f: return json.load(f)
def M(j, k): return (j.get("metrics") or {}).get(k) if j else None

runs = {n: load(f"{n}.json") for n in ("A_2022","B_2022","A_2023","B_2023")}
missing = [n for n,j in runs.items() if j is None]
if missing:
    print("MISSING 결과:", missing); sys.exit(1)

def yb(yr):
    A, B = runs[f"A_{yr}"], runs[f"B_{yr}"]
    pA, pB = M(A,"total_profit_krw"), M(B,"total_profit_krw")
    nA, nB = M(A,"trade_count"), M(B,"trade_count")
    dP = pB - pA
    dNpct = (100.0*(nB-nA)/nA) if nA else None
    c1 = dP > 0
    c2 = (nA>0) and abs(nB-nA)/nA <= 0.20
    c3 = A.get("status")=="success" and B.get("status")=="success"
    return dict(yr=yr, A=A, B=B, pA=pA, pB=pB, nA=nA, nB=nB, dP=dP, dNpct=dNpct,
                c1=c1, c2=c2, c3=c3, verdict=c1 and c2 and c3)

y22, y23 = yb("2022"), yb("2023")
agg_dP = y22["dP"] + y23["dP"]
both_pos = y22["dP"] > 0 and y23["dP"] > 0
all_pass = y22["verdict"] and y23["verdict"]

for y in (y22, y23):
    print(f"\n[{y['yr']}] A={y['pA']:,} B={y['pB']:,} Δ={y['dP']:+,} | 거래 A={y['nA']} B={y['nB']} ({y['dNpct']:+.1f}%) "
          f"| MDD% A={M(y['A'],'mdd_pct')} B={M(y['B'],'mdd_pct')} | C1={y['c1']} C2={y['c2']} C3={y['c3']} => {'PASS' if y['verdict'] else 'FAIL'}")
print(f"\n[AGG] ΣΔ={agg_dP:+,} 둘다+={both_pos} 전체판정={'PASS' if all_pass else 'FAIL'}")

now = datetime.now().isoformat()
def arm_row(yr, arm):
    y = y22 if yr=="2022" else y23
    j = y["A"] if arm=="A" else y["B"]
    sell = "ALP_V4_RR8_12(현직 sha 8ef01e0e)" if arm=="A" else "ALP_D5R_B1_S(패치 sha 48018620)"
    base = (f"{arm}_{yr} 엔진런: 매수 ALP_V4_RR8_12 + 매도 {sell}. "
            f"총수익 {M(j,'total_profit_krw'):,}원, 거래 {M(j,'trade_count')}, 승률 {M(j,'win_rate')}%, "
            f"평균수익률 {M(j,'avg_profit_pct')}%, MDD {M(j,'mdd_pct')}%, 일수 {M(j,'day_count')}, status {j.get('status')}.")
    if arm=="B":
        base += (f" [A/B] Δ(B-A) {y['dP']:+,}원(부호{'+' if y['dP']>0 else '-'}, triage +1.31M 동방향={y['dP']>0}); "
                 f"거래수변화 {y['dNpct']:+.1f}%(≤±20%={y['c2']}); kill-5 C1={y['c1']}·C2={y['c2']}·C3={y['c3']} => {'PASS' if y['verdict'] else 'FAIL'}.")
        if yr=="2023":
            base += (f" [집계·등록결정] ΣΔ {agg_dP:+,}원, 연도 둘다+={both_pos}, 전체판정={'PASS' if all_pass else 'FAIL'}. "
                     f"등록={'실행(ALP_D5R_B1_S → 실 strategy.db INSERT-only, 매수는 348c5181 byte-exact 미러)' if all_pass else '보류'}. "
                     f"※데이터 판정불가 → 실전 30거래일이 최종심판, 성공 주장 아님.")
    return {"ts": now, "series": "D5-R", "window": WINDOW,
            "trial_type": "a(엔진 확인 — 감독형 이관 사전 sanity)",
            "target": f"D5-R B1 감독형 이관 엔진 A/B — {arm}_{yr} (type-a 1회, 예산상한16). {PROFILE}",
            "result": base, "session": SESSION}

rows = [arm_row("2022","A"), arm_row("2022","B"), arm_row("2023","A"), arm_row("2023","B")]
print("\n===== 기록될 ledger 행 (4, 런당 1행) =====")
for r in rows: print(json.dumps(r, ensure_ascii=False))

if WRITE:
    with open(LEDGER, "a", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[LEDGER] 4행 append 완료 -> {LEDGER}")
else:
    print("\n[DRY-RUN] --write 없음. ledger 미기록.")

with open(os.path.join(d, "_ab_verdict.json"), "w", encoding="utf-8") as f:
    json.dump({"all_pass": all_pass, "both_pos": both_pos, "agg_dP": agg_dP,
               "y2022": {k:y22[k] for k in ("pA","pB","nA","nB","dP","dNpct","verdict")},
               "y2023": {k:y23[k] for k in ("pA","pB","nA","nB","dP","dNpct","verdict")}},
              f, ensure_ascii=False, indent=2)
print("\n등록게이트:", "PASS" if all_pass else "FAIL")
