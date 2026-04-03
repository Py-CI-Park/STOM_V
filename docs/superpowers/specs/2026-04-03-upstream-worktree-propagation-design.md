# Upstream Worktree Propagation Design

**Date:** 2026-04-03
**Scope:** `STOM_Version_2` -> `STOM_Version_2U` -> `STOM_Version_2U_C` -> `STOM_Version_2U_C_CLI_v267` -> `research/init`
**Out of Scope:** rewriting release history, flattening downstream branches, treating result data as git-propagated source files

## Goal

Define the operating policy for receiving future official upstream updates into `STOM_Version_2` and propagating them safely across the active worktree chain while preserving already-landed downstream fixes, branch-local contracts, and protected result assets.

This design replaces the assumption that downstream worktrees can be recreated cheaply. The current downstream branches already contain production-relevant fixes for post-sync regressions, so they must be treated as persistent stabilization layers.

## Current State

As of 2026-04-03, the active worktree graph is:

- `C:\System_Trading\STOM\STOM_V` -> `STOM_Version_2`
- `C:\System_Trading\STOM\STOM_V.wt-2u` -> `STOM_Version_2U`
- `C:\System_Trading\STOM\STOM_V.wt-2uc` -> `STOM_Version_2U_C`
- `C:\System_Trading\STOM\STOM_V.wt-dev` -> `STOM_Version_2U_C_CLI_v267`
- `C:\System_Trading\STOM\STOM_V.wt-lab` -> `research/init`

Observed branch state at design time:

- `STOM_Version_2` is clean relative to `origin/STOM_Version_2`
- `STOM_Version_2U` is ahead of origin by 6 commits
- `STOM_Version_2U_C` is ahead of origin by 6 commits
- `STOM_Version_2U_C_CLI_v267` is ahead of origin by 18 commits and has untracked `backtest/graph/`
- `research/init` is ahead of origin by 8 commits

Those downstream-only commits are not disposable churn. They include regression fixes, compatibility fixes, tests, guardrails, and supporting design records for already-encountered runtime failures.

## Constraints

- `STOM_Version_2` remains the only ingress point for official upstream updates.
- Propagation order is fixed: `V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`.
- Every official version must remain a separate propagation unit.
- `git merge`, `git pull upstream master`, or any other history-level synchronization between release and downstream branches is not an acceptable primary strategy.
- Explicit staging remains required. `git add -A` stays forbidden.
- Result data such as `backtest/graph/` must be protected from deletion but must not be treated as git-propagated source content.

## Approaches Considered

### 1. Conservative staged propagation

Receive each official version into `STOM_Version_2`, verify it, then propagate that same version through each downstream branch in sequence while preserving branch-local fixes and protected assets.

**Pros**
- Matches the real branch hierarchy.
- Keeps failures localized to one version and one branch.
- Treats yesterday's downstream fixes as the new baseline instead of fighting them.
- Gives clear stop points before damage spreads further down the chain.

**Cons**
- Slowest operationally.
- Requires explicit preflight and postflight discipline on every stage.

### 2. Downstream realignment and replay

Reconstruct downstream branches from a chosen checkpoint, then replay only selected fixes before resuming new upstream propagation.

**Pros**
- Can produce a cleaner-looking history.

**Cons**
- High risk of dropping already-proven fixes.
- Unsafe with untracked result assets already living in downstream worktrees.
- Expensive to validate because recent fixes were responses to real regressions.

### 3. Automation-first propagation

Immediately formalize the whole chain into scripts or manifests and rely on automated propagation for most updates.

**Pros**
- Better long-term throughput after the rules stabilize.

**Cons**
- Premature while protected paths, branch-local guarantees, and result-asset rules are still being clarified.
- Makes a bad rule fail faster.

## Recommendation

Use **Approach 1: conservative staged propagation**.

The current problem is not raw throughput. The problem is preserving a branch chain that has already accumulated valid fixes while continuing to accept new upstream releases. The safest policy is to accept the current downstream state as a baseline and move one version at a time through a fixed sequence with explicit gates.

## Approved Decisions

### 1. Branch Roles

- `STOM_Version_2`: official release-tracking branch and sole upstream ingress
- `STOM_Version_2U`: first non-release stabilization layer for pyd-to-py and release adaptation
- `STOM_Version_2U_C`: custom integration layer that keeps non-release branch behavior
- `STOM_Version_2U_C_CLI_v267`: CLI-specialized downstream layer with stricter compatibility preservation
- `research/init`: formal final-stage worktree that still participates in official propagation

### 2. Propagation Graph

All future official versions flow only through this chain:

1. `STOM_Version_2`
2. `STOM_Version_2U`
3. `STOM_Version_2U_C`
4. `STOM_Version_2U_C_CLI_v267`
5. `research/init`

No branch may skip its parent stage and pull changes directly from a higher ancestor.

### 3. Baseline Preservation

Existing downstream-only commits are treated as baseline-stabilizing commits, not as disposable local experiments.

Default policy by commit intent:

- `fix`, `test`, and verification `chore` commits are protected by default
- `docs` commits are not behavior-defining, but should be retained because they capture why branch-local fixes exist
- untracked result assets are protected from deletion even though they are outside git history

