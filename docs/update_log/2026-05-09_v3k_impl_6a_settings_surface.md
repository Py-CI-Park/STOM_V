# V3K-IMPL-6A: 비침투적 settings surface contract

- 작성일: 2026-05-09 KST
- 브랜치/워크트리: `STOM_Version_2U_C` / `C:\System_Trading\STOM\STOM_V.wt-dev`
- 상위 목표: `2U_C = V3 신기능 + Kiwoom 유지`
- 현재 단계: V3K analyzer/learning/formula feature flags를 UI/설정에 노출하기 전의 contract-only 설정 surface
- 상태: 구현 및 smoke 검증 완료, GUI/DB/runtime 연결은 보류

## 1. 사용자 요청/프롬프트 맥락

이번 단계는 다음 목표의 연장이다.

> 2U_C의 V3 기능을 개발 계획에 작성했던 문서에 따라 목적을 달성한다.  
> Kiwoom증권을 유지한 채 V3의 신기능을 2U_C에 반영한다.  
> 각 단계는 commit으로 체계적으로 관리하고 전체 계획/현재 단계/남은 단계를 문서화한다.  
> V3K analyzer/learning/formula feature flags를 UI/설정에 노출하기 전, MainWindow/pyd wrapper 직접 변경 없이 비침투적 설정 surface와 contract smoke를 먼저 준비한다.

## 2. 이번 단계의 목적

`V3K-VERIFY-1A`에서 OFF 회귀와 Kiwoom untouched audit을 통과했다. 다음 위험은 UI/설정 노출 과정에서 다음 문제가 생기는 것이다.

1. 기본 OFF가 아닌 flag가 생긴다.
2. 설정 surface가 DB를 직접 읽거나 쓰기 시작한다.
3. MainWindow/pyd wrapper를 잘못 건드려 GUI 계약을 깨뜨린다.
4. 설정 key 이름이 기존 analyzer/learning/facade flag와 어긋난다.
5. runtime hook 없이도 `globals().update(...)`나 Kiwoom path에 side-effect가 생긴다.

따라서 이번 단계는 실제 GUI나 DB 연결이 아니라, **dict/JSON-like 입력을 normalize하는 contract-only surface**를 먼저 추가한다.

## 3. 변경 사항

### 3.1 `strategy/v3k_analyzer_adapter.py`

추가 flag:

- `V3K_ANALYSIS_UI_ENABLED`

이 flag도 `DEFAULT_FLAGS`에서 기본 OFF다. 아직 GUI를 띄우거나 MainWindow/pyd wrapper에 연결하지 않는다.

### 3.2 `strategy/v3k_settings_surface.py`

신규 모듈을 추가했다.

주요 구조:

- `V3K_SETTINGS_SURFACE_VERSION`
- `V3KSettingContract`
- `V3KSettingsSurfaceResult`
- `V3K_SETTING_CONTRACTS`
- `v3k_setting_contract_keys()`
- `v3k_settings_defaults()`
- `v3k_settings_contract_rows()`
- `normalize_v3k_settings()`
- `assert_v3k_settings_contract_aligned()`

설정 contract에 포함된 주요 key:

- `V3K_ANALYSIS_UI_ENABLED`
- `V3K_BACKTEST_LEARNING_ENABLED`
- `V3K_REALTIME_LEARNING_ENABLED`
- `V3K_ANALYZER_MODULE_STAGING`
- `V3K_RISK_ANALYZER_V3_ENGINE`
- `캔들분석`
- `거래량분석`
- `가격대분석`
- `변동성분석`
- `변손익분석`
- `리스크분석`
- `V3K_FORMULA_MANAGER_ADAPTER`
- `V3K_STG_GLOBALS_FACADE`

모든 default는 `False`다.

### 3.3 `scripts/smoke_v3k_settings_surface.py`

신규 smoke를 추가했다.

검증 항목:

1. contract key 중복 없음
2. contract key가 `DEFAULT_FLAGS`와 정렬됨
3. 모든 contract default가 OFF
4. normalize 기본 결과도 all-off
5. 문자열/숫자 입력 normalize 동작 확인
6. unknown setting은 diagnostics로만 기록하고 무시
7. settings 결과가 formula/global facade flags에 안전하게 전달됨
8. 금지 runtime artifact 생성 없음

### 3.4 `scripts/audit_v3k_verify_1a.py`

