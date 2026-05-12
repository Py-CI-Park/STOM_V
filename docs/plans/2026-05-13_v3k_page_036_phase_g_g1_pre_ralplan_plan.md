# V3K Page 036 — Phase G G-1 pre-ralplan 완료 기록

| 항목 | 값 |
| --- | --- |
| 작성/갱신일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 035 / Phase F F-4 approval gate |
| 현재 page | Page 036 / Phase G G-1 pre-ralplan |
| 다음 page | Page 037 / Phase G G-1 engine staging |
| 목적 | V3 microstructure engine 이식 전 고위험 합의 재실행 |
| 결과 | `completed-consensus` |
| 구현 범위 | 구현 전 planning/consensus only. `strategy/v3k_microstructure_engine.py`는 아직 만들지 않음 |

---

## 0. 목적

Phase G는 V3 microstructure engine을 2U_C에 이식할 수 있는지 검토하는 고위험 단계다. LS Securities 의존 제거, Kiwoom OPT* data-shape mapping, parity 한계, 성능 한계, ON 승인 분리를 모두 만족해야 하므로 바로 구현하지 않는다.

Page036의 목적은 `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md`의 §C T01~T05를 실행하기 전에 RALPLAN-DR 형식으로 Planner/Architect/Critic 관점의 합의를 고정하는 것이다.

---

## 1. RALPLAN-DR 요약

### 1.1 Principles

1. **Kiwoom runtime 불변**: G-1은 read-only/default-OFF staging이며 Kiwoom 주문·청산·live runtime은 변경하지 않는다.
2. **LG1 LS excise first**: V3 코드 참고는 허용하지만 LS Securities REST/TR/REAL import·endpoint·payload assumption은 자동 audit으로 0건이어야 한다.
3. **LG2 Mapping before engine**: Kiwoom OPT* data shape mapping 표가 engine input contract보다 먼저 정본화되어야 한다.
4. **LG3/LG4 Quant proof before ON**: parity ±15%, 성능 ±20%는 G-2에서 별도 검증하며, G-1 성공만으로 ON을 허용하지 않는다.
5. **LG5 승인 분리**: G-3 ON, `V3K-PHASE-G-ENABLE`, `V3K_PHASE_G_USER_ACK=1`, 24h monitoring은 별도 사용자 승인 cycle에서만 가능하다.

### 1.2 Decision drivers

| 순위 | driver | 의미 |
| --- | --- | --- |
| 1 | V3K 미션 #7 완료 필요 | V3 microstructure engine replacement는 아직 실제 engine 단계가 남아 있다. |
| 2 | Kiwoom 유지 | LS API 전제를 Kiwoom OPT* data shape로 바꿔야 하므로 mapping이 선행되어야 한다. |
| 3 | runtime risk 차단 | G-1은 구현·단위검증까지만 허용하고 live/order/exit/DB 영향은 0이어야 한다. |

### 1.3 Viable options

| option | 내용 | 판정 |
| --- | --- | --- |
| A | V3 microstructure code를 크게 병합한 뒤 LS 의존을 사후 제거 | Reject — LS field assumption과 import가 섞인 상태로 유입될 위험이 높다. |
| B | analyzer adapter만 유지하고 engine 이식은 생략 | Reject — audit §6.2 #7의 “engine replacement” 목표를 충족하지 못한다. |
| C | T01 inventory → T02 mapping → T03 최소 engine staging → T04 LS audit → T05 unit smoke 순서로 default-OFF 구현 | Choose — 각 위험을 문서·audit·unit smoke로 분리할 수 있다. |

---

## 2. Architect review 요지

- V3 branch를 단순 복사하지 않고 inventory와 mapping을 먼저 고정해야 한다.
- `strategy/v3k_microstructure_engine.py`는 caller-owned data structure만 받아야 하며, 운영 DB·live runtime·broker client를 내부에서 열면 안 된다.
- LS excise audit은 단순 문자열 grep만이 아니라 import/module/endpoint/payload marker를 포함해야 한다.
- G-1 산출물은 G-2 parity·benchmark의 입력이므로 output contract를 명확히 유지해야 한다.

---

## 3. Critic review 요지

- `omx ralplan`이 이 환경에서 직접 실행되지 않았더라도 Page036은 ralplan skill 절차에 맞춰 pre-mortem과 expanded test plan을 문서화해야 한다.
- 다음 Page037은 T01~T05를 수행할 수 있지만, G-2 parity/benchmark와 G-3 ON을 섞으면 안 된다.
- `verify_release_sync.py`는 playbook 원문에 남아 있더라도 2U_C에서는 반드시 `scripts/verify_nonrelease_sync.py`로 대체해야 한다.
- completion claim은 “G-1 구현 가능 상태”까지만 허용하고 “Phase G 완료” 또는 “V3K 완료”로 표현하면 안 된다.

