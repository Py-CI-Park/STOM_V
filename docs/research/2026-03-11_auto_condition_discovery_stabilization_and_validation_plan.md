# STOM 자동 조건식 탐색 시스템 — 안정화 우선 판단 및 실전 검증 계획

- 작성일: 2026-03-11
- 브랜치: `research/auto-condition-discovery`
- 목적: 현재까지 구현된 자동 조건식 탐색 파이프라인을 기준으로  
  **(1) 추가 기능 개발이 더 필요한지**,  
  **(2) 코드 검토/안정화가 더 우선인지**,  
  **(3) 실제로 어떤 순서로 검증해야 하는지**를 정리한다.

---

## 1. 현재까지 구현된 범위 요약

### 최근 핵심 커밋 흐름

| 커밋 | 내용 |
|------|------|
| `91da5ae` | B_/S_/R_ 결과 확장 + CSV 저장 |
| `88587e8` | analyzer + condition generator |
| `06b014a` | WFO 모듈 |
| `77f935b` | 분석 결과 → strategy 생성 연결 |
| `b37eb30` | ML factor analysis |
| `4da5ef0` | WFO 통과 전략만 최종 채택 |
| `4814d1a` | discovery workflow 공식 CLI 승격 |
| `b080fa9` | ML-guided discovery candidate filtering |
| `a34ebe1` | promotion preset + discovery report |
| `eb20ded` | preset report + ML-guided ranking |

### 현재 가능한 흐름

1. 백테스트 결과 상세 CSV 생성
2. `discovery analyze`
3. `discovery ml-analyze`
4. `discovery generate`
5. `discovery create-strategy`
6. `discovery promote`
7. WFO 기준으로 통과한 전략만 최종 채택
8. JSON / Markdown 리포트 생성

즉, **문서 기준 핵심 비-ML/ML 파이프라인은 이미 거의 완성**된 상태다.

---

## 2. 결론: 지금은 “더 만들기”보다 “검토/안정화”가 우선

### 결론

> **현재 우선순위는 추가 기능 개발보다 코드 검토와 안정화, 그리고 실제 데이터 기반 검증이다.**

### 이유

#### 2.1 기능 밀도가 이미 충분히 높다
단기간에 discovery / WFO / ML / promotion / report / CLI가 모두 들어갔다.
지금은 기능이 부족하다기보다, **서로 잘 붙어 있는지 검증하는 단계**다.

#### 2.2 단위 테스트는 강하지만, 실제 운영형 검증은 더 필요하다
현재는 unit/regression test가 많이 쌓였지만,  
다음이 더 중요하다:

- 실제 CSV로 analyze → generate → create-strategy → promote가 잘 이어지는지
- preset별로 결과가 합리적으로 달라지는지
- report가 사람이 읽고 판단 가능한지
- 장시간/실제 runner 경로에서 프로세스 정리가 잘 되는지

#### 2.3 운영 리스크가 이미 관찰되었다
OMX team worker가 terminal completion까지 안정적으로 가지 못하는 문제가 반복되었다.
이는 STOM discovery 핵심 로직의 결함이라기보다는,
**운영형 자동화 경로의 안정화가 아직 더 필요하다는 신호**다.

#### 2.4 지금 단계의 목표는 “새 기능 발명”보다 “실제 유효성 입증”
현재 discovery 시스템이 해야 할 일은:
- 새로운 조건식 후보를 자동으로 찾고
- WFO로 검증하고
- 통과 전략만 채택하는 것

이제 중요한 건 **정말로 그 기능이 실제 전략 탐색 도구로 유효한지**를 입증하는 것이다.

---

## 3. 지금 우리가 하려는 것이 정확히 무엇인가

### 질문 1
**“현재 자동화 프로세스로 새로운 조건식을 찾아보려는 것이 맞나요?”**

정답은 **예**다.  
다만 더 정확히는:

> **완전히 새로운 전략을 무에서 발명하는 것**보다는  
> **기존 전략에 붙일 수 있는 후보 필터/조건식을 자동으로 찾고 검증하는 것**에 가깝다.

즉, 이 시스템은 현 단계에서
- pruning
- filtering
- candidate generation
- validation
에 더 강하다.

### 질문 2
**“지금까지 개발된 내용을 사용해보면서 검증하는 것이 맞나요?”**

정답은 **예, 지금은 그게 맞고 오히려 그게 우선이다.**

