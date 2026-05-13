# V3K GUI sidecar default-OFF payload preview

| Field | Value |
| --- | --- |
| Date | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 062 |
| source | Page059 approval execution packet, Page060 readiness audit, Page061 remaining gate blocker audit |
| marker | `GUI_SIDECAR_DEFAULT_OFF_PAYLOAD_PREVIEW` |
| status | completed-preview-only |
| gate | `gui-sidecar-write-await-user-approval` |

---

## 1. Conclusion

The first GUI sidecar write gate now has a deterministic default-OFF payload preview. The preview is generated to stdout only and is validated against the existing sidecar schema. This advances the gate by fixing the exact first payload while keeping the actual write blocked.

No ON/DB/live execution. No USER_ACK creation. No enable registry creation. No KHOPENAPI connect or login. No operating `_database/` write. No DB file commit. No `_v3k_sidecar` artifact creation. No actual writer implementation. No MainWindow wiring. No Kiwoom live runtime change. No live order/exit rule wiring. No direct LS Securities dependency.

---

## 2. Added preview surface

`scripts/preview_v3k_gui_sidecar_default_payload.py` builds and validates the first sidecar payload candidate:

- target: `_v3k_sidecar/v3k_gui_settings.json`
- schema: `V3K_GUI_SIDECAR_SCHEMA_VERSION`
- surface: `V3K_SETTINGS_SURFACE_VERSION`
- settings: `v3k_settings_defaults()`
- approval state: `preview-only-user-approval-required`
- mode: stdout only, no file write

The script rejects the preview if validation fails, if any V3K setting/feature flag is enabled, if forbidden artifact status is dirty, or if preview execution changes artifact status.

---

## 3. Prompt-to-artifact checklist

| Requirement | Evidence | Status |
| --- | --- | --- |
| exact first payload fixed | `build_default_off_payload()` | complete |
| payload remains default-OFF | `assert_default_off_payload()` | maintained |
| actual sidecar write blocked | no writer, no USER_ACK, no `_v3k_sidecar` artifact | maintained |
| artifact status clean | preview script + audit suite artifact guard | maintained |
| Kiwoom retained | no runtime wiring or live path touched | maintained |
| direct LS Securities dependency excluded | no broker dependency in preview | maintained |
| approval gate still blocked | Page061 blocker audit remains in suite | maintained |

---

## 4. Next step

The recommended approval order first remains `gui-sidecar-write-await-user-approval`. A later approved execution may use this preview as the payload source, but only after explicit user approval, USER_ACK or equivalent update_log approval, owner acceptance, immediate pre-write audit, rollback acceptance, and post-write validation.

Directive: Page062 is preview-only. Passing it means the first payload is deterministic and safe to review; it does not approve or execute sidecar write, Phase F/G/H ON, DB cutover, KHOPENAPI connect/login, Kiwoom live runtime change, or live order/exit rule consumption.
