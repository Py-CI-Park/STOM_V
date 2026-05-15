# V3K Phase H §K.7 clarification 분기 plan v2 (ralplan iteration 2 합의 정본)

> **ralplan 합의 이력**
> - iteration 1: Planner v1 (Option A rename) → Architect ITERATE_WITH_NOTES (Option B 권장) → Critic ITERATE (4 Required + 4 Optional)
> - iteration 2: Planner v2 (4 Rev + 4 Opt 흡수) → Architect `APPROVE` (1 minor optional) → Critic **APPROVE**
> - 합의 모드: short deliberation
> - 분기 근원: v3k-audit-v2-compat-sentinel plan v2 §0 Rev1 / §I.6 — Phase H §K.7 freeze 예외 사안을 본 plan으로 분기
> - 정책: historical script frozen 보존 + 신규 script 병렬 추가 (Option B). v1의 rename(Option A)은 §I.3에서 명시 거부
>
> **Status: ralplan APPROVE, T01–T03 실행 진행**
> /goal 직접 지시를 사용자 명시 승인 marker로 해석. baseline: v4 mid-checkpoint(9423735e) §7.1 1순위.

- 정본화: ralplan iteration 2 APPROVE 합의 산출물
- baseline: v1 (Planner iteration 1) — Architect ITERATE_WITH_NOTES + Critic ITERATE (4 Required / 4 Optional)

---

## §0. v1 대비 변경 요약

본 절은 v1 → v2 delta만 압축 기록한다. 전체 plan 구조는 §A–§L에서 baseline 형식 그대로 재서술.

| 분류 | v1 상태 | v2 변경 | 근거 |
|---|---|---|---|
| **T01 (audit script identity)** | rename `audit_v3k_phase_h_gate4_blocked_environment.py` → `..._environment_status.py` (Option A) | **historical script `audit_v3k_phase_h_gate4_blocked_environment.py` frozen 보존** + 신규 `audit_v3k_phase_h_gate4_environment_status.py` 병렬 추가 (Option B) | Rev1 (Architect 권장 + R1 dangling import 위험 origin 회피) |
| **§K amend 범위** | §K.5 / §K.6 / §K.7 3개 절 신설 | **§K.5 단일 절로 축소**. K.6/K.7은 본 plan 범위 외, 미래 분기 plan으로 위임 | Rev2 (Architect 권장 + amend surface 최소화) |
| **§B LH5 텍스트** | "audit artifact 일반에 적용" 식 비한정 표현 | "**`schema_version >= 2` audit artifact에만 적용. `schema_version == 1` historical (예: `b6327b30`)은 적용 범위 외, retroactive 재평가 금지**" forward-only 명시 | Rev3 |
| **V05** | (없음) | **자동 assertion 1건 추가**: `b6327b30` 시점 audit가 LH5 위반으로 잡히지 않는지 verification | Rev3 |
| **§E R1 mitigation** | "docs freeze 충돌 우려"만 산문 서술 | **4건 명문화**: (1) 영향 docs enumeration, (2) 각각 unfreeze 요건, (3) amend 후 freeze 재적용 시점, (4) freeze 충돌 0건 확인 절차 | Rev4 |
| **§D 검증 산식** | V01–V05 골격 | V01–V08로 확장: primary True/False 분기 검증 + LH5 forward-only assertion + historical script unchanged assertion 표 (O2) | O2 |
| **§E R2 cross-reference** | (없음) | "§K.5와 §K.1–K.4의 cumulative 동작 명시" 1-2 line 추가 | O1 |
| **§F Rollback** | (없음 또는 미흡) | "신규 script만 revert, historical 무영향" rollback 절차 신설 (sentinel v2 §F 스타일) | O3 |
| **§K Freeze 정책 (본 plan 자체)** | 미명시 | "본 plan 자체의 freeze 정책: ralplan iteration 2 Architect→Critic PASS 시점부터 §0 변경 요약 immutable" 명시 | O4 |
| **§I.3 Alternatives** | Option A rename만 본문 | **Option A 거부 / Option B 채택 / Option C 단일 script union type 거부 / Option D §K.5–K.7 3개 절 거부 4종 명시** | Rev1 + Rev2 |
| **§I.6 Follow-ups** | K.5–K.7 통합 amend | "K.6/K.7 amend는 미래 별도 분기 plan에서 처리" 명시. 본 plan은 K.5 단독 amend로 closure | Rev2 |
| **§A.2 Drivers** | D1/D2/D3 | D2 audit self-reject 해소 방법만 갱신 (rename → 신규 script 병렬 추가). Drivers 골격 보존 | Rev1 |

