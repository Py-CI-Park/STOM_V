# STOM 자동 조건식 탐색 브랜치 — 실제 테스트 실행 보고서

- 작성일: 2026-03-15
- 대상 브랜치: `research/auto-condition-validation-pilot`
- 작성 목적: 현재 브랜치에서 개발된 자동 조건식 탐색(discovery) 기능에 대해 **실제 명령을 실행**하고, 그 결과와 해석을 명시적으로 남긴다.

---

## 1. 결론 요약

이번 테스트에서 아래를 실제로 확인했다.

1. **대표 단위 테스트 102개 통과**
2. CLI 기본 경로(`--version`, `--dry-run`) 정상 동작
3. `discovery analyze` / `ml-analyze` / `generate` 정상 동작
4. **실제 `discovery promote`까지 실행 성공**
5. `promoted=true` 결과와 report JSON/Markdown 저장까지 확인

다만 promote 결과 해석은 주의가 필요하다.

- 이번 promote 성공은 **aggressive + relaxed 기준**에서 통과한 것이다.
- 생성된 전략은 실제로 DB에 저장되었고 WFO 기준을 만족했지만,
- raw 수익률/수익금 지표 자체는 음수였으므로,
- 이를 곧바로 “실전 수익 전략 검증 완료”로 해석하면 안 된다.

즉,

> **기능 파이프라인은 실제로 끝까지 동작함을 확인했다.**
> **그러나 전략 품질 평가는 별도로 더 엄격하게 해석해야 한다.**

---

## 2. 테스트 환경

- Shell: `bash`
- Date: `2026-03-15`
- Project root: `/mnt/c/System_Trading/STOM/STOM_V`
- Python: 시스템 기본 `python3`
- DB 사용: `_database/strategy.db`, `_database/stock_min_20250407.db` 등 로컬 DB 사용

주의:
- 설정 DB 복호화 관련 경고(`암호화 필드 복호화에 실패하여 최소 설정 모드`)는 출력되었으나,
  테스트 자체는 계속 진행되었다.
- analyze/generate 단계에서 SciPy warning(precision loss)가 출력되었으나,
  실행 실패는 아니었다.

---

## 3. 실제 실행한 명령, 이유, 결과

## 3.1 대표 단위 테스트 실행

### 실행 이유
기능별 핵심 경로(analyzer / ML / CLI / report / strategy generator)가 깨지지 않았는지 빠르게 확인하기 위함이다.

### 실행 명령
```bash
pytest -q -p no:xdist tests/unit/test_analyzer.py
pytest -q -p no:xdist tests/unit/test_ml_factor_model.py
pytest -q -p no:xdist tests/unit/test_subcommands.py tests/unit/test_discovery_report.py tests/unit/test_strategy_generator.py
```

### 결과
- `tests/unit/test_analyzer.py` → **20 passed**
- `tests/unit/test_ml_factor_model.py` → **11 passed**
- `tests/unit/test_subcommands.py + test_discovery_report.py + test_strategy_generator.py` → **71 passed**

### 합계
- **102 passed**

### 해석
현재 브랜치의 핵심 library / CLI / report / code generation 경로는 단위 테스트 수준에서 정상이다.

---

## 3.2 CLI 버전 확인

### 실행 이유
CLI 엔트리 포인트가 정상 실행되는지 가장 먼저 확인하기 위함이다.

### 실행 명령
```bash
python3 stom_backtest.py --version
```

### 결과
```text
STOM CLI Backtest Runner V2.51.U2.0
```

### 해석
CLI 진입점은 정상이다.

---

## 3.3 dry-run 실행

### 실행 이유
실제 백테스트를 돌리지 않고도 전략명 / 기간 / 설정 파싱 경로가 정상인지 확인하기 위함이다.

### 실행 명령
```bash
python3 stom_backtest.py \
  --buy Min_B_Study_251227 \
  --sell Min_S_Study_251227 \
  --start 20250101 \
  --end 20250131 \
  --dry-run
```

### 결과
```json
{"status": "dry-run", "buy_strategy": "Min_B_Study_251227", "sell_strategy": "Min_S_Study_251227", "start_date": 20250101, "end_date": 20250131, "engine_count": 4, "is_tick": true, "dry_run": true}
```

### 해석
CLI 파서와 기본 BacktestConfig 구성은 정상이다.

---

## 3.4 테스트용 샘플 CSV 생성

### 실행 이유
현재 저장소에는 이번 세션 기준 `backtest/csv/*.csv`를 ignore하도록 정리되어 있어,
재현 가능한 discovery 테스트 입력을 새로 생성할 필요가 있었다.

