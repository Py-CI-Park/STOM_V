# V3 -> 2U_C BP-007A timesync micro-candidate cycle

Created: 2026-05-07 KST
Root lane: `C:/System_Trading/STOM/STOM_V` (`STOM_Version_2`)
2U_C lane: `C:/System_Trading/STOM/STOM_V.wt-dev` (`STOM_Version_2U_C`)
V3 source lane: `C:/System_Trading/STOM/STOM_V.wt-3` (`STOM_Version_3`)

## Progress after Page 1

```text
total progress       [###################-]  94.0%  63 / 67 pages
BP-007A current      [####----------------]  20.0%   1 /  5 pages
remaining pages      [################----]  80.0%   4 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "git -C C:/System_Trading/STOM/STOM_V diff --find-renames STOM_Version_2U_C STOM_Version_3 -- utility/timesync.py utility/sub_process_and_thread/timesync.py"
```

## Page 1 / 5 - read-only inventory

`2UC-V3-BP-007A` is opened as a single-file, in-place timesync micro-candidate after re-running the V3 vs 2U_C inventory from the 62/62 no-more baseline.

Inventory evidence:

- Local inventory logdir: `.omx/logs/v3_2uc_reaudit_inventory_20260507T100249Z/`
- Diff base/source: `STOM_Version_2U_C` -> `STOM_Version_3`
- Total diff paths: 1005
- Status counts: `M=26`, `D=671`, `A=198`, `R=110`
- Python paths: 488
- Binary/runtime extension paths: 49
- Forbidden runtime artifact paths: 0

Candidate evidence:

- V3 source path: `utility/sub_process_and_thread/timesync.py`
- 2U_C target path: `utility/timesync.py`
- Git evidence: `R060 utility/timesync.py -> utility/sub_process_and_thread/timesync.py`
- Source commits: `06b70418 STOM V3.0` and `dbab03b3 STOM V3.11`
- Safe subset only:
  - add docstring to the existing 2U_C function,
  - remove `dateutil.tz` from the existing file and use `datetime.astimezone()`,
  - change user-facing queue messages to Korean text from V3,
  - narrow bare `except:` to `except Exception:`.

Explicit exclusions for this BP:

- Do not move `utility/timesync.py` into `utility/sub_process_and_thread/`.
- Do not import V3 `utility.static_method.*` modules.
- Do not adopt V3 `utility/settings`, `utility/db_control`, LS API, DB migration, UI/pyd restructuring, or process/thread wiring changes.
- Do not create `STOM_Version_3U_C`.

Gate status after Page 1:

| Gate | Result |
|---|---|
| broker-neutral | pass |
| DB-neutral | pass |
| pyd-neutral | pass |
| Kiwoom-compatible | pass, because the existing 2U_C file/path remains in place |
| micro-candidate | pass, four in-place edits in one existing file |
| mock-testable | pass, NTP response, `win32api.SetSystemTime`, `time.sleep`, and `windowQ` can be mocked |

Page 1 decision: continue to Page 2 decision gate for the minimal in-place patch only.

## Progress after Page 2

```text
total progress       [###################-]  95.5%  64 / 67 pages
BP-007A current      [########------------]  40.0%   2 /  5 pages
remaining pages      [############--------]  60.0%   3 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/timesync.py"
```

## Page 2 / 5 - decision gate

Decision: proceed to Page 3 with an in-place patch to `C:/System_Trading/STOM/STOM_V.wt-dev/utility/timesync.py`.

Allowed Page 3 patch:

1. Keep the existing 2U_C path `utility/timesync.py`.
2. Keep the existing 2U_C import boundary `from utility.static import thread_decorator`.
3. Remove only the now-unneeded `from dateutil import tz` import.
4. Add the V3 docstring to the existing function.
5. Replace `astimezone(tz.tzlocal())` with `astimezone()`.
6. Replace the two queue log messages with the V3 Korean messages.
7. Replace bare `except:` with `except Exception:`.

Rejected Page 3 scope:

- No V3 folder move to `utility/sub_process_and_thread/`.
- No `utility.static_method` import split.
- No settings/DB/control module backport.
- No LS API, dashboard, CLI, test-suite, or pyd/UI restructuring.
- No dependency or requirements file change.
- No runtime artifact staging.

Decision evidence:

| Check | Evidence | Result |
|---|---|---|
| broker-neutral | no broker API or market routing touched | pass |
| DB-neutral | no DB path/schema/table/query touched | pass |
| pyd-neutral | no GUI pyd wrapper or inferred pyd file touched | pass |
| Kiwoom-compatible | existing 2U_C `utility.timesync` import path is preserved | pass |
| micro-sized | one existing file, local behavior cleanup/log text only | pass |
| mock-testable | NTP, system-time call, queue output, and sleep can be mocked | pass |

Page 2 result: approve Page 3 minimal patch.

## Progress after Page 3

```text
total progress       [###################-]  97.0%  65 / 67 pages
BP-007A current      [############--------]  60.0%   3 /  5 pages
remaining pages      [########------------]  40.0%   2 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev"
```

## Page 3 / 5 - minimal patch applied

Page 3 applied the approved in-place patch to 2U_C only.

2U_C code commit:

- `61e12951 BP-007A timesync log correction applied` (`BP-007A ???? ?? ??? ????`)

Changed runtime file:

- `utility/timesync.py`

Applied safe subset:

- preserved the 2U_C path `utility/timesync.py`,
- preserved `from utility.static import thread_decorator`,
- removed `from dateutil import tz` from this file,
- added the V3 function docstring,
- changed `astimezone(tz.tzlocal())` to `astimezone()`,
- changed queue messages to the V3 Korean text,
- changed bare `except:` to `except Exception:`.

Verification evidence:

| Command | Result |
|---|---|
| `python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/timesync.py` | passed |
| isolated mock for no-adjust and adjust-then-complete paths | passed |
| `git diff --check -- utility/timesync.py` | passed |
| `git diff --cached --check -- utility/timesync.py` before code commit | passed |

Explicitly not tested:

- live NTP request,
- live `win32api.SetSystemTime`,
- full GUI runtime.

Page 3 result: BP-007A code patch is complete; continue to Page 4 docs sync and registry/update-log closure.

## Progress after Page 4

```text
total progress       [####################]  98.5%  66 / 67 pages
BP-007A current      [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

## Page 4 / 5 - docs sync

Page 4 synchronized the BP-007A decision and applied scope into the active carry-forward/update-log surfaces.

Synced documents:

- `docs/update_log/2026-05-07_v3_2uc_bp007a_timesync_cycle.md`
- `docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md`
- `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
- `docs/CARRY_FORWARD_REGISTRY.md`

BP-007A status after Page 4:

| Item | Value |
|---|---|
| Backport ID | `2UC-V3-BP-007A` |
| Source V3 versions | `STOM V3.0`, `STOM V3.11` |
| Source commits | `06b70418`, `dbab03b3` |
| Source path | `utility/sub_process_and_thread/timesync.py` |
| Target path | `utility/timesync.py` |
| 2U_C code commit | `61e12951` |
| Applied scope | in-place timesync cleanup/log text only |
| Excluded scope | V3 file move, `static_method`, settings/DB split, LS API, pyd/UI changes |
| Verification | py_compile, isolated mock, diff check |

Page 4 result: docs are synchronized; continue to Page 5 final guard.

## Progress after Page 5

```text
total progress       [####################] 100.0%  67 / 67 pages
BP-007A current      [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  0 pages
```

Next OMX command:

```powershell
omx cancel
```

## Page 5 / 5 - final guard

Page 5 final guard passed after BP-007A Page 4 docs sync.

Final verification evidence:

| Guard | Result |
|---|---|
| root status | clean on `STOM_Version_2`, ahead 61 |
| 2U_C status | clean on `STOM_Version_2U_C`, ahead 52 |
| `python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/timesync.py` | passed |
| `python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py` | `release sync preflight passed` |
| `python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev` | `release sync preflight passed` |
| root forbidden artifact guard | no tracked `_database`, `_log`, `*.db`, `backtest/graph/*` |
| 2U_C forbidden artifact guard | no tracked `_database`, `_log`, `*.db`, `backtest/graph/*` |
| `STOM_Version_3U_C` branch guard | branch absent |
| native subagents | drained; both reports received |

BP-007A final status:

- Completed as the only safe micro-candidate found in this re-audit loop.
- No additional safe V3 -> 2U_C candidate is opened after BP-007A.
- Remaining V3 differences stay excluded/held under the existing rules: LS API, DB migration, pyd/UI restructuring, broad backtest/trade/dashboard/CLI/test changes, sound/process split wiring, and AnalyzerRisk runtime wiring.

Stop condition: satisfied after final verification and Page 5 documentation.
