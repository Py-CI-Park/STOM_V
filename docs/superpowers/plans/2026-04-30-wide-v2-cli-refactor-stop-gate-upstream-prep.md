# Wide v2 CLI Refactor Stop Gate and 2U_C Upstream Prep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document the CLI refactor stop gate, lock the 2U_C upstream-update preflight checklist, create a Korean PR report, merge the documentation checkpoint, and prepare the next upstream sync branch.

**Architecture:** This is a documentation and verification checkpoint, not a code refactor. It records that PR #30 and PR #31 reduced the highest-risk research CLI collision surface, classifies remaining command families as backlog/hold, and defines the exact checks to run before any 2U-to-2U_C upstream cherry-pick work.

**Tech Stack:** Markdown, Git, GitHub CLI, pytest, PowerShell, STOM CLI repository.

---

## Current Refactoring Flow

This plan continues the flow that starts from `e4981a143b9e75c725f48b77b69147245b10f499`.

```text
[completed] 1. e4981a14
Wide v2 development closeout and CLI refactor prep

[completed] 2. PR #30 / 4f900fea
research_loop.py helper split

[completed] 3. PR #31 / fe55be1f
subcommands.py research/optimize-wide-v2 wiring split

[completed] 4. 3ff35732
remaining command-family refactor need and upstream-prep design

[current] 5. stop gate and upstream-prep implementation plan
this plan

[next] 6. stop gate and upstream-prep documentation PR
create docs, verify, PR, merge

[later] 7. feature/2uc-upstream-sync-prep
inspect actual 2U -> 2U_C upstream diff and choose cherry-picks

[final] 8. resume condition auto-improvement loop development
return to profit-improvement logic only after sync risk is understood
```

## Scope

In scope:

- Create `docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md`.
- Create `docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md`.
- Create `docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md`.
- Record PR #30 and PR #31 as completed refactor checkpoints.
- Classify remaining command families as `완료`, `backlog`, or `보류`.
- Record minimum and full verification command sets for upstream prep.
- Verify focused CLI/research/WFO/runtime-preflight tests.
- Create PR, merge into `STOM_Version_2U_C`, run full baseline verification.
- Create next branch `feature/2uc-upstream-sync-prep`.

Out of scope:

- Do not move WFO code.
- Do not move runtime-preflight code.
- Do not split additional command families.
- Do not cherry-pick upstream changes in this PR.
- Do not change condition generation, ranking, optimizer, WFO/OOS, or backtest behavior.
- Do not run full backtests or WFO/OOS reruns.
- Do not commit `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, or `utility/strategy.db`.

## File Structure

Create:

- `docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md`
  - Records why refactoring stops after PR #30/#31.
  - Shows command-family classification.
  - Defines what would reopen WFO/runtime-preflight refactoring.

- `docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md`
  - Defines upstream update prep sequence.
  - Lists protected custom areas.
  - Lists exact diff and test commands.
  - Defines next branch and constraints.

- `docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md`
  - Korean PR report for this documentation checkpoint.

Modify:

- No existing source code files.
- No existing tests.

Test:

- `tests/unit/test_subcommands.py`
- `tests/unit/test_research_command_wiring.py`
- `tests/unit/test_research_loop.py`
- `tests/unit/test_wfo.py`
- `tests/unit/test_runtime_preflight.py`
- `scripts/verify_nonrelease_sync.py`
- `git diff --check --ignore-cr-at-eol HEAD`

---

### Task 1: Baseline Verification

**Files:**
- Read only.

- [ ] **Step 1: Confirm branch and protected untracked data**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## feature/cli-command-family-refactor-review
?? backtest/graph/
```

- [ ] **Step 2: Run minimum focused verification**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 3: Run nonrelease guardrail verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

