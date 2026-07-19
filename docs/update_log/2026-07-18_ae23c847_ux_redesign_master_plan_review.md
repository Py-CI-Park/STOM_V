# ae23c847 V4 UX 재설계 마스터 플랜 상세 검토 보고서

- 작성일: 2026-07-18
- 검토 커밋: `ae23c8474c979e7b21c4b6552a300301088efef6`
- 대상: `docs/web_dashboard_expansion/2026-07-18_v4_dashboard_ux_redesign_master_plan.md`
- 전략 방향 판정: **WATCH — 방향은 유효하나 사실·경계 교정 필요**
- 실행 준비도 판정: **BLOCK / REJECT — 현재 문서만으로 단계 구현 승인 불가**

## 1. 요약

마스터 플랜은 사용자 요청을 R-ID로 추적하고, 3440×1440 레이아웃, Live 단계 동행, History 마스터-디테일, Reports/Wiki, P4 후속 연계를 하나의 방향으로 정리했다. D1~D4 결정도 최종 6탭과 P1~P8 순서에 대체로 반영됐다.

그러나 현재 코드와 대조하면 Audit의 역할과 Backtest 구현 상태를 잘못 진단한다. 기존 승인 차단 결함도 P1 이전 교정 단계에 포함하지 않았다. Reports/Wiki의 보안·서빙 계약, 탭 제거 시 route/state 호환, 단계별 산출물·테스트·rollback이 정의되지 않아 실행자가 추측 없이 구현할 수 없다.

## 2. 강점

| 항목 | 평가 |
|---|---|
| 요청 추적 | R01~R52로 요구와 설계 절을 연결해 누락 확인이 쉬움 |
| IA 방향 | Live/Backtest/Replay/History/성과/Reports의 연구 흐름은 이해 가능 |
| 울트라와이드 | 1080p·1440p·3440×1440 검증을 게이트로 제시 |
| 프로세스 스테퍼 | 현재 `current_step`, `step_timings`, `backtest_progress`, `engine_state` 계약과 방향이 맞음 |
| 데이터 무결성 원칙 | `performance_proved=false`, P4 SELECT-only, 단일 발행기 보존을 명시 |
| 가역성 | 단계별 커밋과 단계별 검증 원칙을 제시 |
| 지식 관리 | 보고서와 Wiki 형식, 관련 문서·커밋 연결 요구가 실사용 목적에 부합 |

## 3. 승인 차단 발견사항

### 3.1 Audit 제거 근거가 현재 코드와 충돌 — Blocker

플랜 §5.1은 “실거래·Export가 없는 현 연구 단계”라 결정 이벤트가 없다고 보고 Audit 탭을 제거하면서 안전 문구만 상단에 남긴다. 그러나 현재 시스템은 다음 계약을 가진다.

- `app.py:11-16`: WS `final_approval`이 `export_winner(...)`를 호출하는 human approval/export 경계다.
- `v4-audit.jsx:1-3`, `44-100`: `/decisions` append-only 결정 원장을 조회·필터한다.
- `dashboard-pages.jsx:308-355`, `547-554`: `/record_decision` append-only 기록과 `final_approval` export를 서로 다른 거버넌스 단계로 명시한다.

따라서 “Export가 없고 원장이 사실상 불필요”라는 진단은 사실과 다르다. 탭을 제거할 수는 있지만 `AuditDecisionTrace`와 `VerdictPanel`의 결정 근거·기록·export 경계를 History/Reports의 Governance 섹션 또는 전역 drawer로 완전 이전해야 한다. 안전 strip만 남기는 것은 기능·감사 가능성 손실이다.
특히 실제 export 뒤 append-only 결정을 기록하고 다시 열람하는 동선까지 보존해야 한다. Audit 내비게이션을 없애기 전에 freeze/regime/portfolio/verdict/decision 기능을 새 위치로 옮기고, candidate/evidence binding·capability check·export governance가 동일하게 유지됨을 보안·파리티 테스트로 증명해야 한다.

### 3.2 P5 Backtest가 이미 구현된 범위를 신규 이식으로 계획 — High

플랜 §2.5, §5.1, §8 P5는 python GUI 백테스트를 웹으로 이식하고 `/bt` 잡과 강력한 시각화를 새로 구축하는 것처럼 기술한다. 현재 코드는 이미 다음을 제공한다.

- `backtest_api.py:1149-1153`: `POST /bt/run` 잡 실행.
- `bt-tab-run.jsx:102-176`, `266-300`: 데이터 범위, 잡 이력, WS/poll 추적, 실행, 취소, HTML 보고서.
- `backtest.jsx:1-20`: “GUI 백테스트의 웹 이관”과 결과 분석 계약을 명시.
- `bt-result-area.jsx:28-95`: 메트릭·차트·Monte Carlo.
- `bt-tab-analysis.jsx`: overlay, A/B, 진화 세대, portfolio 분석.

