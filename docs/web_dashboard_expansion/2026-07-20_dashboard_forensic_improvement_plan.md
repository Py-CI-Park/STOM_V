# 대시보드 구조 정상화·강화 상세 계획

- 작성일: 2026-07-20
- 기반 감사: `2026-07-20_dashboard_forensic_audit_after_a8ba6c83.md`
- 현재 점수: **61/100**, 보고서 하위 시스템 **52/100**
- 목표: P0 무결성 BLOCK 해제 후 **85점**, 구조·성능·접근성·보고서 E2E 완료 후 **92점 이상**
- 원칙: **신규 시각화 추가보다 정본 계약과 측정 게이트를 먼저 고친다.**

## 1. 실행 원칙

1. 완료는 클래스·문구 존재가 아니라 **실데이터에서 사용자가 수행하는 행동**으로 판정한다.
2. 각 요구는 `요구 ID → owner → 정본 데이터 → UI 행동 → fixture → viewport/state → 증거` 한 행으로 관리한다.
3. 페이지 브랜치는 독립적으로 개발하되 공용 계약은 선행 브랜치에서 한 번만 정의한다.
4. CSS를 파일 끝에 추가해 덮는 방식은 금지한다. 기존 authoritative rule을 교체하고 obsolete rule을 삭제한다.
5. missing/pending/error/partial/stale은 서로 다른 상태다. 오류를 파생 결과나 demo로 가리지 않는다.
6. 보고서 수치는 profile/기간/단위가 같을 때만 비교한다. 독립 백테스트의 profit을 합산하지 않는다.
7. History·Reports 성능은 warm 단발값이 아니라 cold/warm 30회 p50/p95로 판정한다.
8. 1920/2560/3440뿐 아니라 1280/768/375, 200% zoom, dark/light, 긴 한글/ID를 검증한다.

## 2. 브랜치 구조

통합 기반 브랜치:

```text
loop/process-research-pipeline
└─ refactor/dashboard-forensic-hardening
   ├─ fix/dashboard-data-truth
   ├─ refactor/dashboard-context-shell
   ├─ refactor/dashboard-style-system
   ├─ perf/dashboard-history-index
   ├─ feat/dashboard-report-schema
   ├─ feat/dashboard-report-catalog
   ├─ refactor/dashboard-chart-system
   └─ test/dashboard-quality-gates
```

병합 순서:

1. `fix/dashboard-data-truth`
2. `refactor/dashboard-context-shell`
3. `refactor/dashboard-style-system`
4. `perf/dashboard-history-index`
5. `feat/dashboard-report-schema`
6. `feat/dashboard-report-catalog`
7. `refactor/dashboard-chart-system`
8. `test/dashboard-quality-gates`

각 페이지 브랜치는 이전 공용 계약 브랜치가 통합된 뒤 생성한다. 한 브랜치가 다른 페이지의 CSS나 데이터 계약을 우회 수정하지 않는다.

## 3. Phase 0 — 기준선 동결과 계측

### 목표

현재 동작을 추측이 아닌 재현 가능한 fixture와 수치로 동결한다.

### 작업

- 실제 상태 fixture: idle, running, stopping, complete, error, blocked, archive missing, archive stale
- 데이터 규모 fixture:
  - 현재: runs 527, generations 5,364, docs 930+
  - 성장: 현재의 2배
- 브라우저 측정 수집:
  - request count/bytes
  - FCP/LCP/INP/TBT/long task
  - DOM node 수
  - React commit 횟수
  - scrollWidth/clientWidth, panel bounding boxes
- 서버 `Server-Timing`: scan/query/transform/serialize
- 모든 탭 1920/2560/3440/1280/768/375 × dark/light 캡처
- current source에서 미정의 CSS variable, 동일 selector 중복, raw color inventory 생성

### 완료 게이트

- 기준선 JSON과 screenshot이 같은 bundle hash/run fixture를 가리킴
- console/page/request error가 별도 기록됨
- cold/warm 30회 측정 가능
- 사용자 요구 원장에 owner와 수용 조건 누락 0

## 4. Phase 1 — P0 데이터 정직성·무결성

### 4.1 상태 정본화

- 공용 `ResearchStatus`/`StageState` mapper 정의
- `complete`를 완료 단계와 엔진 완료 상태로 표시
- 자동 stage 선택과 사용자가 pin한 stage를 분리
- `idle/running/stopping/complete/error/blocked` exhaustive test

### 4.2 fallback 상태 분리

- authoritative panel 상태를 `missing | pending | ready | partial | stale | error`로 표준화
- 파생 generation 요약은 `derived` badge와 source 범위를 명시
- error일 때 오류·last good timestamp·retry를 먼저 표시
- empty 화면을 막기 위해 오류를 정상 데이터로 바꾸는 코드 제거

