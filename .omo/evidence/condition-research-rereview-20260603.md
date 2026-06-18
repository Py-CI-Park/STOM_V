# STOM 조건식 자율진화 대시보드/프로세스 2차 검토 보고서

작성일: 2026-06-03  
대상: `http://127.0.0.1:8770/ui/`, `ai_strategy_loop/`, STOM 조건식 자율진화 연구 프로세스  
근거: `docs/AGENT_HANDOFF.md`, `docs/update_log/2026-06-03_tick_program_complete_handoff.md`, live dashboard/API, read-only SQLite, prior autoresearch report, 외부 검증 참고자료

## 1. 결론

현재 STOM 조건식 자율진화 대시보드와 전체 프로세스는 **인간 조건식에 근접한 후보를 자동으로 만들고, 백테스트/분석/정제하는 연구 시스템으로는 충분히 잘 개발되고 있다.** 특히 TICK T0~T4 이후에는 단순 LLM 생성기가 아니라 다음 폐루프가 실제로 닫혔다.

1. 넓은 tick 09:00~09:30 생성 유도
2. 공식 STOM 백테스트
3. 세대별 점수/곡선/보유수 관찰
4. edge ratio, feature importance, 시간대/시총/등락률 세그먼트 분석
5. 패배 세그먼트 avoid 피드백
6. BackFinder 원리 기반 seed 후보 발굴

다만 **“인간 조건식 수준을 이미 자동으로 달성했다” 또는 “초월했다”는 판정은 아직 불가능하다.** T0~T4는 인프라 완성 및 실DB smoke 증명이고, 다음 단계인 **토글 ON 다년 연구 run + 2022/2026 OOS 검증**이 아직 끝나지 않았다. 따라서 현재 상태의 정확한 판정은:

> 후보 개발/분석/정제 시스템은 충분히 성숙했다.  
> 수익 조건식 자동 생산 능력은 가능성이 높아졌지만, 인간 reference 대비 우위는 아직 OOS로 검증해야 한다.

## 2. Prior-report Audit

이전 보고서 `.omx/goals/autoresearch/condition-evolution-profit-research-20260602/research-report.md`의 큰 방향은 여전히 맞다. 즉, 시스템은 강한 연구 플랫폼이지만 overfitting 방어, 다기간 검증, promotion decision card가 필요하다는 결론은 유지된다.

현재 기준으로 바뀐 핵심은 관측성이다.

| 항목 | 이전 보고서 | 현재 read-only 확인 | 상태 |
|---|---:|---:|---|
| `loop_runs.db.runs` | 41 | 73 | 변경됨 |
| `generations` | 283 | 400 | 변경됨 |
| `equity_points` | 0 | 1943 | stale claim |
| `prompts` | 4 | 184 | stale claim |
| `stockbuy` | 311 | 408 | 변경됨 |
| `stocksell` | 309 | 405 | 변경됨 |

따라서 이전 보고서의 “프롬프트/자본곡선 영속화가 거의 없다”는 표현은 이제 그대로 쓰면 부정확하다. 더 정확히는 **영속화 기반은 생겼고 실제 데이터도 쌓였지만, 모든 run에서 일관되게 켜져 있는 promotion-grade evidence discipline은 아직 아니다**.

상세 matrix: `.omo/evidence/condition-research-claim-gap-matrix.csv`.

## 3. Current Local Evidence

### 3.1 Live Dashboard

확인 결과:

- `/health`: HTTP 200, `contract_version=2`.
- `/ui/`: HTTP 200.
- Playwright 실제 렌더: title `STOM AI · 조건식 자율 진화 대시보드`, body length `13656`.
- Screenshot artifact: `.omo/evidence/dashboard-ui-playwright.png`.
- `/runs`: 73개 run 반환.
- `/backtest_detail?run_id=tickwide_t0b&gen_no=1`: daily PnL, cumulative curve, drawdown, holdings 반환.
- `/edge_ratio?run_id=tickwide_t0b&fine_time=true`: pooled_trades `116`, global edge_ratio `1.4039`.
- `/feature_importance?run_id=tickwide_t0b&axis=change&fine_time=true`: B_* feature ranking 반환.

