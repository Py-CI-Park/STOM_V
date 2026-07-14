# Alpha Lab Evidence Chain v2 실행 보고서 (Ultragoal G001)

- 작성일: 2026-07-14
- 대상: Ultragoal G001 — 연구 증거 체인과 현행 서사 정비
- 근거 커밋: `f38a0ef2`, `8f3ffe43`, `c9b8eaaa`
- 문서 지위: 연구 기반 구현 인수인계. 전략 승격 승인이나 실전/엔진 실행 승인 문서가 아니다.
- 실행 제한: **보호 DB에 대한 읽기·쓰기 및 엔진 실행은 수행하지 않았다.** 본 변경은 코드·문서·단위 테스트 범위의 증거 체인 구현이다.

## 1. 목적과 범위

G001의 목적은 사전등록, 측정 게이트, 시행 원장, 카탈로그, 승격 검증 사이에 동일 실험을 식별할 수 있는 강제 연결을 만드는 것이다. 기존 자료의 결과값을 재측정하거나 새로운 알파를 주장하지 않는다. 구현은 다음을 제공한다.

1. 사람이 읽을 수 있는 SEALED 사전등록과 기계 검증 가능한 v2 봉인 sidecar
2. 전체 코드 manifest와 SHA-256을 묶은 PASS gate receipt 및 한 번만 소비되는 usage record
3. receipt/usage에서 재구성되는 evidence identity를 가진 Ledger v2
4. 승격 전(PRE)과 승격 후(POST)를 구분하는 카탈로그 상태와 영수증
5. DB를 열지 않고 promotion manifest의 전체 링크를 검사하는 read-only verifier

## 2. 사전 결함과 수정 방향

| 우선 | 기존 결함 | 실패 가능성 | v2 처리 |
|---:|---|---|---|
| HIGH | 미완성 사전등록도 tracked/clean이면 통과 가능 | 결과 확인 뒤 문서를 완성한 것처럼 보일 수 있음 | 명시적 `SEALED`, draft marker 부재, 필수 구조와 파일 참조를 finalizer가 검증한다. |
| HIGH | SHA 검사가 선택 사항이고 코드 목록을 호출자가 정함 | 의존 코드 누락 또는 코드 drift 상태에서 측정 가능 | 봉인 manifest의 전체 파일 목록과 full SHA-256을 receipt에 고정한다. |
| HIGH | PASS 게이트와 실제 측정이 분리됨 | 과거 PASS 영수증 재사용 가능 | receipt를 한 번 claim해 usage record를 만들고 receipt/HEAD/code를 재검증한다. |
| HIGH | 원장에 prereg/gate/artifact 정체성이 없음 | 다른 실험 행의 혼입을 추적할 수 없음 | v1 보존 위에 evidence ID와 gate identity를 갖는 v2 trial row를 추가한다. |
| HIGH | 카탈로그가 부분 원천 또는 정적 verdict로도 성공 가능 | 불완전한 근거가 승격 후보처럼 보일 수 있음 | 필수/선택 manifest와 PRE/POST 상태를 명시하고 불완전 상태를 구분한다. |
| HIGH | 등록기가 임의의 비어 있지 않은 `ALP_` 식을 받을 수 있음 | 증거와 무관한 전략 등록 위험 | promotion manifest, ledger, gate, catalog receipt가 모두 일치해야 후속 등록 경로로 진행한다. |
| MEDIUM | 원장 read 검사가 키 존재 중심 | malformed 행을 정상 행으로 오인할 수 있음 | 버전·타입·timestamp·정확한 schema를 읽을 때 fail-closed로 검증한다. |
| MEDIUM | 기존 B-ext/O-4 자료를 새 체인으로 소급 포장할 여지 | 측정 후 gate receipt를 재구성하는 오류 | 두 역사 자료를 `LEGACY_V1`, `promotion_authority: NONE`로 경계한다. |

## 3. 구현 근거와 변경 단위

세 논리 커밋 `f38a0ef2`, `8f3ffe43`, `c9b8eaaa`의 구현 결과를 기준으로 다음 파일군을 확인했다. 이 표는 코드의 역할을 적은 것이며, 새 측정 결과나 성능 수치를 포함하지 않는다.

