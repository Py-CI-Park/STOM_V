# V1 Tick 전략 → V2 마이그레이션 계획

> 작성일: 2026-03-09
> 브랜치: `STOM_Version_2U-cli-research-v251`
> 상태: **계획 수립 완료, 실행 대기**

---

## 1. 배경

V1의 `_database/strategy.db`에서 tick 전략 40개(매수 21 + 매도 19)를 V2로 복사했으나,
V1과 V2의 엔진 API가 다르기 때문에 전략 코드를 V2 규격에 맞게 수정해야 합니다.

**접근 방침**: 엔진을 V1에 맞추는 호환성 코드(hack) 대신, **전략 코드 자체를 V2 API에 맞게 수정**합니다.

---

## 2. 문제 분석

### 2.1 전략 코드 실행 흐름

```
Strategy() 메서드에서 변수 언패킹
    ↓
exec(self.buystg)  또는  exec(self.sellstg)
    ↓
전략 코드 내에서 조건 판단 → self.Buy() / self.Sell() 호출
```

`GetBuyStg()`가 전략 코드를 전처리할 때 **주석(`#`)과 빈 줄을 제거**합니다.
따라서 에러의 줄 번호는 원본이 아닌 전처리된 코드 기준입니다.

### 2.2 V1 vs V2 API 차이

| 항목 | V1 (Live 엔진) | V2 (백테스트 엔진) |
|------|---------------|-------------------|
| Buy 호출 | `self.Buy(종목코드, 종목명, 매수수량, 현재가, 매도호가1, 매수호가1, 데이터길이)` | `self.Buy()` |
| Sell 호출 | `self.Sell(종목코드, 종목명, 매도수량, 현재가, 매도호가1, 매수호가1, 강제청산)` | `self.Sell()` |
| Buy 시그니처 | `Buy(self, 종목코드, 종목명, 매수수량, ...)` | `Buy(self, buy_long=False)` |
| Sell 시그니처 | `Sell(self, 종목코드, 종목명, 매도수량, ...)` | `Sell(self, sell_long=False)` |

V2의 `Buy()`/`Sell()`은 내부적으로 `self.info_for_order`, `self.curr_trade_info` 등을 사용하여
호가 정보, 주문수량 등을 자체적으로 계산합니다. 인자가 필요 없습니다.

### 2.3 발생하는 에러

V1 전략을 V2에서 실행하면:
```
NameError: name '매수수량' is not defined
```
- `GetBuyStg()`가 주석/빈줄 제거 후 컴파일
- 전처리된 코드의 마지막 줄 `self.Buy(종목코드, 종목명, 매수수량, ...)` 실행 시
- `매수수량`이 V2 Strategy() 스코프에 존재하지 않아 NameError 발생

---

## 3. 영향 범위

### 3.1 전체 통계

| 구분 | 전략 수 | 비고 |
|------|---------|------|
| Tick 매수 전략 (stockbuy) | 21개 | 모두 수정 필요 |
| Tick 매도 전략 (stocksell) | 18개 | 모두 수정 필요 |
| **전체** | **39개** | |

### 3.2 수정 유형별 분류

#### 유형 A: self.Buy(args) → self.Buy() (21개 매수 전략)

**모든** tick 매수 전략이 동일한 패턴:
```python
# 현재 (V1)
if 매수:
    self.Buy(종목코드, 종목명, 매수수량, 현재가, 매도호가1, 매수호가1, 데이터길이)

# 수정 후 (V2)
if 매수:
    self.Buy()
```

대상 전략:
- `Tick_B_902`, `Tick_B_902_Study`, `Tick_B_902_Study_2`
- `Tick_B_902_Update`, `Tick_B_902_Update_2`
- `Tick_B_902_905`, `Tick_B_902_905_2`
- `Tick_B_902_905_Study`, `Tick_B_902_905_Study_2`
- `Tick_B_902_905_Update`, `Tick_B_902_905_Update_2`
- `Tick_B_902_905_Update_2_Study`
- `Tick_B_902_v2_Study`
- `Tick_B_905`, `Tick_B_905_Study`, `Tick_B_905_Update`
- `Tick_B_905910_Study`, `Tick_B_905_915_LT`
- `Tick_B_910`, `Tick_B_910_930_RB`
- `Tick_B_930_Dev`

#### 유형 B: self.Sell(args) → self.Sell() (18개 매도 전략)

**모든** tick 매도 전략이 동일한 패턴:
```python
# 현재 (V1)
if 매도:
    self.Sell(종목코드, 종목명, 매도수량, 현재가, 매도호가1, 매수호가1, 강제청산)

# 수정 후 (V2)
if 매도:
    self.Sell()
```

대상 전략:
- `Tick_S_902`, `Tick_S_902_Study`, `Tick_S_902_Update`
- `Tick_S_902_905`, `Tick_S_902_905_2`
- `Tick_S_902_905_Study`, `Tick_S_902_905_Update`
- `Tick_S_902_905_Update_2`, `Tick_S_902_905_Update_2_Study`
- `Tick_S_902_v2_Study`
- `Tick_S_905`, `Tick_S_905_Study`, `Tick_S_905_Update`
- `Tick_S_905910_Study`, `Tick_S_905_915_LT`
- `Tick_S_910`, `Tick_S_910_930_RB`
- `Tick_S_930_Dev`

