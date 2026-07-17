# 대시보드 v4 연구 데이터 계약 — /research 4엔드포인트 명세 (P3-1, 2026-07-12)

> **배너: 구현(P4)은 사용자 go + 기존 V4 대시보드 PR(loop/process-research-pipeline) 조율 필요 — 본 문서는 명세만.**
>
> 지위: WBS v3(`2026-07-12_asset_integration_and_dashboard_plan.md`) §4·§6의 **P3-1 산출물**. 백로그 A10(W7-DC) 이행 — "재계산 금지·read-only 뷰어" 1원칙을 데이터 계약으로 봉인한다.
> 짝 문서: `2026-07-12_dashboard_view_specs.md`(P3-2 — 뷰 5종이 본 계약을 소비).
> 감사 구속: `2026-07-11_alpha_restart_research_validity_audit.md`(딱지·표현 교정 조항)를 응답 필드 수준에서 강제한다.
>
> **정본 정합 선언**: 카탈로그 스키마 정본은 `alpha_lab/catalog/schema.py`(P0 — 본 문서 작성 중 생성 확인)다. 본 계약의 테이블·컬럼명·딱지 어휘는 그 DDL과 `alpha_lab/catalog/loaders.py`·`builder.py`·`assets_registry.py`의 실제 적재 규칙에 **정합시켜 작성**했다. 이후 P0 개정 시 본 문서를 동기화하며, 상충 시 `schema.py`가 우선한다. 카탈로그가 아직 채우지 못하는 요구(§8 표)는 계약을 바꾸지 않고 "확장 제안"으로만 남겼다.

---

## 0. 쉬운 요약

대시보드는 **전시실**이고 카탈로그 DB(`research_assets.db`)는 **창고**다. 전시실에는 공작기계(재계산)가 없다 — 창고에서 완성된 전시품(사전 집계·판정 원문)을 꺼내 유리장에 넣고, 유리장마다 **정품 딱지**(`status_tag`·`label_tag`)를 그대로 붙여 보여줄 뿐이다. 전시실이 창고 물건을 깎거나 다시 조립하는 순간 "연구 수치 ≠ 화면 수치" 사고가 시작되므로, 본 계약은 그 행위 자체를 금지한다.

## 1. 제1원칙 — read-only 뷰어 (위반 시 구현 리젝)

1. **재계산 금지**: API는 어떤 통계(평균·CI·비율·분위수·카운트 집계)도 계산하지 않는다. `research_assets.db` 카탈로그 테이블 **SELECT-only**. 허용 연산은 WHERE 필터·ORDER BY 정렬·LIMIT/OFFSET·`SELECT DISTINCT`(§4.3 파티션 목록)뿐이다. `AVG()`·`SUM()`·`GROUP BY` 등 SQL 집계 함수 금지(분포 요약은 전부 카탈로그에 사전 집계로 존재해야 한다).
2. **역직렬화 ≠ 재계산(허용 경계 명시)**: JSON/CSV TEXT 컬럼(`key_metrics_json`·`ledger_rows`(CSV)·`year_delta_json`·`extra_json`·`rank_metrics_json`)을 구조화 객체로 풀어 반환하는 것은 표현 변환이며 허용한다. 그 값으로 새 수치를 만들면 위반이다.
3. **원문 보존**: 판정 문구(`verdict`)·딱지(`status_tag`·`label_tag`)·핵심 수치는 카탈로그 원문 그대로 반환한다. 서버 재요약·반올림·단위 환산 금지(표시 환산은 뷰 렌더링 규칙 몫 — P3-2 §1.3).
4. **레인 간 파일 의존 금지**: 뷰어(wt-dev)는 카탈로그 DB **파일 1개**만 읽는다. `assets.path`·`report_path` 등 카탈로그가 가리키는 원천 파일(parquet/json/md/png)을 대시보드가 직접 열지 않는다 — 경로는 표시·복사용 참조 문자열이다. 빌드 영수증 json(카탈로그 옆 파일)도 열지 않는다.
5. **쓰기 금지**: 4엔드포인트는 전부 GET이며 INSERT/UPDATE/DELETE/ATTACH/쓰기 PRAGMA/트랜잭션 시작을 하지 않는다.

