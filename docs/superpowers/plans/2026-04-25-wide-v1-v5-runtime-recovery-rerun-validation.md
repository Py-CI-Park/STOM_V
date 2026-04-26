# Wide v1 v5 Runtime Recovery Rerun Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Runtime recovery 적용 후 Wide v1 v5를 `candidate_count=10`으로 재실행하고, 실제 row-set 대표 10개 확보 여부를 근거로 promote/WFO 또는 v6 보강으로 분기한다.

**Architecture:** v5 실행 자체는 기존 `stom_backtest.py discovery research` 경로를 유지하고, 새 런타임 복구 옵션인 `--runtime-output`과 `--max-consecutive-candidate-failures`만 명시한다. 검증은 런타임 JSON을 단일 근거로 삼아 checkpoint, candidate 성공/실패 수, actual row-set 선택 결과를 파싱하고 한국어 pilot/PR 보고서에 기록한다. `backtest/` 산출물은 실행 증거로만 사용하고 커밋하지 않는다.

**Tech Stack:** Python 3.11, PowerShell, `stom_backtest.py`, `cli.research_v3_decision.read_runtime_json`, `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`, pytest, git.

---

## File Structure

- Modify: `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`
  - v5 판정 보고서의 다음 명령어 문자열을 깨지지 않는 한국어로 정규화한다.
  - runtime은 성공했지만 candidate 성공 수가 부족해 `actual_rowset_selection.status='not_run'`인 경우를 명시적으로 `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`로 판정한다.
- Modify: `tests/unit/test_wide_v1_v5_analysis.py`
  - 깨지지 않은 다음 명령어 문자열을 기대하도록 갱신한다.
  - `actual_rowset_selection.status='not_run'` 회귀 테스트를 추가한다.
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md`
  - 실제 재실행 후 분석 스크립트가 생성하는 v5 actual row-set 판정 보고서다.
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_iteration_loop_v5_recovery.md`
  - v5 재실행의 목적, 명령어, runtime checkpoint, candidate 결과, 의사결정을 한국어로 기록한다.
- Create: `docs/pr/2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md`
  - 이전 PR 형식에 맞춘 한국어 마크다운 PR 보고서다.
- Use but do not stage: `backtest/temp/wide_v1_iteration_v5_recovery_20260425.json`
  - `--runtime-output` 결과물이다.
- Use but do not stage: `backtest/temp/wide_v1_v5_recovery_preflight_20260425.json`
  - runtime preflight 결과물이다.

---

## MVP Fast-Finish Roadmap

현재 MVP 종료까지의 가장 빠른 경로는 v5 재실행 결과에 따라 갈린다.

1. Current PR: v5 runtime recovery 재실행 검증
   - 목적: v5가 멈추지 않고, candidate 10개 요청에서 실제 row-set 대표 10개를 확보하는지 확인한다.
   - 종료 조건: 아래 세 결정 중 하나가 문서화된다.
     - `PROCEED_TO_PROMOTE_WFO_PLAN`
     - `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`
     - `HOLD_V5_RUNTIME_FAILURE`
2. Happy path PR 1: v5 promote 및 WFO 검증
   - 조건: `actual_rowset_selection.status='ok'`, `row_set_identity_status='all_distinct'`, `selected_count >= requested_count`.
   - 산출물: promote 후보, WFO 실행 결과, pass/fail 기준 보고서.
3. Happy path PR 2: MVP freeze 및 운영 문서화
   - 조건: WFO가 기준을 통과한다.
   - 산출물: 최종 전략 artifact, 재현 명령어, CLI 사용 문서, known risks, 다음 연구 backlog.
4. Recovery path PR 1: v6 actual row-set generation expansion
   - 조건: v5 runtime은 성공했지만 실제 row-set 대표가 10개 미만이다.
   - 목적: 조건식 후보 생성 범위를 넓혀 중복 row-set을 줄인다.
