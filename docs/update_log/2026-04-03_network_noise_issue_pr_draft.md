# 2026-04-03 Network Noise Handling Issue And PR Draft

## GitHub Issue Draft

### Title

`Network failures in webcrawling and telegram polling flood console with tracebacks`

### Body

```markdown
## Summary

When external network requests fail in `utility/webcrawling.py` or `utility/telegram_bot.py`, STOM currently emits long traceback noise to the console even though core workflows such as backtests may have completed successfully.

This makes normal transient outages from Binance, Naver Finance, DNS resolution, or Telegram polling look like internal program failures.

## Problem

- `utility/webcrawling.py`
  - `get_korean_stocks`
  - `get_market_indicator`
  - `get_crypto_data`
- `utility/telegram_bot.py`
  - `start_bot`
  - `restart_bot`

These paths currently surface transient network failures as traceback-heavy logs instead of concise operational warnings.

## Desired behavior

- Keep existing data on transient fetch failures
- Emit one-line throttled warnings instead of traceback floods
- Clear warning state after recovery
- Use operator-facing Korean warning contexts for telegram bot start/restart
- Preserve existing runtime/queue structure in downstream worktrees

## Scope

Official fix branch first:
- `utility/webcrawling.py`
- `utility/telegram_bot.py`

Then propagate to:
- `STOM_Version_2U`
- `STOM_Version_2U_C`
- `STOM_V.wt-dev`
- `research/init`

## Non-goals

- Bootstrap/statistics fixes
- Backtest engine logic changes
- Full external request architecture redesign
```

## GitHub PR Draft

### Title

`fix: reduce webcrawling and telegram network traceback noise`

### Body

```markdown
## Summary

- reduce `webcrawling.py` network failure traceback noise to throttled one-line warnings
- preserve previous home-tab data when transient network requests fail
- reduce telegram bot startup/restart transient network failures to operator-facing one-line warnings
- add focused regression tests for webcrawling and telegram network-noise handling

## Details

### Webcrawling

- added warning-throttling helpers for transient network failures
- kept existing home-tab data on failure for:
  - `get_korean_stocks`
  - `get_market_indicator`
  - `get_crypto_data`
- added recovery behavior that clears warning state after success

### Telegram bot

- added transient network failure classification
- routed `start_bot` and `restart_bot` failures through operator-facing warning paths
- added focused async regressions for startup and restart failure handling

## Verification

- `python -m pytest tests/unit/test_webcrawling_network_noise.py tests/unit/test_telegram_network_noise.py -q`
- `python -m py_compile utility/webcrawling.py utility/telegram_bot.py`

## Downstream propagation

Validated policy propagation in:

| Workspace | Status |
| --- | --- |
| `STOM_Version_2U` | verified |
| `STOM_Version_2U_C` | verified |
| `STOM_V.wt-dev` | verified |
| `research/init` | verified |
```
