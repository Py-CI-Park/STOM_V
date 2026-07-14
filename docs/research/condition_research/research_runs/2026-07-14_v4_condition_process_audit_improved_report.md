# V4 조건식 개선 시스템 프로세스 심층 감사·개선 연구보고서

| 항목 | 내용 |
|---|---|
| 기준 커밋 | `bb41ae4ee4e15f4a0f2f98d63df1e6cb43aa738c` |
| 연구 브랜치 | `research/v4-condition-process-audit-20260714` |
| 선행 보고서 | `2026-07-14_v4_condition_process_audit_initial_report.md` |
| 연구 질문 | 왜 조건식 생성 기능과 대시보드는 확장됐지만 검증 가능한 성과로 연결되지 않는가 |
| 최종 판정 | **BLOCK — 개발 완료와 성능·일반화·승격 증명이 분리되어 있으며 일부 legacy/대시보드 경로가 정본 계약을 우회함** |
| 안전 경계 | CL-R08~R10 실행·후보 생성·공식평가·보호 DB 접근 없이 코드·문서·기존 산출물만 감사 |

## 1. 최초 보고서 이후 정밀화된 결론

| 구분 | 초기 판단 | 심층 검토 결과 | 최종 해석 |
|---|---|---|---|
| DR-01~05 | 핵심 결함이 남아 있음 | 정본 `run_loop`에는 Manifest v2, evidence, final-owner, AnalysisCardV3 교정 경로가 추가됨 | **구현 부재가 아니라 기본 OFF·이중 경로·소비 계약의 문제** |
| CLI 연구 경로 | fresh holdout·best 선정 결함 | `cli/research_loop.py` legacy 연구 경로에서 실제로 잔존 | 정본 루프 교정이 CLI 연구 경로 전체를 자동 교정하지 않음 |
| 후보 다양성 | final-owner 미배선 | DR-04 경로는 존재하지만 활성 profile과 legacy 호출에 따라 우회 가능 | 모든 진입점을 하나의 final-owner 계약으로 수렴해야 함 |
| 수익 성과 | 성과 없음 | 테스트 후보군은 열위이고 CL-R08은 재동결 전 잠금 | 후보 품질 문제와 성능 단계 미실행을 분리해야 함 |
| 대시보드 | 관측성 공백 | 후보 identity·run scope·active config·archive evidence 결합이 부족 | UI 문제가 알고리즘 수익을 직접 만들지는 않지만 잘못된 승격 결정을 유발 가능 |
| 77/100 | 높은 진행도 | 파일·라우트·행수 기반 capability maturity이며 profit proof는 0 | 성과 KPI로 사용 금지 |

## 2. 현재 시스템의 두 경로와 충돌

| 경로 | 목적 | 강점 | 잔여 위험 | 목표 상태 |
|---|---|---|---|---|
| 정본 AI loop | provider 생성→공식 백테스트→채점→부검→환류 | DR-01~05 교정 기능, evidence·profile·AnalysisCard 기반 | 기능 기본 OFF, resume/예산/실행 profile 확인 필요 | 유일한 학습·계보 소유자 |
| CLI research loop | baseline CSV 분석→제외식 후보→비교·랭킹 | 빠른 결정론 분석·fallback·V4/V5 연구 | fresh holdout 미강제, 실패 후보 best, 출력 계약 혼재 | 정본 루프의 read-only 제안 어댑터 |
| V4 dashboard | 상태·연구·비교·승인·감사 | 라이브 truth source와 코드/지표 표시 | 검토 후보와 export winner identity 미결합 | evidence-bound 의사결정 뷰 |
| 문서·artifact | 계획·영수증·실험 결과 보존 | 승인 경계와 실패 기록이 비교적 정직함 | 중간/종결 보고서 supersedes 관계 불명확 | 단일 terminal manifest 색인 |

## 3. 상세 결함 등록부

