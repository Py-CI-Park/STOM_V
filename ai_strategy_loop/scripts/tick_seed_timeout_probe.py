from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ai_strategy_loop import bootstrap
from ai_strategy_loop.controller.loop import REPO_ROOT, _build_warm_btconfig, _read_strategy_code
from ai_strategy_loop.launch_config import config_from_dict
from ai_strategy_loop.scripts._tick_seed_probe_safety import (
    JsonObject,
    assert_safe_command,
    assert_safe_output_path,
    terminate_process_tree,
)

REPO_ROOT_PATH = Path(REPO_ROOT).resolve()


@dataclass(frozen=True, slots=True)
class CommandSpec:
    command: list[str]
    env: dict[str, str]
    cwd: Path = REPO_ROOT_PATH


def _read_json(path: Path) -> JsonObject:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"config JSON must be an object: {path}")
    return data


def _write_json(path: Path, payload: JsonObject) -> JsonObject:
    path = assert_safe_output_path(path, repo_root=REPO_ROOT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "STOM_ALLOW_MINIMAL_SETTING": "1",
        "STOM_CLI_DB_STRATEGY": str(bootstrap.LOOP_DB_STRATEGY),
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1",
    })
    return env


def _strategy_summary(name: str, kind: str, code: str | None) -> JsonObject:
    text = code or ""
    lines = text.splitlines()
    return {
        "name": name,
        "kind": kind,
        "exists": bool(code),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if code else None,
        "length": len(text),
        "line_count": len(lines),
        "first_12_lines": lines[:12],
        "contains_self_buy": "self.Buy" in text,
        "contains_self_sell": "self.Sell" in text,
        "literal_buy_true_count": text.count("매수=True"),
        "literal_sell_true_count": text.count("매도=True"),
        "time_token_count": text.count("시간"),
    }


def _load_loop_config(config_json: Path):
    return config_from_dict(_read_json(config_json))


def inspect_probe(
    *,
    config_json: Path,
    buy_name: str,
    sell_name: str,
    out_path: Path,
) -> JsonObject:
    config = _load_loop_config(config_json)
    warm = _build_warm_btconfig(config)
    payload: JsonObject = {
        "status": "ok",
        "command": "inspect",
        "config_json": str(config_json),
        "seed_buy": _strategy_summary(buy_name, "buy", _read_strategy_code(buy_name, "buy")),
        "seed_sell": _strategy_summary(sell_name, "sell", _read_strategy_code(sell_name, "sell")),
        "effective_warm_backtest_config": {
            "start_date": int(warm.start_date), "end_date": int(warm.end_date),
            "start_time": int(warm.start_time), "end_time": int(warm.end_time),
            "avg_time": int(warm.avg_time), "engine_count": int(warm.engine_count),
            "is_tick": bool(warm.is_tick), "betting": str(warm.betting),
            "divid_mode": str(warm.divid_mode), "timeout": int(warm.timeout),
        },
        "loop_timeout_fields": {
            "bt_timeout": int(config.bt_timeout), "bt_warm_run_timeout": int(config.bt_warm_run_timeout),
            "bt_engine_mode": str(config.bt_engine_mode), "bt_timeframe": str(config.bt_timeframe),
            "bt_warm_engine_count": int(config.bt_warm_engine_count),
        },
    }
    return _write_json(out_path, payload)


def build_loop_command(*, config_json: Path, run_id: str) -> CommandSpec:
    command = [
        sys.executable, "-m", "ai_strategy_loop.controller.loop",
        "--config-json", str(config_json), "--run-id", run_id,
    ]
    assert_safe_command(command)
    return CommandSpec(command=command, env=_base_env())


def build_cold_command(*, config_json: Path, buy_name: str, sell_name: str) -> CommandSpec:
    config = _load_loop_config(config_json)
    warm = _build_warm_btconfig(config)
    timeframe = "tick" if warm.is_tick else "min"
    command = [
        sys.executable, str(REPO_ROOT_PATH / "stom_backtest.py"),
        "--buy", buy_name, "--sell", sell_name,
        "--start", str(warm.start_date), "--end", str(warm.end_date),
        "--timeframe", timeframe, "--betting", str(warm.betting),
        "--avg-time", str(warm.avg_time), "--start-time", str(warm.start_time),
        "--end-time", str(warm.end_time), "--divid-mode", str(warm.divid_mode),
        "--engines", str(warm.engine_count), "--timeout", str(config.bt_warm_run_timeout),
        "--format", "json", "--quiet",
    ]
    assert_safe_command(command)
    return CommandSpec(command=command, env=_base_env())


