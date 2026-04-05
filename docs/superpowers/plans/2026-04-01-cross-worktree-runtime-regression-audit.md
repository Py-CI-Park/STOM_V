# Cross-Worktree Runtime Regression Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `wt-dev`에서 해결한 `V2.70 ~ V2.73` 런타임 회귀를 한글 RCA 문서와 코드 커밋으로 고정하고, 공식 `STOM_Version_2`를 제외한 워크트리들에 동일 결함이 있는지 감사한 뒤 필요한 곳만 최소 반영한다.

**Architecture:** `wt-dev`를 기준 패치(worktree-of-truth)로 삼는다. 먼저 `wt-dev`의 증상, 원인, 해결, 검증을 한글 문서와 테스트로 잠근 뒤, `STOM_Version_2U`, `STOM_Version_2U_C`, `research/init`를 동일 체크리스트로 읽기 전용 감사한다. 동일 결함이 실제로 확인된 워크트리만 같은 최소 수정과 검증을 적용하고, 모든 판정 결과를 하나의 감사 문서 표에 축적한다.

**Tech Stack:** Python 3.11, PyQt5/QThread, multiprocessing, pytest, PowerShell, git worktree, ripgrep

---

## File Structure

- Create: `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`
- Create: `docs/superpowers/plans/2026-04-01-cross-worktree-runtime-regression-audit.md`
- Modify: `ui/ui_mainwindow.py`
- Modify: `ui/ui_process_kill.py`
- Modify: `utility/static.py`
- Modify: `utility/webcrawling.py`
- Modify: `tests/unit/test_static_compat.py`
- Modify: `tests/unit/test_ui_jisu_cleanup.py`
- Create: `tests/unit/test_ui_runtime_wiring.py`
- Audit-only target roots:
  - `C:\System_Trading\STOM\STOM_V.wt-2u`
  - `C:\System_Trading\STOM\STOM_V.wt-2uc`
  - `C:\System_Trading\STOM\STOM_V.wt-lab`

## Task 1: Write the Korean RCA and Audit Log in `wt-dev`

**Files:**
- Create: `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`
- Test: `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`

- [ ] **Step 1: Create the RCA document skeleton**

Write this exact skeleton to `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`:

```markdown
# 2026-04-01 런타임 회귀 RCA 및 워크트리 감사

## 개요

이번 정리는 `wt-dev`에서 공식 `V2.70 ~ V2.73` 반영 후 드러난 런타임 회귀만 다룬다.

## 문제 1: 지수차트 삭제 후 잔여 참조

### 증상
### 원인
### 해결
### 검증

## 문제 2: utility.static 호환 심볼 누락

### 증상
### 원인
### 해결
### 검증

## 문제 3: 홈탭 WebCrawling 전달 경로 불일치

### 증상
### 원인
### 해결
### 검증

## 문제 4: 종료 경로 qtimer0 잔여 참조

### 증상
### 원인
### 해결
### 검증

## 워크트리 감사 매트릭스

| 워크트리 | 동일 문제 존재 여부 | 근거 | 반영 필요 여부 | 실제 반영 여부 |
| --- | --- | --- | --- | --- |
| STOM_Version_2U | 감사 예정 | 감사 후 기록 | 감사 후 판정 | 감사 후 결정 |
| STOM_Version_2U_C | 감사 예정 | 감사 후 기록 | 감사 후 판정 | 감사 후 결정 |
| research/init | 감사 예정 | 감사 후 기록 | 감사 후 판정 | 감사 후 결정 |
```

- [ ] **Step 2: Fill each RCA section with the exact verified incidents**

Use these facts when filling the document:

```text
문제 1:
- 삭제된 모듈: ui.ui_draw_jisuchart
- 잔여 참조 파일: ui/ui_mainwindow.py, ui/ui_process_kill.py
- 직접 증상: startup import failure, shutdown-time dialog_jisu reference

문제 2:
- 누락 심볼: summer_time, get_profile_text
- 직접 증상: ui.ui_mainwindow import chain failure, kiwoom_trader import failure

문제 3:
- V2.70 이후 utility.webcrawling.WebCrawling은 QThread + signal.emit 구조
- ui/ui_mainwindow.py는 여전히 Process(target=WebCrawling, ...) 실행
- 직접 증상: 홈탭 라벨이 계속 "데이터 검색 중 ..." 상태로 남음

문제 4:
- 종료 경로에 ui.qtimer0 참조 존재
- MainWindow에는 qtimer0가 없음
- 직접 증상: process_kill()에서 AttributeError 발생
```

