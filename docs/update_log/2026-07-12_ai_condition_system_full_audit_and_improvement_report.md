# 2026-07-12 AI 조건식 시스템 전수 검사 및 개선 보고서

> 대상: `STOM_Version_2U_C` 파생 전 브랜치 계보(특히 `STOM_Version_2U_C-ai-strategy-loop` → `loop/process-research-pipeline` HEAD `c5fa0341`)와 alpha-lab 연구 워크트리.
> 목적: "존재하는 tick/min DB로 조건식을 만들어 STOM으로 수익을 낸다"는 최종 목표 기준으로, 코드·조건식·생성규칙·프롬프트·연구결과·대시보드·데이터를 전수 검사하고 부족한 점/문제점/개선점을 확정한다.
> 성격: 검토 보고서(read-only 감사). 어떤 no_go 결과도 재해석하지 않으며, 수익 주장을 하지 않는다.

---

## 0. 한 줄 결론 (정직한 판정)

**"연구 프로세스 인프라"는 과잉에 가까울 만큼 완성됐지만, "수익 조건식"은 아직 0개다.** 그리고 그 원인은 백테스트 엔진도, 게이트 엄격성도, 코드 품질도 아니다. 원인은 4가지의 결합이다:

1. **성능 검증 단계가 스스로 잠겨 있다** — CL-R08(제한 min 성능)·R09(봉인 OOS/WF)·R10(인간 비교)이 승인 문구 대기로 잠금 상태. 즉 "수익이 나는지 보는 단계"를 아직 실행한 적이 없다.
2. **후보 생성이 '엣지 가설'이 아니라 '격자 조합'이었다** — 576 lattice는 시장 구조 가설 없이 축(time×size×strength×family)을 기계적으로 곱했고, 결과는 go 0 / no_go 576.
3. **매도/리스크 연구가 매수 연구보다 압도적으로 얕다** — 전체 실패의 1차 축은 profit이 아니라 **MDD 폭발**(mdd_excess 479/576)인데, 청산 구조 연구는 hold-time 오추출 감사(Family 7) 수준에 머물렀다.
4. **시드 자산이 사실상 1개(Tick_902)뿐이고, min 데이터가 11개월뿐이다** — 사용자가 직감한 "시드가 좋은 게 없어서 성과가 없었나"는 절반은 맞다. 나머지 절반은 min lane의 다년 강건성 검증이 데이터상 불가능하다는 구조적 한계다.

---

## 1. 자산 인벤토리 (무엇을 갖고 있는가)

### 1.1 데이터 (`_database/`, 보호 경로 — 읽기 전용 확인)

| 자산 | 범위 | 크기 | 평가 |
|---|---|---|---|
| `stock_tick_back.db` | 2022-03-23 ~ 2026-02-27, **09:00~09:30만** | 29.7 GB | 다년(4년) 검증 가능한 유일한 lane. 단 30분 창 한정 |
| `stock_tick_YYYYMMDD.db` | 2022-03-23 ~ 2026-02-27 일별 | ~0.03 GB/일 | subset/청크 실행용 |
| `stock_min_back.db` | **2025-04-07 ~ 2026-02-27 (약 11개월)**, 09:00~15:19 | 1.46 GB | 풀세션 lane이지만 다년 OOS 불가. **최대 데이터 갭** |
| `stock_min_YYYYMMDD.db` | 2025-04-07 ~ 2026-02-27 일별 | ~0.01 GB/일 | CL-R07 격리 실행에 사용 |
| `strategy.db` | 시드 `Tick_B/S_902_905_Update_2` byte-동일 보존 | — | 유일한 실배포급 골드 시드 |
| `backtest.db` | 3.28 GB | — | 결과 축적 |

핵심 비대칭: **tick = 길지만 좁다(4년×30분), min = 넓지만 짧다(풀세션×11개월).** 이 비대칭이 연구 설계를 계속 왜곡해 왔다(아래 §4.7).

### 1.2 시드/조건식 자산