UI는 실제로 렌더되고, run selector에 `tickwide_t0b`, seed/OOS run들이 표시된다. 다만 콘솔에 Babel transformer 경고와 404 리소스 1건이 있어 정리 대상이다. 기능상 치명적이지는 않지만, 장시간 운영 대시보드로는 빌드/번들 정리가 필요하다.

### 3.2 Tickwide Evidence

`tickwide_t0b`는 T0 넓은 tick 생성의 중요한 증거다.

- gen1: `91` 거래
- final profit: `685127`
- max drawdown from detail payload: `1237550`
- peak holdings: `5`
- edge ratio global: `1.4039`
- losing segment example: 등락률 `상승` total_profit `-459417`
- strong segment example: `0905-0910×소형` total_profit `1250939`

이 수치는 “대시보드가 불필요 구간을 찾아 다음 생성에 환류할 수 있다”는 점을 뒷받침한다. 동시에 17거래일 smoke/탐색 성격이므로 최종 성능 판정은 아니다.

### 3.3 Architecture Fitness

현재 구현 상태는 인간 조건식 연구 흐름과 잘 맞는다.

- 생성: `ai_strategy_loop/brain/prompt.py`, `generator.py`, `filter_gate.py`, `segment_feedback.py`
- 채점: `ai_strategy_loop/fitness/score.py`
- 분석: `edge_ratio.py`, `feature_importance.py`, `adaptive_timing.py`, `backfinder_principle.py`
- 상태: `controller/state.py`, `loop_runs.db`, `loop_strategies.db`
- 대시보드: `dashboard/app.py`, `dashboard/frontend/analysis.jsx`, `chart.jsx`
- 공식 백테스트: `backtest/backtest.py`, `backtest/backengine_*`

중요한 불변식도 유지된다. 엔진, 하드게이트, `backtest/graph/`는 건드리지 않았다. V3K gates는 `3/6` 상태 그대로다.

## 4. External Research Refresh

검증 기준은 외부 자료와도 맞는다.

- PBO/backtest overfitting: https://scholarworks.wmich.edu/math_pubs/42/
- Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- TimeSeriesSplit: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- Optuna multi-objective: https://optuna.readthedocs.io/en/v3.4.1/tutorial/20_recipes/002_multi_objective.html
- Triple-barrier/meta-labeling reference metadata: https://www.econbiz.de/Record/-/10011841464
- Slippage modeling reference: https://www.backtrader.com/docu/slippage/slippage/

적용 결론:

- 많은 후보를 생성한 뒤 best만 보는 구조는 반드시 PBO/DSR류 보정이 필요하다.
- tick 단타 조건식은 slippage/체결지연/부분체결 민감도를 별도 stress로 봐야 한다.
- 단일 scalar score보다 profit, MDD, trade count, payoff, max hold, slippage sensitivity의 Pareto frontier가 더 적합하다.
- BackFinder 양성 라벨은 seed mining에는 좋지만, negative sample과 OOS precision이 없으면 promotion gate가 될 수 없다.

## 5. Gap Matrix Summary

### Confirmed

- 시스템은 연구 플랫폼으로 강하다.
- live dashboard/API는 작동한다.
- TICK T0~T4 인프라는 완료되어 넓은 생성, 분석, feedback loop가 가능하다.
- human reference corpus가 있고 benchmark로 쓸 수 있다.
- seed Tick_902는 여전히 강한 기준선이다.
- V3K는 offline/advisory로 남아야 한다.

### Changed

- 관측성 DB 상태는 좋아졌다. `prompts=184`, `equity_points=1943`.
- TICK 우선 재조준 후 `tickwide_t0b` 같은 실제 분석 가능한 run이 추가됐다.
- portable handoff `docs/AGENT_HANDOFF.md`가 생겨 Claude memory 의존이 줄었다.

### Unsupported

- “이미 인간 조건식을 자동으로 초월했다.”
- “T0~T4 smoke 결과만으로 최종 수익 조건식이다.”
- “BackFinder seed mining 결과가 곧 실전 edge다.”

### Needs More Evidence

- toggles ON multiyear run.
- 2022/2026 OOS split.
- PBO/DSR/Deflated Sharpe or equivalent overfit risk.
- slippage/execution stress.
- promotion/rejection decision card.

