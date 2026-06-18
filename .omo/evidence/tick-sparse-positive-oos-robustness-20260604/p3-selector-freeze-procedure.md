# P3 Selector Freeze Procedure

- selector_version: `yearly_sparse_robust_v1`
- train run id: `tick_oosrob_p5_train_2023_2025_20260604`
- output artifact: `.omo/evidence/tick-sparse-positive-oos-robustness-20260604/p5-selected-candidate.json`
- selection input: training generations from the P5 run only
- CSV source: each generation row `csv_path`, resolved before selection
- OOS fields: forbidden before selector freeze

Procedure:
1. Complete P4 smoke and verify prompt logging; smoke is diagnostic only.
2. Run P5 train with `p3-train-config.json`.
3. Parse P5 generation rows into `CandidateGeneration`, including `csv_path`.
4. Apply `yearly_sparse_robust_v1` to P5 training rows only.
5. Write `p5-selected-candidate.json` with `oos_excluded=true`, `diagnostic_only=false`, `policy_hash`, `config_hash`, aggregate checks, yearly breakdown, eligible candidates, and rejected candidates.
6. If `selected=false`, write `p5-selector-blocked.md` and skip P6 OOS.
7. If `selected=true`, freeze exact `run_id`, `gen_no`, `buy_name`, `sell_name`, config hash, policy hash, and yearly breakdown before building P6 configs.
8. Do not mutate or reselect the candidate after any P6 OOS result appears.

Forbidden in this procedure:
- 2022/2026 OOS metrics as selector inputs.
- OOS-after-the-fact reselection.
- `final_approval` or `export_winner`.
- hard-gate, official engine, or `backtest/graph` edits.
