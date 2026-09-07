# RES-04P 사건 입력 adapter 구현·전체 페이지 안내

기준 b84a90f244f1e567b26f2059de3e2ddf806e4b28.
브랜치 codex/process-research-res-04p-event-stream. 이전 준비계약 브랜치 위 stacked 작업이다.
상태: EVENT_ADAPTER_IMPLEMENTED_SYNTHETIC_VERIFIED. 전체 RES-04P 봉인/실제 Stage F 완료 아님.

## 무엇이 실제 달라졌나

계획만 추가한 것이 아니라 기존 triggered_positions와 DayFactorCache를 호출하는 사건별 adapter를 만들었다. 과거 집계 결과를 사건 기록으로 역산하지 않는다. 실제 source DB를 이번에 열거나 연구 job을 제출하지 않았고, 합성 TickDay로 기존 production predicate를 호출했다.

```text
합성/선언된 단일 종목·하루 TickDay
  ↓ shape·finite·calendar·Fold·시간·작업량 검사
기존 조건식 수치 계산
  ↓
관측 true + 관측 false          warmup / 마지막 입력 / 범위 밖
  ↓                            별도 coverage
이전 상태: true / false / null
  ↓
불변 EventStream JSON + 실제 입력 hash
  ↓
다음: 원천 binding·Episode/control·공식 사전등록 영수증
```

관측 공백 뒤 previous_triggered는 null이다. 기록되지 않은 행을 false로 만들지 않는다. 마지막 제공 행은 기존 predicate의 terminal 제외 규칙 때문에 관측 false로 내보내지 않는다. 이 마지막 행이 실제 장 종료라는 주장은 하지 않는다.

## 실제 합성 출력

외부 파일: C:/Users/parkc/STOM_Verification/v1.5_20260907/res04-event-stream-synthetic-20260908.json.

| 항목 | 관측 |
|---|---:|
| 입력 | 90행 |
| warmup | 59행 |
| 관측 | 30행 |
| 관측 true / false | 29 / 1 |
| 마지막 입력 제외 | 1행 |
| JSON 재읽기 | PASS, exit0 |

content hash(모델의 compact JSON): a471a5a0965a61c12a1eed494de9e8f293496560ee50d06630b3eac46c81a51c.
내보낸 pretty JSON 파일 SHA256: 6d04c0346a436209f85f61a29eb920210545b0511576f87eafe5725cc4669ee0.
두 해시는 정의가 다르므로 같은 이름으로 혼용하지 않는다. 합성신호 수는 시장 신호 수나 경제 성과가 아니다.

## 데이터·방법론 경계

- 신규 schema는 stom.res04.event_stream.v1이다. 원래 8개 관측 필드에 source_position 계보 정보와 coverage/identity envelope를 추가했다. reference 8필드 fixture schema와 동일하다고 주장하지 않는다.
- declared_database_sha256는 준비계약의 선언이다. observed_input_sha256는 실제 전달된 배열의 dtype/길이/bytes를 해시한다. 입력 배열이 선언된 DB에서 왔다는 인증은 후속 binding에서 수행한다.
- 후보 ID가 준비계약 목록에 있는지 확인하지만 candidate manifest의 source/code를 인증하는 기능은 아니다. 결과 authority는 SYNTHETIC_OR_DECLARED_INPUT_NO_EXECUTION이다.
- 원래 계산기의 recorded-row rolling history를 유지한다. gap은 연속성만 unknown으로 만들며, elapsed-time resampling이나 gap 이후 factor 재시작을 했다고 주장하지 않는다.
- warmup은 max(60, 모든 *_window의 2배)로 보수적으로 잡는다. 기존 default보다 긴 후보는 일부 초기 행이 추가 제외된다. 방법 version에 명시했고 역사 결과를 수정하지 않는다.
- 지원 세션은 기존 predicate 범위인 [09:00,09:30) 내부다. 그 밖의 세션 요청은 오류로 거부한다. 단일 날짜·유효한14자리 시각·정렬·개발 Fold를 검사한다.
- 새 코드에 DB open, runner submit, broker/API 호출은 없다. 운영 DB·Holdout·봉인 evidence는 바꾸지 않았다.

## 실제 검증과 발견한 결함

| 검사 | 실제 결과 |
|---|---|
| 최초 adapter red | 11 failed, exit1; import 성공 후 미구현 API 실패 |
| 첫 green + 준비계약 | 35 passed, exit0 |
| 보강 + 기존 신호 계산 | 46 passed, exit0 |
| 자원 결함 red | 2 failed, exit1; 제한 미거부 + 거대 정수 OverflowError |
| 수정 후 집중 회귀 | 48 passed in4.65s, exit0 |
| 독립 집중 재실행 | 48 passed in5.13s, exit0 |
| 독립 추가 QA | 21 passed in0.57s, exit0 |
| basedpyright 신규4파일 | 0 errors/warnings/notes |
| ruff 신규4파일 | 명시적 예외 적용 후 PASS |

집중 명령: `python -m pytest tests/unit/test_res04_event_resource.py tests/unit/test_res04_event_stream.py tests/unit/test_res04_preparation_contract.py tests/unit/test_res02_event_logic.py -q --tb=short -p no:cacheprovider`.
로그 root: C:/Users/parkc/STOM_Verification/v1.5_20260907, res04-stream-red.log, res04-stream-work-red.log, res04-stream-work-green.log.

