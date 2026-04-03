# V2.74-V2.77 Release Sync Design

**Date:** 2026-04-04
**Scope:** `STOM_Version_2` official upstream intake for `V2.74`, `V2.75`, `V2.76`, and `V2.77`
**Out of Scope:** downstream propagation into `2U`, `2U_C`, `CLI_v267`, or `research/init`; deciding whether the local `scripts/stom_v2_update.py` edit should become a permanent tracked improvement

## Goal

Define the release-side execution design for bringing official upstream versions `V2.74` through `V2.77` into `STOM_Version_2` as four separate release commits, without mixing in unrelated local work and without starting downstream propagation in the same cycle.

This design follows the newly merged upstream-worktree policy but keeps the implementation boundary narrow: first make the canonical release worktree safe to use, then create the four official version commits, then hand off clean metadata for the later downstream propagation cycle.

## Current State

As of design time:

- `STOM_Version_2` head is `5779b0a3` (`Merge pull request #7 from Py-CI-Park/feature/upstream-worktree-propagation`)
- local `STOM_Version_2` is synchronized with `origin/STOM_Version_2`
- the release preflight does **not** currently pass because the worktree contains a tracked local modification to `scripts/stom_v2_update.py`
- real upstream (`devstom_tmp/master`) is ahead and `_update.txt` now includes:
  - `2026-03-31 V2.74`
  - `2026-04-01 V2.75`
  - `2026-04-02 V2.76`
  - `2026-04-03 V2.77`

The local `scripts/stom_v2_update.py` change is not part of the official release content. It is a local workflow improvement for environment/path handling and should not be mixed into the `STOM V2.74` through `STOM V2.77` commits.

## Approaches Considered

### 1. Full release-only plan for V2.74-V2.77, then execute sequentially

First isolate the unrelated local script edit, restore a clean canonical release state, then process `V2.74`, `V2.75`, `V2.76`, and `V2.77` as four separate official commits inside one release-only cycle.

**Pros**
- Keeps the actual release work clearly separated from unrelated local tooling edits.
- Preserves the required one-version-one-commit boundary.
- Produces a clean handoff for downstream propagation.

**Cons**
- Requires up-front cleanup before the first version can be applied.

### 2. Plan only `V2.74`, then repeat the same pattern interactively

Design and execute `V2.74` first, then revisit the plan for `V2.75` through `V2.77`.

**Pros**
- Slightly smaller first step.

**Cons**
- Repeats planning overhead.
- Makes it easier to drift from version to version.

### 3. Split cleanup and release sync into separate designs

Write one design only for storing or stashing `scripts/stom_v2_update.py`, then another for the release versions.

**Pros**
- Most conservative separation of concerns.

**Cons**
- Over-splits a tightly connected operator workflow.
- Adds extra document churn without improving the actual execution boundary very much.

## Recommendation

Use **Approach 1**.

The recommended unit of planning is the full release-only batch `V2.74` through `V2.77`, but the recommended unit of execution remains one version at a time. This is the cleanest way to preserve release commit boundaries while still capturing the up-front cleanup and preflight requirement in the same operator design.

## Approved Decisions

### 1. This cycle is release-only

This design covers only `STOM_Version_2`.

It does **not** include:

- `2U`
- `2U_C`
- `CLI_v267`
- `research/init`

Those branches will be handled in a later propagation design after the release-side official commits exist.

### 2. The local `scripts/stom_v2_update.py` edit must be preserved but excluded

The current local change to `scripts/stom_v2_update.py` should not be discarded, but it must not contaminate the official release commits.

For this cycle it is treated as:

- preserved local work
- temporarily removed from the release working tree by a safe mechanism such as `stash`
- explicitly outside the `STOM V2.74` through `STOM V2.77` commits

### 3. Four versions, four commits

This cycle must produce exactly these release commits on `STOM_Version_2`:

- `STOM V2.74`
- `STOM V2.75`
- `STOM V2.76`
- `STOM V2.77`

No combined commit is allowed.

### 4. Commit bodies come from `_update.txt`

Each commit body must use the full corresponding `_update.txt` version section for that release version.

## Execution Model

### Phase 1: Release worktree preparation

Before touching any upstream release content:

1. preserve the local `scripts/stom_v2_update.py` modification safely
2. restore `STOM_Version_2` to a clean tracked state
3. run release preflight on the canonical root:

```powershell
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V
```

Do not begin `V2.74` until the canonical preflight passes.

### Phase 2: Version-by-version official intake

For each of `V2.74`, `V2.75`, `V2.76`, and `V2.77`:

1. identify the upstream boundary for that version from real upstream
2. inspect the release delta for that version
3. apply the official version content to `STOM_Version_2`
4. stage only intended release files explicitly
5. commit with the exact title `STOM V2.xx`
6. use the full `_update.txt` section as the commit body
7. verify the worktree returns to a clean state before moving on

### Phase 3: Release-side handoff

After `V2.77`:

1. record the four new release commit SHAs
2. record any version-specific warning areas discovered during intake
3. prepare the release-side result as input for the downstream propagation design

## Verification Design

### Pre-cycle gate

Before `V2.74` begins:

- `scripts/stom_v2_update.py` local edit is safely preserved and absent from working tree diff
- canonical release preflight passes
- the release branch is on `STOM_Version_2`

### Per-version gate

After each version commit:

- commit subject matches the exact version title
- commit body matches the correct `_update.txt` section
- staged file set was explicit, not broad
- no unintended tracked edits remain

### End-of-cycle gate

After `V2.77`:

- all four version commits exist in order
- the release worktree is clean
- preserved local script work remains recoverable

## Safety Rules

- Do not use `git add -A`
- Do not collapse multiple versions into one commit
- Do not use `git rebase`
- Do not use `git reset --hard`
- Do not let the local `scripts/stom_v2_update.py` edit drift into any official version commit
- Do not start downstream propagation from this design

## Deliverables

This design should lead to:

1. one follow-up implementation plan for `STOM_Version_2` only
2. four official release commits (`V2.74` through `V2.77`)
3. a clean release-side handoff package for the later downstream propagation cycle

## Success Criteria

- `scripts/stom_v2_update.py` local work is preserved but excluded from official release commits
- canonical release preflight passes before official intake begins
- `STOM_Version_2` receives `STOM V2.74`, `STOM V2.75`, `STOM V2.76`, and `STOM V2.77`
- each commit body comes from the matching `_update.txt` section
- the release branch ends clean and ready for downstream planning

## Explicit Non-Goals

- deciding whether the local `scripts/stom_v2_update.py` improvement should later be merged
- propagating `V2.74` through `V2.77` into downstream worktrees
- rewriting or simplifying the new upstream-worktree policy introduced by PR #7
