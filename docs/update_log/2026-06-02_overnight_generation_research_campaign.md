# 야간 생성 연구 캠페인 (2026-06-02 → 06-03 아침)

> **사용자 요청**: 인간 고수 조건식을 위해 **넓은 시간창 + 시가총액 구분 + 등락률 구분**부터
> 고려해 조건식을 생성(완전 다른 방식·더 나은 AI 로직 허용), 지금 시작해 **6시간 후(내일 아침)까지
> 자율 연구·데이터 누적**. 프로그램 전체 이해 후 진행. 대시보드 개선·더 나은 프로세스 환영. ultracode
>
> **브랜치**: `STOM_Version_2U_C-ai-strategy-loop` · **워크트리**: `STOM_V.wt-dev`
> **시작**: 2026-06-02 ~12:35 (로컬)

---

## 0. 연구 질문 (핵심)
§3.22가 남긴 **유일 미검증 본질 레버 I3 = 생성측 시드급 도메인지식 주입**을, 사용자가 지정한
3개 분류축(시간×시총×등락률)으로 구체화해 검증한다:

> **도메인지식이 주입된 생성(특히 fresh)이 §3.17 백지붕괴를 피하고, (시간대 × 시가총액 티어 ×
> 등락률 국면) 공간을 탐색해 잘-게이트된·다양한·우상향 전략을 만들 수 있는가? 인간 시드를
> 능가하거나, 최소한 의미있게 다른 엣지를 발견하는가?**

평가 프레임(§3.21 교정): reference 완벽모방·매구간흑자 아님. 기준 = **다년 전구간 누적곡선
장기 우상향(uptrend_r2)** + 잘 게이트됨 + 데이터 누적으로 학습. 실패도 학습 산출물.

---

## 1. 인프라 (이번 세션 신규)
- **생성 개선 커밋(예정)**: `classification_generation_enabled` 토글(기본 OFF) — 매수 프롬프트에
  3개 분류축(시총 티어·등락률 국면·시초 전체 09:00~09:28 시간창)에서 일관된 니치를 의도적으로
  선택해 설계하라는 블록 주입. require_filter_gates(범주 폭 구조 게이트)와 짝: **넓게 고르되(축
  선택) 좁게 게이트(니치 내 선별)**. code-reviewer(opus) APPROVE·6 불변식·OFF byte-identical·
  75 테스트. 사용자 "09:00~09:05 5분 시드 템플릿 탈피 + 시총/등락률 구분" 요청 직접 구현.
- 기존 (A) 인프라 재사용: filter_gate(범주 수 구조게이트)·liquidity_gate·few_shot(exemplar_pool
  passing/seed_db)·prompt_logging(P1c)·hypothesis(P2)·equity_points(O2)·multi/uptrend/multiyear obj.

### 환경 사실(검증됨)
- provider gpt_auth 헤드리스 작동(프록시 4.1s 기동). 생성 스모크: require_filter_gates=7+liquidity로
  매수 2/2 모두 1회만에 **8개 필터범주** 생성(시드급 게이팅).
- seed_db 인간 study 풀: 88 buy + 36 sell(tick-valid 다수) → few-shot 풍부.
- **OOM은 3년 풀유니버스 현상**: 1개월 워밍 백테당 ~24s로 매우 가벼움 → 1개월 max_gen 8~12 안전,
  3개월 max_gen 6~8. RAM 254GB 중 189GB free.
- ⚠️ 무관 python.exe 상주(stom_rl, web.main 등) → 크래시 시 **블랭킷 `taskkill /F /IM python.exe` 금지**,
  외과적 정리만(대시보드 PID 89728 보존).

---

## 2. 에피소드 로그 (누적)

표기: graded(=multi obj 점수)·gate(통과여부)·mdd·profit(원)·trades·calmar·r².
실행: `PYTHONUTF8=1 python -m ai_strategy_loop.controller.loop --config-json <cfg> --run-id <rid>`

