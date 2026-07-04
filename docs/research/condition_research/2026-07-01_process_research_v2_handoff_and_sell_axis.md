# STOM 조건식 연구 프로세스 v2 전체 핸드오프 — 실전 검증, 파일 정리, 매도축 연구 방향

## 1. 한 장 요약

이 문서만 보면 현재 조건식 연구 프로세스가 어디까지 발전했는지, 2026-07-01 실전 검증에서 무엇을 했는지, 커밋되지 않은 파일을 어떻게 분류해야 하는지, 다음 연구를 어떤 방향으로 진행해야 하는지 알 수 있도록 정리한다.

| 항목 | 현재 결론 |
|---|---|
| 연구 목적 | 좋은 조건식 즉시 확정이 아니라, 좋은 조건식을 만들 확률을 높이는 반복 연구 프로세스 검증 |
| 최신 프로세스 | full parent buy/sell code Context Pack → Analysis Card v2 → multi-hypothesis 후보 → strict validation → 공식 백테스트 → 결과 환류 |
| 실전 검증 run | `process_research_v2_validation_20260701` 완료 |
| 시작 seed | `rr8_12_turnover_min_902=1.5` |
| 실행 엔진 | 64 engine 성공, 32 fallback 미사용 |
| 후보 수 | 4개, repair 2개 + discovery 2개 |
| 핵심 발견 | `거래대금증감 < -5_000_000_000` reject filter가 MDD를 크게 낮춤 |
| 가장 중요한 한계 | 이번 후보들은 buy-side reject filter 중심이며, sell-side 개선은 아직 별도 실험으로 실행하지 않음 |
| 다음 권장 방향 | buy-side threshold ladder와 별도로 **sell-only repair lane**을 추가해 give-back, MFE/MAE, 보유시간, trailing/stop 조건을 연구 |
| 안전 경계 | research-only, no export, no live, no final promotion |

## 2. 왜 매도 조건식 변경도 중요한가

매도 조건식 변경은 매우 타당한 다음 연구 방향이다. 이번 검증은 주로 매수 진입을 줄이는 reject filter 방식이었다. 이 방식은 위험 구간을 제거하는 데 효과가 있지만, 좋은 거래까지 같이 제거할 수 있어 거래수와 수익이 줄어드는 단점이 있다.

반면 매도 조건식 연구는 다음 문제를 직접 다룬다.

| 문제 | buy-side reject filter 접근 | sell-side repair 접근 |
|---|---|---|
| MDD 축소 | 위험 진입을 사전에 제거 | 진입 후 손실 확대/되돌림을 빠르게 차단 |
| 수익 보존 | 거래수 감소로 수익도 줄 수 있음 | 좋은 진입은 유지하고 청산만 개선 가능 |
| give-back | 간접적으로만 줄임 | 최고수익률 대비 반납, trailing, 보유시간 청산을 직접 개선 |
| MFE/MAE | 후보 생성 입력으로만 쓰임 | 매도 조건식 자체의 핵심 목표가 될 수 있음 |
| 연구 위험 | 너무 엄격하면 거래수 급감 | 너무 빠르면 수익 절단, 너무 늦으면 MDD 유지 |

따라서 다음 연구는 buy-side와 sell-side를 섞어 한 번에 바꾸기보다 아래처럼 분리하는 것이 안전하다.

| Lane | 변경 범위 | 목적 | 통과 조건 |
|---|---|---|---|
| buy-only repair | 부모 sell 고정, buy reject filter 1축만 변경 | 위험 진입 제거 | 거래수/수익 감소가 과도하지 않은 MDD 개선 |
| sell-only repair | 부모 buy 고정, sell 조건 1축만 변경 | give-back/MDD/보유시간 개선 | 거래수 보존, MDD/평균손익/보유시간 개선 |
| paired repair | 검증된 buy 축 + 검증된 sell 축을 조합 | 위험 진입 제거 + 청산 개선 | 각각 단독 효과가 확인된 뒤에만 시도 |
| promotion-review | 생성 없음 | frozen/fresh/OOS/WF/evidence health 검토 | research-only 후보의 승격 가능성만 검토, 최종 승격 금지 |

