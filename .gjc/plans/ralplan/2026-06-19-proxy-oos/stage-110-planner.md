# Ralplan Draft — Evolution Dashboard Condition-Discovery Update Based on Baseline `210bba854d03a8680ffebfb94f2544c52e81858b`

## Summary

Baseline `210bba` already landed the major dashboard route/status/telemetry seams that an older plan would have treated as blocked or frozen. The requested condition-discovery improvements remain valuable, but the plan should shift from “add dashboard foundations” to “extend the existing 210bba backend contracts first, then deliberately surface them in the existing evolution-dashboard UI.” Scores must stay advisory; evidence health, hard gates, and human approval remain authoritative. No live/export/operating DB/V3K/KHOPENAPI/Transformer implementation belongs in this plan.

## 1. Baseline Research Verdict

### Still valid and should be reflected
- Split run presets into `fast`, `research`, and `promotion` with explicit defaults and intent.
- Tick research/promotion default window: `09:00-09:28`.
- Minute research/promotion full-session policy: `09:00` through verified close boundary `15:18/15:19`.
- Staged MDD gates as hard eligibility/risk controls, not score decorations.
- Advisory-only 100-point performance score.
- Advisory-only 100-point condition-generation-quality score.
- Evidence health/blockers for CSV, trade, equity, prompt, validation, and promotion readiness.
- System prompt improvements, including buy/sell standard-form guidance.
- Prompt/equity persistence policy.
- Autopsy hypothesis feedback loop into future generation context.
- Human DB composition library, pattern cards, and few-shot creativity support only.
- Explicit prohibition on copying thresholds, full expressions, or performance claims from human DB examples.
- Transformer/ML remains deferred.
- Live/export/operating DB/V3K/KHOPENAPI remains out of scope.
- Promotion/export require explicit human approval.

### Must be revised because of `210bba`
- Do **not** freeze `dashboard/app.py` absolutely. Baseline already imports telemetry, attaches telemetry to `/status`, and integrates `/ui/evolution` routes/subtabs.
- Do **not** plan route deferral as if the dashboard UI shell is absent. Use the existing evolution route/static behavior and extend it only after backend contract fields are stable.
- Treat telemetry/status/page-data as established extension seams, not as new infrastructure to design from scratch.
- Avoid replacing the existing frontend structure. Extend `dashboard-pages.jsx`, `research-index.jsx`, AI context, research records/index, and webui-build conventions incrementally.

### Already partially covered by `210bba`
- Consumer-safe additive `LoopState.page_data` seam exists.
- `GenerationInfo` already has telemetry fields/contract shape.
- `controller/state.py` already persists prompt/equity paths and emits `to_loop_state(..., page_data=...)`.
- `controller/telemetry.py` already provides closed, bounded, offline dashboard telemetry with source allowlist and protected-origin rejection.
- `/status` already includes telemetry attachment.
- Dashboard tests already validate closed/bounded telemetry and `/status` attachment.

## 2. Recommended Option and Alternatives

### Recommended option: Contract-first additive extension
Add backend contracts/state/persistence for condition-discovery policy, evidence health, advisory scores, preset metadata, prompt/equity/autopsy context, and human-approval promotion state before expanding UI panels. Then surface those fields through the existing 210bba status/page-data/evolution-dashboard seams.

Why this is preferred:
- Aligns with 210bba’s additive consumer-safe design.
- Prevents frontend-only promises with no enforceable backend semantics.
- Keeps hard gates, evidence blockers, and human approvals authoritative over advisory scores.
- Minimizes route/static churn in `dashboard/app.py`.

### Alternative A: UI-first dashboard prototype
Use existing evolution UI to mock panels before backend fields are complete. Faster for visual feedback, but high risk of misleading operators because advisory scores, blockers, and approval state may not match backend truth.

### Alternative B: Backend-only policy phase
Implement all contracts, policy, scoring, and evidence health first, deferring UI. Lowest behavioral risk, but weak operator visibility and poorer acceptance feedback for dashboard ergonomics.

## 3. In Scope / Out of Scope

### In scope
- Backend condition-discovery contracts for presets, windows, evidence health, gates, advisory scores, prompt/equity persistence, autopsy feedback, and human DB creativity references.
- Additive status/page-data payloads using existing 210bba seams.
- Dashboard UI panels/subtabs that read backend truth and clearly separate hard blockers from advisory scores.
- Tests for contract shape, evidence blocking, score advisory behavior, persistence policy, and dashboard rendering/state handling.
- ADR documenting advisory scores, evidence authority, human approval, and non-live/export boundaries.

