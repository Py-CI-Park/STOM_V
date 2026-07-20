# STOM 대시보드 종합 핸드오프 (V4→V5 완료·V6 재설계 착수 전)

- 작성: 2026-07-19
- 목적: 어느 세션/에이전트에서든 대시보드 작업을 **끊김 없이 이어가도록** 목적·이력·성숙도·전체 구조·미흡점·재개 방법을 한 문서에 기술.
- 정본 위치: 워크트리 `C:/System_Trading/STOM/STOM_V.wt-v5`, 브랜치 `feature/dashboard-v5-overhaul`, HEAD `2fdc25b0`(2268b709 라인).

---

## 0. 사장님 목적 (원문 보존 · 최상위 기준)

> 실제 대시보드를 통해 연구를 개선·확인하고, **실시간 연구·데이터를 시각화**하여 **더 좋은 브레인스토밍으로
> 수익 나는 조건식을 찾기 위함.** 울트라와이드(3440×1440)에서 한 화면에 많은 정보를 밀도 있게 보고,
> 프로세스가 단계별로 사용자와 함께 진행되며, 연구 히스토리·리포트가 체계적으로 관리되는 대시보드.

- **메타 목표**: AI 자율 루프가 **수익 나는 트레이딩 조건식**을 생성. 대시보드는 그 연구를 관찰·개선·브레인스토밍하는 도구.
- **불변 원칙**: `performance_proved=false` — 통제된 A/B 증거 없이 성능(수익) 주장 금지. 대시보드는 "파이프라인 안전·가시성"이지 "검증된 알파"가 아니다.

---

> **[2026-07-20 갱신]** 본 문서 작성 이후 v5.2.x(스테이지 재설계 S1~S8)·v5.3.0~v5.3.10(버전 체계·Live 벨트 4스테이지·run 종합 보고서·검수 3라운드·보안 이식)이 완료되어 §1·§8 이 아래 표로 대체됩니다. 점수 39→**90/100**(재측정: `2026-07-19_dashboard_score_audit_and_95_plan.md` §7).

## 1-갱신. 현재 작업 위치 (2026-07-20 기준 — 이 표가 정본)

| 항목 | 값 |
|---|---|
| **최종(운영) 대시보드** | `http://127.0.0.1:8770/ui/evolution` — **wt-dev**, 브랜치 `loop/process-research-pipeline`(0e86e630, v5 정본 전체 포함) |
| 개발 대시보드 | `http://127.0.0.1:8771/ui/evolution` — wt-v5, 브랜치 `feature/dashboard-v5-overhaul`(정본 개발 라인) |
| 버전 태그 | `v5.0.7`·`v5.1.4`·`v5.2.7`·`v5.3.0`~`v5.3.10` + `archive/v5-parallel-20260718`(병렬 41+1커밋 연구 보존) — **전부 origin push 완료** |
| CSS 핀 | 현재 `v4.css?v=20260719v71` (편집 시 증가) |
| 대시보드 버전 표기 | 셸 `V4_DASH_VERSION`(현 v5.3.9) — 릴리스마다 수동 갱신, 탭 타이틀·브랜드에 노출 |
| 구버전 탭 감지 | 셸이 60초마다 manifest 폴링 → 불일치 시 "새 버전 배포됨" 배너(v5.3.8) |
| 남은 게이트 | ① 운영 run 1회(+5→95 확정: running 실측·BT 인자EP·Replay 재생·HoF AI 갱신) ② mainline(`STOM_Version_2U_C-ai-strategy-loop`) 반영 PR — 둘 다 사장님 승인 대기 |

## 1. 작업 위치·재개 방법 (이 절만 봐도 재개 가능)

| 항목 | 값 |
|---|---|
| 정본 워크트리 | `C:/System_Trading/STOM/STOM_V.wt-v5` |
| 정본 브랜치 | `feature/dashboard-v5-overhaul` (baseline `2268b709`) |
| 현재 HEAD | `2fdc25b0` (V6 마스터플랜 merge까지) |
| 서버(dev) | `http://127.0.0.1:8771/ui/evolution` (bg, wt-v5 프론트 서빙) |
| 서버 기동 | `cd wt-v5; python -m ai_strategy_loop --host 127.0.0.1 --port 8771` (또는 `stom_dashboard.bat`, 기본 8770) |
| 번들 빌드 | `cd ai_strategy_loop/dashboard/webui-build; node build-app.mjs` (JSX 변경 시 필수, 산출 커밋) |
| CSS 핀 | `v4.css`는 `v4.html`에 수동 `?v=` 핀(현재 `20260719v58`). v4.css 편집 시 핀 갱신. `styles.css` 핀은 테스트 하드검증이라 건드리지 말 것 → V5/V6 CSS는 `v4.css`에만. |
| 릴리스 규약 | 각 항목 **독립 브랜치 → 검증 → `--no-ff` 라인연결 merge**. squash/cherry-pick 금지. 명시적 `git add`(no `git add -A`). 한국어 커밋. |
| 세션 상태 | `.gjc/`, `.omo/` 는 커밋 금지. `artifacts/`는 추적됨(증거 PNG 커밋 OK). |
| 병렬 라인 | `wt-dev`(`feature/dashboard-v5-overhaul-20260718`, 8770)는 **다른 에이전트가 동일 계획 병행** — 건드리지 말 것. |

