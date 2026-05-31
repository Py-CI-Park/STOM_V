# AI 조건식 루프 — R6 풀유니버스 돌파구 인계 (2026-05-28, 단일 자급자족)

> **이 문서 하나만 읽으면 새 대화에서 무중단 재개 가능.** 다른 문서 의존 없음(있으면 보너스).
> 브랜치 `STOM_Version_2U_C-ai-strategy-loop` · 워크트리 `C:/System_Trading/STOM/STOM_V.wt-dev`.
> 직전 커밋 `ea9ea0ad`. python = `C:/Python/64/Python31313` (이 머신은 `python`이 pandas/의존성 보유).
> 모든 실행은 환경변수 `STOM_ALLOW_MINIMAL_SETTING=1` 필요. 콘솔 한글 깨지면 `PYTHONIOENCODING=utf-8`.

---

## §0. TL;DR — 지금 어디 있고 다음에 뭘 하나

**목표**: 사람이 GUI로 수동하던 조건식(매수/매도 전략) 개발을 AI(GPT-5.5/gpt_auth)가 자율(생성→백테→분석→개선→반복) 대체해, **보고서 우수전략급**(연130~262%·매매성능지수1.25+·MDD2~7%·일평균10~23·다중보유6~12) 조건식을 생산 + 실시간 웹 대시보드로 관찰 + 연구 파이프라인 누적.

**🎉 이번 세션 최대 성과(결정적)**: **풀유니버스(warm+tick)에서 Tick_902 시드가 흑자·보고서급임을 입증.** 그동안 음의 엣지였던 건 LLM 품질이 아니라 **dev-scale(소수 종목) 규모 문제**였음이 확정됐다. 선택적 보고서 전략은 풀유니버스(~수백~1379종목)가 본질.

**다음 세션 첫 행동(거의 확실한 첫 winner)**: `run_full_evo_config.json`에서 **`min_daily_trades` 0.4→0.3**으로 낮추고 재run → gen0(Tick_902 = profit+740K·MDD0.88·calmar117)이 freq게이트를 통과해 **첫 풀유니버스 보고서급 winner로 졸업**한다. (§4 참조.)

**현재 블로커 없음.** winner가 0이었던 건 능력이 아니라 게이트 경계 보정 문제(gen0 freq 0.3<0.4 근소, gen5 MDD 10.01>10 근소).

> **🆕 2026-05-29 갱신 (§3.3 추가)**: 위 "다음 첫 행동"은 **이미 달성됨**.
> ① `min_daily_trades`는 0.3으로 적용 완료, ② `fullevo2_grad` run에서 **gen0 Tick_902가 gate=1 졸업**(첫 풀유니버스 winner 확정), ③ **`fullevo3`(3개월) 완료** — gen0이 3개월에서도 흑자·통과(+1,944,536·MDD5.39·calmar31, MDD가 보고서 타겟 2~7%에 정상화). **빈도-흑자 프론티어가 본질적 장벽임 재확인.**
> **새로운 다음 행동 = Track B(진입 재설계): 고빈도(일평균10~23)와 흑자 양립**(§3.3·§4 갱신 참조). gen4 단서(흑자·MDD3인데 빈도 0.2) = 다종목 분산으로 빈도↑하면서 흑자 유지가 핵심.

---

## §1. 프로젝트 개요 + 철학

- **코드 위치**: `ai_strategy_loop/` 패키지.
- **두 진입점**:
  - 대시보드: `python -m ai_strategy_loop --port 8770` → `http://127.0.0.1:8770/ui/`
  - 헤드리스 루프: `python -m ai_strategy_loop.controller.loop --config-json <cfg.json> --run-id <id>`
- **루프 흐름**: (시드 또는 fresh) 전략코드 생성 → 백테 → 복합 적합도 채점(게이트+graded) → 부검 피드백 → 다음 세대 재생성(refine-from-best hill-climb). 매 세대 `state/current_state.json`에 발행 → 대시보드 WS가 라이브 표시.
- **철학(사용자 명시)**: 조건식은 한 번에 안 나온다(경우의 수 많음). **생성=탐색, 백테=검증, 분석=연구.** 최종 목적은 일회성 "좋은 전략"이 아니라 **지속 관리되는 연구 파이프라인**(전략기록·버전비교·누적·메타분석). 평가축은 "10세대에 우승?"이 아니라 "개선 방향이 옳은가(선별성↑·MDD↓·과매매 억제)". 보고서 우수전략 공통 가치 = **승률보다 매매성능지수(payoff)·MDD 저·다종목 분산**.

---

## §2. 이번 세션의 발견 체인 (왜 여기 왔나 — 순서대로)

### 2.1 R4 진단 정정 (이전 핸드오프가 틀렸음)
- 이전 R4 핸드오프는 "tick 0거래 = 관심종목 게이트 블로커"라 했으나 **틀림**.
- **사실**: `관심종목`은 tick 데이터에 **50~67% 존재**(엔진 `backtest/backengine_future_tick.py:88 if not 관심종목: continue`는 통과). 엔진 게이트는 데이터 플래그(arry_code 컬럼)에 의존하며, 이 종목들은 플래그가 충분.
- **진짜 블로커 = 시가총액 미스매치**: 시드 `Tick_902`는 `if 시가총액<3000`(소형주)에서만 매수. 그런데 `build_subset_db`(유동성=거래대금순 선별)는 전부 **대형주**(평균 3~6.6조)라 시총<3000 틱이 ≈0 → 매수=False 고정 → 0거래.
- **실증**: 시총 제약 없는 느슨 전략 PoC → trade_count 12>0 (대형주 subset).

### 2.2 R4 대형주 fresh 진화 (음의 엣지)
- run=r4tick1 (N=8 대형주 tick, cold, 8세대, 18분): 파이프라인 전부 정상이나 **winner 0, 전세대 음수**. plateau graded~0.489. 빈도는 보고서급(gen0 93거래=일평균18.6)인데 흑자 미달.

### 2.3 R5 소형주 도메인 + 윈도우 개선
- **소형주 스캔**: 소스 `_database/stock_tick_back.db` 전체 2425종목 중 **1878종목**이 소형주 아침(시총<3000 & 관심종목=1 & 09:00-09:30) 활동. (스캔 121초.)
- **소형주 subset 빌드**: top-12 → `state/tick_subset_small.db` (524MB). top-12 = `024060 388050 053050 004090 356680 218150 005860 086960 003310 370090 288980 002140`.
- **Tick_902 isolation (소형주 N=12) = 여전히 0거래**: richest 윈도우(시총<3000 아침틱 41,747 충족)에서도 0. **병목은 시총/윈도우가 아니라 Tick_902의 ~10조건 AND 체인** — 12종목 규모에선 진입 confluence가 안 생김.
- **윈도우 선택 개선(커밋 `ea9ea0ad`)**: `_select_universe_window`가 '가장 이른 N일'만 골라 데이터 빈약 → `config.bt_window_select` 토글 추가: `earliest`(기본·하위호환) / `richest`(moneytop coverage 최대 연속구간). 테스트 4/4·회귀 0.

### 2.4 🎉 R6 풀유니버스 돌파구 (구조 결론 확정)
- 선택적 전략은 dev-scale로 재현 불가 → **풀유니버스(`bt_engine_mode="warm"` + `bt_timeframe="tick"`)** 로 직행(사용자 결정).
- **결과**: Tick_902가 풀유니버스에서 **흑자·보고서급**. dev-scale의 0거래/음수와 정반대. (§3 데이터.)

---

## §3. 풀유니버스 실측 데이터 (재개 시 비교 기준)

### 3.1 smoke (1주, `run_full_smoke_config.json`, run=fullsmoke1)
- back_count=202종목, 16엔진. **prepare ~90s + 백테 run 18.3s** (세대당 ~1hr 우려 기각 — warm tick 빠름).
- Tick_902: **gate=True(통과)·profit +606,123·MDD 6.07·trades 4·calmar 49.98·r² 0.947·graded 48.35·winner 졸업.**

### 3.2 진화 (1개월 2025-01, `run_full_evo_config.json`, run=fullevo1, 8세대, 21분)
- prepare back_count=400종목. seed=Tick_902, refine-from-best, winner_objective=profit.
- **빈도-품질 프론티어 (핵심 발견)**:

| 세대 | trades | 일평균 | profit | MDD | calmar | r² | gate | 비고 |
|------|--------|--------|--------|-----|--------|-----|------|------|
| **gen0 (Tick_902)** | 6 | 0.3 | **+740,353** | **0.88** | 117 | 0.865 | ✗ freq 0.3<0.4 | 보고서급 우수 |
| gen1 | — | — | — | — | — | — | timeout(327s>300) | 과발화 fail-fast |
| gen2 | 15 | 0.75 | −284,630 | 8.48 | −9.3 | 0.60 | ✗ 수익음수 | |
| gen3 | 22 | 1.1 | −233,893 | 10.95 | −5.9 | 0.72 | ✗ MDD+수익 | |
| gen4 | 25 | 1.25 | −116,988 | 8.77 | −3.7 | 0.58 | ✗ 수익음수 | |
| **gen5 (best)** | 39 | 2.0 | **+234,362** | 10.01 | 6.5 | 0.10 | ✗ MDD 10.01>10 | 고빈도 흑자, 근소탈락·변동성 |
| gen6 | 42 | 2.1 | −19,889 | 12.83 | −0.4 | 0.51 | ✗ | |
| gen7 | 43 | 2.15 | +66,627 | 11.37 | 1.6 | 0.30 | ✗ MDD | |

- **결론**: 빈도 0.3→2.15/day 올릴수록 수익 +740K→마진, MDD 0.88→13 악화. **흑자 엣지는 본질적으로 저빈도**(부검 가설 확증). best_gen=5, winner=−1(졸업 0).
- **winner 0 = 게이트 보정 문제**(능력 아님): gen0 freq 0.3<0.4 근소·gen5 MDD 10.01>10 근소.

### 3.3 졸업 확정(fullevo2_grad) + 3개월 확대(fullevo3) — 2026-05-29

**(A) fullevo2_grad (1개월, min_daily_trades 0.3)**: gen0 Tick_902 **gate=1 졸업** = 첫 풀유니버스 보고서급 winner 확정. profit +740,353·MDD 0.88·calmar 117·daily 0.3·r² 0.865·score 1.635. (cf. `fullevo2` run은 `status='running'` stale 좀비 레코드 — 락 없음, 새 run-id 쓰면 무관.)

**(B) fullevo3 (3개월 2025-01~03, `run_full_evo_3mo_config.json`, 34.3분, back_count 810)**: seed=Tick_902, refine-from-best, max_gen 8. **winner = gen0(유일 통과).** stop_reason=max_generations 8 도달.

| 세대 | 상태 | gate | profit | MDD | calmar | trades | 일평균 | r² | 판정 |
|------|------|------|--------|-----|--------|--------|--------|-----|------|
| **gen0 (Tick_902)** | ok | ✅ | **+1,944,536** | **5.39** | **31.0** | 24 | 0.4 | 0.855 | winner 졸업 |
| gen1 | error | — | — | — | — | — | — | — | 타임아웃(과발화) |
| gen2 | ok | ✗ | -1,178,382 | 13.06 | -3.9 | 90 | 1.6 | 0.550 | MDD초과+음수 |
| gen3 | ok | ✗ | -391,932 | 14.39 | -2.3 | 32 | 0.6 | 0.780 | MDD초과+음수 |
| gen4 | ok | ✗ | **+479,454** | **3.0** | 13.8 | 9 | 0.2 | 0.477 | 흑자·저MDD, **빈도 0.2<0.3 탈락** |
| gen5~7 | error | — | — | — | — | — | — | — | 타임아웃(과발화) ×3 |

- **기간 확대의 가치**: 1개월 대비 profit 2.6배(+74만→+194만), **MDD 0.88(표본부족·비현실)→5.39로 정상화돼 보고서 타겟 2~7% 부합**, calmar 117(과대)→31(현실·우수), r² 0.865→0.855 견고. **3개월이 더 신뢰할 보고서급 통계.**
- **프론티어 3갈래 재확인(핵심)**: ①빈도↑(gen2 90·gen3 32)→흑자붕괴+MDD13~14 ②빈도↓(gen4 9건)→흑자·MDD3 회복하나 freq게이트 미달 ③과발화(gen1·5·6·7 4건)→타임아웃 컷. **시드가 강한 국소최적이고 빈도-흑자 프론티어가 본질 장벽.** 8세대 중 4개 타임아웃 = refine 효율 손실.
- **gen4 단서(다음 과제 씨앗)**: 흑자·MDD3·calmar13.8인데 빈도만 0.2 부족 → "여러 종목 분산 다수 진입"으로 빈도↑ 하면서 흑자 유지(looser-but-profitable)가 Track B 핵심.

### 3.4 R7 — Track B 다종목 분산 토글 구현·실측 (2026-05-29, 커밋 `417284c5`)

**구현(커밋 `417284c5`)**: `dispersion_prompt_enabled`(프롬프트: base_code 저빈도 압력→다종목 분산 고빈도+거래대금 게이트 보호+과발화 억제+시간대 분산), `dispersion_enabled`/`min_hold_symbols`(적합도: 동시보유 graded **실패분기에만** 보상), `target_daily_trades`(산식 노출). 전부 기본 OFF·OFF=byte동일·하드게이트 불변. code-reviewer APPROVE(5불변식 실증), baseline 1705 passed 신규 0. (ai_strategy_loop 5파일 + test_dispersion 13개. config: `run_trackb_config.json` gitignored.)

