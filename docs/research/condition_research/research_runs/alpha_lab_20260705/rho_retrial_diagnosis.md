# P1 ρ게이트 재판정 — 번역 계층 결함 진단서 (rho_retrial_diagnosis)

- 작성: 2026-07-06 (봉인 재판정 조항에 따른 1회 한정 진단·수정)
- 스테이지: `P1_rho_gate_retrial_diagnosis_and_registration`
- 재판정 조항(엄수): 번역 계층 결함 진단·수정에 한해 1회, 동일 10규칙 재백테 ≤10회.
  규칙 재선별·임계값 하향·표본창 교체 금지. 리프 절(피처·부등호·임계값)은 1차
  등재본과 byte-identical 유지. 판정은 이분법(ρ>=0.5 본빌드 / ρ<0.5 포기).

## 0. 결론 (요약)

1차 번역식은 채굴 표본 공간(월드)보다 넓은 공간에서 발화했다 — **공식 거래
86,916건 중 3,926건(4.52%)이 월드 밖 발화**로 실측됐다(§2). 결함은 두 개다:

- **시간창 결함(주)**: 1차 가드 `90000 <= 시분초 < 93000`은 표본 규약 월드
  `[09:00:01, 09:25:00]`보다 넓다. 시간창 위반 3,281건(3.77%)은 **전량
  092501~092800 대역**이며, 이 대역 매수는 채굴 라벨 L1_180(180초 지평)을
  구조적으로 실현할 수 없다(최대 보유 179초 후 092800 강제청산 — §2.2).
- **유니버스 미표현(부)**: 1차 매수식에는 moneytop 멤버십 조건이 없다. 엔진
  자체의 `관심종목` 선행 게이트가 근사 적용해 왔으나(§2.3), 수식 자체는 월드
  제약을 담지 않았고 잔차 위반 664건(판정 가능 85,212건의 0.78%)이 실측됐다.

수정은 표본화 조건 보완 두 가지뿐이다: 시간창 가드를 표본 규약
`90001 <= 시분초 <= 92500`으로, 유니버스 가드 `관심종목 > 0`(moneytop 프록시,
표본일 2일 238,227행 일치율 **100.0%** — §3)을 AND 결합. 리프 절은 전 규칙
byte-identical 보존을 기계 검증했다(§4). 수정식 ALP_RM2_01~10을 INSERT-only로
등재 완료(§5). stride 5초는 추정 그리드이지 거래 조건이 아니므로 번역하지
않는다(§6).

- key_values: `out_of_window_pct=4.52`(월드 밖 발화; 시간창만은 3.77),
  `universe_proxy="관심종목 > 0"`, `proxy_agreement_pct=100.0`,
  `leaf_clauses_identical=true`

## 1. 판정 맥락 (1차 결과 실측 요지)

- 1차 엔진 확인: `rho_gate_verdict.json` — verdict
  `blocked_indeterminate_engine_censoring`. 실측 8규칙 진단 rho
  `0.5000000000000001`(rho_measured_subset), 검열(타임아웃) 2규칙
  ALP_RM_08/09로 봉인 n=10 rho 미산출(attainable [-0.0729, 0.6565]).
- 실측 8규칙 전원 gate=False(mdd 118.8~1119 > cap 35), 총손실 —
  `rho_gate_engine_runs.json` chunks[*].rows.
- 공식 거래 CSV 8개 존재(RM_01~07, RM_10): `rho_gate_engine_runs.json`
  rows[*].csv_path. RM_08/09는 `csv=no metrics=no`(검열)로 공식 CSV 부재.

## 2. 결함 실증 (a) — 월드 밖 발화 정량 (전부 read-only 실측)

**월드 정의(봉인)**: `preregistration_v1.json` label_spec.grid —
"t0 그리드: 09:00:01~09:30:00 stride 5초, t0 > 09:25:00 스킵(h_max=300 절단
방지), t0 초에 moneytop 유니버스 포함일 때만"(universe: "해당 초 row 존재 AND
세미콜론 조인 코드 포함"). 구현 실측: `alpha_lab/dataset/reader.py:158-189`
(_iter_t0_grid + universe.get 필터).

