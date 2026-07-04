#!/usr/bin/env python
"""Plan B P5 official-profile static audit and config generator.

This tool is intentionally read-only against STOM market/strategy databases. It
creates only research-run JSON/MD artifacts under docs/research/... and never
runs a backtest. The goal is to make the official lattice rerun profile explicit
before any tick/min 288 full batch is allowed.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import ai_strategy_loop.bootstrap as bootstrap
from ai_strategy_loop.controller.condition_discovery import (
    effective_condition_discovery_runtime_config,
)
from ai_strategy_loop.controller.loop import _build_warm_btconfig
from ai_strategy_loop.launch_config import config_from_dict
from ai_strategy_loop.scripts.lattice_strategy_names import is_filename_safe

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = ROOT / "docs" / "research" / "condition_research" / "research_runs" / "seed_lattice_20260702"
DEFAULT_TICK_CONFIG = DEFAULT_RUN_DIR / "smoke_config_tick.json"
DEFAULT_MIN_CONFIG = DEFAULT_RUN_DIR / "smoke_config_min.json"
DEFAULT_TICK_PAIRS = DEFAULT_RUN_DIR / "pairs_tick.json"
DEFAULT_MIN_PAIRS = DEFAULT_RUN_DIR / "pairs_min.json"
DEFAULT_TICK_DB = ROOT / "_database" / "stock_tick_back.db"
DEFAULT_MIN_DB = ROOT / "_database" / "stock_min_back.db"
DEFAULT_STRATEGY_DB = bootstrap.LOOP_DB_STRATEGY
DEFAULT_STAMP = "20260704"
OFFICIAL_ENGINE_COUNT = 64
OFFICIAL_MIN_DAILY_TRADES = 0.5
OFFICIAL_MDD_CAP = 35.0
OFFICIAL_CHUNK_SIZE = 48
TICK_INDEX_MIN_LEN = 14
MIN_INDEX_MIN_LEN = 12


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _temporal_index_where(idx: str, *, min_len: int) -> str:
    """SQL WHERE clause for numeric index tokens eligible for range extrema."""
    return f"{idx} NOT GLOB '*[^0-9]*' AND LENGTH({idx}) >= {int(min_len)}"


def _validate_temporal_extreme(token: str, *, min_len: int) -> None:
    """Fail closed if a selected min/max token is not a real calendar datetime."""
    if min_len >= 14:
        datetime.strptime(token[:14], "%Y%m%d%H%M%S")
    else:
        datetime.strptime(token[:12], "%Y%m%d%H%M")


def inspect_sqlite_index_range(path: Path, *, min_len: int) -> dict[str, Any]:
    """Return min/max numeric index token across all tables in a SQLite DB."""
    if not path.is_file():
        raise FileNotFoundError(path)
    table_count = 0
    row_count = 0
    min_token: str | None = None
    max_token: str | None = None
    skipped_no_index: list[str] = []
    with _connect_readonly(path) as con:
        tables = [
            str(row[0])
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            table_count += 1
            columns = {str(row[1]) for row in con.execute(f"PRAGMA table_info({_quote_identifier(table)})")}
            if "index" not in columns:
                skipped_no_index.append(table)
                continue
            quoted = _quote_identifier(table)
            idx = 'CAST("index" AS TEXT)'
            where = _temporal_index_where(idx, min_len=min_len)
            row = con.execute(
                f"SELECT MIN({idx}), MAX({idx}), COUNT(*) FROM {quoted} WHERE {where}"
            ).fetchone()
            if not row:
                continue
            t_min, t_max, t_count = row
            if not t_count:
                continue
            row_count += int(t_count)
            t_min_s = str(t_min)
            t_max_s = str(t_max)
            min_token = t_min_s if min_token is None or t_min_s < min_token else min_token
            max_token = t_max_s if max_token is None or t_max_s > max_token else max_token
    if min_token is None or max_token is None:
        raise ValueError(f"no numeric index tokens length>={min_len} found in {path}")
    _validate_temporal_extreme(min_token, min_len=min_len)
    _validate_temporal_extreme(max_token, min_len=min_len)
    return {
        "path": _repo_rel(path),
        "table_count": table_count,
        "temporal_row_count": row_count,
        "index_min_len_filter": min_len,
        "min_index": min_token,
        "max_index": max_token,
        "start_date": int(min_token[:8]),
        "end_date": int(max_token[:8]),
        "skipped_no_index_tables": skipped_no_index[:20],
        "skipped_no_index_table_count": len(skipped_no_index),
    }


def _with_official_common(base: Mapping[str, Any], db_range: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(base))
    out.update({
        "provider": out.get("provider", "gpt_auth"),
        "bt_engine_mode": "warm",
        "bt_warm_engine_count": OFFICIAL_ENGINE_COUNT,
        "bt_betting": str(out.get("bt_betting", "5")),
        "bt_avg_time": int(out.get("bt_avg_time", 30)),
        "min_daily_trades": OFFICIAL_MIN_DAILY_TRADES,
        "mdd_cap": OFFICIAL_MDD_CAP,
        "winner_objective": out.get("winner_objective", "uptrend"),
        "autopsy_enabled": False,
        "bt_full_start": int(db_range["start_date"]),
        "bt_full_end": int(db_range["end_date"]),
        "max_generations": 1,
        "equity_points_enabled": True,
        "condition_discovery_preset": "fast",
        "condition_discovery_process": "fast-discovery",
    })
    return out


def build_official_configs(
    *,
    tick_base: Mapping[str, Any],
    min_base: Mapping[str, Any],
    tick_range: Mapping[str, Any],
    min_range: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    tick = _with_official_common(tick_base, tick_range)
    tick.update({
        "_comment": "Plan B P5 official tick lattice profile; DB full period; warm64; preflight required before full run.",
        "bt_timeframe": "tick",
        "bt_universe_start_time": 90000,
        "bt_universe_end_time": 92800,
        "bt_timeout": max(int(tick.get("bt_timeout", 0) or 0), 14400),
        "bt_warm_run_timeout": int(tick.get("bt_warm_run_timeout", 300) or 300),
        "_official_profile": {
            "schema": "plan_b_p5_official_profile_v1",
            "lane": "tick",
            "source_db_range": dict(tick_range),
            "time_window_policy": "fast-discovery runtime resolves tick to 09:00:00-09:28:00; raw DB reaches 09:30:00 but is not claimed as runtime window.",
            "full_run_forbidden_until_preflight_receipt": True,
        },
    })

    minute = _with_official_common(min_base, min_range)
    minute.update({
        "_comment": "Plan B P5 official min lattice profile; DB full period; warm64; run only after official tick export.",
        "bt_timeframe": "min",
        "full_session_enabled": True,
        "bt_universe_start_time": 90000,
        "bt_min_universe_end_time": 151900,
        "bt_timeout": max(int(minute.get("bt_timeout", 0) or 0), 14400),
        "bt_warm_run_timeout": int(minute.get("bt_warm_run_timeout", 1200) or 1200),
        "_official_profile": {
            "schema": "plan_b_p5_official_profile_v1",
            "lane": "min",
            "source_db_range": dict(min_range),
            "time_window_policy": "full_session_enabled runtime resolves min to 09:00-15:19.",
            "full_run_forbidden_until_tick_official_export": True,
        },
    })
    return tick, minute


def effective_profile(config_payload: Mapping[str, Any]) -> dict[str, Any]:
    cfg = config_from_dict(dict(config_payload))
    eff = effective_condition_discovery_runtime_config(cfg)
    warm = _build_warm_btconfig(cfg)
    return {
        "configured": {
            "mdd_cap": float(getattr(cfg, "mdd_cap")),
            "min_daily_trades": float(getattr(cfg, "min_daily_trades")),
            "condition_discovery_preset": getattr(cfg, "condition_discovery_preset"),
            "condition_discovery_process": getattr(cfg, "condition_discovery_process"),
            "bt_universe_start_time": int(getattr(cfg, "bt_universe_start_time")),
            "bt_universe_end_time": int(getattr(cfg, "bt_universe_end_time")),
        },
        "effective": {
            "mdd_cap": float(getattr(eff, "mdd_cap")),
            "min_daily_trades": float(getattr(eff, "min_daily_trades")),
            "condition_discovery_preset": getattr(eff, "condition_discovery_preset"),
            "condition_discovery_process": getattr(eff, "condition_discovery_process"),
            "bt_universe_start_time": int(getattr(eff, "bt_universe_start_time")),
            "bt_universe_end_time": int(getattr(eff, "bt_universe_end_time")),
            "full_session_enabled": bool(getattr(eff, "full_session_enabled", False)),
            "bt_min_universe_end_time": int(getattr(eff, "bt_min_universe_end_time", 0) or 0),
        },
        "warm_backtest_config": {
            "start_date": int(warm.start_date),
            "end_date": int(warm.end_date),
            "start_time": int(warm.start_time),
            "end_time": int(warm.end_time),
            "engine_count": int(warm.engine_count),
            "is_tick": bool(warm.is_tick),
            "avg_time": int(warm.avg_time),
            "betting": str(warm.betting),
            "timeout": int(warm.timeout),
        },
    }


def audit_pairs(pairs: Sequence[Mapping[str, Any]], *, lane: str) -> dict[str, Any]:
    labels = [str(p.get("label", "")) for p in pairs]
    buy_names = [str(p.get("buy", "")) for p in pairs]
    sell_names = [str(p.get("sell", "")) for p in pairs]
    duplicate_labels = sorted({x for x in labels if labels.count(x) > 1})
    unsafe_names = [name for name in [*buy_names, *sell_names] if not is_filename_safe(name)]
    return {
        "lane": lane,
        "pair_count": len(pairs),
        "unique_label_count": len(set(labels)),
        "duplicate_labels": duplicate_labels[:20],
        "unsafe_strategy_name_count": len(unsafe_names),
        "unsafe_strategy_names_preview": unsafe_names[:20],
    }


def audit_strategy_db(strategy_db: Path, pairs_by_lane: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    names_by_table = {
        "stockbuy": [str(p["buy"]) for pairs in pairs_by_lane.values() for p in pairs],
        "stocksell": [str(p["sell"]) for pairs in pairs_by_lane.values() for p in pairs],
    }
    out: dict[str, Any] = {"path": _repo_rel(strategy_db), "tables": {}}
    with _connect_readonly(strategy_db) as con:
        for table, names in names_by_table.items():
            missing: list[str] = []
            quoted = _quote_identifier(table)
            for name in names:
                row = con.execute(f"SELECT 1 FROM {quoted} WHERE \"index\"=? LIMIT 1", (name,)).fetchone()
                if row is None:
                    missing.append(name)
            out["tables"][table] = {
                "expected_count": len(names),
                "unique_expected_count": len(set(names)),
                "missing_count": len(missing),
                "missing_preview": missing[:20],
            }
    return out


def build_chunk_protocol(total_pairs: int, *, chunk_size: int = OFFICIAL_CHUNK_SIZE) -> dict[str, Any]:
    if chunk_size < 40 or chunk_size > 60:
        raise ValueError(f"official chunk_size must be 40..60 (received {chunk_size})")
    if total_pairs < 0:
        raise ValueError(f"total_pairs must be non-negative (received {total_pairs})")
    chunks = []
    for chunk_no, start in enumerate(range(0, total_pairs, chunk_size), start=1):
        end = min(start + chunk_size, total_pairs)
        chunks.append({
            "chunk_id": f"chunk{chunk_no:02d}",
            "start_index_inclusive": start,
            "end_index_exclusive": end,
            "pair_count": end - start,
            "warm_engine_restart_before_chunk": True,
            "warm_engine_close_after_chunk": True,
        })
    return {
        "schema_version": 1,
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "rationale": "Avoid the observed gen154~169 timeout streak by bounding each warm-engine lifetime and restarting between chunks.",
    }


def select_preflight_pairs(pairs: Sequence[Mapping[str, Any]], *, count: int = 4) -> list[dict[str, Any]]:
    if not pairs:
        return []
    if len(pairs) <= count:
        return [dict(p) for p in pairs]
    raw_indices = [0, len(pairs) // 3, (2 * len(pairs)) // 3, len(pairs) - 1]
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for idx in raw_indices:
        if idx in seen:
            continue
        seen.add(idx)
        row = dict(pairs[idx])
        row["preflight_index"] = idx
        selected.append(row)
    return selected[:count]


def build_preflight_plan_md(
    *,
    receipt_path: Path,
    tick_config_path: Path,
    min_config_path: Path,
    tick_preflight_pairs_path: Path,
    tick_range: Mapping[str, Any],
    min_range: Mapping[str, Any],
    preflight_run_id: str,
) -> str:
    return "\n".join([
        "# Plan B P5 Official Full Warm64 Preflight Plan",
        "",
        "## Scope",
        "",
        "This is a preflight plan only. Do not run tick/min 288 full smoke from this step.",
        "",
        "## Read-first receipts",
        "",
        f"- Profile audit receipt: `{_repo_rel(receipt_path)}`",
        f"- Tick official config: `{_repo_rel(tick_config_path)}`",
        f"- Min official config: `{_repo_rel(min_config_path)}`",
        f"- Tick preflight pairs: `{_repo_rel(tick_preflight_pairs_path)}`",
        "",
        "## Verified source DB ranges",
        "",
        f"- tick: `{tick_range['min_index']}` ~ `{tick_range['max_index']}` (date config `{tick_range['start_date']}`~`{tick_range['end_date']}`)",
        f"- min: `{min_range['min_index']}` ~ `{min_range['max_index']}` (date config `{min_range['start_date']}`~`{min_range['end_date']}`)",
        "",
        "## Required preflight command (not run by this audit)",
        "",
        "```powershell",
        "python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `",
        f"  --pairs-json {_repo_rel(tick_preflight_pairs_path)} `",
        f"  --config-json {_repo_rel(tick_config_path)} `",
        f"  --run-id {preflight_run_id}",
        "```",
        "",
        "## Acceptance before any full run",
        "",
        "- The command prepares warm64 successfully on the official tick DB-full-period profile.",
        "- All 2~4 preflight pairs record honest `ok`, `no_trades`, or `error` rows with CSV/metrics status preserved.",
        "- Runtime reason strings show effective gates `min_daily_trades 0.5` and `mdd_cap 35` when those gates fail.",
        "- If a timeout streak appears, stop and lower chunk size or increase per-run timeout before any 288 full run.",
        "",
        "## Full-run protocol after preflight passes",
        "",
        "- Use a new run_id; never reuse `lat_smoke_tick_full_sanitized_20260704*`.",
        "- Split 288 tick pairs into 48-pair chunks; close/restart warm engines between chunks.",
        "- Export tick results normally before min starts.",
        "- Only after official tick export may the min official config be preflighted/run.",
        "- P5 success means coverage-map completion: per-cell trades, gross/net EV, and MDD distribution. `gate_passed` count is advisory.",
        "",
    ])


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    tick_base_path = Path(args.tick_config)
    min_base_path = Path(args.min_config)
    tick_pairs_path = Path(args.tick_pairs)
    min_pairs_path = Path(args.min_pairs)
    tick_db_path = Path(args.tick_db)
    min_db_path = Path(args.min_db)
    strategy_db_path = Path(args.strategy_db)
    stamp = str(args.stamp)

    tick_range = inspect_sqlite_index_range(tick_db_path, min_len=TICK_INDEX_MIN_LEN)
    min_range = inspect_sqlite_index_range(min_db_path, min_len=MIN_INDEX_MIN_LEN)
    tick_base = _load_json(tick_base_path)
    min_base = _load_json(min_base_path)
    tick_pairs = _load_json(tick_pairs_path)
    min_pairs = _load_json(min_pairs_path)
    if not isinstance(tick_pairs, list) or not isinstance(min_pairs, list):
        raise ValueError("pairs JSON files must contain lists")

    tick_config, min_config = build_official_configs(
        tick_base=tick_base,
        min_base=min_base,
        tick_range=tick_range,
        min_range=min_range,
    )

    tick_config_path = run_dir / f"smoke_config_tick_official_full_warm64_{stamp}.json"
    min_config_path = run_dir / f"smoke_config_min_official_full_warm64_{stamp}.json"
    receipt_path = run_dir / f"p5_profile_audit_official_full_warm64_{stamp}.json"
    preflight_pairs_path = run_dir / f"pairs_tick_preflight4_official_full_warm64_{stamp}.json"
    preflight_plan_path = run_dir / f"p5_preflight_plan_official_full_warm64_{stamp}.md"

    preflight_pairs = select_preflight_pairs(tick_pairs, count=4)
    tick_effective = effective_profile(tick_config)
    min_effective = effective_profile(min_config)
    strategy_db_audit = audit_strategy_db(strategy_db_path, {"tick": tick_pairs, "min": min_pairs})

    receipt = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Plan B P5-profile-audit only; no backtest run executed",
        "source_handoffs": [
            "docs/update_log/2026-07-04_plan_b_lattice_wrong_profile_pause_handoff.md",
            "docs/update_log/2026-07-04_quant_midreview_gate_zero_diagnosis_handoff.md",
        ],
        "receipt_path": _repo_rel(receipt_path),
        "forbidden_inputs": {
            "lat_smoke_tick_full_sanitized_20260704_star": "reference_only_not_official",
            "chunk08_to_chunk10_resume": "forbidden",
        },
        "db_ranges": {"tick": tick_range, "min": min_range},
        "official_configs": {
            "tick": {"path": _repo_rel(tick_config_path), "profile": tick_effective},
            "min": {"path": _repo_rel(min_config_path), "profile": min_effective},
        },
        "gate_policy_audit": {
            "previous_tick_config_min_daily_trades": tick_base.get("min_daily_trades"),
            "previous_min_config_min_daily_trades": min_base.get("min_daily_trades"),
            "verdict": "corrected_config_to_effective_policy_floor",
            "explanation": "LoopConfig did read the old 0.3 value, but condition-discovery fast policy raises min_daily_trades to 0.5 before scoring. Official configs now set 0.5 explicitly so configured and effective gates match receipts.",
            "official_configured_min_daily_trades": OFFICIAL_MIN_DAILY_TRADES,
            "official_effective_min_daily_trades": tick_effective["effective"]["min_daily_trades"],
            "official_mdd_cap": tick_effective["effective"]["mdd_cap"],
        },
        "pair_audit": {
            "tick": audit_pairs(tick_pairs, lane="tick"),
            "min": audit_pairs(min_pairs, lane="min"),
        },
        "strategy_db_audit": strategy_db_audit,
        "chunk_protocol": {
            "tick": build_chunk_protocol(len(tick_pairs), chunk_size=OFFICIAL_CHUNK_SIZE),
            "min": build_chunk_protocol(len(min_pairs), chunk_size=OFFICIAL_CHUNK_SIZE),
        },
        "preflight": {
            "tick_pairs_path": _repo_rel(preflight_pairs_path),
            "tick_pair_count": len(preflight_pairs),
            "plan_path": _repo_rel(preflight_plan_path),
            "run_id": f"lat_preflight_tick_official_full_warm64_{stamp}",
            "full_run_allowed_by_this_receipt": False,
        },
        "p5_success_criterion": {
            "primary": "coverage_map_completion",
            "required_fields": ["per_cell_trade_count", "gross_ev", "net_ev", "mdd_distribution"],
            "gate_passed_count": "advisory_only",
            "p6_ev_input": "ai_strategy_loop.fitness.lift.compute_lift_ev/segment_lift_ev from official smoke CSVs",
        },
        "verdict": "profile_audit_complete_full_run_still_blocked_until_preflight",
    }

    _write_json(tick_config_path, tick_config)
    _write_json(min_config_path, min_config)
    _write_json(preflight_pairs_path, preflight_pairs)
    _write_json(receipt_path, receipt)
    preflight_plan_path.write_text(
        build_preflight_plan_md(
            receipt_path=receipt_path,
            tick_config_path=tick_config_path,
            min_config_path=min_config_path,
            tick_preflight_pairs_path=preflight_pairs_path,
            tick_range=tick_range,
            min_range=min_range,
            preflight_run_id=receipt["preflight"]["run_id"],
        ),
        encoding="utf-8",
    )
    return receipt


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    ap.add_argument("--tick-config", default=str(DEFAULT_TICK_CONFIG))
    ap.add_argument("--min-config", default=str(DEFAULT_MIN_CONFIG))
    ap.add_argument("--tick-pairs", default=str(DEFAULT_TICK_PAIRS))
    ap.add_argument("--min-pairs", default=str(DEFAULT_MIN_PAIRS))
    ap.add_argument("--tick-db", default=str(DEFAULT_TICK_DB))
    ap.add_argument("--min-db", default=str(DEFAULT_MIN_DB))
    ap.add_argument("--strategy-db", default=str(DEFAULT_STRATEGY_DB))
    ap.add_argument("--stamp", default=DEFAULT_STAMP)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt = run_audit(args)
    print(json.dumps({
        "status": "ok",
        "receipt": receipt["receipt_path"],
        "verdict": receipt["verdict"],
        "tick_config": receipt["official_configs"]["tick"]["path"],
        "min_config": receipt["official_configs"]["min"]["path"],
        "preflight_plan": receipt["preflight"]["plan_path"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
