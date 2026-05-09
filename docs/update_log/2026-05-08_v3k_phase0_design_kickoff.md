# V3K-DESIGN-0 Phase 0 사전 설계 kickoff

**작성일**: 2026-05-08 KST
**상위 문서**: `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
**대상 root lane**: `STOM_Version_2` (`C:/System_Trading/STOM/STOM_V`)
**최종 구현 lane**: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
**참조 lane**: `STOM_Version_3` (`STOM_V.wt-3`), `STOM_Version_3U` (`STOM_V.wt-3u`)
**작성 성격**: 설계 단계, runtime 코드 변경 0건

---

## 0. 한 줄 결론

본 문서는 **V3K = V3 기능 + Kiwoom 유지** 트랙의 Phase 0 산출물이다. V3.0~V3.18의 LS증권 제외 신기능을 6개 카테고리로 재분류하고, 카테고리별 목표/Kiwoom data shape mapping 항목/DB migration spec 목차/feature flag 정책/2U_C mirror 정책을 고정한다. **다음 단계는 `V3K-DESIGN-1` (DB/학습 데이터 설계)**이며, 본 문서 통과까지는 코드 변경이 없다.

---

## 1. 목적과 종료 조건

### 1.1 Phase 0 목적

`V3K_full_feature_migration_goal_reset.md` §7이 권장한 다음 6개 산출물을 단일 문서로 고정한다.

```text
1. V3.0~V3.18 LS 제외 기능 전체 inventory 재작성
2. 학습/분석/DB/backtest/realtime/UI별 목표 분해
3. 2U_C Kiwoom data shape mapping 항목 정의
4. DB migration spec 목차 작성
5. feature flag 정책 정의
6. 2U_C mirror 필요성 명시
```

### 1.2 종료 조건

| 항목 | 조건 |
|---|---|
| 코드 변경 | 0건 |
| 문서 합의 | 사용자 검토 통과 |
| V2 commit | 1개 (이 문서 추가) |
| 2U/2U_C mirror | §10 정책에 따라 결정 |
| 다음 단계 | `V3K-DESIGN-1` DB/학습 데이터 설계 진입 가능 상태 |

### 1.3 Phase 0이 하지 않는 것

- analyzer 모듈 이식
- DB migration script 작성
- backtest/realtime runtime 변경
- V3 strategy/backtest/trade 파일의 cherry-pick
- Kiwoom Open API 어댑터 코드 작성
- feature flag 코드 도입
- pyd MainWindow 변경

위 모든 항목은 V3K-DESIGN-1 이후 단계의 산출물이다.

---

## 2. V3.0 ~ V3.18 LS 제외 기능 전체 재인벤토리

### 2.1 분류 체계

V3 update.txt 항목을 다음 6개 + 2개 카테고리로 재분류한다.

| 카테고리 | 코드 | 정의 |
|---|---|---|
| 학습/분석 | **L** | strategy/analyzer_*, manager_formula, stg_globals_func, 학습 데이터 처리 |
| DB / 학습 데이터 저장 | **D** | DB schema, PK migration, INSERT OR REPLACE, 학습 데이터 테이블 |
| 백테스트 학습 적용 | **B** | 백테스트 일자 이전 학습 데이터 로드, 시장별 engine 구조, 미래 누수 차단 |
| 실시간 거래 학습 적용 | **R** | 실시간 학습 데이터 로드, 1초 스냅샷, 자동 학습 trigger |
| UI / 분석 화면 | **U** | settings dialog, radar chart, 분석 progressbar, MainWindow 비침투 변경 |
| 의존성 / 유틸리티 | **X** | timezone, requirements, telegram, sound, log 처리 |
| (참고) LS증권 직접 의존 | LS-EXCL | 본 V3K 트랙 제외 |
| (참고) pyd 구조 변경 | PYD-EXCL | 별도 lane 결정 사항 |

### 2.2 V3 version별 LS 제외 신기능 분류표

각 셀의 표기 규칙: `[카테고리] 항목명 — 현재 2U_C 상태`

#### V3.0 ~ V3.05

| V3 ver | 항목 | 분류 | 현재 상태 |
|---|---|---|---|
| V3.0 | UI/DB/실행파일 간소화 (broker-neutral 부분) | U | ❌ 미반영 |
| V3.0 | base receiver/trader/strategy 도입 (LS 제외 구조) | L+R | ❌ 미반영 |
| V3.0 | telegram screenshot 응답 | X | ❌ 미반영 |
| V3.0 | web dashboard | (별도 제품) | ❌ 본 트랙 제외 |
| V3.01 | Python 3.13 호환 | X | ⚠️ 부분 (timezone만 BP-007A/008A/011A) |
| V3.01 | Mainwindow 함수 파일 분리 | PYD-EXCL | ❌ 미반영 |
| V3.01 | chart hoga sound 재구동 삭제 | X | ❌ BP-004C no-op |
| V3.01 | VI 등록/수신 처리 | R | ❌ 미반영 |
| V3.01 | 계정번호 추출 | (LS-EXCL 가능) | ❌ 검토 필요 |
| V3.01 | Binance precision | (broker) | ❌ BP-003 hold |
| V3.01 | 상장주식수 조회 | D | ❌ 미반영 |
| V3.02 | Binance websocket queue/lib | (broker) | ⚠️ BP-010A 부분 |
| V3.02 | 백테스트 unpack/load/resource cleanup | B | ❌ BP-001 hold |
| V3.02 | type conversion guard | B | ❌ 미반영 |
| V3.02 | 실시간 차트 index mismatch | U | ⚠️ BP-002A/009A 부분 |
| V3.03 | 실시간 차트 x축 보정 | U | ❌ BP-002C hold |
| V3.03 | crosshair duplicate | U | ✅ 2U_C 기존 보유 |
| V3.03 | DB chart arg/arrow | U | ⚠️ BP-002B 부분 |
| V3.03 | 이미지 webcrawling 예외 | X | ⚠️ BP-004A 부분 |
| V3.03 | Python 3.13 color code | U | ✅ BP-004A |
| V3.03 | 백테스트 log/cleanup | B | ❌ BP-001 hold |
| V3.03 | websocket close | (broker) | ❌ 미반영 |
| V3.04 | 백테스트 loading bug | B | ❌ BP-001 hold |
| V3.04 | shutdown 60초 | X | ❌ 미반영 |
| V3.04 | receiver overhead | (broker) | ❌ 미반영 |
| V3.04 | 고DPI font | U | ❌ 미반영 |
| V3.04 | 시가총액 단위 보정 | D | ❌ 미반영 |
| V3.04 | **talib 패턴 학습** | **L** | **❌ HOLD-001** |
| V3.05 | **패턴 학습 멀티 카운트** | **L** | **❌ HOLD-001** |
| V3.05 | UI circular import 차단 | PYD-EXCL | ❌ 미반영 |
| V3.05 | **거래량 프로파일 분석기 추가** | **L** | **❌ 파일조차 없음** |

#### V3.06 ~ V3.10

| V3 ver | 항목 | 분류 | 현재 상태 |
|---|---|---|---|
| V3.06 | 실시간 필터 | R | ❌ 미반영 |
| V3.06 | receiver stop hang | (broker) | ❌ BP-003 hold |
| V3.06 | settings lock | U | ❌ 미반영 |
| V3.06 | DB 관리 로그 정책 | D | ❌ HOLD-002 |
| V3.06 | 시가총액 등록 제외 | D | ❌ HOLD-002 |
| V3.06 | login tab 전환 | U | ❌ 미반영 |
| V3.07 | chart moneytop | U | ⚠️ BP-009B 부분 (table clear만) |
| V3.07 | coin hoga after close | (broker) | ❌ 미반영 |
| V3.07 | 시장 개시 predata | R | ❌ 미반영 |
| V3.07 | timeframe factor list | L+U | ❌ HOLD-001 |
| V3.07 | DB chart 간소화 | U | ❌ 미반영 |
| V3.07 | dialog close list | U | ❌ 미반영 |
| V3.07 | **시가총액 DB 저장** | **D** | **❌ HOLD-002** |
| V3.07 | 체결/호가 시간 자릿수 | (broker) | ❌ 미반영 |
| V3.08 | settings lock dialog 위치 | U | ❌ 미반영 |
| V3.08 | 차트 `is_min` | U | ❌ 미반영 |
| V3.08 | **DB primary key migration** | **D** | **❌ HOLD-002** |
| V3.08 | **거래소별 설정 분리** | **D** | **❌ HOLD-002** |
| V3.08 | Upbit 주문 websocket | (broker) | ❌ BP-003 hold |
| V3.08 | error decorator | X | ❌ 미반영 |
| V3.08 | Alt+X 단축키 | U | ❌ 미반영 |
| V3.08 | sound queue thread | X | ❌ 미반영 |
| V3.08 | pyttsx 다운그레이드 | X | ❌ 미반영 |
| V3.09 | 시장 정보 dict cleanup | X | ❌ 미반영 |
| V3.09 | **strategy 폴더 이동** | **L** | **❌ HOLD-001** |
| V3.09 | globals 대문자 (`stg_globals_func`) | L | ❌ 파일조차 없음 |
| V3.09 | window position | U | ❌ 미반영 |
| V3.09 | path refs | X | ❌ 미반영 |
| V3.09 | **변동성 분석 / 거래량 스파이크 분석 추가** | **L** | **❌ 파일조차 없음** |
| V3.09 | **DB order alignment** | **D** | **❌ HOLD-002** |
| V3.09 | **분석 backengine/strategy 적용** | **L+B** | **❌ HOLD-001 + BP-001** |
| V3.10 | **분석 학습 future-reference fix** | **L+B** | **❌ HOLD-001** (가장 중요한 누수 fix) |
| V3.10 | **DB 관리 후 자동 학습** | **L+D** | **❌ HOLD-001 + HOLD-002** |
| V3.10 | **1초 스냅샷 분석** | **L+R** | **❌ HOLD-001** |
| V3.10 | **백테스트가 학습 데이터를 백테스트 일자 이전 기준으로 로드** | **L+B** | **❌ 핵심 미반영** (사용자 요청 항목) |
| V3.10 | code-test 분석 변수 | B | ❌ BP-001 hold |

#### V3.11 ~ V3.15

| V3 ver | 항목 | 분류 | 현재 상태 |
|---|---|---|---|
| V3.11 | **첫 캔들 수량 fix** | **L** | **❌ HOLD-001** |
| V3.11 | **스냅샷 분석 확장** | **L** | **❌ HOLD-001** |
| V3.11 | risk data cleanup | L | ❌ HOLD-001 |
| V3.11 | risk 1m | L | ❌ HOLD-001 |
| V3.11 | pytz/dateutil/tzlocal 삭제 | X | ✅ BP-007A/008A/011A |
| V3.11 | mock trading API skip | (broker) | ❌ 미반영 |
| V3.11 | **INSERT OR REPLACE helper** | **D** | **❌ HOLD-002** |
| V3.11 | **실시간 매매가 학습 데이터를 로드** | **L+R** | **❌ 핵심 미반영** (사용자 요청 항목) |
| V3.11 | analysis 메시지 | U | ❌ HOLD-001 묶음 |
| V3.12 | crosshair zValue | U | ✅ BP-009A |
| V3.12 | prange | L | ❌ HOLD-001 |
| V3.12 | 단일 strategy 로그 process | L | ❌ HOLD-001 |
| V3.12 | get_optistd 속도 | B | ❌ BP-001 hold |
| V3.12 | **레이더 차트** | **L+U** | **❌ HOLD-001** (시장미시구조 시각화) |
| V3.12 | rank filter | L | ❌ HOLD-001 |
| V3.12 | training 속도/chart funcs | L | ❌ HOLD-001 |
| V3.12 | coin receiver cleanup | (broker) | ❌ BP-003 hold |
| V3.12 | **분석 chart/factor settings** | **L+U** | **❌ HOLD-001** |
| V3.12 | 레이더 close guard | U | ❌ 미반영 |
| V3.12 | Binance non-stream guard | (broker) | ✅ BP-010A |
| V3.13 | strategy 모듈 docs | (docs) | ❌ 미반영 |
| V3.13 | filename 단축 | L | ❌ HOLD-001 |
| V3.13 | snapshot date 추출 | L | ❌ HOLD-001 |
| V3.13 | ranking order | L | ❌ HOLD-001 |
| V3.13 | 변동성 속도 | L | ❌ HOLD-001 |
| V3.13 | volume settings 삭제 | L+U | ❌ HOLD-001 |
| V3.13 | **TP/SL 분석 (변손익)** | **L** | **❌ HOLD-001** (`analyzer_volatility_stop_take.py`) |
| V3.13 | 날짜 변경 ignore | X | ❌ 미반영 |
| V3.14 | strategy variable rename | L | ❌ HOLD-001 |
| V3.14 | **최근 30일 학습 (학습 윈도우)** | **L** | **❌ HOLD-001** |
| V3.14 | backengine 1m indicator | B | ❌ BP-001 hold |
| V3.14 | checkbox load 간소화 | U | ❌ 미반영 |
| V3.14 | numba 최적화 | L | ❌ HOLD-001 |
| V3.14 | **AnalyzerRisk** | **L** | **⚠️ BP-006A dormant 파일만 보존, runtime 미연결** |
| V3.14 | 변동성 변화 레벨 | L | ❌ HOLD-001 |
| V3.14 | VI 캔들 width | U | ❌ 미반영 |
| V3.15 | **변동성 분류 DB reset** | **D** | **❌ HOLD-002** |
| V3.15 | 손익 최근 월 | L | ❌ HOLD-001 |
| V3.15 | numba | L | ❌ HOLD-001 |
| V3.15 | **분석 최적화** | **L** | **❌ HOLD-001** |
| V3.15 | BounceButton | U | ✅ 2U_C 기존 보유 |
| V3.15 | **분석 default settings** | **L+U** | **❌ HOLD-001** |
| V3.15 | **분석 progressbar** | **U** | **⚠️ 일반만 BP-005A, 분석 progressbar는 hold** |

#### V3.16 ~ V3.18

| V3 ver | 항목 | 분류 | 현재 상태 |
|---|---|---|---|
| V3.16 | 최소 캔들 수 | L | ❌ HOLD-001 |
| V3.16 | numba/prange | L | ❌ HOLD-001 |
| V3.16 | confidence 계산 | L | ❌ HOLD-001 |
| V3.16 | 손익 confidence | L | ❌ HOLD-001 |
| V3.16 | 선물 주문 오류 | (broker) | ❌ BP-003 hold |
| V3.16 | **분석 progressbar 간소화** | **U** | **❌ HOLD-001 묶음** |
| V3.16 | DB dialog progressbar | U+D | ❌ 미반영 |
| V3.16 | 시스템 로그 색상 태그 | U | ✅ BP-004A |
| V3.17 | **formula manager factors** | **L** | **❌ `manager_formula.py` 파일조차 없음** |
| V3.17 | Analyzer arg rename | L | ❌ HOLD-001 |
| V3.17 | PyCharm rules | (docs) | ❌ 미반영 |
| V3.17 | **price 분석 데이터 로드** | **L+B** | **❌ HOLD-001** |
| V3.17 | chart 예외 unify | U | ⚠️ BP-009A 부분 |
| V3.17 | **listed-shares DB 갱신** | **D** | **❌ HOLD-002** |
| V3.17 | shutdown 확인 | X | ❌ 미반영 |
| V3.17 | financial webcrawling | X | ✅ BP-004B |
| V3.17 | stock-info cleanup | (broker) | ❌ BP-003 hold |
| V3.17 | strategy syntax test pyd 분리 | PYD-EXCL | ❌ BP-012A no-op/hold |
| V3.17 | Upbit 첫 tick 수량 | (broker) | ❌ BP-003 hold |
| V3.18 | **risk min data 30** | **L** | **❌** (AnalyzerRisk 미연결로 무의미) |
| V3.18 | prange removal | L | ❌ HOLD-001 |
| V3.18 | 주문유형 guard | (broker) | ❌ BP-014A hold/excluded |
| V3.18 | 백테스트 손익 분석 load 이름 | B | ❌ BP-001 hold |
| V3.18 | 잔고 변경시만 저장 | D | ❌ HOLD-002 |
| V3.18 | **strategy-test dummy microstructure** | **L** | **❌ BP-013A hold** |
| V3.18 | strategy tab 아이콘 | U | ❌ 미반영 |

### 2.3 카테고리별 합산

| 카테고리 | 항목 수 (대략) | ✅ 반영 | ⚠️ 부분 | ❌ 미반영 |
|---|---|---|---|---|
| **L** 학습/분석 | ~35 | 0 | 1 (AnalyzerRisk dormant) | ~34 |
| **D** DB/학습 데이터 저장 | ~10 | 0 | 0 | ~10 |
| **B** 백테스트 학습 적용 | ~8 | 0 | 0 | ~8 |
| **R** 실시간 거래 학습 적용 | ~5 | 0 | 0 | ~5 |
| **U** UI/분석 화면 | ~25 | 4 | 5 | ~16 |
| **X** 의존성/유틸리티 | ~12 | 4 | 1 | ~7 |
| (broker) | ~20 | 1 (BP-010A) | 0 | ~19 |

→ **L/D/B/R 카테고리(사용자 본 요청 영역)는 합산 ~58개 중 1개(AnalyzerRisk dormant) 외 모두 미반영.**

---

## 3. 카테고리별 목표 분해

### 3.1 학습/분석 (L) 목표

```text
3.1.1  V3 strategy/ 7개 analyzer를 2U_C에 이식
       대상: candle_pattern, microstructure, risk, volatility_pattern,
            volatility_stop_take, volume_profile, volume_spike

