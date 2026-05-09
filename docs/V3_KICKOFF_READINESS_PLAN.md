# STOM V3 진입 최종 검토 및 실행 준비 계획
## 2026-05-06 상태 주석

이 문서는 V3 branch/worktree 생성 직전의 역사적 readiness plan이다. 현재는 Phase 0~10이 완료되어 `STOM_Version_3` 공식 ingress와 `STOM_Version_3U` pyd-free 전환까지 끝났고, 남은 후속 단계는 Phase 11인 `STOM_Version_2U_C` V3 backport queue 시작이다. 현재 상태 판단은 `docs/update_log/2026-05-06_v3_v3u_final_handoff.md`, `docs/WORKTREE_STRATEGY.md`, `docs/CARRY_FORWARD_REGISTRY.md`를 우선한다.

## 문서 목적

이 문서는 V3 branch/worktree를 실제로 만들기 직전에 필요한 최종 검토 결과와 실행 준비 계획을 고정한다. `$deep-interview` 질문 UI가 정상 표시되지 않아, 사용자 선택에 따라 이미 수집한 저장소 증거와 작성된 문서를 기준으로 최종 검토를 수행했다.

이 문서는 다음 세 문서의 실행 준비판이다.

- `AGENTS.md`
- `docs/V3_UPDATE_OPERATING_SYSTEM.md`
- `docs/update_log/2026-05-04_v3_transition_strategy_review.md`

## 현재 결론

현재 상태는 **V3 실행 준비 kick-off 완료, 실제 branch/worktree 생성 직전 단계**다.

아직 실행하지 않은 작업:

- `STOM_Version_3` branch 생성
- `STOM_V.wt-3` worktree 생성
- V3 official update 반영
- `STOM_Version_3U` branch 생성
- `STOM_V.wt-3u` worktree 생성
- `_database` 복사
- V3U pyd 제거

이미 완료된 작업:

- V3 전환 전략 문서 작성
- V3 운영 문서 작성
- `AGENTS.md` V3 진입점 연결
- 6개 worktree 전략 문서화
- `_database` bootstrap 원칙 문서화
- 3U에서 2U pyd-to-py 추론 산출물을 참고/이식하는 원칙 문서화

## 현재 저장소 증거

### 현재 branch와 worktree

현재 `git worktree list --porcelain` 기준 worktree는 4개다.

| 경로 | branch | 현재 역할 |
| --- | --- | --- |
| `C:/System_Trading/STOM/STOM_V` | `STOM_Version_2` | V2 공식 기준선, 현재 작업 위치 |
| `C:/System_Trading/STOM/STOM_V.wt-2u` | `STOM_Version_2U` | V2 pyd-free 유지 lane |
| `C:/System_Trading/STOM/STOM_V.wt-dev` | `STOM_Version_2U_C` | Kiwoom 유지 custom/backport lane |
| `C:/System_Trading/STOM/STOM_V.wt-2uc` | `integration/adopt-cli-v267-into-2uc` | archive/transition lane |

전환 후 목표 worktree는 6개다.

| 경로 | branch | 목표 역할 |
| --- | --- | --- |
| `C:/System_Trading/STOM/STOM_V` | `STOM_Version_2` | V2 공식 유지 |
| `C:/System_Trading/STOM/STOM_V.wt-2u` | `STOM_Version_2U` | V2 pyd-free 유지 |
| `C:/System_Trading/STOM/STOM_V.wt-dev` | `STOM_Version_2U_C` | Kiwoom 유지 custom/backport |
| `C:/System_Trading/STOM/STOM_V.wt-3` | `STOM_Version_3` | V3 공식 ingress, 신규 생성 예정 |
| `C:/System_Trading/STOM/STOM_V.wt-3u` | `STOM_Version_3U` | V3 pyd-free, 신규 생성 예정 |
| `C:/System_Trading/STOM/STOM_V.wt-2uc` | archive branch | active lane 아님 |

### 최근 기준선 커밋

V3 진입 준비 기준선은 다음 커밋들에 의해 형성되었다.

```text
34cb6b2c V3 워크트리의 DB 부트스트랩과 2U 추론 재사용 원칙을 고정한다
5a00366d V3 킥오프 가이던스를 진입점에 연결한다
23924c8f V3 전환 전략 기준선을 문서화한다
067a462f 워크트리별 기준선과 2U_C 커스텀 원칙을 고정한다
```

### upstream V3 source 확인

2026-05-05 확인 기준:

```text
HEAD -> refs/heads/V3.00
refs/heads/V3.00 -> 19d2a49e9d6de9815e525e69844e4ac4a6459949
refs/tags/V2.0   -> 873d51eed3f581daa1925bcd9e3672254f525f0a
refs/tags/V3.0   -> d21e42425cfc6f2254431e8622b1bbf0dd89303e
```

주의:

- `refs/tags/V3.0`는 최신 V3 전체가 아니다.
- 실제 V3 반영 직전에는 `refs/heads/V3.00`을 다시 fetch해야 한다.
- `_update.txt`는 version boundary와 commit body 기준이고, 실제 file source는 upstream V3 tree다.

### runtime DB 상태

현재 `_database`는 local에 존재하지만 tracked file은 아니다.

- `.gitignore`에 `_database`, `_log`, `*.db`가 포함되어 있다.
- 따라서 새 worktree 생성만으로 `_database`는 자동 생성되지 않는다.
- V3/V3U worktree는 별도 runtime bootstrap이 필요하다.

### 현재 untracked 상태

현재 남아 있는 untracked 항목은 다음이다.

```text
.omc/
```

이 항목은 지금까지 모든 V3 문서 커밋에서 제외되었다. V3 branch/worktree 생성 전에 처리 방침을 정하는 것이 좋다.

## 부족한 부분 최종 검토

### 부족분 1. `WORKTREE_STRATEGY.md`는 아직 V3 전환기 지도를 반영하지 않음

현재 `docs/WORKTREE_STRATEGY.md`는 V2, 2U, 2U_C 기준의 active strategy를 설명한다. V3 문서는 별도로 존재하지만, worktree 전략 문서 자체에는 `STOM_V.wt-3`, `STOM_V.wt-3u`가 아직 반영되지 않았다.

판단:

- V3 branch/worktree 생성 전에는 반드시 수정해야 하는 blocker는 아니다.
- 다만 실제 `STOM_V.wt-3`, `STOM_V.wt-3u` 생성 직전 또는 직후에는 이 문서도 갱신하는 것이 좋다.

권장 조치:

```text
V3 worktree 생성 직전 또는 직후 docs/WORKTREE_STRATEGY.md에 “V3 transition worktrees” 섹션 추가
```

### 부족분 2. `CARRY_FORWARD_REGISTRY.md`에는 V3 backport allowlist 양식이 아직 통합되지 않음

2U_C에 V3 기능을 선별 backport하려면 source V3 version, 제외한 LS 의존성, Kiwoom 보정, DB 영향, 검증 결과를 기록해야 한다. 현재 V3 문서에는 양식이 있지만 carry-forward registry 자체에는 아직 template이 없다.

판단:

- V3 official branch 생성에는 blocker가 아니다.
- 2U_C에 V3 기능을 실제 backport하기 전에는 보강해야 한다.

권장 조치:

```text
V3 official 반영 이후, 2U_C backport 시작 전 docs/CARRY_FORWARD_REGISTRY.md에 V3 backport allowlist template 추가
```

### 부족분 3. `utility/upstream_sync_policy.py`와 `scripts/verify_release_sync.py`는 V2 chain만 알고 있음

현재 정책 스크립트의 propagation chain은 다음으로 고정되어 있다.

```text
STOM_Version_2 -> STOM_Version_2U -> STOM_Version_2U_C
```

판단:

- V2 release preflight에는 이 상태가 맞다.
- V3를 같은 스크립트에 바로 추가하면 V2 preflight 의미가 흐려질 수 있다.
- V3에는 별도 verification policy/script를 만들거나, 기존 script에 mode 옵션을 추가해야 한다.

권장 조치:

```text
V3 branch 생성 후 scripts/verify_v3_transition_ready.py 또는 verify_release_sync.py --profile v3 설계
```

초기에는 새 스크립트를 권장한다. V2 검증과 V3 검증을 섞지 않는 편이 안전하다.

### 부족분 4. `.omc/` 처리 방침 미정

현재 `.omc/`는 untracked로 남아 있다. formal 작업 전 preflight noise가 될 수 있다.

판단:

- V3 branch 생성 자체를 막지는 않는다.
- 그러나 clean status 판단을 어렵게 만든다.

권장 조치:

```text
.omc/가 runtime state라면 .gitignore에 추가
프로젝트 자산이면 별도 검토 후 추적 여부 결정
```

