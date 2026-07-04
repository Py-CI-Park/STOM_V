# 2026-07-05 V4 대시보드 최종 검증·운영 가이드 (성숙도 ~98/100)

> 브랜치 `feature/dashboard-v4-20260704` · 관련 문서:
> `2026-07-04_dashboard_v4_redesign_completion.md`(P1~P6 상세),
> `2026-07-05_v4_wtdev_backend_sync_verification.md`(백엔드 동기화 검증)

## 1. 오늘까지의 전체 여정 요약 (커밋 체인)

| 커밋 | 내용 |
|---|---|
| `2e7d7c80`~`dbe4684d` | V4 기초(opt-in 셸·라우트·초기 6탭·하네스 V7 게이트) |
| `7fd1092e` | **P1** wt-dev 연구 관찰성 frontend 6파일 무충돌 포트 |
| `4cd459bb` | **P2~P5** 승인 프로토타입 IA 전면 재구축(좌측 레일 8뷰·run 제어·V4HeroChart·관찰성 rail) |
| `f797d9eb` | **P6** 스크린샷 시각검증 루프(`scripts/v4_capture.py`)·클램프·완성 문서 |
| `3c93936d` | V2 기능 전수감사 누락 4건 보강(History 뷰·GuiParity·Glossary·Wiki) + 실데이터 라이브 실증 |
| `cd5ece18` | 하네스 테스트 격리 수리(jsdom 실 WS 누출 차단 — 결정성 확보) |
| `5cf11cd1` | **A·B·C** 자동 브라우저 UAT(`scripts/v4_uat.py`)·CORS env 옵트인·온보딩/접근성 |
| `19ddf809`~`360e6bef` | **D** wt-dev 백엔드 37커밋 동기화(격리 검증 722 passed → 채택 ff-merge) |
| (본 커밋) | /runs 초기혼잡 재시도 루프 + 아카이브 시각화 스윕(`scripts/v4_archive_check.py`) + 본 문서 |

**머지 방향 명확화**: `loop/process-research-pipeline`(wt-dev) → V4 브랜치로 **가져오기만** 했다.
wt-dev 브랜치·워크트리는 무접촉, 원격 push/PR 없음(전부 로컬).

## 2. 실행·테스트 가이드

```bash
# 터미널1 — V4(머지된 백엔드):
cd STOM_V.wt-dashboard-remodel && python -m uvicorn ai_strategy_loop.dashboard.app:app --port 8790
# 터미널2 — wt-dev 실데이터(읽기 전용):
cd STOM_V.wt-dev && python -m uvicorn ai_strategy_loop.dashboard.app:app --port 8791
# (선택) 크로스오리진 연동용 allowlist origin: 포트 80 으로 터미널1을 대신 기동
```

| 주소 | 용도 |
|---|---|
| `http://127.0.0.1:8790/ui/v4` | V4 단독(자체 백엔드) |
| `http://127.0.0.1/ui/v4?base=http://127.0.0.1:8791` | **wt-dev 실데이터 연동**(80 서빙 시) |
| `http://127.0.0.1:8790/ui/` | V2(무변화 확인용) |

크로스오리진 정식 확장: 데이터 서버 측 env `STOM_DASHBOARD_ALLOWED_ORIGINS=http://127.0.0.1:8790`
(기본 allowlist 는 8770 전용 — 불변).

## 3. wt-dev 과거 연구로 V4 를 점검하는 체크리스트 — ✔ = 본인(Fable)이 직접 구동·판독 완료

캡처 증거: `.omo/evidence/dashboard-v4-redesign-20260704/{captures*,uat,archive-check}/`
사용 과거 run: `lat_tick_official_full_warm64_chunk09_retry01_20260705`(24세대 전부 graded),
`human_fullperiod_seed_replay_20260628`(winner·gate 4).

