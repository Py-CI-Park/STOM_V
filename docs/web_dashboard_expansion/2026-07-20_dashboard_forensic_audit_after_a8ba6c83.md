# 대시보드 전수검사 보고서 — `a8ba6c83` 이후

- 검사일: 2026-07-20
- 검사 브랜치: `audit/dashboard-forensic-review-after-a8ba6c83`
- 기준 범위: `a8ba6c835c933e22303970eb9f0a5be3ba01ea71..916af163d309e1364e3e6d7bf1dac413ab2cf7d4`
- 대상: `ai_strategy_loop/dashboard/`, `tests/unit/dashboard/`, `docs/web_dashboard_expansion/`, HTML 보고서 생성기
- 판정: **BLOCK — 구조 정리와 데이터 정직성 교정 전에는 90점대 성숙도로 간주할 수 없음**
- 종합 성숙도: **61/100**
- 보고서 하위 시스템 성숙도: **52/100**

## 1. 결론

현재 대시보드는 단순 시제품은 아니다. Live 연구 관찰, 백테스트, History, Replay, 성과, 연구 자산, 설정, 용어, 안전한 HTML 뷰어와 상당한 테스트 자산을 갖춘 실사용 가능한 연구 터미널이다. 특히 CSP+sandbox 보고서 경계, archive 실패 시 live 데이터로 대체하지 않는 정책, `/runs?fields=slim`, History lazy mount, 번들 fingerprint와 stale-build 감지는 좋은 기반이다.

하지만 90점대 완성도로 볼 수는 없다. 가장 큰 이유는 다음 네 가지다.

1. **정본 상태와 화면 상태가 어긋나는 결함**이 남아 있다. 완료 상태의 정본은 `complete`인데 Live 단계 계산 일부가 `done`을 검사한다.
2. **오류·partial·stale을 파생 요약으로 덮는 fallback**이 있어 데이터 정직성 계약을 해친다.
3. **CSS가 설계 시스템이 아니라 수정 연대기**가 되었다. 같은 선택자가 버전별로 뒤에서 반복 덮어써 계산 스타일을 소스만으로 예측하기 어렵다.
4. **History/Wiki/Reports는 전수 스캔·중복 파싱 구조**여서 데이터가 커질수록 탭이 느려진다. HTML 보고서는 시각적으로 개선됐지만 정본 manifest, 다중 사이클, 검증, provenance, 내부 정보구조가 완성되지 않았다.

따라서 현재 상태는 “기능이 풍부한 운영형 베타”에 가깝다. 신규 기능 추가보다 정본 데이터 계약, 전역 연구 컨텍스트, CSS/차트 시스템, 인덱싱된 조회, 보고서 스키마를 먼저 정리해야 한다.

## 2. 검사 근거와 규모

### 2.1 변경 이력

- 전체 범위: **144 commits**, 그중 merge **62 commits**
- 대시보드 관련 직접 변경 커밋: **80 commits**
- 관련 파일 변경량: **82 files, +8,980 / -1,697 lines**
- 변경 집중도:
  - `ai_strategy_loop/dashboard/frontend/`: 43.9%
  - `docs/web_dashboard_expansion/`: 28.0%
  - `tests/unit/dashboard/`: 14.6%
  - dashboard backend: 8.5%
- 큰 변경 파일:
  - 번들 `app.js`: 3,225 line churn
  - `v4.css`: +561 lines
  - `v4-research.jsx`: 481 line churn
  - `build_step_reports.py`: +312 lines
  - `v4-reports.jsx`: +210 lines

### 2.2 현행 크기와 구조

- `styles.css`: 약 **3,916 lines**
- `v4.css`: 약 **988 lines**
- V4 셸은 legacy 공용 CSS와 V4 CSS의 cascade를 동시에 소비한다.
- `dashboard-v4-shell.jsx`가 서버 연결, run archive, 내비게이션, 모달, Context drawer, 탭 라우팅을 한 컴포넌트에서 소유한다.
- 세 종류 셸이 단일 번들을 공유하며 V4가 정본이지만 legacy/preview 자산과 window 전역 호환 계약이 남아 있다.

