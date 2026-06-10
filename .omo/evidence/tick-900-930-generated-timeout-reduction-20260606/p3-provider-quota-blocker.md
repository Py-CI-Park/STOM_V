# P3 Provider Quota Blocker - 2026-06-06

## Summary

P3 reached a different blocker than the original `09:00..09:30` warm backtest timeout. Both split probes ended within the wrapper wall cap, but generated strategy creation failed because `gpt_auth` returned HTTP 429 usage limit before candidate code was produced.

## Evidence

| Window | Run ID | Wrapper | Seed gen0 | Generated gen1 | Classification |
|---|---|---|---|---|---|
| `09:20..09:25` | `tick_p3_split_0920_0925_20260606` | `ok`, `64.702s`, timeout `false` | `csv=no`, no metrics | HTTP 429 usage limit before code | `provider_auth_limit_no_generated` |
| `09:25..09:30` | `tick_p3_split_0925_0930_20260606` | `ok`, `62.052s`, timeout `false` | `csv=no`, no metrics | HTTP 429 usage limit before code | `provider_auth_limit_no_generated` |

`gpt_auth` stderr reports:

```text
usage_limit_reached, plan_type=pro, resets_at=1781138513
```

Local reset time from `datetime.fromtimestamp(1781138513)`:

```text
2026-06-11T09:41:53
```

Environment preflight for alternate providers returned:

```text
{'OPENROUTER_API_KEY': False, 'OPENAI_API_KEY': False, 'CODEX_PROXY_BASE_URL': False, 'CODEX_PROXY_API_KEY': False}
```

Supported repo providers are `gpt_auth`, `openrouter`, and `codex_proxy`. No alternate provider is currently configured in this shell.

## Current Decision

Do not run P4 full `09:00..09:30` retry now. It would likely reproduce the same provider quota failure before generating code, and would not answer the original timeout question.

## Next Unlock Options

1. Wait until the `gpt_auth` reset time, then rerun P3/P4.
2. Configure `OPENROUTER_API_KEY` or a local `codex_proxy` and rerun P3 with an explicit research-only provider config.
3. Create a follow-up plan for provider preflight and a safe Codex-assisted offline candidate-generation path that writes evidence artifacts first and does not touch protected DB/export/live paths without explicit approval.

## Claim Boundary

No human-level, seed-superior, OOS, or promotion claim is supported by P3. The current evidence proves only that split-probe orchestration works and that generated strategy evaluation is blocked by provider quota.
