# AI 조건식 루프 DR-00 완료 후 결함 교정 거버넌스 개정 (2026-07-13)

## 1. 상태·권한·적용 범위

DR-00은 완료 후의 문서 전용 overlay이다. 기존 CL-R01~R07 intake, 승인 문구, receipt, quality-gate, run artifact의 bytes와 그 당시 authority는 불변으로 보존한다. 이 개정은 명시한 post-completion DR 해석에만 우선하며, 기존 evidence를 수정·삭제·재발행하거나 소급 무효화하지 않는다.

기록할 stage-13 Ralplan write receipt SHA-256은 `40090a729d23c6425cfc4b26d8640bce72004444873f339b53aba8f85f282b99`이다. 승인된 final Ralplan receipt SHA `ea292845605e7ae2b74371596a2d208b560e079d0f0e8737a5cea9d2b8866285`는 별도 승인 receipt 식별자이며 stage-13 SHA를 대체하지 않는다. existing data only와 defaults OFF를 유지한다.

## 2. 권한 위계와 overlay 규칙

증거는 권한이 아니다. historical behavior soundness, internal verdict, completion receipt는 새 DR 또는 CL 실행 권한이나 exact-intake conformance의 자동 증명이 아니다. 기존 exact CL phrases는 quotation only이며 DR authority를 주지 않는다.

- `I approve CL-R01-R06 code integration only`
- `I approve CL-R07 bounded mini-loop only`
- `I approve CL-R08 bounded min performance only`
- `I approve CL-R09 sealed OOS/WF only`
- `I approve CL-R10 benchmark promotion review only`

모든 후속 DR-01~05 code integration과 DR-06 audit은 later Ralplan이 exact phrase를 처음 제안하고 기존 CL phrase와 reconcile한 뒤 별도 exact approval을 받아야 한다. DR-00은 CL phase/P alias가 아니며 CL-R08~R10으로 자동 전이하지 않는다.

## 3. RALPLAN-DR 원칙과 top drivers

### RALPLAN-DR

1. **R — Receipt immutability:** approval intake, receipt, quality gate, run artifact는 수정·삭제·재발행하지 않는다.
2. **A — Authority non-transferability:** 모든 matrix 행은 `AUTHORITY_NOT_CARRIED_FORWARD`다.
3. **L — Least-authority overlay:** DR-00은 docs overlay만 허용한다.
4. **P — Publication simplicity:** publication identity는 stage-13 Ralplan receipt SHA와 containing Git commit SHA뿐이다.
5. **L — Later phrase reconciliation:** DR-01~05와 DR-06의 executable exact phrase는 후속 Ralplan과 별도 승인에서 정한다.
6. **A — Audit separation:** DR-06은 별도 plan/approval의 artifact-only read-only audit이다.
7. **N — No automatic transition:** 모든 DR-06 verdict 뒤 무조건 HARD STOP이며 CL-R08 자동 전이가 없다.
8. **DR — Claim-scoped remediation:** historical observation, authority conformance, performance claim을 분리한다.

Top drivers는 historical integrity, evidence와 authority의 분리, aggregate label보다 claim precision, least-authority publication, defaults OFF를 포함한 operational safety, ordinary Git revert 가능성이다.

## 4. 기존 CL 승인 문구 불변 보존

기존 intake는 CL-R01..R06 code integration only/defaults OFF/downstream locked 및 CL-R07의 isolated strategy와 tracked/protected path 밖 copied min data에서 one approved official STOM run, same hashes의 written failure receipt가 있는 technical retry only, process proof not profitability, CL-R08~R10 locked를 정한다. 해당 intake와 `.omo` evidence는 Git allowlist 밖 immutable evidence다.

`learning_proved`는 run#6에 부착된 historical report label일 뿐이다. `performance_proved=false`, `human_comparison_proved=false`, `live_authorized=false`이며, DR-00은 historical bytes를 무효화하지도 rerun/retry/next phase를 허가하지도 않는다.

## 5. CL-R01~R07 claim-level receipt disposition

