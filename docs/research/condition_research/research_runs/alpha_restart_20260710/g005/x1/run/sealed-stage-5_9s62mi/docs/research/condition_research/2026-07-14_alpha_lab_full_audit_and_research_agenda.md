# 알파랩 전수 감사 및 후속 연구 의제 보고서

- 작성일: 2026-07-14
- 기준 커밋: `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`
- 대상 브랜치: `research/alpha-lab-audit-ideas-20260714`
- 문서 지위: **1차 결과 보고서를 심층 증거 감사와 창의적 연구 의제로 갱신한 개선판 v1.0**
- 범위: 문서·코드·기존 측정 산출물의 read-only 감사. 신규 시장 데이터 수집, 엔진 실행, 보호 DB 쓰기는 수행하지 않았다.
- 판정 규칙: **측정 사실 / 해석 / 제안**을 분리한다. 운영상 종결을 통계적 불가능성으로 표현하지 않는다.

## 0. 경영 요약

| 질문 | 최종 판단 |
|---|---|
| 알파랩의 목적은 무엇인가 | 기존 09:00~09:30 틱 데이터에서 재현 가능한 STOM `매수식 1 + 매도식 1` 후보를 만들고, 사전등록·시행 원장·엔진 검증·감독형 소액 실전으로 거짓 알파를 걸러내는 **반증 중심 연구 시스템**이다. |
| 연구를 계속할 수 있는가 | **가능하다.** 다만 기존 O-4/B-ext식 오프라인 대량 조합 확대는 운영상 종결하고, 엔진과 오프라인의 관측 프레임 차이를 먼저 규명해야 한다. |
| 현재 신규 알파가 있는가 | 신규 진입 알파는 없다. B1 매도 개선만 엔진 A/B에서 양년 총수익 개선을 확인했다. 실전 성공은 아직 아니다. |
| 가장 중요한 새 단서는 무엇인가 | B-트랙의 엔진 평균과 오프라인 anchor 평균 사이에 큰 집계 차이가 있으나, 같은 거래의 paired 차이가 아니라 cohort·진입·호가깊이·종료 규약이 섞여 있다. |
| 무엇부터 시작해야 하는가 | **U7-F0 Offline Frame Bridge**: 같은 진입을 고정해 L3와 엔진 의미론의 차이를 성분별로 분해한다. 이 1차 패키지는 엔진 0회로 설계한다. |
| 연구 시스템의 가장 큰 부족점 | 사전등록→게이트→원장→카탈로그→전략 등록을 같은 실험으로 묶는 강제 해시/ID 체인이 없고, 일부 현재 정본 서사가 원시 JSON보다 강하게 결론 내린다. |
| 현재 종합 상태 | 연구 탐색은 **WATCH**, 증거 기반 자동 승격은 **BLOCK**, B1 감독형 실전 증거 수집은 사용자 수동 개시 대기다. |

## 1. 1차 결과 보고서 보존본

### 1.1 최초 판단

알파랩은 조건식 생성기나 최고 백테스트 점수 탐색기가 아니다. 후보 생성, 사전등록, 재현성 검증, 시행 수 기록, STOM 엔진 확인을 거쳐 감독형 후보를 만드는 연구 공장이다. 총수익이 1차 목적이며 MDD는 킬스위치 제약이다. 최종 심판은 반복 사용된 과거 DB가 아니라 감독형 소액 실전이다.

### 1.2 최초 결론

오프라인 실패가 모든 알파의 부재를 증명한 것은 아니다. 현행 사건 정의와 단일 L3 판정이 STOM 엔진에서 수익을 내는 희소·상태 의존 사건을 충분히 재현하지 못할 가능성이 크므로, 새 임계값 탐색보다 오프라인↔엔진 프레임 차이 규명이 우선이라고 판단했다.

### 1.3 심층 감사에서 바뀐 부분

