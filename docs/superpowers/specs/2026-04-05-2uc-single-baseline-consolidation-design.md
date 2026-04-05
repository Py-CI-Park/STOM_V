# 2U_C 단일 기준선 통합 설계

## 목적

`STOM_Version_2U_C_CLI_v267`에 누적된 custom/CLI/runtime 변경을 최종적으로 `STOM_Version_2U_C`에 흡수하여, `2U_C`를 코드·CLI·문서·운영 규칙의 단일 기준선으로 재정의한다. 통합이 끝나면 `CLI_v267`는 더 이상 운영상 필수 레인이 아니며, 전파 체계도 `V2 -> 2U -> 2U_C -> research/init`으로 단순화한다.

## 배경

현재 live mapping은 `V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`을 전제로 한다. [CLAUDE.md](C:/System_Trading/STOM/STOM_V.wt-dev/CLAUDE.md)와 [UPSTREAM_SYNC_STRATEGY.md](C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md)는 `CLI_v267`를 `2U_C`의 downstream CLI 레인으로 정의한다.

하지만 실제 개발 이력은 단순한 하위 feature 레인이 아니라 장기 분기 상태다.

- 공통 조상 이후 `2U_C`는 54커밋, `CLI_v267`는 166커밋 독자 진행했다.
- `CLI_v267`는 `cli/` 패키지, auto-discovery, 서브커맨드, 테스트, 문서를 대규모로 소유한다.
- 동시에 `backtest`, `utility`, `ui`의 공용 런타임 파일도 `CLI_v267`에서 후속 수정되었다.
- `2U_C`에도 텔레그램/웹크롤링/비정식 워크트리 가드레일 등 후행 안정화 커밋이 존재한다.

즉, 현재 상태는 “하위 레인을 계속 유지”하는 것보다 “`CLI_v267`의 실질 내용을 `2U_C`로 흡수한 새 기준선”으로 재편하는 편이 목표와 더 잘 맞는다.

## 범위

이번 통합 설계는 아래 범위를 포함한다.

- `STOM_Version_2U_C_CLI_v267`의 코드/문서/테스트를 `STOM_Version_2U_C`에 흡수
- `cli/` 패키지 및 CLI 관련 진입점의 공식 소유권을 `2U_C`로 이동
- `2U_C`와 `CLI_v267` 사이 공용 런타임 차이의 수동 재조정
- `AGENTS.md`, `CLAUDE.md`, `docs/WORKTREE_STRATEGY.md`, `docs/UPSTREAM_SYNC_STRATEGY.md`의 운영 규칙 갱신
- `wt-dev`의 기본 작업 기준과 전파 체인 재정의

## 비목표

- 업스트림 `V2` 또는 `2U` 정책의 변경
- `research/init`의 역할 확대
- `backtest/graph/`를 소스 자산으로 승격
- CLI 기능을 별도 패키지로 재분리하는 신규 아키텍처 도입

## 현재 상태 요약

### 브랜치 역할

- `STOM_Version_2U_C`는 커스텀 통합 레인이다.
- `STOM_Version_2U_C_CLI_v267`는 현재 CLI 계약과 운영 호환성을 보존하는 downstream 레인이다.
- `research/init`은 formal research downstream 레인이다.

### 확인된 drift

- 두 브랜치 간 변경 파일 수가 크고, 공용 핵심 파일 충돌이 다수 예상된다.
- merge simulation 기준으로 직접 충돌 파일이 19개다.
- 충돌 파일에는 `backtest/back_static.py`, `backtest/backengine_base.py`, `backtest/backtest.py`, `utility/telegram_bot.py`, `utility/webcrawling.py`, `ui/ui_mainwindow.py`가 포함된다.

### 현재 검증 상태

- `verify_nonrelease_sync.py`는 `wt-dev`와 `wt-2uc`에서 모두 통과한다.
- `wt-dev`의 `python -m pytest tests/unit/ -q`는 `test_backtest_result_expansion.py` 1건 실패 상태다.
- `wt-2uc`의 `python -m pytest tests/unit/ -q`는 `test_ui_jisu_cleanup.py` 1건 실패 상태다.

통합 완료 판정에는 기존 실패를 포함한 전체 검증 복구가 필요하다.

## 접근안 비교

### 1. `CLI_v267 -> 2U_C` 직접 대형 merge

