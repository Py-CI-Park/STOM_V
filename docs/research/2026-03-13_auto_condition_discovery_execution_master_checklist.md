# STOM 자동 조건식 탐색 시스템 — 상세 실행 계획 및 마스터 체크리스트

- 작성일: 2026-03-13
- 브랜치: `research/auto-condition-validation-pilot`
- 기준 문서:
  - `docs/research/2026-03-13_auto_condition_discovery_code_review_and_improvement_plan.md`
  - `docs/research/2026-03-11_auto_condition_validation_pilot_execution.md`
  - `docs/research/2026-03-10_auto_condition_discovery_implementation_checklist.md`
- 목적:
  1. `promote` 성공 사례 1건 이상 확보
  2. no-trade / cleanup 경로 안정화
  3. 핵심 분석/ML 경계 조건 테스트 보강
  4. 이후 리팩토링(P5/P6)까지 이어질 수 있는 실행 순서 고정

---

## 1. 최종 목표 정의

이 문서의 완료 기준은 단순 코드 추가가 아니다.
아래 4가지를 모두 만족해야 "이번 개선 스프린트 완료"로 판단한다.

### 1.1 필수 완료 기준

- [ ] `discover_and_promote_strategy()`가 no-trade 상황에서 자동 완화(`auto_relax`)를 수행한다.
- [ ] `top_n`, `ml_feature_limit`, `ml_weight`, `promotion_preset` 조합 중 최소 1개에서 **실제 promoted 성공 사례**를 확보한다.
- [ ] `optimiz.py`, `rolling_walk_forward_test.py` 경로에 대해 명시적 검증 기록이 남는다.
- [ ] `analyzer.py`, `ml_factor_model.py`에 핵심 경계 조건 테스트가 추가된다.
- [ ] 중단/정리 시 치명적 cleanup 예외가 재발하지 않는다.

### 1.2 권장 완료 기준

- [ ] JSON/Markdown report가 no-trade / auto-relax history를 설명적으로 보여준다.
- [ ] `shared_memory` warning 빈도 또는 재현 조건이 문서화된다.
- [ ] P5/P6까지 착수 가능하도록 설계 메모가 정리된다.

---

## 2. 작업 원칙

### 2.1 개발 원칙

- [ ] **TDD 우선**: 테스트 추가 → 실패 확인 → 구현 수정 → 재실행
- [ ] **작은 커밋 단위 유지**: 단계별로 커밋 분리
- [ ] **관련 파일만 커밋**: 현재 워킹트리의 다른 변경은 절대 섞지 않음
- [ ] **실행 기록 남기기**: 실제 promote / pilot 재실행 결과는 문서에 반영

### 2.2 우선순위 원칙

1. **실전 채택 성공에 직접 영향 있는 것 먼저**
2. 그 다음 **회귀 위험 제거**
3. 그 다음 **테스트 보강**
4. 마지막에 **리팩토링/품질 개선**

---

## 3. 전체 단계 개요

| 단계 | 코드명 | 목표 | 우선순위 |
|------|--------|------|----------|
| Step 1 | P1-A | auto-relax 설계/테스트 추가 | 🔴 최고 |
| Step 2 | P1-B | auto-relax 구현 + report 반영 | 🔴 최고 |
| Step 3 | P2 | `optimiz.py` / `rolling_walk_forward_test.py` 영향도 검증 | 🔴 높음 |
| Step 4 | P1-C | promote 재실행 및 성공 조합 탐색 | 🔴 높음 |
| Step 5 | P3 | `analyzer.py` 테스트 보강 | 🟡 중간 |
| Step 6 | P4 | `ml_factor_model.py` 테스트 보강 | 🟡 중간 |
| Step 7 | P5 | discovery config 객체화 검토/착수 | 🟢 선택 |
| Step 8 | P6 | `fillna(0)` 전략 개선 검토/착수 | 🟢 선택 |

---

## 4. Step 1 — P1-A: auto-relax 설계 및 테스트 추가

### 4.1 목적

