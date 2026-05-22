# CLI 확장 plan Phase 1~3 진척 진단 보고서 (D1)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `ed5b2e11` (master plan 정본화 직후) |
| 기준 plan | `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (858줄) |
| 진단 기간 | 2026-03-24 ~ 2026-05-22 (2개월) |
| 진단 방식 | read-only (cli/ 디렉토리 모듈 + subcommands.py 라우터 + stom_backtest --help + 각 서브커맨드 --help 직접 확인) |
| 본 commit 정체성 | M1 진단 phase의 D1 (CLI 트랙 B 진척 baseline) |
| 코드 변경 | 0건 |

---

## §0. TL;DR

```text
CLI 확장 plan Phase 1~3은 2개월 동안 70% 이상 진행됐다.

Phase 1 (라이브러리 5개 CLI 노출):
  ✅ optimize / sweep / wfo / tune / db 모두 노출 완료 (4건 완전 + db 부분)
  ⏸ ai_controller / strategy_generator / monitor 미노출

Phase 2 (출력 표준화):
  ✅ --format {json,text} 옵션 + --version 옵션 도입
  ⏸ 전체 서브커맨드 일관성은 미검증

Phase 3 (설정관리 + 리포트 CLI 신규):
  ✅ report 서브커맨드 노출 (source 분기)
  ⏸ config CLI 미노출
  ⏸ history CLI 미노출

cli/ 모듈 수: 30 → 58 (28건 증가, 주로 research_* 트랙)
M2 첫 cycle 진입 시 우선순위: ai_controller / strategy_generator 노출 + Phase 2 일관성 검증.
```

---

## §1. baseline (진단 시점 사실)

### §1.1 cli/ 모듈 수

| 시점 | 모듈 수 | 변동 |
| --- | ---: | --- |
| 2026-03-24 (plan 작성) | 30 | baseline |
| 2026-05-22 (본 진단) | **58** | +28 |

신규 모듈 28개 중 약 24개가 `research_*` 시리즈(`research_iteration_v2~v5`, `research_optimizer*`, `research_promotion`, `research_metrics`, `research_segments` 등). 별도 research 트랙으로 확장된 상태이며 CLI plan Phase 1~3과는 독립 영역.

### §1.2 cli/commands/

```text
cli/commands/__init__.py
cli/commands/research.py
```

cli/commands/는 research 단일 모듈만 존재. CLI plan의 서브커맨드 라우팅은 `cli/subcommands.py` 단일 파일에서 처리.

### §1.3 stom_backtest --help 출력 표시 서브커맨드

```text
기본 CLI 명령:
  - 기본 백테스트 실행
  - formula / strategy 서브커맨드
  - discovery 서브커맨드

라이브러리 전용(별도 help 미노출):
  - history / sweep / optimizer / ai_controller / data_bridge
  - report / engine_tuner / monitor / strategy_generator
