# 기존 DB Entry×Exit Paired 개선 연구 최종 결과 (2026-08-14)

> 사전등록: `2026-08-14_기존DB_entry_exit_paired_개선연구_사전등록.md`
> Screen: `evidence/2026-08-14_paired_exit_screen.json`
> Six folds: `evidence/2026-08-14_paired_exit_six_folds.json`
> 최종 판정: **`NO_ROBUST_ENTRY_EXIT_PAIR`**

## 1. 실행 완결성

| 항목 | 결과 |
|---|---:|
| Entry | 2 |
| 기존 Exit | 4 |
| Pair | 8 |
| 5일 screen 공식엔진 | 8/8 terminal+metrics |
| 6fold 총 evidence | 48 |
| 신규 공식엔진 jobs | 36/36 success |
| D2 baseline exact 재사용 | 12 |
| Buy/sell snapshot hash | 48/48 일치 |
| 운영 DB write | 0 |
| OOS/채택 권한 | 없음 |

36번째 job까지 모두 success가 된 직후 monitor wrapper의 3,600초 상한이 종료됐다. 결과는 각 job의 isolated `strategy.db/backtest.db/csv`와 dashboard terminal result에서 복구했고 `recovered_after_runner_timeout=true`로 봉인했다. 연구 job 자체 timeout·누락은 없다.

## 2. 5일 pair screen

| Entry | Exit | 거래 | 건당 % | 총수익 % | MDD % |
|---|---|---:|---:|---:|---:|
| VOL | baseline | 16 | +0.84 | +4.47 | 1.65 |
| VOL | S1(+3/-2/600s) | 17 | +1.05 | +4.45 | 1.16 |
| VOL | S2(+3/-1/600s) | 26 | -0.22 | -1.91 | 5.41 |
| VOL | hold300 | 15 | +1.30 | +3.91 | 0.96 |
| SPARSE | baseline | 22 | +0.18 | +1.02 | 3.04 |
| SPARSE | S1 | 27 | -0.02 | -0.08 | 4.58 |
| SPARSE | S2 | 30 | -0.26 | -2.58 | 5.62 |
| SPARSE | hold300 | 25 | -0.02 | -0.08 | 2.44 |

VOL에서는 S1/hold300이 국소 risk·건당 성과를 개선했지만 총수익은 baseline을 넘지 못했다. SPARSE는 모든 대체 exit가 5일 성과부터 악화됐다.

## 3. 6fold pair 판정

| Entry | Exit | 성공 fold | 합산 수익금 | 최대 MDD | Bayesian | 판정 |
|---|---|---:|---:|---:|---|---|
| VOL | baseline | 2/6 | -203,385원 | 13.40% | CONTINUE | REJECT |
| VOL | S1 | 0/6 | -1,069,272원 | 21.59% | REJECT | REJECT |
| VOL | S2 | 0/6 | -763,621원 | 26.88% | REJECT | REJECT |
| VOL | hold300 | 2/6 | -533,246원 | 15.54% | CONTINUE | REJECT |
| SPARSE | baseline | 2/6 | -693,353원 | 17.34% | CONTINUE | REJECT |
| SPARSE | S1 | 1/6 | -1,626,320원 | 20.61% | CONTINUE | REJECT |
| SPARSE | S2 | 1/6 | -1,826,782원 | 20.13% | CONTINUE | REJECT |
| SPARSE | hold300 | 2/6 | -1,070,045원 | 20.57% | CONTINUE | REJECT |

Rule-pass pair 0개, Bayesian `APPROVE` 0개, BO eligible 0개다.

## 4. 실패 원인 분해

### 4.1 고정 exit는 주원인이 아님

- 두 entry 모두 기존 baseline exit가 합산 손실이 가장 작다.
- S1/S2 barrier exit는 거래 회전과 손실을 늘렸다.
- 300초 exit는 일부 양수 월을 유지했지만 합산·MDD 경계를 넘지 못했다.

따라서 D1/D2 실패를 `Tick_S_902_905` 하나의 문제로 설명할 수 없다.

### 4.2 진입 edge·국면 의존이 주원인

- Exit를 바꿔도 양수 월 위치가 제한적이다.
- VOL은 2023-01/07, SPARSE는 2023-04/07 부근에서만 부분 양수다.
- 2022 월들은 대부분 손실이다.
- Tighter stop은 잘못된 진입의 손실 실현 빈도만 높였다.

현재 기존 DB에서 가장 강한 결론은 **샘플링된 entry 구조에 월별 지속 edge가 없다**는 것이다.

### 4.3 Platform 결함과 alpha 부재를 분리

P1~P7 플랫폼 결함은 v5.15.0에서 교정됐다. Exact source snapshot, isolated result DB/CSV, FDR, read-only GET, candidate identity가 모두 통과해 이번 pair 실패를 provenance 오류로 설명할 수 없다.

## 5. BO 판정

사전등록 BO 진입 조건:

```text
pair rule-pass AND Bayesian APPROVE
```

통과 pair가 없으므로 BO를 실행하지 않는다. 음수 pair 주변을 사후 최적화하는 것은 기존 DB 과최적화이므로 금지한다.

## 6. 최종 결론

| 질문 | 답 |
|---|---|
| 기존 DB만 사용했는가 | 예 |
| 3순위 신규 구조 연구를 완료했는가 | 예 |
| 4순위 BO gate를 평가했는가 | 예 |
| BO를 실행했는가 | 아니오 — 적격 pair 0 |
| 플랫폼 전수검사를 완료했는가 | 예, P1~P7 20/20 PASS |
| 플랫폼 개선 후 공식엔진을 다시 돌렸는가 | 예, paired 36 신규 jobs |
| Exit 변경이 실패를 구제했는가 | 아니오 |
| 최종 수익 조건식을 발견했는가 | 아니오 |

조건식 플랫폼은 재현·격리·권위 측면에서 개선됐지만, 현재 기존 DB에서 검증한 entry/exit family에는 견고한 경제적 edge가 없다.
