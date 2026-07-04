# 2026-07-04 Plan B Lattice Wrong-Profile Pause Handoff

## 1. 결론

Plan B lattice full smoke 진행은 여기서 일시 중단한다. 현재 산출된 tick 결과는
`2025-01-01~2025-03-31`, `warm 8` 설정으로 실행된 스모크 참고자료이며,
사용자 기준의 공식 생존/기각/portfolio 판단에는 사용하지 않는다.

다음 세션은 chunk08~chunk10을 이어서 실행하지 말고, 먼저 백테스트 프로파일을
전체 DB 기간 + `warm 64` 기준으로 재정의/검증해야 한다.

## 2. 중단 시점 스냅샷

| 항목 | 값 |
|---|---|
| 중단 시각 | 2026-07-04 |
| 대상 계획 | `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md` |
| 현재 단계 | Plan B P5 tick smoke 중간 점검 |
| 실행 중인 batch 프로세스 | 없음 |
| min smoke | 미시작 |
| P6 coverage/refinement/OOS/portfolio | 미시작 |
| Plan D | 미시작, 실행 금지 유지 |

## 3. 현재까지 생성된 run

| run_id | 설정 | 상태 | rows | status_counts | gate_passed | 공식 판단 사용 |
|---|---|---:|---:|---|---:|---|
| `lat_smoke_tick_full_sanitized_20260704` | tick, 2025Q1, warm 8 | `aborted_wrong_profile` | 170 | `ok=154`, `error=16` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume01` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume02` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume03` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume04` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume05` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume06` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| `lat_smoke_tick_full_sanitized_20260704_resume07` | tick, 2025Q1, warm 8 | `complete` | 12 | `ok=12` | 0 | 금지 |
| 합계 | tick, 2025Q1, warm 8 | partial | 254/288 | `ok=238`, `error=16` | 0 | 금지 |

현재 기준으로 남은 chunk는 `chunk08~chunk10`, 총 34쌍이다. 다만 이 프로파일은
사용자 기준과 다르므로 이어서 실행하지 않는다.

## 4. 왜 공식 결과로 쓰면 안 되는가

| 항목 | 현재 실행 | 사용자 기준 / 정정 |
|---|---|---|
| tick 백테스트 기간 | 2025-01-01~2025-03-31 | DB 전체 기간 |
| tick DB 실제 기간 | 일부 Q1만 사용 | 2022-03-23 09:00:00~2026-02-27 09:30:00 |
| min 백테스트 기간 | 미실행, 기존 config는 2025-05-01~2025-05-31 | DB 전체 기간 |
| min DB 실제 기간 | 미실행 | 2025-04-07 09:00~2026-02-27 15:19 |
| tick engine count | warm 8 | warm 64 |
| min engine count | 기존 config warm 16 | warm 64 |
| engine reuse 방식 | prepare 1회 후 순차 실행 | 방식은 맞음 |
| 현재 run 상태 | partial + wrong profile | 공식 실험 제외 |

검증 명령은 원천 DB를 read-only로 열어 각 종목 테이블의 날짜형 `index` 범위를
집계했다. 단순 최소값에는 일부 비시계열 값(`20`)이 있어 tick 14자리,
min 12자리 이상만 필터링했다.

## 5. 산출물 위치

