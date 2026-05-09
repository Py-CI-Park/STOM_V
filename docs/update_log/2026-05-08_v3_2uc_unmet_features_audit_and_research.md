# V3 → 2U_C 미반영 신기능 검증과 달성 방법 연구

**작성일**: 2026-05-08 KST
**대상 lane**: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
**작성 성격**: read-only audit + 향후 작업 설계 연구 (code 변경 없음)
**기준 HEAD**:

| lane | branch | HEAD |
|---|---|---|
| root | `STOM_Version_2` | `81cd732f 백포트 종료 상태를 재확인한다` |
| 2U_C | `STOM_Version_2U_C` | `090421c1 백포트 종료 상태 재확인을 2U_C에 미러링한다` |
| V3 | `STOM_Version_3` | `7faec937 STOM V3.18` |

---

> 2026-05-08 목표 보정: 이 문서는 `V3K 완전 기능 이행 목표 재정의 및 실행 계획`(`docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`)과 함께 읽는다. 본 문서의 `no-more-safe-candidates` 해석은 “safe micro-candidate 종료”일 뿐이며, “V3의 LS증권 제외 신기능 전체가 2U_C에 반영 완료”라는 뜻이 아니다. 향후 목표는 `V3K = V3 기능 + Kiwoom 유지`로 재정의한다.
>
> 명칭 보정: 기존 초안의 `DESIGN-LS` / `LS-IMPL`은 `LS증권`과 혼동되므로 폐기하고, 이후에는 `V3K-DESIGN` / `V3K-IMPL`을 사용한다.

## 1. Executive Summary (결론 먼저)

### 1.1 검증 결론

**❌ V3의 LS증권 변경을 제외한 신기능이 2U_C에 모두 반영되지는 않았다.**

문서가 표기하는 "V3 → 2U_C 100.0% closure"는 **"안전 기준을 통과한 micro-candidate 100% 처리"**라는 의미이며, **"V3 신기능 100% 반영"**이 아니다. 사용자가 묻는 핵심 영역(데이터 학습, 백테스트의 학습 데이터 사용, 실시간 거래의 학습 데이터 사용)은 **거의 전부 HOLD/EXCLUDED 상태**로 닫혀 있다.

### 1.2 무엇이 반영되었는가 (broker/DB/pyd-neutral 표면 보정 11건)

| 영역 | BP-ID | code commit |
|---|---|---|
| 차트 봉 폭 보정 | BP-002A | `f2f447d1` |
| DB차트 상태 초기화 | BP-002B | `76329b3b` |
| ANSI escape 제거 | BP-004A | `e204e0f3` |
| 재무정보 숫자 파싱 | BP-004B | `944bab37` |
| progressbar 표시 보정 | BP-005A | `f942ed2f` |
| AnalyzerRisk dormant 보존 | BP-006A | `15467b43`, `0ea00ea4` |
| timesync stdlib 전환 | BP-007A | `61e12951` |
| static.py timezone 전환 | BP-008A | `6e4c10a0` |
| crosshair 표시 경계 | BP-009A | `f791c54a` |
| moneytop 리스트 초기화 | BP-009B | `cd35395f` |
| Binance websocket non-data guard | BP-010A | `41a09d76` |
| telegram timezone + 의존성 정리 | BP-011A | `59ffaafc` |

→ 총 **12건 code commit, 모두 표면 버그 fix 또는 의존성 정리 수준**이며 V3의 핵심 차별점을 구성하는 학습/분석 기능과는 무관하다.

### 1.3 무엇이 반영되지 않았는가 (V3의 진짜 가치)

| V3 신기능 | V3 출처 | 2U_C 상태 | 사유 |
|---|---|---|---|
| 캔들 패턴 학습 분석기 | V3.04, V3.05 | **❌ 파일조차 없음** | HOLD-001 |
| 거래량 프로파일 학습 분석기 | V3.05 | **❌ 파일조차 없음** | HOLD-001 |
| 거래량 스파이크 학습 분석기 | V3.09 | **❌ 파일조차 없음** | HOLD-001 |
| 변동성 패턴 학습 분석기 | V3.13 | **❌ 파일조차 없음** | HOLD-001 |
| TP/SL (변손익) 학습 분석기 | V3.13 | **❌ 파일조차 없음** | HOLD-001 |
| 시장미시구조 분석기 + 레이더차트 | V3.05, V3.12 | **❌ 파일조차 없음** | HOLD-001 |
| 리스크 학습 분석기 | V3.14 | ⚠️ 파일만 보존, **runtime 미연결** | BP-006A dormant |
| 수식 관리자 (`manager_formula.py`) | V3.09, V3.17 | **❌ 파일조차 없음** | HOLD-001 |
| 전략 글로벌 함수 (`stg_globals_func.py`) | V3.09 | **❌ 파일조차 없음** | HOLD-001 |
| **백테스트가 학습 데이터를 백테스트 일자 이전 기준으로 로드** | V3.10 (`_update.txt` 명시) | **❌ 미반영** | BP-001 hold + HOLD-001 |
| **실시간 매매가 학습 데이터를 로드** | V3.11 (`_update.txt` 명시) | **❌ 미반영** | HOLD-001 |
| DB 관리 후 자동 학습 | V3.10 | **❌ 미반영** | HOLD-001 + HOLD-002 |
| 1초 스냅샷 분석 | V3.10, V3.11 | **❌ 미반영** | HOLD-001 |
| 거래소별 설정 분리 / DB primary key / INSERT OR REPLACE | V3.08, V3.11 | **❌ 미반영** | HOLD-002 |
| 백테스트 엔진 시장별 폴더화 / 학습 적용 구조 | V3.02~V3.18 (broad) | **❌ 미반영** | BP-001 hold |
| 분석 시스템 settings/UI/radar chart | V3.05~V3.18 | **❌ 미반영** | HOLD-001 |

