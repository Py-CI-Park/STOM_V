# DICT_SET 프로세스 전파 버그 분석 및 수정

- 작성일: 2026-03-08
- 대상 브랜치: `STOM_Version_2U-cli-research-v251`
- 관련 파일: `cli/runner.py`, `backtest/backengine_base.py`, `utility/setting.py`
- 수정 파일: `cli/runner.py` (코어 파일 수정 없음)

---

## 1. 배경: 무엇을 하려 했는가

묶음 1~4 개발 완료 후, CLI 백테스트의 E2E(End-to-End) 실행 검증을 시도했다.

### 테스트 명령어

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
    --buy Min_B_Study_251227 \
    --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --timeframe min --avg-time 60 \
    --format json
```

### 테스트 조건

- DB: `_database/stock_min_back.db` (1,379 종목 테이블, 모두 57컬럼)
- 전략: `strategy.db`에서 `stockbuy=Min_B_Study_251227`, `stocksell=Min_S_Study_251227`
- 타임프레임: 분봉(min) — `--timeframe min`으로 CLI에서 명시 지정
- GUI의 현재 `setting.db` 설정: `주식타임프레임 = True` (틱 모드)

---

## 2. 발생한 오류

```
ValueError: not enough values to unpack (expected 56, got 53)
```

- 발생 위치: `backtest/backengine_kiwoom_min.py:15`
- Strategy() 메서드가 56개 변수를 언패킹하려 했으나, 배열에서 53개만 제공됨

---

## 3. 원인 분석: 데이터 흐름 추적

### 3.1 정상 동작 (GUI 경로)

GUI에서 분봉 백테스트를 실행하면:

1. 사용자가 UI에서 타임프레임 = 분봉 선택
2. GUI가 `setting.db`의 `stock` 테이블에 `주식타임프레임 = False` 기록
3. `Process()` 로 엔진 생성
4. 자식 프로세스가 `utility/setting.py` import → `setting.db` 읽기
5. `DICT_SET['주식타임프레임'] = False` (분봉) ← 올바른 값
6. `BackEngineBase.__init__` → `self.dict_set = DICT_SET` → 정상 동작

### 3.2 비정상 동작 (CLI 경로) — 버그

CLI에서 `--timeframe min`으로 실행하면:

```
[부모 프로세스]
│
├─ runner.py:121    _sync_dict_set(config)
│   └─ runner.py:87    DICT_SET['주식타임프레임'] = False (분봉)
│                       → 부모 프로세스 메모리에서만 변경
│                       → setting.db에는 기록하지 않음
│
├─ runner.py:170-173   엔진 클래스 선택
│   └─ config.is_tick=False → target = BackEngineKiwoomMin  ← 올바름
│
├─ runner.py:186       DB 선택
│   └─ config.is_tick=False → DB_STOCK_BACK_MIN  ← 올바름
│
├─ runner.py:175-180   Process(target=BackEngineKiwoomMin, args=(...))
│                       → DICT_SET 전달 없음  ← ★ 문제 지점
│
▼
[자식 프로세스] ── Windows spawn ── 모든 모듈 처음부터 재import
│
├─ utility/setting.py:102    database_load() → setting.db 읽기
├─ utility/setting.py:115    DICT_SET = { ... }
├─ utility/setting.py:195    '주식타임프레임': df_s['주식타임프레임'][0]
│                             = True  ← setting.db의 원본값 (GUI가 틱으로 설정해둔 상태)
│
├─ backengine_base.py:32     self.dict_set = DICT_SET  ← 잘못된 값 (틱)
├─ backengine_base.py:108    self.is_tick = self.dict_set['주식타임프레임']
│                             = True  ← 틱으로 오인식
│
├─ backengine_base.py:116    factor_list = list_stock_tick  ← 틱 컬럼 리스트
│                             (list_stock_min이어야 함)
│
├─ backengine_base.py:121    self.base_cnt = self.dict_findex['관심종목'] + 1
│                             = 54  (틱: 관심종목이 index 53)
│                             (분봉이면 57이어야 함: 관심종목이 index 56)
│
▼
backengine_kiwoom_min.py:15
    현재가, 시가, ..., 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
    → self.arry_code[self.indexn, 1:54] = 53개 값
    → 56개 변수에 언패킹 시도
    → ValueError: not enough values to unpack (expected 56, got 53)