### Task 2: Write CLI Refactor Stop Gate Document

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md`

- [ ] **Step 1: Create stop gate document**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md
+# Wide v2 CLI 리팩터링 Stop Gate
+
+## 목적
+
+이 문서는 `e4981a143b9e75c725f48b77b69147245b10f499` 이후 진행한 CLI 리팩터링을 어디서 멈출지 고정한다.
+
+목표는 리팩터링을 계속 늘리는 것이 아니라, 조건식 자동 개선 후속 개발과 2U 정규 업스트림 업데이트 준비로 넘어갈 수 있는 기준을 만드는 것이다.
+
+## 현재까지 완료한 리팩터링
+
+```text
+[완료] e4981a14
+Wide v2 개발 정리 + CLI 리팩터링 준비
+
+[완료] PR #30 / 4f900fea
+research_loop.py helper 책임 분리
+- cli/research_ranking.py
+- cli/research_cleanup.py
+- cli/research_runtime_metadata.py
+
+[완료] PR #31 / fe55be1f
+subcommands.py research/optimize-wide-v2 wiring 분리
+- cli/commands/research.py
+- tests/unit/test_research_command_wiring.py
+```
+
+## Stop Gate 결론
+
+현재 단계에서는 추가 command family 코드 이동을 진행하지 않는다.
+
+```text
+계속 리팩터링
+  -> WFO 분리
+  -> runtime-preflight 분리
+  -> discovery 전체 분리
+  -> 조건식 자동 개선 재개 지연
+
+현재 선택
+  -> PR #30/#31에서 큰 research 충돌 면적 축소 완료
+  -> 나머지 command family는 backlog로 분류
+  -> 업스트림 업데이트 준비로 이동
+  -> 이후 실제 diff를 보고 필요한 리팩터링만 재개
+```
+
+## Command Family 판단
+
+| 영역 | 상태 | 판단 |
+| --- | --- | --- |
+| `research_loop.py` helper | 완료 | PR #30에서 ranking, cleanup, runtime metadata 분리 완료 |
+| `discovery research` | 완료 | PR #31에서 `cli/commands/research.py`로 이동 |
+| `discovery optimize-wide-v2` | 완료 | PR #31에서 `cli/commands/research.py`로 이동 |
+| `wfo` | backlog | 후속 검증 수단이며 지금 즉시 분리하지 않음 |
+| `runtime-preflight` | backlog | 핵심 로직은 이미 `cli/runtime_preflight.py`에 있고 wiring만 남아 있음 |
+| `discovery promote/auto/evolve` | backlog | discovery 전체 분리는 범위가 커서 실제 upstream diff 확인 후 결정 |
+| `formula`, `strategy`, `db`, `setting`, `report`, `tune` | 보류 | 조건식 자동 개선 핵심 경로와 직접 관련 낮음 |
+| `optimize`, `sweep` | 보류 | 별도 CLI 기능이며 현재 우선순위 낮음 |
+
+## 다시 리팩터링을 여는 조건
+
+다음 중 하나가 발생하면 WFO/runtime-preflight/discovery family 분리를 다시 검토한다.
+
+1. 2U 업스트림 업데이트 중 `cli/subcommands.py`에서 실제 충돌이 크게 발생한다.
+2. 조건식 자동 개선 후속 개발이 WFO/runtime-preflight CLI 옵션을 반복적으로 수정해야 한다.
+3. `tests/unit/test_subcommands.py` 변경이 과도해져 command family별 직접 테스트가 필요해진다.
+4. 새 조건식 개선 기능이 discovery command family 전체를 다시 넓게 수정해야 한다.
+
+## 다음 단계
+
+```text
+1. 2U_C 업스트림 sync preflight 문서 작성
+2. stop gate 문서와 preflight 문서를 PR로 병합
+3. feature/2uc-upstream-sync-prep 브랜치 생성
+4. 실제 2U -> 2U_C diff 확인
+5. cherry-pick 또는 보류 판단
+6. 조건식 자동 개선 후속 개발 재개
+```
*** End Patch
```

