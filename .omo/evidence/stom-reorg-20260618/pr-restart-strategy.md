# PR Restart Strategy - STOM Reorganization Page 2

Captured: 2026-06-18T22:06:15+09:00

## Decision

Use `STOM_Version_2U_C-ai-strategy-loop` as the canonical AI evolution dashboard anchor and bring it forward by reviewed PR merge only.

Do not update the anchor by force-push, reset, rebase, direct overwrite, cherry-pick batch without review, or local checkout mutation.

## Preconditions

| Precondition | Required State | Current State |
|---|---|---|
| Dirty state classified | Page 3 completed | completed in `dirty-worktree-inventory.md` |
| Include/exclude list known | selected files only | not yet selected for commit |
| Source branch pushed | `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` must include local +36 commits | not yet; remote is `19d82beb` |
| Base branch exists on remote | `origin/STOM_Version_2U_C-ai-strategy-loop` | absent |
| Protected/runtime paths untouched | explicit protected path status empty | empty in `protected-path-status.txt` |

## Default Catch-Up PR Route

```text
base:    STOM_Version_2U_C-ai-strategy-loop
compare: lazycodex/tick-sparse-positive-generation-improvement-20260604
```

Execution sequence for later work, not performed in Page 1~3:

1. Finish dirty-state classification.
2. Decide which `wt-dev` changes are included in the restart PR and which remain local/deferred.
3. Commit only selected changes using explicit paths, never `git add -A`.
4. Push the local anchor because `origin/STOM_Version_2U_C-ai-strategy-loop` is absent.
5. Push the current source branch after selected commits are complete.
6. Open PR with the base/compare pair above.
7. Review the +355 commit diff as a catch-up PR.
8. Merge the PR.
9. Create the next development branch from the updated `STOM_Version_2U_C-ai-strategy-loop`.

## Fallback Wave Replay Route

Use this if the +355 commit catch-up PR is too broad to review safely.

| Wave | Proposed branch | Scope | PR base |
|---|---|---|---|
| 1 | `integration/ai-loop-replay-20260618-foundation` | Phase14/webbt foundation and preserved merge history notes | `STOM_Version_2U_C-ai-strategy-loop` |
| 2 | `integration/ai-loop-replay-20260618-dashboard` | dashboard records, GUI parity, API/UI surfaces, bundle gates | updated anchor after Wave 1 |
| 3 | `integration/ai-loop-replay-20260618-research` | condition research/OOS/evidence docs and scripts | updated anchor after Wave 2 |
| 4 | `integration/ai-loop-replay-20260618-local36` | local +36 committed work from `wt-dev` | updated anchor after Wave 3 |
| 5 | `integration/ai-loop-replay-20260618-current-dirty` | selected current dirty/untracked files after Page 3 review | updated anchor after Wave 4 |

Fallback rule:
- Prefer one catch-up PR if review tooling can handle the full 355-commit span.
- Switch to wave replay if the PR obscures source/evidence/dash boundaries, mixes protected paths, or makes file ownership unclear.
- In either route, the final target remains `STOM_Version_2U_C-ai-strategy-loop`.

## Remote Base Readiness QA

Command:
```powershell
git ls-remote --heads origin STOM_Version_2U_C-ai-strategy-loop lazycodex/tick-sparse-positive-generation-improvement-20260604
```

Observed output:
```text
19d82bebe55f82e95cf75a894b7ada10881dfb6f refs/heads/lazycodex/tick-sparse-positive-generation-improvement-20260604
```

Interpretation:
- `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` exists at `19d82beb`.
- `origin/STOM_Version_2U_C-ai-strategy-loop` is absent.
- The anchor must be pushed before a GitHub PR can target it as base.

## Guardrails

- Do not touch V3K gate 4~6, KHOPENAPI, live order wiring, serial-key behavior, or protected runtime paths.
- Do not use `wt-webbt` as the canonical restart branch.
- Keep `wt-webbt` as a clean auxiliary dashboard PR worktree.
- Preserve `wt-dev` research artifacts until Page 3 staging decisions are made.
- Do not stage, commit, push, or open PR in Page 1~3.

Cleanup receipt:
- No branch, PR, push, merge, stash, rebase, reset, or checkout operation was performed.
