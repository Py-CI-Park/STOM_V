# Backtest Button Contract Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `wt-dev`에서 백테스트 버튼 클릭 시 발생하는 `BackTest.__init__()` 인자 계약 오류를 제거하고, 같은 계약 불일치가 있는 워크트리만 함께 정리한다.

**Architecture:** `BackTest` 쪽을 다시 넓히지 않고, 버튼 클릭 호출자 쪽 `Process(target=BackTest, args=...)` 계약을 현재 `backtest/backtest.py` 구조에 맞춘다. `wt-dev`에서 먼저 기준 수정과 회귀 테스트를 만들고, 그 다음 `STOM_Version_2U`, `STOM_Version_2U_C`, `research/init`을 읽기 전용 감사해 동일 불일치가 있는 워크트리만 같은 방식으로 반영한다.

**Tech Stack:** Python 3.11, multiprocessing, PyQt5 UI handlers, pytest, PowerShell, git worktree

---

## File Structure

- Create: `docs/update_log/2026-04-02_backtest_button_contract_audit.md`
- Create: `docs/superpowers/plans/2026-04-02-backtest-button-contract-fix.md`
- Modify: `ui/ui_button_clicked_editer_stock.py`
- Modify: `ui/ui_button_clicked_editer_coin.py`
- Modify: `ui/ui_button_clicked_dialog_backengine.py` (only if this path also instantiates `BackTest` with the stale signature)
- Modify: `backtest/backtest.py` (only if a minimal adapter or explicit assertion is needed; do not widen the constructor back to the old long form without evidence)
- Create: `tests/unit/test_backtest_button_contract.py`
- Create: `tests/unit/test_backtest_spawn_contract_audit.py`
- Audit-only target roots:
  - `C:\System_Trading\STOM\STOM_V.wt-2u`
  - `C:\System_Trading\STOM\STOM_V.wt-2uc`
  - `C:\System_Trading\STOM\STOM_V.wt-lab`

## Task 1: Write the Backtest Contract RCA Log

**Files:**
- Create: `docs/update_log/2026-04-02_backtest_button_contract_audit.md`
- Test: `docs/update_log/2026-04-02_backtest_button_contract_audit.md`

- [ ] **Step 1: Write the RCA skeleton**

Create `docs/update_log/2026-04-02_backtest_button_contract_audit.md` with this exact structure:

```markdown
# 2026-04-02 백테스트 버튼 계약 불일치 RCA

## 개요

## 증상

## 원인

## 해결 방향

## 검증 결과

## 워크트리 감사 매트릭스

| 워크트리 | 동일 문제 존재 여부 | 근거 | 반영 필요 여부 | 실제 반영 여부 |
| --- | --- | --- | --- | --- |
| STOM_Version_2U | 감사 예정 | 감사 후 기록 | 감사 후 판정 | 감사 후 결정 |
| STOM_Version_2U_C | 감사 예정 | 감사 후 기록 | 감사 후 판정 | 감사 후 결정 |
| research/init | 감사 예정 | 감사 후 기록 | 감사 후 판정 | 감사 후 결정 |
```

- [ ] **Step 2: Fill the RCA with the exact observed error**

Use these facts verbatim in the document:

```text
- 버튼 클릭 직후 핵심 오류:
  TypeError: BackTest.__init__() takes 13 positional arguments but 25 were given
- 백테스트 엔진 자체는 먼저 성공적으로 구동됨
- 1차 분석 대상 파일:
  - ui/ui_button_clicked_editer_stock.py
  - ui/ui_button_clicked_editer_coin.py
  - 필요 시 ui/ui_button_clicked_dialog_backengine.py
  - 기준 계약 파일: backtest/backtest.py
- 텔레그램/httpx, get_korean_stocks/get_market_indicator/get_crypto_data 네트워크 예외는 이번 RCA의 1차 원인에서 제외
```

- [ ] **Step 3: Add the expected verification commands**

Add these exact commands under `검증 결과`:

```markdown
- `python -m pytest tests/unit/test_backtest_button_contract.py -q`
- `python -m pytest tests/unit/test_backtest_spawn_contract_audit.py -q`
- `python -m pytest tests/unit/ -q`
- 관련 모듈 import smoke
- 가능하면 백테스트 버튼 시작 경로 smoke
```

- [ ] **Step 4: Placeholder scan**

Run:

```powershell
rg -n "TBD|TODO|미정" docs/update_log/2026-04-02_backtest_button_contract_audit.md -S
```

Expected: no output

- [ ] **Step 5: Commit the RCA document**

Run:

```powershell
git add docs/update_log/2026-04-02_backtest_button_contract_audit.md
git commit -m "docs: add backtest button contract RCA"
```

Expected: a single docs-only commit for the RCA log.

## Task 2: Lock the `wt-dev` Contract Mismatch with Failing Tests

**Files:**
- Create: `tests/unit/test_backtest_button_contract.py`
- Create: `tests/unit/test_backtest_spawn_contract_audit.py`
- Test: `tests/unit/test_backtest_button_contract.py`
- Test: `tests/unit/test_backtest_spawn_contract_audit.py`