- [ ] **Step 3: Add the exact verification commands and observed results**

Append this verification section under each relevant problem:

```markdown
- `python -m pytest tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py -q`
- `python -m pytest tests/unit/ -q`
- `python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"`
- `python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"`
- 짧은 `python stom.py` 실행에서 즉시 traceback 부재 확인
```

- [ ] **Step 4: Run the placeholder scan**

Run:

```powershell
rg -n "TBD|TODO|미정" docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md -S
```

Expected: no output

- [ ] **Step 5: Read the document end-to-end**

Run:

```powershell
Get-Content docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md
```

Expected: every section is filled, the audit matrix exists, and no contradictory wording remains.

## Task 2: Verify and Commit the `wt-dev` Remediation Bundle

**Files:**
- Modify: `ui/ui_mainwindow.py`
- Modify: `ui/ui_process_kill.py`
- Modify: `utility/static.py`
- Modify: `utility/webcrawling.py`
- Modify: `tests/unit/test_static_compat.py`
- Modify: `tests/unit/test_ui_jisu_cleanup.py`
- Create: `tests/unit/test_ui_runtime_wiring.py`
- Create: `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`
- Test: `tests/unit/test_static_compat.py`
- Test: `tests/unit/test_ui_jisu_cleanup.py`
- Test: `tests/unit/test_ui_runtime_wiring.py`

- [ ] **Step 1: Make sure the production files match these exact runtime-fix snippets**

`ui/ui_mainwindow.py` must contain this `WebCrawling` wiring:

```python
self.proc_tele  = Process(target=TelegramBot, args=(self.qlist, dict_set), daemon=True)
self.proc_chqs  = Process(target=ChartHogaQuerySound, args=(self.qlist, dict_set), daemon=True)
self.webc       = WebCrawling(self.qlist)
self.proc_livec = None

self.proc_tele.start()
self.proc_chqs.start()
self.webc.signal.connect(self.windowQ.put)
self.webc.start()
```

`ui/ui_process_kill.py` must remove `qtimer0` and stop the QThread cleanly:

```python
if ui.qtimer1.isActive(): ui.qtimer1.stop()
if ui.qtimer2.isActive(): ui.qtimer2.stop()
if ui.qtimer3.isActive(): ui.qtimer3.stop()

if hasattr(ui, 'webc') and ui.webc.isRunning():
    ui.webc.stop()
```

`utility/static.py` must expose the compatibility symbols:

```python
summer_time = summer_t


def get_profile_text(profile_obj, sort_by='cumulative', limit=None):
    from utility.profile_utils import extract_profile_text
    return extract_profile_text(profile_obj, sort_by=sort_by, limit=limit)
```

`utility/webcrawling.py` must have a stoppable loop:

```python
self.alive = True

while self.alive:
    ...

def stop(self):
    self.alive = False
    self.wait()
```

- [ ] **Step 2: Make sure the regression tests exist exactly at these paths**

The following test files must exist:

```text
tests/unit/test_static_compat.py
tests/unit/test_ui_jisu_cleanup.py
tests/unit/test_ui_runtime_wiring.py
```

Run:

```powershell
Test-Path tests\unit\test_static_compat.py
Test-Path tests\unit\test_ui_jisu_cleanup.py
Test-Path tests\unit\test_ui_runtime_wiring.py
```

Expected:

```text
True
True
True
```

- [ ] **Step 3: Run the targeted regression suite**

Run:

```powershell
python -m pytest tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py -q
```

Expected: `7 passed`

- [ ] **Step 4: Run runtime smoke verification**

Run:

```powershell
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"
```

Expected:

```text
ok
ok
```

- [ ] **Step 5: Run the full unit suite**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected: full suite passes with only existing third-party warnings.

- [ ] **Step 6: Commit the remediation bundle**

Run:

```powershell
git add ui/ui_mainwindow.py ui/ui_process_kill.py utility/static.py utility/webcrawling.py tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md
git commit -m "fix: resolve runtime regressions after V2.70-V2.73 sync"
```

Expected: one commit containing only the runtime regression fix files and the Korean RCA document.

## Task 3: Audit `STOM_Version_2U`

**Files:**
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2u\ui\ui_mainwindow.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2u\ui\ui_process_kill.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2u\utility\static.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2u\utility\webcrawling.py`
- Optional modify if defect exists: matching files above plus `tests/unit/*.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_static_compat.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_ui_jisu_cleanup.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_ui_runtime_wiring.py`

