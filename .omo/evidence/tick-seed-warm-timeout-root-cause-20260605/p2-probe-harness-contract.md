# P2 Diagnostic Probe Harness Contract

Status: `complete`

## Added Files

- `ai_strategy_loop/scripts/_tick_seed_probe_safety.py`
- `ai_strategy_loop/scripts/tick_seed_timeout_probe.py`
- `tests/unit/test_tick_seed_timeout_probe.py`

## TDD Evidence

| Step | Command | Result |
|---|---|---|
| Red | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py -q` | `4 failed`; helper module did not exist yet |
| Green | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py -q` | `4 passed in 7.38s` |
| Refactor guard | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py -q` | `4 passed in 7.57s` |
| Safety regression guard | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py -q` | `8 passed in 11.07s` |
| Focused integration guard | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q` | `22 passed in 21.77s` |

## Helper Contract

Supported commands:

```powershell
python -m ai_strategy_loop.scripts.tick_seed_timeout_probe inspect --config-json <path> --buy <name> --sell <name> --out <json>
python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json <path> --run-id <id> --wall-cap <sec> --out <json>
python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-cold --config-json <path> --buy <name> --sell <name> --wall-cap <sec> --out <json>
```

Safety properties:

- Sets `STOM_ALLOW_MINIMAL_SETTING=1`, `STOM_CLI_DB_STRATEGY`, `PYTHONUTF8=1`, and `PYTHONUNBUFFERED=1`.
- Captures owned child `pid`, command, cwd, elapsed seconds, return code, stdout path, and stderr path.
- On timeout, terminates the owned `Popen` child tree by parent PID and records cleanup details in JSON.
- Rejects command strings containing `final_approval`, `export_winner`, `khopenapi`, `v3k`, or `taskkill`.
- Rejects diagnostic output destinations under protected runtime paths or DB-like suffixes.
- Does not import or edit official engine internals.

## Manual Probe

Command:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONUNBUFFERED='1'; python -m ai_strategy_loop.scripts.tick_seed_timeout_probe inspect --config-json .omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-seed-diag-5m-config.json --buy C_T_900_920_U2_B --sell C_T_900_920_U2_S --out .omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p2-inspect-probe.json
```

Result:

- `status=ok`
- buy seed exists, hash `902cb36b87f5828548531583cd4aa16ed4a5a2a597b3db3abba217cb0f86e2e3`, 431 lines, `self.Buy=yes`
- sell seed exists, hash `e61d8ba393ae74de73d07e0cd291861bc3edeec1050cbc7d06a0750d67cba5c6`, 87 lines, `self.Sell=yes`
- effective window remains `20250101..20250103`, `090000..090500`, tick, warm engines `8`, warm run timeout `120`

The seed snippet text in this CLI artifact shows legacy mojibake for some Korean labels. P2 does not use those labels as root-cause proof; hash and structural facts are the relevant fields.

## Size And Scope

- `tick_seed_timeout_probe.py` pure LOC after refactor: `223`, below the 250-line ceiling.
- `_tick_seed_probe_safety.py` pure LOC after refactor: `91`, below the 250-line ceiling.
- Diff scope check against official engine/hard-gate paths produced no changed tracked file names for `backtest/backengine_*.py`, `backtest/back_static.py`, `ai_strategy_loop/fitness/score.py`, or `backtest/graph`.
