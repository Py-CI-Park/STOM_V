# Alpha Lab Evidence Chain v2 실행·감사 정정 보고서 (G001 + G008)

- 작성일: 2026-07-14
- 대상: Ultragoal G001(연구 증거 체인) 및 G008(정정·감사 해소)
- 이번 정정 기준 커밋: `98fc8469`, `a634ff74`, `098e90ca`, `c197df20`, `d3a47b3f`
- 문서 지위: 구현·검증 이력의 정정 기록이다. 전략 승격 승인, 보호 DB 작업, 실전 또는 엔진 실행 승인이 아니다.
- 실행 제한: 이 문서 갱신에서는 테스트·git·lint·formatter를 실행하지 않았다. 보호 DB를 열거나 읽고 쓰지 않았고 엔진도 실행하지 않았다.

## 1. cleaner 상태와 현재 결론

1~3차 cleaner 실패 뒤의 **4차 cleaner도 실패**했다. 4차는 **blocker 9건**을 기록했으며, 이 문서는 이를 PASS나 인수 완료로 바꾸지 않는다. 아래 커밋열은 그 9건에 대응하는 구현 변경 기록일 뿐, 새 cleaner 재검토가 통과했다는 증거가 아니다.

| cleaner 반복 | 당시 상태 | 결과 |
|---|---|---|
| 1차 (`198db293`) | blocking 6, advisory 2 발견 | 실패; G001 완결 아님 |
| 2차 | seal/identity/legacy read 보정 뒤 consumer·producer 경계 결함 발견 | 실패; 추가 수정 필요 |
| 3차 | receipt·catalog·PRE/POST 결박 보정 뒤 journal/공개 write 경계 결함 발견 | 실패; 추가 수정 필요 |
| 4차 | blocker 9건 발견 | **실패**; 새 PASS 증거 없음 |

현재의 제한적 결론은 v2 producer chain과 v2 bridge가 아래 계약을 구현한다는 것이다. 이는 provenance·쓰기 전 검증의 코드 계약에 한정되며, 연구 가설·성능·엔진 의미론·보호 DB 결과·실전 성공을 뜻하지 않는다.

## 2. 4차 blocker 대응 구현

| 기준 커밋 | 구현된 대응 |
|---|---|
| `98fc8469` | 사전등록(prereg)에 결박된 canonical authority ledger를 사용하도록 정리했다. |
| `a634ff74` | 공식 promotion manifest 발급자를 단일화하고, evidence ID에 따른 canonical manifest 경로만 authority로 인정했다. local dynamic import/load target은 허용 목록·검증 경로 밖이면 fail-closed한다. |
| `098e90ca` | legacy registry를 authority ledger와 분리하고, promotion catalog 출력·receipt를 evidence-ID namespace에 고정했다. |
| `c197df20` | PRE intent의 target DB pre-state를 실제 write lock 안에서 다시 검사한다. 인증되지 않은 전체 mutation primitive를 제거하고, v2 검증 경계 밖의 완전 등록 경로를 제공하지 않는다. |
| `d3a47b3f` | canonical POST의 경로·PRE 결박·live target DB SHA-256·backup SHA-256을 강하게 검증한다. bridge 공개 export는 v2 전용으로 제한했고 B1 writer는 실행 가능한 writer가 아닌 historical non-executable archive로 퇴역했다. |

위 표는 해당 구현의 범위를 요약한다. 각 항목은 v2 authority의 입력·경로·precondition을 강화하지만, 실제 보호 전략 DB에 적용되었거나 엔진에서 실행되었다는 주장은 아니다.

## 3. 현재 공식 생산자 체인과 authority 경계

공식 producer chain은 임의 JSON 조립이나 consumer 우회가 아니라 다음 순서로만 authority artifact를 만든다.

```text
finalize_prereg
  → issue_gate_receipt_v2
  → claim_gate_receipt_v2
  → append_trial_v2 (prereg-bound canonical authority ledger)
  → issue_promotion_manifest_v2 (공식 단일 issuer, canonical path)
  → catalog builder의 evidence-ID namespace PRE receipt
  → verify_promotion_manifest
  → register_conditions_v2 (명시적으로 호출된 경우만)
```