---

## §A. Principles & Decision Drivers

### §A.1 Principles (5개, v1 보존)

- **P1. Historical evidence immutability**: commit `b6327b30` 시점의 audit script(`audit_v3k_phase_h_gate4_blocked_environment.py`)는 historical audit trail로 frozen 보존. 본 plan에서 수정·rename·삭제 0건.
- **P2. Active polling은 신규 surface로 분리**: `primary_signal.exists` 분기 logic은 신규 script `audit_v3k_phase_h_gate4_environment_status.py`에 격리. historical script와의 책임 경계가 schema_version 1/2로 자연스럽게 갈린다.
- **P3. LH5 forward-only invariance**: lifetime invariant LH5는 `schema_version >= 2` audit artifact에만 적용. schema_version 1 historical artifact는 retroactive 재평가 대상 아님.
- **P4. §K amend surface minimization**: Phase H plan §K에 신설하는 절은 K.5 단독. K.6/K.7은 미래 별도 분기 plan으로 위임하여 본 amend의 영향 표면을 최소화.
- **P5. Docs freeze 충돌 0건**: page082 (`docs/update_log/2026-05-14_v3k_phase_h_gate4_blocked_environment.md`)와 registry V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading은 historical 보존. 본 plan amend로 인한 unfreeze 0건.

### §A.2 Decision Drivers (top 3, v1 보존 + D2 갱신)

- **D1. R1 dangling import 위험 origin 회피**: v1 rename(Option A)이 도입했던 dangling reference 발생 origin 자체를 신규 script 병렬 추가로 제거. historical script identity는 frozen.
- **D2. audit self-reject 해소 (방법 갱신)**: `primary_signal.exists`가 True인 환경에서 historical "blocked" naming의 audit가 self-reject되는 문제를, **신규 script 병렬 추가 + schema_version 1/2 분기**로 해소. v1의 rename 산식은 폐기.
- **D3. STOM_Version_2 release-ingress chain 정합**: 본 변경은 `V2 → 2U → 2U_C` chain의 release-ingress 정합을 깨지 않으며, Phase H plan §K.5 amend는 V2 ingress branch 단독 commit 산출물로 propagation.

---

## §B. Signal Architecture & Lifetime Invariants

### §B.1 audit script identity policy

- **historical script**: `scripts/audit_v3k_phase_h_gate4_blocked_environment.py` (commit `b6327b30`)
  - 정책: **frozen**. 본 plan 범위 내 변경 0건.
  - 책임: schema_version 1 audit artifact emit. archaeological lookup 용.
  - 호출 caller: 본 plan amend 후에도 historical references는 그대로 유효.
- **신규 script**: `scripts/audit_v3k_phase_h_gate4_environment_status.py` (신규)
  - 정책: active polling. `primary_signal.exists` 분기 logic 보유.
  - 책임: schema_version 2 audit artifact emit.
  - 분기 함수 2종:
    - `_assert_environment_unblocked()` — primary_signal.exists == True 분기. V2-compat 환경 가정 하에서 audit 동작.
    - `_assert_environment_blocked_or_pending()` — primary_signal.exists == False 분기. blocked/pending 동작 검증.

### §B.2 Lifetime Invariants LH1–LH5

