# Wide v2 MVP Freeze And PR Merge Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only if the user explicitly requests a separate documentation review lane. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the WFO/OOS-passed Wide v2 candidate as the MVP development endpoint and complete the PR/merge reporting routine against `STOM_Version_2U_C`.

**Architecture:** This is a documentation, verification, and integration step, not a new candidate-generation step. The already validated strategy `WideV2Final_B_20260428` becomes the Wide v2 MVP freeze artifact, while `discovery research` and `optimize-wide-v2` remain candidate-generation tools for future post-MVP work. The branch should create reproducible freeze documents, verify that the strategy snapshot and WFO evidence are usable, commit the evidence, create a GitHub PR, merge it, sync local `STOM_Version_2U_C`, and then create the post-MVP risk backlog branch.

**Tech Stack:** Markdown, PowerShell, Python JSON parsing, Git, GitHub CLI `gh`, STOM CLI `stom_backtest.py`, SQLite strategy DB, pytest.

---

## Current State

- Current branch: `feature/wide-v2-mvp-freeze-pr-report`
- Base branch: `STOM_Version_2U_C`
- Current merge-base with base: `2e5143bd2ca65278f09b0cfcc7df371b21a6d7d7`
- Direct v4 shortfall recovery implementation commits:
  - `467aa304 Wide v2 direct_v4 부족 후보를 복구한다`
  - `f6d3c9cb Wide v2 direct_v4 복구 경로를 루프에서 검증한다`
  - `e05438ca Wide v2 direct_v4 복구 검증 결과를 기록한다`
- WFO/OOS plan and evidence commits:
  - `a3163ded Wide v2 WFO/OOS 검증 계획을 고정한다`
  - `f188b7c6 Wide v2 WFO/OOS 검증 통과를 기록한다`
- Final buy strategy: `WideV2Final_B_20260428`
- Strategy snapshot: `utility/ai_agent/WideV2Final_B_20260428.py`
- Source candidate: `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`
- Source expression: `66.999 <= 시가총액 < 2_580 and 등락율 > 3.535`
- WFO/OOS decision: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`
- WFO/OOS report: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`
- WFO/OOS result:
  - `round_count=8`
  - `success_count=8`
  - `success_rate=1.0`
  - `mean_oos_metric=0.5725`
  - `best_oos_metric=0.68`
  - `mean_trade_count=2045.125`
  - `zero_trade_rounds=0`
  - balanced preset passed
  - conservative preset passed

## Scope

In scope:

- Write Wide v2 MVP freeze report.
- Write Wide v2 operational reproduction guide.
- Write Wide v2 release checklist and live-trading exclusions.
- Write Korean PR body / merge report.
- Verify the strategy snapshot can be restored to `utility/strategy.db`.
- Verify runtime preflight and WFO dry-run only.
- Verify the committed WFO/OOS JSON still contains the freeze metrics.
- Run focused WFO/strategy tests and optimizer/research regression tests.
- Run non-release sync guard and whitespace check.
- Commit freeze documentation.
- Push feature branch, create GitHub PR, merge PR, and fast-forward local `STOM_Version_2U_C`.
- Create next post-MVP branch.

Out of scope:

- No new v6/v7 candidate generation.
- No additional full WFO rerun.
- No live-trading execution.
- No serial-key logic.
- No broad CLI refactor.
- No commit of protected raw runtime outputs.

Do not stage:

- `backtest/graph/`
- `backtest/temp/`
- `backtest/csv/`
- `utility/strategy.db`

---

### Task 1: Verify Branch And Source Evidence

**Files:**
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`
- Read: `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json`
- Read: `utility/ai_agent/WideV2Final_B_20260428.py`

- [ ] **Step 1: Confirm branch and tracked state**

Run:

```powershell
git status --short --branch --untracked-files=no
```

Expected:

```text
## feature/wide-v2-mvp-freeze-pr-report
```

- [ ] **Step 2: Confirm WFO/OOS decision is MVP freeze**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_decision.md -Pattern "decision=|next_command=|final_buy_strategy=|source_expression="
```

Expected output contains:

