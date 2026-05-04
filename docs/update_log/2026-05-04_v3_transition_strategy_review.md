# 2026-05-04 V3 전환 전략 연구 및 운영 설계

## 문서 상태

이 문서는 STOM V2.79 반영 이후 V3 전환을 준비하기 위한 전략 연구 문서다. 기존 검토 문서에 한글이 물음표 문자로 저장된 문제가 있어, 같은 파일을 UTF-8 한글 문서로 다시 작성하면서 내용을 확장했다.

- 작성 기준일: 2026-05-04
- 보강 기준일: 2026-05-05
- 기준 저장소 위치: `C:/System_Trading/STOM/STOM_V`
- 문서 성격: 전략 검토, 운영 원칙, 향후 작업 기준선
- 이번 작업 범위: 문서 작성과 한글 깨짐 복구만 수행
- 이번 작업에서 하지 않은 것: 브랜치 생성, worktree 생성, V3 파일 반영, pyd 제거, 커밋 생성

## 이 문서의 목적

V3 전환은 단순한 버전 업데이트가 아니라 broker API, UI pyd 위치, trade 구조, strategy 구조, database 전제, 분석 시스템, dashboard 구성이 함께 바뀌는 큰 전환이다. 따라서 먼저 문서로 기준을 고정하지 않으면 이후 작업 중 다음 혼선이 발생할 수 있다.

- V3 공식 업데이트와 V2 유지보수의 경계가 섞임
- pyd 제거 차이와 custom 기능 차이가 섞임
- LS증권 API 전환 코드가 Kiwoom 유지판인 2U_C에 잘못 유입됨
- 3U가 V3의 pyd-free 변환 lane인지, V2U에서 이어진 혼합 lane인지 모호해짐
- V3 정규 업데이트의 source ref가 tag인지 branch인지 혼동됨
- worktree 수와 역할이 늘어나면서 작업 위치를 잘못 선택함

이 문서는 위 혼선을 막기 위해 다음을 명확히 한다.

1. V2 계열과 V3 계열의 branch 의미
2. 총 6개 worktree 운영안
3. `STOM_Version_3`와 `STOM_Version_3U` 생성 순서
4. `2U_C`에 V3 기능을 선별 backport할 때의 안전 기준
5. `3U_C`를 아직 만들지 않는 이유
6. V3 정규 업데이트를 `_update.txt` 기준으로 수행하는 규칙
7. 향후 실행 전 반드시 확인해야 할 검증 게이트

## 사용자 프롬프트 보존

향후 의사결정 추적과 검색을 위해 사용자의 질문과 아이디어를 원문으로 보존한다.

### 2026-05-04 현재 worktree 확인 질문

> 현재 개발 중인 워크트리가 2 2U 2U_C 맞나요?

### 2026-05-04 V3 전환 아이디어

> 이제 V3 를 위한 아이디어 협의를 하고 싶습니다. V2 에서 V3 으로 진행되면서 많은 부분이 업데이트 되고 키움 api 에서 ls api 로 변경되는 큰 변화가 있습니다. 그래서 Stom V 폴더에서 계속 관리하는 것은 아마 그대로 폴더 유지하고 Stom_Version_2 브랜치에서 STOM_Version_3 브랜치를 만들고 이제 v3의 정규 업데이트를 _update.txt 기준으로 업데이트 해야할것같습니다. 그리고 2U는 2 공식 업데이트의 문제였던 것이나 2 버전을 사용하는 단계에 발생하는 문제를 적용업데이트만 되면 될것 같습니다. 그래서 2U 의 최신에서 새로운 워크트리를 추가해서 3U 를 만들고 V3 의 pyd 제거 업데이틀르 진행 이어가면 될것 같습니다. 그리고 3U_는 아직 만들지 말고, 2U_C 를 계속 이어서 개발하는데,  v2 기능에 V3 에 ls 증권이 아닌 키움 증권을 유지하는 것에서 v3 의 새로운 기능 업데이트를 v3 정규 업데이트 적절하게 2U_C 에 반영하는 것을 일단 아이디어로 생각하고 있습니다. 이것이 가능한지 검토하고 좋은 방향인지 검토해주세요. 그리고 종합 보고서로 마크다운 문서로 검토 결과 남기고 싶습니다. 문서에는 제가 요청한 질문한 이 저의 아이디어 생각(프롬프트) 내용이 함께 정리되어서 추후에 찾을수있어야 합니다.

### 2026-05-05 전략 문서화 요청

