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

- 상태: 완료
- 산출물:
  - `temp/pilot_baseline.json`
  - `backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv`
- 주요 지표:
  - 거래횟수: `1542`
  - 승률: `24.58%`
  - 평균수익률: `-0.97%`
  - 수익률합계: `-57.82%`
  - 수익금합계: `-14,922,548원`
  - 최대낙폭률(MDD): `57.87%`
  - TPI: `0.65`
- 메모:
  - baseline 자체가 상당히 좋지 않은 전략 상태로 확인됨
  - 종료 시 `shared_memory` 관련 `resource_tracker` warning 발생
  - 이 warning은 현재 “안정화 우선” 판단을 강화하는 신호임

### 4.2 discovery analyze

실행 명령:

```bash
python stom_backtest.py discovery analyze \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --output temp/pilot_analysis.json \
  --min-samples 30 \
  --quantiles 10 \
  --alpha 0.05
```

결과:

- 상태: 완료
- 산출물:
  - `temp/pilot_analysis.json`
- 핵심 결과:
  - row_count: `1542`
  - feature_columns: `14개`
  - 대표 시간대 후보:
    - `93000 <= B_시분초 < 113000` (오전)
    - `113000 <= B_시분초 < 130000` (점심)
  - 대표 quantile 후보:
    - `15.304 <= B_등락율 < 17.74`
    - `2182 <= B_시가총액 < 2659`
    - `92.656 <= B_체결강도 < 95.742`
- 메모:
  - 후보는 충분히 생성되었고, 전반적으로 과열/중후반 시간대/특정 시총/체결강도 구간이 나쁜 쪽으로 잡힘
  - 다만 후보 수가 많아 human review 없이 바로 채택하기에는 부담이 있음

### 4.3 discovery ml-analyze

실행 명령:

```bash
python stom_backtest.py discovery ml-analyze \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --output temp/pilot_ml_analysis.json \
  --model-type random_forest \
  --top-n 10 \
  --n-splits 5
```

결과:

- 상태: 완료
- 산출물:
  - `temp/pilot_ml_analysis.json`
- 핵심 결과:
  - row_count: `1542`
  - mean_cv_score: `0.7268`
  - top_features 상위 5개:
    1. `B_당일거래대금`
    2. `B_등락율`
    3. `B_회전율`
    4. `B_시가총액`
    5. `B_거래대금증감`
  - `shap_available: false`
  - `shap_status: unavailable`
- 메모:
  - 통계 분석 결과와 ML top feature가 크게 어긋나지 않음
  - SHAP은 미설치 상태라 fallback 처리됨

### 4.4 discovery generate

실행 명령:

```bash
python stom_backtest.py discovery generate \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --output temp/pilot_generated_conditions.py \
  --top-n 5 \
  --ml-feature-limit 3 \
  --ml-weight 0.5 \
  --min-samples 30 \
  --quantiles 10
```

결과:

- 상태: 완료
- 산출물:
  - `temp/pilot_generated_conditions.py`
- 메모:
  - 첫 실행에서는 `B_등락율` 같은 접두사 기반 표현식이 runtime 전략 코드로 그대로 들어가
    `NameError`를 유발함
  - 이후 생성기에서 runtime 전략 맥락에서는 `B_` 접두사를 제거하도록 수정함
  - 수정 후 생성 코드는 다음처럼 runtime 변수명으로 정상 출력됨
    - `등락율`
    - `당일거래대금`
    - `회전율`
    - `체결강도`

### 4.5 discovery create-strategy

실행 명령:

```bash
python stom_backtest.py discovery create-strategy Auto_B_Pilot01 \
  --input temp/pilot_slice_20250407_20250418.csv \
  --output-code temp/Auto_B_PilotSlice01.py \
  --top-n 5 \
  --ml-feature-limit 3 \
  --ml-weight 0.5 \
  --min-samples 30 \
  --quantiles 10
```

결과:

- 상태: 완료
- 산출물:
  - `temp/Auto_B_PilotSlice01.py`
  - strategy name: `Auto_B_PilotSlice01`
- 메모:
  - 일관성 있는 bounded pilot을 위해 이후 단계는 `2025-04-07 ~ 2025-04-18` slice (`500행`) 기준으로 재수행함
  - slice 기준 ML top feature는
    - `B_당일거래대금`
    - `B_체결강도`
    - `B_회전율`
    로 확인됨
  - 생성된 조건식은 runtime 변수명으로 정상 저장됨

### 4.6 discovery promote

실행 명령:

```bash
python stom_backtest.py discovery promote Auto_B_PilotSlice01 \
  --input temp/pilot_slice_20250407_20250418.csv \
  --sell Min_S_Study_251227 \
  --start 20250407 \
  --end 20250418 \
  --timeframe min \
  --train-window-days 5 \
  --test-window-days 2 \
  --step-days 2 \
  --purge-days 1 \
  --embargo-days 1 \
  --promotion-preset balanced \
  --report-json temp/Auto_B_PilotSlice01_report.json \
  --report-md temp/Auto_B_PilotSlice01_report.md \
  --ml-feature-limit 3 \
  --ml-weight 0.5
```

결과:

- 상태: 실행 완료(실패)
- 결과:
  - 각 WFO 라운드에서 `매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다.` 발생
  - 최종 promote 보고서(JSON/Markdown)는 생성되지 않음
  - 프로세스 종료 시 `shared_memory` 관련 `resource_tracker` warning 반복
- 해석:
  - 현재 생성된 필터가 너무 강해 짧은 검증 구간에서 거래가 사라지는 현상으로 보임
  - 또는 baseline 자체가 충분히 나쁘기 때문에 pruning 후에도 유효 거래가 유지되지 않음
  - bounded pilot의 목적은 달성됨: **현재 promote 파이프라인은 “실행은 되지만 실제 전략 채택에는 추가 조정이 필요”**

---

## 5. 결과 요약

- baseline 성공 여부: **성공**
- analyze 성공 여부: **성공**
- ml-analyze 성공 여부: **성공**
- generate 성공 여부: **성공**
- create-strategy 성공 여부: **성공**
- promote 성공 여부: **실행은 성공했으나 전략 채택은 실패**
- promoted 여부: **False**
- report 생성 여부: **False** (trade 없음)

---

## 6. 해석 및 판단

### 6.1 후보 품질

- 통계 후보와 ML top feature는 대체로 정렬됨
- 즉, 후보가 완전히 무의미한 것은 아님
- 다만 `top-n=5`, `ml-feature-limit=3`, `ml-weight=0.5` 조합은
  pilot slice 기준으로는 다소 공격적으로 작용해 거래가 지나치게 줄어듦

### 6.2 ML 정렬성

- full range 기준 top feature:
  - `당일거래대금`
  - `등락율`
  - `회전율`
- slice 기준 top feature:
  - `당일거래대금`
  - `체결강도`
  - `회전율`
- 공통적으로 거래대금/회전율/체결강도/등락율 계열이 상위에 있어
  “후보가 아예 엉뚱한 방향으로 가고 있지는 않다”고 볼 수 있음

### 6.3 preset 적절성

- `balanced` preset조차 trade-less 상태를 만들었으므로,
  현재 전략/구간 조합에서는 preset보다 **candidate 생성 강도**가 먼저 문제일 가능성이 높음
- 즉 preset만 aggressive로 바꿔도 해결 안 될 수 있으며,
  먼저 `top-n`, `ml-feature-limit`, `ml-weight`를 조정할 필요가 큼

### 6.4 운영 안정성

- baseline과 promote 모두 실제 runner 경로는 동작했음
- 하지만 promote 단계에서 round 반복 시
  - trade 없음
  - `shared_memory` cleanup warning
  이 관찰됨
- 따라서 현재 판단은 여전히 유효함:
  **새 기능 추가보다 안정화/검증이 우선**

---

## 7. 다음 단계 제안

### 7.1 가장 우선할 것

1. `promote` 이전에 candidate 강도를 낮추는 validation matrix를 만든다.
   - `top-n`: 2 / 3 / 5
   - `ml-feature-limit`: 0 / 1 / 3
   - `ml-weight`: 0.0 / 0.3 / 0.5
   - `promotion-preset`: balanced / aggressive

2. 위 조합 중 **거래 수가 0이 아닌 조합**을 먼저 찾는다.

3. 그 다음에야 preset/report 품질을 다시 평가한다.

### 7.2 기술적 안정화 작업

1. `shared_memory` cleanup warning 원인 확인
2. `trade_count == 0`인 WFO round 처리/report 처리 개선
3. `discover_and_promote_strategy()`에서 “거래 없음”을 더 설명적으로 리포트하도록 개선

### 7.3 연구적 다음 단계

1. baseline이 너무 나쁜 전략이면 다른 기준 전략으로 pilot 재수행
2. SHAP 설치는 지금 당장 우선순위가 아님
3. 먼저 “거래가 살아있는 promote 성공 경로”를 확보하는 것이 우선

---

## 8. 2차 안정화 작업 및 readiness 점검

Pilot 결과를 바탕으로 바로 다음 안정화 작업을 수행했다.

### 8.1 수행한 안정화 작업

1. **WFO 요약 정보 보강**
   - `zero_trade_rounds`
   - `trade_count_rounds`
   - `mean_trade_count`
   를 summary에 포함하도록 보강했다.

2. **promotion 평가 보강**
   - 모든 round에서 거래가 0건이면
     `all_rounds_no_trades`
     사유가 평가 결과에 남도록 수정했다.

