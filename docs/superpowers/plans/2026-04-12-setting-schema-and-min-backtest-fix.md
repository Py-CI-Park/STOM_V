# Setting Schema and Minute Backtest Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `setting.db` load compatibility and official minute backtest day-boundary behavior, then verify with CLI backtests.

**Architecture:** Keep the official V2/2U contracts as the source of truth while preserving `2U_C` CLI and non-release policies. Add a small side-effect-free schema helper for `setting.py`, add a testable day-value helper to `BackEngineBase`, and propagate the validated fix from `STOM_Version_2U_C` to `research/init`.

**Tech Stack:** Python 3.11, pandas, sqlite3, pytest, multiprocessing backtest engine, STOM CLI.

---

## File Structure

- Create: `utility/setting_schema.py`
  - Side-effect-free helpers for current and legacy `back` table column compatibility.
- Modify: `utility/setting.py`
  - Replace the stale `최적화로그기록안함` lookup with the current `백테스트로그기록안함` helper.
- Modify: `backtest/backengine_base.py`
  - Restore official tick/minute day-key behavior through a small static helper.
- Create: `tests/unit/test_setting_schema_contract.py`
  - Unit tests for current and legacy setting column names and static DB creation contract.
- Create: `tests/unit/test_backengine_day_boundary.py`
  - Unit tests for tick and minute day-key extraction.
- Create: `docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md`
  - Post-implementation RCA/update log.
- Propagate after `STOM_Version_2U_C` validation:
  - `C:/System_Trading/STOM/STOM_V.wt-lab` (`research/init`)

Do not modify:

- `C:/System_Trading/STOM/STOM_V` (`STOM_Version_2`)
- `C:/System_Trading/STOM/STOM_V.wt-2u` (`STOM_Version_2U`)
- `C:/System_Trading/STOM/STOM_V.wt-2uc` (`integration/adopt-cli-v267-into-2uc`)

## Task 1: Lock the setting schema contract

**Files:**
- Create: `tests/unit/test_setting_schema_contract.py`
- Create: `utility/setting_schema.py`
- Modify: `utility/setting.py`
- Test: `tests/unit/test_setting_schema_contract.py`

- [ ] **Step 1: Write the failing setting schema tests**

Create `tests/unit/test_setting_schema_contract.py` with this content:

```python
from pathlib import Path

import pandas as pd
import pytest

from utility.setting_schema import (
    CURRENT_BACKTEST_LOG_COLUMN,
    LEGACY_BACKTEST_LOG_COLUMN,
    read_backtest_log_skip,
)


def test_database_check_creates_current_backtest_log_column():
    text = Path("utility/database_check.py").read_text(encoding="utf-8")

    assert '"백테스트로그기록안함"' in text
    assert "'최적화로그기록안함': '백테스트로그기록안함'" in text


def test_setting_loader_reads_current_backtest_log_column():
    df_b = pd.DataFrame([{CURRENT_BACKTEST_LOG_COLUMN: 1}])

    assert read_backtest_log_skip(df_b) == 1


def test_setting_loader_reads_legacy_backtest_log_column():
    df_b = pd.DataFrame([{LEGACY_BACKTEST_LOG_COLUMN: 0}])

    assert read_backtest_log_skip(df_b) == 0


def test_setting_loader_requires_backtest_log_column():
    df_b = pd.DataFrame([{"다른컬럼": 1}])

    with pytest.raises(KeyError) as exc:
        read_backtest_log_skip(df_b)

    assert CURRENT_BACKTEST_LOG_COLUMN in str(exc.value)
```

- [ ] **Step 2: Run the schema tests and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_setting_schema_contract.py -q
```

Expected result:

```text
ERROR tests/unit/test_setting_schema_contract.py
ModuleNotFoundError: No module named 'utility.setting_schema'
```

- [ ] **Step 3: Create the side-effect-free schema helper**

Create `utility/setting_schema.py` with this content:

```python
CURRENT_BACKTEST_LOG_COLUMN = "백테스트로그기록안함"
LEGACY_BACKTEST_LOG_COLUMN = "최적화로그기록안함"


def read_backtest_log_skip(df_b):
    if CURRENT_BACKTEST_LOG_COLUMN in df_b.columns:
        return df_b[CURRENT_BACKTEST_LOG_COLUMN][0]
    if LEGACY_BACKTEST_LOG_COLUMN in df_b.columns:
        return df_b[LEGACY_BACKTEST_LOG_COLUMN][0]
    raise KeyError(CURRENT_BACKTEST_LOG_COLUMN)