3.1.2  manager_formula.py 이식 (V3.17 formula manager factors)

3.1.3  stg_globals_func.py 이식 (V3.09 globals 대문자)

3.1.4  V3.10 학습 누수 fix를 백테스트 학습 적용 시점에 반드시 포함

3.1.5  V3.14 학습 윈도우 (최근 30일) / V3.18 risk min data 30 등 학습 파라미터 반영

3.1.6  V3.16 confidence 계산 / V3.13 ranking order 등 분석 알고리즘 반영
```

**비목표(non-goals)**:
- V3 strategy/ 디렉터리 broad cherry-pick (Kiwoom data shape 비호환 위험)
- LS broker 의존 부분의 강제 포함

### 3.2 DB/학습 데이터 저장 (D) 목표

```text
3.2.1  V3 _database/ schema와 2U_C _database/ schema의 file 단위 diff 작성

3.2.2  V3 학습 데이터 저장 테이블/컬럼/PK/index 식별
       대상: 캔들 패턴, 거래량 프로파일, 거래량 스파이크,
            변동성 패턴, TP/SL, 시장미시구조, 리스크

3.2.3  V3.08 DB primary key migration 정책 채택

3.2.4  V3.08 거래소별 설정 분리 정책 채택

3.2.5  V3.11 INSERT OR REPLACE helper 채택

