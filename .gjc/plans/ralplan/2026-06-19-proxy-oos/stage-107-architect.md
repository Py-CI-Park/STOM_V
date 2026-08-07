## Summary
The plan is directionally safe and mostly satisfies the requested split: backend/prompt/scoring/state work is separated from frontend/bundle/page wiring, raw defaults are explicitly protected, new state is planned as nullable/additive, runtime artifacts are excluded, and live/export/operating DB/V3K/KHOPENAPI/Transformer scope remains out. The main risk is one ambiguous allowance for pre-UI `dashboard/app.py` payload exposure while the UI worktree already owns route/static/router changes; keep that path constrained to existing `/status`/`LoopState.page_data` until the UI worktree is reconciled.

## Findings
- **MEDIUM — Shared `dashboard/app.py` ambiguity.** Plan line 74 allows `dashboard/app.py` to expose read-only payloads after backend fields exist. The UI worktree already has active route/router/static changes (`/ui/evolution/*`, routers, static `/ui` mount, telemetry/config panels), so pre-UI app-route edits can collide even if frontend rendering waits. **Fix:** pre-UI exposure should use existing `LoopState.page_data["condition_discovery"]` through `/status`; new routes or `dashboard/app.py` wiring must wait for UI worktree merge or pass a route-collision review.
- **LOW — Shared backend files require discipline, not overlay.** The plan correctly lists `config.py`, `launch_config.py`, `controller/state.py`, `controller/loop.py`, `contract.py`, `dashboard/app.py`, and `backtest_jobs.py` as conflict inventory before execution. This is acceptable only if Phase A is treated as a hard gate.
- **CLEAR — Raw defaults preserved.** Current `LoopConfig` still defaults `bt_timeframe` to `"min"`, and `config_field_specs()` derives defaults from `LoopConfig()`. The plan’s explicit preset resolver avoids hidden tick/promotion default drift.
- **CLEAR — Null-safe/additive contract.** Existing `LoopState.page_data` is a defaulted pass-through dict, and both current/target contracts support optional additive payloads. The proposed nullable/defaulted fields are compatible with old runs if kept out of hard `GenerationInfo` changes unless defaults are supplied.
- **CLEAR — Runtime and protected artifact exclusion.** The target UI worktree contains `.gjc/`, `_database/`, and `ai_strategy_loop/state/` runtime artifacts; the plan explicitly excludes these and bundles until approved UI integration.
- **CLEAR — Scope boundaries maintained.** The plan repeats no live/export/operating DB/V3K/KHOPENAPI/Transformer work, keeps scores advisory, and preserves evidence/hard-gate authority.

## Strongest antithesis / tradeoff
The safest merge strategy is to wait for `STOM_V.wt-dashboard-next` before touching any shared backend file, eliminating conflict risk. The cost is blocking independent preset/evidence/scoring/prompt work that can safely proceed behind additive state contracts; the chosen backend-first path is reasonable if Phase A conflict inventory is mandatory and `dashboard/app.py` remains effectively frozen pre-UI.

## Architectural Status
WATCH

## Product Status
WATCH — product boundaries are correct; watch the UI/backend merge seam.

## Code Status
COMMENT — no implementation reviewed, but existing seams support the plan with the `dashboard/app.py` tightening above.

## Recommendation
COMMENT

## Required fixes
1. Tighten the plan so pre-UI backend execution does **not** add or modify `dashboard/app.py` routes; use existing `/status` + `LoopState.page_data["condition_discovery"]` only, unless a separate route-collision review approves the exact app change.
2. Treat Phase A as a hard pre-execution gate: enumerate shared-file conflicts and exclude `.gjc/`, `_database/`, `ai_strategy_loop/state/`, caches, test output, and bundles before any backend slice starts.
