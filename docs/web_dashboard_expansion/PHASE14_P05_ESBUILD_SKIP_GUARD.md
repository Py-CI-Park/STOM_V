# P0.5 — esbuild 부재 skip 가드 (브랜치 게이트 복구)

> 2026-06-14. ralplan 계획(`webbt-dashboard-frontend-improvement-20260614.md`)의 P0.5. 대시보드 개선 1~4 + 디자인 패스의 선행 단계.
> **목적**: Phase 14.7에서 transform 검증 테스트를 `vendor-babel` → esbuild로 이관하면서, esbuild를 **wt-dev에 없는** `webui-build/node_modules/`(gitignore)에서 require하게 돼 wt-dev 브랜치 게이트가 RED가 된 회귀를 복구.

## 문제 (게이트 RED)
- 11개 `tests/unit/dashboard/test_*::test_*transforms_with_vendor_babel` 테스트가 `require(.../webui-build/node_modules/esbuild)`.
- `node_modules`는 gitignore → **wt-webbt만 `npm install`** 됨, **wt-dev엔 부재**.
- 기존 skip은 `node is None`만 가드 → wt-dev는 node 존재라 미발동 → require 실패 → 11개 FAIL.
- 결과: CLAUDE.md 브랜치 게이트(`pytest tests/unit/`)가 wt-dev에서 RED(실측: 11개 transform 실패).

## 수정 (test-only)
11개 테스트의 `node is None` 체크 직후, esbuild 존재 가드 추가(기존 precedent 미러):
```python
if not (FRONTEND.parent / "webui-build" / "node_modules" / "esbuild").exists():
    pytest.skip("esbuild 미설치(webui-build/node_modules gitignored) — 트랜스폼 검증 생략")
```
- 삭제 안 함, esbuild.transform 재지정 안 함(후속 follow-up). 소스 .jsx·빌드·백엔드 무변.

## 대상 11파일 (broad 토큰 `transforms_with_vendor_babel`)
test_other_tabs_phase7 · test_p11_combo_heatmap · test_p11_engine_gauges · **test_p11_process_flow**(함수명 `test_p11_phase_detail_transforms_with_vendor_babel` — `jsx_` 인픽스 없음, narrow 토큰이 놓치는 11번째) · test_p13_bt_overlay_split · test_p13_combo_drill · test_p13_sim · test_phase8_heatmap_axis · test_phase9_spa_tabs · test_sim_frontend_phase6 · test_sim_phase7_charts

## 검증 (실측)
- **wt-webbt(esbuild 존재)**: 가드 미발동 → 11개 transform 여전히 실행·통과. 전체 게이트 = 베이스라인 7 failed 불변(진짜 pre-existing 백엔드/러너/UI 테스트, vendor-babel 무관).
- **wt-dev(esbuild 부재, 가드 전)**: 11개 transform FAIL 실측 확인(`babel transform failed: node loader:1228`).
- **wt-dev(가드 후, 머지 통합)**: 11개 SKIP → 게이트가 wt-webbt 베이스라인(7 failed)과 일치.

> 주: 계획의 "0 failed" 표현은 부정확 — 진짜 pre-existing 7건(test_backtest_button_contract·protocol_diagnostics×2·spawn_contract_audit×2·runner_helpers·ui_jisu_cleanup)은 vendor-babel과 무관해 양 워크트리 공통. 정확한 기준 = **wt-dev가 7-베이스라인과 일치 + 11 SKIP**.

## 후속
- transform 테스트를 esbuild.transform으로 repoint(또는 폐기)하는 정리 PR — 별도(이 단계는 게이트 그린화만).
- 근본: esbuild bundle-mode 전환(전역 충돌 클래스 제거)은 별도 이니셔티브(ralplan ADR deferral).
