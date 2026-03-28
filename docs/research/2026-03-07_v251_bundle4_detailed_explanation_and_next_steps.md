# 묶음 4 상세 설명 및 다음 단계 안내

- 작성일: 2026-03-07
- 대상 브랜치: `STOM_Version_2U-cli-research-v251`
- 관련 커밋: `1a1d561` (`docs: 묶음 4 - shipped CLI 범위 및 library-only 모듈 정합화`)

---

## 1. 묶음 4의 핵심 목적

묶음 4는 기능을 더 많이 추가하는 단계가 아니라,
이미 구현된 `cli/` 하위 코드 중에서 무엇이 **공식 shipped CLI** 이고,
무엇이 아직 **library-only / Python API / 연구용 모듈** 인지를 명확히 정리하는 단계였다.

즉, 묶음 4의 역할은 다음 네 가지를 일치시키는 것이다.

1. 실제 구현된 코드
2. 현재 사용자가 명령줄에서 접근 가능한 기능
3. help / 진입점 / 사용자 문서에 설명되는 기능
4. shipped 범위로 간주되는 제품 기능

---

## 2. 왜 묶음 4가 필요했는가

`cli/` 디렉터리에는 다음과 같은 모듈들이 이미 구현되어 있었다.

- `cli/history.py`
- `cli/sweep.py`
- `cli/optimizer.py`
- `cli/ai_controller.py`
- `cli/data_bridge.py`
- `cli/report.py`
- `cli/monitor.py`
- `cli/engine_tuner.py`
- `cli/strategy_generator.py`

그러나 실제 공식 진입점은 당시 기준으로 사실상 아래뿐이었다.

- `stom_backtest.py` 기본 백테스트 실행
- `formula` 서브커맨드
- `strategy` 서브커맨드

이 상태를 그대로 두면:

- 사용자 입장에서는 “구현된 모듈 = 공식 CLI 기능”으로 오해할 수 있고,
- 개발자 입장에서는 public interface 와 internal helper 의 경계가 흐려지고,
- 리뷰어 입장에서는 브랜치 완성도를 과대평가할 위험이 있었다.

묶음 4는 이 불일치를 제거하고, shipped 범위를 명시적으로 고정하는 작업이었다.

---

## 3. 묶음 4에서 실제로 바뀐 것

### 3.1 `stom_backtest.py` 설명 정리

`stom_backtest.py` 최상단 설명을 정리하여,
이 파일이 현재 공식적으로 제공하는 것은 아래 두 가지임을 명시했다.

- 기본 백테스트 실행
- `formula` / `strategy` 서브커맨드

그리고 그 외 `cli/` 하위 모듈은 현재 시점에서는
공식 서브커맨드가 아니라 library-only 성격임을 설명했다.

**효과:**
엔트리포인트 파일만 봐도 shipped 범위를 오해하지 않게 되었다.

---

### 3.2 `cli/config.py` help / epilog 정리

`--help` 출력에 아래 정보를 추가했다.

#### 공식 CLI 범위
- 기본 백테스트 실행
- `formula`
- `strategy`

#### 라이브러리 전용 (현재 help 미노출)
- `history`
- `sweep`
- `optimizer`
- `ai_controller`
- `data_bridge`
- `report`
- `engine_tuner`
- `monitor`
- `strategy_generator`

**효과:**
사용자는 `--help` 만 봐도 지금 공식적으로 노출된 기능과,
아직 내부 모듈인 기능을 구분할 수 있다.

---

### 3.3 module docstring 정리

다음 파일들에 “현재 shipped CLI 서브커맨드가 아니라 Python API / library-only 성격”임을 명시했다.

- `cli/ai_controller.py`
- `cli/strategy_generator.py`
- `cli/data_bridge.py`
- `cli/history.py`
- `cli/optimizer.py`
- `cli/report.py`
- `cli/monitor.py`

**효과:**
파일을 직접 여는 개발자나 리뷰어가
이 모듈을 public CLI contract 로 착각하지 않게 되었다.

---

### 3.4 `docs/STOM_CLI_AI_AUTOMATION_PLAN.md` 현실화

이 문서의 “현재 상태” 표현을 정리했다.

기존에는 구현된 모듈이 많아 보이면서,
마치 모두가 제품 수준의 CLI 기능처럼 읽힐 수 있었다.

묶음 4 이후에는:

- **공식 CLI로 이미 제공되는 것**
- **library-only / 내부 모듈인 것**

이 둘을 구분해서 서술하게 만들었다.

**효과:**
문서가 제품 범위를 과장하지 않게 되었다.

---

### 3.5 신규 문서: shipped scope 선언

추가 문서:

- `docs/research/2026-03-07_v251_cli_shipping_scope.md`

이 문서에서 다음을 고정했다.

#### 공식 shipped CLI
- 기본 백테스트 실행
- `formula` / `strategy`

