# STOM V2UC Dashboard 95점 실행 계획

- 실행 브랜치: `audit/dashboard-forensic-review-after-a8ba6c83`
- 기준 커밋: `808b4cc0`
- 기준 점수: 대시보드 61/100, HTML 보고서 52/100
- 최소 완료 목표: 두 영역 모두 90점 이상
- 도전 목표: 두 영역 모두 95점 이상
- 병행 목표: History·Wiki·Reports 체감 지연 제거
- 근거 감사: `2026-07-20_dashboard_forensic_audit_after_a8ba6c83.md`
- 구조 계획: `2026-07-20_dashboard_forensic_improvement_plan.md`

## 1. 완료 정의

다음 조건을 모두 충족해야 “90점 이상 완료”로 판정한다.

1. 정본 상태와 화면 상태 불일치 0
2. authoritative error/partial/stale 은폐 0
3. History 선택 research ID가 모든 상세 패널을 실제 구동
4. shell의 run/research context와 탭 본문 불일치 0
5. `/runs?fields=slim`이 full generation payload를 만들지 않음
6. History cold p95 ≤1.0초, warm p95 ≤0.10초
7. Wiki 첫 색인 cold p95 ≤1.0초, warm p95 ≤0.15초
8. report 선택당 HTML GET 1회, TOC anchor 이동 GET 0회
9. 보고서 수치 의미 오류 0, broken link 0, manifest/hash mismatch 0
10. 다중 cycle→generation→condition→backtest→validation→decision 보고서 계약 존재
11. 375/768/1280/1920/2560/3440과 200% zoom 전역 overflow 0
12. keyboard tab/dialog, contrast, reduced-motion 주요 계약 통과
13. focused unit/API/browser 테스트 신규 실패 0
14. 동일 bundle hash의 성능·브라우저·보고서 증거를 남김

95점은 위 조건에 더해 다음을 요구한다.

- current와 2× 데이터 fixture에서 성능 예산 유지
- report JSON envelope와 standalone HTML/PDF 모두 동일 provenance를 표현
- 모든 핵심 차트에 단위·기간·표본·freshness·threshold/baseline·대체표 계약 적용
- axe/키보드/인쇄/색각 검증과 독립 최종 구조 리뷰에서 Major 0

## 2. 실행 트랙과 파일 범위

### Track A — 데이터 정직성·ResearchContext

주 파일:

- `ai_strategy_loop/dashboard/frontend/v4-research.jsx`
- `ai_strategy_loop/dashboard/frontend/panels-analysis.jsx`
- `ai_strategy_loop/dashboard/frontend/panels-config.jsx`
- `ai_strategy_loop/dashboard/frontend/dashboard-v4-shell.jsx`
- `ai_strategy_loop/dashboard/frontend/v4-history.jsx`

작업:

- `complete` 포함 공용 상태→stage 매퍼 도입
- missing/pending/error/partial/stale/ready 상태 분리
- derived fallback을 보조 근거로 격하
- `ResearchContext`를 shell에서 소유하고 History·Reports·Backtest에 전달
- History 선택 ID를 Compare/Tree/A-B/Heatmap/Funnel/Index에 전달
- stale request abort/request generation guard 통합

수용 조건:

- 상태 fixture 6종과 archive fixture 3종에서 문구·stage·source badge 정확
- History 선택 변경 후 하위 endpoint가 모두 동일 research ID 사용
- 탭 헤더와 본문 context mismatch 0

### Track B — History/Wiki/Runs 성능

주 파일:

- `ai_strategy_loop/dashboard/app.py`
- `ai_strategy_loop/dashboard/history_api.py`
- `ai_strategy_loop/dashboard/research_records.py`
- `ai_strategy_loop/dashboard/research_api.py`
- `ai_strategy_loop/dashboard/frontend/runs-shared.jsx`
- `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`

작업:

- slim runs 전용 readonly aggregate 조회
- campaign summary index와 detail cache 분리
- History metadata index에서 전체 ResearchNode 구축 제거
- source signature+single-flight cache
- Markdown sidecar metadata cache와 O(1) doc lookup
- server search/pagination, ETag/304 기반 재검증

수용 조건:

- 현재 527 runs/5,364 generations/930+ docs에서 계획 성능 예산 통과
- cache miss 동시 요청의 중복 build 1회
- source mtime 변경 후 bounded invalidation
- Compare 필수 지표 누락 0

### Track C — HTML 보고서 정본화

주 파일:

- `ai_strategy_loop/dashboard/report_writer.py`
- `scripts/build_step_reports.py`
- `scripts/build_research_report.py`
- `ai_strategy_loop/dashboard/frontend/v4-reports.jsx`
- `ai_strategy_loop/dashboard/app.py`

작업:

- `stom-research-report-v1` JSON envelope 정의
- run/step/assets/manifest 단일 staging 출판
- source/content hash, schema, status, trust, research/run/gen/cycle metadata
- 조건식 전문/hash/diff, backtest, validation, AI/human insight, decision, limitation 포함
- 독립 후보 profit 합산 제거
- MDD 산점도 위험 방향 설명 교정
- 존재하는 상세 리포트만 링크
- report catalog API에 typed metadata와 TOC 제공
- iframe 본문 단일 요청과 anchor remount 제거

