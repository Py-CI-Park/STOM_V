# V2.68-V2.73 2U Chain Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Propagate `STOM_Version_2` updates `V2.68` through `V2.73` into `STOM_Version_2U`, `STOM_Version_2U_C`, and `STOM_Version_2U_C_CLI_v267` with one version commit per branch per version.

**Architecture:** Use the already-merged `STOM_Version_2` version commits as the canonical source, apply them to `2U` with upstream-first `cherry-pick --no-commit` plus non-release corrections, then propagate the resulting `2U` commits into `2U_C`, and finally into `CLI_v267` with custom-preservation-first conflict handling. Keep commit titles uniform as `STOM V2.68` through `STOM V2.73`, even where older branch docs mention `.U` naming.

**Tech Stack:** Git, PowerShell, Python, `scripts/verify_nonrelease_sync.py`, `pytest tests/unit/ -q`.

---

## Branch Baselines

- `STOM_Version_2U` at `C:\System_Trading\STOM\STOM_V.wt-2u`, head `78a32d1`
- `STOM_Version_2U_C` at `C:\System_Trading\STOM\STOM_V.wt-2uc`, head `e02f270`
- `STOM_Version_2U_C_CLI_v267` at `C:\System_Trading\STOM\STOM_V.wt-dev`, head `8c74e79`

## Source Release Commits

- `V2.68`: `29deac99`
- `V2.69`: `14dbc13d`
- `V2.70`: `8fbb140f`
- `V2.71`: `1bdf4e83`
- `V2.72`: `28ba4bf3`
- `V2.73`: `e8324905`

## Source File Manifests

### V2.68

`_update.txt`, `backtest/back_code_test.py`, `backtest/back_static_numba.py`, `backtest/backengine_base.py`, `backtest/backengine_kiwoom_tick.py`, `backtest/backengine_kiwoom_tick2.py`, `backtest/optimiz_genetic_algorithm.py`, `trade/microstructure_analyzer.py`, `trade/stock_korea/kiwoom_strategy_tick.py`, `trade/stock_korea/kiwoom_trader.py`, `ui/ui_backtest_engine.py`, `ui/ui_show_dialog.py`, `utility/static.py`

### V2.69

`_update.txt`, `backtest/backengine_base.py`, `backtest/backfinder.py`, `backtest/backtest.py`, `backtest/optimiz.py`, `backtest/optimiz_conditions.py`, `backtest/optimiz_genetic_algorithm.py`, `backtest/rolling_walk_forward_test.py`, `trade/binance/binance_receiver_min.py`, `trade/binance/binance_receiver_tick.py`, `trade/binance/binance_strategy_min.py`, `trade/future_oversea/future_agent_min.py`, `trade/future_oversea/future_agent_tick.py`, `trade/future_oversea/future_strategy_min.py`, `trade/microstructure_analyzer.py`, `trade/stock_korea/kiwoom_agent_min.py`, `trade/stock_korea/kiwoom_agent_tick.py`, `trade/stock_korea/kiwoom_strategy_min.py`, `trade/stock_korea/kiwoom_strategy_tick.py`, `trade/stock_korea/kiwoom_trader.py`, `trade/upbit/upbit_receiver_min.py`, `trade/upbit/upbit_receiver_tick.py`, `trade/upbit/upbit_strategy_min.py`, `utility/static.py`, `utility/total_code_line.py`

### V2.70

`_update.txt`, `backtest/backengine_base.py`, `backtest/backengine_base_oms.py`, `trade/binance/binance_receiver_tick.py`, `trade/binance/binance_strategy_tick.py`, `trade/future_oversea/future_agent_tick.py`, `trade/future_oversea/future_strategy_tick.py`, `trade/stock_korea/kiwoom_agent_tick.py`, `trade/stock_korea/kiwoom_strategy_tick.py`, `trade/upbit/upbit_receiver_tick.py`, `trade/upbit/upbit_strategy_tick.py`, `ui/set_dialog_chart.py`, `ui/set_main_menu.py`, `ui/set_order_tap.py`, `ui/set_stg_coin_tap.py`, `ui/set_stg_stock_tap.py`, `ui/set_table.py`, `ui/set_widget.py`, `ui/ui_activated_etc.py`, `ui/ui_button_clicked_settings.py`, `ui/ui_button_clicked_shortcut.py`, `ui/ui_cell_clicked.py`, `ui/ui_checkbox_changed.py`, `ui/ui_draw_chart_base.py`, `ui/ui_draw_chart_db.py`, `ui/ui_draw_chart_real.py`, `ui/ui_draw_crosshair.py`, `ui/ui_draw_jisuchart.py`, `ui/ui_etc.py`, `ui/ui_import_hook.py`, `ui/ui_mainwindow.pyd`, `ui/ui_process_alive.py`, `ui/ui_process_starter.py`, `ui/ui_show_dialog.py`, `ui/ui_update_progressbar.py`, `ui/ui_update_tablewidget.py`, `ui/ui_update_textedit.py`, `utility/chart_hoga_query_sound.py`, `utility/static.py`, `utility/telegram_bot.py`, `utility/webcrawling.py`

### V2.71