그러므로 P5는 “이식”이 아니라 **현 기능 inventory → python GUI와 field-level parity matrix → 실제 결손만 보강**으로 다시 정의해야 한다. 그렇지 않으면 이미 존재하는 실행·시각화 계층을 중복 구현하거나 회귀시킬 가능성이 높다.
기존 `/bt/report`도 Reports 허브에 통합할 기존 자산이다. 별도 보고 시스템을 병렬로 만들기보다 현재 report action과 job taxonomy를 유지한 채 공통 index에 연결해야 한다.

### 3.3 기존 BLOCK 결함을 로드맵이 누락 — High

본 브랜치의 직전 검토에서 확인된 다음 문제는 UX 개편 전에 해결돼야 한다.

- Alpha `measured_ok`를 `gate_passed`로 오표시.
- Alpha soft-error 계약 미완료.
- `/runs` 최초 호출자 timeout과 종료 refresh stale.
- 파리티 주석 import 오인과 V4 runtime 안전 검증 부족.
- 정적 query의 단순 `v=` 지문 판정.

하지만 P1은 연결 debounce·타이포·버전 배지·탭 강조만 포함한다. 잘못된 연구 수치와 신뢰성 결함을 남긴 채 IA·시각화를 확장하면 오류가 더 넓게 전파된다. **P0 Correctness & Safety Remediation**을 추가하고 위 문제를 닫은 뒤 P1에 진입해야 한다.

### 3.4 읽기 전용 원칙과 Backtest mutation 경계가 불명확 — High

문서 상단은 “읽기 전용 조회 불변”을 전역 원칙처럼 적지만 Backtest는 명시적 mutation을 가진다.

- `POST /bt/run`: 잡 생성.
- `POST /bt/job/cancel`, `/bt/job/meta`: 실행·메타 상태 변경.
- `POST /bt/strategy`, `/bt/strategy/delete`: 전략 저장소 변경.

P4 `/research/*` SELECT-only와 일반 대시보드의 수동 mutation을 구분해야 한다. 각 POST에 대해 수동 action, 확인 절차, 허용 저장소, 자동 호출 금지, demo/reference inert, CSRF/origin/auth 경계를 플랜에 명시해야 한다.

### 3.5 Reports/Wiki 서빙·보안 계약 부재 — High

§6은 정적 HTML을 iframe/링크로 연다고만 한다. 다음이 없다.

- 허용 report root와 path traversal 방지.
- iframe `sandbox`/CSP 및 script 허용 여부.
- 생성 HTML의 escape/sanitization과 신뢰 등급.
- 외부 URL·`file://`·절대경로 차단.
- report index schema, stable ID, provenance/hash, missing/stale 상태.
- 검색 API의 범위·pagination·encoding·대형 문서 제한.
- 기존 문서를 수정하지 않는다는 원칙과 frontmatter 추가 방식의 충돌 해결.

보고서가 연구 결과·조건식·로그를 포함하므로 이 계약 없이 iframe 구현을 시작해서는 안 된다.
현재 연구 문서는 allowlisted root와 inert `<pre>` 렌더링으로 제한되지만, 재사용 대상으로 든 `alpha_lab/reporting/build_html.py` 산출물에는 inline JavaScript가 있다. 이를 same-origin iframe으로 열면 대시보드 권한으로 mutation endpoint를 호출할 수 있으므로 “읽기 전용 화면”이라는 설명만으로 안전하지 않다.

### 3.6 단계·번호·연계 설명이 서로 충돌 — Medium

- §7 line 215는 UX `P1~P6` 후 P4 카탈로그를 `P7`이라고 한다.
- §8과 §9는 UX `P1~P7` 후 Alpha P4를 `P8`이라고 한다.
- §7 line 213은 현재 마스터 플랜과 “별도 문서”를 같은 이름으로 적어 사실상 자기참조한다.

정본 순서를 하나로 고정해야 한다. 현재 D4 문맥에 맞는 표현은 `UX-P1~UX-P7 완료 후 UX-P8(Alpha Catalog P4)`다.

### 3.7 기존 P1~P7 문서군과 단계명 충돌 — Medium

`docs/web_dashboard_expansion/`에는 이미 `PROG_P1_TAB_HOMES.md`, `PROG_P2_SIDEBAR_DEDUP.md`, `PROG_P3_IA_DETAILS.md`, `PROG_P4_PIPELINE_CONSOLIDATION.md`, `PROG_P6_*`, `PROG_P7_*`가 존재한다. 새 플랜이 P1~P8을 재사용하면 커밋·보고서·테스트에서 어느 P단계를 뜻하는지 모호하다.

