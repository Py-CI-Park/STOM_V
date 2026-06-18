# P3 — 진화 IA 완화: 섹션 그룹 접이식(`<details>`) · 기본 펼침

> 2026-06-14. 대시보드 스타일·구조 개선 프로그램 Phase 3.

## 한 줄 요약
진화 탭의 7개 SectionLabel 그룹을 **네이티브 `<details>` 접이식**으로 — 기본 펼침(첫 페인트는 기존과 동일, disclosure caret 만 추가), localStorage 영속, 키보드 동작, `aria-expanded`. 패널 이동/제거/재정렬 0(계약 순서 유지). ~31패널 단일 스크롤을 사용자가 접어 정리 가능.

## 변경
- **app.jsx `_EvoSection({storageKey,label,children})`**(신규, SectionLabel 뒤): 제어형 `open`(localStorage 초기값=없으면 true) + `onToggle` 영속 + `<summary>`(aria-expanded) + `.evo-group-body`(flex 14px 리듬 보존). `label`은 기존 `<SectionLabel text="..."/>` 엘리먼트를 그대로 받아 → **리터럴 `text="..."` 가 호출부에 보존**(design_pass/integrated_layout 계약 유지).
- 7개 그룹 래핑: Run Monitor / Strategy·Prompt / Compare / Generation Analytics / Research Lab(+P2 버튼) / 진화 분석 P1~P5 / 판정. ExportStatusBanner·무라벨 차트군은 미래핑.
- **styles.css**: `.evo-group`/`.evo-group-summary`(네이티브 마커 제거 + 작은 caret + focus-visible)/`.evo-group-body`. styles.css ?v= h→i(5 HTML) + validation_views 핀 i.
- 빌드 산출물 재생성·커밋(app.js v=deabd553, manifest) — M2.

## 가드/픽셀
- 기본 펼침 → 펼친 상태 첫 페인트는 기존과 동일(유일 시각 델타 = 섹션 헤더의 작은 disclosure caret + summary 미세 간격). 패널/순서/내용 불변.
- 계약: design_pass(SectionLabel 리터럴 + .stom-section-label) green; integrated_layout 순서(text=라벨 < 패널) green; no_duplicate_globals(_EvoSection 유일) green; p14/index_cache/phase9 green.
- 복귀 사용자(접힌 상태 영속)는 비-기준 첫 페인트 — 의도된 동작(회귀 아님).

## 검증
- 전체 pytest 7 failed(핀 베이스라인 동일) + 3229 passed — 신규 0. verify_nonrelease exit0.
- 8771: localStorage clear 후 **details.evo-group 7개·전부 open(기본 펼침)**, 7 summary 라벨 정확; 첫 그룹 토글 open→closed 동작; 6탭 0 pageerror. code-review (별도 패스).

## 다음
P4(PIPELINE 통합·format.ts) → [P6 전 정지: 사용자 OQ#2 결정 + 시각 재베이스라인 승인 필요].
