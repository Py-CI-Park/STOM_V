# 2026-04-12 BackSubTotal 중간집계 프로세스 계약 복구

## 배경

- 증상: 백테스트 엔진 실행 후 백테스트 버튼을 클릭하면 `백테스트 START` 이후 진행이 멈춤.
- 로그의 직접 오류:
  - `TypeError: BackSubTotal.__init__() takes 5 positional arguments but 6 were given`
- 중간집계용 `BackSubTotal` 프로세스 20개가 생성 직후 모두 종료되어, 이후 집계 단계가 응답을 받지 못했다.

## 원인

- 공식 `STOM_Version_2` UI 호출부는 `BackSubTotal` 생성 시 `windowQ`를 포함해 전달한다.
- `STOM_Version_2U_C` 기준선에는 CLI 통합 과정에서 `BackSubTotal.__init__`이 `windowQ` 없이 축약된 계약으로 남아 있었다.
- 결과적으로 공식 UI 호출 계약과 CLI 계열 생성자 계약이 섞여 인자 수 불일치가 발생했다.

## 변경 사항

- `backtest/back_subtotal.py`
  - `BackSubTotal.__init__(vkey, wq, tq, bstqs, buystd)` 계약으로 복구.
  - `self.wq` 보관을 복구.
- `cli/runner.py`
  - CLI 경로도 `BackSubTotal` 생성 시 `windowQ`를 전달하도록 정렬.
- `tests/unit/test_backtest_button_contract.py`
  - `BackSubTotal` 생성자 계약 회귀 테스트 추가.
- `tests/unit/test_backtest_spawn_contract_audit.py`
  - CLI `BackSubTotal` 생성 경로가 `windowQ`를 전달하는지 감사 테스트 추가.

## 브랜치 반영 매트릭스

| 브랜치 | 상태 | 근거 | 반영 |
| --- | --- | --- | --- |
| `STOM_Version_2` | 수정 불필요 | 생성자와 UI 호출부 모두 `windowQ` 포함 계약 | 미반영 |
| `STOM_Version_2U` | 수정 불필요 | 생성자와 UI 호출부 모두 `windowQ` 포함 계약 | 미반영 |
| `STOM_Version_2U_C` | 동일 문제 존재 | UI는 `windowQ` 포함, 생성자는 `windowQ` 미포함 | `7448e82` |
| `research/init` | 동일 문제 존재 | UI는 `windowQ` 포함, 생성자는 `windowQ` 미포함 | `e50bf19` |
| `integration/adopt-cli-v267-into-2uc` | 비활성 보관 브랜치 | 활성 전파 라인이 아니라서 변경 취소 | 미반영 |

## 검증 결과

- `STOM_Version_2U_C`
  - `python -m pytest tests/unit/test_backtest_button_contract.py -q` 통과.
  - `python -m pytest tests/unit/test_backtest_spawn_contract_audit.py -q` 통과.
  - `python -m pytest tests/unit/test_backtest_result_expansion.py -q` 통과.
  - `python -m pytest tests/unit/ -q` 통과: `823 passed, 1 skipped`.
  - `python scripts/verify_nonrelease_sync.py` 통과.
- `research/init`
  - `python -m pytest tests/unit/test_backtest_button_contract.py tests/unit/test_backtest_spawn_contract_audit.py -q` 통과: `5 passed`.
  - `python scripts/verify_nonrelease_sync.py` 통과.
  - 전체 unit suite는 기존 연구 브랜치 실패 2건이 남아 별도 추적 대상:
    - `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`
    - `tests/unit/test_exit_codes.py::TestExitCodes::test_execution_error_returns_two`

## 주의 사항

- 이번 문제는 공식 `STOM_Version_2` 업데이트 자체의 오류가 아니라, 공식 UI 계약과 CLI 계열 축약 생성자 계약이 `2U_C` 계열에서 혼재되며 발생한 통합 불일치다.
- `integration/adopt-cli-v267-into-2uc`는 보관 브랜치이므로 별도 수정 커밋을 제거했다.
