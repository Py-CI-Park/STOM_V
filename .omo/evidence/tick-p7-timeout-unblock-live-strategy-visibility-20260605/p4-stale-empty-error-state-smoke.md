# P4 Stale Empty Error State Smoke

Status: `done`

## Empty/Error States

Implemented and verified:

- `/strategy_code` missing run: HTTP 200 + `code_status=missing_run`
- `/strategy_code` missing generation: HTTP 200 + `code_status=missing_generation`
- `/strategy_code` existing generation with no code: HTTP 200 + `code_status=empty_code`
- `/strategy_diff` missing run: HTTP 200 + `diff_status=missing_run`
- `/strategy_diff` missing generation: HTTP 200 + `diff_status=missing_generation`
- `/strategy_diff` gen0: HTTP 200 + `diff_status=no_previous_generation`

The frontend panel displays `code_status` and `diff_status` explicitly and shows fetch errors in a visible `active strategy fetch error` line.

## Stale Server Handling

P0 found no server on `8770`. P1-P4 manual smoke used an owned alternate port `8796` and did not touch the user's dashboard process.

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_profit_codeview.py::TestStrategyCodeEndpoint tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_strategy_prompt_frontend.py -q
```

Result: `18 passed in 9.29s`

## Cleanup

- Owned dashboard PID `88576` stopped.
- No `8796` listener remained.
