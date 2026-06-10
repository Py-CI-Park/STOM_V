# P1 Route Contract

Status: `done`

## Changes

- `/strategy_code` now preserves existing HTTP 200/no-throw behavior and adds:
  - `ok`
  - `gen_no`
  - `code_status`
  - `reason`
- `/strategy_diff` now exposes:
  - `ok`
  - `diff_status`
  - `reason`
- Missing/invalid dashboard states are represented in JSON payloads instead of relying on HTTP 404.

## Status Values Covered

| Route | State | Result |
|---|---|---|
| `/strategy_code` | missing run | `code_status=missing_run` |
| `/strategy_code` | missing generation | `code_status=missing_generation` |
| `/strategy_code` | existing generation but no DB code | `code_status=empty_code` |
| `/strategy_code` | code exists | `code_status=ok` |
| `/strategy_diff` | missing run | `diff_status=missing_run` |
| `/strategy_diff` | missing generation | `diff_status=missing_generation` |
| `/strategy_diff` | gen0 previous diff | `diff_status=no_previous_generation` |
| `/strategy_diff` | normal diff | `diff_status=ok` |

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_profit_codeview.py::TestStrategyCodeEndpoint tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_route_parity.py -q
```

Result: `12 passed in 9.28s`

Manual HTTP smoke:

- Artifact: `p1-p4-curl-smoke.txt`
- `/health`: HTTP 200
- `/strategy_code`: HTTP 200, `code_status=missing_run`
- `/strategy_diff?gen_no=1`: HTTP 200, `diff_status=missing_run`
- `/ui/`: HTTP 200

## Cleanup

- Owned dashboard server PID `88576` was stopped.
- No listener remained on port `8796`.

