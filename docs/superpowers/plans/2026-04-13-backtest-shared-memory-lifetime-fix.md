# Backtest Shared Memory Lifetime Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent GUI backtest workers from deleting shared `backdata_N` memory during a run while preserving cleanup on engine shutdown and CLI exit.

**Architecture:** Treat loaded backtest shared memory as engine-lifetime data, not single-run data. Worker `BackTest()` normal completion must leave shared memory alive; explicit stop paths keep worker cleanup, and CLI adds parent-side cleanup for its one-shot process lifecycle.

**Tech Stack:** Python 3.11, multiprocessing shared_memory, pytest, STOM GUI/CLI backtest engine.

---

## File Structure

- Modify: `backtest/backengine_base.py`
  - Remove normal-run shared-memory cleanup from `BackTest()`.
  - Keep `BackStop()` cleanup.
- Modify: `tests/unit/test_backengine_shared_memory_cleanup.py`
  - Strengthen static contract tests for `BackTest()` and `BackStop()` cleanup ownership.
- Modify: `cli/runner.py`
  - Add parent-side `_cleanup_shared_memory(shared_info)` helper.
  - Call helper in `run_backtest()` `finally`.
- Modify: `tests/unit/test_runner_helpers.py`
  - Add tests for CLI shared-memory cleanup helper and `finally` wiring.
- Create: `docs/update_log/2026-04-13_backtest_shared_memory_lifetime_fix.md`
  - Record root cause, official branch comparison, fix, and verification.
- Propagate after validation:
  - `C:/System_Trading/STOM/STOM_V.wt-lab` (`research/init`)

Do not modify:

- `C:/System_Trading/STOM/STOM_V` (`STOM_Version_2`)
- `C:/System_Trading/STOM/STOM_V.wt-2u` (`STOM_Version_2U`)
- `C:/System_Trading/STOM/STOM_V.wt-2uc` (`integration/adopt-cli-v267-into-2uc`)
- `backtest/graph/`

## Task 1: Fix worker shared-memory lifetime

**Files:**
- Modify: `tests/unit/test_backengine_shared_memory_cleanup.py`
- Modify: `backtest/backengine_base.py`
- Test: `tests/unit/test_backengine_shared_memory_cleanup.py`

- [ ] **Step 1: Replace the existing weak cleanup test**

Replace `tests/unit/test_backengine_shared_memory_cleanup.py` with:

```python
import inspect

from backtest.backengine_base import BackEngineBase


def test_backstop_cleans_up_shared_memory():
    source = inspect.getsource(BackEngineBase.BackStop)

    assert "self.CleanupSharedMemory()" in source


def test_backtest_normal_completion_does_not_cleanup_shared_memory():
    source = inspect.getsource(BackEngineBase.BackTest)

    assert "self.CleanupSharedMemory()" not in source


def test_cleanup_shared_memory_unlinks_segments():
    source = inspect.getsource(BackEngineBase.CleanupSharedMemory)

    assert "unlink()" in source
    assert "FileNotFoundError" in source
```

- [ ] **Step 2: Run the cleanup test and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py -q
```

Expected result:

```text
FAILED tests/unit/test_backengine_shared_memory_cleanup.py::test_backtest_normal_completion_does_not_cleanup_shared_memory
```

- [ ] **Step 3: Remove normal-run cleanup from `BackTest()`**

In `backtest/backengine_base.py`, find the end of `BackTest()`:

```python
        if self.gubun == 0 and self.profile:
            from utility.profile_utils import extract_profile_text
            profile_text = extract_profile_text(self.pr, limit=50)
            self.wq.put((ui_num['시스템로그'], profile_text))
        self.CleanupSharedMemory()
```

Remove only the final cleanup call:

```python
        if self.gubun == 0 and self.profile:
            from utility.profile_utils import extract_profile_text
            profile_text = extract_profile_text(self.pr, limit=50)
            self.wq.put((ui_num['시스템로그'], profile_text))
```

Do not remove `CleanupSharedMemory()` from `BackStop()`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py -q
```

Expected result:

```text
3 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add backtest/backengine_base.py tests/unit/test_backengine_shared_memory_cleanup.py
git commit -m "백테스트 정상 완료 시 공유메모리를 유지한다" -m "GUI 백테스트 엔진은 로딩된 backdata_N 공유메모리를 엔진 수명 동안 재사용한다. 정상 백테스트 1회 완료에서 worker가 CleanupSharedMemory를 호출하면 다른 worker가 같은 shared_info를 열 때 FileNotFoundError가 발생한다." -m "BackStop의 명시적 엔진 중지 cleanup은 유지하고, BackTest 정상 완료 cleanup만 제거했다." -m "Constraint: 공유메모리는 백테스트 1회 수명이 아니라 엔진 수명이다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py -q"
```

Expected result:

```text
commit created with only backtest/backengine_base.py and tests/unit/test_backengine_shared_memory_cleanup.py
```

## Task 2: Add CLI parent-side shared-memory cleanup

**Files:**
- Modify: `tests/unit/test_runner_helpers.py`
- Modify: `cli/runner.py`
- Test: `tests/unit/test_runner_helpers.py`

