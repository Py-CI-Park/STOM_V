# V3K 백테스트/CLI 우선 진행 master plan

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `6e8e23d0` (F1 ralplan Planner v1 직후) |
| 동반 update_log | `docs/update_log/2026-05-22_v3k_midcourse_review_backtest_cli_prioritization.md` |
| 본 plan 정체성 | 운영 트랙 보류 + 백테스트/CLI 트랙 우선 진입 결정 후의 **전체 작업 계획 master** |
| 코드 변경 | 0건 (정책/계획 정본화) |
| 우선순위 | V3K 백테스트 강화 (트랙 A) > CLI 확장 (트랙 B) > Sidecar (트랙 C) >> 운영 (트랙 D, 보류) |

---

## §0. TL;DR

```text
4개 트랙 분류:
  A. V3K 백테스트 강화 (#2 + #4 + #6/#7 default-OFF parity)
  B. CLI 확장 plan Phase 1~3 (2026-03-24 plan 이어가기)
  C. Sidecar (#3 GUI setting persistence)
  D. 운영 (트랙 #1 cutover + 페이지 2~5 actual) — 보류

권장 진행 순서:
  M1. 진단 phase (1주) — CLI Phase 1~3 + V3K-IMPL-3 현재 진척 확인
  M2. CLI Phase 1 (라이브러리 5개 노출, 2주) + V3K-IMPL-3 동시 진행
  M3. CLI Phase 2 (출력 표준화) + Phase F/G parity 검증
  M4. CLI Phase 3 (설정관리/리포트) + #4 formula globals 통합
  M5. 사용자 결정 시점에 트랙 D 재개

F6 진척률: 백테스트 트랙은 일부 항목 +25%p 가능 (실측치는 진단 후)
```

---