- [ ] **Step 1: Write the static mismatch audit test**

Create `tests/unit/test_backtest_spawn_contract_audit.py` with this exact starting content:

```python
from pathlib import Path


def test_stock_backtest_spawn_does_not_pass_legacy_long_signature():
    text = Path('ui/ui_button_clicked_editer_stock.py').read_text(encoding='utf-8')
    assert "target=BackTest" in text
    assert "ui.back_sques" not in text
    assert "ui.back_count" not in text


def test_coin_backtest_spawn_does_not_pass_legacy_long_signature():
    text = Path('ui/ui_button_clicked_editer_coin.py').read_text(encoding='utf-8')
    assert "target=BackTest" in text
    assert "ui.back_sques" not in text
    assert "ui.back_count" not in text
```

- [ ] **Step 2: Run the audit test to confirm it fails**

Run:

```powershell
python -m pytest tests/unit/test_backtest_spawn_contract_audit.py -q
```

Expected: FAIL because the current stock/coin button paths still contain the stale long-argument spawn pattern.

- [ ] **Step 3: Write the constructor contract test**

Create `tests/unit/test_backtest_button_contract.py` with this exact starting content:

```python
import inspect

from backtest.backtest import BackTest


def test_backtest_constructor_contract_is_small_and_queue_driven():
    params = list(inspect.signature(BackTest.__init__).parameters)
    assert params == [
        "self",
        "sc",
        "wq",
        "bq",
        "sq",
        "tq",
        "lq",
        "teleQ",
        "beq_list",
        "bstq_list",
        "backname",
        "ui_gubun",
        "dict_set",
    ]
```

- [ ] **Step 4: Run the constructor contract test**

Run:

```powershell
python -m pytest tests/unit/test_backtest_button_contract.py -q
```

Expected: PASS or fail only if the constructor contract has drifted unexpectedly. If it passes, that confirms the bug is on the caller side.

- [ ] **Step 5: Commit the tests**

Run:

```powershell
git add tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py
git commit -m "test: lock backtest button contract mismatch"
```

Expected: tests-only commit capturing the broken contract before the production fix.

## Task 3: Fix the `wt-dev` Button Spawn Contract

**Files:**
- Modify: `ui/ui_button_clicked_editer_stock.py`
- Modify: `ui/ui_button_clicked_editer_coin.py`
- Modify: `ui/ui_button_clicked_dialog_backengine.py` (only if it still spawns `BackTest` directly with the stale signature)
- Modify: `backtest/backtest.py` (only if a tiny adapter/assertion is truly required)
- Test: `tests/unit/test_backtest_button_contract.py`
- Test: `tests/unit/test_backtest_spawn_contract_audit.py`

- [ ] **Step 1: Inspect the current `BackTest` spawn arguments in stock/coin handlers**

Read these exact files:

```powershell
Get-Content ui/ui_button_clicked_editer_stock.py | Select-Object -Skip 1268 -First 28
Get-Content ui/ui_button_clicked_editer_coin.py | Select-Object -Skip 1268 -First 28
Get-Content backtest/backtest.py | Select-Object -Skip 260 -First 40
```

Expected: confirm which arguments are stale and which queues are now duplicated by the queue-driven `BackTest` implementation.

- [ ] **Step 2: Change the stock button path to match the current constructor contract**

Update the `Process(target=BackTest, args=...)` call in `ui/ui_button_clicked_editer_stock.py` so it passes exactly:

```python
args=(
    ui.shared_cnt,
    ui.windowQ,
    ui.backQ,
    ui.soundQ,
    ui.totalQ,
    ui.liveQ,
    ui.teleQ,
    ui.back_eques,
    ui.back_sques,
    '백테스트',
    gubun,
    ui.dict_set,
)
```

Do not keep the legacy direct payload values (`betting`, `avgtime`, `startday`, `endday`, `starttime`, `endtime`, `buystg`, `sellstg`, `ui.dict_cn`, `ui.back_count`, `bl`, `False`, `back_club`) in the constructor args. Those belong in the queues the current implementation already reads.

- [ ] **Step 3: Change the coin button path to match the same contract**

Apply the same constructor-arg reduction in `ui/ui_button_clicked_editer_coin.py`:

```python
args=(
    ui.shared_cnt,
    ui.windowQ,
    ui.backQ,
    ui.soundQ,
    ui.totalQ,
    ui.liveQ,
    ui.teleQ,
    ui.back_eques,
    ui.back_sques,
    '백테스트',
    gubun,
    ui.dict_set,
)
```

- [ ] **Step 4: Check `ui/ui_button_clicked_dialog_backengine.py` for the same stale direct call**

Run:

```powershell
rg -n "target=BackTest" ui/ui_button_clicked_dialog_backengine.py -S
```

If a direct `BackTest` spawn exists there too, update it to the same reduced contract. If it does not exist, make no changes.

- [ ] **Step 5: Run the two contract tests**

Run:

```powershell
python -m pytest tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py -q
```

Expected: PASS

- [ ] **Step 6: Run targeted unit suite for backtest-adjacent coverage**

Run:

```powershell
python -m pytest tests/unit/test_backtest_result_expansion.py tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py -q
```

Expected: PASS

- [ ] **Step 7: Commit the `wt-dev` production fix**

Run:

```powershell
git add ui/ui_button_clicked_editer_stock.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_dialog_backengine.py backtest/backtest.py tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py
git commit -m "fix: align backtest button spawn contract"
```

Expected: one focused commit for the contract fix in `wt-dev`.

## Task 4: Audit `STOM_Version_2U`, `STOM_Version_2U_C`, and `research/init`

**Files:**
- Read-only audit in:
  - `C:\System_Trading\STOM\STOM_V.wt-2u`
  - `C:\System_Trading\STOM\STOM_V.wt-2uc`
  - `C:\System_Trading\STOM\STOM_V.wt-lab`
- Possible modify in each matching worktree:
  - `ui/ui_button_clicked_editer_stock.py`
  - `ui/ui_button_clicked_editer_coin.py`
  - `ui/ui_button_clicked_dialog_backengine.py`
  - `backtest/backtest.py`
  - `tests/unit/test_backtest_button_contract.py`
  - `tests/unit/test_backtest_spawn_contract_audit.py`

- [ ] **Step 1: Run the same signature audit in each worktree**

Run in each target worktree:

```powershell
rg -n "target=BackTest|ui.back_sques|ui.back_count|betting, avgtime|endtime, buystg" ui backtest -S
python -c "import inspect; from backtest.backtest import BackTest; print(list(inspect.signature(BackTest.__init__).parameters))"
```

Expected: identify whether the worktree has the same mismatch pattern: long direct spawn arguments plus short constructor.

- [ ] **Step 2: Patch only the worktrees that match the same pattern**

If a worktree has the same mismatch, apply the same caller-side contract reduction as Task 3 and copy these two tests from `wt-dev`:

```powershell
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_backtest_button_contract.py <TARGET>\tests\unit\test_backtest_button_contract.py -Force
Copy-Item C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit\test_backtest_spawn_contract_audit.py <TARGET>\tests\unit\test_backtest_spawn_contract_audit.py -Force
```

Expected: only matching worktrees are edited.

- [ ] **Step 3: Verify only where patched**

Run in each patched worktree:

```powershell
python -m pytest tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py -q
```

Expected: PASS

- [ ] **Step 4: Commit each patched worktree independently**

Run in each patched worktree:

```powershell
git add ui/ui_button_clicked_editer_stock.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_dialog_backengine.py backtest/backtest.py tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py
git commit -m "fix: align backtest button spawn contract"
```

Expected: only worktrees with the matching defect receive a commit.

## Task 5: Update the Audit Log

**Files:**
- Modify: `docs/update_log/2026-04-02_backtest_button_contract_audit.md`

- [ ] **Step 1: Fill the worktree audit matrix with actual results**

Replace placeholder rows with real values:

```markdown
| 워크트리 | 동일 문제 존재 여부 | 근거 | 반영 필요 여부 | 실제 반영 여부 |
| --- | --- | --- | --- | --- |
| STOM_Version_2U | 존재 / 미존재 | 정적 호출 패턴 + 시그니처 결과 | 필요 / 불필요 | 반영함 / 미반영 |
| STOM_Version_2U_C | 존재 / 미존재 | 정적 호출 패턴 + 시그니처 결과 | 필요 / 불필요 | 반영함 / 미반영 |
| research/init | 존재 / 미존재 | 정적 호출 패턴 + 시그니처 결과 | 필요 / 불필요 | 반영함 / 미반영 |
```

- [ ] **Step 2: Add a short rationale per worktree**

Add three flat bullets:

```markdown
- `STOM_Version_2U`: 동일 계약 불일치가 있었는지와 반영 여부.
- `STOM_Version_2U_C`: 동일 계약 불일치가 있었는지와 반영 여부.
- `research/init`: 동일 계약 불일치가 있었는지와 반영 여부.
```

- [ ] **Step 3: Placeholder scan**

Run:

```powershell
rg -n "감사 예정|감사 후 기록|감사 후 판정|감사 후 결정|TBD|TODO|미정" docs/update_log/2026-04-02_backtest_button_contract_audit.md -S
```

Expected: no output

- [ ] **Step 4: Commit the updated audit log**

Run:

```powershell
git add docs/update_log/2026-04-02_backtest_button_contract_audit.md
git commit -m "docs: record backtest button contract audit"
```

Expected: one docs commit recording the final worktree audit outcome.

## Spec Coverage Check

- `wt-dev` 버튼 불능의 1차 원인인 `BackTest` 계약 불일치 해결: Task 3
- 같은 문제가 있는 워크트리만 함께 수정: Task 4
- 네트워크 예외는 제외: Task 1 RCA와 Task 5 감사 기록에서만 언급
- 결과 문서화: Task 1, Task 5

## Self-Review Check

- 각 단계는 실제 파일 경로와 명령을 포함한다.
- 호출자 정리 우선이라는 설계 방침이 Task 3에 직접 반영되어 있다.
- 타 워크트리 전파는 동일 패턴 존재 시에만 수행되도록 제한했다.