| Category | Meaning |
|---|---|
| `HISTORICAL_RECEIPT_IMMUTABLE` | recorded observation의 bytes와 사실을 보존하며 edit/delete/reissue하지 않는다 |
| `CLAIM_RETAINED_AS_SCOPED` | 명시한 focused-test 또는 observed behavior claim만 retain한다 |
| `CLAIM_LIMITED_NOT_EXPANDED` | production-wide, certification, authority-conformance, performance, live claim으로 확장하지 않는다 |
| `CLAIM_REVALIDATION_REQUIRED` | future integration claim에는 later approved tests 또는 artifact-only audit이 필요하다 |
| `CLAIM_SUPERSEDED_FOR_FUTURE_INTEGRATION` | future DR integration은 old claim을 completion으로 쓰지 않고 revised contract를 쓴다 |
| `AUTHORITY_NOT_CARRIED_FORWARD` | old phrase/receipt는 DR code/audit/provider/backtest/CL-R08을 authorize하지 않는다 |
| `NO_AUTOMATIC_REEXECUTION` | rerun/retry/next phase를 authorize하지 않는다 |
| `AUTHORITY_CONFORMANCE_SUSPENDED` | observed execution label은 historical이나 exact intake conformance는 artifact-only disposition 전까지 withheld다 |

| Phase/evidence | Retained historical claim | Explicitly limited/withheld | Required future treatment | Categories |
|---|---|---|---|---|
| CL-R01 — phase contract; task-6 quality evidence | exact-literal guard 및 focused out-of-order/mutation fail-closed test observations | no new DR phase/mutation authority | later Ralplan proposes/reconciles exact DR authority; separate approval | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `AUTHORITY_NOT_CARRIED_FORWARD` |
| CL-R02 — immutable contracts; task-7 evidence referenced by task-6 gate | five typed contracts 및 canonical hashing/immutability focused tests | no Manifest v2, PromptArtifact, checkpoint, migration-compatibility certification | DR-02/03 later approved contract/tests | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `AUTHORITY_NOT_CARRIED_FORWARD` |
| CL-R03 — EvidenceStore/schema v11; task-8 gate | additive v11 및 INSERT-only/idempotent/corruption/FK/crash-focused test observations | no operating DB application, future schema, production certification fail-closed claim | DR-03 additive compatibility/fault-path verification after separate approval; no old DB/receipt mutation | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `AUTHORITY_NOT_CARRIED_FORWARD` |
| CL-R04 — task-9/task-10 provenance/fingerprint/default-OFF evidence | **only** threshold provenance, B-approval provenance recording, AST/rowset fingerprints, reachable default-OFF enforcement focused evidence | **withhold** approved-B registry reconciliation; **withhold** deep production `research_loop`/`pack_producer` context wiring; no generic completed B-only production guard, actual prompt ID, Manifest v2, or complete causal ledger claim | DR-04 must reconcile approved-B registry and prove deep production `research_loop`→`pack_producer`→canonical-owner context/ingestion wiring in integration QA; DR-02/03 revalidate manifest/prompt causality | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `CLAIM_SUPERSEDED_FOR_FUTURE_INTEGRATION`, `AUTHORITY_NOT_CARRIED_FORWARD` |
| CL-R05 — feedback envelope/consumption; task-12 gate | append-only primitives 및 focused both-side/resume fixture observations | no production actual-prompt FK, rendered-envelope-only consumption, evidence-I/O fail-closed, full checkpoint claim | DR-03 later approved actual prompt/rendered IDs/fail-closed/checkpoint/resume QA | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `CLAIM_SUPERSEDED_FOR_FUTURE_INTEGRATION`, `AUTHORITY_NOT_CARRIED_FORWARD` |
| CL-R06 — bounded pool/2×2; task-12 gate | pure candidate-pool 및 2×2 focused contract tests | no final-owner repair/discovery integration, run-wide dedup, branch-aware OR, production-wide attribution | DR-04 later approved integration and validation-coupled QA | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `AUTHORITY_NOT_CARRIED_FORWARD` |
| CL-R07 prereg/driver — task-13 gate | fake-provider/evaluator driver tests 및 prereg ordering observation | no official result, performance, or authority carry-forward | DR-06 artifact-only existence/hash/contract comparison; no run | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `AUTHORITY_NOT_CARRIED_FORWARD`, `NO_AUTOMATIC_REEXECUTION` |
| CL-R07 task-14/run#6 — GO update log, SOUND_GO summary/rereview, terminal receipt `rr_bdc77dbc9fc07213de68efbe5c07c35524a472a06b33c31ce59bdf85abe6c06f` | immutable artifacts and recorded internal labels `SOUND_GO`/`GO_PROCESS_PROOF`, learning-chain/2×2 observations, are historical observations only | approval-boundary conformance withheld: intake allowed one official run, same-hash technical retry with written failure receipt, isolated copied min data; durable records describe six real runs, intervening code fixes/hashes, and direct read of `_database/stock_min_back.db`. No profit/performance, raw-call budget=3, control-gated validation, enforced-high-reasoning, or downstream authority claim | DR-06 artifact-only disposition of known deviations against intake/receipts; no DB open, provider/backtest, rerun, retry, artifact mutation, or automatic CL-R08 | `HISTORICAL_RECEIPT_IMMUTABLE`, `CLAIM_RETAINED_AS_SCOPED`, `CLAIM_LIMITED_NOT_EXPANDED`, `CLAIM_REVALIDATION_REQUIRED`, `AUTHORITY_CONFORMANCE_SUSPENDED`, `AUTHORITY_NOT_CARRIED_FORWARD`, `NO_AUTOMATIC_REEXECUTION` |

