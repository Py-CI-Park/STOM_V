# V3U 인수인계 검증 체크리스트와 직접 개발 검토 요약

작성일: 2026-05-07
대상 worktree: C:\System_Trading\STOM\STOM_V.wt-3u
대상 branch: STOM_Version_3U
상위 감사 문서: docs/update_log/2026-05-06_v3u_final_parity_audit.md

## 1. 목적

이 문서는 STOM_Version_3U lane이 다음 단계(잠재적 STOM_Version_3U_C 생성 또는 lane 동결)로 넘어가기 전에 필요한 검증 절차를 정리한다. 자동 검증 가능한 항목과 사용자 환경에서만 수행 가능한 항목을 구분하고, 본 세션에서 직접 개발하며 발견한 추가 검토 포인트를 함께 기록한다.

핵심 질문은 다음과 같다.

1. 자동화 가능한 정적/구조 검증은 모두 통과했는가?
2. 자동화 불가능하지만 사용자 환경에서 수행해야 할 검증은 무엇인가?
3. 직접 개발하며 발견한 추가 검토 포인트는 무엇인가?

## 2. 자동 검증 결과 (2026-05-07 시점 재현)

상위 감사 문서의 "Tested" 항목을 본 세션에서 재현하여 모두 PASS를 확인했다.

| # | 검증 명령 | 결과 |
|---|-----------|------|
| 1 | `python -m py_compile ui/main_window.py scripts/v3u_gui_contract_manifest.py scripts/v3u_smoke_offline_gui.py scripts/verify_v3u_pyd_gui_contract.py` | exit=0 |
| 2 | `python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.18 --offline --log-dir .omx/logs/v3u` | `[OK] V3U offline structural smoke passed` |
| 3 | `python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.18 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_v3u_pyd_gui_contract_rerun.json --log-dir .omx/logs/v3u` | `[OK] V3U pyd GUI contract passed` |
| 4 | `git ls-files '*.pyd' '_database/*' '_log/*' '*.db'` (V3U) | 결과 없음 |
| 5 | `git -C STOM_V branch -a \| grep '3U_C\|3_C'` | 결과 없음 (Directive 준수) |
| 6 | `python scripts/verify_release_sync.py` (V2 lane) | `release sync preflight passed` |

## 3. 자동 검증 불가 항목 (사용자 환경 필요)

### 3.A V3U pyd 제거 관련 (ui/main_window.pyd → ui/main_window.py 전환)

| # | 미검증 항목 | 자동화 불가 사유 | 사용자 검증 방법 | 위험도 |
|---|------------|------------------|----------------|--------|
| A1 | PyQt MainWindow 실제 기동 | DISPLAY/Qt 이벤트 루프 필요 | `python stom.py` 실행 후 메인창 표시 확인 | High |
| A2 | guarded fallback 발동 여부 | pyd legacy slot 호출 시점에만 발동 | 메인창 띄우고 로그에서 fallback 메시지 모니터 | High |
| A3 | 위젯 시그널/슬롯 연결 (create_widget, update_widget, draw_chart, etcetera lazy boundary) | Qt event 발생 필요 | 각 탭(전략작성/백테스트/실시간차트/거래) 클릭으로 위젯 반응 확인 | High |
| A4 | 큐/프로세스 핸들 초기화 | 실제 프로세스 spawn 필요 | 백테스트 시작 → engine 프로세스 PID 생성 확인 | Medium |
| A5 | 차트 상태 속성 복원 | 사용자 zoom/pan 동작 필요 | 실시간 차트에서 타임프레임 변경, 줌 인/아웃 | Medium |

### 3.B V3.18 신규 기능 변경

