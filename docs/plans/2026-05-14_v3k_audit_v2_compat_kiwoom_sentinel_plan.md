# V3K Audit V2-Compat Kiwoom Sentinel 보강 실행 계획 (옵션 A)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-14 KST |
| trigger 문서 | `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (`cdd77093`) |
| 대상 phase | Phase H 보조 — Gate4 false-negative 해소 |
| Phase letter | (audit §8에 없음, audit 보강 phase) — F2 convention에 따라 파일명만 사용 |
| 현재 단계 (F6 산식) | S0 (0%) — plan 미작성 → 본 commit으로 S1 (25%) |
| 목표 단계 | S3 (75%) — audit/hook이 V2 ActiveX 방식 정확 인식, Gate4 BLOCKED 자연 해제 |
| 위험도 | **중간** — audit/hook 코드 수정 + Phase H plan §B LH4 의미 명확화 (코드 동작 불변, sentinel 검사 확장) |
| 의존 입력 | Phase H plan(`6e5cdf43`), 발견 문서(`cdd77093`), 본 commit |
| **ralplan 의무** | **YES** — 코드 변경 commit 전 short deliberation 합의 재실행 권장 |

---

## 0. V3K 미션 재인용 + 본 plan의 위치

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영하되 Kiwoom증권 API/runtime을 유지한다.
LS Securities 직접 의존은 제외하고 default-OFF로 단계적 cutover한다.
```

본 plan은 위 미션의 "**Kiwoom API/runtime 유지**" 조항을 **audit 수준에서도 정확히 표현**하기 위한 보조 작업이다. Phase H를 새로 만드는 것이 아니라, Phase H가 이미 가정한 KHOPENAPI sentinel 검사가 V2 실제 사용 방식과 정합하도록 수정한다.

---

## A. Drivers + Scope

### A.1 Drivers

1. `cdd77093` 발견 문서 §5: 옵션 A가 V2 호환 미션과 정확히 일치하는 유일 선택
2. Gate4 false-negative → Gate5·Gate6 의존 잠김 → V3K 미션 closure 영원 불가
3. audit가 STOM의 실제 키움 사용 코드(`autologin.py:24`)와 다른 sentinel을 검사하는 inconsistency를 해소

### A.2 Scope

| In scope | Out of scope |
| --- | --- |
| `strategy/v3k_kiwoom_dryrun_hook.py`의 `resolve_khopenapi_path()` 보강 | KHOPENAPI 환경에서 실제 dry-run 실행 (Gate4 본체, Phase H plan §C T05) |
| `scripts/audit_v3k_phase_h_env_check.py`의 `_candidate_rows()` 확장 | 운영 `_database/` 변경, Kiwoom runtime 변경 |
| Phase H plan §B LH4 invariant의 의미 명확화 (별도 commit) | Gate5/Gate6 unlock (Gate4 본체 실행 후) |
| ActiveX ProgID 등록 검사 추가 | LS Securities 직접 의존 도입 (영구 금지, L7) |
| `OPENAPI_PATH` 디렉터리 존재 검사 추가 | `inicore_*.dll` 직접 import (의미 부적합) |
| sentinel 검사 결과의 `khopenapi_compatible` 산출 boolean 로직 갱신 | feature flag default 변경 (모두 OFF 유지) |

---

## B. Phase-specific invariants

### B.1 보존 (L1–L9)

모두 보존. 특히:
- **L1**: schema_hash semantic hash 무관 (sentinel 검사만 변경, schema 무변경)
- **L2**: `init_v3k_shadow_db.py` 외부 동작 보존 (본 plan 미관련)
- **L4**: `_database_v3k_shadow/` 디렉터리 위치 무관
- **L5**: feature flag default-OFF 유지 (sentinel 검사가 ON 전환을 자동으로 시키지 않음)
- **L7**: LS 직접 의존 금지 (sentinel 검사에 LS marker 등장 0건 유지)
- **L9**: STOM CLI surface 무변경 (`init_v3k_shadow_db.py --dry-run` required 등 무관)

### B.2 신규 V2-compat sentinel 전용 invariants (LA1–LA3)