- [ ] **Step 1: Run the defect signature search in the 2U worktree**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2u
rg -n "ui.ui_draw_jisuchart|DrawRealJisuChart|show_jisu|dialog_jisu|qtimer0|Process\(target=WebCrawling|summer_time|get_profile_text" ui utility trade -S
```

Expected: either no output or a finite set of matching lines proving the defect exists.

- [ ] **Step 2: Run the minimal import probes before editing**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2u
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ui ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('trader ok')"
```

Expected: either both commands print `ok`, or one of them fails with the same runtime-regression signature.

- [ ] **Step 3: If Step 1 or 2 proves the defect exists, port the exact `wt-dev` runtime fix**

Apply the same four verified changes from Task 2 to these files inside `C:\System_Trading\STOM\STOM_V.wt-2u`:

```text
ui/ui_mainwindow.py
ui/ui_process_kill.py
utility/static.py
utility/webcrawling.py
```

Then copy the three regression tests from `wt-dev`:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_static_compat.py C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_static_compat.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_ui_jisu_cleanup.py C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_ui_jisu_cleanup.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_ui_runtime_wiring.py C:\System_Trading\STOM\STOM_V.wt-2u\tests\unit\test_ui_runtime_wiring.py -Force
```

Expected: either no patch is needed, or the target worktree now contains the same minimal fix shape as `wt-dev`.

- [ ] **Step 4: Verify only if files changed**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2u
python -m pytest tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py -q
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"
```

Expected: targeted tests pass and both imports print `ok`.

- [ ] **Step 5: Commit only if files changed**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2u
git add ui/ui_mainwindow.py ui/ui_process_kill.py utility/static.py utility/webcrawling.py tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py
git commit -m "fix: resolve runtime regressions after V2.70-V2.73 sync"
```

Expected: a commit is created only if the defect was actually present.

## Task 4: Audit `STOM_Version_2U_C`

**Files:**
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2uc\ui\ui_mainwindow.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2uc\ui\ui_process_kill.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\static.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-2uc\utility\webcrawling.py`
- Optional modify if defect exists: matching files above plus `tests/unit/*.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_static_compat.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_ui_jisu_cleanup.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_ui_runtime_wiring.py`

- [ ] **Step 1: Run the defect signature search in the 2U_C worktree**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2uc
rg -n "ui.ui_draw_jisuchart|DrawRealJisuChart|show_jisu|dialog_jisu|qtimer0|Process\(target=WebCrawling|summer_time|get_profile_text" ui utility trade -S
```

Expected: either no output or concrete matches proving the defect exists.

- [ ] **Step 2: Run the minimal import probes before editing**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2uc
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ui ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('trader ok')"
```

Expected: both commands pass, or one fails with the same signature already seen in `wt-dev`.

- [ ] **Step 3: If the defect exists, port the exact `wt-dev` runtime fix**

Apply the same four verified changes from Task 2 to these files inside `C:\System_Trading\STOM\STOM_V.wt-2uc`:

```text
ui/ui_mainwindow.py
ui/ui_process_kill.py
utility/static.py
utility/webcrawling.py
```

Then copy the three regression tests from `wt-dev`:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_static_compat.py C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_static_compat.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_ui_jisu_cleanup.py C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_ui_jisu_cleanup.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_ui_runtime_wiring.py C:\System_Trading\STOM\STOM_V.wt-2uc\tests\unit\test_ui_runtime_wiring.py -Force
```

Expected: the target worktree either stays untouched or receives the same minimal remediation set as `wt-dev`.

- [ ] **Step 4: Verify only if files changed**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2uc
python -m pytest tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py -q
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"
```

Expected: targeted tests pass and both imports print `ok`.

- [ ] **Step 5: Commit only if files changed**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-2uc
git add ui/ui_mainwindow.py ui/ui_process_kill.py utility/static.py utility/webcrawling.py tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py
git commit -m "fix: resolve runtime regressions after V2.70-V2.73 sync"
```

Expected: a commit exists only if the worktree actually needed the fix.

## Task 5: Audit `research/init`

**Files:**
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-lab\ui\ui_mainwindow.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-lab\ui\ui_process_kill.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-lab\utility\static.py`
- Read-only audit: `C:\System_Trading\STOM\STOM_V.wt-lab\utility\webcrawling.py`
- Optional modify if defect exists: matching files above plus `tests/unit/*.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_static_compat.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_ui_jisu_cleanup.py`
- Test if patched: `C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_ui_runtime_wiring.py`

