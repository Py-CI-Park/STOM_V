# P1 Generation Quality Policy

## Scope
This policy predeclares generation guidance for the default-OFF toggle `sparse_positive_prompt_enabled`. It is advisory prompt guidance only.

It cannot override:
- the official backtest engine,
- `ai_strategy_loop/fitness/score.py` hard gate behavior,
- `sparse_positive_v1` selector thresholds,
- OOS-blind candidate freeze requirements,
- final verdict requirements.

## Selector Binding
- selector: `sparse_positive_v1`
- selection input: training rows only
- OOS usage: forbidden before candidate freeze
- required freeze fields: `oos_excluded=true`, `diagnostic_only=false`, `forbidden_oos_fields_present=false`

## ON Prompt Targets
The ON prompt must explicitly target all of the following before any 2022/2026 OOS can be attempted:

- profit > 0
- MDD <= 10
- trade_count corridor 20-250
- daily_avg_trades >= 0.05
- payoff_ratio >= 1.05
- no high-frequency overtrading
- sell-side MDD and giveback control

## Buy-Side Guidance
When `sparse_positive_prompt_enabled=true`, buy generation should favor selective entries, avoid chasing every tick, reduce repeated signals in noisy windows, and target conditions that can plausibly produce positive training profit without exceeding the trade_count corridor 20-250.

## Sell-Side Guidance
When `sparse_positive_prompt_enabled=true`, sell generation should prioritize MDD <= 10, controlled giveback, payoff_ratio >= 1.05, and exits that prevent a sparse strategy from becoming a large-loss strategy.

## Forbidden Uses
- Do not relax the hard gate.
- Do not relax `sparse_positive_v1`.
- Do not tune this policy from future OOS metrics.
- Do not use OOS-after-the-fact reselection.
- Do not claim human superiority from smoke or training-only evidence.

## Decision Consequence
If the fresh training run still produces no candidate eligible under `sparse_positive_v1`, OOS remains blocked and the final verdict must be `NEEDS_MORE_EVIDENCE` or `REJECT_CANDIDATE`.
