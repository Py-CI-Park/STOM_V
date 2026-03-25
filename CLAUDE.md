# STOM Project Guidelines (STOM_Version_2U_C)

> **워크트리 위치**: `STOM_V.wt-dev/` (주력 개발)
> **관련 문서**: [`docs/WORKTREE_STRATEGY.md`](docs/WORKTREE_STRATEGY.md), [`docs/STOM_CLI_DEVELOPMENT_OVERVIEW.md`](docs/STOM_CLI_DEVELOPMENT_OVERVIEW.md)

## 브랜치 목적

`STOM_Version_2U_C`는 **커스텀 개발의 홈 브랜치**입니다.
CLI 자동화, UI 보강 등 모든 feature 브랜치의 분기점 역할을 합니다.

```
STOM_Version_2U_C (홈, 여기)
  ├── STOM_Version_2U_C_CLI_v258  ← CLI 자동화 개발
  │    └── feature/cli-*          ← 새 CLI 기능
  └── feature/ui-*                ← UI 보강
```

---

## 작업 방법

### CLI 개발 시

```bash
cd C:\System_Trading\STOM\STOM_V.wt-dev
git switch STOM_Version_2U_C_CLI_v258     # CLI 브랜치로 전환
git checkout -b feature/cli-new-feature    # 새 기능 브랜치 생성
# ... 작업 ...
# 완료 후 CLI_v258에 머지, 홈으로 복귀
git switch STOM_Version_2U_C
```

### UI 보강 시

```bash
git checkout -b feature/ui-fix-something   # 2U_C에서 분기
# ... 작업 ...
git switch STOM_Version_2U_C               # 홈으로 복귀
```

### 업스트림 동기화 수신 시

```bash
# 2U에서 업스트림 변경이 전파되면:
git merge STOM_Version_2U
# 충돌 해결 후 CLI 테스트 확인
pytest tests/unit/ -q
```

---

## 이 브랜치에서 하는 일

- CLI 자동화 기능 개발 (discovery, formula, strategy)
- UI/py 소스 커스텀 교정
- 2U에서 머지받은 업스트림 변경 통합
- feature 브랜치 생성/작업/머지

## 이 브랜치에서 하지 않는 일

- 업스트림 원본 수정 (→ STOM_V/)
- pyd→py 추론 (→ wt-2u/)
- 실험적 프로토타입 (→ wt-lab/)

---

## CLI 개발 현황

> 상세 → [`docs/STOM_CLI_DEVELOPMENT_OVERVIEW.md`](docs/STOM_CLI_DEVELOPMENT_OVERVIEW.md)

### CLI 서브커맨드 (19개)

```
stom_backtest.py
├── formula (list, add, test, delete, export, import)
├── strategy (list, validate, analyze)
└── discovery (analyze, ml-analyze, generate, create-strategy,
               promote, auto, batch, history, compare, evolve)
```

### 주요 수치 (CLI_v258 기준)

| 항목 | 수치 |
|------|------|
| CLI 소스 | 7,073줄 (26개 모듈) |
| 단위 테스트 | 712 passed |
| 통합 테스트 | 28 passed |
| Auto-Discovery | Phase 1~9 완료 |

---

## 커밋 규칙

| 항목 | 규칙 |
|------|------|
| 형식 | `<type>: <설명>` (feat, fix, refactor, docs, test, chore) |
| 스테이징 | 명시적 파일 지정 (`git add -A` 사용 금지) |
| 테스트 | 커밋 전 `pytest tests/unit/ -q` 통과 확인 |

---

## 워크트리 전체 구성

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 업스트림 원본 추적 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 |
| **`STOM_V.wt-dev/`** (여기) | `STOM_Version_2U_C` | 커스텀 개발 (CLI 등) |
| `STOM_V.wt-lab/` | `research/*` | 실험 |

---

## 프로젝트 구조

| 디렉터리 | 용도 |
|----------|------|
| `cli/` | CLI 자동 백테스트 시스템 (19개 서브커맨드) |
| `tests/unit/` | 단위 테스트 (712개) |
| `tests/integration/` | 통합 테스트 (28개) |
| `ui/` | UI 모듈 (PyQt5, py 소스) |
| `utility/` | 유틸리티 클래스 |
| `backtest/` | 백테스팅 엔진 |
| `trade/` | 트레이딩 (주식/코인/해외선물) |
| `docs/` | 문서 |
| `research/` | 연구/분석 모듈 |
