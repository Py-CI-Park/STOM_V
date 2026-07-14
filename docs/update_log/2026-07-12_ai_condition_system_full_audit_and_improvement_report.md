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

---

# 제3부 (v3 증보) — 8ded51f8 반영, V4 대시보드 실시간 연동 검토, 프로세스 일반화 부족점

> v3 성격: `origin/loop/process-research-pipeline` tip `8ded51f8`(PR #105 `feature/dashboard-v4-into-loop` 병합)을 로컬에 반영한 뒤, 대시보드↔연구기능 실시간 연동과 "프로세스 자체의 일반화" 관점에서 검토를 이어간다. 전부 이 워크트리에서의 실측이다.

## 10. 8ded51f8 pull 반영 기록 (실행 내역)

| 항목 | 내용 |
|---|---|
| 반영 방법 | `git fetch` → 로컬 dirty 7파일 stash 보존 → `git merge --no-ff origin/loop/process-research-pipeline` = 병합 커밋 `1b7215f0` (로컬 보고서 커밋 2개 + origin 40커밋 통합) |
| dirty frontend 7파일 | 커밋된 jsx 소스의 **낡은 로컬 재빌드**(v=1ad7aac4)로 판정. origin `36415a5f`가 loop 병합 반영 재빌드(v=443d9ca0)를 이미 커밋 → origin이 정본. 로컬본은 `stash@{0}`으로 보존(기능적으로 병합본에 전부 포함 — gpt-5.6 드롭다운 소스 `f5a3fc5b`, research_observability 패널 소스 병합 포함 — 확인 후 폐기 가능) |
| `.gjc/` 충돌 | **origin에 `.gjc/` 에이전트 세션 상태가 커밋되어 있음**(대시보드 워크트리의 ultragoal 원장 보존 커밋 `3e879624`). 로컬 untracked와 충돌 → 로컬본 `.gjc.local-backup-20260712/` 이동 후 병합. 위생 문제로 §13-8에 기록 |
| 결과 | frontend dirty 해소(워킹트리 = origin 빌드), 대시보드 V4 전체(소스·테스트·검증 스크립트·증거 아티팩트 ~153K줄) 인테이크 완료 |

브랜치 로드맵 정합: 병합된 `docs/web_dashboard_expansion/BRANCH_FLOW_PLAN_2026-07-12.md` 기준 현재 위치는 **P3(loop에서 연구·개발 지속)**. 남은 것은 P4(alpha-lab → loop 반영, 2026-07-12 merge-tree 실측 충돌 0)와 P5(loop → `STOM_Version_2U_C-ai-strategy-loop` 승격 PR).

## 11. 병합 후 검증 실측 — 그리고 새로 확정된 부채 1건

| 게이트 | 결과 |
|---|---|
| `pytest tests/unit/ -p no:randomly -q` (13분15초) | **4,440 passed / 17 failed** |
| `python scripts/verify_nonrelease_sync.py` | 전체 통과 |

17 failed 분류(실측 — 병합 전 `c5fa0341` 체크아웃에서 동일 10건 재현 확인):

1. **기존 known 7**: 백테 spawn/UI 계약(button_contract·protocol_diagnostics×2·spawn_audit×2·runner_helpers·ui_jisu) — 불변식 문서와 일치.
2. **V4 대시보드 신규 실패 0** — PR #105 자체는 회귀를 만들지 않았다(핸드오프 §4의 주장과 실측 일치).
3. **⚠️ P-13 (신규 확정): 연구 계약 테스트 10건이 병합 전부터 깨진 채 방치** — `test_pack_producer` 5건(validate 실패), `test_llm_pack_wiring` 2건, `test_candidate_slots_override` 1건, `test_equity_points`(테스트는 스키마 10 기대, 실제 v11 — CL-R04 스키마 업이후 테스트 미갱신) 1건, `test_tick_seed_timeout_probe` 1건. 즉 **불변식 #6("known 7 외 신규 0")이 CL-R 계보 HEAD에서 이미 깨져 있었고, 핸드오프의 결정론 baseline 주장은 stale**이다. multi-hypothesis pack은 CL-R08의 생성 경로 그 자체이므로, 이 10건 수리는 CL-R08 착수의 사실상 전제조건이다.

## 12. V4 대시보드 — "모든 기능·연구가 실시간으로 보이는가, 체계적으로 UX/UI 개발되었는가"

### 12.1 실시간 연동 구조 (배선 실증)

- **경로**: `run_loop` → `_publish_live()`가 세대 단계(생성 0→백테 1→채점 2→부검 3→반복 4)마다 `current_state.json` 발행 → `dashboard/app.py` `/status` + WebSocket `/ws` push → V4 셸(`dashboard-v4-shell.jsx`)이 구독해 8탭에 props 분배. 프론트는 정적 서빙이라 jsx 수정 즉시 반영(백엔드 모듈 추가만 재시작).
- **연구 관찰성 계약 실배선 확인**: `controller/condition_discovery.py::build_research_observability_contract` → `page_data.condition_discovery.research_observability`(mode_authority / context_pack_health / branch_tree / candidate_pack / analysis_cards / prompt_receipts / promotion_blockers) → V2 패널(`panels-analysis.jsx`)과 V4 Research rail(`v4-research.jsx`) **양쪽 소비**. 즉 "생성 권한·컨텍스트팩 건강·후보팩·프롬프트 영수증·승격 차단 사유"가 라이브로 보이는 구조는 실재한다.
- **아카이브 왕복**: run 셀렉터(`?run=`)로 과거 506개 run 전체를 동일 화면에서 재구성(`/run_state`), 세대별 코드/diff/프롬프트/부검/자본곡선 API 연결.
- **8탭 구성**: Condition AI Overview · Process(cockpit) · History · Lab · Workbench · Decision Audit · Backtest · Chart Replay — `/ui/v4/`.

### 12.2 개발 체계성 평가 — 예, 오히려 과잉 수준

증거: 8뷰 전수 UX 감사 3회전(~90→~95% 성숙도, `2026-07-05_dashboard_v4_full_ux_audit.md`), 자동 브라우저 UAT 13/13(`scripts/v4_uat.py`), 검증 게이트 스크립트 6종(visual gate·safety audit·runtime depth·v2/v3 compare·inventory·human UX rubric), track-z 하네스 V1~V7, dashboard 단위테스트 689+, 보안 계층(`security.py` + `STOM_DASHBOARD_ALLOW_*` mutation 게이트 default-OFF, export 승인 분리), 스크린샷 증거 게이트(ultragoal g001~g007). **대시보드 개발 프로세스는 이 저장소에서 가장 성숙한 엔지니어링 루프다.**

### 12.3 남은 갭 (정직 판정)

1. **판정 뷰 3종은 여전히 부재**(v2 §6 P-9 유지): train/val/OOS 분리 오버레이, 프롬프트 버전×세대 성과 A/B, 증거 원장 소비 사슬 뷰. 관찰성 rail은 "계약/건강 상태" 중심이지 "이번 세대가 왜 나은가"에 답하지 않는다.
2. **C7 라이브 승인 게이트 E2E 미실행**(실 LLM 비용 + `backtest/graph/` 기록 → 사용자 승인 필요), B2 measurement_frame 백엔드 미배선.
3. **역전 현상**: 대시보드 검증 인프라(視覺 게이트·UAT·스코어카드)의 정교함이 정작 관측 대상인 **수익 증거 생산(CL-R08)** 인프라보다 앞서 있다. 화면은 95점인데 화면에 띄울 성능 데이터가 0건이라는 것이 현재 상태의 정확한 요약이다.

## 13. 프로세스 일반화 관점 부족점 — 프롬프트 요청 → 데이터 분석 → 시각화 → 환류 → 조건식 생성/개선

각 단계는 개별적으로 잘 만들어졌지만, **"새 분석/새 가설/새 축을 하나 추가하는 데 드는 비용"** 기준으로 보면 일반화가 안 되어 있다. 이것이 "연구를 해도 체감 효과가 없다"의 공정(工程) 측 원인이다.

| # | 일반화 결핍 | 실측 근거 | 권고 |
|---|---|---|---|
| G-1 | **환류 채널 파편화**: autopsy(매수/매도)·segment avoid·feature hints·hypothesis·meta_seed·edge feedback 등 6+채널이 각자 자유 텍스트 포맷 + 개별 config 토글 + `build_messages` 개별 kwarg. 새 분석 1개 추가 = 분석기·NL 변환·kwarg·토글·loop 배선 **5곳 수정** | `build_messages` 시그니처 20+ 파라미터, config 토글 19개 | 분석 결과를 표준 `FeedbackEnvelope`(이미 스키마 존재, 0행)로 통일하고 "envelope 목록 → 프롬프트 블록" 렌더러 1개로 수렴. 채널 추가 = envelope 생산자 1개 작성으로 축소 |
| G-2 | **분석 축 하드코딩**: `edge_by_segment`/`feature_importance`가 시총×시간대×등락률 고정축. 갭 유형·요일·변동성 레짐 등 새 축은 코드 수정 사항 | `fitness/edge_ratio.py`, `feature_importance.py` | 선언형 세그먼테이션(축 목록을 config/JSON으로) — 분석기는 축 명세를 받아 동일 파이프로 처리 |
| G-3 | **삼중 직렬화 중복**: 같은 분석이 ①대시보드 JSON payload ②프롬프트 NL 라인 ③문서 마크다운으로 각각 따로 구현·유지됨 | T1 히트맵 vs T4 avoid 라인 vs update_log 표가 모두 같은 세그먼트 분석의 수기 3중 렌더 | 구조화 결과(JSON) 단일 소스 + 뷰 렌더러 3개(대시보드/프롬프트/문서)로 분리 |
| G-4 | **프롬프트 조립 이원화**: 루프 lane(`build_messages`, 한국어 지침)과 연구 lane(`build_repair/discovery_research_messages`, Context Pack 250K)이 자산을 부분 공유(`_SYSTEM_ASSETS` 3종만)하고 규약이 갈라짐. 구조론 3종 미주입(P-3)도 이 이원화의 부산물 | `prompt.py` 상수 2벌 | 프롬프트 자산 로더/레지스트리 단일화(자산 추가 1곳) + lane별 조립만 분리. 구조론 3종을 레지스트리에 등재하면 두 lane이 동시에 획득 |
| G-5 | **조건식 자산 카탈로그 부재**: `AILOOP_*`(루프DB) / `lat_*`(격자) / `CSS_*`(차트술사 DB 등재) / Plan D passport(md) / repair composite(jsonl)가 네이밍·저장소·메타데이터 전부 제각각. "우리가 가진 모든 조건식과 그 성적"을 한 번에 조회할 방법이 없음 | `loop_strategies.db` 6,310 buy + docs 산재 | `condition_fingerprint`(AST 지문)를 PK로 하는 단일 카탈로그 뷰(읽기 전용) — 대시보드 Hall of Fame을 이 카탈로그 위로 이전 |
| G-6 | **실험 프로파일 비관리**: `state/run_*_config.json` 60여 개가 gitignored 산재 — 과거 실험 재현이 파일 발굴에 의존. "정본 연구 프로파일"(v2 §7 P0-2)과 동일 문제의 일반형 | state/ 목록 실측 | 프로파일을 소스 관리 디렉토리로 승격 + 대시보드 launch_config와 왕복(내보내기/불러오기) |
| G-7 | **프롬프트→성과 귀속 프레임 부재**: prompt version 상수·receipt는 있으나 세대 성과와 조인하는 실험 설계(A/B)가 없어 "어떤 프롬프트 변경이 효과였는가"를 계량 불가 | prompts 460행 ↔ generations 조인 뷰 없음 | 프롬프트 버전을 generations에 외래키로 기록 + 대시보드 A/B 패널(§12.3-1과 동일 작업) |
| G-8 | **런타임 상태의 저장소 오염**: origin에 `.gjc/` 세션 원장(수백 파일)과 대형 스크린샷 아티팩트가 커밋됨 — pull 충돌 유발 실증(§10). `.omo` evidence untracked 수백과 반대 극단 | 이번 pull에서 실제 충돌 | `.gjc/`는 gitignore(원장 보존이 필요하면 docs/evidence로 요약 이관), 증거 보존 정책 1페이지 확정 |

## 14. 갱신된 실행 우선순위 (v2 §7에 병합·증보)

**P0 (승인 불필요) — v2의 7건에 추가:**
- **P0-8. 연구 계약 테스트 10건 수리**(P-13): equity schema v11 정합, pack_producer/llm_pack/candidate_slots 실패 원인 수정. CL-R08 생성 경로의 사실상 전제.
- **P0-9. G-1 envelope 수렴 착수**: evidence_ledger ON(기존 P0-3)과 묶어 segment/feature/hypothesis 환류를 FeedbackEnvelope 경유로 이관(1채널부터).
- **P0-10. stash@{0} 폐기 판정**: 병합본 포함 확인 완료 후 drop, `.gjc` gitignore 정리(G-8).

**P1 (승인 1개):** CL-R08 + Deflated Sharpe/PBO + 판정 뷰 3종(§12.3-1 = G-7).
**P2:** CL-R09(≈08월 중순), min 수집 연속성, P4 alpha-lab→loop 반영(충돌 0 실측), P5 2U_C-aisl 승격(마일스톤 시).

## 15. 3부 결론

pull 반영으로 이 워크트리는 "V4 대시보드 + CL-R07 연구 통합" 완성 상태(BRANCH_FLOW P3)가 됐고, 실시간 연동 구조(루프→current_state→WS→8탭, research_observability 계약)는 **실재하며 체계적으로 검증되어 있다**. 그러나 전수 검사의 결론은 강화된다: **보이는 것(대시보드 95점)과 증명된 것(수익 증거 0건, 연구 계약 테스트 10건 파손, 환류 파이프 파편화) 사이의 격차가 이 시스템의 현재 병목이다.** 다음 손은 화면이 아니라 §14 P0-8(테스트 수리)과 P0 배선 작업, 그리고 CL-R08이다.

---

# 제4부 (v4 증보) — P0 실행 성과 기록 (브랜치 `feature/audit-p0-execution-20260712`)

> 2026-07-12, 병합 HEAD(`13b855d3`) 위 새 브랜치에서 보고서 P0 항목을 실제 개발·검증한 기록. 승인 잠금 단계(CL-R08~R10)는 실행하지 않았다.

## 16. 완료 항목 (커밋·검증 포함)

| 항목 | 커밋 | 내용 | 검증 |
|---|---|---|---|
| **A-1 연구 계약 테스트 10건 수리** | `10b3ef82` | 근본 원인 = pack_producer(문장형 후보)와 condition_fingerprint(식형 전용 문법)의 **계약 불일치**. ①지문 파서에 문장형 STOM 스니펫(`if 조건: self.Buy()`) 조건 추출 지원(if/elif test OR-결합) ②사칙 BinOp 문법 허용(가환 연산 정준 정렬 — `a*b`=`b*a` 동일 지문) ③validate_b_only가 추출 조건식만 스코프 검사. 기존 식형 지문 전부 불변(이전엔 에러였던 입력만 신규 수용). +스키마 v11 정합, probe는 discovery 하드 정책의 유효 warm 창(92800) 미러로 계약 정정 | 대상 스위트 158 passed |
| **A-2 구조론 자산 배선** | `967d0124` | `principles/constraints_checklist/idiom_dictionary` 3종을 연구 Context Pack(`_FULL_STOM_SOURCE_ASSETS`)에 전문 포함 + `structure_principles_prompt_enabled` 토글(기본 OFF, OFF=byte-동일)로 박스/추세 이분법·종가 우선·사건거래대금·눌림 구조·진입근거 상실 청산(CSC-02~07 핵심) 정제 블록을 매수/매도 프롬프트에 주입. generator/loop/state/launch_config 전 계층 배선 | 신규 계약 테스트 3종 + 관련 233 passed |
| **A-3 정본 연구 프로파일 + 게이트 배선** | `904b660e` | ①`principle_gate_enabled`를 run_loop→generate_strategy로 **실배선**(선언만 있고 루프가 안 읽던 상태 해소) ②`research_presets._COMMON_DISCOVERY`에 정본 ON-세트 승격: principle_gate·**evidence_ledger**(P0-3/A-7 전반부)·mdd_control·exit_edge·dispersion(프롬프트+graded)·meta_seed·structure_principles — 전역 기본값은 전부 OFF 유지(불변식 4) | 신규 계약 테스트: 정본 ON-세트 20키, 프리셋 키=LoopConfig 선언 필드 전수, 루프 배선 소스 가드 — 65 passed |
| **A-6 few-shot 골드 시드 우선** | `08f9caa4` | **정정 발견**: 운영 strategy.db에 인간 전략 본문 102 buy/47 sell 존재(Tick_902 패밀리·C_T_900_920·CSS_V7·Min_Study) — v2 보고서의 "reference 시드 부재"는 과대평가였고 실제 결함은 seed_db few-shot이 **테이블 선착순 k개**를 뽑아 골드가 선발되지 않던 것. 결정론 랭킹(골드 exact → 패밀리 prefix → 기타) + `__AUTO_TMP__` 배제로 교정. reference 17 스크린샷의 성능 스펙은 `_report_pattern_lines`(常時)에 기반영 확인(payoff≥1.25·MDD 3~7%·6~12종목) | 신규 테스트 2종 + exemplar/few_shot 스위트 20 passed |
| **A-8 위생** | `.gitignore` 커밋 | `.gjc/_session-*/`·`.gjc.local-backup-*/` gitignore, 낡은 frontend 로컬 빌드 stash 폐기(병합본 포함 확인 후) | — |
| **A-5 백파인더 밴드 시드 배선** | `61499e33` | `scripts/mine_band_seeds.py`(채굴→분포→시드 오프라인 파이프라인, tick DB 읽기 전용) + `band_seed_hint_enabled` 토글로 승자 셋업 밴드(q25~q75) NL 가이드를 매수 프롬프트에 주입(lookahead 편향 시드 전용·복제 금지·부검 보정 고지). tick 연구 프리셋 ON(아티팩트 없으면 graceful). **실DB 스모크: tick_subset 15거래일×60종목 = 22,545행 채굴 → 승자 3,570 → 시드 5개**(예: `[0900-0905·소형] lift 2.02, 등락율 1.71~7.19, 체결강도 58~181`) 산출·로더 소비 확인 | 계약 테스트 5종 + 관련 476 passed |

## 17. 최종 게이트 실측

| 게이트 | 결과 |
|---|---|
| `pytest tests/unit/` 전수 (A-1~A-3 후 13분50초 / A-5 후 재실행 10분37초) | **7 failed / 4,480 passed / 1 skipped — 신규 실패 0. failed 7 = 전부 known spawn/UI 계약.** P-13(연구 계약 10건 파손) 해소, **불변식 #6 결정론 baseline 복원·유지** |
| `verify_nonrelease_sync.py` | 전체 통과 |
| `pre_commit_check.py` | Syntax/Secrets PASS. print 지적 2건은 병합 유입 `cli/commands/research.py`의 CLI JSON 출력(이 브랜치 무관, 체커 휴리스틱 오탐 성격 — 기존 부채로 기록) |

## 18. 잔여 (정직 보고)

- **A-4 매도/리스크 ablation 캠페인**: 미실행 — 실 provider + 공식 엔진 실행이 필요한 연구 run(R07 하네스 재사용). 코드 준비는 완료 상태이므로 다음 세션에서 격리 min subset으로 실행.
- **A-7 envelope 수렴**: evidence_ledger 프리셋 ON(원장 축적 시작 조건)까지 완료. segment/feature 환류의 envelope 경유 이관은 미착수.
- **A-5 후속(선택)**: 이번 배선은 NL 힌트 경로. BandSpec → band_compiler 직접 컴파일 생성 경로(P1 완전형)는 미착수. 스모크 아티팩트는 threshold 3%(완화값) — 정본 채굴은 풀 tick DB·기본 임계(10%)로 재실행 권장.
- CL-R08~R10: 승인 문구 잠금 유지(실행 안 함).

## 19. 4부 결론

이 브랜치는 보고서가 지적한 **"배선 부채"의 즉시 실행 가능분을 전부 청산**했다: 깨져 있던 결정론 baseline 복원(P-13), 도메인 지식 3종의 두 프롬프트 lane 주입(P-3), 정본 연구 프로파일 확립과 잠자던 게이트/원장 토글의 연구 lane 상시화(P-4·P-5 전반부), 골드 시드의 few-shot 실효화(P-6 절반), **채굴 밴드 시드의 생성 프롬프트 환류(A-5 — 임계값이 데이터 분포에서 오는 첫 경로)**. 다음 정본 연구 run은 `research_presets`(tick_late/min_full) 프리셋으로 곧바로 "구조론 주입 + CSC 게이트 + 증거 원장 + 골드 few-shot + 밴드 힌트"가 켜진 상태에서 돈다. 남은 임계 경로는 A-4 → `I approve CL-R08 bounded min performance only`다.

## 20. 데이터 정책 확정 + 대시보드 실기동 검증 (2026-07-12, PR 전 마감 점검)

### 20.1 데이터 정책 (오너 결정 — 정본)

- **연구는 현존 데이터로만 수행한다**: tick 2022-03-23~2026-02-27(09:00~09:30), min 2025-04-07~2026-02-27(09:00~15:19).
- **데이터 추가(수집 확장·기간 연장·신규 소스)는 오너가 별도 결정할 때까지 계획·실행하지 않는다.** v2 §7 P2-12(min 수집 연속성)와 v3 §14의 데이터 관련 항목은 이 결정에 종속되는 **보류** 항목으로 재분류한다.
- min lane 다년 OOS 한계(P-8)는 현존 데이터 제약으로 수용하고, 강건성 판정은 tick 4년 lane 대조 + CL-R09 봉인 창(현존 데이터 내 시간 분할)으로 수행한다.

### 20.2 대시보드 실기동 검증 (브랜치 HEAD 기준)

| 검증 | 결과 |
|---|---|
| 서버 기동 | `uvicorn ai_strategy_loop.dashboard.app:app` :8799 — startup complete, 오류 0 |
| API 스모크 | `/health` 200(contract v2) · `/status` 200 · `/runs` 200(**506 run**) · `/hall_of_fame` 200 · `/equity_curves` 200 · `/gpt_auth/status` 200 · `/ui/` · `/ui/v4/` 200 |
| **신규 토글 폼 노출** | `/config/spec`에 `structure_principles_prompt_enabled`·`band_seed_hint_enabled` 노출 확인(이번 배선 반영). `principle_gate_enabled` 폼 항목 누락 발견 → 즉시 추가 |
| V4 UI 실렌더(헤드리스 브라우저) | Live 탭: 8탭 셸·"백엔드 연결됨·v2" 배지·HUMAN GATE/APPEND-ONLY 감사 배지·단계 파이프라인(생성→백테→채점→부검)·fitness 곡선·프로세스 거버넌스(fast-discovery, research allowed) 전부 렌더, **JS 에러 0**, 요소 564개. 증거: `artifacts/v4_dashboard_smoke_20260712.png` |
| V4 History 탭 | 아카이브 플로우 + RESEARCH RECORDS 17개 캠페인 실데이터(q4-defense +641,616/MDD 12.52% 등) 렌더. 증거: `artifacts/v4_dashboard_history_20260712.png` |
| 대시보드 회귀 스위트 | `pytest tests/unit/dashboard/` — **689 passed / 0 failed** (BRANCH_FLOW P3 기준 689+/0 정확 충족) |
| 정리 | 스모크 서버 PID 단독 종료(외과적, 불변식 8), 포트 8799 리스너 0 확인 |

### 20.3 PR 전 상태 판정

- **코드 작업: 완료.** 계획된 P0 배선(A-1/2/3/5/6/8) 전부 커밋·검증됨. 전수 pytest 7 known / 4,480 passed / 신규 0, dashboard 689/0, nonrelease sync 통과, 대시보드 실기동·실렌더 확인.
- **남은 것은 코드가 아니라 절차/승인**: ①PR(loop 머지) ②A-4 매도 ablation(실 provider 연구 run) ③CL-R08 승인 문구. 데이터 관련 항목은 20.1 결정으로 보류.
