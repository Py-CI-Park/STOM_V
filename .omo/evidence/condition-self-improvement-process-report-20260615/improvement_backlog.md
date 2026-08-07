# Improvement Backlog - Condition Self-Improvement Process

## Guiding Rule
| Rule | Meaning | Consequence |
|---|---|---|
| OOS/WF first | OOS PROMISING count is the only success metric. | Smoke-pass, near-miss, score gains, and dashboard metrics are progress signals only. |
| Feedback is advisory until revalidated | Autopsy uses train/working data. | Feedback can propose changes, but cannot promote a candidate. |
| Seed breadth is necessary but not sufficient | Wide seeds improve search coverage. | Seed breadth must be paired with gate, feedback policy, and action lineage. |

## Seed Coverage
| Dimension | Current Risk | Update Method | Acceptance Signal |
|---|---|---|---|
| timeframe | tick and min tracks can be mixed in interpretation. | Track tick and min separately; tick is honest OOS pass source, min is advisory if OOS contamination exists. | Every trial has timeframe and pass-policy tag. |
| time bucket | Repeated early open or anchor-like zones can dominate. | Maintain 5-minute coverage buckets from 09:00 to configured end time. | Coverage ledger shows tried/pass/fail/skip per bucket. |
| market-cap bucket | Single cap tier can overfit one liquidity regime. | Bucket small, mid, upper-mid, large by configured STOM units. | Each generation batch covers at least two cap regimes unless anchor mode. |
| change bucket | Momentum phase can be too narrow or flood-prone. | Track negative/flat/low-positive/mid-positive/high-positive change regimes. | Flood failures attach to change bucket and reduce repeated sampling. |
| entry family | LLM can restate the same idea with new names. | Hash normalized entry structure and family label. | Duplicate family rate is visible and capped. |
| exit family | Entry may have edge while sell rule loses it. | Track scalar stop, trailing, time-stop, MFE-lock, MAE-cut families. | Exit mutation is chosen when exit regret dominates. |
| anchor/explore allocation | All-random is wasteful; all-anchor is narrow. | Fixed initial allocation: anchor 30%, broad grid 50%, mutation 20%; adjust only after OOS evidence. | Batch report shows allocation and realized verdicts. |

## Buy-Side Diagnosis
| Failure Class | Diagnostic Signal | Feedback Action | Guard |
|---|---|---|---|
| Flood entry | Trade count high, q1/q2 deeply negative. | `reject` or `tighten_threshold` on liquidity/change/time filters. | Revalidate on full train before OOS. |
| Losing time cell | Segment total profit negative or win-rate below threshold. | `avoid_segment` for time bucket or time x cap cell. | Minimum sample count required. |
| Weak cap regime | Loss concentration in one market-cap bucket. | `mutate_seed` to alternate cap bucket or tighten cap. | Do not infer from tiny cells. |
| Threshold too loose | Winners cluster above stricter B_* quantile. | `tighten_threshold` with winner quantile candidate. | In-sample only; must pass gate. |
| Threshold too strict | Too few trades but near-miss positive in adjacent bucket. | `relax_threshold` within bounded range. | Must not remove required filter gates. |
| Duplicate idea | Structural hash matches recent failed family. | `reject` duplicate or force different family. | Allow preserved anchors by explicit quota. |

## Sell-Side Diagnosis
| Failure Class | Diagnostic Signal | Feedback Action | Guard |
|---|---|---|---|
| Giveback | High MFE but realized return much lower. | `revise_exit` to lock profit after MFE threshold. | Avoid overfitting exact MFE number; use bands. |
| Deep loser | Loss trades have large negative MAE. | `revise_exit` to cut adverse movement faster. | Preserve enough time for winner development. |
| Long losing hold | Losers hold longer than winners. | Add or tighten time-stop family. | Validate by hold-time bucket, not one trade. |
| Bad sell rule concentration | One sell condition has worst average return. | Mutate or demote that sell-rule family. | Require at least 2+ trades and full-train check. |
| Profit capture inefficient | Edge ratio exists but payoff is poor. | Combine trailing or MFE-lock with scalar stop. | OOS/WF promotion only. |
| Exit too reactive | Winners exit before MFE develops. | Relax early sell rule or add minimum hold guard. | Must not increase max-hold/timeouts beyond budget. |

