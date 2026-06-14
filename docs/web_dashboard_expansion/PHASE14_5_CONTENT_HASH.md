# Phase 14.5 — 캐시 계약 content-hash 자동화 (수동 ?v= 핀 폐지)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_4_APP_BUNDLE.md`.
> **목표**: 빌드 산출물(`app.js`·`stom-ui.js`)의 `?v=` 캐시 버전을 **content-hash 로 자동 관리**한다. 매 변경 시 사람이 `?v=` 를 손으로 bump 하던 계약(휴먼에러 원천)을 폐지. 화면 동작 변화 0.

## 한 줄 요약
`build-app.mjs` 가 빌드 후 `app.js`/`stom-ui.js` 의 **sha256[:8]** 을 계산해, 번들을 로드하는 모든 HTML(index/lab/pro/legacy)의 `?v=` 를 자동 갱신하고 `bundle/manifest.json` 을 emit. 소스가 바뀌면 해시가 바뀌고 HTML 이 자동으로 캐시 무효화된다.

## 무엇이 바뀌었나
- `build-app.mjs`: app.js 컴파일 후 ① `app.js`/`stom-ui.js` content-hash(sha256[:8]) 계산 ② `bundle/{app.js,stom-ui.js}` 의 `?v=` 를 index/lab/pro/STOM-legacy HTML 에 정규식으로 자동 주입 ③ `bundle/manifest.json`(해시 + appSources ORDER) emit.
- 결과: index.html `app.js?v=3d05169f`·`stom-ui.js?v=504ab1d4`, lab/pro/legacy `stom-ui.js?v=504ab1d4`(legacy 는 누락됐던 ?v= 도 추가).
- **수동 캐시 bump 불필요**: 더 이상 `?v=20260614x` 를 손으로 올리지 않는다.

## 재현성·자기검증
- **결정적**: 해시는 파일 내용만의 함수(타임스탬프 없음) → 같은 소스 = 같은 해시. 재빌드 멱등(2차 빌드 "변경 없음").
- **자기검증 테스트**(`test_content_hash_cache_consistency`): manifest 해시 == 실제 파일 sha256 == HTML `?v=` 를 전수 대조. **소스 수정 후 재빌드를 깜빡하면(stale 번들/stale ?v=) 즉시 실패** → 수동 핀 폐지의 안전망. `validation_views` 의 하드코딩 버전 단정 제거(값 고정 안 함).

## 검증
- **실화면**: 8771 `/ui/` 번들이 content-hash `?v=` 로 로드(app.js?v=3d05169f·stom-ui.js?v=504ab1d4), 6탭 0 pageerror.
- **게이트**: 전체 pytest 신규 실패 0(pre-existing 7) + `verify_nonrelease_sync.py` exit 0 + 코드리뷰.

## 보류 / 다음
- **app.js 미니파이**: 로컬 서빙(8770/8771) 환경이라 ~950KB 도 무리 없음 + 마커/동작 보존 위해 보류. 필요 시 별도.
- **14.6**(선택): TS 점진. **14.7**: lab/pro/legacy 컴포넌트 빌드 전환 + `vendor-babel.js` 파일 완전 제거.
