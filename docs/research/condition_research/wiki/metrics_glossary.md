# Metrics Glossary

This glossary defines terms used by the condition research dashboard and agent workflow.

## graded

`graded` is the loop's scalar research score. It combines profit, drawdown, trade behavior, and gate status into a sortable value. A high graded score is useful for ranking candidates inside a run, but it is not enough to claim a robust or human-level condition.

## hard gate

A `hard gate` is a mandatory rule that a candidate must satisfy before it can be treated as a viable research winner. Examples include positive profit, acceptable drawdown, sufficient trade count, category coverage, and timeframe-safe variables.

## payoff_ratio

`payoff_ratio` compares average winning trade magnitude to average losing trade magnitude. It helps distinguish high-win-rate fragile systems from lower-win-rate systems with better reward-to-risk.

## OOS

`OOS` means out-of-sample: a period not used to select or tune the candidate. If OOS is disabled, the dashboard may still continue discovery, but the candidate remains research signal, not production proof.

## overfit

`overfit` means a rule is too closely fitted to the sampled period. The working criterion is intentionally looser than a production gate: a condition may remain useful for research if the full-period equity curve is upward and recent years improve, but a human-level claim remains blocked until multiyear holdout evidence exists.

## MDD

`MDD` means maximum drawdown, the largest peak-to-trough drop of the cumulative equity curve. It explains how deep the worst loss period became even when total profit is positive.

## edge_ratio

`edge_ratio` compares maximum favorable excursion against maximum adverse excursion. If edge_ratio is strong but realized profit is weak, exits or timing may be the main problem. If edge_ratio is weak, entry quality is likely poor.

## MFE/MAE

`MFE/MAE` separates entry quality from realized exit quality. `MFE` is the best favorable move while holding a trade, and `MAE` is the worst adverse move while holding it.

## slippage

`slippage` is the difference between the backtest assumed fill and realistic execution. It must be treated as a cost because order book depth, liquidity, and fast tick movement can reduce realized profit.

## PBO

`PBO` means Probability of Backtest Overfitting. It estimates the risk that a selected winner is mainly a product of repeated search rather than a stable condition edge.

## DSR

`DSR` means Deflated Sharpe Ratio. It adjusts Sharpe-style evidence for repeated trials and non-normal return distributions.

## win-day ratio

`win-day ratio` is the share of trading days with positive daily profit/loss. It is useful because a condition can have mixed intraday trades but still produce more profitable days than losing days.

## recent-weighted score

`recent-weighted score` gives stronger research weight to recent years such as 2024, 2025, and available 2026 data. It reflects market regime change, but it is not a standalone promotion rule.

## feature_importance

`feature_importance` measures how entry variables such as B_* columns separate winners from losers. In this project it is treated as a diagnostic for hypothesis generation, not as a promotion rule.

## PBO/DSR advisory blocker

`PBO/DSR advisory blocker` means Probability of Backtest Overfitting and Deflated Sharpe Ratio evidence is missing or insufficient. Until formal PBO and DSR runs exist, candidate promotion must remain blocked even if a short-window graded score looks attractive.

## Reference Policy

Human good-result screenshots and reports are a north-star reference corridor. The required policy sentence is: screenshots are reference, not live proof. Reference material can guide variables, time windows, and expectations, but only holdout and multiyear OOS evidence can support a robustness claim.
