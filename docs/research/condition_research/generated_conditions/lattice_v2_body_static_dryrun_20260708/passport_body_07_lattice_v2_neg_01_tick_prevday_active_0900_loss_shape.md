# body_07_lattice_v2_neg_01_tick_prevday_active_0900_loss_shape

- source_candidate_id: `lattice_v2_neg_01_tick_prevday_active_0900_loss_shape`
- class: `negative_control`
- preferred_data_lane: `tick_diagnostic_or_min_negative_control`
- label: `hypothesis_seed`
- scope: static/dry-run only; no DB apply, replay, OOS, portfolio, or promotion
- rationale: Known-failed tick-like discovery shape retained only to catch misleading success output.
- expected_failure_mode_to_test: expected no_go control
- buy_sha256: `bc73ad16bee4caac9171a9a8157652161c5c9fa2f6b2a599484442c47b4f0a28`
- sell_sha256: `015617a18baaf0b41c6423f97d879a88165577af787de1d4dedfd7aa49c81372`
