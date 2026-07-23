# Dashboard v5.10 P1–P3 UX/UI 고도화 실행 계획 및 재검토 보고서

## 1. 문서 목적

이 문서는 v5.9.1 재감사에서 확인된 누락과 사용자 요청을 단일 실행 기준으로 고정한다. 목표는 기능 수를 늘리는 것이 아니라 데이터 정직성, 정보 위계, 차트 가독성, 페이지 간 일관성, 접근성, 성능을 함께 개선해 1차 90점 이상, 최종 95점 이상의 대시보드를 만드는 것이다.

- 기준 브랜치: `loop/process-research-pipeline`
- 기준 커밋: `a805d527` (`V2UC-Dashboard-v5.9.1`)
- 계획 문서 커밋 후 개발 브랜치: `feature/dashboard-v5.10-p1-p3-ux-quality`
- 정본 프런트엔드: V4 shell (`dashboard-v4-shell.jsx`, `v4-*.jsx`)
- 범위: 대시보드 표시, 읽기 전용 연구 조회, 기존 백테스트·Replay 제어와 검증
- 제외: 브로커 로그인, 실주문, V3K 승인 상태 변경, 보호 DB·연구 결과 변조, 존재하지 않는 지표 추정

## 2. 재감사 결론과 기준점

v5.9.1은 Live 조건식 가독성, 공통 결과 렌더러, 보고서 템플릿, Replay 기본 동작을 개선했지만 95점 완료 보고서의 일부 주장이 실제 구현보다 앞섰다. 특히 3440px에서 구형 다열 CSS가 다시 적용되고, 연결된 Backtest 미선택 화면이 `__demo__` 합성 수익 결과를 자동 표시하며, History 코드 높이와 Reports 목록 폭 변경은 실제 대상 요소에 적용되지 않았다.

따라서 이전 95점은 최종 품질 점수로 유지하지 않는다. 재감사 기준 총점은 57점이며, 이 문서의 점수는 구현 후 직접 측정한 증거로만 갱신한다.

| 영역 | 재감사 점수 | 핵심 감점 원인 |
|---|---:|---|
| 공통 결과 구조 | 72 | 결과 렌더러는 공유됐지만 source capability가 불완전 |
| 전폭·반응형 레이아웃 | 61 | 2000/3000px 구형 `.bt-result-flow` 다열 규칙 |
| 차트 일관성·접근성 | 48 | 원자료·키보드·SVG 접근성 계약 미완성 |
| 성능·대규모 DOM | 67 | 14화면 이상 결과 흐름, 진단 전량 mount |
| Reports·템플릿 | 64 | flex 폭 규칙 무효, 레거시 전수 분류 미완성 |
| 정보 위계·시각 UX | 70 | MDD 위치, Live 중복, 채점 카드 배치 잔여 |
| 증거·주장 정확성 | 35 | v5.9 보고서와 실제 버전·높이·데모 동작 불일치 |
| 데이터 정직성 | 45 | 연결된 미선택 상태에서 합성 결과 자동 표시 |
| **총점** | **57** | 직접 코드·브라우저 재감사 기준 |

## 3. UX/UI 설계 원칙

1. 핵심 차트는 한 행 전체 폭으로 표시한다. 화면 길이는 차트를 다시 작게 만들어 해결하지 않는다.
2. 요약 카드는 2–4열을 허용하되 같은 역할의 카드는 같은 높이와 간격을 사용한다.
3. 결과 순서는 요약 → 수익 → MDD·위험 → 거래 분포 → 진단 → 출처·증거로 고정한다.
4. 긴 화면은 sticky 목차, section jump, 기본 핵심 노출, 진단 lazy mount로 해결한다.
5. 데이터가 없으면 빈 상태와 이유를 표시한다. 합성·추정·0 채움으로 실제 결과처럼 보이게 하지 않는다.
6. 동일 run/job/gen은 Live·Backtest·History에서 같은 단위·범례·수치·상태를 사용한다.
7. 모든 고급 분석에는 목적, 해석법, 데이터 출처, 사용 가능 조건을 표시한다.
8. 시각 효과보다 읽기 순서, 대비, 키보드 흐름, 표 대체자료, 렌더 비용을 우선한다.

