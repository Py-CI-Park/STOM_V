# -*- coding: utf-8 -*-
"""엔진 A/B 판정 — 사전등록 §10 kill-5 준용.

판정 3기준:
 (1) B-A Δ총수익(원) 부호 == + (triage 방향 +1.31M 과 동방향)
 (2) 거래수 변화 |ΔN|/N_A <= 20% (kill-5)
 (3) A·B 실행 오류 없음 (status == success)
사용: python ab_judge.py <ab_runs_dir>
"""
import sys, io, json, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

d = sys.argv[1] if len(sys.argv) > 1 else "."

def load(name):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def m(j, k, default=None):
    if j is None: return default
    return (j.get("metrics") or {}).get(k, default)

def judge_pair(label, A, B):
    print(f"\n===== {label} =====")
    if A is None or B is None:
        print(f"  MISSING: A={'ok' if A else 'MISSING'} B={'ok' if B else 'MISSING'}")
        return None
    sA, sB = A.get("status"), B.get("status")
    pA, pB = m(A, "total_profit_krw"), m(B, "total_profit_krw")
    nA, nB = m(A, "trade_count"), m(B, "trade_count")
    print(f"  status      A={sA}  B={sB}")
    print(f"  총수익(원)   A={pA:>12,}  B={pB:>12,}   Δ(B-A)={pB-pA:>+12,}")
    print(f"  거래수       A={nA:>6}  B={nB:>6}   Δ={nB-nA:+d}"
          + (f"  ({100.0*(nB-nA)/nA:+.1f}%)" if nA else "  (N_A=0)"))
    print(f"  수익률합(%)  A={m(A,'total_profit_pct')}  B={m(B,'total_profit_pct')}")
    print(f"  승률(%)      A={m(A,'win_rate')}  B={m(B,'win_rate')}")
    print(f"  평균수익률(%) A={m(A,'avg_profit_pct')}  B={m(B,'avg_profit_pct')}")
    print(f"  MDD(%)       A={m(A,'mdd_pct')}  B={m(B,'mdd_pct')}")
    print(f"  일평균거래   A={m(A,'daily_avg_trades')}  B={m(B,'daily_avg_trades')}  일수 A={m(A,'day_count')} B={m(B,'day_count')}")
    c1 = (pB - pA) > 0
    c2 = (nA > 0) and abs(nB - nA) / nA <= 0.20
    c3 = (sA == "success") and (sB == "success")
    print(f"  [C1] Δ총수익 부호 +      : {'PASS' if c1 else 'FAIL'}  (Δ={pB-pA:+,})")
    print(f"  [C2] 거래수 변화 ≤±20%   : {'PASS' if c2 else 'FAIL'}"
          + (f"  ({100.0*(nB-nA)/nA:+.1f}%)" if nA else "  (N_A=0)"))
    print(f"  [C3] 실행 오류 없음       : {'PASS' if c3 else 'FAIL'}")
    verdict = c1 and c2 and c3
    print(f"  => {label} {'PASS' if verdict else 'FAIL'}")
    return {"label": label, "c1_sign": c1, "c2_tradecount": c2, "c3_errorfree": c3,
            "verdict": verdict, "dprofit": pB - pA, "nA": nA, "nB": nB,
            "pA": pA, "pB": pB}

results = []
# 2x2 per-year
for yr in ("2022", "2023"):
    r = judge_pair(yr, load(f"A_{yr}.json"), load(f"B_{yr}.json"))
    if r: results.append(r)
# 1x2 full window (fallback)
rf = judge_pair("full(2022-2023)", load("A_full.json"), load("B_full.json"))
if rf: results.append(rf)

# aggregate over available per-year (if both years present)
yr_results = [r for r in results if r["label"] in ("2022", "2023")]
if len(yr_results) == 2:
    dsum = sum(r["dprofit"] for r in yr_results)
    nA = sum(r["nA"] for r in yr_results); nB = sum(r["nB"] for r in yr_results)
    same_dir = all(r["dprofit"] > 0 for r in yr_results)
    print("\n===== AGGREGATE (2022+2023) =====")
    print(f"  ΣΔ총수익(원) = {dsum:+,}   연도별 동방향(둘 다 +) = {same_dir}")
    print(f"  거래수 A={nA} B={nB}  변화={100.0*(nB-nA)/nA:+.1f}%" if nA else "  N_A=0")

print("\n===== 최종 =====")
allv = [r["verdict"] for r in results if r["label"] in ("2022", "2023", "full(2022-2023)")]
if allv:
    print(f"  판정 대상 {len(allv)}건, PASS {sum(allv)}건")
    print(f"  전체 통과(등록 게이트) = {all(allv)}")
else:
    print("  (아직 판정 대상 없음 — 결과 파일 대기)")