이유:
- 핵심 파이프라인은 이미 구현됨
- 지금부터는 “더 개발”보다 “정말 쓸 수 있는지 검증”이 더 중요함
- 검증 결과에 따라
  - preset 조정
  - report 개선
  - ML weighting 조정
  - 실제 SHAP 활성화
  순으로 가는 것이 맞다.

---

## 4. 추천하는 다음 단계: 안정화 스프린트

### 4.1 목표

다음 단계의 목표는

> **“현재 파이프라인이 실제 전략 탐색 도구로 신뢰할 수 있는가”를 입증하는 것**

이다.

### 4.2 안정화 스프린트의 세 축

#### A. 기능 검증
- 각 CLI 서브커맨드가 실제 CSV에 대해 제대로 동작하는지
- temp strategy.db / report 파일이 정상 생성되는지

#### B. 연구 검증
- 후보 조건이 실제로 말이 되는지
- ML top feature와 통계 후보가 어느 정도 정렬되는지
- WFO 통과 전략이 적절히 걸러지는지

#### C. 운영 검증
- long-running path에서 프로세스 정리가 잘 되는지
- report 결과가 사람/AI 모두에게 읽기 좋은지
- preset 차이가 실제로 의미 있게 작동하는지

---

## 5. 실전 검증 시나리오 (권장)

### 5.1 검증 원칙

처음부터 여러 전략을 동시에 검증하지 않는다.

**대표 전략 1~2개만 선택해서 pilot 방식으로 검증**한다.

권장 대상:
- 이미 특성이 잘 알려진 buy 전략 1개
- 충분히 써본 sell 전략 1개
- train/test를 나눌 수 있도록 데이터가 충분한 기간

### 5.2 실전 검증 단계

#### Step 1. baseline 백테스트 실행

목적:
- 기준 성과 확보
- 상세 CSV 확보

예시:

```bash
python stom_backtest.py \
  --buy <기준매수전략> \
  --sell <기준매도전략> \
  --start 20240101 \
  --end 20240630 \
  --timeframe min
```

기대 결과:
- `backtest/csv/` 에 상세 CSV 생성
- 기준 거래 수, 수익률, MDD, TPI 확보

#### Step 2. 통계 분석

목적:
- 시총/시간대/quantile 기반 후보 확인

예시:

```bash
python stom_backtest.py discovery analyze \
  --input backtest/csv/<baseline>.csv \
  --output temp/analysis.json \
  --min-samples 30 \
  --quantiles 10 \
  --alpha 0.05
```

확인 포인트:
- 후보가 너무 많지 않은가
- 후보가 전부 이상한 값은 아닌가
- 시총/시간대 조건이 직관과 크게 어긋나지 않는가

#### Step 3. ML 분석

목적:
- top feature를 뽑아 통계 후보와 비교

예시:

```bash
python stom_backtest.py discovery ml-analyze \
  --input backtest/csv/<baseline>.csv \
  --output temp/ml_analysis.json \
  --model-type random_forest \
  --top-n 10 \
  --n-splits 5
```

확인 포인트:
- top feature가 이해 가능한가
- `shap_available` 값 확인
- ML 상위 feature와 통계 기반 후보가 어느 정도 정렬되는가

#### Step 4. 조건 코드 생성

목적:
- 실제 자동 생성된 코드가 사람이 읽을 수 있는지 확인

예시:

```bash
python stom_backtest.py discovery generate \
  --input backtest/csv/<baseline>.csv \
  --output temp/generated_conditions.py \
  --top-n 5 \
  --ml-feature-limit 3 \
  --ml-weight 0.5 \
  --min-samples 30 \
  --quantiles 10
```

확인 포인트:
- 코드가 지나치게 복잡하지 않은가
- 전부 `B_*` 기반인가
- 임계값이 상식적인가

#### Step 5. strategy.db 저장

목적:
- 자동 생성 후보를 실제 전략으로 등록 가능한지 확인

예시:

```bash
python stom_backtest.py discovery create-strategy Auto_B_Pilot01 \
  --input backtest/csv/<baseline>.csv \
  --output-code temp/Auto_B_Pilot01.py \
  --top-n 5 \
  --ml-feature-limit 3 \
  --ml-weight 0.5 \
  --min-samples 30 \
  --quantiles 10
```

확인 포인트:
- strategy.db 저장 성공 여부
- strategy validate/analyze 시 문제 없는지