### 1.4 핵심 통계

```text
V3 strategy/ 모듈 9개  → 2U_C는 1개만 (analyzer_risk dormant)  = 11.1%
V3 학습 시스템 runtime 연결                                     = 0%
V3 학습 데이터 DB 저장/로딩                                     = 0%
V3 백테스트 학습 데이터 사전 로드                              = 0%
V3 실시간 거래 학습 데이터 로드                                 = 0%
```

**`backtest/`, `trade/` 어느 파일도 `strategy.analyzer_*` 또는 `from strategy`를 import하지 않음 (검증 명령: `grep -c "import.*analyzer\|from strategy" backtest/*.py trade/*.py` → 0건).** 이는 단순 파일 부재가 아니라 **runtime 호출 경로 자체가 존재하지 않음**을 의미한다.

### 1.5 정리

> **현재 2U_C는 "V2.77 Kiwoom 기반 + V3에서 가져온 표면 버그 보정 12건"이며, V3의 학습/분석 시스템은 단 한 줄도 작동하지 않는다.**
>
> 이 상태가 **잘못된 것은 아니다.** 운영 문서(`docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`)가 정한 안전 원칙이 학습 시스템 진입을 차단하기 때문이다. 그러나 사용자의 본 질문 "V3 신기능이 2U_C에 모두 반영되었나"의 답은 **명확히 NO이며, 이를 달성하려면 별도 설계 트랙이 필요하다.**

---

## 2. 검증 방법론

이번 audit은 다음 4단계 증거 수집으로 진행했다.

### 2.1 파일 시스템 비교

```powershell
# V3 strategy/ 디렉터리
ls C:/System_Trading/STOM/STOM_V.wt-3/strategy/

# 2U_C strategy/ 디렉터리
ls C:/System_Trading/STOM/STOM_V.wt-dev/strategy/
```

V3에 존재하지만 2U_C에 부재한 모듈 8개를 확정.

### 2.2 Runtime wiring 검사

```powershell
grep -c "import.*analyzer|from strategy" backtest/*.py trade/*.py
```

→ 결과: **모든 파일에서 0건**. 학습 모듈을 호출하는 runtime 경로가 존재하지 않음을 증명.

### 2.3 운영 문서 추적

다음 문서들을 정독했다.

- `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md` (allowlist + Phase 11 결정)
- `docs/update_log/2026-05-07_v3_2uc_candidate_inventory.md` (V3.0~V3.18 전체 inventory)
- `docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md`
- `docs/update_log/2026-05-08_v3_2uc_residual_batch_scan.md` (BP-009C ~ BP-014A batch)
- `docs/update_log/2026-05-08_v3_2uc_final_closure_audit.md`
- `docs/CARRY_FORWARD_REGISTRY.md`

### 2.4 Git 이력 추적

```powershell
git log --oneline -25 STOM_Version_2U_C
git log --all --oneline -- "strategy/analyzer_*.py"
```

→ `strategy/analyzer_*.py`에 닿은 commit은 BP-006A (`15467b43`, `0ea00ea4`) 단 2건이며 모두 dormant 보존이다. V3 commit `7faec937` 이전의 V3 학습 모듈 발전 이력은 2U_C에 전혀 반영되지 않았다.

---

## 3. V3 신기능 반영 매트릭스 (LS증권 제외, 상세)

다음 표는 V3.0~V3.18 `_update.txt`의 항목을 broker/DB/pyd-neutral 관점에서 분류하고 2U_C 반영 여부를 표시한다. **"LS증권 직접 변경"은 사용자 요청에 따라 제외**했다.

### 3.1 V3.0 ~ V3.05

| V3 항목 | 영역 | 2U_C | 사유 |
|---|---|---|---|
| Python 3.13 호환 | 환경 | ⚠️ 부분 (V3.13 호환 dependency만) | broad 변경 hold |
| Mainwindow 함수 파일 분리 | pyd/UI | ❌ | pyd broad merge 제외 |
| AI agent rules 추가 | docs | ❌ (필요시 별도 후보) | 운영 문서 분리 |
| VI 등록/수신 처리 | trade | ❌ | LS receiver 구조와 묶임 |
| Binance precision 보정 | trade | ❌ | BP-003 hold (broad) |
| 상장주식수 조회 갱신 | trade/DB | ❌ | DB 영향 |
| Binance websocket queue size | trade | ❌ | BP-003 hold |
| 백테스트 unpack/load/resource | backtest | ❌ | BP-001 hold |
| BinanceWebSocket cleanup | trade | ⚠️ BP-010A 부분 (1줄) | 잔여 broad hold |
| 실시간 차트 index mismatch | UI | ⚠️ BP-002A/009A 부분 | 잔여 hold |
| 실시간 차트 x축 보정 | UI | ❌ BP-002C hold | rolling window evidence 필요 |
| crosshair 중복 | UI | ✅ 2U_C 기존 보유 | no-op |
| DB chart arg / arrow | UI | ⚠️ BP-002B 부분 | arrow 음수화 hold |
| 이미지 webcrawling 예외 | utility | ⚠️ BP-004A 부분 | broad 미반영 |
| 백테스트 로딩 버그 (V3.04) | backtest | ❌ | BP-001 hold |
| 종료 60초 처리 | runtime | ❌ | shutdown 흐름 broad |
| receiver overhead | trade | ❌ | BP-003 hold |
| 고DPI font | UI | ❌ | 재현 evidence 필요 |
| 시가총액 단위 보정 | trade | ❌ | DB save broad |
| **talib 패턴 학습 (V3.04)** | **strategy** | **❌ HOLD-001** | **학습 시스템 진입 차단** |
| **패턴 학습 멀티 카운트 (V3.05)** | **strategy** | **❌ HOLD-001** | **학습 시스템 진입 차단** |
| UI circular import 차단 | pyd | ❌ | pyd 계약 충돌 |
| **거래량 프로파일 분석기 추가 (V3.05)** | **strategy** | **❌ HOLD-001** | **분석기 신규 모듈 미이식** |