| ID | 우선순위 | 영역 | 부족한 부분 | 확정 근거 | 영향 | 목표 계약 |
|---|---|---|---|---|---|---|
| G-01 | P0 | 검증 | 후보 발굴과 평가가 같은 기간을 재사용할 수 있음 | `candidate_start/end` 미지정 시 baseline 기간 재사용, `fresh_holdout=False` | 과적합과 실제 개선 구분 불가 | 생성 데이터와 fresh validation의 날짜·행 hash가 달라야 평가 가능 |
| G-02 | P0 | 후보 의미 | 전체 전략 출력과 제외식 소비 계약 혼재 | prompt는 전략 코드, CLI 합성은 `if expression: 매수=False` | 의미 반전·compile 실패·잘못된 필터 | `FULL_STRATEGY`와 `BUY_EXCLUSION_EXPR` schema 완전 분리 |
| G-03 | P0 | 선택 | promotion 실패 후보도 best가 될 수 있음 | 통과 후보 없을 때 실패 후보 중 1위 선택 | 실패 계보 재사용 | promotion 미통과 시 `NO_ELIGIBLE_PARENT` |
| D-01 | P0 | 승인 | review 후보와 current winner identity를 비교하지 않음 | `_approval_binding_payload`가 각각의 통과만 확인 | 다른 후보의 OOS 근거로 export 가능 | candidate identity tuple 완전 일치 시에만 binding 발급 |
| E-01 | P0 | 성과 | 봉인 OOS·순비용 수익증명 없음 | `profit_proof=0`, R08 amendment 필요 | 성능 주장 불가 | R08→R09→R10 순차 receipt 없이는 승격 상태 생성 금지 |
| G-04 | P1 | 변수 | candidate pack 승인 변수 hard block이 legacy 호출에서 OFF | `enforce_approved_b_only` 기본 False | 미승인 변수·오타 이동 | registry에 없는 Name은 저장 전 거부 |
| G-05 | P1 | 게이트 | branch-aware 검사 구현과 실제 경로가 일관되지 않을 수 있음 | whole-code 검사와 분기 검사 경로 공존 | OR 우회·무의미 분기 | 모든 실행 가능 분기별 최소 필터·시간·예산 통과 |
| G-06 | P1 | 다양성 | 라운드 간 fingerprint/실 rowset 비교 불완전 | 호출마다 빈 seen set 가능, 코드 SHA를 rowset으로 사용한 경로 존재 | 중복 평가·국소최적 | run-wide AST hash + 실제 selected-row hash |
| L-01 | P1 | 단일 소유권 | DR final-owner와 legacy research best가 공존 | 정본과 CLI의 별도 selection semantics | 서로 다른 best 정의 | CLI는 proposal만 발급, official parent는 run_loop만 결정 |
| L-02 | P1 | 증거 | evidence 저장 실패가 모든 경로에서 평가 중단을 보장하지 않음 | helper 실패 흡수 경로 | orphan 평가·계보 단절 | passport/manifest FK 발급 실패 시 official evaluation 0회 |
| L-03 | P1 | resume | best 코드·winner·예산·history·dedup 복원 계약 확인 필요 | 일부 값만 복원하는 legacy 초기화 경로 | 예산 우회·다른 다음 prompt | checkpoint hash 기준 완전 복원 또는 resume 거부 |
| L-04 | P1 | 비용 | 기존 R08 frozen cost/fill 식별자가 실제 모델을 정직하게 식별하지 못함 | DR-06 `R08_CONTRACT_AMENDMENT_REQUIRED` | 순성과 재현 불가 | real adapter/version/hash와 gross/net reconciliation |
| S-01 | P1 | 통계 | DSR/PBO·CI·다중검정·최소 표본이 성과 게이트에 완전히 결합되지 않음 | maturity scoring 60, R08 점추정 hard gate | 우연한 양수 통과·저빈도 edge 오기각 | 불확실성 상태를 `PASS/FAIL/INDETERMINATE`로 분리 |
| A-01 | P1 | attribution | 매수·매도 결합 결과만 존재 | V2 실패에서 ablation 부재 | 개선 대상 오판 | 사전등록 2×2 buy/sell main effect·interaction |
| D-02 | P1 | 기준선 | V4 gate 선이 active config가 아닌 spec default 사용 | shell의 configSpec default 계산 | 화면상 오판 | 모든 gate 표시가 run manifest의 active config hash를 사용 |
| D-03 | P1 | run scope | Workbench 하위 패널이 독립 run 선택을 유지 | parent runId 전달·동기화 불완전 | 다른 run을 같은 분석으로 오인 | 화면 전체에 immutable `analysis_scope` 적용 |
| D-04 | P1 | 감사 | decision ledger에 run/gen/code/evidence hash 부족 | `_record_decision` 필드 제한 | 결정 재현 불가 | append-only DecisionReceipt v2 |
| D-05 | P1 | archive | 당시 autopsy·feedback·holdout 문맥 미복원 | `/run_state`가 기본 지표 중심 재구성 | 실패 학습·승격 blocker 소실 | generation evidence snapshot을 content-addressed 보존 |
| D-06 | P1 | 제어 | stop이 graceful 관찰 전 terminate 가능 | manager stop→hard stop 흐름 | checkpoint·receipt 유실 | STOP 요청→경계 대기→timeout 후 terminate 2단계 |
| R-01 | P1 | 연구 진실성 | gate false reject 감사에 정답 라벨이 없음 | reject prevalence만 측정 | 오탐률로 오해 | labeled positive/negative corpus의 TP/FP/TN/FN |
| R-02 | P1 | 산출물 | 중간 CSS 보고서와 후속 종결 결과가 함께 존재 | 초기 hold 21 vs 후속 reject 19/hold 2 | 오래된 결론 재사용 | supersedes와 terminal manifest 강제 |

