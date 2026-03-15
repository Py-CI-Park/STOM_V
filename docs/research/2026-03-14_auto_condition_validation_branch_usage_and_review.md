# STOM 자동 조건식 탐색 브랜치 사용 가이드 및 상태 평가

- 작성일: 2026-03-14
- 대상 브랜치: `research/auto-condition-validation-pilot`
- 목적: 현재 브랜치에서 개발한 자동 조건식 탐색(discovery) 기능의 실제 사용 방법, 검증 상태, Windows 적합성, merge 가능성, 향후 보완점을 한 문서로 정리한다.

---

## 1. 문서 요약

이 브랜치에서는 다음 흐름을 연구·구현·검증했다.

1. 백테스트 상세 CSV를 분석한다.
2. `B_*` 팩터 기준으로 자동 필터 후보를 찾는다.
3. 필요 시 ML 기반 중요도 분석으로 후보 우선순위를 보조한다.
4. 자동 필터를 단독 코드로 생성하거나, 기존 매수 전략에 결합한다.
5. Walk-Forward(WFO) 검증을 통과한 경우에만 전략을 `promote`한다.
6. 결과를 JSON / Markdown report로 남긴다.

현재 상태를 한 줄로 요약하면 다음과 같다.

> **분석/생성/CLI/리포트/테스트 체계는 충분히 usable한 상태이며, research 브랜치로는 merge 가능성이 높다. 다만 strict balanced 달성, Windows 실사용 QA, 장시간 WFO 재현 검증은 아직 후속 과제다.**

---

## 2. 이 브랜치에서 실제로 개발된 핵심 내용

### 2.1 Discovery promotion 평가 체계 보강

- `criteria_mode` 필드 추가
  - `strict` / `relaxed` 구분을 결과에 명시
  - report JSON/Markdown에서도 확인 가능
- `auto_relax` 기능 추가
  - 무거래(no-trade) 상황일 때 `top_n`을 완화하며 재시도 가능
- `max_relax_steps` 추가
  - 자동 완화 최대 단계 수 제어
- `base_buy_strategy` 추가
  - 자동 필터를 기존 매수 전략에 결합한 뒤 promote 검증 가능

### 2.2 CLI 사용성 개선

`discovery promote`에서 다음 옵션을 공식적으로 사용할 수 있다.

- `--auto-relax`
- `--max-relax-steps`
- `--base-buy-strategy`
- `--promotion-preset`
- `--report-json`
- `--report-md`

### 2.3 설정 구조 정리

- `DiscoveryConfig` dataclass 도입
- 분석 / ML / promotion / output 설정을 구조화
- `discover_and_promote_strategy()` 호출부 정리

### 2.4 분석 및 ML 안정화

- `cli/analyzer.py`
  - `benjamini_hochberg()` NaN 인덱싱 버그 수정
  - 경계 조건 테스트 추가
- `cli/ml_factor_model.py`
  - 결측값 대체를 `fillna(0)`에서 **피처별 중앙값(median)** 대체로 변경
  - 경계 조건 테스트 추가

### 2.5 문서화

- strict / relaxed / exploratory baseline 정의
- strict aggressive / strict balanced 해석 기준 정리
- 현재 성과와 한계 명문화

---

## 3. 현재까지 확인된 실제 성과

### 3.1 문서 및 산출물 기준 성과

브랜치 내 문서 기준으로 `promoted=True` 성공 사례가 확보되어 있다.

관련 문서:
- `docs/research/2026-03-13_auto_condition_discovery_generalization_verification.md`
- `docs/research/2026-03-14_discovery_strict_revalidation_and_baseline_standard.md`

기록된 대표 사례:

| 사례 | 결과 | mean_oos_metric | avg_trade_count | 비고 |
|------|------|-----------------|-----------------|------|
| A | promoted=True | 0.55 | 80.0 | aggressive / single-round |
| B | promoted=True | 0.60 | 70.0 | aggressive / top_n=2 |
| C | promoted=True | 0.35 | 38.0 | balanced / multi-round |

추가로 로컬 산출물도 남아 있다.

예:
- `backtest/csv/stock_bt___AUTO_TMP__Auto_B_Generalize_...csv`
- `backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv`

### 3.2 이번 검토에서 직접 확인한 실행 결과

이번 검토 시 실제로 아래 명령을 직접 실행해 동작을 확인했다.

#### (1) 버전 확인
```bash
python3 stom_backtest.py --version
```
결과:
- `STOM CLI Backtest Runner V2.51.U2.0`

#### (2) dry-run 확인
```bash
python3 stom_backtest.py \
  --buy Min_B_Study_251227 \
  --sell Min_S_Study_251227 \
  --start 20250101 --end 20250131 \
  --dry-run
```
결과:
- 설정 JSON 정상 출력
- `status = dry-run`