`_update.txt`, `backtest/back_code_test.py`, `backtest/backengine_base.py`, `backtest/backengine_future_tick.py`, `backtest/backengine_future_tick2.py`, `backtest/backengine_kiwoom_tick.py`, `backtest/backengine_kiwoom_tick2.py`, `backtest/backengine_upbit_tick.py`, `backtest/backengine_upbit_tick2.py`, `trade/binance/binance_strategy_tick.py`, `trade/future_oversea/future_strategy_tick.py`, `trade/microstructure_analyzer.py`, `trade/risk_analyzer.py`, `trade/stock_korea/kiwoom_strategy_tick.py`, `trade/upbit/upbit_strategy_tick.py`, `ui/set_dialog_back.py`, `ui/set_dialog_etc.py`, `ui/set_dialog_strategy.py`, `ui/set_order_tap.py`, `ui/set_setup_tap.py`, `ui/set_text_stg_button.py`, `ui/ui_button_clicked_settings.py`, `ui/ui_import_hook.py`, `ui/ui_mainwindow.pyd`, `ui/ui_update_tablewidget.py`, `utility/database_check.py`, `utility/setting_base.py`, `utility/setting_user.py`, `utility/telegram_bot.py`, `utility/webcrawling.py`

### V2.72

`_update.txt`, `backtest/back_code_test.py`, `backtest/back_static.py`, `backtest/backengine_base.py`, `backtest/backengine_base_oms.py`, `backtest/backengine_future_min.py`, `backtest/backengine_future_min2.py`, `backtest/backengine_future_tick.py`, `backtest/backengine_future_tick2.py`, `backtest/backengine_kiwoom_min.py`, `backtest/backengine_kiwoom_min2.py`, `backtest/backengine_kiwoom_tick.py`, `backtest/backengine_kiwoom_tick2.py`, `backtest/backengine_upbit_min.py`, `backtest/backengine_upbit_min2.py`, `backtest/backengine_upbit_tick.py`, `backtest/backengine_upbit_tick2.py`, `backtest/backfinder.py`, `backtest/backtest.py`, `backtest/optimiz.py`, `backtest/optimiz_conditions.py`, `backtest/optimiz_genetic_algorithm.py`, `backtest/rolling_walk_forward_test.py`, `trade/binance/binance_strategy_min.py`, `trade/binance/binance_strategy_tick.py`, `trade/future_oversea/future_strategy_min.py`, `trade/future_oversea/future_strategy_tick.py`, `trade/microstructure_analyzer.py`, `trade/risk_analyzer.py`, `trade/stock_korea/kiwoom_rest.py`, `trade/stock_korea/kiwoom_strategy_min.py`, `trade/stock_korea/kiwoom_strategy_tick.py`, `trade/strategy_base.py`, `trade/upbit/upbit_strategy_min.py`, `trade/upbit/upbit_strategy_tick.py`, `ui/set_dialog_formula.py`, `ui/set_home_tap.py`, `ui/ui_button_clicked_dialog_backengine.py`, `ui/ui_button_clicked_editer_coin.py`, `ui/ui_button_clicked_editer_stock.py`, `utility/remove_space.py`, `utility/setting_user.py`, `utility/static.py`

### V2.73

`README.md`, `_update.txt`, `backtest/backengine_future_min.py`, `backtest/backengine_future_min2.py`, `backtest/backengine_future_tick.py`, `backtest/backengine_future_tick2.py`, `backtest/backengine_kiwoom_min.py`, `backtest/backengine_kiwoom_min2.py`, `backtest/backengine_kiwoom_tick.py`, `backtest/backengine_kiwoom_tick2.py`, `backtest/backengine_upbit_min.py`, `backtest/backengine_upbit_min2.py`, `backtest/backengine_upbit_tick.py`, `backtest/backengine_upbit_tick2.py`, `trade/binance/binance_websocket.py`, `trade/upbit/upbit_websocket.py`, `ui/set_widget.py`, `ui/ui_draw_chart_base.py`, `ui/ui_draw_crosshair.py`, `utility/imagefiles/18_주문관리.png`, `utility/imagefiles/25_지수차트.png`, `utility/imagefiles/31_텔레그램_사용자버튼.png`, `utility/imagefiles/32_텔레그램_사용자버튼.png`, `utility/telegram_bot.py`

## CLI Protected Files

`backtest/back_static.py`, `backtest/backengine_base.py`, `backtest/back_subtotal.py`, `utility/setting.py`, `utility/setting_base.py`, `utility/lazy_imports.py`

## 2U pyd Audit Finding

Current inspection against the changed `V2.70` and `V2.71` UI files found no new missing public `self.ui.[Capitalized]` method names relative to the existing `ui/ui_mainwindow.py` in `2U`. The default plan is therefore:

- cherry-pick the version
- remove `ui/ui_mainwindow.pyd`
- rerun the interface audit
- stop only if the audit prints missing methods

### Task 1: Preflight And Safety Tags

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2u\.git`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2uc\.git`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-dev\.git`

- [ ] **Step 1: Verify all three worktrees are on the expected branches with no tracked edits**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2u status --short --branch
git -C C:\System_Trading\STOM\STOM_V.wt-2uc status --short --branch
git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short --branch
```

