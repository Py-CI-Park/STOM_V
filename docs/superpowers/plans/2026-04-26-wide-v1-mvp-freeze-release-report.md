# Wide v1 MVP Freeze Release Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when the user explicitly requests parallel subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wide v1 WFO 통과 결과를 MVP freeze 상태로 고정하고, 운영 재현 문서와 실제 GitHub PR 생성/merge 루틴을 완성한다.

**Architecture:** 이번 단계는 신규 조건식 생성이나 백테스트 탐색이 아니다. 이미 WFO를 통과한 `WideV1Final_B_20260425`를 MVP freeze artifact로 선언하고, 재현 가능한 CLI 명령, strategy DB 재생성 방법, 검증 증거, 남은 위험, 실제 PR 운영 절차를 문서로 고정한다. 기존 로컬 `git merge --no-ff` 루틴은 중단하고, 이번 브랜치부터 `git push` -> `gh pr create` -> `gh pr merge` -> `STOM_Version_2U_C` fast-forward 동기화 흐름을 사용한다.

**Tech Stack:** Markdown, PowerShell, Python JSON parsing, Git, GitHub CLI `gh`, STOM CLI `stom_backtest.py`, SQLite strategy DB, pytest.

---

## Current State

- Current branch: `feature/wide-v1-mvp-freeze-release-report`
- Base branch: `STOM_Version_2U_C`
- Previous merge commit on base: `a42e1100 Wide v1 v5 승격 WFO 검증을 병합한다`
- Final buy strategy: `WideV1Final_B_20260425`
- Strategy snapshot: `utility/ai_agent/WideV1Final_B_20260425.py`
- WFO decision: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`
- WFO compact report: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`
- WFO result:
  - `round_count=8`
  - `success_rate=1.0`
  - `mean_oos_metric=0.5762499999999999`
  - `mean_trade_count=2131.75`
  - `zero_trade_rounds=0`
  - balanced preset passed
  - conservative preset passed
- Current remote:
  - `origin=https://github.com/Py-CI-Park/STOM_V.git`
- GitHub CLI is installed:
  - `gh version 2.82.1`

## Scope

This plan freezes documentation and PR operations only.

In scope:

- Write MVP freeze report.
- Write operational reproduction guide.
- Write release checklist.
- Fix the previous WFO PR report newline formatting defect.
- Write Korean PR report for the MVP freeze branch.
- Verify docs and strategy reproduction commands.
- Push feature branch to GitHub.
- Create a real GitHub PR with `gh pr create`.
- Merge that PR with `gh pr merge`.
- Fast-forward local `STOM_Version_2U_C` from `origin`.
- Create the next post-MVP branch.

Out of scope:

- New candidate generation.
- v6 or v7 condition research.
- Additional full WFO rerun.
- Live trading execution.
- Serial-key logic.
- Refactoring CLI folder structure.

## Files

- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md`
  - Freeze decision, final artifact, WFO evidence, acceptance gates, rejected alternatives.
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md`
  - Exact commands to recreate DB strategy, run preflight, run WFO dry-run, and reproduce verification.
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_release_checklist.md`
  - Release readiness checklist, risks, required future pilot checks.
- Modify: `docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md`
  - Replace literal `` `n`` text in the verification section with actual Markdown list lines.
- Create: `docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md`
  - Korean PR body used directly by `gh pr create --body-file`.
- Create: `docs/superpowers/plans/2026-04-26-wide-v1-mvp-freeze-release-report.md`
  - This plan.

Do not stage:

- `backtest/graph/`
- `backtest/temp/`
- `backtest/csv/`
- `utility/strategy.db`

---

### Task 1: Verify Branch And Source Evidence

**Files:**
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json`
- Read: `utility/ai_agent/WideV1Final_B_20260425.py`

- [ ] **Step 1: Confirm branch and tracked state**

Run:

```powershell
git status --short --branch --untracked-files=no
```

Expected:

```text
## feature/wide-v1-mvp-freeze-release-report
```

- [ ] **Step 2: Confirm WFO decision is MVP freeze**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_wfo_decision.md -Pattern "decision=|next_command=|final_buy_strategy="
```

Expected:

