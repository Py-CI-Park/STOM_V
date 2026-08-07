# ai-condition-loop-canonical-rebuild-20260711 - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** One understandable condition-improvement system in which every candidate, data source, failure diagnosis, next change, evaluation, and final decision can be traced. It also delivers a durable master plan and handoff that a new agent can execute without reconstructing this conversation.

**Why this approach:** The existing generator, official backtest, analysis, and dashboard are retained; the missing evidence links and single ownership are added around them. Small learning proof comes before performance testing, and unseen data or human comparison stays locked until the earlier evidence passes.

**What it will NOT do:** It will not reopen failed mass searches, tune on unseen data, mix incomparable human and AI records, or touch live trading. Starting the plan initially creates and commits design/handoff documents only; every later code, replay, unseen-data, and benchmark stage requires its own explicit approval.

**Effort:** XL
**Risk:** High - durable state migration, official backtest evidence, future sealed data, and fair benchmark comparability can each independently block completion.
**Decisions to sanity-check:** Reuse the existing state database with additive evidence tables; use minute data for bounded learning; reserve future post-plan data for final proof; never rank against humans without executable identical-cohort references.

Your next move: start the plan to produce the design and handoff package, or request the optional dual high-accuracy review first. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk gated rebuild: CL-D0..D4 design/handoff first, then separately approved CL-R01..R10 evidence contracts, learning proof, bounded performance, sealed OOS, and cohort-safe benchmark.

## Scope
### Must have

- One canonical roadmap with collision-free `CL-D0..D4` design IDs and `CL-R01..R10` runtime/evidence IDs, plus a legacy alias table for T/P labels.
- One sole canonical design specification; receipts, matrices, protocol, and handoff are supporting evidence only.
- `run_loop` remains the only owner of final generation progression; CLI research and batch evaluation remain proposal/evidence adapters.
- Immutable Candidate Passport, Feedback Envelope, Feedback Consumption, Evaluation Manifest, and Run Receipt contracts with deterministic IDs/hashes.
- Additive, idempotent, append-only evidence storage in the existing `loop_runs.db` plus readable JSON snapshots; runtime DB contents never enter Git.
- Positive B_* variable-scope enforcement, threshold/data/fold provenance, AST and rowset fingerprints, and bounded family/slot quotas.
- Resume-safe feedback restoration with an auditable `source autopsy -> prompt receipt -> next passport -> changed clause` chain.
- A fixed 2x2 buy/sell attribution matrix, a three-round bounded mini-loop, a historical min validation page, prospective sealed OOS, and same-cohort human benchmarking in strict gated order.
- Dashboard/API reconstruction for historical lineage and feedback, semantic version labels, stale-state warnings, cohort-safe Hall of Fame grouping, and explicit non-comparability reasons.
- A durable human-readable master plan, self-contained new-agent handoff, latest-first pointer updates, focused tests, official/manual receipts, and Korean explicit-path commits.

### Must NOT have (guardrails, anti-slop, scope boundaries)

- No Alpha Lab, V3K gate progression, Kiwoom/live broker, production order/exit, portfolio, export, or live/final promotion implementation.
- No reopening Broad-Grid-576, failed V2 bodies, full tick/min 288, unlimited Plan D, or stale V1/V2 mutation loops.
- No source-code integration before `I approve CL-R01-R06 code integration only`; no official replay before its exact phase approval; no OOS or benchmark access before their exact approval phrases.
- No operating `_database/`/runtime `*.db` writes, UPDATE/DELETE evidence mutations, committed DB/CSV/log files, or edits to protected result paths.
- No R_*/S_*/result leakage into buy generation, random time-series split, same-CSV holdout described as sealed OOS, or threshold changes after result disclosure.
- No second autonomous loop, second canonical state DB, new frontend framework, broad runner/backengine rewrite, default-ON research feature, or unapproved dependency.
- No human/AI global ranking without identical cohort keys and executable human reference bodies; missing comparability must remain visible.
- No blanket staging, `git add -A`, cleanup/revert of unrelated dirty files, or commit containing paths outside the todo allowlist.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: contract TDD with `pytest` for CL-R01..R06; tests-after for documentation/dashboard presentation; official isolated-driver and browser QA for CL-R07..R10.
- Every todo records a pre/post `git status --porcelain=v1` snapshot and fails if changed paths exceed its explicit allowlist.
- Cheap contract ladder: focused unit tests per todo, then `pytest tests/unit/ -q`, `python scripts/verify_nonrelease_sync.py`, `git diff --check`, and protected-path status.
- Database tests use `tmp_path` SQLite only and trace SQL to reject UPDATE/DELETE in evidence tables; schema migration is replayed twice to prove idempotency.
- Official backtest evidence is valid only when exit code, status, CSV hash, profile hash, positive/negative controls, timeout/cleanup state, and state/receipt rows agree.
- OOS evidence is valid only when preregistration and candidate/config/profile hashes predate the one-time access receipt and no later generation exists.
- Dashboard QA uses the in-app browser against a local service and verifies real API payloads, three viewport widths, empty/error/stale states, and cohort mismatch behavior.
- Evidence: `.omo/evidence/task-<N>-ai-condition-loop-canonical-rebuild-20260711/` with compact JSON/MD/log receipts; never commit bulky runtime outputs.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