Expected:
- only the known untracked paths remain

- [ ] **Step 2: Create rollback tags**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2u tag backup/2u-before-v268-v273 78a32d1
git -C C:\System_Trading\STOM\STOM_V.wt-2uc tag backup/2uc-before-v268-v273 e02f270
git -C C:\System_Trading\STOM\STOM_V.wt-dev tag backup/cli-v267-before-v268-v273 8c74e79
```

Expected:
- all three tags are created

### Task 2: Propagate V2.68-V2.73 Into STOM_Version_2U

**Files:**
- Modify: files in the `V2.68` through `V2.73` manifests above
- Modify: `ui/ui_mainwindow.py`
- Remove: `ui/ui_mainwindow.pyd`
- Test: `scripts/verify_nonrelease_sync.py`

- [ ] **Step 1: Apply and commit V2.68**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2u
$src = git log --grep '^STOM V2.68$' --format=%H -n 1 STOM_Version_2
git switch STOM_Version_2U
git cherry-pick --no-commit $src
$pydbins = git ls-files | rg '\.pyd$'
if ($pydbins) { $pydbins | ForEach-Object { git rm -f -- $_ } }
python -m py_compile backtest/back_code_test.py backtest/back_static_numba.py backtest/backengine_base.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/optimiz_genetic_algorithm.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py ui/ui_backtest_engine.py ui/ui_show_dialog.py utility/static.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V268.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/back_static_numba.py backtest/backengine_base.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/optimiz_genetic_algorithm.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py ui/ui_backtest_engine.py ui/ui_show_dialog.py utility/static.py
git commit -F .git\V268.msg
Remove-Item .git\V268.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.68`

- [ ] **Step 2: Apply and commit V2.69**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2u
$src = git log --grep '^STOM V2.69$' --format=%H -n 1 STOM_Version_2
git cherry-pick --no-commit $src
$pydbins = git ls-files | rg '\.pyd$'
if ($pydbins) { $pydbins | ForEach-Object { git rm -f -- $_ } }
python -m py_compile backtest/backengine_base.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_receiver_min.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_min.py trade/future_oversea/future_agent_min.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_min.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_agent_min.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py trade/upbit/upbit_receiver_min.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_min.py utility/static.py utility/total_code_line.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V269.msg -Encoding utf8
git add _update.txt backtest/backengine_base.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_receiver_min.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_min.py trade/future_oversea/future_agent_min.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_min.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_agent_min.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py trade/upbit/upbit_receiver_min.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_min.py utility/static.py utility/total_code_line.py
git commit -F .git\V269.msg
Remove-Item .git\V269.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.69`

- [ ] **Step 3: Apply and commit V2.70**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2uc
$src = git log --grep '^STOM V2.70$' --format=%H -n 1 STOM_Version_2U
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { git checkout --ours -- $file; git add -- $file }
python -m py_compile backtest/backengine_base.py backtest/backengine_base_oms.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_tick.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_chart.py ui/set_main_menu.py ui/set_order_tap.py ui/set_stg_coin_tap.py ui/set_stg_stock_tap.py ui/set_table.py ui/set_widget.py ui/ui_activated_etc.py ui/ui_button_clicked_settings.py ui/ui_button_clicked_shortcut.py ui/ui_cell_clicked.py ui/ui_checkbox_changed.py ui/ui_draw_chart_base.py ui/ui_draw_chart_db.py ui/ui_draw_chart_real.py ui/ui_draw_crosshair.py ui/ui_draw_jisuchart.py ui/ui_etc.py ui/ui_import_hook.py ui/ui_process_alive.py ui/ui_process_starter.py ui/ui_show_dialog.py ui/ui_update_progressbar.py ui/ui_update_tablewidget.py ui/ui_update_textedit.py utility/chart_hoga_query_sound.py utility/static.py utility/telegram_bot.py utility/webcrawling.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V270.msg -Encoding utf8
git add _update.txt backtest/backengine_base.py backtest/backengine_base_oms.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_tick.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_chart.py ui/set_main_menu.py ui/set_order_tap.py ui/set_stg_coin_tap.py ui/set_stg_stock_tap.py ui/set_table.py ui/set_widget.py ui/ui_activated_etc.py ui/ui_button_clicked_settings.py ui/ui_button_clicked_shortcut.py ui/ui_cell_clicked.py ui/ui_checkbox_changed.py ui/ui_draw_chart_base.py ui/ui_draw_chart_db.py ui/ui_draw_chart_real.py ui/ui_draw_crosshair.py ui/ui_draw_jisuchart.py ui/ui_etc.py ui/ui_import_hook.py ui/ui_process_alive.py ui/ui_process_starter.py ui/ui_show_dialog.py ui/ui_update_progressbar.py ui/ui_update_tablewidget.py ui/ui_update_textedit.py utility/chart_hoga_query_sound.py utility/static.py utility/telegram_bot.py utility/webcrawling.py
git commit -F .git\V270.msg
Remove-Item .git\V270.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.70`

