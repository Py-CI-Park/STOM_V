# V3K-VERIFY-1A: OFF 회귀 및 Kiwoom untouched audit

- 작성일: 2026-05-09 KST
- 브랜치/워크트리: `STOM_Version_2U_C` / `C:\System_Trading\STOM\STOM_V.wt-dev`
- 상위 목표: `2U_C = V3 신기능 + Kiwoom 유지`
- 검증 기준 범위: `090421c167be26b1a5d2c4ec55023f5f5064058a..HEAD`
- 상태: audit/smoke 통과, 커밋 후 release sync 재확인 필요

## 1. 사용자 요청/프롬프트 맥락

이번 단계는 다음 목적의 검증 단계다.

> 2U_C의 V3 기능을 개발 계획에 작성했던 문서에 따라 목적을 달성한다.  
> Kiwoom증권을 유지한 채 V3의 신기능을 2U_C에 반영한다.  
> 각 단계는 commit으로 체계적으로 관리하고 전체 계획/현재 단계/남은 단계를 문서화한다.  
> 지금까지 추가한 analyzer adapter, analyzer module staging, backtest learning hook, realtime learning boundary, formula/global facade가 feature flag 기본 OFF에서 기존 Kiwoom 유지 runtime에 영향을 주지 않는지 종합 검증한다.

## 2. 이번 단계의 목적

`V3K-IMPL-2A`부터 `V3K-IMPL-5`까지의 구현은 모두 feature flag 기본 OFF와 no-op/dry-run을 원칙으로 진행되었다. 그러나 다음 단계에서 UI/설정 노출 또는 runtime dry-run hook을 검토하기 전에 다음 사실을 증거화해야 한다.

1. Kiwoom receiver/order/strategy 의사결정 경로가 수정되지 않았다.
2. `trade/base_strategy.py`, `trade/formula_manager.py`에 V3K runtime 주입이 없다.
3. V3K feature flags는 기본 OFF다.
4. formula/global facade는 기본 OFF에서 globals를 만들지 않는다.
5. `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph` 산출물이 생성/수정되지 않았다.
6. V3K Python 코드에 LS API 의존 marker가 없다.
7. 기존 V3K smoke 전체가 계속 통과한다.

## 3. 추가한 검증 도구

### `scripts/audit_v3k_verify_1a.py`

VERIFY-1A 전용 audit script를 추가했다.

검사 항목:

- V3K 시작 commit 자동 탐색
  - 시작 subject: `V3K 설계 문맥을 2U_C 구현 lane에 고정한다`
  - base ref: 해당 commit의 parent
- base ref 이후 변경 파일 목록 수집
- 금지 runtime/artifact 경로 변경 여부 검사
- Kiwoom/runtime path 내부 `v3k_` 또는 `V3K` 참조 검사
- V3K feature flags 기본 OFF 검사
- formula/global facade 기본 OFF no-op 검사
- 금지 runtime artifact status 검사
- Python 코드의 LS dependency marker 검사

1차 작성 시 문서의 “LS API 제외/금지” 문구까지 dependency marker로 잡는 오탐이 있었다. 따라서 LS marker 검사는 Python 코드 파일로 한정하도록 보정했다. 문서가 LS API를 “제외 대상”으로 기록하는 것은 정책상 정상이다.

## 4. audit 결과

실행 명령:

```powershell
python -m py_compile scripts\audit_v3k_verify_1a.py
python scripts\audit_v3k_verify_1a.py
```

결과 요약:

```text
V3K VERIFY-1A base ref: 090421c167be26b1a5d2c4ec55023f5f5064058a
V3K changed files audited: 32
Kiwoom/runtime untouched audit passed
V3K feature flags default-OFF audit passed
Forbidden artifact guard passed
LS dependency marker audit passed
v3k verify-1a audit passed
```

커밋 후에는 이번 audit script와 본 문서가 V3K changed files에 포함되므로 변경 파일 수는 증가할 수 있다. 중요한 기준은 금지 경로와 runtime side-effect가 없는지다.

## 5. 전체 검증 결과

실행한 명령:

```powershell
python -m py_compile scripts\audit_v3k_verify_1a.py strategy\v3k_analyzer_adapter.py strategy\v3k_formula_facade.py scripts\smoke_v3k_formula_facade.py scripts\smoke_v3k_realtime_learning_boundary.py scripts\smoke_v3k_backtest_learning_hook.py scripts\smoke_v3k_learning_loader.py scripts\smoke_v3k_analyzer_modules.py scripts\smoke_v3k_analyzer_adapter.py scripts\diff_v3_vs_2uc_db_schema.py scripts\init_v3k_shadow_db.py scripts\v3k_db_health.py
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

- py_compile 통과
- VERIFY-1A audit 통과
- formula/global facade smoke 통과
- realtime learning boundary smoke 통과
- backtest learning hook smoke 통과
- learning loader smoke 통과
- analyzer module import/field-contract smoke 통과
- analyzer adapter OFF/ON smoke 통과
- `git diff --check` 통과
- 금지 runtime artifact guard clean

`verify_release_sync.py --root C:\System_Trading\STOM\STOM_V.wt-dev`는 커밋 전에는 새 audit script가 untracked라서 clean 조건 메시지를 냈다. 이는 의도된 변경 파일을 커밋하기 전의 상태이며, 커밋 후 반드시 재실행한다.

## 6. 안전성 판단

VERIFY-1A 기준으로 다음을 확인했다.

- Kiwoom stock runtime path는 V3K 구현 범위에서 untouched다.
- `trade/base_strategy.py`와 `trade/formula_manager.py`에 V3K runtime 주입이 없다.
- V3K flags는 기본 OFF다.
- formula/global facade는 기본 OFF에서 globals를 생성하지 않는다.
- Backtest hook은 feature flag OFF에서 no-op이고 ON missing-DB에서도 read-only diagnostics만 만든다.
- Realtime learning boundary도 feature flag OFF에서 no-op이고 ON missing-DB에서도 DB를 만들지 않는다.
- analyzer module staging은 import/field contract 검증까지만 수행되며 runtime constructor 연결은 없다.

따라서 지금 상태는 다음 단계로 넘어가기 위한 안전 기준을 만족한다.

## 7. 다음 단계 결정

가장 안전한 다음 단계는 바로 live runtime hook을 추가하는 것이 아니라 `V3K-IMPL-6A`다.

권장 목표:

- V3K feature flags와 분석/학습 상태를 UI/설정에 노출하기 위한 **비침투적 설정 surface**를 준비한다.
- MainWindow/pyd wrapper를 직접 바꾸기 전, 설정 key contract와 smoke를 먼저 만든다.
- 기본값은 모두 OFF여야 한다.
- DB 생성, Kiwoom order/receiver path 변경, runtime globals update는 계속 금지한다.

추천 OMX 명령:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dev
omx ralph --prd "V3K-IMPL-6A를 시작한다. 목표는 STOM_Version_2U_C에서 Kiwoom증권을 유지한 채 V3K analyzer/learning/formula feature flags를 UI/설정에 노출하기 전의 비침투적 설정 surface와 contract smoke를 준비하는 것이다. MainWindow/pyd wrapper 직접 변경, Kiwoom receiver/order/strategy 의사결정 경로 변경, runtime globals update, core DB/DB 파일 생성/수정, LS API 의존성 추가는 금지한다. 기본값은 모두 OFF로 유지하고, 설정 key contract와 smoke, VERIFY-1A audit 재실행, 기존 V3K smoke, forbidden artifact guard, release sync, docs/registry 갱신, 한국어 commit까지 수행한다."
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
- 남은 작업: UI/설정 surface, 선택적 runtime dry-run hook, 최종 검증/종료 보고

현재 추정 전체 진행률: 약 96%.

## 9. post-commit self-scan ??

VERIFY-1A ?? ?? ? audit script? V3K ?? ??? ?????, script ??? `FORBIDDEN_TEXT_PATTERNS` ?? ??? ??? LS dependency marker? ???? self-scan ??? ?????. ?? LS API ???? ??? ?? ???, audit script ??? marker ?? ??? LS dependency scan ???? ????? ????.

?? ? ?? ???? ?? ??:

```powershell
python -m py_compile scripts\audit_v3k_verify_1a.py
python scripts\audit_v3k_verify_1a.py
python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py --root C:\System_Trading\STOM\STOM_V.wt-dev
```