### 2.3 8770 실측

동일 로컬 서비스에서 실제 응답을 측정했다.

| API | 응답 시간 | 크기 | 판정 |
|---|---:|---:|---|
| `/runs?fields=slim` | 0.347s | 250,323 B | 전송은 개선, 서버는 full payload를 먼저 생성 |
| `/research_records` | 0.143s | 140,227 B | 현재는 빠르나 매 요청 JSONL 전수 파싱 |
| `/history/index?limit=50` cold | 6.364~9.322s | 15,332 B | BLOCK |
| `/history/index?limit=50` warm | 0.009s | 15,332 B | 30초 TTL 효과 확인 |
| `/research_docs` | 7.888~9.686s | 264,942 B | 매 요청 지속적으로 느림 |
| `/reports` | 0.338~0.459s | 2,951 B | 현재 규모는 허용, docs 전체 walk 구조 |

1920×1080 실제 화면에서도 Live 첫 문서 높이는 약 2,657px였고 핵심 차트는 2×2로 약 두 viewport를 차지했다. Reports는 목록 22건, TOC 60개를 동시에 렌더하고 iframe을 사용했다.

## 3. 왜 한 번에 이해·반영되지 않고 반복 수정됐는가

반복 수정의 직접 원인은 사용자의 요구가 어려워서가 아니라 **완료 판단 방식과 기존 구조**에 있었다.

### 3.1 마커·문구 검사가 실제 동작 검증을 대신했다

초기 라운드는 클래스 존재, 제목 문자열, JSX 배선 여부를 완료 근거로 많이 사용했다. 실제 run 데이터, 이전 localStorage, 좁은/넓은 해상도, 긴 축 라벨, 비어 있지 않은 History를 동시에 검증하지 않았다. 그 결과 “매트릭스 클래스가 있음”과 “사용자 화면에서 탭이 사라지고 매트릭스로 보임”이 혼동됐다.

### 3.2 V4 셸 위에 legacy 컴포넌트를 CSS로 재배치했다

신규 정보구조로 다시 구성하기보다 기존 패널을 유지한 채 wrapper와 CSS를 추가했다. 회귀 위험은 줄였지만 owner/context/크기 계약은 그대로였다. 결국 같은 패널에 버전별 wrapper와 예외 규칙이 누적됐다.

### 3.3 CSS append-only 보정

`v4.css`의 `.v6-graphs .panel`은 220px, 356px, 236px plot, 460px 등 여러 시대의 규칙이 같은 파일에 남아 뒤 규칙이 앞 규칙을 덮는다. `.v55-board-main`도 460px 고정열과 1열 breakpoint가 다른 위치에서 충돌한다. 잘림 하나를 고치면 높이·여백·반응형이 다른 화면에서 다시 깨질 수밖에 없는 구조다.

### 3.4 정본 상태·컨텍스트를 먼저 고정하지 않았다

- Live 완료 상태: 정본 `complete`와 화면의 `done` 검사 불일치
- shell의 selected run은 모든 탭 헤더에 표시되지만 Reports/Backtest는 그 run을 소비하지 않음
- History는 “아래 모든 섹션이 선택 연구 맥락”이라고 표시하지만 선택 ID를 Compare/Tree/Heatmap/Funnel에 전달하지 않음

화면부터 확장하고 데이터 소유권을 뒤늦게 연결해 동일 정보가 중복되거나 문구만 통합된 상태가 생겼다.

### 3.5 브랜치·버전 단위가 너무 작고 완료 라벨이 과했다

이틀 동안 144커밋과 62 merge가 만들어졌고 V5, V6, v5.3, v5.4, v5.5, v5.6가 연속 등장했다. 페이지별 브랜치 분리는 좋은 방식이지만, 각 브랜치가 **하나의 정본 계약과 실측 수용 조건**을 닫기 전에 “완료”로 병합되었다. 이후 사용자 화면 검수에서 구조적 누락이 드러나 다시 덧붙였다.

