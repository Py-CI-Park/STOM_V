# 아침 자동 보고 — 2026-06-28 01:56

> 범위 주의: 아래 `PROMOTE 체크리스트`, `검증 결산`, `운용 결정 이력`은 대시보드 자동 보고서가 포함한 기존 검증/운용 이력입니다. 이번 2026-06-27 overnight 작업의 직접 증거는 `4-A. 2026-06-27 overnight process-research 실행 요약`과 `artifacts/overnight-process-research-20260627/final_research_summary.json`, `anchor.jsonl`, 관련 로그입니다. 이번 작업은 advisory 연구이며 운영 승격·export·live 증거가 아닙니다.

## 1. PROMOTE 체크리스트

| 조건 | 상태 | 근거 |
|---|---|---|
| V3 두 OOS 연도 모두 흑자 | ✅ | 2022 2,097,751 / 2026 164,602 |
| V3 합산 후보 ≥ 합산 시드 | ✅ | 2,262,353 vs 1,919,273 |
| V3 후보 maxMDD ≤ 시드 | ✅ | 14.70 vs 15.63 |
| V3 연 20거래 | ⚠️ | 2022 55 / 2026 9 — 2026 창 2개월 구조 한계(V4 표본으로 보강) |
| V1 DSR ≥ 0.5 (advisory) | ✅ | 0.945 (n_trials 80) |
| V1 MC P(흑자) ≥ 0.95 | ✅ | 1.0 |
| V2 플라시보 전 표본 상회 | ✅ | 표본 12종 · 백분위 1.0 |
| V5 합산 2틱 불리에도 흑자 | ✅ | 2틱 유지율 34% |
| V5 최신 구간 마진 | ⚠️ | 2026 단독 손익분기 < 2틱 |
| V4 정책 누적 비열등 | ✅ | 5,766,611 vs 5,687,429 (4창) |

> ⚠️ V1: 후보 풀 평균 상관 0.93 > 0.7 — 후보들이 사실상 쌍둥이라 PBO가 과적합을 과소평가할 수 있음(유효 독립 후보 ≈ 1.1)
> ⚠️ V5: 2026 OOS 단독 손익분기 1.21틱 — 얇은 마진

## 2. 검증 결산

- 동결 후보: gen7 THETA_seed_902905_06_B — train 손익 10,965,479 · MDD 10.04 · 272건 · payoff 1.53
- V1 과적합: DSR 0.945 (n_trials 80) · PBO 0.343 · MC P(흑자) 1.0
- V3 OOS 2022: 후보 2,097,751(55건·MDD 13.75) vs 시드 2,110,382(MDD 13.11)
- V3 OOS 2026: 후보 164,602(9건·MDD 14.70) vs 시드 -191,109(MDD 15.63)
- V2 플라시보: 표본 12종 전부 하회 — 후보가 플라시보 전 표본 상회 + 플라시보 중앙값 음수 — 손익의 원천은 진입 신호(우연/매도식 단독 아님)
- V5 슬리피지(합산 330건): 1틱 유지 67% · 2틱 34% · 손익분기 3.03틱
- M1 중복도: jaccard 0.8882 — 사실상 동일 거래 — '보완'은 동일 베팅 2배와 같음(대체 검토)
- C8 체결: 추격 의존 거래 5.1% · 의존 수익비중 20.1%
- M10 서킷: 당일 손실 2건 도달 시 잔여 거래 중단 → x1.0238
- M11 사이징: 권고 배수 x1.471
- V4 walk-forward(4창): 정책 누적 5,766,611 vs 시드 5,687,429

## 4. 최근 완료 run

- ovn_anchor_20260627_resume_r8 (23세대, 최고 3,089,180)
- ovn_anchor_20260627_resume_r7 (23세대, 최고 2,873,814)
- ovn_anchor_20260627_resume_r6 (23세대, 최고 2,617,990)
- ovn_anchor_20260627_resume_r5 (22세대, 최고 2,304,808)
- ovn_anchor_20260627_r3 (23세대, 최고 1,639,150)
- ovn_anchor_20260627_r2 (25세대, 최고 1,288,813)
- ovn_anchor_20260627_r1 (25세대, 최고 889,434)
- overnight_A_fast_20260627 (8세대)

