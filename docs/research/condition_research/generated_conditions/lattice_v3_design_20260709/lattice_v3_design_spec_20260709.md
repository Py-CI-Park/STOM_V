# Lattice V3 Canonical Design Specification (CL-D2)

> This document is the SOLE CANONICAL design specification for the AI condition-generation loop rebuild. Every other V3 artifact (source read receipt, failure lesson matrix, evaluation protocol, next command, handoff, verification receipts) is supporting evidence and may NOT redefine this contract.

- 계획: `.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md` (todo 3 / CL-D2)
- 상위 실행계약: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` (T2)
- 목표 권한: `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md`
- 성격: 설계 전용. 이 문서는 조건식 본문·seed JSON·DB 명령·후속 단계 실행 권한을 포함하지 않는다.

## 1. 목표와 비목표 (objective / non-objective)

**목표(북극성):** 고정된 데이터 분할, 공식 STOM 엔진, 거래비용, 실험 예산 안에서 이전 조건식의 실패를 분석하고, 그 근거로 구조적으로 다른 다음 조건식을 생성하여, 보지 않은 기간에서도 이전 세대와 동일 조건 기준선보다 안정적으로 개선됨을 재현 가능하게 증명한다.

**비목표(이 설계가 하지 않는 것):** Alpha Lab, V3K 이관/게이트, Kiwoom/실거래 브로커, 실주문·청산, 포트폴리오 운용, export/live/final promotion. 실패한 Broad-Grid-576·V2 본체의 무제한 변형, 무제한 Plan D 루프. 인프라·문서 완성만으로 자율 개선 목표 달성 선언.

## 2. 권한 위계 (authority hierarchy)

| 순위 | 문서 | 역할 |
|---:|---|---|
| 1 | 정본 마스터 계획 `2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md` | 유일한 최상위 실행 로드맵 |
| 2 | 이 설계 spec (`lattice_v3_design_spec_20260709.md`) | 유일 정본 설계 계약 (SOLE CANONICAL) |
| 3 | Jul-11 감사 | 현재 목표/상태 권한 |
| 4 | Jul-09 V3 design-only 계획 | 하위 CL-D 실행계약 |
| 5 | receipt·failure matrix·protocol·handoff | 지원 증거 (계약 재정의 불가) |

증거는 권한을 부여하지 않는다(evidence != authority). 어떤 문서도 이 spec의 계약을 재정의할 수 없다.

## 3. 용어집 (glossary)

| 정본 이름 | legacy | 의미 | 결과 | 상태 |
|---|---|---|---|---|
| `Broad-Grid-576` | Lattice V1 | 2×6×4×3×4 넓은 격자, tick 288 + min 288 | go 0 / hold 0 / no_go 576 | 실패 기준선 보존 |
| `Failure-Guided-8` | Lattice V2 | V1 실패지도+repair+제한 Plan D 기반 min 후보 재설계 | 8/7/1/0/0/8, 전부 no_go | 종료·본문 재사용 금지 |
| `Canonical-Loop-Next` | Lattice V3 | 실패 근거로 생성·검증·피드백 구조를 재정의한 정본 루프 | 본 설계의 대상 | design-only |

혼동 방지: 단독 `V1/V2/V3`는 검증 단계(DSR/PBO/OOS의 V1~V5), 제품 계보(STOM V2/2U/2U_C), 과거 챔피언 OOS(`V3'`), 2026-04 CLI 연구(`Wide V1`)와 다르다. 새 문서/대시보드는 연구계열+의미이름+날짜를 사용한다.

## 4. 정본 단계 ID와 legacy alias (canonical phase IDs)

설계 단계는 `CL-D0..CL-D4`, 런타임/증거 단계는 `CL-R01..CL-R10`이다. legacy `T0~T4`(V3 design-only)와 `P0~P11`(Jul-11 감사)은 alias로만 유지한다.

| 정본 ID | legacy T alias | legacy P alias | 내용 |
|---|---|---|---|
| CL-D0 | T0 | P1/T0 | source read receipt & scope lock |
| CL-D1 | T1 | P2/T1 | failure lesson matrix |
| CL-D2 | T2 | P3/T2 | canonical design specification (이 문서) |
| CL-D3 | T3 | P4/T3 | evaluation protocol & next command |
| CL-D4 | T4 | P5/T4 | durable master plan, handoff, verification |
| CL-R01 | - | P6 | phase contract & approval guard |
| CL-R02 | - | P6 | immutable evidence contracts |
| CL-R03 | - | P6 | append-only EvidenceStore & schema v11 |
| CL-R04 | - | P6/P7 | B-only provenance, fingerprints, controller passport wiring |
| CL-R05 | - | P6 | durable feedback envelope & consumption proof |
| CL-R06 | - | P6/P7 | bounded pool, semantic quotas, 2x2 attribution |
| CL-R07 | - | P9 | bounded three-round mini closed-loop (process proof) |
| CL-R08 | - | P10 | bounded historical min performance (train/validation) |
| CL-R09 | - | P10 | sealed prospective OOS / walk-forward |
| CL-R10 | - | P11 | human benchmark & promotion review |

