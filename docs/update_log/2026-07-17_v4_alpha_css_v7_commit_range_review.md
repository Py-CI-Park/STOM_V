# 2026-07-17 V4·Alpha Lab·CSS_V7 커밋 범위 상세 검토 보고서

## 0. 결론

- 최종 검토 기준점: `673757b21e6e53aaf47d500f2b41fec9090ddb5a`
- 최초 요청 범위: `990136c430b35e00d1a911528920ee3e3d70242a~1..0a0ecca5cfde45d6d69ddf1fdd4e67ce15b2b28a`
- 확장 검토 범위: 위 시작점부터 `0a92c3278b2efc6ecae6a0f15fa0611b3fb23d64`, 이후 `673757b2`까지
- 종합 판정: **BLOCK / REQUEST CHANGES**

V4 기본 승격, History 패널 포팅, Alpha Lab 이력 병합, 읽기 전용 Alpha API와 V4 탭 배선, CSS_V7 과거 연구 기록 편입 자체는 확인됐다. 그러나 다음 세 영역에 승인 차단 문제가 남는다.

1. V4 기본 화면의 `/runs` 중복 요청, 안전·UX 검증 누락, 파리티 가드와 캐시 계약의 허점이 해소되지 않았다.
2. Alpha 탭이 실제 `rho_gate_*`·`rho_retrial_*` 영수증 이름과 스키마를 읽지 않아 등록·엔진·최종 판정을 잘못된 0 또는 구판정으로 표시한다.
3. CSS_V7 리페어 도구가 정상 1인자 호출의 의미를 제거하거나 중첩 호출을 문법 오류로 만들고, 그 결과를 DB에 먼저 커밋할 수 있다. 또한 CSS 최종 원장은 승인된 판정 프로토콜과 충돌한다.

현재 상태는 코드·연구 이력의 보존에는 의미가 있지만, 화면 수치를 연구 정본으로 사용하거나 CSS 리페어 도구를 범용 DB 수정기로 재사용하기에는 안전하지 않다.

## 1. 검토 범위와 제외 범위

### 1.1 포함

| 구분 | 대상 |
|---|---|
| V4 승격·성능 | `app.py`, legacy/V4 셸, History 포팅, 정적 캐시, `/runs` 디듀프 |
| 재발 방지 | 셸 파리티 테스트, 라우팅·캐시·대시보드 테스트 |
| Alpha 통합 | PR #108 병합, `alpha_lab/`, `alpha_api.py`, V4 Alpha 탭, 연구·이관 문서 |
| CSS_V7 | call-arity 리페어 도구, 단위 테스트, revival/validation/provenance JSONL, 결과 문서 |
| 검증 | 집중 pytest, 대시보드 pytest, 번들 해시, JSONL 파싱, 재현용 edge case, `git diff --check` |

### 1.2 제외

검토 당시 Git 추적 파일의 미커밋 변경은 없었지만 미추적 항목은 약 330개였다. `.gjc/`, `.omo/`, `artifacts/`의 미추적 파일 전체는 전수검토하지 않았다. 본 보고서의 판정은 커밋된 소스·문서와 직접 관련된 일부 미추적 증거 확인에 한정한다. 미추적 자료가 커밋된 계약을 자동으로 수정하거나 승인 근거로 승격시키지는 않는다.

## 2. 긍정적으로 확인된 사항

