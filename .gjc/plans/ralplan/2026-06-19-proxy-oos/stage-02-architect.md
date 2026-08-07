## Summary
Pass 2 is approvable as a planning artifact. The revision directly addresses the critic-required changes: sandbox path isolation is now a mandatory execution preflight with pinned run-owned paths, and top-trade concentration is now a mandatory pass gate with defined metrics, thresholds, and missing-evidence behavior.

The remaining risks are execution-time WATCH items, not planning blockers, because the revised plan explicitly makes them stop/pass conditions before any OOS result can be considered valid. Recommendation: approve the revised plan for user approval; do not run OOS or mutate research evidence until that approval gate is crossed.

## Analysis

### Spec compliance
- The spec requires up to three `r8_exclude_cap_lt_1500` single proxy candidates, official OOS, combined comparison, and pass/defer/reject card, with no live/export/operating DB/V3K promotion (`.gjc/specs/deep-interview-condition-proxy-official-oos.md:62-69`, `:78-88`).
- The revision preserves that scope: it is `PENDING APPROVAL`, excludes live/export/operating DB/V3K/live, and limits execution to at most three single buy/sell pairs (`stage-02-revision.md:1-48`, `:45-90`).
- Baseline values are grounded: official r8 is profit 7,292,861, trades 263, max MDD 19.09, all gates passed, Q4 profit 310,886 (`post-q4-r8-lowcap-official-oos-summary-20260619.json:119-154`). Combined simulation is explicitly not pure official buy/sell OOS and reports profit 39,402,438, MDD 7.6823, trade count 1,073, Q4 profit 952,502 (`post-20260618-combined-portfolio-simulation-readout-20260619.json:9-10`, `:35-41`, `:91-97`).

### Critic-required changes
- Critic pass 1 required: pin/preflight every mutable wrapper path; make top-trade concentration non-optional; carry both into acceptance, verification, and risk controls (`stage-01-critic.md:19-22`).
- Sandbox isolation is now explicit and feasible. The revision pins a run root, enumerates strategy sqlite, loop-runs sqlite, snapshots, current-state, stop flag, logs, summaries/cards, CSV reference policy, cleanup record, and forbidden targets (`stage-02-revision.md:107-142`). It prefers a proxy-specific wrapper/config and allows the current hardcoded wrapper only as a declared run-owned fallback with unique IDs and cleanup/collision records (`stage-02-revision.md:76-87`, `:94-106`, `:122-142`). This matches the inspected wrapper, which hardcodes `.omo/evidence/tmap-walkforward/post-q4-oos-*` paths for strategy DB, runs DB, snapshots, current state, and stop flag (`run_post_q4_oos_wrapper_20260619.py:11-28`); creating a proxy-specific evidence-local wrapper/config after approval is straightforward.
- Top-trade concentration is now explicit and non-optional. The revision requires official per-trade CSV/equivalent detail, defines `top1_abs_share`, `top5_abs_share`, and `top5_net_share`, sets pass thresholds of `top1_abs_share <= 0.20` and `top5_abs_share <= 0.50`, and forbids `pass` if detail is missing, malformed, or unreconciled (`stage-02-revision.md:144-181`). Acceptance, verification, and risk/mitigation repeat the gate (`stage-02-revision.md:169-190`, `:199-207`).

### Feasibility and boundaries
- Candidate design is feasible within STOM variables. `strategy.txt` exposes buy variables such as `시가총액`, `당일거래대금`, `체결강도`, 호가/잔량, and volatility-derived variables (`utility/ai_agent/strategy.txt:7-21`, `:183-215`), plus sell-side balance variables including `수익금`, `수익률`, `매수가`, `보유시간`, `최고수익률`, `최저수익률` (`utility/ai_agent/strategy.txt:255-260`). `rules.txt` requires separated buy/sell strategies in one generated strategy file (`utility/ai_agent/rules.txt:20-27`).
- The plan correctly rejects direct combined CSV/portfolio switching because the combined readout itself labels that result as portfolio/CSV simulation, not production/export approval (`post-20260618-combined-portfolio-simulation-readout-20260619.json:9-10`; `stage-02-revision.md:89-93`).
- Approval discipline is preserved: sequencing begins with an approval gate and states no OOS or mutation before approval (`stage-02-revision.md:158-166`, `:215-217`).

