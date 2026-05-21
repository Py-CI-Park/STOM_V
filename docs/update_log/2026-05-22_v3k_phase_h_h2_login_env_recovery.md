# V3K Phase H H-2 A-lane 진입 차단 해소 보고서 — 키움 OpenAPI 로그인 환경 복구

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `4e3d3d70` (`STOM_Version_2U_C`) |
| 관련 plan | `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md` |
| 관련 commit | `4e3d3d70` (P-lane closure) |
| 코드 변경 | 0건 (운영 환경 복구만, STOM/V3K 코드 무변경) |
| Phase letter | 메타 (환경 복구 보고) |

---

## §0. TL;DR

```text
V3K 페이지 1(Phase H H-2 A-lane) 진입 직전 stom.bat 로그인이 5월 20일부터 실패.
진짜 원인은 KOA Studio가 모의투자 모드로 설정되어 있었던 것.
KOA Studio에서 모의투자 해제 + 업데이트 완료 후 stom.bat 정상 로그인 회복.
2026-05-22 06:48:50 "OpenAPI 로그인 완료" 확인.
V3K 자산은 4e3d3d70까지 그대로 보존. A-lane runner 진입 가능 상태.
```

---

## §1. 배경

`docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md`의 P-lane이 commit `4e3d3d70`으로 종결되었고, 다음 작업은 A-lane(Phase H H-2 actual) 진입이었다. A-lane 진입 trigger는 다음 4건:

1. 사용자 명시 phrase `I approve phase-h-h2-await-user-approval only` (2026-05-20 발급 완료)
2. `V3K_PHASE_H_USER_ACK=1` durable env 발급
3. 본 PC KHOPENAPI GUI 활성 + 사용자 직접 로그인
4. 24h monitoring baseline 시각

그러나 3번을 검증하기 위해 stom.bat을 띄웠을 때 키움 로그인이 실패했고, 그 후 약 30시간 동안 원인 진단 + 환경 복구 작업이 진행되었다. 본 문서는 그 trail을 정본화한다.

---

## §2. 증상 Timeline

| 시각 | 환경 | 결과 |
| --- | --- | --- |
| 2026-05-19 17:30 | V2 `setting.db` wt-dev로 복사 후 stom.bat | ✅ 정상 로그인 (`stock_min.db`/`code_info.db` 갱신 흔적) |
| 2026-05-20 12:22 | stom.bat 재실행 | ❌ "버전 업그레이드 실패" + `manuallogin.py:77` `pywintypes.error (1400)` |
| 2026-05-20 14:29 | stom.bat 재실행 | ❌ 동일 traceback |
| 2026-05-20 늦은 시간 | 키움 OpenAPI 재설치 시도 1회차 | `C:\OpenAPI` 폴더 사라짐, CLSID 등록 사라짐 |
| 2026-05-21 07:21 | `OpenAPISetup (2).exe` 새로 다운로드 + 재설치 | `C:\OpenAPI` 회복 (93 파일), OCX 등록은 미완 |
| 2026-05-21 (Claude session) | `regsvr32 //s khopenapi.ocx` 실행 | `WOW6432Node\CLSID\{A1574A0D-...}` InprocServer32 등록 완료 |
| 2026-05-21 22:07 | stom.bat 재실행 | ❌ 동일 실패 + `[GetPCIdentity] VER 3.2.0.0  build 2015.8.12` 등장 |
| 2026-05-22 (사용자) | KOA Studio에서 **모의투자 해제** + 업데이트 + 실거래 로그인 끝까지 진행 | ✅ KOA Studio 자체 정상 |
| 2026-05-22 06:46~06:48 | stom.bat 재실행 | ✅ **정상 로그인** ("업데이트 확인 완료" → "OpenAPI 로그인 완료") |

### §2.1 정상 로그인 evidence (사용자 cmd 출력 인용)

