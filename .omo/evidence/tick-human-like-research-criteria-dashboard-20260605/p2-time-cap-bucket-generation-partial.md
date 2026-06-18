# P2 Time-Bucket x Market-Cap Generation - Partial Evidence

## Verdict

Status: implementation-ready, not page-complete.

P2 code and prompt plumbing now supports default-OFF `time_cap_bucket_generation_enabled`
with a configurable `time_cap_bucket_end_time`.

This is not marked complete because the plan acceptance still requires a bounded
`09:00..09:20` preflight that produces real CSV+metrics before expanding to
`09:30`.

## Implemented

- Added `ai_strategy_loop/brain/time_cap_bucket.py`.
- Added `LoopConfig.time_cap_bucket_generation_enabled = False`.
- Added `LoopConfig.time_cap_bucket_end_time = 92000`.
- Wired config validation through `config_from_dict`.
- Wired `/config/spec` dashboard settings fields.
- Wired `build_messages -> generate_strategy -> _generate_pair`.
- Wired prompt logging `injected_features`.
- Wired `active_config` dashboard state.
- Added `tests/unit/test_time_cap_bucket_generation.py`.

## Behavior

- OFF path remains byte-identical for buy and sell prompts.
- ON buy prompt includes:
  - `09:00~09:05`
  - `09:05~09:10`
  - `09:10~09:15`
  - `09:15~09:20`
  - market-cap bands: small / mid / large
  - small branch / C_T timeout avoidance guidance
- `time_cap_bucket_end_time=93000` adds:
  - `09:20~09:25`
  - `09:25~09:30`
- Sell prompt is unaffected.

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_time_cap_bucket_generation.py -q
# 8 passed

$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_time_cap_bucket_generation.py tests/unit/test_classification_generation.py tests/unit/test_time_window.py tests/unit/test_sparse_positive_prompt.py tests/unit/test_prompt_logging.py -q
# 61 passed

$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_launch_config.py tests/unit/test_state_contract.py -q
# 45 passed

$env:PYTHONUTF8='1'; python C:/Users/parkc/.codex/skills/programming/scripts/python/check-no-excuse-rules.py ai_strategy_loop/brain/time_cap_bucket.py tests/unit/test_time_cap_bucket_generation.py
# no violations in 2 file(s)

python scripts/verify_nonrelease_sync.py
# pass

git diff --check
# pass; line-ending warnings only
```

## Dashboard

- Restarted dashboard by targeted port owner PID only:
  - stopped: `98272`
  - started: `125024`
- `http://127.0.0.1:8770/health`: `{"status":"ok","contract_version":2}`
- `http://127.0.0.1:8770/ui/`: `200`
- `http://127.0.0.1:8770/config/spec` exposes:
  - `time_cap_bucket_generation_enabled`
  - `time_cap_bucket_end_time`

## Not Yet Done

- No real bounded `09:00..09:20` backtest CSV was produced in this page.
- No trading performance, human-level, seed-superior, or production-readiness claim is made.
- Next page should run a safe bounded preflight using this toggle before P2 can be checked.
