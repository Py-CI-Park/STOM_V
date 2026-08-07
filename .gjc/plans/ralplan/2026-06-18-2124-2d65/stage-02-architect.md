## Summary
Architectural status: `CLEAR`; code-review recommendation: `APPROVE`. The revised plan resolves the prior `BLOCK` findings at the planning layer by turning branch-base ambiguity into a fail-closed preflight and by making the research index schema, `.omo` exposure boundary, cache invalidation, and full-audit scope explicit.

Approval is for the pending plan only, not for execution proof: the future execution must still run the stated fetch/SHA preflight before any worktree creation and must stop on mismatch.

## Analysis
### Spec compliance and prior finding closure
- Prior architect review blocked approval because stage 1 required `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7` while inspected historical evidence recorded local anchor `84acb6cb` and no remote anchor (`stage-01-architect.md` lines 2, 26-35; `.omo/evidence/stom-reorg-20260618/branch-map.md`; `.omo/evidence/stom-reorg-20260618/pr-restart-strategy.md`).
- The revision now explicitly identifies `.omo/evidence/stom-reorg-20260618/branch-map.md` as stale historical evidence and requires a future preflight before any worktree creation: fetch `origin STOM_Version_2U_C-ai-strategy-loop`, verify local and remote anchor both resolve to `7d7187f7`, and stop/revise if either differs (`stage-02-revision.md` lines 6-11, 61-72). This fixes the architecture defect because execution is fail-closed before mutation.
- Governed index schema is now concrete enough for implementation: namespaced IDs (`campaign:`, `doc:`, `update_log:`, `registry:`), required fields, canonicality/source-authority labels, and rejection of traversal, malformed namespaces, missing files, and disallowed stale entries (`stage-02-revision.md` lines 35-42). This directly addresses the prior collision/source-authority finding.
- `.omo/evidence/stom-reorg-20260618` is now allowlisted rather than wholesale-indexed. The revision permits only registry/source-inventory inputs and explicitly excludes QA screenshots, browser captures, smoke logs, safety snapshots, dirty status dumps, stale branch maps, split strategy files, and planning files as facts (`stage-02-revision.md` lines 44-45). This aligns with `research-source-inventory.md`, which distinguishes canonical raw evidence, derived artifacts, drift, and cautions, and with `research-registry.md`, which says the registry does not replace raw jsonl, summary, official OOS records, CSVs, or update logs.
- Cache behavior is now specified: process-local only, no persistent writes, key includes root path plus each included source path, `mtime_ns`, and size; rebuild on allowlisted add/remove/mtime/size changes; test roots do not share results (`stage-02-revision.md` lines 57-58). This fixes the freshness boundary gap.
- Full-audit scope is now defined as governed all-record and evidence-lineage lookup, while broad route naming audit and generic dashboard consolidation are out of scope (`stage-02-revision.md` lines 13-33). This removes the ambiguity called out in the prior LOW finding.

### Fit with inspected code boundaries
- `ai_strategy_loop/dashboard/research_api.py` currently has separate legacy docs and records routes (`/research_docs`, `/research_doc`, `/research_records`, `/research_records/detail`) and a narrow `_DOC_ROOTS` plus `_SELECTED_UPDATE_LOGS` model. Adding `/research_index` or an equivalent helper while preserving those routes matches the existing boundary and avoids breaking consumers.
- `ai_strategy_loop/dashboard/research_records.py` is campaign-scoped under `.omo/evidence/tmap-walkforward` and already guards detail lookup with `_SAFE_CAMPAIGN`; the new plan correctly treats it as a compatibility source/helper, not as the entire all-record index.
- `research-records-panel.jsx` and `research-wiki.jsx` are separate consumers of records and docs. The wiki renders markdown in a `<pre>` and tests assert no `dangerouslySetInnerHTML`; the planned inert rendering, lazy details, and source badges preserve that safety posture.
- HoF separation remains an explicit invariant. `tests/unit/dashboard/test_p3_consolidation.py` documents that `HallOfFamePanel` and `_RpHallOfFame` are field-diff divergent, and the revision limits work to labels only (`stage-02-revision.md` lines 47-55, 71-79).
- `phase-detail.jsx` already owns `FLOW_STEPS`, `ProcessFlowDiagram`, `ProcessFlowPanel`, current-step mapping, `phase_started_at`, `gen_started_at`, and `step_timings`; the conditional extraction in the revision only if realtime flow grows the file is the least risky path.

### Strongest steelman antithesis against Option A
The strongest case against the chosen research-index-first option is that it may preserve dashboard fragmentation. A broad consolidation branch could address route naming drift, repeated empty/error/loading UI states, and cross-panel usability in one visible pass, while a new `/research_index` route introduces another contract, another cache, and another UI entry point that could drift from legacy docs/records routes.

