# P2 C_T And Control Strategy Time-Filter Inspection

Status: `complete`

Raw artifact: `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p2-strategy-timefilter-inspect.json`

## Strategy Facts

| Strategy | Kind | Exists | Lines | Required call | Static time hints |
|---|---|---:|---:|---|---|
| `C_T_900_920_U2_B` | buy | yes | `431` | `self.Buy` | `90500`, `91000`, `91500`, `92000` |
| `C_T_900_920_U2_S` | sell | yes | `87` | `self.Sell` | `92000`, `93000` |
| `Tick_B_902_905_Update_2` | buy | yes | `128` | `self.Buy` | `90200`, `90500` |
| `Tick_S_902_905_Update_2` | sell | yes | `47` | `self.Sell` | `93000` |

## Static Hints

- C_T buy code has branches around `09:05`, `09:10`, `09:15`, and `09:20`.
- C_T sell code has a general pre-`09:30` branch and `09:20` forced-exit branch.
- Control buy code is explicitly targeted around `09:02..09:05`.
- Therefore the fair same-window active candidate for P3/P4 is `2025-01-03 09:02:00..09:05:00`.

These are static hints only. They do not prove overfire, no-trade behavior, or future profitability.

## QA

| Scenario | Result |
|---|---|
| Strategy code available | pass; all four strategies exist and required calls are present |
| Static hints are not overclaimed | pass; this evidence labels time filters as hints only |

## Adversarial Notes

- Stale state: strategy code was read through `ai_strategy_loop.controller.loop._read_strategy_code`.
- Misleading success: code existence is not counted as runtime success.
- Prompt injection: no AI/export/live path was invoked.
