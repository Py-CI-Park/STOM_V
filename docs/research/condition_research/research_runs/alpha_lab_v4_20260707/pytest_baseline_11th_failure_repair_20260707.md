# pytest 전체 스위트 11번째 실패 — 근본원인·알파 무관성 확정 (2026-07-07 수복)

> **수복 대상 지적**: 알파 랩 v4 검증 라운드 실측 `python -m pytest tests/unit -q`(469s) → `11 failed, 4493 passed, 20 skipped`. 기존 기준선(`../alpha_lab_20260705/baseline_test_failures_20260705.md` + `../alpha_lab_20260705/baseline_failures_rootcause_addendum_20260706.md`)이 확정한 10건과 노드 ID 10개는 완전 일치하나, 11번째 실패 `tests/unit/dashboard/test_backtest_jobs.py::test_cancel_kills_child_tree_and_releases_queue`는 두 기준선 문서 어디에도 없고 저장소 전체에서도 사전 문서화 흔적이 없었다(grep 0건). 격리 재실행 5회(단독 1회+파일단위 1회+단독 3회) 결과 3 fail / 2 pass로 비결정적(flaky) — "기준선 10건 1:1 대조"라는 문서상의 전제가 문자 그대로는 성립하지 않는다는 지적.
>
> **결론(본 수복 문서)**: 독립 재검증으로 위 관측을 재확인하고 근본원인을 파일·라인 단위로 확정했다. 11번째 실패는 **알파 랩이 손대지 않은 사전 존재 플레이키(비결정적) 통합 테스트**이며, 원인 파일·테스트 파일 모두 알파 착수 커밋(`70775539`) 시점과 바이트 동일함을 구성적으로 증명했다(§3). 알파 스코프(`-k test_alpha`)는 본 수복 라운드 재실측에서도 완전 green(505 passed, 0 failed, 4019 deselected, 40.65s) — 원 지적의 수치와 정확히 일치한다. "기준선 10건 1:1 대조"라는 표현을 **"기준선 10건 확정(불변) + 신규 관측 플레이키 1건(비-알파, 비결정적, 아웃오브스코프)"**으로 정정하며, 알파 게이트 판정("알파 스코프 전수 green + 기준선 문서화 면제")에는 영향이 없다.

## 1. 배경 — 지적 내용 원문 요약

| 항목 | 값 |
|---|---|
| 전체 스위트 실측(검증 라운드) | `11 failed, 4493 passed, 20 skipped in 469s` |
| 기준선 10건과의 대조 | 10건 노드 ID 완전 일치 |
| 미문서화 11번째 실패 | `tests/unit/dashboard/test_backtest_jobs.py::test_cancel_kills_child_tree_and_releases_queue` |
| 기준선 문서 내 검색 | 0건(두 문서 모두) |
| 격리 재실행(검증 라운드, 5회) | 3 fail / 2 pass — 비결정적 |
| 알파 스코프(검증 라운드) | `-k test_alpha` → 505 passed, 0 failed |
| 알파 무관성 근거(검증 라운드) | `git diff --stat 70775539 -- ai_strategy_loop/dashboard/backtest_jobs.py tests/unit/dashboard/test_backtest_jobs.py` 출력 없음 |

## 2. 독립 재검증 — 본 수복 라운드 실측 (2026-07-07, STAGE 신뢰 전제 없이 재실측)

1. **기준선 문서 내 검색 재확인**: `docs/` 전체에서 `test_cancel_kills_child_tree_and_releases_queue` 검색 → **0건**(두 기준선 문서 포함 전 저장소 문서 대상). "미문서화" 관측 재확인.
2. **격리 단독 재실행 3회** (`pytest tests/unit/dashboard/test_backtest_jobs.py::test_cancel_kills_child_tree_and_releases_queue -q`, 배경 프로세스 `tasklist` 실측 python 계열 10개 동시 실행 중 — 시스템 부하 낮지 않은 조건):
   - run 1: `1 passed in 1.08s`
   - run 2: `1 passed in 1.23s`
   - run 3: `1 passed in 1.10s`
3. **파일 단위 재실행** (`pytest tests/unit/dashboard/test_backtest_jobs.py -q`, 동일 파일 12개 테스트 전부): `12 passed in 4.67s` — 파일 단위 교차오염 없음.
4. **알파 스코프 재실행** (`pytest tests/unit -k test_alpha -q`): `505 passed, 4019 deselected in 40.65s`, 실패 0 — 검증 라운드 수치(505 passed, 0 failed)와 **정확히 일치**.
5. **누적 재실행 통계**: 검증 라운드 5회(3 fail/2 pass) + 본 라운드 3회(0 fail/3 pass) = 누적 8회 중 **3 fail / 5 pass**. 결정적 회귀가 아니라 확률적 실패(flaky)라는 판단과 정합.

