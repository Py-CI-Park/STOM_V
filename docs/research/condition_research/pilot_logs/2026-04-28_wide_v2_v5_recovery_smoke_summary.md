# Wide v2 optimizer summary

## Run configuration

- run_id=WideV2V5RecoverySmoke_20260428
- status=error
- iteration_v2_mode=best_feature_mix_v5
- iteration_v2_primary_feature=B_시가총액
- iteration_v2_trade_amount_feature=B_등락율

## Initial baseline

- base_buy_strategy=WideV1Final_B_20260425
- source_baseline=WideV1Final_B_20260425
- seed_candidate=WideV1Final_B_20260425
- seed_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83

## Round count

- completed_round_count=1

## Round summary

round-by-round summary

| round | status | source_candidate | round_best | expression |
| --- | --- | --- | --- | --- |
| 1 | ok | WideV1Final_B_20260425 | WideV2V5RecoverySmoke_20260428__round001__cand003 | 66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173 |

## Round best candidates

| round | strategy_name | expression |
| --- | --- | --- |
| 1 | WideV2V5RecoverySmoke_20260428__round001__cand003 | 66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173 |

## Global leaderboard top candidates

| round | candidate | strategy | adjusted_score | promotion_passed | global_best |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | WideV2V5RecoverySmoke_20260428__round001__cand001 | 33.94050979980738 | True | False |
| 1 | 2 | WideV2V5RecoverySmoke_20260428__round001__cand002 | 13.1027248193789 | True | False |
| 1 | 3 | WideV2V5RecoverySmoke_20260428__round001__cand003 | 66.2483852958148 | True | True |
| 1 | 4 | WideV2V5RecoverySmoke_20260428__round001__cand004 | 32.724570627215705 | True | False |

## V5 recovery

- initial_v4_candidate_count=
- recovery_attempted=
- recovery_reason=
- recovery_family_counts={}
- final_candidate_pool_count=
- eligible_count=
- execution_count=
- planned_execution_count=

## Stop reason

- stop_reason=invalid_seed_expression
- failed_round=2
- failure_phase=invalid_seed_expression
- failure_message=next seed expression is invalid
- requested_candidate_count=
- selected_candidate_count=

## Final best candidate

final_best_candidate

- strategy_name=WideV2V5RecoverySmoke_20260428__round001__cand003
- expression=66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173
- adjusted_score=66.2483852958148

## WFO handoff

WFO was not run inside the optimizer loop.
The final candidate is a WFO candidate, not a live-trading approval.

WFO handoff candidate

- strategy_name=WideV2V5RecoverySmoke_20260428__round001__cand003
- expression=66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173

next command for WFO validation plan

- next_command=$writing-plans WideV2V5RecoverySmoke_20260428 optimizer winner WideV2V5RecoverySmoke_20260428__round001__cand003 WFO handoff plan 작성