### 포커스 테스트(전체 스위트는 타임아웃 → targeted)
```
python -m pytest tests/unit/dashboard/test_shell_wiring_parity.py \
  tests/unit/dashboard/test_v4_ui_foundation.py \
  tests/unit/dashboard/test_reports_security.py \
  tests/unit/dashboard/test_research_catalog_api.py \
  tests/unit/dashboard/test_report_writer.py \
  tests/unit/dashboard/test_research_records_frontend.py \
  tests/unit/test_dashboard_phase_mapping.py -q -p no:cacheprovider
```
(현재 53 passed 기준선.)

### 환경 함정(반복 재현됨)
- esbuild가 한글을 `\uXXXX`로 escape → 번들 문자열 테스트는 ASCII 마커 사용.
- `bash cat >>` heredoc이 이 환경에서 "Bad file descriptor" → CSS 추가는 `edit` 툴 사용.
- Windows junction/worktree 제거는 cygwin 경로 변환 실패 가능 → `git worktree remove`/PowerShell 사용.
- 대형 응답 fetch(예: /research_docs 930건)는 프론트 로딩에 수 초 → 검증 시 충분히 대기.

---

## 2. 개발 이력·성숙도

### 2.1 계보
`V4(그래프-우선 셸 인프라)` → `2268b709(V5 실행계약·수치기준 보강, 사장님 확정 baseline)` → **V5.0~V5.7 + 부분보강(완료·merge)** → **V6 마스터플랜(작성·merge, 구현 전)**.

### 2.2 V5 라인 성과 (전부 merge됨, 성숙도 표기)
| 릴리스 | 내용 | 성숙도 |
|---|---|---|
| V5.0 | Live 밀도(세로스택→2열 grid, 스크롤 12.6→1.74화면, hero≤320) | 🟡 부분(3440에서 hero 여전히 1382px 단일그래프) |
| V5.1 | 프로세스 단계 pin(PhaseTimeline, 라이브 자동follow) | 🟡 pin만, 탭 아키텍처 아님 |
| V5.2 | Live 백테 단계 조건식·출처 밴드 | 🟢 |
| V5.3 | Backtest 결과 조건식·기간 밴드(gap-only) | 🟢 |
| V5.4 | History 상세 세대 가드(늦은응답 차단) | 🟢 |
| V5.5 | Alpha 격하 + Lab dual-mount(Live fold·History 섹션)·Context 서랍 | 🟡 fold 통합(스테이지 통합 아님) |
| V5.6 | Reports HTML/Wiki 뷰어(930문서) + 오프라인 리포트 writer·manifest·CSP | 🟡 뷰어·수동생성(동적 시스템 아님) |
| V5.7 | P4 계약(env DB·무집계·provenance)·5뷰 골격·clauses/cells 엔드포인트·G3 효과버튼 | 🟢 계약·G3 / 🟡 5뷰는 데이터 없음 골격 |
| 부분 | Live 엔진·게이트 상단 상황판(_V4EngineGateBar) | 🟡 |

**성숙도 총평**: 인프라·계약·안전·부분 시각화는 **성숙**. 그러나 사장님 최우선인 **Live 스테이지 재배치·울트라와이드 밀도·Lab 프로세스 통합·데이터 가시성**은 **미성숙(BLOCK)**. → V6에서 재설계.

### 2.3 워크트리 정리(2026-07-19 완료)
- 삭제: team-worker 1~4(세션 스크래치) + wt-webbt(병합완료). 워크트리 16→11.
- 잔존 정리 후보(병합완료·미사용, dirty만 남음): wt-dashboard-next(1)·wt-condition-tree(3)·wt-dashboard-remodel(29)·wt-evo-governance(30) — 삭제 시 `--force`.

---

## 3. 현재 대시보드 전체 구조 (섹션별 이해)

