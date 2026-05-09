# STOM Worktree Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md` for V2 formal release work and to `docs/V3_UPDATE_OPERATING_SYSTEM.md` for V3/V3U/2U_C backport work.

- Updated: 2026-05-06
- Scope: active STOM release, V3 transition, pyd-free, and custom/backport worktrees

## Current Active State

```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
+-- STOM_V.wt-3/       -> STOM_Version_3
+-- STOM_V.wt-3u/      -> STOM_Version_3U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
```

- `STOM_V/` remains the V2 official/root orchestration checkout.
- `STOM_V.wt-3/` is the V3 official ingress checkout and currently reflects V3 official updates through `STOM V3.18`.
- `STOM_V.wt-3u/` is the V3 pyd-free checkout and currently has no tracked `.pyd` files.
- `STOM_V.wt-dev/` is the sole active checkout location for `STOM_Version_2U_C`.
- `STOM_V.wt-2uc/` is retained as an archive/history/transition checkout on `integration/adopt-cli-v267-into-2uc`.
- `research/init` is excluded from the current official propagation chain.
- Do not describe `wt-2uc` as an active canonical lane or restore the retired live CLI child-lane model.

## Current Chains

```text
V2 official maintenance:  STOM_Version_2 -> STOM_Version_2U -> STOM_Version_2U_C
V3 official/pyd-free:     STOM_Version_3 -> STOM_Version_3U
2U_C V3 backport queue:   STOM_Version_3 selected feature -> STOM_Version_2U_C documented backport
```

`STOM_Version_3U_C` is intentionally not created.

## Role Of Each Worktree

- `STOM_V/`: V2 official ingress and root orchestration lane. V3/V3U handoff and strategy documents live here for discoverability.
- `STOM_V.wt-2u/`: V2 pyd-free inference lane. It may be used as a reference for pyd-to-py patterns, not as the base for 3U.
- `STOM_V.wt-dev/`: active single-baseline lane for `STOM_Version_2U_C`, the V2/Kiwoom custom/backport lane.
- `STOM_V.wt-3/`: V3 official ingress lane. It keeps upstream files and upstream `.pyd` files.
- `STOM_V.wt-3u/`: V3 pyd-free lane derived from `STOM_Version_3`. It removes/replaces V3 pyd targets only.
- `STOM_V.wt-2uc/`: archive/history/transition lane that preserves old promotion evidence and execution logs.

## Branch Parity Invariants

- `STOM_Version_2` / `*_2` is the V2 official upstream update reflection lane. It keeps official files, including upstream `.pyd` files.
- `STOM_Version_2U` is the V2 pyd-to-py inference lane. All non-pyd official runtime files should match `STOM_Version_2`; pyd inference defects should be fixed in inferred `.py`, MainWindow wrapper, process wrapper, or verification-contract boundaries.
- `STOM_Version_2U_C` is the V2/Kiwoom custom lane derived from 2U. Custom edits may be made in this lane, but each runtime difference from 2U must be documented in the carry-forward/update log allowlist before it is treated as intentional.
- `STOM_Version_3` is the V3 official upstream reflection lane. It must preserve upstream `.pyd` files and must not receive pyd-free/custom edits.
- `STOM_Version_3U` is the V3 pyd-free lane derived from `STOM_Version_3`. Its difference from V3 should be limited to pyd removal, Python replacement/wrapper/inference, and verification/audit scaffolding.
- Verification order:
  1. `2U` vs `V2`: only pyd-to-py inference differences are expected.
  2. `2U_C` vs `2U`: only documented custom/backport differences are expected.
  3. `3U` vs `V3`: only V3 pyd-free differences are expected.

## 2U_C V3 Backport Boundary

`STOM_Version_2U_C` may receive selected V3 features only as documented backports.

Backport rules:

1. Prefer broker-neutral features first.
2. Do not import LS API runtime assumptions into the Kiwoom-maintained lane.
3. Do not apply DB-incompatible changes without migration spec, backup, dry-run, and rollback plan.
4. Record source V3 version/commit/files, excluded LS dependency, Kiwoom adjustment, and verification evidence.
5. Keep backport commits separate from V3 official and V3U pyd-free commits.

## Protection Rules

- V2 official updates enter only through `STOM_Version_2`.
- V3 official updates enter only through `STOM_Version_3`.
- V3 pyd removal occurs only in `STOM_Version_3U`.
- `STOM_Version_3U_C` must not be created until a separate strategy decision explicitly authorizes it.
- `backtest/graph/` is a protected result-data path, not a git-propagated source path.
- `_database`, `_log`, and `*.db` are runtime data and must not be committed.
- Docs, scripts, tests, CLI-only surfaces, and research-only surfaces stay out of release overlays unless a task explicitly targets them.
- Before actual V3 backport work in `2U_C`, confirm `STOM_V.wt-dev/` is on `STOM_Version_2U_C`, note any untracked runtime/output paths, and start from a documented backport queue item.
- Do not check out `STOM_Version_2U_C` in `wt-2uc` while `wt-dev` is the active baseline holder.

Before V2 release work or propagation verification, run:

```bash
python scripts/verify_release_sync.py
```

Before V3U pyd-free verification, use the V3U-specific scripts in `STOM_V.wt-3u/scripts/`.
