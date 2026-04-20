# Tick Research Baseline Condition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the external strategy-analysis report, create clearly documented wide tick research buy/sell strategies, save them to `strategy.db` under research/test/tick/wide names, and run a direct backtest to produce a broad baseline CSV for later automated condition improvement.

**Architecture:** This is a documentation-plus-runtime-strategy task. Repository-tracked outputs are docs under `docs/research/condition_research/`; runtime state is `strategy.db` and generated backtest CSV, which remain local ignored artifacts. Use existing `cli.strategy.validate_strategy()` and `cli.strategy_generator.save_strategy_to_db()` instead of changing core backtest or strategy execution code.

**Tech Stack:** Python 3.11, STOM strategy DSL, SQLite `strategy.db`, existing `cli.strategy`, `cli.strategy_generator`, `stom_backtest.py`, pytest.

---

## Full Flow

```text
[0. 외부 우수 전략 보고서]
   E:\Download\backtest_analysis_report_v2.md
        |
        v
[1. docs에 원문/요약 보존]              <- Task 1
        |
        v
[2. 넓은 tick 연구용 baseline 조건식]   <- Task 2
        |
        v
[3. strategy.db 저장/검증]              <- Task 3
        |
        v
[4. 직접 백테스트]                      <- Task 4
        |
        v
[5. 기준 CSV 확보]
        |
        v
[6. Retention-Aware 후보 선별]
        |
        v
[7. 후보 N개 백테스트/랭킹]
```

## Scope Check

In scope:

- Copy `E:\Download\backtest_analysis_report_v2.md` into repository docs.
- Create a concise summary of the report for condition research.
- Create wide tick buy/sell strategy documentation.
- Validate strategy code through `cli.strategy.validate_strategy()`.
- Save strategies into local `strategy.db`.
- Run a direct tick backtest using the new wide strategies.
- Record result in docs/update log and pilot log.

Out of scope:

- WFO validation.
- Multi-round improvement loop.
- Editing core `backtest/`, `runner`, GUI, or strategy engine code.
- Overwriting `Tick_B_902_905_Update_2` / `Tick_S_902_905_Update_2`.
- Claiming the wide strategy is live-ready.

## File Structure

- Create `docs/research/condition_research/README.md`
- Create `docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md`
- Create `docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md`
- Create `docs/research/condition_research/strategy_designs/2026-04-19_tick_research_baseline_condition_design.md`
- Create `docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md`
- Create `docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_backtest.md`
- Create `docs/update_log/2026-04-19_tick_research_baseline_condition.md`
- Do not commit `_database/strategy.db` or generated `backtest/csv` files.

---

### Task 1: Documentation Tree And Source Report Preservation

**Files:**
- Create: `docs/research/condition_research/README.md`
- Create: `docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md`
- Create: `docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md`

- [ ] **Step 1: Verify source report exists**

Run:

```powershell
Test-Path E:\Download\backtest_analysis_report_v2.md
Get-Item E:\Download\backtest_analysis_report_v2.md | Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
True
FullName: E:\Download\backtest_analysis_report_v2.md
Length: about 30206
```

- [ ] **Step 2: Create documentation directories and copy source report**

Run:

```powershell
New-Item -ItemType Directory -Force -Path docs/research/condition_research/source_reports | Out-Null
New-Item -ItemType Directory -Force -Path docs/research/condition_research/summaries | Out-Null
New-Item -ItemType Directory -Force -Path docs/research/condition_research/strategy_designs | Out-Null
New-Item -ItemType Directory -Force -Path docs/research/condition_research/generated_conditions | Out-Null
New-Item -ItemType Directory -Force -Path docs/research/condition_research/pilot_logs | Out-Null
Copy-Item -LiteralPath E:\Download\backtest_analysis_report_v2.md -Destination docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md -Force
```

- [ ] **Step 3: Create `README.md`**

Create `docs/research/condition_research/README.md`:

