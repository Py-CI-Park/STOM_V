# V3 official update intake plan

- 작성일: 2026-05-05
- 작성 시각: 2026-05-05 16:42:48 +09:00
- 작업 위치: `C:\System_Trading\STOM\STOM_V`
- 대상 브랜치/워크트리: `STOM_Version_3` / `C:\System_Trading\STOM\STOM_V.wt-3`
- 관련 계획: `.omx/plans/prd-v3-kickoff-phase-0-11.md`
- 관련 검증: `.omx/plans/test-spec-v3-kickoff-phase-0-11.md`

## 1. 목적

이 문서는 V3 전환 실행 계획의 **Phase 5. V3 official update slice strategy 작성** 산출물이다.

Phase 6에서 `STOM_Version_3`에 V3 official update를 적용하기 전에, `_update.txt`의 V3 섹션, upstream source ref, marker별 evidence, commit sequencing, stop condition을 먼저 고정한다.

## 2. 실행한 확인 명령

```powershell
git ls-remote --symref https://github.com/devstom/STOM.git HEAD refs/heads/V3.00 refs/tags/V3.0 refs/tags/V2.0
git fetch --no-tags https://github.com/devstom/STOM.git refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00_latest refs/tags/V3.0:refs/remotes/devstom_tmp/tags/V3.0 refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
git show refs/remotes/devstom_tmp/V3.00_latest:_update.txt
git log --date=iso-strict --pretty=format:'%h%x09%H%x09%aI%x09%s' --reverse refs/remotes/devstom_tmp/tags/V3.0..refs/remotes/devstom_tmp/V3.00_latest
git diff --name-status refs/remotes/devstom_tmp/tags/V3.0 refs/remotes/devstom_tmp/V3.00_latest
```

## 3. upstream ref 재확인 결과

Phase 2에서 기록했던 `V3.00_latest`는 `6904f454be1a24bb85f7911cfc3da10aa48deaf1`였다.

Phase 5 시작 시 다시 fetch한 결과, upstream `refs/heads/V3.00`는 다음 commit으로 이동했다.

```text
latest: 9c8b3a166b1fce77691a022d9521cb7833cad0ad
latest summary: 9c8b3a16 2026-05-05T16:07:19+09:00 Merge pull request #33 from c-guevara/V3.00
```

따라서 Phase 5 이후의 모든 V3 slicing 판단은 `9c8b3a16` 기준으로 작성한다.

| 구분 | ref | commit |
| --- | --- | --- |
| V3 최신 source | `refs/remotes/devstom_tmp/V3.00_latest` | `9c8b3a166b1fce77691a022d9521cb7833cad0ad` |
| V3 최초 tag | `refs/remotes/devstom_tmp/tags/V3.0` | `d21e42425cfc6f2254431e8622b1bbf0dd89303e` |
| V2 기준 tag | `refs/remotes/devstom_tmp/tags/V2.0` | `873d51eed3f581daa1925bcd9e3672254f525f0a` |

## 4. `_update.txt` V3 marker 목록

최신 `_update.txt`의 V3 marker는 총 **18개**다.

실행 순서는 반드시 오래된 버전에서 최신 버전으로 진행한다.

| 실행 순서 | marker | formal commit title | commit body source |
| ---: | --- | --- | --- |
| 1 | `2026-04-18 V3.0` | `STOM V3.0` | `_update.txt`의 `2026-04-18 V3.0` section 전문 |
| 2 | `2026-04-19 V3.01` | `STOM V3.01` | `_update.txt`의 `2026-04-19 V3.01` section 전문 |
| 3 | `2026-04-20 V3.02` | `STOM V3.02` | `_update.txt`의 `2026-04-20 V3.02` section 전문 |
| 4 | `2026-04-20 V3.03` | `STOM V3.03` | `_update.txt`의 `2026-04-20 V3.03` section 전문 |
| 5 | `2026-04-21 V3.04` | `STOM V3.04` | `_update.txt`의 `2026-04-21 V3.04` section 전문 |
| 6 | `2026-04-22 V3.05` | `STOM V3.05` | `_update.txt`의 `2026-04-22 V3.05` section 전문 |
| 7 | `2026-04-22 V3.06` | `STOM V3.06` | `_update.txt`의 `2026-04-22 V3.06` section 전문 |
| 8 | `2026-04-23 V3.07` | `STOM V3.07` | `_update.txt`의 `2026-04-23 V3.07` section 전문 |
| 9 | `2026-04-23 V3.08` | `STOM V3.08` | `_update.txt`의 `2026-04-23 V3.08` section 전문 |
| 10 | `2026-04-25 V3.09` | `STOM V3.09` | `_update.txt`의 `2026-04-25 V3.09` section 전문 |
| 11 | `2026-04-26 V3.10` | `STOM V3.10` | `_update.txt`의 `2026-04-26 V3.10` section 전문 |
| 12 | `2026-04-27 V3.11` | `STOM V3.11` | `_update.txt`의 `2026-04-27 V3.11` section 전문 |
| 13 | `2026-04-28 V3.12` | `STOM V3.12` | `_update.txt`의 `2026-04-28 V3.12` section 전문 |
| 14 | `2026-04-29 V3.13` | `STOM V3.13` | `_update.txt`의 `2026-04-29 V3.13` section 전문 |
| 15 | `2026-04-30 V3.14` | `STOM V3.14` | `_update.txt`의 `2026-04-30 V3.14` section 전문 |
| 16 | `2026-05-01 V3.15` | `STOM V3.15` | `_update.txt`의 `2026-05-01 V3.15` section 전문 |
| 17 | `2026-05-03 V3.16` | `STOM V3.16` | `_update.txt`의 `2026-05-03 V3.16` section 전문 |
| 18 | `2026-05-04 V3.17` | `STOM V3.17` | `_update.txt`의 `2026-05-04 V3.17` section 전문 |