3.2.6  V3.07 시가총액 DB / V3.17 listed-shares DB 갱신 정책 채택

3.2.7  V3.18 잔고 변경시만 저장 정책 채택

3.2.8  shadow location에서 V3 호환 schema dry-run 검증

3.2.9  cutover 시 B-1 방식 적용:
       기존 _database/ → backup/_database_pre_v3k_<date>/
       V3 호환 schema로 _database/ 재생성
       runtime이 V3 호환 경로 사용
```

**비목표**:
- 기존 `_database/`의 in-place schema 변경 (반드시 backup 후 재생성)
- migration script 없는 즉시 cutover

### 3.3 백테스트 학습 적용 (B) 목표

```text
3.3.1  백테스트 일자 이전 학습 데이터만 read-only 로드 (V3.10 future-reference fix 핵심)

3.3.2  백테스트 일자 이후 학습 데이터 접근 시 RaiseError로 누수 자동 차단

3.3.3  feature flag OFF 시 기존 백테스트 결과와 100% 동일 (regression 0건)

3.3.4  feature flag ON 시 학습 데이터 로드 evidence 출력 + 결과 차이 측정

3.3.5  V3.10 code-test 분석 변수 / V3.14 backengine 1m indicator / V3.18 손익 분석 load 이름 정책 반영

