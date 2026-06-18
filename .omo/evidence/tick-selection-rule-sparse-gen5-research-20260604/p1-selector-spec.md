# P1 Selector Spec: sparse_positive_v1

## Status
- selector_version: `sparse_positive_v1`
- predeclared_at: `2026-06-04T12:33:00+09:00`
- evidence_root: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/`
- scope: TICK 2023~2025 training generations only
- purpose: select a fixed research candidate before any 2022/2026 OOS run

## OOS-Blind Inputs
Allowed fields:
- `gen_no`
- `status`
- `score` or `graded_score`
- `gate_passed`
- `gate_reason`
- `profit`
- `total_profit_pct`
- `mdd`
- `trade_count`
- `daily_avg_trades`
- `payoff_ratio`
- `max_hold_count`
- `buy_name`
- `sell_name`

Forbidden fields:
- 2022 OOS metrics
- 2026 OOS metrics
- slippage-stress outputs
- PBO/DSR outputs
- final decision verdicts
- any post-OOS analysis field

## Eligibility Rules
A generation is eligible only when all checks below pass:
- `status == "ok"`
- `buy_name` and `sell_name` are non-empty
- `profit > 0`
- `mdd <= 10.0`
- `20 <= trade_count <= 250`
- `daily_avg_trades >= 0.05`
- `payoff_ratio >= 1.05`
- profit, MDD, trade count, and strategy identity are present

If payoff is unavailable, the candidate is rejected unless the selector implementation records explicit missingness and a reviewer accepts that the source data cannot provide payoff. The default behavior is reject on missing payoff.

## Buckets
### Bucket A: hard_gate_positive
Candidate qualifies when:
- `gate_passed == true`
- all eligibility rules pass

### Bucket B: sparse_positive
Candidate qualifies when:
- `gate_passed == false`
- all eligibility rules pass
- `gate_reason` is exactly a daily-frequency failure, for example `daily_avg_trades 0.1 < min_daily_trades 0.3`

Mixed failures do not qualify. Any gate reason involving profit, MDD, TPI, timeout, missing CSV, validation failure, or unknown failure is rejected.

Bucket A outranks Bucket B.

## Ranking
Within each bucket, sort by:
1. Higher `profit / max(mdd, 1.0)`
2. Lower `mdd`
3. Higher `min(trade_count, 150)`
4. Higher `payoff_ratio`
5. Lower `gen_no`

If no candidate qualifies, write a blocked selector artifact and skip OOS.

## Required Selection Artifact
Each selector output must include:
- `selector_version`
- `run_id`
- `config_path`
- `config_hash`
- `selected`
- `blocked`
- `blocker`
- `selected_bucket`
- `gen_no`
- `buy_name`
- `sell_name`
- selected metrics
- `selection_timestamp`
- `oos_excluded: true`
- `diagnostic_only` for prior-run replay
- `eligible_candidates`
- `rejected_candidates` with machine-checkable reasons
- `forbidden_oos_fields_present: false`

## Promotion Blockers
`sparse_positive_v1` only selects a research candidate. It does not promote a strategy.

Promotion remains impossible unless all of the following pass:
- AI profit is positive in both 2022 and 2026 OOS.
- Combined AI profit is greater than or equal to combined seed profit.
- AI max MDD is less than or equal to seed max MDD.
- Each AI OOS year has at least 20 trades.
- Combined AI OOS has at least 50 trades.
- Slippage-stressed OOS remains positive in both years.
- PBO/DSR status is either passed by available tooling or documented as not applicable by an explicit reviewer decision.

If any condition fails or is unavailable, final verdict is `REJECT_CANDIDATE` or `NEEDS_MORE_EVIDENCE`.

## Notes
- Prior P3 gen5 may be replayed only as `diagnostic_only=true`.
- Prior replay cannot be cited as efficacy evidence.
- Existing `best` and `winner` meanings are preserved unless a later source task explicitly adds a separate `selected_candidate` concept.