주: 감사의 P7(metadata dry-run)·P8(DB registration dry-run)은 CL-R04/CL-R06의 정적 dry-run 게이트와 CL-R07 사전등록에 흡수된다. P0은 Jul-11 감사 자체(목표 재고정 기록)다.

## 5. 단일 실행 소유권 (controller ownership)

| 구성요소 | 정본 역할 | 금지 역할 |
|---|---|---|
| `ai_strategy_loop/controller/loop.py::run_loop` | 세대 상태·후보 생성 호출·공식 평가·부검·다음 세대 진행의 유일한 소유자이며 최종 계보(final lineage)의 유일한 진행자 | 별도 batch 결과를 학습 완료로 간주하지 않음 |
| `cli/research_loop.py` | B_* 분석·후보 근거팩 제공 | 독립 최종 후보 소유자/별도 진화 계보가 되지 않음 |
| lattice / batch (`claude_candidate_batch_eval.py`) | 제한 실험 설계·음성 대조군·정적/회귀 평가 도구 | 무제한 Cartesian 탐색·자율 개선 대체물이 되지 않음; 정본 phase 진행 불가 |
| dashboard | 동일 cohort 관찰·표시 | 실행 소유자 아님; 이질 cohort 순위 비교 금지 |

## 6. 허용 입력과 제외 입력 (approved / excluded inputs)

- 허용: timeframe별 승인된 `B_*` 입력 변수 레지스트리, 실패지도, feature family, repair/Plan D seed(근거로만).
- 제외(매수 생성 누수 금지): `R_*`/`S_*`/result 변수, holdout/validation/OOS 행에서 적합한 임계값, full-baseline 결과.
- 외부/LLM 후보는 ingestion 경계에서 승인 B_* scope를 양성 검증(positive validation)해야 하며, 미승인/결과변수는 거부한다.

## 7. 증거 스키마 (Candidate Passport / Feedback / Evaluation Manifest / Run Receipt)

불변(immutable) typed 계약. 각 스키마의 필드(값이 아닌 필드 정의):

- **CandidatePassport**: schema, passport_id, candidate_id, run_id, round_no, gen_no, slot_no, parent_passport_id(nullable), mode(seed|fresh|refine), lane, family, timeframe, buy/sell strategy names, buy_sha256, sell_sha256, ast_fingerprint, rowset_fingerprint, evidence_ids, threshold_provenance, manifest_id, created_at(UTC).
- **FeedbackEnvelope**: feedback_id, source_passport_id, autopsy_kind, side(buy|sell|risk|error|segment|feature|hypothesis), source_result_sha256, directives, rendered_text, rendered_sha256, created_at(UTC).
- **FeedbackConsumption**: consumption_id, feedback_id, prompt_id, target_passport_id, created_at(UTC).
- **EvaluationManifest**: manifest_id, profile, data, universe, methodology, timeframe, scope, session, period, capital, cost, fill, role, code_hash, config_hash.
- **RunReceipt**: receipt_id, run_id, phase_id, outcome, stop_reason, budget_counters, predecessor_ids, artifact_hashes, created_at(UTC).

이 절은 스키마 필드만 정의하며, 실제 조건식 본문·seed 배열·DB 등록 명령을 포함하지 않는다.

## 8. 불변 ID와 hash 규칙 (immutable ID/hash rules)

- Canonical JSON: UTF-8, NFC 정규화, 정렬된 키, compact separators; CRLF은 LF로 정규화. NaN/Infinity·지역시간·가변 컬렉션·누락 hash·미지 enum 거부.
- 모든 ID는 full SHA-256 + 안정 prefix. `candidate_id` = 내용(buy/sell hash)+methodology 정체성; `passport_id` = run/round/gen/slot 범위 정체성.
- 동일 입력은 프로세스가 달라도 동일 hash(cross-platform 결정성).

## 9. append-only 저장 규칙 (append-only store)

- 기존 `loop_runs.db`(LoopState)에 additive·idempotent 증거 테이블을 추가. 증거 행은 append-only INSERT-only; UPDATE/DELETE 금지. 소비 상태는 query로 파생.
- 동일 중복 insert는 idempotent, 불일치 중복은 corruption. 커밋 후 읽기 스냅샷을 JSON으로 미러; DB가 정본, 스냅샷은 복구/읽기 미러.
- 런타임 DB 내용은 Git에 커밋하지 않는다.

## 10. min/tick lane 정책 (lane policy)

- min lane = CL-R07/R08의 primary. tick lane = 진단/스트레스 전용, 별도 게이트 승인 전까지 재개 금지.
- min-primary replay profile을 version화; 기존 tick/2025 profile은 역사로 보존, 조용한 변경 금지.

## 11. semantic identity (의미적 동일성)

- 후보 정체성은 이름/설명이 아니라 구조·행동으로 관리. Python AST fingerprint(허용 노드: Boolean/Compare/name/numeric; Unicode 식별자 정규화, Decimal 수치, chained bound, 교환가능 AND/OR child 정렬) + 실제 선택 rowset fingerprint를 함께 사용.
- 정적 semantic/rowset 중복은 provider/backtest quota를 소비하지 않는다. family/slot quota를 강제한다.