```

- [ ] **Step 4: Run the schema tests and verify the helper works but setting.py is still stale**

Run:

```powershell
python -m pytest tests/unit/test_setting_schema_contract.py -q
rg -n "최적화로그기록안함.*df_b|백테스트로그기록안함.*df_b" utility/setting.py utility/setting_user.py -S
```

Expected result:

```text
4 passed
utility/setting.py still contains a df_b lookup for 최적화로그기록안함
utility/setting_user.py contains the current 백테스트로그기록안함 lookup
```

- [ ] **Step 5: Update `utility/setting.py` to use the helper**

In `utility/setting.py`, add this import near the existing imports:

```python
from utility.setting_schema import read_backtest_log_skip
```

Replace the stale `DICT_SET` entry:

```python
'최적화로그기록안함':    df_b['최적화로그기록안함'][0],
```

with:

```python
'백테스트로그기록안함':    read_backtest_log_skip(df_b),
```

- [ ] **Step 6: Verify `setting.py` imports with the regenerated DB**

Run:

```powershell
python -c "from utility.setting import DICT_SET; print('setting import ok'); print(DICT_SET['백테스트로그기록안함'])"
python -m pytest tests/unit/test_setting_schema_contract.py -q
```

Expected result:

```text
setting import ok
4 passed
```

- [ ] **Step 7: Commit the setting schema fix**

Run:

```powershell
git add utility/setting_schema.py utility/setting.py tests/unit/test_setting_schema_contract.py
git commit -m "설정 DB 로그 컬럼 계약을 공식 스키마에 맞춘다" -m "database_check.py는 공식 V2/2U와 같이 백테스트로그기록안함 컬럼을 생성하지만 setting.py가 최적화로그기록안함을 읽고 있어 새 setting.db도 구버전으로 판정됐다." -m "현재 컬럼을 우선 읽고 legacy 컬럼을 fallback으로 허용하는 작은 helper를 추가해 생성/로드 계약을 맞춘다." -m "Constraint: 계정/API/텔레그램 암호화 정책은 유지해야 한다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python -c \"from utility.setting import DICT_SET; print('setting import ok'); print(DICT_SET['백테스트로그기록안함'])\"" -m "Tested: python -m pytest tests/unit/test_setting_schema_contract.py -q"
```

Expected result:

```text
commit created with only utility/setting_schema.py, utility/setting.py, tests/unit/test_setting_schema_contract.py
```

## Task 2: Restore official minute day-boundary behavior

**Files:**
- Create: `tests/unit/test_backengine_day_boundary.py`
- Modify: `backtest/backengine_base.py`
- Test: `tests/unit/test_backengine_day_boundary.py`

- [ ] **Step 1: Write the failing day-boundary tests**

Create `tests/unit/test_backengine_day_boundary.py` with this content:

```python
import numpy as np

from backtest.backengine_base import BackEngineBase


def test_tick_day_values_use_yyyymmdd_from_tick_index():
    indexes = np.array([20250408090000, 20250408151800, 20250409090000], dtype=np.int64)

    assert BackEngineBase.GetDayValues(indexes, is_tick=True).tolist() == [
        20250408,
        20250408,
        20250409,
    ]


def test_minute_day_values_use_yyyymmdd_from_minute_index():
    indexes = np.array([202504080900, 202504081518, 202504090900], dtype=np.int64)

    assert BackEngineBase.GetDayValues(indexes, is_tick=False).tolist() == [
        20250408,
        20250408,
        20250409,
    ]
```

- [ ] **Step 2: Run the day-boundary tests and verify RED**

Run:

```powershell
python -m pytest tests/unit/test_backengine_day_boundary.py -q
```

Expected result:

```text
FAILED tests/unit/test_backengine_day_boundary.py::test_tick_day_values_use_yyyymmdd_from_tick_index
AttributeError: type object 'BackEngineBase' has no attribute 'GetDayValues'
```

- [ ] **Step 3: Add `GetDayValues` to `BackEngineBase`**

In `backtest/backengine_base.py`, add this static method near `CheckDayAndTime`:

```python
    @staticmethod
    def GetDayValues(indexs, is_tick):
        return indexs // 1_000_000 if is_tick else indexs // 10_000
```

- [ ] **Step 4: Replace the stale day-boundary loop**

In `backtest/backengine_base.py`, replace:

```python
                day_last_indexs = indexs // 1000000
                day_last_indexs = [i for i in range(last) if day_last_indexs[i] != day_last_indexs[i + 1]]
                day_last_indexs.append(last)
```

with:

```python
                day_vals = self.GetDayValues(indexs, self.is_tick)
                day_last_indexs = get_np().where(day_vals[:-1] != day_vals[1:])[0]
                day_last_indexs = get_np().concatenate([day_last_indexs, [last]])
