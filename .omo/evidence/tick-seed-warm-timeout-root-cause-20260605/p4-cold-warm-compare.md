# P4 Cold/Warm Compare

Status: `complete`

## Compared Window

- Period: `2025-01-03..2025-01-03`
- Window: `09:00:00..09:01:00`
- Timeframe: `tick`
- Engines: `1`
- Seed: `C_T_900_920_U2_B/S`

## Warm Result

Artifacts:

- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-w1r-result.json`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-w1r-result.stdout.txt`

Observed:

- wrapper status: `ok`
- wrapper elapsed: `56.372s`
- warm prepare: `completed`, `back_count=41`
- backtest status: `error`
- reason: `warm backtest non-success: status=error message=backtest completed without metrics csv=no`
- loop DB: `csv_path=null`, `trade_count=0`, `metrics=no`

## Cold Result

Artifacts:

- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p4-cold-w1r-config.json`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p4-cold-w1r-result.json`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p4-cold-w1r-result.stdout.txt`

Observed:

- wrapper status: `error`
- wrapper elapsed: `80.315s`
- CLI return code: `2`
- CLI status: `error`
- command timeout: `120s`
- outer wall cap: `240s`
- message: `backtest completed without metrics`
- last checkpoint: `csv_detected`
- `csv_path=null`

Cold checkpoint facts:

| Checkpoint | Value |
|---|---:|
| `moneytop_loaded.rows` | `31` |
| `engine_data_load_requested.data_list_count` | `43` |
| `engine_data_response_received.chunk_count` | `41` |
| `shared_data_loaded.back_count` | `41` |
| `backtest_process_finished.exitcode` | `0` |
| `csv_detected.csv_path` | `null` |
| `backtest_process_diagnostics.event_count` | `0` |

## Decision

- `WARM_SESSION_PATH_REGRESSION` is not supported by this window: cold and warm both reach loaded data/back_count and both end without CSV/metrics.
- The exact W1R data/control path is usable enough to load moneytop and engine data in both modes.
- The plan-bound rerun keeps the same result under the required `--timeout 120` and `wall_cap=240` bounds.
- The remaining split is seed/window no-trade/no-metrics versus tiny-window insufficiency. P5 must distinguish same-window control from active-window environment sanity before P6 chooses confidence.

P5 records both the plan-required same-window control and the supplemental active-window sanity check before P6 chooses a root-cause category.
