# 대시보드·HTML 보고서 90점 완료 증거 원장

- 감사 브랜치: `audit/dashboard-forensic-review-after-a8ba6c83`
- 실행 계획: `2026-07-20_dashboard_95_execution_plan.md`
- 기준 점수: 대시보드 61/100, HTML 보고서 52/100
- 현재 판정: **대시보드 92/100, HTML 보고서 93/100, 90점 게이트 PASS**
- 운영 성과 판정: **`performance_proved=false` 유지** — 이번 작업은 UI·데이터 정직성·응답 성능·보고서 무결성 개선이며, 신규 통제 A/B 또는 운영 연구 실행을 하지 않았다.

## 1. 산출물 감사

| 계획 산출물 | 현재 근거 | 판정 |
|---|---|---|
| 정본 상태 표시 | `complete`를 완료 stage로 매핑하고 error/partial/stale의 authoritative 상태를 derived fallback으로 덮지 않음 | PASS |
| History 연구 맥락 | `campaign:<name>` typed ID가 Compare/Tree/A-B/Heatmap/Funnel/Index에 전달되며 비호환 패널은 독립 분석임을 명시 | PASS |
| slim runs | readonly grouped generation summary 경로로 full comparison payload 생성을 제거 | PASS |
| History 경량 색인 | campaign별 ResearchNode build와 run별 반복 query 제거, aggregate query+TTL/single-flight cache 적용 | PASS |
| Wiki 경량 색인 | 930문서 `stom-research-doc-index-v1` sidecar, O(1) lookup, server search/limit/offset, path traversal 차단 | PASS |
| 보고서 정본 | `stom-research-report-v1`, source/content hash, status/trust/profile/evidence/decision/limitations/TOC, manifest-last 출판 | PASS |
| 대표 HTML 보고서 | complete 2건과 `aborted_wrong_profile` 1건을 실제 DB 상태·세대 근거로 재생성 | PASS |
| Reports UX | typed catalog, 미등록 격리, 검색/필터, provenance/hash badge, decision/evidence, collapsible metadata TOC | PASS |
| iframe 보안 | CSP `default-src 'none'`, `sandbox=""`, `referrerPolicy="no-referrer"`, 선택당 본문 GET 1회 | PASS |
| 로그 경계 | process-local session 필수, redaction, idempotent ring handler | PASS |
| 번들 | dashboard `v5.7.0`, `app.js?v=80bc17cb`, HTML pin 동기화 | PASS |
| 설계 정본 | `DESIGN.md`를 현재 9탭+Context drawer, esbuild, 6 viewport 계약으로 갱신 | PASS |

## 2. 성능 증거

현재 실데이터는 527 runs, 5,364 generations, 930 Wiki 문서다. 같은 `80bc17cb` 번들을 제공한 loopback uvicorn/Chromium에서 측정했다.

| API | cold | warm | bytes | 계획 예산 | 판정 |
|---|---:|---:|---:|---:|---|
| `/history/index?limit=50` | 614.2 ms | 7.0 ms | 15,584 | cold ≤1.0s, warm ≤0.10s | PASS |
| `/research_docs?limit=100` | 46.9 ms (fresh process) | 6.8~10.6 ms | 27,580 | cold ≤1.0s, warm ≤0.15s | PASS |
| `/reports` | 208.4 ms | 7.3 ms | 10,254 | cold ≤1.0s | PASS |
| `/runs?fields=slim` | 144.0 ms | 118.6~135.2 ms | 250,323 | full generation payload 미생성 | PASS |

개선 전 실측은 History 8.45s, Wiki 20.29s였다. 최종 cold 기준 감소율은 각각 약 92.7%, 99.8%다.

## 3. 보고서 무결성 증거

- manifest schema: `stom-research-report-v1`
- 등록 보고서: 4건
- 파일 존재/bytes/content SHA-256 불일치: 0건
- 미등록 HTML: 18건, UI에서 `미등록·검증 불가`로 격리
- 잘못된 run 상태 승격: 0건. `lat_smoke_tick_full_sanitized_20260704`는 `aborted_wrong_profile`과 승격 금지 결론을 표시한다.
- TOC: 대표 run 보고서 7개 metadata anchor
- TOC open 및 anchor UI 변경 뒤 `/reports/view` 추가 GET: 0회
- iframe 동시 개수: 1, 최초 본문 GET: 1회
- report writer golden/보존/tamper/print/scriptless-nav 테스트 통과

## 4. 브라우저·접근성 증거

Chromium, bundle `80bc17cb`:

- 375/768/1280/1920/2560/3440px Reports geometry: 모든 `scrollWidth == clientWidth`, overflow 0
- 200% page scale: layout overflow 0, visual viewport 640px, tab 물리 높이 52px
- 375px: report body 359px, iframe 357px, mode tab CSS 높이 44px, overflow 0
- Reports mode tab ArrowRight/ArrowLeft: focus와 `aria-selected`가 함께 이동
- Reports provenance, status, trust, schema, content/source hash 표시 확인
- Wiki 첫 목록 150/전체 930, `측정계` 서버 검색 1/전체 1 확인
- History 선택 표시 `campaign:q4-defense-prerule-halfexit-dashboard-20260618`와 비호환 패널 독립성 안내 확인
- frontend error buffer: 0건
- Reports 본문 request: 선택당 1회

## 5. 자동 검증

- `npm run build`: runtime JSX **90/538 PASS**, Vite PASS, `app.js v=80bc17cb`
- `python -m pytest tests/unit/dashboard/ -q -p no:cacheprovider`: **778 passed in 446.98s**
- `python scripts/verify_nonrelease_sync.py`: **PASS**
- report manifest 파일/bytes/SHA-256 전건 검사: **4/4 PASS**
- `git diff --check`: 오류 0

## 6. 점수 재평가

### 대시보드 92/100

| 영역 | 점수 | 근거 |
|---|---:|---|
| 기능·프로세스 | 17/18 | 9탭 정본 셸, History context, Reports/Wiki 완성 |
| 데이터 정직성 | 15/15 | 상태·프로venance·미등록 경계와 실패 상태 보존 |
| 정보구조 | 11/12 | typed context/catalog/TOC, 정본 설계 갱신 |
| UX·시각화 | 13/15 | 고밀도 catalog·report insight·대표 report 시각화 |
| 성능 | 12/12 | History/Wiki/Reports 예산 통과 |
| 접근성·반응형 | 8/10 | 6 viewport, 200%, keyboard, print/reduced-motion 계약 |
| 코드 구조 | 9/10 | owner 분리, readonly cache, sidecar builder, schema |
| 테스트·운영 | 7/8 | 778 unit + live browser + verifier |
| 합계 | **92/100** | **90점 목표 달성** |

### HTML 보고서 93/100

| 영역 | 점수 |
|---|---:|
| 기능 | 19/20 |
| 정보구조 | 11/12 |
| 시각화 | 10/12 |
| provenance/insight | 14/14 |
| 성능 | 8/8 |
| 접근성/인쇄 | 9/10 |
| 코드/schema | 13/14 |
| 테스트/보관 | 9/10 |
| 합계 | **93/100** |

## 7. 95점 미달 원장

90점 완료와 별개로 다음 항목은 증거가 없어 95점을 주장하지 않는다.

1. current의 2배 데이터 fixture에서 p95 성능 재검증
2. standalone HTML과 PDF의 동일 provenance 렌더 증명
3. axe·색각·독립 reviewer 최종 Major 0 증거
4. 모든 핵심 차트의 단위·기간·표본·freshness·threshold/baseline·대체표 전수 계약
5. 신규 실제 연구 실행 기반 운영 성과 A/B 증명(사용자 승인·비용 필요)

이 미달 항목은 현재 90점 완료를 막지 않지만, 95점 또는 `performance_proved=true`의 근거로 사용할 수 없다.


## 8. 2026-07-21 부모 통합 전 독립 재감사

두 개의 독립 Architect 리뷰가 최초 `BLOCK`으로 판정한 항목을 모두 원인 수정했다.

- History의 기존 stage/count/status 계약 복원과 DB+WAL freshness
- `/research_docs` 무제한 기본 계약과 문자 단위 `size` 복원
- Markdown symlink/junction allowlist 탈출 차단
- report catalog schema/bytes/content SHA-256 검증과 single-flight
- Bearer credential/path redaction 및 `Cache-Control: no-store, private`
- 다중 보고서 출판 실패 시 파일·manifest 전체 rollback
- canonical SQLite read-transaction source digest
- canonical 성공 상태 `ok`만 포함하는 성과 집계와 실패 건수 분리
- Wiki loading/error/empty·abort·stale response 분리
- checkout mtime과 무관한 상대 ID+content SHA-256 Wiki sidecar drift gate

대표 run 보고서 3건을 다시 생성했으며 각 `source_sha256`은 서로 다른 canonical snapshot digest다. 최종 독립 재검토는 백엔드와 보고서 모두 `CLEAR`, `merge_safe=true`다.

검증 증거:

- `app.js v=09415e55`, runtime JSX 90/538 PASS
- dashboard + History/Wiki API: **818 passed**
- release-blocker focused suite: **108 passed**
- tracked Wiki sidecar parity: **7 passed**, `--check` 930문서 PASS
- report writer: **13 passed**, 등록 보고서 4건 bytes/content SHA-256 PASS
- History cold/warm: 642.3ms / 14.3~48.0ms
- Wiki cold/warm: 28.3ms / 9.5~24.3ms
- `performance_proved=false` 유지