| 항목 | 결과 |
|---|---|
| `/ui` 기본 V4 전환 | 기본 selector가 V4 graph-first 셸을 반환 |
| legacy/V3 선택 | 명시적 query selector로 분리 |
| History 포팅 | History 트리, A/B 비교, Cell Heatmap, Holdout Funnel이 `V4History`에 마운트 |
| 딥링크 | 검토된 경로 매핑은 정상 |
| 번들 | 현재 번들 SHA 앞 8자리와 manifest가 일치 |
| Alpha API 쓰기 경계 | 추가된 `/api/alpha/*`는 GET/read-only 라우트 |
| Alpha 셸 배선 | `alpha_router`와 `V4Alpha`가 실제 앱·번들에 연결 |
| Alpha 이력 보존 | 일반 merge로 연구 브랜치 DAG 이력 보존 |
| CSS 원본 보존 | `_FIXCALL` 신규 행을 사용해 원본 전략 행을 덮어쓰지 않는 방향 |
| CSS 기본 모드 | `--apply` 없는 기본 실행은 DB dry-run |
| CSS JSONL 문법 | revival 19행, validation 45행, provenance 42행이 JSON으로 파싱됨 |

## 3. V4 대시보드 판정

### 3.1 `/runs` 중복 요청이 화면 단위로 남음 — High

`dashboard-v4-shell.jsx`는 실행 선택기용 `/runs`를 요청한다. 기본 Live 화면에 항상 렌더되는 `EvolutionAnalysisPanel`도 `evolution-analysis.jsx`에서 독립적으로 `/runs`를 요청한다. History의 `ResearchRecordsPanel` 등도 별도 소비자다.

따라서 개별 effect의 `liveState.run_id/status` 의존성을 제거한 것은 같은 소비자의 반복 요청을 줄였을 뿐, 페이지 전체의 대형 `/runs` 공유·디듀프를 완료하지 않았다. 감사 문서의 “유휴 1회, 실행 중 최대 2회” 주장은 기본 V4 화면에서도 일반적으로 성립하지 않는다.

완료 조건은 base URL과 refresh epoch 기준의 공용 run-list 자원을 셸 또는 공용 캐시에 두고, 하위 패널이 같은 데이터를 소비하도록 만드는 것이다.

### 3.2 기본 V4가 안전·UX 검증의 주 대상에서 빠짐 — Medium

`verify_dashboard_safety_audit.py`의 runtime surfaces와 source/html 목록은 legacy와 V3 remodel 중심이다. `verify_dashboard_human_ux_rubric.py` 및 비교 스크립트의 기존 canonical 경로도 `?dashboard_version=legacy`로 이동했다.

기본 사용자 화면을 V4로 승격했으므로 legacy 보존 검증과 별도로 `/ui` 및 V4 주요 탭에 대한 안전 네트워크, 금지 DOM, 자동 POST/WS, UX 시나리오 검증이 필요하다.

### 3.3 셸 파리티 가드가 실제 render reachability를 증명하지 못함 — Medium

`test_shell_wiring_parity.py`는 모든 `v4-*.jsx` 파일에서 정규식으로 대문자 JSX 태그를 모은다. 셸에서 import되지 않은 고아 파일이나 주석 문자열도 V4에 배선된 것으로 계산될 수 있다. wrapper 내부 하위 패널의 실질적 동등성도 증명하지 못한다.

재발 방지 가드는 `App`과 `DashboardV4Shell`을 루트로 한 import/render graph 또는 명시적인 패널 parity manifest를 비교해야 한다.

### 3.4 캐시 구현과 문서 계약 불일치 — Medium

`_FingerprintedStaticFiles`는 `.html` 및 `?v=`가 있는 JS/CSS에만 헤더를 설정한다. 주석과 문서는 지문 없는 자산을 `no-store`로 유지한다고 설명하지만 실제 미지문 JS/CSS에는 명시적 `no-store`가 없다. 테스트도 `immutable` 부재만 확인하며 `no-store`를 단정하지 않는다.

또한 query string에 `v=` 문자열만 있으면 내용 해시 검증 없이 1년 immutable이 된다. 수동 버전 CSS의 버전 갱신 누락은 장기 stale 위험으로 이어질 수 있다.

## 4. Alpha Lab 통합 판정

### 4.1 Alpha 퍼널이 실제 authoritative receipt를 읽지 못함 — High

`alpha_api.py`의 funnel은 다음 generic 이름을 읽는다.

