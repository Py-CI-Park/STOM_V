# Git V1.10 vs V2.36 UI 모듈 비교 분석 보고서

## 요약

V1.10의 `ui_mainwindow.py`에서 V2.36.U1로 마이그레이션 시, V2.36의 새로운 UI 모듈들이 요구하는 메서드들의 존재 여부를 분석한 결과입니다.

### 주요 발견사항

- **V1.10**: 383개 메서드 (구식 모듈 구조)
- **V2.36.U1**: 527개 메서드 (신규 모듈 구조)
- **증가**: +144개 메서드

V2.36.U1은 **V1.10에서 직접 가져온 것이 아니라**, V2.00~V2.36에서 사용되던 `ui_mainwindow.pyd` (컴파일된 바이너리)를 `.py`로 디컴파일한 것으로 보입니다.

---

## 1. 모듈 구조 변경 히스토리

### V1 (커밋 80ab4ec)
```
ui/
├── ui_mainwindow.py (383개 메서드)
├── ui_button_clicked_db.py         # DB 관리
├── ui_button_clicked_ob.py         # 주문
├── ui_button_clicked_sd.py         # 설정
├── ui_button_clicked_mn.py         # 메뉴/단축키
├── ui_button_clicked_svc.py        # 주식 변수 설정
├── ui_button_clicked_svj.py        # 주식 전략
├── ui_button_clicked_cvc.py        # 코인 변수 설정
├── ui_button_clicked_cvj.py        # 코인 전략
└── ... (약어 기반 파일명)
```

### V2.36 (커밋 b021269~ddfd9fb)
```
ui/
├── ui_mainwindow.pyd (컴파일된 바이너리, 527개 메서드)
├── ui_button_clicked_dialog_database.py              # DB 관리 다이얼로그
├── ui_button_clicked_dialog_backengine.py            # 백테엔진 다이얼로그
├── ui_button_clicked_dialog_elapsed_tick_number.py   # 경과시간/틱수
├── ui_button_clicked_order.py                        # 주문
├── ui_button_clicked_settings.py                     # 설정
├── ui_button_clicked_shortcut.py                     # 단축키
├── ui_button_clicked_editer_backlog.py               # 백테로그
├── ui_button_clicked_editer_coin.py                  # 코인 전략 에디터
├── ui_button_clicked_editer_stock.py                 # 주식 전략 에디터
├── ui_button_clicked_editer_ga_coin.py               # 코인 GA
├── ui_button_clicked_editer_ga_stock.py              # 주식 GA
├── ui_button_clicked_editer_opti_coin.py             # 코인 최적화
├── ui_button_clicked_editer_opti_stock.py            # 주식 최적화
├── ui_button_clicked_editer_stg_buy_coin.py          # 코인 매수전략
├── ui_button_clicked_editer_stg_buy_stock.py         # 주식 매수전략
├── ui_button_clicked_editer_stg_sell_coin.py         # 코인 매도전략
├── ui_button_clicked_editer_stg_sell_stock.py        # 주식 매도전략
├── ui_button_clicked_etc.py                          # 기타
├── ui_button_clicked_zoom.py                         # 줌
└── ui_button_clicked_chart.py                        # 차트 (유지)
```

### V2.36.U1 (커밋 f2aa6be, 현재)
```
ui/
├── ui_mainwindow.py (527개 메서드) ← .pyd에서 .py로 변환
└── (V2.36과 동일한 모듈 구조)
```

---

## 2. V2.36 모듈이 요구하는 메서드 (총 47개)

V2.36의 신규 UI 모듈들이 `ui.메서드명()` 형태로 호출하는 메서드들입니다.

### 2.1 백테스트 엔진 제어 (9개)