- [ ] **Step 2: Verify stop gate document key lines**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-30_wide_v2_cli_refactor_stop_gate.md -Pattern "Stop Gate 결론|PR #30|PR #31|Command Family 판단|다시 리팩터링을 여는 조건|feature/2uc-upstream-sync-prep"
```

Expected:

```text
Each listed pattern appears at least once.
```

### Task 3: Write 2U_C Upstream Sync Preflight Document

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md`

- [ ] **Step 1: Create upstream preflight document**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md
+# 2U_C 업스트림 업데이트 Preflight
+
+## 목적
+
+이 문서는 `STOM_Version_2U` 최신 코드와 `STOM_Version_2U_C` 커스텀 baseline을 비교하기 전에 실행할 preflight checklist다.
+
+업스트림 업데이트는 overlay merge가 아니라 cherry-pick 또는 파일 단위 검토로 진행한다. 이유는 `2U_C`에 CLI/조건식 개선 커스텀이 포함되어 있고, 이를 덮어쓰면 지금까지 만든 백테스트 반복 개선 경로가 손상될 수 있기 때문이다.
+
+## 현재 기준
+
+```text
+STOM_Version_2U
+-> upstream 2U baseline
+
+STOM_Version_2U_C
+-> 2U 기반 CLI/조건식 개선 custom baseline
+
+현재 2U_C 기준 merge:
+fe55be1f30cb540f0628678024fa41481be82551
+```
+
+## 보호 대상
+
+업스트림 업데이트 시 다음 영역은 먼저 보호 대상으로 본다.
+
+```text
+cli/
+stom_backtest.py
+tests/unit/test_research_*
+tests/unit/test_research_command_wiring.py
+tests/unit/test_wfo*
+tests/unit/test_runtime_preflight.py
+tests/unit/test_strategy_generator.py
+tests/unit/test_strategy_loader.py
+docs/research/condition_research/
+docs/superpowers/
+docs/pr/*wide*
+utility/ai_agent/WideV1Final_B_20260425.py
+utility/ai_agent/WideV2Final_B_20260428.py
+```
+
+## 업스트림 업데이트 전 확인 명령
+
+### 1. 현재 상태 확인
+
+```powershell
+git status --short --branch
+git log --oneline --decorate -8
+```
+
+예상:
+
+```text
+현재 브랜치는 feature/2uc-upstream-sync-prep 또는 그 준비 브랜치여야 한다.
+backtest/graph/ 외 의도하지 않은 변경이 없어야 한다.
+```
+
+### 2. 2U 대비 2U_C 커스텀 diff 확인
+
+```powershell
+git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli stom_backtest.py tests/unit docs/research docs/superpowers docs/pr utility/ai_agent
+```
+
+확인 포인트:
+
+```text
+cli/subcommands.py
+cli/commands/research.py
+cli/research_loop.py
+cli/research_ranking.py
+cli/research_cleanup.py
+cli/research_runtime_metadata.py
+cli/research_optimizer.py
+cli/research_optimizer_report.py
+cli/research_runtime_output.py
+cli/research_iteration_v2.py~v5*.py
+tests/unit/test_research_*
+tests/unit/test_subcommands.py
+tests/unit/test_research_command_wiring.py
+```
+
+### 3. 최소 검증
+
+시간을 줄여야 할 때는 다음을 먼저 실행한다.
+
+```powershell
+python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+### 4. 전체 검증
+
+업스트림 반영 PR merge 전에는 다음을 실행한다.
+
+```powershell
+python -m pytest tests/unit/ -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+## 반영 원칙
+
+```text
+1. STOM_Version_2U_C에 직접 커밋하지 않는다.
+2. feature/2uc-upstream-sync-prep 브랜치에서만 작업한다.
+3. upstream 변경은 cherry-pick 또는 파일 단위 검토로 반영한다.
+4. cli/와 stom_backtest.py는 덮어쓰기 금지다.
+5. 충돌이 발생하면 먼저 충돌 파일과 커스텀 기능을 문서화한다.
+6. 테스트가 통과하기 전에는 PR merge를 하지 않는다.
+```
+
+## 다음 브랜치
+
+```text
+feature/2uc-upstream-sync-prep
+```
+
+## 다음 추천 명령
+
+```text
+$brainstorming 2U_C 업스트림 업데이트 diff 분석 및 cherry-pick 준비
+```
*** End Patch
```

- [ ] **Step 2: Verify upstream preflight document key lines**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-30_2uc_upstream_sync_preflight.md -Pattern "STOM_Version_2U|STOM_Version_2U_C|fe55be1f|보호 대상|최소 검증|전체 검증|feature/2uc-upstream-sync-prep|cherry-pick"
```

