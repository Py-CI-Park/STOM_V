# body_03_lattice_v2_coverage_06_momentum_strength_surge_coverage

- source_candidate_id: `lattice_v2_coverage_06_momentum_strength_surge_coverage`
- class: `coverage_composite`
- preferred_data_lane: `min_primary`
- label: `hypothesis_seed`
- scope: static/dry-run only; no DB apply, replay, OOS, portfolio, or promotion
- rationale: Combine momentum_breakout and strength_surge fragments because both have sparse positive evidence.
- expected_failure_mode_to_test: family correlation may not add independent signal
- buy_sha256: `463c1e97834f001e607ba9d6770016f074749ec4dda840e33c8afd944a9e3211`
- sell_sha256: `f5243a9af045d12e9129099157de4892ffbc7476b6f7932a0129599e2cea0164`
