# P5 Selector Blocked

- run_id: `tick_oosrob_p5_train_2023_2025_20260604`
- selector_version: `yearly_sparse_robust_v1`
- selected: False
- blocker: `no candidate qualified for yearly_sparse_robust_v1`
- OOS action: skip P6 fixed 2022/2026 OOS
- reason: no training-only candidate satisfied aggregate sparse-positive plus 2023/2024/2025 yearly robustness.

## Rejected Candidates
- gen0: status != ok, profit <= 0, trade_count < 20, daily_avg_trades < 0.05, payoff_ratio < 1.05
- gen1: profit <= 0, mdd > 10.0, trade_count > 250
- gen2: status != ok, profit <= 0, trade_count < 20, daily_avg_trades < 0.05, payoff_ratio < 1.05
- gen3: profit <= 0, mdd > 10.0, trade_count > 250
- gen4: profit <= 0, mdd > 10.0
- gen5: profit <= 0, mdd > 10.0, trade_count > 250
- gen6: trade_count < 150
- gen7: mdd > 10.0
- gen8: profit <= 0, mdd > 10.0
- gen9: profit <= 0, mdd > 10.0
