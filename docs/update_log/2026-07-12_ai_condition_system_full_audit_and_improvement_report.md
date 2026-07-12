# 2026-07-12 AI 조건식 시스템 전수 검사 및 개선 보고서 (v2 — 코드·산출물 실물 재검)

> 대상: `STOM_Version_2U_C` 파생 전 계보(정본 `loop/process-research-pipeline`, HEAD `c5fa0341`) + alpha-lab 워크트리(`STOM_V.wt-alpha`).
> 전제: 연구 일시 중단 상태. 목적은 이어가기가 아니라 **문제·부족·개선점의 확정**이다.
> v2 성격: v1(문서 중심 검토)을 **코드·프롬프트 본문·상태 DB 실측·생성 조건식 실물**로 재검증한 판본. v1의 오류 2건을 §5에서 명시 정정한다.

---

## 0. 검사 커버리지 (v2에서 직접 열어 확인한 실물)

| 영역 | 직접 확인한 것 |
|---|---|
| 프롬프트 자산 | `utility/ai_agent/system_prompt/v1/` 7종 본문 전문(system_prompt·variables_reference·forbidden·examples·principles·constraints_checklist·idiom_dictionary), `rules.txt`, `strategy.txt` 예제 |
| 생성 조립 | `brain/prompt.py` 1,342줄 중 `build_messages` 본문 433줄 verbatim + 자산 배선 상수(`_SYSTEM_ASSETS`, `_FULL_STOM_SOURCE_ASSETS`) |
| 게이트 사슬 | `brain/generator.py`(PRE-SAVE), `brain/principle_gate.py` 존재·배선, `cli/condition_generator.py`(pack 검증·B-only·AST 지문) |
| 설정 실측 | `ai_strategy_loop/config.py`에서 생성 품질/탐색 토글 **19개 기본값 전수 확인** |
| 루프 본체 | `controller/loop.py` 3,323줄 구조(백테 경로·부검 3종·환류 5채널·증거 원장 배선) |
| 상태 DB 실측 | `loop_runs.db` SQL 조회(runs 506 / generations 5,124 / prompts 460 / 증거 4테이블 0행), `loop_strategies.db`(buy 6,310 / sell 6,212) |
| 생성 실물 | `AILOOP_follow12_gptauth_B2_seeded64_20260628_g6` 매수/매도 조건식 전문 |
| 채점 | `fitness/score.py` 863줄 구조(하드게이트/graded/exit-quality/dispersion) |
| 대시보드 | `dashboard/app.py` REST/WS 엔드포인트 ~50개 전수 목록 |
| 데이터 | `_database/` 전수 목록: tick 2022-03-23~2026-02-27(09:00~09:30, 29.7GB), min 2025-04-07~2026-02-27(풀세션, 1.46GB) |
| 워크트리/브랜치 | 워크트리 11개, 브랜치 ~90개, alpha-lab `docs/research` 트리(오늘자 엔진 검토 문서 포함) |
| 연구 기록 | 정본 핸드오프(07-11)·마스터 계획·실패 매트릭스 Family 1~8·전체 결과 분석(07-08 전문)·CL-R07 GO 기록 |

---

## 1. 한 줄 결론 (v2 확정판)

**조건식을 "복합적으로 잘 생성하는 능력"은 이미 증명돼 있다. 실물 산출(§3.4)이 그 증거다. 수익이 없는 원인은 생성력이 아니라 ①수익 검증 단계 미실행 ②탐색·품질 토글 19개 전부 기본 OFF인 채 정본 run 부재 ③전체 세대의 91%가 LLM이 아닌 결정론 격자 재생 ④blind OOS 프레임 부재 ⑤min 데이터 11개월 — 이 5가지의 결합이다.**

---

## 2. 자산 인벤토리

### 2.1 데이터 (`_database/`, 읽기 전용 확인)

