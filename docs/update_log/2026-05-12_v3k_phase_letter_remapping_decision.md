# V3K Phase letter 재명명 결정

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| 결정 trigger | mid-checkpoint(`3da98175`) §6 Phase letter 재해석 정합화 필요 |
| 영향 범위 | audit §8 정본 letter, 본 결정 이후 신규 phase plan letter naming |
| Phase A plan freeze 영향 | 없음 — 본 결정은 audit과 별도 메타 |

---

## 0. 결정 요지

```text
1. audit §8의 원안 Phase letter(A–G) 자체는 보존한다. audit 보고서는 freeze 정본.
2. 실제 진행에서 letter가 재해석/재사용된 경우는 본 문서가 매핑 정본이다.
3. 재해석된 letter는 미래 plan에서 정확한 letter로 재배치한다. 충돌은 금지.
4. 핵심: 실제 진행 Phase E0–E6 = GUI sidecar persistence. audit §8 Phase E = live Kiwoom dry-run은 letter `H`로 재배치한다.
```

---

## 1. 배경

audit `2026-05-10_2uc_v3k_full_feature_audit.md` §8 정본은 7개 phase를 다음과 같이 정의했다.

| audit §8 letter | 의미 |
| --- | --- |
| A | shadow DB rehearsal |
| B | read-only learning DB 검증 |
| C | GUI/settings 연결 |
| D | formula/global runtime 연결 |
| **E** | **live Kiwoom dry-run hook** |
| F | analyzer output 전략 반영 |
| G | V3 microstructure engine replacement |

실제 commit 흐름에서는 Page 019 (`87d7e696`) Phase E-0 runtime activation gap review가 6 후보를 위험도로 평가한 결과 **GUI setting persistence가 가장 안전**(Kiwoom live 영향 낮음, smoke 가능성 높음)하여 다음 단계로 선택되었다. 이때 letter `E`가 GUI sidecar에 재사용되었고, 그 결과 audit §8의 본래 Phase E(live Kiwoom dry-run)와 실제 진행 Phase E0–E6(GUI sidecar persistence)가 같은 letter를 공유하게 되었다.

mid-checkpoint `3da98175` §6에서 이 매핑이 명시되었으나, 미래 plan에서 letter 충돌을 차단하려면 letter 자체를 재배치하는 결정이 필요하다.

---

## 2. 결정안

### 2.1 audit §8 정본 letter 보존

audit 보고서는 freeze 정본이며 letter A–G를 변경하지 않는다. audit를 재인용하는 미래 plan은 원안 letter를 그대로 인용한다.

### 2.2 실제 진행 letter 매핑 정본

| audit §8 letter | audit §8 의미 | 실제 진행 letter | 실제 진행 의미 | 상태 |
| --- | --- | --- | --- | --- |
| A | shadow DB rehearsal | A | shadow DB rehearsal | 완료 (`1196946a`) |
| B | read-only learning DB 검증 | B | read-only learning DB 검증 | 완료 (`3eac14ec`) |
| C | GUI/settings 연결 | C1 + C2 | settings bridge + GUI wrapper + session-only preview | 완료 (~`5ed8cd2b`) |
| D | formula/global runtime 연결 | D | formula/global 경계 + dry-run + runtime hook 보류 | 부분 완료 (~`0d8ac586`) |
| **E** | **live Kiwoom dry-run hook** | **H** (신규 letter) | live Kiwoom dry-run hook (미진행) | letter 재배치 |
| F | analyzer output 전략 반영 | F | 동일 의미 (미진행) | 의미 정합 |
| G | V3 microstructure engine replacement | G (G-1/G-2/G-3 분해 권장) | 동일 의미 (미진행) | 의미 정합 |
| — | (audit에 없음) | **E** (실제 진행 letter) | GUI sidecar persistence design (E0–E6) | letter 신규 도입 |

### 2.3 신규 letter 도입 사유

**Letter H (live Kiwoom dry-run hook)**:
- audit §8 원안 letter E는 GUI sidecar에 의해 점유됨
- 알파벳 순서로 자연 다음은 H (A–G 다음)
- `H = Hot-runtime Kiwoom dry-run` 의미로 자기설명적
- audit §6.2 #5와 1:1 매핑 유지

