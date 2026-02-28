# STOM Project Guidelines

## Version Naming Convention

### Format
```
V{major}.{minor}.U{patch}.{hotfix}
```

### Rules
1. **Major (V2)**: 대규모 아키텍처 변경
2. **Minor (.49)**: 기능 추가 또는 중요 업데이트
3. **Patch (U1)**: 마이그레이션, 리팩토링, 중간 규모 변경
4. **Hotfix (.2, .3, ...)**: 버그 수정, 누락된 메서드 추가

### Examples
- `V2.49` - 기본 릴리스
- `V2.49.U1` - 중간 규모 마이그레이션/리팩토링
- `V2.49.U1.2` - 추가 버그 수정

---

## STOM_Version_2 브랜치 업데이트 방법론

### 개요
`STOM_Version_2` 브랜치는 공식 STOM 배포 버전을 순차적으로 기록하는 브랜치입니다.
각 공식 배포 버전(zip 파일)을 하나씩 커밋으로 남겨 버전 이력을 관리합니다.

### 커밋 규칙

#### 커밋 제목
```
STOM V{major}.{minor}
```
예: `STOM V2.49`

#### 커밋 본문
`_update.txt` 파일에서 해당 버전에 해당하는 섹션을 그대로 사용합니다.
```
YYYY-MM-DD V{major}.{minor}
1. 변경사항 1
2. 변경사항 2
...
```

#### 실제 예시
```
STOM V2.37

2026-01-31 V2.37
1. 1초스냅샷용 차트도 현재가 차트를 크게 변경
2. 실시간 차트 축소확대 시 바로 복귀되는 부분 수정
3. 차트 X축 동기화 방법 변경
4. 데이터베이스 읽기 쿼리 속도 개선
```

### 자동 업데이트 프로세스

#### 준비물
- 업데이트 zip 파일: `C:\Users\parkc\Downloads\STOM_temp\STOM_V{버전}.zip`
- 자동화 스크립트: `C:\System_Trading\stom_v2_update.py`

#### 새 버전 업데이트 방법
1. 새 zip 파일을 `C:\Users\parkc\Downloads\STOM_temp\` 폴더에 저장
2. 아래 명령으로 자동 처리:

```bash
# 모든 미반영 버전 자동 처리
python C:/System_Trading/stom_v2_update.py

# 특정 버전부터 처리
python C:/System_Trading/stom_v2_update.py --from 2.50

# 실제 커밋 없이 미리보기
python C:/System_Trading/stom_v2_update.py --dry-run
```

#### 스크립트 동작 방식
1. `STOM_temp` 폴더에서 `STOM_V*.zip` 파일 목록을 버전 순으로 정렬
2. 현재 `STOM_Version_2` 브랜치의 최신 버전 확인
3. 미반영 버전의 zip 파일만 선택
4. 각 zip 파일에 대해:
   - `STOM_Version_2` 브랜치 체크아웃
   - zip 파일을 레포 디렉터리에 압축 해제 (기존 파일 덮어쓰기)
   - zip에 포함된 파일만 선택적으로 스테이징 (레포 전용 파일 보호)
   - `_update.txt`에서 해당 버전 섹션 추출하여 커밋 메시지 자동 생성
   - 커밋 생성

#### 스테이징 규칙
- `git add -A` 대신 zip 파일 목록 기준으로만 스테이징
- `CLAUDE.md`, `AGENTS.md`, `scripts/` 등 레포 전용 파일은 스테이징되지 않음
- `.omx/`, `.shellhive.env` 등 untracked 파일도 스테이징되지 않음

### 수동 업데이트 방법 (레거시)

자동화 스크립트 없이 수동으로 진행할 경우:

```bash
# 1. STOM_Version_2 브랜치 체크아웃
git checkout STOM_Version_2

# 2. zip 파일 압축 해제 (레포 디렉터리에 직접 압축 해제)
# Windows: 탐색기에서 "여기에 압축 풀기"

# 3. 변경된 파일 확인
git diff --stat

# 4. zip에 포함된 파일만 스테이징 (예시)
git add _update.txt backtester/ ui/ coin/ stock/ future/ utility/ stom.py ...

# 5. _update.txt에서 해당 버전 섹션 확인 후 커밋
git commit -m "STOM V2.50

2026-03-01 V2.50
1. 변경사항 설명
..."
```

---

## Project Structure

### Key Directories
- `ui/` - UI 관련 모듈 (PyQt5)
- `utility/` - 유틸리티 함수 및 클래스
- `stock/` - 주식 트레이딩 로직
- `coin/` - 암호화폐 트레이딩 로직
- `backtester/` - 백테스팅 엔진
- `future/` - 해외선물 트레이딩 로직
- `lecture/` - 강의 및 예제 코드
- `scripts/` - 유틸리티 스크립트
- `docs/` - 문서

### Documentation
- `_update.txt` - 전체 버전 업데이트 내역 (최신 버전이 상단)
- `docs/change_log/` - 버전별 변경 로그
- `docs/update_log/` - 상세 업데이트 기록 (날짜_파일명.md 형식)

---

## Migration Notes

### V2.36.U1: ui_mainwindow.pyd → ui_mainwindow.py
- V1.10 소스를 기반으로 V2 모듈 구조에 맞게 마이그레이션
- 모듈명 변경: 축약형(svj, cvj) → 명시적 이름
- 새로운 기능 모듈 추가 (editer_* 시리즈)

### Known Issues
- STOM Live 기능 비활성화 (의도적)
- 일부 메서드는 패치를 통해 점진적 추가
