# P4-functional — 기능 폴리시(백테 CSV·WFO/스윕 드릴다운·DEMO/LWC 라벨)

> 2026-06-14. ralplan 계획 P4-functional. 대시보드 감사 우선순위 2(중간 위험·저결합 빠른 가치).

## 한 줄 요약
백테 결과에 **일별 수익곡선 CSV 내보내기**(sim 체결로그 CSV 규약 미러: BOM·\r\n·Blob), WFO/스윕 결과표 **행 클릭 드릴다운**(선택 파라미터·전체 메트릭 펼침, 백엔드 무변경 프론트 전용), 엔진 게이지 **DEMO 시뮬값 캡션**, 시뮬 **LWC 비대칭 캡션**(의도된 미표시 명시)을 추가. 픽셀 변경은 추가 라벨/버튼뿐(로직·백엔드·계약 무변경).

## 감사 정정(실측 — 계획 가정 수정)
- **Shift+드래그 힌트 = N/A(제거 안 함).** 계획은 "데드 힌트면 제거"였으나 실측 결과
  `backtest-charts.jsx` `onDown`(shiftKey)→brush→`onBrush(dA,dB)`→**구간 분석**으로 **정상 작동**하는 기능이다.
  힌트는 실제 동작을 설명하므로 제거하면 회귀. → 조건부 기준에 따라 **유지(N/A)**.
- **clickable 행 = 프론트 전용 드릴다운.** 계획의 "`/bt/report?run_id=&gen_no=` 로 연결"은 부정확 —
  그 드릴다운은 **진화 세대 전용**(backtest-charts.jsx:1212, 이미 결선)이고 WFO 라운드/스윕 조합은
  per-row run_id/gen_no·리포트 라우트가 **없다**(백엔드 frozen). 라우트 날조 금지 원칙에 따라
  **행 클릭 = 펼침 상세(best_params·전체 메트릭)** 로 구현(프론트 전용, 무라우트).
- **LWC 비대칭 = 이미 ⓘ 팝오버 존재.** `SimEnginePopover`(simulation.jsx) 가 이미 3엔진 역할 표를 보여줌.
  P4 는 **LWC 선택 시 토글 옆 인라인 캡션**으로 보강(팝오버를 열지 않아도 보이게).

## 변경
- **backtest-charts.jsx**: 최상위 헬퍼 3개 신설 — `_btCsvCell`(RFC4180 이스케이프), `_btAnalysisCsv`
  (컬럼: 날짜·일별손익(원)·누적수익(원), utf-8 BOM 선행), `_btDownloadAnalysisCsv`(Blob+a[download],
  파일명 `백테스트_YYYY-MM-DD.csv`). `sim _simDownloadSignalLogCsv` 규약 동일. BtAnalysis 헤더에
  `⬇ CSV` 버튼(`analysis.equity.daily` 존재 시에만). 자급자족 HTML 리포트(/bt/report)는 그대로.
- **backtest.jsx**: `_BtRowDetail`(WFO·스윕 공용 상세 한 줄) 신설. `BtWfoTable`/`BtSweepTable` 에
  `expanded` 상태 + 행 `onClick` 토글 + 펼침 상세 행(WFO: 선택 파라미터+전체 테스트 메트릭 /
  스윕: 조합+전체 메트릭). 정렬·표 구조 무변경(드릴다운은 가산).
- **engine.jsx**: `isDemo` 면 engine-grid 최상단에 전폭 캡션 "DEMO 시뮬값 — CPU·메모리·워커·처리량
  게이지는 데모 시뮬레이션 값입니다(backend 미발행)". 게이지 클래스·임계값 무변경, 색은 토큰만
  (하드코딩 hex/rgba 금지 — test_p11_engine_gauges 일관). 헤더 DemoBadge 와 별개의 오해 방지 캡션.
- **simulation.jsx**: `SimViewBar` 엔진 토글 옆, `engineMode === "lwc"` 시 캡션
  "LWC 비대칭 — RSI·MACD·호가불균형·net-delta 미표시(라이브·SVG 전용)". 로직 변화 없음(라벨 전용).
- **test_p4_functional.py**(신규): 순수 Python grep(node 비의존, esbuild-skip 클러스터 밖) —
  CSV 헬퍼/헤더/BOM/Blob/버튼게이팅, WFO/스윕 드릴다운, 엔진 DEMO 캡션+무하드코딩색, LWC 캡션 검증.

## 검증
- **빌드**: `npm run build` → app.js v=c1e97aae (26 files), stom-ui.js v=ac59ac0e, 5 HTML ?v= 갱신.
- **신규 계약**: test_p4_functional 12/12 통과.
- **기존 계약 무회귀**: test_p11_engine_gauges·test_sim_phase7_charts(비대칭 가드)·test_p13_bt_sweep_builder·
  test_p13_sim·test_no_duplicate_globals 전부 통과(89 passed 배치).
- **게이트**: 전체 pytest 신규 실패 0(핀 베이스라인과 동일 집합) — (게이트 로그 참조).
- **실화면(8771)**: app.js?v=c1e97aae 서빙, 6탭 각 0 pageerror(총 0), LWC 선택 시 캡션 표시,
  FROZEN 전역(RunComparePanel/EnginePanel/LabPage/ProPage/VerdictPanel) 정상.

## 다음
P2(라이브 백테차트 dedup·결정 동선 크로스링크, 픽셀중립) → P3(통합·공유 tick 헬퍼→format.ts) → Design.
