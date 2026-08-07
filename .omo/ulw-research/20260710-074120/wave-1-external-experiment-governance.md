# Wave 1 — experiment governance research

Worker: `/root/experiment_governance_research`

## High-value findings

- Recommended two-lane system: unrestricted exploration, then immutable hypothesis registration, sealed offline gate, paper-only shadow challenger, signed human decision, and champion-alias change.
- Exact protected-test metrics must not silently feed generation; test access needs an append-only family/alpha ledger.
- Separate repeated looks at one challenger (sequential inference) from an endless stream of different candidates (family/online multiple testing).
- A W3C-PROV-style lineage graph should connect strategy artifact, prompt/model, data snapshot, engine/config, backtest, reviewer, promotion, rollback, and all rejected candidates.
- For this checkout, any shadow remains replay/paper-only; the research does not authorize V3K Gate 4, live broker/order wiring, DB cutover, or default-ON flags.

## Suggested state model

`exploratory -> registered -> offline_passed -> shadowing -> promotion_eligible -> champion | rejected | retired`

## Primary anchors retained

- Reusable/adaptive holdout: https://doi.org/10.1126/science.aaa9375
- Ladder: https://proceedings.mlr.press/v37/blum15.html
- Generic Holdout: https://arxiv.org/abs/1809.05596
- White Reality Check: https://doi.org/10.1111/1468-0262.00152
- Hansen SPA: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- NIST AI RMF: https://doi.org/10.6028/NIST.AI.100-1

## Counterevidence / limits

- Restricted feedback can slow optimization; preregistration does not eliminate deviations; alpha-spending and confidence sequences lose power or require assumptions; shadowing cannot establish real fill/market-impact quality.
- A dashboard is not governance if its protected metrics leak or approvals are not evidence-bound.

## EXPAND routing

- Opened wave-2 STOM-specific sequential-evidence fit review.
- State-store/controller/dashboard mapping is already covered by runtime, DB, context-pack, and export-integrity workers; deduplicated.

