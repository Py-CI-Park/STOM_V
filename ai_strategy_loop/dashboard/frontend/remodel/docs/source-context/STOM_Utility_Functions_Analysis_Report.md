# STOM 매도전략 유틸리티 함수 라이브러리 분석 보고서

> **문서 ID**: STOM_UTIL_FUNC_ANALYSIS_V1  
> **작성일**: 2026-02-04  
> **출처**: STOMER 157 커뮤니티 (SoulsnoW 공유)  
> **분석 대상**: 매도전략용 재사용 가능 유틸리티 함수 라이브러리  
> **관련 시스템**: STOM 주식 자동매매 백테스팅 시스템 (Tick 기반)

---

## 목차

1. [출처 및 배경](#1-출처-및-배경)
2. [핵심 설계 철학](#2-핵심-설계-철학)
3. [스크린샷 코드 완전 복원](#3-스크린샷-코드-완전-복원)
4. [전체 함수 라이브러리 정의](#4-전체-함수-라이브러리-정의)
5. [함수별 상세 분석](#5-함수별-상세-분석)
6. [기능별 분류 체계](#6-기능별-분류-체계)
7. [STOM 기존 전략과의 비교 분석](#7-stom-기존-전략과의-비교-분석)
8. [조합 전략 설계 가이드](#8-조합-전략-설계-가이드)
9. [STOM 시스템 통합 방안](#9-stom-시스템-통합-방안)
10. [결론 및 권장사항](#10-결론-및-권장사항)

---

## 1. 출처 및 배경

### 1.1 커뮤니티 정보

- **플랫폼**: STOMER 157 카페 (스톰 커뮤니티)
- **공유자**: SoulsnoW | 부산 | ㅂ○○승ㅎ
- **공유 시각**: 오후 11:01 ~ 11:03
- **반응**: ❤️ 2, 🤩 2, 👍 4

### 1.2 공유 맥락

SoulsnoW는 STOM 시스템의 매도전략에 활용할 수 있는 유틸리티 함수들을 파이썬 클래스 메서드로 **코드화**하는 작업을 진행 중이며, 그 일부를 "맛배기"로 커뮤니티에 공개했습니다.

**핵심 메시지 요약**:

- "코드화 시키는 중입니다."
- "맛배기로 하나만 보여드리죠 ㅋ"
- "조합까지는 코딩 안 할 거예요"
- "예를 들면.. `횡보감지(20) and 급락감지(3, 0.5)`"
- "뭐 이런식으로 두세개 합쳐서 매도전략을 만들 수 있음"
- "다 퍼준다고 보면 됨 ㅋㅋ"

### 1.3 설계 의도

이 함수 라이브러리의 핵심 목적은 **매도 전략의 빌딩 블록(Building Block)** 제공입니다. 개별 함수는 단일 시장 상태(변동성, 횡보, 급락 등)를 감지하는 역할을 하며, 사용자가 이들을 `and`/`or`로 조합하여 다양한 매도 전략을 코딩 없이 구성할 수 있도록 설계되었습니다.

---

## 2. 핵심 설계 철학

### 2.1 모듈화 원칙

```
기존 STOM 매도 전략 (모놀리식)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if 등락율각도(30) >= 20 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.3 and ...
    매도 = True
elif 등락율각도(30) >= 10 and ...
    매도 = True
...

SoulsnoW 유틸리티 함수 (모듈식)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if 횡보감지(20) and 급락감지(3, 0.5):
    매도 = True
```

### 2.2 3계층 구조

```
┌──────────────────────────────────────────────────┐
│  Layer 3: 조합 전략 (사용자 정의)                   │
│  예: 횡보감지(20) and 급락감지(3, 0.5)              │
├──────────────────────────────────────────────────┤
│  Layer 2: 복합 패턴 감지 함수                       │
│  예: 횡보후급등(), 연속상승및급등()                    │
│  예: 변동성기반_동적손절청산()                        │
├──────────────────────────────────────────────────┤
│  Layer 1: 기초 메트릭/상태 감지 함수                 │
│  예: 변동성(), 횡보감지(), 급락감지()                 │
├──────────────────────────────────────────────────┤
│  Layer 0: STOM 시스템 데이터                        │
│  self.arry_data, self.indexn, fi() 등              │
└──────────────────────────────────────────────────┘
```

---

## 3. 스크린샷 코드 완전 복원

> 아래는 첫 번째 이미지(코드 스크린샷)에서 확인 가능한 코드의 **완전 복원본**입니다.  
> 이미지 하단이 잘려있는 `변동성기반_동적손절률청산` 함수는 파라미터 패턴과 변동성 구간 로직을 기반으로 추론하여 완성했습니다.

### 3.1 이평60근접개수

```python
def 이평60근접개수(tick, per=0.33):
    closes = self.arry_data[self.indexn+1-tick:self.indexn+1, 1]
    sma60  = self.arry_data[self.indexn+1-tick:self.indexn+1, 45]
    deviation = np.abs(closes - sma60) / sma60 * 100
    return np.sum(deviation <= per)
```

**분석**:
- `self.arry_data[..., 1]`: 종가(현재가) 컬럼
- `self.arry_data[..., 45]`: 60틱 이동평균 컬럼 (사전 계산된 값)
- 최근 `tick`개 데이터 중 60이평 대비 괴리율이 `per`(0.33%) 이하인 틱의 **개수**를 반환
- 반환값이 클수록 가격이 이동평균선에 밀착하여 횡보 중임을 의미

### 3.2 변동성

```python
def 변동성(tick, pre=0):
    closes = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, 1]
    volatility = np.std(closes) / np.mean(closes) * 100
    return volatility
```

**분석**:
- **변동계수(CV, Coefficient of Variation)** 계산: `(표준편차 / 평균) × 100`
- `pre` 파라미터: 오프셋(시간 이동). `pre=0`이면 현재 기준, `pre=5`이면 5틱 전 기준
- 다른 함수들(`변동성급증`, `횡보감지` 등)의 **기반 메트릭**으로 사용됨
- 단위: 퍼센트(%)

### 3.3 변동성급증

```python
def 변동성급증(tick1=5, tick2=10, multiple=2):
    recent_vol = 변동성(tick1)
    prev_vol   = 변동성(tick2, tick1)
    return recent_vol > prev_vol * multiple
```

**분석**:
- 최근 `tick1`(5틱) 구간의 변동성과 그 직전 구간의 변동성을 비교
- `변동성(tick2, tick1)`: `tick1` 만큼 오프셋된 시점에서 `tick2` 길이만큼의 변동성을 계산
- 최근 5틱 변동성이 직전 10틱(5틱 오프셋) 변동성의 2배 이상이면 True
- Boolean 반환

### 3.4 횡보감지

```python
def 횡보감지(tick, per=0.5):
    closes = self.arry_data[self.indexn+1-tick:self.indexn+1, 1]
    volatility = np.std(closes) / np.mean(closes) * 100
    return volatility <= per
```

**분석**:
- `변동성()` 함수와 동일한 계산을 수행하되, 결과를 `per`(0.5%)와 비교하여 Boolean 반환
- 변동계수가 `per` 이하이면 횡보(박스권) 상태로 판정
- `변동성()` 함수를 내부에서 호출하지 않고 직접 계산하는 것은 성능 최적화 목적으로 추정

### 3.5 급락감지

```python
def 급락감지(tick, per=0.3):
    drop_rate = (현재가 / 현재가N(tick) - 1) * 100
    return drop_rate <= -per
```

**분석**:
- 현재가와 `tick`틱 전 현재가의 등락율을 계산
- 등락율이 `-per`(-0.3%) 이하이면 급락으로 판정
- `현재가`, `현재가N(tick)`은 STOM 시스템의 내장 변수/함수

### 3.6 이평60이탈

```python
def 이평60이탈(per=1.0):
    return (현재가 / 이동평균(60) - 1) * 100 <= -per
```

**분석**:
- 현재가가 60틱 이동평균 대비 `per`(1.0%) 이상 하방 이탈했는지 판정
- 추세 전환(하락 전환) 신호로 활용
- STOM의 기존 매도 조건 "[조건 7] 이동평균 이탈 조건"과 유사한 로직

### 3.7 변동성기반_동적손절률청산 (추론 완성)

```python
def 변동성기반_동적손절률청산(base_per=1.0, vol_tick=30):
    """변동성에 따른 동적 손절률 청산 전략"""
    # 현재 변동성 계산
    current_vol = 변동성(vol_tick)

    # 변동성 구간에 따른 손절률 조정
    if current_vol >= 2.0:          # 초고변동성 (2% 이상)
        dynamic_per = base_per * 3.0  # 3배 넓은 손절률
        reason = "초고변동성"
    elif current_vol >= 1.0:        # 고변동성 (1-2%)
        dynamic_per = base_per * 2.0  # 2배 넓은 손절률
        reason = "고변동성"
    elif current_vol >= 0.5:        # 중변동성 (0.5-1%)
        dynamic_per = base_per * 1.5  # 1.5배 손절률
        reason = "중변동성"
    else:                           # 저변동성 (0.5% 미만)
        dynamic_per = base_per * 1.0  # 기본 손절률
        reason = "저변동성"

    # 현재 수익률이 동적 손절률 이하이면 청산
    return 수익률 <= -dynamic_per
```

**분석**:
- 이미지에서 초고변동성(2% 이상, ×3.0), 고변동성(1-2%, ×2.0), 중변동성(0.5-1%, ×1.5)까지 확인 가능
- 저변동성(0.5% 미만, ×1.0) 구간과 최종 판정 로직은 패턴을 기반으로 추론
- 핵심 원리: 변동성이 높을수록 손절 폭을 넓혀 조기 손절(whipsaw)을 방지

**변동성 구간별 손절률 매핑**:

| 변동성 구간 | CV 범위 | 배수 | base_per=1.0 시 손절률 |
|:-----------:|:-------:|:----:|:---------------------:|
| 초고변동성 | ≥ 2.0% | ×3.0 | -3.0% |
| 고변동성 | 1.0~2.0% | ×2.0 | -2.0% |
| 중변동성 | 0.5~1.0% | ×1.5 | -1.5% |
| 저변동성 | < 0.5% | ×1.0 | -1.0% |

---

## 4. 전체 함수 라이브러리 정의

> 스크린샷의 코드와 제공된 함수 시그니처를 종합하여, 전체 라이브러리의 추론 구현을 카테고리별로 정리합니다.

### 4.1 기초 메트릭 함수 (수치 반환형)

#### 4.1.1 변동성 (tick, pre=0) → float

```python
def 변동성(tick, pre=0):
    """구간 변동계수(CV) 계산"""
    closes = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, 1]
    volatility = np.std(closes) / np.mean(closes) * 100
    return volatility
```

- **반환**: 변동계수(%) - 값이 클수록 가격 변동이 큼
- **용도**: 다른 함수들의 기반 메트릭, 변동성 수준 직접 참조

#### 4.1.2 이평근접개수 (window, tick=30, per=0.33) → int

```python
def 이평근접개수(window, tick=30, per=0.33):
    """이동평균선 근접 틱 수 계산"""
    closes = self.arry_data[self.indexn+1-tick:self.indexn+1, 1]
    sma    = self.arry_data[self.indexn+1-tick:self.indexn+1, fi(f'이동평균{window}')]
    deviation = np.abs(closes - sma) / sma * 100
    return np.sum(deviation <= per)
```

- **반환**: `window` 이평선 대비 괴리율이 `per`% 이하인 틱의 개수
- **용도**: 이동평균선 밀착(수렴) 정도 판단

#### 4.1.3 구간저가대비현재가등락율 (tick, pre=0) → float

```python
def 구간저가대비현재가등락율(tick, pre=0):
    """구간 내 최저가 대비 현재가 등락율"""
    closes = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, 1]
    low_price = np.min(closes)
    return (현재가 / low_price - 1) * 100
```

- **반환**: 구간 저점 대비 반등률(%)
- **용도**: 바닥 대비 얼마나 올랐는지 판단 (과열 판정)

#### 4.1.4 거래대금평균대비비율 (tick, pre=0) → float

```python
def 거래대금평균대비비율(tick, pre=0):
    """현재 거래대금의 구간 평균 대비 비율"""
    volumes = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('초당거래대금')]
    avg_vol = np.mean(volumes)
    if avg_vol == 0:
        return 0
    return 초당거래대금 / avg_vol
```

- **반환**: 비율 (1.0 = 평균 수준, 3.0 = 평균의 3배)
- **용도**: 거래 활성도 상대적 비교

#### 4.1.5 체결강도평균대비비율 (tick, pre=0) → float

```python
def 체결강도평균대비비율(tick, pre=0):
    """현재 체결강도의 구간 평균 대비 비율"""
    strengths = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('체결강도')]
    avg_str = np.mean(strengths)
    if avg_str == 0:
        return 0
    return 체결강도 / avg_str
```

- **반환**: 비율 (1.0 = 평균 수준)
- **용도**: 매수/매도 세력 상대 강도 판단

#### 4.1.6 호가총잔량비율 (tick, pre=0) → float

```python
def 호가총잔량비율(tick, pre=0):
    """매수총잔량 / 매도총잔량 비율"""
    buy_totals = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('매수총잔량')]
    sell_totals = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('매도총잔량')]
    avg_buy = np.mean(buy_totals)
    avg_sell = np.mean(sell_totals)
    if avg_sell == 0:
        return 0
    return avg_buy / avg_sell
```

- **반환**: 비율 (>1.0 = 매수 우위, <1.0 = 매도 우위)
- **용도**: 호가창 수급 균형 판단

#### 4.1.7 횡보감지 (tick, per=0.5, pre=0) → float

```python
def 횡보감지(tick, per=0.5, pre=0):
    """구간 변동계수 반환 (횡보 판정용)"""
    closes = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, 1]
    volatility = np.std(closes) / np.mean(closes) * 100
    return volatility
```

- **반환**: 변동계수(%) - `per` 이하이면 횡보 상태
- **참고**: 수치 반환 버전. Boolean 반환 버전(`횡보감지 → bool`)은 별도 존재
- **두 가지 시그니처**: 수치 반환형(`return 0`)과 Boolean 반환형(`return volatility <= per`) 두 버전이 공존

---

### 4.2 단일 상태 감지 함수 (Boolean 반환형)

#### 4.2.1 변동성 관련

```python
def 변동성급증(tick, multi=2):
    """최근 구간 변동성이 직전 구간의 multi배 이상인지"""
    recent_vol = 변동성(tick)
    prev_vol   = 변동성(tick, tick)
    return recent_vol > prev_vol * multi

def 변동성급감(tick, multi=2):
    """최근 구간 변동성이 직전 구간의 1/multi 이하인지"""
    recent_vol = 변동성(tick)
    prev_vol   = 변동성(tick, tick)
    if prev_vol == 0:
        return False
    return recent_vol < prev_vol / multi
```

#### 4.2.2 가격 변동 관련

```python
def 가격급등(tick, per=0.75):
    """tick틱 전 대비 현재가가 per% 이상 상승했는지"""
    rise_rate = (현재가 / 현재가N(tick) - 1) * 100
    return rise_rate >= per

def 가격급락(tick, per=0.75):
    """tick틱 전 대비 현재가가 per% 이상 하락했는지"""
    drop_rate = (현재가 / 현재가N(tick) - 1) * 100
    return drop_rate <= -per
```

#### 4.2.3 거래대금 관련

```python
def 거래대금급증(tick, ratio=3):
    """현재 거래대금이 구간 평균의 ratio배 이상인지"""
    return 거래대금평균대비비율(tick) >= ratio

def 거래대금급감(tick, ratio=0.75):
    """현재 거래대금이 구간 평균의 ratio배 이하인지"""
    return 거래대금평균대비비율(tick) <= ratio
```

#### 4.2.4 체결강도 관련

```python
def 체결강도급등(tick, ratio=1.1):
    """현재 체결강도가 구간 평균의 ratio배 이상인지"""
    return 체결강도평균대비비율(tick) >= ratio

def 체결강도급락(tick, ratio=0.9):
    """현재 체결강도가 구간 평균의 ratio배 이하인지"""
    return 체결강도평균대비비율(tick) <= ratio
```

#### 4.2.5 호가 관련

```python
def 호가상승압력(tick, ratio=0.66):
    """매수잔량/매도잔량 비율이 ratio 이상인지 (매수 우위)"""
    return 호가총잔량비율(tick) >= ratio

def 호가하락압력(tick, ratio=0.33):
    """매수잔량/매도잔량 비율이 ratio 이하인지 (매도 우위)"""
    return 호가총잔량비율(tick) <= ratio

def 호가갭발생(hogagap, pre=0):
    """호가 갭(스프레드)이 비정상적으로 큰지"""
    spread = (매도호가1 - 매수호가1) / 현재가 * 100
    return spread >= hogagap
```

#### 4.2.6 매수/매도 수량 관련

```python
def 매수수량급증(tick, multi=3, pre=0):
    """현재 매수수량이 구간 평균의 multi배 이상인지"""
    buys = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('초당매수수량')]
    avg_buy = np.mean(buys)
    return 초당매수수량 > avg_buy * multi if avg_buy > 0 else False

def 매수수량급감(tick, multi=3, pre=0):
    """현재 매수수량이 구간 평균의 1/multi 이하인지"""
    buys = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('초당매수수량')]
    avg_buy = np.mean(buys)
    return 초당매수수량 < avg_buy / multi if avg_buy > 0 else False

def 매도수량급증(tick, multi=3, pre=0):
    """현재 매도수량이 구간 평균의 multi배 이상인지"""
    sells = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('초당매도수량')]
    avg_sell = np.mean(sells)
    return 초당매도수량 > avg_sell * multi if avg_sell > 0 else False

def 매도수량급감(tick, multi=3, pre=0):
    """현재 매도수량이 구간 평균의 1/multi 이하인지"""
    sells = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, fi('초당매도수량')]
    avg_sell = np.mean(sells)
    return 초당매도수량 < avg_sell / multi if avg_sell > 0 else False
```

#### 4.2.7 연속 추세 관련

```python
def 연속상승(tick):
    """최근 tick틱 동안 가격이 연속 상승했는지"""
    closes = self.arry_data[self.indexn+1-tick:self.indexn+1, 1]
    for i in range(1, len(closes)):
        if closes[i] <= closes[i-1]:
            return False
    return True

def 연속하락(tick):
    """최근 tick틱 동안 가격이 연속 하락했는지"""
    closes = self.arry_data[self.indexn+1-tick:self.indexn+1, 1]
    for i in range(1, len(closes)):
        if closes[i] >= closes[i-1]:
            return False
    return True
```

#### 4.2.8 이동평균 이탈

```python
def 이평이탈(window, per=1.0):
    """현재가가 window 이동평균 대비 per% 이상 하방 이탈했는지"""
    return (현재가 / 이동평균(window) - 1) * 100 <= -per
```

---

### 4.3 복합 패턴 감지 함수 (Boolean 반환형)

#### 4.3.1 횡보 기반 패턴

```python
def 횡보후급등(tick1, per1=0.5, tick2=2, per2=0.5):
    """tick1 구간 횡보 후 tick2 틱 내 per2% 이상 급등했는지"""
    is_sideways = 횡보감지(tick1, per1)  # Boolean 버전
    is_surge = 가격급등(tick2, per2)
    return is_sideways and is_surge

def 횡보후연속상승(tick1, per1=0.5, tick2=3):
    """tick1 구간 횡보 후 tick2 틱 연속 상승했는지"""
    is_sideways = 횡보감지(tick1, per1)
    is_rising = 연속상승(tick2)
    return is_sideways and is_rising

def 횡보후급락(tick1, per1=0.5, tick2=2, per2=0.5):
    """tick1 구간 횡보 후 tick2 틱 내 per2% 이상 급락했는지"""
    is_sideways = 횡보감지(tick1, per1)
    is_drop = 가격급락(tick2, per2)
    return is_sideways and is_drop

def 횡보후연속하락(tick1, per1=0.5, tick2=3):
    """tick1 구간 횡보 후 tick2 틱 연속 하락했는지"""
    is_sideways = 횡보감지(tick1, per1)
    is_falling = 연속하락(tick2)
    return is_sideways and is_falling
```

#### 4.3.2 연속 추세 + 급변 패턴

```python
def 연속상승및급등(tick1, tick2=2, per=0.5):
    """tick1 틱 연속 상승 후 추가 per% 급등"""
    return 연속상승(tick1) and 가격급등(tick2, per)

def 연속하락및급락(tick1, tick2=2, per=0.5):
    """tick1 틱 연속 하락 후 추가 per% 급락"""
    return 연속하락(tick1) and 가격급락(tick2, per)
```

#### 4.3.3 이동평균 기반 패턴

```python
def 이평지지후급등(window, tick=30, per1=0.33, cnt=10, per2=1.0):
    """이평선 근접(지지) 후 급등"""
    near_count = 이평근접개수(window, tick, per1)
    is_surge = 가격급등(cnt, per2)
    return near_count >= cnt and is_surge
```

#### 4.3.4 변동성 기반 패턴

```python
def 변동성급증후수익률상승(tick, multi=2):
    """변동성 급증 이후 수익률이 상승 중인지"""
    return 변동성급증(tick, multi) and 수익률 > 0

def 변동성급증후수익률하락(tick, multi=2):
    """변동성 급증 이후 수익률이 하락 중인지"""
    return 변동성급증(tick, multi) and 수익률 < 0
```

#### 4.3.5 장기보유 패턴

```python
def 횡보상태장기보유(tick, time_=600):
    """횡보 상태에서 time_(초) 이상 보유 중인지"""
    is_sideways = 횡보감지(tick)  # Boolean 버전: CV ≤ 기본 per
    return is_sideways and 보유시간 >= time_
```

---

### 4.4 동적 청산 함수 (Boolean 반환형)

#### 4.4.1 변동성기반 동적 익절

```python
def 변동성기반_동적익절청산(tick, multi=4):
    """변동성에 비례한 동적 익절"""
    current_vol = 변동성(tick)

    if current_vol >= 2.0:          # 초고변동성
        target_per = current_vol * multi
    elif current_vol >= 1.0:        # 고변동성
        target_per = current_vol * (multi * 0.75)
    elif current_vol >= 0.5:        # 중변동성
        target_per = current_vol * (multi * 0.5)
    else:                           # 저변동성
        target_per = max(current_vol * multi, 0.5)  # 최소 0.5%

    return 수익률 >= target_per
```

#### 4.4.2 변동성기반 동적 손절

```python
def 변동성기반_동적손절청산(tick, multi=2):
    """변동성에 비례한 동적 손절 (스크린샷 코드 기반)"""
    current_vol = 변동성(tick)
    base_per = 1.0

    if current_vol >= 2.0:          # 초고변동성 (2% 이상)
        dynamic_per = base_per * 3.0  # 3배 넓은 손절률
    elif current_vol >= 1.0:        # 고변동성 (1-2%)
        dynamic_per = base_per * 2.0  # 2배 넓은 손절률
    elif current_vol >= 0.5:        # 중변동성 (0.5-1%)
        dynamic_per = base_per * 1.5  # 1.5배 손절률
    else:                           # 저변동성 (0.5% 미만)
        dynamic_per = base_per * 1.0  # 기본 손절률

    return 수익률 <= -dynamic_per
```

#### 4.4.3 장기보유 종목 동적 익절

```python
def 변동성기반_장기보유종목_동적익절청산(tick, time_=600, minper=0.3, multi=1):
    """장기 보유 시 낮은 기준의 익절 적용"""
    if 보유시간 < time_:
        return False
    current_vol = 변동성(tick)
    target_per = max(current_vol * multi, minper)
    return 수익률 >= target_per
```

---

### 4.5 고가/저가 인덱스 함수

```python
def 고가인덱스():
    """데이터 구간 내 최고가 시점의 인덱스"""
    high_index = np.argmax(
        self.dict_arry[self.indexn+1-데이터길이:self.indexn+1, fi('현재가')]
    )
    high_index = self.indexn - 데이터길이 + high_index + 1
    return self.dict_arry[high_index, 0]  # 시간 인덱스 반환

def 저가인덱스():
    """데이터 구간 내 최저가 시점의 인덱스"""
    low_index = np.argmin(
        self.dict_arry[self.indexn+1-데이터길이:self.indexn+1, fi('현재가')]
    )
    low_index = self.indexn - 데이터길이 + low_index + 1
    return self.dict_arry[low_index, 0]  # 시간 인덱스 반환

def 고가갱신():
    """현재 틱이 고가 갱신 시점인지"""
    return self.indexn == 고가인덱스()

def 저가갱신():
    """현재 틱이 저가 갱신 시점인지"""
    return self.indexn == 저가인덱스()

def 고가미갱신지속시간():
    """고가 이후 경과 시간(초)"""
    return int(
        (dt_ymdhms(self.index) - dt_ymdhms(str(고가인덱스()))).total_seconds()
    )

def 저가미갱신지속시간():
    """저가 이후 경과 시간(초)"""
    return int(
        (dt_ymdhms(self.index) - dt_ymdhms(str(저가인덱스()))).total_seconds()
    )
```

---

## 5. 함수별 상세 분석

### 5.1 파라미터 체계 분석

전체 함수 라이브러리에서 사용되는 파라미터 유형은 5가지로 정리됩니다.

| 파라미터 유형 | 변수명 | 의미 | 대표 기본값 |
|:------------:|:------:|:----:|:----------:|
| **구간 길이** | `tick`, `tick1`, `tick2` | 분석 대상 틱 수 | 5, 10, 20, 30 |
| **임계 비율** | `per`, `per1`, `per2` | 판정 기준 퍼센트(%) | 0.3, 0.5, 0.75, 1.0 |
| **배수** | `multi`, `multiple`, `ratio` | 배수/비율 기준 | 2, 3 |
| **오프셋** | `pre` | 과거 시점 이동(틱) | 0 |
| **시간** | `time_` | 보유시간 기준(초) | 600 |

### 5.2 데이터 접근 패턴

함수들의 내부 데이터 접근 방식은 두 가지로 구분됩니다.

**패턴 A: numpy 배열 직접 접근**
```python
# self.arry_data 또는 self.dict_arry 사용
closes = self.arry_data[self.indexn+1-tick:self.indexn+1, 1]
```
- `이평60근접개수`, `변동성`, `횡보감지` 등 구간 연산이 필요한 함수
- 성능이 중요한 기초 메트릭 함수에서 사용

**패턴 B: STOM 내장 변수/함수 참조**
```python
# STOM 시스템 변수 직접 참조
drop_rate = (현재가 / 현재가N(tick) - 1) * 100
```
- `급락감지`, `이평60이탈` 등 단순 비교 함수
- STOM 조건식 문법과의 호환성을 유지하는 함수에서 사용

### 5.3 반환값 체계

| 반환 유형 | 함수 수 | 대표 함수 |
|:---------:|:------:|----------|
| **float** (수치) | 7개 | `변동성()`, `구간저가대비현재가등락율()` |
| **int** (정수) | 1개 | `이평근접개수()` |
| **bool** (참/거짓) | 30+개 | `변동성급증()`, `횡보감지()`, `급락감지()` |
| **datetime index** | 2개 | `고가인덱스()`, `저가인덱스()` |
| **int** (초) | 2개 | `고가미갱신지속시간()`, `저가미갱신지속시간()` |

---

## 6. 기능별 분류 체계

### 6.1 전체 함수 맵

```
STOM 유틸리티 함수 라이브러리
├── A. 기초 메트릭 (7개) ─── 수치 반환
│   ├── 변동성(tick, pre)
│   ├── 이평근접개수(window, tick, per)
│   ├── 구간저가대비현재가등락율(tick, pre)
│   ├── 거래대금평균대비비율(tick, pre)
│   ├── 체결강도평균대비비율(tick, pre)
│   ├── 호가총잔량비율(tick, pre)
│   └── 횡보감지(tick, per, pre) [수치 버전]
│
├── B. 단일 상태 감지 (19개) ─── Boolean 반환
│   ├── 변동성: 변동성급증, 변동성급감
│   ├── 가격: 가격급등, 가격급락
│   ├── 거래대금: 거래대금급증, 거래대금급감
│   ├── 체결강도: 체결강도급등, 체결강도급락
│   ├── 호가: 호가상승압력, 호가하락압력, 호가갭발생
│   ├── 수량: 매수수량급증, 매수수량급감, 매도수량급증, 매도수량급감
│   ├── 추세: 연속상승, 연속하락
│   ├── 이동평균: 이평이탈
│   └── 횡보: 횡보감지 [Boolean 버전]
│
├── C. 복합 패턴 감지 (11개) ─── Boolean 반환
│   ├── 횡보 기반: 횡보후급등, 횡보후연속상승, 횡보후급락, 횡보후연속하락
│   ├── 연속 추세: 연속상승및급등, 연속하락및급락
│   ├── 이동평균: 이평지지후급등
│   ├── 변동성: 변동성급증후수익률상승, 변동성급증후수익률하락
│   └── 장기보유: 횡보상태장기보유
│
├── D. 동적 청산 (3개) ─── Boolean 반환
│   ├── 변동성기반_동적익절청산
│   ├── 변동성기반_동적손절청산
│   └── 변동성기반_장기보유종목_동적익절청산
│
└── E. 고가/저가 인덱스 (6개) ─── 혼합 반환
    ├── 고가인덱스, 저가인덱스
    ├── 고가갱신, 저가갱신
    └── 고가미갱신지속시간, 저가미갱신지속시간
```

### 6.2 매도 시나리오별 함수 매핑

| 매도 시나리오 | 적합 함수 조합 |
|:-------------|:-------------|
| **급락 손절** | `가격급락()` or `변동성기반_동적손절청산()` |
| **이평선 이탈** | `이평이탈()` and `체결강도급락()` |
| **횡보 이탈** | `횡보후급락()` or `횡보상태장기보유()` |
| **과열 후 반전** | `연속상승및급등()` and `매도수량급증()` |
| **거래량 감소** | `거래대금급감()` and `호가하락압력()` |
| **트레일링 스톱** | `변동성기반_동적익절청산()` |
| **변동성 폭발** | `변동성급증후수익률하락()` |
| **호가 이상** | `호가갭발생()` and `매도수량급증()` |

---

## 7. STOM 기존 전략과의 비교 분석

### 7.1 기존 STOM 매도 전략 구조 (제5회 STOMING DAY)

```python
# 기존 방식: 시가총액 구간별 분기 + 등락율각도 + 수급 + 가격변화율
elif 시가총액 < 1500:
    if 20 <= 등락율각도(30) and \
       (초당매도수량 - 초당매수수량) >= 매수총잔량 * 30/100 and \
       (현재가 / 현재가N(1) - 1) * 10000 <= -50:
        매도 = True
    elif 10 <= 등락율각도(30) < 20 and \
         (초당매도수량 - 초당매수수량) >= 매수총잔량 * 90/100 and \
         (현재가 / 현재가N(1) - 1) * 10000 <= -75:
        매도 = True
    # ... 6개 elif 분기
```

### 7.2 유틸리티 함수 적용 시 동일 로직

```python
# 유틸리티 함수 방식: 의미 단위 조합
if 가격급락(1, 0.5) and 매도수량급증(30, multi=3) and 호가하락압력(30, 0.3):
    매도 = True
elif 변동성급증(5) and 연속하락(3):
    매도 = True
elif 변동성기반_동적손절청산(30, multi=2):
    매도 = True
```

### 7.3 비교 분석표

| 비교 항목 | 기존 STOM 방식 | 유틸리티 함수 방식 |
|:---------:|:-------------:|:-----------------:|
| **코드 라인 수** | 60~100줄 | 10~20줄 |
| **가독성** | 낮음 (숫자 나열) | 높음 (의미 명확) |
| **수정 용이성** | 낮음 (연쇄 수정) | 높음 (함수 교체) |
| **파라미터 최적화** | 개별 수치 조정 | 함수 파라미터 조정 |
| **전략 프로토타이핑** | 느림 | 빠름 |
| **시가총액 분기** | 직접 구현 | 별도 래퍼 필요 |
| **실행 성능** | 빠름 (인라인) | 약간 느림 (함수 호출) |
| **STOM 호환성** | 완전 호환 | 커스텀 등록 필요 |
| **재현성** | 낮음 | 높음 |
| **테스트 용이성** | 어려움 | 개별 함수 단위 테스트 |

### 7.4 기존 19개 전략의 매도 핵심 패턴과 매핑

기존 전략 분석에서 도출된 매도 변수 빈도 Top 10을 유틸리티 함수에 매핑하면:

| 순위 | 기존 매도 변수 | 빈도 | 매핑 가능 함수 |
|:----:|:-------------|:----:|:-------------|
| 1 | 현재가 | 19/19 | `가격급등()`, `가격급락()`, `이평이탈()` |
| 2 | 체결강도 | 18/19 | `체결강도급등()`, `체결강도급락()` |
| 3 | 시가총액 | 17/19 | (별도 래퍼 구현 필요) |
| 4 | 체결강도N(1) | 16/19 | `체결강도평균대비비율()` |
| 5 | 이동평균(60) | 16/19 | `이평이탈()`, `이평근접개수()` |
| 6 | 수익률 | 16/19 | `변동성기반_동적손절청산()`, `변동성기반_동적익절청산()` |
| 7 | 최고수익률 | 16/19 | `변동성기반_동적익절청산()` (트레일링 확장) |
| 8 | 매수시간 | 15/19 | `횡보상태장기보유()` |
| 9 | 체결강도평균(30) | 15/19 | `체결강도평균대비비율()` |
| 10 | 등락율 | 13/19 | `가격급등()`, `가격급락()` |

**커버리지**: 상위 10개 매도 변수 중 8개(80%)를 유틸리티 함수로 표현 가능. 시가총액 분기와 최고수익률 기반 트레일링만 추가 구현 필요.

---

## 8. 조합 전략 설계 가이드

### 8.1 SoulsnoW 제안 조합 예시

```python
# 원본 예시
횡보감지(20) and 급락감지(3, 0.5)
```

이 조합의 의미: "최근 20틱 동안 가격이 횡보하다가 직전 3틱 사이에 0.5% 이상 급락하면 매도"

### 8.2 권장 조합 전략

#### 전략 A: 보수적 손절 (리스크 관리 우선)

```python
# 변동성 적응형 손절 + 이동평균 확인
if 변동성기반_동적손절청산(30, multi=2):
    매도 = True
elif 이평이탈(60, per=1.5) and 체결강도급락(30, ratio=0.85):
    매도 = True
elif 가격급락(1, per=1.5):  # 1틱만에 1.5% 급락 (긴급 손절)
    매도 = True
```

#### 전략 B: 수익 실현 (트레일링 스톱)

```python
# 변동성 적응형 익절 + 과열 감지
if 변동성기반_동적익절청산(30, multi=4):
    매도 = True
elif 연속상승및급등(5, tick2=2, per=1.0) and 매도수량급증(10, multi=3):
    매도 = True  # 과열 후 매도세 유입
elif 변동성기반_장기보유종목_동적익절청산(30, time_=600, minper=0.3):
    매도 = True  # 장기 보유 시 낮은 기준 익절
```

#### 전략 C: 횡보 탈출

```python
# 횡보 구간 감지 → 방향 전환 시 매도
if 횡보후급락(20, per1=0.5, tick2=3, per2=0.5):
    매도 = True
elif 횡보상태장기보유(30, time_=300):
    매도 = True  # 5분 이상 횡보 시 타임아웃
elif 횡보후연속하락(15, per1=0.5, tick2=3):
    매도 = True
```

#### 전략 D: 종합 매도전략 (19개 전략 종합 대체)

```python
# ============================
# 1단계: 긴급 청산
# ============================
if 등락율 > 29.5:
    매도 = True

# ============================
# 2단계: 동적 손절
# ============================
elif 변동성기반_동적손절청산(30, multi=2):
    매도 = True

# ============================
# 3단계: 동적 익절
# ============================
elif 변동성기반_동적익절청산(30, multi=4):
    매도 = True

# ============================
# 4단계: 패턴 기반 매도
# ============================
elif 횡보후급락(20, per1=0.5, tick2=3, per2=0.5):
    매도 = True
elif 연속하락및급락(3, tick2=2, per=0.5):
    매도 = True
elif 변동성급증후수익률하락(5, multi=2):
    매도 = True

# ============================
# 5단계: 추세 전환 감지
# ============================
elif 이평이탈(60, per=1.0) and 체결강도급락(30, ratio=0.9):
    매도 = True
elif 호가하락압력(30, ratio=0.33) and 매도수량급증(10, multi=3):
    매도 = True

# ============================
# 6단계: 장기보유 타임아웃
# ============================
elif 횡보상태장기보유(30, time_=420):
    매도 = True
elif 변동성기반_장기보유종목_동적익절청산(30, time_=600, minper=0.3):
    매도 = True
```

### 8.3 조합 파라미터 최적화 가이드

| 함수 | 파라미터 | 보수적 | 균형적 | 공격적 |
|:-----|:--------|:------:|:------:|:------:|
| `변동성기반_동적손절청산` | multi | 3 | 2 | 1.5 |
| `변동성기반_동적익절청산` | multi | 5 | 4 | 3 |
| `횡보감지` | tick / per | 30 / 0.3 | 20 / 0.5 | 10 / 0.7 |
| `가격급락` | tick / per | 3 / 1.0 | 2 / 0.5 | 1 / 0.3 |
| `이평이탈` | per | 2.0 | 1.0 | 0.5 |
| `거래대금급감` | ratio | 0.5 | 0.75 | 0.9 |
| `횡보상태장기보유` | time_ | 600초 | 420초 | 300초 |

---

## 9. STOM 시스템 통합 방안

### 9.1 현재 호환성 이슈

| 이슈 | 상세 | 해결 방안 |
|:-----|:-----|:---------|
| **클래스 메서드 참조** | `self.arry_data`, `self.indexn` 등 직접 접근 | STOM 엔진 클래스에 메서드로 등록 |
| **CheckFactor 검증** | 커스텀 함수는 `back_code_test.py` 검증 미통과 | 화이트리스트에 함수명 등록 |
| **조건식 문법** | `if not ... 매수 = False` 패턴과 상이 | 매도 조건(`if ... 매도 = True`)은 호환 |
| **self.vars 최적화** | 함수 파라미터를 vars에 매핑하는 방법 필요 | 함수 파라미터를 `self.vars[n]`으로 치환 |

### 9.2 통합 구현 방향

```python
# STOM 엔진 클래스에 유틸리티 메서드 추가
class StomBacktestEngine:
    # ... 기존 코드 ...

    # ===== 유틸리티 함수 라이브러리 =====
    def 변동성(self, tick, pre=0):
        closes = self.arry_data[self.indexn+1-tick-pre:self.indexn+1-pre, 1]
        return np.std(closes) / np.mean(closes) * 100

    def 횡보감지(self, tick, per=0.5):
        return self.변동성(tick) <= per

    def 급락감지(self, tick, per=0.3):
        drop_rate = (현재가 / 현재가N(tick) - 1) * 100
        return drop_rate <= -per

    # ... 나머지 함수들 ...
```

### 9.3 self.vars 파라미터 매핑 예시

```python
# 유틸리티 함수의 파라미터를 self.vars로 최적화
self.vars[25] = [[-3.0, -1.0, 0.5], -2.0]  # 동적손절 base_per
self.vars[26] = [[10, 30, 5], 20]           # 횡보감지 tick
self.vars[27] = [[0.3, 0.7, 0.1], 0.5]     # 횡보감지 per
self.vars[28] = [[2, 5, 1], 3]             # 급락감지 tick
self.vars[29] = [[0.3, 1.0, 0.1], 0.5]     # 급락감지 per

# 조건식에서 사용
if 횡보감지(self.vars[26], self.vars[27]) and 급락감지(self.vars[28], self.vars[29]):
    매도 = True
```

---

## 10. 결론 및 권장사항

### 10.1 핵심 평가

SoulsnoW가 공유한 유틸리티 함수 라이브러리는 STOM 매도 전략 개발의 **패러다임 전환**을 제안합니다. 기존의 숫자 나열식 조건문에서 의미 기반 함수 조합으로의 전환은 전략의 가독성, 재현성, 최적화 효율성을 크게 향상시킵니다.

### 10.2 강점

- **46개 이상의 함수**가 5개 카테고리로 체계적으로 분류됨
- 기초 메트릭 → 단일 감지 → 복합 패턴 → 동적 청산의 **계층 구조**가 명확
- `and`/`or` 조합만으로 수백 가지 매도 전략 생성 가능
- 변동성 적응형 동적 청산 함수가 기존 고정 손절/익절의 한계를 극복

### 10.3 보완 필요 사항

- 시가총액 기반 분기 로직이 함수 레벨에 없음 (래퍼 함수 필요)
- 최고수익률 기반 트레일링 스톱 함수 부재
- STOM `back_code_test.py` 검증과의 호환성 확보 필요
- `pre` 파라미터를 활용한 매수 시점 vs 현재 시점 비교 패턴의 문서화 필요

### 10.4 다음 단계 권장

1. 유틸리티 함수를 STOM 엔진 클래스에 메서드로 통합
2. `self.vars` 매핑을 통한 파라미터 최적화 프레임워크 구축
3. 기존 19개 우수 전략의 매도 로직을 유틸리티 함수 조합으로 재구성
4. 조합 전략 백테스트 수행 및 성과 비교 분석
5. 시가총액 분기 래퍼 및 트레일링 스톱 함수 추가 개발

---

## 부록: 함수 Quick Reference

### A. 수치 반환 함수

| 함수명 | 시그니처 | 반환 | 설명 |
|:-------|:---------|:----:|:-----|
| 변동성 | `(tick, pre=0)` | float | 구간 변동계수(%) |
| 이평근접개수 | `(window, tick=30, per=0.33)` | int | 이평 밀착 틱 수 |
| 구간저가대비현재가등락율 | `(tick, pre=0)` | float | 구간 저점 대비 등락율(%) |
| 거래대금평균대비비율 | `(tick, pre=0)` | float | 평균 대비 비율 |
| 체결강도평균대비비율 | `(tick, pre=0)` | float | 평균 대비 비율 |
| 호가총잔량비율 | `(tick, pre=0)` | float | 매수/매도 잔량 비율 |
| 횡보감지 (수치) | `(tick, per=0.5, pre=0)` | float | 변동계수(%) |

### B. Boolean 반환 함수

| 함수명 | 시그니처 | 설명 |
|:-------|:---------|:-----|
| 변동성급증 | `(tick, multi=2)` | 변동성 multi배 이상 증가 |
| 변동성급감 | `(tick, multi=2)` | 변동성 1/multi 이하 감소 |
| 가격급등 | `(tick, per=0.75)` | per% 이상 상승 |
| 가격급락 | `(tick, per=0.75)` | per% 이상 하락 |
| 거래대금급증 | `(tick, ratio=3)` | 평균의 ratio배 이상 |
| 거래대금급감 | `(tick, ratio=0.75)` | 평균의 ratio배 이하 |
| 체결강도급등 | `(tick, ratio=1.1)` | 평균의 ratio배 이상 |
| 체결강도급락 | `(tick, ratio=0.9)` | 평균의 ratio배 이하 |
| 호가상승압력 | `(tick, ratio=0.66)` | 매수잔량 우위 |
| 호가하락압력 | `(tick, ratio=0.33)` | 매도잔량 우위 |
| 호가갭발생 | `(hogagap, pre=0)` | 스프레드 이상 |
| 매수수량급증 | `(tick, multi=3, pre=0)` | 매수수량 multi배 이상 |
| 매수수량급감 | `(tick, multi=3, pre=0)` | 매수수량 1/multi 이하 |
| 매도수량급증 | `(tick, multi=3, pre=0)` | 매도수량 multi배 이상 |
| 매도수량급감 | `(tick, multi=3, pre=0)` | 매도수량 1/multi 이하 |
| 연속상승 | `(tick)` | tick틱 연속 상승 |
| 연속하락 | `(tick)` | tick틱 연속 하락 |
| 이평이탈 | `(window, per=1.0)` | 이평선 하방 per% 이탈 |
| 횡보후급등 | `(tick1, per1=0.5, tick2=2, per2=0.5)` | 횡보 → 급등 |
| 횡보후연속상승 | `(tick1, per1=0.5, tick2=3)` | 횡보 → 연속상승 |
| 횡보후급락 | `(tick1, per1=0.5, tick2=2, per2=0.5)` | 횡보 → 급락 |
| 횡보후연속하락 | `(tick1, per1=0.5, tick2=3)` | 횡보 → 연속하락 |
| 연속상승및급등 | `(tick1, tick2=2, per=0.5)` | 연속상승 + 급등 |
| 연속하락및급락 | `(tick1, tick2=2, per=0.5)` | 연속하락 + 급락 |
| 이평지지후급등 | `(window, tick=30, per1=0.33, cnt=10, per2=1.0)` | 이평 지지 → 급등 |
| 변동성급증후수익률상승 | `(tick, multi=2)` | 변동성↑ + 수익률↑ |
| 변동성급증후수익률하락 | `(tick, multi=2)` | 변동성↑ + 수익률↓ |
| 횡보상태장기보유 | `(tick, time_=600)` | 횡보 + 장기보유 |
| 변동성기반_동적익절청산 | `(tick, multi=4)` | 변동성 적응 익절 |
| 변동성기반_동적손절청산 | `(tick, multi=2)` | 변동성 적응 손절 |
| 변동성기반_장기보유종목_동적익절청산 | `(tick, time_=600, minper=0.3, multi=1)` | 장기보유 적응 익절 |

### C. 인덱스/시간 반환 함수

| 함수명 | 시그니처 | 반환 | 설명 |
|:-------|:---------|:----:|:-----|
| 고가인덱스 | `()` | index | 구간 최고가 시점 |
| 저가인덱스 | `()` | index | 구간 최저가 시점 |
| 고가갱신 | `()` | bool | 현재 = 고가 시점 |
| 저가갱신 | `()` | bool | 현재 = 저가 시점 |
| 고가미갱신지속시간 | `()` | int(초) | 고가 이후 경과(초) |
| 저가미갱신지속시간 | `()` | int(초) | 저가 이후 경과(초) |

---

**문서 끝**

> 본 보고서는 STOMER 커뮤니티에서 공유된 코드를 분석한 것으로, 추론으로 완성된 부분이 포함되어 있습니다.  
> 실제 구현 시 STOM 엔진 소스코드와의 정합성 검증이 필요합니다.
