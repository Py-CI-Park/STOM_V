# V5 시리즈 — 대시보드 대개편 마스터플랜

- 작성: 2026-07-18
- 대상 브랜치: `feature/dashboard-hodo-20260717` (v4 누적 위) → v5 시리즈로 대개편
- 상위 문서: `2026-07-18_v4_dashboard_ux_redesign_master_plan.md`(§11 재검토 체크리스트 정본)
- 재검토 기준: `4479563cf18c93fcb4c92de76164255790c58c66` + `artifacts/review_live_3440.png` + 현 V4 소스/계약 테스트
- 현재 판정: **계획 보강 후 실행 가능(WATCH), 제품 요구 달성은 아직 BLOCK**

---

## 0. 목적 (사장님 원문 보존)

> 실제 대시보드를 통해 연구를 개선·확인하고, **실시간 연구·데이터를 시각화**하여 **더 좋은 브레인스토밍으로
> 수익 나는 조건식을 찾기 위함.** 울트라와이드(3440×1440)에서 한 화면에 많은 정보를 밀도 있게 보고,
> 프로세스가 단계별로 사용자와 함께 진행되며, 연구 히스토리·리포트가 체계적으로 관리되는 대시보드.

**v5 = 이 목적을 "전부" 달성하는 대개편**(v4 는 인프라·정확성 확보 단계였음을 인정).

---

## 1. 왜 지금까지 미완인가 (정직한 근본원인)

| 영역 | 왜 안 됐나 |
|---|---|
| **Live 시각 재배치(G6·G9·L1·L2·L7 등, 최우선)** | v4 에서 "correctness-first"를 과도 적용 — 세션 4401 버그·IA·보안(Reports)·카탈로그를 먼저 처리하고, **시각 레이아웃은 CSS 미디어쿼리로 컨테이너 폭만 조정하는 얕은 접근**을 했다. 실측 근본원인: `v4-research.jsx:241-304`의 `hero-col`이 **모든 차트·패널을 세로 스택**(Fitness 520px→Profit→Quality→Equity→Engine→6×Fold)이라, P4 가 사이드폭(352→480)을 넓히자 hero 컨테이너가 2782px 로 커지고 **그 안의 그래프가 폭에 맞춰 더 거대해졌다.** 스택→그리드 재구조화를 안 해 18,136px 스크롤이 남았다. |
| 스텝별 HTML 리포팅(G5)·Wiki(G8) | 범위가 커서 v4 에선 Reports 허브(열람 인프라)만 만들고 "스텝별 자동생성·탭이동·Wiki 체계"는 후속으로 미룸. |
| Lab/Workbench 통합(W1·W2) | 컴포넌트 이동·중복제거가 회귀 위험이 커 dual-mount+parity 선행이 필요 → v4 에선 라벨·구획만. |
| 단계별 탭 자동전환(L4·G11) | 신규 "단계별 뷰 아키텍처"가 필요해 미착수(P5 는 상태기계만). |

**교훈**: 사장님 최우선은 **시각/레이아웃**인데 인프라를 앞세워 후순위로 밀린 판단 실수. v5 는 **Live 밀도 재설계를 첫 릴리스(V5.0)** 로 못박는다.

---

## 2. 요청 전수 기록 · 상태 · 미진행 사유 · v5 배정

