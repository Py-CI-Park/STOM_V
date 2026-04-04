# V2.74-V2.77 Downstream Propagation Design

**Date:** 2026-04-04
**Scope:** `STOM_Version_2U` -> `STOM_Version_2U_C` -> `STOM_Version_2U_C_CLI_v267` -> `research/init` for official versions `V2.74` through `V2.77`
**Out of Scope:** changing the already-created release commits on `STOM_Version_2`; deciding whether the stashed `scripts/stom_v2_update.py` improvement should later be merged; unrelated feature work outside the four version waves

## Goal

Design the full downstream propagation strategy for reflecting the already-created official release commits `STOM V2.74` through `STOM V2.77` into all active non-release worktrees while preserving each branch's accumulated stabilization fixes, protected assets, and branch-local operating rules.

This design assumes the release branch is already complete and that downstream work is the next phase. The goal is not merely to mirror files; it is to move the official versions across the chain without erasing the fixes and conventions that each worktree has accumulated after earlier official updates.

## Current State

### Release-side source of truth

`STOM_Version_2` now contains these official release commits:

- `67bc0652` — `STOM V2.74`
- `03063b4d` — `STOM V2.75`
- `0dfce757` — `STOM V2.76`
- `5c69dc82` — `STOM V2.77`

These four commits are the only official source of truth for the downstream phase.

### Downstream worktree heads

- `STOM_Version_2U` head: `ca04b12a`
- `STOM_Version_2U_C` head: `41323a93`
- `STOM_Version_2U_C_CLI_v267` head: `b90b3c2f`
- `research/init` head: `7143ade3`

Observed characteristics:

- `2U` is ahead of origin by 6 commits
- `2U_C` is ahead of origin by 6 commits
- `CLI_v267` is ahead of origin by 18 commits and contains protected non-git output at `backtest/graph/`
- `research/init` is ahead of origin by 8 commits

`research/init` is not an independent side branch for this cycle. It already has `CLI_v267` as its effective canonical base (`merge-base` at `8ed5a889`), so it belongs in the formal downstream wave.

## Design Principle

Downstream branches are no longer disposable mirrors. They are stabilization layers.

That means:

- official release intent must be preserved
- existing downstream fixes must be treated as baseline, not noise
- version boundaries must remain explicit
- audit context should exist before execution so later conflict decisions are evidence-based rather than improvised

## Approaches Considered

### 1. Audit-first + version-wave propagation

First document the downstream baseline centrally and per worktree, then propagate one version across the full chain before moving to the next version.

Wave order:

- `V2.74`: `2U` -> `2U_C` -> `CLI_v267` -> `research/init`
- `V2.75`: `2U` -> `2U_C` -> `CLI_v267` -> `research/init`
- `V2.76`: `2U` -> `2U_C` -> `CLI_v267` -> `research/init`
- `V2.77`: `2U` -> `2U_C` -> `CLI_v267` -> `research/init`

**Pros**
- Preserves version traceability across the whole chain.
- Makes it easier to see exactly where one release wave breaks.
- Gives each branch the same version boundary before the next version begins.

**Cons**
- Requires more up-front documentation.
- Slower than branch-by-branch batching.

### 2. Branch-wave propagation

Finish all four versions for `2U`, then all four for `2U_C`, then `CLI_v267`, then `research/init`.

**Pros**
- Simplifies attention to one branch at a time.

**Cons**
- Leaves lower branches stale for longer.
- Makes cross-version conflict reasoning harder for downstream branches.

### 3. Execute immediately without baseline audit

Start propagating `V2.74` through all four branches with only the current memory of branch-local fixes.

**Pros**
- Fastest start.

**Cons**
- High risk of making preservation decisions without recorded rationale.
- Increases the chance of re-breaking already solved downstream behavior.

## Recommendation

Use **Approach 1: audit-first + version-wave propagation**.

This chain already contains meaningful branch-local evolution. The safest approach is to lock the baseline understanding first, then move one official version through the whole chain at a time.

## Approved Decisions

### 1. Final target is full-chain completion

The target for this downstream cycle is not partial propagation. The intended completed state is:

- `2U` contains `STOM V2.74` through `STOM V2.77`
- `2U_C` contains `STOM V2.74` through `STOM V2.77`
- `CLI_v267` contains `STOM V2.74` through `STOM V2.77`
- `research/init` contains `STOM V2.74` through `STOM V2.77`

### 2. Official intake remains authoritative

The release commits already created on `STOM_Version_2` remain authoritative. Downstream should consume those exact version commits, not re-derive version boundaries independently.

### 3. Branch-local history is a first-class input

Existing downstream fixes are not optional. They should be reviewed, summarized, and treated as protected baseline behavior during propagation.

### 4. Documentation exists at two levels

This cycle should produce:

- one central baseline audit / propagation reference in `STOM_V`
- one local baseline strategy note per downstream worktree

The central document explains the chain. The local documents explain why a given branch is allowed to diverge from a blind mirror.

## Documentation Model

### 1. Central reference document

Purpose:

- chain-wide propagation rulebook
- branch roles and parent relationships
- common protection rules
- summary table of branch-local baseline signals

### 2. Per-worktree local strategy documents

Each downstream worktree should have one branch-local note covering exactly three axes:

1. **정규 업데이트 이후 개발 동향**
   - what changed after the last official sync
   - which fixes or behavioral shifts matter most

2. **보호 대상**
   - which files, behaviors, or invariants must survive the next official wave
   - whether protected assets include non-git outputs

3. **다음 반영 시 우선순위**
   - what should win first during conflicts
   - what verification must pass before moving to the next branch

This structure should be identical across `2U`, `2U_C`, `CLI_v267`, and `research/init`.

## Branch-Specific Propagation Strategy

### 1. STOM_Version_2U