## 4-A. 2026-06-27 overnight process-research 실행 요약

| 항목 | 결과 |
|---|---|
| 목적 | 6~8시간 무개입 조건식 연구: A fast-discovery → B process-research → C promotion-review/read-only |
| 1차 경로 | `gpt_auth` 토큰 만료(`refresh_token_invalidated/token_expired`)로 LLM 생성형 A/B/C 루프 중단 |
| 대체 경로 | LLM 0회 `overnight_anchor_mutation` + resume runner로 검증된 `seed_902905` 앵커 변이/재백테스트 진행 |
| 총 평가 후보 | 180개 |
| 게이트 통과 후보 | 105개 |
| 최상위 후보 | `rr8_21_trail_keep=0.7` |
| 최상위 성과 | profit 3,089,180 · MDD 18.84 · trades 165 · daily 0.70 |
| 최상위 theta | `cap_max=3000`, `strength_min=70`, `window_end=90700`, `take_hard=9`, `trail_start=3`, `trail_keep=0.7` |
| 안전 경계 | advisory 연구 전용, export/live/final promotion 없음 |

### Top process-research 후보

| 순위 | label | profit | MDD | trades | daily | 해석 |
|---:|---|---:|---:|---:|---:|---|
| 1 | `rr8_21_trail_keep=0.7` | 3,089,180 | 18.84 | 165 | 0.70 | 현재 최고 손익, MDD도 25 이하 |
| 2 | `rr8_12_turnover_min_902=1.5` | 3,062,696 | 12.87 | 190 | 0.80 | 최고 안정성 후보, MDD가 가장 낮은 상위권 |
| 3 | `rr8_0_cap_max=2500` | 3,047,522 | 17.34 | 145 | 0.60 | 시총 상한 축소가 유효한 후보 |
| 4 | `rr8_4_strength_max=250` | 3,040,172 | 19.01 | 164 | 0.70 | 강도 상한 축소 축도 유효 |
| 5 | `rr7_3_strength_min=70` | 2,873,814 | 20.83 | 165 | 0.70 | r8 개선의 기반 앵커 |

> 이 결과는 연구용 advisory 증거입니다. promotion-review는 후보/evidence health를 읽기 전용으로 정리하는 단계이며, 운영 승격·export·live는 별도 승인 전까지 차단 상태입니다.

> 실행 주의: 1차 A/B/C LLM 루프는 `artifacts/overnight-process-research-20260627/logs/process_a_fast.log`의 `refresh_token_invalidated/token_expired`로 중단되었습니다. fallback round 4는 monitor timeout 때문에 `round_done` 없이 후보 16개만 기록되었고, 이후 resume runner가 best r4 후보에서 중복 theta를 제외하고 r5~r8을 완료했습니다.
> 안전 확인 영수증: `artifacts/overnight-process-research-20260627/safety_receipt.json` (`allPassed=true`, nonrelease sync/diff check/protected paths/driver compile/dashboard health).

## 5. 운용 결정 이력

- complement — V6 포트폴리오(complement): THETA(과거적합 train+10.97M) + T2C3(09:25 시간확장, OOS/WF/슬리피지 THETA 능가) 2-전략 운용. train 상관 0.92·분산이득 7.3% 미미 — 근거는 레짐 상보성: 2026형 저거래장 T2C3 +400,701 vs THETA +164,602(+143%). 평상시 동행+위축장 T2C3 헤지. 둘 다 V1~V5 완주. 카드: 2026-06-13_v6_portfolio_decision_card.md

> 자동 생성(P-C) — 수치는 전부 advisory, 판정 규율은 OOS/사전선언 기준.