> 위의 전략 아주 좋습니다. 그리고 이제 워크트리가 6개가 되는거라고 생각하면 되겠네요. 그리고 C:\System_Trading\STOM\STOM_V\docs\update_log\2026-05-04_v3_transition_strategy_review.md 파일의 물음표 두 개로 표시된 한글 깨짐 부분 수정이 필요하고 위의 추천 작업을 진행하기 전에 위의 연구를 문서화 시키면 좋을 것 같습니다. 아주 자세하게 추후 작업의 방향이 틀어지지 않도록 먼저 전략 문서로 생성하면 좋겠습니다. C:\System_Trading\STOM\STOM_V\docs\update_log\2026-05-04_v3_transition_strategy_review.md 문서에 포함이 되어있다면 더 상세하게 작성하는 방법도 좋아보입니다.

## 핵심 결론

### 최종 권장 전략

V3 전환은 다음 원칙으로 진행하는 것이 가장 안전하다.

```text
공식 branch는 upstream 원본을 보존한다.
U branch는 공식 branch에서 pyd를 제거한 변환 lane이다.
C branch는 custom lane이다.
```

이를 V2와 V3에 적용하면 다음이 된다.

```text
STOM_Version_2       = V2 공식 유지 lane
STOM_Version_2U      = V2 pyd-free 유지 lane
STOM_Version_2U_C    = V2 Kiwoom 유지 custom lane

STOM_Version_3       = V3 공식 업데이트 ingress lane
STOM_Version_3U      = V3 pyd-free 변환 lane
STOM_Version_3U_C    = 아직 만들지 않음
```

### 가장 중요한 조정 사항

사용자 아이디어의 큰 방향은 타당하다. 다만 `3U`의 기준점은 조정하는 것이 좋다.

사용자 아이디어:

```text
최신 2U에서 3U를 만들고 V3 pyd 제거 업데이트를 진행
```

권장 조정:

```text
먼저 STOM_Version_3를 공식 V3 lane으로 만든다.
그 다음 STOM_Version_3에서 STOM_Version_3U를 만든다.
2U는 branch base가 아니라 pyd 제거 노하우와 검증 도구의 이식 원천으로 사용한다.
```

이 조정이 필요한 이유는 `3U`의 의미를 다음처럼 선명하게 유지하기 위해서다.

```text
3U는 V3와 같아야 한다.
단, pyd 제거와 그 pyd 대체를 위한 wrapper, inference, verification 차이만 허용한다.
```

## 현재 확인된 근거

### 현재 local worktree 상태

2026-05-04와 2026-05-05 확인 기준 현재 local worktree는 다음과 같다.

| 경로 | branch | 현재 역할 |
| --- | --- | --- |
| `C:/System_Trading/STOM/STOM_V` | `STOM_Version_2` | V2 공식 release ingress |
| `C:/System_Trading/STOM/STOM_V.wt-2u` | `STOM_Version_2U` | V2 pyd-to-py 변환 lane |
| `C:/System_Trading/STOM/STOM_V.wt-dev` | `STOM_Version_2U_C` | 활성 2U_C custom 개발 lane |
| `C:/System_Trading/STOM/STOM_V.wt-2uc` | `integration/adopt-cli-v267-into-2uc` | archive, transition lane |

따라서 현재는 물리 worktree가 4개다. V3 전환 준비로 `wt-3`과 `wt-3u`를 추가하면 물리 worktree는 총 6개가 된다.

### upstream V3 확인 결과

2026-05-05 재확인 기준 upstream은 다음 상태였다.

```text
HEAD -> refs/heads/V3.00
refs/heads/V3.00 -> 19d2a49e9d6de9815e525e69844e4ac4a6459949
refs/tags/V2.0   -> 873d51eed3f581daa1925bcd9e3672254f525f0a
refs/tags/V3.0   -> d21e42425cfc6f2254431e8622b1bbf0dd89303e
```

`refs/remotes/devstom_tmp/V3.00_latest:_update.txt`의 top marker는 다음이다.

```text
2026-05-04 V3.17
```

`_update.txt`의 V3 marker 수는 18개이며, `V3.0`부터 `V3.17`까지 확인되었다.

중요한 점은 `refs/tags/V3.0`가 최신 V3 전체를 뜻하지 않는다는 점이다. 2026-05-05 기준 최신 확인 source는 upstream branch `refs/heads/V3.00`이다. 향후 실제 V3 작업 직전에는 반드시 다시 fetch하여 최신 ref와 top marker를 재확인해야 한다.

### V2 terminal tag와 V3 최신 branch의 변화 규모

`refs/remotes/devstom_tmp/tags/V2.0`과 `refs/remotes/devstom_tmp/V3.00_latest`의 비교 결과는 다음 규모다.

