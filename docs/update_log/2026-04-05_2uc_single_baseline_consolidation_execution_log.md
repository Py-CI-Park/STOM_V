# 2026-04-05 2U_C 단일 기준선 통합 실행 로그

## Baseline
- source branch: `STOM_Version_2U_C`
- absorbed branch: `STOM_Version_2U_C_CLI_v267`
- integration branch: `integration/adopt-cli-v267-into-2uc`

## Pre-merge failures
- `tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module`
- `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`

## Pre-merge fixes
- `ui/ui_mainwindow.py`에서 삭제된 `ui_activated_coin_stg`/`ui_activated_stock_stg` import를 제거
- 삭제된 알림 활성화 모듈 import 의존성만 제거하고 추가 import 없이 `ui/ui_mainwindow.py` import 통과를 복구

## Conflict inventory
- AGENTS.md
- CLAUDE.md
- backtest/back_static.py
- backtest/back_subtotal.py
- backtest/backengine_base.py
- backtest/backengine_base_oms.py
- backtest/backtest.py
- research/auxiliary_indicator/smart_vwap_bands.py
- stom.bat
- stom_coin.bat
- stom_future.bat
- stom_stock.bat
- ui/ui_button_clicked_dialog_backengine.py
- ui/ui_button_clicked_editer_coin.py
- ui/ui_button_clicked_editer_stock.py
- ui/ui_mainwindow.py
- utility/static.py
- utility/telegram_bot.py
- utility/webcrawling.py

## Reapplied 2U_C-only fixes
- 8c0d1558: 텔레그램 런타임 계약 복구
- b18cb168: 텔레그램 저장/종료 경로 정리
- 249a8514: 비정식 워크트리 시리얼키 구조 제거
- 10edf571: non-release sync verifier 확장
- 96265af4: telegram/webcrawling runtime contract
- 1d116161: webcrawling runtime contract test lock
- 23cdce8e: webcrawling timeout contract
- 5a0c5859: webcrawling legacy compatibility

## Final verification
- 초기 생성 때 비워 두고, Task 7에서 실제 검증 결과로 덮어쓴다.
