# 1. 표지: Alpha Lab 연구 종합 보고서(2026-07-17 현재)

본 문서는 2026-07-17 현재 Alpha Lab 연구를 새 유지보수자가 한 번에 읽을 수 있도록 정리한 standalone 한국어 보고서다. 사실 근거는 아래 source manifest의 다섯 durable 문서와 구조 계약 `agent://366-ResearchReportContentMap`에 한정한다. 본 보고서 작성 작업은 과거 연구·엔진·DB·git·테스트를 재실행했다는 주장을 하지 않는다.

핵심 결론은 네 문장이다.

1. Audit branch G001~G010은 **승격 가능한 STOM 전략 후보 0건**으로 닫혔다. 그 산출물은 감사·거버넌스·비승격 지식·통합 준비이지 전략 등록 권한이 아니다. [SYN §1-3, §10-12], [BRF 목표표, 승격 가능 후보 0건 등록부]
2. Prior target program의 B1은 여전히 **감독형 실전 채점으로 넘겨진 유일한 empirical improvement**다. 단, 30거래일 채점 전에는 live success 또는 최종 성공을 말할 수 없다. [H3 §4]
3. Post-audit target sell D1은 “매도식에서 절 단위로 뺄 것 없음”을 확인한 **load-bearing 지식**이다. 제거-개선 후보는 0개이고, load-bearing 절은 [1, 3, 6, 8, 9]다. [SD1 결론표], [H3 §5 매도식 D1]
4. Current target X1 buy clause-drop은 **봉인·구현되었으나 아직 pre-measurement**라는 report-time observation으로 취급한다. 즉 X1 결과, PASS, KILL, 후보 승격을 보고하면 안 된다. Parent-supplied observation [OBS]; 사전등록 경계 [X1P header, §0, §6-8, §14]

쉬운 설명: audit branch는 “검사와 장부 정리”이고, B1은 “이미 작은 실전 시험장으로 넘긴 유일한 개선안”이며, sell D1은 “매도 그물코 중 빼도 되는 코가 없다는 진단”이고, target X1은 “매수 그물코를 하나씩 빼 보자는 시험 계획이 봉인된 상태”다. 네 항목은 같은 연구 프로그램 안에 있지만 같은 판정 단계가 아니다.

---

# 2. 출처 범위와 읽는 법

## 2.1 Source manifest

| Alias | Durable path / 입력 | 이 보고서에서의 용도 |
|---|---|---|
| [MAP] | `agent://366-ResearchReportContentMap` | 본 보고서의 20개 권장 섹션, 충돌 해소 요구, outcome matrix 구조. 실측 사실의 1차 근거가 아니라 구성 계약이다. |
| [SYN] | `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/2026-07-16_alpha_lab_final_research_synthesis.md` | Audit branch G001~G010 최종 합성, terminal distinction, supersession chain, G003/G005/G006 수치, pre-G007 integration baseline. |
| [BRF] | `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/2026-07-16_alpha_lab_management_briefing.md` | Management-level no-candidate register, approval/protected-surface table, branch baseline wording, business interpretation. |
| [H3] | `docs/research/condition_research/plans/2026-07-12_program_handoff_v3.md` | Prior Alpha Lab program 정본: 라운드 1~7, B1 실전 인계, D1/pairwise/O-series/B-track/B-ext, sell D1 handoff row. |
| [SD1] | `docs/research/condition_research/research_runs/alpha_restart_20260710/sell_d1/sell_d1_report.md` | Post-audit target sell D1 절 ablation 판정 원문: load-bearing 5절, 제거-개선 0, 절별 Δ/CI. |
| [X1P] | `docs/research/condition_research/plans/2026-07-17_x1_buy_clause_drop_ab_preregistration.md` | Current target X1 매수식 절 삭제 엔진 A/B 사전등록: 후보 4개, 기준 A, 판정 기준, U-7/U-4 경계. |
| [OBS] | Parent가 이 assignment에 제공한 report-time observation | 파일 근거가 아닌 현재 관측값: target branch `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`, audit branch `e808015ce4bd62601dd75a535a57b36532d55fd5`, merge-base `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`, target-only 8/audit-only 114. 통합 직전 fresh recheck 필요. |

## 2.2 읽는 법

- “측정 완료”와 “사전등록/대기”를 분리한다. sell D1은 측정 완료지만 target X1 buy clause-drop은 pre-measurement다. [SD1 결론표], [X1P §0, §14]
- “audit lane”과 “target lane”을 합치지 않는다. Audit G001~G010의 후보 0건 결론은 audit 범위 결론이고, prior target B1의 실전 인계 사실을 지우지 않는다. [SYN §1-2, §10], [BRF 승격 가능 후보 0건 등록부], [H3 §4]
- 같은 `X1` 이름을 구분한다. `Audit G005-X1`은 exit competing-risk descriptive PASS이고, `Target X1 buy clause-drop`은 매수식 절 삭제 엔진 A/B 사전등록이다. [SYN §5], [X1P header, §0]
- 모든 실측 수치·commit·receipt는 source alias를 붙였다. [OBS] 값은 현재 관측값으로만 기록하며, durable source에서 검증된 historical fact로 승격하지 않는다.
- 본 보고서는 문서 작성 산출물이다. 전략 등록, 엔진 실행, DB 접근, live 운용, branch integration, protected path 변경을 승인하지 않는다. [SYN §11-14], [BRF 승인 필요 작업], [X1P §11-12]

---

# 3. 한 줄 결론

**Alpha Lab의 현재 상태는 “audit에서는 승격 후보 0건, target prior lane에서는 B1만 supervised live scoring 대기, sell D1은 매도 절 제거 후보 0건을 확정, target X1 buy clause-drop은 봉인·구현된 pre-measurement 연구”다.** [SYN §1-2, §10], [BRF 승격 가능 후보 0건 등록부], [H3 §4-5], [SD1 결론표], [X1P §0, §14], [OBS]

운영적으로는 다음 한 줄이 안전하다.

> 지금 할 수 있는 것은 지식 보존과 승인된 다음 연구 준비뿐이다. 새 전략 등록, 실 DB 변경, live 운용, engine run, merge/cherry-pick/push/rebase/worktree deletion은 각각 별도 승인이 필요하다. [SYN §11-14], [BRF 승인 필요 작업], [X1P §11-12]

---

# 4. 연구 연표: prior program → audit branch → target follow-up