### sell-only 후보가 바꿔볼 만한 축

현재 부모 sell 조건식은 `수익률`, `최고수익률`, `보유시간`, `등락율각도`, `초당매도수량 - 초당매수수량`, `이동평균` 등을 사용한다. 다음 연구에서는 한 번에 하나의 축만 변경한다.

| sell mutation axis | 예시 가설 | 기대 효과 | 위험 |
|---|---|---|---|
| trailing give-back | `최고수익률 > 3 and 최고수익률 * 0.6 >= 수익률` 계수를 조정 | 수익 반납 감소, MDD 완화 | 너무 빠른 청산으로 큰 수익 절단 |
| hard stop | `수익률 <= -5.0` 또는 시가대비 음전환 손절 조건 조정 | 큰 손실 축소 | 노이즈 손절 증가 |
| hold-time stop | `보유시간 > 60` 이후 최저가 이탈 조건 조정 | 장기 보유 손실 축소 | 추세 유지 종목 조기 이탈 |
| orderflow exit | 초당매도수량/매수총잔량/등락율각도 조합 계수 조정 | 매도 압력 감지 개선 | 체결 강도 노이즈에 민감 |
| MA breakdown | 이동평균 이탈 청산 조건 계수 조정 | 추세 훼손 구간 청산 | 횡보 구간에서 과잉 청산 |

## 3. 프로세스 발전 이력

| 단계 | 과거 방식 | 문제 | 현재 v2 방식 |
|---|---|---|---|
| 조건식 전달 | 조건식 id 중심 | LLM이 실제 구조를 알 수 없음 | parent buy/sell 전문 + sha256 필수 전달 |
| 규칙 전달 | 요약 규칙 중심 | 변수/금지 규칙 누락 가능 | `strategy.txt`, `rules.txt`, `system_prompt`, `variables_reference`, `forbidden`, `examples` 포함 |
| 후보 생성 | 후보 1개 또는 deterministic filter 중심 | 한 번의 분석에서 가능한 가설을 충분히 탐색하지 못함 | 2~3개 이상 multi-hypothesis candidate pack |
| 분석 환류 | profit/MDD 중심 | 실패 원인이 다음 생성에 충분히 반영되지 않음 | Analysis Card v2: root-cause, avoid/prefer zone, segment contribution, risk note |
| 후보 권한 | 연구 후보와 승격 후보가 섞일 위험 | 실수로 export/live/final promotion 연결 가능 | research-only authority, promotion-review zero-generation |
| 평가 | prompt score 또는 후보 생성 성공 중심 | 실제 조건식 성과와 분리됨 | 공식 백테스트 receipt를 기준으로 후보 해석 |
| 관측 | 로그/단일 보고서 중심 | 사람이 전체 흐름 이해하기 어려움 | 연구 계획서/관리 보고서/결과 보고서/HTML dashboard |

## 4. 현재 process-research v2 표준 절차

```text
1. Seed Passport
   - 시작 seed와 comparator를 사람이 읽을 수 있는 이름으로 정리
   - buy/sell id, full code, sha256, baseline 성과, 사용 목적 기록

2. Research Prompt Context Pack
   - STOM 변수/규칙 원천 전체 포함
   - parent buy/sell 전문 포함
   - 이전 백테스트 결과와 분석 카드 포함
   - 250k prompt budget 안에서 최대한 상세히 구성

3. Baseline official replay
   - 현재 seed를 공식 백테스트로 다시 재현
   - baseline CSV와 metrics receipt 확보

4. Analysis Card v2
   - profit/MDD/trades/daily/win/payoff
   - 시간대, 시가총액, 등락률, 거래대금, 체결강도 국면
   - segment heatmap, feature importance, edge ratio, MFE/MAE
   - root-cause, avoid/prefer zone, mutation axis, risk note

5. Multi-hypothesis candidate pack
   - 후보 2~3개 이상
   - repair: 부모 구조 보존 + 실패 원인 1개 + mutation axis 1개
   - discovery: 기존 seed와 다른 coverage/feature family/market segment 강제
   - 앞으로 추가할 sell-only repair: 부모 buy 고정 + sell mutation axis 1개

6. Strict validation
   - full parent condition code 누락 차단
   - R_/S_ 누수 차단
   - authority smuggling 차단
   - prompt maturity와 fallback 분리

7. Official candidate backtests
   - 후보별 공식 백테스트 실행
   - prompt 점수가 아니라 실제 receipt 기준으로 해석

8. Result feedback
   - candidate ranking은 advisory only
   - 다음 threshold ladder / sell repair / promotion-review queue로 환류
   - export/live/final promotion 금지
```

