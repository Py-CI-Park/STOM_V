# P1 Yearly Sparse Robust Policy

Timestamp: 2026-06-04
Selector version: `yearly_sparse_robust_v1`

## Purpose
`yearly_sparse_robust_v1` is a training-only selector for fresh 2023-2025 TICK research candidates. It does not replace or mutate `sparse_positive_v1`; a candidate must first satisfy `sparse_positive_v1`, then pass the stricter yearly robustness checks below before any fixed 2022/2026 OOS run is allowed.

Prior 2022/2026 OOS evidence is used only as a rejected-candidate lesson: aggregate sparse-positive training success did not transfer to 2022 and did not produce enough OOS trades. It is forbidden to tune, rank, or reselect candidates using 2022/2026 OOS metrics.

## Aggregate Thresholds
- Candidate must pass `sparse_positive_v1`.
- Total training `trade_count` must be between `150` and `250`, inclusive.
- Total training `daily_avg_trades` must be at least `0.15`.
- Total training MDD must be `<= 10.0`.
- Total training profit must be `> 0`.
- Total training payoff ratio must be `>= 1.05`.

## Yearly Thresholds
Yearly metrics are computed from the candidate generation CSV by sell-date year. The required training years are exactly `2023`, `2024`, and `2025`.

- All required years `2023`, `2024`, and `2025` must be present.
- Each required year must have at least `30 trades`.
- Each required year must have positive profit.
- The full-period training equity uptrend R2 from the same CSV must be `>= 0.50`.
- Missing CSV, malformed CSV, missing date/profit columns, missing required years, or insufficient yearly rows reject the candidate.

## Ranking
Eligible candidates are ranked only after all aggregate and yearly checks pass.

Bucket priority:
1. `hard_gate_yearly_robust`: aggregate hard gate passed plus yearly checks pass.
2. `sparse_yearly_robust`: aggregate sparse-positive bucket plus yearly checks pass.

Rank key:
1. Bucket priority.
2. Descending minimum yearly profit.
3. Descending full-period profit divided by MDD.
4. Ascending MDD.
5. Descending capped total trades.
6. Descending payoff ratio.
7. Ascending generation number.

## Forbidden Selector Inputs
The selector and selection artifact must not contain or consume:

- 2022 OOS metrics.
- 2026 OOS metrics.
- Slippage-stress results.
- PBO or DSR results produced after candidate freeze.
- Final decision-card verdicts.
- Any post-OOS analysis.

If any forbidden field is present in candidate input or selection metadata, the candidate is rejected and `forbidden_oos_fields_present=true` must be recorded.

## Artifact Schema
The selected-candidate artifact must include:

- `selector_version=yearly_sparse_robust_v1`
- `selected`
- `oos_excluded=true`
- `diagnostic_only=false` for P5 freeze
- `forbidden_oos_fields_present=false` for a valid selection
- `policy_hash`
- `config_hash`
- `selected_generation`
- `aggregate_checks`
- `yearly_breakdown`
- `uptrend_r2`
- `eligible_candidates`
- `rejected_candidates`

If no candidate qualifies, P6 fixed 2022/2026 OOS is skipped and `p5-selector-blocked.md` plus `p6-oos-blocked.md` must be written.

## No-Retuning Rule
These thresholds are frozen before implementation, fresh training, or fresh 2022/2026 OOS. Once any new OOS starts, this policy must not be changed for the current plan. Any future threshold change requires a new plan and must not use current-plan OOS results as a selector input.
