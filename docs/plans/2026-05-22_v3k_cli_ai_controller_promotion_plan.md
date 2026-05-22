# CLI 확장 amend — ai-controller 서브커맨드 promotion plan

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `3d71b09f` (v5 mid-checkpoint 직후) |
| 상위 plan | `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (CLI 확장 본체) |
| 마스터 plan | `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (트랙 B baseline) |
| 본 plan 정체성 | 상위 CLI 확장 plan을 **supersede 하지 않고 amend layer**로 ai-controller 서브커맨드를 추가하는 정책 결정 plan |
| 코드 변경 의무 | docstring + subcommands.py + stom_backtest.py SUBCOMMANDS 튜플 |
| 위험도 | 낮음 (CLI 신규 추가, 기존 동작 무변경) |

---

## §0. TL;DR

```text
cli/ai_controller.py의 library-only 정책을 떨면서 stom_backtest ai-controller 서브커맨드를 추가한다.
28개 메서드 중 핵심 8개를 우선 노출: list-strategies / analyze-strategy / run / dry-run / get-history / get-best / system-info / create-strategy.
상위 CLI 확장 plan(2026-03-24)을 supersede하지 않고 §2.7 amend layer로 추가.
LH1 invariant 보존 (trade/, utility/, Kiwoom_OpenAPI/, receiver/ 무변경).
L9 보존 (STOM CLI surface 기존 동작 무변경, 신규 추가만).
```

---

## §1. 배경

`cli/ai_controller.py` 모듈 docstring 인용 (line 1-9):

```python
"""AI 백테스트 컨트롤러 — 통합 파사드.
...
주의:
- 현재는 `stom_backtest.py` 의 공식 서브커맨드가 아니라 Python API 성격의 모듈이다.
- shipped CLI 범위와 혼동하지 않도록 문서/계획서에서 library-only 로 구분한다.
"""
```

본 plan은 위 정책을 **명시적으로 떨어내는 결정**을 정본화한다. 사유:

1. 5개 분야 순차 plan 100% 종결 후 트랙 B 진척률 가장 큰 폭의 산출이 ai_controller 노출
2. 사용자가 "B-1. ai_controller docstring 갱신 + 공식 서브커맨드 노출" 명시 선택
3. AIBacktestController가 dict 반환만 하는 *예외-throw-없는 API*라 CLI wrapping 적합
4. 기존 cli/ai_controller.py 본문 코드 무변경 (docstring만 갱신)

---

## §2. AIBacktestController 28개 메서드 인벤토리

`cli/ai_controller.py` line 22 클래스의 public methods:

| # | 메서드 | line | 노출 우선 |
| ---: | --- | ---: | --- |
| 1 | `list_strategies()` | 52 | **P0 노출** |
| 2 | `analyze_strategy(name, type)` | 60 | **P0 노출** |
| 3 | `analyze_results(input_path, ...)` | 164 | P1 |
| 4 | `analyze_results_ml(...)` | 183 | P1 |
| 5 | `generate_conditions(...)` | 203 | P1 |
| 6 | `create_strategy_from_analysis(...)` | 252 | P1 |
| 7 | `evaluate_walk_forward_result(...)` | 307 | P2 |
| 8 | `discover_strategy(...)` | 372 | P1 |
| 9 | `discover_and_promote_strategy(...)` | 630 | P2 |
| 10 | `get_discovery_history(...)` | 715 | P1 |
| 11 | `compare_discovery_history(ids)` | 725 | P2 |
| 12 | `auto_discover_evolve(...)` | 735 | P2 |
| 13 | `auto_discover_batch(...)` | 748 | P2 |
| 14 | `auto_discover(...)` | 767 | P2 |
| 15 | `research_strategy_once(...)` | 797 | P2 |
| 16 | `run(config_dict)` | 818 | **P0 노출** |
| 17 | `dry_run(config_dict)` | 856 | **P0 노출** |
| 18 | `sweep(config_dict, param_space, ...)` | 882 | P1 |
| 19 | `optimize(config_dict, param_space, ...)` | 902 | P1 |
| 20 | `walk_forward(config_dict, param_space, ...)` | 937 | P1 |
| 21 | `create_strategy(name, conditions, ...)` | 972 | **P0 노출** |
| 22 | `delete_strategy(name, type)` | 983 | **P0 노출** |
| 23 | `get_history(limit, ...)` | 993 | **P0 노출** |
| 24 | `get_best(metric, order, ...)` | 1005 | **P0 노출** |
| 25 | `compare(run_ids)` | 1017 | P1 |
| 26 | `system_info()` | 1027 | **P0 노출** |

