# V3K 완전 기능 이행 목표 재정의 및 실행 계획

작성일: 2026-05-08 KST
대상 root lane: `STOM_Version_2`
실제 구현 목표 lane: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
관련 기준 commit: `c9dec9a4d3d5080e8134a4da866125eca36dea5d`, `94d92787d38db897aae444682ced0fd6828b761a`, `70a8962e861821af7c2c15f97f7402316e8cf810`

## 1. 목적 재정의

이 문서는 `c9dec9a4d3d5080e8134a4da866125eca36dea5d` 이후 진행된 V3/V3U/2U_C 문서와 backport 작업을 재해석하고, 사용자의 현재 목표를 정확히 달성하기 위한 기준을 새로 고정한다.

현재 사용자의 목표는 단순한 safe micro-candidate 백포트가 아니다.

```text
최종 목표:
STOM_Version_2U_C에서 Kiwoom증권을 유지한 채,
V3의 LS증권 직접 의존성을 제외한 신기능을 가능한 한 모두 적용한다.

포함 범위:
- V3 학습/분석 시스템
- V3 학습 데이터 DB 구조
- 백테스트에서 학습 데이터를 백테스트 일자 이전 기준으로 사용하는 기능
- 실시간 거래에서 학습 데이터를 사용하는 기능
- AnalyzerRisk 외 V3 analyzer 계열
- V3 backtest/strategy/trade runtime wiring 중 LS증권 직접 의존성이 아닌 부분
- V3 DB 변경 중 2U_C/Kiwoom에 필요한 schema/adapter/migration
```

따라서 기존 문서의 `no-more-safe-candidates`는 다음 의미로만 해석한다.

```text
올바른 해석:
기존 안전 기준을 통과한 micro-candidate 후보는 모두 처리되었다.

잘못된 해석:
V3의 LS증권 제외 신기능이 2U_C에 모두 반영되었다.
```

즉, 기존 closure 문서는 틀린 것이 아니라 **범위가 좁은 종료 선언**이다. 현재 목표를 완벽히 달성하려면 `V3K`라는 별도 전환 트랙이 필요하다.

## 2. 용어 고정: V3K

혼동을 막기 위해 기존 연구 문서의 `DESIGN-LS` / `LS-IMPL` 명칭은 더 이상 사용하지 않는다. 여기서 `LS`는 Learning System 의도로 쓰였지만, 이 프로젝트에서는 `LS증권`과 혼동된다.

새 명칭:

```text
V3K = V3 기능 + Kiwoom 유지

V3K-DESIGN-# = 설계/검증 사양 단계
V3K-IMPL-#   = 구현 단계
V3K-VERIFY-# = 검증/승격 단계
```

이후 문서와 commit은 가능하면 `V3K` 명칭을 사용한다.

## 3. 기존 작업 판정

### 3.1 잘못된 것은 무엇인가

아래 판단은 잘못이다.

```text
2U_C는 V3의 LS증권 변경만 제외한 모든 신기능을 이미 반영했다.
```

실제 상태는 `94d92787` 문서가 지적한 것처럼 다음에 가깝다.

```text
V3 신기능 전체 반영률: 낮음
표면 버그/표시/의존성/guard: 일부 반영
학습/분석/백테스트 학습/실시간 학습/DB 학습 구조: 대부분 미반영
```

### 3.2 잘못되지 않은 것은 무엇인가

기존 BP-002A~BP-011A 작업은 목적이 좁았다.

```text
목적:
LS API, DB migration, pyd/UI broad merge 없이 안전하게 가져올 수 있는 V3 조각만 반영
```

이 목적에서는 기존 작업이 유효하다. 다만 지금의 최종 목표를 달성하기에는 부족하다.

### 3.3 commit 압축/rewriting 여부

현재 기본 원칙은 commit history rewrite가 아니다.

```text
금지/비추천:
- git rebase
- git reset --hard
- squash를 위한 history rewrite
- 공식 V2 lane의 기존 commit 재작성
```

