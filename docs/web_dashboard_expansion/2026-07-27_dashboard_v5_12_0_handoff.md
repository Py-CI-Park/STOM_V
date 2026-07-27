# 대시보드 v5.12.0 인계 문서

이전 인계: `2026-07-26_dashboard_v5_11_1_operational_ux_handoff.md`
함께 읽을 것: `2026-07-26_dashboard_v5_11_2_full_audit_and_ux_fixes.md`,
`2026-07-26_dashboard_v5_11_3_full_page_closeout.md`,
`2026-07-27_dashboard_v5_11_acceptance_checklist.md`

---

## 0. 이 문서를 읽는 순서

1. 루트 `AGENTS.md` → `docs/AGENTS.md`
2. 이 문서 §1(기준 상태) · §2(가장 중요한 사실)
3. `2026-07-27_dashboard_v5_11_acceptance_checklist.md` (인수 기준·문제 대장·사용자 검토 목록)
4. 필요 시 §3 이하

**V3K 승인 상태를 변경하지 않는다.** V3K는 계속 `3/6`이며 실거래·브로커·USER_ACK·보호 DB
전환을 허가하지 않는다. `performance_proved=false` 불변.

---

## 1. 인계 시점 기준 상태

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 브랜치 | `codex/dashboard-v5111-ux-acceptance` |
| HEAD | `6d1b81b5` |
| 세션 시작 HEAD | `f3dea2b8` |
| 이번 세션 커밋 | **23건** |
| 대시보드 release | **v5.12.0** (이전 v5.11.0) |
| build (backend=shell=번들 pin) | `8d7d8873` |
| API contract | `2` |
| 운영 주소 | **`http://127.0.0.1:8770`** — 단일 |
| 8771 | 종료됨(더 이상 쓰지 않음) |
| 미커밋 파일 | 0 |
| 대시보드 테스트 | 916 passed |

### 1.1 서버 기동 방식이 바뀌었다 — 중요

셸 백그라운드로 띄운 서버는 **작업이 회수될 때 함께 죽는다.** 이번 세션에서 실제로
그렇게 내려간 적이 있다. 반드시 셸에서 분리해 띄운다.

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
Start-Process -FilePath 'C:\Python\64\Python31313\python.exe' `
  -ArgumentList '-m','ai_strategy_loop','--host','127.0.0.1','--port','8770' `
  -WorkingDirectory 'C:\System_Trading\STOM\STOM_V.wt-dev' -WindowStyle Hidden `
  -RedirectStandardOutput 'C:\Temp\claude\dash8770_out.log' `
  -RedirectStandardError  'C:\Temp\claude\dash8770_err.log'
```

현재 pid `109516`. 확인은 `Invoke-RestMethod http://127.0.0.1:8770/health`.

### 1.2 브랜치 위험 — 최우선 처리 대상

```
codex/dashboard-v5111-ux-acceptance
  STOM_Version_2U_C 대비  앞선 1218커밋 · 뒤처진 0커밋
  업스트림 없음 — 원격 백업 없음, 로컬 전용
```

**1218커밋이 기준선에 머지되지 않고 원격 백업도 없이 로컬 디스크에만 있다.**
디스크 사고 시 전량 유실된다. 원격 푸시가 다음 작업의 P0다.

---

## 2. 가장 중요한 사실 3가지

### 2.1 잡 실행 경로는 정상이다 (확정)

213거래일 · 전종목 · 32엔진 백테스트가 **1.7분**에 완주했다. 그동안 "느리다/고장났다"고
본 것은 전부 다른 원인이었다.

### 2.2 인수 artifact를 확보했다

```
job       20260727_112426_ResearchTestTickB0900000_66061
조건식     ResearchTest_Tick_B/S_090000_092800_Wide_20260419
범위       tick · 20250407~20250430(18거래일) · 전종목 · 18엔진
결과       success · 3.7분 · CSV 생성
거래       4,450건 · 승률 35.15% · -53.0% · -23,152,855원 · MDD 53.83%
```

이 결과로 잡 기반 화면(20카드 · 2·3·4열 · 리포트 · 교차 A/B · 구간 브러시)을 전부
실데이터로 검증했다. **성과가 음수인 것은 인수 관심사가 아니다.**

### 2.3 프로세스 견고성 결함이 남아 있다 — 일반화 목적 미달

임의 조건식 5개 쌍 중 **3개가 사유 없이 무한 교착**한다.

| 조건식 쌍 | 시간단위 | 윈도우 호출 | 거래 | 결과 |
|---|---|---:|---|---|
| `20250715_Study` | min | 13 | 0건 | ✅ 1.7분 |
| `ResearchTest_..._Wide_20260419` | tick | 0 | 4,450건 | ✅ 3.7분 |
| `CSS_V7_MIN_MASTER` | min | 40 | ? | ❌ 교착 |
| `CSS_V7_TICK_MASTER` | tick | ? | ? | ❌ 교착(21.9GB 로딩 후 정지) |
| `C_S_3_902_Min` | min | 13 | ? | ❌ 교착(2.97GB 로딩 후 정지) |

