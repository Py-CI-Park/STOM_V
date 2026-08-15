# C0 기존 DB 시가총액 4Band Census 결과 (2026-08-15)

## 판정

- 상태: `CENSUS_COMPLETED`
- 권위: `existing_db_development_no_oos_no_adoption`
- Source: `_database/stock_tick_back.db` immutable read-only
- Source 크기: 29,727,162,368 bytes
- Source fingerprint: sampled_v1 `a944f7c2bf2d22188688c768e3b202406734c4a38ba19bf81dbde6616eb03a48`
- 실행시간: 498.932초
- 운영 DB/WAL/SHM 변경: 없음

## Band 결과

| Band | 시가총액(억) | Rows | 종목 | 거래일 | moneytop 교집합 code-days | 판정 |
|---|---:|---:|---:|---:|---:|---|
| MCAP_A_LT3000 | `<3000` | 42,107,554 | 1,902 | 952 | 26,292 | CENSUS_PASS |
| MCAP_B_3000_5000 | `3000~5000` | 14,573,458 | 804 | 952 | 9,650 | CENSUS_PASS |
| MCAP_C_5000_10000 | `5000~10000` | 15,362,144 | 600 | 952 | 9,882 | CENSUS_PASS |
| MCAP_D_GE10000 | `>=10000` | 50,479,144 | 473 | 952 | 30,504 | CENSUS_PASS |

4개 Band 모두 120일·30종목 하한을 통과했다. 경계 누락·중복 및 invalid 시가총액 row는 0이다.

## 시간 Coverage

원시 min/max만 보면 일부 종목 row가 10:30까지 존재하지만 10:00~10:30은 단 1거래일뿐이다. 따라서 전체기간 Coverage로 사용할 수 없다.

moneytop membership과 실제 종목 row의 교집합, 4개 Band 모두, 거래일 120일·종목 30개, 시작·마지막 분이 존재하는 완전한 5분 bucket만 허용했다.

| Bucket | 공통 Coverage | 사용 |
|---|---|---|
| 09:00~09:05 | 충분 | 포함 |
| 09:05~09:10 | 충분 | 포함 |
| 09:10~09:15 | 충분 | 포함 |
| 09:15~09:20 | 충분 | 포함 |
| 09:20~09:25 | 충분 | 포함 |
| 09:25~09:30 | 충분 | 포함 |
| 09:30~09:35 | 마지막 row가 09:30:01 수준으로 불완전 | 제외 |
| 10:00~10:30 | 1거래일 | 제외 |

최종 W0:

```text
stock_tick: 09:00:00 <= 시분초 < 09:30:00
```

## 해석

- 사용자가 제안한 시총 4Band는 기존 DB에서 모두 연구 가능하다.
- `<3000`과 `>=10000`은 row·code-day가 상대적으로 많다.
- `3000~5000`, `5000~10000`도 최소 하한을 충분히 넘는다.
- 기존 DB의 장기간 공통 Tick 연구 범위는 09:00~09:30이다.
- 10:00 이후 극소수 row를 일반적인 09:00~10:30 Coverage로 표현하는 것은 금지한다.

## 제한

C0는 Population·Coverage Census다. 유동성·미시구조 Quantile과 상태전이 Event 발생량은 BackFinder/Event 단계에서 계산한다. C0 PASS는 경제적 Edge나 전략 성공을 의미하지 않는다.

## Evidence

- `evidence/2026-08-15_mcap_census.json`
- Schema: `stom.mcap_census.v2`
- `window_contract.status=AVAILABLE`
- `window_contract.start=090000`
- `window_contract.end_exclusive=093000`
