# V3K DB/학습 데이터 migration spec

작성일: 2026-05-09 KST
상위 update log: `docs/update_log/2026-05-09_v3k_design_1_db_learning_design.md`
대상 구현 lane: `STOM_Version_2U_C`
상태: DESIGN-1, 실행 금지 spec

## 1. 목적

이 spec은 V3의 학습/분석 DB 구조를 2U_C에 적용하기 위한 schema/migration/rollback 기준을 정의한다.

핵심 원칙:

```text
- Kiwoom setting/trading schema 보존
- LS증권 직접 의존 제외
- shadow DB 우선
- feature flag default OFF
- read-only dry-run 검증 전 runtime 연결 금지
```

## 2. 기준 lane / HEAD

| Lane | Path | 역할 |
| --- | --- | --- |
| V3 | `C:/System_Trading/STOM/STOM_V.wt-3` | V3 학습/분석 DB source |
| 2U_C | `C:/System_Trading/STOM/STOM_V.wt-dev` | 최종 적용 대상, Kiwoom 유지 |
| Root | `C:/System_Trading/STOM/STOM_V` | 공식 문서/계획 commit lane |

## 3. V3 learning schema manifest

| DB | Tables | Primary key |
| --- | --- | --- |
| `pattern_analysis.db` | `pattern_setting`, `{strategy_gubun}_pattern_score` | setting: `(market)`, score: `(code, pattern_name, setting_hash, last_update)` |
| `volume_spike.db` | `spike_setting`, `{strategy_gubun}_volume_spike_{tick|min}` | setting: `(market, is_tick)`, score: `(code, spike_level, setting_hash, last_update)` |
| `volume_profile.db` | `volume_setting`, `{strategy_gubun}_volume_score_{tick|min}` | setting: `(market, is_tick)`, score: `(code, price_level, setting_hash, last_update)` |
| `volatility_pattern.db` | `volatility_setting`, `{strategy_gubun}_volatility_pattern_{tick|min}` | setting: `(market, is_tick)`, score: `(code, volatility_level, setting_hash, last_update)` |
| `volatility_stop_take.db` | `volatility_stop_take_setting`, `{strategy_gubun}_volatility_{tick|min}` | setting: `(market, is_tick)`, score: `(code, volatility_level, setting_hash, last_update)` |

## 4. V3K 추가 meta schema 후보

### 4.1 `v3k_meta.db`

```sql
CREATE TABLE v3k_feature_flags (
    name TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT,
    note TEXT
);

CREATE TABLE v3k_schema_manifest (
    db_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    schema_hash TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_commit TEXT,
    last_verified_at TEXT,
    PRIMARY KEY (db_name, table_name)
);
```

### 4.2 `v3k_code_meta.db`

```sql
CREATE TABLE v3k_listed_shares (
    code TEXT NOT NULL,
    market TEXT NOT NULL,
    listed_shares INTEGER,
    source TEXT NOT NULL,
    as_of_date INTEGER NOT NULL,
    PRIMARY KEY (code, market, as_of_date)
);
```

주의: 위 SQL은 DESIGN-1B script manifest 후보이며, 이번 commit에서 실행하지 않는다.

## 5. migration 분류

| 분류 | 처리 |
| --- | --- |
| V3 analyzer DB 신규 | shadow DB에만 생성 후보 |
| V3 setting.db `back` analyzer columns | 2U_C 기존 table에 즉시 추가 금지, `v3k_meta.db` flag 우선 |
| V3 code_info listed shares | `v3k_code_meta.db` 우선 |
| V3 strategy market family | DESIGN-2 analyzer contract 전까지 hold |
| V3 tradelist market family | 실시간 주문 경로와 분리, merge 금지 |
| 2U_C Kiwoom account/main schema | 무조건 보존 |

## 6. backup policy

```text
backup root: backup/_database_pre_v3k_<YYYYMMDD-HHMMSS>/
trigger: cutover 직전 사용자 명시 승인
verification: file count, size, sha256 manifest, sample sqlite query
```

DESIGN-1/1B에서는 backup을 실행하지 않는다.

## 7. rollback policy

```text
- cutover 실패 시 runtime 정지
- 실패 DB 격리
- backup manifest 검증
- backup/_database_pre_v3k_* → _database 복원
- healthcheck 통과 전 재시작 금지
```

## 8. dry-run scripts 예정 contract

| Script | Mode | Writes allowed | Forbidden |
| --- | --- | --- | --- |
| `scripts/diff_v3_vs_2uc_db_schema.py` | read-only | `.omx/reports/*.json` | DB 파일 생성/수정 |
| `scripts/init_v3k_shadow_db.py --dry-run` | manifest only | `.omx/reports/*.json` | `_database_v3k_shadow/*.db` 생성 |
| `scripts/v3k_db_health.py --read-only` | read-only | stdout/report | DB 수정 |

## 9. acceptance criteria

```text
[ ] schema diff report가 V3/2U_C core DB 차이를 출력한다.
[ ] analyzer learning DB manifest가 5개 DB를 모두 포함한다.
[ ] feature flag 기본값이 모두 OFF로 정의된다.
[ ] 백테스트 학습 loader 기준은 기본 `last_update < backtest_date`로 고정된다.
[ ] 실시간 학습 loader는 read-only advisory만 허용한다.
[ ] `_database`, `_database_v3k_shadow`, `*.db`가 git 변경에 포함되지 않는다.
```

## 10. 다음 단계

`V3K-DESIGN-1B`에서 이 spec을 바탕으로 read-only script를 작성한다. runtime wiring은 `V3K-DESIGN-2`와 `V3K-IMPL-*` 전까지 금지한다.