```text
decision=PROCEED_TO_MVP_FREEZE
next_command=$writing-plans Wide v2 MVP freeze 및 PR 병합 보고서 작성
final_buy_strategy=WideV2Final_B_20260428
source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
```

- [ ] **Step 3: Confirm WFO/OOS summary from committed report**

Run:

```powershell
@'
import json
from pathlib import Path

report = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json").read_text(encoding="utf-8"))
summary = report["summary"]
print(report["status"])
print(summary["round_count"])
print(summary["success_count"])
print(summary["success_rate"])
print(summary["mean_oos_metric"])
print(summary["best_oos_metric"])
print(summary["mean_trade_count"])
print(summary["zero_trade_rounds"])
'@ | python -
```

Expected:

```text
ok
8
8
1.0
0.5725
0.68
2045.125
0
```

- [ ] **Step 4: Confirm final strategy snapshot contains the freeze condition**

Run:

```powershell
@'
import json
from pathlib import Path

manifest = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json").read_text(encoding="utf-8"))
expression = manifest["source_expression"]
code = Path(r"utility\ai_agent\WideV2Final_B_20260428.py").read_text(encoding="utf-8")
print("WideV2Final_B_20260428" in code)
print(expression in code)
print("self.Buy()" in code)
'@ | python -
```

Expected:

```text
True
True
True
```

### Task 2: Create Wide v2 MVP Freeze Report

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md`

- [ ] **Step 1: Create the MVP directory**

Run:

```powershell
New-Item -ItemType Directory -Force docs\research\condition_research\mvp
```

Expected:

```text
Directory exists or is created.
```

- [ ] **Step 2: Create the freeze report with apply_patch**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md
+# Wide v2 MVP freeze
+
+## Freeze decision
+
+- decision=FREEZE_WIDE_V2_MVP_CANDIDATE
+- frozen_at=2026-04-29
+- final_buy_strategy=WideV2Final_B_20260428
+- base_buy_strategy=WideV1Final_B_20260425
+- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
+- source_run=WideV2V5DirectV4ShortfallRecovery_20260428
+- source_candidate=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
+- source_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
+
+## Why freeze now
+
+- Wide v2 v5 direct_v4 shortfall recovery가 실제 `candidate_count=10` 검증에서 작동했다.
+- 후보 풀은 direct_v4 4개에서 recovery 포함 28개로 보강되었고, 실제 실행은 20개 후보까지 진행되었다.
+- actual row-set 기준으로 10개 대표 후보가 선택되었고 `row_set_identity_status=all_distinct`를 만족했다.
+- final best와 WFO handoff candidate가 동일하게 `cand007`로 선정되었다.
+- `WideV2Final_B_20260428` 전략 스냅샷이 생성되었고 DB reload 검증을 통과했다.
+- runtime-preflight가 `status=ok`, `failed_checks=[]`, `validation_errors=[]`로 통과했다.
+- WFO/OOS는 8개 window에서 `status=ok`로 완료되었다.
+- balanced preset과 conservative preset을 모두 통과했다.
+
+## WFO/OOS evidence
+
+- report_path=docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json
+- decision_path=docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md
+- elapsed=00:30:22.5225589
+- exit_code=0
+- round_count=8
+- success_count=8
+- success_rate=1.0
+- metric=tpi
+- mean_oos_metric=0.5725
+- best_oos_metric=0.68
+- trade_count_rounds=8
+- zero_trade_rounds=0
+- mean_trade_count=2045.125
+
+## Freeze gates
+
+| Gate | Required | Actual | Result |
+| --- | --- | --- | --- |
+| v5 recovery | direct_v4 shortfall recovers to candidate_count target | final_candidate_pool_count=28 | PASS |
+| actual row-set selection | selected_count >= 10 | actual_selected_count=10 | PASS |
+| row-set identity | representatives are distinct | row_set_identity_status=all_distinct | PASS |
+| final strategy snapshot | DB-loadable strategy snapshot | WideV2Final_B_20260428 snapshot exists | PASS |
+| runtime preflight | status=ok and no failed checks | status=ok, failed_checks=[] | PASS |
+| WFO windows | round_count >= 3 | round_count=8 | PASS |
+| WFO success rate | success_rate >= 0.60 | success_rate=1.0 | PASS |
+| WFO mean OOS metric | mean_oos_metric >= 0.00 | mean_oos_metric=0.5725 | PASS |
+| WFO average trades | mean_trade_count >= 50 | mean_trade_count=2045.125 | PASS |
+| no-trade failure | zero_trade_rounds < round_count | zero_trade_rounds=0 | PASS |
+
+## Rejected alternatives
+
+- v6/v7 후보 생성을 즉시 진행하지 않는다. WFO/OOS 기준을 통과했으므로 신규 탐색보다 MVP 종료와 재현성 고정이 우선이다.
+- `discovery research`에 WFO를 다시 붙이지 않는다. research loop는 빠른 후보 생성, WFO/OOS는 별도 최종 검증으로 분리한다.
+- 실거래 승인으로 표현하지 않는다. 이번 freeze는 MVP 개발 종료 판단이며, 실거래 전에는 post-MVP 운영 파일럿 검증이 필요하다.
+
+## Freeze meaning
+
+- 이 freeze는 Wide v2 조건식 자동 개선 MVP가 후보 생성, 후보 보강, 실제 row-set 선별, WFO/OOS 검증까지 통과했다는 기준점이다.
+- 이 freeze는 실거래 수익 보장이 아니다.
+- 다음 단계는 PR merge point 생성, 운영 재현 문서 확인, post-MVP risk backlog 및 소액 파일럿 체크리스트 작성이다.
*** End Patch
```