| 자산 | 근거 | 상태 |
|---|---|---|
| `Tick_902` (09:02~09:05 tick 스캘퍼) | 2022~2025 연속 흑자, r²0.90, 2024Q1 +1.55M / 2025Q1 +1.94M | **골드.** AI refine이 정직한 OOS에서 이긴 적 없음 |
| 인간 reference 17개 | `docs/reference/STOM_Good_Results/` 스크린샷 (전부 tick·09:00~09:30·일평균 10~23회·MDD 1.9~6.75%) | **북극성이지만 조건식 본문이 시드로 미등재** — 성능 스펙만 존재 |
| repair composite survivor 15 | selected OOS-style 16 중 15 (2026-07-06) | 참고 자산. fully blind 아님 |
| Plan D rank01/02/03 survivor (대표 rank03 R2-05: profit 554,624 / MDD 5.24 / daily 2.20) | seed passport 보존 | seed 근거. **promotion 근거 아님** (full-period에서 선별 → OOS 창 누수) |
| 검증된 비-AI 자산: 적응형 레짐 타이밍 | 2022~2026 진짜 OOS에서 위험조정 3.5배, MDD −71% | **가장 배포 가능성 높은 결과인데 분석전용 토글로 방치** |
| 백파인더(T2) BandSpec | 실DB 24,229행, 129 승자, 최고셀 lift 8.99 | lookahead 편향 있는 생성 시드 — **밴드 생성경로(P1) 미배선** |

### 1.3 코드 표면 (검사 완료)

- **생성**: `brain/prompt.py`(system 자산 3종 + classification/avoid/crossover/sparse-positive/exec-budget/report-principles 블록, repair/discovery 이중 lane, Context Pack 250K 토큰 예산, R_/S_ 누수 차단), `brain/generator.py`(PRE-SAVE 게이트 사슬), `brain/filter_gate.py`(시간창 측정·no-op 탐지), `brain/segment_feedback.py`(패배 세그먼트 avoid 환류), `brain/band_compiler.py`+`seed_902_band.py`.
- **후보 계약**: `cli/condition_generator.py` — multi-hypothesis candidate pack v1, B-only 검증(`validate_b_only`), AST 의미 지문(`cli/condition_fingerprint.py`), parent provenance, 진단 fallback 라벨링. `enforce_approved_b_only`는 **기본 False**(CL-R07 전제조건으로 명시된 미완).
- **채점**: `fitness/score.py` — `compute_fitness` 하드게이트(불변식) + `compute_graded_fitness`(undertrade/daily 페널티, exit-quality, dispersion, multiyear stability, multi-objective). **Sharpe/CVaR/PBO/CSCV/Deflated Sharpe 미구현**(2026-06-02 감사 backlog 그대로 잔존).
- **루프 소유권**: `controller/loop.py::run_loop`가 유일 계보 소유자, EvidenceStore append-only(schema v11), phase 권한 계약(`verify_ai_loop_phase_contract.py`). batch 평가는 자율학습이 아님이 계약으로 못박힘(Family 8).
- **프롬프트 자산**: `utility/ai_agent/system_prompt/v1/` 7종(system_prompt·variables_reference·forbidden·examples + 최근 추가된 idiom_dictionary·constraints_checklist·principles). `rules.txt`는 대화형 워크플로 규칙 중심으로 **자율 루프용 규칙이 아님**(§4.8).
- **대시보드**: FastAPI + 정적 jsx. 히트맵/막대(T1), run 셀렉터, cohort 안전 비교(CL-R). frontend 번들 파일들이 **uncommitted 수정 상태로 방치**(§5.6).

### 1.4 브랜치/워크트리 지형

- 활성 워크트리 11개. 개발 정본 = `STOM_V.wt-dev`(`loop/process-research-pipeline`), 연구 = `STOM_V.wt-alpha`(`research/alpha-lab-idea5-foundation-20260707`), 대시보드 계열 3개(wt-dashboard-next/remodel/webbt), 거버넌스 1개.
- 로컬 브랜치 약 90개: wide-v1/v2 계열(~20), webbt 계열(원격 포함 ~50), feature 산발. **wide-v1/v2·webbt 계열은 사실상 종료된 계보인데 미정리** — 인지 부하와 "무엇이 정본인가" 혼동의 원인.

---

## 2. 연구 결과 전수 팩트 (2026-06 ~ 2026-07)

시간순 핵심 사실만. 전부 근거 문서가 있는 검증된 수치다.

