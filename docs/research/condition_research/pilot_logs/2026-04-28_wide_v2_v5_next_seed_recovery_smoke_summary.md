# Wide v2 optimizer summary

## Run configuration

- run_id=WideV2V5NextSeedRecoverySmoke_20260428
- status=ok
- iteration_v2_mode=best_feature_mix_v5
- iteration_v2_primary_feature=B_시가총액
- iteration_v2_trade_amount_feature=B_등락율

## Initial baseline

- base_buy_strategy=WideV1Final_B_20260425
- source_baseline=WideV1Final_B_20260425
- seed_candidate=WideV1Final_B_20260425
- seed_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83

## Round count

- completed_round_count=2

## Round summary

round-by-round summary

| round | status | source_candidate | round_best | expression |
| --- | --- | --- | --- | --- |
| 1 | ok | WideV1Final_B_20260425 | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003 | 66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173 |
| 2 | ok | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand001 | WideV2V5NextSeedRecoverySmoke_20260428__round002__cand003 | 66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173 |

## Round best candidates

| round | strategy_name | expression |
| --- | --- | --- |
| 1 | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003 | 66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173 |
| 2 | WideV2V5NextSeedRecoverySmoke_20260428__round002__cand003 | 66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173 |

## Global leaderboard top candidates

| round | candidate | strategy | adjusted_score | promotion_passed | global_best |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand001 | 33.94050979980738 | True | False |
| 1 | 2 | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand002 | 13.1027248193789 | True | False |
| 1 | 3 | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003 | 66.2483852958148 | True | True |
| 1 | 4 | WideV2V5NextSeedRecoverySmoke_20260428__round001__cand004 | 32.724570627215705 | True | False |
| 2 | 1 | WideV2V5NextSeedRecoverySmoke_20260428__round002__cand001 | 13.1027248193789 | True | False |
| 2 | 2 | WideV2V5NextSeedRecoverySmoke_20260428__round002__cand002 | 1.2195918199876796 | True | False |
| 2 | 3 | WideV2V5NextSeedRecoverySmoke_20260428__round002__cand003 | 66.2483852958148 | True | False |
| 2 | 4 | WideV2V5NextSeedRecoverySmoke_20260428__round002__cand004 | 32.724570627215705 | True | False |

## V5 recovery

- initial_v4_candidate_count=
- recovery_attempted=
- recovery_reason=
- recovery_family_counts={}
- final_candidate_pool_count=
- eligible_count=
- execution_count=
- planned_execution_count=

## Next seed selection

- next_seed_selection_status=compatible_fallback
- next_seed_strategy_name=WideV2V5NextSeedRecoverySmoke_20260428__round001__cand001
- next_seed_expression=66.999 <= 시가총액 < 2_580 and 4.39 <= 등락율 < 5.11
- rejected_round_best_seed_strategy_name=WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003
- rejected_round_best_seed_expression=66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173
- rejected_round_best_seed_reason=invalid_seed_expression

## Stop reason

- stop_reason=max_rounds_reached
- failed_round=
- failure_phase=
- failure_message=
- requested_candidate_count=
- selected_candidate_count=

## Final best candidate

final_best_candidate

- strategy_name=WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003
- expression=66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173
- adjusted_score=66.2483852958148

## WFO handoff

WFO was not run inside the optimizer loop.
The final candidate is a WFO candidate, not a live-trading approval.

WFO handoff candidate

- strategy_name=WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003
- expression=66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173

next command for WFO validation plan

- next_command=$writing-plans WideV2V5NextSeedRecoverySmoke_20260428 optimizer winner WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003 WFO handoff plan 작성
