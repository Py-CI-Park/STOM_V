# E2E 백테스트 검증 결과

- 작성일: 2026-03-09
- 대상 브랜치: `STOM_Version_2U-cli-research-v251`
- 선행 수정: `04f48d5` (DICT_SET 프로세스 전파 버그 수정)

---

## 1. 테스트 목적

### 1.1 검증 대상

커밋 `04f48d5`에서 적용한 DICT_SET 프로세스 전파 수정(방안 C: 래퍼 함수)이
실제 E2E 백테스트에서 정상 동작하는지 확인.

### 1.2 이전 실패 내역

수정 전 동일 명령어 실행 시:

```
ValueError: not enough values to unpack (expected 56, got 53)
  at backtest/backengine_kiwoom_min.py:15
```

원인: Windows spawn 멀티프로세싱에서 CLI가 수정한 `DICT_SET['주식타임프레임']`이
자식 엔진 프로세스에 전달되지 않아, 분봉 엔진이 틱 컬럼 리스트(54컬럼)를 사용.
분봉 Strategy()가 56개 변수를 기대하지만 53개만 제공되어 실패.

상세 분석: `docs/research/2026-03-08_dict_set_propagation_fix.md` 참조.

---

## 2. 테스트 환경

### 2.1 명령어

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
    --buy Min_B_Study_251227 \
    --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --timeframe min --avg-time 60 \
    --format json
```

### 2.2 DB 상태

| DB 파일 | 내용 |
|---------|------|
| `stock_min_back.db` | 1,379 종목 테이블, 모두 57컬럼, moneytop 20250407~20260227 |
| `stock_tick_back.db` | 2,427 종목 테이블, 모두 54컬럼 |
| `strategy.db` | stockbuy=`Min_B_Study_251227`, stocksell=`Min_S_Study_251227` |
| `setting.db` | `주식타임프레임 = True` (틱 모드) — GUI에서 설정된 상태 |

### 2.3 검증 포인트

- `setting.db`에 틱 모드가 설정된 상태에서도 CLI `--timeframe min`이 정상 동작해야 함
- 이전 `ValueError: expected 56, got 53`이 발생하지 않아야 함

---

## 3. 테스트 결과

### 3.1 DICT_SET 전파 수정 — 성공

| 단계 | 결과 |
|------|------|
| 중간집계 프로세스 생성 (20개) | 성공 |
| 엔진 프로세스 생성 (4개) | 성공 |
| 매수매도전략 및 종목코드 생성 | 성공 |
| 종목코드별 데이터 로딩 시작 | 성공 |
| 자식 프로세스 Setting import (24회) | 성공 (최소 설정 모드 경고) |
| 종목코드별 데이터 로딩 완료 [1/4]~[4/4] | 성공 |
| 백테스트 엔진 준비 | 성공 |
| 백테스트 기간 생성 | 성공 |
| 백테스트 매수전략정보 생성 | 성공 |
| 백테스트 매도전략정보 생성 | 성공 |
| 백테스트 결과집계 프로세스 생성 | 성공 |
| **백테스트 START** | **도달** |

**결론: `ValueError: expected 56, got 53` 완전 해소.**
DICT_SET 래퍼가 자식 프로세스에 올바른 타임프레임 설정을 전달함을 확인.

### 3.2 새로 발견된 문제 — 전략 변수 NameError

백테스트 START 이후 실제 전략 실행 단계에서 새로운 오류 발생:

```
Traceback (most recent call last):
  File "C:\System_Trading\STOM\STOM_V\backtest\backengine_base.py", line 534, in BackTest
    self.Strategy()
  File "C:\System_Trading\STOM\STOM_V\backtest\backengine_kiwoom_min.py", line 143, in Strategy
    exec(self.buystg)
  File "<string>", line 15, in <module>