| 메서드 | 설명 | V1.10 | V2.36.U1 |
|--------|------|-------|-------|
| `BacktestProcessAlive()` | 백테스트 프로세스 생존 확인 | ✗ | ✓ |
| `BacktestProcessKill()` | 백테스트 프로세스 강제 종료 | ✗ | ✓ |
| `BackTestengineShow()` | 백테엔진 다이얼로그 표시 | ✗ | ✓ |
| `BacktestEngineStart()` | 백테엔진 시작 | ✗ | ✓ |
| `BacktestEngineKill()` | 백테엔진 종료 | ✗ | ✓ |
| `ClearBacktestQ()` | 백테스트 큐 초기화 | ✗ | ✓ |
| `CoinBacktestLog()` | 코인 백테로그 화면 전환 | ✗ | ✓ |
| `StockBacktestLog()` | 주식 백테로그 화면 전환 | ✗ | ✓ |
| `AutoBackSchedule()` | 자동 백테스트 스케줄 | ✗ | ✓ |

### 2.2 전략 코드 검증 (3개)

| 메서드 | 설명 | V1.10 | V2.36.U1 |
|--------|------|-------|-------|
| `BackCodeTest1()` | 전략 코드 검증 레벨1 | ✗ | ✓ |
| `BackCodeTest2()` | 전략 코드 검증 레벨2 | ✗ | ✓ |
| `BackCodeTest3()` | 전략 코드 검증 레벨3 | ✗ | ✓ |

### 2.3 전략 변환 유틸리티 (6개)

| 메서드 | 설명 | V1.10 | V2.36.U1 |
|--------|------|-------|-------|
| `GetFixStrategy()` | 전략 코드 수정 | ✗ | ✓ |
| `GetOptivarsToGavars()` | 최적화변수 → GA변수 변환 | ✗ | ✓ |
| `GetGavarsToOptivars()` | GA변수 → 최적화변수 변환 | ✗ | ✓ |
| `GetStgtxtToVarstxt()` | 전략텍스트 → 변수텍스트 | ✗ | ✓ |
| `GetStgtxtSort()` | 전략텍스트 정렬 | ✗ | ✓ |
| `GetStgtxtSort2()` | 전략텍스트 정렬2 | ✗ | ✓ |

### 2.4 프로세스 모니터링 (3개)

| 메서드 | 설명 | V1.10 | V2.36.U1 |
|--------|------|-------|-------|
| `CoinStrategyProcessAlive()` | 코인 전략 프로세스 확인 | ✗ | ✓ |
| `CoinTraderProcessAlive()` | 코인 트레이더 프로세스 확인 | ✗ | ✓ |
| `CoinReceiverProcessAlive()` | 코인 수신기 프로세스 확인 | ✗ | ✓ |

### 2.5 설정 관리 (24개)

**주의**: 이 메서드들은 `ui_button_clicked_settings.py`에서 `ui.SettingLoad_01()` 형태로 호출되지만,
실제로는 해당 모듈 내부에 `setting_load_01()` (소문자) 함수로 정의되어 있습니다.

**문제점**: `ui_mainwindow.py`에 래퍼 메서드가 필요하지만 현재 **누락**되어 있습니다.

| 메서드 그룹 | 개수 | V1.10 | V2.36.U1 |
|-------------|------|-------|-------|
| `SettingLoad_01()` ~ `_08()` | 8개 | ✗ | **✗ (누락!)** |
| `SettingSave_01()` ~ `_08()` | 8개 | ✗ | **✗ (누락!)** |
| `SettingOrderLoad_01()` ~ `_04()` | 4개 | ✗ | **✗ (누락!)** |
| `SettingOrderSave_01()` ~ `_04()` | 4개 | ✗ | **✗ (누락!)** |

### 2.6 기타 (2개)

| 메서드 | 설명 | V1.10 | V2.36.U1 |
|--------|------|-------|-------|
| `UpdateDictSet()` | 설정 딕셔너리 업데이트 | ✗ | ✓ |
| `StopScheduler()` | 스케줄러 중지 | ✗ | ✓ |

---

## 3. 결론 및 권장사항

### 3.1 현재 상태 평가