## 12. 2x2 기여도 (buy/sell attribution)

동일 manifest/profile/seed/cost에서 4개 arm: A(parent-buy+parent-sell), B(candidate-buy+parent-sell), C(parent-buy+candidate-sell), D(candidate-buy+candidate-sell). `buy_effect=B-A`, `sell_effect=C-A`, `interaction=D-B-C+A`(profit·MDD delta·trade count·daily freq). arm 하나라도 누락/오류면 `attribution_invalid`이며 부분 인과 주장 금지.

## 13. 수치 예산 (numerical budgets)

- **CL-R07 (bounded mini-loop)**: 정확히 3 rounds, round당 4 proposals(2 repair + 2 discovery), round당 1 평가 후보, 고정 positive 1 + negative 1 control, 최종 후보 2x2, max 9 official evaluations, max 3 provider pack calls, 120-minute wall cap. 학습 profile: single_stock, 5 trading days, engine 1, betting 5, avg_time 30, timeout 300s, warm 120s, MDD cap 40, min 30 trades, daily 0.5. 초과 시 `no_go_budget_exhausted`.
- **CL-R08 (bounded historical min)**: 마지막 60 min 거래일(2026-07-11 이하), train 40 + validation 20; train-only top-20 유동 종목; 정확히 8 candidates(4 repair + 4 discovery, family당 max 2, semantic dup 0); provider 호출 0(생성 후); gates: 비용후 profit>0, MDD<=35, daily>=0.5, timeout/error 없음, validation 각 chronological half profit>0; max 11 official evaluations, 4-hour cap.
- **CL-R09 (sealed OOS/WF)**: 2026-07-11 이후 20 거래일, `STOM_AI_LOOP_SEALED_OOS_DB` 경유; 4 folds × 5 days; gates: profit>0, MDD<=35, daily>=0.5, 4 folds 모두 nonnegative, timeout/error 없음, base + 사전등록 cost-stress 통과.
- **CL-R10**: 동일 executable 인간 cohort 비교 또는 `not_comparable_missing_executable_reference`.

## 14. 봉인 OOS 정책 (sealed OOS policy)

- OOS는 candidate/config/profile hash가 동결·사전등록된 뒤에만 접근. same-CSV holdout은 validation 증거일 뿐 최종 OOS 증명이 아니다.
- 랜덤 시계열 분할 금지. custodian 프로세스만 OOS 경로를 수신하며, 1회 open 후 access receipt를 불변 기록. open 이후 해당 계보의 후보 생성은 영구 거부.

## 15. 인간 비교 가능성 정책 (human comparability policy)

- Hall of Fame 비교는 동일 cohort key(timeframe, period, universe, engine/methodology, capital, cost/fill, session window)가 전부 일치할 때만. 불일치 행은 그룹/표시만 하고 전역 순위 비교 금지.
- 인간 executable buy/sell 본문+hash가 없으면 `not_comparable_missing_executable_reference`이며 인간 수준 주장 불가. 인간 보고 수익률과 AI 계산 연율화를 구분한다.

## 16. go/no-go 표 (phase gates)

각 CL-R 단계는 아래 정확한 승인 문구가 기록된 뒤에만 열린다. 직전 단계 receipt가 유효해야 하며, missing/invalid 증거는 fail-closed.

| 단계 | 정확한 승인 문구 | go 조건 | no-go 시 |
|---|---|---|---|
| CL-R01..R06 | `I approve CL-R01-R06 code integration only` | 계약·저장소·provenance·피드백·2x2 테스트 통과 | 코드 통합 중단 |
| CL-R07 | `I approve CL-R07 bounded mini-loop only` | 3라운드 학습 사슬·예산 준수 | `CL-R07_NO_GO`, R08 잠금 |
| CL-R08 | `I approve CL-R08 bounded min performance only` | 1 survivor가 train/validation gate 통과 | `NO_GO_STOP`, OOS 미개방 |
| CL-R09 | `I approve CL-R09 sealed OOS/WF only` | 20일 4-fold 봉인 OOS gate 통과 | `NO_GO_FINAL` |
| CL-R10 | `I approve CL-R10 benchmark promotion review only` | 동일 cohort 비교 또는 정직한 non-comparability | 인간수준·export/live 주장 금지 |

성능 통과도 export/live를 자동 승인하지 않는다. `system_built`/`learning_proved`/`performance_proved`/`human_comparison_proved`/`live_authorized`를 분리 보고한다.
## DR-00 post-completion governance overlay pointer (2026-07-13)

Post-completion governance amendment: `docs/research/condition_research/plans/2026-07-13_ai_condition_loop_dr00_post_completion_governance_amendment.md`. This design specification retains its historical authority; the amendment has overlay-only precedence for explicit post-completion DR interpretation. Evidence != authority, no existing CL phrase/receipt carries DR authority, and there is no automatic CL-R08 transition.