수용 조건:

- golden synthetic research E2E
- manifest↔파일↔hash↔link 전건 일치
- `<script>`/이벤트 handler/외부 asset 0
- standalone/offline/print에서 핵심 내용 보존

### Track D — 스타일·차트·접근성

주 파일:

- `ai_strategy_loop/dashboard/frontend/styles.css`
- `ai_strategy_loop/dashboard/frontend/v4.css`
- `ai_strategy_loop/dashboard/frontend/chart-equity.jsx`
- `ai_strategy_loop/dashboard/frontend/v4-charts.jsx`
- 탭별 chart panel

작업:

- 미정의 `--line` 제거
- 필수 본문 `--ink-3` 사용 교정
- `.v6-graphs`, `.v55-board-main`, stage cell 상충 규칙 통합
- fixed-height nested scroll 축소
- 2/3/4열 표시와 실제 grid 일치
- 공통 ChartFrame metadata/fallback 계약
- Tabs/Dialog keyboard와 focus trap/restore 완성
- mobile/zoom breakpoint 교정

수용 조건:

- undefined CSS variable와 상충 selector 0
- 필수 텍스트 WCAG AA
- 모든 viewport에서 scrollWidth≤clientWidth
- chart clipping/label overlap 0
- 차트마다 제목·단위·기간·표본·freshness·대체 요약 제공

### Track E — 관찰성·품질 게이트

주 파일:

- `ai_strategy_loop/dashboard/app.py`
- `ai_strategy_loop/dashboard/frontend/dashboard-v4-shell.jsx`
- `tests/unit/dashboard/`
- `scripts/`의 기존 검증기

작업:

- fail-safe console capture
- idempotent/redacted/session-protected backend logs
- Server-Timing과 response bytes
- API 성능 회귀 테스트
- real browser geometry/network/keyboard suite
- report schema/hash/link/drift suite

수용 조건:

- 로그 중복·민감값 노출 0
- 성능 예산 CI 검출 가능
- 실제 브라우저에서 console/page/request error 0

## 3. 실행 순서

1. **P0 정합성**: status/fallback/log 오류부터 교정
2. **성능 정본**: runs/history/wiki indexing과 cache
3. **보고서 무결성**: 수치 오류·manifest·broken links
4. **ResearchContext**: History/Reports/Backtest 연결
5. **보고서 UX**: typed catalog와 단일 본문 요청
6. **CSS/Chart 정리**: 상충 규칙 제거 후 시각화 강화
7. **자동 검증**: 단위→API budget→browser→final architecture review

앞 단계의 계약이 끝나기 전 다음 단계가 같은 API/CSS owner를 수정하지 않는다.

## 4. 커밋 단위

1. `계획: 대시보드·보고서 95점 실행 계약`
2. `수정: 연구 상태와 오류 표시 정본화`
3. `성능: runs·history·wiki 인덱스 경량화`
4. `보고서: 정본 스키마와 출판 무결성 구축`
5. `기능: 연구 컨텍스트와 리포트 카탈로그 연결`
6. `리팩터: CSS·차트·접근성 계약 정리`
7. `검증: 성능·브라우저·보고서 품질 게이트 봉인`
8. `문서: 최종 점수와 증거 원장`

## 5. 점수 재평가 기준

| 영역 | 배점 | 90점 목표 | 95점 목표 |
|---|---:|---|---|
| 기능·프로세스 | 18 | 17 | 18 |
| 데이터 정직성 | 15 | 14 | 15 |
| 정보구조 | 12 | 11 | 12 |
| UX·시각화 | 15 | 13 | 14 |
| 성능 | 12 | 11 | 12 |
| 접근성·반응형 | 10 | 8 | 9 |
| 코드 구조 | 10 | 9 | 9 |
| 테스트·운영 | 8 | 7 | 8 |
| 합계 | 100 | 90 | 97 |

보고서 하위 시스템은 기능 20, 정보구조 12, 시각화 12, provenance/insight 14, 성능 8, 접근성/인쇄 10, 코드/schema 14, 테스트/보관 10으로 별도 계산한다. 무결성 오류나 broken link가 하나라도 남으면 최대 89점으로 제한한다.

## 6. 중단·회귀 기준

다음 중 하나가 생기면 해당 변경은 병합하지 않고 원인 단계로 돌아간다.

- report 수치 의미 또는 gate 판정 변화가 근거 없이 발생
- protected DB/실거래/export 경계를 변경
- History/Reports cold p95 악화
- 기존 CSP+sandbox·path boundary 약화
- 전역 overflow를 `overflow-x:hidden`으로 숨김
- 오류를 demo/derived 데이터로 대체
- CSS 파일 끝 override로만 회귀를 가림
- 테스트를 삭제·완화해 통과

## 7. 최종 산출물

- 제품 코드와 번들
- `stom-research-report-v1` schema/envelope/manifest
- regenerated representative reports
- focused unit/API/browser tests
- cold/warm 성능 JSON
- viewport geometry/network/console 증거
- 최종 대시보드·보고서 점수표와 미달 항목 원장
