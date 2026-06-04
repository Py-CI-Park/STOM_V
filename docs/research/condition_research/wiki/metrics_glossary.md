# Metrics Glossary

This glossary defines terms used by the condition research dashboard and agent workflow.

## graded

`graded` is the loop's scalar research score. It combines profit, drawdown, trade behavior, and gate status into a sortable value. A high graded score is useful for ranking candidates inside a run, but it is not enough to claim a robust or human-level condition.

## hard gate

A `hard gate` is a mandatory rule that a candidate must satisfy before it can be treated as a viable research winner. Examples include positive profit, acceptable drawdown, sufficient trade count, category coverage, and timeframe-safe variables.

## payoff_ratio

`payoff_ratio` compares average winning trade magnitude to average losing trade magnitude. It helps distinguish high-win-rate fragile systems from lower-win-rate systems with better reward-to-risk.

## edge_ratio

`edge_ratio` compares maximum favorable excursion against maximum adverse excursion. If edge_ratio is strong but realized profit is weak, exits or timing may be the main problem. If edge_ratio is weak, entry quality is likely poor.

## feature_importance

`feature_importance` measures how entry variables such as B_* columns separate winners from losers. In this project it is treated as a diagnostic for hypothesis generation, not as a promotion rule.

## PBO/DSR advisory blocker

`PBO/DSR advisory blocker` means Probability of Backtest Overfitting and Deflated Sharpe Ratio evidence is missing or insufficient. Until formal PBO and DSR runs exist, candidate promotion must remain blocked even if a short-window graded score looks attractive.

## Reference Policy

Human good-result screenshots and reports are a north-star reference corridor. The required policy sentence is: screenshots are reference, not live proof. Reference material can guide variables, time windows, and expectations, but only holdout and multiyear OOS evidence can support a robustness claim.