### 2.1 전역
| # | 사장님 요청 | 진행 | 미진행 사유 | v5 |
|---|---|---|---|---|
| G1 | Audit 불필요·제거 | 🟡 | 내비 제거·History 이전은 완료, `/ui/audit`·`?tab=audit` 호환/뒤로가기 계약 미봉인 | V5.P0 |
| G2 | 우측 패널 펼쳐 확대·글자 확대 | 🟡 | "펼쳐 확대" 인터랙션 미구현 | V5.0 |
| G3 | 버전 글자 크게+하이라이트 효과 | 🟡 | 배지만, 애니/효과버튼 없음 | V5.7 |
| G4 | 좌측 탭 확대·version 효과버튼 | 🟡 | 애니 효과버튼 미구현 | V5.0/V5.7 |
| G5 | 스텝별 HTML 리포팅·탭이동·결과예시 | 🟡 | 열람 허브만, 자동생성 없음 | V5.6 |
| G6 | 울트라와이드 전체 재배치 | ❌ | 스택→그리드 재구조화 안 함 | **V5.0** |
| G7 | HTML 보고 시스템 | 🟡 | 안전한 평면 HTML 뷰어만 존재. 연구/스텝 manifest·자동생성·링크 재작성 미완 | V5.6 |
| G8 | Wiki 문서 체계 | 🟡 | Lab에 제한적 읽기 전용 브라우저가 있으나 전체 corpus·표준 metadata·검색/연결망 미완 | V5.6 |
| G9 | 3440 그래프 과대·탭제목/버튼 확대 | ❌ | 컨테이너 폭만 조정 | **V5.0** |
| G10 | 연결 끊김 반복 | ✅ | — | 완료(P2) |
| G11 | 단계별 사용자와 함께 진행 | 🟡 | 상태기계만, 자동전환 없음 | V5.1 |

### 2.2 Live 탭
| # | 요청 | 진행 | 미진행 사유 | v5 |
|---|---|---|---|---|
| L1 | 한 화면 많은 정보 재배치 | ❌ | hero-col 세로 스택 유지 | **V5.0** |
| L2 | 글자만 블록(단계시간/차단/로그) ux | ❌ | _V4WorkflowStrip 텍스트 그대로 | **V5.0** |
| L3 | 사이클·현재세대 정리+애니메이션 | ❌ | 상단+우측 분산 유지 | V5.1 |
| L4 | 프로세스별 탭+자동전환+시각화 | ❌ | 뷰 아키텍처 미착수 | V5.1 |
| L5 | 백테엔진 상태 상단 상황판 | ❌ | EnginePanel 본문 매몰 | V5.1 |
| L6 | 백테 단계 조건식·분석 시각화 | ❌ | 미착수 | V5.2 |
| L7 | 불필요 프로세스 병합·버튼 축소 | ❌ | Fold 6개·버튼 과다 | **V5.0** |
| L8 | 게이트/채점기준 클릭 노출 | 🟡 | "설정·게이트" Fold(닫힘) 존재, 계층화 미흡 | V5.0 |
| L9 | History 상세 아키텍처 | 🟡 | stable research ID·cursor pagination은 존재, 통합 join/precedence/provenance/conflict 계약 미완 | V5.4 |
| L10 | 깜빡임 메시지 | ✅ | — | 완료(P2) |

### 2.3 Lab / Workbench / Context / Backtest
| # | 요청 | 진행 | 미진행 사유 | v5 |
|---|---|---|---|---|
| W1 | Lab → Live 백테 분석결과 통합 | ❌ | 회귀 위험, 미착수 | V5.5 |
| W2 | Lab 시간대/시총·워크벤치 중복 통합 | ❌ | 미착수 | V5.5 |
| W3 | 워크벤치=명예의전당만·개명 | 🟡 | "성과" 개명만 | V5.5 |
| W4 | Audit 불필요 | 🟡 | 내비 제거·거버넌스 이전 완료, legacy route/state migration 미완 | V5.P0 |
| W5 | 알파랩 추후 함께 | ❌ | UX 선행 합의와 달리 Alpha/Catalog가 조기 노출되고 P4 계약도 부분 구현 | V5.7 |
| W6 | Context 재검토(가독성·존재이유) | 🟡 | 격하만 | V5.5 |
| B1 | 백테 독립+강력 시각화(**D2: UX 개선 후**) | 🟡 | 독립·divid_mode O, Live UX 완료 뒤 gap-only 보강 필요 | **V5.3** |

**표 행 기준 집계: ✅ 2 · 🟡 14 · ❌ 12(총 28행).** G1/W4(Audit), G10/L10(연결)은 중복 추적 행이므로 고유 요구 집계로 오해하지 않는다.

---

## 3. 현재 Live 구조 실측 (재설계 근거)