VERIFY-1A audit의 OFF flag 목록에 `V3K_ANALYSIS_UI_ENABLED`를 추가했다.

## 4. 명시적으로 제외한 작업

이번 단계에서는 다음을 하지 않았다.

- MainWindow/pyd wrapper 수정
- `set_*.py` 또는 UI clicked/activated wrapper 수정
- `utility/setting.py` 또는 `utility/setting_base.py` DB 설정 쓰기
- `setting.db`, `strategy.db`, `*.db` 생성/수정
- Kiwoom receiver/agent/trader/strategy 파일 수정
- `trade/base_strategy.py` 수정
- `trade/formula_manager.py` 수정
- runtime `globals().update(...)` 호출
- 주문/청산 조건 변경
- LS API 의존성 추가

## 5. 검증 결과

실행한 명령:

```powershell
python -m py_compile strategy\v3k_analyzer_adapter.py strategy\v3k_settings_surface.py scripts\smoke_v3k_settings_surface.py scripts\audit_v3k_verify_1a.py
python scripts\smoke_v3k_settings_surface.py
python scripts\audit_v3k_verify_1a.py
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

- settings surface smoke 통과
- VERIFY-1A audit 통과
- formula/global facade smoke 통과
- realtime learning boundary smoke 통과
- backtest learning hook smoke 통과
- learning loader smoke 통과
- analyzer module import/field-contract smoke 통과
- analyzer adapter OFF/ON smoke 통과
- `git diff --check` 통과
- 금지 runtime artifact guard clean

## 6. 안전성 판단

이번 단계는 실제 UI/DB 연결이 아니라 contract-only 설정 surface다.

안전 장치:

- 모든 key 기본 OFF
- DB import/write 없음
- GUI wrapper import/write 없음
- Kiwoom runtime path 미수정
- runtime globals update 없음
- unknown key는 diagnostics만 남기고 무시
- VERIFY-1A audit 유지

따라서 `V3K-IMPL-6A`는 후속 UI/설정 노출 또는 최종 closure audit으로 넘어가기 위한 안전한 중간 지점이다.

## 7. 다음 단계 결정

가장 안전한 다음 단계는 `V3K-VERIFY-1B` 최종 closure audit이다.

목표:

- 2U_C V3K 목표가 실제로 어느 수준까지 달성되었는지 최종 점검한다.
- V3의 LS 제외 신기능 중 반영 완료/보류/사용자 승인 필요 항목을 다시 분류한다.
- settings surface 이후에도 MainWindow/pyd wrapper와 live runtime hook은 여전히 직접 변경하지 않았음을 확인한다.
- 최종적으로 다음 중 하나를 결정한다.
  1. 현재 V3K safe-staged 목표 완료 선언
  2. UI wrapper를 건드리지 않는 추가 smoke/문서 보강
  3. 사용자 명시 승인 후 GUI/runtime hook 별도 phase 진입

추천 OMX 명령:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
omx ralph --prd "V3K-VERIFY-1B를 시작한다. 목표는 STOM_Version_2U_C의 V3K safe-staged 구현이 개발 계획의 목적을 충족했는지 최종 closure audit으로 검증하는 것이다. V3의 LS 제외 신기능 중 반영 완료, 안전상 보류, 사용자 승인 필요 항목을 문서와 코드 근거로 재분류한다. MainWindow/pyd wrapper 직접 변경, Kiwoom receiver/order/strategy 의사결정 경로 변경, runtime globals update, core DB/DB 파일 생성/수정, LS API 의존성 추가는 금지한다. VERIFY-1A audit, settings surface smoke, 기존 V3K smoke 전체, forbidden artifact guard, release sync, docs/registry 갱신, 한국어 commit까지 수행하고 다음 단계가 필요한지 결론을 낸다."
```

## 8. 진행률 갱신

전체 V3 도입 → V3U → 2U_C V3K 목표 기준:

- V3/V3U 공식 준비: 완료
- 2U_C V3K 설계: 완료
- analyzer adapter/staging: 완료
- backtest learning loader/hook: 완료
- realtime learning boundary: 완료
- formula/global facade: 완료
- OFF regression/untouched audit: 완료
- settings surface contract: 완료
- 남은 작업: final closure audit, 사용자 승인 필요 항목 분리

현재 추정 전체 진행률: 약 98%.