| 산출물 | 경로 | 용도 |
|---|---|---|
| 부분 export | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_results_tick_full_sanitized_20260704_partial_aborted.json` | 참고자료, 공식 판단 금지 |
| chunk manifest | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_remaining_chunk_manifest_20260704.json` | 중단 위치 확인용, 재개 금지 |
| chunk logs | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_tick_full_sanitized_20260704_resume01.log` ~ `resume07.log` | 실행 정상성 참고 |
| original log | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_tick_full_sanitized_20260704.log` | aborted run 참고 |
| pair list | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick.json` / `pairs_min.json` | sanitized lattice pair 원장 |

## 6. 현재 결과를 어떻게 해석할지

| 용도 | 판단 |
|---|---|
| sanitized 이름이 CSV/metrics를 만들 수 있는지 | 참고 가능 |
| warm engine prepare/순차 실행 방식 검증 | 참고 가능 |
| lattice 조건식 성과 판단 | 사용 금지 |
| 생존/기각/go/no_go 판단 | 사용 금지 |
| P6 refinement/OOS/portfolio 입력 | 사용 금지 |
| Plan D 입력 | 사용 금지 |

0개 gate 통과 자체는 신호일 수 있지만, 기간과 engine count가 사용자 기준과 다르므로
현재 단계에서 조건식 품질 결론으로 확정하지 않는다. 먼저 올바른 프로파일로
재실행해야 한다.

## 7. 올바른 실험 기준

### tick lattice

| 항목 | 값 |
|---|---|
| 대상 | tick lattice 288쌍 |
| DB | `_database/stock_tick_back.db` |
| 실제 DB 기간 | 2022-03-23 09:00:00~2026-02-27 09:30:00 |
| 공식 기간 | DB 전체 기간 |
| 시간 | 기존 tick 데이터 기준 09:00~09:30, 현재 canonical은 09:00~09:28 여부 재확인 필요 |
| 엔진 | warm 64 |
| 방식 | engine 64개 prepare 1회 후 288쌍 순차 실행 |
| run_id 권장 | 기존 `lat_smoke_tick_full_sanitized_20260704*` 재사용 금지, 새 이름 사용 |

### min lattice

| 항목 | 값 |
|---|---|
| 대상 | min lattice 288쌍 |
| DB | `_database/stock_min_back.db` |
| 실제 DB 기간 | 2025-04-07 09:00~2026-02-27 15:19 |
| 공식 기간 | DB 전체 기간 |
| 시간 | 09:00~15:19 |
| 엔진 | warm 64 |
| 방식 | engine 64개 prepare 1회 후 288쌍 순차 실행 |

## 8. 다음 세션 시작 순서

1. 이 문서를 먼저 읽는다.
2. `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`의 P5 상태를 확인한다.
3. `smoke_config_tick.json` / `smoke_config_min.json`을 공식 기준으로 새 파일에 복제한다.
   기존 Q1/warm8 config를 덮어쓰지 않는다.
4. 새 config에 대해 static profile receipt를 만든다.
   필수 확인: 기간, DB path, timeframe, warm engine count, start/end time, pair count.
5. 작은 preflight를 먼저 실행한다.
   권장: tick 2~4쌍, warm64 prepare 성공, CSV/metrics 생성 확인.
6. preflight가 맞으면 tick 288 공식 run을 새 `run_id`로 실행한다.
7. tick 288 완료 후에만 min 288 공식 run을 실행한다.
8. 공식 tick/min 결과가 모두 나온 뒤 P6 coverage/go/no_go/refinement로 넘어간다.

## 9. 금지 사항

- `lat_smoke_tick_full_sanitized_20260704*` 결과로 생존/기각 판단 금지.
- chunk08~chunk10 이어 실행 금지.
- min smoke 선행 실행 금지.
- OOS preregistration 없이 OOS 실행 금지.
- Plan D 실행 금지.
- DB UPDATE/DELETE 금지.
- A3/promotion/export/live/final 경로 수정 금지.
- `git add -A` 금지.
- dashboard 7파일, `.gjc`, unrelated `.omo` 잔재 스테이징 금지.

## 10. 추천 다음 명령어 초안

다음 작업은 “공식 재실행”이 아니라 “프로파일 감사 및 공식 config 생성”부터 시작한다.

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 P5-profile-audit만 진행한다.
목표는 기존 2025Q1/warm8 tick smoke 산출물을 공식 판단에서 제외하고,
tick/min lattice 공식 재실행 기준(DB 전체기간 + warm64)을 검증한 뒤
새 config와 preflight 계획만 만드는 것이다.

진행:
1. 이 핸드오프 문서를 먼저 읽는다.
2. 현재 lat_smoke_tick_full_sanitized_20260704* run들은 smoke 참고자료로만 표시한다.
3. tick/min 원천 DB 기간을 read-only로 재확인한다.
4. 공식 tick config를 새 파일로 생성한다: 전체기간 + warm64 + 09:00~09:28/09:30 정책 명시.
5. 공식 min config를 새 파일로 생성한다: 전체기간 + warm64 + 09:00~15:19.
6. pair count tick=288/min=288, sanitized name safety, DB row 존재 여부를 static gate로 확인한다.
7. 공식 full run 전 preflight 2~4쌍 계획과 예상 시간을 산출한다.

금지:
- tick chunk08~chunk10 실행 금지
- tick 288 full 실행 금지
- min 288 full 실행 금지
- P6/P7/Plan D 실행 금지
- 기존 Q1/warm8 결과로 생존/기각 판단 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
```