| Wave | Todos | Authority boundary | Outcome |
|---|---|---|---|
| 0 | 1 -> 2 -> 3 -> 4 -> 5 | `$start-work` authorizes design/docs only | Verified CL-D package, durable plan/handoff, pointer updates, docs commit; then hard stop |
| 1 | 6 -> (7 + 9) -> 8 -> 10 | exact CL-R01-R06 code approval | Canonical phase contract, typed evidence models/store, CLI provenance/fingerprints, controller passport wiring |
| 2 | 11 + 12 -> 13; 17 may start after 13 contracts freeze | same CL-R01-R06 approval | Durable feedback, semantic diversity, 2x2 attribution, frozen manifests, dashboard/API contract implementation |
| 3 | 14 -> 15 | separate CL-R07 then CL-R08 approvals | Three-round process proof, then bounded historical min performance verdict |
| 4 | 16 + final 17 QA -> 18 | separate CL-R09 then CL-R10 approvals and prospective data availability | One-time sealed OOS/WF, finalized cohort-safe UI, normalized benchmark or explicit non-comparability, promotion-review closeout |
| Final | F1 + F2 + F3 + F4 | all prior receipts | Independent plan/code/runtime/scope verification; user acceptance required |

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 2 | none |
| 2 | 1 | 3 | none |
| 3 | 2 | 4 | none |
| 4 | 3 | 5, 6 | none |
| 5 | 1-4 | 6 | none |
| 6 | 5 + code approval | 7, 9 | none |
| 7 | 6 | 8, 10, 11 | 9 |
| 8 | 7 | 10, 11, 17 | 9 |
| 9 | 6 | 10, 12 | 7, 8 after 7 |
| 10 | 8, 9 | 11, 12, 13 | none |
| 11 | 7, 8, 10 | 13 | 12 |
| 12 | 9, 10 | 13 | 11 |
| 13 | 11, 12 | 14, 17 | none |
| 14 | 13 + CL-R07 approval | 15 | 17 |
| 15 | 14 + CL-R08 approval | 16 | 17 |
| 16 | 15 + CL-R09 approval + prospective data | 18 | none |
| 17 | 8, 10, 13 | 18 | 14, 15 |
| 18 | 16, 17 + CL-R10 approval | final wave | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. CL-D0 source receipt, authority hierarchy, and scope lock
  What to do / Must NOT do: Read every source named by the Jul-09 V3 plan to EOF; record path, line count, SHA-256, role (`goal_authority`, `execution_contract`, `closure_evidence`, `supporting_history`), and applied sections in `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/source_read_receipt_v3_design_20260709.json`. Record current branch/HEAD/upstream and full dirty-worktree baseline hash, but list unrelated paths only in the receipt and never alter them. Set scope exactly to `design_only_no_generation_no_db_no_replay_no_oos_no_plan_d_no_portfolio_no_export_live`. Must not generate bodies, import a provider, open runtime DBs, or run backtests.
  Parallelization: Wave 0 | Blocked by: none | Blocks: 2
  References (executor has NO interview context - be exhaustive): `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:113-205`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:1-43,276-284`; `docs/AGENT_HANDOFF.md:10`; `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md:1-60`; root and `docs/AGENTS.md`.
  Acceptance criteria (agent-executable): A JSON verifier recomputes every SHA/line count, asserts required sources are complete, asserts exactly one authority per role, asserts the design-only scope string, and writes `.omo/evidence/task-1-ai-condition-loop-canonical-rebuild-20260711/verification.json`; `git status --short --` protected paths is empty.
  QA scenarios (exact tool + invocation): Happy: run the verifier against the completed receipt and require exit 0. Failure: copy the receipt to temp, change one SHA and scope to include `replay`, require nonzero exit with `sha_mismatch` and `forbidden_scope`. Evidence `.omo/evidence/task-1-ai-condition-loop-canonical-rebuild-20260711/`.
  Commit: NO | accumulated into todo 5 docs commit.

- [ ] 2. CL-D1 consolidated failure-lesson matrix with reusable/forbidden conclusions
  What to do / Must NOT do: Create `lattice_v3_failure_lesson_matrix_20260709.md` covering tick 288, min 288, integrated 576, repair composite, bounded Plan D, V2 eight-body replay, corrected sell/risk audit, and latest batch-vs-autonomous distinction. For each, separate engine/profile/process, gate threshold, entry structure, exit/risk, data leakage/blindness, reusable asset, and forbidden inference. State `gate_relaxation_is_not_sufficient`, `v2_sell_risk_table_superseded_but_decision_unchanged`, and `provider_batch_is_not_autonomous_learning`. Must not relabel no-go rows as survivors or promote repair/Plan D evidence.
  Parallelization: Wave 0 | Blocked by: 1 | Blocks: 3
  References: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:207-250`; `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md:60-111`; `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md:19-60`; `ai_strategy_loop/state/current_state.json`; `ai_strategy_loop/scripts/claude_candidate_batch_eval.py:72-171`.
  Acceptance criteria: Static verifier asserts every evidence family and mandatory conclusion, rejects any `go`/`hold` reinterpretation, and cross-checks V2 counts `8/7/1/0/0/8`; output `.omo/evidence/task-2-ai-condition-loop-canonical-rebuild-20260711/verification.json`.
  QA scenarios: Happy: complete matrix passes. Failure: temp copy omits Plan D and changes “7/7 negative” to “6/7”; verifier fails with explicit missing/mismatch codes. Evidence task-2 directory.
  Commit: NO | accumulated into todo 5 docs commit.

- [ ] 3. CL-D2 sole canonical design specification and collision-free phase glossary
  What to do / Must NOT do: Write `lattice_v3_design_spec_20260709.md` as the sole canonical design contract. Required sections: objective/non-objective, authority hierarchy, `Broad-Grid-576`/`Failure-Guided-8`/`Canonical-Loop-Next` glossary, canonical IDs `CL-D0..D4` and `CL-R01..R10` with legacy T/P aliases, controller ownership, approved/excluded inputs, Candidate Passport/Feedback/Evaluation/Run schemas, exact immutable ID/hash rules, append-only store rules, min/tick lane policy, semantic identity, 2x2 attribution, numerical budgets, sealed OOS policy, human-comparability policy, and go/no-go table. Designate every other V3 artifact as supporting evidence. Must not contain generated buy/sell bodies, seed JSON arrays, DB apply commands, or authority to execute later phases.
  Parallelization: Wave 0 | Blocked by: 2 | Blocks: 4
  References: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:254-310`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:45-81,128-183,185-249`; `ai_strategy_loop/controller/state.py:30-51,121-246`; `ai_strategy_loop/controller/loop.py:1099-1219`; `cli/condition_generator.py:25-255`.
  Acceptance criteria: A canonical-spec verifier asserts required headings, exactly one `sole canonical` declaration, complete phase alias rows, exact approval phrases/numerical caps, and absence of body/DB/replay instructions; a repository scan finds no second active canonical spec. Evidence `.omo/evidence/task-3-ai-condition-loop-canonical-rebuild-20260711/verification.json`.
  QA scenarios: Happy: canonical spec passes. Failure: temp copy removes CL-R05, inserts `buy_code`, and changes the canonical declaration; verifier reports all three defects. Evidence task-3 directory.
  Commit: NO | accumulated into todo 5 docs commit.

