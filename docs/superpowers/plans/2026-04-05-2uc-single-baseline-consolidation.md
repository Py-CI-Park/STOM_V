# 2U_C 단일 기준선 통합 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `STOM_Version_2U_C_CLI_v267`의 custom/CLI/runtime 변경을 `STOM_Version_2U_C`로 흡수해 `2U_C`를 단일 기준선으로 승격하고, 코드·테스트·문서·전파 전략을 모두 그 기준선에 맞춘다.

**Architecture:** 구현은 `C:/System_Trading/STOM/STOM_V.wt-2uc`에서 시작하는 일회성 통합 브랜치 `integration/adopt-cli-v267-into-2uc`에서 수행한다. 내용 채택은 `CLI_v267` 우선, 기준선 소유권은 `2U_C` 유지로 잡고, `2U_C`에만 있던 후행 안정화 수정을 검증 체크리스트와 선택적 재적용으로 복구한다. 마지막에 문서와 worktree 운영 규칙을 `V2 -> 2U -> 2U_C -> research/init` 기준으로 재작성한다.

**Tech Stack:** Git worktree, PowerShell, Python 3.11, pytest, STOM runtime/GUI modules, non-release sync verifier

---

## File Structure

이번 통합에서 직접 다루는 핵심 파일은 아래와 같다.

- `C:/System_Trading/STOM/STOM_V.wt-2uc/ui/ui_mainwindow.py`
  - `2U_C` 기준선의 UI import/wiring 정합성을 먼저 복구하는 파일
- `C:/System_Trading/STOM/STOM_V.wt-2uc/backtest/back_static.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/backtest/backengine_base.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/backtest/back_subtotal.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/backtest/backtest.py`
  - `CLI_v267` 채택 시 공용 런타임 계약을 수동 감사해야 하는 핵심 백테스트 파일
- `C:/System_Trading/STOM/STOM_V.wt-2uc/utility/setting.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/utility/setting_base.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/utility/lazy_imports.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/utility/telegram_bot.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/utility/webcrawling.py`
  - 비정식 워크트리 정책과 네트워크 계약을 보존해야 하는 핵심 공용 유틸리티
- `C:/System_Trading/STOM/STOM_V.wt-2uc/cli/*`
  - 통합 후 `2U_C`가 공식 소유할 CLI 표면
- `C:/System_Trading/STOM/STOM_V.wt-2uc/tests/unit/test_ui_jisu_cleanup.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/tests/unit/test_backtest_result_expansion.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/tests/unit/test_verify_nonrelease_sync.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/tests/unit/test_telegram_network_noise.py`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/tests/unit/test_webcrawling_network_noise.py`
  - 통합 완료 기준을 잠그는 핵심 테스트
- `C:/System_Trading/STOM/STOM_V.wt-2uc/AGENTS.md`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/CLAUDE.md`
- `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/WORKTREE_STRATEGY.md`
- `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`
  - 단일 기준선과 전파 체계를 다시 정의할 메타 문서