```text
428 files changed, 37930 insertions, 37782 deletions
```

이 수치는 V3가 단순 patch가 아니라 구조적 전환임을 보여준다.

### pyd 위치 변화

V2와 V3의 pyd 위치가 다르다.

| 구분 | pyd 위치 | 의미 |
| --- | --- | --- |
| V2 | `ui/ui_mainwindow.pyd` | 기존 V2 pyd GUI 중심 |
| V3 | `ui/main_window.pyd` | V3에서 이름과 구조가 바뀐 pyd GUI 중심 |

따라서 V2의 pyd 제거 스크립트와 검증 도구를 그대로 쓰면 안 된다. V3에서는 `ui/main_window.pyd`를 기준으로 새 contract를 정의하거나 기존 contract 스크립트를 일반화해야 한다.

### broker API 변화

V2 README의 핵심 broker 설명은 Kiwoom 중심이다.

```text
키움증권 국내주식, 해외선물, 업비트, 바이낸스선물 거래소의 API 연동
```

V3 README의 핵심 broker 설명은 LS 중심이다.

```text
LS증권 국내주식, ETF, ETN, 국내선물, 해외선물 및 업비트, 바이낸스선물 거래소의 API 연동
```

따라서 `2U_C`에 V3 기능을 backport할 때 가장 큰 위험은 LS 전용 runtime 전제가 Kiwoom 유지판에 섞이는 것이다.

## 6개 worktree 운영안

### 전환기 기준 6개 worktree

사용자 이해대로, 전환기에는 총 6개 worktree가 되는 것으로 생각하면 된다. 단, 6개가 모두 같은 성격의 활성 개발 lane은 아니다. 권장 구조는 active lane 5개와 archive lane 1개다.

```text
C:/System_Trading/STOM/STOM_V          -> STOM_Version_2
C:/System_Trading/STOM/STOM_V.wt-2u    -> STOM_Version_2U
C:/System_Trading/STOM/STOM_V.wt-dev   -> STOM_Version_2U_C
C:/System_Trading/STOM/STOM_V.wt-3     -> STOM_Version_3
C:/System_Trading/STOM/STOM_V.wt-3u    -> STOM_Version_3U
C:/System_Trading/STOM/STOM_V.wt-2uc   -> integration archive
```

### 각 worktree의 역할

| worktree | branch | 상태 | 역할 |
| --- | --- | --- | --- |
| `STOM_V/` | `STOM_Version_2` | 기존 유지 | V2 공식 기준선 유지, V2 관련 공식 보정 수용 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | 기존 유지 | V2 pyd-free 변환 유지, V2 pyd 관련 결함 보정 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | 기존 활성 | Kiwoom 유지 custom 개발, V3 기능 선별 backport |
| `STOM_V.wt-3/` | `STOM_Version_3` | 신규 예정 | V3 공식 업데이트 수용, upstream V3 pyd 보존 |
| `STOM_V.wt-3u/` | `STOM_Version_3U` | 신규 예정 | V3 pyd-free 변환, V3와 pyd 차이만 허용 |
| `STOM_V.wt-2uc/` | `integration/adopt-cli-v267-into-2uc` | archive | 과거 전환 기록 보존, 활성 propagation 대상 아님 |

### 왜 `STOM_V/`를 바로 V3로 바꾸지 않는가

사용자 아이디어처럼 장기적으로 `STOM_V/` 폴더를 계속 공식 관리 폴더로 유지하는 것은 좋다. 다만 전환기에는 V2 유지와 V3 전환이 잠시 병행될 수 있으므로, 처음부터 `STOM_V/`를 `STOM_Version_3`로 바꾸면 V2 공식 유지 위치가 사라진다.

따라서 권장 흐름은 다음이다.

1. 전환기에는 `STOM_V/`를 `STOM_Version_2`로 유지한다.
2. `STOM_V.wt-3/`에서 `STOM_Version_3`를 만든다.
3. `STOM_Version_3`가 최신 V3까지 안정적으로 반영되면 공식 ingress 위치 승격을 검토한다.
4. 승격 시점에는 `STOM_V/`를 `STOM_Version_3`로 전환하고, V2 유지가 필요하면 별도 `STOM_V.wt-2/`를 둘 수 있다.

초기 전환기와 장기 안정기 구조를 분리하면 작업 위치 혼동을 줄일 수 있다.

## branch 계층 전략

### V2 계열

```text
STOM_Version_2
  ↓
STOM_Version_2U
  ↓
STOM_Version_2U_C
```

V2 계열은 V2.79 이후에도 계속 유지한다. 다만 역할은 더 좁혀야 한다.

