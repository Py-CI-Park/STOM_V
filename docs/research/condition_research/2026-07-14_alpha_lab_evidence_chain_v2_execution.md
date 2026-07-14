# Alpha Lab Evidence Chain v2 실행·감사 정정 보고서 (G001 + G008)

- 작성일: 2026-07-14
- 대상: Ultragoal G001(연구 증거 체인) 및 G008(정정·감사 해소)
- 기준 변경열: `198db293` 이후 `317a79f4`, `9b1dc832`, `5ff1863b`, `45f58785`, `30e8b5cd`, `80993ca0`, `8707db53`, `c03355b8`, `d175954e`, `34433deb`, `9ec30d8d` 및 대응 public/package wrapper 커밋
- 문서 지위: 코드·문서·단위 계약의 실행 이력이다. 전략 승격 승인, 보호 DB 작업, 실전 또는 엔진 실행 승인이 아니다.
- 실행 제한: 이 문서 갱신에서는 테스트·git·lint·formatter를 실행하지 않았다. 보호 DB를 열거나 읽고 쓰지 않았고 엔진도 실행하지 않았다.

## 1. 정정 이력과 현재 결론

`198db293`의 첫 cleaner는 **BLOCKING 6건, ADVISORY 2건**을 발견했다. 그 뒤 cleaner 재검토는 두 차례 더 실패했다. 세 차례의 실패는 “통과”가 아니라, closure 소비자 검증, 생산자 경로, PRE/POST journal 및 공개 경계에서 추가 blocker를 발견한 기록이다. 따라서 초기 보고서의 완전성·one-use·승격 authority 주장은 당시 사실이 아니었고, 중간 cleaner 반복도 완료 판정이 아니었다.

후속 커밋열과 wrapper 정리는 발견된 blocker를 순차적으로 해소했다. 현재 결론은 **v2만 공개 promotion write authority이며, PRE provenance를 완결 검증한 경우에만 그 경계에 도달한다**는 것이다. 이 결론은 provenance 및 쓰기 전 검증 계약에 한정된다. 연구 가설, 성능, 엔진 의미론, 보호 DB 결과나 실전 성공을 뜻하지 않는다.

| cleaner 반복 | 당시 상태 | 결과 |
|---|---|---|
| 1차 (`198db293`) | blocking 6, advisory 2 발견 | 실패; G001 완결 아님 |
| 2차 | seal/identity/legacy read 보정 뒤 consumer·producer 경계 결함 발견 | 실패; 추가 수정 필요 |
| 3차 | receipt·catalog·PRE/POST 결박 보정 뒤 journal/공개 write 경계 결함 발견 | 실패; 추가 수정 필요 |
| 4차 준비 상태 | 아래 커밋열 및 wrapper 반영 후 focused suite 136 passed라는 리더 검증 기록 | 최종 인수 전 cleaner 재검토 대상; 성능·운영 PASS 주장 아님 |

| 변경열 | 해소한 계약 범주 |
|---|---|
| `317a79f4`~`45f58785` | SEALED, receipt/claim, artifact·candidate identity, strict legacy read, legacy write fence의 최초 보정 |
| `30e8b5cd`, `80993ca0`, `8707db53` | 소비자 closure 재도출, canonical 후보 identity, 전 행 ledger/단일 writer 보강 |
| `c03355b8`, `d175954e` | canonical receipt/claim, 완전 chronology, source·catalog DB-bound PRE 결박 보강 |
| `34433deb`, `9ec30d8d` 및 wrapper | durable target-DB PRE intent/anchor, canonical POST, PRE-only reconciliation, conflict 및 v2 sole-writer 경계 보강 |

## 2. 현재 공식 생산자 체인과 소비자 검증

공식 생산자 전용(producer-only) 체인은 임의 JSON 조립이나 소비자 우회가 아니라 다음 v2 순서다.

```text
finalize_prereg
  → issue_gate_receipt_v2
  → claim_gate_receipt_v2
  → append_trial_v2
  → PRE promotion manifest
  → catalog builder의 PRE receipt
  → verify_promotion_manifest
  → register_conditions_v2 (실제 DB 쓰기가 명시적으로 호출된 경우만)
```

