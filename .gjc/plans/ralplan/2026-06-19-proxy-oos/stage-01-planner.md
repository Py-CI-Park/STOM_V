# RALPLAN Planner Artifact: STOM 단일 proxy 조건식 공식 OOS 연구

Generated: 2026-06-19
Source spec: `.gjc/specs/deep-interview-condition-proxy-official-oos.md`
Status: **PENDING APPROVAL — planning only**

## Summary

`r8_exclude_cap_lt_1500` 기반의 단일 proxy STOM 조건식 후보를 최대 3개 설계하고, 공식 OOS로 검증한 뒤, 기존 공식 r8 단독 기준선 및 combined portfolio simulation과 비교해 `pass/defer/reject` 판단 카드를 남긴다. 이번 계획은 연구 전용이며, 실매매/live/export/V3K/운영 strategy DB 반영은 승인 전 금지한다. combined CSV 포트폴리오 조합은 비교 대상일 뿐 공식 buy/sell OOS로 호칭하지 않는다.

## Principles
1. 공식 OOS, evidence-local 산출물, combined portfolio simulation/CSV 재분석을 분리한다.
2. 월별 CSV/포트폴리오 선택 규칙이 아니라 STOM에서 실행 가능한 단일 buy/sell 조건식 pair만 후보로 등록한다.
3. live/export/운영 DB/strategy DB/V3K/KHOPENAPI 경로는 건드리지 않는다. 공식 OOS가 DB를 필요로 하면 운영 DB가 아닌 evidence-local sandbox만 사용한다.
4. 후보는 최대 3개, 통과 기준은 사전 고정, 거래수·구간 분산·Q4·상위 거래 의존도를 함께 본다.
5. 3개 모두 실패하면 fallback 조건식 세트/운영 규칙 연구로 확장하지 않고 실패 판단 카드로 종료한다.

## Top 3 Decision Drivers
1. aggregate profit > 7,292,861원, max MDD <= 19.09%, all gates passed.
2. 거래수 >= 132건, 최소 4개 기간 양수, Q4 양수, 상위 거래 의존 과도 시 `defer`.
3. `strategy.txt`/`rules.txt`의 STOM 변수로 표현 가능하고 미래정보·결과변수·CSV/전월 손익 상태에 의존하지 않아야 한다.

## Evidence Baseline
- 공식 r8 단독 OOS: profit 7,292,861원, trades 263, max MDD 19.09%, all gates passed, Q4 profit 310,886원, Q4 MDD 9.25%.
- combined portfolio simulation: profit 39,402,438원, MDD 7.6823%, Q4 profit 952,502원, trade_count 1,073. 이는 공식 buy/sell OOS가 아니다.
- 2026 OOS는 2026-02-28까지의 YTD이지 full-year가 아니다.

## In scope / out of scope
### In scope
- 최대 3개 단일 proxy STOM buy/sell 조건식 pair 설계 및 코드 기록.
- 승인 후 evidence-local wrapper로 Q4 stress 및 2022/2023/2024/2025/2026 YTD 공식 OOS 수행.
- 후보별 결과표: 총수익, MDD, gate, 거래수, 기간별 수익, Q4 수익.
- 공식 r8 기준선 및 combined simulation과 비교표 작성.
- 최종 `pass/defer/reject` 판단 카드 작성.

### Out of scope
- CSV 포트폴리오 스위칭 구현 또는 운영 규칙 승격.
- 실매매, export, 운영 strategy DB/loop DB 변경.
- V3K gate/live/KHOPENAPI 승인 경로 변경.
- UI/frontend/product source 변경.
- 3개 실패 이후 fallback 조건식 세트/운영 규칙 연구 실행.

## Options
### Option A — Entry-only r8 proxy variants
- 내용: 기존 r8 저시총 제외 entry filter를 중심으로 `시가총액 >= 1500`, 거래대금/체결강도/호가압력/변동성 같은 실시간 재현 가능 변수로 buy 조건만 조정하고 sell은 검증된 baseline 계열을 유지한다.
- Pros: 단일 조건식 순도가 높고 live 재현성이 가장 좋다. CSV/전월 손익 상태 의존이 없다.
- Cons: combined 성과 격차가 exit2/r2full 포트폴리오 레이어에서 온 경우 수익 개선 폭이 작을 수 있다.
- Invalidation: profit <= 7,292,861원, MDD > 19.09%, gate fail, trades < 132, Q4 <= 0이면 `reject`; 상위 거래 의존 과도면 `defer`.

