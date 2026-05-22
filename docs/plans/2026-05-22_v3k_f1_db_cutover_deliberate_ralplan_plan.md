# V3K F1 DB Cutover --deliberate ralplan 합의 plan (Planner v1)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `4fd48ad2` (V3K 페이지 1 A-lane closure 직후) |
| 본체 plan 인용 | `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (T01-T08 + LC1-LC3) |
| approval prep 인용 | `docs/plans/2026-05-13_v3k_page_053_f1_actual_db_cutover_approval_prep_plan.md` |
| 정책 baseline | `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` §4.2 A-lane 표 |
| 지도 baseline | `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` §4.2 페이지 2 |
| 페이지 1 closure evidence | `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json` |
| 본 plan 정체성 | F1 cutover의 **`--deliberate` ralplan 합의 plan** (Planner v1). 본체 plan을 supersede하지 않고 합의 layer를 얹는다 |
| iteration 단계 | **Planner v1** (Architect/Critic review는 후속 commit) |
| ralplan mode | `--deliberate` (CRITICAL risk이므로 Pre-mortem + 확장 테스트 계획 의무) |
| 위험도 | **치명 (CRITICAL)** — 운영 `_database/` 영구 변경 |

---

## §0. TL;DR

```text
F1 DB cutover는 V3K 페이지 2(Step 3)이며 운영 _database/를 V3 학습 schema로 영구 전환한다.
본체 plan(2026-05-12)과 approval prep(page 053)으로 scripts + 4중 guard는 이미 완비.
본 합의 plan은 그 위에 --deliberate ralplan을 얹어 Pre-mortem 12건 + 확장 테스트 4축
(unit/integration/e2e/observability) + Rollback drill을 정본화한다.
페이지 1 A-lane closure 후 24h monitoring 종료(2026-05-23T03:02 UTC) + 사용자 phrase +
V3K_CUTOVER_USER_ACK=1 + transaction lock window 4건 모두 충족 시점에만 A2 진입 가능.
```

---

## §1. V3K 미션 재확인 (페이지 2 측면)

`V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영. LS 제외, Kiwoom 유지.` 페이지 2(F1 DB cutover)는 V3 학습/분석에 필요한 DB schema를 운영 lane으로 *영구* 연결한다. 어제 정본화된 지도 plan §4.2 인용:

```text
페이지 2 (Step 3, F1 DB cutover) — 잔여 50%p
들어있는 V3 기능군: #1 shadow DB + cutover, #2 production learning DB read (동반 완성)
활성화 산출:
- V3 학습 데이터 schema가 운영에 실제 연결됨
- analyzer별 입력/출력/state 저장 테이블 활성화
- 백테스트 기준일 이후 데이터 누수 차단 timestamp index 활성화
- 종목별 학습 누적 데이터 read 경로 활성화
현재: _database_v3k_shadow/ (7건) ↔ _database/ (1176건) parity 검증만 완료
Cutover 후: 운영 경로가 V3 schema를 read하기 시작
사전 조건: A1 closure + V3K_CUTOVER_USER_ACK=1 + --deliberate ralplan + parity ±0 + transaction lock window
Monitoring: 7일
위험도: CRITICAL
```

---

## §2. ralplan iteration log

본 plan은 ralplan 합의 흐름의 **Planner v1** 단계다. 이후 iteration은 별도 commit으로 분리한다 (V3K plan-first 패턴).

| iteration | step | status | commit |
| ---: | --- | --- | --- |
| 1 | Planner v1 (본 plan) | ✅ 본 commit | (this) |
| 2 | Architect review (시스템 설계 정합성 + 인터페이스 + 경계) | ⏸ 후속 commit | (next) |
| 3 | Critic review (위험 요소 + 반박) | ⏸ 후속 commit | (next) |
| 4 | Planner v2 (Architect/Critic 피드백 흡수) | ⏸ 후속 commit | (next) |
| 5 | Architect APPROVE + Critic APPROVE | ⏸ 합의 종결 | (next) |

본 commit으로 iteration 1을 종결하고, 24h monitoring window 동안 Architect/Critic iteration을 병렬로 진행할 수 있다.

### §2.1 ralplan --deliberate 의무 산출

`--deliberate` mode는 다음을 추가로 의무 부담한다:

- **Pre-mortem**: 12+ 실패 시나리오 + 대응 (§6)
- **확장 테스트 계획**: unit / integration / e2e / observability 4축 (§7)
- **Rollback drill**: 단순 rollback script 보유 외에 *실제 drill 시뮬레이션 evidence* (§8)

본 Planner v1은 위 3건의 baseline을 정본화한다.

---

## §3. Planner v1 본문 — 실행 순서

본체 plan §C.0 T01-T08 task 분해는 그대로 유지하며 본 합의 plan은 각 task에 commit-level guard와 정량 검증을 추가한다.

### §3.1 실행 sequence (확정 순서)

```
T01 backup_operational_database.py --apply  (운영 _database/ 전체 backup + checksum manifest)
  ↓ verify: backup hash 정합 + manifest 정본화
