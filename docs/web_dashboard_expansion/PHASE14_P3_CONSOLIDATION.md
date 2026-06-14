# P3 — 통합 + 공유 모듈(tick/format 헬퍼 → format.ts/stom-ui.js)

> 2026-06-14. ralplan 계획 P3. 대시보드 감사 우선순위 4(중상 위험·최고 전역 스코프 리스크).

## 한 줄 요약
중복 tick/format 헬퍼를 빌드 번들(`format.ts`→`stom-ui.js`) **단일 출처**로 이전(소비 .jsx 는 `window.*` 별칭만). **렌더 출력 픽셀 중립**(유한·비널 실데이터에서 기존과 byte-동일) — 단, null/비유한 엣지 입력은 슈퍼셋 가드로 **더 안전**해진다(예: `_simTimeLabel(null)` 의 비렌더 CSV 폴백 `_simCsvTime` 가 `"00:nu:ll"`→`"00:00:00"`, `_simPriceTick(NaN)` 이 `"NaN"`→`"—"`; 모두 회귀 아닌 개선). 컴포넌트 통합(HoF·process-flow·freeze_verdict)은 **field-diff 게이트**가 "픽셀/콘텐츠 변경 유발"로 판정해 Design Pass(픽셀 재베이스라인 허용)로 이연.

## 방법: field-diff 게이트 먼저(계획 필수 절차)
"버리는 사본이 고유 기능을 더하지 않음을 증명하는 field-diff 후 통합" 원칙대로, 4개 대상을 전수 비교했다. 결과가 통합 가부를 결정:

| 대상 | field-diff 판정 | 처리 |
|------|----------------|------|
| **tick/format 헬퍼** | `_btAxisTicks`=번들 `_axisTicks` 로직 동일 · `_simPriceTick`/`_slcPriceTick`, `_simTimeLabel`/`_slcTimeLabel`=near-동일(slc 가드 슈퍼셋) | **통합(이 PR)** — 픽셀 중립(유한/비널 실데이터 동일) |
| **Hall of Fame** | `HallOfFamePanel`(정렬/필터/스크린샷갤러리/인간벤치)·`_RpHallOfFame`(펼침코드/바로백테/score) — 컬럼·CSS·기능이 본질적으로 다름(각 사본 고유 기능 존재) | **이연** — 병합 시 렌더 변경, "고유 없음" 불충족 |
| **process-flow PIPELINE** | `_RL_PIPELINE` vs `RP_PIPELINE`: 7단계 **교육 문구가 전부 다름**(RL 간결/RP 상술), RP 만 `key` 필드 | **이연** — 계획의 "if equal → hoist" 조건 불충족(단일화=콘텐츠 변경) |
| **freeze_verdict 요약** | `_ValidationPanel`(walkforward 표 고유) vs `VerdictPanel`(OOS-CI 표 고유): fontSize 11/12·alert색 `var(--amber)`/`#c95` 차이 | **이연** — 단일 스타일 강제 시 픽셀 변경 |
| **`_btMoneyTick` 계열** | `_btMoneyTick`/`fmtMoneyShort`/`_gpMoney`: 만단위 반올림(`toFixed(0)` vs `Math.round`)·로케일 인자 차이 | **제외** — 리터럴 중복 아님(반올림 정책 결정 필요) |
| **ProcessFlowPanel(phase-detail)** | 라이브 진행 패널(FLOW_STEPS·타이머·진행바) — 교육 오버레이와 무관 | **유지**(통합 대상 아님) |

> 이연은 **범위 축소가 아니라 field-diff 게이트가 픽셀 중립 제약 하에서 안전한 통합만 통과시킨 결과**다. 이연 대상의 시각/콘텐츠 통일은 픽셀 재베이스라인이 허용되는 Design Pass 가 적임(진화 사이드바 정리도 같은 이유로 그쪽에 통합됨).

## 변경(통합 통과분)
- **webui-build/src/format.ts**: `_priceTick`(원·천단위, null/비유한→"—"), `_hmsTimeLabel`(HHMMSS→"HH:MM:SS", null→0) 신설 + `window` 노출. 슈퍼셋 = sim-live-chart 판본(가드 포함).
- **backtest-charts.jsx**: `function _btAxisTicks` 삭제 → `const _btAxisTicks = window._axisTicks`(chart.jsx 패턴). 5개 호출부 무변경.
- **simulation-charts.jsx**: `_simPriceTick`/`_simTimeLabel` 정의 삭제 → `window._priceTick`/`_hmsTimeLabel` 별칭.
- **sim-live-chart.jsx**: `_slcPriceTick`/`_slcTimeLabel` 정의 삭제 → 동일 별칭(과거 "결합 회피" 주석 폐기, `_axisTicks` 와 동일 단일출처 정책에 정렬).
- **test_p14_build_harness.py**: `test_all_entrypoints_loading_deduped_jsx_also_load_bundle` 의 deduped 목록에 backtest-charts/simulation-charts/sim-live-chart 추가(번들 의존 명시).
- **test_p3_consolidation.py**(신규): 순수 Python grep — 번들 신헬퍼 노출, 소비처 별칭화(bare function 정의 잔존 0), 이연 대상 불변(HoF·PIPELINE 분리 유지) 회귀 가드.

## FROZEN/가드 준수
- `test_p14` 26마커·content-hash 계약 불변(ORDER 파일 추가 없음 — 헬퍼는 기존 stom-ui.js 번들 확장).
- stom-ui.js content-hash 변경 → 5 HTML `?v=` 자동 갱신(test_p14 content-hash 단언 green).
- 번들 충돌 가드: 별칭 const 이름(`_btAxisTicks`/`_simPriceTick`/…)은 각 파일 고유(test_no_duplicate_globals green).
- 픽셀 중립: 별칭은 유한/비널 실데이터에서 기존과 동일 출력(런타임 검증으로 확인).

## 검증
- **빌드**: `npm run build` → app.js v=05695bcc, **stom-ui.js v=a142dbb8**(format.ts 변경), 5 HTML ?v= 갱신.
- **계약**: test_p3_consolidation + test_p14 + test_p13_sim + test_sim_phase7_charts + test_no_duplicate_globals = 51 passed.
- **게이트**: 전체 pytest 신규 실패 0(핀 베이스라인 동일) — (게이트 로그 참조).
- **런타임(8771)**: 두 번들 새 해시 서빙, 6탭 각 0 pageerror(총 0), `window._priceTick(1234567)`="1,234,567"·`(Infinity)`="—"·`_hmsTimeLabel(93015)`="09:30:15"·`(null)`="00:00:00"·`_axisTicks(0,100,5).length`=5(별칭 정상 해소).

## 다음
Design Pass(터미널·픽셀 변경 허용) — 진화 사이드바 연구패널 정리 + 그룹화 + 시각 위계 + WCAG, 그리고 P3 가 이연한 시각/콘텐츠 통일(HoF·PIPELINE 문구·verdict 스타일)을 단일 인간승인 재베이스라인에서 처리.
