# STOM Project Guidelines (STOM_Version_2)

> **상세 업데이트 가이드**: [`docs/stom_v2_update_guide.md`](docs/stom_v2_update_guide.md)

## 브랜치 목적

`STOM_Version_2` 브랜치는 공식 STOM 배포 버전의 순차 이력을 관리합니다.

---

## 새 버전 업데이트 (빠른 참조)

### 1. 새 zip 파일 저장
```
C:\Users\parkc\Downloads\STOM_temp\STOM_V{버전}.zip
```

### 2. 자동 업데이트 실행
```bash
python C:/System_Trading/stom_v2_update.py
git push origin STOM_Version_2
```

### Claude Code에게 지시할 때 (복사해서 사용)
```
STOM_Version_2 브랜치 업데이트를 진행해주세요.
docs/stom_v2_update_guide.md 의 프로세스에 따라:
1. python C:/System_Trading/stom_v2_update.py --dry-run
2. python C:/System_Trading/stom_v2_update.py
3. git push origin STOM_Version_2
```

> 스크립트 옵션, 수동 방법, 문제 해결 → `docs/stom_v2_update_guide.md` 참조

---

## 커밋 규칙

| 항목 | 규칙 |
|------|------|
| 제목 | `STOM V{major}.{minor}` |
| 본문 | `_update.txt`의 해당 버전 섹션 전체 |
| 단위 | 배포 버전 1개 = 커밋 1개 |
| 스테이징 | zip 포함 파일만 (`CLAUDE.md`, `AGENTS.md`, `docs/`, `scripts/` 제외) |

---

## 버전 명명 규칙

```
V{major}.{minor}[.U{patch}[.{hotfix}]]
```
- `V2.50` — 공식 배포
- `V2.50.U1` — 마이그레이션/리팩토링
- `V2.50.U1.2` — 버그 수정

---

## 프로젝트 구조

| 디렉터리 | 용도 |
|----------|------|
| `ui/` | UI 모듈 (PyQt5) |
| `utility/` | 유틸리티 클래스 |
| `stock/` | 주식 트레이딩 |
| `coin/` | 암호화폐 트레이딩 |
| `backtester/` | 백테스팅 엔진 |
| `future/` | 해외선물 트레이딩 |
| `scripts/` | 유틸리티 스크립트 |
| `docs/` | 문서 (`stom_v2_update_guide.md` 포함) |
| `_update.txt` | 전체 버전 업데이트 이력 (최신 버전이 상단) |
