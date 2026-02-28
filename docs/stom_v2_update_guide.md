# STOM_Version_2 업데이트 가이드

> 이 문서는 STOM 공식 배포 버전을 `STOM_Version_2` 브랜치에 반영하는 전체 프로세스를 설명합니다.
> CLAUDE.md, AGENTS.md에서 이 문서를 참조합니다.

---

## 1. 사전 준비

| 항목 | 경로 |
|------|------|
| 자동화 스크립트 | `C:\System_Trading\stom_v2_update.py` |
| 레포 내 스크립트 사본 | `scripts\stom_v2_update.py` |
| 업데이트 zip 저장 폴더 | `C:\Users\parkc\Downloads\STOM_temp\` |
| 대상 브랜치 | `STOM_Version_2` |

zip 파일 명명 규칙: `STOM_V{major}.{minor}.zip` (예: `STOM_V2.50.zip`)

---

## 2. Python으로 직접 실행하는 방법

### 기본 실행 (모든 미반영 버전 자동 처리)

```bash
python C:/System_Trading/stom_v2_update.py
```

### 옵션

```bash
# 실제 커밋 없이 미리보기 (파일 복사 없음)
python C:/System_Trading/stom_v2_update.py --dry-run

# 특정 버전부터만 처리
python C:/System_Trading/stom_v2_update.py --from 2.50

# 조합
python C:/System_Trading/stom_v2_update.py --dry-run --from 2.50
```

### 실행 흐름

```
스크립트 실행
  │
  ├─ STOM_temp 폴더에서 STOM_V*.zip 파일 목록 수집 (버전 순 정렬)
  ├─ STOM_Version_2 브랜치 현재 버전 확인 (git log)
  ├─ 미반영 버전 필터링 (현재 버전 초과)
  │
  └─ [각 버전에 대해 반복]
       ├─ STOM_Version_2 브랜치 체크아웃
       ├─ zip 압축 해제 → 임시 폴더 (C:/tmp/stom_extract_temp)
       ├─ 임시 폴더 → 레포 디렉터리로 파일 복사 (덮어쓰기)
       ├─ zip 포함 파일만 선택적 git add (CLAUDE.md 등 보호)
       ├─ _update.txt에서 해당 버전 섹션 추출
       └─ git commit ("STOM V{버전}" + 버전 섹션 본문)
```

### 스크립트 소스 위치

```
레포:    scripts/stom_v2_update.py
실행본:  C:\System_Trading\stom_v2_update.py
```

두 파일은 동일합니다. 실행본을 수정했다면 레포 사본도 같이 업데이트하세요.

---

## 3. Claude Code에게 업데이트 지시하는 방법

새 버전 zip 파일을 `STOM_temp` 폴더에 저장한 뒤, 아래 프롬프트를 그대로 Claude Code에게 붙여넣으세요.

### 단순 실행 프롬프트 (복사해서 바로 사용)

```
STOM_Version_2 브랜치 업데이트를 진행해주세요.

C:\Users\parkc\Downloads\STOM_temp\ 폴더에 새 STOM 버전 zip 파일이 있습니다.
docs/stom_v2_update_guide.md 의 프로세스에 따라 다음을 실행해주세요:

1. python C:/System_Trading/stom_v2_update.py --dry-run 으로 미리보기 확인
2. 이상 없으면 python C:/System_Trading/stom_v2_update.py 로 실제 업데이트 실행
3. git log STOM_Version_2 --oneline -5 로 커밋 확인
4. git push origin STOM_Version_2 로 원격 push
```

### Ralph 모드로 자동화 (복사해서 바로 사용)

```
/ralph STOM_Version_2 브랜치 업데이트:
1. python C:/System_Trading/stom_v2_update.py --dry-run 실행하여 대기 버전 확인
2. 이상 없으면 python C:/System_Trading/stom_v2_update.py 실행
3. 커밋 이력 확인: git log STOM_Version_2 --oneline -5
4. git push origin STOM_Version_2
5. docs/stom_v2_update_guide.md 의 커밋 규칙 준수 확인
```

---

## 4. 커밋 규칙 (참조용)

### 커밋 제목
```
STOM V{major}.{minor}
```

### 커밋 본문
`_update.txt`에서 해당 버전 섹션을 그대로 사용:
```
YYYY-MM-DD V{major}.{minor}
1. 변경사항 1
2. 변경사항 2
```

### 실제 예시
```
STOM V2.50

2026-03-15 V2.50
1. 신규 기능 A 추가
2. 버그 B 수정
```

---

## 5. 스테이징 규칙 (중요)

`git add -A` 대신 **zip 포함 파일만 선택적으로 스테이징**합니다.

보호되는 레포 전용 파일 (절대 스테이징하지 않음):
- `CLAUDE.md`
- `AGENTS.md`
- `docs/` 폴더
- `scripts/` 폴더
- `Dockerfile`, `docker-compose.yml`
- `.omx/`, `.omc/`, `.venv-ralph/` 등 untracked 폴더

---

## 6. 수동 업데이트 방법 (스크립트 없이)

```bash
# 1. STOM_Version_2 브랜치 체크아웃
git checkout STOM_Version_2

# 2. zip 압축 해제 (탐색기 또는 명령줄)
cd C:/tmp && mkdir stom_extract && cd stom_extract
unzip C:/Users/parkc/Downloads/STOM_temp/STOM_V2.50.zip

# 3. 파일 복사 (레포 디렉터리로)
xcopy /E /Y C:/tmp/stom_extract/ C:/System_Trading/STOM/STOM_V/

# 4. 변경사항 확인
git diff --stat

# 5. _update.txt에서 해당 버전 섹션 확인 후 스테이징
git add _update.txt backtester/ ui/ coin/ stock/ future/ utility/ stom.py
# (변경된 파일만 선택적으로 추가)

# 6. 커밋
git commit -m "STOM V2.50

2026-03-15 V2.50
1. 변경사항..."

# 7. Push
git push origin STOM_Version_2
```

---

## 7. 문제 해결

### git index.lock 오류
```bash
rm -f C:/System_Trading/STOM/STOM_V/.git/index.lock
```

### 브랜치 체크아웃 실패 (uncommitted changes)
```bash
# 현재 브랜치 변경사항 임시 저장
git stash
git checkout STOM_Version_2
# 작업 후 복귀
git checkout STOM_Version_2U-cli-research-dev-update-20260212
git stash pop
```

### 잘못된 커밋 되돌리기
```bash
# 마지막 커밋 취소 (파일은 유지)
git reset --soft HEAD~1
```

---

## 8. 브랜치 구조 참조

| 브랜치 | 용도 |
|--------|------|
| `STOM_Version_2` | 공식 배포 버전 이력 (이 가이드 대상) |
| `STOM_Version_2U` | 개발/패치 작업용 |
| `main` | 메인 개발 브랜치 |
