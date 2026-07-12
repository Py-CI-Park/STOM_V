# 2026-07-12 2U/2U_C pyd→py 재검토 결과 및 백포트 상세 계획서 (계획만, 코드 미반영)

## 0. 문서 목적과 범위

이 문서는 두 가지를 담는다.

1. **재검토 결과 (완료)**: V3U/3U_C/2U/wt-dev(2U_C 계열)의 pyd→py 반영 상태를 2026-07-12 기준으로 실제 게이트를 돌려 재검증한 결과.
2. **2* 시리즈 실행 계획서 (미실행)**: 2U/2U_C에는 이번 세션에서 코드 반영을 하지 않았다. 다음 작업자(AI agent 포함)가 본 문서만 보고 그대로 실행할 수 있도록 파일 단위 매핑, 명령, 검증, 금지사항을 명시한다.

전제 문서: `AGENTS.md`, `docs/WORKTREE_STRATEGY.md`, `docs/CARRY_FORWARD_REGISTRY.md`, `docs/V3_UPDATE_OPERATING_SYSTEM.md`.

연결 문서: 전체 워크트리 pyd→py 상태 지도와 본 계획서의 wt-dev 반영 기능 연결은
`docs/update_log/2026-07-12_worktree_pyd_status_map.md`에 정리되어 있다.

---

## 1. 재검토 결과 스냅샷 (2026-07-12 실행 완료)

### 1.1 V3 계열 — V3.35 흡수 완료

| lane | branch | commit | 게이트 결과 |
|---|---|---:|---|
| V3 공식 | `STOM_Version_3` | `c6ac10b2 STOM V3.35` | changed-path parity clean, py_compile pass, `ui/main_window.pyd` 보존 |
| V3U | `STOM_Version_3U` | `2fb212e2` overlay + `f4b8fb42` 기록 | smoke OK, verifier 8/8 PASS, pytest 49, attr critical=0 warn=0 |
| 3U_C | `STOM_Version_3U_C` | merge `ff704397` + 기록 `66220795` | verifier 8/8 PASS, pytest 49, tests/v3uc 32, invariant diff allowlist only |

V3.35 범위: `c3db5f9c..9d24b635` 12개 파일 (+210/-139). marker 이후 tail 4건(`1150bc99`, `01187d69`, `80412a0d`, `9d24b635`) 포함.

### 1.2 V3U pyd→py 재검토 (완료)

| 점검 항목 | 결과 | 판정 |
|---|---|---|
| V3U tracked `.pyd` | 0건 | 정상 |
| 3U_C tracked `.pyd` | 0건 | 정상 |
| V3 공식 `ui/main_window.pyd` | 존재, upstream 최신과 sha256 일치 | 정상 |
| `3U vs 3` diff | V3U scaffolding(tests/scripts/docs/main_window.py/pytest.ini 등) + `CLAUDE.md` + `ui/create_widget/set_style.py` 1줄 | 아래 참고 1건 외 정상 |
| 통합 게이트 | V3U/3U_C 모두 8/8 PASS | 정상 |

**참고 (기지 항목, 신규 결함 아님)**: `ui/create_widget/set_style.py`의 다크레드 테마 분기 `color_hv_bt = QColor(73, 48, 48)` 1줄은 V3U 결함 보정분으로 update_log 사유는 있으나 CARRY_FORWARD allowlist 정식 등재가 안 된 상태다. `docs/V3U_NEXT_STEPS.md` §3 A8(allowlist 정합성) 옵션으로 이미 추적 중. 다음 V3U 사이클에서 A8 실행 권장.

### 1.3 2U pyd→py 재검토 (완료, 코드 무변경)

| 점검 항목 | 결과 | 판정 |
|---|---|---|
| worktree/branch | `STOM_V.wt-2u` / `STOM_Version_2U` @ `3b7a3aeb` | origin 대비 **ahead 1 (미push)** |
| tracked `.pyd` | 0건 | 정상 (pyd-free 유지) |
| `python scripts/smoke_offline_gui.py --branch STOM_Version_2U --version V2.79 --offline --log-dir .omx/logs/2u` | `[OK] offline GUI smoke passed` | 정상 |
| `python scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/2u/verify_2026-07-12_review.json --log-dir .omx/logs/2u` | `[OK] pyd GUI contract passed` | 정상 |
| untracked | `ai_strategy_loop/`, `backtest/graph/` | runtime/보호 경로, 커밋 금지 |

미push commit `3b7a3aeb`("파이썬 3.13 기준으로 2U pyd-free 런타임을 긴급 정렬한다")은 검증 통과 상태다. push 여부는 사용자 결정 항목(§4.1).

