# V3U_C DB 마이그레이션 종합 계획 (E5)

- 작성일: 2026-05-22
- 대상 lane: `STOM_Version_3U_C` (wt-3uc 코드 보관, 실행은 wt-3u의 `_database/` 대상)
- 사이클: 3U_C 사이클 2 (E5 신규 옵션 — DB 호환성 검증·PK 자동 추가 도구)
- 선행 문서: `docs/V3U_C_INGEST_PIPELINE.md` (E1), `docs/V3U_C_NEXT_STEPS.md` (decision tree)
- V3U lane 진실 원천: `docs/V3U_TRANSITION_AUDIT_2026-05-22.md`

---

## 1. 본 문서의 목적

사용자의 `_database/` 디렉토리는 STOM V2(Kiwoom API) 시절에 수집·저장된 DB다. V3는 LS증권 API를 사용하며 V3.08+에서 PRIMARY KEY를 도입했다. V2 DB로 V3 백테를 시도하면 두 가지 결함이 발생한다.

1. **컬럼 schema mismatch** — V2 기본 schema(39 컬럼)에 V3 expected 추가 컬럼(VI해제시간/최고매수금액 등 8개)이 없어 백테 KeyError
2. **PRIMARY KEY 누락** — V3.08+의 DB 검증이 통과 못 함 (`UNIQUE constraint` 또는 `데이터 중복 삽입` 오류)

본 문서는 위 두 결함을 자동·반자동으로 해소하는 절차(A++)를 정본화한다. 사용자가 실제로 stom.py에서 백테 1회를 완주할 수 있도록 하는 사전 마이그레이션 도구를 V3U_C lane에 신규 도입한다.

---

## 2. 사전 조사 — 현재 `_database/` 상태

### 2.1 인벤토리 (V3U 워크트리 `_database/` 기준)

| 파일 | 크기 | 종류 | 추정 출처 |
|---|---|---|---|
| `backtest.db` | 1.5 MB | 백테 결과 | V2 시절 |
| `backtest_history.db` | 40 KB | 백테 이력 | V2 시절 |
| `code_info.db` | 311 KB | 종목 정보 | V2 시절 |
| `coin_tick.db`, `coin_tick_back.db` | 0 byte | 빈 코인 틱 | 미사용 |
| `setting.db` | 184 KB | 사용자 설정 | V2 시절 (account/tele 등) |
| `setting_PCI.db` | 124 KB | PC 식별자 | V2 시절 |
| `stock_min_2025*.db` × 14+ | 5~12 MB 각각 | 종목별 분봉 (4월 2주~3주) | V2 Kiwoom 수집 |
| 분석 시스템 DB (`volume_spike_*`, `pattern_*`, `volatility_*`) | **없음** | 학습 안 됨 | V3 첫 학습 시 신규 |

### 2.2 stock_min_*.db 실 schema 검증 (2026-05-22 측정)

```
총 테이블: 57 (moneytop + 56 종목 코드)

table 025950:
  index (INTEGER)
  현재가 (REAL)
  시가 (REAL)
  고가 (REAL)
  저가 (REAL)
  등락율 (REAL)
  당일거래대금 (REAL)
  체결강도 (REAL)
  → PRIMARY KEY 없음 (V3.08 호환 X)
```

→ **확정**: 모든 stock_min DB가 V3.08+ 호환 안 됨. PK 추가 필요.

### 2.3 V3 expected schema (utility/db_control/update_db_20260418.py 기준)

V3.18 기준 expected 컬럼:
- `list_stock_min` = 47 컬럼 (index/현재가/.../분봉시가/분봉고가/분봉저가 등 V2 기본 39 컬럼 + VI해제시간/VI가격/VI호가단위/분봉시가/분봉고가/분봉저가/당일매수금액/최고매수금액/최고매수가격/당일매도금액/최고매도금액/최고매도가격 등 8 추가)

V2 기본 schema는 39 컬럼만, V3 expected는 47 컬럼 — **8 컬럼 보강 필요**.

---

## 3. V3 changelog에서 발견한 DB 영향 변경사항

`_update.txt` 검색 결과 (V3.0~V3.18 누적):