5. Recovery path PR 2: runner timeout cleanup recovery
   - 조건: v5가 runtime failure로 종료된다.
   - 목적: candidate별 timeout, stale process 정리, partial CSV/JSON 복구 규칙을 보강한다.

빠른 종료 기준으로는 이 계획 이후 happy path에서 2개 PR이 남는다. v5가 shortfall 또는 runtime failure면 보강 PR 1개를 먼저 넣고 다시 v5 재실행 검증으로 돌아간다.

---

### Task 1: v5 Analysis Report Decision Compatibility

**Files:**
- Modify: `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`
- Modify: `tests/unit/test_wide_v1_v5_analysis.py`

- [ ] **Step 1: Update the failing expectations first**

In `tests/unit/test_wide_v1_v5_analysis.py`, replace the mojibake command assertions and add the `not_run` case:

```python
def test_analyze_wide_v1_v5_actual_rowset_selection_proceeds_when_actual_rows_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v5_actual_rowset_selection.py'
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'v5_report.md'
    runtime_path.write_text(
        json.dumps(
            {
                'status': 'ok',
                'actual_rowset_selection': {
                    'status': 'ok',
                    'row_set_identity_status': 'all_distinct',
                    'requested_count': 10,
                    'selected_count': 10,
                    'executed_count': 18,
                    'actual_group_count': 12,
                    'duplicate_actual_rowset_count': 6,
                },
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out
    markdown = output_path.read_text(encoding='utf-8')

    assert excinfo.value.code == 0
    assert 'decision=PROCEED_TO_PROMOTE_WFO_PLAN' in stdout
    assert 'next_command=$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성' in stdout
    assert 'row_set_identity_status=all_distinct' in stdout
    assert 'selected_count=10' in stdout
    assert '# Wide v1 v5 actual row-set selection' in markdown
    assert 'decision=PROCEED_TO_PROMOTE_WFO_PLAN' in markdown


def test_analyze_wide_v1_v5_actual_rowset_selection_holds_when_actual_selection_not_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v5_actual_rowset_selection.py'
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'v5_report.md'
    runtime_path.write_text(
        json.dumps(
            {
                'status': 'ok',
                'phase': 'candidates_evaluated',
                'actual_rowset_selection': {
                    'status': 'not_run',
                    'reason': 'insufficient_successful_candidates',
                    'requested_count': 10,
                    'selected_count': 0,
                    'executed_count': 6,
                },
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out
    markdown = output_path.read_text(encoding='utf-8')

    assert excinfo.value.code == 0
    assert 'decision=HOLD_V5_ACTUAL_ROW_SET_SHORTFALL' in stdout
    assert 'next_command=$brainstorming Wide v1 v6 actual row-set generation expansion 설계' in stdout
    assert 'actual_selection_status=not_run' in markdown
    assert 'actual_selection_reason=insufficient_successful_candidates' in markdown
```

Also update the existing shortfall and runtime failure command assertions to:

```python
assert 'next_command=$brainstorming Wide v1 v6 actual row-set generation expansion 설계' in stdout
assert 'next_command=$brainstorming Wide v1 v5 runtime failure recovery 설계' in stdout
```

- [ ] **Step 2: Run the focused test and confirm it fails before implementation**

Run:

```powershell
python -m pytest tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
FAILED tests/unit/test_wide_v1_v5_analysis.py::test_analyze_wide_v1_v5_actual_rowset_selection_proceeds_when_actual_rows_are_distinct
FAILED tests/unit/test_wide_v1_v5_analysis.py::test_analyze_wide_v1_v5_actual_rowset_selection_holds_when_actual_selection_not_run
```

- [ ] **Step 3: Normalize the report script**

In `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`, replace `NEXT_COMMANDS` and add status/reason lines to `render_v5_actual_rowset_markdown`:

```python
NEXT_COMMANDS = {
    PROCEED_TO_PROMOTE_WFO_PLAN: '$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성',
    HOLD_V5_RUNTIME_FAILURE: '$brainstorming Wide v1 v5 runtime failure recovery 설계',
    HOLD_V5_ACTUAL_ROW_SET_SHORTFALL: '$brainstorming Wide v1 v6 actual row-set generation expansion 설계',
}
```

Inside `render_v5_actual_rowset_markdown`, immediately after the `actual_selection = ...` line is available through `analysis`, render these two fields:

```python
        f"- actual_selection_status={_as_dict(analysis.get('actual_rowset_selection')).get('status')}",
        f"- actual_selection_reason={_as_dict(analysis.get('actual_rowset_selection')).get('reason')}",
```

The resulting line block must include:

```python
        f"- runtime_phase={analysis.get('runtime_phase')}",
        f"- actual_selection_status={_as_dict(analysis.get('actual_rowset_selection')).get('status')}",
        f"- actual_selection_reason={_as_dict(analysis.get('actual_rowset_selection')).get('reason')}",
        f"- row_set_identity_status={analysis.get('row_set_identity_status')}",
```

- [ ] **Step 4: Verify the focused test passes**

Run:

```powershell
python -m pytest tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit compatibility changes**

Run:

```powershell
git add scripts/analyze_wide_v1_v5_actual_rowset_selection.py tests/unit/test_wide_v1_v5_analysis.py
git commit -m "Wide v1 v5 판정 보고서 명령어를 정규화한다" -m "v5 runtime recovery 이후 not_run 상태도 shortfall hold로 판정할 수 있어야 한다. 보고서의 다음 superpower 명령어가 깨져 있으면 다음 PR 분기가 잘못 전달되므로 한국어 명령어 문자열을 정규화했다." -m "Constraint: v5 재실행 판정은 runtime JSON 하나로 promote/WFO 또는 v6 보강을 결정해야 한다`nRejected: 깨진 문자열 유지 | PR 보고서와 다음 명령어 안내가 불명확해진다`nConfidence: high`nScope-risk: narrow`nTested: python -m pytest tests/unit/test_wide_v1_v5_analysis.py -q"
```

Expected:

```text
[feature/wide-v1-v5-runtime-recovery-rerun-validation <hash>] Wide v1 v5 판정 보고서 명령어를 정규화한다
```

---

### Task 2: Preflight Runtime Recovery Verification

**Files:**
- Read: `docs/pr/2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md`
- Use but do not stage: `backtest/temp/wide_v1_v5_recovery_preflight_20260425.json`

- [ ] **Step 1: Confirm branch and tracked cleanliness**

Run:

```powershell
git branch --show-current
git status --short --untracked-files=no
```

Expected:

```text
feature/wide-v1-v5-runtime-recovery-rerun-validation
```

The second command prints no tracked changes after Task 1 commit.

- [ ] **Step 2: Run the runtime recovery regression suite**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Expected:

```text
166 passed
```

- [ ] **Step 3: Run one runtime preflight and save the evidence outside git staging**

Run:

```powershell
python .\stom_backtest.py runtime-preflight --buy WideV1IterationV2_20260423__cand005 --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 --start 20250101 --end 20251231 --timeframe tick --betting 20 --avg-time 30 --start-time 90000 --end-time 92800 --engines 32 --timeout 900 *> backtest\temp\wide_v1_v5_recovery_preflight_20260425.json
```

Expected:

```text
backtest\temp\wide_v1_v5_recovery_preflight_20260425.json exists and contains JSON with status ok or a concrete preflight failure reason.
```

- [ ] **Step 4: Parse the preflight evidence**

Run:

```powershell
@'
import json
from pathlib import Path