| # | invariant | 사유 |
| --- | --- | --- |
| LA1 | sentinel 검사는 다음 3개 중 **하나 이상 확인** 시 compatible: (a) ActiveX ProgID `KHOPENAPI.KHOpenAPICtrl.1` 등록, (b) `utility.setting_base.OPENAPI_PATH` 디렉터리 존재, (c) legacy `khopenapi.dll` 파일 존재 | V2 호환 + 미래 변경 대응 + 기존 audit 행위 보존 |
| LA2 | sentinel 검사 결과는 candidate별 source/path/exists 3-tuple 보고 (구체적 evidence trail) | governance + 디버깅 |
| LA3 | KHOPENAPI 환경 부재 시(3개 모두 False) `require_khopenapi_environment()` 거부 동작은 그대로 유지 (LH4 보존) | KHOPENAPI 없는 PC에서도 안전 |

---

## C. 상세 실행 계획 (T01–T06)

### C.0 task별 실행/commit lane

| Task | 실행 lane | commit lane |
| --- | --- | --- |
| T01 (hook `resolve_khopenapi_path` 보강) | 양쪽 검증 | `STOM_Version_2U_C` |
| T02 (audit `_candidate_rows` 확장) | 양쪽 검증 | `STOM_Version_2U_C` |
| T03 (hook unit smoke 갱신) | 양쪽 검증 | `STOM_Version_2U_C` |
| T04 (audit env_check 결과 재확인 — 본 PC에서) | **본 PC만** (실 환경) | n/a (검증) |
| T05 (Phase H plan §B LH4 의미 명확화) | `STOM_Version_2U_C` | `STOM_Version_2U_C` |
| T06 (CARRY_FORWARD_REGISTRY V3K-AUDIT-V2-COMPAT 섹션) | `STOM_Version_2U_C` | `STOM_Version_2U_C` |

### T01. `resolve_khopenapi_path()` 보강 (`strategy/v3k_kiwoom_dryrun_hook.py`)

- 목표: 3개 sentinel(ProgID / `OPENAPI_PATH` 디렉터리 / legacy DLL) 중 하나 이상 확인 시 compatible
- 변경 파일: `strategy/v3k_kiwoom_dryrun_hook.py` (수정)
- 변경 의도:
  - 새 helper `_active_x_progid_registered(progid: str) -> bool`:
    - `winreg.OpenKey(HKEY_CLASSES_ROOT, "KHOPENAPI.KHOpenAPICtrl.1")` 시도
    - 성공 시 True, `OSError` 시 False
    - non-Windows 환경에서는 import 실패 → False
  - 새 helper `_setting_base_openapi_path() -> Path | None`:
    - `utility.setting_base.OPENAPI_PATH` import 시도
    - import 실패 또는 path 부재 시 None
  - `resolve_khopenapi_path()`가 다음 순서로 반환:
    1. 환경 변수 `V3K_KHOPENAPI_DLL` 경로 (기존 유지)
    2. ProgID 등록 시 → `"registered:KHOPENAPI.KHOpenAPICtrl.1"` (sentinel str)
    3. `OPENAPI_PATH` 디렉터리 존재 시 → 디렉터리 Path
    4. 기존 4개 legacy DLL 후보 (모두 부재면 None)
  - 반환 형식이 기존 `Path | None` → `Path | str | None`으로 확장 (str은 ProgID sentinel)
  - `require_khopenapi_environment()`의 SystemExit 메시지 보존 (LH4)
- 완료 조건:
  ```powershell
  python -m py_compile strategy/v3k_kiwoom_dryrun_hook.py
  python -c "from strategy.v3k_kiwoom_dryrun_hook import V3KKiwoomDryrunHook; h=V3KKiwoomDryrunHook(feature_flags={'V3K_PHASE_H_KIWOOM_DRYRUN':True}); print(h.resolve_khopenapi_path())"
  ```
  PASS: 현재 PC에서 None이 아닌 결과 (ProgID sentinel 또는 OPENAPI_PATH)
- 선행: 없음

### T02. `_candidate_rows()` 확장 (`scripts/audit_v3k_phase_h_env_check.py`)

- 목표: candidate 표에 ActiveX ProgID + `OPENAPI_PATH` 행 추가
- 변경 파일: `scripts/audit_v3k_phase_h_env_check.py` (수정)
- 변경 의도:
  - 기존 `_candidate_rows()`에 다음 행 추가:
    ```python
    # ActiveX ProgID 등록 확인 (winreg)
    rows.append({
        "source": "ActiveX ProgID",
        "path": "HKEY_CLASSES_ROOT\\KHOPENAPI.KHOpenAPICtrl.1",
        "exists": _active_x_progid_registered("KHOPENAPI.KHOpenAPICtrl.1"),
    })
    # STOM setting_base OPENAPI_PATH 디렉터리 확인
    openapi_dir = _setting_base_openapi_path()
    rows.append({
        "source": "OPENAPI_PATH",
        "path": str(openapi_dir) if openapi_dir else "(unresolvable)",
        "exists": bool(openapi_dir and openapi_dir.is_dir()),
    })
    ```
  - `build_report()`의 `khopenapi_compatible` 계산이 자동으로 새 candidate 포함 (`bool(compatible)` 그대로)
  - `next_gate` 메시지 갱신: "H-2/H-3 require KHOPENAPI sentinel (DLL/ProgID/OPENAPI_PATH) and explicit user approval"
