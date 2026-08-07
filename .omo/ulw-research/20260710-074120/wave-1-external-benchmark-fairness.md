# Wave 1 — benchmark fairness research

Worker: `/root/benchmark_fairness_research`

## High-value findings

- A credible comparison evaluates the development processes, not two selected champions: same frozen information, engine, costs/exposure, marginal resource budget, submission count, and sealed evaluation.
- Recommended arms: human-only, automation-only, and human+AI, each with multiple independent development episodes and every official outcome retained.
- Historical OOS may not be blind for an LLM whose training data can overlap the period; prospective post-freeze paper/live-shadow evidence is the clean confirmatory tier.
- Hall-of-Fame should use explicit evidence badges: exploratory, frozen backtest, blind historical OOS, prospective paper-confirmed, live-confirmed, independently reproduced.
- Full trial ledgers are necessary for White/SPA/PBO/DSR-style selection-bias corrections.

## Primary anchors retained

- White Reality Check: https://doi.org/10.1111/1468-0262.00152
- Hansen SPA: https://doi.org/10.1198/073500105000000063
- PBO: https://doi.org/10.21314/JCF.2016.322
- Deflated Sharpe: https://doi.org/10.3905/jpm.2014.40.5.094
- Reusable Holdout: https://doi.org/10.1126/science.aaa9375
- Financial-LLM look-ahead: https://doi.org/10.3905/jfds.2023.1.143
- NIST human/AI benchmark draft: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.800-2.ipd.pdf

## Counterevidence / limits

- No human/AI comparison is perfectly fair because prior human experience and model pretraining are incommensurable.
- Holdout reuse is not the only cause of degradation; distribution shift must be tested separately.
- Preregistration can constrain exploration, so separate open discovery and confirmatory tracks.

## EXPAND routing

- Worker completed two internal expansion waves and returned no unresolved material lead.

