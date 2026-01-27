# CLAUDE.md - STOM_Version_1U 프로젝트 AI 어시스턴트 지침

> 이 파일은 Claude Code 및 AI 어시스턴트가 이 프로젝트에서 작업할 때 따라야 하는 지침입니다.

---

## 프로젝트 개요

**STOM (System Trading Optimization Machine)** - 틱데이터 기반 초단타 시스템 트레이딩 도구

현재 브랜치 `STOM_Version_1U`는 V1 코드베이스에 V2의 33개 커밋 변경사항을 **코드 이해 기반으로 재구현**하는 프로젝트입니다.

---

## 필수 참조 문서

**반드시 아래 문서들을 이 순서대로 참조하십시오:**

### 1. 개발 계획서 (최우선)
```
docs/dev_plan/STOM_Version_1U_Development_Plan.md
```
- 이 프로젝트의 **모든 개발 작업의 근거**이자 **실행 명세서**
- 34단계 순차 개발 계획, V2 커밋 분석, ui_mainwindow.py 추론 방법론 포함
- **어떤 작업이든 이 문서를 먼저 확인한 후 진행**

### 2. 에이전트 가이드 (상세 참조)
```
AGENTS.md
```
- 프로젝트 아키텍처, 코드 패턴, 디렉토리 구조, 파일 역할 상세
- 개발 작업 프로토콜, 검증 체크리스트
- Git 참조 명령어, V2 커밋 해시 빠른 참조

---

## 핵심 규칙

### 절대 금지 사항
1. **체리픽(cherry-pick) 사용 금지** - V2 커밋을 git cherry-pick으로 가져오지 말 것
2. **ui/ui_mainwindow.pyd 파일 생성/추가 금지** - 바이너리 파일은 이 브랜치에 존재해서는 안 됨
3. **순서 무시 금지** - V1U.00 → V1U.01 → ... 순서를 반드시 지킬 것
4. **V2 코드 맹목 복사 금지** - V1U의 현재 상태를 이해하고 해당 맥락에 맞게 적용

### 필수 준수 사항
1. **ui/ui_mainwindow.py는 소스코드(.py) 형태를 유지**할 것
2. 각 단계 완료 시 **커밋 메시지 형식**: `STOM V1U.XX - <한줄 요약>`
3. V2 커밋의 diff를 **분석하고 이해한 뒤** 적용할 것
4. pyd 파일은 읽을 수 없으므로 **주변 파일 변경, 커밋 메시지, pyd 크기 변동으로 추론**

---

## 작업 시작 방법

### 새로운 단계를 시작할 때

1. `docs/dev_plan/STOM_Version_1U_Development_Plan.md`에서 해당 Step 확인
2. `AGENTS.md`에서 관련 아키텍처/패턴 참조
3. V2 커밋의 diff 분석:
   ```bash
   git show --stat <V2_commit_hash>
   git diff <이전V2커밋>..<현재V2커밋> -- <파일>
   ```
4. 코드 변경 적용 (주변 파일 → ui_mainwindow.py 순서)
5. 검증 후 커밋

### 현재 진행 상태 확인

```bash
git log --oneline STOM_Version_1U
```

---

## 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.11 |
| GUI | PyQt5 |
| IPC | ZMQ, multiprocessing.Queue |
| DB | SQLite3 |
| 차트 | pyqtgraph |
| 거래소 API | 키움증권 OCX, 업비트 REST/WebSocket, 바이낸스 REST/WebSocket |
| 백테스트 | 자체 엔진 (멀티프로세스) |
| 최적화 | 그리드, 유전 알고리즘(GA), 옵튜나 |

---

## 코드 컨벤션

- 한글 변수명 사용 (의도된 설계, 유지할 것)
- `수익률` (O) vs `수익율` (X) - V2.01에서 수정됨
- MainWindow 메서드는 외부 모듈에 위임하는 패턴: `def XXX(self): xxx(self)`
- Queue 변수명: `windowQ`, `stockQ`, `coinQ`, `futureQ`, `testQ` 등
- 상수는 `utility/static.py`에 정의

---

## 참고

- 이 프로젝트는 파이퀀트 강좌 수강생 전용 소스코드입니다
- 상업적 이용 및 미수강자 공유가 금지되어 있습니다
- 상세한 아키텍처와 파일 설명은 `AGENTS.md`를 참조하십시오
