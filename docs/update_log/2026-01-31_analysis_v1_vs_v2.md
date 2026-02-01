# STOM V1 vs V2 마이그레이션 분석 보고서

생성일: 2026-02-01

## 1. 모듈 Import 차이점

### 1.1 Set 모듈 (UI 초기화)

| V1 모듈명 | V2 모듈명 | 상태 | 비고 |
|-----------|-----------|------|------|
| `set_logtap` | `set_log_tap` | ✅ 변경됨 | 언더스코어 추가 |
| `set_cbtap` | `set_stg_coin_tap` | ✅ 변경됨 | 명확한 이름으로 변경 |
| `set_sbtap` | `set_stg_stock_tap` | ✅ 변경됨 | 명확한 이름으로 변경 |
| `set_setuptap` | `set_setup_tap` | ✅ 변경됨 | 언더스코어 추가 |
| `set_ordertap` | `set_order_tap` | ✅ 변경됨 | 언더스코어 추가 |
| `set_mainmenu` | `set_main_menu` | ✅ 변경됨 | 언더스코어 추가 |
| - | `set_style.py` | ⚠️ V2 신규 | V2에서 새로 추가된 스타일 모듈 |
| - | `set_text.py` | ⚠️ V2 신규 | V2에서 새로 추가된 텍스트 모듈 |

### 1.2 UI 활성화 모듈

| V1 모듈명 | V2 모듈명 | 상태 |
|-----------|-----------|------|
| `ui_activated_b` | `ui_activated_back` | ✅ 변경됨 |
| `ui_activated_c` | `ui_activated_coin_stg` | ✅ 변경됨 |
| `ui_activated_s` | `ui_activated_stock_stg` | ✅ 변경됨 |

### 1.3 버튼 클릭 모듈 (대규모 리팩토링)

#### V1 전용 모듈 (V2에서 통합/재구성됨)

| V1 모듈명 | V2 대체 모듈 | 기능 |
|-----------|--------------|------|
| `ui_button_clicked_db` | `ui_button_clicked_dialog_database` | 데이터베이스 대화상자 |
| `ui_button_clicked_ob` | `ui_button_clicked_order` | 주문 관련 |
| `ui_button_clicked_sd` | `ui_button_clicked_dialog_backengine` | 백테스트 엔진 대화상자 |
| `ui_button_clicked_mn` | `ui_button_clicked_settings` | 메인 설정 |
| `ui_button_clicked_sj` | `ui_button_clicked_shortcut` | 단축키/바로가기 |
| `ui_button_clicked_etsj` | `ui_button_clicked_dialog_elapsed_tick_number` | 경과 틱 번호 대화상자 |
| `ui_button_clicked_ss_cs` | `ui_button_clicked_settings` | 주식/코인 설정 통합 |

#### V1 전략 에디터 모듈 → V2 세분화

| V1 모듈 | V2 세분화 모듈 | 상태 |
|---------|----------------|------|
| `ui_button_clicked_svjb` (주식 매수) | `ui_button_clicked_editer_stg_buy_stock` | ✅ 분리됨 |
| `ui_button_clicked_svjs` (주식 매도) | `ui_button_clicked_editer_stg_sell_stock` | ✅ 분리됨 |
| `ui_button_clicked_svj` (주식 전략) | `ui_button_clicked_editer_stock` | ✅ 분리됨 |
| `ui_button_clicked_svc` (주식 최적화) | `ui_button_clicked_editer_opti_stock` | ✅ 분리됨 |
| `ui_button_clicked_svoa` (주식 GA) | `ui_button_clicked_editer_ga_stock` | ✅ 분리됨 |
| `ui_button_clicked_cvjb` (코인 매수) | `ui_button_clicked_editer_stg_buy_coin` | ✅ 분리됨 |
| `ui_button_clicked_cvjs` (코인 매도) | `ui_button_clicked_editer_stg_sell_coin` | ✅ 분리됨 |
| `ui_button_clicked_cvj` (코인 전략) | `ui_button_clicked_editer_coin` | ✅ 분리됨 |
| `ui_button_clicked_cvc` (코인 최적화) | `ui_button_clicked_editer_opti_coin` | ✅ 분리됨 |
| `ui_button_clicked_cvoa` (코인 GA) | `ui_button_clicked_editer_ga_coin` | ✅ 분리됨 |

