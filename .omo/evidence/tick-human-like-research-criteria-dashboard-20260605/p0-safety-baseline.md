# P0 Safety, Dashboard, And Criteria Baseline

Status: `complete`

## Snapshot

| Item | Value |
|---|---|
| Branch | `lazycodex/tick-sparse-positive-generation-improvement-20260604` |
| HEAD | `84acb6cb` |
| Dashboard | `http://127.0.0.1:8770/ui/` |
| Health | `{"status":"ok","contract_version":2}` |
| Protected path status | no output from protected-path `git status --short` |
| Runtime process cleanup | none performed |
| Blanket taskkill | not used |

## Read Evidence

| Source | Key Point |
|---|---|
| `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p5-decision-card.md` | C_T blocker follows the buy branch; do not retry large windows before bounded CSV+metrics. |
| `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md` | Strict fixed 2022/2026 OOS rejected the frozen sparse-positive candidate; this is a promotion rejection, not a research dead-end. |
| `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md` | Project direction should separate research discovery from strict seed/human-superiority claims and avoid premature claims. |

## Criteria Gap Confirmed

The prior wording treated OOS mainly as a strict promotion gate. The current plan now requires explicit research modes:

| Mode | Research Meaning |
|---|---|
| `disabled` | OOS is not run or used for candidate rejection; result is research-only. |
| `advisory` | OOS can be shown but cannot reject a research family by itself. |
| `promotion_only` | Fixed OOS is used only after a candidate is frozen for a strict claim. |

## P0 Verdict

Proceed to P1. Keep official engines, hard gates, `backtest/graph`, production export, live broker, and V3K paths untouched.
