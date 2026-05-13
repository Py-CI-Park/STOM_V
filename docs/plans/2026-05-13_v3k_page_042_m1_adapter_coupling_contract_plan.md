# V3K Page 042 — M1 adapter coupling contract 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 041 / governance gap triage |
| 현재 page | Page 042 / M1 adapter coupling contract |
| 목적 | `v3k_analyzer_adapter.py`가 V3K staging module의 single point of coupling임을 명시하고, flag/contract 변경 정책을 고정한다. |
| 위험도 | medium-low |
| ON 여부 | 금지. contract/docstring/audit 보강만 수행한다. |

---

## 1. 허용 범위

Page042에서 허용되는 작업은 다음으로 제한한다.

1. `strategy/v3k_analyzer_adapter.py` module docstring 추가 또는 보강
2. FLAG/DEFAULT_FLAGS backward-compatible 정책 명시
3. `V3KAnalyzerOutput`, `normalize_v3k_flags`, Phase F/G flag surface 제거·rename 금지 경고
4. 필요한 경우 `scripts/audit_v3k_verify_1b_closure.py` 또는 별도 audit에 M1 contract 존재 검증 추가
5. docs/update_log 및 `docs/CARRY_FORWARD_REGISTRY.md` 갱신

---

## 2. 금지 범위

- feature flag 기본값 ON 변경
- Phase F/G/H ON 전환
- enable registry 생성
- USER_ACK 사용
- Kiwoom live runtime 변경
- 운영 DB 또는 `.omx/reports` commit
- live order/exit rule 연결
- LS Securities 직접 의존 추가

---

## 3. 완료 조건

- `v3k_analyzer_adapter.py`가 V3K single point of coupling contract를 명시한다.
- default-OFF 및 backward-compatible flag policy가 audit 가능한 형태로 남는다.
- VERIFY-1A/VERIFY-1B, Phase G proof, nonrelease sync, artifact guard가 계속 PASS한다.
- 다음 후보는 M2 audit runner/policy 또는 M3 evidence archive policy 중 더 안전한 항목으로 이동한다.

Directive: Page042는 governance contract 보강이지 ON 실행이 아니다. runtime path, DB, broker API, live decision은 변경하지 않는다.
