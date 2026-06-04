# DOCS KNOWLEDGE BASE

## OVERVIEW
`docs/` is the durable decision/history layer for this branch: update logs, V3K gate records, research notes, plans, references, and carry-forward registry entries.

## STRUCTURE
```text
docs/
??? update_log/              # dated execution logs, gate records, handoffs
??? research/                # condition discovery and analysis notes
??? reference/               # good-result screenshots/reports and reference material
??? plans/, superpowers/     # planning artifacts
??? CARRY_FORWARD_REGISTRY.md
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| V3K starting context | `update_log/2026-05-08_*` | Goal reset and unmet-feature audit. |
| Gate checklist | `update_log/2026-05-14_v3k_goal_completion_audit_checklist.md` | Gate status/prereqs. |
| Gate phrase guard | `update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md` | Exact approval handling. |
| Gate 5/6 blocker | `update_log/2026-05-14_v3k_gate5_gate6_review_only_blocked.md` | Review-only state. |
| Carry-forward | `CARRY_FORWARD_REGISTRY.md` | Long-running migration facts. |
| Condition research | `research/auto_condition_discovery_research.md` | B_* / validation guidance. |
| Good results | `reference/STOM_Good_Results/` | Human-good condition references. |

## CONVENTIONS
- Use dated filenames for new update logs: `YYYY-MM-DD_short_topic.md`.
- Distinguish evidence from inference, especially in gate records.
- Do not record fake approvals, fake USER_ACKs, or completed gates without concrete evidence.
- Reference docs can guide strategy generation, but do not mutate protected result data.

## ANTI-PATTERNS
- Do not use docs to bypass runtime gate scripts.
- Do not mark V3K complete while gate progress is still `3/6`.
- Do not treat screenshots/reference reports as live trading proof.
