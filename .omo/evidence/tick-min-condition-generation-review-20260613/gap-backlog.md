# Gap Backlog

## 1. Command Contract Fix

priority: P0
why: Current roadmap examples use unsupported `--out-prefix`; future workers will fail before any sweep.
files likely touched: `docs/update_log/2026-06-13_late_tick_min_discovery_roadmap.md`, possibly a CLI contract test.
tests to add/run: `python -m ai_strategy_loop.scripts.tmap_sweep --help`; new unit test for documented command flags if docs tooling exists.
acceptance: tick/min examples use `--run-id` and `--manifest-out`; no `--out-prefix` remains in executable examples.

## 2. Canonical Evidence Path Contract

priority: P0
why: T2C3 aggregate exists as a sibling file, while the run directory lacks `aggregate.json`.
files likely touched: WF helper scripts or runbook generator under `ai_strategy_loop/scripts/` and evidence runbook docs.
tests to add/run: JSON parse test for aggregate output; path existence check for run directory aggregate.
acceptance: every WF run writes a canonical aggregate path and records it in the manifest.

## 3. Tick Late 2-Quarter Smoke

priority: P1
why: Exact 09:20~09:25 template needs bounded runtime proof before full sweep.
files likely touched: `.omo/evidence/.../configs/` only for first smoke; no source needed unless CLI issues appear.
tests to add/run: bounded `tmap_sweep` smoke on two separated quarters; targeted unit tests after any source fix.
acceptance: both quarters return bounded results with trade counts, profit, MDD, and gate reason; no promotion claim.

## 4. Min M1 Primitive Map

priority: P1
why: Full-session min generation lacks evidence about which signal works at which time.
files likely touched: new TMAP template or script under `ai_strategy_loop/tmap/` or `ai_strategy_loop/scripts/`; tests under `tests/unit/`.
tests to add/run: primitive render validation; bounded M1 batch across 6 primitives x time bands.
acceptance: 36 cells produce manifest rows with density/profit/MDD and band labels.

## 5. Min Full-Session Prompt Guidance

priority: P1
why: Current prompt guidance still speaks mainly in opening-session terms.
files likely touched: `ai_strategy_loop/brain/prompt.py`, maybe `ai_strategy_loop/config.py`.
tests to add/run: prompt snapshot/unit test proving 09:00~15:00 band guidance appears only for min full-session.
acceptance: min full-session LLM prompt names all required time bands and does not pollute tick prompt behavior.

## 6. Late-Tick LLM Context Injection

priority: P2
why: LLM should receive T2C3, placebo, and failure lessons before second batch.
files likely touched: prompt context builder, lesson ingestion code, or evidence context pack.
tests to add/run: unit test for context pack inclusion and token-bounded summary.
acceptance: generated prompt contains THETA separation, late-window lessons, and rejected-family warnings.

## 7. Min OOS Protocol Guard

priority: P2
why: Min has only about 11 months of data and fixed OOS is limited to 2026-01~02.
files likely touched: validation protocol/runbook helper, maybe config validator.
tests to add/run: config validation test preventing contaminated OOS reuse.
acceptance: min freeze/OOS commands require train period disclosure and OOS-use count.

## 8. Promotion-Gate Report

priority: P2
why: Gate pass, train profit, OOS, WF, and dashboard verdict must not be conflated.
files likely touched: dashboard/report code if promotion workflow is implemented later.
tests to add/run: report rendering tests and no-overclaim text checks.
acceptance: each candidate report separates train, smoke, OOS, WF, and verdict state.

## 9. Full-Day Min Band Feedback Loop

priority: P3
why: After M1, the LLM needs band-specific feedback instead of a generic min prompt.
files likely touched: feedback summarizer, prompt builder, possibly `segment_feedback.py`.
tests to add/run: feedback construction test with synthetic M1 cell results.
acceptance: prompt contains top/bottom bands and avoids repeating rejected min families.

## 10. Freeze and OOS Automation

priority: P3
why: Only predeclared frozen candidates should consume OOS/WF budget.
files likely touched: OOS/WF helper scripts and manifest schema.
tests to add/run: freeze manifest validation, aggregate parse, and no-OOS-before-freeze guard.
acceptance: OOS command refuses non-frozen candidates and writes a canonical aggregate.

