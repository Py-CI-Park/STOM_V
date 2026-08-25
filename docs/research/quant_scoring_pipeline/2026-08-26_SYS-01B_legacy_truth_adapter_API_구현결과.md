# SYS-01B — Legacy Truth Adapter·터미널 우선순위·읽기 전용 API 구현 결과

> 실행일: 2026-08-26
>
> 실행 브랜치: `codex/process-research-sys-01b-truth-adapter`
>
> 기준선: `codex/process-research-pipeline-restart` @ `05d50ad2`
>
> 연구 실행: **미수행**
>
> 보호 DB·운영 전략 DB write: **없음**

## 1. 결론

SYS-01B를 구현했다. 과거 job JSON의 원시 `status`를 덮어쓰지 않고, 실행·경제·권위·다음 행동을 분리한 `ResearchTruth`를 읽기 전용으로 투영한다. REST와 WebSocket은 같은 builder를 사용한다.

가장 중요한 교정은 `backtest completed without metrics`라는 일반 메시지만으로 `no_trades`를 저장하던 기존 판정을 제거한 것이다. 앞으로는 다음 조건을 모두 만족해야 새 job이 정상 무거래로 저장된다.

| 필수 조건 | 판정 |
|---|---|
| return code | 정확히 `2` |
| metrics | `None` |
| protocol event | 1개 이상 |
| engine receipt | `total_report_no_trades` 정확 일치 |
| 반대 증거 | `engine_strategy_exception`, `engine_data_response_timeout` 없음 |

따라서 PIPE-01에서 발견한 “전략 TypeError인데 `no_trades`로 저장됨” 패턴은 새 실행부터 `error`로 저장된다. 과거 JSON은 바꾸지 않으며 API의 additive Truth view에서 `ERROR`로 정정된다.

## 2. 구현 범위

| 구성 | 역할 | 상태 |
|---|---|---|
| `backtest_terminal_classification.py` | 정확한 엔진 receipt 기반 fail-closed 무거래 판정 | 완료 |
| `research_truth_adapter.py` | legacy job payload strict parsing·복합 identity·Truth projection | 완료 |
| `research_truth_api.py` | `GET /research-truth/job`, `WS /research-truth/ws_job` | 완료 |
| `backtest_jobs.py` | 기존 heuristic을 작은 판정 모듈 호출로 교체 | 최소 수정 완료 |
| `app.py` | 신규 router import/include만 추가 | 최소 수정 완료 |
| unit/integration fixtures | classifier·adapter·REST/WS·job persistence·PIPE-01 10건 | 완료 |

거대 `backtest_jobs.py`와 `app.py`는 전면 리팩터링하지 않고 import/delegation/router mount만 변경했다. 새로운 책임은 모두 250 logical LOC 미만의 작은 모듈에 뒀다.

## 3. API 계약

### 3.1 조회 범위

| 항목 | 계약 |
|---|---|
| manager scope | 서버가 설정한 `STOM_WEBBT_JOBS_DIR` 또는 기본 `webbt_jobs` |
| evidence identity | `manager_id + jobs_dir + job_id + candidate_id + source_sha256` |
| historical provenance | engine/config/data fingerprint 미관측이므로 `LEGACY_INCOMPLETE` |
| authority | incomplete identity는 항상 `FEASIBILITY` |
| persistence | `none`; Truth view를 별도 파일·DB에 쓰지 않음 |
| 미완료 job | `truth_available=false`, `reason=job_not_terminal` |
| 없는 job | `truth_available=false`, `reason=job_not_found` |
| identity 누락 | fail closed, 예: `source_identity_missing` |

호출자는 `job_id`를 보내지만 실제 identity는 서버가 고정한 manager/jobs-dir scope와 함께 계산된다. 같은 문자열의 job ID가 다른 manager에 있어도 같은 Evidence로 합쳐지지 않는다.

### 3.2 네 축의 의미

| 축 | 예시 | 의미 |
|---|---|---|
| execution | `ERROR` | 엔진 실행 결과 |
| economic | `NOT_EVALUABLE` | 실행 실패이므로 손익 판정 금지 |
| authority | `FEASIBILITY` | historical identity 불완전, 승격 근거 아님 |
| next_action | `DEBUG` | 지금 허용되는 다음 행동 |

