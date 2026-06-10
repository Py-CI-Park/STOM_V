# P7 Near-Miss Analysis

P7 did not produce 2023-2025 candidate pools in this pass because the official long training run was blocked by the P6 warm-backtest timeout signal.

The only fresh candidate from P6 is not a near miss:

- gen1: profit `-4,343,533`, MDD `22.96`, trades `269`, payoff `1.17`, max_hold_count `4.0`
- Classification: retained as a research sample by `exploration_pool_v2`/`research_pool_v2`, but not promotion-worthy.
- Promotion blockers: base sparse-positive failed, MDD > `10.0`, missing 2023/2024 training years, 2025 profit <= 0.

No fixed OOS comparison is allowed from this candidate.
