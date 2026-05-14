# V3K Gate4 BLOCKED 진짜 원인 — V2 키움 사용 방식과의 audit 불일치 (false-negative)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-14 KST |
| 발견 commit | `41bf6565` 중간점검 검토 중 |
| 영향 받는 코드 | `strategy/v3k_kiwoom_dryrun_hook.py`, `scripts/audit_v3k_phase_h_env_check.py` |
| 영향 받는 plan | `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (Phase H §B LH4) |
| Phase A plan §K.7 freeze 영향 | 없음 (별도 발견 문서) |

---

## 0. TL;DR

```text
Gate4 "KHOPENAPI sentinel 부재"는 환경이 진짜로 없어서가 아니라,
V3K audit가 V2의 실제 키움 사용 방식(ActiveX ProgID + C:/OpenAPI 디렉터리)을 검사하지 않고
존재할 수 없는 파일(khopenapi.dll)을 잘못된 4개 경로에서 찾고 있었기 때문이다.

증거:
- C:/OpenAPI 디렉터리 존재 (53KB 키움 파일 포함)
- HKEY_CLASSES_ROOT\KHOPENAPI.KHOpenAPICtrl.1 레지스트리 등록
- utility/setting_base.py:2 OPENAPI_PATH='C:/OpenAPI'
- trade/stock_korea/login_kiwoom/autologin.py:24 QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
- C: 전체 depth 10 재귀 검색에서 khopenapi.dll 0건 (V2도 이 파일을 쓰지 않음)

결론: Gate4 BLOCKED는 false-negative. audit 보강이 V2 호환 미션과 정합하는 fix.
```

---

## 1. 발견 경위

`41bf6565` 중간점검 문서를 검토하면서 사용자가 다음을 지적:
> "이 컴퓨터에서는 kiwoom api를 사용하고 있어서 필요한 것은 다 설치되어있을 것입니다. 무엇이 없다고 생각하나요. 2U_C 과거에 로그인도 하고 했습니다."

이 발언이 사실이라면 `audit_v3k_phase_h_env_check.py`의 `khopenapi_compatible=false`는 오판이다. 본 문서는 그 검증 결과를 정본화한다.

---

## 2. 정량 증거 5건

### 2.1 `C:\OpenAPI\` 디렉터리 — 존재 + 키움 OpenAPI+ 설치 흔적

PowerShell `Get-ChildItem 'C:\OpenAPI' -Recurse -Depth 2` 실행 결과 (53KB 파일 목록):

```text
C:\OpenAPI\astxsdk        (디렉터리)
C:\OpenAPI\data           (디렉터리)
C:\OpenAPI\system         (디렉터리, Autologin.dat 위치)
C:\OpenAPI\image          (디렉터리)
C:\OpenAPI\log            (디렉터리)
C:\OpenAPI\temp           (디렉터리)
C:\OpenAPI\aossdk.dll
C:\OpenAPI\aossdkrad.dll
C:\OpenAPI\astxmanager.dll
C:\OpenAPI\inicore_v2.3.32.dll
C:\OpenAPI\inicore_v2.3.42.dll
C:\OpenAPI\absolutedown.ini
C:\OpenAPI\apiinitrsc.lst
C:\OpenAPI\apiotrsc.lst
C:\OpenAPI\asplnchr.exe
C:\OpenAPI\default.lic
... (다수 키움 OpenAPI+ 표준 파일)
```

이건 명백한 키움 OpenAPI+ 설치 디렉터리다.

### 2.2 ActiveX ProgID 레지스트리 — 정상 등록

```text
HKEY_CLASSES_ROOT\KHOPENAPI.KHOpenAPICtrl.1\CLSID
(default) = {A1574A0D-6BFA-4BD7-9020-DED88711818D}
```

즉 `QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')`이 이 PC에서 정상 작동 가능한 상태.

### 2.3 STOM 코드의 명시적 키움 경로 정의

`utility/setting_base.py:2`:

```python
OPENAPI_PATH = 'C:/OpenAPI'
```

V2 시절부터 박혀 있는 상수다. 이게 STOM의 진짜 키움 sentinel.

