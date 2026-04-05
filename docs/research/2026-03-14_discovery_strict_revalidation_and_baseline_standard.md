# STOM 자동 조건식 탐색 — Strict 재검증 결과 및 Baseline 표준안

- 작성일: 2026-03-14
- 브랜치: `research/auto-condition-validation-pilot`
- 선행 문서:
  - `2026-03-14_discovery_baseline_strict_relaxed_definitions.md`
  - `2026-03-13_auto_condition_discovery_generalization_verification.md`
- 목적:
  1. 기존 성공 실험 결과에 strict 기준을 적용하여 통과 여부를 확인한다.
  2. 실험 재실행 없이 분석적으로 판정할 수 있는 근거를 설명한다.
  3. 최종 권장 baseline 표준안을 확정한다.

---

## 1. 재실행 없이 분석 가능한 근거

기존 실험 A/B/C 모두 `zero_trade_rounds=0`이었다.
이는 auto_relax의 재시도 루프가 한 번도 발동하지 않았음을 의미한다.

auto_relax가 실제로 변경한 것은 **평가 기준**(`min_avg_trade_count=0.0`)뿐이다.
WFO 실행 결과(round_count, mean_oos_metric, avg_trade_count, success_rate)는
`auto_relax=True`든 `False`든 동일하다.

따라서 **기존 WFO 결과에 strict 기준을 적용하면 재실행과 동일한 판정**을 얻을 수 있다.

---

## 2. Promotion Preset 원형 기준표

| 기준 | conservative | balanced | aggressive |
|------|:-----------:|:--------:|:----------:|
| min_rounds | 3 | 2 | 1 |
| min_success_rate | 0.80 | 0.60 | 0.50 |
| min_mean_oos_metric | 0.10 | 0.00 | -0.10 |
| min_avg_trade_count | 100.0 | 50.0 | 20.0 |

---

## 3. 기존 실험 결과 (재확인)

| 실험 | top_n | WFO 설정 | round_count | mean_oos_metric | avg_trade_count | zero_trade_rounds |
|------|:-----:|----------|:-----------:|:---------------:|:---------------:|:-----------------:|
| A: aggressive_top1_single | 1 | train=3/test=2/step=3 | 1 | 0.55 | 80.0 | 0 |
| B: aggressive_top2_single | 2 | train=3/test=2/step=3 | 1 | 0.60 | 70.0 | 0 |
| C: balanced_top1_multi | 1 | train=2/test=1/step=2 | 2 | 0.35 | 38.0 | 0 |

- 모든 실험에서 success_rate=1.0 (모든 라운드 수익 양수)
- 모든 실험에서 auto_relax 재시도 미발동

---

## 4. Strict 기준 적용 결과

### 4.1 Strict Aggressive (min_rounds=1, min_success_rate=0.50, min_oos=−0.10, min_avg_trades=20.0)

| 실험 | round_count≥1 | success_rate≥0.50 | oos_metric≥−0.10 | avg_trades≥20.0 | 판정 |
|------|:---:|:---:|:---:|:---:|:---:|
| A | 1≥1 ✅ | 1.0≥0.50 ✅ | 0.55≥−0.10 ✅ | 80.0≥20.0 ✅ | **PASS** |
| B | 1≥1 ✅ | 1.0≥0.50 ✅ | 0.60≥−0.10 ✅ | 70.0≥20.0 ✅ | **PASS** |
| C | 2≥1 ✅ | 1.0≥0.50 ✅ | 0.35≥−0.10 ✅ | 38.0≥20.0 ✅ | **PASS** |

> **결론: 3건 모두 strict aggressive 통과.**

### 4.2 Strict Balanced (min_rounds=2, min_success_rate=0.60, min_oos=0.00, min_avg_trades=50.0)

| 실험 | round_count≥2 | success_rate≥0.60 | oos_metric≥0.00 | avg_trades≥50.0 | 판정 |
|------|:---:|:---:|:---:|:---:|:---:|
| A | 1<2 ❌ | — | — | — | **FAIL** (라운드 부족) |
| B | 1<2 ❌ | — | — | — | **FAIL** (라운드 부족) |
| C | 2≥2 ✅ | 1.0≥0.60 ✅ | 0.35≥0.00 ✅ | 38.0<50.0 ❌ | **FAIL** (거래 수 부족) |

> **결론: 3건 모두 strict balanced 불합격.**
> - A, B는 round_count 미달 (single-round로 실행)
> - C는 avg_trade_count 미달 (38.0 < 50.0, 차이 12건)

### 4.3 Strict Conservative (min_rounds=3, min_success_rate=0.80, min_oos=0.10, min_avg_trades=100.0)

