# 정책 amend — F1 cutover 보류 + Phase F/G ON 진행 정합 결정

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `66f316f6` (ai-controller promotion 직후) |
| supersede 대상 | `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` §2.4 일부 |
| 본 plan 정체성 | F1 cutover(페이지 2)를 보류한 채 페이지 3/4(Phase F/G ON) actual을 진행하는 정합 결정 plan |
| 코드 변경 | 0건 (정책 amend) |
| 위험도 | 중간 (페이지 3/4 매매 wiring 활성화 자체는 별도 commit 위험) |

---

## §0. TL;DR

```text
preparation-first plan §2.4 "Phase F F-4 ON은 F1 cutover + 7-day monitoring 없이 금지"
정책을 부분 떨어낸다.

근거:
- 페이지 3/4 Phase F/G ON은 sidecar 토글 + analyzer/engine 활성화로 동작 가능
- analyzer/engine은 shadow DB read 기반 → F1 cutover(운영 DB 전환) 불필요
- 사용자가 F1 cutover만 보류 + Phase F/G ON 진행 의향 명시 (2026-05-22)

새 정책:
- F1 cutover (페이지 2 A2): 보류 유지
- Phase F F-4 ON (페이지 3 A3): F1 cutover 없이도 진행 가능 (shadow DB read 기반)
- Phase G G-3 ON (페이지 4 A4): A3 closure + 24h monitoring 후 진행 가능
- F7 closure (페이지 5 A5): A3/A4 closure 후 진행 가능 (단 분야 ① 잔여 50%는 미완)
```

---

## §1. 배경

### §1.1 사용자 결정 (2026-05-22)

```text
"페이지 8개에서 1페이지 제외하고 모두 100%까지 될때까지 개발"
"A. ①(F1 cutover)만 제외 + 나머지 다 진행 (페이지 3/4 actual 실행 포함, 매매 wiring 활성화)"
```

분야 ① (F1 cutover)만 제외, 나머지 7개 분야 100%까지 가야 함. 그 중 분야 ⑥/⑦의 잔여 50%p는 페이지 3/4 actual 진행이 필수.

### §1.2 충돌하는 기존 정책

`docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` §2.4 인용:

```text
변경되지 않는 것:
- Phase H H-2 actual은 여전히 첫 actual execution gate다.
- F1 actual DB cutover는 Phase H H-2 actual + 24h monitoring evidence 없이 금지다.
- Phase F F-4 ON은 F1 cutover + 7-day monitoring evidence 없이 금지다.  ← 충돌
- Phase G G-3 ON은 Phase F closure 없이 금지다.
- F7 closure는 Step 2~5 actual closure 없이 금지다.
```

`Phase F F-4 ON은 F1 cutover ... 없이 금지` 조항이 본 amend로 떨어진다.

---

## §2. 기술적 가능성 검증

### §2.1 Phase F F-4 ON이 F1 cutover 없이도 가능한가?

`scripts/audit_v3k_phase_f_gate2_execution.py` + `docs/plans/2026-05-14_v3k_page_080_phase_f_gate2_execution_plan.md` §Scope 인용:

```text
Out of scope:
- No DB cutover
- No KHOPENAPI connect/login
- No Phase G/H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency
```

즉 페이지 3 (Phase F F-4 ON)은 **이미 plan §Scope에 "No DB cutover" 명시**. 즉 F1 cutover 없이 진행 가능하도록 *원래 설계됨*.

다만 §Scope의 "No live order/exit wiring"도 명시. 이건 사용자가 결정한 "매매 wiring 활성화"와 충돌. 해석:

- page 080 §Scope의 "No live order/exit wiring"은 *page 080 자체의 scope* (게이트2 실행만)
- 사용자 의도 "매매 wiring 활성화"는 페이지 3 actual의 *완전 실행*까지 포함
- 즉 페이지 3은 sidecar 토글 활성화로 시작 + analyzer 매매 wiring은 *후속 commit*

본 amend는 그 후속 commit까지 진행할 수 있도록 허용.

### §2.2 Phase G G-3 ON도 동일

`docs/plans/2026-05-14_v3k_page_081_phase_g_gate3_execution_plan.md` §Scope:

```text
Out of scope:
- No DB cutover
- ...
```

마찬가지로 F1 cutover 불필요 설계.

### §2.3 분야 ⑥/⑦ 100%의 의미

- 분야 ⑥ 100% = analyzer 7종이 매매 결정 경로에 wiring됨 + parity 검증
- 분야 ⑦ 100% = microstructure engine이 매매 결정 경로에 wiring됨 + benchmark + parity
- 둘 다 shadow DB read로 동작 가능

다만 *V3K 학습 데이터*가 운영 _database/로 옮겨지지 않은 상태이므로:
- 학습 데이터 read 경로는 shadow DB 기반
- analyzer/engine은 shadow DB의 학습 데이터를 read해서 매매 결정에 사용
- 운영 DB는 그대로 V2 schema 유지 (cutover 미실행)

---

## §3. 새 정책 (본 amend 후)

### §3.1 A-lane 순서 amend

```text
[변경 전]
A1 (Phase H H-2)  →  A2 (F1 cutover)  →  A3 (Phase F)  →  A4 (Phase G)  →  A5 (F7)

[변경 후]
A1 (Phase H H-2) ✅  →  [A2 F1 cutover 보류]
                         ↓
                       A3 (Phase F)  →  A4 (Phase G)  →  A5' (F7 부분 closure)
```

