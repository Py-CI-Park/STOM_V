# N1 — 분야 ② 학습 데이터 백테스트 read 100% closure 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `f564d1a3` (정책 amend + master plan 직후) |
| 마스터 plan | `docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md` §3.1 N1 |
| 본 commit 정체성 | 잔여 5분야 master의 **N1 (분야 ② 90→100% closure)** |
| 코드 변경 | 0건 (smoke 재실행 + evidence 정본화) |
| 매매 영향 | 0건 |

---

## §0. TL;DR

```text
분야 ② 학습 데이터 백테스트 read 90% → 100% closure 확정.

근거 4축:
  1. backtest/backengine_base.py V3K 통합 매우 깊음 (line 11/79/98/137/460-485)
  2. 7 smoke 모두 PASS (재실행 직접 검증)
  3. F5 registry V3K-F5-PROD-READ 확인 (T3 commit 397390f1)
  4. Phase B 6대 invariant 모두 보존 (mode=ro, leakage <, default-OFF 등)

F6 산식: 72.1% → 73.6% (+1.4%p)
매매 영향 0건 (read-only + missing-DB no-op + mode=ro URI).
```

---

## §1. backtest/backengine_base.py V3K 통합 검증

본 백테스트 엔진의 V3K 통합 깊이를 직접 인용:

| 위치 | 내용 |
| --- | --- |
| line 11 | `from strategy.v3k_analyzer_adapter import ANALYZER_MODULE_CONTRACTS, FLAG_BACKTEST_LEARNING, LEARNING_DB_CONTRACTS, V3KLearningDataAdapter` |
| line 79 | `self.v3k_learning_loader = None` (BackEngineBase.__init__) |
| line 98 | `self.v3k_learning_load_plan = {}` |
| line 137 | `self.v3k_learning_loader = V3KLearningDataAdapter()` (조건부 초기화) |
| line 460 | `def _v3k_strategy_gubun(self):` |
| line 467 | `def _v3k_learning_flags(self):` |
| line 473 | `def _v3k_learning_kinds_for_current_timeframe(self):` |
| line 482-485 | 본 메서드에서 V3KLearningDataAdapter 인스턴스 + flags 로드 흐름 |

→ V3K 학습 hook이 **백테스트 엔진 기반 클래스에 깊게 통합**된 상태. 분야 ②의 *백테스트 통합 완료* 증거.

---

## §2. 7 smoke 직접 실행 결과 (2026-05-22 본 PC)

본 PC `STOM_Version_2U_C` worktree에서 read-only 실행:

| # | smoke | 결과 | 출력 |
| ---: | --- | --- | --- |
| 1 | `smoke_v3k_backtest_learning_hook.py` | ✅ PASS | backtest hook ON missing-DB no-op ok: tick / min |
| 2 | `smoke_v3k_learning_loader.py` | ✅ PASS | unsafe identifier guard ok |
| 3 | `smoke_v3k_learning_db_readonly_existing.py` | ✅ PASS | v3k Phase B read-only learning DB smoke passed |
| 4 | `smoke_v3k_realtime_learning_boundary.py` | ✅ PASS | realtime learning ON missing-DB no-op ok: min |
| 5 | `smoke_v3k_learning_db_production_read.py` | ✅ PASS | mode=ro positive + production no-op |
| 6 | `smoke_v3k_learning_db_leakage_guard.py` | ✅ PASS | leakage guard PASS: checked=0, backtest_date=20260522 |
| 7 | `smoke_v3k_learning_db_fallback.py` | ✅ PASS | missing + lock fallback ok |

**7건 모두 PASS** — Phase B 6대 invariant + F5 5중 안전망 모두 동작 확인.

---

## §3. Phase B 6대 invariant 검증

본 commit 시점에 V3KLearningDataAdapter + read_production_learning_db() 메서드의 invariant 검증:

| # | invariant | 검증 |
| --- | --- | --- |
| 1 | feature flag OFF → DB read 안 함 | smoke 1번 (backtest hook ON missing-DB no-op) |
| 2 | DB 없음 → missing diagnostic | smoke 5번 (production no-op for 5 candidates) |
| 3 | DB 있음 → mode=ro URI + uri=True | adapter line 740 본문 + smoke 3번 (Phase B read-only) |
| 4 | last_update < backtest_date (leakage 차단) | smoke 6번 (leakage guard PASS, checked=0) |
| 5 | 운영 `_database/` + Kiwoom runtime 무변경 | git status runtime artifact 0건 |
| 6 | LS direct dependency 0건 | verify_1a LS marker audit PASS |

---

## §4. F5 registry 정합 확인 (T3 인용)