| 계층 | 구현 파일 | 역할 |
|---|---|---|
| 사전등록 봉인 | `alpha_lab/discipline/prereg.py` | 명시적 SEALED 문서, draft marker, 상대 경로, full SHA-256을 검증해 v2 prereg seal을 단독 sidecar로 작성한다. |
| 공통 증거 schema | `alpha_lab/discipline/evidence.py` | prereg seal, gate receipt, usage의 strict schema와 canonical SHA-256, evidence identity를 정의·검증한다. |
| 게이트/영수증 | `alpha_lab/discipline/measure_gate.py`, `scripts/measure_gate.py` | complete manifest의 v2 PASS receipt 발급, 현재 HEAD/code 검증, 원자적 단일 claim 및 CLI 진입점을 제공한다. |
| 원장 | `alpha_lab/discipline/ledger.py` | v1 행을 읽을 수 있게 유지하면서 v2 trial row에 receipt/usage 기반 identity를 기록하고 엄격히 읽는다. |
| 카탈로그 | `alpha_lab/catalog/builder.py` | PRE promotion manifest 또는 POST result 입력을 상호배타적으로 처리하고 상태/원천 완전성을 검사한다. |
| 승격 경계 | `alpha_lab/bridge/registrar.py` | promotion manifest의 ledger record, gate receipt/usage, catalog receipt, 후보 SHA를 read-only로 대조하고, 등록 경로의 선행 검증으로 사용한다. |
| 역사 자료 경계 | `docs/research/condition_research/plans/2026-07-13_o4_generation_grammar_preregistration.md`, `docs/research/condition_research/plans/2026-07-14_b_track_ext_multistrategy_branches_preregistration.md` | 과거 사전등록/결과의 가독성은 보존하되 v2 SEALED 및 사후 one-use receipt 재구성을 금지한다. |
| 단위 시험 | `tests/unit/test_alpha_discipline.py`, `tests/unit/test_alpha_gates.py`, `tests/unit/test_alpha_catalog.py`, `tests/unit/test_alpha_bridge.py` | schema, tamper/reuse 거부, mixed v1/v2 read, PRE/POST 및 promotion verifier 계약을 검증한다. |

## 4. 정확한 v2 증거 체인

v2 체인은 다음 순서를 바꾸지 않는다.

```text
SEALED preregistration
  → prereg seal manifest (sealed document + complete code manifest + SHA-256)
  → PASS gate receipt
  → one-use receipt claim / gate usage
  → Ledger v2 trial row (evidence identity)
  → PRE catalog + PRE receipt
  → read-only promotion-manifest verifier
  → POST catalog/result (등록이 실제로 승인·수행된 경우에만)
```

| 단계 | 입력과 불변식 | 산출물 | 거부 조건 |
|---:|---|---|---|
| 1. SEALED prereg | 문서에 `> 지위: **SEALED**`; draft marker 없음 | 봉인 가능한 사전등록 | 미봉인 상태, `(기입)`·`(미주입)` 등 초안 표식, 문서 외부 경로 |
| 2. manifest | 사전등록 파일 ref와 측정에 필요한 코드 전체의 상대 POSIX 경로·full SHA-256 | `prereg_seal` v2 | 누락/중복/변조 파일, schema·해시 불일치 |
| 3. receipt | 검증된 seal, 현재 repository HEAD, complete code manifest | `measure_gate_receipt` v2, `status=PASS` | repo, SEALED 문서, clean code, SHA seal 검사 실패 |
| 4. claim | PASS receipt, 현재 HEAD 및 코드 재검증, 소비자·시각 | 단일 `gate_usage` | receipt 변조, code/HEAD drift, 이미 claim된 receipt |
| 5. Ledger v2 | 검증된 receipt + usage, 측정 trial 정보 | evidence ID와 identity를 가진 v2 행 | usage가 receipt와 불일치, malformed schema/timestamp/type |
| 6. PRE catalog | v2 evidence, required/optional 원천, PRE promotion manifest | PRE 상태 카탈로그 및 receipt | 필수 원천 누락, 잘못된 manifest 상태, 후보/해시 불일치 |
| 7. read-only verifier | promotion manifest, ledger, receipt, usage, catalog receipt | 검증 verdict 또는 구체적 오류 | evidence ID, ledger record SHA, catalog PRE 상태, candidate SHA 중 하나라도 불일치 |
| 8. POST | 실제 등록 결과가 있는 경우에만 PRE와 연결 | POST 상태 카탈로그/result | PRE 없이 POST를 생성하거나 PRE/POST 입력을 함께 제공 |