#### `STOM_Version_2`

- V2 공식 기준선이다.
- V2 terminal tag인 `V2.0` 기준 반영을 유지한다.
- 향후 V2 공식 보정이나 문서 정리 필요 시에만 최소 변경한다.
- V3 파일이나 V3 `_update.txt` section을 넣지 않는다.

#### `STOM_Version_2U`

- V2 pyd-free 기준선이다.
- V2와의 차이는 pyd 제거와 그 보정으로 제한한다.
- V3 신규 기능, LS API, V3 DB schema, dashboard를 넣지 않는다.
- V2 사용 단계에서 발생한 pyd wrapper, GUI, runtime 문제만 반영한다.

#### `STOM_Version_2U_C`

- V2U 기반 custom 개발 lane이다.
- Kiwoom 유지판이다.
- V3 기능은 선별 backport로만 반영한다.
- 모든 intentional runtime 차이는 carry-forward registry 또는 update log에 기록한다.
- LS 전용 구현을 그대로 받아들이지 않는다.

### V3 계열

```text
STOM_Version_3
  ↓
STOM_Version_3U
```

V3 계열은 V2 계열과 별도 공식 전환 프로젝트로 취급한다.

#### `STOM_Version_3`

- V3 공식 업데이트 ingress branch다.
- upstream V3 파일을 보존한다.
- V3 공식 pyd인 `ui/main_window.pyd`를 그대로 둔다.
- `_update.txt`의 V3 section을 version boundary로 사용한다.
- one official version equals one commit 원칙을 따른다.
- custom 수정이나 pyd 제거를 넣지 않는다.

#### `STOM_Version_3U`

- V3 pyd-free branch다.
- `STOM_Version_3`와 비교했을 때 허용 차이는 pyd 제거와 그 대체 구현뿐이다.
- V3 official non-pyd runtime file은 최대한 `STOM_Version_3`와 동일해야 한다.
- 기존 2U의 경험을 이식하되 V2 경로 하드코딩을 제거해야 한다.
- V3 smoke, import, GUI contract 검증이 준비되기 전에는 완료로 보지 않는다.

#### `STOM_Version_3U_C`

- 현재는 만들지 않는다.
- V3와 3U가 안정화된 뒤, V3 custom 요구가 충분히 명확해질 때만 별도 decision record를 작성하고 생성한다.
- 지금 만들면 `2U_C` backport와 V3 custom 개발의 경계가 모호해진다.

## 왜 3U는 2U가 아니라 V3에서 분기해야 하는가

### 2U에서 바로 3U를 만들 때의 장점

사용자 아이디어의 장점은 분명하다.

- 이미 pyd-free 상태다.
- V2 pyd 제거 경험이 축적되어 있다.
- 2U의 smoke와 contract 검증 개념을 이어가기 쉽다.
- `.pyd` 없는 branch를 시작점으로 삼을 수 있다.

### 2U에서 바로 3U를 만들 때의 위험

하지만 V3는 파일 구조가 크게 바뀌었다. 2U에서 바로 3U를 만들면 다음 문제가 생긴다.

```text
3U와 V3의 차이가 무엇을 의미하는지 불명확해진다.
```

차이의 원인이 다음 중 무엇인지 구분하기 어려워진다.

- pyd 제거 때문에 생긴 차이
- 2U에서 남아 있던 V2 구조 때문에 생긴 차이
- V3 대량 반영 중 충돌 해결로 생긴 차이
- Kiwoom 유지 목적의 의도적 차이
- 실수로 누락된 V3 official 변경

3U의 핵심 가치는 V3와의 비교 가능성이다. 2U를 기준으로 삼으면 그 비교 가능성이 약해진다.

### V3에서 3U를 만들 때의 장점

`STOM_Version_3`에서 `STOM_Version_3U`를 만들면 기준이 단순하다.

```text
3U vs V3
허용 차이 = pyd 제거 관련 차이
비허용 차이 = 공식 V3와 무관한 임의 변경
```

이 구조는 검증, review, rollback, 향후 V3 정규 업데이트 반영에 유리하다.

### 2U의 올바른 활용 방식

2U는 버리는 것이 아니라 다음 지식의 source로 사용한다.

- pyd 제거 절차
- inferred `.py` 정리 방식
- MainWindow wrapper 경계
- process wrapper 경계
- activated, clicked alias 보정 경험
- dialog show, close, position persistence 보정 경험
- offline GUI smoke 설계
- pyd contract manifest 설계
- import와 py_compile 검증 경험

즉, `2U`는 `3U`의 직접 부모라기보다 `3U` 작업의 기술 참고 모델이다.