### 2.4 V2 시절부터의 실제 로그인 코드

`trade/stock_korea/login_kiwoom/autologin.py:24`:

```python
self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
self.ocx.OnEventConnect.connect(self.OnEventConnect)
self.CommConnect()
...
autologin_dat = f'{OPENAPI_PATH}/system/Autologin.dat'
```

- ProgID 기반 OCX 로딩 (파일 직접 import 없음)
- `Autologin.dat`는 `C:/OpenAPI/system/Autologin.dat`로 동적 해석
- V2 시절부터 변경 없이 유지되어 온 코드

### 2.5 C: 전체 depth 10 재귀 검색 — `khopenapi.dll` 0건

```powershell
Get-ChildItem -Path 'C:\' -Filter 'khopenapi.dll' -Recurse -Depth 10
```

결과: **0건**. 즉 V2도 이 파일을 쓰지 않으며, 키움 OpenAPI+가 그런 이름의 단일 dll로 배포된 적이 없다.

---

## 3. audit가 가진 4개 잘못된 가정

| # | audit 가정 | 실제 | 결과 |
| ---: | --- | --- | --- |
| 1 | 키움 sentinel = `khopenapi.dll` 파일 | 키움은 OCX(ActiveX) + `inicore_*.dll` 조합 | 영원히 False |
| 2 | 경로 = 하드코딩된 4곳 | STOM은 `setting_base.OPENAPI_PATH='C:/OpenAPI'` 사용 | 영원히 False |
| 3 | sentinel = 파일 존재 | 실제는 **레지스트리 ProgID 등록** + 설치 디렉터리 | 검사 자체 누락 |
| 4 | STOM 코드를 안 봄 | STOM은 이미 `KHOPENAPI.KHOpenAPICtrl.1` ProgID를 직접 사용 (`autologin.py:24`) | 가장 신뢰할 수 있는 단서 무시 |

---

## 4. V2 실제 방식 ↔ audit 가정 매핑

| 측면 | V2 실제 방식 | audit 가정 |
| --- | --- | --- |
| 파일 형태 | ActiveX OCX + `inicore_*.dll` | 단일 `khopenapi.dll` |
| sentinel | 레지스트리 ProgID 등록 + 디렉터리 존재 | 특정 경로 파일 존재 |
| 사용 경로 | `OPENAPI_PATH='C:/OpenAPI'` 동적 | 하드코딩된 4개 |
| 로딩 방식 | `QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')` | (파일 존재만 확인, 로딩 미검증) |
| Autologin | `{OPENAPI_PATH}/system/Autologin.dat` | 모름 |

---

## 5. 옵션 분석 결과

| 옵션 | V2 방식 일치 | 미션 정합 |
| --- | --- | --- |
| **A** (ActiveX ProgID + `OPENAPI_PATH` 디렉터리 검사) | **정확히 일치** | "V2 Kiwoom 유지" 미션과 완전 정합 |
| B (`V3K_KHOPENAPI_DLL`을 `inicore_*.dll`로 우회) | V2 코드 미사용 파일 | semantic 부적합, 가짜 sentinel |
| C (audit 미수정) | V2는 작동, V3K audit만 작동 안 함 | Gate4 영원히 BLOCKED, 미션 closure 불가 |

→ **옵션 A가 V2 호환 미션과 정확히 일치하는 유일한 선택**.

---

## 6. 영향 분석

### 6.1 Gate4가 false-negative이면 도미노 효과

| 영향 | 현재 |
| --- | --- |
| Gate4 BLOCKED | 실제 환경 있는데 차단 |
| Gate5 (F1 DB cutover) | Gate4 의존으로 잠김 |
| Gate6 (live order/exit) | Gate5 의존으로 잠김 |
| audit §6.2 #5 (live Kiwoom dry-run) | S1 25% 영구 고정 |
| V3K 미션 closure | 영원히 불가능 |

→ audit 보강 없이는 V3K 미션의 절반이 sentinel 오판 하나에 잠겨 있는 상태.

### 6.2 false-negative 자체의 미래 위험

