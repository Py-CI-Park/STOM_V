# V3K-IMPL-4: 실시간 학습 데이터 사용 경계 준비

- 작성일: 2026-05-09 KST
- 브랜치/워크트리: `STOM_Version_2U_C` / `C:\System_Trading\STOM\STOM_V.wt-dev`
- 상위 목표: `2U_C = V3 신기능 + Kiwoom 유지`
- 현재 전체 단계: `V3K-IMPL` 내부의 실시간 learning-data boundary 단계
- 상태: 구현 및 smoke 검증 완료, 실제 매매 의사결정 연결은 보류

## 1. 사용자 요청/프롬프트 맥락

이번 단계는 다음 목적을 유지한다.

> 2U_C의 V3 기능을 개발 계획에 작성했던 문서에 따라 목적을 달성한다.  
> Kiwoom증권을 유지한 채 V3의 신기능, 특히 학습 데이터와 분석 기능을 2U_C에 반영한다.  
> 각 단계는 commit으로 체계적으로 관리하고 전체 계획/현재 단계/남은 단계를 문서화한다.  
> 실시간 학습 데이터 사용은 안전한 feature flag 기본 OFF, missing-DB no-op 방식으로 준비한다.

이번 커밋은 `V3K-IMPL-3B`에서 만든 backtest dry-run/no-op hook 다음 단계이다. 단, 실제 Kiwoom receiver/order/strategy 의사결정 경로에는 아직 연결하지 않는다.

## 2. 이번 단계의 목적

`STOM_Version_2U_C`에서 V3 분석/학습 기능을 실시간 경로에 반영하기 위한 **adapter-only preload boundary**를 만든다.

필수 조건은 다음과 같다.

1. `V3K_REALTIME_LEARNING_ENABLED` feature flag 기본값은 OFF다.
2. OFF 상태에서는 load 결과가 없고 diagnostics만 반환한다.
3. ON 상태에서도 `_database_v3k_shadow` 또는 학습 DB가 없으면 DB를 생성하지 않고 missing-DB diagnostics만 반환한다.
4. tick 실시간 preload에서는 `candle_pattern` 학습 DB를 제외한다.
5. min 실시간 preload에서는 `candle_pattern`을 포함한다.
6. Kiwoom 수신/주문/청산/전략 의사결정 경로는 수정하지 않는다.
7. `V3K_BACKTEST_LEARNING_ENABLED`와 `V3K_REALTIME_LEARNING_ENABLED`를 분리하여 backtest hook과 realtime preload가 서로 다른 master flag를 사용하게 한다.

## 3. 변경 사항

### 3.1 `strategy/v3k_analyzer_adapter.py`

추가된 구조:

- `RealtimeLearningPreloadRequest`
  - 실시간 preload 요청 DTO.
  - 대상 종목 코드, 기준일(`as_of_date`), 전략 구분, tick/min 여부, feature flags, limit를 가진다.
- `RealtimeLearningPreloadResult`
  - 실시간 preload 결과 DTO.
  - load 결과 묶음과 diagnostics를 가진다.
- `V3KRealtimeLearningAdapter`
  - Kiwoom runtime 파일을 import하지 않는 독립 adapter boundary.
  - 내부적으로 기존 `V3KLearningDataAdapter`를 재사용하되 master flag를 `V3K_REALTIME_LEARNING_ENABLED`로 지정한다.
  - 기본 OFF에서는 완전 no-op이다.
  - ON + missing DB에서도 DB 생성 없이 read-only skip 결과만 반환한다.

기존 변경:

- `V3KLearningDataAdapter`에 `master_flag`를 추가했다.
- 기존 backtest path는 기본값 `V3K_BACKTEST_LEARNING_ENABLED`를 계속 사용한다.
- realtime path는 `V3K_REALTIME_LEARNING_ENABLED`를 사용한다.

### 3.2 `scripts/smoke_v3k_realtime_learning_boundary.py`

신규 smoke 검증을 추가했다.

검증 항목:

1. 기본 OFF no-op
2. ON이지만 codes가 없을 때 no-op
3. ON + tick + missing DB no-op
4. ON + min + missing DB no-op
5. tick에서는 `candle_pattern` 제외
6. min에서는 `candle_pattern` 포함
7. `last_update < ?` cutoff 유지
8. `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph` 산출물 생성 없음

## 4. 명시적으로 제외한 작업

이번 단계에서는 다음을 하지 않았다.

- Kiwoom receiver/agent/trader/strategy 파일 수정
- 실시간 주문 조건 변경
- 실시간 청산 조건 변경
- `Strategy()` globals 또는 formula/global layer에 analyzer 결과 주입
- learning DB 생성
- `_database_v3k_shadow` 생성
- core DB 교체
- LS API/LS TR/LS REAL 의존성 추가
- V3 analyzer DB 클래스 constructor runtime 호출

## 5. 검증 결과

실행한 명령:

```powershell
python -m py_compile strategy\v3k_analyzer_adapter.py scripts\smoke_v3k_realtime_learning_boundary.py
python scripts\smoke_v3k_realtime_learning_boundary.py
python scripts\smoke_v3k_backtest_learning_hook.py
python scripts\smoke_v3k_learning_loader.py
python scripts\smoke_v3k_analyzer_modules.py --import-only
python scripts\smoke_v3k_analyzer_modules.py
python scripts\smoke_v3k_analyzer_adapter.py
python scripts\smoke_v3k_analyzer_adapter.py --enable-v3-risk
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph
```

결과 요약:

- `py_compile` 통과
- realtime learning boundary smoke 통과
- backtest learning hook smoke 통과
- learning loader smoke 통과
- analyzer module import/field-contract smoke 통과
- analyzer adapter OFF/ON smoke 통과
- 금지 runtime artifact status 출력 없음

`verify_release_sync.py --root C:\System_Trading\STOM\STOM_V.wt-dev`는 커밋 전에는 의도한 변경 파일 때문에 clean 조건 메시지를 냈다. 커밋 후 다시 실행하여 clean 상태를 확인해야 한다.

## 6. 안전성 판단

이번 단계는 runtime 연결이 아니라 adapter boundary 추가이므로 매매 동작을 바꾸지 않는다.

- feature flag 기본 OFF
- OFF no-op 검증 완료
- missing DB no-create 검증 완료
- Kiwoom runtime 파일 미수정
- 주문/청산 조건 미변경

따라서 `V3K-IMPL-4`는 다음 단계인 formula/global facade 준비로 넘어갈 수 있다.

## 7. 다음 단계

추천 다음 단계는 `V3K-IMPL-5`다.

목표:

- V3 analyzer output을 기존 2U_C formula/global layer가 안전하게 읽을 수 있는 facade를 만든다.
- 기본 OFF에서는 기존 전략 결과와 완전히 동일해야 한다.
- ON smoke에서도 실제 주문/청산 조건 변경은 금지하고, diagnostics 또는 isolated synthetic path까지만 허용한다.

추천 OMX 명령:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
omx ralph --prd "V3K-IMPL-5를 시작한다. 목표는 STOM_Version_2U_C에서 Kiwoom증권을 유지한 채 V3 analyzer output을 strategy formula/global layer에 연결하기 위한 facade를 feature flag 기본 OFF와 no-op 방식으로 준비하는 것이다. 주문/청산 조건 변경, Kiwoom receiver/order path 변경, core DB/DB 파일 생성/수정, LS API 의존성 반영은 금지한다. 기존 trade/formula_manager와 trade/base_strategy를 대체하지 말고 adapter/facade와 smoke를 추가하고, py_compile, realtime/backtest learning smoke, analyzer module smoke, adapter smoke, forbidden artifact guard, release sync, docs/registry 갱신, 한국어 commit까지 수행한다."
```

## 8. 진행률 갱신

전체 V3 도입 → V3U → 2U_C V3K 목표 기준:

- V3/V3U 공식 준비: 완료
- 2U_C V3K 설계: 완료
- analyzer adapter/staging: 완료
- backtest learning loader/hook: 완료
- realtime learning boundary: 완료
- formula/global facade: 다음 단계
- UI/설정 노출, DB shadow cutover, 통합 검증: 남음

현재 추정 전체 진행률: 약 91%.