```markdown
# Condition Research

## 목적

이 폴더는 STOM 조건식 연구를 위한 문서와 산출물을 보존한다.

전체 플로우:

```text
[외부 우수 전략 보고서]
        |
        v
[요약/설계]
        |
        v
[연구용 wide 조건식]
        |
        v
[strategy.db 저장]
        |
        v
[직접 백테스트]
        |
        v
[Retention-Aware 후보 개선 루프]
```

## 하위 폴더

- `source_reports/`: 외부 원본 보고서 보존
- `summaries/`: 원본 보고서의 연구용 요약
- `strategy_designs/`: 조건식 설계 근거
- `generated_conditions/`: 실제 생성한 매수/매도 조건식
- `pilot_logs/`: 저장/백테스트 결과

## 주의

이 폴더의 연구용 조건식은 실전 채택 조건식이 아니다. 거래 데이터 확보와 자동 개선 루프의 기준 CSV 생성을 목적으로 한다.
```
```

- [ ] **Step 4: Create summary**

Create `docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md`:

```markdown
# backtest_analysis_report_v2 요약

## 원본

- 파일: `docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md`
- 원래 위치: `E:\Download\backtest_analysis_report_v2.md`
- 문서 버전: 2.0
- 분석 대상: STOM 백테스팅 결과 19건
- 분석 기간: 2022-02 ~ 2024-05

## 연구용 해석

이 문서는 최종 조건식을 그대로 복사하기 위한 자료가 아니다. 넓은 tick 연구용 baseline 조건식을 만들기 위한 변수/시간대/구조 참고 자료다.

## 핵심 설정

- 거래 시간대: `09:00 ~ 09:30`
- 평균 간격 실틱수: `30`
- 백테스트 기간: 최소 200거래일 이상 권장
- 평균보유기간: 200~300초 권장

## 주요 매수 변수

- 현재가
- 등락율
- 거래대금 계열
- 시가총액
- 시분초
- 체결강도
- 호가/수량 계열

## 주요 매도 변수

- 체결강도
- 이동평균
- 수익률
- 최고수익률
- 현재가
- 매수시간

## wide baseline 반영 원칙

- 시간대와 30틱 설정은 보고서 권장값을 따른다.
- 현재가, 등락율, 거래대금, 관심종목만 넓게 제한한다.
- 체결강도, 시가총액, 회전율, 전일동시간비, 이동평균은 처음부터 강하게 제한하지 않는다.
- 수익률보다 거래 데이터 확보를 우선한다.

## 다음 사용처

`ResearchTest_Tick_B_090000_092800_Wide_20260419`와 `ResearchTest_Tick_S_090000_092800_Wide_20260419` 설계의 근거로 사용한다.
```

- [ ] **Step 5: Verify files**

Run:

```powershell
Test-Path docs/research/condition_research/README.md
Test-Path docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md
Test-Path docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md
git diff --check
```

Expected:

```text
True
True
True
no git diff --check output
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add docs/research/condition_research/README.md docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md
git commit -m "조건식 연구 문서 기반을 구성한다" -m "외부 우수 전략 분석 보고서를 condition_research 문서 트리에 보존하고 wide tick 연구용 요약을 작성했다.

Constraint: 원본 보고서는 임의 수정 없이 보존해야 함
Confidence: high
Scope-risk: narrow
Tested: Test-Path docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md
Tested: git diff --check"
```

---

### Task 2: Wide Tick Buy/Sell Condition Documents

**Files:**
- Create: `docs/research/condition_research/strategy_designs/2026-04-19_tick_research_baseline_condition_design.md`
- Create: `docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md`

- [ ] **Step 1: Create strategy design doc**

Create `docs/research/condition_research/strategy_designs/2026-04-19_tick_research_baseline_condition_design.md`:

```markdown
# Tick Research Baseline Condition Design

## 전체 플로우

```text
[보고서 요약]
        |
        v
[넓은 tick 조건식 설계]
        |
        v
[strategy.db 저장]
        |
        v
[직접 백테스트]
        |
        v
[Retention-Aware 후보 개선]
```