### 3.1 라우팅·셸
- 진입: `/ui`(정본 V4 그래프-우선 셸), `/ui/evolution`(=Live), `/ui/v4`(직접 v4.html), legacy는 `?dashboard_version=legacy` 1회.
- 셸: `dashboard-v4-shell.jsx` → `DashboardV4Shell`. 좌측 레일(`v4-rail`) + 워크스페이스(`v4-topbar` + `v4-controlbar` + main).
- 딥링크 매핑: `V4_PATH_TAB_MAP`(records/verdict/audit→history 등) + `V4_LEGACY_TAB_ALIAS`(audit·verdict→history, V5.P0 봉인).
- 세션 부트스트랩: `security.py` `BOOTSTRAP_PATHS`/`_is_bootstrap_path`(WS 4401 세션 루프 수정, V5.P2).

### 3.2 탭 구성(현재)
| 그룹 | 탭(key) | 컴포넌트 | 렌더 내용 | 현재 상태/미흡 |
|---|---|---|---|---|
| primary | Live(research) | `V4ResearchLive`(v4-research.jsx) | heading→WorkflowStrip→EngineGateBar→(hero-col: HeroChart+Stats+2그래프+Equity+Engine+7 fold)+(side-col 480px: CurrentGen·LoopCycle·Best/Winner·ConditionDiscovery·Population) | **세로 스택·거대 그래프·스테이지 탭 없음(최우선 재설계)** |
| primary | Backtest | `V4Backtest`(v4-backtest.jsx) | /bt/run·job·결과·MC·A/B·portfolio·divid_mode | 독립 유지. 강력 시각화는 UX 후(사장님 3·4) |
| primary | Replay | `V4Replay`(v4-replay.jsx) | 캔들 리플레이 | 순서상 Reports 뒤로 이동 예정(R1) |
| primary | History | `V4History`(v4-history.jsx) | 여정·아카이브(ResearchRecordsPanel)·계보(트리·A/B·CellHeatmap·HoldoutFunnel)·엣지(ResearchLabPanel, V5.5)·색인(ResearchIndexPage)·거버넌스(AuditDecisionTrace·VerdictPanel) | 리스트→상세 데이터 아키텍처 미완(L9) |
| primary | 성과(workbench) | `V4Workbench`(v4-workbench.jsx) | ResearchProPanel+RunComparePanel+HallOfFamePanel+HofInventoryGate | Lab과 중복(히트맵/시총/시간대), 명예의전당 전용 축소 필요(W2·W3), HoF 데이터 안보임(R5) |
| primary | Reports | `V4Reports`(v4-reports.jsx) | /reports 목록·/reports/view(sandbox+CSP) HTML / Wiki(/research_docs 930·원문) 모드 토글 | 동적 시스템 단계·결과예시 탭 미완(G5·R4) |
| secondary | Alpha | `V4Alpha`(v4-alpha.jsx) | 알파 랩 사전등록·원장·퍼널 | 연구기록 체계화 미흡(R3), 추후 통합(W5) |
| secondary | Lab | `V4Lab`(v4-lab.jsx) | ResearchHeatmapPanel(팩터·엣지)+ResearchLabPanel(엣지·상관·안정성)+Wiki | **Live 스테이지에 통합 후 은퇴 예정(W1)** |
| secondary | 카탈로그 | `V4Catalog`(v4-catalog.jsx) | P4 5뷰(연혁실·함정지도·절실험실·출구은행·B1 scorecard) SELECT-only | **데이터 안보임(research_assets.db gitignore)**(R2) |
| 서랍 | Context | window.AIContextPanel | AI 컨텍스트 팩(개발자 서랍, 레일 하단 토글) | 존치/제거 재검토(W6) |

### 3.3 백엔드(FastAPI, `ai_strategy_loop/dashboard/app.py` + 라우터)
- 상태/실시간: `/status`, `/health`, `/ws`(단일 발행기), `/config/spec`.
- 연구 카탈로그(P4, `research_api.py`, SELECT-only·무재집계): `/research/summary`(영수증 provenance 카운트, authoritative=false)·`/research/assets`·`/research/judgments`·`/research/clauses`·`/research/cells`. DB는 `STOM_RESEARCH_ASSETS_DB` env(무설정 시 `legacy_non_authoritative_catalogs/research_assets.db` 폴백, **gitignore**).
- 연구 문서/기록: `/research_docs`·`/research_doc`(Wiki 원문), `/research_records`·`/research_records/detail`, `/research_index`.
- 리포트: `/reports`(docs/ 하위 *.html 열거)·`/reports/view`(traversal 차단·CSP `default-src 'none'`·sandbox). 오프라인 생성기 `report_writer.py`+`scripts/build_step_reports.py`(표준양식·manifest·atomic).
- 백테스트: `/bt/run`·job progress/cancel·결과·MC·A/B·portfolio·`/bt/report`.

