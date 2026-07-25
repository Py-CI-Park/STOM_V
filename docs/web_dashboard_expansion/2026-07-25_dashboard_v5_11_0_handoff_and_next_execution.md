# 대시보드 v5.11.0 상세 핸드오프 및 다음 실행 지침

## 0. 문서 목적과 정본 우선순위

이 문서는 2026-07-25 기준으로 조건식 AI 연구 대시보드 작업을 새 에이전트나 새 세션이 즉시 이어받기 위한 자기완결형 핸드오프다. v5.10 회귀 감사부터 v5.11.0 복구·검증·릴리스까지의 상태, 현재 실행 방법, 안전 경계, 미완료 검증, 다음 권장 실행 순서를 한곳에 고정한다.

읽기 우선순위는 다음과 같다.

1. 이 문서 — 현재 재개 기준점과 다음 실행 순서
2. `docs/web_dashboard_expansion/2026-07-23_dashboard_v5_11_0_recovery_development_and_release_report.md` — v5.11.0 구현·검증 결과
3. `docs/web_dashboard_expansion/2026-07-23_dashboard_v5_10_regression_forensic_audit_and_recovery_plan.md` — 사용자 지적과 회귀 원인
4. `artifacts/v511_final_interaction_gate.json` — 최종 브라우저 상호작용 증거
5. `artifacts/v511_accessibility_gate.json` — 접근성 matrix 증거
6. 루트 `AGENTS.md`와 작업 디렉터리별 `AGENTS.md` — 저장소·경계 규칙

이 문서는 기존 `docs/AGENT_HANDOFF.md`를 대체하지 않는다. 그 문서는 조건식 연구 루프 전체의 역사적 핸드오프이고, 이 문서는 **웹 대시보드 v5.11.0 이후 작업**의 정본이다.

---

## 1. 현재 확정 상태

| 항목 | 현재 값 |
|---|---|
| 작업 디렉터리 | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 정식 부모 브랜치 | `loop/process-research-pipeline` |
| 로컬/원격 HEAD | `73cfafab64c844f0db17cc8f5b7929112baa73b1` |
| 릴리스 태그 | `V2UC-Dashboard-v5.11.0` |
| 최종 통합 PR | `#122` — MERGED |
| 정식 웹 주소 | `http://127.0.0.1:8770/ui/` |
| shell | V4 `v4-ops` — 유일한 정식 shell |
| release | `v5.11.0` |
| app build | `812714fc` |
| CSS build | `ea1ca2fb` |
| API contract | `2` |
| 연구 성능 증명 | `performance_proved=false` |
| V3K gate | `3/6` — 변경 금지 |

2026-07-25 재확인 결과:

- `loop/process-research-pipeline`은 `origin/loop/process-research-pipeline`과 일치했다.
- 추적 파일 변경은 없었다.
- 태그 이후 추가 추적 커밋은 없었다.
- 기존 `.gjc/`, `.omo/`, 연구 evidence, runtime state 등 다수 untracked 파일은 사용자/연구 작업으로 보존되어 있다. 삭제·stage·stash·revert하지 않는다.
- 대시보드는 `stom_dashboard.bat`로 실행 중이며 확인 당시 PID는 `86644`였다. PID는 재실행할 때 달라지는 관찰값이다.
- `/health`는 `status=ok`, release `v5.11.0`, build `812714fc`를 반환했다.

---

## 2. 왜 v5.11.0이 필요했는가

v5.10은 자동화 테스트와 정적 품질 수치는 높았지만 실제 사용 화면에서 다음 회귀가 확인되어 merge/deploy가 차단됐다.