## 2. 카탈로그 DB 경로 설정값 계약 (레인 간 심볼릭 의존 금지)

카탈로그 정본 위치(생산 측): `docs/research/condition_research/research_runs/alpha_restart_20260710/research_assets.db` — git 제외(빌더가 `.gitignore` 자동 보장), 재생성 명령 `python scripts/build_research_catalog.py`(assets 자기 행에 등재).

| 항목 | 계약 |
|---|---|
| 설정 키 | 환경변수 `STOM_RESEARCH_ASSETS_DB` = 카탈로그 DB **절대경로** 1개. (보조로 대시보드 설정파일 키를 둘 경우 env가 우선 — 키 확정은 P4, §8-5) |
| 읽는 시점 | 프로세스 기동 시 1회 + 요청 단위 재검사(파일 mtime 변화 감지). 상주 커넥션 금지 — 요청마다 열고 닫는다(빌더의 원자 교체와 stale 핸들 충돌 방지) |
| 기본값 | **없음**. 미설정 시 4엔드포인트 전부 `{"available": false, "reason": "catalog_not_configured"}` |
| 금지 1 | 워크트리 상대경로 하드코딩(예: `../STOM_V.wt-alpha/...`) — 레인 배치가 바뀌면 침묵 실패한다 |
| 금지 2 | 심볼릭 링크/정션으로 wt-dev 안에 카탈로그를 비추는 방식(과거 V1 심링크 회귀 금지) |
| 금지 3 | wt-alpha 파이썬 모듈 임포트. 계약 대상은 **SQLite 파일 포맷 하나**다 |
| 열기 방식 | `sqlite3.connect("file:{path}?mode=ro", uri=True)` — 읽기 전용 URI 필수. `immutable=1` 금지(빌더가 갱신할 수 있음) |
| 파일 부재 | `{"available": false, "reason": "catalog_not_found", "path_hint": "<설정값 마지막 2계층만>"}` (전체 경로 노출 금지) |
| 잠금 충돌 | SQLITE_BUSY 시 짧은 재시도 후 `{"available": false, "reason": "catalog_busy"}` |
| 구조 검사 | 최초 접속 시 `PRAGMA table_info(...)`(read-only)로 6종 테이블·필수 컬럼 존재 대조. 불일치 → `{"available": false, "reason": "schema_mismatch", "missing": [...]}` — **오표시 대신 빈 화면** 원칙 |

## 3. 공통 응답 규약 (기존 대시보드 관례 승계)

승계 원천: `ai_strategy_loop/dashboard/research_api.py`·`research_records.py`(wt-dev, read-only 참고 — soft error `available/reason`, 목록 `count` 관례). 계획 §4가 언급한 "`alpha_api.py`"는 백로그 A10 단계의 가칭이며 **실존 파일은 `research_api.py`**다(wt-dev 워킹트리·`loop/process-research-pipeline` 브랜치 양쪽 실측 — alpha_api.py는 어느 브랜치에도 없음). 신규 라우터 모듈명·기존 라우터 재사용 여부는 P4 결정(§8-6)이고, 본 계약은 **경로·파라미터·페이로드만** 봉인한다.

### 3.1 전송·엔벨로프

- 전부 **GET + 쿼리 파라미터**, 응답 UTF-8 JSON. 도메인 오류도 HTTP 200(soft error). HTTP 5xx는 코드 결함일 때만.
- 공통 필드:

```json
{
  "available": true,
  "contract_version": "rdc-1",
  "catalog": {"db_mtime_utc": "2026-07-12T12:34:56+00:00", "structure_ok": true},
  "items": [],
  "count": 0
}
```

- `catalog.db_mtime_utc`: 뷰어가 DB **파일 stat**(메타데이터 조회 — 수치 재계산 아님)로 취득한 빌드 식별자 대용. 카탈로그에는 현재 빌드 메타 테이블이 없으므로(§8-1) 파일 mtime이 캐시 키다.
- 목록형은 `items`+`count`, 단건형은 `item`. 정렬 고정: assets=`asset_id` / judgments=`rowid`(빌더 적재 순서 = 판정 체인 순서) / cells=`cell_id` / clauses=`clause_num`.

