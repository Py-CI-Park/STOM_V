# STOM Change Log

## 버전 기록

### V2.36.U1.5 (2026-02-01) - 시리얼키 기능 제거

#### 변경 사항

**1. 시리얼키 GUI 요소 제거**
- 파일: `ui/set_setup_tap.py`
- 제거된 위젯:
  - `sj_etc_labelll_02` (시리얼키 라벨)
  - `sj_etc_liEditt_01` (시리얼키 입력필드)
  - `sj_etc_daEditt_01` (만료날짜 DateEdit)

**2. 시리얼키 로드/저장 코드 제거**
- 파일: `ui/ui_button_clicked_settings.py`
  - `setting_load_08()`: 시리얼키 로드 코드 제거
  - `setting_save_08()`: 시리얼키 저장 및 암호화 코드 제거
  - `setting_acc_view()`: 시리얼키 필드 EchoMode 토글 제거
- 파일: `ui/ui_return_press.py`
  - `return_press_setting_pass()`: 시리얼키 필드 EchoMode 설정 제거

**3. 시리얼키 dict_set 항목 제거**
- 파일: `utility/setting.py`
- 제거: `'시리얼키': de_text(EN_KEY, df_e['시리얼키'][0])` 항목

**4. 시리얼키 DB 스키마 변경**
- 파일: `utility/database_check.py`
- 변경: `etc` 테이블에서 `시리얼키` 컬럼 정의 제거
- 참고: 기존 DB의 시리얼키 컬럼은 유지되며 무시됨 (하위 호환성)

#### 변경 이유
- .pyd → .py 마이그레이션 완료로 시리얼키 보호 불필요
- 오픈소스 운영 방침에 따른 인증 기능 제거

#### 유지되는 기능
- 암호화 인프라 (`en_text()`, `de_text()`, `read_key()`, `write_key()`)
- 계정, API 키, 텔레그램 토큰 등 민감 정보 암호화
- STOM Live 체크박스 및 관련 코드 (비활성화 상태 유지)

#### 수정된 파일
| 파일 | 수정 내용 |
|------|----------|
| `ui/set_setup_tap.py` | 시리얼키 라벨, 입력필드, 만료날짜 위젯 제거 |
| `ui/ui_button_clicked_settings.py` | 시리얼키 로드/저장/암호화 코드 제거 |
| `ui/ui_return_press.py` | 시리얼키 필드 EchoMode 설정 제거 |
| `utility/setting.py` | dict_set에서 시리얼키 항목 제거 |
| `utility/database_check.py` | DB 스키마에서 시리얼키 컬럼 제거 |

---

### V2.36.U1.4 (2026-02-01) - codename 테이블 에러 핸들링 개선

#### 수정된 버그

**1. DatabaseError: no such table: codename**
- 위치: `ui/ui_mainwindow.py:317-319`
- 원인: 주식 로그인 전 `codename` 테이블이 존재하지 않음
- 해결:
  - 중첩 try/except로 양쪽 DB 모두 실패 시 처리
  - 빈 DataFrame으로 초기화하여 프로그램 계속 실행 가능
  - 사용자에게 경고 메시지 출력

---

### V2.36.U1.3 (2026-02-01) - ElapsedTickNumber 메서드 추가

#### 수정된 버그

**1. AttributeError: 'MainWindow' object has no attribute 'SettingStockElapsedTickNumberSample'**
- 위치: `ui/set_dialog_etc.py:373`
- 원인: 메서드명 불일치 (setButtonClicked_01 vs SettingStockElapsedTickNumberSample)
- 해결: `ui/ui_mainwindow.py`에 명시적 메서드 추가
  - `SettingStockElapsedTickNumberSample()`
  - `SettingStockElapsedTickNumberLoad()`
  - `SettingStockElapsedTickNumberSave()`
  - `SettingCoinElapsedTickNumberSample()`
  - `SettingCoinElapsedTickNumberLoad()`
  - `SettingCoinElapsedTickNumberSave()`
- Legacy alias 유지 (setButtonClicked_*, cetButtonClicked_*)

#### 문서 추가
- CLAUDE.md: 프로젝트 가이드라인 및 버전 네이밍 규칙 추가

---

### V2.36.U1.2 (2026-02-01) - 런타임 에러 수정

#### 수정된 버그

**1. NameError: 'int_hms' is not defined**
- 위치: `ui/ui_mainwindow.py:298`
- 원인: `int_hms()` 함수가 utility/static.py에 정의되지 않음
- 해결: `utility/static.py`에 `int_hms()` 함수 추가
  ```python
  def int_hms(std_time=None):
      if std_time is not None:
          return int(strf_time('%H%M%S', std_time))
      else:
          return int(strf_time('%H%M%S'))
  ```

**2. AttributeError: 'NoneType' object has no attribute 'read_sql'**
- 위치: `ui/ui_activated_*.py` 모듈들
- 원인: `self.dbreader`가 `None`으로 초기화되어 있음
- 해결:
  - `DatabaseReadOnly` import 추가
  - `self.dbreader = DatabaseReadOnly()`로 초기화

**3. AttributeError: 'MainWindow' object has no attribute 'ManualSaveAndExit'**
- 위치: `ui/set_main_menu.py:71`
- 원인: `ManualSaveAndExit()` 메서드가 정의되지 않음
- 해결: `ui/ui_mainwindow.py`에 메서드 추가
  ```python
  def ManualSaveAndExit(self):
      self.SettingAllSave()
      self.close()
  ```

#### 검증 결과
- 구문 검사: 통과
- int_hms() 함수 테스트: 정상 동작 (예: 181039 반환)

#### 문서 업데이트
- docs/update_log/2026-01-31_analysis_v1_vs_v2.md: 종합 마이그레이션 분석 보고서 업데이트

---

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
