# UXR-P7 — Reports 허브(보안 서빙) + History identity 계약

- 작성: 2026-07-18 · 브랜치: `uxr-p7-reports`

## 1. Reports 허브 (구현 완료 — 보안 서빙)

`build_html.py`가 명시한 설계 의도("reports/ 폴더 → 대시보드 iframe/정적 서빙")를 **보안 우선**으로 구현.

### 백엔드 (app.py)
- `GET /reports` — docs/ 하위 `*.html` 목록(경로·크기·mtime). 루트 하위만 walk(무예외).
- `GET /reports/view?path=` — 리포트 HTML 서빙.
  - `_safe_report_path`: realpath 후 루트 경계 접두 검사로 **traversal 차단**, 비-html·부재·null byte 거부(404).
  - **CSP `default-src 'none'`**(script-src 없음 → inline JS 포함 리포트도 스크립트 전면 차단), `style-src 'unsafe-inline'`(자가완결 리포트 스타일 허용), `img-src data: blob:`, `frame-ancestors 'self'`.
  - `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Cache-Control: no-store`.

### 프론트 (v4-reports.jsx + 셸 배선)
- Reports 탭(primary 그룹, key=reports) — 목록 + 선택 리포트를 **`sandbox=""` iframe**(스크립트·동일출처·폼·팝업 전면 차단)로 렌더.
- **이중 방어(§10-5)**: 백엔드 CSP + 프론트 sandbox → alpha_lab reporting 산출물의 inline JS 도 실행 불가.
- 빈 상태·로딩·에러 처리, `referrerPolicy=no-referrer`.

### 검증
- 보안 테스트 10종: traversal(`../`·절대경로·`..\\`·중첩)·비-html·빈·null byte → 404; 유효 리포트 200 + CSP(default-src 'none', script-src 없음) + nosniff; `_safe_report_path` 경계 단위.
- 라이브: docs/ **18개 실제 리포트** 서핑(process_flow·orderflow_auto_discovery·b1_program_report 결산 등), CSP 헤더 실측, traversal 404 실측.
- 실브라우저: Reports 탭 18목록 + iframe(process_flow.html 인라인 CSS 완전 렌더, 스크립트 차단, sandbox=""). `artifacts/uxr_p7_reports.png`.
- 회귀: parity·security_boundary·validation_views 등 79 통과. 번들 v=a3ac88b0, v4.css?v=20260718p7.

## 2. History identity (§10-10) — 후속(P7b) 문서화

Reports(보안 신설)를 우선 완료. History stable ID·join precedence·pagination·partial/conflict 응답 계약(§10-10)은 기존 V4History 데이터 계약 리팩터로, 별도 후속 슬라이스로 진행한다(현 V4History는 run/gen 아카이브·Compare·검색 기능 유지 — 회귀 없음).

## 3. Audit 거버넌스 이전 (P3 스코핑 승계)

P3에서 Audit를 보조군으로 구획(삭제 아님)했고, 지정 이전처로 Reports 허브가 이제 존재한다. 거버넌스(freeze/verdict/decisions/export)의 Reports 이전은 dual-mount + parity 통과 후 수행하는 후속(§10-1·§10-7) — 현재 Audit 탭은 보조군에서 완전 기능 유지.

## 4. UX 로드맵 종합 (P1~P7 완료)

- P1 관측(4401 발견) · P2 세션 근본수정+안정화 · P3 IA 정리 · P4 울트라와이드 · P5 Live 상태기계 · P6 Backtest parity 인벤토리 · **P7 Reports 보안 허브**.
- 남은 후속: History identity 데이터 계약(P7b), Audit 거버넌스 Reports 이전, Backtest GUI field 대조 결손 보강, Alpha P4 카탈로그(P8).
