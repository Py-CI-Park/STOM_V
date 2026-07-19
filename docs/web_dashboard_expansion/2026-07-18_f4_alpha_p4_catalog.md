# F4 — Alpha P4 연구 카탈로그 (research_assets.db + SELECT-only API + 뷰)

- 작성: 2026-07-18 · 브랜치: `f4-alpha-p4-catalog`

## Part 1 — research_assets.db 빌드

- `python scripts/build_research_catalog.py` → `legacy_non_authoritative_catalogs/research_assets.db`(gitignore, 빌드 산출물).
- 적재: assets 27 · judgments 7 · clauses 38 · strategies 62 · cells 144 · ledger_mirror 264. 원천 13건.

## Part 2 — SELECT-only 읽기 API (research_api.py, §2026-07-12 data contract)

- `GET /research/summary` — 테이블 카운트 + DB mtime/size.
- `GET /research/assets?limit=` — 자산 목록(bounded ≤500).
- `GET /research/judgments` — 판정카드(verdict + key_metrics JSON 파싱, 깨진 JSON error 플래그).
- 보안·계약: sqlite `mode=ro`(원본 무변형·쓰기 시 OperationalError), 재계산 없음, DB 부재는 500 아닌
  error envelope(available=false + build 힌트).
- 테스트 4종: 합성 DB summary/assets, judgments 파싱·error 플래그, 부재 envelope, read-only 강제.

## Part 3 — 카탈로그 뷰 (v4-catalog.jsx, 보조 탭 "카탈로그")

- 카운트 타일 6종 + 판정카드(verdict 색상: PASS/양성/생존=녹, KILL/무가치=적) + 자산 표(27행).
- 셸 배선(secondary 그룹), P4 배지, DB 아이콘. 파리티 가드 통과.

## 검증

- 회귀: parity + catalog api 7 통과. 번들 v=0b62e34f, v4.css?v=20260718f4.
- 라이브(실 DB): summary counts 6종, judgments 7 실판정(B1 PASS·D1 양성·D5-R/O-1G/S/W5 KILL/무가치·min 생존).
- 실브라우저: 카탈로그 탭 카운트·판정카드 색상·27 자산 표 렌더. artifacts/f4_catalog.png.

## 남은 뷰(후속)

- 계약의 5뷰 중 판정카드·자산 구현. 함정지도(cells)·절실험실(clauses)·출구은행·B1 live scorecard 는 후속 슬라이스.
