# Wide v1 연구 흐름과 CLI 구조 리뷰

## 1. 작성 목적

이 문서는 PR8 이후 진행된 조건식 연구 루프의 방향성을 한 번 정리하고, 현재 `cli/` 중심으로 개발 중인 연구 레이어가 메인 STOM 프로젝트와 어떻게 연결되는지 기록하기 위한 문서다.

최근 v1~v5 흐름이 길어지면서 다음 우려가 생겼다.

```text
- 새 조건식을 데이터 분석으로 생성하는 과정이 맞는가
- row set 같은 검증 개념 때문에 흐름이 과하게 복잡해진 것은 아닌가
- cli/ 파일이 많아졌는데 메인 프로젝트와 경계가 명확한가
- 지금 리팩토링을 해야 하는가, 아니면 v5 검증 후 해야 하는가
- 다음 superpower 명령이 여전히 맞는가
```

결론부터 말하면 현재 방향은 맞다. 다만 지금은 리팩토링보다 v5 실제 실행 검증이 먼저다. 이 문서는 그 판단 근거와 이후 정리 방향을 남긴다.

## 2. 전체 연구 루프의 기본 의도

사용자가 의도한 큰 흐름은 아래와 같다.

```text
백테스트 실행
  -> 결과 CSV 데이터 분석
  -> 새 조건식 후보 생성
  -> 후보 조건식으로 다시 백테스트
  -> 결과 평가
  -> 좋으면 다음 검증
  -> 부족하면 다시 개선
```

현재 `cli/` 연구 레이어도 이 흐름을 구현하고 있다. 다만 자동 개선 루프에서는 후보가 좋아 보이는 착시를 줄이기 위해 몇 가지 검증 gate가 추가됐다.

```text
- 거래 수가 너무 줄지 않았는가
- baseline과 비교할 때 신규/제외 거래가 과도하지 않은가
- 점수 기준선이 같은가
- 조건식은 달라도 실제 매수 거래 목록이 같은 후보는 아닌가
- promote/WFO 전에 실제 백테스트 결과로 후보 품질을 확인했는가
```

## 3. row set의 의미

이 프로젝트에서 row set은 백테스트 결과 CSV에서 실제로 매수된 거래 목록을 의미한다. 더 쉽게 말하면 “이 조건식이 실제로 잡은 거래 묶음”이다.

예시:

```text
조건식 A 실행 결과
- 삼성전자 09:00 매수
- 현대차 09:03 매수
- 카카오 09:07 매수

조건식 B 실행 결과
- 삼성전자 09:00 매수
- 현대차 09:03 매수
- 카카오 09:07 매수
```

조건식 A와 B의 문장이 달라도 실제 백테스트에서 같은 거래만 잡았다면, 독립적인 새 후보로 보기 어렵다. 따라서 v4/v5에서는 후보가 실제로 서로 다른 거래 기회를 만드는지 확인한다.

이 검증은 전략을 복잡하게 만들기 위한 것이 아니라, 새 조건식처럼 보이는 중복 후보를 걸러내기 위한 안전장치다.

## 4. PR8 이후 흐름

```text
PR8  세그먼트 기반 조건식 연구 루프 추가
  -> baseline CSV 분석, 후보 조건식 생성, 후보 전략 저장/실행의 기본 틀

PR9  discovery research WFO 검증 연결
  -> 후보 탐색 후 WFO까지 연결하는 방향 시도

PR10 discovery research에서 WFO 연결 제거
  -> WFO는 후보 품질이 확인된 뒤 별도 gate로 분리

PR11 후보 백테스트 런타임 안정화
  -> 후보 실행 실패, timeout, runtime artifact 처리 안정화

PR12 다중 후보 백테스트 연구 루프 v1
  -> 여러 후보 생성/실행/비교 구조 추가

PR13 거래 유지율 기반 후보 품질 개선
  -> baseline 거래를 과도하게 제거하는 후보를 걸러냄

PR14 넓은 틱 연구 기준 조건식 문서화
  -> Wide tick 연구 기준 조건식 고정

PR15~PR17 CLI/GUI/child runtime 정합성 보강
  -> CLI 백테스트가 GUI와 같은 계약으로 실행되도록 보강

PR18 Wide v1 baseline과 후보 5개 실행 검증
  -> CLI 연구 루프가 실제 Wide v1 후보를 실행할 수 있음을 확인

PR19 Wide v1 iteration loop v2
  -> best 후보를 seed로 반복 개선 후보를 생성

PR20 Wide v1 row-level 후보 차이 분석
  -> baseline/candidate의 공통/제외/신규 거래를 비교

PR21 Wide v1 score 기준선 비교 보강
  -> 서로 다른 기준 CSV 점수를 직접 비교하지 않도록 보강

PR22 Wide v1 v3 후보 생성 규칙 구현과 실행 결과 기록
  -> 후보 family와 candidate_count=10 실행으로 생성 폭 확대

PR23 Wide v1 v3 결과 분석 및 v4 여부 판단
  -> v3 결과가 바로 promote/WFO로 갈 수 없음을 판단

local merge e0cf5ea0
  -> v3 동률 후보 actual row-set 분석 병합

local merge 3b77a70e
  -> v4-v5 실제 행집합 선택 흐름 병합

local merge aa62edc3
  -> v5 병합 절차 문서 보정 병합
```

