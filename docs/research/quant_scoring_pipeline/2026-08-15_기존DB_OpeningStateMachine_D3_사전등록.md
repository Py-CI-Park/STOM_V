# 기존 DB Opening State Machine D3 사전등록 (2026-08-15)

## 권위·Source

- `existing_db_development_no_oos_no_adoption`
- DB: `_database/stock_tick_back.db` immutable read-only
- Census: `stom.mcap_census.v2`, 4Band 4/4 PASS
- W0: `09:00:00 <= 시분초 < 09:30:00`
- W0 hash: `69b2d05c2fd682cdf3f61f78ef33fb0f18f6a3b962fe7e68973662760db9c97b`
- OOS·실전·자동채택 권한: 없음

## Family

| Family | 상태전이 가설 | Entry 변수 |
|---|---|---:|
| ABSORPTION_REVERSAL | 매도호가 압력 지속→저점 진행 제한→Flow 반전 | 6 |
| FAILED_BREAKOUT_RETURN | 고점 이탈→미갱신 지속→Range 복귀·Flow 확인 | 6 |
| COMPRESSION_CONFIRMED_BREAKOUT | 직전 압축→변동성 확장→신고가·Flow 확인 | 6 |
| FLOW_PRICE_DIVERGENCE | 직전 강한 Flow·제한 가격반응→가격·Flow 확인 | 6 |
| OPENING_OVERREACTION_MEAN_REVERT | 시초 급락→저점 미갱신→거래대금 둔화·회귀 | 6 |

상태 순서는 `STATE_ENTER → STATE_PERSIST → EVENT → CONFIRM → ENTER`로 고정한다.

## 시총 Band

- `MCAP_A_LT3000`: `<3000억`
- `MCAP_B_3000_5000`: `3000<=x<5000억`
- `MCAP_C_5000_10000`: `5000<=x<10000억`
- `MCAP_D_GE10000`: `>=10000억`

한 후보는 정확히 한 Family·한 Band만 가진다.

## 후보 Budget

- Seed: `20260815`
- QMC: Family×Band당 32개
- Raw: `5×4×32=640`
- 성과 확인 후 Budget 증액 금지
- AST/runtime/work/window 계약 실패 후보 즉시 제외
- Canonical signature 중복 제외
- 각 Family×Band에서 구조적으로 이격된 2개만 Selection screen
- 공식엔진 최대 40개

## Event·Control Gate

공식엔진 Smoke의 거래/Event count를 발생량 Evidence로 사용한다.

- 전체 Event 200 이상
- 각 Expected development fold 20 이상
- 누락 Fold는 0으로 계산
- Timestamp shuffle
- Symbol shuffle
- Direction inversion
- 동일 Event 수 random offset
- Parameter random baseline

원신호가 Controls를 넘지 못하면 확대하지 않는다.

## 공식엔진·Fold

1. 40개 Selection screen
2. Family×Band Top-2를 Pareto/발생량으로 선정
3. 동일한 calendar development folds
4. Top-3/Family 원칙을 적용하되 Cell 후보가 2개면 둘 다 검증
5. 거래수·평균·총수익·MDD·부호 일관성
6. BH-FDR·Bayesian posterior
7. Source snapshot hash exact match

## Entry·Exit

D3 Selection은 두 Exit Arm을 사용한다.

- Baseline risk Exit
- 단순 time Exit

Entry 후보별 모든 Exit 전수조합은 금지한다. D3 Rule-pass·Bayesian APPROVE·Control 우위가 있는 Cell에만 D4를 허용한다.

## D4

- 완성 전략 Entry 6~8 + Exit 4~6 허용
- 한 단계 Active 최대 8
- Entry QMC 32~64 + TPE 최대 24
- Exit QMC 24~48 + TPE 최대 16
- Joint Entry2+Exit2 16~24
- Random 대조 25% 이상
- 목표 24~36시간, hard stop 48시간
- 적격 Cell 0이면 `GATE_NOT_ENTERED`로 완료

## 최종 판정

- `INSUFFICIENT_SAMPLE`
- `DEVELOPMENT_REJECT`
- `DEVELOPMENT_RULE_PASS`
- `BAYESIAN_APPROVE`
- `BO_ELIGIBLE`

모든 Cell에 봉인 판정이 있으면 프로그램은 완료다. 양성 후보가 없어도 실행 미완료로 표현하지 않는다.