### 4.3 관찰성 안전성

- console.error 원본 호출을 `finally`로 보장
- 순환 객체 안전 직렬화
- backend ring handler idempotent lifespan 설치/해제
- secret/token/절대경로 redaction
- `/debug/logs` 세션 보호와 bounded pagination

### 완료 게이트

- 상태 enum 불일치 0
- authoritative error 은폐 0
- fixture별 화면 상태 golden test 통과
- logger 중복 레코드 0, 민감값 노출 0

## 5. Phase 2 — 전역 ResearchContext와 정보구조

### 목표

화면 제목과 본문이 항상 같은 연구/run/gen을 가리키게 한다.

### 데이터 계약

```text
ResearchContext {
  mode: live | archive,
  research_id,
  run_id,
  generation,
  profile_hash,
  time_range,
  source,
  observed_at
}
```

### 작업

- `ResearchContextProvider`, `BackendProvider`, `ThemeProvider`, `TelemetryProvider` 분리
- 탭 registry에 `owner`, `contextPolicy(consume|override|none)`, `loadPolicy`, `capability` 선언
- Live run selector와 History 선택을 동일 context에 연결
- History의 Compare/Tree/A-B/Heatmap/Funnel/Index에 research ID 전달
- Reports를 현재 research/run으로 필터하고 관련 보고서가 없으면 이유 표시
- Backtest가 독립 profile을 선택하면 shell context에 override를 명시
- 전역 CustomEvent/full reload 이동을 `navigate({tab, context})`로 교체

### 사용자 IA

```text
Observe       Live
Validate      Backtest
Investigate   History
Communicate   Reports
Benchmark     Performance
Auxiliary     Research Assets / Settings / Glossary / Context
```

현재 사용자 요청의 History→Reports→Performance 순서는 유지하되, 각 탭 헤더에 context breadcrumb를 표시한다.

### 완료 게이트

- 탭 이동 후 header/body context mismatch 0
- History 선택 변경 시 모든 하위 요청 identity 변경
- stale 이전 응답이 새 선택을 덮는 경우 0
- context 없는 독립 도구는 archive 표기를 숨김

## 6. Phase 3 — 스타일·레이아웃 시스템 재구축

### 목표

`styles.css + v4.css`의 수정 연대기를 예측 가능한 계층으로 바꾼다.

### 목표 파일 계층

```text
styles/
  tokens.css
  primitives.css
  shell.css
  features/live.css
  features/backtest.css
  features/history.css
  features/reports.css
  features/performance.css
  utilities.css
```

### 정본 토큰

- spacing: 4/8/12/16/24/32
- radius: 4/8/12
- type: 12/14/16/20/24
- control: 32/40/44
- chart height: 280/360/480
- text: primary/secondary/muted-AA/disabled/decorative
- border: subtle/default/strong/focus
- status: success/warning/danger/running/blocked

### 작업

- 미정의 `--line` 제거 또는 정본 정의
- 필수 8~12px 텍스트의 `--ink-3` 사용 제거
- `.v6-graphs`, `.v55-board-main`, panel 높이 중복 규칙 통합
- 720px 고정 셀 대신 shared row sizing + content min/max + 외부 page scroll
- 3/4열 버튼 의미를 실제 레이아웃과 일치시키거나 “compact/comfortable/dense” 모드로 교체
- container query/`auto-fit(minmax())` 사용
- Settings/Glossary prose는 readable max-width, chart/table은 full-bleed
- inline style을 variant class/primitive로 이동

### 완료 게이트

- 미정의 CSS variable 0
- 동일 feature selector의 상충 정의 0
- 전역 가로 overflow 0
- 375px touch target 44px
- 200% zoom에서 핵심 제어 가림 0
- 1920 첫 viewport에서 Live stage navigation 접근 가능

## 7. Phase 4 — History/Wiki/Reports 성능 구조 개선

### 7.1 `/runs?fields=slim`

- full payload 생성 후 projection 금지
- readonly aggregate SQL 1~2개로 직접 summary 생성
- consumer-driven typed slim schema
- Compare 필수 필드 계약 테스트

**예산:** current fixture 기준 cold p95 ≤250ms, warm ≤100ms, gzip wire ≤100KB, SQL ≤2.

### 7.2 History index/detail

- campaign/loop_run metadata materialized index
- source signature(path+mtime+size/schema) 기반 증분 갱신
- cache miss single-flight
- detail은 `(research_id, section, cursor)`에 필요한 데이터만 조회
- loop_run detail은 SQL pagination, campaign은 parsed companion cache

**예산:** index cold p95 ≤1s, warm ≤100ms; detail page p95 ≤250ms.

