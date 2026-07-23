# 대시보드 v5.10 회귀 전수감사 및 복구 계획

## 1. 판정

**현재 판정: BLOCK — v5.10을 부모 브랜치에 병합하거나 배포해서는 안 된다.**

사용자 지적이 맞다. v5.10은 데이터 진실성·접근성·페이지네이션을 개선했지만, 과거에 이미 제공하던 레이아웃 선택권과 시각적 의미를 제거했고, 실제 사용 경로를 충분히 상호작용 검사하지 않은 상태에서 95.6점으로 평가했다. 특히 63개 브라우저 매트릭스는 페이지가 열리고 넘치지 않는지만 확인했으며, 실제 Backtest 결과 선택·전체 그래프 노출·Replay 다중 프레임·Reports 주력 생성기·성과 테이블 의미색을 검증하지 않았다. **95.6점은 철회한다. 복구 구현과 상호작용 전수 게이트가 완료되기 전에는 대체 숫자 점수를 부여하지 않는다.**

## 2. 주소와 버전: 다른 대시보드인가

아니다. 다음 두 주소는 현재 동일한 `frontend/v4.html`, `app.js?v=ecfc1971`, `v4.css?v=edbe0f54`, 대시보드 릴리스 `v5.10.0`을 사용한다.

| 주소 | 실제 의미 | 현재 동작 |
|---|---|---|
| `http://127.0.0.1:8770/ui/evolution/workbench?tab=research` | 운영 기본 포트 8770의 V4 셸 | 경로는 Workbench지만 `tab=research`가 우선되어 **Live**가 열림 |
| `http://127.0.0.1:8770/ui/evolution/workbench` | 성과 Workbench 정본 경로 | 성과 탭이 열림 |
| `http://127.0.0.1:8770/ui/backtest` 또는 `...?tab=backtest` | Backtest 정본/호환 경로 | Backtest 탭 |
| `http://127.0.0.1:8770/ui/chart-replay` 또는 `...?tab=replay` | Replay 정본/호환 경로 | Replay 탭 |
| `http://127.0.0.1:8784/ui/v4/` | 이번 감사에서 띄운 임시 검증 서버 | 같은 프론트엔드, 새로 로드된 Python 백엔드 |

### 포트가 달랐던 직접 원인

- `8770`은 `stom_dashboard.bat` 및 `python -m ai_strategy_loop --port 8770`의 운영 기본 포트다.
- `8784`는 v5.10 검증 중 충돌을 피하려고 별도로 띄운 임시 Uvicorn 포트다.
- 두 서버는 같은 파일을 서빙했기 때문에 프론트엔드 번들은 모두 v5.10이었다.
- 8770의 당시 프로세스(PID 214964)는 장기 실행 중이었고, 최신 정적 번들과 달리 `/hall_of_fame/catalog` route를 제공하지 않았다. 프로세스가 정확히 어떤 source commit을 메모리에 로드했는지는 endpoint만으로 증명할 수 없으므로 “이전 Python app이 로드된 상태”는 강한 추론으로 한정한다.
- 실측 결과 8770의 `/hall_of_fame/catalog`은 HTTP 404, 8784는 HTTP 200이었다. 따라서 8770 성과 탭에는 `조회 실패: Error: HTTP 404`가 표시됐다.

즉, “다른 대시보드”가 아니라 **같은 최신 프론트엔드 + 서로 다른 시점에 로드된 백엔드 프로세스**였다. 이전 보고에서 8784를 최신 주소처럼 안내한 것은 잘못이었다. 운영 정본은 8770이어야 하며, 배포 시 프로세스 재시작과 프론트/백엔드 build 일치 검사가 필수다.

## 3. 사용자의 지적별 원인 분석