소비자는 producer가 적은 manifest를 신뢰만 하지 않는다. SEALED 문서의 `dependency_roots`에서 Python closure를 다시 도출하고, **root package의 `__init__.py`와 local dynamic import/load target까지** 포함한다. 문서의 `dynamic_python_dependencies`는 재도출한 dynamic dependency와 정확히 같아야 하며, 선언된 code file 집합은 그 closure와 non-Python dependency의 정확한 합집합이어야 한다. sorted·unique complete manifest의 각 파일은 full SHA-256으로 검증한다.

| 단계 | 강제 계약 | 거부 조건 |
|---|---|---|
| SEALED prereg | 명시적 `SEALED`, draft marker 부재, repo-relative 경로, 소비자가 재도출한 complete closure | 미봉인/초안, 외부·중복·누락 경로, initializer 또는 dynamic dependency 누락 |
| gate receipt/claim | canonical receipt와 `claims/{receipt_id}.json` 단일 claim, receipt SHA·HEAD·발급 시각 재결박 | 비정규 claim 경로, 변조, 재소비, `consumed_at < issued_at` |
| Ledger v2 | 전 행 strict schema/type/timestamp, receipt·claim·artifact·candidate-bound evidence identity | malformed 행, 임의 identity, chronology 역전 |
| candidate | canonical sorted candidate set의 `name`, `buy_sha256`, `sell_sha256` 및 집합 SHA | 이름만 일치, buy/sell hash 불일치, 순서/중복 변조 |
| catalog PRE | manifest bytes, evidence ID, 후보, source hash와 catalog DB가 결박된 authoritative PRE receipt | POST receipt를 PRE authority로 사용, source/catalog DB 불일치 |
| v2 write | verifier 통과 뒤 durable PRE intent와 anchor, 정확한 items, canonical POST | legacy 진입, PRE 없음, 재실행, target DB pre-state 변조 |

## 3. 원장·후보·chronology의 단일 정본

전역 `n_trials` 원장은 `append_trial`/`append_trial_v2`가 유일한 기입 API다. 보고서 생성기는 원장을 소비할 뿐 자체 기입 경로가 없다. 따라서 D1 및 D9을 포함한 모든 계열은 별도 카운터나 병렬 기록자가 아니라 이 **all-row 단일 writer**를 사용한다. 이는 D1/D9 측정 결과 또는 성능의 주장과 무관한 기록 일관성 계약이다.

v2 evidence ID는 검증된 receipt·usage에 immutable input/result artifact와 canonical candidate set을 결합해 재구성한다. 후보의 정체성은 후보 이름만이 아니라 정확한 buy/sell expression SHA-256 쌍이다. 빈 후보 집합은 `negative_or_kill` 측정에만 허용된다.

chronology는 seal의 `sealed_at` → receipt `issued_at` → claim `consumed_at` → exact ledger row `ledger_at` → journal `pre_at` → POST `post_at` 순서로 기록·검증한다. journal은 evidence ID에 해당하는 ledger authority row가 정확히 하나여야 한다. 이 순서는 호출자가 임의로 붙이는 설명 필드가 아니라 canonical receipt/claim 및 실제 authority artifact에서 재구성되는 값이다.

기존 Ledger v1은 읽기 호환만 제공한다. v1도 정확한 schema/type/timestamp를 엄격 검증하며 malformed 행은 fail-closed한다. v1과 `LEGACY_V1` 역사 자료는 v2 promotion authority를 제공하지 않는다.

## 4. PRE/POST, catalog, target DB의 결박

`PRE`는 등록 전 authority 상태이며 승격 승인이나 DB 변경 결과가 아니다. catalog가 소비하는 canonical authority는 **하나의 PRE promotion manifest**다. catalog PRE receipt는 그 manifest의 path/SHA, evidence ID, candidate set, source hashes 및 catalog DB bytes를 결박한다. POST receipt 또는 별도 manifest는 PRE catalog authority로 대체할 수 없다.

`register_conditions_v2()`는 DB mutation 전에 다음 PRE journal을 exclusive write 및 fsync한다.

