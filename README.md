# STOM - System Trading Optimization Machine

## STOM_Version_1U Branch

틱데이터 기반 초단타 시스템 트레이딩 도구 STOM의 **Version 1U** 개발 브랜치입니다.

---

## 프로젝트 목적

STOM V1 코드베이스를 기반으로, V2에서 순차적으로 개발된 36개 커밋(V2.00 ~ V2.36)의 변경사항을 **코드 이해 기반으로 재구현**합니다.

### 왜 V1U인가?

| 항목 | STOM_Version_2 | STOM_Version_1U |
|------|---------------|-----------------|
| ui_mainwindow | `.pyd` (암호화 바이너리) | `.py` (소스코드 유지) |
| 개발 방식 | 원작자 직접 개발 | V2 분석 후 이해 기반 재구현 |
| 핵심 가치 | 보안 (인증 시스템) | 가독성 (소스코드 유지) |

V2에서 `ui/ui_mainwindow.py`가 `.pyd`로 암호화되었지만, V1U에서는 이 핵심 파일을 **소스코드로 유지**하면서 동일한 기능을 구현합니다.

---

## 브랜치 구조

```
Initial commit (87aee04)
  │
  └── STOM V1 (80ab4ec)
        │
        ├── STOM_Version_1   (V1 최종)
        ├── STOM_Version_1U  (V1 + V2 기능, 소스코드 유지) ← 현재 브랜치
        └── STOM_Version_2   (V2.00 ~ V2.33, pyd 포함)
```

---

## 주요 기능

- **주식 자동매매**: 키움증권 API 기반 (틱/분봉 전략)
- **코인 자동매매**: 업비트 + 바이낸스 WebSocket 기반
- **해외선물 자동매매**: 키움증권 CME 해외선물 (V2.00~)
- **백테스트 엔진**: 멀티프로세스 기반 고속 백테스트
- **최적화**: 그리드 탐색, 유전 알고리즘(GA), 옵튜나
- **전진분석**: Rolling Walk Forward Test
- **실시간 차트**: pyqtgraph 기반 틱/분봉 차트
- **텔레그램 봇**: 잔고/주문 알림 및 원격 제어

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.11 (32bit + 64bit) |
| GUI | PyQt5 |
| 프로세스간 통신 | ZMQ, multiprocessing.Queue |
| 데이터베이스 | SQLite3 |
| 차트 | pyqtgraph |
| 주식 API | 키움증권 Open API+ (OCX, 32bit) |
| 코인 API | 업비트 REST/WebSocket, 바이낸스 REST/WebSocket |

---

## 실행 방법

```bash
# 수동 실행
python stom.py

# 주식 자동 실행
stom_stock.bat

# 코인 자동 실행
stom_coin.bat

# 해외선물 자동 실행 (V1U.00 이후)
stom_future.bat
```

### 사전 요구사항

```bash
# 64bit 패키지 설치
pip_install_64.bat

# 32bit 패키지 설치 (키움 매니저용)
pip_install_32.bat
```

---

## 디렉토리 구조

```
STOM_V/
├── stom.py              # 진입점
├── CLAUDE.md            # AI 어시스턴트 지침
├── AGENTS.md            # AI 에이전트 상세 가이드
├── README.md            # 이 파일
│
├── docs/
│   └── dev_plan/
│       └── STOM_Version_1U_Development_Plan.md  # ★ 개발 계획서
│
├── ui/                  # UI 레이어 (PyQt5)
├── stock/               # 키움증권 주식 모듈
├── coin/                # 코인 모듈 (바이낸스 + 업비트)
├── future/              # 해외선물 모듈 (V1U.00에서 추가)
├── backtester/          # 백테스트 엔진
├── utility/             # 유틸리티 모듈
├── lecture/             # 강의 자료
└── icon/                # 아이콘 리소스
```

---

## 개발 계획

이 브랜치의 개발은 **37단계**로 진행됩니다 (V1U.00 ~ V1U.36).

각 단계는 V2의 해당 커밋과 대응하며, 상세 내용은 아래 문서를 참조하십시오:

```
docs/dev_plan/STOM_Version_1U_Development_Plan.md
```

### 주요 이정표

| 단계 | 내용 | 난이도 |
|------|------|--------|
| V1U.00 | 키움증권 해외선물 추가, 인증 시스템, ZMQ 라이브 | 최고 |
| V1U.02 | DataFrame → Dictionary 전환 | 상 |
| V1U.11 | UI 파일 대규모 리네이밍 (26개 파일) | 최고 |
| V1U.19 | 리시버→에이전트 리네이밍, PyQT 이벤트루프 전환 | 최고 |
| V1U.23 | 리시버공유 코드 대폭 삭제 | 상 |
| V1U.26 | 리시버 공유 모드 완전 삭제 | 상 |
| V1U.34 | 보유시간 조건, 차트창, 보조지표 오류 수정 | 중 |
| V1U.36 | MERGE값 합산 방법 변경 (곱셈→덧셈) | 중 |

---

## 문서 체계

| 문서 | 역할 | 대상 |
|------|------|------|
| `README.md` | 프로젝트 소개 및 실행 방법 | 사용자/개발자 |
| `CLAUDE.md` | AI 어시스턴트 작업 지침 | AI 에이전트 |
| `AGENTS.md` | 아키텍처/코드 상세 가이드 | AI 에이전트 |
| `docs/dev_plan/*.md` | 개발 계획서 (최중요) | AI 에이전트/개발자 |

> `docs/dev_plan/STOM_Version_1U_Development_Plan.md`는 이 프로젝트에서 **가장 중요한 문서**입니다. 모든 개발 작업은 이 문서에 정의된 절차와 규칙을 따릅니다.

---

## 라이선스

파이퀀트 "틱데이터를 이용한 주식 및 암호화폐 초단타 시스템 개발" 강좌 수강생 전용.
상세 사항은 `_license.txt`를 참조하십시오.