### 3.2 오류 규약 (reason 코드 표준 — snake_case)

| reason | 의미 | 부가 필드 |
|---|---|---|
| `catalog_not_configured` | 설정 키 미설정 | — |
| `catalog_not_found` | 설정 경로에 파일 없음 | `path_hint` |
| `catalog_open_error` | 열기/포맷 오류 | — |
| `catalog_busy` | SQLITE_BUSY 재시도 소진 | — |
| `schema_mismatch` | §2 구조 검사 실패 | `missing[]` |
| `invalid_param` | 파라미터 검증 실패 | `param`, (열거형이면) `allowed[]` |

- 형태: `{"available": false, "reason": "...", ...}` — `items` 생략.
- 시스템 경계 검증: 모든 파라미터는 화이트리스트/타입 검증 후 **파라미터화된 쿼리로만** 바인딩(SQL 인젝션 차단). 자유 문자열(`q`)은 LIKE 이스케이프 필수.

### 3.3 빈 결과 규약

**빈 결과는 오류가 아니다**: `{"available": true, "items": [], "count": 0}`. 유효한 필터에 결과가 없을 때 사용한다(예: 존재하지 않는 `kind` 값 — kind는 레지스트리 자유 어휘이므로 열거 검증 대신 빈 결과로 처리). V4 뷰의 "사전 집계 없음" 안내가 이 상태에서 나온다 — 서버가 즉석 계산으로 메꾸지 않는다.

### 3.4 버저닝 규약

| 대상 | 규칙 |
|---|---|
| 계약(`contract_version`) | `rdc-<major>` (+필요 시 `.<minor>`). 필드 **추가**=minor, 의미 변경·이름 변경·삭제=major. major 변경은 본 문서 개정+메인 세션 승인 필수 |
| 카탈로그 구조 | 버전 문자열이 아직 없으므로 **구조 검사**(§2)가 호환성 게이트다. P0에 빌드 메타 테이블이 도입되면(§8-1) 버전 문자열 대조로 승격 |
| 수치 불변성 | `verdict`·핵심 수치·딱지는 재빌드에도 원문 보존(judgments는 확정 판정·번복 금지 카드 — schema.py 주석). 정정은 카탈로그 재빌드+영수증으로만 |
| 캐시 | 클라이언트는 `catalog.db_mtime_utc` 단위 캐시. 값 변경 시 전면 무효화 |

## 4. 엔드포인트 4종 (전부 카탈로그 SELECT-only)

### 4.1 `GET /research/assets` — 자산 레지스트리

목적: 계획 §1 "자산 관계 지도"의 기계가독본(현 27행 — 은행 2·지도 DB 3·판정 json·원장·B1 산출물·카탈로그 자신 등). 무엇이 어디 있고, 어떤 커밋·봉인 문서가 만들었고, 어떤 딱지가 붙었는지.

| 파라미터 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `kind` | str(선택) | 전체 | 문자열 정확 일치. 어휘는 레지스트리 정본(예: `bank_parquet`·`map_db`·`judgment_json`·`ledger_jsonl`·`figure_set`·`catalog_db` 등) — 미존재 값은 빈 결과 |
| `q` | str(선택) | — | `asset_id`·`path`·`summary` 부분일치(LIKE) |
| `exists` | 0/1(선택) | 전체 | `exists_on_disk` 필터(유실 자산 점검용) |
| `limit`/`offset` | int | 500/0 | limit 최대 5000 |

SELECT 매핑: `SELECT * FROM assets [WHERE ...] ORDER BY asset_id LIMIT ? OFFSET ?`

응답 item = `assets` 컬럼 그대로: `asset_id, kind, path, produced_commit, seal_doc, window, status_tag, regen_cmd, summary, exists_on_disk, sha256, size_bytes, mtime_utc`

예시 payload (실측 레지스트리 행 — 출구 은행):

