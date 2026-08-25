# RES-02 성과 비사용 Event Gate 결과

> 실행일: 2026-08-26 · 단계: `RES-02 / G0 Event Gate` · 판정: **`EVENT_GATE_PASS`** · 다음 Gate: **`RES02_G0_OFFICIAL_FOLD_EXECUTION`**
> 권위: development 후보 실행 허용만 의미하며 경제성·OOS·실전·채택을 의미하지 않는다.

## 1. 결론

봉인된 `<3000` 후보 160개를 4개 development Fold의 실제 틱 데이터에서 평가했다. 이 단계는 `candidate/fold/day/symbol/timestamp/triggered`만 사용했고 수익·수익률·MDD·승률·미래가격·청산 결과를 읽지 않았다.

Event 하한을 통과한 후보는 24개였고, Event 수나 PnL 순위가 아닌 사전등록된 Family 내부 parameter maximin 규칙으로 7개를 공식 G0 실행 대상으로 고정했다. 따라서 다음 단계에서 수행할 최대 공식 실행량은 **7후보 × 4Fold = 28 jobs**다.

## 2. 입력·구현 정체성

| 항목 | 관측값 |
|---|---|
| 구현 브랜치 | `codex/process-research-res-02-event-gate` |
| 구현 HEAD | `a55cc67f37d96b6abcddf7ea2a2676ef5584ce3a` |
| 후보 manifest file SHA-256 | `251a37edb2b34539fe343a7ae533262fb41d02af7272fc1167076055136e94dc` |
| 후보 canonical SHA-256 | `39a6d3fd8b4cce65979a530375cdd228fda542ef03dd5963968f7d1ddf326fc0` |
| 후보 수 | 160 (`5 Family × 32`) |
| 원천 DB | `C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db` |
| 원천 DB 크기 | `29,727,162,368 bytes` |
| 원천 sampled-v1 SHA-256 | `a944f7c2bf2d22188688c768e3b202406734c4a38ba19bf81dbde6616eb03a48` |
| 결과 JSON | `evidence/2026-08-26_res02_event_gate.json` |
| 결과 JSON SHA-256 | `cb567e3b76342676e3a66393c849c1dd13d97670afbc09bd103ac88fe0c930bb` |

## 3. 실행 범위와 완전성

| 지표 | 실제 값 | 해석 |
|---|---:|---|
| worker processes | 4 | 결정론적 종목 청크 병렬 합산 |
| moneytop rows | 143,995 | 4개 Fold·09:00:30 이후 membership 원천 행 |
| membership symbols | 1,653 | moneytop에 등장한 종목 수 |
| missing symbol tables | 25 | 원천 틱 테이블이 없어 실행 대상에서 제외, 숨기지 않음 |
| 실제 스캔 symbol tables | 1,628 | `1,653 - 25` |
| scheduled code-days | 12,387 | 실제 테이블이 있는 membership 종목-일 조합 |
| tick 존재 code-days | 5,851 | 지정 시간창에서 실제 틱 행이 존재한 조합 |
| tick rows | 9,785,737 | 12개 현재/과거 틱 열만 read-only 조회 |
| base-eligible tick rows | 1,744,498 | 공식 BaseStrategy 공통 필터 통과 행 |
| elapsed | 211.196초 | 4프로세스 전체 실행 |

원천 DB는 immutable read-only URI로만 열었다. 실행 전후 SQLite sidefile snapshot이 같았고 `.db-wal`, `.db-shm`, `.db-journal`은 생성되지 않았다. 보호 경로 Git 변경도 0건이다.

## 4. Family별 Event 통과와 선택