| 시점 / lane | 사건 | 연구적 의미 | Source |
|---|---|---|---|
| Prior program, 라운드 1~3 | 계획 `703ccbcc`부터 D1 양성 `7171a561`까지 이어진 27-commit 프로그램 체인 기록. | 발굴 시스템과 실험 discipline의 장기 계보. | [H3 §2]
| Prior program 상태 | “공장 4층 완성·14회 실증”, measure_gate → detached_runner → batch_watch → ledger 단일 경로, 원장 245행에서 handoff 시작. | 연구 생산라인 자체는 구축 완료. | [H3 §0]
| B1 마무리, 2026-07-12 | B1 엔진 A/B 4런 PASS, 2022 Δ+947,387원, 2023 Δ+591,485원, ΣΔ+1,538,872원, 매수 sha `348c5181`, 매도 sha `48018620`. | prior target lane의 유일한 empirical improvement; supervised small live start만 남음. | [H3 §4]
| D5/D9, 2026-07-13 | 437일 onset 154,027, 관측가능 116,085, parity 100.0000%; overlap ±30초 pooled 63.48%, 신규 56.16%, 재진입 63.94%가 모두 0.50 상한 초과. | “게시판 등장”은 대개 거래급증 주변에 붙는 모집단으로 판정되어 kill-3. | [H3 §5]
| O-3, 2026-07-13 | onset 702,613, gate 4/4, variant_kill 10/10, CI upper 모두 −0.83~-1.01%p. | 시초 30분 breakout onset은 L3 출구에서 강한 음의 EV. | [H3 §5]
| D1 pairwise, 2026-07-13 | #16×#37 I=+0.129%p, #16×#38 I=+0.157%p, CI 하한 +0.078/+0.090. | #16/#17 현재가 대역 절은 압력 절과의 시너지 보호 대상. | [H3 §5], [X1P §3]
| O-4, 2026-07-13 | N=158, tests 21/21, eligibility 158/158, survivors 0, best −0.734%p CI[−0.794,−0.672]. | 압력 절 결합 문법만으로 surge 음의 지형을 뒤집지 못함. | [H3 §5]
| B-track, 2026-07-13 | anchor n=114, mean +0.166%p, CI[−0.418,+0.765], 양년 동양. | 프로그램 최초 양(+) mean이나 검정력 부족으로 미결. | [H3 §5]
| B-ext, 2026-07-14 | 합동 anchor n=180, mean −0.032%p, CI[−0.503,+0.433]; 가문 13종 전략별 전부 음. | offline deep-branch mass selection 축 최종 종결. | [H3 §5]
| Audit branch G001~G010, 2026-07-16 | G001→G008, G005→G009→G010 supersession; G003 FAIL; G005-X1 descriptive noncausal nonpromotable PASS; G006 DNF_UNIDENTIFIED. | audit/knowledge/integration-prep only, promotable strategy candidate 0. | [SYN §1-3, §5-10], [BRF 목표표]
| Sell D1, 2026-07-16/17 | seal `bd5bb3c4`, generated commit `9937d6cc`, judgment reference `50383772`; load-bearing [1,3,6,8,9], B2 후보 0. | 매도식은 절 단위로 뺄 것이 없고, 출구 개선은 삭제가 아니라 추가 방향. | [SD1 header, 결론표], [H3 §5]
| Target X1 buy clause-drop, 2026-07-17 | U-7 승인 아래 DROP5/DROP15/DROP29/DROP31 단일 절 삭제 엔진 A/B 사전등록. 기준 A는 B1 A_2022/A_2023 재사용. | 매수측 “조건 삭제로 더 많이 사서 더 버는가”를 엔진으로 물을 준비. 아직 결과 없음. | [X1P header, §0, §3, §6-8, §14]
| Report-time branch observation | target `research/alpha-lab-idea5-foundation-20260707` at `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`; audit `research/alpha-lab-audit-ideas-20260714` at `e808015ce4bd62601dd75a535a57b36532d55fd5`; merge-base `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`; target-only 8/audit-only 114. | 현재 관측값일 뿐, 본 executor는 git recheck를 수행하지 않았다. 통합 직전 반드시 fresh read-only recheck 필요. | [OBS]; stale baseline comparison [SYN §14], [BRF 브랜치 기준선]

---

# 5. 한눈에 보는 outcome matrix

| Lane / 연구 | Category | 결론 | 핵심 metric / commit / receipt | Source |
|---|---|---|---|---|
| Prior program governance/factory | measured infrastructure | 발굴 시스템 4층 완성·14회 실증, discipline path 정착. | measure_gate→detached_runner→batch_watch→ledger; handoff 원장 245행. | [H3 §0]
| B1 D5-R live handoff | active/pending live scoring | 유일한 empirical improvement; supervised live scoring 대기. | 2022 Δ+947,387원, 2023 Δ+591,485원, ΣΔ+1,538,872원; buy `348c5181`, sell `48018620`. | [H3 §4]
| Buy-side D1 clause ablation | measured knowledge | 압력 절 5종 양성, 역생산 6절은 guard/selection 지식. | +0.19~0.20%p, +0.180, +0.148, +0.134; 시총<3000 단독 −0.125%p 등. | [H3 §3]
| D1 pairwise interaction | measured knowledge | #16×#37, #16×#38 시너지. | I=+0.129/+0.157%p, CI 하한 +0.078/+0.090. | [H3 §5], [X1P §3]
| O-1G gap×market-cap | negative/discarded | 양EV 증거 0, gap +20% 추격 최악. | 144셀 전 자격, 최악 −2.1%. | [H3 §3]
| D5/D9 transition onset | negative/discarded | D9는 surge와 구별되는 모집단이 아님. | onset 154,027, observable 116,085, parity 100.0000%, overlap 63.48/56.16/63.94% > 0.50. | [H3 §5]
| O-3 breakout onset | negative/discarded | 시초 30분 breakout onset은 강한 음의 EV. | onset 702,613; variant_kill 10/10; CI upper −0.83~-1.01%p. | [H3 §5]
| O-4 generation grammar | negative/discarded with knowledge | 압력 절 결합만으로 surge 음의 지형을 뒤집지 못함. | N=158, survivors 0, best −0.734%p CI[−0.794,−0.672]. | [H3 §5]
| B-track branch decomposition | unresolved/underpowered | 최초 양(+) mean이나 검정력 부족. | anchor n=114, mean +0.166%p CI[−0.418,+0.765]. | [H3 §5]
| B-ext multi-strategy expansion | unresolved/offline limit | 깊은 가지 EV는 offline 대량 선별로 확정 불가. | anchor n=180, mean −0.032%p CI[−0.503,+0.433]; 가문 13종 전부 음. | [H3 §5]
| Audit G001/G008 | governance closure | evidence-chain v2 closure, strategy authority 아님. | G008 report HEAD `86e3ee7`; G001 resolved by G008 evidence at `9db36cbd`. | [SYN §3], [BRF 목표표]
| Audit G003 | negative/discarded | fixed static `O3 OR O4` veto retired. | `delta_profit=-8,453,880`, retained 120/298, false-dropped positives 112/173. | [SYN §7-8], [BRF 확인된 지식]
| Audit G002/G004/G005-C1/C2/G006 | unresolved/nonidentified | identity/schema/trace authority 문제로 KILL/PASS 아님. | G002 671 ledger→298 cohort then timestamp failure; G006 D1 rows 863,446 snapshot only. | [SYN §5-6, §9], [BRF 미해결 질문]
| Audit G005-X1 | nonpromotable knowledge | descriptive/noncausal/nonpromotable PASS; 전략 후보 아님. | receipt `618f8aeb...`; residual ratio 0.07790204613985911; raw contrasts 2022=0.7027777777777778, 2023=0.7352685300302375. | [SYN §5], [BRF 확인된 지식]
| Audit G009/G010 | governance/contract/measurement closure | G005 original superseded, final replacement but no promotion. | G009 HEAD `81901b3d`, 61 passed; G010 HEAD `61d26005`, parent-reported 449 tests. | [SYN §5, §15], [BRF 검증·커밋·영수증]
| Target sell D1 | measured facts | 매도식은 절 단위로 뺄 것 없음; load-bearing 5절. | seal `bd5bb3c4`, generated `9937d6cc`, judgment `50383772`; load-bearing [1,3,6,8,9], B2 후보 0. | [SD1], [H3 §5]
| Current target X1 buy clause-drop | active/pending prereg | 매수식 역생산 절 4개 삭제 A/B는 결과 전. | DROP5/15/29/31; type-a ≤10; A 기준 2022 4,130,117원/101/MDD9.19, 2023 5,649,359원/197/MDD6.98. | [X1P §0, §3, §6-8, §14]
| Current branch observation | integration caution | 최신 관측값은 통합 직전 재확인 대상. | target `ccc6d7c...`, audit `e808015c...`, base `541a8d70...`, 8/114. | [OBS]; prior stale baseline [SYN §14], [BRF 브랜치 기준선]

