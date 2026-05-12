# V3K Page 037 — Phase G G-1 engine staging 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 036 / Phase G G-1 pre-ralplan |
| 현재 page | Page 037 / Phase G G-1 engine staging |
| 목적 | V3 microstructure engine inventory·Kiwoom mapping·default-OFF engine staging |
| 위험도 | high |
| 구현 범위 | T01~T05 only. G-2 parity/benchmark와 G-3 ON 제외 |

---

## 0. 목적

Page037은 Phase G G-1의 실제 staging 단계다. V3 branch(`C:/System_Trading/STOM/STOM_V.wt-3`)에서 microstructure 관련 모듈을 조사하고, Kiwoom OPT* data shape mapping을 정본화한 뒤, 2U_C에 LS-free/default-OFF/caller-owned-data 전용 engine skeleton을 만든다.

이 단계는 engine ON이 아니다. live 전략 결정, 주문/청산, 운영 DB, GUI runtime은 변경하지 않는다.

---

## 1. 실행 범위 T01~T05

| Task | 산출물 | 완료 조건 |
| --- | --- | --- |
| T01 V3 engine inventory | `docs/plans/v3k_phase_g_inventory.md` | V3 microstructure/analyzer 후보 파일, LOC, LS marker, 이식 판정 표 |
| T02 Kiwoom mapping | `docs/update_log/2026-05-13_v3k_kiwoom_opt_data_shape_mapping.md` | V3 field ↔ Kiwoom OPT* field mapping과 fallback 결정 |
| T03 engine staging | `strategy/v3k_microstructure_engine.py` | LS-free, default-OFF, caller-owned data only, no runtime hook |
| T04 LS excise audit | `scripts/audit_v3k_phase_g_ls_excise.py` | LS marker 0건 자동검증 |
| T05 unit smoke | `scripts/smoke_v3k_phase_g_engine_unit.py` | synthetic Kiwoom fixture로 engine unit smoke PASS |

---

## 2. 금지 사항

- G-2 parity/benchmark 구현
- G-3 ON 전환
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- Kiwoom 주문/청산/live runtime 변경
- live order/exit rule 연결
- 운영 `_database/` write
- DB 파일 commit
- LS Securities REST/TR/REAL 직접 의존 추가

---

## 3. 검증 명령

Page037 완료 전 최소 검증:

```powershell
python -m py_compile strategy/v3k_microstructure_engine.py scripts/audit_v3k_phase_g_ls_excise.py scripts/smoke_v3k_phase_g_engine_unit.py scripts/audit_v3k_runtime_activation_gap.py scripts/audit_v3k_verify_1b_closure.py
python scripts/audit_v3k_phase_g_ls_excise.py
python scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph v3k_settings*.json _database.backup.TEST
```

---

## 4. 성공 후 다음 후보

Page037 성공 후 다음 후보는 Page038 / `phase-g-g2-parity-benchmark-plan`이다. 단, G-2에서도 ON은 하지 않고 parity ±15%, 성능 ±20% 검증과 report archive만 수행한다.

---

## 5. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page037 Phase G G-1 engine staging을 1단계만 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-13_v3k_page_036_phase_g_g1_pre_ralplan_plan.md, docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md, docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T01–T05, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. V3 branch(STOM_V.wt-3)에서 microstructure 관련 모듈 inventory를 작성하고, Kiwoom OPT* data shape mapping 표를 정본화한 뒤, default-OFF/caller-owned-data 전용 strategy/v3k_microstructure_engine.py, scripts/audit_v3k_phase_g_ls_excise.py, scripts/smoke_v3k_phase_g_engine_unit.py를 신설한다. LS Securities REST/TR/REAL 직접 의존은 audit으로 0건이어야 하며, Kiwoom 주문/청산/live runtime, 운영 _database/, DB 파일, live order/exit rule, Phase G ON 전환은 변경하지 않는다. 완료 시 py_compile, audit_v3k_phase_g_ls_excise, smoke_v3k_phase_g_engine_unit, audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, scripts/verify_nonrelease_sync.py, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
