# Dashboard v5.8.0 개발·품질 평가 및 다음 작업 보고서

- 작성일: 2026-07-22
- 정본 부모 브랜치: `loop/process-research-pipeline`
- 배포 기준 커밋: `b5c60420da92a71adb7b167c609c588706ebcb56`
- 배포 태그: `V2UC-Dashboard-v5.8.0`
- 대시보드: `v5.8.0`, `app.js?v=15c4c554`
- 서비스 기준 주소: `http://127.0.0.1:8770`
- 평가 범위: V4 정본 셸 9개 탭, 보고서 출판 계층, History/Wiki 성능, 접근성·반응형·배포 계약

## 1. 개발 완료 요약

v5.7 감사에서 상태·데이터 진실성, History 확장성, 보고서 무결성, 차트 설명력, 접근성 자동화가 핵심 결손으로 확인됐다. v5.8은 신규 기능을 늘리기보다 이 결손을 닫는 품질 릴리스로 구현했다.

| 개발 축 | 주요 변경 | 사용자·운영 효과 | 현재 증거 |
|---|---|---|---|
| 데이터 진실성 | run/research/request key, abort, finite-value, explicit boolean 검증 | 이전 응답·형식 오류·truthy 값을 현재 정본처럼 표시하지 않음 | 전체 Dashboard/API 880 tests |
| 대용량 성능 | 격리된 History/Wiki 2× 규모 fixture와 cold/warm 예산 | 데이터 증가 시 조회 회귀를 재현 가능하게 차단 | scale gate PASS |
| 보고서 | strict v1 manifest, HTML/PDF companion, SHA-256·bytes·source binding | 보고서 원본·PDF·manifest의 동일 출처를 검증 | PDF 4/4 PASS |
| 출판 안전성 | canonical path, junction escape 차단, atomic replace, durable rollback | 손상·충돌·부분 출판·복구본 유실을 차단 | 독립 review CLEAR |
| 차트 계약 | 공통 ChartFrame, 6개 metadata, 상태 구분, 최대 200행 raw fallback | 그래프의 단위·기간·표본·기준·출처와 실제 값을 함께 확인 | focused 75 tests |
| 접근성 | 9탭×6폭×2테마×2모션, axe·키보드·focus·overflow·bundle attestation | 화면·테마·키보드 회귀를 자동 차단 | 216/216 PASS |
| 배포 관리 | v5.7 PR #109, v5.8 PR #110, 독립 태그와 부모 병합 | 감사→개발→검증→부모 통합→배포 이력 보존 | 두 PR MERGED |

## 2. 검증 기준과 점수 산식

`DESIGN.md`의 탭별 100점 rubric을 사용한다.

| 평가 항목 | 배점 | 판정 기준 |
|---|---:|---|
| Primary task completion | 25 | 탭의 핵심 사용자 여정을 실제 API·상태로 완료할 수 있는가 |
| State/data honesty | 20 | loading/error/partial/stale/blocked/empty와 출처를 정직하게 구분하는가 |
| Responsive | 15 | 375~3440px에서 전역 overflow나 기능 손실 없이 동작하는가 |
| Keyboard/accessibility | 15 | tab·focus·label·landmark·contrast·reduced motion 계약을 만족하는가 |
| Visual hierarchy/feedback | 15 | 정보 밀도, 상태 강조, 차트 설명, 피드백 우선순위가 명확한가 |
| Automated+browser evidence | 10 | 단위/API/실브라우저 검증과 재현 가능한 증거가 있는가 |

다음이 하나라도 존재하면 최대 94점으로 제한한다: P0/P1 결함, console/page error, 미검증 primary journey, global overflow, 오해를 부르는 상태, stale capture. 현재 자동 행렬에서는 이 제한 사유가 확인되지 않았다. 다만 axe minor/moderate 항목과 실제 운영 cold-start 지연은 감점·후속 작업으로 반영했다.

## 3. 정본 9개 섹션별 점수

