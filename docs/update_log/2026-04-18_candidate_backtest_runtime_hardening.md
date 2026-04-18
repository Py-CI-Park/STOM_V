# 2026-04-18 후보 백테스트 런타임 안정화

## 개요

`discovery research --run-candidate` 후보 백테스트가 timeout되거나 실패해도 연구 루프가 안전하게 복구되도록 실행 계획, 후보 전용 기간/timeout, 실패 후보 cleanup을 추가했다.

이번 변경은 후보 N개를 반복 실행하는 다음 Phase 전에 필요한 안전 장치다. 후보 1개가 실패해도 strategy.db에 잔여 후보가 남지 않고, 실패 원인이 JSON/Markdown 리포트에 남도록 했다.

## 변경 사항

- 후보 실행 계획 `candidate_plan` 추가
- `--candidate-start`, `--candidate-end` 추가
- `--candidate-timeout` 추가
- `--candidate-plan-only` 추가
- `--keep-failed-candidate` 추가
- 후보 백테스트 실패/timeout phase 구분
- 실패/timeout 후보 전략 기본 삭제
- 후보 CSV 누락과 비교 실패 시에도 cleanup 수행
- cleanup 실패가 원래 오류를 가리지 않도록 방어
- cleanup 결과를 JSON/Markdown 리포트에 포함

## 검증

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

결과:

```text
92 passed
```

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

결과:

```text
141 passed
```

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
938 passed, 1 skipped, 10 warnings
```

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 남은 리스크

- 후보 백테스트 자체가 여전히 느릴 수 있다.
- 너무 짧은 candidate 기간은 통계적으로 의미가 약할 수 있다.
- `--keep-failed-candidate`를 사용하면 실패 후보가 strategy.db에 남으므로 수동 정리가 필요할 수 있다.
- 다음 단계는 후보 N개 반복 실행과 최고 후보 선택이다.

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
