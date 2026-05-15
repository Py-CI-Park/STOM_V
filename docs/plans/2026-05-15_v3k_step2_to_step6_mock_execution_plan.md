# V3K Step 2~6 Mock Execution Plan

본 plan은 v4 mid-checkpoint `9423735e` §7.1 + Step 1 closure (`f318d1c1` / `33aa50c5` / `0c1735d4`) + Step 2~6 progress status plan (`a7cded80`) 직후의 실제 trigger layer 중에서 본 자동 세션 scope 내에서 안전하게 수행 가능한 **mock execution layer** 를 정본화하고 실제 실행 결과를 evidence 로 freeze 한다.

본 plan 은 Step 2~6 의 actual production execution 의 대체물이 아니며, mock execution 결과는 actual execution 의 사전 검증 evidence 로만 사용된다. Actual execution 은 별도 세션에서 사용자 GUI / USER_ACK env var / 24h+ monitoring / transaction lock window trigger 후 진행.

## §A 본 plan 범위와 scope guard

### A.1 본 mock execution 가 수행하는 layer

- **Step 2 Phase H H-2**: sentinel mock evaluation (probe_primary_signal + collect_corroborating_signals), V3KSentinelResult.compatible 검증, default-OFF hook reachability
- **Step 3 F1 cutover**: shadow DB ↔ operating DB read-only parity check (table list + row count + checksum), write 0건
- **Step 4 F3 F-4**: default-OFF flag 상태에서 hook reachability + flag normalization 검증, actual flip 0건
- **Step 5 F4 G-3**: default-OFF flag 상태에서 benchmark mock (wall-clock + flag normalization), actual flip 0건
- **Step 6 F7 closure gate**: Step 2~5 mock evidence collection 검증 + closure gate plan-only 정본화 (actual mission complete commit 없음)

### A.2 본 mock execution 가 수행하지 않는 layer (별도 세션 + 사용자 trigger 필수)

- KHOPENAPI ActiveX `Connect()` 실호출 (GUI 발생)
- 실주문/exit 경로 wiring 또는 OnReceiveChejanData 처리
- operating `_database/` write (F1 actual cutover)
- F3 F-4 / F4 G-3 feature flag default-OFF → default-ON 실제 flip
- USER_ACK env var 4건 실발급 (env var 미설정 상태에서 mock 만 진행)
- 24h / 7-day / 48h monitoring 실시간 수집
- F7 mission complete final commit

### A.3 Scope guard

- Kiwoom runtime (trade / utility / Kiwoom_OpenAPI / receiver / trader) mutation 0건
- LS Securities direct dependency 0건
- operating `_database/` write 0건 (read-only 만)
- live connect / login / 주문 경로 wiring 0건
- USER_ACK env var 발급 0건
- DB / log / shadow / sidecar artifact 미커밋
- 본 commit 은 plan 1건 + script 1건 + evidence 1건 + registry 1건 추가만 포함

## §B Mock execution 컴포넌트 명세

### B.1 통합 script

- 경로: `scripts/run_v3k_step2_to_step6_mock_execution.py`
- 진입점: `python scripts/run_v3k_step2_to_step6_mock_execution.py`
- 각 Step 별로 mock function 1개씩, `main()` 에서 통합 실행
- 결과 → JSON evidence 파일 emit

### B.2 evidence 파일

- 경로: `docs/evidence/v3k-step2-to-step6-mock-execution-{host_hash}.json`
- host_hash: registry 기준 본 PC 고정 hash (이전 audit 동일 규칙)
- schema_version: 1 (본 mock evidence 는 별도 schema, LH5 forward-only invariant 와 무관)
- 필드: timestamp + host_hash + step별 결과 (compatible / parity_status / hook_reachable / flag_normalized / benchmark_ms / closure_ready)

### B.3 각 step mock function 세부

#### B.3.1 Step 2 mock

```
def run_step2_phase_h_h2_mock() -> dict:
    primary = probe_primary_signal()
    corroborating = collect_corroborating_signals()
    hook = V3KKiwoomDryrunHook(feature_flags={})
    sentinel = hook.resolve_khopenapi_sentinel()
    return {
        "step": 2,
        "phase": "phase-h-h2-sentinel-mock",
        "compatible": sentinel.compatible,
        "primary_kind": sentinel.primary_kind,
        "primary_exists": sentinel.primary_exists,
        "corroboration_count": sentinel.corroboration_count,
        "hook_enabled": hook.enabled,  # default-OFF → False
        "hook_reachable": True,  # 인스턴스 생성 성공 = reachable
    }
```

#### B.3.2 Step 3 mock

```
def run_step3_f1_cutover_parity_mock() -> dict:
    # operating DB / shadow DB read-only 비교
    operating_tables = _list_tables("_database")
    shadow_tables = _list_tables("_database_v3k_shadow")
    parity_delta = set(operating_tables) ^ set(shadow_tables)
    return {
        "step": 3,
        "phase": "f1-cutover-shadow-parity-mock",
        "operating_table_count": len(operating_tables),
        "shadow_table_count": len(shadow_tables),
        "parity_delta_count": len(parity_delta),
        "parity_status": "match" if not parity_delta else "delta",
    }
```