3.3.6  2U_C B/S/R custom backtest 구조와 V3 학습 적용 hook을 어댑터로 결합
```

**비목표**:
- 2U_C B/S/R custom backtest 엔진의 broad replace
- V3.02~V3.18 backtest 구조 broad merge (BP-001 hold 사유 그대로 유지)

### 3.4 실시간 거래 학습 적용 (R) 목표

```text
3.4.1  Kiwoom 실시간 거래 메인 흐름 비침투 (sidecar/advisory queue 패턴)

3.4.2  V3.10/3.11 1초 스냅샷 분석을 sidecar QThread로 실행

3.4.3  V3.11 실시간 학습 데이터 로드 = sidecar에서 read-only

3.4.4  feature flag OFF 시 기존 실시간 거래와 동작 100% 동일

3.4.5  feature flag ON 시 advisory만 활성화, 실거래 주문 경로 변경 없음

3.4.6  V3.06 실시간 필터 / V3.07 시장 개시 predata 정책 반영
```

**비목표**:
- 메인 거래 결정 함수의 broad replace
- Kiwoom Open API 호출 빈도 증가 (rate limit 보호)
- 실거래 주문 경로 변경 (Phase 7 통과 전 절대 금지)

### 3.5 UI/분석 화면 (U) 목표

```text
3.5.1  분석 dialog를 별도 창으로 구현 (MainWindow 비침투)