## 4. P1 — 기능 추가보다 먼저 해결할 구조·정직성 문제

| 순서 | 작업 | 현재 원인·대상 | 구현 방법 | 완료 증거 |
|---:|---|---|---|---|
| 0 | 조회 경로 강제 read-only | 일부 dashboard GET helper가 기본 `LoopState()`를 열어 schema/WAL 생성 가능 | 조회 helper를 `readonly=True`/SQLite `mode=ro`로 통일하고 DB 부재 시 생성 금지 | GET 전후 DB hash·WAL/SHM·state directory 불변, DB 부재 fixture에서 파일 생성 없음 |
| 1 | 연결 Backtest `__demo__` 자동 결과 제거 | `bt-tab-root.jsx`의 `showDemoResult`, `effectiveJobId`; `backtest_api.py`의 명시적 demo sentinel은 유지 가능 | 연결+미선택은 honest empty state, URL/명시적 Demo 모드에서만 합성 데이터 허용 | 정적 계약 테스트, 연결 브라우저 네트워크에 `job_id=__demo__` 자동 요청 없음, 빈 상태 문구 |
| 2 | 초광폭 구형 다열 규칙 제거 | `v4.css` 2000/3000px `.bt-result-flow` override | 결과 section parent를 전 해상도 1열로 고정하고 요약 카드의 내부 grid만 반응형 유지 | 1920·2560·3440에서 section≈container, 핵심 chart≈section computed width |
| 3 | Live/History result capability 계약 | `bt-result-area.jsx`의 `loadMc`·`onBrush`가 job 전용인데 UI는 공통 노출 | `sourceCapabilities` 또는 source adapter에 `range`, `monteCarlo`, `compare`, 이유를 명시하고 지원 기능만 활성화 | job 및 run/gen에서 버튼 상태·설명·요청 endpoint가 계약과 일치 |
| 4 | 실제 History 코드 블록 확대 | 실제 조건식은 `rp-utils.jsx`의 `.rp-code-block`; 기존 신규 클래스는 평가 영역을 감쌈 | History scope에서 buy/sell code viewport 440px 이상, wrap/scroll/복사 유지 | History 실제 buy/sell `pre.rp-code-block` computed height ≥440px |
| 5 | Reports 목록 폭 수정 | `.v4-reports-body`는 flex인데 뒤 규칙은 `grid-template-columns`만 설정 | catalog에 `flex: 0 1 460px`, `min-width:360px`; 본문 `min-width:0`; 모바일 1열 | desktop catalog 360–460px, 모바일 전체 폭, iframe 잘림 없음 |
| 6 | Hall을 전체 AI Backtest 카탈로그로 재설계 | `_hall_of_fame_payload(ai_limit=30)`가 gate+흑자만 상위 30개 전송 | 인간 명예의 전당과 AI 연구 카탈로그를 분리하고 전체 세대를 상태·결과 필터, 정렬, 페이지네이션으로 제공 | 성공·실패·손실·no-trade 포함 fixture/API/UI 테스트; total·page 정보 |
| 7 | Replay SQL N+1 제거·실규모 프로파일 | `replay_engine.py`가 심볼마다 schema/복수 query를 반복하고 불필요 query 포함 | schema 1회, 집합 query·필요 필드 projection·bounded cache, 읽기 전용 유지 | latest/top-gainer/stocks/first-frame/seek/full-day의 p50·p95와 query count 기록 |

### P1 데이터 계약 제안

