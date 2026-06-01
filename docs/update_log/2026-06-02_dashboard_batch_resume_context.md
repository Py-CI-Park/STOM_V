# AI 조건식 루프 — 세션 재개 컨텍스트 (2026-06-02)

> **목적**: context 96% 도달로 compact/새 세션 전 핸드오프. 무중단 재개용.
> **브랜치**: `STOM_Version_2U_C-ai-strategy-loop` · **워크트리**: `C:/System_Trading/STOM/STOM_V.wt-dev`
> **상세**: `docs/update_log/2026-06-01_direction_reframe_and_infra_plan.md` + MEMORY.md ㉑㉒㉓.

---

## 0. 한 줄 현황
사용자 대규모 요청(버그·명전보강·진행률·동시보유·샘플주입·2번째그래프·P0~P1) **6항목 전부 완료**. 전부 code-reviewer(opus) APPROVE · 결정론 baseline **7 failed / 2081 passed 신규0** · 엔진/하드게이트 무수정 · 신규 토글 기본 OFF. 트래킹 트리 클린(전부 커밋).

---

## 1. 목표 재정의(중요 — 평가 프레임)
**reference 완벽 모방이 목표 아님.** 인간 19전략은 전문가가 수년간 손으로 발견·조합한 것. 목표 = **AI의 반복·퀀트·데이터분석 강점으로 "스스로 발전하는" 조건식 연구 시스템 구축.** reference = PASS/FAIL 타깃이 아니라 **north-star(방향타)**. 이번 세션 인프라가 그 발전 엔진의 골격.

---

## 2. 이번 세션 커밋 체인(후반 대시보드 배치, 최신순)
| 커밋 | 내용 |
|------|------|
| `1ad1ae37` | #65 P0~P1: **run 셀렉터**(/run_state로 임의 run DB재구성→**segrun 오염 영구우회**)+테이블→백테상세 연동+분석클러스터 판정위로+Best/Winner병합. 기본 LIVE 하위호환 |
| `6136884f` | #67 **few-shot 샘플주입**: exemplar_pool(passing/seed_db·timeframe매칭·복제금지·토글 OFF byte-identical) |
| `da9d420d` | #66 **STOM 2번째그래프**: 동시보유 종목수 시계열(매수/매도시간 event-sweep) BacktestDetailChart 상단 |
| `d3943cbb` | #64 **진행률·진행시간·완료시간**: LatestInfo 3필드+loop 단계경계 시각+이산 N/5+/generation_durations(retroactive). LIVE발행전용 graded/DB무관 |
| `41340f25` | #63 명전보강: 백테기간·'단기'(연환산과대)tooltip·인간 스크린샷 갤러리(/reference_img StaticFiles) |
| `190715a4` | Batch A 버그: **동시보유 0**=score.py dispersion OFF시 엔진실측값 버리던 정보손실→raw 항상저장(graded byte-identical) / **수익률 0**=contract Optional+state.py NULL→None+table.jsx '—' |
| `4a6e144c` | 성과 명예의 전당 패널(인간19+시드17+AI13·운영금대비 토탈/연평균) |
| `e5b79abf` | O1 BacktestDetailChart(일별손익+누적, /backtest_detail) |
| `629ee3e0` | O2 equity_points DB(v10)+parse_backtest_series 공유파서 |
| `1c984c4a` | 누적수익곡선 버그(run필터+퍼센타일클립+틱라벨) |

> 더 앞: 방향재조준 `2fea555e` + Phase1(`4b06f087`대시보드차트·`8cbe191d`프롬프트DB·`f60e04af`델타) + Phase2(`0a7beaa5`가정코어·`2ef5fec8`환류·`c7048b6f`패널) + Phase3(`cc32bb12`매도체결강도) + reframe1 smoke검증.

---

