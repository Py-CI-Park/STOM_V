# Alpha Lab Evidence Chain v2 최종 증거 체인 보고서 (Ultragoal G001 + G008)

- 작성일: 2026-07-14
- 대상: Ultragoal G001(연구 증거 체인) 및 G008(정정·감사 해소)
- 최초 정리 기준 커밋: `198db293`
- 후속 수정 커밋: `317a79f4`, `9b1dc832`, `5ff1863b`, `45f58785`
- 문서 지위: 코드·문서·단위 계약의 최종 인수인계 기록이다. 전략 승격 승인, 보호 DB 작업, 실전 또는 엔진 실행 승인 문서가 아니다.
- 실행 제한: **보호 DB를 열거나 읽고 쓰지 않았고, 엔진도 실행하지 않았다.**

## 1. 정정 이력과 최종 결론

`198db293` 시점의 첫 cleaner는 G001 변경 집합에서 **BLOCKING 6건, ADVISORY 2건**을 발견했다. 따라서 최초 G001 보고서의 “완전성”, “한 번만 소비(one-use)”, “승격 권한/authority” 보장 주장은 사실이 아니었으며, 해당 시점에는 G001을 완결된 증거 체인으로 취급할 수 없었다.

후속 네 커밋(`317a79f4`, `9b1dc832`, `5ff1863b`, `45f58785`)은 아래의 여섯 blocking 항목을 해소했다. 최종 상태에서 v2 체인은 사전등록·게이트·소비·측정 산출물·후보 집합·PRE/POST provenance를 연결하고, 공개 legacy DB 쓰기 진입점은 차단한다. 이는 체인의 형식적 일관성과 쓰기 전 provenance 검증 범위에 대한 결론이며, 연구 가설·성능·엔진 의미론·실전 성공에 대한 결론이 아니다.

## 2. 최초 불완전 상태와 blocker 해소 매트릭스

| 최초 blocker | `198db293`에서의 결함 | 후속 수정 및 최종 계약 | 해소 근거 |
|---|---|---|---|
| B1 | 사전등록의 봉인 계약이 문서/호출자 입력에 의존했고, 측정에 필요한 derived import closure가 완전하게 강제되지 않았다. | SEALED 문서의 내장 계약을 엄격히 검증하고, 측정 코드와 파생 import closure를 complete code manifest 및 full SHA-256에 묶는다. | `317a79f4`~`45f58785` |
| B2 | evidence identity가 실제 입력·결과 artifact 및 후보 집합에 충분히 결박되지 않았다. | identity는 receipt/usage뿐 아니라 input artifact, result artifact, candidate set 및 그 canonical SHA-256을 포함한다. | `317a79f4`~`45f58785` |
| B3 | legacy Ledger v1 읽기가 느슨하여 malformed v1 행을 정상 역사 행처럼 읽을 수 있었다. | v1도 strict read 계약(정확한 schema/type/timestamp)을 적용하며 malformed 행은 fail-closed한다. | `317a79f4`~`45f58785` |
| B4 | claim 경로·검사 근거·시간 순서가 충분히 결정적/권위적으로 검증되지 않았다. | claim은 `claims/{receipt_id}.json`만 허용하고, complete manifest에 대한 authoritative check와 `consumed_at >= issued_at`를 강제한다. | `317a79f4`~`45f58785` |
| B5 | PRE와 POST의 provenance가 전 구간에서 완결되게 연결되지 않았다. | PRE promotion manifest, ledger/receipt/claim, catalog PRE receipt, POST result를 각각의 SHA·상태·후보 식으로 연결하고 PRE/POST 혼용을 거부한다. | `317a79f4`~`45f58785` |
| B6 | 공개 legacy 등록 함수가 provenance 검증을 우회하여 DB 쓰기로 갈 수 있었다. | 공개 `register_conditions()`는 영구 차단하고, 검증된 PRE provenance를 받는 v2 경로만 공개 쓰기 경계로 남긴다. | `317a79f4`~`45f58785` |

ADVISORY 2건은 최초 cleaner의 기록으로 보존한다. 이 보고서는 advisory 항목을 성능 또는 운영상의 검증 완료로 재해석하지 않는다.

## 3. 최종 v2 증거 체인

```text
SEALED preregistration
  → prereg seal (sealed document + complete code/derived-import closure + SHA-256)
  → PASS gate receipt (authoritative checks)
  → canonical one-use claim / gate usage
  → Ledger v2 trial row (artifact·candidate-bound evidence identity)
  → PRE promotion manifest + PRE catalog receipt
  → read-only promotion-manifest verifier
  → POST promotion result (실제 v2 등록이 수행된 경우에만)
```