T02 smoke_v3k_cutover_dryrun.py            (tempfile-only dryrun + 4중 guard 동작 검증)
  ↓ verify: PASS
T03 cutover_v3k_shadow_to_database.py --apply --backup-first --backup-dir <ts> --allow-operating-target
  ↓ verify: cutover 완료 + 운영 _database/ checksum 갱신
T04 v3k_db_health.py                       (post-cutover read-only health report)
  ↓ verify: V3 schema 정상 인식 + 학습 데이터 read 경로 확인
T05 7일 모니터링 시작                       (LC3 invariant 활성화)
  ↓ verify: 24h × 7 점검 evidence 누적
T06 registry V3K-CUTOVER-ENABLE 등록        (closure commit)
```

### §3.2 4중 guard (cutover_v3k_shadow_to_database.py 본문 인용)

```python
def require_apply_guards(args, target_dir):
    if current_branch() != "STOM_Version_2U_C":   # G1: branch guard
        raise SystemExit(...)
    if os.environ.get("V3K_CUTOVER_USER_ACK") != "1":   # G2: USER_ACK env
        raise SystemExit(...)
    if not args.backup_first:                          # G3: backup precondition
        raise SystemExit(...)
    if args.backup_dir is None:                        # G4: backup dir 명시
        raise SystemExit(...)
    if target_dir == operating_target and not args.allow_operating_target:
        raise SystemExit(...)                          # G5: operating target ack
```

5중 guard 중 하나라도 실패하면 SystemExit. cutover script 자체가 default-OFF의 정점이다.

### §3.3 transaction lock window 정의

cutover는 다음 시간대에만 수행:

- 한국 정규장 외 시간 (15:30 이후 ~ 익일 08:30 이전)
- 토요일/일요일/공휴일 전일자
- 키움 OpenAPI 정기점검 시간(매월 첫째 토요일 00:00~08:00) 회피
- **권장 시간대**: 토요일 자정 ~ 일요일 자정 (사용자 한가하고 운영 영향 0)

---

## §4. Architect 관점 (system 설계 정합성)

본 Planner v1은 Architect review iteration 전이지만, baseline Architect 관점을 명시한다.

### §4.1 system boundary 분석

```
[ 운영 _database/ ]  ─── L1 invariant (schema 무변경)
       │
       │ cutover write (LC1 exception, backup-first 보장)
       ↓
[ V3 schema overlay ]
       │
       │ runtime read (백테스트 + 실시간)
       ↓
[ analyzer 7종 + microstructure engine ]   (Phase F/G에서 ON 전환)
       │
       │ feature flag default-OFF
       ↓