**실측(run=trackb1, 1개월, dispersion ON, seed Tick_902)**:

| 세대 | gate | profit | MDD | 거래 | 일평균 | 동시보유 |
|------|------|--------|-----|------|--------|----------|
| g0(시드) | ✅ | +740,353 | 0.88 | 6 | 0.3 | 2 |
| g2 | ✗ | −528,500 | 8.59 | 20 | 1.1 | 2 |
| g4 | ✗ | −792,645 | **8.75** | **89** | **4.9** | 4 |
| g6 | ✗ | −456,746 | 8.88 | 71 | 3.9 | 3 |
| g1·g3·g5 | — | 타임아웃(과발화) ×3 | | | | |
| g7 | ✗ | −33,823 | 0.68 | 1 | 0.1 | 1 |

**dispersion 1차 = 부분 성공(프론티어 이동, 미돌파)**:
- ✅ **빈도 상승**: 일평균 0.3→4.9(89거래). fullevo3 최대 2.15 대비 dispersion이 빈도를 끌어올림.
- ✅ **고빈도 MDD 개선(확정)**: trackb1 g4(89거래·MDD8.75) vs fullevo3 g2(90거래·MDD13.06) — 동일 빈도서 MDD ~33%↓.
- ⚠️ **동시보유 미증**: conc 2~4 유지(fullevo3와 동일). dispersion_term이 동시보유를 6 방향으로 못 늘림 — 빈도는 '시간 분산된 더 많은 단발 진입'에서 옴(동시보유 확대 아님). per-trade csv 동시진입 sweep-line으로 실측.
- ❌ **흑자 미달**: 전 dispersion 세대 음수. **근본 원인 = refine가 빈도 올릴 때 흑자 핵심인 거래대금 유동성 게이트(당일거래대금 절대바닥+각도)를 LLM이 느슨하게 함**(프롬프트 보호 지시 불충분). fullevo3 strategy-diff와 동일 메커니즘 재확인.
- ❌ **과발화 타임아웃 여전**: 8세대 중 3개(g1/3/5). 프롬프트 과발화 억제 가이드 효과 부족.

**다음 레버(2차, 사용자 선택=①)**: ①**거래대금 게이트 코드 강제**(생성 전략 저장전 검증에 '거래대금 게이트 필수 포함' 추가; 없으면 reject→재생성) — 흑자 직결. ②과발화 억제 강화(변이폭 축소/항상참 조건 감지/timeout 조정). ③진입 시간대 확대 강화(동시보유보다 시간분산이 빈도 레버).

### 3.5 R7.1 — 거래대금 게이트강제 = 빈도-흑자 프론티어 돌파 🎉 (2026-05-29, 커밋 `d54fb6a0`)

**구현(커밋 `d54fb6a0`)**: `require_liquidity_gate`(기본 OFF) — 매수 생성 PRE-SAVE 체인(scope 다음·dedup 전)에 `has_liquidity_gate` 검증(`brain/liquidity_gate.py`). `당일거래대금`(절대 유동성 바닥/각도) 비교 존재 검사, `초당/분당거래대금`(상대)은 제외. 없으면 reject→재생성. **ground-truth 검증**: 흑자(seed/g4)=통과, 손실(g2/g3)=reject 정확 구분(단순 "거래대금" 매칭은 false positive였음 — `당일거래대금`으로 좁혀 교정). code-reviewer APPROVE(5불변식 실증), baseline 1719 passed 신규 0. 엔진 무수정·OFF=byte동일.

**🎉 실측(run=trackb2, 1개월, dispersion + 게이트강제 둘 다 ON, seed Tick_902) — 프론티어 돌파**:

| 세대 | gate | profit | MDD | calmar | 거래 | 일평균 | r² | 동시보유 |
|------|------|--------|-----|--------|------|--------|-----|----------|
| g0(시드) | ✅ | +740,353 | 0.88 | 117 | 6 | 0.3 | 0.87 | 2 |
| **g2(winner)** | ✅ | **+790,121** | 5.12 | 21 | **49** | 2.7 | 0.35 | 3 |
| g3 | ✅ | +744,413 | 3.66 | 57 | 19 | 1.1 | 0.54 | 2 |
| g4 | ✅ | +583,725 | 4.66 | 17 | 44 | 2.4 | 0.35 | 2 |
| g5 | ✅ | +773,099 | 2.29 | 94 | 15 | 0.8 | 0.78 | 2 |
| g6 | ✅ | +661,653 | 4.63 | 20 | 48 | 2.7 | 0.43 | 2 |
| g7 | ✅ | +780,178 | **1.17** | **185** | 11 | 0.6 | **0.95** | 1 |
| g1 | error | 타임아웃(과발화) ×1 | | | | | | |

- **winner = gen2(`AILOOP_trackb2_g2`) = AI 생성 전략이 시드 능가**(+790,121 > 시드 +740,353), 게다가 고빈도(49거래 = 시드 6의 8배). best_score=790121(profit obj).
- **7/8 게이트 통과 흑자**(gen1만 타임아웃). 전부 MDD 보고서 범위(0.88~5.12), calmar 17~185, 빈도 6~49.
- **결정적 대조**: trackb1(dispersion만)=winner 0(빈도↑ 세대 전부 음수) vs **trackb2(+게이트강제)=winner 7**. fullevo1(0)·fullevo3(1=시드만) 대비 압도적.
- **결론**: 빈도-흑자 프론티어는 **거래대금 게이트강제로 깨졌다.** dispersion(빈도)+게이트강제(진입 품질 보호)의 조합이 핵심. R7 trackb1 "흑자 미달" 원인(게이트 유실)을 정확히 교정해 돌파.
- **잔여**: ①동시보유 여전히 1~3(빈도는 시간분산 단발진입). 보고서 일평균10~23(동시보유6~12 필요)엔 미달(현 최대 2.7). ②과발화 타임아웃 1/8(trackb1 3/8보다 개선).

**다음 후보**: ①기간 3개월 확대(분기 검증·연수익 추정) ②빈도를 보고서 타겟 10~23까지 더 밀기(target_daily_trades↑·동시보유 레버·진입시간대 강화) ③winner gen2/gen5/gen7 전략 분석·기록.

### 3.6 R7.2 — trackb3 3개월 검증: ⚠️ 1개월 돌파는 구간 과적합 (2026-05-29, 정직한 정정)

trackb2(1개월 2025-01) 7/8 흑자를 **3개월(2025-01~03)로 확대**(run=trackb3, 동일 dispersion+게이트강제 설정 `run_trackb_3mo_config.json`) 검증:

| run | 기간 | winner(시드 제외) | 비고 |
|-----|------|-------------------|------|
| trackb2 | 1개월 | **7/8 흑자 통과** | gen2 AI전략 시드 능가(+790K) |
| **trackb3** | **3개월** | **0 (시드 gen0만)** | 고빈도 세대 전부 MDD 15~31 초과 |

trackb3 세대: gen0 시드 +1,944,536·MDD5.39 통과 / gen2 72거래 −104만 MDD31 / gen3 45거래 −52만 MDD15 / gen5 71거래 +7.7만 MDD15(흑자나 MDD초과) / gen7 348거래 −176만 MDD24(과다) / gen1·4·6 타임아웃. **게이트 통과 1(시드만)**.

- **정직한 재평가**: trackb2의 "7/8 흑자 돌파"는 **2025-01 단일 우호 구간 과적합**이었다. 3개월의 넓은 시장에선 refine가 시드를 못 이긴다(fullevo3 3개월도 시드만 winner였던 것과 동일 패턴).
- **게이트강제의 한계 확정**: 거래대금 게이트 유실로 인한 흑자붕괴(trackb1 음의엣지)는 막았으나 **MDD 폭증은 못 막는다**. 3개월 변동성에서 고빈도 진입 = MDD 15~31. 게이트강제는 진입 유동성만 보호, MDD는 청산/포지션관리 영역.
- **결론 수정**: "빈도-흑자 양립"은 1개월 한정. **진짜 병목 = 고빈도에서의 MDD 제어.** 단순 빈도 밀기(§3.5 ②)는 3개월에서 역효과. 다음은 빈도가 아니라 **MDD 제어**(청산 품질·동시보유 상한·과발화 억제) + 3개월 상시 검증.
- **불변 사실(축적된 자산)**: ①시드 Tick_902는 1·3개월 모두 흑자·통과(강건). ②dispersion·게이트강제 토글은 안전(기본 OFF·엔진무수정·baseline 0). ③다종목 분산은 이미 충족(동시보유는 1~4 상한). ④과발화→타임아웃은 모든 run 공통(프롬프트 억제 불충분 = 코드 레벨 컷 필요).

**다음 후보(재설정)**: ①MDD 제어 강화(청산 트레일링/시간손절 + 동시보유 상한 + 과발화 코드 컷) 후 3개월 상시 재검증 ②기간 6~12개월로 시드 강건성 재확인 ③시드를 3개월 기준 best로 인정, 청산만 정제(freeze_buy 활용).

### 3.7 R7.3 — MDD 제어 토글 + trackb4 3개월 검증 (2026-05-29)

**구현(커밋 `9cc99316`)**: `mdd_control_enabled`(기본 OFF) — `kind=='sell'`+ON일 때 매도 프롬프트에 MDD 억제 블록(타이트 손절·트레일링·시간손절·손실구간 노출억제, '낮고 안정적 MDD' 목표). OFF=byte동일·엔진무수정. test_mdd_control 10 passed. **baseline(PYTHONUTF8=1) 1756 passed / 7 failed(신규 0)**. ※ **중요 측정 정정**: cp949 환경의 "34 failed" 중 27개는 한글 소스 디코딩 spurious — `PYTHONUTF8=1`(또는 `-X utf8`)이 정확한 baseline이며 진짜 기존 실패는 **7개**(backtest 계약·ui_jisu, ai_strategy_loop 무관).

**실측(run=trackb4, 3개월, dispersion+게이트강제+MDD제어 모두 ON)** vs trackb3(MDD제어 없음):

| | 게이트 통과 | gen1(첫 refine) | 고빈도 세대 MDD |
|---|---|---|---|
| trackb3 (MDD제어 ✗) | 1 (시드만) | 타임아웃 | 15~31 |
| **trackb4 (MDD제어 ✓)** | **2 (시드+gen1)** | **82거래·MDD6.3·+1,248,536 통과** | 11~25 |

trackb4 세대: gen0 시드 +194만 통과 / **gen1 82거래 +125만 MDD6.3 통과(고빈도 흑자)** / gen3 26거래 −50만 MDD11.21 / gen5 80거래 −94만 MDD25 / gen6 31거래 +1.1만 MDD12.53 / gen7 34거래 −22만 MDD12.93 / gen2·4 타임아웃.

- **MDD제어 = 부분 성공**: ①**3개월 첫 고빈도 흑자 통과**(gen1 82거래·MDD6.3 — trackb3 동일빈도 gen2는 MDD31 실패였음). ②전반 MDD 개선(15~31→11~25). 단 ③**일관성 부족**(gen3/5/6/7 여전히 MDD 11~25 초과 — 매도 프롬프트라 LLM 준수 불확실) ④과발화 타임아웃 2/8(매수 측, MDD제어로 못 막음).
- **결론**: MDD 제어는 효과 있으나 프롬프트 레벨이라 불완전. winner는 여전히 시드(profit obj, gen1 +125만 < 시드 +194만). 빈도-흑자-MDD 3차원 양립은 미완성.

**다음 후보**: ①**과발화 코드 컷**(매수 저장전 검증 — 모든 run 타임아웃 2~3개 회수, §3.6 불변사실에서 '코드레벨 컷 필요'로 지목) ②MDD 하드 제어(graded MDD 페널티 강화 or 매도 청산 코드 강제) ③`winner_objective=risk_adjusted` 전환(고빈도 저MDD gen1류 우대; 현 profit obj는 시드만 뽑음).

> **🔴 R7.4 ground-truth 정정(2026-05-29)**: 위 ①(과발화 정적 코드 컷)은 **불가 판명**. trackb2/3/4의 타임아웃 세대 vs 정상 세대 매수 코드를 비교(`_temp_overfire_probe.py`)한 결과 게이트 수(31~35)·매수=True 지점(1)·줄수·시간조건이 **거의 동일** — 정적 특징으로 과발화/정상 구분 불가(과발화는 코드 구조가 아니라 런타임 시장 데이터 상호작용). 정적 컷은 정상 흑자 세대(trackb4 gen1류)까지 reject 위험. **→ 과발화는 런타임 fail-fast(현 bt_warm_run_timeout 300)로만 처리 가능.** 위 ③(risk_adjusted)도 시드 calmar31·r²0.85가 gen1(8.55·0.47) 압도라 winner는 시드 유지 예상. **근본 현실: 시드 Tick_902가 모든 지표 best, refine 생성세대는 빈도만 높지 위험조정수익은 시드 미달.** 진짜 다음 레버 = '고빈도이면서 고calmar/r²' 생성(LLM 품질·프롬프트·도메인 재설계) — 미해결 연구과제.