path = Path("backtest/temp/wide_v1_v5_recovery_preflight_20260425.json")
text = path.read_text(encoding="utf-8", errors="replace")
start = text.find("{")
end = text.rfind("}") + 1
data = json.loads(text[start:end])
print(f"status={data.get('status')}")
print(f"phase={data.get('phase')}")
print(f"buy={data.get('buy')}")
print(f"sell={data.get('sell')}")
print(f"timeout={data.get('timeout')}")
'@ | python -
```

Expected accepted output:

```text
status=ok
```

If `status=error`, stop before Task 3 and document `HOLD_V5_RUNTIME_FAILURE` in Task 5 using the preflight error.

---

### Task 3: Execute v5 candidate_count=10 With Runtime Output

**Files:**
- Use but do not stage: `backtest/temp/wide_v1_iteration_v5_recovery_20260425.json`
- Use but do not stage: `backtest/temp/wide_v1_iteration_v5_recovery_20260425.stdout.txt`

- [ ] **Step 1: Define the exact execution variables**

Run:

```powershell
$RuntimePath = 'backtest\temp\wide_v1_iteration_v5_recovery_20260425.json'
$StdoutPath = 'backtest\temp\wide_v1_iteration_v5_recovery_20260425.stdout.txt'
$InputCsv = 'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
$ScoreReferenceCsv = 'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
Remove-Item -LiteralPath $RuntimePath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $StdoutPath -Force -ErrorAction SilentlyContinue
```

Expected:

```text
No PowerShell error.
```

- [ ] **Step 2: Confirm the two required CSV inputs exist**

Run:

```powershell
Test-Path -LiteralPath $InputCsv
Test-Path -LiteralPath $ScoreReferenceCsv
```

Expected:

```text
True
True
```

- [ ] **Step 3: Run v5 recovery rerun**

Run:

```powershell
python .\stom_backtest.py discovery research WideV1IterationV5Recovery_20260425 `
  --input $InputCsv `
  --score-reference-csv $ScoreReferenceCsv `
  --base-buy-strategy WideV1IterationV2_20260423__cand005 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --betting 20 `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --top-n 10 `
  --run-candidates `
  --candidate-count 10 `
  --candidate-timeout 900 `
  --candidate-pool-multiplier 3 `
  --cleanup-best-candidate `
  --runtime-output $RuntimePath `
  --max-consecutive-candidate-failures 3 `
  --iteration-v2-mode best_feature_mix_v5 `
  --iteration-v2-best-candidate WideV1IterationV2_20260423__cand005 `
  --iteration-v2-best-expression '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4' `
  --iteration-v2-primary-feature 'B_시가총액' `
  --iteration-v2-secondary-features 'B_체결강도,B_등락율,B_당일거래대금' *> $StdoutPath
```

Expected accepted terminal result:

```text
The command exits with code 0 or exits with code 1 after writing backtest\temp\wide_v1_iteration_v5_recovery_20260425.json.
```

Exit code 0 is not enough to promote. The runtime JSON fields decide the next branch.

- [ ] **Step 4: Monitor runtime JSON if the command is still running**

In a second PowerShell session from `C:\System_Trading\STOM\STOM_V.wt-dev`, run:

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

p = Path("backtest/temp/wide_v1_iteration_v5_recovery_20260425.json")
if not p.exists():
    print("runtime_exists=False")
else:
    data = read_runtime_json(p)
    print(f"status={data.get('status')}")
    print(f"phase={data.get('phase')}")
    print(f"checkpoint={((data.get('checkpoint_summary') or {}).get('last_checkpoint'))}")
    print(f"candidate_result_count={len(data.get('candidates') or [])}")
    print(f"failure_policy={data.get('failure_policy')}")
    print(f"actual_rowset_selection={data.get('actual_rowset_selection')}")
'@ | python -
```

Expected while progressing:

```text
runtime_exists=False
```

or:

```text
status=running
phase=<current phase>
checkpoint=<new checkpoint name>
candidate_result_count=<increasing integer>
```

If the process has no CPU activity, no stdout growth, and no new checkpoint for 20 minutes, record the latest runtime JSON as `HOLD_V5_RUNTIME_FAILURE` evidence in Task 5.

---

### Task 4: Parse v5 Runtime and Generate Actual Row-Set Decision

