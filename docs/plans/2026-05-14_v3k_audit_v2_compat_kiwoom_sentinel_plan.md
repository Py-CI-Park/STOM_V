# V3K Audit V2-compat Kiwoom Sentinel 보강 plan v2 (ralplan iteration 2 합의 정본)

> **ralplan 합의 이력**
> - iteration 1: Planner v1 → Architect ITERATE_WITH_NOTES (F1/F2/F3) → Critic ITERATE (6 Required Revisions + 4 Optional Improvements)
> - iteration 2: Planner v2 (6 Rev + 4 Opt 흡수) → Architect `APPROVE` → Critic **APPROVE**
> - 합의 모드: short deliberation
> - 합의 종결 시점에 본 문서를 v1 baseline(`add50a60`)을 supersede하는 ralplan-approved 정본으로 정착
> - 출처 발견 문서: `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (`cdd77093`)
>
> **Status: pending user approval**
> ralplan 합의 PASS. 본 plan의 T01–T04b 실행은 사용자 명시 승인 후 별도 commit cycle로 진행. 자동 실행 금지.

- 정본화: ralplan iteration 2 APPROVE 합의 산출물 (Planner v2 본문 + 합의 banner)
- baseline: v1 (`add50a60`) — Architect ITERATE_WITH_NOTES + Critic ITERATE(6 Required / 4 Optional)
- letter convention: F2(blocker) / F3(semantic) / Synthesis 1(primary S1 단독 산식) 흡수

---

## §0. v1 대비 변경 요약

본 절은 v1 → v2 delta만 압축 기록한다. 전체 plan 구조는 §A–§L에서 baseline 형식 그대로 재서술.

| 분류 | v1 상태 | v2 변경 | 근거 |
|---|---|---|---|
| **T05 (Phase H §K.7 freeze 예외)** | T05 task 본 plan 포함 | **본 plan에서 제거** → 별도 plan `2026-05-XX_v3k_phase_h_lh4_clarification_plan.md`로 분기 | Rev1 (F1 blocker — Phase H plan §K는 K.1–K.4만 존재) |
| **T01–T06 → T01–T05** | 6개 task | 5개로 축소 (T05 분리) | Rev1 결과 |
| **hook 반환 타입** | `Path \| None → Path \| str \| None` union 확장 | **`Path \| None` 그대로 보존** + 별도 메서드 `resolve_khopenapi_sentinel() → V3KSentinelResult \| None` 신설 | Rev2 (F2 blocker — `require_khopenapi_environment(self) -> Path` annotation 위반) |
| **`khopenapi_compatible` 산식** | "≥2/3 corroboration" | **primary S1 ActiveX ProgID 단독** = `primary_signal.exists` | Rev3 + Synthesis 1 (F3 blocker) |
| **audit JSON schema** | v1 평면 candidate list | **schema_version 2**: `khopenapi_primary_signal` + `khopenapi_corroborating_signals[]` + `khopenapi_corroboration_count` (기존 `candidates[]` 보존 — backward compat) | Rev3 |
| **§B LA1 텍스트** | "≥2/3 corroboration" 산식 서술 | "primary signal = ActiveX ProgID 단독. corroborating signals = OPENAPI_PATH 디렉터리 + legacy DLL" | Rev3 |
| **§E R4 mitigation** | "LA1이 '하나 이상'이라 의도된 동작" | **제거 후 재서술**: "primary signal 부재 시 corroborating만으로 compatible 판정 회피" + `khopenapi_compatible == primary_signal.exists` 자동 assertion | Rev4 |
| **§E R9 신설** | (없음) | "hook 반환 union type 도입으로 caller annotation 위반" — mitigation: Rev2의 별도 메서드 분리 | Rev4 |
| **§E R5** | Phase H plan §K.7 인용 | **§K.7 인용 5개소(§B/§E R5/§F F.3/§J Q4) 모두 제거 또는 footnote 강등** | Rev1 |
| **T04 본 PC 단일점** | 단일 task | **T04a (mock-based, 양쪽 lane CI) + T04b (본 PC live, commit 산출물 승격)** 로 분해 | Rev5 |
| **V03/V04** | V03/V04 단일 | **V03a/V03b/V04a/V04b** mapping | Rev5 |
| **§I Alternatives** | ≥2/3 corroboration만 본문 | **명시적 추가**: "≥2/3 corroboration — 거부(이유: primary/corroborating 정보 손실, S3 git source 정보량 0)" / "primary S1 ProgID 단독 antithesis — 채택(Synthesis 1)" | Rev6 |
| **§I Why chosen** | v1 산식 정당화 | **갱신**: "primary S1 단독 compatible 산식 + corroborating evidence 별도 emit (Synthesis 1)" | Rev6 |
| **§A.2 Drivers** | 2개 | "STOM_Version_2 release-ingress chain 정합" 1줄 **추가** (3개) | O3 |
| **helper dedup** | 산재 | `_active_x_progid_registered` / `_setting_base_openapi_path` 를 `strategy/v3k_kiwoom_sentinel.py` 공용 모듈로 추출 | O1 |
| **V05 PASS/SKIP 결정 룰** | 산문 서술 | **표 형태**: primary signal exists → SKIP, 부재 → PASS | O2 |
| **§0 F2 letter convention** | 미명시 | F2 letter convention 1줄 명시 본 절 상단 | O4 |

---

## §A. Principles & Decision Drivers

### §A.1 Principles (5개, v1 보존)

- **P1. 단일 truth source**: Kiwoom V2-compat 판정은 audit JSON의 `khopenapi_compatible` 1개 필드를 단일 truth로 사용한다. 다중 산식 병존을 금지한다.
- **P2. Primary/Corroborating 분리**: 채택 결정에 직접 영향을 주는 primary signal과 evidence 보존용 corroborating signals를 schema 레벨에서 분리한다.
- **P3. Schema evolution 추적성**: audit JSON 변경은 `schema_version` 정수 bump로 추적하고, 변경 이력을 docs로 보존한다.
- **P4. Annotation 보존**: 기존 hook caller (`require_khopenapi_environment` 등)의 type annotation을 깨는 시그니처 변경을 금지한다. 신규 emit 경로는 별도 메서드로 분리한다.
- **P5. Lane 격리 검증성**: 핵심 산식 로직은 mock 기반으로 양쪽 lane CI에서 재현 가능해야 하며, live host 검증은 commit 산출물로 보존한다.

### §A.2 Decision Drivers (top 3, O3 추가)

- **D1. F1/F2/F3 blocker 해소**: dangling reference / annotation 위반 / semantic 흐림 3종 blocker를 모두 닫는다.
- **D2. ≥2/3 corroboration 산식 거부**: primary/corroborating 정보 손실 + S3 git source 정보량 0인 산식을 폐기하고 Synthesis 1로 대체한다.
- **D3. STOM_Version_2 release-ingress chain 정합** *(O3 신규)*: 본 변경은 `V2 → 2U → 2U_C` chain의 release-ingress 정합을 깨지 않으며, V2 ingress branch 단독 commit 산출물로 propagation 한다.

---

## §B. Signal Architecture (LA1 재서술)

### §B.1 Signals

- **S1. ActiveX ProgID 등록**: `HKEY_CLASSES_ROOT\KHOPENAPI.KHOpenAPICtrl.1` registry key 존재 여부 → `_active_x_progid_registered()`
- **S2. OPENAPI_PATH 디렉터리**: `setting_base["OPENAPI_PATH"]` 디렉터리 + DLL 파일 수 → `_setting_base_openapi_path()`
- **S3. legacy DLL**: `C:/OpenAPI/khopenapi.dll` 등 legacy 절대경로 존재

### §B.2 LA1 — primary/corroborating 산식 (재서술, Rev3)

- **primary signal = S1 (ActiveX ProgID) 단독**
- **corroborating signals = S2 (OPENAPI_PATH 디렉터리) + S3 (legacy DLL)**
- **`khopenapi_compatible` = `primary_signal.exists`** (corroborating은 evidence emit 전용, 판정에 직접 영향 없음)
- corroborating signal은 모두 audit JSON에 emit하되, `khopenapi_corroboration_count`는 정보 표시용 필드일 뿐 결정 산식에 포함되지 않는다.

### §B.3 L1–L9 (v1 보존)

- L1. registry probe는 `winreg.OpenKey`로 READ-only 접근만 허용
- L2. `setting_base` lookup은 hook 외부 누수 금지
- L3. legacy DLL probe는 `Path.exists()`만 사용
- L4. 모든 signal probe는 예외를 잡아 `False` 반환 — audit 전체를 abort시키지 않는다
- L5. signal 결과는 `frozen=True` dataclass에 immutable 캡슐화 (P4)
- L6. ProgID 문자열은 `Path()`로 래핑하지 않는다 (Windows drive-letter 모호성 회피, Rev2)
- L7. audit emit 순서: primary → corroborating[] → corroboration_count → candidates[]
- L8. hook 진입점은 `resolve_khopenapi_path` (기존, `Path | None` 보존) + `resolve_khopenapi_sentinel` (신규)
- L9. 양쪽 lane (`V2` / `V2U_C`) CI에서 mock으로 4가지 scenario matrix 재현 가능해야 함

### §B.4 audit JSON schema v2 (Rev3)

```json
{
  "schema_version": 2,
  "phase": "V3K-PHASE-H-H1",
  "khopenapi_compatible": true,
  "khopenapi_primary_signal": {
    "source": "ActiveX ProgID",
    "path": "HKEY_CLASSES_ROOT\\KHOPENAPI.KHOpenAPICtrl.1",
    "exists": true
  },
  "khopenapi_corroborating_signals": [
    {"source": "OPENAPI_PATH directory", "path": "C:/OpenAPI", "exists": true, "dll_count": 3},
    {"source": "legacy DLL", "path": "C:/OpenAPI/khopenapi.dll", "exists": false}
  ],
  "khopenapi_corroboration_count": 1,
  "candidates": [
    {"source": "S1", "path": "...", "exists": true},
    {"source": "S2", "path": "...", "exists": true},
    {"source": "S3", "path": "...", "exists": false}
  ]
}
```

- `schema_version: 1 → 2` bump
- `candidates[]` 기존 필드 그대로 유지 (backward compat — 외부 reader 보호)

### §B.5 신규 dataclass (Rev2)

```python
from dataclasses import dataclass
from typing import Any, Literal