### Out of scope
- Live trading, export execution, operating DB mutation, V3K integration, KHOPENAPI integration.
- Transformer/ML implementation.
- Promotion/export without explicit human approval.
- Copying human DB thresholds, full formulas, full expressions, or performance claims.
- Broad dashboard route rewrite.
- Merging the current dirty worktree into `210bba`; execution should first establish a clean branch/worktree based on `210bba` or consciously rebase/cherry-pick later work.

## 4. File-Level Change Plan

### Backend contracts and state
- `ai_strategy_loop/controller/contract.py`
  - Add additive condition-discovery policy/status models or fields under existing `GenerationInfo`/page-data-compatible contracts.
  - Represent presets, session windows, staged MDD gates, advisory score summaries, evidence health, and approval state.
- `ai_strategy_loop/controller/state.py`
  - Populate new fields from persisted prompt/equity paths, run metadata, validation state, and autopsy context.
  - Keep missing evidence as explicit blockers rather than silent defaults.
- `ai_strategy_loop/controller/telemetry.py`
  - Preserve closed/bounded/offline telemetry rules.
  - Extend only if new dashboard condition-discovery fields need telemetry-safe summaries.

### Condition-discovery policy/runtime support
- Existing condition-discovery/research loop modules under `ai_strategy_loop/` should receive:
  - `fast/research/promotion` preset definitions.
  - Tick/minute time-window policy.
  - MDD gate evaluation.
  - Advisory performance and generation-quality score calculation.
  - Evidence health aggregation.
  - Prompt/equity persistence and autopsy hypothesis feedback inputs.
  - Human DB composition-library reference mode with anti-copy constraints.

### Dashboard/UI
- `ai_strategy_loop/dashboard/app.py`
  - Keep existing `/status` and `/ui/evolution` behavior.
  - Add only minimal route/status wiring required by backend contracts.
- Frontend evolution dashboard files such as `dashboard-pages.jsx`, `research-index.jsx`, AI context, records/index components, and webui-build support:
  - Add condition-discovery panels for presets, evidence health, hard gates, advisory scores, prompt/equity persistence, autopsy feedback, and approval-required promotion/export state.
  - Clearly label advisory scores and blocked states.

### Tests/docs
- `tests/unit/dashboard/test_dashboard_telemetry.py`
  - Preserve current telemetry guarantees.
  - Add regression coverage that new fields do not violate source allowlist/protected-origin behavior.
- Add focused unit tests for policy defaults, MDD gate staging, advisory scoring, evidence blockers, persistence decisions, autopsy feedback inclusion, and human DB anti-copy behavior.
- Add dashboard/frontend tests for rendering blocked/advisory/approval states where existing test conventions support it.
- Add an ADR under project documentation covering advisory scores, evidence authority, human approval, and non-live/export boundaries.

## 5. Sequencing and Dependencies

### Phase 0 — Execution baseline hygiene
- Start execution from a clean branch/worktree at `210bba854d03a8680ffebfb94f2544c52e81858b` or explicitly reconcile later work before coding.
- Confirm current 210bba dashboard/status telemetry tests still pass before changes.

### Phase 1 — Backend contract and policy definitions
- Define additive condition-discovery contract fields.
- Encode preset defaults:
  - `fast`: quick iteration defaults, not promotion-eligible by itself.
  - `research`: tick default `09:00-09:28`; minute full-session `09:00-15:18/15:19` after boundary verification.
  - `promotion`: same research windows plus stricter evidence/gate/approval requirements.
- Define staged MDD gates as hard gates.
- Define advisory 100-point performance and generation-quality score components.
- Define evidence-health schema and blocker semantics.

### Phase 2 — Persistence and feedback integration
- Wire prompt/equity persistence policy into state/page-data payloads.
- Surface autopsy hypothesis feedback as generation context evidence, with provenance.
- Add human DB library/pattern-card/few-shot reference mode for creativity only.
- Enforce anti-copy checks/metadata for thresholds, full expressions, and performance claims.

### Phase 3 — Status/page-data publication
- Publish condition-discovery state through existing 210bba `LoopState.page_data`, `GenerationInfo`, and `/status` seams.
- Preserve telemetry closed/bounded/offline constraints.
- Ensure missing evidence produces explicit blockers and never optimistic pass states.

### Phase 4 — Dashboard UI extension
- Extend existing evolution-dashboard pages/subtabs after backend payload shape is stable.
- Add panels for presets, evidence health, gates, advisory scores, persistence, autopsy feedback, and approval state.
- Use clear visual hierarchy: hard blockers > human approval > advisory scores.

