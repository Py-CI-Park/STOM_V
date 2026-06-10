# P2 Active Strategy Contract

Status: `done`

## Contract

The main-page active strategy source is resolved in this order:

1. completed run winner;
2. best strategy;
3. latest finalized generation;
4. streaming partial generation;
5. no strategy.

The panel reads identity from `/status` state and fetches full code separately through `/strategy_code`. Full code is not added to `/status` polling.

## Implementation Surface

- `ai_strategy_loop/dashboard/frontend/panels.jsx`
  - added `ActiveStrategyPanel`
  - added `_activeStrategyFromState`
  - added `_activeStrategyGenNo`
- `ai_strategy_loop/dashboard/frontend/app.jsx`
  - mounts `<ActiveStrategyPanel state={state} baseUrl={baseUrl} onViewCode={onViewCodeByGen} />`

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py -q
```

Covered by the combined P1-P4 run: `18 passed in 9.29s`.

## Guardrail

The active strategy panel fetches full code by selected run/gen only. It does not perform heavy DB code reads inside `/status`.

