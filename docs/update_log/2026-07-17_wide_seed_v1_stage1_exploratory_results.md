# 와이드시드V1 Stage-1 탐색 백테스트 결과 기록

- 날짜: 2026-07-17
- 브랜치: `research/condition-history-tree-seeds-20260715`
- 승인 계획: `stage-09-final.md` (SHA-256 `a41097790e2e469c41b94ce515e7d026be03ddca2377ef732a06a824aae5c8cd`) G005 범위
- **결과 역할: `exploratory_full_history` — 탐색/설명용만. OOS·독립 검증·승격·export/live 근거가 아니다.**

## 1. 실행 요약 (sealed 2-trial)

| 레인 | 전략쌍 | 기간(전체 가용) | 유니버스 | 메커니즘 | 거래수 | 거래종목수 | 소요 |
|---|---|---|---|---|---:|---:|---:|
| tick | WSEED_V1_Tick_B/S | 2022-03-23~2026-02-27 (952일) | 전체 | warm-session 32엔진 | 178,247 | 2,314(종목명) | 1,198초 |
| min | WSEED_V1_Min_B/S | 2025-04-07~2026-02-27 | 전체 | warm-session 32엔진 | 26,198 | 1,067(종목명) | 103초 |

- 1차 cold-subprocess(4엔진) 시도는 기존 문서화된 full-universe 로딩 병목(`engine_data_response_timeout`)으로 실패 — `docs/research/condition_research/pilot_logs/2026-04-22_cli_child_runtime_db_override_smoke.md` 재현. warm-session 경로(post-q4 캠페인과 동일 메커니즘)로 해소. 실패/성공 전 과정은 `artifacts/ultragoal-condtree/g004_tested_cell_ledger.jsonl`에 append-only 기록.
- 시세 DB는 `wt-dev/_database` 읽기 전용 참조(env 오버라이드), 쓰기 DB는 전부 워크트리/격리 경로 — wt-dev 무변경 검증 완료.
- min 레인 `매수시간`은 12자리(YYYYMMDDHHMM) 형식으로, 셀 분해기의 14자리 가정 오파싱(82% unassigned)을 적발·수정 후 재분해 — 최종 양 레인 모두 unassigned 0, 파리티 일치.

## 2. 12셀 분해 결과 (매수시간 × 시가총액)

전체 지표는 History 대시보드(캠페인 `wide_seed_v1_stage1_tick` / `wide_seed_v1_stage1_min`)와 `artifacts/ultragoal-condtree/g005_cell_summary.json` 참조. 요약:

### Tick (총 순손익 -40.8억원, 승률 ~31~34%)
| 시간창 | 시총군 | 거래수 | 종목수 | 순손익(원) | 총손실(원) | 손실거래수 | 승률 |
|---|---|---:|---:|---:|---:|---:|---:|
| 09:00~05 | <3000억 | 20,501 | 1,694 | -552,104,488 | -1,477,671,026 | 13,537 | 33.8% |
| 09:00~05 | ≥1조 | 21,306 | 427 | -477,281,406 | -888,313,594 | 14,418 | 32.0% |
| 09:10~20 | <3000억 | 28,059 | 1,648 | -773,284,986 | -1,529,772,326 | 19,296 | 31.0% |
| 09:10~20 | ≥1조 | 31,821 | 420 | -564,866,178 | -928,522,376 | 22,376 | 29.2% |
| (전체 12셀) | | 178,247 | 2,314 | 약 -40.8억 | | | |

### Min (총 순손익 -7.6억원, 승률 ~25~41%)
| 시간창 | 시총군 | 거래수 | 종목수 | 순손익(원) | 승률 |
|---|---|---:|---:|---:|---:|
| 09:00~30 | 6000~1조 | 71 | 45 | -176,386 | 40.8% |
| 09:00~30 | ≥1조 | 458 | 143 | -4,501,834 | 41.5% |
| 10:00~14:00 | <3000억 | 6,178 | 622 | -332,716,433 | 26.9% |
| 10:00~14:00 | ≥1조 | 9,687 | 254 | -161,701,574 | 30.3% |

### 탐색 관찰 (승격 근거 아님)
- 예상대로 광역 시드는 전 셀 순손실 — 목적은 수익이 아니라 **손실·거래폭 지도** 확보.
- 상대적으로 min 장초 30분(09:00~09:30) × 중대형 셀의 승률이 높고 손실이 얕음; tick·min 공통으로 늦은 시간창일수록 승률 하락.
- 소형(<3000억) 셀이 양 레인 모두 손실 집중도가 가장 큼 — 후속 시드 가공 시 갭/등락률 세분화 우선 후보.
- 레인 간 기간 불일치(`non_common_history`) — 직접 비교 금지.

## 3. History 수록·재현성

- 발행: `cli.research_history_projection.publish_condition_history` 단일 발행기 → `.omo/evidence/tmap-walkforward/wide_seed_v1_stage1_{tick,min}_condition_history_v1.json` (레인당 12셀 + overall = 13 condition/evaluation).
- 대시보드: 조건식 AI → 히스토리 → "조건식 History (v4.1)" 패널에서 트리/테이블 조회(`campaign:wide_seed_v1_stage1_*`).
- CSV sha256, 경계/청산 영수증 sha, TrialSpec 해시가 결과에 바인딩됨. per-trade CSV(비추적)는 `backtest/csv/stock_bt_WSEED_V1_*_2026071708*.csv`.

## 4. 후속

- 유망 셀(예: min 장초 중대형)의 시가갭 5구간·등락률 세분화 시드는 **별도 승인** 후 진행.
- 승격 판단은 새 disjoint frozen OOS/WF 계획 필요(기존 경계 불변).
- 부모 브랜치 반영은 검증 완료분만 cherry-pick.