- 장점: 절차가 짧다.
- 단점: feature merge가 아니라 장기 분기 재통합이다.
- 단점: 공용 핵심 파일 충돌과 누락 검증 부담이 크다.
- 단점: 실패 시 롤백과 원인 분리가 어렵다.

### 2. `2U_C` 기준 통합 브랜치에서 `CLI_v267` 흡수 후 `2U_C` 승격

- 장점: 추천안이다.
- 장점: 최종 기준선 이름과 부모 레인 역할을 `2U_C`에 유지할 수 있다.
- 장점: 코드 실질 내용은 `CLI_v267`를 채택하면서도 `2U_C` 후행 안정화 커밋을 보존할 수 있다.
- 장점: 통합 후 전파 체계를 `V2 -> 2U -> 2U_C -> research/init`으로 단순화할 수 있다.
- 단점: 통합 직후 문서와 운영 규칙을 함께 재작성해야 한다.

### 3. `CLI_v267`를 새 기준 브랜치로 승격하고 `2U_C`를 retire

- 장점: 코드 기준선만 보면 직관적이다.
- 단점: 문서, 전파 체계, 워크트리 역할 설명을 더 크게 흔든다.
- 단점: `2U_C`를 canonical parent로 보는 현재 운영 모델과 충돌한다.

## 추천안

추천은 **접근안 2**다.

핵심 원칙은 다음과 같다.

- 최종 기준선은 `STOM_Version_2U_C` 하나로 둔다.
- 통합 작업은 `2U_C`에서 만든 일회성 통합 브랜치에서 수행한다.
- 코드 기준은 `CLI_v267`를 우선 채택한다.
- 다만 `2U_C`에만 존재하는 후행 안정화 수정은 버리지 않고 수동 재주입한다.
- 통합 완료 후 `CLI_v267`는 retire 대상이 되며, 더 이상 운영상 필수 레인이 아니다.

## 목표 상태

통합 이후 저장소의 목표 상태는 다음과 같다.

- `STOM_Version_2U_C`가 custom + CLI + runtime + docs + tests의 단일 기준선이다.
- `cli/` 패키지, CLI 테스트, CLI 문서는 모두 `2U_C`가 공식 소유한다.
- `wt-dev`의 기본 작업 기준은 `2U_C`다.
- `CLI_v267`는 역사 보존용 브랜치로만 남기거나 retire 표기를 남긴다.
- 전파 체인은 `V2 -> 2U -> 2U_C -> research/init`이다.
- `backtest/graph/`는 계속 보호된 결과 데이터다.

## 통합 브랜치 모델

통합 작업은 아래 브랜치 모델을 사용한다.

1. 시작점은 `STOM_Version_2U_C`
2. 여기서 `integration/adopt-cli-v267-into-2uc` 같은 일회성 통합 브랜치를 생성한다.
3. 이 브랜치에 `STOM_Version_2U_C_CLI_v267`를 흡수한다.
4. 검증이 끝나면 통합 브랜치를 `STOM_Version_2U_C`에 머지한다.
5. 이후 `wt-dev`의 기본 작업 브랜치도 `STOM_Version_2U_C`로 맞춘다.
6. `CLI_v267`는 retire 표기 또는 보관 전용 상태로 전환한다.

## 통합 원칙

### 기본 채택 원칙

- 내용 우선순위는 `CLI_v267`
- 기준선 소유권은 `2U_C`

즉, “브랜치는 `2U_C`를 유지하되, 실질 내용은 `CLI_v267`를 채택한 새 `2U_C`”가 목표다.

### 파일군별 충돌 처리 원칙

#### 1. CLI 전용 표면

아래는 기본적으로 `CLI_v267`를 채택한다.

- `cli/`
- CLI 전용 테스트
- CLI 전용 문서
- CLI 런처/배치/보조 스크립트

#### 2. 공용 커스텀 런타임 파일

아래는 `CLI_v267`를 베이스로 삼고, `2U_C` 후행 안정화 누락분만 수동 재적용한다.

- `backtest/back_static.py`
- `backtest/backengine_base.py`
- `backtest/back_subtotal.py`
- `backtest/backtest.py`
- `utility/setting.py`
- `utility/setting_base.py`
- `utility/lazy_imports.py`
- `utility/telegram_bot.py`
- `utility/webcrawling.py`
- `ui/ui_mainwindow.py`

#### 3. 메타 문서

아래 문서는 어느 한쪽을 그대로 채택하지 않고 통합 이후 목표 상태에 맞게 새로 쓴다.