| 지적 | 판정 | 직접 원인 | 왜 이전 검증이 놓쳤는가 |
|---|---|---|---|
| Backtest 차트가 모두 1열 전폭 | 회귀 확인 | `v4.css`가 핵심·진단·GUI parity 그리드를 모두 한 열로 강제 | 1920/2560/3440에서 “전폭인가”만 성공 기준으로 삼음 |
| 다열 선택 기능 소실 | 회귀 확인 | v5.9에서 2/3/4열 상태·버튼·Settings 항목을 의도적으로 제거 | 과거 요구사항과 신규 요구사항을 함께 검토하지 않고 고정 레이아웃을 단순화로 판단 |
| Backtest 결과 그래프 소실 | 조건부 소실 확인 | 기본 결과 선택 없음, 최근 job 다수가 `terminal_without_openable_artifact`, 진단 10종은 기본 `diagnosticsOpen=false`로 DOM에도 없음 | 빈 Replay/Backtest 화면만 로드한 브라우저 매트릭스를 전체 기능 검사로 잘못 간주 |
| Live에 결과 분석이 안 보임 | 노출 구조 문제 | 공유 `BtResultArea`는 특정 Backtest stage와 정확한 run/gen일 때만 보이고 완료 시 다른 stage로 이동 가능 | 컴포넌트 존재 여부만 확인하고 완료 후 사용자 동선을 검사하지 않음 |
| 성과 테이블 색상 소실 | 회귀 확인 | v5.10 Hall 카탈로그 재작성 시 기존 `num-pos`/`num-neg`, MDD·gate·status 의미색을 이식하지 않음 | 서버 필터·페이지네이션·전체 건수에 집중하고 시각 의미 회귀를 비교하지 않음 |
| Reports 템플릿 부족 | 미구현/과장 확인 | `report_writer.py`에는 단일 표준 템플릿과 3개 표시 테마만 추가; 실제 기본 선택 보고서는 별도 `build_step_reports.py`의 기존 light-only 템플릿 | “시스템·라이트·다크”를 서로 다른 템플릿처럼 보고했고, 뷰어에서 실제 선택되는 주력 보고서를 검사하지 않음 |
| Replay가 일자 선처럼 보임 | 렌더러 결함 확인 | 기본 custom Canvas가 최소 48칸을 예약하고 초기 몇 개 캔들은 좌측에만 그리면서 현재가 점선을 전체 폭에 그림 | 백엔드 query p50/p95만 검사하고 실제 재생·seek·캔들 픽셀을 검사하지 않음 |
| 성과/표 가독성 저하 | 회귀+기존 부채 | 의미색 누락, 모든 값이 같은 전경색, 작은 header와 약한 separator, 전폭 표의 시선 추적 어려움 | axe 대비 통과를 정보 계층·시각적 가독성 통과로 잘못 확대 해석 |

## 4. Backtest 상세 감사

### 4.1 현재 구현

- 외곽 `bt-result-flow`는 세로 flex다.
- `.bt-primary-chart-grid`, `.bt-diagnostic-grid`, `.bt-equal-card-grid`, `.bt-gui-parity-cards`는 데스크톱에서도 1열이다.
- 화면에는 1/2/3/4열 전환 컨트롤이 없다.
- 결과 미선택 상태에서 canvas 0, 결과 SVG 0으로 측정됐다.
- 진단 섹션의 heatmap, MAE/MFE, quant, exit reason, orderflow, stats, rolling, monthly, GUI parity, cumulative trades는 펼치기 전에는 mount되지 않는다.
- 차트 구현 자체는 삭제되지 않았지만 사용자 입장에서는 “사라진 것”과 동일하게 보인다.

### 4.2 올바른 복구 구조

외곽 정보 순서는 유지하되 내부 동종 차트만 선택형으로 배치한다.

| 모드 | 사용자 표시 | 실제 규칙 |
|---|---|---|
| `wide` | 1열 대형 | 핵심 집중·프레젠테이션 |
| `balanced` | 2열 균형 | 기본값, 최소 카드 폭 520px |
| `dense` | 3열/4열 밀집 | 2560/3440에서만 허용, 최소 카드 폭 420px |
| `auto` | 화면 맞춤 | viewport와 카드 종류에 따라 1~4열 clamp |

- 선택값은 버전이 붙은 localStorage key에 저장한다.
- “선택 4열 / 실제 2열”처럼 반응형 clamp 결과를 컨트롤에 표시한다.
- 결과 요약·조건식·판정·capability는 항상 전폭이다.
- 진단은 기본 펼침 또는 “카드가 보이고 데이터만 지연 로딩”하는 구조로 바꾼다. DOM 자체를 숨겨 전체 그래프가 사라진 것처럼 만들지 않는다.
- 마지막으로 성공한 **openable artifact**를 자동 선택할 수 있지만 데모·합성 데이터는 절대 사용하지 않는다.
- 열 수 없는 결과는 목록에서 이유와 복구 동작(재실행/원본 찾기)을 제공한다.