### 3.2 V3.06 ~ V3.10

| V3 항목 | 영역 | 2U_C | 사유 |
|---|---|---|---|
| 실시간 필터 | trade | ❌ | receiver broad |
| receiver stop hang | trade | ❌ | BP-003 hold |
| 차트 호가 sound 거래소 갱신 | utility | ❌ BP-004C no-op | payload 계약 차이 |
| settings lock | runtime | ❌ | settings broad |
| DB 관리 로그 정책 | DB | ❌ | HOLD-002 |
| 시가총액 등록 제외 | DB | ❌ | HOLD-002 |
| login tab 전환 | UI | ❌ | UI broad |
| chart moneytop 보정 (V3.07) | UI | ⚠️ BP-009B 부분 (table clear만) | time normalization hold |
| coin hoga after close | trade | ❌ | broker matrix 필요 |
| 시장 개시 predata | trade | ❌ | broker broad |
| timeframe factor list | strategy/UI | ❌ | HOLD-001 |
| DB chart 간소화 | UI | ⚠️ 부분 | broad hold |
| dialog close list | UI | ❌ | dialog 생애주기 broad |
| 시가총액 DB 저장 | DB | ❌ | HOLD-002 |
| 체결/호가 시간 자릿수 | trade | ❌ | broker broad |
| settings lock dialog 위치 | UI | ❌ | settings broad |
| 차트 `is_min` (V3.08) | UI | ❌ | UI broad |
| **DB primary key migration (V3.08)** | **DB** | **❌ HOLD-002** | **DB 비호환 위험** |
| **거래소별 설정 분리 (V3.08)** | **DB** | **❌ HOLD-002** | **DB 비호환 위험** |
| Upbit 주문 websocket | trade | ❌ | BP-003 hold |
| error decorator | utility | ❌ | broad |
| Alt+X 단축키 | UI | ❌ | UI 후보 |
| sound queue thread | utility | ❌ | process 경계 변경 |
| pyttsx 다운그레이드 | dependency | ❌ | runtime 영향 |
| **시장 정보 dict cleanup (V3.09)** | **runtime** | **❌** | **broad** |
| REST 간소화 | trade | ❌ | LS 묶임 |
| **strategy 폴더 이동 (V3.09)** | **strategy** | **❌ HOLD-001** | **strategy 폴더 broad 변경** |
| globals 대문자 | strategy | ❌ | HOLD-001 묶음 |
| pyd rename | pyd | ❌ | pyd broad |
| window position | UI | ❌ | 후보 |
| path refs | runtime | ❌ | broad |
| **변동성/거래량 스파이크 분석 (V3.09)** | **strategy** | **❌ HOLD-001** | **신규 분석기 미이식** |
| **DB order alignment (V3.09)** | **DB** | **❌ HOLD-002** | **DB schema** |
| **분석 backengine/strategy 적용 (V3.09)** | **strategy + backtest** | **❌ HOLD-001 + BP-001** | **학습 적용 핵심 변경** |
| **분석 학습 future-reference fix (V3.10)** | **strategy** | **❌ HOLD-001** | **학습 누수 fix 미반영** |
| **DB 관리 후 자동 학습 (V3.10)** | **strategy + DB** | **❌ HOLD-001 + HOLD-002** | **자동 학습 trigger** |
| **1초 스냅샷 분석 (V3.10)** | **strategy** | **❌ HOLD-001** | **스냅샷 분석 신규** |
| code-test 분석 변수 (V3.10) | backtest | ❌ | BP-001 hold |

### 3.3 V3.11 ~ V3.15

| V3 항목 | 영역 | 2U_C | 사유 |
|---|---|---|---|
| **첫 캔들 수량 fix (V3.11)** | **strategy** | **❌ HOLD-001** | **학습 데이터 정합성 fix** |
| **스냅샷 분석 확장 (V3.11)** | **strategy** | **❌ HOLD-001** | **스냅샷 확장** |
| risk data cleanup | strategy | ❌ HOLD-001 | runtime wiring 필요 |
| risk 1m | strategy | ❌ HOLD-001 | runtime wiring 필요 |
| pytz/dateutil/tzlocal 삭제 | dependency | ✅ BP-007A/008A/011A | 완료 |
| mock trading API skip | trade | ❌ | broker 묶임 |
| **INSERT OR REPLACE helper (V3.11)** | **DB** | **❌ HOLD-002** | **DB primitive** |
| analysis 메시지 | UI | ❌ HOLD-001 묶음 |
| crosshair zValue (V3.12) | UI | ✅ BP-009A | 완료 |
| prange | strategy | ❌ HOLD-001 | runtime |
| 단일 strategy 로그 process | strategy | ❌ HOLD-001 |
| get_optistd 속도 | backtest | ❌ BP-001 hold |
| **레이더 차트 (V3.12)** | **strategy + UI** | **❌ HOLD-001** | **분석 UI broad** |
| rank filter | strategy | ❌ HOLD-001 |
| training 속도/chart funcs | strategy | ❌ HOLD-001 |
| coin receiver cleanup | trade | ❌ BP-003 hold |
| **분석 chart/factor settings (V3.12)** | **strategy + UI** | **❌ HOLD-001** |
| 레이더 close guard | UI | ❌ | radar 묶음 |
| Binance non-stream guard (V3.12) | trade | ✅ BP-010A | 완료 |
| strategy 모듈 docs | docs | ❌ | 후보 |
| filename 단축 (V3.13) | strategy | ❌ HOLD-001 |
| snapshot date 추출 | strategy | ❌ HOLD-001 |
| ranking order | strategy | ❌ HOLD-001 |
| 변동성 속도 | strategy | ❌ HOLD-001 |
| volume settings 삭제 | strategy/UI | ❌ HOLD-001 |
| **TP/SL 분석 (V3.13)** | **strategy** | **❌ HOLD-001** | **변손익 학습 분석기** |
| 날짜 변경 ignore | runtime | ❌ broad |
| strategy variable rename (V3.14) | strategy | ❌ HOLD-001 |
| **최근 30일 학습 (V3.14)** | **strategy** | **❌ HOLD-001** | **학습 윈도우** |
| backengine 1m indicator | backtest | ❌ BP-001 hold |
| checkbox load 간소화 | UI | ❌ | 후보 |
| numba 최적화 | strategy | ❌ HOLD-001 |
| **AnalyzerRisk (V3.14)** | **strategy** | **⚠️ BP-006A dormant** | **파일 보존만, runtime 미연결** |
| 변동성 변화 레벨 | strategy | ❌ HOLD-001 |
| VI 캔들 width | UI | ❌ | 후보 |
| **변동성 분류 DB reset (V3.15)** | **DB** | **❌ HOLD-002** | **DB schema 영향** |
| 손익 최근 월 | strategy | ❌ HOLD-001 |
| numba | strategy | ❌ HOLD-001 |
| **분석 최적화 (V3.15)** | **strategy** | **❌ HOLD-001** |
| BounceButton | UI | ✅ 2U_C 기존 보유 | no-op |
| **분석 default settings (V3.15)** | **strategy/UI** | **❌ HOLD-001** |
| **분석 progressbar (V3.15)** | **UI** | **⚠️ 일반 progressbar만 BP-005A** | **분석 progressbar 별도 hold** |

