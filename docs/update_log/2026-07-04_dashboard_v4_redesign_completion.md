# 2026-07-04 Dashboard V4 리디자인 완성 — 프로토타입 IA 재구축 (P1~P6)

## 1. 결론

승인된 Artifact 프로토타입(`design-system/v4-redesign-prototype.html`,
https://claude.ai/code/artifact/84cca395-6033-487f-a8c3-126da425c37e)의 IA/UX/UI 로
**V4 를 전면 재구축 완료**했다. V2 전체 기능(컴포넌트 정본 재사용) + V3 장점(안전/감사
어휘·workflow) + **최신 wt-dev 연구 관찰성(P1 포트)** 이 통합됐고, run 제어(설정·시작/정지)
가 V4 안에서 직접 동작한다. V2 기본 경로는 무변화(opt-in `/ui/v4`).

브랜치 `feature/dashboard-v4-20260704`. 선행 커밋: Phase 0~7(기초 스캐폴드, `2e7d7c80`~
`dbe4684d`), 본 리디자인: `7fd1092e`(P1) → `4cd459bb`(P2~P5) → (P6 본 커밋).

## 2. 구현 내용

- **P1 — wt-dev frontend 델타 포트(6파일)**: `loop/process-research-pipeline` HEAD
  `4e2e313c` 에서 무충돌 checkout — `panels-analysis.jsx`(ConditionDiscoveryPanel
  research_observability: Research Pack/Branch Tree·Candidate Pack/Analysis Cards·
  Prompt Receipts·Promotion Blockers), `phase-detail.jsx`(process selector,
  research-allowed vs review-only + PROCESS_FALLBACK_CATALOG), `rp-heatmap/rp-panel.jsx`
  (대형 Edge-Ratio 히트맵), `analysis.jsx`, `styles.css`.
- **P2 — 셸**: 좌측 슬림 레일 7뷰(Live/Backtest/Replay/Lab/Bench/Audit/Context) +
  상단바(브랜드·안전 strip·BASE 컨트롤·Conn/Status·테마) + 컨트롤바(**설정·시작/정지·
  진행도·RUN 셀렉터** — app.jsx 패턴 재사용, SettingsModal/CodeViewer 중앙 호스팅).
  `?tab=` 딥링크, `?base=` 1회 오버라이드, Replay keep-alive.
- **P3 — Research Live(플래그십)**: workflow/authority strip(PhaseTimeline+mode_authority
  칩) → **V4HeroChart**(신규 대형 canvas fitness — 그라디언트 area·gate 점선·best/현재
  마커·테마/DPR/리사이즈 대응) → 스탯 행 → 보조 차트 → 접이식(Live 상세·process
  selector·세대표+백테상세·Generation Analytics·가정/부검/계보/홀드아웃·설정/비용) /
  rail(현재세대·Best/Winner 게이트+ApprovalDialog·**ConditionDiscoveryPanel**·Population).
- **P4/P5**: Backtest=BacktestTab·Replay=SimulationTab 통째(기능 정본, keep-alive),
  Lab=대형 히트맵+ResearchLab, Workbench=ResearchPro+RunCompare+HoF+**HofInventoryGate**,
  Audit=VerdictPanel(내부 Vdt* 체크리스트 포함)+안전 strip, Context=**AIContextPanel**.
- **P6**: 클램프 폴리시(idle `current_gen=-1` → "—"), `scripts/v4_capture.py`
  (Playwright 캡처 도구), 게이트/문서.

## 3. 검증 증거

| 게이트 | 결과 |
|---|---|
| 빌드 | 0에러 (esbuild bundle) |
| jsdom 하네스 V1~V7 | **allPass** — V7=V4 셸+7뷰(idle/running), running 은 needles 로 `research-observability-grid` 실렌더 단정(missingNeedles=[]) · V2 index/V3 8탭/V4 standalone 회귀 0 |
| pytest | `test_track_z_pr1_harness.py` + `test_dashboard_route_parity.py` **19 passed** (bundle-sync 1건은 테스트 도중 소스 갱신 경쟁 — 커밋 후 재실행 통과 확인) |
| 브랜치 게이트 | `verify_nonrelease_sync.py` 통과(exit 0) |
| TestClient | `/ui/v4`→307→200(v4-preview)·`?dashboard_version=v4` 서빙·미지값→v2 폴백·V2 4경로 무변화 |
| **시각(스크린샷 판독)** | Playwright(Chrome)로 7뷰×dark + research light 캡처 → 직접 판독: 레일/상단바/hero(첫 뷰 40%+)/관찰성 rail/양 테마 모두 프로토타입대로 렌더. 캡처: `.omo/evidence/dashboard-v4-redesign-20260704/captures*/`(로컬 증거) |

시각 판독에서 잡은 결함 1건(idle `-1/—` 노출)은 클램프로 수정 후 재캡처 확인.

## 4. wt-dev 실데이터 연동 — 실측 결과와 정확한 경로

- wt-dev 백엔드를 8791 로 병행 기동(읽기 전용): `/health` ok·`/runs` **455개**·
  `/status`=**running(gen 10/11, lat_tick_official_full_warm64_chunk08_supplement13_23_20260704)** — 실데이터 서빙 확인.
- 단, `?base=http://127.0.0.1:8791` 크로스오리진 연동은 **데모 폴백**됨. 원인 확정:
  `app.py:81-87 _ALLOWED_ORIGINS` 가 **8770 전용 allowlist**(계획 시 참조한 "CORS 모두
  허용" 주석은 실구현과 다름 — 보안상 의도된 allowlist). 8790-origin 응답이 차단되어
  `conn-backend.jsx` 가 demo 로 폴백.
- **동작하는 경로(코드 무수정)**: V4 프론트를 **8770 에서 서빙**하면 origin 이 allowlist 에
  있어 8791 데이터 연동이 성립 —
  `uvicorn ai_strategy_loop.dashboard.app:app --port 8770` (이 워크트리) 후
  `http://127.0.0.1:8770/ui/v4?base=http://127.0.0.1:8791`.
  (8770 을 기존 구버전 서버가 점유 중이면 먼저 종료 필요 — 사용자 결정.)
- 최종적으로 V4 가 wt-dev 레인에 채택되면 same-origin 이라 이 제약 자체가 소멸.
- 신규 관찰성 패널의 라이브 `research_observability` 데이터는 wt-dev **백엔드**(37커밋,
  이번 범위 외)가 emit — 이 브랜치 백엔드에선 대기/폴백 표시(패널 내장 동작).

## 5. 실행 방법

```
cd ai_strategy_loop/dashboard/webui-build && npm run build   # 소스 수정 시
uvicorn ai_strategy_loop.dashboard.app:app --port 8790       # 이 워크트리
# V4: http://127.0.0.1:8790/ui/v4   (V2 그대로: /ui/)
# 스크린샷: python scripts/v4_capture.py --base http://127.0.0.1:8790
# wt-dev 실데이터(8770 서빙 시): /ui/v4?base=http://127.0.0.1:8791
```

## 6. 남은 항목(후속)

- 상단 BASE 수동 변경도 allowlist 제약 동일 — cross-origin 연동을 정식 지원하려면
  `_ALLOWED_ORIGINS` env 확장(예: `STOM_DASHBOARD_ALLOWED_ORIGINS`)을 별도 검토
  (V2 공유 코드·보안 정책이라 단독 변경 지양).
- measurement frame/slippage UI: 백엔드(wt-dev 37커밋) 동기화 후 표면화.
- 라이브 happy-path UAT(연구 시작→세대 진행→승인 게이트)는 사용자 브라우저 확인.
