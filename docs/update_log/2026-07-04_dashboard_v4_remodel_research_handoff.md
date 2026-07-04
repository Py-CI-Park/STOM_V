# 2026-07-04 Dashboard V4 Remodel Research Handoff

## 1. 결론

V4 대시보드는 가능하며, 권장 방향은 **V2 React 운영 스택과 조용한 quant terminal 테마를 기반으로 V3의 workflow/safety/audit 노하우를 선별 이식하는 것**이다.

현재 V3 remodel은 구조 설계, 안전 게이트, 프로세스 추적성 면에서는 의미가 있지만, 사용자가 실제로 장시간 보는 대시보드 기준에서는 V2보다 약한 지점이 분명하다. 특히 V3는 정보와 설명이 많고, 첫 화면에서 그래프가 주인공이 되지 못하며, 정적 SPA 단일 파일 구조라 장기 운영 구현체로 보기 어렵다.

따라서 다음 리모델링은 "V3를 계속 크게 만드는 작업"보다 **V2 기반 V4**가 더 안전하다.

## 2. 현재 기준점

| 항목 | 값 |
|---|---|
| V3 작업 워크트리 | `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel` |
| V3 브랜치 | `feature/dashboard-remodel-20260626` |
| V3 HEAD | `db0a60f70e56595dcbe9f614286893a41602a105` |
| 최신 V2 참조 워크트리 | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 최신 V2 참조 브랜치 | `loop/process-research-pipeline` |
| 최신 V2 참조 HEAD | `611473b5acc9f7074ce8997abfe35edbe21cd91d` |
| 현재 실행 확인 URL | `http://127.0.0.1:8770/ui/evolution` |
| V3 명시 URL | `http://127.0.0.1:8770/ui/remodel/condition?demo=reference` |

주의: `wt-dev`는 dirty state가 크고 여러 연구 산출물이 미추적 상태다. 이번 작업은 `wt-dev`를 읽기 전용 참조로만 사용했고, 커밋은 V3 handoff 브랜치에 남긴다.

## 3. 이전 V3 평가의 한계

2026-07-02 scorecard는 V3를 데스크톱 기준 95/100으로 평가했다. 그 평가는 다음 기준에는 타당했다.

| 기준 | V3 강점 |
|---|---|
| 기능 표면 보존 | condition/backtest/replay/audit route와 필수 텍스트가 존재 |
| 안전 게이트 | reference/demo mode, no live order, manual gate, append-only audit 표현 |
| 프로세스 체계 | workflow rail, shared context, handoff, state vocabulary |
| 자동 검증 | V2/V3 route identity, static checks, browser CDP checks |

하지만 그 평가는 다음 사용성 기준에는 과하게 낙관적이었다.

| 사용 기준 | 재판단 |
|---|---|
| 조용하고 깔끔한 운용 화면 | V2가 우세 |
| 큰 그래프와 강한 시각화 | V2가 우세 |
| 백테스트와 리플레이 실사용성 | V2가 우세 |
| 장기 유지보수 가능한 frontend stack | V2가 우세 |
| 최신 `wt-dev` 연구 기능 반영 | V3는 미흡 |

## 4. V2/V3 객관 비교

| 항목 | V2 | V3 remodel | 판단 |
|---|---|---|---|
| 구현 스택 | React JSX + Vite/esbuild bundle + 71개 JSX 파일 | no-build static SPA + `src/app.js` 3132 lines + `src/data.js` 3867 lines | V2 우세 |
| 테마 | 조용한 dark quant terminal, 낮은 장식성, 긴 사용에 유리 | badge/card/notice가 많고 색 강조가 잦음 | V2 우세 |
| 정보 밀도 | 많지만 운영 화면 방식으로 접힘 | 안전/설명/프로세스 정보가 첫 화면에 많이 노출 | V2 우세 |
| 그래프 크기 | 주요 SVG chart viewBox 대체로 `880x300~320`, replay chart는 `340px` 계열 | 기본 chart `128px`, tall `210~260px`, replay candle `320px` | V2 우세 |
| 프로세스 구조 | 사용자가 탭 의미를 알고 있어야 함 | workflow, shared context, route owner가 명시됨 | V3 우세 |
| 안전 표현 | 실제 운영 기능 정본이지만 일부 의미는 암묵적 | no live order, broker/account 금지, human gate 명시 | V3 우세 |
| Backtest | 실제 기능 정본에 가까움 | 기능 표면과 안전 matrix는 있으나 reference/demo 중심 | V2 우세 |
| Chart Replay | 실제 SimulationTab이 정본 | 프로토콜 설명은 좋으나 차트 중심성이 약함 | V2 우세 |
| Lab/Workbench | 최신 `wt-dev`에서 계속 개선 중 | 최신 V2 변경 일부 미반영 | V2 우세 |
| 제품화 방향 | 운영 기준선으로 적합 | IA/reference prototype으로 유용 | V2 기반 V4 권장 |

