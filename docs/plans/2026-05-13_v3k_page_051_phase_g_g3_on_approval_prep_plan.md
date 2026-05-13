# V3K Page 051 - Phase G G-3 ON approval prep 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 050 / Phase F F-4 ON approval prep |
| 현재 page | Page 051 / Phase G G-3 ON approval prep |
| 상태 | `completed-approval-prep` |
| 다음 후보 | `phase-g-g3-on-await-user-approval` |
| 목적 | Phase G microstructure engine ON 전에 필요한 사용자 승인, USER_ACK, enable registry, rollback, monitoring, parity/benchmark checklist를 문서와 감사 도구에 고정한다. |
| 위험도 | approval prep은 낮음, actual ON은 critical |
| 실제 ON 여부 | 아님. approval prep 문서화만 수행한다. |

---

## 1. 목표 재확인

V3K의 목표는 **LS Securities 직접 의존성을 제외하고 Kiwoom API/주문/청산/live runtime을 유지한 채 V3의 학습/분석/DB/backtest/realtime 기능을 `STOM_Version_2U_C`에 이행**하는 것이다.

Phase G는 V3 microstructure 기능을 2U_C에 이식하는 영역이다. Page039에서 synthetic parity/benchmark proof가 통과했고 Page040에서 G-3 ON이 사용자 승인 전 blocked 상태임을 문서화했다. Page051은 이 blocked 상태를 실제 승인 준비 packet으로 정리하되, ON 실행은 하지 않는다.

---

## 2. 현재 Phase G 준비 상태

| 증거 | 역할 | 현재 상태 |
| --- | --- | --- |
| `strategy/v3k_microstructure_engine.py` | V3K microstructure engine default-OFF staging | staged |
| `scripts/smoke_v3k_phase_g_engine_unit.py` | default-OFF/unit behavior smoke | PASS 대상 |
| `scripts/backtest_v3k_phase_g_parity.py` | synthetic/caller-owned parity proof | PASS 대상 |
| `scripts/benchmark_v3k_phase_g_engine.py` | synthetic benchmark proof | PASS 대상 |
| `scripts/audit_v3k_phase_g_ls_excise.py` | LS/broker runtime dependency marker 금지 | PASS 대상 |
| `scripts/summarize_v3k_phase_g_evidence.py` | `.omx/reports` raw artifact는 local ignored, commit은 hash/summary만 허용 | PASS 대상 |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | Page051 처리 |
| --- | --- | --- |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A, runtime activation gap | actual runtime 미변경 |
| LS Securities 직접 의존 금지 | Phase G LS excise audit, VERIFY-1A | Phase G ON prep에도 LS broker 의존성 금지 |
| Phase G default-OFF 유지 | unit smoke, DEFAULT_FLAGS audit | actual ON 없이 유지 |
| G-2 parity proof 유지 | `backtest_v3k_phase_g_parity.py` | actual ON 전 필수 검증으로 명시 |
| G-2 benchmark proof 유지 | `benchmark_v3k_phase_g_engine.py` | actual ON 전 필수 검증으로 명시 |
| USER_ACK 없는 ON 금지 | Page051 docs + VERIFY-1B guard | `V3K_PHASE_G_USER_ACK=1` 필요 조건 명시 |
| enable registry 없는 ON 금지 | Page051 docs + runtime gap guard | `V3K-PHASE-G-ENABLE` 필요 조건 명시 |
| rollback/kill switch 없는 ON 금지 | Page051 docs | `V3K_PHASE_G_DISABLE=1` 또는 동등 rollback 조건 명시 |
| live order/exit rule 연결 금지 | VERIFY-1A guarded runtime files | actual live decision path 미연결 |
| 운영 DB write 금지 | audit suite artifact guard | `_database/`, DB 파일, `.omx/reports` raw artifact commit 금지 |

---

## 4. Actual G-3 ON 전 필수 승인 조건

1. 사용자가 `Phase G G-3 ON` gate를 명시적으로 승인한다.
2. `V3K_PHASE_G_USER_ACK=1` 또는 동등한 승인 기록이 생성된다.
3. `V3K-PHASE-G-ENABLE` registry 또는 동등한 enable record가 생성되고 commit된다.
4. `V3K_PHASE_G_DISABLE=1` 또는 동등한 rollback/kill switch path가 실제로 검증된다.
5. 24h monitoring 범위, error budget, fallback trigger가 승인된다.
6. Phase G output이 live order/exit rule consumption에 닿는 경우 별도 critical gate로 분리한다.
7. 아래 검증이 모두 PASS한다.

```powershell
python scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/backtest_v3k_phase_g_parity.py
python scripts/benchmark_v3k_phase_g_engine.py
python scripts/audit_v3k_phase_g_ls_excise.py
python scripts/summarize_v3k_phase_g_evidence.py --format json
python scripts/run_v3k_audit_suite.py
```

---

## 5. STOP condition

다음 중 하나라도 충족되지 않으면 Phase G G-3 ON을 수행하지 않는다.

- 사용자 명시 gate 승인 부재
- `V3K_PHASE_G_USER_ACK=1` 또는 동등 승인 기록 부재
- `V3K-PHASE-G-ENABLE` registry 부재
- rollback/kill switch/monitoring 계획 부재
- Phase G parity/benchmark/LS excise/default-OFF 검증 실패
- Kiwoom live runtime, 주문/청산, live order/exit rule에 닿는 변경 발생
- LS Securities 직접 의존 발생
- 운영 `_database/`, DB 파일, `.omx/reports` raw artifact commit 위험 발생

---

## 6. 다음 단계

현재 Page051의 결론은 `phase-g-g3-on-await-user-approval`이다. 다음 실제 실행은 사용자 승인 전에는 수행하지 않는다. 승인 전 안전 작업으로는 H-2/H-3 Kiwoom live dryrun approval prep 또는 F1 actual DB cutover approval prep 재정리만 허용한다.
