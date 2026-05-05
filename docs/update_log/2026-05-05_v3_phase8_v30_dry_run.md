# V3 Phase 8: STOM V3.0 전용 dry-run 결과

작성일: 2026-05-05  
대상 lane: `STOM_Version_3` 공식 V3 intake  
대상 작업: `STOM V3.0` source apply 전 후보/보호 파일 분류  
기준 문서: `docs/update_log/2026-05-05_v3_phase6_ralph_v30_gate_review.md`

---

## 1. 결론

`STOM V3.0` source apply를 **아직 실행하지 않았다**.

`ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb`를 기준으로 dry-run만 수행했고, 다음 결론을 얻었다.

| 항목 | 결과 |
| --- | ---: |
| 전체 diff row | `499` |
| source 적용 후보 | `463` |
| protected governance 보존 대상 | `36` |
| runtime 제외 대상 | `0` |
| 최신 upstream과 target의 `V3.0` section 일치 | `True` |
| 최신 V3 marker count | `18` |

다음 단계에서 source apply를 진행한다면 반드시 아래 원칙을 지킨다.

1. `source_candidate` 목록만 적용한다.
2. `protected_governance` 목록은 삭제/변경하지 않는다.
3. runtime file은 staging하지 않는다.
4. official V3 lane에서는 `.pyd`를 보존한다.
5. `git add -A`를 사용하지 않는다.
6. `STOM V3.0` formal commit body는 최신 `_update.txt`의 `2026-04-18 V3.0` section 전문을 사용한다.

---

## 2. 사용한 ref

| ref | commit |
| --- | --- |
| base `STOM_Version_3` | `5147349d4cec9c53b61c3e5f7a8aa0dbb2149296` |
| target `ec7db11c` | `ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb` |
| latest upstream `V3.00_latest` | `e42dcfd9e94731f09724c64c7568830854e1433d` |

---

## 3. `V3.0` section 검증

| 항목 | latest upstream | target `ec7db11c` |
| --- | ---: | ---: |
| bytes | `2490` | `2490` |
| lines | `36` | `36` |
| SHA-256 | `d3560b7c970dca3d489375e18da55feaa5d1cd06a2c0e2d2a81046f5edb0d173` | `d3560b7c970dca3d489375e18da55feaa5d1cd06a2c0e2d2a81046f5edb0d173` |

판정: `V3.0` section은 latest upstream과 `ec7db11c`에서 byte 단위로 일치한다.

---

## 4. diff 분류 요약

### class별 count

- `protected_governance`: `36`
- `source_candidate`: `463`

### 전체 status count

- `D`: `219`
- `M`: `22`
- `A`: `135`
- `R`: `123`

### source 후보 status count

- `M`: `22`
- `A`: `135`
- `R`: `123`
- `D`: `183`

### protected governance status count

- `D`: `36`

---

## 5. source 후보 top-level 분포

- `ui`: `153`
- `utility`: `113`
- `trade`: `58`
- `backtest`: `47`
- `dashboard`: `33`
- `research`: `33`
- `(root)`: `16`
- `tests`: `6`
- `ai_agent`: `2`
- `scripts`: `2`

---

## 6. source 후보 확장자 분포

- `.py`: `292`
- `.png`: `106`
- `.tsx`: `13`
- `.bat`: `11`
- `.bmp`: `10`
- `.txt`: `9`
- `.ts`: `5`
- `.json`: `4`
- `.md`: `2`
- `.js`: `2`
- `.html`: `1`
- `.css`: `1`
- `.ico`: `1`
- `.pyd`: `1`
- `.jpg`: `1`
- `.icls`: `1`
- `.xml`: `1`
- `.drawio`: `1`
- `.whl`: `1`

---

## 7. `.pyd` 확인

공식 V3 lane에서는 upstream `.pyd`를 보존한다. pyd 제거는 `STOM_Version_3U`에서만 수행한다.

### base pyd

- `ui/ui_mainwindow.pyd`

### target pyd

- `ui/ui_mainwindow.pyd`

---

## 8. protected governance 보존 대상 전체 목록

다음 파일들은 target upstream에는 없거나 삭제 대상으로 보이지만, 로컬 운영/전환 전략의 기준선이므로 `STOM V3.0` source apply에서 삭제하면 안 된다.