## 5. Reports 템플릿 감사

### 5.1 현재 문제

보고서 시스템이 두 개의 독립 렌더러로 갈라져 있다.

1. `report_writer.py`: 안전한 단일 표준 템플릿, 표시 테마 radio 제공, 구조화 dict/표/차트 표현력 부족.
2. `scripts/build_step_reports.py`: navy/gold masthead, KPI, SVG 차트를 제공하지만 light-only이며 별도 CSS와 구조를 가짐.

`v4-reports.jsx` 뷰어는 목록·무결성·sandbox를 잘 처리하지만 iframe 내부 콘텐츠 품질을 고도화하지는 않는다. 기존 레거시 보고서를 보존한 것은 맞지만, 과거 연구를 새 템플릿으로 재발행하는 migration은 진행하지 않았다.

### 5.2 목표 템플릿 체계

단순 색상 테마가 아니라 실제 정보 구조가 다른 세 가지 템플릿을 만든다.

| template_id | 목적 | 핵심 구성 |
|---|---|---|
| `executive` | 의사결정 요약 | cover, KPI, 최종 판정, 위험, 다음 행동 |
| `quant_research` | 백테스트·세대 분석 | equity/MDD/분포/월별/산점도 SVG, 표본·방법·한계 |
| `research_journal` | 연구 과정 보존 | 가설, 실험 타임라인, 변경 이력, 증거, 관련 문서·커밋 |

공통 계약:
- system/light/dark/print 테마
- 좌측/상단 sticky 목차
- KPI 카드, semantic table, finding/callout, decision, provenance, limitations
- 양수·음수·위험·경고 의미색과 텍스트/아이콘 병행
- script-free SVG 차트와 sandbox/CSP 유지
- 375~3440px 반응형 및 PDF page-break 계약
- `build_step_reports.py`는 DB→typed document adapter로 축소하고 렌더러는 하나로 통합
- 원천이 있는 legacy만 재생성하고 원천 불명 문서는 원문 보존

## 6. 성과 테이블 복구

- 양수 수익/수익률: teal 계열 + `+` 부호.
- 손실/음수 수익: red 계열 + `−` 부호.
- MDD: 위험 단계별 red/amber 강도.
- gate/status/outcome: badge + 텍스트 + 아이콘, 색상만 사용하지 않음.
- 12~13px 중요 셀, sticky header, zebra/hover/selected row, 강한 separator.
- 전폭 표는 첫 식별 열 sticky, 수치 열 우측 정렬, 긴 기간/조건식 열 폭 제한.
- human benchmark와 AI 전체 카탈로그 양쪽에 동일 formatter 적용.

## 7. Replay 복구

### 7.1 실측

- 기존 backend profile은 2026-02-27, 종목 322000에 376개 bar가 있음을 기록한다.
- 재시작 전 실제 재생 화면의 Canvas는 1372×340px였고, 초기 캔들은 왼쪽 일부만 차지한 반면 현재가 점선은 화면 전체를 가로질렀다.
- 재시작 후 운영 8770에서 빠른 시작을 다시 실행하자 날짜·종목 선택과 `⏸ 일시정지` 상태까지 진입했지만 9초 이상 slider가 `0/0`, disabled로 남고 캔들이 노출되지 않았다. 즉, **시각적 착시뿐 아니라 실제 재생 lifecycle 정지 결함도 재현됐다.**
- source상 custom Canvas는 최소 48 slot을 예약하고 full-width last-price guide를 그리므로 초기 착시의 직접 기하 원인이 된다. 0-frame 정지의 별도 원인은 아직 확정하지 않았으며 WebSocket/session/start-history 흐름을 추적해야 한다.
- 별도 결함으로 tick 1초 집계가 일중 누적 시가/고가/저가를 candle OHLC처럼 사용할 가능성이 있다.

### 7.2 수정 계획

1. 이미 vendored된 Lightweight Charts candlestick을 기본 엔진으로 전환한다.
2. custom Canvas는 “실험적 Live/Order-flow 모드”로 명시한다.
3. Canvas 초기 bar는 우측 정렬하거나 현재 보이는 bar에 맞춰 자동 fit한다.
4. bar 수가 적을 때 전체 폭 현재가 ray를 숨기거나 현저히 약화한다.
5. 가격 범위에 3~5% padding과 최소 tick range를 적용한다.
6. `bars/total`, visible OHLC min/max, engine, source fingerprint를 표시한다.
7. tick 1초 OHLC를 current-price observation bucket으로 통일한다.
8. live/LWC/SVG 각각 1/2/20/120 bar, 재생·일시정지·seek backward/forward·full-day 완료를 실제 브라우저로 검증한다.