### Phase 5 — ADR and acceptance hardening
- Record ADR for advisory-only scoring, evidence authority, human approvals, and non-live/export boundaries.
- Add regression tests across backend contracts, policy, persistence, and dashboard rendering.
- Final review should verify no route rewrites, no live/export hooks, and no operating DB assumptions.

## 6. Acceptance Criteria

- Backend exposes additive condition-discovery fields without breaking existing 210bba `/status`, telemetry, or page-data consumers.
- `fast/research/promotion` presets are represented with documented default windows and promotion eligibility semantics.
- Tick research/promotion defaults are `09:00-09:28`.
- Minute research/promotion full-session policy starts at `09:00` and uses verified `15:18/15:19` close boundary handling.
- MDD gates are hard gates and can block promotion regardless of advisory scores.
- Performance and condition-generation-quality scores are 0-100 advisory indicators only.
- Evidence health reports CSV/trade/equity/prompt/validation availability and blockers explicitly.
- Prompt/equity persistence state is visible and auditable.
- Autopsy hypotheses can feed future generation context with provenance.
- Human DB examples are used only for creativity/few-shot/pattern-card guidance and cannot authorize threshold/full-expression/performance copying.
- Dashboard clearly distinguishes blockers, human approval requirements, and advisory scores.
- Promotion/export remains impossible without explicit human approval.
- No live/export/operating DB/V3K/KHOPENAPI/Transformer implementation is introduced.
- ADR exists and matches implemented behavior.

## 7. Verification Matrix

| Area | Verification |
|---|---|
| Baseline preservation | Existing dashboard/status telemetry tests still pass from 210bba baseline before and after changes. |
| Contract compatibility | Unit tests confirm new fields are additive and absent/unknown fields remain consumer-safe. |
| Presets/windows | Unit tests cover `fast`, `research`, `promotion`, tick `09:00-09:28`, and minute `09:00-15:18/15:19` policy. |
| MDD gates | Tests prove staged MDD failures block promotion even when advisory scores are high. |
| Advisory scores | Tests prove scores are bounded 0-100 and never override evidence blockers/human approval. |
| Evidence health | Tests cover missing CSV/trade/equity/prompt/validation evidence as explicit blockers. |
| Persistence | Tests cover prompt/equity path publication and missing/unavailable persistence states. |
| Autopsy feedback | Tests verify hypothesis provenance and safe inclusion in future context. |
| Human DB safety | Tests verify pattern/few-shot use and reject threshold/full-expression/performance copying. |
| Telemetry safety | Tests preserve closed source allowlist, bounded payloads, and protected-origin rejection. |
| Dashboard UI | Frontend/dashboard tests render preset state, blockers, advisory labels, and approval-required promotion/export state. |
| Boundary controls | Static/code review verifies no live/export/operating DB/V3K/KHOPENAPI/Transformer paths were added. |

## 8. Risks and Mitigations

- **Risk: Advisory scores become de facto approval signals.** Mitigate by naming, UI labels, tests, and ADR language that blockers and human approval dominate scores.
- **Risk: UI diverges from backend truth.** Mitigate by backend-first contract sequencing and UI consuming only published status/page-data fields.
- **Risk: Human DB examples leak into copied strategies.** Mitigate with explicit anti-copy constraints, provenance, validation checks, and tests.
- **Risk: Session boundary ambiguity around `15:18/15:19`.** Mitigate by requiring boundary verification and representing uncertainty explicitly until verified.
- **Risk: Telemetry expansion violates 210bba closed/bounded guarantees.** Mitigate by extending through existing telemetry contract tests and rejecting unapproved sources/origins.
- **Risk: Promotion/export accidentally becomes operational.** Mitigate with hard human-approval gate, no export/live implementation, and review checklist.
- **Risk: Dirty current worktree contaminates baseline plan execution.** Mitigate by beginning execution from clean `210bba` baseline or documenting reconciliation before coding.

## 9. ADR Requirement

Create an ADR before final implementation acceptance covering:
- Advisory-only nature of performance and generation-quality scores.
- Evidence health and hard gates as authoritative blockers.
- Human approval as mandatory for promotion/export.
- Human DB use limited to creative inspiration/pattern cards/few-shot context.
- Prohibition on copying thresholds, complete expressions, or performance claims.
- No live/export/operating DB/V3K/KHOPENAPI/Transformer implementation in this phase.
- Use of 210bba dashboard route/status/page-data seams instead of route rewrites.

## 10. Pending-Approval Boundary

This is a planning draft only. Execution requires explicit approval after Ralplan consensus. Until approval, do not edit product source, dashboard bundles, tests, docs, `.gjc` state, operating databases, export paths, live trading integrations, V3K/KHOPENAPI code, or Transformer/ML components.
