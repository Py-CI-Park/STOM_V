# Research Plan — process_research_v2_validation_20260701

## Scope

- canonical process: `process-research`
- preset: `research`
- boundary: research-only, no export, no live, no final promotion
- slippage: 3-tick advisory only
- engine policy: 64 first; 32 fallback receipt on warm prepare failure, engine_data_response_timeout, no-metrics, or replay failure
- prompt policy: `full_condition_code_required_not_id_only`

## Seeds

| Role | condition_id | human_name | buy | sell |
|---|---|---|---|---|
| start_seed | `rr8_12_turnover_min_902=1.5` | `OOSStable_Open902_TurnoverMin_v1` | `GATE_rr8_12_turnover_min_902_1_5_B` | `GATE_rr8_12_turnover_min_902_1_5_S` |
| profit_comparator | `rr8_21_trail_keep=0.7` | `ProfitLead_TrailKeep070_2025Comparator` | `GATE_rr8_21_trail_keep_0_7_B` | `GATE_rr8_21_trail_keep_0_7_S` |
| segment_comparator | `rr8_0_cap_max=2500` | `CapLimited_2500_Comparator` | `GATE_rr8_0_cap_max_2500_B` | `GATE_rr8_0_cap_max_2500_S` |
| failure_coverage_context | `human_seed_gptauth_B_gen8` | `GPTGen8_HighCoverage_FailedProfitContext` | `AILOOP_follow12_gptauth_B_seeded64_20260628_g8_buy` | `AILOOP_follow12_gptauth_B_seeded64_20260628_g8_sell` |

## Required artifacts

- `research_context_pack.json`
- `candidate_cards.jsonl`
- `analysis_cards.jsonl`
- `prompt_mutation_receipts.jsonl`
- `full_period_backtest_receipts.json`
- `dashboard_verification.json`
- `safety_receipt.json`

## Candidate policy

Generate at least 2 and target 4 candidates from one baseline Analysis Card v2: repair >= 1 and discovery >= 1. Each candidate must have hypothesis, mutation axis, expected effect, risk note, parent buy/sell full code, and official backtest result or failure receipt.