## 목적

수익률 최적화가 아니라 자동 조건식 연구 루프가 분석할 충분한 거래 데이터를 확보하는 것이다.

## 전략명

- 매수: `ResearchTest_Tick_B_090000_092800_Wide_20260419`
- 매도: `ResearchTest_Tick_S_090000_092800_Wide_20260419`

## 설계 원칙

- 09:00:00~09:28:00 구간을 대상으로 한다.
- 30틱 기준을 사용한다.
- 관심종목, 현재가, 등락율, 당일거래대금 정도만 넓게 제한한다.
- 체결강도, 시가총액, 회전율, 전일동시간비, 이동평균은 자동 개선 루프의 후보로 남긴다.
- 매도는 단순 익절/손절/보유시간/시간 종료 청산만 둔다.

## 성공 기준

- 기존 `Tick_B_902_905_Update_2`의 2025년 100회 거래보다 훨씬 많은 거래가 발생해야 한다.
- 최소 유용 기준은 500회 이상이다.
- 수익률이 낮아도 실패로 보지 않는다.
```
```

- [ ] **Step 2: Create generated conditions doc**

Create `docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md`:

````markdown
# Research Test Tick Wide Conditions

## 목적

자동 조건식 연구용 거래 데이터를 확보하기 위한 넓은 tick baseline 조건식이다.

## 매수 전략명

`ResearchTest_Tick_B_090000_092800_Wide_20260419`

## 매수 조건식

```python
매수 = True

if 관심종목 != 1:
    매수 = False
elif not (0 < 현재가 <= 50000):
    매수 = False
elif not (90000 <= 시분초 <= 92800):
    매수 = False
elif not (0 < 등락율 <= 25):
    매수 = False
elif not (당일거래대금 > 100):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False

if 매수:
    self.Buy()
```

## 매도 전략명

`ResearchTest_Tick_S_090000_092800_Wide_20260419`

## 매도 조건식

```python
if 수익률 >= 3.0:
    self.Sell()

elif 수익률 <= -3.0:
    self.Sell()

elif 보유시간 >= 300:
    self.Sell()

elif 시분초 >= 92800:
    self.Sell()
```

## 비목표

- 실전 전략 아님
- WFO 검증 전 채택 금지
- 기존 최적화 전략 덮어쓰기 금지
````

- [ ] **Step 3: Verify docs**

Run:

```powershell
Test-Path docs/research/condition_research/strategy_designs/2026-04-19_tick_research_baseline_condition_design.md
Test-Path docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md
git diff --check
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add docs/research/condition_research/strategy_designs/2026-04-19_tick_research_baseline_condition_design.md docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md
git commit -m "넓은 틱 연구 조건식을 문서화한다" -m "연구 데이터 확보용 wide tick 매수/매도 조건식과 설계 근거를 문서화했다.

Constraint: 실전 최적화가 아니라 연구 baseline 확보가 목적임
Confidence: high
Scope-risk: narrow
Tested: git diff --check"
```

---

### Task 3: Validate And Save Wide Strategies

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_strategy_save.md`

- [ ] **Step 1: Validate strategy code without saving**

Run:

```powershell
@'
from cli.strategy import validate_strategy

buy_code = """매수 = True

if 관심종목 != 1:
    매수 = False
elif not (0 < 현재가 <= 50000):
    매수 = False
elif not (90000 <= 시분초 <= 92800):
    매수 = False
elif not (0 < 등락율 <= 25):
    매수 = False
elif not (당일거래대금 > 100):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False

if 매수:
    self.Buy()
"""

sell_code = """if 수익률 >= 3.0:
    self.Sell()

elif 수익률 <= -3.0:
    self.Sell()

elif 보유시간 >= 300:
    self.Sell()

elif 시분초 >= 92800:
    self.Sell()
"""