#### V2 신규 모듈

| 모듈명 | 기능 |
|--------|------|
| `ui_button_clicked_editer_backlog` | 백테스트 로그 에디터 |

### 1.4 Utility 모듈

| 모듈명 | V1 | V2 | 비고 |
|--------|----|----|------|
| `hoga.py` | ✅ | ✅ | 호가 처리 |
| `chart.py` | ✅ | ✅ | 차트 처리 |
| `sound.py` | ✅ | ✅ | 사운드 알림 |
| `query.py` | ✅ | ✅ | 데이터베이스 쿼리 |
| `static.py` | ✅ | ✅ | 정적 함수들 |
| `setting.py` | ✅ | ✅ | 설정 관리 |
| `webcrawling.py` | ✅ | ✅ | 웹 크롤링 |
| `telegram_msg.py` | ✅ | ✅ | 텔레그램 메시지 |
| `syntax.py` | ? | ✅ | 구문 검사 |
| `chart_items.py` | ? | ✅ | 차트 아이템 |
| `database_check.py` | ? | ✅ | DB 체크 |
| `database_read_only.py` | ? | ✅ | 읽기전용 DB |
| `db_distinct.py` | ? | ✅ | DB distinct 처리 |
| `timesync.py` | ? | ✅ | 시간 동기화 |
| `total_code_line.py` | ? | ✅ | 코드 라인 계산 |
| `telegram_bot.py` | ? | ✅ | 텔레그램 봇 |

## 2. MainWindow 클래스 차이점

### 2.1 초기화 함수 호출 순서

#### V1 초기화 순서
```python
SetLogFile(self)          # ❌ V2에서 누락
SetIcon(self)
SetMainMenu(self, self.wc)
SetTable(self, self.wc)
SetStockBack(self, self.wc)
SetCoinBack(self, self.wc)
SetLogTap(self, self.wc)
SetSetupTap(self, self.wc)
SetOrderTap(self, self.wc)
SetDialogChart(self, self.wc)
SetDialogEtc(self, self.wc)
SetDialogBack(self, self.wc)
```

#### V2 초기화 순서
```python
# SetLogFile(self) 호출 누락!
SetIcon(self)
SetMainMenu(self, self.wc)
SetTable(self, self.wc)
SetStockBack(self, self.wc)
SetCoinBack(self, self.wc)
SetLogTap(self, self.wc)
SetSetupTap(self, self.wc)
SetOrderTap(self, self.wc)
SetDialogChart(self, self.wc)
SetDialogEtc(self, self.wc)
SetDialogBack(self, self.wc)
```

**⚠️ 중요: V2에서 `SetLogFile(self)` 호출이 누락되었습니다!**

### 2.2 인스턴스 변수 차이

| 변수명 | V1 | V2 | 비고 |
|--------|----|----|------|
| `self.dbreader` | ❌ | ✅ | V2에서 새로 추가된 DB 리더 |

### 2.3 LiveClient 차이점

#### V1: 완전 구현
```python
class LiveSender(Thread):
    def run(self):
        # 실제 소켓 통신 구현
        send_time = timedelta_sec(5)
        while True:
            # 데이터 전송 로직...
```

#### V2: 비활성화
```python
class LiveSender(Thread):
    def run(self):
        # STOM Live disabled
        pass

class LiveClient:
    def __init__(self, _qlist):
        # STOM Live disabled - do not call Start()
        # self.Start()
```