## 5. 최신 wt-dev 반영도

`feature/dashboard-remodel-20260626` 기준으로 `wt-dev`의 최신 dashboard 관련 변경은 아직 V3에 완전히 반영되지 않았다.

| wt-dev commit | 내용 | V3 반영 판단 |
|---|---|---|
| `47798adc` 프로세스 연구 벤치마크 우선 실행 | process selector UX, research allowed/review only 구분, Lab/Workbench heatmap 크기 제어, browser evidence | 미반영 또는 부분 반영 필요 |
| `332106f2` 조건식 연구 컨텍스트팩과 다중 후보 루프 개선 | Research Pack / Branch Tree, Candidate Pack, Analysis Cards, Prompt Receipts, Promotion Blockers UI | 미반영 |
| `a79b2b27` 조건식 연구 측정 재현성 기반 구축 | replay profile, slippage profiles, measurement frame label, backtest report 표기 | UI 직접 반영 미흡 |
| `611473b5` 현재 wt-dev HEAD | 연구 파이프라인 누적 변경 | V3 기준선보다 앞섬 |

브랜치 diff 기준으로도 `wt-dev`에는 V3 `frontend/remodel/` 산출물이 없고, V3 브랜치는 별도 static remodel 계층을 추가한 상태다. 즉 두 흐름은 서로 보완적이지만 아직 합쳐진 제품 라인이 아니다.

## 6. V4 방향성

### 권장 방향

**V4 = V2 React stack + V2 theme + V3 workflow/safety concepts + 최신 wt-dev research observability.**

| V4에 가져갈 것 | 출처 | 이유 |
|---|---|---|
| React JSX 컴포넌트 구조 | V2 | 유지보수, 기능 연결, 빌드 체계가 더 안정적 |
| 조용한 quant terminal 테마 | V2 | 장시간 PC 운용에 적합 |
| 큰 chart canvas | V2 | 사용자가 원하는 강력한 시각화의 핵심 |
| BacktestTab/SimulationTab 기능 정본 | V2 | 실제 사용성/운영 경로가 더 살아 있음 |
| workflow rail 개념 | V3 | 연구 흐름의 위치와 다음 행동을 명확히 함 |
| safety/audit vocabulary | V3 | 실거래 오해 방지, 승인/감사 분리 |
| Research Pack / Branch Tree | 최신 wt-dev | 실시간 연구 관찰성을 강화 |
| measurement frame / replay/slippage labels | 최신 wt-dev | 결과 해석의 정확도와 재현성 강화 |

### 피해야 할 방향

| 피할 것 | 이유 |
|---|---|
| V3 static `app.js`를 계속 키우기 | 이미 3132 lines, 역할 분리가 약함 |
| 모든 V3 safety/notice를 첫 화면에 노출 | 정보 과다로 도구감이 떨어짐 |
| 그래프를 카드 안 보조요소로 유지 | 사용자가 원하는 핵심은 강력한 시각화 |
| V4를 기본 `/ui/evolution`에 바로 덮어쓰기 | V2 운영 경로 보존 필요 |
| 최신 `wt-dev` 반영 없이 V4 설계 시작 | 최신 연구 파이프라인과 UI 관찰성 누락 |

## 7. V4 IA 초안

| V4 탭 | 첫 화면 원칙 | 주요 기능 |
|---|---|---|
| Research Live | 대형 fitness/equity chart + 현재 generation + BEST 후보 | live run, research observability, branch tree, prompt receipts, blockers |
| Backtest | 큰 equity/underwater/rolling charts를 전면 배치 | strategy select/edit, preflight, run gate, job progress, report |
| Replay | 캔들 차트를 화면 중심에 배치 | source/date/symbol/strategy, playback, timeline, signal log, indicators |
| Lab | 대형 heatmap + factor/correlation drilldown | Edge Ratio, variable importance, regime/time/cap split |
| Workbench | 후보 비교 chart 중심 | HOF, candidate compare, history compare, result review |
| Audit | 결정 funnel은 간결하게, ledger는 접기/열기 | OOS evidence, human decision, append-only ledger |

## 8. V4 시각/UX 원칙

