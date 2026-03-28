# STOM 자동 조건식 탐색 — Strict / Relaxed / Exploratory Baseline 정의

- 작성일: 2026-03-14
- 브랜치: `research/auto-condition-validation-pilot`
- 목적: 성공 baseline의 기준을 표준화하여, "성공했다"는 표현이 어떤 조건에서 성립한 것인지 명확히 한다.
- 선행 문서:
  - `2026-03-13_auto_condition_discovery_strict_cli_alignment_plan.md`
  - `2026-03-13_auto_condition_discovery_generalization_verification.md`

---

## 1. 용어 정의

### 1.1 Strict Baseline

아래를 **모두** 만족하는 baseline:

| 조건 | 설명 |
|------|------|
| preset 원형 기준 사용 | `resolve_promotion_criteria(preset)` 결과를 변경 없이 적용 |
| `promotion_criteria` 오버라이드 없음 | `overrides=None` 또는 preset 원형과 동일한 값 |
| `auto_relax` 완화 미발동 | `auto_relax=False`이거나, True여도 `min_avg_trade_count`가 preset 원형 그대로 유지 |

**핵심:**
preset이 `balanced`이면 `min_avg_trade_count=50.0`이 평가에 그대로 적용되어야 strict이다.

### 1.2 Relaxed Baseline

아래 중 **하나 이상**이 적용된 baseline:

| 완화 유형 | 코드 위치 | 설명 |
|-----------|-----------|------|
| auto_relax 자동 완화 | `ai_controller.py:470-471` | `auto_relax=True` + `promotion_criteria=None` → `min_avg_trade_count=0.0` |
| CLI 기본값 완화 | `subcommands.py:149` | `--promote-min-avg-trade-count` 기본값이 `0.0` |
| 명시적 오버라이드 | `promotion.py:34-36` | `promotion_criteria`로 preset보다 느슨한 값 지정 |

**핵심:**
preset 이름이 `balanced`여도, 실제 평가 기준이 preset 원형과 다르면 relaxed이다.

### 1.3 Exploratory Baseline

연구/탐색 목적으로만 사용하는 baseline:

- 매우 짧은 검증 구간 (예: 5영업일)
- `round_count=1` (single-round만)
- `engine_count=1`
- 성공 여부 탐색이 목적이며, 실전 채택 기준으로 바로 사용하지 않음

**핵심:**
exploratory는 strict/relaxed와 독립적이다. strict이면서 exploratory일 수 있다.

---

## 2. 현재 성공 baseline 분류

### 2.1 분류 기준 흐름도

```
promotion_criteria가 None이고 auto_relax=True인가?
  └─ Yes → min_avg_trade_count=0.0으로 완화됨 → RELAXED
  └─ No  → CLI에서 min_avg_trade_count=0.0을 지정했는가?
              └─ Yes → RELAXED
              └─ No  → preset 원형 기준 그대로 적용 → STRICT
```

### 2.2 검증된 성공 사례 분류표

| 실험 | top_n | preset | auto_relax | min_avg_trade_count 실제값 | 실제 avg_trades | 분류 | 구간 |
|------|-------|--------|:----------:|:-------------------------:|:--------------:|------|------|
| A: aggressive_top1_single | 1 | aggressive | True | **0.0** (완화) | 80.0 | **RELAXED** | exploratory |
| B: aggressive_top2_single | 2 | aggressive | True | **0.0** (완화) | 70.0 | **RELAXED** | exploratory |
| C: balanced_top1_multi | 1 | balanced | True | **0.0** (완화) | 38.0 | **RELAXED** | exploratory |
| D: aggressive_top1_multi | 1 | aggressive | True | **0.0** (완화) | 미확보 | **RELAXED** | exploratory |

### 2.3 분류 해석

**현재 확보된 모든 성공 baseline은 RELAXED이다.**

이유:
- 모든 실험에서 `auto_relax=True` + `promotion_criteria=None` 조합 사용
- 이 조합은 `ai_controller.py:470-471`에서 `min_avg_trade_count=0.0`으로 자동 완화
- 실험 C는 `balanced` preset을 사용했지만, 실제 `min_avg_trade_count`는 0.0으로 평가됨
  - balanced 원형 기준(`min_avg_trade_count=50.0`)으로 평가했다면 `avg_trade_count=38.0`이므로 **불합격**

즉,
> "balanced multi-round 성공"은 사실이지만,
> "strict balanced 기준으로 성공"은 아니다.

---

## 3. Promotion Criteria 완화 로직 상세

### 3.1 완화가 발생하는 코드 경로

#### 경로 1: auto_relax 자동 완화 (내부 API)

```python
# ai_controller.py:468-471
resolved_criteria = resolve_promotion_criteria(promotion_preset, promotion_criteria)
eval_criteria = dict(resolved_criteria)
if auto_relax and promotion_criteria is None:
    eval_criteria['min_avg_trade_count'] = 0.0  # ← 완화 포인트
```

**발동 조건:** `auto_relax=True` AND `promotion_criteria is None`
**완화 내용:** `min_avg_trade_count`만 0.0으로 변경. 나머지 기준은 preset 유지.
**영향 범위:** `discover_and_promote_strategy()` 내부 전체 평가 루프

#### 경로 2: CLI 기본값 완화 (공식 CLI)