3.5.2  V3.12 레이더 차트 위젯을 dialog 내부에 배치

3.5.3  V3.15 분석 default settings를 별도 _learning_settings.json 파일에 저장

3.5.4  V3.15/3.16 분석 progressbar는 dialog 내부에서만 사용

3.5.5  V3.07/3.12 chart factor settings는 dialog의 settings 탭에 통합

3.5.6  pyd MainWindow / pyd wrapper 계약 변경 0건
```

**비목표**:
- pyd MainWindow rename/split (PYD-EXCL)
- 기존 MainWindow 메뉴 구조 재배치

### 3.6 의존성/유틸리티 (X) 보정

이미 BP-007A/008A/011A로 timezone, BP-004A로 ANSI escape, BP-004B로 financial webcrawling이 반영됨. V3K-DESIGN-0 단계에서는 다음 잔여 항목만 식별한다.

```text
3.6.1  V3.0 telegram screenshot 응답 (사용자 결정 필요)
3.6.2  V3.04 shutdown 60초 (사용자 결정 필요)
3.6.3  V3.08 sound queue thread / pyttsx 다운그레이드 (process 경계 변경 위험)
3.6.4  V3.13 날짜 변경 ignore (백테스트 영향 가능)
3.6.5  V3.17 shutdown 확인 (broad)
```

이 항목들은 V3K-IMPL Phase 진입 후 별도 micro-candidate로 검토.

---

## 4. 2U_C Kiwoom data shape mapping 항목 정의

### 4.1 V3 vs Kiwoom data shape 충돌 가능 영역

V3는 LS REST API의 tick/min payload를 가정한다. 2U_C는 Kiwoom Open API (OPT10001/10004 외) 기반이다. V3K-DESIGN-1 이후 단계에서 다음 mapping 항목을 file 단위 명세로 작성해야 한다.

| Mapping ID | V3 입력 | Kiwoom 입력 | 변환 필요성 |
|---|---|---|---|
| `MAP-T1` | LS tick payload (column 순서/이름) | OPT10004 / 실시간 체결 | 컬럼 rename + 순서 정렬 |
| `MAP-T2` | LS tick timestamp (UTC/KST 가정) | Kiwoom KST 고정 | tz 검증, 정수 epoch 변환 |
| `MAP-M1` | LS min candle payload | Kiwoom min candle (TR / 실시간 합성) | 컬럼 정렬, NULL 처리 |
| `MAP-M2` | LS min timestamp | Kiwoom min timestamp | KST 통일 |
| `MAP-H1` | LS 호가 잔량 L1~L10 | Kiwoom 호가 L1~L10 | 잔량 단위 검증 |
| `MAP-V1` | LS 거래량 단위 | Kiwoom 거래량 단위 | 정수 vs 부동소수 검증 |
| `MAP-S1` | 시장 시간 (24h coin / 09:00 stock) | 동일 | (확인만) |
| `MAP-C1` | 종목코드 형식 | Kiwoom 종목코드 형식 | prefix/suffix 검증 |
| `MAP-A1` | 계좌번호 / 주문 식별자 | Kiwoom 계좌/주문 ID | runtime wiring 필요 시점에만 |
| `MAP-F1` | financial 정보 (V3.17) | Kiwoom 재무정보 | BP-004B 기존 + 추가 항목 검토 |

### 4.2 mapping 산출물 형식

각 `MAP-*`는 V3K-DESIGN-2 단계에서 다음 4가지를 갖춘 명세로 만든다.

```text
1. V3 input schema 예시 (실제 V3 코드 발췌)
2. Kiwoom input schema 예시 (실제 Kiwoom payload 캡처)
3. 어댑터 함수 시그니처
4. fixture 3종 (정상 / 결측 / 이상치)
```

### 4.3 fixture 정책

```text
fixture/
  v3k/
    tick_normal.json
    tick_missing.json
    tick_outlier.json
    min_normal.json
    min_missing.json
    min_outlier.json
    hoga_normal.json
    hoga_missing.json
