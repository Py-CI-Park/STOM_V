# V3K 잔여 5분야(②③④⑥⑦) 100% 완성 master plan

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `66f316f6` (ai-controller promotion 직후) |
| 동반 amend plan | `docs/plans/2026-05-22_v3k_f1_bypass_phase_fg_on_policy_amend_plan.md` |
| 본 plan 정체성 | 분야 ① 제외 + 분야 ②③④⑥⑦ 각 100% 완성까지의 전체 작업 master |
| 목표 F6 진척률 | 72.1% → **92.9%** (분야 ① 50% 유지, 분야 ②~⑧ 모두 100%) |
| 코드 변경 의무 | 분야별 commit으로 분리, 총 6+ commit |
| monitoring 누적 | 24h + 48h ≈ 72h+ |

---

## §0. TL;DR

```text
잔여 5분야 100% 완성 master plan:
  N1. 분야 ② 100% — 백테스트 evidence (안전, ~30분)
  N2. 분야 ③ 100% — sidecar live wiring 활성화 (~30분)
  N3. 분야 ④ 100% — formula runtime hook (~1~2시간)
  N4. 분야 ⑥ 100% — Phase F F-4 ON actual (~2시간 + 24h monitoring)
  N5. 분야 ⑦ 100% — Phase G G-3 ON actual (~2시간 + 48h monitoring)
  N6. A5' 부분 closure — F6 92.9% 선언 (~30분)

총 6 commit + monitoring 누적 72h+
F6 산식: 72.1% → 92.9% (+20.8%p)
```

---

## §1. 잔여 작업 매트릭스

| 단계 | 분야 | 작업 | 시간 | monitoring | 매매 영향 | 진척률 변동 |
| ---: | ---: | --- | --- | --- | --- | ---: |
| N1 | ② 90→100% | 백테스트 엔진 V3K 학습 hook 실제 result evidence + parity matrix | ~30분 | 0 | 0건 | +10%p |
| N2 | ③ 90→100% | `phase_f_live_order_exit_wiring=true` + `phase_g_live_order_exit_wiring=true` 활성화 | ~30분 | 0 (선언만) | 약 (sidecar) | +10%p |
| N3 | ④ 75→100% | `trade/formula_manager.py` runtime hook 통합 + Phase E0 closure | ~1~2시간 | 0 | 고 (VERIFY-1A guard 떨어냄) | +25%p |
| N4 | ⑥ 50→100% | Phase F F-4 ON actual (sidecar 토글 + analyzer 매매 wiring) | ~2시간 | 24h | 고위험 | +50%p |
| N5 | ⑦ 50→100% | Phase G G-3 ON actual (engine 매매 wiring + benchmark) | ~2시간 | 48h | 대형 위험 | +50%p |
| N6 | - | A5' F7 부분 closure 선언 (분야 ① 50% 유지) | ~30분 | 0 | 0건 | - |

---

## §2. 의존성 그래프

```
N1 (② 백테스트 evidence)         ─┐
                                    ├─ 독립, 어느 순서든 OK
N2 (③ sidecar wiring 토글)      ─┤
                                    │
N3 (④ formula runtime hook)     ─┤
                                    │
N4 (⑥ Phase F F-4 ON actual)   ─→ N5 (⑦ Phase G G-3 ON actual)  →  N6 (A5')
   (24h monitoring 필요)             (48h monitoring 필요)
```

핵심 의존성:
- N4 → N5: page 081 plan §Goal "after gate1 and gate2 evidence exists"
- N5 → N6: A4 closure 의존
- N1/N2/N3는 N4 이전 어느 시점이든 진행 가능

권장 순서: **N1 → N2 → N3 → N4 → (24h 대기) → N5 → (48h 대기) → N6**

---

## §3. 단계별 상세 plan

### §3.1 N1 — 분야 ② 백테스트 evidence (가장 안전)

**목표**: 백테스트 엔진의 V3K 학습 hook 실제 result evidence 산출.

| 항목 | 값 |
| --- | --- |
| 실행 script | `scripts/smoke_v3k_backtest_learning_hook.py` (이미 존재) + 추가 evidence 산출 wrapper |
| 산출 위치 | `docs/evidence/v3k-impl3-backtest-learning-hook-result-9024e3b9.json` |
| 검증 기준 | 실제 백테스트 1회 + V3K 학습 hook 통과 evidence (timestamp + checksum) |
| 매매 영향 | 0건 (read-only) |
| 시간 | ~30분 |
| F6 영향 | 분야 ② 90% → 100% (+10%p) |

### §3.2 N2 — 분야 ③ sidecar live wiring 활성화

**목표**: `_v3k_sidecar/v3k_gui_settings.json`의 `phase_f_live_order_exit_wiring`, `phase_g_live_order_exit_wiring`을 `true`로 변경 (사이드카 토글 선언).

⚠️ 다만 *선언*만이고 실제 wiring activation은 N4/N5에서.

