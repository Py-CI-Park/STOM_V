# V4 조건식 개선 시스템 프로세스 초기 감사 보고서

| 항목 | 내용 |
|---|---|
| 보고서 성격 | 기준 커밋 상태를 보존한 최초 감사 결과 |
| 기준 커밋 | `bb41ae4ee4e15f4a0f2f98d63df1e6cb43aa738c` |
| 연구 브랜치 | `research/v4-condition-process-audit-20260714` |
| 감사 범위 | 조건식 생성 → 검증 → 공식 백테스트 → 평가 → 선택 → 피드백 → V4 표시 → OOS/승격 |
| 판정 | **BLOCK — 시스템 구축과 조건식 성과 증명이 연결되지 않음** |
| 변경 범위 | 읽기 전용 감사 결과 문서화. 런타임 DB·보호 경로·전략 본문 미변경 |
| 후속 정밀화 | 본 문서는 최초 판정을 보존한다. 잔여 legacy 경로와 DR-01~05 정본 교정 경로를 분리한 최종 해석은 `2026-07-14_v4_condition_process_audit_improved_report.md`를 따른다. |

## 1. 요약 판정

| 구분 | 확인 결과 | 판정 |
|---|---|---|
| 시스템 구축 | 생성·게이트·백테스트·채점·부검·대시보드 기능이 폭넓게 존재 | 부분 완료 |
| 학습 폐루프 | final-owner 후보와 정본 `run_loop` 평가 경로가 분리됨 | 미완료 |
| 성능 증명 | CL-R08 제한 성능 검증이 완료되지 않음 | 미증명 |
| 일반화 증명 | CL-R09 봉인 OOS/WF 결과가 없음 | 미증명 |
| 인간 기준 비교 | CL-R10 동일 cohort 비교가 없음 | 미증명 |
| 라이브 권한 | 자동 export/live 승격은 금지 상태 | 정상 잠금 |
| 종합 | 구현 성숙도는 상승했지만 수익성과 일반화는 증명되지 않음 | BLOCK |

## 2. 성과가 나지 않는 직접 원인

| 우선순위 | 부족한 부분 | 확인된 영향 | 주요 근거 |
|---|---|---|---|
| P0 | 후보 발굴과 평가가 기본적으로 같은 기간을 재사용 | 과적합과 실제 개선을 분리할 수 없음 | `cli/research_loop.py`의 후보 기간 기본값·`fresh_holdout=False` provenance |
| P0 | 테스트 후보군의 수익·MDD가 직접적으로 열위 | 게이트 완화로 해결할 수 없으며 false accept 위험 증가 | tick 288 전부 음수익, min 288 중 271 음수익, 통과 0 |
| P0 | 봉인 OOS 성과 부재 | 실전 일반화 주장 불가 | V3 평가 프로토콜은 design-only, `profit_proof=0` |
| P0 | V4 승인 근거와 export winner 후보 동일성 미검증 | 후보 A의 OOS 근거로 후보 B를 승인할 수 있음 | `dashboard/app.py::_approval_binding_payload`, `_do_final_approval` |
| P1 | 승격 실패 후보도 `selected_as_best` 가능 | 실패 구조가 다음 세대 부모로 재사용됨 | `cli/research_ranking.py`, `cli/research_loop.py` |
| P1 | LLM은 전체 전략을 출력하지만 연구 경로는 제외식으로 소비 | 생성 계약과 실행 의미가 달라질 수 있음 | `brain/prompt.py`, `strategy_generator.py` |
| P1 | 매수·매도 원인 분리 실험 부재 | 무엇을 고쳐야 하는지 피드백이 불명확 | failure lesson matrix, 2×2 미실행 |
| P1 | 비용·체결·자본 계약 미동결 | gross 결과를 순성과로 오인할 위험 | R07~R09 manifest의 cost/fill provenance 부족 |

## 3. 조건식 생성 과정 감사

| 단계 | 현재 동작 | 부족한 부분 | 위험 |
|---|---|---|---|
| 입력 변수 | 결정론 경로는 B_*를 주로 선택하고 S_*/R_* 누수를 검사 | LLM candidate pack의 승인 변수 강제가 기본 OFF | 미승인 변수·오타가 평가 단계로 이동 가능 |
| 프롬프트 | 전략 전체 코드와 다양한 피드백을 조립 | 전체 전략과 제외 조건식 출력 계약이 혼재 | 올바른 코드라도 downstream 의미가 반전될 수 있음 |
| 후보 다양성 | 같은 팩 내 raw/semantic 중복 검사 | 과거 라운드 fingerprint 비교가 기본적으로 비어 있음 | 반복 후보·탐색 예산 낭비 |
| 구조 게이트 | 필터 수·시간·계산예산 게이트 존재 | 전체 코드 집계이며 OR 분기별 검증 미배선 | 무의미한 실행 분기 우회 가능 |
| 0거래 복구 | 필터 축소 지침 제공 | 최소 필터 게이트 지침과 동시에 나타날 수 있음 | 재시도 소진·동일 실패 반복 |
| 후보 합성 | expression을 기존 매수전략에 제외식으로 삽입 | LLM 전체 전략 출력과 형식 불일치 | compile 실패 또는 잘못된 필터 의미 |
| 후보 선택 | promotion 통과 후보를 우선 정렬 | 통과 후보가 없으면 실패 후보 중 best 지정 | 실패 계보 강화 |

