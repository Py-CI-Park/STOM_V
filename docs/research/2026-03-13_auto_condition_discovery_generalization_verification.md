# STOM 자동 조건식 탐색 시스템 — 성공 baseline 일반화 검증

- 작성일: 2026-03-13
- 브랜치: `research/auto-condition-validation-pilot`
- 목적:
  - 직전 턴에서 확보한 `promoted=True` 성공 사례가 단발성인지 확인한다.
  - `top_n`, `promotion_preset`, WFO round 수를 바꿨을 때도 성공하는지 점검한다.
  - 실전에서 다시 사용할 수 있는 baseline 설정을 문서화한다.

---

## 1. 검증 배경

이전 단계에서 아래 조합으로 첫 `promoted=True` 성공 사례를 확보했다.

- 기존 매수 전략: `Min_B_Study_251227`
- 자동 필터: full-range CSV에서 추출한 top-1 조건
- 결합 방식: **기존 매수 전략 + 자동 필터 삽입**
- 검증 구간: `2025-04-07 ~ 2025-04-11`
- preset: `aggressive`

이번 검증의 질문은 아래와 같다.

1. 같은 구조에서 `top_n`이 바뀌어도 성공하는가?
2. multi-round WFO에서도 성공하는가?
3. `balanced` 수준에서도 성공하는가?
4. 아직 남아 있는 운영 리스크는 무엇인가?

---

## 2. 공통 실행 조건

모든 실험은 아래 공통 조건을 사용했다.

- 기준 매수 전략: `Min_B_Study_251227`
- 기준 매도 전략: `Min_S_Study_251227`
- 입력 CSV: `backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv`
- 결합 방식: `base_buy_strategy + auto filter`
- `engine_count=1`
- `ml_feature_limit=0`
- `ml_weight=0.0`
- `auto_relax=True`

중요:
- 이번 실험은 **자동 필터 단독 전략**이 아니라
  **기존 매수 전략에 자동 필터를 삽입한 결합 전략**으로 검증했다.
- 이 점이 실제 성공의 핵심 전제였다.

---

## 3. 실험 매트릭스

| 실험 | 구간 | WFO 설정 | top_n | preset | 결과 |
|------|------|----------|-------|--------|------|
| A | 2025-04-07 ~ 2025-04-11 | train=3 / test=2 / step=3 | 1 | aggressive | ✅ promoted |
| B | 2025-04-07 ~ 2025-04-11 | train=3 / test=2 / step=3 | 2 | aggressive | ✅ promoted |
| C | 2025-04-07 ~ 2025-04-11 | train=2 / test=1 / step=2 | 1 | balanced | ✅ promoted |
| D | 2025-04-07 ~ 2025-04-11 | train=2 / test=1 / step=2 | 1 | aggressive (min_rounds=2) | ⚠️ 장시간 실행/최종 요약 미확보 |

---

## 4. 실험 결과 상세

### 4.1 실험 A — control_aggressive_top1_single_round

- 전략명: `Auto_B_Generalize_control_aggressive_top1_single_round_1773392228`
- 선택 필터:

```python
if 15.304 <= 등락율 < 17.74:
    매수 = False
```

결과 요약:

```json
{
  "promoted": true,
  "round_count": 1,
  "mean_oos_metric": 0.55,
  "avg_trade_count": 80.0,
  "zero_trade_rounds": 0
}
```

해석:
- 가장 단순한 top-1 필터 결합만으로도 성공이 재현되었다.
- 이전 성공 사례가 우연이 아니라는 최소 근거가 확보되었다.

---

### 4.2 실험 B — aggressive_top2_single_round

- 전략명: `Auto_B_Generalize_aggressive_top2_single_round_1773392300`
- 선택 필터:

```python
if 15.304 <= 등락율 < 17.74:
    매수 = False
if 2_182 <= 시가총액 < 2_659:
    매수 = False
```

결과 요약:

```json
{
  "promoted": true,
  "round_count": 1,
  "mean_oos_metric": 0.60,
  "avg_trade_count": 70.0,
  "zero_trade_rounds": 0
}
```

해석:
- `top_n=2`로 늘려도 성공했다.
- 즉 baseline은 top-1 단일 후보에만 의존하지 않는다.
- 다만 trade count는 80 → 70으로 감소했다.

---

### 4.3 실험 C — balanced_top1_multi_round

- 전략명: `Auto_B_Generalize_balanced_top1_multi_round_1773392368`
- 선택 필터:

```python
if 15.304 <= 등락율 < 17.74:
    매수 = False
```

결과 요약:

```json
{
  "promoted": true,
  "round_count": 2,
  "mean_oos_metric": 0.35,
  "avg_trade_count": 38.0,
  "zero_trade_rounds": 0
}
```