- [ ] **Step 1: Add failing CLI cleanup helper tests**

Append this class to `tests/unit/test_runner_helpers.py`:

```python
class TestCliSharedMemoryCleanup:
    """CLI parent process cleans up shared memory segments after a one-shot run."""

    def test_cleanup_shared_memory_unlinks_unique_shm_names(self, monkeypatch):
        from cli import runner

        calls = []

        class FakeSharedMemory:
            def __init__(self, name):
                calls.append(("open", name))
                self.name = name

            def close(self):
                calls.append(("close", self.name))

            def unlink(self):
                calls.append(("unlink", self.name))

        monkeypatch.setattr(runner.shared_memory, "SharedMemory", FakeSharedMemory)

        runner._cleanup_shared_memory([
            {"shm_name": "backdata_1"},
            {"shm_name": "backdata_1"},
            {"shm_name": "backdata_2"},
            {"file_name": "back_0"},
        ])

        assert calls == [
            ("open", "backdata_1"),
            ("close", "backdata_1"),
            ("unlink", "backdata_1"),
            ("open", "backdata_2"),
            ("close", "backdata_2"),
            ("unlink", "backdata_2"),
        ]

    def test_cleanup_shared_memory_ignores_missing_segments(self, monkeypatch):
        from cli import runner

        class MissingSharedMemory:
            def __init__(self, name):
                raise FileNotFoundError(name)

        monkeypatch.setattr(runner.shared_memory, "SharedMemory", MissingSharedMemory)

        runner._cleanup_shared_memory([{"shm_name": "missing"}])
```

- [ ] **Step 2: Run the cleanup helper tests and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q -k TestCliSharedMemoryCleanup
```

Expected result:

```text
FAILED with AttributeError: module 'cli.runner' has no attribute '_cleanup_shared_memory'
```

- [ ] **Step 3: Add `shared_memory` import and helper to `cli/runner.py`**

In `cli/runner.py`, change the multiprocessing import:

```python
from multiprocessing import Process, Queue, Value, Lock
```

to:

```python
from multiprocessing import Process, Queue, Value, Lock, shared_memory
```

Add this helper near `_drain_queues`:

```python
def _cleanup_shared_memory(shared_info):
    seen = set()
    for info in shared_info or []:
        name = info.get('shm_name')
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            shm = shared_memory.SharedMemory(name=name)
            shm.close()
            shm.unlink()
        except FileNotFoundError:
            pass
```

- [ ] **Step 4: Wire cleanup into `run_backtest()` finally**

In `run_backtest()`, initialize parent-visible shared info before the `try` block:

```python
    shared_info = []
```

Replace the local assignment inside data loading:

```python
        shared_info = []
```

with reuse of the outer variable:

```python
        shared_info.clear()
```

In the `finally` block, call cleanup before process cleanup:

```python
        _cleanup_shared_memory(shared_info)
        _drain_queues(all_queues + back_sques + back_eques)
        drainer.stop()
        drainer.join(timeout=2)
        _cleanup_procs()
```

- [ ] **Step 5: Run CLI cleanup tests and helper suite**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q -k TestCliSharedMemoryCleanup
python -m pytest tests/unit/test_runner_helpers.py -q
```

Expected result:

```text
TestCliSharedMemoryCleanup passes
all runner helper tests pass
```

- [ ] **Step 6: Commit Task 2**

Run:

```powershell
git add cli/runner.py tests/unit/test_runner_helpers.py
git commit -m "CLI 종료 시 공유메모리를 부모 프로세스에서 정리한다" -m "worker 정상 완료 cleanup을 제거하면 CLI one-shot 실행은 부모가 shared_info 기준으로 backdata_N을 정리해야 한다." -m "중복 shm_name은 한 번만 unlink하고 이미 사라진 segment는 무시하도록 해 실패 cleanup 경로도 안전하게 유지한다." -m "Constraint: GUI cleanup은 backtest_engine_kill 경로가 계속 담당한다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python -m pytest tests/unit/test_runner_helpers.py -q"
```

Expected result:

```text
commit created with only cli/runner.py and tests/unit/test_runner_helpers.py
```

## Task 3: Verify `STOM_Version_2U_C` runtime behavior

**Files:**
- Test only

- [ ] **Step 1: Run targeted cleanup tests**

Run:

```powershell
python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_runner_helpers.py -q
```

Expected result:

```text
all selected tests pass
```

- [ ] **Step 2: Run broader unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected result:

```text
all unit tests pass, with the existing skipped test and warnings only
```

- [ ] **Step 3: Run non-release guardrails**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected result:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 4: Run CLI long-window backtest**

Run:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --timeout 1200 --format json --quiet
```

Expected result:

```text
exit code 0
status success
trade_count > 0
no leftover multiprocessing-fork Python children for this run
```

- [ ] **Step 5: Check for leftover multiprocessing children**

Run:

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match '^python(\\.exe)?$|^python32(\\.exe)?$' -and
    $_.CommandLine -like '*multiprocessing-fork*' -and
    $_.CommandLine -like '*C:\\Python\\64\\Python3119*'
  } |
  Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine
```

