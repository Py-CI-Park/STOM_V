# STOM V3 Update Operating System

## 문서 목적

이 문서는 STOM V3 진입을 시작하기 전에 모든 작업자가 반드시 공유해야 하는 공식 운영 기준이다. V3 전환은 단순 업데이트가 아니라 LS API 전환, UI pyd 위치 변경, trade 구조 재편, DB 전제 변경, 분석 시스템 확장까지 포함하는 별도 전환 프로젝트다.

이 문서는 다음 질문에 답한다.

- V3 작업을 시작하기 전에 어떤 문서를 읽어야 하는가?
- 새로 생성될 V3 worktree가 기존 전략을 어떻게 인지하게 할 것인가?
- `STOM_Version_3`, `STOM_Version_3U`, `STOM_Version_2U_C`의 책임을 어떻게 분리할 것인가?
- V3 진입 kick-off를 어떤 지점으로 볼 것인가?
- 실제 branch/worktree 생성 전에 어떤 gate를 통과해야 하는가?

## 현재 상태

- 기준일: 2026-05-05
- V3 진입 상태: 전략 kick-off 완료, 실행 전 준비 단계
- 직전 전략 기준선 커밋: `23924c8f V3 전환 전략 기준선을 문서화한다`
- 핵심 전략 문서: `docs/update_log/2026-05-04_v3_transition_strategy_review.md`
- 실행 준비 계획: `docs/V3_KICKOFF_READINESS_PLAN.md`
- 아직 수행하지 않은 작업:
  - `STOM_Version_3` branch 생성
  - `STOM_V.wt-3` worktree 생성
  - V3 공식 update 반영
  - `STOM_Version_3U` branch 생성
  - `STOM_V.wt-3u` worktree 생성
  - V3 pyd 제거

## V3 진입 kick-off 정의

이 저장소에서 V3 진입 kick-off는 다음을 의미한다.

```text
V3 실행 작업을 바로 시작했다는 뜻이 아니라,
V3 실행 전에 필요한 전략, 가이던스, worktree 역할, 금지 사항을 문서로 고정했다는 뜻이다.
```

따라서 kick-off 이후의 모든 V3 관련 작업은 이 문서와 전략 문서를 먼저 확인한 뒤 시작해야 한다.

V3 kick-off 기준선은 다음 두 문서가 존재하고 root `AGENTS.md`가 이 문서들을 참조하는 상태다.

```text
docs/V3_UPDATE_OPERATING_SYSTEM.md
docs/update_log/2026-05-04_v3_transition_strategy_review.md
AGENTS.md의 V3 Kick-off Entry Points 섹션
```

## 필수 진입 문서

V3 작업자는 다음 순서로 문서를 읽어야 한다.

1. `AGENTS.md`
2. `docs/V3_UPDATE_OPERATING_SYSTEM.md`
3. `docs/update_log/2026-05-04_v3_transition_strategy_review.md`
4. `docs/WORKTREE_STRATEGY.md`
5. `docs/CARRY_FORWARD_REGISTRY.md`
6. 필요한 경우 최신 V2/V3 update log

V2.79 공식 작업만 수행하는 경우 기존 V2 문서가 우선이다. V3 진입, 3U 생성, 2U_C에 V3 기능 backport를 수행하는 경우에는 이 문서가 추가 진입점이다.

## 가이던스 전파 원칙

새 worktree가 만들어졌는데 이 기준을 모르면 V3 작업 방향이 쉽게 틀어진다. 따라서 V3 worktree 생성 전에 다음 원칙을 지킨다.

### 1. 문서 포함 커밋에서 branch를 만든다

`STOM_Version_3`는 이 문서와 전략 문서가 포함된 기준선 이후에서 생성해야 한다. 그래야 새 worktree의 root에도 같은 guidance가 존재한다.

### 2. worktree 생성 후 root 문서를 확인한다

`STOM_V.wt-3` 또는 `STOM_V.wt-3u`를 만든 직후 다음을 확인한다.

```powershell
Get-Content AGENTS.md -TotalCount 120
Test-Path docs/V3_UPDATE_OPERATING_SYSTEM.md
Test-Path docs/update_log/2026-05-04_v3_transition_strategy_review.md
```

확인해야 할 내용:

- `AGENTS.md`에 V3 kick-off 진입점이 있는가?
- `docs/V3_UPDATE_OPERATING_SYSTEM.md`가 존재하는가?
- 전략 문서가 존재하는가?
- worktree가 기대 branch를 checkout하고 있는가?