| 자산 | 범위 | 평가 |
|---|---|---|
| `stock_tick_back.db` (29.7GB) | 2022-03-23~2026-02-27, **09:00~09:30만** | 유일한 4년 lane. 단 30분 창 |
| `stock_min_back.db` (1.46GB) | **2025-04-07~2026-02-27 (11개월)**, 09:00~15:19 | primary lane인데 다년 OOS 불가 — 최대 데이터 갭 |
| 일별 tick/min DB | 각 동일 범위 | subset·격리 실행용(CL-R07이 사용) |
| `strategy.db` | 시드 `Tick_B/S_902_905_Update_2` byte-동일 | 유일한 실배포급 골드 |
| subset DB (`state/`) | tick_subset 1.5GB·min_subset 291MB 등 | 스모크 인프라 완비 |

핵심 비대칭: **tick = 길지만 좁다(4년×30분), min = 넓지만 짧다(풀세션×11개월).**

### 2.2 시드/조건식 자산

| 자산 | 상태 |
|---|---|
| `Tick_902` (2022~2025 연속 흑자, r²0.90) | 골드. AI refine이 정직 OOS에서 이긴 적 없음 |
| 인간 reference 17개 (`docs/reference/STOM_Good_Results/`) | 북극성이지만 **스크린샷만 존재, 조건식 본문 시드 미등재** |
| repair composite survivor 15 / Plan D rank01~03 survivor (대표 R2-05: +554,624 / MDD 5.24 / daily 2.20) | seed passport 보존. full-period 선별 → OOS 창 누수, promotion 불가 |
| 적응형 레짐 타이밍 (2022~2026 진짜 OOS 위험조정 3.5배) | 검증 완료·`adaptive_timing_enabled=False` 분석전용 방치 |
| 백파인더 BandSpec (24,229행·129승자·lift 8.99) | 채굴 완료·**생성경로 미배선** |

---

## 3. 생성 파이프라인 해부 (코드 실물 기준)

### 3.1 프롬프트 자산 — 무엇이 실제로 주입되는가

`brain/prompt.py` 실측:

```
_SYSTEM_ASSETS = ("system_prompt.md", "variables_reference.md", "forbidden.md")
_FULL_STOM_SOURCE_ASSETS = (strategy.txt, rules.txt, system_prompt, variables_reference, forbidden, examples)
```

- **system 메시지에 항상 들어가는 것**: 역할 규약 + 화이트리스트 181 함수형 이름 + 금지 규칙(매도전용 변수의 매수 사용 금지, 안전 토큰, 환각 변수 금지). 견고하다.
- **치명적 발견**: 1주 전 추가된 도메인 지식 자산 3종 — `principles.md`(차트술사 구조론 P0~P15: 박스/추세 이분법·기능선·눌림·사건거래대금·갭 해석), `constraints_checklist.md`(CSC-01~14 기계 판정 규칙), `idiom_dictionary.md` — 가 **`_SYSTEM_ASSETS`에도 `_FULL_STOM_SOURCE_ASSETS`(연구 Context Pack)에도 포함되지 않는다.** 유일한 소비처는 `brain/principle_gate.py`(CSC-06/07/10 reject)인데 `principle_gate_enabled: bool = False`. 즉 **사용자가 말한 "시초 매매의 특성, 주식 거래 특성" 지식을 문서화까지 해놓고 LLM에게 한 글자도 보여주지 않는 상태다.** 이것이 v2 검사의 최대 단일 발견이다.

### 3.2 build_messages 실측 — 매수/매도 지침의 실제 품질

`build_messages` 본문(887~1315행) 직접 확인 결과:

- **매수(常時)**: 0거래 방지 가이드 + 보고서 우수전략 패턴(`_report_pattern_lines`).
- **매수(토글 ON 시)**: 필터 게이팅 7범주 AND 강제 가이드(`require_filter_gates`) → 3분류축 니치 선택(`classification_generation_enabled`) → 시간분산 넛지 → 패배 세그먼트 avoid(`segment_feedback`) → prefer 피처 힌트(`feature_importance_feedback`) → few-shot(변수값 복제 금지 명시). 설계 품질 높음.
- **매도(常時)**: give-back 70~88% 부검 사실 교육 + 트레일링/부분익절 + payoff≥1.1 목표 + **강제 종료 청산 필수(§④ "가장 흔한 실패 원인")** + 계산예산 간결성(§⑤). 상시 지침만으로도 상당히 풍부하다.
- **매도(토글 ON 시)**: MDD 억제 최우선 블록(타이트 손절·시간 손절·**체결강도 페이드 청산 — "보고서 19개 우수전략 중 18개가 사용"**) + edge_ratio 환류(손실 MAE 2.6배·최고익 20%만 실현).
- **seed-refine 경로**: "전면 재작성 금지, 1~2개 조건만 조정" + "유동성 게이트 삭제 금지 — 빼면 흑자가 깨진다" 같은 실패 경험이 각인된 지침.