Expected result:

```text
no rows for the completed CLI backtest run
```

## Task 4: Write update log

**Files:**
- Create: `docs/update_log/2026-04-13_backtest_shared_memory_lifetime_fix.md`

- [ ] **Step 1: Create update log**

Create `docs/update_log/2026-04-13_backtest_shared_memory_lifetime_fix.md` with:

```markdown
# 2026-04-13 백테스트 공유메모리 수명 복구

## 증상

- GUI 백테스트 실행 직후 여러 worker에서 `FileNotFoundError: [WinError 2] ... 'backdata_N'`가 발생했다.
- 오류 위치는 `BackEngineBase.GetArrayData()`의 `shared_memory.SharedMemory(name=shared_info['shm_name'])` 호출이었다.

## 원인

- `STOM_Version_2U_C`의 shared memory cleanup hardening이 정상 백테스트 1회 완료 시 worker의 `CleanupSharedMemory()`를 호출했다.
- `backdata_N`은 개별 worker 소유처럼 보이지만 실제 실행 중에는 전체 `shared_info` 목록을 여러 worker가 나눠 처리한다.
- 먼저 끝난 worker가 자기 segment를 unlink하면, 나중에 해당 segment의 `shared_info`를 잡은 다른 worker가 `FileNotFoundError`를 낸다.

## 해결

- `BackTest()` 정상 완료에서는 공유메모리를 삭제하지 않는다.
- `BackStop()`의 명시적 엔진 중지 cleanup은 유지한다.
- CLI는 one-shot 실행 후 parent process가 `shared_info` 기준으로 unique `shm_name`을 정리한다.

## 공식 브랜치 비교

- `STOM_Version_2`와 `STOM_Version_2U`는 정상 백테스트 완료 시 shared memory를 즉시 unlink하지 않는다.
- 이번 문제는 `2U_C` 커스텀 cleanup hardening에서 발생했다.

## 검증

- `python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_runner_helpers.py -q`
- `python -m pytest tests/unit/ -q`
- `python scripts/verify_nonrelease_sync.py`
- CLI long-window minute backtest
- GUI long-window minute backtest
```

- [ ] **Step 2: Replace verification bullets with actual outcomes**

After Task 3 and GUI verification, replace each command bullet with exact pass counts and runtime results.

- [ ] **Step 3: Commit update log**

Run:

```powershell
git add docs/update_log/2026-04-13_backtest_shared_memory_lifetime_fix.md
git commit -m "백테스트 공유메모리 수명 복구 기록을 남긴다" -m "GUI 백테스트에서 backdata_N 공유메모리가 실행 중 삭제되던 원인과 엔진 수명 기준 cleanup 복구 및 CLI parent cleanup 보강 내용을 기록한다." -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: update log placeholder scan" -m "Tested: git diff --check"
```

## Task 5: Propagate to `research/init`

**Files:**
- Cherry-pick to `C:/System_Trading/STOM/STOM_V.wt-lab`

- [ ] **Step 1: Cherry-pick the validated commits**

In `C:/System_Trading/STOM/STOM_V.wt-lab`, cherry-pick:

```powershell
$workerCommit = git -C C:\System_Trading\STOM\STOM_V.wt-dev log --grep "백테스트 정상 완료 시 공유메모리를 유지한다" -n 1 --format=%H
$cliCommit = git -C C:\System_Trading\STOM\STOM_V.wt-dev log --grep "CLI 종료 시 공유메모리를 부모 프로세스에서 정리한다" -n 1 --format=%H
$logCommit = git -C C:\System_Trading\STOM\STOM_V.wt-dev log --grep "백테스트 공유메모리 수명 복구 기록을 남긴다" -n 1 --format=%H
Write-Output $workerCommit
Write-Output $cliCommit
Write-Output $logCommit
git cherry-pick $workerCommit
git cherry-pick $cliCommit
git cherry-pick $logCommit
```

- [ ] **Step 2: Run research targeted checks**

Run:

```powershell
python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_runner_helpers.py -q
python scripts/verify_nonrelease_sync.py
$baseBeforeSharedMemoryPropagation = git rev-parse HEAD~3
git diff --check $baseBeforeSharedMemoryPropagation..HEAD -- backtest/backengine_base.py cli/runner.py tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_runner_helpers.py docs/update_log/2026-04-13_backtest_shared_memory_lifetime_fix.md
```

Expected result:

```text
targeted tests pass
non-release sync passes
diff check passes
```

- [ ] **Step 3: Record research full-suite caveat**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected result:

```text
Either all tests pass, or the same known research failures remain:
tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db
tests/unit/test_exit_codes.py::TestExitCodes::test_execution_error_returns_two
```

## Final Checklist

- [ ] `STOM_Version_2U_C` tracked files clean.
- [ ] `research/init` tracked files clean.
- [ ] `integration/adopt-cli-v267-into-2uc` unchanged.
- [ ] GUI no longer reports `FileNotFoundError` for `backdata_N`.
- [ ] CLI long-window backtest still succeeds.