---

# 6. 확정 측정 사실(measured facts)

## 6.1 B1은 prior target program의 유일한 empirical improvement다

B1 D5-R live handoff는 엔진 A/B 4런 전체 PASS로 기록되어 있다. 2022년은 Δ+947,387원, 거래 +1.0%, MDD 9.19→5.21이고, 2023년은 Δ+591,485원, 거래 +0.5%, MDD 6.98→8.65이며, 합산 Δ는 +1,538,872원이다. 매수식은 `348c5181` byte-exact mirror, 매도식은 `48018620`로 기록됐다. [H3 §4]

쉬운 설명: B1은 “실험실에서 두 해 모두 돈이 늘어난 것으로 측정되어 작은 실전 시험장으로 넘겨진 단 하나의 개선안”이다. 하지만 아직 사용자가 GUI에서 소액 운용을 시작하고 30거래일 채점을 끝내야 하므로 “실전 성공”은 아니다. [H3 §4]

## 6.2 Buy-side D1 clause ablation은 압력 절과 역생산 guard 지식을 남겼다

D1 절 분해는 압력 절 5종을 양성으로 기록했다. 예시는 초당매수수량>매도총잔량×0.2/0.3 계열 +0.19~0.20%p, VI아래5호가 +0.180%p, 라운드피겨 밖 +0.148%p, 초당순매수금액 +0.134%p다. 반대로 역생산 6절은 selection guard 성격으로 해석되며, 시총<3000 단독은 −0.125%p 예시로 기록됐다. [H3 §3]

쉬운 설명: 어떤 조건은 “좋은 압력”을 잡아내는 그물코였고, 어떤 조건은 혼자 보면 나빠 보이지만 전체 그물 구조에서 선택을 좁히는 역할을 할 수 있다.

## 6.3 D1 pairwise interaction은 #16/#17 보호 근거다

D1 pairwise interaction은 #16×#37 I=+0.129%p, #16×#38 I=+0.157%p, CI 하한 +0.078/+0.090으로 시너지를 기록했다. [H3 §5], [X1P §3] 따라서 target X1 buy clause-drop에서 #16과 #17 현재가 대역 족은 삭제 후보에서 제외된다. [X1P §3]

쉬운 설명: #16/#17은 혼자 보면 좋지 않아 보여도 압력 절과 짝을 이룰 때 역할이 생긴다. 그래서 “빼면 좋아질 수 있는 조건” 후보에서 보호한다.

## 6.4 Sell D1은 매도식 load-bearing 5절을 확정했다

Sell D1 판정은 정식 8절에서 제거-개선(B2 후보)이 없고, load-bearing 절이 [1, 3, 6, 8, 9]라고 기록했다. [SD1 결론표] 핵심 절별 수치는 다음과 같다.

| 절 | 설명 | Δ(%p) / CI | 판정 | Source |
|---|---|---|---|---|
| 1 | 등락율>29.5, 상한가 직전 | −1.355, CI[−1.505,−1.174] | load_bearing | [SD1 표]
| 3 | 보유>60 최저가 이탈 손절 | n=542,244, Δ−0.108, CI[−0.126,−0.090] | load_bearing | [SD1 표]
| 6 | 각도급락1 | Δ−0.212, CI[−0.331,−0.091] | load_bearing | [SD1 표]
| 8 | 각도급락3 | Δ−0.341, CI[−0.501,−0.183] | load_bearing | [SD1 표]
| 9 | MA60 이탈 익절 | Δ−0.179, CI[−0.241,−0.107] | load_bearing | [SD1 표]

절 2는 `no_detect_local_opt`, 절 4는 `no_detect_power`, 절 5는 `weak_signal`, 절 7은 `observational_report_only`로 기록됐다. [SD1 표]

쉬운 설명: 매도식은 “빼면 성과가 좋아지는 절”이 아니라 “빼면 보호 장치가 사라지는 절”을 주로 갖고 있었다. 그래서 매도 개선은 삭제가 아니라 B1 같은 추가/조합 방향이다. [H3 §5], [SD1 딱지]

## 6.5 Audit governance 측정은 strategy performance가 아니다

G008은 evidence-chain v2 governance closure이며, G001을 대체·종결했다. G008 report HEAD는 `86e3ee7`, G001은 G008 evidence at `9db36cbd`로 resolved된 historical receipt가 기록됐다. [SYN §3] 이 closure는 receipt/claim/manifest fencing과 reproducibility foundation에 관한 것이며, 전략 수익성·엔진·DB·live 권한을 만들지 않는다. [SYN §4, §11-12], [BRF 목표표]

---

# 7. 음성·폐기 결과(negative/discarded results)

| 연구 / 가설 | 폐기 또는 음성 결론 | 핵심 수치 | 유지보수자 해석 | Source |
|---|---|---|---|---|
| O-1G gap×market-cap | 양EV 증거 0, gap +20% 추격 최악. | 144셀 전 자격, 최악 −2.1%. | 시초 갭 추격은 자동 채택 금지. | [H3 §3]
| D5/D9 transition onset | surge와 구별되는 모집단 아님. | overlap ±30초 pooled 63.48%, 신규 56.16%, 재진입 63.94% > 0.50. | 게시판/전이 온셋은 독립 alpha가 아니라 거래급증 주변 현상. | [H3 §5]
| O-3 breakout onset | L3 출구에서 강한 음의 EV. | onset 702,613; variant_kill 10/10; CI upper −0.83~-1.01%p. | “돌파 시작” 추격은 비용 벽을 넘지 못하는 함정. | [H3 §5]
| O-4 pressure grammar | 생존 0. | N=158, eligibility 158/158, best −0.734%p CI[−0.794,−0.672], type-a 0. | 검증된 압력 절 결합만으로 surge 음의 지형을 뒤집지 못한다. | [H3 §5]
| Audit G003 `O3 OR O4` static veto | FAIL, fixed veto family retired. | `delta_profit=-8,453,880`, retained 120/298, false-dropped positive trades 112/173. | 이 veto를 entry drop driver로 쓰면 가치 훼손 위험. | [SYN §7-8], [BRF 확인된 지식]
| Sell D1 “exit clause removal improves performance” | 제거-개선 후보 0. | load-bearing [1,3,6,8,9], B2 후보 없음. | 매도식 절 삭제로 개선한다는 방향은 닫혔다. | [SD1 결론표], [H3 §5]

음성 결과의 중요한 사용법: “틀렸다”가 아니라 “이 방향으로 자동 승격하면 안 된다”는 안전 표지다. 특히 O-4의 best −0.734%p는 개선 여지가 조금 보인다는 뜻이 아니라, 비용 벽의 절반도 넘지 못해 survivor 0이라는 뜻으로 읽어야 한다. [H3 §5]

