# V3K 백테스트 트랙 — 5개 분야(②③④⑥⑦) 순차 진행 master plan

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `272fff6b` (D2 V3K-IMPL-3 진단 직후) |
| 본 plan 정체성 | 트랙 A (백테스트 강화)의 5개 분야(②③④⑥⑦)를 순차 진행하는 master plan |
| 동반 dashboard | `docs/update_log/2026-05-22_v3k_progress_dashboard_korean.md` |
| 상위 master plan | `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` |
| 코드 변경 | 0건 (plan 정본화만) |
| 위험도 | **낮음** — 5개 분야 모두 백테스트 영역 + default-OFF + read-only |

---

## §0. TL;DR

```text
8개 분야 중 ①(운영 DB 전환, 매매 영향 큼) 제외하고 ②③④⑥⑦ 5개 분야를 순차 진행.
추천 순서: T1=⑥ → T2=⑦ → T3=② → T4=④ → T5=③
총 누적 예상: 약 2~3시간 (백테스트 영역, 매매 영향 0건)
각 단계별 산출은 evidence 또는 진단 보고서로 commit 분리.
```

---

## §1. baseline

- 8개 분야 중 ⑤ 100% 완료, ⑧ 영구 보존
- ① 보류 (사용자 결정, commit `ed5b2e11`)
- 잔여 6개 (②③④⑥⑦) 중 본 plan은 5개 분야 순차 진행 master

| 분야 | 현재 | 본 plan 단계 | 산출 |
| ---: | ---: | --- | --- |
| ② 학습 데이터 백테스트 read | 85% | T3 | F5 027-5 registry 등록 |
| ③ 화면 설정 저장 (사이드카) | 75% | T5 | 진단 + 진행 plan |
| ④ 수식 전역값 공유 | 50% | T4 | 진단 + 진행 plan |
| ⑥ 분석기 7종 백테스트 검증 | 30% | T1 | parity evidence |
| ⑦ 마이크로 엔진 백테스트 검증 | 30% | T2 | parity + benchmark evidence |

---

## §2. 분야 ① 보류 유지 확인

분야 ① (운영 DB 전환, F1 cutover)은 본 plan에서 진행하지 않는다. 이유:

- 운영 `_database/` 영구 변경 (CRITICAL risk)
- 사용자가 매매 시작 결심 전까지 미루기로 결정 (`ed5b2e11`)
- F1 ralplan Planner v1(`6e8e23d0`)까지의 자산은 보존, 재개 시 그대로 인용

본 plan은 ① 자산을 *건드리지 않는다*. ① 관련 scripts/plans/evidence 모두 read-only 인용만.

---

## §3. 5개 분야 순차 진행 순서 (T1 ~ T5)

### §3.1 T1 — 분야 ⑥ 분석기 7종 백테스트 검증 (이미 작성된 스크립트 실행)

**산출 의도**: `scripts/backtest_v3k_phase_f_parity.py` 실제 실행 → analyzer 7종 default-OFF parity evidence JSON 생성 → `.omx/reports/` 또는 `docs/evidence/`에 정본화.

| 항목 | 값 |
| --- | --- |
| 실행 script | `scripts/backtest_v3k_phase_f_parity.py` |
| 기존 evidence | `.omx/reports/v3k-prep-phase-f-parity.json` (어제 2026-05-15 21:14 작성) |
| 본 단계 목표 | 본 PC에서 재실행 + freshness 갱신 + analyzer 7종 default-OFF에서 매매 신호 변동 0% 확인 |
| 예상 시간 | ~30분 |
| 산출 commit | evidence 1~2건 + registry 1 섹션 |
| 진척률 영향 | ⑥ `30%` → `50%` (+20%p) |
| 매매 영향 | 0건 (default-OFF) |

**검증 기준**:
- `--apply` 또는 `--enable` 인자 사용 0건 (default-OFF 유지)
- parity ±0% (default-OFF에서는 기존 결과와 100% 동일이어야 함)
- 운영 `_database/` mtime 무변경
- LH1 invariant 보존

### §3.2 T2 — 분야 ⑦ 마이크로 엔진 백테스트 검증 + 벤치마크

**산출 의도**: `scripts/backtest_v3k_phase_g_parity.py` + `scripts/benchmark_v3k_phase_g_engine.py` (있다면) 실행 → microstructure engine default-OFF parity + benchmark evidence 생성.

| 항목 | 값 |
| --- | --- |
| 실행 script | `scripts/backtest_v3k_phase_g_parity.py` (+ benchmark) |
| 기존 evidence | `.omx/reports/v3k-prep-phase-g-parity.json`, `v3k-prep-phase-g-benchmark.json` |
| 본 단계 목표 | freshness 갱신 + parity ±15% + benchmark ±20% 정량 결과 |
| 예상 시간 | ~40분 |
| 산출 commit | evidence 2건 + registry 1 섹션 |
| 진척률 영향 | ⑦ `30%` → `50%` (+20%p) |
| 매매 영향 | 0건 (default-OFF) |