Expected:

```text
Each listed pattern appears at least once.
```

### Task 4: Write Korean PR Report

**Files:**
- Create: `docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md`

- [ ] **Step 1: Create PR report**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md
+# Wide v2 CLI 리팩터링 Stop Gate 및 2U_C 업스트림 준비
+
+## 목적
+
+이번 PR은 코드 변경 없이 Wide v2 CLI 리팩터링을 어디서 멈출지 정하고, 다음 `2U_C` 업스트림 업데이트 준비 순서를 문서로 고정하는 documentation checkpoint입니다.
+
+PR #30과 PR #31을 통해 조건식 자동 개선에서 가장 자주 변경되던 research 경계는 이미 줄였습니다. 따라서 지금은 WFO/runtime-preflight 등 남은 command family를 계속 분리하기보다, 실제 2U 업스트림 diff를 보기 위한 준비 단계로 넘어갑니다.
+
+## 전체 단계
+
+```text
+[완료] e4981a14
+Wide v2 개발 정리 + CLI 리팩터링 준비
+
+[완료] PR #30
+research_loop.py helper 책임 분리
+
+[완료] PR #31
+subcommands.py research/optimize-wide-v2 wiring 분리
+
+[이번 PR]
+CLI 리팩터링 stop gate + 2U_C 업스트림 sync preflight
+
+[다음]
+feature/2uc-upstream-sync-prep 에서 실제 diff 분석
+
+[최종]
+조건식 자동 개선 루프 후속 개발 재개
+```
+
+## 이번 PR에서 기록한 내용
+
+- 추가 command family 리팩터링은 현재 보류
+- WFO/runtime-preflight/discovery 나머지는 backlog로 분류
+- `cli/subcommands.py`는 아직 크지만 research 충돌 면적은 PR #31에서 축소 완료
+- 업스트림 업데이트 전 보호해야 할 CLI/조건식 개선 파일 목록 정리
+- 최소 검증과 전체 검증 명령 고정
+- 다음 브랜치 `feature/2uc-upstream-sync-prep` 고정
+
+## 추가된 문서
+
+- `docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md`
+- `docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md`
+- `docs/superpowers/specs/2026-04-30-wide-v2-cli-command-family-refactor-and-upstream-prep-design.md`
+- `docs/superpowers/plans/2026-04-30-wide-v2-cli-refactor-stop-gate-upstream-prep.md`
+
+## 검증
+
+```powershell
+python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+merge 후 기준 브랜치 검증:
+
+```powershell
+python -m pytest tests/unit/ -q
+python scripts/verify_nonrelease_sync.py
+```
+
+## 하지 않은 일
+
+- WFO/runtime-preflight 코드 이동
+- 조건식 후보 생성 v6/v7 추가
+- 수익률 목적함수 추가
+- full backtest 또는 WFO/OOS 재실행
+- upstream cherry-pick
+- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db` 변경
+
+## Merge 후 다음 추천 명령
+
+```text
+$brainstorming 2U_C 업스트림 업데이트 diff 분석 및 cherry-pick 준비
+```
*** End Patch
```

- [ ] **Step 2: Verify PR report key lines**

Run:

```powershell
Select-String -Path docs\pr\2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md -Pattern "documentation checkpoint|PR #30|PR #31|feature/2uc-upstream-sync-prep|최소 검증|전체 검증|cherry-pick"
```

Expected:

```text
Each listed pattern appears at least once.
```

### Task 5: Focused Documentation Verification

**Files:**
- Read only.

- [ ] **Step 1: Run minimum focused tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run nonrelease sync guardrail**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 3: Run diff check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
Command exits 0.
```

