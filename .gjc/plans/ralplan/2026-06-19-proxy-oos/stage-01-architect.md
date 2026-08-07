## Summary
계획은 `.gjc/specs/deep-interview-condition-proxy-official-oos.md`의 pending-approval 연구 범위를 대체로 정확히 충족한다. 공식 OOS와 combined CSV/portfolio simulation의 taxonomy를 분리하고, live/export/운영 DB/V3K mutation을 금지하며, STOM 변수/매수·매도 경계에 대한 사전 leakage review와 OOS 검증을 둔 점은 승인 가능한 구조다. 단, 실행 전 evidence sandbox 경로와 top-trade concentration 산출을 명시적으로 고정해야 하는 WATCH 항목이 있다.

## Analysis
### Spec compliance
- Spec의 목표는 `r8_exclude_cap_lt_1500` 기반 단일 proxy 후보 최대 3개를 공식 OOS로 검증하고 combined 결과와 비교한 `pass/defer/reject` 카드로 종료하는 것이다(`.gjc/specs/deep-interview-condition-proxy-official-oos.md:20`, `:62`). Planner는 동일하게 최대 3개 단일 STOM buy/sell pair, 공식 OOS, r8/combined 비교, 판단 카드, 연구 전용 범위를 선언한다(`.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-01-planner.md:9`, `:30-34`).
- Spec은 실매매/export/운영 DB/strategy DB/V3K/live 변경 금지와 combined CSV를 공식 buy/sell OOS로 부르지 않는 조건을 둔다(`spec:65-76`). Planner는 같은 금지선을 원칙·out-of-scope·file-level guardrail·approval gate에 반복 배치했다(`plan:12-16`, `:37-41`, `:82`, `:85`, `:113`).
- Spec의 pass/defer/reject 기준은 총수익 `> 7,292,861`, MDD `<= 19.09%`, all gates, 거래수 `>=132`, 최소 4개 양수 구간, Q4 양수, top-trade concentration 보류이다(`spec:80-88`). Planner는 driver와 acceptance에서 동일 기준을 반영한다(`plan:19-20`, `:95-104`).
- Combined taxonomy는 강하다. Planner는 combined를 비교 대상 portfolio/CSV simulation으로만 다루고 direct CSV/portfolio switching을 invalid option으로 배제한다(`plan:24-25`, `:62-64`, `:118`). Persisted combined evidence도 `not_claimed` 및 notes에서 공식 buy/sell OOS가 아니라고 명시한다(`.omo/evidence/tmap-walkforward/post-20260618-combined-portfolio-simulation-readout-20260619.json:8-10`, `:143-146`).

### Feasibility and evidence grounding
- Baseline numbers are internally consistent with persisted evidence: official r8 aggregate profit `7,292,861`, trades `263`, max MDD `19.09`, all gates passed are present in `.omo/evidence/tmap-walkforward/post-q4-r8-lowcap-official-oos-summary-20260619.json:127-130`; Q4 profit/MDD are present at `:133-140`. Combined profit `39,402,438`, MDD `7.6823`, trade count `1,073`, Q4 profit `952,502` are present in the combined readout(`combined-readout:28-42`, `:89-97`).
- STOM variable feasibility is credible. `시가총액` exists for both 1초스냅샷 and 1분봉 buy-side data(`utility/ai_agent/strategy.txt:21`, `:108`); sell-side/in-position variables including `수익률`, `보유시간`, `최고수익률`, `최저수익률` exist in the sell variable section(`strategy.txt:255-260`); dynamic exit helpers using volatility, liquidity, and 호가 pressure are documented(`strategy.txt:242-250`). Rules require separated buy/sell sections and generated strategy files under `utility/ai_agent/strategy`(`utility/ai_agent/rules.txt:24-27`), matching the planner intended strategy artifact path(`plan:75`).
- The OOS wrapper exists and is evidence-local: `.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py` sets `STOM_CLI_DB_STRATEGY` to `.omo/evidence/tmap-walkforward/post-q4-oos-strategy-20260619.sqlite` and redirects loop run state, snapshots, current-state, and stop flag into `.omo/evidence/tmap-walkforward/*` paths(`wrapper:10-15`, `:20-25`). This supports the planner no operating DB mutation boundary.