| 항목 | 값 |
| --- | --- |
| 변경 파일 | `_v3k_sidecar/v3k_gui_settings.json` (직접 편집) |
| 검증 script | `scripts/audit_v3k_gui_sidecar_write_guard.py` (이미 존재) |
| 매매 영향 | 사이드카 토글만 (실제 wiring은 N4/N5) |
| 시간 | ~30분 |
| F6 영향 | 분야 ③ 90% → 100% (+10%p) |

### §3.3 N3 — 분야 ④ formula runtime hook 통합

**목표**: `trade/formula_manager.py` + `trade/base_strategy.py`에 V3K formula globals runtime hook 통합. VERIFY-1A guard 떨어냄.

| 항목 | 값 |
| --- | --- |
| 변경 파일 | `trade/formula_manager.py`, `trade/base_strategy.py` (LH1 부분 떨어냄) |
| guard 변경 | `scripts/audit_v3k_verify_1a.py`의 trade/ guard amend |
| 본체 plan | `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md` |
| 검증 script | smoke + parity (default-OFF에서 기존 결과 동일) |
| 매매 영향 | 고 (formula globals 매매 결정 경로 노출) |
| 시간 | ~1~2시간 |
| F6 영향 | 분야 ④ 75% → 100% (+25%p) |

### §3.4 N4 — 분야 ⑥ Phase F F-4 ON actual

**목표**: analyzer 7종이 실제 매매 결정 경로에 연결되도록 활성화. page 080 plan §Goal 인용:

```text
Execute only the approved second gate, phase-f-f4-on-await-user-approval, after gate1 evidence exists.
```

| 항목 | 값 |
| --- | --- |
| 본체 plan | `docs/plans/2026-05-14_v3k_page_080_phase_f_gate2_execution_plan.md` |
| 실행 script | `scripts/write_v3k_phase_f_sidecar_enable.py` + audit |
| canonical phrase | `I approve phase-f-f4-on-await-user-approval only` |
| USER_ACK env | `V3K_PHASE_F_USER_ACK=1` |
| monitoring | 24h |
| 매매 영향 | 고위험 (analyzer 매매 결정 영향) |
| 시간 | ~2시간 + 24h monitoring |
| F6 영향 | 분야 ⑥ 50% → 100% (+50%p) |

### §3.5 N5 — 분야 ⑦ Phase G G-3 ON actual

**목표**: microstructure engine이 실제 매매 결정에 연결. page 081 plan §Goal:

```text
Execute only the approved third gate, phase-g-g3-on-await-user-approval,
after gate1 and gate2 evidence exists.
```

| 항목 | 값 |
| --- | --- |
| 본체 plan | `docs/plans/2026-05-14_v3k_page_081_phase_g_gate3_execution_plan.md` |
| 실행 script | `scripts/write_v3k_phase_g_sidecar_enable.py` + audit + benchmark |
| canonical phrase | `I approve phase-g-g3-on-await-user-approval only` |
| USER_ACK env | `V3K_PHASE_G_USER_ACK=1` |
| 사전 조건 | N4 closure + 24h monitoring 통과 |
| monitoring | 48h (parity ±15% + benchmark ±20%) |
| 매매 영향 | 대형 위험 |
| 시간 | ~2시간 + 48h monitoring |
| F6 영향 | 분야 ⑦ 50% → 100% (+50%p) |

### §3.6 N6 — A5' 부분 closure

**목표**: F7 부분 closure 선언. 분야 ① 50% 유지 명시.

| 항목 | 값 |
| --- | --- |
| 본체 plan | `docs/plans/2026-05-14_v3k_page_083_gate5_gate6_review_only_plan.md` (참조) |
| 신규 산출 | `docs/evidence/v3k-a5prime-partial-closure-9024e3b9.json` |
| 산식 | (50 + 100*6) / 700 = 650/700 = **92.9%** |
| F7 closure 조건 | 분야 ② ③ ④ ⑤ ⑥ ⑦ ⑧ 100% (분야 ① 50% 유지) |
| 시간 | ~30분 |

---

## §4. 일정 + monitoring 누적

```
[T+0]      N1 (분야 ② evidence)     ~30분   매매 영향 0
[T+30분]   N2 (sidecar 토글)         ~30분   매매 영향 약
[T+1시간]  N3 (formula runtime hook) ~1.5시간 매매 영향 고
[T+2.5시간] N4 (Phase F F-4 ON)      ~2시간  매매 영향 고
[T+4.5시간] ─ 24h monitoring 시작 ─
[T+28.5시간] N5 (Phase G G-3 ON)     ~2시간  매매 영향 대형
[T+30.5시간] ─ 48h monitoring 시작 ─
[T+78.5시간] N6 (A5' closure)        ~30분
```

총 누적 ≈ **약 3.3일** (작업 시간 + monitoring 누적).

monitoring은 시간 경과만 필요 — 사용자가 다른 작업하며 자연 누적.

---

## §5. F6 산식 갱신 시뮬레이션