P0 노출 (본 plan): 8개 — list-strategies / analyze-strategy / run / dry-run / get-history / get-best / create-strategy / delete-strategy / system-info (9개)

P1/P2는 후속 plan으로 분리.

---

## §3. CLI 서브커맨드 설계 — `stom_backtest ai-controller`

### §3.1 액션 9개 (P0)

```bash
# 전략 목록
stom_backtest ai-controller list-strategies [--format {json,text}]

# 전략 AST 분석
stom_backtest ai-controller analyze-strategy <name> [--type {buy,sell}] [--format {json,text}]

# 백테스트 실행
stom_backtest ai-controller run \
    --buy <name> --sell <name> --start YYYYMMDD --end YYYYMMDD \
    [--timeframe {tick,min}] [--engines N] [--format {json,text}]

# 백테스트 dry-run (실행 안 함, 설정 검증만)
stom_backtest ai-controller dry-run \
    --buy <name> --sell <name> --start YYYYMMDD --end YYYYMMDD \
    [--format {json,text}]

# 히스토리 조회
stom_backtest ai-controller get-history [--limit N] [--strategy <name>] [--format {json,text}]

# 최고 성과 조회
stom_backtest ai-controller get-best [--metric tpi] [--order {desc,asc}] [--limit N] [--format {json,text}]

# 전략 생성 (조건식 list 기반)
stom_backtest ai-controller create-strategy <name> --conditions-file conditions.json [--type {buy,sell}]

# 전략 삭제
stom_backtest ai-controller delete-strategy <name> [--type {buy,sell}]

# 시스템 정보
stom_backtest ai-controller system-info [--format {json,text}]
```

### §3.2 argparse 골격 (subcommands.py 추가)

```python
# --- ai-controller 서브커맨드 ---
ai_parser = sub.add_parser('ai-controller', help='AI 백테스트 컨트롤러 (28개 메서드 중 P0 9개 노출)')
ai_sub = ai_parser.add_subparsers(dest='ai_action')

# list-strategies
ai_ls = ai_sub.add_parser('list-strategies', help='사용 가능한 전략 목록')
ai_ls.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')

# analyze-strategy
ai_an = ai_sub.add_parser('analyze-strategy', help='전략 AST 분석 + 타임프레임')
ai_an.add_argument('name', help='전략명')
ai_an.add_argument('--type', choices=['buy', 'sell'], default='buy', dest='strategy_type')
ai_an.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')

# run
ai_run = ai_sub.add_parser('run', help='백테스트 실행')
ai_run.add_argument('--buy', required=True)
ai_run.add_argument('--sell', required=True)
ai_run.add_argument('--start', type=int, required=True)
ai_run.add_argument('--end', type=int, required=True)
ai_run.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
ai_run.add_argument('--engines', type=int, default=4)
ai_run.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')

# (이하 dry-run, get-history, get-best, create-strategy, delete-strategy, system-info 유사 구조)
```

### §3.3 핸들러 (subcommands.py 추가)

