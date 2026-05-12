# V3K Page 038 — Phase G G-2 parity/benchmark 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 037 / Phase G G-1 engine staging |
| 현재 page | Page 038 / Phase G G-2 parity/benchmark plan |
| 목적 | G-1 engine staging의 parity ±15% 및 성능 ±20% 검증 준비 |
| 위험도 | high |
| 구현 범위 | parity/benchmark script와 report 설계. ON 전환 제외 |

---

## 1. 허용 범위

- `scripts/backtest_v3k_phase_g_parity.py` 설계/구현
- `scripts/benchmark_v3k_phase_g_engine.py` 설계/구현
- synthetic 또는 checked-in fixture 기반 parity/benchmark smoke
- ignored `.omx/reports/` local evidence 생성 허용

---

## 2. 금지 범위

- Phase G ON 전환
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- Kiwoom 주문/청산/live runtime 변경
- 운영 `_database/` write
- DB 파일 commit
- live order/exit rule 연결

---

## 3. 완료 조건

- parity script가 ±15% 한계 기준을 문서화하고 PASS/FAIL을 반환한다.
- benchmark script가 ±20% 한계 기준을 문서화하고 PASS/FAIL을 반환한다.
- Phase G G-1 audit/smoke가 계속 PASS한다.
- `audit_v3k_runtime_activation_gap.py`의 다음 후보가 G-3 ON이 아니라 G-2 실행 또는 G-3 approval gate로 명확히 이동한다.
- 2U_C 검증은 `scripts/verify_nonrelease_sync.py`를 사용한다.