### 3.4 빌드·자산
- `webui-build/build-app.mjs`가 v4-*.jsx 등을 단일 `bundle/app.js`로 esbuild 번들(+ `stom-ui.js`), HTML `?v=` 갱신.
- `v4.css`(V4/V5/V6 전용 CSS, 수동 핀) / `styles.css`(공용, 핀 하드검증 — 건드리지 말 것).

---

## 4. 부족·개선 필요 (V6 대상, 실측 근거)

3440×1440 실측: `.v4-rlive`=`1fr 480px` → **hero-col 2782px에 Fitness 1382px 단일 그래프**, scrollHeight 2653px(1.84화면). "한 화면 여러 과정 동시"는 미달.

핵심 미흡(우선순위 순):
1. **Live 스테이지 구동 재설계(L4·L1·L2·L3·L5·L6·L7·L8·G6·G9)** — generate/backtest/score/autopsy/iterate 스테이지 탭 + 자동전환 + 단계별 단일 포커스 시각화. 상단 통합 상황판. 글자블록→미니 시각화. 거대 그래프→스테이지 멀티뷰. fold/버튼 병합.
2. **Lab을 Live 백테/분석 스테이지에 통합(W1)** — 별도 fold가 아니라 해당 스테이지 자리.
3. **IA 재정렬(R1·W2·W3·W4·W6·G1)** — 탭순서 Backtest·Replay를 Reports 뒤로. 워크벤치=명예의전당 전용. Lab·audit 은퇴. Context 결정.
4. **데이터 가시성(R2·R5)** — Catalog·명예의전당이 실화면에서 보이도록(데모 시드/연결).
5. **동적 리포팅·Wiki(G5·G7·G8·R4)** — 라이브 스텝 연동 자동 HTML + 결과예시 탭 + Wiki 표준·검색.
6. **History 데이터 아키텍처(L9)** — 리스트→상세 마스터-디테일.
7. **Alpha 연구기록 체계화(R3·W5)**.
8. **Backtest 강력 시각화(B1, 사장님 3·4 = UX 후)**.
9. 잔여: 우측 펼쳐확대(G2)·탭 타이포(G4)·재연결 깜빡임(L10).

→ 상세 배정·로드맵·수용기준은 `2026-07-19_v6_dashboard_live_stage_redesign_master_plan.md` 참조.

---

## 5. 핵심 결정·제약 (불변)
- `performance_proved=false`. 통제 A/B 증거 전 성능 주장 금지. v11 strict-resume DDL 금지.
- `/ui` = 정본 V4 그래프-우선 셸. legacy는 1회성.
- 연결 git 라인: `--no-ff` merge(squash/cherry-pick 금지).
- 내비 retire(Lab/Context/audit)는 dual-mount·field parity·redirect·default-off flag·rollback 통과 후에만.
- Reports: allowlist root·traversal 차단·sandbox+CSP 유지.
- P4 카탈로그: SELECT-only·무재집계·정본 승급 전 비정본 preview.
- 보호 경로 쓰기 금지: `_database/`, `_log/`, `backup/`, `*.db`, `backtest/graph/` 등.
- 커밋: 한국어, 명시적 stage, `.gjc/`·`.omo/` 커밋 금지, `artifacts/`는 OK.

---

## 6. 병렬 라인·정본 통합 대기
- `wt-dev`(`feature/dashboard-v5-overhaul-20260718`, HEAD 진행 중, 8770)에서 **다른 에이전트가 동일 V5/V6 계획을 병행**(속도 느림). 미병합·독립.
- **미결 결정**: 두 라인(wt-v5 정본 vs wt-dev)의 정본 통합 방침 + mainline(`STOM_Version_2U_C-ai-strategy-loop`) 라인연결 반환 PR 시점.

---

## 7. 참조 문서(읽기 순서)
1. `2026-07-19_v6_dashboard_live_stage_redesign_master_plan.md` — **현재 정본 계획**(요청 전수·근본원인·V6 로드맵).
2. `2026-07-18_v5_series_dashboard_overhaul_master_plan.md` — V5 계약·수치기준(2268b709 확정).
3. `2026-07-18_v4_dashboard_ux_redesign_master_plan.md` §11 — V4 재검토 체크리스트.
4. 본 문서 — 종합 핸드오프.

---

## 8. 다음 착수(승인 대기)
**V6.0 Live 스테이지 구동 재설계**(사장님 최우선). 구조 변경 규모가 커 승인 후 브랜치→구현→3해상도 수치 검증→라인연결 merge. 병행 결정: Context 존치 여부, 탭 순서 확정, 스테이지 구성(generate/backtest/score/autopsy/iterate) 확정.