**상태: STOM Live 기능이 V2에서 의도적으로 비활성화됨**

## 3. 메서드 차이점

### 3.1 V2에서 새로 추가된 메서드

#### 줌 버튼 별칭 메서드
```python
# V2에서 추가 (set_stg_stock_tap.py, set_stg_coin_tap.py와의 호환성)
def szButtonClicked_01(self): szoo_button_clicked_01(self)
def szButtonClicked_02(self): szoo_button_clicked_02(self)
def czButtonClicked_01(self): czoo_button_clicked_01(self)
def czButtonClicked_02(self): czoo_button_clicked_02(self)
```

#### dActivated 플레이스홀더
```python
def dActivated_01(self): pass  # Detail combo activation
def dActivated_02(self): pass  # Settings combo activation
def dActivated_03(self): pass  # Order dialog combo activation
```

#### 주식 매수 전략 에디터 메서드 (V2 세분화)
```python
def StockBuyStgLoad(self)
def StockBuyStgSave(self)
def StockBuyFactor(self)
def StockBuyStgStart(self)
def StockBuyVitimeComparison(self)
def StockBuyVilowfiveComparison(self)
def StockBuyPerLimit(self)
def StockBuyLowHighAvgPer(self)
def StockChLowerLimit(self)
def StockChAvgGap(self)
def StockBuySignalInsert(self)
def StockBuyStgStop(self)
```

#### 주식 매도 전략 에디터 메서드
```python
def StockSellStgLoad(self)
def StockSellStgSave(self)
def StockSellFactor(self)
def StockSellStgStart(self)
def StockSellDeadLine(self)
def StockSellProfitLine(self)
def StockSellProfitSave(self)
def StockSellHoldTime(self)
def StockSellBeforeVi(self)
def StockSellLowHighAvgPer(self)
def StockSellChHighComparison(self)
def StockSellAskPriceRamainCount(self)
def StockSellSignalInsert(self)
def StockSellStgStop(self)
```

#### 주식 에디터 메서드
```python
def StockStgEditer(self)
def StockOptiEditer(self)
def StockOptiTestEditer(self)
def StockRwfTestEditer(self)
def StockOptiGaEditer(self)
def StockCondEditer(self)
def StockOptiVarsEditer(self)
def StockVarsEditer(self)
def StockBacktestLog(self)
def StockBacktestDetail(self)
def StockBacktestStart(self)
def StockBackfinderStart(self)
def StockBackfinderSample(self)
def StockOptiStart(self, back_name)
def StockOptiRwftStart(self, back_name)
def StockOptiGaStart(self, back_name)
def StockOptiCondStart(self, back_name)
def StockOptivarsToGavars(self)
def StockGavarsToOptivars(self)
def StockStgVarsChange(self)
def StockStgvarsKeySort(self)
def StockOptivarsKeySort(self)
```

#### 주식 최적화 메서드
```python
def StockOptiBuyLoad(self)
def StockOptiBuySave(self)
def StockOptiVarsLoad(self)
def StockOptiVarsSave(self)
def StockOptiSellLoad(self)
def StockOptiSellSave(self)
def StockOptiSample(self)
def StockOptiToBuySave(self)
def StockOptiToSellSave(self)
def StockOptiStd(self)
def StockOptiOptuna(self)
```

#### 주식 GA 메서드
```python
def StockGavarsLoad(self)
def StockGavarsSave(self)
def StockCondbuyLoad(self)
def StockCondbuySave(self)
def StockCondsellLoad(self)
def StockCondsellSave(self)
```

#### 코인 매수 전략 에디터 메서드
```python
def CoinBuyStgLoad(self)
def CoinBuyStgSave(self)
def CoinBuyFactor(self)
def CoinBuyStgStart(self)
def CoinBuyPerLimit(self)
def CoinBuyLowHighAvgPer(self)
def CoinBuyOpenCloseComparison(self)
def CoinBuyChLowerLimit(self)
def CoinBuyChAvgGap(self)
def CoinBuyChHigh(self)
def CoinBuySignalInsert(self)
def CoinBuyStgStop(self)
```

