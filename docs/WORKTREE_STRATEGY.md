# STOM 워크트리 병렬 개발 전략

- 작성일: 2026-03-18
- 적용 대상: 모든 STOM 활성 브랜치

---

## 1. 개요

STOM 프로젝트는 업스트림 추적, py 소스 동기화, 커스텀 개발, 연구 실험 등
여러 개발 방향이 동시에 진행된다. Git worktree를 활용하여 각 방향을
독립 디렉토리에서 병렬로 작업하고, AI Agent(Claude Code 등)를 동시 실행한다.

### 왜 워크트리인가?

| 기존 방식 | 워크트리 방식 |
|-----------|-------------|
| 하나의 디렉토리에서 브랜치 전환 | 4개 디렉토리에서 동시 작업 |
| 전환 시 unstaged 변경 충돌 위험 | 각 디렉토리가 독립 — 충돌 없음 |
| AI Agent 1개만 실행 | AI Agent 최대 4개 병렬 실행 |
| 컨텍스트 전환 비용 | 각 디렉토리가 항상 해당 브랜치 상태 유지 |

---

## 2. 최종 구성

```
C:\System_Trading\STOM\
│
├── STOM_V/              → STOM_Version_2         (메인 레포)
│                           업스트림 원본 기준점
│                           V2.59+ 나오면 여기서 pull
│
├── STOM_V.wt-2u/        → STOM_Version_2U        (워크트리)
│                           pyd→py 추론 동기화
│                           V2 변경분을 py 소스로 반영
│
├── STOM_V.wt-dev/       → STOM_Version_2U_C      (워크트리, 주력 개발)
│                           커스텀 개발 홈 브랜치
│                           CLI, UI 등 feature 브랜치 분기점
│
└── STOM_V.wt-lab/       → research/*             (워크트리)
                            실험적 기능 프로토타입
                            새 research 브랜치 생성하여 사용
```

### 네이밍 규칙

- 워크트리 폴더: `STOM_V.wt-{용도}` — `.wt-` 접두사로 워크트리임을 표시
- `STOM_V` (메인)에는 접미사 없음

---

## 3. 브랜치 계층 구조

```
STOM_Version_2 (V2.58)               ← 메인 레포 (STOM_V/)
    │                                    업스트림 공식 버전 (pyd 포함)
    │
    └── STOM_Version_2U (V2.58.U1.2) ← wt-2u
         │                               pyd 제거, py 소스 운영
         │
         └── STOM_Version_2U_C       ← wt-dev (홈 브랜치)
              │                          커스텀 교정 + 개발 기지
              │
              ├── CLI_v251            (히스토리 참조용)
              │    └── CLI_v258       (활성 CLI 개발)
              │         └── feature/* (새 기능 브랜치)
              │
              └── feature/ui-*       (UI 보강 등)

research/*                            ← wt-lab (독립 실험)
```

---

## 4. 각 워크트리 역할과 작업 방법

### 4.1 STOM_V/ (메인 레포) — 업스트림 추적

**브랜치**: `STOM_Version_2`
**역할**: STOM 공식 버전의 기준점. 새 버전(V2.59 등) 추적.

```bash
cd C:\System_Trading\STOM\STOM_V
# 새 업스트림 버전 확인/반영
git pull origin STOM_Version_2
```

**이 디렉토리에서 하는 일:**
- 업스트림 V2 신규 버전 pull
- pyd 파일 변경 확인 (크기 비교 등)
- 변경 내용 파악 후 wt-2u로 전파 판단

**이 디렉토리에서 하지 않는 일:**
- 직접 코드 수정 (업스트림 원본 유지)
- CLI/커스텀 기능 개발

### 4.2 STOM_V.wt-2u/ — pyd→py 동기화

**브랜치**: `STOM_Version_2U`
**역할**: V2의 pyd 바이너리 변경을 py 소스에 추론 반영.

```bash
cd C:\System_Trading\STOM\STOM_V.wt-2u
# V2 변경분 확인 후 py 소스에 추론 반영
# 새 메서드 추가, 시그니처 보강 등
```

