# RALPLAN Revision Pass 2: STOM 단일 proxy 조건식 공식 OOS 연구

Generated: 2026-06-19
Source spec: `.gjc/specs/deep-interview-condition-proxy-official-oos.md`
Prior pass: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-01-planner.md`
Critic verdict addressed: **ITERATE -> revision ready for review**
Status: **PENDING APPROVAL — planning only**

## Summary

`r8_exclude_cap_lt_1500` 기반 단일 proxy STOM 조건식 후보를 최대 3개 설계하고 공식 OOS로 검증한다. Pass 2는 critic WATCH 항목을 반영해 실행 전 proxy run directory 고정, wrapper mutable path 검증, wrapper/config ownership, top-trade concentration mandatory pass gate를 추가한다. 이번 범위는 연구 산출물과 판단 카드까지이며, 실매매/export/운영 DB/V3K/live 경로는 별도 승인 전 금지한다.

## Principles

1. **Evidence taxonomy first**: 공식 OOS, proxy run evidence, baseline evidence, combined portfolio simulation/CSV 재분석을 혼동하지 않는다.
2. **Run-owned isolation**: proxy OOS 산출물은 고정된 run directory 아래에만 쓰고, wrapper mutable path가 운영 DB나 baseline evidence를 가리키면 즉시 중단한다.
3. **Single proxy constraint**: 월별 CSV/포트폴리오 스위칭이 아니라 STOM에서 실행 가능한 단일 buy/sell 조건식 pair만 최대 3개 평가한다.
4. **Mandatory robustness gates**: profit/MDD/gate/trades/period/Q4/top-trade concentration을 모두 통과해야 `pass`다.
5. **No silent promotion**: 3개 모두 실패하거나 evidence가 부족하면 `reject` 또는 `defer/evidence blocker` 카드만 남기고 fallback·live·export로 확장하지 않는다.

## Top 3 Decision Drivers

1. **Official baseline improvement**: aggregate profit > 7,292,861원, max MDD <= 19.09%, all gates passed.
2. **Robustness and evidence completeness**: trades >= 132, 최소 4개 기간 양수, Q4 양수, top-trade concentration mandatory pass gate 충족, trade-detail/CSV 증거 존재.
3. **Isolation/deployability**: proxy run-owned wrapper/config paths만 사용하고, 조건식은 `strategy.txt`/`rules.txt` 지원 변수로 재현 가능해야 한다.

## Evidence Baseline

- Official r8 baseline: profit 7,292,861원, trades 263, max MDD 19.09%, all gates passed, Q4 profit 310,886원, Q4 MDD 9.25%.
- Combined portfolio simulation: profit 39,402,438원, MDD 7.6823%, Q4 profit 952,502원, trade_count 1,073. 이는 포트폴리오/CSV 재분석이며 공식 buy/sell OOS가 아니다.
- 2026 OOS는 2026-02-28까지의 YTD이며 full-year가 아니다.

## In scope / out of scope

### In scope

- 최대 3개 단일 proxy STOM buy/sell 조건식 pair 설계 및 코드 기록.
- 승인 후 proxy-oos-specific wrapper/config 또는 명시적으로 run-owned 처리된 기존 wrapper sandbox로 공식 OOS 수행.
- 실행 전 preflight: run directory, wrapper mutable paths, operating DB/baseline evidence collision, unique run IDs, cleanup record 계획 확인.
- 후보별 결과표: 총수익, MDD, gate, 거래수, 기간별 수익, Q4 수익, top-trade concentration.
- official r8 baseline 및 combined simulation과 비교표 작성.
- 최종 `pass/defer/reject` 판단 카드 작성.

### Out of scope

- CSV 포트폴리오 스위칭 구현 또는 운영 규칙 승격.
- 실매매, export, 운영 strategy DB/loop DB 변경.
- baseline evidence 파일 덮어쓰기 또는 기존 r8 official OOS 산출물 재소유.
- V3K gate/live/KHOPENAPI 승인 경로 변경.
- UI/frontend/product source 변경.
- 3개 실패 이후 fallback 조건식 세트/운영 규칙 연구 실행.

## Options

### Option A — Entry-only r8 proxy variants

- 내용: 기존 r8 저시총 제외 entry filter를 중심으로 `시가총액 >= 1500`, 거래대금/체결강도/호가압력/변동성 같은 재현 가능 변수로 buy 조건을 조정하고 sell은 검증된 baseline 계열을 유지한다.
- Pros: 단일 조건식 순도가 높고 live 재현성이 가장 좋다. CSV/전월 손익 상태 의존이 없다.
- Cons: combined 성과 격차가 exit2/r2full 포트폴리오 레이어에서 온 경우 수익 개선 폭이 작을 수 있다.
- Invalidation: profit <= 7,292,861원, MDD > 19.09%, gate fail, trades < 132, Q4 <= 0, concentration fail, CSV/trade-detail missing이면 pass 불가.

### Option B — Exit-behavior proxy pair

- 내용: r8 entry는 유지하되 sell 조건에서 `수익률`, `보유시간`, `최고수익률`, `변동성`, 거래대금/호가압력 기반 청산을 사용해 exit2/r2full의 방어·추세 유지 특성을 단일 STOM pair 안에서 근사한다.
- Pros: combined simulation의 핵심 격차인 exit behavior를 직접 겨냥한다. 단일 buy/sell pair 공식 OOS로 검증 가능하다.
- Cons: 파라미터 과최적화 위험이 높고 prior-month 손익 규칙 자체는 단일 조건식으로 재현하지 못한다.
- Invalidation: 전월 손익·CSV 선택·미래 수익 등 런타임 재현 불가능 상태를 쓰면 `reject`; concentration evidence가 없거나 상위 거래 의존이 크면 `defer/reject`.

### Option C — Balanced 3-candidate slate (recommended)

- 내용: 후보 1개는 Option A(entry purity), 후보 2개는 서로 다른 Option B(exit behavior proxy: 방어형/추세형)로 배치한다.
- Pros: 최대 3개 제한 안에서 재현성과 성과 격차 추적을 모두 커버한다.
- Cons: 각 축의 탐색 깊이는 제한된다.
- Invalidation: 세 후보 모두 기준 미달이면 연구 결과는 `reject` 카드로 종료하고 fallback 연구를 별도 후속으로 분리한다.

### Option D — Proxy-specific wrapper/config (preferred execution envelope)

- 내용: approved execution에서 `.omo/evidence/tmap-walkforward/proxy-oos-<YYYYMMDD>/` 아래 wrapper/config/strategy sandbox/run-state/log/snapshot/summary 경로를 새로 고정한다.
- Pros: baseline evidence 오염 가능성이 가장 낮고 preflight가 명확하다.
- Cons: wrapper/config 생성 자체가 연구 evidence mutation이므로 approval 이후에만 가능하다.
- Invalidation: wrapper가 operating DB 또는 baseline evidence directory를 가리키면 stop.

### Option E — Existing hardcoded wrapper as run-owned sandbox

- 내용: 기존 `.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py`와 hardcoded sandbox를 재사용하되, proxy run이 그 sandbox를 명시적으로 소유하고 unique run IDs, cleanup record, collision check를 남긴다.
- Pros: 이미 검증된 command envelope를 재사용한다.
- Cons: 기존 r8 baseline evidence와 경로 혼동 가능성이 있어 preflight·cleanup·summary labeling이 더 엄격해야 한다.
- Invalidation: 기존 baseline 요약/CSV/snapshot을 덮거나 run IDs가 충돌하면 stop. 가능하면 Option D로 전환한다.

### Invalid Option — Direct combined CSV/portfolio switching

- 내용: exit2 prior-month allocation 또는 CSV 성과 조합을 그대로 운영 후보로 삼는다.
- Rejection rationale: 사용자 목표가 단일 proxy 조건식 공식 OOS이며 combined 수치는 공식 buy/sell OOS가 아니다.

## RALPLAN-DR Summary

- Decision: **Option C + Option D를 승인 대기 실행안으로 채택**한다. Option E는 기존 wrapper를 반드시 써야 할 때만 허용되는 fallback envelope다.
- Rationale: proxy-specific run directory와 wrapper/config가 critic WATCH의 mutable path/baseline collision 우려를 가장 명확히 해소한다. 후보 slate는 1 entry-pure + 2 exit-proxy로 유지한다.
- Consequence: execution은 OOS보다 먼저 preflight artifact를 만들고, path ownership이 불명확하거나 trade-detail evidence가 없으면 pass를 내릴 수 없다.

## File-level changes

Planning stage writes only this RALPLAN revision through `gjc ralplan --write`.

Approved execution may create/update research evidence only under a pinned run directory:

- Run root: `.omo/evidence/tmap-walkforward/proxy-oos-<YYYYMMDD>/`.
- Candidate code: `utility/ai_agent/strategy/<한글전략명>_<timestamp>.txt` or run-root mirrored strategy text if approval limits writes to evidence only.
- Pair manifest: `<run_root>/pairs-proxy-oos-<run_tag>.json`.
- Strategy sandbox: `<run_root>/strategy-sandbox.sqlite`.
- Loop runs sandbox: `<run_root>/loop-runs.sqlite`.
- Snapshots: `<run_root>/snapshots/`.
- Current state: `<run_root>/current-state.json`.
- Stop flag: `<run_root>/STOP`.
- Logs: `<run_root>/logs/`.
- Summaries/comparison/card: `<run_root>/summary-*.json`, `<run_root>/comparison-*.json|md`, `<run_root>/decision-card-*.json`.
- CSV references: generated official CSVs may remain under runner-emitted `backtest/csv/...`, but the run summary must record exact paths, mtimes/sizes if available, and must never claim them as source edits or promotion artifacts.
- Cleanup record: `<run_root>/process-cleanup-<run_tag>.json` documenting no orphan runner processes and no path collision.

Forbidden targets: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, operating `*.db`, `ai_strategy_loop/state/loop_strategies.db`, `ai_strategy_loop/state/loop_runs.db`, existing baseline evidence summaries/snapshots/logs, live/export/V3K/KHOPENAPI paths.

## Execution preflight (mandatory before OOS)

1. **Pin run root**: choose a single `<run_root>` such as `.omo/evidence/tmap-walkforward/proxy-oos-20260619/` and write all proxy-owned evidence there after approval.
2. **Choose wrapper envelope**:
   - Preferred: create/use proxy-oos-specific wrapper/config whose mutable path constants all point under `<run_root>`.
   - Allowed fallback: mark existing hardcoded wrapper sandbox as proxy run-owned for this run only, require unique run IDs, and emit cleanup/collision records before and after OOS.
3. **Verify mutable paths** before any OOS:
   - strategy sqlite path
   - loop runs sqlite path
   - snapshots directory
   - current state JSON
   - stop flag path
   - logs directory
   - summary/comparison/decision-card output paths
   - CSV reference capture policy
4. **Stop conditions**:
   - Any mutable path targets operating DBs or `ai_strategy_loop/state/*`.
   - Any mutable path targets baseline evidence files/directories from the r8 official OOS or combined simulation summaries.
   - Any run ID collides with an existing run row/snapshot/log for the same period/candidate.
   - Wrapper cannot prove evidence-local ownership before OOS.
5. **Preflight artifact**: record the resolved paths, wrapper option, run IDs, and stop-condition verdict in `<run_root>/preflight-<run_tag>.json` or equivalent summary.

## Top-trade concentration rule (mandatory pass gate)

- Required evidence: official per-trade CSV or equivalent trade-detail evidence for each candidate and period used in the aggregate.
- Metric: compute absolute profit contribution concentration over the aggregate OOS trade set:
  - `top1_abs_share = abs(largest_trade_profit_krw) / sum(abs(trade_profit_krw))`
  - `top5_abs_share = sum(abs(top_5_trade_profit_krw_by_abs_value)) / sum(abs(trade_profit_krw))`
  - also record `top5_net_share = sum(top_5_trade_profit_krw_by_abs_value) / total_profit_krw` when total_profit_krw > 0.
- Decision rule:
  - `pass` concentration gate requires `top1_abs_share <= 0.20` and `top5_abs_share <= 0.50`.
  - If `top1_abs_share > 0.20` or `top5_abs_share > 0.50`, metrics may not be `pass`; use `defer` when all other gates pass but concentration is the only concern, or `reject` when combined with other failures.
  - If official trade-detail/CSV evidence is missing, malformed, or cannot be reconciled to the summary, final verdict is `defer` or `evidence_blocker`; never `pass`.

## Sequencing and dependencies

1. **Approval gate**: stop until the user approves execution of this revised plan. No OOS or mutation before approval.
2. **Freeze baselines**: copy official r8 baseline and combined simulation metrics into the run manifest with evidence paths and 2026 YTD caveat.
3. **Execution preflight**: pin `<run_root>`, select Option D or E wrapper envelope, verify all mutable paths, unique run IDs, CSV reference policy, cleanup record path, and stop conditions.
4. **Design candidate slate**: P1 entry-pure r8 low-cap/liquidity/momentum proxy; P2 defensive exit proxy approximating exit2 drawdown containment; P3 trend/volatility exit proxy approximating r2full participation.
5. **Syntax/leakage review**: verify STOM-supported variables; buy side must not use holdings/result variables; no future/CSV/prior-month PnL state.
6. **Evidence-local materialization**: create pair JSON and strategy sandbox only under the pinned run-owned location.
7. **Official OOS execution**: run one period at a time, Q4 stress first, then 2022, 2023, 2024, 2025, 2026 YTD. Stop on non-zero runner exit or path ownership violation.
8. **Metric extraction**: aggregate profit, trades, max MDD, all gates, period profits, Q4, daily/trade diagnostics, and mandatory top-trade concentration.
9. **Comparison and decision**: compare each candidate to official r8 and combined simulation; assign `pass`, `defer`, `reject`, or `evidence_blocker` with explicit rationale.
10. **Post-run guardrail check**: cleanup record, path collision check, no operating DB/live/export/protected runtime path mutation.

## Acceptance criteria

- 1-3 candidate condition pairs are documented with code, intent, and leakage review.
- A pinned proxy run directory and preflight artifact exist before any OOS result is considered valid.
- Wrapper/config mutable paths are verified for strategy sqlite, loop runs sqlite, snapshots, current state, stop flag, logs, summaries/cards, and CSV reference capture.
- Preferred execution uses a proxy-oos-specific wrapper/config. If existing hardcoded wrapper is reused, artifact must state it is run-owned, show unique run IDs, and include cleanup/collision records.
- Any path targeting operating DBs, baseline evidence files, live/export/V3K/KHOPENAPI paths, or existing baseline snapshots/logs blocks execution.
- Every enrolled candidate has official OOS evidence or an explicit runner/syntax/preflight failure record.
- Candidate result tables include aggregate profit, max MDD, gates, trades, per-period profit, Q4 profit, CSV/trade-detail references, and concentration metrics.
- `pass` requires profit > 7,292,861원, MDD <= 19.09%, all gates passed, trades >= 132, at least 4 positive periods, Q4 > 0, `top1_abs_share <= 0.20`, `top5_abs_share <= 0.50`, and reconciled official trade-detail/CSV evidence.
- Missing/malformed/unreconciled official trade-detail or CSV evidence yields `defer` or `evidence_blocker`, never `pass`.
- `reject` is used for metric failure, gate failure, trade-count failure, Q4 nonpositive, leakage, unsupported STOM syntax, or severe path guardrail failure.
- Comparison table includes official r8 baseline and combined simulation values: combined profit 39,402,438원, MDD 7.6823%, Q4 profit 952,502원.
- Final card states whether fallback research is deferred because all three failed; it must not execute fallback research in this scope.

## Verification

After approval, verification is research/evidence verification only, not project-wide tests or formatters:

- Verify preflight JSON/summary resolves all mutable paths under `<run_root>` or explicitly approved run-owned wrapper sandbox.
- Verify no mutable path points to `ai_strategy_loop/state/loop_strategies.db`, `ai_strategy_loop/state/loop_runs.db`, `_database/`, operating `*.db`, baseline evidence summaries, baseline snapshots/logs, live/export/V3K/KHOPENAPI paths.
- Verify wrapper/config selection: Option D proxy-specific wrapper/config preferred; Option E requires unique run IDs and cleanup/collision records.
- Parse generated JSON manifests/summaries/cards.
- Inspect condition code against `strategy.txt` variables and buy/sell variable boundaries.
- Reconcile loop run DB rows, snapshots, logs, CSV paths, and summary JSON for each candidate/period.
- Compute and record top-trade concentration from official per-trade CSV/equivalent detail: `top1_abs_share`, `top5_abs_share`, `top5_net_share`.
- Verify pass candidates have reconciled trade-detail/CSV evidence; missing detail blocks pass.
- Verify final comparison arithmetic against frozen baselines.
- Verify post-run cleanup record and guardrails: no live/export/V3K/KHOPENAPI activity and no writes to operating strategy/loop DBs.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Existing hardcoded wrapper writes into baseline sandbox | baseline evidence contamination | Prefer proxy-specific wrapper/config; fallback requires run-owned declaration, unique run IDs, pre/post cleanup and collision records |
| Wrapper mutable path targets operating DB | guardrail breach | mandatory preflight path check; stop on `ai_strategy_loop/state/*`, `_database/`, operating `*.db`, live/export/V3K/KHOPENAPI targets |
| Logs/summaries/CSV references are not pinned | irreproducible evidence | pin `<run_root>` and record logs, summaries, CSV paths, mtimes/sizes where possible |
| combined result mistaken for official OOS | invalid promotion argument | label combined only as portfolio/CSV simulation in every table/card |
| Top-trade concentration hidden by aggregate metrics | false pass | mandatory concentration metric and thresholds; missing trade-detail evidence means defer/evidence blocker, never pass |
| overfit from proxy tuning | false pass | max 3 candidates, fixed thresholds, period/Q4/trade/concentration checks |
| candidate uses non-reproducible state | live-ineligible result | pre-run leakage review; reject unsupported prior-month/CSV/future/result dependencies |
| Q4/2026 interpretation error | wrong robustness conclusion | keep Q4 separate and mark 2026 as YTD through 2026-02-28 |
| all candidates fail | pressure to expand scope | write reject card only; fallback becomes separate follow-up |

## Handoff guidance

- This revision is ready for Architect/Critic review or direct user approval.
- Execution must not start until approval because official OOS and evidence generation are outside this planning-only stage.
- After approval, use a bounded executor for preflight + wrapper/config/run-owned setup, then OOS execution and card generation. No team/ultragoal is needed unless OOS becomes long-running across multiple machines.