**주의**: 일부 매도 전략에 주석 처리된 `# self.Sell(...)` 도 있으나, 주석은 `GetBuyStg()`에서 제거되므로 수정 불필요.

#### 유형 C: VI아래5호가 — 엔진 수정 필요 (21개 매수 전략)

`VI아래5호가` 변수는 전략 조건에서 사용되지만, V2 엔진의 Strategy() 메서드에서 계산되지 않습니다.

```python
# 전략에서 사용하는 조건
elif not (현재가 < VI아래5호가):
    매수 = False
```

이것은 전략 코드의 문제가 아니라 **엔진의 누락**입니다.
`GetUvilower5()` 함수를 `utility/static.py`에 추가하고,
tick/min 엔진의 Strategy()에서 `VI아래5호가`를 계산해야 합니다.

---

## 4. 수정하지 않아도 되는 항목

### 4.1 동적 함수 (SetGlobalsFunc 경유)

아래 함수들은 V2의 `trade/strategy_base.py`에 이미 구현되어 있으며,
`SetGlobalsFunc()` → `UpdateGlobalsFunc()` → `globals().update()`를 통해
exec() 스코프에 자동 주입됩니다. **수정 불필요.**

| 함수명 | strategy_base.py 메서드 | 사용 전략 수 |
|--------|------------------------|-------------|
| `당일거래대금각도(tick, pre)` | `_당일거래대금각도` | 20개 (매수) |
| `등락율각도(tick, pre)` | `_등락율각도` | 28개 (매수+매도) |
| `전일비각도(tick, pre)` | `_전일비각도` | 9개 (매수) |
| `경과틱수(조건명)` | `_경과틱수` | - |
| `최저현재가(tick, hold_time)` | `_최저현재가` | 매도 전략 |
| `이동평균(tick, pre)` | `_이동평균` | 매도 전략 |
| `현재가N(n)` | `_현재가N` | 매도 전략 |
| `초당거래대금N(n)` | `_초당거래대금N` | 매수 전략 |
| `초당거래대금평균(n)` | `_초당거래대금평균` | 매수 전략 |
| `체결강도평균(n, pre)` | `_체결강도평균` | 매도 전략 |
| `체결강도N(n)` | `_체결강도N` | 매도 전략 |

### 4.2 Strategy() 스코프 변수

아래 변수들은 V2의 `backengine_kiwoom_tick.py` Strategy()에서 이미 언패킹됩니다:

`현재가`, `시가`, `고가`, `저가`, `등락율`, `당일거래대금`, `체결강도`,
`초당매수수량`, `초당매도수량`, `거래대금증감`, `전일비`, `회전율`, `전일동시간비`,
`시가총액`, `라운드피겨위5호가이내`, `초당거래대금`, `고저평균대비등락율`,
`저가대비고가등락율`, `매도총잔량`, `매수총잔량`, `매도호가1~5`, `매수호가1~5`,
`매도잔량1~5`, `매수잔량1~5`, `관심종목`, `종목명`, `종목코드`, `데이터길이`, `시분초`

---

## 5. 실행 계획

### 5.1 단계 1: 엔진 보강 (VI아래5호가)

V2 엔진에 `GetUvilower5` 함수와 `VI아래5호가` 변수를 추가합니다.
이것은 V1 호환성 hack이 아니라, V2에 누락된 정당한 기능 보강입니다.

수정 파일:
- `utility/static.py` — `GetUvilower5()` 함수 추가 (JIT + non-JIT)
- `backtest/backengine_kiwoom_tick.py` — `VI아래5호가` 계산 추가
- `backtest/backengine_kiwoom_min.py` — `VI아래5호가` 계산 추가

```python
# backengine_kiwoom_tick.py Strategy() 수정
# 변경 전:
VI해제시간, 순매수금액 = dt_ymdhms(str(int(VI해제시간))), 초당매수금액 - 초당매도금액

# 변경 후:
VI해제시간, VI아래5호가 = dt_ymdhms(str(int(VI해제시간))), GetUvilower5(VI가격, VI호가단위, self.index)
순매수금액 = 초당매수금액 - 초당매도금액
```

### 5.2 단계 2: 전략 DB 일괄 수정

SQLite로 strategy.db의 tick 전략 코드를 일괄 수정합니다.

**수정 규칙:**

| 패턴 | 변환 |
|------|------|
| `self.Buy(종목코드, 종목명, 매수수량, 현재가, 매도호가1, 매수호가1, 데이터길이)` | `self.Buy()` |
| `self.Sell(종목코드, 종목명, 매도수량, 현재가, 매도호가1, 매수호가1, 강제청산)` | `self.Sell()` |
| `self.Sell(종목코드, 종목명, 매도수량*0.5, 현재가, 매도호가1, 매수호가1, 강제청산)` (주석 내) | 변경 불필요 (주석은 무시됨) |

