# 2026-04-13 backtest shared memory lifetime design

## Context

`STOM_Version_2U_C` now loads the target minute backtest data and the CLI long-window run succeeds, but the GUI run exposed a new failure:

```text
FileNotFoundError: [WinError 2] 지정된 파일을 찾을 수 없습니다: 'backdata_4'
```

The traceback shows `BackEngineBase.GetArrayData()` opening a shared memory segment from `shared_info['shm_name']` while another engine process has already removed that segment.

This problem is specific to the current `2U_C` code path. Official `STOM_Version_2` and `STOM_Version_2U` keep loaded backtest shared memory alive for the engine lifetime. `2U_C` added cleanup hardening in commit `5f109bcc`, including `CleanupSharedMemory()` calls from `BackStop()` and from the end of `BackTest()`. That is too early for the GUI backtest-engine model because the loaded data is shared across all worker processes and is intended to be reused across repeated backtests until the engine is killed.

## Goals

- Prevent GUI worker processes from deleting `backdata_N` while other workers still need it.
- Preserve cleanup on explicit engine shutdown, failed startup, and CLI process cleanup so shared memory does not leak.
- Keep official V2/2U engine lifetime semantics: loaded data remains available until the backtest engine is stopped.
- Verify GUI-equivalent behavior through tests where possible and with CLI/runtime checks.
- Propagate the validated fix from `STOM_Version_2U_C` to `research/init`.

## Non-Goals

- Do not alter strategy logic, minute day-boundary logic, or setting DB schema logic.
- Do not change `STOM_Version_2` or `STOM_Version_2U`; they are comparison baselines.
- Do not modify `integration/adopt-cli-v267-into-2uc`; it is an archive branch.
- Do not disable shared-memory bulk loading as the primary fix.

## Design

### Ownership Rule

Shared-memory backtest data has engine lifetime, not single-backtest lifetime.

```text
Create: data-loading phase in each engine process
Use: one or more BackTest / optimization / finder runs
Delete: explicit engine shutdown or failed startup cleanup
```

Normal completion of `BackTest()` must not unlink shared memory. If one engine finishes early and deletes `backdata_N`, other engines can later fail when they pull a `shared_info` entry owned by that segment.

### BackEngineBase Changes

`BackEngineBase.BackTest()` should no longer call `self.CleanupSharedMemory()` on normal completion. The profiling block can remain, but cleanup should be reserved for engine-stop paths.

`BackEngineBase.BackStop()` should keep cleanup because it represents engine cancellation, strategy error, or explicit stop paths.

To make the ownership clear and testable, introduce a lightweight helper if needed:

```python
def FinishBackTestRun(self):
    if self.gubun == 0 and self.profile:
        from utility.profile_utils import extract_profile_text
        profile_text = extract_profile_text(self.pr, limit=50)
        self.wq.put((ui_num['시스템로그'], profile_text))
```

The helper must not call `CleanupSharedMemory()`.

### GUI Cleanup

The GUI already performs parent-side cleanup in `ui/ui_button_clicked_dialog_backengine.py::backtest_engine_kill()`:

- If `ui.shared_info` contains `shm_name`, it opens and unlinks each segment.
- It then kills engine/subtotal processes and clears queues/lists.

That cleanup should remain the primary GUI shared-memory cleanup path.

The design does not require changing `backtest_engine_kill()` unless testing shows duplicate unlink noise or missing stale segment handling.

### CLI Cleanup

CLI creates child processes and already has `_cleanup_procs()` registered through `atexit`. Since CLI exits after one run, it needs parent-visible cleanup for shared memory if child-owned cleanup is removed from normal `BackTest()`.

Preferred CLI cleanup:

- Add a small helper in `cli/runner.py` that receives `shared_info` and unlinks unique `shm_name` values.
- Call it in `run_backtest()` `finally` before or after child process cleanup.
- It should ignore `FileNotFoundError` because a failed child startup or previous cleanup may have already removed a segment.
- It should not touch temp file entries except existing `_drain_queues` / process cleanup paths.

Example shape:

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

This keeps CLI leak prevention without allowing individual worker processes to delete shared data during a run.

## Testing

Add unit tests focused on contracts rather than launching the GUI:

- `BackTest()` normal completion path must not contain or call `CleanupSharedMemory()`.
- `BackStop()` must still call `CleanupSharedMemory()`.
- CLI shared-memory cleanup helper must unlink each unique `shm_name` once and ignore missing segments.
- CLI `run_backtest()` `finally` must call the cleanup helper with the accumulated `shared_info`.

Then run:

```powershell
python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

Runtime verification:

- CLI long-window minute backtest still succeeds:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --timeout 1200 --format json --quiet
```

- GUI verification should use the same loaded engine configuration:
  - minute
  - `2025-04-01` to `2025-12-31`
  - `090000` to `151800`
  - avg tick `30`
  - engine count `20`
  - `Min_B_Study_251227` / `Min_S_Study_251227`

Expected GUI result:

- no `FileNotFoundError` for `backdata_N`
- no "매수전략을 만족하는 경우가 없어" collapse for the long window
- result should be comparable to the CLI long-window result, with CLI observed `trade_count=6323`

## Update Log

Create a follow-up update log:

```text
docs/update_log/2026-04-13_backtest_shared_memory_lifetime_fix.md
```

The log should record:

- GUI traceback and failing `backdata_N` names.
- Root cause: `2U_C` cleanup hardening deleted shared-memory segments at single-run completion.
- Official V2/2U comparison: shared data is engine-lifetime.
- Fix: remove normal-run cleanup from workers; keep cleanup at engine shutdown and CLI parent cleanup.
- Verification results for `2U_C` and `research/init`.