## 5. v1~v5 단계 의미

### v1 baseline

```text
목적:
- Wide v1 기준 조건식과 baseline 실행 결과를 고정
- CLI로 후보를 생성/실행할 수 있는지 확인

판단:
- 연구 루프의 출발점으로 적절하다.
```

### v2 반복 개선

```text
목적:
- best 후보를 seed로 다음 후보 조건식을 생성
- 단발성 후보 생성이 아니라 반복 개선 구조로 이동

판단:
- 방향은 맞다.
- 이때부터 과최적화 위험이 커지므로 이후 row-level/score baseline 검증이 필요했다.
```

### v3 후보 생성 확대

```text
목적:
- primary, secondary, trade amount 조건을 조합해 후보 family 확대
- candidate_count=10 실행

확인된 문제:
- 점수상 동률/유사 후보가 많았다.
- selected/executed family가 한쪽으로 치우쳤다.
- 조건식은 달라도 실제 거래 목록이 같은 후보일 가능성이 있었다.

판단:
- promote/WFO로 바로 가면 안 되고 tie-break와 actual row-set 검증이 필요했다.
```

### v4 proxy row-set 다양성

```text
목적:
- 실행 전에 baseline CSV 기준 proxy row-set 다양성을 계산
- 같은 proxy 거래집합 후보를 중복 선택하지 않음
- 후보 family 분산을 개선

확인된 문제:
- proxy는 예상치이므로 실제 backtest candidate CSV row-set과 완전히 같지 않았다.
- v4 candidate_count=10 실행에서 일부 actual row-set 중복이 남았다.

판단:
- v4는 필요한 개선이었지만 최종 gate로는 부족했다.
```

### v5 actual row-set 대표 선택

```text
목적:
- v4 후보를 요청 수보다 더 넓게 실행
- 실제 후보 CSV row-set을 분석
- 같은 actual row-set group에서는 rank 상위 대표 1개만 최종 후보로 선택

판단:
- 현재 구현된 v5 방향은 적절하다.
- 아직 실제 candidate_count=10 runtime 실행이 남아 있다.
```

## 6. 메인 프로젝트와 cli/ 연구 레이어의 관계

현재 작업은 메인 GUI/실거래 프로그램을 직접 바꾸는 작업이 아니라 `cli/` 중심의 연구 도구 개발이다.

```text
메인 STOM 프로젝트
  - GUI
  - 백테스트 엔진
  - 전략 DB
  - 실거래 런타임
  - 설정/텔레그램/키움 연동

cli 연구 레이어
  - 백테스트 엔진 호출
  - 결과 CSV 분석
  - 조건식 후보 생성
  - 후보 전략 임시 저장
  - 후보 백테스트 실행
  - baseline/candidate 비교
  - markdown/json 보고서 생성
```

핵심 원칙:

```text
cli는 연구/검증 도구다.
메인 프로젝트는 실행 엔진이다.
연구 단계에서는 메인 GUI, 실거래, serial-key, WFO promotion 경로를 불필요하게 건드리지 않는다.
```

## 7. 현재 cli/ 구조 리뷰

현재 주요 파일 역할은 아래와 같다.