### Option B — Exit-behavior proxy pair
- 내용: r8 entry는 유지하되 sell 조건에서 `수익률`, `보유시간`, `최고수익률`, `변동성`, 거래대금/호가압력 기반 청산 등을 사용해 exit2/r2full의 방어·추세 유지 특성을 단일 STOM pair 안에서 근사한다.
- Pros: combined simulation의 핵심 격차인 exit behavior를 직접 겨냥한다. 단일 buy/sell pair 공식 OOS로 검증 가능하다.
- Cons: 파라미터 과최적화 위험이 높고, prior-month 손익 규칙 자체는 단일 조건식으로 재현하지 못한다.
- Invalidation: 전월 손익·CSV 선택·미래 수익 등 런타임에서 재현 불가능한 상태를 쓰면 즉시 `reject`; 기준 통과 후에도 분산/상위거래 의존이 나쁘면 `defer`.

### Option C — Balanced 3-candidate slate (recommended)
- 내용: 후보 1개는 Option A(entry purity), 후보 2개는 서로 다른 Option B(exit behavior proxy: 방어형/추세형)로 배치한다.
- Pros: 최대 3개 제한 안에서 재현성과 성과 격차 추적을 모두 커버한다.
- Cons: 각 축의 탐색 깊이는 제한된다.
- Invalidation: 세 후보 모두 기준 미달이면 연구 결과는 `reject` 카드로 종료하고 fallback 연구를 별도 후속으로 분리한다.

### Invalid Option — Direct combined CSV/portfolio switching
- 내용: exit2 prior-month allocation 또는 CSV 성과 조합을 그대로 운영 후보로 삼는다.
- Rationale for rejection: 사용자 목표가 단일 proxy 조건식 공식 OOS이며, combined 수치는 공식 buy/sell OOS가 아니다. 이번 범위에서 구현/검증 대상이 아니다.

## RALPLAN-DR Summary
- Decision: **Option C를 승인 대기 실행안으로 채택**한다.
- Rationale: entry-only 후보만으로는 combined 격차를 설명하기 어렵고, exit proxy만 3개를 쓰면 실매매 재현성 검토가 약해진다. 1 entry-pure + 2 exit-proxy 조합이 최대 3개 제한, 공식 OOS, guardrail, 비교 가능성을 가장 잘 만족한다.
- Consequence: 후보별 성패가 분명해진다. 3개 모두 실패하면 fallback은 별도 RALPLAN/deep-interview 후속으로 이동한다.

## File-level changes
Planning stage writes only this RALPLAN artifact through `gjc ralplan --write`.

Approved execution may create/update research evidence only:
- `utility/ai_agent/strategy/<한글전략명>_<timestamp>.txt` — 후보 조건식 코드와 매수/매도 설명.
- `.omo/evidence/tmap-walkforward/proxy-oos-<date>/pairs-*.json` — 후보 pair manifest.
- `.omo/evidence/tmap-walkforward/proxy-oos-<date>/strategy-sandbox.sqlite` — evidence-local sandbox only, not operating strategy DB.
- `.omo/evidence/tmap-walkforward/proxy-oos-<date>/logs/`, `snapshots/`, `summary-*.json` — official OOS run evidence.
- `.omo/evidence/tmap-walkforward/proxy-oos-<date>/comparison-*.md|json` — baseline/combined comparison.
- `.omo/evidence/tmap-walkforward/proxy-oos-<date>/decision-card-*.json` — final pass/defer/reject card.

No product source, live/export path, `_database/`, `ai_strategy_loop/state/loop_strategies.db`, or `ai_strategy_loop/state/loop_runs.db` may be mutated.

