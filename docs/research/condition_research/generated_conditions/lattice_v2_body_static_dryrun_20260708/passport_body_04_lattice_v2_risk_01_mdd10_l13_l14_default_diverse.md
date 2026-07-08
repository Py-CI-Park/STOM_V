# body_04_lattice_v2_risk_01_mdd10_l13_l14_default_diverse

- source_candidate_id: `lattice_v2_risk_01_mdd10_l13_l14_default_diverse`
- class: `risk_balanced_composite`
- preferred_data_lane: `min_primary`
- label: `hypothesis_seed`
- scope: static/dry-run only; no DB apply, replay, OOS, portfolio, or promotion
- rationale: Prioritize MDD<=10 survivor-like fragments while varying component mix rather than copying code.
- expected_failure_mode_to_test: low MDD may come with too few trades
- buy_sha256: `727554860621cd54544b22361927897804eb0526da9c6727b4b3ea95ee35a719`
- sell_sha256: `d3ba2e7438a8d3819073e67adbef8765937af7bbe6787e880d812b65c87a761a`
