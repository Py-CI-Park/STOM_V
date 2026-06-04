# RESEARCH KNOWLEDGE BASE

## OVERVIEW
`research/` contains V3K-era analyzers and experimental models for microstructure, risk, portfolio, auxiliary indicators, and deep learning. Treat these as offline analysis assets unless gates explicitly allow runtime integration.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Microstructure | `analyzer/microstructure_analyzer.py` | order-book/flow/pressure diagnostics. |
| Risk | `analyzer/risk_analyzer.py` | VaR, Sharpe/Sortino, drawdown, volatility. |
| Portfolio | `analyzer/portfolio_optimizer.py` | optimization/risk-parity style helpers. |
| Deep learning | `deeplearning/` | factor/PCA/model backtest integration. |
| Auxiliary indicators | `auxiliary_indicator/` | additional analysis helpers. |

## CONVENTIONS
- Use analyzers as offline advisory or research features while V3K gates remain incomplete.
- Keep outputs separated from operating DB/live wiring unless the approved gate specifically authorizes it.
- When deriving condition inputs, avoid label/result leakage and keep B_* style input boundaries in mind.
- Prefer deterministic reports and explicit model/version metadata for experiments.

## ANTI-PATTERNS
- Do not wire analyzer output directly into live order/exit decisions before Gate 6 approval.
- Do not create DB cutover artifacts from research code while Gate 5 is blocked.
- Do not introduce LS Securities direct broker dependencies in 2U_C V3K work.

## LOCAL GOTCHAS
- Analyzer outputs can look actionable, but V3K live consumption is still gated.
- Keep model artifacts and generated reports out of source paths unless explicitly requested.
- Record assumptions for market regime, sample window, and feature availability.
- Prefer small deterministic fixtures when adding tests around analyzers.
- Do not read production DBs implicitly during import.
- Treat deep-learning models as optional/offline; missing model files should fail gracefully where possible.
- Keep Kiwoom-retained semantics distinct from LS-excluded features.
- When reporting research, separate observations from trading recommendations.
- Avoid broad dependency additions for experiments.
- Preserve default-OFF flags in adapter-facing outputs.