---

# 8. 미해결·비식별 work(unresolved/nonidentified)

| Item | 현재 terminal label / 상태 | 빠진 authority 또는 한계 | 다음 permissible framing | Source |
|---|---|---|---|---|
| B-track branch decomposition | unresolved / underpowered | n=114, mean +0.166%p이나 CI[−0.418,+0.765]가 0을 걸침. | 확정 positive EV가 아니라 “챔피언 특이 또는 잡음 가능성이 있는 양(+) mean.” | [H3 §5]
| B-ext multi-strategy expansion | offline limit closure | 합동 n=180, mean −0.032%p CI[−0.503,+0.433]; 가문 13종 전부 음. | offline deep branch mass selection 축은 닫힘. 비가문 원문 확보 전 재개 금지. | [H3 §5]
| Audit G002 U7-F0 bridge | `UNDETERMINED` | 671 ledger rows→298 fixed cohort 후 timestamp identity failure. | 새 preregistration과 새 attempt ID 없이는 rescue/rerun 금지. | [SYN §7, §9], [BRF 미해결 질문]
| Audit G004 P1/M1/S1 | `UNDETERMINED / dependency nonidentification` | G002 common cohort 부재로 denominator/estimand/outcome support 없음. | 승인된 G002-like common cohort 성공 뒤에만 재검토. | [SYN §9], [BRF 미해결 질문]
| Audit G005-C1 | `UNDETERMINED / INPUT_SCHEMA_MISMATCH` | `t0` schema/identity handling 실패, input artifact 없음. | 새 sealed path 승인 전까지 retry 권한 없음. | [SYN §5], [BRF 미해결 질문]
| Audit G005-C2 | `UNDETERMINED / nonidentified` | clause16/37/38 exact first-activation timestamp/trace authority 없음. | activation-trace authority project가 최고 정보가치 후속. | [SYN §5, §9, §13], [BRF 마지막 결정 제안]
| Audit G006-C3/C4 | `UNDETERMINED / DNF_UNIDENTIFIED`, C4 `CLOSED` | D1 bits는 code/day/off/t0 + bit_1..bit_39 final snapshot일 뿐, true-DNF/stateful activation authority가 아님. | formal C3 survivor와 exact timestamp gate 전에는 C4 outcome/metric read 금지. | [SYN §6, §9], [BRF 미해결 질문]
| Target X1 buy clause-drop | active/pending pre-measurement | B_2022/B_2023 변형 metrics와 `x1_ab_verdict.json` 결과가 아직 report source에 없음. | 봉인 후 측정이 별도 집행되어 verdict artifact가 생기기 전까지 결과 언급 금지. | [X1P §6-8, §14], [OBS]

쉬운 설명: “미해결”은 “나쁜 결과”가 아니다. 필요한 신분증이나 시계가 없어서 판정을 못 한 상태다. 특히 activation order 문제는 flat D1 bit/off/t0로 대신 만들 수 없다. [SYN §5-6], [BRF 폐기된 가설·금지된 추론]

---

# 9. 비승격 지식(nonpromotable knowledge)

| 지식 | 무엇을 알게 되었나 | 왜 승격 불가인가 | Source |
|---|---|---|---|
| Audit G005-X1 exit competing-risk | residual ratio 0.07790204613985911, raw contrasts 2022=0.7027777777777778 / 2023=0.7352685300302375, signs +/+로 descriptive PASS. | claim type이 descriptive/noncausal/nonpromotable; counterfactual exit adoption, strategy candidate, engine/DB/registration/promotion 권한 없음. | [SYN §5], [BRF 확인된 지식]
| Evidence-chain v2 governance | receipt/claim/manifest fencing과 legacy fencing 기반이 정리됨. | governance foundation일 뿐 수익성, live success, strategy authority가 아님. | [SYN §4, §7, §11-12], [BRF 목표표]
| G006 D1 final-bit snapshot | D1 bits file은 rows 863,446, schema code/day/off/t0 + bit_1..bit_39로 bound. | final snapshot은 exact first activation timestamp/trace authority가 아니므로 C2/C3/C4를 열 수 없음. | [SYN §6]
| O-4 grammar map | 압력 절 결합 158개 문법족이 survivor 0이라는 지형 지식. | 후보가 없고 type-a 0이므로 strategy candidate가 아님. | [H3 §5]
| Sell D1 load-bearing map | 매도식의 보호 절 5개와 제거-개선 0이 확정됨. | 전략 performance result나 new candidate가 아니라 clause contribution diagnosis. | [SD1 결론표, 딱지], [H3 §5]

비승격 지식은 버리는 지식이 아니다. 유지보수자는 이 지식을 “하지 말아야 할 shortcut”과 “다음 연구 설계의 guardrail”로 써야 한다. [SYN §11-13], [BRF 폐기된 가설·금지된 추론]

---

# 10. 활성·대기 work(active/pending)

| Work | 현재 상태 | 남은 gate | 금지되는 말 | Source |
|---|---|---|---|---|
| B1 supervised live scoring | 사용자 GUI 소액 운용 개시와 30거래일 채점 대기. | U-4 supervised small live 운영 절차, 킬스위치, 기록 양식 준수. | “B1 live 성공 확정.” | [H3 §4]
| Target X1 buy clause-drop | 봉인·구현되었으나 pre-measurement라는 report-time observation. 후보 DROP5/DROP15/DROP29/DROP31. | 봉인 후 변형 생성·검증→measure_gate→분리 runner A/B≤10→verdict→후보 시 U-4 별도 승인. | “X1 PASS”, “X1 후보 승격 완료”, “삭제로 성능 개선 입증.” | [X1P §0, §3, §6-8, §14], [OBS]
| Activation-trace authority project | Audit G005-C2/G006-C3/C4의 최고 정보가치 후속. | outcome-blind, source-hashed exact first activation timestamp/stateful trace authority, 새 preregistration. | “flat39/off/t0로 activation order를 복원했다.” | [SYN §13], [BRF 마지막 결정 제안]
| P4 dashboard | go 대기. | 사용자 go와 기존 PR 조율. | 연구 결과나 strategy authority로 포장. | [H3 §5 WBS row]
| Engine frame research | U-7 계열 새 봉인 필요. | 별도 사전등록·승인. | 현 보고서가 engine run을 승인했다는 말. | [H3 §0, §5]

---

# 11. 승인 상태와 protected-surface boundary

## 11.1 승인 상태

| Surface / action | 현재 권한 | 필요한 승인 | Source |
|---|---|---|---|
| Audit G001~G010 strategy promotion | 권한 없음, 후보 0. | promotable candidate와 별도 maintainer/user approval 필요. | [SYN §10-12], [BRF 승격 가능 후보 0건 등록부]
| B1 supervised live | 사용자 GUI 소액 운용 개시만 남은 prior handoff. | 30거래일 scoring 전 success claim 금지. | [H3 §4]
| Target X1 engine budget | U-7 engine budget 승인 존재, type-a ≤10 봉인. | 실제 DB 등록/live transition은 U-4 별도 승인. | [X1P header, §7-8, §11-14]
| Scratch strategy.db | X1 변형 등록은 scratch only. | 실 `_database/strategy.db` 등록은 U-4 전 금지. | [X1P §4, §11]
| Protected DB / live / broker / registration | 현 보고서로 권한 없음. | 별도 명시 승인과 gate 필요. | [SYN §11-12], [BRF 승인 필요 작업]
| Branch integration | 현 보고서로 권한 없음. | merge/push/rebase/squash/cherry-pick into target/target mutation/worktree deletion은 maintainer explicit approval와 fresh read-only recheck 필요. | [SYN §14], [BRF 브랜치 기준선]

