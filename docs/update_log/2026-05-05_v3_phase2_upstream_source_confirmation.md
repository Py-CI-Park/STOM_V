# V3 Phase 2 upstream source 확인 기록

- 작성일: 2026-05-05
- 작성 시각: 2026-05-05 12:08:00 +09:00
- 작업 위치: `C:\System_Trading\STOM\STOM_V`
- 현재 브랜치: `STOM_Version_2`
- 관련 계획: `.omx/plans/prd-v3-kickoff-phase-0-11.md`
- 관련 검증: `.omx/plans/test-spec-v3-kickoff-phase-0-11.md`

## 1. 목적

이 문서는 V3 전환 실행 계획의 **Phase 2. upstream V3 source 재확인** 결과를 영구 기록하기 위한 문서이다.

Phase 3에서 `STOM_Version_3` 브랜치와 `STOM_V.wt-3` 워크트리를 생성하기 전에, 현재 시점의 공식 upstream ref를 다시 확인하고 다음 단계의 기준 commit을 고정한다.

## 2. 실행한 명령

```powershell
git ls-remote --symref https://github.com/devstom/STOM.git HEAD refs/heads/V3.00 refs/tags/V3.0 refs/tags/V2.0
git fetch --no-tags https://github.com/devstom/STOM.git refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00_latest
git fetch --no-tags https://github.com/devstom/STOM.git refs/tags/V3.0:refs/remotes/devstom_tmp/tags/V3.0
git fetch --no-tags https://github.com/devstom/STOM.git refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
git rev-parse refs/remotes/devstom_tmp/V3.00_latest
git show refs/remotes/devstom_tmp/V3.00_latest:_update.txt | Select-Object -First 80
```

## 3. 확인된 upstream ref

| 구분 | ref | commit | 확인 내용 |
| --- | --- | --- | --- |
| V3 최신 브랜치 | `refs/heads/V3.00` -> `refs/remotes/devstom_tmp/V3.00_latest` | `6904f454be1a24bb85f7911cfc3da10aa48deaf1` | `6904f454 거래소별 미지원 주문유형 선택 방지 코드 수정 - 해외주식의 경우 매수는 지정가, 매도는 지정가, 시장가만 지원함` |
| V3 최초 태그 | `refs/tags/V3.0` -> `refs/remotes/devstom_tmp/tags/V3.0` | `d21e42425cfc6f2254431e8622b1bbf0dd89303e` | `d21e4242 업비트 주문체결 웹소켓 오류 수정` |
| V2 기준 태그 | `refs/tags/V2.0` -> `refs/remotes/devstom_tmp/tags/V2.0` | `873d51eed3f581daa1925bcd9e3672254f525f0a` | `873d51ee 다른 종목 클릭 시 실시간차트 바로 업데이트 안되는 부분 수정` |

확인 결과, upstream `HEAD`는 `refs/heads/V3.00`를 가리킨다.

## 4. `_update.txt` 확인 결과

`refs/remotes/devstom_tmp/V3.00_latest:_update.txt` 파일을 확인했다.

- 파일 길이: 약 126,676자
- 라인 수: 약 4,706줄
- V3 섹션 수: 18개
- V3 섹션 범위: `2026-04-18 V3.0`부터 `2026-05-04 V3.17`까지
- 같은 파일 안에 V2 섹션도 존재한다.

확인된 V3 섹션은 다음과 같다.

```text
2026-05-04 V3.17
2026-05-03 V3.16
2026-05-01 V3.15
2026-04-30 V3.14
2026-04-29 V3.13
2026-04-28 V3.12
2026-04-27 V3.11
2026-04-26 V3.10
2026-04-25 V3.09
2026-04-23 V3.08
2026-04-23 V3.07
2026-04-22 V3.06
2026-04-22 V3.05
2026-04-21 V3.04
2026-04-20 V3.03
2026-04-20 V3.02
2026-04-19 V3.01
2026-04-18 V3.0
```

## 5. 판정

Phase 2는 통과로 판정한다.

근거:

1. upstream `HEAD`가 `refs/heads/V3.00`임을 확인했다.
2. V3 최신 브랜치 `refs/heads/V3.00`를 임시 ref `refs/remotes/devstom_tmp/V3.00_latest`로 고정했다.
3. V3 최초 태그 `refs/tags/V3.0`를 로컬 태그가 아닌 임시 ref로 고정했다.
4. V2 기준 태그 `refs/tags/V2.0`도 임시 ref로 확인했다.
5. `_update.txt`에 V3.0부터 V3.17까지 총 18개 V3 섹션이 존재함을 확인했다.

## 6. 다음 Phase 입력값

Phase 3에서 사용할 기준은 다음과 같다.

```text
V3 latest source branch: refs/remotes/devstom_tmp/V3.00_latest
V3 latest source commit: 6904f454be1a24bb85f7911cfc3da10aa48deaf1
V3 initial tag temp ref: refs/remotes/devstom_tmp/tags/V3.0
V3 initial tag commit: d21e42425cfc6f2254431e8622b1bbf0dd89303e
V2 base tag temp ref: refs/remotes/devstom_tmp/tags/V2.0
V2 base tag commit: 873d51eed3f581daa1925bcd9e3672254f525f0a
```

## 7. 다음 작업 방향

다음은 **Phase 3. `STOM_Version_3` branch와 `STOM_V.wt-3` 생성**이다.

권장 진행 순서:

1. 현재 로컬 branch/worktree 목록 확인
2. `STOM_Version_3` 브랜치가 이미 존재하는지 확인
3. `STOM_V.wt-3` 폴더가 이미 존재하는지 확인
4. 충돌이 없으면 `STOM_Version_2` 최신 commit에서 `STOM_Version_3` 브랜치 생성
5. `../STOM_V.wt-3`에 worktree 추가
6. worktree 내부에도 Phase 2에서 확인한 V3 source ref 정보를 참조할 수 있도록 문서 진입점을 확인

## 8. 주의사항

- 아직 V3 공식 업데이트 파일을 적용하지 않는다.
- 아직 `_database`를 복사하지 않는다. DB bootstrap은 Phase 4에서 별도 수행한다.
- 아직 V3.0~V3.17을 하나의 커밋으로 합치지 않는다. 공식 버전 단위 commit 원칙은 Phase 5에서 slicing plan을 먼저 확정한 뒤 적용한다.
- `V3.00_latest`는 upstream source 확인용 임시 ref이며, `STOM_Version_3` 브랜치 자체와 혼동하지 않는다.