- [ ] 4. CL-D3 executable phase-state protocol, approval stops, and preregistration schemas
  What to do / Must NOT do: Create `lattice_v3_evaluation_protocol_20260709.md` and `lattice_v3_next_command_20260709.md`. Define a deterministic state machine for every CL phase with predecessor receipt, permitted mutation, forbidden action, exact approval phrase, stop state, and failure transition. Evidence never grants authority. Include INSERT-only evidence semantics, five later approval phrases, frozen R07/R08 budgets, OOS custodian/access schema, human cohort manifest, and rule that dashboard work cannot reinterpret evidence. Next command may start CL-D only; it must stop after todo 5. Must not include code integration, DB apply, replay, OOS, or benchmark execution commands.
  Parallelization: Wave 0 | Blocked by: 3 | Blocks: 5, 6
  References: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:314-365`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:185-221,251-284`; `.omo/drafts/ai-condition-loop-canonical-rebuild-20260711.md` decisions 14-21; `ai_strategy_loop/controller/replay_profile.py:20-142`.
  Acceptance criteria: State-machine verifier traverses the valid CL-D path, rejects every out-of-order transition, rejects a forged receipt without approval, rejects UPDATE/DELETE events, and confirms the next command contains design scope only. Evidence `.omo/evidence/task-4-ai-condition-loop-canonical-rebuild-20260711/verification.json`.
  QA scenarios: Happy: D0->D4 transitions pass and end `awaiting_CL_R01_R06_approval`. Failure: attempt D2->R07 and receipt-only R08 transition; both fail closed with expected codes. Evidence task-4 directory.
  Commit: NO | accumulated into todo 5 docs commit.

- [ ] 5. CL-D4 durable master plan, self-contained handoff, pointer correction, and docs-only commit
  What to do / Must NOT do: Materialize `docs/research/condition_research/plans/2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md` as the human-readable governance mirror of this `.omo` plan and create `docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md` with cold-start order, authority hierarchy, current commit/branch, completed/locked phases, exact next command, approvals, source/code/test maps, dirty-worktree warning, stop/recovery rules, and expected effects. Correct the Jul-11 audit P/T ambiguity to CL-D/CL-R and add latest-first supersession banners to `docs/AGENT_HANDOFF.md` and the Jul-09 cross-agent handoff while preserving historical bodies. Write the V3 design-only handoff/verification receipts required by the subordinate plan. Stage only the explicit docs allowlist and commit in Korean. Must not touch `.omo` leftovers, dashboard files, code, runtime state, or protected paths.
  Parallelization: Wave 0 | Blocked by: 1-4 | Blocks: 6
  References: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:370-457`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:185-221`; `docs/AGENT_HANDOFF.md:5,19-21,88-92`; `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md:10-29,159-178,248-257`; `AGENTS.md`; `docs/AGENTS.md`.
  Acceptance criteria: All durable files and pointers exist; handoff cold-start checker resolves every referenced path; audit contains no ambiguous `P1/T0` rows; protected-path status is empty; staged set equals the explicit docs allowlist; `git diff --cached --check` passes; commit subject is `docs(research): AI 조건식 루프 정본 계획과 핸드오프 기록`; after commit the allowlisted paths are clean and unrelated dirty count/hash is unchanged.
  QA scenarios: Happy: a fresh-agent checker reads only the new handoff and resolves objective, current phase, next command, approvals, and every dependency. Failure: temp handoff points to a missing plan and authorizes replay; checker fails. Evidence `.omo/evidence/task-5-ai-condition-loop-canonical-rebuild-20260711/` including staged diff and commit hash.
  Commit: YES | `docs(research): AI 조건식 루프 정본 계획과 핸드오프 기록` with Korean markdown body listing plan, phase aliases, handoff, and pointer corrections.

