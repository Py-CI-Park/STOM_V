# 2026-03-28 STOM_V 계열 워크트리 동기화 누락 분석 및 작업 안내

## 문서 목적

이 문서는 `STOM_Version_2` 공식 브랜치는 정상 실행되지만, `STOM_Version_2U` 계열 워크트리에서
실행 오류가 발생하는 원인을 **pyd 직접 분석 없이** 추론 기반으로 정리한 작업 문서다.

핵심 목적은 다음과 같다.

1. `wt-2u`, `wt-dev`, `wt-lab`의 현재 동기화 상태를 비교한다.
2. `ui_mainwindow.pyd`를 직접 볼 수 없는 상황에서도, **삭제/추가 파일 이력 + import 관계 + 프로세스 생성 흐름**으로
   누락된 반영 사항을 추론하는 방법을 기록한다.
3. 각 워크트리별로 **즉시 수정해야 할 항목**, **보류해야 할 항목**, **차기 sync 시 함께 반영해야 할 항목**을
   작업표 수준으로 정리한다.

---

## 결론 요약

현재 확인된 가장 큰 실행 장애는 `wt-2u`와 `wt-dev`에서 동일하게 존재한다.

- `ui/ui_mainwindow.py`는 아직 `utility.webcrawling_homtab`를 import 하고 있음
- 그러나 해당 파일은 이미 브랜치 HEAD에서 삭제되어 있음
- 결과적으로 `stom.py` 실행 직후 `ModuleNotFoundError` 발생

반면 `wt-lab`은 아직 `utility/webcrawling_homtab.py` 파일이 실제로 존재하므로,
같은 형태의 즉시 크래시는 발생하지 않는다. 다만 구조적으로는 **구버전 분리형 홈탭 크롤링 구조**를 유지 중이므로,
향후 `wt-2u`/`wt-dev` 방식의 웹크롤링 통합을 가져올 때는 **파일 삭제 + import 제거 + 프로세스 제거**를
반드시 한 세트로 맞춰야 한다.

추가 분석 결과, `wt-2u`에는 `utility.lazy_imports.py` 삭제 이후에도 `research/*` 영역에서 해당 모듈을
계속 import 하는 **2차 동기화 누락**도 존재한다. 이 문제는 현재 `stom.py` 기본 기동과 직접 연결되지는 않지만,
추후 연구/분석 스크립트 실행 시 별도 오류를 유발할 가능성이 높다.

---

## 분석 방법 (pyd를 보지 않고도 추론하는 절차)

`ui_mainwindow.pyd`를 직접 열 수 없으므로, 아래 절차로 누락 여부를 판별했다.

### 1. 현재 런타임 에러에서 직접 단서 확보

실행 중 실제로 발생한 에러:

```text
ModuleNotFoundError: No module named 'utility.webcrawling_homtab'
```

이 에러는 단순히 파일이 없다는 의미를 넘어, **`ui_mainwindow.py`가 아직 옛 구조를 참조한다**는 단서를 준다.

### 2. 참조가 남아 있는지 확인

`wt-2u/ui/ui_mainwindow.py` 확인 결과:

- `81행`: `from utility.webcrawling_homtab import *`
- `555~556행`: `Process(target=WebCrawingHomTab, ...)`

동일 패턴은 `wt-dev`에도 존재한다.

### 3. 파일이 실제로 존재하는지 확인

파일 존재 여부:

- `wt-2u/utility/webcrawling_homtab.py` → 없음
- `wt-dev/utility/webcrawling_homtab.py` → 없음
- `wt-lab/utility/webcrawling_homtab.py` → 있음

즉, `wt-2u`, `wt-dev`는 **삭제된 파일을 계속 import** 중이다.

### 4. 대체 구현이 이미 다른 파일에 들어갔는지 확인

`wt-2u/utility/webcrawling.py`를 보면 이미 아래 기능이 들어 있다.

- `CrawlingHomTapData()`
- `get_korean_stocks()`
- `get_market_indicator()`
- `get_crypto_data()`
- `self.windowQ.put((ui_num['홈차트'], self.dict_data))`