**Files:**
- Read: `backtest/temp/wide_v1_iteration_v5_recovery_20260425.json`
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md`

- [ ] **Step 1: Print the runtime decision facts**

Run:

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

runtime_path = Path("backtest/temp/wide_v1_iteration_v5_recovery_20260425.json")
runtime = read_runtime_json(runtime_path)
selection = runtime.get("actual_rowset_selection") or {}
failure = runtime.get("failure_policy") or {}
checkpoints = runtime.get("checkpoints") or []
candidates = runtime.get("candidates") or []
ok_count = sum(1 for c in candidates if c.get("status") == "ok")
err_count = sum(1 for c in candidates if c.get("status") != "ok")
print(f"status={runtime.get('status')}")
print(f"phase={runtime.get('phase')}")
print(f"checkpoint={((runtime.get('checkpoint_summary') or {}).get('last_checkpoint'))}")
print(f"candidate_result_count={len(candidates)}")
print(f"successful_candidate_count={ok_count}")
print(f"failed_candidate_count={err_count}")
print(f"failure_policy={failure}")
print(f"actual_selection_status={selection.get('status')}")
print(f"actual_selection_reason={selection.get('reason')}")
print(f"row_set_identity_status={selection.get('row_set_identity_status')}")
print(f"selected_count={selection.get('selected_count')}")
print(f"requested_count={selection.get('requested_count')}")
print(f"checkpoint_count={len(checkpoints)}")
'@ | python -
```

Expected accepted decision paths:

```text
status=ok
actual_selection_status=ok
row_set_identity_status=all_distinct
selected_count=10
requested_count=10
```

or:

```text
status=ok
actual_selection_status=not_run
actual_selection_reason=insufficient_successful_candidates
```

or:

```text
status=error
phase=<runtime failure phase>
```

- [ ] **Step 2: Generate the actual row-set decision markdown**

Run:

```powershell
python scripts\analyze_wide_v1_v5_actual_rowset_selection.py --runtime-path backtest\temp\wide_v1_iteration_v5_recovery_20260425.json --output docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md
```

Expected accepted outputs:

```text
decision=PROCEED_TO_PROMOTE_WFO_PLAN
next_command=$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성
```

or:

```text
decision=HOLD_V5_ACTUAL_ROW_SET_SHORTFALL
next_command=$brainstorming Wide v1 v6 actual row-set generation expansion 설계
```

or:

```text
decision=HOLD_V5_RUNTIME_FAILURE
next_command=$brainstorming Wide v1 v5 runtime failure recovery 설계
```

---

