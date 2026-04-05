# STOM Worktree Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-05
- Scope: active STOM release and downstream worktrees

## Current Active State

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/     -> STOM_Version_2U_C
└── STOM_V.wt-lab/     -> research/init
```

- `STOM_V.wt-dev/` is the sole active checkout for `STOM_Version_2U_C`.
- `STOM_V.wt-2uc/` is retained as an archive/history/transition checkout on `integration/adopt-cli-v267-into-2uc`.
- Do not describe `wt-2uc` as an active canonical lane or restore the retired live CLI child-lane model.

```text
V2 -> 2U -> 2U_C -> research/init
```

## Role Of Each Worktree

- `STOM_V/`: official ingress lane only. Release updates enter here first.
- `STOM_V.wt-2u/`: translate approved V2 updates into the maintained py-source lane.
- `STOM_V.wt-2uc/`: archive/history/transition lane that preserves promotion evidence and execution logs.
- `STOM_V.wt-dev/`: active single-baseline lane on `STOM_Version_2U_C`.
- `STOM_V.wt-lab/`: research lane fed after downstream propagation. Experimental output does not flow upstream automatically.

## Protection Rules

- Official updates enter only through `STOM_Version_2`.
- `backtest/graph/` is a protected result-data path, not a git-propagated source path.
- Docs, scripts, tests, CLI-only surfaces, and research-only surfaces stay out of release overlays unless a task explicitly targets them.
- Do not check out `STOM_Version_2U_C` in `wt-2uc` while `wt-dev` is the active baseline holder.

Before release work or propagation verification, run:

```bash
python scripts/verify_release_sync.py
```