```
2026-05-22 06:46:34 키움매니저 실행 인터프리터 선택 [C:\Python\32\Python3119\python32.EXE]
2026-05-22 06:46:46 로그인창 열림 대기 중 ...
2026-05-22 06:46:54 아이디 및 패스워드 입력 대기 중 ...
2026-05-22 06:47:04 아이디 및 패스워드 입력 완료
2026-05-22 06:47:04 업데이트 및 버전업 확인 중 ...
2026-05-22 06:47:05 업데이트 확인 완료         ← 어제까지 막혔던 단계 통과
2026-05-22 06:48:50 시스템 명령 실행 알림 - OpenAPI 로그인 완료
2026-05-22 06:48:52 [[84, '장초초단타'], [85, '감시종목']]
2026-05-22 06:48:54 시스템 명령 실행 알림 - 실시간 등록 완료
```

22 그룹 × 100 종목 실시간 알림 등록까지 완료 = STOM Receiver/Trader/Agent 전체 흐름 정상.

---

## §3. 검토한 가설들 (대부분 빗나감)

진단 과정에서 다음 가설을 차례로 검토했고, 각각이 어떻게 빗나갔는지 기록한다. 향후 같은 증상 만나는 경우의 fast-path를 위해 남겨둔다.

| # | 가설 | 검증 | 판정 |
| ---: | --- | --- | --- |
| 1 | STOM 또는 OCX 점유 프로세스 잔존 | `tasklist`에 STOM/python 0개 | ❌ 빗나감 |
| 2 | dict_set 토글 미설정 (`주식에이전트=0`) | `setting.db` 복사로 해소됨 (05-19 17:30 정상) | 보조 원인이었지만 본 원인 아님 |
| 3 | 좀비 python.exe가 OCX 점유 | python 프로세스는 별도 ML 학습 (`Kronos` finetune)으로 STOM 무관 | ❌ 빗나감 |
| 4 | `opstarter.exe` 손상 | 디지털 서명 유효 (Kiwoom Securities Co. Ltd, 2028-12-26까지) | ❌ 빗나감 |
| 5 | OCX 자체 ActiveX 등록 손상 | 재설치 후 `regsvr32`로 보강 → WOW6432Node\CLSID 등록 정상 | 부분 원인 (재설치 단계의 admin 권한 부족) |
| 6 | 키움 OCX 자체 버전 업그레이드 사이클 | `opversionup`이 zombie로 멈춤 | 증상이지 원인 아님 |
| 7 | STOM `manual_login`이 새 OCX dialog ID와 호환 안 됨 | 정상 로그인 후 동일 코드가 작동 | ❌ 빗나감 (다만 모의투자 dialog 흐름 분기는 `manuallogin.py:65-69` 주석에 시사돼 있음) |
| **8** | **KOA Studio 모의투자 모드** | **모의투자 해제 후 정상 로그인** | ✅ **정답** |

---

## §4. 진짜 원인 — KOA Studio 모의투자 모드

### §4.1 메커니즘

KOA Studio (`KOAStudioSA.exe`)는 키움 OpenAPI의 통합 IDE이고 OCX 환경의 source-of-truth로 동작한다. KOA Studio에서 **모의투자 모드**(Mock Trading)를 활성화하면 다음이 발생한다:

1. KOA Studio가 키움 모의투자 서버로 접속 시도
2. 모의투자 서버는 별도의 OCX 등록 정보를 요구
3. 모의투자 모드의 로그인 dialog는 실거래 모드와 흐름이 다름 (추가 인증 단계, dialog control ID 변경 가능성)
4. STOM은 실거래 모드를 가정하고 작성되어 있어 `OpenapiLoginWait`의 `find_window('Open API login')` 또는 `manual_login`의 `GetDlgItem(0x3E8/0x3E9/0x3EA)`이 모의투자 dialog의 다른 ID와 매핑되지 않아 invalid handle 반환

### §4.2 manuallogin.py가 남긴 단서

`trade/stock_korea/login_kiwoom/manuallogin.py` 본문 64~69행:

```python
""" 모의서버 접속용
if win32gui.IsWindowEnabled(win32gui.GetDlgItem(hwnd, 0x3EA)):
    click_button(win32gui.GetDlgItem(hwnd, 0x3ED))
if win32gui.IsWindowEnabled(win32gui.GetDlgItem(hwnd, 0x3EA)):
    click_button(win32gui.GetDlgItem(hwnd, 0x3ED))
"""
```

