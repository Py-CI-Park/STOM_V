# 2026-07-02 Replay 프로파일 포렌식 — rr8_12_turnover_min_902=1.5 2025 재현 불일치 규명

> 상태: research-only. can_promote/export/live=false 계약 불변. 이 문서는 기록 비교·프로파일 동결 권고이며 권한/승격 로직 변경 없음.

## 결론 (요약)

두 기록의 상충은 **엔진 수·기간·유니버스·시간창·조건식 차이가 아니라, 백테스트 실행 프로파일 중 `betting`(종목당 배팅금)과 `avg_time`(평균값 계산 틱수) 2개 파라미터 차이** 때문이다.

| 기록 | profit | trades | MDD | betting | avg_time |
|---|---:|---:|---:|---:|---:|
| 2026-06-28 replay | +3,062,696 | 190 | 12.87 | "5" (종목당 500만원) | 30 |
| 2026-07-01 replay | +518,822 | 175 | 20.54 | "1" (종목당 100만원) | 60 |

- `betting`은 호가 기반 체결 시뮬레이션의 주문금액을 바꿔 **체결가/체결시각/수익금 스케일**을 바꾼다 (공통 156거래 중 75건 체결가 상이, 10건 매도시각 상이 — 실측).
- `avg_time`은 틱 엔진의 워밍업 게이트(`self.tick_count < self.avgtime`면 평가 skip)로 **개장 직후 진입 가능 시점**을 바꾼다 (30틱 vs 60틱). `max_hold_count=1`이므로 초반 진입 1건이 달라지면 이후 하루 전체 거래열이 연쇄적으로 달라진다.
- 두 프로파일 각각의 내부 재현성은 완벽하다: 06-28 CSV 4개 md5 동일(`1bdb5d0b...`), 07-01/07-02 공식 설정 CSV들 md5 동일(`2736fd04...`). 즉 "비결정성"이 아니라 "프로파일 분기"다.

**권장 동결 프로파일: 2026-06-28 프로파일 (betting="5", avg_time=30, engine 64, tick, 90000–92800).** 근거는 하단 참조.

---

## 1. 두 기록의 출처 확정

### 1.1 2026-06-28 기록 (+3,062,696 / 190거래 / MDD 12.87)

- 문서: `docs/update_log/2026-06-28_human_process_research_loop.md` 24행
  `| human_seed_rr8_12_turnover_min_902=1.5 | 3,062,696 | 12.87 | 190 | 0.8 | 1 | backtest/csv\stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260628234642.csv |`
- 수치 원본 receipt: `artifacts/human-process-research-20260628/full_period_backtest_receipts.json`
  (`run_id: human_fullperiod_seed_replay_20260628`, gen_no 0: trade_count 190, mdd 12.87, profit 3062696.0, csv `...20260628234642.csv`)
- 같은 날 동일 수치의 독립 실행: `artifacts/12h-followup-research-20260628/fallback_validation_summary.json`
  (`run_id: follow12_fallback_oos_2025_r2`, gen_no 1: profit 3062696.0, mdd 12.87, trade_count 190, csv `...20260628095906.csv`)

### 1.2 2026-07-01 기록 (+518,822 / 175거래 / MDD 20.54)

- 문서: `docs/update_log/2026-07-01_ai_strategy_loop_branch_handoff_commit_record.md` 69행
  `| baseline | parent | 518,822 | 20.54 | 175 | 기준 |`
- 수치 원본 receipt: `artifacts/process-research-validation-20260701/result_engine64.json` → `baseline_result.metrics`
  (trade_count 175, total_profit_krw 518822, mdd_pct 20.54, seed_capital 1003101.0, csv `backtest/csv\stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260701170259.csv`)
- 실행 스크립트: `artifacts/process-research-validation-20260701/run_process_research_validation.py`
  (`AIBacktestController().research_strategy_once(cfg)` 호출, cfg는 512–541행에 하드코딩)

---

## 2. 설정 실측 비교 표

모든 값은 아래 파일에서 직접 읽은 것이다. 추정값은 "(정황)"으로 표기.