#### 코인 매도 전략 에디터 메서드
```python
def CoinSellStgLoad(self)
def CoinSellStgSave(self)
def CoinSellFactor(self)
def CoinSellStgStart(self)
def CoinSellDeadLine(self)
def CoinSellProfitLine(self)
def CoinSellProfitSave(self)
def CoinSellHoldTime(self)
def CoinSellChAvgComparison(self)
def CoinSellChHighComparison(self)
def CoinSellLowHighAvgPer(self)
def CoinSellAskPriceRamainCount(self)
def CoinSellSignalInsert(self)
def CoinSellStgStop(self)
```

#### 코인 에디터 메서드
```python
def CoinStgEditer(self)
def CoinOptiEditer(self)
def CoinOptiTestEditer(self)
def CoinRwfTestEditer(self)
def CoinOptiGaEditer(self)
def CoinCondEditer(self)
def CoinOptiVarsEditer(self)
def CoinVarsEditer(self)
def CoinBacktestLog(self)
def CoinBacktestDetail(self)
def CoinBacktestStart(self)
def CoinBackfinderStart(self)
def CoinBackfinderSample(self)
def CoinOptiStart(self, back_name)
def CoinOptiRwftStart(self, back_name)
def CoinOptiGaStart(self, back_name)
def CoinOptiCondStart(self, back_name)
def CoinOptivarsToGavars(self)
def CoinGavarsToOptivars(self)
def CoinStgVarsChange(self)
def CoinStgvarsKeySort(self)
def CoinOptivarsKeySort(self)
```

#### 코인 최적화 메서드
```python
def CoinOptiBuyLoad(self)
def CoinOptiBuySave(self)
def CoinOptiVarsLoad(self)
def CoinOptiVarsSave(self)
def CoinOptiSellLoad(self)
def CoinOptiSellSave(self)
def CoinOptiSample(self)
def CoinOptiToBuySave(self)
def CoinOptiToSellSave(self)
def CoinOptiStd(self)
def CoinOptiOptuna(self)
```

#### 코인 GA 메서드
```python
def CoinGavarsLoad(self)
def CoinGavarsSave(self)
def CoinCondbuyLoad(self)
def CoinCondbuySave(self)
def CoinCondsellLoad(self)
def CoinCondsellSave(self)
```

#### 설정 관련 메서드
```python
def SettingLoad_01(self) ~ SettingLoad_08(self)
def SettingSave_01(self) ~ SettingSave_08(self)
def SettingAllLoad(self)
def SettingAllApp(self)
def SettingAllDel(self)
def SettingAllSave(self)
def SettingAccView(self)
def SettingOrderLoad_01(self) ~ SettingOrderLoad_04(self)
def SettingOrderSave_01(self) ~ SettingOrderSave_04(self)
def SettingStockWeightControl(self)
def SettingCoinWeightControl(self)
def SettingStockWeightCotrolLoad(self)
def SettingStockWeightCotrolSave(self)
def SettingStockWeightCotrolChanged(self, state)
def SettingCoinWeightCotrolLoad(self)
def SettingCoinWeightCotrolSave(self)
def SettingCoinWeightCotrolChanged(self, state)
def SettingStockElapsedTickNumber(self)
def SettingCoinElapsedTickNumber(self)
```

#### 경과 틱 번호 설정
```python
def setButtonClicked_01(self): setting_stock_elapsed_tick_number_sample(self)
def setButtonClicked_02(self): setting_stock_elapsed_tick_number_load(self)
def setButtonClicked_03(self): setting_stock_elapsed_tick_number_save(self)
def cetButtonClicked_01(self): setting_coin_elapsed_tick_number_sample(self)
def cetButtonClicked_02(self): setting_coin_elapsed_tick_number_load(self)
def cetButtonClicked_03(self): setting_coin_elapsed_tick_number_save(self)
```