## 5. 2026-07-01 실전 검증 run 요약

| 항목 | 값 |
|---|---|
| run id | `process_research_v2_validation_20260701` |
| process | `process-research` |
| preset | `research` |
| engine | 64 |
| fallback | false |
| start seed | `rr8_12_turnover_min_902=1.5` |
| baseline buy | `GATE_rr8_12_turnover_min_902_1_5_B` |
| baseline sell | `GATE_rr8_12_turnover_min_902_1_5_S` |
| context pack | `artifacts/process-research-validation-20260701/research_context_pack.json` |
| result report | `docs/research/condition_research/research_runs/process_research_v2_validation_20260701_result.md` |
| HTML report | `artifacts/process-research-validation-20260701/process_research_validation_report.html` |

### Baseline 공식 결과

| Profit KRW | MDD % | Trades | Daily | Win % | TPI |
|---:|---:|---:|---:|---:|---:|
| 518,822 | 20.54 | 175 | 0.7 | 52.57 | 1.13 |

### 후보 공식 결과

후보 표현식은 모두 buy-side reject filter다. 즉 조건이 참이면 `매수 = False`로 진입을 차단한다.

| 후보 | Lane | Reject filter | Profit KRW | ΔProfit | MDD % | ΔMDD | Trades | Win % | 판단 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `prv2_20260701_e64__cand001` | repair | `시가총액 < 700 and 등락율 < 3.0` | 518,822 | +0 | 20.54 | +0.00 | 175 | 52.57 | baseline/no-op에 가까움 |
| `prv2_20260701_e64__cand002` | discovery | `체결강도 < 120` | 419,904 | -98,918 | 14.68 | -5.86 | 121 | 51.24 | MDD 개선, 완화 ladder 후보 |
| `prv2_20260701_e64__cand003` | repair | `등락율 >= 7.2` | -25,668 | -544,490 | 12.56 | -7.98 | 55 | 43.64 | 과도한 차단, 후순위/제외 |
| `prv2_20260701_e64__cand004` | discovery | `거래대금증감 < -5_000_000_000` | 439,000 | -79,822 | 5.0 | -15.54 | 36 | 66.67 | 가장 강한 risk-control branch |

### 핵심 해석

`cand004`는 MDD를 20.54%에서 5.0%로 낮췄다. 하지만 거래수가 175에서 36으로 줄고 profit도 감소했으므로 즉시 승격 후보가 아니다. 다음 연구에서는 `거래대금증감` threshold ladder로 수익 보존과 MDD 축소 사이의 균형점을 찾아야 한다.

`cand002`는 `체결강도 < 120` 차단으로 MDD를 낮추면서 cand004보다 거래수를 더 보존했다. 이 축도 완화 ladder 후보로 유지한다.

## 6. 다음 연구 권장 설계

### 6.1 Buy-side threshold ladder

| 우선순위 | 축 | 후보 예시 | 목적 |
|---:|---|---|---|
| 1 | 거래대금증감 | `< -2B`, `< -3B`, `< -4B`, `< -5B`, `< -6B` | cand004의 MDD 개선을 유지하면서 거래수/수익 회복점 탐색 |
| 2 | 체결강도 | `< 100`, `< 110`, `< 120`, `< 130`, `< 140` | cand002의 완화 구간 탐색 |
| 3 | 결합 금지 | 거래대금증감 + 체결강도 동시 변경 | 단독 효과 확인 전에는 금지 |

### 6.2 Sell-only repair lane

다음 연구에 새로 추가해야 할 축이다.