| 섹션 | 핵심 과업 | 과업 25 | 정직성 20 | 반응형 15 | 접근성 15 | 시각·피드백 15 | 증거 10 | 총점 | 판정 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Live | 연구 시작·단계·세대·로그·조건식 관찰 | 24 | 20 | 15 | 12 | 14 | 10 | **95** | 연구 운영 가능 |
| History | campaign/run 선택과 동일 연구 맥락 탐색 | 25 | 20 | 15 | 13 | 14 | 10 | **97** | 정본 탐색 가능 |
| Reports | typed catalog·TOC·안전한 HTML/PDF 열람 | 25 | 20 | 15 | 12 | 14 | 10 | **96** | 출판·감사 가능 |
| 성과 | 인간/AI benchmark와 근거 비교 | 24 | 19 | 15 | 12 | 14 | 10 | **94** | 사용 가능, 비교 계약 보강 권장 |
| Backtest | 전략 실행·진행·결과·민감도 분석 | 25 | 20 | 15 | 13 | 14 | 10 | **97** | 실행·분석 가능 |
| Replay | play/pause/seek/speed와 프레임 검토 | 24 | 20 | 15 | 13 | 14 | 10 | **96** | 신호 맥락 검토 가능 |
| 연구 자산 | 비정본 연구 결과·연혁·prototype 탐색 | 23 | 19 | 15 | 13 | 13 | 10 | **93** | 비정본 경계 유지, 구조 개선 필요 |
| 설정 | theme·density·layout·로그 관리 | 24 | 20 | 15 | 12 | 13 | 10 | **94** | 운영 가능, heading 구조 개선 필요 |
| 용어 | 지표·분석·거버넌스 용어 검색 | 24 | 20 | 15 | 13 | 14 | 10 | **96** | 연구 지원 가능 |
| **평균** |  | **24.2** | **19.8** | **15.0** | **12.6** | **13.8** | **10.0** | **95.3** | 95점 목표 달성 |

## 4. 섹션별 개선 내용과 남은 작업

### 4.1 Live — 95점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| 정본 `complete` 상태와 화면 단계 매핑 정리 | 완료 run을 진행 중·오류로 오인하지 않음 | 페이지 최상위 H1과 landmark 구조 정리 |
| blocker·error·partial·stale 분리 | 파생 값이 authoritative 오류를 숨기지 않음 | 첫 화면 차트 밀도와 stage 노출 비율 재조정 |
| ChartFrame metadata·raw rows | 차트 수치의 단위·표본·출처 확인 가능 | linked hover/brush는 후속 시각화 기능 |
| 선택 run/gen 요청 key | 이전 응답이 현재 run을 덮지 않음 | 실운영 장시간 스트리밍 soak 증거 추가 |

### 4.2 History — 97점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| 선택 research ID를 detail panel에 결속 | Compare/Tree/A-B/Heatmap/Funnel의 연구 맥락 일치 | 실제 운영 cold-start의 첫 인덱스 준비 비용 최적화 |
| DB+WAL signature와 cache | 최신 WAL 변경을 놓치지 않음 | 운영 데이터 p95를 장시간 수집해 합성 gate와 비교 |
| page cursor·has_more 검증 | 잘린 데이터를 완료 목록으로 오인하지 않음 | 대규모 campaign 검색 UX 개선 |
| holdout boolean·분모 정직성 | 실패가 분모에서 사라지지 않음 | holdout canonical field를 API schema에 더 명시적으로 문서화 |

### 4.3 Reports — 96점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| strict manifest v1 | 누락·추가·중복 key와 잘못된 envelope 거부 | 보고서 생성 UI에서 validation 실패 원인 안내 강화 |
| HTML/PDF source binding | 두 형식이 같은 원본인지 검증 | 전체 정본 보고서로 PDF 범위 확대 |
| atomic publication·rollback | 중간 snapshot과 복구본 유실 방지 | versioned report path와 보존 정책 정립 |
| sandbox iframe·no-referrer | 보고서 실행·referrer 경계 강화 | complementary landmark의 top-level 구조 개선 |

### 4.4 성과 — 94점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| 표본 내 성과와 운영 증명 분리 | 과최적화 결과를 실거래 증명으로 승격하지 않음 | profile/기간이 다른 인간·AI 결과의 비교 금지 규칙 강화 |
| Hall of Fame 접근성·스크롤 focus | 키보드로 표 탐색 가능 | benchmark denominator·OOS 상태를 표 열로 표준화 |
| metadata·출처 노출 | 성과 수치의 근거를 추적 가능 | 정규화되지 않은 legacy 성과를 별도 격리 |

### 4.5 Backtest — 97점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| run/gen 응답 identity와 abort | 다른 run 결과가 현재 차트에 표시되지 않음 | 장시간 job queue·cancel·timeout soak 자동화 |
| finite numeric/date validation | NaN·역순 날짜·문자열 boolean의 차트 오염 차단 | 복수 job 비교의 표본·기간 normalization 강화 |
| explicit no-trade 판정 | CSV 부재를 무거래로 오인하지 않음 | 실제 GUI backtest와 웹 결과의 주기적 parity gate |
| daily/equity/holdings raw fallback | SVG 밖에서도 원자료 확인 가능 | 200행 초과 자료의 다운로드 계약 검토 |

