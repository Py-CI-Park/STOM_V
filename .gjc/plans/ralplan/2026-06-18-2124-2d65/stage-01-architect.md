## Summary
Architectural status: `BLOCK`; code-review recommendation: `REQUEST CHANGES`. The dashboard improvement architecture is directionally sound for Option A, the governed research index first plan, and it preserves HoF divergence plus dirty `wt-dev` protection. Approval is blocked because the branch-base contract in the planner artifact is contradicted by inspected evidence: the artifact requires `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7`, while repository evidence records the origin branch as absent and the local anchor as `84acb6cb`.

The implementation plan should be revised before approval: establish the canonical anchor, correct the SHA and branch commands, and make the governed index schema and allowlist contract explicit. After that correction, Option A is the right execution shape.

## Analysis
### Spec compliance
- User goals: new branch from `STOM_Version_2U_C-ai-strategy-loop`, dashboard improvements, full-audit or research feature improvement, duplicate reduction, usability, all-record lookup, process visualization, realtime process node flowchart, and speed improvements.
- The planner artifact covers most dashboard goals: governed index, all-record lookup, Research Records and Wiki cross-links, HoF labels instead of merging, process-flow extraction, and performance instrumentation are explicit in `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-01-planner.md`.
- Existing backend shape supports the need for a governed index: `ai_strategy_loop/dashboard/research_api.py` currently exposes `/research_docs`, `/research_doc`, `/research_records`, and `/research_records/detail`; docs are limited by `_DOC_ROOTS` plus `_SELECTED_UPDATE_LOGS`, so a governed index would remove a real manual-allowlist bottleneck.
- Existing research records are campaign-scoped only: `ai_strategy_loop/dashboard/research_records.py` reads `.omo/evidence/tmap-walkforward` summaries, jsonl, pairs, and logs, and guards campaign detail with `_SAFE_CAMPAIGN`; this is a good compatibility base but not an all-record lookup by itself.
- Existing frontend panels are separate consumers: `research-records-panel.jsx` fetches `/research_records` and `/research_records/detail`, while `research-wiki.jsx` fetches `/research_docs` and `/research_doc`; the planned cross-link and index layer fits the current architecture without forcing a panel merge.
- Existing process-flow code already consumes `latest.current_step`, `phase_started_at`, `gen_started_at`, `step_timings`, and recent logs in `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`; extracting diagram helpers while preserving public exports is architecturally low-risk.

### HoF divergent-by-design preservation
Confirmed preserved. The plan explicitly says not to merge Evolution `HallOfFamePanel` and Research Pro `_RpHallOfFame`. Source and test evidence supports this boundary: `tests/unit/dashboard/test_p3_consolidation.py` documents the two HoF surfaces as field-diff divergent, with different columns, CSS, and functions, and asserts `function HallOfFamePanel(` in `chart-hall-of-fame.jsx` and `function _RpHallOfFame(` in `rp-heatmap.jsx`. The proposed label-only change respects that invariant.

### Dirty `wt-dev` protection
Confirmed as a principle and execution intent. The plan requires a clean worktree and says not to reset, stash, or stage dirty `C:/System_Trading/STOM/STOM_V.wt-dev`. This is necessary: `.omo/evidence/stom-reorg-20260618/dirty-worktree-inventory.md` records 443 dirty status lines, and `safety-snapshot.txt` shows `wt-dev` on `lazycodex/tick-sparse-positive-generation-improvement-20260604`, ahead of its upstream, with many tracked and untracked dashboard or research artifacts. Protected runtime status is clean in `protected-path-status.txt` and `final-protected-path-status.txt`.

### Strongest steelman antithesis against Option A
The strongest case against the conservative research-index-first option is that it may entrench dashboard fragmentation. The user asked for duplicate reduction, usability, process visualization, all-record lookup, and speed; a broad consolidation branch could attack visible duplicated empty, error, and status states, route naming confusion, and UX inconsistencies in one pass instead of adding a new index layer beside existing Research Records and Wiki panels. Option A also adds a new route, schema, and caching surface that can drift from raw evidence unless governance is precise, while it defers some high-visibility cleanup called out in `.omo/evidence/stom-reorg-20260618/dashboard-improvement-backlog.md`, including route naming audit and shared state components.

The antithesis does not win because existing tests and source comments show several surfaces are intentionally divergent. A broad consolidation would risk merging semantically different HoF, workbench, and process views and would be harder to review in a dirty, multi-branch repository. The index-first path produces operator value while keeping rollback localized.

## Root Cause
The blocking defect is branch-base ambiguity, not the dashboard design. The planner artifact hard-codes a future branch base of `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7`, but inspected evidence in `.omo/evidence/stom-reorg-20260618/branch-map.md` says the local anchor is `STOM_Version_2U_C-ai-strategy-loop` at `84acb6cb` and the remote anchor is absent. `.omo/evidence/stom-reorg-20260618/pr-restart-strategy.md` also says `origin/STOM_Version_2U_C-ai-strategy-loop` is absent and must be pushed before it can be used as a PR base.

This means the first execution command can fail or target an unproven base, and the acceptance criterion cannot currently be verified from inspected repository evidence.

