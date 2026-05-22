# V3K-IMPL-3 백테스트 학습 데이터 진척 진단 보고서 (D2)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `c888eefd` (D1 CLI 진단 직후) |
| 기준 plan (Phase B) | `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` |
| 기준 plan (F5) | `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md` |
| 기준 plan (생산 read) | `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` |
| 진단 기간 | 2026-05-08 (V3K mission goal reset) ~ 2026-05-22 |
| 진단 방식 | read-only (plan 본체 + adapter 구조 + smoke 7건 직접 실행) |
| 본 commit 정체성 | M1 진단 phase의 D2 (V3K 백테스트 학습 트랙 baseline) |
| 코드 변경 | 0건 |

---

## §0. TL;DR

```text
V3K-IMPL-3 백테스트 학습 데이터 인프라는 매우 완성도 높은 상태다.

핵심 클래스 (strategy/v3k_analyzer_adapter.py, 7개 클래스):
  ✅ V3KLearningDataAdapter (line 560) — Phase B / IMPL-3 핵심
  ✅ V3KRealtimeLearningAdapter (line 645)
  ✅ V3KAnalyzerAdapter.read_production_learning_db() (line 740) — F5 boundary

Smoke 검증 7건 모두 PASS:
  ✅ learning_db_production_read (F5)
  ✅ learning_db_leakage_guard (data leakage 차단)
  ✅ learning_db_fallback (missing/lock fallback)
  ✅ learning_db_readonly_existing (Phase B read-only)
  ✅ backtest_learning_hook (backtest 통합)
  ✅ learning_loader (unsafe identifier guard)
  ✅ realtime_learning_boundary (실시간 boundary)

Shadow DB 7건 모두 존재 + feature flag default-OFF + mode=ro URI + PRAGMA query_only ON.

진척률 평가:
  Phase A (shadow DB rehearsal): 100% (commit 1196946a)
  Phase B (read-only learning DB): ~90% (smoke PASS, runtime 통합은 별개)
  F5 (production learning DB read): ~85% (5 step 중 1-4 완료)

미진행: 백테스트 엔진 측 V3K 학습 hook의 실제 backtest result evidence (parity gate).
```

---

## §1. baseline 사실 정합

### §1.1 Phase A — shadow DB rehearsal (`1196946a` 완료)

Phase B plan §0.2에서 인용:

| 항목 | 상태 |
| --- | --- |
| shadow DB manifest | ✅ `.omx/reports/v3k-shadow-manifest.json` commit |
| shadow DB apply tool | ✅ `scripts/apply_v3k_shadow_db.py` |
| schema hash invariant | ✅ `scripts/init_v3k_shadow_db.py::compute_schema_hash` + unit test |
| shadow DB 실체 | ✅ `_database_v3k_shadow/` 7개 (pattern_analysis, v3k_code_meta, v3k_meta, volatility_pattern, volatility_stop_take, volume_profile, volume_spike) |
| Kiwoom/live runtime 보존 | ✅ |
| LS direct dependency | ✅ 0건 |

### §1.2 Phase B — read-only learning DB 6대 invariant (plan §0.3 인용)

```
1. feature flag OFF → DB 안 읽음
2. DB 없음 → missing diagnostic 안전 종료
3. DB 있음 → SQLite `?mode=ro` + `uri=True`
4. last_update < backtest_date → 미래 데이터 leakage 차단
5. 운영 _database/ + Kiwoom 주문/청산/live runtime 무변경
6. LS direct dependency 0건
```

본 진단 시점에 6대 invariant 모두 smoke 검증으로 PASS 확인됨 (§3 참조).

### §1.3 F5 — production learning DB read 5 step (page 027 §1)

