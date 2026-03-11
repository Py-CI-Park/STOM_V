# STOM 자동 조건식 탐색 시스템 — 실전 검증 Pilot 실행 기록

- 작성일: 2026-03-11
- 브랜치: `research/auto-condition-validation-pilot`
- 기준 문서:
  - `docs/research/2026-03-11_auto_condition_discovery_stabilization_and_validation_plan.md`
  - `docs/research/2026-03-10_auto_condition_discovery_implementation_checklist.md`
- 목적: 안정화 스프린트의 **실전 검증 시나리오**를 실제로 수행하고,
  단계별 결과를 기록한다.

---

## 1. Pilot 검증 목표

이번 Pilot의 목표는 아래를 실제 데이터/전략으로 검증하는 것이다.

1. baseline 백테스트가 정상 실행되는가
2. detailed CSV가 정상 생성되는가
3. `discovery analyze`가 후보를 정상 생성하는가
4. `discovery ml-analyze`가 ML top feature를 정상 생성하는가
5. `discovery generate`가 조건 코드를 생성하는가
6. `discovery create-strategy`가 strategy.db에 전략을 저장하는가
7. `discovery promote`가 WFO를 수행하고 preset 기준으로 채택/탈락을 판정하는가
8. report(JSON/Markdown)가 충분히 설명적인가

---

## 2. Pilot 대상

### 2.1 대상 전략

- 기준 매수 전략: `Min_B_Study_251227`
- 기준 매도 전략: `Min_S_Study_251227`

### 2.2 대상 구간

- 시작일: `2025-04-07`
- 종료일: `2025-05-30`
- 타임프레임: `min`

### 2.3 선택 이유

- `stock_min_back.db` 기준 `2025-04-07` ~ `2025-05-30` 구간에 **34 거래일** 존재
- 너무 길지 않으면서도 train/test 구간을 여러 번 나눌 수 있는 최소 수준
- 문서에서 제안한 pilot 성격에 적합

---

## 3. 실행 체크리스트

### Step 1. baseline 백테스트
- [ ] 실행
- [ ] JSON 결과 저장 확인
- [ ] CSV 저장 확인
- [ ] baseline 지표 기록

### Step 2. discovery analyze
- [ ] 실행
- [ ] analysis JSON 저장 확인
- [ ] candidate 수 기록
- [ ] 대표 후보 메모

### Step 3. discovery ml-analyze
- [ ] 실행
- [ ] ML analysis JSON 저장 확인
- [ ] top feature 기록
- [ ] `shap_available` 상태 기록

### Step 4. discovery generate
- [ ] 실행
- [ ] generated condition code 저장 확인
- [ ] 코드 품질 / 가독성 메모

### Step 5. discovery create-strategy
- [ ] 실행
- [ ] strategy.db 저장 확인
- [ ] 생성된 전략명 기록

### Step 6. discovery promote
- [ ] 실행
- [ ] WFO 동작 확인
- [ ] promoted 여부 확인
- [ ] preset/report 생성 확인

### Step 7. 결과 해석
- [ ] preset 결과 해석
- [ ] ML top feature와 통계 후보 정렬 여부 메모
- [ ] 다음 조치 제안 작성

---

## 4. 실행 로그

### 4.1 baseline 백테스트

실행 명령:

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
  --buy Min_B_Study_251227 \
  --sell Min_S_Study_251227 \
  --start 20250407 \
  --end 20250530 \
  --timeframe min \
  --engines 2 \
  -o temp/pilot_baseline.json
```

결과:

- 상태: 미실행
- 메모:

### 4.2 discovery analyze

실행 명령:

```bash
python stom_backtest.py discovery analyze \
  --input <baseline_csv_path> \
  --output temp/pilot_analysis.json \
  --min-samples 30 \
  --quantiles 10 \
  --alpha 0.05
```

결과:

- 상태: 미실행
- 메모:

### 4.3 discovery ml-analyze

실행 명령:

```bash
python stom_backtest.py discovery ml-analyze \
  --input <baseline_csv_path> \
  --output temp/pilot_ml_analysis.json \
  --model-type random_forest \
  --top-n 10 \
  --n-splits 5
```

결과:

- 상태: 미실행
- 메모:

### 4.4 discovery generate

실행 명령:

```bash
python stom_backtest.py discovery generate \
  --input <baseline_csv_path> \
  --output temp/pilot_generated_conditions.py \
  --top-n 5 \
  --ml-feature-limit 3 \
  --ml-weight 0.5 \
  --min-samples 30 \
  --quantiles 10
```

결과:

- 상태: 미실행
- 메모:

### 4.5 discovery create-strategy

실행 명령:

```bash
python stom_backtest.py discovery create-strategy Auto_B_Pilot01 \
  --input <baseline_csv_path> \
  --output-code temp/Auto_B_Pilot01.py \
  --top-n 5 \
  --ml-feature-limit 3 \
  --ml-weight 0.5 \
  --min-samples 30 \
  --quantiles 10
```

결과:

- 상태: 미실행
- 메모:

### 4.6 discovery promote

실행 명령:

```bash
python stom_backtest.py discovery promote Auto_B_Pilot01 \
  --input <baseline_csv_path> \
  --sell Min_S_Study_251227 \
  --start 20250407 \
  --end 20250530 \
  --timeframe min \
  --train-window-days 10 \
  --test-window-days 5 \
  --step-days 5 \
  --purge-days 1 \
  --embargo-days 1 \
  --promotion-preset balanced \
  --report-json temp/Auto_B_Pilot01_report.json \
  --report-md temp/Auto_B_Pilot01_report.md \
  --ml-feature-limit 3 \
  --ml-weight 0.5
```

결과:

- 상태: 미실행
- 메모:

---

## 5. 결과 요약

- baseline 성공 여부:
- analyze 성공 여부:
- ml-analyze 성공 여부:
- generate 성공 여부:
- create-strategy 성공 여부:
- promote 성공 여부:
- promoted 여부:
- report 생성 여부:

---

## 6. 해석 및 판단

### 6.1 후보 품질

- 작성 예정

### 6.2 ML 정렬성

- 작성 예정

### 6.3 preset 적절성

- 작성 예정

### 6.4 운영 안정성

- 작성 예정

---

## 7. 다음 단계 제안

- 작성 예정