**이 디렉토리에서 하는 일:**
- V2에서 pyd 변경 시 대응하는 py 파일 업데이트
- `ui/ui_mainwindow.py` 추론 업데이트
- 새 UI 파일(`set_*.py`, `ui_*.py`) 분석 → 인터페이스 맞춤

**이 디렉토리에서 하지 않는 일:**
- CLI 기능 개발
- 커스텀 기능 추가

### 4.3 STOM_V.wt-dev/ — 주력 개발

**홈 브랜치**: `STOM_Version_2U_C`
**역할**: 커스텀 개발의 기지. CLI, UI 보강 등 모든 feature 브랜치의 분기점.

```bash
cd C:\System_Trading\STOM\STOM_V.wt-dev

# CLI 개발 시
git switch STOM_Version_2U_C_CLI_v258
git checkout -b feature/cli-new-feature
# ... 작업 ...
git switch STOM_Version_2U_C   # 홈으로 복귀

# UI 보강 시
git checkout -b feature/ui-fix-something
# ... 작업 ...
git switch STOM_Version_2U_C   # 홈으로 복귀
```

**이 디렉토리에서 하는 일:**
- CLI 자동화 기능 개발 (discovery, formula, strategy 등)
- UI/py 소스 커스텀 교정
- 2U에서 머지받은 업스트림 변경 통합
- feature 브랜치 생성/작업/머지

**브랜치 전환 규칙:**
- 홈 = `STOM_Version_2U_C` (작업 없을 때 여기)
- 작업 = `feature/*` 또는 `CLI_v258` (실제 코딩)

### 4.4 STOM_V.wt-lab/ — 연구 실험

**브랜치**: `research/*` (새로 생성)
**역할**: 실험적 기능 프로토타입. 실패해도 다른 브랜치에 영향 없음.

```bash
cd C:\System_Trading\STOM\STOM_V.wt-lab
# 새 실험 시작
git checkout -b research/new-ml-model
# ... 실험 ...
# 성공 시: wt-dev에서 머지
# 실패 시: 브랜치 유지 (히스토리 보존)
```

**이 디렉토리에서 하는 일:**
- 새 분석 방법 실험
- ML 모델 프로토타입
- 새 데이터 소스 연동 테스트
- PoC (Proof of Concept) 개발

---

## 5. 업스트림 동기화 순서

V2에 새 버전(예: V2.59)이 나왔을 때:

```
[1] STOM_V/ (V2)
    V2.59 pull → 변경 내용 파악
        │
        ▼
[2] STOM_V.wt-2u/ (2U)
    pyd 변경분 → py 소스에 추론 반영
    테스트 확인
        │
        ▼
[3] STOM_V.wt-dev/ (2U_C)
    2U 변경분 머지 → 충돌 해결
    CLI 테스트 확인
        │
        ▼
    완료: CLI_v258 또는 새 feature 브랜치에도 머지
```

**이 순서를 지키면 충돌을 최소화**할 수 있습니다.
상위 브랜치에서 하위 브랜치로 한 단계씩 전파합니다.

---

## 6. AI Agent (Claude Code) 실행 방법

### 6.1 기본 실행

각 워크트리 디렉토리에서 독립적으로 `claude` 명령을 실행합니다.

```bash
# 터미널 1: 업스트림 확인
cd C:\System_Trading\STOM\STOM_V
claude

# 터미널 2: pyd→py 동기화
cd C:\System_Trading\STOM\STOM_V.wt-2u
claude

# 터미널 3: CLI 개발 (주력)
cd C:\System_Trading\STOM\STOM_V.wt-dev
claude

# 터미널 4: 연구 실험
cd C:\System_Trading\STOM\STOM_V.wt-lab
claude
```

### 6.2 독립성 보장