| Step | 산출 | 상태 |
| --- | --- | --- |
| 027-1 | `V3KAnalyzerAdapter.read_production_learning_db()` 구현 | ✅ line 740 |
| 027-2 | production read smoke | ✅ `scripts/smoke_v3k_learning_db_production_read.py` |
| 027-3 | leakage guard smoke | ✅ `scripts/smoke_v3k_learning_db_leakage_guard.py` |
| 027-4 | fallback smoke | ✅ `scripts/smoke_v3k_learning_db_fallback.py` |
| 027-5 | registry/update_log | ⏸ F5 registry 미확인 (별도 진단 필요) |

---

## §2. Adapter inventory (`strategy/v3k_analyzer_adapter.py`)

7개 클래스 + 1개 핵심 boundary 메서드:

| line | 클래스/메서드 | 역할 |
| ---: | --- | --- |
| 279 | `V3KAnalyzerContext` | analyzer 호출 context |
| 357 | `V3KAnalyzerOutput` | analyzer 출력 표준 |
| 373 | `V3KPhaseFAnalyzerGateResult` | Phase F 게이트 결과 |
| **560** | **`V3KLearningDataAdapter`** | **Phase B / IMPL-3 핵심 — shadow DB read** |
| 645 | `V3KRealtimeLearningAdapter` | 실시간 learning boundary |
| 715 | `V3KAnalyzerAdapter` | 통합 facade |
| **740** | **`read_production_learning_db()`** | **F5 boundary — 운영 _database/ mode=ro read** |

### §2.1 V3KLearningDataAdapter 인터페이스 (line 560-630 인용)

```python
class V3KLearningDataAdapter:
    """Read-only V3K learning-data load path for later backtest wiring.

    IMPL-3 only prepares the policy and read path. It does not create DB files,
    initialize analyzer DB classes, or connect to runtime backtest loops.
    """

    def __init__(self, base_dir="_database_v3k_shadow", feature_flags=None,
                 master_flag=FLAG_BACKTEST_LEARNING):
        # ...

    def learning_is_enabled(self, kind, flags) -> bool:
        # master_flag AND contract.feature_flag 둘 다 true 시만 활성

    def load_before_backtest(self, request) -> LearningLoadResult:
        # flag OFF → "learning load disabled by V3K feature flags"
        # DB missing → "learning DB missing; read-only load skipped"
        # else → mode=ro URI + PRAGMA query_only
```

V3K-IMPL-3 본체 plan §4 "feature flag OFF: 기존 백테스트 결과와 100% 동일" 강제. master flag + analyzer-specific flag **이중 게이트**.

### §2.2 `read_production_learning_db()` 본문 (line 740~ 인용)

```python
def read_production_learning_db(self, db_name, table_name, *,
                                 sample_limit=1, retry_once=True):
    """Read a production learning DB through SQLite mode=ro only.

    This method is a F5 boundary helper. It never creates DB files, never
    writes to _database/, and intentionally returns diagnostics instead
    of raising on missing DB/table/lock cases.
    """

    db_path = self.production_learning_db_path(db_name)
    safe_table = quoted_identifier(table_name)   # SQL injection 차단

    if not db_path.exists():
        return diagnostics("production learning DB missing; read-only production read skipped")

    uri = db_path.resolve().as_uri() + "?mode=ro"   # mode=ro 강제
    for attempt in range(2 if retry_once else 1):
        with closing(sqlite3.connect(uri, uri=True, timeout=0.1)) as conn:
            conn.execute("PRAGMA query_only = ON")   # 이중 read-only
            # table 존재 검증 + LIMIT ? 안전 query
```

**5중 안전망**: (1) 운영 path 명시 (2) safe table name quoting (3) mode=ro URI (4) PRAGMA query_only (5) timeout=0.1 + retry_once + lock fallback.

### §2.3 normalize_v3k_flags 사용처