또한 `ui_mainwindow.py`는 이미 별도 프로세스로 다음을 시작한다.

```python
self.proc_webc = Process(target=WebCrawling, args=(self.qlist,), daemon=True)
self.proc_webc.start()
```

즉, 홈탭 크롤링 로직은 이미 `utility/webcrawling.py` 쪽으로 **통합되었는데**,
예전 전용 프로세스 `WebCrawingHomTab` 관련 참조만 제거되지 않은 상태다.

### 5. 삭제 이력과 현재 참조를 결합해 누락 판단

브랜치 이력 확인 결과:

- `wt-2u`: `256fa95` (`STOM V2.65`)에서 `utility/webcrawling_homtab.py` 삭제
- `wt-dev`: `94aea66` (`STOM V2.65`)에서 `utility/webcrawling_homtab.py` 삭제

그러나 현재 HEAD의 `ui/ui_mainwindow.py`에는 import / process 시작 코드가 그대로 남아 있다.

이 조합은 다음을 의미한다.

> **파일 삭제는 반영되었지만, 해당 파일을 참조하던 `ui_mainwindow.py` 정리는 누락되었다.**

이것이 이번 실행 오류의 직접 원인이다.

---

## 워크트리별 상태 요약 테이블

| 워크트리 | 브랜치 | 현재 실행 상태 | 핵심 누락/상태 | 우선순위 | 처리 방향 |
|---|---|---|---|---:|---|
| `STOM_V.wt-2u` | `STOM_Version_2U` | **실행 불가** | `utility.webcrawling_homtab` 삭제 후 import/process 참조 잔존 | **긴급** | 즉시 수정 필요 |
| `STOM_V.wt-dev` | `STOM_Version_2U_C_CLI_v267` | **동일 오류 가능성 매우 높음** | `wt-2u`와 동일한 stale import/process 참조 | **긴급** | `wt-2u`와 동일 패치 필요 |
| `STOM_V.wt-lab` | `research/init` | **즉시 크래시는 아님** | 아직 `webcrawling_homtab.py` 파일이 살아 있는 구형 분리 구조 | 중간 | 지금은 보류, 차기 sync 시 세트 반영 |
| `STOM_V.wt-2u` 부가 영역 | `STOM_Version_2U` | 기본 GUI 기동과 직접 무관 | `utility.lazy_imports.py` 삭제 후 `research/*` import 잔존 28건 | 중간 | 별도 정리 작업 필요 |
| `STOM_V` | `STOM_Version_2` | 정상 | `ui_mainwindow.pyd` 기준 동작 | 참고용 | 수정 대상 아님 |

---

## 이력 기반 증거 테이블

| 구분 | 워크트리 | 증거 | 의미 |
|---|---|---|---|
| 홈탭 전용 모듈 삭제 | `wt-2u` | `256fa95` (`STOM V2.65`)에서 `utility/webcrawling_homtab.py` 삭제 | 파일 삭제는 반영됨 |
| 홈탭 전용 모듈 삭제 | `wt-dev` | `94aea66` (`STOM V2.65`)에서 `utility/webcrawling_homtab.py` 삭제 | CLI 브랜치도 동일하게 삭제 반영됨 |
| stale import 잔존 | `wt-2u` | `ui/ui_mainwindow.py:81` | 삭제된 모듈을 아직 import 중 |
| stale import 잔존 | `wt-dev` | `ui/ui_mainwindow.py:81` | 동일 stale import 존재 |
| stale process 잔존 | `wt-2u` | `ui/ui_mainwindow.py:555~556` | `WebCrawingHomTab` 프로세스를 아직 시작하려 함 |
| stale process 잔존 | `wt-dev` | `ui/ui_mainwindow.py:555~556` | 동일 stale process 존재 |
| 대체 구현 존재 | `wt-2u` | `utility/webcrawling.py` 내 `CrawlingHomTapData()` / `ui_num['홈차트']` 전송 | 홈탭 로직이 이미 통합되어 있음 |
| 대체 구현 존재 | `wt-dev` | `utility/webcrawling.py` 구조 동일 | `wt-2u`와 같은 방식으로 정리 가능 |
| 구형 구조 유지 | `wt-lab` | `utility/webcrawling_homtab.py` 실제 존재 | 지금은 삭제하면 안 되는 구조 |
| 2차 누락 후보 | `wt-2u` | `utility.lazy_imports.py` 삭제 후 AST scan 기준 28개 import 잔존 | 별도 후속 sync 누락 가능성 높음 |

