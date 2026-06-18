# P2 Diagnostic Copy Map

Status: `complete`

## Copies

Artifact: `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p2-diagnostic-copy-map.json`

| Role | Source | Diagnostic Name | Table | Lines | Hash Match |
|---|---|---|---|---:|---|
| C_T buy | `C_T_900_920_U2_B` | `CT_DIAG_CTB_902905_20260605` | `stockbuy` | `431` | yes |
| C_T sell | `C_T_900_920_U2_S` | `CT_DIAG_CTS_902905_20260605` | `stocksell` | `87` | yes |
| Control buy | `Tick_B_902_905_Update_2` | `CT_DIAG_CTLB_902905_20260605` | `stockbuy` | `128` | yes |
| Control sell | `Tick_S_902_905_Update_2` | `CT_DIAG_CTLS_902905_20260605` | `stocksell` | `47` | yes |

## Runtime Configs

- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-ctbuy-controlsell-config.json`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p3-controlbuy-ctsell-config.json`

Both configs use:

- Date: `2025-01-03`
- Window: `09:02:00..09:05:00`
- Timeframe: `tick`
- Warm engines: `1`
- Warm timeout: `120s`
- Outer wall cap planned: `240s`

## Cleanup Policy

The `CT_DIAG_*_20260605` rows are temporary runtime DB rows. They must be deleted after P3/P4 evidence is captured, with cleanup recorded in Final.