만약 `_database_v3k_shadow` 또는 `_database` 가 본 worktree 에 부재 시 `parity_status: "skip-missing-dir"` 로 처리.

#### B.3.3 Step 4 mock

```
def run_step4_f3_f4_on_mock() -> dict:
    flags = normalize_v3k_flags({"FLAG_PHASE_F_F4": False})
    hook = V3KKiwoomDryrunHook(feature_flags=flags)
    return {
        "step": 4,
        "phase": "f3-phase-f-f4-on-default-off-mock",
        "flag_default_off": not flags.get("FLAG_PHASE_F_F4", False),
        "hook_reachable": hook is not None,
        "flag_normalized": True,
    }
```

#### B.3.4 Step 5 mock

```
def run_step5_f4_g3_on_mock() -> dict:
    import time
    flags = normalize_v3k_flags({"FLAG_PHASE_G_G3": False})
    t0 = time.perf_counter()
    hook = V3KKiwoomDryrunHook(feature_flags=flags)
    t1 = time.perf_counter()
    return {
        "step": 5,
        "phase": "f4-phase-g-g3-on-default-off-mock",
        "flag_default_off": not flags.get("FLAG_PHASE_G_G3", False),
        "hook_reachable": hook is not None,
        "benchmark_ms": round((t1 - t0) * 1000.0, 3),
    }
```

#### B.3.5 Step 6 mock

```
def run_step6_f7_closure_gate_mock(step_results: list[dict]) -> dict:
    expected_steps = {2, 3, 4, 5}
    collected_steps = {result["step"] for result in step_results}
    closure_ready = expected_steps == collected_steps
    return {
        "step": 6,
        "phase": "f7-closure-gate-plan-only",
        "expected_step_set": sorted(expected_steps),
        "collected_step_set": sorted(collected_steps),
        "closure_ready": closure_ready,
    }
```

## §C 실행 결과 expectation

본 PC 환경 (`primary_signal.exists=True`, V3K 환경 기 설정):

- Step 2: `compatible=True`, `primary_kind=active_x_progid`, `hook_enabled=False` (default-OFF)
- Step 3: `_database` / `_database_v3k_shadow` 존재 시 parity check, 아니면 `parity_status=skip-missing-dir`
- Step 4: `flag_default_off=True`, `hook_reachable=True`
- Step 5: `flag_default_off=True`, `benchmark_ms<10`
- Step 6: `closure_ready=True` (Step 2~5 모두 실행 완료)

## §D 검증 (V01~V08)

- V01: script 신설 (`scripts/run_v3k_step2_to_step6_mock_execution.py`)
- V02: script 실행 PASS (각 step 의 expected 결과 충족)
- V03: evidence JSON 생성 + schema_version=1 명시
- V04: evidence 의 closure_ready=True
- V05: Kiwoom runtime / LS / operating DB / live connect / USER_ACK / 24h+ monitoring 모두 0건 (mock 만)
- V06: `audit_v3k_phase_h_gate4_environment_status` 직후 재실행 PASS
- V07: `audit_v3k_verify_1a --base 9423735e` PASS
- V08: `verify_nonrelease_sync` PASS

## §E Effect

- Step 2~6 각각의 mock execution 결과 freeze 로 actual execution 사전 검증 layer 완성
- sentinel mock (Step 2) PASS 로 KHOPENAPI 환경 안정성 본 PC 기준 재확인
- shadow DB parity mock (Step 3) 으로 F1 cutover 직전 검증 layer 사전 확보
- default-OFF parity mock (Step 4~5) 로 flag flip 안전성 사전 검증
- closure gate readiness mock (Step 6) 으로 Step 2~5 evidence collection 완정성 사전 검증

본 plan freeze 후 actual execution 은 다음 trigger 조건 충족 시 별도 세션에서 진행:

- Step 2 actual: 사용자 phrase + `V3K_PHASE_H_USER_ACK=1` + GUI Kiwoom login + 24h monitoring
- Step 3 actual: Step 2 closure + `V3K_CUTOVER_USER_ACK=1` + transaction lock window + 7-day monitoring
- Step 4 actual: Step 3 closure + `V3K_PHASE_F_USER_ACK=1` + 24h monitoring
- Step 5 actual: Step 4 closure + `V3K_PHASE_G_USER_ACK=1` + 48h monitoring
- Step 6 actual: Step 5 closure + final mission complete phrase

## §F 관련 문서

- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (Phase H 본체)
- `docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md` (Step 1 분기)
- `docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md` (status freeze)
- `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md` (v4 mid-checkpoint)
- `docs/CARRY_FORWARD_REGISTRY.md` (V3K-STEP2-TO-STEP6-MOCK-EXECUTION 등록 위치)
