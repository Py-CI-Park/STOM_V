# STOM 자동 조건식 탐색 시스템 — Strict 기준 / CLI 정리 우선 계획

- 작성일: 2026-03-13
- 브랜치: `research/auto-condition-validation-pilot`
- 작성 목적:
  1. 현재 확보한 promoted 성공 baseline을 **strict 기준**과 **relaxed 기준**으로 명확히 구분한다.
  2. 현재 내부 API 중심으로 성공한 경로를 **공식 CLI 관점에서 재현 가능하게 정리**한다.
  3. 이후 `analyzer.py`, `ml_factor_model.py` 테스트 보강으로 넘어가기 전에,
     성공 경로의 의미와 사용 기준을 표준화한다.
- 기준 문서:
  - `docs/research/2026-03-13_auto_condition_discovery_generalization_verification.md`
  - `docs/research/2026-03-13_auto_condition_discovery_execution_master_checklist.md`
  - `docs/research/2026-03-11_auto_condition_validation_pilot_execution.md`
  - `docs/research/2026-03-13_auto_condition_discovery_code_review_and_improvement_plan.md`

---

## 1. 왜 지금 이 계획이 필요한가

현재 브랜치는 이미 다음 수준까지 도달했다.

- 자동 조건식 후보 생성
- auto-relax 동작
- no-trade / shared_memory 1차 보강
- 기존 매수 전략 + 자동 필터 결합 구조 확보
- 실제 `promoted=True` 성공 사례 확보
- top_n=1~2 / 일부 multi-round까지 성공 일반화 확인

즉, 이제 더 중요한 질문은

> “분석 엔진을 더 늘릴 것인가?”

보다,

> “지금 성공했다고 말하는 경로가 정확히 어떤 기준에서 성공한 것이며,
>  그 경로를 다른 사람이 공식적으로 재현할 수 있게 정리되었는가?”

이다.

따라서 현재 우선순위는
**analyzer/ml 테스트 보강 전에, strict 기준과 CLI 기준을 먼저 정리하는 것**이 맞다.

---

## 2. 현재 상태에서의 핵심 문제

### 2.1 strict vs relaxed 기준이 섞여 있다

현재 성공 사례 중 일부는 아래 조건에서 나왔다.

- `auto_relax=True`
- `promotion_criteria=None`

이 경우 내부적으로 `min_avg_trade_count`가 완화되어 평가된다.
즉, 문서상 `balanced`로 성공했다고 써도,
그것이 **strict balanced 원형 기준 그대로의 성공**인지 아닌지가 명확하지 않다.

### 2.2 성공 경로가 아직 내부 API 중심이다

현재 성공한 대표 경로는 다음 전제를 가진다.

- `config_dict['base_buy_strategy']` 지정
- 자동 필터를 기존 매수 전략의 최종 `self.Buy()` 직전에 삽입
- `discover_and_promote_strategy()` 사용

하지만 CLI 관점에서 보면 아직 아래가 불명확하다.

- `base_buy_strategy`를 공식적으로 어떤 이름/옵션으로 노출할 것인가
- `auto_relax`를 CLI로 제어할 것인가
- `max_relax_steps`를 CLI에 노출할 것인가
- strict/relaxed 여부를 report에 어떻게 남길 것인가

### 2.3 “성공”의 의미가 문서마다 다르게 읽힐 수 있다

지금 상태로는 아래 표현이 모두 혼동을 만들 수 있다.

- balanced 성공
- multi-round 성공
- promoted 성공

왜냐하면,
- 어느 성공은 strict 기준
- 어느 성공은 relaxed 기준
- 어느 성공은 controller 경로
- 어느 성공은 CLI 기준이 아닌 내부 경로
일 수 있기 때문이다.

즉,
**성공 baseline의 의미를 표준화하지 않으면 이후 테스트 보강도 기준이 흔들린다.**

---

## 3. 이번 계획의 최종 목표

이 계획의 완료 기준은 아래 4가지다.

### 3.1 기준 정리 목표
- [ ] strict / relaxed / exploratory baseline을 명확히 정의한다.
- [ ] `auto_relax=True`일 때 어떤 promotion criteria가 실제로 완화되는지 문서화한다.
- [ ] strict balanced / strict aggressive / relaxed aggressive를 구분하는 표를 만든다.

### 3.2 CLI 정리 목표
- [ ] 성공 경로에서 필요한 핵심 옵션을 CLI 기준으로 정리한다.
- [ ] `base_buy_strategy` 노출 방식 방향을 확정한다.
- [ ] `auto_relax`, `max_relax_steps`를 CLI로 노출할지 결정한다.
- [ ] report에 strict/relaxed 여부를 남기는 규칙을 정리한다.

