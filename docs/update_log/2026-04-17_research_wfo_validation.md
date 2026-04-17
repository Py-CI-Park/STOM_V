# 2026-04-17 research WFO validation

## 개요

`discovery research` 후보 전략 검증에 선택형 WFO 검증을 연결했다.

이번 변경은 PR #8에서 추가된 세그먼트 기반 조건식 연구 루프 위에 검증 계층을 얹는 작업이다. 후보 전략을 생성하고 기준/후보 CSV를 비교한 뒤, 사용자가 `--run-wfo`를 명시한 경우 기존 WFO 경로를 재사용해 OOS 검증 결과까지 함께 판단한다.

## 변경 사항

- `ResearchLoopConfig`에 WFO 설정 필드를 추가했다.
- `--run-wfo`가 `--run-candidate` 없이 실행되지 않도록 막았다.
- `--run-wfo` 실행 시 `--train-window-days`, `--test-window-days`를 요구한다.
- WFO promotion criteria를 후보 전략 저장/백테스트 전에 사전 검증한다.
- 후보 전략 백테스트 이후 `controller.walk_forward()`와 `controller.evaluate_walk_forward_result()`를 호출한다.
- CSV 비교 승격 결과와 WFO 평가 결과를 `combined_evaluation`으로 결합한다.
- 연구 리포트에 `## WFO 검증`, `## 최종 판단` 섹션을 추가했다.
- `discovery research` CLI에 WFO 옵션을 추가했다.
- 잘못된 `--param-space-json` 또는 누락된 `--param-space-file`이 traceback으로 새지 않도록 CLI 오류 응답을 추가했다.

## CLI 예시

```powershell
python stom_backtest.py discovery research AutoResearchWfo `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --run-wfo `
  --train-window-days 20 `
  --test-window-days 5
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

1. WFO는 과최적화 위험을 줄이는 검증 장치이며 수익을 보장하지 않는다.
2. 실제 장기간 데이터에 대한 운영 파일럿은 별도 수행이 필요하다.
3. 기회집합 로그와 조건식 변형은 후속 Phase이다.
4. WFO 실행 비용이 크므로 계속 opt-in으로 유지해야 한다.
5. 매우 짧은 기간에서는 WFO window가 없을 수 있으며, 이 경우 구조화된 실패로 처리해야 한다.

## 후속 후보

- 실제 CSV와 기존 전략으로 `--run-candidate --run-wfo` 파일럿 실행
- WFO 결과를 기존 discovery history에 저장하는 확장
- 조건식 임계값 완화/강화 후보 생성
- 기회집합 로그 설계