| 최초 표현 | 심층 감사 후 교정 |
|---|---|
| 가문 확장이 신호를 희석했다 | 추가 66건이 합동 평균을 낮춘 것은 파생 계산으로 보이지만, 중복·혼합·프록시 과소발화 때문에 인과적 ‘희석’으로 확정하지 않는다. |
| 깊은 가지의 물리적 한계가 확정됐다 | 현 은행·창·AND 프록시·L3 출구에서 검정력 부족이 반복됐다. 사전등록 사다리를 **운영상 종료**할 근거는 되지만, 모든 오프라인 방법의 물리적 불가능성은 아니다. |
| 가문 전략은 전부 음이다 | 원시 JSON에는 양의 raw 평균인 비챔피언 전략도 있다. 모두 표본부족이다. 정확한 표현은 **자격 양성 0**이다. |
| 엔진 차이가 프레임 원인을 보여준다 | 현재 차이는 서로 다른 집계 평균의 차감이다. common-entry paired 분석 전에는 원인을 특정할 수 없다. |

## 2. 감사 범위와 근거

### 2.1 핵심 정본·산출물

| 구분 | 근거 |
|---|---|
| 현행 프로그램 상태 | `docs/research/condition_research/plans/2026-07-12_program_handoff_v3.md` |
| B-ext 판정 | `.../b_track_ext/b_ext_report.md`, `b_ext_summary.json`, `b_ext_gates_summary.json` |
| O-4 판정 | `.../o4/o4_candidate_report.md` 및 현행 핸드오프의 후속 정오 |
| B1 엔진 A/B | `.../d5r_b1_live/_ab_verdict.json` |
| 판정기 | `alpha_lab/btrack/judge_b.py`, `o4lab/judge_o4.py`, `clause_lab/pair_judge.py` |
| 라벨 | `alpha_lab/dataset/labels_v2.py` |
| 연구 규율 | `alpha_lab/discipline/prereg.py`, `measure_gate.py`, `ledger.py` |
| 카탈로그·승격 | `alpha_lab/catalog/builder.py`, `alpha_lab/bridge/registrar.py` |

### 2.2 검증 기준

1. 서술 수치를 원시 JSON과 대조했다.
2. 점추정치, 통계 판정, 운영 결정을 분리했다.
3. 빈 분모·표본부족·FDR 분모·비가문 표본을 확인했다.
4. 연구 단계 간 동일 실험 정체성이 강제되는지 추적했다.
5. 새 아이디어는 임계값 재조정이 아니라 새로운 estimand 또는 프레임을 요구했다.
6. 2022~2023도 이미 반복 사용됐으므로 진정한 미개봉 OOS로 부르지 않는다.

## 3. 현재 연구 결과의 교정된 상태

| 연구축 | 직접 측정 사실 | 올바른 판정 | 금지되는 확대 해석 |
|---|---|---|---|
| 칸 지도 | h300·L3 계열에서 챔피언 조준 실패 | 기술통계·함정 설명 자산 | 하드 veto, 모든 지형 알파 부재 |
| O-1G 갭×시총 | 자격 셀에서 양EV 증거 0 | 단순 시초 갭 추격 종결 | 모든 갭 조합·경로효과 부재 |
| O-3 돌파 온셋 | 자격 10/10의 CI 상한이 음수 | 현 L3 출구에서 추격 진입 음성 | 모든 돌파/모든 출구 음성 |
| 2절 교호작용 | 16×37, 16×38 양의 DiD 시너지 | 조건부 가드 효과의 제한적 증거 | 원 임계값을 전략에 직접 이식 |
| O-4 문법 | 닫힌 후보 158개, 생존·약신호 0 | 이 문법족·온셋·L3 범위 kill | flat-39 overlap으로 비아류 판정 |
| B anchor | n=114, mean +0.1658%p, CI 0 포함 | 미결·검정력 부족 | 양EV 존재 증명 |
| B-ext anchor | n=180(2022 59, 2023 121), mean -0.0322%p, CI [-0.5027,+0.4327], p=0.93 | 미결·자격 양성 0 | 음EV 확정 또는 오프라인 전체 불가능 |
| B-ext 분모 | 13전략, 신규 비트 31, 측정 가능 가지 19, 정식 가지 0, FDR 분모 1, 비가문 n=0 | 현 사다리 운영상 종료 | 가문 전부 음, 비가문 일반화 |
| B1 엔진 A/B | 2022 +947,387원, 2023 +591,485원, 합계 +1,538,872원; 거래 101→102, 197→198 | 양년 총수익 개선 확인 | 실전 성공, 신규 매수 알파 증명 |

### 3.1 B-ext 서사의 구체적 정정