### 1.4 wt-dev(2U_C 계열) 재검토 (완료, 코드 무변경)

| 점검 항목 | 결과 | 판정 |
|---|---|---|
| worktree/branch | `STOM_V.wt-dev` / `feature/audit-p0-execution-20260712` @ `3542f5d4` | 활성 개발 중 |
| base 관계 | `STOM_Version_2U_C`(@`8006cd93`)가 HEAD의 ancestor, 696 commits ahead | 정상 계보 |
| `STOM_Version_2U_C` origin 대비 | **ahead 26 (미push)** | 사용자 결정 항목(§4.1) |
| tracked `.pyd` | 0건 | 정상 (2U 상속) |
| smoke + pyd GUI contract (wt-dev 워크트리에서 실행) | 둘 다 `[OK]` | **pyd 추론 상속 정상, 개발 계속 가능** |
| 진행 중 프로그램 | **V3K** (V3 기능 + Kiwoom 유지) — `docs/plans/*v3k*`, `scripts/audit_v3k_*`, phase A~H 진행, LS excise(g) 완료 흔적 | 백포트는 V3K 프로그램과 조율 필수 |

결론: **2U/2U_C 모두 pyd→py 추론 상태 건강. wt-dev는 문제없이 개발 계속 가능.**

---

## 2. 2U_C(wt-dev) V3 최신 기능 백포트 후보 매트릭스 — V3.33~V3.35

Kiwoom 유지 원칙: LS API 전제 변경은 **제외**. broker-neutral(바이낸스/업비트/백테/UI)만 선별.

| ID | 원천 | 기능 | 후보 판정 | 이유 |
|---|---|---|---|---|
| BP-1 | V3.35 `231bea44` | 바이낸스선물 정정주문 (native modify) | **후보 (P1)** | broker-neutral. V2는 현재 취소+재주문 방식(`ModifyOrder`) — native 정정으로 개선 여지 |
| BP-2 | V3.35 `8dceab9f`/`e64dce1b` | 주문 응답/예외 처리 강화 (upbit/binance) | **후보 (P1)** | broker-neutral 방어 패턴. 실거래 안정성 직접 영향 |
| BP-3 | V3.34 `213d5e4a` | 바이낸스선물 감시종목제한 설정 | **후보 (P2)** | broker-neutral. 단 설정 DB `main` 테이블 컬럼 추가 → migration spec 필수 |
| BP-4 | V3.35 `9db1f2d9` | LS 시장가 주문가격 오류 수정 | **제외** | LS 전용. Kiwoom 주문 경로와 무관 |
| BP-5 | V3.34 `934c4f26` | 해외주식 주문체결 처리 수정 | **제외** | LS 해외주식 전용. V2는 키움 해외선물 구조 |
| BP-6 | V3.35 tail `1150bc99`/`80412a0d` | LS ordxctptncode 방어, 해외선물 체결/정정취소 분리 | **제외** | LS restapi 전용 |
| BP-7 | V3.33 | 백테 시작 코드 분리/간소화, 명언 분리 | **보류 (P3)** | V3 UI 구조 리팩토링. V2 구조가 달라 이식 이득 낮음. 필요 시 명언 텍스트만 선택 반영 |

---

## 3. 백포트 실행 절차 (그대로 실행 가능한 상세 계획)

### 3.0 공통 준비 (모든 BP 공통, 순서 고정)

```bash
# 1) 작업 위치와 기준 확인
cd C:/System_Trading/STOM/STOM_V.wt-dev
git status --short --branch        # 활성 feature 브랜치 확인. 개발 중 파일과 섞이지 않게 새 브랜치 사용
git log --oneline -3 STOM_Version_2U_C

# 2) 백포트 전용 feature 브랜치 생성 (2U_C에 직접 커밋 금지)
git switch -c feature/v3-backport-bp1-bp2-<YYYYMMDD> STOM_Version_2U_C

# 3) V3 원천 diff 확보 (wt-3u 워크트리에서 조회)
git -C ../STOM_V.wt-3u diff c3db5f9c..9d24b635 -- trade/binance/binance_trader.py   # BP-1/BP-2 원천
git -C ../STOM_V.wt-3u diff c3db5f9c..9d24b635 -- trade/restapi_upbit.py trade/upbit/upbit_trader.py  # BP-2 원천
git -C ../STOM_V.wt-3u diff bc23a067..c3db5f9c -- trade/binance/binance_receiver.py ui/event_click/button_clicked_settings.py utility/db_control/database_check.py utility/settings/setting_user.py  # BP-3 원천
```