### 3. 기존 downstream worktree에는 의도적으로 전파한다

새로 생성되는 V3 worktree는 기준선에서 branch를 만들면 문서를 자동으로 가진다. 그러나 기존 `STOM_V.wt-2u`, `STOM_V.wt-dev`는 이미 다른 branch다. 따라서 V3 backport를 수행하기 전에는 다음 중 하나를 선택해야 한다.

- 문서 커밋을 해당 branch에 전파한다.
- 또는 작업자가 root `STOM_V/`의 V3 문서를 명시적으로 읽고 backport 기록에 참조한다.

특히 `2U_C`에 V3 기능을 backport할 때는 이 문서의 backport 원칙을 반드시 따른다.

### 4. AGENTS.md는 짧은 진입점, docs는 상세 기준

`AGENTS.md`는 모든 agent가 자동으로 읽는 제어 표면이다. 따라서 여기에 모든 세부 전략을 길게 넣기보다, V3 작업의 필수 진입 문서와 금지 사항을 짧게 적고 상세 내용은 docs로 분리한다.

권장 구조:

```text
AGENTS.md
  - V3 작업 전 읽을 문서 목록
  - V3 worktree 역할 요약
  - V3 공식 lane과 U/C lane 금지 사항

docs/V3_UPDATE_OPERATING_SYSTEM.md
  - 실행 기준
  - kick-off gate
  - 가이던스 전파 규칙
  - worktree 생성 전 체크리스트

docs/update_log/2026-05-04_v3_transition_strategy_review.md
  - 전략 연구 상세본
  - 사용자 프롬프트와 의사결정 배경
```

## 전환기 worktree 지도

전환기 기준으로는 총 6개 worktree를 운영한다.

```text
C:/System_Trading/STOM/STOM_V          -> STOM_Version_2
C:/System_Trading/STOM/STOM_V.wt-2u    -> STOM_Version_2U
C:/System_Trading/STOM/STOM_V.wt-dev   -> STOM_Version_2U_C
C:/System_Trading/STOM/STOM_V.wt-3     -> STOM_Version_3
C:/System_Trading/STOM/STOM_V.wt-3u    -> STOM_Version_3U
C:/System_Trading/STOM/STOM_V.wt-2uc   -> integration archive
```

정확한 의미는 다음과 같다.

| worktree | branch | 역할 |
| --- | --- | --- |
| `STOM_V/` | `STOM_Version_2` | V2 공식 유지 lane |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | V2 pyd-free 유지 lane |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | Kiwoom 유지 custom/backport lane |
| `STOM_V.wt-3/` | `STOM_Version_3` | V3 공식 ingress lane |
| `STOM_V.wt-3u/` | `STOM_Version_3U` | V3 pyd-free 변환 lane |
| `STOM_V.wt-2uc/` | `integration/adopt-cli-v267-into-2uc` | archive/transition lane |

## branch 책임 규칙

### 공식 branch

공식 branch는 upstream 원본을 보존한다.

```text
STOM_Version_2 = V2 공식
STOM_Version_3 = V3 공식
```

공식 branch에서는 upstream `.pyd`를 제거하지 않는다.

### U branch

U branch는 pyd-free 변환 lane이다.

```text
STOM_Version_2U = V2 pyd-free
STOM_Version_3U = V3 pyd-free
```

U branch와 공식 branch의 차이는 pyd 제거와 그 대체 구현으로 제한한다.

### C branch

C branch는 custom lane이다.

```text
STOM_Version_2U_C = V2/Kiwoom 유지 custom lane
STOM_Version_3U_C = 아직 만들지 않음
```

`2U_C`는 V3 기능을 선별 backport할 수 있지만, V3 branch가 아니다.

## V3 source ref 원칙

V3 공식 source는 GitHub upstream이다.

```text
https://github.com/devstom/STOM.git
```

2026-05-05 확인 기준:

```text
HEAD -> refs/heads/V3.00
refs/heads/V3.00 -> 19d2a49e9d6de9815e525e69844e4ac4a6459949
refs/tags/V3.0   -> d21e42425cfc6f2254431e8622b1bbf0dd89303e
```

하지만 실제 실행 전에는 항상 다시 확인한다.

```powershell
git ls-remote --symref https://github.com/devstom/STOM.git HEAD refs/heads/V3.00 refs/tags/V3.0
```

`refs/tags/V3.0`는 최신 V3 전체가 아닐 수 있다. V3 정규 업데이트 source는 실행 시점의 upstream `refs/heads/V3.00`을 우선 확인한다.