[ 매매 전략 결정 경로 ]   ─── LH1 invariant (코드 무변경)
```

### §4.2 인터페이스 계약

| 컴포넌트 | 입력 | 출력 | 호환성 의무 |
| --- | --- | --- | --- |
| `cutover_v3k_shadow_to_database.py` | shadow DB 7건 + ack env + backup dir | 운영 `_database/` overlay + manifest | LC1 (backup) + LC2 (single commit) |
| `v3k_db_health.py` | 운영 `_database/` | health report JSON | read-only |
| analyzer adapter (Phase F) | 운영 `_database/` (V3 schema) | analyzer output | feature flag OFF |
| 매매 전략 결정 (운영) | 운영 `_database/` (V3 schema 무관 view) | 매매 신호 | LH1 무영향 |

### §4.3 backward compatibility 책임

cutover 후 V3 schema가 운영에 추가되지만 **기존 V2 schema(1176건)는 보존**된다. 즉:

- V3 schema: 신규 추가 (overlay)
- V2 schema: 기존 그대로 (보존)
- 운영 매매 경로: 기존 V2 schema read (LH1 무영향)
- V3K analyzer/engine 경로: V3 schema read (feature flag default-OFF)

backward compatibility는 schema overlay 방식으로 자연 보장된다.

---

## §5. Critic 관점 (위험 요소 + 반박)

### §5.1 검토할 위험 요소

| # | 위험 | severity | 대응 |
| ---: | --- | --- | --- |
| 1 | shadow → operating write 중 키움 OCX가 동시 write 시도 | High | transaction lock window로 매매 외 시간만 수행 |
| 2 | backup 파일 자체 손상 | High | LC1 + checksum manifest로 backup 무결성 사전 검증 |
| 3 | cutover 중간 실패 (partial write) | Critical | atomic copy + 실패 시 즉시 rollback (T04 script) |
| 4 | V3 schema와 V2 schema 컬럼명 충돌 | Medium | shadow 단계에서 parity 검증 완료 (어제 evidence) |
| 5 | 7일 모니터링 중 매매 영향 발견 | Critical | rollback_v3k_cutover.py로 즉시 V2 복귀 |
| 6 | rollback이 backup manifest 손상으로 실패 | Critical | backup 다중화(LC1 + offsite copy) 검토 의무 |
| 7 | cutover commit 후 git revert로 코드는 복귀하지만 DB는 그대로 | Critical | LC2 (single commit) + rollback script가 DB 복귀 책임 분리 |
| 8 | 24h monitoring window가 사용자 부재 시간과 겹침 | Low | 한국 표준 업무시간 + 평일 시작 권장 |
| 9 | 키움 OpenAPI 자체 업데이트가 cutover와 겹침 | High | cutover 전 KOA Studio 환경 점검 의무 |
| 10 | V3K_CUTOVER_USER_ACK env가 child process scope만 발급되어 cutover script가 못 읽음 | Low | bash inline `V3K_CUTOVER_USER_ACK=1 python ...` 형식이면 자식에 전파 |

### §5.2 반박/완화 baseline

본 Planner v1은 위 10건에 대해 baseline 대응을 명시했으나, Architect review iteration에서 추가 위험 + Critic review iteration에서 반박 검증이 의무다.

---

## §6. Pre-mortem (실패 시나리오 12건)

`--deliberate` 의무 산출. cutover가 실패하는 시나리오와 사전 차단 대책.

| # | 실패 시나리오 | 발생 시 결과 | 사전 차단 | Rollback path |
| ---: | --- | --- | --- | --- |
| P-01 | branch 잘못 둠 (V2 main에서 cutover 시도) | V2 main DB 손상 | G1 branch guard | branch 자동 abort |
| P-02 | USER_ACK env 미발급 | guard abort | G2 env guard | abort, 손상 없음 |
| P-03 | backup 안 만들고 cutover | rollback 불가능 | G3 `--backup-first` 강제 | abort, 손상 없음 |
| P-04 | backup_dir 명시 안 함 | backup 위치 추적 불가 | G4 `--backup-dir` 강제 | abort, 손상 없음 |
| P-05 | operating target 명시 ack 누락 | shadow에 잘못 write | G5 `--allow-operating-target` 강제 | abort, 손상 없음 |
| P-06 | cutover 중 디스크 full | partial write | 사전 디스크 공간 검증 (`scripts/v3k_db_health.py`로 free space 확인) | rollback_v3k_cutover.py |
| P-07 | cutover 중 stom.bat 등 OCX 동시 사용 | DB lock | transaction lock window | rollback_v3k_cutover.py |
| P-08 | cutover 중 PC 강제 종료 (정전 등) | partial write | atomic shutil.copyfile + manifest-first sync | rollback_v3k_cutover.py |
| P-09 | cutover 후 health smoke 실패 | V3 schema 손상 | T04 health check 의무 + 실패 시 즉시 rollback | rollback_v3k_cutover.py |
| P-10 | 7일 모니터링 중 매매 신호 왜곡 발견 | 잠재적 실거래 손실 | 매매 신호는 V3 schema 무관 (LH1), 발견 시 즉시 rollback | rollback_v3k_cutover.py |
| P-11 | rollback 시 backup manifest 손상 | rollback 불가능 | backup 직후 checksum 검증 + multi-copy (1차 `_database.backup.<ts>/` + 2차 offsite) | manual restore |
| P-12 | cutover commit이 git push까지 가서 다른 사용자에 영향 | 전체 lane 오염 | LC2 + push는 별도 단계 (cutover commit과 분리) | branch revert + DB rollback 병행 |

---

## §7. 확장 테스트 계획 (4축)

`--deliberate` 의무 산출.

### §7.1 Unit tests (script 단위)

| script | 테스트 항목 |
| --- | --- |
| `cutover_v3k_shadow_to_database.py` | 5중 guard 각각의 abort 시나리오 5건 + dry-run vs apply 분기 + checksum 산출 |
| `rollback_v3k_cutover.py` | manifest read 정합 + branch guard + ack guard + 누락 파일 검출 |
| `backup_operational_database.py` | dry-run vs apply + manifest 생성 + checksum 정합 |
| `smoke_v3k_cutover_dryrun.py` | tempfile-only 보장 + operating DB write 0건 검증 |

### §7.2 Integration tests (script 조합)

| 시나리오 | 흐름 | 통과 기준 |
| --- | --- | --- |
| backup → dry-run cutover → rollback (tempfile) | tempfile에서 전체 흐름 | exit 0 + 무손상 + manifest 정합 |
| backup → cutover --apply (tempfile) → health smoke | tempfile에서 apply | health smoke PASS |
| guard abort 5건 × 각 script | 5 × 3 = 15 시나리오 | 모두 SystemExit + 운영 DB 무영향 |

### §7.3 E2E test (실제 시뮬레이션)

| 시나리오 | 흐름 | 통과 기준 |
| --- | --- | --- |
| 운영 환경 simulator (test_database 디렉토리) | 운영과 동일 schema의 미니 DB로 전체 cutover 흐름 | 1주일 시뮬레이션 + 매매 신호 무변경 |
| Rollback drill | 운영 환경 simulator에서 cutover 후 rollback 강제 발동 | 100% V2 schema 복원 + checksum 정합 |

### §7.4 Observability (관측 지표)

cutover 전/중/후 다음 지표를 monitoring 의무:

| 지표 | 측정 시점 | 정상 범위 |
| --- | --- | --- |
| 운영 `_database/` 전체 file count | cutover 전 = 1176건 / 후 = 1176+7 = 1183건 | 정확히 +7 |
| 운영 `_database/` 전체 checksum | cutover 전 manifest = 후 V2 schema 부분 | V2 부분 checksum 무변경 |
| 백테스트 결과 (feature flag OFF) | cutover 전 vs 후 동일 sample period | 100% 동일 (LH1) |
| stom.bat 정상 로그인 | cutover 후 24h × 7 | 매일 1회 정상 |
| 키움 OCX 매매 신호 분포 | cutover 후 7일 | 분포 변화 ±0% |
| analyzer adapter import (feature flag OFF) | cutover 후 | import 성공, 호출 0건 |

---

## §8. Rollback procedure

### §8.1 Rollback 발동 조건

다음 중 하나라도 발생하면 즉시 rollback:

1. T04 health smoke 실패
2. cutover 후 stom.bat 로그인 실패
3. 백테스트 결과 변동 (feature flag OFF에서 변경)
4. 매매 신호 분포 ±0% 초과
5. 사용자 명시 rollback 지시

### §8.2 Rollback 순서

```powershell
# 관리자 PowerShell
cd C:\System_Trading\STOM\STOM_V.wt-dev
$env:V3K_CUTOVER_USER_ACK='1'
python scripts/rollback_v3k_cutover.py --apply --backup-manifest <ts>/v3k_backup_manifest.json --allow-operating-target

