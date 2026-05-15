# STOM Project Guidelines

## Formal Update Operating System

Primary operating document:
- `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`

Carry-forward registry:
- `docs/CARRY_FORWARD_REGISTRY.md`

Current resume context:
- `docs/update_log/2026-04-30_v279_update_resume_context.md`

Previous closed cycle status:
- `docs/update_log/2026-04-05_v274_v277_cycle_status.md`

Release preflight:
```bash
python scripts/verify_release_sync.py
```

## Commit Language Rules

- All git commit titles must be written in Korean.
- All git commit bodies must be written in Korean markdown.
- Prefer descriptive intent titles over prefix-only titles such as `docs:` or `fix:`.

## Release And Worktree Mapping

## Current Promoted State

```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
```

`STOM_V.wt-dev/` is the active checkout location for `STOM_Version_2U_C`. `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/transition checkout that preserves promotion history and execution logs.

## Upstream Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- Judge upstream freshness against `https://github.com/devstom/STOM.git`.
- Treat `C:/System_Trading/STOM/STOM_devstom` as a reference-only mirror, not the sole freshness authority.
- Use GitHub `refs/tags/V2.0` as the source for the current V2.79 wave.
- Exclude `refs/heads/V3.00`, `refs/tags/V3.0`, and all V3 update sections from this V2 wave.

Current live flow:

```text
V2 -> 2U -> 2U_C
```

Archive reference:

```text
integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C
```

`STOM_Version_2` remains the release-ingress branch. The canonical active propagation chain is `V2 -> 2U -> 2U_C`. The current official propagation chain stops at `2U_C`; `research/init` is not part of the V2.79 wave. Do not bypass V2 ingress, and do not restore the retired live CLI child-lane model.

## Upstream Freshness Check

Use this operator sequence before deciding whether the V2 release lane needs an update:

```bash
git fetch https://github.com/devstom/STOM.git refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
git show refs/remotes/devstom_tmp/tags/V2.0:_update.txt | head -5
python scripts/verify_release_sync.py
```

The `git fetch` command refreshes a temporary ref from the authoritative GitHub upstream. Inspect `_update.txt` from the fetched V2 terminal tag to confirm the `2026-04-08 V2.79` marker before starting propagation.

## Release Preflight

Before release propagation, policy verification, or handoff, run:

```bash
python scripts/verify_release_sync.py
```

If you are validating an isolated checkout root, use:

```bash
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-upsync
```

Expect `release sync preflight passed` before claiming the lane is clean. If `STOM_V.wt-dev/` is still on a preparation feature branch, prepare a clean `STOM_Version_2U_C` work location before actual V2.78/V2.79 propagation.

## Protected Paths

- `backtest/graph/` is protected result data.
- It is not a git-propagated source path.
- Do not treat result files there as release-overlay inputs.

## Operator Rules

- Keep docs, scripts, tests, CLI-only surfaces, and research-only surfaces out of release overlays unless the task explicitly targets them.
- Keep this guide aligned with `docs/WORKTREE_STRATEGY.md` and `docs/UPSTREAM_SYNC_STRATEGY.md`.

## V3U Test Automation Gate

V3U lane(`STOM_V.wt-3u/`)은 V3 official(`STOM_V.wt-3/`) 흡수 시 자동 검증 게이트를 통과해야 lane이 clean으로 판정된다. 본 게이트는 pyd 추론 회귀를 자동 감지하고 V3 official source 0줄 수정 invariant를 보장한다.

### 단일 명령 통합 게이트

```bash
python scripts/verify_v3u_pyd_gui_contract.py \
    --branch STOM_Version_3U --version <V3.X> \
    --upstream-ref STOM_Version_3 \
    --manifest .omx/logs/v3u/verify_<date>.json
```

이 호출은 정적 + 구조 + 동적 5단계를 통합 실행한다 (`docs/V3U_PYD_REMOVAL_PLAN.md` §11 참조).

### V3 흡수 시 작업 순서

1. `git merge STOM_Version_3` → `STOM_Version_3U`
2. 위 통합 게이트 실행
3. PASS → 감사 증적 1개를 `docs/update_log/`에 한글 commit
4. FAIL → `ui/main_window.py` 또는 `tests/v3u/`에서만 수정 (V3 official source 절대 수정 금지)

### 허용 diff 경계

V3U lane이 V3 lane과 가질 수 있는 차이는 `docs/CARRY_FORWARD_REGISTRY.md`의 "V3U custom allowlist rule"에 명문화돼 있다. 위반 시 통합 게이트가 자동 fail한다.

### 자동화 한계

다음은 본질적 자동화 불가이며 release 전 사용자 직접 검증이 필수다.

- 실거래 (LS/바이낸스/업비트): 자격증명·실 자금
- 사용자 실 DB 마이그레이션: 사용자 환경 고유 schema drift
- `STOM_Version_3U_C` 생성 시점: 정책 판단

상세는 `docs/V3U_TEST_AUTOMATION_GUIDE.md` 참조.

### 한글 커밋 규칙 reaffirm

자동 검증 시스템에 추가되는 모든 커밋도 본 문서 "Commit Language Rules"를 따른다.

### 결함 발견·수정 4단계 워크플로우

V3U 결함이 발견되면 다음 4단계를 반드시 수행한다 (`docs/V3U_INFERENCE_LESSONS.md` §8.1).

1. 발견·진단 (사용자 보고 또는 자동 검증 fail)
2. V3U 전용 파일에서만 수정 (V3 official source 0줄 수정 invariant 유지)
3. 회귀 테스트 추가 (`tests/v3u/`)
4. `docs/V3U_INFERENCE_LESSONS.md` §6에 결함 기록 + §7 통계 갱신 + 패턴 반복 시 §5 재발 방지 액션 갱신

본 문서는 lane 종료 시까지 누적 갱신되는 진실 원천이다. 빠뜨리면 lessons learned가 휘발된다.
