# V3U / 3U_C compact 재개 핸드오프 (2026-05-28)

본 문서는 **compact(컨텍스트 압축) 이후 동일 작업을 그대로 이어가기 위한 단일 진입점**이다. 재개 시 본 문서를 가장 먼저 읽으면 전체 맥락을 복원할 수 있다.

---

## 0. 30초 요약

- **V3U lane** (`wt-3u`, `STOM_Version_3U`): V3 pyd-free 추론 + V3.18~V3.29 흡수 완료 + 자동 검증 안전망(45+ pytest, CRITICAL baseline 0).
- **3U_C lane** (`wt-3uc`, `STOM_Version_3U_C`): custom 작업 lane. E1(V3.X 흡수 자동화) + E5(DB 호환성·PK) + E7(조건식 마이그레이션) 도입 완료.
- **DB 마이그레이션 완료**: 사용자 `_database/` V2→V3 변환 끝 (88,534 테이블 PK 추가 + 조건식 95 rows V2→V3 복사).
- **지금 잔여**: 사용자가 `python stom.py`로 **백테 1회 시각 확인** (조건식·DB 모두 준비됨). + V3.27~V3.29 GUI 검증.

---

## 1. 워크트리 / 브랜치 맵

| 워크트리 | 브랜치 | 역할 | HEAD (2026-05-28) |
|---|---|---|---|
| `C:/System_Trading/STOM/STOM_V` | STOM_Version_2 | V2 공식 ingress | — |
| `C:/System_Trading/STOM/STOM_V.wt-2u` | STOM_Version_2U | V2 pyd-free 추론 | — |
| `C:/System_Trading/STOM/STOM_V.wt-3` | STOM_Version_3 | V3 공식 보관 | 7faec937 |
| **`C:/System_Trading/STOM/STOM_V.wt-3u`** | **STOM_Version_3U** | **V3 pyd-free 추론 + 운영 + 백테 + DB** | 878e0d5b |
| **`C:/System_Trading/STOM/STOM_V.wt-3uc`** | **STOM_Version_3U_C** | **custom 도구 작성·보관** | 87b6645b |
| `C:/System_Trading/STOM/STOM_V.wt-dev` | STOM_Version_2U_C | V2 custom (V3K / AI strategy loop, 별개 작업) | — |

> **주의**: `wt-dev`(2U_C)는 별개의 AI strategy loop 작업 중이다 (MEMORY.md 참조). 본 V3U/3U_C 작업과 혼동 금지.

---

## 2. 진실 원천 문서 (재개 시 순서대로 참조)

### V3U lane (`wt-3u/docs/`)
1. `V3U_INFERENCE_LESSONS.md` — **과거**: 결함 #1~#15 기록 + 근본 원인 5 + 재발 방지 액션 5 + 사이클 1~11 이력
2. `V3U_NEXT_STEPS.md` — **미래**: 옵션 카탈로그(그룹 A~E) + 우선순위 + 사이클 선택 이력
3. `V3U_TRANSITION_AUDIT_2026-05-22.md` — 3U_C 생성 전 중간 점검 (다른 워크트리 영향 + 2U_C 컨셉 흡수)
4. `V3U_TEST_AUTOMATION_GUIDE.md` — 45 pytest + verifier 운영 매뉴얼
5. `V3U_PYD_REMOVAL_PLAN.md` §11 — 자동 검증 시스템 extension
6. `update_log/2026-05-28_v3u_resume_handoff.md` — **본 문서**

### 3U_C lane (`wt-3uc/docs/`)
7. `V3U_C_NEXT_STEPS.md` — 3U_C decision tree (E1~E7 옵션)
8. `V3U_C_INFERENCE_LESSONS.md` — 3U_C 결함 진실 원천
9. `V3U_C_INGEST_PIPELINE.md` — E1 V3.X 흡수 자동화 매뉴얼
10. `V3U_C_DB_MIGRATION_PLAN.md` — E5/E7 DB 마이그레이션 종합 계획
11. `CARRY_FORWARD_REGISTRY.md` — V3U_C custom allowlist rule + 사이클 1~3 등록