주의: V3와 V2는 파일 구조가 다르다. **diff를 그대로 apply 하지 말고**, 아래 파일 매핑에 따라 의미 단위로 이식한다.

### 3.1 BP-1: 바이낸스선물 정정주문 (P1)

V3 원천 요지: `BinanceTrader.__init__`에 `지정가코드 = {'지정가':'GTC','지정가IOC':'IOC','지정가FOK':'FOK'}` 도입, 주문/정정 흐름 재정리.

| 단계 | 내용 |
|---:|---|
| 1 | 현행 확인: `trade/binance/binance_trader.py`의 `ModifyOrder`(약 line 505~529)는 `CANCEL 주문 + CreateOrder` 재주문 방식. `dict_order`의 정정횟수 증가 로직 확인 |
| 2 | python-binance 클라이언트에 `futures_modify_order` 지원 여부 확인: `python -c "import binance; print(hasattr(binance.Client, 'futures_modify_order'))"` |
| 3-a | **지원 시**: `ModifyOrder`에서 CANCEL+재주문 대신 `self.binance.futures_modify_order(symbol=종목코드, orderId=주문번호, side=매도수구분, quantity=미체결수량, price=정정가격)` 호출로 교체. 실패(예외) 시 기존 CANCEL+재주문 경로로 fallback 유지 |
| 3-b | **미지원 시**: BP-1은 라이브러리 업그레이드 선행 항목으로 보류 기록만 남기고 종료 |
| 4 | 모의투자 분기(`self.dict_set['모의투자']`)는 기존 UpdateChejanData 시뮬 경로 유지 — native 호출 금지 |
| 5 | 검증: `python -m py_compile trade/binance/binance_trader.py` → 아래 §3.5 공통 검증 |

### 3.2 BP-2: 주문 응답/예외 처리 강화 (P1)

V3 원천 요지: ① upbit `order_coin` 시그니처 정리(시장가/지정가 분기 명확화) + REST 응답 예외처리, ② 주문 응답 dict 접근 전 `ret` 유효성 검사, ③ 주문 실패 시 로그 후 안전 반환.

| 단계 | 파일(wt-dev) | 이식 내용 |
|---:|---|---|
| 1 | `trade/upbit/upbit_restapi.py` | 주문 함수의 응답 처리에 V3 패턴 이식: 응답이 dict가 아니거나 `error` 키 포함 시 (주문번호=None, 응답메시지=오류문자열) 반환. 시장가 매수=`price`만/시장가 매도=`volume`만/지정가=둘 다 세팅 분기를 V3 `order_coin` 구조로 정리 |
| 2 | `trade/upbit/upbit_trader.py` | 주문번호 None 체크 후 FAIL 로그(`windowQ` 기본로그) + 조기 반환 경로 확인/보강 |
| 3 | `trade/binance/binance_trader.py` | `SendOrder` 내 `self.binance.futures_create_order(...)` 호출을 try/except로 감싸고, 실패 시 `[{주문구분}_FAIL]` 로그 + `dict_order` 미등록 보장 (V3 `_check_order_error` 패턴의 V2식 인라인 이식) |
| 4 | 검증 | `python -m py_compile trade/upbit/upbit_restapi.py trade/upbit/upbit_trader.py trade/binance/binance_trader.py` → §3.5 |

### 3.3 BP-3: 바이낸스선물 감시종목제한 (P2, DB migration 포함)

V3 원천 요지: 설정 `main` 테이블에 `바낸감시종목제한`(0/1), `바낸감시종목개수`(기본 100) 추가. receiver가 전일 거래대금 상위 N개만 감시.