```text
decision=PROCEED_TO_MVP_FREEZE
next_command=$writing-plans Wide v1 MVP freeze 및 운영 재현 문서 작성
final_buy_strategy=WideV1Final_B_20260425
```

- [ ] **Step 3: Confirm WFO summary from compact report**

Run:

```powershell
@'
import json
from pathlib import Path

report = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json").read_text(encoding="utf-8"))
summary = report["summary"]
print(report["status"])
print(summary["round_count"])
print(summary["success_rate"])
print(summary["mean_oos_metric"])
print(summary["mean_trade_count"])
print(summary["zero_trade_rounds"])
'@ | python -
```

Expected:

```text
ok
8
1.0
0.5762499999999999
2131.75
0
```

- [ ] **Step 4: Confirm final strategy snapshot contains the freeze condition**

Run:

```powershell
@'
from pathlib import Path

code = Path(r"utility\ai_agent\WideV1Final_B_20260425.py").read_text(encoding="utf-8")
print("WideV1Final_B_20260425" in code)
print("66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" in code)
print("self.Buy()" in code)
'@ | python -
```

Expected:

```text
True
True
True
```

### Task 2: Fix Previous WFO PR Report Formatting

**Files:**
- Modify: `docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md`

- [ ] **Step 1: Confirm the literal newline defect exists**

Run:

```powershell
Select-String -Path docs\pr\2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md -Pattern '`n'
```

Expected currently shows one line in the `## 검증` section containing literal `` `n`` text.

- [ ] **Step 2: Replace the verification section with real Markdown list lines**

Use `apply_patch` with this exact patch:

```diff
*** Begin Patch
*** Update File: docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md
@@
-- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py -q`: 14 passed`n- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`: 113 passed`n- `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`: 167 passed`n- `cmd /c "git diff --check --ignore-cr-at-eol 2>&1"`: whitespace 오류 없음, Windows line-ending 경고만 출력
+- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py -q`: 14 passed
+- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`: 113 passed
+- `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`: 167 passed
+- `cmd /c "git diff --check --ignore-cr-at-eol 2>&1"`: whitespace 오류 없음, Windows line-ending 경고만 출력
*** End Patch
```

- [ ] **Step 3: Verify literal newline text is gone**

Run:

```powershell
Select-String -Path docs\pr\2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md -Pattern '`n'
```

Expected:

```text
명령 출력이 없다.
```

### Task 3: Create MVP Freeze Report

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md`

- [ ] **Step 1: Create the MVP directory**

Run:

```powershell
New-Item -ItemType Directory -Force docs\research\condition_research\mvp
```

Expected:

```text
Directory: C:\System_Trading\STOM\STOM_V.wt-dev\docs\research\condition_research
```

- [ ] **Step 2: Write the freeze report from committed evidence**

Run:

