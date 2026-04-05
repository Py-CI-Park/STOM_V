# 2026-04-05 2U_C 단일 기준선 통합 실행 로그

## Baseline
- source branch: `STOM_Version_2U_C`
- absorbed branch: `STOM_Version_2U_C_CLI_v267`
- integration branch: `integration/adopt-cli-v267-into-2uc`

## Pre-merge failures
- `tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module`
- `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`

## Conflict inventory
- 초기 생성 시 비워 두고, Task 3에서 실제 충돌 파일 목록으로 덮어쓴다.

## Reapplied 2U_C-only fixes
- 초기 생성 시 비워 두고, Task 4에서 실제 재적용 커밋 목록으로 덮어쓴다.

## Final verification
- 초기 생성 시 비워 두고, Task 7에서 실제 검증 결과로 덮어쓴다.