- 완료 조건:
  ```powershell
  python -m py_compile scripts/audit_v3k_phase_h_env_check.py
  python scripts/audit_v3k_phase_h_env_check.py --stdout
  ```
  PASS: stdout JSON에 6개 candidate (기존 4 + 신규 2), `khopenapi_compatible=true` (현 PC), `live_connect_attempted=false`
- 선행: T01 (helper 함수가 hook에 있으므로 import 또는 동일 helper 복제)

### T03. hook unit smoke 갱신 (`scripts/smoke_v3k_phase_h_hook_unit.py`)

- 목표: 신규 sentinel 3종 모두에 대한 unit 시나리오 추가
- 변경 파일: `scripts/smoke_v3k_phase_h_hook_unit.py` (수정)
- 변경 의도:
  - 시나리오 1: ProgID 등록 mock → compatible 반환 확인
  - 시나리오 2: `OPENAPI_PATH` 디렉터리 mock (tempfile) → compatible 반환 확인
  - 시나리오 3: 모두 부재 mock → SystemExit 확인 (LA3/LH4 보존)
  - 기존 hook unit 검증(LH1 주문 메서드 등록 거부, LH2 idempotent)는 그대로 유지
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_phase_h_hook_unit.py
  ```
  PASS: exit 0, 3개 시나리오 + 기존 unit 모두 PASS
- 선행: T01

### T04. audit env_check 본 PC 실 결과 재확인

- 목표: 본 PC에서 실제로 `khopenapi_compatible=true`로 전환되는지 확인
- 변경 파일: 없음 (검증)
- 실행:
  ```powershell
  python scripts/audit_v3k_phase_h_env_check.py --stdout
  ```
- 기대 결과:
  ```json
  {
    "khopenapi_compatible": true,
    "candidates": [
      {"source": "V3K_KHOPENAPI_DLL", "path": "...", "exists": false},
      {"source": "default", "path": "C:\\OpenAPI\\khopenapi.dll", "exists": false},
      {"source": "default", "path": "C:\\Kiwoom\\OpenAPI\\khopenapi.dll", "exists": false},
      {"source": "default", "path": "C:\\OpenAPI-W\\khopenapi.dll", "exists": false},
      {"source": "ActiveX ProgID", "path": "HKEY_CLASSES_ROOT\\KHOPENAPI.KHOpenAPICtrl.1", "exists": true},
      {"source": "OPENAPI_PATH", "path": "C:/OpenAPI", "exists": true}
    ],
    "live_connect_attempted": false,
    "order_or_exit_path_changed": false
  }
  ```
- 선행: T01, T02, T03 commit 완료

### T05. Phase H plan §B LH4 의미 명확화

- 목표: LH4 invariant 정의를 "khopenapi.dll 파일 부재 시 거부"에서 "**KHOPENAPI sentinel (ProgID 등록 OR OPENAPI_PATH 디렉터리 OR legacy DLL) 전부 부재 시 거부**"로 확장
- 변경 파일: `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (수정)
- 변경 의도:
  - 본 plan은 Phase H plan §K.7 freeze 정책에 의해 amend가 원칙적으로 금지되지만, **freeze 정책 §K.7 자체에 "오탈자/포맷 정정 commit 허용" 예외 조항**이 있음 (Phase A plan §K.7과 동일 패턴)
  - LH4 의미 명확화는 의미 변경이 아니라 **원래 의도된 의미를 코드 보강에 맞춰 정확히 표현**하는 것이므로 §K.7 예외에 해당
  - 만약 의미 변경으로 분류된다면, 본 plan을 amend하지 않고 새 phase plan으로 분리 → T05를 별도 plan으로 분기
- 완료 조건: §B LH4 표현이 ProgID + OPENAPI_PATH + legacy DLL 3-source를 명시
- 선행: T01, T02 commit 완료

### T06. `CARRY_FORWARD_REGISTRY` V3K-AUDIT-V2-COMPAT 섹션 추가