| 단계 | 내용 |
|---|---|
| 입력 | 같은 baseline buy를 고정하고 parent sell 전문을 Context Pack에 넣음 |
| 분석 | MFE/MAE, 최고수익률 대비 반납, 보유시간, 손절 발생 위치를 Analysis Card v2에 추가 강조 |
| 후보 생성 | sell 조건식만 한 축 변경, buy는 완전히 동일 유지 |
| 후보 수 | sell-only 2~3개 + buy ladder 2~3개를 분리 평가 |
| 평가 | 공식 백테스트로 profit/MDD/trades/win/avg_hold_time/TPI 비교 |
| 금지 | buy와 sell을 동시에 바꾸는 paired repair는 단독 효과 확인 전 금지 |

### 6.3 Promotion-review

promotion-review는 조건식 생성이 아니다. 다음 조건을 만족할 때만 별도 검토한다.

- fresh/frozen holdout 결과 존재
- OOS/WF evidence 존재
- slippage는 advisory only로 표시
- evidence health가 충분함
- export/live/final promotion은 여전히 금지

## 7. 파일 정리와 커밋 결과

이번 정리에서는 `git add -A`를 쓰지 않고 코드/테스트, 연구 문서, evidence artifacts를 분리해 명시적으로 커밋했다. 현재 남은 untracked는 `.gjc/` runtime state와 `.omo/` 대량 evidence이며, 둘 다 일반 소스 커밋에서 제외했다.

### 7.1 완료 커밋 A — 프로세스 개선 코드와 테스트

| Commit | 포함 범위 |
|---|---|
| `332106f2 조건식 연구 컨텍스트팩과 다중 후보 루프 개선` | `ai_strategy_loop/brain/prompt.py`, `ai_strategy_loop/controller/condition_discovery.py`, `cli/condition_generator.py`, `cli/research_loop.py`, `cli/research_ranking.py`, dashboard observability, focused unit tests |

### 7.2 완료 커밋 B — durable 연구 문서

| Commit | 포함 범위 |
|---|---|
| `833bc650 조건식 연구 기록과 핸드오프 문서 정리` | Condition Passport, process-research v2 계획/관리/결과 보고서, research docs index, update logs, 현재 핸드오프 문서 계열 |

### 7.3 완료 커밋 C — 검증 evidence artifacts

| Commit | 포함 범위 |
|---|---|
| `942e8b28 조건식 연구 검증 산출물 보존` | `artifacts/process-research-validation-20260701/`의 Context Pack, Analysis/Card/Candidate receipts, official backtest receipts, HTML/screenshot, quality gates와 관련 연구 evidence artifacts |

### 7.4 보류한 파일군

| 분류 | 이유 |
|---|---|
| `.gjc/` | 현재 세션 workflow/runtime state다. Ultragoal ledger/checkpoint audit trail로 유지하고 일반 소스 커밋에는 포함하지 않는다. |
| `.omo/evidence/`, `.omo/plans/`, `.omo/drafts/` | 과거/별도 연구 evidence, WAL/로그/스크린샷, draft plan이 섞여 있다. 별도 OMO inventory 전까지 커밋하지 않는다. |
| `artifacts/*__pycache__*` | Python bytecode 생성물. 정리 후 커밋 제외했다. |
| protected paths | `_database/`, `_log/`, `*.db`, `backtest/graph/` 등은 source edit로 취급하지 않는다. 이번 protected path check에서는 변경 없음. |

### 7.5 최종 확인 명령

```powershell
git log --oneline -5
git status --short
git diff --check
git status --short -- _database _database_v3k_shadow _log backup "*.db" backtest/graph .omx/reports "v3k_settings*.json" _v3k_sidecar/v3k_gui_settings.json
```

## 8. 주요 evidence 경로