`v4-research.jsx` `V4ResearchLive`:
- `.v4-research`(flex col): heading → ExportStatusBanner → **_V4WorkflowStrip**(단계시간·차단사유·로그 텍스트 = L2 문제) → `.v4-rlive`.
- `.v4-rlive`(grid `1fr 480px`):
  - **hero-col(세로 스택 = 18k px 근본원인)**: ① Fitness 곡선(V4HeroChart 2780×520) ② _V4Stats(4) ③ v4-two(Profit+Quality) ④ EquityOverlay ⑤ EnginePanel ⑥ 6×`_V4Fold`(Live상세·프로세스·Strategy·Analytics·진화분석·설정).
  - side-col(480px): CurrentGen·LoopCycle·Best/Winner·ConditionDiscovery·Population.
- 실측: 3440×1440 CSS viewport 캡처(`review_live_3440.png`, 이미지 4300×1800은 DPR 1.25): 첫 화면에서 **완전히 읽히는 주 분석 그래프는 Fitness 1개**, Profit·Quality는 하단 일부만 노출되고 우측 프로세스 다이어그램이 보인다. "여러 분석 그래프를 동시에 읽는다"는 요구는 미달이다. 전체 문서 높이는 18,136px(약 12.6화면).

---

## 4. V5 시리즈 로드맵

> 각 릴리스 = 독립 브랜치 → 개발 → 라인연결 merge. 각 단계 1920×1080·2560×1440·3440×1440 **CSS viewport 수치 검증**(DPR·zoom·fixture·storage 상태 고정, before/after DOM receipt 저장).

### V5.P0 — 계약 정합성 선행 게이트(짧은 교정, 기능 확장 아님)
- `/ui/evolution/verdict`→History 직접 계약 테스트를 유지하고 `/ui/audit`·`?tab=audit`·query/back-forward 호환 정책을 봉인한다.
- 현재 10개 목적지의 최종 owner map을 고정한다: 최상위는 Live·Backtest·Replay·History·성과·Reports 6개만 허용하고 Alpha/P4·Wiki는 해당 owner의 내부 섹션으로 배치한다.
- 현 Catalog를 **비정본 prototype**으로 명시·격하하고, P4 봉인 계약 복구 전 정식 P4 완료/뷰로 세지 않는다.
- 모든 V5.x에 target/non-target 파일, API/props/routes, fixture, focused tests, bundle hash, default-off flag, rollback 조건을 작성한 뒤 구현한다.
### V5.0 — Live 밀도 재설계 (최우선 · G6·G9·L1·L2·L7·L8·G2·G4)
- **JSX 소유권 재구조화 + 반응형 그래프 그리드**: CSS 크기 조절만 하지 않는다. `V4ResearchLive`의 hero/side 세로 스택을 상단 상황바·핵심 그래프 그리드·클릭 상세 drawer로 분해한다.
- 3440: 상단 KPI/프로세스 바 + 2~3열 그래프 그리드(Fitness·Profit·Quality·Equity 동시 노출), Fitness 높이 520→**최대 320 CSS px**.
- **텍스트 블록 → 상단 compact 상황 바**: `_V4WorkflowStrip`의 단계시간(미니 바 차트)·차단사유(배지 그룹)·로그(1줄+펼침)를 한 카드에 통합한다.
- **정보 계층화**: 6 Fold를 "요약 상시 + 상세 클릭"으로 정리하고 중복 패널을 병합한다. 게이트/채점기준은 현재 run의 유효값만 요약하고 정책 기본값과 구분한다.
- **타이포/패널 조작**: 본문 14px 이상, 패널 제목 16px 이상, 페이지 제목 22px 이상. 우측 패널은 접기/확장 가능하며 키보드와 포커스를 지원한다.
- **수용 기준**: clean storage·고정 running fixture·DPR 1·zoom 100%에서 검증한다. 3440×1440 첫 화면에 핵심 상황바와 Fitness·Profit·Quality·Equity가 각각 DOM rect 기준 **90% 이상 노출**, hero 높이 ≤320px, `scrollHeight / innerHeight ≤ 2.0`, 가로 overflow ≤3px. 2560×1440·1920×1080에서도 내용 손실·콘솔/page error 없이 검증하고 selector별 DOM metrics JSON을 캡처와 함께 저장한다.