| # | 미검증 항목 | 자동화 불가 사유 | 사용자 검증 방법 | 위험도 |
|---|------------|------------------|----------------|--------|
| B1 | 리스크분석 최소 데이터 수량 30개 적용 | 실데이터 분석 사이클 필요 | 실시간 매매 활성화 후 30개 미만/이상 시 분석 결과 차이 비교 | Medium |
| B2 | 실시간 매매 prange 삭제로 CPU<90% | OS 리소스 모니터 + 멀티프로세스 실행 필요 | 작업 관리자에서 분석 프로세스 CPU 사용률 측정 | Medium |
| B3 | LS증권 웹소켓 체결/호가 분리 | LS 자격증명 + 라이브 시장 필요 | LS증권 로그인 후 체결과 호가 두 채널 별도 수신 로그 확인 | High |
| B4 | 거래소별 미지원 주문유형 차단 (해외주식 매수=지정가, 매도=지정가/시장가) | UI 콤보박스 + 거래소 컨텍스트 필요 | 해외주식 선택 → 매수에서 시장가 비활성 확인 | Low |
| B5 | DB 잔고 테이블 변동시만 저장 | 실시간 잔고 변동 + DB write 추적 필요 | 잔고 동일 상태에서 INSERT 발생 안 함을 sqlite log로 확인 | Medium |
| B6 | 백테스트엔진 변손익분석 학습데이터 로드 함수명 수정 | 실제 백테스트 실행 필요 | 변손익분석 옵션으로 백테스트 한 사이클 완주 | High |
| B7 | 더미용 시장미시구조분석 객체 생성 오류 수정 | 전략테스트 진입 필요 | 전략테스트 탭에서 미시구조 옵션 비활성 시에도 오류 없음 확인 | Medium |
| B8 | 전략작성탭 아이콘 변경 | 시각 확인 | 메인창에서 strategy.png/strategy2.png 표시 확인 | Low |

### 3.C 거래소 실거래 흐름

| # | 미검증 항목 | 자동화 불가 사유 | 사용자 검증 방법 | 위험도 |
|---|------------|------------------|----------------|--------|
| C1 | LS증권 REST API (trade/restapi_ls.py 150줄 변경) | 자격증명 + 영업시간 필요 | 모의투자 계좌로 주문/체결/잔고 조회 | High |
| C2 | 바이낸스 REST API (trade/restapi_binance.py 108줄 변경) | API key + 거래 활성 시간 | 테스트넷에서 주문 라이프사이클 검증 | High |
| C3 | 업비트 REST API (trade/restapi_upbit.py 98줄 변경) | API key 필요 | 최소 단위 시장가 매수 후 즉시 매도 | High |
| C4 | base_strategy / base_trader 22+13줄 변경 | 실시간 전략 실행 필요 | 모의 전략으로 1시간 이상 무인 운영 | High |

### 3.D 데이터베이스 영속성

| # | 미검증 항목 | 자동화 불가 사유 | 사용자 검증 방법 | 위험도 |
|---|------------|------------------|----------------|--------|
| D1 | DB 마이그레이션 호환성 (V3.08 PRIMARY KEY 도입 이후 누적) | 기존 user DB 필요 | 백업 후 기존 DB로 V3U 기동 → 충돌/마이그레이션 로그 확인 | High |
| D2 | 거래소별 18개 분리 설정 저장/로드 | 18개 거래소 컨텍스트 전환 필요 | 기본설정에서 거래소 변경 → 설정값 별도 보존 확인 | Medium |
| D3 | database_check.py 변경 효과 | 실 DB 파일 필요 | 첫 기동 시 테이블 자동 생성 로그 확인 | Medium |

### 3.E V3 라인 업스트림 정합성

| # | 미검증 항목 | 자동화 불가 사유 | 사용자 검증 방법 | 위험도 |
|---|------------|------------------|----------------|--------|
| E1 | 로컬 V3.09~V3.18 vs 업스트림 V3.0 태그 발산 | 정책 결정 필요 (CLAUDE.md상 V3는 V2.79 웨이브 제외) | 향후 V3 wave 시작 시 업스트림 PR/체결 수정 10개 흡수 결정 | Low (현재 정책상) |
| E2 | 업스트림에만 있는 10개 커밋 (업비트 웹소켓, DB PRIMARY KEY, README 등) | 머지 결정 필요 | `git log STOM_Version_3..refs/remotes/devstom_tmp/tags/V3.0` 검토 | Low |

### 3.F V3U → 3U_C 다음 단계

