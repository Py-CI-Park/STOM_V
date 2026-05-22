# T1 + T2 — 분야 ⑥ + ⑦ 백테스트 검증 결과 정본화 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `1c02578c` (한글 dashboard + 5개 분야 순차 plan 직후) |
| 마스터 plan | `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` |
| 본 commit 정체성 | 5개 분야 순차 plan의 **T1 (⑥ 분석기) + T2 (⑦ 엔진) 병렬 실행** 결과 정본화 |
| 코드 변경 | 0건 (default-OFF parity + benchmark 결과 산출만) |
| 매매 영향 | 0건 |

---

## §0. TL;DR

```text
T1 (분야 ⑥ 분석기 7종 백테스트 검증) PASS — 모든 메트릭 delta 0%.
T2 parity (분야 ⑦ 마이크로 엔진 백테스트 검증) PASS — 3 시나리오 relative_delta 0.
T2 benchmark (분야 ⑦ 엔진 성능 측정) PASS — elapsed 2.796s/3.6s, peak 231KB/9.6MB.

진척률 영향:
  ⑥ 분석기 7종    30% → 50% (+20%p)
  ⑦ 마이크로 엔진 30% → 50% (+20%p)
  
F6 산식 단독 영향: +40%p / 700 = +5.7%p
```

---

## §1. baseline

5개 분야 순차 plan(`1c02578c`)에서 정의된 T1+T2 병렬 실행. 두 작업 상호 독립이라 동시 진행했다.

| 단계 | 분야 | script |
| --- | --- | --- |
| T1 | ⑥ 분석기 7종 | `scripts/backtest_v3k_phase_f_parity.py` |
| T2-A | ⑦ 엔진 parity | `scripts/backtest_v3k_phase_g_parity.py` |
| T2-B | ⑦ 엔진 benchmark | `scripts/benchmark_v3k_phase_g_engine.py` |

3개 script 모두 어제(2026-05-15 P3 prep) 단계에서 이미 작성되어 있었고, 본 commit은 본 PC에서 freshness 갱신 + 정본 evidence 승격.

---

## §2. T1 실행 결과 — 분야 ⑥ 분석기 백테스트 검증

### §2.1 실행 명령

```powershell
python scripts/backtest_v3k_phase_f_parity.py --report .omx/reports/v3k-phase-f-parity-t1.json
```

### §2.2 결과 (정본 evidence)

```
v3k phase f parity baseline passed: .omx/reports/v3k-phase-f-parity-t1.json
deltas: loss=0.00%/5.0%, mdd=0.00%/3.0%, trades=0.00%/10.0%
```

| 메트릭 | 실측 delta | 한계 | breach |
| --- | ---: | ---: | --- |
| `loss_pct` | **0.00%** | 5.0% | False |
| `mdd_pct` | **0.00%** | 3.0% | False |
| `trade_count_pct` | **0.00%** | 10.0% | False |

`enabled_metrics` (default-OFF analyzer 상태) = `disabled_metrics` (analyzer 없이 실행) 완전 일치:

```
loss        : 100.0 == 100.0
mdd         : 10.0  == 10.0
trade_count : 20.0  == 20.0
```

### §2.3 candidate_formula_values (V3 formula 값 확인)

13개 formula 값 모두 V3 globals에서 정상 산출:

```
가격대신뢰도 0.5  가격대점수 1.0   거래량신뢰도 0.5  거래량점수 1.0
리스크점수   5.0  변동성신뢰도 0.5  변동성점수 1.0    변손익신뢰도 0.5
손절수익률   0.0  예상수익률 0.0   익절수익률 0.0    패턴신뢰도 0.5
패턴점수     1.0
```

### §2.4 정본 evidence

`docs/evidence/v3k-phase-f-parity-t1-9024e3b9.json` (2,028 bytes)

---

## §3. T2 실행 결과 — 분야 ⑦ 마이크로 엔진 백테스트 검증

### §3.1 T2-A parity 실행

```powershell
python scripts/backtest_v3k_phase_g_parity.py --report .omx/reports/v3k-phase-g-parity-t2.json
```

결과:

```
v3k phase g parity proof passed
  - buy_flow:        worst_delta=0.00%, signal=buy
  - sell_flow:       worst_delta=0.00%, signal=sell
  - balanced_flow:   worst_delta=0.00%, signal=buy
```

mode: **`phase-g-proof-only-synthetic-fixture`**  
parity_limit: 0.15 (15%)  
3개 시나리오 모두 5개 output (`미시구조신호`, `미시구조신뢰도`, `미시구조리스크`, `호가불균형`, `가중호가비율`) **relative_delta = 0**

scope_guard:
- `broker_runtime_called`: False
- `live_decision_consumption`: False
- `runtime_hook_connected`: False
- `operating_store_written`: False

→ default-OFF 상태에서 엔진 출력 완전 일관성 확인.

### §3.2 T2-B benchmark 실행

```powershell
python scripts/benchmark_v3k_phase_g_engine.py --report .omx/reports/v3k-phase-g-benchmark-t2.json
```

결과:

```
v3k phase g benchmark proof passed
elapsed=2.796177s / 3.6s, peak=231223 / 9600000 bytes
```

| 지표 | 실측 | 한계 | 비율 |
| --- | ---: | ---: | ---: |
| elapsed_seconds | 2.796 | 3.600 | **78%** |
| peak_bytes | 231,223 | 9,600,000 | **2.4%** |
| baseline_seconds | 3.0 | - | - |
| baseline_peak_bytes | 8,000,000 | - | - |
| seconds_delta | -0.068 (-6.8%) | - | - |
| peak_delta | -0.971 (-97.1%) | - | - |
| iterations | 50 | - | - |
| operations | 6,000 | - | - |
| seconds_per_operation | 0.000466 | - | - |

elapsed는 baseline보다 6.8% 빠르고, peak memory는 baseline보다 97.1% 적음. 성능 충분 + 메모리 효율 매우 좋음.

### §3.3 T2 정본 evidence

- `docs/evidence/v3k-phase-g-parity-t2-9024e3b9.json` (1,489 bytes)
- `docs/evidence/v3k-phase-g-benchmark-t2-9024e3b9.json` (1,515 bytes)

---

## §4. 진척률 영향 (8개 분야 dashboard 갱신)

```
변경 전:
  ⑥ 분석기 7종         ████████░░░░░░░░░░░░  30%
  ⑦ 마이크로 엔진       ████████░░░░░░░░░░░░  30%

변경 후:
  ⑥ 분석기 7종         ████████████████░░░░  50%  (+20%p)
  ⑦ 마이크로 엔진       ████████████████░░░░  50%  (+20%p)
```

F6 산식 (#1~#7 카운트):

```
이전: (50+85+75+50+100+30+30)/700 = 420/700 = 60.0%
이후: (50+85+75+50+100+50+50)/700 = 460/700 = 65.7%

⊕ +5.7%p
```

⚠️ master plan 53.6% 표기는 mid-checkpoint v4 산식(#2/#3/#4/#5 보수 카운트) 기준. v5 mid-checkpoint 정본화 시점에 통일.

---

## §5. Scope guard

| # | 항목 | 보장 | 근거 |
| ---: | --- | --- | --- |
| 1 | Kiwoom runtime mutation | 0건 | T1/T2 script는 mock fixture 사용 |
| 2 | operating `_database/` write | 0건 | `operating_store_written: false` |
| 3 | `_database_v3k_shadow/` 변경 | 0건 | read 0건 |
| 4 | `_v3k_sidecar/` 토글 변경 | 0건 | `sidecar_toggle_changed: false` |
| 5 | feature flag default-ON 전환 | 0건 | default-OFF 유지 |
| 6 | live broker runtime 호출 | 0건 | `broker_runtime_called: false`, `runtime_hook_connected: false` |
| 7 | live trade decision 소비 | 0건 | `live_decision_consumption: false` |
| 8 | LS direct dependency | 0건 | smoke script LS import 0건 |
| 9 | V3K USER_ACK env durable 발급 | 0건 | 본 단계에서 발급 안 함 |

---

## §6. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log 1건 + evidence 3건 |
| read-only smoke 실행 | ✅ 3개 script default-OFF |

| 금지 | 본 commit |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| `_database_v3k_shadow/` 변경 | ❌ 0건 |
| `_v3k_sidecar/` 토글 ON | ❌ 0건 |
| feature flag default-ON 전환 | ❌ 0건 |
| LS direct dependency 추가 | ❌ 0건 |
| cutover script `--apply` 실행 | ❌ 0건 (분야 ① 보류 유지) |

→ P-lane 적격.

---

## §7. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

모든 audit 통과 예정.

---

## §8. 다음 인계

본 T1+T2 commit 직후 5개 분야 순차 plan의 **T3 (분야 ② F5 마지막 등록 정리, ~15분)** 진입 가능.

이후 T4 (분야 ④ 수식 전역값 진단 + plan) + T5 (분야 ③ 사이드카 진단 + plan)이 잔여.

T1+T2 완료로 5개 분야 중 **2개 완전 진척** (실행 evidence 산출), 3개 잔여 (T3 정리 / T4·T5 진단).

---

## §9. 관련 문서

- `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` (master plan)
- `docs/update_log/2026-05-22_v3k_progress_dashboard_korean.md` (한글 dashboard)
- `docs/evidence/v3k-phase-f-parity-t1-9024e3b9.json` (T1 정본)
- `docs/evidence/v3k-phase-g-parity-t2-9024e3b9.json` (T2-A 정본)
- `docs/evidence/v3k-phase-g-benchmark-t2-9024e3b9.json` (T2-B 정본)
- `scripts/backtest_v3k_phase_f_parity.py` (T1 실행)
- `scripts/backtest_v3k_phase_g_parity.py` (T2-A 실행)
- `scripts/benchmark_v3k_phase_g_engine.py` (T2-B 실행)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-T1-PHASE-F-PARITY` + `V3K-T2-PHASE-G-PARITY-BENCHMARK` 섹션)