| 단계 | 현재 강제 계약 | 거부/경계 |
|---|---|---|
| SEALED prereg | 명시적 `SEALED`, draft marker 부재, 안전한 repo-relative 참조, complete manifest | 미봉인 문서, 초안 표식, 외부/중복/누락 경로 |
| code closure | 측정 코드와 derived import closure를 포함한 sorted·unique manifest와 full SHA-256 | 누락·변조·manifest 불일치 |
| gate receipt | seal, 현재 repo HEAD, prereg, complete manifest, authoritative repo/sealed-doc/code-clean/SHA-seal check | PASS처럼 보이는 비권위 검사 또는 불일치 |
| one-use claim | receipt ID에 결정적으로 대응하는 `claims/{receipt_id}.json`, receipt SHA·HEAD·발급 시각 결박 | 비정규 경로, 변조, 재소비, 소비 시각 역전 |
| Ledger | receipt/usage와 입력·결과 artifact, candidate set, negative/kill 상태로 재구성한 identity | 임의 ID, malformed v1/v2 행, artifact/candidate 불일치 |
| PRE | ledger record SHA, receipt/claim, candidate buy/sell SHA 및 catalog PRE receipt를 promotion manifest와 대조 | PRE 원천 누락, 후보/해시 불일치, PRE/POST 혼용 |
| POST | 실제 `register_conditions_v2()` 결과만 PRE manifest 경로·SHA 및 evidence ID와 함께 기록 | PRE 없이 POST 생성 또는 legacy 경로를 POST로 주장 |

## 4. identity, strict read, 검사 순서의 사실

v2 receipt ID는 `issued_at`, nonce, repository HEAD, seal manifest, prereg ref 및 code-manifest SHA의 canonical SHA-256이다. evidence ID는 검증된 receipt와 usage에 더해 immutable input/result artifact와 canonical candidate set을 포함하여 재구성한다. 호출자가 임의 ID를 주입해 다른 실험·결과·후보를 연결하는 계약은 없다.

현재 receipt 검증은 다음 authoritative check가 모두 명시적으로 통과했는지 요구한다.

1. repository clean 결과,
2. SEALED preregistration에 결박된 committed provenance,
3. complete code manifest의 모든 파일에 대한 tracked·clean 결과,
4. 같은 complete manifest의 모든 파일에 대한 expected/actual SHA-256 일치.

usage는 receipt ID와 receipt canonical SHA-256, issued-at 및 repo HEAD를 다시 결박한다. claim path는 `claims/{receipt_id}.json`이어야 하며, timezone-aware `consumed_at`은 `issued_at`보다 앞설 수 없다.

Ledger v1 호환은 “느슨한 legacy 허용”이 아니다. 기존 v1 형식을 읽는 경우에도 schema·type·timestamp를 엄격히 검증한다. v1 역사 행은 계속 v2 promotion authority를 제공하지 않으며, malformed 행은 읽기 단계에서 fail-closed한다.

## 5. PRE/POST provenance 및 verifier 범위

`PRE`는 검증 가능한 등록 전 후보 상태이지 승격 승인이 아니다. `POST`는 검증을 통과한 v2 쓰기가 실제로 완료된 경우에만 생성되는 결과 상태다. `verify_promotion_manifest()`는 read-only로 다음을 검증한다.

- promotion manifest의 schema v2, `kind=promotion_manifest`, `status=PRE`;
- manifest와 supplied ledger/receipt/claim의 repo-relative 경로 일치;
- manifest evidence ID 및 ledger record SHA의 일치;
- receipt/usage에서 재구성한 evidence identity의 일치;
- catalog receipt의 PRE status, manifest 경로/SHA 및 후보 이름·buy/sell SHA의 일치.

verifier의 PASS는 체인 일관성 verdict일 뿐, DB 접근·DB 쓰기·전략 승인·시행 예산·운영 권한을 발행하지 않는다.

## 6. 정확한 현재 공개 write boundary

현재 공개 legacy write boundary는 다음과 같이 차단되어 있다.

```python
register_conditions(db_path, items, *, backup_dir, now)
```

이 함수는 DB를 열기 전에 항상 `LegacyPromotionBlockedError`를 발생시키며, 오류 식별자는 `legacy-promotion-blocked`이다. 즉, 이 공개 legacy 진입점으로는 어떤 보호 DB 읽기·백업·쓰기·엔진 실행도 시작되지 않는다.

현재 공개 DB 쓰기 경계는 다음 v2 함수뿐이다.

```python
register_conditions_v2(
    db_path, items, *, manifest_path, repo_root, ledger_path,
    gate_receipt_path, gate_usage_path, catalog_receipt_path, backup_dir, now,
)
```

