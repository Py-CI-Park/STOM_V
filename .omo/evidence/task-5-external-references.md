# Task 5 — External Quant, AI, and Validation References

Access date: 2026-06-03

| Source family | URL | Label | Applicability | Status / stale-claim note |
|---|---|---|---|---|
| PBO / backtest overfitting | https://scholarworks.wmich.edu/math_pubs/42/ | Primary | Core evidence for overfitting defense in strategy research; frames probability of backtest overfitting and CSCV. | Confirms that simple hold-out techniques can be unreliable for investment backtests. |
| Deflated Sharpe Ratio | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 | Primary | Correction for selection bias, multiple testing, backtest overfitting, and non-normal returns. | Supports trial-count-adjusted ranking instead of naive best-backtest selection. |
| Time-series CV | https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html | Primary/official docs | Baseline time-ordered validation splitter; avoids training on future samples. | Current docs show default `n_splits=5`; any old `3 splits` statement is stale. |
| Multi-objective optimization | https://optuna.readthedocs.io/en/v3.4.1/tutorial/20_recipes/002_multi_objective.html | Primary/official docs | Pareto-style optimization for return/MDD/frequency/payoff/slippage tradeoffs. | Confirms multi-objective studies with per-objective directions. |
| Triple-barrier / meta-labeling | https://www.econbiz.de/Record/-/10011841464 | Secondary metadata | Supports labeling workflow concepts from financial ML; useful for future BackFinder-style positive/negative label refinement. | Use as secondary because it is catalog metadata, not the full book text. |
| Slippage / execution realism | https://www.backtrader.com/docu/slippage/slippage/ | Secondary framework docs | Practical reminder that backtests need explicit slippage/execution stress assumptions. | Use as implementation reference, not a theory source. |
| LLM code-generation evaluation caveats | https://arxiv.org/abs/2507.06920 | Primary | Relevant to AI-generated strategy code: limited/homogeneous tests can miss subtle faults and inflate performance estimates. | Supports adversarial tests and broader validation beyond happy-path pass/fail. |
| LLM code-quality caveats | https://arxiv.org/abs/2511.10271 | Primary | Relevant to strategy-generation pipelines where correctness alone is not enough. | Supports code-quality and non-functional review around generated strategies. |

## Implications for STOM

- Treat PBO and DSR as promotion-card guardrails.
- Treat TimeSeriesSplit as baseline only; financial labels need purging/embargo around overlapping horizons.
- Treat BackFinder positive labels as seed-mining evidence until negative samples and OOS precision are added.
- Use multi-objective/Pareto search instead of a single scalar when balancing profit, MDD, frequency, payoff, max-hold, and slippage sensitivity.
- Do not use LLM-generated strategy code as evidence of profitability without official backtest, OOS, and adversarial validation.