```powershell
$report = Get-Content docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_wfo_report.json -Raw -Encoding UTF8 | ConvertFrom-Json
$manifest = Get-Content docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_promote_manifest.json -Raw -Encoding UTF8 | ConvertFrom-Json
$primary = $manifest.primary_candidate
$summary = $report.summary
$path = 'docs\research\condition_research\mvp\2026-04-26_wide_v1_mvp_freeze.md'
$lines = @(
'# Wide v1 MVP freeze',
'',
'## Freeze decision',
'',
'- decision=FREEZE_WIDE_V1_MVP_CANDIDATE',
'- frozen_at=2026-04-26',
'- final_buy_strategy=WideV1Final_B_20260425',
'- base_buy_strategy=WideV1IterationV2_20260423__cand005',
'- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419',
"- primary_candidate=$($primary.strategy_name)",
"- primary_expression=$($primary.expression)",
"- source_candidate_csv=$($primary.candidate_csv)",
'',
'## Why freeze now',
'',
'- v5에서 실제 row-set 기준 대표 후보 10개를 확보했다.',
'- cand017은 selected_as_best=True 및 actual_rowset_selected=True로 선택되었다.',
'- cand017 임시 전략은 cleanup으로 삭제될 수 있어 조건식을 영구 전략 `WideV1Final_B_20260425`로 재생성했다.',
'- `runtime-preflight`가 `status=ok`로 통과했다.',
'- WFO는 8개 window에서 `status=ok`로 완료되었다.',
'- balanced preset과 conservative preset 모두 통과했다.',
'',
'## WFO evidence',
'',
"- round_count=$($summary.round_count)",
"- success_count=$($summary.success_count)",
"- success_rate=$($summary.success_rate)",
"- metric=$($summary.metric)",
"- mean_oos_metric=$($summary.mean_oos_metric)",
"- best_oos_metric=$($summary.best_oos_metric)",
"- mean_trade_count=$($summary.mean_trade_count)",
"- zero_trade_rounds=$($summary.zero_trade_rounds)",
'',
'## Freeze gates',
'',
'| Gate | Required | Actual | Result |',
'| --- | --- | --- | --- |',
'| actual row-set selection | selected_count >= 10 | selected_count=10 | PASS |',
'| final strategy recreation | DB-loadable strategy snapshot | WideV1Final_B_20260425 snapshot exists | PASS |',
'| runtime preflight | status=ok | status=ok | PASS |',
"| WFO rounds | round_count >= 3 | round_count=$($summary.round_count) | PASS |",
"| WFO success rate | success_rate >= 0.60 | success_rate=$($summary.success_rate) | PASS |",
"| WFO mean OOS metric | mean_oos_metric >= 0.00 | mean_oos_metric=$($summary.mean_oos_metric) | PASS |",
"| WFO average trades | mean_trade_count >= 50 | mean_trade_count=$($summary.mean_trade_count) | PASS |",
"| no-trade failure | zero_trade_rounds < round_count | zero_trade_rounds=$($summary.zero_trade_rounds) | PASS |",
'',
'## Rejected alternatives',
'',
'- v6 후보 생성으로 즉시 진행하지 않는다. WFO 기준을 통과했으므로 신규 후보 탐색보다 freeze와 운영 재현성 고정이 우선이다.',
'- `discovery research`에 WFO를 다시 붙이지 않는다. research는 빠른 후보 생성 루프이고 WFO는 별도 최종 검증 루프다.',
'- raw WFO JSON 전체를 PR에 넣지 않는다. compact report를 커밋하고 raw runtime copy는 `backtest/temp` 증거로 둔다.',
'',
'## Freeze meaning',
'',
'- 이 freeze는 실거래 수익 보장이 아니다.',
'- 이 freeze는 Wide v1 연구 루프의 MVP 후보를 더 이상 v6/v7 탐색으로 확장하지 않고 운영 재현 문서화 단계로 이동한다는 기준점이다.',
'- 실거래 전에는 별도 소액 파일럿, 슬리피지 확인, 장중 장애 대응, broker/API runtime 확인이 필요하다.'
)
$lines | Set-Content -Path $path -Encoding UTF8
Write-Output $path
```

Expected:

```text
docs\research\condition_research\mvp\2026-04-26_wide_v1_mvp_freeze.md
```

- [ ] **Step 3: Verify freeze report contains the required decision**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-26_wide_v1_mvp_freeze.md -Pattern "FREEZE_WIDE_V1_MVP_CANDIDATE|WideV1Final_B_20260425|mean_oos_metric=0.5762499999999999"
```

Expected:

```text
FREEZE_WIDE_V1_MVP_CANDIDATE
WideV1Final_B_20260425
mean_oos_metric=0.5762499999999999
```

### Task 4: Create Operational Reproduction Guide

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md`

- [ ] **Step 1: Write exact reproduction commands**

Run:

