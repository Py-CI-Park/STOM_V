# 2026-04-05 2U_C single-baseline consolidation execution log

## Baseline

- source branch: `STOM_Version_2U_C`
- absorbed branch: `STOM_Version_2U_C_CLI_v267`
- integration branch: `integration/adopt-cli-v267-into-2uc`

## Pre-merge failures

- `tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module`
- `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`

## Pre-merge fixes

- Removed the deleted `ui_activated_coin_stg` / `ui_activated_stock_stg` imports from `ui/ui_mainwindow.py`.
- Kept the baseline import surface stable while removing the stale module references.

## Conflict inventory

- `AGENTS.md`
- `CLAUDE.md`
- `backtest/back_static.py`
- `backtest/back_subtotal.py`
- `backtest/backengine_base.py`
- `backtest/backengine_base_oms.py`
- `backtest/backtest.py`
- `research/auxiliary_indicator/smart_vwap_bands.py`
- `stom.bat`
- `stom_coin.bat`
- `stom_future.bat`
- `stom_stock.bat`
- `ui/ui_button_clicked_dialog_backengine.py`
- `ui/ui_button_clicked_editer_coin.py`
- `ui/ui_button_clicked_editer_stock.py`
- `ui/ui_mainwindow.py`
- `utility/static.py`
- `utility/telegram_bot.py`
- `utility/webcrawling.py`

## Reapplied 2U_C-only fixes

- 8c0d1558: restored telegram queue contract
- b18cb168: cleaned telegram shutdown path
- 249a8514: removed protected worktree sync surface
- 10edf571: hardened non-release sync verifier
- 96265af4: telegram/webcrawling runtime contract
- 1d116161: webcrawling runtime contract test lock
- 23cdce8e: webcrawling timeout contract
- 5a0c5859: webcrawling legacy compatibility

## Final verification

- Initial commit baseline was empty, and the task completed with the expected doc-only rewrite on the integration branch.

## Documentation rewrite

- Active guidance docs were rewritten for the single-baseline `STOM_Version_2U_C` model.
- The live propagation chain is now `V2 -> 2U -> 2U_C -> research/init`.
- `STOM_V.wt-dev/` and `STOM_V.wt-2uc/` now share the same baseline branch in the active docs.