`b_ext_summary.json`에는 raw 평균이 양수인 비챔피언 전략이 존재한다. 예를 들어 `Tick_B_902 +0.3199%p(n=31)`, `Tick_B_902_Study +1.0424%p(n=17)`, `Tick_B_902_Update +0.0581%p(n=17)`이다. 모두 `insufficient`이므로 양성으로 승격할 수 없지만 “가문 13종 전부 음”도 사실이 아니다.

B-ext의 정확한 결론은 다음과 같다.

> 일부 작은 층의 점추정치는 양수지만 정식 자격 가지는 0개이고 합동 anchor도 미결이다. 현 은행·09:00~09:30 창·AND 과소집합 프록시·RR8_12 L3 출구에서 반복된 검정력 부족과 사전등록 중단 규칙에 따라 이 오프라인 사다리를 운영상 종료한다.

### 3.2 O-4 overlap 정오

기존 flat-39-AND 프록시는 시간상 상호배타적인 2가지 DNF 챔피언을 하나의 AND로 합쳐 구조적 공집합을 만들었다. 따라서 “참 overlap의 하한”이라는 해석은 폐기한다. O-4의 EV 기반 생존 0 판정은 유지되지만, 미래 후보의 비아류·독립성 판정에는 이 프록시를 재사용하지 않는다.

### 3.3 B1 상태 분리

| 상태 | 현재 |
|---|---|
| 엔진 A/B 총수익 개선 | 완료 |
| 전략 DB 등록 | 기존 정본상 완료, 본 감사에서는 쓰기 없음 |
| GUI 감독형 소액 운용 개시 | 사용자 수동 작업 대기 |
| 30거래일 채점 | 미시작 |
| 실전 성공 주장 | 금지 |

## 4. 부족한 부분 상세 감사

### 4.1 연구 서사·통계 판정

| 심각도 | 부족점 | 실패 방식 | 개선 방법 |
|---|---|---|---|
| HIGH | raw 점추정, 자격 양성, 운영 종결을 혼용 | 작은 양수 평균을 존재 증명으로 부르거나, 미결을 물리적 불가능성으로 확대 | 모든 보고서에 `관측 / 판정 / 운영결정` 3단 블록 강제 |
| HIGH | B-ext 분모가 결론에서 누락 | 정식 가지 0·비가문 n=0인데 전체 깊은 전략으로 일반화 | 13/31/19/0/FDR1/nonfamily0을 결론과 함께 출력 |
| HIGH | 현재 핸드오프의 “가문 전부 음”이 JSON과 모순 | 다음 연구가 잘못된 확정 지식을 상속 | “자격 양성 0, 일부 raw 양수는 insufficient”로 정정 |
| MEDIUM | `sanity: False`의 의미가 불명확 | sanity 실패로 오독 | `sanity_anchor_tripped=false(비정상 수렴 미발동)`로 풀어 씀 |
| MEDIUM | B-ext의 “B1 engine” 비교 대상 불명 | 101/197은 B1 A/B의 A측 거래수와 일치 | 기준선·수정 런 식별자와 원천 필드를 명시 |
| MEDIUM | O-4 정오가 원 보고서에 전파되지 않음 | 폐기된 overlap 하한을 재사용 | 원 보고서에 superseded 주석 또는 정오 인덱스 추가 |

### 4.2 증거 체인

현재 의도는 `사전등록 → measure_gate → 측정 → n_trials → 카탈로그 → 전략 등록`이지만 공통 `experiment_id`와 전 단계 해시 연결이 강제되지 않는다.