## 3. 대시보드 현황 (`python -m ai_strategy_loop` → `http://127.0.0.1:8770/ui/`)
**모든 신규 기능 LIVE**(엔드포인트 실측 확인됨):
- **run 셀렉터**(상단 드롭다운): 41 run 선택 열람. `reframe1` 선택 시 segrun 오염 무관 실데이터.
- **명예의 전당**: 인간19+시드17+AI13, 운영금대비 토탈/연평균%, 백테기간, '단기'플래그, 📷스크린샷 갤러리(17).
- **백테 상세**(BacktestDetailChart): 상단 동시보유 종목수 + 하단 일별손익+누적곡선 (STOM 2그래프).
- **품질지표 추이**·**가정 패널**(verdict)·**프로세스 진행률/시간**·**코드뷰어**.

⚠️ **운영 주의**: 에이전트/테스트가 `current_state.json`에 합성 `segrun`을 덮어쓰면 LIVE 뷰가 오염됨. **해결=run 셀렉터로 실 run 선택**. 임시 복원 스크립트(reframe1):
```python
# LoopState→to_loop_state(summary, gens, status='complete')→publish_loop_state. (이전 세션 본문 참조)
```

---

## 4. 🔴 다음 단계 (재정의된 목표 = AI 발전형 연구 시스템)
**핵심 = 인프라/관찰/버그 다 정리됨 → 이제 도구로 "생성 개선"을 실측할 차례.**

| 우선 | 작업 | 방법 |
|---|---|---|
| 🟢 **A** | **few-shot 생성 실효 검증** | `few_shot_enabled=ON`(source=passing 또는 seed_db) + 짧은 백테(1개월/소형, 3년 OOM회피)로 생성물 거래수 bounded·흑자·시드급인지 측정. config=`run_reframe_smoke_config.json` 변형 |
| 🟢 **B** | **재조준 검증 확대** | reframe1(1개월)을 3개월/1년 OOS로 확대해 빈도·동시보유·MDD 이동 측정(우호창 과적합 차단). 단 OOM 주의(~5세대 한계) |
| 🟡 **C** | 라이브 page_data 발행 | PhaseDetailPanel 상세뷰가 DEMO 전용 → 실 LIVE run에서 부검/가정 패널 비는 비대칭. loop.py _build_live_page_data 발행 보강(실 진행 run으로 검증 필요) |
| 🟡 **D** | phase 4중 중복 통합 | PhaseTimeline+ProcessFlowPanel 통합·5단계 정식화 |

**인프라 주의**: 3년 풀유니버스 단일 warm run은 과발화 전략 메모리폭증으로 ~5세대 OOM. 크래시 시 고아 엔진 누적 → `MSYS_NO_PATHCONV=1 taskkill /F /IM python.exe`(python3.exe 보존). 검증은 짧은/소형 우선.

**불변식(모든 작업)**: 엔진(backengine_*)·하드게이트(compute_fitness)·backtest/graph/ 무수정 · 신규기능 config 토글 기본 OFF·byte-identical · code-reviewer(opus) APPROVE · `PYTHONUTF8=1 python -m pytest tests/unit/ -q -p no:randomly` 기존 7 failed 외 신규0 · `python scripts/verify_nonrelease_sync.py` 통과.

---

## 5. 재개 명령어 (compact 후 / 새 세션 첫 메시지)
```
ai_strategy_loop 이어가자. docs/update_log/2026-06-02_dashboard_batch_resume_context.md +
MEMORY.md ㉑㉒㉓ 먼저 읽고. 6항목 대시보드 배치 완료됨(트리 클린).
다음=(A) few-shot 생성 실효 검증: few_shot_enabled=ON으로 짧은 백테(1개월/소형, 3년 OOM회피)에서
생성물 거래수 bounded·흑자·시드급인지 측정. 또는 (B) 재조준 3개월/1년 OOS 확대.
크래시 시 taskkill /F /IM python.exe(python3.exe 보존). 엔진무수정·토글OFF·code-reviewer·
결정론 baseline 신규0 유지. 대시보드 python -m ai_strategy_loop → run 셀렉터로 reframe1 선택.
```
재개 시 MEMORY.md ㉑㉒㉓ + 이 문서 자동 로드 → 무중단.