```

- [ ] **Step 5: Run the day-boundary tests and verify GREEN**

Run:

```powershell
python -m pytest tests/unit/test_backengine_day_boundary.py -q
```

Expected result:

```text
2 passed
```

- [ ] **Step 6: Commit the day-boundary fix**

Run:

```powershell
git add backtest/backengine_base.py tests/unit/test_backengine_day_boundary.py
git commit -m "분봉 백테스트의 일자 경계를 공식 로직으로 복구한다" -m "분봉 index는 YYYYMMDDHHMM 형식이므로 일자 계산에 10_000 divisor를 사용해야 한다. 현재 2U_C는 tick divisor인 1_000_000을 분봉에도 적용해 월 단위로 상태를 이어갔다." -m "공식 V2/2U의 tick/minute 분기 로직을 현재 lazy NumPy 패턴에 맞춰 복구하고 회귀 테스트로 고정한다." -m "Constraint: 공식 V2/2U와 동일한 날짜 경계 계약을 따라야 한다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python -m pytest tests/unit/test_backengine_day_boundary.py -q"
```

Expected result:

```text
commit created with only backtest/backengine_base.py and tests/unit/test_backengine_day_boundary.py
```

## Task 3: Verify `STOM_Version_2U_C`

**Files:**
- Test: `tests/unit/test_setting_schema_contract.py`
- Test: `tests/unit/test_backengine_day_boundary.py`
- Test: repository unit suite
- Test: CLI real backtest

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
python -m pytest tests/unit/test_setting_schema_contract.py tests/unit/test_backengine_day_boundary.py -q
```

Expected result:

```text
6 passed
```

- [ ] **Step 2: Run adjacent backtest tests**

Run:

```powershell
python -m pytest tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py tests/unit/test_backtest_result_expansion.py tests/unit/test_backengine_shared_memory_cleanup.py -q
```

Expected result:

```text
all selected tests pass
```

- [ ] **Step 3: Run the full unit suite**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected result:

```text
823 or more tests pass, 1 skipped, 0 failed
```

- [ ] **Step 4: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected result:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 5: Run CLI dry-run for the target case**

Run:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --dry-run --format json
```

Expected result:

```json
{"status":"dry-run","buy_strategy":"Min_B_Study_251227","sell_strategy":"Min_S_Study_251227","start_date":20250401,"end_date":20251231,"engine_count":20,"is_tick":false,"dry_run":true}
```

- [ ] **Step 6: Run CLI real backtest for the short window**

Run:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 092800 --timeout 600 --format json --quiet
```

Expected result:

```text
exit code 0
JSON status is success
metrics.trade_count is greater than 0
```

- [ ] **Step 7: Run CLI real backtest for the long window**

Run:

```powershell
python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --timeout 600 --format json --quiet
```

Expected result:

```text
exit code 0
JSON status is success
metrics.trade_count is greater than 0
output does not contain 매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다.
```

## Task 4: Write the update log

**Files:**
- Create: `docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md`

- [ ] **Step 1: Create the update log**

Create `docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md` with this content:

```markdown
# 2026-04-12 설정 DB 스키마와 분봉 일자 경계 복구

## 배경

- 새로 생성한 `setting.db`가 `KeyError: '최적화로그기록안함'`으로 로드되지 않았다.
- 분봉 백테스트에서 `09:00~09:28` 구간은 거래가 발생하지만 `09:00~15:18` 구간은 "매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다."로 끝났다.

## 원인

- DB 생성 경로는 공식 V2/2U처럼 `백테스트로그기록안함`을 생성하지만, `utility/setting.py`가 legacy 컬럼 `최적화로그기록안함`을 읽고 있었다.
- `STOM_Version_2U_C`의 `backtest/backengine_base.py`가 분봉 index `YYYYMMDDHHMM`에도 tick divisor `1_000_000`을 사용해 일자 경계를 월 단위처럼 계산했다.

## 해결

- `setting.py`를 현재 컬럼 `백테스트로그기록안함` 기준으로 정렬하고, legacy 컬럼 `최적화로그기록안함` fallback을 유지했다.
- 분봉 day value 계산을 `index // 10_000`으로 복구하고, tick day value 계산은 `index // 1_000_000`으로 유지했다.

## 브랜치 반영

| 브랜치 | 판단 | 반영 |
| --- | --- | --- |
| `STOM_Version_2` | 공식 로직 정상 | 미반영 |
| `STOM_Version_2U` | 공식 로직 정상 | 미반영 |
| `STOM_Version_2U_C` | 문제 존재 | 반영 |
| `research/init` | 하위 전파 대상 | 반영 예정 |
| `integration/adopt-cli-v267-into-2uc` | 비활성 보관 브랜치 | 제외 |

## 검증

- `python -m pytest tests/unit/test_setting_schema_contract.py tests/unit/test_backengine_day_boundary.py -q`
- `python -m pytest tests/unit/ -q`
- `python scripts/verify_nonrelease_sync.py`
- `python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 092800 --timeout 600 --format json --quiet`
- `python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --timeout 600 --format json --quiet`
```

- [ ] **Step 2: Replace verification bullets with actual outcomes**

After Task 3 completes, edit the `## 검증` section so each command includes the observed result. Use concrete output counts such as `6 passed`, `823 passed, 1 skipped`, exit codes, and CLI trade counts.