- [ ] **Step 3: Verify freeze report contains the required decision**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-29_wide_v2_mvp_freeze.md -Pattern "FREEZE_WIDE_V2_MVP_CANDIDATE|WideV2Final_B_20260428|mean_oos_metric=0.5725|PROCEED_TO_MVP_FREEZE"
```

Expected output contains:

```text
FREEZE_WIDE_V2_MVP_CANDIDATE
WideV2Final_B_20260428
mean_oos_metric=0.5725
```

The `PROCEED_TO_MVP_FREEZE` pattern may not appear in this file because the freeze report records the final freeze decision label. That is acceptable if the first three patterns are present.

### Task 3: Create Operational Reproduction Guide

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md`

- [ ] **Step 1: Create the reproduction guide with apply_patch**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md
+# Wide v2 operational reproduction
+
+## Purpose
+
+이 문서는 `WideV2Final_B_20260428` MVP 후보를 다른 세션에서 재현하기 위한 최소 명령어 세트다.
+
+## Constants
+
+```text
+FINAL_BUY=WideV2Final_B_20260428
+BASE_BUY=WideV1Final_B_20260425
+SELL=ResearchTest_Tick_S_090000_092800_Wide_20260419
+SOURCE_EXPRESSION=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
+START=20250101
+END=20251231
+TIMEFRAME=tick
+BETTING=20
+AVG_TIME=30
+START_TIME=90000
+END_TIME=92800
+ENGINES=32
+TRAIN_WINDOW_DAYS=120
+TEST_WINDOW_DAYS=30
+STEP_DAYS=30
+PURGE_DAYS=1
+EMBARGO_DAYS=1
+OBJECTIVE=tpi
+METHOD=grid
+MAX_ITER=1
+TIMEOUT=1200
+```
+
+## Step 1: Restore final buy strategy into strategy DB
+
+```powershell
+@'
+from pathlib import Path
+from cli.paths import DB_STRATEGY
+from cli.strategy_generator import save_strategy_to_db
+
+strategy_name = "WideV2Final_B_20260428"
+code = Path(r"utility\ai_agent\WideV2Final_B_20260428.py").read_text(encoding="utf-8")
+result = save_strategy_to_db(DB_STRATEGY, strategy_name, code, "buy")
+print(result)
+'@ | python -
+```
+
+Expected:
+
+```text
+status=ok with action created or updated
+```
+
+## Step 2: Verify strategy loads from DB
+
+```powershell
+@'
+import json
+from pathlib import Path
+from cli.paths import DB_STRATEGY
+from cli.strategy_loader import load_strategy_from_db
+
+manifest = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json").read_text(encoding="utf-8"))
+expression = manifest["source_expression"]
+result = load_strategy_from_db(DB_STRATEGY, "WideV2Final_B_20260428", "buy")
+print(result.get("status"))
+print(expression in result.get("code", ""))
+print("self.Buy()" in result.get("code", ""))
+'@ | python -
+```
+
+Expected:
+
+```text
+ok
+True
+True
+```
+
+## Step 3: Runtime preflight
+
+```powershell
+$preflight = python .\stom_backtest.py runtime-preflight --buy WideV2Final_B_20260428 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 1200
+$preflight | Set-Content -Path backtest\temp\wide_v2_mvp_freeze_preflight_20260429.json -Encoding UTF8
+if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
+```
+
+Expected:
+
+```text
+PowerShell exits 0 and the JSON file contains status=ok, failed_checks=[], validation_errors=[].
+```
+
+## Step 4: WFO window dry-run
+
+```powershell
+python .\stom_backtest.py wfo --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --dry-run -o backtest\temp\wide_v2_mvp_freeze_wfo_windows_20260429.json
+```
+
+Expected:
+
+```text
+round_count=8
+```
+
+## Step 5: Optional full WFO/OOS reproduction
+
+```powershell
+python .\stom_backtest.py wfo --buy WideV2Final_B_20260428 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --objective tpi --method grid --max-iter 1 --engines 32 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --timeout 1200 --format json -o backtest\temp\wide_v2_mvp_freeze_wfo_report_20260429.json
+```
+
+Expected based on the frozen run:
+
+```text
+status=ok
+round_count=8
+success_rate=1.0
+mean_oos_metric=0.5725
+mean_trade_count=2045.125
+zero_trade_rounds=0
+```
+
+## Step 6: Unit and regression verification
+
+```powershell
+python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
+python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
+python scripts/verify_nonrelease_sync.py
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+Expected from the frozen branch:
+
+```text
+113 passed
+195 passed
+non-release sync guard passes
+diff check prints no whitespace errors
+```
+
+## Operational caution
+
+- 이 재현 절차는 백테스트와 WFO/OOS 검증 재현 절차다.
+- 실거래 전에는 소액 파일럿, 슬리피지, 호가 체결, API 장애 대응을 별도 검증해야 한다.
+- `utility/strategy.db`는 런타임 DB이므로 Git diff 대신 `utility/ai_agent/WideV2Final_B_20260428.py` 스냅샷을 기준 artifact로 사용한다.
*** End Patch
```