**1차 번역 가드 실측**: `rho_gate_registration_receipt.json` selection.top10[*]
buy_expr — 전 규칙 `if (90000 <= 시분초 < 93000) and <리프>` 형태(시간창만,
유니버스 조건 없음). 가드 출처는 `alpha_lab/translate/codegen.py`의
`DEFAULT_TIME_GUARD`(CSC-10/11 관례 창).

**측정 방법**: 공식 CSV 8개의 전 거래에서 매수 신호 초 = `B_시분초`
(전 86,916건에서 `매수시간%1e6`과 불일치 0건), 종목코드 =
`code_info.db` stockinfo 역매핑 ∩ 해당일 tick DB 테이블(6자리 명칭은 직접
코드) — 해석 불가 1,704건(1.96%)은 유니버스 판정에서 정직 제외. 멤버십 =
해당일 `stock_tick_YYYYMMDD.db` moneytop `거래대금순위` 세미콜론 리스트 포함
여부. 산출: `rho_retrial_evidence_trade_window.json` (스키마 v2).

### 2.1 규칙별 월드 밖 발화율

| 규칙 | 거래 | 시간창 위반(092501~092800) | 유니버스 위반/판정가능 | 월드 밖 합계 | out_of_world_pct |
|---|---|---|---|---|---|
| ALP_RM_01 | 981 | 52 (5.30%) | 0/938 | 52 | 5.30 |
| ALP_RM_02 | 6,845 | 74 (1.08%) | 9/6,688 | 83 | 1.21 |
| ALP_RM_03 | 598 | 0 (0.00%) | 21/585 | 21 | 3.51 |
| ALP_RM_04 | 672 | 3 (0.45%) | 20/658 | 22 | 3.27 |
| ALP_RM_05 | 4,166 | 27 (0.65%) | 6/4,056 | 33 | 0.79 |
| ALP_RM_06 | 4,651 | 654 (14.06%) | 17/4,478 | 668 | 14.36 |
| ALP_RM_07 | 49,273 | 2,310 (4.69%) | 315/48,433 | 2,614 | 5.31 |
| ALP_RM_10 | 19,730 | 161 (0.82%) | 276/19,376 | 433 | 2.19 |
| **합계** | **86,916** | **3,281 (3.77%)** | **664/85,212 (0.78%)** | **3,926** | **4.52** |

- 시간대 히스토그램: `<=090000` 0건, `090001-092500` 83,635건,
  `092501-092800` 3,281건, `>092800` 0건 — 시간창 위반은 **전량 마감 직전
  대역**이다(per_rule.hms_hist 합산).
- 시간창·유니버스 이중 위반 중복 19건(3,281+664−3,926).

### 2.2 시간창 위반의 구조적 성격

- 채굴 근거 라벨은 L1_180(t0+180초 매수호가1 경로) — `preregistration_v1.json`
  mining_spec.label="L1_180". 092501 이후 매수는 092800 강제청산까지 최대
  179초로, **채굴이 증거로 삼은 180초 지평 자체가 존재하지 않는 공간**이다.
- 실측: 시간창 위반 3,281건의 매도조건 최빈값이 `전략종료청산`(RM_06
  434/654건, RM_07 1,661/2,310건 등 —
  per_rule.time_violation_sell_conditions). 엔진 마감 92800은 동결 프로파일
  `bt_universe_end_time=92800`(smoke_config_tick_official_full_warm64_20260704
  .json)과 일치하고, `>092800` 매수 0건이 이를 재확인한다.

### 2.3 유니버스 위반의 성격 — 엔진 게이트 실측

- 엔진은 매수식 실행 전에 `if not 관심종목: continue`로 선행 게이트한다 —
  `backtest/backengine_kiwoom_tick.py:89,117,145`,
  `backtest/backengine_kiwoom_tick2.py:99,147,201`. 따라서 1차 백테에서도
  유니버스는 근사 적용됐다(위반이 0.78%에 그친 이유).
