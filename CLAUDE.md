# STOM Project Guidelines (STOM_Version_2)

## 브랜치 목적

`STOM_Version_2` 브랜치는 **STOM 공식 업스트림 원본의 순차 이력**을 관리합니다.
pyd 파일을 포함한 원본 그대로를 보존하며, 하위 브랜치(2U, 2U_C 등)의 기준점입니다.

> **워크트리 위치**: `STOM_V/` (메인 레포)
> **관련 문서**: [`docs/WORKTREE_STRATEGY.md`](docs/WORKTREE_STRATEGY.md)

---

## 업데이트 방법

### 방법 1: V2.58 이하 (zip 기반, 레거시)

```bash
# 1. zip 파일 저장
C:\Users\parkc\Downloads\STOM_temp\STOM_V{버전}.zip

# 2. 자동 업데이트 스크립트 실행
python C:/System_Trading/stom_v2_update.py
git push origin STOM_Version_2
```

> 상세 → [`docs/stom_v2_update_guide.md`](docs/stom_v2_update_guide.md)

### 방법 2: V2.59 이후 (devstom git 기반)

```bash
# 1. devstom 레포에서 새 버전 확인
cd /c/System_Trading/STOM/STOM_devstom
git pull origin master
head -5 _update.txt   # 최신 버전 확인

# 2. 해당 버전 체크포인트 export
mkdir -p /tmp/stom_export
git archive <버전커밋해시> | tar -x -C /tmp/stom_export/

# 3. STOM_V에 오버레이 (dry-run 먼저)
cd /c/System_Trading/STOM/STOM_V
rsync -avn --delete \
  --exclude='.git' --exclude='.gitignore' --exclude='.omc/' \
  --exclude='CLAUDE.md' --exclude='AGENTS.md' \
  --exclude='cli/' --exclude='tests/' --exclude='docs/' \
  --exclude='scripts/' --exclude='research/' --exclude='temp/' \
  --exclude='requirements64-2.txt' \
  /tmp/stom_export/ ./
# → 삭제 대상 검토 후 -n 제거하여 실제 적용

# 4. 명시적 스테이징 후 커밋 (git add -A 사용 금지)
git add -u
git add backtest/ trade/ ui/ utility/
git add stom.py stom.bat _update.txt _license.txt requirements*.txt
git commit -m "STOM V{버전}"
```

> 상세 → [`docs/UPSTREAM_SYNC_STRATEGY.md`](docs/UPSTREAM_SYNC_STRATEGY.md)

---

## 이 브랜치에서 하는 일

- 업스트림 새 버전 반영 (오버레이 방식)
- 변경 내역 파악 후 하위 브랜치(2U)로 전파 판단
- 문서 업데이트 (`docs/` 디렉토리)

## 이 브랜치에서 하지 않는 일

- 직접 소스 코드 수정 (업스트림 원본 유지)
- CLI 기능 개발 (→ wt-dev에서 수행)
- pyd→py 추론 (→ wt-2u에서 수행)

---

## 커밋 규칙

| 항목 | 규칙 |
|------|------|
| 제목 | `STOM V{major}.{minor}` |
| 본문 | `_update.txt`의 해당 버전 섹션 전체 |
| 단위 | 배포 버전 1개 = 커밋 1개 |
| 스테이징 | 업스트림 파일만 (`CLAUDE.md`, `AGENTS.md`, `docs/`, `scripts/`, `cli/`, `tests/` 제외) |

---

## 워크트리 전체 구성

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| **`STOM_V/`** (여기) | `STOM_Version_2` | 업스트림 원본 추적 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | 커스텀 개발 (CLI 등) |
| `STOM_V.wt-lab/` | `research/*` | 실험 |

---

## 프로젝트 구조

| 디렉터리 | 용도 |
|----------|------|
| `ui/` | UI 모듈 (PyQt5, pyd 포함) |
| `utility/` | 유틸리티 클래스 |
| `backtest/` | 백테스팅 엔진 |
| `trade/` | 트레이딩 (주식/코인/해외선물) |
| `docs/` | 문서 |
| `_update.txt` | 전체 버전 업데이트 이력 (최신 버전이 상단) |