### Steelman antithesis, tradeoff tension, and synthesis
- Steelman antithesis: request changes until the preflight artifact and concentration computation exist, because the plan has not yet proven the wrapper can be made proxy-specific or that per-trade CSV detail will reconcile.
- Tension: demanding those artifacts now would turn read-only planning into execution; approving without gates would be unsafe.
- Synthesis: Pass 2 takes the correct middle. It does not claim execution evidence already exists; it makes path ownership and concentration detail prerequisites for a valid result and forbids pass on missing evidence. Under the acceptance rule, these WATCH items are acceptable because they are explicit, feasible, and gated.

## Root Cause
The prior gap was implicit evidence integrity: the initial plan relied on an evidence-local wrapper that was actually hardcoded to `post-q4-oos-*` paths, and it treated concentration as optional while using concentration as a robustness concern. Pass 2 fixes this by moving both assumptions into preflight, acceptance, verification, and risk controls.

## Findings

| Severity | Reference | Impact | Fix / disposition |
|---|---|---|---|
| LOW / WATCH | `stage-02-revision.md:107-142`; `run_post_q4_oos_wrapper_20260619.py:11-28` | Existing wrapper reuse can confuse proxy and baseline evidence. | Resolved for planning: Option D proxy-specific wrapper/config is preferred; Option E requires run-owned declaration, unique IDs, cleanup, and collision records. Stop if ownership is not proven. |
| LOW / WATCH | `stage-02-revision.md:144-181`, `:169-190` | Aggregate metrics cannot reveal top-trade dependence. | Resolved for planning: per-trade/equivalent detail is mandatory; missing/malformed/unreconciled detail yields `defer` or `evidence_blocker`, never `pass`. |
| LOW / WATCH | `stage-02-revision.md:107-109`; `utility/ai_agent/rules.txt:20-27` | Candidate text location depends on approval scope. | Not a blocker. Prefer run-root mirroring unless approval explicitly permits writing strategy text outside evidence; no DB/export/live promotion is allowed. |

No CRITICAL, HIGH, or MEDIUM planning blockers found.

## Recommendations
1. Approve Pass 2 as the pending-approval plan; do not execute OOS until explicit user approval.
2. Use Option D first during approved execution: proxy-specific wrapper/config with all mutable paths under `.omo/evidence/tmap-walkforward/proxy-oos-<YYYYMMDD>/`.
3. Treat Option E as an exception only when preflight proves run ownership, unique IDs, and no baseline collision.
4. Treat missing or unreconciled official trade detail as `defer`/`evidence_blocker`; never allow a concentration-blind `pass`.
5. Keep combined portfolio numbers labeled as comparison evidence, not official buy/sell OOS, and retain the 2026 YTD caveat.

## Architectural Status
`WATCH`

Execution-time path isolation and concentration checks remain to be performed, but both are explicitly gated and feasible. There is no material planning blocker.

## Code Review Recommendation
`APPROVE`

Product Status: `CLEAR` — the plan matches the spec scope and non-goals.
Code Status: `WATCH` — no implementation was reviewed; wrapper/path and per-trade evidence checks must be verified during approved execution.

## Trade-offs

| Option | Benefit | Cost / risk | Verdict |
|---|---|---|---|
| Option C + D: balanced slate with proxy-specific wrapper/config | Best spec and critic alignment; isolates mutable evidence paths. | Requires approved evidence wrapper/config creation. | Preferred and approvable. |
| Option C + E: reuse current hardcoded wrapper | Reuses known runner envelope. | Higher collision/confusion risk from `post-q4-oos-*` paths. | Accept only as gated fallback. |
| Demand preflight before plan approval | Maximizes certainty. | Turns planning review into execution and violates pending-approval boundary. | Reject for this stage. |
| Direct combined CSV/portfolio switching | Chases strongest combined result. | Violates single official proxy buy/sell OOS objective and evidence taxonomy. | Reject. |