## Sequencing and dependencies
1. **Approval gate**: stop until the user approves execution of this plan. No OOS or mutation before approval.
2. **Freeze baselines**: copy official r8 baseline metrics and combined simulation metrics into the run manifest, including evidence paths and the 2026 YTD caveat.
3. **Design candidate slate**: P1 entry-pure r8 low-cap/liquidity/momentum proxy; P2 defensive exit proxy approximating exit2 drawdown containment; P3 trend/volatility exit proxy approximating r2full participation.
4. **Syntax and leakage review**: verify every condition uses STOM-supported variables; buy side must not use holdings/result variables; no future/CSV/prior-month PnL state.
5. **Evidence-local materialization**: build pair JSON and sandbox only under `.omo/evidence/tmap-walkforward/proxy-oos-<date>/`; do not call helpers that write operating DBs.
6. **Official OOS execution**: run wrapper one period at a time, Q4 stress first for operational sanity, then 2022, 2023, 2024, 2025, 2026 YTD. Stop on non-zero runner exit and record blocker.
7. **Metric extraction**: aggregate profit, trades, max MDD, all gates, period profits, Q4, daily/trade diagnostics, top-trade concentration if CSV detail is available.
8. **Comparison and decision**: compare each candidate to official r8 and combined simulation; assign `pass`, `defer`, or `reject` with explicit rationale.
9. **Guardrail check**: confirm no operating DB/live/export/protected runtime paths changed; generated official CSVs are evidence only and must be referenced, not promoted.

## Acceptance criteria
- 1-3 candidate condition pairs are documented with code, intent, and leakage review.
- Every enrolled candidate has official OOS evidence or an explicit runner/syntax failure record.
- Candidate result tables include aggregate profit, max MDD, gates, trades, per-period profit, and Q4 profit.
- `pass` requires profit > 7,292,861원, MDD <= 19.09%, all gates passed, trades >= 132, at least 4 positive periods, Q4 > 0, and no excessive top-trade concentration.
- `defer` is used for metrics pass but robustness/deployability concerns, especially concentration or suspicious parameter sensitivity.
- `reject` is used for metric failure, gate failure, trade-count failure, Q4 nonpositive, leakage, or unsupported STOM syntax.
- Comparison table includes official r8 baseline and combined simulation values: combined profit 39,402,438원, MDD 7.6823%, Q4 profit 952,502원.
- Final card states whether fallback research is deferred because all three failed; it must not execute fallback research in this scope.
- Pending-approval boundary and no live/export/strategy DB mutation are visible in final artifacts.

## Verification
After approval, verification is research/evidence verification, not project-wide tests or formatters:
- Parse generated JSON manifests/summaries with JSON tooling.
- Inspect condition code against `strategy.txt` variables and buy/sell variable boundaries.
- Use evidence-local wrapper command shape from `.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py` with configs `oos-2025-q4-e32-config.json`, `oos-2022-e32-config.json`, `oos-2023-e32-config.json`, `oos-2024-e32-config.json`, `oos-2025-e32-config.json`, `oos-2026-e32-config.json`.
- Reconcile loop run DB rows, snapshots, CSV paths, and summary JSON for each candidate/period.
- Verify final comparison arithmetic against frozen baselines.
- Verify guardrails: no live/export/V3K/KHOPENAPI activity and no writes to operating strategy/loop DBs.

## Risks and mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| combined result mistaken for official OOS | invalid promotion argument | label combined only as portfolio/CSV simulation in every table/card |
| overfit from proxy tuning | false pass | max 3 candidates, fixed thresholds, period/Q4/trade/concentration checks |
| runner writes operating DB | guardrail breach | use wrapper and evidence-local sandbox; stop if a command targets `ai_strategy_loop/state/*.db` |
| candidate uses non-reproducible state | live-ineligible result | pre-run leakage review; reject unsupported prior-month/CSV/future/result dependencies |
| Q4/2026 interpretation error | wrong robustness conclusion | keep Q4 separate and mark 2026 as YTD through 2026-02-28 |
| all candidates fail | pressure to expand scope | write reject card only; fallback becomes separate follow-up |

## Handoff guidance
- This artifact is ready for Architect/Critic review or direct user approval.
- After approval, a bounded executor can run the research sequence; no team/ultragoal is needed unless OOS execution becomes long-running across multiple machines.
- Execution must not start until approval because official OOS and evidence generation are outside this planning-only stage.
