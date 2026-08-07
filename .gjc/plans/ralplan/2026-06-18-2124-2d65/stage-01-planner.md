# RALPLAN-DR short: Dashboard improvement branch plan

## Summary
Plan a pending-approval execution branch from `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7`. The branch should protect dirty `wt-dev` by using a clean worktree and should improve dashboard research management first: all-record lookup, governed index, safe duplicate reduction, process-flow clarity, usability labels, and incremental performance. No source execution is approved by this artifact.

## Principles
1. Clean branch only: do not reset, stash, or stage dirty `C:/System_Trading/STOM/STOM_V.wt-dev`.
2. Research IA before component merging: connect records, docs, update logs, and evidence before collapsing UI.
3. Preserve divergent-by-design surfaces: Evolution HoF and Research Pro HoF remain separate.
4. Keep dashboard changes read-only against research evidence and runtime state; no protected DB or live export writes.
5. Decompose near-threshold frontend modules; do not grow `phase-detail.jsx` or other 700+ line files.

## Top decision drivers
1. Operator value: fast lookup across campaigns, docs, update logs, and evidence beats cosmetic cleanup.
2. Regression risk: dashboard route contracts and standalone Lab/Pro/Verdict pages already have harness coverage.
3. Worktree safety: unrelated dirty research/dashboard artifacts in `wt-dev` require isolated execution.

## Options
### Option A - chosen: conservative research-index-first branch
Pros: highest research value, preserves HoF/process divergence, limited backend and frontend surface, easy rollback, compatible with existing tests. Cons: does not immediately redesign every duplicated visual state.

### Option B: broad dashboard consolidation branch
Pros: could reduce more duplicated empty/error/status rendering in one pass. Cons: higher risk across many panels, likely grows near-threshold files, obscures HoF divergence, harder review.

### Option C: process-flow-only branch
Pros: small and visually focused. Cons: misses user priority for full audit, all-record lookup, and research governance.

Chosen option: Option A. It can include small labels and flow extraction, but the first acceptance anchor is the governed research index.

## In scope
- Future clean branch/worktree creation from `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7`.
- Read-only governed research index over Research Records, Research Wiki/docs, selected update logs, and `.omo/evidence/stom-reorg-20260618` registry artifacts.
- All-record lookup UI with filters, source badges, detail lazy-load links, and campaign-to-doc/evidence navigation.
- Safe duplicate reduction by labeling and helper extraction only where behavior remains unchanged.
- Realtime process node flowchart using current `state.latest.current_step`, `step_timings`, `phase_started_at`, and recent logs.
- Incremental performance improvements with measurable before/after timings.