| # | 체크 항목 | 방법 | 결과 |
|---|---|---|---|
| 1 | RUN 셀렉터에 과거 run 목록 로드(457+) | Live 우상단 RUN 드롭다운 | ✔ 458개 로드(초기 혼잡 재시도 루프로 안정화) |
| 2 | 과거 run 선택 → **run=archive** 전환 | run 선택 후 헤더 확인 | ✔ 두 run 모두 archive 표기 |
| 3 | **hero fitness 곡선**(다세대) | 24세대 run 선택 | ✔ g0~g23 24점 곡선·gate 점선·best/현재 마커 |
| 4 | **BEST=WINNER 카드 + 승인·Export 게이트** | winner 보유 run 선택 | ✔ 5.532/1.804 graded·게이트✓·승인 버튼 노출 |
| 5 | 스탯 행(현재세대/best/MDD/비용) | 아카이브 상태 | ✔ 실측치(예: -8.0%·-19.8%) |
| 6 | 수익 추이·품질지표 보조 차트 | Live 하단 | ✔ 실 라인 렌더 |
| 7 | **EquityOverlayChart**(run 자본곡선) | Live 중단 | ✔ 다색 실 곡선(기간 축 포함) |
| 8 | 세대표(GenerationsTable) + **백테상세 차트** | Strategy/Prompt fold | ✔ 행·일별 PnL·누적 곡선 |
| 9 | **EvolutionGuiParityPanel**(GUI 패리티 차트군) | 동일 fold | ✔ 일별/시간대/보유/롤링 차트 렌더 |
| 10 | Generation Analytics(멀티라인·산점도·상위표) | 전용 fold | ✔ |
| 11 | **process selector**(research vs review 권한) | 프로세스 fold | ✔ 3-프로세스 카드·readout·파이프라인(포트 기능) |
| 12 | 가정/부검/계보/홀드아웃 | 진화 분석 fold | ✔ 렌더(데이터 없는 항목은 대기 표기) |
| 13 | **History**: 캠페인 17건·TOP CANDIDATES | History 뷰 | ✔ Best PnL·후보 실측 |
| 14 | **Lab**: Edge Ratio 히트맵/구간별 edge | Lab 뷰(선택 run 컨텍스트) | ✔ 0.510·21k~36k건 셀 |
| 15 | **Workbench**: run 심층 + HoF 프로 테이블 | Bench 뷰 | ✔ 12행 실측(점수·수익·MDD) |
| 16 | **AI Context Pack**(과거 run/gen) | Context 뷰 | ✔ gen3/36·전략명·verdict·forbidden 3건·copy |
| 17 | Replay 실재생 + **keep-alive** | ⚡최근 거래일 → 재생 → 뷰 이탈/복귀 | ✔ 09:02→09:03 재생 지속 |
| 18 | Backtest 라이브러리 로드+전략 선택 | Backtest 뷰(8791 데이터) | ✔ (실행은 옵트인 보류) |
| 19 | 라이브 스트리밍(연구 실행 중) | 실행 중 run 관찰 | ✔ gen 진행·배치 라벨 실시간(당시 chunk09 실행 중 실증) |
| 20 | 양 테마·V2 무회귀·미지버전 폴백 | light 캡처·TestClient | ✔ |

미검증(의도적 보류): 백테 **실행**(활성 연구 CPU 경합 회피 — `v4_uat.py --execute` 옵트인),
**E** 실연구 시작→승인 E2E(LLM 비용 — 사용자 승인 대기).

## 4. 이번 검증에서 발견·수리한 결함

| 결함 | 원인 | 수리 |
|---|---|---|
| 하네스 비결정 실패 | jsdom 이 WebSocket 을 구현 → 실서버(:80) state 프레임이 fixture 를 덮음 | mock 무조건 설치(hermetic) — `cd5ece18` |
| RUN 목록 간헐 미도착 | `/runs` 2.6MB 가 초기 동시 fetch 큐 맨 뒤로 밀려 타임아웃, 재시도 없음 | 15s + 4s 간격 최대 4회 재시도(본 커밋) |
| idle 진행도 "-1" 노출 | 백엔드 idle current_gen=-1 | "—" 클램프 — `f797d9eb` |

## 5. wt-dev 반영(PR) 전략

① 이 브랜치에서 실험·안정화(현 단계) → ② PR 직전 wt-dev tip 재머지+게이트 재실행 →
③ `git push -u origin feature/dashboard-v4-20260704` 후 **base=`loop/process-research-pipeline`** PR
(이미 wt-dev 를 포함하므로 diff 는 V4 프론트+게이트/문서만) → ④ merge 는 **wt-dev 연구 run 사이(idle)** 에 →
⑤ merge 후 wt-dev 에서 `/ui/v4` 스모크·본 실험 워크트리 정리. push/PR 은 사용자 지시 시에만 실행.

## 6. 남은 항목(→100)

- **E**: V4 에서 실연구 시작→세대 진행→승인 게이트 E2E(LLM 비용 승인 시 자동 수행)
- 사용자 주관 UX 피드백 1회전(브라우저 확인 후 CSS/배치 미세조정)