- [ ] **Step 2: Verify reproduction guide has exact commands**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-29_wide_v2_operational_reproduction.md -Pattern "runtime-preflight|wfo --buy WideV2Final_B_20260428|113 passed|195 passed|mean_oos_metric=0.5725"
```

Expected output contains:

```text
runtime-preflight
wfo --buy WideV2Final_B_20260428
113 passed
195 passed
mean_oos_metric=0.5725
```

### Task 4: Create Release Checklist

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-29_wide_v2_release_checklist.md`

- [ ] **Step 1: Create release checklist with apply_patch**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/research/condition_research/mvp/2026-04-29_wide_v2_release_checklist.md
+# Wide v2 release checklist
+
+## MVP readiness
+
+- [x] Wide v2 direct_v4 shortfall recovery 구현
+- [x] direct_v4 shortfall recovery loop integration 검증
+- [x] candidate_count=10 full validation에서 후보 풀 28개 확보
+- [x] planned_execution_count=20 실행
+- [x] actual row-set 대표 후보 10개 확보
+- [x] row_set_identity_status=all_distinct 확인
+- [x] final candidate `cand007` 선택
+- [x] 최종 전략명 `WideV2Final_B_20260428` 고정
+- [x] 최종 전략 스냅샷 `utility/ai_agent/WideV2Final_B_20260428.py` 커밋
+- [x] runtime-preflight 통과
+- [x] WFO dry-run window count 8 확인
+- [x] WFO/OOS full validation 통과
+- [x] balanced preset 통과
+- [x] conservative preset 통과
+- [x] Korean PR-ready validation report 작성
+
+## Not yet release-safe for live trading
+
+- [ ] 소액 실거래 파일럿 기간 정의
+- [ ] 슬리피지와 호가 체결 차이 측정
+- [ ] 장중 네트워크/API 장애 대응 확인
+- [ ] 주문 수량, 예수금, 종목당 배팅금액 live guard 확인
+- [ ] 실거래 중지 조건과 rollback 절차 정의
+- [ ] 장 종료 후 거래 로그와 백테스트 예측 비교 템플릿 작성
+- [ ] WFO/OOS 결과를 실거래 주문 로직과 연결하기 전 risk owner 확인
+
+## Frozen artifacts
+
+| Artifact | Path |
+| --- | --- |
+| Final strategy snapshot | `utility/ai_agent/WideV2Final_B_20260428.py` |
+| WFO/OOS manifest | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json` |
+| WFO/OOS windows | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json` |
+| WFO/OOS report | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json` |
+| WFO/OOS decision | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md` |
+| MVP freeze report | `docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md` |
+| Operational reproduction | `docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md` |
+
+## Next branch after PR merge
+
+- branch=feature/wide-v2-post-mvp-risk-backlog
+- command=$writing-plans Wide v2 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성
+
+## Stop conditions
+
+- 신규 조건식 탐색은 MVP freeze PR merge 이후 별도 post-MVP backlog에서만 재개한다.
+- WFO/OOS 결과를 덮어쓰는 full rerun은 별도 브랜치와 별도 PR로만 수행한다.
+- `STOM_Version_2U_C`에 직접 커밋하지 않는다.
+- 이후 통합은 GitHub PR 생성과 PR merge 기록을 남긴다.
*** End Patch
```

- [ ] **Step 2: Verify checklist includes live-trading exclusions**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-29_wide_v2_release_checklist.md -Pattern "Not yet release-safe|소액 실거래|STOM_Version_2U_C에 직접 커밋하지 않는다|post-MVP"
```

