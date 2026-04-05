# STOM Project Guidelines (STOM_Version_2U_C transition lane)

> **Worktree location**: `STOM_V.wt-2uc/`
> **Role**: integration/promotion lane preparing the single-baseline cutover
> **Current state**: `STOM_V.wt-2uc/` -> `integration/adopt-cli-v267-into-2uc`; `STOM_V.wt-dev/` -> `STOM_Version_2U_C_CLI_v267`
> **Target state**: both worktrees -> `STOM_Version_2U_C` after promotion
> **Authoritative local topology doc**: `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/WORKTREE_STRATEGY.md`

## Read First

- `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/WORKTREE_STRATEGY.md`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`

## Branch Gate

- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
- `backtest/graph/` is protected result data.

## Current Transition State

- `STOM_V.wt-2uc/` is the integration lane for `integration/adopt-cli-v267-into-2uc`.
- `STOM_V.wt-dev/` still carries `STOM_Version_2U_C_CLI_v267` until promotion completes.
- Do not describe the single-baseline cutover as already complete.

## Target State

- After promotion, both `STOM_V.wt-2uc/` and `STOM_V.wt-dev/` should point at `STOM_Version_2U_C`.
- The target propagation chain is `V2 -> 2U -> 2U_C -> research/init`.

## Working Rules

- Follow `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/WORKTREE_STRATEGY.md` for the live lane map of this checkout.
- Use `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md` only as upstream release-ingress context; it is not the authoritative live topology for this lane.
- Do not route live coding through a downstream CLI child lane.
- `backtest/graph/` is protected result data and must not be used as a source path.

## When to Use Other Lanes

- Use `research/init` only for formal research, experimentation, or branch-local proof-of-concept work.
- Use `STOM_Version_2` and `STOM_Version_2U` as upstream inputs, not as live editing lanes for the 2U_C baseline.