정리 방식은 다음을 사용한다.

```text
권장:
- corrective checkpoint commit 추가
- 목표 재정의 문서 추가
- 기존 closure 문서를 “safe micro-candidate 종료”로 재해석
- V3K-DESIGN 트랙을 새로 시작
```

## 4. V3K 목표 범위

### 4.1 반드시 포함할 영역

| 영역 | 목표 |
| --- | --- |
| V3 analyzer modules | V3의 학습/분석 모듈을 2U_C 구조로 이식 |
| AnalyzerRisk | dormant 보존에서 runtime 후보로 승격 검토 |
| 학습 DB | V3 학습 데이터 구조를 2U_C에 적용하기 위한 schema/adapter/migration 설계 |
| 백테스트 학습 데이터 | 백테스트 기준일 이후 데이터 누수 없이 이전 학습 데이터만 로드 |
| 실시간 학습 데이터 | Kiwoom 실시간 거래 흐름을 막지 않는 sidecar/advisory 방식부터 적용 |
| DB migration | 기존 `_database` 보호 + V3 호환 schema 적용 경로 설계 |
| strategy/runtime wiring | 기존 전략/거래 흐름에 feature flag와 adapter로 연결 |
| UI/분석 화면 | MainWindow/pyd wrapper를 깨지 않는 별도 dialog 또는 최소 UI로 시작 |

### 4.2 제외할 영역

| 영역 | 제외 이유 |
| --- | --- |
| LS증권 REST/TR/REAL 직접 의존성 | 2U_C는 Kiwoom 유지 lane |
| V3 공식 lane 변경 | `STOM_Version_3`는 upstream 보존 lane |
| V3U pyd-free 구현 자체 | 이미 `STOM_Version_3U`에서 완료된 별도 lane |
| `STOM_Version_3U_C` 생성 | 현재 만들지 않는 원칙 유지 |
| 무검증 live trading wiring | 실거래 영향이 크므로 mock/spec/feature flag 전 필수 금지 |

## 5. V3 DB 적용 원칙

사용자 목표에는 “데이터베이스도 V3로 적용”이 포함된다. 다만 이것은 기존 `_database`를 즉시 덮어쓴다는 뜻으로 실행하면 위험하다.

따라서 V3K에서 DB 적용은 다음 순서로 정의한다.

```text
1. V3 DB schema와 2U_C DB schema를 비교한다.
2. V3 학습/분석에 필요한 테이블/컬럼/PK/index를 식별한다.
3. 기존 2U_C `_database`를 보호한다.
4. shadow/adapter schema 또는 `_learning_database`로 먼저 검증한다.
5. migration script, backup, rollback, healthcheck를 만든다.
6. 검증 통과 후 2U_C runtime에서 V3 호환 DB 경로를 사용한다.
```

즉, **V3 DB는 적용 대상**이지만, 적용은 migration spec과 rollback을 갖춘 방식이어야 한다.

## 6. 실행 단계

### Phase 0 — 목표/계약 고정 (`V3K-DESIGN-0`)

산출물:

```text
- V3.0~V3.18 LS 제외 기능 전체 목록
- “반영 완료 / 부분 반영 / 미반영 / 제외” 재분류표
- V3K 용어/범위/금지선
- 2U_C Kiwoom 유지 계약
- DB 적용 원칙
```

종료 조건:

```text
코드 변경 0건
문서 합의 완료
2U_C mirror 완료
```

### Phase 1 — DB/학습 데이터 설계 (`V3K-DESIGN-1`)

산출물:

```text
- V3 DB schema diff
- 2U_C DB schema diff
- 학습 DB/table/adapter/migration spec
- backup/rollback plan
- healthcheck command spec
```

종료 조건:

```text
기존 `_database`를 변경하지 않고 dry-run으로 V3 학습 DB 구조 생성 가능
```

### Phase 2 — Analyzer 이식 설계 (`V3K-DESIGN-2`)

