# STOM Worktree Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-30
- Scope: active STOM release and downstream worktrees

## Current Active State

```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
```

- `STOM_V.wt-dev/` is the sole active checkout location for `STOM_Version_2U_C`.
- `STOM_V.wt-2uc/` is retained as an archive/history/transition checkout on `integration/adopt-cli-v267-into-2uc`.
- `research/init` is excluded from the current official propagation chain.
- Do not describe `wt-2uc` as an active canonical lane or restore the retired live CLI child-lane model.

```text
V2 -> 2U -> 2U_C
```

## Role Of Each Worktree

- `STOM_V/`: official ingress lane only. Release updates enter here first.
- `STOM_V.wt-2u/`: translate approved V2 updates into the maintained py-source lane.
- `STOM_V.wt-2uc/`: archive/history/transition lane that preserves promotion evidence and execution logs.
- `STOM_V.wt-dev/`: active single-baseline lane for `STOM_Version_2U_C`.

## Branch Parity Invariants

- `STOM_Version_2` / `*_2` is the official upstream update reflection lane. It keeps official files, including upstream `.pyd` files.
- `STOM_Version_2U` is the pyd-to-py inference lane. All non-pyd official runtime files should match `STOM_Version_2`; pyd inference defects should be fixed in inferred `.py`, MainWindow wrapper, process wrapper, or verification-contract boundaries.
- `STOM_Version_2U_C` is the custom update lane derived from 2U. Custom edits may be made in this lane, but each runtime difference from 2U must be documented in the carry-forward/update log allowlist before it is treated as intentional.
- Verification order:
  1. `2U` vs `V2`: only pyd-to-py inference differences are expected.
  2. `2U_C` vs `2U`: only documented custom differences are expected.

## Protection Rules

- Official updates enter only through `STOM_Version_2`.
- `backtest/graph/` is a protected result-data path, not a git-propagated source path.
- Docs, scripts, tests, CLI-only surfaces, and research-only surfaces stay out of release overlays unless a task explicitly targets them.
- Before actual V2.78/V2.79 propagation into `2U_C`, use a clean `STOM_Version_2U_C` work location. If `wt-dev` remains on a preparation feature branch, switch/use a clean checkout or create a temporary clean worktree for `STOM_Version_2U_C`.
- Do not check out `STOM_Version_2U_C` in `wt-2uc` while `wt-dev` is the active baseline holder.

Before release work or propagation verification, run:

```bash
python scripts/verify_release_sync.py
```

## V3 Lane Branch Parity Invariants

V3 lane은 V2 lane과 별도 운영되며, V2.79 웨이브에서는 정규 propagation 대상이 아니다 (`docs/V3_UPDATE_OPERATING_SYSTEM.md` 참조). 그러나 V3 lane도 `STOM_Version_2/2U/2U_C`와 동일 패턴의 parity invariants를 가진다.

- `STOM_Version_3` is the V3 official upstream reflection lane. V3 공식 파일과 upstream `.pyd`(`ui/main_window.pyd`)을 보존한다.
- `STOM_Version_3U` is the V3 pyd-to-py 추론 lane. V3 official runtime source와 0줄 차이를 유지하며, 차이는 다음에 한정된다.
  - `ui/main_window.py` (pyd 추론 본체, V3U 전용)
  - `scripts/v3u_*.py` (검증 도구 3개)
  - `tests/v3u/**` (자동 GUI 검증 시스템, Phase 1~4 + drift 회귀 차단)
  - `docs/V3U_*` 및 `docs/update_log/*v3u*` (계획·감사·가이드)
  - `requirements-dev.txt`, `pytest.ini` (V3U 전용 dev 의존성)
- `STOM_Version_3U_C` is the V3U 위에 분기된 custom 작업 lane. V3U 안전망을 모두 상속하며 추가 차이는 `docs/CARRY_FORWARD_REGISTRY.md`의 "V3U_C custom allowlist rule"에 명시된 카테고리에 한정된다.
  - 허용 차이: `docs/V3U_C_*.md`, `scripts/v3uc_*.py`, `tests/v3uc/**`, 3U_C 전용 신규 worker·helper
  - 금지: V3 official source 수정, V3U 안전망 임의 수정

### V3 Verification Order (3단계)

1. `3U vs 3`: pyd 제거 + V3U 전용 추론/검증/문서 차이만 기대.
2. `3U_C vs 3U`: V3U_C custom 차이가 carry-forward registry의 허용 카테고리에 모두 등록되어야 한다.
3. `3U_C vs 3`: 1·2 합집합 — V3 official 0줄 + V3U 안전망 + V3U_C custom.

### V3 Verification Order

1. `3U` vs `3`: pyd 제거 + V3U 전용 추론/검증/문서 차이만 기대.
2. `3U_C` vs `3U`: 향후 생성 시 custom 차이가 `docs/CARRY_FORWARD_REGISTRY.md`의 V3U custom allowlist에 등록되어야 한다.

### V3 Worktree Roles

- `STOM_V.wt-3/`: V3 공식 보관 (V2.79 웨이브 제외 정책상 흡수 일시 정지).
- `STOM_V.wt-3u/`: V3 pyd-free 추론 + 자동 검증 시스템 활성 lane.
- `STOM_V.wt-3uc/`: V3U_C custom 작업 활성 lane (3U_C 생성 후).

### V3 Verification Gate

V3 official 흡수 또는 V3U lane 정합성 점검 시 다음 한 번이 통합 게이트가 된다.

```bash
python scripts/verify_v3u_pyd_gui_contract.py \
    --branch STOM_Version_3U --version <V3.X> \
    --upstream-ref STOM_Version_3 \
    --manifest .omx/logs/v3u/verify_<date>.json
```

이 호출은 정적(pyd evidence, AST, imports) + 구조(contract manifest, smoke) + 동적(`pytest tests/v3u/`) 5단계를 통합 실행한다. PASS = V3.X 흡수 안전. FAIL = `ui/main_window.py` 또는 `tests/v3u/`에서만 수정한다 (V3 official source는 절대 수정 금지).
