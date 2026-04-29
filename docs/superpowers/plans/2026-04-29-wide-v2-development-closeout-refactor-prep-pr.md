# Wide v2 Development Closeout And Refactor Prep PR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a documentation-only PR that closes out the current Wide v1/v2 condition-improvement development phase, records its limits, inventories 2U_C customizations versus 2U, and prepares the next CLI refactor and upstream-update workflow.

**Architecture:** This plan does not change application code. It creates four Korean Markdown documents that separate closeout, refactor preparation, custom inventory, and PR/merge narrative, then verifies and merges them through the established feature-branch PR routine.

**Tech Stack:** Markdown, PowerShell, Git, GitHub CLI `gh`, pytest, existing STOM verification script.

---

## Current State

- Current branch: `feature/wide-v2-development-closeout-refactor-prep`
- Base branch: `STOM_Version_2U_C`
- Latest base commit before this plan: `4dfc8095 Wide v2 MVP freeze 및 PR 병합 보고서`
- Design commit already present on this branch: `ec7d182e Wide v2 개발 정리와 리팩토링 준비 설계를 고정한다`
- Existing untracked protected data: `backtest/graph/`
- Do not stage or commit `backtest/graph/`.

## Scope

In scope:

- Record that Wide v2 built the pipeline but did not yet meet the user's final condition-profit improvement goal.
- Record Wide v1 to Wide v2 WFO/OOS performance deltas.
- Record latest PR flow from PR #17 through PR #28.
- Record `STOM_Version_2U` to `STOM_Version_2U_C` custom inventory.
- Record CLI refactor preparation order and protected custom areas.
- Create a Korean PR body for merge into `STOM_Version_2U_C`.
- Verify docs and focused research CLI tests.
- Create PR, merge PR, fast-forward local `STOM_Version_2U_C`, and create the next refactor-plan branch.

Out of scope:

- No code refactor.
- No profit-objective implementation.
- No v6/v7 candidate generation.
- No WFO/OOS rerun.
- No full backtest rerun.
- No live trading, paper trading, or operational pilot.
- No commit of `utility/strategy.db`.
- No commit of raw runtime outputs under `backtest/graph/`, `backtest/temp/`, or `backtest/csv/`.

## Files

Create:

- `docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md`
- `docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md`
- `docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md`
- `docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md`

Already created by brainstorming and stageable in this PR:

- `docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md`

Created by this writing-plans step and stageable in this PR:

- `docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md`

Do not modify:

- `cli/`
- `stom_backtest.py`
- `tests/unit/`
- `utility/strategy.db`
- `backtest/graph/`
- `backtest/temp/`
- `backtest/csv/`

---

### Task 1: Verify Branch And Source Evidence

**Files:**
- Read: `docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`

- [ ] **Step 1: Confirm branch and untracked state**

Run:

```powershell
git status --short --branch
```

Expected output contains:

```text
## feature/wide-v2-development-closeout-refactor-prep
?? backtest/graph/
```

- [ ] **Step 2: Confirm branch is based on `STOM_Version_2U_C`**

Run:

```powershell
git merge-base --is-ancestor STOM_Version_2U_C HEAD
if ($LASTEXITCODE -eq 0) { "base_is_ancestor=True" } else { "base_is_ancestor=False"; exit 1 }
```

Expected:

```text
base_is_ancestor=True
```

- [ ] **Step 3: Confirm 2U to 2U_C custom file counts**

Run:

```powershell
$all = git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli tests/unit docs/pr docs/research docs/superpowers utility/ai_agent stom_backtest.py | Measure-Object
$cli = git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli | Measure-Object
$tests = git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- tests/unit | Measure-Object
$docs = git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- docs | Measure-Object
"all=$($all.Count)"
"cli=$($cli.Count)"
"tests=$($tests.Count)"
"docs=$($docs.Count)"
```

Expected:

```text
all=340
cli=55
tests=84
docs=234
```

- [ ] **Step 4: Confirm Wide v1 to Wide v2 WFO/OOS comparison values**

Run:

```powershell
@'
import json
from pathlib import Path

def metrics(round_obj):
    if "test_result" in round_obj:
        return round_obj["test_result"]["metrics"]
    if "test_metrics" in round_obj:
        return round_obj["test_metrics"]
    return {}

def summarize(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rounds = data.get("rounds") or []
    values = [metrics(item) for item in rounds]
    def avg(key):
        return sum(item.get(key, 0.0) for item in values) / len(values)
    def total(key):
        return sum(item.get(key, 0.0) for item in values)
    summary = data.get("summary") or {}
    return {
        "mean_oos_metric": summary.get("mean_oos_metric"),
        "mean_trade_count": summary.get("mean_trade_count"),
        "avg_profit_pct": avg("avg_profit_pct"),
        "total_profit_pct": avg("total_profit_pct"),
        "total_profit_pct_sum": total("total_profit_pct"),
        "total_profit_krw": avg("total_profit_krw"),
        "total_profit_krw_sum": total("total_profit_krw"),
        "win_rate": avg("win_rate"),
        "mdd_pct": avg("mdd_pct"),
    }

v1 = summarize(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json")
v2 = summarize(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json")
print(f"v1_total_profit_pct={v1['total_profit_pct']:.5f}")
print(f"v2_total_profit_pct={v2['total_profit_pct']:.5f}")
print(f"delta_total_profit_pct={v2['total_profit_pct'] - v1['total_profit_pct']:.5f}")
print(f"delta_total_profit_krw_sum={v2['total_profit_krw_sum'] - v1['total_profit_krw_sum']:.0f}")
'@ | python -
```

Expected:

```text
v1_total_profit_pct=-53.20000
v2_total_profit_pct=-52.05875
delta_total_profit_pct=1.14125
delta_total_profit_krw_sum=106317169
```

### Task 2: Create Wide v2 Development Closeout Document

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md`

- [ ] **Step 1: Create closeout document**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md
+# Wide v2 개발 정리
+
+## 결론
+
+Wide v2는 조건식 개선을 위한 CLI 실행 파이프라인을 만들었지만, 수익률 개선 목표는 아직 완료하지 못했다.
+
+따라서 지금 단계의 판단은 다음과 같다.
+
+```text
+조건식 개선 개발 성과 정리
+-> 부족한 부분과 추후 재개 지점 문서화
+-> 리팩토링 준비
+-> 정규 업스트림 업데이트 준비
+```
+
+이번 문서는 성과를 폐기하기 위한 문서가 아니다. 추후 다시 조건식 개선을 이어갈 수 있도록 현재 상태, 한계, 재개 지점을 고정하는 문서다.
+
+## 지금까지 만든 것
+
+Wide v1/Wide v2 개발로 다음 기반을 만들었다.
+
+- CLI 기반 백테스트 실행 경로
+- 조건식 후보 생성 경로
+- 후보별 백테스트 실행 경로
+- 후보별 결과 기록과 Markdown 보고서
+- retention-aware 후보 선택
+- row-level 후보 차이 분석
+- score baseline 비교
+- v3/v4/v5 후보 생성과 actual row-set 선택
+- runtime checkpoint와 실패 복구
+- Wide v2 반복 개선 optimizer
+- v5 후보 부족 recovery
+- WFO/OOS 검증 경로
+- PR 기반 merge 루틴
+
+## 최근 PR 흐름
+
+```text
+PR #17 CLI child DB override와 BackTest timeout protocol 보강
+-> PR #18 Wide v1 CLI baseline과 후보 5개 실행 검증
+-> PR #19 Wide v1 반복 개선 루프 v2 실행 검증
+-> PR #20 Wide v1 row-level 후보 차이 분석
+-> PR #21 Wide v1 score 기준선 비교 보강
+-> PR #22 Wide v1 v3 후보 생성 규칙 구현과 실행 결과 기록
+-> PR #23 Wide v1 v3 결과 분석 및 v4 여부 판단
+-> PR #24 Wide v1 MVP freeze 및 운영 재현 문서화
+-> PR #25 Wide v1 post-MVP risk backlog 및 향후 조건식 개선 로드맵
+-> PR #26 Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 구현
+-> PR #27 Wide v2 smoke/full run 검증 계획
+-> PR #28 Wide v2 MVP freeze 및 PR 병합 보고서
+```
+
+## 수익률 관점 성과
+
+Wide v2는 Wide v1보다 손실을 조금 줄였지만, 아직 수익 전략은 아니다.
+
+| 항목 | Wide v1 | Wide v2 | 변화 |
+| --- | ---: | ---: | ---: |
+| 평균 OOS metric `tpi` | `0.57625` | `0.57250` | `-0.00375` |
+| 평균 거래 수 | `2131.75` | `2045.125` | `-86.625` |
+| 평균 거래당 수익률 | `-0.62375%` | `-0.61875%` | `+0.005%p` |
+| 평균 총수익률 | `-53.20%` | `-52.05875%` | `+1.14125%p` |
+| 8라운드 합산 총수익률 | `-425.60%` | `-416.47%` | `+9.13%p` |
+| 8라운드 합산 손익금 | `-2,110,984,765원` | `-2,004,667,596원` | `+106,317,169원` |
+| 평균 승률 | `29.03125%` | `29.04%` | `+0.00875%p` |
+| 평균 MDD | `53.22625%` | `52.08625%` | `-1.14%p` |
+
+해석:
+
+- 손실은 줄었지만 개선 폭은 작다.
+- Wide v2 평균 총수익률은 여전히 `-52.05875%`다.
+- 평균 거래당 수익률도 `-0.61875%`로 음수다.
+- 따라서 `WideV2Final_B_20260428`은 수익 나는 최종 조건식이 아니라 추후 개선을 위한 중간 후보로 본다.
+
+## 부족한 부분
+
+현재 부족한 부분은 다음이다.
+
+- 후보 ranking이 수익률 자체보다 `tpi`, retention, row-set 다양성에 더 강하게 맞춰져 있다.
+- 후보별 조건식과 runtime 기록은 개선됐지만, 수익률 개선 원인을 자동으로 설명하는 수준은 아니다.
+- 후보 생성 family가 넓어지면서 코드가 커졌고, `cli/research_loop.py`와 `cli/subcommands.py`가 리팩토링 대상이 됐다.
+- 정규 업스트림 업데이트를 받을 때 CLI 커스텀 영역을 보호할 인벤토리가 필요하다.
+
+## 추후 재개 지점
+
+조건식 개선 개발을 다시 시작할 때는 다음 순서로 재개한다.
+
+```text
+1. CLI 리팩토링으로 구조 정리
+2. 수익률 목적함수 기반 ranking/report 보강
+3. 축소 후보 실행으로 profit score 로그 검증
+4. candidate_count=10 full run 재검증
+5. Wide v1/Wide v2 대비 수익률 개선 여부 판단
+6. 개선이 부족하면 후보 family 확장 설계
+```
+
+## 이번 merge point 의미
+
+이번 merge point는 다음을 의미한다.
+
+- 조건식 개선 파이프라인 개발 기록을 `STOM_Version_2U_C`에 보존한다.
+- 수익률 개선 미완료 상태를 명시한다.
+- 지금은 새 조건식 개발보다 리팩토링과 업스트림 업데이트 준비가 우선임을 고정한다.
+- 추후 다시 조건식 개선을 이어갈 수 있는 기준점을 만든다.
*** End Patch
```

