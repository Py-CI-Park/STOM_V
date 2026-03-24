# STOM CLI 서브커맨드 확장 개발 계획서

- 작성일: 2026-03-24
- 브랜치: `feature/cli-expand-subcommands` (from `STOM_Version_2U_C_CLI_v258`)
- 기반 버전: V2.58.U1.6

---

## 1. 개요

### 1.1 목적

STOM CLI v258에는 이미 구현되어 테스트된 내부 라이브러리 모듈이 CLI 서브커맨드로 노출되지 않은 채 `discovery auto` 파이프라인 내부에서만 사용되고 있다. 이 계획은 해당 모듈들을 **독립 서브커맨드로 노출**하고, 전체 CLI의 **출력 품질을 표준화**하며, **신규 기능**을 추가하는 것을 목표로 한다.

### 1.2 현황

| 항목 | 수치 |
|------|------|
| CLI 모듈 | 30개 (`cli/*.py`) |
| 노출 서브커맨드 | 19개 (backtest + formula 6 + strategy 3 + discovery 10) |
| 유닛 테스트 | 720개 수집, 302 passed |
| 라이브러리 전용 모듈 | 6개 (optimizer, sweep, wfo, engine_tuner, data_bridge, strategy_generator) |

### 1.3 목표

- **Phase 1**: 라이브러리 모듈 5개를 CLI 서브커맨드로 노출 → 서브커맨드 19개 → 24개+
- **Phase 2**: 전체 서브커맨드 출력 표준화 (JSON, UTF-8, 버전)
- **Phase 3**: 설정 관리 CLI + 리포트 생성 CLI 신규 추가

---

## 2. Phase 1: 내부 라이브러리 → CLI 서브커맨드 노출

### 2.1 `stom_backtest optimize` — 파라미터 최적화

#### 기존 모듈
- `cli/optimizer.py` (192줄)
- 클래스: `GridOptimizer`, `RandomOptimizer`
- 핵심 함수: `optimize(base_config, param_space, objective, method, maximize, max_iter, seed, run_fn, save_fn, on_progress)`

#### CLI 인터페이스

```bash
# Grid 최적화
stom_backtest optimize \
    --buy MyBuy --sell MySell \
    --start 20250101 --end 20250630 \
    --param-space params.json \
    --method grid \
    --objective tpi \
    --maximize \
    --format json

# Random 최적화
stom_backtest optimize \
    --buy MyBuy --sell MySell \
    --start 20250101 --end 20250630 \
    --param-space params.json \
    --method random --max-iter 50 --seed 42 \
    --objective tpi \
    -o results.json
```

#### argparse 정의

```python
opt_parser = subparsers.add_parser('optimize', help='파라미터 최적화 (Grid/Random)')

# 필수
opt_parser.add_argument('--buy', required=True, help='매수 전략명')
opt_parser.add_argument('--sell', required=True, help='매도 전략명')
opt_parser.add_argument('--start', type=int, required=True, help='시작일자 YYYYMMDD')
opt_parser.add_argument('--end', type=int, required=True, help='종료일자 YYYYMMDD')
opt_parser.add_argument('--param-space', required=True, dest='param_space_file',
                         help='파라미터 탐색 공간 JSON 파일 경로')

# 선택
opt_parser.add_argument('--method', choices=['grid', 'random'], default='grid',
                         help='최적화 방법 (default: grid)')
opt_parser.add_argument('--objective', default='tpi', help='최적화 목표 지표 (default: tpi)')
opt_parser.add_argument('--maximize', action='store_true', default=True,
                         help='목표 지표 최대화 (default: True)')
opt_parser.add_argument('--no-maximize', action='store_false', dest='maximize',
                         help='목표 지표 최소화')
opt_parser.add_argument('--max-iter', type=int, default=100,
                         help='Random 방법 최대 반복 (default: 100)')
opt_parser.add_argument('--seed', type=int, default=None, help='랜덤 시드')
opt_parser.add_argument('--engines', type=int, default=4, help='엔진 프로세스 수')
opt_parser.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
opt_parser.add_argument('--timeout', type=int, default=3600)
opt_parser.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
opt_parser.add_argument('-o', '--output', dest='output_file', help='결과 저장 파일')
```

