# CLI Phase 1 확장 — ai-controller 서브커맨드 promotion 실행 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `3d71b09f` (v5 mid-checkpoint 직후) |
| 정책 plan | `docs/plans/2026-05-22_v3k_cli_ai_controller_promotion_plan.md` |
| 본 commit 정체성 | ai-controller 서브커맨드 promotion **실행 commit** |
| 코드 변경 | 3 파일 (docstring + SUBCOMMANDS + subcommands.py 라우터/핸들러) |
| 매매 영향 | 0건 |

---

## §0. TL;DR

```text
cli/ai_controller.py의 library-only 정책을 떨고 stom_backtest ai-controller 서브커맨드 9개 액션 노출.
LH1 보존 (trade/, utility/, Kiwoom_OpenAPI/ 무변경).
L9 보존 (기존 11개 서브커맨드 동작 무변경, 신규 1개 추가만).
audit 7건 모두 PASS — Kiwoom/runtime untouched + V3K feature flags default-OFF +
Forbidden artifact guard + LS dependency marker + verify-1a + gate4 + nonrelease_sync.
CLI 노출 검증: list-strategies / system-info 직접 실행 PASS.
기존 setting list 동작 보존 확인.
```

---

## §1. 변경 사항

### §1.1 `cli/ai_controller.py` docstring 갱신 (line 1-9 → 1-12)

기존:
```python
"""AI 백테스트 컨트롤러 — 통합 파사드.
...
주의:
- 현재는 `stom_backtest.py` 의 공식 서브커맨드가 아니라 Python API 성격의 모듈이다.
- shipped CLI 범위와 혼동하지 않도록 문서/계획서에서 library-only 로 구분한다.
"""
```

신규:
```python
"""AI 백테스트 컨트롤러 — 통합 파사드 + 공식 shipped CLI.
...
CLI 노출 (2026-05-22 promotion):
- `stom_backtest ai-controller <action>` 서브커맨드로 P0 9개 액션 노출.
- P0 노출: list-strategies / analyze-strategy / run / dry-run /
  get-history / get-best / create-strategy / delete-strategy / system-info.
- promotion plan: docs/plans/2026-05-22_v3k_cli_ai_controller_promotion_plan.md
"""
```

본문 코드 무변경.

### §1.2 `stom_backtest.py` SUBCOMMANDS 튜플 (line 42-46)

```python
SUBCOMMANDS = (
    'formula', 'strategy', 'discovery',
    'optimize', 'sweep', 'wfo', 'tune', 'db',
    'setting', 'report', 'runtime-preflight',
    'ai-controller',   # ← 추가
)
```

### §1.3 `cli/subcommands.py` 추가 사항

- **add_parser block** (db 직후, return 직전):
  - `ai-controller` 메인 + 9 액션 (list-strategies / analyze-strategy / run / dry-run / get-history / get-best / create-strategy / delete-strategy / system-info)
- **handle_subcommand 라우터**: `elif parsed.command == 'ai-controller': return _handle_ai_controller(parsed)`
- **신규 함수**:
  - `_emit_ai_result(result, output_format)` (line 1500~) — JSON/text 출력 헬퍼
  - `_handle_ai_controller(parsed)` (line 1512~) — 9 액션 분기 핸들러

---

## §2. 검증

### §2.1 정적 검증

```
python -m py_compile cli/ai_controller.py     : OK
python -m py_compile cli/subcommands.py        : OK
python -m py_compile stom_backtest.py          : OK
```

### §2.2 --help 검증

```
python stom_backtest.py ai-controller --help
```

기대 출력 (확인됨):
```
usage: stom_backtest ai-controller [-h]
    {list-strategies,analyze-strategy,run,dry-run,
     get-history,get-best,create-strategy,delete-strategy,system-info} ...
```

9 액션 모두 노출 확인.

### §2.3 핵심 액션 동작 검증 (직접 실행)

```
python stom_backtest.py ai-controller list-strategies --format json
→ {"status": "ok", "strategies": {"stockbuy": [...], "stocksell": [...]}}

python stom_backtest.py ai-controller system-info --format json
→ {"status": "ok", "system": {"cpu_count": 64, "memory_total_gb": 254.64, ...},
    "recommended_engines": {"recommended": 8, ...}}
```