### 3.6 설계 문서도 최신 정본이 아니다

`docs/web_dashboard_expansion/design.md`는 상단에서 V4 8탭과 in-browser Babel을 전제로 하지만 현재 셸은 9탭이고 esbuild 단일 번들을 사용한다. 문서의 375px/200% zoom 계약도 최근 1920/2560/3440 기하 검증에는 포함되지 않았다. 잘못된 정본을 품질 게이트가 참조했다.

## 4. 성숙도 점수 — 61/100

| 영역 | 배점 | 점수 | 근거 |
|---|---:|---:|---|
| 기능·연구 프로세스 범위 | 18 | 14 | Live→Backtest→History→Reports→Performance 기능은 넓음. 일부 owner/context 연결 미완성 |
| 데이터 정직성·신뢰 | 15 | 8 | 상태 enum 불일치, broad fallback, report 집계/설명 오류 |
| 정보구조·사용자 여정 | 12 | 8 | 탭 owner는 개선됐으나 전역 run/gen context와 History master-detail이 미완성 |
| UX·시각화 품질 | 15 | 10 | 차트·heatmap·scatter·matrix가 풍부하나 차트 문법과 density가 불균일 |
| 성능·확장성 | 12 | 5 | warm cache는 양호, cold History/Wiki 전수 스캔은 BLOCK |
| 접근성·반응형 | 10 | 5 | shell tab/inert 기반은 좋으나 저대비, mobile overflow, 복합 widget 미완성 |
| 코드 구조·유지보수성 | 10 | 4 | CSS 연대기, shell 결합, fetch 분산, 미정의 토큰 |
| 테스트·배포·운영 | 8 | 7 | 테스트·보안·번들 fingerprint는 강함. 실제 성능/접근성/기하 자동 게이트 부족 |
| **합계** | **100** | **61** | **운영형 베타, 구조 개선 필요** |

이전 문서의 87/90점은 당시 정의한 화면 항목과 자기 검수 범위에서는 의미가 있지만, 현행 코드의 상태 정합성, cold-path 성능, 접근성, 보고서 무결성까지 포함한 성숙도 점수로 재사용하면 안 된다.

## 5. 코드 포렌식 발견사항

### P0 — 정본 상태 매핑 오류

`ai_strategy_loop/controller/contract.py`의 완료 상태는 `complete`인데 `v4-research.jsx` 일부 단계 계산은 `done`을 검사한다. 완료 run이 엔진 “대기” 또는 생성 단계로 보일 수 있다.

**필요 조치:** 공용 `ResearchStatus` 매퍼를 만들고 idle/running/stopping/complete/error fixture로 자동 stage와 문구를 검증한다.

### P0 — authoritative 오류를 파생 fallback이 숨김

`panels-analysis.jsx`, `panels-config.jsx`에서 `status !== "ok"`인 경우를 넓게 generation 파생 데이터로 대체한다. missing/pending뿐 아니라 error/partial/stale도 정상 요약 뒤로 가려질 수 있다.

**필요 조치:** authoritative 상태를 `missing | pending | ready | partial | stale | error`로 분리한다. 파생 결과는 “보조 추정”으로만 병기하고 오류·마지막 정상 시각·재시도를 우선 표시한다.

### P1 — History master-detail은 문구만 연결

`v4-history.jsx`의 선택 campaign은 컨텍스트 바를 갱신하지만 Compare, Condition Tree, A/B, Heatmap, Funnel, ResearchIndex에 전달되지 않는다. “아래 모든 섹션은 이 선택 연구 맥락”이라는 문구가 실제보다 강하다.

**필요 조치:** `research_id`를 모든 상세 API와 컴포넌트의 필수 키로 만들고 선택 변경 시 이전 요청 취소와 provenance 일치를 검증한다.

### P1 — 전역 run 컨텍스트 분절

셸 헤더는 archive run을 표시하지만 Reports와 Backtest 본문은 이를 소비하지 않는다. 사용자에게 같은 연구를 보고 있다는 오해를 줄 수 있다.

