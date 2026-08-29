# SYS-04 Fast/Slow Unit Gate 구현 결과

> 실행일: 2026-08-29~30
>
> 기능 커밋: `2d73a9f7`
>
> 문서 커밋: `4b1ca309` · 재출발 병합: `05ab7df2` · 파이프라인 병합: `2a221586`
>
> 작업 브랜치: `codex/process-research-sys-04-suite-performance`
>
> 연구 실행: 없음 · G2: 없음 · Holdout: `SEALED_NOT_TOUCHED`

---

## 1. 한 문장 결론

> **89분 36초 unit suite에서 실제 18~19% 병목 24건을 측정해 분리했고, assertion을 삭제하지 않은 채 fast Gate를 23분 22초로 줄였다.**

```text
BASELINE FULL ........ 89m 36s
        │
        ├── FAST COMMIT GATE .... 7,928 PASS · 27 SKIP · 23m 22s
        │
        └── SLOW PUSH GATE ......    24 PASS ·          19m 04s

연구 결과 변화 ........ 없음
경제 후보 변화 ........ 0/7 STOP 유지
Holdout ............... SEALED_NOT_TOUCHED
```

---

## 2. Status Dashboard

| 항목 | 상태 | 증거 |
|---|---|---|
| 병목 실제 측정 | **PASS** | 파일·test ID·duration 확보 |
| fast Gate | **PASS** | 7,928 pass · 27 skip · 24 deselect |
| slow Gate | **PASS** | 24 pass · 7,955 deselect |
| assertion 삭제 | **0건** | 기존 테스트 본문 유지 |
| marker 분류 | **PASS** | `slow_suite` 24건 |
| 핵심 18~19% 구간 | **개선** | 약 20분 → 약 30초 통과 |
| 전체 one-process full | **이번 변경 후 미반복** | fast+slow 두 Gate로 전 항목 실행 |
| 연구 실행 | **NONE** | 코드/테스트 성숙화만 수행 |
| 보호 DB | **주의** | main worktree에 0-byte test artifact 1개 잔존 |
| 공식 review-work | **미실행** | 무위임 경계로 5-agent review 불가, 로컬 검토만 수행 |
| 정본 통합 | **PASS** | restart `05ab7df2` → pipeline `2a221586` |

---

## 3. 무엇이 실제로 느렸는가

### 3.1 18~19% 원인

| 대상 | 수 | 1차 파일 실행 | 역할 |
|---|---:|---:|---|
| `test_alpha_bridge.py::TestPromotionV2` | 23 | 19m 52s | Git/SQLite authority·충돌·복구·fail-closed |
| `test_alpha_catalog.py::test_minimal_authority_catalog_builds_real_pre_and_post` | 1 | 146.61s | 실물 PRE/POST authority catalog |
| 합계 | **24** | 약 22분대 | push/nightly에 유지 |

경계 주변 11개 파일도 직접 실행했다. 대부분 0.89~19.95초였고 병목이 아니었다.

### 3.2 slow Gate 최종 상위 duration

| 순위 | test ID 요약 | 시간 |
|---:|---|---:|
| 1 | canonical POST direct input | 111.35s |
| 2 | real PRE/POST catalog | 108.07s |
| 3 | tampered PRE/POST fail-closed | 103.85s |
| 4 | DB-before-POST crash reconciliation | 82.65s |
| 5 | stale live DB strong verification | 63.31s |

24개 전체는 `19m 04s`에 PASS했다. 실행시간은 PC 부하와 filesystem cache에 따라 달라질 수 있다.

---

## 4. 구현 구조

```text
pytest collection
      │
      ▼
slow_suite_manifest.is_slow_suite(nodeid)
      │
      ├── PromotionV2 class prefix ─────┐
      └── real PRE/POST exact node ─────┤
                                        ▼
                               pytest.mark.slow_suite
                                  │            │
                                  │            └── -m slow_suite
                                  └── -m "not slow_suite"
```

| 파일 | 책임 |
|---|---|
| `pytest.ini` | `slow_suite` marker 등록 |
| `tests/unit/slow_suite_manifest.py` | 실측 selector 두 개와 분류 함수 |
| `tests/unit/conftest.py` | 수집 시 해당 24개에 marker 적용 |
| `tests/unit/test_slow_suite_manifest.py` | slow 2경로·nearby fast 1경로 계약 |
| `tests/unit/test_btrack_ext.py` | file-only 전제를 required table/core row 전제로 강화 |