| 버전 | DB 영향 |
|---|---|
| **V3.08** | **PRIMARY KEY 삽입 — 기존 DB 호환 X, 백업+삭제 권장** (line 145) |
| V3.14 | "모든 분석 시스템 학습에 최근 30일 데이터만 사용" |
| **V3.15** | **모든 분석시스템 관련 DB 삭제 요망** (line 49) |
| V3.16 | 분석시스템 신뢰도 계산 방법 일부 수정 |
| V3.17 | 가격대분석 학습데이터 필요한 데이터만 로드 |
| V3.18 | DB 잔고 테이블 변동시만 저장 + 변손익분석 학습데이터 로드 함수명 수정 |

**핵심 invariant 2개**:
- V3.08+: 모든 학습·시장 DB에 PRIMARY KEY 필수
- V3.15+: 분석 학습 DB는 V3.14 이전 schema와 비호환

---

## 4. `update_db_20260418.py` 동작 분석

### 4.1 함수 시그니처

```python
def Updater(gubun, file_list):
    def convert_dataframe(df):
        if '당일매수금액' not in df.columns:    # V2 schema 자동 감지
            # 일자별 그룹화 + 누적 매수/매도금액 계산
            # 최고매수금액·최고매도금액·최고매수가격·최고매도가격 derive
        if 'VI해제시간' in df3.columns:
            df3 = df3[list_stock_tick]            # 47 컬럼 stock 정렬
        else:
            df3 = df3[list_stock_min]
        return df3
    ...
    df_converted.to_sql(code, con, index=False, if_exists='replace', chunksize=2000)
```

### 4.2 동작 매트릭스

| 항목 | 가능? | 비고 |
|---|---|---|
| V2 → V3 컬럼 schema 자동 변환 | ✅ | `if '당일매수금액' not in df.columns` 분기로 자동 감지 |
| VI해제시간/VI가격/VI호가단위 추가 | ✅ | `if 'VI해제시간' in df3.columns:` 기준 stock/basic 분기 |
| 최고매수금액 등 derive 계산 | ✅ | 일자별 누적값 자동 계산 |
| 다중 프로세스 변환 | ✅ | psutil.cpu_count로 multiprocessing |
| moneytop 테이블 제외 | ✅ | `table_list.remove('moneytop')` |
| **PRIMARY KEY 추가** | ❌ | `to_sql(if_exists='replace')`만, PK 안 추가 |
| backtest.db·code_info.db·setting.db 변환 | ❌ | `file_list = ['_tick_' in x or '_min_' in x and 'back' not in x]` — stock_min/tick만 처리 |

### 4.3 `update_db_20260418.bat`의 admin 권한

```batch
@echo off
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
)
...
python ./utility/db_control/update_db_20260418.py
pause
```

→ admin 권한은 **bat의 wrapper용**이지 python 자체엔 불필요. `_database/`는 사용자 디렉토리이므로 일반 권한으로 read+write 가능.

→ **`python utility/db_control/update_db_20260418.py` 직접 호출하면 admin 없이 동작**. Claude 자율 실행 가능.

---

## 5. 잔여 결함 — `update_db_20260418.py`가 못 하는 것

| 결함 | 영향 | 본 사이클 해결 방법 |
|---|---|---|
| PRIMARY KEY 미추가 | V3.08+ 검증 통과 못 함 | `scripts/v3uc_db_compatibility_check.py` 신규 (PK 진단 + `--add-pk` 자동 추가) |
| backtest.db / code_info.db / setting.db 미변환 | 위 3개 DB의 schema가 V3 expected와 다르면 fail | 진단 도구가 매트릭스 제공, 자동 변환은 별도 도구 (잔여 의무) |
| 분석 시스템 학습 DB 미정리 | V3.15 권장 사항 미준수 | 진단 도구가 존재 여부 보고 (현재 0건이므로 자동 충족) |

---

## 6. A++ 자동화 절차 (Claude 끝까지, 사용자 최종 1분만)

### Step 1 — Claude 자율 (wt-3uc)

