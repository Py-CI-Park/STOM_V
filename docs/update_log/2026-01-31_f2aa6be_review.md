# f2aa6be UI MainWindow 마이그레이션 커밋 검토 보고서

- **대상 커밋**: `f2aa6bef1f991c231fa59184e066f5ba3507ad54` (STOM V2.36.U1)
- **기준 커밋**: `ddfd9fbdc68bdb78da495f3eccec7273130ac4cc` (STOM V2.36)
- **브랜치**: `STOM_Version_2U`
- **검토일**: 2026-01-31

---

## 결론 (요약)

`ui/ui_mainwindow.pyd`를 제거하고 `ui/ui_mainwindow.py`를 추가한 방향(목적)은 적절하나, **V2.36 UI 모듈들이 요구하는 MainWindow API(메서드) 일부가 누락**되어 있어 **현 상태로는 기능 회귀/런타임 오류 가능성이 높습니다.**

또한, 마이그레이션 문서(`docs/update_log/2026-01-31_ui_mainwindow_migration.md`)에 **사실과 다른 내용**이 일부 포함되어 신뢰도가 떨어집니다.

---

## 요구사항 대비 충족 여부

- **STOM_Version_2U 브랜치 생성**: 충족 (현재 브랜치가 `STOM_Version_2U`)
- **pyd 미사용 방향 검토/전략/계획 문서 작성**: 부분 충족
  - 마이그레이션 “완료 보고서”는 존재하나, 실제 코드 상태와 불일치하는 내용이 있어 보완 필요.
- **ui_mainwindow.pyd → ui_mainwindow.py 대체(최종 목적 방향)**: 부분 충족
  - 파일 교체는 되었으나, MainWindow의 필수 메서드 누락으로 기능상 완전 대체로 보기 어려움.

---

## 주요 발견사항 (심각도 순)

### [Critical] V2 UI가 참조하는 MainWindow 메서드 다수 누락 → 클릭/동작 시 AttributeError 예상

아래 메서드들은 여러 UI 구성 모듈에서 `self.ui.<method>` 형태로 **핸들러로 연결**되거나, `ui.<method>(...)` 형태로 **직접 호출**됩니다.  
그러나 `ui/ui_mainwindow.py`에 해당 메서드가 정의되어 있지 않아, 해당 UI 동작 시 **즉시 예외(대부분 AttributeError)** 가능성이 큽니다.

- **보조지표 설정(차트 다이얼로그) 핸들러 누락**
  - 참조: `ui/set_dialog_chart.py:236`, `ui/set_dialog_chart.py:237`, `ui/set_dialog_chart.py:238`
  - 누락: `IndicatorSettingBasic`, `IndicatorSettingLoad`, `IndicatorSettingSave`

- **설정(Setup) 탭의 설정파일 로딩/적용/삭제/저장 및 계정 보기 핸들러 누락**
  - 참조: `ui/set_setup_tap.py:19`, `ui/set_setup_tap.py:20`, `ui/set_setup_tap.py:21`, `ui/set_setup_tap.py:23`, `ui/set_setup_tap.py:181`
  - 누락: `SettingAllLoad`, `SettingAllApp`, `SettingAllDel`, `SettingAllSave`, `SettingAccView`

- **경과틱수 설정(주식/코인) 다이얼로그 및 버튼 핸들러 누락**
  - 참조: `ui/set_dialog_etc.py:373`, `ui/set_dialog_etc.py:374`, `ui/set_dialog_etc.py:375`, `ui/set_dialog_etc.py:418`, `ui/set_dialog_etc.py:419`, `ui/set_dialog_etc.py:420`
  - 참조: `ui/set_setup_tap.py:182`, `ui/set_setup_tap.py:183`
  - 누락: `SettingStockElapsedTickNumber`, `SettingStockElapsedTickNumberSample`, `SettingStockElapsedTickNumberLoad`, `SettingStockElapsedTickNumberSave`
  - 누락: `SettingCoinElapsedTickNumber`, `SettingCoinElapsedTickNumberSample`, `SettingCoinElapsedTickNumberLoad`, `SettingCoinElapsedTickNumberSave`

- **비중조절(주식/코인) UI 핸들러 누락**
  - 참조: `ui/set_order_tap.py:271`, `ui/set_order_tap.py:272`
  - 참조: `ui/set_dialog_etc.py:252`, `ui/set_dialog_etc.py:253`, `ui/set_dialog_etc.py:256`
  - 참조: `ui/set_dialog_etc.py:285`, `ui/set_dialog_etc.py:286`, `ui/set_dialog_etc.py:289`
  - 누락: `SettingStockWeightControl`, `SettingCoinWeightControl`
  - 누락: `SettingStockWeightCotrolLoad`, `SettingStockWeightCotrolSave`, `SettingStockWeightCotrolChanged`
  - 누락: `SettingCoinWeightCotrolLoad`, `SettingCoinWeightCotrolSave`, `SettingCoinWeightCotrolChanged`