| # | Invariant | 적용 범위 |
|---|---|---|
| LH1 | historical script identity는 frozen — 본 plan 및 미래 plan에서 변경 금지 | 모든 schema_version |
| LH2 | 신규 script `..._environment_status.py`는 primary_signal.exists 분기를 단일 진입점에서 처리 | schema_version 2+ |
| LH3 | audit JSON에 `audit_script_identity` 필드를 emit (값: `blocked_environment` 또는 `environment_status`) | schema_version 2+ |
| LH4 | `audit_script_identity` 값과 emit한 schema_version의 cardinality는 1:1 — historical은 v1+blocked, 신규는 v2+environment_status로 고정 | 모든 schema_version |
| **LH5** *(forward-only, Rev3 갱신)* | **`schema_version >= 2` audit artifact에만 LH5 invariant family를 적용한다. `schema_version == 1`인 historical audit (예: `b6327b30` 시점 결과)은 적용 범위 외이며 retroactive 재평가하지 않는다.** | schema_version >= 2 한정 |

### §B.3 §K.5와 §K.1–K.4 cumulative 동작 (Rev O1 cross-reference)

§K.5 신설 절은 §K.1–K.4의 cumulative 효과 위에 추가된다:
- §K.1–K.4가 정의하는 Phase H gate4 freeze 정책 위에, §K.5는 **audit script identity policy + primary_signal.exists 분기 logic + LH5 schema_version bump 의무**를 추가한다.
- §K.5는 §K.1–K.4 invariant를 깨지 않는다 (historical script frozen 정책 P1·LH1과 정합).

---

## §C. Task Flow

### §C.0 Task별 lane 표 (Rev1 + Rev2 재배치)

worktree 매핑:
- `C:/System_Trading/STOM/STOM_V` = `STOM_Version_2` branch (V2 root, release-ingress)
- `C:/System_Trading/STOM/STOM_V.wt-dev` = `STOM_Version_2U_C` branch (구현 lane)

| Task | 내용 | 실행 lane | commit lane | 사유 |
|---|---|---|---|---|
| **T01** *(Rev1 재작성)* | 신규 script `scripts/audit_v3k_phase_h_gate4_environment_status.py` **신설**. `_assert_environment_unblocked()` + `_assert_environment_blocked_or_pending()` 분기 함수 포함. historical script는 변경 0건 | 양쪽 (코드 검증) | `STOM_Version_2` (V2 ingress) | rename 산식 폐기 (Rev1). R1 dangling import 위험 origin 회피 |
| **T02** *(Rev2 축소)* | Phase H plan §K에 **§K.5 단일 절** amend. 통합 책임: (a) audit script identity policy, (b) primary_signal.exists 분기 logic 정책, (c) LH5 schema_version bump 의무 명시 | `STOM_Version_2` | `STOM_Version_2` | §K amend는 release-ingress branch 단독 commit |
| **T03** | 본 plan 자체를 `docs/update_log/2026-05-XX_v3k_phase_h_lh4_clarification_plan.md`로 promote (또는 산출물 trail로 첨부). commit 본문은 한국어 markdown | `STOM_Version_2` | `STOM_Version_2` | 분기 plan closure trail 보존 |

**참고**: v1 T01 "rename" task는 폐기. v1 T02/T03 "K.6/K.7 amend" task는 본 plan 범위 외로 분기 (미래 별도 plan).

### §C.1 진행 순서

T01 → T02 → T03. T01은 신규 script 신설이라 historical script와 격리되어 안전. T02 §K.5 amend는 T01 결과 반영 후 적용. T03 commit은 T01·T02 산출물을 한 commit 또는 분리 commit으로 트레일.

---

## §D. Verification (V01–V08, O2 확장)