- [ ] **Step 4: Apply and commit V2.71**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2uc
$src = git log --grep '^STOM V2.71$' --format=%H -n 1 STOM_Version_2U
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { git checkout --ours -- $file; git add -- $file }
python -m py_compile backtest/back_code_test.py backtest/backengine_base.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_back.py ui/set_dialog_etc.py ui/set_dialog_strategy.py ui/set_order_tap.py ui/set_setup_tap.py ui/set_text_stg_button.py ui/ui_button_clicked_settings.py ui/ui_import_hook.py utility/database_check.py utility/setting_base.py utility/setting_user.py utility/telegram_bot.py utility/webcrawling.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V271.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/backengine_base.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_back.py ui/set_dialog_etc.py ui/set_dialog_strategy.py ui/set_order_tap.py ui/set_setup_tap.py ui/set_text_stg_button.py ui/ui_button_clicked_settings.py ui/ui_import_hook.py utility/database_check.py utility/setting_base.py utility/setting_user.py utility/telegram_bot.py utility/webcrawling.py
git commit -F .git\V271.msg
Remove-Item .git\V271.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.71`

- [ ] **Step 5: Apply and commit V2.72**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2uc
$src = git log --grep '^STOM V2.72$' --format=%H -n 1 STOM_Version_2U
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { git checkout --ours -- $file; git add -- $file }
python -m py_compile backtest/back_code_test.py backtest/back_static.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_strategy_min.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_min.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_rest.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/strategy_base.py trade/upbit/upbit_strategy_min.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_formula.py ui/set_home_tap.py ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py utility/remove_space.py utility/setting_user.py utility/static.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V272.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/back_static.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_strategy_min.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_min.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_rest.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/strategy_base.py trade/upbit/upbit_strategy_min.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_formula.py ui/set_home_tap.py ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py utility/remove_space.py utility/setting_user.py utility/static.py
git commit -F .git\V272.msg
Remove-Item .git\V272.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.72`

- [ ] **Step 6: Apply and commit V2.73**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2uc
$src = git log --grep '^STOM V2.73$' --format=%H -n 1 STOM_Version_2U
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { git checkout --ours -- $file; git add -- $file }
python -m py_compile backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_websocket.py trade/upbit/upbit_websocket.py ui/set_widget.py ui/ui_draw_chart_base.py ui/ui_draw_crosshair.py utility/telegram_bot.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V273.msg -Encoding utf8
git add README.md _update.txt backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_websocket.py trade/upbit/upbit_websocket.py ui/set_widget.py ui/ui_draw_chart_base.py ui/ui_draw_crosshair.py utility/imagefiles/18_주문관리.png utility/imagefiles/25_지수차트.png utility/imagefiles/31_텔레그램_사용자버튼.png utility/imagefiles/32_텔레그램_사용자버튼.png utility/telegram_bot.py
git commit -F .git\V273.msg
Remove-Item .git\V273.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.73`

### Task 4: Propagate V2.68-V2.73 Into STOM_Version_2U_C_CLI_v267

**Files:**
- Modify: files in the `V2.68` through `V2.73` manifests above
- Modify: `backtest/back_static.py`
- Modify: `backtest/backengine_base.py`
- Modify: `backtest/back_subtotal.py`
- Modify: `utility/setting.py`
- Modify: `utility/setting_base.py`
- Modify: `utility/lazy_imports.py`
- Test: `tests/unit/`
- Test: `scripts/verify_nonrelease_sync.py`

- [ ] **Step 1: Apply and commit V2.68**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-dev
$src = git log --grep '^STOM V2.68$' --format=%H -n 1 STOM_Version_2U_C
$protected = @('backtest/back_static.py','backtest/backengine_base.py','backtest/back_subtotal.py','utility/setting.py','utility/setting_base.py','utility/lazy_imports.py')
git switch STOM_Version_2U_C_CLI_v267
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { if ($protected -contains $file) { git checkout --ours -- $file }; git add -- $file }
python -m py_compile backtest/back_code_test.py backtest/back_static_numba.py backtest/backengine_base.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/optimiz_genetic_algorithm.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py ui/ui_backtest_engine.py ui/ui_show_dialog.py utility/static.py
python scripts/verify_nonrelease_sync.py
pytest tests/unit/ -q
git diff --check
git show -s --format=%B $src | Set-Content .git\V268.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/back_static_numba.py backtest/backengine_base.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/optimiz_genetic_algorithm.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py ui/ui_backtest_engine.py ui/ui_show_dialog.py utility/static.py
git commit -F .git\V268.msg
Remove-Item .git\V268.msg
Pop-Location
```

Expected:
- clean verification
- protected CLI files keep branch-local behavior
- commit title `STOM V2.68`