- [ ] **Step 2: Verify closeout document**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-29_wide_v2_development_closeout.md -Pattern "수익률 개선 목표는 아직 완료하지 못했다|PR #28|WideV2Final_B_20260428|평균 총수익률|추후 재개 지점"
```

Expected output contains all five patterns.

### Task 3: Create CLI Refactor Preparation Document

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md`

- [ ] **Step 1: Create refactor preparation document**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md
+# Wide v2 CLI 리팩토링 준비
+
+## 목적
+
+이번 문서는 리팩토링을 바로 수행하기 위한 문서가 아니라, 다음 리팩토링 브랜치에서 무엇을 어떤 순서로 나눌지 고정하는 준비 문서다.
+
+현재 우선순위는 다음이다.
+
+```text
+문서-only closeout PR
+-> 리팩토링 계획 PR
+-> 테스트로 기존 동작 고정
+-> 작은 단위 리팩토링
+-> 정규 업스트림 업데이트 준비
+```
+
+## 리팩토링이 필요한 이유
+
+Wide v1/Wide v2 조건식 개선 기능이 빠르게 확장되면서 CLI 커스텀 코드가 커졌다.
+
+특히 다음 파일이 커졌다.
+
+| 파일 | 크기 | 판단 |
+| --- | ---: | --- |
+| `cli/research_loop.py` | 약 84KB | 후보 생성, 실행, ranking, cleanup, report 책임이 섞여 있음 |
+| `cli/subcommands.py` | 약 81KB | parser, validation, handler 연결 책임이 커짐 |
+| `cli/ai_controller.py` | 약 49KB | optimizer/history/controller 책임이 넓음 |
+| `cli/auto_discovery.py` | 약 36KB | 자동 탐색과 evolution 흐름이 큼 |
+| `cli/runner.py` | 약 27KB | 백테스트 실행 연결과 프로세스 제어 책임이 큼 |
+| `cli/research_report.py` | 약 24KB | report 생성 책임이 확장됨 |
+| `cli/research_optimizer.py` | 약 24KB | Wide v2 반복 개선 coordinator |
+
+## 리팩토링 원칙
+
+다음 브랜치에서 리팩토링할 때는 이 원칙을 지킨다.
+
+```text
+1. 기존 동작을 테스트로 먼저 고정한다.
+2. 기능을 삭제하지 않는다.
+3. 파일 분리는 동작 변경 없이 한다.
+4. CLI command contract를 유지한다.
+5. raw runtime output은 계속 커밋하지 않는다.
+6. 한 PR에서 한 책임만 줄인다.
+7. STOM_Version_2U_C에 직접 커밋하지 않는다.
+```
+
+## 우선 분리 대상
+
+### 1. `cli/subcommands.py`
+
+현재 역할:
+
+- CLI parser 구성
+- action dispatch
+- command별 validation
+- research/wfo/runtime-preflight/strategy 관련 handler 연결
+
+분리 후보:
+
+```text
+cli/subcommands.py
+-> cli/commands/research.py
+-> cli/commands/wfo.py
+-> cli/commands/runtime.py
+-> cli/commands/strategy.py
+-> cli/commands/common.py
+```
+
+첫 PR에서는 parser와 handler의 동작을 바꾸지 않고 command family별 함수 이동만 검토한다.
+
+### 2. `cli/research_loop.py`
+
+현재 역할:
+
+- 후보 생성 orchestration
+- 후보 백테스트 실행
+- promotion/ranking
+- retention penalty
+- row-set selection 연결
+- cleanup
+- runtime metadata 정리
+
+분리 후보:
+
+```text
+cli/research_loop.py
+-> cli/research_execution.py
+-> cli/research_ranking.py
+-> cli/research_cleanup.py
+-> cli/research_runtime_metadata.py
+```
+
+첫 PR에서는 ranking 계산과 leaderboard metadata 정리를 분리하는 것이 가장 작다.
+
+### 3. 보고서와 대용량 결과물 관리
+
+현재 `docs/research/condition_research/pilot_logs/`에는 큰 JSON report가 포함되어 있다. 예를 들어 Wide v2 WFO/OOS report는 매우 크다.
+
+다음 원칙을 검토한다.
+
+```text
+1. 커밋 대상은 curated summary와 manifest 중심으로 제한한다.
+2. raw runtime JSON은 backtest/temp 또는 외부 artifact로 둔다.
+3. 이미 커밋된 큰 결과물은 별도 정리 PR에서 유지/압축/요약 여부를 검토한다.
+```
+
+## 리팩토링 전 필수 테스트
+
+다음 리팩토링 계획에서 최소한 이 테스트를 먼저 통과시킨다.
+
+```powershell
+python -m pytest tests/unit/test_subcommands.py -q
+python -m pytest tests/unit/test_research_loop.py -q
+python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+## 다음 리팩토링 브랜치
+
+추천 브랜치:
+
+```text
+feature/cli-research-refactor-plan
+```
+
+추천 명령:
+
+```text
+$brainstorming Wide v2 CLI research 리팩토링 범위와 업스트림 업데이트 보호 설계
+```
+
+그 다음:
+
+```text
+$writing-plans Wide v2 CLI research 리팩토링 1차 구현 계획 작성
+```
*** End Patch
```