**필요 조치:** `ResearchContext {mode, researchId, runId, genNo, profileHash, timeRange, source}`를 도입하고 각 탭이 `consume/override/none`을 선언한다.

### P1 — CSS 연대기와 반응형 충돌

- 동일 selector가 릴리스별로 반복 정의됨
- 375px에서 460px 고정열이 overflow를 만들 수 있음
- 3/4열 버튼을 선택해도 1920px에서는 breakpoint가 2열로 강제함
- `--line` 변수를 사용하지만 정의된 토큰은 `--line-1`, `--line-2`임
- 필수 메타 텍스트에도 장식용 저대비 `--ink-3` 사용

**필요 조치:** token→primitive→shell→feature 순서로 CSS를 재구축하고 컴포넌트당 authoritative rule 하나만 둔다.

### P1 — 관찰성 코드 위험

프런트 console.error wrapper는 JSON 직렬화가 실패하면 원래 오류 출력도 막을 수 있다. backend ring log handler는 여러 logger와 app factory에 누적될 수 있고 redaction/session 보호가 없다.

**필요 조치:** 원래 console 호출을 반드시 보장하고 안전 직렬화한다. backend는 lifespan 단일 handler, secret/path redaction, 세션 보호를 적용한다.

### P2 — stale request 경로

일부 상관 분석 요청은 AbortController/request generation guard가 없어 느린 이전 응답이 현재 선택을 덮을 수 있다.

**필요 조치:** 공용 read client에서 abort, single-flight, identity guard, timing을 통합한다.

## 6. UX·UI와 시각화 전수평가

### 6.1 Live

**좋은 점**
- 연구 단계, 현재 세대, gate, blocker, 로그, 적합도·수익·품질 정보를 한 흐름에 모음
- 2/3/4열과 stage 선택 기능 존재
- 매수/매도 조건식, 부검, 계보, 안정성 분석의 가시성이 과거보다 크게 개선됨

**부족한 점**
- 1920에서 4차트가 2×2×460px로 첫 화면을 과도하게 점유해 stage가 아래로 밀림
- 현재 세대 카드 내부에 실제 콘텐츠보다 빈 공간이 크게 남는 fixture가 있음
- 단계·상태 자동 선택이 완료 상태 매핑 오류의 영향을 받음
- 동일 run/gen/time range를 차트 간 linked hover/brush로 비교할 수 없음
- benchmark, 표본수, freshness, confidence/불확실성 슬롯이 차트마다 다름

### 6.2 Backtest

**좋은 점**
- GUI parity, 상세 결과, 퀀트 회귀·상관·요일 구조, matrix 배치가 존재
- 결과 판정 banner와 조건식/기간 맥락을 제공

**부족한 점**
- 셀 720px 고정 높이와 내부 스크롤은 정렬은 맞추지만 내용량이 적은 셀에는 여백, 많은 셀에는 중첩 스크롤을 만든다.
- 비용·슬리피지·수수료 민감도, walk-forward/OOS cohort, regime, bootstrap confidence가 정본 시각화 계약으로 통합되지 않음
- 결과 선택 시 full CSV 분석과 다수 SVG가 한 번에 마운트되어 체감 정지가 생길 수 있음

### 6.3 History

**좋은 점**
- 목록, 정렬, 필터, compare, lineage, A/B, heatmap, funnel, governance를 owner 탭에 모음
- 무거운 하위 영역을 접힘 상태에서 lazy mount

**부족한 점**
- 선택 research ID가 하위 분석을 실제로 필터하지 않음
- cold index 6~9초
- campaign 목록/detail이 동일 JSONL corpus를 반복 스캔
- 많은 행에서 virtualization과 서버 pagination이 부족

### 6.4 Reports

**좋은 점**
- CSP+sandbox 이중 차단
- run/step/일반 문서를 시각적으로 구분
- iframe 기반 원문 격리와 목차 제공

