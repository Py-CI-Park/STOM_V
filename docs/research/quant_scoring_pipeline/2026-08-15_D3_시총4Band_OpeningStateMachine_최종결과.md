# D3 시총 4Band Opening State Machine 최종결과 (2026-08-15)

## 최종 판정

- D3: `NO_EVENT_QUALIFIED_D3_CANDIDATE`
- D4: `GATE_NOT_ENTERED`
- 경제적 성공: **아님**
- OOS·실전·자동채택 권한: **없음**
- Platform: `EXECUTION_FAILURES_PRESENT`

## Scope

- 기존 `_database/stock_tick_back.db`만 immutable read-only로 사용
- 신규 데이터 수집 없음
- C0 4Band 4/4 PASS
- Tick W0: `09:00:00 <= 시분초 < 09:30:00`
- W0 hash: `69b2d05c2fd682cdf3f61f78ef33fb0f18f6a3b962fe7e68973662760db9c97b`
- Development screen: 2023-11-14 1거래일
- Exit: 고정 baseline risk/time Exit

## Candidate Funnel

| 단계 | 수 | 결과 |
|---|---:|---|
| 5 Family × 4 Band × QMC 32 | 640 | 640/640 static/runtime/work/window 계약 PASS |
| 성과 비사용 exact max-distance pair | 40 | Cell당 2개 |
| Official engine direct-source snapshot | 40 | 40/40 exact source hash match |
| Metrics | 2 | 모두 표본 부족·음수 |
| No trades | 21 | Event 부재 |
| Execution error | 15 | terminal execution constraint |
| Monitor/runner timeout | 2 | terminal execution constraint |
| Rule-pass | 0 | 없음 |
| Bayesian APPROVE | 0/0 | Gate 미진입 |
| D4 BO eligible | 0 | `GATE_NOT_ENTERED` |

## 경제 결과

Metrics가 생성된 후보는 2개뿐이다.

| 후보 | Family/Band | 거래 | 평균 | 총수익률 | MDD | 판정 |
|---|---|---:|---:|---:|---:|---|
| `D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_cb7275dfee` | Absorption / `<3000` | 2 | -1.67% | -1.67% | 1.03% | 표본부족·음수 |
| `D3_COMPRESSION_CONFIRMED_BREAKOUT_MCAP_A_LT3000_f6320dda9d` | Compression / `<3000` | 4 | -0.48% | -1.93% | 4.01% | 표본부족·음수 |

양수 후보, 최소 10거래 후보, 2차 Fold 진입 후보가 모두 0이다.

## Typed failure 해석

17개 execution failure는 숨기거나 플랫폼 PASS로 바꾸지 않았다.

- Error 15
- Timeout 2
- Family별: Absorption 5, Opening mean-revert 4, Compression 3, Flow divergence 3, Failed breakout 2
- Band별: `<3000` 6, `>=10000` 5, `3000~5000` 4, `5000~10000` 2
- 40개 전체 source snapshot hash는 일치했다.
- 640 proposal·40 snapshot 생성과 official job submission은 성공했지만, 전 후보 실행성까지 플랫폼 PASS하지는 못했다.

117tick 후보의 one-day 300초 무진행을 관측한 뒤 PnL을 보지 않고 E2 비용 상한을 60tick으로 낮췄다. 최종 screen도 signal 부재 또는 실행비용 과다를 보였으므로 후보 주변 threshold 미세조정은 하지 않는다.

## 왜 Fold·Negative control·Bayesian·D4를 실행하지 않았는가

사전등록상 screen 최소 표본과 Rule-pass가 먼저다. 적격 후보가 0이므로:

- Rolling/Fold: `NOT_ENTERED_NO_EVENT_QUALIFIED_CANDIDATE`
- Timestamp/Symbol/Direction/Random controls: `NOT_ENTERED_NO_EVENT_QUALIFIED_CANDIDATE`
- Bayesian: `APPROVE_0_OF_0`
- Entry/Exit/Joint BO: `GATE_NOT_ENTERED`

이는 누락이 아니라 사전등록된 계획 중지다. 무거래·실행실패 후보를 Controls나 BO에 넣는 것은 연구비용만 늘리고 winner's curse를 악화한다.

## 결론

시총 4Band는 Population 관점에서 연구 가능했지만, 이번 5개 상태전이 Family는 기존 DB의 09:00~09:30 opening window에서 충분한 Event와 양의 개발 성과를 만들지 못했다. 시총 분할 자체가 Edge를 만들지는 않았다. D1/D2/Paired와 마찬가지로 자동채택 가능한 Robust 조건식은 0개다.

## Evidence

- `evidence/2026-08-15_mcap_census.json`
- `evidence/2026-08-15_d3_candidate_manifest.json`
- `evidence/2026-08-15_d3_engine_screen.json`
- `evidence/2026-08-15_d3_screen_decision.json`
- `utility/ai_agent/strategy/D3_OpeningStateMachine_시총4Band_20260815.txt`