큰 `test_alpha_bridge.py`(777 pure LOC)와 `test_alpha_catalog.py`(1,175 pure LOC)는 이번 변경에서 수정하지 않았다. marker를 외부 manifest에 둔 이유는 성능 Gate와 대형 테스트 리팩터링을 분리하기 위해서다.

---

## 5. 실행 명령

```powershell
# 커밋 전: slow authority 24건 제외
python -m pytest tests/unit -m 'not slow_suite' -q

# push/nightly: slow authority 24건만
python -m pytest tests/unit -m slow_suite -q

# 필요 시 기존 one-process full
python -m pytest tests/unit -q
```

fast와 slow를 모두 실행하면 수집된 unit 계약 전체를 검증한다. 이번 SYS-04에서는 두 Gate를 각각 실제 완주했으며, 변경 후 one-process full 명령은 다시 실행하지 않았다.

---

## 6. Red → Green과 부수 결함

### 6.1 marker 계약

```text
RED   ModuleNotFoundError: tests.unit.slow_suite_manifest
GREEN 3 passed
COLLECT slow 24 / fast 7,955 / total 7,979
```

### 6.2 B-track 환경 전제

1차 fast 실행은 다음으로 실패했다.

```text
test_btrack_ext.py::test_mechanized_selection
sqlite3.OperationalError: no such table: stockbuy
```

원인은 `_database/strategy.db` 파일 존재만 보고 실행 가능하다고 판정한 것이었다. 0-byte 파일은 DB가 아니다. 격리 detached worktree에서 absence 상태는 정상 skip됐고 보호 DB 생성도 재현되지 않았다.

수정 후에는 `stockbuy`와 핵심 `CORE_7[0]` 행이 있을 때만 실행한다.

```text
FOCUSED  10 passed · 2 skipped
FAST     7,928 passed · 27 skipped · 24 deselected
```

---

## 7. 검증 영수증

| 검증 | 결과 |
|---|---|
| manifest RED | import failure 확인 |
| manifest GREEN | 3 pass |
| marker collect | slow 24 · fast 7,955 · total 7,979 |
| focused btrack+manifest | 13 pass · 2 skip |
| fast Gate | 7,928 pass · 27 skip · 24 deselect · 23m22s |
| slow Gate | 24 pass · 7,955 deselect · 19m04s |
| Ruff | PASS |
| no-excuse | 4 files · 0 violation |
| basedpyright | 0 error · 0 warning · 0 note |
| pure LOC | 13 / 21 / 22 / 129, 모두 250 이하 |
| `git diff --check` | PASS |

`review-work`는 5개 subagent가 모두 PASS해야 공식 PASS다. 이번 작업은 무위임 경계 때문에 subagent를 생성하지 않았으며, 따라서 공식 review-work PASS를 주장하지 않는다.

---

## 8. 남은 성능 부채

fast Gate 상위에는 아직 다음 묶음이 있다.

| 후보 | 관측 | 이번 처리 |
|---|---:|---|
| Track-Z harness 7건 | 각 27~29초 | 유지 |
| research index route | 26.71초 | 유지 |
| alpha discipline manifest issuer | 23.08초 | 유지 |
| alpha runlab 2건 | 각 12~13초 | 유지 |

fast Gate 23분은 기존 89분보다 훨씬 낫지만 “수초 단위 commit Gate”는 아니다. 후속 성능 단계는 별도 SYS branch에서 다루고, 이번 24개 selector에 임의로 섞지 않는다.

---

## 9. 보호 경로 주의

main worktree에 다음 파일이 남아 있다.

```text
C:\System_Trading\STOM\STOM_V.wt-process-research-restart\_database\strategy.db
size: 0 bytes
created: 2026-08-29 22:38:08 KST
```

자동 삭제는 안전 정책에 의해 차단됐으며 우회하지 않았다. Git stage/commit에는 포함되지 않는다. 다음 세션 시작 전 사용자가 경로와 0-byte를 다시 확인한 뒤 제거해야 한다.

```powershell
$db = Get-Item -LiteralPath 'C:\System_Trading\STOM\STOM_V.wt-process-research-restart\_database\strategy.db'
$db | Select-Object FullName, Length, CreationTime, LastWriteTime
if ($db.Length -eq 0) { Remove-Item -LiteralPath $db.FullName }
```

0-byte가 아니면 삭제하지 말고 즉시 중지한다.

---

## 10. 다음 단계

```text
[SYS-04 COMPLETE]
        ↓
[zero-byte artifact 확인·제거]
        ↓
[새 구조 가설 검토 문서]
        ↓
[RES-04 사전등록]
        ↓
[새 G0]
```

새 연구 실행, G2, Holdout, 기존 threshold 미세조정은 아직 금지다.