### Task 6: Commit Documentation Checkpoint

**Files:**
- Stage only intended files.

- [ ] **Step 1: Confirm status**

Run:

```powershell
git status --short --branch
```

Expected changed/untracked paths:

```text
?? backtest/graph/
?? docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md
?? docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md
?? docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md
```

- [ ] **Step 2: Stage explicit files**

Run:

```powershell
git add docs/research/condition_research/mvp/2026-04-30_wide_v2_cli_refactor_stop_gate.md
git add docs/research/condition_research/mvp/2026-04-30_2uc_upstream_sync_preflight.md
git add docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md
```

- [ ] **Step 3: Confirm staged diff**

Run:

```powershell
git diff --cached --stat
git diff --cached --check --ignore-cr-at-eol
```

Expected:

```text
Only the three intended documentation files are staged.
Diff check exits 0.
```

- [ ] **Step 4: Commit with Korean Lore message**

Run:

```powershell
git commit -m "Wide v2 리팩터링 중단 기준과 업스트림 준비 문서를 고정한다" -m "PR #30과 PR #31 이후 research 중심 충돌 면적은 줄었다고 판단하고, 남은 command family 분리는 backlog로 돌렸다. 다음 단계에서 실제 2U 업스트림 diff를 보기 전에 stop gate, 보호 파일, 최소/전체 검증 명령, feature/2uc-upstream-sync-prep 흐름을 문서로 고정한다." -m "Constraint: 조건식 자동 개선 후속 개발을 더 지연시키지 않기 위해 리팩터링을 무기한 계속하지 않는다" -m "Rejected: WFO/runtime-preflight 즉시 분리 | 실제 업스트림 diff를 보기 전에는 추가 PR 비용이 더 크다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Directive: 업스트림 sync 전에는 보호 대상 목록과 최소 검증 명령을 먼저 확인할 것" -m "Tested: python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_command_wiring.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q; python scripts/verify_nonrelease_sync.py; git diff --check --ignore-cr-at-eol HEAD" -m "Not-tested: full backtest; WFO/OOS rerun; upstream cherry-pick"
```

### Task 7: Push, Create PR, Merge, and Prepare Next Branch

**Files:**
- No edits expected.

- [ ] **Step 1: Push feature branch**

Run:

```powershell
git push -u origin feature/cli-command-family-refactor-review
```

Expected:

```text
Branch pushed to origin.
```

- [ ] **Step 2: Create GitHub PR**

Run:

```powershell
gh pr create --base STOM_Version_2U_C --head feature/cli-command-family-refactor-review --title "Wide v2 CLI 리팩터링 Stop Gate 및 2U_C 업스트림 준비" --body-file docs/pr/2026-04-30_wide_v2_cli_refactor_stop_gate_and_upstream_prep_pr.md
```

Expected:

```text
GitHub PR URL is printed.
```

- [ ] **Step 3: Merge PR and delete remote branch**

Run:

```powershell
gh pr merge <PR_NUMBER> --merge --delete-branch
```

Expected:

```text
PR merged into STOM_Version_2U_C.
```

- [ ] **Step 4: Verify merged baseline**

Run:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
All unit tests pass.
All nonrelease sync guardrails pass.
```

- [ ] **Step 5: Create next upstream prep branch**

Run:

```powershell
git switch -c feature/2uc-upstream-sync-prep
```

Expected:

```text
Switched to a new branch 'feature/2uc-upstream-sync-prep'
```

## Handoff Summary

After this plan is executed, report:

- PR URL and merge commit.
- Changed files.
- Focused verification commands and pass counts.
- Merged baseline verification commands and pass counts.
- Whether `backtest/graph/` remained untracked and untouched.
- Current branch.
- Next recommended command:

```text
$brainstorming 2U_C 업스트림 업데이트 diff 분석 및 cherry-pick 준비
```