| 항목 | 2026-06-28 실행 | 2026-07-01 실행 | 차이 | 근거 파일 |
|---|---|---|---|---|
| 기간 | 20250101–20251231 | 20250101–20251231 | 동일 | `artifacts/12h-followup-research-20260628/fallback_validation_2025.json` (`bt_full_start/bt_full_end`) / `artifacts/process-research-validation-20260701/config_engine64.json` (`start_date/end_date`) |
| 시간창 | 90000–92800 | 90000–92800 | 동일 | 위 두 파일 (`bt_universe_start_time/end_time` vs `start_time/end_time`) |
| 타임프레임 | tick | tick | 동일 | `bt_timeframe: "tick"` / `is_tick: true` |
| 엔진 수 | 64 (warm) | 64 | **동일 — 32/64 가설 기각** | `fallback_validation_2025.json` (`bt_warm_engine_count: 64`) / `config_engine64.json` (`engine_count: 64`), `result_engine64.json` checkpoint `engine_processes_started {engine_count: 64}` |
| 유니버스/분배 | 전체 유니버스, `divid_mode="종목코드별 분류"` | 동일 | 동일 | `ai_strategy_loop/controller/loop.py:404-414` (`_build_warm_btconfig`) / `artifacts/12h-followup-research-20260628/engine_benchmark_32_48_64.json` measurements.config (`divid_mode`) |
| **betting (종목당 배팅)** | **"5" = 500만원** | **"1" = 100만원** | **상이 (핵심 차이 1)** | 06-28: `ai_strategy_loop/config.py:140` 기본값 `bt_betting="5"` + config JSON에 override 없음 + CSV 실측(매수금액 중앙값 5,000,419원) / 07-01: `run_process_research_validation.py:520` `"betting": "1"` + CSV 실측(매수금액 중앙값 997,815원) |
| **avg_time (평균값 계산 틱수)** | **30** | **60** | **상이 (핵심 차이 2)** | 06-28: `ai_strategy_loop/config.py:141` 기본값 `bt_avg_time=30` + 동일 warm 경로 벤치마크 receipt `engine_benchmark_32_48_64.json` (`avg_time: 30`) / 07-01: `run_process_research_validation.py:521` `"avg_time": 60`, `result_engine64.json` checkpoint `engine_data_load_requested {avg_list: [60]}` |
| seed_capital (metrics 기준자본) | 5,013,375 (betting 5 기준) | 1,003,101 | betting 종속 파생 차이 | `engine_benchmark_32_48_64.json` metrics / `result_engine64.json` baseline_result.metrics |
| 조건식 (buy/sell id) | GATE_rr8_12_turnover_min_902_1_5_B / _S | 동일 id | 동일 | `artifacts/human-process-research-20260628/human_seed_pairs.json` / `config_engine64.json` |
| 조건식 코드 동일성 | sha receipt 없음. sell 조건 분기 문자열 9종이 양 CSV에서 완전 일치(실측) → 코드 불변 (정황) | buy sha `348c5181...`, sell sha `8ef01e0e...` 기록 | 상이 증거 없음 | 07-01: `artifacts/process-research-validation-20260701/seed_condition_records.json`, `docs/research/condition_research/condition_passports/rr8_12_turnover_min_902_1.5.md` / 양쪽 CSV 매도조건 컬럼 비교 |
| DB 경로 | 명시 receipt 없음 (정황: 동일 워크트리 warm 경로; 익일 동일 레인 receipt가 같은 경로 기록) | `C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_tick_back.db` | 상이 증거 없음 | 07-01: `result_engine64.json` checkpoint `stock_back_db_selected` / 정황: `artifacts/process-research-actual-20260629/relaxed_result.json` (동일 db_path) |
| 슬리피지/체결/수수료 가정 | 공식 엔진 내장 모델(호가 스윕 체결 + 수수료/세금), per-run override 없음 | 동일 | 설정 차이 없음 — 단 betting이 체결 모델 **입력**이므로 결과 체결가는 달라짐 | `artifacts/human-process-research-20260628/baseline_setup.json` `backtestSemantics.officialBacktest` ("models betting/order amount, hoga/orderbook fill depth, and Kiwoom fees/tax") |
| exit 규칙 | sell 전략 코드 동일 (매도조건 문자열 집합 9종 완전 일치) | 동일 | 동일 | 양쪽 CSV `매도조건` 컬럼 실측 비교 |
| score 기준 CSV | (해당 없음) | `stock_bt_..._20260628234642.csv` — **betting 5 프로파일 CSV를 betting 1 실행의 score 기준으로 사용 (교차 오염)** | 별도 결함 | `config_engine64.json` `score_reference_csv`, `cli/research_loop.py:924-937` |

