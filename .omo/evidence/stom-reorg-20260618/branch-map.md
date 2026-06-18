# Branch Map - STOM Reorganization Page 2

Captured: 2026-06-18T22:06:15+09:00
Worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`

## Current Facts

| Item | Value |
|---|---|
| Current worktree | `wt-dev` |
| Current branch | `lazycodex/tick-sparse-positive-generation-improvement-20260604` |
| Current HEAD | `067ef184` |
| Current HEAD title | `공식 OOS 후속 연구 기록 추가` |
| Upstream | `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` |
| Upstream HEAD | `19d82beb` |
| Local anchor branch | `STOM_Version_2U_C-ai-strategy-loop` |
| Local anchor HEAD | `84acb6cb` |
| Anchor remote | absent from `git ls-remote --heads origin STOM_Version_2U_C-ai-strategy-loop` |
| Anchor is ancestor of current HEAD | yes |

## Distance Table

| Comparison | Left count | Right count | Meaning |
|---|---:|---:|---|
| `HEAD...STOM_Version_2U_C-ai-strategy-loop` | 355 | 0 | Current HEAD contains 355 commits after the anchor; anchor has no commits missing from HEAD. |
| `STOM_Version_2U_C-ai-strategy-loop..HEAD` | 355 | n/a | Direct catch-up PR would carry 355 commits into the anchor. |
| `HEAD..STOM_Version_2U_C-ai-strategy-loop` | 0 | n/a | Current HEAD already contains the anchor. |
| `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604...HEAD` | 0 | 36 | `wt-dev` is 36 commits ahead of the remote source branch and 0 behind. |
| `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604..HEAD` | 36 | n/a | Local-only committed work after the upstream source branch. |
| `HEAD..origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` | 0 | n/a | No remote commits missing from current HEAD. |
| `STOM_Version_2U_C-ai-strategy-loop..origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` | 319 | n/a | Remote parent branch has 319 commits after the anchor. |
| first-parent count for anchor to remote source | 186 | n/a | First-parent replay surface before local +36 commits. |
| merge commits for anchor to remote source | 73 | n/a | Actual `git log --merges` count at execution time. Earlier planning estimate was 59 and is superseded by this command output. |

## Graph

```text
STOM_Version_2U_C
    ↓ +125 commits
STOM_Version_2U_C-ai-strategy-loop
84acb6cb  local anchor, no origin branch currently present
    ↓ +319 commits to remote source
origin/lazycodex/tick-sparse-positive-generation-improvement-20260604
19d82beb  PR #96 merge point
    ↓ +36 local commits
wt-dev HEAD
067ef184  lazycodex/tick-sparse-positive-generation-improvement-20260604
```

## Representative First-Parent Merge Surface

The first-parent merge list is dominated by upstream sync merges and webbt PR merges. Representative latest entries:

```text
7412f1a3 Merge remote-tracking branch 'origin/lazycodex/tick-sparse-positive-generation-improvement-20260604' into lazycodex/tick-sparse-positive-generation-improvement-20260604
d036da5e Merge remote-tracking branch 'origin/lazycodex/tick-sparse-positive-generation-improvement-20260604' into lazycodex/tick-sparse-positive-generation-improvement-20260604
a43c458c Merge remote-tracking branch 'origin/lazycodex/tick-sparse-positive-generation-improvement-20260604' into lazycodex/tick-sparse-positive-generation-improvement-20260604
87529165 Merge remote-tracking branch 'origin/lazycodex/tick-sparse-positive-generation-improvement-20260604' into lazycodex/tick-sparse-positive-generation-improvement-20260604
ae9f0af7 Merge pull request #53 from Py-CI-Park/feature/webbt-phase14
```

## QA Results

| Scenario | Command | Result |
|---|---|---|
| graph count reproduction | `git rev-list --left-right --count "HEAD...STOM_Version_2U_C-ai-strategy-loop"` | `355 0` |
| direct anchor to HEAD count | `git rev-list --count "STOM_Version_2U_C-ai-strategy-loop..HEAD"` | `355` |
| reverse count | `git rev-list --count "HEAD..STOM_Version_2U_C-ai-strategy-loop"` | `0` |
| current source ahead/behind | `git rev-list --left-right --count "origin/lazycodex/tick-sparse-positive-generation-improvement-20260604...HEAD"` | `0 36` |
| no branch mutation | `git branch --show-current` before/after Page 2 | remained `lazycodex/tick-sparse-positive-generation-improvement-20260604` |

Cleanup receipt:
- No branch was created, checked out, moved, reset, rebased, pushed, or merged.
