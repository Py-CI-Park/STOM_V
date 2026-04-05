# STOM Worktree Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-05
- Scope: active STOM release and downstream worktrees

## Current Transition State

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/     -> STOM_Version_2U_C_CLI_v267
└── STOM_V.wt-lab/     -> research/init
```

- `STOM_V.wt-2uc/` is the active integration lane.
- `STOM_V.wt-dev/` still reflects the absorbed CLI baseline.
- Do not describe either lane as already repointed to `STOM_Version_2U_C`.

```text
V2 -> 2U -> integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C_CLI_v267 -> research/init
```

## Target Post-Promotion State

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> STOM_Version_2U_C
├── STOM_V.wt-dev/     -> STOM_Version_2U_C
└── STOM_V.wt-lab/     -> research/init
```

After promotion, both `STOM_V.wt-2uc/` and `STOM_V.wt-dev/` should point at `STOM_Version_2U_C`.

```text
V2 -> 2U -> 2U_C -> research/init
```

## Role Of Each Worktree

- `STOM_V/`: official ingress lane only. Release updates enter here first.
- `STOM_V.wt-2u/`: translate approved V2 updates into the maintained py-source lane.
- `STOM_V.wt-2uc/`: integration lane that absorbs the CLI baseline and prepares the single-baseline cutover.
- `STOM_V.wt-dev/`: absorbed CLI lane during transition. It is not yet the post-promotion canonical baseline.
- `STOM_V.wt-lab/`: research lane fed after downstream propagation. Experimental output does not flow upstream automatically.

## Protection Rules

- Official updates enter only through `STOM_Version_2`.
- `backtest/graph/` is a protected result-data path, not a git-propagated source path.
- Docs, scripts, tests, CLI-only surfaces, and research-only surfaces stay out of release overlays unless a task explicitly targets them.
- Only after promotion lands should the docs describe `STOM_V.wt-2uc/` and `STOM_V.wt-dev/` as both on `STOM_Version_2U_C`.

Before release work or propagation verification, run:

```bash
python scripts/verify_release_sync.py
```