## 3. CSV 레벨 실측 (거래 단위 diff)

비교 대상: A = `backtest/csv/stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260628095906.csv` (190행),
B = `backtest/csv/stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260701170259.csv` (175행).

- md5 동일 그룹 (byte-identical 재현):
  - 06-28 프로파일: `20260628014938`, `20260628095906`, `20260628100641`, `20260628234642` → 모두 `1bdb5d0b...` (190거래, 매수금액 중앙값 5,000,419원, profit 3,062,696)
  - 07-01 프로파일: `20260701170259`, `20260701234317`, `20260702000718`, `20260702001243`, `20260702005928` → 모두 `2736fd04...` (175거래, 매수금액 중앙값 997,815원, profit 518,822)
- (종목명, 매수시간) 키 기준: 공통 156건 / A 전용 34건 / B 전용 19건.
- 공통 156건 중: 매도시각 동일 146건, 상이 10건; 매수가·매도가 모두 동일 81건, 체결가 상이 75건.
  - 체결가 상이 예: 유라클(매수 20250327090105) 매수가 12400 동일이나 매도가 12430(A) vs 11740(B); 대동기어(매수 20250206090557) 평균 매수체결가 15576(A) vs 15563(B) — 주문금액(500만 vs 100만)에 따른 호가 스윕 깊이 차이와 일치.
- 공통 거래의 평균 수익률: A 0.286% vs B 0.2034% — 동일 진입에서도 체결가 차이로 거래당 수익률 자체가 달라짐. 즉 profit 차이는 단순 배팅 스케일(×5)만으로 환원되지 않는다 (3,062,696/5=612,539 ≠ 518,822).
- 진입 시각 패턴: A 전용 거래 다수가 09:00:36–09:04 사이 초반 진입, B에서 같은 종목이 수십 초 늦게 진입하거나 소멸 — `avg_time` 30→60 워밍업 게이트(`backtest/backengine_kiwoom_tick.py:136` `if self.tick_count < self.avgtime: return`)와 정합.

## 4. 실행 경로 코드 근거

- 06-28 경로: `ai_strategy_loop/controller/loop.py:386-421` `_build_warm_btconfig()` —
  `avg_time=config.bt_avg_time`(409행), `betting=config.bt_betting`(412행), `engine_count=config.bt_warm_engine_count`.
  기본값: `ai_strategy_loop/config.py:140` `bt_betting: str = "5"  # 종목당 배팅(백만원 단위; 사용자 GUI=5=500만원, fidelity 핵심)`,
  `config.py:141` `bt_avg_time: int = 30  # 평균 틱수 (사용자=30)`.
  `artifacts/12h-followup-research-20260628/fallback_validation_2025.json`에는 `bt_betting`/`bt_avg_time` override 키가 없음 → 기본값 적용.
- 07-01 경로: `artifacts/process-research-validation-20260701/run_process_research_validation.py:512-541` —
  `"betting": "1"`(520행), `"avg_time": 60`(521행)을 하드코딩하여 `cli/ai_controller.py`의 `AIBacktestController.research_strategy_once`로 전달.

## 5. 권장 "공식 replay 프로파일" (동결안)

**2026-06-28 프로파일을 공식으로 동결한다.**

```json
{
  "profile_id": "official_replay_v1_20260702",
  "is_tick": true,
  "betting": "5",
  "avg_time": 30,
  "engine_count": 64,
  "start_time": 90000,
  "end_time": 92800,
  "divid_mode": "종목코드별 분류",
  "db": "_database/stock_tick_back.db",
  "replay_2025": { "start_date": 20250101, "end_date": 20251231 },
  "fallback_engine_count": 32
}
```

근거:

