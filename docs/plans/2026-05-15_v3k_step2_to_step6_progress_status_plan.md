# V3K Step 2~6 진척 Status Plan

본 plan은 v4 mid-checkpoint `9423735e` §7.1 + Step 1 closure (`f318d1c1` / `33aa50c5` / `0c1735d4`) 이후 V3K 잔여 단계 (Step 2~6) 의 현재 상태, 다음 trigger 조건, 자동 vs 수동 경계를 단일 문서로 정리한 운영 status 정본이다. 본 문서는 implementation plan 이 아니라 mission state-of-the-art 의 freeze 보고서이며, 각 Step 의 실제 execution 은 별도 plan + 사용자 명시 USER_ACK trigger 후 별도 세션에서 진행한다.

## §A 현재 V3K mission 진척 요약

- **F6 progress (S0–S4 5-stage)**: 50.0% (v4 mid-checkpoint 마일스톤, `9423735e`)
- **Step 1 closure 추가 반영**: +0% (LH 거버넌스 종결, F6 stage 진행은 아님)
- **잔여 Step 5건**: Phase H H-2 본체 dryrun → F1 DB cutover → F3 F-4 ON → F4 G-3 ON → F7 closure gate
- **현 활성 approval gate**: `phase-h-h2-h3-live-dryrun-await-user-approval`
- **현 활성 phrase**: `I approve phase-h-h2-h3-live-dryrun-await-user-approval only`
- **다음 활성 gate (Step 2 execution 후)**: `f1-actual-db-cutover-await-user-approval`

## §B Step 2 — Phase H H-2 본체 dryrun

### B.1 plan 상태

