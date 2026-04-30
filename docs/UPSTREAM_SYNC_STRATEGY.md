# Upstream Sync Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-30
- Scope: release ingestion and downstream propagation from the official STOM upstream

## Source Of Truth

Upstream freshness is judged by the official upstream remote:

- Official freshness authority: `https://github.com/devstom/STOM.git`
- Local reference mirror: `C:/System_Trading/STOM/STOM_devstom`
- Current V2 wave source: `refs/tags/V2.0`

The local mirror is reference-only. It is useful for inspection and fallback access, but it is not the sole freshness authority. When deciding whether the release lane is current, compare against the GitHub upstream first.

For the V2.79 wave, use the terminal V2 tag:

```text
refs/tags/V2.0 -> 873d51eed3f581daa1925bcd9e3672254f525f0a
```

Do not use `refs/heads/V3.00` or `refs/tags/V3.0` for the V2.79 wave.

## Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- `STOM_V/` is the only release-ingress worktree.
- Downstream branches receive propagated changes only after `STOM_Version_2` is updated and checked.
- Remaining V2 targets for the current wave are exactly `STOM V2.78` and `STOM V2.79`.

## Worktree Propagation Chain

### Current promoted state

```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
```

Current propagation flow:

```text
V2 -> 2U -> 2U_C
```

`STOM_V.wt-dev/` is the active `STOM_Version_2U_C` checkout location. `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/history/transition checkout and is not part of the active canonical flow. `research/init` is not part of the current V2.79 propagation wave. Do not import upstream changes directly into downstream or research lanes. Every release-originated change must enter through V2 and move one lane at a time.

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

The preflight must pass before claiming the release sync is clean. A branch mismatch on `STOM_V.wt-dev/` means a clean `STOM_Version_2U_C` work location still needs to be prepared before propagation.

## Practical Operator Notes

- Use `STOM_devstom` for convenient local inspection when network access is unavailable or when comparing file history locally.
- Reconfirm against `https://github.com/devstom/STOM.git` before declaring the release lane current.
- Keep `CLAUDE.md` and the local worktree strategy docs aligned with the promoted `2U_C` baseline, the archive role of `wt-2uc`, and the exclusion of `research/init`.