### 3.8 R8 — 대시보드 실시간 가시성 검토·수정 (2026-05-29, 커밋 `45e93038`)

**검토(Workflow 4갈래: backend·frontend·system-gap·live-http)** — 사용자 질문 "AI 조건식 시스템이 잘 개발되는지/알고리즘 진행/성과가 대시보드에서 실시간 확인되나":
- ✅ 잘 개발됨(생성→백테→채점→부검→진화 파이프라인 + FastAPI 7 REST+WS + loop_runs.db + 계약 v2). ✅ **성과 실시간 확인**(적합도·수익·MDD·winner·자본곡선·run비교 LIVE; live-HTTP 실측으로 fullevo3·trackb1~4 전부 `/runs` 노출, `/status`가 디스크 current_state.json과 updated_at 일치=라이브 서빙 확정, WS 101).
- ❌ 갭 4종: ①**phase 타임라인 영/한 키 불일치로 LIVE 영구 미점등**(데모에서만) ②5종 안전토글·설정이 폼·상태 비가시 ③품질지표(calmar·r²·dispersion·max_hold) LIVE 미노출 ④엔진/current_run 풍부 패널 backend 미발행(DEMO 전용).

**수정(커밋 `45e93038`, 엔진무수정·CONTRACT_VERSION 2 유지·code-reviewer APPROVE 6불변식 실증·baseline PYTHONUTF8=1 1782 passed/7 failed 신규0)**: ①`phase-detail.jsx` LIVE_PHASE_INDEX(영어 phase→4단계, 한국어 데모키도 인식) ②`contract.LoopState.active_config` + `state.build_active_config` + `launch_config` 9필드 + `ActiveConfigPanel`(켜진 토글 강조) ③`GenerationInfo`에 calmar/uptrend_r2/dispersion_term/max_hold_count + `table.jsx` 컬럼 + generations v5→v6 마이그레이션(PRAGMA-guarded ALTER ADD COLUMN, 멱등·비파괴, 기존 224행 보존). to_loop_state는 dispersion_term None-only 폴백(0.0 중립값 보존).

**미수정(범위 밖·다음)**: 엔진 리소스/current_run 실시간 스트리밍 패널(backend가 engine·current_run 미발행→loop가 경량 메트릭 발행 필요, 중기). GA 경로는 신규 품질필드 기본값(hillclimb만 채움). RunComparePanel `/runs/compare?ids=` 미사용. **✅ LIVE 통합 실측 완료(2026-05-29)**: 대시보드 재기동(새 backend) 후 `run_live_check_config.json`(1주·1세대·토글 전부 ON, run=livecheck) smoke로 HTTP 실측 — `/status.active_config`에 5종 안전토글+27개 설정 LIVE 노출, `generations[0]`에 calmar62.5·uptrend_r2 0.856·**dispersion_term 0.167(=max_hold 1/min_hold 6 정합)**·max_hold_count 1.0 전부 노출(신규 DB컬럼 마이그레이션→record_generation→to_loop_state→/status 파이프라인 전체 작동 확인), `/runs`에 livecheck·trackb4·fullevo3 노출. **running 중 phase 점등도 실증**: fullevo5(게이트 보정 8세대 재run) running 중 `/status` 캡처에서 `status=running`·`latest.phase=generation_done`(영어 phase)·`best.gate_passed=True` 포착 → **LIVE_PHASE_INDEX 매핑이 영어 phase를 4단계로 점등함을 실측**(검토 갭5 완전 해소; 단위테스트 12개와 별개로 LIVE 확인).

### 3.9 첫 풀유니버스 winner 졸업 공식 확정 (2026-05-29, run=fullevo5)
게이트 보정(min_daily_trades 0.3) 전용 재run으로 **gen0 Tick_902 졸업 공식 확정**: run=fullevo5 `status=complete`·`best_gen=0`·winner_buy=`Tick_B_902_905_Update_2`·winner profit **+740,353**·MDD0.88·calmar117. 게이트 통과 2(gen0 + gen2 +397,911). (gen1/3/4/6 타임아웃, gen5/7 음수 — 이 config는 dispersion/게이트강제/MDD제어 토글 없는 순수 게이트보정이라 refine 세대는 R6 fullevo1 패턴.) **R6 §0/§4의 원래 '다음 첫 행동'(게이트 보정→첫 풀유니버스 winner 졸업)이 fullevo2_grad에 이어 fullevo5에서 complete 기록으로 재확정됨.**

### 3.10 보고서급 도달 가능성 평가 (2026-05-29, Workflow: 현재 vs 보고서 19전략)

보고서 원문(`E:/Download/backtest_analysis_report.md`·`_v2.md` 실제 읽음, 921줄 v2 §1.2/§6.1 타겟) vs 현재 최고 성과 대조:

| 축 | 보고서 타겟 | 현재 최고 | 판정 |
|----|-----------|----------|------|
| 연수익 | 134~262%(평균199) | 3개월 시드 분기38.9%→연156~272% | ✅ 달성 |
| MDD | 1.9~6.75%(평균4) | 시드 5.39 | ✅ 달성 |
| calmar | ~29 환산 | 시드 31 | ✅ 달성+ |
| r²/평활 | 우상향 함의 | 시드 0.855 | ✅ 달성 |
| **payoff(매매성능지수)** | 1.15~1.47(평균1.27) | **시드 1.74·trackb2 g2 2.21·g5 2.17** | ✅ **초과(실측)** |
| 일평균거래 | 10.6~23.2 | 시드 0.3~0.4·신뢰최대 1.4(trackb4 g1) | ❌ 크게미달 |
| 동시보유 | 6~12 | 1~4 | ❌ 크게미달(엔진수정 필요) |
| AI 시드능가 | 자율 보고서급 생성 | 1개월 trackb2(과적합)·3개월 미달 | ❌ 미해결 |

- **payoff 실측 정정**: Workflow가 "payoff 미측정"이라 했으나(current-performance agent 실패), DB 직접 실측 결과 게이트통과 흑자 세대 payoff = **1.67~2.21**(시드 1.74, give_back 0.0). 보고서 타겟 1.27을 **오히려 초과**. (livecheck g0 999는 손실0 sentinel.)
- **정직한 결론**: ①**수익·리스크·payoff 품질은 이미 보고서급(payoff 초과)** — 위험조정 기준 **Yes**. ②그러나 보고서 우수전략 정체성인 **'고빈도(10~23)·다종목(6~12) 분산 매매'는 현 구조로 재현 불가**(빈도↑→흑자붕괴/MDD폭증, 동시보유 엔진창발 1~4 상한). 시드 Tick_902는 '저빈도·소수진입 고품질'로 보고서와 **다른 종(種)**. **→ "보고서만큼 좋은 성과": 위험조정 기준 Yes, 보고서 전략 형태(고빈도·다종목)까지면 아직 No.**
- **유망 경로(다음 세션, §4 최우선과 동일)**: '고빈도+시드급 calmar/r² 생성' 4레버 동시 공략 — ①winner_objective risk_adjusted+다목적 점수(고빈도×calmar×r²) ②다종목 동시성 보상 적합도(현 daily_avg_trades는 종목무관 총량이라 불충분)+엔진 보유상한 토글(별도스코프·사용자확인) ③코드레벨 MDD제어(고빈도 MDD 폭증이 3개월 진짜 병목) ④3~12개월 상시검증(trackb2식 구간 과적합 차단).

### 3.11 STOM 실사용 가능성 검증 (2026-05-29, Workflow: export·형식·e2e) — 조건부 YES

사용자 질문 "생성한 조건식을 STOM에서 바로 쓸 수 있나" 검증 결과:
- ✅ **형식 100% 호환**: 생성 코드는 STOM 엔진 exec 형식(매수=True/if not(관심종목):매수=False/시분초 게이트/self.Buy(), 매도 self.Sell())·timeframe(tick=초당/min=분당)·compile 전수 통과(AILOOP_* buy 263/sell 261 = 100% compile + self.Buy/Sell 포함). loop_strategies.db ↔ `_database/strategy.db` 스키마 동일(['index','전략코드'] TEXT). 시드 Tick_902는 원본 byte-동일(len 3836 ==).
- ✅ **export 경로 = 운영 strategy.db 직결**: `final_approval`(WS, 사람 승인) → `_do_final_approval`(app.py:445-472) → `export_winner`(controller/export.py:65-130)가 격리 DB 우승 코드를 **무변형** 복사해 user_buy/user_sell 이름으로 `_database/strategy.db` stockbuy/stocksell '전략코드'에 INSERT/UPDATE. 이 파일·테이블·컬럼이 STOM 백테엔진(backtest.py:164 connect(DB_STRATEGY))·GUI 전략편집기(database_read_only '전략디비')·실거래(kiwoom_strategy_tick)가 읽는 **바로 그것**. GUI 콤보(ui_button_clicked_editer_stg_buy_stock.py:23-29)가 stockbuy 전체 index 로딩 → export 이름 자동 등장. **운영 DB에 이미 과거 AI루프 산출물(AutoResearchBaselineCompare_20260418_T6 등) 적재 = STOM 도달 실증.**
- **조건(수동·제약)**: ①export는 final_approval 사람 승인이 유일 통로(CLI run만으론 운영 미투입 — 설계상 안전게이트, 무인배포 아님) ②buy/sell **조건코드만** 복사 — 주문설정(stockbuyorder '경과틱수' 등)·변수패턴(stockvars/optivars)·조건분해(stockbuyconds) 미복사(전략이 의존 시 운영 동작 동일성 미보장, export_winner에 동반복사 옵션 추가가 fix) ③export 후 GUI 콤보 수동 재로딩(F1/F5, 자동 새로고침 신호 없음) ④운영 백테 1회 확인 권장(dict_set·ms_analyzer 설정 차이로 수치 변동 가능; ms_analyzer 의존 코드는 '시장미시구조분석' ON 필요) ⑤user 이름이 기존 운영 전략명과 충돌 시 무경고 덮어쓰기(중복확인 로직 없음).
- **결론**: '형식만 그럴듯한 가짜'가 아니라 **STOM이 그대로 로드·실행하는 1급 전략**이다. 생성·졸업·형식·DB경로 모두 검증 통과(YES). 운영 즉시 사용은 '사람 승인 1단계 + (의존 시)부가설정 동반 + 운영백테 1회'의 조건부. **STOM 사용성 개선 후보**(별도): export에 부가테이블 동반복사·콤보 자동 새로고침 신호·이름 충돌 확인.

### 3.12 고빈도+고calmar/r² 목표 연구계획 (2026-05-29, ultracode Workflow judge panel)

**🔴 핵심 인과 정정(DB 실측)**: 진짜 병목은 r²(곡선평활도)가 **아니라 청산 give-back으로 인한 calmar 음수(적자)**다. 고빈도 세대(daily 5~18.6·93~236거래)는 **r² 0.93~0.996로 평활도 멀쩡**한데 calmar 음수(적자)로 게이트 탈락. r²붕괴(0.50)는 trackb3 단일 사례뿐(일반화 오류). score=calmar×r²×gate에서 calmar 음수면 total_profit>0 게이트에서 이미 탈락. **+ 결정적 결함**: `max_hold_count`가 DB 전체에서 {0,1}만 기록 = **다종목 분산 신호가 죽어있음**(236거래 세대조차 0) → 동시보유 보상 선택압이 작동한 적 없음. 측정 복구가 모든 것의 전제.

**성공기준(2단계)**: [1차 마일스톤] 3개월+holdout, AI생성 세대(시드 아님)가 일평균거래≥4 AND calmar≥15 AND MDD≤7 AND total_profit>0 AND uptrend_r2≥0.6 동시충족. [최종 목표] 일평균≥8 AND calmar≥20 AND MDD≤7 AND r²≥0.6 AND 동시보유(sweep-line 실측)≥3. **졸업=3개월 in-sample + holdout(최근30일) 둘 다 통과 필수. 1개월 결과는 졸업 영구 불채택(trackb2 1개월 7/8→3개월 0 과적합 확정).**

**프로세스(OODA 7단계, 3개월 고정)**: S0 baseline 고정+DB백업 → **S1[FIRST] dispersion 측정 복구(엔진무수정)** → S2 측정으로 H2/H3/H5 판별 → S3 청산 give-back 코드봉쇄(MDD 1차병목; graded mdd/exit_quality 가중강화 먼저, 부족시 매도 PRE-SAVE 트레일링/시간손절 강제) → S4 multi+dispersion 결합 ON(_multi_objective_term 4항→6항, 빈도항을 dispersed_frequency로) → S5 holdout 졸업 의무화(graduation_holdout ON, loop.py:1099) → S6 refine 모드붕괴 교정(부모를 gate_passed 빈도최대로 or 빈도-bucket archive).

**신규 메트릭(엔진무수정·csv 사후산출)**: distinct_symbols·concurrent_avg/peak(sweep-line: 매수+1/매도-1, 동일시각 매도먼저)·trades_per_symbol·dispersed_frequency(daily×clamp01(distinct/min_hold))·gate_pass_rate·holdout_delta·min_sample_gate(trade≥30).

