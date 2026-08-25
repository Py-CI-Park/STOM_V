# SYS-01A — Research Truth Contract 구현 결과

> 실행일: 2026-08-25
>
> 작업 브랜치: `codex/process-research-sys-01a-truth-contract`
>
> 판정: **구현·회귀 fixture PASS / API·대시보드 배선 미착수 / 연구 재실행 금지 유지**

## 1. 이번 단위의 결론

PIPE-01에서 봉인한 `<3000` 10건을 실행·경제·권위·행동의 네 축으로 분리하는 순수 계약을 구현했다. 과거 JSON과 로그는 수정하지 않으며, legacy 원문 위에 additive typed view만 만든다.

| 확인 항목 | 결과 | 의미 |
|---|---|---|
| 10건 typed 재분류 | **10/10 PASS** | 지표 2 / 정상 무거래 0 / 오류 6 / timeout 2 |
| 가려진 `no_trades` 2건 | **ERROR로 정정** | raw 값은 보존하고 correction provenance를 별도 기록 |
| 소표본 손실 2건 | `SUCCESS / INCONCLUSIVE / FEASIBILITY / REPRODUCE` | 실행 성공을 전략 성공으로 승격하지 않음 |
| job ID 중복 | 복합 identity로 분리 | manager·jobs_dir·job·candidate·source를 필수 결합하고 runtime provenance 완전성을 별도 상태로 표시 |
| 정상 무거래 | `trade_count == 0` 필수 | 거래 수 미상은 `PARTIAL`로 fail-closed |
| watchdog 상세 원인 | diagnostics 부재 + 0-byte log 필수 | 둘 중 하나라도 미상·상충이면 상세 원인을 단정하지 않음 |
| legacy 권위 | `FEASIBILITY` 고정 | raw payload가 `LIVE`나 robust 상태를 자체 주입할 수 없음 |
| correction provenance | identity + legacy input SHA-256 | 상태 정정을 입력 message/checkpoint/telemetry와 결정적으로 결합 |

PIPE-01의 raw job에는 검증 가능한 engine/config/data fingerprint가 없으므로 이를 합성하지 않았다. 10건은 모두 `LEGACY_INCOMPLETE`이며 미관측 필드는 `None`이다. 신규 Evidence가 `COMPLETE`를 주장할 때는 engine/config/data identity 세 값이 모두 있어야 한다.

## 2. 구현 산출물

| 파일 | 책임 |
|---|---|
| `ai_strategy_loop/controller/research_truth_models.py` | enum, 복합 Evidence identity, strict Pydantic model, 불변식, 다음 행동 결정 |
| `ai_strategy_loop/controller/research_truth_legacy_input.py` | legacy 입력 경계와 telemetry/checkpoint 필드 |
| `ai_strategy_loop/controller/research_truth_contract.py` | legacy status 파싱, 진단 우선순위, additive typed projection, 공개 타입 재수출 |
| `tests/unit/test_research_truth_contract.py` | 상태 전수·fail-closed·watchdog·무거래·identity·불변식 검사 |
| `tests/unit/test_research_truth_contract_pipe01.py` | PIPE-01 10건과 정정 집계 회귀 fixture |
| `tests/unit/test_research_truth_models.py`, `test_research_truth_fail_closed.py` | identity 완전성·schema 고정·부정 receipt·진단 모순 검사 |

세 production 모듈과 네 테스트 모듈은 각각 pure LOC 250 미만으로 유지했다. 기존 과대 모듈인 `backtest_jobs.py`와 `backtest_api.py`에는 로직을 추가하지 않았다.

## 3. 상태 계약

| 축 | 허용 값 |
|---|---|
| Execution | `SUCCESS / NO_TRADES / ERROR / TIMEOUT / CANCELLED / PARTIAL` |
| Economic | `POSITIVE / NEGATIVE / INCONCLUSIVE / NOT_EVALUABLE` |
| Authority | `FEASIBILITY / DEVELOPMENT / FROZEN_OOS / SHADOW / LIVE` |
| Next Action | `DEBUG / REPRODUCE / STRUCTURAL_REVISE / EXPAND / STOP / HOLDOUT` |

핵심 불변식은 다음과 같다.