- [ ] **Step 2: Verify refactor preparation document**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-29_wide_v2_refactor_prep.md -Pattern "cli/research_loop.py|cli/subcommands.py|기존 동작을 테스트로 먼저 고정|feature/cli-research-refactor-plan|업스트림 업데이트 보호"
```

Expected output contains all five patterns.

### Task 4: Create 2U To 2U_C Custom Inventory

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md`

- [ ] **Step 1: Create custom inventory document**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md
+# 2U to 2U_C custom inventory
+
+## 목적
+
+이 문서는 `STOM_Version_2U` 최신 코드와 `STOM_Version_2U_C`의 차이를 정리해, 이후 정규 업스트림 업데이트를 받을 때 CLI 커스텀 기능을 잃지 않도록 하기 위한 인벤토리다.
+
+## 현재 브랜치 역할
+
+```text
+STOM_Version_2U
+-> upstream 2U baseline
+
+STOM_Version_2U_C
+-> 2U 기반 CLI/조건식 개선 커스텀 baseline
+```
+
+`2U_C`의 CLI 커스텀은 `2U`에 없는 기능이다. 따라서 업스트림 동기화 시 overlay merge로 덮어쓰면 안 된다.
+
+## 파일 수 요약
+
+확인 명령:
+
+```powershell
+git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli tests/unit docs/pr docs/research docs/superpowers utility/ai_agent stom_backtest.py
+```
+
+요약:
+
+| 영역 | 파일 수 |
+| --- | ---: |
+| 주요 커스텀 전체 | `340` |
+| `cli/` | `55` |
+| `tests/unit/` | `84` |
+| `docs/` | `234` |
+
+## 보호 대상
+
+업스트림 업데이트 시 다음 영역은 `2U_C` 커스텀 보호 대상으로 본다.
+
+```text
+cli/
+stom_backtest.py
+tests/unit/test_research_*
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
+## 주요 CLI 커스텀 기능
+
+| 영역 | 대표 파일 | 설명 |
+| --- | --- | --- |
+| CLI 진입점 | `stom_backtest.py` | STOM 백테스트 CLI entry point |
+| command routing | `cli/subcommands.py` | discovery, research, WFO, strategy, runtime-preflight 명령 연결 |
+| 백테스트 실행 | `cli/runner.py` | CLI에서 GUI 백테스트 흐름과 맞춰 실행 |
+| 실행 전 검증 | `cli/runtime_preflight.py` | strategy/db/date/timeframe/engine 사전 점검 |
+| WFO/OOS | `cli/wfo.py` | window 생성과 OOS 검증 |
+| 조건식 생성 | `cli/condition_generator.py`, `cli/research_iteration_v2.py`~`v5.py` | 후보 조건식 생성 |
+| 후보 부족 복구 | `cli/research_iteration_v5_recovery.py` | direct_v4/v5 shortfall recovery |
+| 반복 개선 | `cli/research_optimizer.py` | Wide v2 multi-round coordinator |
+| 결과 기록 | `cli/research_optimizer_report.py`, `cli/research_report.py`, `cli/research_runtime_output.py` | Markdown/JSON evidence |
+| ranking/품질 | `cli/research_promotion.py`, `cli/research_retention.py`, `cli/research_rowdiff.py`, `cli/research_v3_tiebreak.py`, `cli/research_v4_rowset.py` | 후보 비교와 row-set 다양성 |
+
+## 정규 업스트림 업데이트 원칙
+
+업스트림 업데이트는 다음 원칙으로 진행한다.
+
+```text
+1. STOM_Version_2U_C에 직접 덮어쓰지 않는다.
+2. 별도 update branch를 만든다.
+3. upstream 변경은 cherry-pick 또는 파일 단위 검토로 반영한다.
+4. cli/와 stom_backtest.py는 충돌 여부를 먼저 확인한다.
+5. 테스트로 CLI 커스텀 동작을 확인한 뒤 PR merge한다.
+```
+
+추천 branch:
+
+```text
+feature/2uc-upstream-sync-prep
+```
+
+추천 검증:
+
+```powershell
+python -m pytest tests/unit/ -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+시간이 오래 걸릴 때 최소 검증:
+
+```powershell
+python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_loop.py tests/unit/test_wfo.py tests/unit/test_runtime_preflight.py -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+## 커밋하지 않을 것
+
+다음은 로컬 실행 결과 또는 보호 결과물이므로 PR에 포함하지 않는다.
+
+```text
+backtest/graph/
+backtest/temp/
+backtest/csv/
+utility/strategy.db
+```
+
+## 다음 단계
+
+1. 이 인벤토리를 `STOM_Version_2U_C`에 PR로 병합한다.
+2. CLI research 리팩토링 계획을 만든다.
+3. 리팩토링으로 커스텀 경계를 명확히 한다.
+4. 그 다음 정규 업스트림 업데이트 준비 브랜치를 만든다.
*** End Patch
```

