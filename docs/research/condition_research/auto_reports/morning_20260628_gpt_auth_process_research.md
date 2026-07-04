# 아침 자동 보고 — 2026-06-28 05:19

> 범위 주의: 이 파일의 `PROMOTE 체크리스트`, `검증 결산`, `운용 결정 이력`은 대시보드 자동 보고서가 포함한 기존 historical/advisory 정보입니다. 이번 GPT OAuth 재실행의 직접 증거는 `4-A. 2026-06-27 GPT OAuth A/B/C 재실행 요약`, `artifacts/gpt-auth-process-research-20260627/final_gpt_auth_research_summary.json`, `gpt-auth-research-summary.json`, 각 `logs/*.log` 입니다. 이번 작업은 research-only이며 운영 승격·export·live 근거가 아닙니다.

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

- gptauth_C_review_20260627 (3세대, 최고 -14,492,886)
- gptauth_B_research_20260627 (18세대, 최고 174,904)
- gptauth_A_fast_20260627 (8세대, 최고 -2,290)
- gptauth_smoke_20260627 (1세대, 최고 -580,680)
- ovn_anchor_20260627_resume_r8 (23세대, 최고 3,089,180)
- ovn_anchor_20260627_resume_r7 (23세대, 최고 2,873,814)
- ovn_anchor_20260627_resume_r6 (23세대, 최고 2,617,990)
- ovn_anchor_20260627_resume_r5 (22세대, 최고 2,304,808)


## 4-A. 2026-06-27 GPT OAuth A/B/C 재실행 요약

| 항목 | 결과 |
|---|---|
| 목적 | OAuth 재로그인 후 원래 GPT 기반 A/B/C 연구 루프 재실행 |
| 인증 | `oauth_status` authenticated true, proxy smoke `STOM_OK` HTTP 200 |
| smoke | 1세대 생성/백테스트 성공, gate 통과 없음 |
| A `fast-discovery` | 8세대 생성/백테스트 성공, hard gate winner 없음 |
| B `process-research` | 18세대 생성/백테스트 성공, hard gate winner 없음 |
| C `promotion-review` | 3세대 생성/백테스트 성공, hard gate winner 없음 |
| GPT-auth best | `gptauth_B_research_20260627` gen10 profit 174,904 / MDD 4.30 / trades 33 / daily 0.1, gate 미통과 |
| 이전 fallback best | `rr8_21_trail_keep=0.7` profit 3,089,180 / MDD 18.84 / trades 165 / daily 0.70 |
| 결론 | OAuth 루프는 정상 복구됐지만, 이번 GPT 생성 후보는 이전 fallback 기준선을 넘지 못함 |
| 안전 경계 | advisory 연구 전용, export/live/final promotion 없음 |

### GPT-auth 단계별 성과

| 단계 | run id | 세대 | best 기준 | best profit | gate winner | 해석 |
|---|---|---:|---|---:|---:|---|
| Smoke | `gptauth_smoke_20260627` | 1 | gen0 | -580,680 | 0 | 인증/생성/백테스트 연결 확인용 |
| A | `gptauth_A_fast_20260627` | 8 | best score gen6 | -1,855,006 | 0 | 후보 생성은 됐지만 전부 손실/빈도/MDD 문제 |
| B | `gptauth_B_research_20260627` | 18 | best score gen3 / best profit gen10 | 174,904 | 0 | 소폭 흑자 후보는 있었으나 일평균 거래수 부족으로 gate 미통과 |
| C | `gptauth_C_review_20260627` | 3 | best score gen2 | -14,492,886 | 0 | promotion-review 생성 후보는 과다거래/MDD로 부적합 |

> 이번 GPT-auth 재실행은 “인증 복구와 생성형 루프 동작”은 검증했지만, “새로운 우수 조건식 발견”은 실패했습니다. 다음 연구는 fallback best의 theta를 프롬프트 seed/evidence로 더 강하게 제공하거나, GPT 생성 후보의 시간대/거래빈도 제약을 재설계하는 방향이 필요합니다.

> 안전 확인 영수증: `artifacts/gpt-auth-process-research-20260627/safety_receipt.json` (`allPassed=true`, nonrelease sync/diff check/protected paths/driver compile/dashboard health).
## 5. 운용 결정 이력

- complement — V6 포트폴리오(complement): THETA(과거적합 train+10.97M) + T2C3(09:25 시간확장, OOS/WF/슬리피지 THETA 능가) 2-전략 운용. train 상관 0.92·분산이득 7.3% 미미 — 근거는 레짐 상보성: 2026형 저거래장 T2C3 +400,701 vs THETA +164,602(+143%). 평상시 동행+위축장 T2C3 헤지. 둘 다 V1~V5 완주. 카드: 2026-06-13_v6_portfolio_decision_card.md

> 자동 생성(P-C) — 수치는 전부 advisory, 판정 규율은 OOS/사전선언 기준.