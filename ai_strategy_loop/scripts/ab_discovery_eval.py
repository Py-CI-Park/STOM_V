"""P1 A/B 대조 오케스트레이터 — 무작위(무상태) vs 폐루프(유상태) 비교.

사전등록서 .omo/evidence/tmap-walkforward/p1_ab_preregistration.md 의 동결 상수대로:
  - 두 arm을 동일 조건으로 순차 실행(유일 차이 = --stateful).
  - 합격 = OOS PROMISING 수(tick 한정). 진행 = valid-attempt당 rate 대리지표.
  - 결정규칙(§7) 적용해 verdict 출력.

엔진 무수정 — tmap_multiband_discovery.py 헤드리스 재사용. 측정 스크립트일 뿐.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.ab_discovery_eval --n 8        # pilot
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.ab_discovery_eval --n 40       # full
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[2]
EVID = REPO / ".omo/evidence/tmap-walkforward"

_PROMISING = {"★PROMISING"}
_SMOKE_OK = {"smoke-pass", "train-pass", "train-only", "★PROMISING"}


def run_arm(stateful: bool, n: int, deadline: str, out_md: Path) -> int:
    args = [sys.executable, "-m", "ai_strategy_loop.scripts.tmap_multiband_discovery",
            "--max-iters", str(n), "--deadline-hhmm", deadline, "--out", str(out_md)]
    if stateful:
        args.append("--stateful")
    print(f"[AB] arm {'STATEFUL' if stateful else 'RANDOM'} 시작: n={n} out={out_md.name}", flush=True)
    p = subprocess.run(args, cwd=str(REPO))
    print(f"[AB] arm {'STATEFUL' if stateful else 'RANDOM'} 종료 rc={p.returncode}", flush=True)
    return p.returncode


def metrics(jsonl: Path) -> Dict:
    """arm jsonl → valid-attempt당 rate 대리지표 + OOS PROMISING 수(tick 한정)."""
    recs: List[Dict] = []
    if jsonl.is_file():
        recs = [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = len(recs)
    valid = 0  # generate 성공 + 스모크 진입(evaluate 도달, smoke[0] 측정됨)
    smoke_ok = near_miss = promising_tick = 0
    for r in recs:
        ev = r.get("eval") or {}
        if not r.get("template"):
            continue  # gen-fail = valid-attempt 분모 제외(사전등록 §3)
        smoke = ev.get("smoke") or [None, None]
        if smoke and smoke[0] is not None:
            valid += 1
        v = ev.get("verdict")
        if v in _SMOKE_OK:
            smoke_ok += 1
        q1, q2 = (smoke + [None, None])[:2]
        if isinstance(q1, (int, float)) and isinstance(q2, (int, float)):
            if (q1 > 0) ^ (q2 > 0):
                near_miss += 1
        if v in _PROMISING and (r.get("timeframe") == "tick"):
            promising_tick += 1
    denom = max(1, valid)
    return {
        "total": total, "valid_attempt": valid,
        "oos_promising_tick": promising_tick,
        "smoke_pass_rate": round(smoke_ok / denom, 4),
        "near_miss_rate": round(near_miss / denom, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="arm당 반복(pilot 8 / full 40)")
    ap.add_argument("--deadline-hhmm", default="0700")
    ap.add_argument("--flat-threshold", type=float, default=0.05)
    args = ap.parse_args()

    rand_md = EVID / f"ab_random_n{args.n}.md"
    state_md = EVID / f"ab_stateful_n{args.n}.md"

    run_arm(False, args.n, args.deadline_hhmm, rand_md)
    run_arm(True, args.n, args.deadline_hhmm, state_md)

    m_rand = metrics(rand_md.with_suffix(".jsonl"))
    m_state = metrics(state_md.with_suffix(".jsonl"))
    print("\n=== P1 A/B 결과 ===", flush=True)
    print(f"RANDOM  : {m_rand}", flush=True)
    print(f"STATEFUL: {m_state}", flush=True)

    # 결정규칙(사전등록 §7)
    sp_edge = m_state["smoke_pass_rate"] - m_rand["smoke_pass_rate"]
    nm_edge = m_state["near_miss_rate"] - m_rand["near_miss_rate"]
    rate_superior = (sp_edge > args.flat_threshold) or (nm_edge > args.flat_threshold)
    if m_state["oos_promising_tick"] >= 1 and m_rand["oos_promising_tick"] == 0:
        verdict = "①합격 — 폐루프 OOS 우위 → P3~P5 진행"
    elif m_state["oos_promising_tick"] == 0 and m_rand["oos_promising_tick"] == 0 and not rate_superior:
        verdict = "②천장후보 — OOS 0 + rate 평탄(C3 K회 누적 필요). 1회로 천장선언 금지"
    elif rate_superior and m_state["oos_promising_tick"] == 0:
        verdict = f"③진행 — rate 우위(sp+{sp_edge:.3f}/nm+{nm_edge:.3f}) but OOS 0 → P2 정제 계속(천장선언 금지)"
    elif sp_edge < -args.flat_threshold:
        verdict = "④폐루프 열위 — P2 환류 배선 결함 점검"
    else:
        verdict = "혼합 — pilot은 방향성만(underpowered). full n=40 권고"
    print(f"\n판정: {verdict}", flush=True)
    print(f"rate edge: smoke_pass {sp_edge:+.4f} / near_miss {nm_edge:+.4f} "
          f"(평탄임계 {args.flat_threshold})", flush=True)
    (EVID / f"ab_result_n{args.n}.json").write_text(
        json.dumps({"random": m_rand, "stateful": m_state, "verdict": verdict,
                    "sp_edge": sp_edge, "nm_edge": nm_edge}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