```text
cli/research_loop.py
  - 전체 discovery research 실행 흐름
  - 현재 가장 큰 파일이며 리팩토링 후보 1순위

cli/research_metrics.py
  - 백테스트 CSV 지표 계산

cli/research_compare.py
  - baseline/candidate 거래 비교

cli/research_promotion.py
  - 후보 통과 점수 계산

cli/research_retention.py
  - 거래 유지율 기반 후보 선택

cli/research_iteration_v2.py
cli/research_iteration_v3.py
cli/research_iteration_v4.py
cli/research_iteration_v5.py
  - 각 반복 개선 버전별 후보 생성/선택 helper

cli/research_v3_decision.py
cli/research_v3_tiebreak.py
cli/research_v4_rowset.py
  - 실행 결과 분석 및 다음 단계 의사결정 helper

cli/research_report.py
  - markdown 보고서 생성

cli/subcommands.py
  - CLI parser와 command routing
```

파일이 많아진 이유는 실험 단계에서 각 버전의 판단과 helper를 분리했기 때문이다. 이는 현재 단계에서는 허용 가능하다. 다만 장기적으로는 구조 정리가 필요하다.

## 8. 리팩토링 후보

지금 당장 실행하지 않고 후보로만 기록한다.

```text
후보 1. cli/research_loop.py 분해
  - config validation
  - candidate pool construction
  - candidate execution
  - ranking/cleanup
  - result building

후보 2. iteration mode 이름 정리
  - 현재 iteration_v2_mode에 v3/v4/v5가 계속 들어간다.
  - 장기적으로는 research_iteration_mode 또는 candidate_generation_mode가 더 정확하다.

후보 3. runtime schema 타입화
  - dict 중심 구조를 TypedDict/dataclass로 일부 고정
  - basedpyright가 research_loop.py 전체를 통과하지 못하는 기존 타입 부채 완화

후보 4. 분석 스크립트 구조 통합
  - scripts/analyze_wide_v1_v3_*.py
  - scripts/analyze_wide_v1_v4_*.py
  - scripts/analyze_wide_v1_v5_*.py
  - 공통 read/write/report boilerplate 통합

후보 5. cli 하위 연구 패키지 분리
  - 예: cli/research/
  - 예: cli/research/iterations/
  - 예: cli/research/decisions/
  - 예: cli/research/reports/
```

## 9. 지금 리팩토링하지 않는 이유

현재는 v5 실제 실행 전이다. 이 시점에서 구조를 크게 바꾸면 다음 문제가 생긴다.

```text
- v5 결과가 나쁠 때 전략 문제인지 리팩토링 버그인지 구분하기 어렵다.
- v1~v5 비교 기준이 흔들릴 수 있다.
- 후보 생성/실행/평가 흐름을 다시 검증해야 한다.
- 최종 promote/WFO 판단이 더 늦어진다.
```

따라서 현재 전략은 다음이 맞다.

```text
1. v5 candidate_count=10 실제 실행
2. actual row-set 대표 후보가 충분한지 판단
3. 통과하면 promote/WFO 계획
4. 부족하면 v6 최소 보강
5. 이 분기 후 research_loop.py와 cli 구조 리팩토링 계획 작성
```

## 10. 다음 단계 판단

현재 다음 superpower 명령은 여전히 맞다.

```text
$writing-plans Wide v1 v5 candidate_count=10 실제 실행 및 actual row-set 검증 계획 작성
```

단, 이 명령은 반드시 새 feature branch에서 시작해야 한다.

```powershell
git switch STOM_Version_2U_C
git switch -c feature/wide-v1-v5-candidate-count-10-runtime-validation
```

그 다음 실제 실행 결과를 기준으로 분기한다.

```text
성공:
  actual_rowset_selection.status=ok
  row_set_identity_status=all_distinct
  selected_count >= requested_count
  -> promote/WFO 계획 작성

부족:
  selected_count < requested_count
  -> v6 후보 생성 확장 설계

실패:
  runtime status=error
  -> runtime failure recovery 설계
```

## 11. 결론

현재까지의 v1~v5는 “복잡한 전략을 만들기 위한 복잡화”가 아니라, 자동 조건식 개선 루프에서 나쁜 후보를 좋은 후보로 착각하지 않기 위한 gate 강화 과정이다.

다만 v5 이후에는 더 오래 머무르면 안 된다. v5 실제 실행 검증을 통해 promote/WFO로 넘어갈지, v6 최소 보강으로 갈지 결정해야 한다.
