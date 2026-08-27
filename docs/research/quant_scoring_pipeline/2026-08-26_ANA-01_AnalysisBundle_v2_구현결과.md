# ANA-01 — AnalysisBundle v2 schema/builder/read API 구현 결과

> 실행일: 2026-08-26
>
> 실행 브랜치: `codex/process-research-ana-01-analysis-bundle-v2`
>
> 기준선: `codex/process-research-pipeline-restart` @ `62dcef38`
>
> 연구 실행: **미수행**
>
> 보호 DB·운영 전략 DB write: **없음**

## 1. 결론

공식 legacy job 하나를 동일 입력에서 항상 같은 내용과 SHA-256으로 변환하는 `AnalysisBundle v2`의 첫 수직 슬라이스를 구현했다. 기존 `/bt/result`처럼 요청 때마다 이름 없는 분석 dict를 돌려주는 대신, identity·source·execution·decision을 포함한 strict content-addressed 계약을 제공한다.

이 번들은 기존 `Analysis Card v2/V3`나 SQLite 쓰기형 `analysis_snapshot.py`와 다른 책임이다. 기존 카드는 부검·프롬프트 피드백 도구이고, 새 bundle은 화면·연구·감사의 단일 읽기 계약이다. 이번 구현은 과거 artifact를 읽을 뿐 별도 bundle 파일이나 DB를 만들지 않는다.

## 2. 구현 범위

| 구성 | 역할 | 상태 |
|---|---|---|
| `analysis_bundle_artifacts.py` | canonical JSON·SHA-256·streaming CSV 지문 | 완료 |
| `analysis_bundle_models.py` | strict/frozen bundle schema·cross-section invariant·hash 검증 | 완료 |
| `analysis_bundle_builder.py` | legacy job + Truth + CSV를 결정적 bundle로 조립 | 완료 |
| `analysis_bundle_api.py` | `GET /analysis-bundle/job` read-only API | 완료 |
| `app.py` | 신규 router mount만 추가 | 최소 수정 완료 |
| unit/integration tests | 결정성·변조·모순·5상태·REST·missing job | 완료 |

신규 Python 모듈은 모두 250 logical LOC 이하로 분리했다. 기존 거대 `backtest_api.py`와 `backtest_analysis.py`는 수정하지 않고, 검증된 순수 분석 함수를 builder가 소비한다.

## 3. Bundle v2 계약

| 영역 | 현재 포함 내용 | 결측 표현 |
|---|---|---|
| identity | version, job, candidate, Evidence ID, source hash, identity status | 필수 |
| source | strategy snapshot hashes, legacy spec hash, CSV path/hash/size, runtime identities | 미관측 runtime identity는 `null` |
| preregistration | 정식 program/Band/Family/fold/기간/비용/seed/stop rule | legacy job은 `NOT_OBSERVED`, 전 필드 `null` |
| execution | status, cause, raw status, return code, elapsed, checkpoint, event/row/trade count, correction | 미관측은 `null` |
| metrics | 기존 summary 또는 terminal metrics | 실패는 `NOT_EVALUABLE`, 값 `{}` |
| series | equity/underwater/rolling/monthly/cumulative | CSV 없으면 `NOT_RUN` |
| distribution | PnL/holding/MAE/MFE/exit reason | CSV 없으면 `NOT_RUN` |
| episodes | 사전 정의 cohort와 trade key | 아직 `NOT_RUN` |
| attribution | heatmap/orderflow/insights | 실행 실패는 `NOT_EVALUABLE` |
| counterfactual | 방법·가정·matched/new/lost·권위 | 아직 `NOT_RUN` |
| robustness | folds/controls/FDR/posterior/plateau/power | 아직 `NOT_RUN` |
| decision | execution/economic/authority/next action/robustness | Truth와 동일 |
| evidence | artifact paths/hashes, deterministic generated_at source, generator, persistence | persistence `none` |

숫자가 없을 때 0을 합성하지 않는다. 실행 실패에는 경제 분석을 붙일 수 없고, 실행하지 않은 robustness를 실패나 성공으로 바꾸지 않는다.

## 4. 결정성·불변성

content hash는 `content_sha256` 필드 자체를 제외한 전체 bundle의 canonical JSON으로 계산한다.

| 규칙 | 구현 |
|---|---|
| key ordering | JSON key sort |
| encoding | UTF-8, compact separator, Unicode 보존 |
| non-finite number | 거부 |
| generated time | 현재 시각 금지, legacy `finished_at`만 사용; 없으면 `null` |
| source file | CSV를 chunk 단위 SHA-256·size 계산 |
| mutation | 기존 hash와 내용이 다르면 model validation 거부 |
| repeat read | 동일 record+CSV 두 번의 전체 payload와 hash가 동일 |