| 시기 | 실행 | 결과 | 교훈 |
|---|---|---|---|
| ~06-03 | TICK T0~T4 인프라(넓은생성·퀀트시각화·백파인더·avoid 환류·시간창 측정) | 인프라 완성, 각 단계 실DB 스모크 통과 | **토글 ON 다년 run + OOS는 미실행인 채 다음 국면으로 넘어감** |
| 06-14~06-19 | tmap/walk-forward, 앙상블, OOS 2023~2025 실험 대량 | 적응형 타이밍만 진짜 OOS 생존. 앙상블 고정전이 실패 | AI는 시드 대체가 아니라 보완 |
| 07-02~07-05 | **Broad-Grid-576** (tick 288 + min 288, 공식 warm64 전체기간) | **gate_passed 0/576. go 0 / hold 0 / no_go 576.** tick: 288/288 음수익, avg MDD 512%. min: 271/281 음수익, avg MDD 71% | 격자 조합은 엣지가 아니다. 게이트 완화로 해결 불가(`gate_relaxation_is_not_sufficient`) |
| 07-06 | repair composite | selected 16 중 **survivor 15** | 실패 지도의 조각 조합(composite)이 단일 seed보다 우월 |
| 07-06~07-08 | Plan D rank01/02/03 controlled mutation | rank별 survivor 누적, rank03 R2-05(+554K/MDD 5.24/daily 2.20) | 단, full-period 선별 → OOS 창 누수. seed 근거로만 보존 |
| 07-08~07-09 | V2 Failure-Guided-8 제한 replay | **8중 OK 7 전부 손실**, MDD 89~442. survivor 0 → V2 계보 종료 | 실패 본체의 미세 변형은 답이 아님 |
| 07-09~07-11 | Lattice V3 설계 + CL 정본 재구축(CL-D0~D4, CL-R01~R06) | 증거계약·EvidenceStore·B-only provenance·AST 지문·phase 권한 계약 통합 | 프로세스 체계화 |
| 07-12 | **CL-R07 제한 폐루프** (실 gpt-5.6-terra + 공식 엔진, 단일종목 5거래일) | **GO_PROCESS_PROOF(건전)** — 생성→부검→피드백 소비→재생성 학습사슬 + 2×2 ablation 증명, ~14분 | **폐루프가 실제로 돈다.** 단 수익은 판정 기준이 아니었음 |

**누적 판정**: 시스템은 (a) 자율 폐루프 작동 증명, (b) 완전한 음성 기준선(576+8), (c) 참고용 survivor seed 풀, (d) 검증된 비-AI 개선(적응형 타이밍)까지 확보했다. 확보하지 못한 것은 단 하나 — **미관측 기간에서 비용 차감 후 수익이 나는 조건식**이다.

---

## 3. 사용자 질문에 대한 직답

### Q1. "조건식을 복합적으로 잘 생성하고 여러 가능성을 잘 보는가?"

**구조적으로는 상위권, 실질 탐색 폭은 아직 좁다.**

잘 갖춘 것:
- multi-hypothesis candidate pack(후보 2+개 강제, 후보별 가설 분리), crossover(GA 부모 결합), classification 축(시간×시총×등락률), few-shot(seed_db 인간전략), 패배 세그먼트 avoid 환류, 시간분산 장려, AST 의미 지문으로 중복 후보 차단, B-only 누수 가드.

부족한 것:
1. **탐색이 대부분 default-OFF다.** classification/few-shot/segment_feedback/dispersion/band 등 탐색 폭을 만드는 토글이 전부 기본 꺼짐이고, 이걸 모두 켠 "연구 표준 프로파일" run은 2026-06-03 핸드오프의 최우선 과제였는데 **한 번도 완주되지 않았다.**
2. **임계값이 데이터에서 오지 않는다.** 백파인더가 실데이터에서 승리셋업 분포(등락율 q25~q75 = −1.5~5.4, 체결강도 116~180)를 이미 채굴했는데, 이 BandSpec → 생성 프롬프트 배선(P1 `band_generation_enabled`)이 미완이라 LLM이 임계값을 여전히 "감"으로 찍는다.
3. **가설 어휘가 진입 중심이다.** 청산/리스크(트레일링, 시간 손절, 변동성 스탑, 부분청산) 가설 공간은 프롬프트에 사실상 없다. MDD가 1차 사인인 시스템에서 치명적 편식이다.
4. 576 lattice의 "여러 가능성"은 조합 폭발이지 가설 다양성이 아니었다 — 이미 Family 3 결론으로 확정(재개 금지).

