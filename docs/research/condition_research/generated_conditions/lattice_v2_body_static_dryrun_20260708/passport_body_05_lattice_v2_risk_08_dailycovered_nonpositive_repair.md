# body_05_lattice_v2_risk_08_dailycovered_nonpositive_repair

- source_candidate_id: `lattice_v2_risk_08_dailycovered_nonpositive_repair`
- class: `risk_balanced_composite`
- preferred_data_lane: `min_primary`
- label: `hypothesis_seed`
- scope: static/dry-run only; no DB apply, replay, OOS, portfolio, or promotion
- rationale: Explicitly target min rows that had MDD<=35 and daily>=0.5 but nonpositive profit.
- expected_failure_mode_to_test: profit sign may not flip
- buy_sha256: `410cfa548c0a6fc1291964816631fd34bfdf33da904b3ce0a5add8c3577b5ca8`
- sell_sha256: `361481aeedba7a8f638c7b37688fd2d247eb985e32a222fc78cd76e821f97f1d`