### 7.3 Research Records

- 목록 summary-only
- candidate rows는 선택 campaign detail에서 pagination
- 목록/detail이 동일 source snapshot 공유
- ETag/304와 변경 파일만 재파싱

### 7.4 Wiki

- Markdown 원문 전수 읽기 제거
- sidecar index에 id/title/category/mtime/size/hash 저장
- 서버 q/category/cursor pagination, O(1) id lookup
- frontend virtual list, DOM node ≤150

**예산:** 첫 100행 cold p95 ≤1s, warm ≤150ms, wire ≤150KB, 검색 long task <50ms.

### 7.5 Reports

- docs 전체 walk 대신 manifest/catalog index
- report metadata에 TOC 포함
- HTML 본문은 iframe에서 1회만 요청
- anchor 변경 시 iframe remount 금지
- content hash/ETag 적용

**예산:** 보고서 선택당 HTML GET 1회, anchor 이동 GET 0회, 200KB 문서 p95 ≤1s.

## 8. Phase 5 — 정본 연구 보고서 시스템

### 8.1 단일 스키마

```text
ReportEnvelope {
  schema_version,
  report_id,
  type,
  research_id,
  run_id,
  status,
  generated_at,
  generator,
  source_snapshots[],
  run_profile,
  cycles[],
  stages[],
  comparisons[],
  decision,
  limitations
}

Stage {
  stage_id,
  kind,
  sequence,
  status,
  parent_ids[],
  inputs[],
  outputs[],
  condition { name, text_ref, sha256, diff },
  metrics[] { name, value, unit, window, n },
  gates[] { rule, threshold, observed, pass, reason },
  evidence_refs[],
  ai_insight { model, prompt_id, text },
  human_insight { actor, at, decision, rationale }
}
```

모든 artifact는 `path/uri, sha256, bytes, schema_version, observed_at`을 가진다.

### 8.2 CanonicalReport adapter

LoopState의 다음 자료를 조인한다.

- runs config/status/timestamps
- generations parent/diff/hypothesis/condition text/hash
- prompts/model/token/cost
- equity/trades/backtest artifact
- candidate passports
- feedback/autopsy/meta
- evaluation manifest/gates/validation/OOS
- receipts/human decision/export boundary

값이 없으면 `not_run`, `unavailable`, `missing`, `failed`를 구분한다. best와 winner를 분리한다.

### 8.3 단일 출판 트랜잭션

1. staging에 JSON envelope, run HTML, stage HTML, assets 생성
2. schema/경로/HTML 안전 검사
3. broken link 0 검사
4. content/source hash 계산
5. manifest↔파일 전건 대조
6. 디렉터리 atomic replace
7. 이전 manifest에 없는 HTML은 “미등록/검증 불가” 격리

### 8.4 보고서 내부 구조

- Overview
- Research question & profile
- Cycle map
- Condition evolution
- Backtest
- Validation
- Comparisons
- AI insight
- Human decision
- Provenance & limitations
- Print appendix

정적 HTML은 scriptless anchor navigation과 연속 section을 정본으로 한다. 화면에서는 sticky TOC와 CSS-only section view를 제공할 수 있으나 인쇄 시 모두 펼친다. React Reports 탭은 JSON envelope를 소비해 실제 tab/drill-down/compare를 제공한다.

### 8.5 시각화 교정

- 독립 후보 profit 합산 제거
- MDD-score: 좌상단=저위험·고성과로 교정
- score/MDD/profit small multiples 분리
- cycle/generation lineage DAG
- equity+drawdown
- monthly/regime heatmap
- trade distribution/holding/slippage sensitivity
- baseline/previous/best/winner 직접 라벨
- 표본수·기간·단위·threshold·confidence·대체표 필수

### 완료 게이트

- 잘못된 집계/축 설명 0
- broken link 0
- manifest/hash mismatch 0
- synthetic research 1건의 cycle→generation→backtest→validation→decision E2E
- 1920/1280/375, keyboard, screen reader, grayscale print-to-PDF 통과
- offline standalone 재열람 가능

## 9. Phase 6 — 공통 차트 시스템과 프로세스별 보강

### 9.1 공통 차트 계약

```text
ChartFrame
  title / question
  metric + unit
  time range + sample size + freshness
  benchmark + thresholds
  ChartSpec
  legend / tooltip / linked selection
  empty / loading / partial / stale / error
  accessible data table
  export PNG / CSV / context
```

현재 Canvas/SVG/lightweight-charts를 즉시 제거하지 않는다. 먼저 공통 adapter를 만들고 신규 차트부터 같은 계약을 사용한다. 라이브러리를 추가할 경우 offline bundle과 tree-shaking 가능한 ECharts Core를 별도 승인 후 검토한다.