- [ ] **Step 2: Apply and commit V2.69**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-dev
$src = git log --grep '^STOM V2.69$' --format=%H -n 1 STOM_Version_2U_C
$protected = @('backtest/back_static.py','backtest/backengine_base.py','backtest/back_subtotal.py','utility/setting.py','utility/setting_base.py','utility/lazy_imports.py')
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { if ($protected -contains $file) { git checkout --ours -- $file }; git add -- $file }
python -m py_compile backtest/backengine_base.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_receiver_min.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_min.py trade/future_oversea/future_agent_min.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_min.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_agent_min.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py trade/upbit/upbit_receiver_min.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_min.py utility/static.py utility/total_code_line.py
python scripts/verify_nonrelease_sync.py
pytest tests/unit/ -q
git diff --check
git show -s --format=%B $src | Set-Content .git\V269.msg -Encoding utf8
git add _update.txt backtest/backengine_base.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_receiver_min.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_min.py trade/future_oversea/future_agent_min.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_min.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_agent_min.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py trade/upbit/upbit_receiver_min.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_min.py utility/static.py utility/total_code_line.py
git commit -F .git\V269.msg
Remove-Item .git\V269.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.69`

- [ ] **Step 3: Apply and commit V2.70**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-dev
$src = git log --grep '^STOM V2.70$' --format=%H -n 1 STOM_Version_2U_C
$protected = @('backtest/back_static.py','backtest/backengine_base.py','backtest/back_subtotal.py','utility/setting.py','utility/setting_base.py','utility/lazy_imports.py')
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { if ($protected -contains $file) { git checkout --ours -- $file }; git add -- $file }
python -m py_compile backtest/backengine_base.py backtest/backengine_base_oms.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_tick.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_chart.py ui/set_main_menu.py ui/set_order_tap.py ui/set_stg_coin_tap.py ui/set_stg_stock_tap.py ui/set_table.py ui/set_widget.py ui/ui_activated_etc.py ui/ui_button_clicked_settings.py ui/ui_button_clicked_shortcut.py ui/ui_cell_clicked.py ui/ui_checkbox_changed.py ui/ui_draw_chart_base.py ui/ui_draw_chart_db.py ui/ui_draw_chart_real.py ui/ui_draw_crosshair.py ui/ui_draw_jisuchart.py ui/ui_etc.py ui/ui_import_hook.py ui/ui_process_alive.py ui/ui_process_starter.py ui/ui_show_dialog.py ui/ui_update_progressbar.py ui/ui_update_tablewidget.py ui/ui_update_textedit.py utility/chart_hoga_query_sound.py utility/static.py utility/telegram_bot.py utility/webcrawling.py
python scripts/verify_nonrelease_sync.py
pytest tests/unit/ -q
git diff --check
git show -s --format=%B $src | Set-Content .git\V270.msg -Encoding utf8
git add _update.txt backtest/backengine_base.py backtest/backengine_base_oms.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_tick.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_chart.py ui/set_main_menu.py ui/set_order_tap.py ui/set_stg_coin_tap.py ui/set_stg_stock_tap.py ui/set_table.py ui/set_widget.py ui/ui_activated_etc.py ui/ui_button_clicked_settings.py ui/ui_button_clicked_shortcut.py ui/ui_cell_clicked.py ui/ui_checkbox_changed.py ui/ui_draw_chart_base.py ui/ui_draw_chart_db.py ui/ui_draw_chart_real.py ui/ui_draw_crosshair.py ui/ui_draw_jisuchart.py ui/ui_etc.py ui/ui_import_hook.py ui/ui_process_alive.py ui/ui_process_starter.py ui/ui_show_dialog.py ui/ui_update_progressbar.py ui/ui_update_tablewidget.py ui/ui_update_textedit.py utility/chart_hoga_query_sound.py utility/static.py utility/telegram_bot.py utility/webcrawling.py
git commit -F .git\V270.msg
Remove-Item .git\V270.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.70`

- [ ] **Step 4: Apply and commit V2.71**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-dev
$src = git log --grep '^STOM V2.71$' --format=%H -n 1 STOM_Version_2U_C
$protected = @('backtest/back_static.py','backtest/backengine_base.py','backtest/back_subtotal.py','utility/setting.py','utility/setting_base.py','utility/lazy_imports.py')
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { if ($protected -contains $file) { git checkout --ours -- $file }; git add -- $file }
python -m py_compile backtest/back_code_test.py backtest/backengine_base.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_back.py ui/set_dialog_etc.py ui/set_dialog_strategy.py ui/set_order_tap.py ui/set_setup_tap.py ui/set_text_stg_button.py ui/ui_button_clicked_settings.py ui/ui_import_hook.py utility/database_check.py utility/setting_base.py utility/setting_user.py utility/telegram_bot.py utility/webcrawling.py
python scripts/verify_nonrelease_sync.py
pytest tests/unit/ -q
git diff --check
git show -s --format=%B $src | Set-Content .git\V271.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/backengine_base.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_back.py ui/set_dialog_etc.py ui/set_dialog_strategy.py ui/set_order_tap.py ui/set_setup_tap.py ui/set_text_stg_button.py ui/ui_button_clicked_settings.py ui/ui_import_hook.py utility/database_check.py utility/setting_base.py utility/setting_user.py utility/telegram_bot.py utility/webcrawling.py
git commit -F .git\V271.msg
Remove-Item .git\V271.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.71`

- [ ] **Step 5: Apply and commit V2.72**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-dev
$src = git log --grep '^STOM V2.72$' --format=%H -n 1 STOM_Version_2U_C
$protected = @('backtest/back_static.py','backtest/backengine_base.py','backtest/back_subtotal.py','utility/setting.py','utility/setting_base.py','utility/lazy_imports.py')
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { if ($protected -contains $file) { git checkout --ours -- $file }; git add -- $file }
python -m py_compile backtest/back_code_test.py backtest/back_static.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_strategy_min.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_min.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_rest.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/strategy_base.py trade/upbit/upbit_strategy_min.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_formula.py ui/set_home_tap.py ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py utility/remove_space.py utility/setting_user.py utility/static.py
python scripts/verify_nonrelease_sync.py
pytest tests/unit/ -q
git diff --check
git show -s --format=%B $src | Set-Content .git\V272.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/back_static.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_strategy_min.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_min.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_rest.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/strategy_base.py trade/upbit/upbit_strategy_min.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_formula.py ui/set_home_tap.py ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py utility/remove_space.py utility/setting_user.py utility/static.py
git commit -F .git\V272.msg
Remove-Item .git\V272.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.72`

