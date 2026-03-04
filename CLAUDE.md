# STOM Project Guidelines

## STOM_Version_2U 브랜치 핵심 목적

> **이 브랜치의 목적은 단순한 일회성 변환(pyd → py)이 아닙니다.**

`STOM_Version_2U`는 `STOM_Version_2`에서 컴파일 바이너리(`ui_mainwindow.pyd`)로만 제공되는
UI 핵심 로직을 **항상 수정·업데이트 가능한 소스 파일**(`ui_mainwindow.py`)로 운영하는
**지속적 동기화 개발 브랜치**입니다.

- `STOM_Version_2`가 `ui_mainwindow.pyd`를 업데이트하면 → `STOM_Version_2U`도 반드시 동기화
- `.pyd`는 직접 읽을 수 없으므로 → 주변 `.py` 파일 변화를 추론하여 `ui_mainwindow.py`에 반영
- `ui_mainwindow.py`는 `ui_mainwindow.pyd`와 **항상 동일한 공개 인터페이스** 제공
- 이 브랜치는 `STOM_Version_2`를 **지속적으로 따라가는 살아있는 추적 브랜치**

---

## Version Naming Convention

### Format
```
V{major}.{minor}.U{patch}.{hotfix}
```

### Rules
1. **Major (V2)**: 대규모 아키텍처 변경
2. **Minor (.36)**: 기능 추가 또는 중요 업데이트
3. **Patch (U1)**: 마이그레이션, 리팩토링, 중간 규모 변경
4. **Hotfix (.2, .3, ...)**: 버그 수정, 누락된 메서드 추가

### Examples
- `V2.36` - 기본 릴리스
- `V2.36.U1` - ui_mainwindow.pyd → ui_mainwindow.py 마이그레이션
- `V2.36.U1.2` - int_hms, dbreader 초기화 수정
- `V2.36.U1.3` - 추가 누락 메서드 수정

### Commit Message Format
```
STOM V{version} - {brief description}

수정 내용:
- {change 1}
- {change 2}
...

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Project Structure

### Key Directories (V2.51~)
- `ui/` - UI 관련 모듈 (PyQt5), `ui/icon/` 아이콘 파일
- `utility/` - 유틸리티 함수 및 클래스, `utility/imagefiles/`, `utility/pycharm/`
- `trade/stock_korea/` - 주식(키움증권) 트레이딩 로직
- `trade/binance/` - 바이낸스 암호화폐 트레이딩
- `trade/upbit/` - 업비트 암호화폐 트레이딩
- `trade/future_oversea/` - 해외선물 트레이딩
- `trade/strategy_base.py` - 글로벌 전략 함수 클래스
- `backtest/` - 백테스팅 엔진
- `research/deeplearning/` - 딥러닝 모델
- `research/analyzer/` - 시장 분석기
- `research/auxiliary_indicator/` - 보조지표
- `docs/` - 문서

### Documentation
- `docs/change_log/` - 버전별 변경 로그
- `docs/update_log/` - 상세 업데이트 기록 (날짜_파일명.md 형식)

---

## Migration Notes (V2.36.U1)

### ui_mainwindow.pyd → ui_mainwindow.py
- V1.10 소스를 기반으로 V2 모듈 구조에 맞게 마이그레이션
- 모듈명 변경: 축약형(svj, cvj) → 명시적 이름
- 새로운 기능 모듈 추가 (editer_* 시리즈)

### Known Issues
- STOM Live 기능 비활성화 (의도적)
- 일부 메서드는 패치를 통해 점진적 추가

---

## STOM_Version_2U 업데이트 규칙 (필수)

### 추론 우선 원칙 (자동 스크립트 금지)

`ui_mainwindow.pyd → ui_mainwindow.py` 동기화는 **항상 추론 기반 수동 업데이트**로 수행합니다.

- 금지: `/c/System_Trading/stom_v2u_update.py` 같은 자동 동기화 스크립트로
  `ui_mainwindow.py` 변경을 생성/확정하는 방식
- 이유: `.pyd`는 직접 분석이 불가능하므로, `set_*.py`, `ui_button_clicked_*.py`,
  `ui_update_*.py` 등의 호출/속성 사용 패턴을 해석해 인터페이스를 맞춰야 함
- 허용: 스크립트/도구는 보조 참고용 확인(파일 목록, diff 범위 확인)까지만 사용

### pyd 파일 변경 → py 파일 추론 업데이트 규칙

**STOM_Version_2에서 `.pyd` 파일이 변경(M/A)된 경우, STOM_Version_2U의 대응하는 `.py` 파일도 반드시 업데이트해야 합니다.**

#### 적용 대상
- `ui/ui_mainwindow.pyd` 변경 → `ui/ui_mainwindow.py` 추론 업데이트

#### 추론 방법
1. **변경 규모 파악**: `git show {prev}:ui/ui_mainwindow.pyd | wc -c` vs `git show {curr}:ui/ui_mainwindow.pyd | wc -c` 비교
2. **크기 변화 없음 (0 diff)**: 재컴파일로 인한 변경 → py 파일 업데이트 불필요
3. **크기 변화 있음**: 실질적 코드 변경 → 아래 방법으로 추론:
   - 해당 버전에서 새로 추가된 `set_*.py`, `ui_*.py` 파일들의 내용 분석
   - 새 파일에서 `self.ui.XXX()` 형태로 호출하는 메서드 파악
   - 해당 메서드가 `ui_mainwindow.py`에 없으면 추론하여 추가
   - 필요한 초기화 속성(`__init__`)과 import를 함께 보강

#### 추론 패턴
```python
# 새 Set* 클래스가 초기화 단계에서 호출되어야 함
SetDialogStrategy(self, self.wc)  # __init__에 추가

