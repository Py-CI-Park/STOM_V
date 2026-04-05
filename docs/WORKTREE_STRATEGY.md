# STOM Worktree Strategy

> This document describes the worktree lanes used by the STOM project.

## 1. Purpose

The project uses separate worktrees so the release upstream, the 2U py lane, the 2U_C single-baseline lane, and the research lane can move independently without mixing responsibilities.

## 2. Current Layout

```text
C:/System_Trading/STOM/
├── STOM_V/       -> STOM_Version_2
├── STOM_V.wt-2u/ -> STOM_Version_2U
├── STOM_V.wt-2uc/-> STOM_Version_2U_C
├── STOM_V.wt-dev/-> STOM_Version_2U_C
└── STOM_V.wt-lab/-> research/init
```

`STOM_V.wt-2uc/` and `STOM_V.wt-dev/` both point at the same single-baseline branch. `STOM_V.wt-dev/` is the active development checkout.

## 3. Propagation Chain

Required propagation order:

```text
V2 -> 2U -> 2U_C -> research/init
```

Mapped lanes:

1. `STOM_Version_2` in `STOM_V/`
2. `STOM_Version_2U` in `STOM_V.wt-2u/`
3. `STOM_Version_2U_C` in `STOM_V.wt-2uc/`
4. `STOM_Version_2U_C` in `STOM_V.wt-dev/`
5. `research/init` in `STOM_V.wt-lab/`

## 4. Lane Rules

### 4.1 STOM_V/ — Release ingress

- Only release-originated changes enter through `STOM_Version_2`.
- Keep the release lane separate from baseline development work.
- Do not use this lane for direct feature coding.

### 4.2 STOM_V.wt-2u/ — pyd to py translation

- Use this lane to mirror upstream pyd changes into editable py sources.
- Keep the lane focused on translation and verification of upstream changes.
- Do not push single-baseline feature work into this worktree.

### 4.3 STOM_V.wt-dev/ — 주력 개발

**홈 브랜치**: `STOM_Version_2U_C`
**역할**: custom + CLI 단일 기준선 작업 레인

- This is the primary checkout for the current baseline.
- Use it for active coding, integration work, and baseline-safe CLI automation.
- Do not route live work through a downstream CLI child branch.

### 4.4 STOM_V.wt-2uc/ — companion baseline checkout

- Shares the same `STOM_Version_2U_C` branch as `STOM_V.wt-dev/`.
- Use it when a second checkout is helpful for inspection, comparison, or isolated edits.
- Keep the branch model identical to the main baseline lane.

### 4.5 STOM_V.wt-lab/ — research lane

- Use `research/init` only for formal research, experiments, and proof-of-concept work.
- Research results should not be treated as release input until they are explicitly promoted.

## 5. Operating Notes

- Keep `STOM_V.wt-dev/` and `STOM_V.wt-2uc/` aligned on the same baseline branch.
- Treat `research/init` as downstream of the baseline chain, not as a live development lane.
- Historical CLI child-lane names are retired and should not be used in active guidance.
