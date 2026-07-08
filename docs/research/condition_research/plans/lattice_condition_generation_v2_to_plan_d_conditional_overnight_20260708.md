# lattice condition-generation v2 to Plan D conditional overnight plan

작성일: 2026-07-08

## 목표

2026-07-09 06:50 KST까지 `lattice v2 body` 후보 8개만 대상으로 공식 min 전체기간 warm64 limited replay를 수행하고, Plan D 입력 가능 여부 또는 중단 결론을 확정한다.

이번 페이지의 핵심은 후보를 더 늘리는 것이 아니라, 이미 static gate와 DB registration dry-run을 통과한 8개 body seed가 실제 공식 min 전체기간 warm64 프로파일에서 생존 가능한지 확인하는 것이다.

## Read-First Source Package

반드시 아래 문서를 먼저 EOF까지 확인하고, line_count / sha256 / 적용 섹션을 receipt로 남긴다.

- `docs/update_log/2026-07-08_lattice_condition_generation_v2_body_static_dryrun_handoff.md`
- `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/lattice_v2_body_static_dryrun_seeds_20260708.json`
- `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/lattice_v2_body_static_gate_receipt_20260708.json`
- `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/lattice_v2_body_db_registration_dryrun_receipt_20260708.json`
- `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json`

## 공식 실행 프로파일

- lane: min official limited replay
- DB: `_database/stock_min_back.db`
- 기간: 2025-04-07 ~ 2026-02-27
- 시간: 09:00 ~ 15:19
- engine: warm64
- 방식: 64개 warm engine prepare 후 등록된 8개 후보만 순차 평가
- config: `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json`

## 진행 순서

1. 최신 handoff와 v2 body static dry-run 산출물을 확인한다.
2. DB INSERT-only apply 전 preflight를 수행한다.
3. 8개 body seed만 INSERT-only로 등록한다.
4. DB UPDATE/DELETE는 절대 하지 않는다.
5. 등록 후 pairs / mapping / provenance / backup receipt를 기록한다.
6. 등록된 8개만 공식 min 전체기간 warm64 limited replay로 실행한다.
7. 결과를 `survivor` / `hold` / `no_go`로 분류한다.
8. survivor가 없으면 Plan D를 실행하지 않고 중단 보고한다.
9. survivor가 있으면 selected survivor만 freeze/preregistration 확정한다.
10. preregistration된 selected survivor만 공식 OOS-style robustness replay로 실행한다.
11. OOS survivor가 있으면 append-only로 `oos_survivors`, `seed_pool`, `passport`를 기록한다.
12. seed_pool 입력이 생긴 경우에만 Plan D intake/readiness를 수행한다.
13. Plan D는 R-a/R-b readiness와 다음 R-c 가능 여부 판단까지만 진행한다.
14. portfolio / export / live / final promotion은 실행하지 않는다.
15. 2026-07-09 06:50 KST 전에는 전체 handoff와 다음 명령어를 작성하고 한글 커밋한다.

## 금지 조건

- DB UPDATE/DELETE 금지
- 8개 body seed 외 DB 등록 금지
- 8개 body seed 외 replay 금지
- preregistration 없는 OOS 금지
- survivor 없는 Plan D 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- full tick 288 실행 금지
- full min 288 실행 금지
- `git add -A` 금지
- dashboard 7파일, `.gjc`, unrelated `.omo` 잔재 스테이징 금지

## 분기 기준

### limited replay survivor

공식 min 전체기간 warm64 limited replay에서 아래 조건을 동시에 만족하면 survivor로 분류한다.

- batch status가 정상 row를 생성함
- `gate_passed=true`
- 손익이 양수
- MDD가 config gate 범위 이내
- 거래수 및 daily trade가 gate 기준을 만족

### hold

성과가 완전 생존은 아니지만 구조적으로 다음 후보 설계에 쓸 정보가 있거나, gate 근처의 부분 개선이 확인되면 hold로 분류한다.

### no_go

row 생성 실패, no_trades, 손익 음수, MDD 초과, daily trade 부족, static/profile 위반은 no_go로 분류한다.

## 완료 보고 항목

- DB INSERT-only 결과
- backup/provenance/mapping 경로
- limited replay 결과
- survivor/hold/no_go 목록
- OOS 실행 여부와 결과
- seed_pool 반영 여부
- Plan D 진행 가능/불가능 판단
- 전체 연구 진행률
- 다음 추천 명령어
- 커밋 해시