- [ ] **Step 2: Verify custom inventory document**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-29_2u_to_2uc_custom_inventory.md -Pattern "주요 커스텀 전체|cli/|STOM_Version_2U_C에 직접 덮어쓰지 않는다|feature/2uc-upstream-sync-prep|backtest/graph"
```

Expected output contains all five patterns.

### Task 5: Create Korean PR Body

**Files:**
- Create: `docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md`

- [ ] **Step 1: Create PR body**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md
+# Wide v2 개발 정리 및 CLI 리팩토링 준비
+
+## 목적
+
+이번 PR은 코드 변경 PR이 아니라 문서-only 정리 PR입니다.
+
+Wide v1/Wide v2 조건식 개선 개발로 CLI 기반 후보 생성, 백테스트, WFO/OOS 검증, PR merge 루틴은 만들었지만, 수익률 개선 성과는 아직 충분하지 않습니다. 따라서 현재 상태를 `STOM_Version_2U_C`에 정리된 merge point로 남기고, 다음 단계에서 CLI 리팩토링과 정규 업스트림 업데이트 준비를 진행하기 위한 기준을 고정합니다.
+
+## 이번 PR의 결론
+
+```text
+조건식 개선 개발을 계속 밀기보다
+-> 지금까지의 성과와 한계를 정리
+-> 2U 대비 2U_C 커스텀 범위를 인벤토리화
+-> CLI/조건식 개선 기능 리팩토링 준비
+-> 이후 정규 업스트림 업데이트 준비
+```
+
+## 추가 문서
+
+- `docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md`
+- `docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md`
+- `docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md`
+- `docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md`
+- `docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md`
+
+## 현재 성과
+
+- CLI 기반 백테스트 실행 경로 구축
+- 조건식 후보 생성 및 후보별 백테스트 실행 경로 구축
+- retention-aware 후보 선택
+- row-level 후보 차이 분석
+- v3/v4/v5 후보 생성과 actual row-set 선택
+- v5 후보 부족 recovery
+- Wide v2 반복 개선 optimizer
+- WFO/OOS 검증 경로
+- PR 기반 merge 루틴 안정화
+
+## 현재 한계
+
+Wide v2는 Wide v1보다 손실을 조금 줄였지만 아직 수익 전략은 아닙니다.
+
+- Wide v1 평균 총수익률: `-53.20%`
+- Wide v2 평균 총수익률: `-52.05875%`
+- 개선 폭: `+1.14125%p`
+- Wide v2 8라운드 합산 손익금 개선: `+106,317,169원`
+- Wide v2 평균 거래당 수익률: `-0.61875%`
+
+따라서 `WideV2Final_B_20260428`은 수익 나는 최종 조건식이 아니라 추후 개선을 위한 중간 후보로 봅니다.
+
+## 2U 대비 2U_C 커스텀 범위
+
+- 주요 커스텀 전체: `340` files
+- `cli/`: `55` files
+- `tests/unit/`: `84` files
+- `docs/`: `234` files
+
+보호 대상:
+
+```text
+cli/
+stom_backtest.py
+tests/unit/test_research_*
+docs/research/condition_research/
+docs/superpowers/
+utility/ai_agent/Wide*Final*
+```
+
+## 포함하지 않는 것
+
+- 코드 리팩토링
+- 수익률 목적함수 구현
+- v6/v7 후보 생성
+- WFO/OOS 재실행
+- full backtest 재실행
+- 실거래, paper trading, 운영 파일럿
+- `utility/strategy.db`
+- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`
+
+## 검증
+
+계획된 검증:
+
+```powershell
+git diff --check --ignore-cr-at-eol HEAD
+python scripts/verify_nonrelease_sync.py
+python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
+```
+
+시간이 오래 걸릴 때 최소 검증:
+
+```powershell
+git diff --check --ignore-cr-at-eol HEAD
+python scripts/verify_nonrelease_sync.py
+python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer_report.py -q
+```
+
+## Merge 이후 다음 단계
+
+다음 브랜치:
+
+```text
+feature/cli-research-refactor-plan
+```
+
+다음 추천 명령:
+
+```text
+$brainstorming Wide v2 CLI research 리팩토링 범위와 업스트림 업데이트 보호 설계
+```
*** End Patch
```

- [ ] **Step 2: Verify PR body**

Run:

```powershell
Select-String -Path docs\pr\2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md -Pattern "문서-only 정리 PR|WideV2Final_B_20260428|주요 커스텀 전체|feature/cli-research-refactor-plan|brainstorming Wide v2 CLI research"
```

Expected output contains all five patterns.

### Task 6: Verify Documentation Set

**Files:**
- Read: all files created by Tasks 2-5
- Read: `docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md`
- Read: `docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md`

- [ ] **Step 1: Check required files exist**

Run:

```powershell
$files = @(
  "docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md",
  "docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md",
  "docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md",
  "docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md",
  "docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md",
  "docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md"
)
foreach ($file in $files) {
  if (!(Test-Path $file)) { throw "missing $file" }
  "exists $file"
}
```

Expected output contains six `exists` lines.

- [ ] **Step 2: Run placeholder scan**

Run:

```powershell
$patterns = @("TB" + "D", "TO" + "DO", "나중" + "에 작성", "추후" + " 작성")
Select-String -Path `
  docs\research\condition_research\mvp\2026-04-29_wide_v2_development_closeout.md,`
  docs\research\condition_research\mvp\2026-04-29_wide_v2_refactor_prep.md,`
  docs\research\condition_research\mvp\2026-04-29_2u_to_2uc_custom_inventory.md,`
  docs\pr\2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md `
  -Pattern $patterns
```

