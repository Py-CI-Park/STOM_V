# V3K Page 039 — Phase G G-2 parity/benchmark work 완료

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 038 / Phase G G-2 parity·benchmark plan |
| 현재 page | Page 039 / Phase G G-2 parity·benchmark work |
| 다음 page | Page 040 / Phase G G-3 approval gate |
| 목적 | Page038에서 고정한 한계와 report schema에 따라 Phase G engine parity·benchmark proof를 생성한다. |
| 결과 | `completed-proof` |
| ON 여부 | 금지. Page039는 proof 생성까지만 수행했다. |

---

## 1. 수행 범위

Page039에서는 아래 두 script를 추가했다.

| 스크립트 | 역할 | 실행 방식 | 산출물 |
| --- | --- | --- | --- |
| `scripts/backtest_v3k_phase_g_parity.py` | Phase G microstructure output contract 5개 값이 synthetic 기준 fixture 대비 ±15% 안에 있는지 확인 | `V3KMicrostructureEngine(enabled=True)`를 명시적으로 사용하되 caller-owned row만 전달 | `.omx/reports/v3k-phase-g-parity-latest.json` |
| `scripts/benchmark_v3k_phase_g_engine.py` | fixed synthetic rows/iterations 기준 성능이 budget +20% 안에 있는지 확인 | `time.perf_counter()`와 `tracemalloc` 사용 | `.omx/reports/v3k-phase-g-benchmark-latest.json` |

두 report는 ignored `.omx/reports/` 아래에만 생성되며 commit 대상이 아니다.

---

## 2. parity 기준과 결과

Parity script는 아래 output contract를 검사한다.

| output | 기준 |
| --- | --- |
| `미시구조신호` | fixture 기준 정수 신호와 일치 |
| `미시구조신뢰도` | fixture 기준 대비 ±15% |
| `미시구조리스크` | fixture 기준 대비 ±15% |
| `호가불균형` | fixture 기준 대비 ±15% |
| `가중호가비율` | fixture 기준 대비 ±15% |

검증 fixture는 `buy_flow`, `sell_flow`, `balanced_flow` 세 scenario로 구성했다. 각 scenario는 Kiwoom field mapping contract를 직접 하드코딩하지 않고 `KIWOOM_OPT_FIELD_MAPPING`에서 field name을 가져온 caller-owned dict로 구성한다.

실행 결과:

```text
v3k phase g parity proof passed
buy_flow worst_delta=0.00%
sell_flow worst_delta=0.00%
balanced_flow worst_delta=0.00%
```

---

## 3. benchmark 기준과 결과

Benchmark script는 다음 조건을 사용한다.

| 항목 | 값 |
| --- | ---: |
| rows | 120 |
| iterations | 50 |
| operations | 6,000 |
| baseline seconds | 3.00 |
| allowed limit | +20% = 3.60 seconds |
| memory baseline | 8,000,000 bytes |
| memory allowed limit | +20% = 9,600,000 bytes |

실행 결과는 로컬 Windows/Python 3.13 환경에서 PASS했다.

```text
v3k phase g benchmark proof passed
elapsed <= 3.60s
peak <= 9,600,000 bytes
```

---

## 4. 계속 금지되는 범위

Page039 proof가 통과했지만 아래는 여전히 금지된다.

- Phase G ON 전환
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=True`를 기본값으로 변경
- Kiwoom 주문/청산/live runtime 변경
- `trade/base_strategy.py` 또는 live strategy decision path 연결
- 운영 `_database/` read/write 또는 DB 파일 commit
- LS Securities 직접 의존 import/call 추가
- GUI/pyd wrapper 연결

---

## 5. audit 반영

- `scripts/audit_v3k_phase_g_ls_excise.py`가 두 신규 script를 broker/runtime marker audit 대상으로 포함한다.
- `scripts/audit_v3k_runtime_activation_gap.py`의 next candidate는 `phase-g-g3-approval-gate`로 이동했다.
- `scripts/audit_v3k_verify_1b_closure.py`는 Page039 proof script와 문서를 closure 조건에 포함한다.

---

## 6. 다음 단계

다음 단계는 Page040 / `phase-g-g3-approval-gate`이다. Page040은 ON 실행 단계가 아니라, G-2 proof가 있어도 왜 바로 ON 할 수 없는지와 어떤 사용자 승인·rollback·monitoring·registry 조건이 필요한지를 고정하는 gate page로 시작해야 한다.

Directive: Page039 PASS는 Phase G ON 승인과 동의어가 아니다. G-3에서 명시적 사용자 승인, rollback, monitoring, registry 조건이 충족되기 전까지 default-OFF 상태를 유지한다.