---

## 4. Deliberate pre-mortem

| 시나리오 | 실패 형태 | 탐지 | 차단/완화 |
| --- | --- | --- | --- |
| LS 의존 잔존 | `xingapi`, `ls_securities`, REST/TR/REAL field assumption 유입 | `scripts/audit_v3k_phase_g_ls_excise.py` + manual inventory | LS marker 1건이라도 있으면 G-1 실패, mapping 또는 adapter 재작성 |
| Kiwoom data shape mismatch | V3 field와 Kiwoom OPT* field 의미·단위가 달라 indicator가 왜곡 | T02 mapping completeness + unit smoke fixture | missing/ambiguous field는 fallback 또는 제외 사유를 mapping 표에 명시 |
| parity 한계 이탈 | G-2에서 V3 baseline 대비 indicator 결과가 ±15%를 벗어남 | `backtest_v3k_phase_g_parity.py` | ON 차단, G-1 mapping/engine contract 재검토 |

---

## 5. Expanded test plan

| 레벨 | Page037/G-1 계획 | G-2/G-3 이후 계획 |
| --- | --- | --- |
| Unit | `python -m py_compile strategy/v3k_microstructure_engine.py`; synthetic Kiwoom fixture로 engine unit smoke | gate/rollback unit smoke |
| Integration | V3 inventory와 Kiwoom mapping 문서 coverage 검증; LS excise audit | V3 baseline vs 2U_C engine parity script |
| E2E | G-1에서는 금지. live/order/exit/GUI runtime 연결 없음 | 사용자 승인 후 G-3에서만 ON e2e 가능 |
| Observability | update_log, registry, audit output, ignored `.omx/reports` local evidence | parity/benchmark/monitoring report archive |
| Regression | `audit_v3k_verify_1a --base 57496d24`, `audit_v3k_verify_1b_closure`, `verify_nonrelease_sync.py`, `git diff --check` | 동일 + Phase G parity/benchmark/monitoring |

---

## 6. ADR

- **Decision**: Phase G는 Option C, 즉 inventory/mapping-first default-OFF staging으로 진행한다.
- **Drivers**: V3K #7 달성, Kiwoom 유지, LS 제거 자동화, live runtime risk 차단.
- **Alternatives considered**:
  - A: broad transplant 후 사후 LS 제거 — LS assumption 유입 위험으로 기각.
  - B: adapter 유지로 충분하다고 간주 — engine replacement 목표 미달로 기각.
- **Consequences**:
  - 긍정: G-1에서 구현 위험을 작은 단위로 검증할 수 있다.
  - 부정: inventory/mapping 문서가 선행되어 작업량은 늘어난다.
- **Follow-ups**:
  - Page037에서 T01~T05를 하나의 default-OFF staging commit으로 수행한다.
  - G-2에서 parity/benchmark를 별도 commit으로 수행한다.
  - G-3 ON은 사용자 승인과 `V3K_PHASE_G_USER_ACK=1` 없이는 진행하지 않는다.

---

## 7. Page036 완료 판정

```text
phase-g-g1-pre-ralplan = completed-consensus
next candidate = phase-g-g1-engine-staging
strategy/v3k_microstructure_engine.py = not created in Page036
Kiwoom live runtime change = none
LS direct dependency = none
operating database write = none
```

---

## 8. 다음 OMX 명령

다음 단계는 Page037 / Phase G G-1 engine staging이다. 아래 명령은 playbook C4를 2U_C 규칙에 맞게 보정한 것이다.

```powershell
omx ralph "force: V3K Page037 Phase G G-1 engine staging을 1단계만 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-13_v3k_page_036_phase_g_g1_pre_ralplan_plan.md, docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md, docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T01–T05, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. V3 branch(STOM_V.wt-3)에서 microstructure 관련 모듈 inventory를 작성하고, Kiwoom OPT* data shape mapping 표를 정본화한 뒤, default-OFF/caller-owned-data 전용 strategy/v3k_microstructure_engine.py, scripts/audit_v3k_phase_g_ls_excise.py, scripts/smoke_v3k_phase_g_engine_unit.py를 신설한다. LS Securities REST/TR/REAL 직접 의존은 audit으로 0건이어야 하며, Kiwoom 주문/청산/live runtime, 운영 _database/, DB 파일, live order/exit rule, Phase G ON 전환은 변경하지 않는다. 완료 시 py_compile, audit_v3k_phase_g_ls_excise, smoke_v3k_phase_g_engine_unit, audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, scripts/verify_nonrelease_sync.py, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
