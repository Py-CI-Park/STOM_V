# 2026-07-12 G2 — 기계 검사 게이트 오탐(false-reject) 실측 감사 보고서 (v2, 아키텍트 판정 반영)

> 목적: "매수/매도식이 너무 타이트하지 않은가, 기계 검사가 잘못 거부하지 않는가"를
> 운영 `_database/strategy.db`의 **검증된 인간 전략 실물**(stockbuy 102 / stocksell 47,
> `__AUTO_TMP__` 3건 제외 후 146개)에 대한 전수 실측으로 판정한다.
> 도구: `scripts/audit_gate_false_rejects.py`(읽기 전용), 산출물 `artifacts/g2_gate_false_reject_audit.json`.
>
> **v2 정정**: v1은 `back_code_test.py`(저장 시점 검증기)를 진실 공급원으로 삼아
> `강제청산/매도수량` 허용을 오탐 교정이라 판정했으나, 아키텍트 리뷰(5-G2ArchitectReview,
> product lane BLOCK)가 범주 혼동을 입증했다 — **가드의 계약은 백테 엔진 exec env**
> (backengine_* Strategy 스코프)이고 그 env에 두 이름은 없다(허용 시 NameError→BackStop
> 무신호→타임아웃 홀 재개방, exemplar_pool로 GUI 매도 29건이 few-shot 후보화되는 노출 포함).
> 해당 화이트리스트 추가는 **철회**했고, 양 kind·양 timeframe 거부를 회귀 테스트로 고정했다.

## 1. 검사별 실측 (최종)

| 검사 | 대상 | 거부 | 거부율 | 오탐 판정 |
|---|---:|---:|---:|---|
| variable_scope | 197평가* | 72 | 36.5% | **오탐 0건 확정** — 전 사유가 루프-호환성 근거 있음(§2) |
| token_check | 146 | 1 | 0.7% | 정탐(실제 구문 오류 1건) |
| filter_gate(범주≥5) | 매수 99 | 10 | 10.1% | 의도적 타이트(§3) |
| exec_budget(윈도우≤8) | 매도 47 | 20 | 42.6% | 의도적 타이트(§3) |
| principle_gate(CSC) | 짝 38(평가 41) | 24 | 58.5% | 문맥 차이(§3) |
| **어느 검사든 거부** | 146 | 103 | **70.5%** | — |

\* variable_scope는 timeframe 불확실 전략을 tick/min 양쪽에서 평가(both 분류)하므로 평가 수 > 전략 수.

## 2. 스코프 거부 사유 전수 분류 — 오탐 0건

판정 기준(아키텍트 확정): **진실 공급원 = 백테 엔진 exec env**. `backengine_kiwoom_tick/min`의
sell exec env는 {포지션, 수익금, 수익률, 최고/최저수익률, 보유시간, 매수가, 보유수량}(+OMS 변형)이며,
저장 시점 검증기(back_code_test.py)는 GUI 라이브 이름까지 포함한 superset이라 근거가 될 수 없다.

| 사유(건수) | 분류 | 설명 |
|---|---|---|
| `매수수량`(34), `매도수량`(29), `강제청산`(29) | **정탐 — GUI 라이브 전용** | 인간 운영 시그니처 `self.Buy(종목코드, 종목명, 매수수량, ...)` / `self.Sell(종목코드, 종목명, 매도수량, 강제청산)`가 쓰는 이름. 루프 백테 엔진 env에 없어 exec 시 NameError(엔진 Sell 시그니처는 `Sell(sell_long=False)`) → 가드가 정확히 막은 것 |
| `VI아래5호가`(12) | 정탐 + **신규 발견** | trade/·backtest/ 전수 검색에서 엔진 정의 없음. 그런데 `brain/seed_902_band.py`(밴드 시드)가 사용 — 밴드 경로 실행 전 검증 필요(원장 기록, §4) |
| `분당*`/`분봉*`(각 7~8), bare `RSI/MACD/BBM` 등(1~5) | 교차평가 잡음 | both-분류 전략의 tick측 평가에서 min 전용 계열이 위반으로 잡힌 것 — min측 평가는 통과. **가드가 정확히 작동한 증거** |
| `분당순매수금액`(1), `최고등락율각도`(1) | 정탐 | 화이트리스트·SetGlobalsFunc 미존재 이름(`초당순매수금액`도 동일 — seed_902_band 사용, §4) |

