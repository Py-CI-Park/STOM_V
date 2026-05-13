# V3K Page 062 GUI sidecar default-OFF payload preview plan

| Field | Value |
| --- | --- |
| Date | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 062 |
| source | Page059 approval execution packet, Page060 readiness audit, Page061 remaining gate blocker audit |
| marker | `GUI_SIDECAR_DEFAULT_OFF_PAYLOAD_PREVIEW` |
| status | plan |
| gate | `gui-sidecar-write-await-user-approval` |

---

## 1. Purpose

Page062 prepares the first GUI sidecar write gate without executing it. The only safe work before explicit approval is to prove the exact default-OFF payload that would be written later and to verify that previewing the payload does not create `_v3k_sidecar`, DB, report, or live runtime artifacts.

This page intentionally does not implement the actual writer. It does not create USER_ACK, does not write `_v3k_sidecar/v3k_gui_settings.json`, does not wire MainWindow, does not turn ON Phase F/G/H, does not touch operating `_database/`, and does not connect Kiwoom live order/exit rules.

---

## 2. Deliverables

- `scripts/preview_v3k_gui_sidecar_default_payload.py`
- Page062 plan and update log
- V3K audit suite step for payload preview
- VERIFY-1B and runtime activation matrix coverage
- Carry-forward registry entry

---

## 3. Preview contract

| Contract | Requirement |
| --- | --- |
| target | `_v3k_sidecar/v3k_gui_settings.json` only after later approval |
| current mode | preview-only, stdout only |
| payload | schema v1, current settings surface version, all V3K settings false |
| validation | `validate_v3k_gui_sidecar_payload` must accept it and report all-off |
| artifacts | no `_v3k_sidecar`, `_database`, DB, backup, log, report, or live artifact status |
| runtime | Kiwoom order/exit/live runtime unchanged |
| LS dependency | no direct LS Securities dependency |

---

## 4. STOP condition

Stop if preview generation writes any repository artifact, enables any V3K flag, creates USER_ACK-equivalent state, or weakens the Page061 blocker audit.

Directive: `GUI_SIDECAR_DEFAULT_OFF_PAYLOAD_PREVIEW` is not approval for actual sidecar write. It is only a deterministic no-write payload preview for a later approved execution cycle.