- [ ] **Step 6: Apply and commit V2.73**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-dev
$src = git log --grep '^STOM V2.73$' --format=%H -n 1 STOM_Version_2U_C
$protected = @('backtest/back_static.py','backtest/backengine_base.py','backtest/back_subtotal.py','utility/setting.py','utility/setting_base.py','utility/lazy_imports.py')
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { if ($protected -contains $file) { git checkout --ours -- $file }; git add -- $file }
python -m py_compile backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_websocket.py trade/upbit/upbit_websocket.py ui/set_widget.py ui/ui_draw_chart_base.py ui/ui_draw_crosshair.py utility/telegram_bot.py
python scripts/verify_nonrelease_sync.py
pytest tests/unit/ -q
git diff --check
git show -s --format=%B $src | Set-Content .git\V273.msg -Encoding utf8
git add README.md _update.txt backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_websocket.py trade/upbit/upbit_websocket.py ui/set_widget.py ui/ui_draw_chart_base.py ui/ui_draw_crosshair.py utility/imagefiles/18_주문관리.png utility/imagefiles/25_지수차트.png utility/imagefiles/31_텔레그램_사용자버튼.png utility/imagefiles/32_텔레그램_사용자버튼.png utility/telegram_bot.py
git commit -F .git\V273.msg
Remove-Item .git\V273.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.73`

### Task 5: Final Verification

**Files:**
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2u\.git`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-2uc\.git`
- Modify: `C:\System_Trading\STOM\STOM_V.wt-dev\.git`

- [ ] **Step 1: Verify version history on all branches**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2u log --oneline --decorate -8
git -C C:\System_Trading\STOM\STOM_V.wt-2uc log --oneline --decorate -8
git -C C:\System_Trading\STOM\STOM_V.wt-dev log --oneline --decorate -8
```

Expected:
- each branch shows `STOM V2.68` through `STOM V2.73` after its pre-sync baseline

- [ ] **Step 2: Verify branch guardrails**

Run:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-2u ls-files | rg '\.pyd$'
python C:\System_Trading\STOM\STOM_V.wt-2u\scripts\verify_nonrelease_sync.py
python C:\System_Trading\STOM\STOM_V.wt-2uc\scripts\verify_nonrelease_sync.py
python C:\System_Trading\STOM\STOM_V.wt-dev\scripts\verify_nonrelease_sync.py
pytest -q C:\System_Trading\STOM\STOM_V.wt-dev\tests\unit
git -C C:\System_Trading\STOM\STOM_V.wt-dev ls-files backtest/back_static.py backtest/backengine_base.py backtest/back_subtotal.py utility/setting.py utility/setting_base.py utility/lazy_imports.py
```

Expected:
- `2U` pyd scan prints nothing
- all verify scripts exit `0`
- CLI tests pass
- all six protected CLI files are listed

- [ ] **Step 3: Apply and commit V2.70**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2u
$src = git log --grep '^STOM V2.70$' --format=%H -n 1 STOM_Version_2
git cherry-pick --no-commit $src
git rm -f -- ui/ui_mainwindow.pyd
@'
import re, subprocess, pathlib, sys
repo = pathlib.Path(r'C:\System_Trading\STOM\STOM_V.wt-2u')
text = (repo / 'ui' / 'ui_mainwindow.py').read_text(encoding='utf-8', errors='ignore')
defined = set(re.findall(r'^\s+def\s+([A-Z][A-Za-z0-9_]*)\s*\(', text, re.M))
files = subprocess.check_output(['git','ls-tree','-r','--name-only','STOM_Version_2','ui'], cwd=repo, text=True).splitlines()
called = set()
for f in files:
    if f.endswith('.py'):
        content = subprocess.check_output(['git','show',f'STOM_Version_2:{f}'], cwd=repo, text=True, encoding='utf-8', errors='ignore')
        called.update(re.findall(r'self\.ui\.([A-Z][A-Za-z0-9_]*)', content))
missing = sorted(called - defined)
print('\n'.join(missing))
sys.exit(1 if missing else 0)
'@ | python -
python -m py_compile backtest/backengine_base.py backtest/backengine_base_oms.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_tick.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_chart.py ui/set_main_menu.py ui/set_order_tap.py ui/set_stg_coin_tap.py ui/set_stg_stock_tap.py ui/set_table.py ui/set_widget.py ui/ui_activated_etc.py ui/ui_button_clicked_settings.py ui/ui_button_clicked_shortcut.py ui/ui_cell_clicked.py ui/ui_checkbox_changed.py ui/ui_draw_chart_base.py ui/ui_draw_chart_db.py ui/ui_draw_chart_real.py ui/ui_draw_crosshair.py ui/ui_draw_jisuchart.py ui/ui_etc.py ui/ui_import_hook.py ui/ui_process_alive.py ui/ui_process_starter.py ui/ui_show_dialog.py ui/ui_update_progressbar.py ui/ui_update_tablewidget.py ui/ui_update_textedit.py utility/chart_hoga_query_sound.py utility/static.py utility/telegram_bot.py utility/webcrawling.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V270.msg -Encoding utf8
git add _update.txt backtest/backengine_base.py backtest/backengine_base_oms.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_tick.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_chart.py ui/set_main_menu.py ui/set_order_tap.py ui/set_stg_coin_tap.py ui/set_stg_stock_tap.py ui/set_table.py ui/set_widget.py ui/ui_activated_etc.py ui/ui_button_clicked_settings.py ui/ui_button_clicked_shortcut.py ui/ui_cell_clicked.py ui/ui_checkbox_changed.py ui/ui_draw_chart_base.py ui/ui_draw_chart_db.py ui/ui_draw_chart_real.py ui/ui_draw_crosshair.py ui/ui_draw_jisuchart.py ui/ui_etc.py ui/ui_import_hook.py ui/ui_mainwindow.py ui/ui_process_alive.py ui/ui_process_starter.py ui/ui_show_dialog.py ui/ui_update_progressbar.py ui/ui_update_tablewidget.py ui/ui_update_textedit.py utility/chart_hoga_query_sound.py utility/static.py utility/telegram_bot.py utility/webcrawling.py
git commit -F .git\V270.msg
Remove-Item .git\V270.msg
Pop-Location
```