print('buy', validate_strategy(buy_code, v251_compat=True))
print('sell', validate_strategy(sell_code, v251_compat=True))
'@ | python -
```

Expected:

```text
buy {'status': 'ok', ...}
sell {'status': 'ok', ...}
```

- [ ] **Step 2: Check strategy-name collisions**

Run:

```powershell
@'
import sqlite3
from cli.paths import DB_STRATEGY

names = [
    ('stockbuy', 'ResearchTest_Tick_B_090000_092800_Wide_20260419'),
    ('stocksell', 'ResearchTest_Tick_S_090000_092800_Wide_20260419'),
]

with sqlite3.connect(DB_STRATEGY) as con:
    for table, name in names:
        count = con.execute(f'SELECT COUNT(*) FROM {table} WHERE "index"=?', (name,)).fetchone()[0]
        print(table, name, count)
'@ | python -
```

Expected:

```text
stockbuy ResearchTest_Tick_B_090000_092800_Wide_20260419 0
stocksell ResearchTest_Tick_S_090000_092800_Wide_20260419 0
```

- [ ] **Step 3: Save to strategy.db**

Run:

```powershell
@'
from cli.paths import DB_STRATEGY
from cli.strategy_generator import save_strategy_to_db
from cli.strategy import evaluate_strategy

buy_name = 'ResearchTest_Tick_B_090000_092800_Wide_20260419'
sell_name = 'ResearchTest_Tick_S_090000_092800_Wide_20260419'

buy_code = """매수 = True

if 관심종목 != 1:
    매수 = False
elif not (0 < 현재가 <= 50000):
    매수 = False
elif not (90000 <= 시분초 <= 92800):
    매수 = False
elif not (0 < 등락율 <= 25):
    매수 = False
elif not (당일거래대금 > 100):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False

if 매수:
    self.Buy()
"""

sell_code = """if 수익률 >= 3.0:
    self.Sell()

elif 수익률 <= -3.0:
    self.Sell()

elif 보유시간 >= 300:
    self.Sell()

elif 시분초 >= 92800:
    self.Sell()
"""

print(save_strategy_to_db(DB_STRATEGY, buy_name, buy_code, 'buy'))
print(save_strategy_to_db(DB_STRATEGY, sell_name, sell_code, 'sell'))
print(evaluate_strategy(DB_STRATEGY, buy_name, 'buy')['status'])
print(evaluate_strategy(DB_STRATEGY, sell_name, 'sell')['status'])
'@ | python -
```

Expected:

```text
{'status': 'ok', 'name': 'ResearchTest_Tick_B_090000_092800_Wide_20260419', 'action': 'created'}
{'status': 'ok', 'name': 'ResearchTest_Tick_S_090000_092800_Wide_20260419', 'action': 'created'}
ok
ok
```

- [ ] **Step 4: Record save log**

Create `docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_strategy_save.md` with actual command outputs:

```markdown
# Research Test Tick Wide Strategy Save Log

## 전략명

- buy: `ResearchTest_Tick_B_090000_092800_Wide_20260419`
- sell: `ResearchTest_Tick_S_090000_092800_Wide_20260419`

## 검증 결과

실제 validate/evaluate/save 결과를 기록한다.

## 주의

`strategy.db`는 로컬 런타임 DB이므로 Git에 커밋하지 않는다.
```

- [ ] **Step 5: Commit log**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_strategy_save.md
git commit -m "넓은 틱 연구 조건식 저장 기록을 남긴다" -m "ResearchTest tick wide 매수/매도 조건식의 구문 검증, strategy.db 저장, 로드 확인 결과를 기록했다.

Constraint: strategy.db는 로컬 런타임 DB라 커밋하지 않음
Confidence: high
Scope-risk: narrow
Tested: cli.strategy.validate_strategy
Tested: cli.strategy.evaluate_strategy"
```

---

### Task 4: Direct Backtest Pilot

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_backtest.md`
- Create: `docs/update_log/2026-04-19_tick_research_baseline_condition.md`

- [ ] **Step 1: Run direct backtest**

Run:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
```

Record:

```text
status
trade_count
avg_profit_pct
total_profit_pct
tpi
runtime
csv_path
```