```python
def _handle_ai_controller(parsed):
    """ai-controller 서브커맨드 핸들러."""
    from cli.ai_controller import AIBacktestController
    controller = AIBacktestController()
    action = parsed.ai_action

    if action == 'list-strategies':
        result = controller.list_strategies()
    elif action == 'analyze-strategy':
        result = controller.analyze_strategy(parsed.name, parsed.strategy_type)
    elif action == 'run':
        config = {
            'buy_strategy': parsed.buy,
            'sell_strategy': parsed.sell,
            'start_date': parsed.start,
            'end_date': parsed.end,
            'is_tick': parsed.timeframe == 'tick',
            'engine_count': parsed.engines,
        }
        result = controller.run(config)
    elif action == 'dry-run':
        config = {...}
        result = controller.dry_run(config)
    elif action == 'get-history':
        result = controller.get_history(limit=parsed.limit, strategy=parsed.strategy)
    elif action == 'get-best':
        result = controller.get_best(metric=parsed.metric, order=parsed.order, limit=parsed.limit)
    elif action == 'create-strategy':
        # conditions-file JSON 로드 후
        result = controller.create_strategy(parsed.name, conditions=...)
    elif action == 'delete-strategy':
        result = controller.delete_strategy(parsed.name, parsed.strategy_type)
    elif action == 'system-info':
        result = controller.system_info()
    else:
        return 0

    exit_code = 0 if result.get('status') == 'ok' else 1
    output_format = getattr(parsed, 'output_format', 'json')
    if output_format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_text(result))
    return exit_code
```

---

## §4. ai_controller.py docstring 갱신

기존 (line 1-9):

```python
"""AI 백테스트 컨트롤러 — 통합 파사드.

AI가 하나의 인터페이스로 전체 백테스트 파이프라인을 제어한다.
모든 메서드는 dict를 반환하며, 예외를 throw하지 않는다.

주의:
- 현재는 `stom_backtest.py` 의 공식 서브커맨드가 아니라 Python API 성격의 모듈이다.
- shipped CLI 범위와 혼동하지 않도록 문서/계획서에서 library-only 로 구분한다.
"""
```

신규:

```python
"""AI 백테스트 컨트롤러 — 통합 파사드 + 공식 shipped CLI.

AI가 하나의 인터페이스로 전체 백테스트 파이프라인을 제어한다.
모든 메서드는 dict를 반환하며, 예외를 throw하지 않는다.

CLI 노출 (2026-05-22 promotion):
- `stom_backtest ai-controller <action>` 서브커맨드로 P0 9개 액션 노출.
- P0 노출: list-strategies / analyze-strategy / run / dry-run /
  get-history / get-best / create-strategy / delete-strategy / system-info.
- P1/P2 (sweep / optimize / walk_forward / discover_* / auto_discover_*)은 후속 plan으로 분리.
- promotion plan: docs/plans/2026-05-22_v3k_cli_ai_controller_promotion_plan.md
"""
```

본문 코드는 무변경.

---

## §5. SUBCOMMANDS 튜플 갱신 (stom_backtest.py line 41-45)

```python
# 기존
SUBCOMMANDS = (
    'formula', 'strategy', 'discovery',
    'optimize', 'sweep', 'wfo', 'tune', 'db',
    'setting', 'report', 'runtime-preflight',
)

# 신규
SUBCOMMANDS = (
    'formula', 'strategy', 'discovery',
    'optimize', 'sweep', 'wfo', 'tune', 'db',
    'setting', 'report', 'runtime-preflight',
    'ai-controller',   # ← 추가
)
```

---

## §6. handle_subcommand 라우터 추가 (cli/subcommands.py line 432~)

```python
def handle_subcommand(args=None):
    ...
    elif parsed.command == 'runtime-preflight':
        return _handle_runtime_preflight(parsed)
    elif parsed.command == 'ai-controller':       # ← 추가
        return _handle_ai_controller(parsed)
    else:
        parser.print_help()
        return 0
```

---

## §7. 검증 기준

### §7.1 정적 검증

```powershell
python -m py_compile cli/ai_controller.py
python -m py_compile cli/subcommands.py
python -m py_compile stom_backtest.py
```

### §7.2 --help 검증

```powershell
python stom_backtest.py ai-controller --help
python stom_backtest.py ai-controller list-strategies --help
python stom_backtest.py ai-controller analyze-strategy --help
python stom_backtest.py ai-controller run --help
python stom_backtest.py ai-controller dry-run --help
python stom_backtest.py ai-controller get-history --help
python stom_backtest.py ai-controller get-best --help
python stom_backtest.py ai-controller create-strategy --help
python stom_backtest.py ai-controller delete-strategy --help
python stom_backtest.py ai-controller system-info --help
```

