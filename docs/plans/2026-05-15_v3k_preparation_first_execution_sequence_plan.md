# V3K 준비 선행 / 실제 실행 순서 기준 변경 계획

## §0. 문서 목적

본 문서는 2026-05-15 사용자 질의에 대한 운영 기준을 정본화한다.

사용자 질의 요지:

```text
페이지 1은 마지막으로 이동하고 2,3,4,5 진행 후 1은 나중에 하는 것으로 가능한가?
미리 준비해두기는 미리 코드 업데이트를 의미하는가?
```

결론:

```text
실제 실행(actual execution) 순서는 변경할 수 없다.
다만 실제 실행을 하지 않는 default-OFF 준비 코드/검증 스크립트/rollback 장치는
Phase H H-2 live dry-run 전에 선행할 수 있다.
```

따라서 본 문서는 기존 `docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md`를 폐기하지 않고, 그 위에 **준비 선행(preparation-first) 기준**을 보완한다.

---

## §1. 용어와 범위

### §1.1 V3K 목표 재확인

V3K는 다음 목표를 뜻한다.

```text
V3K = V3 기능 + Kiwoom 유지
```

- `STOM_Version_2U_C`에 V3의 학습/분석/DB/backtest/realtime/UI 기능을 가능한 한 반영한다.
- LS증권 REST/TR/REAL/WebSocket 직접 의존은 제외한다.
- Kiwoom OpenAPI 기반 runtime은 유지한다.
- 기존 운영 `_database/`, Kiwoom live 주문/청산 경로, feature flag default-OFF 원칙은 보호한다.

### §1.2 “페이지 1~5”의 재해석

본 문서에서 사용자가 말한 “페이지 1~5”는 역사적 `Page 079~083` 문서 번호가 아니라, 현재 남은 큰 실행 단계를 쉽게 부른 표현으로 해석한다.

| 사용자 표현 | 현재 V3K 단계 | 실제 의미 |
| ---: | --- | --- |
| 페이지 1 | 남은 단계 1 / Step 2 | Phase H H-2 Kiwoom live dry-run actual |
| 페이지 2 | 남은 단계 2 / Step 3 | F1 actual DB cutover |
| 페이지 3 | 남은 단계 3 / Step 4 | Phase F F-4 ON 전환 |
| 페이지 4 | 남은 단계 4 / Step 5 | Phase G G-3 ON 전환 |
| 페이지 5 | 남은 단계 5 / Step 6 | F7 closure gate |

### §1.3 준비와 실행의 구분

| 구분 | 정의 | Phase H H-2 actual 전 선행 가능 여부 |
| --- | --- | --- |
| 준비 코드 | default-OFF adapter, read-only dry-run, parity/checksum/rollback 검증, audit, evidence schema | 가능 |
| 준비 문서 | plan, registry, update_log, approval packet, rollback packet | 가능 |
| mock/preflight | 운영 DB write 없이 현재 상태를 읽고 비교하는 검증 | 가능 |
| actual execution | live connect/login, 운영 DB write, feature flag ON, closure 선언 | 불가 |

---

## §2. 기준 변경 선언

### §2.1 이전 기준

이전 운영 기준은 다음처럼 해석되기 쉬웠다.

```text
다음 실제 작업은 Phase H H-2 live dry-run이며,
그 전에는 Step 3~6 관련 작업을 진행하지 않는다.
```

이 해석은 안전하지만, 실제 실행 전 준비 코드까지 막는 것으로 오해될 수 있다.

### §2.2 변경된 기준

본 문서 이후 기준은 다음으로 변경한다.

```text
Actual execution 순서:
Phase H H-2 live dry-run → F1 DB cutover → Phase F F-4 ON → Phase G G-3 ON → F7 closure

Preparation 순서:
F1/F3/F4/F7 준비 코드와 검증 장치는 Phase H H-2 actual 전에 선행 가능
```