새 단계는 `UXR-P0`~`UXR-P8`처럼 별도 namespace를 사용해야 한다.

### 3.8 IA 제거·이전의 route/state/data migration 계약 부재 — Medium

Audit·Context·Lab 제거와 Bench 축소에는 다음이 필요하지만 플랜에 없다.

- 기존 `/ui/audit`, `/ui/lab`, `/ui/context`, localStorage tab key의 redirect/fallback.
- deep-link와 브라우저 뒤로가기 호환.
- 각 기존 컴포넌트의 새 owner와 field-level parity 표.
- `test_shell_wiring_parity.py` whitelist 변경 기준.
- V4 번들 재생성 및 manifest hash 검증.
- 이전 완료 전 기존 탭 유지 또는 feature flag에 의한 rollback.

단순 탭 제거로 구현하면 기능은 번들에 남아도 사용자가 접근하지 못하는 과거 회귀가 반복될 수 있다.
또한 현재 P2는 Lab/Audit/Context를 먼저 제거하지만 목적지는 P4 Live, P6 History, P7 Reports에서 뒤늦게 구축된다. 삭제를 목적지보다 앞세우지 말고, 새 owner에 dual-mount한 뒤 field/interaction/error-state parity가 통과한 경우에만 기존 내비게이션을 retire해야 한다.

### 3.9 단계별 완료 조건이 너무 포괄적 — High

§8의 공통 게이트는 방향만 있고 각 단계의 산출물·명령·수치 기준이 없다. 특히 다음이 필요하다.

- 정확한 대상 파일과 비대상 범위.
- API/props/route 계약.
- before/after 스크린샷과 viewport별 허용 overflow.
- 연결 깜빡임의 측정 기준과 false-offline 허용치.
- 자동 탭 전환 시 사용자 수동 선택을 덮지 않는 규칙.
- keyboard/focus/reduced-motion/accessibility 기준.
- bundle build 명령과 focused test 목록.
- rollback 조건과 단계별 feature flag.

현재 상태는 전략 문서로는 사용할 수 있으나 실행 계획으로는 추측이 많이 필요하다.

### 3.10 Live 스테퍼 상태기계 계약 부재 — High

현재 backend에는 `latest.phase`, `current_step`, `phase_started_at`, `step_timings`, `backtest_progress`, `engine_state`가 있지만 플랜은 Generate→Backtest→Score→Autopsy→Iterate라는 표시 이름만 제시한다. 모든 raw phase의 pending/active/success/failure/skipped/retry 매핑, idle/complete/stopping/legacy snapshot 처리, blocker·로그·시간의 원천 필드, reconnect/replay 동작이 없다.

자동 전환도 follow-live와 user-pinned 상태를 분리하고, 사용자가 다른 단계를 보는 동안 강제 이동하지 않아야 한다. backend 단일 발행기를 추가하지 않고 현재 계약으로 가능한 범위와 필요한 계약 확장을 표로 봉인해야 한다.

### 3.11 History 데이터 계약이 “모든 정보” 수준에 머묾 — High

`condition_history_v1`, `loop_runs.db`, 문서 링크를 결합하려면 stable research/run/series ID, join key, source precedence, provenance, pagination, redaction, partial/missing/conflict 상태가 필요하다. 현재 `/history/index`와 `/history/detail` 계약만으로 세대·조건식·A/B·홀드아웃·문서를 임의 결합하면 의미가 달라질 수 있다.

P6 전에 endpoint/query/response schema와 byte-identical 필드, presentation-only 변환, complete/partial/missing/conflict fixture를 정의해야 한다.

### 3.12 P8이 봉인된 P4 계약과 5뷰 요구를 충분히 승계하지 않음 — High

플랜은 “카탈로그 DB·4엔드포인트·5뷰”로만 축약하고 실제로는 판정카드·함정지도·절실험실·출구은행 네 개만 열거한다. `2026-07-12_dashboard_data_contract.md`의 mode=ro, 무집계, 단일 DB, schema/mtime 검사, 오류 envelope, 원문 딱지와 acceptance checks 및 짝 문서 `2026-07-12_dashboard_view_specs.md`를 normative input으로 지정해야 한다.

누락된 다섯 번째 뷰는 gated B1 live scorecard이며 data-vessel/U-4 선행조건과 별도 승인 경계가 있다. 현 `alpha_router`와 `research_router`의 소유권·경로 충돌도 재조사하고, 카탈로그 경로를 파일 서빙 URL로 바꾸지 않아야 한다.

