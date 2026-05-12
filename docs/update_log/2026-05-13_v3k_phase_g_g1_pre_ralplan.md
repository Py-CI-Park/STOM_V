# V3K Phase G G-1 pre-ralplan 결과

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| branch | `STOM_Version_2U_C` |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 이전 단계 | `phase-f-f4-approval-gate` |
| 현재 단계 | `phase-g-g1-pre-ralplan` |
| 다음 단계 | `phase-g-g1-engine-staging` |
| 결과 | `completed-consensus` |

---

## 1. 배경

Phase G는 V3 microstructure engine replacement를 2U_C에 반영하기 위한 고위험 단계다. LS API 전제를 제거하고 Kiwoom OPT* data shape로 재해석해야 하므로, 구현 전에 `--deliberate` ralplan 수준의 합의가 필요하다.

이번 Page036은 실제 engine 구현이 아니라, G-1 구현 전 stop condition과 검증 계획을 고정하는 단계다.

---

## 2. 합의 결과

- Option C, 즉 **inventory/mapping-first default-OFF staging**을 채택한다.
- G-1은 T01~T05만 수행한다.
  - T01: V3 microstructure engine inventory
  - T02: Kiwoom OPT* data-shape mapping 표
  - T03: LS-free default-OFF engine staging
  - T04: LS excise audit guard
  - T05: unit smoke
- G-2 parity/benchmark와 G-3 ON 전환은 다음 cycle로 분리한다.
- 2U_C 검증에서는 `verify_release_sync.py`가 아니라 `scripts/verify_nonrelease_sync.py`를 사용한다.

---

## 3. 고정된 LG invariant

| invariant | 고정 내용 |
| --- | --- |
| LG1 | LS direct dependency는 audit에서 0건이어야 한다. |
| LG2 | Kiwoom OPT* mapping 표가 engine contract보다 선행되어야 한다. |
| LG3 | parity ±15%는 G-2에서 검증하며 G-1 성공만으로 ON하지 않는다. |
| LG4 | 성능 ±20%는 G-2 benchmark에서 검증한다. |
| LG5 | ON commit, `V3K-PHASE-G-ENABLE`, `V3K_PHASE_G_USER_ACK=1`은 사용자 승인 cycle로 분리한다. |

---

## 4. 명시적으로 하지 않은 일

- `strategy/v3k_microstructure_engine.py`를 아직 생성하지 않았다.
- V3 code transplant를 아직 수행하지 않았다.
- Kiwoom 주문/청산/live runtime을 변경하지 않았다.
- 운영 `_database/` 또는 DB 파일을 변경하지 않았다.
- LS Securities REST/TR/REAL 직접 의존을 추가하지 않았다.
- Phase G ON 전환 또는 registry를 만들지 않았다.

---

## 5. 다음 단계

다음 단계는 Page037 / `phase-g-g1-engine-staging`이다. Page037에서는 T01~T05만 수행하며, G-2 parity/benchmark와 G-3 ON은 섞지 않는다.
