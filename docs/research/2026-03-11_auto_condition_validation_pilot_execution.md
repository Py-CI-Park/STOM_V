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

---

## 9. 3차 promote 재실행 (auto-relax 적용 후) 결과

2차 안정화 작업에서 `auto_relax`가 controller/report 수준에 구현된 뒤,
실제 promoted 성공 사례를 확보하기 위해 promote를 다시 재실행했다.

### 9.1 재실행 목표

이번 재실행의 목표는 아래 2가지였다.

1. `auto_relax_history`가 실제 promote 실행 결과에 남는지 확인
2. `promoted=True`가 되는 실제 조합을 최소 1건 확보

### 9.2 1차 재실행 — slice 기반, auto-relax 활성

설정:

- 입력 CSV: `temp/pilot_slice_20250407_20250418.csv`
- 시작/종료일: `2025-04-07 ~ 2025-04-11`
- `train_window_days=3`
- `test_window_days=1`
- `step_days=3`
- `top_n=3`
- `auto_relax=True`
- `max_relax_steps=2`
- `promotion_preset=aggressive`
- `engine_count=1`

요약 결과:

```json
{
  "status": "ok",
  "promoted": false,
  "auto_relax_history": [
    {"step": 0, "top_n": 3, "zero_trade_rounds": 0, "total_rounds": 1}
  ],
  "promotion_reasons": ["mean_oos_metric<-0.1"],
  "wf_summary": {
    "round_count": 1,
    "success_count": 1,
    "success_rate": 1.0,
    "mean_oos_metric": null,
    "trade_count_rounds": 0,
    "zero_trade_rounds": 0
  }
}
```

산출물:

- `temp/Auto_B_PilotSuccess_1773386515_report.json`
- `temp/Auto_B_PilotSuccess_1773386515_report.md`

해석:

- auto-relax 이력은 실제로 결과에 남았다.
- 하지만 이번 케이스는 `zero_trade_rounds == 0`으로 기록되면서도
  `mean_oos_metric == null`, `trade_count_rounds == 0`이었다.
- 즉 현재 no-trade 감지가 **trade_count가 아예 생성되지 않는 test_result** 케이스를
  완전히 포착하지 못하고 있을 가능성이 드러났다.
- 결과적으로 `auto_relax`가 재시도까지 가지 못했고,
  `promoted=True`도 확보하지 못했다.

### 9.3 2차 재실행 — full-range 입력 기반, 짧은 검증 구간

설정:

- 입력 CSV: `backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv`
- 시작/종료일: `2025-04-07 ~ 2025-04-11`
- `train_window_days=3`
- `test_window_days=2`
- `step_days=3`
- `top_n=1`
- `auto_relax=True`
- `max_relax_steps=0`
- `promotion_preset=aggressive`
- `engine_count=1`

관찰 결과:

- 백테스트 엔진 재실행 과정에서 아래 예외가 발생했다.

```text
FileExistsError: [Errno 17] File exists: '/backdata_0'
```

발생 위치:

- `backtest/backengine_base.py`
- `shared_memory.SharedMemory(name=name, create=True, size=total_size)`

해석:

- 기존에 관찰되던 `shared_memory` cleanup warning이
  이번에는 실제 재실행 차단 예외로 드러났다.
- 즉 현재 단계에서는 **shared_memory 정리 문제가 단순 warning 수준이 아니라,
  반복 promote 탐색을 방해하는 실질적 blocker**임이 확인되었다.

### 9.4 추가 관찰

별도 확인 차원에서,
full-range CSV 기반 top-1 전략을 strategy.db에 저장한 뒤
단일 일자 백테스트를 실행해 보았으나,
프로세스가 정상 종료되지 않고 다수의 하위 프로세스가 남는 현상을 확인했다.

이 관찰은 아래 가능성을 시사한다.

1. 단일/초단기 구간 실행에서 runner 종료 조건이 취약할 수 있음
2. shared memory / subprocess 정리 경로가 여전히 불안정함
3. 실전 promoted 성공 사례 확보 전, cleanup 안정화가 먼저 필요할 수 있음

### 9.5 이번 재실행 단계의 결론

이번 단계에서 확인된 사실은 다음과 같다.

1. `auto_relax` 구현 자체는 결과 이력을 남기는 수준까지 동작한다.
2. 하지만 no-trade 감지가 아직 완전하지 않다.
   - `trade_count_rounds == 0`
   - `mean_oos_metric == null`
   - `zero_trade_rounds == 0`
   조합이 실제로 발생했다.