### 실행 명령
```bash
python3 - <<'PY'
from pathlib import Path
import pandas as pd
rows = []
for i in range(80):
    rows.append({
        '매수시간': 20240101090000 + i,
        '수익률': 1.2 if i >= 40 else -1.0,
        'B_등락율': 3.0 + i * 0.1 if i >= 40 else 0.5 + i * 0.02,
        'B_체결강도': 120 + i if i >= 40 else 80 + i,
        'B_시가총액': 2_000_000_000_000 if i >= 40 else 100_000_000_000,
        'B_시분초': 140000 if i >= 40 else 91000,
        'B_분봉시가': 5000 + i * 10,
        'B_분봉고가': 5050 + i * 10,
        'B_분봉저가': 4950 + i * 10,
        'B_당일거래대금': 1_000_000_000 + i * 10_000_000,
        'B_거래대금증감': 100_000_000 + i * 1_000_000,
        'B_회전율': 5 + i * 0.1,
        'B_전일동시간비': 100 + i,
        'B_매수총잔량': 10000 + i * 100,
        'B_매도총잔량': 12000 + i * 120,
    })
path = Path('temp/sample_discovery_result.csv')
path.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8-sig')
print(path)
PY
```

### 결과 파일
- `temp/sample_discovery_result.csv`

### 해석
이 파일은 analyze / ml-analyze / generate / promote를 재현하는 테스트 입력으로 사용했다.

---

## 3.5 `discovery analyze` 실행

### 실행 이유
통계 기반 후보 탐색이 실제 CSV 입력에 대해 제대로 동작하는지 확인하기 위함이다.

### 실행 명령
```bash
python3 stom_backtest.py discovery analyze \
  --input temp/sample_discovery_result.csv \
  --min-samples 10 \
  --quantiles 4
```

### 핵심 결과
- `status = ok`
- `row_count = 80`
- `feature_columns = 13개`
- `market_cap_candidates` 생성
- `time_candidates` 생성
- `quantile_candidates` / `ttest_candidates` 생성

### 대표 결과 예
- `B_시가총액` → `소형주` 구간이 불리한 후보로 탐지
- `B_시분초` → `장초반` 구간이 불리한 후보로 탐지
- 여러 `B_*` 피처에서 `ttest` 후보가 `accepted_fdr=true`로 추출됨

### 해석
분석기는 실제 입력 DataFrame에 대해 정상 작동했다.
특히 구간 기반 후보와 통계 검정 기반 후보가 동시에 생성되는 것을 확인했다.

---

## 3.6 `discovery ml-analyze` 실행

### 실행 이유
ML 기반 feature importance 분석이 실제 입력에서 정상 작동하는지 확인하기 위함이다.

### 실행 명령
```bash
python3 stom_backtest.py discovery ml-analyze \
  --input temp/sample_discovery_result.csv \
  --top-n 5 \
  --n-splits 3
```

### 결과 요약
- `status = ok`
- `model_type = random_forest`
- `row_count = 80`
- `feature_count = 13`
- `positive_ratio = 0.5`
- `mean_cv_score = 0.6666666666666666`

### top feature
1. `B_분봉저가`
2. `B_매도총잔량`
3. `B_분봉시가`
4. `B_분봉고가`
5. `B_시가총액`

### 해석
ML 분석기는 정상 동작했고, 중요 피처 목록과 CV score를 실제로 반환했다.
다만 이번 샘플 CSV는 인위적으로 분리도가 큰 데이터라 CV score 변동성이 크다.

---

## 3.7 `discovery generate` 실행

### 실행 이유
analyze 결과를 실제 전략 필터 코드로 변환할 수 있는지 확인하기 위함이다.

### 실행 명령
```bash
python3 stom_backtest.py discovery generate \
  --input temp/sample_discovery_result.csv \
  --top-n 2 \
  --min-samples 10 \
  --quantiles 4
```

### 결과 요약
- `status = ok`
- `candidate_count = 2`

### 실제 생성 코드
```python
if 등락율 <= 4.14: 매수 = False
if 체결강도 <= 139.5: 매수 = False
```

### 해석
통계 후보를 실제 전략 필터 코드로 렌더링하는 경로가 정상 동작했다.
즉, analyze → generate 파이프라인이 실제로 연결되었다.

---

## 3.8 `discovery promote` 실제 실행

### 실행 이유
현재 브랜치의 핵심 가치는 “분석 → 필터 생성 → 기존 전략 결합 → WFO 평가 → promote” 전체 경로에 있으므로,
가능한 범위에서 실제 DB와 전략을 사용해 end-to-end 실행을 확인하기 위함이다.

