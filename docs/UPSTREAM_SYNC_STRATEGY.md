# Upstream Sync Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-03
- Scope: release ingestion and downstream propagation from the official STOM upstream

## Source Of Truth

Upstream freshness is judged by the official upstream remote:

- Official freshness authority: `https://github.com/devstom/STOM.git`
- Local reference mirror: `C:/System_Trading/STOM/STOM_devstom`

The local mirror is reference-only. It is useful for inspection and fallback access, but it is not the sole freshness authority. When deciding whether the release lane is current, compare against the GitHub upstream first.

## Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- `STOM_V/` is the only release-ingress worktree.
- Downstream branches receive propagated changes only after `STOM_Version_2` is updated and checked.

## Worktree Propagation Chain

The current worktree layout is:

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> STOM_Version_2U_C
├── STOM_V.wt-dev/     -> STOM_Version_2U_C_CLI_v267
└── STOM_V.wt-lab/     -> research/init
```

The required propagation order is:

```text
V2 -> 2U -> 2U_C -> CLI_v267 -> research/init
```

Mapped to current worktrees:

1. `STOM_Version_2` in `C:/System_Trading/STOM/STOM_V`
2. `STOM_Version_2U` in `C:/System_Trading/STOM/STOM_V.wt-2u`
3. `STOM_Version_2U_C` in `C:/System_Trading/STOM/STOM_V.wt-2uc`
4. `STOM_Version_2U_C_CLI_v267` in `C:/System_Trading/STOM/STOM_V.wt-dev`
5. `research/init` in `C:/System_Trading/STOM/STOM_V.wt-lab`

Do not import upstream changes directly into `STOM_V.wt-2uc/`, `STOM_V.wt-dev/`, or research lanes. Every release-originated change must enter through V2 and move one lane at a time.

## Release Overlay Boundaries

Release overlays intentionally exclude branch-only surfaces such as docs, scripts, tests, CLI-only files, and research-only content. They also exclude protected result data.

- Protected result-data path: `backtest/graph/`
- Policy: `backtest/graph/` is not a git-propagated source path

If that directory is present as untracked output, it is allowed as result data. It must not be treated as release input or as evidence that propagation is incomplete.

## Preflight Workflow

Before release propagation, lane verification, or final handoff, run:

```bash
python scripts/verify_release_sync.py
```

To verify from another checkout root, use:

```bash
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-upsync
```

The preflight must pass before claiming the release sync is clean.

## Practical Operator Notes

- Use `STOM_devstom` for convenient local inspection when network access is unavailable or when comparing file history locally.
- Reconfirm against `https://github.com/devstom/STOM.git` before declaring the release lane current.
- Keep `CLAUDE.md` and the worktree strategy doc aligned with the live mapping: `STOM_V.wt-2uc/`, `STOM_V.wt-dev/`, `STOM_Version_2U_C_CLI_v267`, and `research/init`.