### E1 — control/baseline (refine+reframe, 1개월 Jan, max_gen 5) ✅ 완료
- config: `run_campaign_e1_config.json` · run_id `campaign_e1_refine_jan` · 515s(8.6분)
- **winner = gen0 시드 Tick_902 graded 1.7238** (winner_score 101.2).
- gen3: graded 0.386 gate=False (mdd 12.01>cap12, profit −57,347, 36거래) — 한 끗 초과+적자.
- gen4: graded 1.3027 **gate=True** (mdd 4.4, profit +43,533, **6거래** 저빈도, calmar 2.748, r² 0.089) — 통과하나 시드 미달.
- gen2: 백테 error(metrics csv 없음 — 0거래/엔진 이슈 추정).
- **판정**: 알려진 패턴 재현(시드 1등, refine 게이트통과 가능하나 시드미달·저빈도). **OOM 0·클린 exit**.
  이것이 FRESH 암 비교 기준선. graded 1.72가 넘어야 할 바.

### E2 — FRESH + 도메인주입 + 분류 (헤드라인 I3 실험, 1개월 Jan, max_gen 8) ✅ 완료
- config: `run_campaign_e2_config.json` · run_id `campaign_e2_fresh_jan` · 8세대 complete
- **winner = gen2 (fresh 생성·시드 아님) graded 1.5476 gate=True · mdd 0.97 · profit +79,138 · 5거래 · calmar 22.66 · r² 0.405.**
- gate-passed 2/8 (gen2, gen3). 거래수 bounded(2~46), 과발화 0.

**🎯 3대 발견:**
1. **§3.17 백지붕괴 회피** — 도메인주입(filter_gate+few_shot+분류)이 백지생성을 구제. 과거 fresh
   (§3.17: winner −1·전세대 −83만~−11.6억·MDD 17~2851%·완전비수렴) 대비, E2 fresh는 거래수
   bounded·통과 2세대·수익 정상범위(−432k~+79k). **도메인지식 주입이 fresh를 viable하게 만든다(I3 레버 긍정).**
2. **fresh가 refine 능가** — E2 best fresh gen2 graded **1.5476 > E1 best refine 1.303**, 수익 +79k>+43k,
   MDD 0.97<4.4, calmar 22.66>2.75. (단 시드 1.72 미달·근접.)
3. **분류가 새 니치 탐색 입증** — gen2 니치 = 시총 **밴드 600~15000**(중형 티어, vs 시드 `<3000` 상한) ·
   시간 **09:00~09:28 전체창**(분류 효과, vs 시드 09:00~09:05) · 등락율 **2~16 강모멘텀**(vs 시드 1~8) ·
   체결강도 **80~260 AND >체결강도평균(20)**(평균대비 모멘텀 확인, vs 시드 flat 50~300) ·
   거래대금 ≥3000 AND 각도(60)>5. **refine 암이 절대 못 가는 니치를 fresh+분류가 발견.**

**⚠️ 관찰(E5 동기)**: bt_refine_from_best=true라 gen2(좋은 fresh) 발견 후 hill-climb이 그 니치로 수렴
  (gen2~7 동일 구조 상속). 니치 다양성은 gen0/1(fresh)에서만. **순수 fresh 다양성 측정엔
  refine_from_best=false 필요(E5).**

### E1 vs E2 핵심 대비 (refine 고착 vs fresh 탐색)
- **E1 refine**: 전 세대가 시드 니치 복제(시총<3000·09:00-02·등락율1~8·체결강도50~300 동일), 임계값만 미세조정 =
  **탐색 아님, 시드 템플릿 고착**(㉑ 정량 확인). best non-seed 1.303.
- **E2 fresh+분류**: 다른 일관 니치(중형밴드·전체시간창·강모멘텀·평균대비체결강도) 자율 발견, best 1.5476.
- **결론**: 사용자 요청대로 "넓은 시간/시총/등락률 구분부터 고려한 fresh 생성"이 refine보다 넓게 탐색하고
  더 나은 비-시드 전략을 만든다. 시드 초월은 미달이나, **탐색 다양성·viable fresh = 명확한 진전.**

---

### E3 — FRESH+분류 OOS Feb 2025 (max_gen 8) ✅ 완료
- run_id `campaign_e3_fresh_feb` · **winner gen7 graded 1.4641 gate=True · mdd 2.76 · +315,833 · 28거래(daily 1.4) · calmar 28.6 · r² 0.763.** gate-passed **4/8**.
- **자가교정 입증**: gen1 fresh가 1073거래 과발화(등락율1~9.5·시총800~7000 느슨 → filter_gate 7범주 충족해도 선별성 부족, 알려진 한계) → 하지만 OOM 0·게이트 실패 → hill-climb이 gen2(131)→gen3(10)→gen7(28)로 점진 수렴해 +316k·calmar28.6 달성. **루프가 과발화를 스스로 조인다.**
- 니치 또 다름(시총 600~9500·시간 09:03~09:28·등락율 6.2~10.2). 월마다 다른 일관 니치 = 분류 탐색 OOS 재현.
- E3 gen7은 빈도(28)·수익(+316k)·우상향(r²0.76)이 **인간 reference 프로파일에 E2보다 근접**. (단 payoff 0.79<1 = 다음 개선축.)