```json
{
  "available": true, "contract_version": "rdc-1",
  "catalog": {"db_mtime_utc": "2026-07-12T12:34:56+00:00", "structure_ok": true},
  "items": [{
    "asset_id": "onset_l3_bank_parquet",
    "kind": "bank_parquet",
    "path": "docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet",
    "produced_commit": "7171a561",
    "seal_doc": "plans/2026-07-12_d1_clause_ablation_preregistration.md(56564cba)",
    "window": "2022-03-23~2023-12-31(발견 가용)",
    "status_tag": "RR8_12 출구 조건부·bit-identical 검증(Jul-11 npz 일치)",
    "regen_cmd": "전용 CLI 없음 — alpha_lab/clause_lab(bank.py) 경로를 D1 사전등록(56564cba) 절차로 재실행, d1_clause_ablation_summary.json consolidate 절 참조",
    "summary": "출구 은행: 온셋 86.3만 행, L3=RR8_12 출구 net%p 라벨. D5/O-3/2절 교호작용의 공용 입력",
    "exists_on_disk": 1,
    "sha256": "…(64 hex — 빌더가 기록)…",
    "size_bytes": 12345678,
    "mtime_utc": "2026-07-12T10:38:00+00:00"
  }],
  "count": 1
}
```

주의: `status_tag`는 **단일 TEXT**(구분자 `·`)이며 뷰는 원문 그대로 표기한다(분해·재조합 금지). `produced_commit`이 null인 행은 "커밋 체인 문서에 명시 없음 또는 메인 세션 커밋 대기"(빌더는 git 미호출 — 영수증 note).

### 4.2 `GET /research/judgments` — 판정 카드 (+원장 행 동봉)

목적: V1 파이프라인 보드의 단일 원천. 현 7계열(빌더 `_JUDGMENT_SPECS` 정본): `S-트랙 칸-조준(V2-C)`·`O-1G 시초 갭 조합표`·`D1 절-단위 분해`·`D5-R 조건부 청산 triage`·`W5 RR8 3형제 병합`·`min·D9 프로브`·`B1 감독형 이관 엔진 A/B`.

| 파라미터 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `series` | str(선택) | 전체 | PK 정확 일치(위 7계열 문자열) |
| `q` | str(선택) | — | `series`·`verdict` 부분일치 |
| `include_ledger` | 0/1 | 0 | 1이면 카드별 연결 원장 행을 `ledger[]`로 동봉 |
| `limit`/`offset` | int | 200/0 | — |

SELECT 매핑: `SELECT * FROM judgments [WHERE ...] ORDER BY rowid` + (`include_ledger=1`) `SELECT * FROM ledger_mirror WHERE row_num IN (<ledger_rows 역직렬화 값>) ORDER BY row_num`. 조인은 행 첨부이지 수치 연산이 아니다.

응답 item: `series, verdict, key_metrics(객체 — key_metrics_json 역직렬화), ledger_rows(정수 배열 — CSV TEXT 역직렬화), n_ledger_rows, report_path, source_path, produced_commit, ga_path_flag, note` (+선택 `ledger[]` = `row_num, ts, series, window, trial_type, target, result, session` — `raw_json` 원문 포함).

`verdict`는 **열거형이 아니라 한국어 원문 TEXT**다(예: `"양성 — 압력 절 5종 load-bearing·역생산 6절(RR8_12 계보·원-임계 이식 금지)"`). 결과 칩 분류는 뷰의 고정 매핑표가 수행한다(P3-2 §2) — 서버는 분류하지 않는다.

예시 payload (실측 — D1 카드, key_metrics 일부 발췌):

```json
{
  "available": true, "contract_version": "rdc-1",
  "catalog": {"db_mtime_utc": "2026-07-12T12:34:56+00:00", "structure_ok": true},
  "items": [{
    "series": "D1 절-단위 분해",
    "verdict": "양성 — 압력 절 5종 load-bearing·역생산 6절(RR8_12 계보·원-임계 이식 금지)",
    "key_metrics": {
      "load_bearing_nums": [1, 4, 10, 37, 38],
      "counter_productive_nums": [5, 15, 16, 17, 29, 31],
      "weak_signal_nums": [2, 11, 13, 14, 23],
      "inconclusive_nums": [22, 25, 32, 36],
      "fdr_denominator": 34, "fdr_q": 0.1
    },
    "ledger_rows": [12, 13, 14, 15],
    "n_ledger_rows": 38,
    "report_path": "d1_clause_ablation_report.md",
    "source_path": "d1_clause_ablation_summary.json",
    "produced_commit": "7171a561",
    "ga_path_flag": 0,
    "note": null
  }],
  "count": 1
}
```

