# 2026-07-03 Plan A 이월 코드 실행 로그

## 범위

- 실행 계획: `.omo/plans/ai-loop-full-next-execution-20260703.md`
- 원문 계획: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md`
- 실행 범위: T0~T3 only
- 제외 범위: Plan C, Plan B, Plan D 미실행
- A3 상태: `blocked_pending_user_approval`

## T0 Preflight

- Read-first source package는 EOF까지 전체 문서로 확인했다.
- 영수증: `.omo/evidence/ai-loop-full-next-execution-20260703/source_read_receipt.md`
- Preflight 증거: `.omo/evidence/ai-loop-full-next-execution-20260703/t0-preflight.md`
- Positive control 기준: `.omo/evidence/ai-loop-full-next-execution-20260703/baseline_positive_control_source.json`
- Positive control 결과: `.omo/evidence/ai-loop-full-next-execution-20260703/positive_control_receipt_reference.json`

## T1 A1 FailoverProvider

- 상태: 완료
- 커밋: `a4681b15`
- 변경 파일:
  - `ai_strategy_loop/provider/failover.py`
  - `ai_strategy_loop/provider/__init__.py`
  - `ai_strategy_loop/controller/loop.py`
  - `tests/unit/test_provider_failover.py`
- 핵심 결과:
  - `ProviderError(retryable=False, status in {401, 403})`는 즉시 fallback provider로 전환한다.
  - retryable 오류는 연속 3회 후 전환한다.
  - fallback이 없거나 비 `ProviderError` 예외인 경우 원래 예외를 삼키지 않는다.
  - `_make_provider_with_proxy`는 `OPENROUTER_API_KEY`가 있고 현재 provider가 `openrouter`가 아닐 때만 fallback wrapper를 구성한다.

검증:

- `python -m pytest tests/unit/test_provider_failover.py -q` -> `7 passed`
- `python -m pytest tests/unit/test_provider.py tests/unit/test_provider_failover.py -q` -> `15 passed`
- `python -m pytest tests/unit/ -q` -> `8 failed, 3989 passed, 40 warnings`; T0 baseline 대비 신규 실패 없음
- `python scripts/verify_nonrelease_sync.py` -> 통과
- 실패 비교: `.omo/evidence/ai-loop-full-next-execution-20260703/t1-failure-set-comparison.json`

## T2 A2 Provider Upper Entrypoints

- 상태: 완료
- 커밋: `1586e751`
- 변경 파일:
  - `cli/research_provider.py`
  - `cli/ai_controller.py`
  - `cli/research_optimizer.py`
  - `tests/unit/test_research_provider_entrypoints.py`
- 핵심 결과:
  - `llm_pack_provider` 예약 키를 `ResearchLoopConfig` 구성 전에 분리한다.
  - `research_strategy_once(... run_candidates=True ...)`에서만 provider resolver를 호출한다.
  - provider가 실제로 해석된 경우에만 `run_research_iteration(..., provider=provider)`로 전달한다.
  - `run_wide_v2_optimizer(..., provider=...)`는 기본 `run_research_iteration` runner에만 provider를 주입하고, 사용자 지정 runner 시그니처는 변경하지 않는다.
  - `gpt_auth` proxy 시작 실패는 예외로 iteration을 죽이지 않고 deterministic fallback 경로로 내려간다.

검증:

- `python -m pytest tests/unit/test_ai_controller.py::test_research_strategy_once_routes_iteration tests/unit/test_research_provider_entrypoints.py -q` -> `9 passed`
- `python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q` -> `137 passed`
- `python -m pytest tests/unit/ -q` -> `8 failed, 3997 passed, 40 warnings`; T0 baseline 대비 신규 실패 없음
- `python scripts/verify_nonrelease_sync.py` -> 통과
- `git diff --cached --check` -> 통과
- 실패 비교: `.omo/evidence/ai-loop-full-next-execution-20260703/t2-failure-set-comparison-postfix.json`

남아 있는 baseline 실패:

- `tests/unit/test_backtest_button_contract.py::test_backtest_constructor_contract_is_small_and_queue_driven`
- `tests/unit/test_backtest_process_protocol_diagnostics.py::test_backtest_start_emits_key_protocol_checkpoints`
- `tests/unit/test_backtest_process_protocol_diagnostics.py::test_total_emits_key_protocol_checkpoints`
- `tests/unit/test_backtest_spawn_contract_audit.py::test_stock_backtest_spawn_does_not_pass_legacy_long_signature`
- `tests/unit/test_backtest_spawn_contract_audit.py::test_coin_backtest_spawn_does_not_pass_legacy_long_signature`
- `tests/unit/test_runner_helpers.py::TestCliDictSetProcessArgs::test_backtest_process_passes_dict_set_to_constructor`
- `tests/unit/test_tick_seed_timeout_probe.py::test_run_cold_command_uses_warm_window_and_forbidden_tokens_are_absent`
- `tests/unit/test_ui_jisu_cleanup.py::test_v270_removed_jisu_chart_references_are_fully_cleaned`

## T3 A3 Approval Gate

- 상태: `blocked_pending_user_approval`
- 이유: 사용자 승인 전 A3 승격 검토 관련 코드 수정 금지 조건이 있다.
- 실행 내용: 문서 기록만 수행했다.
- 코드 변경 금지 확인:
  - `promotion_preconditions` 미수정
  - `condition_discovery` 미수정
  - 내보내기/라이브/최종 승격 경로 미수정
  - 승격 또는 내보내기 활성화 경로 추가 없음

다음 세션에서 A3를 진행하려면 사용자가 별도 승인 문구로 promotion-review 리포트 배선을 허용해야 한다. 승인 전에는 A3 코드를 계속 보류한다.
