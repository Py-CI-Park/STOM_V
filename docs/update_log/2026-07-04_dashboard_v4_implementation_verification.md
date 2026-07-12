# 2026-07-04 Dashboard V4 Implementation — Verification & V2/V3/V4 Comparison

## 1. 결론

V4 대시보드가 **opt-in 프리뷰로 구현·검증**됐다. 브랜치 `feature/dashboard-v4-20260704`.
V2 기본 경로는 100% 보존되고, V4는 기존 V2 React 컴포넌트를 graph-first 레이아웃으로
재배치한 별도 셸(`DashboardV4Shell`)로 `/ui/v4` opt-in 노출된다. design-sync(claude.ai)는
이 앱이 모놀리식이라 부적합해 접었고, 전 과정이 로컬 코드다.

## 2. 커밋 (Phase 0~7)

| 커밋 | Phase | 내용 |
|---|---|---|
| `2e7d7c80` | 1 | opt-in 셸 스캐폴드 (`dashboard-v4-shell.jsx`, `v4.html`, `v4.css`) |
| `f2751270` | 2 | `/ui/v4` 라우트 + `?dashboard_version=v4` + V2 셸 "V4 Preview" 링크 |
| `71890aad` | 3 | Research Live graph-first (대형 fitness hero + 관찰성 rail) |
| `0faff968` | 4 | Backtest 탭(BacktestTab 재사용) + `?tab=` 딥링크 |
| `d11dd997` | 5 | Replay 탭(SimulationTab) + keep-alive |
| `f89d8a97` | 6 | Lab / Workbench / Audit 탭 |
| (this) | 7 | 하네스 V7 게이트 분리 + 검증 문서 |

## 3. 아키텍처

- **opt-in**: `app.py`가 `?dashboard_version=`로 V2/V3/V4 분기(미지값→V2 폴백). `/ui/v4`·`/ui/v4/`
  전용 라우트(V3 remodel 미러, fail-closed 404). V2 기본 경로 불변.
- **마운트**: `frontend/v4.html`이 `__STOM_NO_AUTO_MOUNT__` 후 `window.DashboardV4Shell` 이름-마운트
  (lab/pro/verdict.html 패턴). **같은 `bundle/app.js`·단일 React 공유**(별도 번들 없음).
- **재사용**: 컴포넌트 신규 생성 없이 기존 V2 컴포넌트를 재배치. graph-first 는 `.v4-root` 스코프
  CSS(대형 chart-wrap)로 달성 — V2 styles.css 회귀 0.
- **탭 상태**: `?tab=<key>` 로 딥링크·새로고침 유지. Replay 는 keep-alive(hidden 상주).

## 4. V4 IA — 탭별 재사용 컴포넌트

| V4 탭 | 재사용(드롭인) | 파일 |
|---|---|---|
| Research Live | FitnessChart·ProfitChart·QualityTrendChart·EquityOverlayChart·EnginePanel·PhaseTimeline·ResearchProPanel / CurrentGenPanel·Best·Winner·PopulationPanel·ApprovalDialog | `v4-research.jsx` |
| Backtest | BacktestTab (통째) | `v4-backtest.jsx` |
| Replay | SimulationTab (keep-alive) | `v4-replay.jsx` |
| Lab | ResearchHeatmapPanel·ResearchLabPanel | `v4-lab.jsx` |
| Workbench | ResearchProPanel·RunComparePanel·HallOfFamePanel | `v4-workbench.jsx` |
| Audit | VerdictPanel + compact 안전 strip | `v4-audit.jsx` |

## 5. 검증 증거

| 게이트 | 방법 | 결과 |
|---|---|---|
| 빌드 | `webui-build && npm run build` | 0에러, `DashboardV4Shell` + 6탭 번들 |
| 라우트 서빙 | FastAPI TestClient | `/ui/v4`→307→`/ui/v4/`(200 `v4-preview`), `?dashboard_version=v4` 서빙, 미지값→V2 폴백, V2 4경로 무변화 |
| 렌더 (jsdom) | `track-z-harness.mjs` V1~V7 | **allPass** — V7(V4 셸+6탭) 전부 0에러 렌더(idle+running), V2 index·V3 8탭 sweep·V4 lab/pro/verdict 회귀 0 |
| pytest 게이트 | `tests/unit/dashboard/test_track_z_pr1_harness.py` | **15 passed** (신규 `test_track_z_v7_v4_dashboard_shell` 포함) |
| 브랜치 게이트 | `scripts/verify_nonrelease_sync.py` | **통과** (모든 [OK]) |
| 번들 동기화 | `test_committed_bundle_in_sync_with_source` | 통과 (재빌드 no-op, byte-stable) |
| 보호 경로 | git status | `backtest/graph`·`_database`·`_log`·`.omx/reports` 무변화 |

## 6. V2 / V3 / V4 비교

| 항목 | V2 | V3 remodel | V4 (구현) |
|---|---|---|---|
| 스택 | React JSX 번들 | no-build static SPA | **V2 React 번들 재사용** |
| 노출 | 기본 `/ui/` | `/ui/remodel/`·`?dashboard_version=v3` | `/ui/v4`·`?dashboard_version=v4` (opt-in) |
| 테마 | 조용한 quant terminal | 장식성 높음 | **V2 테마 재사용** |
| 그래프 | 큰 SVG | 작음(128px 계열) | **graph-first 대형 hero** |
| 컴포넌트 | 기능 정본 | 별도 static 재구현 | **V2 정본 재사용(재구현 없음)** |
| 안전/감사 | 인라인 타일 | 명시적 | compact strip + VerdictPanel |
| 회귀 위험 | — | 별도 계층 | **V2 무변화(additive)** |

## 7. 남은 것 / 수동 UAT

- **라이브 happy-path UAT**: 실제 STOM 백엔드(실데이터)를 띄우고 `/ui/v4`에서 세대 진행·백테
  실행→리포트·리플레이 재생을 눈으로 확인. jsdom 하네스는 "0에러 렌더"만 증명한다.
- **시각 graph-first 튜닝**: jsdom 에 레이아웃 엔진이 없어 차트 **크기/배치는 자동 검증 불가**.
  브라우저에서 hero/rail 비율·차트 높이를 눈으로 확인하고 `.v4-*` CSS 로 미세조정.
- **탭별 심화 graph-first**: Backtest/Replay 는 현재 원 컴포넌트를 통째 재사용(내부 레이아웃
  보존). "차트 전면 배치" 심화는 후속 리팩터(원 컴포넌트 state 분리 필요) 대상.

## 8. 실행 방법

```
# 빌드(소스 수정 시)
cd ai_strategy_loop/dashboard/webui-build && npm run build
# 서버
uvicorn ai_strategy_loop.dashboard.app:app --port 8770
# 열기: http://127.0.0.1:8770/ui/v4  (또는 V2 상단 "V4 Preview")
# V2 그대로: http://127.0.0.1:8770/ui/
```