def run_owned_command(*, spec: CommandSpec, wall_cap: int, out_path: Path) -> JsonObject:
    assert_safe_command(spec.command)
    out_path = assert_safe_output_path(out_path, repo_root=REPO_ROOT_PATH)
    stdout_path = out_path.with_suffix(".stdout.txt")
    stderr_path = out_path.with_suffix(".stderr.txt")
    for path in (out_path, stdout_path, stderr_path):
        assert_safe_output_path(path, repo_root=REPO_ROOT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    pid: int | None = None
    returncode: int | None = None
    status = "error"
    timeout = False
    cleanup: JsonObject | None = None

    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_file:
        with stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_file:
            try:
                proc = subprocess.Popen(
                    spec.command,
                    cwd=spec.cwd,
                    env=spec.env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                )
                pid = int(proc.pid)
                try:
                    returncode = int(proc.wait(timeout=wall_cap))
                except subprocess.TimeoutExpired:
                    timeout = True
                    status = "timeout"
                    cleanup = terminate_process_tree(pid, grace_seconds=10)
                    try:
                        returncode = int(proc.wait(timeout=1))
                    except subprocess.TimeoutExpired:
                        returncode = proc.returncode
                else:
                    status = "ok" if returncode == 0 else "error"
            except OSError as exc:
                stderr_file.write(f"spawn failed: {exc}\n")
                status = "error"

    payload: JsonObject = {
        "status": status,
        "timeout": timeout,
        "pid": pid,
        "returncode": returncode,
        "command": spec.command,
        "cwd": str(spec.cwd),
        "wall_cap": wall_cap,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "cleanup": cleanup,
    }
    return _write_json(out_path, payload)


def run_loop_probe(
    *,
    config_json: Path,
    run_id: str,
    wall_cap: int,
    out_path: Path,
) -> JsonObject:
    spec = build_loop_command(config_json=config_json, run_id=run_id)
    return run_owned_command(spec=spec, wall_cap=wall_cap, out_path=out_path)


def run_cold_probe(
    *,
    config_json: Path,
    buy_name: str,
    sell_name: str,
    wall_cap: int,
    out_path: Path,
) -> JsonObject:
    spec = build_cold_command(config_json=config_json, buy_name=buy_name, sell_name=sell_name)
    return run_owned_command(spec=spec, wall_cap=wall_cap, out_path=out_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TICK seed timeout diagnostic probe")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect")
    for option in ("--config-json", "--out"):
        inspect_parser.add_argument(option, required=True, type=Path)
    inspect_parser.add_argument("--buy", required=True)
    inspect_parser.add_argument("--sell", required=True)

    run_loop_parser = sub.add_parser("run-loop")
    for option in ("--config-json", "--out"):
        run_loop_parser.add_argument(option, required=True, type=Path)
    run_loop_parser.add_argument("--run-id", required=True)
    run_loop_parser.add_argument("--wall-cap", required=True, type=int)

    run_cold_parser = sub.add_parser("run-cold")
    for option in ("--config-json", "--out"):
        run_cold_parser.add_argument(option, required=True, type=Path)
    run_cold_parser.add_argument("--buy", required=True)
    run_cold_parser.add_argument("--sell", required=True)
    run_cold_parser.add_argument("--wall-cap", required=True, type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    match args.command:
        case "inspect":
            payload = inspect_probe(config_json=args.config_json, buy_name=args.buy, sell_name=args.sell, out_path=args.out)
        case "run-loop":
            payload = run_loop_probe(config_json=args.config_json, run_id=args.run_id, wall_cap=args.wall_cap, out_path=args.out)
        case "run-cold":
            payload = run_cold_probe(config_json=args.config_json, buy_name=args.buy, sell_name=args.sell, wall_cap=args.wall_cap, out_path=args.out)
        case _:
            raise AssertionError(f"unknown command: {args.command}")
    return 0 if payload["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
