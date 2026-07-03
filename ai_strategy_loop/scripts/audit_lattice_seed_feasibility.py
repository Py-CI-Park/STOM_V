#!/usr/bin/env python
"""Audit sampled lattice seeds before running a full smoke batch."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEEDS = ROOT / "docs" / "research" / "condition_research" / "generated_conditions" / "lattice" / "lattice_seeds.json"
DEFAULT_RUN_DIR = ROOT / "docs" / "research" / "condition_research" / "research_runs" / "seed_lattice_20260702"
DEFAULT_RESULTS = [
    DEFAULT_RUN_DIR / "smoke_results_tick_first10.json",
    DEFAULT_RUN_DIR / "smoke_results_tick_stratified_probe.json",
]
DEFAULT_OUT = DEFAULT_RUN_DIR / "lattice_sample_feasibility_audit.json"
LABEL_IN_REASON = re.compile(r"\[([^\]]+)\]")

CAP_RULES = {
    "small": "market_cap < 1500.0",
    "midsmall": "1500.0 <= market_cap < 3000.0",
    "midlarge": "3000.0 <= market_cap < 10000.0",
    "large": "market_cap >= 10000.0",
}
REGIME_RULES = {
    "low": "0.0 <= change_pct < 3.0",
    "mid": "3.0 <= change_pct < 8.0",
    "high": "8.0 <= change_pct < 29.0",
}


def load_seeds(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    seeds = data.get("seeds")
    if not isinstance(seeds, list):
        raise ValueError(f"seeds list missing: {path}")
    return [dict(seed) for seed in seeds]


def load_result_rows(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("results", []):
            item = dict(row)
            item["source_results"] = str(path)
            rows.append(item)
    return rows


def _condition_id_from_row(row: Mapping[str, Any]) -> str:
    for key in ("condition_id", "strategy_gist", "label"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    reason = str(row.get("reason") or "")
    match = LABEL_IN_REASON.search(reason)
    if match:
        return match.group(1)
    name = str(row.get("buy_name") or "").strip()
    if name.startswith("LAT_") and name.endswith("_B"):
        return name[4:-2]
    return name


def _runtime_status(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "").strip().lower()
    reason = str(row.get("reason") or "").strip().lower()
    if status == "no_trades":
        return "no_trades"
    if "status=success" in reason and "csv=no" in reason:
        return "no_trades"
    if "no_trades" in reason and "csv=no" in reason:
        return "no_trades"
    if "timeout" in reason or status == "timeout":
        return "timeout"
    if status in {"error", "failed"}:
        return "error"
    return status or "unknown"


def _cell_parts(cell_id: str) -> tuple[str, str, str, str]:
    parts = cell_id.split("_")
    if len(parts) != 4:
        return cell_id, "unknown", "unknown", "unknown"
    return parts[0], parts[1], parts[2], parts[3]


def _time_bounds(time_bucket: str) -> tuple[int | None, int | None]:
    try:
        start = int(time_bucket) * 100
    except ValueError:
        return None, None
    return start, start + 500


def _family_trigger(family: str, params: Mapping[str, Any]) -> str:
    if family == "momentum_breakout":
        return f"price >= high * {params.get('high_mult')}"
    if family == "prevday_active":
        return f"prev_same_time_ratio >= {params.get('prev_ratio_min')}"
    if family == "strength_surge":
        return f"execution_strength >= {params.get('strength_min')}"
    if family == "volume_surge":
        return f"trade_value_per_sec >= avg({params.get('avg_win')}) * {params.get('surge_mult')}"
    return f"unknown family: {family}"


def _gates_for_seed(seed: Mapping[str, Any]) -> list[dict[str, Any]]:
    cell_id = str(seed.get("cell_id") or "")
    family = str(seed.get("family") or "")
    params = seed.get("params") if isinstance(seed.get("params"), dict) else {}
    lane, time_bucket, cap_tier, regime = _cell_parts(cell_id)
    start, end = _time_bounds(time_bucket)
    return [
        {
            "gate": "universe_filter",
            "condition": "interest_universe == 1",
            "feasibility": "data_dependent",
            "relaxation_candidate": False,
        },
        {
            "gate": "time_window",
            "condition": f"{start} <= hhmmss < {end}" if start is not None else time_bucket,
            "lane": lane,
            "feasibility": "structural_ok",
            "relaxation_candidate": False,
        },
        {
            "gate": "market_cap_tier",
            "condition": CAP_RULES.get(cap_tier, cap_tier),
            "feasibility": "strict_axis",
            "relaxation_candidate": True,
        },
        {
            "gate": "regime_filter",
            "condition": REGIME_RULES.get(regime, regime),
            "feasibility": "strict_axis",
            "relaxation_candidate": True,
        },
        {
            "gate": "family_trigger",
            "condition": _family_trigger(family, params),
            "feasibility": "strict_axis",
            "relaxation_candidate": True,
        },
        {
            "gate": "exit_rule",
            "condition": (
                f"take_profit={params.get('take_profit')} stop_loss={params.get('stop_loss')} "
                f"max_hold={params.get('max_hold')} force_exit={params.get('force_exit')}"
            ),
            "feasibility": "post_entry_only",
            "relaxation_candidate": False,
        },
    ]


def build_audit(seeds: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_condition = {str(seed["condition_id"]): dict(seed) for seed in seeds}
    samples: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    missing: list[str] = []
    for row in rows:
        condition_id = _condition_id_from_row(row)
        runtime_status = _runtime_status(row)
        counts[runtime_status] += 1
        seed = by_condition.get(condition_id)
        if seed is None:
            missing.append(condition_id)
            gates: list[dict[str, Any]] = []
        else:
            gates = _gates_for_seed(seed)
        samples.append(
            {
                "condition_id": condition_id,
                "cell_id": None if seed is None else seed.get("cell_id"),
                "family": None if seed is None else seed.get("family"),
                "runtime_status": runtime_status,
                "raw_status": row.get("status"),
                "reason": row.get("reason"),
                "trade_count": row.get("trade_count", 0),
                "source_results": row.get("source_results"),
                "gates": gates,
            }
        )

    sample_count = len(samples)
    no_trade_count = counts.get("no_trades", 0)
    all_no_trades = sample_count > 0 and no_trade_count == sample_count
    primary_targets = ["family_trigger", "regime_filter", "market_cap_tier"] if no_trade_count else []
    decision = {
        "threshold_relaxation_needed": all_no_trades,
        "primary_relaxation_targets": primary_targets,
        "keep_locked": ["universe_filter", "time_window", "exit_rule"],
        "rationale": (
            "All sampled seeds completed without csv/metrics; entry gates are the likely bottleneck."
            if all_no_trades
            else "Mixed or non-no-trade statuses require runtime-specific triage before relaxing thresholds."
        ),
    }
    return {
        "schema_version": 1,
        "sample_count": sample_count,
        "status_counts": dict(counts),
        "missing_seed_definitions": missing,
        "decision": decision,
        "samples": samples,
    }


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--result-json", type=Path, action="append", default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    result_paths = args.result_json or DEFAULT_RESULTS
    audit = build_audit(load_seeds(args.seeds), load_result_rows(result_paths))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("sample_count", "status_counts", "decision")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