| 단계 | 파일(wt-dev) | 이식 내용 |
|---:|---|---|
| 1 | **DB migration 먼저**. `_database/setting.db` 백업 후: `main` 테이블에 두 컬럼 추가. V3 `database_check.py`의 자동 마이그레이션 패턴 이식 — 컬럼 부재 시 `df['바낸감시종목제한']=0; df['바낸감시종목개수']=100` 후 `to_sql(..., if_exists='replace')`. V2의 해당 파일은 `utility/database_check.py`(또는 wt-dev 기준 동등 파일)에서 main 컬럼 정의 확인 후 동일 위치에 반영 |
| 2 | `utility/setting.py`(V2의 `setting_user` 동등부) | `dict_set`에 `바낸감시종목제한`, `바낸감시종목개수` 로드 추가 |
| 3 | `trade/binance/binance_receiver_min.py`, `trade/binance/binance_receiver_tick.py` | 종목 목록 구성 지점에서 V3 패턴 이식: `if self.dict_set['바낸감시종목제한']: rank=self.dict_set['바낸감시종목개수']; self.dict_data=dict(sorted(self.dict_data.items(), key=lambda x: x[1][5], reverse=True)[:rank])` — V2의 데이터 구조 인덱스(전일 거래대금 위치)는 실제 코드에서 확인 후 조정 |
| 4 | 설정 UI | V2 설정탭(binance 그룹)에 체크박스+입력칸 추가. wt-dev의 pyd-free UI 파일에서 기존 바이낸스 설정 그룹 위치를 찾아 V3 `set_setup_tap.py`의 `sj_main_cheBox_03`/`sj_main_liEdit_02` 패턴 이식. 저장 로직에는 `int()` 변환 전 `isdigit()` 검증 추가 (V3.34 late review watch 반영) |
| 5 | 검증 | migration 재실행 멱등성 확인(두 번 실행해도 스키마 동일) → §3.5 |

### 3.4 BP-7 (보류, 선택): V3.33 명언 텍스트

실행할 경우: V3 `ui/create_widget/famous_saying.py`의 리스트에서 신규/수정 명언만 추출해 V2의 명언 정의 위치에 텍스트만 반영. 구조 변경(파일 분리) 금지.

### 3.5 공통 검증 게이트 (각 BP 완료마다 전부 실행)

```bash
cd C:/System_Trading/STOM/STOM_V.wt-dev
python -m py_compile <수정한 파일들>
python scripts/smoke_offline_gui.py --branch <feature-branch> --version V2.79 --offline --log-dir .omx/logs/2uc
python scripts/verify_pyd_gui_contract.py --branch <feature-branch> --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/2uc/verify_<date>_bp.json --log-dir .omx/logs/2uc
python -m pytest tests/unit -q   # 존재하는 단위 테스트 회귀
```

기대: smoke `[OK]`, contract `[OK]`, pytest 기존 통과 수 유지.

### 3.6 커밋/기록 의무 (각 BP별)

| 항목 | 규칙 |
|---|---|
| 커밋 | 한글 제목 + `## 배경/## 변경 사항/## 검증` 본문. BP당 1커밋. `git add`는 파일 명시 |
| carry-forward | wt-dev `docs/`의 2U_C allowlist/update_log에 항목 추가: source V3 version, source commit, 제외한 LS 의존성, Kiwoom/V2 보정 내용, 검증 결과 |
| V3K 조율 | 백포트 파일이 V3K phase 대상 파일과 겹치면(특히 trade/binance, 설정 DB) V3K 계획 문서(`docs/plans/*v3k*`)의 해당 phase 상태를 먼저 확인하고 충돌 시 V3K 우선 |
| 순서 | BP-2 → BP-1 → BP-3 권장 (예외 처리 기반을 먼저 깔고, 정정주문, 마지막으로 DB migration 동반 항목) |

---

## 4. 사용자 결정 필요 항목

### 4.1 미push 커밋 처리

| lane | 상태 | 권장 |
|---|---|---|
| `STOM_Version_2U` | ahead 1 (`3b7a3aeb`, 검증 통과) | push 권장 — 사용자 승인 후 `git -C C:/System_Trading/STOM/STOM_V.wt-2u push origin STOM_Version_2U` |
| `STOM_Version_2U_C` | ahead 26 (`8006cd93`) | wt-dev 개발 흐름과 연결된 커밋들 — 개발 주체가 시점 결정 |

### 4.2 기타

| 항목 | 내용 |
|---|---|
| V3U A8 (allowlist 정합성) | `set_style.py` 1줄을 CARRY_FORWARD allowlist에 정식 등재 + 게이트에 allowlist diff 검사 추가 (다음 V3U 사이클 후보) |
| `_database_backup_2026-05-22/` | wt-3u untracked 백업. 보존/이동/삭제 사용자 판단 유지 |
| 사용자 GUI 확인 | V3.34~V3.35 주문 경로(바이낸스 정정주문, 감시종목제한, 주문 예외) 실거래 전 수동 확인 |

---

## 5. 완료 기준 요약

| 작업 | 완료 기준 |
|---|---|
| BP 백포트 각각 | py_compile + smoke + contract + pytest 통과, 커밋 1건, allowlist/update_log 기록 |
| 전체 | `STOM_Version_2U_C`(또는 승격 대상 feature) 기준 smoke/contract `[OK]` 유지, V3K 프로그램과 충돌 0 |
| 재검증 주기 | 다음 V3.36+ 흡수 시 §1 스냅샷 표 갱신 |
