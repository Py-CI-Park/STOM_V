# SCRIPTS KNOWLEDGE BASE

## OVERVIEW
`scripts/` contains verification, audit, smoke, rollback, and V3K gate writer tooling. Many scripts are safety gates, not generic helpers.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Nonrelease guard | `verify_nonrelease_sync.py` | Required verifier for this 2U_C lane. |
| pyd GUI contract | `verify_pyd_gui_contract.py` | MainWindow/import/activation parity checks. |
| Offline GUI smoke | `smoke_offline_gui.py` | GUI smoke evidence helper. |
| V3K audit suite | `run_v3k_audit_suite.py` | Umbrella audit entry. |
| Gate status audits | `audit_v3k_*.py` | Read-only gate/status assertions. |
| Completed gate writers | `write_v3k_gui_sidecar_from_preview.py`, `write_v3k_phase_f_sidecar_enable.py`, `write_v3k_phase_g_sidecar_enable.py` | Only for already-approved gate behavior. |
| Later gate writers | `write_v3k_phase_h_user_ack.py`, `write_v3k_gate5_user_ack.py`, `write_v3k_gate6_user_ack.py` | Must remain blocked without exact approvals/prereqs. |
| Test runner | `run_tests.py`, `pre_commit_check.py` | Local validation entry points. |

## CONVENTIONS
- Use `verify_nonrelease_sync.py` in this branch, not `verify_release_sync.py`.
- Audit scripts should stay read-only unless their name and docs explicitly define a gated write.
- Gate writer scripts require exact approval phrase, correct gate order, and environment evidence.
- Keep script output deterministic enough for tests and future audit logs.

## ANTI-PATTERNS
- Do not create USER_ACK or enable registry headings from scripts unless the gate is valid and approved.
- Do not write operating DBs, live wiring, or protected report paths from convenience scripts.
- Do not weaken checks to pass local dirty state.

## COMMANDS
```powershell
python scripts/verify_nonrelease_sync.py
python scripts/audit_v3k_gate5_gate6_review_only_blocked.py
python scripts/run_tests.py --unit
python scripts/pre_commit_check.py
```
