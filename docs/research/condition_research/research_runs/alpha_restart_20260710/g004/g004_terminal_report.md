# G004 terminal dependency closure 보고

## 최종 판정

- experiment_id: `alpha_restart_20260710-g004`
- terminal_decision: `UNDETERMINED`
- terminal_stage: `dependency_closure`
- repository HEAD: `cfe5f4ab283bd5bfaf9301d04fc2c2879ccc3986`

G004는 통계적 음성 판정이 아니라 **의존성 비식별(dependency nonidentification)** 로 종결한다. G004의 P1/M1/S1 진단은 G002가 만들기로 한 동일 `common cohort`를 전제로 한다. 그러나 G002의 유일한 canonical identity-only commitment는 `identity_projection` 단계에서 실패했고, 그 실패는 identity crosswalk, design marker, materialized input, full attempt, receipt, claim, result, outcome보다 앞서 발생했다.

따라서 G004에는 식별된 공통 분모, estimand, 실행 호출이 없다. `KILL`/`PASS`는 평가하지 않는다. 재시도, rescue 분석, 대체 cohort 제조도 수행하지 않는다.

## G002 의존성 증거 바인딩

- G002 terminal report: `docs/research/condition_research/research_runs/alpha_restart_20260710/g002/g002_u7_f0_terminal_report.md`
  - sha256: `fdbffdcd66269f8fc5cc6feef3e0663c191cb2532ada5c52b937c2cf1d813552`
- G002 terminal evidence: `docs/research/condition_research/research_runs/alpha_restart_20260710/g002/g002_identity_failure_evidence.json`
  - sha256: `abce305b4d1397a2e7c11f878c6ee661f0412ac0ee4f4c84317278d9954cd712`
- G002 identity attempt: `docs/research/condition_research/research_runs/alpha_restart_20260710/g002/identity_attempt.json`
  - sha256: `b178ccdc0498dff171bb9c73a1f08186c5089507c785b8a4a28bce3aa537c1cc`
  - state: `reserved`
- G002 identity status: `docs/research/condition_research/research_runs/alpha_restart_20260710/g002/identity_status.json`
  - sha256: `0e43be2f1092c75e15d0a40e4fb7ef66b0ca07aae25e3179b607bf07aa5dbd50`
  - state: `failed`

G004가 상속해야 할 아래 dependency artifact는 없다.

```text
identity_crosswalk.json
identity_design_marker.json
materialization_attempt.json
materialization_status.json
u7_f0_materialized_input.json
seal
receipt
claim
result
```

## P1/M1/S1 식별 상태

| 항목 | identified | 필요한데 없는 전제 | 판정 상태 |
|---|---:|---|---|
| P1 Path Surface | `false` | common denominator, path/exit outcomes | `KILL`/`PASS` 미평가 |
| M1 Missingness Bounds | `false` | match/exclusion partition, outcome support | `KILL`/`PASS` 미평가 |
| S1 Sparse Fragility | `false` | exact common cohort, code/day/week cluster contribution table | `KILL`/`PASS` 미평가 |

P1의 path band, M1의 missingness bound, S1의 fragility statistic은 산출하지 않는다. 공통 cohort가 없으므로 후보, live claim, 수치 outcome claim도 없다.

## 부작용 및 원장 상태

G004 invocation은 `0`이다. G002 terminal evidence에서 상속되는 부작용 counter와 G004 closure의 추가 counter는 모두 `0`으로 유지된다.

- engine: `0`
- db_writes: `0`
- registration: `0`
- promotion: `0`
- full_attempt: `0`
- target_runs: `0`
- outcome_computations: `0`
- n_trials rows appended: `0`

G004 estimand와 invocation이 없으므로 G004 사전등록 또는 측정 receipt는 생성하지 않는다. receipt 또는 claim도 만들지 않았다.

보존된 금지사항: G002 rerun 없음, fabricated cohort 없음, engine/DB write 없음, registration/promotion 없음, 2024+ 선택 없음.

## 감사 출처

다음 문서는 판단 출처로만 참조한다. `.gjc` 경로는 hash를 기록하지 않는다.

- agenda: `docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md`
- n_trials ledger: `docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl`
- durable goals: `.gjc/_session-019f6093-0be6-7000-b496-a9b6b2305f30/ultragoal/goals.json`
- durable ledger: `.gjc/_session-019f6093-0be6-7000-b496-a9b6b2305f30/ultragoal/ledger.jsonl`

## 종결 문구

G004는 의존성 비식별 때문에 `UNDETERMINED`로 terminal closure한다. 이는 통계적 `KILL`도 성공 `PASS`도 아니며, 누락된 G002 common cohort를 제조하거나 rescue 분석으로 대체하지 않는다.