Expected:

```text
No output.
```

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
No output.
```

### Task 7: Run Verification

**Files:**
- No file edits.

- [ ] **Step 1: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
Exit code 0.
```

- [ ] **Step 2: Run focused docs-safe research tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer_report.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Run broader focused research CLI tests if time allows**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

Expected:

```text
All tests pass.
```

If this command takes too long, stop it only after recording elapsed time and report that the minimum verification in Step 2 passed.

### Task 8: Commit Documentation

**Files:**
- Stage only files listed below.

- [ ] **Step 1: Review changed files**

Run:

```powershell
git status --short
```

Expected includes:

```text
?? backtest/graph/
?? docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md
?? docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md
?? docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md
?? docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md
?? docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md
```

- [ ] **Step 2: Stage explicit files only**

Run:

```powershell
git add docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md
git add docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md
git add docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md
git add docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md
git add docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md
git add docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md
```

- [ ] **Step 3: Confirm staged files**

Run:

```powershell
git diff --cached --name-only
```

Expected exactly:

```text
docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md
docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md
docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md
docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md
docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md
docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md
```

- [ ] **Step 4: Commit with Lore protocol**

Run:

```powershell
git commit -m "Wide v2 개발 정리와 리팩토링 준비 문서를 고정한다" -m "조건식 개선 파이프라인은 구축됐지만 수익률 개선 성과가 아직 작으므로 현재 개발 단계를 문서-only closeout으로 정리한다. 2U 대비 2U_C 커스텀 범위와 CLI 리팩토링 준비 원칙을 기록해 다음 리팩토링 및 업스트림 업데이트 준비의 기준점을 만든다.

Constraint: 이번 PR은 코드 변경 없이 문서만 추가한다
Constraint: backtest/graph, backtest/temp, backtest/csv, utility/strategy.db는 커밋하지 않는다
Rejected: 수익률 목적함수 구현을 즉시 진행 | 현재 구조 정리와 커스텀 인벤토리 고정이 먼저다
Rejected: 리팩토링을 같은 PR에 포함 | 문서 정리 PR의 목적이 흐려지고 회귀 위험이 커진다
Confidence: high
Scope-risk: narrow
Directive: 이 merge point 이후 실제 리팩토링은 feature/cli-research-refactor-plan 계열 브랜치에서 별도 PR로 진행할 것
Tested: git diff check, verify_nonrelease_sync, focused pytest
Not-tested: full backtest, WFO/OOS rerun, live trading"
```

