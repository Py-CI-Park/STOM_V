# 2026-04-17 discovery research WFO 연결 제거

## 개요

`discovery research`를 빠른 백테스트 반복 연구 루프로 유지하기 위해 WFO 연결을 제거했다.

실제 파일럿에서 `discovery research --run-candidate --run-wfo`가 짧은 기간에서도 10~15분 이상 소요되어 timeout되었다. 조건식 연구 초반에는 후보를 빠르게 만들고 재백테스트로 비교하는 흐름이 더 중요하므로, WFO는 `discovery promote`와 `cli.wfo`의 최종 검증 경로로 남긴다.

## 변경 사항

- `ResearchLoopConfig`에서 WFO 설정 필드 제거
- `research_loop.py`의 WFO 실행/평가/결합 판단 제거
- `research_report.py`의 `## WFO 검증`, `## 최종 판단` 섹션 제거
- `discovery research` CLI에서 WFO 옵션 제거
- research WFO 관련 테스트 제거 및 부재 검증 테스트 추가

## 유지되는 WFO 기능

- `cli/wfo.py`
- `AIBacktestController.walk_forward()`
- `AIBacktestController.evaluate_walk_forward_result()`
- `discovery promote`
- `auto_discovery` WFO 검증 구조

## 검증

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
75 passed
```

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

결과:

```text
124 passed
```

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
921 passed, 1 skipped, 10 warnings
```

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 남은 리스크

- `discovery research`는 더 이상 직접 WFO 검증을 하지 않는다.
- 최종 후보 검증은 `discovery promote` 또는 별도 WFO 경로로 수행해야 한다.
- 다음 개발은 백테스트 결과 분석, 후보 N개 생성, 후보별 재백테스트, 최고 후보 선택을 반복하는 `Backtest Iteration Research Loop`이다.

## 다음 단계

다음 브랜치 후보:

```text
feature/backtest-iteration-research-loop
```

목표:

```text
백테스트 결과 분석
-> 후보 N개 생성
-> 후보별 백테스트
-> 기준/후보 비교
-> 최고 후보 선택
-> 반복
```
