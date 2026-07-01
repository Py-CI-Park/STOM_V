from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ai_strategy_loop.bootstrap as bootstrap  # noqa: F401 - ensure project import bootstrap
from ai_strategy_loop.controller import state as _state
from ai_strategy_loop.tmap.mutator import propose_mutations
from ai_strategy_loop.tmap.refine_gate import materialize_candidate
from ai_strategy_loop.tmap.template import load_template, render

ART = ROOT / "artifacts" / "overnight-process-research-20260627"
LOG_DIR = ART / "logs"
SUMMARY = ART / "anchor-resume-summary.json"


def theta_sig(theta: dict[str, Any]) -> str:
    return json.dumps({k: theta[k] for k in sorted(theta)}, ensure_ascii=False)


def deadline_epoch(hhmm: str) -> float:
    hh, mm = (int(x) for x in hhmm.split(":"))
    now = time.localtime()
    target = time.struct_time((now.tm_year, now.tm_mon, now.tm_mday, hh, mm, 0, now.tm_wday, now.tm_yday, now.tm_isdst))
    ep = time.mktime(target)
    if ep <= time.time():
        ep += 24 * 3600
    return ep


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def query_round(run_id: str) -> list[dict[str, Any]]:
    try:
        con = sqlite3.connect(str(_state.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT strategy_gist, gate_passed, profit, mdd, trade_count, daily_avg_trades, score"
                " FROM generations WHERE run_id=?",
                (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception:
        return []
    return [dict(r) for r in rows]


def choose_anchor(template: Any, rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    candidates = [r for r in rows if r.get("event") == "cand" and isinstance(r.get("theta"), dict) and r.get("profit") is not None]
    passers = [r for r in candidates if r.get("gate") and float(r.get("profit") or 0) > 0]
    pool = passers or candidates
    if not pool:
        return dict(template.defaults()), None
    best = max(pool, key=lambda r: float(r.get("profit") or -1e18))
    anchor = dict(template.defaults())
    anchor.update(best["theta"])
    return anchor, best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resume LLM-free overnight anchor mutation from best existing theta.")
    parser.add_argument("--config-json", default=str(ART / "process_b_research.json"))
    parser.add_argument("--out", default=str(ART / "anchor.jsonl"))
    parser.add_argument("--template", default="seed_902905")
    parser.add_argument("--run-prefix", default="ovn_anchor_20260627_resume")
    parser.add_argument("--deadline-hhmm", default="06:00")
    parser.add_argument("--max-rounds", type=int, default=2)
    parser.add_argument("--round-timeout", type=int, default=5400)
    parser.add_argument("--max-per-param", type=int, default=2)
    args = parser.parse_args(argv)

    out_jsonl = Path(args.out)
    template = load_template(args.template)
    existing = read_jsonl(out_jsonl)
    seen = {theta_sig(r["theta"]) for r in existing if r.get("event") == "cand" and isinstance(r.get("theta"), dict)}
    anchor, source = choose_anchor(template, existing)
    existing_rounds = [int(r.get("round") or 0) for r in existing if r.get("event") in {"cand", "round_done"}]
    start_round = (max(existing_rounds) if existing_rounds else 0) + 1
    deadline = deadline_epoch(args.deadline_hhmm)
    best_overall = source
    adopted_total = sum(1 for r in existing if r.get("event") == "cand" and r.get("gate") and float(r.get("profit") or 0) > 0)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    append_jsonl(out_jsonl, {
        "event": "resume_start",
        "template": args.template,
        "deadline_hhmm": args.deadline_hhmm,
        "existing_lines": len(existing),
        "seen_theta": len(seen),
        "source_label": source.get("label") if source else None,
        "source_profit": source.get("profit") if source else None,
        "ts": time.time(),
    })
    print(f"[RESUME] source={(source or {}).get('label')} profit={(source or {}).get('profit')} seen={len(seen)} start_round={start_round}", flush=True)

    completed_rounds = 0
    for round_no in range(start_round, start_round + max(args.max_rounds, 0)):
        if time.time() >= deadline:
            print("[RESUME] deadline reached", flush=True)
            break
        muts = propose_mutations(template, anchor, max_per_param=args.max_per_param)
        fresh = [m for m in muts if theta_sig(m["theta"]) not in seen]
        if not fresh:
            muts = propose_mutations(template, anchor, max_per_param=args.max_per_param + 2)
            fresh = [m for m in muts if theta_sig(m["theta"]) not in seen]
        if not fresh:
            print("[RESUME] no fresh mutations", flush=True)
            break

        label2theta: dict[str, dict[str, Any]] = {}
        pairs: list[dict[str, str]] = []
        for i, mutation in enumerate(fresh):
            label = f"rr{round_no}_{i}_{mutation['param']}={mutation['value']}"
            try:
                buy, sell = render(template, mutation["theta"])
                buy_name, sell_name = materialize_candidate(label, buy, sell, template.timeframe)
            except Exception as exc:
                append_jsonl(out_jsonl, {"event": "materialize_error", "round": round_no, "label": label, "error": str(exc), "ts": time.time()})
                continue
            seen.add(theta_sig(mutation["theta"]))
            label2theta[label] = mutation["theta"]
            pairs.append({"label": label, "buy": buy_name, "sell": sell_name})

        run_id = f"{args.run_prefix}_r{round_no}"
        pairs_path = out_jsonl.parent / f"{run_id}_pairs.json"
        pairs_path.write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
        print(f"[RESUME] r{round_no}: materialized {len(pairs)} candidates", flush=True)
        append_jsonl(out_jsonl, {"event": "resume_round_start", "round": round_no, "run_id": run_id, "pairs": len(pairs), "pairs_path": str(pairs_path), "ts": time.time()})

        remaining = int(deadline - time.time())
        if remaining < 600:
            print("[RESUME] not enough time for next batch", flush=True)
            break
        subprocess.run(
            [sys.executable, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval", "--pairs-json", str(pairs_path), "--config-json", args.config_json, "--run-id", run_id],
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),
            timeout=min(args.round_timeout, remaining),
            check=False,
        )

        results = query_round(run_id)
        passers = [r for r in results if r.get("gate_passed") and float(r.get("profit") or 0) > 0]
        for row in results:
            append_jsonl(out_jsonl, {
                "event": "cand",
                "round": round_no,
                "label": row.get("strategy_gist"),
                "gate": bool(row.get("gate_passed")),
                "profit": row.get("profit"),
                "mdd": row.get("mdd"),
                "trades": row.get("trade_count"),
                "daily": row.get("daily_avg_trades"),
                "theta": label2theta.get(row.get("strategy_gist") or ""),
                "ts": time.time(),
            })
        adopted_total += len(passers)
        pool = passers if passers else [r for r in results if r.get("profit") is not None]
        moved = False
        if pool:
            best = max(pool, key=lambda r: float(r.get("profit") or -1e18))
            best_theta = label2theta.get(best.get("strategy_gist") or "")
            if best_theta:
                anchor = dict(template.defaults())
                anchor.update(best_theta)
                moved = True
                best_entry = {
                    "label": best.get("strategy_gist"),
                    "profit": best.get("profit"),
                    "mdd": best.get("mdd"),
                    "trades": best.get("trade_count"),
                    "daily": best.get("daily_avg_trades"),
                    "gate": bool(best.get("gate_passed")),
                    "theta": best_theta,
                }
                if best_entry["gate"] and (best_overall is None or float(best_entry["profit"] or -1e18) > float(best_overall.get("profit") or -1e18)):
                    best_overall = best_entry
        append_jsonl(out_jsonl, {
            "event": "round_done",
            "round": round_no,
            "passers": len(passers),
            "evaluated": len(results),
            "adopted_total": adopted_total,
            "best_overall": best_overall,
            "anchor_moved": moved,
            "ts": time.time(),
        })
        print(f"[RESUME] r{round_no} done passers={len(passers)}/{len(results)} adopted={adopted_total} best={(best_overall or {}).get('profit')}", flush=True)
        completed_rounds += 1

    summary = {
        "completedRounds": completed_rounds,
        "adoptedTotal": adopted_total,
        "bestOverall": best_overall,
        "finishedTs": time.time(),
        "out": str(out_jsonl),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RESUME] summary={SUMMARY}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