### 3.4 V3.16 ~ V3.18

| V3 항목 | 영역 | 2U_C | 사유 |
|---|---|---|---|
| 최소 캔들 수 (V3.16) | strategy | ❌ HOLD-001 |
| numba/prange | strategy | ❌ HOLD-001 |
| confidence 계산 | strategy | ❌ HOLD-001 |
| 손익 confidence | strategy | ❌ HOLD-001 |
| 선물 주문 오류 | trade | ❌ BP-003 hold |
| **분석 progressbar 간소화 (V3.16)** | **UI** | **❌ HOLD-001 묶음** |
| DB dialog progressbar | UI | ❌ | DB 묶음 |
| 시스템 로그 색상 태그 (V3.16) | UI | ✅ BP-004A | 완료 |
| formula manager factors (V3.17) | strategy | ❌ HOLD-001 |
| Analyzer arg rename | strategy | ❌ HOLD-001 |
| PyCharm rules | docs | ❌ |
| price 분석 데이터 로드 | strategy | ❌ HOLD-001 |
| chart 예외 unify | UI | ⚠️ BP-009A 부분 |
| listed-shares DB 갱신 | DB | ❌ HOLD-002 |
| shutdown 확인 | runtime | ❌ broad |
| financial webcrawling | utility | ✅ BP-004B | 완료 |
| stock-info cleanup | trade | ❌ BP-003 hold |
| **strategy syntax test pyd 분리 (V3.17)** | **pyd** | **❌ BP-012A no-op/hold** | **pyd 계약 충돌** |
| Upbit 첫 tick 수량 | trade | ❌ BP-003 hold |
| **risk min data 30 (V3.18)** | **strategy** | **❌** | **AnalyzerRisk runtime 미연결로 무의미** |
| prange removal | strategy | ❌ HOLD-001 |
| 주문유형 guard (V3.18) | trade | ❌ BP-014A hold/excluded |
| 백테스트 손익 분석 load 이름 | backtest | ❌ BP-001 hold |
| 잔고 변경시만 저장 | DB | ❌ HOLD-002 |
| **strategy-test dummy microstructure (V3.18)** | **strategy** | **❌ BP-013A hold** | **microstructure runtime 필요** |
| strategy tab 아이콘 | UI | ❌ | 후보 |

### 3.5 매트릭스 합산

| 분류 | 항목 수 | 비율 |
|---|---|---|
| ✅ 완료 (전체 또는 부분) | 12 | ~12% |
| ⚠️ no-op/이미 보유 | 3 | ~3% |
| ❌ HOLD/excluded | 80+ | ~85% |

→ V3 신기능 단위로 보면 **약 12%만 반영, 약 85%는 미반영**. 더욱 중요한 것은, 미반영 85%에 **사용자 가치가 가장 큰 학습/분석/백테스트 학습/실시간 학습/DB 학습 데이터 구조가 모두 포함**되어 있다는 점이다.

---

## 4. 미반영의 근본 원인 분석

### 4.1 6대 진입 차단 원칙 (allowlist plan §4)

운영 문서가 정한 절대 제외 목록은 다음과 같다.

1. LS REST/REAL/WebSocket 전환 (사용자 요청으로 본 audit에서도 제외 대상)
2. **DB primary key, 거래소별 설정 분리, 잔고 저장 schema, 분석 DB reset**
3. V3U pyd-free 또는 V3 pyd rename/split
4. dashboard 전체 도입
5. **백테스트 시장별 engine 구조 broad merge**
6. **analysis runtime 전체 wiring**

→ 사용자가 묻는 "학습 + 백테스트 학습 적용 + 거래 학습 적용"은 **2 + 5 + 6**에 정확히 해당하므로, 현재 운영 원칙 자체가 진입을 막고 있다.

### 4.2 closure audit이 명시한 7대 재개 차단 항목

`docs/update_log/2026-05-08_v3_2uc_final_closure_audit.md` §5는 다음을 별도 설계 문서/runtime evidence/mock spec 없이 다시 열지 않는다고 못박는다.

1. LS API / LS websocket / LS TR/REAL
2. **DB schema migration / 잔고 저장 정책 변경**
3. pyd/UI broad merge / V3U-only pyd-free
4. **analysis runtime wiring / AnalyzerRisk 실제 연결**
5. **backtest engine 대형 구조 변경**
6. broker별 주문유형 matrix 변경
7. chart moneytop time/query normalization

