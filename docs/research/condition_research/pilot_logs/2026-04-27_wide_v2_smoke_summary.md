# Wide v2 optimizer summary

## Run configuration

- run_id=WideV2Smoke_20260427
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

- completed_round_count=0

## Round summary

round-by-round summary

| round | status | source_candidate | round_best | expression |
| --- | --- | --- | --- | --- |
| 1 | error | WideV1Final_B_20260425 |  |  |

## Round best candidates

| round | strategy_name | expression |
| --- | --- | --- |
| 1 |  |  |

## Global leaderboard top candidates

| round | candidate | strategy | adjusted_score | promotion_passed | global_best |
| --- | --- | --- | --- | --- | --- |

## Stop reason

- stop_reason=insufficient_candidates
- failed_round=1
- failure_phase=insufficient_retention_candidates
- failure_message=candidate_count=2 requested but only 0 candidates selected after retention filtering
- requested_candidate_count=
- selected_candidate_count=

## Final best candidate

final_best_candidate

- strategy_name=
- expression=
- adjusted_score=

## WFO handoff

WFO was not run inside the optimizer loop.
The final candidate is a WFO candidate, not a live-trading approval.

WFO handoff candidate

- strategy_name=
- expression=

next command for WFO validation plan

- next_command=
