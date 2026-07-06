# Repair Composite Selected OOS Preregistration

created_at: 2026-07-06T10:41:56+09:00
status: finalized_before_oos_execution
scope: repair-composite-selected-oos-no-D
source_run_id: `lat_repair_composite_expanded_48_official_full_warm64_20260706`
selected_count: 16

## Fixed Inputs

- freeze recheck: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_freeze_recheck_20260706.json`
- pairs json: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/pairs_repair_composite_selected_16_oos_20260706.json`
- config json: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/oos_config_min_selected16_20260706.json`
- lane: `min`
- DB: `_database/stock_min_back.db`
- OOS window: `2026-01-01~2026-02-27`
- time window: `09:00~15:19`
- warm engines: `64`
- run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`

## Selection Rule

`gate_passed and mdd <= 25 and daily_avg_trades >= 0.8; top16 by profit then lower mdd`.

## Decision Rule

- survivor: status ok, gate_passed true, profit > 0, MDD <= 35, daily_avg_trades >= 0.5.
- hold: status ok and profit > 0, but one non-critical gate fails.
- no_go: error/no_trades, profit <= 0, or MDD > 35.

## Caveat

The selected 16 were chosen from a full-period min preflight that included the fixed OOS window. Therefore this run is a fixed OOS-style robustness replay for Plan D input screening, not a fully blind discovery OOS.

## Selected Candidates

| rank | condition_id | buy_sha256 | sell_sha256 | preflight_profit | preflight_mdd | daily | sell_profile |
| ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60` | `3158a4cfd78c4cc0edee798ba2b1bb58190e676ffa2774fa52cb06059a4b032e` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 1887171.0 | 19.25 | 1.0 | `sell_default_tp3_sl3_hold60` |
| 2 | `repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60` | `2ef5f5be3e8a7332efec2e80338a5acd95afc72386c1e9f081b9ee7783491e52` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 1393641.0 | 13.34 | 1.8 | `sell_default_tp3_sl3_hold60` |
| 3 | `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90` | `3158a4cfd78c4cc0edee798ba2b1bb58190e676ffa2774fa52cb06059a4b032e` | `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6` | 1340830.0 | 18.56 | 0.9 | `sell_loose_tp4_sl3_hold90` |
| 4 | `repair_v3_20260706_25_daily_boost_core_l13_sell_default_tp3_sl3_hold60` | `ddc2608237d36cb984a778f59572be4e7544ce827751bc2ade9a06920e125233` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 1285028.0 | 14.11 | 1.8 | `sell_default_tp3_sl3_hold60` |
| 5 | `repair_v3_20260706_13_top_four_plus_l14_sell_tight_tp3_sl2p5_hold60` | `3158a4cfd78c4cc0edee798ba2b1bb58190e676ffa2774fa52cb06059a4b032e` | `01c800b9d64fa573fd823487d7e88e33b611ba818ca3b390b0904bb9464b35ce` | 1203245.0 | 17.0 | 1.0 | `sell_tight_tp3_sl2p5_hold60` |
| 6 | `repair_v3_20260706_17_balanced_plus_l14_sell_default_tp3_sl3_hold60` | `045cc07ee3d87a11e2aceaacc01132b2057ac78e373dee770099028a21fb184d` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 1140636.0 | 19.84 | 0.9 | `sell_default_tp3_sl3_hold60` |
| 7 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_default_tp3_sl3_hold60` | `7e8bfbd4c2bceaba03868658c8242e31c00c303efea82e44e2682c5328b95716` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 1123124.0 | 22.58 | 1.2 | `sell_default_tp3_sl3_hold60` |
| 8 | `repair_v3_20260706_15_top_four_plus_l13_l14_sell_default_tp3_sl3_hold60` | `e347cd23d07dc0bc0b3559e2f8f68b0af4ea23238f8e65f8796844a4de2b80ec` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 1059257.0 | 18.49 | 2.1 | `sell_default_tp3_sl3_hold60` |
| 9 | `repair_v3_20260706_16_sparse_four_plus_l13_l14_sell_default_tp3_sl3_hold60` | `ab0983742a1a4c19a1cbe9333b7b078a93dd0bcc2c74442c27b0ab9d79263109` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 950644.0 | 19.21 | 2.1 | `sell_default_tp3_sl3_hold60` |
| 10 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90` | `8bc41fe1cead5449625dc6daf7b675fdc23009237d382a32028b6c10c413feb4` | `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6` | 874241.0 | 17.04 | 0.8 | `sell_loose_tp4_sl3_hold90` |
| 11 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_loose_tp4_sl3_hold90` | `1ca21c07387c0ae1c709af4fd9b16ed4602b781a8f594309af62d65b9e7f0112` | `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6` | 852468.0 | 17.77 | 0.8 | `sell_loose_tp4_sl3_hold90` |
| 12 | `repair_v3_20260706_27_l14_focus_sparse_strength_sell_default_tp3_sl3_hold60` | `877bd24ab0b9ac9543937a64d7965fa47a28db6e43da199ff4832dd04181fa83` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 797362.0 | 20.92 | 0.8 | `sell_default_tp3_sl3_hold60` |
| 13 | `repair_v3_20260706_17_balanced_plus_l14_sell_tight_tp3_sl2p5_hold60` | `045cc07ee3d87a11e2aceaacc01132b2057ac78e373dee770099028a21fb184d` | `01c800b9d64fa573fd823487d7e88e33b611ba818ca3b390b0904bb9464b35ce` | 751652.0 | 18.99 | 0.9 | `sell_tight_tp3_sl2p5_hold60` |
| 14 | `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90` | `7e8bfbd4c2bceaba03868658c8242e31c00c303efea82e44e2682c5328b95716` | `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6` | 726216.0 | 20.5 | 1.2 | `sell_loose_tp4_sl3_hold90` |
| 15 | `repair_v3_20260706_25_daily_boost_core_l13_sell_loose_tp4_sl3_hold90` | `ddc2608237d36cb984a778f59572be4e7544ce827751bc2ade9a06920e125233` | `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6` | 718567.0 | 13.19 | 1.7 | `sell_loose_tp4_sl3_hold90` |
| 16 | `repair_v3_20260706_24_strength_profitmax_l13_l14_sell_default_tp3_sl3_hold60` | `6df2e60c6a1dd2fe0b8f4edba7e9359d8419fa6b8f78a446351ce53305b6466f` | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` | 715983.0 | 21.06 | 2.0 | `sell_default_tp3_sl3_hold60` |

## Forbidden In This Scope

- Plan D/P7 execution
- portfolio output
- full tick 288 or full min 288
- OOS for any candidate outside selected 16
- DB UPDATE/DELETE
- A3/promotion/export/live/final changes
