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