## 5. Fail-closed 교차 계약

| 모순 | 처리 |
|---|---|
| CSV row count ≠ Truth trade count | bundle 생성 거부 `analysis_bundle_trade_count_mismatch` |
| execution 축 ≠ decision execution | schema 거부 |
| `LEGACY_INCOMPLETE`인데 authority 승격 | schema 거부 |
| next action이 Truth 상태 기계와 다름 | schema 거부 |
| non-success에 경제 metrics 부착 | schema 거부 |
| series observed인데 CSV identity 없음 | schema 거부 |
| observed row count ≠ terminal trade count | schema 거부 |

hash를 다시 계산해 붙여도 위 의미 모순은 통과하지 않는다. 즉 content-addressing이 잘못된 의미를 정당화하지 않는다.

## 6. fixture와 실제 job 결과

### 6.1 고정 fixture

| 입력 | execution | metrics/series | 결과 |
|---|---|---|---|
| success + 3-row CSV | `SUCCESS` | `OBSERVED/OBSERVED` | 동일 bundle/hash PASS |
| no-trades | `NO_TRADES` | `NOT_EVALUABLE` | 0 KPI 합성 없음 |
| error | `ERROR` | `NOT_EVALUABLE` | 실패 원인 보존 |
| timeout | `TIMEOUT` | `NOT_EVALUABLE` | 원인 미관측 보존 |
| partial | `PARTIAL` | `NOT_EVALUABLE` | terminal metrics를 경제 결과로 사용하지 않음 |

### 6.2 현재 worktree 실제 취소 job

`20260824_232753_기존매수_73311`을 두 번 조회한 결과:

| 항목 | 관측값 |
|---|---|
| content SHA-256 | `94d5f878bb447bfe6b9075e1113f7a82035e5854c95cd6e1fd6f9abfd7c0b202` 두 번 동일 |
| execution | `CANCELLED` |
| metrics / series | `NOT_EVALUABLE / NOT_EVALUABLE` |
| authority / next action | `FEASIBILITY / REPRODUCE` |
| persistence | `none` |
| raw JSON hash | 전후 `03E52E0C8A1F05A94B60EC99411E5B423B3B72D41D08AB6CC6FA754E392B8FE1` 동일 |

## 7. 검증 영수증

| 검증 | 결과 |
|---|---|
| ANA-01 집중 schema/builder/API | `10 passed` |
| Truth·bundle·기존 분석·result identity·analysis card·security 통합 | `219 passed` |
| no-excuse rules, 신규 6개 Python 파일 | `0 violations` |
| Ruff | `All checks passed` |
| basedpyright error level | `0 errors, 0 warnings, 0 notes` |
| 실제 job repeat read | payload/hash 동일, raw artifact hash 불변 |

전체 unit suite는 UX-01 결과 문서에 기록한 provisioning 경계 때문에 실행하지 않았다. 관련 분석·보안 회귀는 모두 통과했으며 누락 인프라를 PASS로 간주하지 않는다.

## 8. 범위 밖과 현재 한계

| 항목 | 현재 상태 | 이유/다음 처리 |
|---|---|---|
| generation bundle | **미지원** | generation 행에 코드 hash와 engine/config/data identity가 없어 source identity를 꾸미지 않음 |
| immutable 파일 저장 | 미수행 | ANA-01은 content-addressed read view; persistence `none` |
| episode cohort/trade key | `NOT_RUN` | ANA-02/분석 페이지 단계에서 사전 정의 |
| counterfactual | `NOT_RUN` | advisory/official 권위 계약 후 연결 |
| folds/controls/FDR/posterior | `NOT_RUN` | 실제 연구 실행 전 값을 합성하지 않음 |
| Result Overview UI | 기존 `/bt/result` 사용 | 다음 UX-02에서 bundle API로 재배선 |

generation을 억지로 지원하지 않은 것은 기능 실패가 아니라 provenance fail-closed 경계다. 향후 generation passport나 code snapshot이 source hash를 제공할 때 별도 adapter로 확장한다.

## 9. 다음 원자 단위

다음은 `UX-02 — Result Overview bundle 기반 재배선`이다. 기존 차트를 제거하지 않고 상단 Overview가 bundle의 다음 필드를 먼저 읽게 한다.

1. identity와 `LEGACY_INCOMPLETE` 표시
2. execution completeness와 failure cause
3. metrics/series/episode/robustness capability matrix
4. economic·authority·next action과 차단 사유
5. bundle hash·artifact hash·persistence
6. success/no-trades/error/timeout/partial 실제 브라우저 QA