1. 8770과 임시 8784 주소가 혼동되고 path와 `?tab=`이 충돌했다.
2. 8770 프로세스가 최신 frontend와 낡은 backend를 함께 제공해 `/hall_of_fame/catalog`가 404가 되는 stale server 상태가 발생했다.
3. Backtest 결과 그래프가 강제 1열이 되었고 과거의 사용자 선택형 다중 열 레이아웃이 사라졌다.
4. 결과·진단 그래프가 조건부 접힘과 artifact 부재 때문에 사용자가 “그래프가 없어졌다”고 판단할 수 있었다.
5. 성과/Hall 표의 양수·음수·MDD·gate/status 의미 색상과 가독성이 퇴행했다.
6. Replay 기본 Canvas가 소수 봉과 최신가 guide를 평평한 선처럼 보이게 했고 quick start 후 slider `0/0` 정지가 재현됐다.
7. Reports는 안전한 viewer를 가졌지만 실제 보고서 renderer가 둘로 나뉘었고 template 차이가 색상 theme 수준에 머물렀다.
8. 기존 단위·브라우저 load 테스트가 실제 선택·재생·seek·레이아웃 전환을 충분히 검증하지 못했다.

상세 원인과 v5.10 증거는 forensic 보고서와 `artifacts/v510_forensic_*` 파일을 참조한다. v5.10의 기존 `95.6/100` 주장은 철회됐으며 다시 사용하면 안 된다.

---

## 3. v5.11.0 단계별 구현 기록

| 단계 | 구현 커밋 | 병합 PR/커밋 | 핵심 결과 |
|---|---|---|---|
| PR-1 Foundation | `61f871f0` | `#115` / `3278ba0e` | frontend/backend release·build·PID, capability freshness, canonical path 우선, stale 경고 |
| PR-2 Backtest/Live | `812d7802` | `#116` / `a67a0644` | `auto/wide/balanced/dense`, 실제 열 수, 진단 발견성, Live 완료 후 결과 진입 |
| PR-3 성과 | `76854149` | `#117` / `4b1e0e9c` | signed return, MDD risk, gate/status/outcome badge, sticky header/identity, zebra/hover |
| PR-4 Replay | `ad120c9c` | `#118` / `eb0eef9f` | LWC 기본, Canvas 실험적, 0-frame timeout, lifecycle/OHLC/progress/sparse geometry |
| PR-5 Reports | `e5e3ac6f` | `#119` / `476ea98a` | typed script-free renderer, 3 templates, 4 themes, run-report adapter, manifest metadata |
| PR-6 History/Settings | `390246f6` | `#120` / `3a88cddd` | History source-only trend/scatter/regression, shared layout, probes, redacted logs, scoped reset |
| PR-7 Final gate | `2276fde7` | `#121` / `19f9df5f` | 전체 회귀·접근성·responsive gate, Hall `++` 수정, Windows jsdom timeout 안정화 |
| 최종 통합 | — | `#122` / `73cfafab` | `loop/process-research-pipeline` 병합 및 v5.11.0 태그 |

### 3.1 서버·주소·버전 계약

- 정식 주소는 `http://127.0.0.1:8770/ui/` 하나다.
- 8784는 과거 forensic audit용 임시 포트였으며 정식 주소로 안내하지 않는다.
- canonical path가 상충하는 query보다 우선한다. 예: `/ui/evolution/workbench?tab=research`는 `/ui/evolution/workbench`로 정규화되고 성과 탭을 유지한다.
- `/health`는 frontend/backend release, build, process PID/start metadata를 제공한다.
- frontend/backend capability가 어긋나면 UI는 stale 상태를 경고하고 기능을 정상인 것처럼 가장하지 않는다.

### 3.2 Backtest·Live 결과 계약

- 공유 localStorage key는 `stom_v511_result_layout`이다.
- 허용 mode는 `auto`, `wide`, `balanced`, `dense`뿐이다.
- 요약·identity·capability는 전폭을 유지하고 동종 chart/diagnostic group만 선택형 열 배치를 적용한다.
- 실제 계산된 열 수를 표시한다. viewport가 좁으면 사용자 선택보다 안전한 1열 clamp가 우선한다.
- 결과 identity와 request sequence가 바뀌면 낡은 응답을 폐기한다.
- metrics-only generation이나 명시적 `null`에는 차트를 꾸며내지 않는다.
- artifact가 없으면 demo substitution을 하지 않고 unavailable 이유를 표시한다.

### 3.3 성과/Hall 계약