---

## 권장 작업 단위(커밋 단위) 테이블

| 순서 | 워크트리 | 커밋 단위 | 포함 파일 | 포함하지 말아야 할 것 |
|---|---|---|---|---|
| 1 | `wt-2u` | 런타임 복구 커밋 | `ui/ui_mainwindow.py` | `research/*`, `utility/lazy_imports.py` 관련 정리 |
| 2 | `wt-dev` | 런타임 복구 커밋 | `ui/ui_mainwindow.py` | CLI 기능 변경, 테스트 정리, 다른 문서 수정 |
| 3 | `wt-2u` | 후속 정리 커밋 | `research/*` + 필요 시 `utility/lazy_imports.py` | GUI 런타임 복구와 섞지 않기 |
| 4 | `wt-lab` | 차기 sync 시 세트 커밋 | `utility/webcrawling.py`, `utility/webcrawling_homtab.py`, `ui/ui_mainwindow.py` | 일부 파일만 단독 반영 금지 |

---

## 세부 작업표

### A. `STOM_V.wt-2u` 작업표

#### A-1. 즉시 수정 항목 (필수)

| 파일 | 위치 | 현재 문제 | 수정 내용 | 기대 효과 |
|---|---|---|---|---|
| `ui/ui_mainwindow.py` | import 구간 | `from utility.webcrawling_homtab import *` 잔존 | 해당 import 제거 | 시작 직후 `ModuleNotFoundError` 제거 |
| `ui/ui_mainwindow.py` | 프로세스 시작 구간 | `self.proc_webc_home = Process(target=WebCrawingHomTab, ...)` 잔존 | `proc_webc_home` 생성 제거 | 삭제된 클래스 참조 제거 |
| `ui/ui_mainwindow.py` | 프로세스 시작 구간 | `self.proc_webc_home.start()` 잔존 | start 호출 제거 | 중복/불능 프로세스 제거 |

#### A-2. 수정 판단 근거

- 이미 `self.proc_webc = Process(target=WebCrawling, ...)`가 존재함
- `utility/webcrawling.py` 내부에 홈탭 크롤링 기능이 이미 통합되어 있음
- 따라서 `WebCrawingHomTab` 전용 프로세스는 **이제 존재할 이유가 없음**

#### A-3. 추가 점검 항목 (2차)

| 파일군 | 현재 문제 | 영향도 | 권장 방향 |
|---|---|---:|---|
| `research/*` | `utility.lazy_imports` import 28건 잔존 | 중간 | 2U 정책에 맞게 직접 import 방식으로 정리하거나, 필요 시 lazy_imports 복원 여부 별도 결정 |
| `utility/lazy_imports.py` | HEAD에서 삭제됨 | 중간 | 기본 GUI 기동과 직접 무관. research 정리 전까지 후순위 |

#### A-4. 작업 순서

1. `ui/ui_mainwindow.py` stale import 제거
2. `proc_webc_home` 생성/시작 제거
3. `stom.bat` 또는 `python stom.py`로 재기동 확인
4. 그 다음 `utility.lazy_imports` 관련 secondary audit 진행

---

### B. `STOM_V.wt-dev` 작업표

#### B-1. 즉시 수정 항목 (필수)

| 파일 | 위치 | 현재 문제 | 수정 내용 | 기대 효과 |
|---|---|---|---|---|
| `ui/ui_mainwindow.py` | import 구간 | `from utility.webcrawling_homtab import *` 잔존 | 해당 import 제거 | 2U_C/CLI 브랜치의 동일 실행 장애 예방 |
| `ui/ui_mainwindow.py` | 프로세스 시작 구간 | `proc_webc_home = Process(target=WebCrawingHomTab, ...)` 잔존 | 생성 제거 | 삭제된 모듈 참조 제거 |
| `ui/ui_mainwindow.py` | 프로세스 시작 구간 | `proc_webc_home.start()` 잔존 | start 제거 | 이중 홈크롤링 경로 제거 |

