# Architect Stage 1 Review — STOM Dashboard V2/V3 selectable rollout plan

## Summary
Reviewed only the persisted planner artifact `stage-01-planner.md` and the supplied known facts. The plan is architecturally sound in direction: it protects the 8770 V2 baseline, makes V3 opt-in, keeps 8776 as preview, and preserves the research-only, local-only, no-live-order, no-broker-login, no-account-trading, Human Approval Gate, and Append-Only Audit boundaries. I recommend COMMENT rather than unconditional approval because execution needs a stricter route ownership matrix, the visual comparison command currently points both sides at 8776, and any 100 percent claim is valid only after machine-readable inventory evidence exists.

## Analysis
Evidence reviewed: the planner Summary states the exact target, known facts, and safety boundary; the RALPLAN-DR summary chooses Option A, with V2 default on 8770 and V3 explicit under `/ui/remodel/*` plus optional selector/query/session flag; File-level changes call for explicit dashboard-version dispatch and no broad catchall; the V2 route checklist lists canonical and alias routes that must remain V2 by default; the 8 V3 page checklist inventories the remodel pages and their gaps; Current V3 gaps explicitly names default preservation, main-server selectability, fixture/data, audit persistence, export boundary, exact V2/V3 parity diff, observability, cache contamination, and unknown-route catchall risk; Acceptance and Expanded test plan require focused tests, browser checks, source and DOM safety scans, read-only API evidence, and manual gates for mutating paths.

Architecture assessment: the plan correctly treats route/version ownership as the central contract. That is the right root architecture decision because the supplied facts say 8770 is the current V2 baseline where `/ui/remodel/*` is 404, while 8776 currently serves V3/remodel on canonical routes and `/ui/remodel/*`, with `/` still old V2. The plan also correctly avoids immediate canonical V3 replacement and requires explicit opt-in before any promotion.

Strongest steelman antithesis: the safest rollout could reject V3 selectability on 8770 entirely and keep V3 as a separate-port preview until parity proof is complete. This would avoid injecting selector state, links, cache markers, and route dispatch into the stable V2 surface; it would reduce duplicate asset contamination; and it would prevent a user from mistaking a research preview for an approved production dashboard. This objection is strongest because the planner itself admits exact V2/V3 parity diff, audit persistence, export boundary, fixture/data provenance, and observability artifacts are not complete.

Synthesis: Option A remains better than a separate-port-only plan because the user explicitly wants V2 preserved and V3 selectable where possible. The correct synthesis is not to replace canonical routes, and not to rely on port separation alone, but to add a narrow, observable, reversible selector with a route-by-route ownership matrix, V2 default tests, no broad catchall, and evidence-gated promotion. V3 can be selectable only as a preview until the inventory, safety, and append-only audit evidence pass.

## Root Cause
The fundamental risk is that two dashboard generations currently coexist without a formal, executable ownership contract for route, asset, cache, data provenance, and side-effect authority. The planner identifies this risk, but execution still needs a single source of truth so canonical V2 routes, explicit V3 routes, query/session selection, redirects, unknown routes, assets, and safety gates cannot drift independently.

## Findings
- MEDIUM — `stage-01-planner.md` sections File-level changes, V2 route checklist, and Sequencing: route/version ownership is directionally correct but not yet specified at implementation granularity. Impact: a selector or dispatch change could accidentally make V3 canonical, leave `/ui/remodel/*` unavailable on the main server, or allow broad catchalls to mask broken routes. Fix: add a route ownership matrix before execution with columns for route, default version, selectable version, selection mechanism, expected title, expected asset marker, cache policy, redirect behavior, 404 behavior, and test owner.
- MEDIUM — `stage-01-planner.md` Verification: the visual comparison extension says `--compare-base-url http://127.0.0.1:8776` while the comparison target is 8770. Impact: the visual gate could compare V3 against V3 and falsely support a 100 percent or parity claim. Fix: compare the V3 preview base URL to `http://127.0.0.1:8770/` and store the side-by-side route matrix that proves which side is V2 and which side is V3.
- MEDIUM — `stage-01-planner.md` Current V3 gaps and Acceptance criteria: the plan honestly says exact V2/V3 parity diff is not complete, so 100 percent is not currently verifiable. Impact: execution could ship a visually improved dashboard with missing V2 functions, fixture-only panels, or unwired controls. Fix: make the inventory machine-readable with stable item IDs, source evidence, V2 status, V3 status, safety status, missing reason, owner, and closure evidence; fail the gate on any unexplained missing or unsafe item.
- LOW — `stage-01-planner.md` File-level changes: separate edits to V2 frontend files and V3 remodel files risk duplicate frontend drift. Impact: route labels, selector behavior, safety badges, and approval wording can diverge over time. Fix: keep one route/version manifest or generated contract consumed by tests, with minimal V2 selector injection and no duplicated business logic in the old shell.
- LOW — `stage-01-planner.md` 8 V3 page checklist and Acceptance criteria: safety boundaries are well represented, but audit persistence and export separation remain future proof obligations. Impact: buttons that look safe can still imply approval or mutation if not backed by negative network evidence. Fix: require append-only audit proof, explicit export gate proof, and forbidden network scan artifacts before promotion.

## Recommendations
1. Keep Option A: V2 default on 8770, V3 only via explicit `/ui/remodel/*` or selector/query/session preview, 8776 as remodel preview, no immediate canonical replacement.
2. Before implementation, add the route ownership matrix and make it the acceptance source for route dispatch tests.
3. Correct the visual comparison target so 8776 V3 is compared against 8770 V2, not against another 8776 page.
4. Define the 100 percent inventory schema and require unresolved gaps to block promotion, not merely appear in notes.
5. Minimize duplicate frontend drift with a shared manifest and tests for titles, assets, cache headers, safety labels, and forbidden calls.
6. Preserve the Ralplan boundary: planning only until explicit human approval; no product edits, no project-wide tests, no broker login, no live order, no account trading.

## Architectural Status
WATCH

## Product Status
WATCH

## Code Status
WATCH

## Code Review Recommendation
COMMENT

## Trade-offs
| Option | Benefit | Cost or Risk | Verdict |
| --- | --- | --- | --- |
| Separate-port preview only | Lowest risk to V2; no selector mutation in stable UI | Fails the user need for selectability in the main surface and delays integration feedback | Useful fallback, not enough as final plan |
| Option A explicit V3 selection | Preserves V2, makes V3 observable and reversible, supports staged promotion | Needs precise route dispatch, selector tests, cache isolation, and inventory proof | Best plan if the findings above are applied |
| Immediate canonical V3 replacement | Fastest path to one frontend | Violates V2 preservation, weak rollback, high risk of missing functions and unsafe controls | Reject until explicit approval and complete evidence |

Overall verdict: the planner plan is sound enough to proceed to refinement or approved execution planning with comments. It should not be treated as proof of 100 percent completion, and it should not permit canonical V3 replacement until the inventory, route ownership, safety, and comparison evidence are complete.