### 거버넌스 (양 lane 공유)
12. `CLAUDE.md` — V3U Test Automation Gate + 결함 발견·수정 4단계 워크플로우 + 사이클 종료 의무

---

## 3. 완료된 것 (compact 전 확정 상태)

### V3U lane
- V3.18 pyd-free 추론 + V3.19~V3.29 순차 흡수 완료
- 결함 #1~#15 모두 fix·회귀 테스트·문서화
- 자동 검증: 45+ pytest + CRITICAL drift baseline 0 (strict) + 통합 verifier 8 stage
- V3 official source 0줄 수정 invariant 유지

### 3U_C lane (사이클 1~3)
- **E1**: `scripts/v3uc_ingest_pipeline.py` (V3.X 흡수 5 T-step 자동화) + 4 pytest
- **E5**: `scripts/v3uc_db_compatibility_check.py` (PK 진단·자동 추가) + 7 pytest
- **E7**: `scripts/v3uc_strategy_migration.py` (V2→V3 조건식 마이그레이션) + 5 pytest
- 총 16 pytest PASS

### DB 마이그레이션 (사용자 `_database/`, 완료)
- 백업: `_database_backup_2026-05-22` (1175 파일)
- Step 3: `update_db_20260418.py` V2→V3 컬럼 변환 (1166 stock DB)
- Step 5: 88,534 테이블 PRIMARY KEY 추가 (에러 0, V3.08 호환)
- E7: 조건식 95 rows V2→V3 복사 (stock_buy 51 / stock_sell 35 / opti 9)
- **검증**: `stock_buy=51 rows, stock_sell=35 rows` 현재도 보존 확인됨 (2026-05-28)

---

## 4. 잔여 작업 (재개 후 진행)

### 최우선 — 사용자 직접 (Step 6, 약 1분~15분)
백테에 필요한 DB·조건식 모두 준비 완료. 사용자가 시각 확인만 남음:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-3u
python stom.py
```
1. 메인창 + 9탭 표시 (사이클 6에서 이미 PASS)
2. **백테 라이브** 탭 → **백테스트 시작** → 51 매수 + 35 매도 조건식 표시 확인
3. 조건식 선택 + 백테 1회 → DB/PK 오류 없이 완주 + 결과 차트
4. (V3.27~29 신규 기능 GUI 검증 — 878e0d5b 체크리스트 참조)
5. 종료 시 cmd 창 traceback 없음

### 결과별 다음 액션
- ✅ 백테 정상 → 사이클 10·11 종료. lane 안정. 다음 사이클 후보(E2/E3/E4) 선택
- ⚠️ 조건식 표시 안 됨 → 다른 거래소 prefix 마이그레이션 (`--target stock_etf/coin/future`)
- ⚠️ DB 다른 오류 → 기타 DB(backtest/code_info/setting) PK/schema (E5 v2 또는 E8 신규 사이클)
- ⚠️ V3.27~29 GUI 결함 → V3U lane 4단계 워크플로우

### 자율 가능 후보 (Claude)
- 3U_C E2 (STOM_CLI 자동화) / E3 (web_dashboard) / E4 (백테 최적화)
- 기타 DB 마이그레이션 도구 (backtest/code_info/setting PK)
- V3.30+ 발표 시 E1 ingest pipeline 실 dry-run

---

## 5. compact 후 재개 명령어 (복사용)

### 5.1 재개 첫 명령 (맥락 복원)
```
docs/update_log/2026-05-28_v3u_resume_handoff.md 읽고 V3U/3U_C 작업 이어서 진행해줘
```

### 5.2 상태 빠른 확인 (Claude가 실행)
```powershell
# 양 lane HEAD + 워크트리
git -C C:/System_Trading/STOM/STOM_V.wt-3u log --oneline -3
git -C C:/System_Trading/STOM/STOM_V.wt-3uc log --oneline -3
git worktree list

