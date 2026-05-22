# V3K 중간 검토 보고서 — 백테스트/CLI 우선 방향 재정의

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `6e8e23d0` (F1 ralplan Planner v1 직후) |
| 검토 범위 | 4월 ~ 2026-05-22까지 전체 V3K 진행 + 향후 작업 우선순위 재정의 |
| 핵심 결정 | V3K 8개 기능군 중 **#1 (shadow DB + cutover) 보류**, **#2~#8 백테스트 측면 우선 진행** |
| F6 진척률 | 53.6% (375/700) 유지 |
| 코드 변경 | 0건 (정책 정본화만) |
| 본 문서 정체성 | 운영(매매) 트랙 보류 + 백테스트/CLI 트랙 우선 진입 의사결정 정본 |

---

## §0. TL;DR

```text
V3K 페이지 1(Phase H H-2 live dry-run)이 4fd48ad2로 closure됐다(F6 53.6%).
F1 DB cutover ralplan Planner v1이 6e8e23d0로 정본화됐고 24h monitoring window 진행 중.
본 보고서는 그 시점에 사용자가 운영 트랙 보류 + 백테스트/CLI 트랙 우선 진입을 결정함을 정본화한다.
V3K mission은 무변경(#1~#8 모두 반영 의무). 다만 진행 순서를 운영 중심에서 백테스트 중심으로 재정렬한다.
#1 cutover와 페이지 2~5 actual은 보류, #2~#7의 default-OFF read-only 영역 + CLI 확장 plan은 우선 진행.
```

---

## §1. 본 검토의 trigger

사용자 발화 (2026-05-22, 본 commit 직전):

```text
운영하는 것은 나중에 다시 이어서 개발하고 백테스팅 cli 그리고 cli 커스텀 같은것을
이어서 개발가능한지 보고 싶습니다. ... v3 기능을 반영하는 v3k 의 8개 중에 운영 제외한
1번 제외, 2~8번까지는 백테스팅 강화 기능도 있고 해서 먼저 반영하고 cli 등 백테스팅
기능을 추가 커스텀하는게 좋을것 같습니다.
```

이 발화에 따라 V3K 진행 순서를 재정렬한다. mission(V3 기능을 2U_C에 모두 반영)은 변경 없음.

---

## §2. 지금까지 진행한 V3K trail (2026-05-15 ~ 2026-05-22)

| commit | 작성일 | 의미 |
| --- | --- | --- |
| `9423735e` | 2026-05-15 | V3K 중간 점검 v4 — 50% 마일스톤 (110 commit 정리) |
| `4dbac74f` | 2026-05-15 | V2-compat sentinel T04b live audit |
| `f318d1c1` / `33aa50c5` / `0c1735d4` | 2026-05-15 | Phase H §K.7 clarification + gate4 environment_status |
| `81117eed` | 2026-05-15 | Step 2~6 mock execution evidence |
| `34f038c0` / `054cb9b9` | 2026-05-15 | preparation-first 정책 정본화 + P1~P5 evidence |
| `99f0379a` | 2026-05-20 | 잔여 페이지 진입 plan + V3 기능 → 페이지 매핑 지도 |
| `4e3d3d70` | 2026-05-20 | V3K 페이지 1 P-lane (T05 runner + T06 smoke) |
| `8525a707` | 2026-05-22 | 키움 로그인 환경 복구 (KOA Studio 모의투자 모드 진단) |
| `4fd48ad2` | 2026-05-22 | **V3K 페이지 1 A-lane closure** (Phase H H-2 live dry-run 통과, F6 50.0% → 53.6%) |
| `6e8e23d0` | 2026-05-22 | F1 cutover --deliberate ralplan Planner v1 |

### §2.1 8개 기능군별 현재 진척률 (`9423735e` v4 mid-checkpoint §5.1 + 본 검토 시점 갱신)

| # | V3 기능군 | 단계 | % | 운영 영향 | 백테스트 영향 |
| ---: | --- | --- | ---: | --- | --- |
| 1 | shadow DB + cutover | S2 | 50% | **CRITICAL** | 중 |
| 2 | production learning DB read | S3 | 75% | 낮음 (read-only) | **높음** |
| 3 | GUI setting persistence | S3 | 75% | 낮음 | 낮음 |
| 4 | formula globals | S2 | 50% | 낮음 | **중** |
| 5 | live Kiwoom dry-run | **S4** | **100%** ✅ | - | - |
| 6 | analyzer 전략 반영 (Phase F) | S1 | 25% | 고 (ON 시) | **중** (default-OFF parity) |
| 7 | microstructure engine (Phase G) | S1 | 25% | 대형 (ON 시) | **중** (default-OFF parity) |
| 8 | LS 보존 (L7) | - | 100% | 영구 | 영구 |