#### 차트 인디케이터
```python
def IndicatorSettingBasic(self)
def IndicatorSettingLoad(self)
def IndicatorSettingSave(self)
def GetIndicatorDetail(self, code)
```

#### 스케줄러
```python
def StopScheduler(self, gubun=False)
```

#### 백테스트 엔진 별칭
```python
def BacktestEngineStart(self, gubun): start_backengine(self, gubun)
```

### 3.2 V2에서 레거시 호환성 매핑

V2는 V1 메서드명을 유지하면서 내부적으로 새로운 메서드를 호출하도록 매핑:

```python
# V1 svjb* 메서드 → V2 Stock*Buy* 메서드로 매핑
def svjbButtonClicked_01(self): self.StockBuyStgLoad()
def svjbButtonClicked_02(self): self.StockBuyStgSave()
# ... 등등

# V1 svjs* 메서드 → V2 Stock*Sell* 메서드로 매핑
def svjsButtonClicked_01(self): self.StockSellStgLoad()
def svjsButtonClicked_02(self): self.StockSellStgSave()
# ... 등등

# V1 cvjb* 메서드 → V2 Coin*Buy* 메서드로 매핑
def cvjbButtonClicked_01(self): self.CoinBuyStgLoad()
# ... 등등
```

## 4. 중요 발견 사항

### 4.1 ❌ 누락된 함수

| 함수명 | 위치 | 영향도 |
|--------|------|--------|
| `SetLogFile(self)` | V1 line 449 호출 | 🔴 HIGH - 로그 파일 초기화 누락 |

**권장사항**: `SetLogFile` 함수를 찾아서 V2에 추가하거나, V2에서 로그 초기화를 다른 방식으로 처리하는지 확인 필요.

### 4.2 ⚠️ 비활성화된 기능

| 기능 | 상태 | 비고 |
|------|------|------|
| STOM Live | V2에서 완전 비활성화 | LiveSender, LiveClient의 run() 메서드가 pass로 처리됨 |
| proc_live 프로세스 | V2에서 시작 안 함 | 주석 처리됨 |

### 4.3 ✅ 개선된 구조

1. **모듈 네이밍 개선**: 축약형 → 명시적 이름
   - `svjb` → `editer_stg_buy_stock`
   - `cvj` → `editer_coin`

2. **기능별 모듈 분리**: 단일 대형 모듈 → 기능별 세분화
   - V1의 `ui_button_clicked_svj` → V2의 여러 `editer_*` 모듈

3. **메서드명 명확화**:
   - V1: `svjbButtonClicked_01()` (불명확)
   - V2: `StockBuyStgLoad()` (명확)

## 5. 검증 필요 사항

### 5.1 파일 존재 여부 확인

다음 V2 모듈들이 실제로 존재하고 필요한 함수를 export하는지 확인:

```
✅ ui/ui_button_clicked_dialog_database.py
✅ ui/ui_button_clicked_order.py
✅ ui/ui_button_clicked_settings.py
✅ ui/ui_button_clicked_chart.py
✅ ui/ui_button_clicked_shortcut.py
✅ ui/ui_button_clicked_dialog_backengine.py
✅ ui/ui_button_clicked_dialog_elapsed_tick_number.py
✅ ui/ui_button_clicked_editer_backlog.py
✅ ui/ui_button_clicked_editer_coin.py
✅ ui/ui_button_clicked_editer_ga_coin.py
✅ ui/ui_button_clicked_editer_ga_stock.py
✅ ui/ui_button_clicked_editer_opti_coin.py
✅ ui/ui_button_clicked_editer_opti_stock.py
✅ ui/ui_button_clicked_editer_stg_buy_coin.py
✅ ui/ui_button_clicked_editer_stg_buy_stock.py
✅ ui/ui_button_clicked_editer_stg_sell_coin.py
✅ ui/ui_button_clicked_editer_stg_sell_stock.py
✅ ui/ui_button_clicked_editer_stock.py
✅ ui/ui_button_clicked_etc.py
✅ ui/ui_button_clicked_zoom.py
```