## 6. DR-01~05 미래 source/test allowlist와 별도 승인

후속 exact code-integration Ralplan은 이 maximum list를 좁힐 수만 있으며, symbol-level diff, compatibility/migration decision, command, exact phrase proposal/reconciliation 및 separate approval이 필요하다. 현재 어느 listed file도 변경 authority를 얻지 않는다. expansion에는 later governance amendment가 필요하다.

| DR | Maximum later source allowlist | Maximum later test allowlist | Frozen obligations |
|---|---|---|---|
| DR-01 math/CSV | `ai_strategy_loop/fitness/score.py`; `ai_strategy_loop/autopsy/trade_quant.py`; `ai_strategy_loop/autopsy/analysis_card.py`; `ai_strategy_loop/fitness/edge_ratio.py` | `tests/unit/test_composite_score.py`; `tests/unit/test_trade_quant.py`; `tests/unit/test_analysis_card.py`; `tests/unit/test_edge_ratio.py` | positive-slope R²; MDD from zero; deterministic ordering; win/loss/neutral; canonical MFE/MAE alias; all-negative slice non-actionable |
| DR-02 profile/Manifest v2 | `ai_strategy_loop/scripts/research_presets.py`; `ai_strategy_loop/launch_config.py`; `ai_strategy_loop/config.py`; `ai_strategy_loop/controller/condition_discovery.py`; `ai_strategy_loop/controller/loop.py`; `ai_strategy_loop/controller/evidence_contract.py` | `tests/unit/test_research_presets.py`; `tests/unit/test_feedback_toggles_on.py`; `tests/unit/test_launch_config.py`; `tests/unit/test_condition_discovery_policy.py`; `tests/unit/test_canonical_passport_wiring.py`; `tests/unit/test_prompt_logging.py` | CLI/UI/preset effective hash equality; min-full argv 09:00–15:00; evidence/profile toggles explicit; global defaults OFF; manifest binds data/universe/engine/cost/fill/capital/session/prompt/seed/code/config |
| DR-03 causal evidence/resume | `ai_strategy_loop/controller/state.py`; `ai_strategy_loop/controller/evidence_contract.py`; `ai_strategy_loop/controller/evidence_store.py`; `ai_strategy_loop/brain/generator.py`; `ai_strategy_loop/brain/prompt.py`; `ai_strategy_loop/controller/loop.py` | `tests/unit/test_prompt_logging.py`; `tests/unit/test_evidence_contract.py`; `tests/unit/test_evidence_store.py`; `tests/unit/test_feedback_evidence_wiring.py`; `tests/unit/test_canonical_passport_wiring.py`; `tests/unit/test_state_schema_migration.py`; `tests/unit/test_state_concurrency.py`; `tests/unit/test_evidence_lineage_check.py` | real prompt ID/FK; only rendered envelope IDs; certification fail-closed; additive compatibility; deterministic crash/resume; no orphan/double/mismatch |
| DR-04 candidate integration | `ai_strategy_loop/brain/pack_producer.py`; `ai_strategy_loop/brain/prompt.py`; `ai_strategy_loop/brain/generator.py`; `ai_strategy_loop/brain/filter_gate.py`; `ai_strategy_loop/controller/loop.py`; `ai_strategy_loop/controller/candidate_pool.py`; `ai_strategy_loop/controller/context_pack_builder.py`; `cli/research_loop.py`; `cli/condition_fingerprint.py`; `cli/condition_generator.py` | `tests/unit/test_pack_producer.py`; `tests/unit/test_llm_pack_wiring.py`; `tests/unit/test_context_pack_builder.py`; `tests/unit/test_candidate_pool.py`; `tests/unit/test_condition_fingerprint.py`; `tests/unit/test_condition_generator.py`; `tests/unit/test_filter_gate.py`; `tests/unit/test_research_prompt_contracts.py`; `tests/unit/test_research_loop.py` | final owner bounded repair2/discovery2; SeedPlan; run-wide AST/rowset dedup; family/coverage quotas; bounded bundle receipt; branch-aware OR; origin/capability evidence; **approved-B registry reconciliation**; **deep production `research_loop`/`pack_producer` context wiring and canonical-owner integration QA** |
| DR-05 AnalysisCardV3/statistics | `ai_strategy_loop/autopsy/analysis_card.py`; `ai_strategy_loop/autopsy/trade_quant.py`; `ai_strategy_loop/autopsy/segment.py`; `ai_strategy_loop/autopsy/hypothesis.py`; `ai_strategy_loop/autopsy/ablation.py`; `ai_strategy_loop/fitness/edge_ratio.py`; `ai_strategy_loop/fitness/overfit_stats.py`; `ai_strategy_loop/fitness/promotion_diagnostics.py`; `ai_strategy_loop/brain/segment_feedback.py`; `ai_strategy_loop/brain/feature_importance_feedback.py`; `ai_strategy_loop/controller/loop.py` | `tests/unit/test_analysis_card.py`; `tests/unit/test_trade_quant.py`; `tests/unit/test_segment_autopsy.py`; `tests/unit/test_hypothesis_loop.py`; `tests/unit/test_condition_ablation.py`; `tests/unit/test_edge_ratio.py`; `tests/unit/test_overfit_stats.py`; `tests/unit/test_promotion_diagnostics.py`; `tests/unit/test_segment_feedback.py`; `tests/unit/test_condition_discovery_feedback.py` | source/role/manifest/hash/quality; CI and n_days/n_symbols/n_trades; prereg axis or BH-FDR; descriptive/directive split; train-only; row ablation non-causal without separate official 2×2 authority |

