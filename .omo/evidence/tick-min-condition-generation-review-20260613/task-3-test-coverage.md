# Task 3 Test Coverage and Meaning Audit

Command executed:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/unit/test_warm_session_window.py tests/unit/test_variable_scope.py tests/unit/test_time_window.py tests/unit/test_time_cap_bucket_generation.py tests/unit/test_late_tick_and_min_templates.py tests/unit/test_research_presets.py -q -p no:cacheprovider
```

Result: `68 passed in 13.91s`.

## What The Tests Prove

- `test_warm_session_window.py`: min + full session opens the warm backtest end time to `bt_min_universe_end_time`; tick does not inherit min full-session behavior.
- `test_variable_scope.py`: timeframe variable scope separation catches invalid tick/min variable usage.
- `test_time_window.py`: no-op or overwide time windows are detected, while meaningful narrow windows such as 09:02 are protected.
- `test_time_cap_bucket_generation.py`: time-cap config defaults are off, 09:20~09:30 prompt injection works, complexity guard blocks oversized candidates, and `_generate_pair` forwards time-cap config.
- `test_late_tick_and_min_templates.py`: tick late and min full-session templates render and validate across coordinate points.
- `test_research_presets.py`: tick late and min full-session presets are stable and serializable.

## What The Tests Do Not Prove

- They do not prove that the LLM follows the late-tick or min full-session prompt.
- They do not prove that generated candidates are profitable.
- They do not prove 2022/2026 OOS robustness or 4-window WF stability.
- They do not prove dashboard verdict completion, V6 approval, live deployment, or strategy promotion.
- They do not prove min 09:00~15:00 time-band edge; existing min smoke logs are negative.

Explicit non-proof checklist:

- Contract tests pass, but this does not prove LLM quality.
- Template validation passes, but this does not prove profitable candidate generation.
- Warm-window tests pass, but this does not prove OOS robustness.
- Preset tests pass, but this does not prove dashboard verdict completion.
- Min template tests pass, but this does not prove full-day min edge.

## Missing Future Tests

- A CLI contract test that fails if roadmap examples use unsupported `tmap_sweep` flags such as `--out-prefix`.
- A min full-session prompt test proving the LLM receives explicit 09:00~15:00 band instructions.
- A TMAP manifest-path test requiring aggregate output to land in a canonical location.
- A small deterministic min primitive-map test covering all planned M1 time bands.
- A late-tick report test separating THETA baseline evidence from new 09:20~09:25 discovery evidence.
