# Wide v1 v3 Tie-Break and Ranking Reinforcement Design

## 1. Purpose

PR #23 concluded with:

```text
decision=HOLD_V3_TIE_REVIEW
tie_status=rank_metric_tie
tie_candidate_count=10
row_set_identity_status=not_evaluated
selected_family=v3_tighten_secondary only
```

The next step is not v4 candidate generation. The next step is to make the v3 tie state measurable and reproducible so the CLI does not treat the first generated tied candidate as a real quant winner.

This design defines the next implementation scope:

```text
1. compare tied v3 candidate CSV row sets
2. group row-identical candidates into equivalence classes
3. choose a deterministic representative for each row-set class
4. expose why retention-aware selection chose only v3_tighten_secondary
5. route the next branch after tie-break analysis
```

It does not run new backtests, promote a strategy, run WFO, or mutate `strategy.db`.

## 2. Current Evidence

The merged v3 decision report is:

```text
docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
```

Additional local read-only diagnostics against the PR #22 runtime artifacts show:

```text
runtime_path=C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json
candidate_count=10
top_10_adjusted_score=13497.662902097409 for all 10
top_10_trade_count_retention=0.8817451205510907 for all 10
top_10_row_sets_same_as_cand001=True for all 10
unique_row_sets=1
rows_per_candidate=36096
```

Retention-selection context:

```text
retention_pool_count=33
retention_passed_count=33
retention_selected_count=10
fallback_count=0
selected_family=v3_tighten_secondary only
```

The selected tighten candidates had estimated retention close to 1.0. Repair and replace candidates passed the retention filter but were not selected because the retention-aware selector sorts primarily by estimated retention, then candidate score. After actual backtest, the selected tighten candidates all produced the same row set.

## 3. Quant Interpretation

The top-10 v3 tie is stronger than a numeric score tie:

```text
score tie      = yes
rank metric tie = yes
row-set tie    = yes, based on read-only diagnostics
```

That means:

```text
- cand001 is not a unique winner.
- the extra third condition in each selected tighten expression did not change the executed trade set.
- v3_tighten_secondary selection did not produce measurable execution diversity.
- moving to v4 by extending the same pattern risks generating cosmetic conditions that do not change trades.
```

From a quant-trading perspective, a tie-break should not reward arbitrary generation order. If two expressions produce the same trade set, the system should prefer the simpler or lower-risk expression and record the rest as equivalent alternatives, not as separate winners.

## 4. Approaches Considered

### Approach A: Add More Numeric Rank Keys

Add more scalar metrics to `_rank_key`, such as total profit, win rate, avg MAE, or generated candidate score.

Rejected for this stage.

Reason:

```text
The current top 10 have identical trade row sets. Any metric derived from executed trades will also be identical. Using generation score or expression score would break ties without proving trading superiority.
```

### Approach B: Force Family Diversity Before Backtest

Change retention-aware selection so candidate_count=10 includes repair and replace families.

Useful later, but not first.

Reason:

```text
Family diversity may improve exploration, but it changes selection behavior before we have a reproducible row-set equivalence report. It also risks mixing two concerns: diagnosing the v3 tie and designing v4 exploration.
```

### Approach C: Row-Set Equivalence First, Then Representative Selection

Compute row-set identity for tied candidates, group identical row sets, and choose one deterministic representative per group. Add selection diagnostics that explain whether family diversity was lost before or after row-set execution.

Recommended.

Reason:

```text
It directly answers the open PR #23 risk: whether top tied candidates are execution-distinct. It also gives the next v4 design a concrete input: either diversify row-set classes, simplify equivalent expressions, or change candidate generation.
```

## 5. Recommended Design

Add a tie-break analysis layer that runs after v3 candidate execution and before any v4 decision.

The layer should produce:

```text
row_set_identity_status:
  not_evaluated
  all_identical
  partially_distinct
  all_distinct
  error

row_set_group_count:
  number of unique row-set equivalence classes

row_set_groups:
  list of groups with representative candidate, member candidates, row count, and common key diagnostics

representative_selection:
  deterministic rule used inside each group

family_selection_diagnostics:
  pool/pass/selected/executed counts and selected-vs-unselected family explanation

next_decision:
  HOLD_ROW_SET_EQUIVALENCE
  HOLD_SELECTION_DIVERSITY_REVIEW
  PROCEED_TO_V4_PLAN
```