#### (3) discovery analyze 실행
```bash
python3 stom_backtest.py discovery analyze \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --min-samples 30 --quantiles 4
```
결과 요약:
- `status = ok`
- `row_count = 1542`
- `feature_columns = 14개`
- 시간대/분위수 후보 정상 생성

#### (4) discovery ml-analyze 실행
```bash
python3 stom_backtest.py discovery ml-analyze \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --top-n 5 --n-splits 3
```
결과 요약:
- `status = ok`
- `feature_count = 14`
- `mean_cv_score ≈ 0.7411`
- top feature 산출 정상

#### (5) discovery generate 실행
```bash
python3 stom_backtest.py discovery generate \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --top-n 2 --min-samples 30 --quantiles 4
```
결과 요약:
- `status = ok`
- `candidate_count = 2`
- 자동 필터 코드 생성 성공

예시 생성 코드:
```python
if 3778.75 <= 분봉시가 < 8_550: 매수 = False
if 3772.5 <= 분봉저가 < 8_550: 매수 = False
```

### 3.3 이번 검토에서 확인한 테스트 상태

직접 실행하여 통과를 확인한 대표 테스트는 다음과 같다.

- `tests/unit/test_analyzer.py`
- `tests/unit/test_ml_factor_model.py`
- `tests/unit/test_discovery_report.py`
- `tests/unit/test_subcommands.py`
- `tests/unit/test_strategy_generator.py`
- `tests/unit/test_ai_controller.py` 핵심 일부(`criteria_mode`, `auto_relax`)

해석:
- 분석/ML/CLI/report/전략 생성 핵심 경로는 테스트 근거가 있다.
- 다만 full promote 장시간 실행을 매번 테스트로 재현하는 구조는 아직 아니다.

### 3.4 성과 해석

정리하면 다음과 같다.

- **기능은 실제로 작동한다.**
- **promotion 성공 사례도 존재한다.**
- 다만 현재 성과는 **research baseline 기준 성과**로 보는 것이 정확하다.
- 즉, “기능 검증과 baseline 확보”는 성공했지만, “실전형 장기 검증 완료”까지는 아직 아니다.

---

## 4. 이 브랜치 기능을 어떻게 사용하는가

### 4.1 사전 준비

### Windows 권장
이 프로젝트는 사실상 **Windows 중심**이다.

근거:
- `stom.bat`, `stom_backtest.bat` 제공
- UAC(admin) 처리 포함
- `PyQt5`, `pywin32`, `win32gui`, `win32api` 사용
- Windows용 TA-Lib wheel 포함

권장 준비:
- Python 3.11 계열 확인
- Windows CMD 또는 PowerShell 사용
- 필요 시 `pip_install_64.bat` 실행

### 주요 실행 파일
- GUI 실행: `stom.bat`
- CLI 백테스트/분석 실행: `stom_backtest.bat`
- 직접 Python 실행: `python stom_backtest.py ...`

---

### 4.2 가장 먼저 해볼 명령

### 버전 확인
```bash
python stom_backtest.py --version
```
또는
```bat
stom_backtest.bat --version
```

### CLI 하위 명령 확인
```bash
python stom_backtest.py discovery -h
python stom_backtest.py discovery promote -h
```

---

### 4.3 기본 사용 흐름

### Step 1. 결과 CSV 분석
백테스트 상세 결과에서 자동 필터 후보를 찾는다.

```bash
python stom_backtest.py discovery analyze \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --min-samples 30 \
  --quantiles 4
```

언제 쓰는가:
- 어떤 `B_*` 구간이 성능을 깎는지 파악할 때
- 후보 필터를 먼저 확인하고 싶을 때

---

### Step 2. ML 기반 중요도 분석
ML 기준으로 어떤 `B_*` feature가 중요한지 확인한다.

```bash
python stom_backtest.py discovery ml-analyze \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --top-n 5 \
  --n-splits 3
```

언제 쓰는가:
- feature importance를 보고 싶을 때
- discovery candidate ranking에 참고할 때

---

### Step 3. 자동 필터 코드 생성
분석 결과를 바탕으로 실제 조건 코드를 만든다.

```bash
python stom_backtest.py discovery generate \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --top-n 2 \
  --min-samples 30 \
  --quantiles 4 \
  --output generated_filter.py
```

언제 쓰는가:
- promote 전에 후보 코드만 미리 보고 싶을 때
- 사람이 직접 검토하고 싶을 때

---

### Step 4. 자동 필터를 기존 매수 전략에 결합해 promote
이 브랜치에서 가장 중요한 사용 방식이다.

