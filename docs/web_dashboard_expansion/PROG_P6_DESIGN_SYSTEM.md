# P6 — 디자인시스템 랜딩(토큰 적용·타이포 ≥14px·반응형·WCAG) · PIXEL-CHANGING

> 2026-06-15. 프로그램 P6(former P5+P6 병합). 터미널 픽셀 변경 단계 — 사용자 사후 시각 승인 대상.
> 선행조건 OQ#2(밀집 데이터 폰트 예외목록)는 PROG_P6_DENSE_DATA_EXCEPTIONS.md 로 기본값 승인 완료.

## 한 줄 요약
P0 토큰을 styles.css 호출부에 적용(값 보존) + 본문 타이포 ≥14px(한국어 가독, 밀집 데이터는 예외 12px 유지) + 반응형 리듬(auto-fit) + WCAG AA 대비(양 테마). 정량 화면 정보밀도는 보존.

## 변경(styles.css 전용 + HTML 핀 + 핀 테스트)
- **타이포**: `body` 13→14px(상속 prose 만 상승; 명시 크기 가진 ~75 밀집 규칙은 불변 → 자동 보호). 직접 상속 밀집 1곳(`.mono`)만 `--fs-dense`(12px) 명시 오버라이드. prose 1곳(`.alert-danger` 모달/배너 경고문) 12→`--fs-prose`(14px).
- **토큰 롤아웃**(값 보존): gap 매칭 가능 79/79(100%, 전체 82%), border-radius 32/32(100%, 전체 44%) → `var(--space-*)`/`var(--radius-*)`. 비매칭(3/5/12/18px 등)은 토큰 없어 유지.
- **반응형**: `.engine-grid` `repeat(4,1fr)`→`repeat(auto-fit,minmax(180px,1fr))`, `.bt-summary-row`→`minmax(150px,1fr)`(기존 700px 2컬 폴백 유지). `.grid-main` 불변.
- **WCAG AA 대비**(양 테마): `--ink-2` 가 일부 bg 에서 normal AA(<4.5:1) 실패 → 밝기만 조정(색상 유지): dark `#6a7686→#778496`, light `#6a7686→#5f6a79`. 이후 ink-0/1/2 전 배경 ≥4.5:1(최저 4.51/4.55). `--ink-3`은 장식/faint 전용(36곳 감사 — placeholder·dot·코드주석 등) → AA-large 기준 유지. 매트릭스: PROG_P6_CONTRAST_MATRIX.md.
- **핀**: styles.css ?v= i→j(5 HTML) + validation_views 핀 j.

## 검증(M4 객관 + MVQA)
- **타이포 grep**: 14px 미만 잔여 112 규칙 — 전부 명시 크기 보유 + 밀집 예외목록 해당(표/게이지/축/뱃지/컨트롤/mono).
- **대비**: contrast-matrix(token×bg, 양 테마) — normal ≥4.5:1 실패 0(ink-2 수정 후). 커밋 아티팩트.
- **반응형**: 1280/1600/2200 × 6탭 × 2테마 — 가로 오버플로(scrollWidth>clientWidth, 비스크롤) **0**.
- **게이트**: 전체 pytest 7 failed(핀 베이스라인 동일) + 3229 passed — 신규 0. verify_nonrelease exit0. test_p14·design_pass·index_cache·p11_engine_gauges(엔진 하드코딩색 0) green.
- **MVQA**: 6탭×2테마×3폭 전/후 PNG(`$JOB/tmp/shots_p6/`). app.js/stom-ui 해시 불변(CSS-only). **사용자 8770 사후 시각 승인 대상**.

## 리뷰어 판단 플래그
- `--ink-2` hex 변경은 양 테마 전 ink-2 사용처에 영향(재베이스라인 단계 의도된 픽셀 변화).
- glossary/wiki/autopsy 본문(11.5/10.5/13px mono pre-wrap)은 참조/모노 pre 패널이라 확대 시 레이아웃 깨짐 → 밀집(참조/코드) 예외로 유지. 진짜 prose ≥14px 원하면 후속 결정.

## 다음
P7(HoF·freeze_verdict 공유 셸 통합 — 픽셀 변경, field-diff). 그 후 프로그램 완료.