Expected output contains:

```text
Not yet release-safe for live trading
소액 실거래 파일럿 기간 정의
STOM_Version_2U_C에 직접 커밋하지 않는다
post-MVP
```

### Task 5: Create Korean PR Body And Merge Report

**Files:**
- Create: `docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md`

- [ ] **Step 1: Create PR body with apply_patch**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md
+# Wide v2 MVP freeze 및 PR 병합 보고서
+
+## 목적
+
+Wide v2 v5 direct_v4 shortfall recovery와 WFO/OOS 검증을 통과한 `WideV2Final_B_20260428`를 MVP freeze 후보로 고정하고, 기준 브랜치 `STOM_Version_2U_C`로 병합할 PR 증거를 정리한다.
+
+## 전체 방향
+
+```text
+Wide v2 candidate_count=10 full validation
+-> direct_v4 shortfall recovery
+-> candidate pool 28
+-> executed candidates 20
+-> actual row-set representatives 10
+-> cand007 final best
+-> WideV2Final_B_20260428 permanent strategy
+-> runtime-preflight
+-> WFO/OOS 8 windows
+-> balanced/conservative pass
+-> MVP freeze
+-> PR merge point
+-> post-MVP risk backlog
+```
+
+## 변경 사항
+
+- Wide v2 MVP freeze 보고서 추가
+- Wide v2 운영 재현 명령어 문서 추가
+- Wide v2 release checklist 추가
+- Wide v2 PR merge report 본문 추가
+- WFO/OOS 검증 결과를 freeze 판단 기준으로 연결
+
+## 핵심 근거
+
+- final_buy_strategy=`WideV2Final_B_20260428`
+- base_buy_strategy=`WideV1Final_B_20260425`
+- source_candidate=`WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`
+- source_expression=`66.999 <= 시가총액 < 2_580 and 등락율 > 3.535`
+- final_candidate_pool_count=`28`
+- execution_count=`20`
+- actual_selected_count=`10`
+- row_set_identity_status=`all_distinct`
+- WFO/OOS `round_count=8`
+- WFO/OOS `success_rate=1.0`
+- WFO/OOS `mean_oos_metric=0.5725`
+- WFO/OOS `mean_trade_count=2045.125`
+- WFO/OOS `zero_trade_rounds=0`
+- balanced preset 통과
+- conservative preset 통과
+
+## 검증 계획
+
+- `python .\stom_backtest.py runtime-preflight --buy WideV2Final_B_20260428 ...`
+- `python .\stom_backtest.py wfo --dry-run ...`
+- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`
+- `python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q`
+- `python scripts/verify_nonrelease_sync.py`
+- `git diff --check --ignore-cr-at-eol HEAD`
+- `gh pr create --base STOM_Version_2U_C --head feature/wide-v2-mvp-freeze-pr-report --title "Wide v2 MVP freeze 및 PR 병합 보고서" --body-file docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md`
+
+## 병합 원칙
+
+- 기준 브랜치에 직접 커밋하지 않는다.
+- `feature/wide-v2-mvp-freeze-pr-report`에서 GitHub PR을 생성한다.
+- PR merge 후 local `STOM_Version_2U_C`는 `git pull --ff-only origin STOM_Version_2U_C`로 동기화한다.
+- raw runtime 산출물인 `backtest/temp`, `backtest/csv`, `backtest/graph`는 커밋하지 않는다.
+- `utility/strategy.db`는 런타임 DB이므로 커밋하지 않는다.
+
+## 남은 위험
+
+- MVP freeze는 실거래 수익 보장이 아니다.
+- 실거래 전에는 소액 파일럿, 슬리피지, 호가 체결, 주문 실패 대응을 별도 확인해야 한다.
+- 신규 후보 탐색은 post-MVP backlog에서 별도 브랜치와 PR로 재개한다.
+
+## 다음 단계
+
+- PR merge 후 `feature/wide-v2-post-mvp-risk-backlog` 브랜치를 생성한다.
+- 다음 명령어: `$writing-plans Wide v2 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성`
*** End Patch
```