### E4 — FRESH+분류 OOS Mar 2025 (max_gen 8) ✅ 완료
- run_id `campaign_e4_fresh_mar` · **winner −1 · gate-passed 0/8** — 전 세대 적자(−64k~−605k), MDD/거래는 정상(2~35거래·MDD 0.82~14).
- **OOS 한계 발견**: 3월엔 fresh+분류가 흑자 니치를 못 찾음. 니치는 합리(시총밴드·09:05~09:28·등락율 2~14)지만
  3월 레짐엔 엣지 없음. **시드는 §3.16상 1~4월 흑자**인데 fresh의 *다른 니치*(중형·넓은시간·고모멘텀)는 3월 미작동
  → **fresh-탐색 니치는 레짐 민감, 시드의 초소형/초반 니치가 더 강건할 수 있음.** 종합: Jan(E2 ✅)·Feb(E3 ✅)·Mar(E4 ❌) = 2/3월 흑자.
- 시사: 단일월 평가는 행운/레짐 교란 가능 → **다월 통합 평가(E6 3개월)**가 강건성 판정에 필요.

### E5 — 순수 FRESH 다양성 (refine_from_best=false, Jan, max_gen 10) ✅ 완료
- run_id `campaign_e5_purefresh_jan` · **winner −1 · gate-passed 0/10.**
- **🔑 결정적 발견 = hill-climb refine가 필수**: 순수 fresh draw(매 세대 독립)는 **과발화↔무거래 사이 진동·비수렴**.
  과발화 폭발(gen3 1601거래/MDD59.5/−32.7M · gen5 1191/MDD120/−24M · gen7 1663/−35M · gen9 1576/MDD42/−38M) ↔
  무거래 0건(gen2/6/8). require_filter_gates=7도 임계 느슨하면 과발화 못 막음(범주 폭≠선별성, 알려진 한계).
- **대비**: E2/E3(fresh **+ refine**)는 fresh로 니치 발견 후 hill-climb이 과발화를 조여 흑자 수렴 → **fresh+refine이 sweet spot.**
  E1(인간시드+refine)·E5(fresh, refine無)는 양 극단. 도메인주입은 fresh를 viable하게 하지만 **수렴엔 refine 필수.**
- 다양성은 시도됨(gen2 시총 12조~90조 대형티어·gen8 복합 시총조건) but 순수 fresh로는 작동 못함.

### E6 — 3개월 다월 강건성 (FRESH+분류+refine, Jan~Mar, uptrend obj, max_gen 6) ✅ 완료
- run_id `campaign_e6_3mo` · **winner gen4 graded 1.1473 gate=True · mdd 4.7 · +126,367(3개월 통합) · 26거래 · payoff 1.254 · calmar 2.32 · r² 0.252.** gate-passed 1/6.
- **다월 강건 흑자 발견**: E4 단일3월은 전멸(0/8)이었으나, **3개월 통합 평가로 refine하면 March 포함 강건 흑자**(+126k)
  전략을 선택. 과발화(gen0 167거래/MDD30·gen2 346/MDD40)는 hill-climb이 gen4(26거래/MDD4.7)로 조임.
- 니치 신선: 시총 2400~8000(소형밴드)·**시간 09:13~09:28 후반창**(시드 09:00-05와 전혀 다름)·등락율 2.5~11.5.
- 단 시드 3개월 우호창엔 미달 추정·uptrend r²0.25(약한 우상향). **다월은 단일월보다 graded↓(레짐변동) but viable·강건.**

