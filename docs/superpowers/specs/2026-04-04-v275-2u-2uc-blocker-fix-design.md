# V2.75 2U/2U_C Blocker-Fix Design

**Date:** 2026-04-04
**Scope:** `STOM_Version_2U` and `STOM_Version_2U_C` only, focused on the `V2.75` downstream blocker surfaced on telegram/webcrawling contract checks
**Out of Scope:** `CLI_v267`, `research/init`, `V2.76`, `V2.77`, broad runtime cleanup, or reworking already-created official `STOM V2.75` release commits

## Goal

Define the narrow blocker-audit and corrective strategy required before the downstream wave can continue past `V2.75`.

The immediate goal is not to continue propagation. The immediate goal is to determine whether the newly surfaced `2U` / `2U_C` red gates are:

1. a true downstream propagation break that requires a branch-local corrective commit, or
2. an intentional release-side contract change that should instead update the downstream verification expectation.

## Current State

### Release-side source of truth

`STOM_Version_2` already contains:

- `67bc0652` — `STOM V2.74`
- `03063b4d` — `STOM V2.75`

### Downstream wave state

The `V2.75` wave has already created these commits:

- `2U`: `76cfb876` — `STOM V2.75`
- `2U_C`: `7d6f7d32` — `STOM V2.75`
- `CLI_v267`: `684f4be4` — `STOM V2.75`
- `research/init`: `1e877456` — `STOM V2.75`

### Newly surfaced blocker

After the `V2.75` wave:

- `2U` verifier now fails on:
  - telegram qlist contract mismatch
  - WebCrawling stop contract incomplete
- `2U_C` verifier now fails on:
  - telegram qlist contract mismatch
  - WebCrawling stop contract incomplete

This matters because `V2.75` did touch the relevant surface on the release side:

- `utility/telegram_bot.py`
- `utility/webcrawling.py`
- adjacent release runtime surface (`ui/ui_mainwindow.pyd`)

That means this red gate cannot be safely dismissed as obviously pre-existing.

## Why This Needs A Separate Design

The downstream propagation design already established a blocker-audit rule:

- if a newly touched verification surface turns red during a wave,
- do not automatically classify it as carry-forward,
- first perform a focused audit and decide whether it is a real propagation break.

The `V2.75` telegram/webcrawling failure is the first concrete example of that rule in action.

## Approaches Considered

### 1. Continue to `V2.76` and classify the new red gate as carry-forward

**Pros**
- fastest path to keep the wave moving

**Cons**
- violates the blocker-audit rule
- risks carrying a real propagation break further downstream
- makes later diagnosis harder

### 2. Narrow blocker audit, then minimum corrective action if needed

Audit only the newly touched failure surface in `2U` and `2U_C`, determine whether the verifier or branch state is wrong, then make the smallest branch-local correction needed to restore the intended contract.

**Pros**
- matches the approved downstream design
- contains scope tightly
- preserves the rest of the downstream plan

**Cons**
- adds one more design/plan cycle before `V2.76`

### 3. Roll back the `V2.75` wave in `2U` and `2U_C`

**Pros**
- resets to known-green pre-wave state

**Cons**
- throws away already-created version commits
- complicates the explicit version-boundary history
- unnecessary unless the wave is fundamentally irrecoverable

## Recommendation

Use **Approach 2**.

The problem is narrowly scoped to a verifier/runtime contract boundary on `2U` and `2U_C`. The safest response is a narrow audit plus the smallest corrective path, not a rollback and not an immediate advance to `V2.76`.

## Approved Decisions

### 1. Treat `V2.75` as paused, not rejected

`V2.75` has already been propagated into all four downstream branches. We are not undoing that work yet.

Instead:

- the downstream wave is paused after `V2.75`
- the `2U` / `2U_C` blocker must be classified and resolved first
- only then may `V2.76` begin

### 2. Limit scope to `2U` and `2U_C`

Even though `CLI_v267` and `research/init` have their own red tests, those were already classified as carry-forward branch-local blockers.

This blocker-fix design is only about the **newly touched** `telegram_bot.py` and `webcrawling.py` surface in:

- `2U`
- `2U_C`

### 3. Audit the contract, not the whole app

The audit should answer:

1. What does `verify_nonrelease_sync.py` currently expect?
2. What changed between `V2.74` and `V2.75` on the release side?
3. What code actually exists now in `2U` and `2U_C`?
4. Is the verifier stale, or did the propagated branch state really violate an intended non-release contract?

### 4. If correction is needed, correct upstream-most first

If a branch-local corrective commit is required:

1. fix `2U` first
2. verify `2U`
3. either re-apply or reproduce the same minimum correction in `2U_C`
4. verify `2U_C`

The downstream chain should not continue until both are green or explicitly reclassified.

## Audit Surface

The audit is limited to this neighborhood:

- `utility/telegram_bot.py`
- `utility/webcrawling.py`
- `scripts/verify_nonrelease_sync.py`
- the immediate runtime/contract references those checks rely on, such as:
  - `ui/ui_mainwindow.py`
  - `ui/ui_etc.py`
  - `ui/ui_process_alive.py`
  - `ui/ui_process_kill.py`
  - `utility/static.py`
  - `utility/database_check.py`

## Required Audit Questions

### Question 1: Telegram contract

Determine whether the expected qlist contract in `verify_nonrelease_sync.py` is still the intended non-release contract after `V2.75`, or whether the release change intentionally moved the expected slot usage.

### Question 2: WebCrawling stop contract

Determine whether the release-side `V2.75` edits intentionally weakened or changed the timeout/cancellation contract, or whether `2U` / `2U_C` lost a non-release guard that still must be preserved.

### Question 3: Branch-local invariant

Decide whether this branch family still requires the previous non-release contract even if the release branch changed around it.

That is the core branch-governance question.

## Possible Outcomes

### Outcome A: Verifier stale, no branch correction needed

If the release-side `V2.75` change is intentional and compatible with the downstream branch role:

- update the verifier expectation
- re-run verification
- document the contract change
- continue to `V2.76`

### Outcome B: Branch correction required

If the new release-side behavior breaks a non-release branch invariant:

- add one minimum corrective commit to `2U`
- verify `2U`
- add matching minimum corrective commit to `2U_C`
- verify `2U_C`
- document the reason
- only then continue to `V2.76`

### Outcome C: Unclear / mixed contract

If the surface is too ambiguous to classify safely:

- stop further downstream propagation
- escalate into a narrower deep-dive design for this contract alone

## Verification Design

The blocker-fix phase is complete only if:

- the audit conclusion is explicit
- `2U` passes `python scripts/verify_nonrelease_sync.py`
- `2U_C` passes `python scripts/verify_nonrelease_sync.py`
- the result is documented as either verifier update or branch-local corrective fix

Only then can `V2.76` begin.

## Deliverables

This design should lead to:

1. one blocker-audit note or RCA
2. optionally one `2U` corrective commit
3. optionally one `2U_C` corrective commit
4. a documented conclusion that reopens or halts the downstream wave

## Success Criteria

- the `V2.75` telegram/webcrawling blocker is explicitly classified
- `2U` and `2U_C` are no longer in an ambiguous red state for this surface
- downstream wave policy remains consistent with the blocker-audit rule

## Explicit Non-Goals

- fixing the carry-forward test failures already known on `CLI_v267` or `research/init`
- broad hardening of telegram or webcrawling behavior outside the exact blocker surface
- starting `V2.76` before the blocker is resolved
