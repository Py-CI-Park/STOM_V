# V2.75 2U_C WebCrawling Legacy Compatibility Design

**Date:** 2026-04-04
**Scope:** `STOM_Version_2U_C` only, focused on the remaining legacy compatibility blocker around `utility/webcrawling.py` after the WebCrawling timeout contract fix
**Out of Scope:** `2U`, `CLI_v267`, `research/init`, resuming `V2.76`, or broad crawler refactoring beyond the minimum compatibility surface

## Goal

Define the minimum follow-up design needed to make `STOM_Version_2U_C` fully green again after the `V2.75` blocker-fix work.

At this point:

- the direct text contract is fixed
- `verify_nonrelease_sync.py` is green
- `test_ui_runtime_wiring.py` is green

But the branch still fails the legacy compatibility tests that construct `WebCrawling` via `__new__()` and call helper methods without the full runtime initialization path.

The goal of this design is to restore that compatibility without undoing the already-approved timeout contract fix.

## Current State

### Already resolved

The following `2U_C` blocker-fix work is already in place:

- telegram helper contract locked and restored
- WebCrawling timeout contract changed to the literal `self.request_timeout` form required by the non-release verifier
- `verify_nonrelease_sync.py` passes again

### Remaining red gate

`tests/unit/test_webcrawling_network_noise.py` still fails because some paths instantiate `WebCrawling` with `__new__()` and manually seed attributes such as `network_timeout`, but the current implementation now assumes direct `self.request_timeout` attribute access and no longer exposes some of the legacy helper methods expected by those tests.

This means the branch has a **legacy compatibility blocker**, not a timeout-contract blocker anymore.

## Why A Separate Design Is Needed

The previous blocker-fix design was intentionally narrow:

- restore telegram contract
- restore WebCrawling timeout contract
- unblock the downstream wave

Execution proved that the timeout contract and the legacy compatibility path are separate concerns.

If we try to fix both under one vague plan, scope will sprawl.

So this design narrows the remaining problem to:

- preserving the currently correct timeout contract
- reintroducing only the compatibility behavior needed for existing `__new__`-based test construction and helper calls

## Approaches Considered

### 1. Revert the timeout contract fix

**Pros**
- Might make the legacy tests pass again

**Cons**
- Re-breaks the already fixed verifier contract
- invalidates the previous blocker-fix work

### 2. Add a compatibility-safe layer while keeping the timeout contract

Keep the visible `self.request_timeout` contract in production code, but reintroduce the smallest helper/attribute-lookup compatibility path needed by the legacy tests and any branch-local tooling that depends on them.

**Pros**
- Preserves the current green verifier/test contract
- Keeps scope tightly focused
- Matches the evidence from the failing tests

**Cons**
- Leaves some compatibility code in place longer

### 3. Rewrite the legacy tests to match the new implementation

**Pros**
- Simplifies production code

**Cons**
- Too risky right now
- could hide real branch-local assumptions that still matter
- changes acceptance boundaries while the downstream wave is already paused

## Recommendation

Use **Approach 2**.

The safest next step is to preserve the timeout contract fix and add only the smallest compatibility-safe behavior needed for the existing `__new__`-constructed test path.

## Approved Decisions

### 1. Timeout contract stays as fixed

Do not revert the current `self.request_timeout` contract.

That work already closed the explicit `verify_nonrelease_sync.py` blocker.

### 2. Scope stays inside `utility/webcrawling.py` unless proven impossible

The preferred implementation scope is:

- production: `utility/webcrawling.py`

Only widen scope if a test proves that one adjacent file is strictly required to restore compatibility.

### 3. Existing legacy tests are part of the acceptance boundary

The following now define success for this fix:

- `tests/unit/test_webcrawling_contract_text.py`
- `tests/unit/test_telegram_contract_text.py`
- `tests/unit/test_ui_runtime_wiring.py`
- `tests/unit/test_verify_nonrelease_sync.py`
- `tests/unit/test_webcrawling_network_noise.py`
- `tests/test_worktree_policy.py`
- `python scripts/verify_nonrelease_sync.py`

All of them must pass before the downstream wave can resume.

## Audit Focus

The remaining compatibility audit should answer:

1. Which helper methods from the older `WebCrawling` implementation are still required by the existing tests?
2. Which attribute lookups assume `network_timeout` instead of `request_timeout`?
3. Can the branch keep literal `self.request_timeout` calls while still tolerating `__new__()`-constructed objects that seed only `network_timeout`?

Likely minimum compatibility surface:

- `_emit_network_warning`
- `_clear_network_warning`
- `_complete_network_job`
- `_run_network_job`
- `_get_market_indicator`
- `_get_crypto_data`
- `_get_korean_stocks`
- a compatibility-safe timeout accessor or property that does not break the literal `self.request_timeout` contract

## Desired Outcome

The desired result is a single additional corrective commit on `STOM_Version_2U_C` that:

- keeps the current timeout contract intact
- restores the minimum legacy helper compatibility needed by the existing tests
- makes the full `2U_C` blocker-fix gate green

## Success Criteria

- all focused `2U_C` blocker-fix tests pass
- `python scripts/verify_nonrelease_sync.py` stays green
- the branch is clearly ready to resume the downstream wave at `V2.76`

## Explicit Non-Goals

- changing `2U`
- changing `CLI_v267` or `research/init`
- cleaning up every legacy helper permanently
- resuming downstream propagation before the compatibility gate is green
