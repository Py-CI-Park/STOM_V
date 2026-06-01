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

### E2 — FRESH + 도메인주입 + 분류 (헤드라인 I3 실험, 1개월 Jan, max_gen 8) 🔄 진행예정
- config: `run_campaign_e2_config.json` · run_id `campaign_e2_fresh_jan`
- seed_null 백지생성 + classification ON + require_filter_gates(7) + liquidity_gate + few_shot(seed_db)
  + 시간분산 + 분산매매 + mdd제어. E1과 동일 윈도우(직접 비교).
- 관전 포인트: ①§3.17 백지붕괴(비수렴·과발화·OOM) 회피하는가 ②잘게이트된 다양한 니치 탐색하는가
  ③시드 graded 1.72 근접/능가하는가 ④동시보유·빈도 이동.

---

## 3. 계획 (적응적)
- E3: FRESH+분류, **Feb 2025**(OOS 월). E4: FRESH+분류, **Mar 2025**.
- E5: 최선 암 **3개월**(Jan-Mar) max_gen 6 — 넓은 윈도우 강건성.
- E6+: E1~E5 결과로 최선 방향 심화(예: few_shot_source 변경·min_filter_categories 튜닝·uptrend obj).
- 각 에피소드 후: DB 분석 + 본 로그 갱신 + config 조정. 크래시 시 외과적 정리.

## 4. 불변식 (모든 작업)
엔진(backengine_*)·하드게이트(compute_fitness)·backtest/graph/ 무수정 · 신규기능 토글 기본 OFF·
byte-identical · code-reviewer(opus) APPROVE · `PYTHONUTF8=1 pytest tests/unit/ -q -p no:randomly`
기존 7 failed 외 신규 0 · verify_nonrelease_sync 통과.

## 5. 아침 요약 (06-03 채울 자리)
_(캠페인 종료 시 종합: 에피소드별 결과표·I3 레버 판정·다음 단계·MEMORY.md 갱신)_
