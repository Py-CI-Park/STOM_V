# F3 — Backtest 데이터 분류(divid_mode) GUI 패리티 결손 보강

- 작성: 2026-07-18 · 브랜치: `f3-backtest-dividmode`

## 대조 결과 (§10-2 gap-only)

웹 백테스트는 P6 인벤토리대로 이미 광범위(모드 single/optimize/wfo/sweep=GUI 패리티 진입점,
equity/분포/지표·portfolio·A/B·Monte Carlo). 자본/벳팅/수수료는 전략 config 소속(per-run 아님) → 결손 아님.

**확정 결손 1건**: python GUI 백테스트는 데이터 분류 3옵션(`cli/subcommands.DIVID_MODE_CHOICES` =
`종목코드별 분류`·`일자별 분류`·`한종목 로딩`)을 제공하는데, 웹 폼은 이를 노출하지 않고 기본값만 사용.
백엔드 `/bt/run` 은 이미 `divid_mode`·`one_code` 를 파싱(backtest_api allowed/model/spec) → **프론트 결손만**.

## 보강 (frontend-only, 백엔드 무변경)

- `bt-tab-run.jsx`: 단일 backtest 모드에 '데이터 분류' 셀렉터(3옵션) + '한종목 로딩' 시 종목코드 입력.
  payload 에 `divid_mode`(+ 한종목 시 `one_code`, 검증) 포함. optimize/wfo/sweep 은 CLI 가 --divid-mode
  미수용이라 단일 모드 한정(backtest_jobs 주석 정합).

## 검증

- **정본 일치 테스트**: 프론트 3옵션 == `DIVID_MODE_CHOICES`(드리프트 방지), payload·one_code 요구,
  백엔드 수용 고정. 31 통과. 번들 v=0e677476.
- 실브라우저: Backtest 폼 '데이터 분류' 3옵션 렌더, '한종목 로딩' → 종목코드 입력 등장. artifacts/f3_backtest_dividmode.png.
