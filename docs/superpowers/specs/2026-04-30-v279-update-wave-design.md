# V2.79 Official Update Wave Design

**Date:** 2026-04-30
**Scope:** official V2.78/V2.79 intake and downstream propagation through `V2 -> 2U -> 2U_C`
**Out of Scope:** V3 migration, `research/init`, the retired live CLI child-lane model, and local zip-based official intake

## Context

The previous official cycle closed at `STOM V2.77`. The current resume context is recorded in `docs/update_log/2026-04-30_v279_update_resume_context.md`.

The official GitHub default branch now points at V3 work, so the V2.79 wave must not follow the default branch. The bounded V2 source is GitHub tag `refs/tags/V2.0`, commit `873d51eed3f581daa1925bcd9e3672254f525f0a`. Its `_update.txt` top marker is `2026-04-08 V2.79`.

## Decisions

1. Use `refs/tags/V2.0` as the only official source for V2.78/V2.79.
2. Exclude `refs/heads/V3.00`, `refs/tags/V3.0`, and all V3 `_update.txt` sections.
3. Propagate only through `V2 -> 2U -> 2U_C`.
4. Treat `STOM_V.wt-2uc/` as archive/transition only.
5. Treat `research/init` as preserved remote history, not an active official propagation target.
6. Mark the zip updater workflow as legacy for this wave.
7. Require a clean `STOM_Version_2U_C` work location before downstream propagation into `2U_C`.

## Design

### Operating document alignment

The entry documents must make the current boundary unambiguous:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- `docs/UPSTREAM_SYNC_STRATEGY.md`
- `docs/WORKTREE_STRATEGY.md`
- `docs/stom_v2_update_guide.md`
- `docs/CARRY_FORWARD_REGISTRY.md`

These documents should point operators to the resume context, the V2.0 tag source, the `V2 -> 2U -> 2U_C` chain, and the V3/research exclusions.

### Verification policy

`utility/upstream_sync_policy.py` is the single source for the active release preflight chain. For this wave it must list only:

```python
(
    ("STOM_Version_2", "C:/System_Trading/STOM/STOM_V"),
    ("STOM_Version_2U", "C:/System_Trading/STOM/STOM_V.wt-2u"),
    ("STOM_Version_2U_C", "C:/System_Trading/STOM/STOM_V.wt-dev"),
)
```

`scripts/verify_release_sync.py` should continue to consume that policy rather than duplicating branch names. A preflight failure on `STOM_V.wt-dev` is acceptable before propagation if it reports that the worktree is still on the preparation branch; that failure is the signal to prepare a clean `2U_C` checkout.

### Official intake

After document and policy alignment, the release wave should intake exactly:

```text
STOM V2.78
STOM V2.79
```

Each formal version commit must use:

- title: `STOM V{version}`
- body: the full matching `_update.txt` section from `refs/tags/V2.0`

### Downstream propagation

`2U` owns pyd-to-py translation. `2U_C` owns active downstream runtime compatibility. Branch-local behavior should be preserved unless the official release change directly invalidates it and blocker audit proves a correction is required.

## Success Criteria

- Entry documents no longer instruct the zip workflow as the V2.79 official path.
- Policy tests lock the `V2 -> 2U -> 2U_C` active chain.
- Release preflight excludes `research/init`.
- V2.78/V2.79 intake uses `refs/tags/V2.0`.
- No V3 section enters the V2 wave.
- A clean `2U_C` work location is confirmed before propagation.
