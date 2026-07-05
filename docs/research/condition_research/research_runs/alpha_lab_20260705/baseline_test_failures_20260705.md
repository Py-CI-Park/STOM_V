# 기준선 테스트 실패 10건 증빙 (2026-07-05)

> **결론**: `tests/unit` 전체 스위트의 실패 10건은 알파 랩 작업과 무관한 **기준선/환경 실패**다. 알파 신규 테스트 247건(246 + app.py 배선 1)은 전원 통과. 커밋 게이트는 핸드오프 §6("신규 테스트 + 관련 회귀 통과")를 충족한다.

## 1. 실패 10건 목록 (분류)

| # | 테스트 | 분류 |
|---|---|---|
| 1 | `test_backtest_button_contract.py::test_backtest_constructor_contract_is_small_and_queue_driven` | 백테 계약 감사 |
| 2 | `test_backtest_process_protocol_diagnostics.py::test_backtest_start_emits_key_protocol_checkpoints` | 백테 계약 감사 |
| 3 | `test_backtest_process_protocol_diagnostics.py::test_total_emits_key_protocol_checkpoints` | 백테 계약 감사 |
| 4 | `test_backtest_spawn_contract_audit.py::test_stock_backtest_spawn_does_not_pass_legacy_long_signature` | 백테 계약 감사 |
| 5 | `test_backtest_spawn_contract_audit.py::test_coin_backtest_spawn_does_not_pass_legacy_long_signature` | 백테 계약 감사 |
| 6 | `test_runner_helpers.py::TestCliDictSetProcessArgs::test_backtest_process_passes_dict_set_to_constructor` | 백테 계약 감사 |
| 7 | `test_tick_seed_timeout_probe.py::test_run_cold_command_uses_warm_window_and_forbidden_tokens_are_absent` | 백테 계약 감사 |
| 8 | `test_filter_gate.py::test_real_seed_buy_has_many_categories` | 런타임 시드 상태 의존 |
| 9 | `test_time_window.py::test_noop_real_seed_buy_is_NOT_noop` | 런타임 시드 상태 의존 |
| 10 | `test_ui_jisu_cleanup.py::test_v270_removed_jisu_chart_references_are_fully_cleaned` | UI 정리 감사 |

## 2. 증거 3종 (교차 검증)

1. **순수 기준선 재현 (결정적)** — 유일한 tracked 변경(app.py alpha 라우터 +2줄)을 stash로 제거한 상태(= HEAD 추적 트리 + 미추적 알파 파일)에서 전체 스위트 실행: **동일 10건 실패** + `test_alpha_api::test_app_py_wires_alpha_router` 1건(스태시로 배선이 없으니 당연한 실패 — 언스태시 후 14/14 통과 확인). `11 failed, 4235 passed, 20 skipped in 340.88s`. 로그: 세션 스크래치패드 `baseline_proof_pytest.log`.
2. **단독 실행 격리 (wf1 수복 에이전트 실측)** — 10건은 알파 테스트를 하나도 수집하지 않은 파일 단독 실행에서도 재현. 실패 집합이 검증 라운드와 바이트 단위 동일(신규/소멸 실패 0) → 교차 오염 배제.
3. **알파 스코프 전수 green** — `tests/unit/test_alpha_*.py` 11파일 = 246 passed (+배선 1 = 247).

## 3. 처리 결정

- **시딩 금지**: wf1 fix r2가 #8·#9를 통과시키려 `ai_strategy_loop/state/loop_strategies.db`(gitignore 경로)를 시딩했던 것을 **삭제·원복**했다. 가짜 런타임 상태로 테스트를 녹색화하는 것은 부정직하며, 두 테스트는 wt-dev의 라이브 루프가 만드는 런타임 산출물(시드 전략 DB)을 전제하는 환경 의존 테스트다. 신선한 워크트리에는 그 산출물이 없어 실패하는 것이 정직한 상태다.
- **기존 파일 불수정**: 기준선 테스트·소스는 수정하지 않는다(알파 랩 규율). 본 10건의 수리는 알파 랩 소관이 아니며, 필요 시 wt-dev 레인에서 별도 처리할 사안.
- **wt-dev 현행 상태 미검증**: min 스윕 실행 중 간섭 금지 원칙에 따라 wt-dev에서의 재현 여부는 확인하지 않았다.

## 4. 부수 소음 (비실패)

`.omo/evidence/tmap-walkforward/_discovery_feedback.txt`(9바이트 '회피: a')가 주기적으로 재생성됨 — 작성자는 라이브 min 스윕의 기준선 스크립트 `ai_strategy_loop/scripts/tmap_multiband_discovery.py:141`(PID 120556 계열). '회피: a' 단일토큰 퇴화는 2026-06-15부터 문서화된 기지 이슈. 알파 커밋에서 제외하며 삭제해도 재생성될 수 있다.

## 5. 게이트 해석

핸드오프 §6 커밋 게이트 = "신규 테스트 + 관련 회귀 통과". 본 문서 기준: 알파 신규 247 green + `verify_nonrelease_sync.py` exit 0 + 관련 회귀(대시보드 route parity 5 passed) green. 기준선 10건은 위 증거로 알파 무관 확정 — 커밋 진행.
