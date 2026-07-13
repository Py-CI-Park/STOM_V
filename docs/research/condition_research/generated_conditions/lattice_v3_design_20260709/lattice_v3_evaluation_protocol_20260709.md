# Lattice V3 Evaluation Protocol And Phase State Machine (CL-D3)

- 계획: `.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md` (todo 4 / CL-D3)
- 상위 정본 설계: `lattice_v3_design_spec_20260709.md` (CL-D2)
- 성격: 설계 전용. 이 문서는 code integration, DB apply, replay, OOS, benchmark 실행 명령을 포함하지 않는다.

## 1. 상태기계 개요 — evidence does not grant authority

모든 CL 단계는 결정론적 상태기계로 진행한다. 핵심 불변식: **evidence does not grant authority**. 직전 단계의 유효한 receipt(증거)는 다음 단계로의 이동 조건이지만, 그 자체로 실행 권한을 만들지 않는다. `CL-R*` 단계는 정확한 승인 문구가 별도로 기록돼야만 열린다. 증거만 있고 승인 문구가 없으면 `authority_missing`으로 fail-closed 한다.

증거 이벤트는 append-only INSERT-only다. 어떤 `UPDATE`/`DELETE` 증거 이벤트도 `evidence_mutation_forbidden`으로 거부한다.

## 2. 단계 전이표 (transition table)

| 상태(완료 단계) | 다음 단계 | 선행 receipt | 허용 mutation | 금지 행위 | 승인 문구 | 실패 전이 |
|---|---|---|---|---|---|---|
| START | CL-D0 | 없음 | INSERT source receipt | 생성/DB/replay | 없음(설계) | fail-closed |
| CL-D0 | CL-D1 | CL-D0 receipt | INSERT matrix | go/hold 재해석 | 없음 | fail-closed |
| CL-D1 | CL-D2 | CL-D1 receipt | INSERT spec | 본문/DB 명령 | 없음 | fail-closed |
| CL-D2 | CL-D3 | CL-D2 receipt | INSERT protocol | 실행 명령 | 없음 | fail-closed |
| CL-D3 | CL-D4 | CL-D3 receipt | INSERT handoff, docs commit | 코드/DB/OOS | 없음 | fail-closed |
| CL-D4 | (정지) | CL-D4 receipt | 없음 | CL-R 진행 | — | stop state `awaiting_CL_R01_R06_approval` |
| awaiting_CL_R01_R06_approval | CL-R01..CL-R06 | CL-D4 receipt | 코드+테스트 INSERT 증거 | default-ON, receipt-only 권한 | `I approve CL-R01-R06 code integration only` | `authority_missing` |
| CL-R06 | CL-R07 | CL-R01..R06 receipts | 제한 폐루프 실행 | 예산 초과 | `I approve CL-R07 bounded mini-loop only` | `authority_missing` / `no_go_budget_exhausted` |
| CL-R07 | CL-R08 | CL-R07 `GO_PROCESS_PROOF` | 제한 성능 검증 | validation 조기 열람 | `I approve CL-R08 bounded min performance only` | `authority_missing` / `NO_GO_STOP` |
| CL-R08 | CL-R09 | CL-R08 1 survivor | 봉인 OOS 1회 open | 재생성/2차 open | `I approve CL-R09 sealed OOS/WF only` | `authority_missing` / `NO_GO_FINAL` |
| CL-R09 | CL-R10 | CL-R09 `GO_R10` | benchmark/승격 검토(분석) | export/live | `I approve CL-R10 benchmark promotion review only` | `authority_missing` |

전이 규칙(요약): (a) UPDATE/DELETE 이벤트 → `evidence_mutation_forbidden`; (b) 직전 단계 미완료 → `out_of_order`; (c) 승인 필요 단계에 정확 문구 없음 → `authority_missing`; 그 외 허용.

정상 경로 CL-D0 → CL-D1 → CL-D2 → CL-D3 → CL-D4는 승인 없이 진행되고, CL-D4 완료 후 상태는 `awaiting_CL_R01_R06_approval`에서 멈춘다.

### 2.1 CL-R01..CL-R06 code-integration sub-phase

코드 통합 게이트는 하나의 승인 문구를 공유하지만 다음 sub-phase로 세분되며, 각 sub-phase도 INSERT-only 증거를 남긴다.

- CL-R01: phase contract & fail-closed approval guard
- CL-R02: immutable evidence contracts (Candidate Passport / Feedback / Evaluation / Run)
- CL-R03: append-only EvidenceStore & LoopState schema v11
- CL-R04: B-only provenance, AST/rowset fingerprints, controller passport/manifest/receipt wiring
- CL-R05: durable feedback envelope, resume restoration, consumption proof
- CL-R06: bounded candidate pool, semantic quotas, 2x2 buy/sell attribution

