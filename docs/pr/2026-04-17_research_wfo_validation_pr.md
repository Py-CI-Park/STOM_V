# discovery research WFO 검증 연결 PR 보고서

## 목적

`discovery research`가 생성한 후보 전략을 WFO로 검증할 수 있도록 연결한다.

PR #8에서 세그먼트 기반 조건식 연구 루프 1차 기반이 들어갔지만, 후보 판단은 아직 단일 CSV 비교와 휴리스틱 게이트 중심이었다. 이번 PR은 후보 전략이 여러 forward validation window에서도 유지되는지 확인할 수 있도록 기존 WFO 경로를 선택 옵션으로 연결한다.

## 변경 요약

- `ResearchLoopConfig`에 WFO 설정 필드를 추가했다.
- `discovery research`에 `--run-wfo` 옵션을 추가했다.
- `--run-wfo`는 `--run-candidate`와 train/test window 설정이 있을 때만 실행된다.
- WFO promotion criteria를 후보 전략 저장/백테스트/WFO 실행보다 먼저 검증한다.
- 후보 전략 백테스트 이후 기존 `AIBacktestController.walk_forward()`를 호출한다.
- 기존 `AIBacktestController.evaluate_walk_forward_result()`로 WFO 결과를 평가한다.
- `combined_evaluation`으로 CSV 비교 통과 여부와 WFO 통과 여부를 함께 판단한다.
- 연구 리포트에 `## WFO 검증`, `## 최종 판단` 섹션을 추가했다.
- CLI param-space 입력 오류가 traceback으로 새지 않도록 구조화된 JSON 오류로 처리했다.

## 주요 파일

- `cli/research_loop.py`
- `cli/research_report.py`
- `cli/subcommands.py`
- `tests/unit/test_research_loop.py`
- `tests/unit/test_research_report.py`
- `tests/unit/test_subcommands.py`
- `docs/superpowers/specs/2026-04-17-research-wfo-validation-design.md`
- `docs/superpowers/plans/2026-04-17-research-wfo-validation.md`
- `docs/update_log/2026-04-17_research_wfo_validation.md`

## CLI 사용 예시

```powershell
python stom_backtest.py discovery research AutoResearchWfo `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --run-wfo `
  --train-window-days 5 `
  --test-window-days 2
```

기존 CSV를 후보 생성 입력으로 쓰면서 WFO만 같은 기간 설정으로 검증할 수도 있다.

```powershell
python stom_backtest.py discovery research AutoResearchWfo `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --run-wfo `
  --train-window-days 5 `
  --test-window-days 2
```

## 검증

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
84 passed
```

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

결과:

```text
133 passed
```

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
930 passed, 1 skipped, 10 warnings
```

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 남은 리스크

1. WFO는 과최적화 위험을 줄이는 검증 장치이지 수익을 보장하지 않는다.
2. 실제 장기간 데이터에 대한 운영 파일럿은 별도 수행이 필요하다.
3. 기회집합 로그와 조건식 변형은 후속 Phase이다.
4. WFO 실행 비용이 크므로 계속 opt-in으로 유지해야 한다.
5. 매우 짧은 기간에서는 WFO window가 없을 수 있으며, 이 경우 구조화된 실패로 처리해야 한다.

## PR 판단

이번 PR은 후보 생성 능력을 넓히는 작업이 아니라 검증 계층을 강화하는 작업이다.

PR #8에서 만든 연구 루프 기반 위에 WFO/OOS 검증을 선택적으로 연결하므로, 전체 조건식 연구 자동화 방향성과 맞다.
