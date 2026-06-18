# Branch Attribution And AND/OR Contribution Plan

Generated: 2026-06-18T23:19:07+09:00  
Plan page: 14  
Status: analysis design only. No generator syntax, official engine, or backtest runtime was changed.

## Problem

The system can generate broad condition structures, but the research notes show a gap: literal OR appears in 38/149 templates, if/elif branches appear in 121/149 templates, and the actual branch contribution to profit, MDD reduction, and OOS stability is not measured. The next research loop needs branch-level evidence so the seed bank learns which branches help and which branches create overfit or dead trades.

## Attribution Dimensions

| Dimension | Definition | Example signal | Why it matters |
|---|---|---|---|
| literal OR | A condition that explicitly joins alternatives with OR. | `A or B` style expression. | Measures whether direct alternative logic improves coverage or adds noisy trades. |
| if/elif | Procedural branch path selected before generating buy/sell condition. | `if open_bucket`, `elif mid_bucket`. | Current generated corpus uses this heavily; branch lift must be measured. |
| time bucket | Session/time group that activates a branch. | open, morning, midday, afternoon, close. | Tick research is still open-heavy; time generalization must be visible. |
| cap bucket | Market-cap/liquidity branch group. | small, mid, upper-mid, large; `cap_lt_1500`. | Q4 defense candidates depend on cap filtering. |
| sell branch | Exit branch or defensive sell rule path. | `exit2_skip_after_prior_exit2_loss_500k_else_full`. | Buy-side lift is incomplete without exit-rule attribution. |
| fallback branch | Default branch when no specialized path fires. | `else_full`, `else_off`. | Detects whether a complex strategy is mostly using its fallback. |

## Proposed Data Model

| Field | Type | Required | Notes |
|---|---|---:|---|
| `run_id` | string | yes | Official or research run id. |
| `candidate_id` | string | yes | Canonical machine name from registry. |
| `display_alias` | string | yes | Human-readable Korean alias. |
| `branch_id` | string | yes | Stable branch identifier, e.g. `buy.open.smallcap.or_1`, `sell.exit2.loss_skip`. |
| `branch_kind` | enum | yes | `literal_or`, `if_elif`, `time`, `cap`, `sell`, `fallback`. |
| `branch_condition` | string | yes | Normalized expression or selected rule label. |
| `trade_id` | string | yes | Stable trade row key from official result. |
| `entry_ts` / `exit_ts` | datetime | yes | Needed for time-bucket attribution. |
| `profit_krw` | number | yes | Branch-level P/L. |
| `mdd_contribution` | number | later | Approximate drawdown attribution; define from equity curve segment. |
| `oos_period` | string | yes | Distinguish train, validation, official OOS periods. |
| `is_shadow` | bool | yes | Calendar/month and other suspicious candidates stay shadow. |

## Instrumentation Choices

1. **Non-invasive first pass**: parse generated templates and candidate metadata to assign static branch ids without changing the official engine.
2. **CSV/result join pass**: join official backtest rows to branch ids using candidate label, time bucket, cap bucket, and sell rule labels.
3. **Future engine annotation**: only after tests exist, add optional branch tag emission around candidate evaluation. This must be default-off and must not alter official engine behavior.
4. **Dashboard summarization**: aggregate by branch id into trade count, profit, MDD segment, win rate, OOS pass/fail, and lift versus candidate baseline.

## Metrics

| Metric | Purpose |
|---|---|
| `branch_trade_count` | Detect dead branches and over-narrow branches. |
| `branch_profit_krw` | Identify branches that drive total profit. |
| `branch_mdd_delta` | Identify branches that reduce or increase drawdown. |
| `branch_oos_lift` | Compare OOS performance with/without branch or against baseline seed. |
| `branch_stability` | Count periods where branch remains positive. |
| `fallback_ratio` | Detect strategies whose special branches rarely fire. |
| `sell_branch_loss_saved` | Estimate defense contribution from exit/sell branch. |

## Dashboard View

Add a future dashboard view after data exists:

| Panel | Content |
|---|---|
| Branch contribution table | `branch_id`, alias, kind, trades, P/L, MDD contribution, OOS lift, stability. |
| Branch waterfall | Candidate total profit decomposed by branch. |
| Branch heatmap | time bucket x cap bucket branch contribution. |
| Sell branch audit | exit/sell branches, loss saved, missed upside. |
| Seed-bank feedback card | Promote/penalize branch motifs for future generation prompts. |

## Tests

| Test | Scope |
|---|---|
| Static parser fixture | Given template examples with literal OR, if/elif, time, cap, and sell branches, branch ids are deterministic. |
| CSV join fixture | Given synthetic trade rows and branch map, branch metrics sum to candidate totals. |
| Dashboard contract test | Branch table renders empty, partial, and populated payloads without crashing. |
| Drift test | Registry candidate id and branch-attribution candidate id must match. |
| Nonrelease guard | No live, V3K, or official engine behavior changes unless a later approved implementation task adds default-off annotations. |

## Feedback Into Seed Bank And Prompts

Branch contribution should feed future research as follows:

1. Branches with positive OOS lift and acceptable MDD become seed-bank motifs.
2. Dead branches with low trade count are downweighted or simplified.
3. Branches that improve train but fail OOS become negative examples for prompts.
4. Time/cap buckets with stable lift get quota in future generation.
5. Sell branches that reduce loss without killing upside become explicit prompt examples.
6. Dashboard cards should expose the branch reason so the next agent can choose mutation targets without rereading raw CSV.

## Non-Goals

- Do not change generator syntax in this planning task.
- Do not change official backtest engine in this planning task.
- Do not infer live strategy readiness from branch attribution.
- Do not merge branch attribution with HoF or GUI parity panels in the first slice.