### Task 5: Write Korean Pilot and PR Reports

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_iteration_loop_v5_recovery.md`
- Create: `docs/pr/2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md`
- Read: `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md`
- Read: `backtest/temp/wide_v1_iteration_v5_recovery_20260425.json`

- [ ] **Step 1: Generate the Korean report drafts from runtime JSON**

Run:

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json
from scripts.analyze_wide_v1_v5_actual_rowset_selection import decide_v5_actual_rowset

runtime_path = Path("backtest/temp/wide_v1_iteration_v5_recovery_20260425.json")
runtime = read_runtime_json(runtime_path)
analysis = decide_v5_actual_rowset(runtime)
selection = runtime.get("actual_rowset_selection") or {}
failure = runtime.get("failure_policy") or {}
checkpoints = runtime.get("checkpoints") or []
candidates = runtime.get("candidates") or []
ok_count = sum(1 for c in candidates if c.get("status") == "ok")
err_count = sum(1 for c in candidates if c.get("status") != "ok")
last_checkpoint = (runtime.get("checkpoint_summary") or {}).get("last_checkpoint")

pilot_path = Path("docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_iteration_loop_v5_recovery.md")
pr_path = Path("docs/pr/2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md")
pilot_path.parent.mkdir(parents=True, exist_ok=True)
pr_path.parent.mkdir(parents=True, exist_ok=True)

decision = analysis["decision"]
next_command = analysis["next_command"]

pilot = f"""# Wide v1 v5 runtime recovery 재실행 검증

## 목적

v5의 목적은 v4에서 좋아 보이는 후보 조건식이 실제 백테스트 row-set에서도 서로 다른 매매 집합을 만드는지 확인하는 것이다. 이번 재실행은 runtime recovery 적용 후 `candidate_count=10` 요청이 멈춤 없이 완료되고, 실제 row-set 대표 10개를 확보하는지 검증한다.

## 실행 조건

- branch: feature/wide-v1-v5-runtime-recovery-rerun-validation
- runtime_path: {runtime_path}
- candidate_count: 10
- candidate_timeout: 900
- max_consecutive_candidate_failures: 3
- base_buy_strategy: WideV1IterationV2_20260423__cand005
- sell_strategy: ResearchTest_Tick_S_090000_092800_Wide_20260419
- period: 20250101-20251231

## Runtime 결과

- status: {runtime.get("status")}
- phase: {runtime.get("phase")}
- last_checkpoint: {last_checkpoint}
- checkpoint_count: {len(checkpoints)}
- candidate_result_count: {len(candidates)}
- successful_candidate_count: {ok_count}
- failed_candidate_count: {err_count}
- failure_policy: {failure}

## Actual row-set selection

- status: {selection.get("status")}
- reason: {selection.get("reason")}
- row_set_identity_status: {selection.get("row_set_identity_status")}
- requested_count: {selection.get("requested_count")}
- selected_count: {selection.get("selected_count")}
- executed_count: {selection.get("executed_count")}
- actual_group_count: {selection.get("actual_group_count")}
- duplicate_actual_rowset_count: {selection.get("duplicate_actual_rowset_count")}

## 결정

- decision: {decision}
- next_command: {next_command}

## 전문가 검토

퀀트 관점에서는 v5가 단순히 조건식 10개를 실행하는 단계가 아니라, 실제 체결 row-set이 분리되는지 확인하는 검증 단계다. CLI 관점에서는 runtime JSON이 partial failure, checkpoint, 최종 decision을 모두 남겨야 재실행과 PR 리뷰가 가능하다. 전체 프로젝트 관점에서는 이 결과가 MVP를 WFO/promote로 보낼지, v6 후보 생성 확장으로 되돌릴지를 결정하는 merge point다.
"""

pr = f"""# Wide v1 v5 runtime recovery 재실행 검증 PR

## 전체 계획

Wide v1의 MVP 종료 경로는 `후보 생성 -> 실제 row-set 검증 -> promote/WFO -> MVP freeze` 순서다. 이번 PR은 runtime recovery가 적용된 v5를 `candidate_count=10`으로 재실행하여, v5가 promote 가능한 상태인지 또는 v6 보강이 필요한지 결정한다.

## 현재 계획

1. v5 분석 보고서의 다음 명령어 문자열을 한국어로 정규화한다.
2. runtime recovery 관련 단위 테스트를 통과시킨다.
3. v5를 `candidate_count=10`, `--runtime-output`, `--max-consecutive-candidate-failures 3`로 재실행한다.
4. runtime JSON에서 checkpoint, candidate 성공/실패 수, actual row-set 대표 선택 결과를 파싱한다.
5. decision과 next_command를 pilot log와 PR 보고서에 남긴다.

## 실행 결과

- runtime_path: {runtime_path}
- status: {runtime.get("status")}
- phase: {runtime.get("phase")}
- last_checkpoint: {last_checkpoint}
- candidate_result_count: {len(candidates)}
- successful_candidate_count: {ok_count}
- failed_candidate_count: {err_count}
- actual_selection_status: {selection.get("status")}
- actual_selection_reason: {selection.get("reason")}
- row_set_identity_status: {selection.get("row_set_identity_status")}
- requested_count: {selection.get("requested_count")}
- selected_count: {selection.get("selected_count")}

## 결정

- decision: {decision}
- next_command: {next_command}

## 변경 파일

- `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`
- `tests/unit/test_wide_v1_v5_analysis.py`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md`
- `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_iteration_loop_v5_recovery.md`
- `docs/pr/2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md`

