# Lattice / Condition-Generation V2 Redesign Overnight Plan

작성시각: 2026-07-07 23:05 KST

## 목적

2026-07-08 06:50 KST까지 기존 576 lattice 실패와 repair composite / Plan D survivor 결과를 바탕으로 조건식 생성 v2 재설계 산출물을 완성한다.

이번 범위는 실행 계획 수립과 증빙 정리까지만이다. backtest, DB INSERT apply, OOS, portfolio, Plan D R3, export/live/final promotion은 실행하지 않는다.

## 기준 문서

- `docs/research/condition_research/plans/2026-07-08_lattice_condition_generation_v2_redesign_plan.md`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_redesign_source_receipt_20260708.json`
- `docs/update_log/2026-07-08_lattice_condition_generation_v2_redesign_plan_handoff.md`

## 반드시 먼저 읽을 문서

- `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`
- `docs/update_log/2026-07-08_plan_d_rank03_r2_selected_oos_closeout_handoff.md`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_overnight_20260705/overnight_no_d_576_deep_analysis_20260705.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`
- `docs/research/condition_research/generated_conditions/seed_pool.jsonl`
- `docs/research/condition_research/generated_conditions/oos_survivors.jsonl`
- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

## 진행 페이지

| page | 목적 | 산출물 | 예상 |
|---|---|---|---:|
| T0 | source receipt 재확인 | SHA/line count/source map | 10~20m |
| T1 | 576 failure map 재분해 | discard/keep axis ledger | 40~60m |
| T2 | seed_pool lineage audit | lineage diversity table | 30~60m |
| T3 | V2 axis spec 작성 | axis spec JSON/MD | 60~90m |
| T4 | blind split / WF boundary 설계 | evaluation protocol JSON/MD | 60~90m |
| T5 | candidate class quota 설계 | quota ledger | 40~60m |
| T6 | static/dry-run-only 다음 명령 설계 | execution command draft | 30~45m |
| T7 | adversarial boundary review | no-execution proof | 30~45m |
| T8 | handoff / commit | update_log, ULW evidence, Korean commit | 30~60m |

총 예상: 5~7시간.

## 설계 방향

1. 기존 576 lattice를 재실행하지 않는다.
2. tick lane은 discovery가 아니라 stress/diagnostic으로 낮춘다.
3. min / composite / coverage 중심으로 v2 axis를 설계한다.
4. repair composite 15/16 survivor와 Plan D R2-05는 promotion 근거가 아니라 seed-lineage 입력과 benchmark로만 쓴다.
5. fully blind split 또는 walk-forward 경계를 먼저 고정한다.
6. 다음 단계 후보 생성은 static gate와 DB registration dry-run까지만 허용한다.

## 금지

- full tick 288 실행 금지
- full min 288 실행 금지
- limited replay 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- Plan D R3 자동 진행 금지
- export/live/final promotion 금지
- DB INSERT apply 금지
- DB UPDATE/DELETE 금지
- 새 STOM 조건식 코드 생성 금지
- `git add -A` 금지
- dashboard 7파일, `.gjc`, unrelated `.omo` 잔재 스테이징 금지

## 완료 후 보고

- 전체 페이지별 완료 여부
- 576 lattice 실패 재분석 요약
- V2 axis spec
- blind split / WF boundary
- candidate quota
- 다음 static/dry-run-only 명령어
- 남은 위험
- 커밋 해시
