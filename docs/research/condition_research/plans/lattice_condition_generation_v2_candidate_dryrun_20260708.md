# Lattice Condition Generation V2 Candidate Dry-Run Plan

작성시각: 2026-07-08 10:02 KST

## 목적

조건식 생성 v2 재설계 산출물을 바탕으로 후보 메타데이터를 최대 32개까지 설계하고, static gate와 DB registration dry-run까지만 수행한다.

이번 계획은 다음 실행 단계의 입력 문서다. 이 문서는 DB 등록 apply, backtest, limited replay, OOS, portfolio, Plan D R3, export/live/final promotion을 허용하지 않는다.

## 반드시 먼저 읽을 문서

- `docs/research/condition_research/plans/lattice_condition_generation_v2_failure_map_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_seed_lineage_audit_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_axis_spec_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_evaluation_protocol_20260708.json`
- `docs/research/condition_research/plans/lattice_condition_generation_v2_candidate_quota_ledger_20260708.json`
- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

## 진행

1. 후보 메타데이터만 설계한다.
2. 총 후보 수는 최대 32개로 제한한다.
3. 후보 class quota는 다음을 기본값으로 한다.
   - `coverage_composite`: 최대 8
   - `risk_balanced_composite`: 최대 8
   - `survivor_seed_derivative`: 최대 8
   - `negative_control`: 최대 4
   - `holdout_control`: 최대 4
4. 모든 후보는 research lane 전용, `hypothesis_seed` 라벨, sanitized 이름만 사용한다.
5. 조건식 본문을 작성하는 경우 `strategy.txt`와 `rules.txt` 기준 static gate만 수행한다.
6. DB registration은 dry-run까지만 수행하고 apply하지 않는다.
7. 결과는 candidate ledger, static receipt, dry-run receipt, handoff로 남긴다.

## 금지

- DB INSERT apply 금지
- DB UPDATE/DELETE 금지
- backtest 실행 금지
- limited replay 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- Plan D R3 실행 금지
- export/live/final promotion 금지
- full tick 288 실행 금지
- full min 288 실행 금지
- `git add -A` 금지
- dashboard 7파일, `.gjc`, unrelated `.omo` 스테이징 금지

## 완료 후 보고

- 후보 class별 설계 개수
- candidate ledger 경로
- static gate receipt 경로
- DB registration dry-run receipt 경로
- apply/replay/OOS 미실행 증빙
- 다음 단계 개방 가능 여부