# 검증
python scripts/v3k_db_health.py
# 운영 DB가 V2 schema로 복귀했는지 확인 (1176건, V2 checksum 정합)
```

### §8.3 Rollback drill (cutover 전 의무 시뮬레이션)

cutover 전 **반드시** test_database/ 디렉토리에 mini 환경 만들어 다음 drill 수행:

```
1. mini operating DB 생성 (V2 schema 일부)
2. mini shadow DB 생성 (V3 schema 일부)
3. cutover --apply 실행 → 정상 진행 확인
4. health smoke PASS 확인
5. rollback --apply 실행 → 100% V2 schema 복귀 확인
6. checksum 정합 확인
```

drill 결과 evidence는 cutover 진입 전 commit으로 사전 정본화.

---

## §9. A2 진입 trigger (4건 확정)

페이지 1 (A1) closure 후 페이지 2 (A2) 진입은 다음 4건 모두 충족 시점에만 가능:

| # | Trigger | 검증 방법 | 현재 상태 |
| ---: | --- | --- | --- |
| 1 | A1 24h monitoring window 종료 | 시각 매치 (2026-05-23T03:02 UTC 이후) | ⏳ 대기 |
| 2 | `V3K_CUTOVER_USER_ACK=1` durable env 발급 | env var 검증 | ⏸ 대기 |
| 3 | `--deliberate ralplan` 합의 종결 (Planner v1→v2 + Architect APPROVE + Critic APPROVE) | iteration log 검증 | ⏳ Planner v1 (본 commit) |
| 4 | transaction lock window 진입 시각 명시 | 시각 명시 evidence | ⏸ 대기 |

본 commit으로 #3의 iteration 1이 종결. #1은 시간 경과로 자동, #2/#4는 cutover 실행 시점 사용자 명시.

---

## §10. 보존 invariant check (본 commit 시점)

| invariant | 보존 |
| --- | --- |
| L1 database schema unchanged | ✅ (cutover 미실행) |
| L7 no LS direct dependency | ✅ |
| L9 STOM CLI surface preserved | ✅ |
| LH1 Kiwoom order/exit path unchanged | ✅ |
| LH5 forward-only schema_version | ✅ |
| LC1 cutover 전 backup 필수 | 본 plan §3.1 T01 명시 |
| LC2 single commit + 명시 승인 dance | 본 plan §3.1 T06 + A2 trigger §9 명시 |
| LC3 7일 모니터링 기간 동안 새 cutover 금지 | 본 plan §3.1 T05 명시 |

본 commit은 docs 1건 추가, 코드 변경 0, runtime 무영향. 모든 invariant 보존.

---

## §11. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports _v3k_sidecar
```