Expected:
- audit prints nothing
- clean verification
- commit title `STOM V2.70`

- [ ] **Step 4: Apply and commit V2.71**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2u
$src = git log --grep '^STOM V2.71$' --format=%H -n 1 STOM_Version_2
git cherry-pick --no-commit $src
git rm -f -- ui/ui_mainwindow.pyd
@'
import re, subprocess, pathlib, sys
repo = pathlib.Path(r'C:\System_Trading\STOM\STOM_V.wt-2u')
text = (repo / 'ui' / 'ui_mainwindow.py').read_text(encoding='utf-8', errors='ignore')
defined = set(re.findall(r'^\s+def\s+([A-Z][A-Za-z0-9_]*)\s*\(', text, re.M))
files = subprocess.check_output(['git','ls-tree','-r','--name-only','STOM_Version_2','ui'], cwd=repo, text=True).splitlines()
called = set()
for f in files:
    if f.endswith('.py'):
        content = subprocess.check_output(['git','show',f'STOM_Version_2:{f}'], cwd=repo, text=True, encoding='utf-8', errors='ignore')
        called.update(re.findall(r'self\.ui\.([A-Z][A-Za-z0-9_]*)', content))
missing = sorted(called - defined)
print('\n'.join(missing))
sys.exit(1 if missing else 0)
'@ | python -
python -m py_compile backtest/back_code_test.py backtest/backengine_base.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_back.py ui/set_dialog_etc.py ui/set_dialog_strategy.py ui/set_order_tap.py ui/set_setup_tap.py ui/set_text_stg_button.py ui/ui_button_clicked_settings.py ui/ui_import_hook.py ui/ui_update_tablewidget.py utility/database_check.py utility/setting_base.py utility/setting_user.py utility/telegram_bot.py utility/webcrawling.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V271.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/backengine_base.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_back.py ui/set_dialog_etc.py ui/set_dialog_strategy.py ui/set_order_tap.py ui/set_setup_tap.py ui/set_text_stg_button.py ui/ui_button_clicked_settings.py ui/ui_import_hook.py ui/ui_mainwindow.py ui/ui_update_tablewidget.py utility/database_check.py utility/setting_base.py utility/setting_user.py utility/telegram_bot.py utility/webcrawling.py
git commit -F .git\V271.msg
Remove-Item .git\V271.msg
Pop-Location
```

Expected:
- audit prints nothing
- clean verification
- commit title `STOM V2.71`

- [ ] **Step 5: Apply and commit V2.72**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2u
$src = git log --grep '^STOM V2.72$' --format=%H -n 1 STOM_Version_2
git cherry-pick --no-commit $src
$pydbins = git ls-files | rg '\.pyd$'
if ($pydbins) { $pydbins | ForEach-Object { git rm -f -- $_ } }
python -m py_compile backtest/back_code_test.py backtest/back_static.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_strategy_min.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_min.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_rest.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/strategy_base.py trade/upbit/upbit_strategy_min.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_formula.py ui/set_home_tap.py ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py utility/remove_space.py utility/setting_user.py utility/static.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V272.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/back_static.py backtest/backengine_base.py backtest/backengine_base_oms.py backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_strategy_min.py trade/binance/binance_strategy_tick.py trade/future_oversea/future_strategy_min.py trade/future_oversea/future_strategy_tick.py trade/microstructure_analyzer.py trade/risk_analyzer.py trade/stock_korea/kiwoom_rest.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/strategy_base.py trade/upbit/upbit_strategy_min.py trade/upbit/upbit_strategy_tick.py ui/set_dialog_formula.py ui/set_home_tap.py ui/ui_button_clicked_dialog_backengine.py ui/ui_button_clicked_editer_coin.py ui/ui_button_clicked_editer_stock.py utility/remove_space.py utility/setting_user.py utility/static.py
git commit -F .git\V272.msg
Remove-Item .git\V272.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.72`