### 4.6 Replay — 96점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| 비활성 panel `hidden`·`aria-hidden`·`inert` | keep-alive 상태가 focus 순서를 오염하지 않음 | 저사양 환경 프레임 드롭 계측 |
| select/range 접근 이름 | 스크린리더로 transport 조작 가능 | 캔들·호가 차트의 키보드 cursor 탐색 |
| 외부 WebSocket 차단 검증 | 감사 브라우저가 loopback 밖으로 연결되지 않음 | 실제 replay WS reconnect·backpressure soak |

### 4.7 연구 자산 — 93점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| 비정본 preview 표시 | prototype을 정본 성과로 오인하지 않음 | catalog taxonomy와 owner를 정본 schema로 통합 |
| provenance·counts·상태 chip | 자산 출처와 상태 확인 가능 | 오래된 비정본 asset의 archive/retention 정책 |
| 216-case 반응형·대비 통과 | 좁은 화면에서도 catalog 사용 가능 | primary research journey와 보조 자산의 IA 분리 강화 |

### 4.8 설정 — 94점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| theme `aria-pressed`·button type | 현재 테마 상태가 보조기기에 전달됨 | axe `heading-order` moderate 정리 |
| focus 가능한 로그 영역 | 키보드로 로그 탐색 가능 | 로그 다운로드·필터·보존 기간 안내 |
| Bearer redaction·no-store | 민감정보 및 캐시 노출 감소 | 설정 변경별 영향 범위와 reset 결과 표시 강화 |

### 4.9 용어 — 96점

| 개선된 점 | 현재 효과 | 남은 개선 |
|---|---|---|
| 930개 문서 index 검증 | 용어·연구 문서 검색 기반 안정화 | 검색 relevance와 동의어 사전 개선 |
| metadata cache와 O(1) lookup | 문서 수 증가 시 반복 파싱 감소 | 현재 탭·차트와 관련 용어 자동 연결 |
| 반응형·키보드 행렬 통과 | 다양한 화면과 입력 방식 지원 | H1·region landmark 구조 공통 개선 |

## 5. 공통 플랫폼 점수

| 플랫폼 영역 | 점수 | 근거 | 다음 개선 |
|---|---:|---|---|
| 데이터 진실성·출처 | **98** | request identity, explicit boolean, finite validation, stale/error 구분 | API schema 타입을 프런트와 자동 공유 |
| 보고서 무결성 | **97** | strict v1, HTML/PDF 4/4, atomic rollback, SHA-256 | 전체 보고서 PDF 확대·보존 정책 |
| 성능·확장성 | **94** | 합성 2× cold/warm 예산 통과 | 실제 운영 History cold-start p95 개선 |
| 접근성·반응형 | **94** | 216/216, blocking 0 | H1/region/heading-order/complementary moderate 정리 |
| 코드 구조·유지보수 | **93** | ChartFrame 공통화, gate scripts, 테스트 확대 | V4 shell 결합도·CSS legacy 누적 추가 축소 |
| 테스트·배포·운영 | **98** | 880 tests, bundle attestation, PR/tag/deploy audit | CI에서 216-case와 scale gate 자동 실행 |
| **플랫폼 평균** | **95.7** | 95점 목표 달성 | medium debt를 v5.9로 이관 |

## 6. 현재 검증 증거

| 검증 | 결과 |
|---|---|
| Dashboard/API 전체 테스트 | `880 passed` |
| v5.8 집중 계약 테스트 | `75 passed` |
| Runtime JSX | `91 JSX / 539 graph files PASS` |
| App bundle | `15c4c554`, served SHA-256 일치 |
| 접근성 | `216/216 PASS`, serious/critical 0 |
| PDF provenance | `4/4 PASS` |
| Research docs index | `930 docs PASS` |
| Scale gate | PASS, `performance_proved=false` |
| Nonrelease sync | PASS |
| 부모·원격 HEAD | `b5c60420`, 일치 |
| 보호 경로 | 변경 없음 |

접근성 자동 행렬은 모든 탭에서 blocking 0이다. 남은 비차단 항목은 공통 `page-has-heading-one`, `region`, Reports/성과의 `landmark-complementary-is-top-level`, Live의 `empty-table-header`, 설정의 `heading-order`다.

## 7. 다음 작업 우선순위

