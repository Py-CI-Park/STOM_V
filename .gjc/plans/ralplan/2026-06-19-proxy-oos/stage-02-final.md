# RALPLAN Final Pending Approval: STOM 단일 proxy 조건식 공식 OOS 연구

Status: **PENDING APPROVAL — no execution authorized**
Generated: 2026-06-19
Source spec: `.gjc/specs/deep-interview-condition-proxy-official-oos.md`
Consensus artifacts:
- Planner: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-01-planner.md`
- Architect pass 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-01-architect.md`
- Critic pass 1: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-01-critic.md` — ITERATE
- Revision pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-02-revision.md`
- Architect pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-02-architect.md` — APPROVE, WATCH only
- Critic pass 2: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-02-critic.md` — OKAY

## ADR

### Decision

Adopt the revised planning path: **Option C + Option D**.

- Design up to 3 single STOM proxy buy/sell condition pairs derived from `r8_exclude_cap_lt_1500`.
- Candidate slate: 1 entry-pure proxy plus 2 exit-behavior proxies that approximate exit2/r2full properties without CSV switching or prior-month strategy PnL state.
- Validate each candidate with official OOS only after explicit execution approval.
- Use a proxy-oos-specific wrapper/config and pinned evidence run directory before any OOS.
- Compare results against the official r8 baseline and the combined portfolio/CSV simulation, then produce a `pass`, `defer`, `reject`, or `evidence_blocker` decision card.
- Do not execute fallback condition-set/operational-rule research in this scope; if all 3 fail, write a failure/reject card and defer fallback to a separate follow-up.

### Drivers

1. The user's true goal is a real STOM condition expression or executable condition pair, not a CSV portfolio switch.
2. Official OOS baseline must improve over `r8_exclude_cap_lt_1500`: profit > 7,292,861원, MDD <= 19.09%, all gates pass.
3. Robustness must be demonstrable: trades >= 132, at least 4 positive periods, Q4 > 0, and top-trade concentration below thresholds.
4. Evidence must be run-owned and isolated from operating DBs, baseline evidence, live/export, and V3K/KHOPENAPI paths.
5. Combined portfolio results remain a comparison target, not official buy/sell OOS evidence.

### Alternatives considered

| Option | Verdict | Reason |
|---|---|---|
| Entry-only r8 proxy variants | Viable but incomplete | Highest reproducibility, but may miss the exit/r2full behavior driving combined performance. |
| Exit-behavior proxy pair only | Viable but risky | Targets the performance gap but increases overfit and unsupported-state risk. |
| Balanced 3-candidate slate | Chosen | Best balance under the user's max-3-candidate constraint. |
| Proxy-specific wrapper/config | Chosen | Cleanest evidence isolation and path ownership. |
| Existing hardcoded wrapper as run-owned sandbox | Fallback only | Acceptable only with unique run IDs, collision checks, cleanup records, and explicit run ownership. |
| Direct combined CSV/portfolio switching | Rejected | Not a single official STOM buy/sell condition path and not suitable as the requested live-candidate condition expression. |

### Consequences

- Execution requires a separate approval before any condition generation, wrapper creation, OOS run, or evidence artifact mutation.
- The plan may conclude `reject` even if combined CSV performance is strong, because the goal is official single proxy condition OOS.
- A successful `pass` candidate still does not authorize live/export/strategy DB mutation.
- Fallback condition-set/operational-rule research remains a separate future plan, not hidden continuation.

### Follow-ups

- If approved and all 3 proxy candidates fail, create a separate ralplan/deep-interview brief for condition-set + operational-rule research.
- If any candidate passes, run a separate promotion/export readiness plan before touching live/export/operating DB surfaces.

## Principles

1. **Evidence taxonomy first**: 공식 OOS, proxy run evidence, baseline evidence, and combined portfolio/CSV 재분석 stay separately labeled.
2. **Run-owned isolation**: all proxy OOS mutable artifacts must be under a pinned run-owned evidence directory or explicitly run-owned wrapper sandbox.
3. **Single proxy constraint**: no CSV switching, no prior-month strategy PnL state inside the condition expression.
4. **Mandatory robustness gates**: profit, MDD, gates, trades, period spread, Q4, and top-trade concentration all matter.
5. **No silent promotion**: pass/defer/reject card only; no live/export/operating DB mutation.

## Baselines to freeze before execution

| Baseline | Value | Evidence type |
|---|---:|---|
| Official r8 profit | 7,292,861원 | 공식 OOS |
| Official r8 max MDD | 19.09% | 공식 OOS |
| Official r8 trades | 263 | 공식 OOS |
| Official r8 Q4 profit | 310,886원 | 공식 OOS |
| Combined portfolio profit | 39,402,438원 | 포트폴리오 시뮬레이션/CSV 재분석 |
| Combined portfolio MDD | 7.6823% | 포트폴리오 시뮬레이션/CSV 재분석 |
| Combined Q4 profit | 952,502원 | 포트폴리오 시뮬레이션/CSV 재분석 |