- 위반 664건 전수 감사: 매수 초의 저장 `관심종목` 플래그가 **664건 전부 1**
  (flag0 0건, 행부재 0건) — `rho_retrial_evidence_universe_violation_audit.json`.
  즉 엔진 게이트 오작동이 아니라, 일부 초에서 저장 플래그와 moneytop 리스트가
  갈라지는 **데이터 수준 잔차**다(표본일 2일 전수에서는 0건 — §3).
- 다만 1차 등재 **수식 자체**에는 월드의 유니버스 조건이 없었다. 수식이 봉인
  자산(등재본)이고 엔진 게이트는 엔진 구현의 부수 효과이므로, 수식 단독 평가
  환경(수식만 이식되는 평가기)에서는 월드 밖 발화가 차단되지 않는다. 이것이
  번역 계층 결함으로 등재 수식에 유니버스 가드를 명시해야 하는 근거다.

### 2.4 결함의 계측 왜곡 진단(참고값 — 판정 불사용)

- CSV 재계산 PF는 1차 판정값과 정확 일치(교차검증): 8규칙 재계산 rho =
  `0.5000000000000001` == verdict.rho_measured_subset.
- 월드-안 부분집합 PF(참고 진단): 8규칙 rho `0.5476`(0.5 대비 +0.048), 월드 밖
  거래 수익금 합은 전 규칙 음수(예: RM_07 −61,094,693; RM_06 −18,316,205).
  단, 완료된 런에서 거래를 사후 제외하는 것은 자본 점유·재진입 동학을 반영하지
  못하므로 **참고 진단값**이다. 판정은 오직 수정식 재백테로 한다
  (`rho_retrial_evidence_trade_window.json` diagnostic_rho_measured8.note).

### 2.5 한계(정직 기록)

- **RM_08/09 CSV 부재**: 공식 run 기록이 `csv=no metrics=no`(검열)이므로 이 두
  규칙의 월드 밖 발화율은 계측 불가. `loop_runs.db` run 기록도 status=error로
  거래 행이 없다(`rho_gate_engine_runs.json` chunk 3~6 rows). 디스크의
  `stock_bt_ALP_RM_08_20260706045347.csv`(mtime 04:53)는 chunk05 실행 구간
  (04:43:46~04:54:35 KST) 내 타임스탬프의 **미기록 고아 산출물**이라 공식
  계측에서 제외했다(봉인 runs 기록 기준).
- **명칭→코드 해석 불가 1,704건(1.96%)**: code_info.db 스냅샷에 없는 개명
  종목 등. 시간창 판정에는 포함(코드 불필요), 유니버스 판정에서만 제외.
- 표본일 외 날짜의 플래그/리스트 잔차(0.78%)는 전 기간 전수 측정이 아니라
  거래 발생 지점에서의 조건부 측정이다.

## 3. 결함 실증 (b) — '관심종목' 컬럼 의미 실측과 프록시 채택

- 측정(mode=ro): 표본일 `20230601` + `20240103`의 전 종목 테이블 행에 대해
  `flag=(관심종목!=0)` vs `member=(코드 in moneytop[같은 초 세미콜론 리스트])`
  일치율 — `rho_retrial_evidence_universe_proxy.json`.

| 표본일 | 종목테이블 | moneytop 초 | 측정 행 | 일치율 | flag1·member0 | flag0·member1 |
|---|---|---|---|---|---|---|
| 20230601 | 82 | 1,799 | 137,029 | 100.0% | 0 | 0 |
| 20240103 | 60 | 1,801 | 101,198 | 100.0% | 0 | 0 |
| 합계 | — | — | **238,227** | **100.0000%** | 0 | 0 |

- 가드 창(90001~92500) 한정 199,070행도 100.0%. `관심종목` 저장값은 {0, 1}
  (int) 전수. 20230601의 moneytop 행 부재 1초 표본도 flag=0으로 일치.
- **채택 판정**: 일치율 100.0% >= 99% → `관심종목 > 0`을 유니버스(moneytop
  멤버십) 프록시 가드로 채택. moneytop 세미콜론 리스트 자체는 조건식
  네임스페이스에 존재하지 않아 직접 표현 불가(변수 화이트리스트:
  `ai_strategy_loop/brain/variable_scope.py:78` — `관심종목`은 _COMMON_SCALARS
  에 존재, moneytop 리스트형 변수는 부재). 프록시의 알려진 잔차는 §2.3의
  0.78%(거래 조건부)다.

