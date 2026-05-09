# BP-008A commit message index 보정 기록

작성일: 2026-05-07 KST
대상 cycle: `2UC-V3-BP-008A`
목적: BP-008A 실행 중 일부 commit 제목이 PowerShell/CLI 인코딩 문제로 `??` 형태로 표시되어, rebase 없이 각 commit의 정확한 의미를 문서로 고정한다.

## 1. 보정 원칙

- `git rebase`와 history rewrite는 사용하지 않는다.
- 기존 commit hash는 그대로 유지한다.
- 후속 작업자는 아래 표의 “정상 제목/의미”를 기준으로 BP-008A 진행 단계를 해석한다.
- 이후 한글 commit message는 PowerShell here-string 대신 UTF-8 파일 기반 `git commit -F`로 작성한다.

## 2. root `STOM_Version_2` commit index

| hash | git log 표시 | 정상 제목/의미 |
|---|---|---|
| `1740ba8c` | `BP-008A Page 1 ?? ??? ????` | `BP-008A Page 1 후보 재감사 근거를 고정한다` |
| `0de8a7bc` | `BP-008A Page 2 ?? ??? ????` | `BP-008A Page 2 적용 범위를 확정한다` |
| `26be7c81` | `BP-008A Page 3 ?? ??? ?? ??? ???` | `BP-008A Page 3 적용 결과와 검증을 기록한다` |
| `29f382cd` | `BP-008A Page 4 ?? ??? ?????` | `BP-008A Page 4 문서 동기화를 완료한다` |
| `a323b64b` | `BP-008A Page 5 ?? ??? ?????` | `BP-008A Page 5 최종 검증을 통과시킨다` |

## 3. 2U_C `STOM_Version_2U_C` commit index

| hash | git log 표시 | 정상 제목/의미 |
|---|---|---|
| `7c904d38` | `BP-008A Page 1 ?? ??? 2U_C? ?????` | `BP-008A Page 1 문서를 2U_C에 동기화한다` |
| `e4227c3e` | `BP-008A Page 2 ??? 2U_C? ?????` | `BP-008A Page 2 문서를 2U_C에 동기화한다` |
| `6e4c10a0` | `BP-008A static timezone dependency? ????` | `BP-008A static timezone dependency를 표준 라이브러리로 보정한다` |
| `c7a41055` | `BP-008A Page 3 ?? ??? 2U_C? ?????` | `BP-008A Page 3 문서를 2U_C에 동기화한다` |
| `b2e48196` | `BP-008A Page 4 ??? ??? 2U_C? ???` | `BP-008A Page 4 문서 동기화를 2U_C에 반영한다` |
| `8251fd55` | `BP-008A Page 5 ?? ??? 2U_C? ?????` | `BP-008A Page 5 문서를 2U_C에 동기화한다` |

## 4. BP-008A 실제 완료 상태

```text
전체 진행률          [####################] 100.0%  72 / 72 page
BP-008A 진행률       [####################] 100.0%   5 /  5 page
남은 단계            [--------------------]   0.0%   0 /  0 page
```

실제 code 반영:

- 대상: `C:/System_Trading/STOM/STOM_V.wt-dev/utility/static.py`
- 변경: residual `pytz` timezone bootstrap을 Python 표준 라이브러리 `datetime.timezone.utc` + `zoneinfo.ZoneInfo` 기반으로 대체
- 제외: V3 `utility/static_method/` 구조 분리, telegram cleanup, requirements cleanup, LS API, DB migration, pyd/UI 변경

검증:

- `python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/utility/static.py`
- timezone equivalence mock
- root `verify_release_sync.py`
- 2U_C `verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev`
- forbidden runtime artifact guard
- `STOM_Version_3U_C` branch 부재 확인

## 5. 다음 단계 기준

BP-008A 이후 추가 탐색은 새 후보 ID로만 시작한다.

추천 OMX 검증 명령:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

다시 재탐색할 경우에는 `BP-008A` 완료 기준에서 다음 BP-ID를 열고 Page 1 read-only inventory부터 시작한다.