→ 학습 시스템 활성화는 **2 + 4 + 5 동시 해제 필요**. 어느 하나가 빠져도 학습 시스템은 동작하지 않는다.

### 4.3 micro-candidate 전략의 한계

현재 운영 방식은 **broad merge 금지 + 파일 단위 cherry-pick 금지 + 단일 함수/조건 단위 수동 이식**이다. 이 방식은 표면 버그 수정에는 매우 안전하지만, **다음과 같은 본질적 한계**가 있다.

| 영역 | micro-candidate 한계 |
|---|---|
| 신규 모듈 도입 | analyzer 모듈 1개 추가 = 파일 1개 = "파일 단위 cherry-pick"에 가까움 → 자체 원칙 위배 위험 |
| Runtime wiring | 모듈 + 호출 지점 + DB + settings를 동시에 변경해야 동작 → 한 commit 1개 BP-ID 원칙으로 분해 어려움 |
| DB schema | migration script + backup/rollback이 필수 → micro 단위 분해 불가 |
| 백테스트 학습 적용 | 백테스트 일자 이전 데이터 로드 = engine 구조 변경 → BP-001 hold와 충돌 |
| 실시간 학습 적용 | receiver/strategy/DB가 동시 영향 → broker matrix 설계 필요 |

**결론**: 학습/분석 시스템은 micro-candidate 단위로 백포트 불가능하다. **별도 설계 트랙이 필수**.

### 4.4 Kiwoom data shape 위험

V3는 broker가 LS 중심이며, V3 analyzer는 LS REST API의 tick/min 데이터 shape를 가정한다. 2U_C는 Kiwoom Open API 기반이므로 다음 차이가 존재할 가능성이 높다.

| 항목 | LS (V3) | Kiwoom (2U_C) | 위험 |
|---|---|---|---|
| tick payload 컬럼 순서/이름 | LS API 명세 | Kiwoom OPT10001/OPT10004 명세 | shape mismatch |
| min 데이터 timestamp | UTC/KST 혼재 | KST 고정 | tz 보정 필요 |
| 호가 잔량 | LS L1~L10 | Kiwoom L1~L10 | OK 가능성 |
| 거래량 단위 | 통합 | 정수 | OK 가능성 |
| 시장 시간 | 24h(coin) / 09:00(stock) | 동일 | OK |

→ **V3 analyzer 입력 계약 = Kiwoom data shape**임을 검증하기 전에는 학습 결과가 실거래에서 잘못된 신호를 낼 위험이 있다. 이 검증 자체가 별도 설계 산출물이다.

---

## 5. 목표 달성 방법 연구

> **목표**: V3의 LS증권 변경을 제외한 신기능(특히 학습 시스템, 백테스트 학습 데이터 적용, 실시간 거래 학습 데이터 적용, DB 학습 데이터 저장 구조, 분석 UI)을 **2U_C의 Kiwoom 유지 lane을 깨뜨리지 않고** 작동시킨다.

### 5.1 전략 원칙

#### 원칙 1: micro-candidate 한계 인정, 별도 "설계 트랙" 신설

기존 BP-### micro-candidate 트랙은 표면 보정용으로 유지하고, 학습/분석 시스템 활성화는 **`V3K-DESIGN-#`(Learning System) 별도 트랙**으로 분리한다.

```text
기존: BP-### (Backport, micro-candidate, 1 file 1 commit 1 ID)
신설: V3K-DESIGN-# (Learning System, multi-file design phase)
       └── 산출물: 설계서 → mock test spec → DB migration spec → wiring spec
       └── 코드: design 통과 후에만 V3K-IMPL-# (Implementation) 트랙으로 분리
```

#### 원칙 2: Kiwoom 호환 계약을 먼저 고정

V3 analyzer 입력/출력 계약을 2U_C Kiwoom data shape 위에서 **테스트 가능한 계약**으로 다시 정의한다. 계약은 다음을 포함한다.

```python
@dataclass(frozen=True)
class TickInput:
    code: str
    timestamp: int  # Kiwoom 기준 KST epoch
    price: int
    volume: int
    # ... Kiwoom OPT10004 매핑

@dataclass(frozen=True)
class MinInput:
    code: str
    timestamp: int
    open: int
    high: int
    low: int
    close: int
    volume: int

@dataclass(frozen=True)
class AnalyzerOutput:
    pattern_id: str
    confidence: float
    feature_vector: dict
```

#### 원칙 3: DB는 격리된 신규 학습 DB로 시작

기존 `_database/`의 schema/PK는 절대 변경하지 않는다. 학습 데이터는 **별도 `_learning_database/`** 에 저장하고, migration 없이 신규 생성만으로 동작하게 만든다.

```text
2U_C 기존 DB:           _database/      (보호, 변경 금지)
2U_C 학습 DB (신규):    _learning_database/   (이번 트랙에서 신설)
```

이 분리로 HOLD-002의 "DB 비호환 위험"을 우회한다.

#### 원칙 4: 백테스트 학습 적용은 read-only feature flag로

백테스트 엔진을 변경하지 않고, **학습 데이터 read-only loader를 별도 모듈로 만들어 feature flag로 켜고 끈다**. 이 방식은 BP-001 hold 사유(B/S/R custom 충돌)를 우회한다.

```python
# backtest/back_learning_loader.py (신규)
def load_learning_data_for_backtest(date, code, *, enabled=False):
    if not enabled:
        return None
    return _learning_db.read_pre_date_only(date, code)
```

엔진은 호출만 추가하고, flag가 꺼져 있으면 기존 동작과 100% 동일하다.

#### 원칙 5: 실시간 학습 적용은 sidecar 프로세스로

거래 receiver/trader 흐름을 변경하지 않고, **학습 데이터 read-only sidecar**를 별도 thread로 띄워 결과를 큐로 전달한다. 메인 거래 흐름은 큐를 무시할 수도 있고 사용할 수도 있다.

