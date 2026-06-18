# P3 Sell Strategy Generation From Existing Forms

## Verdict

Status: page-complete.

P3 is complete as a research-control-plane evidence step. The `guarded2`
bounded run generated a sell strategy from existing forms, paired it with the
generated time-cap buy strategy, and produced CSV+metrics. Dashboard code/diff
routes also expose the sell code without HTTP 404.

This is not a human-level, OOS, or production-readiness claim.

## Sell Families Reviewed

| Family | Example | Notes |
|---|---|---|
| Tick seed sell | `Tick_S_902_905_Update_2` | baseline tick sell with profit/stop/trailing/order-flow/trend-break exits |
| C_T sell | `C_T_900_920_U2_S` | broader 09:00..09:20 sell with 체결강도 급락, max hold, and post-window forced exit patterns |
| Min simple sell | `AILOOP_min_sell` | minimal profit/loss/hold-time skeleton |
| Min study sell | `Min_S_Study_251227` | min-frame sell with trend break and trailing patterns |
| Generated P2 sell | `AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_sell` | paired with generated P2 buy and produced CSV+metrics |

## Generated Sell Coverage

Generated sell strategy:

```text
AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_sell
```

| Required Exit Type | Evidence In Generated Sell |
|---|---|
| profit taking | `수익률 >= 5`, `등락율 > 29.5` |
| stop loss | `수익률 <= -3.0`, `수익률 <= -2.0 and 현재가 < 최저현재가(...)` |
| trailing give-back | `최고수익률 >= 2.5 and 최고수익률 - 수익률 >= 1.2`; `최고수익률 > 6 and 최고수익률 * 0.6 >= 수익률` |
| 체결강도/order-flow weakening | `(초당매도수량 - 초당매수수량) >= 매수총잔량 * ...` with negative price tick |
| moving-average/trend break | `현재가N(1) >= 이동평균(60, 1) and 이동평균(60) > 현재가` |
| time/hold duration exit | `보유시간 >= 300`, `보유시간 > 60`, `시분초 < 93000` branch |

## Paired Backtest Evidence

Run:

```text
tick_p2_timecap_900_920_preflight_guarded2_20260606
```

Generated pair:

| Field | Value |
|---|---|
| buy | `AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_buy` |
| sell | `AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_sell` |
| status | ok |
| CSV | `backtest/csv\stock_bt_AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_buy_20260606065007.csv` |
| score | 6.903167973883284 |
| gate_passed | true |
| profit | 76,127 |
| trades | 5 |
| MDD | 0.97 |
| payoff_ratio | 2.055147058823529 |
| max_hold_count | 3 |

## Dashboard Visibility

Live dashboard route checks for the same run/gen:

| Route | Result |
|---|---|
| `/strategy_code?run=tick_p2_timecap_900_920_preflight_guarded2_20260606&gen=1` | `200 OK`, returns buy/sell names and code |
| `/strategy_diff?run_id=tick_p2_timecap_900_920_preflight_guarded2_20260606&gen_no=1` | `200 OK`, returns buy/sell diffs against gen0 and prompts |
| `/prompts?run_id=tick_p2_timecap_900_920_preflight_guarded2_20260606&gen_no=1` | `200 OK`, returns 4 prompt rows including the sell prompt |
| `/ai_context_pack?run_id=tick_p2_timecap_900_920_preflight_guarded2_20260606&gen_no=1` | `200 OK`, includes strategy names, config window, prompt count, and forbidden-action warnings |

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_profit_codeview.py -q
# 26 passed
```

Additional P2 verification remains valid for the generated pair:

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_time_cap_bucket_generation.py -q
# 10 passed
```

## UltraQA Notes

- malformed input: dashboard tests cover missing run/gen and missing strategy rows returning non-breaking payloads.
- prompt injection: sell generation stayed in the normal token-checked strategy path; no export/live/final action invoked.
- cancel/resume: P3 used completed P2 bounded run evidence and live route reads only; no new runtime process was spawned.
- stale state: route checks targeted explicit `run_id` and `gen=1`.
- dirty worktree: no unrelated edits or reverts; runtime CSV is evidence only.
- hung or long commands: only bounded curl/test commands were run for P3.
- flaky tests: dashboard code/diff tests passed in a focused suite.
- misleading success: dashboard 200 alone was not counted; paired CSV+metrics and sell coverage were also checked.
- repeated interruptions: this evidence file and ledger entry capture the P3 completion boundary.

## Next

Proceed to P4: make the dashboard live code/diff/prompt/history panel the first-class user-facing workflow, including empty/stale states and browser smoke.