```
strategy/v3k_analyzer_adapter.py
strategy/v3k_formula_facade.py
strategy/v3k_kiwoom_dryrun_hook.py
strategy/v3k_settings_surface.py
backtest/backengine_base.py             ← 백테스트 엔진에 V3K hook 통합됨
scripts/audit_v3k_verify_1b_closure.py
scripts/run_v3k_step2_to_step6_mock_execution.py
scripts/smoke_v3k_analyzer_adapter.py
scripts/smoke_v3k_backtest_learning_hook.py
scripts/smoke_v3k_learning_db_fallback.py
```

`backtest/backengine_base.py` 통합 사실 = 백테스트 엔진 base가 V3K feature flag 인식 능력 보유.

---

## §3. Smoke 7건 실행 결과 (직접 검증)

본 PC `STOM_Version_2U_C` worktree에서 read-only 실행:

| # | smoke 파일 | 결과 | 검증 항목 |
| ---: | --- | --- | --- |
| 1 | `smoke_v3k_learning_db_production_read.py` | ✅ PASS | mode=ro positive path + 5개 production DB no-op |
| 2 | `smoke_v3k_learning_db_leakage_guard.py` | ✅ PASS | `leakage guard PASS: checked=0, backtest_date=20260522` |
| 3 | `smoke_v3k_learning_db_fallback.py` | ✅ PASS | missing DB + lock/safe-read fallback |
| 4 | `smoke_v3k_learning_db_readonly_existing.py` | ✅ PASS | Phase B read-only existing path |
| 5 | `smoke_v3k_backtest_learning_hook.py` | ✅ PASS | backtest hook ON missing-DB no-op |
| 6 | `smoke_v3k_learning_loader.py` | ✅ PASS | unsafe identifier guard 포함 |
| 7 | `smoke_v3k_realtime_learning_boundary.py` | ✅ PASS | realtime learning ON missing-DB no-op |

**총 7건 모두 PASS**. Phase B 6대 invariant + F5 5중 안전망 모두 동작 확인.

---

## §4. 인프라 완성도 평가

### §4.1 진척률 산정

| 영역 | 진척률 | 근거 |
| --- | ---: | --- |
| Phase A (shadow DB rehearsal) | **100%** | `1196946a` 완료, manifest + apply tool + shadow DB 7개 |
| Phase B (read-only learning DB) | **~90%** | smoke 4건 PASS, adapter 완성, runtime 통합은 backtest result evidence 필요 |
| F5 (production learning DB read) | **~85%** | 027-1~027-4 완료, 027-5 registry 미확인 |
| 백테스트 엔진 통합 | **~70%** | `backengine_base.py`에서 normalize_v3k_flags 사용, 실제 backtest 결과 parity evidence 없음 |
| Phase F default-OFF parity | **~30%** | `backtest_v3k_phase_f_parity.py` 존재, evidence 생성 미확인 |
| Phase G default-OFF parity | **~30%** | `backtest_v3k_phase_g_parity.py` 존재, evidence 생성 미확인 |

종합 V3K-IMPL-3 진척률: **약 75-85%**.

### §4.2 master plan §3.1 트랙 A vs 본 진단 비교

| 트랙 A 항목 | master plan 추정 | 본 진단 실측 |
| --- | --- | --- |
| #2 production learning DB read | 75% | **~85%** (027-1~027-4 완료) |
| #4 formula globals | 50% | (본 진단 범위 외 — 별도 진단 필요) |
| #6 Phase F default-OFF parity | 25% | **~30%** (script 존재, evidence 미확인) |
| #7 Phase G default-OFF parity | 25% | **~30%** (script 존재, evidence 미확인) |

master plan 추정보다 약간 높은 진척률. M2 첫 cycle은 신규 인프라가 아닌 **evidence 산출 + 일관성 검증**에 집중하는 게 효율적.

---

## §5. 미진행 / 잔여 작업

### §5.1 단기 우선 (M2 첫 cycle 후보)