## 4. 생성 계약 개선 설계

| 개선 항목 | 구현 지점 | 구체 방법 | Fail-closed 조건 | 검증 |
|---|---|---|---|---|
| Payload 종류 분리 | `brain/prompt.py`, `condition_generator.py` | `candidate_kind`, schema version, expression AST/body hash 추가 | kind와 parser 불일치 시 저장 금지 | 전체 전략·제외식 교차 입력 4종 contract test |
| 승인 변수 강제 | `validate_candidate_pack` 호출부 | `enforce_approved_b_only=True`, timeframe별 registry hash 결합 | unknown Name 하나라도 있으면 후보 기각 | B_* 양성·S_/R_/오타 음성 corpus |
| 분기별 게이트 | `brain/generator.py`, `filter_gate.py` | 실행 가능한 AND/OR branch를 정규화해 각각 검사 | 한 분기라도 최소 계약 미달 시 기각 | OR 우회·중첩 괄호·상수분기 property test |
| 실패 후보 격리 | `research_ranking.py`, `research_loop.py` | `eligible_candidates`만 parent selection 입력 | eligible 0이면 status=`no_eligible_candidate` | 전 후보 gate fail 회귀 테스트 |
| fresh validation | `research_loop.py` | analysis/train/fresh-validation manifest 분리, 날짜 겹침 0 검사 | overlap·동일 row hash·미동결 reference면 promotion 불가 | 전반 train/후반 validation 순위 유지율 실험 |
| 다양성 | `condition_fingerprint.py`, loop evidence | AST·family·실 rowset hash를 run-wide archive에 저장 | 동일 AST 또는 동일 실제 rowset은 평가예산 0 | 문법 다름/행 동일, 창 다름/코드 동일 골든 테스트 |
| 0거래 복구 | prompt+gate policy | 최소 필터 수를 무조건 완화하지 말고 exploration lane으로 격리 | hard gate와 상충하는 지시 렌더 시 prompt 거부 | 0거래 feedback snapshot test |

## 5. 성능 검증 프로토콜 개선

| 단계 | 입력 | 수행 | 필수 증거 | 통과 조건 | 중단 조건 |
|---|---|---|---|---|---|
| R07 재확인 | effective profile·Manifest v2·4후보 pool | 제한 3라운드 parent→child 폐루프 | prompt/passport/feedback/consumption FK, budget ledger | 다음 prompt가 직전 증거를 소비하고 재개 결정론 유지 | evidence FK 실패·예산 초과·profile drift |
| R08 재동결 | train40/validation20, real cost/fill/engine hash | train-only 채굴 후 최대 8 train·3 validation | data/universe/cost/fill/capital/config/code hash | 사전등록 net profit·MDD·daily·half 기준과 최소 거래수 충족 | amendment 부재·동결 후 provider 호출·hash drift |
| R08 통계 보조 | 누적 trial count·candidate returns | block bootstrap CI, DSR 또는 동등 선택편향 보정 | seed·block rule·trial count·CI artifact | hard gate 통과 + CI/보정 지표가 사전등록 범위 충족 | 표본 부족은 FAIL이 아닌 INDETERMINATE |
| R09 봉인 OOS | R08 통과 후보만, prospective 20일 | custodian one-open, 4-fold 정의 고정 | ACL·open receipt·fold 결과·비용 민감도 | net positive, CI/최소 거래수, fold 안정성 모두 충족 | open 후 생성·튜닝·재오픈 |
| R10 동일 cohort | 동일 data/cost/fill/capital의 AI·human 후보 | blind 비교와 승격 검토 | cohort manifest·candidate identity·decision receipt | 사전등록 benchmark 기준 충족 | 후보/환경 identity 불일치 |