**Letter E (GUI sidecar persistence)**:
- Phase A plan §0.2와 실제 진행에서 이미 letter E로 명명된 상태
- Page 019의 risk-driven 재선택 결과로 정당
- audit §6.2 #3 GUI setting persistence와 정합

### 2.4 letter 충돌 차단 규칙

1. 동일 letter가 두 다른 의미로 동시에 미진행 상태가 되는 것을 금지한다.
2. 새 phase plan은 본 문서 §2.2 표를 인용해 letter 충돌 여부를 사전 검증한다.
3. letter 재배치가 추가로 필요하면 본 문서를 amend하지 않고 별도 신규 letter remapping decision 문서를 작성한다.

---

## 3. 미래 phase plan letter convention

### 3.1 letter 명명 규칙

- **A–G**: audit §8 원안에 정의된 letter (단, E는 재해석됨)
- **H**: live Kiwoom dry-run hook (audit §8 원안 Phase E의 의미 이전)
- **H+**: H 이후 신규 도입되는 letter (예: 향후 DB cutover phase는 `I` 또는 별도 명명)
- **sub-phase**: phase letter 뒤에 숫자 (예: G-1, G-2, G-3)

### 3.2 phase plan 파일명 convention

```text
docs/plans/<YYYY-MM-DD>_v3k_phase_<letter>_<purpose>_plan.md
```

예시:
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md`
- `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md`
- `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md`

DB cutover처럼 audit §8에 없는 신규 phase는:
```text
docs/plans/<YYYY-MM-DD>_v3k_<topic>_plan.md
```
예시: `docs/plans/2026-05-12_v3k_db_cutover_plan.md`

### 3.3 phase plan 의무 인용

새 phase plan은 다음 4건을 의무 인용한다.

1. `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (audit 정본)
2. `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan, §0 미션 + §K 전환 지침)
3. `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` (mid-checkpoint)
4. **본 문서** (`2026-05-12_v3k_phase_letter_remapping_decision.md`)

---

## 4. audit §6.2 8 항목 letter 매핑 (재배치 후 최종)

| audit §6.2 # | 항목 | 책임 letter (재배치 후) | 현재 상태 |
| ---: | --- | --- | --- |
| 1 | shadow DB 생성 + cutover | A (rehearsal) + 신규 phase (cutover) | rehearsal 완료 / cutover 미진행 |
| 2 | production learning DB read | B (read-only) + 신규 phase (production read) | read-only 완료 / production 미진행 |
| 3 | GUI setting persistence | C1, C2, E0–E6 | E5 진행 중 |
| 4 | formula/global runtime hook | D | 부분 완료, runtime hook 보류 |
| 5 | live Kiwoom dry-run hook | **H** (재배치) | 미진행 |
| 6 | analyzer output 전략 반영 | F | 미진행 |
| 7 | V3 microstructure engine | G (G-1/G-2/G-3 분해 권장) | 미진행 |
| 8 | LS Securities 직접 의존 | (L7 invariant, 영구 금지) | 보존 |

---

## 5. 결정의 영향 범위

| 영향 대상 | 영향 |
| --- | --- |
| audit `2026-05-10_2uc_v3k_full_feature_audit.md` | 변경 없음 (정본 freeze) |
| Phase A plan `2026-05-10_v3k_phase_a_shadow_db_plan.md` | 변경 없음 (§K.7 freeze) — 단, §0.2 표의 Phase E "live Kiwoom dry-run hook" 라벨은 본 문서 §2.2에 의해 letter H로 재배치된다는 점을 미래 인용자가 인지해야 함 |
| mid-checkpoint `2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` | 변경 없음 (snapshot freeze) — §6 매핑 표는 본 문서의 전조 |
| 미래 phase plan | **본 문서 §2.2 표를 의무 인용해야 한다** |
| CARRY_FORWARD_REGISTRY | letter 재배치 항목을 후속 commit에서 별도 행으로 등록 가능 |

---

## 6. 관련 문서

- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (audit §6.2, §8)
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (§0.2, §K)
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` (§6 letter 매핑 전조)
- `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md` (letter 재사용 결정의 출처)