Role:

- first downstream stabilization layer
- closest to the official branch, but not a blind overwrite target

Propagation rule:

- consume the official release version first
- prefer release intent by default
- preserve branch-local non-release invariants when they conflict with blind parity

Protected signals:

- no `.pyd` files
- serial-key exclusion behavior
- earlier non-release runtime fixes already proven necessary

### 2. STOM_Version_2U_C

Role:

- custom integration branch

Propagation rule:

- receive each completed `2U` version as the parent input
- prefer custom branch behavior over blind parity when they conflict
- preserve already-landed custom integration fixes

Protected signals:

- existing custom UI/runtime behavior
- previous non-release verification guardrails
- fixes proving `2U_C` is not a passive mirror

### 3. STOM_Version_2U_C_CLI_v267

Role:

- CLI-focused downstream branch
- strongest branch-local compatibility expectations in the chain

Propagation rule:

- receive each completed `2U_C` version as parent input
- preserve CLI-specific runtime behavior and compatibility surfaces first
- accept official changes only where they do not break CLI contracts

Protected signals:

- CLI compatibility behavior
- branch-local runtime/test assumptions
- `backtest/graph/` as protected non-git output
- previous runtime fixes recorded after official syncs

### 4. research/init

Role:

- formal final stage of the propagation chain
- research-specific branch that still follows the official downstream wave

Propagation rule:

- use `CLI_v267` as the practical canonical parent
- preserve research-specific compatibility/documentation/branch-local structure
- do not treat it as a disposable experiment branch for this cycle

Protected signals:

- research-specific compatibility layers
- minimal branch-local documentation and adaptations
- previously applied fixes that aligned it with the CLI base

## Execution Model

### Phase A: Baseline audit

Before any version propagation:

1. write the central audit document
2. write one local strategy note per downstream worktree
3. confirm each downstream worktree is on the expected branch
4. confirm tracked working-tree cleanliness
5. confirm protected non-git assets are identified before any command can touch them

### Phase B: Version-wave propagation

For each version from `V2.74` through `V2.77`:

1. propagate into `2U`
2. verify `2U`
3. propagate into `2U_C`
4. verify `2U_C`
5. propagate into `CLI_v267`
6. verify `CLI_v267`
7. propagate into `research/init`
8. verify `research/init`

Only after the whole chain is stable for one version may the next version begin.

### Phase C: blocker audit when a newly touched contract surface turns red

If a downstream wave introduces a **new** red gate on a surface that the current version actually touched, do not automatically classify it as a carry-forward failure.

Instead insert a blocker-audit step before the next version begins.

Current known example for this cycle:

- after the `V2.75` wave, `2U` and `2U_C` surfaced a new `utility/telegram_bot.py` qlist contract mismatch
- `V2.75` officially touched `utility/telegram_bot.py`, `utility/webcrawling.py`, and related release-side runtime surfaces

Required blocker-audit question:

- is the new red gate a true propagation break that must be fixed before `V2.76`
- or is it an intentional release-side contract change that should be documented and then carried forward

This audit is narrower than a general branch review. It focuses only on the newly touched failure surface and its immediate call/contract neighborhood.

### Phase D: continue or stop based on blocker-audit result

If the blocker audit concludes the new red gate is a **true propagation break**:

1. stop the downstream wave after the current version
2. design the minimum branch-local corrective step
3. repair the affected branch or branches
4. re-run that version’s verification before continuing

If the blocker audit concludes the new red gate is an **intentional release-side contract change**:

1. record the reasoning in the audit/update log
2. classify it as a carry-forward downstream risk
3. continue to the next version wave

This rule applies only to newly touched surfaces. Pre-existing failures on untouched protected surfaces remain carry-forward blockers unless the current version changes them.

## Verification Design

### Common gate before each branch step

- correct branch checked out
- no unrelated tracked edits
- protected asset status known
- intended version source commit identified exactly

### 2U gate

- `python scripts/verify_nonrelease_sync.py`
- confirm `.pyd` absence remains true
- confirm branch-local non-release invariants still hold

### 2U_C gate

- `python scripts/verify_nonrelease_sync.py`
- conflict resolutions preserve custom branch behavior

### CLI_v267 gate

- `python scripts/verify_nonrelease_sync.py`
- `pytest tests/unit/ -q`
- confirm `backtest/graph/` is untouched as result data
- confirm protected CLI contracts did not regress

### research/init gate

- `python scripts/verify_nonrelease_sync.py`
- branch-local research compatibility still holds
- canonical-parent alignment with `CLI_v267` is preserved where intended

## Carry-Forward Risk Rule

Official upstream feature issues found during release intake should not be silently fixed during this downstream cycle unless they directly break a branch-local protected behavior that must survive propagation.

Default treatment:

- record as carry-forward upstream risk
- allow exact official propagation to continue
- only branch-local breakages justify downstream-local corrective preference

This prevents the downstream wave from turning into an uncontrolled mix of official intake and opportunistic bugfixing.

## Deliverables

This design should lead to:

1. one central downstream baseline audit document
2. four local branch strategy notes
3. one implementation plan covering the full downstream wave
4. completed `STOM V2.74` through `STOM V2.77` propagation on all four downstream branches

## Success Criteria

- every downstream branch receives `STOM V2.74` through `STOM V2.77`
- branch-local stabilization behavior remains preserved
- `CLI_v267` protected outputs and compatibility surfaces survive the wave
- `research/init` ends aligned with the propagated CLI base while retaining research-local intent
- version boundaries stay explicit across the whole chain

## Explicit Non-Goals

- rewriting the just-created release commits
- treating downstream branches as disposable mirrors
- skipping baseline documentation in favor of direct execution
- flattening branch-local fixes into one generic preservation rule without branch-specific reasoning