```text
D	.gitignore
D	AGENTS.md
D	CLAUDE.md
D	docs/CARRY_FORWARD_REGISTRY.md
D	docs/FORMAL_UPDATE_OPERATING_SYSTEM.md
D	docs/UPSTREAM_SYNC_STRATEGY.md
D	docs/UPSTREAM_SYNC_STRATEGY_REVIEW.md
D	docs/V3_KICKOFF_READINESS_PLAN.md
D	docs/V3_UPDATE_OPERATING_SYSTEM.md
D	docs/WORKTREE_STRATEGY.md
D	docs/stom_v2_update_guide.md
D	docs/superpowers/plans/2026-03-31-v268-v273-2u-chain-propagation.md
D	docs/superpowers/plans/2026-04-03-upstream-worktree-propagation.md
D	docs/superpowers/plans/2026-04-30-v279-update-wave.md
D	docs/superpowers/specs/2026-03-31-v268-v273-2u-chain-propagation-design.md
D	docs/superpowers/specs/2026-04-03-upstream-worktree-propagation-design.md
D	docs/superpowers/specs/2026-04-04-v274-v277-downstream-propagation-design.md
D	docs/superpowers/specs/2026-04-04-v274-v277-release-sync-design.md
D	docs/superpowers/specs/2026-04-04-v275-2u-2uc-blocker-fix-design.md
D	docs/superpowers/specs/2026-04-04-v275-2uc-webcrawling-compatibility-design.md
D	docs/superpowers/specs/2026-04-04-v275-2uc-webcrawling-contract-design.md
D	docs/superpowers/specs/2026-04-05-formal-update-operating-system-design.md
D	docs/superpowers/specs/2026-04-30-v279-update-wave-design.md
D	docs/update_log/2026-04-04_v274_v277_downstream_baseline_audit.md
D	docs/update_log/2026-04-04_v275_2u_2uc_blocker_audit.md
D	docs/update_log/2026-04-05_v274_v277_cycle_status.md
D	docs/update_log/2026-04-30_v279_update_resume_context.md
D	docs/update_log/2026-05-01_v278_v279_cycle_status.md
D	docs/update_log/2026-05-04_v3_transition_strategy_review.md
D	docs/update_log/2026-05-05_v3_official_intake_plan.md
D	docs/update_log/2026-05-05_v3_phase2_upstream_source_confirmation.md
D	docs/update_log/2026-05-05_v3_phase3_worktree_creation.md
D	docs/update_log/2026-05-05_v3_phase4_runtime_db_bootstrap.md
D	docs/update_log/2026-05-05_v3_phase6_preflight_dry_run.md
D	docs/update_log/2026-05-05_v3_phase6_ralph_v30_gate_review.md
D	docs/update_log/2026-05-05_v3_phase6_team_runtime_attempt.md
```

---

## 9. runtime 제외 대상 전체 목록

```text
(none)
```

---

## 10. source 적용 후보 전체 목록

다음 목록은 다음 단계의 source apply 후보이다. 실제 적용 시에는 status별로 다르게 처리해야 한다.

- `M`: target의 파일 내용으로 checkout 가능
- `A`: target의 파일을 checkout
- `D`: 로컬 source 파일 삭제 가능. 단 protected/runtime이면 삭제 금지
- `R`: old path 삭제와 new path checkout을 함께 검토. 이 목록에서는 effective target path가 source 후보로 분류되어 있다.

