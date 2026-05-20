# V3K V3 → 2U_C 기능 → 페이지 매핑 단일 지도 plan

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-20 KST |
| baseline HEAD | `054cb9b9` (`STOM_Version_2U_C`) |
| prior 의존 문서 | `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md` §4, `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md` §5.1, `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` §1.2 |
| 본 plan 정체성 | 8개 V3 기능군과 잔여 5 페이지(Step 2~6)의 1:N 매핑을 단일 지도로 정본화한다. 기존 mid-checkpoint·goal_reset·preparation-first plan을 supersede하지 않고 보완 공존한다 |
| 코드 변경 | 0건 |
| Phase letter | 메타 (지도 문서) |

---

## §0. 문서 목적

V3 신기능 중 2U_C 미반영분과 그 활성화 페이지를 한 장으로 보여주는 *지도*를 정본화한다. 이전까지는 다음 두 문서를 별도로 인용해야 했다.

1. `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md` §4.1 — V3 포함 영역 8개
2. `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md` §5.1 — F6 산식 8개 항목별 단계

본 plan은 위 둘을 단일 표로 합치고 각 페이지에 어떤 V3 기능이 실제로 활성화되는지를 명시한다.

---

## §1. V3K 미션 재인용

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지한다.
```

---

## §2. 현재 진척률 요약

F6 산식 기준 **350 / 700 = 50.0%** (v4 mid-checkpoint `9423735e` 시점, 본 plan baseline `054cb9b9`까지 추가 코드 변경 0건이라 진척률 동일).

```text
[==========          ]  350 / 700
                          현재