즉, **페이지 1 actual을 마지막으로 이동하는 것은 불가**하지만, **페이지 2~5의 준비 코드/문서/검증을 먼저 작성하는 것은 가능**하다.

### §2.3 변경되는 것

- Step 3~6 actual을 위한 준비 패키지를 Phase H actual 전에도 작성할 수 있다.
- “준비 완료”와 “actual 실행 완료”를 별도 상태로 기록한다.
- 준비 패키지는 default-OFF, read-only, no-USER_ACK, no-operating-DB-write를 기본 조건으로 한다.
- 준비 패키지 commit은 runtime activation으로 계산하지 않는다.

### §2.4 변경되지 않는 것

- Phase H H-2 actual은 여전히 첫 actual execution gate다.
- F1 actual DB cutover는 Phase H H-2 actual + 24h monitoring evidence 없이 금지다.
- Phase F F-4 ON은 F1 cutover + 7-day monitoring evidence 없이 금지다.
- Phase G G-3 ON은 Phase F closure 없이 금지다.
- F7 closure는 Step 2~5 actual closure 없이 금지다.
- `V3K_PHASE_H_USER_ACK`, `V3K_CUTOVER_USER_ACK`, `V3K_PHASE_F_USER_ACK`, `V3K_PHASE_G_USER_ACK`는 actual gate에서만 사용한다.

---

## §3. 허용되는 준비 코드 업데이트

### §3.1 F1 DB cutover 준비

허용:

- shadow DB ↔ operating DB read-only parity 검사 보강
- table/row-count/checksum 산출 스크립트
- transaction lock window 사전 검증 스크립트
- rollback packet/checklist 생성기
- approval phrase guard / USER_ACK guard
- cutover 직전 preflight audit

금지:

- 운영 `_database/` write
- shadow → operating 실제 복사/전환
- transaction lock 실제 진입
- cutover 완료 registry 선언

### §3.2 Phase F F-4 ON 준비

허용:

- feature flag default-OFF 상태 검증
- default-OFF vs simulated-ON parity dry-run
- analyzer/strategy adapter reachability smoke
- rollback-to-OFF script/audit
- approval packet 생성

금지:

- default-ON 전환
- trading decision path에 analyzer output 직접 연결
- Kiwoom 주문/청산/exit runtime wiring 변경

### §3.3 Phase G G-3 ON 준비

허용:

- default-OFF benchmark harness
- large workload parity/benchmark 기준 재검증
- ±15% parity / ±20% benchmark 판정 스크립트
- rollback packet/checklist

금지:

- G-3 default-ON 전환
- live runtime workload 확대
- 성능 회귀 허용 범위 미검증 상태의 ON commit

### §3.4 F7 closure 준비

허용:

- closure checklist/audit script
- Step 2~5 evidence manifest schema
- final registry template
- closeout report skeleton

금지:

- V3K mission complete 선언
- F6 progress 100% 선언
- Step 2~5 actual evidence 없이 closure commit 생성

---

## §4. 준비 선행 실행 계획

### §4.1 준비 선행 lane

다음 순서는 actual execution이 아니라 **준비 코드/문서 선행 lane**이다.

| 순서 | 작업 | 산출물 | 검증 | actual side effect |
| ---: | --- | --- | --- | --- |
| P0 | 본 기준 변경 문서화 | 본 plan + registry | diff check, audit | 없음 |
| P1 | F1 cutover prep package | read-only parity/checksum/rollback/preflight script | py_compile, dry-run, no DB write audit | 없음 |
| P2 | Phase F F-4 prep package | default-OFF parity/approval/rollback script | smoke, verify_1a, flag OFF audit | 없음 |
| P3 | Phase G G-3 prep package | benchmark/parity/rollback script | benchmark dry-run, threshold audit | 없음 |
| P4 | F7 closure prep package | closure manifest/checklist audit | mock evidence validation | 없음 |
| P5 | 준비 선행 중간 점검 | update_log + registry | full guard suite | 없음 |

