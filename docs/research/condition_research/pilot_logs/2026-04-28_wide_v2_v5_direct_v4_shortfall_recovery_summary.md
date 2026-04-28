# Wide v2 optimizer summary

## Run configuration

- run_id=WideV2V5DirectV4ShortfallRecovery_20260428
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

- completed_round_count=1

## Round summary

round-by-round summary

| round | status | source_candidate | round_best | expression |
| --- | --- | --- | --- | --- |
| 1 | ok | WideV1Final_B_20260425 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007 | 66.999 <= 시가총액 < 2_580 and 등락율 > 3.535 |

## Round best candidates

| round | strategy_name | expression |
| --- | --- | --- |
| 1 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007 | 66.999 <= 시가총액 < 2_580 and 등락율 > 3.535 |

## Global leaderboard top candidates

| round | candidate | strategy | adjusted_score | promotion_passed | global_best |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand001 | 33.94050979980738 | True | False |
| 1 | 2 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand002 | 13.1027248193789 | True | False |
| 1 | 3 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand003 | 70.18193557985185 | True | False |
| 1 | 4 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand004 | 66.2483852958148 | True | False |
| 1 | 5 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand005 | -1.9428902930940238e-17 | False | False |
| 1 | 6 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand006 | 0.0 | False | False |
| 1 | 7 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007 | 112.06250936127728 | True | True |
| 1 | 8 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand008 | 1.2195918199876796 | True | False |
| 1 | 9 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand009 | 3.769382689127234 | True | False |
| 1 | 10 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand010 | 48.91465643114266 | True | False |
| 1 | 11 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand011 | 4.750779523364467 | True | False |
| 1 | 12 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand012 | 12.897250593131718 | True | False |
| 1 | 13 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand013 | -0.12714404550625558 | False | False |
| 1 | 14 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand014 | 2.2820405682896654 | True | False |
| 1 | 15 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand015 | 7.9232034949259 | True | False |
| 1 | 16 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand016 | 6.865904169780946 | True | False |
| 1 | 17 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand017 | 32.724570627215705 | True | False |
| 1 | 18 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand018 | 16.61236796988501 | True | False |
| 1 | 19 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand019 | -1.9428902930940238e-17 | False | False |
| 1 | 20 | WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand020 | -1.9428902930940238e-17 | False | False |

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

- next_seed_selection_status=
- next_seed_strategy_name=
- next_seed_expression=
- rejected_round_best_seed_strategy_name=
- rejected_round_best_seed_expression=
- rejected_round_best_seed_reason=

## Stop reason

- stop_reason=max_rounds_reached
- failed_round=
- failure_phase=
- failure_message=
- requested_candidate_count=
- selected_candidate_count=

## Final best candidate

final_best_candidate

- strategy_name=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
- expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535
- adjusted_score=112.06250936127728

## WFO handoff

WFO was not run inside the optimizer loop.
The final candidate is a WFO candidate, not a live-trading approval.

WFO handoff candidate

- strategy_name=WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007
- expression=66.999 <= 시가총액 < 2_580 and 등락율 > 3.535

next command for WFO validation plan

- next_command=$writing-plans WideV2V5DirectV4ShortfallRecovery_20260428 optimizer winner WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007 WFO handoff plan 작성