**부족한 점**
- 실제 정보모델이 아니라 경로 prefix와 파일명 regex로 문서 종류를 추론
- 현재 run context, research hierarchy, status/trust/hash/stale/broken을 목록에서 소비하지 않음
- TOC 추출을 위해 HTML을 먼저 fetch하고 iframe이 같은 HTML을 다시 fetch
- 60개 목차와 22개 문서를 좁은 양쪽 rail에 동시에 배치해 보고서 본문 폭이 줄어듦

### 6.5 Performance·Settings·Glossary·Replay

- Performance는 기간·profile이 다른 후보의 정규화 비교와 신뢰구간이 부족하다.
- Settings는 표시 옵션은 있으나 density/contrast/motion이 전체 컴포넌트 토큰에 일관되게 반영되지 않는다.
- Glossary는 정적 위키로 검색·anchor·현재 화면 용어 딥링크가 부족하다.
- Replay는 keep-alive/inert 계약은 좋지만 활성 화면에서만 shortcut/listener가 동작하는 실제 키보드 검증을 계속 유지해야 한다.

### 6.6 공통 차트 시스템 누락

차트는 Canvas, SVG, lightweight-charts가 혼재하고 각 패널이 legend, tooltip, empty/error, 축, 색을 개별 구현한다. 공통 `ChartFrame`과 `ChartSpec`이 없어 다음이 일관되지 않다.

- 제목·단위·기간·표본수·freshness
- benchmark·gate threshold·confidence band
- tooltip·linked crosshair·brush/zoom
- 색+선형+shape의 중복 인코딩
- accessible data table
- export PNG/CSV/context pack

## 7. History와 Reports가 느린 정확한 이유

### 7.1 `/runs?fields=slim`

slim projection은 `_runs_payload(None)`이 모든 run의 generation rows를 만든 뒤 마지막에 적용된다. 네트워크는 줄었지만 DB query와 Python 객체 생성 비용은 거의 그대로다. Compare가 요구하는 일부 필드도 slim allowlist에서 빠져 `—`로 퇴행할 위험이 있다.

### 7.2 `/history/index`

목록을 만들면서 각 campaign/run의 전체 ResearchNode를 빌드해 count/status를 계산한다. TTL 30초 안에서는 0.009초로 빠르지만 cold miss마다 6~9초가 재발하고 동시 miss single-flight가 없다.

### 7.3 `/history/detail`

section/cursor와 무관하게 전체 ResearchNode를 다시 만든 뒤 잘라 반환한다. 페이지 이동과 section 전환마다 같은 원천을 재파싱한다.

### 7.4 `/research_records`

모든 JSONL을 `read_text().splitlines()`로 읽고 후보를 파싱·정렬한다. detail도 `list_research_records()`를 다시 호출하므로 목록 직후 첫 campaign 상세에서 같은 corpus를 중복 스캔한다. 60초 polling도 전량 반복한다.

### 7.5 `/research_docs`

허용된 930+ Markdown 파일을 `rglob`하고 **모든 원문을 읽어 제목을 추출**한다. 캐시가 없어 매 요청 8~10초가 지속된다. 선택 문서 `/research_doc`도 전체 index를 다시 만든 후 원문을 또 읽는다.

### 7.6 `/reports`와 리포트 본문

`/reports`는 docs 전체를 매번 walk/stat/sort한다. 현재 22건이라 0.3~0.5초지만 성장에 선형이다. 프런트는 선택 HTML 전체를 TOC 추출용으로 받고 iframe으로 다시 받아 동일 문서를 두 번 전송·파싱한다. anchor 변경 시 iframe key가 바뀌어 다시 마운트된다.

## 8. HTML 보고서 체계 전수검사 — 52/100

### 8.1 이미 있는 것

- `report_writer.py`: 9개 표준 section, escaping, scriptless HTML, step manifest, atomic file write
- `build_step_reports.py`: loop DB에서 step 및 run 종합 HTML 생성, flow SVG, KPI, score bar, MDD-score scatter
- `build_research_report.py` + `alpha_lab/reporting`: versioned manifest, source/content hash, stale/missing 상태, staging directory 교체
- dashboard: CSP+sandbox 안전 뷰어