```text
[Kiwoom Receiver] ──┐
                    ├──> [Trade Decider] ──> [Trader]
                    │            ▲
                    │            │ optional advisory
[Learning Sidecar] ─┘────────────┘
```

이 방식은 BP-003 hold 사유(receiver/trader broad 변경)를 우회한다.

### 5.2 단계별 로드맵

#### Phase 0 — 사전 설계 (코드 0건, 문서만)

| Step | 산출물 | 검증 |
|---|---|---|
| 0.1 V3 학습 시스템 reverse-engineering | V3 analyzer 7개 + manager_formula의 입력/출력/state 계약 문서 | V3 코드 정독 + 사용자 검증 |
| 0.2 Kiwoom data shape 명세 | Kiwoom OPT10001/10004 ↔ V3 TickInput 매핑표 | 실제 Kiwoom payload 1개 캡처 |
| 0.3 학습 DB schema 설계 | `_learning_database/` 테이블/컬럼/인덱스/PK 정의 | sqlite mock 1회 통과 |
| 0.4 Feature flag 정책 | 백테스트/실시간 각각 ON/OFF 시 동작 매트릭스 | 4가지 조합 모두 명세 |
| 0.5 위험 매트릭스 | data shape mismatch / DB 누수 / 학습 누수 / Kiwoom rate limit / mock vs live 차이 | 각 위험별 mitigation |
| 0.6 Test fixture 설계 | Kiwoom mock data 3종 (정상 / 결측 / 이상치) | mock 자체 sanity test |

**Phase 0 종료 조건**: 모든 산출물이 docs/superpowers/specs/에 commit, 사용자 리뷰 통과, runtime 코드 변경 없음.

#### Phase 1 — 학습 DB 인프라 (`V3K-DESIGN-1` → `V3K-IMPL-1`)

| Step | 변경 범위 | 검증 |
|---|---|---|
| 1.1 `_learning_database/` 디렉터리 신설 + .gitignore 등록 | `.gitignore` 1줄 | git status clean |
| 1.2 `utility/learning_db.py` 신규 (read/write helper) | 신규 파일 1개 | unit test (sqlite in-memory) |
| 1.3 schema migration script | `scripts/init_learning_db.py` 신규 | dry-run 출력 확인 |
| 1.4 healthcheck CLI | `python scripts/learning_db_health.py` | 빈 DB 생성 + 검증 |

**Phase 1 종료 조건**: 학습 DB가 빈 상태로 생성되며, 기존 `_database/`는 1바이트도 변경되지 않는다. GUI/거래/백테스트 동작 100% 동일.

#### Phase 2 — Dormant analyzer 활성화 (`V3K-IMPL-2A` ~ `V3K-IMPL-2G`)

V3 analyzer 7개를 **하나씩** 2U_C에 이식하되, runtime 호출은 하지 않고 **단위 테스트로만 검증**한다. 가장 위험이 낮은 순서:

| 순번 | analyzer | 우선순위 사유 |
|---|---|---|
| 1 | `analyzer_volume_profile.py` (가격대) | DB read-only, output decision 영향 적음 |
| 2 | `analyzer_volume_spike.py` (거래량) | 단순 통계, state 적음 |
| 3 | `analyzer_candle_pattern.py` (캔들 패턴) | talib 의존성 사전 검증 필요 |
| 4 | `analyzer_volatility_pattern.py` (변동성) | numba 의존성 검증 필요 |
| 5 | `analyzer_microstructure.py` (시장미시구조) | 1136 lines, 가장 복잡 |
| 6 | `analyzer_volatility_stop_take.py` (TP/SL) | 거래 결정에 영향, 마지막에 도입 |
| 7 | `analyzer_risk.py` runtime 활성화 | 이미 dormant 보존 → wiring만 |

각 V3K-IMPL-2X는 다음을 포함한다.

```text
V3K-IMPL-2X
  ├── strategy/analyzer_<name>.py 추가 (V3에서 가져오되 Kiwoom 계약으로 어댑터 적용)
  ├── tests/test_analyzer_<name>.py (mock fixture 3종으로 단위 테스트)
  ├── docs/update_log/<date>_ls_impl_2x_<name>.md
  └── runtime 호출 없음 (Phase 3 전까지 dormant)
```

**Phase 2 종료 조건**: 7개 analyzer가 2U_C 파일로 존재하며 단위 테스트 통과. runtime은 호출하지 않으므로 GUI/거래/백테스트 동작 100% 동일.

#### Phase 3 — 백테스트 학습 데이터 적용 (`V3K-IMPL-3`)

V3.10의 "학습 데이터를 백테스트 일자 이전 기준으로 로드"를 2U_C에 적용한다.

| Step | 변경 |
|---|---|
| 3.1 `backtest/back_learning_loader.py` 신규 | feature flag 기본 OFF, 학습 DB read-only |
| 3.2 백테스트 엔진에 1줄 호출 추가 | `learning = back_learning_loader.load(...)` (flag OFF면 None) |
| 3.3 analyzer 결과를 백테스트 결정 함수에 전달하는 어댑터 | None 처리 명시 |
| 3.4 통합 테스트 | 동일 backtest 케이스를 flag ON/OFF로 비교, OFF == 기존 결과 |
| 3.5 학습 데이터 누수 방지 검증 | 백테스트 일자 이후 데이터 접근 시 RaiseError |

**Phase 3 종료 조건**:
- flag OFF: 기존 백테스트와 결과 100% 동일 (regression 0)
- flag ON: 학습 데이터를 사용하되 백테스트 일자 이후 데이터를 절대 참조하지 않음 (자동 검증)

#### Phase 4 — 실시간 거래 학습 데이터 적용 (`V3K-IMPL-4`)

