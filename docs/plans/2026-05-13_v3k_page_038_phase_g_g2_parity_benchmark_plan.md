# V3K Page 038 — Phase G G-2 parity/benchmark 계획 고정

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 037 / Phase G G-1 default-OFF microstructure engine staging |
| 현재 page | Page 038 / Phase G G-2 parity·benchmark plan |
| 다음 page | Page 039 / Phase G G-2 parity·benchmark work |
| 목적 | Phase G engine을 ON 하기 전에 parity ±15%, 성능 ±20% 검증을 어떤 입력·출력·한계로 수행할지 고정한다. |
| 결론 | Page038은 실행 스크립트 구현 전 계획/감사/registry 고정까지만 수행한다. 실제 parity·benchmark 스크립트 구현은 Page039에서 진행한다. |
| 위험도 | high |

---

## 1. 왜 Page038을 별도 계획 page로 분리했는가

Page037에서 `strategy/v3k_microstructure_engine.py`는 이미 `enabled=False` 기본값, caller-owned row/mapping 입력, Kiwoom runtime 미접속, LS 직접 의존 금지 조건으로 staging되었다. 그러나 다음 단계에서 바로 ON 또는 live 연결을 하면 아래 위험이 발생한다.

1. V3 `strategy/analyzer_microstructure.py`와 2U_C 경량 engine 출력이 같은 방향인지 검증되지 않았다.
2. Kiwoom OPT* field mapping의 fallback이 실제 계산 민감도에 어떤 영향을 주는지 아직 수치화되지 않았다.
3. 실시간 주문/청산 경로에 연결하기 전에 성능 예산을 확인하지 않으면 live loop 지연 위험이 생긴다.
4. G-1 unit smoke는 구조 검증이지 parity·benchmark 검증이 아니다.

따라서 Page038은 “검증 실행 전 계획 고정”으로 두고, Page039에서만 script 구현·실행을 수행한다.

---

## 2. Page039에서 구현할 스크립트 범위

| 스크립트 | 목적 | 허용 입력 | 금지 입력/동작 | 출력 |
| --- | --- | --- | --- | --- |
| `scripts/backtest_v3k_phase_g_parity.py` | Phase G engine output이 기준 fixture 대비 ±15% 한계 안에 있는지 확인 | synthetic/caller-owned fixture, checked-in tiny fixture | 운영 `_database/`, live Kiwoom, 주문/청산 runtime | console PASS/FAIL, ignored `.omx/reports/v3k-phase-g-parity-latest.json` |
| `scripts/benchmark_v3k_phase_g_engine.py` | 계산 성능이 기준 대비 ±20% budget 안에 있는지 확인 | synthetic rows, `time.perf_counter`, 선택적 `tracemalloc` | 운영 DB, 네트워크/API, live loop 연결 | console PASS/FAIL, ignored `.omx/reports/v3k-phase-g-benchmark-latest.json` |

Page039 script는 deterministic fixture 기반이어야 하며, 실행할 때마다 운영 DB·sidecar·Kiwoom API를 읽거나 쓰면 안 된다.

---

## 3. parity 기준

Page039 parity script는 아래 output contract를 검사한다.

| output | 의미 | 허용 오차 |
| --- | --- | --- |
| `미시구조신호` | buy=1, sell=-1, hold=0 | 정수 신호 일치 또는 fixture 기준 허용 범위 |
| `미시구조신뢰도` | 0~1 confidence | 기준값 대비 ±15% |
| `미시구조리스크` | 0~1 risk | 기준값 대비 ±15% |
| `호가불균형` | bid/ask imbalance | 기준값 대비 ±15% |
| `가중호가비율` | weighted bid/ask depth ratio | 기준값 대비 ±15% |

기준 fixture는 V3 baseline을 직접 live로 호출하지 않고, Page037 engine contract와 Kiwoom mapping 문서에 맞춘 synthetic baseline으로 시작한다. 추후 실제 V3 baseline extraction이 필요하면 별도 page에서 추가하되, LS API 또는 runtime broker dependency를 끌어오면 안 된다.

---

## 4. benchmark 기준

Page039 benchmark script는 다음 기준을 사용한다.

- 반복 횟수와 row 수는 script 상수로 고정하여 재현 가능하게 한다.
- wall-clock은 `time.perf_counter()`로 측정한다.
- memory 측정이 필요한 경우 `tracemalloc`을 사용하되, memory failure가 Windows/Python minor version에 과민하지 않도록 보조 지표로 둔다.
- 허용 한계는 기준 budget 대비 ±20%이다.
- benchmark 결과는 `.omx/reports/v3k-phase-g-benchmark-latest.json`에만 남기며 이 경로는 commit 대상이 아니다.

---

## 5. 금지 범위

아래 항목은 Page038/Page039 모두에서 금지한다.

- Phase G ON 전환
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=True`를 runtime 기본값으로 변경
- Kiwoom 주문/청산/live runtime 변경
- `trade/base_strategy.py` 또는 live strategy decision path 연결
- 운영 `_database/` write 또는 DB 파일 commit
- LS Securities REST/TR/REAL 직접 의존 추가
- GUI/pyd wrapper 연결

---

## 6. Page038에서 실제 수행한 일

- Page038 계획 문서를 깨진 인코딩 상태에서 UTF-8 한글 문서로 재작성했다.
- Page039 실행 계획 문서를 새로 생성했다.
- `docs/CARRY_FORWARD_REGISTRY.md`에 `V3K-PHASE-G-G2-PARITY-BENCHMARK-PLAN` 결정을 추가했다.
- `scripts/audit_v3k_runtime_activation_gap.py`의 next candidate를 `phase-g-g2-parity-benchmark-work`로 이동시켰다.
- `scripts/audit_v3k_verify_1b_closure.py`에 Page038 plan 완료와 Page039 work plan 존재를 감사 대상으로 추가했다.
- Phase G ON은 수행하지 않았다.

---

## 7. 완료 조건과 검증

Page038 완료 조건은 다음과 같다.

- runtime activation gap audit의 next candidate가 `phase-g-g2-parity-benchmark-work`로 이동한다.
- VERIFY-1B closure audit이 Page038 문서와 Page039 계획을 요구한다.
- Phase G G-1 LS excise audit/smoke가 계속 PASS한다.
- 2U_C non-release sync 검증이 PASS한다.
- `_database/`, `_database_v3k_shadow/`, `_log/`, `*.db`, sidecar/report artifact가 commit 대상에 들어오지 않는다.

Page039 완료 전까지 `scripts/backtest_v3k_phase_g_parity.py`와 `scripts/benchmark_v3k_phase_g_engine.py`는 요구 스크립트 목록에 넣지 않는다. 이는 “계획 완료”와 “검증 구현 완료”를 혼동하지 않기 위한 의도적 분리다.

---

## 8. 다음 단계

다음 단계는 Page039 / `phase-g-g2-parity-benchmark-work`이다.

Page039에서만 아래를 수행한다.

1. `scripts/backtest_v3k_phase_g_parity.py` 구현
2. `scripts/benchmark_v3k_phase_g_engine.py` 구현
3. synthetic/caller-owned fixture 기반 실행
4. `.omx/reports/*latest.json` ignored evidence 생성
5. G-2 PASS 후에도 G-3 ON은 별도 사용자 승인 gate로 유지

Directive: Page038 계획 완료를 Phase G ON 승인으로 해석하지 말 것. Page039는 parity·benchmark proof까지만 수행하며, G-3 ON은 별도 명시 승인 없이는 실행하지 않는다.
