# P4 Smoke A/B Comparison

## Scope
This is a short 2025 Q1 TICK smoke A/B run. It is not OOS, not promotion evidence, and not a human-superiority claim.

## OFF
- run_id: `tick_spgen_p4_smoke_off_20260604`
- generations: 3
- errors/timeouts: 1
- best_graded: 0.34655019651835495
- gate_passed_count: 0
- prompt_count: 4
- sparse prompt true count: 0
- selector selected: False

## ON
- run_id: `tick_spgen_p4_smoke_on_20260604`
- generations: 3
- errors/timeouts: 1
- best_graded: 0.32683118576768705
- gate_passed_count: 0
- prompt_count: 4
- sparse prompt true count: 4
- selector selected: False

## Interpretation
- ON prompt records include `sparse_positive_prompt_enabled=true`.
- OFF prompt records do not include a true sparse-positive prompt feature.
- ON gen2 improved sparsity shape to 29 trades and MDD 16.96, but profit remained negative (-900,989), so `sparse_positive_v1` selected no candidate.
- P4 remains pipeline evidence only. P5 is still required for fresh 2023-2025 train evidence.