| ID | 항목 | 산식 |
|---|---|---|
| **V01** | 신규 script 신설 확인 | `Test-Path C:/System_Trading/STOM/STOM_V/scripts/audit_v3k_phase_h_gate4_environment_status.py` PASS |
| **V02** | historical script unchanged | `git log --oneline -- scripts/audit_v3k_phase_h_gate4_blocked_environment.py` 가 본 plan commit 이후 변경 entry 0건. `git diff b6327b30 HEAD -- scripts/audit_v3k_phase_h_gate4_blocked_environment.py` 빈 diff |
| **V03** | primary_signal.exists == True 분기 (unblocked path) | mock test: `_assert_environment_unblocked()` 호출 시 audit가 `schema_version=2`, `audit_script_identity="environment_status"`, blocked-environment self-reject 0건으로 emit |
| **V04** | primary_signal.exists == False 분기 (blocked_or_pending path) | mock test: `_assert_environment_blocked_or_pending()` 호출 시 audit가 blocked 또는 pending 동작 emit. LH4 cardinality 위반 0건 |
| **V05** *(Rev3 신설)* | LH5 forward-only assertion — historical artifact 보호 | 자동 assertion: `b6327b30` 시점 audit artifact를 LH5 검사 입력으로 넣었을 때 위반 0건. `schema_version == 1` 검출 시 LH5 검사 skip. retroactive 재평가 0건 |
| **V06** | §K.5 amend 적용 확인 | `Select-String -Path docs/v3k-phase-h-plan-*.md -Pattern "^### K\.5"` 매치 1건. K.5 신설 절에 (a)(b)(c) 세 책임 모두 명시 |
| **V07** | docs freeze 충돌 0건 (R1 mitigation 자동 검증) | (1) `git diff STOM_Version_2 -- docs/update_log/2026-05-14_v3k_phase_h_gate4_blocked_environment.md` 빈 diff (page082 unchanged). (2) `git diff STOM_Version_2 -- docs/CARRY_FORWARD_REGISTRY.md` 결과에 V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading text 변경 0건 |
| **V08** | release preflight | `python scripts/verify_release_sync.py` → `release sync preflight passed` |

### §D.1 V03/V04 분기 검증 결정 룰

| `primary_signal.exists` | 호출되는 분기 함수 | audit 동작 |
|---|---|---|
| `true` | `_assert_environment_unblocked()` | V2-compat 환경 가정. blocked-environment self-reject 0건 |
| `false` | `_assert_environment_blocked_or_pending()` | blocked 또는 pending 동작 검증 |

---

## §E. Risk Register

| ID | Risk | Mitigation |
|---|---|---|
| **R1** *(Rev4 강화)* | docs freeze 충돌 — page082 / registry V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading 영향 | **4건 명문화**: (1) **영향 docs enumeration**: `docs/CARRY_FORWARD_REGISTRY.md` (V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading은 historical audit script 인용 검증 후 변경 없음 확인), `docs/update_log/2026-05-14_v3k_phase_h_gate4_blocked_environment.md` (page082, 변경 없음 — historical audit trail의 일부), Phase H plan §K (K.5 amend로만 영향). (2) **각각의 unfreeze 요건**: page082 frozen 유지 (Option B 채택으로 인용은 historical script 그대로). registry V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED는 historical heading으로 보존, 신규 entry는 본 plan §G 산출물로 추가. (3) **amend 후 freeze 재적용 시점**: §K.5 amend commit 후 Phase H plan freeze 재적용. (4) **freeze 충돌 0건 확인**: V07 자동 diff + V05 자동 assertion으로 봉인. |
| **R2** *(O1 cross-reference)* | §K.5 신설이 §K.1–K.4 invariant와 cumulative 모순 가능성 | §B.3에 cross-reference 1-2 line으로 cumulative 동작 명시. §K.5는 §K.1–K.4 위에 audit script identity + 분기 logic + LH5 bump 의무를 추가하며, P1·LH1과 정합 (historical script frozen) |
| **R3** | 신규 script가 historical script와 import cycle 또는 책임 중복 발생 | 신규 script는 historical script를 import하지 않는다. 책임 경계는 schema_version 1/2 / `audit_script_identity` 값으로 분리 (LH3·LH4). |
| **R4** | LH5 forward-only 명시 누락 시 historical artifact가 LH5 위반으로 retroactive 잡힐 위험 | §B.2 LH5 텍스트에 "`schema_version >= 2` 한정" 명시 + V05 자동 assertion. `schema_version == 1` 검출 시 LH5 검사 skip. |
| **R5** | 미래 §K.6 또는 §K.7 amend가 본 plan §K.5와 충돌 | 본 plan은 §K.5 단독 closure. K.6/K.7 amend는 미래 별도 분기 plan으로 위임 (Rev2). 본 plan §I.6 Follow-ups에 위임 사실 명시. |
| **R6** | 신규 script 명명이 historical script와 prefix 충돌 (`audit_v3k_phase_h_gate4_*`) | 의도된 prefix 공유. suffix(`_blocked_environment` vs `_environment_status`)로 식별성 확보. caller는 schema_version 1/2 또는 `audit_script_identity` 값으로 분기. |
| **R7** | sentinel v2 plan §I.6 "K.5–K.7" 문구가 본 plan §K.5 단독 closure와 충돌 | sentinel v2 §I.6 "K.5–K.7" 문구는 "K.5 단독"으로 재해석 (Rev2). K.6/K.7은 미래 별도 분기 plan으로 위임됨이 본 plan §I.6에 명시. |

