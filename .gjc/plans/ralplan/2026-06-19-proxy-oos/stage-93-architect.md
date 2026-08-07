## AI SLOP CLEANUP REPORT
Status: BLOCK

## Summary
The sweep found two blocking slop issues against the G002 Phase 2 History ownership contract. The route-alias test coverage is present, but the static ownership inventory still treats records/search as a separate owner and the Workbench duplicate test can false-pass.

## Analysis
- `ai_strategy_loop/dashboard/frontend/visual-quality.jsx:4` labels the `records` route as `히스토리`, so the visual baseline file does not block the History naming objective. Its `surface: "records"` performance key at line 13 appears to be an internal route key rather than a user-facing duplicate owner.
- `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx:12` still names the `records` owner `전체 기록 조회`, sets `owns` to campaign/docs/update_log/registry lineage search, and points `primarySurface` to `ResearchIndexPanel`. This conflicts with the G002 contract that History owns the run/gen archive, ResultDetail, and Compare.
- `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx:19` makes `PHASE2_SOURCE_INVENTORY` for `records` owned by `research-index.jsx` and `GET /research_index`, omitting `research-records-panel.jsx` and the History ResultDetail/Compare archive responsibility.
- `tests/unit/test_dashboard_route_parity.py:44-46` pins `/ui/history` and `/ui/evolution/history` to `/ui/evolution/records`, and `tests/unit/test_dashboard_route_parity.py:121-124` verifies redirect status plus `location`. Route alias coverage meets the G002 contract.
- `tests/unit/dashboard/test_dashboard_ui_remodel.py:44-48` pins `ResultDetailBody` as shared/presentational by checking it exists, does not fetch in the body block, carries `sourceContext`, and is exported to charts.
- `tests/unit/dashboard/test_dashboard_ui_remodel.py:50-57` does not fully pin ownership behavior: the History-positive assertions are whole-file string checks and the Workbench-negative assertions only inspect the `rp-grid` slice before `{showFlow &&`.

## Root Cause
The cleanup appears partially applied: runtime/source files moved ResultDetail and Compare into History, while the older Phase 2 inventory and substring-based tests kept pre-cleanup Records/Search assumptions and layout-specific slices.

## Findings
1. HIGH - `ai_strategy_loop/dashboard/frontend/dashboard-inventory.jsx:12-19`
   Impact: The static ownership inventory still presents `records` as a separate full-record/search owner backed by `ResearchIndexPanel` and `GET /research_index`, not as the History archive owner. This can reintroduce duplicate Records/Search ownership and contradicts the G002 source of truth that History owns run/gen ResultDetail and Compare.
   Fix: Keep the internal `records` route key if required, but rename the owner/contract to History, set the primary surface to the History/records panel, include `research-records-panel.jsx`, and describe research-index search as a capability inside History rather than a separate owner. Include ResultDetail/Compare/run/gen archive sentinels.

2. HIGH - `tests/unit/dashboard/test_dashboard_ui_remodel.py:50-57`
   Impact: The test can pass even if Workbench renders `<_RpRunCompare>` or `<_RpHistory>` outside the narrow `workbench_grid` slice, for example after `{showFlow &&`. The positive History checks can also pass from comments or dead text because they scan the whole file.
   Fix: Extract the full `ResearchProPanel` component/render scope and assert `<_RpRunCompare` and `<_RpHistory` are absent there. Extract the active `ResearchRecordsPanel` History section and assert the History label, ownership sentence, and both component tags occur together in that rendered section.

## Recommendations
1. Fix `dashboard-inventory.jsx` first so every product-visible static contract calls the archive surface History while preserving the canonical `/ui/evolution/records` route key.
2. Tighten `test_dashboard_ui_remodel.py` ownership assertions to component/section scopes instead of whole-file presence and current-layout substring gaps.
3. Keep `test_dashboard_route_parity.py` alias checks as written; they directly cover `/ui/history` and `/ui/evolution/history` canonicalization without broad catchall behavior.
4. No tests, build, lint, formatters, or Ultragoal checkpoint were run, per assignment constraints.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
| Option | Benefit | Risk | Recommendation |
| --- | --- | --- | --- |
| Keep route key `records` and relabel contracts to History | Preserves URL/API compatibility while removing duplicate ownership language | Requires clear distinction between internal key and user-facing owner | Preferred |
| Rename all internal keys from `records` to `history` | Semantic purity | High churn and unnecessary alias risk | Avoid for this cleanup |
| Static component-scope tests | Fast and aligned with current contract-test style | Still less complete than rendered tests | Preferred minimum |
| Browser/render tests for ownership | Stronger behavioral proof | Outside this read-only sweep and heavier | Consider later only if regressions recur |
