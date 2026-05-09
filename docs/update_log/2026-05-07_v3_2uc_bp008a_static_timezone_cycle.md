# 2UC-V3-BP-008A static timezone cleanup cycle

## Scope

`2UC-V3-BP-008A` is opened after the BP-007A final guard because the fresh V3-vs-2U_C inventory still shows one residual V3.11 dependency-cleanup sub-candidate that can be isolated without broad-merging V3.

Candidate boundary:

| Item | Value |
|---|---|
| Backport ID | `2UC-V3-BP-008A` |
| Source V3 version | `STOM V3.11` |
| Source commit | `dbab03b3` |
| Source update item | `pytz, dateutil, tzlocal ????? ??` |
| Source file evidence | `utility/static_method/static_datetime.py` uses stdlib `datetime.timezone.utc` and `zoneinfo.ZoneInfo` for CME DST calculation |
| Target file | `utility/static.py` in `STOM_Version_2U_C` |
| Candidate type | in-place static timezone dependency cleanup only |
| Explicit exclusions | V3 `utility/static_method/` split, requirements cleanup, telegram bot timezone cleanup, DB/settings split, LS API, pyd/UI changes, runtime wiring changes |

## Page 1 / 5 - read-only inventory

Fresh inventory evidence was generated at:

- `.omx/logs/v3_2uc_remaining_inventory_20260507T103436Z/`
- `name_status_v3_vs_2uc.txt`
- `numstat_v3_vs_2uc.txt`
- `stat_v3_vs_2uc.txt`
- `dirstat_files_v3_vs_2uc.txt`
- `summary.json`

Inventory summary:

| Metric | Value |
|---|---:|
| name-status lines | 1006 |
| unique paths | 1116 |
| modified paths | 26 |
| added paths in 2U_C-vs-V3 direction | structural / custom only |
| deleted V3-source paths in 2U_C target | broad V3/UI/trade/static split surfaces |
| forbidden runtime artifact paths | 0 |

Residual timezone evidence in 2U_C:

| File | Evidence | Page 1 decision input |
|---|---|---|
| `utility/static.py` | imports `pytz`; computes CME DST with `pytz.utc` and `pytz.timezone('America/Chicago')` | safe sub-candidate for stdlib `zoneinfo` substitution |
| `utility/telegram_bot.py` | imports `pytz` for bot timezone | excluded from BP-008A to keep this candidate one-file and avoid telegram runtime scope |
| `requirements32.txt`, `requirements64.txt` | still list `pytz`/`tzlocal`/`python-dateutil` | excluded from BP-008A because dependency removal can affect non-code install surfaces |

Gate check:

| Gate | Result |
|---|---|
| broker-neutral | pass; timezone calculation does not touch Kiwoom/LS broker APIs |
| DB-neutral | pass; no schema/query/migration change |
| pyd-neutral | pass; no GUI pyd or wrapper boundary change |
| Kiwoom-compatible | pass; target remains `utility/static.py` and existing function names/exports remain unchanged |
| micro-candidate | pass; expected change is a few lines in one file |
| mock-testable | pass; DST equivalence can be checked with stdlib `zoneinfo` vs current `pytz` for fixed UTC dates |

Sidecar audit note: native subagents re-affirmed the broad no-more state and did not propose a candidate. The local Page 1 grep narrowed a smaller residual V3.11 sub-candidate than their broad scope reports: `utility/static.py` timezone dependency cleanup only.

## Progress after Page 1

```text
total progress       [###################-]  94.4%  68 / 72 pages
BP-008A current      [####----------------]  20.0%   1 /  5 pages
remaining pages      [################----]  80.0%   4 /  5 pages
```