- [ ] **Step 1: Run the defect signature search in the research worktree**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-lab
rg -n "ui.ui_draw_jisuchart|DrawRealJisuChart|show_jisu|dialog_jisu|qtimer0|Process\(target=WebCrawling|summer_time|get_profile_text" ui utility trade -S
```

Expected: either no output or concrete matches proving the same defect exists here too.

- [ ] **Step 2: Run the minimal import probes before editing**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-lab
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ui ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('trader ok')"
```

Expected: both imports pass, or one fails with the same runtime-regression signature.

- [ ] **Step 3: Patch only if the same defect is actually present**

If Step 1 and Step 2 do not show the same signature, do not edit this worktree. If they do, apply the same four-file remediation from Task 2 and copy the three regression tests from `wt-dev`:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_static_compat.py C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_static_compat.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_ui_jisu_cleanup.py C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_ui_jisu_cleanup.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_ui_runtime_wiring.py C:\System_Trading\STOM\STOM_V.wt-lab\tests\unit\test_ui_runtime_wiring.py -Force
```

Expected: `research/init` is changed only if the exact same defect exists.

- [ ] **Step 4: Verify only if files changed**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-lab
python -m pytest tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py -q
python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"
python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"
```

Expected: targeted tests pass and both imports print `ok`.

- [ ] **Step 5: Commit only if files changed**

Run:

```powershell
Set-Location C:\System_Trading\STOM\STOM_V.wt-lab
git add ui/ui_mainwindow.py ui/ui_process_kill.py utility/static.py utility/webcrawling.py tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py
git commit -m "fix: resolve runtime regressions after V2.70-V2.73 sync"
```

Expected: no commit if the research worktree did not need the fix.

## Task 6: Update the Audit Matrix and Final Decision Notes in `wt-dev`

**Files:**
- Modify: `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`
- Test: `docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md`

- [ ] **Step 1: Fill the audit matrix with the real observations**

Replace the initial matrix rows with actual values gathered from Tasks 3-5:

```markdown
| 워크트리 | 동일 문제 존재 여부 | 근거 | 반영 필요 여부 | 실제 반영 여부 |
| --- | --- | --- | --- | --- |
| STOM_Version_2U | 존재 / 미존재 | `rg` 결과 + import 결과 | 필요 / 불필요 | 반영함 / 미반영 |
| STOM_Version_2U_C | 존재 / 미존재 | `rg` 결과 + import 결과 | 필요 / 불필요 | 반영함 / 미반영 |
| research/init | 존재 / 미존재 | `rg` 결과 + import 결과 | 필요 / 불필요 | 반영함 / 미반영 |
```

- [ ] **Step 2: Add a short per-worktree rationale below the table**

Write one flat bullet per worktree:

```markdown
- `STOM_Version_2U`: 어떤 시그니처가 있었고 왜 반영했는지 또는 왜 반영하지 않았는지.
- `STOM_Version_2U_C`: 어떤 시그니처가 있었고 왜 반영했는지 또는 왜 반영하지 않았는지.
- `research/init`: 동일 결함이 실제 있었는지, 없었다면 왜 미반영인지.
```

- [ ] **Step 3: Run the placeholder scan again**

Run:

```powershell
rg -n "감사 예정|감사 후 기록|감사 후 판정|감사 후 결정|TBD|TODO|미정" docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md -S
```

Expected: no output

- [ ] **Step 4: Commit the final audit note update**

Run:

```powershell
git add docs/update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md
git commit -m "docs: record cross-worktree runtime regression audit"
```

Expected: the audit document now records the final per-worktree decision and commit status.

## Spec Coverage Check

- `wt-dev` 문제의 한글 RCA 작성: Task 1
- 현재 수정분 검증 및 커밋: Task 2
- 공식 워크트리 제외 감사: Task 3, Task 4, Task 5
- 존재하는 워크트리만 선택 반영: Task 3-5의 조건부 편집 단계
- 반영 필요 여부 판정과 기록: Task 6

## Self-Review Check

- Placeholder scan accounted for in Task 1 and Task 6.
- Worktree별 경로와 명령은 모두 절대 경로 또는 저장소 상대 경로로 고정했다.
- `research/init`은 동일 결함 존재 시에만 편집하도록 범위를 제한했다.
