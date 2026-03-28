# 2026-03-28 wt-lab 홈탭 크롤링 통합 전환 작업 계획서

## 목적

이 문서는 `research/init` 워크트리(`STOM_V.wt-lab`)에서
홈탭 크롤링 구조를 추후 안전하게 통합형 구조로 전환하기 위한 **작업 계획서**다.

현재 `wt-lab`은 즉시 실행이 깨진 상태는 아니지만,
`wt-2u` / `wt-dev`와 달리 아직 **구형 분리형 홈탭 크롤링 구조**를 유지하고 있다.
따라서 다음 동기화 작업에서 단순히 파일 하나만 지우거나 import 한 줄만 제거하면,
오히려 `wt-2u`에서 발생했던 것과 같은 깨진 상태가 만들어질 수 있다.

이 문서의 목표는 다음과 같다.

1. 현재 `wt-lab`이 왜 즉시 수정 대상이 아닌지 설명한다.
2. 추후 구조 통합이 필요할 때 어떤 파일을 어떤 순서로 바꿔야 하는지 기록한다.
3. 다음 세션에서 바로 이어서 작업할 수 있도록 검증 기준과 주의사항을 남긴다.

---

## 현재 상태 요약

### 현재 `wt-lab` 구조

| 항목 | 현재 상태 | 의미 |
|---|---|---|
| `utility/webcrawling_homtab.py` | 존재 | 홈탭 전용 크롤링 모듈이 아직 살아 있음 |
| `ui/ui_mainwindow.py` | `from utility.webcrawling_homtab import *` 유지 | 현재 구조와 일치 |
| `ui/ui_mainwindow.py` | `proc_webc_home = Process(target=WebCrawingHomTab, ...)` 유지 | 전용 홈탭 프로세스 사용 중 |
| `utility/webcrawling.py` | 통합형 홈탭 크롤링 구조 아님 | `wt-2u`/`wt-dev`와 구조가 다름 |
| `utility/lazy_imports.py` | 존재 | 현재 브랜치 의존성과 일치 |

### 현재 판단

> `wt-lab`은 **지금 당장 같은 패치를 적용하면 안 되는 브랜치**다.

이유는 간단하다.

- `wt-2u` / `wt-dev`는 `webcrawling_homtab.py`가 이미 삭제된 상태라 stale reference 제거가 필요했다.
- `wt-lab`은 그 파일이 아직 실제로 존재하고, 현재 구조가 그 파일에 의존하고 있다.
- 따라서 `wt-2u`에서 했던 패치를 그대로 적용하면 `wt-lab`이 오히려 깨진다.

---

## 기준 비교: 왜 `wt-lab`은 바로 안 건드리는가

| 구분 | `wt-2u` / `wt-dev` | `wt-lab` |
|---|---|---|
| `utility/webcrawling_homtab.py` | 삭제됨 | 존재함 |
| `ui_mainwindow.py`의 import | 남아 있어서 stale reference | 실제 파일을 참조 중 |
| `proc_webc_home` | stale process | 실제 구조 일부 |
| `utility/webcrawling.py` | 홈탭 통합 로직 이미 포함 | 아직 통합 전 |
| 조치 방식 | stale reference 제거 | 지금은 보류, 나중에 세트 전환 |

즉, `wt-lab`은 **삭제된 파일을 참조하는 상태가 아니라, 아직 구형 구조를 유지하는 상태**다.
따라서 지금 필요한 것은 “즉시 수정”이 아니라 “전환 계획”이다.

---

## 실제 전환이 필요해지는 시점

다음 중 하나가 발생하면 `wt-lab`도 통합 전환을 검토해야 한다.

1. `wt-2u` 또는 `wt-dev`의 웹크롤링 통합 구조를 `wt-lab`에 반영해야 할 때
2. 홈탭 크롤링 관련 버그 수정이 `utility/webcrawling.py` 통합 경로로만 제공될 때
3. `webcrawling_homtab.py`와 `webcrawling.py`의 중복 유지 비용이 커질 때
4. 리서치 브랜치도 장기적으로 2U 계열 공통 런타임 구조를 따라가야 할 때

---

## 전환 작업의 기본 원칙

### 절대 금지

다음은 **단독으로 적용하면 안 된다**.

- `utility/webcrawling_homtab.py`만 삭제
- `ui/ui_mainwindow.py`의 `webcrawling_homtab` import만 제거
- `proc_webc_home` 생성/시작 코드만 제거

이 셋 중 하나라도 단독 반영하면,
현재 `wt-lab`은 홈탭 데이터 공급 경로를 잃고 즉시 비정상 상태가 될 수 있다.

### 반드시 세트로 움직여야 하는 단위

1. `utility/webcrawling.py`
2. `utility/webcrawling_homtab.py`
3. `ui/ui_mainwindow.py`

---

## 권장 작업 순서 (다음 세션용 실행 계획)

### 0단계. 작업 시작 전 확인

작업 시작 전에 반드시 다음을 먼저 확인한다.

- `wt-lab`의 현재 로컬 변경사항 중 `utility/webcrawling_homtab.py`가 이미 수정되어 있는지
- 그 수정이 실험 목적의 유효한 변경인지, 임시 변경인지
- `wt-2u` / `wt-dev`의 최신 `utility/webcrawling.py`가 기준 버전으로 사용 가능한지

권장 명령:

```bash
git --git-dir=/mnt/c/System_Trading/STOM/STOM_V/.git/worktrees/STOM_V.wt-lab \
    --work-tree=/mnt/c/System_Trading/STOM/STOM_V.wt-lab status --short -- \
    utility/webcrawling.py utility/webcrawling_homtab.py ui/ui_mainwindow.py
```

