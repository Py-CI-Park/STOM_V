# V3K Phase G Inventory — V3 microstructure 후보 조사

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| 대상 V3 worktree | `C:/System_Trading/STOM/STOM_V.wt-3` / `STOM_Version_3` |
| 대상 2U_C worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` / `STOM_Version_2U_C` |
| Phase | G-1 / T01 |
| 결론 | `strategy/analyzer_microstructure.py`를 주 source로 삼고, backtest/trade/UI 연계 파일은 참조·검증 후보로만 둔다. |

---

## 1. 조사 기준

- V3에서 `microstructure`, 호가, 체결, 잔량, radar/chart, analyzer keyword를 포함하는 Python 파일을 조사했다.
- 2U_C에는 LS Securities 직접 의존을 들여오지 않는다.
- G-1은 engine staging만 수행하며, V3 trade runtime이나 UI runtime을 병합하지 않는다.

---

## 2. 후보 inventory

| V3 path | LOC | 관련성 | 금지 marker | G-1 판정 |
| --- | ---: | --- | --- | --- |
| `strategy/analyzer_microstructure.py` | 1137 | V3 microstructure engine 본체. 호가 imbalance, depth, layering, pump/dump, iceberg, stop-hunt, risk/signal 계산 포함 | 0 | 핵심 참조. 단, 직접 복사 대신 2U_C용 caller-owned/default-OFF skeleton으로 재구성 |
| `backtest/backengine_base.py` | 1228 | backtest에서 microstructure 결과를 사용하는 후보 경로 | 0 | G-2 parity/benchmark 참조. G-1에서는 runtime 변경 금지 |
| `trade/base_strategy.py` | 1857 | live strategy와 microstructure 결과 소비 가능성이 있는 runtime 경로 | 0 | G-1에서 절대 수정 금지. G-3 승인 전 연결 금지 |
| `utility/sub_process_and_thread/chart_hoga_query.py` | 1018 | 호가/차트 조회와 radar 표시 보조 경로 | 0 | UI/조회 참조용. G-1 engine에는 import 금지 |
| `ui/create_widget/set_dialog_chart.py` | 421 | chart/radar UI 표시 후보 | 0 | UI runtime 연결 금지. 향후 별도 UI page 후보 |
| `ui/create_widget/set_setup_tap.py` | 334 | microstructure 설정 노출 후보 | 0 | 설정 persistence와 분리. G-1에서 미수정 |
| `ui/create_widget/set_widget.py` | 1345 | radar/chart widget 구성 후보 | 0 | UI runtime 연결 금지 |
| `strategy/analyzer_risk.py` | 734 | risk analyzer와 체결강도/변동성 결합 후보 | 0 | Phase F/G 결합 smoke 때 참조 |

---

## 3. G-1 이식 결정

- 직접 이식 대상은 `strategy/v3k_microstructure_engine.py` 신규 파일 하나로 제한한다.
- V3의 `AnalyzerMicrostructure` 구조는 다음 개념만 선별 반영한다.
  - 5단계 호가 가격·잔량
  - 매수/매도 수량 기반 imbalance
  - depth ratio와 weighted depth ratio
  - concentration/pressure/risk score
  - signal/confidence output contract
- V3의 runtime integration, chart/radar UI, trade strategy consumption은 G-1에서 제외한다.

---

## 4. G-2/G-3로 넘긴 항목

| 항목 | 이유 |
| --- | --- |
| V3 baseline parity | G-2에서 별도 script와 report로 검증해야 함 |
| 성능/메모리 benchmark | G-2에서 `time.perf_counter`/`tracemalloc` 기준으로 검증해야 함 |
| live strategy consumption | G-3 사용자 승인 전 금지 |
| UI/radar 연결 | GUI/pyd wrapper 경계 검토가 별도 필요 |
| ON registry | `V3K-PHASE-G-ENABLE`은 사용자 승인 cycle에서만 생성 |