```powershell
$path = 'docs\research\condition_research\mvp\2026-04-26_wide_v1_operational_reproduction.md'
$lines = @(
'# Wide v1 operational reproduction',
'',
'## Purpose',
'',
'이 문서는 `WideV1Final_B_20260425` MVP 후보를 다른 세션에서 재현하기 위한 최소 명령어 세트다.',
'',
'## Constants',
'',
'```text',
'FINAL_BUY=WideV1Final_B_20260425',
'BASE_BUY=WideV1IterationV2_20260423__cand005',
'SELL=ResearchTest_Tick_S_090000_092800_Wide_20260419',
'START=20250101',
'END=20251231',
'TIMEFRAME=tick',
'BETTING=20',
'AVG_TIME=30',
'START_TIME=90000',
'END_TIME=92800',
'ENGINES=32',
'TRAIN_WINDOW_DAYS=120',
'TEST_WINDOW_DAYS=30',
'STEP_DAYS=30',
'PURGE_DAYS=1',
'EMBARGO_DAYS=1',
'OBJECTIVE=tpi',
'METHOD=grid',
'MAX_ITER=1',
'```',
'',
'## Step 1: Restore final buy strategy into strategy DB',
'',
'```powershell',
'@''',
'from pathlib import Path',
'from cli.paths import DB_STRATEGY',
'from cli.strategy_generator import save_strategy_to_db',
'',
'strategy_name = "WideV1Final_B_20260425"',
'code = Path(r"utility\ai_agent\WideV1Final_B_20260425.py").read_text(encoding="utf-8")',
'result = save_strategy_to_db(DB_STRATEGY, strategy_name, code, "buy")',
'print(result)',
'''@ | python -',
'```',
'',
'Expected:',
'',
'```text',
'status=ok with action created or updated',
'```',
'',
'## Step 2: Verify strategy loads from DB',
'',
'```powershell',
'@''',
'from cli.paths import DB_STRATEGY',
'from cli.strategy_loader import load_strategy_from_db',
'',
'result = load_strategy_from_db(DB_STRATEGY, "WideV1Final_B_20260425", "buy")',
'print(result.get("status"))',
'print("66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" in result.get("code", ""))',
'print("self.Buy()" in result.get("code", ""))',
'''@ | python -',
'```',
'',
'Expected:',
'',
'```text',
'ok',
'True',
'True',
'```',
'',
'## Step 3: Runtime preflight',
'',
'```powershell',
'$preflight = python .\stom_backtest.py runtime-preflight --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 900',
'$preflight | Set-Content -Path backtest\temp\wide_v1_mvp_freeze_preflight_20260426.json -Encoding UTF8',
'if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
'```',
'',
'Expected:',
'',
'```text',
'PowerShell exits 0 and the JSON file contains status=ok.',
'```',
'',
'## Step 4: WFO window dry-run',
'',
'```powershell',
'python .\stom_backtest.py wfo --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --dry-run -o backtest\temp\wide_v1_mvp_freeze_wfo_windows_20260426.json',
'```',
'',
'Expected:',
'',
'```text',
'round_count=8',
'```',
'',
'## Step 5: Optional full WFO reproduction',
'',
'```powershell',
'python .\stom_backtest.py wfo --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --objective tpi --method grid --max-iter 1 --engines 32 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --timeout 900 --format json -o backtest\temp\wide_v1_mvp_freeze_wfo_report_20260426.json',
'```',
'',
'Expected based on the frozen run:',
'',
'```text',
'status=ok',
'round_count=8',
'success_rate=1.0',
'mean_oos_metric=0.5762499999999999',
'mean_trade_count=2131.75',
'zero_trade_rounds=0',
'```',
'',
'## Step 6: Unit and regression verification',
'',
'```powershell',
'python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q',
'python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q',
'cmd /c "git diff --check --ignore-cr-at-eol 2>&1"',
'```',
'',
'Expected from the frozen branch:',
'',
'```text',
'113 passed',
'167 passed',
'diff check prints no whitespace errors',
'```',
'',
'## Operational caution',
'',
'- 이 재현 절차는 백테스트와 WFO 검증 재현 절차다.',
'- 실거래 전에는 소액 파일럿, 슬리피지, 호가 체결, API 장애 대응을 별도 검증해야 한다.',
'- `utility/strategy.db`는 런타임 DB이므로 Git diff 대신 `utility/ai_agent/WideV1Final_B_20260425.py` 스냅샷을 기준 artifact로 사용한다.'
)
$lines | Set-Content -Path $path -Encoding UTF8
Write-Output $path
```

Expected:

```text
docs\research\condition_research\mvp\2026-04-26_wide_v1_operational_reproduction.md
```

- [ ] **Step 2: Verify reproduction guide has exact commands**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-26_wide_v1_operational_reproduction.md -Pattern "runtime-preflight|wfo --buy WideV1Final_B_20260425|113 passed|167 passed"
```

Expected:

```text
runtime-preflight
wfo --buy WideV1Final_B_20260425
113 passed
167 passed
```

### Task 5: Create Release Checklist

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_release_checklist.md`

- [ ] **Step 1: Write release checklist**

Run:

```powershell
$path = 'docs\research\condition_research\mvp\2026-04-26_wide_v1_release_checklist.md'
$lines = @(
'# Wide v1 release checklist',
'',
'## MVP readiness',
'',
'- [x] v5 actual row-set 대표 후보 10개 확보',
'- [x] 대표 후보 cand017 선택',
'- [x] 최종 전략명 `WideV1Final_B_20260425` 고정',
'- [x] 최종 전략 스냅샷 `utility/ai_agent/WideV1Final_B_20260425.py` 커밋',
'- [x] runtime-preflight 통과',
'- [x] WFO dry-run window count 8 확인',
'- [x] WFO full validation 통과',
'- [x] balanced preset 통과',
'- [x] conservative preset 통과',
'- [x] WFO CLI dict config bugfix 테스트 포함',
'',
'## Not yet release-safe for live trading',
'',
'- [ ] 소액 실거래 파일럿 기간 정의',
'- [ ] 슬리피지와 호가 체결 차이 측정',
'- [ ] 장중 네트워크/API 장애 대응 확인',
'- [ ] 주문 수량, 예수금, 종목당 배팅금액 live guard 확인',
'- [ ] 실거래 중지 조건과 rollback 절차 정의',
'- [ ] 장 종료 후 거래 로그와 백테스트 예측 비교 템플릿 작성',
'',
'## Frozen artifacts',
'',
'| Artifact | Path |',
'| --- | --- |',
'| Final strategy snapshot | `utility/ai_agent/WideV1Final_B_20260425.py` |',
'| Promote manifest | `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json` |',
'| WFO report | `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json` |',
'| WFO decision | `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md` |',
'| MVP freeze report | `docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md` |',
'| Operational reproduction | `docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md` |',
'',
'## Next branch after PR merge',
'',
'- branch=feature/wide-v1-post-mvp-risk-backlog',
'- command=$writing-plans Wide v1 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성',
'',
'## Stop conditions',
'',
'- 신규 조건식 탐색은 MVP freeze PR merge 이후 별도 post-MVP backlog에서만 재개한다.',
'- WFO 결과를 덮어쓰는 full rerun은 별도 브랜치와 별도 PR로만 수행한다.',
'- `STOM_Version_2U_C`에 직접 커밋하지 않는다.',
'- 이후 통합은 GitHub PR 생성과 PR merge 기록을 남긴다.'
)
$lines | Set-Content -Path $path -Encoding UTF8
Write-Output $path
```

Expected:

```text
docs\research\condition_research\mvp\2026-04-26_wide_v1_release_checklist.md
```

- [ ] **Step 2: Verify checklist includes live-trading exclusions**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-26_wide_v1_release_checklist.md -Pattern "Not yet release-safe|소액 실거래|STOM_Version_2U_C에 직접 커밋하지 않는다"
```

Expected:

```text
Not yet release-safe for live trading
소액 실거래 파일럿 기간 정의
STOM_Version_2U_C에 직접 커밋하지 않는다
```

### Task 6: Create GitHub PR Body

**Files:**
- Create: `docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md`

- [ ] **Step 1: Write the Korean PR body**

Run:

```powershell
$path = 'docs\pr\2026-04-26_wide_v1_mvp_freeze_release_report_pr.md'
$lines = @(
'# Wide v1 MVP freeze 및 운영 재현 문서화 PR',
'',
'## 목적',
'',
'Wide v1 v5 promote/WFO 검증에서 통과한 `WideV1Final_B_20260425`를 MVP freeze 후보로 고정하고, 운영 재현 명령어와 릴리스 전 체크리스트를 문서화한다.',
'',
'## 전체 방향',
'',
'```text',
'v5 actual row-set representative selection',
'-> cand017 primary representative',
'-> WideV1Final_B_20260425 permanent strategy',
'-> runtime-preflight',
'-> WFO 8 windows',
'-> balanced/conservative pass',
'-> MVP freeze',
'-> operational reproduction and live-pilot backlog',
'```',
'',
'## 변경 사항',
'',
'- MVP freeze 보고서 추가',
'- 운영 재현 명령어 문서 추가',
'- 릴리스 체크리스트 추가',
'- 이전 WFO PR 보고서의 verification 줄바꿈 표시 정정',
'- 실제 GitHub PR 운영으로 전환하기 위한 PR 본문 추가',
'',
'## 근거',
'',
'- final_buy_strategy=`WideV1Final_B_20260425`',
'- primary_candidate=`WideV1IterationV5ObservableFull_20260425__cand017`',
'- primary_expression=`66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`',
'- WFO `round_count=8`',
'- WFO `success_rate=1.0`',
'- WFO `mean_oos_metric=0.5762499999999999`',
'- WFO `mean_trade_count=2131.75`',
'- WFO `zero_trade_rounds=0`',
'- balanced preset 통과',
'- conservative preset 통과',
'',
'## 검증 계획',
'',
'- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`',
'- `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`',
'- `python scripts/verify_nonrelease_sync.py`',
'- `cmd /c "git diff --check --ignore-cr-at-eol 2>&1"`',
'- `gh pr create --base STOM_Version_2U_C --head feature/wide-v1-mvp-freeze-release-report --title "Wide v1 MVP freeze 및 운영 재현 문서화" --body-file docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md`',
'',
'## 남은 위험',
'',
'- MVP freeze는 실거래 수익 보장이 아니다.',
'- 실거래 전에는 소액 파일럿, 슬리피지, 호가 체결, 주문 실패 대응을 별도 확인해야 한다.',
'- 신규 후보 탐색은 post-MVP backlog에서 별도 브랜치와 PR로 재개한다.',
'',
'## 다음 단계',
'',
'- PR merge 후 `feature/wide-v1-post-mvp-risk-backlog` 브랜치를 생성한다.',
'- 다음 명령어: `$writing-plans Wide v1 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성`'
)
$lines | Set-Content -Path $path -Encoding UTF8
Write-Output $path
```

Expected:

```text
docs\pr\2026-04-26_wide_v1_mvp_freeze_release_report_pr.md
```

- [ ] **Step 2: Verify PR body contains GitHub PR command**

Run:

```powershell
Select-String -Path docs\pr\2026-04-26_wide_v1_mvp_freeze_release_report_pr.md -Pattern "gh pr create|Wide v1 MVP freeze 및 운영 재현 문서화|post-MVP"
```

Expected:

```text
gh pr create
Wide v1 MVP freeze 및 운영 재현 문서화
post-MVP
```

### Task 7: Verify Documentation And Runtime Reproduction

**Files:**
- Read: all files changed by this plan

- [ ] **Step 1: Verify final strategy can be restored to DB from snapshot**

Run:

```powershell
@'
from pathlib import Path
from cli.paths import DB_STRATEGY
from cli.strategy_generator import save_strategy_to_db
from cli.strategy_loader import load_strategy_from_db

strategy_name = "WideV1Final_B_20260425"
code = Path(r"utility\ai_agent\WideV1Final_B_20260425.py").read_text(encoding="utf-8")
save_result = save_strategy_to_db(DB_STRATEGY, strategy_name, code, "buy")
load_result = load_strategy_from_db(DB_STRATEGY, strategy_name, "buy")
print(save_result.get("status"))
print(load_result.get("status"))
print("66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" in load_result.get("code", ""))
'@ | python -
```

Expected:

```text
ok
ok
True
```

- [ ] **Step 2: Run runtime preflight**

Run:

```powershell
$preflight = python .\stom_backtest.py runtime-preflight --buy WideV1Final_B_20260425 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 900
$preflight | Set-Content -Path backtest\temp\wide_v1_mvp_freeze_preflight_20260426.json -Encoding UTF8
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Expected:

```text
PowerShell exits 0.
```

- [ ] **Step 3: Inspect preflight result**

Run:

```powershell
@'
import json
from pathlib import Path

data = json.loads(Path(r"backtest\temp\wide_v1_mvp_freeze_preflight_20260426.json").read_text(encoding="utf-8-sig"))
print(data.get("status"))
print(data.get("failed_checks"))
'@ | python -
```

Expected:

```text
ok
[]
```

- [ ] **Step 4: Run WFO dry-run only**

Run:

```powershell
python .\stom_backtest.py wfo --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --dry-run -o backtest\temp\wide_v1_mvp_freeze_wfo_windows_20260426.json
```

Expected:

```text
PowerShell exits 0.
```

- [ ] **Step 5: Inspect WFO dry-run window count**

Run:

```powershell
@'
import json
from pathlib import Path

data = json.loads(Path(r"backtest\temp\wide_v1_mvp_freeze_wfo_windows_20260426.json").read_text(encoding="utf-8"))
print(data.get("status"))
print(data.get("round_count"))
'@ | python -
```

Expected:

```text
dry-run
8
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
```

Expected:

```text
113 passed
```

- [ ] **Step 7: Run research regression tests**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
167 passed
```

- [ ] **Step 8: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
All non-release sync checks passed.
```

- [ ] **Step 9: Run whitespace check**

Run:

```powershell
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
명령 출력이 없다.
```

### Task 8: Commit MVP Freeze Documentation

**Files:**
- Stage only files listed in the Files section.

- [ ] **Step 1: Review changed files**

Run:

```powershell
git status --short
```

Expected includes these tracked/untracked files:

```text
docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md
docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_release_checklist.md
```

- [ ] **Step 2: Stage explicit files only**

Run:

```powershell
git add docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md
git add docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md
git add docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md
git add docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md
git add docs/research/condition_research/mvp/2026-04-26_wide_v1_release_checklist.md
git add docs/superpowers/plans/2026-04-26-wide-v1-mvp-freeze-release-report.md
```

- [ ] **Step 3: Confirm staged files**

Run:

```powershell
git diff --cached --name-only
```

Expected exactly:

```text
docs/pr/2026-04-25_wide_v1_v5_promote_wfo_validation_pr.md
docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_release_checklist.md
docs/superpowers/plans/2026-04-26-wide-v1-mvp-freeze-release-report.md
```

- [ ] **Step 4: Commit with Lore protocol**

Run:

```powershell
git commit -m "Wide v1 MVP freeze 운영 재현 문서를 고정한다" -m "WFO를 통과한 WideV1Final_B_20260425를 MVP freeze 후보로 선언하고 운영 재현 명령어, 릴리스 체크리스트, 실제 GitHub PR 본문을 문서화한다. 이전 WFO PR 보고서의 줄바꿈 표시 오류도 함께 정정한다." -m "Constraint: 이번 단계는 신규 조건식 탐색이 아니라 WFO 통과 artifact의 freeze 문서화다
Constraint: 이후 통합은 로컬 merge가 아니라 GitHub PR 생성과 PR merge 기록을 남긴다
Rejected: v6 후보 생성으로 즉시 진행 | WFO 기준을 통과했으므로 MVP 종료 문서화가 우선이다
Confidence: high
Scope-risk: narrow
Directive: 실거래 전에는 post-MVP risk backlog와 소액 파일럿 체크리스트를 별도 PR로 진행한다
Tested: strategy snapshot DB restore, runtime-preflight, WFO dry-run, focused pytest, research regression pytest, verify_nonrelease_sync, git diff check
Not-tested: live trading execution"
```

### Task 9: Push Branch And Create Real GitHub PR

**Files:**
- Read: `docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md`

- [ ] **Step 1: Verify GitHub CLI auth**

Run:

```powershell
gh auth status
```

Expected:

```text
Logged in to github.com
```

If `gh auth status` exits nonzero, stop and report that PR creation is blocked by missing GitHub authentication. Do not use local `git merge --no-ff` as a substitute.

- [ ] **Step 2: Push the feature branch**

Run:

```powershell
git push -u origin feature/wide-v1-mvp-freeze-release-report
```

Expected:

```text
branch 'feature/wide-v1-mvp-freeze-release-report' set up to track 'origin/feature/wide-v1-mvp-freeze-release-report'
```

- [ ] **Step 3: Create the GitHub PR**

Run:

```powershell
gh pr create --base STOM_Version_2U_C --head feature/wide-v1-mvp-freeze-release-report --title "Wide v1 MVP freeze 및 운영 재현 문서화" --body-file docs/pr/2026-04-26_wide_v1_mvp_freeze_release_report_pr.md
```

Expected:

```text
https://github.com/Py-CI-Park/STOM_V/pull/
```

- [ ] **Step 4: Record PR metadata locally**

Run:

```powershell
gh pr view --json number,url,state,mergeStateStatus,reviewDecision --jq '"PR #\(.number) \(.url) state=\(.state) mergeState=\(.mergeStateStatus) review=\(.reviewDecision)"'
```

Expected:

```text
PR #숫자 https://github.com/Py-CI-Park/STOM_V/pull/숫자 state=OPEN mergeState=UNKNOWN review=
```

`mergeStateStatus` may be `UNKNOWN`, `CLEAN`, or `UNSTABLE` depending on repository settings. Continue only if the PR exists and points to base `STOM_Version_2U_C`.

### Task 10: Merge PR And Sync Local Base

**Files:**
- No file edits.

- [ ] **Step 1: Merge the PR through GitHub**

Run:

```powershell
gh pr merge --merge --delete-branch=false --subject "Wide v1 MVP freeze 및 운영 재현 문서화" --body "WFO 통과 후보 WideV1Final_B_20260425를 MVP freeze artifact로 문서화하고 운영 재현 절차를 고정한다."
```

Expected:

```text
Merged pull request
```

If GitHub blocks merge because of repository checks, stop and report the blocking check names from:

```powershell
gh pr view --json statusCheckRollup,mergeStateStatus,reviewDecision
```

- [ ] **Step 2: Switch local base branch and fast-forward from origin**

Run:

```powershell
git switch STOM_Version_2U_C
git pull --ff-only origin STOM_Version_2U_C
```

Expected:

```text
Updating ... Fast-forward
```

- [ ] **Step 3: Verify local base contains the PR commit**

Run:

```powershell
git log --oneline --decorate -5
```

Expected includes:

```text
Wide v1 MVP freeze 운영 재현 문서를 고정한다
```

- [ ] **Step 4: Run post-merge smoke verification**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
113 passed
명령 출력이 없다.
```

### Task 11: Create Next Branch

**Files:**
- No file edits.

- [ ] **Step 1: Create post-MVP risk backlog branch**

Run:

```powershell
git switch -c feature/wide-v1-post-mvp-risk-backlog
```

Expected:

```text
Switched to a new branch 'feature/wide-v1-post-mvp-risk-backlog'
```

- [ ] **Step 2: Report next command**

Report this exact next command:

```text
$writing-plans Wide v1 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성
```

---

## Self-Review

Spec coverage:

- `Wide v1 MVP freeze`: covered by Task 3 and Task 5.
- `운영 재현 문서`: covered by Task 4.
- 실제 PR 루틴 전환: covered by Task 9 and Task 10.
- 기존 로컬 merge 루틴 중단: covered by Scope, Task 9 auth block, and Task 10 GitHub merge.
- 이전 PR 문서 품질 정정: covered by Task 2.
- 검증과 후속 단계: covered by Task 7 and Task 11.

Red-flag scan:

- Every created file path is exact.
- Every command has an expected result.
- The plan does not rely on undefined helper scripts.
- The plan uses explicit `git add` paths and avoids `git add -A`.
- The plan excludes protected runtime outputs.

Type and field consistency:

- WFO summary fields match `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json`: `round_count`, `success_rate`, `mean_oos_metric`, `mean_trade_count`, `zero_trade_rounds`.
- Final strategy name is consistently `WideV1Final_B_20260425`.
- Base branch is consistently `STOM_Version_2U_C`.
- Feature branch is consistently `feature/wide-v1-mvp-freeze-release-report`.

## Execution Recommendation

Recommended execution mode: Inline Execution using `executing-plans`.

Reason:

- Tasks are sequential and depend on committed docs before PR creation.
- The only external side effect is GitHub PR creation and merge; this should stay in one session for traceability.
- Subagents are unnecessary unless the user explicitly requests a separate documentation review lane.