| 우선 | 심각도 | 부족점 | 최소 개선 | 검증 기준 |
|---:|---|---|---|---|
| 1 | HIGH | 커밋된 미완성 사전등록도 tracked/clean이면 게이트 통과 가능 | machine-readable `status=sealed`, 미결·`(기입)`·필수 수치 검사 | placeholder 하나라도 남으면 기동 거부 |
| 2 | HIGH | SHA 검사가 기본 선택이고 코드 목록 완전성을 호출자가 결정 | 전체 코드 manifest와 full SHA를 사전등록에 봉인, `require_sha=True` 고정 | 의존 파일 누락·코드/HEAD 변경 시 거부 |
| 3 | HIGH | 게이트 PASS 영수증이 측정 실행과 결합되지 않음 | prereg/code/tree SHA를 가진 1회용 gate receipt를 wrapper가 즉시 소비 | 과거 receipt 재사용·다른 HEAD 실행 거부 |
| 4 | HIGH | 원장에 prereg/gate/artifact 정체성이 없음 | 기존 v1 보존 + 신규 v2에 experiment ID와 해시·trial row ID 추가 | 동일 series의 과거/다른 실험 행 혼입 방지 |
| 5 | HIGH | `known_ok=True` 근거가 원장에 남지 않음 | `window_role`, `override_reason`, 승인 근거 해시 저장 | 결과 측정 목적 known 접촉은 항상 거부 |
| 6 | HIGH | 카탈로그가 부분 누락·정적 verdict에도 성공 가능 | required/optional manifest, 동적 판정 또는 봉인 verdict, `VALID/PARTIAL/INVALID` 상태 | 필수 원천 누락 시 promotion 금지 |
| 7 | HIGH | 등록기는 임의의 비어 있지 않은 `ALP_` 식을 삽입 가능 | 봉인 promotion manifest와 PRE_PROMOTION receipt를 DB open 전에 검증 | 해시·판정·원장 중 하나라도 불일치하면 쓰기 전 거부 |
| 8 | MEDIUM | 원장 read가 필수 키 존재만 확인 | 읽을 때도 전체 스키마·버전·timestamp·type 검증 | malformed 행을 행 번호와 함께 fail-closed |
| 9 | MEDIUM | DB conflict 검사→raw copy→write가 단일 잠금이 아님 | `BEGIN IMMEDIATE`, 재조회, SQLite backup API, post-write hash 검증 | 동시 등록에서도 한 쌍만 삽입, backup integrity PASS |

### 4.3 판정기와 estimand

| 부족점 | 영향 | 개선 |
|---|---|---|
| 단일 L3 평균 의존 | 진입 알파 실패와 출구/경로 불일치를 구별하지 못함 | 사전 고정된 전체 path 함수와 동시 신뢰대 |
| 집계 엔진 gap | cohort·진입가·호가깊이·강제청산이 혼합 | common-entry paired factorial 분해 |
| 표본부족과 kill 혼동 가능 | “검증되지 않음”을 “음성”으로 종결 | `insufficient / undetermined / negative / positive` 상태를 배타적으로 강제 |
| O4 overlap 하한 오류 | 신규 후보 독립성 오판 | true DNF/stateful activation 또는 overlap=`unidentified` |
| 진정한 미개봉 OOS 부재 | 기존 DB 결과의 확증 주장 불가 | 과거 DB 결과는 diagnostic/supervised candidate로 한정, 새 시간 증거는 감독형 실전으로 확보 |

## 5. 개선 로드맵

| 단계 | 작업 | 산출물 | 완료 조건 |
|---:|---|---|---|
| R0 | 현행 서사 정오 | 정정 인덱스와 상태표 | JSON과 문서 결론 모순 0 |
| R1 | Evidence Envelope v1 | experiment/prereg/code/gate/artifact/trial/catalog SHA 스키마 | 샘플 실험 하나를 끝까지 hash로 추적 가능 |
| R2 | 사전등록 finalizer·1회용 gate receipt | SEALED manifest와 launch receipt | draft·오래된 receipt·코드 drift 전부 거부 |
| R3 | Ledger v2·PRE/POST catalog 분리 | exact trial link, catalog status | PRE_PROMOTION이 등록 receipt 없이 VALID 생성 |
| R4 | promotion manifest 검증 | read-only verifier | B1 기존 자산 dry run으로 누락 링크 목록 생성 |
| R5 | U7-F0 프레임 연구 | paired frame receipt | 엔진 0회, common-entry gap 분해와 kill 판정 |
| R6 | 통과 시 후속 한 축 | veto 또는 path/exit 패키지 | 별도 사전등록, 한 family 1회 |
| R7 | 승인된 엔진 확인 | 소수 고정 후보 A/B | 사용자 승인·예산·원장 선봉인 |
| R8 | 감독형 실전 | 30거래일 scorecard | 성공/유지/강등 판정 전 성공 주장 없음 |

## 6. 창의적 후속 연구 포트폴리오

점수는 정보이득·비용·타당성 위험 각각 5점 만점이다. 아래 아이디어는 임계값 재조정이 아니라 서로 다른 질문을 측정한다.