DR-01~05는 validation-coupled이다. focused slice tests만으로 integration을 complete할 수 없고, later plan은 frozen profile→manifest→prompt→candidate→result→analysis→feedback QA를 정의한다. 그 QA도 provider/backtest authority를 inherit하지 않는다.

## 7. DR-06 별도 read-only 감사 계약

DR-06은 여기서 executed 또는 approved되지 않는다. later Ralplan은 DR-01~05와 분리되고 own exact audit phrase를 propose/reconcile하여 separate approval을 받아야 하며, exact existing artifact paths, expected hashes/receipt IDs, source roles, permitted read operations를 enumerate해야 한다.

DR-06은 task-13 prereg/intake와 task-14 historical files의 six-run/intervening-fix/direct-protected-min-read deviations를 DB를 열지 않고 비교한다. provider/evaluator/backtest 호출, candidate generate/rank/replace, validation open, threshold/tie rule change, schema migration, runtime-state write를 하지 않는다. run#6의 artifact-only authority-conformance disposition과 frozen R08 readiness를 별도로 assess한다. readiness output은 `R08_READY`, `R08_CONTRACT_AMENDMENT_REQUIRED`, `READINESS_BLOCKED` 중 하나뿐이며 어떤 verdict도 authority가 아니다. 필요한 disposition에 DB open, provider/backtest, protected-path read, new evidence가 필요하면 `READINESS_BLOCKED`로 끝내며 scope를 넓히지 않는다.

## 8. 무조건 HARD STOP과 CL-R08 비전이

Ultragoal A의 문서 commit 뒤 종료 상태는 다음과 같다.

```text
DR00_DOCS_COMMITTED
HARD_STOP_AWAITING_SEPARATE_DR_CODE_INTEGRATION_PLAN_AND_EXACT_APPROVAL
```

Future DR-06의 모든 verdict는 다음에서 멈춘다.

```text
R08_READY | R08_CONTRACT_AMENDMENT_REQUIRED | READINESS_BLOCKED
→ HARD_STOP_AWAITING_CL_R08_DECISION
```

`R08_READY`는 approval도 command도 아니며 CL-R07 rerun 또는 automatic CL-R08 transition은 없다.

## 9. Exact non-goals

