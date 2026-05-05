# V3 Phase 4 runtime DB bootstrap 기록

- 작성일: 2026-05-05
- 작성 시각: 2026-05-05 16:34:44 +09:00
- 작업 위치: `C:\System_Trading\STOM\STOM_V`
- V3 워크트리: `C:\System_Trading\STOM\STOM_V.wt-3`
- 관련 계획: `.omx/plans/prd-v3-kickoff-phase-0-11.md`
- 관련 검증: `.omx/plans/test-spec-v3-kickoff-phase-0-11.md`

## 1. 목적

이 문서는 V3 전환 실행 계획의 **Phase 4. V3 runtime DB bootstrap** 결과를 기록한다.

Phase 4의 목표는 `STOM_Version_3` 공식 업데이트 lane인 `STOM_V.wt-3`에 runtime DB seed와 로그 디렉터리를 준비하되, DB/runtime 파일을 source commit에 포함하지 않는 것이다.

## 2. 실행 전 확인

다음 항목을 확인했다.

```powershell
Test-Path C:\System_Trading\STOM\STOM_V\_database
Test-Path C:\System_Trading\STOM\STOM_V.wt-3\_database
Test-Path C:\System_Trading\STOM\STOM_V.wt-3\_log
git -C C:\System_Trading\STOM\STOM_V.wt-3 check-ignore -v _database\setting.db
git -C C:\System_Trading\STOM\STOM_V.wt-3 check-ignore -v _log\placeholder.log
```

확인 결과:

- 원본 `_database`는 존재했다.
- 대상 `STOM_V.wt-3\_database`는 존재하지 않았다.
- 대상 `STOM_V.wt-3\_log`는 존재하지 않았다.
- `_database`와 `_log`는 `.gitignore` 규칙으로 ignore 처리되어 있었다.
- C 드라이브 여유 공간은 복사 대상보다 충분했다.

## 3. 복사 범위 결정

이번 Phase 4에서는 V3 official lane이 V2 기준 runtime seed와 같은 조건에서 시작하도록 **원본 `_database` 전체를 복사**했다.

복사 범위:

```text
source: C:\System_Trading\STOM\STOM_V\_database
target: C:\System_Trading\STOM\STOM_V.wt-3\_database
files: 1177
dirs: 1
bytes: 62899068972
size_gib: 58.58
```

`_log`는 과거 실행 로그를 복사하지 않고, V3 runtime용 빈 디렉터리만 생성했다.

```text
target_log: C:\System_Trading\STOM\STOM_V.wt-3\_log
files: 0
bytes: 0
```

## 4. 실행한 명령

대상 `_database`가 없음을 확인한 뒤 다음 방식으로 복사했다.

```powershell
New-Item -ItemType Directory -Path C:\System_Trading\STOM\STOM_V.wt-3\_log -Force
robocopy C:\System_Trading\STOM\STOM_V\_database C:\System_Trading\STOM\STOM_V.wt-3\_database /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /MT:16 /NFL /NDL /NP
```

`robocopy` 종료 코드는 `1`이었다. Windows `robocopy`에서 `1`은 복사할 파일이 있었고 성공적으로 복사되었음을 의미한다.

## 5. 검증 결과

복사 후 원본과 대상의 파일 수 및 총 바이트를 비교했다.

| 구분 | 파일 수 | 디렉터리 수 | 바이트 | GiB |
| --- | ---: | ---: | ---: | ---: |
| 원본 `_database` | 1177 | 1 | 62899068972 | 58.58 |
| 대상 `_database` | 1177 | 1 | 62899068972 | 58.58 |

검증 명령:

```powershell
Test-Path C:\System_Trading\STOM\STOM_V.wt-3\_database
Test-Path C:\System_Trading\STOM\STOM_V.wt-3\_log
git -C C:\System_Trading\STOM\STOM_V.wt-3 status --short --branch
git -C C:\System_Trading\STOM\STOM_V.wt-3 status --short --ignored --untracked-files=normal
git -C C:\System_Trading\STOM\STOM_V.wt-3 diff --cached --name-only
```

검증 결과:

- `STOM_V.wt-3\_database` 존재
- `STOM_V.wt-3\_log` 존재
- 대상 `_database` 파일 수와 총 바이트가 원본과 일치
- `git -C STOM_V.wt-3 status --short --branch`는 깨끗함
- ignored status에서 `_database/`가 ignored runtime data로만 표시됨
- staged runtime 파일 없음

## 6. 판정

Phase 4는 통과로 판정한다.

근거:

1. V3 워크트리에 `_database`와 `_log`가 모두 존재한다.
2. `_database` 복사 범위가 이 문서에 기록되었다.
3. 원본과 대상의 파일 수 및 총 바이트가 일치한다.
4. DB/runtime 파일은 git tracked/staged 변경으로 잡히지 않는다.
5. 기존 대상 DB를 덮어쓰지 않았다. 대상이 없을 때만 복사했다.

## 7. 다음 Phase 입력값

다음은 **Phase 5. V3 official update slice strategy 작성**이다.

Phase 5의 핵심 입력값:

```text
V3 latest source ref: refs/remotes/devstom_tmp/V3.00_latest
V3 update sections: V3.0 ~ V3.17, 18 sections
V3 worktree: C:\System_Trading\STOM\STOM_V.wt-3
V3 runtime DB seed: C:\System_Trading\STOM\STOM_V.wt-3\_database
V3 runtime log dir: C:\System_Trading\STOM\STOM_V.wt-3\_log
current STOM_Version_2 head: f0974285
current STOM_Version_3 head: f0974285
```

## 8. 주의사항

- `_database`와 `_log`는 runtime data이며 commit 대상이 아니다.
- V3 공식 업데이트 파일 적용은 아직 시작하지 않았다.
- Phase 5에서 V3.0~V3.17을 version 단위로 어떻게 자를지 먼저 문서화해야 한다.
- Phase 6 전까지는 V3.0~V3.17을 하나의 commit으로 합치지 않는다.