- 본체 plan: `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (정본화 완료)
- §K.1 ~ K.5 합의 반영 완료 (Step 1 결과 `33aa50c5`)
- §K.6 / K.7 미정 사안은 미래 분기 plan 으로 위임 (Phase A §K.7 freeze 패턴 준수)
- approval prep plan: `docs/plans/2026-05-13_v3k_page_052_phase_h_h2_h3_live_dryrun_approval_prep_plan.md`
- gate4 환경 audit: `scripts/audit_v3k_phase_h_gate4_environment_status.py` (Step 1 결과 `f318d1c1`)
- historical gate4 audit: `scripts/audit_v3k_phase_h_gate4_blocked_environment.py` (`b6327b30` frozen)
- environment 상태: 본 PC 기준 `primary_signal.exists=True`, `khopenapi_compatible=True`, `schema_version=2` (LH5 forward-only 준수)

### B.2 다음 trigger 조건 (4건 모두 충족 필수)

1. **사용자 명시 phrase 발급**: `I approve phase-h-h2-h3-live-dryrun-await-user-approval only`
2. **env var 발급**: `V3K_PHASE_H_USER_ACK=1`
3. **gate4 environment_status audit 직전 재실행**: branch=unblocked 확인 + `primary_signal.exists=True` 확인 + V3K runtime untouched 확인
4. **registry 사전 freeze 절차**: `V3K-PHASE-H-LIVE-DRYRUN-ACTUAL-APPROVAL` 헤딩 신설 (현재는 `V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED` 만 존재)

### B.3 execution 범위 (별도 세션, 본 plan scope 외)

- KHOPENAPI ActiveX login (interactive GUI, 사용자 직접 클릭 필수)
- 1 cycle 시뮬레이션 모드 dryrun (실주문/exit 경로 wiring 0건 유지)
- 거부 시나리오 전수 (login fail / handshake fail / heartbeat fail / cleanup fail / re-entry block)
- post-execution 24h heartbeat monitoring + audit 재실행
- 결과 evidence → `docs/evidence/v3k-phase-h-h2-execution-{host_hash}.json`

### B.4 자동 vs 수동 경계

| 항목 | 분류 |
|------|------|
| plan 작성/검토 | 자동 (완료) |
| gate4 audit 실행 | 자동 (완료) |
| KHOPENAPI ActiveX login | **수동 (사용자 GUI 클릭 필수)** |
| 1 cycle execution trigger | **수동 (`V3K_PHASE_H_USER_ACK=1` 발급)** |
| 24h monitoring 결과 수집 | **시간 경과 필요** |
| post-execution evidence freeze | 자동 (사용자 결과 제공 후) |

## §C Step 3 — F1 DB cutover

### C.1 plan 상태

- F1 cutover plan: 미정본화 (v4 mid-checkpoint §7.1 우선 3순위 등재)
- 의존성: Step 2 execution 완료 (KHOPENAPI live 환경에서 1 cycle dryrun 통과 + 24h 안정성 확인)
- 거버넌스: `--deliberate` ralplan 필수 (CRITICAL risk + operating `_database/` write + rollback 어려움)
- 활성 gate phrase: `I approve f1-actual-db-cutover-await-user-approval only` (현재 evaluate_approval_phrase 에 미등록)

### C.2 다음 trigger 조건 (5건 모두 충족 필수)

1. Step 2 closure (Phase H H-2 dryrun 완료 + 24h 안정성 evidence 정본화)
2. F1 cutover plan 정본화 (`--deliberate` ralplan iteration 2~5회 합의 필요)
3. 사용자 명시 phrase 발급: `I approve f1-actual-db-cutover-await-user-approval only`
4. env var 발급: `V3K_CUTOVER_USER_ACK=1`
5. F1 cutover 직전 dry-run shadow DB parity 검증 (operating DB ↔ shadow DB delta ±0)

### C.3 execution 범위 (별도 세션, 본 plan scope 외)

- shadow DB → operating DB 1회성 cutover (rollback path 사전 준비)
- transaction lock 진입 → snapshot → write → checksum 검증 → release
- 사후 7-day heartbeat monitoring (regression / drift / corruption 감시)
- 결과 evidence → `docs/evidence/v3k-f1-cutover-result-{host_hash}.json`

### C.4 자동 vs 수동 경계

| 항목 | 분류 |
|------|------|
| F1 plan ralplan iteration | 자동 |
| shadow DB parity 검증 | 자동 |
| cutover execution trigger | **수동 (`V3K_CUTOVER_USER_ACK=1` 발급)** |
| transaction lock window | **수동 (운영 시간외 / 거래 비활성 시간대 선정 필수)** |
| 7-day monitoring 결과 수집 | **시간 경과 필요** |
| rollback decision | **수동 (운영자 판단)** |

## §D Step 4 — F3 Phase F F-4 ON 전환

### D.1 plan 상태

- F3 Phase F plan: v4 mid-checkpoint §7.1 우선 4순위
- F-4 단계 ON 의존성: F1 cutover 완료 + 7-day 안정성 evidence
- 활성 gate phrase: `I approve f3-phase-f-f4-on-await-user-approval only`

### D.2 다음 trigger 조건 (4건 모두 충족 필수)

1. Step 3 closure (F1 cutover 7-day monitoring 통과)
2. F3 Phase F F-4 plan 정본화 (ralplan iteration 2~3회)
3. 사용자 명시 phrase 발급 + `V3K_PHASE_F_USER_ACK=1`
4. parity 검증 (default-ON vs default-OFF behavior delta ±0 in 1 cycle)

### D.3 execution 범위

- F-4 feature flag default-OFF → default-ON 1회성 flip
- parity dry-run (이전 cycle 결과 동일성 확인)
- 24h heartbeat monitoring
- regression 감지 시 즉시 rollback (default-OFF 복귀)

### D.4 자동 vs 수동 경계

| 항목 | 분류 |
|------|------|
| F3 F-4 plan ralplan | 자동 |
| parity 검증 | 자동 |
| flag flip execution | **수동 (`V3K_PHASE_F_USER_ACK=1`)** |
| 24h monitoring | **시간 경과 필요** |

## §E Step 5 — F4 Phase G G-3 ON 전환

### E.1 plan 상태

- F4 Phase G plan: v4 mid-checkpoint §7.1 우선 5순위
- G-3 단계 ON 의존성: F3 F-4 ON 24h 안정성 + parity 확인
- 활성 gate phrase: `I approve f4-phase-g-g3-on-await-user-approval only`

### E.2 다음 trigger 조건 (5건 모두 충족 필수)

1. Step 4 closure
2. F4 Phase G G-3 plan 정본화 (ralplan iteration 2~3회)
3. 사용자 명시 phrase 발급 + `V3K_PHASE_G_USER_ACK=1`
4. parity ±15% (large workload 변동성 허용 범위)
5. benchmark ±20% (성능 회귀 허용 범위)

### E.3 execution 범위

- G-3 feature flag default-OFF → default-ON 1회성 flip
- benchmark dry-run (CPU / memory / wall-clock 측정)
- 48h heartbeat monitoring (G-3 는 large workload 영향 가능)
- regression 감지 시 즉시 rollback

### E.4 자동 vs 수동 경계

| 항목 | 분류 |
|------|------|
| F4 G-3 plan ralplan | 자동 |
| parity / benchmark 검증 | 자동 |
| flag flip execution | **수동 (`V3K_PHASE_G_USER_ACK=1`)** |
| 48h monitoring | **시간 경과 필요** |

## §F Step 6 — F7 closure gate

### F.1 plan 상태

- F7 closure gate plan: 미정본화 (Step 2~5 모두 완료 의존)
- closure 의미: V3K mission "complete" 선언 + Kiwoom OpenAPI 의존 stack 안정화 종결
- 활성 gate phrase: 미발급 (Step 5 closure 시 신규 발급)

### F.2 다음 trigger 조건 (Step 2~5 모두 closure)

1. Step 2 closure (Phase H H-2 dryrun)
2. Step 3 closure (F1 cutover)
3. Step 4 closure (F3 F-4 ON)
4. Step 5 closure (F4 G-3 ON)
5. closure gate plan 정본화 + ralplan iteration 합의
6. 사용자 명시 phrase 발급 (Step 5 closure 시 신규 발급)

### F.3 execution 범위

- mission completion 선언 commit (registry V3K-MISSION-COMPLETE 헤딩 신설)
- F6 progress 100% 마일스톤 evidence freeze
- 잔여 거버넌스 항목 (v4 mid-checkpoint §7.2 / §7.3 잔여) 종결 처리
- 후속 mission (V4 / V3K-extension / 별도 lane) 으로 baton pass

### F.4 자동 vs 수동 경계

| 항목 | 분류 |
|------|------|
| closure plan ralplan | 자동 |
| F6 100% evidence freeze | 자동 |
| mission complete commit | **수동 (사용자 final phrase)** |

## §G 다음 trigger 매트릭스

| Step | 의존 | 자동 가능 | 사용자 trigger 필수 | 시간 경과 |
|------|------|-----------|---------------------|-----------|
| 2 | Step 1 closure (DONE) | plan, audit | phrase + `V3K_PHASE_H_USER_ACK=1` + GUI login | 24h |
| 3 | Step 2 + 24h | plan ralplan | phrase + `V3K_CUTOVER_USER_ACK=1` | 7-day |
| 4 | Step 3 + 7-day | plan ralplan | phrase + `V3K_PHASE_F_USER_ACK=1` | 24h |
| 5 | Step 4 + 24h | plan ralplan | phrase + `V3K_PHASE_G_USER_ACK=1` | 48h |
| 6 | Step 5 + 48h | plan ralplan | final mission phrase | 0 |

총 최소 monitoring 경과 시간: 24h + 7-day + 24h + 48h ≈ 11일 (이상적 fast-path). 실제로는 Step 사이 검증/ralplan/rollback 가능성으로 인해 더 길어질 수 있다.

## §H 운영자 수동 개입 항목 (요약)

1. Kiwoom OpenAPI+ ActiveX login GUI 클릭 (Step 2)
2. 4건의 USER_ACK env var 발급 (Step 2~5)
3. 4건의 사용자 명시 approval phrase 입력 (Step 2~5)
4. F1 cutover transaction lock window 선정 (Step 3)
5. 각 Step 의 24h / 7-day / 48h monitoring 결과 수집
6. regression 감지 시 rollback 의사결정 (Step 3~5)
7. F7 closure 시 final mission completion phrase 입력 (Step 6)

본 7건 모두 본 자동 세션 scope 외에 있으며, 별도 세션에서 사용자 직접 trigger 후 진행한다.

## §I 본 plan freeze 정책

- 본 plan 은 status 보고서이며 Step 2~6 실제 plan 의 대체물이 아니다.
- 각 Step 의 실제 execution plan 은 본 plan 의 §B.2 / §C.2 / §D.2 / §E.2 / §F.2 의 trigger 조건 충족 시 별도 plan 으로 정본화한다.
- 본 plan 은 v4 mid-checkpoint `9423735e` 시점 진척률 50.0% 의 직후 보충 status freeze 이며, 다음 v5 mid-checkpoint 가 정본화될 때까지 운영 기준선으로 사용한다.

## §J Scope guard

본 plan 자체는 단순 docs 추가이며 runtime 변경 0건. 본 plan 작성에 따른 변경:

- Kiwoom runtime mutation 0건 (trade / utility / Kiwoom_OpenAPI)
- LS Securities direct dependency 0건
- operating `_database/` write 0건
- live connect / order / exit 경로 wiring 0건
- USER_ACK env var 발급 0건
- DB / log / shadow / sidecar artifact 미커밋

본 plan 은 docs 1건 + registry 1줄 추가만 포함하며, 사용자 GUI 개입 또는 시간 경과를 요구하는 단계는 일체 trigger 하지 않는다.