## 8. 이전 태그 전수 비교

| 버전 | 보존할 자산 | 확인된 한계/회귀 |
|---|---|---|
| v5.5.0 | Backtest matrix, Reports TOC | 구형 CSS cascade, 진실성 계약 이전 |
| v5.5.1 | Backtest detail 반폭·딥링크 | 초광폭 규칙과 데이터 owner 중복 |
| v5.6.0 | 2/3/4열 선택, 실제 4열, report v3 | 레이아웃 CSS를 그대로 가져오면 과거 충돌 재발 |
| v5.6.1 | GUI parity 펼침, MDD/손익 강조 | best UX donor지만 배포 baseline으로는 부적절 |
| v5.7.0 | typed report manifest, truthful states | 현재 Hall/Replay 성능 계약 이전 |
| v5.8.0 | ChartFrame, 접근성, PDF provenance | 상호작용 시각 검사가 부족 |
| v5.9.0 | 공유 `BtResultArea`, 결과 source 계약 | 레이아웃 선택을 의도적으로 제거 |
| v5.9.1 | Backtest 전폭 대형 hotfix | 전폭을 유일한 모드로 밀어 사용자 선택권 상실 |
| v5.10.0 | no-demo, capability, Hall 전체 목록, Replay batching | 1열 강제, 진단 숨김, Hall 의미색 누락, Reports 과장, Replay 시각 미검증 |

**복구 기준선은 현재 v5.10을 유지한다.** v5.6.1은 레이아웃 UX donor, v5.9.1 이전 Hall은 의미색 donor로만 사용한다. 과거 CSS·컴포넌트를 통째로 cherry-pick하지 않는다.

## 9. 실행 계획과 완료 기준

| 순서 | 우선순위 | 작업 | 완료 기준 |
|---:|---|---|---|
| 1 | P0 | 8770 stale backend 방지 | frontend release/build와 backend release/commit이 모두 표시되고 불일치 시 BLOCK 배너; 배포 후 프로세스 재시작 |
| 2 | P0 | path/query 정규화 | canonical path가 query보다 우선; 충돌 URL은 정본 URL로 redirect; route conflict 테스트 |
| 3 | P1 | Backtest 선택형 레이아웃 | 1/2/3/4/auto 제공, 실제 열 수 표시, 375~3440px clamp |
| 4 | P1 | 결과 선택·전체 그래프 복구 | 마지막 openable 결과 선택, 미열람 이유/복구 동작, 모든 진단 카드 기본 발견 가능 |
| 5 | P1 | Live 결과 지속 노출 | 완료 후에도 결과-ready affordance와 전체 분석 진입점 유지 |
| 6 | P1 | 성과 의미색·테이블 계층 복구 | 양/음/MDD/gate/status/outcome semantic style + 비색상 표현 |
| 7 | P1 | Replay LWC 기본화 | 실제 376 bar 재생·seek, 초기 horizontal-ray 착시 제거, 3엔진 비교 증거 |
| 8 | P1 | Reports typed renderer 통합 | 3개 진짜 template_id, 4개 theme/print, SVG 차트·목차·semantic table |
| 9 | P2 | 과거 보고서 재발행 | source-backed 항목만 신규 renderer로 재생성; legacy 원문과 provenance 보존 |
| 10 | P2 | 상호작용 전수 게이트 | 실제 job/run/gen, 결과 선택, layout 전환, Replay full-day, report theme/print, Hall 필터/페이지 |
| 11 | P3 | 시각 회귀 게이트 | 375/768/1199/1200/1920/2560/3440, dark/light, screenshot diff + computed style |
| 12 | P3 | 성능·접근성 재검증 | axe, keyboard, DOM/SVG/canvas, long task, render p50/p95, Hall/Replay API p50/p95 |

## 10. 전수검사 결과

### 현재 런타임