```text
ResultSource
- kind: "job" | "evolution" | "demo"
- id: { job_id } | { run_id, gen_no }
- capabilities:
  - range_analysis: { supported, reason }
  - monte_carlo: { supported, reason }
  - compare: { supported, reason }
- provenance: endpoint, fetched_at, status
```

지원되지 않는 기능은 클릭 후 무반응으로 남기지 않는다. 컨트롤을 숨기거나 disabled 상태와 이유를 함께 제공한다. Demo는 명시적 사용자가 선택한 경우에만 `kind="demo"`가 될 수 있다.

## 5. P2 — UX/UI 및 구조 고도화

| 순서 | 페이지 | 작업 | 구현·검증 기준 |
|---:|---|---|---|
| 1 | Backtest·Live·History | sticky 결과 목차와 진단 lazy mount | 요약/수익/MDD/분포/진단/증거 jump; 접힌 진단은 DOM·SVG에 존재하지 않음; 전체 펼치기 제공 |
| 2 | Backtest | MDD Random을 핵심 결과 바로 다음으로 이동 | 수익과 MDD를 초기 분석 흐름에서 연속 확인; source와 반복 횟수 표시 |
| 3 | Live | 공유 결과 이후 중복 Detail·GUI parity 제거 | `BacktestDetailChart`, `EvolutionGuiParityPanel` 중복 owner 제거; 짧은 provenance strip으로 대체 |
| 4 | 채점·부검 | 5개 카드 전용 균일 grid | 동일 min-height; 5번째 카드의 의도적 span; 1·2열 반응형; 빈 공간·반쪽 고립 카드 없음 |
| 5 | Live·반복 성과 | 역할별 높이 token 도입 | Live status/iteration 280–360px 잔여를 내용 역할에 맞춰 확대; 핵심 chart와 compact strip 분리 |
| 6 | History | 연구일·목적·사용처·referenced-by read model | authoritative source가 있는 값만 표시; 없는 값은 `—`; 추정 날짜 금지 |
| 7 | Settings | 로그 viewer·filter·redacted export·retention 안내 | 기존 frontend buffer와 허용된 server observability를 읽기 전용으로 연결; 민감정보 redaction; reset 영향 명시 |
| 8 | Backtest | 차트를 `ChartFrame` 접근성 계약으로 통합 | 제목·단위·기간·표본·freshness·threshold·source·상태·raw table 제공; keyboard 대안 |
| 9 | Reports | 레거시 리포트 전수 inventory | canonical registered / source-backed regenerable / legacy static / unverifiable 분류; 데이터 없는 재생성 금지 |
| 10 | 문서 | v5.9.1 기준 보고서·점수·증거 재발행 | 이전 보고서를 삭제·왜곡하지 않고 정정 addendum에서 버전·CSS·데이터 동작·검증 범위를 명시 |

## 6. 페이지별 최종 정보 구조

| 페이지 | 상단 | 핵심 분석 | 상세·진단 | UX 완료 기준 |
|---|---|---|---|---|
| Live | 활성 전략·상태·출처 | 좌우 buy/sell 전체 코드, 선택 run/gen 결과 | 정책·관찰성·증거 탭, 반복 성과 | 중복 차트 없음, 지원되지 않는 분석은 이유 명시 |
| Backtest | 선택 job·기간·상태 | KPI, Equity/PnL, MDD, 분포 | 보유·월별·orderflow·GUI parity·증거 | 모든 핵심 차트 1열 전폭, sticky jump, 진단 lazy |
| 채점·부검 | 종합 점수·판정 | 점수 구성·실패 원인·민감도 | 피드백·근거 | 5-card 균일 grid와 일관된 높이 |
| 반복 성과 | 세대·run 요약 | 점수·수익·MDD·거래수 추세 | 산점도·상위 후보·퇴보 원인 | 역할별 높이 token, 단위·범례 일치 |
| History | 검색·필터·메타 | Run Compare, 조건식 tree, buy/sell code | 결과 분석, 12-cell/holdout | 코드 440px+, 목록 bounded scroll, 설명·출처 제공 |
| Reports | 360–460px catalog | 선택 보고서 summary·TOC·본문 | provenance·inventory 상태 | desktop master/detail, mobile 1열, 명시적 테마 전환 |
| Hall | 인간 benchmark와 AI catalog 구분 | 수익·MDD·승률·거래·점수 | 상태·gate·기간·출처 | 전체 연구 필터·정렬·pagination, 누락값 `—` |
| Replay | source/date/symbol | first frame·timeline·재생 상태 | 신호·로그·성능 정보 | 실제 WS 흐름, 빠른 seek, 대규모 p95 증거 |
| Settings | 버전·bundle·health | UI 설정·로그 filter | redacted export·retention/reset | 읽기 전용 운영 진단, stale 문구 없음 |

