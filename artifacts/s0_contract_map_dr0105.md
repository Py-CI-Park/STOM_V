# S0 Contract Map — DR-01 through DR-05 (working artifact, uncommitted)

Authority ceiling: DR-00 commit `70da4702b554996b896c8993c30c80bdd1735c52` (HEAD verified equal).
Frozen sources (verified SHA-256):
- stage-19 revision `055f59ba9353da2d9b1f41568bc63d9825cd0758a2b389db86370bd6efad31e2` — fixtures/oracle: Full literal T01–T40 canonical array; Canonical AST vectors; exact proposal/target/replacement response bytes; exact result call payload bytes; Statistics and hard null-FDR acceptance; DDL/transaction/count.
- stage-21 revision `133b8123b69212c1945721d3762b7c3c40158ff6c7cba612b3cb0e65b7e0168c` — Appendix A–D, Complete v2 schema contract, crash table.

DR-C0 semantics are ABSORBED here by reference; no separate DR-C0 commit is produced. S0 makes no product source changes.

## Gate results (S0 fail-close checks)
- AUTHORITY_CEILING: PASS (HEAD == ceiling).
- FROZEN_SOURCE_INTEGRITY: PASS (both revision SHAs match).
- ANCHOR_SYMBOLS_EXIST: PASS — `controller/loop.py::{run_loop@1158, run_backtest_for@269, BacktestOutcome@102}`; `controller/evidence_store.py::EvidenceStore@53`; `controller/evidence_contract.py::{canonical_json@112, sha256_hex@120}`; `controller/candidate_pool.py::select_official_candidate@131`; `brain/pack_producer.py::produce_candidate_pack_result@547`; `cli/condition_fingerprint.py::{ast_fingerprint@186, rowset_fingerprint@241}`.
- AUTOMATIC_SCHEMA_V11: confirmed `controller/state.py::SCHEMA_VERSION = 11` with v11 evidence tables (candidate_passports/feedback_envelopes/feedback_consumptions/evaluation_manifests/run_receipts). Any DR-03 evidence graph change is additive and must keep the automatic/default schema at v11.

## Symbol ownership per DR slice (narrowed from DR-00 maxima)
Shared-file single owner: `ai_strategy_loop/controller/loop.py` and `ai_strategy_loop/controller/evidence_contract.py` are edited ONLY by the Integrator. Executors for DR-02..05 hand loop.py/evidence_contract.py edits to the Integrator.

- DR-01 (Executor A): `fitness/score.py`, `autopsy/trade_quant.py`, `autopsy/analysis_card.py`, `fitness/edge_ratio.py`. Tests: test_composite_score, test_trade_quant, test_analysis_card, test_edge_ratio.
- DR-02 (Executor B + Integrator for loop.py/evidence_contract.py): `scripts/research_presets.py`, `launch_config.py`, `config.py`, `controller/condition_discovery.py`, [Integrator: `controller/loop.py`, `controller/evidence_contract.py`]. Tests: test_research_presets, test_feedback_toggles_on, test_launch_config, test_condition_discovery_policy, test_canonical_passport_wiring, test_prompt_logging.
- DR-03 (Executor B + Integrator): `controller/state.py`, `controller/evidence_store.py`, `brain/generator.py`, `brain/prompt.py`, [Integrator: `controller/evidence_contract.py`, `controller/loop.py`]. Tests: test_prompt_logging, test_evidence_contract, test_evidence_store, test_feedback_evidence_wiring, test_canonical_passport_wiring, test_state_schema_migration, test_state_concurrency, test_evidence_lineage_check.
- DR-04 (Executor C + Integrator for loop.py): `brain/pack_producer.py`, `brain/prompt.py`, `brain/generator.py`, `brain/filter_gate.py`, `controller/candidate_pool.py`, `controller/context_pack_builder.py`, `cli/research_loop.py`, `cli/condition_fingerprint.py`, `cli/condition_generator.py`, [Integrator: `controller/loop.py`]. Tests: test_pack_producer, test_llm_pack_wiring, test_context_pack_builder, test_candidate_pool, test_condition_fingerprint, test_condition_generator, test_filter_gate, test_research_prompt_contracts, test_research_loop.
- DR-05 (Executor D + Integrator for loop.py): `autopsy/analysis_card.py`, `autopsy/trade_quant.py`, `autopsy/segment.py`, `autopsy/hypothesis.py`, `autopsy/ablation.py`, `fitness/edge_ratio.py`, `fitness/overfit_stats.py`, `fitness/promotion_diagnostics.py`, `brain/segment_feedback.py`, `brain/feature_importance_feedback.py`, [Integrator: `controller/loop.py`]. Tests: test_analysis_card, test_trade_quant, test_segment_autopsy, test_hypothesis_loop, test_condition_ablation, test_edge_ratio, test_overfit_stats, test_promotion_diagnostics, test_segment_feedback, test_condition_discovery_feedback.

