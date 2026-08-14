# 기존 DB Entry×Exit Paired 개선 연구 사전등록 (2026-08-14)

> Trigger: D2 `NO_ROBUST_FAMILY`, 플랫폼 감사 원인 R5
> Branch: `research/platform-improvement-paired-exit-20260814`
> 권위: development diagnostic only, no OOS, no adoption
> 데이터: 현재 존재하는 stock tick DB만 read-only 사용

## 1. 질문

D1/D2가 하나의 고정 매도식 `Tick_S_902_905`만 사용했기 때문에 진입식 성과와 exit 정책 효과가 혼입됐는가?

## 2. 고정 Entry

| ID | 근거 |
|---|---|
| `D2_VOL_EXPANSION_BREAKOUT_04_269804ee` | D2 5일 +4.47%, 6fold 2/6 |
| `D2_SPARSE_CONFIRMED_BREAKOUT_01_fc007ca8` | D2 5일 +1.02%, 6fold 2/6 |

Entry source·parameters는 동결한다.

## 3. 기존 DB Exit library

| Exit | 구조 |
|---|---|
| `Tick_S_902_905` | 기존 adaptive/시간 청산 기준선 |
| `QSP12_tick_S1` | +3% / -2% / 600초 / 09:28 |
| `QSP12_tick_S2` | +3% / -1% / 600초 / 09:28 |
| `QSP9_M3_tick_S_hold300` | 300초 / 09:28 시간청산 |

모두 현재 `_database/strategy.db`에 존재하는 source를 isolated per-job snapshot으로 복사해 사용한다. 운영 DB는 쓰지 않는다.

## 4. Pair budget

- Entry 2 × Exit 4 = 8 pairs
- 사전 screen 8회
- 개발 fold 8 × 6 = 48회
- 동시 실행 최대 4 jobs
- 요청 engines 16, 실제 worker 수는 receipt에 기록

## 5. 기간

### Screen

`20231114~20231121`, 09:00~15:29 요청. 실제 DB availability 범위만 엔진이 읽는다.

### 6 development folds

| Fold | 기간 |
|---|---|
| DEV_202204 | 20220401~20220430 |
| DEV_202207 | 20220701~20220731 |
| DEV_202210 | 20221001~20221031 |
| DEV_202301 | 20230101~20230131 |
| DEV_202304 | 20230401~20230430 |
| DEV_202307 | 20230701~20230731 |

모두 기존 DB 개발 evidence다.

## 6. Pair 판정

Fold 성공:

- 공식 엔진 `success`
- 거래 20건 이상
- 총수익률 > 0
- 평균수익률 > 0
- MDD <= 15%

Pair rule-pass:

- 성공 fold 4/6 이상
- 6fold 합산 수익금 > 0
- 최대 MDD <= 15%
- 실제 buy/sell source hash 전 fold 일치

Bayesian posterior는 별도 기록하며 `CONTINUE`이면 statistical approval로 부르지 않는다.

## 7. BO gate

- Pair rule-pass + Bayesian posterior `APPROVE`일 때만 저차원 BO 허용
- Rule-pass지만 posterior `CONTINUE`이면 BO 중지
- 통과 pair가 없으면 현 기존 DB에서 entry와 exit 양쪽 모두 견고하지 않은 것으로 연구를 종결

## 8. 실패 원인 분해

| 결과 | 해석 |
|---|---|
| 대체 exit가 robust | 기존 fixed exit가 주요 실패 원인 |
| 월별 양수 위치만 변함 | regime dependence가 주요 원인 |
| 전체 exit에서 동일 음수 | entry signal edge 부재가 주요 원인 |
| 거래만 감소·MDD 개선 | risk control은 개선되나 alpha 없음 |