## 6. Roadmap

### P0

1. **토글 ON 다년 tick 연구 run**
   - `classification_generation_enabled`
   - `require_filter_gates`
   - `encourage_time_dispersion`
   - `few_shot_enabled`, `few_shot_source=seed_db`
   - `segment_feedback_enabled`
   - tick 09:00~09:30

2. **2022/2026 OOS 분리검증**
   - 2023~2025 탐색/튜닝
   - 2022, 2026 holdout/OOS
   - seed Tick_902와 직접 비교

3. **Promotion Decision Card**
   - seed 대비 profit/MDD/trade/max_hold/payoff
   - OOS pass/fail
   - PBO/DSR warning
   - slippage stress
   - 패배 세그먼트
   - 인간이 이해할 edge hypothesis

4. **청산/MDD 개선**
   - edge_ratio상 진입 edge는 있으나 mae_efficiency가 낮다.
   - 매도/손절/트레일/시간청산이 우선 개선 영역이다.

### P1

1. BackFinder `to_band_seeds`를 밴드 생성경로에 연결.
2. T3 시간창 span 분포를 대시보드 패널로 추가.
3. PBO/DSR/CVaR/Sortino를 graded/advisory 지표로 추가.
4. prompt/equity/hypothesis logging을 연구 profile에서 기본 ON.

### P2

1. Pareto frontier 기반 후보 선택.
2. slippage/latency/partial-fill stress.
3. ML factor model에 purged/embargo validation과 triple-barrier labels.
4. long-run failure taxonomy를 prompt/rubric으로 환류.

## 7. Human Condition-Expression Workflow

권장 workflow:

1. 인간 reference/seed를 benchmark로 고정한다.
2. AI는 seed를 복제하는 것이 아니라 시간대/시총/등락률 축에서 새로운 niche를 고르게 한다.
3. 공식 STOM 백테스트로 평가한다.
4. T1/T3/T4 분석으로 패배 구간과 no-op 조건을 찾는다.
5. segment_feedback으로 다음 세대 prompt에 avoid guidance를 넣는다.
6. 후보는 1개월 smoke가 아니라 multi-horizon/OOS로 판정한다.
7. promotion card가 통과할 때만 사람이 승인한다.

이 방식이면 시스템은 인간 조건식 제작을 **실질적으로 보조하고 확장할 수 있다.** 단, 자동 승인이나 자동 실전 배포는 금지해야 한다.

## 8. Safe Operating Playbook

- `final_approval` 또는 `export_winner` 호출 금지.
- 운영 `_database/strategy.db` 쓰기 금지.
- V3K gate advancement 금지.
- 신규 기능은 토글 기본 OFF.
- `taskkill /F /IM python.exe` 금지. 대시보드/worker는 PID 기준 외과적으로만 정리.
- 1개월 좋은 결과는 “후보”다. 다년/OOS 전에는 “수익 조건식”이라고 부르지 않는다.

## 9. Verification Record

Evidence files:

- `.omo/evidence/task-1-safety-snapshot.txt`
- `.omo/evidence/task-2-claim-audit.txt`
- `.omo/evidence/condition-research-claim-gap-matrix.csv`
- `.omo/evidence/task-3-local-refresh.md`
- `.omo/evidence/task-4-state-observability.md`
- `.omo/evidence/task-5-external-references.md`
- `.omo/evidence/dashboard-ui-playwright.png`

No source, runtime DB, protected result path, live broker, or V3K gate changes were made by this review.

## 10. Final Answer to the User Question

대시보드와 전체 프로세스는 **조건식 인간 고수의 조건식에 근접한 후보를 자동 개발하는 연구 시스템으로는 충분히 잘 진행되고 있다.** 특히 TICK T0~T4 이후에는 인간 reference의 tick 09:00~09:30 구조를 따라 넓게 생성하고, 결과를 세그먼트/feature/edge로 분석하고, 패배 구간을 다시 prompt로 환류할 수 있다.

하지만 **아직 “자동으로 인간을 능가하는 수익 조건식을 만든다”고 말할 단계는 아니다.** 그 주장은 다음 작업, 즉 토글 ON 다년 run과 2022/2026 OOS가 통과해야만 가능하다.