- 2개 포트 × 9개 탭 = 18개 기능 route 검사.
- 재시작 전 8770 성과 탭에서 `HTTP 404`를 재현했고 8784의 같은 endpoint는 200이었다.
- 두 포트에서 동일 v5.10.0 / `ecfc1971` frontend를 확인했다.
- 8770 Backtest 결과 분석 진입 후 layout control 0개, result canvas 0, result SVG 0을 재현했다. 실제 openable run/gen의 강제 1열 폭은 기존 `v510_real_run_fullwidth.json`과 source evidence가 보강한다.
- 재시작 후 운영 8770 성과 데이터 69행·1,328셀을 검사했으며 모든 셀의 computed color가 `rgb(232, 237, 242)` 하나뿐이었다.
- Replay는 재시작 전 초기 Canvas 착시와 재시작 후 0-frame lifecycle 정지를 각각 재현했다.
- Reports 실제 기본 iframe과 run comprehensive template screenshot을 확보했다.
- 감사 후 PID 214964를 종료하고 운영 정본 `python -m ai_strategy_loop --host 127.0.0.1 --port 8770`을 다시 시작했다.
- 재시작 후 `/health` HTTP 200 및 `/hall_of_fame/catalog?limit=1` HTTP 200, 카탈로그 총 5,364건을 확인했다. 운영 주소는 `http://127.0.0.1:8770/ui/`이다.

### 태그/소스

- `V2UC-Dashboard-v5.5.0`부터 `v5.9.1`까지 8개 peeled release commit과 현재 v5.10 source commit `5bf4f4c1`을 비교했다. detector 정의와 source line은 tag feature matrix v2에 기록했다.
- v5.6 계열의 2/3/4열 선택, v5.9의 의도적 제거, v5.10의 Hall 의미색 누락을 확인했다.
- 단순 rollback은 v5.7~v5.10의 데이터 진실성·보안·접근성·페이지네이션을 잃으므로 금지한다.

### 테스트

다음 집중 회귀 테스트는 **276 passed**였다.

- Backtest phase/result identity/analysis
- Replay lifecycle/backend/simulation
- Reports security/writer
- Hall catalog

이 테스트 통과와 실제 UX 회귀가 동시에 존재한다. 따라서 기존 테스트는 구조·API 계약에는 유효하지만 시각적 상호작용 완료 기준으로는 불충분하다.

## 11. 증거

- `artifacts/v510_forensic_route_function_matrix.json`
- `artifacts/v510_forensic_tag_feature_matrix.json`
- `artifacts/v510_forensic_backtest_empty_full.png`
- `artifacts/v510_forensic_performance_table.png`
- `artifacts/v510_forensic_replay_flat_candle.png`
- `artifacts/v510_forensic_report_template.png`
- `artifacts/v510_forensic_canonical_restart.json`
- `artifacts/v510_forensic_performance_style.json`
- `artifacts/v510_forensic_replay_interaction.json`
- `artifacts/v510_forensic_source_evidence.json`
- `artifacts/v510_real_run_fullwidth.json`
- `artifacts/v510_replay_profile.json`
- `artifacts/v510_forensic_server_mismatch.json`

## 12. 최종 책임 분석

이전 작업이 엉망으로 보인 핵심 이유는 코드 양이 부족해서가 아니라 **검증 기준이 사용자 작업 흐름과 일치하지 않았기 때문**이다.

1. “차트를 크게”를 “모든 차트를 항상 1열”로 과잉 해석했다.
2. 최신 데이터 진실성만 우선해 과거 레이아웃 선택권을 보존하지 않았다.
3. 컴포넌트가 소스에 존재하는 것을 사용자가 볼 수 있는 것으로 간주했다.
4. API·DOM·overflow 검사를 실제 클릭·선택·재생·seek·보고서 내용 검사로 확대하지 않았다.
5. 미래에 생성될 표준 report writer를 개선하고, 현재 뷰어가 기본으로 보여주는 별도 run report generator를 놓쳤다.
6. 백엔드 프로세스 freshness를 검증하지 않고 임시 포트 결과를 운영 포트 결과처럼 보고했다.
7. 접근성 대비 통과를 시각적 계층과 정보 가독성 통과로 잘못 확대했다.

복구 구현은 이 보고서의 P0→P1→P2→P3 순서를 따라야 하며, 각 단계는 실제 운영 URL 8770에서 사용자 작업 흐름을 끝까지 실행한 증거가 없으면 완료로 판정하지 않는다.