결론: 본 라운드는 검증 라운드가 보고한 모든 수치를 독립적으로 재현했다(신규/소멸 없음). 알파 스코프는 여전히 완전 green.

## 3. 알파 무관성 구성적 증명 (증거 재실측 + 확장)

```
git diff --stat 70775539 -- ai_strategy_loop/dashboard/backtest_jobs.py tests/unit/dashboard/test_backtest_jobs.py
→ (출력 없음 = 바이트 동일)

git status --porcelain -- ai_strategy_loop/dashboard/backtest_jobs.py tests/unit/dashboard/test_backtest_jobs.py
→ (출력 없음 = 미커밋 변경 없음)
```

- **원인 파일 최종 수정 커밋(알파 착수 시점 기준)**: `git log --oneline 70775539 -1 -- ai_strategy_loop/dashboard/backtest_jobs.py` → `c5c531e41 대시보드 연구 UX와 조건식 AI 화면 완성`.
- **테스트 파일 최종 수정 커밋(알파 착수 시점 기준)**: `git log --oneline 70775539 -1 -- tests/unit/dashboard/test_backtest_jobs.py` → `d23f513a0 fix: 잡 매니저 워치독·트리킬 — 무출력 CLI 타임아웃 미발동과 취소 후 큐 영구 점유 해소`(공교롭게도 이 테스트가 감사하는 바로 그 트리킬·큐 해제 회귀의 원 수정 커밋).
- **조상 관계 확인**: `git merge-base --is-ancestor d23f513a0 70775539` → 참(0) — `d23f513a0`은 알파 착수 커밋 `70775539`의 조상. 즉 테스트 파일은 알파 랩이 존재하기 이전부터 현재 형태였다.
- **alpha 토큰 검색**: 원인 소스(`ai_strategy_loop/dashboard/backtest_jobs.py`)·테스트 파일(`tests/unit/dashboard/test_backtest_jobs.py`) 양쪽에서 대소문자 무시 `alpha` 검색 → **0건**. import·로직 어느 경로로도 알파 코드와 접점 없음.

∴ 원본 기준선 10건과 동일한 방법론(구성적 증명)으로, 11번째 실패도 알파 랩 착수 이전부터 존재한 코드 경로에 대한 것이며 알파 신규 코드와 무관함이 확정된다.

## 4. 근본원인 (파일·라인 단위)

| 대상 | 위치 | 메커니즘 |
|---|---|---|
| 테스트 본체 | `tests/unit/dashboard/test_backtest_jobs.py:180-208` | 실제 OS 프로세스 트리 기동(부모가 `subprocess.Popen`으로 120초 sleep 자식을 spawn 후 `p.wait()`) → `manager.cancel(job_id)` 호출 → `_wait_status(..., {"cancelled","error","timeout"}, timeout=20.0)`로 최대 20초간 상태 전이 대기 → `"cancelled"` 단정 |
| 상태 폴링 | `tests/unit/dashboard/test_backtest_jobs.py:60-67 (_wait_status)` | 0.1초 간격 폴링, `timeout` 도달 시 마지막 상태 그대로 반환(재시도 없음) |
| 트리 킬 구현 | `ai_strategy_loop/dashboard/backtest_jobs.py:652-686 (_hard_stop)` | `psutil.Process(proc.pid).children(recursive=True)`로 자식 전수 조회 후 `child.kill()` → 부모 `proc.terminate()` → `proc.wait(timeout=10.0)`(grace) → 타임아웃 시 `proc.kill()` 폴백 |
| 상태 확정 | 워커 스레드(별도) | 자식 프로세스가 상속받은 stdout 파이프를 모두 반납해야 `for line in proc.stdout` 루프가 EOF를 받아 종료 → 그 후에야 레코드 상태가 `"cancelled"`로 갱신됨(2026-06-12 회귀 주석, 테스트 docstring L183-184 참조) |