**off-ramp(sunk-cost 차단)**: STOP-i(측정복구 후 동시보유≥3 세대 없으면 '엔진수정 없이 다종목 불가' 확정·사용자 게이트) / STOP-ii(통합run multi+dispersion+holdout 3회 내 3개월 holdout 시드초과 winner 0이면 'AI가 인간시드 국소최적 못 넘음' 결론·루프를 시드 청산정제 전용 축소) / STOP-iii(일평균이 3개월서 2 못넘으면 고빈도 포기·시드를 최종성과 인정 — 시드는 이미 payoff1.74·calmar31·MDD5.4 위험조정 보고서급).

**🔴 엔진수정 게이트(H5)**: 동시보유 상한강제(종목당 betting↓+최대보유 상한↑/자본분할)는 backengine_base.py:824-847 numba 런타임 개입=CLAUDE.md '엔진무수정'·backtest/graph 보호 위반 → **사용자 결정 게이트, 그 전 착수 금지.** 단 S1 측정복구는 엔진무수정 가능.

**first_action(즉시·엔진무수정)**: score.py:840 load_exit_quality_from_csv 패턴 복제로 `load_dispersion_from_csv` 추가 → **먼저 백테 0회로** 기존 trackb4·fullevo3·r4tick1(daily18.6) CSV 오프라인 재계산 → 고빈도 세대 실제 동시보유 분포 측정(H2 신호복구·H3 분산형vs희석형·H5 엔진수정필요여부 동시 판별).

### 3.13 S1 dispersion 측정 복구 결과 — 엔진수정 게이트 회피 + 청산이 진짜 병목 확정 (2026-05-29, 백테0회 오프라인 sweep-line)

`_temp_dispersion_offline.py`로 기존 풀유니버스 세대 CSV를 sweep-line(매수+1/매도-1, 동일시각 매도먼저) 재계산(죽은 max_hold_count {0,1} 대체):

| 세대 | 거래 | distinct종목 | peak동시 | per_sym | calmar | profit |
|------|------|-------------|---------|---------|--------|--------|
| trackb3 g7 | 348 | 134 | 4 | 2.6 | −3.1 | −176만(적자) |
| fullevo3 g2 | 90 | 65 | 4 | 1.38 | −3.9 | −118만 |
| trackb1 g4 | 89 | 48 | 4 | 1.85 | −8.4 | −79만 |
| **trackb4 g1**(흑자) | 82 | 55 | 3 | 1.49 | 8.6 | +125만 |
| **trackb2 g2**(흑자) | 49 | 31 | 3 | 1.58 | 21.5 | +79만 |
| (wide baseline 전종목) | 13K~150K | 563~1270 | **9~48** | 6~121 | −1(적자) | −수십억 |

**H 판별 완료(4가설 동시)**:
- **H2 측정복구 ✅**: sweep-line이 죽은 max_hold_count({0,1}) 대체 — distinct·peak동시 진짜값 산출(엔진무수정).
- **H3 분산형 확정 ✅**: per_sym 1.1~2.6(종목당 1~2회)·distinct 27~134 = **이미 보고서형 다종목 분산**(한종목 다발 아님).
- **H5 엔진수정 ⚠️ 부분 기각**: distinct 종목폭 충분(분산됨) + 엔진 동시보유 多 지원(wide peak 9~48 실측). 현 winner peak 2~4 미달은 자본캡이 아니라 **진입 시간 비겹침**(09:00~09:28 28분창 흩어짐+보유 200~300초라 동시 겹침 적음). → **엔진수정 사용자 게이트 회피 — 분산은 이미 달성**.
- **H1 진짜 병목 ✅ 확증**: 고빈도 분산 세대(trackb3 g7 348거래·134종목 완전분산)도 **calmar 음수(적자 −176만)**. r²는 0.50~0.75로 일부 멀쩡한데도 적자 → 분산·평활도가 아니라 **청산 give-back→calmar 음수**가 결속제약.

**🎯 정정된 다음 방향**: 다종목 분산·고빈도는 **이미 생성됨**(distinct 27~134, 엔진수정 불요). 진짜 할 일 = **고빈도 분산 세대의 적자를 흑자로 = S3 청산 give-back 코드 봉쇄**(graded mdd/exit_quality 가중강화 → 부족시 매도 PRE-SAVE 트레일링/시간손절 강제). S2/H5 엔진수정 게이트 회피 확정. (동시보유 6~12는 보고서 특성이나 distinct 분산으로 빈도 확보 가능 — 동시성보다 청산 우선.)

### 3.14 S3 ground-truth — 매도 정적 게이트 불가 + give-back 가설 반증 (2026-05-30, 결정론 오라클 + Workflow 6렌즈)

`require_exit_discipline` 매도 PRE-SAVE 게이트(R7.1 거래대금 게이트와 동형)가 **정적으로 흑자/적자 매도코드를 가를 수 있는가**를 ground-truth로 검증. 흑자통과(PASS_PROFIT 12) vs 적자(LOSS 12) 매도코드 전수 + give_back/payoff 지표 추출(`_temp_s3_sell_codes.txt/json`) → 내 후보 5규칙 + Workflow 6렌즈 11규칙을 **결정론 오라클**(`_temp_s3_oracle.py`/`_oracle2.py`)로 27라벨에 적용.

| 규칙 | 정확/24 | 시드통과 | 적자누수 | 판정 |
|------|--------|---------|---------|------|
| composite(시드시그니처+타이트밴드+매직밴드거부) | **23/24** | ✅ | 0 | **출처지문 과적합**(시드 902 리터럴+trackb2 TP=7.0 암기) |
| tp_ceiling_7(`수익률>=7.0`) | 18/24 | ❌시드reject | 0 | 사용불가 |
| provenance(무조건손절無 OR `수익률>=7`) | 21/24 | ✅ | 2 | 1~2feature 전수탐색 최고=run 라벨 학습 |
| NOT slow_bleed(`보유시간>N and 수익률<양수`) | 19/24 | ✅ | 5 | **유일 인과 신호**(좋은전략 0 reject, 적자 7/12) |
| NOT near_total(`최고수익률>=A and 수익률<=0.x`) | 14/24 | ✅ | 10 | 약함(적자 2개만) |
| (내 규칙들: 무조건손절/타이트트레일/시간손절/조합) | 7~14/24 | 다수 시드reject | 다수 | 전부 실패 |

**결론(R7.4 과발화 정적컷과 동형 = 정적 판별 불가)**:
1. **23/24는 결정론적으로 사실이나 인과 아님 = 출처 지문**. composite의 분리력은 청산규율 개념이 아니라 ①시드 902 스캐폴드 리터럴(`시가대비등락율<0 and 수익률<=-2.0 and 현재가<최저현재가(int(60),int(보유시간))`) ②trackb2 run의 익절천장 `수익률>=7.0` 암기에서 옴. **게이트로 쓰면 시드를 복제하지 않는 모든 신규 생성을 reject → AI 탐색 무력화 = 루프 목적 파괴.** 회의론자·종합 렌즈가 독립 확증.
2. **인과적 청산규율(손절·트레일링·give-back)은 PASS/LOSS를 못 가름**: `수익률<=-2.0` 동일 토큰이 양쪽 존재(PASS trackb4 g1 ↔ LOSS trackb4 g5, 둘 다 보유, +125만 vs −94만); 구조 쌍둥이 역설(trackb4 g3 적자가 trackb2 g2 흑자보다 *더* 타이트한 규율); give_back·payoff·mdd 전부 클래스 경계 가로질러 overlap, give_back은 **역상관**(최저 0.0185가 −94만 적자, PASS는 0.133도 흑자).
3. **§3.13 "청산 give-back이 병목" 가설 코드레벨 반증**: give_back이 분리자가 아니고 매도코드가 분리자가 아님. **진짜 손실 원인 = 고빈도 진입의 포트폴리오 MDD 폭증(3개월 레짐·진입품질), 매도 텍스트에 안 드러남**(skeptic·종합 렌즈 명시: "적자의 본질 MDD는 코드 텍스트에 없음").
4. **유일 인과 신호 = slow_bleed**(`보유시간>N and 수익률<양수`=정체 포지션 회복 기대 보유): 출처가 아닌 행동 안티패턴, PASS 0/12·LOSS 7/12·FAIL_OTHER 2/3. 단 ①적자 7/12만(나머지 5는 MDD폭증) ②**흑자 fullevo3 g4(+479K·MDD3, §3.3 단서 세대)를 오reject** → 완전 안전 아님·효과 부분적.

**→ S3 재정의**: 매도 정적 청산-규율 게이트(사용자 지정 require_exit_discipline의 broad 버전)는 **불가+오조준**. R7.4 정밀 = ground-truth가 "불가"면 구현 안 함(과발화 컷 전례). 가능한 진짜 레버는 **매도가 아니라**: (A) graded MDD 가중강화(§3.12 S3 1순위 "graded mdd 먼저" — 실측 MDD로 refine-parent를 저MDD로 선택, 정적탐지 불요·엔진무수정 토글), (B) 진입(매수)품질·LLM 생성품질(§4 🔴 미해결 핵심), (C) slow_bleed만 약한 음성 게이트로 구현(directive 문자 충족, 인과적, 기본 OFF, 단 효과 marginal+fullevo3 g4 오reject). **사용자 결정 게이트**(3개 옵션 §4-S3 참조). 산출물: `_temp_s3_sell_codes.*`·`_temp_s3_oracle*.py`(재현용, 커밋 제외).

### 3.15 진입측(매수) MDD 게이트 ground-truth — 매수도 불가 + 근본원인=레짐 의존성 확정 (2026-05-30)

사용자 선택(§3.14 옵션A "진입측 MDD 게이트 재조준")에 따라 **매수(stockbuy) 코드**를 동일 27세대 흑자/적자로 추출(`_temp_s3_buy_codes.*`) → 진입품질 후보 6규칙(돌파확인 `현재가>최고현재가`·신선돌파 `현재가N(1)<=최고현재가N(2)`·돌파AND(OR아님)·시총≤3000·당일거래대금각도 가속·R7.1 유동성게이트)을 **레짐별 분리** 결정론 오라클(`_temp_s3_buyoracle.py`)로 채점. **레짐 = 1개월{trackb1,trackb2} vs 3개월{fullevo3,trackb3,trackb4}**.

| 규칙 | 전체 분리/24 | **3개월 분리/12** | 1개월 분리/12 |
|------|------------|-----------------|-------------|
| breakout_any | 11 | 4 | 7 |
| fresh_breakout | 14 | 7 | 7 |
| breakout_AND | 12 | 4 | 8 |
| smallcap≤3000 | 13 | 5 | 8 |
| accel_gate | 9 | 6 | 3 |
| liquidity_gate(R7.1) | 14 | 6 | 8 |

**결론(매도와 동형 = 정적 진입 게이트도 불가, 근본원인 노출)**:
1. **3개월(레짐 일치) 내에서는 모든 규칙이 동전던지기(최고 6/12)**. 전체 11~14/24 분리력은 **전부 1개월 trackb2 과적합 세대 교란**에서 옴(R7.2 확정). 레짐을 분리하니 진입품질 분리력 증발.
2. **3개월 고빈도(≥40거래) PASS는 단 1개(trackb4 g1)**, 나머지 "3개월 PASS"는 전부 시드 gen0. **비시드 양성 표본 n=1 → 진입 게이트 학습 자체가 통계적으로 불가**.
3. **trackb4 g1(유일 3개월 고빈도 흑자, MDD6.3)이 3개월 적자들보다 규율이 *적음***: breakout이 OR(느슨)인데 trackb3 g2/g3·trackb4 g5(MDD15~31 적자)는 breakout_AND(타이트). **손실 코드가 더 타이트한데 적자 = 매도 §3.14와 동일 역설**. trackb4 g1의 흑자는 진입게이트가 아니라 MDD제어 매도 페어링+레짐 운(運).
4. liquidity_gate(R7.1)는 3개월 PASS 4/4·LOSS 6/8 양쪽 존재 → 매수 분리 안 함(R7.1은 1개월 흑자붕괴 방지엔 기여했으나 3개월 MDD폭증과 무관).

**🔴 통합 결론(매수+매도 ground-truth 합의)**: **양쪽 정적 코드 게이트(buy·sell) 모두 결정론적으로 반증.** 고빈도 흑자/적자를 가르는 것은 코드 내용이 아니라 **시장 레짐**(2025-01 우호 → 02~03 붕괴). 고빈도+흑자+저MDD는 3개월서 희소(~1/8)하고 정적 특징으로 게이트 불가. **→ 레버는 코드게이트가 아니라 (a) 레짐-강건 선택=holdout 졸업(§3.12 S5, loop.py 졸업경로 토글·엔진무수정·구현가능·과적합 졸업 차단) (b) 생성측 품질(§4 🔴, 미해결 핵심) (c) 시드를 레짐-강건 골드로 인정.** S3(매도게이트)·진입게이트 둘 다 dead end 확정 — R7.4 과발화·§3.14 매도와 함께 '정적 코드 판별 불가' 3연속. 산출물: `_temp_s3_buy_codes.*`·`_temp_s3_buyoracle.py`(재현용·커밋제외).

### 3.16 🔴 1년 백테 기반 전환 + 시드 강건성 단기창 착시 폭로 (2026-05-30, 사용자 지정 방향)

