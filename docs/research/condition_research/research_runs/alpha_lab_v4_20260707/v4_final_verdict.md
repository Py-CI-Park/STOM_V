# 알파 랩 v4 — R3 OOS 블라인드 판정: **성공** (정적 등가중 앙상블, 타이밍 아님)

> 봉인: `preregistration_v4.json` (sha `87821aaa…`) / `v4_ensemble_frozen.json` (sha `111f5180…`) — 실행 전·후 `alpha_lab.registry.verify_seal` 통과
> OOS 봉인창: **2025-01 ~ 2026-02**(14개월, `bt_full_end=20260227`=DB 실측 최대일자로 절삭) — R3에서 최초이자 유일하게 개봉, 봉인 구성별 각 1회, 재시도 0회
> 엔진 예산: 봉인 ≤60 — 이번 R3 **4회**(챔피언당 정확히 1회) + R0 5회 = 누적 **9/60**
> 산출물: `v4_oos_verdict.json`(수치 원장, 본 문서의 모든 숫자 출처) / 본 문서(관리자 판독용)
> n_trials: `n_trials_ledger.jsonl`에 `V4E` 배치 `alp_v4_r3_oos_chunk1_20260707+chunk2_20260707` n=4 append 완료(V4E 누적 9)

## 결론 (3줄)

1. **판정 = 성공(primary 규칙 충족).** `ensemble_a_static_equal`(4챔피언 always-on 원본을 1/4 등가중 합산, 타이밍 오버레이 없음)이 OOS(calmar **5.2845**, MDD 493,591원)로 OOS 최선 단일 챔피언 always-on(`RR8_0`, calmar 3.8259, MDD 757,275원)을 초과했다.
2. **배포 후보 = `ensemble_a_static_equal`만.** 적응형 합산(b), 레짐-로테이션(c), 단일 적응형(4/4 챔피언 전부)은 OOS에서 always-on 대비 개선에 실패했다 — 성공은 순수 **다각화(비상관 손익 상쇄)** 효과이지, 설계 문서가 기대한 타이밍 효과가 아니다.
3. **정직한 반전 2건**: (i) discovery 창에서 `ensemble_a`는 11개 구성 중 8위였으나 OOS에서 1위로 뒤집혔다(discovery 순위가 OOS를 예측 못함). (ii) `GPTAUTH_G8`은 discovery에서 게이트 실패(mdd 77.05%)였으나 OOS에서 게이트 통과(mdd 15.14%)로 반전 — 이 반전이 상보적 다각화 가설을 실현시킨 핵심 축이다.

## 1. 판정 규칙 적용 (봉인, `preregistration_v4.json.success_rule`)

| 규칙 | 조건 (봉인 원문) | 결과 |
|---|---|---|
| **primary** | OOS에서 (수익/MDD) 또는 calmar이 최선 단일 챔피언 always-on 초과 구성 ≥1 | **충족** — `ensemble_a_static_equal` (calmar 5.2845 > 3.8259) |
| partial | 단일 적응형이 always-on 대비 MDD 유의 개선(다년 재현) | 해당 없음(primary 충족으로 판정 확정) — 참고: 4/4 챔피언 전부 OOS에서 오히려 악화(아래 §4) |
| fail | 적응형·앙상블 어느 것도 개선 없음 | 미해당 |

**최종 판정: `success`** (`v4_oos_verdict.json.verdict = "success"`, `verdict_rule_applied = "primary"`)

## 2. 관리자 표 — 발견창(2022-03~2024-12, 34개월) vs OOS(2025-01~2026-02, 14개월)

단위: 수익/MDD = 원(월별 P&L 누적곡선 peak-drawdown 관례, `risk_adjusted_metrics`), calmar = 수익/MDD.