## 4. 수정 명세 — 가드 보강, 리프 절 byte-identical

**허용 수정 = 표본화 조건 보완뿐** (a) 유니버스 가드, (b) 시간창 가드.

- 시간창: `90000 <= 시분초 < 93000` → **`90001 <= 시분초 <= 92500`**
  (표본 규약 t0 월드의 HHMMSS 폐구간 직역).
- 유니버스: **`관심종목 > 0`** AND 결합(§3 채택 근거).
- 수정식 형태: `if (90001 <= 시분초 <= 92500) and (관심종목 > 0) and <리프>:`
  — 리프 절은 1차 등재본에서 바이트 하나 바꾸지 않는다.

**구현(additive)**: `alpha_lab/translate/codegen.py`

- 신규 상수 `SAMPLE_TIME_GUARD = "90001 <= 시분초 <= 92500"`,
  `UNIVERSE_GUARD_MONEYTOP_PROXY = "관심종목 > 0"`.
- `translate_leaf_rule`/`leaf_rule_to_buy_expr`에 `universe_guard=None` 옵션
  추가(기본 None=미결합 — 기존 산출 byte-identical). 가드 결합 순서는
  time_guard → universe_guard → 리프.
- 재수출 부속: `alpha_lab/translate/__init__.py`(+4/−0) — 신규 상수 2종의
  import 2행 + `__all__` 2행 추가뿐(순수 additive, 로직 무변경). codegen 변경의
  패키지 재수출로서 tracked 수정 전수에 포함해 선언한다(검증 지적 수복
  2026-07-06 — 전수 선언은 `rho_retrial_verdict.md` 변경 파일 전수 선언 절).
- 테스트 보강: `tests/unit/test_alpha_translate.py`에 7케이스 추가 —
  기본 호출이 1차 등재본과 byte-identical임을 ALP_RM_01 골든 sha256
  (`9b48b605...`)으로 고정(`test_default_output_byte_identical_to_first_registration`),
  가드 순서/생략/리프 불변(`test_guard_overrides_preserve_leaf_bytes`)/저장소
  가드 통과. 결과: 파일 78 passed. 전체 unit 스위트 10 failed는
  `baseline_test_failures_20260705.md`에 봉인된 기존 기준선 실패 10건과
  전건 동일(회귀 0) — 4,314 passed.
- 저장소 가드 정합: `check_time_integrity`는 함수 호출 인자만 검사
  (`ai_strategy_loop/brain/time_integrity.py:39-75`)하므로 비교식 가드는
  영향 없음 — 수정식 전 규칙 repo_gate_check 통과 실측(영수증 verification).

## 5. 등재 — ALP_RM2_01~10 (INSERT-only)

- 영수증: `rho_retrial_registration_receipt.json` / 원장:
  `rho_gate_registration_provenance.jsonl`(stage=rho_retrial_registration
  10행 append). 원장 append는 등재기 계약상의 tracked 수정(+10/−0)이므로
  전수 선언에 포함한다 — 기존 1차 10행은 HEAD 대비 byte-identical(기계 대조),
  추가 10행의 buy/leaf/first_buy/sell sha256·retrial_of·rule_id는 영수증
  verification[]·registration.inserted[]와 전건 일치(불일치 0, 검증 지적 수복
  2026-07-06 기계 교차 대조).
- 절차 검증(전 규칙): (1) 1차 rounded_rule 기본 재생성이 1차 buy_sha256과
  byte-identical(비회귀), (2) 수정식 리프 절 == 기본식 리프 절
  (**leaf_clauses_identical 전수 true**), (3) 정적검증+저장소가드 통과,
  (4) INSERT-only 등재 10건·충돌 0·백업
  `_database/strategy.db.bak.alpha_lab_20260706T074953`, (5) post-verify
  재조회 sha 전건 일치.
- 매도식: 1차와 동일 — 챔피언 hard-stop 원문(`GATE_rr8_12_turnover_min_902_1_5_S`),
  sha256 `8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07`
  (등재 전 strategy.db ALP_RM_01 stocksell 원문 sha 재검증 일치).

