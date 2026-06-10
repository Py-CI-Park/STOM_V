# P4 Smoke Summary

- run_id: `tick_oosrob_p4_smoke_20260604`
- generations: 3
- prompts: 4
- prompt text sparse_positive_v1 hits: 4
- prompt feature sparse_positive_prompt_enabled hits: 4
- diagnostic selector selected: False
- diagnostic selector blocker: `no candidate qualified for yearly_sparse_robust_v1`
- promotion evidence: false

This smoke run is not OOS evidence and is not promotion evidence. It only proves the configured TICK loop path can generate/backtest and persist prompt records under the predeclared config.

## Generations
- gen0: status=error gate=False profit=0.0 mdd=0.0 trades=0 reason=backtest failed/timeout: warm backtest non-success: status=error message=백테스트 시간 초과 (300초) csv=no
- gen1: status=ok gate=False profit=-9708723.0 mdd=29.93 trades=705 reason=total_profit -9.709e+06 <= 0
- gen2: status=ok gate=False profit=37127.0 mdd=0.74 trades=1 reason=daily_avg_trades 0 < min_daily_trades 0.3

## Diagnostic Rejections
- gen0: status != ok, profit <= 0, trade_count < 20, daily_avg_trades < 0.05, payoff_ratio < 1.05
- gen1: profit <= 0, mdd > 10.0, trade_count > 250
- gen2: trade_count < 20, daily_avg_trades < 0.05
