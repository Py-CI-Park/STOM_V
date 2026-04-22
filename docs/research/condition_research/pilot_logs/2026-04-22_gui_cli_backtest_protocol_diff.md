# GUI/CLI Backtest Protocol Diff

- Date: 2026-04-22
- Branch: `feature/cli-backtest-moneytop-protocol-parity`
- Scope: docs-only protocol investigation. No code, runtime DB, CSV, graph, or temp files were intentionally modified.
- Evidence files: `ui/ui_backtest_engine.py`, `backtest/backtest.py`, `cli/runner.py`

## Evidence Searches

Required searches were run:

```powershell
rg -n "moneytop|GetMoneytopQuery|backengine_start|백테엔진 준비 완료|백테정보|shared_info|back_count|BackTest" ui\ui_backtest_engine.py backtest\backtest.py
rg -n "moneytop|GetMoneytopQuery|shared_info|back_count|BackTest|backQ|get|stock_back_db_selected|csv_detected" cli\runner.py
```

Key hits:

- `ui/ui_backtest_engine.py:82` starts `backengine_start`.
- `ui/ui_backtest_engine.py:161-185` selects the back DB, builds `GetMoneytopQuery(...)`, and reads `df_mt`.
- `ui/ui_backtest_engine.py:269-285` collects `shared_info`, sets `ui.back_count`, sends `('공유데이터', ui.back_count, ui.shared_info)`, and emits `백테엔진 준비 완료`.
- `backtest/backtest.py:254-275` defines `BackTest` and immediately starts it.
- `backtest/backtest.py:280-323` receives the backtest tuple, selects the DB again, builds `GetMoneytopQuery(...)`, and reads `df_mt`.
- `backtest/backtest.py:326-339` treats empty moneytop or zero `back_count` as an error and sends `백테정보` setup data to subtotal workers.
- `backtest/backtest.py:361-362` sends `백테정보` to `Total` with `back_count` and `day_count`.
- `cli/runner.py:217-235` creates queues and records the `backtest.db` rowid watermark.
- `cli/runner.py:279-293` selects the CLI stock back DB, records `stock_back_db_selected`, builds `GetMoneytopQuery(...)`, and reads `df_mt`.
- `cli/runner.py:384-398` collects CLI `shared_info`, checkpoints `back_count`, and sends `('공유데이터', back_count, shared_info)`.
- `cli/runner.py:408-433` puts the 13-tuple on `backQ` and starts the `BackTest` child process.
- `cli/runner.py:455-458` reads metrics from `backtest.db` and checkpoints `csv_detected`.

## GUI Engine Start Stage

`ui/ui_backtest_engine.py:82-285` is the GUI engine preparation path. It reads GUI dates, times, average windows, engine count, division mode, and selected one-code inputs, then creates `BackSubTotal` workers and back engine workers.

For stock backtests, the engine start stage chooses `DB_STOCK_TICK_BACK` or `DB_STOCK_MIN_BACK` from `utility.setting_base` according to `ui.dict_set['주식타임프레임']` (`ui/ui_backtest_engine.py:160-168`). It opens that DB, reads `stockinfo` or `codename`, builds `GetMoneytopQuery(is_tick, 'S', ui.startday, ui.endday, ui.starttime, ui.endtime)`, and reads moneytop into `df_mt` (`ui/ui_backtest_engine.py:170-185`).

After moneytop is read, GUI derives `day_list`, `code_set`, `day_codes`, and `code_days` from the moneytop text (`ui/ui_backtest_engine.py:210-227`). It sends `종목명` and `데이터로딩` messages to child engines, waits for one `shared_info` response per engine, sorts by `shape[0]`, sets `ui.back_count = len(ui.shared_info)`, and sends `('공유데이터', ui.back_count, ui.shared_info)` back to every engine (`ui/ui_backtest_engine.py:250-281`). The stage ends by setting `ui.backtest_engine = True` and emitting `백테엔진 준비 완료` (`ui/ui_backtest_engine.py:283-285`).

## GUI Backtest Execute Stage

`backtest/backtest.py:254-368` is the shared `BackTest` execution stage used after the GUI has prepared engines. `BackTest.Start()` consumes the 13-field tuple from `backQ`; `back_count` is `data[9]` (`backtest/backtest.py:280-296`).

