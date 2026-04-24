# Wide v1 v5 actual row-set 선택 판정

## 결론

```text
Decision: HOLD_V5_RUNTIME_FAILURE
```

v5 `candidate_count=10` 실제 실행은 완료되지 않았다. 따라서 actual row-set 대표 10개 확보 여부를 판정할 수 없다.

## 실행 요약

- preflight: 성공
- v5 실행 시작: `2026-04-24 22:53:03 KST`
- v5 실행 정리: `2026-04-25 06:30 KST` 이후 수동 프로세스 정리
- runtime JSON: 생성되지 않음
- 생성된 candidate CSV: 7개
- 누락 candidate: `cand007`
- 마지막 생성 candidate: `cand008`

## 생성된 candidate CSV

| candidate | 상태 | CSV 생성 시각 |
| --- | --- | --- |
| cand001 | generated | 2026-04-24 22:55:21 |
| cand002 | generated | 2026-04-24 22:57:36 |
| cand003 | generated | 2026-04-24 23:00:04 |
| cand004 | generated | 2026-04-24 23:02:44 |
| cand005 | generated | 2026-04-24 23:05:29 |
| cand006 | generated | 2026-04-24 23:08:03 |
| cand007 | missing | 없음 |
| cand008 | generated | 2026-04-25 06:22:00 |

## actual row-set 판정

actual row-set 판정은 보류한다.

이유:

- `backtest\temp\wide_v1_iteration_v5_20260424.json` 파일이 생성되지 않았다.
- `actual_rowset_selection` payload가 없다.
- `selected_count`, `requested_count`, `row_set_identity_status`, `duplicate_actual_rowset_count`를 검증할 수 없다.
- partial CSV 7개만으로 v5 selector의 row-set 대표성 또는 후보 10개 충족 여부를 판단하면 연구 기준이 흔들린다.

## 원인 가설

현재 증거상 원인은 조건식 품질이 아니라 CLI runtime 안정성이다.

- 개별 candidate backtest가 중간에 지연 또는 timeout 상태에 들어갔다.
- `candidate_timeout=900` 설정에도 nested worker cleanup이 즉시 완료되지 않은 것으로 보인다.
- shell/tool timeout 이후 stdout 기반 `Tee-Object` capture가 끊기면서 최종 runtime JSON을 확보하지 못했다.
- 장시간 실행 중 candidate별 checkpoint가 없어서 partial result를 구조적으로 복구할 수 없다.

## 다음 의사결정

promote/WFO로 진행하지 않는다.

v6 조건식 생성 확장으로도 바로 진행하지 않는다. actual row-set 다양성 부족이 확인된 것이 아니기 때문이다.

먼저 v5 runtime failure recovery를 설계하고, 다음 조건을 만족한 뒤 v5를 재실행한다.

- `discovery research`에 명시적 runtime output file 저장 경로 제공
- candidate별 checkpoint 저장
- candidate timeout 시 nested worker까지 cleanup
- partial run 발생 시 실패 보고서 자동 생성
- 작은 candidate_count smoke로 timeout cleanup 검증

## 다음 추천 명령

```text
$brainstorming Wide v1 v5 runtime failure recovery 설계
```