### V5.1 — 프로세스 스테퍼 & 단계별 뷰 (L3·L4·L5·G11)
- 상단 **단일 프로세스 상황판**: 반복세대 사이클 + 현재세대 + 백테엔진 상태 통합, 애니메이션(진행 pulse).
- `latest.phase`·`current_step`·`phase_started_at`·`step_timings`·`backtest_progress`·`engine_state`를 pending/active/success/failure/skipped/retry로 변환하는 표를 봉인한다.
- 생성/백테/채점/부검 단계별 `tablist/tab/tabpanel`과 라이브 자동 포커스를 구현한다. user-pinned는 run/gen 변경 전까지 자동 이동이 덮지 않으며, idle/complete/stopping/error/legacy/reconnect fixture와 keyboard/focus/reduced-motion을 검증한다.

### V5.2 — Live 백테 단계 시각화 (L6)
- 백테 단계에서 매수·매도 조건식, source/run/generation, 엔진 진행률과 분석 결과를 함께 노출한다.
- 각 표시값의 authoritative WS/GET 필드·단위·fresh/stale/error 상태·owner를 field-source 표로 봉인한다. 기존 필드가 있으면 신규 polling·client 재계산·두 번째 publisher를 금지한다.

### V5.3 — 독립 Backtest gap-only 시각화 (B1 · D2)
- Live/울트라와이드 UX(V5.0~V5.2) 완료 직후 수행한다.
- 기존 `/bt/run`·job progress/cancel·결과/Monte Carlo·A/B·portfolio·`/bt/report`를 재사용하고 PyQt↔웹 field-level parity matrix에서 확인된 결손만 보강한다. 병렬 runner/report 경로를 만들지 않는다.
- mutation은 수동 확인·허용 저장소·demo inert·자동 호출 금지·origin/CSRF/auth 경계를 유지하며, 추가 차트마다 원천 endpoint·단위·empty/error·성능 예산을 명시한다.

### V5.4 — History 연구 아키텍처 고도화 (L9)
- 기존 `campaign:`/`loop_run:` stable ID와 signed cursor를 승계한다. 새로 만드는 것이 아니라 source precedence·join key·provenance·redaction·byte-identical 필드·complete/partial/missing/conflict 상태를 보강한다.
- 하나의 selected research ID가 조건식·평가·부검·홀드아웃·A/B·문서·커밋·거버넌스를 구동한다. 상세 요청은 abort/generation guard로 늦은 응답의 선택 덮어쓰기를 차단한다.

### V5.5 — IA 통합·정리 (W1·W2·W3·W6)
- Lab의 백테스트 증거/히트맵은 Live, Edge/변수 분석은 History로 dual-mount 후 field parity를 증명한다. 비교 기능은 History, 성과는 Hall of Fame 전용, Wiki는 Reports/History 내부 섹션으로 이동한다.
- Context는 developer drawer로 격하한다. route/query/localStorage/back-forward/keyboard migration과 feature-flag rollback을 통과한 뒤에만 Lab/Context 내비를 retire한다.
- Alpha/Catalog는 최상위 rail에서 제거하고 P4 계약 수용 전까지 내부 prototype으로만 표시한다.

### V5.6 — 리포팅·Wiki 체계 (G5·G7·G8)
- 전체+스텝별 상세 **HTML 자동 리포팅**(연구목적·일자·원인·결과·분석·결론 표준양식) + 탭 이동 + 결과 보고서 예시.
- 생성은 명시적 offline/manual writer에서만 수행하고 GET/WS 쓰기를 금지한다. allowlisted output에 atomic write하며 stable `research_id`/`step_id`, provenance·hash·missing/stale·trust, 크기/개수/pagination 한도를 manifest로 제공한다.
- sandbox/CSP를 완화하지 않고 parent React tab 또는 scriptless anchor를 사용하며 모든 내부 링크를 allowlisted `/reports/view`로 재작성한다.
- 기존 `/research_docs`와 Wiki 브라우저를 sidecar/index로 확장한다. 원문 Markdown/frontmatter는 byte-for-byte 불변으로 두고 검색·태그·연대기·관련 링크를 History/Reports에서 제공한다.