- 목표: registry에 본 plan 산출을 V3K-DESIGN-1B / V3K-PHASE-A 패턴으로 등록
- 변경 파일: `docs/CARRY_FORWARD_REGISTRY.md` (수정)
- 변경 의도: Records, Decision, Verification (V01–V08), Next phase, Directive 기재
- 완료 조건:
  ```powershell
  Select-String -Path docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-AUDIT-V2-COMPAT"
  ```
  PASS: 매치 1건
- 선행: T01–T05

---

## D. 검증 단계 V01–V08

| # | 명령 | lane | PASS |
| --- | --- | --- | --- |
| V01 | `python -m py_compile strategy/v3k_kiwoom_dryrun_hook.py scripts/audit_v3k_phase_h_env_check.py scripts/smoke_v3k_phase_h_hook_unit.py` | 양쪽 | exit 0 |
| V02 | `python scripts/smoke_v3k_phase_h_hook_unit.py` | 양쪽 | 3개 sentinel 시나리오 + 기존 unit 모두 PASS |
| V03 | `python scripts/audit_v3k_phase_h_env_check.py --stdout` | **본 PC** | `khopenapi_compatible=true`, candidate 6건, ProgID + OPENAPI_PATH 모두 `exists=true` |
| V04 | `python scripts/audit_v3k_phase_h_env_check.py --stdout` | **키움 미설치 가상 환경 또는 mock** | `khopenapi_compatible=false` (기존 audit 동작 보존) |
| V05 | `python scripts/audit_v3k_phase_h_gate4_blocked_environment.py` | 본 PC 환경 변경 전 | `khopenapi_compatible=true`이 되어 본 audit는 의도된 "blocked-env audit가 더 이상 적용 불가"라고 보고. **이 audit의 의미가 바뀜** → V05도 별도 plan에서 다룰 수도 있음. 본 plan에서는 단순 PASS 또는 명시적 SKIP |
| V06 | `git diff cd6f5bd2..HEAD --name-only -- trade/ utility/ Kiwoom_OpenAPI/ KiwoomOpenAPI/ receiver/ trader/` | 양쪽 | 0건 (Kiwoom runtime 무변경) |
| V07 | `Select-String -Path docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-AUDIT-V2-COMPAT"` | 양쪽 | 매치 1건 |
| V08 | `python scripts/verify_release_sync.py` | 양쪽 | "release sync preflight passed" |

---

## E. 위험 매트릭스 R1–R8

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지, 차단액션) |
| --- | --- | --- | --- | --- |
| R1 | LH1 위반 (주문/청산 경로 변경) | 치명 | 매우 낮음 | (`trade/` 변경, V06 audit, commit reject) |
| R2 | ProgID 검사가 다른 ProgID와 충돌 | 중간 | 낮음 | (정확한 ProgID 문자열 사용, smoke 시나리오 1) |
| R3 | `OPENAPI_PATH` import 실패 (`utility.setting_base` 없는 환경) | 중간 | 낮음 | (try/except로 None 반환, smoke 시나리오 3) |
| R4 | sentinel 3종 중 1종만 존재해 false-positive | 중간 | 낮음 | (LA1이 "하나 이상"이라 의도된 동작. Phase H live dry-run 시 실패 시 rollback) |
| R5 | Phase H plan §K.7 freeze 정책 위반 | 높음 | 낮음 | (T05를 별도 plan으로 분기 옵션 보유) |
| R6 | gate4_blocked_environment audit의 의미 변경 (V05 우려) | 높음 | 중간 | (별도 plan에서 audit name/로직 정정 검토) |
| R7 | non-Windows 환경에서 winreg import 실패 | 낮음 | 중간 | (try/except로 ProgID False 반환, 기능 영향 없음) |
| R8 | LS 직접 의존 신규 (L7 위반) | 치명 | 매우 낮음 | (LS marker grep, 본 plan은 winreg만 추가) |

---

## F. Rollback

### F.1 hook/audit 보강 후 본 PC에서 의도치 않게 compatible로 잡힘

```powershell
# 1) rollback flag로 hook 자체 OFF
$env:V3K_PHASE_H_DISABLE = "1"
# 2) T01-T03 commit revert
git -C C:/System_Trading/STOM/STOM_V.wt-dev revert <commit-sha> --no-edit
# 3) audit env_check 재실행해 기존 BLOCKED 상태 복원 확인
python scripts/audit_v3k_phase_h_env_check.py --stdout
```

### F.2 ProgID 검사가 false-positive 발생 (예: 손상된 레지스트리 entry)

