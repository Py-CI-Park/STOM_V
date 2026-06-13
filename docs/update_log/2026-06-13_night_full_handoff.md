# 전체 핸드오프 (2026-06-13 밤 21:20) — compact 후 어디서든 재개

> 이 문서 하나로 다음 세션/에이전트가 오늘 전체 맥락을 복원하고 즉시 이어간다.
> 전임: `2026-06-13_afternoon_t2c3_handoff.md` · `2026-06-13_paper_operation_setup.md`.
> 작업트리 클린. 오늘 연구 커밋 ~30건 + 외부 대시보드 PR #43~46 머지 통합.

## 1. 오늘 도달점 (한눈에)

1. **V6 운용 결정 완료** — 2-전략 포트폴리오(THETA+T2C3) `complement` 채택,
   `decisions.jsonl` 기록 + 정식 결정 카드(`2026-06-13_v6_portfolio_decision_card.md`).
2. **신규 챔피언 T2C3 발굴** — "09:25까지 매수" 시간확장 변형이 V1~V5 완주,
   실전검증(OOS·WF·슬리피지)에서 THETA를 능가(train만 열위 = 일반화 우월).
3. **운용 전환 준비 완료** — M4 모니터 도구 + 페이퍼 사전선언(종료조건·리스크).
4. **대시보드 SPA 6탭 통합**(외부 PR #46) — 운영/연구실/리서치프로/결정 인페이지 탭,
   결정 페이지에 레짐·부활·**추천 포트폴리오 패널** 정상 표시(버그 머지로 해소).
5. **비상관 니치 탐색 한계 확정** — LLM 11~13세대 전멸, 시드 모멘텀 코어가 유일 안정 알파.

## 2. 명예의 전당 — 사용 가능 조건식 (수익률 상세)

### 🥇 THETA_seed_902905_06_B/S (전략 DB) — train·통계 최강, V1~V5 완결
시드 + cap_max 2500 · take_hard 9 · trail_start 4 (09:00~05 소형주 모멘텀)
- train 2023~25: **+10,965,479 / MDD 10.04 / 272건 / payoff 1.53 / 3개년 흑자**
- OOS 2022: +2,097,751(55건) · OOS 2026: +164,602(9건) · V4: +1.4%(2창 기권)
- V1 DSR 0.945 · V2 플라시보 12종 압도 · V5 슬리피지 2틱(2026 단독 1.21)

### 🥇 T2C3_B/S (전략 DB) — 실전검증 최강, V1~V5 완주 (오늘 발견)
THETA θ + 제3분기 09:05~09:15(시총 4000억+ 대형주 반전, burst 4.0)
- train 2023~25: +9,866,240 / MDD 11.30 / 356건 / payoff 1.66 (연 2023 +408만·2024 +437만·2025 +142만)
- **OOS 2022: +2,593,894(60건) — THETA +24%** · **OOS 2026: +400,701(15건) — THETA +143%**
- **V4: +10.6% 비열등, 전 창 적격(THETA보다 강함)** · V1 DSR 0.802 · V2 무작위 8종 -7~18.6억 압도 · V5 2.43틱
- 동결분: `.omo/evidence/tmap-walkforward/t2c3_freeze_20260613/` · 검증표: `t2c3_verdict_findings.md`

### 🥇 포트폴리오 (THETA 50% + T2C3 50% 균등) — V6 채택
- M4 baseline 48개월: **+13,044,334 vs 시드 +10,550,472 (+24%, 경보 없음)**
- train 상관 0.92(분산이득 7.3% 미미) — 가치는 **레짐 상보성**(2026 위축장 T2C3 헤지)
- 운영금: 종목당 5백만원 배팅(저빈도 일 0.4~0.5건). 실전 기대는 OOS 수준(연 50%대)으로 보수적.

### 보류/기각 (지금 사용 불가)
HOLD: R2R3_B(V4 기권)·g20/g13(미검증). 부활 레지스트리 4: C7·EXIT2C·EXIT2NA·g9.

## 3. 오늘 전체 작업 결과

### R-체인 (시드 재연구)
R1 부검(알파9·데드웨이트3[VI회피 발동0]·개선3) → R5C 비가산 기각 → R2 burst2.0
발견(+11.13M/6.78) → R3 9/9 mesa → R5 R2R3_B HOLD(V4 4창 기권) → R4 미니멀 기각.
상세: `r1_ablation_findings.md`

### T-트랙 (09:25 진입 연장) — ★최대 성과
T1 단순연장 열위 → T3 부검(09:05+ 알파=시총2500+ 대형주 반전) → T2 차등구조 →
**T2C3 V1~V5 완주, 신규 챔피언**. 로드맵: `2026-06-13_entry_extension_and_min_roadmap.md`

### M-트랙 (min ~15:00)
M1 36셀 지도(P4강도급등만 생존·12시대 손익분기) → M2 결합 no-go(거래폭발).
min 전 세션 안정 알파 없음. 상세: `m1_primitive_findings.md`

### LLM 루프 11~13세대 (비상관 니치 — 전멸)
11세대 대형주후반(체결강도평균 3회 타임아웃) → 12세대 다이어트(밀도 양극단 폭발/0)
→ 13세대 소형주 돌파전(돌파실패 비용·거래과다). 교훈: `llm_context_failure_lessons.md`
(13세대까지 알파 0, 깔때기 정적 규칙 6종 자산화).

## 4. 시스템 자산 (오늘 추가/갱신)

- **M4 모니터**: `ai_strategy_loop/scripts/gen_m4_monitor.py` — 포트폴리오 vs 시드 월별
  championship_report. 실행 `python -m ai_strategy_loop.scripts.gen_m4_monitor`.
- **페이퍼 사전선언**: `2026-06-13_paper_operation_setup.md` (종료조건 3개·리스크 공시).
- **대시보드 SPA 6탭**(PR #46): `/ui/` 인페이지 탭, 결정 페이지 = `dashboard-pages.jsx`
  window.VerdictPanel. /portfolio_verdict·/regime_report·/revival_registry 엔드포인트.
- **깔때기 정적 규칙 6종**: 타입가드·신호밀도·무인자함수·잔량과다호출·호출형 화이트리스트
  ·윈도우함수 다중호출 — `gen_template_hypothesis.py` validate_hypothesis.
- **스모크 2-분기 규약**: 2025Q1 + 2023Q2(`smoke-2023q2-config.json`), min 2025-05+2025-09.

## 5. 내일 아침(~09:00)까지 계획 (compact 후 이어서 실행)

> **[2026-06-13 23:05 실행 완료]** 14~17세대 전부 측정·전멸(no-go) → 동결.
> 결과·인프라 수확·다음 단계: **`2026-06-13_night_gen14_17_exhaustion.md`** 참조.
> 아래 표는 당시 계획(이제 실행됨, 이력용).

> 정직: 비상관 니치 13세대 전멸 — 14~17세대는 살아있는 단서 4개 소진이고
> 성공 확률 낮음. 기각이어도 교훈 누적. 단서 소진 후엔 무한 반복 회피·동결.

| 시각 | 작업 |
|---|---|
| 14세대 | F07 burst 극단(8배+×좁은 창) 생성→2-분기 스모크 |
| 15세대 | exit2 레짐 조건부(고변동 게이트) |
| 16세대 | min LLM(M1 P4 지도 컨텍스트) — min 2-분기 스모크 |
| 17세대 | 전일동시간비 주신호 변형 |
| 결산 | 14~17 교훈 누적 + go 후보 시 본 스윕→P-A→OOS+V4 |
| 매시 :43 | 워치독(health·배치 정체) |
| ~08:30 | 아침 종합 핸드오프 |

재개 명령(compact 후): 위 14세대부터 —
`PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_template_hypothesis --provider gpt_auth --write --max-retries 3 --principles "<단서별 방향>"` → 주입 → 2-분기 스모크 → 판정 → 교훈 등재.

## 6. 재개 절차 (어느 에이전트든)

1. 이 문서 → `t2c3_verdict_findings.md` · `r1_ablation_findings.md` ·
   `llm_context_failure_lessons.md` · `m1_primitive_findings.md` 순 읽기
2. `git log --oneline -15`(HEAD `1874fb5a`+) · `PYTHONUTF8=1 python -m pytest tests/unit/ -q`
   (기대: 고정 실패 7건 외 통과 — dashboard 415 통과 확인됨)
3. 대시보드: `PYTHONUTF8=1 python -m ai_strategy_loop --port 8770` → `/ui/`(SPA 6탭)
4. 챔피언 아티팩트 = THETA(복원됨), T2C3 동결분 = `t2c3_freeze_20260613/`
5. M4 모니터: `python -m ai_strategy_loop.scripts.gen_m4_monitor`

## 7. 주의사항

- **gpt_auth 프록시**: LLM 세대는 127.0.0.1:18761 로컬 프록시 필요(매 호출 자동 기동
  시도하나 환경 닫히면 실패). 14세대~ 실행 전 가용성 확인.
- **워치독 크론(매시 :43)**: 세션 종속 — 새 세션이면 재등록 필요(점검 전용, git/엔진 무수정).
- **외부 대시보드 PR**: 오늘 #43~46(webbt-phase6~9)이 원격에서 머지됨 — 대시보드가 SPA로
  재구조화. 연구 백엔드(app.py portfolio_verdict 등)와 정합 확인 완료(415 테스트).
- **데이터 경계 고정**: tick 09:00~09:30 / min 09:00~15:19 — 확장 불가. 비상관 니치는
  신규 데이터 도착 후가 현실적(부활 6쌍+HOLD 3종 일괄 재평가 대기).