## 커밋 제외 파일

- `backtest/temp/wide_v1_iteration_v5_recovery_20260425.json`
- `backtest/temp/wide_v1_iteration_v5_recovery_20260425.stdout.txt`
- `backtest/temp/wide_v1_v5_recovery_preflight_20260425.json`

## 검증

- `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`
- `cmd /c "git diff --check --ignore-cr-at-eol 2>&1"`

## 남은 리스크

v5가 실제 row-set 대표 10개를 확보하지 못하면 전략 품질 문제가 아니라 후보 생성 다양성 문제일 수 있다. 이 경우 promote/WFO로 진행하지 않고 v6 actual row-set generation expansion 설계로 분기한다.
"""

pilot_path.write_text(pilot, encoding="utf-8")
pr_path.write_text(pr, encoding="utf-8")
print(f"wrote={pilot_path}")
print(f"wrote={pr_path}")
'@ | python -
```

Expected:

```text
wrote=docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_iteration_loop_v5_recovery.md
wrote=docs\pr\2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md
```

- [ ] **Step 2: Review the three markdown reports**

Run:

```powershell
Get-Content docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md
Get-Content docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_iteration_loop_v5_recovery.md
Get-Content docs\pr\2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md
```

Expected:

```text
Each file includes decision=<one accepted decision> and next_command=<matching command>.
```

---

### Task 6: Verification and Commit

**Files:**
- Stage only:
  - `scripts/analyze_wide_v1_v5_actual_rowset_selection.py`
  - `tests/unit/test_wide_v1_v5_analysis.py`
  - `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md`
  - `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_iteration_loop_v5_recovery.md`
  - `docs/pr/2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md`

- [ ] **Step 1: Run full focused verification**

Run:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

Expected:

```text
166 passed
```

and:

```text
No whitespace errors.
```

- [ ] **Step 2: Confirm no protected runtime artifacts are staged**

Run:

```powershell
git status --short
```

Expected staged list after the next step must not include:

```text
backtest/temp/wide_v1_iteration_v5_recovery_20260425.json
backtest/temp/wide_v1_iteration_v5_recovery_20260425.stdout.txt
backtest/temp/wide_v1_v5_recovery_preflight_20260425.json
backtest/graph/
backtest/csv/
```

- [ ] **Step 3: Stage explicit files only**

Run:

```powershell
git add scripts/analyze_wide_v1_v5_actual_rowset_selection.py tests/unit/test_wide_v1_v5_analysis.py docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md docs\research\condition_research\pilot_logs\2026-04-25_wide_v1_iteration_loop_v5_recovery.md docs\pr\2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md
git status --short
```

Expected staged files:

```text
M  scripts/analyze_wide_v1_v5_actual_rowset_selection.py
M  tests/unit/test_wide_v1_v5_analysis.py
A  docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_recovery_actual_rowset_selection.md
A  docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_iteration_loop_v5_recovery.md
A  docs/pr/2026-04-25_wide_v1_v5_runtime_recovery_rerun_validation_pr.md
```

- [ ] **Step 4: Commit rerun validation**

Run:

```powershell
git commit -m "Wide v1 v5 런타임 복구 재실행을 검증한다" -m "candidate_count=10 재실행의 runtime JSON을 기준으로 promote/WFO 진행 여부를 결정한다. 실제 row-set 대표 10개가 확보되면 WFO 계획으로 가고, 부족하거나 runtime failure가 발생하면 각각 v6 생성 확장 또는 runtime recovery 보강으로 분기한다." -m "Constraint: backtest 산출물은 증거로만 사용하고 커밋하지 않는다`nRejected: stdout 로그만으로 판정 | partial failure와 checkpoint 근거가 부족하다`nConfidence: medium`nScope-risk: moderate`nDirective: v5 promote는 actual_rowset_selection.status=ok 및 all_distinct 없이는 진행하지 않는다`nTested: python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`nTested: cmd /c `"git diff --check --ignore-cr-at-eol 2>&1`""
```

Expected:

```text
[feature/wide-v1-v5-runtime-recovery-rerun-validation <hash>] Wide v1 v5 런타임 복구 재실행을 검증한다
```

---

### Task 7: Merge Point and Next Branch

**Files:**
- No file modification in this task.

- [ ] **Step 1: Merge the validation branch into `STOM_Version_2U_C`**

Run:

```powershell
git checkout STOM_Version_2U_C
git merge --no-ff feature/wide-v1-v5-runtime-recovery-rerun-validation -m "Wide v1 v5 런타임 복구 재실행 검증을 병합한다" -m "runtime recovery 이후 v5 candidate_count=10 재실행 결과를 merge point로 남긴다. 이 병합은 다음 단계를 promote/WFO, v6 row-set 확장, runtime failure 보강 중 하나로 분기하기 위한 기준점이다." -m "Constraint: 2U_C는 현재 단일 baseline lane이다`nRejected: 2U_C 직접 커밋 지속 | PR 흐름과 merge point가 사라진다`nConfidence: medium`nScope-risk: moderate`nTested: validation branch verification commands passed before merge"
```

Expected:

```text
Merge made by the 'ort' strategy.
```

- [ ] **Step 2: Create the next branch from the decision**

If Task 4 output was `PROCEED_TO_PROMOTE_WFO_PLAN`, run:

```powershell
git checkout -b feature/wide-v1-v5-promote-wfo-validation-plan
```

Then use:

```text
$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성
```

If Task 4 output was `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`, run:

```powershell
git checkout -b feature/wide-v1-v6-actual-rowset-generation-expansion-design
```

Then use:

```text
$brainstorming Wide v1 v6 actual row-set generation expansion 설계
```

If Task 4 output was `HOLD_V5_RUNTIME_FAILURE`, run:

```powershell
git checkout -b feature/wide-v1-v5-runner-timeout-cleanup-recovery
```

Then use:

```text
$brainstorming Wide v1 v5 runner timeout cleanup recovery 설계
```

Expected:

```text
Switched to a new branch '<matching next branch>'
```

---

## Decision Rules

- `PROCEED_TO_PROMOTE_WFO_PLAN`
  - `runtime.status in {'ok', 'success'}`
  - `actual_rowset_selection.status == 'ok'`
  - `actual_rowset_selection.row_set_identity_status == 'all_distinct'`
  - `selected_count >= requested_count`
- `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`
  - runtime은 완료됐지만 actual row-set 대표 10개 확보에 실패했다.
  - 대표 예시는 `actual_rowset_selection.status in {'shortfall', 'not_run'}` 또는 `row_set_identity_status != 'all_distinct'`다.
- `HOLD_V5_RUNTIME_FAILURE`
  - `runtime.status == 'error'`
  - 대표 phase는 `candidate_iteration_runtime_failure`, `runtime_output_write_failure`, `baseline`, `analysis`, `expression`, `retention`이다.

---

## Self-Review

- Spec coverage: runtime recovery 적용 후 `candidate_count=10` 재실행, actual row-set 검증, 한국어 보고서, 다음 단계 및 MVP 종료 경로를 모두 포함했다.
- Placeholder scan: 이 문서는 작업자가 채워 넣어야 하는 빈 항목 없이 모든 파일 경로, 명령어, 기대 출력을 명시한다.
- Type consistency: runtime 파싱은 `read_runtime_json(Path) -> dict`와 기존 `decide_v5_actual_rowset(runtime)` 경로를 사용한다. decision 문자열은 `PROCEED_TO_PROMOTE_WFO_PLAN`, `HOLD_V5_ACTUAL_ROW_SET_SHORTFALL`, `HOLD_V5_RUNTIME_FAILURE` 세 개로 통일했다.