두 액션 모두 exit code 0 + JSON 출력.

### §2.4 기존 동작 보존 (L9)

```
python stom_backtest.py setting list --format text
→ === STOM Settings (271 keys) === (정상 출력)
```

기존 11개 서브커맨드 동작 무변경 확인.

### §2.5 V3K audit suite

```
python scripts/audit_v3k_phase_h_gate4_environment_status.py: PASS
python scripts/audit_v3k_verify_1a.py --base 9423735e        : PASS
  - Kiwoom/runtime untouched audit passed
  - V3K feature flags default-OFF audit passed
  - Forbidden artifact guard passed
  - LS dependency marker audit passed
  - v3k verify-1a audit passed
python scripts/verify_nonrelease_sync.py                      : PASS
git diff --check                                              : 가짜 양성 (실제 trailing whitespace 0건, binary 검증)
```

---

## §3. 보존 invariant

| invariant | 보장 |
| --- | --- |
| L1 database schema unchanged | DB read-only 액션만 (list / system-info) |
| L7 LS direct dependency 0건 | 본 commit LS import 0건 |
| L9 STOM CLI surface 보존 | 기존 11 서브커맨드 무변경, ai-controller 추가만 |
| LH1 Kiwoom 주문/청산 경로 무변경 | trade/, utility/, Kiwoom_OpenAPI/, receiver/ 변경 0건 (verify_1a PASS) |
| LH2~LH5 | 본 commit과 무관 (Phase H 영역) |

---

## §4. 진척률 영향

```
이전 (3d71b09f v5 시점):
  트랙 B (CLI 확장) 약 60-70%
  서브커맨드 노출 30개+ (subcmd + sub-action)

이후 (본 commit):
  트랙 B 약 70-75% (+5-10%p)
  서브커맨드 노출 39개+ (+9 ai-controller actions)
```

F6 산식 단독에는 직접 영향 없음 (트랙 B는 V3K 8개 분야 외 별도 트랙). v5 mid-checkpoint의 72.1%는 유지.

---

## §5. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 (plan + update_log) | ✅ |
| CLI 신규 추가 (기존 동작 보존) | ✅ ai-controller subcommand |
| docstring 갱신 (정책 명시화) | ✅ |
| read-only smoke 실행 | ✅ list-strategies / system-info |

| 금지 | 본 commit |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| feature flag default-ON 전환 | ❌ 0건 |
| LS direct dependency 추가 | ❌ 0건 |
| Kiwoom runtime mutation | ❌ 0건 (LH1 PASS) |

→ 코드 측 P-lane 적격.

---

## §6. Scope guard

- 코드 변경 3 파일 (docstring + SUBCOMMANDS + subcommands.py)
- Kiwoom runtime mutation 0건
- operating `_database/` write 0건
- LS direct dependency 0건
- V3K USER_ACK env 0건
- feature flag default-ON 0건
- 기존 서브커맨드 동작 변경 0건

---

## §7. 후속 작업

1. P1 액션 노출 (sweep / optimize / walk-forward / discover-* / analyze-results / ...)
2. P2 액션 노출 (auto-discover-* / research-strategy-once / compare-discovery-history / ...)
3. ai-controller 유닛 테스트 신규 (`tests/unit/test_ai_controller_cli.py`)
4. v5 mid-checkpoint에 트랙 B 진척 갱신 (v6 mid-checkpoint 시점)

---

## §8. 관련 문서

- `docs/plans/2026-05-22_v3k_cli_ai_controller_promotion_plan.md` (정책 plan)
- `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (상위 CLI 확장 plan)
- `docs/update_log/2026-05-22_v3k_midpoint_checkpoint_v5_4dbac74f_to_1a8fdcde.md` (v5 mid-checkpoint)
- `cli/ai_controller.py` (1038줄, AIBacktestController, 28 메서드)
- `cli/subcommands.py` (+9 add_parser + 2 함수 추가)
- `stom_backtest.py` (SUBCOMMANDS 튜플 1줄 추가)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-CLI-AI-CONTROLLER-PROMOTION-EXECUTION` 섹션)