```

### 3.3 핵심 원인 요약

| 구분 | GUI | CLI |
|------|-----|-----|
| 설정 변경 방식 | `setting.db`에 직접 기록 | 부모 프로세스 메모리에서만 수정 |
| 자식 프로세스 import 시 | DB에서 올바른 값 읽음 | DB에서 원본값(틱) 읽음 |
| 결과 | 정상 동작 | ValueError |

**근본 원인**: Windows의 `spawn` 멀티프로세싱은 Linux의 `fork`와 달리
부모 메모리를 복사하지 않고 자식이 처음부터 모듈을 재import한다.
CLI의 `_sync_dict_set()`은 부모 메모리만 수정하고 DB에는 쓰지 않으므로,
자식 프로세스는 수정 사항을 알 수 없다.

### 3.4 컬럼 수 차이 상세

| 항목 | 틱 (list_stock_tick) | 분봉 (list_stock_min) | 차이 |
|------|:---:|:---:|:---:|
| 관심종목 위치 (index) | 53 | 56 | +3 |
| base_cnt | 54 | 57 | +3 |
| arry[1:base_cnt] 값 개수 | 53 | 56 | +3 |
| Strategy() 변수 개수 | 53 | 56 | 일치해야 함 |

차이나는 3개 컬럼은 분봉 전용: `분봉시가`(idx 18), `분봉고가`(idx 19), `분봉저가`(idx 20)

---

## 4. 해결책 비교 분석

### 4.1 방안 개요

| 방안 | 핵심 아이디어 | 코어 수정 |
|------|-------------|:---------:|
| A. 파라미터 전달 | `BackEngineBase.__init__`에 `dict_set` 파라미터 추가 | **있음** |
| B. DB 기록 | CLI가 `setting.db`에 직접 기록 (GUI 방식 모방) | 없음 |
| C. 래퍼 함수 | 자식 프로세스 시작 시 래퍼가 DICT_SET 패치 | **없음** |
| D. 환경변수 | `os.environ`으로 설정값 전달 | 있음 |
| E. pickle 파일 | 임시 파일로 DICT_SET 전달 | 없음 |

### 4.2 상세 분석표

#### 수정 범위

| 기준 | A (파라미터) | B (DB 기록) | C (래퍼) | D (환경변수) | E (pickle) |
|------|:-:|:-:|:-:|:-:|:-:|
| 수정 파일 | `backengine_base.py` + `runner.py` | `runner.py` | `runner.py` | `setting.py` + `runner.py` | `runner.py` |
| 코어 수정 파일 수 | **1개** | 0개 | **0개** | **1개** | 0개 |
| 수정 코드량 | ~3줄 | ~30줄 | ~10줄 | ~15줄 | ~25줄 |

#### V2 상류 동기화 영향

| 기준 | A (파라미터) | B (DB 기록) | C (래퍼) | D (환경변수) | E (pickle) |
|------|:-:|:-:|:-:|:-:|:-:|
| V2 업데이트 시 재적용 | 매번 확인 필요 | 불필요 | **불필요** | 매번 확인 필요 | 불필요 |
| 재적용 누락 위험 | 있음 | 없음 | **없음** | 있음 | 없음 |
| 추적 문서 필요 | 필수 | 불필요 | **불필요** | 필수 | 불필요 |

#### 안전성

| 기준 | A (파라미터) | B (DB 기록) | C (래퍼) | D (환경변수) | E (pickle) |
|------|:-:|:-:|:-:|:-:|:-:|
| DB 부작용 | 없음 | **setting.db 수정** | 없음 | 없음 | 없음 |
| 비정상 종료 시 | 안전 | **DB 오염 위험** | 안전 | 안전 | **파일 잔존** |
| 동시 실행 안전 | 안전 | **경합 위험** | 안전 | 안전 | **경합 가능** |
| GUI 영향 | 없음 | **잠재적 충돌** | 없음 | `setting.py` 변경 | 없음 |

#### 구현 품질

| 기준 | A (파라미터) | B (DB 기록) | C (래퍼) | D (환경변수) | E (pickle) |
|------|:-:|:-:|:-:|:-:|:-:|
| 명시성 | 높음 | 중간 | 중간 | 낮음 | 낮음 |
| 디버깅 용이성 | 높음 | 중간 | 중간 | 낮음 | 낮음 |
| DICT_SET 외 전역변수 | DICT_SET만 | 모든 DB 설정 | **모든 DICT_SET 키** | 키마다 추가 필요 | 가능 |
| 구현 복잡도 | 매우 낮음 | 높음 | 낮음 | 중간 | 높음 |

### 4.3 종합 점수 (5점 만점, 가중 평가)

| 평가 항목 (가중치) | A | B | C | D | E |
|------|:-:|:-:|:-:|:-:|:-:|
| V2 동기화 부담 (30%) | 3 | 5 | **5** | 3 | 5 |
| 안전성 (25%) | 5 | 2 | **5** | 4 | 3 |
| 구현 간결성 (15%) | 5 | 2 | **4** | 3 | 2 |
| 명시성/디버깅 (10%) | 5 | 3 | **4** | 2 | 2 |
| 호환성 (10%) | 5 | 3 | **5** | 3 | 4 |
| 확장성 (10%) | 4 | 5 | **5** | 2 | 4 |
| **가중 합계** | **4.15** | **3.15** | **4.75** | **2.95** | **3.55** |

### 4.4 각 방안 상세

#### 방안 A: 파라미터 전달

`BackEngineBase.__init__`에 `dict_set=None` 파라미터를 추가하고,
`runner.py`에서 `Process(kwargs={'dict_set': dict(DICT_SET)})`로 전달.

```python
# backengine_base.py line 20 (코어 수정)
def __init__(self, ..., profile=False, dict_set=None):
# backengine_base.py line 32 (코어 수정)
    self.dict_set = dict_set if dict_set is not None else DICT_SET