## 7. P3 — 최종 품질 게이트

### 7.1 해상도·반응형

`375, 768, 1199, 1200, 1920, 2560, 3440`에서 Live, Backtest, 채점·부검, 반복 성과, History, Reports, Hall, Replay, Settings를 확인한다.

- 핵심 차트 실제 width와 parent width
- History code 실제 height
- Reports catalog 실제 width
- overflow, 잘림, 겹침, 1px 초과 수평 스크롤
- sticky header/section index의 viewport 가림 여부
- dark/light, reduced motion

### 7.2 실제 데이터 흐름

- 연결 상태 + 미선택 Backtest
- 명시적 Demo
- 실제 완료 job
- 실제 `run_id/gen_no`
- no-trade, 손실, 실패, unavailable, stale, request race
- Hall의 gate pass/fail, profit/loss, no-trade
- Reports의 canonical/legacy/unverifiable

### 7.3 성능

- document height, section height
- DOM node와 SVG/canvas 수
- initial render와 interaction render 시간
- long task 수와 총시간
- 접기 전후 진단 mount 수
- Replay query count, first-frame, seek, full-day playback p50/p95

### 7.4 접근성

- 키보드만으로 tab 이동, 결과 section jump, 차트 raw table, Reports 선택, Replay 제어
- focus visibility, 이름·역할·값, aria-expanded/pressed/disabled reason
- 로컬 axe-core serious/critical 0
- 색상 외 상태 표현, raw-data table, reduced motion

## 8. 테스트·증거 매트릭스

| 범위 | 집중 테스트 | 통합·게이트 | 브라우저 증거 |
|---|---|---|---|
| Demo/ResultSource | Backtest root·result source contract | dashboard API/unit suite | 미선택 네트워크·empty, Demo 명시 흐름 |
| Layout/History/Reports | shell/static/CSS contract | bundle sync, scale verifier | 7 viewport computed style JSON·screenshots |
| Hall | `test_dashboard_hall_of_fame.py` 확장 | pagination/filter API | loss/fail/no-trade rows와 total |
| Replay | replay engine·playback tests | real-size read-only profile | REST/WS action transcript, p50/p95 |
| Settings/Logs | settings source/static tests | redaction fixture | filter/export keyboard flow |
| ChartFrame/A11y | chart contract tests | accessibility verifier | axe, keyboard transcript, raw table |
| 전체 | focused union 후 dashboard unit suite | `verify_nonrelease_sync.py`, production build, `git diff --check` | 실제 served bundle hash와 artifact manifest |

## 9. 브랜치·커밋 전략

