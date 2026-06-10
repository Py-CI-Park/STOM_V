# Required Future Report Template

Use this format after every page, bounded run, or major checkpoint.

## 1. Master Roadmap Progress

| Stage | Status | Progress | Current Evidence | Blocker / Next Unlock |
|---|---|---:|---|---|
| M0 Canonical safety baseline |  |  |  |  |
| M1 Governance |  |  |  |  |
| M2 Dashboard/process visibility |  |  |  |  |
| M3 Generation families |  |  |  |  |
| M4 Bounded backtest preflight |  |  |  |  |
| M5 Quant analysis |  |  |  |  |
| M6 Feedback/wiki loop |  |  |  |  |
| M7 Recent-weighted research |  |  |  |  |
| M8 Strict promotion validation |  |  |  |  |
| M9 Wiki/knowledge base |  |  |  |  |
| M10 Human comparison |  |  |  |  |
| M11 Operating loop |  |  |  |  |

## 2. Current Page Progress

| Page / Plan | Step | Status | Evidence | Next |
|---|---|---|---|---|
|  |  |  |  |  |

## 3. Dashboard Visibility

| Panel | Status | Browser/API Evidence | Remaining Gap |
|---|---|---|---|
| Engine status/progress/logs |  |  |  |
| Strategy inspector code/diff |  |  |  |
| Prompt timeline / AI Context Pack |  |  |  |
| Fitness/equity chart |  |  |  |
| Hall of Fame |  |  |  |
| Research Wiki |  |  |  |
| Analysis heatmaps |  |  |  |
| Run Compare |  |  |  |

## 4. Performance Status

Always separate infrastructure from candidate proof.

| Layer | Current Result | Evidence | Claim Level |
|---|---|---|---|
| Infrastructure |  |  | can claim only tooling progress |
| Research candidate |  |  | research-only unless strict validation passes |
| Strict promotion |  |  | human-level/production claim only after all gates |

Minimum metrics:

| Metric | Value |
|---|---|
| Run ID |  |
| Period / years |  |
| Timeframe |  |
| Time window |  |
| Market-cap bands |  |
| OOS mode |  |
| Total profit |  |
| Total return |  |
| MDD |  |
| Trade count |  |
| Max/current holdings |  |
| Win-day ratio |  |
| Payoff |  |
| Recent-weighted score |  |
| 2024 split |  |
| 2025 split |  |
| available 2026 split |  |
| Fixed 2022/2026 OOS |  |
| Seed/human-reference comparison |  |

## 5. Evidence

| Evidence Type | Path / Command | Result |
|---|---|---|
| HTTP/API |  |  |
| Browser screenshot/DOM |  |  |
| Unit tests |  |  |
| `git diff --check` |  |  |
| `python scripts/verify_nonrelease_sync.py` |  |  |
| Protected-path status |  |  |
| Cleanup receipt |  |  |

## 6. Risk Register

| Risk | Current Severity | Evidence | Mitigation |
|---|---|---|---|
| Overfit / OOS collapse |  |  |  |
| Trade count too small |  |  |  |
| Generated strategy timeout |  |  |  |
| Token/prompt bloat |  |  |  |
| Condition complexity bloat |  |  |  |
| Protected-path/runtime safety |  |  |  |
| Misleading dashboard success |  |  |  |

## 7. Next Recommended Command

```text
$ulw-plan <or $start-work> ...
```

Required explanation:

- Why this command is next.
- What it should prove or unlock.
- What must not be claimed yet.
- Which guardrails must remain unchanged.

## Current Recommended Command

```text
$ulw-plan tick 09:00~09:30 generated strategy timeout reduction plan: use .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-bounded-research-run-sequence.md and p7-timecap-900-930-result.stdout.txt as primary evidence. Reduce generated buy/sell complexity or split 09:20~09:30 into smaller bounded probes before retrying multi-year research. Preserve official engines, hard gates, backtest_graph, protected paths, final_approval/export_winner/live/V3K guardrails.
```

Do not claim human-level, seed-superior, or production-ready performance before a frozen candidate passes strict fixed validation.