| 용도 | 경로 |
|---|---|
| 최종 결과 요약 | `artifacts/process-research-validation-20260701/final_summary.json` |
| full Context Pack | `artifacts/process-research-validation-20260701/research_context_pack.json` |
| prompt용 Context Pack | `artifacts/process-research-validation-20260701/research_context_pack_prompt.md` |
| 후보 카드 | `artifacts/process-research-validation-20260701/candidate_cards.jsonl` |
| 분석 카드 | `artifacts/process-research-validation-20260701/analysis_cards.jsonl` |
| prompt mutation receipt | `artifacts/process-research-validation-20260701/prompt_mutation_receipts.jsonl` |
| 공식 백테스트 receipt | `artifacts/process-research-validation-20260701/full_period_backtest_receipts.json` |
| fallback receipt | `artifacts/process-research-validation-20260701/engine_fallback_receipt.json` |
| safety receipt | `artifacts/process-research-validation-20260701/safety_receipt.json` |
| HTML dashboard | `artifacts/process-research-validation-20260701/process_research_validation_report.html` |
| 브라우저 검증 receipt | `artifacts/process-research-validation-20260701/dashboard_verification.json` |
| Ultragoal quality gates | `artifacts/process-research-validation-20260701/quality_gate_G001.json`, `quality_gate_G002.json`, `quality_gate_G003.json` |

## 9. 현재 완료 검증

이 문서의 `process_research_v2_validation_20260701` 실전 검증 run은 완료 상태다. 이후 별도로 시작된 "커밋/핸드오프 정리" Ultragoal은 이 문서 작성 시점에 leader-owned checkpoint를 진행 중일 수 있으므로, 아래 표는 **직전 연구 검증 run의 evidence**에만 적용한다.

| 검증 | 결과 |
|---|---|
| 직전 연구 검증 Ultragoal quality gates | `artifacts/process-research-validation-20260701/quality_gate_G001.json`, `quality_gate_G002.json`, `quality_gate_G003.json` 존재 |
| artifact validation | 통과 |
| `python -m py_compile artifacts/process-research-validation-20260701/run_process_research_validation.py` | 통과 |
| `git diff --check` 관련 문서/스크립트/HTML | 통과 |
| protected path status | 변경 없음 |
| browser HTML load | 200 OK 확인 |

## 10. 다음 연구 명령 초안

다음 실행은 sell-only repair를 포함해 분기하는 것이 좋다.

```text
/skill:ultragoal "STOM process-research v2 후속 research-only 검증을 실행한다. 시작 seed는 rr8_12_turnover_min_902=1.5이며 직전 run process_research_v2_validation_20260701의 Context Pack, Analysis Card v2, full backtest receipts를 입력으로 사용한다. no export, no live, no final promotion을 유지한다. 64 engine first, 32 fallback receipt 정책을 유지한다.

반드시 두 갈래를 분리한다.
1. buy-side threshold ladder: 거래대금증감 reject filter와 체결강도 reject filter를 각각 단일 축으로 완화/강화해 후보 2~3개 이상 생성한다.
2. sell-only repair lane: parent buy는 완전히 고정하고 parent sell만 한 축씩 변경한다. give-back, MFE/MAE, 보유시간, 최고수익률 대비 반납, hard stop, trailing 계수를 Analysis Card에서 뽑아 sell 후보 2~3개 이상 생성한다.

각 후보는 full parent buy/sell condition code와 sha256, hypothesis_id, mutation_axis, expected_effect, risk_note, prompt receipt를 포함해야 한다. buy와 sell을 동시에 바꾸는 paired repair는 단독 효과가 확인된 뒤 별도 후보로만 허용한다. 모든 후보는 strict validation 후 공식 백테스트로 평가하고 연구 계획서/관리 보고서/결과 보고서/HTML dashboard/safety receipt를 남긴다." 
```

## 11. 최종 결론

현재 연구 프로세스는 “id 기반 후보 생성”에서 “조건식 전문 + 규칙 전체 + 분석 카드 + 다중 후보 + 공식 백테스트 + 문서화” 구조로 발전했다. 2026-07-01 run은 그 구조가 실제로 작동함을 증명했다. 다만 지금까지의 후보는 buy-side reject filter 중심이므로, 다음 의미 있는 개선은 sell-only repair lane이다. 매도 조건식은 좋은 진입을 버리지 않고 MDD/give-back/보유시간을 개선할 수 있어, 현재 발견된 risk-control branch보다 수익 보존력이 높은 개선 후보를 찾을 가능성이 있다.
