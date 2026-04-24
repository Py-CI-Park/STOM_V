# PR 보고서: Wide v1 v5 candidate_count=10 실제 실행 및 actual row-set 검증

## 1. 목적

Wide v1 v5에서 `best_feature_mix_v5` 후보 생성 흐름이 실제 백테스트 CSV 기준으로 서로 다른 actual row-set 대표 10개를 만들 수 있는지 검증하려고 했다.

이번 PR의 목적은 성과가 좋은 조건식을 확정하는 것이 아니라, v5 실행 결과를 재현 가능한 문서로 남기고 다음 단계 판단을 명확히 하는 것이다.

## 2. 전체 계획

전체 Wide v1 흐름은 다음 순서다.

```text
v1: 최초 Wide 조건 후보 생성 및 백테스트 기준 확보
v2: best candidate 기준 조건식 재생성
v3: 조건식 후보 다양화 및 tie-break 판단
v4: proxy row-set 기준 후보 다양성 확보
v5: 실제 백테스트 CSV actual row-set 기준 대표 후보 선택
promote/WFO: v5 대표 후보가 검증된 경우에만 승격 검증
```

v5는 v4의 proxy 다양성이 실제 체결 row-set 다양성으로 이어지는지 확인하는 단계다. 따라서 v5가 통과하려면 단순히 후보 CSV가 생성되는 것만으로 부족하고, runtime JSON의 `actual_rowset_selection` 결과가 확인되어야 한다.

## 3. 현재 계획

이번 실행 계획은 다음과 같았다.

```text
1. v4와 같은 입력 CSV, score reference CSV, base expression을 고정한다.
2. best_feature_mix_v5로 후보 실행 pool을 만든다.
3. candidate_count=10을 요청한다.
4. oversampled candidate 실행 후 actual row-set 대표를 고른다.
5. selected_count=10, row_set_identity_status=all_distinct이면 promote/WFO 계획으로 이동한다.
6. 실행 실패 또는 shortfall이면 원인별 hold branch로 이동한다.
```

## 4. 실행 입력

- branch: `feature/wide-v1-v5-candidate-count-10-runtime-validation`
- mode: `best_feature_mix_v5`
- candidate_count: `10`
- candidate_pool_multiplier: `3`
- candidate_timeout: `900`
- timeframe: `tick`
- engines: `32`
- period: `20250101` - `20251231`
- time window: `090000` - `092800`
- base buy strategy: `WideV1IterationV2_20260423__cand005`
- sell strategy: `ResearchTest_Tick_S_090000_092800_Wide_20260419`

## 5. 실행 결과

preflight는 통과했다.

```text
status=ok
failed_checks=[]
validation_errors=[]
```

그러나 v5 본 실행은 완료되지 않았다.

- 실행 시작: `2026-04-24 22:53:03 KST`
- `cand001` - `cand006` CSV 생성
- `cand007` CSV 미생성
- `cand008` CSV 생성: `2026-04-25 06:22:00 KST`
- 이후 10분 이상 parent/worker CPU와 CSV 수정 시간 변화 없음
- runtime JSON 미생성
- 잔여 v5 multiprocessing worker 정리

## 6. actual row-set 선택 결과

actual row-set 결과는 판정 불가다.

```text
Decision: HOLD_V5_RUNTIME_FAILURE
```

이 판정은 v5 조건식 생성 방식이 실패했다는 뜻이 아니다. `actual_rowset_selection`을 담은 완료 runtime JSON이 없으므로, v5 후보 10개의 실제 row-set 대표성을 검증할 수 없다는 뜻이다.

## 7. 퀀트 트레이더 관점 검토

이 상태에서 promote/WFO로 가면 안 된다.

partial candidate CSV만 보고 성능을 평가하면 survivorship bias와 실행 편향이 생긴다. 특히 `cand007`이 누락되고 `cand008`만 뒤늦게 생성된 상태에서는 후보 순서, timeout, actual row-set 선택이 모두 불완전하다.

따라서 지금의 문제는 전략 조건식 개선 문제가 아니라 검증 인프라 문제로 분류하는 것이 맞다.

## 8. CLI 개발 전문가 관점 검토

현재 CLI 연구 루프는 장시간 실행 실패를 완전히 견디지 못한다.

보강해야 할 부분:

- `discovery research` 결과를 stdout capture에만 의존하지 않고 명시적 output path로 저장
- candidate별 checkpoint 저장
- candidate timeout 시 nested multiprocessing worker cleanup 보장
- partial run 발생 시 구조화된 실패 runtime JSON 생성
- 장시간 실행 재개 또는 최소한 실패 원인 재현 가능성 확보

## 9. 변경 파일

- `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v5.md`
- `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v5_actual_rowset_selection.md`
- `docs/pr/2026-04-24_wide_v1_v5_candidate_count_10_actual_rowset_validation_pr.md`

백테스트 산출물은 staging하지 않는다.

## 10. 검증

실행 검증:

- `runtime-preflight` 통과
- v5 실행 프로세스 command line 확인
- 생성 candidate CSV 7개 확인
- runtime JSON 부재 확인
- 10분 이상 CPU/file 변화 없음 확인
- v5 잔여 프로세스 정리 확인

문서 검증:

- focused unit tests 실행 예정
- whitespace diff check 실행 예정
- markdown 문서만 explicit staging 예정

## 11. 다음 단계

추천 다음 브랜치:

```text
feature/wide-v1-v5-runtime-failure-recovery
```

추천 다음 명령:

```text
$brainstorming Wide v1 v5 runtime failure recovery 설계
```

이 다음 단계가 타당한 이유는 actual row-set 다양성 부족이 아직 확인되지 않았기 때문이다. v6 조건식 확장보다 먼저 v5 실행 안정성을 확보해야 이후 결과를 신뢰할 수 있다.

