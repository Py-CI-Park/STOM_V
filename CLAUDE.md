# STOM Project Guidelines (research/*)

> **워크트리 위치**: `STOM_V.wt-lab/`
> **관련 문서**: [`docs/WORKTREE_STRATEGY.md`](docs/WORKTREE_STRATEGY.md)

## 브랜치 목적

`research/*` 브랜치는 **실험적 기능 프로토타입** 전용입니다.
실패해도 다른 브랜치에 영향을 주지 않으며, 성공 시 `wt-dev`에서 머지합니다.

---

## 공식 업데이트 추적 기준

`research/*` 브랜치도 부모 브랜치의 공식 업데이트를 계속 따라가야 합니다.
다만 그대로 복사하는 것이 아니라, 리서치 브랜치 맥락에 맞게 조정하여 반영합니다.

### 기준 브랜치

- **canonical base**: `wt-dev / STOM_Version_2U_C_CLI_v267`

### 적용 원칙

| 원칙 | 의미 |
|------|------|
| A | 공식 업데이트는 부모 브랜치 기준으로 계속 흡수 |
| B | 리서치 브랜치 상태와 실험 구조를 고려해 추론/조정 적용 |
| C | `AGENTS.md`, `CLAUDE.md`, 연구 계획 문서, 최소 호환 보정은 유지 |

### 반드시 먼저 읽을 문서

- `docs/research/2026-03-28_research_init_v259_v267_sync_matrix_and_plan.md`
- `docs/research/2026-03-28_research_init_official_update_playbook.md`
- `docs/research/2026-03-28_research_init_v267_preparation_completion_report.md`

### 이상적인 반영 순서

1. 용어/키 체계 (`V2.59` 계열)
2. UI / 설정 골격 (`V2.60~V2.63`)
3. 홈탭 crawler 구조 (`V2.64~V2.65`)
4. 런타임 구조 (`V2.64~V2.65`)
5. 백테스트 의미 체계
6. tick + 시장미시구조 분석 (`V2.67`)
7. safe subset / tail sync
8. broad `py_compile` + startup smoke + push

### 금지

- 공식 업데이트를 장기간 미반영한 채 연구 코드만 누적
- stale import / stale process 구조를 방치
- branch-specific 문서/호환 보정까지 모두 없애고 byte-identical parity를 강제

---

## 작업 방법

### 새 실험 시작

```bash
cd C:\System_Trading\STOM\STOM_V.wt-lab
git checkout -b research/new-experiment
# ... 실험 작업 ...
```

### 실험 성공 → wt-dev에 머지

```bash
# wt-dev에서 머지
cd C:\System_Trading\STOM\STOM_V.wt-dev
git merge research/new-experiment
```

### 실험 실패 → 브랜치 유지 (히스토리 보존)

```bash
# 새 실험 브랜치를 생성하고 전환
cd C:\System_Trading\STOM\STOM_V.wt-lab
git checkout -b research/another-experiment
# 이전 실패 브랜치는 히스토리 참조용으로 유지
```

---

## 이 브랜치에서 하는 일

- 새 분석 방법 실험
- ML 모델 프로토타입
- 새 데이터 소스 연동 테스트
- PoC (Proof of Concept) 개발
- 성능 벤치마크, 비교 실험

## 이 브랜치에서 하지 않는 일

- 프로덕션 기능 개발 (→ wt-dev/)
- 업스트림 동기화 (→ STOM_V/)
- pyd→py 추론 (→ wt-2u/)

---

## 커밋 규칙

| 항목 | 규칙 |
|------|------|
| 브랜치명 | `research/{실험 주제}` |
| 커밋 형식 | 자유 (실험이므로 유연하게) |
| 스테이징 | 명시적 파일 지정 (`git add -A` 사용 금지) |

---

## 워크트리 전체 구성

| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 업스트림 원본 추적 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | pyd→py 동기화 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | 커스텀 개발 (CLI 등) |
| **`STOM_V.wt-lab/`** (여기) | `research/*` | 실험 |
