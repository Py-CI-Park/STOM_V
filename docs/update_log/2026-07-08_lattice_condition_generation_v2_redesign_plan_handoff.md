# 2026-07-08 Lattice / Condition-Generation V2 Redesign Plan Handoff

작성시각: 2026-07-07 22:55 KST

## 1. 이번 작업 범위

사용자 요청:

```text
$ulw-loop 내일 아침 까지 재설계 계획
```

이번 작업은 실제 재설계 실행이 아니라, 내일 아침까지 이어갈 수 있는 lattice/condition-generation v2 재설계 계획과 ULW evidence를 만드는 범위로 제한했다.

## 2. 생성한 ULW 세션

| item | value |
|---|---|
| session_id | `20260708_lattice_generation_v2_redesign_plan` |
| goal_id | `G001-one-goal-only-by-2026-07-08-06-50-ks` |
| plan | `.omo/ulw-loop/20260708_lattice_generation_v2_redesign_plan/goals.json` |
| ledger | `.omo/ulw-loop/20260708_lattice_generation_v2_redesign_plan/ledger.jsonl` |

주의:

기존 Codex goal이 `paused` 상태로 남아 있어 `create_goal`/`checkpoint complete`까지는 정상 사용하지 않았다. ULW evidence와 git commit으로 추적한다.

## 3. Source Read

Source receipt:

- `.omo/ulw-loop/evidence/20260708_lattice_generation_v2_redesign_plan/C001_source_read_and_synthesis.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_redesign_source_receipt_20260708.json`

핵심 입력:

- `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`
- `docs/update_log/2026-07-08_plan_d_rank03_r2_selected_oos_closeout_handoff.md`
- tick/min 288 official summaries
- 576 deep analysis
- repair composite OOS result
- `seed_pool.jsonl`
- `oos_survivors.jsonl`
- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

## 4. 재설계 계획

Main plan:

- `docs/research/condition_research/plans/2026-07-08_lattice_condition_generation_v2_redesign_plan.md`
- `.omo/plans/lattice-condition-generation-v2-redesign-overnight-20260708.md`

핵심 결론:

- 같은 576 lattice를 반복하지 않는다.
- tick lane은 diagnostic/stress로 낮춘다.
- min/composite/coverage 중심으로 V2 axis를 설계한다.
- fully blind split 또는 walk-forward 경계를 먼저 고정한다.
- Plan D survivor seed는 promotion 근거가 아니라 generation v2 설계 입력이다.

## 5. 내일 아침까지 추천 범위

권장 범위는 `redesign-plan-only-until-20260708-0650-KST`다.

허용:

- failure map 재분해
- seed lineage audit
- V2 axis spec
- evaluation boundary
- candidate class quota
- static/dry-run-only 다음 명령어 작성
- handoff/commit

금지:

- full tick/min 288
- OOS
- portfolio
- export/live/final
- Plan D R3
- DB UPDATE/DELETE
- DB INSERT apply
- 새 조건식 코드 생성

## 6. 다음 추천 명령어

```text
$ulw-loop .omo/plans/lattice-condition-generation-v2-redesign-overnight-20260708.md

범위는 redesign-plan-only-until-20260708-0650-KST까지만 진행한다.
목표는 기존 576 lattice 실패와 repair composite/Plan D survivor seed를 바탕으로
lattice/condition-generation v2 재설계 계획과 다음 실행 명령어를 완성하는 것이다.

금지:
- full tick 288 실행 금지
- full min 288 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- Plan D R3 자동 진행 금지
- DB UPDATE/DELETE 금지
- DB INSERT apply 금지
- 새 조건식 코드 생성 금지
- git add -A 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 stage 금지
```

## 7. 다음 판단

이 계획이 완료된 뒤에도 바로 backtest로 가면 안 된다. 다음 단계는 `candidate generation dry-run only`가 맞다.

후속 단계의 순서:

1. V2 axis spec 확정
2. 후보명/lineage/passport 설계
3. strategy/rules 기준 static syntax 검토
4. DB registration dry-run
5. dry-run 검증 후 사용자 승인 시 INSERT-only apply 검토
6. 그 후에만 limited preflight 검토