| # | 미검증 항목 | 자동화 불가 사유 | 사용자 검증 방법 | 위험도 |
|---|------------|------------------|----------------|--------|
| F1 | STOM_Version_3U_C 생성 시점 결정 | Directive에 의해 의도적 보류 중 | 인수인계 완료 + 1~2순위 검증 통과 후 사용자 결정 | N/A |

## 4. 우선순위 권장 사용자 검증 시나리오

| 순위 | 검증 그룹 | 시나리오 | 예상 시간 |
|------|-----------|---------|----------|
| 1순위 | A1+A2+A3+B8 | `python stom.py` → 모든 탭 클릭 → 로그 확인 | 15분 |
| 2순위 | A4+A5+B6+B7 | 백테스트 1회 + 차트 조작 | 30분 |
| 3순위 | D1+D2+D3 | 백업 DB로 기동 → 거래소 전환 | 20분 |
| 4순위 | C1~C4+B3+B5 | 모의/테스트넷 거래 1시간 | 1시간 이상 |

1~2순위만 통과해도 V3U pyd-free 전환의 핵심 리스크는 거의 모두 커버된다. 3순위는 production 사용 전, 4순위는 release 전에 수행한다.

## 5. 직접 개발 검토 요약 (2026-05-07 세션)

본 세션에서는 V3 라인 두 워크트리(STOM_Version_3, STOM_Version_3U)의 작업 정합성을 직접 검토했다. 아래는 그 과정에서 발견하고 평가한 내용이다.

### 5.1 워크트리 구조 정합성

확인된 워크트리 6개 모두가 CLAUDE.md `Current Promoted State` 섹션과 일치한다.

| 경로 | 브랜치 | 역할 |
|------|--------|------|
| STOM_V/ | STOM_Version_2 | 릴리스 인그레스 |
| STOM_V.wt-2u/ | STOM_Version_2U | V2 → 2U_C 중간 단계 |
| STOM_V.wt-2uc/ | integration/adopt-cli-v267-into-2uc | 아카이브/전환 체크아웃 |
| STOM_V.wt-dev/ | STOM_Version_2U_C | 활성 작업 위치 (V2 lane) |
| STOM_V.wt-3/ | STOM_Version_3 | V3 보관 (V2.79 웨이브 제외) |
| STOM_V.wt-3u/ | STOM_Version_3U | pyd-free 변환 lane |

### 5.2 V3U 마이크로 사이클 평가

V3 위에 4개 커밋으로 응집적 사이클이 형성되어 있다.

```
c04faec0  V3U pyd 제거 경계를 먼저 고정한다       (계획)
d05c132c  V3U pyd 대체 검증 발판을 먼저 세운다     (검증 발판)
3d8f9c1e  V3U pyd 제거를 실제 코드 경계로 전환한다 (실제 코드)
4aef1cce  V3U 최종 parity 감사 증적을 고정한다    (감사 문서)
```

판정: 모범적 구조다. 각 커밋이 단일 책임을 가지며 Constraint, Directive, Rejected, Tested, Not-tested가 명시되어 추후 작업자가 의도와 경계를 재구성할 수 있다.

### 5.3 정책 준수 검증

| 정책 | 상태 |
|------|------|
| 한글 의도 중심 커밋 제목 (CLAUDE.md "Commit Language Rules") | 준수 |
| pyd 보존(V3) vs pyd 제거(V3U) lane 분리 | 준수 |
| _database, _log, *.db 미추적 (CLAUDE.md "Protected Paths") | 준수 |
| STOM_Version_3U_C 미생성 (4aef1cce Directive) | 준수 |
| backtest/graph/ 보호 경로 비침범 | 준수 |
| upstream ingress 정책(V2만 인그레스) 비침범 | 준수 |

### 5.4 발견된 주목 포인트

#### NP-1: V3 업스트림 양방향 발산

- 로컬 V3.09~V3.18 10개가 업스트림 V3.0 태그에 없음 (parkchanil 직접 추가)
- 업스트림 V3.0 태그에 로컬 V3에 없는 10개 커밋 존재 (업비트 웹소켓 수정, DB PRIMARY KEY, README 등)
- CLAUDE.md상 V3는 V2.79 웨이브 제외이므로 현재 시점 동기화 의무 없음
- 향후 V3 wave 시작 시 reconcile 결정 필요 (E1, E2 항목)