## 11.2 Protected surfaces

다음은 문서가 아무리 상세해도 자동으로 열리지 않는다.

- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, runtime sidecars. Project protected path policy와 audit approval boundary에 따른다. [SYN §11-14], [BRF 승인 필요 작업]
- 2024/2025 창은 blind validation이 아니다. 2024는 known/selection 또는 veto/audit-only, 2025-01~2026-02는 known/OOS opened 상태로 취급한다. [H3 §1], [X1P §1]
- 실전 최종 심판은 별도 승인된 supervised small live trading이고, 30거래일 scoring 전 성공 주장은 금지된다. [H3 §1, §4], [X1P §12]

쉬운 설명: 이 보고서는 지도다. 지도에 항구가 그려져 있어도 배를 출항시키는 허가증은 아니다.

---

# 12. Prior Alpha Lab program 상세

## 12.1 프로그램 목적과 규율

Prior Alpha Lab program은 기존 DB만 사용하고, 수집/백필/코인 작업을 하지 않으며, 측정은 사전등록 봉인 후에만 수행하는 원칙을 갖는다. 최종 심판은 감독형 소액 실전이며, known 2025-01~2026-02와 청산 레버 계열 2024는 veto/audit only로 제한된다. [H3 §1]

발굴 시스템은 4층 공장으로 정리됐다. 한 줄 상태는 “공장 완성·14회 실증, 라운드 6 종결, 깊은 가지 offline EV 확정 불가, B1만 유일한 실증 개선”이다. [H3 §0]

## 12.2 Commit chain

프로그램 commit chain은 다음 historical receipt로 보존된다. [H3 §2]

- 라운드 1: `703ccbcc` 계획 → `0608043c` 원장 → `721db080` W1+W2 → `0b8dcd43` W3 봉인 → `4a7ae6c0` v1 파일럿 → `3a9b7843` 칸-조준 kill-2 → `fa09f5ca` 플랜 v2. [H3 §2]
- 감사: `0f89796e` 타당성 감사 → `0e087d23` C-0 반영 → `bb0778ef` W3-R+V2-A 봉인 → `303c5fba` V2-B → `f553378b` V2-C KILL(0/2). [H3 §2]
- 라운드 2: `8bc8dbb9` R15/16+O-1G 봉인 → `8b95eb09`+`a1fe15c8` 엔진 검수+2U 대조 → `ac5ca448` D5-R 봉인 → `3ade1286` 프로브 생존 → `c5e6a4c3`+`87165d35` 백로그 → `4ee6ed80` W5 → `19138c90` O-1G 양EV 0 → `951c9748` D5-R kill-2(B1 주목) → `b70c6c05` 핸드오프. [H3 §2]
- 라운드 3: `56564cba` D1 봉인 → `47d871dd` O-1G 코드 정리 → `7171a561` D1 양성. [H3 §2]

## 12.3 확정 판정

| 판정 | 결과 | Source |
|---|---|---|
| 칸-조준(시간대×등락율×시총) | 2개 라벨 h300/L3 교차 KILL. | [H3 §3]
| O-1G | 144셀 전 자격, 양EV 증거 0, gap +20% 추격 최악 −2.1%. | [H3 §3]
| D1 절 분해 | 압력 절 5종 양성, 역생산 6절은 선정 guard 성격. | [H3 §3]
| D5-R 청산 8후보 | 전부 kill-2, B1만 실전 이관. | [H3 §3-4]
| RR8 3형제 병합 | 중복 97.6~100%, 순증분 +1%, 무가치. | [H3 §3]
| min·D9 probe | min audit-grade 전용, D9 일치 100%·재진입 관측 75.75%. | [H3 §3]

## 12.4 B1 상세

B1은 `ALP_D5R_B1_S` sell pair로 등록되었고, INSERT-only와 sha 검증, 백업 `strategy.db.bak.alpha_lab_20260712T213918`, evidence path `research_runs/alpha_restart_20260710/d5r_b1_live/`가 기록됐다. [H3 §4] 하지만 남은 단계는 user GUI에서 정본 페어링(매수 `ALP_V4_RR8_12` + 매도 `ALP_D5R_B1_S`)으로 소액 운용을 시작하고 30거래일 채점하는 것이다. [H3 §4]

## 12.5 라운드 5~7과 대기열

B-track은 anchor n=114, mean +0.166%p, CI[−0.418,+0.765]로 최초 양(+) mean이지만 미결이다. [H3 §5] B-ext는 합동 anchor n=180, mean −0.032%p, CI[−0.503,+0.433]이고 가문 13종 전부 음이라 offline 대량 선별 축을 닫았다. [H3 §5] Sell D1은 라운드 7로 편입되어 seal `bd5bb3c4`, harness `9937d6cc`, judgment `50383772`, load-bearing [1,3,6,8,9], B2 후보 0을 남겼다. [H3 §5], [SD1]

다음 대기열은 B1 실전 운용·30거래일 scoring, 매수측 X1 절 삭제 A/B, engine frame 연구, P4 dashboard, 조건부 B-ext 재개다. [H3 §5]

---

# 13. Audit-branch G001~G010 상세

## 13.1 Audit final assertion

Audit branch의 frozen evidence는 “promotable strategy candidate 없음, integration은 audit/knowledge/prep-only, future progress requires separately approved authority work”라는 결론만 지지한다. [SYN §15.4]

## 13.2 Goal별 상세

