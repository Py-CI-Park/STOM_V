# V3K-DESIGN-1 DB/학습 데이터 설계

작성일: 2026-05-09 KST
대상 root lane: `STOM_Version_2` (`C:/System_Trading/STOM/STOM_V`)
최종 구현 lane: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
참조 lane: `STOM_Version_3` (`C:/System_Trading/STOM/STOM_V.wt-3`)
상위 문서: `docs/update_log/2026-05-08_v3k_phase0_design_kickoff.md`
상세 spec: `docs/superpowers/specs/2026-05-09-v3k-db-learning-migration-spec.md`
작성 성격: 설계 단계, runtime 코드 변경 0건, DB 파일 변경 0건

## 0. 한 줄 결론

`V3K-DESIGN-1`은 V3 학습/분석 DB를 2U_C에 바로 병합하지 않고, **Kiwoom 유지 + shadow/read-only + feature flag OFF 기본값** 방식으로 이행하기 위한 DB/학습 데이터 설계이다.

이번 단계에서 확정한 원칙은 다음과 같다.

```text
1. 2U_C의 기존 Kiwoom setting.db / strategy.db / tradelist.db를 V3 파일로 대체하지 않는다.
2. V3 analyzer 학습 DB는 별도 V3K analysis DB 묶음으로 시작한다.
3. 백테스트는 기준일 이전 학습 데이터만 로드해야 한다.
4. 실시간 거래는 주문 경로를 바꾸지 않고 sidecar/advisory read-only로 시작한다.
5. 실제 DB 생성/마이그레이션은 다음 단계의 read-only dry-run script와 별도 승인 후 수행한다.
```

## 1. 이번 단계의 범위

### 1.1 포함

| 영역 | 이번 산출물 |
| --- | --- |
| V3 vs 2U_C DB schema diff | 코드/샘플 DB read-only 탐색 기반 분류표 |
| 학습 데이터 DB 후보 | analyzer별 DB 파일/테이블/PK/날짜 기준 명세 |
| Kiwoom 유지 mapping | 2U_C 보존 테이블과 V3K shadow 테이블 분리 기준 |
| backup/rollback | B-1 방식의 실제 cutover 전제조건과 금지사항 |
| feature flag | backtest/realtime 학습 활성 시점과 기본 OFF 정책 |
| dry-run script 초안 | 다음 단계에서 작성할 read-only script 인터페이스 |

### 1.2 제외

```text
- analyzer 코드 이식
- database_check.py 수정
- setting_base.py 수정
- _database 또는 *.db 파일 생성/수정/커밋
- backtest/realtime runtime wiring
- feature flag 코드 도입
- 2U_C 실제 cutover
```

## 2. 탐색 근거

`omx explore`는 Windows 환경에서 POSIX wrapper allowlist 문제로 실행되지 않아, PowerShell + ripgrep + Python read-only 탐색으로 대체했다.

확인한 주요 근거:

| 근거 | 내용 |
| --- | --- |
| V3 `utility/settings/setting_base.py` | `DB_PATH = './_database'`, core DB 상수만 정의, `UI_NUM['학습로그']` 존재 |
| V3 `utility/db_control/database_check.py` | V3 setting/strategy/tradelist/code_info schema 초기화, `back` table에 분석/자동학습 설정 포함 |
| V3 `strategy/analyzer_*.py` | analyzer별 별도 analysis DB 파일과 `CREATE TABLE IF NOT EXISTS` 정의 |
| V3 `backtest/backengine_base.py` | analyzer 생성, 학습 데이터 load, 현재 캔들 분석 wiring 존재 |
| 2U_C `utility/setting_base.py` | `STOM_CLI_DATABASE_DIR` 및 개별 DB env override를 지원하는 custom 경로 정책 존재 |
| 2U_C `utility/database_check.py` | Kiwoom 중심 setting schema, `stock/coin/future` legacy table, 일부 microstructure/risk column만 보유 |
| 2U_C `strategy/analyzer_risk.py` | BP-006A dormant 보존, V3 analyzer runtime 전체는 미연결 |

## 3. V3 학습 DB 후보

V3 analyzer code 기준으로 다음 학습 DB가 식별된다.