#### NP-2: 3d8f9c1e 커밋의 medium confidence

- V3U 커밋 4개 중 이 커밋만 confidence: medium, scope-risk: broad로 표기됨
- 사유: 실제 PyQt GUI runtime 검증이 미완 상태에서 이루어진 코드 경계 전환
- 본 검토 문서의 사용자 검증 시나리오 1~2순위가 이 confidence를 high로 끌어올리는 핵심 절차다

#### NP-3: V3.18 변경 폭이 넓음

- 19개 V3 커밋 누적 + V3.18 한 wave에 8개 신규 기능 변경
- LS증권/바이낸스/업비트 REST API 모두 수정됨 (각각 150/108/98줄)
- 거래소별 실거래 검증 없이는 V3U pyd-free 전환 효과를 단독으로 검증할 수 없음
- 본 문서 3.B와 3.C의 미검증 항목이 이 변경 폭을 반영한다

#### NP-4: 감사 문서 허용 diff 목록과 본 세션 재확인 결과 일치

`STOM_Version_3...STOM_Version_3U`의 변경 파일 7개가 4aef1cce 감사 문서의 허용 목록과 정확히 일치한다.

```
docs/V3U_PYD_REMOVAL_PLAN.md
docs/update_log/2026-05-06_v3u_final_parity_audit.md
scripts/v3u_gui_contract_manifest.py
scripts/v3u_smoke_offline_gui.py
scripts/verify_v3u_pyd_gui_contract.py
ui/main_window.py
ui/main_window.pyd  (D, 삭제됨)
```

본 검토 문서가 추가되면 8개로 늘어나며, 추가 항목은 V3U 전용 증적 범주로 허용 목록에 자연스럽게 포함된다.

### 5.5 자동 검증 한계 명시

| 검증 영역 | 자동 가능 | 자동 불가 |
|----------|----------|----------|
| 정적 (py_compile) | 가능 | - |
| 구조 (import contract) | 가능 (Qt 미기동) | - |
| diff allowlist | 가능 | - |
| guard (pyd/DB/log/branch) | 가능 | - |
| GUI 표시 / 위젯 반응 | - | 불가 (DISPLAY 필요) |
| 시그널/슬롯 / Qt event | - | 불가 |
| 외부 API (LS/바이낸스/업비트) | - | 불가 (자격증명/시장시간) |
| 실 DB 마이그레이션 | - | 불가 (사용자 DB 필요) |
| 멀티프로세스 spawn | - | 불가 (실행 환경 필요) |
| 거래 라이프사이클 | - | 불가 |

본 세션에서 자동 가능한 영역은 모두 통과시켰고, 자동 불가 영역을 본 문서의 3절 25개 항목으로 명시했다.

## 6. 다음 단계 제안

1. 사용자 환경에서 1~2순위 검증 수행 (총 약 45분)
2. 각 항목 결과를 본 문서에 후속 commit으로 추가하거나 별도 결과 문서를 생성
3. 1~2순위 모두 PASS 시 STOM_Version_3U_C 생성 결정 가능
4. 3순위 PASS 후 production 사용 가능 판정
5. 4순위 PASS 후 release 준비 가능

## 7. 제약 조건 및 감사 메타

- Constraint: V3 공식 lane은 upstream pyd를 보존하고 pyd 제거는 V3U에서만 수행해야 한다
- Constraint: 본 검토 문서는 V3U 전용 증적이며 공식 V3 runtime 파일 변경으로 간주하지 않는다
- Constraint: STOM_Version_3U_C branch는 사용자 환경 1~2순위 검증 통과 후에 생성 결정해야 한다
- Confidence: high (자동 검증 영역 재현), medium (사용자 검증 필요 영역의 불확실성 명시)
- Scope-risk: narrow (문서-only 후속 추가)
- Directive: 본 문서를 commit한 후에도 3U_C branch는 사용자 검증 결과 누적 전까지 생성하지 말 것
- Tested: 자동 검증 6종 재현 통과 (본 문서 2절)
- Not-tested: 본 문서 3절에 나열된 25개 항목 전체