## 6. 통계 기준 연구안

| 항목 | 권장 방식 | 이유 | 주의점 |
|---|---|---|---|
| 시계열 불확실성 | 거래일 또는 세션 단위 block bootstrap | 거래 독립성 가정 완화 | block 길이를 결과 확인 전에 고정 |
| 다중 후보 선택편향 | 누적 trial 수를 포함한 DSR 또는 동등 보정 | 최고 후보만 본 낙관 편향 억제 | DSR을 단독 hard gate로 사용하지 않음 |
| 전략 과적합 | fold별 순위 기반 PBO 또는 CSCV 적용 가능성 검토 | in-sample winner의 OOS 붕괴 측정 | 짧은 20일·저거래 전략에는 불안정할 수 있음 |
| 최소 표본 | 기간뿐 아니라 유효 거래수 하한 | 저빈도 우연 수익 방지 | 표본 부족은 자동 실패보다 prospective 연장 |
| 비용 민감도 | base/adverse fee·slippage 시나리오 | 얇은 edge 식별 | adverse 시나리오를 사후 변경 금지 |
| 판정 상태 | PASS/FAIL/INDETERMINATE 3상태 | 부족한 증거를 실패나 성공으로 왜곡하지 않음 | INDETERMINATE는 parent 승격 금지 |

## 7. V4 안전한 의사결정 계약

| 계약 | 백엔드 정본 필드 | UI 요구 | 차단 동작 | 테스트 시나리오 |
|---|---|---|---|---|
| CandidateIdentity | run_id, gen_no, candidate_id, buy/sell body hash, profile/config/data/cost/fill hash | 모든 검토·비교·승인 화면에 동일 identity badge | review/winner/export tuple 불일치 시 승인 409 | A의 review+B의 winner 주입 |
| AnalysisScope | selected run ID + state version + manifest hash | Workbench 모든 패널이 동일 scope 표시 | 하위 패널 독립 선택 금지 | run A→B 전환 후 모든 요청 ID 확인 |
| ActiveGateConfig | run manifest의 target/MDD/trade 기준 | 기본값과 실행값을 구분 표시 | active config 부재 시 gate 선 숨김 | 비기본 config run 렌더 |
| EvidenceStatus | TRAIN/VALIDATION/SEALED_OOS/BENCHMARK + receipt hash | HOF·compare에 인증 수준 열 추가 | train-only 후보 export 금지 | 고수익 train 후보와 OOS 후보 혼합 |
| DecisionReceiptV2 | identity, 판단, reviewer, reason, evidence hashes, timestamp | 감사 탭에서 전체 trace 제공 | 필수 hash 누락 시 기록 거부 | 같은 이름·다른 code 후보 2개 기록 |
| ArchiveSnapshot | autopsy·feedback·holdout·blocker content hash | 당시 상태와 현재 재계산을 구분 | snapshot 부재 시 `evidence unavailable` | live 캡처와 archive 재개방 비교 |
| StopReceipt | requested_at, graceful_boundary, forced, checkpoint hash | 종료 단계와 강제 종료 여부 표시 | grace 전 terminate 금지 | 정상 경계 종료와 timeout 강제 종료 |

## 8. 구현 우선순위와 예상 효과