| 신규 | 1차 | rule_id | leaf_sha256(12) | buy_sha256(12) |
|---|---|---|---|---|
| ALP_RM2_01 | ALP_RM_01 | P1-s02-l019 | e8cecfed8a76 | 1fdce899f9a0 |
| ALP_RM2_02 | ALP_RM_02 | P1-s04-l011 | 5983dd270585 | 5562a691d8dd |
| ALP_RM2_03 | ALP_RM_03 | P1-s03-l026 | 369d81daf0be | 6c6b8c2f9a4d |
| ALP_RM2_04 | ALP_RM_04 | P1-s00-l026 | 4e36552b004e | 60766459e2e5 |
| ALP_RM2_05 | ALP_RM_05 | P1-s02-l020 | a5080a587fe1 | bff112b30e12 |
| ALP_RM2_06 | ALP_RM_06 | P1-s03-l007 | 688c7afbcc21 | ad26654d3287 |
| ALP_RM2_07 | ALP_RM_07 | P1-s01-l029 | 00ced6d60f94 | 0c2e95de33d5 |
| ALP_RM2_08 | ALP_RM_08 | P1-s04-l027 | fcbacb45bd47 | 1b32004f65fd |
| ALP_RM2_09 | ALP_RM_09 | P1-s00-l012 | 7215d4838d9f | 48a98066f88b |
| ALP_RM2_10 | ALP_RM_10 | P1-s03-l011 | 5a3744f60821 | 8ff672a92fcf |

## 6. 비번역 항목과 근거

- **stride 5초**: 채굴 t0 그리드의 표본 추출 간격 — 월드(발화 가능 공간)의
  제약이 아니라 그 공간을 5초마다 관측한 **추정 그리드**다. 거래 조건으로
  번역하면 오히려 채굴이 평가한 공간(임의 초 발화)과 어긋난다. 번역하지 않음.
- **표본 채택 조건(entry/3지평 행 존재, 매도호가1>0)**: 라벨 측정 가능성
  규약(정직 제외)이지 진입 조건이 아니다. 번역하지 않음.
- **moneytop 리스트 직접 조건**: 조건식 네임스페이스에 해당 변수 부재로 직접
  표현 불가 — `관심종목 > 0` 프록시로 대체(§3, 일치율 100.0%).

## 7. 기대 효과의 정직한 범위

- 수정으로 **월드 밖 발화 4.52%(특히 180초 지평이 없는 092501+ 대역 3.77%)가
  수식 수준에서 차단**되고, 등재 수식이 채굴 증거 공간과 정합해진다.
- 참고 진단(§2.4)상 월드-안 부분집합 PF 개선 폭은 크지 않았다(rho 참고값
  0.5476). 재백테 결과를 예단하지 않는다 — 판정은 이분법 재백테가 결정한다.
- 검열(RM_08/09) 완화 가능성: 매수 평가 유효 창이 1,681초→1,500초로 10.8%
  축소되고 규칙별 신호 수가 0.8~14.4% 감소하나, 타임아웃 해소는 보장이 아니라
  재백테로만 확인된다.

## 8. 산출물·근거 경로

- 본 진단서: `rho_retrial_diagnosis.md`
- 거래 월드 계측: `rho_retrial_evidence_trade_window.json` (v2: PF 진단 포함)
- 프록시 일치율: `rho_retrial_evidence_universe_proxy.json`
- 위반 전수 감사: `rho_retrial_evidence_universe_violation_audit.json`
- 등재 영수증: `rho_retrial_registration_receipt.json` (+provenance jsonl append)
- 코드: `alpha_lab/translate/codegen.py`, `alpha_lab/translate/__init__.py`,
  `tests/unit/test_alpha_translate.py`
- 원천(읽기 전용): `rho_gate_engine_runs.json`, `rho_gate_verdict.json`,
  `rho_gate_registration_receipt.json`, `preregistration_v1.json`,
  `backtest/csv/stock_bt_ALP_RM_{01..07,10}_*.csv`,
  `_database/stock_tick_20230601.db`, `_database/stock_tick_20240103.db`,
  `_database/code_info.db`, `_database/strategy.db`
