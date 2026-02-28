# STOM_Version_2U - AI Agent Instructions

## 브랜치 핵심 목적 (반드시 숙지)

> **이 브랜치의 목적은 단순한 일회성 변환(pyd → py)이 아닙니다.**

`STOM_Version_2U`는 `STOM_Version_2`에서 컴파일된 바이너리로만 제공되는
`ui_mainwindow.pyd`를 **항상 수정·업데이트 가능한 소스 파일** `ui_mainwindow.py`로
운영하는 **지속적 동기화 개발 브랜치**입니다.

### 이 브랜치가 존재하는 이유

`STOM_Version_2`의 핵심 UI 로직(`MainWindow`)은 `.pyd` 바이너리로만 배포되어
소스 수정이 불가능합니다. `STOM_Version_2U`는 이 `.pyd`를 소스 형태로 유지하여:

1. **수정 가능성**: UI 로직을 언제든지 수정·개선할 수 있는 구조 유지
2. **지속적 동기화**: `STOM_Version_2`가 업데이트(pyd 변경)될 때마다 `ui_mainwindow.py` 동기화
3. **동일 동작 보장**: `ui_mainwindow.py`가 `ui_mainwindow.pyd`와 동일한 인터페이스 및 동작 제공

### 두 브랜치의 관계

| 항목 | STOM_Version_2 | STOM_Version_2U |
|------|----------------|-----------------|
| `ui_mainwindow` | `.pyd` (컴파일 바이너리, 수정 불가) | `.py` (소스코드, 수정 가능) |
| 업데이트 방법 | 재컴파일 후 pyd 교체 | 추론으로 py 파일 업데이트 |
| 브랜치 성격 | 프로덕션 릴리스 브랜치 | 소스 추적·수정 개발 브랜치 |
| `stom.py` 진입점 | `from ui.ui_mainwindow import MainWindow` | 동일 |

### 브랜치 운영 원칙

- `STOM_Version_2`의 새 버전이 나오면 → `STOM_Version_2U`도 반드시 동기화
- `.pyd`는 직접 읽을 수 없으므로 → 주변 `.py` 파일 변화로 추론하여 적용
- 이 브랜치는 `STOM_Version_2`를 **항상 따라가는 살아있는 추적 브랜치**

---

## CRITICAL RULE: pyd 변경 시 py 파일 추론 업데이트 (필수)

### 규칙 설명

`STOM_Version_2`에서 `.pyd` 파일이 변경된 경우, 해당 `.pyd`를 직접 열 수 없으므로
**추론(inference)을 통해** 대응하는 `.py` 파일을 업데이트해야 합니다.

이 규칙은 **항상, 예외 없이** 적용됩니다.

### 어떤 pyd가 관리되는가

현재 관리 대상:
- `ui/ui_mainwindow.pyd` → `ui/ui_mainwindow.py`

### pyd 변경 여부 판별

```bash
# 버전 간 pyd 파일 크기 비교
git show {commit} --stat | grep pyd
# 결과 예시:
#   ui/ui_mainwindow.pyd  | Bin 788480 -> 817664 bytes  ← 실제 코드 변경
#   ui/ui_mainwindow.pyd  | Bin 817664 -> 817664 bytes  ← 재컴파일만 (무시)
```

- **크기 변화 있음**: 실제 코드 변경 → py 파일 추론 업데이트 필요
- **크기 변화 없음**: 재컴파일만 → 무시 가능

### 추론 방법

`.pyd` 파일은 직접 읽을 수 없으므로, 다음 방법으로 변경사항을 추론합니다:

1. **새 .py 파일 분석**: 해당 버전에서 추가된 `set_*.py`, `ui_button_clicked_*.py` 등 확인
   ```bash
   git show {commit} --stat | grep "^+ *ui/"
   ```

2. **기존 .py 파일 diff 분석**: 변경된 UI 모듈들이 `self.ui.*` 메서드/속성을 새로 참조하는지 확인
   ```bash
   git show {commit} -- ui/{changed_file}.py | grep "self\.ui\."
   ```

3. **커밋 메시지 분석**: 어떤 기능이 추가/변경되었는지 파악

4. **패턴 매칭**: 기존 코드 패턴과 유사한 구조로 누락된 메서드/속성 추론

### 추론 적용 예시

#### V2.39 사례 (pyd -29KB)
- **단서**: `set_dialog_strategy.py` 신규 추가, `StrategyButtonClicked` 호출 발견
- **적용**: `ui_mainwindow.py`에 4개 메서드 + 2개 속성 추가
  ```python
  # __init__에 추가
  SetDialogStrategy(self, self.wc)
  self.stg_btn_number = 1
  self.dict_stg_btn   = dict(dict_stg_button)
  # 메서드 추가
  def StrategyButtonClicked(self, cmd):  button_clicked_strategy(self, cmd)
  def StrategyCustomBottunDel(self):     button_clicked_strategy_delete(self)
  def StrategyCustomBottunSave(self):    button_clicked_strategy_save(self)
  def StrategyCustomDialogShow(self):    ...
  ```

