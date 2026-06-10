# P6 Decision Card

## Executive Verdict
NEEDS_MORE_EVIDENCE

The predeclared `sparse_positive_v1` selector was implemented and replayed correctly, but the fresh 2023-2025 P4 run did not produce an eligible candidate. Therefore no fixed 2022/2026 OOS comparison was executed.

## Selector Version
- selector_version: `sparse_positive_v1`
- predeclared evidence: `p1-selector-spec.md`, `p1-selector-spec.json`
- OOS discipline: candidate selection uses training rows only and requires `oos_excluded=true`

## Candidate Identity
No candidate was selected.

P4 selector artifact:
- selected: false
- blocked: true
- blocker: `no candidate qualified for sparse_positive_v1`
- eligible_candidates: 0
- rejected_candidates: 6

## Training Evidence
Fresh P4 run:
- run_id: `tick_sel_sparse_p4_train_2023_2025_20260604`
- period: 2023-01-01 through 2025-12-31
- timeframe: tick
- window: 09:00-09:30
- max_generations: 6
- official loop exit: 0
- wall clock: about 2704.2 seconds
- winner: null

Observed rows:
- gen0: error, warm backtest timeout.
- gen1: profit -35,206,257, MDD 167.56, trades 4212, gate fail.
- gen2: profit -1,945,943, MDD 43.76, trades 688, gate fail.
- gen3: error, no metrics CSV.
- gen4: profit -2,153,502, MDD 39.05, trades 687, gate fail; existing graded-best but training-negative.
- gen5: profit -353,764, MDD 13.4, trades 111, daily_avg_trades 0.2, gate fail on daily frequency; rejected because profit <= 0 and MDD > 10.0.

## Replay Caveat
Prior P3 replay selected prior gen5 under `sparse_positive_v1`, but that replay is `diagnostic_only=true`. It is mechanics evidence only, not efficacy evidence, because the old P5 failure was already known.

## OOS Evidence
P5 was skipped by rule because P4 did not freeze a candidate.

OOS run-id row checks:
- `tick_sel_sparse_p5_seed_2022_20260604`: 0 rows
- `tick_sel_sparse_p5_seed_2026_20260604`: 0 rows
- `tick_sel_sparse_p5_ai_2022_20260604`: 0 rows
- `tick_sel_sparse_p5_ai_2026_20260604`: 0 rows

## Seed Comparison
No comparison was performed in this plan. Comparing without a frozen candidate would violate the predeclared process.

## Trade-Count Sufficiency
Not applicable. No AI OOS rows exist.

## Slippage Status
Not run. Slippage stress is blocked until a candidate exists and fixed 2022/2026 OOS rows exist.

## PBO/DSR Status
Not run. PBO/DSR is an advisory blocker until a candidate and OOS evidence exist.

## Forbidden Actions Check
- `final_approval`: not invoked.
- `export_winner`: not invoked.
- production strategy DB writes: not invoked.
- live broker / KHOPENAPI / V3K gate advancement: not invoked.
- `taskkill`: not used.
- official backtest engine edits: not performed.
- hard-gate edits: not performed.
- `backtest/graph` edits: not performed.

## Final Verdict
NEEDS_MORE_EVIDENCE

Rationale: the improved selection rule prevented a training-negative candidate from being sent to OOS, but the fresh research run did not find a positive eligible candidate. The process is safer and more honest, but it has not produced a candidate capable of challenging the human seed.

## Recommended Next Research Direction
- Do not run OOS for this P4 result.
- Investigate why the fresh 2023-2025 run collapses to high-MDD/negative candidates.
- Consider a separate plan for generation prompt/constraint improvements, especially reducing overtrading and enforcing positive-profit sparse candidates during training without weakening hard gates.
