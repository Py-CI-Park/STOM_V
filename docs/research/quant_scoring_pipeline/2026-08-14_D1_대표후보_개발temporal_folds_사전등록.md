# D1 대표후보 개발 temporal folds 사전등록 (2026-08-14)

> 선행: `SECOND_STAGE_CANDIDATES`, `DETERMINISTIC_REPRESENTATIVES`
> 성격: 선택 fixture보다 과거인 개발용 temporal cross-check. 최종 OOS가 아님.

## 1. 동결 후보

| family | candidate |
|---|---|
| BOOK_IMBALANCE | `D1_BOOK_IMBALANCE_01_a0e44d3c` |
| FLOW_SURGE | `D1_FLOW_SURGE_04_b506a923` |
| MOMENTUM_QUALITY | `D1_MOMENTUM_QUALITY_07_da23c5ff` |

후보 source·문턱·family는 결과를 본 뒤 변경하지 않는다.

## 2. 고정 개발 folds

| fold | 기간 |
|---|---|
| `DEV_202303` | `20230301~20230331` |
| `DEV_202306` | `20230601~20230630` |
| `DEV_202309` | `20230901~20230930` |

공통: tick, `090000~152900`, `Tick_S_902_905`, timeout 240초, 운영 DB 미사용 sidecar.

## 3. Fold 성공 정의

- terminal success와 metrics 존재
- 거래 20건 이상
- 총수익률 > 0
- 건당 평균수익률 > 0
- MDD <= 15%

## 4. 후보 판정

| 판정 | 조건 |
|---|---|
| `DEVELOPMENT_ROBUST` | 성공 fold 3/3 |
| `DEVELOPMENT_MIXED` | 성공 fold 1~2/3 |
| `DEVELOPMENT_REJECT` | 성공 fold 0/3 또는 실행 실패 |

Beta(1,1), ROPE `p>0.5`, approve/reject 0.95로 fold 성공률 posterior를 함께 기록한다. 3개 fold만으로 Bayesian `APPROVE`를 강요하지 않는다. `CONTINUE`는 데이터 부족이지 전략 승인이나 실패가 아니다.

## 5. 자원·권위

이 기간들은 신규 전진 표본이 아니며 과거 연구에서 접근됐을 수 있다. 따라서 통과해도 후보 적격성은 개발 가설 수준이다. tick 신규 데이터는 2026-02-27 이후 0일이므로 최종 forward verdict는 이 실행으로 대체하지 않는다.