(예시의 `ledger_rows`는 앞 4행만 발췌 — 실측은 12~49의 38행. `report_path`·`source_path`는 run 디렉토리 상대 경로가 정본이며 참조 문자열이다.)

주의 필드: `ga_path_flag=1`은 "GA/최적화 경로 산출물 — 엔진 dict 공유 버그 미수정 상태 해석 주의"(계획 §5-4; 현 7계열 전부 0 — 경고 그릇). judgments 테이블 자체가 **확정 판정(번복 금지) 카드**다(schema.py 주석) — V1 잠금 표시의 근거.

### 4.3 `GET /research/cells` — 지도 셀 통합 뷰

목적: V2 함정 지도 히트맵·V4 출구 은행 조회의 단일 원천. 파티션 union(실측 1,104행): `sv1_l0`(288)·`sv1_l1`(288)·`v2a_full`(192)·`v2a_pilot`(192)·`o1g`(144 = 갭 6×시총 3×진입창 2×출구 4). **`label_tag` 딱지 NOT NULL**(딱지 없는 셀은 적재 자체가 금지 — schema.py).

| 파라미터 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `source` | str(**필수**) | — | 파티션. 허용값은 `SELECT DISTINCT source FROM cells ORDER BY source`(SELECT-only 동적 검증). 누락/미존재 → `invalid_param` + `allowed[]`(실측 목록 — P2 은행 일반화로 파티션이 늘면 자동 확장) |
| `label_kind` | str(선택) | 전체 | `h300`(sv1 고정)·`h300/l3`(v2a)·`h60/h120/h300/l3`(o1g — exit와 동일값) |
| `axis_set` | str(선택) | 전체 | sv1/v2a 전용. 실측 DISTINCT = `time_ud`·`time_mc_ud`(`time_mc_ud` 파티션은 시총×등락율 3축 좌표를 동시 보유) |
| `time_b`·`updown_q`·`mktcap_b`·`gap_b`·`win` | int(선택) | 전체 | 축 좌표 필터. 해당 파티션에 없는 축을 지정하면 빈 결과(축 유효성은 데이터가 판정) |
| `limit`/`offset` | int | 2000/0 | 전량 조회 허용 규모 |

SELECT 매핑: `SELECT * FROM cells WHERE source=? [AND ...] ORDER BY cell_id`

`insufficient` 셀 제외 파라미터는 **의도적으로 없다** — 데이터는 항상 전량 반환하고 회색 마스킹은 뷰(P3-2 §1.1 R1)가 수행한다(서버가 셀을 숨기면 "표본 부족" 사실 자체가 사라진다).

응답 item = `cells` 컬럼 그대로 + `extra`(= `extra_json` 역직렬화, null 가능): `cell_id, source, source_path, label_kind, label_tag, axis_set, map_type, time_label, time_b, updown_q, mktcap_b, gap_b, gap_label, win, win_label, exit_kind, h, n, n_candidates, censor_rate, exclusion_rate, insufficient, mean_net, median_net, q25_net, q75_net, p_net_ge0, p_net_ge1, ci_low, ci_high, winrate, payoff, mfe_mean, mae_mean, year2022_mean, year2022_sign, year2023_mean, year2023_sign, extra`

**단위 계약(혼동 주의)**: `cells`의 `*_net`·`ci_*`·`mfe_mean`·`mae_mean`은 **소수 비율**(실측 `mean_net=-0.010445` = −1.04%). `clauses`의 `*_pp`는 **%p 숫자**(`delta_pp=0.133951` = +0.134%p). 서버는 환산하지 않고, 표시 환산(×100)과 단위 라벨은 뷰 규칙(P3-2 §1.3)이 책임진다.

**파티션별 필드 채움 실측(로더 정본)**: sv1·o1g는 연도 값이 전용 연도 컬럼(`year2022_mean`·`year2022_sign` 등)으로 채워진다(o1g는 원천 필드명 `mean_net_2022`/`year_sign_2022` 계열을 로더가 매핑 — 검증 지적 반영 정정). v2a는 연도·MFE/MAE 없음(null). o1g의 `p_one_sided`·`mktcap_label`·`year_same_sign_pos`는 **`extra`로 들어간다**(역직렬화 표시 — 재계산 아님).

