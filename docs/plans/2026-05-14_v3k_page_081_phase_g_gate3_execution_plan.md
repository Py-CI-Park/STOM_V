# V3K Page 081 Phase G gate3 execution plan

`V3K_PHASE_G_GATE3_EXECUTION_PLAN`

## Goal

Execute only the approved third gate, `phase-g-g3-on-await-user-approval`, after gate1 and gate2 evidence exists. The implementation uses the local GUI sidecar as the source-of-truth for the Phase G microstructure engine flag and leaves live order/exit consumption blocked.

## Scope

- Approval gate: `phase-g-g3-on-await-user-approval`
- Canonical approval phrase: `I approve phase-g-g3-on-await-user-approval only`
- Required USER_ACK: `V3K_PHASE_G_USER_ACK=1`
- Enable registry: `V3K-PHASE-G-ENABLE`
- Source-of-truth: `_v3k_sidecar/v3k_gui_settings.json`
- Enabled sidecar setting: `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=true`
- Preserved sidecar setting: `V3K_PHASE_F_ANALYZER_STRATEGY=true`
- Rollback guard: `V3K_PHASE_G_DISABLE=1`
- Writer: `scripts/write_v3k_phase_g_sidecar_enable.py`
- Audit: `scripts/audit_v3k_phase_g_gate3_execution.py`

## Out of scope

- No DB cutover
- No KHOPENAPI connect/login
- No Phase H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

## Verification

```powershell
$env:V3K_PHASE_G_USER_ACK='1'; python scripts/write_v3k_phase_g_sidecar_enable.py --approve "I approve phase-g-g3-on-await-user-approval only" --format json
python scripts/audit_v3k_phase_g_gate3_execution.py
python scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/backtest_v3k_phase_g_parity.py
python scripts/benchmark_v3k_phase_g_engine.py
python scripts/audit_v3k_phase_g_ls_excise.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
git ls-files _v3k_sidecar/v3k_gui_settings.json
```

## Stop condition

- `V3K_PHASE_G_GATE3_EXECUTION` audit passes.
- Actual gate execution progress becomes `3/6`.
- Next gate is `phase-h-h2-h3-live-dryrun-await-user-approval`.
- `_v3k_sidecar` runtime artifact remains uncommitted.