- 양수·음수·보합은 색상만이 아니라 텍스트와 아이콘을 함께 사용한다.
- MDD는 절댓값 위험 등급으로 `낮음/주의/높음`을 표시한다.
- gate/status/outcome badge는 저장된 값을 표현할 뿐 새 verdict를 계산하지 않는다.
- 인간 표와 AI full catalog 모두 같은 semantic formatter를 사용한다.
- 양수 formatter가 이미 `+`를 포함하더라도 화면에 `++`가 생기지 않도록 중앙 formatter가 정규화한다.
- AI catalog는 서버 pagination/filter/sort 소유권을 유지하며 전체 5,364개를 frontend가 임의 축소하지 않는다.

### 3.4 Replay 계약

- 신규 사용자 기본 renderer는 vendored Lightweight Charts(LWC)다.
- 명시적으로 저장된 기존 `live/svg/lwc` 선택은 보존한다.
- Canvas는 `고급/실험적`, SVG는 fallback이다.
- 0-frame 상태가 무한 playing으로 보이지 않도록 timeout/error/progress를 명시한다.
- slider max는 수신한 전체 프레임 계약에 맞고 pause/resume/seek가 실제 lifecycle과 일치해야 한다.
- OHLC가 없는 값을 0으로 만들지 않는다.
- 1초 tick OHLC는 실제 tick 묶음으로 집계하며 마지막가 guide를 candle data로 오인하게 만들지 않는다.

### 3.5 Reports 계약

- renderer는 `ai_strategy_loop/dashboard/report_writer.py`가 정본이다.
- template ID는 `executive`, `quant_research`, `research_journal`이다.
- theme은 `system`, `light`, `dark`, `print`이다.
- typed block, escaped data, inert SVG, CSP, sandbox, script-free publication을 유지한다.
- manifest/catalog에 `renderer_version`, `template_id`, `theme`, TOC, provenance/integrity metadata가 전달된다.
- `scripts/build_step_reports.py`는 공통 renderer adapter를 사용한다.
- 실패·누락 measurement는 평균/성과 집계에서 제외하고 제외 건수와 unavailable evidence를 보존한다.
- 검증할 수 없는 legacy HTML을 자동 덮어쓰거나 새 template 결과로 가장하지 않는다.

### 3.6 History·Settings 계약

- History의 authoritative selection은 `run_id + generation`이다.
- exact strategy code와 stale-request guard를 유지한다.
- 반복 분석은 이미 로드된 generation의 score/MDD/reason만 사용한다.
- 누락 metric은 0으로 바꾸지 않고 `—`/사용 불가로 표시한다.
- trend/scatter에는 접근 가능한 텍스트·표 대안을 제공한다.
- Settings probe는 manifest와 읽기 전용 `/health` 응답만 표시한다.
- `/debug/logs`는 인증된 same-origin GET, 최대 200행, redaction 경계를 유지한다.
- log export는 현재 화면에서 이미 가려지고 필터된 행만 로컬 파일로 만든다.
- preference reset은 allowlist category만 삭제하며 연구 데이터·runtime state·임의 `stom_*` key를 지우지 않는다.

---

## 4. 최종 검증 기준선

다음은 v5.11.0 릴리스 직전 실제 실행된 기준선이다.

| 검증 | 결과 |
|---|---|
| `python -m pytest tests/unit/dashboard/ -q` | `886 passed in 583.78s` |
| Reports focused suite | `100 passed` |
| Hall/Replay/UI focused | `56 passed` |
| History/Settings focused | `9 passed` |
| runtime JSX | `91 JSX / 541 graph files PASS` |
| final app bundle | `812714fc` |
| final CSS bundle | `ea1ca2fb` |
| responsive route matrix | 7 viewport × 7 route = `49/49`, overflow/root/error failure 0 |
| accessibility | `252/252`, serious/critical 0, runtime/axe errors 0 |
| Hall browser evidence | 실제 69 rows, positive color `rgb(76, 214, 179)`, `++` 0 |
| Replay browser evidence | LWC/min, 376 total bars, 활성 slider, 실제 OHLC/candles |
| nonrelease sync | PASS |
| `git diff --check` | PASS |