| 우선순위 | 작업 | 완료 기준 | 연구 진행과 관계 |
|---:|---|---|---|
| P1 | 실제 운영 History cold-start 최적화 | 재시작 후 운영 데이터 p95 ≤1.0초 또는 원인별 예산 확정 | 연구와 병행 가능 |
| P1 | CI release gate 자동화 | PR에서 full tests, scale, PDF, 216 accessibility 자동 실행 | 연구와 병행 가능 |
| P2 | 접근성 moderate debt 제거 | H1/region/heading-order/complementary 위반 0 | 연구를 막지 않음 |
| P2 | 성과 비교 정규화 | profile·기간·OOS 불일치 비교 차단 | 연구 결과 해석 품질 향상 |
| P2 | 연구 자산 taxonomy 정리 | owner·정본/비정본·retention schema 확정 | 연구 산출물 누적 전에 권장 |
| P3 | 차트 linked inspection | 동일 run/gen/time range hover·brush 연동 | 연구 편의 기능 |
| P3 | Replay·Backtest soak | WS reconnect, queue/cancel, 장시간 실행 자동 검증 | 대규모 실험 전 권장 |

## 8. 연구 재개 판단

**판정: 연구를 재개할 수 있다.** 대시보드 개선을 더 완료할 때까지 연구를 전면 중단할 필요는 없다.

| 판단 축 | 상태 | 해석 |
|---|---|---|
| 연구 실행·관찰 | 가능 | Live·Backtest·History·Reports primary journey가 동작하고 검증됨 |
| 결과 정직성 | 가능 | stale/error/malformed/source mismatch를 정상 결과로 승격하지 않음 |
| 보고서 보존 | 가능 | HTML/PDF와 manifest provenance를 함께 검증 가능 |
| 접근성·반응형 | 가능 | 216개 조합에서 blocker 0 |
| 전략 성과 증명 | 미증명 | `performance_proved=false`; 새 연구는 별도 OOS·통계 검증 필요 |
| 실거래·V3K 후속 gate | 차단 유지 | 현재 작업은 V3K 승인 gate를 진전시키지 않음 |

### 권장 운영 방식

1. **연구 트랙을 주 작업으로 재개한다.** 조건 생성→공식 backtest→History 비교→Reports 출판 흐름을 사용한다.
2. **v5.9 품질 부채는 별도 브랜치에서 병행한다.** 연구 코드와 Dashboard 운영 개선을 같은 커밋에 섞지 않는다.
3. **새 성과는 자동 승격하지 않는다.** OOS, 표본 수, profile, 기간, 비용·슬리피지, holdout evidence를 함께 기록한다.
4. **운영 cold-start를 계속 계측한다.** 합성 scale PASS를 실제 운영 성능 증명으로 바꾸지 않는다.
5. **V3K gate는 현행 3/6을 유지한다.** 승인 문구·KHOPENAPI 증거 없이 live wiring이나 보호 DB 쓰기를 진행하지 않는다.

## 9. 최신 서비스 재배포 결과

| 항목 | 결과 |
|---|---|
| 재시작 시각 | 2026-07-22 현재 작업 |
| 실행 PID | `181324` |
| 주소 | `http://127.0.0.1:8770` |
| `/health` | 200, contract v2 |
| Bundle manifest | 200, 19.5ms |
| `/runs?fields=slim` | 200, 139.6ms |
| `/history/index?limit=50` | 200, cold 875.8ms |
| `/research_docs?limit=100` | 200, 30.6ms |
| `/reports` | 200, 558.3ms |
| `/debug/logs` 미인증 | 401 |
| Reports 브라우저 | v5.8.0, build 15c4c554, sandbox/no-referrer 정상 |
| History 브라우저 | 선택 탭·campaign 내용 정상 |
| Console/page error | 0 |

운영 cold History는 이번 재시작에서 1초 예산 안에 들어왔지만 단일 관측치이므로 성능 증명으로 승격하지 않는다. 장시간 p95 계측 과제는 유지한다.

## 10. 최종 결론

v5.8은 Dashboard 9개 섹션 평균 **95.3/100**, 공통 플랫폼 평균 **95.7/100**으로 평가한다. 현재 남은 문제는 연구를 차단하는 P0/P1 제품 결함이 아니라 실제 운영 cold-start, 접근성 moderate 구조, 성과 비교 정규화, 연구 자산 taxonomy와 같은 다음 릴리스 품질 부채다.

따라서 현재 단계는 **“대시보드 개발을 계속해야만 연구 가능한 상태”가 아니라, “연구를 재개하면서 v5.9 운영 품질을 분리 병행하는 상태”**다.