#### library-only 모듈
- `history`
- `sweep`
- `optimizer`
- `ai_controller`
- `data_bridge`
- `report`
- `engine_tuner`
- `monitor`

#### 생성/실험 성격 모듈
- `strategy_generator`

그리고 운영 원칙도 함께 정리했다.

예를 들어:
- 문서에서 “CLI 기능 구현 완료”라고 말할 때는 공식 shipped 범위만 기준으로 삼는다.
- library-only 모듈은 help / entrypoint / smoke test 없이 공식 CLI로 간주하지 않는다.
- 나중에 공식 CLI로 승격할 기능은 subcommand 연결, 테스트, 사용 예시까지 갖춰야 한다.

---

## 4. 묶음 4가 해결한 문제

### 4.1 구현 파일 수와 shipped 기능 수의 혼동 제거
`cli/` 아래 파일 수가 많다는 이유만으로 “CLI 완성”처럼 보이던 문제를 줄였다.

### 4.2 리뷰 기준 명확화
이제 리뷰할 때는:
- 공식 CLI
- library-only 모듈
- 실험/보류 기능
을 구분해서 판단할 수 있다.

### 4.3 향후 승격 작업의 기준점 확보
앞으로 `history`, `sweep`, `optimizer`, `ai_controller` 등을 공식 CLI로 승격할 때,
현재 상태를 baseline 으로 삼을 수 있게 되었다.

---

## 5. 묶음 4가 일부러 하지 않은 것

묶음 4는 범위 정리 단계였지,
아래 기능을 강제로 CLI 제품 범위로 올린 단계는 아니다.

- `history` 공식 서브커맨드화
- `sweep` 공식 서브커맨드화
- `optimizer` 공식 서브커맨드화
- `ai_controller` CLI 노출
- `strategy_generator` 공식 기능 승격

즉, “문서와 shipped 범위를 맞춘 것”이지,
“기능 범위를 확장한 것”은 아니다.

---

## 6. 묶음 4 이후 현재 상태의 의미

현재 브랜치는 다음과 같이 해석하는 것이 정확하다.

### 공식 CLI
- 기본 백테스트 실행
- `formula`
- `strategy`

### 구현되었지만 library-only
- `history`
- `sweep`
- `optimizer`
- `ai_controller`
- `data_bridge`
- `report`
- `engine_tuner`
- `monitor`
- `strategy_generator`

즉, “코드가 존재한다”와 “현재 제품으로 출하되는 CLI다”를 분리해서 관리하게 된 상태다.

---

## 7. 다음 단계 안내

이제 선택지는 크게 3가지다.

### A. 릴리스/병합 준비 단계로 이동 (추천)

현재 상태는:
- bundle 1~4 완료
- `python3 scripts/pre_commit_check.py` 통과
- `python3 scripts/run_tests.py --all` 통과
- architect verification `APPROVE`

이므로, 가장 안전한 다음 단계는 **릴리스 마감 단계**다.

권장 작업:
1. PR 본문 정리
2. release checklist 정리
3. CLI 환경 문서 또는 `requirements-cli.txt` 정리
4. 브랜치 push / 병합 준비

---

### B. library-only 기능을 공식 CLI로 승격

다음 승격 후보 우선순위는 아래를 권장한다.

1. `history`
2. `sweep`
3. `optimizer`
4. `report`
5. `engine_tuner`
6. `ai_controller`

이 경로는 기능 확장 효과가 크지만,
이번 단계처럼 문서 정리가 아니라 실제 제품 범위 확장이므로
subcommand 설계와 테스트까지 함께 따라붙어야 한다.

---

### C. `strategy_generator` 정식화 여부 결정

현재 `strategy_generator` 는 구현은 되어 있지만,
공식 shipped CLI 기능으로 올릴지 여부를 신중히 결정해야 한다.

선택지:
- 정식 전략 템플릿으로 강화해 공식 기능으로 승격
- 또는 experimental / library-only 로 유지

현재로서는 두 번째가 더 안전하다.

---

## 8. 추천 실행 순서

가장 현실적인 다음 순서는 아래와 같다.

### 1순위
- PR 본문 초안 작성
- release checklist 작성
- push / merge 준비

### 2순위
- `history` / `sweep` / `optimizer` 를 공식 CLI로 승격하는 별도 라운드 시작

### 3순위
- `ai_controller` / `strategy_generator` 재설계 또는 정식화

---

## 9. 결론

묶음 4는 단순 문서 작업이 아니라,
**이 브랜치에서 무엇이 실제 CLI 제품 범위인지 확정한 단계**다.

이 작업 덕분에:
- help 출력,
- 엔트리포인트 설명,
- 모듈 docstring,
- 계획 문서,
- shipped scope 문서

가 같은 그림을 보게 되었고,
향후 확장 작업도 “무엇을 승격하는지”가 분명해졌다.
