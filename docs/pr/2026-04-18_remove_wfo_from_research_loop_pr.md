# discovery research에서 WFO 연결 제거

## 목적

`discovery research`를 빠른 조건식 연구/개선 루프로 유지하기 위해 WFO 연결을 제거한다.

실제 파일럿에서 `discovery research --run-candidate --run-wfo`가 짧은 기간에서도 timeout되었고, 연구 초반 후보 생성/재백테스트 반복 속도와 맞지 않는다는 점이 확인되었다.

## 변경 요약

- `ResearchLoopConfig`에서 WFO 관련 필드를 제거했다.
- `research_loop.py`에서 WFO 실행/평가/결합 판단을 제거했다.
- `research_report.py`에서 WFO 검증/최종 판단 섹션을 제거했다.
- `discovery research` CLI에서 WFO 옵션과 param-space 옵션을 제거했다.
- WFO 관련 research 테스트를 제거하고, WFO 부재를 검증하는 테스트를 추가했다.
- 업데이트 로그를 추가했다.

## 유지되는 WFO 기능

이번 변경은 WFO 전체 삭제가 아니다.

유지:

- `cli/wfo.py`
- `AIBacktestController.walk_forward()`
- `AIBacktestController.evaluate_walk_forward_result()`
- `discovery promote`
- `auto_discovery` WFO 검증 구조

## 역할 분리

```text
discovery research:
빠른 조건식 연구/개선 루프

discovery promote:
무거운 WFO 최종 검증 루프
```

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
- 다음 개발은 백테스트 결과 분석, 후보 N개 생성, 후보별 백테스트, 최고 후보 선택을 반복하는 `Backtest Iteration Research Loop`이다.