| 항목 | 상태 |
|------|------|
| 백테스트 기능 (9개) | ✓ 모두 존재 |
| 코드 검증 (3개) | ✓ 모두 존재 |
| 전략 변환 (6개) | ✓ 모두 존재 |
| 프로세스 모니터링 (3개) | ✓ 모두 존재 |
| **설정 관리 (24개)** | **✗ 모두 누락** |
| 기타 (2개) | ✓ 모두 존재 |

**총계**: 47개 중 23개 존재, **24개 누락**

### 3.2 누락된 설정 메서드 해결 방안

`ui_button_clicked_settings.py`에는 함수가 소문자로 정의되어 있으나,
호출은 대문자 메서드명으로 이루어집니다. 이를 연결하려면:

**방법 1: ui_mainwindow.py에 래퍼 메서드 추가**
```python
def SettingLoad_01(self):     setting_load_01(self)
def SettingLoad_02(self):     setting_load_02(self)
# ... (24개 모두)
```

**방법 2: 호출부 수정 (비추천)**
- `ui_button_clicked_settings.py` 내부에서 `setting_load_01(ui)` 직접 호출
- 다만 이 파일들이 별도 모듈이므로 구조적으로 부적절

### 3.3 최종 권장사항

1. **V1.10으로 되돌리지 마세요**
   - V1.10은 383개 메서드만 있어 더 많은 기능 누락
   
2. **현재 V2.36.U1 유지하되 설정 메서드 추가**
   - 24개 래퍼 메서드만 추가하면 완전 호환
   
3. **V2.36 백업에서 복원 (최선책)**
   - 작동하는 V2.36 백업이 있다면 그것 사용
   - 또는 V2.36의 `.pyd`를 디컴파일하여 누락 부분 확인

---

## 4. 부록: 모듈 매핑 테이블

| V1.10 모듈명 | V2.36 모듈명 | 주요 기능 |
|--------------|--------------|-----------|
| `ui_button_clicked_db` | `ui_button_clicked_dialog_database` | DB 관리 다이얼로그 |
| `ui_button_clicked_ob` | `ui_button_clicked_order` | 주문 실행 |
| `ui_button_clicked_sd` | `ui_button_clicked_settings` | 설정 관리 |
| `ui_button_clicked_mn` | `ui_button_clicked_shortcut` | 단축키/메뉴 |
| `ui_button_clicked_svc` | `ui_button_clicked_editer_stock` | 주식 에디터 |
| `ui_button_clicked_cvc` | `ui_button_clicked_editer_coin` | 코인 에디터 |
| `ui_button_clicked_svj` | `ui_button_clicked_editer_stg_buy_stock` | 주식 매수전략 |
| `ui_button_clicked_cvj` | `ui_button_clicked_editer_stg_buy_coin` | 코인 매수전략 |
| `ui_button_clicked_svjs` | `ui_button_clicked_editer_stg_sell_stock` | 주식 매도전략 |
| `ui_button_clicked_cvjs` | `ui_button_clicked_editer_stg_sell_coin` | 코인 매도전략 |
| `ui_button_clicked_svoa` | `ui_button_clicked_editer_opti_stock` | 주식 최적화 |
| `ui_button_clicked_cvoa` | `ui_button_clicked_editer_opti_coin` | 코인 최적화 |
| `ui_button_clicked_etsj` | `ui_button_clicked_editer_backlog` | 백테로그 |
| (신규) | `ui_button_clicked_dialog_backengine` | 백테엔진 설정 |
| (신규) | `ui_button_clicked_dialog_elapsed_tick_number` | 경과시간/틱수 |
| (신규) | `ui_button_clicked_editer_ga_coin` | 코인 GA 최적화 |
| (신규) | `ui_button_clicked_editer_ga_stock` | 주식 GA 최적화 |
| (신규) | `ui_button_clicked_etc` | 기타 기능 |
| (신규) | `ui_button_clicked_zoom` | 줌 기능 |

---

**작성일**: 2026-02-01  
**분석 대상**: STOM V1.10 (80ab4ec) vs V2.36 (ddfd9fb) vs V2.36.U1 (f2aa6be)