예시 payload (실측 — O-1G 첫 셀, 적재 후 형태):

```json
{
  "available": true, "contract_version": "rdc-1",
  "catalog": {"db_mtime_utc": "2026-07-12T12:34:56+00:00", "structure_ok": true},
  "items": [{
    "cell_id": 961, "source": "o1g", "source_path": "o1g/o1g_grid_summary.json",
    "label_kind": "h60", "label_tag": "시초 함정 지도·O-3 null 기준선·자동 veto 금지",
    "axis_set": null, "map_type": null,
    "time_label": null, "time_b": null, "updown_q": null,
    "mktcap_b": 0, "gap_b": 0, "gap_label": "lt0",
    "win": 0, "win_label": "0900-0904", "exit_kind": "h60", "h": null,
    "n": 13201, "n_candidates": 13943,
    "censor_rate": 0.0, "exclusion_rate": 0.0532, "insufficient": 0,
    "mean_net": -0.010445, "median_net": -0.011242,
    "q25_net": -0.018928, "q75_net": -0.0023,
    "p_net_ge0": 0.2121, "p_net_ge1": 0.0946,
    "ci_low": -0.012246, "ci_high": -0.008459,
    "winrate": null, "payoff": null,
    "mfe_mean": -0.000642, "mae_mean": -0.026465,
    "year2022_mean": -0.009515, "year2022_sign": -1,
    "year2023_mean": -0.010884, "year2023_sign": -1,
    "extra": {"mktcap_label": "lt1000", "p_one_sided": 1.0,
              "year_same_sign_pos": false}
  }],
  "count": 1
}
```

> **예시 표기 규약**: 본 문서의 예시 payload 수치는 가독을 위한 소수 자리 축약이고(예: `exclusion_rate` 0.0532 ← 실측 0.053216667862…), `size_bytes`·`mtime`·`db_mtime_utc`류는 자리표시자다. §1-3 "서버 반올림 금지"는 **API 실응답** 기준이며 예시 문서에는 적용되지 않는다 — 구현 검수는 §7-4(카탈로그 원문 바이트 대조)로 한다.

`label_tag` 실측 어휘 4종(로더 정본 — 뷰 워터마크의 원문): `"함정 설명 전용(S-v1 칸-조준 kill-2)·자동 veto 금지"` / `"함정 설명 전용(V2-C KILL 0/2)·자동 veto 금지"` / `"함정 설명 전용·V2-B 파일럿 참고"` / `"시초 함정 지도·O-3 null 기준선·자동 veto 금지"`.

### 4.4 `GET /research/clauses` — D1 절 카드

목적: V3 절 실험실의 단일 원천. D1 절별 전 수치(Δ·CI·MDE·분류) + W5 어휘 유형(`w5_category`).

| 파라미터 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `classification` | str(선택) | 전체 | 실측 어휘: `load_bearing`(5)·`counter_productive`(6)·`weak_signal`(5)·`inconclusive`(4)·`none`(18 — 원천 문자열 그대로 적재, 판정 비대상 절) |
| `family` | str(선택) | 전체 | 절 가문 정확 일치(예: `초당순매수금액`) |
| `w5_category` | str(선택) | 전체 | `cap_price`·`surge_value`·`change_band`·`time_gate`·`quote_qty`·`vi_round`·`exec_strength`·`breakout_ma`·`other` |
| `clause_num` | int(선택) | — | 단건 조회(`item` 반환) |

SELECT 매핑: `SELECT * FROM clauses [WHERE ...] ORDER BY clause_num`

응답 item = `clauses` 컬럼 + 역직렬화: `clause_num, text, family, w5_category, tier, n_sat, n_unsat, delta_pp, ci_low_pp, ci_high_pp, mde_pp, p_one_sided, p_two_sided, both_year_positive, both_year_negative, floor_pass, fdr_survive, classification, year_delta(객체), extra(객체 — polarity_note·mean_sat_pp·mean_unsat_pp·year_counts·n_boot·seed 등)`