#### param-space JSON 형식

```json
{
    "avg_time": [60, 120, 180],
    "betting": ["1", "2", "3"],
    "start_time": [90000, 90500],
    "end_time": [152000, 152800]
}
```

#### 구현 흐름

```
1. parse args → BacktestConfig 생성
2. param_space JSON 로드 및 검증
3. run_fn = lambda config: runner.run_backtest(config) 래핑
4. optimizer.optimize(base_config, param_space, ...) 호출
5. 결과를 format_result()로 포맷팅 → stdout 또는 파일
```

#### 수정 파일
- `cli/subcommands.py` — optimize 파서 추가 + 핸들러 라우팅
- `stom_backtest.py:46` — `'optimize'` 서브커맨드 감지 추가
- `tests/unit/test_optimizer_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `optimize --help` 정상 출력
- [ ] `--param-space` JSON 로드 검증
- [ ] grid 방법 조합 수 계산 정확성
- [ ] random 방법 seed 재현성
- [ ] `--format json` 출력 파싱 가능
- [ ] 잘못된 param-space 파일 시 exit code 1

---

### 2.2 `stom_backtest sweep` — 파라미터 스윕 / 날짜 롤링

#### 기존 모듈
- `cli/sweep.py` (146줄)
- 함수: `generate_combinations()`, `generate_rolling_windows()`, `run_sweep()`, `run_rolling()`

#### CLI 인터페이스

```bash
# 파라미터 스윕
stom_backtest sweep param \
    --buy MyBuy --sell MySell \
    --start 20250101 --end 20250630 \
    --params sweep_config.json \
    --format json -o sweep_results.json

# 날짜 롤링
stom_backtest sweep rolling \
    --buy MyBuy --sell MySell \
    --start 20240101 --end 20251231 \
    --window-days 90 --step-days 30 \
    --format json -o rolling_results.json

# 윈도우 미리보기 (dry-run)
stom_backtest sweep rolling \
    --start 20240101 --end 20251231 \
    --window-days 90 --step-days 30 \
    --dry-run
```

#### argparse 정의

```python
sweep_parser = subparsers.add_parser('sweep', help='파라미터 스윕 및 날짜 롤링')
sweep_sub = sweep_parser.add_subparsers(dest='sweep_action', required=True)

# sweep param
sweep_param = sweep_sub.add_parser('param', help='파라미터 조합 스윕')
sweep_param.add_argument('--buy', required=True)
sweep_param.add_argument('--sell', required=True)
sweep_param.add_argument('--start', type=int, required=True)
sweep_param.add_argument('--end', type=int, required=True)
sweep_param.add_argument('--params', required=True, dest='sweep_params_file',
                          help='스윕 파라미터 JSON 파일')
sweep_param.add_argument('--engines', type=int, default=4)
sweep_param.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
sweep_param.add_argument('--timeout', type=int, default=3600)
sweep_param.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
sweep_param.add_argument('-o', '--output', dest='output_file')

# sweep rolling
sweep_rolling = sweep_sub.add_parser('rolling', help='날짜 롤링 (고정 윈도우 이동)')
sweep_rolling.add_argument('--buy', help='매수 전략명 (--dry-run 시 불필요)')
sweep_rolling.add_argument('--sell', help='매도 전략명 (--dry-run 시 불필요)')
sweep_rolling.add_argument('--start', type=int, required=True, help='전체 시작일')
sweep_rolling.add_argument('--end', type=int, required=True, help='전체 종료일')
sweep_rolling.add_argument('--window-days', type=int, required=True, help='윈도우 크기 (일)')
sweep_rolling.add_argument('--step-days', type=int, required=True, help='이동 간격 (일)')
sweep_rolling.add_argument('--engines', type=int, default=4)
sweep_rolling.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
sweep_rolling.add_argument('--timeout', type=int, default=3600)
sweep_rolling.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
sweep_rolling.add_argument('-o', '--output', dest='output_file')
sweep_rolling.add_argument('--dry-run', action='store_true',
                            help='윈도우 목록만 출력하고 실행하지 않음')