3. **discovery report 가시성 개선**
   - 생성된 candidate expression 목록을 report에 포함했다.
   - Markdown report에 `Candidate Expressions` 섹션을 추가했다.

4. **runner 중단 안정화**
   - 실제 promote 재시도 중 `Ctrl+C` / timeout 계열 종료 상황에서
     `cli.runner._cleanup_procs()`가
     `AssertionError: can only test a child process`
     로 깨지는 문제를 발견했다.
   - foreign process/parent mismatch 상황에서는 cleanup이 예외를 삼키고
     계속 진행하도록 수정했다.

### 8.2 TDD 관점에서 이번 안정화 작업이 어떻게 진행되었는가

이번 안정화 작업은 **테스트를 먼저 추가한 뒤 구현을 수정하는 방식**으로 진행했다.

적용한 테스트:

- `tests/unit/test_wfo.py`
  - zero-trade round 집계 검증
- `tests/unit/test_ai_controller.py`
  - 모든 round 무거래 시 `all_rounds_no_trades` 사유 검증
- `tests/unit/test_discovery_report.py`
  - expression/report 섹션 추가 검증
- `tests/unit/test_runner_helpers.py`
  - foreign process cleanup 시 `AssertionError`를 삼키는지 검증

실행 흐름:

1. 테스트 추가
2. 실패 확인
3. 구현 수정
4. 관련 단위 테스트 재실행 통과 확인

따라서 **이번 턴의 안정화 작업 자체는 TDD 흐름에 가깝게 수행되었다**고 볼 수 있다.

다만 프로젝트 전체 히스토리 기준으로는,
기존 기능 개발 커밋들이 항상 엄격한 red → green → refactor 형태였다는
증거까지 확보되지는 않았다.
즉, **전체 프로젝트가 엄격한 TDD로 일관되게 개발되었다고 단정하기는 어렵고,
이번 안정화 작업은 TDD 방식으로 보강되었다**가 더 정확한 표현이다.

### 8.3 2차 promote 재시도 결과

다음과 같은 더 약한 조건으로 promote를 재시도했다.

- 입력 CSV: `temp/pilot_slice_20250407_20250418.csv`
- `top-n=1`
- `ml_feature_limit=0`
- `ml_weight=0.0`
- `promotion_preset=aggressive`
- `engine_count=1`

관찰 결과:

- 실제 WFO/runner 경로는 다시 시작되었다.
- 그러나 실행 시간이 여전히 길었고,
  중단 시 cleanup 경로에서 parent/child mismatch 예외가 발생하는 운영 문제를 확인했다.
- 위 문제는 이번 턴에서 수정했다.
- 그럼에도 `shared_memory` warning은 여전히 관찰되었고,
  최종 promoted 성공 사례는 확보하지 못했다.

### 8.4 readiness 최종 판단

현재 시스템은 아래 수준까지는 도달했다.

1. 자동 조건식 후보 생성 가능
2. ML 기반 feature ranking 가능
3. strategy 저장 가능
4. WFO 기반 promotion 판정 가능
5. JSON / Markdown report 생성 가능
6. no-trade / cleanup 관측성을 이전보다 더 잘 제공

하지만 아직 아래 문제 때문에
**“실전 채택 성공까지 가능하도록 시스템이 완성되었다”**고 보기는 어렵다.

#### 아직 부족한 점

1. **실제 promoted 성공 사례 부재**
   - 현재 pilot에서는 end-to-end로 최종 채택된 전략을 확보하지 못했다.

2. **candidate 강도 자동 튜닝 부재**
   - `top-n`, `ml_feature_limit`, `ml_weight`, `preset`
     조합을 자동 탐색해
     “거래가 살아있는 후보”를 찾는 기능이 아직 없다.

3. **runner cleanup 완전 안정화 미완료**
   - parent/child mismatch 예외는 완화했지만
     `shared_memory` warning은 남아 있다.

4. **no-trade promotion의 운영 품질 미완성**
   - 지금은 no-trade 원인을 더 잘 설명할 수 있게 되었지만,
     실전 채택 판단을 자동으로 재시도/완화하는 orchestration은 없다.

### 8.5 현재 시점의 결론

정리하면:

- **기능적 연결성**: 충분히 확보됨
- **TDD 기반 안정화 보강**: 이번 턴 기준으로 수행됨
- **실전 채택 성공 가능성**: 아직 검증 부족
- **시스템 완성 판정**: 아직 아님

즉 현재 시스템은
**“자동 조건식 탐색 파일럿 플랫폼”으로는 상당히 진전됐지만,
실전에서 반복적으로 채택 가능한 전략을 안정적으로 뽑아내는 완성형 시스템”이라고 보기는 아직 이르다.**
