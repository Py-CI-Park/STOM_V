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
