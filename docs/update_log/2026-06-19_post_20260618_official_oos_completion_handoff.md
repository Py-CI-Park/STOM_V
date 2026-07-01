# 2026-06-19 Post-20260618 Official OOS Completion Handoff

## Scope

This handoff closes the research-only post-20260618 official OOS sequence for the robust primary candidate. It does not change dashboard UI/frontend/bundles, `backtest.py`, live trading, V3K, serial-key behavior, export/final approval, or operating strategy DB paths.

## Page / Goal Progress

| Page | Ultragoal story | Status | Evidence |
|---:|---|---|---|
| P7/P8 | Run robust primary official OOS | complete | `.omo/evidence/tmap-walkforward/post-q4-r8-lowcap-official-oos-summary-20260619.json` |
| P9/P10 | Build robust decision and portfolio report | complete | `.omo/evidence/tmap-walkforward/post-20260618-robust-decision-card-20260619.json` |
| P11/P12 | Shadow and standalone follow-up checks | complete | `.omo/evidence/tmap-walkforward/post-20260618-shadow-standalone-followup-20260619.json` |
| P13/P14 | Research record handoff and verification | complete | this file + final verification artifacts |

## Official OOS Result — r8 Low-Cap Entry Filter

| Slice | Status | Profit KRW | MDD | Trades | Evidence type |
|---|---|---:|---:|---:|---|
| 2025 Q4 stress | pass | 310,886 | 9.25% | 19 | 공식 OOS |
| 2022-2025 full-year + 2026 YTD aggregate | pass | 7,292,861 | max 19.09% | 263 | 공식 OOS |

All official OOS rows in the summary are wrapper-backed and inspectable. 2026 is YTD through 2026-02-28, not full-year 2026. The official OOS evidence is for `r8_exclude_cap_lt_1500` only.

## Portfolio-Layer Decision

| Layer | Status | Profit KRW | MDD | Notes |
|---|---|---:|---:|---|
| r8 low-cap entry filter | `oos_passed` | 7,292,861 | max 19.09% | official OOS |
| exit2 prior-month -500k exclusion | supported as portfolio rule | 31,702,635 | 9.2726% | separate portfolio-layer evidence |
| combined label | research-only composite | — | — | `공식 OOS(r8 low-cap) + 포트폴리오 규칙(exit2 prior-month)` |

The prior-month exit2 rule is not relabeled as a plain official buy/sell OOS pair.

## Shadow / Standalone Follow-up

| Candidate | Role | Status | Evidence |
|---|---|---|---|
| `r8_exclude_cap_lt_1500` | standalone attribution | covered | official entry-filter OOS above |
| `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | high-overfit shadow comparison | kept separate | CSV reanalysis only; not promotion evidence |

## Verification Notes

- JSON artifacts parse and point to inspectable snapshots/results.
- Wrapper outputs are evidence-local `.sqlite`/snapshot/current-state artifacts.
- Protected runtime path status remains clean for `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph`, `.omx/reports`, `v3k_settings*.json`, and `_v3k_sidecar/v3k_gui_settings.json`.
- Stale wrapper/batch OOS processes from a log-only rerun attempt were stopped; no accepted result depends on the timed-out log-only 2026 rerun.

## Recommendation

Research can stop this OOS page as `oos_passed` for the robust primary entry-filter layer. Next work should either:

1. continue with a separately approved production/export readiness plan, or
2. run a fresh combined portfolio simulation specifically for `r8_exclude_cap_lt_1500 + exit2 prior-month` if exact combined allocation metrics are needed before any promotion discussion.