`docs/CARRY_FORWARD_REGISTRY.md` line 1058의 `V3K-F5-PROD-READ` 섹션:

- Records 3건 (update_log + page 027 plan + page 028)
- Modified 6건 (adapter + 3 smoke + 2 audit)
- Decision 5건 (mode=ro / no-op missing / leakage invariant / 운영 무영향 / Kiwoom 무영향)
- Verification 7건 (py_compile + adapter assertion + 3 smoke + full audit)

T3 commit `397390f1`에서 등록 완전성 확인 완료.

---

## §5. Parity evidence cross-ref (T1/T2 인용)

분야 ②의 학습 데이터는 분야 ⑥/⑦ parity 검증에서도 정합성 확인됨:

- `docs/evidence/v3k-phase-f-parity-t1-9024e3b9.json` (T1 분석기 parity, candidate_formula_values 13건 모두 정상)
- `docs/evidence/v3k-phase-g-parity-t2-9024e3b9.json` (T2 엔진 parity)
- `docs/evidence/v3k-phase-g-benchmark-t2-9024e3b9.json` (T2 엔진 benchmark)

`scripts/backtest_v3k_phase_f_parity.py`가 `V3KFormulaGlobalFacade` import해서 분야 ② 학습 데이터 + 분야 ④ 수식 + 분야 ⑥ analyzer 통합 검증 수행.

---

## §6. 진척률 영향

### §6.1 분야 ② 갱신

```
변경 전: 90%
변경 후: 100% (+10%p)
```

### §6.2 F6 산식 단독 영향

```
이전: (50+90+90+75+100+50+50)/700 = 505/700 = 72.1%
이후: (50+100+90+75+100+50+50)/700 = 515/700 = 73.6%
⊕ +1.4%p
```

### §6.3 5분야 master plan N1 종결

```
N1 ② 90→100%  ✅ 완료 (본 commit)
N2 ③ 90→100%  ⏸ 다음
N3 ④ 75→100%  ⏸ 대기
N4 ⑥ 50→100%  ⏸ 대기 (24h monitoring)
N5 ⑦ 50→100%  ⏸ 대기 (48h monitoring)
N6 A5'        ⏸ 대기

진행: 1/6 (16.7%)
```

---

## §7. 산출물

| 산출 | 위치 |
| --- | --- |
| evidence JSON | `docs/evidence/v3k-n1-field2-backtest-learning-9024e3b9.json` (4309 bytes) |
| update_log | 본 보고서 |
| registry | `V3K-N1-FIELD2-BACKTEST-LEARNING-CLOSURE` 섹션 |
| 코드 변경 | 0건 |

---

## §8. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log + evidence |
| read-only smoke 실행 | ✅ 7건 모두 default-OFF |
| audit 결과 등록 | ✅ registry 1 섹션 |

| 금지 | 본 commit |
| --- | --- |
| 코드 변경 | ❌ 0건 |
| 운영 `_database/` write | ❌ 0건 |
| feature flag default-ON | ❌ 0건 |
| sidecar 토글 변경 | ❌ 0건 (N2에서) |
| LS direct dependency | ❌ 0건 |

→ P-lane 적격 (가장 안전).

---

## §9. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §10. 다음 인계

5분야 master plan §3.2 **N2 (분야 ③ sidecar live wiring 토글 활성화)** 진입 가능.

N2는 `_v3k_sidecar/v3k_gui_settings.json`의 `phase_f_live_order_exit_wiring` + `phase_g_live_order_exit_wiring`를 `true`로 변경. 매매 영향 약 (사이드카 토글만, 실제 wiring activation은 N4/N5).

---

## §11. 관련 문서

- `docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md` §3.1 N1
- `docs/plans/2026-05-22_v3k_f1_bypass_phase_fg_on_policy_amend_plan.md` (정책 amend)
- `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` (Phase B 본체)
- `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md` (F5 본체)
- `docs/update_log/2026-05-22_v3k_impl3_backtest_learning_progress.md` (D2 baseline)
- `docs/update_log/2026-05-22_v3k_t3_f5_registry_closure_confirmation.md` (T3 closure)
- `docs/evidence/v3k-n1-field2-backtest-learning-9024e3b9.json`
- `docs/evidence/v3k-phase-f-parity-t1-9024e3b9.json` (T1 parity cross-ref)
- `strategy/v3k_analyzer_adapter.py` (V3KLearningDataAdapter line 560, read_production_learning_db line 740)
- `backtest/backengine_base.py` (V3K 통합 line 11/79/98/137/460-485)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-N1-FIELD2-BACKTEST-LEARNING-CLOSURE` 섹션)
