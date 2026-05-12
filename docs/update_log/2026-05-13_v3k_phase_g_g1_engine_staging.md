# V3K Phase G G-1 engine staging 결과

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| branch | `STOM_Version_2U_C` |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 이전 단계 | `phase-g-g1-pre-ralplan` |
| 현재 단계 | `phase-g-g1-engine-staging` |
| 다음 단계 | `phase-g-g2-parity-benchmark-plan` |
| 결과 | `completed-default-off-staging` |

---

## 1. 배경

Page036에서 Phase G G-1은 inventory/mapping-first default-OFF staging으로 합의되었다. Page037은 그 합의에 따라 V3 후보 inventory, Kiwoom data-shape mapping, default-OFF microstructure engine, excise audit, unit smoke를 구현한 단계다.

---

## 2. 변경 사항

- V3 후보 파일 inventory를 `docs/plans/v3k_phase_g_inventory.md`에 기록했다.
- Kiwoom OPT* mapping을 `docs/update_log/2026-05-13_v3k_kiwoom_opt_data_shape_mapping.md`에 기록했다.
- `strategy/v3k_microstructure_engine.py`를 추가했다.
  - default-OFF
  - caller-owned row/frame만 입력
  - 운영 DB/runtime/order API 사용 없음
  - output contract: `미시구조신호`, `미시구조신뢰도`, `미시구조리스크`, `호가불균형`, `가중호가비율`
- `scripts/audit_v3k_phase_g_ls_excise.py`로 broker/runtime marker와 금지 import를 자동검증한다.
- `scripts/smoke_v3k_phase_g_engine_unit.py`로 default-OFF 및 synthetic enabled unit smoke를 검증한다.

---

## 3. 금지 상태 유지

- Phase G ON 전환 없음
- `V3K-PHASE-G-ENABLE` registry 없음
- `V3K_PHASE_G_USER_ACK=1` 사용 없음
- Kiwoom 주문/청산/live runtime 변경 없음
- 운영 `_database/` write 없음
- DB 파일 commit 없음
- live order/exit rule 연결 없음

---

## 4. 다음 단계

다음 단계는 Page038 / `phase-g-g2-parity-benchmark-plan`이다. G-2는 parity ±15%와 성능 ±20% 검증 script/report를 준비하는 단계이며, ON 전환은 여전히 G-3 사용자 승인 cycle로 분리한다.