1. 본 문서 작성 (`docs/V3U_C_DB_MIGRATION_PLAN.md`)
2. `scripts/v3uc_db_compatibility_check.py` 신규
   - `--scan`: PK 진단 매트릭스 출력 (read-only)
   - `--add-pk`: PK 누락 테이블에 자동으로 `CREATE TABLE ... PRIMARY KEY` 재생성
   - `--analyze-extra-dbs`: backtest/code_info/setting DB 별도 분석
3. `tests/v3uc/test_db_compatibility.py` 단위 테스트 (mock sqlite)
4. `CARRY_FORWARD_REGISTRY` 사이클 2 항목 등록
5. commit + push origin/STOM_Version_3U_C

### Step 2 — Claude 자율 (wt-3u에서 실행, 사용자 데이터 read+copy만)

```powershell
cd C:/System_Trading/STOM/STOM_V.wt-3u
xcopy _database _database_backup_2026-05-22 /E /I /Y
```

→ Claude가 PowerShell 명령으로 백업 자동 실행. 사용자 데이터 수정 없음(복사만).

### Step 3 — Claude 자율 (admin 우회, python 직접 호출)

```powershell
cd C:/System_Trading/STOM/STOM_V.wt-3u
python utility/db_control/update_db_20260418.py
```

→ V2 → V3 컬럼 schema 변환 (stock_min_*/tick_*.db 일괄).

### Step 4 — Claude 자율 (PK 진단)

```powershell
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_db_compatibility_check.py --scan
```

→ PK 매트릭스 + 누락 테이블 카운트 보고.

### Step 5 — Claude 자율 (PK 자동 추가, 필요 시)

```powershell
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_db_compatibility_check.py --add-pk
```

→ 누락 PK 자동 추가. 백업이 사전에 있어 안전.

### Step 6 — 사용자 (최종 시각 확인, 약 1분)

```powershell
cd C:/System_Trading/STOM/STOM_V.wt-3u
python stom.py
# 백테 라이브 탭 → 시작 버튼 클릭 → 백테 1회 완주 → 결과 차트 시각 확인
```

→ "그래프가 정상 그려졌나" 시각 판단은 사람만.

### Step 7 — Claude reactive (사용자 에러 보고 시)

V3U lane 4단계 워크플로우 적용.

---

## 7. 안전 invariant

| invariant | 보장 |
|---|---|
| V3 official source 0줄 수정 | utility/db_control/update_db_20260418.py 자체는 V3 official, 호출만 |
| V3U 안전망 0줄 수정 | tests/v3u/, scripts/v3u_* 변경 0 (3U_C 신규 도구만) |
| 사용자 데이터 안전 | Step 2에서 자동 백업, Step 5는 백업 보유 후에만 PK 추가 |
| dry-run 우선 | --scan은 read-only, --add-pk는 백업 보유 검증 |

---

## 8. 잔여 의무 (본 사이클 종료 후)

- backtest.db / code_info.db / setting.db schema 진단 결과에 따라 별도 변환 도구 (다음 사이클 후보)
- V3.19 발표 시 `v3uc_ingest_pipeline.py`(E1)가 DB 마이그레이션 단계도 자동 포함하도록 통합 (E1·E5 통합 검토)
- 분석 학습 DB 폴리시 자동화 (V3.15 권장 자동 적용)

---

## 9. 관련 문서

- `scripts/v3uc_db_compatibility_check.py` (본 사이클 산출)
- `tests/v3uc/test_db_compatibility.py` (본 사이클 산출)
- `docs/V3U_C_INGEST_PIPELINE.md` (E1, V3.X 흡수)
- `docs/V3U_C_INFERENCE_LESSONS.md` (3U_C 결함 진실 원천)
- `docs/V3U_C_NEXT_STEPS.md` (3U_C decision tree, E5 옵션 추가)
- `docs/CARRY_FORWARD_REGISTRY.md` (V3U_C custom allowlist)
- (V3U lane) `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` (3U_C 생성 전 중간 점검)
- (V3U lane) `utility/db_control/update_db_20260418.py` (V3 official, 컬럼 schema 변환)
- (V3U lane) `_update.txt` (V3 changelog V3.0~V3.18)