#### V2.40 사례 (pyd +9.7KB)
- **단서**: `ui_get_label_text.py` 등에서 `ui.dict_findex_*` 참조로 변경
- **적용**: `ui_mainwindow.py` `__init__`에 10개 팩터 인덱스 딕셔너리 초기화
  ```python
  self.dict_findex_stock_tick   = {name: i for i, name in enumerate(list_stock_tick)}
  self.dict_findex_stock_min    = {name: i for i, name in enumerate(list_stock_min)}
  # ... (총 10개)
  ```

#### V2.42 사례 (pyd +2KB)
- **단서**: `ui_button_clicked_strategy.py`에서 임계값 200→205 변경
- **적용**: `StrategyCustomDialogShow`의 임계값 동기화

### 커밋 형식

```
STOM V{version}.U1.2 - {설명} (pyd 변경분 반영)

수정 내용:
- ui/ui_mainwindow.py: {추가된 내용}
- 추론 근거: {어떤 파일/변경에서 추론했는지}

pyd 분석: V{version}에서 ui_mainwindow.pyd {크기변화} →
  {새로 발견된 set_*.py 등}이 요구하는 mainwindow 변경사항 반영
```

---

## 프로젝트 구조

```
STOM_V/                    (STOM_Version_2U 브랜치)
├── ui/
│   ├── ui_mainwindow.py   ← pyd 대체 소스 (핵심 파일)
│   ├── set_dialog_*.py    ← 다이얼로그 초기화 클래스
│   ├── ui_button_clicked_*.py  ← 버튼 클릭 핸들러
│   ├── ui_draw_*.py       ← 차트 그리기 클래스
│   └── ui_update_*.py     ← UI 업데이트 함수
├── utility/
│   └── setting.py         ← 팩터 리스트, 설정값 정의
├── stock/                 ← 주식 트레이딩 로직
├── coin/                  ← 암호화폐 트레이딩 로직
├── backtester/            ← 백테스팅 엔진
├── CLAUDE.md              ← Claude 작업 규칙 (pyd→py 규칙 포함)
└── AGENTS.md              ← AI 에이전트 지침 (이 파일)
```

---

## 업데이트 절차

`STOM_Version_2`의 새 버전을 `STOM_Version_2U`에 적용할 때:

1. 스크립트 실행: `/c/System_Trading/stom_v2u_update.py`
2. pyd 크기 변화 확인: 각 버전별 `ui_mainwindow.pyd` 크기 비교
3. 크기 변화가 있는 버전: 추론으로 `ui_mainwindow.py` 업데이트
4. 패치 커밋: `STOM V{version}.U1.2` 형식으로 커밋

---

## CRITICAL RULE: pyd 파일 부재 및 구조 동일성 검증

### 규칙
1. **STOM_Version_2U에는 `.pyd` 파일이 절대 존재하면 안 됩니다**
2. **`ui_mainwindow.py`는 `STOM_Version_2`의 `ui_mainwindow.pyd`와 동일한 공개 인터페이스를 제공해야 합니다**
3. **stom.py 진입점은 양 브랜치가 동일해야 합니다**: `from ui.ui_mainwindow import MainWindow`

### 검증 명령어 (업데이트 후 반드시 실행)

```bash
# Step 1: .pyd 파일 없음 확인 (0이어야 함)
git ls-tree -r STOM_Version_2U --name-only | grep "\.pyd$" | wc -l

# Step 2: 누락 메서드 확인 (출력 없어야 함)
cd /c/System_Trading/STOM/STOM_V
CALLED=$(git grep -h "self\.ui\." STOM_Version_2 -- "ui/*.py" 2>/dev/null | \
    grep -o "self\.ui\.[A-Z][a-zA-Z0-9_]*" | sed 's/self\.ui\.//' | sort -u)
DEFINED=$(cat ui/ui_mainwindow.py | grep "^    def [A-Z]" | \
    grep -o "def [A-Z][a-zA-Z0-9_]*" | sed 's/def //' | sort -u)
comm -23 <(echo "$CALLED") <(echo "$DEFINED")
```

### 메서드 누락 발견 시 수정 패턴
```python
# ui_mainwindow.py 끝 부분에 추가
# from ui.ui_show_dialog import * 로 함수 임포트됨
def MethodName(self):    function_name(self)         # 단일 인자
def MethodName(self, x): function_name(self, x)      # 다중 인자
```

### 누락 메서드 찾기
```bash
# 어떤 파일에서 self.ui.MethodName을 호출하는지 확인
git grep -rn "MethodName" STOM_Version_2 -- "ui/*.py"
# 대응 함수가 어디 있는지 확인
git grep -rn "def method_name\|def function_name" STOM_Version_2U -- "ui/*.py"
```

---

## 주의사항

- `.pyd` 파일은 절대 커밋하지 않음 (`.gitattributes`로 관리)
- `ui/ui_mainwindow.py`는 `stom_v2u_update.py` 스크립트가 보호함
- 새 `.py` 파일이 추가된 경우, `ui_mainwindow.py`의 import도 확인
- **업데이트 후 반드시 위 검증 명령어 실행하여 누락 메서드 없는지 확인**
