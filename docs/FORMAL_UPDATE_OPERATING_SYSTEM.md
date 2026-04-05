# Formal Update Operating System

## Purpose
This document is the top-level operating model for official STOM version intake and downstream propagation.

## Lifecycle
1. release intake
2. downstream baseline check
3. version-wave propagation
4. blocker audit
5. branch-local corrective fix
6. carry-forward recording
7. cycle closeout

## Canonical flow
`STOM_Version_2` is the only official ingress.

## Current promoted state
Propagation order:
`V2 -> 2U -> 2U_C -> research/init`

`STOM_V.wt-dev/` is the active `STOM_Version_2U_C` checkout. `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/history/transition checkout and is not part of the active canonical propagation chain.

## Documentation map
- Stable strategy: `docs/UPSTREAM_SYNC_STRATEGY.md`
- Worktree map: `docs/WORKTREE_STRATEGY.md`
- Carry-forward registry: `docs/CARRY_FORWARD_REGISTRY.md`
- Current cycle status: `docs/update_log/2026-04-05_v274_v277_cycle_status.md`
- Execution entrypoints: `AGENTS.md`, `CLAUDE.md`

## Entrypoint rule
- `AGENTS.md` = top-level rule summary and routing hub
- central `CLAUDE.md` = official intake guide
- worktree-local `CLAUDE.md` = branch-local execution guide
- entry-point docs must describe the promoted `2U_C` baseline as current and treat `wt-2uc` as archive/history only

## Carry-forward rule
- untouched red gates may be carried forward only when documented
- newly touched red gates require blocker audit before the wave can continue