### Strongest steelman antithesis
The best objection is that the combined result may not be reducible to a single STOM buy/sell pair at all. The combined evidence describes a portfolio-layer prior-month allocation rule and separate per-strategy contribution, not one causal condition expression(`combined-readout:28-30`, `:127-133`). A single condition can use current market and held-position state, but it cannot natively express cross-strategy prior-month PnL selection without becoming an operating-rule/fallback design. Therefore a proxy pair may merely overfit exit thresholds to a historical portfolio artifact. The planner handles this antithesis acceptably by treating direct combined switching as invalid, limiting the attempt to 3 candidates, requiring official OOS, and ending with reject/defer rather than promotion if the proxy does not generalize(`plan:62-69`, `:95-104`, `:118-123`).

### Synthesis
Option C is the right bounded research synthesis: one entry-pure r8 candidate protects live reproducibility and two exit-behavior proxies test the only plausible single-pair path toward the combined performance gap. This does not prove deployability, but it is a feasible pending-approval research plan because it freezes thresholds before execution, keeps evidence local, and reserves production/export/live promotion for a separate approval boundary.

### Principle violations
No blocking principle violation found. The plan respects official OOS vs CSV taxonomy, avoids live/export/operating DB/V3K paths, keeps fallback out of scope, and defines testable research verification. Two WATCH items below should be tightened during execution handoff.

## Root Cause
The root architectural tension is translation, not implementation: an edge observed in portfolio CSV reanalysis with prior-month allocation must be tested as a causal single STOM condition pair without smuggling in prior-month portfolio state, future outcomes, or operating-rule behavior. The planner structure is built around containing that translation risk rather than pretending the combined result is already an official strategy.

## Findings
1. **LOW / WATCH — Align wrapper output paths with the planned proxy evidence directory.**
   - Reference: Planner lists new artifacts under `.omo/evidence/tmap-walkforward/proxy-oos-<date>/...`(`plan:75-80`, `:89`), while the inspected wrapper hardcodes `.omo/evidence/tmap-walkforward/post-q4-oos-*20260619*` sandbox paths(`wrapper:10-15`, `:20-25`).
   - Impact: Still evidence-local, so this is not an operating DB/live mutation blocker, but reusing the fixed post-q4 sandbox could mix candidate runs with baseline evidence and weaken auditability.
   - Fix: Before execution, either create a proxy-oos-specific wrapper/config that redirects `STOM_CLI_DB_STRATEGY`, `LOOP_RUNS_DB`, snapshots, current-state, and stop flag into the run directory, or explicitly update the manifest to treat the fixed wrapper sandbox as the run-owned evidence store with unique run IDs and cleanup records.

2. **LOW / WATCH — Make top-trade concentration non-optional for a pass.**
   - Reference: Metric extraction says top-trade concentration is collected “if CSV detail is available”(`plan:91`), while pass requires “no excessive top-trade concentration”(`plan:99`) and the spec requires 보류 when top trades dominate(`spec:84`).
   - Impact: A candidate should not pass with missing concentration evidence; otherwise the plan could satisfy aggregate metrics while skipping a robustness gate.
   - Fix: Treat missing trade-detail/CSV evidence as `defer` or an explicit evidence blocker, and compute concentration from official CSV detail whenever a candidate reaches metric-pass territory.

## Recommendations
1. Approve the plan as a pending-approval research plan; do not execute OOS or mutate evidence until user approval.
2. Add an execution preflight that pins the sandbox/run directory and verifies wrapper DB redirection before the first OOS period.
3. Make concentration evidence mandatory for `pass`; missing trade-detail evidence should result in `defer`, not `pass`.
4. Preserve the existing taxonomy in every output: official r8/proxy OOS is validation evidence; combined CSV/portfolio simulation is only a comparison reference.

## Architectural Status
`WATCH`

## Code Review Recommendation
`APPROVE`

## Trade-offs
| Option | Benefit | Cost / Risk | Verdict |
|---|---|---|---|
| Entry-only r8 proxy | Highest runtime reproducibility; uses supported buy-side variables such as `시가총액`, liquidity, 체결강도 | May not capture the exit/portfolio layer that produced the combined gap | Include one candidate |
| Exit-behavior proxy | Directly tests whether supported sell variables like `수익률`, `보유시간`, `최고수익률`, volatility and liquidity can approximate exit2/r2full behavior | Higher overfit risk; cannot encode prior-month cross-strategy allocation | Include two candidates with strict OOS/defer gates |
| Direct combined CSV/portfolio switching | Closest to observed combined result | Violates user goal and official OOS taxonomy; not a single buy/sell pair | Reject for this scope |
| Reuse existing evidence-local wrapper | Fast, already redirects operating DB state into `.omo/evidence` | Hardcoded post-q4 paths may reduce run isolation | Accept only with path/run-id preflight |
| Create proxy-specific wrapper | Cleanest provenance and sandbox ownership | Slightly more evidence-script setup before OOS | Preferred execution hardening |
