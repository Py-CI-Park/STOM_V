# Wide v1 연구 흐름과 CLI 구조 리뷰 PR 보고서

## 1. 목적

이번 PR은 코드 동작을 바꾸지 않고, PR8 이후 이어진 조건식 연구 루프의 전체 방향성과 `cli/` 중심 개발 구조를 문서로 고정하기 위한 기록 PR이다.

최근 v1~v5 흐름이 길어지면서 다음 우려가 있었다.

```text
- 새 조건식 생성/백테스트/평가 루프가 원래 의도와 맞는가
- row set 검증 때문에 흐름이 과하게 복잡해진 것은 아닌가
- cli/ 파일이 많아졌는데 메인 프로젝트와 경계가 명확한가
- 지금 리팩토링을 먼저 해야 하는가
- v5 실제 실행 계획으로 넘어가는 것이 맞는가
```

이 PR은 위 질문에 대한 현재 판단을 문서화한다.

## 2. 전체 방향성

현재 연구 루프의 의도는 아래와 같다.

```text
백테스트 실행
  -> 결과 데이터 분석
  -> 새 조건식 후보 생성
  -> 후보 조건식으로 다시 백테스트
  -> 결과 평가
  -> 좋으면 promote/WFO 검증
  -> 부족하면 최소 보강 후 반복
```

지금까지의 v1~v5는 이 방향에서 벗어나지 않았다. 다만 자동 후보 생성에서 중복 후보와 과최적화 착시를 줄이기 위해 검증 gate가 늘어났다.

## 3. 현재 계획

이 PR의 범위:

```text
1. PR8 이후 전체 흐름 정리
2. v1~v5 단계별 의미 정리
3. row set 개념을 거래 목록 기준으로 설명
4. 메인 프로젝트와 cli 연구 레이어의 경계 정리
5. 현재 cli/ 구조 리뷰
6. 리팩토링 후보와 보류 이유 기록
7. 다음 단계가 v5 실제 실행 계획임을 확인
```

이 PR에서 하지 않은 일:

```text
- 코드 리팩토링
- cli/ 폴더 이동
- research_loop.py 분해
- runtime schema 전면 타입화
- v5 실제 백테스트 실행
```

## 4. 변경 파일

```text
docs/research/condition_research/2026-04-24_wide_v1_research_flow_and_cli_structure_review.md
docs/pr/2026-04-24_wide_v1_research_flow_and_cli_structure_review_pr.md
```

## 5. 검토 결과

### 퀀트 트레이더 관점

현재 방향은 적절하다. 단순히 수익 점수가 높은 후보를 고르는 것이 아니라, 후보가 실제로 다른 거래 기회를 만드는지 확인하고 있다. `row set`은 조건식의 실제 매수 거래 목록이며, 조건식 문장이 달라도 거래 목록이 같다면 독립 후보로 보기 어렵다.

따라서 v4/v5에서 actual row-set 검증을 붙인 것은 과최적화와 중복 후보 착시를 줄이는 보수적 개선이다.

### CLI 개발 관점

현재 개발은 `cli/` 중심 연구 레이어에 집중되어 있다. 메인 GUI, 실거래 런타임, serial-key, WFO promotion 경로는 불필요하게 건드리지 않았다.

이는 맞는 경계다.

```text
메인 프로젝트 = 실행 엔진
cli/ = 연구/분석/후보 생성/후보 검증 도구
```

### 전체 프로그램 관점

지금 바로 대규모 리팩토링을 하면 v5 실제 실행 결과를 해석하기 어려워진다. 따라서 리팩토링은 v5 실행 결과로 promote/WFO 또는 v6 최소 보강 분기를 판단한 뒤 진행하는 것이 맞다.

## 6. 리팩토링 후보

문서에 다음 후보를 기록했다.

```text
- research_loop.py 분해
- iteration_v2_mode 명칭 정리
- runtime schema 타입화
- 분석 스크립트 boilerplate 통합
- cli/research/ 하위 패키지 분리
```

다만 이번 PR에서는 실행하지 않았다. 현재 우선순위는 v5 실제 실행 검증이다.

## 7. 검증

문서 전용 변경이므로 코드 테스트 대신 문서와 git 상태 중심으로 검증한다.

```text
git diff --check --ignore-cr-at-eol
```

문서가 코드 동작을 바꾸지 않는 것도 확인한다.

## 8. 다음 단계

이 PR을 `STOM_Version_2U_C`에 merge한 뒤, 새 브랜치에서 다음 superpower 명령으로 진행한다.

```powershell
git switch STOM_Version_2U_C
git switch -c feature/wide-v1-v5-candidate-count-10-runtime-validation
```

```text
$writing-plans Wide v1 v5 candidate_count=10 실제 실행 및 actual row-set 검증 계획 작성
```

다음 단계의 판단 기준:

```text
성공:
  actual_rowset_selection.status=ok
  row_set_identity_status=all_distinct
  selected_count >= requested_count
  -> promote/WFO 계획

부족:
  selected_count < requested_count
  -> v6 최소 보강 설계

실패:
  runtime status=error
  -> runtime failure recovery 설계
```

## 9. 결론

현재 v1~v5 흐름은 원래 의도인 “백테스트 데이터 분석 기반 조건식 생성과 재평가”에 맞다. 복잡성은 전략 자체를 복잡하게 만들기 위한 것이 아니라, 자동 개선 루프에서 잘못된 후보를 걸러내기 위한 검증 비용이다.

따라서 지금은 구조 리팩토링보다 v5 실제 실행 검증으로 넘어가는 것이 맞다.