| 순서 | 묶음 | 먼저 해야 하는 이유 | 기대 효과 | 회귀 위험 |
|---:|---|---|---|---|
| 1 | G-02, G-03, G-01 | 잘못된 의미·실패 parent·동일기간 평가는 이후 모든 결과를 오염 | 후보 결과의 최소 신뢰성 확보 | 기존 artifact schema 호환 |
| 2 | D-01, D-02, D-03 | 잘못된 후보·run 승인과 시각적 오판 차단 | V4 의사결정 안전성 확보 | 프론트 캐시·구버전 API |
| 3 | L-01, L-02, L-03 | 정본 계보와 재개 결정론 확보 | 실제 폐루프 학습 증명 가능 | 기존 resume 데이터 마이그레이션 |
| 4 | G-04~G-06, A-01 | 탐색 낭비와 잘못된 피드백 감소 | 후보 품질·원인 식별 개선 | 후보 수 급감 가능 |
| 5 | L-04, S-01, R08 amendment | 순비용 성능을 정직하게 측정하기 위한 전제 | CL-R08 실행 준비 | 기존 frozen hash 폐기 필요 |
| 6 | D-04~D-06, R-01~R-02 | 감사·운영 복구·연구 해석 개선 | 재현성과 운영 신뢰성 향상 | ledger schema versioning |
| 7 | 승인된 R07→R10 | 구조 검증 뒤에만 성능 비용을 지출 | 학습·성능·일반화·비교를 분리 증명 | 시간·표본 부족 |

## 9. 성공 측정표

| 목표 | 지표 | 현재 확인 상태 | 목표 |
|---|---|---|---|
| 계약 정확성 | 잘못된 candidate kind 저장 건수 | 미계측 | 0 |
| 검증 독립성 | train-validation 날짜/row overlap | 기본 경로에서 가능 | 0 |
| 선택 안전성 | promotion fail인데 parent로 사용된 수 | 기존 artifact에서 발생 확인 | 0 |
| 다양성 | unique AST·실 rowset 비율, family entropy | 라운드 간 미완전 | 사전등록 하한 이상 |
| 증거 완전성 | 공식 평가 중 passport/manifest/receipt 완전 비율 | 런타임 실측 필요 | 100% |
| 재개 결정론 | 중단 전후 다음 prompt/candidate hash 일치 | DR E2E 주장 존재 | 실제 profile에서도 100% |
| 의사결정 결합 | review/winner/export identity 일치율 | 서버 강제 없음 | 100% 강제 |
| 성능 | 순비용 validation/OOS CI·MDD·거래수 | 미증명 | R08/R09 사전등록 기준 충족 |
| 인간 비교 | 동일 cohort benchmark 결과 | 미실행 | R10 기준 충족 또는 정직한 실패 |

## 10. 연구 결론

| 질문 | 결론 |
|---|---|
| 왜 지금 성과가 없는가 | 후보군 자체 열위와 함께, 성능 검증 단계가 아직 재동결·실행되지 않았기 때문 |
| 시스템을 더 돌리면 해결되는가 | 아니오. 계약·검증·identity 결함을 먼저 고치지 않으면 더 많은 후보가 더 많은 신뢰 불가능 결과를 만듦 |
| 가장 먼저 개선할 것은 무엇인가 | 후보 payload 의미 분리, 실패 후보 parent 차단, fresh validation 강제, V4 후보 identity 결합 |
| DR-01~05는 무효인가 | 아니오. 정본 경로의 중요한 기반이지만 legacy/기본 OFF/다중 진입점 때문에 시스템 전체 계약으로 아직 강제되지 않음 |
| 대시보드가 수익 부진의 직접 원인인가 | 직접 원인으로 확정할 수 없으나 잘못된 run·후보·근거를 선택하게 할 수 있어 승격 안전성에는 P0 |
| 성능 연구를 언제 재개할 수 있는가 | R08 amendment로 real cost/fill/engine·profile·후보 hash를 재동결하고 앞선 P0 계약이 닫힌 뒤, 별도 승인 범위에서만 가능 |

## 11. 제한 및 금지된 해석

| 항목 | 내용 |
|---|---|
| 실행 | 본 연구는 CL-R08~R10, provider, 공식 백테스트를 실행하지 않음 |
| 보호 데이터 | `_database/`, `*.db`, `ai_strategy_loop/state` 등 보호 경로를 조회·변경하지 않음 |
| 인과 | 구조 결함별 수익 영향 크기는 동일 예산 A/B 전에는 미확정 |
| 성숙도 | 77/100을 수익성·일반화·자율학습 증거로 해석하지 않음 |
| 후보 성과 | 과거 후보 실패를 미래 후보군 전체의 불가능성으로 일반화하지 않음 |
| 승인 | 이 보고서는 CL-R08~R10 실행 승인이나 export/live 권한을 부여하지 않음 |
