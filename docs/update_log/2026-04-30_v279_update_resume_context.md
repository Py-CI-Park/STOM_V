# 2026-04-30 V2.79 update resume context

## Purpose

This document preserves the working context for resuming the official STOM update work without relying on chat history.

The immediate goal is not to start the code update yet. The immediate goal is to align the update operating documents and verification policy, then later intake the remaining V2 releases through `V2.79`.

## Current decision summary

- Official V2 work must stop at GitHub release tag `V2.0`.
- `V2.0` tag commit is `873d51eed3f581daa1925bcd9e3672254f525f0a`.
- The top release marker in `V2.0:_update.txt` is `2026-04-08 V2.79`.
- Current `STOM_Version_2` is updated only through `STOM V2.77`.
- Remaining V2 official intake target is exactly `V2.78` and `V2.79`.
- GitHub upstream default branch is now `V3.00`.
- Latest checked `V3.00` head is `ab98d536c7776005456438647ec4552bc55cc627`.
- Latest checked `V3.00:_update.txt` top marker is `2026-04-29 V3.13`.
- `V3.00` is out of scope for the V2.79 update wave.
- `research/init` is no longer part of the local official propagation chain.

## Upstream facts checked on 2026-04-30

Official GitHub repository:

```text
https://github.com/devstom/STOM
```

Latest checked refs:

```text
HEAD -> refs/heads/V3.00
refs/heads/V3.00 -> ab98d536c7776005456438647ec4552bc55cc627
refs/tags/V2.0   -> 873d51eed3f581daa1925bcd9e3672254f525f0a
refs/tags/V3.0   -> d21e42425cfc6f2254431e8622b1bbf0dd89303e
```

GitHub release `V2.0` says it is the Kiwoom domestic stock, overseas futures, Upbit, and Binance futures linked version, and that the tag closes V2 before the LS Securities REST API rewrite.

Important implication:

```text
Use refs/tags/V2.0 for V2.78/V2.79.
Do not use refs/heads/V3.00 or refs/tags/V3.0 for the V2 update wave.
```

## Current local branch/worktree state

Main release worktree:

```text
C:/System_Trading/STOM/STOM_V
branch: STOM_Version_2
head: 0fdb7264fc483ec244320156bcb0e9c4af32858f
status: clean
latest official release commit: STOM V2.77
```

2U worktree:

```text
C:/System_Trading/STOM/STOM_V.wt-2u
branch: STOM_Version_2U
head: 92c40ab1d0f937f87e9b3b68bdcb8b4adb7788a3
status: clean
```

2U_C active worktree:

```text
C:/System_Trading/STOM/STOM_V.wt-dev
branch: feature/2uc-upstream-sync-prep
head: d9abdcae6e59491983f2816249f8af015d4917f3
status: only untracked backtest/graph/
```

2U_C branch:

```text
STOM_Version_2U_C
origin/STOM_Version_2U_C
head: d9abdcae6e59491983f2816249f8af015d4917f3
commit: Merge pull request #32 from Py-CI-Park/feature/cli-command-family-refactor-review
```

Interpretation:

- `2U_C` development has been mostly consolidated.
- `wt-dev` is on a preparation feature branch, not directly on `STOM_Version_2U_C`.
- The feature branch points at the same commit as `STOM_Version_2U_C`.
- `backtest/graph/` is protected result data and should not be treated as release input.
- Before actual V2.78/V2.79 propagation into `2U_C`, either switch/use a clean `STOM_Version_2U_C` worktree or create a temporary clean worktree for the branch.

Archive/transition worktree:

```text
C:/System_Trading/STOM/STOM_V.wt-2uc
branch: integration/adopt-cli-v267-into-2uc
role: archive/transition only
```

Research lane:

```text
local research/init worktree was removed
local research/init branch was deleted
origin/research/init still exists and was intentionally preserved
```

## Current official propagation chain

Use this chain for the V2.79 update wave:

```text
V2 -> 2U -> 2U_C
```

Do not use this older chain for new official propagation:

```text
V2 -> 2U -> 2U_C -> CLI_v267 -> research/init
```

Current roles:

```text
STOM_V/       -> STOM_Version_2       -> official release ingress
STOM_V.wt-2u/ -> STOM_Version_2U      -> pyd-to-py translation lane
STOM_V.wt-dev -> STOM_Version_2U_C    -> active single-baseline downstream lane
STOM_V.wt-2uc -> integration archive  -> not active propagation target
```

## Stale instructions already identified

The repository still contains old or conflicting guidance that must be corrected before official update execution:

- `AGENTS.md` still mentions zip-only staging and `C:/Users/parkc/Downloads/STOM_temp/STOM_V{version}.zip`.
- `docs/stom_v2_update_guide.md` is mostly a legacy zip workflow guide.
- `scripts/stom_v2_update.py` is a zip-driven updater and should not be the official path for this wave.
- `utility/upstream_sync_policy.py` and `scripts/verify_release_sync.py` have historically expected the older `2U_C -> CLI_v267 -> research/init` chain.
- Some branch-local guidance in downstream worktrees still mentions `CLI_v267` or `research/init` as active propagation lanes.

Correct target:

```text
Official source: GitHub refs/tags/V2.0
Version boundary: _update.txt sections in that tag
Propagation: V2 -> 2U -> 2U_C
V3: excluded
research/init: excluded
```

## V2.79 wave scope

Already present in `STOM_Version_2`:

```text
STOM V2.77
```

To intake from `refs/tags/V2.0`:

```text
STOM V2.78
STOM V2.79
```

Commit rule:

```text
one official version = one commit
commit title: STOM V{version}
commit body: full matching _update.txt section from refs/tags/V2.0
```