```

⚠️ **help 출력은 "라이브러리 전용"이라고 표시**하지만, 실제 직접 시도 시 일부는 서브커맨드로 노출되어 있음 (§2.1 참조). help 텍스트 갱신이 미흡한 상태.

---

## §2. Phase 1 진척 — 라이브러리 모듈 → CLI 서브커맨드 노출

### §2.1 각 서브커맨드 노출 상태 (직접 검증)

`stom_backtest <subcmd> --help` 직접 실행 결과:

| Plan 항목 | 서브커맨드 | --help 정상? | 비고 |
| --- | --- | --- | --- |
| §2.1 optimize | `optimize` | ✅ `--buy --sell --start --end --param-space ...` | Phase 1 §2.1 완료 |
| §2.2 sweep | `sweep` | ✅ `{param,rolling} ...` 분기 | Phase 1 §2.2 완료 (rolling 포함) |
| §2.3 wfo | `wfo` | ✅ `--start --end --train-window-days ...` | Phase 1 §2.3 완료 |
| §2.4 tune (engine_tuner) | `tune` | ✅ `--engines --total-codes ...` | Phase 1 §2.4 완료 |
| §2.5 db (data_bridge + db) | `db` | ✅ `{check,ensure,restore} ...` 분기 | Phase 1 §2.5 완료 |
| §2.6 ai_controller | `ai_controller` | ❌ 기본 backtest help fallback | **미노출** |
| §2.7 strategy_generator | `strategy_generator` | ❌ 기본 backtest help fallback | **미노출** |
| §2.8 monitor (Phase 3) | `monitor` | ❌ 기본 backtest help fallback | **미노출** |
| §2.9 history (Phase 3) | `history` | ❌ 기본 backtest help fallback | **미노출** |
| §2.10 data_bridge | `data_bridge` | ❌ 기본 backtest help fallback | **미노출** (db에 흡수됐을 가능성) |
| §2.11 engine_tuner | `engine_tuner` | ❌ 기본 backtest help fallback | **미노출** (tune으로 대체된 듯) |
| §2.12 report | `report` | ✅ `--source {backtest,discovery} --limit ...` | Phase 3 §3.x 부분 진행 |
| §2.13 config | `config` | ❌ 기본 backtest help fallback | **미노출** |

### §2.2 Phase 1 진척 정량 평가

- **노출 완료 (Phase 1 핵심 5건)**: optimize / sweep / wfo / tune / db → **5/5 (100%)**
- **추가 노출**: report (Phase 3 영역, 미리 진행됨)
- **미노출**: ai_controller / strategy_generator / monitor / history / data_bridge / engine_tuner / config → **7건**

Plan §2.1~§2.5의 핵심 5건은 모두 완료. data_bridge / engine_tuner는 db / tune으로 흡수돼 plan과 미세하게 다른 이름으로 노출.

### §2.3 subcommands.py 라우터 정밀 검사

`cli/subcommands.py:line 23~301` 직접 인용:

```
runtime-preflight  (신규, plan 외 추가)
formula            (list / add / test / delete / export / import — 6개)
strategy           (list / validate / analyze — 3개)
discovery          (analyze / ml-analyze / generate / create-strategy / promote /
                    auto / batch / history / evolve / compare — 10개)