audit가 다른 PC(키움 미설치)에서 실행될 때는 정상 차단해야 하므로, 옵션 A 보강 시 다음을 모두 만족해야 한다:

1. ActiveX ProgID 부재 시 → BLOCKED (현재 PC 외 환경에서 보호)
2. `OPENAPI_PATH` 디렉터리 부재 시 → BLOCKED
3. 둘 다 존재 시 → COMPATIBLE
4. 한쪽만 존재 시 → BLOCKED 또는 WARNING (보수적)

이는 옵션 A plan에서 정본화한다.

---

## 7. 사용자 발언 정합성

| 사용자 발언 | 검증 결과 |
| --- | --- |
| "이 컴퓨터에서는 kiwoom api를 사용하고 있다" | TRUE (C:/OpenAPI + 레지스트리 + setting_base 모두 정합) |
| "필요한 것은 다 설치되어있을 것" | TRUE (키움 OpenAPI+ 표준 설치 흔적 완비) |
| "2U_C에서 과거에 로그인도 했다" | TRUE (autologin.py가 ProgID + Autologin.dat로 정상 작동 가능한 환경) |

3건 모두 정합. 사용자 기억과 시스템 상태가 정확히 일치한다.

---

## 8. 차후 조치

본 발견의 직접 조치는 별도 plan 문서 `docs/plans/2026-05-14_v3k_audit_v2_compat_kiwoom_sentinel_plan.md`에서 정본화한다.

핵심 변경 대상:
- `strategy/v3k_kiwoom_dryrun_hook.py` — `resolve_khopenapi_path()` 보강
- `scripts/audit_v3k_phase_h_env_check.py` — `_candidate_rows()` 확장
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` §B LH4 invariant 의미 명확화 (별도 commit, freeze 정책 검토)

---

## 9. 본 문서 freeze 정책

- **freeze 시점**: 본 commit
- **갱신 정책**: 본 문서는 발견 snapshot. 미래에 audit가 보강되거나 추가 증거가 나오면 새 finding 문서를 신설
- **인용 의무**: V2 키움 호환을 다루는 모든 미래 plan은 본 문서 §2 증거 5건을 인용

---

## 10. 관련 문서

- `docs/update_log/2026-05-14_v3k_midpoint_feature_coverage_and_custom_audit.md` (Gate4 차단 상태가 처음 명시된 중간점검)
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (LH4 invariant 정의)
- `strategy/v3k_kiwoom_dryrun_hook.py` (수정 대상 1)
- `scripts/audit_v3k_phase_h_env_check.py` (수정 대상 2)
- `trade/stock_korea/login_kiwoom/autologin.py:24` (V2 실제 사용 증거)
- `utility/setting_base.py:2` (`OPENAPI_PATH` 정의)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 #5)
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (V3K 미션 §0.1)

---

## 11. 검증 명령 (재현 가능)

```powershell
# 디렉터리 존재
Test-Path 'C:\OpenAPI'

# 키움 표준 파일 일부 존재
Test-Path 'C:\OpenAPI\inicore_v2.3.42.dll'

# ActiveX ProgID 등록 확인
Get-ItemProperty 'Registry::HKEY_CLASSES_ROOT\KHOPENAPI.KHOpenAPICtrl.1\CLSID'

# audit가 찾는 파일 부재 재확인
Test-Path 'C:\OpenAPI\khopenapi.dll'
Test-Path 'C:\Kiwoom\OpenAPI\khopenapi.dll'
Test-Path 'C:\OpenAPI-W\khopenapi.dll'

# C: 전체 재귀 검색 (수 분 소요)
Get-ChildItem -Path 'C:\' -Filter 'khopenapi.dll' -Recurse -Depth 10 -ErrorAction SilentlyContinue
```

기대 결과:
- `C:\OpenAPI` 존재 = True
- `C:\OpenAPI\inicore_v2.3.42.dll` 존재 = True
- ProgID CLSID = `{A1574A0D-6BFA-4BD7-9020-DED88711818D}`
- 4개 `khopenapi.dll` 후보 = 모두 False
- depth 10 재귀 검색 = 0건