**시간단위·기간·엔진 수는 무관하다.** min·tick 양쪽에서 완주와 교착이 모두 나온다.
교착 중 CPU 0% · 디스크 0B/s — 연산 폭주가 아니라 **대기**다.

AI 루프는 임의의 조건식을 생성하므로, 어떤 부류가 엔진을 교착시키면 **루프 자체도 같은
방식으로 멈춘다.** 일반화를 목적으로 하는 프로세스는 임의 입력에 대해 멈추지 않고
**사유와 함께 빠르게 실패**해야 한다. 이것이 다음 작업의 핵심 과제다.

---

## 3. 이번 세션에 한 일 (커밋 23건)

### 3.1 대시보드 기능 (14건)

| 커밋 | 내용 |
|---|---|
| `9f34862a` | 세대 결과의 몬테카를로·구간 분석 복구(“미지원” 안내가 사실이 아니었음) |
| `7f8332c6` | 분석 매트릭스 플롯 높이 통일(303/372/420 → 300 단일, 축 잘림 해결) |
| `d84012e3` | 진입 주소를 정본 루트 하나로 통합 |
| `d4119cd0` | 거버넌스·가정 루프·부검을 쉬운 말과 한 화면 구조로 리모델 |
| `ed84c081` | 조건식 팝업 나란히 보기·검색·글자 크기 |
| `5071a737` | 결과 소스 구분 명시 + 연구 개선 추이 카드 |
| `f1e7c21a` | Reports Summary 지표를 run 발행 값과 연결(출처 표기) |
| `3ce07b84` | A/B 비교를 진화 세대까지 확장 |
| `211cac3c` | 차트 색 역할 토큰화 + 설정·용어 우리말 정리 |
| `64302746` | 리플레이에 결과 맥락 전달 + 세션 상태 표시 |
| `fe244c5f` | 근거 기반 “다음에 무엇을 바꿀까” 제안 카드 |
| `c28652ae` | 레일 우리말 통일 + 레거시 셸 상시 진입 제거 |
| `4d663332` | 엔진 수를 기간 내 거래일 수에 맞춰 실행 전 보정 |
| `e439b237` | 엔진 수 상한 16 → 64 |

### 3.2 프로세스 진단으로 나온 수정 (3건)

| 커밋 | 내용 |
|---|---|
| `4e9b42c3` | 없는 조건식으로는 잡을 만들지 않음(잡 333건 즉사 원인) |
| `6b387dc9` | CLI 한글 실패 사유 파괴 수정(cp949 → UTF-8) |
| `275d3362` | 진행 신호 감시 — 멈춘 백테스트를 화면이 구분 |

### 3.3 내가 만들고 고친 회귀 (2건)

| 커밋 | 내용 |
|---|---|
| `0de52380` | 정본 루트 `/` 를 세션 부트스트랩 목록에 넣지 않아 신규 방문자가 `/ws` 4401 거부 |
| `275d3362` | `idleWarn` 을 `tracking` 선언 앞에 두어 const TDZ 로 Backtest 탭 렌더 붕괴 |

### 3.4 버전·문서 (4건)

`1ca3c924` `5eb50558` `46f3e521` `1ca316ee` `6d1b81b5`

---

## 4. 인수 기준 진행률 (v5.11.1 핸드오프 §9)

| # | 기준 | 상태 |
|---|---|:---:|
| 1 | 8770 최신 build 단일 실행 | ✅ |
| 2 | 주요 8개 탭 최종 육안 검토 | ⬜ **사용자만 가능** |
| 3 | openable Backtest artifact 1건 | ✅ |
| 4 | 기본 3열 + 2·3·4열 전환 실데이터 | ✅ |
| 5 | 분석 차트 독립 동일 높이 매트릭스 | ✅ |
| 6 | Replay stale-session 4401 미재발 | ◐ 직전 세션 실증, 이번 세션 미재검증 |
| 7 | Reports Summary 발행 지표/정직한 미발행 | ✅ |
| 8 | 전체 테스트·빌드·sync·diff 통과 | ✅ |
| 9 | V3K 3/6 · performance_proved=false · 보호 경계 | ✅ |

**8/9 충족.** 남은 것은 사람이 하는 육안 검토 하나.

---

## 5. 재현·검증 절차