# 조건식 마이그레이션 보존 확인
cd C:/System_Trading/STOM/STOM_V.wt-3u
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_strategy_migration.py --db ./_database/strategy.db scan

# DB PK 호환성 확인
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_db_compatibility_check.py --db-dir ./_database scan

# 3U_C 도구 회귀
cd C:/System_Trading/STOM/STOM_V.wt-3uc && python -m pytest tests/v3uc/ -q

# V3U 안전망 회귀
cd C:/System_Trading/STOM/STOM_V.wt-3u && python -m pytest tests/v3u/ -q
```

### 5.3 사용자 백테 시각 확인 (Step 6)
```powershell
cd C:\System_Trading\STOM\STOM_V.wt-3u
python stom.py
```

### 5.4 백업 복원 (문제 시)
```powershell
cd C:\System_Trading\STOM\STOM_V.wt-3u
rmdir _database /s /q
move _database_backup_2026-05-22 _database
```

### 5.5 다른 거래소 조건식 추가 마이그레이션 (필요 시)
```powershell
cd C:\System_Trading\STOM\STOM_V.wt-3u
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_strategy_migration.py --target coin migrate
python C:\System_Trading\STOM\STOM_V.wt-3uc\scripts\v3uc_strategy_migration.py --target future migrate
```

---

## 6. 핵심 invariant (재개 후에도 반드시 준수)

| invariant | 내용 |
|---|---|
| V3 official source 0줄 수정 | `backtest/`, `strategy/`, `trade/`, `utility/`, `stom.py`, `ui/create_widget/`, `ui/update_widget/`, `ui/draw_chart/`, `ui/event_click/`, `ui/etcetera/` 절대 수정 금지 |
| V3U 안전망 격리 | `tests/v3u/`, `scripts/v3u_*`, `ui/main_window.py`는 V3U lane(wt-3u)에서만 수정 |
| 3U_C custom 격리 | custom 도구는 `wt-3uc`에서 작성·commit. 실행은 wt-3u에서 절대경로 호출 |
| 한글 commit | 모든 commit 제목·본문 한글 (CLAUDE.md Commit Language Rules) |
| 4단계 워크플로우 | 결함 발견 시: 발견→V3U/3U_C 전용 수정→회귀 테스트→LESSONS·NEXT_STEPS 갱신 |
| 사이클 종료 의무 | LESSONS.md §6/§7 + NEXT_STEPS.md §5 갱신 |
| 백업 보유 검증 | DB 변경 도구는 `_database_backup_*` 보유 시에만 write |

---

## 7. 작업 위치 빠른 참조

| 작업 | 위치 |
|---|---|
| 사용자 stom.py 실행·백테·DB | `wt-3u` |
| V3U pyd 추론 결함 fix | `wt-3u` (`ui/main_window.py`) |
| V3U 안전망 테스트 추가 | `wt-3u` (`tests/v3u/`) |
| 3U_C custom 도구 작성 | `wt-3uc` (`scripts/v3uc_*`, `tests/v3uc/`) |
| V3 정규 업데이트 흡수 | `wt-3u` (`git merge STOM_Version_3` + verifier) 또는 3U_C E1 ingest pipeline |

---

## 8. 관련 commit (최근 누적)

### V3U lane
- 878e0d5b 다음 직접 테스트 단계 기록 (현 HEAD)
- 7b068a09 V3.29 pyd-free 반영
- 2d09bad3 사이클 11 (E7 마이그레이션) 기록
- 6d359932 사이클 10 (E5 + A++ DB 마이그레이션) 기록

### 3U_C lane
- 87b6645b E7 strategy.db 마이그레이션 (현 HEAD)
- c0c43958 E5 DB 호환성·PK
- ebd9a8f3 E1 V3.X 흡수 파이프라인
- 2ba974f8 Phase A 거버넌스
