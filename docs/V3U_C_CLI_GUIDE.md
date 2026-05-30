# V3U / 3U_C 통합 CLI 운영 매뉴얼 (E2)

- 최초 작성: 2026-05-30
- 산출: 3U_C 사이클 4 (E2)
- 스크립트: `scripts/v3uc_cli.py`
- 회귀 테스트: `tests/v3uc/test_cli.py` (16 케이스)
- 상위 진실 원천: `V3U_C_NEXT_STEPS.md` E2 항목

## 1. 본 CLI의 목적

V3U lane(`wt-3u`) 운영과 3U_C custom 도구 호출을 **단일 진입점**에 묶는다. 자주
쓰는 명령어를 외울 필요 없이 7개 subcommand로 양 lane 모든 운영을 처리한다.

본 CLI는 **디스패처 레이어**다 — 실 도구(`v3uc_strategy_migration.py`,
`v3uc_db_compatibility_check.py`, `v3uc_ingest_pipeline.py`, `verify_v3u_pyd_gui_contract.py`)를
subprocess로 호출하고 exit code만 전파한다. 진실은 기존 도구가 보유.

## 2. 설치·호출 위치

- 스크립트 위치: `C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_cli.py`
- 호출 위치: **V3U 워크트리(`wt-3u`)에서 호출** (기본 동작이 호출 cwd를 V3U 워크트리로 가정)
- 명시 override: `--workspace <path>` 옵션으로 워크트리 경로 강제 지정 가능

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-3u
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py <subcommand>
```

## 3. subcommand 카탈로그

| subcommand | 동작 | 호출 대상 |
|---|---|---|
| `status` | 양 lane HEAD + 조건식 보존 상태 | `git log` + `v3uc_strategy_migration scan` |
| `verify` | V3U 통합 verifier 8 stage | `scripts/verify_v3u_pyd_gui_contract.py` |
| `db scan` | strategy + DB 호환성 동시 scan | `v3uc_strategy_migration scan` + `v3uc_db_compatibility_check scan` |
| `db migrate <what>` | 조건식/PK 마이그레이션 (실수 차단) | 위 2개 도구의 migrate/--add-pk |
| `test` | 양 lane pytest 일괄 | `python -m pytest tests/v3u` + `tests/v3uc` |
| `ingest --version X` | V3.X 흡수 파이프라인 | `v3uc_ingest_pipeline.py` |
| `gui [--offscreen]` | `python stom.py` 실행 | `stom.py` (옵션으로 QT_QPA_PLATFORM=offscreen) |

## 4. 사용 시나리오

### 4.1 매 세션 시작 — 상태 확인
```powershell
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py status
```
출력: 양 lane HEAD 3 commit + strategy.db 조건식 scan 결과.

### 4.2 V3U 안전망 정기 점검
```powershell
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py verify
```
8 stage 통합 verifier 실행. CRITICAL drift 0 + pytest PASS 확인.

### 4.3 DB·조건식 보존 검증
```powershell
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py db scan
```
strategy.db 조건식 95 rows + 기타 DB PK 상태 표.

### 4.4 V3.X 흡수 (예: V3.30 발표 시)
```powershell
# dry-run으로 미리 검증
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py ingest --version V3.30 --dry-run

# 통과 시 live
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py ingest --version V3.30
```

### 4.5 양 lane pytest 일괄
```powershell
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py test
```
`tests/v3u/` (V3U 안전망 46+) + `tests/v3uc/` (3U_C 도구 32) 일괄 실행.

### 4.6 GUI 실행 (사용자 백테 시)
```powershell
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py gui
```
또는 헤드리스 점검 (Qt offscreen, 메인창 즉시 종료 시뮬):
```powershell
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_cli.py gui --offscreen
```

## 5. 안전 가드

| 가드 | 동작 |
|---|---|
| `db migrate <what>` `--confirm` 미지정 + `--dry-run` 미지정 | `exit 1`로 차단 (실수 변경 방지) |
| `db migrate strategy` 백업 디렉토리 없음 | 하위 `v3uc_strategy_migration.py`가 `exit 1`로 차단 |
| `verify` script 미발견 | `exit 2` + 에러 메시지 |
| `gui` `stom.py` 미발견 | `exit 2` + 에러 메시지 |
| `--dry-run` 전역 | 모든 subprocess 호출이 echo only (실 변경 없음) |
| utf-8 stdout/stderr 재설정 | Windows cp949 인코딩 실패 방지 (em-dash 등) |

## 6. 옵션 위치 자유도

`--workspace` 와 `--dry-run` 은 subcommand 앞·뒤 모두 허용 (`parents=` + `default=SUPPRESS` 패턴):

```powershell
python ...\v3uc_cli.py --dry-run status            # 앞
python ...\v3uc_cli.py status --dry-run            # 뒤
python ...\v3uc_cli.py ingest --version V3.30 --dry-run   # 뒤 (자연스러운 위치)
```

## 7. 실패 모드와 진단

| 증상 | 원인 | 대응 |
|---|---|---|
| `exit 1` `--confirm 또는 --dry-run 필요` | 실수 차단 가드 | 의도 확인 후 `--confirm` 추가 또는 `--dry-run` 사용 |
| `exit 2` `미발견` | 스크립트/stom.py 경로 어긋남 | `--workspace`로 경로 명시 |
| 일부 pytest fail | V3U 안전망 결함 | `verify` 실행하여 CRITICAL 라인 식별 + V3U 4단계 워크플로우 |
| GUI 행 (hang) | 헤드리스 환경에서 `gui` 호출 | `--offscreen` 추가 또는 `--dry-run`만 사용 |

## 8. 관련 문서

- `V3U_C_NEXT_STEPS.md` E2 항목 (옵션 정의 + 사이클 4 이력)
- `V3U_C_INFERENCE_LESSONS.md` (사이클 4 결함 기록 — argparse parents gotcha, cp949 인코딩)
- `V3U_C_INGEST_PIPELINE.md` (E1 V3.X 흡수 매뉴얼, ingest subcommand가 호출)
- `V3U_C_DB_MIGRATION_PLAN.md` (E5 DB 호환성 + E7 조건식, db scan/migrate가 호출)
- (V3U lane) `V3U_TEST_AUTOMATION_GUIDE.md` (verify subcommand가 호출하는 verifier 매뉴얼)