## V3 정규 업데이트 원칙

### source ref 원칙

V3 공식 업데이트의 source는 GitHub upstream이다.

```text
https://github.com/devstom/STOM.git
```

2026-05-05 기준 최신 확인 ref는 다음이다.

```text
refs/heads/V3.00
```

중요한 규칙은 다음이다.

- `refs/tags/V3.0`는 존재하지만 최신 V3 전체가 아닐 수 있다.
- 실행 직전에는 반드시 `git ls-remote --symref`로 upstream HEAD와 V3 branch를 재확인한다.
- fetch한 source commit hash를 update log에 기록한다.
- `_update.txt` top marker와 반영 대상 marker 목록을 기록한다.

### commit 원칙

V3 공식 lane에서도 V2 formal update 원칙을 승계한다.

```text
one official version = one commit
```

예시:

```text
STOM V3.0
STOM V3.01
STOM V3.02
...
STOM V3.17
```

공식 release commit body는 `_update.txt`의 해당 section 전문을 사용한다. 이 원칙은 나중에 특정 V3 버전만 추적하거나 되돌릴 때 중요하다.

### 반영 순서

V3 section은 낮은 버전에서 높은 버전으로 반영한다.

```text
V3.0 -> V3.01 -> V3.02 -> ... -> latest V3 marker
```

중간 version을 건너뛰지 않는다.

### official lane 금지 사항

`STOM_Version_3`에는 다음을 넣지 않는다.

- pyd 제거
- inferred py 보정
- 2U_C custom 기능
- Kiwoom 유지용 backport 수정
- 검증 스크립트 보강을 공식 runtime 변경과 섞는 것
- V2 유지보수 변경

공식 lane은 upstream V3 reflection 역할을 유지해야 한다.

## V3U pyd 제거 전략

### V3 pyd 대상

V3의 pyd는 다음 파일이다.

```text
ui/main_window.pyd
```

이 파일은 V2의 `ui/ui_mainwindow.pyd`와 이름이 다르므로 기존 2U 스크립트는 그대로 사용할 수 없다.

### V3U의 목표 상태

`STOM_Version_3U`의 목표는 다음이다.

```text
tracked .pyd 파일이 없어야 한다.
V3 official non-pyd runtime file은 V3와 같아야 한다.
pyd 대체 구현은 V3 GUI 구조에 맞아야 한다.
```

### V3U에서 허용되는 차이

`STOM_Version_3U`와 `STOM_Version_3`의 차이는 다음 범위로 제한한다.

- `ui/main_window.pyd` 제거
- `ui/main_window.py` 또는 V3 구조에 맞는 대체 Python entry 추가
- pyd 내부 동작을 보완하는 wrapper
- pyd 대체를 위한 import boundary 수정
- pyd GUI contract 검증 스크립트
- smoke offline GUI 검증 스크립트
- pyd 제거와 직접 관련된 문서와 manifest

### V3U에서 피해야 할 차이

다음은 3U에 섞지 않는다.

- Kiwoom 유지 custom 수정
- V3 기능 선별 backport 판단
- LS API 제거 또는 대체
- 2U_C 전용 기능
- 임의 UI 개선
- DB migration 정책 변경
- dashboard custom 변경

이런 변경은 V3U가 아니라 별도의 custom lane 또는 backport queue에서 다뤄야 한다.

### 기존 2U 검증 도구 이식 시 수정해야 할 전제

기존 2U 검증 도구는 V2 경로를 전제한다.

| 항목 | V2 전제 | V3에서 필요한 조정 |
| --- | --- | --- |
| pyd 경로 | `ui/ui_mainwindow.pyd` | `ui/main_window.pyd` |
| inferred py 경로 | `ui/ui_mainwindow.py` | `ui/main_window.py` 또는 V3 wrapper 경로 |
| set 파일 | `ui/set_*.py` | `ui/create_widget/set_*.py` |
| activated 파일 | `ui/ui_activated_*` | `ui/event_activate/*` |
| clicked 파일 | `ui/ui_button_clicked_*` | `ui/event_click/*` |
| contract manifest | V2 GUI 요소 기준 | V3 GUI 요소 기준 재작성 |

V3U 작업 전에 검증 스크립트의 하드코딩 경로를 줄이고, branch별 pyd path를 인자로 받는 구조로 일반화하는 것이 좋다.

## 2U_C에 V3 기능을 backport하는 전략

### 2U_C의 정체성

`STOM_Version_2U_C`는 V3 branch가 아니다. 다음 성격으로 유지한다.

