# Revised UI-worktree-aware execution sequence — pending approval

Status: **PENDING APPROVAL — planning only.** No tests/builds/formatters, no source edits, no `.gjc` persistence, no live/export/operating DB/V3K/KHOPENAPI/Transformer work.

## Hard constraints
- **Freeze `ai_strategy_loop/dashboard/app.py` pre-UI integration.** No new routes, app wiring, static mounts, route aliases, route behavior changes, or dashboard app-side payload routes before the UI worktree lands.
- Pre-UI backend fields may surface only through existing `/status`, via `LoopState.page_data["condition_discovery"]`.
- Any `dashboard/app.py` change requires a separate route-collision review approving the exact change.
- Frontend/bundle/dashboard page edits wait: no JSX/HTML/CSS/static bundle/webui-build work before UI integration.
- Raw backend defaults remain compatible; preset behavior is explicit opt-in.
- New fields are optional/null-safe until UI catches up.

## Phase A — mandatory merge-readiness gate
Must run **first after execution approval**. If Phase A fails, Phases B-D do not start.

Acceptance:
- Produce and pass a shared-file conflict inventory for UI worktree overlap, at minimum:
  - `ai_strategy_loop/controller/contract.py`
  - `ai_strategy_loop/controller/state.py`
  - `ai_strategy_loop/controller/loop.py`
  - `ai_strategy_loop/controller/ga.py`
  - `ai_strategy_loop/controller/telemetry.py`
  - `ai_strategy_loop/config.py`
  - `ai_strategy_loop/launch_config.py`
  - `ai_strategy_loop/dashboard/app.py`
  - `ai_strategy_loop/dashboard/backtest_jobs.py`
  - dashboard tests touching these contracts
- Record owner/merge-order decision per shared file:
  - UI worktree owns frontend, routes/layout/static assets, dashboard telemetry display, and bundle outputs.
  - Backend plan owns preset/evidence/scoring/prompt semantics.
  - Shared backend files require manual reconciliation; no overlay copy.
- Explicitly exclude from propagation/commit:
  - `.gjc/`
  - `_database/`
  - `ai_strategy_loop/state/`
  - caches (`__pycache__`, `.pytest_cache`, etc.)
  - test output (`test-results/`, ad hoc output files)
  - screenshots/reference captures unless explicitly approved
  - frontend bundles/generated build artifacts unless explicitly approved by the UI integration plan
- Confirm `dashboard/app.py` remains frozen for B-D unless separate route-collision review approves an exact app change.

## Phase B — pre-UI-safe backend base
After Phase A passes:
- Add explicit preset resolver for `fast`, `research`, `promotion` without changing raw `LoopConfig()` defaults or existing form defaults.
- Research/promotion tick policy: `09:00-09:28`.
- Research/promotion min policy: full session through verified `15:18/15:19` boundary.
- Add nullable/default-safe backend evidence/session fields under `LoopState.page_data["condition_discovery"]` only.

## Phase C — advisory scores and evidence blockers
- Add `performance_score_100` and `condition_quality_score_100` as advisory fields only.
- Hard gates remain authoritative.
- Missing CSV/equity/prompt/validation evidence sets promotion-ineligible state regardless of score.
- Scores never set winner, promotion, export, or final approval fields.

## Phase D — prompt, pattern-card, autopsy backend
- Improve prompt guidance and validation for buy/sell structure, forbidden variables, always-true gates, and bounded exits.
- Add human-condition pattern-card backend schema/copy guards: threshold stripping, normalized hashes, no performance-truth import.
- Add autopsy hypothesis feedback as advisory prompt context only.
- Persist all new data as optional/null-safe bridge payloads compatible with old runs and current UI.

## Deferred until UI worktree integration
- Any `dashboard/app.py` route/app/static behavior unless exact change passes route-collision review.
- Dashboard JSX/HTML/CSS/page layout/bundle/webui-build edits.
- DOM/page tests and bundle regeneration.
- UI display of scores, evidence health, pattern cards, presets, and hypotheses.

## Verification after approval
- Phase A artifact review is the first verification gate.
- B-D focused tests only after Phase A passes: preset resolver, old-run null compatibility, `/status` payload compatibility, score authority, evidence blockers, prompt/pattern negative cases.
- Frontend/build tests wait for UI integration.

## Handoff
Execution handoff order: **Phase A gate first**. Only after Phase A passes, delegate backend executor slices for **B-D**. UI/frontend wiring starts only after the separate UI worktree is integrated and route-collision review clears any exact `dashboard/app.py` changes.
