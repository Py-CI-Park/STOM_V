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

## Commit Language Rules

- All git commit titles must be written in Korean.
- All git commit bodies must be written in Korean markdown.
- Prefer descriptive intent titles over prefix-only titles such as `docs:` or `fix:`.

## Release And Worktree Mapping

## Current Promoted State

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/     -> STOM_Version_2U_C
└── STOM_V.wt-lab/     -> research/init
```

`STOM_V.wt-dev/` is the sole active checkout for `STOM_Version_2U_C`. `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/transition checkout that preserves promotion history and execution logs.

## Upstream Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- Judge upstream freshness against `https://github.com/devstom/STOM.git`.
- Treat `C:/System_Trading/STOM/STOM_devstom` as a reference-only mirror, not the sole freshness authority.

Current live flow:

```text
V2 -> 2U -> 2U_C -> research/init
```

Archive reference:

```text
integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C
```

`STOM_Version_2` remains the release-ingress branch. The canonical active propagation chain is `V2 -> 2U -> 2U_C -> research/init`. Do not bypass V2 ingress, and do not restore the retired live CLI child-lane model.

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

Expect `release sync preflight passed` before claiming the lane is clean. The live flow is `V2 -> 2U -> 2U_C -> research/init`, while `STOM_V.wt-2uc/` remains an archive/transition checkout rather than an active canonical lane.

## Protected Paths

- `backtest/graph/` is protected result data.
- It is not a git-propagated source path.
- Do not treat result files there as release-overlay inputs.

## Operator Rules

- Keep docs, scripts, tests, CLI-only surfaces, and research-only surfaces out of release overlays unless the task explicitly targets them.
- Keep this guide aligned with `docs/WORKTREE_STRATEGY.md` and `docs/UPSTREAM_SYNC_STRATEGY.md`.