```text
V2 기반
pyd-free
Kiwoom 유지
custom 개발 lane
V3 기능은 선별 backport
```

따라서 V3 기능을 가져오더라도 공식 V3 추종이 아니라 Kiwoom 유지판에 맞춘 선별 이식이다.

### backport 기본 원칙

V3 기능을 2U_C에 반영할 때는 다음 원칙을 지킨다.

1. broker/API 독립성이 높은 기능부터 검토한다.
2. LS API 전제를 제거할 수 없는 기능은 제외하거나 별도 설계로 넘긴다.
3. DB 비호환 변경은 migration spec 없이 반영하지 않는다.
4. 기능마다 source V3 version과 관련 파일을 기록한다.
5. 제외한 LS 의존성과 Kiwoom 유지 보정 내용을 기록한다.
6. 반영 후 smoke, import, runtime 영향 검증을 수행한다.
7. carry-forward registry 또는 update log에 intentional diff로 남긴다.

### backport 후보 우선순위

#### 1순위: broker-neutral 기능

가져오기 쉬운 후보군이다.

- UI 편의 개선 중 broker API와 무관한 항목
- 차트 예외처리 통합
- 로그 정리
- 순수 계산 함수 최적화
- 전략 문법 테스트 분리 같은 구조 개선 중 broker 독립 항목
- 일부 backtest 계산 개선
- 분석 함수 중 API 의존이 낮은 순수 계산 부분

#### 2순위: 구조 의존이 있으나 분리 가능한 기능

주의해서 가져올 수 있는 후보군이다.

- 분석 시스템 일부
- 학습 데이터 저장과 로딩 중 독립 가능한 부분
- strategy 모듈 분리 중 순수 전략 helper
- backtest 엔진 공통 개선
- UI tab과 dialog 개선 중 trade runtime과 무관한 부분

#### 3순위: 원칙적으로 보류할 기능

Kiwoom 유지판에는 그대로 가져오면 위험한 후보군이다.

- `trade/restapi_ls.py`
- `trade/restapi_lsdata.py`
- LS TR, REAL 변경 대응
- LS 주문체결 데이터 타입 수정
- Kiwoom 파일 제거를 전제로 한 trade 구조
- 거래소별 설정 전면 분리
- 기존 DB 비호환 primary key migration
- LS 계좌, 주문, 체결 runtime 전제

### backport 기록 양식

2U_C에 V3 기능을 backport할 때는 다음 양식을 update log 또는 carry-forward registry에 남긴다.

```text
Backport ID:
Source V3 version:
Source upstream commit:
Source files:
Target branch:
목표 기능:
반영 범위:
제외한 LS 의존성:
Kiwoom 유지 보정:
DB 영향:
UI 영향:
검증 명령:
검증 결과:
남은 위험:
되돌리기 방법:
```

이 양식은 나중에 2U_C와 2U의 차이를 검토할 때 필수 기준이 된다.

## DB 변경에 대한 별도 주의

V3 `_update.txt`에는 DB primary key 추가, 거래소별 설정 분리, 전략과 거래 관련 table 분리 같은 내용이 들어 있다. 이 변경은 runtime 편의 개선이 아니라 사용자의 기존 DB와 직접 충돌할 수 있는 migration 성격이다.

따라서 DB 관련 V3 변경은 다음 원칙을 적용한다.

- `STOM_Version_3`에서는 upstream official 변경으로 그대로 보존한다.
- `STOM_Version_3U`에서는 V3 official과 동일하게 따라간다.
- `STOM_Version_2U_C`에는 별도 migration spec 없이는 반영하지 않는다.
- 기존 Kiwoom DB와 호환성 검토가 끝나기 전에는 2U_C backport 금지 항목으로 둔다.
- 실제 적용 시에는 backup, dry-run, rollback 절차가 먼저 필요하다.

## 작업 단계 제안

### Phase 0: 전략 문서 고정

현재 단계다.

목표:

- V3 전환 전략 문서 작성
- 6개 worktree 운영안 명확화
- V3 official, 3U, 2U_C backport의 경계 고정
- 한글 깨짐 수정

완료 기준:

- 이 문서가 UTF-8 한글로 정상 저장됨
- 물음표 두 개 형태의 깨진 문자열이 남지 않음
- 향후 작업자가 이 문서만 보고 branch 역할을 구분할 수 있음

### Phase 1: V3 운영 문서 초안 작성

권장 신규 문서:

```text
docs/V3_UPDATE_OPERATING_SYSTEM.md
```

또는 기존 공식 운영 문서에 V3 부록을 추가할 수 있다. 다만 V3는 독립 프로젝트 성격이 강하므로 별도 문서를 권장한다.