| 순위 | ID | 가설 | 주 estimand | 정보/비용/위험 | kill |
|---:|---|---|---|---:|---|
| 1 | F1 Frame Bridge | 같은 진입을 고정하면 엔진 우위의 과반이 진입·호가깊이·종료 규약으로 설명된다 | paired `Δ_frame`, 3성분 factorial/Shapley share | 5/3/2 | 무결성 실패, 양년 방향 불일치, 설명력 <50% |
| 2 | V1 Negative Veto | 확정 음성 지형은 매수 신호가 아니라 손실 거래 제외기로 가치가 있다 | drop-only `ΔTotalProfit_static`, 보존율, 양수거래 오제거 | 5/2/3 | 어느 연도든 개선≤0 또는 MDD 악화 |
| 3 | P1 Path Surface | L3 종착점이 지우는 일시적 양의 경로가 있다 | 순비용 markout 함수, 동시신뢰대, 경로 면적 | 5/3/2 | 양년 전 경로 상한≤0 또는 형태 비재현 |
| 4 | M1 Missingness Bounds | L3 제외·결측률 차이가 frame gap 일부를 만든다 | 관측률 차이, exclusion별 비율, Manski bounds | 4/1/1 | bounds가 기존 판정을 바꾸지 못함 |
| 5 | S1 Sparse Fragility | B anchor 양수는 소수 종목·일·주 cluster 착시가 아니다 | leave-one-cluster-out 최소 mean, 상위5 기여율 | 4/1/2 | 한 cluster 제거로 mean≤0 또는 상위5>50% |
| 6 | C1 Time-shift Placebo | 16×37/38 시너지는 정적 종목 특성이 아니라 정확한 동시성 효과다 | 실제 I와 일내 circular-shift null의 차이 | 4/2/2 | 실제 I가 shift null 상위 5% 밖 |
| 7 | X1 Exit Competing Risk | 그룹 차이는 특정 청산절/forced-cap 구성 차이로 설명된다 | cause incidence와 `P(cause)×E[net|cause]` | 4/2/3 | 표준화 후 원 contrast 80% 이상 잔존 |
| 8 | C2 Activation Order | 같은 최종 bit라도 `#16→pressure`와 역순의 손익이 다르다 | matched activation-order mean 차이 | 4/3/3 | CI 0 포함 또는 양년 부호 불일치 |
| 9 | C3 L3-blind Temporal Motif | snapshot AND가 아닌 bit 전이 motif에 이질성이 있다 | outcome-blind motif의 global heterogeneity 후 FDR | 4/4/4 | global gate 또는 formal motif gate 실패 |
| 10 | C4 Opportunity Portfolio | 약한 독립 trigger도 incumbent와 비중복이면 총수익을 높인다 | 고정 scheduler의 incremental total profit | 3/3/4 | 어느 연도든 증분≤0 또는 MDD 악화 |

### 6.1 아이디어별 오염 방지 공통 규칙

1. 신규 수집·백필 금지, 원천 DB read-only.
2. known 2025~2026과 청산 계열 known 2024는 선택·수정·재랭킹에 사용하지 않는다.
3. 2022~2023 결과도 반복 노출된 진단 근거이며 미개봉 OOS로 부르지 않는다.
4. 후보 family, estimand, 분모, 비용, seed, kill을 결과 열람 전에 봉인한다.
5. 일자 block을 기본 추론 단위로 하고 종목 cluster 민감도를 병기한다.
6. 표본부족을 kill로 바꾸지 않는다.
7. 엔진 실행은 별도 봉인·명시적 사용자 승인·시행예산 이후에만 한다.
8. 오프라인 통과는 실전 성공이 아니라 엔진 검증 요청 자격이다.

## 7. 추천 첫 연구 패키지 — U7-F0 Offline Frame Bridge

### 7.1 질문

“엔진이 더 좋다”가 아니라 **동일한 진입에서 어떤 의미론 차이가 얼마의 손익 차이를 만드는가**를 답한다.

### 7.2 봉인 계약 초안

| 항목 | 봉인 내용 |
|---|---|
| 기간 | 2022·2023, 09:00~09:30 |
| Cohort A | 기존 엔진/P5 exact-entry 원장 전수 |
| Cohort B | A와 exact timestamp로 매치되는 902∨905, 별도 sparse 층 |
| Primary | common-entry `Δ_frame = net_engine_semantics - L3_net` |
| 성분 | synthetic/recorded entry × top-book/3-level depth × L3 cap/engine terminal의 full factorial |
| 추론 | paired day-block CI, 연도별 방향, 성분 기여율, residual |
| 결측 | match/exclusion flow와 M1 worst/best bounds |
| 실행 제한 | 본 패키지는 엔진 0회. 기존 기록과 재생 의미론만 사용 |