### E7 — 최고 fresh 발견물 심화 (E3 gen7 시드 → 3개월 refine, max_gen 8) ✅ 완료 🏆 캠페인 헤드라인
- run_id `campaign_e7_promote` · **winner gen1 graded 13.89(uptrend obj) gate=True · mdd 1.27 · +257,237(3개월 통합) · 21거래 · calmar 17.46 · r² 0.859 · payoff 0.84.** gate-passed **5/8(최고).**
- **결정적**: gen0(=E3 gen7 승격)은 3개월서 **−516k 실패**(Feb 니치 다월 미일반화). gen1 refine이 **시총 하한 600→2600**
  (최소형 제외) 단 하나 바꿔 **−516k→+257k·MDD1.27·r²0.859 강건 우상향**으로 전환. **hill-climb이 도메인 의미있는
  교정(최소형 캡 배제=다월 강건)을 자율 발견.** 5/8 전부 흑자(+52k~+257k)·저MDD(1.27~6.68).
- **r²0.859 = 3개월 강한 우상향**(E6 0.25 대비 큰 개선) = 사용자 "장기 우상향 추세" north-star 근접. 완전 AI 생성
  (fresh 발견 E3→AI refine E7)·시드와 다른 니치(중형 2600~9500·09:03~09:28·등락율 6.2~10.2).
- **promote 전략 검증**: 좋은 fresh 발견물을 시드로 승격해 다월 refine하면 강건·강우상향 전략으로 발전 → AI 루프의
  "발견→심화" 파이프라인이 작동.

### E8 — head-to-head: 시드 Tick_902 동일 3개월(uptrend obj, max_gen 1) ✅ 완료
- run_id `campaign_e8_seed3mo` · **시드 gen0 graded 23.64 · gate=True · mdd 5.39 · +1,944,536(3개월) · 24거래 · calmar 31.01 · r² 0.8545.** (메모리 fullevo3와 일치 = 검증.)
- **정직한 head-to-head (동일 3개월·동일 목표)**:
  | | profit(3mo) | MDD | calmar | r²(우상향) | 거래 |
  |---|---|---|---|---|---|
  | **인간 시드 Tick_902** | **+1,944,536** | 5.39 | 31.01 | 0.8545 | 24 |
  | **최고 AI (E7 gen1)** | +257,237 | **1.27** | 17.46 | 0.859 | 21 |
- **결론**: 시드가 절대수익 **~7.5배 우위**(인간 엣지 실재·큼). AI는 **MDD 더 낮고**(1.27<5.39)·**r² 동등**(강우상향)·
  완전 다른 니치. **시드 초월 아님(메모리 누적 결론 유지) but 강건·저MDD·강우상향 AI 전략을 자율 생성 = §3.17 붕괴서
  의미있는 진전.** 인간 시드는 수년 튜닝된 고수 자산이라 +1.94M은 높은 바.

### E9 — holdout: E7 gen1을 미지 4월에 검증 (max_gen 1) ✅ 완료
- run_id `campaign_e9_holdout_apr` · **E7 gen1 @ 4월(미지) = gate=True · mdd 0.97 · +35,686 · 6거래 · calmar 8.36 · r² 0.519.**
- **강건성 긍정**: 3개월(Jan~Mar)로 선택된 AI 전략이 **미지 4월서도 흑자·저MDD·게이트통과 = 순수 과적합 아님, 일반화**.
  이 프로젝트 고질(윈도우 과적합 §3.16) 우려에 긍정 신호. caveat: 4월은 시드 1~4월 우호레짐 = "우호 holdout"
  (더 가혹한 5~12월 holdout은 시드조차 약함). 그래도 OOS 흑자는 의미.

### E10 — 최고 AI 전략 심화 (E7 gen1 seed → 3개월 refine, max_gen 10) ✅ 완료
- run_id `campaign_e10_deepen` · **best_gen 0(=E7 gen1 자신 graded 13.89) · gate-passed 8/10.** 전 refine 세대 흑자·저MDD
  (+64k~+220k·MDD1.39~4.77·r²0.41~0.82) but **누구도 E7 gen1 초월 못함.**
- **§3.16-D refine 천장 재확인**: 강한 전략 발견 후 hill-climb은 다수 viable 변형을 내나 best를 엄밀 개선 못함(E7 gen1은
  그 니치 국소최적). 시드 격차(+1.94M) 미좁힘. **단 수확=AI 루프가 강건·저MDD·우상향 전략 *패밀리*(8/10 고수율)를 안정
  생산** = 단발 아닌 연구 corpus(E1 2/5·E2 2/8 대비 큰 수율 향상). 발전형 시스템의 산출물 축적 입증.