## §1. V3K 미션 재인용 (무변경)

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지한다.
```

본 master plan은 mission 무변경 + 진행 순서만 재정렬.

---

## §2. baseline

| 항목 | 값 |
| --- | --- |
| 2U_C HEAD | `6e8e23d0` |
| F6 진척률 | 53.6% (375/700, #5 100% 반영 후) |
| 완료된 페이지 | 1 (Phase H H-2 live dry-run, A-lane closure `4fd48ad2`) |
| 보류된 페이지 | 2~5 (F1 cutover + Phase F ON + Phase G ON + F7 closure) |
| 관련 자산 보존 | Plan 11건, scripts 10+ 건, evidence 4건 모두 그대로 유효 |

---

## §3. 작업 트랙 분류

### §3.1 트랙 A — V3K 백테스트 강화 (Active)

V3K 8개 기능군 중 **백테스트 영역에서 default-OFF 또는 read-only로 진행 가능한 항목**.

| # | 항목 | 현재 | 본 트랙 목표 | 운영 영향 |
| ---: | --- | ---: | --- | --- |
| 2 | production learning DB read | 75% | 백테스트가 V3 학습 DB read (기준일 이전만, leakage 차단) | 0건 (read-only) |
| 4 | formula globals | 50% | V3 globals(volatility 계수, threshold)을 runtime에 노출, feature flag default-OFF | 0건 |
| 6 | analyzer Phase F default-OFF parity | 25% | analyzer 7종을 default-OFF로 백테스트 parity 검증 (matrix +/- 100건) | 0건 (ON 안 함) |
| 7 | microstructure engine Phase G default-OFF parity | 25% | engine을 default-OFF로 백테스트 parity + benchmark 검증 | 0건 (ON 안 함) |

기존 자산:

- `scripts/backtest_v3k_phase_f_parity.py` ✅ 작성됨
- `scripts/backtest_v3k_phase_g_parity.py` ✅ 작성됨
- `scripts/smoke_v3k_backtest_learning_hook.py` ✅ 작성됨
- `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` (Phase B 본체)
- `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md` (F5 본체)
- `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` (동반)

### §3.2 트랙 B — CLI 확장 (Active)

`docs/plans/2026-03-24_cli_expand_subcommands_plan.md` Phase 1~3 이어가기. V3K와 독립 트랙이며 LH9(STOM CLI surface 보존)와 호환 (기존 동작 보존, 신규 추가만).

| Phase | 목표 | 현재 |
| --- | --- | --- |
| Phase 1 | 라이브러리 5개를 CLI 서브커맨드로 노출 (`optimize`, `sweep`, `wfo`, `tune`, `db` — 일부 이미 노출) | 진단 필요 |
| Phase 2 | 전체 서브커맨드 출력 표준화 (JSON, UTF-8, 버전) | 진단 필요 |
| Phase 3 | 설정 관리 CLI + 리포트 생성 CLI 신규 | 미진행 |

CLI 모듈 현황 (`cli/*.py`): 30개 모듈, 서브커맨드 19개 노출.

### §3.3 트랙 C — Sidecar (Boost)

V3K #3 (GUI setting persistence) sidecar 작업. Phase F/G 토글 source-of-truth(`_v3k_sidecar/v3k_gui_settings.json`).

운영 영향 0건이고 우선순위 보조. 트랙 A/B 진행 중 병행 가능.

기존 자산:

- `docs/plans/2026-05-14_v3k_page_078_preapproval_stop_condition_plan.md` (sidecar 정책)
- `_v3k_sidecar/` 디렉토리 구조 정의
- `scripts/write_v3k_phase_f_sidecar_enable.py`, `scripts/write_v3k_phase_g_sidecar_enable.py` (sidecar writer)

### §3.4 트랙 D — 운영 (Frozen)

| 항목 | 자산 보존 |
| --- | --- |
| V3K #1 shadow DB + cutover | 본체 plan, ralplan Planner v1, scripts 모두 보존 |
| V3K 페이지 2 (F1 cutover actual) | ralplan iteration 2-5 미진행 상태 유지 |
| V3K 페이지 3 (Phase F F-4 ON actual) | sidecar writer/audit/parity scripts 보존 |
| V3K 페이지 4 (Phase G G-3 ON actual) | engine staging + benchmark scripts 보존 |
| V3K 페이지 5 (F7 closure) | closure audit scripts 보존 |

**재개 조건**:

1. 사용자 명시 의사 표시
2. 트랙 A/B/C에서 default-OFF parity 충분 검증된 후
3. 24h+ monitoring window 진입 가능 시점

재개 시 본 master plan을 인용해 보류 trail을 깨우고 이어간다.

---

## §4. 각 트랙별 의존성 + milestone

### §4.1 의존성 그래프

```
트랙 A.V3K-IMPL-3 (백테스트 학습 DB)  ──┐
                                       ├─→  트랙 A 본격 작업
트랙 A.Phase B (read-only learning DB) ┘
                                       
트랙 B.Phase 1 (라이브러리 노출)        ──┐
                                       ├─→  트랙 B 완성
트랙 B.Phase 2 (출력 표준화)          ──┤
                                       │
트랙 B.Phase 3 (설정관리/리포트)      ──┘

트랙 C (sidecar)            ──→  트랙 A/B와 병행

트랙 D                       ── 보류 (트랙 A/B/C 완료 후 재개 가능)
```

트랙 A/B/C는 **상호 독립**이라 병렬 진행 가능.

### §4.2 milestone

| Milestone | 기간 | 목표 산출 | 동시 진행 트랙 |
| --- | --- | --- | --- |
| **M1: 진단 phase** | ~1주 | CLI Phase 1~3 진척 확인 + V3K-IMPL-3 진척 확인 + 유닛 테스트 720건 실패 분석 | A/B 진단만 |
| **M2: 첫 cycle** | ~2주 | CLI Phase 1 (라이브러리 5개 노출) + V3K-IMPL-3 baseline | A.V3K-IMPL-3 + B.Phase 1 |
| **M3: 두 번째 cycle** | ~2주 | CLI Phase 2 (출력 표준화) + Phase F/G default-OFF parity 검증 evidence | A.#6+#7 parity + B.Phase 2 + C.sidecar |
| **M4: 세 번째 cycle** | ~2주 | CLI Phase 3 (설정관리/리포트) + #4 formula globals 통합 | A.#4 + B.Phase 3 |
| **M5: V3K 백테스트 트랙 closure** | ~1주 | 트랙 A 모든 항목 default-OFF 100% 검증 evidence | A closure |
| **M6: 사용자 결정 시점** | - | 트랙 D 재개 여부 + 일정 결정 | (사용자 결정) |

총 예상: ~8주 (백테스트 트랙 + CLI 트랙 완전 진행, 트랙 D 제외)

### §4.3 우선순위 매트릭스

| 우선순위 | 작업 | 이유 |
| --- | --- | --- |
| 🔥🔥🔥 | M1 진단 phase | 어디서 이어갈지 정확히 알아야 다음 결정 가능 |
| 🔥🔥 | CLI Phase 1 첫 서브커맨드 노출 (`optimize` 또는 `db`) | 빠른 가시 산출 + 사용자 경험 개선 |
| 🔥🔥 | V3K-IMPL-3 백테스트 학습 DB hook smoke 재실행 | 본 PC 환경에서 작동 확인 (페이지 1 closure 후 보강 가능) |
| 🔥 | 유닛 테스트 720건 중 실패 418건 분석 | 코드 품질 baseline 확보 |
| 🔥 | Phase F/G default-OFF parity 결과 evidence 산출 | 향후 트랙 D 재개 시 baseline |
| 보조 | sidecar 토글 메커니즘 정리 | 트랙 D 재개 시 사용 |

---

## §5. 진행 순서 권장

### §5.1 즉시 시작 (M1 진단 phase)

본 master plan commit 직후 4건의 진단 작업 병렬 가능:

1. **CLI 확장 plan Phase 1~3 진척 진단** — 2026-03-24 plan 작성 후 2개월 동안 어디까지 진행됐는지 확인. 서브커맨드 노출 현재 19개에서 변동 여부, 출력 표준화 진척, 설정관리/리포트 CLI 존재 여부.
2. **V3K-IMPL-3 (백테스트 학습 데이터) 진척 진단** — `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` 본체 + scripts 작성 상태 + 실행 evidence 존재 여부.
3. **유닛 테스트 진단** — `pytest` 실행 + 720건 중 실패 418건의 카테고리 분류 (import 실패 / 환경 의존 / 기능 결함 등).
4. **`_v3k_sidecar/` 구조 진단** — 현재 토글 파일 + writer/reader 인터페이스 + 운영 vs 백테스트 측 read path 분리 확인.

M1 산출: 4건 진단 보고서 → 다음 cycle(M2) 우선순위 확정.

### §5.2 M2 첫 cycle 진입 조건

- M1 4건 모두 완료
- 사용자가 첫 작업 선택 (CLI Phase 1 vs V3K-IMPL-3 vs 다른 항목)
- 작업별 P-lane plan 작성

---

## §6. 검증 기준

### §6.1 매 commit 단위 (기존 audit suite 유지)

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db .omx/reports _v3k_sidecar
```

### §6.2 트랙 A 단위 (백테스트 강화)

| 항목 | 통과 기준 |
| --- | --- |
| #2 production learning DB read | 백테스트가 기준일 이전만 read + leakage 0건 + feature flag OFF 시 결과 동일 |
| #4 formula globals | feature flag OFF 시 기존 결과 동일 + ON 시 V3 globals 노출 확인 |
| #6 Phase F parity | matrix 100건 sample + parity ±0% (default-OFF) |
| #7 Phase G parity | matrix sample + parity ±15% + benchmark ±20% (default-OFF) |

### §6.3 트랙 B 단위 (CLI 확장)

| 항목 | 통과 기준 |
| --- | --- |
| Phase 1 | 라이브러리 5개 모두 `stom_backtest <subcmd> --help` 출력 + JSON 출력 + 유닛 테스트 PASS |
| Phase 2 | 모든 서브커맨드 JSON/UTF-8/버전 일관 출력 + 유닛 테스트 PASS |
| Phase 3 | 설정관리 + 리포트 CLI 신규 + 유닛 테스트 신규 |

---

## §7. 보류 트랙 재개 조건 (트랙 D)

다음 4건 모두 충족 시점에 트랙 D 재개 가능:

1. **사용자 명시 재개 의사 표시** (canonical phrase 발급)
2. **트랙 A 백테스트 default-OFF parity 검증 완료** (`backtest_v3k_phase_f_parity.py`, `backtest_v3k_phase_g_parity.py` PASS evidence)
3. **24h monitoring window 새로 진입 가능 시점**
4. **F1 cutover ralplan iteration 5 합의 종결** (Architect APPROVE + Critic APPROVE)

이 4건이 충족된 시점에 `6e8e23d0` F1 ralplan Planner v1을 baseline으로 iteration 2부터 이어간다.

---

## §8. Scope guard

| # | 항목 | 보장 |
| ---: | --- | --- |
| 1 | Kiwoom runtime mutation | 0건 |
| 2 | LS direct dependency | 0건 |
| 3 | operating `_database/` write | 0건 (트랙 D 보류) |
| 4 | `_database_v3k_shadow/` 구조 변경 | 0건 (read-only 사용만) |
| 5 | `_v3k_sidecar/` 토글 ON 발급 | 0건 (트랙 C는 read/write 메커니즘만, ON 활성화 안 함) |
| 6 | order/account API 호출 | 0건 |
| 7 | V3K USER_ACK env durable 발급 | 0건 |
| 8 | feature flag default-ON 전환 | 0건 |
| 9 | F6 산식 변동 | 트랙 A 항목별 +25%p 가능 (실측치는 cycle별 확정) |

본 master plan + 트랙 A/B/C 진행 시점 전체에 위 9건 guarantee.

---

## §9. preparation-first §3 정합

| §3 허용 | 본 plan |
| --- | --- |
| docs 추가 | ✅ master plan 1건 |
| approval packet 작성 | ✅ §7 보류 트랙 재개 조건 |
| 진단 작업 read-only | ✅ M1 4건 |

| §3 금지 | 본 plan |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| live connect/login | ❌ 0건 |
| feature flag default-ON 전환 | ❌ 0건 |
| LS Securities 직접 의존 추가 | ❌ 0건 |
| cutover script `--apply` 실행 | ❌ 0건 (트랙 D 보류) |

→ P-lane 적격.

---

## §10. 다음 인계 (M1 진단 phase 진입)

본 plan commit 직후 진행 가능한 첫 작업 4건은 §5.1에 명시. 다음 cycle은 진단 보고서 산출 후 사용자 결정으로 시작.

### §10.1 권장 진단 commit 순서

| 순서 | 작업 | 산출 |
| ---: | --- | --- |
| 1 | CLI Phase 1~3 진척 진단 | `docs/update_log/2026-05-XX_cli_phase_progress_diagnosis.md` |
| 2 | V3K-IMPL-3 진척 진단 | `docs/update_log/2026-05-XX_v3k_impl3_backtest_learning_progress.md` |
| 3 | 유닛 테스트 720건 실패 진단 | `docs/update_log/2026-05-XX_unit_test_failure_categorization.md` |
| 4 | sidecar 메커니즘 진단 | `docs/update_log/2026-05-XX_v3k_sidecar_mechanism_audit.md` |

각 진단 commit은 독립적이고 read-only이므로 병렬 또는 순차 진행 가능.

### §10.2 M2 진입 trigger

- 4건 진단 보고서 commit 완료
- 사용자가 M2 첫 작업 선택 (CLI Phase 1 첫 서브커맨드 vs V3K-IMPL-3 baseline 등)
- 작업별 P-lane plan 작성 시점에 M2 진입

---

## §11. 관련 문서

- `docs/update_log/2026-05-22_v3k_midcourse_review_backtest_cli_prioritization.md` (본 plan의 동반 검토 보고서)
- `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md` (V3K mission)
- `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` (8개 기능군 지도)
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` (P-lane/A-lane 정책)
- `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (CLI 확장 plan, 트랙 B baseline)
- `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` (Phase B 본체, 트랙 A baseline)
- `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md` (F5 본체)
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (F1 cutover 본체, 보류)
- `docs/plans/2026-05-22_v3k_f1_db_cutover_deliberate_ralplan_plan.md` (F1 ralplan Planner v1, 보류)
- `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json` (페이지 1 closure evidence)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-BACKTEST-CLI-PRIORITIZATION-MASTER-PLAN` 섹션)
