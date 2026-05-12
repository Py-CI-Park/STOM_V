# V3K Phase G G-2 parity/benchmark 계획 기록

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 038 |
| phase | Phase G / G-2 parity·benchmark plan |
| source | Page037 default-OFF microstructure engine staging |
| 결과 | `completed-plan` |
| next candidate | `phase-g-g2-parity-benchmark-work` |

---

## 1. 배경

Phase G는 V3 microstructure 기능을 2U_C에 이식하되, LS Securities 의존을 제외하고 Kiwoom API/runtime을 유지하는 V3K 작업이다. Page037에서는 broker-neutral, caller-owned, default-OFF engine skeleton을 staging했다. 하지만 G-1 smoke만으로는 V3 기능 parity와 runtime 성능을 주장할 수 없기 때문에 G-2 검증 page가 필요하다.

Page038의 목적은 실제 script 구현 전에 아래를 고정하는 것이다.

- parity 한계: ±15%
- benchmark 한계: ±20%
- output contract: `미시구조신호`, `미시구조신뢰도`, `미시구조리스크`, `호가불균형`, `가중호가비율`
- evidence 위치: ignored `.omx/reports/*latest.json`
- 금지 범위: Phase G ON, live runtime 연결, 운영 DB 접근, LS 직접 의존

---

## 2. 결정

Page038은 plan-only로 완료한다. 즉, `scripts/backtest_v3k_phase_g_parity.py`와 `scripts/benchmark_v3k_phase_g_engine.py`는 Page039에서 구현한다.

이 결정을 내린 이유는 다음과 같다.

1. Page037 산출물은 engine staging이지 parity/benchmark 실행 설계까지 포함하지 않는다.
2. Page039 구현 전에 audit script가 “다음 후보가 실제 G-2 work”임을 명확히 표시해야 한다.
3. G-2 proof와 G-3 ON approval gate가 섞이면 feature flag default-OFF invariant가 흐려진다.
4. 사용자 승인 없이 ON registry나 runtime hook을 생성하지 않기 위해 planning boundary가 필요하다.

---

## 3. 수행 내용

- `docs/plans/2026-05-13_v3k_page_038_phase_g_g2_parity_benchmark_plan.md`를 UTF-8 한글 문서로 재작성하고 Page038 완료 기록을 추가했다.
- `docs/plans/2026-05-13_v3k_page_039_phase_g_g2_parity_benchmark_work_plan.md`를 생성했다.
- `docs/CARRY_FORWARD_REGISTRY.md`에 Page038 decision record를 추가했다.
- `scripts/audit_v3k_runtime_activation_gap.py`에서 next candidate를 `phase-g-g2-parity-benchmark-work`로 이동했다.
- `scripts/audit_v3k_verify_1b_closure.py`에서 Page038 plan과 Page039 work plan을 요구 문서로 추가했다.

---

## 4. 아직 하지 않은 일

아래 항목은 의도적으로 수행하지 않았다.

| 항목 | 이유 | 다음 처리 |
| --- | --- | --- |
| `scripts/backtest_v3k_phase_g_parity.py` 구현 | Page038은 계획 고정 단계 | Page039에서 구현 |
| `scripts/benchmark_v3k_phase_g_engine.py` 구현 | Page038은 계획 고정 단계 | Page039에서 구현 |
| Phase G ON | 사용자 승인과 G-2 proof가 없음 | G-3 approval gate에서만 검토 |
| `V3K-PHASE-G-ENABLE` registry | ON 승인 전 생성 금지 | G-3에서 명시 승인 시만 가능 |
| live strategy/order/exit 연결 | live trading decision 변경 위험 | 별도 승인·monitoring 전 금지 |
| 운영 DB 읽기/쓰기 | G-2는 synthetic/caller-owned fixture만 허용 | DB cutover/production read gate와 분리 |

---

## 5. 검증 방침

Page038 검증은 아래 명령으로 수행한다.

```powershell
python -m py_compile scripts/audit_v3k_runtime_activation_gap.py scripts/audit_v3k_verify_1b_closure.py
python -m py_compile strategy/v3k_analyzer_adapter.py strategy/v3k_microstructure_engine.py scripts/audit_v3k_phase_g_ls_excise.py scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/audit_v3k_phase_g_ls_excise.py
python scripts/smoke_v3k_phase_g_engine_unit.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
python scripts/audit_v3k_db_artifact_status.py
python scripts/audit_v3k_sidecar_artifact_status.py
git diff --check
```

---

## 6. 다음 단계

다음 단계는 Page039 / `phase-g-g2-parity-benchmark-work`이다. Page039는 synthetic/caller-owned fixture 기반으로 두 script를 구현하고 실행한다. Page039가 PASS하더라도 Phase G ON은 여전히 G-3 사용자 승인 gate로 남는다.

Directive: Page039에서 parity/benchmark proof를 만들더라도 `V3K_PHASE_G_MICROSTRUCTURE_ENGINE` 기본값을 ON으로 바꾸거나 live runtime에 연결하지 말 것.