- `C:/System_Trading/STOM/STOM_V.wt-2uc/docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
  - 통합 충돌 목록, 재적용 항목, 은퇴 처리까지 기록할 실행 로그

통합 중 비교 대상으로만 사용하는 기준 파일은 아래와 같다.

- `C:/System_Trading/STOM/STOM_V.wt-dev/docs/update_log/2026-04-04_v274_v277_cli_v267_baseline_note.md`
- `C:/System_Trading/STOM/STOM_V.wt-dev/cli/*`
- `C:/System_Trading/STOM/STOM_V.wt-dev/tests/unit/test_backtest_result_expansion.py`

---

### Task 1: 통합 작업장 준비와 기준선 기록

**Files:**
- Create: `docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
- Modify: 없음
- Test: `tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module`

- [ ] **Step 1: 현재 `2U_C` 실패를 기준선으로 고정**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2uc switch STOM_Version_2U_C
python -m pytest tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module -v
```

Expected: `ModuleNotFoundError: No module named 'ui.ui_activated_coin_stg'`로 FAIL

- [ ] **Step 2: 통합 브랜치 생성**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2uc switch -c integration/adopt-cli-v267-into-2uc
git -C C:\System_Trading\STOM\STOM_V.wt-2uc branch --show-current
```

Expected: `integration/adopt-cli-v267-into-2uc`

- [ ] **Step 3: 실행 로그 파일 생성**

```md
# 2026-04-05 2U_C 단일 기준선 통합 실행 로그

## Baseline
- source branch: `STOM_Version_2U_C`
- absorbed branch: `STOM_Version_2U_C_CLI_v267`
- integration branch: `integration/adopt-cli-v267-into-2uc`

## Pre-merge failures
- `tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module`
- `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`

## Conflict inventory
- 초기 생성 시 비워 두고, Task 3에서 실제 충돌 파일 목록으로 덮어쓴다.

## Reapplied 2U_C-only fixes
- 초기 생성 시 비워 두고, Task 4에서 실제 재적용 커밋 목록으로 덮어쓴다.

## Final verification
- 초기 생성 시 비워 두고, Task 7에서 실제 검증 결과로 덮어쓴다.
```

- [ ] **Step 4: 실행 로그 스켈레톤 커밋**

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2uc add -- docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md
@'
통합 실행 로그 기준선 추가

## 배경
- `2U_C` 단일 기준선 통합 작업을 별도 통합 브랜치에서 추적할 실행 로그가 필요했다.
- 현재 실패와 충돌, 재적용 항목을 한 곳에 기록해야 이후 검증과 승격 판단이 가능하다.

## 변경 사항
- 통합 브랜치 정보와 사전 실패 목록을 담은 실행 로그 파일을 추가했다.

## 검증
- 통합 브랜치 생성 확인
- 로그 파일 생성 확인

Constraint: 통합 이력은 코드 변경과 별도로 남아야 함
Rejected: 메모 없이 터미널 기록만 사용 | 이후 검증 근거로 재사용하기 어려움
Confidence: 높음
Scope-risk: 좁음
Directive: 이후 merge-tree 충돌 목록과 재적용 항목을 이 로그에 계속 누적할 것
Tested: 통합 브랜치 생성, 로그 파일 생성
Not-tested: 실제 머지/코드 통합
'@ | git -C C:\System_Trading\STOM\STOM_V.wt-2uc commit -F -
```

---

### Task 2: `2U_C` 시작점의 UI import 회귀 복구

**Files:**
- Modify: `ui/ui_mainwindow.py`
- Modify: `docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
- Test: `tests/unit/test_ui_jisu_cleanup.py`

- [ ] **Step 1: failing test 재확인**

Run:

```powershell
python -m pytest tests/unit/test_ui_jisu_cleanup.py -v
```

Expected: `test_ui_mainwindow_import_succeeds_without_deleted_jisu_module` 1건 FAIL

- [ ] **Step 2: 삭제된 import를 현재 활성 모듈로 교체**

`ui/ui_mainwindow.py` 상단 import 블록을 아래처럼 맞춘다.

```python
from ui.set_dialog_formula import SetDialogFormula
from ui.set_home_tap import SetHomeTap
from ui.set_style import dict_set
from ui import ui_activated_stg

from ui.ui_etc import *
from ui.ui_draw_chart_db import *
from ui.ui_activated_back import *
from ui.ui_show_dialog import *
```

그리고 아래 두 줄은 제거한다.

```python
from ui.ui_activated_coin_stg import *
from ui.ui_activated_stock_stg import *
```

- [ ] **Step 3: 회귀 테스트 통과 확인**

Run:

```powershell
python -m pytest tests/unit/test_ui_jisu_cleanup.py -v
```

Expected: `2 passed`

- [ ] **Step 4: 실행 로그에 시작점 복구 반영**

```md
## Pre-merge fixes
- `ui/ui_mainwindow.py`에서 삭제된 `ui_activated_coin_stg`/`ui_activated_stock_stg` import 제거
- `from ui import ui_activated_stg`로 현재 모듈 구조에 정렬
```

- [ ] **Step 5: 시작점 복구 커밋**

```powershell
git add -- ui/ui_mainwindow.py docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md
@'
2U_C 시작점의 ui import 회귀를 복구

## 배경
- `2U_C` 기준선 자체가 삭제된 `ui_activated_coin_stg` import를 참조해 단위 테스트가 실패하고 있었다.
- 통합 작업은 깨진 시작점이 아니라 최소한의 정상 기준선에서 시작해야 했다.

## 변경 사항
- `ui/ui_mainwindow.py` import를 현재 구조에 맞게 `ui_activated_stg`로 정렬했다.
- 실행 로그에 사전 복구 내역을 추가했다.

## 검증
- `python -m pytest tests/unit/test_ui_jisu_cleanup.py -v`

Constraint: 통합 전 기준선 실패를 먼저 줄여야 충돌 원인 분리가 쉬움
Rejected: 통합 후 한 번에 수정 | 머지 회귀와 기존 회귀를 구분하기 어려움
Confidence: 높음
Scope-risk: 좁음
Directive: 이후 머지 충돌 해결 시 이 import 블록이 다시 예전 모듈명으로 돌아가지 않게 확인할 것
Tested: `tests/unit/test_ui_jisu_cleanup.py`
Not-tested: 전체 unit suite
'@ | git commit -F -
```

---

### Task 3: `CLI_v267` 흡수와 1차 충돌 정리

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `backtest/back_static.py`
- Modify: `backtest/back_subtotal.py`
- Modify: `backtest/backengine_base.py`
- Modify: `backtest/backengine_base_oms.py`
- Modify: `backtest/backtest.py`
- Modify: `research/auxiliary_indicator/smart_vwap_bands.py`
- Modify: `stom.bat`
- Modify: `stom_coin.bat`
- Modify: `stom_future.bat`
- Modify: `stom_stock.bat`
- Modify: `ui/ui_button_clicked_dialog_backengine.py`
- Modify: `ui/ui_button_clicked_editer_coin.py`
- Modify: `ui/ui_button_clicked_editer_stock.py`
- Modify: `ui/ui_mainwindow.py`
- Modify: `utility/static.py`
- Modify: `utility/telegram_bot.py`
- Modify: `utility/webcrawling.py`
- Modify: `docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
- Test: `git merge-tree`, `git status --short`

- [ ] **Step 1: merge-tree 충돌 목록을 실행 로그에 기록**

Run:

```powershell
$base = git merge-base STOM_Version_2U_C STOM_Version_2U_C_CLI_v267
git merge-tree $base STOM_Version_2U_C STOM_Version_2U_C_CLI_v267 | Out-File -Encoding utf8 merge-tree.txt
```

`docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`에 아래 항목을 실제 충돌 목록으로 채운다.

```md
## Conflict inventory
- AGENTS.md
- CLAUDE.md
- backtest/back_static.py
- backtest/back_subtotal.py
- backtest/backengine_base.py
- backtest/backengine_base_oms.py
- backtest/backtest.py
- research/auxiliary_indicator/smart_vwap_bands.py
- stom.bat
- stom_coin.bat
- stom_future.bat
- stom_stock.bat
- ui/ui_button_clicked_dialog_backengine.py
- ui/ui_button_clicked_editer_coin.py
- ui/ui_button_clicked_editer_stock.py
- ui/ui_mainwindow.py
- utility/static.py
- utility/telegram_bot.py
- utility/webcrawling.py
```

- [ ] **Step 2: `CLI_v267`를 내용 우선으로 머지**

Run:

```powershell
git merge --no-ff -X theirs STOM_Version_2U_C_CLI_v267
```

Expected: 자동 병합 + 일부 수동 충돌 정리 필요

- [ ] **Step 3: 코드 충돌은 `CLI_v267` 우선, 메타 문서는 `ours` 우선으로 정리**

Run:

```powershell
git checkout --theirs -- backtest/back_static.py backtest/back_subtotal.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backtest.py
git checkout --theirs -- research/auxiliary_indicator/smart_vwap_bands.py stom.bat stom_coin.bat stom_future.bat stom_stock.bat
git checkout --theirs -- ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py ui/ui_mainwindow.py
git checkout --theirs -- utility/static.py utility/telegram_bot.py utility/webcrawling.py
git checkout --ours -- AGENTS.md CLAUDE.md
git add -- backtest/back_static.py backtest/back_subtotal.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backtest.py
git add -- research/auxiliary_indicator/smart_vwap_bands.py stom.bat stom_coin.bat stom_future.bat stom_stock.bat
git add -- ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py ui/ui_mainwindow.py
git add -- utility/static.py utility/telegram_bot.py utility/webcrawling.py AGENTS.md CLAUDE.md
```

`ui/ui_mainwindow.py`는 아래 import 형태가 유지되는지 다시 확인한다.

```python
from ui.set_home_tap import SetHomeTap
from ui.set_style import dict_set
from ui import ui_activated_stg
```

- [ ] **Step 4: 작업 트리에 남은 충돌이 없는지 확인**

Run:

```powershell
git status --short
```

Expected: `UU` 항목 없음

- [ ] **Step 5: 1차 흡수 체크포인트 커밋**

```powershell
git add -- docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md
@'
CLI_v267 기준 내용을 2U_C 통합 브랜치에 1차 흡수

## 배경
- 단일 기준선 전략상 `CLI_v267`의 실질 내용을 `2U_C` 통합 브랜치로 먼저 가져와야 했다.
- 공용 코드와 메타 문서를 같은 규칙으로 다루면 정리 비용이 커져 파일군별 충돌 원칙을 분리했다.

## 변경 사항
- 공용 코드/CLI 관련 충돌 파일은 `CLI_v267` 내용을 우선 채택했다.
- 메타 문서는 이후 목표 상태에 맞게 재작성하기 위해 임시로 `ours` 기준을 유지했다.
- merge-tree 기반 충돌 목록을 실행 로그에 기록했다.

## 검증
- `git status --short`에서 `UU` 항목 없음 확인

Constraint: 기준선 소유권은 `2U_C`, 내용 채택은 `CLI_v267` 우선
Rejected: 전체 파일 일괄 `theirs` 채택 | 운영 문서까지 같이 덮어써 이후 재작성 범위가 불명확해짐
Confidence: 중간
Scope-risk: 넓음
Directive: 이 커밋 직후 반드시 `2U_C` 후행 안정화 재주입과 verifier 재확인을 수행할 것
Tested: merge-tree 충돌 목록 기록, `git status --short`
Not-tested: runtime verifier, unit tests
'@ | git commit -F -
```

---

### Task 4: `2U_C` 후행 안정화 수정 재주입

**Files:**
- Modify: `utility/telegram_bot.py`
- Modify: `utility/webcrawling.py`
- Modify: `utility/setting.py`
- Modify: `utility/setting_base.py`
- Modify: `utility/lazy_imports.py`
- Modify: `scripts/verify_nonrelease_sync.py`
- Modify: `tests/unit/test_verify_nonrelease_sync.py`
- Modify: `tests/unit/test_telegram_network_noise.py`
- Modify: `tests/unit/test_webcrawling_network_noise.py`
- Modify: `docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
- Test: `python scripts/verify_nonrelease_sync.py`

- [ ] **Step 1: 통합 직후 verifier 실행**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected: 실패하더라도 누락 계약 항목이 메시지로 드러남

- [ ] **Step 2: `2U_C` 후행 안정화 커밋을 재적용**

Run:

```powershell
git cherry-pick -n 8c0d1558 b18cb168 249a8514 10edf571 96265af4 1d116161 23cdce8e 5a0c5859
```

Expected:

- 이미 반영된 패치는 empty 또는 no-op일 수 있음
- 빈 패치는 `git cherry-pick --skip`로 넘김
- 충돌 시 아래 파일군만 수동 정리

```text
utility/setting.py
utility/setting_base.py
utility/lazy_imports.py
utility/telegram_bot.py
utility/webcrawling.py
scripts/verify_nonrelease_sync.py
tests/unit/test_verify_nonrelease_sync.py
tests/unit/test_telegram_network_noise.py
tests/unit/test_webcrawling_network_noise.py
```

- [ ] **Step 3: verifier 기준이 되는 코드 조각 확인**

아래 정책 조각이 유지되는지 확인한다.

```python
# 비정식 워크트리에서는 시리얼키 UI/저장을 차단한다.
if is_nonrelease_worktree():
    serial_key = ''
```

```python
# 네트워크 실패는 timeout/cancellation guard를 통해 정리한다.
if self._stop_requested:
    return
```

- [ ] **Step 4: verifier 재실행**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected: 모든 가드레일 검사 통과

- [ ] **Step 5: 실행 로그 갱신**

```md
## Reapplied 2U_C-only fixes
- 8c0d1558: 텔레그램 런타임 계약 복구
- b18cb168: 텔레그램 저장/종료 경로 정리
- 249a8514: 비정식 워크트리 시리얼키 구조 제거
- 10edf571: non-release sync verifier 확장
- 96265af4: telegram/webcrawling runtime contract
- 1d116161: webcrawling runtime contract test lock
- 23cdce8e: webcrawling timeout contract
- 5a0c5859: webcrawling legacy compatibility
```

- [ ] **Step 6: 안정화 재주입 커밋**

```powershell
git add -- utility/setting.py utility/setting_base.py utility/lazy_imports.py utility/telegram_bot.py utility/webcrawling.py
git add -- scripts/verify_nonrelease_sync.py tests/unit/test_verify_nonrelease_sync.py tests/unit/test_telegram_network_noise.py tests/unit/test_webcrawling_network_noise.py
git add -- docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md
@'
2U_C 후행 안정화 계약을 통합 브랜치에 재주입

## 배경
- `CLI_v267` 우선 채택 이후 `2U_C`에만 있던 가드레일과 네트워크 계약이 일부 약화될 수 있었다.
- 단일 기준선 승격 전 verifier 기준을 먼저 복구해야 했다.

## 변경 사항
- 시리얼키 차단, 텔레그램/webcrawling 런타임 계약, non-release verifier 관련 후행 수정을 통합 브랜치에 재반영했다.
- 실행 로그에 재적용한 커밋 근거를 남겼다.

## 검증
- `python scripts/verify_nonrelease_sync.py`

Constraint: `CLI_v267` 내용을 채택하더라도 `2U_C` 후행 안정화 계약은 잃으면 안 됨
Rejected: verifier 없이 수동 육안 확인만 수행 | 누락 계약을 놓칠 위험이 큼
Confidence: 중간
Scope-risk: 보통
Directive: 이후 unit suite 실패를 수정하더라도 verifier가 다시 깨지지 않게 먼저 고정할 것
Tested: `python scripts/verify_nonrelease_sync.py`
Not-tested: 전체 unit suite
'@ | git commit -F -
```

---

### Task 5: 남은 unit 실패 복구와 전체 테스트 green

**Files:**
- Modify: `tests/unit/test_backtest_result_expansion.py`
- Modify: `backtest/backtest.py` (필요할 때만)
- Modify: 추가 실패가 발생한 파일 전부
- Test: `tests/unit/test_backtest_result_expansion.py`, `tests/unit/test_ui_jisu_cleanup.py`, `tests/unit/`

- [ ] **Step 1: 알려진 failing test 먼저 재현**

Run:

```powershell
python -m pytest tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db -v
```

Expected: `SystemExit`로 FAIL

- [ ] **Step 2: 테스트를 현재 런타임 계약에 맞게 수정**

`tests/unit/test_backtest_result_expansion.py`의 직접 호출부를 아래처럼 바꾼다.

```python
    # Report는 CSV/DB 기록 후 종료 시그널로 SystemExit를 발생시킨다.
    with pytest.raises(SystemExit):
        total.Report(list_tsg, arry_bct)
```

`backtest/backtest.py`의 아래 종료 계약은 유지한다.

```python
        self.mq.put(f'{self.backname} 완료')
        time.sleep(1)
        sys.exit()
```

- [ ] **Step 3: 타깃 테스트 재실행**

Run:

```powershell
python -m pytest tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db -v
python -m pytest tests/unit/test_ui_jisu_cleanup.py -v
```

Expected: 둘 다 PASS

- [ ] **Step 4: 전체 unit suite 실행**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected: 전체 PASS

- [ ] **Step 5: 테스트 green 복구 커밋**

```powershell
git add -- tests/unit/test_backtest_result_expansion.py
@'
통합 기준선의 unit 실패를 해소

## 배경
- 통합 전 양쪽 브랜치에 이미 존재하던 실패를 그대로 두면 단일 기준선 승격 의미가 없다.
- `backtest.Total.Report`는 종료 시그널로 `SystemExit`를 발생시키는 현재 런타임 계약을 유지해야 한다.

## 변경 사항
- `test_backtest_result_expansion`이 `SystemExit`를 현재 계약으로 받아들이도록 수정했다.
- 전체 unit suite를 기준선 통과 상태로 복구했다.

## 검증
- `python -m pytest tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db -v`
- `python -m pytest tests/unit/test_ui_jisu_cleanup.py -v`
- `python -m pytest tests/unit/ -q`

Constraint: 종료 계약을 코드에서 제거하지 않고 테스트를 맞추는 것이 최소 변경
Rejected: `backtest.Report`에서 `sys.exit()` 제거 | 기존 런타임 계약을 깨뜨릴 수 있음
Confidence: 중간
Scope-risk: 보통
Directive: 이후 backtest 관련 테스트는 종료 계약과 파일 기록 계약을 함께 검증할 것
Tested: targeted pytest, full unit pytest
Not-tested: 수동 GUI 실행
'@ | git commit -F -
```

---

### Task 6: 단일 기준선 문서와 전파 전략 재작성

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/WORKTREE_STRATEGY.md`
- Modify: `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`
- Modify: `docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
- Test: `rg` 검색으로 구 체인/구 브랜치 참조 확인

- [ ] **Step 1: `CLAUDE.md`를 단일 기준선 모델로 갱신**

상단 핵심 블록을 아래 의미로 바꾼다.

```md
> **워크트리 위치**: `STOM_V.wt-dev/`
> **브랜치 역할**: `STOM_Version_2U_C` 단일 기준선 작업 레인
```

그리고 역할/전파 설명은 아래 기준으로 정리한다.

```md
V2 -> 2U -> 2U_C -> research/init
```

- [ ] **Step 2: `AGENTS.md`의 브랜치 역할과 동기화 예시를 `2U_C` 단일 기준선으로 수정**

유지할 핵심 표현:

```md
`STOM_Version_2U_C`는 커스텀 개발과 CLI 자동화를 모두 포함한 단일 기준선 브랜치입니다.
업스트림(V2) -> 2U(pyd→py) -> 2U_C(커스텀+CLI) -> research/init 순서로 전파됩니다.
```

- [ ] **Step 3: `docs/WORKTREE_STRATEGY.md`를 새 worktree 운영 규칙으로 재작성**

최소한 아래 부분이 바뀌어야 한다.

```md
### 4.3 STOM_V.wt-dev/ — 주력 개발

**홈 브랜치**: `STOM_Version_2U_C`
**역할**: custom + CLI 단일 기준선 작업 레인
```

그리고 옛 예시인 `git switch STOM_Version_2U_C_CLI_v258`/`CLI_v258`는 제거한다.

- [ ] **Step 4: 상위 저장소의 `docs/UPSTREAM_SYNC_STRATEGY.md`를 새 전파 체인으로 수정**

유지할 핵심 문구:

```text
C:/System_Trading/STOM/
├── STOM_V/            -> STOM_Version_2
├── STOM_V.wt-2u/      -> STOM_Version_2U
├── STOM_V.wt-2uc/     -> STOM_Version_2U_C
├── STOM_V.wt-dev/     -> STOM_Version_2U_C
└── STOM_V.wt-lab/     -> research/init
```

```text
V2 -> 2U -> 2U_C -> research/init
```

- [ ] **Step 5: 구 레인 참조 제거 검증**

Run:

```powershell
rg -n "CLI_v267|CLI_v258|V2 -> 2U -> 2U_C -> CLI_v267" AGENTS.md CLAUDE.md docs/WORKTREE_STRATEGY.md C:\System_Trading\STOM\STOM_V\docs\UPSTREAM_SYNC_STRATEGY.md
```

Expected: active guidance 문서에서는 retire note 외 참조 없음

- [ ] **Step 6: 문서 재정의 커밋**

```powershell
git add -- AGENTS.md CLAUDE.md docs/WORKTREE_STRATEGY.md
git add -- C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md
git add -- docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md
@'
단일 기준선 운영 문서와 전파 전략을 재정의

## 배경
- 코드 기준선 통합 후에도 문서가 예전 `2U_C -> CLI_v267` 체인을 유지하면 이후 작업자가 잘못된 운영 규칙을 따르게 된다.
- 완료 조건에는 코드뿐 아니라 브랜치 역할, worktree 전략, 전파 체계의 일치가 포함된다.

## 변경 사항
- `AGENTS.md`, `CLAUDE.md`, `docs/WORKTREE_STRATEGY.md`, `docs/UPSTREAM_SYNC_STRATEGY.md`를 `2U_C` 단일 기준선 기준으로 갱신했다.
- 실행 로그에 문서 재정의 단계를 반영했다.

## 검증
- `rg -n "CLI_v267|CLI_v258|V2 -> 2U -> 2U_C -> CLI_v267" AGENTS.md CLAUDE.md docs/WORKTREE_STRATEGY.md C:\System_Trading\STOM\STOM_V\docs\UPSTREAM_SYNC_STRATEGY.md`

Constraint: 운영 문서는 코드 기준선과 동시에 갱신돼야 함
Rejected: 코드 통합 후 문서 사후 정리 | 다음 작업자가 구 규칙을 그대로 따를 위험이 큼
Confidence: 중간
Scope-risk: 보통
Directive: retire 대상 브랜치 이름은 실행 로그나 업데이트 로그에서만 역사 보존용으로 언급할 것
Tested: `rg` 기반 active guidance 검색
Not-tested: 문서 외부 링크 클릭 확인
'@ | git commit -F -
```

---

### Task 7: 최종 승격과 worktree 전환

**Files:**
- Modify: `docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`
- Modify: 필요 시 `docs/update_log/2026-04-05_2uc_single_baseline_promotion_note.md`
- Test: `python scripts/verify_nonrelease_sync.py`, `python -m pytest tests/unit/ -q`, `git status -sb`

- [ ] **Step 1: 최종 verifier + full unit 재확인**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
python -m pytest tests/unit/ -q
git status -sb
```

Expected:

- verifier PASS
- unit PASS
- `backtest/graph/` 외 예상 밖 변경 없음

- [ ] **Step 2: 실행 로그에 최종 검증 결과 기록**

```md
## Final verification
- `python scripts/verify_nonrelease_sync.py` : PASS
- `python -m pytest tests/unit/ -q` : PASS
- `git status -sb` : expected clean state (allow `backtest/graph/` result data)
```

- [ ] **Step 3: 통합 브랜치를 `2U_C`로 승격**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2uc switch STOM_Version_2U_C
git -C C:\System_Trading\STOM\STOM_V.wt-2uc merge --no-ff integration/adopt-cli-v267-into-2uc
```

Expected: merge commit 생성

- [ ] **Step 4: `wt-dev` 작업 기준을 `2U_C`로 전환**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-dev switch STOM_Version_2U_C
git -C C:\System_Trading\STOM\STOM_V.wt-dev status -sb
```

Expected: `## STOM_Version_2U_C...origin/STOM_Version_2U_C`

- [ ] **Step 5: `CLI_v267` retire 처리 기록**

`docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md`에 아래 문구를 추가한다.

```md
## Retirement note
- `STOM_Version_2U_C_CLI_v267`는 역사 보존용 브랜치로만 유지한다.
- active development baseline은 `STOM_Version_2U_C`다.
```

- [ ] **Step 6: 승격 완료 커밋**

```powershell
git add -- docs/update_log/2026-04-05_2uc_single_baseline_consolidation_execution_log.md
@'
2U_C를 단일 기준선으로 승격

## 배경
- 통합 브랜치에서 검증을 끝낸 뒤 `2U_C`를 custom + CLI 단일 기준선으로 승격해야 했다.
- `wt-dev`의 기본 작업 기준과 전파 체계도 최종 상태로 닫아야 했다.

## 변경 사항
- 통합 브랜치를 `STOM_Version_2U_C`에 병합했다.
- `wt-dev` 작업 기준을 `2U_C`로 전환하고 `CLI_v267`를 retire 대상으로 기록했다.

## 검증
- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
- `git status -sb`

Constraint: 단일 기준선 승격은 코드/문서/검증/운영 전환이 동시에 끝나야 의미가 있음
Rejected: 브랜치만 병합하고 worktree 전환은 사후 처리 | 운영 기준이 두 개로 남아 혼란을 키움
Confidence: 중간
Scope-risk: 넓음
Directive: 이후 feature 작업은 기본적으로 `STOM_Version_2U_C`에서 분기하고, 별도 CLI 전용 장기 레인은 다시 만들지 말 것
Tested: verifier, full unit suite, branch status
Not-tested: 수동 앱 실행, `research/init` 전파
'@ | git commit -F -
```

---

## Self-Review

### Spec coverage

- 단일 기준선 목표: Task 3, Task 7
- `CLI_v267` 흡수 + `2U_C` 유지: Task 3
- `2U_C` 후행 안정화 재주입: Task 4
- 기존 unit 실패 해소: Task 2, Task 5
- 문서/전파 전략 갱신: Task 6
- `wt-dev` 기본 작업 기준 변경 + `CLI_v267` retire: Task 7

### Placeholder scan

- 금지어 패턴 없음
- 실행 로그 파일명, 브랜치명, 테스트명, 명령어를 모두 구체화함

### Type consistency

- 통합 브랜치명은 전 구간에서 `integration/adopt-cli-v267-into-2uc`
- 최종 기준선은 전 구간에서 `STOM_Version_2U_C`
- retire 대상은 전 구간에서 `STOM_Version_2U_C_CLI_v267`
