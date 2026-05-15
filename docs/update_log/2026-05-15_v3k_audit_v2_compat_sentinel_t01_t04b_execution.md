# V3K Audit V2-Compat Sentinel — T01–T04b 실행 결과 보고

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-15 KST |
| 출처 plan | `docs/plans/2026-05-14_v3k_audit_v2_compat_kiwoom_sentinel_plan.md` (ralplan iteration 2 합의 v2, `4d132139`) |
| 트리거 발견 문서 | `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (`cdd77093`) |
| 실행 범위 | T01–T04b (전체 5 task) |
| 본 PC host_identifier | `9024e3b9` |
| 본 PC 결과 | **Gate4 BLOCKED 자연 해제** (`khopenapi_compatible: false → true`) |

---

## 0. TL;DR

```text
V3K audit V2-compat sentinel 보강 plan v2의 T01–T04b 5 task 모두 commit 완료.
본 PC에서 audit 실행 결과 khopenapi_compatible=true로 전환되어 Gate4 BLOCKED 자연 해제 확정.
V01–V08 invariant 모두 PASS (V05는 plan §D.1 결정 룰대로 SKIP).
보존 원칙 5건(Kiwoom runtime / 운영 _database / LS 직접 의존 / DB 파일 commit / CLI surface) 회귀 0건.
```

---

## 1. 실행 commit 5건

| Commit | Task | 산출 |
| --- | --- | --- |
| `5da51dcd` | T01+T02 | `strategy/v3k_kiwoom_sentinel.py` (98줄) + hook `V3KSentinelResult` dataclass + `resolve_khopenapi_sentinel()` 메서드 |
| `696cc4b3` | T03 | audit emitter schema v2 + primary/corroborating 분리 emit + `candidates[]` backward compat |
| `2611ab61` | T04a | `smoke_v3k_kiwoom_sentinel_scenarios.py` (mock 4 scenario) |
| 본 commit | T04b + 거버넌스 | 본 PC live audit evidence + CARRY_FORWARD_REGISTRY V3K-AUDIT-V2-COMPAT 섹션 + 본 update_log |

---

## 2. V01–V08 invariant 검증 결과

| ID | 항목 | 결과 |
| --- | --- | --- |
| V01 | `resolve_khopenapi_path` 시그니처 `Path \| None` 보존 | **PASS** (inspect.signature 정적 assertion) |
| V02 | `resolve_khopenapi_sentinel` 신규 메서드 export + `V3KSentinelResult \| None` 반환 | **PASS** |
| V03a | mock primary only (S1=True, S2=False, S3=False) → compatible=True | **PASS** |
| V03b | mock corroborating only (R4 boundary, S1=False, S2=True, S3=True) → compatible=False | **PASS** |
| V04a | mock both (S1=True, S2=True, S3=True) → compatible=True | **PASS** |
| V04b | mock neither (S1=False, S2=False, S3=False) → compatible=False | **PASS** |
| V05 | `gate4_blocked_environment` audit 결정 룰 | **SKIP** (primary exists → plan §D.1 표) |
| V06 | `schema_version == 2` + 신규 4 필드 + `candidates[]` 보존 | **PASS** |
| V07 | `khopenapi_compatible == khopenapi_primary_signal.exists` invariant | **PASS** (4 scenario + 본 PC 실 결과 모두 만족) |
| V08 | 본 PC live audit + host hash trail | **PASS** (`docs/evidence/v3k-phase-h-env-host-9024e3b9.json`) |

---

## 3. 본 PC live audit 결과 (T04b)

```json
{
  "schema_version": 2,
  "phase": "V3K-PHASE-H-H1",
  "host_identifier": "9024e3b9",
  "captured_at_utc": "2026-05-15T00:05:21.149353+00:00",
  "evidence_kind": "V3K-PHASE-H-T04B-LIVE-AUDIT",
  "khopenapi_compatible": true,
  "khopenapi_primary_signal": {
    "source": "ActiveX ProgID",
    "path": "HKEY_CLASSES_ROOT\\KHOPENAPI.KHOpenAPICtrl.1",
    "exists": true
  },
  "khopenapi_corroborating_signals": [
    {"source": "OPENAPI_PATH directory", "path": "C:\\OpenAPI", "exists": true, "dll_count": 6},
    {"source": "legacy DLL", "path": "C:\\OpenAPI\\khopenapi.dll", "exists": false}
  ],
  "khopenapi_corroboration_count": 1,
  "candidates": [
    {"source": "default", "path": "C:\\OpenAPI\\khopenapi.dll", "exists": false},
    {"source": "default", "path": "C:\\Kiwoom\\OpenAPI\\khopenapi.dll", "exists": false},
    {"source": "default", "path": "C:\\OpenAPI-W\\khopenapi.dll", "exists": false}
  ],
  "contract_only": true,
  "live_connect_attempted": false,
  "order_or_exit_path_changed": false
}
```

전체 결과는 `docs/evidence/v3k-phase-h-env-host-9024e3b9.json` 참조.

---

## 4. `gate4_blocked_environment` audit 의미 변경

본 audit는 T03 적용 후 다음과 같이 self-reject:

```
AssertionError: KHOPENAPI sentinel is available; do not use the blocked-env audit path.
Run an actual live-dryrun execution gate instead.
```

이는 **plan v2 §D.1 V05 결정 룰의 코드 측면 자동 검증** — `primary_signal.exists=true`일 때 `gate4_blocked_environment` audit는 SKIP되어야 한다는 명시적 분기.

후속 처리: 분기 plan(`2026-05-XX_v3k_phase_h_lh4_clarification_plan.md`)에서 audit name/logic 정정 별도 진행 (Critic R6 follow-up).

---

## 5. 보존 원칙 검증 (회귀 0건)

| 원칙 | 검증 | 결과 |
| --- | --- | --- |
| Kiwoom runtime 무변경 | `git diff cd6f5bd2..HEAD --name-only -- trade/ utility/ Kiwoom_OpenAPI/ KiwoomOpenAPI/ receiver/ trader/` | 0건 ✅ |
| 운영 `_database/` 무변경 | `git diff cd6f5bd2..HEAD --name-only -- _database/` | 0건 ✅ |
| LS 직접 의존 도입 0건 | `grep -rn 'ls_securities\|LS_REST\|xingapi\|restapi_ls' strategy/v3k_kiwoom_sentinel.py strategy/v3k_kiwoom_dryrun_hook.py scripts/audit_v3k_phase_h_env_check.py scripts/smoke_v3k_kiwoom_sentinel_scenarios.py` | 0건 ✅ |
| DB 파일 commit 0건 | `git log --all -- '*.db' '*.sqlite*'` | 0건 ✅ |
| CLI surface 무회귀 | `init_v3k_shadow_db.py` 무변경, audit/hook의 `--stdout` 등 기존 인터페이스 보존 | ✅ |
| feature flag default-OFF | `FLAG_PHASE_H_KIWOOM_DRYRUN` 기본 False 유지 | ✅ |
| hook 시그니처 보존 (V01) | `resolve_khopenapi_path() -> Path | None`, `require_khopenapi_environment() -> Path` | ✅ |

---

## 6. 다음 단계

본 plan v2 §K freeze 정책에 따라 본 plan은 commit 후 freeze. 후속 작업은 별도 plan으로 분기.

### 6.1 즉시 가능

- audit 보강 결과를 다른 audit/smoke 회귀 일괄 검증 (예: `smoke_v3k_phase_h_hook_unit.py` 등 기존 24 smoke + 19 gate/audit)

### 6.2 별도 plan 필요

- **Phase H §K.7 clarification 분기 plan**: `gate4_blocked_environment` audit name/logic 정정 + Phase H plan §K.5–K.7 절 추가
- **Phase H H-2 본체 실행 plan**: 본 PC 환경 + 사용자 명시 승인(`V3K_PHASE_H_USER_ACK=1`) + Phase H plan §C T05 절차로 1회 dry-run 실행

### 6.3 V3K 미션 진척

| audit §6.2 항목 | 본 commit 전 | 본 commit 후 |
| --- | --- | --- |
| #5 live Kiwoom dry-run | S1 25% (plan 정본화만) | **S1 → S2 진입 준비** (Gate4 BLOCKED 해제, H-2 실행은 사용자 승인 후) |

다른 항목은 본 commit으로 변동 없음 (audit 보강만 수행).

---

## 7. 관련 문서

- v2 plan: `docs/plans/2026-05-14_v3k_audit_v2_compat_kiwoom_sentinel_plan.md` (`4d132139`)
- 발견 baseline: `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (`cdd77093`)
- Phase H plan: `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (`6e5cdf43`)
- audit 보고서: `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md`
- mid-checkpoint v2: `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_067886d3.md`
- F2 letter convention: `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md`
- F6 산식: `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md`
- T04b live evidence: `docs/evidence/v3k-phase-h-env-host-9024e3b9.json`
- Registry entry: `docs/CARRY_FORWARD_REGISTRY.md` (`## V3K-AUDIT-V2-COMPAT`)

---

## 8. 본 update_log freeze 정책

- **freeze 시점**: 본 commit
- **갱신 정책**: 본 문서는 T01–T04b 실행 snapshot. 후속 단계는 별도 update_log 신설.
- **인용 의무**: Phase H H-2 본체 실행 plan은 본 update_log §3의 host_identifier `9024e3b9`를 baseline evidence로 인용.
