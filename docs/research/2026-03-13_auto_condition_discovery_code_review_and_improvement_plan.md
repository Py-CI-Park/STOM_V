# STOM 자동 조건식 탐색 시스템 — 구현 검토 보고서 및 개선 계획

- 작성일: 2026-03-13
- 브랜치: `research/auto-condition-validation-pilot`
- 검토 기준: `docs/research/auto_condition_discovery_research.md` + `docs/research/2026-03-10_auto_condition_discovery_implementation_checklist.md`
- 검토 방법: Architect 에이전트 (Claude Opus) 심층 분석
- 종합 등급: **B+**

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [계획 대비 이행률](#2-계획-대비-이행률)
3. [계획 초과 달성 항목](#3-계획-초과-달성-항목)
4. [설계 원칙 준수 여부](#4-설계-원칙-준수-여부)
5. [테스트 커버리지](#5-테스트-커버리지)
6. [리스크 항목](#6-리스크-항목)
7. [개선 권장 사항 및 상세 구현 계획](#7-개선-권장-사항-및-상세-구현-계획)
8. [종합 평가](#8-종합-평가)

---

## 1. 프로젝트 개요

### 목적

백테스트 결과 CSV에서 손실 패턴을 자동으로 탐지하여
전략 매수 조건 필터 코드(`if 조건: 매수 = False`)를 자동 생성하는
end-to-end 파이프라인을 구축한다.

### 전체 파이프라인

```
[백테스트 실행]
  └─ B_*/S_*/R_* 컬럼 포함 상세 CSV 생성
       └─ discover analyze       : 시간대/시가총액/분위수/t-test 통계 분석
            └─ discover ml-analyze   : RandomForest/GradientBoosting 팩터 분석
                 └─ discover generate    : 조건식 Python 코드 생성
                      └─ discover create-strategy : 전략 DB 임시 저장
                           └─ discover promote      : WFO 검증 → 채택/미채택
                                └─ [마크다운 리포트 저장]
```

### 구현 규모

| 파일 | 줄수 | 역할 |
|------|------|------|
| `cli/analyzer.py` | 400 | 통계 분석기 |
| `cli/condition_generator.py` | 174 | 조건식 코드 생성기 |
| `cli/wfo.py` | 188 | Walk-Forward Optimization |
| `cli/ml_factor_model.py` | 146 | ML 팩터 분석기 |
| `cli/ai_controller.py` | 753 | 통합 파사드 |
| `cli/discovery_report.py` | 117 | 마크다운 리포트 생성기 |
| `cli/promotion.py` | 38 | 채택 기준 프리셋 |
| `cli/subcommands.py` | 406 | 공식 CLI 서브커맨드 |
| **합계** | **2,222** | |

---

## 2. 계획 대비 이행률

### 2.1 Phase 0/1 — 데이터 확장 (이행률 92%)

| 체크리스트 항목 | 파일 위치 | 상태 |
|----------------|-----------|------|
| B_* 컬럼 14개 정의 | `back_static.py:35-38` | ✅ 완료 |
| S_* 컬럼 5개 정의 | `back_static.py:39-43` | ✅ 완료 |
| R_* 컬럼 4개 정의 | `back_static.py:44-46` | ✅ 완료 |
| 일반 엔진 매수 시점 스냅샷 | `backengine_base.py:424-438` | ✅ 완료 |
| OMS 엔진 동일 반영 | `backengine_base_oms.py:392-394` | ✅ 완료 |
| subtotal 가변 언패킹 | `back_subtotal.py:84` | ✅ 완료 |
| DataFrame 컬럼 확장 | `back_static.py:686-698` | ✅ 완료 |
| CSV 저장 (UTF-8-SIG) | `backtest.py:205-207` | ✅ 완료 |
| 최초 매수 시점 기준 스냅샷 | `backengine_base.py:470-504` | ✅ 완료 |
| `optimiz.py` 영향도 확인 | — | ⚠️ **미확인** |
| `rolling_walk_forward_test.py` 영향도 확인 | — | ⚠️ **미확인** |

**구현된 컬럼 명세:**

```python
TRADE_RESULT_B_COLUMNS = [
    'B_현재가', 'B_등락율', 'B_당일거래대금', 'B_거래대금증감', 'B_체결강도',
    'B_시가총액', 'B_회전율', 'B_전일동시간비', 'B_매수총잔량', 'B_매도총잔량',
    'B_시분초', 'B_분봉시가', 'B_분봉고가', 'B_분봉저가'      # 14개
]
TRADE_RESULT_S_COLUMNS = [
    'S_현재가', 'S_등락율', 'S_체결강도', 'S_매수총잔량', 'S_매도총잔량'  # 5개
]
TRADE_RESULT_R_COLUMNS = [
    'R_매수후최고수익률', 'R_매수후최저수익률', 'R_MFE', 'R_MAE'           # 4개
]
```

### 2.2 Phase 2+ — 분석기/생성기/WFO (이행률 95%)

| 계획 항목 | 구현 함수 | 상태 |
|-----------|-----------|------|
| 시가총액 구간 분석 | `analyze_market_cap_segments()` | ✅ 완료 |
| 시간대 분석 | `analyze_time_segments()` | ✅ 완료 |
| 분위수 분석 | `generate_quantile_candidates()` | ✅ 완료 |
| FDR(Benjamin-Hochberg) 적용 | `benjamini_hochberg()` | ✅ 완료 |
| 최소 샘플 수 필터 | 전 함수에 `min_samples=30` | ✅ 완료 |
| 조건식 코드 생성 (주석 포함) | `generate_condition_code()` | ✅ 완료 |
| Purged Walk-Forward | `generate_walk_forward_windows()` | ✅ 완료 |
| OOS 성과 검증 | `run_walk_forward()` | ✅ 완료 |
| ML 통합 | `analyze_results_ml()` | ✅ 완료 (계획에 "미정"이었음) |
| RL 통합 | — | ❌ 미구현 (계획에도 미정, 적절) |

---

## 3. 계획 초과 달성 항목

계획 문서에 명시되지 않았으나 실제로 구현된 기능:

### 3.1 ML 팩터 분석기

- **위치**: `cli/ml_factor_model.py` (146줄)
- **내용**: RandomForest / GradientBoosting 선택, TimeSeriesSplit 교차검증, SHAP 선택적 지원
- **가치**: 통계(t-test)로 포착 어려운 비선형 피처 중요도 탐지. 후보 정렬에 직접 연동

### 3.2 채택 기준 프리셋 시스템

- **위치**: `cli/promotion.py` (38줄)
- **내용**:

| 프리셋 | min_rounds | success_rate | oos_metric | avg_trades |
|--------|-----------|--------------|------------|------------|
| `conservative` | 3 | ≥ 80% | ≥ 0.10 | ≥ 100 |
| `balanced` | 2 | ≥ 60% | ≥ 0.00 | ≥ 50 |
| `aggressive` | 1 | ≥ 50% | ≥ -0.10 | ≥ 20 |

- **가치**: 채택 기준 하드코딩 방지, 재현성 확보, 상황별 유연한 적용

### 3.3 공식 CLI 서브커맨드 승격

- **위치**: `cli/subcommands.py` (406줄)
- **내용**: library-only에서 `stom_backtest.py discover` 공식 CLI로 승격

```bash
python stom_backtest.py discover analyze        --result-csv {path}
python stom_backtest.py discover ml-analyze     --result-csv {path} --model gradient_boosting
python stom_backtest.py discover generate       --result-csv {path} --with-ml --top-n 5
python stom_backtest.py discover create-strategy --strategy {name}
python stom_backtest.py discover promote        --strategy {name} --wfo-preset balanced
```

### 3.4 파이럿 실행에서 즉시 수정된 버그

| 버그 | 수정 위치 | 내용 |
|------|-----------|------|
| B_ 접두사 NameError | `condition_generator.py:23-26` | `B_시가총액` → `시가총액` 런타임 변환 (`runtime_context` 파라미터) |
| zero_trade_rounds 누락 | `wfo.py:157`, `ai_controller.py:336-342` | 거래 0회 라운드 감지 및 `all_rounds_no_trades` 평가 항목 추가 |
| Windows AssertionError | `runner.py:49-63` | 프로세스 정리 시 `is_alive()` 예외 try/except 처리 |
| 리포트에 조건식 미표시 | `discovery_report.py:30-33, 87-94` | `expressions` 섹션 추가 |

---

## 4. 설계 원칙 준수 여부

| 원칙 | 준수 | 근거 |
|------|------|------|
| B_* 전용 피처 (S_*/R_* 누수 방지) | ✅ | `analyzer.py:70` `get_feature_columns(prefix='B_')` + 코드 주석 명시 |
| library-only 모듈 | ✅ | analyzer/generator/wfo/ml 모두 `import argparse` 없음 |
| CLI는 subcommands.py에만 집중 | ✅ | argparse 정의가 단일 파일에만 존재 |
| scipy 선택적 의존 | ✅ | `analyzer.py:17-20` `try/except ImportError` |
| 불변성 (`df.copy()`) | ✅ | 모든 DataFrame 처리 함수에서 일관 적용 |
| 예외 throw 없는 dict 반환 API | ✅ | 모든 메서드 `{'status': 'error', 'message': str(e)}` 반환 |

---

## 5. 테스트 커버리지

| 모듈 | 구현 | 테스트 | 비율 | 평가 |
|------|------|--------|------|------|
| `analyzer.py` | 400줄 | 74줄 | 0.19 | 🔴 부족 |
| `condition_generator.py` | 174줄 | 94줄 | 0.54 | 🟡 양호 |
| `wfo.py` | 188줄 | 138줄 | 0.73 | 🟢 우수 |
| `ml_factor_model.py` | 146줄 | 43줄 | 0.29 | 🔴 부족 |
| `ai_controller.py` | 753줄 | 596줄 | 0.79 | 🟢 우수 |
| `discovery_report.py` | 117줄 | 61줄 | 0.52 | 🟡 양호 |
| `promotion.py` | 38줄 | 17줄 | 0.45 | 🟡 양호 |
| `subcommands.py` | 406줄 | 506줄 | 1.25 | 🟢 우수 |
| **합계** | **2,222줄** | **2,037줄** | **0.92** | 🟡 양호 |

**주요 갭:**
- `analyzer.py`: `analyze_ttest_candidates()` 독립 테스트 없음. FDR alpha 경계값 미검증
- `ml_factor_model.py`: TimeSeriesSplit 경계 조건(데이터 극소, 클래스 극단 불균형) 미검증

---

## 6. 리스크 항목

### 🔴 R1 — promoted 성공 사례 미확보 (높음)

파이럿 실행 결과:

```
balanced 프리셋 기준:
  성공률 0.50  (기준 0.60 ✗)
  OOS 지표 -0.02  (기준 0.00 ✗)
  평균 거래수 43  (기준 50 ✗)
  → 미채택 (all_rounds_no_trades)
```

**근본 원인**: 자동 생성된 조건식이 지나치게 강하게 작동하여 전체 거래를 차단.
`top_n`, `ml_feature_limit`, `ml_weight` 파라미터를 수동 탐색해야 함.
**후속 처리 자동화 없음** — candidate 강도 자동 완화 메커니즘이 필요하다.

### 🔴 R2 — `optimiz.py` / `rolling_walk_forward_test.py` 영향도 미확인 (높음)

체크리스트 3.2절에 명시된 필수 검증 항목:
B_*/S_*/R_* 컬럼 확장 후 이 파일들의 데이터 경로가 깨지지 않는지 검증 흔적 없음.

### 🟡 R3 — `analyzer.py` / `ml_factor_model.py` 테스트 부족 (중간)

각각 단위 테스트 4개, 2개로 구현 복잡도 대비 미흡.
`benjamini_hochberg()` 경계 조건, TimeSeriesSplit 분할 실패 케이스 미검증.

### 🟡 R4 — `fillna(0)` 노이즈 가능성 (낮음)

`ml_factor_model.py:72`의 `X.fillna(0)`:
`B_시가총액`처럼 0이 의미 있는 피처에서 결측값을 0으로 대체하면 ML 모델 학습에 노이즈 발생.

---

## 7. 개선 권장 사항 및 상세 구현 계획

### Improvement #1 — candidate 강도 자동 완화 fallback (최우선)

**우선순위**: 🔴 최고
**난이도**: 중간 (약 3~4시간)
**영향**: 파이럿 실행에서 all_rounds_no_trades 문제를 자동 해결, 실전 사용성 대폭 향상

#### 문제 상황

```
생성된 조건식 5개 → 모든 거래 차단 → WFO 거래 0건 → 미채택
    ↓
수동으로 top_n=3, top_n=2 등으로 재실행해야 채택 가능 여부를 알 수 있음
```

#### 구현 계획

**위치**: `cli/ai_controller.py` — `discover_and_promote_strategy()` 함수

**알고리즘**:

```python
def discover_and_promote_strategy(self, ..., top_n=5, auto_relax=True, max_relax_steps=3):
    """
    auto_relax=True 일 때:
      1. top_n 조건식으로 WFO 실행
      2. all_rounds_no_trades 발생 시 → top_n을 1 줄이고 재시도
      3. max_relax_steps 번까지 반복
      4. top_n=1까지 줄여도 거래 0건이면 완화 실패로 기록 후 종료
    """
```

**단계별 상세 구현**:

```python
# ai_controller.py 수정 위치: discover_and_promote_strategy() 내 WFO 실행 부분

def _run_with_auto_relax(self, base_config, top_n, max_relax_steps, **kwargs):
    """거래 0건 감지 시 top_n을 자동으로 줄이며 재시도."""
    current_top_n = top_n
    relax_history = []

    for step in range(max_relax_steps + 1):
        # 조건식 생성 (현재 top_n 적용)
        expr_result = self._generate_expressions(current_top_n, **kwargs)

        # 임시 전략 저장 및 WFO 실행
        wfo_result = self._run_wfo_with_strategy(expr_result, base_config, **kwargs)

        summary = (wfo_result.get('walk_forward') or {}).get('summary', {})
        zero_trade_rounds = summary.get('zero_trade_rounds', 0)
        total_rounds = summary.get('round_count', 1)

        relax_history.append({
            'step': step,
            'top_n': current_top_n,
            'zero_trade_rounds': zero_trade_rounds,
            'total_rounds': total_rounds,
        })

        # 거래가 발생하면 이 top_n으로 프로모션 평가 진행
        if zero_trade_rounds < total_rounds:
            return wfo_result, relax_history, current_top_n

        # 거래 0건 → top_n 완화
        if current_top_n <= 1:
            break  # 더 이상 완화 불가
        current_top_n = max(1, current_top_n - 1)

    # 완화 실패 — 최종 결과에 relax_history 포함
    wfo_result['auto_relax_failed'] = True
    wfo_result['relax_history'] = relax_history
    return wfo_result, relax_history, current_top_n
```

**결과 리포트 반영**:

```markdown
## Auto-Relax History
| 시도 | top_n | 거래 0회 라운드 | 총 라운드 |
|------|-------|----------------|-----------|
| 0    | 5     | 4              | 4         |
| 1    | 4     | 3              | 4         |
| 2    | 3     | 0              | 4         |  ← 이 설정으로 WFO 진행
```

**테스트 추가 위치**: `tests/unit/test_ai_controller.py`

```python
def test_auto_relax_reduces_top_n_on_zero_trades():
    """top_n=5 → 0거래 → top_n=3에서 거래 발생하면 top_n=3으로 진행"""

def test_auto_relax_fails_gracefully_when_top_n_1_still_zero():
    """top_n=1까지 줄여도 0거래면 auto_relax_failed=True 반환"""

def test_auto_relax_disabled_when_false():
    """auto_relax=False면 재시도 없이 첫 결과 반환"""
```

---

### Improvement #2 — `optimiz.py` / `rolling_walk_forward_test.py` 영향도 확인

**우선순위**: 🔴 높음
**난이도**: 낮음 (약 1시간, 코드 수정 없을 수도 있음)
**영향**: B_*/S_*/R_* 확장 후 기존 최적화/WFO 경로의 회귀 방지

#### 확인 방법

```bash
# 1. optimiz.py의 데이터 언패킹 경로 확인
python -c "
import ast, pathlib
src = pathlib.Path('backtest/optimiz.py').read_text(encoding='utf-8')
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, (ast.Assign, ast.Unpack)):
        print(ast.dump(node)[:200])
" | grep -i "extra\|column\|B_\|S_\|R_"

# 2. rolling_walk_forward_test.py 동일 확인
grep -n "CollectData\|GetResultDataframe\|extra_column\|B_\|columns1\|columns2" \
    backtest/rolling_walk_forward_test.py backtest/optimiz.py

# 3. 실제 실행으로 크래시 여부 확인
python stom_backtest.py run --strategy {전략명} --optimize 2>&1 | tail -20
```

#### 예상 결과 및 대응

| 결과 | 대응 |
|------|------|
| 에러 없음 | 체크리스트 항목 완료로 기록 |
| `ValueError: too many values to unpack` | `back_subtotal.py`의 `*extra_columns` 패턴을 `optimiz.py` 경로에도 적용 |
| 기타 에러 | 영향받는 코드 위치 분석 후 수정 |

#### 수정이 필요한 경우 패턴

```python
# 기존 (optimiz.py에 이런 패턴이 있다면)
보유시간, 매도시간, 수익률, 수익금, 수익금합계 = row

# 수정 후
보유시간, 매도시간, 수익률, 수익금, 수익금합계, *extra = row
```

---

### Improvement #3 — `analyzer.py` 단위 테스트 보강

**우선순위**: 🟡 중간
**난이도**: 낮음 (약 2시간)
**영향**: 분석 로직의 회귀 감지 능력 향상

#### 현재 테스트 갭

```
analyze_ttest_candidates() — 독립 테스트 없음
benjamini_hochberg() — 경계값 테스트 없음
analyze_market_cap_segments() — B_시가총액 컬럼 없는 경우 테스트 없음
analyze_time_segments() — B_시분초 컬럼 없는 경우 테스트 없음
```

#### 추가할 테스트 목록

```python
# tests/unit/test_analyzer.py 추가

class TestAnalyzeTtestCandidates:
    def test_returns_empty_when_scipy_unavailable(self, monkeypatch):
        """scipy 없을 때 빈 리스트 반환"""

    def test_fdr_filters_non_significant(self):
        """p-value > alpha 후보가 FDR 보정 후 제거되는지 확인"""

    def test_min_samples_threshold(self):
        """min_samples=30 미만 피처는 후보에서 제외"""

    def test_operator_direction(self):
        """low_mean < high_mean 이면 operator='<=' 반환"""


class TestBenjaminiHochberg:
    def test_all_significant(self):
        """모든 p-value가 매우 작으면 모두 accepted_fdr=True"""

    def test_none_significant(self):
        """모든 p-value가 크면 모두 accepted_fdr=False"""

    def test_empty_input(self):
        """빈 입력에서 빈 리스트 반환"""

    def test_single_value(self):
        """단일 p-value 처리"""


class TestAnalyzeMarketCapSegments:
    def test_missing_column_returns_error(self):
        """B_시가총액 컬럼 없을 때 status='error' 반환"""

    def test_min_samples_filters_small_groups(self):
        """소형주 샘플이 min_samples 미만이면 해당 그룹 제외"""


class TestAnalyzeTimeSegments:
    def test_missing_column_returns_error(self):
        """B_시분초 컬럼 없을 때 status='error' 반환"""


class TestAnalyzeResultFrame:
    def test_full_pipeline_integration(self):
        """전체 통합 분석 흐름: market_cap + time + quantile + ttest"""

    def test_empty_dataframe(self):
        """빈 DataFrame에서 크래시 없이 status='ok' 반환"""
```

---

### Improvement #4 — `ml_factor_model.py` 테스트 보강

**우선순위**: 🟡 중간
**난이도**: 낮음 (약 1시간)
**영향**: ML 분석 신뢰성 확보

#### 추가할 테스트 목록

```python
# tests/unit/test_ml_factor_model.py 추가

class TestAnalyzeResultsMl:
    def test_class_imbalance_balanced_weight(self):
        """수익/손실 비율이 극단적일 때 class_weight='balanced' 효과 확인"""

    def test_min_splits_adjustment(self):
        """데이터가 적을 때 n_splits가 max(2, len(df)//10)로 자동 조정되는지 확인"""

    def test_gradient_boosting_model(self):
        """model_type='gradient_boosting' 정상 동작 확인"""

    def test_no_numeric_b_features(self):
        """숫자형 B_* 컬럼이 없을 때 status='error' 반환"""

    def test_feature_importance_dict_keys_match_top_features(self):
        """feature_importance_dict의 키가 B_* 컬럼명과 일치"""

    def test_shap_fallback_when_unavailable(self, monkeypatch):
        """shap 미설치 시 shap_summary=None으로 정상 완료"""
```

---

### Improvement #5 — `ai_controller.py` 파라미터 객체화

**우선순위**: 🟡 중간
**난이도**: 중간 (약 2~3시간)
**영향**: 코드 가독성 및 유지보수성 개선

#### 현재 문제

`discover_and_promote_strategy()` 파라미터 29개:

```python
def discover_and_promote_strategy(
    self, name, input_path=None, top_n=5, strategy_type='buy',
    buy_var='매수', min_samples=30, quantiles=10, alpha=0.05,
    ml_analysis_result=None, ml_feature_limit=0, ml_model_type='random_forest',
    ml_top_n=10, ml_n_splits=5, ml_random_state=42, ml_weight=0.0,
    wfo_preset='balanced', wfo_train_days=120, wfo_test_days=40,
    wfo_step_days=None, purge_days=0, embargo_days=0,
    objective='tpi', method='grid', maximize=True, max_iter=10,
    output_path=None, on_progress=None, dry_run=False, skip_wfo=False
):
```

#### 개선 방안

```python
# cli/discovery_config.py (신규 파일)
from dataclasses import dataclass, field

@dataclass
class DiscoveryAnalysisConfig:
    """통계 분석 설정"""
    top_n: int = 5
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    buy_var: str = '매수'


@dataclass
class DiscoveryMlConfig:
    """ML 분석 설정"""
    enabled: bool = True
    model_type: str = 'random_forest'
    top_n: int = 10
    n_splits: int = 5
    random_state: int = 42
    weight: float = 0.0
    feature_limit: int = 0


@dataclass
class DiscoveryWfoConfig:
    """WFO 설정"""
    preset: str = 'balanced'
    train_days: int = 120
    test_days: int = 40
    step_days: int | None = None
    purge_days: int = 0
    embargo_days: int = 0
    objective: str = 'tpi'
    method: str = 'grid'
    maximize: bool = True
    max_iter: int = 10
    skip: bool = False


@dataclass
class DiscoveryConfig:
    """전체 탐색 설정"""
    analysis: DiscoveryAnalysisConfig = field(default_factory=DiscoveryAnalysisConfig)
    ml: DiscoveryMlConfig = field(default_factory=DiscoveryMlConfig)
    wfo: DiscoveryWfoConfig = field(default_factory=DiscoveryWfoConfig)
    output_path: str | None = None
    dry_run: bool = False
    auto_relax: bool = True
    max_relax_steps: int = 3
```

**수정 후 호출 예시**:

```python
config = DiscoveryConfig(
    analysis=DiscoveryAnalysisConfig(top_n=5, min_samples=30),
    ml=DiscoveryMlConfig(enabled=True, model_type='gradient_boosting'),
    wfo=DiscoveryWfoConfig(preset='balanced', train_days=120),
    auto_relax=True,
)
result = controller.discover_and_promote_strategy('my_strategy', config)
```

---

### Improvement #6 — `fillna(0)` 전략 개선

**우선순위**: 🟢 낮음
**난이도**: 낮음 (약 30분)
**영향**: ML 모델 학습 품질 미세 개선

#### 현재 코드

```python
# ml_factor_model.py:72
X = df[feature_columns].fillna(0)
```

#### 개선 방안

```python
# 피처별 중앙값으로 대체 (더 안전한 기본값)
X = df[feature_columns].copy()
for col in X.columns:
    median_val = X[col].median()
    X[col] = X[col].fillna(median_val)

# 또는 -1 sentinel 사용 (결측을 명시적 범주로 처리)
X = df[feature_columns].fillna(-1)
```

**선택 기준**:
- 시가총액처럼 연속형 피처 → 중앙값 대체 권장
- 결측 자체가 정보인 경우(예: VI 발동 시각이 없음 = VI 미발동) → -1 sentinel 권장

---

## 8. 종합 평가

### 등급: B+

### 잘된 점

1. **계획 대비 이행률 높음**: Phase 0/1 92%, Phase 2+ 95%
2. **계획 초과 달성**: ML 팩터 분석, 프리셋 시스템, CLI 서브커맨드 등 계획에 없던 핵심 기능 추가
3. **설계 원칙 일관 준수**: B_* 전용, library-only, 불변성, 예외 미전파 모두 코드 레벨에서 지켜짐
4. **테스트 코드 충실**: 구현 2,222줄 대비 테스트 2,037줄 (비율 0.92)
5. **파이럿 실행 버그 즉시 수정**: B_ 접두사, zero_trade_rounds, 프로세스 정리 모두 당일 수정

### 개선이 필요한 점

1. **🔴 promoted 성공 사례 미확보**: 자동 완화 메커니즘 없어 수동 파라미터 탐색 필요
2. **🔴 `optimiz.py`/`rolling_walk_forward_test.py` 미검증**: 체크리스트 필수 항목 누락
3. **🟡 analyzer/ml 테스트 부족**: 핵심 분석 로직의 경계 조건 미검증
4. **🟡 파라미터 과다**: 29개 파라미터를 config 객체로 정리 필요

### 다음 스프린트 권장 순서

```
Week 1:
  [필수] R2: optimiz.py / rolling_walk_forward_test.py 영향도 확인 (1일)
  [필수] I1: candidate 강도 자동 완화 fallback 구현 (1일)

Week 2:
  [권장] I3: analyzer.py 단위 테스트 보강 (1일)
  [권장] I4: ml_factor_model.py 테스트 보강 (반나절)

Week 3+ (여유 시):
  [선택] I5: DiscoveryConfig 객체화 리팩토링
  [선택] I6: fillna 전략 개선
```

---

*이 문서는 Architect 에이전트(Claude Opus)의 코드 심층 분석을 바탕으로 작성되었습니다.*
*참조 코드 베이스 시점: 2026-03-13, 커밋 `19dc3b7`*