## 4. 전체 개선 루프 감사

| 단계 | 현재 경로 | 핵심 공백 |
|---|---|---|
| 생성 | `_generate_pair`가 단일 buy/sell 쌍 생성 | 2 repair + 2 discovery final-owner 결과를 소비하지 않음 |
| 증거 | manifest/passport/evidence ledger는 선택 기능 | 기록 실패 후에도 공식 백테스트 진행 가능 |
| 중복 제거 | AST 및 `rowset_fingerprint` 기반 옵션 | rowset 값이 실제 선택 행이 아니라 코드 SHA |
| 백테스트 | warm 우선, 실패 시 cold fallback | 같은 manifest 아래 engine mode가 바뀔 수 있음 |
| 채점 | hard fitness와 graded fitness 분리 | 통계적 불확실성·선택편향 보정 부족 |
| 피드백 | autopsy·segment·feature·hypothesis 확장점 존재 | 실행 프로파일에서 다수 기본 OFF, 소비 증거 부족 |
| 재개 | 일부 best score/gen 복원 | winner·best 코드·history·budget·dedup 복원 누락 |
| 종료 | 세대·토큰·목표 점수 제한 | CL-R07 provider/evaluation/wall-clock 예산과 불일치 |

## 5. V4 대시보드 감사

| 사용자 여정 | 지원되는 기능 | 부족한 부분 | 영향 |
|---|---|---|---|
| 실행 선택 | LIVE/Archive 선택, 상태·로그 표시 | shell run과 Workbench 내부 선택이 분리됨 | 서로 다른 run을 같은 화면에서 비교 가능 |
| 설정·시작 | config spec·설정 모달·start 제어 | start 실패 응답이 사용자에게 표시되지 않음 | 실행 실패 원인 은폐 |
| 진행 관찰 | 단계·지표·전략·비용 표시 | 8노드 그림이 실제 5단계로 축약 | 현재 단계 오해 |
| 세대 비교 | generations·code diff·HOF·run compare | 실행 당시 active config가 아닌 기본 gate 선 사용 | 잘못된 통과/실패 시각화 |
| OOS 검토 | freeze verdict·체크리스트 제공 | 검토 후보와 winner identity 결합 없음 | 잘못된 후보 승인 가능 |
| 감사 | append-only decision UI | run/gen/code/evidence hash 기록 부족 | 결정 재현 불가 |
| 정지 | stop 버튼·STOP flag 존재 | graceful 대기 전에 subprocess terminate | receipt·checkpoint 유실 위험 |
| 아카이브 | 기본 지표와 코드 복원 | 당시 autopsy·feedback·holdout 문맥 미복원 | 실패 학습 근거 상실 |

## 6. 우선 개선 방향

| 순서 | 개선 작업 | 완료 조건 |
|---:|---|---|
| 1 | 전체 전략과 제외 표현식을 별도 스키마·타입으로 분리 | 잘못된 payload가 저장·평가 전에 거부됨 |
| 2 | promotion 실패 후보의 best/parent 사용 금지 | 통과 후보가 없으면 명시적 `no_candidate` 종료 |
| 3 | 시간순 train/fresh-validation 강제 | 생성에 사용하지 않은 기간의 비교 receipt 존재 |
| 4 | 매수·매도 2×2 attribution 실행 | 진입·청산 main effect와 interaction이 분리됨 |
| 5 | Context Pack → 4후보 → final-owner → `run_loop` 단일화 | 선택 candidate ID가 공식 평가 receipt까지 동일 |
| 6 | 증거와 resume를 fail-closed로 전환 | passport 실패 시 평가 0회, 재개 상태 완전 복원 |
| 7 | cost/fill/engine/data manifest 동결 | 모든 결과에 동일한 버전·해시와 gross/net 존재 |
| 8 | V4 review/winner/export identity 결합 | 후보 hash가 하나라도 다르면 승인 불가 |
| 9 | CL-R07 프로세스 증명 | 3라운드 예산 내 parent→child 소비 계보 확인 |
| 10 | CL-R08→R09→R10 순차 검증 | 제한 성능, 봉인 OOS, 동일 cohort 비교를 분리 통과 |

## 7. 제한 사항

| 구분 | 제한 |
|---|---|
| 실행 검증 | 본 초기 감사에서는 백테스트·브라우저 UAT·보호 DB 조회를 실행하지 않음 |
| 런타임 상태 | 실제 실패 run에 활성화된 profile·feature flag는 추가 artifact-only 검토 필요 |
| 인과관계 | 구조 결함이 수익 저하에 미친 크기는 동일 예산 A/B 전에는 확정 불가 |
| 미추적 산출물 | 작업 트리의 미추적 artifact는 보조 증거이며 기준 커밋 포함 여부와 분리함 |
| 라이브 성과 | 실거래 체결·지연·시장 데이터 품질은 본 코드/문서 감사만으로 검증 불가 |