```powershell
# 1) hook의 _active_x_progid_registered 임시 비활성화
# 2) sentinel 검사 결과를 OPENAPI_PATH 디렉터리만으로 좁힘
# 3) 재실행 후 동작 확인
```

### F.3 Phase H plan §K.7 freeze 정책 위반 판정

```powershell
# 1) T05를 본 plan에서 제거 (Phase H plan 본문 수정 취소)
# 2) 별도 phase plan(예: 2026-05-XX_v3k_phase_h_lh4_clarification_plan.md)으로 분리
# 3) 본 plan은 hook/audit 코드 + registry 등록만 유지
```

---

## G. 산출물

### G.1 Commit 포함 (6건)

| # | 분류 | 경로 |
| ---: | --- | --- |
| 1 | 수정 hook | `strategy/v3k_kiwoom_dryrun_hook.py` (ActiveX ProgID + OPENAPI_PATH sentinel 추가) |
| 2 | 수정 audit | `scripts/audit_v3k_phase_h_env_check.py` (candidate 표 확장) |
| 3 | 수정 smoke | `scripts/smoke_v3k_phase_h_hook_unit.py` (3 시나리오 추가) |
| 4 | 수정 docs | `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (§B LH4 명확화) |
| 5 | 수정 docs | `docs/CARRY_FORWARD_REGISTRY.md` (V3K-AUDIT-V2-COMPAT 섹션) |
| 6 | 신규 docs | `docs/update_log/<YYYY-MM-DD>_v3k_audit_v2_compat_kiwoom_sentinel.md` (실행 결과 보고서) |

### G.2 Ephemeral

| # | 경로 |
| --- | --- |
| E1 | `.omx/reports/v3k-phase-h-env-<utc>.json` (T04 결과, ignored artifact) |

---

## H. Commit message 한국어 sample

### H.1 commit 1+2+3 — hook/audit/smoke 보강

```text
V3K KHOPENAPI sentinel을 V2 ActiveX 방식과 정합하도록 보강한다

- `resolve_khopenapi_path()`에 ActiveX ProgID와 OPENAPI_PATH 디렉터리 검사를 추가한다.
- `audit_v3k_phase_h_env_check.py`의 candidate 표를 6건으로 확장한다.
- LH4 무환경 거부 동작은 그대로 유지하며 unit smoke 3 시나리오를 추가한다.
```

### H.2 commit 4 — Phase H plan §B LH4 명확화

```text
V3K Phase H plan LH4 invariant를 V2 ActiveX 방식 정합으로 명확화한다

- LH4를 "KHOPENAPI 환경 부재 시 거부"에서 "ProgID/OPENAPI_PATH/legacy DLL 전부 부재 시 거부"로 확장 표현한다.
- 의미 변경이 아니라 코드 보강에 맞춘 정확한 표현이며 §K.7 freeze 예외에 해당한다.
- Phase H 본문(§C/§D/§E)는 변경하지 않는다.
```

### H.3 commit 5 — registry V3K-AUDIT-V2-COMPAT

```text
V3K-AUDIT-V2-COMPAT 섹션을 carry-forward registry에 등록한다

