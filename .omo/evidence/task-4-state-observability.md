# Task 4 — Runtime State and Observability Evidence

## Method

SQLite DBs were opened with URI `mode=ro`; no migrations or writes were run. Dashboard export/final approval was not invoked.

## Read-only SQLite Counts

`ai_strategy_loop/state/loop_runs.db`

| table | count |
|---|---:|
| `runs` | 73 |
| `generations` | 400 |
| `prompts` | 184 |
| `equity_points` | 1943 |
| `schema_meta` | 1 |
| `sqlite_sequence` | 1 |

`ai_strategy_loop/state/loop_strategies.db`

| table | count |
|---|---:|
| `stockbuy` | 408 |
| `stocksell` | 405 |
| `formula` | 0 |

## Prior DB Claims

- Prior report claim `equity_points=0`: **stale**. Current count is `1943`.
- Prior report claim `prompts=4`: **stale**. Current count is `184`.

## Dashboard Observability

- `/health`: HTTP 200, `{"status":"ok","contract_version":2}`.
- `/ui/`: HTTP 200, local vendored React/Babel bundle loaded.
- Playwright render: HTTP 200, title `STOM AI · 조건식 자율 진화 대시보드`, body length `13656`.
- Screenshot: `.omo/evidence/dashboard-ui-playwright.png`, 995,615 bytes.
- `/runs`: returned 73 runs, including `tickwide_t0b`, `seed3yr`, `ens_seed_2022full`, `ens_seed_2026full`.
- `/run_state`: current state is idle, while `/status` still returns historical `segrun` complete state. This mismatch is not fatal but should be clarified in UI/API semantics.
- `/backtest_detail?run_id=tickwide_t0b&gen_no=1`: returned daily PnL, cumulative curve, drawdown, holdings; summary trade_count `91`, final_profit `685127`, peak_holdings `5`.
- `/edge_ratio?run_id=tickwide_t0b&fine_time=true`: returned pooled_trades `116`, edge_ratio `1.4039867`, mae_efficiency `0.054057`, losing `상승` change segment total_profit `-459417`, strong `0905-0910×소형` total_profit `1250939`.
- `/feature_importance?run_id=tickwide_t0b&axis=change&fine_time=true`: returned B_* feature rankings and per-change-segment rankings.
- `/adaptive_timing?run_id=ens_seed_2022full&lookback=2`: returned monthly adaptive timing payload.

## Read-only Safety Check

Command: `git status --short -- *.db ai_strategy_loop/state`

Output: empty.

Interpretation: read-only DB inspection did not dirty DB files.

## Observability Gaps

- Good: prompt/equity persistence is now materially better than the prior report.
- Remaining gap: not every run necessarily has CSV/prompts/equity data; demo/current `segrun` lacks CSV and fails analysis endpoints.
- Remaining gap: dashboard shows a lot of useful data, but promotion evidence is still distributed across panels rather than consolidated into a decision card.
