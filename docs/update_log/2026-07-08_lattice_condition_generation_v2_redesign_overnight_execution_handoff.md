# 2026-07-08 Lattice / Condition Generation V2 Redesign Overnight Execution Handoff

작성시각: 2026-07-08 10:02 KST

## 1. 이번 작업 목적

이번 작업은 백테스트를 더 돌리는 것이 아니라, 기존 576 lattice 실패를 바탕으로 조건식 생성 v2 설계를 실제 실행 가능한 산출물로 정리하는 것이다.

## 2. 완료한 페이지

| page | 결과 | 산출물 |
|---|---|---|
| T0 | 완료 | source receipt |
| T1 | 완료 | failure map |
| T2 | 완료 | seed lineage audit |
| T3 | 완료 | v2 axis spec |
| T4 | 완료 | evaluation protocol |
| T5 | 완료 | candidate quota ledger |
| T6 | 완료 | static/dry-run-only next command |
| T7 | C002에서 검증 | boundary guard receipt |
| T8 | C003/커밋에서 완료 | final verification + Korean commit |

## 3. 핵심 결론

- 기존 tick 288은 discovery lane으로 쓰지 않는다. tick은 stress/diagnostic/negative-control로 낮춘다.
- 기존 min 288은 gate 통과는 0이지만 sparse positive + low-MDD fragment가 있으므로 v2의 primary redesign lane으로 둔다.
- 576 lattice를 같은 구조로 반복하지 않는다.
- repair composite와 Plan D survivor는 promotion 근거가 아니라 seed lineage input과 benchmark로만 사용한다.
- 다음 단계는 candidate generation static/dry-run only이며, DB INSERT apply와 replay/OOS는 열지 않는다.

## 4. 주요 산출물

- `docs/research/condition_research/plans/lattice_condition_generation_v2_failure_map_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_seed_lineage_audit_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_axis_spec_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_evaluation_protocol_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_candidate_quota_ledger_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_static_dryrun_next_command_20260708.md`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_candidate_dryrun_20260708.md`

## 5. 다음 명령어

```text
$ulw-loop docs/research/condition_research/plans/lattice_condition_generation_v2_candidate_dryrun_20260708.md
```

해당 plan 파일은 이미 작성되어 있으며, 범위는 static gate + DB registration dry-run only로 제한되어 있다.