```

#### 구현 흐름

```
sweep param:
  1. sweep_params JSON 로드
  2. generate_combinations(params) → 조합 목록 생성
  3. run_sweep(base_config, params, on_progress) 실행
  4. 결과 포맷팅 출력

sweep rolling:
  1. --dry-run이면 generate_rolling_windows()만 호출하여 윈도우 목록 출력
  2. 아니면 run_rolling(base_config, window_days, step_days) 실행
  3. 윈도우별 결과 집계 및 출력
```

#### 수정 파일
- `cli/subcommands.py` — sweep 파서 + 핸들러
- `stom_backtest.py:46` — `'sweep'` 감지
- `tests/unit/test_sweep_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `sweep param --help` / `sweep rolling --help` 정상 출력
- [ ] rolling --dry-run 윈도우 목록 JSON 검증
- [ ] 파라미터 조합 수 정확성
- [ ] 잘못된 날짜 범위 시 에러 메시지

---

### 2.3 `stom_backtest wfo` — Walk-Forward 검증

#### 기존 모듈
- `cli/wfo.py` (192줄)
- 함수: `generate_walk_forward_windows()`, `run_walk_forward()`, `save_walk_forward_report()`

#### CLI 인터페이스

```bash
# WFO 실행
stom_backtest wfo \
    --buy MyBuy --sell MySell \
    --start 20240101 --end 20251231 \
    --train-window-days 180 --test-window-days 60 \
    --step-days 30 \
    --param-space params.json \
    --objective tpi \
    --format json -o wfo_report.json

# 윈도우 미리보기
stom_backtest wfo \
    --start 20240101 --end 20251231 \
    --train-window-days 180 --test-window-days 60 \
    --step-days 30 \
    --dry-run
```

#### argparse 정의

```python
wfo_parser = subparsers.add_parser('wfo', help='Walk-Forward Optimization 검증')

# 필수
wfo_parser.add_argument('--start', type=int, required=True)
wfo_parser.add_argument('--end', type=int, required=True)
wfo_parser.add_argument('--train-window-days', type=int, required=True, help='훈련 윈도우 크기 (일)')
wfo_parser.add_argument('--test-window-days', type=int, required=True, help='테스트 윈도우 크기 (일)')

# 선택
wfo_parser.add_argument('--buy', help='매수 전략명 (--dry-run 시 불필요)')
wfo_parser.add_argument('--sell', help='매도 전략명 (--dry-run 시 불필요)')
wfo_parser.add_argument('--step-days', type=int, help='윈도우 이동 간격 (미지정 시 test-window-days)')
wfo_parser.add_argument('--purge-days', type=int, default=0, help='train-test 사이 퍼지 기간')
wfo_parser.add_argument('--embargo-days', type=int, default=0, help='test 후 엠바고 기간')
wfo_parser.add_argument('--param-space', dest='param_space_file',
                         help='최적화 파라미터 공간 JSON (미지정 시 고정 파라미터로 검증만)')
wfo_parser.add_argument('--objective', default='tpi')
wfo_parser.add_argument('--method', choices=['grid', 'random'], default='grid')
wfo_parser.add_argument('--maximize', action='store_true', default=True)
wfo_parser.add_argument('--max-iter', type=int, default=100)
wfo_parser.add_argument('--engines', type=int, default=4)
wfo_parser.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
wfo_parser.add_argument('--timeout', type=int, default=3600)
wfo_parser.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
wfo_parser.add_argument('-o', '--output', dest='output_file')
wfo_parser.add_argument('--dry-run', action='store_true',
                         help='train/test 윈도우 목록만 출력')
```

#### 구현 흐름