### 7.3 실행 순서

1. sell-expression SHA와 vector equivalence receipt를 검증한다.
2. common-entry manifest와 join key/window를 봉인한다.
3. matched/offline-only/engine-only 수와 제외 사유를 먼저 출력한다.
4. 동일 entry에서 2×2×2 full factorial을 계산한다.
5. paired gap, 성분별 기여, residual, 결측 bounds를 한 receipt에 기록한다.
6. 양년 방향과 설명력 gate를 판정한다.
7. 통과할 때만 별도의 승인형 엔진 연구 사전등록을 작성한다.

### 7.4 중단 기준

- equivalence 또는 SHA 무결성 실패
- exact-entry match 계약 실패
- paired gap 양년 방향 불일치
- 봉인된 성분 설명력 합계가 aggregate gap의 50% 미만
- 결측 worst/best bounds가 결론을 뒤집음

중단 후 성분을 보고 새 진입·출구 규칙을 즉석 최적화하지 않는다.

## 8. 하지 말아야 할 연구

| 금지 | 이유 |
|---|---|
| O-4 문법에 임계값만 추가해 재탐색 | 같은 estimand의 연구자유도만 증가 |
| B-ext에 부트스트랩 횟수만 증가 | 희소 사건 수는 늘지 않음 |
| flat-39 overlap 재사용 | true DNF와 구조 불일치 |
| 2023을 새 OOS로 재명명 | 이미 반복 사용됨 |
| path 최고 시점을 보고 출구 채택 | 최적시점 선택편향 |
| negative map을 즉시 실전 veto로 적용 | 챔피언 오제거 가능, 동적 자본효과 미검증 |
| 집계 engine gap을 원인으로 해석 | matched cohort가 아니며 성분 혼합 |
| B1 엔진 개선을 실전 성공으로 표현 | 30거래일 증거 없음 |

## 9. 최종 판정

| 영역 | 상태 | 판정 |
|---|---|---|
| 기존 오프라인 대량 조합 사다리 | CLOSED(운영상) | 현 범위에서 반복된 무생존·검정력 부족으로 자원 투입 중단 |
| 알파랩 연구 시스템 | WATCH | 반증·재현 인프라는 가치가 있으나 증거 연결과 서사 정오 필요 |
| 자동 전략 승격 | BLOCK | promotion manifest·완전한 증거 체인 부재 |
| B1 | SUPERVISED CANDIDATE | 엔진 개선 확인, 실전 채점 대기 |
| U7-F0 | RECOMMENDED | 가장 높은 정보이득의 엔진 0회 후속 패키지 |
| 신규 대량 엔진 스윕 | BLOCK | 별도 사전등록·사용자 승인·예산 필요 |
| P4 대시보드 | HOLD | 연구 정본·카탈로그 유효성 정리 후 진행 |

## 10. 결론

알파랩의 가장 큰 성과는 아직 새 매수 알파가 아니라, 실패한 지형·문법·온셋을 재현 가능하게 종결하고 유일한 엔진 개선인 B1을 분리해낸 것이다. 가장 큰 약점은 오프라인 판정과 STOM 엔진이 같은 사건과 체결 의미론을 측정한다는 보장이 없고, 연구 단계 사이의 증거 정체성이 자동으로 연결되지 않는다는 점이다.

따라서 다음 연구는 조건을 더 많이 만드는 방향이 아니라 다음 두 질문에 집중해야 한다.

1. **같은 진입에서 엔진과 L3의 차이를 만드는 성분은 무엇인가?**
2. **이미 실패한 신호가 진입 알파가 아니라 손실 회피·경로·순서 정보로 가치가 있는가?**

첫 질문을 U7-F0으로 먼저 반증한 뒤, 결과가 설명력을 가질 때만 V1/P1 중 하나를 별도 봉인한다. 이 순서가 현재 데이터와 시행 예산에서 가장 높은 정보가치를 제공하며, 기존 오프라인 탐색을 이름만 바꿔 반복하는 일을 막는다.