포함할 내용:

- V3 official source ref 정책
- V3 branch/worktree map
- V3 formal commit 규칙
- V3U pyd-free invariant
- 2U_C backport policy
- `3U_C` 생성 보류 조건
- V2 유지 정책

### Phase 2: V3 official branch와 worktree 준비

권장 작업 개념:

```text
STOM_Version_2에서 STOM_Version_3 branch 생성
STOM_V.wt-3 worktree 추가
upstream refs/heads/V3.00 fetch
V3.0부터 latest marker까지 one-version-one-commit 반영
```

주의:

- 이 단계에서는 pyd 제거를 하지 않는다.
- `ui/main_window.pyd`는 official V3 파일로 유지한다.
- V3 official commit에는 custom 수정이 섞이면 안 된다.

### Phase 3: V3U branch와 worktree 준비

권장 작업 개념:

```text
STOM_Version_3에서 STOM_Version_3U branch 생성
STOM_V.wt-3u worktree 추가
ui/main_window.pyd 제거와 inferred Python 대체 작업 시작
V3용 GUI contract와 smoke 검증 작성
```

주의:

- 2U에서 직접 분기하지 않는다.
- 2U의 코드는 참고와 이식 대상으로 사용한다.
- V3U의 non-pyd official runtime file은 V3와 같아야 한다.

### Phase 4: 2U_C V3 기능 backport queue 운영

권장 작업 개념:

```text
V3 기능 후보를 version별로 분류
broker-neutral 후보부터 2U_C에 선별 적용
각 항목마다 source, 제외한 LS 의존성, Kiwoom 보정, 검증 결과 기록
```

주의:

- backport는 공식 V3 정규 업데이트와 별도 흐름이다.
- 2U_C가 V3 branch처럼 변하면 안 된다.
- Kiwoom 유지가 2U_C의 핵심 가치다.

### Phase 5: STOM_V 폴더 승격 여부 결정

V3가 안정화되면 다음을 결정한다.

선택 A:

```text
STOM_V/를 계속 STOM_Version_2로 유지
STOM_V.wt-3/를 V3 official로 유지
```

선택 B:

```text
STOM_V/를 STOM_Version_3 official ingress로 승격
V2 official 유지가 필요하면 STOM_V.wt-2/를 별도로 생성
```

초기에는 선택 A가 안전하고, 장기적으로 V3가 주력이 되면 선택 B가 자연스럽다.

## 실행 전 체크리스트

실제 V3 branch와 worktree 생성 전에 다음을 확인한다.

- [ ] 현재 `STOM_Version_2`, `STOM_Version_2U`, `STOM_Version_2U_C` 상태가 의도한 기준선인지 확인
- [ ] `STOM_V/`에 untracked `.omc/` 같은 preflight 방해 요소 처리 방침 결정
- [ ] upstream `refs/heads/V3.00` 최신 commit hash 확인
- [ ] upstream `_update.txt` top marker 확인
- [ ] `refs/tags/V3.0`와 `refs/heads/V3.00`의 차이를 기록
- [ ] V3 반영 대상 version 목록 확정
- [ ] V3 official commit body 규칙 확정
- [ ] V3U pyd 대상 경로를 `ui/main_window.pyd`로 확정
- [ ] V3U 검증 스크립트 일반화 계획 확정
- [ ] 2U_C backport 기록 양식 확정
- [ ] `3U_C`는 생성하지 않는다는 decision을 명시

## 금지 사항

V3 전환 중 다음은 금지한다.

- V3 official commit에 pyd 제거를 섞음
- V3 official commit에 2U_C custom 기능을 섞음
- 2U에 V3 기능을 직접 반영함
- 2U_C에 LS API runtime을 검토 없이 반영함
- DB 비호환 변경을 migration spec 없이 2U_C에 반영함
- `3U_C`를 조기 생성함
- `STOM_V.wt-2uc` archive lane을 다시 active propagation lane으로 사용함
- `research/init`을 현재 V3 전환 chain에 자동 포함함
- V3 source ref를 확인하지 않고 과거 fetch 상태만 믿음

## 권장 의사결정 기록

향후 실제 작업에 들어가기 전에 다음 decision record를 남기는 것이 좋다.

### Decision 1: V3 공식 ingress 생성

```text
Decision: STOM_Version_3를 V3 official ingress branch로 생성한다.
Constraint: V3는 V2 대비 LS API, UI pyd, trade 구조, DB 전제가 크게 바뀐다.
Rejected: 기존 STOM_Version_2에 V3를 계속 누적한다 | V2 유지와 V3 전환 경계가 사라진다.
Rejected: 2U_C에 V3를 직접 흡수한다 | Kiwoom 유지판과 LS 전환판이 섞인다.
```