### 9.2 Live

- linked crosshair/brush로 fitness-profit-MDD-quality 동기화
- 현재/최고/baseline/gate 직접 표기
- uncertainty/sample/freshness 슬롯
- compact 첫 viewport와 상세 matrix 분리

### 9.3 Backtest

- cost/slippage/commission sensitivity
- IS/OOS/walk-forward cohort
- regime/month/year heatmap
- bootstrap confidence와 parameter stability
- 핵심 summary 우선, 상세 차트 IntersectionObserver mount
- 시계열당 기본 ≤1,000 points, 확대 시 detail fetch

### 9.4 History

- 선택 research 기반 lineage/compare
- profile hash mismatch 표시와 delta 금지
- 세대/조건식 diff/결과를 같은 cursor로 탐색

### 9.5 Performance

- 기간·profile 정규화
- baseline 및 confidence interval
- OOS cohort/생존 편향 경고
- human/AI 후보의 비교 가능한 universe 명시

### 9.6 Glossary·Settings

- 용어 검색/anchor/현재 패널 딥링크
- density/contrast/reduced-motion 설정을 정본 token에 즉시 반영
- 설정 export/import와 reset scope 명시

## 10. Phase 7 — 자동 품질 게이트

### 코드·계약

- status exhaustive test
- ResearchContext owner/consumer contract
- stale request race
- slim response schema
- report schema/golden/hash/link
- source artifact drift
- undefined CSS variable/duplicate selector/raw color

### 실제 브라우저

- 탭 keyboard Arrow/Home/End, focus retention
- Dialog focus trap/restore
- History selection→all details identity
- Reports current run filter→single HTML request→TOC anchor network 0
- 375/768/1280/1920/2560/3440, 200% zoom
- dark/light/reduced-motion/long CJK
- empty/loading/partial/stale/error/blocked
- console/page/request errors 0

### 성능

- current와 2× fixture에서 cold/warm 30회
- p50/p95, query count, bytes, long task, DOM nodes, React commits
- 새 run/report/doc 생성 후 cache invalidation 검증

### 릴리스 증거

각 릴리스는 다음을 같은 bundle hash로 보관한다.

- acceptance matrix
- focused test 결과
- API timing JSON
- viewport geometry JSON
- screenshot set
- console/network transcript
- report manifest/link/hash receipt

## 11. 우선순위와 예상 점수

| 단계 | 핵심 결과 | 목표 점수 |
|---|---|---:|
| 현재 | 기능 풍부, 구조·cold 성능·보고서 무결성 BLOCK | 61 |
| Phase 0~1 | 상태·오류·관찰성 정직성 회복 | 68 |
| Phase 2~3 | context/IA/CSS 정상화 | 76 |
| Phase 4 | History/Wiki/Reports 성능 budget 달성 | 82 |
| Phase 5 | 정본 보고서 E2E와 무결성 | 87 |
| Phase 6~7 | 공통 차트·접근성·자동 gate | 92+ |

점수는 작업량이나 커밋 수가 아니라 승인 게이트를 실제로 통과한 항목만 반영한다.

## 12. 즉시 금지할 개발 방식

- 버전명 주석을 붙여 CSS 파일 끝에 같은 selector를 추가하는 방식
- 화면 문구만 통합하고 data/context props를 연결하지 않는 방식
- `status !== ok` 전체를 파생 데이터로 대체하는 방식
- cold-path를 고치지 않고 timeout/TTL만 늘리는 방식
- 파일명 regex와 디렉터리 prefix를 정본 metadata로 사용하는 방식
- 독립 백테스트 수익을 합산해 누적 성과로 표현하는 방식
- 실제 viewport/fixture 없이 클래스 존재만으로 UX 완료를 선언하는 방식
- 페이지별 브랜치가 공용 shell/CSS/API 계약을 각자 수정하는 방식

## 13. 완료 정의

대시보드 강화 작업은 다음이 모두 충족될 때 완료다.

1. 정본 상태와 화면 상태 불일치 0
2. 전역 research/run/gen context mismatch 0
3. History/Wiki/Reports cold p95 budget 통과
4. report schema·manifest·파일·링크·hash 전건 일치
5. 다중 cycle→조건식→백테스트→검증→결론 보고서 E2E
6. 핵심 시각화의 단위·기간·표본·threshold·baseline·대체표 완비
7. 375~3440과 200% zoom overflow/겹침 0
8. keyboard/contrast/reduced-motion/print gate 통과
9. 신규 기능이 append-only CSS override 없이 owner 컴포넌트에 구현됨
10. 사용자 요구 원장의 각 행이 동일 bundle hash의 실제 증거를 가짐