---

## §F. Rollback (Rev O3 신설, sentinel v2 §F 스타일)

| ID | 시나리오 | 절차 |
|---|---|---|
| **F.1** | T01 신규 script commit 후 분기 함수에서 buguous behavior 발견 | 신규 script 파일만 revert (`git revert -- scripts/audit_v3k_phase_h_gate4_environment_status.py`). historical script 무영향. caller는 historical script로 자동 fallback (LH3 `audit_script_identity` 값으로 판별). |
| **F.2** | T02 §K.5 amend 후 §K.1–K.4와 cumulative 모순 검출 | §K.5 절만 revert. T01 신규 script는 유지 가능 (단, §K.5 amend 부재 시 caller가 분기 logic 사용처를 모름 → 신규 script 사용 보류 권고). historical script 무영향. |
| **F.3** | T03 promote 후 docs freeze 충돌 detect (V07 fail) | promote commit revert. page082·registry heading 원복. T01·T02 산출물은 freeze 충돌 0건 재확인 후 재promote. |

---

## §G. 산출물

- 코드: `scripts/audit_v3k_phase_h_gate4_environment_status.py` (신규, T01)
- 문서: 본 plan promote 위치 — `docs/update_log/2026-05-XX_v3k_phase_h_lh4_clarification_plan.md` (T03)
- amend: Phase H plan §K에 §K.5 단일 절 신설 (T02)
- registry entry: `docs/CARRY_FORWARD_REGISTRY.md`에 신규 entry 추가 (historical V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading은 보존, 신규 entry는 별도 heading로)

---

## §H. 커밋 message 골격 (한국어, CLAUDE.md 정책)

- T01: `V3K Phase H gate4 환경 상태 점검 신규 script를 병렬로 도입한다`
- T02: `V3K Phase H plan §K.5 절에 audit script identity 정책을 명시한다`
- T03: `V3K Phase H §K.7 clarification 분기 plan을 docs trail로 보존한다`

각 commit body는 한국어 markdown. CLAUDE.md 정책상 prefix-only 제목(`docs:`, `fix:`) 금지.

---

## §I. ADR — Alternatives, Decision, Consequences

### §I.1 Decision

V3K Phase H §K.7 clarification은 다음 3축으로 결정한다 (Option B + §K.5 단독 + LH5 forward-only):

