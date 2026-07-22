# Dashboard v5.9 comprehensive UX development report

## 1. Scope and branch

- Feature branch: `feature/dashboard-v5.9-comprehensive-ux`
- Parent branch: `loop/process-research-pipeline`
- Dashboard version: `v5.9.0`
- Boundary: dashboard presentation, read-only research inspection, backtest/replay controls already owned by the dashboard. No broker, live order, V3K gate, protected database, or research-result mutation was added.
- Benchmark: `D:/Chanil_Park/Project/Programming/Newsletter_AI/` was inspected for information hierarchy and dense-list UX. No framework, package, or source was copied.

## 2. Why the previous request was not fully reflected

The earlier Live surface did not own a reusable result-analysis component. It linked to Backtest while Backtest kept its charts in a separate result renderer. That duplication caused three problems:

1. Live could display generation summaries but not the full Backtest evidence stack.
2. Backtest detail, GUI parity, and evolution result panels used different chart heights and grouping rules.
3. Adding a chart to Backtest did not automatically add it to Live or History.

v5.9 fixes the structural cause rather than copying charts again: Live and History now mount the same `BtResultArea` contract used by Backtest, keyed by the selected `run_id` and `gen_no`. A result is shown only when the authoritative run/generation identity exists; an honest pending state is shown otherwise.

## 3. Implemented changes by section

| Section | Before | v5.9 implementation | Primary source |
|---|---|---|---|
| Live strategy | Buy/sell preview was truncated and folded; the full context required extra navigation | Buy/sell code is always visible side by side in a 420–620 px bounded viewport; wrap toggle and copy buy/sell/both actions were added | `panels-config.jsx`, `v4.css` |
| Live governance | Policy, observability, and evidence health were mixed into one dense area | Governance is split into policy/gate, research observability, and evidence health tabs with purpose text | `panels-config.jsx` |
| Live result analysis | Only a Backtest deep-link existed | Shared `BtResultArea` is mounted directly for the current evolution run/generation; the same primary, evidence, and diagnostic charts are available | `v4-research.jsx`, `panels-analysis.jsx` |
| Live layout | User-selectable 2/4-column setting created inconsistent composition | Fixed responsive 12-column stage contract; obsolete column setting removed | `v4-research.jsx`, `v4-settings.jsx`, `v4.css` |
| Research matrix | The integrated heatmap/edge/correlation/stability matrix duplicated analysis and increased density | Removed from the Live scoring/autopsy flow | `panels-analysis.jsx` |
| Backtest result flow | Summary, charts, evidence, parity, and diagnostics were interleaved | Explicit summary → primary → evidence → diagnostics hierarchy | `bt-result-area.jsx` |
| Backtest charts | Card and SVG heights varied | Common 320 px chart contract; holdings strip remains a compact 96 px context band | `bt-equity-charts.jsx`, `bt-gui-parity.jsx`, `chart-backtest-detail.jsx`, `v4.css` |
| GUI parity | Multiple bordered chart boxes had no semantic grouping | Risk, timing, and holding/trade groups with purpose and provenance text | `bt-gui-parity.jsx` |
| MDD/Monte Carlo | MDD random and Monte Carlo evidence was buried in secondary flow | Both are visible in the normal result evidence flow | `bt-gui-parity.jsx`, `bt-result-area.jsx` |
| Backtest library | Hundreds of jobs were rendered into the DOM at once | Initial DOM is capped at 60 rows with explicit incremental “더 보기”; the 360 px scroll viewport remains | `bt-tab-run.jsx` |
| History | Compare/tree required opening, condition details were short, and result charts were separate | Run Compare and condition tree default open; bounded vertical/horizontal scrolling, sticky headers, richer metadata, selected run/generation analysis through shared `BtResultArea` | `v4-history.jsx`, `run-compare.jsx`, `history-condition-tree.jsx`, `research-records-panel.jsx` |
| Reports catalog | Narrow catalog and weak selected-report context | 360–460 px responsive catalog, sticky filters, newest-first ordering, progressive loading, richer provenance/evidence metadata | `v4-reports.jsx`, `v4.css` |
| Report HTML | Basic script-free page with limited hierarchy | Script-free responsive template with executive summary, KPI strip, internal table of contents, dark/light system theme, and print contract | `report_writer.py` |
| Historic research | Separate HTML reports and research documents were difficult to discover together | Reports retains HTML mode and Research Wiki mode; existing historic documents remain source-of-truth and are searchable without inventing reports | `v4-reports.jsx` |
| Hall of Fame | MDD sort treated higher loss as better; metadata was sparse | MDD ascending semantics fixed; rank/direction and existing AI/human performance fields retained in a sticky dense table | `chart-hall-of-fame.jsx` |
| Replay | Availability and time-basis were not explicit; hidden tabs could continue playback | Workflow/availability contract added; market/frame timestamp basis stated; leaving Replay automatically pauses an active stream | `v4-replay.jsx`, `sim-tab-root.jsx` |
| Settings | Obsolete Live column and removed matrix controls remained; reset keys were inaccurate | Obsolete controls removed; only real theme/navigation keys are allowlisted; common layout contract, runtime health, version, and bundle hash are shown | `v4-settings.jsx` |
| Connection startup | A 1.5 s cold-start timeout could incorrectly lock a healthy local server into demo mode | Health, config, and status bootstrap windows increased to 5 s; explicit reconnect remains available | `conn-backend.jsx` |

## 4. Common design contract

