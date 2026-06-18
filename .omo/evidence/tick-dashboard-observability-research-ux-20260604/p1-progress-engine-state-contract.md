# P1 Backtest Progress And Engine State Contract Evidence

## Scope
- Plan: `.omo/plans/tick-dashboard-observability-research-ux-20260604.md`
- Task: P1 - Backtest progress and engine state contract with focused tests.

## Files Changed
- `ai_strategy_loop/controller/contract.py`
- `ai_strategy_loop/controller/state.py`
- `ai_strategy_loop/controller/progress_contract.py`
- `tests/unit/test_dashboard_engine_progress_contract.py`

## Contract Added
`LatestInfo` now carries two backward-compatible read-only payloads:

- `latest.backtest_progress`
- `latest.engine_state`

Both default to `{}` for old `current_state.json` payloads.

## Progress Semantics
The progress payload is intentionally honest:

- `source="loop_generation"` when no real runner/tick counter is available.
- Explicit runner counters win when `latest.backtest_progress` supplies them.
- No GUI `shared_cnt` or fake tick-level counter is imported.
- ETA is computed only when elapsed time, total units, and completed units are available.

Manual contract QA:

```powershell
$env:PYTHONUTF8='1'
python -c "... to_loop_state(... progress/engine summary ...)"
```

Observed payload:

```json
{
  "engine": {
    "bt_engine_mode": "warm",
    "bt_timeframe": "tick",
    "cpu_count": 64,
    "effective_engine_count": 32,
    "period_end": 20251231,
    "period_start": 20230101,
    "recent_logs": ["a", "b"]
  },
  "progress": {
    "current_gen": 2,
    "done_units": 2,
    "elapsed_sec": 10.0,
    "eta_sec": 15.0,
    "max_generations": 5,
    "message": "manual qa",
    "percent": 40.0,
    "phase": "backtest_start",
    "source": "loop_generation",
    "timeframe": "tick",
    "total_units": 5
  }
}
```

## Red-Green Evidence
Red command:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_engine_progress_contract.py -q
```

Initial result:

```text
5 failed
Failure reason: LatestInfo had no backtest_progress or engine_state fields.
```

Green command:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_engine_progress_contract.py -q
```

Result:

```text
5 passed in 0.84s
```

Focused P1 regression:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_state_contract.py tests/unit/test_process_timing.py tests/unit/test_publish_live_page_data.py tests/unit/test_dashboard_phase_mapping.py -q
```

Result:

```text
74 passed in 12.39s
```

P0+P1 regression:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_docs.py tests/unit/test_variable_correlation.py tests/unit/test_state_contract.py tests/unit/test_process_timing.py tests/unit/test_publish_live_page_data.py tests/unit/test_dashboard_phase_mapping.py -q
```

Result:

```text
95 passed in 18.25s
```

## Safety Checks
`git diff --check`:

```text
exit 0; no whitespace errors. PowerShell printed CRLF conversion warnings only.
```

Protected paths:

```powershell
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

```text
<empty>
```

## P1 Verdict
P1 is complete.

- Dashboard state contract now has explicit progress and engine-state payloads.
- Progress is generation/runner-counter based only, not fabricated tick progress.
- Engine state exposes CPU count, engine counts, warm/cold mode, timeframe, period, time window, logs, and active config.
- No official backtest engine math, hard gate, protected path, live broker, `final_approval`, or `export_winner` path was touched.

Next task: P2 frontend dashboard UX repair.