## Branch Update Model

### 1. STOM_Version_2

`STOM_Version_2` is the only branch allowed to receive new official upstream content directly.

Policy:

- determine official version boundaries from the real upstream repository, not only from the local mirror
- import official release deltas version by version
- review deletion candidates before applying any overlay-like step
- stage only intended release files explicitly
- commit each version separately

`STOM_Version_2` should stay free of downstream repair commits. It is the release-side source for the rest of the chain.

### 2. STOM_Version_2U

`2U` is no longer safe to treat as a mostly-recreatable overlay branch. It already contains stabilization fixes after prior syncs.

Policy:

- receive each version from `STOM_Version_2`
- prefer release intent, but only when it does not break established `2U` constraints
- preserve branch-local fixes for runtime, serial-key exclusion, and non-release behavior
- keep `.pyd` absence and py-surface parity as enforced invariants

Operationally this is still the most upstream-biased downstream branch, but it is no longer a blind overwrite target.

### 3. STOM_Version_2U_C

`2U_C` is a curated custom integration branch.

Policy:

- receive each completed `2U` version as a distinct propagation step
- preserve custom branch behavior first when conflicts compete with upstream intent
- re-apply upstream intent only where it does not break known downstream fixes

### 4. STOM_Version_2U_C_CLI_v267

`CLI_v267` is a protected compatibility branch, not just another descendant.

Policy:

- receive each completed `2U_C` version as a distinct propagation step
- preserve CLI-specific compatibility surfaces, runtime assumptions, and test contracts
- treat local result directories as protected non-git assets during every update

### 5. research/init

`research/init` is part of the official propagation chain.

Policy:

- receive each completed `CLI_v267` version after CLI verification passes
- preserve research-side fixes and branch-local adaptations
- do not treat it as a disposable lab-only branch anymore

## Protected Assets and Paths

Two protection classes must be handled explicitly.

### 1. Protected code surfaces

These include:

- branch-local fixes already landed in downstream branches
- serial-key exclusion paths in non-release branches
- CLI compatibility files and runtime guardrails
- branch-local tests and verification helpers

For these surfaces, downstream-local behavior wins over blind overwrite when conflicts arise.

### 2. Protected non-git assets

These include:

- `backtest/graph/` and similar generated backtest result directories

Policy:

- they are formally protected and must be considered during every official update
- they are not part of git propagation
- they must never be deleted or implicitly cleaned by sync procedures
- they require preflight existence checks and postflight preservation checks

## Verification Design

Verification runs at every stage before propagation continues.

### Universal gates

Before and after each version step:

- confirm the worktree is on the expected branch
- confirm there are no tracked edits unrelated to the current step
- confirm protected paths were not deleted or overwritten unintentionally
- confirm the branch remains in a reviewable state for that exact version

### V2 verification

`STOM_Version_2` does not currently carry `scripts/verify_nonrelease_sync.py`, so release verification must use release-appropriate checks only.

At minimum:

- confirm imported version boundaries match upstream `_update.txt`
- confirm explicit staging excludes docs, scripts, and branch-local worktree assets
- review the final staged diff before commit

### Downstream verification

`STOM_Version_2U`, `STOM_Version_2U_C`, `STOM_Version_2U_C_CLI_v267`, and `research/init` already contain `scripts/verify_nonrelease_sync.py`.

At minimum:

- run `python scripts/verify_nonrelease_sync.py`
- run branch-relevant tests for changed surfaces
- confirm protected branch-local fixes did not regress during conflict resolution

Additional stage-specific checks:

- `CLI_v267`: verify protected CLI files and preserve `backtest/graph/`
- `research/init`: verify research-side fixes remain intact after propagation from `CLI_v267`

## Failure Handling

- If one stage fails verification, stop the propagation for that version immediately.
- Do not continue into a lower worktree and hope to absorb the problem there.
- Fix the issue at the failing stage, re-run verification, then continue.
- Do not delete or clean result data to simplify the sync.
- Do not reinterpret yesterday's downstream fixes as optional unless there is an explicit decision to replace them with a better fix.

## Documentation Drift To Correct

Current docs do not fully match the real operating state.

Required doc updates:

- `docs/WORKTREE_STRATEGY.md` must reflect the actual worktree layout, especially `wt-2uc`, `wt-dev`, and the fact that `research/init` is now in the formal propagation chain
- `docs/UPSTREAM_SYNC_STRATEGY.md` must be updated from a release-centric sync note into a full-chain policy
- downstream policy must explicitly distinguish protected code surfaces from protected non-git assets
- release-side guidance must stop implying that the local `STOM_devstom` mirror alone is authoritative for upstream freshness

## Success Criteria

- future official versions enter only through `STOM_Version_2`
- each version propagates through the full chain in order
- downstream stabilization commits remain preserved
- protected result assets survive every update
- verification failures stop propagation before downstream contamination
- the written operating policy matches the actual worktree topology

## Explicit Non-Goals

- replacing the chain with a single merged branch
- auto-cleaning downstream result assets
- reclassifying downstream fixes as disposable by default
- treating `research/init` as outside the official update flow
- using `git add -A`, `git merge`, or blind downstream overlays as the default operating model