### §3.2 A5' 정의 (부분 closure)

기존 A5 F7 closure는 A1~A4 모두 closure를 요구. 본 amend로 A5'를 정의:

- A5' = 분야 ② ③ ④ ⑤ ⑥ ⑦ ⑧ 100% closure
- 분야 ① (F1 cutover) 50% 상태 유지 명시
- F6 진척률 산식: `(50 + 100*6) / 700 = 650/700 = 92.9%` (분야 ① 50%, 나머지 100%)
- 100% 만점은 분야 ① cutover 진행 시점에 별도 A5'' 추후 closure

### §3.3 보존 invariant

| invariant | 변경 |
| --- | --- |
| L1 database schema unchanged | ✅ 보존 (cutover 미실행) |
| L7 LS direct dependency 0건 | ✅ 보존 |
| L9 STOM CLI surface 보존 | ✅ 보존 |
| LH1 Kiwoom 주문/청산 경로 무변경 | ⚠️ **부분 떨어냄** — Phase F/G ON 시 analyzer/engine output이 매매 결정에 참여 |
| LH2~LH5 | 본 amend와 무관 |
| LC1-LC3 (cutover invariants) | ✅ 보존 (cutover 미실행) |

### §3.4 LH1 부분 떨어냄 정합

LH1 원래 정의: "Kiwoom 주문/청산/계좌/체결 처리 경로 코드 무변경".

본 amend에서 LH1 부분 떨어냄:
- "코드 무변경"은 유지 (trade/, utility/, Kiwoom_OpenAPI/, receiver/ 파일 변경 0건)
- 다만 sidecar 토글 + V3K analyzer/engine output을 *기존* 매매 결정 경로에서 *소비*하도록 활성화
- 코드 자체는 V2 그대로, 단 V3K hook 결과를 입력으로 받는 변화

즉 LH1의 *코드 invariant*는 유지, *매매 결정 영향* 측면은 의도적으로 변경.

---

## §4. 진행 조건 + 위험 완화

### §4.1 A3 (Phase F F-4 ON) 진행 조건

1. 사용자 명시 phrase: `I approve phase-f-f4-on-await-user-approval only`
2. `V3K_PHASE_F_USER_ACK=1` durable env
3. `_v3k_sidecar/v3k_gui_settings.json`의 `phase_f_live_order_exit_wiring=true` 변경
4. **24h monitoring window** (F1 cutover 사전 조건 없이도 진행)

### §4.2 A4 (Phase G G-3 ON) 진행 조건

1. A3 closure (24h monitoring 통과)
2. 사용자 명시 phrase: `I approve phase-g-g3-on-await-user-approval only`
3. `V3K_PHASE_G_USER_ACK=1` durable env
4. parity ±15% + benchmark ±20%
5. **48h monitoring window**

### §4.3 위험 완화

| 위험 | 완화 |
| --- | --- |
| analyzer/engine 활성화로 매매 신호 분포 변동 | parity matrix ±0% (default-OFF) + ±15% (ON) 사전 검증 (이미 evidence 산출됨) |
| operating _database/ write 발생 | sidecar 토글 변경만 (운영 DB 무변경 유지) |
| rollback 어려움 | `V3K_PHASE_F_DISABLE` + `V3K_PHASE_G_DISABLE` env로 즉시 OFF |
| 학습 데이터가 shadow DB이므로 read 일관성 | 모든 분야 ②/③/④의 read-only mode=ro 보장 |

---

## §5. preparation-first §3 정합

| §3 허용 | 본 amend |
| --- | --- |
| docs 추가 | ✅ amend plan 1건 |
| 정책 amend (mission 무변경) | ✅ §2.4 부분 떨어냄 |

| §3 금지 | 본 amend |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 (cutover 보류) |
| F1 cutover `--apply` | ❌ 0건 |
| LS direct dependency | ❌ 0건 |

→ amend 자체는 P-lane 적격. 후속 A3/A4 commit은 매매 wiring 활성화이므로 별도 ack 단계 필요.

---

## §6. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §7. 다음 인계

본 amend plan 정본화 + master plan 정본화 후 분야별 commit 순서:

1. 분야 ② (백테스트 evidence, 안전)
2. 분야 ③ (sidecar wiring 활성화, 매매 영향 약)
3. 분야 ④ (formula runtime hook, VERIFY-1A guard 떨어냄)
4. 분야 ⑥ (Phase F F-4 ON, 24h monitoring)
5. 분야 ⑦ (Phase G G-3 ON, 48h monitoring)
6. F7 부분 closure (A5' 선언)

총 6 commit + monitoring 누적 72h+ 필요.

---

## §8. 관련 문서

- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` (§2.4 amend 대상)
- `docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md` (master plan, 동반)
- `docs/plans/2026-05-14_v3k_page_080_phase_f_gate2_execution_plan.md` (페이지 3 본체)
- `docs/plans/2026-05-14_v3k_page_081_phase_g_gate3_execution_plan.md` (페이지 4 본체)
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (F1 cutover 보류 자산)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-F1-BYPASS-PHASE-FG-ON-POLICY-AMEND` 섹션)