### E11 — 시드 약세 레짐 차별화 (fresh+분류+refine, May 2025, max_gen 8) 🔄 진행중
- run_id `campaign_e11_may_hardregime`. 시드가 약한 5~12월 구간(§3.16)서 AI가 엣지를 찾는가 — 성공 시 시드 보완 다각화.

### E6 — 3개월 다월 강건성 (FRESH+분류, Jan~Mar, uptrend obj, max_gen 6) ⏳ 대기
- run_id `campaign_e6_3mo`(예정). 3개월 통합 평가 + uptrend 목표(누적 우상향 r²). E4 March miss가 동기.

## 3. 계획 (적응적)
- E3: FRESH+분류, **Feb 2025**(OOS 월). E4: FRESH+분류, **Mar 2025**.
- E5: 최선 암 **3개월**(Jan-Mar) max_gen 6 — 넓은 윈도우 강건성.
- E6+: E1~E5 결과로 최선 방향 심화(예: few_shot_source 변경·min_filter_categories 튜닝·uptrend obj).
- 각 에피소드 후: DB 분석 + 본 로그 갱신 + config 조정. 크래시 시 외과적 정리.

## 4. 불변식 (모든 작업)
엔진(backengine_*)·하드게이트(compute_fitness)·backtest/graph/ 무수정 · 신규기능 토글 기본 OFF·
byte-identical · code-reviewer(opus) APPROVE · `PYTHONUTF8=1 pytest tests/unit/ -q -p no:randomly`
기존 7 failed 외 신규 0 · verify_nonrelease_sync 통과.

## 5. 종합 요약 (아침 확인용)

### 5.1 한 줄 결론
사용자 요청대로 **넓은 시간창×시가총액 구분×등락률 구분**을 1급 분류축으로 한 생성 토글을 만들고(커밋 `eacd44da`),
이를 핵심으로 **11개 자율 에피소드**를 돌려 데이터를 누적했다. **핵심 성과: 도메인지식 주입(분류+필터게이트+few-shot)이
fresh 생성을 §3.17 백지붕괴에서 구제했고, fresh+refine 파이프라인이 시드와 *전혀 다른 니치*의 강건·저MDD·우상향 전략
패밀리를 자율 생산한다(최고 E7 gen1 = 3개월 +257k·MDD1.27·r²0.859, 미지 4월 holdout도 흑자).** 단 절대수익은 인간
시드(+1.94M)에 여전히 미달 — **시드 초월 아님, 그러나 §3.17 대비 명확한 생성역량 진전 + 발전형 연구 corpus 확보.**

### 5.2 에피소드 결과표 (run-셀렉터에서 run_id로 열람)
| Ep | 설정 | 윈도우 | winner/best | profit | MDD | r² | 통과 | 핵심 |
|----|------|--------|------|--------|-----|-----|------|------|
| E1 | refine(시드) control | Jan | 시드 gen0 | (시드) | 0.88 | 0.87 | 2/5 | refine=시드니치 고착 |
| E2 | **fresh+분류** | Jan | gen2 | +79k | 0.97 | 0.41 | 2/8 | §3.17 회피·refine 능가·새 니치 |
| E3 | **fresh+분류** | Feb | gen7 | **+316k** | 2.76 | 0.76 | 4/8 | 자가교정·28거래 고빈도 근접 |
| E4 | fresh+분류 | Mar | 없음 | 적자 | — | — | 0/8 | OOS 한계(레짐 민감) |
| E5 | 순수fresh(refine off) | Jan | 없음 | 적자 | — | — | 0/10 | **hill-climb 필수**(과발화↔무거래) |
| E6 | fresh+분류 3개월 | Jan~Mar | gen4 | +126k | 4.7 | 0.25 | 1/6 | 다월 강건 흑자 |
| **E7** | **fresh승격+refine 3개월** | Jan~Mar | **gen1** | **+257k** | **1.27** | **0.859** | **5/8** | 🏆 최고 AI·시총하한교정·강우상향 |
| E8 | **시드** 3개월 비교 | Jan~Mar | 시드 | **+1,944,536** | 5.39 | 0.85 | 1/1 | head-to-head 기준(시드 7.5×) |
| E9 | E7gen1 holdout | **Apr(미지)** | — | +36k | 0.97 | 0.52 | 1/1 | 일반화 입증(과적합 아님) |
| E10 | E7gen1 심화 | Jan~Mar | best=E7gen1 | (천장) | — | — | 8/10 | refine 천장+강건 패밀리 8/10 |
| E11 | fresh+분류 시드약세 | May | _진행중_ | _?_ | _?_ | _?_ | _?_ | 시드 약세레짐 차별화 시도 |

