# Alpha Lab Evidence Chain v2 실행·감사 기록 (G008)

- 작성일: 2026-07-14
- 대상: G008 정정·감사 해소 기록 (G001/G002 상태 변경 기록이 아님)
- 현재 코드 기여 HEAD: `86e3ee7`
- 문서 지위: G008의 구현·review·검증 closure를 기록한다. 전략 승격 승인, 보호 DB 작업, 엔진 실행 또는 실전 운용 승인은 아니다.
- 실행 제한: 이 문서 갱신에서 테스트·git·lint·formatter·엔진을 실행하지 않았고, 보호 DB를 접근·읽기·쓰기하지 않았다.

## 1. 현재 closure와 근거/추론의 구분

| 구분 | 관찰된 근거 | 기록 가능한 결론 |
|---|---|---|
| 코드 | `86e3ee7`의 기여 | 지원되는 모든 runlab 경로가 schema-v2 canonical receipt+claim, 정확히 sealed된 dependency root, manifest-only stage에 결박된다. |
| authority | `agent://153-153-G008AuthorityVerdict`: `PASS/CLEAR`, HIGH/MEDIUM 없음 | authority 검토 lane은 현재 차단 사항 없이 통과했다. |
| runner | `agent://190-G008PycClosureVerdict`: `PASS/CLEAR`, findings 비어 있음, `unblock_goals: true` | 최종 runner 검토 lane은 현재 차단 사항 없이 통과했다. |
| 단위 검증 | 아래 관찰 결과 | 계약 시험은 현재 code surface에서 통과했다. |

**추론의 한계:** 위 근거는 provenance, fencing, 검증 계약의 closure만 뒷받침한다. 수익성, 연구 가설의 진실성, 전략/운영 승격, 사용자 승인, 보호 DB 결과, 엔진 의미론 또는 실거래 성공을 뜻하지 않는다.

G008의 문서상 상태는 **implementation/review/verification closure**다. G001/G002의 Ultragoal 상태 변경은 별도 ledger action이며, 이 문서는 그 변경을 선행 주장하지 않는다. `.gjc`는 audit state일 뿐 승인·등록·운영 상태가 아니다.

## 2. 역사적 실패와 현재 해소

| 검토 | 당시 결과 | 현재 기록 |
|---|---|---|
| 1차 cleaner (`198db293`) | blocking 6, advisory 2 | 역사적 실패 |
| 2차 cleaner | consumer·producer 경계 결함 | 역사적 실패 |
| 3차 cleaner | journal/공개 write 경계 결함 | 역사적 실패 |
| 4차 cleaner | blocker 9건 | 역사적 실패; 현재 terminal result가 아님 |
| reviews `182`, `185`, `187`, `188`, `189` | 구체적 bypass 발견으로 실패 | 발견된 bypass가 후속 hardening을 유도했다. 현재 blocker가 아니다. |
| authority `153` / runner `190` | `PASS/CLEAR` | 현재 closure 근거 |

이력의 실패를 삭제하거나 PASS로 재기록하지 않는다. 반대로 4차 cleaner 실패를 현재 최종 결론으로도 사용하지 않는다.

## 3. 현재 canonical producer·runner chain

| 구간 | 현재 계약 |
|---|---|
| producer | `finalize_prereg → issue_gate_receipt_v2 → claim_gate_receipt_v2 → append_trial_v2 → issue_promotion_manifest_v2 → catalog PRE receipt → verify_promotion_manifest` 순서의 canonical artifact만 authority 입력이다. |
| schema/closure | sealed `dependency_roots`에서 Python closure를 재도출하고, source-only digest-attested runner import를 요구한다. root `__init__.py`와 local dynamic import/load target도 선언·해결·hash 검증을 모두 만족해야 한다. |
| identity/stage | authority/live/stage/runner identity를 유지하며, stage는 manifest-only다. 복사본·별도 issuer·임의 경로 manifest 및 임의 Python executable은 허용하지 않는다. |
| runner handoff | private inherited Windows event handoff를 사용하고 Job Object pre-ack cleanup을 수행한다. |
| legacy | legacy registry, Ledger v1, historical B1 archive 및 legacy public path는 역사 보존/읽기 호환으로 fenced되며 v2 authority나 mutation authority가 아니다. |

## 4. PRE/POST·catalog·ledger·promotion 계약

| 대상 | 계약 |
|---|---|
| ledger/receipt/claim | canonical receipt+claim과 prereg-bound canonical authority ledger로 evidence identity를 재구성한다. candidate identity는 이름과 buy/sell expression SHA-256 쌍을 포함한다. |
| PRE | manifest, catalog PRE receipt, candidate set/SHA, source hash, canonical ledger 검증 뒤에만 남긴다. PRE intent/hash anchor는 exclusive write·fsync로 기록한다. |
| write 직전 | exclusive write lock 안에서 live target DB SHA-256을 PRE `pre_sha256`와 재검사한다. 불일치는 backup 또는 mutation 전에 거부한다. |
| POST | evidence-ID canonical sibling 경로에 한 번만 기록하고 PRE ref/anchor, outcome, DB pre/post SHA-256, backup ref/SHA-256을 결박한다. copied/stale/tampered/orphan POST는 거부한다. |
| catalog/promotion | catalog promotion DB와 receipt는 evidence-ID namespace여야 하며, 공식 단일 issuer의 canonical PRE manifest만 promotion authority다. |
| 미완료/legacy | PRE만 존재하면 `INCOMPLETE_REQUIRES_RECONCILIATION`이며 자동 recovery·retry·POST 생성으로 해소하지 않는다. legacy `register_conditions()`는 `LegacyPromotionBlockedError`로 DB 접근 전 차단되고 v2 public surface만 write authority다. |

## 5. 관찰된 현재 검증

| 범위 | 관찰 결과 |
|---|---|
| `python -m pytest tests/unit/test_alpha_runlab.py -q` | `13 passed` |
| 5-file evidence chain: `test_alpha_discipline.py`, `test_alpha_gates.py`, `test_alpha_bridge.py`, `test_alpha_catalog.py`, `test_alpha_runlab.py` | `396 passed` |
| `python -m pytest tests/unit -k alpha -q` | `921 passed, 5 skipped, 4238 deselected` |

`pytest_asyncio` 경고는 별도 경고로 관찰되었으며 시험 실패로 분류하지 않는다. 이 문서 갱신은 위 결과를 재실행한 것이 아니라 제공된 현재 검증 기록을 감사용으로 정리한 것이다.

## 6. 커밋 범위와 운영상 비주장

| 범주 | 관찰된 사실 |
|---|---|
| 현재 | `86e3ee7` |
| 대표 prior hardening | `98fc8469`, `a634ff74`, `098e90ca`, `c197df20`, `d3a47b3f` |
| branch history | baseline `a994d9fe`부터 `86e3ee7`까지 **85 commits**가 관찰된다. 이는 관찰된 branch history 수량이며, 위 다섯 커밋만으로 G008 전체를 구성한다는 주장이 아니다. |

보호 DB 접근·write·backup 생성, 엔진 실행, live registration, 전략 promotion 또는 운영 등록은 이 기록의 대상도 결과도 아니다. 시험은 계약을 증명할 뿐 그러한 운영 행위를 대체하지 않는다.