현재는 생성된 조건식이 너무 강하면 `promote`가 거래 0건으로 실패한다.
이를 자동으로 완화하는 fallback 메커니즘을 먼저 설계하고,
테스트로 기대 동작을 고정한다.

### 4.2 대상 파일

- `tests/unit/test_ai_controller.py`
- 필요 시 `tests/unit/test_discovery_report.py`

### 4.3 추가할 테스트 체크리스트

- [ ] `top_n=5`에서 무거래 → `top_n=4` 또는 `top_n=3`으로 완화 재시도
- [ ] 완화 후 거래가 발생하면 해당 설정으로 promotion 평가 진행
- [ ] `top_n=1`까지도 무거래면 `auto_relax_failed=True`
- [ ] `auto_relax=False`이면 재시도 없이 종료
- [ ] `relax_history`가 결과 dict에 남음
- [ ] Markdown report에 auto-relax 이력 반영 가능 구조 확인

### 4.4 완료 기준

- [ ] 테스트가 먼저 추가됨
- [ ] 테스트가 초기에는 실패함
- [ ] 실패 원인이 auto-relax 미구현 때문임이 명확함

### 4.5 추천 커밋 단위

```text
test: add auto relax promotion fallback coverage
```

---

## 5. Step 2 — P1-B: auto-relax 구현 및 report 반영

### 5.1 목적

Step 1에서 정의한 기대 동작을 실제 구현으로 연결한다.

### 5.2 대상 파일

- `cli/ai_controller.py`
- `cli/discovery_report.py`
- 필요 시 `cli/promotion.py`

### 5.3 구현 체크리스트

- [ ] `discover_and_promote_strategy()`에 `auto_relax` 인자 추가
- [ ] `max_relax_steps` 인자 추가
- [ ] 완화 루프 설계
- [ ] 각 시도별 `top_n`, `zero_trade_rounds`, `round_count` 기록
- [ ] 거래 발생 시점의 설정으로 평가 진행
- [ ] 끝까지 실패하면 `auto_relax_failed=True` 표기
- [ ] report에 `auto_relax_history` 반영
- [ ] report Markdown에 `Auto-Relax History` 섹션 추가

### 5.4 검증 체크리스트

- [ ] Step 1 테스트 통과
- [ ] 기존 `discover_and_promote_strategy` 테스트 회귀 없음
- [ ] 기존 report 테스트 회귀 없음

### 5.5 완료 기준

- [ ] no-trade 전략에서 자동 완화 재시도가 실제로 수행됨
- [ ] 결과 dict와 report에 완화 이력이 남음

### 5.6 추천 커밋 단위

```text
feat: add auto relax fallback for discovery promotion
```

---

## 6. Step 3 — P2: `optimiz.py` / `rolling_walk_forward_test.py` 영향도 검증

### 6.1 목적

B_*/S_*/R_* 결과 확장 이후 기존 최적화/WFO 경로가 깨지지 않았는지 명시적으로 검증한다.

### 6.2 대상 파일

- `backtest/optimiz.py`
- `backtest/rolling_walk_forward_test.py`
- `backtest/back_static.py`
- `backtest/back_subtotal.py`

### 6.3 정적 점검 체크리스트

- [ ] `GetResultDataframe()` 호출 위치 확인
- [ ] 고정 tuple 언패킹 패턴 확인
- [ ] `B_`, `S_`, `R_` 추가 컬럼이 downstream에서 무시/보존되는 방식 확인
- [ ] `*extra` 패턴 필요 여부 확인

### 6.4 실행 점검 체크리스트

- [ ] 관련 유닛/회귀 테스트 존재 여부 확인
- [ ] 최소 smoke 경로 실행 또는 호출 구조 점검 기록 남김
- [ ] 크래시 증거 없음 / 수정 필요 여부 문서화

### 6.5 결과 분기

#### A. 문제 없음
- [ ] 문서에 “검증 완료, 회귀 없음” 기록

#### B. unpack/shape 관련 문제 발견
- [ ] 영향받는 위치 수정
- [ ] 관련 테스트 추가
- [ ] 재검증 후 문서 반영