접근성 결과의 minor/moderate 관찰을 “모든 violation 0”으로 왜곡하지 않는다. 정확한 주장은 **serious/critical 0이며 gate failure 0**이다.

최종 독립 architect review는 code/release blocker가 없고 PR-7 merge가 안전하다고 판정했다. 초기 LOW finding은 Replay screenshot이 이전 build였다는 provenance 문제였으나 최종 build `812714fc`에서 다시 촬영하고 receipt를 갱신한 뒤 병합했다.

---

## 5. 현재 실행·종료·재시작 방법

### 5.1 권장 실행 — 배치파일과 실제 웹 브라우저

```bat
C:\System_Trading\STOM\STOM_V.wt-dev\stom_dashboard.bat
```

배치파일은 다음을 수행한다.

- Python: `C:\Python\64\Python31313\python.exe`
- host: `127.0.0.1`
- port: `8770`
- health가 응답하면 기본 웹 브라우저에서 `http://127.0.0.1:8770/ui`를 연다.
- 새 명령창의 `Ctrl+C` 또는 창 닫기로 해당 서버만 종료한다.

현재 배치 실행 상태를 확인하려면:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8770/health
```

### 5.2 브라우저를 열지 않는 진단 실행

```bat
set STOM_DASHBOARD_NO_BROWSER=1
stom_dashboard.bat
```

### 5.3 금지되는 종료 방식

- `taskkill /F /IM python.exe` 금지
- 모든 Python 프로세스 종료 금지
- 무관 dashboard/research/backtest worker 종료 금지

8770 listener PID를 조회한 뒤 그 PID만 종료하거나, 배치 명령창에서 `Ctrl+C`를 사용한다.

### 5.4 frontend/backend 반영 규칙

- `.jsx` 또는 CSS 변경 후 반드시 `ai_strategy_loop/dashboard/webui-build`의 정식 build를 실행해 bundle과 HTML pin을 함께 갱신한다.
- backend Python endpoint/module 변경은 uvicorn 재시작이 필요하다.
- 정적 source만 바꾸고 bundle을 재생성하지 않은 상태를 완료로 보고하지 않는다.
- stale server를 피하기 위해 재시작 뒤 `/health` release/build와 `/ui/bundle/manifest.json`을 함께 확인한다.

---

## 6. 절대 보존해야 하는 경계

1. V4 shell이 정본이다. legacy `app.jsx`에 신규 기능을 추가하지 않는다.
2. 없는 authoritative data를 demo, inferred value, 빈 차트, 0으로 채우지 않는다.
3. `performance_proved=true`로 바꾸지 않는다. synthetic scale/UX gate는 투자 성능 증거가 아니다.
4. V3K는 `3/6`이다. 승인 phrase와 KHOPENAPI evidence 없이 gate 4~6, live order, USER_ACK, protected DB cutover를 진행하지 않는다.
5. Reports CSP/sandbox/script-free/inert SVG를 약화하지 않는다.
6. `/debug/logs` 인증·same-origin·redaction 경계를 약화하지 않는다.
7. protected/runtime path를 source나 scratch로 취급하지 않는다: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/v3k_gui_settings.json`.
8. 기존 untracked `.gjc`, `.omo`, research artifacts는 사용자 작업이다. `git add -A`, stash, reset, clean, 삭제를 하지 않는다.
9. commit은 명시적 path staging만 사용하고 한국어 title/markdown body 규칙을 지킨다.
10. release score를 테스트 통과 수만으로 다시 산출하지 않는다.

---

## 7. 남아 있는 실제 검증 공백

v5.11.0에서 알려진 가장 중요한 공백은 다음 하나다.

> 현재 최근 Backtest 목록에는 **열 수 있는 완료 artifact**가 없어 최종 브라우저 gate에서 새 실제 Backtest 완료 결과를 선택해 전체 chart/layout/diagnostics 상호작용을 끝까지 검증하지 못했다.

이미 검증된 것:

- renderer/layout/identity/request guard 단위·통합 계약
- artifact 부재 fail-closed 상태
- Live/Backtest 결과 영역의 source ownership
- viewport와 접근성 계약

아직 실제 운영 인수에서 확인할 것:

- 실제 완료 job 또는 openable run/gen 선택
- summary/equity/distribution/MDD/rolling/monthly/diagnostics의 실제 데이터 렌더
- `auto/wide/balanced/dense` 전환과 실제 열 수
- Live 완료 뒤 결과 재진입
- Monte Carlo와 구간 분석 capability별 표시
- stale selection 전환 중 낡은 결과가 섞이지 않는지

이 공백 때문에 신규 기능 확장보다 **v5.11.1 operational acceptance**가 다음 우선순위다.

---

## 8. 다음 권장 실행 — v5.11.1 Operational Acceptance

### 8.1 브랜치와 범위

새 작업은 현재 정본에서 시작한다.

```text
base branch: loop/process-research-pipeline
base commit: 73cfafab
new branch: feature/dashboard-v5.11.1-operational-acceptance
```

이 단계의 기본 원칙은 “문제가 없으면 코드 변경 없음”이다. 실제 상호작용 결함이 발견될 때만 작은 source fix, focused test, bundle rebuild를 수행한다.

### 8.2 P0 — 실행 정합성 preflight

1. `git status --short --branch --untracked-files=no`가 tracked clean인지 확인한다.
2. `git rev-parse HEAD`가 `73cfafab...` 또는 그 이후 승인된 후속 commit인지 확인한다.
3. `stom_dashboard.bat`로 8770을 실행한다.
4. `/health`의 frontend/backend release/build가 일치하는지 확인한다.
5. manifest의 app/CSS hash가 HTML query pin과 일치하는지 확인한다.
6. `/hall_of_fame/catalog?limit=1`, `/reports`, `/bt/health`, `/sim/health` capability probe가 성공하는지 확인한다.
7. `/ui/evolution/workbench?tab=research`가 성과 canonical path로 정규화되는지 확인한다.

### 8.3 P1 — 실제 Backtest 완료 artifact 확보

- 기존 openable 완료 artifact가 있으면 재사용한다.
- 없다면 protected DB나 운영 gate를 건드리지 않는 공식 offline Backtest profile로 최소 1건을 완료한다.
- demo result를 사용하지 않는다.
- job/run/gen identity, source hash, profile, 기간, 상태를 evidence에 기록한다.
- 실패·취소 job은 완료 artifact 대신 사용할 수 없다.

### 8.4 P1 — Backtest/Live 실제 상호작용 matrix

각 viewport `375, 768, 1199, 1200, 1920, 2560, 3440`에서:

- 결과 선택 전 unavailable 상태
- 완료 artifact 선택 후 실제 chart 수와 source identity
- `auto`, `wide`, `balanced`, `dense` 각각 클릭
- 표시된 실제 열 수와 computed grid columns
- summary/identity/capability full-width 유지
- diagnostics shell 가시성 및 lazy data load
- Monte Carlo 지원/미지원 표시
- range brush 및 clear
- source를 빠르게 두 번 바꿨을 때 stale response 폐기
- Live 완료 뒤 결과 분석으로 복귀
- horizontal overflow, pageerror, console error, error boundary 0

### 8.5 P1 — Replay full-day acceptance

- 신규 profile의 기본이 LWC인지 확인한다.
- 1봉, 2봉, 20봉, 120봉, 376봉 시점 캔들 geometry를 확인한다.
- play → pause → seek → resume → full-day completion을 수행한다.
- slider value/max/disabled, received/total, OHLC를 기록한다.
- Canvas와 SVG는 보조 renderer로 각각 한 번 전환해 error가 없는지만 확인한다.
- 0-frame timeout을 별도 fixture로 확인한다.
- screenshot에는 release/build와 lifecycle state가 함께 보여야 한다.

### 8.6 P1 — Reports acceptance

3 template × 4 theme 조합을 검증한다.

