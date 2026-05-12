# V3K Page 037 — Phase G G-1 engine staging 완료 기록

| 항목 | 값 |
| --- | --- |
| 작성/갱신일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 036 / Phase G G-1 pre-ralplan |
| 현재 page | Page 037 / Phase G G-1 engine staging |
| 다음 page | Page 038 / Phase G G-2 parity benchmark plan |
| 목적 | V3 microstructure engine inventory·Kiwoom mapping·default-OFF engine staging |
| 결과 | `completed-default-off-staging` |
| 구현 범위 | T01~T05 완료. G-2 parity/benchmark와 G-3 ON 제외 |

---

## 1. 수행 결과

| Task | 산출물 | 결과 |
| --- | --- | --- |
| T01 V3 engine inventory | `docs/plans/v3k_phase_g_inventory.md` | 완료 |
| T02 Kiwoom mapping | `docs/update_log/2026-05-13_v3k_kiwoom_opt_data_shape_mapping.md` | 완료 |
| T03 engine staging | `strategy/v3k_microstructure_engine.py` | default-OFF/caller-owned data 전용으로 완료 |
| T04 excise audit | `scripts/audit_v3k_phase_g_ls_excise.py` | PASS |
| T05 unit smoke | `scripts/smoke_v3k_phase_g_engine_unit.py` | PASS |

---

## 2. 명시적으로 하지 않은 일

- G-2 parity/benchmark 구현은 하지 않았다.
- G-3 ON 전환은 하지 않았다.
- `V3K-PHASE-G-ENABLE` registry를 만들지 않았다.
- `V3K_PHASE_G_USER_ACK=1`을 사용하지 않았다.
- Kiwoom 주문/청산/live runtime을 변경하지 않았다.
- live order/exit rule에 연결하지 않았다.
- 운영 `_database/` 또는 DB 파일을 변경하지 않았다.

---

## 3. 완료 판정

```text
phase-g-g1-engine-staging = completed-default-off-staging
next candidate = phase-g-g2-parity-benchmark-plan
strategy/v3k_microstructure_engine.py = default-OFF, caller-owned data only
Phase G ON = not performed
Kiwoom live runtime change = none
operating database write = none
```

---

## 4. 다음 OMX 명령

```powershell
omx ralph "force: V3K Page038 Phase G G-2 parity/benchmark plan을 1단계만 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. Page037 산출물(docs/plans/v3k_phase_g_inventory.md, docs/update_log/2026-05-13_v3k_kiwoom_opt_data_shape_mapping.md, strategy/v3k_microstructure_engine.py, scripts/audit_v3k_phase_g_ls_excise.py, scripts/smoke_v3k_phase_g_engine_unit.py)을 먼저 읽고, G-2 parity ±15% 및 성능 ±20% 검증을 위한 scripts/backtest_v3k_phase_g_parity.py, scripts/benchmark_v3k_phase_g_engine.py 설계/구현 범위를 문서화한다. 이 단계에서도 Phase G ON, V3K-PHASE-G-ENABLE, Kiwoom live runtime, 운영 _database write, DB 파일 commit, live order/exit rule 연결은 금지한다. 완료 시 py_compile, Phase G G-1 audit/smoke, runtime activation gap, VERIFY-1A/1B, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 한국어 Lore commit한다."
```