| ID | V3 파일 | DB 파일 | setting table | score table 패턴 | PK |
| --- | --- | --- | --- | --- | --- |
| LDB-PT | `strategy/analyzer_candle_pattern.py` | `pattern_analysis.db` | `pattern_setting` | `{strategy_gubun}_pattern_score` | `(code, pattern_name, setting_hash, last_update)` |
| LDB-VS | `strategy/analyzer_volume_spike.py` | `volume_spike.db` | `spike_setting` | `{strategy_gubun}_volume_spike_{tick|min}` | `(code, spike_level, setting_hash, last_update)` |
| LDB-VF | `strategy/analyzer_volume_profile.py` | `volume_profile.db` | `volume_setting` | `{strategy_gubun}_volume_score_{tick|min}` | `(code, price_level, setting_hash, last_update)` |
| LDB-VP | `strategy/analyzer_volatility_pattern.py` | `volatility_pattern.db` | `volatility_setting` | `{strategy_gubun}_volatility_pattern_{tick|min}` | `(code, volatility_level, setting_hash, last_update)` |
| LDB-VT | `strategy/analyzer_volatility_stop_take.py` | `volatility_stop_take.db` | `volatility_stop_take_setting` | `{strategy_gubun}_volatility_{tick|min}` | `(code, volatility_level, setting_hash, last_update)` |
| LDB-MS | `strategy/analyzer_microstructure.py` | 별도 DB 없음 | 없음 | in-memory 계산 | DB migration 대상 아님 |
| LDB-RK | `strategy/analyzer_risk.py` | 별도 DB 없음 | 없음 | in-memory 계산 | DB migration 대상 아님 |

### 3.1 V3K 채택 방식

V3K에서는 위 파일명을 그대로 `_database/`에 즉시 생성하지 않는다.

```text
DESIGN-1 결정:
- shadow path: `_database_v3k_shadow/`
- runtime cutover 전까지 git ignored / runtime 미사용
- learning DB 파일은 shadow에서 먼저 생성/검증
- 2U_C 기본 `_database/`는 변경하지 않음
```

### 3.2 table naming 보정

V3의 `strategy_gubun`은 V3 market 체계와 연결되어 있으므로 2U_C/Kiwoom에서는 mapping이 필요하다.

| V3 table prefix 후보 | 2U_C/Kiwoom mapping 원칙 |
| --- | --- |
| `stock_*` | Kiwoom 국내주식 기본 mapping |
| `stock_etf_*`, `stock_etn_*`, `stock_usa_*` | 2U_C에 동등 runtime이 없으면 hold 또는 별도 market id 필요 |
| `future_*`, `future_nt_*`, `future_os_*` | Kiwoom/기존 2U_C 선물 구조와 충돌 가능성이 높아 DESIGN-2에서 별도 검토 |
| `coin_*`, `coin_future_*` | Kiwoom 목적과 직접 무관하지만 2U_C coin 기능 보존을 위해 read-only 후보로 분리 |

## 4. V3 vs 2U_C core DB diff 판정

### 4.1 `setting.db`

| 항목 | V3 | 2U_C | V3K 판정 |
| --- | --- | --- | --- |
| `main` | `거래소`, `타임프레임`, `데이터저장`, `모의투자` 중심 | `증권사`, `주식에이전트`, `주식트레이더`, `주식데이터저장` 등 Kiwoom 중심 | V3로 대체 금지 |
| `back` | `자동학습`, `시장미시구조분석`, `리스크분석`, `캔들분석`, `거래량분석`, `가격대분석`, `변동성분석`, `변손익분석` 포함 | `시장미시구조분석`, `시장리스크분석` 일부만 존재 | 기존 table 확장 전 별도 V3K flag table 권장 |
| `etc` | `웹대시보드`, `웹대시보드포트번호`, `팩터선택`, `시가총액상위제외목록` 포함 | worktree policy 기반 custom columns | 즉시 merge 금지, 필요 항목만 별도 table |
| `account` | LS/API 계정 구조 가능성 | Kiwoom `sacc`, coin `cacc` | LS 직접 의존 제외 |
| `stock`, `coin` | V3에도 일부 보유 | 2U_C legacy runtime 중심 | 2U_C 보존 |

결정:

```text
setting.db는 V3로 교체하지 않는다.
V3K 학습 flag와 analyzer 설정은 `v3k_meta.db` 또는 shadow 전용 setting table로 시작한다.
```