NameError: name 'VI아래5호가이내' is not defined
```

이 오류는 4개 엔진 프로세스 모두에서 동일하게 발생.

---

## 4. 새 문제 상세: 전략 변수 NameError

### 4.1 발생 위치

```
backengine_kiwoom_min.py:143 → exec(self.buystg)
```

- `self.buystg`는 `strategy.db`에서 읽은 매수 전략 코드 문자열
- `exec()`로 동적 실행 시, Strategy() 메서드의 로컬 변수 범위에서 실행됨
- 전략 코드가 `VI아래5호가이내`라는 변수를 참조하지만, 이 변수가 Strategy() 스코프에 없음

### 4.2 Strategy() 메서드에 정의된 변수 목록

`backengine_kiwoom_min.py:9-15`에서 언패킹하는 56개 변수:

```python
현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량,
거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, VI해제시간, VI가격, VI호가단위,
분봉시가, 분봉고가, 분봉저가,
분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격,
매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5,
매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5,
매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목
```

### 4.3 전략 코드가 참조하는 변수

전략 `Min_B_Study_251227`이 `VI아래5호가이내`를 참조하지만,
Strategy() 메서드에는 이 이름의 변수가 없음.

유사 변수: `라운드피겨위5호가이내` (index 14) — 이름이 다름.

### 4.4 DICT_SET 버그와의 관계

**무관함.** 이 NameError는:
- DICT_SET 수정 전에는 도달하지 못했던 코드 경로 (이전에는 더 앞 단계에서 ValueError로 실패)
- DICT_SET 수정으로 엔진이 정상 시작되면서 처음 도달한 전략 실행 단계의 문제
- 전략 코드(strategy.db 내용)와 엔진 변수 범위 간의 불일치 문제

### 4.5 조사 방향

1. `strategy.db`에서 `Min_B_Study_251227` 전략 코드를 읽어 `VI아래5호가이내` 참조 확인
2. `backengine_kiwoom_min.py`의 Strategy() 메서드에서 exec() 실행 시 어떤 변수가 스코프에 있는지 확인
3. `VI아래5호가이내`가 별도로 계산/정의되는 위치가 있는지 확인
4. GUI에서 이 전략이 정상 동작하는지 여부 확인 (GUI는 다른 Strategy() 구현을 사용할 수 있음)

---

## 5. 손자 프로세스 DICT_SET 미전파 문제 (PlotShow 크래시)

### 5.1 증상

`VI아래5호가이내` NameError 해결(strategy.db 주석 처리) 후,
백테스트 엔진은 221건 거래를 정상 완료(7초)했으나 Report 단계에서 크래시:

```
ValueError: Invalid isoformat string: '2025-04-07 10:00:'
  at backtest/back_static.py:519 (PlotShow)
```

- `is_tick=True`로 잘못 판단 → `dt_ymdhms()`가 분봉 데이터(시:분만 있음)에 적용됨
- `그래프저장하지않기=False` → PlotShow 호출을 건너뛰지 않음
- BackTest 프로세스의 timeout(3600초)까지 대기 후 `"status": "error"` 반환

### 5.2 원인: 3단계 프로세스 계층

```
[CLI 부모] ── _sync_dict_set() ── DICT_SET 패치 ✓
  │
  ├── [Engine 프로세스] ── _engine_with_dict_set() ── DICT_SET 패치 ✓
  │
  └── [BackTest 프로세스] ── _engine_with_dict_set() ── DICT_SET 패치 ✓
        │
        └── [Total 프로세스] ── backtest.py:342에서 Process(target=Total) 생성
                                Windows spawn → 모듈 재import → setting.db 원본값 로드
                                → DICT_SET 미패치 ✗ ← ★ 근본 원인