# 새 Set* 클래스가 self.ui.XXX()를 호출하면 mainwindow에 메서드 추가
def StrategyButtonClicked(self, cmd): button_clicked_strategy(self, cmd)
def StrategyCustomDialogShow(self):   ...

# 새 속성이 필요하면 __init__에 초기화
self.stg_btn_number = 1
self.dict_stg_btn   = dict(dict_stg_button)
```

#### 커밋 형식 (pyd 변경 반영)
```
STOM V{version}.U1.2 - {설명} (pyd 변경분 반영)

수정 내용:
- ui_mainwindow.pyd 변경사항을 ui_mainwindow.py에 추론 적용
- {구체적 변경 내용}
```

---

### pyd 파일 존재 여부 및 구조 동일성 검증 규칙

**STOM_Version_2U에는 절대 `.pyd` 파일이 존재해서는 안 됩니다.**
`ui_mainwindow.py`는 `STOM_Version_2`의 `ui_mainwindow.pyd`와 동일한 인터페이스를 제공해야 합니다.

#### 검증 방법

```bash
# 1. STOM_Version_2U에 .pyd 파일이 없는지 확인 (결과가 0이어야 함)
git ls-tree -r STOM_Version_2U --name-only | grep "\.pyd$" | wc -l

# 2. STOM_Version_2의 UI 파일들이 호출하는 mainwindow 메서드 목록 추출 (빠른 1차)
CALLED=$(git grep -h "self\.ui\." STOM_Version_2 -- "ui/*.py" 2>/dev/null | \
    grep -o "self\.ui\.[A-Z][a-zA-Z0-9_]*" | sed 's/self\.ui\.//' | sort -u)

# 3. STOM_Version_2U의 MainWindow 정의 메서드 목록 추출
DEFINED=$(git show STOM_Version_2U:ui/ui_mainwindow.py | \
    grep "^    def [A-Z]" | grep -o "def [A-Z][a-zA-Z0-9_]*" | sed 's/def //' | sort -u)

# 4. 호출되지만 정의되지 않은 누락 메서드 확인 (결과가 없어야 함)
comm -23 <(echo "$CALLED") <(echo "$DEFINED")

# 5. 메서드 누락 + 시그니처(인자 개수) 불일치 확인 (정밀 검사, 결과가 없어야 함)
python3 - <<'PY'
import ast, pathlib, re, subprocess, sys
ROOT = pathlib.Path('/mnt/c/System_Trading/STOM/STOM_V')
main_text = (ROOT / 'ui' / 'ui_mainwindow.py').read_text(encoding='utf-8')
main_mod  = ast.parse(main_text)
methods   = {}
for node in main_mod.body:
    if isinstance(node, ast.ClassDef) and node.name == 'MainWindow':
        for fn in node.body:
            if isinstance(fn, ast.FunctionDef) and re.match(r'^[A-Z][A-Za-z0-9_]*$', fn.name):
                args = fn.args.args[1:]   # skip self
                min_args = len(args) - len(fn.args.defaults)
                max_args = None if fn.args.vararg else len(args)
                methods[fn.name] = (min_args, max_args)

files = subprocess.check_output(
    "git ls-tree -r --name-only STOM_Version_2 ui | grep '\\.py$'",
    shell=True, text=True, cwd=ROOT
).splitlines()

missing = set()
arity_errors = []
for f in files:
    text = subprocess.check_output(f"git show STOM_Version_2:{f}", shell=True, text=True, cwd=ROOT)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        m = n.func.attr
        if not re.match(r'^[A-Z][A-Za-z0-9_]*$', m):
            continue
        t = n.func.value
        is_ui = (
            (isinstance(t, ast.Name) and t.id == 'ui') or
            (isinstance(t, ast.Attribute) and t.attr == 'ui' and isinstance(t.value, ast.Name) and t.value.id == 'self')
        )
        if not is_ui:
            continue
        if m not in methods:
            missing.add(m)
            continue
        min_a, max_a = methods[m]
        pos = len(n.args)
        if pos < min_a or (max_a is not None and pos > max_a):
            arity_errors.append(f"{f}:{n.lineno} {m}({pos}) vs def({min_a}..{max_a if max_a is not None else '∞'})")

if missing:
    print("MISSING:", ", ".join(sorted(missing)))
if arity_errors:
    print("\\n".join(arity_errors))
if missing or arity_errors:
    sys.exit(1)
PY
```

#### 검증 기준
- `.pyd` 파일 개수: **반드시 0**
- 누락 메서드: **반드시 없음**
- 메서드 인자 개수 불일치: **반드시 없음** (예: `BacktestProcessKill(False, False)` 호출 대비 wrapper 시그니처)
- `stom.py` 진입점: `from ui.ui_mainwindow import MainWindow` 동일 ✓
- `MainWindow(auto_run)` 생성자 호출 가능 ✓

#### 메서드 누락 시 수정 방법
1. STOM_Version_2의 해당 메서드가 어떤 UI 파일에서 호출되는지 확인
2. `ui_show_dialog.py`, `ui_button_clicked_*.py` 등에서 대응 함수 찾기
3. `ui_mainwindow.py`에 `def MethodName(self): function_name(self)` 패턴으로 추가
