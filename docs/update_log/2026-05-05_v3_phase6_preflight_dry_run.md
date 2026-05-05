# V3 Phase 6 preflight dry-run 기록

> [!IMPORTANT]
> ## Ralph fallback 이후 보정 notice
>
> 이 dry-run 문서는 당시 upstream `V3.00`가 `9c8b3a16`일 때의 preflight 결과다.
> 이후 upstream은 `e42dcfd9e94731f09724c64c7568830854e1433d`까지 이동했고, `V3.0` commit body 기준도 `f6cb5057` marker-first-seen에서 `ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb` latest-section-match로 보정되었다.
> 다음 source apply 전에 `docs/update_log/2026-05-05_v3_phase6_ralph_v30_gate_review.md`를 기준으로 `STOM V3.0` 전용 dry-run을 다시 수행한다.
- 작성일: 2026-05-05
- 작성 시각: 2026-05-05 16:55:40 +09:00
- 작업 위치: `C:\System_Trading\STOM\STOM_V`
- 대상 워크트리: `C:\System_Trading\STOM\STOM_V.wt-3`
- 대상 브랜치: `STOM_Version_3`
- 관련 계획: `docs/update_log/2026-05-05_v3_official_intake_plan.md`
- 관련 PRD: `.omx/plans/prd-v3-kickoff-phase-0-11.md`
- 관련 test spec: `.omx/plans/test-spec-v3-kickoff-phase-0-11.md`

## 1. 목적

이 문서는 V3 전환 실행 계획의 **Phase 6. V3 official update 반영**을 시작하기 전 preflight/dry-run 결과를 기록한다.

이번 단계에서는 실제 V3 source 파일을 아직 적용하지 않고, 다음을 검증했다.

1. `$team` runtime 사용 가능성
2. upstream `V3.00` 최신 ref 재확인
3. `_update.txt` V3 marker gate 검증
4. `STOM_V.wt-3` status/runtime/pyd 상태 검증
5. official source snapshot 적용 시 변경될 파일 목록 dry-run 분류
6. protected governance/runtime 영역 보존 필요성 확인

## 2. `$team` runtime 확인

확인 결과:

```text
TMUX=/tmp/psmux-117576/default,62734,0
tmux 3.3.4
omx=C:\Users\parkc\AppData\Roaming\npm\omx.ps1
```

따라서 tmux 기반 `$team` runtime은 사용 가능하다.

다만 이번 실행은 Phase 6의 실제 source mutation이 아니라 **preflight/dry-run gate**이므로 worker pane을 열어 source를 변경하지 않았다. 다음 실제 source 적용 단계에서 `$team`을 worker 분리 방식으로 사용하는 것이 안전하다.

## 3. upstream ref 재확인

실행:

```powershell
git ls-remote --symref https://github.com/devstom/STOM.git HEAD refs/heads/V3.00 refs/tags/V3.0 refs/tags/V2.0
git fetch --no-tags https://github.com/devstom/STOM.git +refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00_latest +refs/tags/V3.0:refs/remotes/devstom_tmp/tags/V3.0 +refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
```

확인된 ref:

| 구분 | ref | commit |
| --- | --- | --- |
| V3 latest | `refs/remotes/devstom_tmp/V3.00_latest` | `9c8b3a166b1fce77691a022d9521cb7833cad0ad` |
| V3 initial tag | `refs/remotes/devstom_tmp/tags/V3.0` | `d21e42425cfc6f2254431e8622b1bbf0dd89303e` |
| V2 base tag | `refs/remotes/devstom_tmp/tags/V2.0` | `873d51eed3f581daa1925bcd9e3672254f525f0a` |

Latest summary:

```text
9c8b3a16 9c8b3a166b1fce77691a022d9521cb7833cad0ad 2026-05-05T16:07:19+09:00 Merge pull request #33 from c-guevara/V3.00
```

Phase 5 문서의 기준 commit `9c8b3a16`과 동일하여 upstream ref gate는 통과했다.

## 4. `_update.txt` marker gate

최신 `_update.txt`에서 V3 marker를 다시 계산했다.

- top marker: `2026-05-04 V3.17`
- oldest marker: `2026-04-18 V3.0`
- marker count: `18`
- Phase 5 계획과 일치: yes

