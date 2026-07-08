# Next Command: Candidate Generation Static / Dry-Run Only

```text
$ulw-loop docs/research/condition_research/plans/lattice_condition_generation_v2_candidate_dryrun_20260708.md

Scope is candidate-generation-static-dryrun-only-no-execution.
Goal: use the v2 failure map, seed lineage audit, axis spec, evaluation protocol, and candidate quota ledger to draft at most 32 v2 candidate metadata records and perform static gate + DB registration dry-run only.

Required read-first docs:
- docs/research/condition_research/plans/lattice_condition_generation_v2_failure_map_20260708.json
- docs/research/condition_research/plans/lattice_condition_generation_v2_seed_lineage_audit_20260708.json
- docs/research/condition_research/plans/lattice_condition_generation_v2_axis_spec_20260708.json
- docs/research/condition_research/plans/lattice_condition_generation_v2_evaluation_protocol_20260708.json
- docs/research/condition_research/plans/lattice_condition_generation_v2_candidate_quota_ledger_20260708.json
- utility/ai_agent/strategy.txt
- utility/ai_agent/rules.txt

Proceed:
1. Generate candidate metadata only, max 32.
2. Use research lane only, hypothesis_seed label, sanitized names.
3. Include coverage_composite 8, risk_balanced_composite 8, survivor_seed_derivative 8, negative_control 4, holdout_control 4 unless evidence justifies a smaller batch.
4. Run STOM syntax/static checks only if condition text is drafted.
5. Run DB registration dry-run only; do not apply.
6. Write candidate ledger, static receipt, dry-run receipt, and handoff.

Forbidden:
- DB INSERT apply
- DB UPDATE/DELETE
- backtest
- limited replay
- OOS
- portfolio
- Plan D R3
- export/live/final promotion
- full tick/min 288
- git add -A
- dashboard 7 files, .gjc, unrelated .omo staging
```