### 3.3 검증 목표
- [ ] strict balanced 기준 재검증 결과를 확보한다.
- [ ] strict aggressive 기준 재검증 결과를 확보한다.
- [ ] 현재 성공 baseline이 strict인지 relaxed인지 문서로 확정한다.

### 3.4 다음 단계 연결 목표
- [ ] 이 정리 결과를 바탕으로 다음 순서(`analyzer.py`, `ml_factor_model.py` 테스트 보강)를 확정한다.

---

## 4. 기준 용어 정의

문서 전체에서 아래 용어를 일관되게 사용한다.

### 4.1 Strict Baseline
아래를 모두 만족하는 baseline:
- preset 원래 기준을 그대로 사용
- `promotion_criteria` 추가 완화 없음
- auto-relax가 켜져 있더라도 평가 기준이 자동 완화되지 않음

### 4.2 Relaxed Baseline
아래 중 하나 이상이 적용된 baseline:
- `promotion_criteria`로 일부 기준 완화
- `min_avg_trade_count`를 0으로 조정
- multi-round 기준을 줄이거나 완화

### 4.3 Exploratory Baseline
연구/탐색 목적으로만 쓰는 baseline:
- 매우 짧은 구간
- `round_count=1`
- 성공 여부 탐색이 목적
- 실전 채택 기준으로는 바로 사용하지 않음

---

## 5. 현재까지 확보된 baseline의 임시 분류

| baseline | 현재 분류 | 이유 |
|----------|-----------|------|
| top_n=1, aggressive, single-round, `min_rounds=1`, `min_avg_trade_count=0` | Relaxed / Exploratory | 기준 완화가 명시적으로 들어감 |
| top_n=2, aggressive, single-round, `min_rounds=1`, `min_avg_trade_count=0` | Relaxed / Exploratory | top_n 확장 성공이지만 strict 아님 |
| balanced, multi-round, `promotion_criteria=None`, `auto_relax=True` | Relaxed | 내부적으로 avg trade count 완화가 들어감 |

즉 현재는
**성공 baseline은 확보했지만 strict baseline은 아직 확정되지 않은 상태**로 보는 것이 가장 정확하다.

---

## 6. 작업 단계

---

## Step 1. strict / relaxed 기준 표준화 문서 작성

### 목적
성공 결과를 읽는 사람이 오해하지 않도록,
어떤 성공이 strict이고 어떤 성공이 relaxed인지 먼저 고정한다.

### 작업 체크리스트
- [ ] 현재 성공 사례를 전부 표로 재정리
- [ ] 각 사례에 strict / relaxed / exploratory 라벨 부여
- [ ] `promotion_preset`만으로 strict 여부를 판단하지 않는다는 원칙 명시
- [ ] `auto_relax=True` + `promotion_criteria=None` 시 평가 완화 로직 설명

### 산출물
- strict/relaxed 기준 요약 문서 또는 기존 검증 문서 업데이트

### 완료 기준
- [ ] 누가 봐도 성공 사례의 의미를 혼동하지 않는 상태

---

## Step 2. promotion criteria 완화 로직 명문화

### 목적
현재 코드에서 실제로 기준이 어떻게 변하는지 문서와 코드 모두에서 명확히 한다.

### 확인해야 할 것
- [ ] `auto_relax=True`일 때 어떤 criteria가 바뀌는가
- [ ] `promotion_criteria=None`일 때 기본 preset이 어떻게 해석되는가
- [ ] strict 모드와 relaxed 모드를 코드 레벨에서 명시적으로 분리할 필요가 있는가

### 권장 방향
- [ ] relaxed 평가인 경우 report에 `criteria_mode='relaxed'` 같은 표시 추가 검토
- [ ] strict 평가를 강제하는 옵션(`strict_promotion=True` 또는 동등 개념) 필요 여부 검토

### 완료 기준
- [ ] 현재 코드를 읽지 않아도 평가 기준 완화 로직을 문서로 이해 가능

---

## Step 3. CLI 성공 경로 정리

### 목적
내부 controller 성공 경로를 공식 CLI 기준으로 정리한다.

### 핵심 질문
1. `base_buy_strategy`는 CLI에서 어떤 옵션으로 받을 것인가?
2. `auto_relax`는 CLI에서 on/off 할 수 있어야 하는가?
3. `max_relax_steps`를 CLI에서 받게 할 것인가?
4. report에 strict/relaxed 여부를 표시할 것인가?