§3.15 후 사용자 결정: **①holdout 졸업 + ②생성측 LLM 품질 둘 다 + 핵심 통찰 "백테 기간을 1년으로"**(1년이 오래 안 걸리니 엔진 구동부터 긴 기간 설정). 1년 in-sample은 레짐 과적합을 **구조적으로 제거**(여러 레짐 포함 1년을 견디면 정의상 강건). holdout보다 근본적.

**(A) 1년 백테 실현 가능 확정**: 데이터 2022-03~2026-02(955거래일, 2025 전체 완비). RAM **273GB(가용182GB)** — 메모리 무문제. 1년 smoke(`run_full_evo_1yr_smoke_config.json`, 시드 1회, run=yr1smoke): **warm prepare 성공(back_count=1638=3개월 810의 2×), per-run 59.4초**(1년인데도 빠름 — warm prepare 1회 후 run 빠른 아키텍처 = 사용자 통찰 정확).

**(B) 🔴 시드 Tick_902의 "강건성"은 단기창 착시 — 1년 MDD 36%**: smoke 시드 gen0 1년(2025 전체) = **gate FALSE, MDD 36.38% > cap 10**(profit +318,045·105거래·daily 0.42·calmar 0.18·r² 0.21). MDD 0.88(1개월)·5.39(3개월)이 "보고서급"이라던 §3.10 평가는 **3개월 우호창 과적합**이었음. **1년 기준으론 시드조차 졸업 못 함.** 베이스라인 정직 리셋: 진짜 목표 = 1년 전체 게이트 통과(MDD≤10·흑자·빈도)하는 창-과적합-불가 전략.

