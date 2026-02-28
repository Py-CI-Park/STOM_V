# STOM_Version_2U - AI Agent Instructions

## 브랜치 개요

`STOM_Version_2U`는 `STOM_Version_2`의 `.pyd` 컴파일된 바이너리 파일을
`.py` 소스 파일로 대체한 개발 브랜치입니다.

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

## 주의사항

- `.pyd` 파일은 절대 커밋하지 않음 (`.gitattributes`로 관리)
- `ui/ui_mainwindow.py`는 `stom_v2u_update.py` 스크립트가 보호함
- 새 `.py` 파일이 추가된 경우, `ui_mainwindow.py`의 import도 확인