1. **historical script `audit_v3k_phase_h_gate4_blocked_environment.py`는 frozen 보존**. 신규 script `audit_v3k_phase_h_gate4_environment_status.py`를 병렬 추가.
2. **Phase H plan §K에 §K.5 단일 절만 신설**. K.6/K.7은 본 plan 범위 외로 미래 별도 분기 plan에 위임.
3. **LH5 invariant는 `schema_version >= 2` audit artifact에만 적용**. schema_version 1 historical은 retroactive 재평가 금지.

### §I.2 Decision Drivers

§A.2 D1–D3 참조.

### §I.3 Alternatives considered (Rev1 + Rev2 명시)

| 대안 | 채택 여부 | 이유 |
|---|---|---|
| **Option A** — historical script rename `audit_v3k_phase_h_gate4_blocked_environment.py` → `..._environment_status.py` (Planner v1) | **거부** | R1 dangling import 위험 origin 도입. page082·registry V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading 인용이 깨질 수 있음. historical evidence immutability(P1) 위반 |
| **Option B** — historical frozen 보존 + 신규 script 병렬 추가 (Architect 권장) | **채택** | R1 dangling import 위험 origin 자체를 회피. page082·registry heading 인용은 historical script 그대로 보존. P1·LH1 정합. 책임 경계는 schema_version 1/2 / `audit_script_identity` 값으로 자연 분리 |
| **Option C** — 단일 script에 union type으로 분기 흡수 | 거부 | `primary_signal.exists` True/False 분기 logic을 historical script에 retrofit 시 schema_version 1 audit artifact가 새 logic 결과로 오염될 위험. P1 위반 |
| **Option D** — Phase H plan §K에 §K.5 / §K.6 / §K.7 3개 절 신설 (Planner v1) | **거부** | amend surface 과다. K.6/K.7은 현 시점 amend 필요성 불명확. §K.5 단독으로도 audit script identity + 분기 logic + LH5 bump 의무 3축이 통합 가능 (Rev2) |

### §I.4 Why chosen

Option B + §K.5 단독 + LH5 forward-only 조합 채택. 이유:

- historical evidence immutability(P1) 보존. R1 dangling import 위험 origin 자체 회피.
- 책임 경계가 schema_version 1/2로 자연 분리되어 caller 분기 logic이 명확 (LH3·LH4).
- §K amend surface가 §K.5 단독으로 최소화되어 §K.1–K.4와의 cumulative 모순 발생 가능성 축소 (R2).
- LH5 forward-only 명시로 historical audit artifact가 retroactive 재평가 대상에서 명시적으로 제외됨 (R4).
- 미래 §K.6/§K.7 amend 필요성이 구체화되면 별도 분기 plan으로 위임 (R5).

### §I.5 Consequences

- `+` historical script `audit_v3k_phase_h_gate4_blocked_environment.py` identity는 frozen 보존되어 archaeological lookup이 영구 안정.
- `+` 신규 script는 active polling + 분기 logic을 명확한 surface로 격리 — 미래 변경 시 historical과 격리되어 안전.
- `+` page082·registry V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading은 변경 0건, docs freeze 충돌 0건.
- `-` `scripts/audit_v3k_phase_h_gate4_*.py` 파일 2개 공존으로 인한 약간의 명명 중복. caller는 schema_version 또는 `audit_script_identity` 값으로 분기 판별 필요.
- `-` LH5 forward-only로 schema_version 1 audit artifact는 LH5 invariant family 보호 대상 외 — 단, P1에 의해 historical은 이미 frozen이라 실질 영향 0.

### §I.6 Follow-ups (Rev2 명시)

- **§K.6 amend는 본 plan 범위 외**. 필요성 구체화 시 별도 분기 plan으로 처리.
- **§K.7 amend는 본 plan 범위 외**. 필요성 구체화 시 별도 분기 plan으로 처리.
- sentinel v2 plan §I.6 "K.5–K.7" 문구는 "K.5 단독"으로 재해석. 본 plan amend 적용 후 sentinel v2 §I.6 footnote에 명시 권고.
- 신규 script `audit_v3k_phase_h_gate4_environment_status.py`의 unit test coverage 80% 이상 (mock-based scenario matrix 권장).
- audit JSON schema v3 변경 시 LH5 invariant family를 v3에도 forward 적용할지 별도 평가.