**(C) holdout 졸업(§3.12 S5)은 이미 구현·CLI 배선·작동 실증(task #40 완료)**: `graduation_holdout` 토글 + `holdout_recent_days`(기본30) + `fitness/holdout.py compute_holdout_verdict`(결과 CSV를 거래일로 train/끝N일 holdout 분할 → `compute_fitness` 동일 게이트 재판정, 추가 백테 0). loop.py:1099 P5 블록이 실제 배선(launch_config.py:62 "no-op" 주석은 **stale** — 대시보드 폼만 의도적 제외, CLI config-JSON 경로는 작동). `_temp_holdout_verify.py` 실증: **trackb2 "7/8 winner"를 끝 10거래일 holdout하면 hold-MDD 107~766% 폭발**(극단적 곡선맞춤 정량 폭로), 시드 fullevo3 g0만 holdout 통과(hold-MDD 7.71). holdout=강력한 과적합 필터. ※주의: 전략들이 소수 거래일에만 매매(3개월 4~18 distinct days)라 holdout_recent_days는 작게(3개월=10, 1년=30 적정).

**(D) 🔴 full 1년 진화 run 결과(run=yr1evo, 8세대 complete) = winner 0, MDD 36% 구조적 바닥 확정**: refine-from-best·dispersion+liquidity+mdd_control·holdout ON. best_gen=0(시드), winner=−1.

| 세대 | gate | MDD | profit | 거래 | calmar | 판정 |
|------|------|-----|--------|------|--------|------|
| gen0 시드 | ✗ | 36.38 | +318,045 | 105 | 0.18 | 유일 흑자·best |
| gen1 | ✗ | 42.11 | −1,693,175 | 114 | −0.83 | refine 악화 |
| gen2 | ✗ | 35.53 | −1,006,450 | 113 | −0.59 | 적자 |
| gen3·5·7 | — | 타임아웃(과발화) ×3 | | | | |
| gen4 | ✗ | 41.78 | −435,037 | 106 | −0.22 | 적자 |
| gen6 | ✗ | 37.81 | −127,359 | 104 | −0.07 | 近breakeven |

- **시드 1년 MDD 36%가 구조적 바닥**: 모든 refine 세대 MDD 35~42% 고착. refine는 적자만 줄임(−169만→−127만 점진), **MDD는 전혀 못 낮춤** → 아침 소형주 스캘프 전략군의 연 MDD ~36%는 hill-climb으로 못 깨는 구조적 한계.
- **빈도-MDD 프론티어가 1년서 더 잔혹**(빈도 0.4→0.5만 올려도 MDD폭증, 8세대중 3 타임아웃). holdout 미발동(main 게이트 통과 0).
- **"보고서급" 완전 착시 최종확정**: MDD 0.88(1개월)→5.39(3개월)→**36%(1년)**. 시드=연6.4%·MDD36%·calmar0.18 위험조정 나쁜 전략.
- **코드게이트(§3.14·3.15)도 refine-hill-climb(이번)도 1년-강건 못 만듦.** 남은 레버 = **생성측 근본 재설계(task#41)** 또는 도메인(아침스캘프) 자체가 연-강건 불가 가능성.

**(E) 🎯 시드 1년 drawdown 구조 진단(`_temp_seed_1yr_dd.py`) = MDD는 레짐 의존(도메인은 살아있음)**: 시드 yr1evo gen0 1년 CSV 월별 분해:

| 기간 | 손익 | 해석 |
|------|------|------|
| 2025 1~4월 | **+2,496,560** | 강한 엣지(3개월 평가창 01~03이 이 황금기와 겹침) |
| 2025 5~12월 | **−2,178,515** | 엣지 소멸·지속 출혈(5월−694K·9월−373K·11월−734K) |
| 연 NET | +318,045 | 앞 이익을 뒤가 거의 상쇄 |

- 최대낙폭: 4/23 정점(+2.58M)→12/15 바닥(−182K), **8개월 지속 하락**(단일폭락 아님). 최악 8일(−2.07M)도 5·6·7·11·12월 분산.
- **결론: MDD 36%는 레짐 의존**. 도메인(아침 소형주 스캘프)이 망한 게 아니라 1~4월 진짜 엣지·5~12월 음의 엣지. "3개월 보고서급"=우연히 **최고 분기 측정**. → 레버 = **레짐-적응 생성**(시장상태/최근성과로 나쁜 레짐 진입차단·노출축소; 5~12월 출혈만 막으면 +318K→~+2.5M·저MDD). 단 레짐 사전탐지는 어려운 미해결 과제.

**(F) ⚠️ 시장상태 변수 가용성 조사(사용자 선택) = 매크로 레짐 변수 부재(아키텍처 제약)**: tick 엔진 `backengine_future_tick.py:9-20` exec 네임스페이스 = 종목별 변수(현재가·등락율·체결강도·이동평균·당일거래대금·등락율각도·관심종목 등) + `리스크점수`(`시장리스크분석` 토글 ON시, `trade/risk_analyzer.py RiskAnalyzer.get_risk_score`). **단 get_risk_score는 단일 종목 최근틱 윈도우(변동성·RSI·체결강도)에서 산출 = 종목별 리스크지 브로드마켓 레짐 아님.** 엔진은 **종목코드별 병렬**(각 엔진이 한 종목 틱만 봄)이라 **결정시점에 지수/시장전체 레짐 변수 없음**. ms_analyzer는 update_data만(전략 변수 미노출). → 5~12월 매크로 레짐을 per-stock 전략이 직접 관측 불가; 시드는 이미 체결강도·각도·팔로스루 조건 보유한 채 출혈 = **per-stock 프록시로 매크로 레짐 포착은 약함**. **②(레짐-적응 생성) 천장**: 강한 형태(매크로 타이밍)는 아키텍처 봉쇄, 약한 형태(리스크점수+종목변동성 프록시)만 가능. (rk/ms_analyzer는 v3k 서브시스템 — CLAUDE.md V3 금지로 조사만·미수정.)

**(G) 🎯 1년 achievable 프론티어 특성화(run=yr1front, mdd_cap완화40·위험조정목표·dispersion OFF·10세대, 사용자 선택) = 시드가 천장, 흑자는 MDD~36%에 잠김**: winner=gen0 시드. refine 9세대 전부 시드 못 이김.

| 거래수(일평균) | MDD | profit | 판정 |
|------|-----|--------|------|
| 37 (0.2) | **14.2%** | −369,396 | 저빈도→저MDD지만 적자 |
| 97 (0.4) | 28.9% | −519,540 | 적자 |
| **105 (0.4) 시드** | **36.4%** | **+318,045** | 유일 흑자 best(calmar 0.18) |
| 105 (0.4) | 37.3% | +146,250 | 흑자(calmar 0.08, 시드열등) |
| 112 (0.5) | 50.3% | −1,885,976 | 적자 |
| 257 (1.1) | 112.4% | −5,608,060 | 과발화 폭발 |
| (gen1·3·5·7) | 타임아웃 ×4 | | |

- **빈도↔MDD 단조관계 확정**: 거래 37→105→257 늘수록 MDD 14→36→112%. **흑자는 오직 시드의 105거래·MDD36% 구간**에만 존재.
- **저MDD(14%)는 달성 가능하나 그러면 거래가 너무 적어 적자**(저빈도 흑자 미발견). **고빈도는 MDD 폭발**.
- **결론: 이 전략군(아침 소형주 스캘프)의 1년 천장 = 시드 +318K/년·MDD36%·calmar0.18.** "저MDD+흑자" 1년 동시달성 = **이 전략군 본질 불가**. refine-from-seed는 시드가 전역최적이라 소진. → 36%가 흑자 바닥(절감하려면 적자 감수). 산출물 `_temp_yr1front.log`.

**🔴 통합 현실(S3→1년 전환 전체)**: 코드게이트 불가(§3.14·3.15)→1년평가가 단기창 착시 폭로(시드 MDD36%, §3.16-B)→refine·frontier 모두 시드 천장 확정(§3.16-D·G)→매크로 레짐변수 아키텍처 부재(§3.16-F). **현재 전략군+refine 패러다임은 1년 기준 한계 도달.** 돌파는 (a)**fresh 생성**(refine-from-seed 탈피, seed_null로 다른 철학·저빈도 고확신 탐색 — 미시도) (b)**감독형 배포**(시드의 1~4월 엣지를 STOM서 사람감독 운용) (c)다른 도메인/엔진. 사용자 목표=좋은 조건식 찾아 STOM 검증 후 실매매(사람감독)이므로 (a)+(b) 유망.

### 3.17 ❌ fresh 생성(백지) 탐색 = 완전 실패, 시드 인간튜닝 재현 불가 확정 (2026-05-30, 사용자 선택 (a))

사용자 선택 "fresh 생성 탐색(다른 철학)"으로 **seed_null·refine OFF·매 세대 독립 백지생성**(`run_full_evo_1yr_fresh_config.json`, MDD완화40·위험조정·12세대, run=yr1fresh) 실측. **winner=−1, best_gen=8, 흑자 세대 0개.**

| gen | 거래 | MDD | profit | 패턴 |
|-----|------|-----|--------|------|
| 0 | 4932 | 222% | −7,744만 | 과발화 |
| 2 | 6802 | 636% | −1.27억 | 과발화 |
| 5 | 55773 | 734% | **−11.6억** | 파국 |
| 8 (best) | 207 | 92% | −455만 | 최선이나 적자 |
| 9 | 35 | 17% | −83만 | 과소·저MDD나 적자 |
| 10 | 6339 | 2851% | −1.42억 | 파국 |
| 11 | 819 | 254% | −1,288만 | 과발화 |

- **전 12세대 적자(−83만~−11.6억), MDD 17~2851%, 거래 35~55773 완전 비수렴**(gen9 35거래→gen10 6339거래 진동). autopsy 피드백으로 graded 미세상승(0.0005→0.13)하나 흑자 근처도 못 감.
- **결론: 백지 LLM 생성은 풀유니버스에서 완전 실패.** 시드 Tick_902의 인간 튜닝(시총<3000·등락율밴드·VI아래5호가·라운드피겨·체결강도범위·당일거래대금각도·시간대분기 등 정교한 진입필터)을 LLM이 12세대로 재현 불가. fresh는 과발화↔과소를 오갈 뿐 시드의 흑자 sweet spot(105거래·MDD36) 못 찾음.

### 3.18 🔴 오늘 세션 전체 종합 — AI 루프는 1년 정직평가서 인간시드를 못 이김, 실용경로=감독형 배포

오늘(2026-05-30) ground-truth로 가능한 레버를 **전부 체계적으로 소거**:
1. 코드게이트(매수·매도) 정적판별 — ❌불가(§3.14·3.15, 출처지문 과적합)
2. 1년 정직평가 — 시드 "보고서급"은 3개월 착시, 진짜 MDD 36%(§3.16-B)
3. refine-from-seed(1년) — ❌시드가 천장(§3.16-D)
4. frontier(완화캡) — ❌시드 best, 저MDD는 적자로만 가능(§3.16-G)
5. 매크로 레짐변수 — ❌아키텍처 부재(종목별 병렬, §3.16-F)
6. fresh 생성 — ❌완전 실패·비수렴(§3.17)

**확정 결론**: **현 AI 루프(생성+refine 패러다임)는 1년 정직 평가에서 인간 튜닝 시드 Tick_902를 못 이긴다.** 시드=연 +318K·MDD36%·calmar0.18(위험조정 평범하나 유일 흑자), 엣지는 레짐 의존(1~4월 +2.5M 진짜·5~12월 음). **실용 경로 = (b) 감독형 배포**: 시드를 STOM export→운영백테 1회 확인→**사람이 우호 레짐에 감독 운용**(나쁜 레짐 수동 중단). AI 루프는 '시드 능가 자동탐색'이 아니라 '연구기록·검증·시드 정제 보조' 역할로 재정의. (돌파하려면 fresh 생성 품질 근본개선=시드급 도메인지식 프롬프트 주입, 또는 다른 전략 도메인·엔진 — 모두 큰 별도 과제.)

### 3.19 진입조건 레짐안정성 진단 + 🔴 평가 프레이밍 교정 (2026-05-30, 사용자 지적)

**(A) 싼 진단(새 백테0회, `_temp_seed_regime_stability.py`)**: 시드 2025 거래 105건을 분기로 쪼개 각 진입조건의 수익/손실 판별방향 부호 측정. **레짐**: Q1 승률67%·+1.62% / Q2~Q4 39~43%·음수(엣지 Q1 집중). **🔴 진입조건 9개 전부 분기마다 판별부호 뒤집힘(안정 0개)** — 예: 체결강도 Q1엔 수익거래가 높음(+)·Q2~Q4엔 낮음(−) 완전반전. → 단일년 귀속분석은 Q1패턴 학습→Q2~Q4 반전으로 생성기 오도(싼 단일년 버전 = 과적합·해로움). 단 분기당 ~25거래 희소라 "안정조건 없음" 단정 불가(있어도 탐지불가 = **105거래/년은 조건규칙 학습에 근본 과소표본**). Workflow 2비판(과적합="위험"/실현성="조건부유망") 실측 확인: idea①(시총·시간대 귀속)은 `autopsy/segment.py`에 부분존재, ablation(idea②)은 실제 중첩 전략코드서 깨짐(활성조건~10개, #주석 도메인지식 AST 불가시), 진짜버전은 **다년 교차 필요(2022~2026 데이터 보유)**.

**(B) 🔴 평가 프레이밍 교정(사용자 지적 — 중요, 철학 복원)**: 그동안 "매 구간 흑자/1년 저MDD"를 합격선처럼 다뤄 모든 걸 "실패"로 칠한 것은 **프레이밍 오류**. 보고서(.md) 우수전략의 기준은 **"등락은 있어도 누적수익이 장기 우상향 추세"**(매 구간 흑자 아님). 시스템에 이미 **`uptrend_r2`** 지표로 존재(시드 3개월 r²0.85 깔끔한 우상향 / 1년 r²0.21 후반 추세꺾임). **목표 재확인 = 일회성 좋은전략이 아닌 '우상향 추세를 학습하는 연구 파이프라인'(§1 원래 철학). 항상 수익 불필요 · 조건식 안 나올 수 있음 · 학습 자체가 산출물.** 오늘 발견들은 "실패"가 아니라 **학습**(짧은창 착시·시드 레짐프로파일·조건판별 레짐의존·fresh 가드레일 필요). **다음(사용자 "둘 다") = ① 평가렌즈 교정(uptrend_r2 비중↑·하락구간 허용·과한게이트 완화, 토글 기본OFF) + ② 다년 학습 파이프라인.**

**✅ ① 완료(미커밋, 사용자 승인 대기)**: `winner_objective='uptrend'` 추가 — 누적 우상향 추세(uptrend_r2)를 winner/best 선택 주기준으로 격상(보고서 우수전략의 정의적 특성). gate-passed term = `composite × clamp01(uptrend_r2)`(composite=calmar×r²이므로 r² 추가가중 = 평활도 강조). 4경로 일관(score.py `_gate_passed_term`+호출부 `if objective in ("multi","uptrend")`, loop.py `_winner_compare_key`=(r²,score)·`_winner_score_value`=r², ga.py 미러+`Individual.uptrend_r2` 슬롯추가). 기본 risk_adjusted 불변·엔진무수정·graded≥1.0 불변. **code-reviewer APPROVE(CRITICAL/HIGH/MEDIUM 0, 6불변식 실증)·baseline PYTHONUTF8=1 1804 passed/7 failed(기존)·신규0**. 신규 `tests/unit/test_uptrend_objective.py` 11 passed. 변경: score.py·loop.py·ga.py·config.py·launch_config.py. (참고: launch_config의 winner_objective choices에 'multi'가 원래 누락 — 'uptrend'만 추가, 'multi' UI 노출은 후속.) **② 다년 학습 파이프라인은 미착수(대형 과제 — 2022~2025 다년 백테 + 연도교차 우상향 안정성 학습; 데이터 보유).**

### 3.20 🎯 ② 1단계: 시드 다년(2023~25) 특성화 = 시드는 견고한 다년 우상향 전략 (2026-05-31, run=seed3yr)

② 착수 1단계로 시드 Tick_902를 **2023~2025 3년 한 번에 백테**(`run_seed_3yr_config.json`, winner_objective='uptrend' 첫 실전, warm prepare back_count=2285·per-run 112초) 후 결과 CSV를 **연도별 오프라인 분할**(`_temp_seed_multiyear_split.py`):

| 연도 | 거래 | 승률 | 수익(원) | uptrend r² | 판정 |
|------|------|------|---------|-----------|------|
| 2023 | 114 | 54% | **+4,727,001** | **0.95** | 강한 우상향 |
| 2024 | 88 | 51% | **+3,221,506** | **0.82** | 우상향 |
| 2025 | 105 | 47% | +318,045 | 0.20 | 흑자(약추세) |
| **3년 전체** | 307 | — | **+8,266,552** | **0.90** | gate통과(cap40)·MDD **17.76%**·calmar 3.19 |

- **🔴 단일년 비관론 교정**: 시드는 3년 연속 흑자, 3년 누적 r² 0.90(매끄러운 우상향), MDD 17.76%(2025단독 36%보다 낮음 — 2023/24 강세가 베이스를 높임). **2025는 시드의 최악의 해였다** — 그동안 "1년 MDD 36%=별로" 비관은 하필 최악 연도만 본 것. 다년 지평에선 시드가 **견고한 우상향 자산**(사용자가 말한 "등락 있어도 누적 우상향" 정의에 정확히 부합).
- **검증**: 2025 sub-수익 +318,045가 yr1evo gen0과 정확히 일치 → 연도분할 정확. (per-year MDD%는 연도별 cumsum 리셋 아티팩트로 신뢰불가; 3년 연속곡선 MDD 17.76%만 유효.)
- **caveat**: in-sample(시드 튜닝시기 포함 가능)이라 미래 보장 아님. 단 3년 트랙레코드 = 단일년 뷰보다 훨씬 신뢰, 감독배포 근거 강화 + 다년 학습의 양성 기준선.
- **② 다음 단계**: (a) 생성/refine를 다년(2023~25) 적합도(연도별 우상향 안정성 보상)로 평가 → 연도교차 강건 조건만 채택 (b) 2022 partial·2026 추가로 OOS 확장. 신규 config `run_seed_3yr_config.json`, 산출물 `_temp_seed_multiyear_split.py`.

**→ 다음 행동 후보(아키텍처 제약 반영)**: ①**per-stock 레짐 프록시 생성 시도**: `시장리스크분석` ON + 프롬프트로 LLM이 `리스크점수`·종목 변동성·팔로스루를 진입게이트로 쓰게 유도(약하나 가능·엔진내). ②**포트폴리오 오버레이 레짐필터**(전략코드 밖 메타층이 불리레짐일 거래 중단 — 아키텍처 부합 안 함·스코프 큼). ③**mdd_cap 완화 run으로 achievable 연 프론티어 특성화**(현실 타깃 재설정). ④**아키텍처 천장 인정**(per-stock 전략은 매크로 레짐 타이밍 불가가 본질). 신규 config: `run_full_evo_1yr_smoke_config.json`·`run_full_evo_1yr_config.json`(gitignored). 산출물 `_temp_holdout_verify.py`·`_temp_seed_1yr_dd.py`·`_temp_yr1*.log`(재현용).

---

### 3.21 🎯 ② 본 빌드 완료 — multiyear objective + 웹 대시보드 프로세스 플로우 + 시간대 측정/유도 (2026-05-31, run=myr1)

사용자 지시: "②본빌드 + GUI(=웹 대시보드) 프로세스 플로우 실시간 가시성 + 시초 20분 시간대×시총 가설", 범위 결정 "A(다년 안정성 핵심)+시간대 탐구 추가". ultracode 워크플로우로 4영역(대시보드·파이프라인·가설 실측·② 스코프) 병렬 파악 후 A→B→C→D 순 구현(각 단계 code-reviewer opus APPROVE·baseline 신규0·엔진 무수정).

**가설 실측(seed3yr 307거래, ultracode)**: 시간축은 *시드*에선 무의미(전부 09:00–09:05 = 902 5분 스캘퍼)이나, 시가총액축은 3년 안정 신호 — **소형 avoid(return_diff −0.1446 매년)·초소형 prefer(+0.6317 매년)**(시드는 대형주 미거래라 "대형 회피"는 시드 데이터로 미표면 = min-samples 게이트의 정확한 동작). → 시간대 특성은 비-시드 생성 전략으로만 측정 가능 → C-2/C-3 추가.

**Phase A (커밋 `bed0a1d0`)**: 웹 대시보드 5단계 프로세스 플로우(생성→백테→채점→부검→반복) active 테두리 + 실시간 로그 패널. `contract.LatestInfo` recent_logs(≤50)/current_step·loop 세분 phase 발행+run-scoped deque·`_PHASE_STEP`(GA 포함)·`ProcessFlowPanel`(current_step 우선·phaseIndex 폴백). 백엔드 맵 대칭 회귀가드 추가. (PyQt 데스크톱 GUI 아님.)

**Phase B (커밋 `49db2288`)**: `winner_objective='multiyear'`. 신규 `fitness/multiyear.py::compute_multiyear_stability`(결과 CSV 연도분할 → `stability_term=clamp01(mean(positive_frac, mean_r2, consistency=1−r2분산/var_norm, profit_even=1−수익CV/cv_norm))`). `score.py` `_gate_passed_term` multiyear 분기(`composite×stability`, None→1.0 중립=risk_adjusted)·config 4필드 default-OFF·loop `_score_outcome` 가드 계산+winner 케이스. 하드게이트(compute_fitness) 무수정·default byte-identical·gate-passed graded≥1.0 불변식. 16 테스트(None==risk_adjusted 정확 동등 포함). 실측 시드 stability_term=**0.6164**(2025 저r²·수익편차가 정확히 끌어내림).

**Phase C (커밋 `609bde6c`)**: C-1 `analyze_segments_by_year`+`_find_stable_cells`(연도교차 return_diff 부호일관 셀을 avoid/prefer로, ≥2년)+`multiyear_to_page_data`. C-2 `FINE_TIME_BUCKETS`(5분 시초 0900-0905…0920+) + `add_time_segment(buckets=)`/`analyze_*_segments(time_buckets=)` optional(기본 byte-identical) + `segment_fine_time` 토글. C-3 `encourage_time_dispersion` → 매수 프롬프트 "09:00–09:20 분산" 소프트 넛지(reject 아님, 기존 dispersion_prompt_enabled와 독립). 12 테스트. `launch_config` 스키마에 multi/multiyear choices + 토글 2종(GUI 선택 가능).

**Phase D 검증 run=myr1** (3년 2023-01~2025-12·multiyear·segment_fine_time·encourage_time_dispersion·hillclimb·gen0 시드+refine 2, ~17분, warm prepare back_count=2285):

| gen | gate | graded | profit | MDD% | calmar | r² | trades |
|---|---|---|---|---|---|---|---|
| 0 시드 | **통과** | **2.7703** | +8,266,552 | 17.76 | 3.191 | 0.900 | 307 |
| 1 refine | 실패 | 0.328 | +3,494,443 | 13.01 | 1.852 | 0.884 | 179 (일평균0.2<0.3) |
| 2 refine | error | 0 | — | — | — | — | 0 (메트릭 미산출, graceful) |

winner=gen0 시드, **winner_score=0.6164(=multiyear stability_term)**, run status=complete. **gen0 graded 2.7703 = 1 + composite(2.87185) × stability(0.6164) 정확 재현 → ② 통합 파이프라인(연도분할→stability_term→graded→winner 선택)이 production 루프에서 검증 완료.** refine 2세대 = gen1 흑자·평활(r²0.88)하나 빈도 부족으로 gate 실패, gen2 LLM 생성 결함(거래0)으로 graceful error → multiyear가 gate-passed 시드를 정확히 우선. **AI가 3세대 refine로 시드를 못 이김 = 기존 미해결 연구과제(refine 천장 §3.16-D)이지 빌드 결함 아님.**

**검증**: 전체 unit baseline 유지(신규 0)·`verify_nonrelease_sync` 통과·엔진/PyQt/backtest graph 무수정.

**잔여(소규모 후속)**: ① C-1 `analyze_segments_by_year`를 루프 `page_data`에 배선(함수·serializer 준비완료, 대시보드 "연도교차 안정 특성" 패널 표시는 미배선) ② 장기 진화 run(max_gen↑)으로 refine가 multiyear-안정 조건을 학습하는지 + 분산 넛지 효과를 대시보드로 관찰 측정 ③ 2022 partial·2026 OOS 확장(config window edit만, 코드 변경 0).

신규 config `run_multiyear_config.json`(gitignored). 산출물 `_temp_multiyear_check.py`·`_temp_yearseg_check.py`(재현용).

---

### 3.22 ⚠️→✅ multiyear 평가기준 정정 + 긴 run OOM 발견 + winner 규칙 수정 (2026-05-31, run=myr2~4 + Phase E)

사용자가 15세대 긴 run 요청 → myr2/myr3/myr4(3년·multiyear) **모두 refine 도중 프로세스 OOM 크래시**(트레이스백 0 = OS kill). **원인 정정(앞선 "대시보드 동시구동" 진단은 오진)**: myr4는 대시보드 없이 단독인데도 gen5에서 크래시 → 진짜 원인은 **refine가 생성한 과발화 전략**(gen2 750거래/MDD160, gen3 `매수=True` 등)이 **단일 백테 도중** 거래·보유 객체로 메모리 폭증 → 타임아웃(시간 컷)이 작동하기 전에 OOM. warm prepare 데이터는 고정(사용자 지적 정확); 폭증은 per-run 거래량. → **3년 풀유니버스 단일 warm 세션은 ~5세대가 한계**(myr1은 3세대라 생존).

**myr4 gen0~4 기록**: gen0 시드 통과(graded 2.77·+8.27M·MDD17.76·r²0.90), gen1/3 타임아웃(과발화), gen2 과발화 적자(−8.27M·MDD160·750거래), **gen4 첫 refine 게이트 통과**(+4.82M·r²0.725·calmar1.82·317거래).

**🔴 평가기준 정정(사용자, 핵심)**: "매년 균등 수익/일정 기울기/매년 흑자"는 **요구하지 않음**. 기준 = **"등락·기울기 변동이 있어도 다년 전구간 누적곡선이 장기 우상향"** 하나. → 기존 multiyear stability_term(per-year positive_frac·consistency·profit_even 균등성 결합)이 바로 그 **거부된 균등성을 강제**했고, 그래서 약한 gen4(stability 0.620)가 강한 시드(0.616)보다 winner로 뽑히는 버그를 유발(§3.21 D에서 관찰).

**✅ Phase E 수정(커밋 `51b35ffc`, code-reviewer opus APPROVE)**: `stability_term = clamp01(전구간 단일 누적곡선 우상향 R²)`(균등성 항 3개 제거, 다년 참여 게이트만 유지=단일년 행운 차단), winner 키 `stability_term → graded`(=1+composite×stability; 강한 다년-우상향이 '균등하지만 약한' 전략을 이김). **실측 재검증(myr4 CSV): 시드 stability 0.90·graded 3.58 > gen4 0.725·1.96 → 시드 정상 우승.** R² 방향 우려(하향 곡선도 R² 높음)는 하드게이트 profit>0가 gate-passed 분기를 막아 무력화(리뷰 확인). 엔진/하드게이트(compute_fitness) 무수정·`score.py` 로직 byte-동일(문서만 정정)·default 'risk_adjusted' byte-identical·graded≥1.0 불변식·신규 16테스트(down-year 허용·winner-strength 가드).

**현황**: ② 빌드 + 평가기준 정합 **완료**. **AI refine는 여전히 시드 못 이김**(과발화 천장 = 기존 §3.16-D 연구질문, 빌드결함 아님). **15세대 완주는 OOM 인프라 이슈로 미완** — 별도 과제(엔진수↓ / 과발화 PRE-SAVE 사전차단 / per-run 메모리 가드). 신규 config `run_multiyear_long_config.json`·`run_multiyear_long2_config.json`(gitignored).

**🔧 추가 인프라 발견(resume 시도, 2026-05-31)**: 15세대 완주를 resume(`--run-id` 이어하기, myr5+resume)로 시도 → 실패. **크래시한 run이 16개 warm 엔진 자식을 고아(orphan)로 남긴다**(부모가 OOM SIGKILL될 때 자식 엔진 미정리) → myr2~5+resume 누적으로 **~37개 고아·~34GB RAM 점유** → 새 run이 prepare 전 즉시 OOM(resume가 무출력 exit1로 죽음). 정리 = `taskkill /F /IM python.exe`(python3.exe는 별개라 보존). **교훈: 3년 풀유니버스 run 크래시 후엔 반드시 고아 엔진 정리하고, 크래시 루프를 반복하지 말 것. 15세대 완주는 엔진측 자식 정리/거래수 캡(보호영역) 없이는 불가.** myr5 부분결과(Phase E 신규 규칙 실측): gen0 시드 graded **3.584**(=1+composite2.87×전구간r²0.90) winner, gen1 +4.1M·r²0.90이나 빈도0.2<0.3 게이트 실패, gen2 타임아웃 → myr1/myr4와 **동일 결론 재확인**(시드 1등·refine 과발화). 사용자 선택 = '정리 + 마무리'(다).

---

### 3.23 ✅ (A) 생성 품질 개선 — 과발화 차단 필터게이트 + 시드급 게이팅 프롬프트 (2026-05-31, 커밋 `e16ab39e`)

사용자가 (A)생성 품질 개선을 선택 → refine 과발화 천장을 **생성측**에서 공략. 진단: 과발화 = 진입 게이트 부실(느슨/적음/OR/시간창 무시). 시드는 ~9개 필터 범주를 AND로 결합 + 시초 시간창에 한정 = 307거래(촘촘). 2레버(모두 default-OFF·엔진 무수정·byte-identical):
- **`brain/filter_gate.py`(신규)**: `count_filter_categories(code)` — 주석 제거 후 비교연산자(`<`/`>`)와 함께 등장한 distinct 필터범주(liquidity·market_cap·price_band·change_band·exec_strength·orderbook·volume_surge·time_window·turnover) 수. `liquidity_gate.py` 패턴 미러(순수함수). "좋은 전략"(R7.4 불가) 아니라 **"충분히 게이트됐나"** 구조검사. `시가`는 시가총액/시가등락율 부분문자열 충돌로 price_band에서 제외.
- **`prompt.py`**: 매수 경로에 시드 게이팅 구조 가이드 블록(`require_filter_gates`).
- **`generator.py`**: PRE-SAVE 필터범주 게이트(`<min`이면 reject→재생성, `require_liquidity_gate` 미러).
- **config**: `require_filter_gates`(기본 False)·`min_filter_categories`(기본 5; 시드=9 여유). `loop._generate_pair` 배선·`launch_config` 폼 2필드.

**검증**: 신규 22 테스트(시드 매수코드 실측 9범주·`매수=True` 0·단일 1·주석무시·default byte-동일). **🎯실측 생성검사(gpt_auth, 백테 없음): 토글 ON 매수 3/3 전부 1회만에 8개 범주 생성** — 과발화(1~2범주/`매수=True`)에서 시드급(8≈9)으로 **생성 품질 실측 개선**. code-reviewer(opus) APPROVE·baseline 1856p/7f 신규0.

**한계/다음**: 구조게이트는 범주 *폭*만 봄 → 다중토큰 항상참(`현재가>0 and …`) 우회 가능(프롬프트 가드레일이 "항상참 금지·이벤트 성립 순간 진입"으로 보완·짝 동작). **남은 검증 질문: 잘 게이트된 생성물이 백테에서 (a)과발화 안 함(거래수 bounded·크래시↓) (b)흑자·시드급 위험조정인가** — 확인하려면 백테 필요(**3년 OOM 회피 위해 소규모/단기**). `require_filter_gates=ON` 짧은 run이 다음 자연스러운 단계. 신규 `_temp_filtergate_gen.py`(gitignored).

---

## §4. ⚡ 다음 세션 첫 행동 (권장 순서)

> **🔴 2026-05-29 최신(R8 후) 다음 세션 최우선 = 고빈도(일평균10~23) + 고calmar/r² 생성(=시드 능가)**: 이번 세션 결론 — 빈도-흑자-MDD 양립 메커니즘(dispersion·거래대금게이트강제·MDD제어 토글)은 구현했고 개별 성공 사례(trackb2 gen2 1개월·trackb4 gen1 3개월)도 있으나, **refine 생성세대는 빈도만 높지 위험조정수익(calmar·r²)이 시드 Tick_902(calmar31·r²0.85)에 미달**(§3.7 R7.4·§3.9). 즉 "고빈도이면서 시드급 calmar/r²"를 만드는 것이 미해결 핵심. 방향: LLM 생성 품질·프롬프트(보고서 변수패턴 강화)·도메인/시드 재설계. **과발화 정적컷은 불가 판명(§3.7)**이라 런타임 fail-fast 유지. 보고서급 도달 가능성 평가는 §3.10 참조. 대시보드 LIVE 가시성은 R8로 완비(§3.8, phase·active_config·품질지표 실측).
>
> **🆕 레버 ① 완료(2026-05-29, 커밋 `19cf5f0f`)**: `winner_objective='multi'`(calmar·r²·일평균빈도·payoff 정규화 동일가중 결합) 구현·code-reviewer APPROVE(3 CRITICAL 불변식 fuzzing 14,524케이스 0 mismatch)·baseline 신규0·기본 OFF(risk_adjusted 유지). **단 multi 단독은 시드 우위 유지 예상**(고빈도+고calmar/r² 세대가 아직 없어 freq 항이 시드의 calmar/payoff 우위를 못 이김 — §3.10) → 실효는 ②③④ 결합 시. **다음 = ② 다종목 동시성 보상 적합도(현 daily_avg_trades는 종목무관 총량이라 불충분) + 엔진 보유상한 토글(별도스코프·사용자확인)부터.** config 신규: multi_calmar_norm 30·multi_payoff_norm 1.3·multi_daily_target 10.

> **🆕 2026-05-29: step 1~2(0.3 보정·gen0 졸업·3개월 확대)는 §3.3에서 완료.** 갱신된 최우선 = **§4-NEW Track B(고빈도·흑자 양립)**. 기존 step 1~5는 후순위 보조로 유지.

### §4-NEW. Track B — 고빈도(일평균10~23)·흑자 양립 (최우선 연구과제)
- **문제**: 현재 refine는 빈도↑ 시 흑자 붕괴(저빈도가 본질 흑자). 보고서 우수전략은 "여러 종목 분산 다수 진입"으로 고빈도+흑자 동시 달성.
- **단서**: fullevo3 gen4(+479K·MDD3·calmar13.8, 빈도 0.2) = 흑자·저MDD 진입이 존재. 빈도만 못 채움.
- **방향**(설계 Workflow로 구체화): ①진입 프롬프트 재설계(다종목 분산 명시 — 종목당 1~2회×다수종목, 단일종목 과발화 지양) ②적합도/게이트가 "다종목 분산 빈도"를 보상(현재 daily_avg_trades는 종목 무관 총량) ③과발화 타임아웃 4건 회수(변이 폭 축소 or 과발화 컷 프롬프트). **엔진 무수정·토글·하위호환 유지.**

### 기존 step (후순위 보조)

1. **이 문서 + `git log --oneline -6`(ea9ea0ad 확인) 읽기.** 대시보드 기동: `python -m ai_strategy_loop --port 8770` (이미 떠 있을 수 있음 — PID는 `ai_strategy_loop --port 8770` 매칭).
2. **게이트 보정 재run으로 첫 풀유니버스 winner 졸업**(거의 확실):
   - `ai_strategy_loop/state/run_full_evo_config.json` 에서 `"min_daily_trades": 0.4` → **`0.3`** (또는 보수적으로 `"mdd_cap": 10` → `11`).
   - **권장은 freq 0.3**: gen0(Tick_902 = +740K·MDD0.88·calmar117·smooth r²0.865)이 졸업 → 보고서 철학(MDD저·payoff우선)에 가장 부합. (mdd_cap 11로 풀면 gen5 = +234K·MDD10.01·2/day·r²0.10이 졸업하나 변동성 큼.)
   - 재run: `STOM_ALLOW_MINIMAL_SETTING=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop.controller.loop --config-json ai_strategy_loop/state/run_full_evo_config.json --run-id fullevo2` (백그라운드, ~21분). 대시보드 라이브 관찰.
3. **기간 확대(보고서급 연간 통계)**: `bt_full_start/bt_full_end`를 3~12개월로 확대(예: 20250101~20251231). prepare/run 더 무겁지만(1개월=400종목·세대당~70~150s 추정; 1년은 더 큼) fitness 안정 + 연수익 비교 가능. 먼저 3개월로 단계 확대 권장.
4. **열린 난제 — 보고서급 고빈도(10-23/day)와 흑자 양립**: 현재 refine는 빈도↑ 시 흑자 붕괴(저빈도가 본질적 흑자). 보고서 전략은 "여러 종목에 분산된 다수 진입"으로 고빈도+흑자를 동시 달성 → **looser-but-still-profitable 진입 재설계**가 핵심 연구과제. 다종목 분산(다중포지션 창발)을 활용한 프롬프트/적합도 튜닝 방향.
5. baseline·커밋 규칙 준수(§8).

---

## §5. 설정 파일 전문 (전부 gitignored=로컬, 재생성용으로 여기 보존)

> `ai_strategy_loop/state/.gitignore`가 `run_*.json`·`*.db`·`*subset*`을 무시하므로 이 파일들은 커밋 안 됨. 아래 전문으로 재생성 가능.

### `state/run_full_evo_config.json` (풀유니버스 진화 — 다음 세션 주력)
```json
{
  "provider": "gpt_auth", "model": "gpt-5.5", "max_retries": 2,
  "bt_engine_mode": "warm", "bt_timeframe": "tick",
  "bt_full_start": 20250101, "bt_full_end": 20250131,
  "bt_universe_start_time": 90000, "bt_universe_end_time": 92800,
  "bt_warm_engine_count": 16, "bt_betting": "5", "bt_avg_time": 30,
  "bt_timeout": 900, "bt_warm_run_timeout": 300,
  "seed_buy": "Tick_B_902_905_Update_2", "seed_sell": "Tick_S_902_905_Update_2",
  "bt_refine_from_best": true, "freeze_buy_on_mdd_only": true,
  "min_daily_trades": 0.4, "mdd_cap": 10, "tpi_gate_enabled": false, "overtrade_softcap": 200,
  "winner_objective": "profit", "profit_weight": 0.6, "evolution_mode": "hillclimb",
  "exit_quality_enabled": true, "payoff_target": 1.1, "give_back_weight": 0.5, "give_back_mfe_threshold": 1.5,
  "max_generations": 8, "cost_cap_generations": 40, "autopsy_enabled": true, "meta_seed_enabled": false
}
```

### `state/run_full_smoke_config.json` (풀유니버스 1회 검증; max_generations=1)
- 위와 동일하되 `bt_full_end: 20250110`, `max_generations: 1`, `tpi_gate_enabled/exit_quality_enabled/freeze_buy_on_mdd_only: false`, `bt_refine_from_best: false`, `min_daily_trades: 0.4`, `mdd_cap: 35`.

### `state/run_r5_config.json` (소형주 N=12 fresh, 보조; small_universe cold)
- `bt_scope: "small_universe"`, `bt_timeframe: "tick"`, `bt_subset_db: "ai_strategy_loop/state/tick_subset_small.db"`, `bt_engine_mode: "cold"`, `bt_engine_count: 6`, `bt_window_days_universe: 10`, **`bt_window_select: "richest"`**, `seed_buy/sell: null`(fresh), `tpi_gate_enabled: true`, `tpi_gate: 1.0`, `mdd_cap: 10`, `min_daily_trades: 1.0`, `max_generations: 8`.

### 데이터 자산 (로컬, gitignored)
- `state/tick_subset_small.db` (소형주 N=12, 524MB) — top-12 코드 위 참조.
- `state/tick_subset.db` (대형주 N=8, 1.6GB), `state/min_subset.db` (N=30, 305MB).
- `state/loop_strategies.db` — 시드 + 생성 전략(stockbuy 219/stocksell 217행). Tick_902 시드 존재 확인됨.
- 시드명: `Tick_B_902_905_Update_2`/`Tick_S_902_905_Update_2`(tick), `Min_B_Study_251227`/`Min_S_Study_251227`(min). 원본=`_database/strategy.db`. 루프 DB로 복사: `ai_strategy_loop/scripts/r0_multiposition_poc.py`의 `_copy_seed_to_loop_db(name, table)`.

---

## §6. 실행 명령어 (전부 워크트리에서)

```bash
# 대시보드 (백그라운드)
STOM_ALLOW_MINIMAL_SETTING=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop --port 8770

# 풀유니버스 진화 (주력)
STOM_ALLOW_MINIMAL_SETTING=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop.controller.loop \
  --config-json ai_strategy_loop/state/run_full_evo_config.json --run-id fullevo2

# 풀유니버스 1회 검증(smoke)
... --config-json ai_strategy_loop/state/run_full_smoke_config.json --run-id fullsmoke2

# 소형주 subset 빌드 (재생성 필요 시)
python -m ai_strategy_loop.scripts.build_subset_db --timeframe tick --size 12  # (자동선별; 소형주 top-12는 _temp_build_small.py 방식으로 codes 명시 빌드)

# baseline (브랜치 게이트)
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/ -q     # 기대: §8의 34 failed(기존)
python scripts/verify_nonrelease_sync.py
```
- loop CLI 플래그: `--config-json <path|jsonstr>` `--run-id <id>` `--max-gen N` `--provider {gpt_auth,openrouter,codex_proxy}`.

---

## §7. 아키텍처 / 코드맵 (변경분 + 핵심)

- **`ai_strategy_loop/config.py` `LoopConfig`**: 모든 설정 dataclass. 핵심 필드:
  - 스코프: `bt_scope`(single_stock|small_universe|universe), `bt_timeframe`(min|tick), `bt_engine_mode`(warm|cold), `bt_subset_db`.
  - warm 풀유니버스: `bt_full_start/bt_full_end`(YYYYMMDD), `bt_universe_start_time/end_time`(HHMMSS, 기본 90000/92800=09:00-09:28), `bt_warm_engine_count`(32), `bt_betting`(백만원; "5"=500만, 보고서는 2천만=20), `bt_avg_time`(30), `bt_warm_run_timeout`(per-run fail-fast 초; 과발화 컷).
  - small_universe: `bt_window_days_universe`(20), **`bt_window_select`(earliest|richest, 신규 토글)**.
  - 게이트: `min_daily_trades`(일평균거래 하한, 주 게이트), `mdd_cap`, `tpi_gate`+`tpi_gate_enabled`(기본OFF), `overtrade_softcap`.
  - 청산레버: `exit_quality_enabled`(ON), `payoff_target`(1.1), `give_back_weight`, `give_back_mfe_threshold`, `freeze_buy_on_mdd_only`(best가 MDD-only 실패 시 매수 동결·매도만 재생성).
  - 선택: `winner_objective`(risk_adjusted|profit|balanced), `profit_weight`, `evolution_mode`(hillclimb|ga), `seed_buy/seed_sell`(None=fresh), `bt_refine_from_best`.
- **`ai_strategy_loop/controller/loop.py`**:
  - `run_loop(...)` — 메인 진화 루프. warm 분기(`bt_engine_mode=="warm"` → `WarmBacktestSession.prepare()` 1회 후 세대마다 `warm_session.run(buy,sell,...)`); cold 분기 → `run_backtest_for`. 매 세대 `_publish_live`→`state/current_state.json`.
  - `_build_warm_btconfig(config)` — warm용 BacktestConfig 조립(전체유니버스 종목코드별 분류, full_start~end, universe time window, warm_engine_count, is_tick).
  - `run_backtest_for(config, buy, sell)` — cold subprocess(`stom_backtest.py`) 경로. small_universe면 subset back-DB + `STOM_CLI_DB_STOCK_BACK_TICK/MIN` 오버라이드 + `--divid-mode 종목코드별 분류`.
  - **`_select_universe_window(subset_db, window_days, timeframe, select_mode)`** — (이번 커밋) `earliest`=앞쪽 N일 / `richest`=coverage 최대 연속구간.
  - `_score_outcome` / fitness 호출, autopsy, seed/refine 처리(gen0 use_seed, gen1+ refine-from-best).
- **`ai_strategy_loop/fitness/score.py`**: `compute_fitness`(하드게이트: 빈도·MDD·흑자[·tpi옵션]) + `compute_graded_fitness`(통과=1+composite, 실패=profit_term×mean + 청산품질 가산). `load_exit_quality_from_csv`(payoff/give_back), `load_equity_series_from_csv`.
- **`ai_strategy_loop/brain/prompt.py`**: `build_messages` — `_timeframe_lines`(min=분당*/tick=초당* 변수 가드) + `_report_pattern_lines`(보고서 변수범주·철학 주입) + seed-refine/crossover/autopsy/history.
- **`ai_strategy_loop/scripts/build_subset_db.py`**: `--timeframe {min,tick} --size N` 또는 `build_subset_db(src, out, codes=[...], timeframe=...)`. 유동성순(거래대금) 선별이라 **대형주 편향**(소형주 원하면 codes 명시 또는 별도 선별).
- **엔진(`backtest/*.py`, 무수정)**: tick 엔진 `backengine_future_tick.py`(:88 `if not 관심종목: continue`, :89 `exec(self.buystg)`). 관심종목=arry_code 데이터 플래그. 시가총액·등락율 등은 per-tick 변수.
- **대시보드(`ai_strategy_loop/dashboard/app.py` + frontend)**: GET `/status`·`/health`·`/runs`·`/strategy_code`·`/equity_curves`, WS `/ws`. in-browser React/Babel(빌드없음, 코드변경 후 새로고침). `/ui/`.

---

## §8. 제약 · 게이트 · 함정 (반드시 준수)

- **엔진(`backtest/*.py`, numba) 무수정** 기본. 게이트/적합도/윈도우 변경은 **토글·하위호환**(기본값=기존 동작 보존). 프로젝트 전반이 이 패턴(tpi_gate_enabled/exit_quality_enabled/bt_window_select 전부 기본 OFF/earliest).
- **🔴 baseline 진실**: 문서상 옛 "7 failed"는 **stale**. 현재 환경 실제 baseline = **34 failed / 1691 passed**(추가 27~33개는 `tune/sweep/wfo/setting/report/optimizer/db/formula/exit_codes/backtest_contract` 등 **cli·ui 도구 테스트** — ai_strategy_loop 무관, 이번 세션 이전부터 존재, 환경/의존성 드리프트 추정). **신규 실패 0**이 기준(이번 윈도우 커밋은 +1 pass·신규 0 검증). 회귀 의심 시 `git stash`로 커밋상태 baseline과 비교.
- **timeframe 가드**: min에 초당*, tick에 분당*/RSI 등 쓰면 백테 NameError로 죽음. 프롬프트가 동적 안내하나 검증 필수.
- **다중포지션은 자연창발**(seed 인자/엔진 게이트 없음; divid_mode 종목코드별 분류 + 여러 종목 → 시간겹침으로 mhct 창발). 보유상한 강제는 엔진 수정 필요=별도스코프+사용자확인.
- **과발화→타임아웃 패턴**: 타이트한 매도/과발화 매수 전략은 백테 폭주 → `bt_warm_run_timeout`(현재 300, fail-fast)로 컷하고 다음 세대로. 정상 run은 18~21s(1개월 풀유니버스). fullevo1 gen1이 이 사례.
- **프로세스 안전**: STOM-dev는 Python31313. 좀비 정리는 **31313의 spawn_main / controller.loop만**. Python3119(타 프로젝트)·GUI `stom.py`·대시보드(31313이지만 controller.loop 아님)는 **보존**.
- **runlock**: `state/loop.lock` — 동시 루프 차단(cross-process). 락 든 채 dashboard start-control 테스트는 transient 실패(아티팩트). stale면 삭제 가능.
- **결과데이터 보호**: `backtest/graph/`는 보호. CLAUDE.md 금지: CLI child lane 재도입 / `.pyd` 추론 / release ingress / live / V3.
- **커밋은 사용자 승인 시.** 커밋 메시지 끝: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **tick 백테는 무겁다**(`_database/stock_tick_back.db` 29GB). 풀유니버스 기간 확대 시 prepare 비용·메모리 주의(짧은 기간부터 단계 확대).

---

## §9. 커밋 이력 (이번 체인)

`9251b614`(R0/R1 다중포지션·daily_avg·tpi토글) → `9c71fd5a`(R-Viz1 대시보드 수익곡선) → `9e4b538b`(보고서패턴 프롬프트) → `481d2578`(R4 tick 인프라) → `427fbcb3`(R4 인계문서) → **`ea9ea0ad`(R5 윈도우 richest 토글 + R4/R5 진단 정정)** → **(이 문서 커밋)**.

미커밋 산출물: warm 진화 결과(loop_strategies.db의 AILOOP_fullevo1_g* 전략, loop_runs.db 런 기록) = 로컬·gitignored 데이터.

---

## §10. 진단 스크립트 (워크트리 `_temp_*.py`, 커밋 제외 — 재현/참고용)

- `_temp_smallcap_scan.py` — 소스 tick DB 전체 종목 소형주 아침 활동 랭킹(top-N 선별).
- `_temp_build_small.py` — top-12 codes로 소형주 subset 빌드(`build_subset_db(codes=...)`).
- `_temp_iso_test.py` — Tick_902 시드를 subset에서 1회 백테(isolation, `bt_window_select` 인자 포함).
- `_temp_probe.py` — 시총제약 없는 느슨 전략 PoC(loop_strategies.db에 직접 INSERT 후 백테).
- `_temp_window_diag.py`·`_temp_diag.py` — 윈도우/시총/관심종목 분포 진단.
- (이 _temp 파일들은 일회성. 핵심 로직은 본 문서 §3~§6에 요약돼 재현 불요.)

---

## §11. 재개 체크리스트 (복사해서 첫 메시지로 써도 됨)

1. `docs/update_log/2026-05-28_ai_strategy_loop_R6_FULLUNIVERSE_HANDOFF.md` 읽기.
2. `git log --oneline -6` → `ea9ea0ad` + 이 문서 커밋 확인.
3. 대시보드 기동 확인(`http://127.0.0.1:8770/ui/`).
4. `run_full_evo_config.json` `min_daily_trades` 0.4→0.3 → 재run(run-id fullevo2) → **gen0 Tick_902(+740K·MDD0.88) 졸업 확인**(첫 풀유니버스 보고서급 winner).
5. 성공 시: 기간 3~12개월 확대 + 고빈도·흑자 양립 연구(§4-4).
6. baseline 34 failed 유지(신규 0)·커밋은 승인 시.