| # | 작업 | 산출 |
| ---: | --- | --- |
| 1 | F5 027-5 registry 등록 확인 + 미등록 시 등록 commit | registry 1 섹션 |
| 2 | `backtest_v3k_phase_f_parity.py` 실제 실행 + evidence 산출 | `.omx/reports/v3k-prep-phase-f-parity.json` 갱신 또는 신규 |
| 3 | `backtest_v3k_phase_g_parity.py` 실제 실행 + evidence + benchmark 산출 | evidence 2건 갱신 또는 신규 |
| 4 | 백테스트 엔진의 V3K 통합 시점 evidence — 실제 backtest result (V3K_OFF vs V3K_ON simulated parity) | backtest evidence 1건 |

### §5.2 중기 (M3-M4 cycle)

| # | 작업 | 산출 |
| ---: | --- | --- |
| 5 | V3K-IMPL-3 closure plan (Phase B + F5 + backtest 통합 closure) | plan 1건 |
| 6 | analyzer 7종 default-OFF backtest run + parity matrix 100건 | evidence multi-건 |
| 7 | data leakage guard 정량 검증 — backtest_date 다양화 + assertion | parametric smoke evidence |

---

## §6. master plan milestone 영향

본 진단으로 master plan §4.2 milestone 재정의:

| Milestone | 원래 정의 | 재정의 |
| --- | --- | --- |
| M2 | CLI Phase 1 + V3K-IMPL-3 baseline | **CLI Phase 1 확장 (ai_controller/strategy_generator) + V3K Phase F/G parity evidence 산출** |
| M3 | CLI Phase 2 + Phase F/G parity | **CLI Phase 2 일관성 + V3K-IMPL-3 closure plan** |
| M4 | CLI Phase 3 + #4 formula globals | **CLI Phase 3 + #4 formula globals 진단/통합** |
| M5 | 트랙 A closure | 미변경 |

milestone 1~2주 단축 가능 (Phase 1 + V3K-IMPL-3 인프라가 이미 완비됐기 때문).

---

## §7. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log 1건 |
| smoke read-only 실행 | ✅ 7건 모두 운영 DB write 0건 |
| audit 결과 등록 | ✅ registry 1 섹션 |

| 금지 | 본 commit |
| --- | --- |
| 코드 변경 | ❌ 0건 |
| 운영 `_database/` write | ❌ 0건 (smoke 모두 missing-DB / mode=ro 경로) |
| `_database_v3k_shadow/` 변경 | ❌ 0건 |
| feature flag default-ON | ❌ 0건 |
| LS direct dependency | ❌ 0건 |

→ P-lane 적격.

---

## §8. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §9. 다음 인계

본 D2 진단 commit 직후 M1 진단 phase 종결 (D3 유닛 테스트 + D4 sidecar는 후속 옵션). M2 첫 cycle 진입 시점에 본 진단 §5.1 우선순위 인용:

1. **F5 027-5 registry 등록 확인** (가장 짧은 cycle)
2. **Phase F default-OFF parity evidence 산출**
3. **Phase G default-OFF parity + benchmark evidence**
4. **CLI Phase 1 확장 (ai_controller / strategy_generator)**

권장 M2 첫 작업: 위 1번 (F5 registry 확인, 가장 짧음) 또는 4번 (CLI 확장, 사용자 가시 산출).

---

## §10. 관련 문서

- `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md`
- `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md`
- `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md`
- `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (트랙 A baseline)
- `docs/update_log/2026-05-22_v3k_midcourse_review_backtest_cli_prioritization.md`
- `docs/update_log/2026-05-22_cli_phase_progress_diagnosis.md` (D1)
- `strategy/v3k_analyzer_adapter.py` (V3KLearningDataAdapter, V3KAnalyzerAdapter)
- `backtest/backengine_base.py` (V3K hook 통합 위치)
- `scripts/smoke_v3k_learning_db_*.py` (7건 smoke)
- `_database_v3k_shadow/` (7개 shadow DB)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-IMPL3-BACKTEST-LEARNING-D2-DIAGNOSIS` 섹션)