1. 부모 브랜치에서 이 계획 문서만 명시적으로 stage·commit한다.
2. 계획 커밋을 기준으로 `feature/dashboard-v5.10-p1-p3-ux-quality`를 만든다.
3. P1은 데이터 계약/레이아웃, Hall/Replay, History/Reports의 독립 묶음으로 병렬 구현하되 공통 파일 충돌은 부모가 통합한다.
4. P2는 P1 result-source 계약과 CSS token이 확정된 후 진행한다.
5. JSX/CSS 변경 후 `webui-build` production bundle을 한 번 재생성한다.
6. 집중 테스트 → dashboard 전체 unit → nonrelease sync → 브라우저 P3 순으로 검증한다.
7. 개발 보고서와 증거 manifest를 작성한 뒤 한국어 제목·본문으로 명시적 파일만 commit한다.
8. 부모 통합은 PR에서 수행하며, 이 작업은 커밋·검증·통합 가능 상태까지 증거를 남긴다. 임의 merge·push는 하지 않는다.

권장 커밋 단위:

| 커밋 | 내용 |
|---|---|
| 1 | 계획·재검토 보고서 |
| 2 | P1 데이터 정직성·result capability·전폭 layout |
| 3 | P1 History·Reports·Hall·Replay |
| 4 | P2 탐색 UX·MDD·Live·채점·높이 token |
| 5 | P2 History metadata·Settings logs·ChartFrame·report inventory |
| 6 | P3 test·verifier·bundle·최종 개발 보고서 |

## 10. 위험과 통제

| 위험 | 영향 | 통제 |
|---|---|---|
| 공통 result renderer 변경이 세 페이지를 동시에 깨뜨림 | 높음 | typed capability와 source별 fixture, 실제 job/run-gen 양쪽 검사 |
| 초광폭 수정 후 모바일 회귀 | 높음 | 7 viewport computed-style gate와 모바일 1열 명시 |
| Hall 전체 조회가 응답을 비대화 | 높음 | server-side pagination, stable sort, total/count metadata |
| Replay 최적화가 DB별 schema 호환성을 깨뜨림 | 높음 | schema 1회 탐색, fixture DB 변형, read-only query, fallback을 명시적으로 테스트 |
| lazy mount가 정보를 숨김 | 중간 | 핵심·MDD 기본 노출, section count, 전체 펼치기, URL/keyboard 접근 |
| 로그 export가 민감정보 노출 | 높음 | allowlist/redaction, 크기 제한, 브라우저 다운로드 전 사용자 action |
| 접근성 wrapper가 SVG interaction을 방해 | 중간 | 기존 pointer 동작 유지 + keyboard/raw table 병행 |
| 점수 과대평가 반복 | 높음 | 점수 항목별 명령·artifact·bundle hash 없으면 미달 처리 |

## 11. 독립 검토 결과와 병합 차단 조건

읽기 전용 Planner 검토는 현재 계획을 `BLOCK`, Architecture 검토는 구조적으로 실행 가능하지만 증거가 부족한 `WATCH`로 판정했다. BLOCK은 계획 자체가 불가능하다는 뜻이 아니라 다음 항목을 P1·P3에서 닫기 전에는 90점·병합·배포를 주장할 수 없다는 의미다.

| 독립 검토 항목 | 심각도 | 계획 반영 |
|---|---|---|
| 자동 `__demo__`가 연결된 실제 화면의 데이터 정직성을 위반 | HIGH | P1-1에서 자동 fallback만 제거하고 명시적 Demo endpoint는 유지 |
| dashboard GET helper가 기본 쓰기 모드로 DB를 열 수 있음 | HIGH | P1-0 read-only hard gate 추가 |
| Hall 상위 30 절단·client 재정렬·run 조회 N+1 | HIGH | server-side 전체 정렬·pagination·total·provenance 계약 |
| Replay symbol별 schema/복수 query와 truncation 비가시성 | HIGH | bounded batch/cache, dedupe, source fingerprint, truncated metadata |
| Settings 로그 수집은 있으나 viewer가 없고 redaction 시점이 늦음 | MEDIUM | capture 전 redaction, bounded memory, 수동 refresh와 읽기 전용 export |
| ChartFrame이 잘못된 row를 조용히 필터링하고 raw table을 즉시 생성 | MEDIUM | 명시적 상태·validator·lazy raw table·승인 exemption inventory |
| 기존 scale gate가 `performance_proved:false`이고 실제 job/run-gen이 아님 | HIGH | P3 실제 identity journey와 fail-closed 성능 계측 |
| 기존 보고서의 95점이 직접 증거 범위를 초과 | HIGH | v5.9.1 정정 addendum와 미검증 0점 원칙 |

