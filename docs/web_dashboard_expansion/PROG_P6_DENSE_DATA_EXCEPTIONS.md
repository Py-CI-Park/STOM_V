# P6 선행조건(OQ#2) — 밀집 데이터 폰트 예외목록 (사용자 승인: 기본값)

> 2026-06-15. 프로그램 P6(디자인시스템 랜딩)의 PRECONDITION. 본문(prose)은 ≥14px(한국어 가독)로 올리되,
> 정량 밀집 화면은 정보밀도 보존을 위해 `--fs-dense`(12px) 미만 유지를 허용한다. 사용자가 기본값 승인.

## 원칙
- **prose(설명·본문·카드·배너·도움말·빈상태·모달 본문)** → `--fs-prose`(≥14px).
- **dense(정량 표·수치·게이지·축 라벨·뱃지·태그·로그)** → `--fs-dense`(12px) 또는 현행 밀집 크기 유지(예외).

## 예외(=14px 미만 유지 허용) — 셀렉터/영역
정량 정보밀도가 핵심인 다음은 `--fs-dense`(12px) 또는 현행 유지:

1. **mono 수치 표** — `.data-table`(및 그 안 `td`/`th`), `table.mono`, 백테 WFO/스윕 결과표(BtWfoTable/BtSweepTable), HoF 표(HallOfFamePanel/_RpHallOfFame), 세대표(GenerationsTable), run 비교표.
2. **메트릭/게이지 수치** — `.stom-gauge-*`(라벨/값), `.bt-summary-row`/`_BtMetricCard`, `.engine-*` 셀 수치, `.val.tnum`/`.mono` 수치 셀.
3. **차트 축/라벨** — `.chart-axis-text`, `.chart-grid-line` 라벨, sim/backtest 차트 축 텍스트.
4. **상태 배지·태그·칩** — `.badge*`, `.tag-slim`, `.rp-kind*`, `.research-badge`, `.stom-section-label`(이미 12px·디자인 의도).
5. **로그·코드·시각열** — 체결로그/신호로그 표, `.code-viewer`/`CvCodeBlock` 코드, 모노 시각 컬럼.
6. **밀집 컨트롤 라벨** — 작은 토글/버튼의 mono 캡션(`.btn.sm`/`.btn.tiny`의 수치성 라벨), 엔진/지표 토글 바.

## ≥14px 로 올리는 대상(prose)
- `body` 기본 폰트 13→14px(전역 prose 기준).
- 패널/카드 설명문(`.panel-bd` 산문, `.summary-sub` 설명, 카드 desc), 배너(`ResearchCriteriaBanner`/`ExportStatusBanner`), 도움말 스트립(`MetricHelpStrip`/`.research-help`), 용어/위키 본문(glossary/wiki prose), 빈상태(`.research-empty`/`.empty` 안내문), 모달 본문 산문(`ApprovalDialog`/SettingsModal 설명).

## 검증(M4 — 객관)
- **타이포 grep/CSS-parse**: prose 규칙은 ≥14px OR 위 예외 셀렉터에 해당. (예외목록이 단언 근거.)
- **대비(WCAG)**: contrast-ratio 매트릭스(token×bg, 양 테마) — normal ≥4.5:1, large ≥3:1, 실패 0(커밋 아티팩트).
- **반응형**: 1280/1600/2200px 에서 가로 오버플로(scrollWidth>clientWidth) 0, grid 컬럼 최소폭 하회 0.
- **토큰 커버리지**: 하드코딩 gap/border-radius 의 ≥80% 토큰 치환(전/후 grep 수).
- **MVQA**: 6탭×2테마×3폭 전/후 PNG + 사용자 8770 사후 승인.
