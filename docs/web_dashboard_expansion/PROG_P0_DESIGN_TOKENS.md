# P0 — 디자인 토큰 스캐폴딩(간격/모서리/타이포 스케일) · ENABLING · PIXEL-NEUTRAL

> 2026-06-14. 대시보드 스타일·구조 개선 프로그램 Phase 0. P6(디자인시스템 랜딩)의 선행.

## 한 줄 요약
간격/모서리/타이포 **스케일 토큰을 `:root`에 가산 정의**(현행 어떤 호출부도 미참조 → 픽셀 변화 0). 호출부 치환은 P6. 각 값은 현행 de-facto 리터럴과 **byte-동일**(px↔px) → P6 롤아웃이 값 보존.

## 토큰 (styles.css `:root, [data-theme="dark"]`)
간격/모서리/폰트는 색이 아니라 **테마 무관** → :root 1회 정의(라이트 테마로 캐스케이드).

| 토큰 | 값 | 근거(현행 빈도) |
|------|----|----------------|
| `--space-1` | 4px | gap:4px(14회) |
| `--space-2` | 6px | gap:6px(13회) |
| `--space-3` | 8px | gap:8px(29회·최빈) |
| `--space-4` | 10px | gap:10px(12회) |
| `--space-5` | 14px | gap:14px(5회) |
| `--space-6` | 16px | gap:16px(4회) |
| `--radius-sm` | 4px | border-radius:4px(15회) |
| `--radius-md` | 6px | border-radius:6px(14회) |
| `--radius-lg` | 10px | border-radius:10px(3회) |
| `--fs-prose` | 14px | **한국어 가독 목표**(현행 미참조 — P6 적용 전까지 픽셀 불변) |
| `--fs-dense` | 12px | 밀집 표/수치(현행 존재값) |
| `--fs-label` | 11px | 라벨/캡션(현행 존재값) |

## 픽셀 중립 보장(M3)
- **가산 전용**: 위 토큰 이름은 `:root` 정의에만 등장, 어떤 호출부도 참조 안 함(grep 확인) → 렌더 픽셀 0 변화.
- **단위 보존**: 모두 px(rem/em 변환 없음), 현행 리터럴과 byte-동일 → P6 치환 시 값 보존.
- 진짜 중립성은 자동 스냅샷 인프라가 없으므로 MVQA "no perceptible change"로 확인.

## 변경
- styles.css: `:root` 블록에 12개 토큰 가산.
- 5 HTML: `styles.css?v=20260614g → 20260614h`(수동 핀).
- test_dashboard_validation_views.py: 핀 단언 g→h. (test_design_pass 캐시테스트는 핀-불특정 → 무수정.)

## 검증
- grep: 토큰 이름이 styles.css `:root` 정의에만 등장(호출부 0).
- 전체 pytest == 핀 베이스라인; 두 핀 테스트 green.
- MVQA: 6탭 PNGs, no perceptible change.

## 다음
P2(사이드바 중복 제거) → P3 → P4 → **P6(토큰 롤아웃 — 이 스케일 적용)** → P7.