```

- 장점: 명시적, 깔끔, 최소 변경량
- **단점: `backengine_base.py`(코어)를 수정해야 함 → V2 동기화 시 매번 재적용 필요**
- `dict_set=None` 폴백으로 GUI 호환성은 유지됨

#### 방안 B: DB 기록 (GUI 방식 모방)

CLI가 `setting.db`에 직접 값을 기록하고, 완료 후 원본값으로 복원.

```python
# runner.py
con.execute("UPDATE stock SET 주식타임프레임 = ? WHERE ...", (config.is_tick,))
```

- 장점: GUI와 동일 방식, 코어 수정 없음
- **단점: DB 부작용(오염 위험), 복원 실패 시 setting.db 손상, 동시 실행 불가**
- 비정상 종료(kill, 정전) 시 DB가 오염된 상태로 남을 수 있음

#### 방안 C: 래퍼 함수 (채택)

`runner.py`에 래퍼 함수를 추가하여, 자식 프로세스 시작 시
엔진 생성 전에 DICT_SET을 올바른 값으로 패치.

```python
# runner.py (CLI 전용 파일)
def _engine_with_dict_set(engine_cls, dict_set_override, *args):
    from utility.setting import DICT_SET
    DICT_SET.update(dict_set_override)
    engine_cls(*args)