---

### 1단계. 기준 소스 확보

우선 `wt-2u` 또는 `wt-dev`의 통합형 `utility/webcrawling.py`를 기준으로 잡는다.

우선순위:
1. `wt-dev` 최신 안정 버전
2. `wt-2u` 최신 안정 버전

이때 아래 항목이 실제로 들어 있는지 확인한다.

- `CrawlingHomTapData()`
- `get_korean_stocks()`
- `get_market_indicator()`
- `get_crypto_data()`
- `windowQ.put((ui_num['홈차트'], ...))`

---

### 2단계. `utility/webcrawling.py` 통합 반영

`wt-lab/utility/webcrawling.py`를 통합형 구조로 교체 또는 수동 병합한다.

이 단계의 목표는:

- 홈탭 데이터가 더 이상 `webcrawling_homtab.py` 없이도
- `WebCrawling` 메인 경로에서 생성/전송되도록 만드는 것

#### 확인 포인트

| 확인 항목 | 기대 상태 |
|---|---|
| 홈탭 크롤링 함수 존재 | 있어야 함 |
| `ui_num['홈차트']` 전송 | 있어야 함 |
| 메인 루프에서 주기 실행 | 있어야 함 |
| 리서치 브랜치 고유 로직 충돌 | 없어야 함 |

---

### 3단계. `ui/ui_mainwindow.py` 정리

`utility/webcrawling.py` 통합이 먼저 반영된 뒤에만 진행한다.

수정 항목:

1. `from utility.webcrawling_homtab import *` 제거
2. `self.proc_webc_home = Process(target=WebCrawingHomTab, ...)` 제거
3. `self.proc_webc_home.start()` 제거

#### 주의

이 단계는 반드시 2단계 이후에만 수행한다.

---

### 4단계. `utility/webcrawling_homtab.py` 처리

`ui_mainwindow.py`와 `webcrawling.py`가 통합형 구조로 정리된 뒤,
그때 `webcrawling_homtab.py`를 삭제할지 결정한다.

판단 기준:

| 조건 | 조치 |
|---|---|
| 파일 기능이 완전히 `webcrawling.py`로 흡수됨 | 삭제 |
| 리서치 실험 코드 일부가 여전히 직접 사용 | 임시 유지 + TODO 주석/문서화 |
| 구조 전환 검증 전 | 삭제 금지 |

권장 방향은 **최종적으로 삭제**지만,
실험 브랜치 특성상 즉시 삭제보다 검증 후 삭제가 안전하다.

---

### 5단계. 검증

#### 정적 검증

```bash
rg -n "webcrawling_homtab|WebCrawingHomTab|proc_webc_home" ui/ui_mainwindow.py
```

기대 결과:
- 출력 없음

#### 런타임 검증

```bash
cmd.exe /c "cd /d C:\System_Trading\STOM\STOM_V.wt-lab && python stom.py"
```

확인 포인트:
- 시작 직후 모듈 누락 예외가 없어야 함
- 프로세스가 최소 짧은 관찰 시간 동안 유지되어야 함
- 홈탭 데이터가 실제로 갱신되는지 수동 확인 필요

#### 추가 검증

- 홈탭 UI 업데이트 신호가 정상 수신되는지
- `windowQ`를 통한 `ui_num['홈차트']` 데이터가 실제 들어오는지
- 리서치 브랜치 고유 실험 흐름과 충돌이 없는지

---

## 커밋 전략

리서치 워크트리에서는 다음처럼 **분리 커밋**하는 것을 권장한다.

### 커밋 1: 계획/준비
- 문서
- 조사 결과
- 근거 기록

### 커밋 2: 구조 전환
- `utility/webcrawling.py`
- `ui/ui_mainwindow.py`
- 필요 시 `utility/webcrawling_homtab.py`

### 커밋 3: 검증/후속 정리
- 검증 결과 문서
- 남은 TODO 정리

즉, 코드 전환과 문서를 한 번에 섞지 말고,
**계획 → 전환 → 검증** 순으로 나누는 것이 안전하다.

---

## 다음 세션에서 바로 할 일 체크리스트

- [ ] `wt-lab`의 현재 `utility/webcrawling_homtab.py` 로컬 수정 내용 확인
- [ ] `wt-dev` 또는 `wt-2u`의 통합형 `utility/webcrawling.py`를 기준 소스로 선택
- [ ] `wt-lab/utility/webcrawling.py`에 홈탭 통합 반영
- [ ] 이후에만 `ui/ui_mainwindow.py` stale reference 제거
- [ ] 검증 후 `webcrawling_homtab.py` 삭제 여부 결정
- [ ] `python stom.py` 실행 및 홈탭 수동 확인

---

## 이번 세션 기준 기록

이번 세션에서는 **코드 수정 없이 계획만 커밋**한다.

그 이유는 다음과 같다.

1. `wt-lab`은 현재 구조상 즉시 깨진 상태가 아님
2. 부분 수정은 오히려 런타임을 깨뜨릴 수 있음
3. 현재 `utility/webcrawling_homtab.py`에 로컬 수정 흔적이 있어 선행 확인이 필요함
4. 따라서 먼저 계획과 판단 기준을 남기고, 다음 세션에서 안전하게 이어가는 편이 맞다

---

## 한 줄 결론

> `wt-lab`은 지금 당장 `wt-2u` 방식 패치를 적용할 브랜치가 아니라,
> **통합형 `webcrawling.py` 반영 → `ui_mainwindow.py` 정리 → `webcrawling_homtab.py` 처리**를
> 반드시 한 세트로 수행해야 하는 차기 전환 대상이다.
