# STOM Worktree Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-30
- Scope: active STOM release and downstream worktrees

## Current Active State

```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
```

- `STOM_V.wt-dev/` is the sole active checkout location for `STOM_Version_2U_C`.
- `STOM_V.wt-2uc/` is retained as an archive/history/transition checkout on `integration/adopt-cli-v267-into-2uc`.
- `research/init` is excluded from the current official propagation chain.
- Do not describe `wt-2uc` as an active canonical lane or restore the retired live CLI child-lane model.

```text
V2 -> 2U -> 2U_C
```

## Role Of Each Worktree

- `STOM_V/`: official ingress lane only. Release updates enter here first.
- `STOM_V.wt-2u/`: translate approved V2 updates into the maintained py-source lane.
- `STOM_V.wt-2uc/`: archive/history/transition lane that preserves promotion evidence and execution logs.
- `STOM_V.wt-dev/`: active single-baseline lane for `STOM_Version_2U_C`.

## Protection Rules

- Official updates enter only through `STOM_Version_2`.
- `backtest/graph/` is a protected result-data path, not a git-propagated source path.
- Docs, scripts, tests, CLI-only surfaces, and research-only surfaces stay out of release overlays unless a task explicitly targets them.
- Before actual V2.78/V2.79 propagation into `2U_C`, use a clean `STOM_Version_2U_C` work location. If `wt-dev` remains on a preparation feature branch, switch/use a clean checkout or create a temporary clean worktree for `STOM_Version_2U_C`.
- Do not check out `STOM_Version_2U_C` in `wt-2uc` while `wt-dev` is the active baseline holder.

Before release work or propagation verification, run:

```bash
python scripts/verify_release_sync.py
```