### 4.2 `strategy.db`

| 항목 | V3 | 2U_C | V3K 판정 |
| --- | --- | --- | --- |
| market table 수 | `stock`, `stock_etf`, `stock_etn`, `stock_usa`, `future`, `future_nt`, `future_os`, `coin`, `coin_future` 조합으로 다수 | `stock/coin/future` legacy table 중심 | broad merge 금지 |
| `formula` | `PRIMARY KEY ('수식명')` 명시 | 기존 table + index 보정 | formula manager 이식은 DESIGN-2에서 계약 정의 |
| `_passticks`, `_optigavars` | V3 신규 table family | 2U_C 대부분 없음 | analyzer/strategy contract 이후 선택 적용 |

결정:

```text
strategy.db는 analyzer table 저장소가 아니다.
학습 DB는 별도 DB 파일로 분리하고, strategy formula 연동은 V3K-DESIGN-2에서 다룬다.
```

### 4.3 `tradelist.db`

| 항목 | V3 | 2U_C | V3K 판정 |
| --- | --- | --- | --- |
| market별 주문/잔고 table | V3 market family 확장 | `s_`, `c_`, `f_` legacy table + custom queue table | 직접 merge 금지 |
| 실시간 학습 데이터 | V3 realtime analyzer가 side data를 읽을 수 있음 | Kiwoom 주문/체결 경로 보존 필요 | V3K_REALTIME은 read-only advisory만 |

결정:

```text
실시간 학습 기능은 tradelist.db를 쓰기 대상으로 삼지 않는다.
sidecar가 학습 DB와 현재 snapshot만 읽고, 주문/잔고 table에는 쓰지 않는다.
```

### 4.4 `code_info.db`

| 항목 | V3 | 2U_C | V3K 판정 |
| --- | --- | --- | --- |
| stock metadata | `stock_info`, `stock_etf_info`, `stock_etn_info`, `stock_usa_info`, `상장주식수` | `stockinfo`, `코스닥` | 별도 mapping 필요 |
| listed shares | V3.07/V3.17 관련 | 2U_C schema 미보유 | `v3k_code_meta.db` 후보 |

결정:

```text
상장주식수/listed-shares는 기존 code_info.db를 즉시 변경하지 말고 `v3k_code_meta.db` 후보로 분리한다.
Kiwoom code shape와 KOSDAQ flag는 보존한다.
```

## 5. V3K DB 파일 배치안

### 5.1 shadow stage

```text
_database_v3k_shadow/
  v3k_meta.db
  v3k_code_meta.db
  pattern_analysis.db
  volume_spike.db
  volume_profile.db
  volatility_pattern.db
  volatility_stop_take.db
  manifest.json              # git tracked 금지, dry-run output only
```

### 5.2 future cutover 후보

```text
_database/
  기존 2U_C DB 유지
  pattern_analysis.db         # V3K-VERIFY 이후에만 복사/생성 후보
  volume_spike.db
  volume_profile.db
  volatility_pattern.db
  volatility_stop_take.db
  v3k_meta.db
  v3k_code_meta.db
```

### 5.3 git 관리 원칙

```text
절대 commit 금지:
- _database/
- _database_v3k_shadow/
- backup/_database_pre_v3k_*/
- *.db
- manifest.json runtime output
```

## 6. feature flag별 DB 사용 시점

| Flag | 기본값 | DB 접근 | 주문/거래 영향 | 활성 가능 시점 |
| --- | --- | --- | --- | --- |
| `V3K_BACKTEST_LEARNING_ENABLED` | False | OFF: 접근 없음 / ON: analysis DB read-only | 백테스트 결과만 영향 | V3K-IMPL-3 + 누수 guard 통과 후 |
| `V3K_REALTIME_LEARNING_ENABLED` | False | OFF: 접근 없음 / ON: analysis DB read-only | 주문 경로 변경 금지, advisory만 | V3K-IMPL-4 + paper trading 24h 후 |
| `V3K_ANALYSIS_UI_ENABLED` | False | analysis DB read-only | 없음 | analyzer DB health 통과 후 |

초기에는 환경 변수 override보다 `v3k_meta.db`의 manifest/flag table을 먼저 설계하고, runtime 연결 전에는 문서와 dry-run script만 둔다.

## 7. 백테스트 학습 데이터 누수 방지 규칙

