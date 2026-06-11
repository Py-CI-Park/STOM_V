# V5 슬리피지 스트레스 도구 구현 (2026-06-11)

## 배경
- 6/11 세션 핸드오프(`2026-06-11_session_handoff_full.md`) 검증 트랙 V5는 "승격 전 필수
  advisory blocker — 도구 미구현(정직 공시)" 상태였다.
- 본 빌드로 미구현 공시를 해소한다. 순수 CSV 후처리 advisory이며 엔진/하드게이트/
  backtest_graph/기존 fitness 모듈은 무수정이다(신규 파일 3개만 추가).

## 산출물
| 파일 | 역할 |
|---|---|
| `ai_strategy_loop/fitness/slippage_stress.py` | KRX 호가단위(`krx_tick_size`) + 시나리오 재계산(`stress_report_from_csvs`) |
| `ai_strategy_loop/scripts/slippage_stress_report.py` | CLI 진입점 (CSV 읽기 전용, DB 접근 금지 — `--run-id` 없음) |
| `tests/unit/test_slippage_stress.py` | 단위 테스트 18건 |

## 모델 (사전선언)
- 시나리오 = 진입 +N틱 불리 × 청산 -N틱 불리 동시 적용 + 추가 수수료 bps
  (매수금액+매도금액 합산 기준). 기본 N∈{0,1,2}, fee∈{0,5}bps.
- 수량 역산: 수량 = 수익금/(매도가-매수가). 역산 불가 행(0 나눗셈, 수량<=0)은
  추정 폴백 없이 `skipped_trades`로 정직 공시.
- MDD는 매도일 기준 일별 집계 누적곡선의 최대낙폭 금액(원).
- `breakeven_tick`: 조정수익이 틱 수에 선형임을 이용한 수익 0 틱 수 추정.
- 한계(정직 공시): 호가단위는 현재가 기준 근사(경계 통과 시 1단계 오차),
  체결 분할/부분체결 미모델링, 인샘플 CSV 기반 — **advisory 전용, 판정 규율 아님**.

## 승격 게이트 내 위치 (V5 절차)
1. 동결(select_and_freeze) 후, 동결 후보의 train CSV에 본 도구를 1회 실적용한다.
   ```powershell
   PYTHONUTF8=1 python -m ai_strategy_loop.scripts.slippage_stress_report `
     --csv <동결후보 train CSV> --out .omo/evidence/<사이클>/v5-slippage-stress.json `
     --ticks 0,1,2 --fee-bps 0,5
   ```
2. 결정 카드에 advisory blocker로 기록한다: 1틱 시나리오 retention과 breakeven_tick을
   명시하고, retention이 크게 무너지면(예: 1틱에 흑자 소멸) PROMOTE를 보류한다
   (보류 기준 자체는 운용 결정 — 카드에 수치만 정직 기록).
3. OOS/walk-forward 판정(V3/V4)은 본 도구와 무관하게 기존 규율을 따른다.

## 검증
- `PYTHONUTF8=1 python -m pytest tests/unit/test_slippage_stress.py -q` → 18 passed.
- 전체 단위 테스트: 2495 passed / 고정 실패 7건(기존 목록과 동일 — 본 빌드 영향 없음).
- CLI 스모크: 합성 CSV로 JSON 생성·수치 검산(틱당 비용 1200원/틱, 5bps 수수료 407.5원) 일치.
