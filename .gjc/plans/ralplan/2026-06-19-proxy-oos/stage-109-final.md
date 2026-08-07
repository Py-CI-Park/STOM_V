# Pending Approval Plan — Evolution Dashboard Condition Discovery System Improvements, UI-Aware Sequence

Status: **PENDING APPROVAL — planning only.** This plan does not authorize implementation, tests, source edits, OOS runs, exports, live trading, V3K/KHOPENAPI work, Transformer/ML work, frontend edits, or operating DB changes.

This updates the prior evolution-dashboard condition-discovery plan with explicit sequencing around the active UI worktree `C:/System_Trading/STOM/STOM_V.wt-dashboard-next`.

## Consensus Receipts

| Stage | Artifact | Verdict |
|---|---|---|
| Original final | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-106-final.md` | pending approval |
| UI split planner | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-107-planner.md` | backend-first split |
| UI split architect | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-107-architect.md` | COMMENT / fixes required |
| UI split critic | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-107-critic.md` | ITERATE |
| UI split revision | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-108-revision.md` | blockers resolved |
| UI split architect final | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-108-architect.md` | APPROVE / CLEAR |
| UI split critic final | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-108-critic.md` | OKAY |

## Decision

Proceed, after explicit execution approval only, with the existing **Option B-narrow staged backend plan**, but enforce a **UI-aware execution sequence**:

1. Phase A merge-readiness gate runs first.
2. Only after Phase A passes, backend-safe phases B-D may proceed.
3. UI/frontend/dashboard route/page/bundle work waits until `STOM_V.wt-dashboard-next` is integrated and route-collision review clears any exact dashboard app changes.

## Scope Preserved from Prior Plan

| Area | Decision |
|---|---|
| Presets | Split `fast`, `research`, and `promotion`. |
| Tick research/promotion | Default 09:00-09:28. |
| Min research/promotion | Full session through verified 15:18/15:19 boundary. |
| Scores | `performance_score_100` and `condition_quality_score_100` are advisory only. |
| Evidence | CSV/trade/equity/prompt/validation evidence blockers prevent promotion regardless of score. |
| Prompt quality | Improve buy/sell standard form, anti-copy guidance, forbidden variable handling, bounded exits. |
| Human DB | Use as composition grammar/pattern cards only; no threshold/full-expression/performance copying. |
| Autopsy | Add structured, non-authoritative hypotheses. |
| Transformer/ML | Deferred to future research. |
| Live/export/operating DB/V3K/KHOPENAPI | Out of scope. |

## Hard UI-Aware Constraints

| Constraint | Requirement |
|---|---|
| `dashboard/app.py` pre-UI | Frozen. No new routes, route aliases, static mounts, app wiring, route behavior, or dashboard app-side payload routes before UI integration. |
| Pre-UI backend exposure | New fields may surface only through existing `/status` via `LoopState.page_data["condition_discovery"]`. |
| Route exceptions | Any `dashboard/app.py` change requires a separate route-collision review approving the exact change. |
| Frontend | No JSX/HTML/CSS/static bundle/webui-build work before UI integration. |
| Defaults | Raw backend defaults remain compatible; preset behavior is explicit opt-in. |
| New fields | Optional/null-safe until UI catches up. |
| Runtime artifacts | Do not propagate `.gjc/`, `_database/`, `ai_strategy_loop/state/`, caches, test output, screenshots, or generated bundles unless separately approved. |

## Phase A — Mandatory Merge-Readiness Gate

Phase A must run **first after execution approval**. If Phase A fails, phases B-D do not start.

### Phase A Acceptance

| Check | Required result |
|---|---|
| Shared-file inventory | Produce conflict inventory for UI worktree overlap. |
| Owner decision | Record owner/merge-order decision per shared file. |
| Runtime exclusion | Explicitly exclude `.gjc/`, `_database/`, `ai_strategy_loop/state/`, caches, test output, screenshots, and generated bundles. |
| `dashboard/app.py` freeze | Confirm no pre-UI app route/static/app wiring changes. |
| `controller/telemetry.py` | If absent in this worktree, record absent/not-applicable; do not invent or overlay it. |
| Stop/go | If any check fails, stop before backend phases. |

Minimum files to inventory:

- `ai_strategy_loop/controller/contract.py`
- `ai_strategy_loop/controller/state.py`
- `ai_strategy_loop/controller/loop.py`
- `ai_strategy_loop/controller/ga.py`
- `ai_strategy_loop/controller/telemetry.py` if present in the UI worktree
- `ai_strategy_loop/config.py`
- `ai_strategy_loop/launch_config.py`
- `ai_strategy_loop/dashboard/app.py`
- `ai_strategy_loop/dashboard/backtest_jobs.py`
- dashboard tests touching these contracts

Ownership rule:

| Surface | Owner until UI integration |
|---|---|
| Frontend/routes/layout/static assets/bundles | UI worktree |
| Preset/evidence/scoring/prompt semantics | Backend plan |
| Shared backend files | Manual reconciliation only; no overlay copy |

## Phase B — Pre-UI-Safe Backend Base

May start only after Phase A passes.

| Work | Acceptance |
|---|---|
| Preset resolver | `fast`, `research`, `promotion` explicit resolver; raw `LoopConfig()` and existing form defaults compatible. |
| Tick policy | Research/promotion tick resolves to 09:00-09:28. |
| Min policy | Research/promotion min requires verified full-session 15:18/15:19 boundary. |
| Bridge payload | Add nullable/default-safe backend evidence/session fields under `LoopState.page_data["condition_discovery"]` only. |
| `/status` compatibility | Existing UI continues to tolerate absent/null fields. |

## Phase C — Advisory Scores and Evidence Blockers

| Work | Acceptance |
|---|---|
| Performance score | `performance_score_100` serializes as advisory only. |
| Quality score | `condition_quality_score_100` serializes as advisory only. |
| Hard gates | Existing hard gates remain authoritative. |
| Evidence blockers | Missing CSV/equity/prompt/validation marks promotion-ineligible regardless of score. |
| Authority tests | Scores never set winner, promotion, export, or final approval fields. |

## Phase D — Prompt, Pattern-Card, Autopsy Backend

| Work | Acceptance |
|---|---|
| Prompt guidance | Buy/sell standard forms, forbidden-variable handling, always-true rejection, and bounded exits. |
| Pattern cards | Schema/hash/source required; threshold stripping; no copied full expressions; no performance truth import. |
| Autopsy hypotheses | Advisory prompt feedback only; no gate/evidence override. |
| Persistence | Optional/null-safe bridge payloads compatible with old runs and current UI. |

## Deferred Until UI Worktree Integration

| Deferred item | Reason |
|---|---|
| `dashboard/app.py` route/static/app behavior | UI worktree already changes route/static surface. |
| Dashboard JSX/HTML/CSS/layout | Active UI worktree owns this surface. |
| `frontend/bundle/*` and `webui-build/*` | Generated/build assets collide easily. |
| DOM/page tests and bundle regeneration | Must follow integrated UI contract. |
| UI display for scores/evidence/pattern cards/presets/hypotheses | Requires stable backend contract and merged UI worktree. |

## Verification Plan After Approval

| Phase | Verification |
|---|---|
| A | Artifact review of conflict inventory, owner decisions, runtime exclusions, and `dashboard/app.py` freeze. |
| B | Preset resolver tests, old-run null compatibility, `/status` payload compatibility. |
| C | Score authority tests and evidence blocker tests. |
| D | Prompt/pattern negative cases and hypothesis non-authority tests. |
| UI later | Frontend/build/dashboard route tests only after UI integration. |

## Risks and Controls

| Risk | Control |
|---|---|
| UI/backend merge conflict | Phase A hard gate and app freeze. |
| Hidden route change | Existing `/status` + `LoopState.page_data["condition_discovery"]` only before UI. |
| Runtime contamination | Explicit runtime/protected artifact exclusion. |
| Default drift | Explicit preset resolver; raw defaults stay compatible. |
| Score/promotion confusion | Scores advisory only; hard gates and evidence block promotion. |
| Human DB copying | Pattern-card hashes, threshold stripping, and anti-copy negative tests. |

## ADR

- **Decision:** Keep the original backend-first plan, but add Phase A as the mandatory first gate and defer all UI/frontend/app-route work until the UI worktree lands.
- **Drivers:** Avoid conflicts with active dashboard UI work, preserve backend progress, keep promotion safety explicit.
- **Alternatives considered:**
  - Wait for UI before all work: safest but blocks backend-safe progress.
  - Overlay UI worktree now: rejected due `.gjc`, `_database`, state, bundle, and shared backend risks.
  - Add frontend placeholders now: rejected because it duplicates active UI worktree changes.
- **Consequences:** Approved execution must start with Phase A. B-D can proceed only after Phase A passes. UI wiring remains a separate later step.
- **Follow-ups:** After UI worktree integration, create or approve a separate UI wiring plan for display tables, tabs, bundle, and dashboard page tests.

## Pending Approval

This plan is complete for consensus planning and remains **pending approval**. Recommended execution handoff after explicit approval:

```text
/skill:ultragoal .gjc/plans/ralplan/2026-06-19-proxy-oos/pending-approval.md
```

Execution instruction should explicitly say: run Phase A first, then backend phases B-D only if Phase A passes; no frontend/bundle/dashboard app route work before UI integration.