| journal/결과 | schema·상태 | 필수 결박 |
|---|---|---|
| PRE intent | `schema_version=2`, `kind=promotion_journal`, `status=PRE` | manifest·catalog PRE receipt·candidate set/SHA·repo-relative target DB path·target DB `pre_sha256`·완전 chronology |
| PRE hash anchor | PRE bytes의 SHA-256 ASCII anchor | PRE 파일의 정확한 bytes를 고정; anchor 없거나 불일치하면 거부 |
| POST result | `schema_version=2`, `kind=promotion_result`, `status=POST` | 같은 PRE manifest/catalog receipt/candidate set, target DB pre/post SHA, outcomes, PRE ref/anchor, chronology |

PRE intent가 생겼지만 POST가 없으면 상태는 `INCOMPLETE_REQUIRES_RECONCILIATION`이다. 자동 recovery, 재시도 또는 새 POST 생성은 하지 않는다. 검사 시점의 target DB SHA가 PRE `pre_sha256`와 같은지만 보고하는 **PRE-only reconciliation**이며, 불일치는 명시적 reconciliation을 요구한다. POST가 있을 때만 POST SHA가 현재 target DB bytes와 일치하는지 검증한다.

POST는 evidence ID당 canonical 경로에 exclusive write되는 하나뿐인 결과다. `inserted`와 `conflicts`는 PRE 후보 전부를 정확히 한 번씩 account해야 한다. 어느 한 테이블에 동명 조건이 있으면 buy/sell 쌍 전체를 삽입하지 않고 `{"name", "reason": "name_exists", "existing_tables"}` conflict로 남긴다. 이는 부분 삽입을 허용하지 않는 pair-level skip이며 재실행을 정당화하지 않는다.

## 5. 공개 write boundary

```python
register_conditions(db_path, items, *, backup_dir, now)
```

legacy 공개 함수는 DB를 열기 전에 항상 `LegacyPromotionBlockedError` (`legacy-promotion-blocked`)를 발생시킨다.

```python
register_conditions_v2(
    db_path, items, *, manifest_path, repo_root, ledger_path,
    gate_receipt_path, gate_usage_path, catalog_receipt_path,
    journal_dir, backup_dir, now,
)
```

v2만 공개 DB write authority다. 이 함수는 read-only `verify_promotion_manifest()`와 catalog PRE 검증을 통과하고, supplied item의 이름 집합 및 buy/sell expression SHA가 PRE 후보와 정확히 일치한 뒤에만 진행한다. `_database` 및 `_database_v3k_shadow` 보호 전략 DB는 명시적으로 거부한다. 정상 package import와 public wrapper는 이 v2 경계만 노출하며 private helper는 authority가 아니다.

## 6. 검증 기록과 비주장

리더 검증 기록의 focused suite는 **136 passed**다. 이 문서 작업에서는 사용자 제약에 따라 테스트·git·lint·formatter를 실행하지 않았으므로, 그 수치를 이번 작업에서 재실행한 결과로 주장하지 않는다.

```powershell
pytest -q tests/unit/test_alpha_discipline.py tests/unit/test_alpha_gates.py tests/unit/test_alpha_catalog.py tests/unit/test_alpha_bridge.py
```

이 focused suite는 closure/SEALED, canonical receipt·claim, strict ledger read, artifact·candidate binding, catalog PRE, PRE intent/anchor, POST/journal/reconciliation, conflict 및 legacy fence/v2 public boundary의 단위 계약을 다룬다. 보호 DB는 읽거나 쓰지 않았고 엔진도 실행하지 않았다.

- 이 구현과 136개 단위 시험은 연구 가설의 진실성, 전략 수익성 또는 실전 적합성을 증명하지 않는다.
- 과거 2022~2023 자료는 반복 노출된 진단 자료이며, 새로운 미개봉 OOS가 아니다.
- 실제 POST 등록, DB conflict/backup/write 결과, 엔진 의미론은 이 보고서의 관측 사실이 아니다.
- verifier PASS는 provenance consistency일 뿐 사용자 승인, 시행 예산, 등록 승인 또는 운영 승인을 대체하지 않는다.