본 commit은 `docs/plans/` 1건 + `docs/CARRY_FORWARD_REGISTRY.md` 1 섹션만 추가.

---

## §12. preparation-first §3 정합

| §3 허용 | 본 plan |
| --- | --- |
| docs 추가 | ✅ plan 1건 |
| approval packet 작성 | ✅ §9 trigger 정의 |
| cutover script 점검 (read-only) | ✅ §3.2 인용 |

| §3 금지 | 본 plan |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| shadow → operating 실제 복사 | ❌ 0건 |
| transaction lock 실제 진입 | ❌ 0건 |
| cutover 완료 registry 선언 | ❌ 0건 (`V3K-CUTOVER-ENABLE`은 A2 closure commit에서) |

→ P-lane 적격.

---

## §13. 다음 인계

본 commit 이후 24h monitoring window(2026-05-23T03:02 UTC) 동안 다음 ralplan iteration을 병렬 진행 가능:

| iteration | 작성 commit | 책임 |
| ---: | --- | --- |
| 2 | Architect review (별도 commit) | §4 baseline 확장 + 시스템 boundary 추가 검토 |
| 3 | Critic review (별도 commit) | §5/§6 baseline 검증 + 추가 위험 발견 |
| 4 | Planner v2 (Architect/Critic 흡수) | 본 plan amend or 신규 plan |
| 5 | 합의 종결 (APPROVE) | registry V3K-F1-DELIBERATE-RALPLAN-CONSENSUS 등록 |

iteration 5 이후 사용자 명시 trigger 4건 충족 시점에 A2(F1 cutover actual) 진입 가능.

---

## §14. 관련 문서

- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (본체 plan, T01-T08 + LC1-LC3)
- `docs/plans/2026-05-12_v3k_page_029_f1_db_cutover_pre_ralplan_plan.md`
- `docs/plans/2026-05-12_v3k_page_030_f1_cutover_scripts_dryrun_plan.md`
- `docs/plans/2026-05-12_v3k_page_031_f1_actual_cutover_approval_gate_plan.md`
- `docs/plans/2026-05-13_v3k_page_053_f1_actual_db_cutover_approval_prep_plan.md`
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md`
- `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` (지도 §4.2)
- `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json` (페이지 1 closure)
- `scripts/cutover_v3k_shadow_to_database.py`
- `scripts/rollback_v3k_cutover.py`
- `scripts/smoke_v3k_cutover_dryrun.py`
- `scripts/backup_operational_database.py`
- `scripts/v3k_db_health.py`
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-F1-DELIBERATE-RALPLAN-PLANNER-V1` 섹션)