| 입력·조합 | 계약 결과 |
|---|---|
| exception이 있는 legacy `no_trades` | `ERROR / NOT_EVALUABLE / DEBUG` |
| metrics 없는 실행 실패 | 경제 판정 `NOT_EVALUABLE` |
| `SUCCESS` | metrics 존재 + `trade_count > 0` 필수 |
| 정상 `NO_TRADES` | diagnostics 존재 + metrics/손익 없음 + `trade_count == 0` + 명시적 engine receipt 필수 |
| 미확인 status/불완전 terminal | `PARTIAL / NOT_EVALUABLE / REPRODUCE` |
| 취소·시간초과 + 오류 문자열 | 종단 interrupt 상태를 우선하여 문자열 오분류 차단 |
| status와 return code 모순 | `PARTIAL / LEGACY_TERMINAL_UNVERIFIED` |
| watchdog + event/checkpoint 존재 | 상세 no-telemetry cause 금지 |
| watchdog + 알려진 engine 진단 문자열 | 상세 no-telemetry cause 금지 |
| 무거래 receipt가 message substring에만 존재 | 정상 `NO_TRADES` 금지 |
| 무거래 + 손익 값 존재 | 정상 `NO_TRADES` 금지 |
| `LEGACY_INCOMPLETE` + 상위 권위/robustness | public model 직접 생성도 거부 |

## 4. 관측된 검증 증거

| 단계 | 명령·범위 | 결과 |
|---|---|---|
| 초기 RED | 구현 전 14개 계약 fixture | `14 failed` |
| 엄격화 RED | 상세 TypeError cause와 새 telemetry 경계 추가 | collection error로 미구현 경계 확인 |
| 계약 GREEN | 네 신규 테스트 모듈 | **47 passed** |
| 관련 회귀 | Truth Contract + D3 4종 + result identity | **77 passed** |
| 정적 규칙 | Python no-excuse checker | **0 violations** |
| lint | Ruff | **All checks passed** |
| type | basedpyright `--level error` | **0 errors / 0 warnings** |
| 비릴리스 계약 | `verify_nonrelease_sync.py` | **PASS** |
| 문법·diff | compileall, `git diff --check` | **PASS** |

수동 변환에서도 raw `no_trades`를 보존하면서 아래 typed view가 관측됐다.

```text
identity_status=LEGACY_INCOMPLETE
execution=ERROR
economic=NOT_EVALUABLE
authority=FEASIBILITY
next_action=DEBUG
failure_cause=ENGINE_STRATEGY_EXCEPTION.TYPE_ERROR_LIST_STRING_INDEX
correction_applied=true
```

## 5. 성공·실패 경계

| 범위 | 판정 |
|---|---|
| SYS-01A 순수 계약 구현 | **성공** |
| PIPE-01 10건 fixture 재현 | **성공** |
| 역사 Evidence 보존 | **성공** — 원본 파일을 수정하지 않음 |
| 실제 job 저장 시 typed 상태 기록 | **미구현** |
| read-only API/WS 노출 | **미구현** |
| Global Truth Bar | **미구현** |
| 조건식 개선·백테스트 재실행 | **미수행** |
| 수익성·OOS·실전 가능성 | **판정 불가** |

TypeError의 직접 발생 코드 위치는 traceback과 재현 테스트가 없으므로 이번 단위에서 추정하지 않는다. 확인한 것은 오류 문자열과 상태 오분류 메커니즘이다.

## 6. 다음 원자 단위

다음 브랜치는 **`codex/process-research-sys-01b-truth-adapter`**다.

| 순서 | SYS-01B 작업 | 완료 조건 |
|---:|---|---|
| 1 | legacy job payload를 `LegacyTruthInput`으로 만드는 read-only adapter | 누락·모순 필드 fail-closed 테스트 |
| 2 | terminal 판정을 과대 모듈 밖의 작은 모듈로 추출 | 새 저장부터 exception 우선 판정 |
| 3 | 과거 artifact를 수정하지 않는 typed result API | duplicate job ID를 scope와 함께 조회 |
| 4 | API·WebSocket 동일 truth payload | 두 경로 schema parity |
| 5 | PIPE-01 실제 artifact 10건 projection 통합 테스트 | 정정 집계 2/0/6/2 유지 |

SYS-01B까지 통과하기 전에는 UX-01, 연구 사전등록, 백테스트 재실행으로 넘어가지 않는다.