- `AGENTS.md`
- `CLAUDE.md`
- `docs/WORKTREE_STRATEGY.md`
- `docs/UPSTREAM_SYNC_STRATEGY.md`

#### 4. 보호 데이터

- `backtest/graph/`는 끝까지 통합 입력에서 제외한다.
- 결과 데이터 존재 여부는 drift 근거가 아니라 운영 산출물로 취급한다.

## 2U_C 후행 안정화 재주입 체크리스트

`CLI_v267`를 베이스로 삼더라도 아래 범주의 `2U_C` 후행 수정은 누락 여부를 반드시 점검한다.

- 텔레그램 런타임 계약 복구
- 웹크롤링 timeout / legacy compatibility
- 비정식 워크트리 시리얼키 차단 정책
- non-release sync guardrails
- 최근 런타임 회귀 수정

이 항목은 파일 단위 diff뿐 아니라 계약 단위로도 확인한다.

## 실행 단계

### 1단계: 코드 통합

- 통합 브랜치 생성
- `CLI_v267` 흡수
- 충돌 파일 정리
- `CLI_v267` 우선 채택 원칙 적용

### 2단계: 안정화 재주입

- `2U_C` 전용 후행 안정화 수정 누락 점검
- 공용 런타임 계약 재정렬
- 현재 알려진 unit 실패 원인 제거

### 3단계: 운영 재정의

- 브랜치 역할 문서 갱신
- 전파 체계 문서 갱신
- `wt-dev` 기본 작업 기준 변경
- `CLI_v267` retire 정책 문서화

## 검증 기준

통합 완료의 검증 기준은 다음과 같다.

### 계약 검증

- `python scripts/verify_nonrelease_sync.py` 통과

### 테스트 검증

- `python -m pytest tests/unit/ -q` 통과

### 보호 경계 검증

- `backtest/graph/`는 여전히 비전파 결과 데이터로 유지
- `.pyd` 비재도입
- 시리얼키 비재도입
- 텔레그램 qlist / runtime wiring / webcrawling 계약 유지

### 문서 검증

아래 문서가 모두 새 목표 상태와 일치해야 한다.

- `AGENTS.md`
- `CLAUDE.md`
- `docs/WORKTREE_STRATEGY.md`
- `docs/UPSTREAM_SYNC_STRATEGY.md`

### 운영 검증

- 전파 체인이 문서상과 실제 운영상 모두 `V2 -> 2U -> 2U_C -> research/init`
- `2U_C`가 custom + CLI + docs + tests의 단일 기준선
- `CLI_v267`가 더 이상 운영상 필수 레인이 아님

## 완료 정의

이번 통합 작업의 완료 정의는 아래와 같다.

- `2U_C`가 코드, CLI, 문서, 테스트, 전파 전략을 모두 소유하는 단일 기준선이 된다.
- `verify_nonrelease_sync`와 `tests/unit`가 모두 통과한다.
- 기존 양쪽 브랜치에 존재하던 unit 실패가 해소된다.
- `CLI_v267`는 retire 대상이 되며, 운영상 필수 레인이 아니다.

## 위험 요소

### 1. 공용 파일 덮어쓰기 위험

`CLI_v267` 우선 채택 과정에서 `2U_C`의 최근 안정화 수정이 사라질 수 있다. 이 위험 때문에 공용 핵심 파일은 무조건 자동 채택하지 않고 체크리스트 기반 수동 감사를 넣는다.

### 2. 문서-운영 불일치 위험

코드만 통합하고 문서를 갱신하지 않으면 이후 작업자가 잘못된 전파 체계를 따를 수 있다. 문서 갱신은 부수 작업이 아니라 완료 조건에 포함된다.

### 3. 기존 실패 방치 위험

현재 양 브랜치에 이미 unit 실패가 있으므로, 이를 “기존 문제”로 남기고 통합 완료를 선언하면 기준선 승격 의미가 없다. 기존 실패도 통합 범위에서 복구해야 한다.

## 성공 판정

성공은 “머지가 되었다”가 아니라 다음 상태다.

- `STOM_Version_2U_C` 하나만 보면 custom/CLI/runtime/docs/tests 운영 판단이 가능하다.
- `wt-dev`에서도 `2U_C`를 기본 기준으로 바로 작업할 수 있다.
- `CLI_v267`가 없어도 downstream `research/init`까지의 전파와 유지보수 절차가 성립한다.
