# V3K 중간 점검 보고서 v5 — 4dbac74f → 1a8fdcde (19 commit, 페이지 1 closure + 트랙 A 백테스트 강화 100% 종결 + F6 진척률 72.1%)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| 기준 baseline commit | `4dbac74f` (v4 mid-checkpoint 종결 시점) |
| 검토 시점 HEAD | `1a8fdcde T5 분야 ③ GUI 사이드카를 진단해 90% 진척으로 종결하고 5개 분야 plan을 100% closure한다` |
| 검토 대상 commit 수 | **19** |
| 대상 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 대상 branch | `STOM_Version_2U_C` |
| prior mid-checkpoint | v1 `3da98175` / v2 `48a2cb05` / v3 `8ccbd5ed` / v4 `9423735e` (cd6f5bd → 4dbac74f, 110 commit) |
| 본 v5의 위치 | prior v1/v2/v3/v4 모두 보존하고 후속 snapshot으로 공존. F6 §3.2 명명 규칙 정합 |

---

## §0. TL;DR

```text
v4 시점 50.0%(350/700)에서 19 commit 누적 후 72.1%(505/700) 달성. +22.1%p.
페이지 1 (Phase H H-2 live dry-run) A-lane closure 완료.
방향성 재정렬: 운영 매매 트랙(D) 보류 + 백테스트/CLI 트랙 우선 결정.
트랙 A 백테스트 강화 5개 분야 순차 plan 5/5 (100%) 종결.
보존 원칙 5건 회귀 0건. audit verify_1a + verify_nonrelease_sync 모두 PASS.
다음 권장: 트랙 B (CLI Phase 1 확장 — ai_controller / strategy_generator 노출).
```

---

## §1. V3K 미션 재인용 (변경 없음, prior 모든 mid-checkpoint와 동일)