```
1. --dry-run이면:
   generate_walk_forward_windows(...) → 윈도우 목록 JSON 출력 → 종료

2. 정상 실행:
   a. param-space가 있으면 → run_walk_forward(..., optimize_fn=optimizer.optimize)
   b. param-space가 없으면 → 각 윈도우에 대해 고정 파라미터로 run_backtest 실행
   c. save_walk_forward_report(result, output_path)
   d. 결과 포맷팅 출력
```

#### 수정 파일
- `cli/subcommands.py` — wfo 파서 + 핸들러
- `stom_backtest.py:46` — `'wfo'` 감지
- `tests/unit/test_wfo_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `wfo --help` 정상 출력
- [ ] --dry-run 윈도우 생성 검증 (날짜 계산 정확성)
- [ ] purge/embargo 적용 검증
- [ ] step-days 미지정 시 test-window-days 기본값 적용
- [ ] param-space 없이 고정 파라미터 실행

---

### 2.4 `stom_backtest tune` — 시스템 리소스 분석

#### 기존 모듈
- `cli/engine_tuner.py` (138줄)
- 함수: `get_system_info()`, `recommend_engine_count()`, `estimate_memory_per_engine()`, `check_resources()`

#### CLI 인터페이스

```bash
# 시스템 정보 + 추천 엔진 수
stom_backtest tune --format json

# 특정 엔진 수로 리소스 체크
stom_backtest tune --engines 8 --timeframe tick

# 종목 수 기반 추천
stom_backtest tune --total-codes 500
```

#### argparse 정의

```python
tune_parser = subparsers.add_parser('tune', help='시스템 리소스 분석 및 엔진 수 추천')
tune_parser.add_argument('--engines', type=int, default=None,
                          help='확인할 엔진 수 (미지정 시 자동 추천)')
tune_parser.add_argument('--total-codes', type=int, default=0,
                          help='백테스트 대상 종목 수 (추천 정밀도 향상)')
tune_parser.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
tune_parser.add_argument('--format', choices=['json', 'text'], default='text', dest='output_format')
```

#### 구현 흐름

```
1. get_system_info() → CPU, RAM, 디스크 정보
2. --engines 지정 시: check_resources(engines, is_tick) → 적합성 판단
3. --engines 미지정 시: recommend_engine_count(total_codes) → 추천값
4. estimate_memory_per_engine(is_tick) → 예상 메모리 사용량
5. 결과 취합 → JSON 또는 text 포맷 출력
```

#### 수정 파일
- `cli/subcommands.py` — tune 파서 + 핸들러
- `stom_backtest.py:46` — `'tune'` 감지
- `tests/unit/test_tune_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `tune --help` 정상 출력
- [ ] JSON 출력에 cpu_count, memory_total, recommended_engines 키 존재
- [ ] --engines 과다 지정 시 경고 메시지
- [ ] text 포맷 읽기 편의성

---

### 2.5 `stom_backtest db` — 데이터베이스 유틸리티

#### 기존 모듈
- `cli/data_bridge.py` (154줄)
- 함수: `check_tick_db()`, `find_v1_tick_db()`, `ensure_tick_db()`, `restore_empty_db()`

#### CLI 인터페이스

```bash
# DB 상태 확인
stom_backtest db check --format json

# 틱 DB 존재 확인 + 자동 복구
stom_backtest db ensure --timeframe tick

# 빈 DB 복원
stom_backtest db restore --target backtest
```

#### argparse 정의

```python
db_parser = subparsers.add_parser('db', help='데이터베이스 상태 확인 및 유틸리티')
db_sub = db_parser.add_subparsers(dest='db_action', required=True)

# db check
db_check = db_sub.add_parser('check', help='DB 파일 상태 확인')
db_check.add_argument('--format', choices=['json', 'text'], default='text', dest='output_format')

# db ensure
db_ensure = db_sub.add_parser('ensure', help='필수 DB 존재 확인 및 자동 복구')
db_ensure.add_argument('--timeframe', choices=['tick', 'min'], default='tick')

# db restore
db_restore = db_sub.add_parser('restore', help='빈 DB 파일 복원')
db_restore.add_argument('--target', required=True,
                         choices=['backtest', 'strategy', 'tick', 'min'],
                         help='복원할 DB 종류')
```