산출물:

```text
- V3 analyzer별 입력/출력/state 계약
- Kiwoom tick/min data shape mapping
- adapter interface
- fixture 3종: 정상/결측/이상치
```

종료 조건:

```text
Analyzer 1개를 runtime 미연결 상태로 unit test 통과 가능
```

### Phase 3 — Analyzer 구현 (`V3K-IMPL-2A~2G`)

대상 예시:

```text
- analyzer_candle_pattern
- analyzer_volume_profile
- analyzer_volume_spike
- analyzer_volatility_pattern
- analyzer_volatility_stop_take
- analyzer_microstructure
- analyzer_risk runtime adapter
```

종료 조건:

```text
각 analyzer가 2U_C fixture로 unit test 통과
runtime 기본값 OFF
```

### Phase 4 — 백테스트 학습 데이터 적용 (`V3K-IMPL-3`)

목표:

```text
백테스트 기준일 이후 데이터를 절대 읽지 않고,
기준일 이전 학습 데이터만 read-only로 로드한다.
```

필수 검증:

```text
feature flag OFF: 기존 백테스트 결과와 100% 동일
feature flag ON: 학습 데이터 사용 확인 + future data leakage 차단
```

### Phase 5 — 실시간 거래 학습 데이터 적용 (`V3K-IMPL-4`)

목표:

```text
Kiwoom 실시간 거래 흐름을 유지하면서,
학습 결과를 sidecar/advisory queue로 전달한다.
```

필수 검증:

```text
feature flag OFF: 기존 실시간 거래 흐름과 동일
feature flag ON: advisory만 활성화, 실거래 주문 경로 변경 없음
```

### Phase 6 — UI/분석 화면 (`V3K-IMPL-5`)

목표:

```text
MainWindow/pyd wrapper를 깨지 않는 별도 analysis dialog 또는 최소 UI를 구현한다.
```

### Phase 7 — 승격 검증 (`V3K-VERIFY-1`)

필수 검증:

```text
- py_compile
- unit tests
- DB healthcheck
- backtest regression OFF/ON
- mock realtime sidecar
- GUI smoke
- forbidden artifact guard
- rollback rehearsal
```

## 7. 즉시 다음 작업

현재 root `STOM_Version_2`에서 해야 할 다음 작업은 구현이 아니라 Phase 0 문서화다.

```text
다음 권장 문서:
docs/update_log/2026-05-08_v3k_phase0_design_kickoff.md
```

포함해야 할 것:

```text
1. V3.0~V3.18 LS 제외 기능 전체 inventory 재작성
2. 학습/분석/DB/backtest/realtime/UI별 목표 분해
3. 2U_C Kiwoom data shape mapping 항목 정의
4. DB migration spec 목차 작성
5. feature flag 정책 정의
6. 2U_C mirror 필요성 명시
```

## 8. 현재 문서들의 해석 규칙

| 문서 | 새 해석 |
| --- | --- |
| `2026-05-08_v3_2uc_final_closure_audit.md` | safe micro-candidate 종료 문서. V3K 목표 완료 문서가 아님 |
| `2026-05-08_v3_2uc_post_closure_status_check.md` | closure 상태 확인 문서. V3K 기능 완료 증거가 아님 |
| `2026-05-08_v3_2uc_unmet_features_audit_and_research.md` | V3K 필요성을 지적한 연구 문서. 본 문서로 명칭/목표 보정 |
| `docs/CARRY_FORWARD_REGISTRY.md` | 기존 BP 이력 + 이후 V3K 트랙의 공식 registry |

## 9. 한 줄 결론

`2U_C`에 V3 기능을 완벽히 달성하려면 기존 BP micro-backport를 반복하면 안 된다. 이제부터는 **V3K = V3 기능 + Kiwoom 유지**라는 별도 전환 트랙으로, DB/학습/분석/백테스트/실시간 학습을 설계와 검증 기반으로 적용해야 한다.