이 함수는 먼저 read-only `verify_promotion_manifest()`를 통과시켜야 하며, supplied item의 이름 집합과 buy/sell expression SHA가 PRE manifest의 후보와 정확히 일치해야 한다. 그 뒤에만 내부 INSERT-only 등록 경로에 도달한다. 정상 패키지 import(`alpha_lab...`)를 사용하는 이 경계는 private 내부 helper를 공개 authority로 취급하지 않는다.

## 7. 역사 자료 경계

| 대상 | 읽기 상태 | promotion authority |
|---|---|---|
| 기존 Ledger v1 | strict schema/type/timestamp 검증 아래 읽기 호환 | 없음; v2 chain을 대체하지 않음 |
| B-ext | 역사 사전등록/결과로만 보존 | `evidence_contract: LEGACY_V1`, `promotion_authority: NONE` |
| O-4 | 역사 사전등록/결과로만 보존 | `evidence_contract: LEGACY_V1`, `promotion_authority: NONE` |

이 경계는 과거 측정 기록을 삭제하거나 성능을 판정하지 않는다. 다만 그 기록을 사후에 SEALED v2·one-use claim·artifact/candidate-bound identity·PRE/POST provenance로 포장하여 authority를 부여할 수 없게 한다.

## 8. 검증 기록

리더 검증에서 다음 focused suite는 **118 passed**였다. 이 문서 갱신 작업에서는 사용자 제약에 따라 테스트, git, lint, formatter를 실행하지 않았다.

```powershell
pytest -q tests/unit/test_alpha_discipline.py tests/unit/test_alpha_gates.py tests/unit/test_alpha_catalog.py tests/unit/test_alpha_bridge.py
```

이 결과는 v2 seal/receipt/usage, strict read, tamper·reuse 거부, artifact/candidate binding, PRE/POST provenance, read-only verifier 및 public legacy write fence에 대한 단위 계약 결과다. 시장 성과, 수익성, 엔진 동작, 보호 DB 등록 성공을 뜻하지 않는다.

## 9. 한계와 비주장

- 이 구현과 118개 단위 시험은 연구 가설의 진실성, 전략 수익성 또는 실전 적합성을 증명하지 않는다.
- 과거 2022~2023 자료는 반복 노출된 진단 자료이며, 새로운 미개봉 OOS가 아니다.
- B-ext의 양수 점추정 또는 B1 엔진 A/B 관측을 신규 매수 알파나 실전 성공 증거로 승격하지 않는다.
- 본 작업에서 보호 DB를 읽거나 쓰지 않았고 엔진을 실행하지 않았다. 그러므로 DB conflict/backup/write 결과, 엔진 의미론, 실제 POST 등록은 본 보고서의 관측 사실이 아니다.
- read-only verifier의 PASS는 provenance consistency일 뿐 사용자 승인, 시행 예산, 등록 승인, 운영 승인을 대신하지 않는다.

## 10. U7-F0 인수인계

G001/G008 이후 U7-F0의 질문은 “엔진이 더 좋다”가 아니라 **동일 진입에서 엔진 의미론과 L3 재생 의미론의 차이가 얼마이며 어떤 성분에서 생기는가**이다. U7-F0는 G001의 기존 receipt나 `LEGACY_V1` 자료를 재사용하지 않고, 별도의 SEALED v2 preregistration과 새 one-use gate receipt로 시작해야 한다.

| U7-F0 계약 항목 | 인수 내용 |
|---|---|
| 기간/창 | 2022·2023, 09:00~09:30 |
| cohort | 기존 엔진/P5 exact-entry 원장과 exact timestamp로 매치되는 cohort를 사전 고정 |
| primary estimand | common-entry `Δ_frame = net_engine_semantics - L3_net` |
| 성분 | synthetic/recorded entry × top-book/3-level depth × L3 cap/engine terminal의 2×2×2 factorial |
| 산출 | match/exclusion flow, 연도별 paired day-block CI, 성분 기여·residual, 결측 bounds를 하나의 receipt에 연결 |
| 실행 제한 | 기존 기록과 재생 의미론만 사용하며 **엔진 실행 0회** |
| 중단 | SHA/vector equivalence 실패, exact-entry 계약 실패, 양년 방향 불일치, 봉인 성분 설명력 합계가 aggregate gap의 50% 미만, 또는 결측 bounds가 결론을 뒤집는 경우 |

U7-F0가 위 계약을 통과해도 엔진 실행은 자동으로 시작되지 않는다. 별도 봉인, 명시적 사용자 승인, 시행 예산 및 새 evidence chain이 필요하다.
