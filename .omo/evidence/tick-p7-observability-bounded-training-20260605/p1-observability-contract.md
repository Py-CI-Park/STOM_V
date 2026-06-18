# P1 Observability Contract

Status: completed
Captured: 2026-06-05 KST

## What Changed

The read-only dashboard observability contract now exposes bounded backtest metadata without editing official backtest engines or hard-gate fitness:

- `latest.backtest_progress.progress_source`
- `latest.backtest_progress.timeout_sec`
- `latest.backtest_progress.timeout_deadline_epoch`
- `latest.engine_state.bt_timeout`
- `latest.engine_state.bt_warm_run_timeout`
- `latest.engine_state.timeout_sec`
- `latest.engine_state.bt_full_start`
- `latest.engine_state.bt_full_end`
- `latest.engine_state.bt_universe_start_time`
- `latest.engine_state.bt_universe_end_time`

Existing `latest.backtest_progress.source` remains backward compatible. For loop-derived progress it still reports `loop_generation`, while the new `progress_source` label reports `generation_level`.

## Guardrails

- Official engines were not edited.
- `ai_strategy_loop/fitness/score.py::compute_fitness` was not edited.
- `backtest/graph/` was not edited.
- This is an observability-only payload expansion; it does not relax gates or change scoring.

## Commit Status

Commit deferred.

Reason: the same files touched by this task already contained broad pre-existing dirty changes from the current branch baseline. Staging those files would also stage unrelated prior edits. No explicit staging was performed.

## Evidence

- `p1-progress-contract-tests.txt`
- `p1-legacy-status-tests.txt`