- [ ] **Step 3: Run document checks**

Run:

```powershell
$patterns = @(('T' + 'BD'), ('TO' + 'DO'), ('미' + '정'), ('PLACE' + 'HOLDER'))
foreach ($pattern in $patterns) { Select-String -Path docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md -Pattern $pattern -SimpleMatch }
git diff --check -- docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md
```

Expected result:

```text
no placeholder output
git diff --check exits 0
```

- [ ] **Step 4: Commit the update log**

Run:

```powershell
git add docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md
git commit -m "설정 DB와 분봉 일자 경계 복구 기록을 남긴다" -m "새 setting.db 로드 실패와 분봉 긴 시간 구간 백테스트 붕괴의 원인, 브랜치별 반영 여부, 검증 결과를 update log에 기록한다." -m "Constraint: 정규 V2/2U는 수정 불필요하며 active propagation은 2U_C -> research/init이다" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: rg placeholder scan" -m "Tested: git diff --check"
```

Expected result:

```text
commit created with only docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md
```

## Task 5: Propagate to `research/init`

**Files:**
- Modify in `C:/System_Trading/STOM/STOM_V.wt-lab` by cherry-pick:
  - `utility/setting_schema.py`
  - `utility/setting.py`
  - `backtest/backengine_base.py`
  - `tests/unit/test_setting_schema_contract.py`
  - `tests/unit/test_backengine_day_boundary.py`
  - `docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md`

- [ ] **Step 1: Cherry-pick the validated `STOM_Version_2U_C` commits**

In `C:/System_Trading/STOM/STOM_V.wt-lab`, run these commands. They resolve the commit IDs from the already-validated `STOM_Version_2U_C` history by Korean commit title:

```powershell
$settingCommit = git -C C:\System_Trading\STOM\STOM_V.wt-dev log --grep "설정 DB 로그 컬럼 계약을 공식 스키마에 맞춘다" -n 1 --format=%H
$dayBoundaryCommit = git -C C:\System_Trading\STOM\STOM_V.wt-dev log --grep "분봉 백테스트의 일자 경계를 공식 로직으로 복구한다" -n 1 --format=%H
$updateLogCommit = git -C C:\System_Trading\STOM\STOM_V.wt-dev log --grep "설정 DB와 분봉 일자 경계 복구 기록을 남긴다" -n 1 --format=%H
git cherry-pick $settingCommit
git cherry-pick $dayBoundaryCommit
git cherry-pick $updateLogCommit
```

Expected result:

```text
each variable prints a non-empty commit SHA when echoed, and cherry-picks apply cleanly or expose small conflicts in the same files listed above
```

- [ ] **Step 2: Resolve conflicts by preserving research branch policy**

If conflicts occur, keep these rules:

```text
Keep research/init AGENTS.md and branch policy unchanged.
Keep no-serial-key behavior.
Keep the current 백테스트로그기록안함 setting key.
Keep minute day-boundary logic identical to STOM_Version_2U_C after Task 2.
```

- [ ] **Step 3: Run targeted research checks**

Run:

```powershell
python -m pytest tests/unit/test_setting_schema_contract.py tests/unit/test_backengine_day_boundary.py -q
python scripts/verify_nonrelease_sync.py
```

Expected result:

```text
targeted tests pass
non-release sync verifier passes
```

- [ ] **Step 4: Run full research unit suite and record known failures**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected result:

```text
Either all tests pass, or the same pre-existing research failures remain:
tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db
tests/unit/test_exit_codes.py::TestExitCodes::test_execution_error_returns_two
```

- [ ] **Step 5: Commit conflict resolutions if cherry-pick did not auto-commit**

Run only if a cherry-pick stopped for conflicts:

```powershell
git add utility/setting_schema.py utility/setting.py backtest/backengine_base.py tests/unit/test_setting_schema_contract.py tests/unit/test_backengine_day_boundary.py docs/update_log/2026-04-12_setting_schema_and_min_day_boundary_fix.md
git cherry-pick --continue
```

Expected result:

```text
research/init contains the same setting schema and minute day-boundary behavior as STOM_Version_2U_C
```

## Final Verification Checklist

- [ ] `STOM_Version_2U_C` has no unstaged changes except protected `backtest/graph/` output.
- [ ] `research/init` has no unstaged changes after propagation.
- [ ] `integration/adopt-cli-v267-into-2uc` was not modified.
- [ ] `utility.setting` imports successfully with the regenerated `setting.db`.
- [ ] Minute day-boundary tests pass.
- [ ] CLI long-window minute backtest exits successfully and produces trades.