**검증 기준**:
- default-OFF에서 parity ±15% 이내
- benchmark ±20% 이내 (성능 회귀 허용 범위)
- 운영 DB / 사이드카 토글 변경 0건

### §3.3 T3 — 분야 ② F5 마지막 등록 정리 (가장 짧음)

**산출 의도**: F5 page 027의 5 step 중 027-1~027-4 완료, 027-5(registry 등록)만 미확인. 본 단계에서 registry 등록 확인 + 미등록 시 등록 commit.

| 항목 | 값 |
| --- | --- |
| 확인 대상 | `docs/CARRY_FORWARD_REGISTRY.md`에 `V3K-F5-PRODUCTION-LEARNING-DB-READ` 또는 유사 섹션 존재 여부 |
| 본 단계 목표 | F5 trail 완전 종결 |
| 예상 시간 | ~15분 |
| 산출 commit | registry 1 섹션 (필요 시) |
| 진척률 영향 | ② `85%` → `90%` (+5%p) |
| 매매 영향 | 0건 |

**검증 기준**:
- F5 027-1~027-4 evidence trail 인용 완전성
- read_production_learning_db() 메서드 동작 보장

### §3.4 T4 — 분야 ④ 수식 전역값 공유 진단 + 진행 plan

**산출 의도**: `strategy/v3k_formula_facade.py` 본문 분석 + 현재 진척 + 향후 진행 plan 작성.

| 항목 | 값 |
| --- | --- |
| 진단 대상 | `strategy/v3k_formula_facade.py` (formula globals facade) |
| 관련 plan 인용 | `docs/plans/2026-05-09_v3k_impl_5_formula_global_facade.md` (있는 경우) |
| 본 단계 목표 | formula globals의 백테스트 read path 진척 측정 + 잔여 작업 plan |
| 예상 시간 | ~30분 (진단) + ~15분 (plan 작성) |
| 산출 commit | 진단 보고서 + plan 1건 |
| 진척률 영향 | ④ `50%` baseline 확정 (실측치는 진단 결과에 따라 조정) |
| 매매 영향 | 0건 |

**검증 기준**:
- formula globals의 default-OFF 동작 확인
- runtime hook 통합 위치 식별
- 백테스트 측 read 경로 확인

### §3.5 T5 — 분야 ③ 화면 설정 사이드카 진단 + 진행 plan

**산출 의도**: `_v3k_sidecar/v3k_gui_settings.json` 메커니즘 + `strategy/v3k_gui_sidecar.py` 본문 + writer/reader 인터페이스 분석.

| 항목 | 값 |
| --- | --- |
| 진단 대상 | `strategy/v3k_gui_sidecar.py` + `_v3k_sidecar/` 디렉토리 |
| 관련 plan 인용 | `docs/plans/2026-05-14_v3k_page_078_preapproval_stop_condition_plan.md` (sidecar 정책) |
| 본 단계 목표 | 화면 설정 토글 메커니즘 진척 + 잔여 작업 plan |
| 예상 시간 | ~20분 (진단) + ~15분 (plan 작성) |
| 산출 commit | 진단 보고서 + plan 1건 |
| 진척률 영향 | ③ `75%` baseline 확정 (실측치는 진단 결과에 따라 조정) |
| 매매 영향 | 0건 |

**검증 기준**:
- 사이드카 토글 default-OFF
- writer/reader 인터페이스 정합
- 운영 사이드카 토글 ON 발급 0건 (본 단계에서는 메커니즘만 진단)

---

## §4. 의존성 그래프

```
T1 (⑥ 분석기 parity)   ─┐
                          ├─ 독립, 어느 순서든 OK
T2 (⑦ 엔진 parity)     ─┤
                          │
T3 (② F5 마무리)        ─┘   (T1/T2와 독립)

T4 (④ 수식 진단)        ─┐
                          ├─ 진단 후 plan 작성, T1~T3과 독립
T5 (③ 사이드카 진단)    ─┘
```

5개 단계 상호 독립. 권장 순서는 **시간 짧은 순 + 진척률 영향 큰 순**:

1. **T1 + T2 병렬** (가장 큰 진척률 변동, ~50분)
2. **T3** (가장 짧음, ~15분)
3. **T4** (진단 + plan, ~45분)
4. **T5** (진단 + plan, ~35분)

또는 사용자가 순차 1건씩 진행 의사면 T1 → T2 → T3 → T4 → T5 순서.

---

## §5. 일정 예상