현 시점 추천은 `.gitignore`에 `.omc/`를 추가하는 것이다. 단, 커밋 전에 `.omc/` 내부가 source 자산이 아닌지 한 번 확인한다.

### 부족분 5. V3 official update를 version별로 실제 반영하는 절차가 아직 세분화되지 않음

문서에는 one version = one commit 원칙이 있지만, 실제 V3.0부터 V3.17까지 어떤 방식으로 file tree를 version별로 맞출지 세부 실행 절차는 아직 없다.

판단:

- 가장 큰 실무 리스크다.
- upstream commit history가 `_update.txt` section과 1:1로 대응하지 않을 수 있으므로, version별 file state를 재구성하는 절차가 필요하다.

권장 조치:

```text
V3 official branch 생성 후, upstream V3.00 history와 _update.txt marker를 대조하여 version slice strategy 작성
```

가능한 전략:

1. upstream commit history에서 `_update.txt` marker 변경 commit을 찾아 version boundary로 사용
2. 각 marker별 tree state를 `STOM_Version_3`에 한 commit씩 반영
3. marker와 commit history가 맞지 않으면 update section 기준 commit body를 유지하되 file 반영 단위는 upstream history evidence를 문서화

### 부족분 6. DB bootstrap은 문서화되었지만 실제 안전 복사 절차는 아직 명령화되지 않음

`_database` bootstrap 원칙은 문서화되었다. 하지만 실제 copy 명령, 백업 위치, 제외 파일, 민감 파일 검토 기준은 아직 명령 수준으로 고정되지 않았다.

판단:

- worktree 생성 직후 반드시 필요한 절차다.
- DB copy는 데이터 작업이므로 코드 commit과 분리해야 한다.

권장 조치:

```text
V3 worktree 생성 직후 DB bootstrap plan을 update log에 기록하고 수동/스크립트 중 하나로 실행
```

초기에는 수동 복사를 권장한다. 자동 스크립트는 DB 제외/민감 파일 기준이 정해진 뒤 만든다.

### 부족분 7. V3U pyd 제거 전 분석 checklist가 아직 별도 문서로 분리되지 않음

V3U는 `ui/main_window.pyd`를 대상으로 한다. 기존 2U는 `ui/ui_mainwindow.pyd` 기준이다. 검증 스크립트 일반화가 필요하다.

판단:

- V3U branch 생성 전에는 blocker가 아니다.
- V3U pyd 제거 착수 전에는 반드시 별도 checklist가 필요하다.

권장 조치:

```text
V3 official 반영 완료 후 docs/V3U_PYD_REMOVAL_PLAN.md 작성
```

포함할 내용:

- V3 pyd path
- 2U 참고 파일 목록
- wrapper mapping
- GUI smoke 항목
- manifest 항목
- allowed diff policy

## 최종 readiness 판단

### 지금 바로 가능한 작업

다음 작업은 바로 진행 가능하다.

1. `.omc/` 처리 방침 확정 또는 `.gitignore` 추가
2. upstream V3 ref 재확인
3. `STOM_Version_3` branch 생성
4. `STOM_V.wt-3` worktree 생성
5. `STOM_V.wt-3`에 `_database`/`_log` 디렉터리 생성
6. V3 official update 계획 세분화

### 아직 바로 하면 안 되는 작업

다음 작업은 선행 조건이 필요하다.

| 작업 | 선행 조건 |
| --- | --- |
| V3.0~V3.17 official 반영 | version slice strategy 작성 |
| `_database` 실제 복사 | 백업 위치와 제외 파일 기준 확인 |
| `STOM_Version_3U` 생성 | `STOM_Version_3` official 반영 안정화 |
| V3U pyd 제거 | V3U pyd removal plan 작성 |
| 2U_C V3 기능 backport | V3 official 반영 및 backport allowlist template 준비 |
| 3U_C 생성 | 현재 보류. V3/3U 안정화 후 별도 결정 |

## 전체 실행 계획

### Phase 0. 현재 기준선 고정 완료

완료된 기준:

```text
AGENTS.md
V3_UPDATE_OPERATING_SYSTEM.md
2026-05-04_v3_transition_strategy_review.md
```

완료 기준:

- V3 진입 문서 존재
- AGENTS 진입점 존재
- DB bootstrap 원칙 존재
- 2U 추론 산출물 재사용 원칙 존재

상태: 완료

### Phase 1. preflight noise 정리

목표:

- V3 branch/worktree 생성 전 status noise를 줄인다.

작업:

1. `.omc/` 내부 확인
2. runtime state이면 `.gitignore`에 `.omc/` 추가
3. status 확인

검증:

```powershell
git status --short --branch
git check-ignore -v .omc/project-memory.json
```

완료 조건:

- `.omc/`가 더 이상 untracked noise로 보이지 않거나, 명시적으로 ignore하지 않기로 결정된 상태

### Phase 2. upstream V3 source 재확인

목표:

- 실제 V3 작업 직전 source ref를 고정한다.

작업:

```powershell
git ls-remote --symref https://github.com/devstom/STOM.git HEAD refs/heads/V3.00 refs/tags/V3.0 refs/tags/V2.0
git fetch --no-tags https://github.com/devstom/STOM.git refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00_latest
```

검증:

```powershell
git rev-parse refs/remotes/devstom_tmp/V3.00_latest
git show refs/remotes/devstom_tmp/V3.00_latest:_update.txt | Select-Object -First 40
```

완료 조건:

- source commit hash 기록
- top marker 기록
- V3 marker 목록 기록

### Phase 3. `STOM_Version_3` branch와 `STOM_V.wt-3` 생성

목표:

- V3 official ingress worktree를 만든다.

작업 개념:

```powershell
git branch STOM_Version_3 STOM_Version_2
git worktree add C:/System_Trading/STOM/STOM_V.wt-3 STOM_Version_3
```

주의:

- 실제 명령 전 `STOM_V.wt-3` 경로가 없는지 확인한다.
- branch가 이미 존재하면 생성하지 않고 상태를 확인한다.

검증:

```powershell
git worktree list --porcelain
git -C C:/System_Trading/STOM/STOM_V.wt-3 branch --show-current
Test-Path C:/System_Trading/STOM/STOM_V.wt-3/docs/V3_UPDATE_OPERATING_SYSTEM.md
```

완료 조건:

- `STOM_V.wt-3`가 `STOM_Version_3`를 checkout
- V3 guidance 문서가 worktree에 존재

### Phase 4. V3 runtime DB bootstrap

목표:

- V3 worktree의 runtime directory를 준비한다.

작업 개념:

```powershell
New-Item -ItemType Directory -Force C:/System_Trading/STOM/STOM_V.wt-3/_database
New-Item -ItemType Directory -Force C:/System_Trading/STOM/STOM_V.wt-3/_log
```

DB 복사는 별도 확인 후 수행한다.

권장 절차:

1. `STOM_V/_database` 백업
2. 복사 대상 파일 목록 작성
3. 민감 가능 파일 확인
4. 필요한 DB seed만 복사
5. 복사 내역 update log 기록

완료 조건:

- `_database`와 `_log` 디렉터리 존재
- DB seed 복사 여부와 범위가 기록됨

### Phase 5. V3 official update slice strategy 작성

목표:

- V3.0~latest marker를 어떤 commit 단위로 반영할지 결정한다.

작업:

1. `_update.txt` V3 marker 목록 추출
2. upstream commit history에서 marker 변경 commit 확인
3. marker와 file tree state 대응표 작성
4. version별 반영 순서 확정

산출물 후보:

```text
docs/update_log/YYYY-MM-DD_v3_official_intake_plan.md
```

완료 조건:

- `STOM V3.0`부터 latest까지의 commit plan 존재
- 각 version source evidence 존재

### Phase 6. V3 official update 반영

목표:

- `STOM_Version_3`에 V3 official updates를 version별로 반영한다.

원칙:

```text
one official version = one commit
commit title = STOM V3.x
commit body = _update.txt 해당 section 전문
```

금지:

- pyd 제거 금지
- 2U_C custom 섞기 금지
- DB runtime data commit 금지

완료 조건:

- latest V3 marker까지 반영
- official pyd 보존
- source ref와 update section 기록

### Phase 7. `STOM_Version_3U` branch와 `STOM_V.wt-3u` 생성

전제:

- `STOM_Version_3` official 반영 안정화

작업 개념:

```powershell
git branch STOM_Version_3U STOM_Version_3
git worktree add C:/System_Trading/STOM/STOM_V.wt-3u STOM_Version_3U
```

