# V3K Page 080 Phase F gate2 execution plan

`V3K_PHASE_F_GATE2_EXECUTION_PLAN`

## Goal

Execute only the approved second gate, `phase-f-f4-on-await-user-approval`, after gate1 evidence exists. The implementation uses the local GUI sidecar as the source-of-truth for the Phase F analyzer strategy flag and leaves live order/exit consumption blocked.

## Scope

- Approval gate: `phase-f-f4-on-await-user-approval`
- Canonical approval phrase: `I approve phase-f-f4-on-await-user-approval only`
- Required USER_ACK: `V3K_PHASE_F_USER_ACK=1`
- Enable registry: `V3K-PHASE-F-ENABLE`
- Source-of-truth: `_v3k_sidecar/v3k_gui_settings.json`
- Enabled sidecar setting: `V3K_PHASE_F_ANALYZER_STRATEGY=true`
- Writer: `scripts/write_v3k_phase_f_sidecar_enable.py`
- Audit: `scripts/audit_v3k_phase_f_gate2_execution.py`

## Out of scope

- No DB cutover
- No KHOPENAPI connect/login
- No Phase G/H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

## Verification

```powershell
$env:V3K_PHASE_F_USER_ACK='1'; python scripts/write_v3k_phase_f_sidecar_enable.py --approve "I approve phase-f-f4-on-await-user-approval only" --format json
python scripts/audit_v3k_phase_f_gate2_execution.py
python scripts/smoke_v3k_phase_f_default_off.py
python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
python scripts/audit_v3k_phase_f_rollback.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
git ls-files _v3k_sidecar/v3k_gui_settings.json
```

## Stop condition

- `V3K_PHASE_F_GATE2_EXECUTION` audit passes.
- Actual gate execution progress becomes `2/6`.
- Next gate is `phase-g-g3-on-await-user-approval`.
- `_v3k_sidecar` runtime artifact remains uncommitted.