주석으로 남겨진 이 4행은 **모의투자 모드 접속 시 별도 dialog 처리가 필요**함을 시사한다. STOM 정규 운영은 실거래 모드만 지원하고 모의투자 분기는 주석화되어 있어, KOA Studio가 모의투자 모드일 때 OCX 환경이 실거래 dialog 패턴과 다르게 작동하면 `manual_login`이 race condition을 만난다.

### §4.3 왜 5월 19일에는 됐는가

추정: 5월 19일 시점에는 KOA Studio가 실거래 모드였거나 또는 키움 서버 측 세션이 실거래로 캐시되어 있었다. 5월 20일경 키움 서버가 어떤 정책 변경 또는 사용자 모의투자 토글 변경 시점에 모의투자 모드가 활성화되었고, 그 이후 모든 로그인이 모의투자 dialog 흐름으로 진입해 STOM이 실패. 본 PC 사용자 측 진단으로는 그 정확한 전환 시점은 추적 불가하나, 결과적으로 KOA Studio에서 모의투자 해제 + 업데이트 통과 시 즉시 해소되었다.

---

## §5. 해결 절차 (재현 가능)

향후 같은 증상 만났을 때의 fast-path:

1. **KOA Studio (`C:\OpenAPI\KOAStudioSA.exe`) 관리자 권한 실행**
2. KOA Studio UI에서 **모의투자 체크박스 해제** (좌측 또는 설정 메뉴)
3. KOA Studio에서 자체 로그인 시도 → 키움 ID/PW/인증서비밀번호 입력
4. "**버전 처리 중 ...**" → "**버전 업데이트 완료**" → "**로그인 성공**" 끝까지 진행 (1~5분, 중단 금지)
5. KOA Studio 종료
6. STOM 또는 V3K runner 실행 → 정상 로그인 회복

### §5.1 부수적으로 진행된 환경 보강 (필수 아님)

진단 과정에서 다음 작업도 함께 진행되었고 환경 안정성에 기여했다:

- 키움 OpenAPI 재설치 (`OpenAPISetup (2).exe`, 2026-05-21 07:21 다운로드)
- `regsvr32 //s C:\OpenAPI\khopenapi.ocx` 실행으로 ActiveX 등록 보강 (Claude session에서)
- `WOW6432Node\CLSID\{A1574A0D-6BFA-4BD7-9020-DED88711818D}\InprocServer32` 등록 확인

이들은 모의투자 해제와 독립적 단계이고 단독으로는 해소되지 않았으나, **모의투자 해제와 결합되면서 클린 상태**가 되었다.

---

## §6. 학습 포인트 (운영 매뉴얼 amend 의무)

향후 STOM 운영 매뉴얼 amend 또는 trouble-shooting 가이드 추가 시 다음 점을 반영한다:

1. **stom.bat 첫 실행 실패 시 가장 먼저 KOA Studio의 모의투자 토글을 확인**
2. **manuallogin.py의 모의서버 주석 4행**은 미완성 dead code가 아니라 실거래 모드와 모의투자 모드의 dialog 흐름 차이를 시사하는 단서로 보존
3. **STOM은 실거래 모드 가정**으로 작성되어 있으며, 모의투자 운영이 필요할 경우 `manuallogin.py` 모의투자 분기 활성화 + Phase F LF2 패턴의 feature flag 도입 필요
4. **키움 OpenAPI 재설치만으로는 해소되지 않음** — KOA Studio의 모의/실거래 모드까지 점검 의무
5. **`opversionup.exe`가 zombie 상태**가 되어도 그 자체가 원인이 아니라 모의투자 모드의 부수 증상일 수 있음

---

## §7. V3K 거버넌스 영향

### §7.1 코드 변경

```text
trade/         : 무변경 (verify_1a로 강제 검증)
utility/       : 무변경
Kiwoom_OpenAPI/: 무변경
receiver/      : 무변경
```

본 환경 복구 작업은 V3K plan §C T05/T06 task 외부의 **외부 SDK 환경 복구**이며 V3K 보존 invariant L1~L9, LH1~LH5 전부 보존.

### §7.2 P-lane 자산 보존