실행 순서:

```text
2026-04-18 V3.0
2026-04-19 V3.01
2026-04-20 V3.02
2026-04-20 V3.03
2026-04-21 V3.04
2026-04-22 V3.05
2026-04-22 V3.06
2026-04-23 V3.07
2026-04-23 V3.08
2026-04-25 V3.09
2026-04-26 V3.10
2026-04-27 V3.11
2026-04-28 V3.12
2026-04-29 V3.13
2026-04-30 V3.14
2026-05-01 V3.15
2026-05-03 V3.16
2026-05-04 V3.17
```

## 5. commit body section 추출 검증

`_update.txt`가 내림차순 구조이므로 section boundary는 다음 V3 marker가 아니라 **다음 version header 전체** 기준으로 계산해야 한다. 이 보정을 적용한 결과는 다음과 같다.

| marker | lines | chars |
| --- | ---: | ---: |
| $(@{marker=2026-04-18 V3.0; chars=1148; lines=35}.marker) | 35 | 1148 |
| $(@{marker=2026-04-19 V3.01; chars=421; lines=14}.marker) | 14 | 421 |
| $(@{marker=2026-04-20 V3.02; chars=469; lines=17}.marker) | 17 | 469 |
| $(@{marker=2026-04-20 V3.03; chars=494; lines=18}.marker) | 18 | 494 |
| $(@{marker=2026-04-21 V3.04; chars=555; lines=13}.marker) | 13 | 555 |
| $(@{marker=2026-04-22 V3.05; chars=414; lines=9}.marker) | 9 | 414 |
| $(@{marker=2026-04-22 V3.06; chars=379; lines=10}.marker) | 10 | 379 |
| $(@{marker=2026-04-23 V3.07; chars=380; lines=15}.marker) | 15 | 380 |
| $(@{marker=2026-04-23 V3.08; chars=843; lines=21}.marker) | 21 | 843 |
| $(@{marker=2026-04-25 V3.09; chars=453; lines=15}.marker) | 15 | 453 |
| $(@{marker=2026-04-26 V3.10; chars=580; lines=13}.marker) | 13 | 580 |
| $(@{marker=2026-04-27 V3.11; chars=272; lines=9}.marker) | 9 | 272 |
| $(@{marker=2026-04-28 V3.12; chars=502; lines=15}.marker) | 15 | 502 |
| $(@{marker=2026-04-29 V3.13; chars=366; lines=13}.marker) | 13 | 366 |
| $(@{marker=2026-04-30 V3.14; chars=269; lines=9}.marker) | 9 | 269 |
| $(@{marker=2026-05-01 V3.15; chars=266; lines=11}.marker) | 11 | 266 |
| $(@{marker=2026-05-03 V3.16; chars=231; lines=9}.marker) | 9 | 231 |
| $(@{marker=2026-05-04 V3.17; chars=658; lines=21}.marker) | 21 | 658 |

이전 dry-run에서 `V3.0` section이 뒤쪽 V2 section까지 포함될 수 있음을 감지했고, 즉시 boundary를 보정했다. Phase 6 formal commit body 생성 시에도 이 boundary 규칙을 사용해야 한다.

## 6. V3 worktree 상태 검증

확인 결과:

```text
git -C ..\STOM_V.wt-3 status --short --branch
=> ## STOM_Version_3

git -C ..\STOM_V.wt-3 status --short --ignored --untracked-files=normal
=> !! _database/
```

판정:

- tracked working tree는 깨끗하다.
- `_database/`는 ignored runtime data로만 존재한다.
- staged runtime file은 없다.

## 7. pyd 상태 검증

현재 `STOM_Version_3` worktree의 pyd:

```text
ui/ui_mainwindow.pyd
```

upstream V3 latest의 pyd:

```text
ui/main_window.pyd
```

판정:

- Phase 6 official source intake에서는 upstream V3 pyd를 보존해야 한다.
- 즉, official V3 lane에서는 `ui/main_window.pyd`가 들어와야 한다.
- pyd 제거는 Phase 10 `STOM_Version_3U`에서만 수행한다.

## 8. dry-run diff summary

비교 기준:

```text
base: STOM_Version_3
latest: 9c8b3a166b1fce77691a022d9521cb7833cad0ad
```