**평가**: 프롬프트 공학 자체는 성숙 단계다. 문제는 이 블록들 대부분이 잠겨 있다는 것(§3.3)과, 구조론 지식이 미주입(§3.1)이라 LLM의 가설 어휘가 "필터 조합"에 갇혀 있다는 것 — 박스/눌림/리테스트/기능선 같은 **구조 문맥 가설**은 생성 공간에 사실상 없다(CSC-03이 정확히 이걸 위반으로 정의하는데, 그 게이트가 OFF다).

### 3.3 토글 기본값 실측 (config.py 전수)

전부 `False` 확인: `full_session_enabled`, `meta_seed_enabled`, `dispersion_prompt_enabled`, `mdd_control_enabled`, `exit_edge_feedback_enabled`, `segment_feedback_enabled`, `encourage_time_dispersion`, `require_filter_gates`, `few_shot_enabled`, `classification_generation_enabled`, `time_cap_bucket_generation_enabled`, `sparse_positive_prompt_enabled`, `exec_budget_prompt_enabled`, `report_principles_enabled`, `feature_importance_feedback_enabled`, `adaptive_timing_enabled`, `principle_gate_enabled`, (+ band/evidence 계열).

불변식 4(기본 OFF)는 옳다. 문제는 **이 토글들을 묶어 켠 "정본 연구 프로파일"로 완주한 다년 run이 존재하지 않는다**는 것 — 2026-06-03 핸드오프 §6-1이 최우선으로 못박은 그 작업이 5주째 미실행이다(그 사이 실행된 것은 토글 OFF 격자/배치 계열이 지배적).

### 3.4 생성 실물 검증 — "복합 생성 능력" 직답

`loop_strategies.db`에서 꺼낸 실제 LLM 산출(2026-06-28, gpt_auth seed-refine, 토글 ON 캠페인):

- **매수**: 공통 게이트 12범주(관심종목·시간창·초당거래대금·체결강도 밴드·시총 밴드·가격·등락율·고저평균대비등락율·**VI가격 가드**·라운드피겨·직전틱 상승·거래대금 급증비) 후 **시분초 <90200 / 90200~91500 두 국면으로 분기**해 국면별로 시가 갭 범위·양봉 위치·전일비·회전율·거래대금각도 창·호가압력 임계를 **다르게** 설정. 총 ~24개 조건의 계층 구조.
- **매도**: 시간 강제청산(92800) + 상한가 익절 + 하드 스톱(-1.8) + 시간 손절(260초) + 2단 트레일링(최고수익률 2.0/4.5 기준) + **체결강도 페이드**(직전 대비 하락·평균 0.8배) + 이평 이탈 — 7경로 청산.

**판정**: "조건식을 복합적으로 잘 생성하고 여러 가능성을 보는가?" — **생성 구조력은 인간 중급자 이상이다.** 시간대 국면 분기·호가/체결 오더플로우 결합·다단 청산을 자율 생성한다. 병목은 생성이 아니라 (a) 이런 세대가 전체의 소수라는 것(§4.2), (b) 임계값 숫자가 여전히 데이터 분포가 아닌 LLM 사전확률에서 나온다는 것(밴드 미배선), (c) bounded 창 통과 후 다년/OOS 강건성 검증이 없다는 것.

### 3.5 격자(lattice) lane — 실패의 실체

`cli/seed_lattice.py` + Family 1~3: 진입 family(momentum_breakout/prevday_active/strength_surge/volume_surge)×시간×size×strength 기계 조합 576개 → **go 0 / no_go 576, 주 사인 mdd_excess 479(87%)**. 이 lane은 LLM 생성이 아니고, §3.2의 청산 지식도 §3.1의 구조론도 적용받지 않은 **가설 없는 조합 폭발**이었다. 음성 기준선으로서의 가치만 남기고 재개 금지(확정 결론 `gate_relaxation_is_not_sufficient` 유지).