### 5.2 함수 정의 확인

다음 함수들이 해당 모듈에 정의되어 있는지 확인:

**ui_button_clicked_editer_stg_buy_stock.py**:
- `stock_buy_stg_load()`
- `stock_buy_stg_save()`
- `stock_buy_factor()`
- `stock_buy_stg_start()`
- `stock_buy_vitime_comparison()`
- `stock_buy_vilowfive_comparison()`
- `stock_buy_per_limit()`
- `stock_buy_low_high_avg_per()`
- `stock_ch_lower_limit()`
- `stock_ch_avg_gap()`
- `stock_buy_signal_insert()`
- `stock_buy_stg_stop()`

**ui_button_clicked_settings.py**:
- `setting_load_01()` ~ `setting_load_08()`
- `setting_save_01()` ~ `setting_save_08()`
- `setting_all_load()`
- `setting_all_app()`
- `setting_all_del()`
- `setting_all_save()`
- `setting_acc_view()`
- `setting_order_load_01()` ~ `setting_order_load_04()`
- `setting_order_save_01()` ~ `setting_order_save_04()`
- `setting_stock_weight_control()`
- `setting_coin_weight_control()`
- `setting_stock_weight_cotrol_load()`
- `setting_stock_weight_cotrol_save()`
- `setting_stock_weight_cotrol_changed()`
- `setting_coin_weight_cotrol_load()`
- `setting_coin_weight_cotrol_save()`
- `setting_coin_weight_cotrol_changed()`
- `setting_stock_elapsed_tick_number()`
- `setting_coin_elapsed_tick_number()`

**ui_button_clicked_chart.py**:
- `indicator_setting_basic()`
- `indicator_setting_load()`
- `indicator_setting_save()`
- `get_indicator_detail()`

## 6. 권장 조치 사항

### 우선순위 HIGH 🔴

1. **SetLogFile 함수 찾기 및 추가**
   - V1에서 `SetLogFile` 함수 정의 위치 확인
   - V2의 ui_mainwindow.py 초기화에 추가

2. **STOM Live 기능 결정**
   - 완전 제거할 것인지, 나중에 재활성화할 것인지 결정
   - 관련 코드 정리 또는 주석 명확화

### 우선순위 MEDIUM 🟡

3. **모든 새로운 메서드 구현 확인**
   - 각 `ui_button_clicked_editer_*` 모듈에 필요한 함수들이 모두 정의되어 있는지 확인
   - 누락된 함수는 구현하거나 placeholder 추가

4. **dbreader 변수 사용처 확인**
   - `self.dbreader`가 어디서 사용되는지 확인
   - 초기화 로직 검증

### 우선순위 LOW 🟢

5. **레거시 메서드 정리**
   - V1 호환성 메서드들을 유지할지, 제거할지 결정
   - Deprecation 경고 추가 고려

6. **문서화**
   - 새로운 메서드명 규칙 문서화
   - 모듈 구조 변경 사항 README 업데이트

## 7. 요약

### ✅ 장점
- 모듈 구조 개선 (가독성 향상)
- 명확한 메서드 네이밍
- 기능별 세분화로 유지보수성 향상

### ⚠️ 주의사항
- SetLogFile 누락
- STOM Live 비활성화
- 대규모 리팩토링으로 인한 잠재적 버그 가능성

### 📊 통계
- 변경된 set 모듈: 6개
- 변경된 activated 모듈: 3개
- 통합/재구성된 button 모듈: 17개
- 새로 추가된 메서드: 약 200개
- V2 신규 인스턴스 변수: 1개 (dbreader)