| 실험 | round_count≥3 | 판정 |
|------|:---:|:---:|
| A | 1<3 ❌ | **FAIL** |
| B | 1<3 ❌ | **FAIL** |
| C | 2<3 ❌ | **FAIL** |

> **결론: 3건 모두 strict conservative 불합격.**

---

## 5. 핵심 발견

### 5.1 Strict Aggressive 성공 확정

**기존 3건의 성공 baseline은 모두 strict aggressive 기준으로도 통과한다.**

이는 relaxed 완화(`min_avg_trade_count=0.0`)가 없어도 성공한다는 의미다.
즉, 현재 시스템의 성공이 완화 기준에만 의존한 것이 아니라 실질적인 성과가 있음을 확인했다.

### 5.2 Strict Balanced는 아직 미달

실험 C가 가장 가까웠으나 `avg_trade_count=38.0`이 기준 `50.0`에 12건 부족하다.

strict balanced 통과를 위한 방법:
1. 검증 구간을 늘려 거래 수 확보 (현재 5영업일은 매우 짧음)
2. top_n을 줄여 필터 강도를 낮추기 (이미 top_n=1)
3. WFO window를 늘려 round당 거래 수 확보

### 5.3 Auto-Relax는 실질적으로 불필요했음

3건 모두 `zero_trade_rounds=0`이었으므로, auto_relax 재시도가 한 번도 발동하지 않았다.
auto_relax의 유일한 효과는 `min_avg_trade_count` 평가 완화뿐이었다.

---

## 6. 최종 Baseline 표준안

### 6.1 권장 Baseline A — STRICT aggressive (실전 사용 가능)

```
Baseline: STRICT aggressive EXPLORATORY
- criteria_mode: strict
- preset: aggressive
- min_avg_trade_count (실제 적용값): 20.0
- auto_relax: false
- top_n: 1
- base_buy_strategy: Min_B_Study_251227
- 결합 방식: 기존 매수 전략 + 자동 필터
- WFO: train=3일 / test=2일 / step=3일
- engine_count: 1
```

**CLI 명령어:**
```bash
python stom_backtest.py discovery promote Auto_B_StrictAgg \
    --input backtest/csv/result.csv \
    --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --train-window-days 3 --test-window-days 2 --step-days 3 \
    --engines 1 --top-n 1 \
    --base-buy-strategy Min_B_Study_251227 \
    --promotion-preset aggressive \
    --promote-min-avg-trade-count 20.0 \
    --report-json report.json --report-md report.md
```

**검증 근거:** 실험 A/B/C 모두 strict aggressive 통과 확인 (avg_trade_count 38~80)

### 6.2 권장 Baseline B — RELAXED aggressive (연구/탐색용)

```
Baseline: RELAXED aggressive EXPLORATORY
- criteria_mode: relaxed
- preset: aggressive
- min_avg_trade_count (실제 적용값): 0.0
- auto_relax: true
- top_n: 1~2
- base_buy_strategy: Min_B_Study_251227
- 결합 방식: 기존 매수 전략 + 자동 필터
- WFO: train=3일 / test=2일 / step=3일
- engine_count: 1
```

**CLI 명령어:**
```bash
python stom_backtest.py discovery promote Auto_B_RelaxedAgg \
    --input backtest/csv/result.csv \
    --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --train-window-days 3 --test-window-days 2 --step-days 3 \
    --engines 1 --top-n 1 \
    --base-buy-strategy Min_B_Study_251227 \
    --auto-relax \
    --promotion-preset aggressive \
    --report-json report.json --report-md report.md
```

**용도:** 탐색/실험. 다양한 필터 조합 빠르게 시도할 때 사용.

### 6.3 미달 Baseline — STRICT balanced (향후 목표)

```
Baseline: STRICT balanced (미달)
- criteria_mode: strict
- preset: balanced
- min_avg_trade_count (실제 적용값): 50.0
- 현재 상태: avg_trade_count=38.0으로 미달 (차이 12건)
- 달성 조건: 검증 구간 확대 또는 WFO window 조정 필요
```

---

## 7. 다음 단계 연결

strict/CLI 기준 정리가 완료되었다. 다음 순서:

1. **P3: `analyzer.py` 테스트 보강** — 9개 경계 조건 테스트 추가
2. **P4: `ml_factor_model.py` 테스트 보강** — 6개 경계 조건 테스트 추가
3. **향후: strict balanced 달성** — 검증 구간 확대 실험
4. **향후: P5/P6** — config 객체화, fillna 전략 개선

---

## 8. 한 줄 요약

**기존 성공 baseline 3건은 모두 strict aggressive 기준으로 통과하며, 이는 완화 기준 없이도 실질적 성과가 있음을 확인한 것이다. strict balanced는 avg_trade_count 12건 부족으로 미달.**