```

---

## §3. 8개 V3 기능군 단계표 (지도)

| # | V3 기능군 | 현재 단계 | 만점 | 잔여 | 활성화 페이지 (남은 Step) | 비고 |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | shadow DB + cutover | 50% (S2) | 100% | 50%p | **페이지 2 (Step 3, F1 cutover)** | _database_v3k_shadow_ → _database_ 실제 전환 |
| 2 | production learning DB read | 75% (S3) | 100% | 25%p | Step 3 동반 closure | 학습 DB read-only 경로 확장 |
| 3 | GUI setting persistence | 75% (S3) | 100% | 25%p | sidecar 작업 (Phase F/G 동반) | `_v3k_sidecar/v3k_gui_settings.json` |
| 4 | formula globals | 50% (S2) | 100% | 50%p | Step 4 동반 | volatility 계수, threshold 등 runtime 노출 |
| 5 | **live Kiwoom dry-run (Gate4)** | 50% (S2) | 100% | 50%p | **페이지 1 (Step 2, Phase H H-2)** | 통과 의식 (기능 활성화 0) |
| 6 | analyzer 전략 반영 (Phase F) | 25% (S1) | 100% | 75%p | **페이지 3 (Step 4, F-4 ON)** | V3 analyzer 7종 활성화 |
| 7 | microstructure engine (Phase G) | 25% (S1) | 100% | 75%p | **페이지 4 (Step 5, G-3 ON)** | tick/orderbook 미시 엔진 |
| 8 | LS 보존 (L7) | 100% | 100% | 0 | 영구 보존 | LS 직접 의존 금지 |

`(현재단계 + 잔여) = 700` 합산 확인: `50+75+75+50+50+25+25+100 = 450? → 표 산정과 불일치 확인 → §3.1 정정 표 참조`

### §3.1 산정 정정

v4 mid-checkpoint §5.1 표는 #8을 100%로 보아도 700 만점 산식에서는 #1~#7만 카운트한다 (#8은 영구 금지 항목으로 산식 외).

```text
F6 산식 = (50 + 75 + 75 + 50 + 50 + 25 + 25) / 700 = 350 / 700 = 50.0%
```

#8은 보존 invariant이므로 진척률 산식에서 100%로 고정 카운트하거나 산식 분모를 700으로 두는 두 표기가 공존한다. 본 plan은 mid-checkpoint와 동일하게 350/700 = 50.0% 표기를 유지한다.

---

## §4. 페이지별 — 활성화되는 V3 기능 상세

### §4.1 페이지 1 (Step 2, Phase H H-2 live dry-run)

| 항목 | 값 |
| --- | --- |
| 들어있는 V3 기능군 | #5 live Kiwoom dry-run |
| 활성화 산출 | 사실상 0건. 키움 OCX 1회 connect/login 후 V3K preload diagnostic 1회 실행, 즉시 disconnect |
| 정체성 | 기능 활성화가 아닌 *환경 가동성 실측* |
| 페이지 2~5의 사전 증거 | 본 PC에서 V3K adapter/hook 안전 부팅 단 한 번 증거 확보 |
| 사전 조건 | 사용자 phrase + `V3K_PHASE_H_USER_ACK=1` + gate4 audit PASS + KHOPENAPI GUI 활성 |
| Monitoring | 24h |
| 산출 | `.omx/reports/v3k-phase-h-dryrun-<utc>.json` |

### §4.2 페이지 2 (Step 3, F1 DB cutover)

| 항목 | 값 |
| --- | --- |
| 들어있는 V3 기능군 | #1 shadow DB + cutover, #2 production learning DB read (동반 완성) |
| 활성화 산출 | V3 학습 DB schema가 운영에 실제 연결됨 |
| V3 학습 DB 포함 내용 | analyzer별 입력/출력/state 테이블, 백테스트 기준일 timestamp index, 종목별 학습 누적 데이터 |
| 현재 격리 위치 | `_database_v3k_shadow/` (7건), 운영 `_database/` (1176건)와 parity 검증만 완료 |
| Cutover 후 | 운영 경로가 V3 schema를 read하기 시작 |
| 사전 조건 | A1 closure + `V3K_CUTOVER_USER_ACK=1` + `--deliberate ralplan` + parity ±0 + transaction lock window |
| Monitoring | 7일 |
| 위험도 | 치명 (CRITICAL) |

### §4.3 페이지 3 (Step 4, Phase F F-4 ON)

| 항목 | 값 |
| --- | --- |
| 들어있는 V3 기능군 | #6 analyzer 전략 반영 |
| 활성화 산출 | V3 analyzer 7종이 백테스트/실시간 매매 결정 경로에 실제 연결 |
| sidecar source-of-truth | `_v3k_sidecar/v3k_gui_settings.json` `V3K_PHASE_F_ANALYZER_STRATEGY=true` |
| 사전 조건 | A2 closure + `V3K_PHASE_F_USER_ACK=1` + canonical phrase `I approve phase-f-f4-on-await-user-approval only` |
| Monitoring | 24h + parity ±0 |
| 위험도 | 고위험 |

활성화되는 V3 analyzer 7종:

| analyzer 모듈 | 역할 |
| --- | --- |
| `analyzer_candle_pattern` | 캔들 패턴 인식 (망치형, 도지, 엥걸핑 등) → 추세 전환 시그널 |
| `analyzer_volume_profile` | 가격대별 거래량 분포 → 지지/저항 자동 식별 |
| `analyzer_volume_spike` | 거래량 급증 감지 → 돌파/추세 시그널 |
| `analyzer_volatility_pattern` | 변동성 수축/확장 사이클 인식 → 분출 직전 포착 |
| `analyzer_volatility_stop_take` | 변동성 기반 동적 손절/익절 레벨 산정 (ATR 진화형) |
| `analyzer_microstructure` | 호가/체결 단위 미시 분석 (Phase G로 확장) |
| `analyzer_risk` runtime adapter | 종합 리스크 점수 + risk-adjusted 포지션 사이징 |

### §4.4 페이지 4 (Step 5, Phase G G-3 ON)

| 항목 | 값 |
| --- | --- |
| 들어있는 V3 기능군 | #7 microstructure engine |
| 활성화 산출 | tick/orderbook stream 기반 정밀 미시구조 분석층 |
| §4.3 analyzer_microstructure와의 차이 | 한 단계 깊은 층 — tick aggressive/passive 분류 + microprice + orderbook depth/imbalance + liquidity vacuum |
| sidecar source-of-truth | `_v3k_sidecar/v3k_gui_settings.json` `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=true` |
| preserved sidecar | `V3K_PHASE_F_ANALYZER_STRATEGY=true` 유지 |
| 사전 조건 | A3 closure + `V3K_PHASE_G_USER_ACK=1` + canonical phrase `I approve phase-g-g3-on-await-user-approval only` + parity ±15% + benchmark ±20% |
| Monitoring | 48h |
| 위험도 | 대형 |

### §4.5 페이지 5 (Step 6, F7 closure)

| 항목 | 값 |
| --- | --- |
| 들어있는 V3 기능군 | 없음 (메타 — V3K 미션 100% 선언) |
| 활성화 산출 | 기능 0건 |
| 산출 | `V3K-CLOSURE` registry entry + F6 진척률 100% 선언 + mission complete commit |
| 사전 조건 | A1~A4 closure + `audit_v3k_closeout_gate.py` PASS + final phrase |

---

## §5. 부분반영 항목의 흡수 경로

| # | 기능군 | 흡수 페이지 | 흡수 방식 |
| ---: | --- | --- | --- |
| 3 | GUI setting persistence | 페이지 3 / 4 sidecar 작업 | `_v3k_sidecar/v3k_gui_settings.json` 토글이 페이지 3/4의 source-of-truth로 기능 |
| 4 | formula globals | 페이지 4 동반 | microstructure engine 활성화 시 volatility 계수·threshold 등 runtime 노출 |

이 둘은 별도 페이지가 없고 페이지 3/4의 sidecar 작업으로 자동 흡수된다.

---

## §6. 보존 invariants

본 지도는 다음 L1~L9 + LH1~LH5 invariant를 보존한다 (Phase A plan §0.4, Phase H plan §B.2 인용).

- L1: 기존 `_database/` schema 무변경
- L7: LS Securities 직접 의존 금지
- L9: STOM CLI surface 보존
- LH1: Kiwoom 주문/청산/계좌/체결 처리 경로 코드 무변경
- LH2: dry-run hook은 connect/login 직후 한 번만 (idempotent)
- LH3: dry-run log는 `.omx/reports/v3k-phase-h-*.json`에만 archive
- LH4: KHOPENAPI 호환 환경 외 실행 거부 (sentinel guard)
- LH5: forward-only schema invariant (`schema_version >= 2`)

---

## §7. preparation-first plan §4.1 정합

본 지도 plan은 P-lane(준비 lane)에 속한다.

| Plan §3 허용 | 본 plan 포함 |
| --- | --- |
| docs 추가 | ✅ 본 plan 1건 |
| 운영 DB write | ❌ 0건 |
| live connect/login | ❌ 0건 |
| USER_ACK env var 발급 | ❌ 0건 |
| feature flag default-ON 전환 | ❌ 0건 |
| LS Securities 직접 의존 추가 | ❌ 0건 |

→ P-lane 적격.

---

## §8. 다음 인계

본 지도 plan이 정본화되면, 다음 P-lane 작업은 다음 plan을 baseline으로 진행한다.

```text
2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md
  → 페이지 1(Step 2) actual을 위한 T05/T06 runner 코드 작성
  → 본 지도 §4.1 참조
```

본 지도가 baseline이 되어 잔여 5개 페이지의 작업 plan들이 §4.x를 참조한다.

---

## §9. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar
```

`_database/`, `_database_v3k_shadow/`, `_v3k_sidecar/` 모두 무변경.

---

## §10. 관련 문서

- `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
- `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md`
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md`
- `docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md`
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md`
- `docs/plans/2026-05-14_v3k_page_080_phase_f_gate2_execution_plan.md`
- `docs/plans/2026-05-14_v3k_page_081_phase_g_gate3_execution_plan.md`
- `docs/CARRY_FORWARD_REGISTRY.md`