## Findings
1. **HIGH — Branch base and SHA contract are contradictory**
   - Reference: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-01-planner.md` lines 4, 31, 73-90; `.omo/evidence/stom-reorg-20260618/branch-map.md`; `.omo/evidence/stom-reorg-20260618/pr-restart-strategy.md`.
   - Impact: Future execution cannot safely create the requested branch as written. A clean-worktree command based on an absent origin branch or wrong SHA undermines reviewability and may cause implementation to start from the wrong commit lineage.
   - Fix: Revise the plan to include an explicit precondition: publish, fetch, or otherwise establish `STOM_Version_2U_C-ai-strategy-loop` on origin, verify the exact SHA, and update every branch command and acceptance criterion to the observed canonical anchor. If the correct base is local-only, say so and require read-only verification before any worktree creation.

2. **MEDIUM — Governed index schema needs a collision and source-authority contract**
   - Reference: `research_api.py` currently uses relative markdown IDs and a selected update-log allowlist; `research_records.py` currently uses campaign names and artifact filenames; `.omo/evidence/stom-reorg-20260618/research-registry.md` defines registry fields but not a dashboard ID namespace.
   - Impact: A unified all-record lookup over campaigns, docs, update logs, and registry artifacts can collide or mislead users if IDs, `kind`, `source_path`, canonicality, and derived-vs-raw authority are not explicit.
   - Fix: Define stable IDs as namespaced records, for example `campaign:<name>`, `doc:<repo-rel-path>`, `update_log:<repo-rel-path>`, `registry:<machine_name>`, or equivalent. Include canonical, derived, source-of-truth fields and tests for collisions, traversal, missing files, and malformed IDs.

3. **MEDIUM — `.omo/evidence/stom-reorg-20260618` exposure needs a precise allowlist**
   - Reference: plan scope includes `.omo/evidence/stom-reorg-20260618` registry artifacts; `research-source-inventory.md` distinguishes canonical raw evidence, derived artifacts, drift, and cautions; `research-registry.md` states it does not replace raw jsonl, summary, OOS records, or update logs.
   - Impact: Indexing the whole evidence directory would expose QA captures, screenshots, logs, or stale planning files as if they were governed research facts.
   - Fix: Restrict the dashboard index to specific registry or source-inventory files, or to a machine-readable registry JSON with declared categories. Keep raw evidence as links, not promoted claims, and preserve warnings such as CSV reanalysis not being official OOS.

4. **LOW — Performance plan should specify freshness and cache invalidation boundaries**
   - Reference: the plan calls for metadata-only responses, lazy detail endpoints, optional mtime cache, debounce, `useMemo`, and timing capture.
   - Impact: A cache can improve speed but risks hiding newly-created evidence if invalidation is too coarse; no persistent cache writes are allowed.
   - Fix: Document cache key inputs and invalidation, such as `mtime_ns`, file size, root path, and maybe max age. Keep cache process-local, expose no persistent cache files, and test that file additions and removals are visible after invalidation.

5. **LOW — Full-audit feature scope should be named more concretely**
   - Reference: backlog ranks route naming contract audit and API contract docs separately; the plan focuses on governed research index first.
   - Impact: The phrase "full-audit feature improvement" can be interpreted as route-contract audit, evidence-lineage audit, or all-record research audit.
   - Fix: Add a one-paragraph definition: this branch audit improvement is the governed all-record and evidence-lineage lookup; route naming contract audit remains deferred unless explicitly pulled into scope.

## Recommendations
1. Block approval until the branch-base precondition is corrected. Update the plan from `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7` to the verified canonical anchor, or add the required anchor-publish and fetch step plus verification evidence before execution.
2. Keep Option A after the branch correction. The source layout and tests favor a bounded governed-index-first branch over broad consolidation.
3. Define the research-index contract before implementation: namespaced IDs, kind, source, category fields, canonicality flags, allowlisted paths, safe relative paths, and detail endpoint behavior should be acceptance criteria.
4. Preserve HoF separation and add labels only. This matches the existing divergent-by-design regression test.
5. Keep process-flow extraction conditional. Extract only if realtime additions would grow `phase-detail.jsx`; preserve `PhaseDetailPanel`, `PhaseTimeline`, `ProcessFlowPanel`, `ProcessFlowDiagram`, and timing semantics.
6. Keep focused verification only. The plan correctly avoids project-wide gates and instead lists dashboard API, frontend, process-flow, and build harness checks for future execution.

## Architectural Status
`BLOCK`

## Code Review Recommendation
`REQUEST CHANGES`

## Trade-offs
| Tension | Option 1 | Option 2 | Recommendation |
|---|---|---|---|
| Research index vs broad UI consolidation | Add governed all-record lookup first, keep panels separate | Consolidate shared empty, error, status, and domain components broadly | Choose index first after branch-base fix; it gives highest research value and lower regression risk. |
| Backwards compatibility vs richer payloads | Keep `/research_records` and `/research_docs` stable, add `/research_index` | Extend existing payloads aggressively | Prefer a new index or helper route plus optional backwards-compatible metadata only after tests. |
| Speed vs freshness | Cache metadata and lazy-load detail | Re-scan every source on each request | Use process-local mtime and size invalidated cache; never persistent cache writes. |
| Duplicate reduction vs divergent domain behavior | Label and extract tiny helpers only | Merge HoF, Research Pro, and process components | Preserve divergence where tests and comments say behavior differs; reduce duplication only after field equivalence is proven. |
| Clean branch isolation vs current dirty context | Use clean worktree from verified anchor | Work inside dirty `wt-dev` | Clean worktree only, but first fix the missing or contradictory origin anchor. |
