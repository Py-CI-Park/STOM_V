# STOM Worktree Strategy

> This document describes the active promoted topology for the STOM worktrees.

## 1. Purpose

The project is running on the promoted single-baseline `STOM_Version_2U_C` model. This doc is the authoritative local lane map for `STOM_V.wt-dev/`.

## 2. Current Execution State

```text
C:/System_Trading/STOM/
├── STOM_V/       -> STOM_Version_2
├── STOM_V.wt-2u/ -> STOM_Version_2U
├── STOM_V.wt-2uc/-> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/-> STOM_Version_2U_C
└── STOM_V.wt-lab/-> research/init
```

- `STOM_V.wt-dev/` is the sole active checkout for `STOM_Version_2U_C`.
- `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/transition checkout.
- Do not describe `wt-2uc` as the active canonical lane.

Required propagation chain:

```text
V2 -> 2U -> 2U_C -> research/init
```

## 3. Lane Rules

### 3.1 STOM_V/ - Release ingress

- Only release-originated changes enter through `STOM_Version_2`.
- Keep the release lane separate from baseline development work.
- Do not use this lane for direct feature coding.

### 3.2 STOM_V.wt-2u/ - pyd to py translation

- Use this lane to mirror upstream pyd changes into editable py sources.
- Keep the lane focused on translation and verification of upstream changes.
- Do not push single-baseline feature work into this worktree.

### 3.3 STOM_V.wt-2uc/ - archive transition lane

- Current branch: `integration/adopt-cli-v267-into-2uc`
- Role: preserve promotion logs, consolidation history, and transition references.
- Do not treat this lane as the active `2U_C` baseline.

### 3.4 STOM_V.wt-dev/ - active single-baseline lane

- Current branch: `STOM_Version_2U_C`
- Role: live single-baseline lane after promotion.
- This is the only active checkout that should hold `STOM_Version_2U_C` in the current topology.

### 3.5 STOM_V.wt-lab/ - research lane

- Use `research/init` only for formal research, experiments, and proof-of-concept work.
- Research results should not be treated as release input until they are explicitly promoted.

## 4. Operating Notes

- The current state is the promoted single-baseline `2U_C` model.
- `wt-2uc` remains an archive/history checkout while `wt-dev` holds the live baseline branch.
- Do not restore the retired live CLI child-lane model in active docs.
