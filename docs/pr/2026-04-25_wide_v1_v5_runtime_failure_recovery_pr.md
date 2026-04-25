# PR 보고서: Wide v1 v5 runtime failure recovery

## 1. 목적

Wide v1 v5 `candidate_count=10` 실제 실행이 runtime JSON 없이 정지한 문제를 해결하기 위해, `discovery research` 연구 루프에 복구 가능한 runtime output과 candidate checkpoint 정책을 추가했다.

## 2. 전체 방향

이번 작업은 v6 조건식 확장이 아니라 v5 실행 안정성 보강이다.

```text
v4 proxy row-set diversity
  -> v5 actual row-set validation
  -> runtime failure 확인
  -> runtime recovery 보강
  -> v5 재실행
  -> promote/WFO 판단
```

## 3. 현재 구현 범위

- `discovery research --runtime-output` 추가
- `--max-consecutive-candidate-failures` 추가
- candidate checkpoint 저장
- 개별 candidate 실패 후 다음 후보 계속 실행
- 연속 실패 3회 시 구조화된 중단
- 성공 후보 부족 시 actual row-set 선택 미실행
- runtime output write failure 구조화
- baseline, analysis, expression, retention 단계의 candidate 이전 실패 runtime 저장

## 4. 제외 범위

- `cli/runner.py` 대규모 multiprocessing cleanup 리팩토링
- GUI 변경
- v6 조건식 확장
- promote/WFO 실행
- 실제 v5 full rerun

## 5. 퀀트 트레이더 관점 검토

partial candidate CSV는 성과 검증 근거가 아니다. 이번 변경은 성공/실패 후보와 actual row-set 미실행 사유를 JSON으로 남겨, 불완전한 실험 결과가 promote/WFO 판단으로 넘어가지 않게 한다.

## 6. CLI 개발 전문가 관점 검토

stdout capture 의존을 줄이고 runtime output file을 명시적으로 저장한다. candidate 실패를 exception 흐름이 아니라 data item으로 보존해 장시간 실행을 진단 가능하게 만든다.

## 7. 전체 프로그램 관점 검토

STOM 백테스트 runner의 핵심 multiprocessing 구조를 이번 PR에서 크게 바꾸지 않는다. 연구 루프 레벨에 복구 계층을 추가해 회귀 위험을 제한한다.

## 8. 검증

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
cmd /c "git diff --check --ignore-cr-at-eol 2>&1"
```

## 9. 다음 단계

다음 추천 명령:

```text
$writing-plans Wide v1 v5 runtime recovery 적용 후 candidate_count=10 재실행 검증 계획 작성
```