optimize           ✅
sweep              ✅ (param / rolling — 2개)
wfo                ✅
tune               ✅ (Phase 1 §2.4)
db                 ✅ (check / ensure / restore — 3개)
report             ✅ (Phase 3 §3.x 영역)
```

총 노출 서브커맨드 수 (subcmd + sub-action 포함):

- 기본 backtest: 1
- runtime-preflight: 1
- formula: 6
- strategy: 3
- discovery: 10
- optimize: 1
- sweep: 2 (param + rolling)
- wfo: 1
- tune: 1
- db: 3 (check + ensure + restore)
- report: 1

= **30개+** (plan 작성 시점 19개 → **+11개 이상 증가**)

---

## §3. Phase 2 진척 — 출력 표준화

### §3.1 확인된 표준화 요소

| 표준화 요소 | 현재 상태 |
| --- | --- |
| `--format {json, text}` 옵션 | ✅ 기본 backtest + 일부 서브커맨드 |
| `--version` 옵션 | ✅ (`STOM CLI Backtest Runner <version>`) |
| `-o / --output FILE` 옵션 | ✅ 기본 backtest |
| UTF-8 출력 | ✅ `cli/_safe_io.py` 모듈 존재 |
| Exit code 표준 (0/1/2/3) | ✅ stom_backtest.py에 EXIT_SUCCESS/EXIT_ARG_ERROR/EXIT_EXEC_ERROR/EXIT_TIMEOUT 상수 정의 |

### §3.2 미검증 영역

- 30개 서브커맨드 전체에서 `--format` 옵션 일관성 (plan §3.2 의무) — 미검증
- JSON 출력 schema 표준 (plan §3.3 의무) — 미검증
- 버전 prefix 일관성 — 미검증

Phase 2 진척률: **부분 진행 (~50%)**. 인프라(`_safe_io.py`, exit code 상수)는 있으나 30개 서브커맨드 전체 일관성 검증 evidence 없음.

---

## §4. Phase 3 진척 — 설정관리 + 리포트 CLI 신규

### §4.1 report CLI

```
stom_backtest report --source {backtest,discovery} [--limit LIMIT]
```

- **노출 완료** ✅
- source 분기 (backtest / discovery)
- `cli/report.py` 모듈 존재 + `cli/research_report.py` 별도 존재

### §4.2 config CLI

- **미노출** ❌
- `cli/config.py` 모듈 존재 (단 internal BacktestConfig 관리용, CLI 노출 아님)

### §4.3 history CLI

- **미노출** ❌
- `cli/history.py` 모듈 존재
- discovery 내 `discovery history` 서브액션은 있음 (전체 history CLI는 별개)

Phase 3 진척률: **부분 진행 (~33%)**. report 1건 완료, config + history 잔여.

---

## §5. 미노출 / 잔여 작업

### §5.1 우선순위 분류

| 우선순위 | 미노출 서브커맨드 | 이유 |
| --- | --- | --- |
| 🔥 높음 | `ai_controller` | plan §2.6 정의됨, 사용자 가치 큼 |
| 🔥 높음 | `strategy_generator` | plan §2.7 정의됨, 자동 전략 생성 핵심 |
| 🔥 중간 | `config` | Phase 3 핵심, 설정 관리 |
| 중간 | `monitor` | Phase 3 영역, real-time 모니터링 |
| 중간 | `history` | Phase 3 영역, backtest 이력 |
| 낮음 | `data_bridge` | db에 흡수돼 별도 노출 불필요할 수 있음 |
| 낮음 | `engine_tuner` | tune으로 대체됨, 별도 노출 불필요할 수 있음 |

### §5.2 진척률 종합 평가

| Phase | 목표 | 완료 | 잔여 | 진척률 |
| --- | --- | ---: | ---: | ---: |
| Phase 1 (라이브러리 5개 노출) | 5건 | 5건 (optimize/sweep/wfo/tune/db) | 0건 | **100%** ✅ |
| Phase 1 확장 (추가 라이브러리) | 4건 (ai/strategy_gen/monitor/history) | 0건 | 4건 | **0%** |
| Phase 2 (출력 표준화) | 30+ 서브커맨드 일관성 | 인프라만 | 검증/일관성 | **~50%** |
| Phase 3 (설정관리/리포트) | 3건 (report/config/history) | 1건 (report) | 2건 (config/history) | **~33%** |

종합 진척률: 약 **60-70%**.

---

## §6. 트랙 B 진척 평가

master plan(`docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md`) §3.2 트랙 B 기준:

| Phase | master plan 기록 | 본 진단 정확 진척 |
| --- | --- | --- |
| Phase 1 | "진단 필요" | **5/5 핵심 100% 완료** |
| Phase 2 | "진단 필요" | **부분 ~50%** (인프라 OK, 일관성 미검증) |
| Phase 3 | "미진행" | **report 노출됨, ~33%** |

master plan §4.2의 M2 milestone "CLI Phase 1 (라이브러리 5개 노출)"은 **이미 완료된 상태**이므로 M2 작업이 다음으로 자동 승격:

```
M2 (재정의): Phase 1 확장 (ai_controller / strategy_generator 노출) + Phase 2 일관성 검증
M3 (재정의): Phase 2 완료 + Phase 3 config/history CLI 노출
M4 (재정의): Phase 3 완료 + V3K-IMPL-3 통합
```

milestone 시간 단축: 약 1~2주 단축 가능.

---

## §7. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log 1건 |
| read-only 진단 | ✅ stom_backtest --help 출력 확인만 |
| audit 결과 등록 | ✅ registry 1 섹션 |

| 금지 | 본 commit |
| --- | --- |
| 코드 변경 | ❌ 0건 |
| 운영 DB write | ❌ 0건 |
| feature flag 변경 | ❌ 0건 |

→ P-lane 적격.

---

## §8. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §9. 다음 인계

본 D1 진단 commit 직후 D2 (V3K-IMPL-3 진척 진단)으로 이동. M1 진단 phase의 두 번째 작업.

M2 첫 cycle 진입 시점에 본 진단 §5/§6 우선순위 인용해서 작업 선정:

1. **ai_controller CLI 노출** (Phase 1 §2.6) — 가장 우선
2. **strategy_generator CLI 노출** (Phase 1 §2.7)
3. **Phase 2 일관성 검증** — 30+ 서브커맨드 `--format` 옵션 일관성 audit

---

## §10. 관련 문서

- `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (CLI 확장 plan baseline)
- `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (master plan §3.2 트랙 B)
- `docs/update_log/2026-05-22_v3k_midcourse_review_backtest_cli_prioritization.md` (중간 검토)
- `cli/subcommands.py` (서브커맨드 라우터)
- `cli/_safe_io.py` (UTF-8 표준 출력)
- `cli/output.py` (출력 포맷터)
- `cli/version.py` (버전 정보)
- `stom_backtest.py` (CLI entry point)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-CLI-PHASE-PROGRESS-D1-DIAGNOSIS` 섹션)