V3 code inspection 결과, 일부 analyzer는 `last_update < backtest_date`를 사용하고 일부는 `<=`를 사용한다.

| Analyzer | V3 observed query | V3K 결정 |
| --- | --- | --- |
| Candle pattern | `last_update < backtest_date` | 채택 |
| Volume spike | `last_update < backtest_date` | 채택 |
| Volume profile | `last_update < backtest_date` | 채택 |
| Volatility pattern | `last_update <= date` | 기본 보류, `< backtest_date`로 정규화 후보 |
| Volatility stop/take | `last_update <= backtest_date` | 기본 보류, `< backtest_date`로 정규화 후보 |

V3K 규칙:

```text
V3K backtest learning load는 기본적으로 `last_update < backtest_date`만 허용한다.
동일 일자 학습 데이터 사용이 필요한 경우에는 데이터 생성 시각과 백테스트 시작 시각이 분리되어 있음을 별도 증명해야 한다.
증명 전에는 같은 날짜 학습 데이터를 미래 데이터 누수 후보로 본다.
```

## 8. 실시간 학습 데이터 규칙

실시간 거래에서 학습 데이터는 다음 단계로만 진입한다.

```text
Phase R0: OFF, 접근 없음
Phase R1: sidecar가 analysis DB read-only open 가능
Phase R2: advisory score를 로그/별도 queue에만 출력
Phase R3: 사용자가 명시 승인한 paper trading에서만 전략 변수로 노출
Phase R4: 실거래 주문 조건 반영은 V3K-VERIFY 별도 승인 전 금지
```

금지:

```text
- sidecar가 Kiwoom API를 직접 호출
- sidecar가 주문/잔고/tradelist table에 쓰기
- score 미존재 시 주문 판단 기본값을 바꾸기
- DB read 지연이 main trader latency를 증가시키기
```

## 9. adapter 설계

V3K DB adapter는 다음 책임을 가진다.

| Adapter | 책임 | 이번 단계 상태 |
| --- | --- | --- |
| `V3KLearningDbPaths` | DB_PATH, shadow path, runtime path 결정 | 문서 설계 |
| `V3KSchemaManifest` | analyzer DB/table/PK manifest 생성 | script 초안 |
| `V3KBacktestLearningReader` | 기준일 이전 학습 데이터 read-only 로드 | DESIGN-2/IMPL-3 후보 |
| `V3KRealtimeLearningReader` | 실시간 sidecar read-only 로드 | DESIGN-2/IMPL-4 후보 |
| `V3KCodeMetaMapper` | Kiwoom code_info와 V3 listed-shares mapping | DESIGN-2 후보 |

2U_C의 기존 `utility.setting_base._resolve_db()`와 CLI env override 정책은 보존한다. V3K adapter는 그 위에 shadow/runtime DB path를 추가하는 별도 layer로 설계한다.

## 10. backup / rollback 정책

### 10.1 backup

```text
backup/_database_pre_v3k_<YYYYMMDD-HHMMSS>/
```

backup은 cutover 직전 사용자 명시 승인 후에만 수행한다. 이번 DESIGN-1에서는 backup 명령을 실행하지 않는다.

### 10.2 cutover

cutover는 다음 조건을 모두 만족해야 한다.

```text
- V3K-DESIGN-1B read-only schema diff script 통과
- V3K-DESIGN-2 analyzer contract 통과
- V3K-IMPL-3/4 feature flag OFF regression 통과
- shadow DB healthcheck 통과
- 거래/백테스트 runtime 정지 확인
- 사용자 명시 승인
```

### 10.3 rollback

```text
1. runtime 정지
2. `_database/`를 손대기 전 backup 존재/해시 확인
3. 실패한 `_database/` 또는 V3K DB 파일 격리
4. backup 경로에서 원복
5. healthcheck + smoke 확인
6. 원인 문서화 전 재시도 금지
```

## 11. read-only dry-run script 초안

이번 단계에서는 script를 작성하지 않고, 다음 단계의 인터페이스만 고정한다.

### 11.1 `scripts/diff_v3_vs_2uc_db_schema.py`