| Template | 목적 |
|---|---|
| `executive` | 빠른 의사결정과 KPI 중심 |
| `quant_research` | 지표·표·chart·제약 중심 |
| `research_journal` | 가설·실행·부검·다음 행동 중심 |

각 조합에서:

- template hierarchy가 실제로 구분되는지
- TOC와 anchor 이동
- KPI/semantic table/inert SVG
- 긴 표 overflow와 print page break
- CSP/sandbox와 script 0
- manifest `renderer_version/template_id/theme`
- HTML/PDF provenance와 content hash
- unavailable evidence 및 failed measurement 제외 문구

### 8.7 P2 — History·성과·Settings acceptance

- History exact run/gen code, 440~560px code viewport, source-only trend/scatter/regression을 확인한다.
- missing score/MDD가 0이 아닌 `—`인지 확인한다.
- 성과 69+ loaded rows에서 positive/negative/MDD/gate/status computed style과 텍스트/icon을 확인한다.
- full 5,364 catalog pagination/filter/sort에서 duplicate 0과 complete behavior를 확인한다.
- Settings release/build/PID probe를 `/health`와 대조한다.
- redacted log level/source/query filter와 local export를 확인한다.
- scoped reset이 allowlist key만 제거하는지 확인한다.

### 8.8 P3 — 최종 gate와 종료 조건

필수 gate:

```powershell
python -m pytest tests/unit/dashboard/ -q
npm --prefix ai_strategy_loop/dashboard/webui-build run build
python scripts/verify_dashboard_v58_accessibility.py --base-url http://127.0.0.1:8770 --output artifacts/v5111_accessibility_gate.json
python scripts/verify_nonrelease_sync.py
git diff --check
```

추가로 실제 브라우저 interaction transcript와 viewport screenshots를 남긴다. 결과는 다음 중 하나로 종료한다.

- **CLEAR / no code change**: v5.11.0 유지, acceptance evidence/report만 필요할 경우 별도 문서 commit
- **PATCH**: 실제 결함만 최소 수정하고 `v5.11.1` 후보 생성
- **BLOCK**: data truth, stale identity, security boundary, Replay lifecycle 같은 신뢰성 결함이 남음

`v5.11.1` tag는 실제 code fix와 전체 gate가 있을 때만 만든다. 단순 재검증만으로 새 release tag를 만들 필요는 없다.

---

## 9. 문제 발생 시 진단 순서

### 화면은 v5.11인데 API가 404

1. `/health` backend build 확인
2. manifest app build 확인
3. 8770 listener PID/cwd/cmdline 확인
4. 해당 PID만 종료
5. `stom_dashboard.bat` 재실행
6. capability endpoint 재확인

### path와 선택 탭이 다름

- 최종 URL에서 상충 query가 제거됐는지 확인한다.
- `dashboard-v4-shell.jsx`의 path 우선 routing을 확인한다.
- legacy query behavior를 다시 우선시키지 않는다.

### Backtest 차트가 없음

1. source identity가 선택됐는지
2. artifact가 openable인지
3. metrics-only 또는 explicit null인지
4. capability가 chart/analysis를 지원하는지
5. request sequence/source key가 현재 선택과 같은지
6. unavailable shell이 이유를 표시하는지

없는 data를 demo로 대체하지 않는다.

### Hall 색상이 모두 같아 보임

- `td` 자체가 아니라 `.hof-metric--positive/negative` descendant computed color를 확인한다.
- `++`가 없는지 확인한다.
- 색상만 확인하지 말고 텍스트·icon·aria-label도 함께 확인한다.

### Replay가 0/0 또는 선처럼 보임

1. renderer가 LWC인지
2. engine mode localStorage가 legacy Canvas를 명시적으로 보존한 상태인지
3. WebSocket accepted/open 여부
4. received/total과 slider max
5. selected date/code와 backend row count
6. 0-frame timeout message
7. OHLC high/low가 실제로 벌어지는지

### Reports metadata가 UI에 없음

- generated manifest entry 확인
- `app.py` catalog allowlist의 `renderer_version/template_id/theme` 확인
- integrity status와 content hash 확인
- legacy static report인지 typed renderer report인지 구분