**수정 스크립트 예시:**

```python
import sqlite3

conn = sqlite3.connect('_database/strategy.db')

for tbl in ('stockbuy', 'stocksell'):
    rows = conn.execute(f'SELECT [index], * FROM {tbl}').fetchall()
    # 실제 컬럼명 확인 필요 (index, 전략코드)
    cursor = conn.execute(f'PRAGMA table_info({tbl})')
    cols = [row[1] for row in cursor.fetchall()]
    code_col = cols[1]  # 두 번째 컬럼이 전략코드

    for row in rows:
        name = row[0]
        code = row[1]
        if not name.startswith('Tick_'):
            continue

        original = code
        # Buy 호출 수정
        code = code.replace(
            'self.Buy(종목코드, 종목명, 매수수량, 현재가, 매도호가1, 매수호가1, 데이터길이)',
            'self.Buy()'
        )
        # Sell 호출 수정
        code = code.replace(
            'self.Sell(종목코드, 종목명, 매도수량, 현재가, 매도호가1, 매수호가1, 강제청산)',
            'self.Sell()'
        )

        if code != original:
            conn.execute(
                f'UPDATE {tbl} SET [{code_col}] = ? WHERE [index] = ?',
                (code, name)
            )
            print(f'  수정됨: {tbl}:{name}')

conn.commit()
conn.close()
```

### 5.3 단계 3: 검증

```bash
# Tick E2E 테스트
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
  --buy Tick_B_902 --sell Tick_S_902 \
  --start 20250407 --end 20250408 \
  --start-time 90000 --end-time 153000 \
  --engines 2 --timeframe tick --timeout 300

# Min 회귀 테스트
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
  --buy Min_B_Study_251227 --sell Min_S_Study_251227 \
  --start 20250407 --end 20250411 \
  --start-time 90000 --end-time 153000 \
  --engines 2 --timeframe min --timeout 120
```

기대 결과: 두 테스트 모두 `"status": "success"`

---

## 6. V2 전략 작성 규칙 (향후 참고)

### 매수 전략 템플릿

```python
# 커스텀 지표 계산 (선택)
전일종가 = 현재가 / (1 + (등락율 / 100))
시가등락율 = ((시가 - 전일종가) / 전일종가) * 100

# 매수 조건 체크
매수 = True
if not (관심종목 == 1):
    매수 = False
elif not (1000 < 현재가 <= 50000):
    매수 = False
# ... 추가 조건 ...

# V2 매수 호출 (인자 없음)
if 매수:
    self.Buy()
```

### 매도 전략 템플릿

```python
# 매도 조건 체크
매도 = False
if 등락율 > 29.5:
    매도 = True
elif 수익률 <= -5.0:
    매도 = True
# ... 추가 조건 ...

# V2 매도 호출 (인자 없음)
if 매도:
    self.Sell()
```

### 사용 가능한 변수/함수 목록

**Strategy() 스코프 변수** (exec 시 자동 사용 가능):
- 가격: `현재가`, `시가`, `고가`, `저가`, `등락율`
- 거래: `당일거래대금`, `체결강도`, `초당매수수량`, `초당매도수량`, `초당거래대금`
- 시장: `거래대금증감`, `전일비`, `회전율`, `전일동시간비`, `시가총액`
- VI: `VI아래5호가`, `라운드피겨위5호가이내`
- 호가: `매도호가1~5`, `매수호가1~5`, `매도잔량1~5`, `매수잔량1~5`, `매도총잔량`, `매수총잔량`
- 메타: `종목명`, `종목코드`, `데이터길이`, `시분초`, `관심종목`
- 보유 (매도 시): `수익률`, `보유시간`, `최고수익률`, `최저수익률`, `포지션`

**SetGlobalsFunc 주입 함수** (exec 시 자동 사용 가능):
- N틱 전: `현재가N(n)`, `시가N(n)`, `등락율N(n)`, `당일거래대금N(n)`, `체결강도N(n)` 등
- 통계: `이동평균(tick, pre)`, `체결강도평균(tick, pre)`, `초당거래대금평균(tick)`
- 각도: `당일거래대금각도(tick, pre)`, `등락율각도(tick, pre)`, `전일비각도(tick, pre)`
- 구간: `최고현재가(tick)`, `최저현재가(tick, hold_time)`, `변동성(tick)` 등
- 기타: `경과틱수(조건명)`, `이평지지(tick)`, `시가지지(tick)` 등

---

## 7. 요약

| 단계 | 작업 | 파일/대상 | 수정 수 |
|------|------|-----------|---------|
| 1 | `GetUvilower5` 추가 + `VI아래5호가` 계산 | static.py, tick/min 엔진 | 3파일 |
| 2 | `self.Buy(args)` → `self.Buy()` | strategy.db stockbuy | 21개 전략 |
| 2 | `self.Sell(args)` → `self.Sell()` | strategy.db stocksell | 18개 전략 |
| 3 | E2E 검증 (tick + min 회귀) | CLI 백테스트 | 2회 |