#### 구현 흐름

```
db check:
  1. paths.py의 모든 DB 경로 순회
  2. 각 DB: 존재 여부, 파일 크기, 테이블 수, 최종 수정 시각
  3. check_tick_db() 결과 포함
  4. JSON 또는 text 포맷 출력

db ensure:
  1. ensure_tick_db(db_path) 호출
  2. 없으면 find_v1_tick_db()로 V1 DB 탐색
  3. 결과 메시지 출력

db restore:
  1. target에 해당하는 DB 경로 결정
  2. restore_empty_db(db_path) 호출
  3. 복원 결과 출력
```

#### 수정 파일
- `cli/subcommands.py` — db 파서 + 핸들러
- `stom_backtest.py:46` — `'db'` 감지
- `tests/unit/test_db_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `db check --help` / `db ensure --help` / `db restore --help` 정상
- [ ] db check JSON에 각 DB별 status 키 존재
- [ ] db restore로 빈 DB 생성 후 check에서 확인
- [ ] 존재하지 않는 target 시 에러

---

### 2.6 Phase 1 공통 구현 사항

#### stom_backtest.py 수정

```python
# 기존 (line 46)
if len(sys.argv) > 1 and sys.argv[1] in ('formula', 'strategy', 'discovery'):

# 변경
SUBCOMMANDS = ('formula', 'strategy', 'discovery', 'optimize', 'sweep', 'wfo', 'tune', 'db')
if len(sys.argv) > 1 and sys.argv[1] in SUBCOMMANDS:
```

#### subcommands.py 구조

```python
# 기존 handle_subcommand() 함수 말미에 추가
def handle_subcommand(args):
    cmd = args[0]
    if cmd == 'formula':
        return _handle_formula(args)
    elif cmd == 'strategy':
        return _handle_strategy(args)
    elif cmd == 'discovery':
        return _handle_discovery(args)
    # --- Phase 1 추가 ---
    elif cmd == 'optimize':
        return _handle_optimize(args)
    elif cmd == 'sweep':
        return _handle_sweep(args)
    elif cmd == 'wfo':
        return _handle_wfo(args)
    elif cmd == 'tune':
        return _handle_tune(args)
    elif cmd == 'db':
        return _handle_db(args)
