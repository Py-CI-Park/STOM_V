# Freeze / Preregistration Draft - Composite Coverage Repair

created_at: 2026-07-06T08:12:35+09:00
source_run_id: `lat_repair_composite_coverage_24_official_full_warm64_20260706`
status: draft_only_no_oos_executed

## Scope

- This draft is for review before any OOS or Plan D work.
- Current range forbids OOS, portfolio, and Plan D/P7 execution.
- Candidates come from official min full-period warm64 bounded preflight only.

## Freeze Candidate Priority

| rank | gen | condition_id | profit | mdd | daily | trades | sell_profile | components |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 6 | `repair_v2_20260706_04_cov04_profitmax_fourcell_sell_default_tp3_sl3_hold60` | 2164253 | 27.16 | 0.5 | 106 | `sell_default_tp3_sl3_hold60` | `S09_PMAX,S10_PMAX,M09_POS,M10_POS` |
| 2 | 4 | `repair_v2_20260706_03_cov03_sparse_positive_fourcell_sell_default_tp3_sl3_hold60` | 2055640 | 28.11 | 0.5 | 111 | `sell_default_tp3_sl3_hold60` | `S09_D03,S10_PMAX,M09_POS,M10_POS` |
| 3 | 22 | `repair_v2_20260706_12_cov12_all_positive_plus_l14_sell_default_tp3_sl3_hold60` | 1778558 | 20.31 | 1.0 | 211 | `sell_default_tp3_sl3_hold60` | `S09_D03,S10_PMAX,M09_POS,M10_POS,L14_NEAR` |
| 4 | 2 | `repair_v2_20260706_02_cov02_sparse_positive_balanced_sell_default_tp3_sl3_hold60` | 1417718 | 27.31 | 0.5 | 97 | `sell_default_tp3_sl3_hold60` | `S09_D03,S10_BAL,M09_POS` |
| 5 | 7 | `repair_v2_20260706_04_cov04_profitmax_fourcell_sell_protect_tp2p5_sl2_hold45` | 1179483 | 21.3 | 0.5 | 111 | `sell_protect_tp2p5_sl2_hold45` | `S09_PMAX,S10_PMAX,M09_POS,M10_POS` |
| 6 | 5 | `repair_v2_20260706_03_cov03_sparse_positive_fourcell_sell_protect_tp2p5_sl2_hold45` | 1133643 | 21.3 | 0.5 | 116 | `sell_protect_tp2p5_sl2_hold45` | `S09_D03,S10_PMAX,M09_POS,M10_POS` |
| 7 | 1 | `repair_v2_20260706_01_cov01_sparse_positive_core_sell_protect_tp2p5_sl2_hold45` | 1122503 | 20.95 | 0.5 | 98 | `sell_protect_tp2p5_sl2_hold45` | `S09_D03,S10_PMAX,M10_POS` |
| 8 | 3 | `repair_v2_20260706_02_cov02_sparse_positive_balanced_sell_protect_tp2p5_sl2_hold45` | 1069026 | 21.6 | 0.5 | 101 | `sell_protect_tp2p5_sl2_hold45` | `S09_D03,S10_BAL,M09_POS` |

## Required Before OOS

- User approval for the next range that explicitly permits OOS.
- Confirm no DB UPDATE/DELETE is required; keep strategy rows append-only.
- Freeze selected buy/sell sha256 values from the seed JSON and DB mapping ledger.
- Use official OOS/preregistration protocol from the parent plan; do not infer OOS from this train/full-period preflight.