Do not include:

```text
V3.0
V3.01
V3.02
V3.03
V3.04
V3.05
V3.06
V3.07
V3.08
V3.09
V3.10
V3.11
V3.12
V3.13
```

## Latest measured diffs

Current `STOM_Version_2` to official V2 terminal tag:

```text
git diff --shortstat STOM_Version_2..refs/remotes/devstom_tmp/tags/V2.0
194 files changed, 7695 insertions(+), 30645 deletions(-)
```

Current `STOM_Version_2` to latest V3 branch:

```text
git diff --shortstat STOM_Version_2..refs/remotes/devstom_tmp/V3.00
518 files changed, 36553 insertions(+), 59417 deletions(-)
```

V2 terminal tag to latest V3 branch:

```text
git diff --shortstat refs/remotes/devstom_tmp/tags/V2.0..refs/remotes/devstom_tmp/V3.00
426 files changed, 37662 insertions(+), 37576 deletions(-)
```

V2 terminal tag to latest V3 branch commit count:

```text
360 commits
```

Interpretation:

- V2.78/V2.79 is a bounded release intake wave.
- V3 is a separate migration project, not the next small official update.

## V3 facts to remember

V3 currently remains out of scope, but later migration planning must account for these facts:

- Latest checked V3 marker is `V3.13`.
- V3 still has a compiled UI component: `ui/main_window.pyd`.
- Latest checked `ui/main_window.pyd` size is `282624` bytes.
- V3 includes data learning and analysis systems under `strategy/analyzer_*.py`.
- V3 learning/analysis surfaces include candle pattern, microstructure, risk, volatility pattern, volume profile, and volume spike analysis.
- V3 `_update.txt` explicitly mentions analysis learning, learned data storage, duplicate learning avoidance, real-time loading of learned data, and backtest loading of learned data before the backtest date.
- V3 also changes broker/API, DB compatibility, folder structure, UI structure, and runtime assumptions.

V3 must be handled with a separate migration design after the V2.79 wave is complete.

## Required next work before actual update execution

1. Align formal update docs and entrypoint guidance.
2. Remove or legacy-mark zip-based official update workflow.
3. Update policy constants and verification scripts to the current chain.
4. Ensure `verify_release_sync.py` reflects `V2 -> 2U -> 2U_C` and excludes `research/init`.
5. Confirm a clean `2U_C` work location before propagation.
6. Create a design/spec for the V2.79 wave.
7. Create a detailed implementation plan.
8. Execute `STOM V2.78` and `STOM V2.79` release intake.
9. Propagate to `2U`, preserving pyd-to-py translation rules.
10. Propagate to `2U_C`, preserving branch-local runtime and compatibility contracts.
11. Record V2.79 cycle closeout.

## Verification expectations

Before claiming any update stage is complete:

- Run release preflight from `STOM_V`.
- Run non-release verification in `STOM_V.wt-2u`.
- Run non-release verification in the active `2U_C` worktree.
- Confirm `backtest/graph/` remains protected result data.
- Confirm no V3 files or V3 `_update.txt` sections entered the V2 wave.
- Confirm commit titles and bodies follow the official version commit rule.

## Useful commands

Refresh latest upstream references:

```powershell
git fetch https://github.com/devstom/STOM.git `
  refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00 `
  refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0 `
  refs/tags/V3.0:refs/remotes/devstom_tmp/tags/V3.0
```

Check V2 terminal marker:

```powershell
git show refs/remotes/devstom_tmp/tags/V2.0:_update.txt |
  Select-String -Pattern '^\d{4}-\d{2}-\d{2} V[0-9]+\.[0-9]+' |
  Select-Object -First 20
```

Check latest V3 marker:

```powershell
git show refs/remotes/devstom_tmp/V3.00:_update.txt |
  Select-String -Pattern '^\d{4}-\d{2}-\d{2} V[0-9]+\.[0-9]+' |
  Select-Object -First 30
```

Check active worktrees:

```powershell
git worktree list --porcelain
```

Check V2 target diff:

```powershell
git diff --shortstat STOM_Version_2..refs/remotes/devstom_tmp/tags/V2.0
```

Check V3 divergence:

```powershell
git diff --shortstat STOM_Version_2..refs/remotes/devstom_tmp/V3.00
```

## Current recommended action

Do not start applying V2.78/V2.79 yet.

First create and review the formal design/spec for update-procedure alignment and the V2.79 wave. The design must incorporate this document as current context and must explicitly preserve these decisions:

- `V2.0` tag is the source for V2.78/V2.79.
- `V3.00` is excluded.
- `research/init` is excluded.
- `2U` owns pyd-to-py translation.
- `2U_C` owns active downstream runtime compatibility.
- zip-based official update instructions are stale.

## Resume continuation on 2026-04-30

Follow-up alignment work completed after this context was written:

- Added this resume context to git history.
- Added V2.79 design/spec: `docs/superpowers/specs/2026-04-30-v279-update-wave-design.md`.
- Added V2.79 implementation plan: `docs/superpowers/plans/2026-04-30-v279-update-wave.md`.
- Updated entrypoint docs and verification policy to the active `V2 -> 2U -> 2U_C` chain.
- Marked the zip workflow as legacy for the V2.79 wave.
- Switched `C:/System_Trading/STOM/STOM_V.wt-dev` from `feature/2uc-upstream-sync-prep` to `STOM_Version_2U_C`; both branches pointed at `d9abdcae6e59491983f2816249f8af015d4917f3` before the switch.
- Confirmed `backtest/graph/` remains the only untracked item in `wt-dev`.
- Confirmed `python scripts/verify_release_sync.py` passes after the `wt-dev` branch switch.