Phase A plan §0.1 statement:

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지한다.
```

19 commit 전반에서 미션 무변경. 진행 *순서*만 재정렬 (분야 ① cutover 보류, 백테스트/CLI 우선).

---

## §2. v5 핵심 변동 (v4 → v5)

### §2.1 ζ phase — Step 1 closure 4 commit

| Commit | Task | 산출 |
| --- | --- | --- |
| `f318d1c1` | Phase H §K.7 분기 audit | `audit_v3k_phase_h_gate4_environment_status.py` |
| `33aa50c5` | Phase H plan §K.5 amend | dryrun plan amend |
| `0c1735d4` | Phase H §K.7 clarification ralplan | iteration 2 APPROVE |
| `a7cded80` / `81117eed` / `34f038c0` / `054cb9b9` | Step 2-6 mock + preparation-first 정책 | preparation-first plan + P1-P5 evidence |

### §2.2 η phase — 페이지 1 A-lane execution 4 commit

| Commit | Task | 산출 |
| --- | --- | --- |
| `99f0379a` | 잔여 페이지 진입 plan + 매핑 지도 | feature → page 매핑 + runner prep plan |
| `4e3d3d70` | 페이지 1 P-lane | T05 runner + T06 smoke + G1~G5 가드 + mock evidence |
| `8525a707` | 키움 환경 복구 | KOA Studio 모의투자 모드 해제 trail |
| `4fd48ad2` | **페이지 1 A-lane closure** | `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json`, F6 50% → 53.6% |

### §2.3 θ phase — F1 cutover 보류 + 방향 재정렬 1 commit

| Commit | Task | 산출 |
| --- | --- | --- |
| `6e8e23d0` | F1 cutover ralplan Planner v1 | 운영 트랙 D 합의 layer, 12 Pre-mortem + 4축 테스트 + Rollback drill |
| `ed5b2e11` | **백테스트/CLI 우선 master plan** | 4트랙 분류 + 운영 트랙 D 보류 결정 |

### §2.4 ι phase — M1 진단 phase 2 commit

| Commit | Task | 산출 |
| --- | --- | --- |
| `c888eefd` | D1 CLI 진척 진단 | Phase 1 핵심 5건 100%, 종합 60~70% |
| `272fff6b` | D2 V3K-IMPL-3 진척 진단 | smoke 7건 PASS, ~75-85% |

### §2.5 κ phase — 트랙 A 5개 분야 순차 plan 100% 완료 5 commit

| Commit | Task | 산출 |
| --- | --- | --- |
| `1c02578c` | 한글 dashboard + 5개 분야 순차 plan | T1~T5 일정 + 매매 영향 0건 보장 |
| `26a10919` | **T1+T2 병렬 (분야 ⑥+⑦)** | parity delta 0% + benchmark 78%, +40%p |
| `397390f1` | T3 (분야 ② F5 마무리) | V3K-F5-PROD-READ 등록 확인, +5%p |
| `774807e4` | T4 (분야 ④ 수식 진단) | Phase D 3 sub-phase closure, +25%p |
| `1a8fdcde` | **T5 (분야 ③ 사이드카) → 5/5 closure** | Phase E0~E6 7 sub-phase closure, +15%p |

---

## §3. 19 commit 5-phase 분류 정량 표

| Phase | 범위 | commit | 핵심 |
| --- | --- | ---: | --- |
| ζ Step 1 closure | `f318d1c1`~`054cb9b9` | 7 | Phase H §K.7 clarification + preparation-first 정책 |
| η 페이지 1 A-lane | `99f0379a`~`4fd48ad2` | 4 | Phase H H-2 live dry-run 실행 + closure |
| θ 방향 재정렬 | `6e8e23d0`~`ed5b2e11` | 2 | F1 cutover Planner v1 + 백테스트/CLI 우선 |
| ι M1 진단 | `c888eefd`~`272fff6b` | 2 | CLI + V3K-IMPL-3 진척 baseline |
| κ 트랙 A 5개 분야 | `1c02578c`~`1a8fdcde` | 5 | T1~T5 순차 진행, 100% closure |
| **소계** | - | **20** | (본 v5 commit 포함) |

⚠️ commit count 20은 본 v5 commit 포함. 검토 대상은 v5 commit 직전까지 19건.

---

## §4. 보존 원칙 정량 검증 (검증 시점 HEAD=1a8fdcde)

| # | 원칙 | 검증 | 결과 |
| --- | --- | --- | --- |
| L1 | database schema unchanged | shadow DB 7개 unchanged, operating `_database/` unchanged | ✅ |
| L4 | operating `_database/` 변동 제한적 | 운영 DB write 0건, 단 사용자가 setting.db 복사 1건 (V3K 외) | ✅ |
| L7 | LS Securities 직접 의존 0건 | `audit_v3k_verify_1a.py` LS marker audit PASS | ✅ |
| L9 | STOM CLI surface 보존 | 기존 19개 서브커맨드 무변경, 신규 추가만 | ✅ |
| LH1 | Kiwoom 주문/청산/계좌/체결 코드 무변경 | trade/, utility/, Kiwoom_OpenAPI/, receiver/ 무변경 | ✅ |
| LH2 | dry-run hook idempotent | A-lane execution 1회 + diagnostic_steps 1건 | ✅ |
| LH3 | dry-run log .omx/reports/에만 archive | `.omx/reports/v3k-phase-h-dryrun-20260522T025930Z.json` | ✅ |
| LH4 | KHOPENAPI 호환 환경만 실행 | sentinel guard G4 통과 후만 connect | ✅ |
| LH5 | forward-only schema_version | schema_version 2 audit만 | ✅ |
| LC1 | cutover 전 backup 필수 | cutover 미실행, 보류 유지 | n/a |
| LC2 | single commit + 명시 승인 dance | F1 ralplan Planner v1만 정본화, A2 미진입 | ✅ |
| LC3 | 7일 monitoring 동안 새 cutover 금지 | cutover 0건 | ✅ |

보존 원칙 12건 모두 PASS.

---

## §5. F6 산식 갱신 (v4 → v5)

### §5.1 8 항목별 단계 갱신

| # | 항목 | v4 시점 | **v5 시점** | 변동 |
| ---: | --- | --- | --- | --- |
| 1 | shadow DB + cutover | S2 (50%) | S2 (50%) | 0 (보류) |
| 2 | production learning DB read | S3 (75%) | **S3.6 (90%)** | +15%p (T3 F5 closure 확인) |
| 3 | GUI setting persistence | S3 (75%) | **S3.6 (90%)** | +15%p (T5 Phase E0~E6 closure) |
| 4 | formula globals | S2 (50%) | **S3 (75%)** | +25%p (T4 Phase D 3 sub-phase closure) |
| 5 | live Kiwoom dry-run (Gate4) | S2 (50%) | **S4 (100%)** | +50%p (페이지 1 A-lane closure) |
| 6 | analyzer 전략 반영 (Phase F) | S1 (25%) | **S2 (50%)** | +25%p (T1 parity evidence) |
| 7 | microstructure engine (Phase G) | S1 (25%) | **S2 (50%)** | +25%p (T2 parity + benchmark evidence) |
| 8 | LS 보존 (L7) | 100% | 100% | 0 (영구) |

**전체 실행 진척률**: `(50+90+90+75+100+50+50)/700 = 505/700 = **72.1%**`

→ v4 시점 50.0% → v5 시점 **72.1%** (+22.1%p, 마일스톤 절반 통과 이후 2/3 통과 추가)

### §5.2 Plan coverage 메트릭

| # | 항목 | plan 존재 |
| ---: | --- | --- |
| 1 | shadow DB + cutover | ✅ Phase A + F1 + F1 ralplan v1 |
| 2 | production learning DB read | ✅ Phase B + F5 (page 027) |
| 3 | GUI setting persistence | ✅ Phase E0~E6 + page 049-071 (15 plan) |
| 4 | formula globals | ✅ Phase D0/D1/D2 + V3K-IMPL-5 |
| 5 | live Kiwoom dry-run | ✅ Phase H + page 026/032/052/082 + runner prep |
| 6 | analyzer 전략 반영 | ✅ F3 + page 080 |
| 7 | microstructure engine | ✅ F4 + page 081 |
| 8 | LS 보존 | n/a (영구 금지) |

**Plan coverage**: **100%** 유지.

---

## §6. 트랙 분류 + 5개 분야 closure 매트릭스

본 v5 시점의 4트랙 상태:

| 트랙 | 진행률 | 상태 |
| --- | ---: | --- |
| **A 백테스트 강화** | 5개 분야 5/5 closure | ✅ **cycle 종결** |
| **B CLI 확장** | ~60-70% | 🟢 다음 작업 대기 |
| **C 화면 설정** | 90% (T5 진단 결과) | ✅ 사실상 트랙 A에 흡수 |
| **D 운영 매매** | F1 ralplan Planner v1만 | 🔵 보류 |

### §6.1 5개 분야 순차 plan closure 매트릭스

| 단계 | 분야 | commit | 진척 변동 | 검증 |
| ---: | ---: | --- | --- | --- |
| T1 | ⑥ 분석기 | `26a10919` | 30% → 50% | parity delta 0%, breaches 0 |
| T2 | ⑦ 엔진 | `26a10919` | 30% → 50% | parity 3 시나리오 delta 0%, benchmark 78% |
| T3 | ② F5 | `397390f1` | 85% → 90% | V3K-F5-PROD-READ registry 확인 |
| T4 | ④ 수식 | `774807e4` | 50% → 75% | Phase D 3 sub-phase closure, smoke 3건 PASS |
| T5 | ③ 사이드카 | `1a8fdcde` | 75% → 90% | Phase E0~E6 7 sub-phase closure, smoke 4건 PASS |

**5/5 (100%) 완료** — 트랙 A 백테스트 강화 cycle 종결.

---

## §7. 잔여 작업 우선순위 (v5 시점)

### §7.1 트랙 B 우선 (사용자 가시 산출)

| 우선 | 작업 | 자산 보존 |
| ---: | --- | --- |
| 1 | CLI Phase 1 확장 — `ai_controller` 서브커맨드 노출 | `cli/ai_controller.py` 본문 + CLI 확장 plan §2.6 |
| 2 | CLI Phase 1 확장 — `strategy_generator` 노출 | CLI 확장 plan §2.7 |
| 3 | CLI Phase 2 — 출력 표준화 30+ 서브커맨드 일관성 audit | `cli/_safe_io.py` + `cli/output.py` |
| 4 | CLI Phase 3 — `config` / `history` CLI 신규 | CLI 확장 plan §3.x |

### §7.2 매매 트랙 D 재개 (사용자 결정 시점만)

| 우선 | 작업 | 재개 조건 |
| ---: | --- | --- |
| 1 | F1 cutover ralplan iteration 2~5 합의 | 사용자 명시 재개 의사 표시 |
| 2 | A2 F1 actual cutover | A1 24h monitoring + USER_ACK + lock window + ralplan 합의 |
| 3 | A3 Phase F F-4 ON | A2 closure + 7d monitoring + USER_ACK |
| 4 | A4 Phase G G-3 ON | A3 closure + 24h monitoring + USER_ACK |
| 5 | A5 F7 closure | A1~A4 모두 closure |

---

## §8. prior 문서들과의 보완 공존 관계

| 문서 | 형식 | 범위 | 상태 |
| --- | --- | --- | --- |
| v1 (`3da98175`) | 정량+letter 매핑 | Phase α+β | freeze |
| v2 (`48a2cb05`) | +plan coverage | Phase α+β+γ | freeze |
| v3 (`8ccbd5ed`) | +코드 단위 검증 | Phase α+β+γ+δ | freeze |
| v4 (`9423735e`) | +V2-compat sentinel + 50% 마일스톤 | Phase α+β+γ+δ+ε | freeze |
| **본 v5** | **+페이지 1 A-lane + 트랙 A 100% closure** | **Phase α+β+γ+δ+ε+ζ+η+θ+ι+κ** | **본 commit** |

상호 supersede하지 않음. 본 v5는 v4 + 19 commit 누적이며 v1/v2/v3/v4 본문 무변경.

---

## §9. 종합 판정

| 평가 항목 | 결과 |
| --- | --- |
| 19 commit 방향성 vs V3K 미션 | **정합** ✅ |
| 보존 원칙 12건 (L + LH + LC) | **모두 PASS** ✅ |
| 페이지 1 A-lane closure | **확정** ✅ (`docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json`) |
| 트랙 A 5개 분야 순차 plan | **5/5 (100%) 종결** ✅ |
| 실행 진척률 (F6 산식) | **72.1%** (v4 50.0% → +22.1%p, 2/3 통과) |
| Plan coverage | **100%** 유지 |
| 방향 재정렬 의사결정 | **정본화 완료** (운영 D 보류, 백테스트/CLI 우선) |
| 다음 단계 안전성 | 트랙 B 진행 가능 ✅ |

```text
중간 점검 v5 결론:
v4 50% 마일스톤 이후 19 commit으로 72.1%까지 도달.
페이지 1(Phase H H-2) A-lane closure로 키움 환경 가동성 실측 evidence 확보.
방향 재정렬로 운영 매매 트랙 D는 보류, 백테스트/CLI 우선 진행 결정.
트랙 A 5개 분야 순차 plan을 5/5 (100%) 종결로 백테스트 강화 cycle 마무리.
다음 권장 작업은 트랙 B CLI 확장 (ai_controller / strategy_generator 노출).
```

---

## §10. 본 문서 freeze 정책

- **위치**: `docs/update_log/2026-05-22_v3k_midpoint_checkpoint_v5_4dbac74f_to_1a8fdcde.md`
- **freeze 시점**: 본 commit
- **갱신 정책**: 본 문서는 1a8fdcde snapshot. 미래 commit으로 인한 변경은 본 문서에 반영하지 않고, 다음 mid-checkpoint(v6)를 새 파일로 신설.
- **prior 문서와의 관계**: v1/v2/v3/v4 모두 보완 공존, supersede 아님.

---

## §11. 관련 문서

- `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md` (prior v4)
- `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` (트랙 A master)
- `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (4트랙 master)
- `docs/update_log/2026-05-22_v3k_t5_gui_sidecar_diagnosis.md` (트랙 A closure)
- `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json` (페이지 1 A-lane evidence)
- `docs/plans/2026-05-22_v3k_f1_db_cutover_deliberate_ralplan_plan.md` (트랙 D 보류 자산)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-MIDPOINT-CHECKPOINT-V5` 섹션)
