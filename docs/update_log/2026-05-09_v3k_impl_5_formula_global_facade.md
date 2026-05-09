# V3K-IMPL-5: formula/global facade 준비

- 작성일: 2026-05-09 KST
- 브랜치/워크트리: `STOM_Version_2U_C` / `C:\System_Trading\STOM\STOM_V.wt-dev`
- 상위 목표: `2U_C = V3 신기능 + Kiwoom 유지`
- 현재 단계: V3 analyzer output을 기존 formula/global layer 앞단에서 안전하게 다루기 위한 facade 단계
- 상태: 구현 및 smoke 검증 완료, 실제 runtime 주입은 보류

## 1. 사용자 요청/프롬프트 맥락

이번 단계는 다음 반복 목표의 연장이다.

> 2U_C의 V3 기능을 개발 계획에 작성했던 문서에 따라 목적을 달성한다.  
> Kiwoom증권을 유지한 채 V3의 신기능을 2U_C에 반영한다.  
> 각 단계는 commit으로 체계적으로 관리하고 전체 계획/현재 단계/남은 단계를 문서화한다.  
> analyzer output을 formula/global layer에 연결할 준비를 하되, 주문/청산 조건 변경과 Kiwoom receiver/order path 변경은 금지한다.

## 2. V3 원본 검토 결과

V3 공식 lane에서는 `trade/base_strategy.py`가 다음 analyzer를 직접 초기화하고 runtime 전략 흐름에서 결과를 지역변수 및 배열 구간에 직접 넣는다.

- `AnalyzerRisk`
- `AnalyzerCandlePattern`
- `AnalyzerVolumeSpike`
- `AnalyzerVolumeProfile`
- `AnalyzerVolatilityPattern`
- `AnalyzerVolatilityStopTake`

V3 runtime은 예를 들어 다음 analyzer output을 직접 계산한다.

- `패턴점수`, `패턴신뢰도`
- `리스크점수`
- `거래량점수`, `거래량신뢰도`
- `가격대점수`, `가격대신뢰도`
- `변동성점수`, `변동성신뢰도`
- `예상수익률`, `익절수익률`, `손절수익률`, `변손익신뢰도`

그러나 2U_C는 Kiwoom 유지 custom lane이다. V3 방식처럼 `trade/base_strategy.py`, Kiwoom strategy, 주문/청산 흐름에 바로 결과를 주입하면 OFF 회귀와 실거래 안전성이 깨질 수 있다. 따라서 이번 단계는 직접 runtime merge가 아니라 **facade-only**로 제한한다.

## 3. 구현 결정

### 3.1 feature flag 정렬

기존 설계 문서의 flag 이름을 따른다.

- `V3K_FORMULA_MANAGER_ADAPTER`
- `V3K_STG_GLOBALS_FACADE`

두 flag가 모두 ON일 때만 facade가 globals 후보를 생성한다. 둘 중 하나라도 OFF이면 no-op이다.

호환을 위해 코드 내부에서는 다음 alias도 유지한다.

- `FLAG_FORMULA_GLOBAL_FACADE = FLAG_FORMULA_MANAGER_ADAPTER`

### 3.2 신규 facade

추가 파일:

- `strategy/v3k_formula_facade.py`

추가 구조:

- `V3KFormulaGlobalRequest`
  - analyzer output 후보와 feature flags를 받는다.
- `V3KFormulaGlobalResult`
  - 변환된 analyzer value, prefixed globals dict, diagnostics를 담는다.
- `V3KFormulaGlobalFacade`
  - analyzer output을 formula/global layer가 나중에 받을 수 있는 `V3K_` prefix callable dict로 변환한다.

### 3.3 prefix 정책

이번 facade는 기존 전략명/수식명과 충돌하지 않도록 모든 global 후보를 `V3K_` prefix로 내보낸다.

예:

- `V3K_리스크점수()`
- `V3K_패턴점수()`
- `V3K_거래량신뢰도()`

중요: unprefixed `리스크점수`, `패턴점수` 등은 아직 globals로 내보내지 않는다. 이는 기존 전략식과 이름 충돌을 방지하기 위한 의도적 제한이다.

## 4. 변경 파일

### 4.1 `strategy/v3k_analyzer_adapter.py`

추가:

- `FLAG_FORMULA_MANAGER_ADAPTER = "V3K_FORMULA_MANAGER_ADAPTER"`
- `FLAG_STG_GLOBALS_FACADE = "V3K_STG_GLOBALS_FACADE"`
- `FLAG_FORMULA_GLOBAL_FACADE = FLAG_FORMULA_MANAGER_ADAPTER`
- DEFAULT_FLAGS의 기본값 OFF 추가

### 4.2 `strategy/v3k_formula_facade.py`