2026 evidence remains YTD through 2026-02-28, not full-year 2026.

## Approved execution scope after separate approval

1. **Preflight / run ownership**
   - Pin run root: `.omo/evidence/tmap-walkforward/proxy-oos-<YYYYMMDD>/`.
   - Prefer creating/using proxy-oos-specific wrapper/config.
   - Verify all mutable paths before OOS: strategy sqlite, loop runs sqlite, snapshots, current state, stop flag, logs, summaries/cards, CSV reference capture.
   - Stop if any mutable path targets operating DBs, baseline evidence, live/export/V3K/KHOPENAPI paths, or existing baseline snapshots/logs.

2. **Candidate design**
   - Candidate P1: entry-pure r8 low-cap/liquidity/momentum proxy.
   - Candidate P2: defensive exit proxy approximating exit2 drawdown containment.
   - Candidate P3: trend/volatility exit proxy approximating r2full participation.
   - Each candidate must document code, intent, supported STOM variables, and leakage review.

3. **Official OOS sequence**
   - Q4 stress first.
   - Then 2022, 2023, 2024, 2025, and 2026 YTD.
   - Stop on non-zero runner exit, unsupported syntax, path collision, or guardrail violation.

4. **Metric extraction**
   - Aggregate profit, max MDD, gate status, trades, daily average trades, per-period profit, Q4 profit.
   - Mandatory top-trade concentration from official trade CSV/equivalent detail.
   - CSV/log/snapshot/run DB references must reconcile.

5. **Comparison and decision**
   - Compare each candidate to official r8 baseline and combined portfolio target.
   - Assign `pass`, `defer`, `reject`, or `evidence_blocker`.
   - If all candidates fail, write failure card and defer fallback research.

## Pass / defer / reject gates

### Pass requires all of the following

- Profit > 7,292,861원.
- Max MDD <= 19.09%.
- All official OOS gates passed.
- Trades >= 132.
- At least 4 positive periods across 2022, 2023, 2024, 2025, and 2026 YTD.
- Q4 profit > 0.
- `top1_abs_share <= 0.20`.
- `top5_abs_share <= 0.50`.
- Official trade-detail/CSV evidence reconciles to summaries.
- No unsupported STOM syntax, future/result leakage, CSV selection state, or prior-month strategy PnL state.

### Defer / evidence blocker

Use `defer` or `evidence_blocker`, never `pass`, when:

- official CSV/trade-detail evidence is missing, malformed, or cannot be reconciled;
- concentration metrics cannot be computed;
- path ownership is ambiguous but no source/operating surface was touched;
- a candidate is promising but needs separate fallback/operational-rule research.

### Reject

Use `reject` when:

- metric gates fail;
- OOS gate fails;
- trades < 132;
- Q4 is nonpositive;
- concentration is too high and other weaknesses exist;
- unsupported syntax/leakage is present;
- mutable paths target forbidden surfaces.

## Top-trade concentration rule

Required evidence: official per-trade CSV or equivalent trade-detail evidence for every candidate/period used in aggregate.

Metrics:

```text
top1_abs_share = abs(largest_trade_profit_krw) / sum(abs(trade_profit_krw))
top5_abs_share = sum(abs(top_5_trade_profit_krw_by_abs_value)) / sum(abs(trade_profit_krw))
top5_net_share = sum(top_5_trade_profit_krw_by_abs_value) / total_profit_krw  # when total_profit_krw > 0
```

Pass thresholds:

- `top1_abs_share <= 0.20`
- `top5_abs_share <= 0.50`

Missing or unreconciled trade-detail evidence blocks pass.

## Verification plan after approval

- Parse preflight JSON and verify pinned run root / wrapper mutable paths.
- Verify no mutable path points to `ai_strategy_loop/state/loop_strategies.db`, `ai_strategy_loop/state/loop_runs.db`, `_database/`, operating `*.db`, baseline evidence, live/export/V3K/KHOPENAPI paths.
- Review candidate code against `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt` for STOM variable support and leakage boundaries.
- Reconcile loop run DB rows, snapshots, logs, CSV paths, and summary JSON for every candidate/period.
- Compute top-trade concentration and period spread.
- Verify comparison arithmetic against frozen baselines.
- Verify post-run cleanup and protected runtime path status.

## Pending approval boundary

This plan is **not execution approval**. Before explicit approval, do not:

- generate or mutate candidate condition files;
- create wrapper/config artifacts;
- run official OOS;
- touch live/export/operating DB/V3K/KHOPENAPI paths;
- commit, push, or open PRs.

Recommended execution path after approval: `/skill:ultragoal` with this pending-approval plan.