- SEALED prereg의 `dependency_roots`에서 Python closure를 재도출한다. root package `__init__.py` 및 local dynamic import/load target도 검증 대상이며, 선언과 재도출 결과가 다르면 거부한다.
- dynamic 실행은 선언되지 않았거나 검증할 수 없는 target을 추정해 계속하지 않는다. 허용·해결·hash 검증을 모두 만족하지 못하면 fail-closed한다.
- v2 ledger evidence ID는 canonical receipt/claim, immutable input/result artifact, canonical candidate set을 결합해 재구성한다. candidate identity는 이름뿐 아니라 buy/sell expression SHA-256 쌍이다.
- legacy registry 및 Ledger v1 역사 자료는 읽기 호환·역사 보존 대상이다. canonical authority ledger 또는 v2 promotion authority를 제공하지 않는다.
- promotion manifest는 공식 issuer가 evidence ID별 canonical path에 발급한 PRE manifest만 인정한다. 복사본, 별도 issuer 또는 임의 경로의 manifest는 authority가 아니다.
- catalog의 promotion DB와 receipt는 evidence ID namespace에 위치해야 한다. legacy 기본 catalog 출력이나 alias는 promotion authority로 승격되지 않는다.

## 4. PRE/POST와 DB write 경계

`PRE`는 등록 전 authority 상태이지 승격 승인이나 DB 변경 결과가 아니다. v2 등록은 manifest, catalog PRE receipt, candidate set/SHA, source hash 및 canonical authority ledger를 검증한 후에만 PRE intent를 남긴다.

1. PRE intent와 PRE hash anchor는 exclusive write·fsync로 기록된다.
2. DB mutation 직전에, **write lock 안에서** live target DB bytes의 SHA-256을 PRE `pre_sha256`와 재비교한다. 다르면 backup 또는 mutation 전에 거부한다.
3. POST는 evidence ID별 canonical sibling 경로에 한 번만 기록한다. POST에는 PRE ref/anchor, candidate outcomes, target DB pre/post SHA-256 및 backup ref/SHA-256이 결박된다.
4. POST verifier는 canonical POST 경로, PRE 결박, 현재 live DB SHA-256 및 backup bytes SHA-256을 확인한다. 복사한 POST, stale live DB, tampered backup 또는 orphan POST는 통과하지 않는다.
5. PRE만 있고 POST가 없으면 `INCOMPLETE_REQUIRES_RECONCILIATION`이다. 자동 recovery·재시도·새 POST 생성으로 해소하지 않는다.

`register_conditions()` legacy 공개 함수는 DB 접근 전에 `LegacyPromotionBlockedError` (`legacy-promotion-blocked`)를 발생시킨다. `register_conditions_v2()`만 공개 write authority이며, bridge package도 v2 public export만 노출한다. private helper나 historical B1 archive는 mutation authority가 아니다.

이 문서는 `_database` 및 `_database_v3k_shadow` 보호 전략 DB에 대해 검증·변경·등록·backup 생성이 있었다고 주장하지 않는다.

## 5. 검증 기록과 비주장

- 이전 4모듈 focused suite의 **136 passed**는 후속 변경 이전의 역사 기록이다. 현재 5모듈 전체 결과나 4차 cleaner PASS로 재사용할 수 없다.
- 현재 커밋열의 bridge focused 검증 기록은 다음 명령의 **20 passed**다.

```powershell
python -m pytest tests/unit/test_alpha_bridge.py -q
```

- 이 bridge 결과는 synthetic `tmp_path` DB와 producer chain fixture에서 canonical PRE/POST, lock 안 pre-state 재검사, copied/stale/tampered POST 거부, backup hash 검증, legacy fence, v2-only export 및 B1 archive 경계를 다룬다.
- producer-chain의 discipline/gates/catalog을 bridge와 함께 묶는 현재 5모듈 전체 재검증은 **pending**이다. 따라서 이 문서는 136 passed를 현재 결과로 쓰지 않으며 cleaner 통과도 주장하지 않는다.
- 본 문서 갱신 자체에서는 위 명령을 포함한 테스트를 실행하지 않았다.
- 단위 시험 결과는 provenance consistency 계약의 증거일 뿐, 연구 가설의 진실성, 전략 수익성, 사용자 승인, 시행 예산, 등록 승인, 운영 승인, 보호 DB 결과 또는 엔진 의미론을 증명하지 않는다.