3. 반복 promote 탐색 중 `FileExistsError('/backdata_0')`가 발생해
   shared memory cleanup 문제가 실제 blocker로 승격되었다.
4. 따라서 **현재 최우선 과제는 promoted 성공 사례 탐색 자체보다,
   no-trade 판정 보강 + shared memory cleanup 안정화**로 재정렬할 필요가 있다.

### 9.6 다음 우선순위 조정

기존 계획에서는 다음 단계가
“promoted 성공 조합 찾기”였지만,
이번 재실행 결과를 반영하면 실제 우선순위는 아래처럼 바뀐다.

1. `trade_count_rounds == 0` / `mean_oos_metric is None` 케이스를
   no-trade로 간주하도록 promotion 평가 보강
2. `shared_memory` 재사용 충돌(`FileExistsError: /backdata_0`) 원인 분석 및 정리 경로 수정
3. 그 다음에 다시 promote 성공 조합 탐색 재개

---

## 10. 4차 보강 — no-trade 판정 / shared_memory cleanup 수정 및 재검증

9장의 blocker를 바탕으로, 다음 두 가지를 우선 수정했다.

### 10.1 적용한 수정

1. **no-trade 판정 보강**
   - `run_walk_forward()`에서
     `status='success'`이지만 metrics가 비어 있고
     메시지가 `결과 테이블이 비어있습니다`인 경우를
     `trade_count=0` 라운드로 간주하도록 보강했다.
   - `evaluate_walk_forward_result()`에서도
     동일 패턴을 추론해
     `all_rounds_no_trades`로 판정할 수 있게 수정했다.

2. **shared_memory cleanup 보강**
   - `backtest/backengine_base.py`에서
     stale shared memory 이름(`backdata_{gubun}`)이 남아 있으면
     새 생성 전에 정리하도록 수정했다.
   - 엔진 종료/중지 경로에서
     `close() + unlink()` 기반 정리 루틴을 추가했다.

### 10.2 TDD 기반 보강

이번 수정은 테스트를 먼저 추가한 뒤 구현을 수정하는 방식으로 진행했다.

추가/보강한 테스트:

- `tests/unit/test_wfo.py`
  - metrics 없는 success 결과를 zero-trade round로 집계하는지 검증
- `tests/unit/test_ai_controller.py`
  - `mean_oos_metric is None`, `trade_count_rounds == 0` 케이스를
    `all_rounds_no_trades`로 판정하는지 검증
- `tests/unit/test_backengine_shared_memory_cleanup.py`
  - `backengine_base.py`에 shared memory unlink 경로가 존재하는지 검증

검증 결과:

- 관련 회귀 집합: **17 passed**

### 10.3 수정 후 재실행 관찰

slice 기반 promote를 다시 재실행했을 때,
이전과 달리 첫 번째 no-trade 이후 실제로 다음 시도가 이어지는 것을 확인했다.
즉, **auto-relax가 no-trade를 더 잘 감지하고 재시도에 들어가는 방향으로 개선**되었다.

또한 이전에 관찰된
`FileExistsError: '/backdata_0'`
는 같은 형태로 즉시 재현되지는 않았다.

다만,
세 번째 시도 구간에서 프로세스가 예상보다 길게 머무르는 현상이 남아 있어,
shared memory 충돌은 완화되었지만
**반복 promote 탐색의 완전 안정화가 끝났다고 보기는 아직 어렵다.**

### 10.4 현재 판단

이번 보강으로 아래는 개선되었다.

1. no-trade 판정 정확도
2. auto-relax 재시도 진입 가능성
3. stale shared memory 이름 충돌 가능성

하지만 아직 아래는 남아 있다.

1. `promoted=True` 실제 성공 사례 미확보
2. 반복 promote 탐색 시 long-running/hang 가능성
3. 운영 관점의 완전한 종료 안정성 검증 부족

### 10.5 다음 우선순위

현재 시점의 다음 우선순위는 아래 순서가 적절하다.

1. **짧은 구간/단일 round 위주로 promote 성공 조합 재탐색**
2. 성공 사례 확보 후 report/parameter baseline 고정
3. 그 다음 `analyzer.py`, `ml_factor_model.py` 테스트 보강 재개