@dataclass(frozen=True)
class V3KSentinelResult:
    primary_kind: Literal["active_x_progid", "openapi_path_dir", "legacy_dll", "absent"]
    primary_path: str            # ProgID 문자열 또는 디렉터리/파일 절대경로
    primary_exists: bool         # primary signal 존재 여부
    corroborating_signals: tuple[dict[str, Any], ...]

    @property
    def compatible(self) -> bool:
        return self.primary_exists  # Synthesis 1: S1 단독 산식
```

> **caller routing 책임** (Architect optional 권고 1 흡수):
> 기존 caller (`require_khopenapi_environment`, `_assert_default_off_and_sentinel_contract` 등)는 `resolve_khopenapi_path() -> Path | None` 단독 사용. **신규 audit emitter만** `resolve_khopenapi_sentinel() -> V3KSentinelResult | None` 호출. T03 작업에서 caller routing을 명시 분리한다.

---

## §C. Task Flow & Lane Mapping

### §C.0 Task별 lane 표 (T05 제거 후 T01–T05)

| Task | 내용 | Lane | 종속 |
|---|---|---|---|
| **T01** | hook에 `resolve_khopenapi_sentinel() -> V3KSentinelResult \| None` 신규 메서드 추가. `resolve_khopenapi_path() -> Path \| None` 시그니처 **보존**. 기존 caller routing은 변경하지 않는다 (Architect 권고 1) | V2 ingress | — |
| **T02** | `strategy/v3k_kiwoom_sentinel.py` 공용 helper 모듈 신설: `_active_x_progid_registered()` / `_setting_base_openapi_path()` 추출 (O1) | V2 ingress | T01 |
| **T03** | audit emitter에서 schema_version 1 → 2 bump, `khopenapi_primary_signal` / `khopenapi_corroborating_signals[]` / `khopenapi_corroboration_count` 필드 emit. `candidates[]` 보존. audit emitter만 신규 메서드 호출, 기존 hook 진입점 caller는 무변경 | V2 ingress | T01, T02 |
| **T04a** | mock-based scenario matrix test: winreg + setting_base + tempfile mock으로 4 scenario(primary only / corroborating only / both / neither) 검증. 양쪽 lane CI에서 PASS | V2 + V2U_C | T01, T02, T03 |
| **T04b** | 본 PC live audit 실행. 결과 JSON에 `socket.gethostname()` sha256 첫 8자 + UTC timestamp 첨부. `docs/evidence/v3k-phase-h-env-host-<hash>.json`으로 commit 산출물 승격 | 본 PC | T04a |

**참고**: 기존 v1 T05 (Phase H §K.7 freeze 예외) 는 **본 plan에서 제거**되어 별도 plan `2026-05-XX_v3k_phase_h_lh4_clarification_plan.md` 로 분기됨 (Rev1).

### §C.1 진행 순서

T01 → T02 → T03 → T04a → T04b. T04a 까지는 mock 기반이므로 양쪽 lane CI에서 검증 가능, T04b만 본 PC 단일점이다.

---

## §D. Verification

| ID | 항목 | 산식 |
|---|---|---|
| **V01** | hook 시그니처 보존 | `inspect.signature(resolve_khopenapi_path).return_annotation == Path \| None` 자동 assertion |
| **V02** | 신규 메서드 export | `hasattr(hook, "resolve_khopenapi_sentinel")` 및 반환 타입 `V3KSentinelResult \| None` 확인 |
| **V03a** | mock scenario matrix (primary only) | S1=True, S2=False, S3=False → `compatible=True`, `corroboration_count=0` |
| **V03b** | mock scenario matrix (corroborating only) | S1=False, S2=True, S3=True → `compatible=False`, `corroboration_count=2` (R4 핵심) |
| **V04a** | mock scenario matrix (both) | S1=True, S2=True, S3=True → `compatible=True`, `corroboration_count=2` |
| **V04b** | mock scenario matrix (neither) | S1=False, S2=False, S3=False → `compatible=False`, `corroboration_count=0` |
| **V05** | gate4_blocked_environment audit | 아래 결정 룰 표 (O2) 참조 |
| **V06** | audit JSON schema | `schema_version == 2` 및 신규 3 필드 존재 + `candidates[]` 유지 |
| **V07** | `khopenapi_compatible == khopenapi_primary_signal.exists` invariant | Rev4 자동 assertion |
| **V08** | 본 PC live audit (T04b) | host hash + UTC timestamp 포함, `docs/evidence/`에 commit |

### §D.1 V05 PASS/SKIP 결정 룰 (O2 표)

| `primary_signal.exists` | gate4_blocked_environment audit 동작 |
|---|---|
| `true` | **SKIP** (V2-compat 환경이므로 blocked-environment gate 검사 불필요) |
| `false` | **PASS** (compatible=False 이므로 blocked 동작 검증해야 함) |

---

## §E. Risk Register

| ID | Risk | Mitigation |
|---|---|---|
| **R1** | winreg probe가 비 Windows 환경에서 ImportError | `try/except ImportError` 후 `False` 반환, L4 정책 |
| **R2** | `setting_base` lookup 시 환경 변수 누락 | `KeyError` 잡아 `False` 반환, audit 계속 |
| **R3** | legacy DLL 경로가 권한 제한 디렉터리 | `Path.exists()`만 사용, `os.access` 금지 |
| **R4** *(재서술, Rev4)* | primary signal 부재 시 corroborating만으로 compatible 판정 회피 실패 | `V07` 자동 assertion(`compatible == primary_signal.exists`) + V03b scenario test로 강제 검증 |
| **R5** *(§K.7 인용 제거, Rev1)* | (v1 R5 Phase H §K.7 freeze 예외 의존성) → **본 plan 범위 외, 별도 plan으로 분기** | 본 plan 본문에서 §K.7 인용 5개소 모두 제거 또는 footnote 강등 |
| **R6** | schema bump가 외부 reader 깨뜨림 | `candidates[]` 필드를 v1 형태 그대로 보존, `schema_version` 정수로 명시적 분기 가능하게 함 |
| **R7** | mock test가 실제 winreg API 동작과 괴리 | T04b live audit를 commit 산출물로 승격하여 실 환경 동작 trail 보존 (Rev5) |
| **R8** | helper 추출 시 import cycle | 신규 `strategy/v3k_kiwoom_sentinel.py`는 hook을 import하지 않고, hook이 helper를 import하는 단방향만 허용 |
| **R9** *(신규, Rev4)* | hook 반환 union type 도입으로 caller annotation(`require_khopenapi_environment(self) -> Path`) 위반 | **별도 메서드** `resolve_khopenapi_sentinel()` 로 분리. `resolve_khopenapi_path()` 시그니처 `Path \| None` 보존 |
| **R10** | 본 PC live audit가 단일점이라 재현 불가 | T04a mock matrix가 양쪽 lane CI를 cover, T04b는 audit trail 보존 목적 (Rev5) |

---

## §F. Rollback

| ID | 시나리오 | 절차 |
|---|---|---|
| **F.1** | T01–T03 commit 후 caller annotation 위반 발견 | T01 신규 메서드만 revert, audit emitter는 schema_version 1로 fallback (`candidates[]` 그대로 유지되므로 무해) |
| **F.2** | T04a mock matrix 4 scenario 중 1개라도 fail | T03 emitter revert, helper 모듈(T02) 유지. R9/Rev2 미달 시점이므로 신규 메서드만 disable |
| **F.3** *(§K.7 제거, Rev1)* | T04b live audit에서 primary/corroborating 불일치 발견 | T04b 결과 JSON commit revert. 본 plan 범위에서는 Phase H §K.7 freeze 예외를 **재인용하지 않는다** (해당 항목은 분기 plan에서 별도 처리) |

---

## §G. 산출물

- 코드: `strategy/v3k_kiwoom_sentinel.py` (신규, O1) + hook 변경 (T01) + audit emitter 변경 (T03)
- 테스트: `tests/strategy/test_v3k_kiwoom_sentinel.py` (T04a, 4 scenario matrix)
- 문서: 본 plan + audit JSON schema v2 ADR (§I)
- **commit 산출물 승격 (Rev5)**: `docs/evidence/v3k-phase-h-env-host-<hostname-sha256-8자>.json` — T04b live audit 결과, host identifier + UTC timestamp 첨부

---

## §H. 커밋 message 골격 (한국어, CLAUDE.md 정책)

- T01–T02: `V3K Kiwoom sentinel hook을 별도 메서드 경로로 분리한다`
- T03: `V3K audit JSON schema를 v2로 승격하고 primary/corroborating signal을 분리한다`
- T04a: `V3K sentinel 산식을 mock scenario matrix 4종으로 검증한다`
- T04b: `V3K Phase H live audit 결과를 host hash trail과 함께 보존한다`

각 commit body는 한국어 markdown. baseline 정책상 prefix-only 제목(`docs:`, `fix:`) 금지.

---

## §I. ADR — Alternatives, Decision, Consequences

### §I.1 Decision

V3K Kiwoom V2-compat 판정은 **primary S1 ActiveX ProgID 단독 산식** + **corroborating evidence 별도 emit** 으로 결정한다 (Synthesis 1).

### §I.2 Decision Drivers

§A.2 D1–D3 참조.

### §I.3 Alternatives considered (Rev6 명시)

| 대안 | 채택 여부 | 이유 |
|---|---|---|
| **≥2/3 corroboration 산식** (Planner v1) | **거부** | primary/corroborating 정보 손실, S3 git source 정보량 0, R4 mitigation 모순(v1) |
| **primary S1 ProgID 단독 antithesis** (Synthesis 1) | **채택** | F2/F3 blocker 동시 해소, annotation 보존, audit JSON에 corroborating evidence는 별도 emit하여 정보 손실 없음 |
| hook 반환을 `Path \| str \| None` union 확장 | 거부 | `require_khopenapi_environment(self) -> Path` annotation 위반 (F2 blocker), Path 래핑 시 Windows drive-letter 모호성 (Rev2) |
| T04 단일 본 PC task 유지 | 거부 | 양쪽 lane CI 재현 불가, audit trail 부재 (Rev5) |

### §I.4 Why chosen (갱신, Rev6)

primary S1 단독 compatible 산식 + corroborating evidence 별도 emit (Synthesis 1) 채택. 이유:

- `khopenapi_compatible` semantic이 단일 산식(`primary_signal.exists`)로 명확 (F3 해소)
- 기존 hook 시그니처 `Path | None` 보존, 신규 메서드 분리로 annotation 위반 회피 (F2 해소)
- corroborating signal은 audit JSON에 그대로 emit되어 정보량 손실 없음
- mock scenario matrix 4종으로 양쪽 lane CI 재현 가능 (Rev5)

### §I.5 Consequences

- `+` audit JSON consumer는 schema_version 2부터 명확한 primary/corroborating 분리 사용 가능
- `+` 기존 `candidates[]` reader는 그대로 동작 (backward compat)
- `-` audit JSON 크기 소폭 증가 (3 필드 추가)
- `-` 외부 reader가 schema_version 분기 로직 추가 필요 (단, candidates[] fallback 가능)

### §I.6 Follow-ups

- Phase H plan §K에 K.5–K.7 절 추가는 **별도 plan**으로 분리 (Rev1)
- audit JSON schema v3 후속 변경(예: signal weight 도입)은 본 v2 채택 후 검토
- `strategy/v3k_kiwoom_sentinel.py` 공용 helper의 unit test coverage 80% 이상 (O1 확장)

---

## §J. Q&A 골격

- **Q1.** `khopenapi_compatible`는 어떻게 결정되나? → `primary_signal.exists` (S1 ActiveX ProgID 단독). corroborating은 evidence 전용.
- **Q2.** v1 reader는 깨지나? → 아니다. `candidates[]` 보존 + `schema_version`으로 명시적 분기 가능.
- **Q3.** 본 PC가 아닌 환경에서는 어떻게 검증하나? → T04a mock scenario matrix 4종이 양쪽 lane CI에서 PASS.
- **Q4.** *(§K.7 제거, Rev1)* Phase H freeze 정책과의 관계? → 본 plan은 Phase H plan §K freeze에 영향 없음. Phase H §K.7 관련 사안은 별도 plan으로 분기됨.
- **Q5.** hook caller `require_khopenapi_environment(self) -> Path`는 안전한가? → 안전. `resolve_khopenapi_path()` 반환 타입이 `Path | None` 그대로 보존됨.

---

## §K. Freeze 정책

- 본 plan(v2) 자체의 freeze: ralplan iteration 2 Architect → Critic 재평가 PASS 시점부터 §0 변경 요약 표는 immutable.
- §B.4 audit JSON schema v2 구조는 commit 후 schema_version 3 bump 없이는 변경 금지.
- §B.5 `V3KSentinelResult` dataclass 필드 5개 (`primary_kind` / `primary_path` / `primary_exists` / `corroborating_signals` / `compatible` property)는 immutable. 신규 필드 추가는 schema_version bump 동반.
- T05 분기 plan은 본 plan의 freeze 정책과 독립.
- **본 plan v2는 사용자 명시 승인까지 `pending approval` 상태**. T01–T04b 실행 commit은 사용자 승인 후에만 진행.

---

## §L. 관련 문서

- baseline v1 plan: `add50a60` (git object)
- 발견 baseline: `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (`cdd77093`)
- Phase H plan: `6e5cdf43` §K.1–K.4 (K.7 부재 — Rev1 근거)
- 분기 plan (예정): `2026-05-XX_v3k_phase_h_lh4_clarification_plan.md`
- audit baseline: `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md`
- Phase A plan: `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (§0 미션 + §K 패턴)
- F2 letter convention: `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md`
- F6 산식: `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md`
- F7 closure procedure: `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md`
- STOM Formal Update OS: `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- Carry-forward registry: `docs/CARRY_FORWARD_REGISTRY.md`
- Worktree strategy: `docs/WORKTREE_STRATEGY.md`
- Upstream sync strategy: `docs/UPSTREAM_SYNC_STRATEGY.md`

---

**END v2 정본.** ralplan iteration 2 APPROVE 합의 산출물. 사용자 명시 승인 후 T01–T04b 실행 cycle 진입.