**이번 커밋 계열의 실제 가드 변경은 강화 1건뿐**: 파생 접두 가드 홀 교정 —
`누적초당*/누적분당*/최고초당*/최고분당*`이 공통 취급되던 결함을 계열 전용으로 분류
(양방향 회귀 8시나리오/7테스트, dict_add_func 181개 전수 대조로 오분류 0 확인 — QA B5).
추가로 GUI 라이브 전용 3이름의 전-조합(kind×timeframe) 거부를 회귀 테스트로 고정했다.

## 3. "너무 타이트한가?" — 게이트별 정직 판정

- **variable_scope**: 오탐 0건. 거부 36.5%의 실체는 "인간 운영(GUI 라이브) 전략과 루프
  정규형의 **호스트 환경 차이**"다. 함의: 인간 전략을 루프 시드/few-shot으로 재사용할 때
  GUI 시그니처 호출(`self.Buy(인자...)`)은 정규형(bare `self.Buy()`)으로 변환해야 한다.
- **filter_gate(범주 5+)**: 인간 매수 10.1%가 2~4범주 미달 — 인간 실전 기준 다소 타이트하나
  §3.22 과발화 실측 근거의 연구 lane 전용 게이트(기본 OFF)라 유지.
- **exec_budget(윈도우 ≤8)**: 인간 매도 42.6%(20/47)가 9~11개 호출 — 명백히 타이트하나
  2026-06-10 warm 타임아웃 11/11 분리 실측 근거로 유지. 인간 매도를 seed-refine 출발점으로
  쓸 때 42.6%가 걸린다는 마찰 비용을 문서화.
- **principle_gate CSC-10**(26건): 인간 tick 매도 대부분이 시분초 강제청산 분기 없음 — 운영
  GUI는 장중 전체 데이터라 불필요했던 것. 연구 lane(tick 데이터 09:30 캡)에선 의도적 요구.
  CSC-07 손절 부재 2건은 정탐.

**종합**: "기계 검사가 잘못 거부하는가?" → **아니오 — 전수 감사 결과 확정 오탐 0건.**
초기 오탐 후보 2종(강제청산/매도수량)은 진실 공급원 재검토에서 정탐으로 뒤집혔고, 그 과정
자체가 가드 계약("엔진 exec env가 유일 기준")을 문서·주석·테스트로 명문화하는 성과가 됐다.
게이트의 타이트함은 전부 실측 근거(과발화/타임아웃/데이터 경계)가 있으며, 비용은 "인간 운영
전략 재사용 시 변환 필요"로 정량화됐다(스코프 92건·budget 20건·CSC-10 26건).

## 4. 신규 발견 (팔로우업 등록, 원장 주석)

- `VI아래5호가`, `초당순매수금액`: 화이트리스트·엔진 정의 미확인인데 `brain/seed_902_band.py`
  (밴드 시드 P0)가 사용 — 밴드 컴파일 산출물의 백테 NameError 잠재 위험. 밴드 경로 실행 전 검증 필요.
- 선재 홀(아키텍트 P3): 기존 `분할매수횟수/분할매도횟수`도 kiwoom 엔진 sell env 바인딩과
  어순 불일치(OMS는 `매수분할횟수/매도분할횟수`) — sell 스코프의 엔진-env AST 도출 전환 시 함께 재감사.
- 장기 개선(아키텍트 옵션 C): sell 스코프를 backengine Strategy() unpack에서 AST로 도출해
  진실 공급원을 엔진 단일화(_derive_setglobals_names와 동일 패턴).

## 5. 재현

```powershell
PYTHONUTF8=1 python scripts/audit_gate_false_rejects.py   # → artifacts/g2_gate_false_reject_audit.json
PYTHONUTF8=1 python -m pytest tests/unit/test_audit_gate_false_rejects.py tests/unit/test_variable_scope_cumulative_prefix.py -q
```