receipt identity는 `issued_at`, nonce, repository HEAD, seal manifest, prereg ref, code-manifest SHA로부터 canonical SHA-256으로 구성된다. Ledger v2 evidence identity는 검증된 receipt와 usage에서 다시 구성된다. 따라서 caller가 임의 ID를 지정해 체인을 연결하는 방식이 아니다.

## 5. PRE/POST와 read-only verifier의 의미

`PRE`는 등록 전의 검증 가능한 승격 후보 상태이며, 승격 그 자체가 아니다. `POST`는 실제 등록 결과가 존재할 때만 별도 입력으로 표현한다. `alpha_lab/bridge/registrar.py`의 `verify_promotion_manifest()`는 DB를 열거나 변경하지 않고 다음을 대조한다.

- manifest가 schema v2, `kind=promotion_manifest`, `status=PRE`인지
- manifest의 evidence ID와 ledger 경로/record SHA가 ledger v2 행과 일치하는지
- receipt와 usage가 유효하고, 재구성한 evidence identity가 ledger 행과 같은지
- catalog receipt의 PRE promotion 상태와 후보 이름·매수식 SHA·매도식 SHA가 manifest와 같은지

등록 함수는 이 verifier가 성공한 뒤에만 계속되도록 배치되어 있다. 이는 verifier가 promotion approval을 발행한다는 뜻이 아니다. DB 접근, 쓰기, 전략 등록 또는 운영 승격 권한은 이 보고서와 verifier의 범위를 벗어난다.

## 6. 하위 호환성과 역사 자료의 경계

| 대상 | 처리 | 승격 권한 |
|---|---|---|
| 기존 Ledger v1 | 읽기 호환을 유지한다. v2 trial 행을 추가하며 기존 행을 v2로 변환하거나 재작성하지 않는다. | v1 행만으로는 v2 promotion chain을 만족하지 않는다. |
| 기존 카탈로그 | 기존 입력/읽기 흐름을 보존하고 v2 PRE/POST 입력을 명시적으로 추가한다. | 상태와 완전한 v2 증거가 없으면 자동 승격 근거가 아니다. |
| B-ext | 역사 사전등록/결과로 계속 읽을 수 있다. | `evidence_contract: LEGACY_V1`, `promotion_authority: NONE`. 측정 뒤 one-use receipt를 재구성할 수 없다. |
| O-4 | 역사 사전등록/결과로 계속 읽을 수 있다. | `evidence_contract: LEGACY_V1`, `promotion_authority: NONE`. 새 사전등록과 새 complete v2 chain 없이는 승격할 수 없다. |

이 경계는 B-ext/O-4의 측정 사실을 무효화하지 않는다. 다만 그 자료가 v2의 사전 봉인·단일 소비 receipt·exact ledger identity 계약을 갖지 않았다는 사실을 보존한다.

## 7. 보안·실패 매트릭스

| 위협/실패 | 예방 또는 탐지 지점 | 예상 동작 |
|---|---|---|
| 초안 사전등록으로 측정 시작 | finalizer | SEALED 표식/placeholder 검사에서 거부 |
| 코드 파일 누락 | seal manifest 및 gate 발급 | complete manifest 불일치로 거부 |
| 코드 변경 후 과거 receipt 사용 | receipt validation 및 claim | 파일 SHA 또는 현재 HEAD 불일치로 거부 |
| receipt JSON 변조 | canonical receipt ID·strict schema | receipt ID/키/해시 검증에서 거부 |
| receipt 재사용 | exclusive usage 생성 | 이미 존재하는 usage path를 덮어쓰지 않고 거부 |
| receipt와 다른 usage 연결 | evidence identity 재구성 | receipt ID/usage SHA 불일치로 거부 |
| malformed ledger 행 | `read_all()`의 schema/type/timestamp 검증 | 행 번호를 포함한 fail-closed 오류 |
| 다른 실험 ledger record 사용 | manifest record SHA + evidence ID 대조 | verifier가 불일치로 거부 |
| PRE 원천 누락 또는 후보 변경 | catalog/manifest의 required source 및 candidate SHA 검사 | `VALID`처럼 취급하지 않고 거부 또는 불완전 상태 |
| PRE 검증을 POST 또는 등록으로 오인 | status 분리 및 verifier 범위 | verifier는 read-only verdict만 반환; 등록 결과가 없으면 POST 없음 |
| legacy 자료의 사후 v2 포장 | LEGACY_V1 명시 | 새 preregistration과 새 v2 chain 없이는 promotion 근거가 될 수 없음 |

