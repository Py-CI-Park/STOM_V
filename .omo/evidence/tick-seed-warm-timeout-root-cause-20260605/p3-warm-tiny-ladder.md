# P3 Warm Tiny Diagnostic Ladder

Status: `complete`

## Configs

- Manifest: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-ladder-manifest.json`
- Original W1 config: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-w1-config.json`
- Corrected W1R config: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-w1r-config.json`
- Exact time-window coverage audit: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p3-window-coverage-audit.json`

## Exact Window Coverage Correction

The initial one-day W1 used `2025-01-02` because P1 broad range coverage found rows on that date. P3 refined the audit to apply the actual per-day time window.

| Variant Window | Rows | Distinct Codes | First Index | Decision |
|---|---:|---:|---:|---|
| W1 `20250102 09:00:00..09:01:00` | 0 | 0 | null | invalid tiny window |
| W2 `20250102 09:00:00..09:05:00` | 0 | 0 | null | invalid tiny window |
| W3 broad `20250101..20250103 09:00:00..09:01:00` | 1860 | 203 | `20250102100001` | broad numeric range includes middle-day 10:00+ rows |
| W4 broad `20250101..20250103 09:00:00..09:05:00` | 2100 | 205 | `20250102100001` | broad numeric range includes middle-day 10:00+ rows |

Correction: rerun W1 as W1R on the first exact covered day, `2025-01-03`, `09:00:00..09:01:00`.

## Runtime Results

| Variant | Run ID | Period | Window | Engines | Wrapper Status | Backtest Status | CSV | Metrics | Elapsed | Decision |
|---|---|---|---|---:|---|---|---|---|---:|---|
| W1 | `tick_seed_timeout_warm_1d_1m_e1_20260605` | `2025-01-02` | `09:00..09:01` | 1 | `ok` | `error` after warm prepare data failure and cold fallback | no | no | `114.108s` | invalid data window, not used as seed proof |
| W1R | `tick_seed_timeout_warm_1d_1m_e1_20260605_r1` | `2025-01-03` | `09:00..09:01` | 1 | `ok` | `error` after warm prepare success | no | no | `56.372s` | stop ladder |

W1R stdout key lines:

```text
[LOOP] warm prepare completed (back_count=41)
[LOOP] backtest status=error elapsed=11.0s reason=warm backtest non-success: status=error message=backtest completed without metrics csv=no
```

The loop DB generation row for W1R records:

- `status=error`
- `csv_path=null`
- `trade_count=0`
- `reason=backtest failed/timeout: warm backtest non-success: status=error message=backtest completed without metrics csv=no`

## Stop Rule

The ladder stops after W1R because passing preflight requires `status=success`, CSV path, metrics, elapsed under timeout, and no timeout/recovery branch. W1R has data and warm prepare succeeds, but produces no CSV/metrics.

## Interpretation

- W1 original exposed a data-window selection issue: `2025-01-02 09:00..09:05` is empty.
- W1R refutes “warm cannot prepare data at all” for the corrected tiny window because `back_count=41`.
- W1R does not prove overfit/performance failure; it proves there is no passing seed preflight even in the corrected smallest warm TICK window.
- P4 must compare the exact W1R window through `run-cold` before choosing between warm-path regression and seed/no-trade workload categories.