검증:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3u branch --show-current
Test-Path C:/System_Trading/STOM/STOM_V.wt-3u/docs/V3_UPDATE_OPERATING_SYSTEM.md
```

완료 조건:

- `STOM_V.wt-3u`가 `STOM_Version_3U` checkout
- V3 guidance 문서 존재

### Phase 8. V3U runtime DB bootstrap

목표:

- 3U 검증을 3과 같은 DB seed 조건에서 수행한다.

작업 개념:

```powershell
New-Item -ItemType Directory -Force C:/System_Trading/STOM/STOM_V.wt-3u/_database
New-Item -ItemType Directory -Force C:/System_Trading/STOM/STOM_V.wt-3u/_log
```

DB seed:

```text
STOM_V.wt-3/_database -> STOM_V.wt-3u/_database
```

완료 조건:

- 3과 3U의 runtime seed 조건이 같음
- DB 복사 범위 기록

### Phase 9. V3U pyd removal plan 작성

목표:

- pyd 제거 전 mapping과 검증 기준을 고정한다.

산출물 후보:

```text
docs/V3U_PYD_REMOVAL_PLAN.md
```

포함 내용:

- V3 pyd path: `ui/main_window.pyd`
- V2 참고 path: `ui/ui_mainwindow.py`
- V3 UI 구조 mapping
- 2U 검증 도구 이식 계획
- allowed diff policy
- smoke/import/manifest 검증 기준

완료 조건:

- 3U pyd 제거 착수 전 checklist 존재

### Phase 10. V3U pyd 제거 실행

목표:

- `STOM_Version_3U`를 pyd-free로 만든다.

원칙:

```text
3U vs 3 차이는 pyd 제거와 대체 wrapper/inference/verification 차이로 제한
```

검증:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3u ls-files *.pyd
python -m py_compile ...
python scripts/smoke_offline_gui.py ...
python scripts/verify_pyd_gui_contract.py ...
```

검증 스크립트는 V3 경로에 맞게 일반화가 필요하다.

### Phase 11. 2U_C V3 backport queue 시작

전제:

- V3 official이 반영됨
- V3 기능 source가 명확함
- CARRY_FORWARD_REGISTRY 또는 update log에 backport template 준비

원칙:

- broker-neutral 기능부터
- LS API 전제는 제외
- DB 비호환 변경은 migration spec 전에는 제외
- source V3 version과 제외한 LS 의존성을 기록

완료 조건:

- 각 backport 항목별 기록과 검증 증거 존재

## 권장 stop line

현재 단계에서 권장 stop line은 다음이다.

```text
Phase 1~4까지는 바로 진행 가능
Phase 5부터는 V3 official update slicing 계획을 먼저 작성한 뒤 진행
```

즉, 다음 실제 실행은 다음 순서가 가장 안전하다.

1. `.omc/` ignore 처리
2. upstream V3 ref 재확인
3. `STOM_Version_3` branch 생성
4. `STOM_V.wt-3` worktree 생성
5. `_database`/`_log` 디렉터리 생성
6. DB 복사 전 백업/복사 범위 확인
7. V3 official intake plan 작성

## 최종 readiness 점수

| 영역 | 점수 | 판단 |
| --- | ---: | --- |
| 전략 방향 | 0.95 | 충분히 명확함 |
| branch/worktree 역할 | 0.90 | 문서화 완료, WORKTREE_STRATEGY 보강은 추후 필요 |
| V3 source ref | 0.85 | 현재 확인 완료, 실행 직전 재확인 필요 |
| DB bootstrap | 0.80 | 원칙 문서화 완료, 실제 복사 절차는 추가 확인 필요 |
| V3 official slicing | 0.55 | 가장 큰 미해결 영역 |
| V3U pyd removal | 0.65 | 방향은 명확하나 별도 plan 필요 |
| 2U_C backport policy | 0.75 | 원칙은 명확, registry template 추가 필요 |
| automation/verification | 0.60 | V2 script와 V3 script 분리가 필요 |

종합 판단:

```text
V3 branch/worktree 생성 준비는 가능하다.
V3 official update 대량 반영은 version slicing plan 작성 후 진행해야 한다.
V3U pyd 제거는 V3 official 안정화와 별도 pyd removal plan 이후 진행해야 한다.
```

## 직접 진행 가능 여부

직접 진행 가능하다. 단, 한 번에 V3 전체 반영까지 밀어붙이기보다 다음 handoff를 권장한다.

```text
다음 실행 단위:
1. .omc ignore 처리
2. upstream V3 ref 재확인
3. STOM_Version_3 branch 생성
4. STOM_V.wt-3 worktree 생성
5. _database/_log 디렉터리 생성
6. V3 official intake plan 작성
```

이 단위는 위험이 낮고, V3 진입을 실제로 시작했다는 기준점을 만들 수 있다.