```

→ Kiwoom 실거래 캡처 1회 필요 (live 환경 또는 paper trading). Phase 0에서는 캡처 권한/방법만 확정.

---

## 5. DB Migration spec 목차

### 5.1 V3K-DESIGN-1에서 작성할 산출물 목차

```text
docs/superpowers/specs/2026-05-XX-v3k-db-migration-spec.md
  1. 목적과 종료 조건
  2. 기준 lane / HEAD / sample DB 출처
  3. V3 _database/ schema 전체 목록 (file → table → column → PK)
  4. 2U_C _database/ schema 전체 목록 (동일 형식)
  5. diff 분류표
     5.1 V3 신규 테이블 (학습 데이터 저장 위주)
     5.2 V3 컬럼 추가
     5.3 V3 PK 변경
     5.4 V3 거래소별 분리
     5.5 2U_C 보존 필요 항목 (Kiwoom-only)
  6. shadow DB 설계
     6.1 shadow location: _database_v3k_shadow/
     6.2 dry-run script: scripts/init_v3k_shadow_db.py
     6.3 healthcheck: scripts/v3k_db_health.py
  7. migration script 설계
     7.1 신규 테이블 생성 SQL
     7.2 기존 데이터 변환 규칙 (선택적, 데이터 보존이 필요한 경우)
     7.3 INSERT OR REPLACE helper 적용 범위
  8. backup 정책
     8.1 backup location: backup/_database_pre_v3k_<YYYYMMDD-HHMM>/
     8.2 backup 시점: cutover 직전
     8.3 backup 검증: 파일 크기, 해시, sample query
  9. cutover 절차 (B-1 방식)
     9.1 전제 조건: V3K-VERIFY-1 통과
     9.2 cutover step:
         a. 사용자 명시 승인
         b. 거래/백테스트 runtime 정지 확인
         c. _database/ → backup/_database_pre_v3k_<date>/ 이동
         d. _database_v3k_shadow/ → _database/ 이동 (또는 재생성)
         e. healthcheck 통과
         f. 서비스 재개
     9.3 cutover 소요 시간 추정
  10. rollback 절차
     10.1 cutover 실패 시 즉시 rollback
     10.2 rollback step:
         a. 거래/백테스트 정지
         b. _database/ 제거
         c. backup/_database_pre_v3k_<date>/ → _database/ 복원
         d. healthcheck 통과
         e. 서비스 재개
  11. forbidden artifact guard
     - _database, _database_v3k_shadow, backup/_database_pre_v3k_*는 git tracked 금지
     - .gitignore에 추가
  12. 검증 명령
     - python scripts/init_v3k_shadow_db.py --dry-run
     - python scripts/v3k_db_health.py
     - python scripts/diff_v3_vs_2uc_db_schema.py
```

### 5.2 DB B-1 방식의 책임 분담

| 단계 | 행위자 | 행동 |
|---|---|---|
| Phase 1 (DESIGN-1) | Claude/사용자 | spec 작성, dry-run 검증, 코드 commit 0건 |
| Phase 7 (VERIFY-1) | Claude/사용자 | rehearsal 환경에서 backup → cutover → rollback 1회 검증 |
| Cutover 본 실행 | **사용자만** | 명시 승인 + 거래/백테스트 정지 확인 |

→ **cutover 실행은 절대 자동화하지 않음. 사용자 명시 승인 필수.**

---

## 6. Feature flag 정책

### 6.1 정의

V3K 트랙은 **2개의 feature flag**로 학습 시스템 활성화를 제어한다.

```text
V3K_BACKTEST_LEARNING_ENABLED   (default: False)
V3K_REALTIME_LEARNING_ENABLED   (default: False)
```

### 6.2 위치

```text
설정 파일: settings.json (또는 _learning_settings.json)
환경 변수 override: V3K_BACKTEST_LEARNING=1, V3K_REALTIME_LEARNING=1
```

코드 레벨 위치는 V3K-IMPL-1에서 결정 (예: `utility/v3k_flags.py`).

### 6.3 flag별 영향 매트릭스

| 상태 | 백테스트 | 실시간 거래 | 분석 dialog | DB 경로 |
|---|---|---|---|---|
| BACKTEST=OFF, REALTIME=OFF | 기존 동작 100% 동일 | 기존 동작 100% 동일 | dialog 열기 가능, 학습 데이터는 read-only display | 기존 `_database/` |
| BACKTEST=ON, REALTIME=OFF | 학습 데이터 로드 (이전 일자만) | 기존 동작 100% 동일 | 동일 | V3 호환 경로 (cutover 후) |
| BACKTEST=OFF, REALTIME=ON | 기존 백테스트 동작 | sidecar advisory 활성 (주문 경로 변경 없음) | 동일 | V3 호환 경로 |
| BACKTEST=ON, REALTIME=ON | 학습 적용 | sidecar advisory 활성 | 동일 | V3 호환 경로 |

### 6.4 flag 진입 조건

```text
V3K_BACKTEST_LEARNING_ENABLED=True 가능 시점:
  - V3K-IMPL-3 통과 후
  - regression 검증 결과 OFF/ON 차이 명세 통과