#### Step 6. promote (핵심)

목적:
- 후보 전략을 자동으로 검증하고 통과 전략만 채택

예시:

```bash
python stom_backtest.py discovery promote Auto_B_Pilot01 \
  --input backtest/csv/<baseline>.csv \
  --sell <기준매도전략> \
  --start 20240101 \
  --end 20240630 \
  --timeframe min \
  --train-window-days 60 \
  --test-window-days 20 \
  --step-days 20 \
  --purge-days 2 \
  --embargo-days 2 \
  --promotion-preset balanced \
  --report-json temp/Auto_B_Pilot01_report.json \
  --report-md temp/Auto_B_Pilot01_report.md \
  --ml-feature-limit 3 \
  --ml-weight 0.5
```

확인 포인트:
- promoted=True/False가 합리적인가
- report에 채택/탈락 이유가 충분한가
- preset을 바꾸면 결과 차이가 있는가

### 5.3 preset 비교 실험

같은 입력 CSV / 같은 후보 전략에 대해 아래 3개를 각각 돌린다.

- `conservative`
- `balanced`
- `aggressive`

기대:
- conservative: 통과 가장 적음
- balanced: 중간
- aggressive: 통과 가장 많음

만약 차이가 거의 없다면:
- preset 수치가 부적절하거나
- 평가 지표가 충분히 민감하지 않거나
- candidate quality가 낮을 수 있다.

---

## 6. 성공/실패 기준

### 6.1 성공 기준

다음 중 다수가 만족되면 현재 시스템은 유효하다고 본다.

1. candidate가 과도하게 많지 않다
2. candidate 내용이 상식적으로 이해 가능하다
3. ML top feature와 통계 후보가 어느 정도 정렬된다
4. promote에서 일부 전략은 통과, 일부는 탈락한다
5. preset별로 합리적인 차이가 난다
6. JSON/Markdown report가 실제 판단에 도움이 된다
7. 실제 long-running path에서 프로세스 정리가 무리 없이 된다

### 6.2 실패 신호

다음은 안정화/튜닝이 필요하다는 신호다.

1. candidate가 너무 많다
2. candidate가 전부 비상식적이다
3. 거의 모든 전략이 promote 통과한다
4. 거의 어떤 전략도 promote 통과하지 못한다
5. ML top feature가 매번 불안정하게 튄다
6. report를 보고도 채택 이유를 설명할 수 없다
7. 실행 후 프로세스 정리나 CLI 흐름이 자주 꼬인다

---

## 7. 지금 시점에서 더 개발이 필요한가?

### 답: “필요는 하지만, 새 기능보다 안정화가 우선”

즉,
- **새 기능 추가 개발**
  보다는
- **현재까지 만든 파이프라인을 실제로 돌려보고 안정화**
  하는 것이 더 중요하다.

### 더 개발이 필요한 영역

필수보다 “고도화” 성격이 강한 것:
- 실제 SHAP 활성화
- GUI 연동
- 더 정교한 ML ranking/ensemble
- scheduler/cron용 실행 예제

### 지금 더 우선인 영역

- discovery CLI 통합 검증
- preset 값 검증
- report 품질 점검
- 실제 temp DB / temp CSV 기반 end-to-end pilot
- 프로세스/runner 안정성 확인

---

## 8. 다음 단계 추천

### 바로 다음 단계 (권장)

#### Phase S1 — 안정화 스프린트

권장 작업:
1. 대표 전략 1~2개로 pilot 검증 수행
2. `analyze → ml-analyze → generate → create-strategy → promote` 전 과정 실행
3. preset 3종 비교
4. report 품질 점검
5. 채택 기준 조정 필요 여부 판단

### 그 다음 단계

pilot 결과가 좋다면 다음 중 하나로 간다.

1. **SHAP 실제 활성화**
2. **GUI 연동**
3. **scheduler/cron용 운영 시나리오 정리**

---

## 9. 한 줄 정리

> **지금은 자동화 프로세스로 새로운 조건식을 실제로 찾아보고,  
> 지금까지 개발한 파이프라인을 사용해 그 유효성을 검증하는 단계가 맞다.**

즉,
- 네, 자동화 프로세스로 조건식을 찾으려는 것이 맞고
- 네, 지금은 그걸 “더 개발”보다 “실제로 사용해보며 검증”하는 것이 더 우선이다.