- `registration_receipt.json`
- `engine_check_receipt.json`
- `rho_gate_verdict.json`

그러나 기본 run 디렉터리에는 다음 실제 영수증이 존재한다.

- `rho_gate_registration_receipt.json`
- `rho_gate_engine_runs.json`
- `rho_retrial_registration_receipt.json`
- `rho_retrial_engine_runs.json`
- `rho_retrial_verdict.json`

그 결과 등록·엔진 확인이 0으로 표시되고, 후속 retrial 최종 판정보다 이전 gate 판정이 사용된다. stage ladder도 `events_analyzed`에서 끝나 등록·엔진·재판정 단계를 표현하지 못한다.

이는 단순 빈 화면이 아니라 실제 연구 상태의 오표시다. schema-aware adapter 또는 버전된 manifest를 사용해 authoritative receipt를 명시적으로 선택해야 한다.

### 4.2 번역 조건식 필드가 화면에서 잘못 선택됨 — Medium

실제 `translation_receipt.json`은 번역식을 `expr`, 실행문을 `buy_statement`에 저장한다. `v4-alpha.jsx`는 `expression`, `text`, `rule` 순으로 읽어 정식 식 대신 내부 rule 배열 또는 부정확한 문자열을 표시할 수 있다.

화면은 schema-defined `expr`/`buy_statement`, validated/reasons, lift/FDR/adoption 근거를 명시적으로 렌더해야 한다.

### 4.3 파일 존재를 봉인 완료로 오인 — Medium

사전등록 상태의 `available`은 파일 존재를 기준으로 한다. JSON 손상, sidecar 부재, SHA 불일치가 있어도 UI는 파일이 존재하면 `sealed` 또는 프로그램명을 표시할 수 있다.

`present`, `valid_json`, `sidecar_present`, `sha_match`, `sealed`를 분리하고 sealed는 정상 JSON과 일치 SHA를 모두 요구해야 한다.

### 4.4 explicit zero와 read error 처리 오류 — Medium

`_fdr_survived_count()`는 explicit count를 truthiness로 검사한다. authoritative `n_fdr_survived=0`이면 rule flags fallback으로 넘어가 0을 양수로 바꿀 수 있다. Funnel은 `_load_json()` 오류를 버려 손상·읽기 실패를 측정된 0처럼 표시할 수 있고, 일부 직접 `read_bytes/read_text`는 예외가 HTTP 500으로 전파될 수 있다.

0, unknown, unavailable, malformed를 서로 다른 상태로 유지해야 한다.

### 4.5 Alpha 폴링 source 전환 race — Medium

`V4Alpha.load()` 호출마다 별도 `done` flag를 만들지만 effect cleanup은 최초 호출의 closure만 보유한다. interval에서 시작된 이전 base URL 요청은 unmount 또는 base URL 변경 뒤 새 상태를 덮을 수 있다.

하나의 effect-scoped AbortController 또는 monotonically increasing request generation이 필요하다.

### 4.6 승인된 P4 데이터 계약과 현재 구현 불일치 — High

P4 계약은 다음을 봉인한다.

- `research_assets.db` 단일 source
- `/research/assets`, `/research/judgments`, `/research/cells`, `/research/clauses`
- SQLite read-only SELECT
- 원천 JSON 직접 읽기 금지
- 서버 통계·카운트 재계산 금지
- 전체 로컬 경로 노출 금지
- 사용자 go와 기존 V4 PR 조율 후 구현

현재 구현은 `/api/alpha/status|dataset|events|rules|funnel`이 여러 JSON/JSONL을 직접 읽고 원장을 합산하며 `run_dir`을 반환한다. 따라서 현재 Alpha 탭은 승인된 P4 구현으로 볼 수 없다.

현재 API를 임시·비-P4 관찰 화면으로 명확히 분류하거나, 승인 절차를 통해 계약을 개정하거나, 봉인된 P4 계약대로 다시 구현해야 한다.

