# STOM Project Guidelines

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

### Key Directories
- `ui/` - UI 관련 모듈 (PyQt5)
- `utility/` - 유틸리티 함수 및 클래스
- `stock/` - 주식 트레이딩 로직
- `coin/` - 암호화폐 트레이딩 로직
- `backtester/` - 백테스팅 엔진
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