| 구성 | 발견 수익 | 발견 MDD | 발견 calmar | OOS 수익 | OOS MDD | **OOS calmar** |
|---|---:|---:|---:|---:|---:|---:|
| single_alwayson[RR8_12] | 12,631,722 | 668,472 | 18.896 | 2,652,432 | 873,720 | 3.036 |
| **single_alwayson[RR8_0]** (발견·OOS 공통 최선 단일) | 11,404,295 | 578,298 | **19.720** | 2,897,270 | 757,275 | **3.826** ← baseline |
| single_alwayson[RR8_21] | 11,134,615 | 606,871 | 18.348 | 3,444,287 | 1,204,437 | 2.860 |
| single_alwayson[GPTAUTH_G8] | -6,932,292 | 10,060,666 | -0.689 | 1,439,459 | 1,199,665 | 1.200 |
| single_adaptive[RR8_12] | 11,175,622 | 662,395 | 16.872 | 1,990,655 | 1,415,148 | 1.407 |
| single_adaptive[RR8_0] | 8,678,271 | 873,141 | 9.939 | 2,682,253 | 859,394 | 3.121 |
| single_adaptive[RR8_21] | 7,819,114 | 606,871 | 12.884 | 1,597,623 | 2,144,669 | 0.745 |
| single_adaptive[GPTAUTH_G8] | -93,519 | 1,772,830 | -0.053 | 17,331 | 1,199,665 | 0.014 |
| **ensemble_a_static_equal** | 7,059,585 | 599,845 | 11.769 (발견창 8위) | **2,608,362** | **493,591** | **5.2845 (OOS 1위, 승자)** |
| ensemble_b_adaptive_sum | 6,894,872 | 450,277 | 15.313 | 1,571,966 | 1,132,640 | 1.388 |
| ensemble_c_regime_rotation | 11,419,954 | 662,395 | 17.240 | 1,727,516 | 1,207,774 | 1.430 |

원자료: `v4_oos_verdict.json.discovery_vs_oos_comparison` / `.per_config_oos` / `v4_assembly_report.json.discovery`.

## 3. 배포 후보 원문 (`ensemble_a_static_equal`)

4개 챔피언의 **원본 always-on 매수/매도식**(변경 없음, R0/R1/R2가 이미 확정한 코드 그대로)을 **1/4 등가중**으로 병행 운용한다. 코드 조합·수정 없음 — 각 챔피언을 그대로 동일 비중으로 나란히 돌리고 손익을 합산하는 것 뿐이다.

| slug | human_name | source_doc | buy_sha256 | sell_sha256 |
|---|---|---|---|---|
| RR8_12 | OOSStable_Open902_TurnoverMin_v1 | `condition_passports/rr8_12_turnover_min_902_1.5.md` | `348c5181…` | `8ef01e0e…` |
| RR8_0 | CapLimited_2500_Comparator | `condition_passports/rr8_0_cap_max_2500.md` | `3d14a1f4…` | `8ef01e0e…` |
| RR8_21 | ProfitLead_TrailKeep070_2025Comparator | `condition_passports/rr8_21_trail_keep_0.7.md` | `157b58b0…` | `01a1673b…` |
| GPTAUTH_G8 | GPTGen8_HighCoverage_FailedProfitContext | `condition_passports/human_seed_gptauth_B_gen8.md` | `83e7322e…` | `4ed51bb1…` |

가중 스킴: `weighting_scheme = equal_1_over_n`(봉인, `v4_ensemble_frozen.json`). 조합 함수: `alpha_lab.ensemble.portfolio.static_equal`(순수함수, 매월 4개 챔피언 원본 손익의 1/4 평균).

## 4. 정직한 한계 (전부 `v4_oos_verdict.json.honest_notes` 원문 근거)