### Q2. "시드가 좋은 게 없어서 성과가 없었나?"

**부분적으로 맞다.** 검증된 골드 시드는 Tick_902 하나뿐이고, 북극성인 인간 reference 17개는 스크린샷(성능 스펙)만 있지 **조건식 본문이 시드 DB에 없다.** AI가 "인간 고수 수준"을 목표로 하는데 인간 고수의 실제 조건식 구조를 few-shot 이상으로 흡수할 경로가 없다. 다만 "시드만 좋으면 됐을 것"도 아니다 — repair composite/Plan D가 보여주듯 시드가 생겨도 **blind OOS 프레임이 없으면 window 과적합으로 수렴**한다(§18, 2026-07-08 분석). 시드 부족과 검증 프레임 부재가 쌍으로 문제였다.

### Q3. "경험/도메인 지식 부족을 AI가 대체하는가?"

절반만. 도메인 주입(classification·few-shot·filter_gate)이 백지붕괴를 막는다는 것은 실증됐지만(GROUND-TRUTH #4), 시초 30분 매매의 미시구조 지식(갭 유형별 행동, 프로그램/기관 수급, 상한가 근접 동학 등)은 프롬프트 자산에 원리 어휘 수준(`principles.md`, report-principles 블록 — 이것도 default-OFF)으로만 있다. **백파인더 채굴 결과가 이 갭을 데이터로 메울 수 있는 유일한 통로인데 미배선 상태**라는 점이 반복적으로 병목이다.

---

## 4. 근본 문제점 전수 목록 (우선순위순)

### P-1. 성능 검증 미실행 — "수익이 나는지 본 적이 없다" [최상위]
CL-R08(60일 train40/val20 제한 min 성능, 최대 11 공식평가/4시간)·R09(20거래일 봉인 OOS/WF)·R10(인간 비교)이 전부 승인 잠금. 프로세스 증명(R07)까지 끝난 지금, **수익 무존재의 1차 원인은 기술이 아니라 실행 순서다.** R09는 2026-07-11 이후 20거래일 데이터 대기라 대략 2026-08-10 전후에나 열린다.

### P-2. MDD/청산 연구 부재
576 실패의 primary_fail: mdd_excess 479 + mdd_excess_and_low_daily 23 = **87%가 MDD 축.** 그런데 매도측 연구 자산은 임계값 재추출 감사(stop −3/−2, take +1~4, 장후반 145500 exit)뿐이다. exit-quality 항(payoff/give-back)이 graded에 있지만 **생성 프롬프트에는 청산 설계 가이드가 없다.** 매수 고정(골드 시드) × 매도 변형 ablation은 CL-R07의 2×2 인프라로 즉시 가능해졌는데 아직 그 용도로 안 썼다.

### P-3. 좋은 기능의 default-OFF 방치 (배선 부채)
불변식 4("신규 기능 = 기본 OFF") 자체는 옳지만, 그 결과 **검증된 개선들이 켜진 적 없는 상태로 누적**됐다: 적응형 타이밍(OOS 3.5배 검증), 백파인더 밴드(P1), full_session, classification+few_shot+segment_feedback 묶음, report principles 어휘. "OFF가 안전"과 "OFF라서 성과 없음"이 동시에 참인 상태다. 필요한 것은 기본값 변경이 아니라 **정본 연구 프로파일 config 1개**(전 토글 ON)를 고정하고 모든 연구 run이 그걸 쓰는 것.

### P-4. min 데이터 11개월 — 다년 OOS 구조적 불가
min lane이 primary lane으로 확정됐는데(Family 2 재사용 자산) `stock_min_back.db`는 2025-04부터다. 2026-07 현재 최대 15개월. **min 전략의 다년 레짐 강건성은 데이터가 쌓이기 전엔 증명 불가능하다.** 이것은 코드로 못 고친다 — min 일별 DB 수집을 중단 없이 유지하는 것 자체가 최고 가치의 연구 투자다. (보조: tick 4년 lane을 스트레스/레짐 대조군으로 병행.)

### P-5. 인간 reference 17개가 죽은 자산
북극성인데 스크린샷이다. 조건식 본문이 있다면 seed_db 등재(few_shot_source 확장 + 시드 passport)로 즉시 최고 품질 시드 17개가 생긴다. 본문이 없다면(스크린샷만 소유) 성능 스펙(일평균 10~23회, MDD<7, 시간창)을 **생성 목표 스펙으로 프롬프트에 정량 주입**하는 차선책이라도 배선해야 한다. 현재는 둘 다 아니다.

### P-6. 통계적 과적합 방어 미구현
2026-06-02 분석역량 감사에서 지적된 Deflated Sharpe/PBO/CSCV가 여전히 없다. Plan D처럼 같은 lineage에서 파생된 survivor를 반복 선별하는 구조는 selection bias가 기본값이므로, graded 가산항으로라도 넣지 않으면 R08/R09 결과 해석이 또 "우호창 과적합" 논쟁으로 돌아간다.

### P-7. 대시보드가 '관찰'까지만 하고 '판정'을 돕지 않음
현재: 세대 목록, 히트맵/막대(등락률·시간대), run 셀렉터, cohort 비교. 없음: (a) 실패 원인 분해 뷰(mdd_excess/low_daily/negative_profit 비율 — P6 데이터는 이미 JSON으로 존재), (b) 세대별 학습곡선(피드백 소비 → graded 변화 — EvidenceStore v11에 데이터 있음), (c) train/val/OOS 분리 오버레이, (d) T3 시간창 분산 패널(핸드오프 §6-3, 미완), (e) 시드 대비 상대성과(vs Tick_902 baseline). 즉 **데이터는 다 쌓이는데 시각화가 의사결정 질문("이번 세대가 저번보다 왜 나은가/나쁜가")에 답을 못 준다.**

### P-8. `utility/ai_agent/rules.txt`가 자율 루프와 불일치
rules.txt는 "초기계획 제출 → 사용자 선택메뉴 → 승인 후 구현" 대화형 워크플로 규칙이다. 자율 루프의 실제 규칙(B-only, 누수 금지, 임계값 provenance, 매수=True/매도=False 정규형, 시간창 규약)은 `system_prompt/v1/*`에 있다. 두 소스의 역할 구분이 문서화돼 있지 않아 "생성 규칙이 어디 있는가"가 신규 세션마다 재발견 대상이 된다. 얇은 색인 문서 하나로 해결 가능.

### P-9. 위생 부채
- frontend 번들/HTML 8개 파일 tracked-modified 상태 장기 방치(§1.3) — 의도 커밋인지 빌드 부산물인지 판정 필요.
- `.omo/evidence/` untracked 수백 파일, `artifacts/` .err/.py 혼재 — 증거 보존 정책(어디까지 커밋/아카이브)이 없어 worktree가 항상 dirty.
- 브랜치 ~90개 중 종료 계보(wide-v1/v2, webbt phase 계열, 초기 feature) 미정리.
- `enforce_approved_b_only=False` 기본값 — approved B_* 레지스트리 reconcile이 CL-R07 전제로 명시됐으나 미완.
- CL-R07 이월 nit 4건(control GO 게이팅, `_generate` try/except, reasoning_effort payload 미전송, manifest fake 표기) — 문서상 추적 중이나 코드 미반영.

### P-10. 거버넌스 대 실행의 비율
2026-07 한 달의 커밋/문서를 보면 승인 게이트·증거 계약·재검증 문서가 실제 신규 연구 실행보다 몇 배 많다. 과거 과적합 사고(1개월 보고서급 우승자 소동)의 반작용으로 이해되지만, 현재 잠금 구조는 **"실패로부터 배우는 속도" 자체를 승인 대기열에 종속**시켰다. 게이트는 유지하되, 게이트 안에서 돌 수 있는 실험(R07 하네스 재사용 매도 ablation, 밴드 배선 스모크, 대시보드 패널)은 승인 없이도 진행 가능하다는 사실이 활용되지 않고 있다.

---

## 5. 부문별 상세 검토

### 5.1 조건식 생성 규칙·프롬프트 (`brain/prompt.py`, `system_prompt/v1`)
- **강점**: system 자산 조립(변수 레퍼런스+금지어), min/tick 상호배타 변수 스코프(`variable_scope.py`), 코드펜스 strict 추출, 연구 Context Pack 250K 토큰 예산 fail-closed, R_/S_ 누수 금지 이중 검사(프롬프트단+ingestion단), repair(1 분석카드/1 축)·discovery(1 갭/1 후보) lane 분리, 프롬프트 성숙도 receipt.
- **약점**: (a) 청산 설계 어휘 부재, (b) 임계값 데이터 근거(밴드) 미주입, (c) report principles·sparse-positive 등 품질 블록 default-OFF, (d) 인간 reference 스펙 미주입, (e) 프롬프트 버전이 receipt로 기록되지만 **프롬프트 A/B 성과 비교 루프는 없음**(어떤 프롬프트 변경이 세대 성과를 올렸는지 계량 불가).

### 5.2 후보 계약 (`cli/condition_generator.py`, `condition_fingerprint.py`)
- **강점**: pack 검증(최소 2후보), parent 코드/sha 컨텍스트 병합, AST 의미 지문으로 표절/재탕 차단, 진단 fallback을 "프롬프트 성숙 증거 아님"으로 명시 라벨, authority-key 오염 차단.
- **약점**: `enforce_approved_b_only` 기본 False(레지스트리 미정비), timeframe unknown 시 min으로 조용히 폴백(안전하지만 지문 왜곡 가능성 — 로그로 노출 권장).

### 5.3 채점 (`fitness/score.py`)
- **강점**: 하드게이트 불변 원칙 준수, graded가 게이트 실패에도 그래디언트 제공(undertrade daily 제곱 페널티, gate-distance 텍스트), exit-quality/dispersion/multiyear 가산, Calmar ∞ 안전 처리.
- **약점**: Deflated Sharpe/PBO/CSCV/CVaR 부재(P-6), 비용/슬리피지 스트레스 항 부재(슬리피지 도구는 2026-06-11에 만들었으나 graded 미연결).

### 5.4 루프/증거 (`controller/`)
- **강점**: 단일 소유권(run_loop), append-only EvidenceStore v11, phase 권한 계약 + 검증 스크립트, 후보 여권↔실행 영수증 연결(CL-R04), 피드백 영속·소비 증거(CL-R05), 다양성/기여도 검증(CL-R06). 이 부분은 업계 기준으로도 과할 만큼 잘 되어 있다.
- **약점**: CL-R07 이월 nit 4건, OOM 한계(3년 풀유니버스 warm ~5세대) 대응이 여전히 "주의" 수준 — 세대별 메모리 워터마크 기록/자동 캡이 없다.

### 5.5 백테스트 실행
- warm 엔진/큐/argv 계약 보존 양호. wrong-profile·stale/partial을 receipt로 분리하는 관행 정착(2026-07-08 §12) — 이건 유지해야 할 최고 관행.
- 0거래 백테스트를 CLI가 RC=2로 반환하는 관례는 R07에서 엔진 체크포인트 기반 판별로 우회했지만, 상류(공식 CLI)의 의미론은 그대로다 — 후속 하네스 작성자가 또 밟을 함정이므로 cli/AGENTS.md gotcha 등재 가치.

### 5.6 대시보드/시각화
- P-7 참조. 추가로: 수정된 frontend 번들 8파일이 커밋도 폐기도 아닌 상태 — `bundle/manifest.json`까지 변경돼 있어 서빙 중인 UI와 저장소 상태가 불일치할 수 있다. 정본 확정(커밋 or 재빌드 or checkout) 필요.

### 5.7 alpha-lab 워크트리 (`STOM_V.wt-alpha`, idea5-foundation)
- 연구 lane 분리는 올바르다. 단 alpha-lab 산출물이 정본 계보(EvidenceStore/seed passport)로 환류되는 계약이 없다 — 좋은 아이디어가 브랜치에 고립될 위험. "alpha-lab → 정본 seed intake" 어댑터(batch 평가 + passport 등재, 자율학습 주장 금지)를 명시 계약으로 만들 것.

---

## 6. 개선 로드맵 (구체적, 우선순위·의존성 포함)

### P0 — 지금 즉시, 승인 불필요 (게이트 안에서 가능한 것)
1. **매도/리스크 ablation 캠페인**: R07 하네스(`run_canonical_mini_loop_official.py`)의 2×2를 재사용해 매수=Tick_902 고정, 매도 변형(시간손절/트레일링/부분청산/변동성 스탑)만 탐색. 격리 min subset, 예산 상한 동일. MDD 축 공략의 최단 경로.
2. **백파인더 밴드 배선(P1)**: `backfinder_principle.to_band_seeds` → `band_generation_enabled` 생성 경로 연결 + 1개월 subset 스모크. 임계값을 데이터 분포로 대체하는 유일한 준비된 수단. (핸드오프 §6-2, 3주째 대기 중)
3. **정본 연구 프로파일 config 고정**: classification+few_shot(seed_db)+segment_feedback+dispersion+filter_gate+(밴드) ON 묶음을 `run_canonical_research_config.json`으로 저장소에 고정(state가 아닌 소스 관리) — "매번 어떤 토글을 켜는가" 재발견 비용 제거.
4. **인간 reference 17 스펙 주입**: 조건식 본문 확보 여부 확인 → 있으면 seed_db 등재, 없으면 성능 스펙(일평균/MDD/시간창)을 생성 목표 블록으로 프롬프트에 정량 주입.
5. **위생**: frontend 8파일 정본 확정, 브랜치 아카이브 태깅(wide-*, webbt-*), `.omo/evidence` 보존 정책 1페이지.

### P1 — 승인 1개로 열리는 것
6. **CL-R08 실행** (`I approve CL-R08 bounded min performance only`): 60일 train40/val20, 위 정본 프로파일 + 매도 ablation 승자 반영. **여기가 최초의 "수익 여부" 데이터 포인트다.**
7. **Deflated Sharpe/PBO graded 가산항**: R08 결과 해석 전에 구현해야 "또 우호창 논쟁"을 차단.
8. **대시보드 판정 패널 4종**: 실패 원인 분해(P6 JSON 재사용), 세대 학습곡선(EvidenceStore), 시드 대비 상대성과, T3 시간창 분산.

### P2 — 시간이 여는 것
9. **CL-R09 봉인 OOS/WF**: 2026-07-11 이후 20거래일 축적(≈08월 중순) 후. 이것만이 "미관측 개선"의 정직한 증명.
10. **min 데이터 수집 연속성 보장**: 수집 파이프라인 모니터링/결측일 알림. min lane의 미래 검증력은 전적으로 여기 달렸다.
11. **적응형 레짐 타이밍 배선 검토**: 이미 OOS 검증된 자산 — R10(인간 비교) 국면에서 시드+타이밍 조합을 기준선으로 승격 심사.

### 명시적으로 하지 말 것 (실패 매트릭스 준수)
- Broad-Grid-576 재실행·축 확장, tick 격자 반복, full-period 선별 후보의 OOS 승자 해석, go 없는 portfolio 산출, 자동 R-라운드 무한 루프, 게이트 완화, no_go 재해석.

---

## 7. 종합 판정

이 프로그램의 문제는 "AI가 조건식을 못 만드는 것"이 아니다. CL-R07이 증명했듯 생성→평가→부검→재생성 폐루프는 실제로 돈다. 문제는 (1) **수익을 측정하는 단계가 한 번도 열리지 않았고**, (2) 탐색이 **MDD를 만드는 쪽(청산)을 비워둔 채 진입만 팠으며**, (3) 데이터에서 캔 근거(밴드)와 검증된 개선(적응형 타이밍)과 북극성 시드(reference 17)가 **전부 배선되지 않은 채 창고에 있다**는 것이다. 다음 한 수는 새 인프라가 아니라 **P0-1(매도 ablation)·P0-2(밴드 배선)·P0-3(정본 프로파일) → CL-R08 승인 실행**이다. 그 결과가 나와야 비로소 "시드 문제였는지, 프레임 문제였는지"에 데이터로 답할 수 있다.

---

## 8. 근거 문서 색인
- `docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md` (정본 핸드오프, §11 CL-R07 종료)
- `docs/research/condition_research/plans/2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md`
- `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_failure_lesson_matrix_20260709.md` (Family 1~8)
- `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md` (576/composite/Plan D 전체 수치)
- `docs/update_log/2026-07-12_cl_r07_bounded_mini_loop_GO.md`
- `docs/AGENT_HANDOFF.md` (GROUND-TRUTH 1~8, T0~T4)
- `docs/update_log/2026-06-02_analysis_capability_audit.md` (통계 지표 갭)
- 코드: `ai_strategy_loop/brain/prompt.py`, `cli/condition_generator.py`, `cli/condition_fingerprint.py`, `ai_strategy_loop/fitness/score.py`, `ai_strategy_loop/scripts/run_canonical_mini_loop_official.py`