## 4. 추가 보완사항

| 심각도 | 항목 | 보완 |
|---|---|---|
| Medium | 연결 debounce가 실제 장애를 가릴 수 있음 | 먼저 disconnect 빈도·원인·ping/pong 증거를 수집하고 UI grace 적용 |
| Medium | 자동 단계 전환이 사용자의 분석을 방해할 수 있음 | follow-live 토글, 수동 이탈 시 자동전환 pause, 새 단계 배지 제공 |
| Medium | `performance_proved=false` 표시 위치 불명확 | 모든 연구 카드·보고서·export 근처에 source field 기반 표시 |
| Medium | 문서 Wiki가 source 문서를 수정할 위험 | 원문 불변, 별도 sidecar/index DB 또는 generated manifest 사용 |
| Low | 요청 수 집계 오류 | 표에는 31행, 두 중복쌍 통합 후 29개 고유 요청인데 “그 외 24개”로 기술 |
| Low | 2.5~3일 추정 근거 없음 | 작업 분해·인력·검증 비용 근거 없으면 기간 제거 |

## 5. 권장 재구성

| 새 단계 | 필수 범위 | 종료 증거 |
|---|---|---|
| **UXR-P0 정확성·안전** | 기존 Alpha/V4 BLOCK 전부 교정 | 의미 fixture, 캐시 동작, runtime 안전 테스트 통과 |
| **UXR-P1 관측·계약 동결** | WS disconnect 계측, 현 탭/route/field inventory, Backtest parity matrix | current-state manifest와 baseline screenshots |
| **UXR-P2 IA migration** | Audit 거버넌스 이전, Context 개발자 메뉴, Lab field-level 이전, redirects | route·field parity 및 rollback flag |
| **UXR-P3 반응형·타이포** | 1080p/1440p/3440 레이아웃, density, version badge | overflow·접근성·스크린샷 게이트 |
| **UXR-P4 Live 스테퍼** | 현재 contract 기반 stepper, follow-live 정책, reduced motion | phase fixture·browser 시나리오 |
| **UXR-P5 Backtest gap 보강** | 기존 웹 기능 inventory 후 실제 GUI 결손만 구현 | GUI↔웹 parity matrix와 수동 mutation gate |
| **UXR-P6 History** | stable research ID, master-detail, Lab 분석 이전 | 데이터 owner·empty/error/stale 계약 |
| **UXR-P7 Reports/Wiki** | safe report root, CSP/sandbox, index schema, provenance | traversal/XSS/대형문서/누락 테스트 |
| **UXR-P8 Alpha P4** | 봉인된 `/research/*` 계약과 5뷰 | catalog schema·SELECT-only·원문 대조 |

## 6. 실행 승인 전 필수 문서 수정

1. Audit의 실제 export/decision 역할을 정정하고 거버넌스 UI의 새 위치를 확정한다.
2. P5를 “GUI 이식”에서 “현 웹 구현 inventory와 gap-only 보강”으로 변경한다.
3. UXR-P0을 추가해 현재 BLOCK을 먼저 닫는다.
4. read-only 범위를 P4 research API로 한정하고 Backtest POST별 수동 mutation 경계를 적는다.
5. Reports/Wiki 보안·경로·index·provenance 계약을 추가한다.
6. P1~P8 번호 충돌과 §7/§8/§9 순서 불일치를 고친다.
7. 탭 제거의 route/state/field migration 표와 rollback 전략을 추가한다.
8. 각 단계에 파일·API·acceptance test·브라우저 시나리오·build 명령을 명시한다.
9. Live 스테퍼의 raw phase→표시 상태기계, fallback, follow-live/user-pinned, reconnect·terminal 규칙을 봉인한다.
10. History의 stable identity·join precedence·pagination·redaction·partial/conflict 응답 계약을 추가한다.
11. P8의 두 2026-07-12 계약 문서를 normative input으로 지정하고 다섯 번째 B1 뷰와 별도 승인 선행조건을 명시한다.

## 7. 최종 판정

이 문서는 사용자 의도와 UX 방향을 잘 모은 **상위 전략 초안**으로는 가치가 있다. 그러나 현재 구현 사실을 일부 잘못 전제하고, 승인·감사·Backtest mutation·Reports 보안 같은 load-bearing 경계를 충분히 정의하지 않았다. 따라서 `ae23c847`을 실행 기준 마스터 플랜으로 승인할 수 없다.

- 전략 방향: **WATCH**
- 구현 착수 기준: **BLOCK / REJECT**
- 권고: 위 필수 수정 후 실행 계획 재검토
