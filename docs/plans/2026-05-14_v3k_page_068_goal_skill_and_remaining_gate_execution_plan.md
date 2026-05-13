# V3K Page 068 goal/remaining-gate execution plan

| Field | Value |
| --- | --- |
| Date | 2026-05-14 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 068 |
| source | Page065 remaining gate matrix, Page066 goal completion authority audit, Page067 one-gate sequence guard, user question about goal skill |
| status | review-only-command-handoff |

---

## 1. 목적

현재 목표는 다음과 같이 고정한다.

```text
STOM_Version_2U_C에서 LS증권 직접 의존을 제외하고,
현재 Kiwoom API와 Kiwoom 주문/청산/live runtime을 유지한 채
V3의 DB/학습/분석/backtest/realtime/GUI 설정/sidecar/검증 체계를 반영한다.
```

이 page는 승인 gate 실행 문서가 아니다. Page068은 active Codex goal과 다음 `omx ralph` 실행 방향을 보존하는 review-only handoff다.

---

## 2. 실행 전 불변 조건

- `USER_ACK` marker는 명시적인 one-gate 승인 전 생성하지 않는다.
- enable registry heading은 명시적인 one-gate 승인 전 생성하지 않는다.
- 운영 `_database/` 내용은 쓰지 않고 DB 파일도 commit하지 않는다.
- 실제 `_v3k_sidecar` runtime artifact는 승인 전 생성하지 않는다.
- KHOPENAPI connect/login/live dry-run은 승인 전 실행하지 않는다.
- live order/exit rule consumption은 승인 전 연결하지 않는다.
- LS Securities REST/TR/REAL/order 직접 의존성은 채택하지 않는다.
- V3K feature flag는 승인 전 default-OFF를 유지한다.
- `STOM_Version_2U_C`에서는 `scripts/verify_release_sync.py`가 아니라 `scripts/verify_nonrelease_sync.py`를 사용한다.

---

## 3. Page068 작업 항목

1. Page065, Page066, Page067, `docs/CARRY_FORWARD_REGISTRY.md`를 재확인한다.
2. 현재 상태를 아래 명령으로 검증한다.
   - `python scripts/run_v3k_audit_suite.py`
   - `python scripts/verify_nonrelease_sync.py`
   - `git diff --check`
   - `git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`
3. 명시적인 단일 gate 승인 문구가 없으면 review-only 상태로 멈춘다.
4. 이후 사용자가 정확히 하나의 gate를 승인하면 그 gate만 preflight → execution → post-audit → commit 순서로 진행한다.

---

## 4. 중단 기준

남은 gate 중 하나라도 승인/실행 증거가 없으면 active goal을 완료 처리하지 않는다.

현재 첫 승인 후보는 다음 하나다.

```text
I approve gui-sidecar-write-await-user-approval only
```

위 문구 없이 `approve all`, `all gates`, `turn everything on` 류의 broad approval은 수용하지 않는다.