### 4.7 Alpha 문서의 현재 상태·운영 안내 충돌 — High

- 종합 보고서는 audit 후보 0, target X1 pre-measurement, P4 go 대기를 설명한다.
- 후속 커밋은 X1 측정·판정을 진행했고 V4 Alpha 탭도 구현했다.
- wt-dev 복귀 체크리스트는 B1 페어가 어느 레인에서도 즉시 사용 가능하다고 안내하지만, 병합 기록은 현재 wt-dev DB에 필요한 매수 SHA가 없어 reporting test가 실패했다고 적는다.
- “안정화 통과” 요약과 49/50 실패 기록도 동시에 존재한다.

문서는 lane과 작성 시점을 명시하고 하나의 최신 current-state 문서로 X1/B1/P4 권한을 정리해야 한다. 현재 branch 정책과 별도 승인 없이 live·protected DB·registration 권한이 생겼다고 해석해서는 안 된다.

## 5. CSS_V7 리페어 도구 판정

### 5.1 정규식 수리가 중첩 호출을 문법 오류로 만듦 — High

현재 변환은 다음 정규식을 사용한다.

```python
re.sub(r"self\.Buy\([^\n)]*\)", "self.Buy()", code)
```

재현 입력:

```python
self.Buy(make_qty(code))
```

실제 결과:

```python
self.Buy())
```

`compile()` 결과는 `SyntaxError: unmatched ')'`였다. multiline call은 남을 수 있고 문자열·주석의 `self.Buy(...)`도 변조된다.

더 위험한 점은 apply mode가 INSERT를 commit한 후 `build_receipt()`에서 다시 AST를 파싱한다는 것이다. 잘못된 `_FIXCALL` 행이 DB에 커밋된 뒤 영수증 생성이 실패할 수 있다.

AST가 제공하는 source offset으로 실제 call argument span만 치환하고, 어떤 파일·백업·DB 쓰기보다 먼저 전체 fixed code를 parse/compile해야 한다.

### 5.2 정상 1인자 Buy/Sell의 의미를 제거 — High

실제 backtest 엔진 계약은 다음과 같다.

```python
def Buy(self, buy_long=False)
def Sell(self, sell_long=False)
```

현재 visitor는 positional argument가 하나라도 있으면 위반으로 판정한다. 따라서 정상적인 `self.Buy(True)` 또는 `self.Sell(True)`를 무인자로 바꿔 long/short 체결 의미를 변경할 수 있다. keyword argument는 반대로 검사에서 누락된다.

검사는 “인자 존재”가 아니라 알려진 legacy 7인자 형식 또는 명시적인 engine contract 위반만 판정해야 한다.

### 5.3 문자열·주석 변조 — High

정규식은 AST가 식별한 호출만 수정하지 않고 소스 전체에 적용된다. 다음 입력에서 문자열 내용까지 변경됨을 재현했다.

```python
note = "self.Buy(example)"
self.Buy(code)
```

결과:

```python
note = "self.Buy()"
self.Buy()
```

이는 수리 대상 외 바이트와 SHA를 변경하고 전략 코드의 의미를 바꿀 수 있다.

### 5.4 buy/sell 테이블 구분 없는 mapping — High

`repaired_pairs()`의 mapping key는 `source_name`뿐이다. 같은 이름이 `stockbuy`와 `stocksell`에 존재하고 한쪽만 수리 대상이면 양쪽 모두 `_FIXCALL`로 바뀌어 생성되지 않은 endpoint를 참조할 수 있다.

mapping을 `(table, source_name)`으로 만들고 emitted pair의 buy/sell endpoint가 기존 또는 planned row에 존재하는지 검증해야 한다.

### 5.5 백업과 collision 판단이 안정된 SQLite snapshot이 아님 — High