#### B-2. 수정 판단 근거

- `wt-dev`에서도 `utility/webcrawling_homtab.py`는 HEAD에 없음
- `ui/ui_mainwindow.py`에는 동일 참조가 남아 있음
- `utility/webcrawling.py`는 `wt-2u`와 같은 통합 구조를 이미 가지고 있음

#### B-3. 주의사항

`wt-dev`는 AGENTS 상 `utility/lazy_imports.py`를 **의도적으로 복원 유지**하는 브랜치다.
따라서 `wt-2u`와 달리 `lazy_imports`는 여기서 문제로 간주하지 않는다.

---

### C. `STOM_V.wt-lab` 작업표

#### C-1. 현재 상태

| 항목 | 상태 |
|---|---|
| `utility/webcrawling_homtab.py` | 존재 |
| `ui/ui_mainwindow.py`의 `webcrawling_homtab` import | 존재 |
| `proc_webc_home` 생성/시작 | 존재 |
| `utility/webcrawling.py` | 아직 홈탭 통합 구조 아님 |

즉, `wt-lab`은 현재 **구형 분리형 구조가 자체적으로는 일관적**이다.

#### C-2. 당장 하지 말아야 할 것

`wt-lab`에서 지금 바로 다음 작업을 하면 안 된다.

- `webcrawling_homtab.py`만 삭제
- `ui_mainwindow.py`의 import만 제거
- `proc_webc_home`만 제거

이렇게 일부만 반영하면 `wt-lab`도 `wt-2u`와 똑같은 깨진 상태가 된다.

#### C-3. 차기 sync 시 필요한 세트 작업

| 단계 | 작업 내용 | 함께 반영해야 하는 이유 |
|---|---|---|
| 1 | `utility/webcrawling.py`를 통합형 버전으로 업데이트 | 홈탭 데이터를 이쪽에서 처리해야 함 |
| 2 | `utility/webcrawling_homtab.py` 삭제 여부 결정 | 통합 후 전용 모듈 불필요 |
| 3 | `ui/ui_mainwindow.py`에서 `webcrawling_homtab` import 제거 | 삭제 모듈 참조 제거 |
| 4 | `proc_webc_home` 생성/시작 제거 | 통합 후 중복 프로세스 제거 |
| 5 | 홈탭 데이터 수신이 `proc_webc` 경로에서 정상 동작하는지 확인 | 통합 완료 검증 |

#### C-4. 현재 권장 결론

- `wt-lab`은 **지금 즉시 수정 대상은 아님**
- 다만 문서상 **“향후 sync 시 반드시 세트 반영”** 대상으로 관리해야 함

---

## 추가 분석: 업데이트에 놓친 부분 후보

### 1. `utility.webcrawling_homtab` 누락

#### 현재 판정
- `wt-2u`: **확정 누락 / 실행 장애 발생 중**
- `wt-dev`: **확정 누락 / 동일 오류 가능성 매우 높음**
- `wt-lab`: 누락 아님 (현재 구조상 파일 존재)

#### 이유
삭제 커밋은 반영됐지만, 참조 제거가 누락되었다.

---

### 2. `utility.lazy_imports` 누락 (`wt-2u`만)

#### 현재 판정
- `wt-2u`: **확정 누락 후보**
- `wt-dev`: 아님 (의도적으로 파일 유지)
- `wt-lab`: 아님 (파일 존재)

#### 근거
AST 기반 local import 검사 결과, `wt-2u`에서 아래 missing local import가 확인됐다.

- `utility.webcrawling_homtab` → 1건
- `utility.lazy_imports` → 28건

#### 영향 범위
- 기본 `stom.py` GUI 기동: 직접 영향 낮음
- `research/*`, `analyzer/*`, `deeplearning/*`, test 실행: 영향 높음

