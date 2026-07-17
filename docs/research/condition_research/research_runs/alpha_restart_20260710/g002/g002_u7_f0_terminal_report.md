# G002 U7-F0 identity terminal failure 보고

## 판정

G002 U7-F0의 유일한 canonical identity-only commitment는 `identity_projection` 단계에서 실패했다. 최종 판정은 **UNDETERMINED**이다. SEALED 사전등록은 identity-only commitment를 정확히 한 번만 허용하고 retry, rerun, variant 및 rescue run을 금지한다. 따라서 이 실패는 재실행으로 고칠 일이 아니라, estimand 구성 전에 닫힌 유효한 terminal integrity failure다.

- experiment: `alpha_restart_20260710-g002`
- identity attempt: `alpha_restart_20260710-g002-identity-attempt-001` — `reserved`
- full attempt: `alpha_restart_20260710-g002-attempt-001` — 생성되지 않음
- canonical module invocation exit: `1`
- exception: `ValueError: timestamp must be an exact integer or digit string`
- repository HEAD: `6bf93002aeda356da66c68ded322a2b83b7a0efd`

정확한 canonical 명령은 다음과 같다.

```text
python -m scripts.u7_f0_materialize --ledger docs/research/condition_research/research_runs/alpha_lab_20260705/distill/champion_ledger.jsonl --l3 C:/System_Trading/STOM/STOM_V.wt-alpha/docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet --d1-bits docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet --tick-db C:/System_Trading/STOM/STOM_V.wt-alpha/_database/stock_tick_back.db --evidence docs/research/condition_research/research_runs/alpha_restart_20260710/g002/materialization_launch.json --identity-output docs/research/condition_research/research_runs/alpha_restart_20260710/g002/identity_crosswalk.json --design-marker docs/research/condition_research/research_runs/alpha_restart_20260710/g002/identity_design_marker.json --identity-only
```

앞선 direct-script 명령은 import 단계에서 main 진입 전에 실패했고 어떤 artifact도 만들지 않았다. 이는 canonical attempt가 아니다. 이후의 module invocation만이 canonical 명령이었으며, identity attempt를 reserve한 뒤 실패 status를 기록했다.

## 확인된 원인과 범위

Champion ledger JSON은 파싱되었고 전체 671행 중 고정 cohort 298행이 선택되었다. 첫 선택 행에서 `진입시각='090127'`은 정확한 digit identity였지만 `매수시간=20220323090127.0`은 float였다. 구현은 buy timestamp 후보로 `buy_timestamp`, `buy_time`, `매수시간` 순서를 사용한다. 이 구현은 float `매수시간`을 선택하고 `_timestamp`가 이를 거부한다. `진입시각`은 후보 또는 fallback에 포함되지 않아 전혀 고려되지 않는다.

Tick DB는 query-only로 열어 첫 code/day resolution만 수행했다. 보호 DB는 source authority와 동일한 SHA-256 및 크기로 재확인되었고 `-wal`, `-shm`, `-journal` sidecar가 없다. 외부 L3 read path와 local D1 및 나머지 authority source도 authority SHA-256/크기와 재해시 값의 일치를 확인했다. 상세 경로·hash·부재 artifact 목록은 `g002_identity_failure_evidence.json`에 있다.

실패는 identity crosswalk, L3/D1 row materialization, factorial, full attempt, target, bootstrap 및 result보다 앞서 발생했다. 따라서 paired-factorial estimand나 그 추정치를 주장하지 않는다. outcome 수치도 이 보고서에 포함하지 않는다.

## 부작용 및 후속 권한

engine, DB write, registration, promotion, full attempt, target run 및 outcome computation은 모두 0이다. candidate도 없고 promotion도 없다. crosswalk, design marker, full attempt/status, materialized input, seal, receipt, claim, result는 존재하지 않는다. receipt 또는 claim을 만들어 내지 않았다.

`n_trials` v2 연구 ledger에는 append하지 않았다. receipt, claim 또는 materialized estimand가 없고 v1 writer는 retire되었으므로, 행을 제조하는 것은 G008을 위반한다. 이 terminal failure의 durable audit trail은 Ultragoal ledger/checkpoint와 본 evidence/report 두 파일이다.

가능한 remediation은 이 SEALED attempt의 재시도나 수정이 아니다. 장래에만 새 preregistration과 새 attempt ID를 통해 별도로 권한화될 수 있으며, 본 기록은 그 실행을 승인하지 않는다.
