# STOM Project Guidelines

## Formal Update Operating System

Primary operating document:
- `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`

Carry-forward registry:
- `docs/CARRY_FORWARD_REGISTRY.md`

Current cycle status:
- `docs/update_log/2026-04-05_v274_v277_cycle_status.md`

Release preflight:
```bash
python scripts/verify_release_sync.py
```

## Release And Worktree Mapping

The current worktree mapping is:

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> STOM_Version_2U_C
├── STOM_V.wt-dev/     -> STOM_Version_2U_C_CLI_v267
└── STOM_V.wt-lab/     -> research/init
```

Use the directories for their assigned branches only. `STOM_V.wt-dev/` is the CLI lane, and `STOM_V.wt-2uc/` is the dedicated `STOM_Version_2U_C` lane.

## Upstream Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- Judge upstream freshness against `https://github.com/devstom/STOM.git`.
- Treat `C:/System_Trading/STOM/STOM_devstom` as a reference-only mirror, not the sole freshness authority.

The required propagation chain is:

```text
V2 -> 2U -> 2U_C -> CLI_v267 -> research/init
```

That maps to:

1. `STOM_Version_2`
2. `STOM_Version_2U`
3. `STOM_Version_2U_C`
4. `STOM_Version_2U_C_CLI_v267`
5. `research/init`

Do not bypass V2 ingress and do not skip intermediate lanes.

## Upstream Freshness Check

Use this operator sequence before deciding whether the release lane needs an update:

```bash
git fetch https://github.com/devstom/STOM.git master:refs/remotes/devstom_tmp/master
git show refs/remotes/devstom_tmp/master:_update.txt | head -5
python scripts/verify_release_sync.py
```

The `git fetch` command refreshes a temporary remote-tracking ref from the authoritative GitHub upstream. Inspect `_update.txt` from that fetched ref to confirm the newest release marker before starting propagation.

## Release Preflight

Before release propagation, policy verification, or handoff, run:

```bash
python scripts/verify_release_sync.py
```

If you are validating an isolated checkout root, use:

```bash
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-upsync
```

Expect `release sync preflight passed` before claiming the lane is clean. The propagation order remains `V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`.

## Protected Paths

- `backtest/graph/` is protected result data.
- It is not a git-propagated source path.
- Do not treat result files there as release-overlay inputs.

## Operator Rules

- Keep docs, scripts, tests, CLI-only surfaces, and research-only surfaces out of release overlays unless the task explicitly targets them.
- Keep this guide aligned with `docs/WORKTREE_STRATEGY.md` and `docs/UPSTREAM_SYNC_STRATEGY.md`.