- [ ] **Step 6: Apply and commit V2.73**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2u
$src = git log --grep '^STOM V2.73$' --format=%H -n 1 STOM_Version_2
git cherry-pick --no-commit $src
$pydbins = git ls-files | rg '\.pyd$'
if ($pydbins) { $pydbins | ForEach-Object { git rm -f -- $_ } }
python -m py_compile backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_websocket.py trade/upbit/upbit_websocket.py ui/set_widget.py ui/ui_draw_chart_base.py ui/ui_draw_crosshair.py utility/telegram_bot.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V273.msg -Encoding utf8
git add README.md _update.txt backtest/backengine_future_min.py backtest/backengine_future_min2.py backtest/backengine_future_tick.py backtest/backengine_future_tick2.py backtest/backengine_kiwoom_min.py backtest/backengine_kiwoom_min2.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/backengine_upbit_min.py backtest/backengine_upbit_min2.py backtest/backengine_upbit_tick.py backtest/backengine_upbit_tick2.py trade/binance/binance_websocket.py trade/upbit/upbit_websocket.py ui/set_widget.py ui/ui_draw_chart_base.py ui/ui_draw_crosshair.py utility/imagefiles/18_주문관리.png utility/imagefiles/25_지수차트.png utility/imagefiles/31_텔레그램_사용자버튼.png utility/imagefiles/32_텔레그램_사용자버튼.png utility/telegram_bot.py
git commit -F .git\V273.msg
Remove-Item .git\V273.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.73`

### Task 3: Propagate V2.68-V2.73 Into STOM_Version_2U_C

**Files:**
- Modify: files in the `V2.68` through `V2.73` manifests above
- Test: `scripts/verify_nonrelease_sync.py`

- [ ] **Step 1: Apply and commit V2.68**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2uc
$src = git log --grep '^STOM V2.68$' --format=%H -n 1 STOM_Version_2U
git switch STOM_Version_2U_C
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { git checkout --ours -- $file; git add -- $file }
python -m py_compile backtest/back_code_test.py backtest/back_static_numba.py backtest/backengine_base.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/optimiz_genetic_algorithm.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py ui/ui_backtest_engine.py ui/ui_show_dialog.py utility/static.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V268.msg -Encoding utf8
git add _update.txt backtest/back_code_test.py backtest/back_static_numba.py backtest/backengine_base.py backtest/backengine_kiwoom_tick.py backtest/backengine_kiwoom_tick2.py backtest/optimiz_genetic_algorithm.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py ui/ui_backtest_engine.py ui/ui_show_dialog.py utility/static.py
git commit -F .git\V268.msg
Remove-Item .git\V268.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.68`

- [ ] **Step 2: Apply and commit V2.69**

Run:

```powershell
Push-Location C:\System_Trading\STOM\STOM_V.wt-2uc
$src = git log --grep '^STOM V2.69$' --format=%H -n 1 STOM_Version_2U
git cherry-pick --no-commit $src
$conflicts = git diff --name-only --diff-filter=U
foreach ($file in $conflicts) { git checkout --ours -- $file; git add -- $file }
python -m py_compile backtest/backengine_base.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_receiver_min.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_min.py trade/future_oversea/future_agent_min.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_min.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_agent_min.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py trade/upbit/upbit_receiver_min.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_min.py utility/static.py utility/total_code_line.py
python scripts/verify_nonrelease_sync.py
git diff --check
git show -s --format=%B $src | Set-Content .git\V269.msg -Encoding utf8
git add _update.txt backtest/backengine_base.py backtest/backfinder.py backtest/backtest.py backtest/optimiz.py backtest/optimiz_conditions.py backtest/optimiz_genetic_algorithm.py backtest/rolling_walk_forward_test.py trade/binance/binance_receiver_min.py trade/binance/binance_receiver_tick.py trade/binance/binance_strategy_min.py trade/future_oversea/future_agent_min.py trade/future_oversea/future_agent_tick.py trade/future_oversea/future_strategy_min.py trade/microstructure_analyzer.py trade/stock_korea/kiwoom_agent_min.py trade/stock_korea/kiwoom_agent_tick.py trade/stock_korea/kiwoom_strategy_min.py trade/stock_korea/kiwoom_strategy_tick.py trade/stock_korea/kiwoom_trader.py trade/upbit/upbit_receiver_min.py trade/upbit/upbit_receiver_tick.py trade/upbit/upbit_strategy_min.py utility/static.py utility/total_code_line.py
git commit -F .git\V269.msg
Remove-Item .git\V269.msg
Pop-Location
```

Expected:
- clean verification
- commit title `STOM V2.69`