Current page: BP-008A Page 1 / 5 read-only inventory
Remaining pages: 4

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "git -C C:/System_Trading/STOM/STOM_V.wt-3 show --stat --oneline dbab03b3 -- utility/static_method/static_datetime.py; Select-String -Path C:/System_Trading/STOM/STOM_V.wt-dev/utility/static.py -Pattern 'pytz|ZoneInfo|now_cme|summer_t'"
```


## Page 2 / 5 - decision

Page 2 decision: proceed with a minimal 2U_C-only patch in Page 3.

Decision basis:

| Check | Result |
|---|---|
| Existing 2U_C code | `utility/static.py` imports `pytz` only for UTC/CME DST bootstrap |
| V3 reference | `utility/static_method/static_datetime.py` uses stdlib `datetime.timezone.utc` and `zoneinfo.ZoneInfo('America/Chicago')` |
| Target shape | Keep the monolithic 2U_C `utility/static.py`; do not introduce `utility/static_method/` |
| Patch size | Replace `pytz` import and two timezone bootstrap calls only |
| Runtime surface | existing functions/variables `summer_t`, `time_gap`, `summer_time`, `now_cme()` remain unchanged |
| Mock test shape | compare `pytz` vs `ZoneInfo` DST offsets for fixed UTC winter/summer/current dates before applying; after applying, py_compile and code grep verify `utility/static.py` has no `pytz` import |

Approved Page 3 patch:

1. Replace `import pytz` with `from zoneinfo import ZoneInfo` in `utility/static.py`.
2. Replace `datetime.datetime.now(pytz.utc)` with `datetime.datetime.now(datetime.timezone.utc)`.
3. Replace `pytz.timezone('America/Chicago')` with `ZoneInfo('America/Chicago')`.

Explicitly not approved in this cycle:

- `utility/telegram_bot.py` timezone cleanup.
- Removing `pytz`, `tzlocal`, or `python-dateutil` from requirements files.
- Importing or creating V3 `utility/static_method/` modules in 2U_C.
- Any LS API, DB, pyd/UI, or AnalyzerRisk runtime wiring change.

## Progress after Page 2

```text
total progress       [###################-]  95.8%  69 / 72 pages
BP-008A current      [########------------]  40.0%   2 /  5 pages
remaining pages      [############--------]  60.0%   3 /  5 pages
```

Current page: BP-008A Page 2 / 5 decision
Remaining pages: 3

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/static.py; python - <<'PY'
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytz
for dt in [datetime(2026,1,15,tzinfo=timezone.utc), datetime(2026,7,15,tzinfo=timezone.utc)]:
    assert dt.astimezone(pytz.timezone('America/Chicago')).dst() == dt.astimezone(ZoneInfo('America/Chicago')).dst()
print('timezone equivalence passed')
PY"
```


## Page 3 / 5 - minimal patch applied

Page 3 applied the approved 2U_C-only patch.

2U_C code commit:

- `6e4c10a0 BP-008A static timezone dependency? ????`

Changed runtime file:

- `utility/static.py`

Applied safe subset:

- preserved the existing 2U_C monolithic `utility/static.py` module and all exported function/variable names,
- replaced only the CME DST bootstrap dependency from `pytz` to stdlib `zoneinfo`,
- changed UTC bootstrap to `datetime.timezone.utc`,
- left `utility/telegram_bot.py`, requirements files, and V3 `utility/static_method/` split untouched.

Verification evidence:

| Command | Result |
|---|---|
| `python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/static.py` | passed |
| fixed UTC winter/summer/current Chicago DST equivalence mock (`pytz` vs `ZoneInfo`) | passed |
| `git diff --check -- utility/static.py` | passed |
| `git diff --cached --check -- utility/static.py` before code commit | passed |
| changed runtime files | `utility/static.py` only |

Explicitly not tested:

- full GUI/runtime launch,
- live broker runtime,
- dependency removal from installer/requirements files.

Page 3 result: BP-008A code patch is complete; continue to Page 4 docs sync and registry/update-log closure.

## Progress after Page 3

```text
total progress       [###################-]  97.2%  70 / 72 pages
BP-008A current      [############--------]  60.0%   3 /  5 pages
remaining pages      [########------------]  40.0%   2 /  5 pages
```

Current page: BP-008A Page 3 / 5 minimal patch
Remaining pages: 2

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev log -1 --oneline"
```


## Page 4 / 5 - docs sync

Page 4 synchronized the BP-008A decision and applied scope into the active carry-forward/update-log surfaces.

Synced documents:

- `docs/update_log/2026-05-07_v3_2uc_bp008a_static_timezone_cycle.md`
- `docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md`
- `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
- `docs/CARRY_FORWARD_REGISTRY.md`

BP-008A status after Page 4:

| Item | Value |
|---|---|
| Backport ID | `2UC-V3-BP-008A` |
| Source V3 version | `STOM V3.11` |
| Source commit | `dbab03b3` |
| Source path | `utility/static_method/static_datetime.py` |
| Target path | `utility/static.py` |
| 2U_C code commit | `6e4c10a0` |
| Applied scope | in-place `pytz` to stdlib `zoneinfo` substitution for CME DST bootstrap only |
| Excluded scope | V3 `utility/static_method/` split, telegram bot cleanup, requirements cleanup, LS API, DB migration, pyd/UI changes |
| Verification | py_compile, DST equivalence mock, diff check, cached diff check |

Page 4 result: docs are synchronized; continue to Page 5 final guard.

## Progress after Page 4

```text
total progress       [####################]  98.6%  71 / 72 pages
BP-008A current      [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Current page: BP-008A Page 4 / 5 docs sync
Remaining pages: 1

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```


## Page 5 / 5 - final guard

Page 5 final guard passed after BP-008A Page 4 docs sync.

Final verification evidence:

| Guard | Result |
|---|---|
| root status | clean on `STOM_Version_2` before Page 5 doc append |
| 2U_C status | clean on `STOM_Version_2U_C` before Page 5 doc append |
| `python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/static.py` | passed |
| timezone grep | `utility/static.py` uses `ZoneInfo` and `datetime.timezone.utc`; no `pytz` match in target file |
| `python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py` | `release sync preflight passed` |
| `python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev` | `release sync preflight passed` |
| root forbidden artifact guard | no tracked `_database`, `_log`, `*.db`, `backtest/graph/*` |
| 2U_C forbidden artifact guard | no tracked `_database`, `_log`, `*.db`, `backtest/graph/*` |
| `STOM_Version_3U_C` branch guard | branch absent |
| native subagents | drained; both reports received |

BP-008A final status:

- Completed as exactly one additional safe micro-candidate after BP-007A.
- Applied runtime code only to `STOM_Version_2U_C` in commit `6e4c10a0`.
- Remaining broad V3 differences stay excluded/held under the existing rules: LS API, DB migration, pyd/UI restructuring, broad backtest/trade/dashboard/CLI/test changes, sound/process split wiring, telegram/requirements dependency cleanup, and AnalyzerRisk runtime wiring.

## Progress after Page 5

```text
total progress       [####################] 100.0%  72 / 72 pages
BP-008A current      [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  0 pages
```

Current page: BP-008A Page 5 / 5 final guard
Remaining pages: 0

Next OMX command:

```powershell
omx cancel
```

Stop condition: satisfied after final verification and Page 5 documentation.
