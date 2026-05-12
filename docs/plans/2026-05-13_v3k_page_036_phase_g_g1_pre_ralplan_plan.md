# V3K Page 036 — Phase G G-1 pre-ralplan 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 035 / Phase F F-4 approval gate |
| 현재 page | Page 036 / Phase G G-1 pre-ralplan |
| 목적 | V3 microstructure engine 이식 전 고위험 합의 재실행 |
| 기본 판정 | 구현 전 planning/consensus only |

---

## 0. 목적

Phase G는 V3 microstructure engine을 2U_C에 이식할 수 있는지 검토하는 고위험 단계다. LS Securities 의존 제거, Kiwoom OPT* data-shape mapping, parity 한계, 성능 한계, ON 승인 분리를 모두 만족해야 하므로 바로 구현하지 않는다.

Page036의 목적은 `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md`의 §C T01~T05를 실행하기 전에 Planner/Architect/Critic 합의를 다시 고정하는 것이다.

---

## 1. 이번 page에서 허용되는 일

- Phase G G-1 합의 재실행 문서화
- LG1~LG5 invariant 재검토
- pre-mortem 3개 시나리오 문서화
- expanded test plan 문서화
- V3 engine inventory와 Kiwoom OPT* mapping 표가 G-1 핵심 산출물임을 명시
- 다음 구현 page의 범위와 stop condition 정의

---

## 2. 이번 page에서 금지되는 일

- `strategy/v3k_microstructure_engine.py` 구현
- V3 microstructure engine code transplant
- Kiwoom 주문/청산/live runtime 변경
- live order/exit rule 연결
- 운영 `_database/` write
- DB 파일 commit
- LS Securities REST/TR/REAL 직접 의존 추가
- Phase G ON 전환

---

## 3. LG invariant

| invariant | 설명 | Page036 목표 |
| --- | --- | --- |
| LG1 | LS 의존 자동 제거 | LS marker·import·endpoint 검출 계획 확정 |
| LG2 | Kiwoom OPT* data-shape mapping 정본화 | V3 input field와 Kiwoom source field mapping 표 범위 확정 |
| LG3 | parity ±15% | benchmark 기간·metric·허용 오차 확정 |
| LG4 | 성능 ±20% | runtime cost·backtest wall time 비교 기준 확정 |
| LG5 | ON 단일 commit + 사용자 승인 | 구현 commit과 ON commit 분리 원칙 재확인 |

---

## 4. pre-mortem 시나리오

1. **LS 의존 잔존**: V3 engine 내부의 LS REST/TR/REAL 명칭·payload·field assumption이 2U_C로 유입될 수 있다. 대응은 자동 audit과 manual inventory를 둘 다 요구한다.
2. **Kiwoom data-shape mismatch**: LS 기준 호가/체결/잔량/미시구조 field가 Kiwoom OPT* field와 의미 또는 단위가 다를 수 있다. 대응은 mapping 표와 missing-field fallback을 구현 전 확정하는 것이다.
3. **parity 한계 이탈**: microstructure engine이 backtest 결과를 크게 바꿀 수 있다. 대응은 구현 전 metric·기간·허용 오차를 고정하고, 초과 시 OFF 유지한다.

---

## 5. 다음 OMX 명령

```powershell
omx ralplan --deliberate "V3K F4 Phase G G-1 (V3 microstructure engine 2U_C 이식, docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T01–T05)을 실행하기 전에 Planner/Architect/Critic 합의를 재실행한다. LG1(LS 의존 자동 제거) / LG2(Kiwoom OPT* data shape mapping 정본화) / LG3(parity ±15%) / LG4(성능 ±20%) / LG5(ON 단일 commit + 사용자 승인) invariant가 충분한지 pre-mortem 3 시나리오(LS 의존 잔존 / Kiwoom data shape mismatch / parity 한계 이탈)와 expanded test plan을 추가 검증한다. V3 engine inventory (T01)와 Kiwoom OPT* mapping 표 (T02)는 G-1의 핵심 산출물임을 명시한다. 2U_C 검증에서는 verify_release_sync.py가 아니라 scripts/verify_nonrelease_sync.py를 사용한다."
```

로컬 `omx ralplan`이 지원되지 않는 환경에서는 Codex 대화창에서 `$ralplan --deliberate ...`로 동일 내용을 실행한다.

---

## 6. Page036 완료 조건

- Phase G G-1 합의 문서가 생성된다.
- LG1~LG5가 구현 전 stop condition으로 고정된다.
- pre-mortem과 expanded test plan이 문서화된다.
- `scripts/audit_v3k_runtime_activation_gap.py`의 next candidate가 Phase G 구현 후보로 넘어갈지, 추가 합의가 필요한지 명확히 기록된다.
- 검증은 `verify_nonrelease_sync.py`, closure audit, runtime activation gap audit, `git diff --check`, DB/sidecar artifact status를 포함한다.