### Decision 2: 3U 생성 기준

```text
Decision: STOM_Version_3U는 STOM_Version_3에서 분기한다.
Constraint: 3U와 V3의 차이를 pyd 제거 차이로 제한해야 한다.
Rejected: STOM_Version_2U에서 3U를 직접 분기한다 | V2 잔여 구조와 V3 pyd 제거 차이가 섞인다.
```

### Decision 3: 2U_C의 역할

```text
Decision: STOM_Version_2U_C는 Kiwoom 유지 custom lane으로 남긴다.
Constraint: V3는 LS API 중심으로 전환되어 Kiwoom 유지판과 runtime 전제가 다르다.
Rejected: 2U_C를 V3 추종 branch로 바꾼다 | 기존 custom과 Kiwoom 유지 가치가 사라진다.
```

### Decision 4: 3U_C 보류

```text
Decision: STOM_Version_3U_C는 지금 만들지 않는다.
Constraint: V3 official과 V3U pyd-free 변환이 먼저 안정화되어야 한다.
Rejected: V3 시작과 동시에 3U_C를 만든다 | branch 수가 늘고 custom 경계가 모호해진다.
```

## 검증 전략

### 문서 검증

- UTF-8 한글 정상 저장 확인
- 물음표 두 개 형태의 깨진 문자열 없음 확인
- branch 역할 표와 worktree 표의 일관성 확인
- current upstream ref와 top marker 기록 확인

### V3 official 검증

- upstream source commit hash 기록
- `_update.txt` section 목록 확인
- one-version-one-commit 순서 확인
- official V3 pyd 존재 확인
- official runtime file이 upstream과 일치하는지 확인

### V3U 검증

- tracked `.pyd` 파일 없음 확인
- `ui/main_window.pyd` 대체 구현 존재 확인
- import와 py_compile 확인
- GUI smoke offline 확인
- V3 GUI contract manifest 확인
- `3U vs V3` diff가 pyd 제거 관련 차이로 제한되는지 확인

### 2U_C backport 검증

- source V3 version과 commit 기록
- LS 의존성 제거 또는 제외 기록
- Kiwoom runtime 영향 확인
- DB 영향 확인
- smoke 또는 unit 검증 기록
- carry-forward registry 또는 update log 기록

## 향후 작업자가 반드시 기억할 요약

1. 전환기 물리 worktree는 총 6개가 맞다.
2. 활성 canonical lane은 V2, 2U, 2U_C, V3, 3U이고, `wt-2uc`는 archive다.
3. V3 official은 upstream V3를 그대로 반영하고 pyd를 보존한다.
4. V3U는 V3에서 분기하고 pyd 제거만 담당한다.
5. 2U는 V2 유지보수와 pyd-free 보정만 담당한다.
6. 2U_C는 Kiwoom 유지 custom lane이며 V3 기능은 선별 backport만 허용한다.
7. 3U_C는 아직 만들지 않는다.
8. V3 source는 실행 직전 GitHub `refs/heads/V3.00`을 다시 확인한다.
9. `_update.txt`는 version boundary와 commit body 기준이며, 실제 파일 source는 upstream V3 tree다.
10. DB 비호환 변경과 LS API 변경은 2U_C에 섞지 않도록 특별 관리한다.

## 최종 판단

사용자의 전략은 전체 방향이 좋다. 특히 V3를 별도 공식 branch로 분리하고, V2 계열은 유지보수와 Kiwoom custom으로 남기며, 3U_C를 보류하는 판단은 장기 운영에 유리하다.

다만 가장 중요한 보정은 `3U`의 출발점이다. `3U`는 최신 2U에서 바로 만들기보다 `STOM_Version_3`를 먼저 만든 뒤 그 위에서 분기해야 한다. 이렇게 해야 `3U`의 의미가 V3 pyd-free 변환으로 고정되고, 이후 검증과 업데이트 전파가 단순해진다.

따라서 권장 최종 구조는 다음과 같다.

```text
V2 유지 계열:
STOM_Version_2 -> STOM_Version_2U -> STOM_Version_2U_C

V3 전환 계열:
STOM_Version_3 -> STOM_Version_3U

보류:
STOM_Version_3U_C
```

이 문서를 V3 전환의 기준 문서로 삼고, 다음 단계는 `docs/V3_UPDATE_OPERATING_SYSTEM.md` 또는 동등한 공식 운영 문서를 작성한 뒤 실제 branch와 worktree 생성을 진행하는 것이다.