Cross-slice shared files that need serialized ownership beyond the two Integrator files: `autopsy/analysis_card.py` (DR-01 + DR-05), `autopsy/trade_quant.py` (DR-01 + DR-05), `fitness/edge_ratio.py` (DR-01 + DR-05), `brain/prompt.py`/`brain/generator.py` (DR-03 + DR-04), `cli/condition_fingerprint.py` (DR-04). Serialize: DR-01 lands before DR-05 for the three autopsy/fitness files; DR-03 lands before DR-04 for prompt/generator.

## Fixture-only E2E boundary inputs
- Source dataset: literal T01–T40 canonical array from stage-19 (9,852 bytes, SHA `497385332bb2988e41ea861e3d52ea972c57244c1d4e6942f03f56519fd076bc`).
- Effective profile: min_full_0900_1500 canonical object from stage-21 Appendix C (session 090000–150000).
- v2 evidence graph exercised in-memory only via `sqlite3.connect(':memory:')`; no operating/protected DB, no WAL/SHM, no `ai_strategy_loop/state` writes.
- No provider/evaluator/official-backtest calls: external seams are faked; `run_backtest_for` subprocess is guarded.

## Compatibility / migration / rollback decision
- Automatic/default `LoopState` stays v11. Any new evidence structures are additive `CREATE TABLE IF NOT EXISTS` and exercised only in fixtures; no operating-DB migration is part of this program.
- Defaults for all new features remain OFF; named research/certification profiles opt in explicitly.
- Rollback: ordinary reviewed source revert of the affected slice only. No history rewrite, no protected-data mutation, no rollback protocol.
- Fail-close `COMPATIBILITY_BLOCKED` if additive compatibility cannot be proven against fixtures.

## Observability fields (existing product surfaces only)
profile/manifest identity; prompt/rendered-envelope linkage; candidate origin/fingerprints/quota/branch-gate decisions; card role/quality/directive eligibility; resume decision. No workflow custody data added.

## Failure-state matrix
`AUTHORITY_CEILING_MISMATCH` (stop before S0); `FROZEN_CONTRACT_CONFLICT` / `ALLOWLIST_EXPANSION_REQUIRED` (stop, escalate); `PROFILE_HASH_MISMATCH` / `MANIFEST_INCOMPLETE` (certification blocked); `EVIDENCE_LINEAGE_INVALID` / `INDETERMINATE_EXTERNAL_EFFECT` (no GO, no auto-retry); `COMPATIBILITY_BLOCKED` (preserve data, stop); `CANDIDATE_POLICY_REJECTED` (reject before budget); `STATISTICAL_DIRECTIVE_INELIGIBLE` (descriptive-only); `E2E_LINEAGE_OR_PARITY_FAILURE` (program incomplete, no DR-06 transition).

## Out of scope (require separate exact approval)
DR-06 audit; CL-R08~R10; provider/evaluator/official-backtest; protected DB/runtime access; defaults ON; v11 startup change; new files beyond the allowlist. Program terminal state: `HARD_STOP_AWAITING_SEPARATE_DR_06_PLAN_AND_EXACT_APPROVAL`.