전체 diff row 수: `529`

status별 요약:

```text
- A: 167
- D: 231
- M: 21
- R050: 1
- R051: 2
- R052: 1
- R054: 1
- R055: 3
- R056: 1
- R057: 1
- R059: 1
- R060: 2
- R061: 1
- R063: 1
- R066: 1
- R069: 2
- R070: 2
- R072: 3
- R073: 1
- R074: 1
- R075: 1
- R076: 2
- R078: 1
- R079: 1
- R080: 3
- R081: 2
- R082: 1
- R083: 1
- R085: 2
- R086: 1
- R087: 1
- R089: 2
- R090: 1
- R091: 1
- R092: 1
- R093: 2
- R095: 1
- R096: 3
- R097: 1
- R099: 1
- R100: 56
```

category별 요약:

```text
- official_source_candidate: 496
- protected_local_governance: 33
```

상위 경로별 official source candidate 요약:

```text
- ui: 166
- "utility: 73
- trade: 56
- utility: 52
- backtest: 47
- research: 33
- dashboard: 32
- strategy: 10
- tests: 6
- ai_agent: 2
- scripts: 2
- README.md: 1
- _license.txt: 1
- _update.txt: 1
- npm_uninstall.bat: 1
- pip_install.bat: 1
- pip_install_32.bat: 1
- pip_install_wd.bat: 1
- requirements32.txt: 1
- requirements64-2.txt: 1
- requirements64.txt: 1
- stom.bat: 1
- stom.py: 1
- stom_coin.bat: 1
- stom_future.bat: 1
- stom_login.bat: 1
- stom_stock.bat: 1
- update_db_20260418.bat: 1
```

## 9. 핵심 판정

raw snapshot overlay를 그대로 수행하면 다음 문제가 발생한다.

1. `AGENTS.md`, `docs/`, `CLAUDE.md`, `.gitignore`가 upstream snapshot에 없어서 삭제 후보로 잡힌다.
2. 이 파일들은 V3 전환 운영/검증/guidance의 핵심이므로 삭제하면 안 된다.
3. `_database/`는 tracked diff에는 없지만 ignored runtime data로 존재하므로 stage하면 안 된다.
4. official source candidate는 496건으로 많고 rename/delete가 섞여 있어, `git add -A` 사용은 매우 위험하다.
5. formal commit body section 추출은 header boundary를 정확히 적용해야 한다.

따라서 다음 실제 적용 단계는 반드시 protected file allowlist와 exact staging 목록을 사용해야 한다.

## 10. protected local governance 목록

