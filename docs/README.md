# STOM 문서 폴더

**프로젝트**: STOM (System Trading Operation Manager)
**버전**: V2.36.U1+
**최종 업데이트**: 2026-01-31

---

## 폴더 구조

```
docs/
├── README.md                    # 본 파일 - 문서 폴더 설명
└── update_log/                  # 업데이트 로그 폴더
    └── 2026-01-31_ui_mainwindow_migration.md
```

---

## 문서 목록

### update_log/ - 업데이트 로그

주요 변경사항 및 마이그레이션 기록을 보관합니다.

| 날짜 | 문서 | 설명 |
|------|------|------|
| 2026-01-31 | [ui_mainwindow_migration.md](update_log/2026-01-31_ui_mainwindow_migration.md) | ui_mainwindow.pyd → ui_mainwindow.py 마이그레이션 |

---

## 최근 변경사항

### V2.36.U1 (2026-01-31)

#### ui_mainwindow.pyd → ui_mainwindow.py 마이그레이션

**목적**: 컴파일된 pyd 파일을 Python 소스로 대체하여 개발 편의성 향상

**주요 작업**:
- V1.10 원본 소스를 기반으로 V2.36 모듈 구조에 맞게 업데이트
- 13개 모듈명 변경 반영
- 13개 신규 editer 모듈 import 추가
- STOM Live 인증 시스템 비활성화
- SetLogFile 호출 제거 (미정의 함수)
- .gitignore에 pyd 파일 제외 규칙 추가

**변경 파일**:
- `ui/ui_mainwindow.py` - 신규 생성
- `ui/ui_mainwindow.pyd` - 삭제됨 (백업: .pyd.backup)
- `.gitignore` - 업데이트됨

자세한 내용은 [마이그레이션 문서](update_log/2026-01-31_ui_mainwindow_migration.md)를 참조하세요.

---

## 문서 작성 규칙

### 파일명 규칙
```
YYYY-MM-DD_작업명.md
```

예시:
- `2026-01-31_ui_mainwindow_migration.md`
- `2026-02-15_database_schema_update.md`

### 필수 포함 내용
1. **개요**: 작업 목적 및 배경
2. **계획 과정**: 분석 및 계획 수립 내용
3. **실행 과정**: 단계별 실행 내역
4. **검증 결과**: 테스트 및 검증 결과
5. **변경 파일 목록**: 생성/수정/삭제된 파일
6. **결론**: 작업 완료 요약

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `_update.txt` | 버전별 업데이트 기록 (간략) |
| `CHANGELOG.md` | 변경 이력 (있는 경우) |
| `README.md` | 프로젝트 루트 설명 |

---

## 연락처

문서 관련 문의사항은 프로젝트 관리자에게 문의하세요.

### 2026-04-02 - 동기화 후 필수 검증

업스트림 반영 후에는 아래 문서와 스크립트를 기준으로 반드시 검증합니다.

- [runtime_regression_rca_and_worktree_audit.md](update_log/2026-04-01_runtime_regression_rca_and_worktree_audit.md)
- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