### 6.6 완료 기준

- [ ] 두 파일 모두 “미확인” 상태에서 벗어남
- [ ] 검증 결과가 문서로 남음

### 6.7 추천 커밋 단위

```text
docs: verify optimiz and rolling walk forward result expansion impact
```
또는 수정이 있으면
```text
fix: sync optimize and rolling walk forward with expanded result columns
```

---

## 7. Step 4 — P1-C: promote 재실행 및 성공 조합 탐색

### 7.1 목적

실제 promoted 성공 사례 1건 이상을 확보한다.

### 7.2 기본 전략

자동 완화가 들어간 상태에서 우선 작은 pilot slice부터 재시도하고,
그 후 full-range 또는 다른 전략으로 확대한다.

### 7.3 탐색 대상 파라미터

- [ ] `top_n`: 5 / 4 / 3 / 2 / 1
- [ ] `ml_feature_limit`: 0 / 1 / 3
- [ ] `ml_weight`: 0.0 / 0.3 / 0.5
- [ ] `promotion_preset`: aggressive / balanced
- [ ] 필요 시 `engine_count`: 1 / 2

### 7.4 실행 순서

#### 1차
- [ ] 기존 slice (`2025-04-07 ~ 2025-04-18`)로 재실행
- [ ] auto-relax 동작 확인
- [ ] no-trade에서 완화 이력 확인

#### 2차
- [ ] slice에서 promoted 성공이 없으면 다른 `top_n`/preset 조합 확인
- [ ] 필요 시 full-range 또는 대체 전략으로 pilot 확대

#### 3차
- [ ] promoted 성공 사례 1건 확보
- [ ] 해당 설정을 문서에 baseline successful config로 기록

### 7.5 성공 기준

- [ ] `promoted=True` 결과 1건 이상 확보
- [ ] report JSON/Markdown 생성 확인
- [ ] 채택 근거가 report에서 설명 가능

### 7.6 실패 시 기록해야 할 것

- [ ] 어느 조합에서 무거래가 발생했는지
- [ ] 어느 조합에서 WFO round는 돌았지만 기준 미달인지
- [ ] cleanup/shared_memory warning 발생 여부

### 7.7 추천 커밋 단위

성공/실패 여부를 코드 변경과 함께 묶지 말고,
실행 기록은 문서 커밋으로 분리한다.

```text
docs: record auto relax promotion pilot results
```

---

## 8. Step 5 — P3: `analyzer.py` 테스트 보강

### 8.1 목적

분석 로직 경계 조건을 명시적으로 고정한다.

### 8.2 대상 파일

- `tests/unit/test_analyzer.py`

### 8.3 추가할 테스트 체크리스트

- [ ] `analyze_ttest_candidates()` 독립 테스트
- [ ] `benjamini_hochberg()` empty input
- [ ] `benjamini_hochberg()` single value
- [ ] `benjamini_hochberg()` all significant
- [ ] `benjamini_hochberg()` none significant
- [ ] `B_시가총액` 컬럼 누락 처리
- [ ] `B_시분초` 컬럼 누락 처리
- [ ] 전체 통합 분석 흐름 smoke
- [ ] empty dataframe 처리

### 8.4 완료 기준

- [ ] analyzer 핵심 함수별 직접 테스트 존재
- [ ] 경계 조건 테스트 포함
- [ ] 회귀 없이 전체 테스트 통과

### 8.5 추천 커밋 단위

```text
test: expand analyzer edge case coverage
```

---

## 9. Step 6 — P4: `ml_factor_model.py` 테스트 보강

### 9.1 목적

ML 분석기의 경계 조건과 fallback 경로를 고정한다.

### 9.2 대상 파일

- `tests/unit/test_ml_factor_model.py`

### 9.3 추가할 테스트 체크리스트

- [ ] class imbalance 케이스
- [ ] 작은 데이터셋의 `n_splits` 조정
- [ ] `gradient_boosting` 경로
- [ ] 숫자형 B_* 컬럼 없음 처리
- [ ] importance dict key 검증
- [ ] SHAP 미설치 fallback 검증