| 항목 | 공유 여부 | 설명 |
|------|----------|------|
| git 히스토리/브랜치 | 공유 | 모든 워크트리가 동일 .git 참조 |
| 작업 디렉토리 파일 | **독립** | 각 디렉토리가 해당 브랜치의 파일 보유 |
| `_database/*.db` | **독립** (수동 복사) | .gitignore이므로 자동 복사 안 됨 |
| `CLAUDE.md` | 공유 (git 추적) | 각 브랜치에 존재하면 자동 체크아웃 |
| `~/.claude/` 설정 | 공유 | 사용자 전역 설정 (모든 세션 공유) |
| AI Agent 컨텍스트 | **독립** | 각 세션이 별도 대화/컨텍스트 |

### 6.3 주의사항

- **동시 실행 수**: 2~3개가 적절 (API 비용 × 세션 수)
- **같은 브랜치 금지**: 두 워크트리에서 동일 브랜치를 동시 체크아웃 불가
- **DB 파일**: 필요한 워크트리에 수동 복사 후 사용
- **커밋 동기**: 한 워크트리에서 커밋하면 다른 워크트리에서 즉시 `git log`로 확인 가능 (같은 .git)

---

## 7. 워크트리 관리 명령어

### 생성

```bash
cd C:\System_Trading\STOM\STOM_V   # 메인 레포에서 실행
git worktree add ../STOM_V.wt-2u   STOM_Version_2U
git worktree add ../STOM_V.wt-dev  STOM_Version_2U_C
git worktree add ../STOM_V.wt-lab  -b research/init  # 새 브랜치 생성
```

### 확인

```bash
git worktree list
```

### 제거 (브랜치/히스토리 보존)

```bash
git worktree remove ../STOM_V.wt-2u
git worktree remove ../STOM_V.wt-dev
git worktree remove ../STOM_V.wt-lab
```

### 완전 복귀 (워크트리 없는 단일 레포)

```bash
git worktree remove ../STOM_V.wt-2u
git worktree remove ../STOM_V.wt-dev
git worktree remove ../STOM_V.wt-lab
cd C:\System_Trading\STOM\STOM_V
git switch STOM_Version_2U_C_CLI_v258  # 원하는 브랜치로 전환
# → 기존과 완전히 동일한 상태
```

---

## 8. DB 파일 초기 세팅

워크트리 생성 후 필요한 DB 파일을 복사합니다.

```bash
# wt-dev에 DB 복사 (CLI 개발에 필요)
cp -r C:\System_Trading\STOM\STOM_V\_database C:\System_Trading\STOM\STOM_V.wt-dev\_database

# wt-lab에 DB 복사 (연구 실험에 필요)
cp -r C:\System_Trading\STOM\STOM_V\_database C:\System_Trading\STOM\STOM_V.wt-lab\_database

# wt-2u는 보통 DB 불필요 (pyd→py 추론 작업만)
```

---

## 9. FAQ

**Q: 워크트리를 나중에 없앨 수 있나요?**
A: 네. `git worktree remove`로 디렉토리만 삭제됩니다. 브랜치, 커밋, 히스토리는 전부 보존됩니다. 언제든 다시 만들 수 있습니다.

**Q: 워크트리 간에 커밋이 공유되나요?**
A: 네. 모든 워크트리가 동일한 `.git` 저장소를 공유합니다. wt-dev에서 커밋하면 wt-2u에서도 `git log`로 즉시 볼 수 있습니다.

**Q: 두 워크트리에서 같은 파일을 동시에 수정하면?**
A: 서로 다른 브랜치이므로 작업 디렉토리 충돌은 없습니다. 나중에 머지할 때 git이 충돌을 알려줍니다.

**Q: 워크트리에서 새 브랜치를 만들 수 있나요?**
A: 네. 각 워크트리에서 자유롭게 `git checkout -b feature/xxx`로 새 브랜치를 생성할 수 있습니다.

**Q: 메인 레포의 브랜치를 바꿔야 하나요?**
A: 현재 메인 레포는 `CLI_v258`에 있습니다. 워크트리 전략 적용 시 `STOM_Version_2`로 전환합니다. 이는 워크트리 생성 시점에 진행합니다.
