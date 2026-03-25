# STOM 업스트림 동기화 전략 — devstom GitHub 연동

- 작성일: 2026-03-24
- 분석 기준일: 2026-03-24 (devstom 133커밋, V2.65까지)
- 적용 대상: `STOM_Version_2` → `STOM_Version_2U` → `STOM_Version_2U_C` 브랜치 체인
- 관련 문서: `docs/WORKTREE_STRATEGY.md`

> **주의**: 이 문서의 분석 데이터(커밋 수, 버전 번호, 파일 목록)는 2026-03-24 기준입니다.
> devstom 레포는 활발히 개발 중이며, 이 문서 작성 이후에도 새 커밋과 버전이
> 계속 추가됩니다. 방법론은 동일하게 적용됩니다.

---

## 목차

1. [배경: 배포 방식 변경](#1-배경-배포-방식-변경)
2. [업스트림 분석 결과](#2-업스트림-분석-결과-2026-03-24-기준)
3. [V2.58 연결 검증 결과](#3-v258-연결-검증-결과)
4. [동기화 전략](#4-동기화-전략)
5. [버전 단위 동기화 절차](#5-버전-단위-동기화-절차)
6. [pyd→py 추론 전파](#6-pydpy-추론-전파-2u-2u_c-research)
7. [전파 순서도](#7-전파-순서도)
8. [정기 동기화 루틴](#8-정기-동기화-루틴)
9. [V2.58 파일 구조 차이 상세](#9-v258-파일-구조-차이-상세)
10. [FAQ](#10-faq)

---

## 1. 배경: 배포 방식 변경

### 1.1 기존 방식 (V2.58 이하)

```
개발자 → 특정 버전 zip 파일 릴리즈 (V2.50, V2.51, ..., V2.58)
       → 각 zip을 STOM_Version_2 브랜치에 1커밋으로 반영
       → python C:/System_Trading/stom_v2_update.py 스크립트로 자동 처리
       → 버전 단위 스냅샷 관리
```

### 1.2 새 방식 (V2.59 이후)

```
개발자 → GitHub 레포(devstom/STOM)에서 직접 개발
       → 특정 버전 zip 릴리즈 없이 연속 커밋 진행
       → _update.txt 에 버전 정보 기록 (V2.59, V2.60, ...)
       → 버전은 명명되지만 별도 태그/릴리즈 없이 커밋 스트림으로 진행
```

### 1.3 업스트림 레포 정보

| 항목 | 값 |
|------|-----|
| 레포 URL | `https://github.com/devstom/STOM.git` |
| 로컬 클론 | `C:\System_Trading\STOM\STOM_devstom` |
| 기본 브랜치 | `master` |
| 초기 커밋 | `ee6a63f` (V2.58 상당, 2026-03-15) |
| 분석 시점 커밋 수 | 133개 (2026-03-24 기준, 계속 증가 중) |
| 분석 시점 최신 버전 | V2.65 (2026-03-24) |

---

## 2. 업스트림 분석 결과 (2026-03-24 기준)

### 2.1 `_update.txt` 기반 버전 매핑

devstom 레포는 `_update.txt` 파일에 버전을 기록합니다.
**이 파일이 갱신되는 커밋이 자연스러운 버전 경계(마일스톤)** 입니다.

| 커밋 | 날짜 | 버전 | 구간 커밋 수 | pyd 변경 |
|------|------|------|-------------|---------|
| `ee6a63f` | 03-15 | **V2.58** (초기) | — | — |
| `6752d68` | 03-17 | **V2.59** | 20 | 2회 |
| `dc035b8` | 03-21 | **V2.60** | 35 | 0회 |
| `959b4dd` | 03-22 | **V2.61** | 13 | 1회 |
| `0c07344` | 03-22 | **V2.62** | 20 | 0회 |
| `706d158` | 03-23 | **V2.63** | 9 | 1회 |
| `0ad733e` | 03-24 | **V2.64** | 18 | 7회 |
| `041699d` | 03-24 | **V2.65** | 17 | 7회 |
| | | **합계** | **132** | **18회** |

> 이 표는 2026-03-24 기준이며, 이후 V2.66, V2.67... 등이 계속 추가될 수 있습니다.

### 2.2 버전별 주요 변경 내용

**V2.59** (03-17, 20커밋):
- 전략탭 애니메이션, 홈화면 항목 변경
- 최적화 변수명 변경, 공유메모리 중복 계산 제거
- 크롤링 오류 수정

**V2.60** (03-21, 35커밋, pyd 변경 없음):
- 디알로그 애니메이션 추가
- 분할 로딩 시 백테엔진 멈춤 수정
- 주문관리 익절청산 추가
- DB 업데이트 경로 오류 수정

**V2.61** (03-22, 13커밋):
- 백테엔진 프로세스 생성 속도 대폭 향상
- cython 재빌드
- 집계탭 차트 표시 오류 수정

**V2.62** (03-22, 20커밋, pyd 변경 없음):
- MDD 몬테카를로 100회 증가
- DB차트 매수/매도 인덱스 방법 변경
- 백테 중지 기능 강화
- numpy 연산 최적화

**V2.63** (03-23, 9커밋):
- 체결데이터 예외 처리
- pandas apply → 벡터연산
- 딕셔너리 중복 호출 제거
- np.int32 → np.int64 변경

**V2.64** (03-24, 18커밋):
- zmq 소켓 타임리밋 변경 (5초→1초)
- 색상테마 5종 추가
- 프로세스 통합 (차트/호가/쿼리/사운드)
- 콤보박스 마우스오버 드롭다운

**V2.65** (03-24, 17커밋):
- Zmq Process → QThread 변경 (메모리 대폭 감소) ★★★
- ui_process_kill.py → pyd 안으로 이동
- pyttsx3 스레딩락 추가
- 시리얼키 만료 일자 오류 수정

### 2.3 가장 빈번하게 변경되는 파일

```
18회  ui/ui_mainwindow.pyd          ← pyd (추론 필요)
15회  utility/chart.py              ← py (직접 반영)
11회  backtest/backengine_base.py   ← py (직접 반영)
10회  utility/webcrawling_homtab.py ← py (삭제→통합)
10회  ui/ui_backtest_engine.py      ← py (직접 반영)
 9회  backtest/rolling_walk_forward_test.py
 9회  backtest/optimiz.py
 9회  _update.txt                   ← 버전 마커
 8회  backtest/backtest.py
```

---

## 3. V2.58 연결 검증 결과

### 3.1 핵심 발견: 직접 git merge 불가능

우리 STOM_V의 V2.58과 devstom의 초기 커밋(V2.58)을 비교한 결과:

```
공통 파일: 268개
 ├── 내용 동일: ~135개 (50%)
 └── 내용 불일치: ~133개 (50%)  ← 직접 merge 불가 원인
```

**불일치 원인**: 우리 V2.58은 zip 파일에서 가져왔고, devstom의 V2.58은
개발자가 GitHub에 올린 시점의 스냅샷입니다. 같은 "V2.58"이지만
미세한 차이(공백, 인코딩, 중간 수정 등)가 133개 파일에 존재합니다.

### 3.2 불일치 파일 분포

| 디렉토리 | 불일치 수 | 설명 |
|----------|----------|------|
| `ui/` | ~50개 | UI 파일 대부분 불일치 |
| `backtest/` | ~20개 | 백테스트 엔진 전체 |
| `trade/` | ~30개 | 트레이딩 전략 전체 |
| `utility/` | ~15개 | 유틸리티 대부분 |
| 기타 | ~18개 | bat, txt, requirements 등 |

### 3.3 결론: "오버레이 방식" 채택

두 레포의 git 히스토리가 독립적이므로(공통 조상 없음),
`git merge --allow-unrelated-histories`는 133개 파일에서 충돌을 일으킵니다.

대신 **기존 zip 가져오기와 동일한 "오버레이 방식"**을 사용합니다:

```
devstom 버전 체크포인트의 파일들을
→ STOM_V의 V2 브랜치에 덮어쓰기 (우리 커스텀 파일 제외)
→ 1커밋으로 기록
```

이는 기존 `stom_v2_update.py`가 zip으로 했던 것과 동일한 방식이며,
소스가 zip에서 git으로 바뀐 것뿐입니다.

---

## 4. 동기화 전략

### 4.1 핵심 원칙

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. devstom을 git remote로 추가하여 버전 변경 추적 (참조용)         │
│  2. _update.txt 갱신 커밋 = 버전 경계 = 동기화 단위                │
│  3. 버전 단위로 오버레이 방식 동기화 (기존 zip 방식의 git 버전)     │
│  4. pyd 추론은 버전 단위로 수행 (pyd 변경이 있는 버전만)           │
│  5. V2 → 2U → 2U_C 순서로 한 단계씩 전파                          │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 왜 "오버레이 방식"인가?

| 방식 | 장점 | 단점 | 적합성 |
|------|------|------|--------|
| `git merge upstream` | 자동 병합 | V2.58 baseline 불일치로 133파일 충돌 | **불가** |
| `cherry-pick` 커밋별 | 세밀한 이력 | 132커밋 × 충돌 가능성 | **비현실적** |
| **오버레이 (버전별)** | 기존 방식과 동일, 안전 | 중간 커밋 이력 미반영 | **최적** |
| 스냅샷 1회 | 빠름 | 중간 버전 이력 누락 | 초기 catchup용 |

### 4.3 remote 구성 (참조용)

devstom을 remote로 추가하여 `git log`와 `git diff`로 변경 내역을 참조합니다.
직접 merge하지는 않습니다.

```bash
cd C:\System_Trading\STOM\STOM_V
git remote add upstream https://github.com/devstom/STOM.git
# 또는 로컬 클론 사용:
git remote add upstream C:/System_Trading/STOM/STOM_devstom
git fetch upstream
```

### 4.4 커밋 단위 추론을 하지 않는 이유

devstom의 132커밋 중 pyd가 변경된 커밋은 18개이며,
상당수가 동일 기능의 반복 빌드(cython 재빌드, 오류 수정 후 재빌드)입니다:

```
예시: V2.65 구간 pyd 7회 변경 중 실질 기능 변경

d597da0 Zmq Process → QThread 변경    ★ 기능 변경
3873b7b Zmq Process → QThread 변경    ★ 동일 기능 계속
59fb0aa Zmq Process → QThread 변경    ★ 동일 기능 계속
8f6790e Zmq Process → QThread 변경    ★ 동일 기능 완료
fd14c6d cython 재빌드                 ← 단순 재빌드
ce82d01 ui_process_kill.py → pyd 이동 ★ 파일 이동
4c465a2 시리얼키 만료 일자 수정       ← 설정 수정
```

커밋 단위로 추론하면 **동일 코드 영역을 4~5번 반복 추론**하게 됩니다.
버전 단위(V2.65)로 하면 **최종 상태만 1번 추론**하면 됩니다.

또한 중간 커밋은 불안정할 수 있습니다 (빌드 실패, 부분 구현, 즉시 수정 등).
버전 경계의 안정된 상태만 반영하는 것이 안전합니다.

---

## 5. 버전 단위 동기화 절차

### 5.1 사전 준비 (최초 1회)

```bash
# 1. devstom remote 추가
cd C:\System_Trading\STOM\STOM_V
git remote add upstream https://github.com/devstom/STOM.git
git fetch upstream

# 2. 보호 대상 파일/디렉토리 목록 확인 (우리 커스텀 추가분)
# 아래 파일/디렉토리는 오버레이 시 덮어쓰지 않음:
#   .gitignore, CLAUDE.md, AGENTS.md
#   cli/, tests/, docs/, scripts/, research/, temp/
#   requirements64-2.txt
```

### 5.2 단일 버전 동기화 (예: V2.59)

> **실행 환경**: 아래 명령어는 **Git Bash** 기준입니다.
> Windows CMD/PowerShell에서는 경로 구분자와 일부 명령이 다릅니다.

```bash
# 1. devstom에서 해당 버전 체크포인트 확인
cd /c/System_Trading/STOM/STOM_devstom
git log --oneline -- _update.txt
# → 6752d68 업데이트 파일 갱신 (V2.59)

# 2. 임시 디렉토리 생성 후 export
mkdir -p /tmp/stom_v259_export
git archive 6752d68 | tar -x -C /tmp/stom_v259_export/

# 3. STOM_V로 이동하여 오버레이 적용
cd /c/System_Trading/STOM/STOM_V
git switch STOM_Version_2

# 4. dry-run으로 삭제될 파일 먼저 확인 (안전 점검)
rsync -avn --delete \
  --exclude='.git' \
  --exclude='.gitignore' \
  --exclude='.omc/' \
  --exclude='CLAUDE.md' \
  --exclude='AGENTS.md' \
  --exclude='cli/' \
  --exclude='tests/' \
  --exclude='docs/' \
  --exclude='scripts/' \
  --exclude='research/' \
  --exclude='temp/' \
  --exclude='requirements64-2.txt' \
  /tmp/stom_v259_export/ \
  ./
# → "deleting ..." 항목을 검토하여 커스텀 파일이 포함되지 않았는지 확인
# → 문제가 있으면 --exclude 항목을 추가

# 5. 확인 완료 후 실제 오버레이 적용
rsync -av --delete \
  --exclude='.git' \
  --exclude='.gitignore' \
  --exclude='.omc/' \
  --exclude='CLAUDE.md' \
  --exclude='AGENTS.md' \
  --exclude='cli/' \
  --exclude='tests/' \
  --exclude='docs/' \
  --exclude='scripts/' \
  --exclude='research/' \
  --exclude='temp/' \
  --exclude='requirements64-2.txt' \
  /tmp/stom_v259_export/ \
  ./

# 6. 변경 확인 및 커밋 (명시적 파일 스테이징, git add -A 사용 금지)
git diff --stat                          # 변경 내역 확인
git add -u                               # 수정/삭제된 추적 파일만 스테이징
git add backtest/ trade/ ui/ utility/    # 신규 파일은 디렉토리 단위로 명시 추가
git add stom.py stom.bat _update.txt _license.txt requirements*.txt  # 루트 파일 명시
git diff --cached --stat                 # 최종 스테이징 내역 검토
git commit -m "STOM V2.59"              # _update.txt 내용은 본문에 수동 기재
```

### 5.3 일괄 catch-up (V2.59~V2.65 한번에)

현재 V2.58 → V2.65까지 7개 버전을 한번에 따라잡을 때:

**방법 A: 버전별 순차 커밋 (이력 보존, 권장)**
```bash
# V2.59, V2.60, ..., V2.65 각각에 대해 위 5.2 절차 반복
# 장점: 기존 zip 방식과 동일한 이력 구조 유지
# 결과: 7개 커밋 (V2.59, V2.60, ..., V2.65)
```

**방법 B: 최신 스냅샷 1회 (빠른 catch-up)**
```bash
# devstom 최신(V2.65)을 한번에 오버레이
# 장점: 빠름
# 단점: V2.59~V2.64 중간 이력 없음
# 결과: 1개 커밋 (V2.59~V2.65 통합)
```

**권장: 방법 A**. 기존 `STOM_Version_2` 브랜치가 버전 단위 커밋으로
관리되어 왔으므로, 동일한 패턴을 유지하는 것이 히스토리 일관성에 좋습니다.

### 5.4 자동화 스크립트 (향후)

기존 `stom_v2_update.py`를 확장하여 devstom git 기반 동기화를 자동화할 수 있습니다:

```python
# 개념 예시 (향후 구현)
def sync_version(devstom_path, target_commit, version_label):
    """devstom의 특정 커밋을 STOM_V에 오버레이."""
    # 1. git archive로 export
    # 2. 보호 파일 제외하고 rsync (dry-run 먼저)
    # 3. 명시적 파일 스테이징 후 commit
```

---

## 6. pyd→py 추론 전파 (2U, 2U_C, research)

### 6.1 추론이 필요한 시점

V2 브랜치에 새 버전을 반영한 후, **pyd 변경이 있는 버전에서만** 추론이 필요합니다.

```bash
# V2 동기화 커밋 전후의 pyd 변경 여부 확인
# (버전 커밋 해시를 명시하여 정확한 비교)
git diff <이전버전커밋>..<새버전커밋> --name-only | grep '\.pyd$'

# 예: V2.58 → V2.59 구간의 pyd 변경 확인
git diff STOM_V2.58..STOM_V2.59 --name-only | grep '\.pyd$'

# 출력이 없으면 → 추론 불필요, 그냥 merge
# 출력이 있으면 → 2U에서 py 추론 작업 필요
```

> **참고**: `HEAD~1` 방식은 merge 커밋이나 중간 커밋이 섞이면
> 의도한 버전 구간을 정확히 잡지 못할 수 있습니다.
> 가능하면 버전 커밋 해시 또는 태그를 명시하여 비교하세요.

### 6.2 버전별 추론 필요 여부 (2026-03-24 기준)

| 버전 | pyd 변경 | 추론 필요 | 주요 변경 내용 |
|------|---------|----------|---------------|
| V2.59 | 2회 | **예** | cython 재빌드, 애니메이션 추가 |
| V2.60 | 0회 | 아니오 | py 파일만 변경 |
| V2.61 | 1회 | **예** | 프로세스 생성 속도 향상 |
| V2.62 | 0회 | 아니오 | py 파일만 변경 |
| V2.63 | 1회 | **예** | 프로세스 통합 관련 |
| V2.64 | 7회 | **예** | 프로세스 통합 (차트/호가/쿼리/사운드) |
| V2.65 | 7회 | **예** | Zmq Process→QThread, ui_process_kill 이동 |

### 6.3 추론 작업 흐름

> **핵심 제약**: `STOM_Version_2U` 브랜치에는 `.pyd` 파일이 존재하면 안 됩니다.
> merge 후 반드시 `.pyd` 파일을 삭제하고 커밋해야 합니다.

```bash
# wt-2u 에서 실행 (Git Bash 기준)
cd /c/System_Trading/STOM/STOM_V.wt-2u

# 1. V2 변경분 머지 (py 파일은 자동 반영, pyd도 함께 들어옴)
git merge STOM_Version_2

# 2. ★ pyd 파일 즉시 제거 (2U 브랜치 원칙: pyd 비존재)
git rm -f $(git ls-files '*.pyd') 2>/dev/null
# 또는 명시적으로:
git rm -f ui/ui_mainwindow.pyd 2>/dev/null

# 3. pyd 변경 여부 확인 (V2 커밋 기준)
git diff STOM_Version_2U@{1}..STOM_Version_2 --name-only | grep '\.pyd$'
# → 출력이 있으면 py 추론 작업 필요

# 4. pyd 변경이 있으면 AI Agent로 추론
claude
# → "V2.65에서 ui_mainwindow.pyd가 변경되었습니다.
#    _update.txt와 주변 py 파일 변경을 참고하여
#    ui_mainwindow.py에 추론 반영해주세요."
```

### 6.4 추론 참고 자료

AI Agent가 pyd 추론 시 참고할 자료:

1. **`_update.txt`의 해당 버전 섹션** — 기능 변경 설명
2. **같은 버전 구간의 py 파일 diff** — pyd와 상호작용하는 코드 변경
3. **devstom의 개별 커밋 메시지** — 각 변경의 의도
4. **주변 파일의 import/호출 패턴** — 새 메서드/시그니처 역추론

---

## 7. 전파 순서도

### 7.1 pyd 변경이 없는 버전 (빠른 경로)

```
[STOM_V/]               [wt-2u/]              [wt-dev/]
STOM_Version_2          STOM_Version_2U        STOM_Version_2U_C

V2.60 오버레이 적용     git merge V2           git merge 2U
     │                      │                       │
     ▼                      ▼                       ▼
  py 변경만 반영        git rm *.pyd           머지 + 충돌 해결
  (pyd 변경 없음)       py 변경 자동 반영      + CLI 테스트
                        (추론 불필요)
```

### 7.2 pyd 변경이 있는 버전 (추론 경로)

```
[STOM_V/]               [wt-2u/]              [wt-dev/]
STOM_Version_2          STOM_Version_2U        STOM_Version_2U_C

V2.65 오버레이 적용     git merge V2           git merge 2U
     │                      │                       │
     ▼                      ▼                       ▼
  py + pyd 모두 반영    git rm *.pyd           머지 + 충돌 해결
                        py 자동 반영            + CLI 테스트
                        + pyd→py 추론 작업
                        (AI Agent 활용)
```

### 7.3 전체 흐름

```
devstom/STOM (upstream)
    │
    │  git fetch upstream (참조용)
    │  _update.txt에서 새 버전 확인
    │  해당 버전 커밋에서 git archive → 오버레이
    ▼
[STOM_V/] STOM_Version_2
    │     원본 그대로 (pyd 포함)
    │     커밋: "STOM V2.XX" + _update.txt 내용
    │
    │  git merge STOM_Version_2
    │  + git rm *.pyd (2U 원칙: pyd 비존재)
    │  + pyd 변경 시 py 추론
    ▼
[wt-2u/] STOM_Version_2U
    │     pyd 제거, py 소스만
    │
    │  git merge STOM_Version_2U
    │  + 충돌 해결 + CLI 테스트
    ▼
[wt-dev/] STOM_Version_2U_C
    │      커스텀 + CLI 코드
    │
    └── CLI_v258, feature/* 등에 전파
```

---

## 8. 정기 동기화 루틴

### 8.1 새 버전 확인 (필요 시)

```bash
cd C:\System_Trading\STOM\STOM_devstom
git pull origin master
head -5 _update.txt   # 최신 버전 확인
```

또는 upstream remote 사용:
```bash
cd C:\System_Trading\STOM\STOM_V
git fetch upstream
git show upstream/master:_update.txt | head -5
```

### 8.2 버전 동기화 판단

```
_update.txt에 새 버전이 추가됨?
    │
    ├── 아니오 → 대기 (아직 버전 업데이트 안 됨)
    │
    └── 예 → 동기화 시작
         │
         ├── 1. V2 브랜치에 해당 버전 오버레이
         ├── 2. pyd 변경 확인
         │       ├── 변경 없음 → 2U에 바로 merge
         │       └── 변경 있음 → 2U에 merge + pyd 추론
         └── 3. 2U_C에 merge + 테스트
```

### 8.3 권장 동기화 빈도

| 상황 | 빈도 | 방법 |
|------|------|------|
| 일상 | 주 1~2회 확인 | `git fetch upstream` + `_update.txt` 확인 |
| 새 버전 발견 | 즉시 또는 다음 작업 전 | 버전 오버레이 + 전파 |
| 급한 버그 수정 | 즉시 | 해당 커밋만 cherry-pick 가능 |

---

## 9. V2.58 파일 구조 차이 상세

### 9.1 devstom에서 삭제/통합된 파일 (STOM_V에만 존재)

| STOM_V V2.58 파일 | devstom 변경 | 비고 |
|-------------------|-------------|------|
| `ui/ui_process_kill.py` | pyd 안으로 이동 | V2.65, ce82d01 |
| `ui/ui_draw_chart.py` | `ui_draw_chart_base/db/real/items`로 분리 | V2.53 리팩토링 |
| `ui/ui_crosshair.py` | `ui_draw_crosshair.py`로 리네임 | V2.53 |
| `ui/ui_get_label_text.py` | `ui_draw_label_text.py`로 리네임 | V2.53 |
| `ui/ui_betting_cotrol.py` | 리네임 또는 통합 | |
| `ui/ui_draw_realchart.py` | 분리/통합 | |
| `utility/setting.py` | `setting_base.py` + `setting_user.py` 분리 | V2.52 |
| `utility/chart.py` | 대폭 리팩토링 (15회 변경) | |
| `utility/chart_items.py` | 통합 | |
| `utility/hoga.py` | 리팩토링 | |
| `utility/lazy_imports.py` | V2.62에서 삭제 | pandas 지연로딩 제거 |
| `utility/sound.py` | 리팩토링 | |
| `utility/webcrawling_homtab.py` | `webcrawling.py`에 통합 | 최근 삭제 |

### 9.2 devstom에서 신규 추가된 파일

- `backtest/backengine_*2.py` 시리즈 (엔진 버전 2 파일들)
- `ui/ui_draw_chart_base.py`, `ui_draw_chart_db.py` 등 (차트 분리)
- `ui/ui_draw_crosshair.py`, `ui_draw_label_text.py` (리네임)
- `ui/set_home_tap.py` (홈탭 신규)
- `ui/ui_splash_screen.py` (스플래시 화면)
- `utility/setting_base.py`, `utility/setting_user.py` (설정 분리)

### 9.3 초기 동기화 시 주의사항

V2.58 → V2.59+ 오버레이 시, 위 삭제/리네임 파일들이 자동으로 처리됩니다.
다만 **우리 커스텀 코드에서 이 파일들을 import하고 있다면** 수정이 필요합니다:

```
검사 필요:
  cli/ 코드에서 utility/setting.py 를 import하는 곳
  → utility/setting_base.py + setting_user.py 로 변경 필요 여부
  (이미 V2.52 동기화 시 처리되었을 수 있음)
```

---

## 10. FAQ

**Q: devstom을 remote로 추가하면 우리 레포에 영향이 있나요?**
A: 없습니다. `git remote add`는 원격 참조만 추가합니다. `git fetch`로 커밋을 가져와도 우리 브랜치에 자동 반영되지 않습니다. 오버레이 방식으로 수동 반영합니다.

**Q: upstream에 push할 위험은 없나요?**
A: `git push`의 기본 타겟은 `origin`입니다. upstream에 push하려면 `git push upstream`을 명시해야 하고, 권한이 없으면 거부됩니다.

**Q: devstom 레포가 private이면 어떻게 하나요?**
A: 로컬 클론(`STOM_devstom`)이 이미 있으므로, remote URL을 로컬 경로로 설정합니다:
```bash
git remote add upstream C:/System_Trading/STOM/STOM_devstom
```

**Q: 마일스톤(버전 경계)은 어떻게 찾나요?**
A: `_update.txt`가 갱신된 커밋이 버전 경계입니다:
```bash
cd C:\System_Trading\STOM\STOM_devstom
git log --oneline -- _update.txt
```

**Q: 초기 동기화(V2.58→V2.65) 시 충돌이 많을까요?**
A: 오버레이 방식이므로 git 충돌은 없습니다. 파일을 통째로 복사하는 방식입니다. 다만 우리 커스텀 코드(cli/, tests/ 등)에서 변경된 파일을 import하는 경우 수동 조정이 필요합니다.

**Q: 기존 `stom_v2_update.py` 스크립트는 어떻게 되나요?**
A: zip 기반이므로 V2.58 이하에서만 사용합니다. V2.59부터는 git 기반 오버레이 방식을 사용하며, 향후 새 스크립트로 자동화할 수 있습니다.

**Q: 이 문서의 분석 데이터가 오래되면 어떻게 하나요?**
A: 방법론은 동일합니다. 새 버전이 추가되면 2.1절의 버전 매핑 표만 업데이트하면 됩니다. `_update.txt` 기반 버전 경계 식별 → 오버레이 → 전파 순서는 변하지 않습니다.
