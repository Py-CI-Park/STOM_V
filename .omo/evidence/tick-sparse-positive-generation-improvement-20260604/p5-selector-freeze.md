# P5 Selector Freeze

- Run id: `tick_spgen_p5_train_2023_2025_20260604`
- Scope: 2023-2025 training only; no 2022/2026 OOS used.
- Rows read: 8
- Selector: `sparse_positive_v1`
- Selected: `true`
- Blocked: `false`
- Selected bucket: `sparse_positive`
- Selected gen: `4`
- Buy: `AILOOP_tick_spgen_p5_train_2023_2025_20260604_g4_buy`
- Sell: `AILOOP_tick_spgen_p5_train_2023_2025_20260604_g4_sell`
- Profit: `1,155,715`
- MDD: `9.12`
- Trades: `124`
- Daily avg trades: `0.2`
- Payoff ratio: `1.5523029966703663`
- Gate reason: `daily_avg_trades 0.2 < min_daily_trades 0.3`

## OOS Guard
- `oos_excluded=true` in the selection artifact.
- `diagnostic_only=false` because this is the frozen pre-OOS selection.
- `forbidden_oos_fields_present=false`.
