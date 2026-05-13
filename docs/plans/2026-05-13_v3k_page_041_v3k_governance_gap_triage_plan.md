# V3K Page 041 — governance gap triage 완료

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 040 / Phase G G-3 approval gate |
| 현재 page | Page 041 / V3K governance gap triage |
| 다음 page | Page 042 / M1 adapter coupling contract |
| 목적 | Architect addendum에서 정본화한 M1/M2/M3 governance gap을 ON 전 후속 과제로 triage한다. |
| 결과 | `completed-triage` |
| ON 여부 | 금지. governance 정리만 수행했다. |

---

## 1. 입력 문서와 현재 판단

Page041은 아래 문서를 기준으로 진행했다.

- `docs/update_log/2026-05-13_v3k_code_review_addendum_architect_iterate.md`
- `docs/update_log/2026-05-13_v3k_phase_g_g3_approval_gate.md`
- `docs/plans/2026-05-13_v3k_page_040_phase_g_g3_approval_gate_plan.md`
- `scripts/audit_v3k_runtime_activation_gap.py`
- `scripts/audit_v3k_verify_1b_closure.py`

Architect addendum의 M1/M2/M3는 모두 Critical이 아니라 Minor governance gap이다. 따라서 Phase G/F/H ON을 실행할 사유가 아니며, ON 전 안전성을 높이는 후속 정리 대상으로 분리한다.

---

## 2. M1/M2/M3 triage 결과

| gap | 내용 | Page041 판정 | 이유 | 다음 처리 |
| --- | --- | --- | --- | --- |
| M1 | `v3k_analyzer_adapter.py`가 V3K staging module의 single point of coupling | 즉시 수행 가능 | 코드 동작 변경 없이 module docstring/contract로 변경 정책을 고정할 수 있다. | Page042 `governance-m1-adapter-contract` |
| M2 | audit guard CI/pre-commit 자동 실행 부재 | 보류 / 설계 필요 | `.git/hooks`는 repo 밖 로컬 상태이며, GitHub Actions 여부도 현재 lane에서 결정하기 어렵다. 우선 audit runner/CI 정책 문서와 후속 plan이 필요하다. | M1 이후 별도 page 후보 |
| M3 | Phase F/G/H benchmark baseline archive 정책 부재 | 보류 / 승인 필요 | 현재 원칙은 `.omx/reports/` commit 금지다. baseline archive 예외는 정책 변경이므로 별도 승인 또는 repo-tracked evidence path 설계가 필요하다. | M1/M2 이후 별도 page 후보 |

---

## 3. 왜 M1을 다음 후보로 선택했는가

M1은 실제 runtime, DB, live decision, broker API에 영향을 주지 않는 낮은 위험 작업이다. `v3k_analyzer_adapter.py`는 이미 여러 V3K staging module의 shared contract 역할을 하므로, module-level contract를 명시하면 다음과 같은 이점이 있다.

1. future agent가 FLAG 이름 변경 또는 제거를 쉽게 시도하지 못한다.
2. `DEFAULT_FLAGS` default-OFF 원칙을 문서화할 수 있다.
3. `V3KAnalyzerOutput`, `normalize_v3k_flags`, Phase F/G flag surface의 backward compatibility를 고정할 수 있다.
4. M2/M3처럼 repo 정책 또는 artifact 정책을 바꾸지 않는다.

따라서 다음 safe candidate는 Page042 / `governance-m1-adapter-contract`로 정한다.

---

## 4. 보류 항목의 이유

### M2 — audit guard 자동 실행

M2는 중요하지만 Page041에서 바로 hook을 설치하지 않는다.

- `.git/hooks/pre-commit`은 보통 git-tracked 파일이 아니다.
- GitHub Actions 추가는 remote CI 정책과 repository 운영 정책을 건드린다.
- 자동 실행을 강제하면 사용자 환경의 Windows/PowerShell/파이썬 경로 차이로 false failure가 생길 수 있다.

따라서 우선 Page042 M1을 완료한 뒤, 별도 Page에서 `scripts/run_v3k_audit_suite.py` 같은 tracked audit runner 또는 CI 문서 정책으로 분리하는 편이 안전하다.

### M3 — baseline archive

M3는 `.omx/reports` commit 금지 원칙과 충돌한다. Page039/040에서 생성된 latest JSON은 ignored local evidence이므로 commit하지 않았다. baseline을 commit하려면 아래 중 하나의 정책 선택이 필요하다.

- tracked `docs/evidence/` 또는 `docs/update_log/evidence/`에 summary JSON만 저장
- `.omx/reports`는 계속 ignored로 두고 hash/summary만 update_log에 기록
- 사용자 승인 후 특정 baseline report만 예외 commit

이는 artifact 정책 변경이므로 Page041에서는 보류하고, M1 이후 별도 page에서 설계해야 한다.

---

## 5. 금지 범위 유지

Page041에서는 아래를 수행하지 않았다.

- Phase F/G/H ON 전환
- `V3K-PHASE-F-ENABLE` 또는 `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_F_USER_ACK=1` 또는 `V3K_PHASE_G_USER_ACK=1` 사용
- Kiwoom live runtime 변경
- 운영 `_database/` write
- DB 파일 commit
- `.omx/reports/` commit
- live order/exit rule 연결

---

## 6. 다음 단계

다음 단계는 Page042 / `governance-m1-adapter-contract`이다. Page042에서는 `strategy/v3k_analyzer_adapter.py`의 module contract/docstring과 필요한 audit guard만 보강한다. 이 단계도 ON 실행이 아니며, runtime/DB/live path를 변경하면 안 된다.

Directive: governance triage 결과를 ON 승인으로 해석하지 말 것. M1/M2/M3는 ON 전 안정성 보강 과제이며, Phase F/G/H ON은 사용자 명시 승인 전까지 계속 금지된다.