```

- 장점: **코어 수정 없음**, DB 부작용 없음, 모든 DICT_SET 키 해결
- 단점: 래퍼 간접층 추가 (스택 트레이스 1층 증가)
- Windows spawn의 프로세스 격리로 `DICT_SET.update()`는 해당 자식에만 영향

#### 방안 D: 환경변수

`os.environ`에 설정값 저장, `setting.py`에서 환경변수 우선 읽기.

- 장점: 환경변수는 자식에게 자동 상속
- **단점: `setting.py`(코어)를 수정해야 함, 문자열만 전달 가능, 확장성 나쁨**

#### 방안 E: pickle 파일

DICT_SET을 임시 파일로 저장, 자식이 읽어서 패치.

- 장점: 복잡한 데이터 전달 가능
- **단점: 파일 I/O, 정리 필요, 경합 조건, 오버엔지니어링**

---

## 5. 결정: 방안 C (래퍼 함수)

### 5.1 결정 이유

이 브랜치(`STOM_Version_2U`)는 상류 `STOM_Version_2`를 지속적으로 추적하는 브랜치이다.
코어 파일(`backtest/backengine_base.py`, `utility/setting.py` 등)을 수정하면,
V2가 해당 파일을 업데이트할 때마다 수정 사항을 재적용해야 하는 동기화 부담이 발생한다.

방안 C는:

1. **코어 파일 수정 0건** — V2 동기화에 영향 없음
2. **`runner.py`(CLI 전용 파일)만 수정** — V2에 존재하지 않는 파일
3. **안전성 최고** — DB 부작용 없음, 프로세스 격리로 전역 변이 위험 없음
4. **모든 DICT_SET 키 해결** — `update()` 로 전체 딕셔너리 동기화

### 5.2 프로세스 격리 안전성 근거

Windows `spawn` 방식은 `fork`와 달리 완전히 새로운 프로세스를 생성한다.
각 자식 프로세스는 독립된 메모리 공간을 가지므로:

- 자식 내부에서 `DICT_SET.update()`를 해도 부모 프로세스에 영향 없음
- 다른 자식 프로세스에도 영향 없음
- "전역 변이" 우려는 프로세스 격리 환경에서는 해당되지 않음

### 5.3 pickle 직렬화 안전성

Windows `spawn`은 `Process(target=..., args=...)`를 pickle로 직렬화한다.

- `_engine_with_dict_set`: 모듈 최상위 함수 → pickle 가능 ✓
- `dict(DICT_SET)`: 순수 dict (값은 str, bool, int, list) → pickle 가능 ✓
- `target` (엔진 클래스): 모듈 최상위 클래스 → pickle 가능 ✓

### 5.4 방안 A 유보 사유

방안 A는 기술적으로 가장 깔끔하지만, `backengine_base.py`를 수정해야 한다.
현 시점에서 방안 C로 충분히 해결되므로, 코어 수정이 필요한 방안 A는 유보한다.

향후 다른 코어 모듈에서도 동일한 DICT_SET 문제가 발생하여
래퍼만으로 해결이 어려운 경우, 방안 A를 재검토할 수 있다.
그 경우 반드시 코어 수정 추적 문서를 함께 작성해야 한다.

---

## 6. 구현 상세

### 6.1 수정 파일

`cli/runner.py` — 이 파일만 수정 (CLI 전용 파일, V2에 존재하지 않음)

### 6.2 변경 내용

#### 추가: `_engine_with_dict_set` 래퍼 함수

```python
def _engine_with_dict_set(engine_cls, dict_set_override, *args):
    """자식 프로세스 시작 시 DICT_SET을 CLI 값으로 패치한 후 엔진을 생성한다.

    Windows spawn 방식은 자식 프로세스에서 모든 모듈을 재import하므로,
    부모 프로세스의 _sync_dict_set()이 수정한 DICT_SET 값이 자식에게 전달되지 않는다.
    이 래퍼가 엔진 생성자 호출 전에 올바른 DICT_SET 값을 주입한다.

    각 자식 프로세스는 Windows spawn으로 생성된 독립 메모리 공간이므로
    DICT_SET.update()는 해당 프로세스에만 영향을 미치며,
    부모 프로세스나 다른 자식 프로세스에는 전파되지 않는다.

    See: docs/research/2026-03-08_dict_set_propagation_fix.md
    """
    from utility.setting import DICT_SET
    DICT_SET.update(dict_set_override)
    engine_cls(*args)
```

#### 변경: Process 생성부

```python
# 변경 전
proc = Process(
    target=target,
    args=(i, shared_cnt, shared_lock, windowQ, totalQ, backQ, back_eques, back_sques),
    daemon=True
)

# 변경 후
proc = Process(
    target=_engine_with_dict_set,
    args=(target, dict(DICT_SET),
          i, shared_cnt, shared_lock, windowQ, totalQ, backQ, back_eques, back_sques),
    daemon=True
)
```

### 6.3 동작 원리

```
[부모 프로세스]
  _sync_dict_set(config)
    → DICT_SET['주식타임프레임'] = False (분봉)
  dict(DICT_SET)
    → 현재 DICT_SET의 얕은 복사본 생성 (올바른 값 포함)
  Process(target=_engine_with_dict_set, args=(EngineClass, 복사본, ...))
    → pickle 직렬화하여 자식에게 전달