The v3 decision report should be updated to distinguish:

```text
rank_metric_tie_without_row_check
rank_metric_tie_with_identical_rows
rank_metric_tie_with_distinct_rows
```

## 6. Representative Rule

For a row-identical group, choose the representative by deterministic non-performance criteria:

```text
1. fewer executable conditions
2. candidate family priority:
   v3_control_keep_best
   v3_repair_trade_amount
   v3_replace_secondary
   v3_tighten_secondary
3. simpler expression text length
4. lower original rank
5. lower original index
```

Rationale:

```text
If row sets are identical, performance cannot distinguish candidates. A simpler expression is easier to audit and less likely to overfit. The family priority intentionally avoids rewarding tighten-only additions that do not change trades.
```

This representative is a reporting and routing choice only. It is not a promote decision.

## 7. CLI and Data Flow

Use the existing artifact inputs:

```text
runtime JSON -> candidate_csv paths -> trade-key row-set ids -> equivalence classes -> markdown report
```

Implementation should reuse:

```text
cli.research_v3_decision.read_runtime_json
cli.research_compare._with_trade_key
cli.research_compare._trade_id_pairs
cli.research_v3_decision.family_distribution
```

The row-set comparison should be a pure helper so it can be tested without launching STOM backtests.

Candidate CSV paths in runtime are relative to the runtime worktree. The script should accept:

```text
--runtime-path
--runtime-root
--output
--top-n
```

Default runtime inputs should point to the known PR #22 artifacts, but overrides must be supported.

## 8. Report Output

Create a new pilot log:

```text
docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md
```

Required sections:

```text
1. Decision
2. Inputs
3. Tie Candidate Summary
4. Row-Set Equivalence
5. Representative Selection
6. Family Selection Diagnostics
7. Quant Interpretation
8. Next Step
```

Expected decision for the known PR #22 artifacts:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
reason=top 10 v3 candidates are row-identical
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```

If future artifacts show more than one row-set group, the decision can instead become:

```text
decision=HOLD_SELECTION_DIVERSITY_REVIEW
next_command=$brainstorming Wide v1 v3 selection diversity 보강 설계
```

If future artifacts show distinct row sets and no family selection concern, the decision can become:

```text
decision=PROCEED_TO_V4_PLAN
next_command=$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성
```

## 9. Testing Requirements

Focused tests should cover:

```text
1. identical candidate CSV row sets collapse into one group
2. partially distinct candidate CSV row sets produce multiple groups
3. missing candidate CSV returns an error status without crashing the CLI
4. representative selection prefers simpler expressions over generation order
5. representative selection uses family priority only after condition count ties
6. known v3 family distribution reports tighten-only selected/executed state
7. markdown report contains decision, group count, representative, and next command
8. script accepts explicit runtime-root and output paths
```

Regression tests should keep existing v3 decision behavior intact.

## 10. Out of Scope

This design does not include:

```text
- new v4 candidate generation
- changing retention-aware selection
- changing promotion scoring weights
- rerunning v3 backtests
- promote or WFO
- strategy.db mutation
```

Those are downstream tasks after row-set equivalence and representative selection are documented.

## 11. Acceptance Criteria

The implementation is acceptable when:

```text
- the known v3 runtime produces row_set_identity_status=all_identical
- row_set_group_count=1 for the known top 10
- the report explains that cand001 is not a unique quant winner
- the report records a deterministic representative rule
- the generated report does not route back to the same implementation plan
- the next command routes to v4 diversity brainstorming when the known v3 artifacts are row-identical
- unit tests, ruff, sync guard, and diff check pass
```

## 12. Recommended Next Command

After this spec is reviewed, the next command should be:

```text
$writing-plans Wide v1 v3 row-set equivalence 및 ranking 보강 구현 계획 작성
```
