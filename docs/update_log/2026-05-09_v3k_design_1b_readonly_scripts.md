# V3K-DESIGN-1B read-only schema 검증 script 초안

작성일: 2026-05-09 KST
대상 root lane: `STOM_Version_2`
최종 구현 lane: `STOM_Version_2U_C`
상위 문서: `docs/update_log/2026-05-09_v3k_design_1_db_learning_design.md`
상위 spec: `docs/superpowers/specs/2026-05-09-v3k-db-learning-migration-spec.md`
작성 성격: script 초안 + 문서, runtime 연결 0건, DB 생성/수정 0건

## 0. 한 줄 결론

`V3K-DESIGN-1B`는 V3K DB/학습 데이터 설계를 실제 DB에 적용하기 전, **읽기 전용으로만 schema 차이와 shadow manifest를 검증하는 발판**이다.

이번 단계에서 추가한 script는 다음 3개다.

```text
scripts/diff_v3_vs_2uc_db_schema.py
scripts/init_v3k_shadow_db.py --dry-run
scripts/v3k_db_health.py --read-only
```

이 script들은 runtime 코드에 연결되지 않으며, 기본 출력은 `.omx/reports/` 아래 JSON report뿐이다.

## 1. script별 책임

| Script | 목적 | 허용 write | 금지 |
| --- | --- | --- | --- |
| `scripts/diff_v3_vs_2uc_db_schema.py` | V3/2U_C core DB와 V3 learning DB manifest를 read-only 비교 | `.omx/reports/v3k-db-schema-diff.json` | DB 생성/수정 |
| `scripts/init_v3k_shadow_db.py --dry-run` | shadow DB에 생성할 learning/meta DB manifest와 SQL 초안을 JSON으로 출력 | `.omx/reports/v3k-shadow-manifest.json` | `_database_v3k_shadow/` 생성 |
| `scripts/v3k_db_health.py --read-only` | shadow DB가 존재할 때 read-only healthcheck를 수행하고, 없으면 missing 상태를 report | `.omx/reports/v3k-db-health.json` | DB 생성/수정 |

## 2. 구현 원칙

```text
- 모든 SQLite 연결은 read-only URI (`mode=ro`)를 사용한다.
- 출력 파일 경로는 repo root의 `.omx/reports/` 하위로 제한한다.
- `_database`, `_database_v3k_shadow`, `backup`, `*.db`를 생성하거나 수정하지 않는다.
- `init_v3k_shadow_db.py`는 `--dry-run`을 필수 인자로 요구한다.
- `v3k_db_health.py`는 `--read-only`를 필수 인자로 요구한다.
```

## 3. 확인된 V3K learning DB manifest

`init_v3k_shadow_db.py --dry-run` manifest에는 다음 DB가 포함된다.

| DB | 근거 V3 analyzer | 주요 table |
| --- | --- | --- |
| `pattern_analysis.db` | `strategy/analyzer_candle_pattern.py` | `pattern_setting`, `{strategy_gubun}_pattern_score` |
| `volume_spike.db` | `strategy/analyzer_volume_spike.py` | `spike_setting`, `{strategy_gubun}_volume_spike_{tick|min}` |
| `volume_profile.db` | `strategy/analyzer_volume_profile.py` | `volume_setting`, `{strategy_gubun}_volume_score_{tick|min}` |
| `volatility_pattern.db` | `strategy/analyzer_volatility_pattern.py` | `volatility_setting`, `{strategy_gubun}_volatility_pattern_{tick|min}` |
| `volatility_stop_take.db` | `strategy/analyzer_volatility_stop_take.py` | `volatility_stop_take_setting`, `{strategy_gubun}_volatility_{tick|min}` |
| `v3k_meta.db` | V3K 관리 DB 후보 | `v3k_feature_flags`, `v3k_schema_manifest` |
| `v3k_code_meta.db` | listed-shares/code mapping 후보 | `v3k_listed_shares` |

## 4. 실행한 검증 명령

```powershell
python -m py_compile `
  scripts/diff_v3_vs_2uc_db_schema.py `
  scripts/init_v3k_shadow_db.py `
  scripts/v3k_db_health.py

python scripts/diff_v3_vs_2uc_db_schema.py `
  --output .omx/reports/v3k-db-schema-diff.json

python scripts/init_v3k_shadow_db.py `
  --dry-run `
  --manifest .omx/reports/v3k-shadow-manifest.json

python scripts/v3k_db_health.py `
  --read-only `
  --output .omx/reports/v3k-db-health.json
```

검증 결과:

```text
py_compile 통과
schema diff report 생성: .omx/reports/v3k-db-schema-diff.json
shadow manifest 생성: .omx/reports/v3k-shadow-manifest.json
health report 생성: .omx/reports/v3k-db-health.json
health status: shadow dir/DB 없음 (DESIGN-1B에서는 정상 상태)
```

`.omx/reports/`는 runtime report 영역이며 git commit 대상이 아니다.

## 5. 금지 산출물 guard

다음 항목은 생성/수정되지 않았다.

```text
_database/
_database_v3k_shadow/
backup/
_log/
*.db
backtest/graph/
```

## 6. DESIGN-1B 종료 판정

| 조건 | 상태 |
| --- | --- |
| read-only script 3종 추가 | 완료 |
| runtime 연결 없음 | 완료 |
| DB 파일 생성/수정 없음 | 완료 |
| `.omx/reports/` 외 output 없음 | 완료 |
| py_compile 통과 | 완료 |
| `git diff --check` 대상 | commit 전 검증 |

## 7. 다음 단계

다음 단계는 `V3K-DESIGN-2`이다.

목표:

```text
- analyzer별 input/output contract 작성
- Kiwoom tick/min/candle/snapshot data shape mapping 작성
- V3 analyzer를 2U_C에 이식하기 위한 adapter boundary 정의
- AnalyzerRisk dormant → runtime 후보 승격 조건 정의
- 아직 runtime 구현은 하지 않음
```

## 8. 전체 계획 progress

| 단계 | 상태 | 설명 |
| --- | --- | --- |
| 1. V3 공식 lane 도입 | 완료 | V3.18 ingress 완료 |
| 2. V3U pyd-free 전환 | 완료 | 3U parity audit 완료 |
| 3. 2U_C safe-candidate 백포트 | 완료 | BP-002A~BP-011A micro 후보 소진 |
| 4. V3 미반영 신기능 audit | 완료 | 학습/분석/DB 미반영 확인 |
| 5. V3K 목표 재정의 | 완료 | Kiwoom 유지 + V3 신기능 목적 고정 |
| 6. V3K-DESIGN-0 | 완료 | Phase 0 kickoff |
| 7. V3K-DESIGN-1 | 완료 | DB/학습 설계 |
| 8. V3K-DESIGN-1B | 완료 | 본 문서, read-only script 3종 |
| 9. V3K-DESIGN-2 | 남음 | analyzer/data contract |
| 10. V3K-IMPL backtest/realtime/UI | 남음 | 설계 승인 후 구현 |
| 11. V3K-VERIFY | 남음 | 통합 검증/승격 |

```text
전체 11단계 중 8단계 완료 = 73%
[███████░░░] 73%

현재 단계 V3K-DESIGN-1B = 100%
[██████████] 100%
```

## 9. 한 줄 결론

`V3K-DESIGN-1B`는 DB를 건드리지 않고도 V3K DB/학습 데이터 설계를 반복 검증할 수 있는 read-only 발판을 만들었으며, 다음 단계는 analyzer/data contract를 고정하는 `V3K-DESIGN-2`이다.