### 작업 체크리스트
- [ ] 현재 CLI 인자와 성공 경로의 차이 표 작성
- [ ] `discovery promote`에 필요한 추가 옵션 설계
- [ ] backward compatibility 영향 검토
- [ ] CLI help/문서에 baseline 사용 예시 초안 작성

### 최소 정리안
다음 중 하나는 결정해야 한다.

#### 안 A — 공식 CLI 확장
- `--base-buy-strategy`
- `--auto-relax`
- `--max-relax-steps`
- `--strict-promotion`

#### 안 B — controller-only 유지 + 문서 명시
- CLI는 단순 경로 유지
- 성공 baseline은 controller 경로 기준으로 문서화
- CLI 승격은 다음 스프린트로 미룸

### 완료 기준
- [ ] 성공 경로를 CLI 관점에서 설명 가능
- [ ] productization 우선순위가 정리됨

---

## Step 4. strict balanced / strict aggressive 재검증

### 목적
현재 성공 사례가 relaxed인지 strict인지 실제로 검증한다.

### 권장 실험 세트

#### 실험 A — strict aggressive
- [ ] `promotion_preset='aggressive'`
- [ ] `promotion_criteria=None`
- [ ] 내부 완화가 없는지 확인
- [ ] single-round / multi-round 각각 1회 이상 실행

#### 실험 B — strict balanced
- [ ] `promotion_preset='balanced'`
- [ ] `promotion_criteria=None`
- [ ] strict balanced 원래 기준 유지 확인
- [ ] single-round / multi-round 각각 1회 이상 실행

#### 실험 C — relaxed aggressive (기준점)
- [ ] 기존 성공 baseline 재실행
- [ ] strict 결과와 비교표 작성

### 결과 기록 체크리스트
- [ ] promoted 여부
- [ ] round_count
- [ ] mean_oos_metric
- [ ] avg_trade_count
- [ ] zero_trade_rounds
- [ ] strict/relaxed 여부

### 완료 기준
- [ ] strict success / strict fail / relaxed success 구분이 명확해짐

---

## Step 5. baseline 표준안 확정

### 목적
앞으로 문서/코드/CLI에서 “현재 권장 baseline”이 무엇인지 딱 하나 이상 정한다.

### 권장 출력 형태

```markdown
## Current Recommended Baselines

### Baseline A — Relaxed exploratory baseline
- existing buy strategy + auto filter
- top_n=1
- aggressive
- min_rounds=1
- min_avg_trade_count=0

### Baseline B — Strict candidate baseline
- existing buy strategy + auto filter
- top_n=1
- balanced
- no extra relaxation
- multi-round
```

### 완료 기준
- [ ] 연구용 baseline
- [ ] 실전용 baseline 후보
를 분리해서 제시 가능

---

## Step 6. 다음 스프린트 연결

strict/CLI 기준 정리가 끝나면,
그 다음은 아래 순서가 자연스럽다.

### 추천 순서
1. `analyzer.py` 테스트 보강
2. `ml_factor_model.py` 테스트 보강
3. 필요 시 strict/CLI 구현 반영

즉,
**지금은 성공 경로의 의미를 먼저 고정하고,
그 다음에 분석 엔진 신뢰성 보강으로 넘어가는 구조**가 맞다.

---

## 7. 추천 커밋 흐름

```text
1. docs: define strict vs relaxed discovery baselines
2. docs: clarify promotion criteria relaxation behavior
3. docs: define CLI alignment plan for discovery success path
4. docs: record strict balanced and strict aggressive validation
5. docs: establish current recommended discovery baselines
```

만약 CLI 구현까지 바로 들어간다면:

```text
6. feat: expose base buy strategy and auto relax controls in discovery CLI
7. docs: add official CLI examples for promoted baseline flows
```

---

## 8. 최종 완료 판단 기준

이 계획의 완료는 아래 5가지를 모두 만족할 때다.

- [ ] strict / relaxed / exploratory baseline이 문서상 명확히 분리된다.
- [ ] 현재 성공 사례가 strict인지 relaxed인지 확정된다.
- [ ] CLI 기준으로 성공 경로를 설명할 수 있다.
- [ ] strict balanced / strict aggressive 재검증 결과가 남는다.
- [ ] 다음 단계(`analyzer.py`, `ml_factor_model.py` 테스트 보강)로 넘어갈 기준이 확정된다.

---

## 9. 한 줄 요약

지금부터의 우선 과제는
**“성공했다”는 사실 자체보다, 그 성공이 어떤 기준에서 성립한 것이고 그것을 공식 경로로 어떻게 재현할지 정리하는 것**이다.
