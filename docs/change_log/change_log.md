# STOM Change Log

## 버전 기록

### V2.36.U1 (2026-01-31) - ui_mainwindow.pyd → ui_mainwindow.py 마이그레이션

#### 변경 사항

**1. ui/ui_mainwindow.py 생성**
- V1.10 원본 소스(commit 80ab4ec)를 기반으로 V2.36 모듈 구조에 맞게 업데이트
- 13개 모듈명 변경 반영
- 13개 신규 editer 모듈 import 추가
- STOM Live 인증 시스템 비활성화

**2. 누락된 메서드 54개 추가**
- Settings Load/Save: SettingLoad_01~08, SettingSave_01~08 (16개)
- Settings Management: SettingAllLoad, SettingAllApp, SettingAllDel, SettingAllSave, SettingAccView (5개)
- Order Settings: SettingOrderLoad_01~04, SettingOrderSave_01~04 (8개)
- Weight Control: SettingStockWeightControl, SettingCoinWeightControl 및 Load/Save/Changed (8개)
- Elapsed Tick Number: SettingStockElapsedTickNumber, SettingCoinElapsedTickNumber (2개)
- Indicator Settings: IndicatorSettingBasic, IndicatorSettingLoad, IndicatorSettingSave, GetIndicatorDetail (4개)
- Scheduler: StopScheduler (1개)
- Activated: dActivated_02 (1개)

**3. utility/telegram_msg.py 생성**
- TelegramMsg 함수 정의 (TelegramBot 래퍼)
- Process target으로 사용 가능한 구조

**4. .gitignore 업데이트**
- *.pyd.backup 추가

**5. 문서 추가**
- docs/README.md
- docs/update_log/2026-01-31_ui_mainwindow_migration.md
- docs/update_log/2026-01-31_f2aa6be_review.md

#### 삭제된 파일
- ui/ui_mainwindow.pyd (백업: ui_mainwindow.pyd.backup)

#### 영향받는 모듈
- ui/set_setup_tap.py - SettingLoad_*, SettingSave_* 메서드 사용
- ui/set_dialog_chart.py - IndicatorSetting* 메서드 사용
- ui/set_dialog_etc.py - WeightControl, ElapsedTickNumber 메서드 사용
- ui/set_order_tap.py - SettingOrderLoad_*, SettingOrderSave_* 메서드 사용
- ui/ui_button_clicked_dialog_backengine.py - StopScheduler 메서드 사용

#### 검증 결과
- 구문 검사 (py_compile): 통과
- Import 구조: V2.36 모듈 구조 반영 완료
- 메서드 정의: 모든 참조 메서드 존재 확인

---

### V2.36 (이전)
- ui_mainwindow.pyd 컴파일 버전 사용
