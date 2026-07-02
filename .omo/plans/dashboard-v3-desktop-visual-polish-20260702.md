# Dashboard V3 Desktop Visual Polish And Scorecard Update

작성일: 2026-07-02
상태: COMPLETED
워크트리: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
브랜치: `feature/dashboard-remodel-20260626`
기준 계획: `.omo/plans/dashboard-v3-functional-parity-20260701.md`

## Objective

모바일 사용을 범위 밖으로 두고, PC/데스크톱 운영 기준에서 V2/V3 대시보드 시각 검토 결과를 재정리한다. V3에서 실제 데스크톱 blocker로 남은 graph/heatmap overflow를 보정하고, 현재 기능 이식 점수와 UX/UI 성숙도 평가를 데스크톱 전용 기준으로 갱신한다.

## Constraints

- V2 기본 경로는 유지한다.
- V3는 `/ui/remodel/*` 명시 경로만 유지한다.
- 라이브 주문, 브로커 로그인, 계좌/잔고, KHOPENAPI, DB 컷오버, USER_ACK, V3K gate 4~6은 범위 밖이다.
- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/v3k_gui_settings.json`는 건드리지 않는다.
- 기존 미추적 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`는 그대로 둔다.
- 스테이징은 명시 파일만 사용한다.

## Baseline Evidence

- `.omo/evidence/dashboard-v3-visual-comparison-20260702/visual_compare_results.json`
  - 전체 48 checks, overflow failures 16, graphic failures 9.
  - 모바일 findings는 사용자 조건상 out-of-scope.
  - 데스크톱 V3 실제 수정 대상은 Condition page `heatmap` 내부 label/cell overflow.
- `.omo/evidence/dashboard-v3-visual-comparison-20260702/problem_v3-condition-desktop-heatmap.png`
  - 데스크톱 V3 Condition GUI Parity/품질 panel의 heatmap 내부 scrollbar/child overflow 재현.

## TODOs

- [x] TODO 01 - Desktop Visual Baseline Reclassify
- [x] TODO 02 - V3 Desktop Heatmap Overflow Fix
- [x] TODO 03 - Desktop Scorecard And Maturity Update

## TODO 01 - Desktop Visual Baseline Reclassify

Goal:
기존 V2/V3 시각 비교 결과를 PC 전용 기준으로 재분류한다.

Steps:
- 기존 visual compare JSON에서 desktop-1280/desktop-1440만 집계한다.
- 모바일 이슈를 out-of-scope로 명시한다.
- V3 desktop blocker를 Condition heatmap 내부 overflow로 한정한다.

Acceptance Criteria:
- 데스크톱 기준 update list가 evidence에 남는다.
- 모바일 findings는 residual이 아니라 scope exclusion으로 분류된다.

QA:
- Existing visual evidence review.

## TODO 02 - V3 Desktop Heatmap Overflow Fix

Goal:
V3 Condition desktop에서 heatmap 축/셀 박스가 panel 밖으로 계산되는 문제를 좁게 수정한다.

Steps:
- 생산 코드 변경 전 기존 `problem_v3-condition-desktop-heatmap.png`와 JSON offender를 baseline reproduction으로 고정한다.
- `heatmap()` grid column 최소폭과 CSS child 최소폭을 데스크톱 panel 안에서 수축 가능하게 조정한다.
- chart/table의 기존 desktop density는 유지한다.

Acceptance Criteria:
- V3 Condition desktop heatmap 내부 overflow가 사라진다.
- chart/replay/backtest/audit desktop 화면에는 새 page-level overflow가 생기지 않는다.

QA:
- `node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
- Desktop browser check: `/ui/remodel/condition?demo=reference` at 1280x720, 1440x900, 1920x1080.

## TODO 03 - Desktop Scorecard And Maturity Update

Goal:
지금까지의 V2/V3 비교 점수, 기능 성숙도, UX/UI 완성도를 데스크톱 기준으로 문서화한다.

Steps:
- 기존 94/100 scorecard를 desktop-only 전제로 갱신한다.
- V2 대비 V3 성숙도와 잔여 risk를 구분해 기록한다.
- 검증 명령과 evidence path를 남긴다.

Acceptance Criteria:
- desktop-only 점수/성숙도 평가 문서가 존재한다.
- 커밋 전 검토자가 바로 확인할 수 있는 stage/include/exclude guidance가 남는다.

QA:
- `git diff --check`
- `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`

## Final Verification Wave

- [x] F1 - Desktop Visual Evidence Review
- [x] F2 - Scorecard And Protected Path Audit