**비결정성의 원인**: 이 테스트는 실제 OS 서브프로세스 트리 생성·종료·스케줄링에 의존하는 **타이밍 민감 통합 테스트**다. `psutil` 자식 전수 조회·`kill()`·`terminate()`+`wait(grace=10s)`·워커 스레드 스케줄링·OS 프로세스 회수(reap) 각 단계가 시스템 부하에 비례해 지연될 수 있고, 이 지연의 합이 테스트의 20초 상한을 확률적으로 초과하면 실패로 관측된다. 검증 라운드의 실패는 전체 스위트 실행(469초, 다수 테스트 프로세스·스레드 동시 존재) 중 관측됐고, 당시 `tasklist`에 python.exe/pythonw.exe 계열 프로세스 12개가 동시 실행 중이었음이 이미 보고됐다. 본 수복 라운드에서도 재실행 시점에 배경 python 프로세스 10개가 동시 실행 중이었음을 확인했다(§2-2) — 그럼에도 3/3 통과했다는 사실은, 실패가 "배경 python 프로세스 개수"보다 **"동일 pytest 프로세스 내 스레드/파일핸들 총량이 큰 전체 스위트 실행 컨텍스트"**와 더 강하게 상관될 가능성을 시사한다(정직한 미확정 요인으로 기록 — 추가 재현 실험은 본 수복 스코프 밖).

## 5. 스코프 내 수리 가능성 판정

기존 기준선 부록(`baseline_failures_rootcause_addendum_20260706.md` §6)이 확립한 동일 원칙을 적용한다:

- 수리 방법은 두 갈래뿐이다 — (a) `ai_strategy_loop/dashboard/backtest_jobs.py`의 `_hard_stop`/트리킬 경로 수정(예: grace 단축, psutil 폴링 최적화), 또는 (b) 테스트의 `timeout=20.0` 상향·재시도 로직 추가. 둘 다 **알파 랩이 소관하지 않는 코어(대시보드 백테 잡 매니저) 또는 비알파 테스트 수정**을 요구한다 — 원본 문서 §3 "기존 파일 불수정(알파 랩 규율)"과 동일하게 알파 랩 소관 외.
- 알파 랩 산출물(`alpha_lab/**`, `cli/alpha_*.py`, `tests/unit/test_alpha_*.py`)에는 이 실패와 관련된 어떤 코드도 없다(§3, §4).
- **권고**: 수리는 wt-dev 레인 별도 사안으로 이관한다. 알파 랩 게이트는 이 실패로 인해 영향받지 않는다.

## 6. 게이트 해석 갱신

| 이전 표현(기준선 문서) | 갱신 표현(본 수복 문서) |
|---|---|
| "기준선 10건 1:1 대조" (전체 스위트 = 알파 247/290/505 green + 정확히 10건 실패) | "기준선 10건 확정(불변, 알파 무관) + 신규 관측 플레이키 1건(`test_cancel_kills_child_tree_and_releases_queue`, 비결정적, 알파 무관, 아웃오브스코프)" |
| 게이트 판정 | 불변: **"알파 스코프 전수 green(505 passed, 0 failed) + 비알파 실패 전건(10건 고정 + 1건 플레이키) 알파 무관 확정"** — 원본 §6 권고("알파 스코프 전수 green + 기준선 문서화 면제")를 11번째 항목까지 확장 적용 |

11번째 실패는 **결정적 실패가 아니므로 "10건" 고정 목록에 합류시키지 않는다** — 플레이키 테스트는 재실행마다 집합이 달라질 수 있어(§2-5 누적 8회 중 3 fail) 기준선 문서의 "고정 10건 노드 ID" 성격과 다르다. 대신 별도 항목("신규 관측 플레이키 1건")으로 명시해 향후 검증 라운드가 "11건이 나오면 기준선 불일치"로 오판하지 않도록 기록을 남긴다.

## 7. 예산·무결성 준수

- 본 수복 작업은 `pytest` 실행만 수반한다 — 백테스트 엔진 미사용(엔진 예산 영향 없음, 누적 V4E 9/60 불변), tick DB 미접근, `_database` 미접근.
- git 커밋 없음(오케스트레이터 소관). `backtest/graph/` 미접근.
- 기존 파일 수정: 없음(본 문서는 신규 파일). `baseline_failures_rootcause_addendum_20260706.md`에는 본 문서를 가리키는 additive 각주 1개 섹션만 추가(§8, 기존 텍스트 변경 없음).
- pip 미사용, print 미사용(문서 작성 및 `pytest`/`git` 조회만 수행).

## 8. 참조

- 원본 기준선: `../alpha_lab_20260705/baseline_test_failures_20260705.md`
- 근본원인 부록(1·2차 수복): `../alpha_lab_20260705/baseline_failures_rootcause_addendum_20260706.md`
- v4 프로그램 최종 판정(본 지적과 무관, 참고용): `v4_final_verdict.md`