## Typed Feedback Ledger
| Field | Purpose | Example |
|---|---|---|
| `action_id` | Stable feedback identity. | `fb_20260615_0001` |
| `source_run_id` | Links action to backtest/generation run. | `ab_stateful_n8_iter4` |
| `candidate_id` | Strategy/template affected. | `llmgen_theta_...` |
| `action_type` | Machine-readable action. | `avoid_segment`, `revise_exit`, `promote_candidate` |
| `source_metric` | Why action exists. | `full_train_profit=-2030044`, `giveback_gap=1.8` |
| `scope` | Where action applies. | `tick:09:00-09:05:smallcap` |
| `instruction` | Human-readable prompt/action text. | `avoid this cell unless liquidity filter tightens` |
| `leakage_guard` | Prevents holdout misuse. | `train_only_advisory` |
| `next_validation` | Required proof. | `q1/q2/full/OOS` |
| `outcome` | Result after action is tried. | `dropped`, `promoted`, `needs_more_data` |

## Gate Policy
| Gate | Purpose | Pass | Fail |
|---|---|---|---|
| Syntax/schema | Prevent invalid STOM/template output. | Candidate can be rendered and tested. | Reject or retry with prior error. |
| Cost/budget | Prevent timeout-heavy sell formulas. | Candidate within static/empirical budget. | Reject before long run. |
| q1/q2 same-coordinate | Block one-slice wins. | Same parameter coordinate positive in both. | No-go or near-miss. |
| Full train | Catch smoke overfit. | Full train profit positive and required metrics acceptable. | Mark smoke-pass as overfit avoid. |
| P0b/refine gate | Catch post-hoc slice traps. | Known-good passes, bad candidate refused. | Stop feedback expansion. |
| OOS/WF | Final success proof. | PROMISING count increases. | No promotion. |
| C3 stop rule | Avoid endless retries. | Rate flat and OOS 0 for configured windows. | Move to new data/axis rather than more prompts. |

## P0-P5 Update Roadmap
| Phase | Objective | Files/Areas | Acceptance | Stop Condition | Score Impact |
|---|---|---|---|---|---|
| P0 | Freeze success metrics and gate order. | Evidence docs, gate configs, report/runbook. | OOS/WF count is declared sole success metric; P0b gate remains before feedback expansion. | Any report or UI claims success from smoke-only metrics. | OOS proof, gate discipline |
| P1 | Improve lineage/report reliability. | LoopState, prompt logging design, dashboard analysis snapshot, evidence writer. | Every generation can be traced to prompt, seed, feedback action, artifact, verdict. | Protected DB/runtime writes needed without explicit plan. | DB lineage, dashboard |
| P2 | Add seed coverage ledger. | Research loop planner, templates metadata, evidence reports. | Each batch records timeframe x time x cap x change x entry x exit coverage and allocation. | Duplicate/anchor reuse exceeds planned quota without justification. | Seed breadth, diversity |
| P3 | Add typed buy/sell feedback. | Autopsy, segment feedback, prompt builder, action ledger. | Buy and sell diagnostics create separate action records with leakage guard. | Any in-sample action directly promotes a candidate. | Buy diagnosis, sell diagnosis, feedback policy |
| P4 | Add mutation/grid/coarse-to-fine loop. | TMAP templates, mutation planner, validation funnel. | Mutations declare the action they test and are accepted only after full/OOS validation. | Mutations increase proxy rates but OOS stays 0 across C3 windows. | End-to-end autonomy |
| P5 | Add dashboard/runbook automation. | Dashboard, reports, evidence summary. | User can see coverage debt, action history, gate status, and next recommended work. | Dashboard hides OOS 0 behind proxy score. | Dashboard, management |

## Recommended Next Start-Work Scope
| Scope | Why First | Deliverable |
|---|---|---|
| `condition-self-improvement-p0-p2-implementation-20260615` | P0-P2 harden measurement, lineage, and seed coverage before adding more feedback complexity. | A new plan that implements metric freeze, action/prompt lineage design, and seed coverage ledger with tests. |
| `condition-self-improvement-p3-feedback-ledger-20260615` | Start only after P0-P2 prove evidence quality. | Typed feedback action records and buy/sell feedback wiring. |
