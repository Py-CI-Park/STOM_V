# V2.68-V2.73 2U Chain Propagation Design

**Date:** 2026-03-31
**Scope:** `STOM_Version_2U` -> `STOM_Version_2U_C` -> `STOM_Version_2U_C_CLI_v267`
**Out of Scope:** `research/init` and other `research/*` branches

## Goal

Reflect the already-merged official `STOM_Version_2` updates `V2.68` through `V2.73` into the non-release worktree chain while preserving each branch's role, constraints, and existing custom behavior. The result should leave all three branches with version-by-version commits named `STOM V2.68` through `STOM V2.73`.

## Context

- `STOM_Version_2U` is a persistent pyd-to-py tracking branch, not a one-time migration branch.
- `STOM_Version_2U_C` is the custom development home branch and receives official changes from `2U`.
- `STOM_Version_2U_C_CLI_v267` is a CLI-specialized non-release branch with stricter custom preservation requirements.
- Branch-specific rules already require:
  - no serial-key reintroduction in any 2U-derived branch
  - no `.pyd` files remaining in non-release branches
  - `ui_mainwindow.py` interface parity with the release branch's `ui_mainwindow.pyd`
  - branch-specific verification with `scripts/verify_nonrelease_sync.py`
  - explicit file staging only

## Approaches Considered

### 1. Full sequential propagation

Apply each version to `2U`, verify and commit, then propagate the resulting version commit to `2U_C`, verify and commit, then propagate again to `CLI_v267`, verify and commit.

**Pros**
- Matches documented branch hierarchy.
- Keeps failures localized to one branch and one version.
- Preserves traceability for every propagated version.

**Cons**
- Slowest approach.

### 2. Parallel branch propagation after a single 2U design pass

Design all branch updates together, then execute parts of `2U_C` and `CLI_v267` in parallel.

**Pros**
- Faster on paper.

**Cons**
- Real conflicts still resolve sequentially.
- Easy to diverge from the actual `2U` result that downstream branches should consume.

### 3. Partial propagation only

Update `2U` now and defer `2U_C` and `CLI_v267`.

**Pros**
- Lowest immediate risk.

**Cons**
- Leaves the official propagation chain half-done.
- Increases future merge complexity.

## Recommendation

Use **Approach 1**.

This work is fundamentally a staged propagation problem, not a broad refactor. The safest design is to move one version at a time and one branch at a time, while preserving version commit boundaries across the entire chain.

## Approved Decisions

### Propagation Order

1. `STOM_Version_2U`
2. `STOM_Version_2U_C`
3. `STOM_Version_2U_C_CLI_v267`

### Conflict Policy

- `2U`: upstream-first, with explicit exceptions
- `2U_C`: custom-preservation-first
- `CLI_v267`: custom-preservation-first, with CLI contracts treated as protected surfaces

### Commit Naming

All three branches keep the same version commit titles:

- `STOM V2.68`
- `STOM V2.69`
- `STOM V2.70`
- `STOM V2.71`
- `STOM V2.72`
- `STOM V2.73`

## Branch-Specific Design

### 1. STOM_Version_2U

`2U` consumes the official release branch as its source of truth. The implementation unit is still each official version, but the update is not a blind overlay.

For each version:

- start from the already-updated `STOM_Version_2`
- identify release-side file changes for that version
- determine whether `ui/ui_mainwindow.pyd` changed meaningfully
- if pyd changed, infer the matching `ui/ui_mainwindow.py` updates from surrounding `ui/*.py` call patterns and newly required interfaces
- remove any `.pyd` file from the branch state before commit
- exclude serial-key behavior even if release-side code changed around it

`2U` is the only branch in this chain where upstream behavior should win by default. Even here, the branch-specific invariants are stronger than blind parity.

### 2. STOM_Version_2U_C

`2U_C` receives each completed `2U` version commit by cherry-pick.

For each version:

- cherry-pick the matching `2U` version commit
- resolve conflicts in favor of existing `2U_C` custom behavior
- re-apply upstream intent only where it does not break established custom behavior
- preserve non-release guardrails from recent `v267`-era fixes

The key design point is that `2U_C` is not a passive mirror. It is a curated integration branch.

### 3. STOM_Version_2U_C_CLI_v267

`CLI_v267` receives each completed `2U_C` version commit by cherry-pick.

For each version:

- cherry-pick the matching `2U_C` version commit
- protect CLI-specific compatibility surfaces
- keep branch-local runtime and testing assumptions intact
- prefer local CLI behavior over official behavior when both compete

Protected surfaces include, at minimum:

- CLI-oriented backtest compatibility changes
- CLI setting aliases and non-release configuration structures
- branch-local import/lazy-loading compatibility
- CLI tests and test fixtures
- non-release runtime/telegram guardrails

## Version Handling Model

Each version is a complete mini-cycle:

1. analyze release delta for that version
2. adapt for the current branch
3. verify for the current branch
4. commit as that version
5. move to the next version

This applies independently for:

- `2U`: `V2.68` through `V2.73`
- `2U_C`: `V2.68` through `V2.73`
- `CLI_v267`: `V2.68` through `V2.73`

No branch should skip directly from `V2.67` to `V2.73`.

## Verification Design

### 2U Verification

- confirm no `.pyd` files remain
- confirm `ui_mainwindow.py` still satisfies the release UI call surface
- run `python scripts/verify_nonrelease_sync.py`
- run syntax-level verification on modified Python files

### 2U_C Verification

- verify cherry-pick conflict resolutions preserve existing custom behavior
- run `python scripts/verify_nonrelease_sync.py`
- run branch-relevant regression checks for modified Python files

### CLI_v267 Verification

- run `pytest tests/unit/ -q`
- run `python scripts/verify_nonrelease_sync.py`
- verify protected CLI files did not regress during cherry-pick resolution

## Error-Handling Rules

- stop on the first version that cannot be verified cleanly
- do not continue propagation to downstream branches until the upstream stage of that version is stable
- if a `2U` inference is uncertain, resolve that uncertainty before propagating to `2U_C`
- if a downstream conflict exposes a branch-specific contract not captured in docs, document it before proceeding

## Deliverables

This design produces one follow-up implementation plan that contains:

- `2U` version-by-version tasks
- `2U_C` version-by-version propagation tasks
- `CLI_v267` version-by-version propagation tasks
- exact verification commands and commit checkpoints

## Success Criteria

- all three branches end with `STOM V2.68` through `STOM V2.73`
- `2U` contains no `.pyd` files
- `2U` keeps serial-key behavior excluded
- `2U_C` retains custom branch behavior after official propagation
- `CLI_v267` passes `pytest tests/unit/ -q`
- non-release verification script passes on every non-release branch

## Explicit Non-Goals

- updating `research/init` in the same implementation cycle
- rewriting branch strategy or hierarchy
- collapsing multiple version updates into one commit
- replacing inference/cherry-pick with blind file overlay in custom branches