병합 차단 hard gate:

1. GET 전후 보호·runtime DB와 디렉터리가 불변이어야 한다.
2. 연결 Backtest 미선택 상태가 합성 결과를 요청하거나 표시하면 안 된다.
3. Hall의 `total`, 페이지 합집합, 서버 정렬 결과가 fixture 전체와 정확히 일치해야 한다.
4. Replay는 query count·중복·truncation을 증거로 기록해야 한다.
5. 실제 job과 persisted run/gen을 UI에서 선택한 브라우저 receipt가 있어야 한다.
6. serious/critical 접근성 오류, global overflow, 데이터 identity mismatch가 하나라도 있으면 점수와 무관하게 FAIL이다.

## 12. 점수 산정 방법

| 영역 | 가중치 | 90점 기준 | 95점 기준 |
|---|---:|---|---|
| 데이터 정직성·기능 정확성 | 20 | Demo/실데이터/no-data 구분과 모든 핵심 기능 정상 | race·실패·stale·no-trade까지 자동 증거 |
| UX/UI 정보 위계·가독성 | 20 | 전폭 chart, 동일 높이, 명확한 순서·설명 | 긴 화면 탐색과 progressive disclosure까지 우수 |
| 페이지 간 일관성 | 15 | Live/Backtest/History 공통 결과 계약 | 모든 단위·상태·원자료 계약까지 통일 |
| 반응형·시각 품질 | 15 | 7 viewport 겹침·잘림 없음 | dark/light/reduced-motion 시각 회귀까지 고정 |
| 접근성 | 10 | 핵심 keyboard·focus·serious/critical 0 | 차트 원자료·전체 흐름·상세 keyboard 검증 |
| 성능 | 10 | 과도한 DOM 제거, Replay 체감 지연 해소 | p50/p95·long task·query count 기준 충족 |
| 테스트·문서·증거 | 10 | focused/full tests와 정확한 보고서 | artifact manifest와 served bundle hash로 재현 가능 |

총점은 가중 합계로 계산한다. 90점은 P1·P2 핵심 및 P3 기본 게이트가 모두 통과해야 하며, 95점은 성능·접근성·실제 데이터·전 해상도 증거가 빠짐없이 존재해야 한다. 한 영역이라도 심각한 데이터 거짓 표시나 안전 경계 위반이 있으면 총점과 무관하게 release BLOCK이다.

## 13. 결과 보고 형식

최종 개발 보고서는 다음을 포함한다.

- 시작·종료 시각과 wall-clock 소요시간
- 런타임이 제공하는 실제 token 사용량; 제공되지 않으면 `측정 불가`로 표기하고 추정하지 않음
- 변경 파일·커밋·served bundle/CSS hash
- P1–P3 각 항목 상태와 직접 증거
- 페이지별 비포/애프터 표
- 섹션별 점수, 가중 총점, 감점 근거
- 테스트·브라우저·성능·접근성 결과
- 미완료·외부 환경 blocker와 다음 PR/배포 단계

## 14. 실행 판정

계획은 실행 가능하나 `WATCH` 상태로 시작한다. 이유는 공통 결과 렌더러, Hall API, Replay query, Settings observability가 서로 다른 데이터 경계를 건드리며, v5.9.1의 기존 보고서와 정적 테스트 일부가 현재의 잘못된 동작을 계약으로 고정하고 있기 때문이다. P1에서 데이터 정직성과 source capability를 먼저 확정한 뒤 P2 시각 고도화를 적용해야 한다.