| Goal | Terminal disposition | 핵심 evidence | 하지 말아야 할 해석 | Source |
|---|---|---|---|---|
| G001 | G008로 superseded/resolved. | G001 resolved by G008 evidence at `HEAD 9db36cbd`; G008 report records code contribution HEAD `86e3ee7`. | 독립 strategy result로 해석 금지. | [SYN §3]
| G002 | `UNDETERMINED`, identity integrity failure. | 671 champion ledger rows parsed, 298 fixed cohort selected, float `매수시간=20220323090127.0`가 exact timestamp 요구 실패. | KILL/PASS/FAIL 통계 결과로 재라벨 금지. | [SYN §7, §9], [BRF 확인된 지식]
| G003 | `FAIL`, fixed static `O3 OR O4` veto retired. | `delta_profit=-8,453,880`, retained 120/298, false-dropped positive trades 112/173. | reweight/reselect/rescue로 같은 family 부활 금지. | [SYN §7-8], [BRF 폐기된 가설]
| G004 | `UNDETERMINED / dependency nonidentification`. | G002 common cohort 부재로 P1/M1/S1 all identified=false. | fabricated common cohort 금지. | [SYN §9], [BRF 미해결 질문]
| G005 original | G009/G010으로 superseded. | original G005를 final measurement authority로 쓰지 않음. | original G005를 후보나 ledger authority로 사용 금지. | [SYN §3, §5]
| G005-C1 | `UNDETERMINED / INPUT_SCHEMA_MISMATCH`. | builder exit 1, `ValueError: t0 must be a nonempty string`, target/finalizer/receipt/claim/runlab 미실행. | failed synergy 또는 passed synergy로 말하지 않음. | [SYN §5]
| G005-X1 | descriptive/noncausal/nonpromotable `PASS`. | receipt `618f8aeb...`, residual ratio 0.07790204613985911, raw contrasts 2022=0.7027777777777778 / 2023=0.7352685300302375, signs +/+. | causal, counterfactual, strategy, registration, promotion 금지. | [SYN §5], [BRF 확인된 지식]
| G005-C2 | `UNDETERMINED / nonidentified`. | exact first activation timestamp for clause16/37/38, outcome, pre-existing trace authority 없음. | flat D1 bit/off/t0 proxy 사용 금지. | [SYN §5], [BRF 미해결 질문]
| G006 | `UNDETERMINED / DNF_UNIDENTIFIED`, C4 closed. | D1 rows 863,446, schema code/day/off/t0 + bit_1..bit_39, final-bit snapshot only. | motif 실패나 C4 opportunity failure로 해석 금지. | [SYN §6], [BRF 목표표]
| G008 | evidence-chain v2 closure. | authority review 153 PASS, runner 190 PASS, cited 13/396/921 passed histories. | strategy promotion, protected DB, engine, live authority 금지. | [SYN §3, §15], [BRF 검증·커밋]
| G009 | sealed measurement contract repair only. | HEAD `81901b3d`, focused 61 passed after commit. | final measurement 자체나 promotion authority로 해석 금지. | [SYN §5, §15], [BRF 검증·커밋]
| G010 | authoritative final G005 replacement. | completion HEAD `61d26005`, parent-reported 449 tests passed; G005 artifacts bound to `25975531...`. | no promotion, no engine/DB/registration/retry/rescue. | [SYN §5, §15], [BRF 검증·커밋]

## 13.3 Audit no-candidate register

Audit branch의 promotable STOM strategy candidate는 0이다. Retired/failed family는 G003 static `O3 OR O4` veto 1개, nonpromotable knowledge는 G005-X1 descriptive PASS 1개, research follow-up idea는 activation trace/timestamp authority project 1개로 요약된다. [SYN §10], [BRF 승격 가능 후보 0건 등록부]

---

# 14. Post-audit target sell D1 상세

Sell D1 문서는 “매도식 D1 판정 — 절-단위 ablation (봉인 `bd5bb3c4`)”로 생성되었고, 생성 시각은 2026-07-16T20:42:21+00:00, commit은 `9937d6cc`로 기록됐다. [SD1 header]

## 14.1 핵심 판정

- 제거-개선(B2 후보): 없음. [SD1 결론]
- load-bearing: [1, 3, 6, 8, 9]. [SD1 결론]
- kill-1(절 단위 국소 최적): False. [SD1 결론]
- H3 handoff는 sell D1 judgment reference `50383772`와 “매도식은 절 단위 뺄 것 없음”을 기록했다. [H3 §5]

## 14.2 절별 해석

절 3 “보유>60 최저가 이탈 손절”은 n=542,244, Δ−0.108, CI[−0.126,−0.090]로 지배 절이지만 load-bearing이다. [SD1 표] 즉 give-back의 범인이 아니라 수호자라는 해석이 H3에 기록됐다. [H3 §5]

절 1, 6, 8, 9도 각각 상한가 직전, 각도급락, MA60 이탈 계열의 보호 기능을 보인다. [SD1 표] 절 2/4/5/7은 개선 후보가 아니라 no-detect/weak/observational 영역이다. [SD1 표]

## 14.3 딱지와 한계

Sell D1은 성능 주장이나 실전 수익 주장이 아니다. 조건은 surge onset × champion buy lineage × original sell context에 묶여 있으며, 온셋 replay는 엔진 진입 frame을 담지 않는다. B2 승격은 별도 engine A/B(type-a ≤8)와 U-4 실전 심판이 필요하다는 딱지가 강제 인쇄되어 있다. [SD1 딱지]

쉬운 설명: sell D1은 “매도 규칙 중 버릴 수 있는 부품을 찾는 분해 검사”였다. 결과는 “버릴 부품 없음, 몇몇 부품은 보호 장치”다. 이것은 새 자동차가 완성됐다는 말이 아니라, 기존 브레이크를 빼면 위험하다는 정비 기록이다.

---

# 15. Current X1 buy clause-drop preregistration 상세

## 15.1 상태

Target X1 buy clause-drop은 매수식 `ALP_V4_RR8_12`(buy sha `348c5181...`)에서 D1이 역생산으로 판정한 절 중 시너지 보호절을 제외한 4개를 하나씩 삭제해 엔진 A/B로 직접 재는 사전등록이다. [X1P header, §0, §3]

Parent가 제공한 current observation에 따르면 current target HEAD에서 X1은 sealed/implemented 상태이나, 측정 결과는 아직 pre-measurement다. 이 관측은 본 보고서에서 [OBS]로만 태깅하며, X1 결과를 뜻하지 않는다. [OBS]; 사전등록 경계 [X1P §6-8, §14]

## 15.2 후보 4개

| 후보 | D1 절 | 술어 | 가지 소속 / 제거 방식 | D1 Δ와 유입 한계 | Source |
|---|---|---|---|---|---|
| DROP5 | #5 | 시가총액 < 3000 | 902+905 공통 gate; `if 시가총액<3000` 무력화. | Δ−0.125, mean_unsat −0.959, n_unsat 528,237. | [X1P §3, §5, §14]
| DROP15 | #15/#39 | 회전율 > 1.5 | 902+905 공통 guard line 삭제. | Δ−0.120, mean_unsat −0.940, n_unsat 377,733. | [X1P §3, §5, §14]
| DROP29 | #29 | 매도총잔량*0.1 < 매수총잔량 | 905 단독 simple line 삭제. | Δ−0.167, mean_unsat −0.841, n_unsat 3,687. | [X1P §3, §5, §14]
| DROP31 | #31 | 매도총잔량 > 매수총잔량*0.1 | 902 단독 #30 AND 복합 line에서 #31만 제거, #30 보존. | Δ−0.238, mean_unsat −0.770, n_unsat 2,122. | [X1P §3, §5, §14]

제외 절 #16/#17은 현재가 대역 족이며 #16×#37, #16×#38 시너지가 있으므로 삭제 후보에서 보호된다. [X1P §3], [H3 §5]

## 15.3 기준 A와 판정 기준

기준 A는 B1 A/B의 A_2022/A_2023을 재사용한다. 기록된 A 기준은 2022 총수익 4,130,117원, 101거래, MDD 9.19%; 2023 총수익 5,649,359원, 197거래, MDD 6.98%다. [X1P §6]

X1 후보가 되려면 후보별로 2022와 2023 각각에서 Δ총수익>0, 거래수 증가율 ≤+300%, MDD_B ≤ MDD_A×1.5 및 MDD_B ≤15%, A/B status success를 통과해야 한다. [X1P §7, §14] 예산은 후보 4×연도 2=8런 + 예비 2, type-a ≤10이다. [X1P §8, §14]

## 15.4 금지 범위