[자식 프로세스]
  _engine_with_dict_set(engine_cls, dict_set_override, *args) 실행
    ① from utility.setting import DICT_SET
       → 자식이 재import한 DICT_SET (setting.db 원본값, 잘못된 값)
    ② DICT_SET.update(dict_set_override)
       → 부모가 보낸 올바른 값으로 덮어쓰기
       → DICT_SET['주식타임프레임'] = False (분봉) ← 올바른 값!
    ③ engine_cls(*args)
       → BackEngineKiwoomMin(i, shared_cnt, ...)
       → BackEngineBase.__init__() → self.dict_set = DICT_SET ← 패치된 올바른 값
       → UpdateSubVars() → self.is_tick = False → list_stock_min → base_cnt = 57
       → Strategy() → arry[1:57] = 56개 값 → 56개 변수 언패킹 성공 ✓
```

### 6.4 BackSubTotal 프로세스는 수정 불필요

```python
# runner.py line 156-159
proc = Process(
    target=BackSubTotal,
    args=(i, totalQ, back_sques, DICT_SET['백테매수시간기준']),
    daemon=True
)
```

`BackSubTotal`에는 `DICT_SET['백테매수시간기준']` 값이 **직접 전달**되고 있다.
이 값은 부모 프로세스에서 `_sync_dict_set()` 적용 후 읽으므로 올바른 값이 전달된다.
따라서 래퍼 적용이 불필요하다.

---

## 7. 검증 계획

### 7.1 단위 테스트

기존 505개 unit test, 11개 integration test가 계속 통과해야 함.

### 7.2 E2E 백테스트 검증

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
    --buy Min_B_Study_251227 \
    --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --timeframe min --avg-time 60 \
    --format json
```

성공 기준:
- `ValueError` 없이 완료
- JSON 출력에 `status: "success"` 또는 유의미한 결과 포함
- `backtest.db`에 결과 기록

### 7.3 설정 독립성 검증

GUI의 `setting.db`에 `주식타임프레임 = True` (틱)이 설정된 상태에서도
CLI `--timeframe min` 이 정상 동작해야 한다.
(수정 전에는 이 조합에서 실패했음)

---

## 8. 향후 고려 사항

### 8.1 방안 A 재검토 시점

다음 상황이 발생하면 방안 A(코어 수정)를 재검토한다:

- `BackEngineBase` 이외의 코어 모듈에서도 DICT_SET 전파 문제 발생
- 래퍼 방식으로는 해결할 수 없는 모듈 초기화 순서 문제 발생
- V2 상류에서 `backengine_base.py`에 `dict_set` 파라미터를 추가하는 변경이 발생

### 8.2 코어 수정이 필요해질 경우

방안 A를 적용할 때는 반드시 아래 사항을 기록해야 한다:

1. 수정한 코어 파일 목록
2. 각 파일의 정확한 수정 위치와 내용
3. V2 동기화 시 재적용 방법
4. 재적용하지 않으면 어떤 문제가 발생하는지

이 정보는 별도의 `docs/research/cli_core_patches.md` 문서로 관리한다.

### 8.3 다른 전역변수 점검

현재 `DICT_SET` 외에 `setting.py`에서 모듈 레벨로 정의되는 전역변수
(예: `DB_STOCK_BACK_TICK`, `list_stock_min`, `indicator` 등)는
CLI에서 동적으로 수정하지 않으므로, 동일한 문제가 발생하지 않는다.

향후 CLI에서 다른 전역변수를 동적으로 수정해야 하는 경우,
동일한 래퍼 패턴으로 `dict_set_override`에 추가 정보를 포함시킬 수 있다.

---

## 9. 참고: 컬럼 리스트 상세

### list_stock_tick (utility/setting.py)

총 72항목, `관심종목`은 index 53, base_cnt = 54

```
[0]  현재가
[1]  시가
...
[17] VI호가단위
     (분봉시가, 분봉고가, 분봉저가 없음)
[18] 초당거래대금
...
[53] 관심종목  ← base_cnt = 54
[54] 최고현재가
...
```

### list_stock_min (utility/setting.py)

총 77항목 (list_stock_min_base 77 + list_indicator 28), `관심종목`은 index 56, base_cnt = 57

```
[0]  현재가
[1]  시가
...
[17] VI호가단위
[18] 분봉시가    ← 분봉 전용
[19] 분봉고가    ← 분봉 전용
[20] 분봉저가    ← 분봉 전용
[21] 분당거래대금
...
[56] 관심종목  ← base_cnt = 57
[57] 최고현재가
...
```

차이: index 18~20의 3개 분봉 전용 컬럼으로 인해 이후 모든 인덱스가 3씩 밀림.
