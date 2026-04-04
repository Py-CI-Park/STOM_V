# V2.75 2U_C WebCrawling Contract Design

**Date:** 2026-04-04
**Scope:** `STOM_Version_2U_C` only, focused on the `utility/webcrawling.py` / telegram-related non-release contract that remains red after the exact `V2.74` restore
**Out of Scope:** `2U` (already green), `CLI_v267`, `research/init`, `V2.76`, `V2.77`, or broad runtime cleanup outside the exact failing contract surface

## Goal

Determine the minimum branch-local corrective shape needed to make `STOM_Version_2U_C` pass its non-release verification again after `V2.75`, without turning this pause into a broad refactor.

This design exists because the original blocker-fix hypothesis was only half-correct:

- restoring the `V2.74` telegram/webcrawling contract fully fixed `2U`
- the same exact restore did **not** fix `2U_C`

So the remaining work is no longer "restore pre-`V2.75` exactly." The remaining work is "identify the smallest `2U_C`-specific delta required to satisfy the non-release contract again."

## Current State

### Proven result on `2U`

`2U` now passes after a strict restore of:

- `utility/telegram_bot.py`
- `utility/webcrawling.py`

from `9822681d` (`STOM V2.74` on `2U`).

### Current `2U_C` result

`2U_C` currently has:

- `V2.75` downstream propagation commit
- text-based telegram contract lock test
- attempted exact restore from `2c660152` (`STOM V2.74` on `2U_C`)

But after that exact restore:

- `python -m pytest tests/unit/test_telegram_contract_text.py tests/unit/test_ui_runtime_wiring.py tests/unit/test_verify_nonrelease_sync.py tests/test_worktree_policy.py -q`
  still has a failing `test_webcrawling_network_calls_use_timeouts`
- `python scripts/verify_nonrelease_sync.py`
  still fails with `WebCrawling stop contract is incomplete.`

That means the remaining blocker is specifically the `2U_C` WebCrawling contract, not the telegram qlist helper anymore.

## Key Design Fact

The downstream blocker-fix plan assumed that restoring both files from the `2U_C` pre-`V2.75` head would be enough.

Execution proved that assumption false.

Therefore the next corrective step must:

1. keep the already-restored telegram contract stable
2. isolate the remaining `WebCrawling` contract mismatch
3. make the smallest possible `2U_C`-local change that satisfies the branch’s verifier/test expectations

## Approaches Considered

### 1. Re-run exact restore and accept verifier disagreement

**Pros**
- Closest to historical purity

**Cons**
- Already disproven by execution
- leaves `2U_C` blocked

### 2. Minimum `2U_C`-local contract patch

Keep `telegram_bot.py` aligned with the restored helper contract, but patch only the WebCrawling details that `2U_C`’s verifier still requires.

**Pros**
- Narrowest practical fix
- Matches the evidence from execution
- Keeps the blocker-fix focused on the actual remaining red surface

**Cons**
- Produces a branch-local divergence from strict `V2.74` restore

### 3. Rewrite verifier expectations

Treat the remaining failure as verifier stale and update `verify_nonrelease_sync.py` instead of `utility/webcrawling.py`.

**Pros**
- Potentially smaller code change

**Cons**
- Dangerous without first proving the branch should intentionally accept the weaker contract
- risks hiding a real non-release runtime guarantee

## Recommendation

Use **Approach 2: minimum `2U_C`-local contract patch**.

The evidence now says `2U_C` genuinely expects a stronger WebCrawling contract than the exact pre-`V2.75` restore provides. The correct next step is to patch only that contract surface, not to widen the scope or pretend the verifier is wrong without proof.

## Approved Decisions

### 1. Telegram contract is no longer the blocker

The telegram helper contract should remain locked as restored. The remaining blocker work should focus on `utility/webcrawling.py`.

### 2. Keep scope to one production file if possible

The preferred implementation scope is:

- production: `utility/webcrawling.py`
- tests/verifier already in place

Only widen the scope if the WebCrawling contract turns out to depend on one adjacent runtime surface that cannot be expressed in that file alone.

### 3. Use the existing verifier as the acceptance boundary

The branch-local success boundary for this fix is:

- `python -m pytest tests/unit/test_telegram_contract_text.py tests/unit/test_ui_runtime_wiring.py tests/unit/test_verify_nonrelease_sync.py tests/test_worktree_policy.py -q`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`

All of them must pass.

## Audit Focus

The design assumes a focused comparison of:

- `2U` green state after restore
- `2U_C` red state after restore

Primary question:

- what exact `utility/webcrawling.py` contract difference explains why `2U` is green but `2U_C` is still red?

Likely areas to inspect:

- `self.request_timeout = 10`
- `self.treemap_timer = None`
- `self.treemap_timer.cancel()`
- `self.wait(2000)`
- count of `timeout=self.request_timeout`
- any helper abstraction that hides the literal contract string the verifier currently expects

## Desired Outcome

The result of this design should be one branch-local corrective commit on `2U_C` that:

- keeps the restored telegram helper contract intact
- restores the required WebCrawling stop/network contract in the exact form `2U_C` verification expects
- reopens the downstream wave for `V2.76`

## Success Criteria

- `2U_C` verifier is green again
- the `2U_C` blocker is explicitly closed
- `V2.76` downstream propagation can resume without ambiguity

## Explicit Non-Goals

- revisiting the `2U` fix
- changing `CLI_v267` / `research/init`
- solving carry-forward runtime risks unrelated to the WebCrawling contract