```
현재 (66f316f6 시점):  (50+90+90+75+100+50+50)/700 = 505/700 = 72.1%

N1 (② +10%p) 후:        (50+100+90+75+100+50+50)/700 = 515/700 = 73.6%
N2 (③ +10%p) 후:        (50+100+100+75+100+50+50)/700 = 525/700 = 75.0%
N3 (④ +25%p) 후:        (50+100+100+100+100+50+50)/700 = 550/700 = 78.6%
N4 (⑥ +50%p) 후:        (50+100+100+100+100+100+50)/700 = 600/700 = 85.7%
N5 (⑦ +50%p) 후:        (50+100+100+100+100+100+100)/700 = 650/700 = 92.9%
N6 (A5' 선언) 후:       동일 92.9% (선언만)

목표: 92.9% (분야 ① 50% 유지)
100% 만점은 분야 ① F1 cutover 진행 시점에 추후 A5'' closure.
```

---

## §6. 위험 평가 + 완화

| 단계 | 위험 | 완화 |
| --- | --- | --- |
| N1 | 백테스트 evidence 부정확 | smoke 재실행 + 직접 인용 |
| N2 | sidecar 토글 후 실제 wiring 안 됨 | N4/N5에서 wiring 본 작업 |
| N3 | trade/formula_manager.py 변경으로 기존 매매 회귀 | default-OFF parity ±0% smoke 강제 + rollback flag |
| N4 | Phase F F-4 ON 후 analyzer 매매 신호 분포 변동 | parity matrix ±15% 사전 검증 (이미 evidence 산출됨) + rollback (V3K_PHASE_F_DISABLE) |
| N5 | Phase G ON 후 engine 성능 영향 | benchmark ±20% 사전 검증 + rollback (V3K_PHASE_G_DISABLE) |
| 전체 | 운영 _database/ write 발생 | sidecar 토글만 변경, cutover 미실행으로 운영 DB 무영향 |

---

## §7. 보존 invariant

| invariant | 변경 |
| --- | --- |
| L1 database schema unchanged | ✅ 보존 (cutover 미실행) |
| L4 운영 DB write 제한 | ✅ 보존 (sidecar 토글만) |
| L7 LS direct dependency 0건 | ✅ 보존 |
| L9 STOM CLI surface 보존 | ✅ 보존 |
| LH1 Kiwoom 주문/청산 경로 코드 무변경 | ⚠️ N3에서 부분 떨어냄 (trade/formula_manager.py + trade/base_strategy.py) |
| LH2~LH5 | 본 master와 무관 |
| LC1-LC3 (cutover invariants) | ✅ 보존 (cutover 미실행) |

---

## §8. preparation-first §3 정합

| 허용 | 본 master |
| --- | --- |
| docs 추가 | ✅ master plan 1건 + amend plan 1건 |
| sidecar 토글 변경 | ✅ N2 |
| trade/ runtime hook 통합 | ⚠️ N3 (LH1 부분 떨어냄 + VERIFY-1A guard amend) |
| Phase F/G ON actual | ⚠️ N4/N5 (매매 wiring 활성화) |

| 금지 | 본 master |
| --- | --- |
| F1 cutover `--apply` | ❌ 0건 (분야 ① 보류 유지) |
| 운영 `_database/` 영구 변경 | ❌ 0건 |
| LS direct dependency | ❌ 0건 |

→ master plan 자체는 P-lane. 후속 N1~N6 commit은 별도 ack 단계.

---

## §9. 검증 (각 commit별 의무)

```powershell
# 정적
python -m py_compile <변경 파일>

# audit
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check

# 분야별 추가
python scripts/audit_v3k_phase_f_gate2_execution.py    # N4
python scripts/audit_v3k_phase_g_gate3_execution.py    # N5
python scripts/audit_v3k_phase_f_rollback.py            # N4 rollback 검증
python scripts/backtest_v3k_phase_f_parity.py           # N4 parity
python scripts/backtest_v3k_phase_g_parity.py           # N5 parity
python scripts/benchmark_v3k_phase_g_engine.py          # N5 benchmark
```

---

## §10. 다음 인계

본 master + amend plan 정본화 commit 직후 N1 진입 가능. N1 (분야 ② 백테스트 evidence)는 매매 영향 0건이라 가장 안전.

각 N# commit:
1. update_log + evidence/script 작성
2. registry 섹션 추가
3. audit suite + git diff --check
4. 한글 commit 메시지

monitoring 단계 (N4/N5 후)는 자연 시간 경과. 사용자가 다른 세션 작업 가능.

---

## §11. 관련 문서

- `docs/plans/2026-05-22_v3k_f1_bypass_phase_fg_on_policy_amend_plan.md` (정책 amend)
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` (§2.4 amend 대상)
- `docs/plans/2026-05-14_v3k_page_080_phase_f_gate2_execution_plan.md` (N4 본체)
- `docs/plans/2026-05-14_v3k_page_081_phase_g_gate3_execution_plan.md` (N5 본체)
- `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md` (N3 baseline)
- `docs/plans/2026-05-14_v3k_page_083_gate5_gate6_review_only_plan.md` (N6 참조)
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (분야 ① 보류 자산)
- `docs/update_log/2026-05-22_v3k_midpoint_checkpoint_v5_4dbac74f_to_1a8fdcde.md` (v5 baseline)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-REMAINING-5FIELDS-COMPLETION-MASTER` 섹션)