```

#### 에러 처리 패턴 (모든 새 핸들러 공통)

```python
def _handle_optimize(args):
    parser = _build_optimize_parser()
    parsed = parser.parse_args(args[1:])  # 'optimize' 제거
    try:
        # ... 실행 로직 ...
        result = optimizer.optimize(...)
        output = format_result(result, parsed.output_format)
        if parsed.output_file:
            with open(parsed.output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        else:
            print(output)
        return 0
    except FileNotFoundError as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 1
    except Exception as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 2
```

---

## 3. Phase 2: CLI 출력 품질 표준화

### 3.1 UTF-8 안전 출력 레이어

#### 문제
- Windows CP949 콘솔에서 em-dash(`-`), 특수문자 출력 시 `UnicodeEncodeError` crash
- 이미 `subcommands.py:162, 218`에서 한 건 수정했지만, 향후 추가 방지 필요

#### 해결

`cli/_safe_io.py` 신규 모듈:

```python
"""UTF-8 안전 stdout/stderr 래퍼.

Windows CP949 환경에서 UnicodeEncodeError를 방지한다.
인코딩 불가 문자는 '?' 또는 가장 유사한 ASCII로 대체한다.
"""
import sys
import io


def configure_safe_output():
    """stdout/stderr를 UTF-8 또는 errors='replace' 모드로 재설정."""
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(errors='replace')
            sys.stderr.reconfigure(errors='replace')
        except Exception:
            pass
```

적용 위치: `stom_backtest.py`의 `main()` 최상단에서 호출

```python
def main():
    from cli._safe_io import configure_safe_output
    configure_safe_output()
    # ... 이하 기존 로직 ...
```

#### 수정 파일
- `cli/_safe_io.py` — 신규
- `stom_backtest.py` — main() 상단에 호출 추가
- `tests/unit/test_safe_io.py` — 신규 테스트

#### 테스트 항목
- [ ] em-dash, 유니코드 이모지 등 출력 시 crash 없음
- [ ] 한글 정상 출력 유지
- [ ] reconfigure 미지원 환경에서 graceful fallback

---

### 3.2 전체 서브커맨드 `--json` 출력 보장

#### 현황 분석

| 서브커맨드 | JSON 지원 | 비고 |
|-----------|----------|------|
| 기본 백테스트 | **O** | `--format json` |
| formula list | **O** | JSON 배열 |
| formula add/delete | **부분** | 성공/실패 메시지만 |
| formula test | **X** | text only |
| formula export | **O** | JSON 파일 |
| formula import | **X** | text only |
| strategy list | **O** | JSON |
| strategy validate | **부분** | 결과 dict |
| strategy analyze | **O** | JSON |
| discovery * | **O** | 대부분 JSON |

#### 작업

1. `formula test` — 결과를 `{"status": "ok", "code": "..."}` 또는 `{"status": "error", "message": "..."}`로 래핑
2. `formula add/delete/import` — `{"status": "success", "name": "...", "action": "added"}` 형태
3. 각 핸들러에 `--json` 플래그 추가 (기존 `--format` 인자와 통일)

#### 수정 파일
- `cli/formula.py` — 반환값 dict 통일
- `cli/subcommands.py` — formula 핸들러에서 JSON 분기
- `tests/unit/test_formula.py` — JSON 출력 테스트 추가

#### 테스트 항목
- [ ] 모든 formula 서브커맨드에 `--json` 플래그 동작
- [ ] JSON 출력이 `json.loads()` 가능
- [ ] 에러 시에도 JSON 형태 유지 (`{"status": "error", ...}`)

---

### 3.3 `--version` 중앙 관리

#### 현황
- `cli/config.py`에 `VERSION` 상수가 있을 수 있으나 확인 필요
- `stom_backtest.py --version` 은 존재하지만 버전 값의 출처 불명확

#### 작업

`cli/version.py` 신규:

```python
"""STOM CLI 버전 중앙 관리."""
__version__ = '2.58.2'

# V{major}.{minor}.U{patch}.{hotfix} 형식의 display 버전
DISPLAY_VERSION = 'V2.58.U2'
```

모든 `--version` 출력이 이 파일을 참조하도록 통일.

#### 수정 파일
- `cli/version.py` — 신규
- `cli/config.py` — version 참조 변경
- `stom_backtest.py` — `--version` 출력 소스 변경

---

## 4. Phase 3: 신규 기능 추가

### 4.1 `stom_backtest setting` — 설정 조회 (read-only)

#### 배경
- `utility/setting.py`에서 `DICT_SET` 딕셔너리로 전역 설정 관리
- `setting.db`는 Fernet 암호화 — 암호키가 PC별로 다름
- 워크트리 환경에서는 `STOM_ALLOW_MINIMAL_SETTING=1`로 우회

#### CLI 인터페이스

```bash
# 전체 설정 조회
stom_backtest setting list --format json

# 특정 키 조회
stom_backtest setting get 주식타임프레임

# 설정 키 검색
stom_backtest setting search 백테
```

#### argparse 정의

```python
setting_parser = subparsers.add_parser('setting', help='STOM 설정 조회')
setting_sub = setting_parser.add_subparsers(dest='setting_action', required=True)

# setting list
setting_list = setting_sub.add_parser('list', help='전체 설정 키-값 목록')
setting_list.add_argument('--format', choices=['json', 'text'], default='text', dest='output_format')

# setting get
setting_get = setting_sub.add_parser('get', help='특정 설정 값 조회')
setting_get.add_argument('key', help='설정 키 이름')
setting_get.add_argument('--format', choices=['json', 'text'], default='text', dest='output_format')

# setting search
setting_search = setting_sub.add_parser('search', help='설정 키 검색')
setting_search.add_argument('query', help='검색어 (부분 일치)')
setting_search.add_argument('--format', choices=['json', 'text'], default='text', dest='output_format')
```

#### 구현 흐름

```
1. from utility.setting import DICT_SET 로드 시도
2. fernet.InvalidToken 발생 시:
   - STOM_ALLOW_MINIMAL_SETTING=1 안내 메시지 출력
   - 기본값으로 대체하여 부분 표시
3. list: DICT_SET 전체를 정렬하여 출력
4. get: DICT_SET[key] 조회 (KeyError 시 에러)
5. search: key에 query가 포함된 항목 필터링
```

#### 주의사항
- **read-only**: 설정 변경(write)은 이 단계에서 구현하지 않음
  - 이유: Fernet 암호화 + PC별 키 → write 시 무결성 보장 어려움
  - 향후 `setting set KEY VALUE` 추가 시 별도 설계 필요
- DICT_SET import 시 side effect (로깅, DB 접근) 최소화 필요

#### 수정 파일
- `cli/subcommands.py` — setting 파서 + 핸들러
- `stom_backtest.py:46` — `'setting'` 감지
- `tests/unit/test_setting_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `setting list --format json` 출력 파싱 가능
- [ ] `setting get` 존재하는 키 조회
- [ ] `setting get` 존재하지 않는 키 → 에러 메시지 + exit code 1
- [ ] `setting search` 부분 일치 필터링
- [ ] DICT_SET 로드 실패 시 graceful 에러 (crash 아님)

---

### 4.2 `stom_backtest report` — 리포트 생성

#### 기존 모듈
- `cli/report.py` (97줄)
- 함수: `results_to_dataframe()`, `save_csv()`, `save_excel()`, `summary_stats()`

#### CLI 인터페이스

```bash
# 백테스트 결과 DB에서 리포트 생성
stom_backtest report \
    --source backtest \
    --format csv \
    -o report.csv

# 최근 N건 요약 통계
stom_backtest report \
    --source backtest \
    --limit 100 \
    --summary \
    --format json

# Discovery 히스토리 리포트
stom_backtest report \
    --source discovery \
    --format excel \
    -o discovery_report.xlsx
```

#### argparse 정의

```python
report_parser = subparsers.add_parser('report', help='백테스트/Discovery 결과 리포트 생성')
report_parser.add_argument('--source', required=True,
                           choices=['backtest', 'discovery'],
                           help='데이터 소스')
report_parser.add_argument('--limit', type=int, default=0,
                           help='최근 N건 제한 (0=전체)')
report_parser.add_argument('--summary', action='store_true',
                           help='요약 통계만 출력')
report_parser.add_argument('--format', choices=['json', 'csv', 'excel', 'text'],
                           default='json', dest='output_format')
report_parser.add_argument('-o', '--output', dest='output_file',
                           help='출력 파일 (csv/excel 시 필수)')
```

#### 수정 파일
- `cli/subcommands.py` — report 파서 + 핸들러
- `stom_backtest.py:46` — `'report'` 감지
- `tests/unit/test_report_cli.py` — 신규 테스트

#### 테스트 항목
- [ ] `report --help` 정상
- [ ] --summary --format json 출력 검증
- [ ] csv/excel 파일 생성 확인
- [ ] --limit 적용 검증

---

## 5. 구현 순서 및 커밋 전략

### 5.1 커밋 단위

각 서브커맨드를 **독립 커밋**으로 진행한다. 의존성 순서:

```
Commit 1: docs: CLI 서브커맨드 확장 개발 계획서 (이 문서)
Commit 2: feat: UTF-8 안전 출력 레이어 (cli/_safe_io.py)
Commit 3: feat: 버전 중앙 관리 (cli/version.py)
Commit 4: feat: stom_backtest tune - 시스템 리소스 분석 (가장 단순)
Commit 5: feat: stom_backtest db - DB 유틸리티
Commit 6: feat: stom_backtest optimize - 파라미터 최적화
Commit 7: feat: stom_backtest sweep - 파라미터 스윕 / 날짜 롤링
Commit 8: feat: stom_backtest wfo - Walk-Forward 단독 실행
Commit 9: feat: formula 서브커맨드 JSON 출력 통일
Commit 10: feat: stom_backtest setting - 설정 조회 (read-only)
Commit 11: feat: stom_backtest report - 리포트 생성
```

### 5.2 각 커밋 포함 사항

```
1. cli/subcommands.py 수정 (파서 + 핸들러)
2. stom_backtest.py 서브커맨드 목록 추가
3. tests/unit/test_{name}_cli.py 신규 테스트
4. --help 동작 확인
5. 기존 테스트 regression 없음 확인
```

### 5.3 버전 관리

- Phase 1 완료 시: `V2.58.U2` (CLI 서브커맨드 확장)
- Phase 2 완료 시: `V2.58.U2.1` (출력 표준화)
- Phase 3 완료 시: `V2.58.U2.2` (신규 기능)
- 전체 완료 후: `STOM_Version_2U_C_CLI_v258`로 머지

---

## 6. 완료 기준

### Phase 1 완료 조건
- [ ] optimize, sweep, wfo, tune, db 5개 서브커맨드 정상 동작
- [ ] 각 서브커맨드 `--help` 출력 (CP949 crash 없음)
- [ ] 각 서브커맨드 `--format json` 출력 파싱 가능
- [ ] 기존 720개 테스트 regression 없음
- [ ] 신규 테스트 전수 통과

### Phase 2 완료 조건
- [ ] 모든 서브커맨드에서 UTF-8 특수문자 안전 출력
- [ ] formula 전체 서브커맨드 JSON 출력 통일
- [ ] `--version` 중앙 관리 동작

### Phase 3 완료 조건
- [ ] setting list/get/search read-only 동작
- [ ] report csv/excel/json 생성 동작
- [ ] DICT_SET 로드 실패 시 graceful 처리

---

## 7. 리스크 및 주의사항

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| `subcommands.py` 비대화 (현재 629줄) | 유지보수 어려움 | 핸들러를 별도 파일로 분리 가능 (cli/handle_optimize.py 등) |
| optimizer/sweep/wfo가 runner.run_backtest 의존 | setting.db 암호키 문제 | STOM_ALLOW_MINIMAL_SETTING=1 환경에서 테스트 |
| setting 조회 시 side effect | DICT_SET import가 DB 접근 유발 | try/except 격리, timeout 설정 |
| 기존 테스트 regression | 서브커맨드 라우팅 변경 | 매 커밋마다 기존 테스트 실행 |

---

## 8. 신규 파일 목록

```
cli/_safe_io.py              (Phase 2 - UTF-8 안전 출력)
cli/version.py               (Phase 2 - 버전 중앙 관리)
tests/unit/test_safe_io.py   (Phase 2)
tests/unit/test_optimizer_cli.py  (Phase 1)
tests/unit/test_sweep_cli.py      (Phase 1)
tests/unit/test_wfo_cli.py        (Phase 1)
tests/unit/test_tune_cli.py       (Phase 1)
tests/unit/test_db_cli.py         (Phase 1)
tests/unit/test_setting_cli.py    (Phase 3)
tests/unit/test_report_cli.py     (Phase 3)
```

---

## 9. 서브커맨드 최종 목록 (완료 후)

```
stom_backtest [기본 백테스트]           # 기존
stom_backtest formula (6 actions)      # 기존
stom_backtest strategy (3 actions)     # 기존
stom_backtest discovery (10 actions)   # 기존
stom_backtest optimize                 # Phase 1 NEW
stom_backtest sweep param|rolling      # Phase 1 NEW
stom_backtest wfo                      # Phase 1 NEW
stom_backtest tune                     # Phase 1 NEW
stom_backtest db check|ensure|restore  # Phase 1 NEW
stom_backtest setting list|get|search  # Phase 3 NEW
stom_backtest report                   # Phase 3 NEW

합계: 기본 1 + formula 6 + strategy 3 + discovery 10
      + optimize 1 + sweep 2 + wfo 1 + tune 1 + db 3
      + setting 3 + report 1 = 32개 서브커맨드
```