That antithesis does not win here. The inspected codebase already has intentionally divergent surfaces, especially the two HoF components, and the repository has dirty `wt-dev` state that makes broad route/UI consolidation difficult to review safely. Option A gives operator value through all-record lookup and evidence lineage while preserving rollback locality and compatibility.

## Root Cause
The original blocker was not the dashboard feature choice; it was an unsafe execution contract plus underspecified evidence governance. The revision fixes that root cause by requiring SHA verification before branch/worktree mutation and by turning the all-record lookup into a governed index with namespaces, authority labels, allowlists, and freshness rules.

## Findings
1. **LOW — Capture the future SHA preflight as execution evidence**
   - Reference: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-02-revision.md` lines 6-11, 61-72; stale contradictory evidence remains in `.omo/evidence/stom-reorg-20260618/branch-map.md` and `pr-restart-strategy.md` by design.
   - Impact: The plan is safe because it stops on mismatch, but reviewers will need a durable receipt showing that local and remote anchor actually resolved to `7d7187f7` at execution time.
   - Fix: In execution, record the fetch/verify result in the PR or execution evidence before creating the dashboard worktree. Do not rely on the stale `.omo` branch map.

2. **LOW — Freeze canonicality and source-authority values in implementation tests**
   - Reference: `stage-02-revision.md` lines 35-42.
   - Impact: The schema names the right fields, but terms like canonical, derived, historical, stale, reference, candidate, raw campaign, curated doc, selected update log, registry entry, and historical planning context should not become free-form labels that drift across rows.
   - Fix: Implement them as a small enum or constant set and test representative rows and detail rejection cases.

3. **LOW — Keep the `.omo` registry parser deterministic**
   - Reference: `stage-02-revision.md` lines 44-45; `.omo/evidence/stom-reorg-20260618/research-registry.md`; `.omo/evidence/stom-reorg-20260618/research-source-inventory.md`.
   - Impact: If no machine-readable `research-registry.json` is available, scraping markdown tables can be brittle and could accidentally promote prose notes as facts.
   - Fix: Prefer a machine-readable registry or a deliberately narrow markdown-table parser with tests for allowed rows, excluded files, and authority downgrades.

No HIGH or MEDIUM issues remain. No principle violation remains in the revised plan: dirty `wt-dev` is protected, protected runtime paths and V3K/live/export/dependency changes are out of scope, HoF divergence is preserved, project-wide gates remain skipped, and execution remains pending approval.

## Recommendations
1. Approve the revised Option A plan for pending execution.
2. Treat the branch preflight as mandatory and fail-closed: fetch, verify local and remote anchor SHA, persist the receipt, then create the clean worktree only if both match.
3. Implement the research index as a separate governed helper/route while preserving `/research_records`, `/research_records/detail`, `/research_docs`, and `/research_doc` contracts.
4. Keep `.omo` exposure narrow: registry/source-inventory facts may point to raw evidence as lineage, but stale planning and QA artifacts must not become authoritative dashboard facts.
5. Add focused tests for namespace parsing, traversal rejection, malformed IDs, allowlist exclusions, add/remove/mtime/size cache invalidation, and root isolation.
6. Keep broad route naming audit and UI consolidation deferred unless explicitly re-scoped.

## Architectural Status
`CLEAR`

## Code Review Recommendation
`APPROVE`

## Trade-offs
| Tension | Option 1 | Option 2 | Recommendation |
|---|---|---|---|
| Strict branch SHA preflight vs execution agility | Stop and revise on any local/remote anchor mismatch | Proceed from best-known branch state | Use strict preflight; reviewability matters more than speed. |
| New governed index vs extending legacy routes | Add `/research_index` or helper while preserving records/docs routes | Fold all metadata into existing records/docs payloads | Prefer the governed index to avoid breaking existing consumers and to isolate all-record semantics. |
| `.omo` allowlist precision vs completeness | Index only registry/source-inventory facts and link raw evidence as lineage | Index the whole evidence directory for maximum discoverability | Choose precision; false authority over stale screenshots/logs is worse than omitted convenience links. |
| Cache speed vs evidence freshness | Process-local cache keyed by root/path/mtime/size with add/remove invalidation | Re-scan every request or persist cache files | Use process-local invalidated cache; no persistent writes. |
| Duplicate reduction vs divergent domain behavior | Labels and tiny helpers only | Merge HoF/process/domain panels broadly | Preserve divergence now; consolidate only where field equivalence is proven. |

## Synthesis
The revised plan is architecturally sound because it narrows the branch to a governed research/evidence-lineage improvement, protects existing routes and dirty worktree state, and converts every prior blocker into an explicit contract with acceptance criteria. The remaining risks are implementation hygiene items, not planning blockers.