## Out of scope and protected paths
- No V3K gate movement, default-ON feature flags, KHOPENAPI login, live broker/runtime wiring, strategy export, final approval, or strategy DB writes.
- No writes under `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, or `_v3k_sidecar/`.
- No dependency additions unless explicitly approved.
- No project-wide build/test/lint/format gates for role agents. Future execution uses focused dashboard checks only.
- No merging of Evolution `HallOfFamePanel` and Research Pro `_RpHallOfFame`.

## File-level changes
### Backend research index
- `ai_strategy_loop/dashboard/research_records.py`: preserve existing `/research_records` behavior; add optional metadata fields only if tests prove backwards compatibility, or expose them through a new helper.
- `ai_strategy_loop/dashboard/research_api.py`: replace the narrow `_SELECTED_UPDATE_LOGS` model with a governed read-only index path or add `/research_index` and `/research_index/detail` while keeping `/research_docs`, `/research_doc`, `/research_records`, and `/research_records/detail` stable.
- Candidate new helper `ai_strategy_loop/dashboard/research_index.py`: build normalized records with `id`, `kind`, `title`, `category`, `source_path`, `updated_at`, `campaign`, `tags`, `summary`, and `detail_available`; enforce repo-root relative safe paths.

### Frontend research management
- `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`: add source badges, related docs/evidence links, and all-record lookup entry without changing existing campaign detail flow.
- `ai_strategy_loop/dashboard/frontend/research-wiki.jsx`: consume the same index metadata for categories and links; render markdown as inert text as current tests require.
- `ai_strategy_loop/dashboard/frontend/app.jsx` and `dashboard-pages.jsx` only for navigation placement, labels, or props. Avoid centralizing business logic here.
- Optional small helper `research-index-panel.jsx` or `research-index-utils.jsx` if the lookup UI would otherwise bloat records/wiki panels.

### Duplicate clarity
- `ai_strategy_loop/dashboard/frontend/chart-hall-of-fame.jsx` and `rp-heatmap.jsx`: add purpose/source labels only. Evolution HoF = benchmark plus AI generated ranking; Research Pro HoF = workbench expansion and backtest workflow.
- Preserve `tests/unit/dashboard/test_p3_consolidation.py` invariant that HoF components remain separate.

### Process visualization
- `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`: keep `PhaseDetailPanel`, `PhaseTimeline`, and `ProcessFlowPanel` as public exports, but move flow constants, formatting, and SVG drawing helpers to a small process-flow module if implementation grows.
- Candidate new helper `ai_strategy_loop/dashboard/frontend/process-flow-diagram.jsx`: own `FLOW_STEPS`, `fmtElapsedSec`, `fmtClockFromEpoch`, `ProcessFlowDiagram`, node status mapping, and realtime sublabels.
- `ai_strategy_loop/scripts/build_process_flow_html.py` and `docs/process_flow.html`: keep static process page as a source artifact; update only if the branch deliberately regenerates static docs with the same conceptual node model.

### Tests
- `tests/unit/dashboard/test_research_records.py`: cover governed index metadata, path safety, detail lookup, malformed IDs, and backwards-compatible campaign payloads.
- `tests/unit/dashboard/test_research_records_frontend.py` and `tests/unit/test_dashboard_wiki_frontend.py`: cover index UI strings, inert rendering, source badges, and navigation hooks.
- `tests/unit/test_dashboard_phase_mapping.py` and `tests/unit/dashboard/test_p11_process_flow.py`: cover any extracted process-flow module, current-step mapping, timings, SVG classes, and no hardcoded token colors.
- `tests/unit/dashboard/test_no_duplicate_globals.py`: must remain green after adding modules.

## Sequencing and dependencies
1. Future branch setup only after approval: fetch anchor, create a clean worktree branch from `origin/STOM_Version_2U_C-ai-strategy-loop`, confirm it is at `7d7187f7`, and leave `wt-dev` untouched.
2. Baseline focused inspection in the clean worktree: confirm `/research_records`, `/research_docs`, process flow tests, and HoF separation tests before edits.
3. Implement backend governed index as read-only, safe-path, metadata-first. Keep old routes stable.
4. Add all-record lookup UI and cross-links. Use lazy detail fetches for markdown and campaign candidates.
5. Add HoF and GUI/source labels. Do not share component bodies; only share tiny display tokens if needed.
6. Extract process-flow helpers only if new realtime flow work would increase `phase-detail.jsx`. Keep the public panel contract stable.
7. Add performance instrumentation and incremental caching after behavior is correct.
8. Run focused verification, review dirty paths explicitly, then prepare a pending PR only after user approval.

Future branch commands, not to run during planning:
```powershell
git fetch origin STOM_Version_2U_C-ai-strategy-loop
git worktree add ../STOM_V.wt-dashboard-next -b lazycodex/dashboard-research-index-flow-20260618 origin/STOM_Version_2U_C-ai-strategy-loop
git -C ../STOM_V.wt-dashboard-next status --short --branch
```

## Acceptance criteria
- Branch starts from `origin/STOM_Version_2U_C-ai-strategy-loop` at `7d7187f7`; dirty `wt-dev` remains untouched.
- `/research_records` and `/research_records/detail` remain backwards compatible.
- New governed index returns all allowed records with stable IDs, source categories, updated times, safe relative paths, and no traversal.
- All-record lookup can find campaigns, docs, update logs, and approved evidence registry entries from one dashboard path.
- Research Records and Research Wiki cross-link but remain separate task surfaces.
- Evolution HoF and Research Pro HoF remain separate and are clearly labeled by purpose.
- Process flow reflects realtime current node, elapsed timing, completion timing, and recent logs without adding bulky logic to `phase-detail.jsx`.
- No protected path is modified and no new dependency is added.
- Frontend source files remain under the watch threshold; new logic is extracted rather than appended to near-threshold files.

## Verification
Future execution should run only focused dashboard checks, not project-wide gates:
```powershell
pytest tests/unit/dashboard/test_research_records.py -q
pytest tests/unit/dashboard/test_research_records_frontend.py -q
pytest tests/unit/test_dashboard_wiki_frontend.py -q
pytest tests/unit/test_dashboard_phase_mapping.py tests/unit/dashboard/test_p11_process_flow.py -q
pytest tests/unit/dashboard/test_no_duplicate_globals.py -q
cd ai_strategy_loop/dashboard/webui-build; node build-app.mjs
cd ai_strategy_loop/dashboard/webui-build; node check-missing-imports.mjs
cd ai_strategy_loop/dashboard/webui-build; node track-z-harness.mjs
```
Manual/API smoke for future execution: `/ui/`, `/research_records`, `/research_records/detail?campaign=<known>`, `/research_docs`, `/research_doc?id=<known>`, new `/research_index` route if added, `/evolution_gui_parity?run_id=&gen_no=-1`, and process tab iframe. Capture timings before/after for index endpoints and first render.

## Performance plan
- Backend: metadata-only index response, detail endpoints for large markdown/candidate payloads, optional in-memory cache invalidated by source file mtimes, no persistent cache writes.
- Frontend: debounce search input, `useMemo` filtered rows, abort stale fetches, lazy detail load, cap initial visible rows, avoid repeated wiki and records fetches when the shared index is already loaded.
- Measurement: record response size, endpoint latency for repeated TestClient or curl smoke, and Track Z harness render result. Revert any optimization that changes payload contracts or hides fresh files.

## Rollback rules
- Revert the feature branch commit or PR only; never reset dirty `wt-dev`.
- If the governed index breaks discovery, keep legacy `/research_records` and `/research_docs` routes active and hide only the new lookup entry.
- If process extraction breaks bundle or tests, revert the extraction and keep the existing `ProcessFlowPanel` behavior.
- If HoF labels cause confusion, revert labels only; never merge HoF components as rollback.
- After rollback, rerun the same focused tests and webui gates that covered the reverted slice.

## Handoff guidance
- Use an executor for implementation slices after approval: backend index, frontend lookup, process-flow extraction, and focused tests can be separate bounded tasks.
- Use architect review if adding a new route family or changing route contracts.
- Use critic review before execution if scope expands beyond Option A.
- Use team only if multiple approved branches need concurrent dashboard and research work.
- Use ultragoal only for a durable multi-branch ledger, not for this single pending branch.

## Status
Pending approval. No source edits, branch creation, commit, push, PR, test, build, lint, format, or execution delegation is authorized by this plan.
