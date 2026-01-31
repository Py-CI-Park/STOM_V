# STOM 문서 관리 허브

> 이 문서는 `docs/` 폴더 내 모든 마크다운 문서를 **관리하고 총괄**하는 중앙 허브입니다.
>
> **관리 주체**: 이 문서는 상위 문서들(`README.md`, `AGENTS.md`, `CLAUDE.md`)에 의해 관리됩니다.

---

## 문서 계층 구조

```
STOM_V/                           ← 프로젝트 루트
│
├── README.md                     ← 프로젝트 총괄 (1)
├── AGENTS.md                     ← 프로젝트 총괄 (2)
├── CLAUDE.md                     ← 프로젝트 총괄 (3)
│
└── docs/                         ← 문서 디렉토리
    │
    ├── README.md                 ← ★ 이 파일 (docs 총괄)
    │                               - 상위 md 파일들이 관리
    │                               - docs/ 내 문서 목록 관리
    │
    └── dev_plan/                 ← 개발 계획 문서
        └── STOM_Version_1U_Development_Plan.md
```

### 관리 체계

| 계층 | 문서 | 역할 | 관리 대상 |
|------|------|------|----------|
| **1층 (최상위)** | `README.md` | 프로젝트 총괄 소개 | 전체 프로젝트 |
| **1층 (최상위)** | `AGENTS.md` | AI 에이전트 아키텍처 가이드 | 전체 프로젝트 |
| **1층 (최상위)** | `CLAUDE.md` | AI 작업 지침 및 규칙 | 전체 프로젝트 |
| **2층 (docs)** | `docs/README.md` | docs 폴더 문서 총괄 | docs/ 내 문서들 |
| **3층 (하위)** | `docs/dev_plan/*.md` | 개발 계획 문서 | 해당 주제 |

---

## docs/ 폴더 문서 목록

### 현재 등록된 문서

| 경로 | 문서명 | 설명 | 상태 |
|------|--------|------|------|
| `dev_plan/` | `STOM_Version_1U_Development_Plan.md` | V1U 37단계 개발 계획서 | 활성 |

### 문서 추가 규칙

새 문서를 `docs/` 에 추가할 때:

```
1. docs/ 내 적절한 하위 폴더에 문서 배치
2. 이 파일(docs/README.md)의 "문서 목록" 테이블에 등록
3. 필요시 상위 문서(README.md, AGENTS.md, CLAUDE.md)에 참조 추가
```

### 하위 폴더 구조

| 폴더 | 용도 | 상태 |
|------|------|------|
| `dev_plan/` | 개발 계획 및 명세 문서 | 활성 |
| `architecture/` | 아키텍처 다이어그램 | 예정 |
| `api/` | API 문서 | 예정 |
| `guides/` | 사용자 가이드 | 예정 |

---

## 개발 계획서 상세

### STOM_Version_1U_Development_Plan.md

**이 프로젝트의 핵심 실행 명세서입니다.**

| 섹션 | 내용 |
|------|------|
| V2 커밋 이력 분석 | 37개 커밋(V2.00~V2.36)의 상세 분석 |
| ui_mainwindow.py 추론 | pyd 바이너리 기반 변경사항 추론 방법론 |
| 37단계 개발 계획 | V1U.00 ~ V1U.36 상세 체크리스트 |
| 파일 변경 매핑 | 신규/삭제/리네이밍 파일 전체 목록 |

---

## 문서 명명 규칙

```
<프로젝트명>_<버전/유형>_<설명>.md

예시:
- STOM_Version_1U_Development_Plan.md
- STOM_Architecture_Overview.md
- STOM_API_Reference.md
```

---

## 참고

- 이 문서(`docs/README.md`)는 상위 문서들에 의해 관리됩니다
- 모든 문서 변경 시 이 허브도 함께 업데이트해야 합니다
- AI 에이전트는 작업 전 반드시 `dev_plan/` 문서를 먼저 확인해야 합니다
