# STOM Worktree Strategy

> This document describes the current transition state and the target post-promotion topology for the STOM worktrees.

## 1. Purpose

The project is in transition from the absorbed CLI lane to the single-baseline `STOM_Version_2U_C` lane. This doc is the authoritative local lane map for `STOM_V.wt-2uc/`.

## 2. Current Execution State

```text
C:/System_Trading/STOM/
├── STOM_V/       -> STOM_Version_2
├── STOM_V.wt-2u/ -> STOM_Version_2U
├── STOM_V.wt-2uc/-> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/-> STOM_Version_2U_C_CLI_v267
└── STOM_V.wt-lab/-> research/init
```

- `STOM_V.wt-2uc/` is the active integration lane.
- `STOM_V.wt-dev/` still reflects the absorbed CLI baseline.
- Do not describe either lane as already repointed to `STOM_Version_2U_C`.

## 3. Target Post-Promotion State

```text
C:/System_Trading/STOM/
├── STOM_V/       -> STOM_Version_2
├── STOM_V.wt-2u/ -> STOM_Version_2U
├── STOM_V.wt-2uc/-> STOM_Version_2U_C
├── STOM_V.wt-dev/-> STOM_Version_2U_C
└── STOM_V.wt-lab/-> research/init
```

Required propagation chain:

```text
V2 -> 2U -> 2U_C -> research/init
```

## 4. Lane Rules

### 4.1 STOM_V/ - Release ingress

- Only release-originated changes enter through `STOM_Version_2`.
- Keep the release lane separate from baseline development work.
- Do not use this lane for direct feature coding.

### 4.2 STOM_V.wt-2u/ - pyd to py translation

- Use this lane to mirror upstream pyd changes into editable py sources.
- Keep the lane focused on translation and verification of upstream changes.
- Do not push single-baseline feature work into this worktree.

### 4.3 STOM_V.wt-2uc/ - integration lane

- Current branch: `integration/adopt-cli-v267-into-2uc`
- Role: absorb the CLI lane and prepare the cutover
- Do not describe this lane as already on `STOM_Version_2U_C`.

### 4.4 STOM_V.wt-dev/ - absorbed CLI lane during transition

- Current branch: `STOM_Version_2U_C_CLI_v267`
- Role: legacy absorbed lane until promotion completes
- The lane remains transitional until the post-promotion branch move lands.

### 4.5 STOM_V.wt-lab/ - research lane

- Use `research/init` only for formal research, experiments, and proof-of-concept work.
- Research results should not be treated as release input until they are explicitly promoted.

## 5. Operating Notes

- The current state is transition mode.
- The target state is the single-baseline `2U_C` model.
- Only after promotion lands should the docs describe `STOM_V.wt-2uc/` and `STOM_V.wt-dev/` as both on `STOM_Version_2U_C`.
