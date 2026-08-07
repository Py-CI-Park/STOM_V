## Summary
G005 is not ready. The inspected files preserve the generic LoopState.page_data/status seam and keep existing winner/export authority on hard gates plus final approval, but they do not publish or render condition-discovery policy/evidence/advisory-score/persistence feedback.

Recommendation: REQUEST CHANGES. Add an additive, null-safe condition-discovery payload and UI consumer through the existing seams; do not introduce route rewrites or allow advisory scores to affect best/winner/export selection.

## Analysis
### Spec compliance
- Backend status/page_data seam exists: `_publish_live` accepts optional `page_data` and passes it to `to_loop_state` before `publish_loop_state` (`ai_strategy_loop/controller/loop.py:818-956`).
- The current page_data builder emits only `autopsy`, optional `holdout`, `lineage`, and optional `meta` (`ai_strategy_loop/controller/loop.py:1818-1869`). There is no condition-discovery policy/evidence/advisory-score/persistence section in the reviewed files.
- The only generation-complete page_data publication calls `_build_live_page_data(...)` and passes it at `generation_done` (`ai_strategy_loop/controller/loop.py:1581-1595`), but final `complete` status is published without page_data (`ai_strategy_loop/controller/loop.py:1599-1611`), so any generation-only page_data would be cleared unless carried forward.
- The evolution UI renders the heatmap, ResearchLabPanel, and existing P1-P5 analysis panels (`ai_strategy_loop/dashboard/frontend/app.jsx:415-469`) but no condition-discovery status/policy/evidence/advisory panel.
- `panels-analysis.jsx` consumes only existing autopsy, lineage, and holdout page_data sections (`ai_strategy_loop/dashboard/frontend/panels-analysis.jsx:146-330`).
- The reviewed unit test still covers P3/P4 lineage/meta/autopsy page_data and serialization only (`tests/unit/test_loop_lineage_meta_wiring.py:1-8`, `:65-89`). It does not guard G005 payload shape or advisory-only semantics.

### Architecture
- The intended architecture should be additive: keep `/status` and `LoopState.page_data` as the transport, add a namespaced condition-discovery payload, and render it in the existing evolution dashboard groups.
- Current code is authority-safe by omission: selection and export are still driven by graded best, hard-gated winner, holdout gate, and `final_approval` on `state.winner` (`ai_strategy_loop/controller/loop.py:1489-1545`, `ai_strategy_loop/dashboard/frontend/app.jsx:220-231`). However, because condition-discovery scores are absent, the review cannot verify their advisory-only handling.
- Product navigation mostly preserves access to records/lab/workbench/verdict via canonical evolution subtabs (`ai_strategy_loop/dashboard/frontend/app.jsx:368-393`) and workspace cards (`ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx:80-100`). The Lab page still includes an active `연구실` card that navigates to `lab` while already on the Lab page, so duplicate self-navigation is not fully removed.

### Code quality / maintainability
- Existing page_data code is appropriately null-safe and failure-isolating for auxiliary data, but the required G005 data model is missing.
- Adding the payload in `_build_live_page_data` and a small UI panel would fit existing conventions better than any route rewrite.
- Tests need to extend the existing page_data wiring test rather than adding a project-wide gate.

## Root Cause
The change appears to have rearranged existing dashboard surfaces and retained existing P1-P5 status wiring, but it never introduced a G005-specific condition-discovery data contract. Without a backend payload, UI consumer, and targeted test, policy/evidence/advisory/persistence feedback cannot be verified or displayed.

## Findings
1. HIGH — `ai_strategy_loop/controller/loop.py:1818-1869`: `_build_live_page_data` does not publish condition-discovery policy/evidence/advisory-score/persistence feedback. Impact: `/status` cannot satisfy G005. Fix: add a namespaced, null-safe condition-discovery section sourced from the discovery state; keep scores explicitly advisory.
2. HIGH — `ai_strategy_loop/dashboard/frontend/app.jsx:415-469`: `/ui/evolution` has no panel/banner/card for condition-discovery status. Impact: published G005 data would not be visible. Fix: render a small consumer in the existing Research Lab or analysis section without changing routes.
3. MEDIUM — `ai_strategy_loop/controller/loop.py:1599-1611`: final `complete` publication omits page_data. Impact: generation-complete status data can disappear after completion, undermining persistence feedback. Fix: rebuild/carry latest page_data into the final status publish.
4. MEDIUM — `ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx:80-100` and `:197-199`: LabPage renders a Lab card that self-navigates to `lab`. Impact: duplicate self-navigation remains. Fix: disable/omit the active workspace card action while preserving records/workbench/verdict links.
5. MEDIUM — `tests/unit/test_loop_lineage_meta_wiring.py:1-8`, `:65-89`: no G005 page_data/advisory-only test coverage. Impact: seam regressions are unguarded. Fix: add minimal unit coverage for payload round-trip and advisory-only labels/fields.

## Recommendations
1. Add `page_data.condition_discovery` (or a documented equivalent) in `_build_live_page_data` with fields for policy, evidence, advisory scores, persistence feedback, and human pattern-card creativity status.
2. Carry/rebuild the latest page_data during final `complete` status publication.
3. Add a null-safe evolution-dashboard panel under the existing Research Lab/analysis grouping; mark advisory scores as non-authoritative and do not feed them into best/winner/export paths.
4. Remove active self-navigation in workspace cards while preserving records/lab/workbench/verdict access.
5. Extend `test_loop_lineage_meta_wiring.py` with focused G005 seam coverage only.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
- Additive page_data section: preferred; preserves existing `/status` and dashboard seams with minimal coupling.
- New route/API: not recommended; increases surface area and violates the broad-route-rewrite constraint.
- Reusing existing ResearchLabPanel only: acceptable only if it receives and labels the condition-discovery status; currently the reviewed integration does not show that contract.