Expected:

```text
Git exits 0 and prints a commit summary for "Wide v2 개발 정리와 리팩토링 준비 문서를 고정한다".
```

### Task 9: Push Branch And Create PR

**Files:**
- Read: `docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md`

- [ ] **Step 1: Confirm GitHub CLI auth**

Run:

```powershell
gh auth status
```

Expected:

```text
Logged in to github.com
```

If `gh auth status` exits nonzero, stop and report that PR creation is blocked by missing GitHub authentication.

- [ ] **Step 2: Push branch**

Run:

```powershell
git push -u origin feature/wide-v2-development-closeout-refactor-prep
```

Expected:

```text
branch 'feature/wide-v2-development-closeout-refactor-prep' set up to track 'origin/feature/wide-v2-development-closeout-refactor-prep'
```

- [ ] **Step 3: Create PR**

Run:

```powershell
gh pr create --base STOM_Version_2U_C --head feature/wide-v2-development-closeout-refactor-prep --title "Wide v2 개발 정리 및 CLI 리팩토링 준비" --body-file docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md
```

Expected:

```text
https://github.com/Py-CI-Park/STOM_V/pull/<number>
```

- [ ] **Step 4: Record PR metadata**

Run:

```powershell
gh pr view --json number,url,state,mergeStateStatus,reviewDecision,baseRefName,headRefName --jq '"PR #\(.number) \(.url) state=\(.state) base=\(.baseRefName) head=\(.headRefName) mergeState=\(.mergeStateStatus) review=\(.reviewDecision)"'
```