```text
M	README.md
M	_license.txt
M	_update.txt
A	ai_agent/rules.md
R091	utility/ai_agent/strategy.txt	ai_agent/strategy.txt
M	backtest/back_code_test.py
M	backtest/back_static.py
M	backtest/back_static_numba.py
M	backtest/back_subtotal.py
M	backtest/backengine_base.py
M	backtest/backengine_base_oms.py
D	backtest/backengine_binance_min.py
D	backtest/backengine_binance_min2.py
D	backtest/backengine_binance_tick.py
D	backtest/backengine_binance_tick2.py
D	backtest/backengine_future_min.py
D	backtest/backengine_future_min2.py
D	backtest/backengine_future_tick.py
D	backtest/backengine_future_tick2.py
D	backtest/backengine_kiwoom_min.py
D	backtest/backengine_kiwoom_min2.py
D	backtest/backengine_kiwoom_tick.py
D	backtest/backengine_kiwoom_tick2.py
D	backtest/backengine_upbit_min.py
D	backtest/backengine_upbit_min2.py
D	backtest/backengine_upbit_tick.py
D	backtest/backengine_upbit_tick2.py
M	backtest/backfinder.py
M	backtest/backtest.py
R100	research/__init__.py	backtest/binance/__init__.py
A	backtest/binance/backengine_binance.py
A	backtest/binance/backengine_binance_oms.py
R100	research/auxiliary_indicator/__init__.py	backtest/future/__init__.py
A	backtest/future/backengine_future.py
A	backtest/future/backengine_future_oms.py
R100	trade/future_oversea/login_future/__init__.py	backtest/future_oversea/__init__.py
A	backtest/future_oversea/backengine_future_oversea.py
A	backtest/future_oversea/backengine_future_oversea_oms.py
M	backtest/optimiz.py
M	backtest/optimiz_3d_visualization.py
M	backtest/optimiz_conditions.py
M	backtest/optimiz_genetic_algorithm.py
M	backtest/rolling_walk_forward_test.py
R100	trade/stock_korea/login_kiwoom/__init__.py	backtest/stock_korea/__init__.py
A	backtest/stock_korea/backengine_stock.py
A	backtest/stock_korea/backengine_stock_oms.py
R100	utility/blacklist_coin.txt	backtest/stock_usa/__init__.py
A	backtest/stock_usa/backengine_stock_usa.py
A	backtest/stock_usa/backengine_stock_usa_oms.py
R100	utility/blacklist_future.txt	backtest/upbit/__init__.py
A	backtest/upbit/backengine_upbit.py
A	backtest/upbit/backengine_upbit_oms.py
A	dashboard/__init__.py
A	dashboard/backend/__init__.py
A	dashboard/backend/database.py
A	dashboard/backend/main.py
A	dashboard/backend/requirements.txt
A	dashboard/backend/web_socket.py
A	dashboard/dashboard_starter.py
A	dashboard/frontend/index.html
A	dashboard/frontend/package-lock.json
A	dashboard/frontend/package.json
A	dashboard/frontend/postcss.config.js
A	dashboard/frontend/src/App.tsx
A	dashboard/frontend/src/components/AlertPanel.tsx
A	dashboard/frontend/src/components/ChegeolTable.tsx
A	dashboard/frontend/src/components/JangoTable.tsx
A	dashboard/frontend/src/components/SummaryCards.tsx
A	dashboard/frontend/src/components/TradeTable.tsx
A	dashboard/frontend/src/components/ui/alert.tsx
A	dashboard/frontend/src/components/ui/button.tsx
A	dashboard/frontend/src/components/ui/card.tsx
A	dashboard/frontend/src/components/ui/table.tsx
A	dashboard/frontend/src/components/ui/tabs.tsx
A	dashboard/frontend/src/hooks/useWebSocket.ts
A	dashboard/frontend/src/index.css
A	dashboard/frontend/src/lib/utils.ts
A	dashboard/frontend/src/main.tsx
A	dashboard/frontend/src/pages/Dashboard.tsx
A	dashboard/frontend/src/types/index.ts
A	dashboard/frontend/src/vite-env.d.ts
A	dashboard/frontend/tailwind.config.js
A	dashboard/frontend/tsconfig.json
A	dashboard/frontend/tsconfig.node.json
A	dashboard/frontend/vite.config.ts
A	npm_uninstall.bat
R084	pip_install_64.bat	pip_install.bat
D	pip_install_32.bat
A	pip_install_wd.bat
D	requirements32.txt
D	requirements64-2.txt
D	research/H1H2_L1L2_lines.py
D	research/analyzer/__init__.py
D	research/analyzer/advanced_manipulation_detector.py
D	research/analyzer/advanced_portfolio_optimizer.py
D	research/analyzer/korean_news_analyzer.py
D	research/analyzer/microstructure_analyzer.py
D	research/analyzer/portfolio_optimizer.py
D	research/analyzer/realtime_volatility_analyzer.py
D	research/analyzer/risk_analyzer.py
D	research/analyzer/test_microstructure_analyzer.py
D	research/auxiliary_indicator/H1H2_L1L2_lines.py
D	research/auxiliary_indicator/smart_vwap_bands.py
D	research/auxiliary_indicator/supply_demand_lines.py
D	research/auxiliary_indicator/test_tracking_money_chart.py
D	research/deeplearning/__init__.py
D	research/deeplearning/backtest_integration.py
D	research/deeplearning/config.py
D	research/deeplearning/data_preprocessor.py
D	research/deeplearning/factor_analysis_model.py
D	research/deeplearning/multiprocessing_utils.py
D	research/deeplearning/pca_prediction_model.py
D	research/deeplearning/realtime_deeplearning.py
D	research/deeplearning/run_parallel_models.py
D	research/korean_news_analyzer.py
D	research/microstructure_analyzer.py
D	research/optimal_sell_analyzer.py
D	research/realtime_deeplearning.py
D	research/smart_vwap_bands.py
D	research/supply_demand_lines.py
D	research/test_microstructure_analyzer.py
D	research/test_optimal_sell_analyzer.py
D	research/test_realtime_deeplearning.py
D	research/test_tracking_money_chart.py
D	scripts/stom_v2_update.py
D	scripts/verify_release_sync.py
M	stom.bat
M	stom.py
D	stom_coin.bat
D	stom_future.bat
A	stom_login.bat
D	stom_stock.bat
D	tests/unit/test_formal_update_operating_docs.py
D	tests/unit/test_telegram_network_noise.py
D	tests/unit/test_upstream_sync_docs.py
D	tests/unit/test_upstream_sync_policy.py
D	tests/unit/test_verify_release_sync.py
D	tests/unit/test_webcrawling_network_noise.py
A	trade/analyzer_microstruc.py
R085	trade/risk_analyzer.py	trade/analyzer_risk.py
A	trade/base_receiver.py
M	trade/base_strategy.py
A	trade/base_trader.py
A	trade/binance/binance_receiver.py
D	trade/binance/binance_receiver_min.py
D	trade/binance/binance_receiver_tick.py
A	trade/binance/binance_strategy.py
D	trade/binance/binance_strategy_min.py
D	trade/binance/binance_strategy_tick.py
M	trade/binance/binance_trader.py
A	trade/future/__init__.py
A	trade/future/future_receiver.py
A	trade/future/future_strategy.py
A	trade/future/future_trader.py
D	trade/future_oversea/future_agent_min.py
D	trade/future_oversea/future_agent_tick.py
D	trade/future_oversea/future_manager.py
A	trade/future_oversea/future_os_receiver.py
A	trade/future_oversea/future_os_strategy.py
A	trade/future_oversea/future_os_trader.py
D	trade/future_oversea/future_strategy_min.py
D	trade/future_oversea/future_strategy_tick.py
D	trade/future_oversea/future_trader.py
D	trade/future_oversea/login_future/manuallogin.py
D	trade/future_oversea/login_future/versionupdater.py
R072	trade/formula_manager.py	trade/manager_formula.py
D	trade/microstructure_analyzer.py
R071	trade/binance/binance_websocket.py	trade/restapi_binance.py
A	trade/restapi_ls.py
A	trade/restapi_lsdata.py
A	trade/restapi_upbit.py
A	trade/stg_globals_func.py
D	trade/stock_korea/kiwoom_agent_min.py
D	trade/stock_korea/kiwoom_agent_tick.py
D	trade/stock_korea/kiwoom_manager.py
D	trade/stock_korea/kiwoom_strategy_min.py
D	trade/stock_korea/kiwoom_strategy_tick.py
D	trade/stock_korea/kiwoom_trader.py
D	trade/stock_korea/login_kiwoom/autologin.py
D	trade/stock_korea/login_kiwoom/manuallogin.py
D	trade/stock_korea/login_kiwoom/versionupdater.py
A	trade/stock_korea/stock_receiver.py
A	trade/stock_korea/stock_strategy.py
A	trade/stock_korea/stock_trader.py
A	trade/stock_usa/__init__.py
A	trade/stock_usa/stock_usa_receiver.py
A	trade/stock_usa/stock_usa_strategy.py
A	trade/stock_usa/stock_usa_trader.py
A	trade/upbit/upbit_receiver.py
D	trade/upbit/upbit_receiver_min.py
D	trade/upbit/upbit_receiver_tick.py
D	trade/upbit/upbit_restapi.py
A	trade/upbit/upbit_strategy.py
D	trade/upbit/upbit_strategy_min.py
D	trade/upbit/upbit_strategy_tick.py
M	trade/upbit/upbit_trader.py
R100	ui/icon/ADA.png	ui/_icon/ADA.png
R100	ui/icon/BNB.png	ui/_icon/BNB.png
R100	ui/icon/BTC.png	ui/_icon/BTC.png
R100	ui/icon/DOGE.png	ui/_icon/DOGE.png
R100	ui/icon/ETH.png	ui/_icon/ETH.png
R100	ui/icon/LINK.png	ui/_icon/LINK.png
R100	ui/icon/SOL.png	ui/_icon/SOL.png
R100	ui/icon/XRP.png	ui/_icon/XRP.png
R100	ui/icon/checked.png	ui/_icon/checked.png
R100	ui/icon/down.bmp	ui/_icon/down.bmp
R100	ui/icon/gold.png	ui/_icon/gold.png
R100	ui/icon/high.bmp	ui/_icon/high.bmp
R100	ui/icon/home.png	ui/_icon/home.png
R100	ui/icon/korea.png	ui/_icon/korea.png
R100	ui/icon/live.png	ui/_icon/live.png
R100	ui/icon/log.png	ui/_icon/log.png
R100	ui/icon/log2.png	ui/_icon/log2.png
R100	ui/icon/logo.png	ui/_icon/logo.png
R100	ui/icon/low.bmp	ui/_icon/low.bmp
R100	ui/icon/oilgsl.png	ui/_icon/oilgsl.png
R100	ui/icon/open.bmp	ui/_icon/open.bmp
R100	ui/icon/perb.bmp	ui/_icon/perb.bmp
R100	ui/icon/pers.bmp	ui/_icon/pers.bmp
R100	ui/icon/python.png	ui/_icon/python.png
R100	ui/icon/set.png	ui/_icon/set.png
R100	ui/icon/stom.ico	ui/_icon/stom.ico
R100	ui/icon/stocks.png	ui/_icon/strategy.png
R100	ui/icon/stocks2.png	ui/_icon/strategy2.png
R100	ui/icon/totalb.bmp	ui/_icon/totalb.bmp
R100	ui/icon/totals.bmp	ui/_icon/totals.bmp
R100	ui/icon/stock.png	ui/_icon/trade.png
R100	ui/icon/unchecked.png	ui/_icon/unchecked.png
R100	ui/icon/up.bmp	ui/_icon/up.bmp
R100	ui/icon/usdkrw.png	ui/_icon/usdkrw.png
R100	ui/icon/vi.bmp	ui/_icon/vi.bmp
A	ui/create_widget/__init__.py
R098	ui/ui_dialog_animation.py	ui/create_widget/dialog_animation.py
R089	ui/set_dialog_back.py	ui/create_widget/set_dialog_back.py
R086	ui/set_dialog_chart.py	ui/create_widget/set_dialog_chart.py
R067	ui/set_dialog_etc.py	ui/create_widget/set_dialog_etc.py
R089	ui/set_dialog_formula.py	ui/create_widget/set_dialog_formula.py
R091	ui/set_dialog_strategy.py	ui/create_widget/set_dialog_strategy.py
R095	ui/set_home_tap.py	ui/create_widget/set_home_tap.py
R070	ui/set_icon.py	ui/create_widget/set_icon.py
R069	ui/set_log_tap.py	ui/create_widget/set_log_tap.py
R062	ui/set_main_menu.py	ui/create_widget/set_main_menu.py
A	ui/create_widget/set_order_tap.py
A	ui/create_widget/set_setup_tap.py
R055	ui/set_stg_stock_tap.py	ui/create_widget/set_stg_tap.py
R097	ui/set_style.py	ui/create_widget/set_style.py
A	ui/create_widget/set_table.py
R086	ui/set_text.py	ui/create_widget/set_text.py
R096	ui/set_text_stg_button.py	ui/create_widget/set_text_stg_button.py
R074	ui/set_widget.py	ui/create_widget/set_widget.py
A	ui/draw_chart/__init__.py
R086	ui/ui_draw_chart_base.py	ui/draw_chart/draw_chart_base.py
A	ui/draw_chart/draw_chart_db.py
R067	ui/ui_draw_chart_items.py	ui/draw_chart/draw_chart_items.py
A	ui/draw_chart/draw_chart_real.py
R091	ui/ui_draw_crosshair.py	ui/draw_chart/draw_crosshair.py
R095	ui/ui_draw_home_chart.py	ui/draw_chart/draw_home_chart.py
R079	ui/ui_draw_label_text.py	ui/draw_chart/draw_label_text.py
R094	ui/ui_draw_treemap.py	ui/draw_chart/draw_treemap.py
A	ui/etcetera/__init__.py
A	ui/etcetera/etc.py
A	ui/etcetera/import_hook.py
A	ui/etcetera/load_database.py
R069	ui/ui_process_alive.py	ui/etcetera/process_alive.py
A	ui/etcetera/process_starter.py
R091	ui/ui_splash_screen.py	ui/etcetera/splash_screen.py
A	ui/event_activate/__init__.py
R082	ui/ui_activated_back.py	ui/event_activate/activated_back.py
A	ui/event_activate/activated_etc.py
A	ui/event_activate/activated_stg.py
A	ui/event_change/__init__.py
A	ui/event_change/changed_checkbox.py
R056	ui/ui_text_changed.py	ui/event_change/changed_text.py
A	ui/event_click/__init__.py
R055	ui/ui_backtest_engine.py	ui/event_click/button_clicked_backtest_engine.py
R074	ui/ui_button_clicked_dialog_backengine.py	ui/event_click/button_clicked_backtest_start.py
R063	ui/ui_button_clicked_chart.py	ui/event_click/button_clicked_chart.py
R090	ui/ui_chart_count_change.py	ui/event_click/button_clicked_chart_count.py
A	ui/event_click/button_clicked_database.py
R072	ui/ui_button_clicked_etc.py	ui/event_click/button_clicked_etc.py
R095	ui/ui_button_clicked_dialog_formula.py	ui/event_click/button_clicked_formula.py
A	ui/event_click/button_clicked_order.py
A	ui/event_click/button_clicked_passticks.py
A	ui/event_click/button_clicked_settings.py
A	ui/event_click/button_clicked_shortcut.py
R062	ui/ui_show_dialog.py	ui/event_click/button_clicked_show_dialog.py
R085	ui/ui_button_clicked_editer_stock.py	ui/event_click/button_clicked_stg_editer.py
A	ui/event_click/button_clicked_stg_editer_backlog.py
R061	ui/ui_button_clicked_editer_stg_buy_stock.py	ui/event_click/button_clicked_stg_editer_buy.py
R066	ui/ui_button_clicked_editer_ga_stock.py	ui/event_click/button_clicked_stg_editer_ga.py
R061	ui/ui_button_clicked_editer_opti_stock.py	ui/event_click/button_clicked_stg_editer_opti.py
R061	ui/ui_button_clicked_editer_stg_sell_stock.py	ui/event_click/button_clicked_stg_editer_sell.py
R087	ui/ui_button_clicked_strategy.py	ui/event_click/button_clicked_stg_module.py
R065	ui/ui_strategy_version.py	ui/event_click/button_clicked_strategy_version.py
R073	ui/ui_vars_change.py	ui/event_click/button_clicked_varstext_change.py
R052	ui/ui_button_clicked_zoom.py	ui/event_click/button_clicked_zoom.py
A	ui/event_click/table_cell_clicked.py
A	ui/event_keypress/__init__.py
A	ui/event_keypress/extend_window.py
R073	ui/ui_event_filter.py	ui/event_keypress/overwrite_event_filter.py
A	ui/event_keypress/overwrite_keypress_event.py
R051	ui/ui_return_press.py	ui/event_keypress/overwrite_return_press.py
D	ui/icon/accdel.png
D	ui/icon/backdel.png
D	ui/icon/coin.png
D	ui/icon/coins.png
D	ui/icon/coins2.png
D	ui/icon/dbdel.png
D	ui/icon/start.png
D	ui/icon/total.png
D	ui/set_order_tap.py
D	ui/set_setup_tap.py
D	ui/set_stg_coin_tap.py
D	ui/set_stg_unified_tap.py
D	ui/set_table.py
D	ui/ui_activated_etc.py
D	ui/ui_activated_stg.py
D	ui/ui_button_clicked_dialog_database.py
D	ui/ui_button_clicked_dialog_elapsed_tick_number.py
D	ui/ui_button_clicked_editer_backlog.py
D	ui/ui_button_clicked_editer_coin.py
D	ui/ui_button_clicked_editer_ga_coin.py
D	ui/ui_button_clicked_editer_ga_unified.py
D	ui/ui_button_clicked_editer_opti_coin.py
D	ui/ui_button_clicked_editer_opti_unified.py
D	ui/ui_button_clicked_editer_stg_buy_coin.py
D	ui/ui_button_clicked_editer_stg_buy_unified.py
D	ui/ui_button_clicked_editer_stg_sell_coin.py
D	ui/ui_button_clicked_editer_stg_sell_unified.py
D	ui/ui_button_clicked_editer_unified.py
D	ui/ui_button_clicked_order.py
D	ui/ui_button_clicked_settings.py
D	ui/ui_button_clicked_shortcut.py
D	ui/ui_cell_clicked.py
D	ui/ui_checkbox_changed.py
D	ui/ui_draw_chart_db.py
D	ui/ui_draw_chart_real.py
D	ui/ui_etc.py
D	ui/ui_extend_window.py
D	ui/ui_import_hook.py
D	ui/ui_key_press_event.py
D	ui/ui_load_database.py
M	ui/ui_mainwindow.pyd
D	ui/ui_process_starter.py
D	ui/ui_update_textedit.py
A	ui/update_widget/__init__.py
R080	ui/ui_update_progressbar.py	ui/update_widget/update_progressbar.py
R069	ui/ui_update_tablewidget.py	ui/update_widget/update_tablewidget.py
A	ui/update_widget/update_textedit.py
R089	update_db_20260211.bat	update_db_20260418.bat
A	utility/_imagefiles/00_?덊솕硫?png
A	utility/_imagefiles/01_湲곕낯李?png
A	utility/_imagefiles/02_吏묎퀎李?png
A	utility/_imagefiles/03_?꾨왂?몄쭛湲?png
A	utility/_imagefiles/04_諛깊뙆?몃뜑.png
A	utility/_imagefiles/05_理쒖쟻?뷀렪吏묎린.png
A	utility/_imagefiles/06_?뚯뒪?명렪吏묎린.png
A	utility/_imagefiles/07_?꾩쭊遺꾩꽍.png
A	utility/_imagefiles/08_蹂?섑렪吏묎린.png
A	utility/_imagefiles/09_踰붿쐞?몄쭛湲?png
A	utility/_imagefiles/10_議곌굔?몄쭛湲?png
A	utility/_imagefiles/11_GA?몄쭛湲?png
A	utility/_imagefiles/12_諛깊뀒濡쒓렇.png
A	utility/_imagefiles/13_諛깊뀒湲곕줉.png
R100	utility/imagefiles/14_諛깊뀒湲곕줉_洹몃옒?꾨퉬援?png	utility/_imagefiles/14_諛깊뀒湲곕줉_洹몃옒?꾨퉬援?png
R100	utility/imagefiles/15_諛깊뀒?ㅼ?伊대윭.png	utility/_imagefiles/15_諛깊뀒?ㅼ?伊대윭.png
A	utility/_imagefiles/16_濡쒓렇李?png
A	utility/_imagefiles/17_?ㅼ젙李?png
A	utility/_imagefiles/18_二쇰Ц愿由?png
A	utility/_imagefiles/19_?ㅽ넱?쇱씠釉?png
A	utility/_imagefiles/20_?붾퉬愿由?png
R100	utility/imagefiles/21_源?꾩갹.png	utility/_imagefiles/21_源?꾩갹.png
R100	utility/imagefiles/22_李⑦듃李?png	utility/_imagefiles/22_李⑦듃李?png
R100	utility/imagefiles/23_?섏떇愿由ъ옄.png	utility/_imagefiles/23_?섏떇愿由ъ옄.png
R100	utility/imagefiles/24_?꾨왂紐⑤뱢.png	utility/_imagefiles/24_?꾨왂紐⑤뱢.png
R100	utility/imagefiles/25_?멸?李?png	utility/_imagefiles/25_?멸?李?png
R100	utility/imagefiles/26_湲곗뾽?뺣낫.png	utility/_imagefiles/26_湲곗뾽?뺣낫.png
R100	utility/imagefiles/27_諛깊뀒?붿쭊李?png	utility/_imagefiles/27_諛깊뀒?붿쭊李?png
A	utility/_imagefiles/28_?꾨왂踰꾩쟾愿由?png
R100	utility/imagefiles/29_?낆쥌蹂꾪뀒留덈퀎?몃━留?png	utility/_imagefiles/29_?낆쥌蹂꾪뀒留덈퀎?몃━留?png
R100	utility/imagefiles/30_諛깊뀒寃곌낵洹몃옒??png	utility/_imagefiles/30_諛깊뀒寃곌낵洹몃옒??png
R100	utility/imagefiles/31_諛깊뀒寃곌낵遺媛?뺣낫.png	utility/_imagefiles/31_諛깊뀒寃곌낵遺媛?뺣낫.png
A	utility/_imagefiles/32_?밸??쒕낫??png
R100	utility/imagefiles/parse_dat.png	utility/_imagefiles/parse_dat.png
R100	utility/imagefiles/李멸퀬 援먯감寃利?png	utility/_imagefiles/李멸퀬 援먯감寃利?png
R100	utility/imagefiles/李멸퀬 ?꾩쭊遺꾩꽍.jpg	utility/_imagefiles/李멸퀬 ?꾩쭊遺꾩꽍.jpg
R096	utility/pycharm/Darcula_copy.icls	utility/_pycharm/Darcula_copy.icls
R100	utility/pycharm/Project_Default.xml	utility/_pycharm/Project_Default.xml
R085	utility/remove_space.py	utility/_remove_space.py
R085	utility/total_code_line.py	utility/_total_code_line.py
D	utility/ai_agent/rules.txt
D	utility/blacklist_stock.txt
D	utility/database_check.py
A	utility/db_control/__init__.py
R096	utility/_db_distinct.bat	utility/db_control/_db_distinct.bat
A	utility/db_control/database_check.py
R056	utility/database_read_only.py	utility/db_control/database_read_only.py
R086	utility/db_distinct.py	utility/db_control/db_distinct.py
A	utility/db_control/update_db_20260418.py
D	utility/imagefiles/00_?덊솕硫?png
D	utility/imagefiles/01_湲곕낯李?png
D	utility/imagefiles/02_吏묎퀎李?png
D	utility/imagefiles/03_?꾨왂?몄쭛湲?png
D	utility/imagefiles/04_諛깊뙆?몃뜑.png
D	utility/imagefiles/05_理쒖쟻?뷀렪吏묎린.png
D	utility/imagefiles/06_?뚯뒪?명렪吏묎린.png
D	utility/imagefiles/07_?꾩쭊遺꾩꽍.png
D	utility/imagefiles/08_蹂?섑렪吏묎린.png
D	utility/imagefiles/09_踰붿쐞?몄쭛湲?png
D	utility/imagefiles/10_議곌굔?몄쭛湲?png
D	utility/imagefiles/11_GA?몄쭛湲?png
D	utility/imagefiles/12_諛깊뀒濡쒓렇.png
D	utility/imagefiles/13_諛깊뀒湲곕줉.png
D	utility/imagefiles/16_濡쒓렇李?png
D	utility/imagefiles/17_?ㅼ젙李?png
D	utility/imagefiles/18_二쇰Ц愿由?png
D	utility/imagefiles/19_?ㅽ넱?쇱씠釉?png
D	utility/imagefiles/20_?붾퉬愿由?png
D	utility/imagefiles/24_吏?섏감??png
D	utility/imagefiles/26_?멸?李?png
D	utility/imagefiles/27_湲곗뾽?뺣낫.png
D	utility/imagefiles/28_湲곗뾽?뺣낫.png
D	utility/imagefiles/28_諛깊뀒?붿쭊李?png
D	utility/imagefiles/28_?낆쥌蹂꾪뀒留덈퀎?몃━留?png
D	utility/imagefiles/29_諛깊뀒寃곌낵洹몃옒??png
D	utility/imagefiles/29_?뱀뿏吏꾨럭??png
D	utility/imagefiles/30_諛깊뀒寃곌낵遺媛?뺣낫.png
D	utility/imagefiles/30_?낆쥌蹂꾪뀒留덈퀎?몃━留?png
D	utility/imagefiles/31_諛깊뀒寃곌낵洹몃옒??png
D	utility/imagefiles/31_?붾젅洹몃옩 ?ъ슜?먮쾭??png
D	utility/imagefiles/31_?붾젅洹몃옩_?ъ슜?먮쾭??png
D	utility/imagefiles/32_諛깊뀒寃곌낵遺媛?뺣낫.png
D	utility/imagefiles/32_?붾젅洹몃옩 ?ъ슜?먮쾭??png
D	utility/imagefiles/33_?붾젅洹몃옩 ?ъ슜?먮쾭??png
D	utility/imagefiles/35_鍮꾩쨷議곗젅.png
D	utility/imagefiles/36_諛깊뀒?붿쭊李?png
D	utility/imagefiles/diagram_01.png
D	utility/imagefiles/diagram_02.png
D	utility/imagefiles/stom.drawio
D	utility/profile_utils.py
D	utility/realtime_fid_kiwoom.py
R100	requirements64.txt	utility/requirements.txt
D	utility/setting_base.py
D	utility/setting_user.py
A	utility/settings/__init__.py
A	utility/settings/setting_base.py
A	utility/settings/setting_market.py
A	utility/settings/setting_user.py
A	utility/static_method/__init__.py
R100	utility/numba_rolling.py	utility/static_method/numba_rolling.py
R055	utility/static.py	utility/static_method/static.py
R096	utility/strategy_version_manager.py	utility/static_method/strategy_version_manager.py
R093	utility/syntax.py	utility/static_method/syntax.py
A	utility/sub_process_and_thread/__init__.py
R051	utility/chart_hoga_query_sound.py	utility/sub_process_and_thread/chart_hoga_query_sound.py
R067	utility/kimp_upbit_binance.py	utility/sub_process_and_thread/kimp_upbit_binance.py
R058	utility/telegram_bot.py	utility/sub_process_and_thread/telegram_bot.py
R064	utility/timesync.py	utility/sub_process_and_thread/timesync.py
A	utility/sub_process_and_thread/webcrawling.py
D	utility/ta_lib-0.6.8-cp311-cp311-win32.whl
D	utility/update_db_20260211.py
D	utility/upstream_sync_policy.py
D	utility/webcrawling.py
```