초기 독립 코드·보안 리뷰는 FAIL이었다. rows만 제한하면 NumPy rolling std의 rows×window 임시 배열이 커진다. 안전한 runtime probe는36000행/window18000에서 shape(18001,18000), logical_bytes=2592144000을 확인하고 실제 할당 직전에 중지했다. 이는 실제 OOM을 일으켰다는 뜻이 아니다.

수정: predicate 호출 전 rows×보수적 history ≤2,000,000 cells, 파라미터 절댓값 ≤1e12를 검사한다. 원래 공격 사례 재실행 결과는 `TruthContractViolation EVENT_FACTOR_WORK_LIMIT`, `std_call_count 0`이었다. 이 한도는 운영 작업량 제한이지 퀀트 표본 Gate나 RSS 실측 보장이 아니다.

debugging 스킬의 원인 확인/red→green을 적용했다. 과도한 행 수 자체가 아니라 rolling 작업량이 원인이었고, 세션 밖 행도 factor 계산 이전에는 남는다는 점을 확인했다. 임시 debug journal은 이 영수증으로 요약 후 삭제하며, 요청된 회귀 로그와 외부 QA 코드는 보존한다. 전역 env·디버거 포트·계측 print는 추가하지 않았다.

| 독립 검토 | 최초 | 수정 후 |
|---|---|---|
| 목표/경계 | PASS | PASS |
| 코드 | FAIL: factor memory | PASS |
| 보안 | FAIL: factor memory | PASS: std 호출0 |
| 실제 library QA | PASS | PASS |
| 기존 맥락 | PASS | PASS |

production100 acceptance/전체unit/브라우저QA/실제시장 성과를 실행했다고 주장하지 않는다. 기존 pytest-asyncio scope warning은 남아 있다. lint 예외는 CPY001(저작권자 임의 작성 안 함), EM101(기존 typed error code), COM812(formatter와 충돌), tests D103/S101/PLR2004 관례다. 전역 설정은 바꾸지 않았다.

## 전체 페이지 안내와 현재 연결 상태

기존 V4 페이지/탭/패널을 재사용한다. 아래는 신설 페이지14개가 완성됐다는 뜻이 아니라 기능군별 작업 지도다. 이번에는 JSX/API 배선을 변경하지 않았다.

| 페이지 | 사용자가 얻을 답 | 연결 단계 | 이번 상태 |
|---|---|---|---|
| P01 Mission | 지금 어디이고 다음 행동은? | ANA-07/UX-06 | 기존 유지, 계획 기록 |
| P02 결과 라이브러리 | 어떤 결과를 분석하나? | SYS-05/ANA-05 | 기존 유지, 품질 연결 대기 |
| P03 품질·계보 | 자료를 믿어도 되나? | SYS-05 | 사건 입력 검증 기반 추가, 화면 미연결 |
| P04 성과·위험 | 비용/자본 기준 손익은? | SYS-05/ANA-05 | 지표/화면 변경 없음 |
| P05 거래·Replay | 언제 시작·반복·종료했나? | ANA-06 | 사건 adapter 합성 검증, UI 미연결 |
| P06 집단·피처맵 | 어떤 상황에서 차이가 있나? | ANA-06 | true/false·gap 입력 기반 추가 |
| P07 마이닝 | 규칙이 별도 자료에서도 유지되나? | ANA-07 | 평가 재집계 연결 대기 |
| P08 A/B·반사실 | 개선인가 단순 거래 감소인가? | ANA-07 | control 연결 대기 |
| P09 Fold·대조군 | 누락 없이 충분히 확인했나? | ANA-07 | 기존4Fold scope 검증, 집계 미연결 |
| P10 지식·반증 | 배운 것과 반복 금지 방향은? | ANA-08 | 기존 원장 재사용 계획 |
| P11 가설·사전등록 | 다음 실험을 어떻게 고정하나? | RES-04P/ANA-08 | 준비계약/사건adapter 부분 구현 |
| P12 큐·예산 | 승인된 작업이 어떻게 진행되나? | ANA-08 | 실행 금지 유지; 이번 작업량 제한은 별개 |
| P13 리포트 | 같은 근거를 공유할 수 있나? | ANA-05/UX-06 | 합성 EventStream JSON 왕복, 화면 export 미연결 |
| P14 설정·건강 | 실제 설정·자료 상태는? | UX-06 | 기존 유지, 후속 read projection |

## 다음 개발과 현재 Gate

```text
준비계약 [구현]
  ↓
사건별 adapter [구현·합성 검증] ← 현재
  ↓
원천/후보 binding·code identity·expected receipt·control/STOP 상세
  ↓
RES-04P 전체 Gate 판정
  ↓
SYS-05 → ANA-05 → ANA-06 → ANA-07 → ANA-08 → UX-06
```

작업 adapter가 인증하는 입력 범위를 분명히 한 뒤 manifest/source binding을 별도 모듈로 연결한다. adapter는 비공백/비주석222줄로 warning band이므로 다음 책임을 이 파일에 누적하지 않는다. 테스트 파일도205줄이므로 후속 binding/control 시험은 별도 파일로 작성한다.
필요한 경제 실행 승인은 별도지만, 개발상의 선택은 위임 범위에서 직접 결정한다. 이번에 새 masterplan을 재작성하거나 사용자에게 입력 경로를 다시 요구하지 않는다.