## 5. marker별 source evidence

아래 commit은 각 V3 marker가 upstream `_update.txt`에 처음 등장한 commit이다.

| marker | first-seen commit | date | subject |
| --- | --- | --- | --- |
| `2026-04-18 V3.0` | `f6cb505720252be14849bb9c962ec75d29852cf5` | 2026-04-18T11:40:40+09:00 | DB 업데이트 파일 일자 수정 |
| `2026-04-19 V3.01` | `632d455da5bc1016f40b1627db4961b8f654ca15` | 2026-04-19T12:12:42+09:00 | 파이썬 3.13 버전으로 업그레이드 누락된 라이브러리 목록 추가 |
| `2026-04-20 V3.02` | `f636ff073919655c1fb20af681425a2fb0a2ae3c` | 2026-04-20T07:43:29+09:00 | 업데이트 파일 갱신 |
| `2026-04-20 V3.03` | `0bd9120cc79eee414a21eb0a52748aea96c97eb5` | 2026-04-20T17:39:16+09:00 | 업데이트 파일 갱신 |
| `2026-04-21 V3.04` | `0d233a712806c7fd34295020f8f805871b12889d` | 2026-04-21T16:31:50+09:00 | 업데이트 파일 갱신 |
| `2026-04-22 V3.05` | `013e9887e67f1f84294135c5672b99ebdc2d2d38` | 2026-04-22T01:52:18+09:00 | 추가모듈, 전략연산, 백테엔진에 패턴분석 및 가격대분석 추가 |
| `2026-04-22 V3.06` | `68d742237e54ed445bb837ed11983b8cd5a02edc` | 2026-04-22T13:21:59+09:00 | 로그인 시작 시 로그탭으로 변경 후 리시버시작 완료되면 트레이딩탭으로 자동 변경되도록 수정 |
| `2026-04-23 V3.07` | `c968a7b09db593724a4452f349e274b6b3d6b3f3` | 2026-04-23T09:57:34+09:00 | 업데이트 파일 갱신 |
| `2026-04-23 V3.08` | `b10cb1f5ec37d296c30c15453e1bded3e6ce4880` | 2026-04-23T16:44:33+09:00 | 데이터베이스 PRIMARY KEY 삽입 및 거래소별 분리 |
| `2026-04-25 V3.09` | `928fda02fd51f0a0f5d334a0b9d27dd600ef0817` | 2026-04-25T22:25:10+09:00 | 업데이트 파일 갱신 |
| `2026-04-26 V3.10` | `6c4d1bc67b48b1dd67a27bbbb9b5bdf5b6b55076` | 2026-04-26T12:50:36+09:00 | 분석 설정을 포함하여 학습 데이터 저장하도록 변경 |
| `2026-04-27 V3.11` | `8bc2af7f5396319fceac6df0b3059abf7308ccc2` | 2026-04-27T13:40:47+09:00 | 업데이트 파일 갱신 |
| `2026-04-28 V3.12` | `5f55743d478e97661c91f7964c447589af16258f` | 2026-04-28T19:56:54+09:00 | 업데이트 파일 갱신 |
| `2026-04-29 V3.13` | `3c00b342808a0829f6bb03f921eac7c46bb0b331` | 2026-04-28T22:35:04+09:00 | 긴 파일명 짧게 변경 |
| `2026-04-30 V3.14` | `42c3f2a9a5c33c474721dbaae8a7943de977c37b` | 2026-04-30T12:26:56+09:00 | numba 함수 최적화 |
| `2026-05-01 V3.15` | `8bb9aa557f30d2e3e9ac49095d437fbd79a7f3a8` | 2026-05-01T15:30:50+09:00 | 변동성 변화 레별별 분류 방법 변경 - 0.5배 단위로 균등 분류 - 레벨수 설정 삭제 |
| `2026-05-03 V3.16` | `7c1e33b58135aadd643ec0f832db0ae94819ac61` | 2026-05-03T21:45:00+09:00 | 업데이트 파일 갱신 |
| `2026-05-04 V3.17` | `01e6c0a6e1d8598f9a159ac97fc94c383e8a141f` | 2026-05-04T17:06:55+09:00 | 업데이트 파일 갱신 |

## 6. source diff 규모

`refs/remotes/devstom_tmp/tags/V3.0`부터 `refs/remotes/devstom_tmp/V3.00_latest`까지의 name-status 요약은 다음과 같다.

