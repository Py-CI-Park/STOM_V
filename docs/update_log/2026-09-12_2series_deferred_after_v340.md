# 2026-09-12 2U/2U_C/wt-dev 후속 계획 (이번 사이클 코드 미반영)

- 기준일: 2026-09-12
- 성격: HOLD 레인의 추후 재개 정본. 지금 wt-dev를 건드리지 않는다.
- 전제: V2 upstream 신규 없음 (refs/tags/V2.0 여전히 V2.79).
- 연결: docs/update_log/2026-09-12_upstream_v336_v340_intake_plan.md
- 이전 계획: docs/update_log/2026-07-12_2series_pyd_review_and_backport_plan.md (V3.33~35 백포트, 미실행 유지)

---

## 0. 한줄 판정

~~~
2* 시리즈는 이번 업스트림 흡수에서 제외한다.
V2.80이 생기기 전에는 V2->2U 공식 전파 사유가 없다.
wt-dev는 research/v516-d3-mcap-dev + dirty 이므로 공식 overlay 금지.
나중에 할 때는 wt-dev를 정리하지 말고, 깨끗한 2U_C worktree를 새로 만든다.
~~~

---

## 1. 현재 위치

| 대상 | 상태 | 이번 사이클 | 나중 |
|---|---|---|---|
| STOM_V (V2 공식) | V2.79 완료, origin 일치 | 문서만 | V2.80 생기면 ingress |
| wt-2u | V2.79 완료, 3b7a3aeb ahead 1 | HOLD | push 승인, 2U_C에 추론 정렬 이식은 merge 금지 |
| STOM_Version_2U_C 브랜치 | 8006cd93, origin ahead 26, 체크아웃 없음 | HOLD | 깨끗한 worktree에서만 백포트 |
| wt-dev | research/v516-d3-mcap-dev 97a59ad3, dirty | HOLD | 개발 계속. 공식 파일 투입 금지 |

중요 계보: 2U 와 2U_C 의 merge-base는 220cadc9 (V2.51.U1.5) 이다.
2U_C는 2U를 fast-forward한 브랜치가 아니다. V2.79는 c38050fa 등 custom 경로로 되살렸다.
따라서 나중에 2U의 3.13 pyd-free 정렬(3b7a3aeb 등)을 넣을 때도 git merge STOM_Version_2U 를 쓰지 않는다.

~~~
STOM_Version_2  --V2.79-->  STOM_Version_2U (3b7a3aeb, ahead 1)
        |
        X  merge 금지 (base = V2.51)
        |
STOM_Version_2U_C (8006cd93, ahead 26, 미체크아웃)
        |
        +-- (나중) 새 worktree + feature/v3-backport-*
        |
wt-dev research/v516-d3-mcap-dev  << 지금 여기, dirty 보존
~~~

---

## 2. wt-dev HOLD 규칙

보존할 것:

- 브랜치 research/v516-d3-mcap-dev @ 97a59ad3
- 삭제된 docs/research/condition_research/reports/* (작업 트리 D). 복구/삭제는 사용자 판단
- untracked .gjc / .omo / evidence. 커밋 금지, 삭제 금지

하지 말 것:

~~~
X git add -A
X git clean
X STOM_Version_2U_C 로 checkout (wt-dev가 홀더가 아님)
X V3 official 파일 restore
X 2U merge
X 백포트를 이 dirty 트리에 섞기
~~~

재개 명령 (미래, 사용자 승인 후):

~~~powershell
# wt-dev는 그대로 둔다
git -C C:\System_Trading\STOM\STOM_V worktree add C:\System_Trading\STOM\STOM_V.wt-2uc-clean STOM_Version_2U_C
cd C:\System_Trading\STOM\STOM_V.wt-2uc-clean
git switch -c feature/v3-backport-bp2-bp1-YYYYMMDD STOM_Version_2U_C
~~~

경로 이름은 예시. 기존 wt-2uc archive 브랜치(integration/adopt-cli-v267-into-2uc)를 덮어쓰지 말 것.

---

## 3. 나중에 이식할 후보 (Kiwoom 유지)

LS 전용은 제외. broker-neutral만. 이전 계획서 BP-1/2/3는 미실행 상태로 유지하고, V3.36~40에서 추가된 것만 아래에 덧붙인다.

### 3.1 기존 (2026-07-12, 미실행)

| ID | 원천 | 기능 | 우선 | 2U_C 파일 |
|---|---|---|---|---|
| BP-2 | V3.35 | 주문 응답/예외 처리 (upbit/binance) | P1 | trade/upbit/upbit_restapi.py, upbit_trader.py, binance_trader.py |
| BP-1 | V3.35 | 바이낸스선물 native 정정주문 | P1 | trade/binance/binance_trader.py |
| BP-3 | V3.34 | 바이낸스 감시종목제한 | P2 | receiver + 설정 UI + DB migration |
| BP-7 | V3.33 | 명언 텍스트만 | P3 보류 | 구조 변경 금지 |
| 제외 | V3.34/35 | LS 시장가, 해외주식 체결, ordxctptncode | - | Kiwoom 무관 |

실행 순서 유지: BP-2 -> BP-1 -> BP-3. 2U_C 직접 커밋 금지.

### 3.2 신규 (V3.36~V3.40, 이번 발견)

| ID | 원천 | 기능 | 판정 | 이유 |
|---|---|---|---|---|
| BP-8 | V3.36 | 바이낸스 주문체결 데이터 처리 수정 | 검토 P2 | binance_trader.py 존재. 의미 단위 이식. diff 그대로 apply 금지 |
| BP-9 | V3.37 | 위탁증거금율/선물 수익률 | 대부분 제외 | wt-dev에 국내선물(future) lane 없음. binance 수익률 공식만 증상 대조 |
| BP-10 | V3.37 | requirements bump | 보류 | 2U_C 런타임 고정과 충돌 가능. 별도 승인 |
| BP-11 | V3.38 | 차트 화살표 zValue, 분봉 시간 표시 | 검토 P3 | UI 파일이 V2 구조(ui/set_*, ui_mainwindow)라 라인 이식 불가. 증상 단위 |
| BP-12 | V3.38/39 | 무료 라이선스 실매매 제한, check_stom_public | 제외 | V3 라이선스/pyd 계약. 2U_C 시리얼 체계와 다름 |
| BP-13 | V3.39 | 거래량분석 순매수금액 기준 | 검토 P2 | wt-dev에 strategy/analyzer_volume_spike.py 존재. 의미 이식 가능 |
| BP-14 | V3.39 | 계정삭제 단축키 A->L | 보류 | V2 단축키 맵이 다름. 충돌 확인 후 |
| BP-15 | V3.40 | 텔레그램 잔고청산 핸들러 / 매도 스크린샷 | 검토 P1 | 2U/wt-dev 모두 utility/telegram_bot.py 존재. 구조는 V2식. 의미 이식 |
| BP-16 | V3.40 tail | 코스닥150 틱가치 | 제외 | LS restapi 전용 |
| BP-17 | V3.40 | info_for_buy/info_for_sell 언팩 | 검토 P2 | wt-dev trade/base_strategy.py 존재. 분봉 언팩 버그면 채택 |

나중에 시작 순서 권고:

~~~
1) 깨끗한 2U_C worktree
2) BP-2 (예외 처리)  -> BP-1 (정정주문)   # 기존 P1
3) BP-15 (텔레그램)                     # 신규 P1, 실거래 알림
4) BP-8 / BP-13 / BP-17                 # 증상 대조 후 채택
5) BP-3 (감시종목제한, DB migration)
6) 나머지 보류/제외
~~~

V3K 프로그램 파일과 겹치면 V3K 우선 (2026-07-12 계획서 규칙 유지).

---

## 4. 2U ahead 1 처리

커밋 3b7a3aeb '파이썬 3.13 기준으로 2U pyd-free 런타임을 긴급 정렬한다' 는 2026-07-12 게이트 통과, 미push.

| 선택 | 언제 |
|---|---|
| origin push | 사용자 명시 시. 이번 흡수와 무관 |
| 2U_C 이식 | merge 금지. 의미 단위 cherry-pick 또는 재구현 |
| 방치 | 기본. 2U lane은 이미 V2.79 정합 |

---

## 5. 재개 체크리스트

~~~
[ ] wt-dev 브랜치/dirty 가 그대로인지 확인 (정리하지 말 것)
[ ] 새 2U_C worktree 가 archive wt-2uc 와 경로가 겹치지 않는지
[ ] 2026-07-12 BP-1/2/3 계획서를 먼저 읽고, 본 문서 BP-8~17을 덧붙인다
[ ] V3 원천 diff는 wt-3u 의 해당 버전 경계에서 조회한다. 2U 파일에 그대로 apply 하지 않는다
[ ] 각 BP마다 smoke_offline_gui + verify_pyd_gui_contract + py_compile
[ ] 완료 항목은 CARRY_FORWARD_REGISTRY 2U_C allowlist에 기록
~~~

이 문서만으로는 수익/릴리스/실거래 완료를 주장하지 않는다. 백포트 구현과 게이트는 별 사이클이다.
