# P5 Control Baseline

Status: `complete`

## Control Seed

- Buy: `Tick_B_902_905_Update_2`
- Sell: `Tick_S_902_905_Update_2`
- Inspect artifact: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-inspect.json`

Availability through the same loop seed-read path:

| Seed | Exists | SHA-256 | Lines | Required Call |
|---|---:|---|---:|---|
| `Tick_B_902_905_Update_2` | yes | `15feb9f96176a666f58fc2e7e5d32dad6f4779c01d7f0e2419bfad41a43f6afa` | 128 | `self.Buy=yes` |
| `Tick_S_902_905_Update_2` | yes | `093ba24ee300691afb7e4e8ef48c4d85e4ea92356c4c73a7795d3e059254b8f1` | 47 | `self.Sell=yes` |

## Runtime Configs

### Equivalent W1R Control

Plan-required same-window control:

- Period: `2025-01-03..2025-01-03`
- Window: `09:00:00..09:01:00`
- Timeframe: `tick`
- Warm engines: `1`
- Warm run timeout: `60s`
- Wall cap: `150s`
- Config artifact: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-w1r-config.json`

### Supplemental Active-Window Control

The known control is documented as a `09:02..09:05` tick scalper. P5 also kept the same covered day but used the control's intended active window as supplemental stack sanity evidence:

- Period: `2025-01-03..2025-01-03`
- Window: `09:02:00..09:05:00`
- Timeframe: `tick`
- Warm engines: `1`
- Warm run timeout: `90s`
- Wall cap: `210s`
- Config artifact: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-902-905-config.json`

## Results

### Equivalent W1R Control

Artifacts:

- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-w1r-result.json`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-w1r-result.stdout.txt`

Observed:

| Field | Value |
|---|---:|
| wrapper status | `ok` |
| wrapper elapsed | `65.927s` |
| warm prepare | `completed` |
| back_count | `41` |
| backtest status | `error` |
| backtest elapsed | `13.2s` |
| csv_path | `null` |
| metrics | `no` |

### Supplemental Active-Window Control

Artifacts:

- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-902-905-result.json`
- `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p5-control-902-905-result.stdout.txt`

Observed:

| Field | Value |
|---|---:|
| wrapper status | `ok` |
| wrapper elapsed | `54.436s` |
| warm prepare | `completed` |
| back_count | `43` |
| backtest status | `success` |
| backtest elapsed | `11.7s` |
| gate_passed | `1` |
| csv_path | `backtest/csv\stock_bt_Tick_B_902_905_Update_2_20260605162808.csv` |
| trade_count | `1` |
| profit | `149,567` |
| mdd | `2.99` |

## Decision

- The exact W1R control is non-passing: it loads the same `back_count=41` but also produces no CSV/metrics.
- The active-window control is non-equivalent to W1R, but it shows the same day/backtest stack can load data, run warm mode, write CSV, and record metrics when the control is evaluated in its intended `09:02..09:05` window.
- `WARM_SESSION_PATH_REGRESSION` remains unsupported: cold and warm C_T paths both fail no-metrics, while a nearby active warm control can succeed.
- P6 must not treat P5 as a strict same-window refutation of environment/window effects. It supports only a narrower conclusion: the helper/dashboard/process stack is not generally broken, while the exact W1R no-metrics result remains unresolved without a better active control or seed/window repair.

This is a diagnostic sanity check only. It is not an OOS result and not a new performance claim.
