# P4 Runtime Log Review

Status: `complete`

## C_T Buy + Control Sell

Artifacts:

- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-ctbuy-controlsell-result.json`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-ctbuy-controlsell-result.stdout.txt`
- `ai_strategy_loop/state/snapshots/ct_branch_ctbuy_controlsell_warm_20260605_g0.json`

Checkpoint summary:

| Checkpoint | Value |
|---|---|
| seed pair | `CT_DIAG_CTB_902905_20260605` + `CT_DIAG_CTLS_902905_20260605` |
| warm prepare | completed |
| back_count | `43` |
| backtest elapsed | `134.8s` |
| status | `error` |
| reason | warm backtest timeout at `120s`, `csv=no` |
| snapshot csv_path | `null` |
| wrapper cleanup | `null` because wrapper itself exited normally |

## Control Buy + C_T Sell

Artifacts:

- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-controlbuy-ctsell-result.json`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-controlbuy-ctsell-result.stdout.txt`
- `ai_strategy_loop/state/snapshots/ct_branch_controlbuy_ctsell_warm_20260605_g0.json`

Checkpoint summary:

| Checkpoint | Value |
|---|---|
| seed pair | `CT_DIAG_CTLB_902905_20260605` + `CT_DIAG_CTS_902905_20260605` |
| warm prepare | completed |
| back_count | `43` |
| backtest elapsed | `10.7s` |
| status | `success` |
| reason | `ok` |
| snapshot csv_path | `backtest/csv\stock_bt_CT_DIAG_CTLB_902905_20260605_20260605195559.csv` |
| profit / trades / MDD | `149,567` / `1` / `2.99` |

## Interpretation

The C_T sell code is not the blocker for this same-window preflight. The blocker follows the C_T buy code even when the sell side is replaced by the passing control sell.
