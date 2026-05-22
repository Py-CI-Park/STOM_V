# V3.X 흡수 자동화 파이프라인 운영 매뉴얼 (V3U_C E1)

- 작성일: 2026-05-22
- 대상 lane: `STOM_Version_3U_C`
- 핵심 도구: `scripts/v3uc_ingest_pipeline.py`
- 2U_C T-step 패턴 적용 (T01~T05, mock execution + live dry-run)

## 1. 목적

V3 upstream에서 새 버전(V3.19, V3.20 등)이 발표될 때마다 V3U lane으로 흡수하는 흐름을 5단계 T-step 파이프라인으로 자동화한다. 사용자 개입 최소화 + audit 증적 정본화 + dry-run 안전망을 동시 제공.

## 2. T-step 5단계

| T | 단계 | 입력 | 출력 | dry-run 동작 |
|---|---|---|---|---|
| **T01** | upstream merge | `--upstream-ref` (예: `STOM_Version_3`) | merge commit | diff stat만 표시 |
| **T02** | 통합 verifier | T01 결과 | `.omx/logs/v3u/ingest_v3_<version>_verifier.json` (8 stage) | 실 verifier 실행 (read-only) |
| **T03** | audit JSON 정본화 | T01·T02 결과 | `.omc/audits/v3u_ingest_<version>_<date>.json` (schema v2) | 동일 (write) |
| **T04** | 한글 commit | T03 audit path | git commit | echo만 |
| **T05** | origin push | T04 commit | `git push origin` | echo만 |

각 단계 fail-fast — 실패 시 즉시 abort + audit JSON에 fail 기록.

## 3. 사용법

### 사전 조건

- 현재 워크트리는 `wt-3u` (V3U lane)에서 실행
- 현재 branch는 `STOM_Version_3U` (T01이 자동 검증)
- working tree clean (uncommitted 변경 없음)

### dry-run (권장 첫 시도)

```powershell
cd C:/System_Trading/STOM/STOM_V.wt-3u
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_ingest_pipeline.py `
    --version 19 --upstream-ref STOM_Version_3 --dry-run
```

기대 출력:
```
=== V3.19 흡수 파이프라인 (mode=dry-run) ===

[T01] upstream merge: STOM_Version_3 → STOM_Version_3U
  → T01 passed
[T02] integrated verifier (V3U pyd contract + pytest + attr inventory)
  → T02 passed
[T03] audit JSON 정본화 (.omc/audits/v3u_ingest_*)
  → T03 passed (audit: .omc/audits/v3u_ingest_19_<date>.json)
[T04] 한글 commit (audit 증적 + V3 흡수 메시지)
  → T04 passed
[T05] origin push (STOM_Version_3U)
  → T05 passed

[OK] V3.19 흡수 파이프라인 5 T-step 모두 PASS (mode=dry-run)
```

### live 실행 (dry-run PASS 확인 후)

```powershell
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_ingest_pipeline.py `
    --version 19 --upstream-ref STOM_Version_3 --live
```

T01 실 merge + T04 실 commit + T05 실 push가 실행됨.

## 4. audit JSON schema v2

```json
{
  "schema_version": "v2",
  "version": "19",
  "upstream_ref": "STOM_Version_3",
  "timestamp_utc": "2026-...",
  "mode": "dry-run|live",
  "primary_signals": {
    "t01_upstream_merge": "passed|failed",
    "t02_integrated_verifier": "passed|failed"
  },
  "corroborating_signals": {
    "t01_diff_stat_present": true,
    "t02_manifest_path": "/path/to/manifest.json",
    "t02_stdout_lines": 15
  },
  "decision": "PASS|FAIL"
}
```

primary signals만으로 PASS/FAIL 결정. corroborating signals는 audit 추적용.

## 5. fail 시 대응

| 단계 fail | 의미 | 조치 |
|---|---|---|
| T01 wrong branch | 현재 STOM_Version_3U 아님 | `git checkout STOM_Version_3U` 후 재실행 |
| T01 uncommitted changes | working tree dirty | commit·stash·discard 후 재실행 |
| T01 merge conflict | upstream과 V3U 차이가 자동 merge 불가 | 수동 merge resolve 후 abort 또는 별도 사이클 |
| T02 verifier fail | V3U 안전망 깨짐 | 8 stage 중 fail 단계 식별 → V3U 4단계 워크플로우 |
| T03 file write fail | .omc/audits/ 권한 | 디렉토리 권한 확인 |
| T04 commit fail | git config 또는 hook 문제 | git log 확인 후 수동 commit |
| T05 push fail | remote 권한 또는 비-fast-forward | git pull --rebase 후 재시도 |

## 6. V3U lane 4단계 워크플로우와의 관계

본 파이프라인은 V3U lane의 **흡수 단계 자동화**이고, V3U lane의 **결함 발견·수정 4단계 워크플로우**(CLAUDE.md)는 흡수 후 발견되는 결함을 처리한다.

```
V3.X upstream 발표
    ↓
v3uc_ingest_pipeline.py --version <X> --live  (T01~T05 자동화)
    ↓
[PASS] → 흡수 완료. 다음 V3.X+1 발표까지 대기
[FAIL] → V3U lane 4단계 워크플로우 발동 (결함 발견·V3U 수정·회귀·LESSONS 갱신)
```

## 7. 차후 개선 후보

- T06: pre-flight check (V3 upstream fetch + delta 미리 보기)
- T07: post-flight notification (Telegram/email)
- conflict 자동 resolve 시도 (단순 case만)
- multi-version 흡수 (V3.19 + V3.20 연속)

## 8. 관련 문서

- `scripts/v3uc_ingest_pipeline.py` 도구 본체
- `tests/v3uc/test_ingest_pipeline.py` 단위 테스트
- `docs/V3U_C_INFERENCE_LESSONS.md` 3U_C lane 결함 진실 원천
- `docs/V3U_C_NEXT_STEPS.md` 3U_C lane decision tree
- `docs/CARRY_FORWARD_REGISTRY.md` V3U_C custom allowlist rule
- `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` §6.3 E1 옵션 정의
- (V3U lane) `CLAUDE.md` 결함 발견·수정 4단계 워크플로우