- **설정파일 교체 적용 시 호출되는 로드/세이브 루틴 누락**
  - 참조: `ui/ui_button_clicked_settings.py:1254` ~ `ui/ui_button_clicked_settings.py:1277`
  - 누락: `SettingLoad_01`~`SettingLoad_08`, `SettingSave_01`~`SettingSave_08`
  - 누락: `SettingOrderLoad_01`~`SettingOrderLoad_04`, `SettingOrderSave_01`~`SettingOrderSave_04`

- **백테 스케쥴러 중단 메서드 누락**
  - 참조: `ui/ui_button_clicked_dialog_backengine.py:153`
  - 누락: `StopScheduler`

- **차트/클릭 흐름에서 사용되는 보조지표 상세 조회 메서드 누락**
  - 참조: `ui/ui_show_dialog.py:137`, `ui/ui_return_press.py:43`, `ui/ui_cell_clicked.py:181`
  - 누락: `GetIndicatorDetail`

검토 중 간단한 정적 분석(호출/핸들러 연결 패턴 기반)으로 확인된 **누락 메서드 수: 49개**.

---

### [High] 로컬 모듈 import 불일치: `utility.telegram_msg` 미존재

- `ui/ui_mainwindow.py:74` 에서 `from utility.telegram_msg import *`를 import 하지만,
  현 브랜치 기준 `utility/telegram_msg.py` 파일이 존재하지 않습니다.
  - 관련: `ui/ui_mainwindow.py:274` 에서 `Process(target=TelegramMsg, ...)` 사용
  - 영향: 레지스트리 권한 문제 등을 해결하고 실제 실행 단계로 넘어가더라도, 텔레그램 프로세스 로직에서 **ModuleNotFoundError / NameError** 가능성이 큼.

---

### [Medium] 마이그레이션 문서의 사실 불일치/과장 표현

- `.gitignore`에 `*.pyd`가 추가되었다고 문서/커밋 메시지에 기재되어 있으나 실제 변경은 `*.pyd.backup`만 추가됨
  - 실제: `.gitignore:17`
  - 문서: `docs/update_log/2026-01-31_ui_mainwindow_migration.md` (3.8, 5.2 등)

- Zmq 스레드 클래스 상속 관계 설명 오류
  - 실제: `ui/ui_mainwindow.py:193`, `ui/ui_mainwindow.py:213` 는 `QThread` 상속
  - 문서: `docs/update_log/2026-01-31_ui_mainwindow_migration.md` 에서는 `threading.Thread`로 기술

- “모든 참조 메서드 존재 확인”, “최종 완성도 100%” 등의 결론이 현재 코드 상태와 부합하지 않음

---

### [Low] 검증(테스트) 범위가 py_compile 중심으로 제한됨

- 문서상 검증은 `python -m py_compile` 수준으로 보이며(문서 4.1), 이는 **런타임 동작/핸들러 연결/누락 메서드**를 검출하지 못합니다.
- 최소 수준의 “UI 구성 단계에서 핸들러 존재 여부 확인” 같은 체크(예: Set* 모듈이 요구하는 메서드 목록 검증)가 필요합니다.

---

## 확인한 변경사항 (사실 기반)

- `ui/ui_mainwindow.pyd` 삭제 (Git 상 삭제, 로컬에는 `ui/ui_mainwindow.pyd.backup` 존재)
- `ui/ui_mainwindow.py` 신규 생성 (V1.10 기반으로 다수 모듈 import 및 메서드 정의 포함)
- 문서 추가: `docs/README.md`, `docs/update_log/2026-01-31_ui_mainwindow_migration.md`
- `.gitignore` 변경: `*.pyd.backup` 추가 (`.gitignore:17`)

---

## 질의/가정 (추가 확인 필요)

- `utility.telegram_msg`를 제거한 의도(텔레그램 기능 제거/대체/파일명 변경)와, 현재 정상 동작 기대 스펙은 무엇인가?
  - (예: `utility/telegram_bot.py` 기반으로 교체가 맞는지 여부)
- STOM Live(라이선스) 비활성화는 “개발 전용”인지, 아니면 본 브랜치의 목표 스펙인지?
- 누락된 49개 메서드는 기존 pyd에 존재하던 기능을 모두 포팅해야 하는지, 혹은 일부 기능을 제거해도 되는지(기능 스코프 확정 필요)

---

## 권장 수정 방향 (우선순위)

1. **MainWindow에 누락된 핸들러 메서드(49개) 추가/매핑**
   - 대부분은 `ui_button_clicked_settings.py`, `ui_button_clicked_chart.py`, `ui_button_clicked_dialog_backengine.py` 내 함수에 대한 thin-wrapper 형태가 예상됨.
2. **`utility.telegram_msg` 의존성 정리**
   - (a) 실제로 텔레그램 기능 사용 시: 현 구조에 맞게 모듈/엔트리포인트 정합성 맞추기
   - (b) 미사용 시: 관련 import/프로세스 기동 코드 제거 및 문서에 명시
3. **문서 정정**
   - `.gitignore` 실제 변경 내용 반영, Zmq 상속 관계 수정, “100% 완료” 표현은 근거(검증 항목) 추가 후 조정
4. **최소 검증 자동화**
   - “UI 구성 모듈이 참조하는 `self.ui.<method>`가 MainWindow에 존재하는지”를 검사하는 스크립트(정적) 추가 후 CI/로컬에서 실행 권장

