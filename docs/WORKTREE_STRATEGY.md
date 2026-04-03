# STOM Worktree Strategy

- Updated: 2026-04-03
- Scope: active STOM release and downstream worktrees

## Actual Worktree Layout

The current local layout is:

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> STOM_Version_2U_C
├── STOM_V.wt-dev/     -> STOM_Version_2U_C_CLI_v267
└── STOM_V.wt-lab/     -> research/init
```

`research/init` is the baseline research branch. New research branches start from that lane, but the protected propagation path still ends at `research/init`.

## Propagation Order

The approved propagation order is:

```text
V2 -> 2U -> 2U_C -> CLI_v267 -> research/init
```

Expanded by branch and directory:

1. `STOM_Version_2` in `STOM_V/`
2. `STOM_Version_2U` in `STOM_V.wt-2u/`
3. `STOM_Version_2U_C` in `STOM_V.wt-2uc/`
4. `STOM_Version_2U_C_CLI_v267` in `STOM_V.wt-dev/`
5. `research/init` in `STOM_V.wt-lab/`

Do not skip lanes, and do not treat `STOM_V.wt-dev/` as a substitute for the `2U_C` worktree. `wt-dev` is the CLI lane, not the home for `STOM_Version_2U_C`.

## Role Of Each Worktree

- `STOM_V/`: official ingress lane only. Release updates enter here first.
- `STOM_V.wt-2u/`: translate approved V2 updates into the maintained py-source lane.
- `STOM_V.wt-2uc/`: integrate 2U into the custom-corrected branch before CLI work.
- `STOM_V.wt-dev/`: maintain `STOM_Version_2U_C_CLI_v267` and feature work on top of it.
- `STOM_V.wt-lab/`: research lane fed after CLI propagation. Experimental output does not flow upstream automatically.

## Protection Rules

- Official updates enter only through `STOM_Version_2`.
- `backtest/graph/` is a protected result-data path, not a git-propagated source path.
- Docs, scripts, tests, CLI-only surfaces, and research-only surfaces stay out of release overlays unless a task explicitly targets them.

Before release work or propagation verification, run:

```bash
python scripts/verify_release_sync.py
```
