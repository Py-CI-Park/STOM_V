# P3 Selector Freeze Procedure

## Selector
- selector_version: sparse_positive_v1
- application point: after `tick_spgen_p5_train_2023_2025_20260604` completes and before any OOS command is created or run
- input scope: training rows only from `ai_strategy_loop/state/loop_runs.db`
- output artifact: `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p5-selected-candidate.json`

## Required Artifact Fields
- `selector_version`
- `run_id`
- `config_path`
- `config_hash`
- `selected`
- `blocked`
- `gen_no`
- `buy_name`
- `sell_name`
- `metrics`
- `oos_excluded=true`
- `diagnostic_only=false`
- `forbidden_oos_fields_present=false`

## OOS-Blind Rule
The selector reads training rows only. It must not read or accept fields named `oos_2022`, `oos_2026`, `seed_2022`, `seed_2026`, `ai_2022`, `ai_2026`, `slippage`, `pbo`, `dsr`, `final_verdict`, or `post_oos_analysis`.

Any candidate row containing forbidden OOS fields is invalid and must be rejected by the parser before ranking.

## OOS Gate
If `selected=false`, write `p5-selector-blocked.md`, write `p6-oos-blocked.md`, and do not run 2022/2026 OOS.

If `selected=true`, freeze the exact `buy_name`, `sell_name`, `gen_no`, `bucket`, and metrics in `p5-selected-candidate.json` before building fixed 2022/2026 OOS configs. No OOS-after-the-fact candidate change is allowed.