---

## 10. 변경 시 파일 지도

| 영역 | 주요 파일 |
|---|---|
| server/route/catalog | `ai_strategy_loop/dashboard/app.py` |
| V4 shell/routing | `ai_strategy_loop/dashboard/frontend/dashboard-v4-shell.jsx` |
| Backtest result | `bt-result-area.jsx`, `bt-equity-charts.jsx`, `bt-distribution-charts.jsx`, `bt-gui-parity.jsx` |
| Live ownership | `v4-research.jsx` |
| History | `v4-history.jsx`, `research-records-panel.jsx`, `rp-utils.jsx` |
| Hall | `chart-hall-of-fame.jsx`, `hof-inventory.jsx` |
| Replay frontend | `sim-tab-root.jsx`, `sim-tab-utils.jsx`, `sim-live-chart.jsx` |
| Replay backend | `replay_engine.py`, `simulation_api.py` |
| Reports | `report_writer.py`, `v4-reports.jsx`, `scripts/build_step_reports.py` |
| Settings/logs | `v4-settings.jsx`, `dashboard-v4-shell.jsx` |
| shared chart state | `chart-frame.jsx` |
| styling | `v4.css`, 필요한 경우 `styles.css` |
| frontend build | `ai_strategy_loop/dashboard/webui-build/` |

수정 전에는 해당 디렉터리의 `AGENTS.md`를 읽고 exported symbol을 바꾸면 LSP references를 먼저 확인한다.

---

## 11. Commit·PR 운영 규칙

- 현재 parent에서 직접 기능 개발하지 말고 목적별 feature branch를 만든다.
- 여러 독립 결함을 한 commit에 섞지 않는다.
- source와 직접 영향을 받는 test, generated bundle, report/evidence를 함께 갱신한다.
- `git add -A`를 사용하지 않는다. 명시적 파일만 stage한다.
- commit title과 markdown body는 한국어로 작성한다.
- PR body에 실제 실행한 명령과 결과만 적는다.
- 테스트를 실행하지 않았으면 실행했다고 쓰지 않는다.
- merge 전 tracked status, staged name/status, `git diff --cached --check`를 확인한다.
- merge 후 parent를 fast-forward하고 tag가 merge commit을 가리키는지 확인한다.

---

## 12. 새 세션 즉시 재개 체크리스트

```text
[ ] 루트 AGENTS.md와 작업 영역 AGENTS.md를 읽었다.
[ ] 이 핸드오프와 v5.11 release report, v5.10 forensic report를 읽었다.
[ ] branch=loop/process-research-pipeline, HEAD=73cfafab 기준을 확인했다.
[ ] tracked worktree가 clean이고 untracked 사용자 작업을 건드리지 않았다.
[ ] stom_dashboard.bat로 8770을 실행했다.
[ ] /health release/build/backend process를 확인했다.
[ ] canonical URL과 7개 주요 route를 smoke했다.
[ ] 다음 작업을 operational acceptance로 제한했다.
[ ] 실제 openable Backtest artifact를 확보하거나 부재를 명시했다.
[ ] data truth/security/V3K/performance_proved 경계를 유지했다.
[ ] 결함이 있을 때만 최소 patch와 focused test를 작성했다.
[ ] 전체 dashboard/build/accessibility/nonrelease/diff gate를 통과했다.
[ ] 보고서와 evidence가 최종 bundle build와 일치한다.
```

---

## 13. 최종 인계 문장

현재 v5.11.0은 merge·tag·자동화·접근성·responsive·Replay 상호작용 검증이 완료된 정식 기준선이다. 다음 작업은 새 기능 확대가 아니라 **실제 완료 Backtest artifact를 중심으로 한 v5.11.1 operational acceptance**다. 문제가 없으면 v5.11.0을 유지하고, 실제 사용자 상호작용에서 재현되는 결함만 최소 patch로 고친다. 투자 성능 증명과 V3K gate는 이 작업과 분리하며 각각 `performance_proved=false`, `3/6`을 유지한다.