- [ ] **Step 2: Verify strategy still exists**

Run:

```powershell
@'
import sqlite3
from cli.paths import DB_STRATEGY
for table, name in [
    ('stockbuy', 'ResearchTest_Tick_B_090000_092800_Wide_20260419'),
    ('stocksell', 'ResearchTest_Tick_S_090000_092800_Wide_20260419'),
]:
    with sqlite3.connect(DB_STRATEGY) as con:
        print(table, name, con.execute(f'SELECT COUNT(*) FROM {table} WHERE "index"=?', (name,)).fetchone()[0])
'@ | python -
```

Expected:

```text
1
1
```

- [ ] **Step 3: Create pilot log**

Create `docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_backtest.md`:

```markdown
# Research Test Tick Wide Backtest Pilot

## 전체 플로우

[wide strategy] -> [direct tick backtest] -> [CSV baseline for retention-aware loop]

## 실행 조건

- buy: `ResearchTest_Tick_B_090000_092800_Wide_20260419`
- sell: `ResearchTest_Tick_S_090000_092800_Wide_20260419`
- period: `2025-01-01 ~ 2025-12-31`
- time: `09:00:00 ~ 09:28:00`
- timeframe: `tick`
- avg_time: `30`
- engines: `32`

## 결과

실제 백테스트 결과를 기록한다.

## 판단

- 거래 수가 500회 이상이면 retention-aware 연구 기준 CSV로 사용 가능
- 거래 수가 너무 적으면 매수 조건을 더 넓혀야 함
- 거래 수가 너무 많고 runtime이 무거우면 최소 유동성 조건을 강화해야 함
```

- [ ] **Step 4: Create update log**

Create `docs/update_log/2026-04-19_tick_research_baseline_condition.md`:

```markdown
# 2026-04-19 Tick Research Baseline Condition

## 목적

자동 조건식 연구용 거래 데이터 확보를 위해 넓은 tick baseline 매수/매도 조건식을 생성하고 직접 백테스트했다.

## 변경 사항

- 외부 보고서 원문 보존
- 보고서 요약
- wide tick 조건식 문서화
- strategy.db 저장
- 직접 백테스트

## 결과

실제 백테스트 결과와 CSV 경로를 기록한다.

## 다음 단계

생성된 CSV를 `discovery research --run-candidates` 입력으로 사용한다.
```

- [ ] **Step 5: Run repository checks**

Run:

```powershell
git diff --check
python -m pytest tests/unit/test_strategy.py tests/unit/test_subcommands.py -q
python scripts/verify_nonrelease_sync.py
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-19_research_test_tick_wide_backtest.md docs/update_log/2026-04-19_tick_research_baseline_condition.md
git commit -m "넓은 틱 연구 기준 백테스트 결과를 기록한다" -m "ResearchTest tick wide 조건식의 직접 백테스트 결과와 다음 자동 개선 루프 입력 CSV 사용 가능 여부를 기록했다.

Constraint: 백테스트 CSV와 strategy.db는 로컬 런타임 산출물이라 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: python stom_backtest.py --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419
Tested: python scripts/verify_nonrelease_sync.py"
```

---

## Final Verification Checklist

- [ ] External report copied to `docs/research/condition_research/source_reports/`.
- [ ] Summary document created.
- [ ] Strategy design document created.
- [ ] Generated conditions document created.
- [ ] Strategy code validates through `cli.strategy.validate_strategy()`.
- [ ] Strategy names saved to local `strategy.db`.
- [ ] Direct tick backtest runs.
- [ ] Pilot log records trade count and CSV path.
- [ ] `python scripts/verify_nonrelease_sync.py` passes.
- [ ] Existing optimized strategies are not overwritten.

## Plan Self-Review Notes

- Spec coverage: source report preservation, summary, strategy design, generated conditions, DB save, direct backtest, pilot log, and update log are covered.
- Scope: this plan does not implement WFO, automatic improvement loop v2, or core backtest changes.
- Type consistency: strategy names match the spec exactly.