The execute stage selects the DB independently from the engine start stage. For `ui_gubun == 'S'`, it chooses `DB_STOCK_TICK_BACK` or `DB_STOCK_MIN_BACK` from `utility.setting_base` according to `self.dict_set['주식타임프레임']` (`backtest/backtest.py:298-305`). It then reopens the selected DB, reruns `GetMoneytopQuery(is_tick, self.ui_gubun, startday, endday, starttime, endtime)`, and reads `df_mt` (`backtest/backtest.py:321-323`).

If `df_mt` is empty or `back_count == 0`, the child reports the generic no-data/date error and exits (`backtest/backtest.py:326-328`). Otherwise, it derives `day_count`, sends `백테정보` data to subtotal workers, loads buy/sell strategy code from `DB_STRATEGY`, starts `Total`, and sends the final `백테정보` tuple to `Total` with `dict_cn`, `back_count`, `day_count`, blacklist, schedule, and back club values (`backtest/backtest.py:330-362`).

`Total.Report()` later writes summary and trade detail tables to `DB_BACKTEST` from `utility.setting_base` (`backtest/backtest.py:197-204`).

## CLI `run_backtest` Stage

`cli/runner.py:191-462` reproduces the GUI stock flow for headless CLI runs. The parent process imports DB paths from `cli.paths`: `DB_STOCK_BACK_TICK`, `DB_STOCK_BACK_MIN`, and `DB_BACKTEST` (`cli/runner.py:14`). `cli.paths` resolves these from `PROJECT_ROOT/_database` by default and allows environment overrides through `STOM_CLI_DATABASE_DIR`, `STOM_CLI_DB_STOCK_BACK_TICK`, `STOM_CLI_DB_STOCK_BACK_MIN`, and `STOM_CLI_DB_BACKTEST`.

The CLI parent records a `backtest.db` watermark via `_get_backtest_last_rowid()` using `cli.paths.DB_BACKTEST` (`cli/runner.py:41-52`, `cli/runner.py:235-238`). It then starts 20 subtotal workers, starts `config.engine_count` back engines through `_engine_with_dict_set`, selects `db = DB_STOCK_BACK_TICK if config.is_tick else DB_STOCK_BACK_MIN`, records `stock_back_db_selected`, builds `GetMoneytopQuery(config.is_tick, 'S', config.start_date, config.end_date, config.start_time, config.end_time)`, and reads moneytop in the parent (`cli/runner.py:240-298`).

The CLI parent derives `day_list`, `code_set`, `day_codes`, and `code_days`, sends `종목명` and `데이터로딩` to engines, collects one `shared_info` response per engine, sorts by `len`, checkpoints `shared_data_loaded`, sets `back_count = len(shared_info)`, checkpoints `back_count_ready`, and sends `('공유데이터', back_count, shared_info)` to engines (`cli/runner.py:306-398`).

For the backtest execution, the parent sends `('백테유형', '백테스트')`, puts the 13-field tuple on `backQ`, and starts a `BackTest` process through `_engine_with_dict_set` (`cli/runner.py:404-433`). After the child exits, the parent reads metrics from `cli.paths.DB_BACKTEST` through `_extract_metrics()` and records the latest CSV path with `csv_detected` (`cli/runner.py:455-458`, `cli/runner.py:493-508`).

## Moneytop Read Locations

| Location | File/lines | DB source | Query target |
| --- | --- | --- | --- |
| GUI engine start | `ui/ui_backtest_engine.py:160-185` | `utility.setting_base` back DB constants | `GetMoneytopQuery(is_tick, 'S' or 'X', GUI dates/times)` |
| GUI/child backtest execute | `backtest/backtest.py:298-323` | `utility.setting_base` back DB constants | `GetMoneytopQuery(is_tick, self.ui_gubun, tuple dates/times)` |
| CLI parent data load | `cli/runner.py:279-293` | `cli.paths` stock back DB constants | `GetMoneytopQuery(config.is_tick, 'S', config dates/times)` |

The important protocol detail is that moneytop is read twice: once while preparing shared engine data, then again inside `BackTest.Start()` before `백테정보` is sent to the aggregation path.