```python
# subcommands.py:149
disc_promote.add_argument('--promote-min-avg-trade-count', type=float, default=0.0)

# subcommands.py:375-379
promotion_criteria = {
    'min_rounds': parsed.promote_min_rounds,              # 기본 1
    'min_success_rate': parsed.promote_min_success_rate,  # 기본 0.6
    'min_mean_oos_metric': parsed.promote_min_mean_oos,   # 기본 0.0
    'min_avg_trade_count': parsed.promote_min_avg_trade_count,  # 기본 0.0
}
```

**발동 조건:** CLI 사용 시 `--promote-min-avg-trade-count`를 명시하지 않으면 기본 0.0
**완화 내용:** `min_avg_trade_count=0.0`이 promotion_criteria로 전달됨
**추가 효과:** `promotion_criteria`가 None이 아니므로 auto_relax 경로 1은 발동하지 않지만, 결과적으로 동일한 완화 효과

#### 경로 3: 명시적 오버라이드

```python
# promotion.py:33-36
if overrides:
    for key, value in overrides.items():
        if value is not None:
            result[key] = value  # preset 기준을 덮어씀
```

**발동 조건:** 사용자가 `promotion_criteria`에 명시적으로 느슨한 값 전달
**완화 내용:** 지정된 기준값이 preset 원형을 대체

### 3.2 완화되는 기준 요약

| 기준 | conservative | balanced | aggressive | auto_relax 완화 후 | CLI 기본값 |
|------|:-----------:|:--------:|:----------:|:-----------------:|:----------:|
| min_rounds | 3 | 2 | 1 | **변경 없음** | 1 |
| min_success_rate | 0.80 | 0.60 | 0.50 | **변경 없음** | 0.6 |
| min_mean_oos_metric | 0.10 | 0.00 | -0.10 | **변경 없음** | 0.0 |
| min_avg_trade_count | 100.0 | 50.0 | 20.0 | **→ 0.0** | **0.0** |

**결론: auto_relax는 `min_avg_trade_count` 한 가지만 완화한다.**

### 3.3 criteria_mode 판정 규칙

코드에서 `criteria_mode`를 결정하는 로직은 다음과 같다:

```
criteria_mode = 'strict'

IF auto_relax=True AND promotion_criteria is None:
    → criteria_mode = 'relaxed'  (auto_relax 자동 완화)

ELIF promotion_criteria가 주어졌고, preset 원형보다 느슨한 값이 포함됨:
    → criteria_mode = 'relaxed'  (명시적 오버라이드 완화)

ELSE:
    → criteria_mode = 'strict'
```

---

## 4. Strict 성공을 확인하려면

현재 확보된 baseline 중 strict 성공은 없다. strict 성공을 확보하려면:

### 4.1 내부 API 경로

```python
result = controller.discover_and_promote_strategy(
    name='strict_test',
    config_dict=config,
    auto_relax=False,           # ← 자동 완화 끔
    promotion_criteria=None,    # ← preset 원형 사용
    promotion_preset='balanced', # ← min_avg_trade_count=50.0 적용
    ...
)
```

### 4.2 CLI 경로

```bash
python stom_backtest.py discovery promote strict_test \
    --input result.csv \
    --promotion-preset balanced \
    --promote-min-avg-trade-count 50.0  # ← preset 원형과 동일하게 명시
```

### 4.3 예상 결과

| preset | min_avg_trade_count | 실험 C의 avg_trades (38.0) | 판정 |
|--------|:-------------------:|:-------------------------:|:----:|
| balanced (strict) | 50.0 | 38.0 < 50.0 | **FAIL** |
| aggressive (strict) | 20.0 | 38.0 > 20.0 | **PASS** |

즉, **실험 C는 strict aggressive 기준으로는 통과할 수 있지만, strict balanced로는 불합격**이다.

---

## 5. 표준 baseline 분류 체계

앞으로 성공 사례를 기록할 때 아래 형식을 사용한다.

```
Baseline: [STRICT|RELAXED] [preset] [EXPLORATORY 여부]
- criteria_mode: strict | relaxed
- preset: conservative | balanced | aggressive
- min_avg_trade_count (실제 적용값): X.X
- auto_relax: true | false
- round_count: N
- avg_trade_count (실제 결과): X.X
- 구간: YYYY-MM-DD ~ YYYY-MM-DD
```

예시:
```
Baseline: RELAXED aggressive EXPLORATORY
- criteria_mode: relaxed
- preset: aggressive
- min_avg_trade_count (실제 적용값): 0.0
- auto_relax: true
- round_count: 1
- avg_trade_count (실제 결과): 80.0
- 구간: 2025-04-07 ~ 2025-04-11
```

---

## 6. 다음 단계

1. **코드에 `criteria_mode` 필드 추가** → report JSON/Markdown에 명시적 표시
2. **strict aggressive 재검증** → 실험 A/B를 `auto_relax=False`로 재실행
3. **strict balanced 재검증** → 실험 C를 `auto_relax=False`로 재실행
4. **baseline 표준안 확정** → strict 성공 여부에 따라 권장 baseline 갱신

---

## 7. 한 줄 요약

**현재 모든 성공 baseline은 `min_avg_trade_count=0.0` 완화가 적용된 RELAXED 기준이며, strict 성공은 아직 미확인 상태다.**