즉 “템플릿이 전혀 없다”는 상태는 아니다. 그러나 서로 다른 세 보고 체계가 하나의 정본 스키마로 합쳐지지 않았다.

### 8.2 BLOCK 결함

1. run report는 run 6필드와 generation 11필드만 읽어 config, lineage, prompt, 조건식 전문/해시, equity, candidate passport, feedback, validation manifest, receipt, 인간 판정을 잃는다.
2. 독립 후보의 profit을 합해 “누적 profit”으로 표기한다. 포트폴리오 집계가 아니므로 잘못된 의미다.
3. MDD가 오른쪽으로 커지는 scatter를 “우상단이 저위험·고성과”라고 설명한다. 실제로는 좌상단이 저위험이다.
4. run report는 HTML만 만들고 step manifest를 갱신하지 않는다. 현 `manifest.json`은 demo 1건인데 디렉터리에는 run report 3건이 있다.
5. run report가 링크한 세대 상세 HTML이 없는 경우가 있어 broken link가 발생한다.
6. alpha 연구 보고서의 tracked HTML은 inline script tab을 사용하지만 뷰어 CSP가 script를 막아 탭 버튼이 동작하지 않을 수 있다.
7. 내부 “탭형 보고서” 요구를 충족하는 정본 구조가 없다. run report는 긴 연속 문서이며 170세대 같은 run은 지나치게 길다.

### 8.3 필요한 정본 보고서 정보구조

1. **결정 요약**: status, winner/best 구분, promotion 권한 없음, 핵심 위험
2. **연구 질문·가설**: 목표, prior, 실패 조건
3. **실행 프로파일**: 데이터 기간, 시장, tick/min, 비용·수수료·슬리피지, 엔진/commit/config hash
4. **다중 사이클 개요**: cycle→generation→candidate lineage DAG
5. **조건식 진화**: 매수/매도 전문, 부모 diff, rule provenance, validation
6. **백테스트**: equity, drawdown, trade distribution, monthly/regime, turnover/cost
7. **검증**: IS/OOS, walk-forward, gate, stability, leakage/overfit defense
8. **비교**: baseline, previous, best, winner, cross-run; profile hash가 다르면 delta 금지
9. **AI 분석과 인간 판단 분리**: model/prompt ID, AI insight, reviewer decision/rationale
10. **결론과 다음 행동**: 사실·추론·제안 분리
11. **provenance·한계·부록**: artifact URI/hash/schema/observed_at, missing reason, print appendix

정적 HTML 내부는 CSP와 장기 보관을 위해 **scriptless anchor navigation**을 정본으로 삼고, 대시보드에서만 React tab/drill-down을 제공하는 편이 안전하다. HTML 자체에 실제 탭을 넣어야 한다면 JS 없이 radio/anchor 기반으로 만들고 인쇄 시 전 섹션을 펼쳐야 한다.

## 9. 보존해야 할 좋은 자산

- CSP `default-src 'none'` + sandbox iframe
- report path realpath boundary와 symlink escape 차단
- archive 실패를 live로 위장하지 않는 display state
- Replay hidden+inert keep-alive
- runs shared cache와 in-flight dedupe
- History heavy section lazy mount
- static bundle fingerprint/immutable cache/stale banner
- readonly/atomic writer 패턴
- shell wiring parity와 보고서 보안 테스트
- 조건식/백테스트/검증 데이터를 임의로 합성하지 않는 원칙

## 10. 최종 판정

현재 대시보드는 많은 기능을 갖췄지만 **코드와 보고서 모두 “한 번 더 덧붙이는 방식”을 중단해야 하는 시점**이다. 다음 강화 개발은 P0 정합성·보고서 무결성·cold-path 성능을 먼저 닫고, 이후 ResearchContext와 디자인/차트 시스템을 재정립해야 한다. 상세 실행 순서와 브랜치/검증 게이트는 동반 계획서 `2026-07-20_dashboard_forensic_improvement_plan.md`에 정의한다.