- ActiveX ProgID + OPENAPI_PATH sentinel 도입을 records/decision/verification으로 기재한다.
- Phase H Gate4 BLOCKED 자연 해제 조건을 next phase 항목에 명시한다.
- V01–V08 검증 명령을 verification 절에 포함한다.
```

---

## I. ADR 요지

- **Decision**: V3K audit의 KHOPENAPI sentinel 검사를 ActiveX ProgID + `OPENAPI_PATH` 디렉터리 + legacy DLL 3-source로 확장 (OR 조건). V2가 실제로 사용하는 ProgID 방식을 audit가 인식하도록 보강
- **Drivers**:
  1. V3K 미션의 "Kiwoom API/runtime 유지" 조항을 audit 수준에서도 정확 표현
  2. Gate4 false-negative 해소로 Gate5·Gate6 unlock 가능
  3. V2 키움 사용 코드(`autologin.py:24`)와 audit 가정 일치
- **Alternatives considered**:
  - 옵션 B (`V3K_KHOPENAPI_DLL` env 임시 우회) → semantic 부적합, 가짜 sentinel
  - 옵션 C (audit 미수정) → Gate4 영구 BLOCKED, 미션 closure 불가
- **Why chosen**: 옵션 A가 V2 호환 미션과 정확히 일치하는 유일안. 발견 문서(`cdd77093`) §5 분석 참조
- **Consequences**:
  - 긍정: Gate4 BLOCKED 자연 해제, F6 #5 항목 S1 → S3 전이 가능, V3K closure path 회복
  - 부정: `gate4_blocked_environment` audit의 의미가 바뀜 (V05 우려) → 별도 plan에서 정정 검토
- **Follow-ups**:
  - F1: 본 plan 완료 후 Phase H plan §C T04–T05 실행 가능 (KHOPENAPI 환경 dry-run)
  - F2: `gate4_blocked_environment` audit이 더 이상 적용 불가 상태가 되면 audit name/logic 정정 별도 plan
  - F3: 다른 환경(non-Windows, 키움 미설치)에서 winreg import 실패 시 동작 검증 (R7)

---

## J. 핵심 설계 질문

### Q1. ActiveX ProgID 검사를 어떻게 구현하나?
A. `winreg.OpenKey(HKEY_CLASSES_ROOT, "KHOPENAPI.KHOpenAPICtrl.1")` 시도. 성공 시 True, `OSError` 또는 `WindowsError` 시 False. non-Windows에서는 `winreg` import 자체 실패 → False.

### Q2. `OPENAPI_PATH` import 실패 시?
A. `try/except ImportError`로 None 반환. R3 위험으로 분류.

### Q3. 3 sentinel이 모두 존재해도 됨?
A. 가능. LA1은 "**하나 이상**" 조건이라 OR 조건. 셋 다 존재해도 LA3(부재 시 거부) 정합 유지.

### Q4. Phase H plan §K.7 freeze 정책 위반 여부?
A. T05의 LH4 의미 명확화는 §K.7 "오탈자/포맷 정정 commit 허용"에 해당. 만약 의미 변경으로 분류되면 T05를 별도 plan으로 분기 (R5 / F.3 rollback). 본 plan 작성 시점에서는 명확화로 분류.

### Q5. ralplan 합의 의무?
A. 본 plan은 sentinel 검사 확장이라는 단일 변경이므로 short deliberation ralplan 1회 권장. F1 cutover / F3 Phase F / F4 Phase G의 `--deliberate` ralplan과 달리 본 plan은 위험도 중간이므로 short mode 충분.

---

## K. 다음 단계 전환 지침

### K.1 완료 조건

- T01–T06 모두 commit
- V01–V08 모두 PASS
- 본 PC에서 `audit_v3k_phase_h_env_check.py --stdout` 결과 `khopenapi_compatible=true`
- F6 산식 본 plan은 S1 → S3 전이 (audit 수정 + 실 환경 확인 후)

### K.2 본 plan 완료 후 진행 가능한 작업

- **Phase H plan §C T04–T05 (KHOPENAPI 환경 dry-run)**: Gate4 BLOCKED 해제 후 실제 H-2 sub-phase 진행
- **`gate4_blocked_environment` audit 정정**: 별도 plan으로 분리
- **Gate5 F1 cutover unlock 가능성 검토**: Phase H 본체 완료 후

### K.3 본 plan freeze 정책

본 plan 완료 commit 후 freeze. 추가 sentinel(예: 다른 broker SDK) 추가가 필요하면 별도 plan.

### K.4 ralplan 합의 의무

본 plan **실행 전** `/oh-my-claudecode:ralplan` (short deliberation) 재합의 필수. Planner → Architect → Critic 한 라운드. ITERATE 발생 시 v2로 보강.

---

## L. 관련 문서 (Phase A plan §K.5 + F2 §3.3 의무 인용)

- `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (trigger 발견 문서, `cdd77093`)
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (Phase H plan §B LH4)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (audit §6.2 #5)
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan §0 미션 + §K)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (F2 letter convention)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (F6 산식)
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` (F7 closure)
- `docs/update_log/2026-05-14_v3k_midpoint_feature_coverage_and_custom_audit.md` (중간점검, Gate4 BLOCKED 명시)
- `strategy/v3k_kiwoom_dryrun_hook.py` (수정 대상 1)
- `scripts/audit_v3k_phase_h_env_check.py` (수정 대상 2)
- `scripts/smoke_v3k_phase_h_hook_unit.py` (수정 대상 3)
- `utility/setting_base.py:2` (`OPENAPI_PATH` 정의)
- `trade/stock_korea/login_kiwoom/autologin.py:24` (V2 실제 사용 증거)
- `docs/CARRY_FORWARD_REGISTRY.md` (V3K-AUDIT-V2-COMPAT 등록 위치)