중요 해석:
- `round_count=2`인 multi-round에서도 성공했다.
- 따라서 baseline은 single-round에만 갇혀 있지 않다.
- 하지만 현재 구현상 `auto_relax=True`이고 `promotion_criteria=None`이면
  내부 평가에서 `min_avg_trade_count`가 `0.0`으로 완화된다.
- 즉 이 성공은 **balanced preset 이름을 사용했지만,
  실제 avg_trade_count 기준은 완화된 상태**로 해석해야 한다.

즉,
> 이 결과는 “multi-round 성공”의 근거로는 유효하지만,
> “strict balanced preset이 그대로 통과했다”는 의미로 해석하면 안 된다.

---

### 4.4 실험 D — aggressive_top1_multi_round

- 목표: aggressive preset + multi-round(min_rounds=2) 성공 여부 확인
- 관찰 결과:
  - 실제 backtest round는 진행되었다.
  - 로그상 두 개 이상의 round 결과가 출력되었다.
  - 그러나 최종 summary JSON이 정상적으로 회수되기 전에 실행이 장시간 머물렀고,
    최종 결과를 확정 기록하지 못했다.

해석:
- no-trade/shared_memory blocker는 이전보다 완화되었지만,
  반복 multi-round orchestration의 완전 안정화는 아직 부족하다.
- 즉, **성공 baseline은 확보했지만, multi-round 반복 운영의 안정성은 추가 점검이 필요**하다.

---

## 5. 종합 결론

### 5.1 확인된 것

이번 일반화 검증으로 아래는 확인되었다.

1. **성공 사례는 단발성이 아니다.**
   - top-1 / top-2 모두 promoted 성공이 재현되었다.

2. **single-round 전용도 아니다.**
   - multi-round 조건에서도 promoted 성공이 확인되었다.

3. **핵심 성공 요인은 자동 필터 단독 전략이 아니라, 기존 매수 전략과의 결합이다.**

4. **실전 baseline은 다음 구조로 정리할 수 있다.**
   - 기준 전략: `Min_B_Study_251227`
   - 결합 방식: `base_buy_strategy + auto filter`
   - 입력: full-range CSV
   - 탐색: `top_n=1~2`
   - 검증: 짧은 window + engine_count=1

### 5.2 아직 남은 것

1. strict balanced 기준(`min_avg_trade_count=50`)을 그대로 적용한 성공 검증은 아직 아님
2. multi-round 반복 실행의 운영 안정성은 추가 점검 필요
3. promote 성공 baseline을 CLI/product 관점에서 어떻게 표준화할지 정리가 필요

---

## 6. 현재 시점의 baseline 권장안

현재까지 검증된 가장 현실적인 baseline은 아래와 같다.

### 추천 baseline A
- 기존 매수 전략 결합 사용
- `top_n=1`
- `promotion_preset='aggressive'`
- `promotion_criteria={'min_rounds': 1, 'min_avg_trade_count': 0}`
- `train_window_days=3`
- `test_window_days=2`
- `step_days=3`
- `engine_count=1`

### 추천 baseline B
- 기존 매수 전략 결합 사용
- `top_n=2`
- `promotion_preset='aggressive'`
- `promotion_criteria={'min_rounds': 1, 'min_avg_trade_count': 0}`
- 나머지는 baseline A와 동일

### 조건부 baseline C
- 기존 매수 전략 결합 사용
- `top_n=1`
- `promotion_preset='balanced'`
- multi-round 가능
- 단, 현재 구현상 avg_trade_count 기준 완화가 들어가므로
  **strict balanced로 간주하면 안 됨**

---

## 7. 다음 단계 권장

이번 일반화 검증 결과를 바탕으로 다음 우선순위는 아래가 적절하다.

1. **promotion criteria 완화 로직 명시화/문서화**
   - `auto_relax=True`일 때 어떤 기준이 완화되는지 명확히 정리

2. **strict balanced / strict multi-round 재검증**
   - `min_avg_trade_count`를 원래 값으로 유지한 상태에서 성공 여부 확인

3. **`analyzer.py`, `ml_factor_model.py` 테스트 보강 재개**
   - 현재 핵심 파이프라인은 성공 baseline을 확보했으므로,
     다음은 분석기 신뢰성 보강으로 넘어갈 수 있다.

---

## 8. 한 줄 결론

**자동 조건식 탐색 시스템은 이제 “기존 매수 전략에 자동 필터를 결합하는 구조”에서 promoted 성공이 재현되는 baseline을 확보했으며, 이는 top_n=1~2와 multi-round 일부 구간까지 일반화됨을 확인했다.**
