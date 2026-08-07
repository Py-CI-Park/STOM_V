## Summary
The command mapping resolves the G002 blocker for the robust primary candidate at the artifact level. It gives an explicit, bounded envelope that materializes only the r8 low-cap official engine pair, runs fixed OOS configs with `claude_candidate_batch_eval`, and keeps the exit2 prior-month rule in a labeled portfolio-report layer.

## Analysis
Reviewed only the requested files: `.omo/evidence/tmap-walkforward/post-20260618-official-oos-command-mapping-20260619.md`, `.omo/evidence/tmap-walkforward/post-20260618-official-oos-preregistration-20260619.md`, and `.gjc/ultragoal/goals.json`.

Spec compliance: the preregistration requires P4 to wait until the compound candidate is mapped to official engine inputs without `backtest.py`, live/V3K paths, protected DB writes, or unclear evidence labels. The mapping note satisfies this by splitting `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` into an official engine layer for `r8_exclude_cap_lt_1500` and a portfolio report layer for `exit2_skip_after_prior_exit2_loss_500k_else_full`.

Architecture: the boundary is clean. DB-backed official runner inputs are limited to the materialized r8 buy/sell pair. The note explicitly states that the compound machine name is not a plain STOM buy/sell strategy and that `claude_candidate_batch_eval` cannot encode the portfolio allocation rule as a single pair. This prevents false official-OOS labeling of the combined rule.

Safety: the proposed commands avoid `backtest.py`, do not reference live/V3K/KHOPENAPI execution, read the source loop strategy DB with SQLite `mode=ro` before materialization, and explicitly forbid writes to operating `_database/strategy.db`. The note also includes stop rules for invalid materialization, live/export boundary violations, `backtest.py` edits, live/V3K paths, and taxonomy ambiguity.

## Root Cause
The blocker came from conflating a deployable r8 entry-filter pair with a causal prior-month portfolio allocation rule under one machine name. The mapping resolves the root cause by making official OOS evidence apply only to the engine-runnable r8 pair and by requiring the combined robust candidate to be reported as official OOS plus portfolio rule composition.

## Findings
No blocking findings.

LOW advisory, `.omo/evidence/tmap-walkforward/post-20260618-official-oos-command-mapping-20260619.md` section Safe Runner Envelope: the review did not execute commands or inspect helper implementation by constraint, so P4 should still validate materialization output names and evidence labels before running annual OOS. Impact is operational, not architectural. Fix suggestion: keep the existing stop rules and treat the materialized pair JSON as the first inspectable artifact.

LOW advisory, `.omo/evidence/tmap-walkforward/post-20260618-official-oos-preregistration-20260619.md` section Primary Candidate: preregistration says the primary candidate evidence type to produce is `공식 OOS`, while the mapping correctly refines the combined candidate to `공식 OOS + 포트폴리오 규칙 조합`. Impact is possible reader confusion. Fix suggestion: subsequent handoff should carry the mapping taxonomy forward verbatim.

## Recommendations
1. Approve the mapping note as resolving G002 for proceeding to P4 preparation.
2. During P4, execute the materialization command first and inspect the produced pair JSON before annual OOS.
3. Preserve the labels from the mapping table: r8 filtered buy/sell is `공식 OOS`, exit2 prior-month allocation is `포트폴리오 규칙`, and the combined robust candidate is `공식 OOS + 포트폴리오 규칙 조합`.
4. Do not claim completed official OOS until the listed `claude_candidate_batch_eval` commands have produced their run artifacts.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
- Single compound official command: simpler operator story, but incorrect because the exit2 prior-month allocation rule is not a buy/sell pair and would blur evidence taxonomy.
- Split official engine plus portfolio report: slightly more steps, but preserves runner boundaries, avoids `backtest.py`, avoids live/V3K and operating `_database/strategy.db`, and keeps evidence types honest.
