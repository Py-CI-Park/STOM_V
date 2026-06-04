# Research Method Registry

This wiki records the condition-research methods currently used or planned in the AI strategy loop. It is a working research map, not a deployment approval record.

## Methods

### hillclimb/refine
The legacy refinement loop mutates an existing condition around observed weak segments. It is useful for small threshold moves, but it can overfit if the same train window is reused without holdout or multiyear OOS checks.

### GA
GA-style search is useful when condition fragments can be represented as bounded genes. It should stay behind default-OFF toggles and must be judged by the same hard gate and OOS rules as LLM-generated strategies.

### band compiler and seed_902 band
The band compiler direction converts fixed condition templates into bounded variables: feature, operator, lower bound, upper bound, active flag, and optional window. The seed_902 band work aims to represent the known Tick_902 seed pair as a deterministic band baseline before search.

### Optuna band optimizer
The planned Optuna path treats band limits and active flags as a constrained optimization space. The intended sequence is short-window search, top-k carry-forward, then longer holdout and multiyear OOS validation. Optuna can search; it cannot prove robustness by itself.

### edge ratio
edge ratio analysis compares favorable excursion against adverse excursion, separating entry quality from exit quality. It is diagnostic and should feed refinement, not bypass promotion gates.

### feature_importance
feature_importance analysis ranks B_* entry features by how well they separate profitable and losing trades across segments such as time, market-cap bucket, and change bucket.

### adaptive timing
adaptive timing measures whether a strategy performs only in a narrow time window. It can suggest safer start/end windows, but any timing change must be re-tested out of sample.

### segment feedback
segment feedback turns weak segment analysis into generation guidance. It should appear in prompt logging evidence before claiming that the model actually used the avoid or repair instruction.

### prompt logging
prompt logging records prompt metadata, hashes, and bounded text heads so future agents can audit what was requested without exposing full prompt bodies by default.

## Pitfalls

BackFinder-derived seeds can contain lookahead or survivorship bias if interpreted as deployable rules. PBO and DSR are not implemented as hard promotion gates yet, so they remain advisory blockers. Short-window winners are not proof of human-level condition generation.

## Next Experiments

1. Run toggles-ON tick research with generation, filter gates, time dispersion, few-shot seed examples, and segment feedback enabled.
2. Compare selected candidates against Tick_902 on 2022 and 2026 OOS without changing the candidate after selection.
3. Add formal PBO and DSR measurements as read-only diagnostics before any promotion workflow is considered.