열린 SQLite DB 파일을 `shutil.copy2()`로 복사한다. WAL 내용이 누락될 수 있고 collision 검사 후 INSERT 전 동시 변경도 가능하다. 안전한 구현은 typo path에서 DB를 새로 만들지 않도록 열고, `BEGIN IMMEDIATE`, SQLite backup API, source/target SHA 재검증, INSERT, post-read SHA 확인을 하나의 통제된 경계에서 수행해야 한다.

### 5.6 collision abort가 canonical pair 파일을 먼저 덮어씀 — Medium

`write_pair_files()`가 collision abort보다 먼저 실행된다. 충돌을 알고도 canonical `pairs_*_fixcall.json`이 잘못된 target을 참조한 상태로 남는다. preview는 별도 경로에 staging하고 collision·endpoint 검증 후 원자적으로 publish해야 한다.

### 5.7 DB commit과 영수증이 원자적이지 않음 — Medium

`apply_inserts()`가 내부에서 commit하고 이후 receipt를 만들고 쓴다. parse error, report I/O failure, interruption이 발생하면 DB는 변경됐지만 durable outcome receipt가 없을 수 있다. 두 번째 idempotent apply도 신규 insert가 없는데 status가 `inserted`가 될 수 있으며 receipt는 stored row를 post-read하지 않는다.

준비 영수증, transaction, post-verification, commit, atomic finalization을 하나의 복구 가능한 절차로 설계해야 한다.

## 6. CSS_V7 연구 증거 판정

### 6.1 인간 결과 문서가 pre-repair 결과를 최종처럼 표시 — High

`css_v7_validation_20260702_result.md`는 다음을 적는다.

- tick smoke 7/7 timeout
- min 첫 페어 장시간 무출력 후 중단
- train 미실행
- survivor 0, rejected 0, hold 21

그러나 post-repair validation ledger는 17 smoke no_go, 2 smoke go, 2 hold를 기록하고 provenance/revival은 19 rejected, 2 hold를 최종처럼 기록한다. 결과 문서에 pre-repair/superseded 표시가 없고 final summary를 반영하지 않는다.

문서는 07:41 pre-repair와 15:04 repaired smoke, 15:22 후속 기록을 시간 순서로 분리해야 한다.

### 6.2 train 측정 결과로 2개 후보를 절차 밖 최종 기각 — High

승인된 Plan C 프로토콜은 train을 “측정 단계 — 판정 없음”으로 규정하고 기각은 OOS/WF 단계에서 수행하도록 한다. 그러나 smoke go 2개 후보가 train MDD 기준으로 rejected 처리됐고 revival registry에도 들어갔다. OOS/WF는 실행되지 않았다.

따라서 machine-readable 19 rejected는 산술적으로는 17 smoke no_go + 2 train reject와 맞지만, 프로토콜상 후자의 2개는 최종 기각으로 인정할 수 없다. 두 후보는 train 결과를 advisory로 보존하고 OOS/WF 전까지 hold/pending으로 복원해야 한다.

### 6.3 durable 문서가 미추적 artifact에 의존 — Medium

JSONL과 결과 문서는 `artifacts/chart_sulsa_validation_20260702/*`와 `.omo/evidence/*` receipt를 참조하지만 해당 evidence는 커밋에서 제외됐다. 현재 워크스테이션에서는 일부 확인할 수 있어도 새 clone은 원본 receipt를 교차검증할 수 없다.

최종 summary receipt와 필요한 해시를 durable 경로에 보존하거나 외부 evidence 보존 위치·수명·검증 방법을 명시해야 한다.

## 7. 검증 기록

