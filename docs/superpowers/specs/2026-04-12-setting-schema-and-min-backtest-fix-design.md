# 2026-04-12 setting schema and minute backtest fix design

## Context

`STOM_Version_2U_C` is the active baseline checkout, and `research/init` is the downstream research branch. The live propagation path is:

```text
STOM_Version_2 -> STOM_Version_2U -> STOM_Version_2U_C -> research/init
```

`integration/adopt-cli-v267-into-2uc` is an archive/transition checkout and is not part of the active update path.

Two defects are blocking reliable validation:

- A freshly regenerated `setting.db` still fails to load because the database creation path creates `백테스트로그기록안함`, while `utility/setting.py` reads `최적화로그기록안함`.
- Minute backtests in `STOM_Version_2U_C` split loaded rows by `index // 1000000`, which is correct for tick indexes but wrong for minute indexes.

## Goals

- Make newly generated `setting.db` load successfully in `STOM_Version_2U_C`.
- Preserve compatibility with older DBs that may still contain `최적화로그기록안함`.
- Restore official V2/2U minute-day boundary behavior in `STOM_Version_2U_C`.
- Verify the fix with unit tests, non-release sync guards, CLI dry-run, and CLI real backtest when the local DB permits it.
- Propagate the validated fix from `STOM_Version_2U_C` to `research/init`.

## Non-Goals

- Do not modify `STOM_Version_2` or `STOM_Version_2U`; both already have the official DB creation direction and minute-day boundary behavior.
- Do not modify `integration/adopt-cli-v267-into-2uc`; it is an archive branch.
- Do not remove account/API/Telegram encryption from `setting.db`.
- Do not rewrite the backtest engine or strategy execution pipeline beyond the two contract fixes.

## Approach

Use the official V2/2U contracts as the baseline while preserving `2U_C` custom work:

- Keep `database_check.py` aligned with the official schema column `백테스트로그기록안함`.
- Update `setting.py` to read `백테스트로그기록안함`, with fallback support for older `최적화로그기록안함` databases.
- Restore the official day-boundary logic in `backengine_base.py`:
  - tick index `YYYYMMDDHHMMSS` -> `index // 1_000_000`
  - minute index `YYYYMMDDHHMM` -> `index // 10_000`
- Add regression tests so the creation and load contracts cannot drift apart again.

## Components

### Setting Schema Compatibility

`utility/database_check.py` already creates `백테스트로그기록안함` and renames old `최적화로그기록안함` columns to the new name. `utility/setting.py` must match that direction.

The implementation should add a small local helper or inline guarded lookup in `utility/setting.py`:

```python
log_column = '백테스트로그기록안함'
if log_column not in df_b.columns and '최적화로그기록안함' in df_b.columns:
    log_column = '최적화로그기록안함'
```

`DICT_SET` should expose the current key `백테스트로그기록안함`. If existing code still reads `최적화로그기록안함`, keep a compatibility alias only if a grep confirms it is still needed.

### Minute Backtest Day Boundary

The engine must split each loaded symbol array by trading day before calling `LastSell()` and `InitTradeInfo()`. The current `2U_C` logic uses the tick divisor unconditionally, making minute data split by month instead of day.

The implementation should restore the official logic while using the current lazy NumPy accessor:

```python
day_vals = indexs // 1_000_000 if self.is_tick else indexs // 10_000
day_last_indexs = get_np().where(day_vals[:-1] != day_vals[1:])[0]
day_last_indexs = get_np().concatenate([day_last_indexs, [last]])
```

### CLI Verification

After `setting.py` can load the regenerated DB, CLI validation should include:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 `
  --start 20250401 --end 20251231 `
  --timeframe min --avg-time 30 --engines 20 `
  --start-time 090000 --end-time 092800 `
  --timeout 600 --format json --quiet
```

and:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 `
  --start 20250401 --end 20251231 `
  --timeframe min --avg-time 30 --engines 20 `
  --start-time 090000 --end-time 151800 `
  --timeout 600 --format json --quiet
```

The long run must not collapse to "매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다." The exact trade count may differ from the short run because sell/hold paths can change when the available intraday window changes.

## Testing

Add focused unit tests:

- DB schema creation/load compatibility:
  - A generated or fixture-like `back` table with `백테스트로그기록안함` is considered current.
  - A legacy `back` table with only `최적화로그기록안함` remains readable.
- Day-boundary logic:
  - Tick indexes for adjacent dates split by `YYYYMMDD`.
  - Minute indexes for adjacent dates split by `YYYYMMDD`, not `YYYYMM`.

Run in `STOM_Version_2U_C`:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --timeout 600 --format json --quiet
```

Run equivalent targeted checks in `research/init` after propagation. If existing unrelated research-branch unit failures remain, record them as pre-existing verification gaps.

## Update Log

Create an update log after implementation:

```text
docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md
```

The log should state:

- DB creation follows the official `백테스트로그기록안함` schema.
- `setting.py` was behind the official schema and has been aligned.
- Minute day-boundary handling was restored from official V2/2U behavior.
- `STOM_Version_2` and `STOM_Version_2U` required no code change.
- `STOM_Version_2U_C` and `research/init` received the fix.
- `integration/adopt-cli-v267-into-2uc` was intentionally excluded.