원시 `legacy_raw_status=no_trades`는 보존되며, 숨겨진 TypeError가 확인되면 `correction_applied=true`와 정확한 failure cause가 함께 반환된다.

## 4. PIPE-01 10건 재투영

SYS-01A에서 봉인한 실제 PIPE-01 identity·진단 fixture 10건을 이번 legacy adapter 경로로 다시 통과시켰다.

| Truth execution | 수 | 해석 |
|---|---:|---|
| `SUCCESS` | 2 | metrics는 있으나 거래 2/4건 소표본 손실; 경제성은 `INCONCLUSIVE` |
| `NO_TRADES` | 0 | 정상 무거래를 입증한 사례 없음 |
| `ERROR` | 6 | TypeError 2 + data response timeout 4 |
| `TIMEOUT` | 2 | protocol telemetry 없는 hard watchdog |

정정 집계는 `2 / 0 / 6 / 2`로 유지됐다. 이 검증은 과거 artifact를 수정하거나 백테스트를 다시 실행한 것이 아니다.

## 5. 성공·실패·가능성 판정

| 질문 | 판정 | 근거/제한 |
|---|---|---|
| legacy status 오분류를 읽기 시점에 교정 가능한가 | **성공** | strict adapter와 10건 projection |
| 새 job의 masked no-trades 저장을 차단 가능한가 | **성공** | exact receipt classifier + manager integration test |
| REST/WS schema parity가 있는가 | **성공** | 동일 payload builder 회귀 테스트 |
| 과거 raw JSON을 자동 수정했는가 | **아니오—의도된 경계** | immutable raw + additive view |
| historical Evidence가 완전한가 | **아니오** | engine/config/data fingerprint가 기록되지 않음 |
| 조건식 자율 개선 연구가 성공했는가 | **아직 판정 불가** | 이번 단위는 실행 진실성 기반만 구현 |
| 수익성/OOS/실전 가능성이 입증됐는가 | **아니오** | 연구 실행·fold·holdout·승인 없음 |

## 6. 검증 영수증

| 검증 | 결과 |
|---|---|
| SYS-01A/B Truth·PIPE-01 관련 | `67 passed` |
| job manager·WS·result identity 관련 | `59 passed` |
| 최종 관련 회귀·보안·문서 통합 묶음 | `193 passed` |
| no-excuse rules, 신규 7개 파일 | `0 violations` |
| Ruff | `All checks passed` |
| basedpyright error level | `0 errors, 0 warnings, 0 notes` |

추가로 이 worktree에 실제 남아 있던 최근 `webbt_jobs` JSON 6건을 파일 수정 없이 직접 투영했다. 6건 모두 원시 `cancelled`에서 `CANCELLED / FEASIBILITY / LEGACY_INCOMPLETE`로 일관되게 해석됐다. 다만 현장 파일 6건에는 success/error/no-trades가 없으므로 그 상태들은 PIPE-01 10건과 manager integration fixture가 검증 권위를 담당한다.

최종 branch merge 전에는 전체 unit suite, nonrelease verifier, 문서 index, compile, diff/protected-path 검사를 다시 수행한다.

## 7. 남은 한계와 다음 단위

| 한계 | 다음 처리 |
|---|---|
| UI는 아직 네 축을 직접 보여주지 않음 | `UX-01 Global Truth Bar` |
| 신규 job도 engine/config/data fingerprint를 아직 영속하지 않음 | 별도 SYS provenance sub-gate로 추적; 값 합성 금지 |
| 결과분석 bundle은 기존 구조 | `ANA-01 AnalysisBundle v2` |
| 연구 사전등록·재실행 없음 | UX-01·ANA-01·UX-02 완료 후 `RES-01` |

다음 원자 단위는 `codex/process-research-ux-01-global-truth-bar`다. 먼저 error/no-trades/success/timeout/partial fixture를 V4 정본 셸에서 직접 사용해, 사용자가 30초 안에 “무슨 일이 일어났고 지금 무엇을 할 수 있는가”를 알 수 있는지 검증한다.