| 검증 | 결과 |
|---|---|
| 최초 V4 집중 테스트 | 39 passed |
| 현재 dashboard 선택 테스트 | 1118 passed, 5252 deselected |
| Alpha API·V4 집중 테스트 | 26 passed |
| Alpha 광범위 `-k alpha` | 1200초 timeout, 완료 판정 불가 |
| CSS 리페어 단위 테스트 | 4 passed |
| 중첩 호출 재현 | `self.Buy(make_qty(code))` → `self.Buy())`, compile 실패 |
| keyword 호출 재현 | `self.Buy(code=code)`가 violation에서 누락 |
| 문자열 변조 재현 | 문자열 내부 `self.Buy(example)`까지 변경 |
| 동일 이름 pair 재현 | buy/sell 양쪽이 존재하지 않을 수 있는 동일 `_FIXCALL`로 변경 |
| CSS JSONL 파싱 | revival 19, validation 45, provenance 42 모두 JSON 파싱 성공 |
| 현재 번들 hash | manifest와 일치 |
| `0a92c327..673757b2` diff check | 통과 |
| 전체 대형 병합 범위 diff check | imported 문서의 trailing whitespace/EOF 문제로 실패 관측 |

기존 테스트 통과는 단순 positional 7인자 입력과 synthetic Alpha fixture를 검증한다. 실제 receipt 이름·schema, nested/multiline call, valid one-argument semantics, 문자열 보존, side-qualified mapping, SQLite concurrency·backup, receipt fault를 검증하지 않으므로 본 BLOCK 항목을 반박하지 않는다.

## 8. 수정 우선순위와 완료 조건

| 순서 | 작업 | 완료 조건 |
|---:|---|---|
| 1 | Alpha authoritative receipt adapter | `rho_gate_*`/`rho_retrial_*` 실제 fixture와 화면 단계·수치·최종 판정 일치 |
| 2 | Alpha P4 권한·계약 정리 | 임시 비-P4 또는 승인된 P4 중 하나로 명시, current-state 문서 갱신 |
| 3 | CSS AST 기반 수리 | nested/multiline/string/comment/valid one-arg/keyword 테스트 통과 |
| 4 | CSS DB transaction 재설계 | SQLite backup API, stable transaction, prevalidate, post-read SHA, atomic receipt |
| 5 | CSS pair publish 안전화 | side-qualified mapping, endpoint 존재 검증, collision 시 canonical 파일 불변 |
| 6 | CSS 판정 복원 | train 기각 2건을 hold/pending으로 되돌리고 OOS/WF 전 최종 기각 금지 |
| 7 | CSS 인간 결과 문서 갱신 | pre-repair와 repaired/final 기록을 시간순으로 구분 |
| 8 | `/runs` 공용 자원화 | V4 route별 실제 브라우저 요청 수가 문서와 일치 |
| 9 | V4 안전·UX·파리티·캐시 보강 | canonical V4 런타임 검사, reachable parity, 미지문 no-store 계약 통과 |
| 10 | 전체 검증 | focused+dashboard+Alpha+CSS 테스트, 실제 fixture, browser request count, diff check 통과 |

## 9. 최종 승인 기준

다음 조건 전에는 본 범위를 승인 완료로 표시하지 않는다.

1. Alpha 화면이 실제 authoritative receipt를 사용하고 0/unknown/error/final verdict를 구분한다.
2. P4 구현 여부와 사용자 승인 상태가 문서·코드에서 하나의 계약으로 일치한다.
3. CSS 수리 도구가 정상 1인자 의미와 비호출 텍스트를 보존하고 DB 쓰기 전에 문법·계약을 검증한다.
4. CSS DB 변경, 백업, pair publish, receipt가 복구 가능한 transaction 경계에 있다.
5. train 단계에서 잘못 기각된 2개 후보의 상태가 프로토콜에 맞게 정정된다.
6. V4 `/runs`, 안전·UX, 파리티, 캐시 문제와 실제 브라우저 수치가 해소된다.
7. 새 clone에서도 핵심 증거와 최신 current-state 결론을 재현할 수 있다.

이 보고서는 코드·문서 검토 결과이며 전략 성능, live 운용, 보호 DB 변경, broker 연결, V3K later gate 실행 또는 후보 승격 권한을 부여하지 않는다.