| 단계 | 작업 | 누적 시간 |
| --- | --- | --- |
| T1 | 분석기 parity | 30분 |
| T2 | 엔진 parity + benchmark | +40분 (총 70분) |
| T3 | F5 마무리 | +15분 (총 85분) |
| T4 | 수식 진단 + plan | +45분 (총 130분) |
| T5 | 사이드카 진단 + plan | +35분 (총 165분 ≈ 2시간 45분) |

**완료 시점 (5개 분야 모두 진척)**: 약 2시간 45분 후. F6 진척률은 +50%p (분야 ⑥+⑦+② 합산) + 진단 baseline 2건.

---

## §6. 백테스트 트랙 단독 진척률 예상

본 plan 완료 후 F6 산식 재계산:

| 분야 | 현재 | T1~T5 후 |
| ---: | ---: | ---: |
| ② | 85% | **90%** |
| ④ | 50% | 50% (진단만, 진척률 변동 없음) |
| ⑥ | 30% | **50%** |
| ⑦ | 30% | **50%** |
| (기타) | - | - |

F6 산식 (#1~#7 카운트, #8 외):
- 현재: `(50+85+75+50+100+30+30)/700 = 420/700 = 60.0%` (실측 갱신 시)
- T1~T5 후: `(50+90+75+50+100+50+50)/700 = 465/700 = 66.4%`

→ **+6.4%p 예상 진척** (T1~T3 evidence 산출 시).

⚠️ master plan 53.6% 산정은 mid-checkpoint v4 §5.1 산식(#5 50% 시점) 기준이라 본 plan과 미세한 차이. v5 mid-checkpoint 정본화 시점에 통일 예정.

---

## §7. preparation-first §3 정합

| 허용 | 본 plan |
| --- | --- |
| docs 추가 | ✅ plan 1건 + 동반 dashboard 1건 |
| read-only smoke 실행 | ✅ T1~T2 parity script (default-OFF) |
| 진단 작업 read-only | ✅ T4/T5 |

| 금지 | 본 plan |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| `_database_v3k_shadow/` 구조 변경 | ❌ 0건 (read-only) |
| `_v3k_sidecar/` 토글 ON 발급 | ❌ 0건 (T5는 진단만) |
| feature flag default-ON 전환 | ❌ 0건 |
| LS direct dependency 추가 | ❌ 0건 |
| cutover script `--apply` 실행 | ❌ 0건 (분야 ① 보류 유지) |

→ P-lane 적격.

---

## §8. Scope guard

본 plan + T1~T5 전체 진행 시 다음 9건 guarantee:

| # | 항목 | 보장 |
| ---: | --- | --- |
| 1 | Kiwoom runtime mutation | 0건 |
| 2 | LS direct dependency | 0건 |
| 3 | operating `_database/` write | 0건 |
| 4 | `_database_v3k_shadow/` 구조 변경 | 0건 |
| 5 | `_v3k_sidecar/` 토글 ON 발급 | 0건 |
| 6 | order / account API 호출 | 0건 |
| 7 | V3K USER_ACK env durable 발급 | 0건 |
| 8 | V3K feature flag default-ON 전환 | 0건 |
| 9 | F1 cutover `--apply` 실행 | 0건 |

---

## §9. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db .omx/reports _v3k_sidecar
```

T1~T5 각 단계별 commit에서 위 audit suite 모두 통과해야 함.

---

## §10. 다음 인계

본 plan + dashboard 정본화 commit 직후 T1 (분야 ⑥ 분석기 parity) 진입 가능.

T1 진입 시:
1. `scripts/backtest_v3k_phase_f_parity.py` 본문 head 확인
2. 본 PC에서 실행 (default-OFF 가드 작동 확인)
3. evidence JSON 생성 + freshness 갱신
4. T06 smoke 패턴 따라 사후 검증
5. update_log + registry 등록 + commit

---

## §11. 관련 문서

- `docs/update_log/2026-05-22_v3k_progress_dashboard_korean.md` (동반 dashboard)
- `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (상위 master)
- `docs/update_log/2026-05-22_v3k_midcourse_review_backtest_cli_prioritization.md` (방향성 결정)
- `docs/update_log/2026-05-22_cli_phase_progress_diagnosis.md` (D1)
- `docs/update_log/2026-05-22_v3k_impl3_backtest_learning_progress.md` (D2)
- `scripts/backtest_v3k_phase_f_parity.py` (T1 실행 대상)
- `scripts/backtest_v3k_phase_g_parity.py` (T2 실행 대상)
- `strategy/v3k_analyzer_adapter.py` (분야 ②, ⑥ 핵심)
- `strategy/v3k_microstructure_engine.py` (분야 ⑦ 핵심)
- `strategy/v3k_formula_facade.py` (T4 진단 대상)
- `strategy/v3k_gui_sidecar.py` (T5 진단 대상)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-BACKTEST-5FIELDS-SEQUENTIAL-PLAN` 섹션)