### §4.2 actual execution lane

준비 lane이 끝나도 actual 순서는 변하지 않는다.

| 순서 | actual 단계 | 사전 조건 | monitoring |
| ---: | --- | --- | --- |
| A1 | Phase H H-2 live dry-run | 사용자 phrase + `V3K_PHASE_H_USER_ACK=1` + GUI Kiwoom login + gate4 audit PASS | 24h |
| A2 | F1 DB cutover | A1 closure + `V3K_CUTOVER_USER_ACK=1` + transaction lock window + parity ±0 | 7-day |
| A3 | Phase F F-4 ON | A2 closure + `V3K_PHASE_F_USER_ACK=1` + parity ±0 | 24h |
| A4 | Phase G G-3 ON | A3 closure + `V3K_PHASE_G_USER_ACK=1` + parity ±15% + benchmark ±20% | 48h |
| A5 | F7 closure gate | A1~A4 closure + final phrase | 0 |

### §4.3 권장 즉시 다음 작업

본 commit 이후 실제로 진행할 첫 작업은 다음 중 하나다.

```text
P1: F1 cutover prep package
```

P1은 Phase H H-2 actual 전에도 가능하지만, 다음 guard를 반드시 만족해야 한다.

- operating `_database/` write 0건
- live connect/login 0건
- USER_ACK env var 발급 0건
- default-OFF 유지
- LS direct dependency 0건
- rollback/checksum/preflight는 read-only 또는 temp-only

---

## §5. 검증 기준

각 준비 패키지는 최소 다음 검증을 통과해야 한다.

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

작업 성격별 추가 검증:

| 준비 패키지 | 추가 검증 |
| --- | --- |
| F1 prep | operating DB 파일 timestamp/hash 변화 없음, write-attempt flag false |
| Phase F prep | feature flag default-OFF, simulated-ON parity only |
| Phase G prep | benchmark dry-run 결과와 threshold 판정 JSON |
| F7 prep | Step 2~5 actual evidence가 없으면 closure_ready=false |

---

## §6. rollback / stop 조건

즉시 중단 조건:

- operating `_database/` write가 발생한 경우
- live connect/login이 사용자 승인 없이 호출된 경우
- USER_ACK env var가 준비 단계에서 설정된 경우
- feature flag가 default-ON으로 바뀐 경우
- LS Securities direct dependency가 추가된 경우
- Kiwoom 주문/청산/exit 경로가 변경된 경우

rollback 원칙:

- 준비 패키지는 작은 commit 단위로 유지한다.
- runtime side effect가 없어야 하므로 rollback은 해당 commit revert로 충분해야 한다.
- 운영 DB나 live runtime state를 복구해야 하는 상황이 발생했다면 준비 기준 위반으로 간주한다.

---

## §7. 현재 상태와 다음 인계

현재 상태:

- `STOM_Version_2U_C` HEAD `81117eed` 기준 Step 2~6 mock execution PASS
- host_identifier `9024e3b9`
- KHOPENAPI primary signal exists, `khopenapi_compatible=True`
- Gate4 environment_status audit branch는 `unblocked`
- actual live dry-run / DB cutover / flag ON / closure는 아직 미실행

다음 인계 문장:

```text
V3K actual 순서는 유지한다. 다만 Phase H H-2 actual 전에 F1/F3/F4/F7 준비 코드와 검증 장치를 default-OFF/read-only/no-USER_ACK 조건으로 선행할 수 있다. 다음 추천 작업은 P1 F1 cutover prep package이며, 실제 F1 cutover는 Phase H H-2 actual + 24h evidence 후에만 가능하다.
```

---

## §8. 관련 문서

- `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
- `docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md`
- `docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md`
- `docs/plans/2026-05-15_v3k_step2_to_step6_mock_execution_plan.md`
- `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md`
- `docs/CARRY_FORWARD_REGISTRY.md`
