# P3 Mixed-Pair Bounded Preflights

Status: `complete`

## Window / Config

- Date: `2025-01-03`
- Window: `09:02:00..09:05:00`
- Timeframe: `tick`
- Warm engines: `1`
- Warm timeout: `120s`
- Outer wall cap: `240s`

## Results

| Pair | Run ID | Wrapper | Elapsed | Backtest | CSV | Metrics |
|---|---|---|---:|---|---|---|
| C_T buy + control sell | `ct_branch_ctbuy_controlsell_warm_20260605` | `ok` | `177.258s` | `error`, warm timeout at `120s` | no | no |
| control buy + C_T sell | `ct_branch_controlbuy_ctsell_warm_20260605` | `ok` | `51.979s` | `success` | yes | yes |

## Artifact Map

| Pair | Config | Result | Snapshot |
|---|---|---|---|
| C_T buy + control sell | `p3-ctbuy-controlsell-config.json` | `p3-ctbuy-controlsell-result.json` | `ai_strategy_loop/state/snapshots/ct_branch_ctbuy_controlsell_warm_20260605_g0.json` |
| control buy + C_T sell | `p3-controlbuy-ctsell-config.json` | `p3-controlbuy-ctsell-result.json` | `ai_strategy_loop/state/snapshots/ct_branch_controlbuy_ctsell_warm_20260605_g0.json` |

## Key Observations

- C_T buy + control sell loaded the same `back_count=43`, then failed with `warm backtest non-success`, timeout `120s`, and `csv=no`.
- control buy + C_T sell loaded `back_count=43`, completed in `10.7s` inside the backtest, and produced metrics:
  - profit: `149,567`
  - trades: `1`
  - MDD: `2.99`
  - CSV path: `backtest/csv\stock_bt_CT_DIAG_CTLB_902905_20260605_20260605195559.csv`

## Decision Input

This isolates the timeout to the C_T buy side for this exact date/window. The C_T sell side does not reproduce the blocker when paired with the passing control buy.
