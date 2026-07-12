# 2026-07-12 G5 — 연구 관리 진행도 스코어카드(research_maturity) + /research_maturity

## 무엇
- `scripts/research_maturity_scorecard.py::build_scorecard` — 연구 파이프라인 9단계
  (엔진계약/생성/게이트/채점/부검·환류/증거원장/프로필·토글/대시보드/수익증명)를
  **결정론 실측 신호**(파일·AST·라우트 문자열·ro DB 행수)로 채점. JSON+마크다운 표,
  무예외(빈 저장소 → 전 단계 0점+note). CLI 산출은 `state/research_maturity.json`(비커밋).
- 대시보드 `GET /research_maturity` — 지연 import·무예외·읽기 전용·무캐시 즉석 계산.

## 현재 점수 (2026-07-12, 이 브랜치 HEAD)
전체 **77/100** — 엔진/생성/게이트/부검환류/대시보드 100, 프로필 91,
채점 60(Deflated Sharpe·PBO 미구현 −40), 증거원장 40(스키마 존재·행수 0),
**수익증명 0(하드코드 — CL-R08~R10 승인 게이트 전 고정)**.

## 정직성 설계 (레드팀 실증)
- 수익증명 0점은 **우회 불가**: docs/update_log에 허위 "CL-R08 완료" 문구를 주입해도
  점수 불변(QA E2 게임화 공격 실증 — 스캔 결과는 note에만, 점수는 하드코드 False).
- **한계 고지**: 존재 기반 신호는 빈 파일/가짜 행으로 개별 단계 부풀리기 가능 —
  advisory 지표이지 감사 증명 아님(행 품질·계보는 EvidenceStore/CL-R 게이트 소관).
  모듈 docstring에 동일 고지 명문화.

## 검증
- 단위 21종(결정론 3회 byte-동일·빈/파일/권한거부 경로 무예외·9단계·0점 락·CLI exit0)
  + 엔드포인트 4종(정상/무캐시/모듈 부재/raise 흡수). QA 레드팀 5케이스 PASS
  (결정론·게임화 공격·무예외·라이브 :8803 200·loop_runs.db sha 불변).