## V3 정규 업데이트 규칙

`STOM_Version_3`에서는 다음 규칙을 적용한다.

1. one official version equals one commit
2. version 순서는 오름차순
3. commit title은 `STOM V3.0`, `STOM V3.01` 형식
4. commit body는 upstream `_update.txt`의 해당 section 전문
5. 공식 V3 branch에는 upstream pyd를 보존
6. pyd 제거는 `STOM_Version_3U`에서만 수행
7. custom 변경은 공식 V3 commit에 섞지 않음

## V3U pyd-free 규칙

V3 pyd 대상은 다음이다.

```text
ui/main_window.pyd
```

V2의 pyd 대상과 다르다.

```text
V2: ui/ui_mainwindow.pyd
V3: ui/main_window.pyd
```

따라서 V3U 검증 스크립트는 V2 전용 경로를 그대로 쓰지 말고 일반화해야 한다.

V3U 완료 기준:

- tracked `.pyd` 파일 없음
- V3 official non-pyd runtime file은 V3와 동일
- pyd 대체 Python entry 또는 wrapper 존재
- import/py_compile 통과
- offline GUI smoke 통과
- V3 GUI contract manifest 통과
- `3U vs V3` 차이가 pyd 제거 관련으로 제한됨

## 2U_C V3 backport 규칙

`STOM_Version_2U_C`는 Kiwoom 유지 custom lane이다. V3 기능을 가져오더라도 다음을 지킨다.

- LS API 전제를 그대로 가져오지 않는다.
- DB 비호환 변경은 migration spec 없이 반영하지 않는다.
- broker-neutral 기능부터 선별한다.
- source V3 version, source commit, 제외한 LS 의존성, Kiwoom 보정, 검증 결과를 기록한다.
- `2U_C`와 `2U`의 차이는 allowlist 또는 update log에 남긴다.

## V3 작업 시작 전 gate

V3 branch/worktree 생성 전에 다음 gate를 통과해야 한다.

- [ ] `AGENTS.md`가 V3 kick-off 문서를 참조함
- [ ] `docs/V3_UPDATE_OPERATING_SYSTEM.md` 존재
- [ ] `docs/update_log/2026-05-04_v3_transition_strategy_review.md` 존재
- [ ] upstream `refs/heads/V3.00` 최신 commit 확인
- [ ] `_update.txt` top marker 확인
- [ ] `STOM_Version_3` branch 생성 기준 commit 확인
- [ ] `STOM_V.wt-3` 경로 충돌 없음 확인
- [ ] `STOM_V.wt-3u` 경로 충돌 없음 확인
- [ ] `.omc/` 같은 untracked runtime state 처리 방침 확인
- [ ] `3U_C`는 아직 만들지 않는다는 결정을 재확인

## 금지 사항

- V3 official branch에 pyd 제거를 섞지 않는다.
- V3 official branch에 2U_C custom 변경을 섞지 않는다.
- 2U에 V3 기능을 직접 넣지 않는다.
- 2U_C에 LS API runtime을 검토 없이 넣지 않는다.
- DB 비호환 변경을 migration spec 없이 2U_C에 넣지 않는다.
- 3U_C를 조기 생성하지 않는다.
- `STOM_V.wt-2uc` archive lane을 active propagation lane으로 되살리지 않는다.
- V3 실행 전에 source ref 확인을 생략하지 않는다.

## 직접 진행 가능성

이 문서 기준으로 다음 작업은 직접 진행 가능하다.

1. V3 source ref 재확인
2. `STOM_Version_3` branch 생성
3. `STOM_V.wt-3` worktree 생성
4. V3 official update plan 작성
5. V3 official update를 version별로 반영
6. `STOM_Version_3U` branch 생성
7. `STOM_V.wt-3u` worktree 생성
8. V3U pyd-free 검증 체계 설계

다만 실제 V3 official update와 V3U pyd 제거는 변화량이 크므로 version별, gate별로 나누어 진행해야 한다.
## runtime DB bootstrap 원칙

Git worktree는 tracked file만 checkout한다. 현재 저장소의 `.gitignore`에는 `_database`, `_log`, `*.db`가 포함되어 있으므로, 새 worktree를 만들더라도 runtime DB 폴더와 DB 파일은 자동으로 생성되거나 복제되지 않는다.

따라서 `STOM_V.wt-3`와 `STOM_V.wt-3u`를 만들 때는 별도의 runtime bootstrap 단계를 둔다.

### `_database` 기본 원칙

