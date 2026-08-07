# Task 1 Evidence Inventory

Scope: review-only snapshot for tick late 09:20~09:25 and min 09:00~15:00 condition generation readiness. No source, test, runtime DB, or roadmap document was edited.

| path | type | proves | does_not_prove | confidence |
|---|---|---|---|---|
| `docs/AGENT_HANDOFF.md` | handoff/design doc | Historical AI loop infrastructure direction, tick 09:00~09:30 boundary, min 09:00~15:19 boundary, T0-T4 completion, and explicit warning that toggle-on multiyear/OOS was not complete at that point. | Does not prove current late-tick or min-full profitable discovery. | medium |
| `docs/update_log/2026-06-13_dawn_handoff.md` | handoff/roadmap | THETA is the current usable champion; V6 user decision remains; R2R3_B is HOLD, not promoted. | Does not prove new tick 09:20~09:25 or min 09:00~15:00 generation success. | high |
| `docs/update_log/2026-06-13_late_tick_min_discovery_roadmap.md` | roadmap | Desired next direction: tick late niche separated from seed, min full-session split by time block. | Its example `tmap_sweep` commands use `--out-prefix`, which current CLI does not accept. | high |
| `docs/research/condition_research/2026-06-13_entry_extension_and_min_roadmap.md` | roadmap/design doc | T-track order T1-T4 and M-track order M1-M4; M1 primitive map is the missing min starting point. | Does not prove M1 exists or min profitable conditions are discovered. | high |
| `docs/research/condition_research/2026-06-12_min_timeframe_validation_protocol.md` | protocol/design doc | Min data window is about 11 months, 2025-04-07 through 2026-02-27; fixed OOS is structurally limited to 2026-01~02. | Does not provide a full multi-year min OOS proof. | high |
| `ai_strategy_loop/scripts/research_presets.py` | code/config contract | Tick late and min full-session presets exist; preset writing is explicit and does not touch runtime state unless invoked with an output path. | Does not prove generated strategy quality or sweep success. | high |
| `ai_strategy_loop/tmap/templates/tick_late_0920_0925_continuation.json` | template | A tick TMAP template exists with default `entry_start=92000`, `entry_end=92500`, and forced exit by 09:30. | Does not prove profitable 09:20~09:25 discovery. | high |
| `ai_strategy_loop/tmap/templates/min_session_0900_1500_rotation.json` | template | A min TMAP template exists with 09:00~15:00 entry span and 15:00 force exit. | Does not prove all time bands are profitable or adequately sampled. | high |
| `tests/unit/test_late_tick_and_min_templates.py` | unit test | Tick/min templates render and validate against timeframe-specific variable scope. | Does not run real backtests or discover profitable candidates. | high |
| `tests/unit/test_research_presets.py` | unit test | Preset contracts for tick late and min full-session are stable. | Does not exercise LLM generation or TMAP sweeps. | high |
| `tests/unit/test_warm_session_window.py` | unit test | Min `full_session_enabled` opens warm config to `bt_min_universe_end_time`; tick ignores full session. | Does not prove data quality, strategy quality, or OOS robustness. | high |
| `tests/unit/test_time_cap_bucket_generation.py` | unit test | Time-cap prompt/config wiring covers 09:20~09:30 and `_generate_pair` forwarding. | Does not prove LLM follows the prompt or produces profitable code. | high |
| `.omo/evidence/tmap-walkforward/t2_corner_log.txt` | runtime log | Tick-side T2C train batch produced positive/gate-true candidates; THETA baseline remained strong. | Does not isolate exact 09:20~09:25 profitability or prove OOS robustness by itself. | medium |
| `.omo/evidence/tmap-walkforward/t2c3_placebo_log.txt` | runtime log | Placebo variants overfire and fail badly, supporting the need for controlled late-tick structure. | Does not prove the selected late-tick structure is production ready. | medium |
| `.omo/evidence/tmap-walkforward/wf_t2c3_20260613/*` | partial/structured run outputs | Four window manifests/pairs exist under the run directory. | The expected in-directory `aggregate.json` is absent, so the directory is not self-contained. | medium |
| `.omo/evidence/tmap-walkforward/wf_t2c3_aggregate.json` | runtime aggregate | A sibling aggregate exists with 4 windows, all `status=ok`, policy total 9,882,323 vs baseline 8,933,830. | Non-canonical sibling location creates runbook/evidence-path ambiguity; still not proof of LLM generation quality. | medium |
| `.omo/evidence/tmap-walkforward/min_e2e_smoke_log.txt` | runtime log | Min backtest engine chain can prepare and run a min candidate. | It is negative profit (-64,197) and gate false; it is not strategy-success evidence. | high |
| `.omo/evidence/tmap-walkforward/m2_smoke_log.txt` | runtime log | M2 min smoke prepares and executes. | It is negative profit (-803,805) and gate false; it argues against current min strategy success. | high |
| `.omo/evidence/tmap-walkforward/llm_context_failure_lessons.md` | research memory | Lists rejected LLM/min/tick families and live clues such as prev_ratio, exit2 2022 regime, F07 extreme burst, and underexplored min late session. | Does not itself generate or validate a new candidate. | high |
| `.omo/evidence/tmap-walkforward/r1_ablation_findings.md` | research findings | THETA champion evidence, R2R3_B HOLD, and remaining LLM/v2-gate work are documented. | Does not close the new tick late/min full-session roadmap. | high |

## Evidence Strength Summary

- Infrastructure proof is strong: config fields, presets, templates, validation, variable scope, and warm-window tests are present.
- Tick TMAP proof is moderate: T2C/T2C3 have positive train and sibling WF aggregate evidence, but exact 09:20~09:25 discovery is not yet isolated from broader extension structures.
- Tick LLM proof is weaker: prompt wiring exists, but no current successful LLM candidate batch proves the late niche.
- Min proof is mostly infrastructure-only: smoke logs show the min chain runs, but current min candidates are negative.
- OOS/WF proof is uneven: THETA and T2C3 have useful evidence, but min full-session and LLM generation remain pending.