---

## 11. 다음 단계 권장 적용 방식

다음 페이지에서 `STOM V3.0` source apply를 진행한다면, 자동화 스크립트는 다음 guard를 가져야 한다.

1. 이 문서의 기준 commit이 현재 `STOM_Version_3` head와 일치하는지 확인한다.
2. upstream `V3.00_latest`를 다시 fetch하고 새 V3 marker가 생겼는지 확인한다.
3. `ec7db11c`의 `V3.0` section hash가 이 문서의 hash와 일치하는지 확인한다.
4. `protected_governance`와 `runtime_excluded` 목록은 apply 대상에서 제외한다.
5. source 후보 중 `D`와 `R`은 old path가 protected/runtime이 아닌지 다시 확인한다.
6. 적용 후 `git status --short`로 변경 파일이 source 후보 목록 안에만 있는지 확인한다.
7. `git add -A` 없이 source 후보 중 실제 변경된 파일만 stage한다.
8. formal commit title은 `STOM V3.0`으로 한다.
9. formal commit body는 `_update.txt`의 `2026-04-18 V3.0` section 전문으로 한다.

---

## 12. 중단 조건

다음 조건 중 하나라도 발생하면 `STOM V3.0` source apply를 중단한다.

- `STOM_Version_3` worktree에 예상하지 못한 tracked 변경이 있다.
- protected governance 파일이 staged 또는 삭제 상태가 된다.
- `_database`, `_log`, `*.db`, `backtest/graph/`가 staged 된다.
- upstream `V3.00_latest`에 새 V3 marker가 추가된다.
- `V3.0` section SHA-256이 이 문서와 달라진다.
- source 후보 diff가 이 dry-run과 다르게 변한다.

---

## 13. 다음 OMX 명령 후보

```powershell
omx ralph --no-deslop --prompt "V3 Phase 9: apply STOM V3.0 only. Use docs/update_log/2026-05-05_v3_phase8_v30_dry_run.md as the guard. Apply only source_candidate paths from the dry-run against ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb. Preserve .gitignore, AGENTS.md, CLAUDE.md, docs/, _database/, _log/, *.db, and backtest/graph/. Do not use git add -A. Create exactly one formal commit titled STOM V3.0 with the full 2026-04-18 V3.0 _update.txt section as body, then stop and report before V3.01."
```