### 실행 명령
```bash
python3 stom_backtest.py discovery promote Auto_B_TestRun_20260315 \
  --input temp/sample_discovery_result.csv \
  --sell Min_S_Study_251227 \
  --start 20250407 \
  --end 20250411 \
  --timeframe min \
  --train-window-days 3 \
  --test-window-days 2 \
  --step-days 3 \
  --engines 1 \
  --top-n 1 \
  --base-buy-strategy Min_B_Study_251227 \
  --promotion-preset aggressive \
  --auto-relax \
  --report-json temp/promote_test_report.json \
  --report-md temp/promote_test_report.md
```

### 실행 시 사용한 실제 자원
- buy base strategy: `Min_B_Study_251227`
- sell strategy: `Min_S_Study_251227`
- 실제 minute DB: `_database/stock_min_20250407.db` ~ `_database/stock_min_20250411.db`
- 실제 strategy DB: `_database/strategy.db`

### 핵심 결과
- `status = ok`
- `promoted = true`
- `criteria_mode = relaxed`
- `promotion_preset = aggressive`
- `saved_report_json = temp/promote_test_report.json`
- `saved_report_md = temp/promote_test_report.md`

### WFO 요약
- `round_count = 1`
- `success_rate = 1.0`
- `mean_oos_metric = 0.46`
- `mean_trade_count = 72.0`
- `zero_trade_rounds = 0`

### promote evaluation
- `passed = true`
- `min_rounds = 1`
- `min_success_rate = 0.5`
- `min_mean_oos_metric = -0.1`
- `min_avg_trade_count = 0.0`
- `criteria_mode = relaxed`

### 생성/저장된 전략
- 전략명: `Auto_B_TestRun_20260315`
- 자동 필터: `if 등락율 <= 4.14: 매수 = False`
- 기존 `Min_B_Study_251227` 전략 코드에 자동 필터가 결합된 상태로 저장됨

### 중요한 해석
이 테스트는 **파이프라인 검증 관점에서는 성공**이다.

즉 확인된 것:
- CSV 분석 → expression 생성 → 기존 전략 결합 → WFO 실행 → promote 평가 → report 저장
- 이 전체 흐름이 실제로 끝까지 동작함

그러나 성능 해석은 별개다.

#### raw train/test 결과 중 확인된 수치
- train optimization best score: `tpi = 0.45`
- test result metric: `tpi = 0.46`
- test result trade_count: `72`
- test result total_profit_pct: `-7.28%`
- test result total_profit_krw: `-1,232,300원`

즉,
- 현재 aggressive relaxed 기준에서는 promote에 통과했지만,
- raw 수익률/수익금은 음수였다.

따라서 이번 테스트의 결론은:

> **“현재 코드가 실제로 promote까지 수행 가능하다”는 것은 입증되었다.**
> **하지만 “이번 입력/기준에서 생성된 전략이 실전적으로 우수하다”는 뜻은 아니다.**

이 차이를 분명히 구분해야 한다.

---

## 4. 테스트 산출물

이번 테스트로 생성/저장된 대표 산출물:

- 샘플 CSV
  - `temp/sample_discovery_result.csv`
- promote 결과 JSON
  - `temp/promote_test_report.json`
- promote 결과 Markdown
  - `temp/promote_test_report.md`
- 생성/저장 전략
  - `Auto_B_TestRun_20260315` (strategy.db)

---

## 5. 종합 평가

## 5.1 확인된 것

- analyzer 정상
- ml_factor_model 정상
- code generation 정상
- CLI 정상
- 기존 매수 전략 결합 경로 정상
- report 저장 정상
- 실제 promote 경로 정상

## 5.2 아직 남은 과제

- strict balanced 기준에서 실제 통과 가능한지 검증
- promote 기준 자체가 raw 수익성과 얼마나 정렬되는지 재검토
- synthetic CSV가 아니라 실제 backtest result CSV로 같은 흐름을 다시 검증
- 장시간 반복 실행/운영형 QA 보강

---

## 6. 최종 결론

이번 실제 실행 테스트 기준으로 다음 결론을 내릴 수 있다.

1. **현재 브랜치의 핵심 기능은 실제로 동작한다.**
2. **분석 → 생성 → 결합 → WFO → promote → report 저장** 흐름이 실제로 연결된다.
3. **기능 검증은 성공**이다.
4. 다만 **전략 성능 검증은 별도 문제**이며, 이번 promote 통과를 곧바로 실전 수익 전략으로 해석하면 안 된다.

한 줄 요약:

> **현재 브랜치는 “자동 조건식 탐색 기능이 실제로 돌아간다”는 점은 입증했지만, “항상 좋은 전략을 만든다”는 점까지 입증한 것은 아니다.**