```text
목적:
- V3와 2U_C의 sample DB/schema를 read-only로 읽는다.
- table/column/PK/index 차이를 JSON/Markdown report로 출력한다.
- DB 파일을 생성/수정하지 않는다.

예정 명령:
python scripts/diff_v3_vs_2uc_db_schema.py `
  --v3-root C:/System_Trading/STOM/STOM_V.wt-3 `
  --twouc-root C:/System_Trading/STOM/STOM_V.wt-dev `
  --output .omx/reports/v3k-db-schema-diff.json

허용 write:
- .omx/reports/*.json only

금지 write:
- _database/
- _database_v3k_shadow/
- *.db
```

### 11.2 `scripts/init_v3k_shadow_db.py --dry-run`

```text
목적:
- 실제 shadow DB 생성 전 SQL manifest만 생성한다.
- analyzer DB/table/PK 정의가 누락되지 않았는지 검증한다.

예정 명령:
python scripts/init_v3k_shadow_db.py --dry-run --manifest .omx/reports/v3k-shadow-manifest.json

DESIGN-1B에서는 --dry-run만 허용한다.
실제 DB 생성 옵션은 V3K-VERIFY 전까지 금지한다.
```

### 11.3 `scripts/v3k_db_health.py`

```text
목적:
- shadow 또는 runtime V3K DB가 존재할 때만 read-only healthcheck를 수행한다.
- table/PK/index/row count/sample query를 확인한다.

예정 명령:
python scripts/v3k_db_health.py --shadow-dir _database_v3k_shadow --read-only
```

## 12. 다음 단계

### 12.1 즉시 다음 단계: V3K-DESIGN-1B

다음 commit은 runtime 구현이 아니라 **read-only schema diff script 작성**이어야 한다.

```text
V3K-DESIGN-1B 목표:
- scripts/diff_v3_vs_2uc_db_schema.py 작성
- scripts/init_v3k_shadow_db.py --dry-run skeleton 작성
- scripts/v3k_db_health.py read-only skeleton 작성
- 출력은 .omx/reports/만 허용
- _database, _database_v3k_shadow, *.db 생성 금지
```

### 12.2 그 다음 단계: V3K-DESIGN-2

```text
- analyzer별 input/output contract
- Kiwoom candle/tick/snapshot data shape mapping
- V3 backengine_base wiring을 2U_C에 적용할 최소 adapter boundary
- AnalyzerRisk dormant → runtime 후보 승격 조건
```

## 13. 전체 계획 progress

| 단계 | 상태 | 설명 |
| --- | --- | --- |
| 1. V3 공식 lane 도입 | 완료 | V3.18 ingress 완료 |
| 2. V3U pyd-free 전환 | 완료 | 3U parity audit 완료 |
| 3. 2U_C safe-candidate 백포트 | 완료 | BP-002A~BP-011A micro 후보 소진 |
| 4. V3 미반영 신기능 audit | 완료 | 학습/분석/DB 미반영 확인 |
| 5. V3K 목표 재정의 | 완료 | Kiwoom 유지 + V3 신기능 목적 고정 |
| 6. V3K-DESIGN-0 | 완료 | Phase 0 kickoff |
| 7. V3K-DESIGN-1 | 완료 | 본 문서, DB/학습 설계 |
| 8. V3K-DESIGN-1B | 남음 | read-only schema diff script |
| 9. V3K-DESIGN-2 | 남음 | analyzer/data contract |
| 10. V3K-IMPL-3/4/5 | 남음 | backtest/realtime/UI 구현 |
| 11. V3K-VERIFY | 남음 | 통합 검증/승격 |

```text
전체 11단계 중 7단계 완료 = 64%
[██████░░░░] 64%

현재 단계 V3K-DESIGN-1 = 100%
[██████████] 100%
```

## 14. stop condition

본 단계는 다음 조건을 만족하면 완료로 본다.

```text
- 문서만 변경한다.
- root `STOM_Version_2`에 commit한다.
- V3K DB/학습 설계를 Kiwoom 유지 조건으로 정리한다.
- `_database`, `_log`, `*.db`, `backtest/graph` 변경이 없다.
- `git diff --check` 통과.
```

## 15. 한 줄 결론

V3K의 DB/학습 데이터 이행은 V3 DB를 2U_C에 덮어쓰는 작업이 아니라, **2U_C Kiwoom DB를 보존하면서 V3 analyzer 학습 DB를 shadow/read-only/feature-flag 방식으로 단계적으로 붙이는 작업**이다.