- product/runtime source, tests, fixtures, schemas, configuration mutation.
- custom publisher/Windows publisher/event log/journal/transaction/recovery platform/content-addressed publication store.
- SQLite schema/migration/copy/open/query, DB/WAL/SHM, CSV/log/result mutation.
- provider/evaluator calls, candidate generation, replay, official STOM backtest, Plan D, OOS/WF, benchmark, portfolio, export/live.
- new data collection/addition/period extension/operating data migration.
- protected/runtime paths `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `ai_strategy_loop/state` read/write/copy/open.
- defaults ON, UI/product behavior, broker/live/V3K changes.
- DR-01~05 code integration, DR-06 audit execution, CL-R08~R10 execution or approval.
- existing CL intake/receipt/quality-gate/run artifact edit/delete/reissue.
- existing CL phrase reuse as DR authority or invention of executable DR code/audit phrase.
- run#6 rerun, provider/backtest retry, protected DB reinspection.
- tests/builds/formatters/gates.

## 10. ADR과 선택지

### Option A — New amendment + three EOF pointers + one dated receipt + one Git commit (selected)

Historical bytes/phrases를 보존하는 smallest diff이며 ordinary review/revert와 no runtime을 제공한다.

### Option B — Rewrite historical master/spec/protocol sections

한 파일 읽기는 쉬우나 완료 당시 authority와 overlay를 섞고 phrase/receipt history를 훼손하므로 기각한다.

### Option C — Reuse custom publisher/event-log/transaction design

별도 publication protocol은 docs-only commit에 불필요하고 stage-11 scope failure를 되살리므로 기각한다.

**ADR-DR00-001 — Authority-preserving post-completion overlay**: Status는 Proposed이며 Ultragoal A docs commit 시 Accepted. Option A를 채택한다. original documents는 original time의 authority를 유지하고 amendment는 explicit post-completion DR interpretation에만 우선한다. identity는 stage-13 Ralplan receipt SHA + one containing Git commit SHA다. publisher, event-log runtime, journal, transaction platform, custom receipt runtime, SQLite schema는 없다. rollback은 ordinary `git revert <DR00_COMMIT_SHA>`이며 historical CL evidence는 untouched다.

## 11. 3-scenario pre-mortem

| # | Failure scenario | Early signal | Mitigation/recovery |
|---:|---|---|---|
| 1 | Pointer edit rewrites historical bytes/phrases | deletion hunk, prefix/phrase mismatch | EOF append only; no commit; fix then rerun Pass A+Pass B; published면 ordinary revert |
| 2 | Historical CL-R04/run#6 label launders future authority | generic completed B-only wording; missing intake deviations; `learning_proved=true` without suspension | exact retained/withheld rows, every-row no authority, DR-06 artifact-only disposition, no rerun/performance |
| 3 | Receipt records stale or preclaimed verification | receipt edited after Pass B, pending token, Pass B tokens not emitted | one receipt-only finalization, final staged Pass B, no later edit; any failure restarts both passes |

## 12. Publication identity와 ordinary Git flow

Publication identity는 오직 stage-13 Ralplan write receipt SHA `40090a729d23c6425cfc4b26d8640bce72004444873f339b53aba8f85f282b99`와 이 receipt를 포함하는 one containing Git commit SHA다. Git SHA는 자기 tree에 넣지 않으며 commit 후 `git rev-parse HEAD`로 외부 관측하여 resolve한다. custom publisher, event log runtime, transaction platform, SQLite schema, separate publication ID를 만들지 않는다.

## 13. Acceptance·verification·rollback

Verification은 docs/Git byte verification만 허용한다: exact five-path allowlist, three pointer prefix preservation 및 existing phrase counts, H1/H2 order, stage-13 SHA, every-row authority category, CL-R04/run#6 wording, exact non-goals, three scenarios, both HARD STOPs, receipt pending-token state를 점검한다. tests, builds, formatters, gates, provider, evaluator, backtest, DB commands는 실행하지 않는다.

Before publication에는 target-only authored work만 멈추고 제거할 수 있으며 unrelated work는 건드리지 않는다. After publication에는 ordinary reviewed `git revert <DR00_COMMIT_SHA>`만 사용한다. reset --hard, history rewrite, force push, receipt deletion은 금지한다. revert는 five docs overlay만 제거하며 CL intake, receipt, `.omo` evidence, product code, runtime/protected data의 historical observation은 바꾸지 않는다.

## 14. Ultragoal A docs-only handoff

Deliverables는 exact five paths, Pass A 후 receipt-only finalization, final staged Pass B, one Korean commit, stage-13 Ralplan SHA와 containing Git SHA다. 이 draft 단계에서는 staging, commit, Pass A/Pass B, test/gate/formatter 실행을 하지 않는다. Parent가 final verification, staging, checkpointing, commit을 소유한다.

Exit는 `DR00_DOCS_COMMITTED` 다음 `HARD_STOP_AWAITING_SEPARATE_DR_CODE_INTEGRATION_PLAN_AND_EXACT_APPROVAL`이다. Next possible authority는 symbols/tests를 좁히고 exact phrase를 propose/reconcile한 separate DR-01~05 code-integration Ralplan 및 separate exact approval이다. DR-06은 later separate artifact-only plan/approval이고 항상 CL-R08 전에 멈춘다.