---

## 4. 상태 DB 실측 — 시스템이 실제로 한 일

`loop_runs.db` SQL 실측 (2026-07-12):

| 항목 | 값 | 해석 |
|---|---:|---|
| runs | 506 | 실험량 자체는 방대 |
| generations | 5,124 (status ok 4,897) | |
| gate_passed | 1,583 (31%) | **bounded 연구창 게이트** 통과 — 수익 증명 아님(GROUND-TRUTH #6 "게이트통과 ≠ 수익") |
| profit>0 | 1,782 (35%) | 우호창 포함 수치 |
| avg MDD(ok) | 80.5% | 게이트 cap 35의 2.3배 — MDD가 여전히 1차 사인 |
| **prompts** | **460** | **LLM 프롬프트가 기록된 세대는 전체의 ~9%. 나머지 91%는 격자/배치 결정론 재생.** |
| candidate_passports / feedback_envelopes / feedback_consumptions / run_receipts | **전부 0행** | CL-R04/R05 증거 원장이 정본 DB에서 **한 번도 미사용**(격리 CL-R07 sandbox에서만 사용) |

이 표가 "왜 효과가 없는가"의 정량 답이다: **"AI의 힘으로 대체한다"는 목표 대비, 실제 계산 자원의 9할이 AI가 아닌 결정론 격자에 쓰였고, 그 격자는 구조적으로 실패가 증명됐다.** 그리고 학습 사슬을 증명하는 증거 인프라는 만들어졌지만 정본 루프에 아직 꽂히지 않았다.

---

## 5. v1 보고서 정정 (정직 기록)

1. **"생성 프롬프트에 청산 설계 가이드가 없다" → 오류.** `build_messages` 매도 경로는 상시 give-back/트레일링/강제청산/payoff 지침을 포함하며, 토글 ON 시 체결강도 페이드·edge_ratio 환류까지 있다(§3.2). 정확한 문제는 "없다"가 아니라 **"강화 블록 2종이 OFF이고, MDD로 죽은 격자 lane은 이 지침의 적용 대상 밖이었다"**이다.
2. **"대시보드가 관찰만 하고 판정을 돕지 않는다" → 과장.** `app.py` 실측 결과 edge_ratio·feature_importance·adaptive_timing·tmap 히트맵·counterfactual·**freeze_mc(블록 부트스트랩 MC)**·portfolio_preview·strategy_diff·prompts 뷰어·ai_context_pack 등 판정 보조 API ~50개가 이미 있다. 실제 갭은 §6 P-9의 3가지(OOS 오버레이·프롬프트 A/B 성과 비교·증거 원장 뷰)와 frontend 번들 8파일 dirty 방치다.

---

## 6. 근본 문제 확정 목록 (v2, 우선순위순)

| # | 문제 | 실측 근거 |
|---|---|---|
| **P-1** | **수익 검증 단계 미실행.** CL-R08(60일 train40/val20)·R09(봉인 OOS/WF)·R10(인간 비교) 승인 잠금. "수익이 나는지 보는 실험"을 한 번도 안 함 | 마스터 계획 §CL-R, R09는 ~08월 중순 데이터 대기 |
| **P-2** | **AI 사용률 9%.** 세대 5,124 중 프롬프트 기록 460. 자원의 91%가 실패 증명된 결정론 격자에 소모 | §4 SQL 실측 |
| **P-3** | **도메인 지식 미주입.** principles/constraints/idiom 3종이 어느 프롬프트 배선에도 없음. principle_gate(CSC 강제)도 OFF. 구조 문맥(박스/눌림/리테스트) 가설이 생성 공간에 부재 | §3.1 상수 실측 |
| **P-4** | **토글 19개 전부 OFF + 정본 연구 프로파일 run 부재.** 검증된 프롬프트 블록·환류 5채널·적응형 타이밍이 전부 잠자는 중 | §3.3 config 실측 |
| **P-5** | **증거 원장 0행.** CL-R04/05 인프라가 정본 loop_runs.db에서 미사용 → "무엇을 배웠는가"가 여전히 문서 서사에 의존 | §4 실측 |
| **P-6** | **시드 자산 미활용.** reference 17 본문 미등재(few_shot_source='seed_db'는 Tick_902 계열만 실효), 백파인더 밴드 미배선 → 임계값이 데이터 아닌 LLM 감 | §2.2, §3.4(b) |
| **P-7** | **blind OOS 프레임 부재.** gate_passed 1,583이 전부 bounded/full-period 창 — survivor조차 선별창 누수(R2-05 사례). Deflated Sharpe/PBO/CSCV 미구현 | §4, 07-08 분석 §18 |
| **P-8** | **min 데이터 11개월.** min-primary 결정과 데이터 깊이가 모순. 다년 레짐 강건성은 현재 증명 불가능 | §2.1 |
| **P-9** | **대시보드 마지막 1마일.** (a) train/val/OOS 분리 오버레이 부재 (b) 프롬프트 버전↔세대 성과 A/B 뷰 부재 (c) 증거 원장 뷰 부재(0행이라 무의미하기도) (d) frontend 번들 8파일 uncommitted 방치 | §5-2, git status |
| **P-10** | **워크트리 문서 트리 이원화.** wt-dev와 wt-alpha가 각각 `docs/research/condition_research/`를 보유·분기(알파랩엔 오늘자 엔진 검토 문서). 환류 계약 없음 → 연구 고립 위험 | wt-alpha 실측 |
| **P-11** | **위생 부채.** 브랜치 ~90개(wide/webbt 종료 계보 미정리), `.omo/evidence` untracked 수백, `enforce_approved_b_only=False`(레지스트리 미정비), CL-R07 이월 nit 4건, state에 `loop_strategies.db.bak.*` 23개 방치 | git/디렉토리 실측 |
| **P-12** | **rules.txt 역할 혼선.** 대화형 워크플로 규칙이며 자율 루프 규칙은 system_prompt/v1에 있음 — 색인 부재로 신규 세션마다 재발견 | 본문 확인 |

---

## 7. 개선 로드맵 (v2)

### P0 — 승인 불필요, 즉시 (모두 기존 게이트 안)
1. **구조론 자산 배선**: `principles.md`(+ constraints 요약)를 연구 Context Pack(`_FULL_STOM_SOURCE_ASSETS`) 및 선택 프롬프트 블록으로 주입하는 토글 신설(기본 OFF, 정본 프로파일에서 ON). 문서의 "임계값은 무근거 가설 — 부검 분위수로 보정" 원칙을 그대로 계승. **P-3 해소, 비용 최소·기대효과 최대.**
2. **정본 연구 프로파일 1개 고정**: §3.3 토글 중 검증된 묶음(require_filter_gates+classification+few_shot(seed_db)+segment_feedback+feature_importance+mdd_control+exit_edge+exec_budget+principle_gate)을 ON한 config를 **소스 관리 파일로** 저장(state 아님). 모든 후속 연구 run의 기준. **P-4 해소.**
3. **증거 원장 상시화**: `evidence_ledger_enabled`를 정본 프로파일에서 ON — passport/envelope/consumption이 정본 DB에 쌓이기 시작해야 "이번 세대가 왜 나은가"가 데이터가 된다. **P-5 해소.**
4. **매도 ablation 캠페인**: CL-R07 하네스 2×2 재사용, 매수=Tick_902 고정 × 매도 변형(체결강도 페이드 파라미터·트레일링 폭·시간 손절) 탐색. MDD 축(87%) 직공. 격리 min subset, R07 예산 상한 준수.
5. **백파인더 밴드 배선**: `to_band_seeds` → `band_generation_enabled` 연결 + 1개월 subset 스모크. 임계값을 데이터 분포로. **P-6 절반 해소.**
6. **reference 17 처리**: 본문 확보 시 seed_db 등재, 불가 시 성능 스펙(일평균 10~23·MDD<7·시간창)을 생성 목표 블록으로 정량 주입. **P-6 나머지 해소.**
7. **위생**: frontend 8파일 정본 확정(커밋/재빌드/checkout 택1), state .bak 23개 아카이브 정책, 종료 브랜치 태깅.

### P1 — 승인 1개(`I approve CL-R08 bounded min performance only`)로 열림
8. **CL-R08 실행**: P0-2 프로파일 + P0-4 청산 승자 반영. **최초의 "수익 여부" 데이터 포인트.** 실행 전에 —
9. **Deflated Sharpe/PBO graded 가산항 구현**: R08 결과가 또 "우호창 논쟁"이 되지 않게 선행. **P-7 절반.**
10. **대시보드 3패널**: train/val/OOS 오버레이, 프롬프트 버전×세대 성과 A/B, 증거 원장 소비 사슬 뷰. **P-9.**

### P2 — 시간이 여는 것
11. **CL-R09 봉인 OOS/WF** (≈2026-08 중순, 20거래일 축적 후) — "미관측 개선"의 유일한 정직 증명. **P-7 완결.**
12. **min 수집 연속성 보장** (결측일 모니터링) — min lane의 미래 검증력 전부가 여기 달림. **P-8.**
13. **alpha-lab 환류 계약**: 알파랩 산출 → 정본 seed intake 어댑터(batch 평가 + passport 등재, 자율학습 주장 금지). **P-10.**

### 금지 (실패 매트릭스 준수 — 재확인)
Broad-Grid 재실행/축 확장 · tick 격자 반복 · full-period 선별 후보의 OOS 승자 해석 · go 없는 portfolio · 자동 R-라운드 무한 루프 · 게이트 완화 · no_go 재해석 · 승인 없는 export/live.

---

## 8. 종합 판정

전수 검사로 확정된 그림: **이 시스템은 "조건식을 못 만드는" 시스템이 아니라 "잘 만든 조건식 생성기를 9%만 쓰고, 가진 도메인 지식을 프롬프트에 안 꽂고, 수익 검증 단계 앞에서 스스로 멈춰 있는" 시스템이다.** 생성 실물(§3.4)은 시간대 국면 분기와 7경로 청산을 자율 산출할 만큼 성숙했고, 대시보드·증거·게이트 인프라는 과잉에 가깝다. 반대로 (1) 구조론 3종 미주입, (2) 토글 19개 OFF 방치, (3) 증거 원장 0행, (4) LLM 세대 9%, (5) blind OOS 부재는 전부 **배선 문제**지 능력 문제가 아니다. 다음 한 수는 새 개발이 아니라 §7 P0 1~6(전부 승인 불필요) → CL-R08이다. 그 결과가 나와야 "시드 부족이었는가, 프레임 부재였는가"에 데이터로 답할 수 있고, 현재 증거로는 **둘 다이며 프레임 쪽이 더 크다**가 잠정 답이다.

---

## 9. 근거 색인 (v2 실측)

- 코드: `brain/prompt.py:22-57,887-1315`, `brain/generator.py`, `brain/principle_gate.py`, `ai_strategy_loop/config.py`(토글 19개), `controller/loop.py`, `fitness/score.py`, `cli/condition_generator.py`, `cli/condition_fingerprint.py`, `cli/seed_lattice.py`, `dashboard/app.py:2680-3357`
- 프롬프트 자산: `utility/ai_agent/system_prompt/v1/{system_prompt,forbidden,examples,principles,constraints_checklist}.md`, `utility/ai_agent/rules.txt`
- 상태 DB: `ai_strategy_loop/state/loop_runs.db`(runs 506·generations 5,124·gate_passed 1,583·prompts 460·증거 4테이블 0행), `loop_strategies.db`(stockbuy 6,310·stocksell 6,212, 실물 `AILOOP_follow12_gptauth_B2_seeded64_20260628_g6_buy/sell`)
- 문서: `docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md`, `.../2026-07-08_condition_research_full_result_and_analysis.md`, `.../2026-07-12_cl_r07_bounded_mini_loop_GO.md`, `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_failure_lesson_matrix_20260709.md`, `docs/AGENT_HANDOFF.md`, `.../2026-06-02_analysis_capability_audit.md`
- 데이터/지형: `_database/` 전수 목록, `git worktree list`(11), 브랜치 목록(~90), `STOM_V.wt-alpha/docs/research/`(2026-07-12 엔진 검토 문서)
