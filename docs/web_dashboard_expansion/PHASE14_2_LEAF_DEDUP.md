# Phase 14.2 — 리프/유틸 첫 실전 전환 (포매터 de-dup)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_1_BUILD_HARNESS.md`.
> **목표**: 14.1에서 양립(중복)시켰던 디스플레이 포매터를 **빌드 번들 단일 출처**로 통합(de-dup). connection.jsx는 정의를 버리고 window 별칭만 둔다. 첫 진짜 "babel→빌드" 전환.

## 한 줄 요약
`connection.jsx`의 포매터 6종(`fmtScore/fmtPct/fmtMoney/fmtInt/fmtTime/STATUS_KR`) **정의를 제거**하고 `const fmtScore = window.fmtScore` 형태의 **window 별칭**으로 교체. 구현 정본은 이제 `webui-build/src/format.mjs`(→ `bundle/stom-ui.js`)뿐. 화면 동작 변화 0.

## 무엇이 바뀌었나
| | 14.1 | 14.2 |
|---|---|---|
| 포매터 구현 | connection.jsx **와** format.mjs 양쪽(중복) | **format.mjs(번들) 단일 출처** |
| connection.jsx | 포매터 정의 보유(babel 폴백) | 정의 제거 → `window.*` 별칭만 |
| 소비처 | bare `fmtMoney(...)` → connection.jsx 정의 | bare `fmtMoney(...)` → **번들 window 전역** |

## 왜 안전한가 (검증된 근거)
- **bare-식별자 해소**: connection.jsx에서 `const fmtMoney` 정의를 없애도, 다른 .jsx의 bare `fmtMoney(...)`는 전역 `window.fmtMoney`(번들 제공)로 해소된다. 실화면 6탭 전수 클릭 결과 **pageerror 0**으로 실증(backtest-charts·table·cards·chart·evolution-analysis·research-pro 등 bare 소비처 정상 렌더).
- **로드 순서**: 번들(ESM 모듈)은 babel 실행(DOMContentLoaded)보다 먼저 실행되어 `window.fmt*`를 세팅 → connection.jsx의 별칭(`= window.fmtScore`)이 안전하게 캡처.
- **판정 함수 유지**: `isDemoSource/livePanelPending`는 내부 의존(livePanelPending→isDemoSource)이 있어 14.2에선 connection.jsx 정의 유지(번들도 동일 제공). 후속 단계에서 통합.

## 검증
- **실화면**: 8771 실 `/ui/` 6탭 전수 클릭 pageerror 0 + `window.fmtMoney(1234567)="+1,234,567원"`·음수 U+2212·`fmtPct(12.345)="12.35%"`·`STATUS_KR.running="실행중"` 정확.
- **회귀 가드**(갱신): `test_p14_build_harness.py` 5/5 — 포매터 본문이 connection.jsx에서 **제거**됐고(de-dup) format.mjs에만 존재 + connection.jsx가 `window.*` 별칭 보유 + 판정함수는 아직 양쪽 유지 + 번들 완전성/신선도. (토큰은 데모코드 생성기 문자열과의 오탐을 피하려 `v.` 접두·`: "—"` 앵커로 고유화.)
- **게이트**: 전체 pytest 신규 실패 0(pre-existing 7만) + `verify_nonrelease_sync.py` exit 0 + 코드리뷰.
- 캐시: `connection.jsx?v=20260612h → 20260614i` bump(계약 테스트는 connection.jsx 버전 미핀, 로드 존재만 단정 → 안전).

## 다음 (14.3)
중간 컴포넌트 — `chart.jsx` 순수 헬퍼(`_axisTicks`) 및 대형 차트 파일(`backtest-charts` 2,814줄·`simulation-charts` 1,842줄)의 빌드 이전/분할. 차트 픽셀 회귀 0.