- [ ] **Step 2: Verify PR body contains GitHub PR command**

Run:

```powershell
Select-String -Path docs\pr\2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md -Pattern "gh pr create|Wide v2 MVP freeze 및 PR 병합 보고서|post-MVP|mean_oos_metric=0.5725"
```

Expected output contains:

```text
gh pr create
Wide v2 MVP freeze 및 PR 병합 보고서
post-MVP
mean_oos_metric=0.5725
```

### Task 6: Verify Documentation And Runtime Reproduction

**Files:**
- Read: all files changed by this plan.

- [ ] **Step 1: Verify final strategy can be restored to DB from snapshot**

Run:

```powershell
@'
import json
from pathlib import Path
from cli.paths import DB_STRATEGY
from cli.strategy_generator import save_strategy_to_db
from cli.strategy_loader import load_strategy_from_db

manifest = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_manifest.json").read_text(encoding="utf-8"))
expression = manifest["source_expression"]
strategy_name = "WideV2Final_B_20260428"
code = Path(r"utility\ai_agent\WideV2Final_B_20260428.py").read_text(encoding="utf-8")
save_result = save_strategy_to_db(DB_STRATEGY, strategy_name, code, "buy")
load_result = load_strategy_from_db(DB_STRATEGY, strategy_name, "buy")
print(save_result.get("status"))
print(load_result.get("status"))
print(expression in load_result.get("code", ""))
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
$preflight = python .\stom_backtest.py runtime-preflight --buy WideV2Final_B_20260428 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 1200
$preflight | Set-Content -Path backtest\temp\wide_v2_mvp_freeze_preflight_20260429.json -Encoding UTF8
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

data = json.loads(Path(r"backtest\temp\wide_v2_mvp_freeze_preflight_20260429.json").read_text(encoding="utf-8-sig"))
print(data.get("status"))
print(data.get("failed_checks"))
print(data.get("validation_errors"))
print(data.get("strategies", {}).get("buy", {}).get("status"))
print(data.get("strategies", {}).get("sell", {}).get("status"))
'@ | python -
```

Expected:

```text
ok
[]
[]
ok
ok
```

- [ ] **Step 4: Run WFO dry-run only**

Run:

```powershell
python .\stom_backtest.py wfo --start 20250101 --end 20251231 --train-window-days 120 --test-window-days 30 --step-days 30 --purge-days 1 --embargo-days 1 --dry-run -o backtest\temp\wide_v2_mvp_freeze_wfo_windows_20260429.json
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

data = json.loads(Path(r"backtest\temp\wide_v2_mvp_freeze_wfo_windows_20260429.json").read_text(encoding="utf-8"))
print(data.get("status"))
print(data.get("round_count"))
'@ | python -
```

