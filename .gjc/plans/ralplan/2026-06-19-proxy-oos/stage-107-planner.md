# UI-worktree-aware refinement: evolution-dashboard condition discovery plan

Status: **PENDING APPROVAL — planning only.** This refines `.gjc/plans/ralplan/2026-06-19-proxy-oos/pending-approval.md`; it does **not** authorize implementation, tests/builds/formatters, live/export/operating DB, V3K/KHOPENAPI, Transformer/ML, or frontend edits.

## Evidence inspected
- Pending ralplan: backend-first phases for presets, staged gates, advisory 100-point scores, evidence health, prompt/equity persistence, pattern cards, autopsy feedback, and dashboard contract handoff.
- Active dev worktree rules: `ai_strategy_loop/` owns loop/dashboard backend; generated `state/` and DBs are protected; frontend framework/dependency changes require explicit request.
- UI worktree `C:/System_Trading/STOM/STOM_V.wt-dashboard-next` contains active dashboard/backend/frontend work: `controller/contract.py`, `state.py`, `dashboard/app.py`, `backtest_jobs.py`, extensive `dashboard/frontend/*`, `webui-build/*`, `tests/unit/dashboard/*`, and new `controller/telemetry.py`.
- UI worktree has a new `.gjc/` runtime tree and protected `_database/` zero-byte/runtime DB files; these must not be propagated.

## Principles
1. **Backend-first, UI-safe:** implement engine/state/prompt/scoring seams before touching dashboard pages.
2. **No raw default drift:** raw `LoopConfig()` and `config_field_specs()` defaults remain compatible; `fast/research/promotion` behavior is only through an explicit preset resolver.
3. **Additive contracts only until UI lands:** new API/state fields are optional, nullable, defaulted, and ignored safely by existing UI.
4. **Scores are advisory:** `performance_score_100` and `condition_quality_score_100` never set winner/promotion/pass fields.
5. **Evidence blocks promotion:** missing CSV/equity/prompt/validation evidence overrides good scores.
6. **Frontend waits:** JSX/HTML/CSS/bundle/dashboard page and `webui-build` changes are deferred until the UI worktree is integrated.

## Decision drivers
- The pending plan needs execution sequencing that avoids conflicts with the in-progress UI worktree.
- Current UI worktree already changes dashboard routes, SPA/static assets, telemetry, config form fields, and dashboard tests.
- Backend schema can move safely if all new fields are null-safe and old snapshots/runs still parse.
- Human approval/export boundaries must remain untouched.

## Alternatives
- **A. Wait for UI worktree before all work:** safest merge-wise, but blocks independent engine/prompt/scoring progress unnecessarily.
- **B. Backend-only now, UI later:** chosen. It preserves momentum while avoiding frontend collisions.
- **C. Rebase/overlay UI worktree first:** rejected until merge-readiness checks prove no `.gjc/`, `_database/`, bundle, or backend-contract surprises leak.
- **D. Implement frontend placeholders now:** rejected; duplicates active UI worktree changes and risks stale bundle/page conflicts.

## 1) Pre-UI-safe backend/engine work
Can proceed after explicit execution approval, before UI worktree lands:

- `ai_strategy_loop/config.py`, `launch_config.py`
  - Add explicit preset resolver: `fast`, `research`, `promotion`.
  - Preserve raw constructor defaults and existing form defaults; no hidden default switch to tick/promotion.
  - Research/promotion preset: tick `09:00-09:28`; min preset policy requires full session through verified `15:18/15:19` boundary.
- `ai_strategy_loop/fitness/score.py` or narrow helper
  - Add advisory 100-point score calculators and reason lists.
  - Keep hard gates authoritative and unchanged unless separately approved.
- `ai_strategy_loop/controller/state.py`, `controller/loop.py`
  - Persist optional evidence status, blockers, candidate status, resolved preset/session policy, prompt/equity references.
  - Old DB rows/current_state snapshots must deserialize with `None`, `{}`, or `[]` defaults.
- `ai_strategy_loop/brain/prompt.py`, `brain/generator.py`, prompt rule docs
  - Improve buy/sell prompts, anti-copy guidance, forbidden variable handling, exit-structure guidance.
- Human composition pattern-card backend helpers
  - Threshold stripping, normalized hashes, copy guards, schema validation; no frontend card gallery yet.
- Autopsy hypothesis feedback backend
  - Structured accepted/rejected/deferred hypotheses as advisory prompt feedback; no gate override.
- Focused tests may be planned for execution approval, but none are run during planning.

## 2) Deferred until UI worktree is integrated
Must wait:

- All `ai_strategy_loop/dashboard/frontend/*.jsx`, `*.html`, `styles.css`, `frontend/bundle/*`, and `dashboard/webui-build/*` edits.
- Dashboard page/layout wiring for score cards, evidence panels, pattern cards, autopsy hypothesis panels, preset pickers, and bundle regeneration.
- Route/page behavior that overlaps existing UI worktree SPA changes (`/ui/evolution/*`, tabs, telemetry panels, config forms).
- Any dashboard test updates that assert DOM/bundle/page text rather than backend payload contracts.