#### 권장 방안
- 2U 브랜치의 정책이 “지연로딩 삭제 유지”라면 `research/*` 쪽 import 정리
- 반대로 연구 코드 활용이 중요하면 `utility/lazy_imports.py` 복원 고려
- 단, 이는 별도 결정이 필요하므로 **1차 런타임 복구 후 후속 작업**으로 처리하는 것이 안전함

---

## 우선순위 기준 작업 안내

### 1순위: 즉시 실행 복구

#### 대상
- `wt-2u`
- `wt-dev`

#### 해야 할 일
- `ui/ui_mainwindow.py`에서 `webcrawling_homtab` 관련 import / process 제거

#### 완료 기준
- `stom.py` 시작 시 `ModuleNotFoundError: utility.webcrawling_homtab`가 더 이상 발생하지 않을 것

---

### 2순위: 2U research 계열 누락 정리

#### 대상
- `wt-2u`

#### 해야 할 일
- `utility.lazy_imports` 의존 파일 목록 분류
- 실제 사용 대상과 보관용 파일 분리
- 필요 시 직접 import로 변환하거나 helper 복원

#### 완료 기준
- `research/*` 주요 실행 경로에서 `ModuleNotFoundError: utility.lazy_imports`가 발생하지 않을 것

---

### 3순위: wt-lab 차기 sync 준비

#### 대상
- `wt-lab`

#### 해야 할 일
- 다음 upstream / 2U_C sync 때 `webcrawling.py` 통합형 반영 여부 먼저 확인
- 통합형이 들어오면 `webcrawling_homtab.py` 제거와 `ui_mainwindow.py` 수정까지 세트로 적용

#### 완료 기준
- `wt-lab`이 구형 분리형 구조를 유지하든, 통합형 구조로 전환하든 **둘 중 하나로 일관성 유지**

---

## 권장 검증 명령어

### A. 즉시 오류 재현/해소 확인

```bash
cmd.exe /c "cd /d C:\System_Trading\STOM\STOM_V.wt-2u && python stom.py"
cmd.exe /c "cd /d C:\System_Trading\STOM\STOM_V.wt-dev && python stom.py"
```

### B. stale import 제거 확인

```bash
rg -n "webcrawling_homtab|WebCrawingHomTab|proc_webc_home" ui/ui_mainwindow.py
```

### C. local missing import 재스캔

AST 기반 missing local import 검사 시,
최소한 아래 항목은 사라져야 한다.

- `utility.webcrawling_homtab` (`wt-2u`, `wt-dev`)

### D. 런처 확인

```bash
cmd.exe /c "cd /d C:\System_Trading\STOM\STOM_V.wt-2u && call stom.bat"
```

기대 결과:
- CMD 창이 유지되어야 함
- 종료 시 원인과 exit code를 확인할 수 있어야 함

---

## 최종 정리

이번 이슈는 단순한 파일 누락이 아니라, 다음과 같은 **동기화 반영 불완전성**의 전형적인 사례다.

1. `webcrawling_homtab.py` 삭제는 반영됨
2. 홈탭 크롤링 통합 로직은 `webcrawling.py`에 이미 들어옴
3. 그러나 `ui_mainwindow.py`의 옛 import / 프로세스 참조는 제거되지 않음
4. 결과적으로 `wt-2u`, `wt-dev`에서 즉시 실행 장애 발생

반면 `wt-lab`은 아직 구형 분리형 구조를 유지하고 있어 현재는 일관적이다.
따라서 `wt-lab`은 **지금 수정할 대상이 아니라**, 차기 sync 시에만 세트 작업으로 다뤄야 한다.

즉, 현재 실무 작업 우선순위는 다음 한 줄로 요약된다.

> **먼저 `wt-2u`, `wt-dev`에서 stale import / stale process를 제거해 실행을 복구하고,
> 그 다음 `wt-2u`의 `lazy_imports` 잔존 의존성을 별도 정리한다. `wt-lab`은 차기 sync 대비 문서 관리 대상으로 둔다.**
