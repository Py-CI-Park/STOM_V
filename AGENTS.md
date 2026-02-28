# STOM_Version_2 브랜치 - AI 에이전트 가이드

## 브랜치 목적

`STOM_Version_2` 브랜치는 공식 STOM 배포 버전의 순차 이력을 관리합니다.
이 브랜치에서 작업 시 반드시 아래 규칙을 따르세요.

---

## 핵심 규칙: STOM_Version_2 업데이트 방법론

### 1. 커밋은 배포 버전 단위로만

각 커밋은 반드시 하나의 공식 STOM 배포 버전(zip 파일)에 대응합니다.
- ✅ `STOM V2.50` - 올바른 커밋
- ❌ 여러 버전을 하나의 커밋으로 합치기
- ❌ 배포 버전과 무관한 코드 수정을 함께 커밋

### 2. 커밋 메시지 형식

```
STOM V{major}.{minor}

{_update.txt의 해당 버전 섹션 전체}
```

**예시:**
```
STOM V2.50

2026-03-01 V2.50
1. 새로운 기능 A 추가
2. 버그 B 수정
3. 성능 C 개선
```

### 3. 스테이징 규칙

zip 파일에 포함된 파일만 스테이징합니다. 레포 전용 파일(CLAUDE.md, AGENTS.md, scripts/ 등)은 절대 스테이징하지 않습니다.

### 4. 버전 순서 보장

항상 버전 번호 오름차순으로 커밋합니다. 버전을 건너뛰거나 역순으로 적용하지 않습니다.

---

## 자동 업데이트 프로세스

### 스크립트 위치
```
C:\System_Trading\stom_v2_update.py
```

### 사용법

```bash
# 전체 자동 처리 (권장)
python C:/System_Trading/stom_v2_update.py

# 미리보기 (커밋 없음)
python C:/System_Trading/stom_v2_update.py --dry-run

# 특정 버전부터 처리
python C:/System_Trading/stom_v2_update.py --from 2.50
```

### 스크립트 동작 흐름

```
STOM_temp 폴더 스캔
    ↓
미반영 zip 파일 목록화 (버전 순 정렬)
    ↓
STOM_Version_2 브랜치 체크아웃
    ↓
[각 버전에 대해 반복]
    zip 압축 해제 → 레포에 파일 복사
        ↓
    zip 파일 목록 기준으로만 git add
        ↓
    _update.txt에서 버전 섹션 추출
        ↓
    git commit (제목: "STOM V{버전}", 본문: 버전 섹션)
```

---

## 새 버전 추가 워크플로우

### 자동 (권장)
1. `C:\Users\parkc\Downloads\STOM_temp\` 에 `STOM_V{버전}.zip` 저장
2. `python C:/System_Trading/stom_v2_update.py` 실행
3. 완료 확인: `git log --oneline -5`

### 수동 (스크립트 없이)
1. `git checkout STOM_Version_2`
2. zip 파일을 레포 디렉터리에 압축 해제
3. `git diff --stat` 으로 변경사항 확인
4. zip 포함 파일만 선택적으로 `git add`
5. `_update.txt` 에서 해당 버전 섹션 확인
6. 커밋 생성

---

## 파일 구조 이해

### zip 파일 구조
각 `STOM_V*.zip`은 전체 STOM 배포본입니다:
- 모든 Python 소스 파일 (`.py`)
- 컴파일된 바이너리 (`ui_mainwindow.pyd`)
- 리소스 파일 (아이콘, 설정 등)
- `_update.txt` (전체 버전 이력 누적)

### _update.txt 구조
```
YYYY-MM-DD V{최신버전}
1. ...

YYYY-MM-DD V{이전버전}
1. ...
```
최신 버전이 파일 상단에 위치합니다.

### 레포 전용 파일 (zip에 미포함 → 보호됨)
- `CLAUDE.md` - 프로젝트 가이드라인
- `AGENTS.md` - 이 파일
- `scripts/` - 유틸리티 스크립트
- `Dockerfile`, `docker-compose.yml`
- `docs/`, `requirements-*.txt`

---

## 주의사항

### 브랜치 혼동 방지
- `STOM_Version_2`: 배포 버전 이력 전용 (이 브랜치)
- `STOM_Version_2U`: 개발/패치 작업용
- `main`: 메인 개발 브랜치

### 절대 하지 말 것
- `git add -A` 사용 (untracked 파일 오염 위험)
- 여러 버전을 하나의 커밋으로 합치기
- `git rebase` 또는 `git reset --hard` (이력 파괴)
- 다른 브랜치의 개발 코드를 STOM_Version_2에 직접 커밋

---

## 현재 상태 (2026-02-28 기준)

- **최신 커밋 버전**: STOM V2.49
- **커밋 수**: V2.25 ~ V2.49 (연속 이력)
- **STOM_temp 처리 완료**: V2.37 ~ V2.49 (13개 버전)