## 3) Bridge/contract work: design now, wire UI later
Design as additive backend contract only:

- Prefer `LoopState.page_data["condition_discovery"]` or similarly namespaced optional payload for experimental dashboard fields; do not break `GenerationInfo` consumers unless fields are additive defaults.
- Suggested nullable/defaulted fields:
  - `resolved_preset: null|string`
  - `session_policy: {timeframe,start_time,end_time,full_session_required,source}`
  - `performance_score_100: null|number`, `condition_quality_score_100: null|number`
  - `score_reasons: []`
  - `evidence_status: null|"complete"|"warning"|"evidence_blocker"`
  - `evidence_components: {csv,prompt,equity,validation}` with missing keys tolerated
  - `promotion_ineligible_reasons: []`
  - `candidate_status: null|"research_only"|"not_promotable"|"frozen_pending_review"`
  - `pattern_cards: []`, `hypotheses: []`
- `dashboard/app.py` may expose read-only payloads after backend fields exist, but page rendering waits.
- Contract tests should cover old-run null compatibility and unknown-field tolerance before UI wiring.

## 4) UI worktree merge-readiness checks before execution starts
Before backend execution or integration, review the UI worktree with no mutation:

- Confirm tracked/untracked boundary: **exclude `.gjc/`, `ai_strategy_loop/state/`, `_database/`, caches, test output, bundles unless intentionally produced by UI build approval**.
- Inventory conflicts in backend files already changed there: `controller/contract.py`, `controller/state.py`, `controller/ga.py`, `controller/loop.py`, `dashboard/app.py`, `dashboard/backtest_jobs.py`, `launch_config.py`, `config.py`, `controller/telemetry.py`.
- Verify telemetry contract remains closed/bounded and does not become a source for promotion/evidence decisions.
- Decide merge order per file:
  - UI worktree owns frontend/routes/layout/static assets.
  - Backend plan owns preset/evidence/scoring/prompt semantics.
  - Shared files require manual reconciliation, not overlay copy.
- Ensure UI worktree does not change export/live/operating DB/V3K/KHOPENAPI behavior.

## Phased acceptance criteria

### Phase A — Merge-readiness gate
- `.gjc/` from UI worktree is not copied or committed.
- Runtime/protected DB files are not propagated.
- Shared backend conflicts are listed before implementation.
- Execution remains pending approval.

### Phase B — Backend preset/evidence base
- Raw `LoopConfig()` defaults remain compatible.
- Explicit presets resolve deterministically.
- Tick research/promotion = `09:00-09:28`; min research/promotion = verified full session.
- New fields are optional/null-safe for old runs and current UI.

### Phase C — Scores and blockers
- Advisory scores serialize without changing hard gates.
- Missing CSV/equity/prompt/validation blocks promotion metadata even with high scores.
- `promotion_gate_passed` or winner fields cannot be set by scores alone.

### Phase D — Prompt/pattern/autopsy backend
- Prompt changes reject copy/leakage/always-true cases.
- Pattern cards require schema/hash/source and reject copied thresholds/full expressions.
- Hypotheses are advisory feedback only.

### Phase E — UI wiring after UI worktree lands
- Frontend displays optional fields gracefully when absent.
- Bundle/page tests update only after backend contract is stable.
- Existing telemetry/config dashboard behavior remains intact.

## Verification plan for approved execution
Do not run during planning. After approval, use focused checks first:

- Preset resolver unit tests: raw defaults, `fast`, `research`, `promotion`, invalid preset, tick/min session policy.
- State/contract tests: old snapshot parsing, null fields, evidence blocker serialization, DB migration idempotence.
- Score authority tests: high scores + missing evidence/hard-gate fail remains not promotable.
- Prompt/pattern tests: forbidden variables, always-true gates, threshold/full-expression copy rejection.
- Dashboard backend tests only after contract changes: `/status`, `/config/spec`, read-only endpoints with absent fields.
- Frontend/build tests only after UI worktree integration.

## Risk controls
- **Merge conflicts:** isolate frontend ownership to UI worktree; backend execution avoids JSX/HTML/CSS/bundle edits.
- **UI breakage from schema drift:** additive optional fields only; use `page_data` for bridge payloads.
- **Default drift:** preset resolver is opt-in; raw defaults remain byte/behavior compatible where feasible.
- **Promotion safety regression:** evidence blockers and hard gates remain authoritative.
- **Runtime contamination:** do not propagate `.gjc/`, `_database/`, `state/`, caches, screenshots, or live/export artifacts.

## Handoff
Recommended next approved execution path: backend executor slice for phases B-D only, with architect review before any UI wiring. UI/frontend work resumes only after `STOM_V.wt-dashboard-next` is merged cleanly and its runtime artifacts are excluded.