---

## §J. Q&A 골격

- **Q1.** historical script는 정말 변경 0건인가? → 그렇다. P1·LH1·V02로 봉인. `git diff b6327b30 HEAD -- scripts/audit_v3k_phase_h_gate4_blocked_environment.py` 빈 diff.
- **Q2.** caller는 어느 script를 호출해야 하나? → `primary_signal.exists` 분기 logic이 필요하면 신규 script(`..._environment_status.py`)를 호출. archaeological lookup 또는 schema_version 1 audit 재현이 목적이면 historical script.
- **Q3.** `audit_script_identity` 필드는 schema_version 1 audit에도 있나? → 아니다. LH3·LH4에 의해 `audit_script_identity`는 schema_version 2+ audit에만 emit. historical (v1)은 이 필드 부재 — caller는 부재 자체를 `blocked_environment` 식별자로 해석.
- **Q4.** LH5는 historical artifact를 보호하지 않는 것 아닌가? → 맞다. 단, P1·LH1에 의해 historical은 이미 frozen이라 추가 보호가 불필요. LH5는 forward-only 정책으로 schema_version 2+ artifact만 보호한다.
- **Q5.** page082 변경 없이 신규 entry는 어디에 추가하나? → `docs/CARRY_FORWARD_REGISTRY.md`에 신규 heading으로 별도 entry 추가. V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading은 historical로 보존.
- **Q6.** §K.5 amend가 §K.1–K.4와 모순되는가? → 아니다. §B.3 cross-reference에 cumulative 동작 명시. §K.5는 §K.1–K.4 위에 audit script identity + 분기 logic + LH5 bump 의무를 추가하며 P1·LH1과 정합.

---

## §K. Freeze 정책 (Rev O4 명시)

- 본 plan(v2) 자체의 freeze: ralplan iteration 2 Architect → Critic 재평가 PASS 시점부터 **§0 변경 요약 표는 immutable**.
- §B.2 LH1–LH5 invariant 골격은 commit 후 schema_version bump 없이는 변경 금지. 단, LH5의 forward-only 표현은 본 plan의 핵심 invariant로 immutable.
- §I.3 Alternatives 표(Option A/B/C/D 채택 여부)는 immutable.
- 분기 위임(K.6/K.7 미래 별도 plan)은 본 plan §I.6 명시 사항으로 immutable. 위임 철회 시 새 plan 작성 필요.

---

## §L. 관련 문서

- baseline v1 plan: Planner iteration 1 출력 (on-disk 부재, 메모리만)
- 분기 근원 plan: `.omc/plans/v3k-audit-v2-compat-sentinel-v2.md` §0 Rev1 / §C.0 / §I.6
- Phase H plan: `6e5cdf43` §K.1–K.4 (K.5–K.7 부재 — 본 plan amend로 K.5 신설)
- historical audit script: `scripts/audit_v3k_phase_h_gate4_blocked_environment.py` (commit `b6327b30`, frozen)
- page082: `docs/update_log/2026-05-14_v3k_phase_h_gate4_blocked_environment.md` (frozen)
- registry historical heading: `docs/CARRY_FORWARD_REGISTRY.md` § V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED (frozen)
- STOM Formal Update OS: `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Worktree strategy: `docs/WORKTREE_STRATEGY.md`
- Upstream sync strategy: `docs/UPSTREAM_SYNC_STRATEGY.md`

---

**END v2.** 본 plan은 ralplan iteration 2 Planner 출력이며, 다음 Architect → Critic 재평가 대상. 핵심 invariant V01(신규 script 신설)·V02(historical unchanged)·V05(LH5 forward-only)·V07(docs freeze 충돌 0건)을 정적 봉인.