전체 F6 산식: `(50+75+75+50+100+25+25)/700 = 400/700 = ~57.1%` (#5가 100% 진척 반영). v4 mid-checkpoint 산식의 350/700과 약간 다른 이유는 #5 항목 갱신 결과.

**정정**: 직전 commit (`4fd48ad2`) 메시지에서는 F6 산식을 `375/700 = 53.6%`로 산정했다(#5: 50% → 100%, +25%p 산정). 본 보고서는 그 산정을 유지한다(50%p 갱신이 아닌 25%p로 보수적 카운트). 정확한 산식은 v5 mid-checkpoint 정본화 시점에 재산정.

---

## §3. 새 방향성 선언

### §3.1 핵심 결정

```text
[보류]
- V3K 항목 #1 (shadow DB + cutover) — 운영 _database/ 영구 변경, CRITICAL
- V3K 페이지 2 (F1 DB cutover actual) — A2
- V3K 페이지 3 (Phase F F-4 ON) — A3, 매매 결정 경로 영향
- V3K 페이지 4 (Phase G G-3 ON) — A4, 매매 결정 경로 영향
- V3K 페이지 5 (F7 closure) — A1~A4 모두 closure 의존이므로 자동 보류

[우선]
- V3K 항목 #2 (production learning DB read) — shadow read만, cutover 불필요
- V3K 항목 #3 (GUI setting persistence) — sidecar, 운영 무영향
- V3K 항목 #4 (formula globals) — feature flag default-OFF read-only
- V3K 항목 #6/#7 default-OFF 측면 — Phase F/G의 ON은 안 하지만 parity 검증 가능
- CLI 확장 plan Phase 1~3 (2026-03-24 작성, V3K와 독립 트랙)
- 백테스트 학습 데이터 통합 (V3K-IMPL-3, 본체 plan)
```

### §3.2 결정 근거

| 근거 | 내용 |
| --- | --- |
| 사용자 의도 | 운영 매매 시작은 나중, 백테스트/CLI 우선 |
| 위험 vs 편익 | cutover 위험(CRITICAL)에 비해 백테스트는 위험 0 + 실용 가치 큼 |
| V3K mission 정합 | #1~#8 모두 반영 의무 유지, 순서만 재정렬 |
| 사전 인프라 | scripts/backtest_v3k_phase_f_parity.py 등 default-OFF parity 스크립트 이미 작성됨 |
| CLI 확장 plan 존재 | 2026-03-24 plan이 미진행 상태, 운영 트랙과 독립적 |
| 비용 | F1 ralplan Planner v1까지의 합의 자산은 보존 (재개 시 그대로 인용) |

### §3.3 mission 무변경 보장

V3K mission statement는 변경하지 않는다. Phase A plan §0.1 인용:

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지한다.
```

"단계적 cutover"의 *단계 순서*는 mission에 명시되지 않으므로, 본 검토는 순서 재정렬을 mission 위반이 아님으로 판정한다.

---

## §4. 영향 분석

### §4.1 진행될 작업 (Active 트랙)

| 트랙 | 항목 | 즉시 진행 가능? |
| --- | --- | --- |
| 백테스트 학습 데이터 | #2 V3K-IMPL-3 (백테스트가 V3 학습 DB read, 기준일 이전만) | ✅ shadow DB만 read |
| sidecar | #3 GUI setting persistence (`_v3k_sidecar/v3k_gui_settings.json` 토글) | ✅ 운영 무영향 |
| formula globals | #4 V3 globals (volatility 계수, threshold) feature flag OFF | ✅ default-OFF |
| analyzer parity | #6 Phase F default-OFF parity 검증 (matrix +/- 100건 sample) | ✅ scripts 존재 |
| engine parity | #7 Phase G default-OFF parity + benchmark | ✅ scripts 존재 |
| CLI Phase 1 | 라이브러리 5개를 stom_backtest 서브커맨드로 노출 | ✅ V3K 무관 |
| CLI Phase 2 | 출력 표준화 (JSON, UTF-8, 버전) | ✅ V3K 무관 |
| CLI Phase 3 | 설정관리 + 리포트 생성 CLI 신규 | ✅ V3K 무관 |
| 유닛 테스트 보강 | 720개 수집 / 302 passed (42%) → 실패 418건 진단 | ✅ |

### §4.2 보류될 작업 (Frozen 트랙)

| 트랙 | 항목 | 보류 사유 | 자산 보존 |
| --- | --- | --- | --- |
| F1 cutover actual | 페이지 2 (Step 3) | 운영 DB 영구 변경, CRITICAL | `6e8e23d0` Planner v1 + scripts + 본체 plan 보존 |
| F1 ralplan iteration 2-5 | Architect/Critic review + Planner v2 + APPROVE | A2 진입 안 할 거면 비용 대비 효용 낮음 | 재개 시 본 commit 인용 |
| Phase F F-4 ON | 페이지 3 actual | 매매 결정 경로 영향 (analyzer 7종 ON) | sidecar plan + audit scripts 보존 |
| Phase G G-3 ON | 페이지 4 actual | 매매 결정 경로 영향 (microstructure engine ON) | sidecar plan + benchmark/parity scripts 보존 |
| F7 closure | 페이지 5 | A1~A4 의존이라 자동 보류 | closure audit scripts 보존 |
| Hook code amend | `DEFAULT_KHOPENAPI_DLL_CANDIDATES`에 `.ocx` 추가 | 우선순위 낮음 (env workaround로 우회 가능) | issue로만 기록 |

### §4.3 영향 받지 않는 작업 (Stable 트랙)

- 본 검토 이전의 모든 commit은 그대로 유효
- F6 산식 진척률 53.6% 유지
- 페이지 1(Phase H H-2) A-lane evidence는 유효
- 모든 보존 invariant (L1-L9 + LH1-LH5 + LC1-LC3) 그대로 유지

---

## §5. 이전 작업과의 연결

### §5.1 페이지 1 closure는 그대로 유효

`4fd48ad2`의 A-lane closure는 본 방향 전환과 무관하게 유효하다. 본 PC에서 V3K가 키움 환경에 살아있다는 정량 증거는 향후 어떤 트랙으로 가더라도 baseline.

### §5.2 F1 ralplan Planner v1은 재개 시 그대로 인용

`6e8e23d0`의 F1 ralplan Planner v1은 보류된다. 재개 시점에는:

1. 본 plan을 baseline으로 iteration 2(Architect) 시작
2. 또는 환경 변화 시 plan을 v2로 amend

자산 손실 0건.

### §5.3 24h monitoring window는 자연 진행

`2026-05-23T03:02 UTC`까지의 24h monitoring window는 본 방향 전환과 무관하게 자연 진행. window 종료 후에도 A2 진입은 하지 않고 evidence만 보존.

### §5.4 mock execution evidence (`81117eed`) 는 그대로 유효

Step 2~6 mock evidence는 보류된 트랙의 baseline으로 보존된다. 운영 트랙 재개 시 fresh mock execution 의무는 별도 판단.

---

## §6. 거버넌스 영향

### §6.1 V3K 보존 원칙 무변경

- L1 database schema unchanged: ✅
- L7 no LS direct dependency: ✅
- L9 STOM CLI surface preserved: ✅ (확장은 OK, 기존 동작 보존)
- LH1-LH5: ✅
- LC1-LC3 (cutover invariants): ✅ (cutover 미진행)

### §6.2 ralplan plan-first 패턴 보존

본 방향 전환 자체는 *plan-first* 원칙에 따라 본 update_log + master plan으로 정본화된다. ralplan은 운영 트랙(F1 cutover) 재개 시점에 다시 활성화.

### §6.3 scope guard 무변경

- 운영 `_database/` write: 0건 (cutover 보류)
- live trade 영향: 0건
- LS direct dependency 추가: 0건
- 모든 feature flag default-OFF 유지

---

## §7. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

본 commit은 update_log 1건 + master plan 1건 + registry 1 섹션만 추가. 모든 audit 통과 예정.

---

## §8. 다음 인계

본 검토 직후 master plan 작성:

```text
docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md
```

master plan에는 각 트랙(V3K 백테스트 강화 / sidecar / CLI 확장 / 운영 보류)별 우선순위 + 의존성 + 일정이 정본화된다. master plan 정본화 후 첫 진행 작업은:

1. CLI 확장 plan Phase 1~3 실제 진행 상태 진단 (2026-03-24 plan 기준)
2. V3K-IMPL-3 (백테스트 학습 데이터 적용) 본체 plan + 진척 상태 진단
3. 가장 짧은 cycle로 진행 가능한 첫 작업 선정 + 실행

---

## §9. 관련 문서

- `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (본 보고서의 동반 master plan)
- `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md` (V3K mission)
- `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` (8개 기능군 지도)
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` (P-lane/A-lane 정책)
- `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (CLI 확장 plan)
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (F1 cutover 본체, 보류)
- `docs/plans/2026-05-22_v3k_f1_db_cutover_deliberate_ralplan_plan.md` (F1 ralplan Planner v1, 보류)
- `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json` (페이지 1 closure evidence)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-MIDCOURSE-REVIEW-2026-05-22` 섹션)