| Family | Event 하한 통과 | 공식 G0 선택 | 선택 규칙 |
|---|---:|---:|---|
| `ABSORPTION_REVERSAL` | 12 | 2 | 통과 집합 내부 parameter maximin |
| `FAILED_BREAKOUT_RETURN` | 1 | 1 | 단일 통과 후보 |
| `COMPRESSION_CONFIRMED_BREAKOUT` | 1 | 1 | 단일 통과 후보 |
| `FLOW_PRICE_DIVERGENCE` | 1 | 1 | 단일 통과 후보 |
| `OPENING_OVERREACTION_MEAN_REVERT` | 9 | 2 | 통과 집합 내부 parameter maximin |
| **합계** | **24** | **7** | Family당 최대 2, 전체 최대 10 |

## 5. 공식 실행 대상으로 봉인된 7개 후보

| Family | candidate | 전체 Event | 최소 Fold | 일수 | 종목 수 |
|---|---|---:|---:|---:|---:|
| Absorption | `D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_cb7275dfee` | 332 | 70 | 56 | 95 |
| Absorption | `D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_639515aa1e` | 207 | 21 | 25 | 31 |
| Failed Breakout | `D3_FAILED_BREAKOUT_RETURN_MCAP_A_LT3000_55b6c25f13` | 588 | 139 | 78 | 241 |
| Compression | `D3_COMPRESSION_CONFIRMED_BREAKOUT_MCAP_A_LT3000_ad1fb159a2` | 228 | 33 | 57 | 106 |
| Flow Divergence | `D3_FLOW_PRICE_DIVERGENCE_MCAP_A_LT3000_c5850a62eb` | 451 | 76 | 46 | 70 |
| Opening Revert | `D3_OPENING_OVERREACTION_MEAN_REVERT_MCAP_A_LT3000_3205e5b871` | 1,875 | 384 | 72 | 152 |
| Opening Revert | `D3_OPENING_OVERREACTION_MEAN_REVERT_MCAP_A_LT3000_89a4f88e5a` | 269 | 53 | 38 | 43 |

모든 선택 후보는 전체 Event 200, Fold별 20, distinct days 20, distinct symbols 10을 각각 충족한다. 가장 경계에 가까운 후보도 전체 207·최소 Fold 21로 사전등록 기준을 넘었다.

## 6. 검증 증거

| 검증 | 결과 |
|---|---|
| 실제 JSON Pydantic 재검증 | PASS |
| 금지 outcome key 재귀 검사 | 0건 |
| `pnl_fields_read` | `false` |
| `forbidden_outcome_fields_present` | `false` |
| `economic_result` | `NOT_EVALUATED` |
| `official_execution_status` | `NOT_STARTED` |
| holdout | `SEALED_NOT_TOUCHED` |
| 병렬 2프로세스 vs 순차 fixture 동일성 | PASS |
| 집중 unit tests | 11 passed |
| Ruff | PASS |
| basedpyright | 0 errors, 0 warnings |
| no-excuse Python 검사 | PASS |
| nonrelease sync | PASS |

## 7. 성공·실패의 정확한 의미

| 질문 | 판정 |
|---|---|
| Event 측정 시스템이 실제 대규모 DB에서 작동했는가 | **성공** |
| 과거 `FAILED_BREAKOUT` 런타임 결함이 차단되지 않았는가 | **사전점검 성공** |
| 성과를 보지 않고 공식 실행 후보를 고정했는가 | **성공** |
| 수익 후보를 찾았는가 | **아직 모름** — PnL 미평가 |
| 전략이 강건한가 | **아직 모름** — ANA-02/RES-04 미실행 |
| OOS·실전 적용 가능한가 | **아니오** — holdout 봉인·인간 승인 없음 |

## 8. 다음 단일 행동

새 브랜치에서 봉인된 7개 후보를 같은 4개 Fold·비용·exit·engine 계약으로 **28개 공식 G0 job** 실행한다. job당 4 engines, manager 최대 2개, timeout 3,600초, 인프라 실패만 1회 재시도한다. 결과를 보기 전 실행 프로필을 바꾸지 않으며 strategy DB와 보호 DB에는 쓰지 않는다.