### 9.4 완료 기준

- [ ] fallback/경계 조건 테스트 확보
- [ ] analyzer와 함께 최소 신뢰성 기준 충족

### 9.5 추천 커밋 단위

```text
test: expand ml factor model edge case coverage
```

---

## 10. Step 7 — P5: config 객체화 (선택)

### 목적

현재 discovery 관련 파라미터를 더 구조적으로 관리한다.

### 체크리스트

- [ ] `DiscoveryAnalysisConfig` 정의
- [ ] `DiscoveryMlConfig` 정의
- [ ] `DiscoveryWfoConfig` 정의
- [ ] `DiscoveryConfig` 정의
- [ ] controller 시그니처 단순화
- [ ] 기존 CLI 연결 방식 유지 또는 migration 계획 수립

### 착수 조건

- [ ] P1~P4 완료 후
- [ ] promoted 성공 사례 확보 후

---

## 11. Step 8 — P6: `fillna(0)` 전략 개선 (선택)

### 목적

ML 입력 결측치 처리 품질 개선

### 체크리스트

- [ ] 현재 결측치 발생 피처 파악
- [ ] 중앙값 대체 vs sentinel(-1) 비교
- [ ] 피처별 전략 문서화
- [ ] 회귀 테스트 추가

### 착수 조건

- [ ] P1~P4 완료 후
- [ ] ML 성능 또는 해석성 개선 필요가 명확할 때

---

## 12. 권장 커밋 흐름

```text
1. test: add auto relax promotion fallback coverage
2. feat: add auto relax fallback for discovery promotion
3. docs/fix: verify optimize and rolling walk forward impact
4. docs: record auto relax promotion pilot results
5. test: expand analyzer edge case coverage
6. test: expand ml factor model edge case coverage
7. refactor: introduce discovery config objects          (선택)
8. refactor: improve ml missing value strategy          (선택)
```

---

## 13. 첫 번째 단계 착수 전 확인 사항

### 환경 확인
- [ ] 현재 브랜치 확인
- [ ] 관련 문서 최신 상태 확인
- [ ] 기존 pilot CSV 경로 확인
- [ ] strategy.db 접근 가능 여부 확인

### 작업 범위 고정
- [ ] Step 1에서는 테스트 파일만 우선 수정
- [ ] Step 2 구현 전 Step 1 실패 결과를 확인
- [ ] unrelated 변경은 절대 커밋에 포함하지 않음

---

## 14. 바로 실행할 첫 번째 단계

### Step 1 즉시 실행 항목

1. `tests/unit/test_ai_controller.py`에 auto-relax 관련 테스트 3개 추가
2. 필요 시 `tests/unit/test_discovery_report.py`에 relax history report 테스트 1개 추가
3. pytest로 실패 확인
4. 실패 결과를 기준으로 Step 2 구현 착수

### Step 1 성공 판정

- [ ] 테스트가 실제로 실패한다
- [ ] 실패 이유가 auto-relax 미구현 때문임이 분명하다
- [ ] 다음 단계 구현 범위가 확정된다

---

## 15. 완료 후 문서 반영 대상

이번 마스터 체크리스트를 따라 작업이 끝나면 다음 문서를 업데이트한다.

- `docs/research/2026-03-11_auto_condition_validation_pilot_execution.md`
- `docs/research/2026-03-13_auto_condition_discovery_code_review_and_improvement_plan.md`

반영 내용:
- [ ] auto-relax 구현 여부
- [ ] promoted 성공 사례 확보 여부
- [ ] 영향도 검증 결과
- [ ] 테스트 보강 결과
- [ ] 남은 선택 작업(P5/P6)

---

## 16. 최종 한 줄 요약

이번 스프린트의 핵심은
**"auto-relax를 넣어 실제 promote 성공 사례를 확보하고, 그 과정에서 기존 최적화/WFO 경로와 분석 테스트를 안정화하는 것"**이다.