## 3. INSERT-only 증거 의미

- 후보 여권·피드백·소비·평가 manifest·실행 receipt는 append-only INSERT-only로만 기록한다.
- 소비/진행 상태는 query로 파생한다. 증거 테이블에 UPDATE/DELETE는 존재하지 않는다.
- 동일 중복 insert는 idempotent, 불일치 중복은 corruption으로 fail-closed.

## 4. 후속 승인 문구 (later approval phrases)

정확히 아래 다섯 문구만 각 게이트를 연다. 유사어·의역은 무효다.

1. `I approve CL-R01-R06 code integration only`
2. `I approve CL-R07 bounded mini-loop only`
3. `I approve CL-R08 bounded min performance only`
4. `I approve CL-R09 sealed OOS/WF only`
5. `I approve CL-R10 benchmark promotion review only`

## 5. R07/R08 예산 동결 (frozen budgets)

- CL-R07: 3 rounds, round당 4 proposals(2 repair + 2 discovery), round당 1 평가, positive 1 + negative 1 control, 최종 2x2, max 9 official evaluations, max 3 provider pack calls, 120-minute wall cap. profile: single_stock, 5 days, engine 1, betting 5, avg_time 30, timeout 300s, warm 120s, MDD cap 40, min 30 trades, daily 0.5.
- CL-R08: 마지막 60 min 거래일(train 40 + validation 20), train-only top-20 유동 종목, 정확히 8 candidates(4 repair + 4 discovery, family당 max 2, semantic dup 0), gates profit>0/MDD<=35/daily>=0.5/각 chronological half profit>0, max 11 official evaluations, 4-hour cap.
- 이 예산은 CL-R07 첫 결과-보유 실행 전에 동결되며, 결과를 본 뒤 CL-R08/R09/R10 임계값을 바꿀 수 없다.

## 6. OOS custodian / access 스키마 (sealed OOS)

- CL-R09 데이터는 `STOM_AI_LOOP_SEALED_OOS_DB`(2026-07-11 이후 20 거래일)만 사용.
- custodian 프로세스만 OOS 경로를 수신한다. custodian은 prospective 날짜, source SHA/size/read-only ACL, survivor/config/profile/prereg hash, 사전 1일 purge, 이전 access receipt 부재를 검증한 뒤 `oos_opened`를 append하고 공식 runner를 provider/generation import 없이 실행한다.
- open 이후 해당 계보의 후보 생성은 phase guard가 영구 거부한다. 2차 open·재생성·OOS 식별자 누수는 OOS 주장을 무효화한다.
- access receipt 스키마: {receipt_id, lineage_id, oos_source_sha256, oos_source_bytes, acl_readonly(bool), survivor_hash, config_hash, profile_hash, prereg_hash, opened_at_utc, fold_ids[4]}.

## 7. 인간 cohort manifest (human cohort manifest)

- CL-R10 human cohort manifest 스키마: {cohort_id, timeframe, period, universe, engine, methodology, capital, cost, fill, session_window, ranking_formula, tie_rule, human_bodies[]:{name, buy_sha256, sell_sha256}}.
- executable buy/sell 본문+hash가 없으면 `not_comparable_missing_executable_reference`이며 인간 수준 주장 불가.

## 8. dashboard cannot reinterpret evidence

- dashboard cannot reinterpret evidence: 대시보드/표시 계층은 저장된 증거의 판정을 재해석·승격할 수 없다. 관찰·버전 표기·cohort 안전 그룹만 수행한다.

## 9. 실패 전이와 stop state (failure transitions)

- `out_of_order`: 직전 단계 미완료 상태에서의 전이.
- `authority_missing`: 승인 필요 단계에 정확 문구 부재(receipt만 있음).
- `evidence_mutation_forbidden`: UPDATE/DELETE 증거 이벤트.
- `no_go_budget_exhausted` / `NO_GO_STOP` / `NO_GO_FINAL`: 각 성능 게이트 미통과. 후속 단계를 잠근다.
- 모든 실패는 fail-closed이며 다음 단계를 자동으로 열지 않는다.
## DR-00 post-completion governance overlay pointer (2026-07-13)

Post-completion governance amendment: `docs/research/condition_research/plans/2026-07-13_ai_condition_loop_dr00_post_completion_governance_amendment.md`. This evaluation protocol retains its historical authority; the amendment has overlay-only precedence for explicit post-completion DR interpretation. Evidence != authority, no existing CL phrase/receipt carries DR authority, there is no automatic CL-R08 transition, and every post-DR-06 verdict stops at `HARD_STOP_AWAITING_CL_R08_DECISION`.
