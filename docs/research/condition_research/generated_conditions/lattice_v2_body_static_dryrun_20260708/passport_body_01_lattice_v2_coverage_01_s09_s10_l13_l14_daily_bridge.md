# body_01_lattice_v2_coverage_01_s09_s10_l13_l14_daily_bridge

- source_candidate_id: `lattice_v2_coverage_01_s09_s10_l13_l14_daily_bridge`
- class: `coverage_composite`
- preferred_data_lane: `min_primary`
- label: `hypothesis_seed`
- scope: static/dry-run only; no DB apply, replay, OOS, portfolio, or promotion
- rationale: Bridge S09/S10 morning coverage with L13/L14 low-MDD fragments to attack daily_avg_trades gap.
- expected_failure_mode_to_test: low daily trades with otherwise low-MDD positive fragments
- buy_sha256: `05f190da08e931d71d473793e51ea333cbb33ae4da3eb1a2bc5528a5ec961b98`
- sell_sha256: `361481aeedba7a8f638c7b37688fd2d247eb985e32a222fc78cd76e821f97f1d`
