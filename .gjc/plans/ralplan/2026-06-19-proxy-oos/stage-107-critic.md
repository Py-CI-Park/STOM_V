[ITERATE]

**Justification**: The refinement is close and the backend-first shape is sound, but it is not yet actionable as the final pending-approval plan because it does not fully incorporate the architect's required fixes. Existing code supports the safe path: `LoopConfig.bt_timeframe` remains raw `"min"`, `config_field_specs()` derives defaults from `LoopConfig()`, and `LoopState.page_data` is already a defaulted pass-through exposed by existing `/status`. The UI worktree also really owns route/static/frontend territory: its `dashboard/app.py` adds `/ui/evolution/*` and UI aliases, and the worktree contains `.gjc/`, `_database/`, `ai_strategy_loop/state/`, frontend bundles, and dashboard tests that must be excluded.

**Blocking issues / required fixes**:
1. Freeze `ai_strategy_loop/dashboard/app.py` pre-UI. Replace the planner allowance that `dashboard/app.py` may expose read-only payloads with: no new routes, app wiring, static mounts, or route behavior before UI integration; backend fields are exposed only through existing `/status` via `LoopState.page_data["condition_discovery"]`, unless a separate route-collision review approves an exact app change.
2. Make Phase A a hard first gate after execution approval and before any backend slice. It must produce/pass a shared-file conflict inventory, owner/merge-order decision per shared file, and explicit exclusion of `.gjc/`, `_database/`, `ai_strategy_loop/state/`, caches, test output, screenshots, and bundles. If Phase A fails, phases B-D do not start.
3. Update the handoff from “backend executor slice for phases B-D only” to “Phase A gate, then phases B-D only after pass,” with testable acceptance wording for the gate.

**Representative simulation**: preset work is implementable without raw default drift; contract/state work is implementable through nullable `page_data`; route exposure is the unsafe seam because the UI worktree already changes app routes and static UI behavior.

**Final pending-approval plan can be persisted**: No — persist only after the fixes above are folded into the planner artifact. Read-only review only; no tests, builds, formatters, or files were mutated.