## 8. 검증 결과와 재현 명령

리더가 다음 focused suite를 실행해 **121 tests passed**를 확인했다. 이 실행 보고서 작성 과정에서는 사용자 제약에 따라 테스트, git, lint, formatter를 실행하지 않았다.

```powershell
pytest -q tests/unit/test_alpha_discipline.py tests/unit/test_alpha_gates.py tests/unit/test_alpha_catalog.py tests/unit/test_alpha_bridge.py
```

시험 범위에는 v2 seal/receipt/usage schema, tamper 및 one-use 실패, Ledger v1/v2 혼합 읽기, PRE/POST catalog 계약, promotion manifest read-only 검증, legacy B-ext/O-4 boundary가 포함된다. 이 결과는 단위 계약의 통과 사실이며 시장 성과, 엔진 동작 또는 DB 등록 성공을 의미하지 않는다.

## 9. 한계와 비주장

- 이 구현은 증거 연결을 강화하지만, 연구 가설의 진실성이나 전략의 수익성을 증명하지 않는다.
- 과거 2022~2023 자료는 반복 노출된 진단 자료이며 새로운 미개봉 OOS가 아니다.
- B-ext의 일부 raw 양수 점추정 또는 B1 엔진 A/B 개선은 실전 성공이나 신규 매수 알파의 증거로 승격되지 않는다.
- G001에서 보호 DB를 열거나 쓰지 않았고, STOM 엔진 실행도 하지 않았다. 따라서 DB conflict/backup/write 경로 및 엔진 의미론은 이 보고서의 실행 증거가 아니다.
- read-only verifier의 PASS는 체인 일관성의 판정일 뿐, 사용자 승인, 시행 예산, 실전 운영, 전략 등록의 대체물이 아니다.

## 10. 다음 목표 인수인계: U7-F0 Offline Frame Bridge

G001 완료 뒤의 우선 연구는 U7-F0이다. 질문은 “엔진이 더 좋다”가 아니라 **같은 진입에서 엔진 의미론과 L3 재생 의미론의 차이가 얼마이며 어느 성분에서 생기는가**이다. 이 연구는 별도 SEALED v2 사전등록과 새 one-use gate receipt로 시작해야 하며, G001 또는 LEGACY_V1 자료의 receipt를 재사용하지 않는다.

| U7-F0 계약 항목 | 인수 내용 |
|---|---|
| 기간/창 | 2022·2023, 09:00~09:30 |
| cohort | 기존 엔진/P5 exact-entry 원장과 exact timestamp로 매치되는 cohort를 사전 고정 |
| primary estimand | common-entry `Δ_frame = net_engine_semantics - L3_net` |
| 성분 | synthetic/recorded entry × top-book/3-level depth × L3 cap/engine terminal의 2×2×2 factorial |
| 산출 | match/exclusion flow, 연도별 paired day-block CI, 성분 기여·residual, 결측 bounds가 하나의 receipt에 연결된 결과 |
| 실행 제한 | 기존 기록과 재생 의미론만 사용하며 **엔진 실행 0회** |
| 중단 | SHA/vector equivalence 실패, exact-entry 계약 실패, 양년 방향 불일치, 봉인 성분 설명력 합계가 aggregate gap의 50% 미만, 또는 결측 bounds가 결론을 뒤집는 경우 |

U7-F0가 위 계약을 통과하더라도 엔진 연구는 자동으로 시작하지 않는다. 엔진 실행에는 별도 봉인, 명시적 사용자 승인, 시행 예산 및 그 결과의 새 evidence chain이 필요하다.