V3.11의 "실시간 매매가 학습 데이터를 로드"를 sidecar 패턴으로 적용한다.

| Step | 변경 |
|---|---|
| 4.1 `trade/learning_sidecar.py` 신규 | QThread, 학습 DB read-only |
| 4.2 trader에 advisory queue 1개 추가 | flag OFF면 큐 무시 |
| 4.3 1초 스냅샷 분석 (V3.10/11) sidecar에서 실행 | 메인 흐름 차단 금지 |
| 4.4 Kiwoom rate limit 영향 검증 | 학습 DB read만, Kiwoom API 호출 없음 |
| 4.5 mock 모의 거래 환경에서 24시간 회귀 | flag ON/OFF 비교 |

**Phase 4 종료 조건**:
- flag OFF: 기존 거래와 동작 100% 동일
- flag ON: advisory 결과가 거래 결정에 반영되되, 메인 흐름 latency 증가가 측정 한계 이내

#### Phase 5 — 분석 시스템 UI (`V3K-IMPL-5`)

settings, radar chart, analysis progressbar를 도입한다. **pyd MainWindow wrapper 계약은 변경하지 않는다**.

| Step | 변경 |
|---|---|
| 5.1 별도 분석 dialog (`ui/ui_analysis_dialog.py`) 신규 | MainWindow와 분리, dialog 내부에서만 동작 |
| 5.2 학습 시작/중지 버튼 + progressbar | sidecar 제어 only |
| 5.3 radar chart 위젯 | pyqtgraph standalone, MainWindow에 영향 없음 |
| 5.4 settings 저장 | 별도 `_learning_settings.json`, 기존 settings 영향 없음 |
| 5.5 GUI 회귀 테스트 | MainWindow는 변경 0건 검증 |

**Phase 5 종료 조건**: 분석 UI가 별도 dialog로 동작, 메인 GUI/거래/백테스트 코드는 변경 0건.

### 5.3 위험 매트릭스와 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| Kiwoom data shape ≠ V3 input contract | analyzer 결과가 잘못됨 | Phase 0.2 매핑표 + Phase 2 어댑터 + mock fixture 3종 |
| 학습 누수 (백테스트 일자 이후 데이터 사용) | 백테스트 결과 과대평가 | Phase 3.5 자동 검증 (RaiseError) |
| 학습 DB 손상 → 거래 영향 | 실거래 정지 | sidecar는 read-only, 메인 흐름은 advisory queue 무시 가능 |
| Kiwoom API rate limit 초과 | 차단 | sidecar는 학습 DB read만, Kiwoom API 호출 없음 |
| numba/talib 의존성 충돌 | 빌드 실패 | Phase 0.5 위험 매트릭스 + Phase 2 단계별 도입 |
| feature flag 누락 → 의도하지 않은 활성화 | 거래 위험 | flag 기본 OFF + ON 시 명시 로그 + GUI 표시 |
| 기존 `_database/` 변경 사고 | 기존 데이터 손실 | Phase 1.1 `_learning_database/` 격리 |
| pyd MainWindow 계약 충돌 | UI 깨짐 | Phase 5 별도 dialog, MainWindow 변경 0건 |
| micro-candidate 원칙 위배 | 운영 일관성 손상 | 별도 `V3K-IMPL-#` 트랙 신설 명시 |

### 5.4 검증/Verification 요구사항

각 V3K-IMPL-#는 다음 4계층 검증을 통과해야 한다.

#### 계층 1: 정적 검증 (offline, 즉시)

```powershell
python -m py_compile <changed-files>
python scripts/verify_release_sync.py
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev
git diff --check
```

#### 계층 2: Mock unit test (offline, CI 가능)

```powershell
python -m pytest tests/test_analyzer_<name>.py -v
python -m pytest tests/test_learning_db.py -v
python -m pytest tests/test_back_learning_loader.py -v
python -m pytest tests/test_learning_sidecar.py -v
```

각 테스트는 다음 fixture를 사용한다.

- `fixture_kiwoom_tick_normal.json` (정상 시장)
- `fixture_kiwoom_tick_missing.json` (결측치 포함)
- `fixture_kiwoom_tick_outlier.json` (이상치)

#### 계층 3: 통합 회귀 테스트 (offline)

```powershell
python scripts/run_backtest_regression.py --flag OFF --baseline <date>
python scripts/run_backtest_regression.py --flag ON --baseline <date>
python scripts/diff_backtest_results.py --expect "OFF == baseline"
```

#### 계층 4: GUI/Live runtime 회귀 (manual)

| 검증 항목 | 도구 |
|---|---|
| MainWindow 시작/종료 | 수동 + 시간 측정 |
| 백테스트 실행 (flag OFF) | 기존 결과와 100% 일치 |
| 백테스트 실행 (flag ON) | 학습 데이터 사용 확인 + 누수 검증 |
| 모의 거래 24h | 메인 흐름 latency, advisory queue 동작 |
| 실거래 (사용자 승인 시) | 격리된 소액 계정 + 단계적 ramp-up |

### 5.5 권장 실행 순서

#### 최단 경로 (학습 시스템만 작동시키기)

```text
Phase 0 (설계, 1~2주)
  └─> Phase 1 (학습 DB 인프라, 1주)
       └─> Phase 2 analyzer 1개 (volume_profile, 1주)
            └─> Phase 3 (백테스트 학습 적용, 2주)
                 └─> Phase 4 (실시간 학습 적용, 2주)
                      └─> Phase 5 (분석 UI, 2주)
```

총 9~10주, code commit 약 30~40개 추정.

#### 안전 우선 경로 (모든 analyzer 활성화)

```text
Phase 0 (설계)
  └─> Phase 1 (DB)
       └─> Phase 2.1~2.7 (analyzer 7개 순차)
            └─> Phase 3 (백테스트, analyzer 별로 flag)
                 └─> Phase 4 (실시간, advisory only)
                      └─> Phase 5 (UI)
```

