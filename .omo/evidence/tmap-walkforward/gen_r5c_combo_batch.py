"""R5 후보 결합 (2026-06-13) — R1 발견의 즉시 검증: THETA θ × 부검 개선 조건.

사전선언 2점: ① THETAθ(cap2500·take9·trail4)+전일비조건 제거(R1: MDD -30%)
② ①+등락율 밴드 제거(R1: +1.9%). 비교군 시드·THETA. v2 판정 후보 풀.
n_trials: r1_ablation(21)+본 배치 합산 의무(동결 시).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.tmap.template import load_template, render, validate_rendered  # noqa: E402

EVID = Path(__file__).resolve().parent
THETA = {"cap_max": 2500, "take_hard": 9, "trail_start": 4}

def ablate(lines, keys):
    out = list(lines)
    for i, ln in enumerate(lines):
        s = ln.strip()
        if any(k in s for k in keys) and (s.startswith("elif not (") or s.startswith("if not (")):
            indent = ln[: len(ln) - len(ln.lstrip())]
            head = "elif" if s.startswith("elif") else "if"
            out[i] = f"{indent}{head} False:  # R5C 제거: {s[:50]}"
    return out

def main() -> int:
    t = load_template("seed_902905")
    buy, sell = render(t, THETA)
    lines = buy.splitlines()
    v1 = "\n".join(ablate(lines, ["전일비 >"]))
    v2 = "\n".join(ablate(ablate(lines, ["전일비 >"]), ["< 등락율 <="]))
    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415
    db = str(bootstrap.LOOP_DB_STRATEGY)
    pairs = [
        {"label": "BASE_SEED", "buy": "Tick_B_902_905_Update_2", "sell": "Tick_S_902_905_Update_2"},
        {"label": "FROZEN_THETA", "buy": "THETA_seed_902905_06_B", "sell": "THETA_seed_902905_06_S"},
    ]
    for name, code, label in (("R5C_01_B", v1, "R5C THETA-전일비제거"),
                              ("R5C_02_B", v2, "R5C THETA-전일비-등락율밴드제거")):
        errs = validate_rendered(code, sell, "tick")
        assert errs == [], (label, errs)
        r = save_strategy_to_db(db, name, code, "buy")
        assert r.get("status") == "ok" or "exist" in str(r).lower(), (name, r)
        rs = save_strategy_to_db(db, name.replace("_B", "_S"), sell, "sell")
        assert rs.get("status") == "ok" or "exist" in str(rs).lower()
        pairs.append({"label": label, "buy": name, "sell": name.replace("_B", "_S")})
    (EVID / "pairs-r5c-combo.json").write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(pairs)} pairs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
