## Summary
The revised mapping resolves the prior materialize_candidate and protected DB blocker for a document-only current story. It gives a bounded command envelope that writes an evidence-local .sqlite sandbox and pair JSON, sets STOM_CLI_DB_STRATEGY before official runner invocation, and preserves official OOS versus portfolio-rule taxonomy without claiming execution.

## Analysis
Evidence inspected was limited to the three requested files: .omo/evidence/tmap-walkforward/post-20260618-official-oos-command-mapping-20260619.md, .omo/evidence/tmap-walkforward/post-20260618-official-oos-preregistration-20260619.md, and .gjc/ultragoal/goals.json. The preregistration establishes the original blocker: the robust candidate combines an r8 entry filter with an exit2 prior-month portfolio-layer rule, and P4 must stop if command mapping would require manual *.db writes, backtest.py edits, live or V3K paths, or unclear evidence labeling. The ultragoal state shows G001 review_blocked and G002 active specifically to resolve this mapping before P4 execution. The revised mapping answers that by running only the r8 filtered buy and sell pair as official OOS and deferring the exit2 prior-month allocation to a portfolio-layer report.

Architecture is acceptable for the stated evidence-only change: the mapping removes materialize_candidate, reads the source loop_strategies.db read-only, writes a .sqlite sandbox under .omo/evidence/tmap-walkforward, and requires STOM_CLI_DB_STRATEGY for runner commands. Product taxonomy is corrected by labeling r8 low-cap as 공식 OOS, exit2 prior-month allocation as 포트폴리오 규칙, and the combined candidate as 공식 OOS + 포트폴리오 규칙 조합. Code/source status is clear for this review because no product source edits are proposed or inspected; the command remains unexecuted by design.

## Root Cause
The blocker was not an OOS runner failure; it was an impedance mismatch between a compound research candidate and official runner inputs. Treating the compound name as a single buy and sell pair would either require unsafe materialization into protected DB paths or mislabel a portfolio allocation rule as official engine OOS. The revised mapping fixes the boundary by splitting official engine evidence from portfolio-layer evidence.

## Findings
No blocking findings.

## Recommendations
1. Approve the revised mapping for the document and evidence-only story.
2. Keep the next execution bounded to section 1 of the mapping, then inspect generated pair JSON and sandbox contents before running OOS.
3. Preserve the mapping stop rules: no *.db writes, no _database/strategy.db or ai_strategy_loop/state/loop_strategies.db writes, no backtest.py edits, no live or V3K or KHOPENAPI paths, and no mixed evidence labels.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
- Evidence-local .sqlite sandbox: safer than protected DB mutation and compatible with STOM_CLI_DB_STRATEGY; requires explicit pre-run inspection of generated artifacts.
- materialize_candidate or protected DB materialization: simpler operationally but violates the blocker and guardrails.
- Treating the compound candidate as one official OOS pair: simpler reporting but architecturally wrong because the exit2 component is a portfolio rule, not a buy and sell pair.
