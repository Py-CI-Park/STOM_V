# Dashboard Duplicate And Overlap Audit

Generated: 2026-06-18T22:55:14+09:00  
Plan page: 10  
Scope: dashboard feature pairs/groups. Classifications used: `true duplicate`, `divergent-by-design`, `shared-helper candidate`, `obsolete`, `overlap-not-duplicate`.

## Summary

| Classification | Count | Meaning |
|---|---:|---|
| true duplicate | 1 | Current or recently resolved duplicate behavior with one canonical owner. |
| divergent-by-design | 5 | Similar label/domain but different user job or payload; do not merge without design change. |
| shared-helper candidate | 8 | Similar rendering/state handling that could share helpers without collapsing UX. |
| obsolete | 2 | Older path/list/process should be retired or replaced by governed index. |
| overlap-not-duplicate | 3 | Same research domain, different granularity or lifecycle. |

## Feature Pair/Group Audit

| # | Pair/group | Classification | Evidence | Risk | Recommended action |
|---:|---|---|---|---|---|
| 1 | `HallOfFamePanel` vs `_RpHallOfFame` | divergent-by-design | `docs/web_dashboard_expansion/PROG_P7_FIELD_DIFF.md` documents different columns and behaviors; evolution HoF has sort/filter/gallery/refresh, Research Pro HoF has code expansion/workbench workflow. | Forced merge would hide unique fields or create config-heavy component. | Keep separate; share CSS/table tokens only. |
| 2 | `RunComparePanel` legacy `panels.jsx` vs canonical `run-compare.jsx` | true duplicate (resolved) | `docs/web_dashboard_expansion/PHASE14_P1_DEDUP_CLEANUP.md`; current `frontend/panels.jsx` is a tiny barrel and `frontend/run-compare.jsx` owns `RunComparePanel`. | Regression if another global silently shadows it. | Keep `test_no_duplicate_globals` guard; no new merge work. |
| 3 | `ResearchRecordsPanel` vs `ResearchWikiPanel`/docs list | shared-helper candidate | Records uses `/research_records`; wiki/docs uses `/research_docs` and `/research_doc`. Both expose research provenance. | Users may not know whether to look under Records or Wiki. | Later slice: shared campaign/doc index adapter with separate record/detail views. |
| 4 | `/research_records` evidence index vs `.omo/evidence/stom-reorg-20260618/research-registry.*` | overlap-not-duplicate | Registry is planning/process evidence; endpoint indexes walk-forward research campaigns. | Manual registry and live endpoint can drift. | Link registry items to endpoint campaigns; do not merge storage yet. |
| 5 | `BtGuiParitySection` in Backtest results vs Evolution GUI Parity panel | shared-helper candidate | `frontend/bt-result-area.jsx` and `frontend/evolution-gui-parity-panel.jsx` both render `BtGuiParitySection`. | Duped surrounding chips/status may diverge. | Keep shared chart section; extract small status-chip helper only if edits continue. |
| 6 | Evolution `ProcessFlowPanel` vs Research Lab/Pro process overlays | shared-helper candidate | `phase-detail.jsx` owns live process panel; `rl-panel.jsx` and `rp-heatmap.jsx` own overlay variants. | Separate stage labels can drift. | Share `window.STOM_PIPELINE`/stage mapping; keep display modes separate. |
| 7 | `/process_flow` static HTML vs Process tab iframe | overlap-not-duplicate | Process tab intentionally embeds `/process_flow`; static page remains route artifact. | Styling mismatch if regenerated without dashboard CSS awareness. | Treat static HTML as source artifact for process tab; verify through harness. |
| 8 | Research Lab vs Research Pro | divergent-by-design | Lab validates candidates and docs; Pro aggregates portfolio/niche/heatmap/hall-of-fame. | Merging would make one overloaded research page. | Keep top-level separate, but standardize empty/loading/error components. |
| 9 | Verdict tab vs freeze/portfolio verdict panels in Pro | divergent-by-design | Verdict tab is decision history/action surface; Pro verdict snippets are analysis context. | Merging may mix audit trail with exploratory analysis. | Link from Pro to Verdict, not component merge. |
| 10 | `/portfolio_sim` vs `/portfolio_preview` | shared-helper candidate | Both serve portfolio what-if/preview style data used by Research Pro. | Slight payload differences can create user confusion. | Document payload boundary; consider shared normalization helper. |
| 11 | `/equity_curves` vs `/equity_curve` | shared-helper candidate | Both route names exist in `dashboard/app.py` and feed chart surfaces. | Naming suggests duplicate and complicates API discovery. | Audit payload shape next; if equivalent, alias one route and mark canonical. |
| 12 | `ResearchCriteriaBanner` vs research process/criteria docs | overlap-not-duplicate | Banner exposes runtime criteria; docs/process explain research management. | Runtime criteria may not cite governing research rule. | Add doc link or version label, not merge content. |
| 13 | `AIContextPanel` vs `StrategyInspectorTabs`/code viewer | shared-helper candidate | All inspect context, prompts, strategy code and diffs. | Similar code blocks/error states may drift. | Shared code-block/status helpers; keep task-specific layouts. |
| 14 | `ReferenceGallery` vs Hall of Fame screenshot gallery | shared-helper candidate | `chart-hall-of-fame.jsx` owns both gallery-like surfaces. | Duplicate thumbnail/empty-state logic. | Extract thumbnail grid only if future work touches gallery. |
| 15 | `run_log` endpoint vs research campaign run-log artifact rows | shared-helper candidate | `/run_log` gives current run detail; Research Records lists stored run log artifact. | Labels can imply same log freshness. | Add freshness/source badges in later UX pass. |
| 16 | Static `_ALLOWED_DOCS` style docs exposure vs latest update-log growth | obsolete | Research docs endpoint exposes curated docs while update logs and `.omo/evidence` continue expanding. | New research can be invisible unless manually added. | Replace manual allowlist with governed registry or generated index. |
| 17 | `lab.html`/`pro.html`/`verdict.html` standalone pages vs SPA tabs | divergent-by-design | Track Z V4 explicitly validates standalone pages while V3 validates SPA tabs. | Removing standalone pages would break direct URLs/QA harness. | Keep as compatibility surfaces; ensure bundle/cache version stays aligned. |
| 18 | Demo/live empty states across panels | shared-helper candidate | Multiple panels implement their own `Demo mode`, pending, loading, and parse warning blocks. | Inconsistent error color and text makes triage slower. | Centralize small Empty/Error/SourceBadge helpers. |

## Decision Notes

- HoF remains divergent-by-design. Do not collapse `HallOfFamePanel` and `_RpHallOfFame` in the first implementation slice.
- Confirmed current true duplicate candidate is already resolved; the useful work is maintaining the guardrail, not reworking that area.
- Highest-value cleanup is not visual consolidation. It is research information architecture: records, docs, registry, and update logs need a governed index.