```text
A: 19
D: 6
M: 124
R055/R075/R076/R086/R095/R099: 각 1
```

상위 경로 기준 주요 변경 규모:

```text
ui: 62
trade: 28
backtest: 24
utility: 24
strategy: 10
README.md: 1
_update.txt: 1
dashboard: 1
stom.py: 1
```

따라서 Phase 6은 단순한 수동 patch가 아니라 version gate가 필요한 official source intake 작업으로 취급한다.

## 7. Phase 6 commit sequencing 원칙

Phase 6에서는 다음 원칙을 따른다.

1. **one official version = one commit**
2. commit title은 `STOM V3.x` 형식으로 작성한다.
3. commit body는 최신 `_update.txt`에서 해당 marker section 전문을 추출해 그대로 사용한다.
4. version 순서는 반드시 `V3.0 -> V3.01 -> ... -> V3.17` ascending order로 진행한다.
5. upstream `.pyd`는 공식 V3 lane에서 보존한다.
6. `3U` pyd-free 변경, `2U_C` Kiwoom 유지 backport, custom 개발 변경은 Phase 6 commit에 섞지 않는다.
7. `_database`, `_log`, `*.db`, runtime data는 stage하지 않는다.
8. `backtest/graph/`는 release input으로 취급하지 않는다.

## 8. Phase 6 적용 방식 권고

V3 upstream history는 merge commit과 post-marker commit이 섞여 있으므로, 개별 upstream commit을 무작정 cherry-pick하는 방식은 비추천한다.

권장 방식은 다음과 같다.

1. Phase 6 시작 직전에 upstream ref를 다시 fetch한다.
2. `_update.txt` top marker와 marker count를 다시 계산한다.
3. 새 V3 marker가 생겼으면 이 문서를 갱신한 뒤 진행한다.
4. 각 version별 commit body section을 먼저 파일로 추출한다.
5. version별 source file 적용은 dry-run으로 변경 파일 목록을 먼저 생성한다.
6. protected governance files는 보존한다.
7. 실제 stage는 `git add <정확한 파일 목록>` 방식만 사용한다. `git add -A`는 금지한다.
8. 각 version commit 직후 다음 검증을 실행한다.

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3 status --short --branch
git -C C:/System_Trading/STOM/STOM_V.wt-3 ls-files *.pyd
git -C C:/System_Trading/STOM/STOM_V.wt-3 diff --cached --name-only | Select-String -Pattern '^_database/|^_log/|\.db$'
```

## 9. 보호해야 할 로컬 governance/runtime 영역

Phase 6 source intake 중 다음은 공식 runtime source와 분리해서 보호한다.

| 영역 | 정책 |
| --- | --- |
| `.git/`, `.omx/`, `.omc/` | runtime/orchestration state, source intake 제외 |
| `_database/`, `_log/`, `*.db` | runtime data, stage 금지 |
| `docs/update_log/*v3_*strategy*`, `docs/update_log/*phase*`, `docs/V3_*`, `AGENTS.md` | 전환 운영 문서, upstream official source overlay로 삭제 금지 |
| `STOM_V.wt-3/_database`, `STOM_V.wt-3/_log` | Phase 4에서 준비한 runtime seed, commit 금지 |

## 10. 감지된 ambiguity / stop line

Phase 5 재확인에서 upstream `V3.00`가 Phase 2 이후 이동했다.

`6904f454` 이후 최신 `9c8b3a16`까지의 diff는 다음과 같다.

```text
M	strategy/manager_formula.py
M	trade/restapi_binance.py
M	trade/restapi_ls.py
M	utility/_pycharm/Project_Default.xml
```

현재 `_update.txt` top marker는 여전히 `2026-05-04 V3.17`이다.

따라서 Phase 6 시작 전 다음 조건을 반드시 확인해야 한다.

- upstream latest가 다시 바뀌었는가?
- top marker가 `V3.18` 이상으로 증가했는가?
- `6904f454` 이후 변경을 `STOM V3.17`에 포함할 것인지, 또는 새 marker를 기다릴 것인지?

이 판단이 확정되지 않으면 Phase 6에서 최신 snapshot을 그대로 overlay하지 않는다.

## 11. Phase 6 진입 조건

Phase 6 진입 전 필수 조건:

- 이 문서가 최신 upstream ref와 일치한다.
- V3 marker list가 최신 `_update.txt`와 일치한다.
- `STOM_V.wt-3` status가 깨끗하다. ignored `_database/`만 허용한다.
- V3 official source 적용 대상과 protected governance file 목록이 dry-run으로 확인되어 있다.
- 첫 formal commit `STOM V3.0`의 commit body section이 정확히 추출되어 있다.

## 12. 판정

Phase 5는 통과로 판정한다.

근거:

1. V3 marker list 18개를 확인했다.
2. source ref와 commit hash를 기록했다.
3. marker별 first-seen evidence를 기록했다.
4. version-by-version formal commit plan을 작성했다.
5. ambiguous mapping과 upstream 변경 위험을 stop line으로 문서화했다.