- `_database`는 runtime seed/data이지 공식 release source가 아니다.
- `_database`와 `*.db` 파일은 커밋하지 않는다.
- V3 official code 반영과 DB 복사는 별도 단계로 분리한다.
- DB 복사 전에는 반드시 원본 `_database`를 백업하거나 snapshot한다.
- V3에는 DB primary key, 거래소별 설정 분리, strategy/trade table 분리 등 비호환 가능성이 있으므로 V2 DB는 “초기 seed”로만 취급한다.

### V3 worktree bootstrap

`STOM_V.wt-3` 생성 후에는 다음 순서로 runtime directory를 준비한다.

```text
1. STOM_V.wt-3 worktree 생성
2. STOM_V.wt-3/_database 디렉터리 생성
3. STOM_V.wt-3/_log 디렉터리 생성
4. 필요 시 V2 기준 STOM_V/_database 내용을 STOM_V.wt-3/_database로 복사
5. 복사한 DB는 V3 runtime 검증용 seed로만 사용
6. V3 DB 비호환 또는 재생성 요구가 있으면 V3 기준으로 별도 migration/초기화
```

중요한 점은 `STOM_Version_3` branch 자체는 V3 official source를 반영하는 branch이며, `_database` 복사는 worktree runtime 준비 단계라는 점이다.

### V3U worktree bootstrap

`STOM_V.wt-3u`는 `STOM_Version_3U` branch를 checkout하는 worktree다. 3U는 3을 기준으로 pyd-free 변환을 수행하므로 runtime DB도 가능하면 준비된 V3 worktree의 DB 상태를 기준으로 맞춘다.

권장 순서:

```text
1. STOM_Version_3 공식 반영과 V3 runtime seed 준비
2. STOM_Version_3에서 STOM_Version_3U 분기
3. STOM_V.wt-3u worktree 생성
4. STOM_V.wt-3u/_database 디렉터리 생성
5. STOM_V.wt-3/_database를 STOM_V.wt-3u/_database의 seed로 복사
6. 3U pyd-free 검증은 3과 같은 DB seed 조건에서 수행
```

이렇게 하면 `3U vs 3` 비교가 pyd 제거 차이에 집중될 수 있다.

### 2U_C DB와의 분리

`STOM_Version_2U_C`는 Kiwoom 유지 custom lane이다. V3 DB seed와 2U_C DB를 자동 동기화하지 않는다. V3 기능을 2U_C에 backport할 때 DB 변경이 필요하면 별도 migration spec, backup, dry-run, rollback 절차를 먼저 작성한다.

## 3U에서 2U pyd 추론 산출물을 활용하는 원칙

`STOM_Version_3U`의 branch base는 반드시 `STOM_Version_3`이다. 그러나 pyd 제거 구현을 새로 처음부터 작성할 필요는 없다. 기존 `STOM_Version_2U`에는 V2 pyd를 Python으로 추론하며 축적한 산출물과 검증 경험이 있으므로, 3U 작업에서는 이를 적극적으로 참고하고 필요한 부분을 이식한다.

### 허용되는 활용

- `STOM_Version_2U`의 pyd-derived MainWindow Python 구현을 V3 `ui/main_window.pyd` 분석의 참고 자료로 사용
- dialog show/close, position persistence, process wrapper, activated/clicked alias 보정 패턴 참고
- `scripts/smoke_offline_gui.py`, `scripts/verify_pyd_gui_contract.py`, `scripts/gui_contract_manifest.py`의 검증 개념 이식
- import/py_compile, tracked `.pyd` 없음 검증, GUI contract manifest 방식 재사용
- 2U에서 이미 해결한 pyd 추론 결함을 V3 구조에 맞게 재적용

### 금지되는 활용

- `STOM_Version_2U` 파일을 V3 파일 위에 무검토 overwrite
- V2 경로인 `ui/ui_mainwindow.py` 전제를 V3에 그대로 강제
- 2U_C custom 코드를 3U pyd-free 변환으로 위장
- Kiwoom 유지 custom logic을 3U에 섞음
- 3U와 3의 차이를 pyd 제거 범위 밖으로 확장

### 적용 방식

3U 구현 시 기준은 다음과 같다.

```text
branch ancestry: STOM_Version_3 -> STOM_Version_3U
implementation reference: STOM_Version_2U의 pyd 추론 산출물과 검증 도구
allowed diff: V3 pyd 제거와 대체 wrapper/inference/verification
```

즉, 3U는 “3에서 분기하되 2U의 pyd-free 경험을 이식하는 branch”로 운영한다.