Expected:

```text
dry-run
8
```

- [ ] **Step 6: Verify committed WFO/OOS report metrics**

Run:

```powershell
@'
import json
from pathlib import Path

report = json.loads(Path(r"docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_wfo_oos_report.json").read_text(encoding="utf-8"))
summary = report["summary"]
print(report.get("status") == "ok")
print(summary.get("round_count") == 8)
print(summary.get("success_rate") == 1.0)
print(summary.get("mean_oos_metric") == 0.5725)
print(summary.get("mean_trade_count") == 2045.125)
print(summary.get("zero_trade_rounds") == 0)
'@ | python -
```

Expected:

```text
True
True
True
True
True
True
```

- [ ] **Step 7: Run focused WFO and strategy tests**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
```

Expected:

```text
113 passed
```

- [ ] **Step 8: Run optimizer/research regression tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

Expected:

```text
195 passed
```

- [ ] **Step 9: Run non-release sync guard**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 10: Run whitespace check**

Run:

```powershell
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
No output.
```

### Task 7: Commit MVP Freeze Documentation

**Files:**
- Stage only files listed in this task.

- [ ] **Step 1: Review changed files**

Run:

```powershell
git status --short
```

Expected includes:

```text
?? docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md
?? docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md
?? docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md
?? docs/research/condition_research/mvp/2026-04-29_wide_v2_release_checklist.md
```

- [ ] **Step 2: Stage explicit files only**

Run:

```powershell
git add docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md
git add docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md
git add docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md
git add docs/research/condition_research/mvp/2026-04-29_wide_v2_release_checklist.md
git add docs/superpowers/plans/2026-04-29-wide-v2-mvp-freeze-pr-merge-report.md
```

- [ ] **Step 3: Confirm staged files**

Run:

```powershell
git diff --cached --name-only
```

Expected exactly:

```text
docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md
docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md
docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md
docs/research/condition_research/mvp/2026-04-29_wide_v2_release_checklist.md
docs/superpowers/plans/2026-04-29-wide-v2-mvp-freeze-pr-merge-report.md
```

- [ ] **Step 4: Commit with Lore protocol**

Run:

```powershell
git commit -m "Wide v2 MVP freeze 병합 보고서를 고정한다" -m "WFO/OOS를 통과한 WideV2Final_B_20260428를 MVP freeze 후보로 선언하고 운영 재현 명령어, release checklist, PR merge report를 문서화한다. 신규 후보 생성은 중단하고 후속 작업은 post-MVP risk backlog로 분리한다." -m "Constraint: 이번 단계는 신규 조건식 탐색이 아니라 WFO/OOS 통과 artifact의 freeze 문서화다
Constraint: 기준 브랜치에는 직접 커밋하지 않고 GitHub PR merge 기록을 남긴다
Rejected: v6/v7 후보 생성으로 즉시 진행 | WFO/OOS 기준을 통과했으므로 MVP 종료 문서화가 우선이다
Confidence: high
Scope-risk: narrow
Directive: 실거래 전에는 post-MVP risk backlog와 소액 파일럿 체크리스트를 별도 PR로 진행한다
Tested: strategy snapshot DB restore, runtime-preflight, WFO dry-run, committed WFO metric check, focused pytest, optimizer regression pytest, verify_nonrelease_sync, git diff check
Not-tested: live trading execution"
```

Expected:

```text
Git exits 0 and prints a commit summary for "Wide v2 MVP freeze 병합 보고서를 고정한다".
```

### Task 8: Push Branch And Create GitHub PR

**Files:**
- Read: `docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md`

- [ ] **Step 1: Verify GitHub CLI auth**

Run:

```powershell
gh auth status
```

Expected:

```text
Logged in to github.com
```

If `gh auth status` exits nonzero, stop and report that PR creation is blocked by missing GitHub authentication. Do not use local `git merge --no-ff` as a substitute unless the user explicitly redirects the integration method.

- [ ] **Step 2: Push the feature branch**

Run:

```powershell
git push -u origin feature/wide-v2-mvp-freeze-pr-report
```

Expected:

```text
branch 'feature/wide-v2-mvp-freeze-pr-report' set up to track 'origin/feature/wide-v2-mvp-freeze-pr-report'
```

- [ ] **Step 3: Create the GitHub PR**

Run:

```powershell
gh pr create --base STOM_Version_2U_C --head feature/wide-v2-mvp-freeze-pr-report --title "Wide v2 MVP freeze 및 PR 병합 보고서" --body-file docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md
```

Expected:

```text
https://github.com/Py-CI-Park/STOM_V/pull/숫자
```

- [ ] **Step 4: Record PR metadata locally**

Run:

```powershell
gh pr view --json number,url,state,mergeStateStatus,reviewDecision,baseRefName,headRefName --jq '"PR #\(.number) \(.url) state=\(.state) base=\(.baseRefName) head=\(.headRefName) mergeState=\(.mergeStateStatus) review=\(.reviewDecision)"'
```

Expected:

```text
PR #숫자 https://github.com/Py-CI-Park/STOM_V/pull/숫자 state=OPEN base=STOM_Version_2U_C head=feature/wide-v2-mvp-freeze-pr-report
```

### Task 9: Merge PR And Sync Local Base

**Files:**
- No file edits.

- [ ] **Step 1: Merge the PR through GitHub**

Run:

```powershell
gh pr merge --merge --delete-branch=false --subject "Wide v2 MVP freeze 및 PR 병합 보고서" --body "WFO/OOS 통과 후보 WideV2Final_B_20260428를 MVP freeze artifact로 문서화하고 PR merge point를 고정한다."
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
git log --oneline --decorate -8
```

Expected includes:

```text
Wide v2 MVP freeze 병합 보고서를 고정한다
Wide v2 WFO/OOS 검증 통과를 기록한다
Wide v2 direct_v4 복구 검증 결과를 기록한다
```

- [ ] **Step 4: Run post-merge smoke verification**

Run:

```powershell
python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
113 passed
No whitespace errors.
```

### Task 10: Create Next Branch

**Files:**
- No file edits.

- [ ] **Step 1: Create post-MVP risk backlog branch**

Run:

```powershell
git switch -c feature/wide-v2-post-mvp-risk-backlog
```

Expected:

```text
Switched to a new branch 'feature/wide-v2-post-mvp-risk-backlog'
```

- [ ] **Step 2: Report next command**

Report this exact next command:

```text
$writing-plans Wide v2 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성
```

---

## Self-Review

Spec coverage:

- `Wide v2 MVP freeze`: covered by Task 2 and Task 4.
- `운영 재현 문서`: covered by Task 3.
- `PR 병합 보고서`: covered by Task 5, Task 8, and Task 9.
- WFO/OOS result grounding: covered by Task 1 and Task 6.
- Existing PR routine: uses GitHub PR creation and merge instead of direct base-branch commit.
- Protected artifact policy: covered in Scope and Task 7.
- Next stage: covered by Task 10.

Red-flag scan:

- Every created file path is exact.
- Every command has an expected result.
- The plan does not rely on undefined helper scripts.
- The plan uses explicit `git add` paths and avoids `git add -A`.
- The plan excludes protected runtime outputs and `utility/strategy.db`.
- No broad refactor or new dependency is introduced.

Type and field consistency:

- WFO summary fields match `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json`: `round_count`, `success_count`, `success_rate`, `mean_oos_metric`, `best_oos_metric`, `mean_trade_count`, `zero_trade_rounds`.
- Final strategy name is consistently `WideV2Final_B_20260428`.
- Base strategy is consistently `WideV1Final_B_20260425`.
- Base branch is consistently `STOM_Version_2U_C`.
- Feature branch is consistently `feature/wide-v2-mvp-freeze-pr-report`.

## Execution Recommendation

Recommended execution mode: Inline Execution using `executing-plans`.

Reason:

- Tasks are sequential and depend on committed docs before PR creation.
- The only external side effect is GitHub PR creation and merge; this should stay in one session for traceability.
- Subagents are unnecessary unless the user explicitly requests a separate documentation review lane.