Expected contains:

```text
state=OPEN base=STOM_Version_2U_C head=feature/wide-v2-development-closeout-refactor-prep
```

### Task 10: Merge PR And Sync Local Base

**Files:**
- No file edits.

- [ ] **Step 1: Merge PR through GitHub**

Run:

```powershell
gh pr merge --merge --delete-branch=false --subject "Wide v2 개발 정리 및 CLI 리팩토링 준비" --body "조건식 개선 파이프라인 개발 성과와 한계, 2U 대비 2U_C 커스텀 인벤토리, CLI 리팩토링 준비 원칙을 문서-only merge point로 고정한다."
```

Expected:

```text
Merged pull request
```

If GitHub blocks merge, run:

```powershell
gh pr view --json statusCheckRollup,mergeStateStatus,reviewDecision
```

Then report the blocking check names and do not use local direct merge as a substitute.

- [ ] **Step 2: Switch local base branch and fast-forward**

Run:

```powershell
git switch STOM_Version_2U_C
git pull --ff-only origin STOM_Version_2U_C
```

Expected:

```text
Fast-forward
```

- [ ] **Step 3: Verify merged commit is on local base**

Run:

```powershell
git log --oneline --decorate -6
```

Expected includes:

```text
Wide v2 개발 정리와 리팩토링 준비 문서를 고정한다
Wide v2 개발 정리와 리팩토링 준비 설계를 고정한다
Wide v2 MVP freeze 및 PR 병합 보고서
```

- [ ] **Step 4: Run post-merge smoke check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
No whitespace errors and verify_nonrelease_sync exits 0.
```

### Task 11: Create Next Refactor Planning Branch

**Files:**
- No file edits.

- [ ] **Step 1: Create next planning branch**

Run:

```powershell
git switch -c feature/cli-research-refactor-plan
```

Expected:

```text
Switched to a new branch 'feature/cli-research-refactor-plan'
```

- [ ] **Step 2: Report next recommended command**

Report:

```text
$brainstorming Wide v2 CLI research 리팩토링 범위와 업스트림 업데이트 보호 설계
```

---

## Self-Review

Spec coverage:

- Development closeout: covered by Task 2.
- Refactor preparation: covered by Task 3.
- 2U to 2U_C custom inventory: covered by Task 4.
- Korean PR body and merge routine: covered by Tasks 5, 9, and 10.
- Documentation-only scope: covered in Scope, Files, and Tasks 2-5.
- No code refactor in this PR: covered in Scope, Files, and Task 8 staging.
- Protected runtime outputs: covered in Scope, Files, Task 4, and Task 8 staging.
- Next branch and next command: covered by Task 11.

Placeholder scan:

- This plan contains no open placeholder requirements.
- Every created file path is exact.
- Every command has an expected result.
- Every document creation task includes complete content.

Type and field consistency:

- Branch name is consistently `feature/wide-v2-development-closeout-refactor-prep`.
- Base branch is consistently `STOM_Version_2U_C`.
- Next refactor branch is consistently `feature/cli-research-refactor-plan`.
- Wide v2 final strategy is consistently `WideV2Final_B_20260428`.
- Protected paths are consistently `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, and `utility/strategy.db`.

## Execution Recommendation

Recommended execution mode: Inline Execution using `superpowers:executing-plans`.

Reason:

- The plan is sequential and documentation-only.
- PR creation and merge should stay in one session for traceability.
- Subagents are unnecessary unless a separate documentation review lane is explicitly requested.