- [ ] 6. CL-R01 canonical phase contract and fail-closed approval guard
  What to do / Must NOT do: Stop unless the exact user record `I approve CL-R01-R06 code integration only` exists in the handoff/intake receipt. With contract tests first, add `ai_strategy_loop/controller/phase_contract.py` and `scripts/verify_ai_loop_phase_contract.py`. Define enums for every CL phase/state, legacy aliases, predecessor evidence schemas, exact approval requirements, permitted mutations, terminal/blocked outcomes, and transition validation. The guard must distinguish `evidence_valid` from `authority_valid`; neither defaults true. Existing batch/research commands may record evidence but cannot set the canonical phase. Must not inspect approval prose loosely, infer permission from a receipt, or enable a runtime feature by default.
  Parallelization: Wave 1 | Blocked by: 5 + exact code approval | Blocks: 7, 9
  References: `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_evaluation_protocol_20260709.md`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:185-221,276-284`; `ai_strategy_loop/controller/contract.py:24-104`; `ai_strategy_loop/controller/state.py:53-58,737-766`; exact approval decisions in the todo-5 durable master plan.
  Acceptance criteria: `pytest tests/unit/test_ai_loop_phase_contract.py -q` passes; verifier accepts the complete D0->D4 path and rejects missing/forged approval, receipt-only authority, wrong alias, and all out-of-order CL-R transitions; default config reports `CL-D4_AWAITING_APPROVAL` without code execution.
  QA scenarios: Happy: temp receipts + exact phrase allow R01 and no later phase. Failure: valid D4 receipt without approval and approval with stale/mismatched plan hash both fail. Evidence `.omo/evidence/task-6-ai-condition-loop-canonical-rebuild-20260711/`.
  Commit: YES after phase approval | `feat(ai-loop): 조건식 루프 단계 권한 계약 추가`.

- [ ] 7. CL-R02 immutable evidence contracts, IDs, canonical JSON, and manifests
  What to do / Must NOT do: With tests first, add `ai_strategy_loop/controller/evidence_contract.py` using frozen stdlib dataclasses and boundary validators. Define exact schemas: `CandidatePassport` (schema/passport/candidate/run/round/gen/slot/parent/mode/lane/family/timeframe, strategy names, buy/sell SHA-256, AST+rowset fingerprints, evidence IDs, threshold provenance, manifest ID, UTC creation); `FeedbackEnvelope` (feedback/source passport/autopsy kind+side/source result SHA/directives/rendered text+SHA/UTC); `FeedbackConsumption` (consumption/feedback/prompt/target passport/UTC); `EvaluationManifest` (profile/data/universe/methodology/timeframe/scope/session/period/capital/cost/fill/role/code+config hashes); `RunReceipt` (receipt/run/phase/outcome/stop reason/budget counters/predecessor IDs/artifact hashes/UTC). Canonical JSON is UTF-8, NFC, sorted keys, compact separators; code normalizes CRLF to LF. IDs use full SHA-256 with stable prefixes; `candidate_id` is content+methodology identity, `passport_id` is run/round/gen/slot scoped. Must not accept NaN/Infinity, local timestamps, mutable dict/list fields, missing hashes, or unknown enum values.
  Parallelization: Wave 1 | Blocked by: 6 | Blocks: 8, 10, 11 | Can parallelize with: 9
  References: `ai_strategy_loop/controller/replay_profile.py:20-100`; `ai_strategy_loop/autopsy/trade_ledger.py:72-125`; `ai_strategy_loop/seeds/passport.py:83-133`; `ai_strategy_loop/controller/state.py:301-430`; `.omo/drafts/ai-condition-loop-canonical-rebuild-20260711.md` decisions 4-6.
  Acceptance criteria: `pytest tests/unit/test_evidence_contract.py -q` proves cross-platform deterministic hashes, round-trip JSON, immutable collections, parent/root candidates, seed/fresh/refine modes, exact timestamp/enums, and rejects every invalid boundary. Golden receipt SHA remains stable across two processes.
  QA scenarios: Happy: construct, serialize, restore, and hash all five types. Failure: CRLF/NFC equivalence must hash the same; NaN, missing buy hash, unknown side, local timestamp, and mutable post-construction input must fail or remain immutable as specified. Evidence task-7 directory.
  Commit: YES after phase approval | `feat(ai-loop): 후보와 피드백 증거 계약 추가`.

- [ ] 8. CL-R03 append-only EvidenceStore and idempotent LoopState schema v11
  What to do / Must NOT do: With temp-SQLite tests first, add `ai_strategy_loop/controller/evidence_store.py`; compose it with the existing `LoopState` connection rather than opening a second canonical DB. Raise `SCHEMA_VERSION` from 10 to 11 and initialize five tables: `candidate_passports(passport_id PK, candidate_id, run_id, round_no, gen_no, slot_no, parent_passport_id NULL, manifest_id, payload_json, created_at, UNIQUE(run_id,round_no,gen_no,slot_no))`; `feedback_envelopes(feedback_id PK, source_passport_id FK, payload_json, created_at)`; `feedback_consumptions(consumption_id PK, feedback_id FK, prompt_id, target_passport_id FK, created_at, UNIQUE(feedback_id,prompt_id,target_passport_id))`; `evaluation_manifests(manifest_id PK, run_id, role, payload_json, created_at, UNIQUE(run_id,role))`; `run_receipts(receipt_id PK, run_id, phase_id, outcome, payload_json, created_at)`. Enable foreign keys, add query indexes, use one INSERT-only transaction per event, treat identical duplicate inserts as idempotent and mismatched duplicates as corruption. Snapshot to `state/snapshots/<run_id>/evidence/<type>/<id>.json` after commit; DB is canonical, snapshots are recovery/read mirrors only. Never UPDATE/DELETE evidence rows or auto-import snapshots.
  Parallelization: Wave 1 | Blocked by: 7 | Blocks: 10, 11, 17 | Can parallelize with: 9 after 7
  References: `ai_strategy_loop/controller/state.py:1-113,118-246,301-430`; `tests/unit/test_state_concurrency.py:23-102`; `tests/unit/dashboard/test_loopstate_readonly.py`; `AGENTS.md` protected/runtime rules.
  Acceptance criteria: `pytest tests/unit/test_evidence_store.py tests/unit/test_state_concurrency.py tests/unit/dashboard/test_loopstate_readonly.py -q` passes; migration 10->11 and fresh v11 run twice without change; SQL trace contains no evidence-table UPDATE/DELETE; readonly dashboard creates no WAL/DDL; crash before commit leaves zero partial rows; crash after commit can reconstruct from DB and matching snapshot.
  QA scenarios: Happy: append a full passport->feedback->consumption->receipt chain and query by run/gen/ID. Failure: conflicting duplicate ID, broken FK, UPDATE/DELETE, corrupt snapshot, and mid-transaction exception fail closed without partial chain. Evidence task-8 directory with schema/SQL traces.
  Commit: YES after phase approval | `feat(ai-loop): 증거 저장소와 상태 스키마 v11 추가`.

- [ ] 9. CL-R04 B-only provenance and semantic/rowset fingerprinting at every candidate boundary
  What to do / Must NOT do: With tests first, add `cli/condition_fingerprint.py`; extend `cli/analyzer.py`, `cli/condition_generator.py`, `cli/research_loop.py`, `ai_strategy_loop/brain/pack_producer.py`, and context-pack wiring. Require an explicit timeframe-specific approved B-variable registry at ingestion, parse expressions with Python AST, allow only Boolean/Compare/name/numeric nodes, normalize Unicode identifiers, numeric Decimal form, chained bounds, commutative AND/OR child order, and reject calls/attributes/subscripts/unknown names/result/S_/R_ variables. Bind AST fingerprint to timeframe+methodology version; bind rowset fingerprint to dataset/window hash plus sorted stable row keys. Threshold provenance must include estimator (`bucket`, `quantile`, `median_ttest`, `model_importance`), parameters, fit role, period, row count/signature, dataset SHA, fold ID, and source receipt. Enforce existing fingerprints and zero semantic duplicates before provider/backtest quota. Must not use regex-only validation, full-baseline validation/OOS rows for threshold fit, or silently fall back to uncredited unsafe candidates.
  Parallelization: Wave 1 | Blocked by: 6 | Blocks: 10, 12 | Can parallelize with: 7
  References: `cli/analyzer.py:67-68,114-175,247-343`; `cli/condition_generator.py:25-155,159-255,339-428`; `cli/research_loop.py:114-139,1268-1480,2549-2581`; `ai_strategy_loop/brain/variable_scope.py`; `tests/unit/test_condition_generator.py:13-310`; `tests/unit/test_pack_producer.py:158-527`.
  Acceptance criteria: focused condition-generator/pack/context/research tests pass plus new `test_condition_fingerprint.py`; `UNKNOWN > 1`, S_/R_, function calls, profile-mismatched B variables, semantic reorder duplicates, and provenance omissions all fail; equivalent whitespace/order/numeric forms share AST fingerprint; different data windows produce different rowset fingerprints.
  QA scenarios: Happy: four approved B expressions across repair/discovery yield unique passports with complete provenance. Failure: external pack injects unknown/S_/R_ and an AND-reordered duplicate; ingestion returns explicit blockers and performs zero controller calls. Evidence task-9 directory.
  Commit: YES after phase approval | `feat(research): 조건식 근거와 의미 중복 검증 강화`.

- [ ] 10. CL-R04 canonical controller passport, manifest, and run-receipt wiring
  What to do / Must NOT do: With integration tests first, make narrow orchestration changes in `controller/loop.py`, `brain/generator.py`, and `controller/state.py`. At run start freeze one evaluation manifest. Preserve generated buy/sell code from `generate_strategy`; after generation/static acceptance and before backtest, build/persist one passport for seed/fresh/refine candidates. Store parent passport, proposal slot, candidate-pack/provenance IDs, and code hashes. Append backtest outcome and run-stop receipts at existing outcome/finish seams. Batch evaluator must publish `execution_kind=fixed_batch` and may never advance canonical lineage. Generation rows may reference passport IDs additively but evidence data stays in EvidenceStore. Must not alter backengine/fitness gates, create a second run loop, or write an operating strategy DB in tests.
  Parallelization: Wave 1 | Blocked by: 8, 9 | Blocks: 11, 12, 13, 17
  References: `ai_strategy_loop/controller/loop.py:1099-1435,1442-1805`; `ai_strategy_loop/brain/generator.py:193-295,457-505`; `ai_strategy_loop/controller/state.py:266-430,737-766`; `ai_strategy_loop/scripts/claude_candidate_batch_eval.py:72-171`; `tests/unit/test_lineage.py:54-174`; `tests/unit/test_loop_lineage_meta_wiring.py`.
  Acceptance criteria: new `tests/unit/test_canonical_passport_wiring.py` plus loop robustness/lineage/state tests pass; a mocked two-generation run produces one manifest, two linked passports, outcome/stop receipts, stable hashes, and no unlinked generation; seed root has null parent; batch run has no canonical passport progression; generated-code/hash mismatch fails before backtest.
  QA scenarios: Happy: seed->refine chain persists and reconstructs. Failure: generator returns altered name/code, EvidenceStore insert fails, or batch claims autonomous kind; controller fails/records error without running backtest or corrupting lineage. Evidence task-10 directory.
  Commit: YES after phase approval | `feat(ai-loop): 정본 후보 여권과 실행 영수증 연결`.

- [ ] 11. CL-R05 durable feedback envelope, resume restoration, and consumption proof
  What to do / Must NOT do: With tests first, replace raw transient-only feedback handling with typed envelopes while preserving rendered strings for prompts. When buy/exit/error/segment/feature/hypothesis autopsy completes, append a FeedbackEnvelope linked to the source passport/result hash. On normal continuation or resume, query the newest unconsumed eligible envelope; pass its ID and rendered content through `_generate_pair -> generate_strategy -> build_messages`; write the feedback ID into structured prompt metadata; only after the prompt receipt exists append FeedbackConsumption linking source envelope, prompt, and target passport. If provider/generation fails before target passport creation, leave the envelope unconsumed and safely retry once on resume. Verify the resulting AST diff contains at least one commanded clause change or explicitly records `feedback_noop_rejected`. Must not UPDATE a status flag, consume before prompt persistence, carry stale feedback after a backtest-without-CSV error, or count mere prompt text as learning proof.
  Parallelization: Wave 2 | Blocked by: 7, 8, 10 | Blocks: 13 | Can parallelize with: 12
  References: `ai_strategy_loop/controller/loop.py:1150-1219,1385-1414,1513-1528,1722-1756,2202-2348`; `ai_strategy_loop/brain/generator.py:193-295`; `ai_strategy_loop/brain/prompt.py:1277-1293`; `tests/unit/test_autopsy.py:231-308`; `tests/unit/test_feedback_toggles_on.py:323-386`; `tests/unit/test_error_feedback.py:140-222`.
  Acceptance criteria: focused autopsy/error/feedback tests plus new `test_feedback_evidence_wiring.py` pass; two-generation and stop/resume tests prove one source envelope, one prompt link, one target passport, one immutable consumption row, and an expected AST clause delta; SQL trace contains no UPDATE/DELETE.
  QA scenarios: Happy: gen0 loss produces feedback, process restarts, gen1 consumes it and changes the targeted clause. Failure: crash before prompt, crash after prompt before passport, provider error, no-op candidate, and corrupt envelope each yield deterministic retry/rejection without double consumption. Evidence task-11 directory.
  Commit: YES after phase approval | `feat(ai-loop): 세대 피드백 영속과 소비 증거 연결`.

- [ ] 12. CL-R06 bounded candidate pool, semantic quotas, and 2x2 buy/sell attribution
  What to do / Must NOT do: With tests first, add a small candidate-pool selector (reuse existing selection helpers where possible) and `ai_strategy_loop/controller/ablation_matrix.py`. Every round accepts exactly four proposals: two `repair`, two `discovery`; no semantic duplicate; maximum two of one family; deterministic tie order by static validity, provenance completeness, novelty, then candidate ID. The static selector chooses exactly one official candidate and records rejection reasons for the other three. Define four ablation arms on identical manifest/profile/seed/cost inputs: A parent-buy+parent-sell, B candidate-buy+parent-sell, C parent-buy+candidate-sell, D candidate-buy+candidate-sell. Compute `buy_effect=B-A`, `sell_effect=C-A`, `interaction=D-B-C+A` for profit, MDD delta (sign-normalized), trade count, and daily frequency. Missing/error arm invalidates attribution; it never substitutes a partial causal claim. Must not spend official quota on semantic duplicates or run an unbounded cartesian combination.
  Parallelization: Wave 2 | Blocked by: 9, 10 | Blocks: 13 | Can parallelize with: 11
  References: `cli/research_loop.py:2767-2797,3109-3120`; `tests/unit/test_condition_ablation.py:99-437`; `tests/unit/test_research_iteration_v4.py:177-323`; `tests/unit/test_token_check.py:142-180`; `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:254-279`.
  Acceptance criteria: new candidate-pool and ablation tests plus existing ablation/diversity/token tests pass; shuffled input produces identical selection; duplicate/family quota violations consume zero evaluator calls; complete 2x2 fixture yields exact effects; one failed arm returns `attribution_invalid` with no buy/sell winner claim.
  QA scenarios: Happy: four distinct candidates select one deterministically and a complete 2x2 matrix emits a signed attribution receipt. Failure: whitespace/reordered duplicate, third same-family candidate, missing parent sell, and timeout arm fail with exact reason and bounded call count. Evidence task-12 directory.
  Commit: YES after phase approval | `feat(ai-loop): 후보 다양성과 매수매도 기여도 검증 추가`.

- [ ] 13. CL-R07 preregistration freeze and isolated three-round mini-loop driver
  What to do / Must NOT do: Before any result-bearing run, add versioned manifests and a CLI driver `ai_strategy_loop/scripts/run_canonical_mini_loop.py`. Freeze: learning profile (min/single_stock/five days/engine1/betting5/avg30/timeout300/warm120/MDD40/min-trades30/min-daily0.5), exactly three rounds, four proposals/round, one evaluated candidate/round, one fixed positive and one fixed negative control, final-candidate 2x2 attribution, max nine official evaluations, max three provider pack calls, 120-minute wall cap, and all stop reasons. Also preregister CL-R08 historical 60-day split/thresholds, CL-R09 prospective post-2026-07-11 20-day rule, and CL-R10 human cohort before CL-R07 writes results. Driver requires an isolated strategy DB path and evidence directory, validates all plan/profile/data/code hashes, and refuses operating DB paths. Unit/integration tests inject fake provider/evaluator; do not run the official engine in this todo.
  Parallelization: Wave 2 | Blocked by: 11, 12 | Blocks: 14, 17
  References: `ai_strategy_loop/config.py:31-44,68-115,173-189`; `ai_strategy_loop/controller/replay_profile.py:50-142`; `ai_strategy_loop/scripts/e2e_smoke.py:1-18,359-363`; `tests/unit/test_smoke_budget.py:51-240`; decisions 16-20 in the draft.
  Acceptance criteria: driver `--help` exits 0; fake happy run creates frozen preregistration, manifest/passport/feedback/ablation/run receipts with exact counters and no operating paths; cap/timeout/hash/profile mismatch stops before excess call; tests prove R08/R09/R10 manifests predate first R07 result.
  QA scenarios: Happy: deterministic fake three-round loop yields exactly 12 proposals, 3 primary evaluations, 2 controls, 4 ablation arms, and two feedback consumptions within cap. Failure: fourth provider call, tenth evaluation, 121-minute simulated clock, operating DB path, or post-result manifest edit fails closed. Evidence task-13 directory.
  Commit: YES after phase approval | `feat(ai-loop): 제한 폐루프 사전등록과 실행기 추가`.

- [ ] 14. CL-R07 approved official mini-loop process proof on isolated databases
  What to do / Must NOT do: Stop unless the exact user approval `I approve CL-R07 bounded mini-loop only` and valid todo-13 receipt exist. Create isolated copies/temporary strategy and min data inputs outside tracked/protected paths, record source/copy hashes and ACLs, run the driver once with the frozen profile, and capture exit/status, process cleanup, provider/evaluation counts, control results, every passport/feedback/consumption/ablation receipt, CSV hashes, and protected-path before/after diff. The success criterion is an unbroken learning chain and budget compliance, not profitability. Do not tune/retry after reading results; a technical failure may be retried only from the same hashes after a written failure receipt and user-visible reason.
  Parallelization: Wave 3 | Blocked by: 13 + exact CL-R07 approval | Blocks: 15 | Can parallelize with: 17
  References: todo-13 `ai_strategy_loop/scripts/run_canonical_mini_loop.py` and preregistration manifest; `ai_strategy_loop/scripts/e2e_smoke.py:359-363`; `cli/runner.py`; `backtest/backtest.py`; `AGENTS.md` protected-path rules; `tests/unit/test_positive_control.py`.
  Acceptance criteria: command exits 0; exactly three primary generations exist; gen2/gen3 each consume the preceding feedback and contain a non-noop clause change; controls are correctly classified; official evaluations <=9, provider calls <=3, elapsed <=120 minutes; no orphan engine/process; protected and unrelated worktree hashes unchanged. Write compact closeout `docs/update_log/2026-07-11_cl_r07_bounded_mini_loop_result.md` and machine receipt; do not call it alpha proof.
  QA scenarios: Happy: one complete official run satisfies process proof. Failure: no-trades/timeout/provider failure/feedback no-op produces `CL-R07_NO_GO` with cleanup and blocks R08; a same-hash technical retry cannot exceed the total budget. Evidence task-14 directory.
  Commit: YES after approved run | docs/result receipts only, `docs(research): CL-R07 제한 폐루프 결과 기록`; never commit DB/CSV/log bulk.

- [ ] 15. CL-R08 approved bounded historical min performance page
  What to do / Must NOT do: Stop unless CL-R07 is `GO_PROCESS_PROOF` and the exact approval `I approve CL-R08 bounded min performance only` exists. Resolve the last 60 complete min trading days ending no later than 2026-07-11 from the isolated source hash; freeze first 40 as train and last 20 as validation. Select the top 20 liquid symbols using train-only aggregate trade amount and freeze their IDs/hash. Before any backtest, generate and freeze exactly eight candidates (four repair/four discovery, max two/family, zero semantic duplicates), then make no provider calls. Evaluate all eight on train; preselect at most three by train gates and deterministic order; evaluate those unchanged on validation. Gates on both partitions: profit after engine costs >0, MDD <=35, daily average >=0.5, no timeout/error; validation must also have positive profit in each chronological half. Select one survivor lexicographically by validation worst-half profit, total profit, lower MDD, then candidate ID. Maximum official evaluations 11 and wall cap 4 hours. Must not inspect validation to mutate candidates, change thresholds, reopen V2/Plan D, or call this OOS.
  Parallelization: Wave 3 | Blocked by: 14 + exact CL-R08 approval | Blocks: 16 | Can parallelize with: 17
  References: frozen R08 manifest from todo 13; `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:254-279,314-335`; `ai_strategy_loop/config.py:31-44`; `cli/research_loop.py:2767-2797,3109-3120`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:165-174,208-221`.
  Acceptance criteria: all manifests/hashes predate first train result; provider calls after first result equal zero; evaluations <=11/time <=4h; train-only universe proof exists; validation candidate bodies/hashes equal train; machine verdict is exactly `GO_R09_ONE_SURVIVOR` or `NO_GO_STOP`; no-go performs no OOS access. Write compact result/receipt and protected-path diff.
  QA scenarios: Happy: at least one unchanged candidate passes all train/validation gates and deterministic tie-break. Failure: zero survivors, validation half loss, post-train body change, ninth candidate, twelfth evaluation, or time cap yields `NO_GO_STOP` and locks R09. Evidence `.omo/evidence/task-15-ai-condition-loop-canonical-rebuild-20260711/`.
  Commit: YES after approved run | docs/result receipts only, `docs(research): CL-R08 제한 성능 검증 기록`.