| Contract | Value |
|---|---:|
| Layout grid | 12 columns, responsive collapse |
| Main gap | 16 px |
| Card radius | 12 px |
| Standard analytical chart height | 320 px |
| Holdings context strip | 96 px |
| Strategy code viewport | 420–620 px |
| Data-heavy lists | Bounded scroll + sticky headers + progressive DOM limit where required |
| Information order | Summary → primary evidence → diagnostics → details |
| Empty/error states | No fabricated chart; source/pending/error state remains visible |

## 5. Newsletter_AI benchmark decisions

Adopted principles:

- summary-first page hierarchy;
- equal-height cards and consistent gaps;
- bounded lists rather than page-length uncontrolled DOMs;
- master/detail catalog composition;
- explicit loading, empty, stale, and unavailable states.

Rejected approaches:

- introducing another frontend framework or dependency;
- hiding scrollbars on dense research lists;
- copying newsletter-specific components or visual identity;
- replacing STOM safety, provenance, and human-gate contracts with presentation-only success states.

## 6. Verification evidence

| Verification | Result |
|---|---|
| Runtime JSX graph check + production build | PASS: 91 JSX / 539 graph files; Vite and `build-app.mjs` completed |
| Focused v5.9 tests | PASS: 92 tests |
| Dashboard unit suite | 849 tests passed; the only first-pass failure was an intentionally stale committed bundle, then the bundle-sync test passed after rebuild |
| Replay REST | `/sim/health`, `/sim/days`, and `/sim/demo` returned live local data |
| Replay WebSocket | Authenticated `meta → bars → pause → speed → seek_index/history → resume/bars → stop` completed in about 450 ms |
| Replay browser | Selected `322000`, started playback, rendered canvas/SVG and an advancing slider; tab departure changed the control to `재개`, proving automatic pause |
| Browser: Live | v5.9 shell, equal stage layout, side-by-side strategy area and connected state rendered |
| Browser: History | archive summary and richer bounded records table rendered |
| Browser: Reports | catalog, provenance, evidence summary, iframe and TOC rendered; an object-valued metadata crash found during audit was fixed |
| Browser: Hall of Fame | human/AI table, ranking controls and extended performance columns rendered |
| Browser: Settings | obsolete controls absent; common layout and real reset allowlists rendered |

## 7. Section scores after the browser audit

These are implementation-quality scores, not trading-alpha scores.

| Section | Score / 100 | Evidence | Remaining deduction |
|---|---:|---|---|
| Live | 96 | full code, governance split, shared result analysis, consistent layout | result charts require a valid run/generation, by design |
| Backtest | 95 | common result hierarchy, equal charts, parity groups, bounded job list | very large historical libraries still require incremental paging clicks |
| Scoring/autopsy | 94 | duplicate matrix removed, cards normalized, evidence hierarchy clarified | additional domain-specific visualizations should be driven by real new fields, not decorative charts |
| Iteration/performance | 94 | common sizing and evidence hierarchy; Hall fields and sorting improved | no new authoritative AI score fields were fabricated |
| History | 95 | default-open compare/tree, richer tables, shared result charts, bounded scrolling | exceptionally large archives may later need server-side pagination |
| Reports | 94 | wider catalog, provenance, TOC, safe iframe, richer new template | older generated HTML keeps its original template until legitimately regenerated from source records |
| Hall of Fame | 94 | corrected MDD direction and denser human/AI comparison | missing source metrics remain `—` rather than inferred |
| Replay | 96 | actual REST/WS/browser playback and auto-pause verified | full-day ultra-high-speed profiling remains a separate performance study |
| Settings | 95 | obsolete preferences removed; truthful allowlist, health, version and build | intentionally does not expose research/runtime mutation controls |
| Overall | **95** | source, tests, production bundle, API/WS, and browser evidence | no claim of trading-strategy quality improvement |

## 8. Research readiness and next work

Dashboard engineering is no longer a blocker for ordinary research. Research can resume after this feature branch is reviewed and integrated. Recommended sequence:

1. review this branch diff and verification evidence;
2. commit and push the feature branch;
3. open a PR to `loop/process-research-pipeline` and run parent integration checks;
4. merge only after the generated bundle and dashboard unit suite remain green;
5. tag/deploy v5.9 and keep port 8770 as the canonical local dashboard;
6. resume condition research using Live for generation/governance, Backtest for authoritative result analysis, History for replay/compare, and Reports for durable evidence;
7. treat full-day Replay profiling and regeneration of old report HTML as separate evidence-backed maintenance work, not prerequisites for research.

The release does not authorize live trading, broker connection, V3K gates, or protected database changes.

## 9. Independent review closure

The first independent architecture review returned `BLOCK` and the branch was not merged. Every finding was addressed before the PR was updated:

| Review finding | Resolution |
|---|---|
| Superseded Backtest result/Monte Carlo responses could overwrite a newer Live/History selection | Added abort controllers, request sequence and source-key acceptance guards, unmount cleanup, and an executable A→B guard test |
| Metrics-only generation could render zero-filled analysis and lose stored MDD | Added a fail-closed metrics-only summary, `max_drawdown_pct` alias handling, and explicit unavailable chart evidence |
| v5.9 CSS still used an old immutable cache key | Build now hashes normalized `v4.css`, writes the hash to the manifest, updates `v4.html`, and verifies the contract |
| History tree interactions were mouse-only | Research rows, stage/condition toggles, and sortable headers now use focusable buttons, `aria-expanded`/`aria-pressed`, and visible keyboard focus |
| Backtest detail referenced a nonexistent chart-height token | Corrected to `--v59-chart-height` |
| Report catalog was grouped before limiting and therefore not globally newest-first | Preserved the globally date-sorted catalog order and changed the UI label to `최신순 리포트` |