### §7.3 핵심 동작 검증

```powershell
# 가장 가벼운 read-only 액션 2건
python stom_backtest.py ai-controller list-strategies --format json
python stom_backtest.py ai-controller system-info --format json
```

JSON 출력 + exit code 0 확인.

### §7.4 기존 동작 보존 (L9)

```powershell
python stom_backtest.py --help                          # 기존 백테스트 help
python stom_backtest.py formula --help                  # 기존 formula
python stom_backtest.py optimize --help                 # 기존 optimize
python stom_backtest.py setting list --format text      # 기존 setting
```

모두 정상 동작 유지.

---

## §8. 보존 invariant

| invariant | 보장 방법 |
| --- | --- |
| L1 database schema unchanged | DB 접근은 read-only (list/analyze) 또는 기존 함수 wrap만 |
| L7 LS direct dependency 0건 | 본 plan은 LS import 추가 안 함 |
| L9 STOM CLI surface 보존 | 기존 11개 서브커맨드 동작 무변경, ai-controller 신규 추가만 |
| LH1 Kiwoom 주문/청산/체결 경로 무변경 | trade/, utility/, Kiwoom_OpenAPI/, receiver/ 무변경 |
| LH2~LH5 | 본 plan과 무관 (Phase H 영역) |

---

## §9. preparation-first §3 정합

| 허용 | 본 plan |
| --- | --- |
| docs 추가 | ✅ plan 1건 |
| CLI 신규 추가 (기존 동작 보존) | ✅ ai-controller subcommand |
| docstring 갱신 (정책 명시화) | ✅ 본 plan §4 |

| 금지 | 본 plan |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 (read-only 액션만 P0 노출) |
| feature flag default-ON 전환 | ❌ 0건 |
| LS direct dependency 추가 | ❌ 0건 |
| Kiwoom runtime mutation | ❌ 0건 (trade/, utility/ 무변경) |

→ P-lane 적격 (단, 코드 변경 발생하므로 코드 측 P-lane).

---

## §10. 후속 plan (P1/P2 노출)

본 plan 종결 후 다음 plan으로 P1/P2 액션 추가:

- P1 액션 9개: analyze-results / analyze-results-ml / generate-conditions / create-strategy-from-analysis / discover-strategy / get-discovery-history / sweep / optimize / walk-forward / compare
- P2 액션 8개: evaluate-walk-forward-result / discover-and-promote-strategy / compare-discovery-history / auto-discover-evolve / auto-discover-batch / auto-discover / research-strategy-once

후속 plan은 본 plan §3.1 ai-controller 라우터 패턴 그대로 확장.

---

## §11. 다음 인계

본 plan 정본화 commit 직후:

1. cli/ai_controller.py docstring 갱신
2. cli/subcommands.py 라우터 + 9 액션 add_parser + `_handle_ai_controller` 함수 추가
3. stom_backtest.py SUBCOMMANDS 튜플에 'ai-controller' 추가
4. py_compile + --help + list-strategies / system-info 동작 검증
5. update_log + registry + commit

순차 진행. 위 4건은 단일 commit으로 묶음.

---

## §12. 관련 문서

- `docs/plans/2026-03-24_cli_expand_subcommands_plan.md` (CLI 확장 상위 plan)
- `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md` (트랙 B baseline)
- `docs/update_log/2026-05-22_cli_phase_progress_diagnosis.md` (D1 진단)
- `docs/update_log/2026-05-22_v3k_midpoint_checkpoint_v5_4dbac74f_to_1a8fdcde.md` (v5 mid-checkpoint)
- `cli/ai_controller.py` (1038줄, AIBacktestController, 28 메서드)
- `cli/subcommands.py` (라우터, line 432 handle_subcommand)
- `stom_backtest.py` (SUBCOMMANDS 튜플, line 41-45)
- `docs/CARRY_FORWARD_REGISTRY.md` (`V3K-CLI-AI-CONTROLLER-PROMOTION` 섹션)