총 16~20주, code commit 약 60~80개 추정.

### 5.6 진입 트리거 (closure audit이 명시한 재개 조건과의 매핑)

`final_closure_audit.md` §6은 다음 중 하나가 있을 때 새 후보를 연다고 명시한다.

| closure audit 조건 | 본 연구의 충족 방법 |
|---|---|
| GUI/live runtime 재현 evidence | Phase 5 + 계층 4 검증 |
| mock 가능한 단일 입력/출력 test spec | Phase 0.6 + 계층 2 |
| broker별 주문유형 matrix | Phase 4의 advisory queue 패턴은 broker matrix 회피 가능 |
| DB migration spec | Phase 0.3 + Phase 1.3 |
| analysis runtime wiring spec | Phase 0.1 + Phase 0.2 + Phase 2/3/4 |
| V3.19 이상 신규 upstream | 본 연구는 현재 V3.18 기준이므로 충족 가능 |

→ **본 연구의 Phase 0 산출물이 closure audit이 요구하는 모든 재개 조건을 만족시킨다.**

---

## 6. 권장 다음 단계

### 6.1 즉시 (이번 주)

1. **본 문서를 사용자가 검토/승인**한다.
2. 승인 시, **Phase 0 사전 설계만 별도 트랙으로 개시**한다 (코드 변경 0건).
3. Phase 0 산출물은 `docs/superpowers/specs/2026-05-XX-learning-system-design/`에 저장한다.

### 6.2 Phase 0 산출물 체크리스트

```text
[ ] V3 analyzer 7개 입력/출력/state 계약 문서
[ ] manager_formula 역할 분석 문서
[ ] Kiwoom OPT10001/10004 ↔ V3 TickInput/MinInput 매핑표
[ ] 학습 DB schema 설계 (테이블/컬럼/PK/인덱스/마이그레이션 정책)
[ ] Feature flag 정책 (backtest/realtime ON/OFF 매트릭스)
[ ] 위험 매트릭스 + mitigation (≥9개 항목)
[ ] Test fixture 설계 (정상/결측/이상치 ≥3종)
[ ] V3 → 2U_C 어댑터 인터페이스 명세
[ ] sidecar QThread 통신 프로토콜 명세
[ ] 분석 dialog UI 와이어프레임 (MainWindow 비침투 보장)
```

### 6.3 Phase 0 통과 후

`oh-my-claudecode:plan --consensus`로 Planner + Architect + Critic의 합의 plan 생성 → 사용자 승인 → Phase 1 V3K-IMPL-1 개시.

### 6.4 미실행 시 영향

Phase 0~5를 실행하지 않을 경우, **2U_C는 영구히 "V2.77 + 표면 보정 12건" 상태**로 남는다. 이 상태가 안전하며 Kiwoom 거래 lane으로서는 정당하지만, **V3가 갖춘 학습 기반 거래 능력은 영구 미반영**이다.

---

## 7. 부록: 검증 명령 모음

### 7.1 본 audit이 사용한 검증 명령

```powershell
# 파일 시스템 비교
ls C:/System_Trading/STOM/STOM_V.wt-3/strategy/
ls C:/System_Trading/STOM/STOM_V.wt-dev/strategy/

# Runtime wiring 검사
grep -r "import.*analyzer\|from strategy" `
  C:/System_Trading/STOM/STOM_V.wt-dev/backtest/ `
  C:/System_Trading/STOM/STOM_V.wt-dev/trade/

# Git 이력
git -C C:/System_Trading/STOM/STOM_V.wt-dev log --all --oneline -- "strategy/analyzer_*.py"
git -C C:/System_Trading/STOM/STOM_V.wt-dev log --oneline -25

# Release sync (현재 상태 confirm)
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev
```

### 7.2 Phase 0 후 사용할 검증 명령

```powershell
# Phase 1 학습 DB
python scripts/init_learning_db.py --dry-run
python scripts/learning_db_health.py

# Phase 2 analyzer
python -m pytest tests/test_analyzer_volume_profile.py -v
python -m pytest tests/test_analyzer_volume_spike.py -v
# ... 나머지 5개

# Phase 3 백테스트
python scripts/run_backtest_regression.py --flag OFF --baseline 2026-04-01
python scripts/run_backtest_regression.py --flag ON --baseline 2026-04-01
python scripts/diff_backtest_results.py --expect "OFF == baseline"

# Phase 4 실시간
python scripts/run_paper_trading_24h.py --flag OFF
python scripts/run_paper_trading_24h.py --flag ON --advisory-only
```

---

## 8. 메타 정보

| 항목 | 값 |
|---|---|
| 문서 ID | 2026-05-08_v3_2uc_unmet_features_audit_and_research |
| 작성 lane | `STOM_Version_2U_C` (`STOM_V.wt-dev`) |
| code 변경 | 없음 |
| 다음 commit 제안 | "V3 미반영 신기능 검증과 달성 방법 연구를 기록한다" |
| 후속 트랙 제안 | `V3K-DESIGN-#` (Learning System) 별도 설계 트랙 신설 |
| 본 문서를 무효화하는 조건 | (1) V3.19+ 새 upstream으로 학습 시스템 구조가 바뀌는 경우, (2) 사용자가 학습 시스템 백포트 자체를 영구 보류로 결정하는 경우 |

---

## 9. 한 줄 결론

> **V3 신기능은 약 12%만 2U_C에 반영되었고, 핵심 가치인 학습/분석/백테스트 학습/실시간 학습/DB 학습 데이터 구조는 0% 반영되었다. 이를 달성하려면 기존 micro-candidate 트랙으로는 불가능하며, 본 문서가 제안하는 5단계(Phase 0~5) 별도 설계 트랙(V3K-DESIGN / V3K-IMPL)이 필요하다. Phase 0 사전 설계만 코드 변경 없이 즉시 시작 가능하다.**
