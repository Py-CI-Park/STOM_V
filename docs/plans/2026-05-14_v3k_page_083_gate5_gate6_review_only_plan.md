# V3K Page 083 Gate5/Gate6 review-only plan

`V3K_GATE5_GATE6_REVIEW_ONLY_PLAN`

## Goal

Honor the operator decision to pause the blocked Phase H live-dryrun gate and inspect later gates in review-only mode. This page does not advance actual gate execution because Gate 4 remains incomplete.

## Scope

- Mode: `review-only`
- Current blocked gate: `phase-h-h2-h3-live-dryrun-await-user-approval`
- Review target 1: `f1-actual-db-cutover-await-user-approval`
- Review target 2: `live-order-exit-rule-consumption-await-user-approval`
- Audit: `scripts/audit_v3k_gate5_gate6_review_only_blocked.py`
- Marker: `V3K_GATE5_GATE6_REVIEW_ONLY_BLOCKED`
- Actual gate progress: `3/6`

## Review-only findings

| Gate | Review finding | Actual execution status |
| --- | --- | --- |
| Gate 4 Phase H live dry-run | Gate 4 blocked by missing KHOPENAPI sentinel. | Still current gate. |
| Gate 5 F1 actual DB cutover | Prep artifacts exist, but actual cutover requires Gate 4 completion, `V3K_CUTOVER_USER_ACK=1`, backup apply, checksum manifest, rollback, post-health, and monitoring. | Blocked / out-of-order. |
| Gate 6 live order/exit consumption | Prep artifacts exist, but live decision requires all earlier gates, `V3K_LIVE_DECISION_USER_ACK=1`, enable registry, kill switch, shadow/dry-run proof, staged rollout, and monitoring. | Blocked / out-of-order. |

## Out of scope

- No USER_ACK creation
- No enable registry creation
- No DB cutover
- No KHOPENAPI connect/login
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

## Verification

```powershell
python scripts/audit_v3k_gate5_gate6_review_only_blocked.py
python scripts/smoke_v3k_cutover_dryrun.py
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.page083.json
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
git ls-files _v3k_sidecar/v3k_gui_settings.json
```

## Stop condition

- Gate5/Gate6 review-only audit passes.
- Actual gate execution remains `3/6`.
- Phase H remains the current executable gate until KHOPENAPI-compatible evidence exists.
- Gate 5 and Gate 6 approval phrases remain rejected as out-of-order.