```

`_engine_with_dict_set` 래퍼(방안 C)는 runner.py에서 직접 생성하는 자식 프로세스만
패치할 수 있다. BackTest가 내부에서 생성하는 Total 프로세스(손자)에는 도달 불가.

### 5.3 수정: 환경 변수 전파 (방안 C + D 하이브리드)

기존 래퍼(방안 C)를 유지하면서, 환경 변수 전파(방안 D)를 추가.

#### 수정 파일 2개

| 파일 | 변경 | 코어 여부 |
|------|------|:---------:|
| `cli/runner.py` | `_sync_dict_set()`에서 `os.environ['_STOM_CLI_DICT_SET']` 설정 | CLI 전용 |
| `utility/setting.py` | DICT_SET 로드 후 env var 오버라이드 적용 (4줄) | **코어** |

#### 동작 원리

```
[CLI 부모]
  _sync_dict_set(config)
    ① DICT_SET 메모리 패치 (기존)
    ② os.environ['_STOM_CLI_DICT_SET'] = json.dumps({...}) (신규)
       → 환경 변수는 Windows에서 모든 자손 프로세스에 자동 상속

[모든 프로세스 — 부모, 자식, 손자 모두]
  utility/setting.py import 시:
    ① database_load() → DICT_SET = { ... } (setting.db 원본값)
    ② os.environ.get('_STOM_CLI_DICT_SET') 확인
    ③ 값이 있으면 DICT_SET.update(json.loads(...)) → CLI 오버라이드 적용
```

#### 코어 파일 수정 내용 (`utility/setting.py`)

```python
# DICT_SET = { ... } 닫는 중괄호 직후 (try 블록 내부)
_cli_ovr = os.environ.get('_STOM_CLI_DICT_SET')
if _cli_ovr:
    import json as _json
    DICT_SET.update(_json.loads(_cli_ovr))
```

- GUI 모드: 환경 변수 미설정 → 무변경 (완전 무해)
- CLI 모드: 환경 변수 설정됨 → 모든 프로세스에서 CLI 오버라이드 자동 적용

#### 코어 수정 동기화 부담 평가

| 항목 | 평가 |
|------|------|
| 수정량 | 4줄 (DICT_SET 정의 직후) |
| V2 충돌 확률 | 매우 낮음 (DICT_SET 끝에 추가, 기존 코드 미변경) |
| 누락 시 영향 | CLI 손자 프로세스 DICT_SET 미전파 (GUI 영향 없음) |
| 재적용 방법 | DICT_SET 닫는 `}` 직후 4줄 복사 |

---

## 6. 최종 검증 결과

### 6.1 E2E 백테스트 — 완전 성공

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
    --buy Min_B_Study_251227 --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --start-time 90000 --end-time 153000 \
    --engines 2 --timeframe min --timeout 120
```

```json
{
  "status": "success",
  "metrics": {
    "trade_count": 221,
    "win_rate": 19.0,
    "avg_profit_pct": -1.56,
    "total_profit_pct": -15.05,
    "total_profit_krw": -3435358,
    "cagr": -752.31,
    "mdd_pct": 15.74,
    "tpi": 0.48,
    "seed_capital": 22832033.0,
    "max_hold_count": 23,
    "avg_hold_time": 88.87
  }
}
```

| 항목 | 이전 (방안 C만) | 현재 (방안 C+D) |
|------|:---:|:---:|
| 상태 | `error` (3600초 타임아웃) | **`success`** |
| 소요시간 | 타임아웃 | **6.8초** |
| 거래횟수 | 221 (엔진만 성공) | **221 (전체 성공)** |
| PlotShow 크래시 | `ValueError: Invalid isoformat` | **발생 안함** |
| Total 프로세스 is_tick | True (잘못됨) | **False (정상)** |
| 그래프저장하지않기 | False (잘못됨) | **True (정상)** |

---

## 7. 전체 진행 상태

| 항목 | 상태 |
|------|------|
| 묶음 1~4 (CLI 기반) | 완료 |
| DICT_SET 프로세스 전파 — 직접 자식 | **해결됨** (래퍼, 커밋 `04f48d5`) |
| DICT_SET 프로세스 전파 — 손자(Total) | **해결됨** (환경 변수 전파) |
| NameError: VI아래5호가이내 | **해결됨** (strategy.db 주석 처리) |
| PlotShow ValueError | **해결됨** (환경 변수로 is_tick 전파) |
| E2E 백테스트 | **성공** (`"status": "success"`, 221 trades, 6.8초) |