| Asset | 상태 |
| --- | --- |
| 2U_C HEAD `4e3d3d70` | ✅ 보존 |
| T05 runner `scripts/run_v3k_phase_h_dryrun.py` | ✅ 보존 |
| T06 smoke `scripts/smoke_v3k_phase_h_post_health.py` | ✅ 보존 |
| evidence `docs/evidence/v3k-phase-h-h2-runner-prep-9024e3b9.json` | ✅ 보존 |
| canonical phrase `I approve phase-h-h2-await-user-approval only` | ✅ 발급 기록 보존 (본 문서 §0 / §1 인용) |

### §7.3 A-lane 진입 조건 재점검 (2026-05-22 시점)

| 조건 | 상태 |
| --- | --- |
| 사용자 명시 phrase 발급 | ✅ 2026-05-20 발급 완료 |
| `V3K_PHASE_H_USER_ACK=1` durable env 발급 | ⏸ A-lane 실행 시점에 발급 |
| 본 PC KHOPENAPI GUI 활성 | ✅ 본 문서 §2.1 evidence로 확인 |
| 사용자 직접 로그인 수행 능력 | ✅ 본 문서 §2.1 evidence로 확인 |
| 24h monitoring baseline 시각 | ⏸ A-lane 실행 직후 기록 |

→ **A-lane 진입 가능 상태**.

---

## §8. Scope guard

| # | 항목 | 통과 조건 |
| ---: | --- | --- |
| 1 | kiwoom_runtime_mutated | False ✅ (trade/, utility/, Kiwoom_OpenAPI/ 무변경) |
| 2 | ls_direct_dependency_added | False ✅ |
| 3 | operating_database_write_attempted | False ✅ (`_database/`, `_database_v3k_shadow/` 무변경) |
| 4 | live_connect_attempted | True ✅ (stom.bat 정상 로그인 발생, 단 V3K A-lane은 별개) |
| 5 | user_ack_emitted_to_runtime | False ✅ (V3K_PHASE_H_USER_ACK env 미발급) |
| 6 | monitoring_24h_or_more_collected | False (A-lane 실행 후 시작) |
| 7 | sidecar_toggle_changed | False ✅ (`_v3k_sidecar/` 무변경) |

본 환경 복구는 STOM 정규 운영의 live connect/login은 사용했지만 V3K 측 USER_ACK env / sidecar toggle / actual gate 진입은 0건이다.

---

## §9. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

본 commit은 문서 1건 + registry 1 섹션만 추가하므로 모든 audit 통과 예정.

---

## §10. 다음 인계 — A-lane 진입

본 문서가 commit된 직후, A-lane 진입은 다음 절차로 수행 가능:

```powershell
# 사용자 본 PC, 관리자 PowerShell
cd C:\System_Trading\STOM\STOM_V.wt-dev

# 1) 프로세스 정리 확인 (STOM 종료 상태)
Get-Process | Where-Object {$_.ProcessName -match "stom|opstart|KOA"} | Format-Table

# 2) USER_ACK env 발급 (A-lane 진입 trigger)
$env:V3K_PHASE_H_USER_ACK='1'

# 3) 32-bit Python으로 A-lane runner 실행
& "C:\Python\32\Python3119\python32.EXE" scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only
```

이후 흐름:

```
1. G1~G5 가드 통과 (silent)
2. Open API login 창 팝업 (이번엔 실거래 모드라 정상)
3. 사용자 직접 ID/PW/인증서비밀번호 입력 → 로그인
4. V3KKiwoomDryrunHook.on_login → diagnostic 1회
5. 30초 timeout → CommTerminate() → disconnect
6. .omx/reports/v3k-phase-h-dryrun-<utc>.json archive 생성
```

archive 생성 후 T06 health smoke:

```powershell
& "C:\Python\32\Python3119\python32.EXE" scripts/smoke_v3k_phase_h_post_health.py
```

기대: `[PASS] Phase H H-2 post-health smoke clean ...`

이 4건 (runner stdout / archive / smoke / login GUI 결과)을 공유하면 A-lane closure commit 진행.

---

## §11. 관련 문서

- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (본체 plan)
- `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` (지도)
- `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md` (P-lane plan)
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` (P-lane/A-lane 정책)
- `docs/evidence/v3k-phase-h-h2-runner-prep-9024e3b9.json` (P-lane evidence)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-PHASE-H-H2-LOGIN-ENV-RECOVERY` 섹션)