V3K_REALTIME_LEARNING_ENABLED=True 가능 시점:
  - V3K-IMPL-4 통과 후
  - paper trading 24h 회귀 통과
  - 사용자 명시 승인
```

### 6.5 flag UI 표시

flag가 ON일 때 사용자에게 **MainWindow 상단 또는 시스템 로그**에 명시적으로 표시한다.

```text
[V3K] backtest learning: ON (loaded 2026-05-08T14:00:00)
[V3K] realtime learning: ON (sidecar PID 12345)
```

→ 의도하지 않은 활성화로 인한 사고 방지.

---

## 7. 2U_C Mirror 정책

### 7.1 propagation chain 원칙 (CLAUDE.md 기준)

```text
V2 root  →  2U  →  2U_C
```

본 V3K 트랙도 이 chain을 따른다. 다만 단계별로 mirror 시점이 다르다.

### 7.2 단계별 mirror 시점

| 단계 | V2 root | 2U mirror | 2U_C mirror |
|---|---|---|---|
| **V3K-DESIGN-0** (이 문서) | ✅ 작성 | ⏳ 대기 (이번 단계 종료 후) | ⏳ 대기 |
| **V3K-DESIGN-1 ~ 2** (DB/analyzer 설계) | 작성 | mirror | mirror |
| **V3K-IMPL-2A ~ 2G** (analyzer 구현) | 문서만 | 문서만 | **실제 코드 적용 lane** |
| **V3K-IMPL-3** (백테스트 학습) | 문서만 | 문서만 | **실제 코드 적용 lane** |
| **V3K-IMPL-4** (실시간 학습) | 문서만 | 문서만 | **실제 코드 적용 lane** |
| **V3K-IMPL-5** (UI) | 문서만 | 문서만 | **실제 코드 적용 lane** |
| **V3K-VERIFY-1** | 검증 보고 | mirror | **실제 검증 lane** |
| **Cutover** | 승인 commit | mirror | **실제 cutover lane** |

→ **V3K-IMPL 단계의 코드 변경은 2U_C에서만 일어난다. V2 root와 2U는 문서 mirror만 받는다.**

### 7.3 2U_C에 남아있는 잔여 처리

| 항목 | 처리 |
|---|---|
| 2U_C에 untracked 상태인 구버전 audit 문서 (94d92787 이전 버전) | V3K-DESIGN-0 통과 후 V2 root 최신본을 동일 lane에 복사하여 mirror commit |
| 2U_C BP-002A~011A 12개 코드 commit | V3K 트랙에서도 그대로 활용. 별도 처리 없음 |

### 7.4 V2 root에 V3K-DESIGN-0 후속 commit 권장 메시지

```text
V3K Phase 0 사전 설계 kickoff을 고정한다
```

(설명 본문은 본 문서 §1과 §2 요약)

---

## 8. 다음 단계: V3K-DESIGN-1 진입 조건

### 8.1 V3K-DESIGN-1 시작 가능 조건

| 조건 | 상태 |
|---|---|
| 본 문서 (V3K-DESIGN-0) 사용자 검토 통과 | ⏳ 대기 |
| V2 root commit 완료 | ⏳ 대기 |
| 2U/2U_C mirror 정책 확정 (§7) | ✅ 본 문서에 고정 |
| DB B-1 방식 명시 승인 | ✅ 사용자 답변 완료 |
| V3 / 2U_C / V3U lane HEAD 확인 | ✅ 본 문서 메타에 기록 |

### 8.2 V3K-DESIGN-1 산출물 (예정)

```text
docs/superpowers/specs/2026-05-XX-v3k-db-migration-spec.md
docs/update_log/2026-05-XX_v3k_design_1_db_design.md
scripts/diff_v3_vs_2uc_db_schema.py (사용자 검토 후 작성)
scripts/init_v3k_shadow_db.py (사용자 검토 후 작성)
scripts/v3k_db_health.py (사용자 검토 후 작성)
```

V3K-DESIGN-1은 dry-run script까지만 작성하며, 실제 DB 변경은 0건.

### 8.3 V3K-DESIGN-2 산출물 (예정)

```text
docs/superpowers/specs/2026-05-XX-v3k-analyzer-contracts.md
fixture/v3k/*.json (정상/결측/이상치 ≥ 9개)
docs/update_log/2026-05-XX_v3k_design_2_analyzer_contracts.md
```

---

## 9. 위험 매트릭스 (Phase 0 인지 단계)

본 매트릭스는 Phase 0에서 인지하고 후속 Phase의 mitigation에 반영할 위험들이다.

| 위험 ID | 영역 | 설명 | mitigation Phase |
|---|---|---|---|
| `RISK-DS-1` | data shape | Kiwoom tick payload ≠ V3 LS tick payload (컬럼 순서/이름) | DESIGN-2 어댑터 |
| `RISK-DS-2` | data shape | timestamp tz 가정 차이 | DESIGN-2 |
| `RISK-DS-3` | data shape | 거래량/잔량 단위 차이 | DESIGN-2 |
| `RISK-DB-1` | DB | V3.08 PK migration이 기존 데이터와 충돌 | DESIGN-1 + VERIFY |
| `RISK-DB-2` | DB | 기존 `_database/` 손상 사고 | DESIGN-1 backup 정책 |
| `RISK-DB-3` | DB | shadow 단계에서 fault → cutover 미진행 | rollback rehearsal |
| `RISK-LK-1` | 학습 누수 | 백테스트가 백테스트 일자 이후 데이터 참조 | IMPL-3 RaiseError guard |
| `RISK-LK-2` | 학습 누수 | sidecar가 실시간 거래에 미래 정보 사용 | IMPL-4 read-only 보장 |
| `RISK-FL-1` | feature flag | flag 누락으로 의도하지 않은 활성화 | IMPL-1 default OFF + UI 표시 |
| `RISK-DB-4` | DB | Kiwoom rate limit 초과 (sidecar가 API 호출 시) | IMPL-4 sidecar는 DB read만, API 호출 금지 |
| `RISK-RT-1` | runtime | 메인 거래 latency 증가 | IMPL-4 advisory queue 비차단 |
| `RISK-PYD-1` | pyd | MainWindow 계약 충돌 | IMPL-5 별도 dialog |
| `RISK-NB-1` | numba/talib | 의존성 충돌 / 빌드 실패 | DESIGN-2에서 사전 확인 |
| `RISK-PR-1` | 운영 | micro-candidate 원칙 위배로 인한 일관성 손상 | V3K 트랙 명시 분리 |
| `RISK-CO-1` | cutover | 실수로 자동 cutover 발생 | DESIGN-1 §5.2 사용자 승인 필수 |

---

## 10. 검증 체크리스트 (Phase 0 종료 시점)

```text
[ ] §2 V3.0~V3.18 inventory에 LS-EXCL/PYD-EXCL을 제외한 모든 update.txt 항목이 카테고리화됨
[ ] §3 6개 카테고리별 목표 분해가 모두 명세됨
[ ] §3 각 카테고리에 비목표(non-goals)가 명세됨
[ ] §4 Kiwoom data shape mapping이 ≥10개 ID로 표기됨
[ ] §4 fixture 정책 명세
[ ] §5 DB migration spec 목차 12개 섹션 명세
[ ] §5.2 DB cutover 책임 분담 명시 (사용자 승인 필수)
[ ] §6 feature flag 2개 정의 + 영향 매트릭스 4가지
[ ] §6.4 flag 진입 조건 명세
[ ] §7 V2/2U/2U_C mirror 정책 명세
[ ] §8 V3K-DESIGN-1 진입 조건 명세
[ ] §9 위험 매트릭스 ≥15개 ID
[ ] runtime 코드 변경 0건 확인 (`git diff --stat HEAD~ docs/update_log/2026-05-08_v3k_phase0_design_kickoff.md` 외 0)
```

---

## 11. 참조 문서

| 역할 | 경로 |
|---|---|
| V3K 목표 정의 | `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md` |
| V3K 검증 baseline | `docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md` |
| 기존 closure (재해석 대상) | `docs/update_log/2026-05-08_v3_2uc_final_closure_audit.md` |
| Carry-forward registry | `docs/CARRY_FORWARD_REGISTRY.md` (§ Goal reset 추가됨) |
| Allowlist plan (legacy + V3K 보정) | `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md` (§43 추가됨) |
| Worktree map | `docs/WORKTREE_STRATEGY.md` |
| AGENTS entry point | `AGENTS.md` (V3K 안내 추가됨) |

---

## 12. 한 줄 결론

`V3K-DESIGN-0`은 V3.0~V3.18의 LS 제외 신기능을 6개 카테고리(L/D/B/R/U/X)로 재분류하고, 카테고리별 목표/Kiwoom data shape mapping/DB migration spec 목차/feature flag 정책/2U_C mirror 정책을 고정한 사전 설계 문서이다. 본 문서 통과 후 `V3K-DESIGN-1` (DB/학습 데이터 설계)로 진입한다. 코드 변경은 V3K-IMPL Phase에서만 발생하며, cutover는 사용자 명시 승인이 있을 때만 실행한다.