X1 라운드에서 금지되는 것은 시너지 보호 절 삭제, 2절 이상 동시 삭제, 신규 조건 추가, 매도식 변경, 실 `_database/strategy.db` 등록, 2024/2025 측정, 문턱 사후 조정, engine budget 초과다. [X1P §11]

쉬운 설명: X1은 “매수 그물코 4개를 하나씩 넓혀 실제로 더 많이 잡아 더 버는지 보자”는 계획이다. 아직 그물을 던져서 잡은 결과표는 없다. 따라서 X1에 대해 말할 수 있는 것은 후보, 기준 A, 판정 기준, 승인 경계뿐이다. [X1P §0, §6-8, §14]

---

# 16. 충돌처럼 보이는 지점과 시간순 해소

| Apparent conflict | 왜 충돌처럼 보이나 | 해소 문구 | Source |
|---|---|---|---|
| Audit은 “승격 가능한 후보 0건”인데 H3는 B1 실전 인계를 말한다. | audit G001~G010과 prior target program lane의 scope가 다르다. | “Audit branch produced no promotable candidate. Separately, prior target program B1 remains the only empirical improvement handed to supervised live workflow; 30거래일 채점 전 성공 주장은 금지.” | [SYN §1-2, §10], [BRF 승격 가능 후보 0건 등록부], [H3 §4]
| Audit `G005-X1 PASS`와 target `X1 buy clause-drop`이 둘 다 X1이다. | 같은 label을 다른 연구가 썼다. | “Audit G005-X1 exit competing-risk descriptive PASS”와 “Target X1 buy clause-drop A/B preregistration, not yet measured”를 항상 분리한다. | [SYN §5], [X1P header, §0]
| Audit baseline의 target `bd5bb3c4`와 sell D1 `9937d6cc`/`50383772`가 다르다. | audit report는 특정 시점의 target baseline을 기록했고, target lane은 이후 sell D1 구현/판정을 기록한다. | `bd5bb3c4`는 sell D1 seal 및 이전 target baseline 관측값이고, `9937d6cc`는 sell D1 report commit, `50383772`는 H3 judgment reference다. audit baseline을 current target state로 취급하지 않는다. | [SYN §14], [SD1 header], [H3 §5]
| Audit의 최고 후속은 activation trace authority인데, target의 다음 작업은 X1 buy clause-drop이다. | 병목이 다르다. | Activation trace authority는 audit G005-C2/G006-C3/C4를 여는 research authority project이고, X1 buy-drop은 target-engine A/B lane이다. | [SYN §13], [BRF 마지막 결정 제안], [X1P §0, §14]
| Sell D1이 양성인데 B2 후보 0이다. | “양성”이 성능 후보를 뜻한다고 오해할 수 있다. | Sell D1의 양성은 load-bearing exit clauses를 찾았다는 뜻이고, removal-improvement candidate는 0이다. | [SD1 결론표], [H3 §5]
| H3 상단은 ledger 245행, sell D1 row는 ledger 253행을 말한다. | handoff top summary와 later row가 다른 chronology를 반영한다. | 상단 원장 245행은 handoff 시작 상태이고, sell D1 row의 253행은 후속 편입 상태다. 숫자를 하나로 덮어쓰지 않는다. | [H3 §0, §5]
| Source baseline은 target-only 2/audit-only 112인데 parent observation은 8/114다. | source 문서는 pre-G007 or previous baseline이고, parent는 report-time observation을 제공했다. | 이 보고서는 parent observation을 현재 관측값으로 별도 표시하되, integration 전 fresh read-only recheck가 최종 authority다. | [SYN §14], [BRF 브랜치 기준선], [OBS]

---

# 17. Key metrics / commits / receipts index

| Area | Key facts to preserve | Source |
|---|---|---|
| Program commit chain | `703ccbcc`→`0608043c`→`721db080`→`0b8dcd43`→`4a7ae6c0`→`3a9b7843`→`fa09f5ca`; audit `0f89796e`→`0e087d23`→`bb0778ef`→`303c5fba`→`f553378b`; round2 `8bc8dbb9`→`8b95eb09`/`a1fe15c8`→`ac5ca448`→`3ade1286`→`c5e6a4c3`/`87165d35`→`4ee6ed80`→`19138c90`→`951c9748`→`b70c6c05`; round3 `56564cba`→`47d871dd`→`7171a561`. | [H3 §2]
| B1 | 2022 Δ+947,387원, 거래 +1.0%, MDD 9.19→5.21; 2023 Δ+591,485원, 거래 +0.5%, MDD 6.98→8.65; ΣΔ+1,538,872원; `ALP_D5R_B1_S`; buy `348c5181`, sell `48018620`. | [H3 §4]
| D5/D9 | 437일 onset 154,027; 관측가능 116,085; parity 100.0000%; overlap ±30초 pooled 63.48%, 신규 56.16%, 재진입 63.94% > 0.50. | [H3 §5]
| O-3 | onset 702,613; gates 4/4; variant_kill 10/10; CI upper 전부 negative; surge overlap P20 97.5%~OP 95.1%, VI 50.7%. | [H3 §5]
| O-4 | N=158; tests 21/21; eligibility 158/158; survivors 0; best −0.734%p CI[−0.794,−0.672]; type-a 0. | [H3 §5]
| B-track / B-ext | B-track anchor n=114 mean +0.166%p CI[−0.418,+0.765]; B-ext anchor n=180 mean −0.032%p CI[−0.503,+0.433]. | [H3 §5]
| Audit source baseline | pre-G007 audit baseline `61d26005a26799e9e13ddaca423873850fae834f`; primary G007 doc `f10e41d7`; target baseline `bd5bb3c4bc9253034326eadfe8afdfd4605258c4`; merge base `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`; divergence target-only 2/audit-only 112. | [SYN §14], [BRF 브랜치 기준선]
| Report-time branch observation | target `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`; audit `e808015ce4bd62601dd75a535a57b36532d55fd5`; merge-base `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`; target-only 8/audit-only 114. Must be freshly rechecked before integration. | [OBS]
| Audit G003 | `delta_profit=-8,453,880`; retained 120/298; false-dropped positive trades 112/173; O4 equivalence mismatch 0. | [SYN §7], [BRF 확인된 지식]
| Audit G005-X1 | receipt `618f8aeb...`; residual ratio `0.07790204613985911`; raw contrasts 2022 `0.7027777777777778`, 2023 `0.7352685300302375`; signs +/+. | [SYN §5], [BRF 확인된 지식]
| Audit G006 | D1 snapshot SHA `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56`; rows 863,446; schema `code/day/off/t0 + bit_1..bit_39`; clause dictionary SHA `def0f5c8750c19c02b52f026461422572641b36730d28e5bdfa97f20deabb7d4`. | [SYN §6]
| Audit G009/G010 | G009 HEAD `81901b3d`, focused 61 passed; G010 completion HEAD `61d26005`, parent-reported 449 tests; G005 artifacts bound to `25975531...`. | [SYN §5, §15], [BRF 검증·커밋]
| Target sell D1 | seal `bd5bb3c4`; generated commit `9937d6cc`; judgment reference `50383772`; load-bearing [1,3,6,8,9]; B2 removal-improvement candidates none. | [SD1 header, 결론표], [H3 §5]
| Sell D1 clauses | §1 Δ−1.355 CI[−1.505,−1.174]; §3 n=542,244 Δ−0.108 CI[−0.126,−0.090]; §6 Δ−0.212; §8 Δ−0.341; §9 Δ−0.179. | [SD1 표]
| Target X1 prereg | buy sha `348c5181`, sell original `8ef01e0e`; candidates DROP5/DROP15/DROP29/DROP31; type-a ≤10; scratch strategy.db only; no 2024/2025 measurement. | [X1P §0, §3-8, §11, §14]
| Target X1 기준 A | 2022 total_profit 4,130,117원 / 101 trades / MDD 9.19%; 2023 total_profit 5,649,359원 / 197 trades / MDD 6.98%. | [X1P §6]