1. **사용자 실거래 GUI fidelity**: `ai_strategy_loop/config.py:140-141`이 betting "5"·avg_time 30을 "사용자 GUI=5=500만원, fidelity 핵심", "사용자=30"으로 명시 — 실전 세팅과의 정합이 연구 목적이다. 07-01의 betting "1"/avg_time 60은 해당 스크립트에만 존재하는 임의값으로, 코드/문서 어디에도 채택 근거 기록이 없다.
2. **기존 증거 자산과의 비교 가능성**: 2022/2023/2024/2025 4개년 OOS 검증(`fallback_validation_summary.json`), 엔진 벤치마크·48/64 결정(`engine_benchmark_32_48_64.json`, `engine_decision_receipt_48_inclusive.json`), 슬리피지 스트레스(`slippage_rr8_12_turnover_min_902_1_5.json`, betting_krw 5,000,000), 조건 passport의 prior(3,062,696/190/12.87) 전부가 06-28 프로파일 산출물이다. 07-01 프로파일을 공식화하면 이 증거 전체를 재산출해야 한다.
3. **재현성 입증량**: 06-28 프로파일은 서로 다른 4개 실행(01:49 / 09:59 / 10:06 / 23:46, 서로 다른 호출자)이 byte-identical CSV를 산출했다. (07-01 프로파일도 결정적이므로 재현성 자체는 동률이나, 검증 횟수·호출자 다양성은 06-28이 우세.)
4. **MDD 해석 안정성**: seed_capital이 betting에서 파생되므로(5,013,375 vs 1,003,101) MDD%·수익률% 지표의 역사적 연속성도 06-28 프로파일 유지가 유리하다.

부속 권고 (동결과 함께 적용):

- 모든 replay receipt에 `betting`, `avg_time`, `engine_count`, `db_path`, `start/end_time`, buy/sell `sha256`을 필수 기록한다 (07-01 run은 sha를 기록했으나 06-28 run은 누락 — 이번 포렌식에서 sell 조건 문자열 집합 일치로 보완 확인).
- `score_reference_csv`는 **동일 프로파일에서 산출된 CSV만** 허용한다. 07-01 실행은 betting 5 프로파일 CSV(`...20260628234642.csv`)를 betting 1 실행의 score 기준으로 사용했다 (`config_engine64.json`) — 교차 프로파일 점수 비교는 무효로 간주한다.
- 07-01 기록(+518,822/175/20.54)과 그 파생 quality gate 수치는 "비공식 프로파일(betting 1, avg 60) 산출물"로 주석 처리하고, 공식 비교 기준선은 06-28 프로파일 수치(+3,062,696/190/12.87)로 재고정한다.

## 6. 근거 파일 전체 목록

- `docs/update_log/2026-06-28_human_process_research_loop.md`
- `docs/update_log/2026-07-01_ai_strategy_loop_branch_handoff_commit_record.md`
- `artifacts/human-process-research-20260628/full_period_backtest_receipts.json`
- `artifacts/human-process-research-20260628/baseline_setup.json`
- `artifacts/human-process-research-20260628/human_seed_pairs.json`
- `artifacts/12h-followup-research-20260628/fallback_validation_summary.json`
- `artifacts/12h-followup-research-20260628/fallback_validation_2025.json`
- `artifacts/12h-followup-research-20260628/fallback_validation_run_receipt.json`
- `artifacts/12h-followup-research-20260628/engine_benchmark_32_48_64.json`
- `artifacts/12h-followup-research-20260628/slippage_rr8_12_turnover_min_902_1_5.json`
- `artifacts/process-research-validation-20260701/config_engine64.json`
- `artifacts/process-research-validation-20260701/result_engine64.json`
- `artifacts/process-research-validation-20260701/run_process_research_validation.py`
- `artifacts/process-research-validation-20260701/seed_condition_records.json`
- `docs/research/condition_research/condition_passports/rr8_12_turnover_min_902_1.5.md`
- `backtest/csv/stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260628095906.csv` (및 md5 동일 3개)
- `backtest/csv/stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260701170259.csv` (및 md5 동일 4개)
- `ai_strategy_loop/config.py` (140–141행), `ai_strategy_loop/controller/loop.py` (386–421행)
- `backtest/backengine_kiwoom_tick.py` (108, 136행 — avgtime 워밍업 게이트)
- `cli/research_loop.py` (924–937행 — score_reference_csv 처리)