1. **적응형 타이밍은 OOS에서 전원 역효과.** lookback=2 워밍업(202501~202502)이 하필 `GPTAUTH_G8`의 창 전체 최대 손실월(202501, −1,199,665)을 그대로 통과시켜(워밍업 중엔 무조건 원본 유지) 낙폭을 막지 못했고, 이후 회복 흑자월들만 FLAT 처리해 수익만 깎았다(같은 MDD, 수익 1,439,459→17,331). `RR8_12`(−61.97%)·`RR8_21`(−78.06%)도 연속 손실 직후 반등월을 FLAT 처리해 낙폭을 못 메운 동일 기제. 유일하게 `RR8_0`만 −13.49%로 상대적으로 덜 나쁘지만 여전히 악화.
2. **discovery 순위가 OOS 승자를 예측하지 못했다.** `ensemble_a`는 발견창 11개 구성 중 8위(calmar 11.77)로 당시엔 눈에 띄지 않았다. 파라미터(가중·lookback·전환규칙)는 발견창에서만 확정해 봉인했으므로 이 반전은 **사후 파라미터 조정이 전혀 없는 상태**에서 나온 결과다(SealViolation 규율 위반 없음) — 다만 "발견창 최상위 구성이 OOS 승자"라는 순진한 기대는 반증됐다는 점을 정직히 기록한다.
3. **GPTAUTH_G8의 게이트 반전.** discovery mdd 77.05%(게이트 실패) → OOS mdd 15.14%(게이트 통과). 동일 조건식의 게이트 통과 여부가 창마다 뒤집힌다 — R0/R1/R2가 게이트 실패에도 상관 진단(corr 0.077~0.308)에 근거해 1차 앙상블에 포함시킨 결정이 이 반전을 포착할 수 있었던 전제 조건이었다.
4. **OOS 단일 창, 전환비용 미모델.** `ensemble_a`는 always-on 병행이라 로테이션 전환비용 자체가 없지만(감독형 배포 전제 원 설계는 (c)에 해당하는 caveat), 창 하나(14개월)의 결과이며 재시도 없이 확정한 결과다.
5. **척도 주의**: 본 표의 MDD/calmar는 월별 P&L 누적곡선의 원화 peak-drawdown 관례(`risk_adjusted_metrics`)이며, 엔진이 보고하는 equity MDD%(예: RR8_12 OOS 13.33%, RR8_0 17.34%, RR8_21 18.84%, GPTAUTH_G8 15.14% — `v4_oos_verdict.json.engine_runs.per_champion`)와는 다른 척도다. 두 척도 모두 정확하지만 잣대가 다르다(`v4_assembly_report.json` honest_notes와 동일 주의사항 승계).
6. **TICK902U3 제외 유지.** R0 discovery 백테 타임아웃(300s)으로 monthly_pnl이 없어 v4_ensemble_frozen.json 구성에서 이미 제외됐고 R3도 동일하게 4챔피언만 백테했다(재탐색 없음).

## 5. 배포 규칙 (감독형, 초안)

- 자본을 4등분해 `RR8_12`/`RR8_0`/`RR8_21`/`GPTAUTH_G8` 원본 always-on 코드를 **변경 없이** 병행 운용(리밸런싱·전환 로직 불필요 — 모두 always-on, 로테이션 아님).
- 타이밍 오버레이(적응형)는 **적용하지 않는다** — OOS에서 4/4 챔피언 전부 역효과였다(§4-1).
- 모니터링 권고: (a) `GPTAUTH_G8` 게이트 상태(MDD%) 분기별 재확인 — discovery↔OOS 반전 전례가 있음, (b) 4챔피언 월별 상관 재계산 — 상관 상승 시 다각화 이득 축소 가능.
- 이 판정은 단일 OOS 창(14개월) 기준이며, 추가 검증(R4 패키지 단계) 전에는 감독 없는 완전 자동 배포를 권하지 않는다.

## 6. 예산·무결성 준수

- 엔진 사용: 이번 R3 4회(챔피언당 정확히 1회, 재시도 0) — 청크 2개(2쌍씩), `STOM_CLI_DB_STRATEGY=`로컬 `_database/strategy.db`(wt-dev 무접촉), `--fail-fast-timeout`. 청크 간 프로세스 확인 완료(잔존 warm 엔진 프로세스 0, `tasklist`/`Win32_Process` 실측).
- 봉인 검증: 실행 전·후 `preregistration_v4.json`(sha `87821aaa…`) + `v4_ensemble_frozen.json`(sha `111f5180…`) `verify_seal` 통과. 파라미터(가중·lookback=2·전환규칙) 재추정 없음 — 봉인값 그대로 적용.
- 원장: `n_trials_ledger.jsonl`에 V4E n=4 append(누적 V4E=9, 프로그램 총합=9). 이중 장부 없음.
- 무결성 교차검증: `monthly_pnl_from_csv(csv)` 합계 == 엔진 `generation.profit` 4/4 정확 일치(diff=0.0, `v4_oos_verdict.json.engine_runs.crosscheck`).
- git 커밋 없음(오케스트레이터 소관). `backtest/graph/` 미접근. `_database`는 git-ignored 로컬 사본.