### V5.7 — P4 계약 교정·5뷰 완성 + 마감
- 현재 Catalog는 **부분 preview**다. 먼저 하드코딩된 비정본 DB와 서버 `COUNT(*)` 집계를 제거하고 `STOM_RESEARCH_ASSETS_DB`(기본값 없음), 표준 오류 envelope, schema/mtime 검증, `/research/assets|judgments|cells|clauses` 4엔드포인트를 봉인 계약과 일치시킨다.
- 연혁실·함정지도·절실험실·표본/출구은행의 정본 조회 뷰를 완성한다. B1 scorecard는 운용 개시·U-4·data-vessel 선행 증거가 없으면 **데이터 없음 골격만** 허용한다.
- Alpha/Catalog 조기 노출은 feature flag 또는 보조 메뉴로 격하하고, 6탭 IA와 V5.0~V5.6 수용 게이트 통과 후 정식 승격한다. version 효과버튼/애니메이션(G3)과 mainline 라인연결 반환 PR은 마지막에 수행한다.

---

## 5. 표준 양식 (G5·G8 반영)

**연구 보고서 표준**: 제목 · 연구목적 · 일자 · 가설/원인 · 방법 · 결과(데이터·차트) · 분석 · 결론 · 한계 · 히스토리 · 관련 문서 · 관련 커밋.
**Wiki 문서 표준**: 제목 · 목차 · 내용 · 결론 · 히스토리(변경이력) · 관련 문서 · 관련 커밋/작업. (기존 내용 보존·유사화, 원문 frontmatter 불변.)

---

## 6. 검증·안전 게이트 (전 릴리스 공통)
- 캡처에는 CSS viewport·DPR·zoom·fixture·localStorage/fold 상태를 기록한다. 3440×1440, 2560×1440, 1920×1080 실측 스크린샷과 DOM 수치(선택자별 90% 노출 여부·`scrollHeight/innerHeight`·가로 overflow)를 before/after JSON으로 저장한다.
- 셸 배선 파리티·deep-link·뒤로가기·키보드 tab/focus·44px target·contrast·비-hover 값 확인·`prefers-reduced-motion`·zero console/page error를 검증한다.
- 최종 IA는 Live·Backtest·Replay·History·성과·Reports 6개다. Lab/Context/Audit/Alpha/Catalog 내비 제거는 새 owner dual-mount와 field-level parity, redirect, default-off flag, rollback을 통과한 뒤 수행한다.
- History 비동기 상세는 abort 또는 generation guard로 선택 identity를 검증하고, 하나의 stable research ID가 모든 상세 패널을 구동해야 한다.
- Reports는 allowlisted root·path traversal 차단·sandbox+CSP·절대경로 비노출을 유지하면서 manual writer와 manifest 기반 탐색을 증명한다.
- P4는 mode=ro뿐 아니라 **정본 경로·무재집계·4 API·rdc-1 schema/error envelope·provenance·R1~R11** 전체를 계약 테스트로 검증한다.
- 공통 focused suite: `test_shell_wiring_parity.py`, `test_v4_ui_foundation.py`, `test_dashboard_phase_mapping.py`, `test_history_api.py`, `test_v4_lab_workbench_contract.py`, `test_reports_security.py`, `test_research_catalog_api.py` + 해당 Backtest 계약 테스트. JSX 변경 시 bundle/manifest hash를 재생성·검증한다.
- `performance_proved=false`·단일 발행기·읽기전용 조회·human approval/export 경계를 불변으로 유지한다.
- 각 V5.x 실행 문서는 owner, target/non-target 파일, 입력 계약, route/API/props, fixture, 테스트, evidence, feature flag 기본값, rollback trigger를 표로 채우지 않으면 구현을 시작하지 않는다.
- 각 릴리스는 독립 브랜치→라인연결 merge, 변경 파일 명시적 stage, 한국어 커밋을 사용한다.

---

## 7. 실행 순서 (의존성)
V5.P0(계약 정합) → V5.0(Live 밀도) → V5.1(스테퍼) → V5.2(Live 백테 단계) → **V5.3(독립 Backtest gap-only, D2)** → V5.4(History) → V5.5(IA 통합) → V5.6(리포팅/Wiki) → V5.7(P4·마감·PR).

**다음 착수: V5.P0 계약 정합성 교정 후 즉시 V5.0 Live 밀도 재설계**(기능 우회 없이 사장님 최우선 미완을 직접 해소).