---

# 18. Forbidden overclaims and safe wording

| Forbidden overclaim | Safe wording |
|---|---|
| “Audit branch found a promotable STOM strategy.” | “Audit G001~G010 produced no promotable STOM strategy candidate; it produced governance closure, one discarded veto family, unresolved/nonidentified branches, and nonpromotable descriptive knowledge.” [SYN §1-2, §10] |
| “G005-X1 proves an actionable strategy.” | “Audit G005-X1 is descriptive, noncausal, nonpromotable PASS only.” [SYN §5] |
| “Target X1 already passed.” | “Target X1 buy clause-drop is sealed/implemented but pre-measurement; no result yet.” [X1P §0, §14], [OBS] |
| “B1 is proven live-successful.” | “B1 is the only empirical improvement handed to supervised live workflow; 30 trading-day scoring is still required before success claims.” [H3 §4] |
| “Sell D1 says remove exit clauses.” | “Sell D1 says no removal-improvement candidate; five clauses are load-bearing.” [SD1 결론표] |
| “Sell D1 is a strategy performance result.” | “Sell D1 is clause contribution diagnosis under surge onset × champion buy lineage × original sell context.” [SD1 딱지] |
| “O-4 pressure grammar nearly works.” | “O-4 had zero survivors; best candidate remained negative and below the cost wall.” [H3 §5] |
| “B-track champion +0.166 is confirmed positive EV.” | “B-track +0.166 was underpowered with CI crossing zero; B-ext showed offline deep-branch limit.” [H3 §5] |
| “G002/G004/G005-C1/C2/G006 failed statistically.” | “They are unresolved/nonidentified due identity/schema/trace authority gaps; KILL/PASS was not evaluated unless explicitly stated.” [SYN §5-6, §9] |
| “Activation order can be inferred from flat D1 bits/off/t0.” | “Flat snapshots/off/t0 are not first-activation trace/timestamp authority.” [SYN §5-6], [BRF 폐기된 가설] |
| “2024/2025 are blind validation.” | “2024/2025 are known/veto/audit-only in these sources; blind/OOS success claims are forbidden.” [H3 §1], [X1P §1] |
| “The report author reran tests/git/engine.” | “This report cites historical receipts from sources; no new commands/tests/engine/git were run for this documentation assignment.” |
| “Documentation commit authorizes merge/integration.” | “Documentation-only work is not integration approval; merge/push/rebase/squash/cherry-pick/worktree deletion require separate maintainer approval and fresh recheck.” [SYN §14], [BRF 승인 필요 작업] |
| “Scratch or prereg approval authorizes real DB registration.” | “Scratch strategy.db or U-7 engine approval does not authorize real `_database/strategy.db` registration or live operation; U-4/user approval is separate.” [X1P §4, §11-14] |

---

# 19. Maintainer handoff checklist

- [ ] Preserve the source aliases [SYN], [BRF], [H3], [SD1], [X1P], and keep [OBS] explicitly labeled as report-time observation requiring fresh recheck.
- [ ] Keep audit lane and target lane separate in any branch handoff or integration note.
- [ ] State audit G001~G010 candidate count as 0; do not let that erase B1’s prior target live-handoff status.
- [ ] Use “Audit G005-X1 exit competing-risk descriptive PASS” and “Target X1 buy clause-drop pre-measurement” as distinct names.
- [ ] Do not call target X1 measured until B_2022/B_2023 metrics and `x1_ab_verdict.json` or equivalent verdict artifact exist.
- [ ] Do not call B1 live successful before 30 trading-day supervised scoring evidence exists.
- [ ] Do not convert sell D1 load-bearing knowledge into a strategy promotion or exit-removal recommendation.
- [ ] Do not open C4, infer activation order, or construct first-activation traces from flat D1 bits/off/t0 without a separately approved authority project.
- [ ] Do not run engine, touch protected DB/runtime paths, register strategies, or start live trading from this report.
- [ ] Before any approved integration, freshly recheck branch HEAD/base/divergence; do not rely on stale [SYN]/[BRF] baseline or unverified [OBS] values as execution authority.
- [ ] Preserve detailed evidence chain; do not squash or delete audit evidence without explicit maintainer approval.
- [ ] If future checks are run, label them as newly run checks and keep them separate from historical source-reported receipts.

---

# 20. Appendix: source manifest

## 20.1 Full source list

1. [MAP] `agent://366-ResearchReportContentMap` — structure/content contract for this report. It requested 20 sections, source manifest, chronology, outcome matrix, measured/negative/unresolved/nonpromotable/active approval separation, conflict resolution, key metrics index, forbidden overclaims, checklist, appendix.
2. [SYN] `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/2026-07-16_alpha_lab_final_research_synthesis.md` — audit G001~G010 final synthesis and integration-prep boundaries.
3. [BRF] `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/2026-07-16_alpha_lab_management_briefing.md` — management summary, no-candidate register, protected-surface and approval summary.
4. [H3] `docs/research/condition_research/plans/2026-07-12_program_handoff_v3.md` — prior Alpha Lab program canonical handoff, B1, D1, O-series, B-track/B-ext, sell D1 handoff row.
5. [SD1] `docs/research/condition_research/research_runs/alpha_restart_20260710/sell_d1/sell_d1_report.md` — sell D1 clause ablation final report.
6. [X1P] `docs/research/condition_research/plans/2026-07-17_x1_buy_clause_drop_ab_preregistration.md` — current X1 buy clause-drop A/B preregistration and boundary.
7. [OBS] Parent-supplied report-time observation — target branch `research/alpha-lab-idea5-foundation-20260707` at `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`; audit branch `research/alpha-lab-audit-ideas-20260714` at `e808015ce4bd62601dd75a535a57b36532d55fd5`; merge-base `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`; divergence target-only 8/audit-only 114. This is not a durable file source and must be freshly rechecked before integration.

## 20.2 Report author process boundary

This documentation assignment created only this Markdown report. It did not run historical research, tests, gates, formatters, git commands, engine runs, DB reads/writes, workflow state changes, or live/supervised trading. Historical receipts and test counts are cited only as source-reported facts. [SYN §15], [BRF 검증·커밋·영수증]

## 20.3 Final safe summary

The safe maintainer summary is:

> Preserve the audit conclusion of zero promotable candidates; preserve B1 as the only prior empirical improvement pending supervised live scoring; preserve sell D1 as load-bearing/no-removal knowledge; preserve target X1 as sealed/implemented but not yet measured; require separate approvals and fresh rechecks before any engine, DB, live, registration, promotion, or branch integration action. [SYN §1-2, §10-14], [BRF 승인 필요 작업], [H3 §4-5], [SD1], [X1P §0, §11-14], [OBS]