#### (A) 연구용 / relaxed promote
```bash
python stom_backtest.py discovery promote Auto_B_RelaxedAgg \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --sell Min_S_Study_251227 \
  --start 20250407 --end 20250411 \
  --train-window-days 3 --test-window-days 2 --step-days 3 \
  --engines 1 \
  --top-n 1 \
  --base-buy-strategy Min_B_Study_251227 \
  --promotion-preset aggressive \
  --auto-relax \
  --report-json report_relaxed.json \
  --report-md report_relaxed.md
```

용도:
- baseline 탐색
- no-trade 상황에서 자동 완화 재시도
- 연구/실험용

#### (B) strict aggressive promote
```bash
python stom_backtest.py discovery promote Auto_B_StrictAgg \
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260311210622.csv \
  --sell Min_S_Study_251227 \
  --start 20250407 --end 20250411 \
  --train-window-days 3 --test-window-days 2 --step-days 3 \
  --engines 1 \
  --top-n 1 \
  --base-buy-strategy Min_B_Study_251227 \
  --promotion-preset aggressive \
  --promote-min-rounds 1 \
  --promote-min-success-rate 0.5 \
  --promote-min-mean-oos -0.1 \
  --promote-min-avg-trade-count 20.0 \
  --report-json report_strict_aggressive.json \
  --report-md report_strict_aggressive.md
```

용도:
- 완화 기준 없이 strict aggressive 기준으로 평가
- 현재 문서상 가장 현실적인 strict baseline

---

### 4.4 strict 사용 시 매우 중요한 주의점

CLI에서 **정확한 strict preset**을 재현하려면 `--promote-min-*` 값을 **모두 preset 원형에 맞게 명시하는 것이 안전**하다.

예를 들어 balanced strict를 정말 그대로 재현하려면 아래처럼 4개를 전부 명시하는 것을 권장한다.

```bash
python stom_backtest.py discovery promote Auto_B_StrictBalanced \
  --input result.csv \
  --sell Min_S_Study_251227 \
  --start 20250407 --end 20250411 \
  --train-window-days 2 --test-window-days 1 --step-days 2 \
  --base-buy-strategy Min_B_Study_251227 \
  --promotion-preset balanced \
  --promote-min-rounds 2 \
  --promote-min-success-rate 0.6 \
  --promote-min-mean-oos 0.0 \
  --promote-min-avg-trade-count 50.0
```

이유:
- CLI 기본값이 preset 원형과 완전히 같지 않을 수 있다.
- 따라서 “preset 이름만 balanced”인데 실제 criteria는 strict balanced 원형과 다를 수 있다.

---

### 4.5 report 결과는 어디에 남는가

`discovery promote`에서는 아래 결과를 남길 수 있다.

- `--report-json report.json`
- `--report-md report.md`

report에서 확인할 항목:
- `promoted`
- `promotion_preset`
- `criteria_mode`
- `promotion_evaluation`
- `walk_forward_summary`
- `auto_relax_history`
- 선택된 expression / feature 정보

---

## 5. Windows 환경을 고려했을 때의 평가

### 5.1 장점

이 프로젝트는 Windows를 실제 사용 환경으로 강하게 상정하고 있다.

확인된 근거:
- `.bat` 실행 파일 다수 존재
- 관리자 권한(UAC) 처리 존재
- `PyQt5` GUI 기반
- `ctypes.windll.kernel32` 사용
- `pywin32`, `win32gui`, `win32api` 사용
- Windows용 wheel 파일 포함

따라서 아래 평가는 가능하다.

> **이 프로젝트는 Windows를 “고려한” 수준이 아니라, 거의 Windows-first 설계에 가깝다.**

### 5.2 현재 기준 한계

다만 이번 검토에서 직접 확인한 것은 주로 다음이다.

- CLI 동작
- 분석/ML/생성 기능
- 테스트 통과 여부

즉, 다음까지 완전하게 실기 검증한 것은 아니다.

- 네이티브 Windows GUI 전체 동작
- 실제 증권사/차트 프로그램 연동 시나리오
- 장시간 운영 세션 안정성

따라서 Windows 관점 평가는 다음처럼 정리하는 것이 정확하다.

> **개발 방향과 구조는 Windows 친화적이며 타당하다. 다만 최종 실사용 QA(특히 GUI + 외부 프로그램 연동)는 별도 검증이 더 필요하다.**

---

## 6. 브랜치 평가

### 6.1 좋은 점

1. **기능 추가 → 테스트 → 문서화 흐름이 좋다.**
2. 단순 실험 코드가 아니라 **CLI 인터페이스까지 정리**되어 있다.
3. `criteria_mode` 추가로 결과 해석이 명확해졌다.
4. `DiscoveryConfig` 도입으로 구조가 정리되었다.
5. `fillna(0)` → median 변경은 실제 모델 품질 관점에서 의미가 있다.
6. `base_buy_strategy + auto filter` 방식이 실제 성과를 낸 baseline으로 정리되었다.