추가:

- V3 analyzer output field order
- analyzer kind → output field mapping
- feature flag gated facade build
- side-effect-free `globals_dict` 생성

### 4.3 `scripts/smoke_v3k_formula_facade.py`

검증 항목:

1. 기본 OFF no-op
2. ON + empty analyzer output → zero-default prefixed globals 생성
3. ON + synthetic analyzer output → 값 변환 및 callable 반환 검증
4. unprefixed 이름 미노출 검증
5. 금지 runtime artifact 생성 없음

## 5. 명시적으로 제외한 작업

이번 단계에서는 다음을 하지 않았다.

- `trade/formula_manager.py` 수정
- `trade/base_strategy.py` 수정
- Kiwoom receiver/agent/trader/strategy 파일 수정
- `FormulaManager.UpdateGlobalsFunc()` 직접 호출
- `globals().update()` runtime 호출
- 주문/청산 조건 변경
- analyzer constructor runtime 호출
- `_database`, `_database_v3k_shadow`, `*.db` 생성
- LS API 의존성 추가

## 6. 검증 결과

실행한 명령:

```powershell
python -m py_compile strategy\v3k_analyzer_adapter.py strategy\v3k_formula_facade.py scripts\smoke_v3k_formula_facade.py
python scripts\smoke_v3k_formula_facade.py
python scripts\smoke_v3k_realtime_learning_boundary.py
python scripts\smoke_v3k_backtest_learning_hook.py
python scripts\smoke_v3k_learning_loader.py
python scripts\smoke_v3k_analyzer_modules.py --import-only
python scripts\smoke_v3k_analyzer_modules.py
python scripts\smoke_v3k_analyzer_adapter.py
python scripts\smoke_v3k_analyzer_adapter.py --enable-v3-risk
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph
```

결과 요약:

- py_compile 통과
- formula/global facade smoke 통과
- realtime learning boundary smoke 통과
- backtest learning hook smoke 통과
- learning loader smoke 통과
- analyzer module import/field-contract smoke 통과
- analyzer adapter OFF/ON smoke 통과
- 금지 artifact status 출력 없음

## 7. 안전성 판단

이번 단계는 runtime injection이 아니다. 따라서 기존 2U_C/Kiwoom 매매 동작을 변경하지 않는다.

안전 장치:

- feature flag 기본 OFF
- `V3K_FORMULA_MANAGER_ADAPTER`와 `V3K_STG_GLOBALS_FACADE` 이중 gate
- `V3K_` prefix로 기존 전략식 이름 충돌 방지
- no runtime globals update
- no Kiwoom path edit
- no DB artifact

## 8. 다음 단계

이제 facade는 준비되었지만 실제 runtime 연결은 아직 하지 않았다. 다음 단계는 `V3K-VERIFY-1A` 또는 `V3K-IMPL-6` 중 하나다.

가장 안전한 추천은 `V3K-VERIFY-1A`이다.

목표:

- 지금까지 추가한 V3K adapter/learning/facade가 OFF 상태에서 기존 2U_C와 동작 차이를 만들지 않는지 종합 점검한다.
- 직접 runtime hook을 더 추가하기 전에 branch/file diff, smoke, 금지 artifact, Kiwoom path untouched, DB untouched를 고정한다.
- 이후 UI/설정 노출 또는 runtime dry-run hook 진입 여부를 판단한다.

추천 OMX 명령:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
omx ralph --prd "V3K-VERIFY-1A를 시작한다. 목표는 STOM_Version_2U_C에서 지금까지 추가한 V3K analyzer adapter, analyzer module staging, backtest learning hook, realtime learning boundary, formula/global facade가 feature flag 기본 OFF에서 기존 Kiwoom 유지 runtime에 영향을 주지 않는지 종합 검증하는 것이다. Kiwoom receiver/order/strategy 의사결정 경로, core DB, DB 파일 생성/수정, LS API 의존성 추가는 금지한다. 최신 V3K smoke 전체, py_compile, forbidden artifact guard, Kiwoom path untouched audit, release sync, docs/registry 갱신, 한국어 commit까지 수행하고 다음 UI/설정 노출 또는 runtime dry-run hook 진입 여부를 결정한다."
```

## 9. 진행률 갱신

전체 V3 도입 → V3U → 2U_C V3K 목표 기준:

- V3/V3U 공식 준비: 완료
- 2U_C V3K 설계: 완료
- analyzer adapter/staging: 완료
- backtest learning loader/hook: 완료
- realtime learning boundary: 완료
- formula/global facade: 완료
- 남은 작업: 종합 OFF 회귀 검증, UI/설정 노출 여부 결정, DB shadow cutover는 사용자 승인 전 보류

현재 추정 전체 진행률: 약 94%.