- [ ] 16. CL-R09 mechanically sealed prospective OOS/WF custodian and one-time execution
  What to do / Must NOT do: Stop unless CL-R08 has one frozen survivor, the exact approval `I approve CL-R09 sealed OOS/WF only` exists, and `STOM_AI_LOOP_SEALED_OOS_DB` points to 20 complete trading days strictly after 2026-07-11. With tests first, add a narrow custodian script that is the only process receiving the OOS path. It validates prospective dates, source SHA/size/read-only ACL, survivor/config/profile/prereg hashes, one-day purge before OOS, no OOS identifiers in prior prompts/manifests, and no previous access receipt; then appends `oos_opened` and launches the official runner without provider/generation imports. Split the 20 days into four fixed five-day folds; use unchanged candidate and profile. After opening, phase guard permanently rejects further candidate generation for this lineage. Gates: total profit >0, MDD <=35, daily average >=0.5, all four folds nonnegative, no timeout/error, and base plus preregistered cost-stress calculation pass. Any contamination or later generation invalidates the claim.
  Parallelization: Wave 4 | Blocked by: 15 + exact CL-R09 approval + prospective data | Blocks: 18
  References: `ai_strategy_loop/fitness/holdout.py:19-27,200-208` (validation-only limitation); `ai_strategy_loop/controller/replay_profile.py:50-142`; `tests/unit/test_promotion_preconditions.py:182-255`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:150-174,223-228`; `AGENTS.md` protected-path rules.
  Acceptance criteria: custodian unit tests deny pre-freeze, reused receipt, pre-2026-07-12 dates, writable/mismatched source, leaked OOS identifier, provider import, or post-open generation; approved official run creates one immutable access receipt and four fold receipts; candidate/config/profile hashes are identical across folds; verdict is `GO_R10` or `NO_GO_FINAL`.
  QA scenarios: Happy: one-time prospective run passes or honestly fails with complete folds and no generation access. Failure: attempt a second open, change candidate, expose OOS path to generator, or append a later passport; verifier invalidates OOS and blocks R10. If 20 days are not yet available, write `WAITING_FOR_PROSPECTIVE_DATA` and stop without opening. Evidence task-16 directory.
  Commit: YES after approved run/data availability | custodian code/tests commit under `feat(ai-loop): 봉인 OOS 실행 경계 추가`; small result docs commit separately, never OOS DB/CSV.

- [ ] 17. CL-R10 dashboard/state provenance, historical reconstruction, and cohort-safe HOF contract
  What to do / Must NOT do: After evidence/API schemas freeze, extend state contract/API/frontend without changing execution ownership. Add distinct `state_contract_version`, `state_db_schema_version`, `hof_payload_version`, `human_benchmark_version`, and `evaluation_methodology_version`. Persist/freeze cohort fields in evaluation manifests; `/hall_of_fame` returns cohort key, comparability boolean/reasons, methodology/caveat fields, and groups/sorts only within identical cohorts. Preserve reference metadata and distinguish human reported annual return from AI computed annualization. Historical `/run_state` reconstructs lineage, passport, feedback links, and source=`db_reconstructed`; current state exposes age/stale/DB-conflict/degraded-contract status. Frontend shows provenance/version badges, comparable groups, unranked non-comparable rows, feedback lineage, and stale warnings at 1440/1180/980 widths. Must not merge cohorts globally, imply missing historical feedback is live, add a framework/dependency, or modify dirty generated bundles outside the explicit source/build allowlist.
  Parallelization: Waves 2-3 | Blocked by: 8, 10, 13 | Blocks: 18 | Can parallelize with: 14, 15
  References: `ai_strategy_loop/dashboard/app.py:177-187,739-961,1464-1469`; `ai_strategy_loop/dashboard/reference_strategies.json:2-7`; `ai_strategy_loop/dashboard/frontend/chart-hall-of-fame.jsx:53-69,107-110,168-252`; `ai_strategy_loop/dashboard/frontend/panels-analysis.jsx:447-515`; `ai_strategy_loop/controller/contract.py:24-104`; `ai_strategy_loop/controller/state.py:973-1086`; `ai_strategy_loop/AGENTS.md`.
  Acceptance criteria: focused dashboard/state tests pass; API fixtures prove incompatible min/tick or period/cost cohorts cannot share rank; missing executable human bodies return an explicit reason; historical run shows DB lineage/feedback availability; stale snapshot/DB conflict is surfaced; browser QA confirms three widths, empty/error states, no console errors, and source bundles match built artifacts.
  QA scenarios: Happy: comparable cohort ranks internally and a historical chain remains inspectable after restart. Failure: min single-stock AI vs human tick, inconsistent human metadata, stale JSON vs newer DB, and missing feedback persistence all show warnings/unranked state rather than success. Evidence task-17 directory with screenshots/API JSON/console log.
  Commit: YES after code approval | `feat(dashboard): 조건식 근거와 비교 가능성 표시 강화` with explicit source/generated paths only.

- [ ] 18. CL-R10 approved human benchmark or explicit non-comparability, promotion review, and final handoff
  What to do / Must NOT do: Stop unless CL-R09 verdict is `GO_R10` and exact approval `I approve CL-R10 benchmark promotion review only` exists. Freeze authoritative human source inventory before opening AI OOS results: executable buy/sell bodies and hashes, same period/universe/timeframe/session/capital/cost/fill/engine/methodology, missing-data policy, ranking formula, and tie rule. If any required executable/cohort field is absent, emit `not_comparable_missing_executable_reference`, keep AI/human unranked, and prohibit a human-level claim. If an identical executable cohort exists, run both unchanged, compare cost-adjusted profit, MDD, daily frequency, worst fold and predefined risk-adjusted score, and record complete receipts. Promotion review is analysis only; it cannot export/live. Update final durable handoff with all phase verdicts, receipts, remaining locks, exact resume command, and honest achieved/not-achieved statement.
  Parallelization: Wave 4 | Blocked by: 16, 17 + exact CL-R10 approval | Blocks: final verification
  References: `docs/reference/STOM_Good_Results/`; `ai_strategy_loop/dashboard/reference_strategies.json`; `ai_strategy_loop/dashboard/app.py:739-961`; `tests/unit/test_dashboard_hall_of_fame.py:114-219,343-430`; `tests/unit/test_trade_ledger.py:266-340`; `tests/unit/test_promotion_preconditions.py:182-255`; `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:223-249`.
  Acceptance criteria: benchmark inventory is frozen before AI OOS disclosure hash; identical cohort checker either passes every field or returns explicit non-comparability; no cross-cohort ranking; promotion preconditions fail closed unless CL-R07-10 receipts all pass; export/live paths remain untouched; final handoff resolves all referenced files and states whether the core autonomous-improvement and performance goals were separately achieved.
  QA scenarios: Happy A: executable identical human cohort produces reproducible comparison and analysis-only review. Happy B: screenshots only produce honest non-comparability and no human-level claim. Failure: period/cost/timeframe mismatch, missing body hash, changed formula, or attempted export causes hard rejection. Evidence task-18 directory.
  Commit: YES after approved review | `docs(research): AI 조건식 루프 최종 검증과 핸드오프 기록`; never commit runtime data or claim live readiness.

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance and evidence-chain audit
  Independently parse the canonical spec, phase protocol, every predecessor/approval/run receipt, Candidate Passport chain, feedback consumptions, preregistration/access times, and benchmark inventory. Recompute all artifact hashes from source; traverse the state machine; reject worker-authored “pass” text without the underlying assertion. Require an unbroken `CL-D0 -> ... -> last reached CL-R phase` chain and distinguish `GO`, `NO_GO`, `WAITING_FOR_PROSPECTIVE_DATA`, and `NOT_COMPARABLE` without upgrading any status. Evidence `.omo/evidence/final-f1-ai-condition-loop-canonical-rebuild-20260711/`.

- [ ] F2. Code quality, diagnostics, and contract regression review
  Run the complete focused ladders for condition generation/feedback, state/passport/ledger, research/profile/holdout/promotion, and dashboard; then `pytest tests/unit/ -q`, `python scripts/pre_commit_check.py`, `python scripts/verify_nonrelease_sync.py`, language-server diagnostics for every changed Python/JSX file, and the mandatory post-implementation `review-work` quality/security review. Any timeout, skipped targeted test, new failure, or inconclusive review is a rejection; pre-existing failures must be reproduced on baseline and named. Evidence final-f2 directory.

- [ ] F3. Real manual QA and debugging runtime audit
  Drive the artifact through its matching surfaces: CLI `--help`, happy fake mini-loop, bad profile/forged approval, approved isolated official run receipts, OOS custodian denial/open behavior when data exists, and the live local dashboard via in-app browser at 1440/1180/980. Record three runtime debugging hypotheses with evidence: feedback lost across resume, evidence partial-write/duplicate consumption, and stale/cohort-mismatched dashboard state. Verify each by executing the relevant failure and happy path; no source-reading-only pass. Evidence final-f3 directory.

- [ ] F4. Scope, authorization, worktree, and protected-path fidelity
  Compare final worktree against the initial porcelain snapshot and per-todo allowlists; inspect every commit and staged diff; reject unrelated dashboard/.omo/artifact/user changes, DB/CSV/log bulk, engine/fitness/live/V3K/Alpha-Lab scope, default-ON flags, UPDATE/DELETE evidence SQL, unauthorized phase execution, or post-OOS generation. Run `git diff --check` and protected-path status. Evidence final-f4 directory.

## Commit strategy

- Never use `git add -A`, broad directory staging, stash/reset/checkout cleanup, amend/rebase, or push unless the user separately requests that exact operation.
- At each todo, hash `git status --porcelain=v1` before work, maintain an explicit path allowlist, and stop if unexpected paths change. Existing unrelated tracked/untracked files remain untouched.
- Stage implementation with its direct tests. Split docs/handoff, evidence contracts/store, CLI provenance/fingerprints, controller feedback/passport wiring, dashboard comparability, and run-result docs into separate revertible commits.
- Commit titles and markdown bodies are Korean and follow recent style. Planned subjects are listed in each todo; later result commits contain only compact source-controlled receipts/docs, never DB/CSV/logs/screenshots unless the repository convention explicitly tracks them.
- Before every commit: `git diff --cached --check`, `git diff --cached --stat`, full staged diff inspection, exact staged-name allowlist assertion, focused tests, and protected-path status.
- After every commit: `git log -1 --oneline`, `git show --stat`, target-path clean check, remaining dirty count/hash report, and no push.

## Success criteria

### Development-system completion

- CL-D0..D4 artifacts exist, hashes verify, one sole canonical design spec is identifiable, latest handoff is cold-start complete, and the docs-only commit is recorded.
- `run_loop` is the sole final lineage owner; fixed batch/research paths cannot claim autonomous learning or advance canonical phase.
- Every evaluated generation has an immutable Candidate Passport, Evaluation Manifest, outcome/stop Run Receipt, code/profile/data hashes, and reconstructible lineage in DB and snapshot.
- Every next-generation learning claim has an immutable autopsy/feedback/prompt/target-passport/changed-clause chain that survives stop/resume; no evidence-table UPDATE/DELETE exists.
- External/LLM candidates are positively constrained to approved B variables, carry complete threshold provenance, and cannot spend quota on semantic/rowset duplicates.
- Entry/sell/interaction attribution requires a complete fixed-profile 2x2 matrix and refuses partial causal claims.
- Historical and live dashboard views expose evidence source/freshness/version; Hall of Fame never ranks incompatible cohorts together.
- All focused/full tests, diagnostics, verifiers, review-work, manual QA, debugging hypotheses, diff hygiene, and protected-path checks pass with no new unexplained failure.

### Process-proof completion

- CL-R07 runs exactly three rounds within three provider calls, nine official evaluations, and 120 minutes; gen2/gen3 each consume prior feedback and make a non-noop clause change; controls and 2x2 attribution are valid; isolated/protected paths remain clean.

### Performance-proof completion

- CL-R08 has one unchanged candidate passing frozen train/validation gates and chronological-half stability; otherwise the honest terminal state is `NO_GO_STOP` and no OOS/human-performance claim is permitted.
- CL-R09 has one prospective 20-day, one-time-open, four-fold sealed OOS result passing all frozen gates with no contamination or post-open generation; if data is unavailable, status remains `WAITING_FOR_PROSPECTIVE_DATA` and the plan is not declared performance-complete.
- CL-R10 either completes an identical executable human cohort comparison or returns `not_comparable_missing_executable_reference`; only the former may support a human-level comparison, and neither authorizes export/live.
- Do not mark the original autonomous-improvement objective complete merely because infrastructure or documentation is complete. Report separately: `system_built`, `learning_proved`, `performance_proved`, `human_comparison_proved`, and `live_authorized` (always false in this scope).