### 6.2 아쉬운 점

1. strict CLI 예시는 아직 문서상 더 엄밀해질 필요가 있다.
2. strict balanced는 아직 달성되지 않았다.
3. full WFO promote를 이번 리뷰에서 다시 장시간 재실행한 것은 아니다.
4. Windows GUI 전체 흐름의 실사용 QA 기록은 더 필요하다.
5. 일부 테스트는 기능 성공 여부 중심이며, 내부 값 검증을 더 촘촘히 할 여지가 있다.

### 6.3 종합 평가

- **연구 브랜치로서의 완성도: 높음**
- **실제 사용 가능성: 있음**
- **바로 프로덕션 확정 수준인가?: 아직 아님**

즉,

> **research / integration 단계로는 충분히 좋은 상태이며, production 최종 확정 전 단계로 보는 것이 적절하다.**

---

## 7. merge 가능성 평가

### 7.1 merge에 긍정적인 이유

다음 이유로 research 계열 브랜치에는 merge 가능성이 높다.

- 기능이 실제 실행된다.
- 관련 테스트가 보강되었다.
- 문서가 함께 정리되었다.
- 기존 성공 사례와 baseline이 정리되었다.
- CLI 사용 흐름이 분명하다.

### 7.2 조건부 판단

다만 merge 대상을 구분하는 것이 좋다.

### (A) research / integration 브랜치로 merge
**권장 가능**

이유:
- 기능 검증과 문서화가 이미 충분히 진행됨
- 후속 실험을 같은 축 위에서 이어가기 좋음

### (B) main / production 성격 브랜치로 merge
**조건부 권장**

아래가 추가되면 더 안전하다.
- strict balanced 달성 또는 명확한 미달 결론 확정
- Windows GUI 실사용 QA
- 장시간 WFO / promote 재현 검증
- strict CLI 예시/문서 정밀화

### 7.3 최종 merge 판단

> **현재 상태라면 research 또는 dev 통합 브랜치에는 merge 가능성이 높다. 다만 production 최종 merge는 “조건부 승인”이 더 적절하다.**

---

## 8. 앞으로 더 보완할 점

### 8.1 1순위: strict balanced 재검증

현재 가장 중요한 남은 과제다.

필요한 작업:
- 검증 구간 확대
- WFO window 조정
- round당 거래 수 확보
- strict balanced 기준(`avg_trade_count >= 50`) 충족 여부 재확인

### 8.2 2순위: strict CLI 문서 정밀화

권장 작업:
- preset별 strict 예시를 3종(conservative / balanced / aggressive) 명시
- `--promote-min-*` 4개를 전부 적는 예제 제공
- “preset 이름”과 “실제 적용 criteria”가 다를 수 있다는 주의 문구 강화

### 8.3 3순위: Windows 실사용 QA

권장 작업:
- `stom.bat`, `stom_backtest.bat` 기준 실제 실행 점검
- GUI에서 전략 생성/반영/조회 흐름 점검
- 외부 프로그램/차트 연동 여부 점검
- 관리자 권한/UAC 경로 이슈 정리

### 8.4 4순위: promote 회귀 테스트 확대

권장 작업:
- 실제 promote 결과 구조를 fixture로 고정
- report JSON/Markdown snapshot 테스트 추가
- `base_buy_strategy` 결합 경로 단위 테스트 강화

### 8.5 5순위: 운영성 개선

권장 작업:
- `.bat`에서 Python 경로/venv 감지 개선
- 장시간 실행 시 로그 저장 표준화
- report 저장 경로 규칙 정리
- 산출물(`backtest/csv`) 정리 규칙 문서화

---

## 9. 최종 결론

이 브랜치에서 개발한 내용은 다음처럼 평가할 수 있다.

1. **실제로 사용 가능하다.**
   - 분석, ML 분석, 필터 생성, promote CLI 흐름이 존재한다.
2. **실제 테스트와 연구 성과가 있다.**
   - promoted 성공 사례가 문서와 산출물로 남아 있다.
3. **Windows를 고려해 잘 개발되었다.**
   - 구조상 Windows-first 성향이 강하다.
4. **바로 production 최종판은 아니다.**
   - strict balanced, Windows 실사용 QA, 장시간 재현 검증이 남아 있다.
5. **merge는 가능하지만, 대상 브랜치에 따라 판단을 나누는 것이 좋다.**
   - research/dev 통합: 긍정적
   - production/main: 조건부

최종 한 줄 평:

> **이 브랜치는 “자동 조건식 탐색을 실제로 써볼 수 있는 수준까지 끌어올린 연구 브랜치”이며, 현재 기준으로는 문서·테스트·기능이 잘 연결된 편이다. 다음 핵심 과제는 strict balanced 달성과 Windows 실사용 QA다.**