예시 payload (실측 — 절 #1):

```json
{
  "available": true, "contract_version": "rdc-1",
  "catalog": {"db_mtime_utc": "2026-07-12T12:34:56+00:00", "structure_ok": true},
  "items": [{
    "clause_num": 1, "text": "1 < 초당순매수금액 < 1000",
    "family": "초당순매수금액", "w5_category": "quote_qty", "tier": "M-namespace",
    "n_sat": 373112, "n_unsat": 489820,
    "delta_pp": 0.133951, "ci_low_pp": 0.125539, "ci_high_pp": 0.1434,
    "mde_pp": 0.012767, "p_one_sided": 0.0, "p_two_sided": 0.0,
    "both_year_positive": 1, "both_year_negative": 0,
    "floor_pass": 1, "fdr_survive": 1,
    "classification": "load_bearing",
    "year_delta": {"2022": {"delta_pp": 0.1215, "sign": 1, "n_sat": 156845, "n_unsat": 206442},
                    "2023": {"delta_pp": 0.1429, "sign": 1, "n_sat": 216267, "n_unsat": 283378}},
    "extra": {"num": 1, "cat": "quote_qty", "polarity_note": "not(P)→만족=P",
              "mean_sat_pp": -0.931762, "mean_unsat_pp": -1.065713, "n_boot": 400, "seed": 20260712}
  }],
  "count": 1
}
```

절 수 정합(정본): 봉인 상한 39절 중 `#39`는 `#15`와 순수 중복으로 병합돼 **카탈로그에 행이 없다**(측정 38행 — 빌더 영수증 note가 "미포함 절 번호 [39]"를 기록). **FDR 분모는 34**(= 측정 38 − inconclusive 4 분모 제외, `d1_clause_ablation_summary.json` judgment.fdr_denominator=34 실측). 화면 표기는 "39절 중 측정 38절(#39=#15 순수 중복 병합) · FDR 분모 34"로 통일한다. 압력 절 5종 Δ 실측 범위 = +0.134~+0.198%p(#38 최대 0.197531). **W5 유형 분포(2,278절 9범주)는 현 카탈로그에 원천 테이블이 없어 본 엔드포인트가 제공하지 않는다** — §8-3 확장 제안 참조(그 전까지 V3 분포 패널은 "데이터 없음").

## 5. 카탈로그 정본 스키마 참조 (schema.py DDL 요약 — 재기술 아님)

| 테이블 | PK | 실측 행수 | 원천 | 4엔드포인트 노출 |
|---|---|---:|---|---|
| `assets` | asset_id | 27 | `assets_registry.py`(계획 §1 표) + 실물 stat/sha256 | /research/assets |
| `judgments` | series | 7 | 판정 json 7계열(빌더 `_JUDGMENT_SPECS`) | /research/judgments |
| `clauses` | clause_num | 38 | `d1_clause_ablation_summary.json` per_clause | /research/clauses |
| `strategies` | name | W2 union+B1 | `w2_strategy_inventory.json` 4섹션 + B1 등록 영수증 | **미노출**(§8-7 — 랭킹 뷰는 후속) |
| `cells` | cell_id | 1,104 | stats_map DB 3종 + o1g json | /research/cells |
| `ledger_mirror` | row_num | 53+ | `n_trials_ledger.jsonl` 원문(raw_json 보존) | /research/judgments의 `ledger[]` |

컬럼 정의는 `alpha_lab/catalog/schema.py`가 정본이며 본 문서는 §4의 응답 스키마로만 재서술한다(이중 정의 금지). `strategies`의 인간 전당 행은 `status_tag="외부 벤치마크·원문 없음 확정·절 파싱 금지(전당 목표선)"`가 이미 붙어 있다 — 노출 시에도 이 딱지 강제 표기가 전제다.

## 6. 예약(비봉인) — V5 B1 실전 채점판의 데이터

V5는 "(B1 운용 시작 후) 실전 기록 테이블"을 쓴다(계획 §4). 운용 개시 전 + `schema.py`가 "테이블 6종 외에는 만들지 않는다"고 봉인했으므로, **본 계약의 4엔드포인트에 포함하지 않고 예약만** 한다. 그릇의 위치(카탈로그 개정 vs 별도 live DB)는 P0 개정 판단 + 사용자 go 사항(§8-4).

- 예약 테이블 `b1_live_trades`(절차서 §4 기록 양식 1:1): `trade_date, code, buy_fill, buy_tick2_assumed, buy_resid, sell_fill, sell_tick2_assumed, sell_resid, exit_reason, hold_secs, max_ret_at_cut, ret_at_cut, counterfactual_note` — 뒤 3필드는 절차서 §5(저활력 절단 스냅샷·반사실).
- 예약 테이블 `b1_live_days`: `trade_date, day_pnl_krw, n_trades, cum_pnl_krw, day_killswitch_used_pct, cum_killswitch_used_pct, notes` — 킬스위치 분모(스케일MDD = 873,720 × C/5,000,000)는 자본 `C` 확정(U-4) 후 봉인.
- 예약 엔드포인트 `/research/b1_live`(가칭). 채점 판정값(실현율 등 비율)은 **기록·집계 파이프라인**이 계산해 적재하고 뷰는 표시만(1원칙 유지).

## 7. 계약 준수 수용 기준 (P4 구현 검수 시 그대로 사용)

1. 4엔드포인트 응답이 §3.1 엔벨로프 필수 필드를 포함하고, 오류가 §3.2 코드 표만 사용한다.
2. 구현 코드에 수치 연산(산술·집계 SQL)이 없다(허용: §1-2 역직렬화). sqlite trace에서 SELECT/PRAGMA(read-only) 외 문장 0건.
3. 카탈로그 미설정/부재/구조 불일치 3상태가 각각 규약대로 응답한다(수동 3케이스).
4. `verdict`·`status_tag`·`label_tag`가 카탈로그 원문과 바이트 동일(무작위 3건 대조).
5. 빈 결과가 `available:true`로 반환된다(존재하지 않는 family 필터 등).
6. wt-dev 코드에 wt-alpha 경로 문자열·심링크·모듈 임포트가 없다(§2 금지 3종 grep).
7. `/research/cells`의 `allowed[]`가 카탈로그 실측 DISTINCT와 일치한다(파티션 증설 시 코드 무수정 확장 확인).

## 8. 확장 제안·미결 항목표 (메인 세션/P0/P4 결정 필요)

| # | 항목 | 현 상태(정본) | 제안/결정 주체 |
|---|---|---|---|
| 1 | 빌드 메타(스키마 버전·build_id) 테이블 | 없음 — 영수증은 DB 밖 json. 뷰어는 파일 mtime+구조 검사로 대체(§2·§3.4) | P0 개정 제안: `catalog_meta` 1행(단, schema.py "6종 외 금지" 봉인 해제 필요) |
| 2 | 진행 중 연구 상태(sealed/measuring) | judgments는 확정 판정 전용 — 진행 중 카드 없음 | V1 "진행 중" 레인은 확장 전 미구현(안내만 — P3-2 §2). 제안: 별도 원천 또는 judgments 개정 |
| 3 | W5 어휘 유형 분포(2,278절 9범주) | 카탈로그에 원천 없음(W5 카드 key_metrics는 §3 중복 조사만) | P0 제안: W5 카드 `key_metrics_json`에 `category_frequency` 추가 적재 — 그 전까지 V3 분포 패널 "데이터 없음" |
| 4 | V5 실전 기록 그릇(§6) | 미존재(운용 미개시 + 6종 봉인) | 카탈로그 개정 vs 별도 live DB — 사용자 go 시 결정 |
| 5 | 경로 설정 키 이름(`STOM_RESEARCH_ASSETS_DB`) | 잠정(본 계약 제안) | P4에서 확정(env 우선 원칙 유지) |
| 6 | 라우터 배치 | `alpha_api.py`는 실존하지 않음 — `research_api.py`가 관례 원천 | P4: 신규 모듈 분리 권장(기존 문서 라우트와 관심사 분리) + 기존 PR 조율 |
| 7 | `strategies` 노출(랭킹 뷰) | 테이블은 존재, 엔드포인트 없음 | 후속 계획(노출 시 human 딱지 강제 표기 전제) |
