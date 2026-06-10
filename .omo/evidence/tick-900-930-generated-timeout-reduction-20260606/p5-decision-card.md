# P5 Decision Card - Tick 09:00..09:30 Generated Timeout Reduction

Date: 2026-06-06

## Decision

`BLOCK_LONG_RESEARCH`

Reason: generated strategy creation is currently blocked by LLM provider quota before code exists. Do not run P4 full `09:00..09:30` retry or 2024-2026 broad research until provider availability or a safe offline fallback is resolved.

## Evidence Used

| Evidence | Result |
|---|---|
| P1 timeout autopsy | P7 timeout shape classified `unknown_needs_probe`; split probes needed |
| P2 prompt/guard decision | no-code decision; focused tests passed |
| P3 `09:20..09:25` split | wrapper `ok`, `64.702s`, no wall timeout; gen0 `csv=no`; gen1 blocked by HTTP 429 before code |
| P3 `09:25..09:30` split | wrapper `ok`, `62.052s`, no wall timeout; gen0 `csv=no`; gen1 blocked by HTTP 429 before code |
| Provider preflight | no `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `CODEX_PROXY_BASE_URL`, or `CODEX_PROXY_API_KEY` configured |
| Dashboard health | `200 {"status":"ok","contract_version":2}` |
| Protected paths | clean |

## What This Proves

- The split-probe wrapper and owned-process orchestration worked.
- The immediate blocker changed from backtest runtime timeout to provider availability.
- Current evidence cannot evaluate whether split generated strategies are profitable, fast, or slow.

## What This Does Not Prove

- It does not prove human-level or human-superior performance.
- It does not prove `09:00..09:30` full generated candidates are feasible.
- It does not prove OOS validity.
- It does not justify promotion, export, final approval, live trading, or V3K advancement.

## Next Command

```text
$ulw-plan provider preflight and safe offline candidate fallback plan: use .omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-provider-quota-blocker.md and .omo/plans/tick-900-930-generated-timeout-reduction-20260606.md as primary evidence. Add a research-only preflight for gpt_auth/openrouter/codex_proxy availability, and if no provider is available, plan a Codex-assisted offline candidate-generation path that writes evidence artifacts first and does not touch official engines, hard gates, backtest_graph, protected paths, production export, final_approval, live, or V3K.
```

## Resume Conditions

Resume P3/P4 only when at least one is true:

- `gpt_auth` quota has reset and a provider smoke call succeeds.
- `openrouter` is configured with a valid key and model.
- a local `codex_proxy` is running and passes a provider smoke call.
- a user-approved offline fallback plan exists and preserves all protected-path/export/live/OOS guardrails.
