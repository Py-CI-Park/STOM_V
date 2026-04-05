# STOM Project Guidelines

## Formal Update Operating System

Primary operating document:
- `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`

Carry-forward registry:
- `docs/CARRY_FORWARD_REGISTRY.md`

Current cycle status:
- `docs/update_log/2026-04-05_v274_v277_cycle_status.md`

Release preflight:
```bash
python scripts/verify_release_sync.py
```

## 커밋 작성 언어 규칙

- 모든 신규 커밋 제목은 한글로 작성합니다.
- 모든 신규 커밋 본문은 한글 마크다운으로 작성합니다.
- 기본 본문 구조는 `## 배경`, `## 변경 사항`, `## 검증`, 필요 시 `## 주의사항`을 사용합니다.
- `docs: ...`, `fix: ...` 같은 영문 타입 접두사 제목은 더 이상 기본 형식으로 사용하지 않습니다.
- 트레일러를 사용할 때도 한글 값을 우선합니다.
- 정식 버전 기록 커밋만 제목을 `STOM V{major}.{minor}`로 유지하고, 본문은 한글 마크다운으로 작성합니다.

## Release And Worktree Mapping

## Current Transition State

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/     -> STOM_Version_2U_C_CLI_v267
└── STOM_V.wt-lab/     -> research/init
```

`STOM_V.wt-2uc/` is the active integration lane. `STOM_V.wt-dev/` still carries the absorbed CLI baseline. Do not describe the single-baseline cutover as already complete.

## Target Post-Promotion State

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> STOM_Version_2U_C
├── STOM_V.wt-dev/     -> STOM_Version_2U_C
└── STOM_V.wt-lab/     -> research/init
```

After promotion, both `STOM_V.wt-2uc/` and `STOM_V.wt-dev/` should point at `STOM_Version_2U_C`.

## Upstream Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- Judge upstream freshness against `https://github.com/devstom/STOM.git`.
- Treat `C:/System_Trading/STOM/STOM_devstom` as a reference-only mirror, not the sole freshness authority.

Current transition flow:

```text
V2 -> 2U -> integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C_CLI_v267 -> research/init
```

Target post-promotion flow:

```text
V2 -> 2U -> 2U_C -> research/init
```

`STOM_Version_2` remains the release-ingress branch. The target cutover is not yet the current live topology, so do not bypass V2 ingress or skip intermediate lanes.

## Upstream Freshness Check

Use this operator sequence before deciding whether the release lane needs an update:

```bash
git fetch https://github.com/devstom/STOM.git master:refs/remotes/devstom_tmp/master
git show refs/remotes/devstom_tmp/master:_update.txt | head -5
python scripts/verify_release_sync.py
```

The `git fetch` command refreshes a temporary remote-tracking ref from the authoritative GitHub upstream. Inspect `_update.txt` from that fetched ref to confirm the newest release marker before starting propagation.

## Release Preflight

Before release propagation, policy verification, or handoff, run:

```bash
python scripts/verify_release_sync.py
```

If you are validating an isolated checkout root, use:

```bash
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-upsync
```

Expect `release sync preflight passed` before claiming the lane is clean. During the current transition the live flow remains `V2 -> 2U -> integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C_CLI_v267 -> research/init`, and only after promotion does the target flow become `V2 -> 2U -> 2U_C -> research/init`.

## Protected Paths

- `backtest/graph/` is protected result data.
- It is not a git-propagated source path.
- Do not treat result files there as release-overlay inputs.

## Operator Rules

- Keep docs, scripts, tests, CLI-only surfaces, and research-only surfaces out of release overlays unless the task explicitly targets them.
- Keep this guide aligned with `docs/WORKTREE_STRATEGY.md` and `docs/UPSTREAM_SYNC_STRATEGY.md`.