아래 항목은 raw upstream snapshot 기준으로 삭제 후보지만 보존해야 한다.

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
```

## 11. runtime excluded 목록

```text
(tracked diff에서 runtime 제외 항목 없음)
```

## 12. official source candidate 목록

아래 목록은 Phase 6 source intake에서 검토할 official source candidate다. 실제 적용 시에는 version별 gate와 exact staging을 사용해야 한다.

```text
M	README.md
M	_license.txt
M	_update.txt
A	ai_agent/rules.md
R087	utility/ai_agent/strategy.txt	ai_agent/strategy.txt
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
R072	pip_install_64.bat	pip_install.bat
D	pip_install_32.bat
A	pip_install_wd.bat
D	requirements32.txt
D	requirements64-2.txt
D	requirements64.txt
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
A	strategy/__init__.py
A	strategy/analyzer_candle_pattern.py
A	strategy/analyzer_microstructure.py
A	strategy/analyzer_risk.py
A	strategy/analyzer_volatility_pattern.py
A	strategy/analyzer_volatility_stop_take.py
A	strategy/analyzer_volume_profile.py
A	strategy/analyzer_volume_spike.py
R055	trade/formula_manager.py	strategy/manager_formula.py
A	strategy/stg_globals_func.py
D	tests/unit/test_formal_update_operating_docs.py
D	tests/unit/test_telegram_network_noise.py
D	tests/unit/test_upstream_sync_docs.py
D	tests/unit/test_upstream_sync_policy.py
D	tests/unit/test_verify_release_sync.py
D	tests/unit/test_webcrawling_network_noise.py
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
D	trade/binance/binance_websocket.py
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
D	trade/microstructure_analyzer.py
A	trade/restapi_binance.py
A	trade/restapi_ls.py
A	trade/restapi_lsdata.py
A	trade/restapi_upbit.py
D	trade/risk_analyzer.py
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
R099	ui/ui_dialog_animation.py	ui/create_widget/dialog_animation.py
A	ui/create_widget/dialog_radar_chart.py
R083	ui/set_dialog_back.py	ui/create_widget/set_dialog_back.py
R073	ui/set_dialog_chart.py	ui/create_widget/set_dialog_chart.py
R055	ui/set_dialog_etc.py	ui/create_widget/set_dialog_etc.py
R081	ui/set_dialog_formula.py	ui/create_widget/set_dialog_formula.py
R076	ui/set_dialog_strategy.py	ui/create_widget/set_dialog_strategy.py
R096	ui/set_home_tap.py	ui/create_widget/set_home_tap.py
R070	ui/set_icon.py	ui/create_widget/set_icon.py
R082	ui/set_log_tap.py	ui/create_widget/set_log_tap.py
R059	ui/set_main_menu.py	ui/create_widget/set_main_menu.py
A	ui/create_widget/set_order_tap.py
A	ui/create_widget/set_setup_tap.py
R055	ui/set_stg_stock_tap.py	ui/create_widget/set_stg_tap.py
R097	ui/set_style.py	ui/create_widget/set_style.py
A	ui/create_widget/set_table.py
R086	ui/set_text.py	ui/create_widget/set_text.py
A	ui/create_widget/set_text_stg_button.py
R072	ui/set_widget.py	ui/create_widget/set_widget.py
A	ui/draw_chart/__init__.py
R076	ui/ui_draw_chart_base.py	ui/draw_chart/draw_chart_base.py
A	ui/draw_chart/draw_chart_db.py
R072	ui/ui_draw_chart_items.py	ui/draw_chart/draw_chart_items.py
A	ui/draw_chart/draw_chart_real.py
R080	ui/ui_draw_crosshair.py	ui/draw_chart/draw_crosshair.py
R095	ui/ui_draw_home_chart.py	ui/draw_chart/draw_home_chart.py
R079	ui/ui_draw_label_text.py	ui/draw_chart/draw_label_text.py
A	ui/draw_chart/draw_radar_chart.py
R092	ui/ui_draw_treemap.py	ui/draw_chart/draw_treemap.py
A	ui/etcetera/__init__.py
A	ui/etcetera/etc.py
A	ui/etcetera/import_hook.py
A	ui/etcetera/load_database.py
A	ui/etcetera/monitor_windowQ.py
R069	ui/ui_process_alive.py	ui/etcetera/process_alive.py
A	ui/etcetera/process_starter.py
R091	ui/ui_splash_screen.py	ui/etcetera/splash_screen.py
A	ui/event_activate/__init__.py
R081	ui/ui_activated_back.py	ui/event_activate/activated_back.py
A	ui/event_activate/activated_etc.py
A	ui/event_activate/activated_stg.py
A	ui/event_change/__init__.py
A	ui/event_change/changed_checkbox.py
A	ui/event_change/changed_text.py
A	ui/event_click/__init__.py
A	ui/event_click/button_clicked_backtest_engine.py
R069	ui/ui_button_clicked_dialog_backengine.py	ui/event_click/button_clicked_backtest_start.py
A	ui/event_click/button_clicked_chart.py
R090	ui/ui_chart_count_change.py	ui/event_click/button_clicked_chart_count.py
A	ui/event_click/button_clicked_database.py
R061	ui/ui_button_clicked_etc.py	ui/event_click/button_clicked_etc.py
R089	ui/ui_button_clicked_dialog_formula.py	ui/event_click/button_clicked_formula.py
A	ui/event_click/button_clicked_order.py
A	ui/event_click/button_clicked_passticks.py
A	ui/event_click/button_clicked_settings.py
A	ui/event_click/button_clicked_shortcut.py
A	ui/event_click/button_clicked_show_dialog.py
R080	ui/ui_button_clicked_editer_stock.py	ui/event_click/button_clicked_stg_editer.py
A	ui/event_click/button_clicked_stg_editer_backlog.py
R051	ui/ui_button_clicked_editer_stg_buy_stock.py	ui/event_click/button_clicked_stg_editer_buy.py
R052	ui/ui_button_clicked_editer_ga_stock.py	ui/event_click/button_clicked_stg_editer_ga.py
A	ui/event_click/button_clicked_stg_editer_opti.py
R050	ui/ui_button_clicked_editer_stg_sell_stock.py	ui/event_click/button_clicked_stg_editer_sell.py
R078	ui/ui_button_clicked_strategy.py	ui/event_click/button_clicked_stg_module.py
R063	ui/ui_strategy_version.py	ui/event_click/button_clicked_strategy_version.py
R070	ui/ui_vars_change.py	ui/event_click/button_clicked_varstext_change.py
R051	ui/ui_button_clicked_zoom.py	ui/event_click/button_clicked_zoom.py
A	ui/event_click/table_cell_clicked.py
A	ui/event_keypress/__init__.py
A	ui/event_keypress/extend_window.py
R074	ui/ui_event_filter.py	ui/event_keypress/overwrite_event_filter.py
A	ui/event_keypress/overwrite_keypress_event.py
A	ui/event_keypress/overwrite_return_press.py
D	ui/icon/accdel.png
D	ui/icon/backdel.png
D	ui/icon/coin.png
D	ui/icon/coins.png
D	ui/icon/coins2.png
D	ui/icon/dbdel.png
D	ui/icon/start.png
D	ui/icon/total.png
A	ui/main_window.pyd
D	ui/set_order_tap.py
D	ui/set_setup_tap.py
D	ui/set_stg_coin_tap.py
D	ui/set_stg_unified_tap.py
D	ui/set_table.py
D	ui/set_text_stg_button.py
D	ui/ui_activated_etc.py
D	ui/ui_activated_stg.py
D	ui/ui_backtest_engine.py
D	ui/ui_button_clicked_chart.py
D	ui/ui_button_clicked_dialog_database.py
D	ui/ui_button_clicked_dialog_elapsed_tick_number.py
D	ui/ui_button_clicked_editer_backlog.py
D	ui/ui_button_clicked_editer_coin.py
D	ui/ui_button_clicked_editer_ga_coin.py
D	ui/ui_button_clicked_editer_ga_unified.py
D	ui/ui_button_clicked_editer_opti_coin.py
D	ui/ui_button_clicked_editer_opti_stock.py
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
D	ui/ui_mainwindow.pyd
D	ui/ui_process_starter.py
D	ui/ui_return_press.py
D	ui/ui_show_dialog.py
D	ui/ui_text_changed.py
D	ui/ui_update_textedit.py
A	ui/update_widget/__init__.py
A	ui/update_widget/update_crawling_data.py
R075	ui/ui_update_progressbar.py	ui/update_widget/update_progressbar.py
R060	ui/ui_update_tablewidget.py	ui/update_widget/update_tablewidget.py
A	ui/update_widget/update_telegram_msg.py
A	ui/update_widget/update_textedit.py
R089	update_db_20260211.bat	update_db_20260418.bat
A	"utility/_imagefiles/00_\355\231\210\355\231\224\353\251\264.png"
A	"utility/_imagefiles/01_\352\270\260\353\263\270\354\260\275.png"
A	"utility/_imagefiles/02_\354\247\221\352\263\204\354\260\275.png"
A	"utility/_imagefiles/03_\354\240\204\353\236\265\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/04_\353\260\261\355\214\214\354\235\270\353\215\224.png"
A	"utility/_imagefiles/05_\354\265\234\354\240\201\355\231\224\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/06_\355\205\214\354\212\244\355\212\270\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/07_\354\240\204\354\247\204\353\266\204\354\204\235.png"
A	"utility/_imagefiles/08_\353\263\200\354\210\230\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/09_\353\262\224\354\234\204\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/10_\354\241\260\352\261\264\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/11_GA\355\216\270\354\247\221\352\270\260.png"
A	"utility/_imagefiles/12_\353\260\261\355\205\214\353\241\234\352\267\270.png"
A	"utility/_imagefiles/13_\353\260\261\355\205\214\352\270\260\353\241\235.png"
R100	"utility/imagefiles/14_\353\260\261\355\205\214\352\270\260\353\241\235_\352\267\270\353\236\230\355\224\204\353\271\204\352\265\220.png"	"utility/_imagefiles/14_\353\260\261\355\205\214\352\270\260\353\241\235_\352\267\270\353\236\230\355\224\204\353\271\204\352\265\220.png"
R100	"utility/imagefiles/15_\353\260\261\355\205\214\354\212\244\354\274\200\354\245\264\353\237\254.png"	"utility/_imagefiles/15_\353\260\261\355\205\214\354\212\244\354\274\200\354\245\264\353\237\254.png"
A	"utility/_imagefiles/16_\353\241\234\352\267\270\354\260\275.png"
A	"utility/_imagefiles/17_\354\204\244\354\240\225\354\260\275.png"
A	"utility/_imagefiles/18_\354\243\274\353\254\270\352\264\200\353\246\254.png"
A	"utility/_imagefiles/19_\354\212\244\355\206\260\353\235\274\354\235\264\353\270\214.png"
A	"utility/_imagefiles/20_\353\224\224\353\271\204\352\264\200\353\246\254.png"
R100	"utility/imagefiles/21_\352\271\200\355\224\204\354\260\275.png"	"utility/_imagefiles/21_\352\271\200\355\224\204\354\260\275.png"
R100	"utility/imagefiles/22_\354\260\250\355\212\270\354\260\275.png"	"utility/_imagefiles/22_\354\260\250\355\212\270\354\260\275.png"
R100	"utility/imagefiles/23_\354\210\230\354\213\235\352\264\200\353\246\254\354\236\220.png"	"utility/_imagefiles/23_\354\210\230\354\213\235\352\264\200\353\246\254\354\236\220.png"
R100	"utility/imagefiles/24_\354\240\204\353\236\265\353\252\250\353\223\210.png"	"utility/_imagefiles/24_\354\240\204\353\236\265\353\252\250\353\223\210.png"
R100	"utility/imagefiles/25_\355\230\270\352\260\200\354\260\275.png"	"utility/_imagefiles/25_\355\230\270\352\260\200\354\260\275.png"
R100	"utility/imagefiles/26_\352\270\260\354\227\205\354\240\225\353\263\264.png"	"utility/_imagefiles/26_\352\270\260\354\227\205\354\240\225\353\263\264.png"
R100	"utility/imagefiles/27_\353\260\261\355\205\214\354\227\224\354\247\204\354\260\275.png"	"utility/_imagefiles/27_\353\260\261\355\205\214\354\227\224\354\247\204\354\260\275.png"
A	"utility/_imagefiles/28_\354\240\204\353\236\265\353\262\204\354\240\204\352\264\200\353\246\254.png"
R100	"utility/imagefiles/29_\354\227\205\354\242\205\353\263\204\355\205\214\353\247\210\353\263\204\355\212\270\353\246\254\353\247\265.png"	"utility/_imagefiles/29_\354\227\205\354\242\205\353\263\204\355\205\214\353\247\210\353\263\204\355\212\270\353\246\254\353\247\265.png"
R100	"utility/imagefiles/30_\353\260\261\355\205\214\352\262\260\352\263\274\352\267\270\353\236\230\355\224\204.png"	"utility/_imagefiles/30_\353\260\261\355\205\214\352\262\260\352\263\274\352\267\270\353\236\230\355\224\204.png"
R100	"utility/imagefiles/31_\353\260\261\355\205\214\352\262\260\352\263\274\353\266\200\352\260\200\354\240\225\353\263\264.png"	"utility/_imagefiles/31_\353\260\261\355\205\214\352\262\260\352\263\274\353\266\200\352\260\200\354\240\225\353\263\264.png"
A	"utility/_imagefiles/32_\354\233\271\353\214\200\354\213\234\353\263\264\353\223\234.png"
A	"utility/_imagefiles/33_\353\266\204\354\204\235\354\213\234\354\212\244\355\205\234.png"
R100	utility/imagefiles/parse_dat.png	utility/_imagefiles/parse_dat.png
R100	"utility/imagefiles/\354\260\270\352\263\240 \352\265\220\354\260\250\352\262\200\354\246\235.png"	"utility/_imagefiles/\354\260\270\352\263\240 \352\265\220\354\260\250\352\262\200\354\246\235.png"
R100	"utility/imagefiles/\354\260\270\352\263\240 \354\240\204\354\247\204\353\266\204\354\204\235.jpg"	"utility/_imagefiles/\354\260\270\352\263\240 \354\240\204\354\247\204\353\266\204\354\204\235.jpg"
R096	utility/pycharm/Darcula_copy.icls	utility/_pycharm/Darcula_copy.icls
R080	utility/pycharm/Project_Default.xml	utility/_pycharm/Project_Default.xml
R085	utility/remove_space.py	utility/_remove_space.py
R085	utility/total_code_line.py	utility/_total_code_line.py
D	utility/ai_agent/rules.txt
D	utility/blacklist_stock.txt
D	utility/chart_hoga_query_sound.py
D	utility/database_check.py
A	utility/db_control/__init__.py
R096	utility/_db_distinct.bat	utility/db_control/_db_distinct.bat
A	utility/db_control/database_check.py
R056	utility/database_read_only.py	utility/db_control/database_read_only.py
R057	utility/db_distinct.py	utility/db_control/db_distinct.py
A	utility/db_control/update_db_20260418.py
D	"utility/imagefiles/00_\355\231\210\355\231\224\353\251\264.png"
D	"utility/imagefiles/01_\352\270\260\353\263\270\354\260\275.png"
D	"utility/imagefiles/02_\354\247\221\352\263\204\354\260\275.png"
D	"utility/imagefiles/03_\354\240\204\353\236\265\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/04_\353\260\261\355\214\214\354\235\270\353\215\224.png"
D	"utility/imagefiles/05_\354\265\234\354\240\201\355\231\224\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/06_\355\205\214\354\212\244\355\212\270\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/07_\354\240\204\354\247\204\353\266\204\354\204\235.png"
D	"utility/imagefiles/08_\353\263\200\354\210\230\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/09_\353\262\224\354\234\204\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/10_\354\241\260\352\261\264\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/11_GA\355\216\270\354\247\221\352\270\260.png"
D	"utility/imagefiles/12_\353\260\261\355\205\214\353\241\234\352\267\270.png"
D	"utility/imagefiles/13_\353\260\261\355\205\214\352\270\260\353\241\235.png"
D	"utility/imagefiles/16_\353\241\234\352\267\270\354\260\275.png"
D	"utility/imagefiles/17_\354\204\244\354\240\225\354\260\275.png"
D	"utility/imagefiles/18_\354\243\274\353\254\270\352\264\200\353\246\254.png"
D	"utility/imagefiles/19_\354\212\244\355\206\260\353\235\274\354\235\264\353\270\214.png"
D	"utility/imagefiles/20_\353\224\224\353\271\204\352\264\200\353\246\254.png"
D	"utility/imagefiles/24_\354\247\200\354\210\230\354\260\250\355\212\270.png"
D	"utility/imagefiles/26_\355\230\270\352\260\200\354\260\275.png"
D	"utility/imagefiles/27_\352\270\260\354\227\205\354\240\225\353\263\264.png"
D	"utility/imagefiles/28_\352\270\260\354\227\205\354\240\225\353\263\264.png"
D	"utility/imagefiles/28_\353\260\261\355\205\214\354\227\224\354\247\204\354\260\275.png"
D	"utility/imagefiles/28_\354\227\205\354\242\205\353\263\204\355\205\214\353\247\210\353\263\204\355\212\270\353\246\254\353\247\265.png"
D	"utility/imagefiles/29_\353\260\261\355\205\214\352\262\260\352\263\274\352\267\270\353\236\230\355\224\204.png"
D	"utility/imagefiles/29_\354\233\271\354\227\224\354\247\204\353\267\260\354\226\264.png"
D	"utility/imagefiles/30_\353\260\261\355\205\214\352\262\260\352\263\274\353\266\200\352\260\200\354\240\225\353\263\264.png"
D	"utility/imagefiles/30_\354\227\205\354\242\205\353\263\204\355\205\214\353\247\210\353\263\204\355\212\270\353\246\254\353\247\265.png"
D	"utility/imagefiles/31_\353\260\261\355\205\214\352\262\260\352\263\274\352\267\270\353\236\230\355\224\204.png"
D	"utility/imagefiles/31_\355\205\224\353\240\210\352\267\270\353\236\250 \354\202\254\354\232\251\354\236\220\353\262\204\355\212\274.png"
D	"utility/imagefiles/31_\355\205\224\353\240\210\352\267\270\353\236\250_\354\202\254\354\232\251\354\236\220\353\262\204\355\212\274.png"
D	"utility/imagefiles/32_\353\260\261\355\205\214\352\262\260\352\263\274\353\266\200\352\260\200\354\240\225\353\263\264.png"
D	"utility/imagefiles/32_\355\205\224\353\240\210\352\267\270\353\236\250 \354\202\254\354\232\251\354\236\220\353\262\204\355\212\274.png"
D	"utility/imagefiles/33_\355\205\224\353\240\210\352\267\270\353\236\250 \354\202\254\354\232\251\354\236\220\353\262\204\355\212\274.png"
D	"utility/imagefiles/35_\353\271\204\354\244\221\354\241\260\354\240\210.png"
D	"utility/imagefiles/36_\353\260\261\355\205\214\354\227\224\354\247\204\354\260\275.png"
D	utility/imagefiles/diagram_01.png
D	utility/imagefiles/diagram_02.png
D	utility/imagefiles/stom.drawio
D	utility/numba_rolling.py
D	utility/profile_utils.py
D	utility/realtime_fid_kiwoom.py
A	utility/requirements.txt
D	utility/setting_base.py
D	utility/setting_user.py
A	utility/settings/__init__.py
A	utility/settings/setting_base.py
A	utility/settings/setting_market.py
A	utility/settings/setting_user.py
D	utility/static.py
A	utility/static_method/__init__.py
A	utility/static_method/builtin_print.py
A	utility/static_method/static_datetime.py
A	utility/static_method/static_decorator.py
A	utility/static_method/static_etcetera.py
A	utility/static_method/static_fernet_key.py
A	utility/static_method/static_indicator.py
A	utility/static_method/static_numba.py
R093	utility/syntax.py	utility/static_method/syntax.py
R093	utility/strategy_version_manager.py	utility/static_method/version_manager.py
A	utility/sub_process_and_thread/__init__.py
A	utility/sub_process_and_thread/chart_hoga_query.py
R066	utility/kimp_upbit_binance.py	utility/sub_process_and_thread/kimp_upbit_binance.py
A	utility/sub_process_and_thread/pyttsx_sound.py
R054	utility/telegram_bot.py	utility/sub_process_and_thread/telegram_bot.py
R060	utility/timesync.py	utility/sub_process_and_thread/timesync.py
A	utility/sub_process_and_thread/webcrawling.py
D	utility/ta_lib-0.6.8-cp311-cp311-win32.whl
D	utility/ta_lib-0.6.8-cp311-cp311-win_amd64.whl
A	utility/ta_lib-0.6.8-cp313-cp313-win_amd64.whl
D	utility/update_db_20260211.py
D	utility/upstream_sync_policy.py
D	utility/webcrawling.py
```

## 13. 다음 단계 권고

다음 단계는 Phase 6 source 적용 본작업이다.

권장 실행 방식:

1. `$team`으로 worker lane을 나눈다.
2. Lane A: formal commit body 추출과 version boundary 검증
3. Lane B: official source candidate 적용 스크립트/dry-run 작성
4. Lane C: protected governance/runtime guard 검증
5. Lane D: `STOM V3.0` 첫 commit trial 또는 적용 후 검증

Phase 6 본작업에서 지켜야 할 절대 규칙:

- `git add -A` 금지
- one official version = one commit
- title = `STOM V3.x`
- body = `_update.txt` 해당 section 전문
- official V3 pyd 보존
- `_database`, `_log`, `*.db` stage 금지
- `AGENTS.md`, `docs/V3_*`, `docs/update_log/*`, `.gitignore` 삭제 금지

## 14. 판정

Phase 6 preflight/dry-run은 통과로 판정한다.

하지만 실제 source 적용은 아직 수행하지 않았다. 다음 단계에서 `$team` 또는 보수적 `$ralph`를 사용해 Phase 6 source intake를 진행한다.