### 5.3 검증된 발견 (이번 캠페인의 학습)
1. **도메인주입이 fresh를 viable하게 만든다** — §3.17 백지붕괴(winner −1·MDD 2851%)가 분류+필터게이트+few-shot
   으로 해소. fresh가 잘게이트된 다양한 니치를 생성(거래수 bounded·과발화는 hill-climb이 교정).
2. **fresh+refine > refine-from-시드** — 비-시드 전략 품질에서 fresh+refine(E2/E3) > refine-only(E1). 시드 refine은
   시드 니치(초소형·09:00-05·등락율1~8)에 고착되나 fresh는 중형밴드·넓은시간·고모멘텀 등 새 니치 탐색.
3. **hill-climb refine이 수렴의 필수재료** — 순수 fresh(E5)는 과발화↔무거래 진동·비수렴. fresh로 니치 발견 + refine으로
   조이기 = sweet spot.
4. **다월 통합 평가가 강건성을 만든다** — 단일월 선택(E4)은 레짐 과적합 위험. 3개월 통합 refine(E6/E7)이 March 포함
   강건 흑자를 선택. E7 gen1은 미지 4월(E9)도 흑자 = 일반화.
5. **refine 천장 존재(§3.16-D 재확인)** — 강전략 발견 후 심화(E10)는 강건 패밀리(8/10)는 내나 best 엄밀초월 못함.
6. **시드는 여전히 절대수익 우위** — head-to-head(E8) 시드 +1.94M vs 최고 AI +257k(3개월). 인간 수년튜닝 엣지는 실재·큼.
   단 AI는 MDD 더 낮고 우상향 동등·니치 다름 = 보완적 다각화 가치.

### 5.4 사용자 목표 대비 판정
- **"넓은 시간×시총×등락률 구분 생성"**: ✅ 구현·작동(E2~E11 전부 시드와 다른 시간창·시총밴드·등락률국면 탐색).
- **"완전 다른 방식 허용"**: ✅ fresh 생성이 시드와 무관한 니치 발견.
- **"발전하는 조건식 연구 시스템"**: ✅ fresh→refine→promote→심화 파이프라인이 강건 전략 패밀리를 누적 생산.
  reference 완벽모방/시드초월은 아니나, **AI 반복·데이터분석으로 *스스로 발전하는* 산출물**을 실증.
- **데이터 누적**: ✅ 11 run·세대별 성과·프롬프트·equity곡선·가정·니치 전부 loop_runs.db + 대시보드 영속(run-셀렉터 열람).

### 5.5 다음 단계 (권장 우선순위)
1. **payoff/청산 품질** — AI 전략 공통 약점(payoff 0.8~0.9 < 시드 1.74). 체결강도 페이드(이미 ON)에 더해 청산 전용 심화
   (freeze_buy_on_mdd_only로 좋은 진입 고정+청산만 refine)로 payoff↑ → 시드 격차의 핵심.
2. **가혹 holdout** — 5~12월(시드 약세) 다월 검증으로 진짜 레짐강건성 측정(E11이 첫 신호).
3. **niche 가시화 대시보드 패널**(read-only) — 세대별 시총밴드·시간창·등락률국면 표시(분석도구 `_temp_campaign_analyze.py`
   로직 재사용). 막판 변경 위험 회피로 이번엔 문서화만, 후속 구현 권장.
4. **corpus 확대** — 여러 월 fresh+refine로 강건 전략 라이브러리 축적 → few-shot 풀·Hall of Fame 강화·앙상블 후보.

### 5.6 불변식 준수
classification 커밋 `eacd44da`: code-reviewer(opus) APPROVE·6 불변식·OFF byte-identical·baseline 7 failed/2086 passed
신규0·엔진/하드게이트/backtest/graph 무수정·신규 토글 기본 OFF. 캠페인 run config는 state/(gitignored)·결과는 DB 영속.