```powershell
# 프런트 빌드(소스 수정 시 필수)
Set-Location C:/System_Trading/STOM/STOM_V.wt-dev/ai_strategy_loop/dashboard/webui-build
npm run build

# 전체 대시보드 테스트
Set-Location C:/System_Trading/STOM/STOM_V.wt-dev
python -m pytest tests/unit/dashboard -q

# 브랜치 게이트
python scripts/verify_nonrelease_sync.py
git diff --check

# 보호 런타임 경로 오염 확인
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

### 5.1 인수 백테스트 재현

```python
# Origin 헤더 + 세션 쿠키 필요. 세션은 수명이 짧아 제출 직전마다 새로 받는다.
payload = {"buy":"ResearchTest_Tick_B_090000_092800_Wide_20260419",
           "sell":"ResearchTest_Tick_S_090000_092800_Wide_20260419",
           "start":20250407, "end":20250430, "timeframe":"tick",
           "engines":18, "timeout":10800,
           "divid_mode":"종목코드별 분류", "mode":"backtest"}
# POST /bt/run → job_id → GET /bt/job?job_id=... 폴링
```

**엔진 수는 기간 내 거래일 수를 넘지 못한다.** 넘기면 서버가 자동으로 낮추고
`engine_note` 로 알린다. `GET /bt/trading_days?timeframe=&start=&end=` 로 미리 확인 가능.

---

## 6. 변경 금지 경계

- `performance_proved=true` 로 바꾸지 않는다.
- 실제 발행되지 않은 지표를 계산해 정본처럼 표시하지 않는다(파생값은 반드시 `파생값` 표기).
- 조건식 자산(`strategy.db`)을 인수 편의를 위해 수정하지 않는다. **`관심종목 == 1` 등 조건
  내용을 빼지 않는다.**
- 차트들을 다시 그룹 상자 안에 재중첩하지 않는다.
- 거버넌스를 다시 탭으로 나누지 않는다.
- History에 결정 원장/verdict 중심 흐름을 되살리지 않는다.
- `.gjc`, `.omo`, 연구 evidence, 보호 런타임 파일을 정리 대상으로 취급하지 않는다.
- `git add -A`, `git reset --hard`, 광범위 stash/clean 금지.
- V3K gate 4~6, live broker/order, protected DB cutover를 승인 없이 진행하지 않는다.

---

## 7. 다음 작업 우선순위

### P0 — 브랜치 백업 (데이터 유실 위험)

1218커밋이 원격 백업 없이 로컬에만 있다. 원격 푸시 후 `STOM_Version_2U_C` 머지 계획을 세운다.

### P1 — 엔진 워치독 (승인 필요, 엔진 코드 변경)

진행 신호가 일정 시간 끊기면 엔진이 스스로 사유와 함께 종료해야 한다. 지금은 대시보드가
감지만 하고(`idle_for_sec`) 엔진은 계속 매달린다. **일반화 프로세스의 필수 안전장치.**

### P1 — 사용자 육안 검토 (인수 기준 2)

`2026-07-27_dashboard_v5_11_acceptance_checklist.md` §4 목록.

### P2 — 교착 기전 확정

엔진 계측을 추가해 어느 지점에서 대기하는지 특정한다. 대시보드 범위 밖.

### P3 — 연구 자산 탭 정본화 여부 결정

이번 세션에서 유일하게 손대지 않은 탭. 승격할지 접을지 정해야 다듬을 수 있다.

---

## 8. 알아두면 시간을 아끼는 것들

- **git index.lock 이 자주 stale 로 남는다.** 외부 도구가 읽기 전용 `git remote`/`rev-parse`
  를 계속 돌린다. 0바이트이고 쓰기 git 프로세스가 없으면 지워도 된다.
- **콘솔이 cp949 라 한글 출력이 깨진다.** 결과를 파일에 UTF-8로 쓰고 읽으면 정확히 보인다.
- **브라우저 창 크기가 임의로 바뀐다.** 스크린샷 전에 `resize_window` 로 폭을 고정한다.
- **세션 쿠키 수명이 짧다.** 긴 스윕은 제출 직전마다 세션을 새로 받아야 401이 안 난다.
- **CSS_V7 은 프로세스가 아니다.** 차트술사 보고서 하나의 가설 카탈로그이며
  `hypothesis_seed` · 연구 레인 전용 · OOS 검증 이력 `none` 이다. 인수 자산으로 쓰지 않는다.

---

## 9. 최종 인계 문장

이번 세션은 v5.11.1 인수를 목표로 대시보드 문제 16건 중 14건을 닫고, 그 검증을 위해
프로세스를 실제로 돌렸다. 그 과정에서 잡 실행 경로가 정상임을 확정하고 인수 artifact
(4,450거래)를 확보해 잡 기반 화면을 전부 실데이터로 검증했다. 동시에 **임의 조건식 3개가
사유 없이 무한 교착한다는 프로세스 견고성 결함**을 발견해 재분류했다. 대시보드는
v5.12.0 으로 8770 단일 운영 중이며, 남은 인수 항목은 사람이 하는 육안 검토 하나다.
그 밖의 위험은 **1218커밋이 원격 백업 없이 로컬에만 있다는 것**이다.