## Parent/Child DB Path Mismatch Risk

The CLI parent and child do not currently share a single explicit DB path contract.

The CLI parent uses `cli.paths`, which supports absolute project-root paths and CLI-specific environment overrides. The `BackTest` child uses constants imported in `backtest/backtest.py` from `utility.setting_base` (`DB_STOCK_TICK_BACK`, `DB_STOCK_MIN_BACK`, `DB_BACKTEST`). `_engine_with_dict_set()` updates only `DICT_SET` before constructing the engine class (`cli/runner.py:159-174`); it does not rewrite DB constants.

When defaults happen to resolve to the same `./_database` files, this can work by coincidence. When `STOM_CLI_DATABASE_DIR` or a per-DB CLI override is used, the parent can:

- load moneytop and compute `back_count` from one stock back DB,
- start a `BackTest` child that re-queries moneytop from another stock back DB,
- have `Total.Report()` write results to another `backtest.db`,
- then read metrics from the parent-side `cli.paths.DB_BACKTEST`.

That mismatch can produce empty child moneytop, a child `back_count`/`day_count` mismatch, missing metrics, stale metrics, or a timeout that looks like a runtime hang rather than a DB target mismatch.

## Comparison Table

| Item | GUI | CLI current | Risk |
| --- | --- | --- | --- |
| Stock back DB path | Engine start and `BackTest` both use `utility.setting_base` stock back constants. | Parent uses `cli.paths.DB_STOCK_BACK_TICK/MIN`; child `BackTest` uses `utility.setting_base.DB_STOCK_TICK_BACK/MIN`. | Parent and child may read different DB files when CLI path overrides are active. |
| Moneytop read | GUI engine start reads moneytop, and `BackTest` re-reads moneytop from the same constant family. | Parent reads moneytop from `cli.paths`; child re-reads via `BackTest` from `setting_base`. | Parent `back_count` can be based on a different moneytop source than child `day_count` and `백테정보`. |
| Shared data count | `shared_info` is sorted by `shape[0]`; `ui.back_count` is sent as `공유데이터`. | `shared_info` is sorted by `len`; `back_count` is checkpointed and sent as `공유데이터`. | Data shape metadata is not identical in the two parent protocols; mismatches are harder to diagnose without child context. |
| Backtest result DB | `Total.Report()` writes to `utility.setting_base.DB_BACKTEST`. | Parent watermarks and extracts from `cli.paths.DB_BACKTEST`; child/`Total` write through `setting_base.DB_BACKTEST`. | CLI may fail to find the row just written by the child, or may read a stale row from a different DB. |
| Error context | GUI child emits a generic no-data/date error when moneytop is empty or `back_count == 0`. | CLI parent checkpoints parent DB path and row count, but child moneytop failures still report generic context. | A path mismatch can be reported as ordinary no-data, causing the next investigation to look at date/strategy instead of DB target. |
| Process path contract | GUI process family uses the application constants consistently. | `_engine_with_dict_set()` propagates `DICT_SET` only. | CLI path overrides do not automatically reach `BackTest` or `Total`. |

## Concrete Next Targets

1. Child stock back DB path: make the `BackTest` child use the exact stock back DB path selected by the CLI parent, and checkpoint or log that child path.
2. Child backtest DB path: make the child/`Total.Report()` write to the same `backtest.db` that the CLI parent watermarks and reads through `cli.paths.DB_BACKTEST`.
3. Child moneytop query target: expose the child moneytop target as structured context: DB path, `is_tick`, `ui_gubun`, date range, time range, query row count, and `day_count`.
4. Child moneytop error context: when `len(df_mt) == 0` or `back_count == 0`, return or emit child-side error context so CLI results distinguish no source rows, zero prepared shared data, and parent/child DB mismatch.

## Conclusion

The GUI and CLI parent protocols are structurally close: both create subtotal workers, create back engines, read moneytop, derive code/day sets, collect shared data, send `공유데이터`, then start `BackTest`. The remaining parity risk is not the high-level message sequence; it is the DB path boundary between the CLI parent and the `BackTest`/`Total` child path. The next implementation should make those paths explicit and observable before re-running the Wide v1 CLI baseline.
