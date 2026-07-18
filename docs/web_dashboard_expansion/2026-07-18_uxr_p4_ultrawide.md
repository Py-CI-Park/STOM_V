# UXR-P4 — 울트라와이드·반응형 (CSS-only)

- 작성: 2026-07-18 · 브랜치: `uxr-p4-ultrawide`

## 변경 (v4.css, 신규 미디어쿼리만 — 표준 해상도 불변)

- `@media (min-width: 2400px)`: Live 사이드 컬럼 352→420px, stage 패딩 확대, 주인공 차트 min-height 460px, 프로즈 `max-width:68ch`(초광폭 줄길이 폭주 방지).
- `@media (min-width: 3200px)`: 사이드 480px, stage 패딩 `18px 40px 52px`(여백 프레이밍), 주인공 차트 520px.
- `v4.css?v=` 핀 `20260718p4`.

## 검증 (실브라우저 3해상도 — 점진·무회귀)

| 뷰포트 | `.v4-rlive` grid | side |
|---|---|---|
| 1920 | `1442px 352px` | 352 (브레이크포인트 아래 **불변**) |
| 2560 | `1990px 420px` | 420 |
| 3440 | `2782px 480px` | 480 |

- 3440에서 LIVE 연결(백엔드 v2)·gen_14 데이터로 fitness 곡선·수익추이·품질지표·사이클·BEST 패널이 넓은 화면을 밀도 있게 채움. `artifacts/uxr_p4_{3440,2560,1920}.png`.

## 다음(P5 Live 스테퍼)

- raw phase → 표시 상태기계, follow-live vs user-pinned, 텍스트→시각화(§10-9).