| 원칙 | 구체 기준 |
|---|---|
| Graph-first | 첫 viewport에서 대형 chart가 최소 35~45% 면적을 차지해야 함 |
| Quiet by default | 안전/증거 설명은 상단 작은 strip 또는 drawer로 접음 |
| Research observable | 실시간 세대, 후보 pack, context health, blocker가 한눈에 보여야 함 |
| Strong backtest | 결과 차트, 지표, 거래 로그, report가 도구처럼 연결되어야 함 |
| Strong replay | candle chart, timeline, signal log가 한 화면 workflow로 보여야 함 |
| Human gate explicit | 실행성 action은 명확히 manual-gated, reference/demo에서는 inert |
| Dense but ordered | 카드 수를 줄이고, primary canvas + secondary drawer 구조를 사용 |
| V2 route preserved | `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`는 기본 보존. V4는 opt-in route로 시작 |

## 9. Claude Design 가능성

사용자가 말한 "Claude design"을 다음 의미로 해석하면 V4에 적용 가능하다.

| 해석 | 적용 가능성 |
|---|---|
| Claude가 만든 외형 mockup을 그대로 붙이기 | 단독으로는 위험. STOM 기능/안전/운영 제약을 놓칠 수 있음 |
| Claude식 넓은 시각 설계 감각을 참고해 V2 기반 UI를 리디자인 | 가능하고 권장 |
| V2 기능 정본을 유지하면서 Claude design으로 visual hierarchy를 재설계 | 가장 좋은 방향 |

권장 방식은 **Claude design = visual hierarchy/reference**, **V2 React = implementation base**, **V3 = process/safety concept library**로 역할을 나누는 것이다.

## 10. 권장 구현 순서

| 순서 | 작업 | 산출물 |
|---:|---|---|
| 1 | `wt-dev` 최신 dashboard/research 변경을 기준선으로 삼을지, V3 브랜치로 cherry-pick할지 결정 | branch strategy 문서 |
| 2 | V4 opt-in route 설계: `/ui/v4` 또는 `?dashboard_version=v4` | route contract |
| 3 | V2 React shell/theme를 복제하지 말고 확장 가능한 `DashboardV4Shell`로 분리 | React component skeleton |
| 4 | Research Live first screen 구현 | 대형 chart + current gen + BEST + observability |
| 5 | Backtest/Replay graph-first 재구성 | equity/candle primary canvas |
| 6 | Lab/Workbench 최신 wt-dev 관찰성 이식 | Research Pack, Branch Tree, Edge heatmap |
| 7 | Audit/safety는 compact strip + drawer로 축소 | safety drawer |
| 8 | V2/V3/V4 visual comparison gate 작성 | automated scorecard |
| 9 | 실제 live backend happy path UAT | manual QA report |

## 11. 다음 에이전트 핸드오프

다음 작업자는 아래 순서로 시작한다.

1. `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`에서 이 문서와 `.omo/evidence/dashboard-v4-remodel-research-handoff-20260704/branch-divergence-evidence.md`를 읽는다.
2. `C:/System_Trading/STOM/STOM_V.wt-dev`의 `loop/process-research-pipeline` HEAD `611473b5`를 최신 V2 기능 기준으로 본다.
3. V4 구현 전에는 `wt-dev` 최신 commit `47798adc`, `332106f2`, `a79b2b27`을 어떤 branch에 흡수할지 먼저 정한다.
4. V4는 V3 `frontend/remodel/src/app.js`를 확장하지 말고, V2 React component stack 안에서 만든다.
5. 첫 pass는 화면을 더 화려하게 만드는 것이 아니라, `Research Live`, `Backtest`, `Replay`의 **대형 시각화와 직관적 조작감**을 회복하는 데 둔다.

## 12. 현재 판단 점수

| 항목 | V2 | V3 현 상태 | V4 목표 |
|---|---:|---:|---:|
| 조용함/깔끔함 | 93 | 78 | 94 |
| 기술스택 성숙도 | 92 | 62 | 92 |
| 그래프 크기/시각화 힘 | 90 | 76 | 95 |
| 실시간 연구 관찰성 | 84 | 86 | 94 |
| Backtest 사용성 | 90 | 78 | 94 |
| Replay 사용성 | 88 | 78 | 94 |
| 프로세스 체계 | 76 | 92 | 92 |
| 안전/감사 체계 | 84 | 95 | 96 |
| 최신 wt-dev 반영 | 100 | 65 | 100 |
| 종합 | 87 | 81 | 94 |

## 13. Commit Scope

이번 commit은 문서/계획/증거/핸드오프만 포함한다. UI production code는 변경하지 않는다.

포함 대상:

- `.omo/plans/dashboard-v4-remodel-research-handoff-20260704.md`
- `.omo/evidence/dashboard-v4-remodel-research-handoff-20260704/branch-divergence-evidence.md`
- `docs/update_log/2026-07-04_dashboard_v4_remodel_research_handoff.md`
- `.omo/start-work/ledger.jsonl`
- `.omo/boulder.json`

제외 대상:

- `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`
- runtime/protected paths
- `wt-dev` dirty files
