# P5 Phase 0 — 챔피언 원장 배선 노트 (2026-07-05)

> 레인 H 산출. 범위: **원장 배선만** — 조건식 생성·청산 탐색·엔진 기동 없음(research-only).
> 코드: `alpha_lab/distill/ledger_wiring.py` · 테스트: `tests/unit/test_alpha_distill.py` (20 passed)

## 1. Phase 0 범위

게이트런 per-trade CSV들을 **명시 경로 인자**로 받아(자동 글롭·자동 실행 없음) 레코드를
정규화(`normalize_trade_row`)하고, identity 4-튜플 `(전략명, 종목코드, 진입일자, 진입시각)`로
중복 제거(`dedup_records`)한 뒤 JSONL 원장으로 영속(`write_ledger`/`read_ledger`)한다.
이 원장이 Phase 1(진입 증류)·Phase 2(최적 청산)의 유일한 입력이다. 원본 CSV는 읽기 전용.

## 2. 선행 조사 실측 (추정 없음 — 전부 파일 실물 확인)

| 항목 | 실측 결과 |
|---|---|
| `trade_ledger.py` | `ai_strategy_loop/autopsy/trade_ledger.py` — 미배선 완성 자산 실재. 후보 identity=(run_id, candidate_id, buy_sha256, sell_sha256), LEDGER_COLUMNS=기본 15(종목코드 포함)+B_14+S_5+R_4, 원천에 없는 컬럼은 None 허용 |
| `analyze.py` 번역표 | `ai_strategy_loop/autopsy/analyze.py:33-55` — `B_COLUMNS` 14종, `B_TO_STOM_VAR`(B_*→STOM 진입 변수) 실재. `RETURN_COLUMN='수익률'`(:24), `MFE_COLUMN='R_매수후최고수익률'`/`MAE_COLUMN='R_매수후최저수익률'`(:66-67) |
| 엔진 헤더 원천 | `backtest/back_static.py:24-36` — `TRADE_RESULT_B_COLUMNS`(14)·`_S_`(5)·`_R_`(4=R_매수후최고수익률·R_매수후최저수익률·**R_MFE·R_MAE**) |
| 게이트런 CSV 위치 | wt-dev `backtest/csv/` **6,458개** (`stock_bt_<전략명>_<YYYYMMDDHHMMSS>.csv`). 챔피언 계보 `stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_*.csv` 다수 + `stock_bt_EXIT2C_*` 실재. wt-alpha 로컬에는 `backtest/csv/stock_bt___AUTO_TMP__*.csv` 2개뿐 |
| CSV 실측 헤더 | utf-8-sig(BOM), **37컬럼** — 아래 표. 실측 파일: wt-dev `stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260701234829.csv`(175거래, tick 14자리) · wt-alpha `stock_bt___AUTO_TMP__..._20260315111609.csv`(min 12자리) |

### 실측 37컬럼 (헤더 순서 그대로)

| 그룹 | 컬럼 |
|---|---|
| 기본 14 | 종목명, 시가총액, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매수금액, 매도금액, 수익률, 수익금, 수익금합계, 매도조건, 추가매수시간 |
| B_* 진입 스냅샷 14 | B_현재가, B_등락율, B_당일거래대금, B_거래대금증감, B_체결강도, B_시가총액, B_회전율, B_전일동시간비, B_매수총잔량, B_매도총잔량, B_시분초, B_분봉시가, B_분봉고가, B_분봉저가 |
| S_* 청산 스냅샷 5 | S_현재가, S_등락율, S_체결강도, S_매수총잔량, S_매도총잔량 |
| R_* 결과 4 | R_매수후최고수익률, R_매수후최저수익률, **R_MFE, R_MAE** (있음 — 값 예 6.84/−0.96) |

### 핵심 발견 (배선 설계를 결정한 사실)

1. **CSV에 전략명·종목코드 컬럼이 없다.** 전략명은 파일명에서만(`strategy_from_csv_name`이
   `stock_bt_` 접두와 말미 14자리 타임스탬프만 제거 — 전략명 내부 밑줄 보존), 종목 식별은
   `종목명`뿐 → identity의 종목코드 필드는 종목명 폴백(종목명 컬럼 병행 보존으로 추적 가능).
2. **매수시간 자릿수 혼재**: tick 엔진 14자리(`20250103090403`) · min 엔진 12자리(`202504071000`)
   둘 다 실물 확인 → 12자리는 초 `00` 부여로 6자리 진입시각 정규화. 그 외 자릿수는 drop.
3. **재실행 중복 실증**: 같은 챔피언 전략의 게이트런 재실행 CSV 2벌(각 175거래) 스캔 →
   `dedup_records`가 정확히 175건 중복 검출(고유 175). 실물 3파일(364행) 정규화 drop 0건.
4. 매도조건 원문(선행 공백 포함)을 보존 — Phase 2 절 단위 PnL 어트리뷰션 파싱용.
5. 스키마 드리프트 봉쇄: 대조 테스트가 `analyze.B_COLUMNS`·`trade_ledger.S_/R_COLUMNS`와
   모듈 상수의 일치를 검증(`test_columns_match_engine_sources`).

### 알려진 한계 (정직 신고)

- min 12자리 매수시간은 분 해상도 — 동일 분 내 재진입(이론상)과 tick/min 혼합 스캔의 동일
  거래 병합은 불가. **Phase 1 원장은 tick 게이트런(14자리)만 대상 권장.**
- 종목명 폴백 identity는 동일 종목명 이종목(희귀) 충돌 가능성 잔존 — 게이트런 CSV에
  종목코드가 없는 실측 제약의 산물. 코드 컬럼이 있는 원천이 오면 자동으로 코드 우선.

## 3. API 계약 (봉인)

`normalize_trade_row(row: Mapping, *, source: str) -> dict | None`(필수: 전략명·종목코드·진입일자·진입시각·수익률, B_*/S_*/R_* 있으면 통과) ·
`identity(rec) -> (전략명, 종목코드, 진입일자, 진입시각)` · `dedup_records(records) -> (unique, dup_count)`(first-wins) ·
`write_ledger(records, out_path) -> int`(JSONL) · `read_ledger(path) -> list[dict]` ·
`scan_csvs(paths: Sequence[Path]) -> (records, report)`(명시 경로만, report=파일별 rows/kept/dropped).
ValueError는 계약 위반에만, 데이터 불량 행은 None-drop(리포트 집계) — autopsy 관례 정합.

## 4. 다음 단계

1. **P1 진입 증류 (Phase 1)**: 이 원장(챔피언 tick 게이트런 CSV 명시 목록 → JSONL)에서
   B_* 14피처 × ~20분위 임계 탐색 + purged day-CV 4-fold(1일 embargo) + 라벨 셔플 placebo
   100회 p95. n_trials는 alpha_lab.registry 통합 원장에 합산.
2. **P2 최적 청산 (Phase 2)**: **엔진 검증 창에서만** — warm64 min 스윕 종료 후 재현 게이트
   (현직 매도식 경로 재실행 오차 중앙값 ≤0.1%p, 95% 거래 ≤1틱) 선행 통과가 전제. 미달 시
   청산 축 전면 폐기(프로그램 §4.4). 지금은 어떤 엔진 프로세스도 기동하지 않는다.
3. 제안 3 Phase 3b와 청산 축 단일 프로그램 통합(§3.3 상보성 권고) 유지.
