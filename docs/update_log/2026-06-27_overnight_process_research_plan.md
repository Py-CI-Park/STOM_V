# Overnight Process Research Plan — 6~8h 무개입 연구

Status: research plan and operator record. This is not a production-promotion approval and does not authorize export/live wiring.

## 목적

| 항목 | 내용 |
|---|---|
| 목적 | 내일 아침 06:00까지 6~8시간 동안 사용자 개입 없이 의미 있는 조건식 연구를 진행한다. |
| 핵심 루틴 | 전체기간 백테스트 → Edge Ratio/구간/변수/청산 분석 → 조건식 개선 → 재백테스트. |
| 권장 기본 | `process-research` 중심. `fast-discovery`는 후보 발굴, `promotion-review`는 승격 전 검토 전용. |
| 엔진 수 | 2026-06-27 벤치마크 근거상 32 유지. |
| 안전 경계 | 연구 결과는 advisory이다. `production_promote`, `export`, `live`, final promotion은 별도 승인 전 차단한다. |

## 프로세스 A/B/C 정의

| 프로세스 | 코드/선택 | 목적 | 6~8h 야간 사용법 | 산출물 |
|---|---|---|---|---|
| A | `1 fast-discovery` | 새 후보를 빠르게 넓게 발굴 | 초반 60~90분만 사용. 다양한 시간대/시총/등락률 니치를 시도해 후보 풀을 만든다. | 후보 조건식, smoke/full-period 초기 점수, reject 이유 |
| B | `2 process-research` | 전체기간 중심 조건식 개선 | 야간의 주력. 후보를 전체기간으로 돌리고 Edge Ratio/segment/feature/exit 분석을 다음 세대 개선에 반영한다. | 개선 후보, 비교 성과, 분석 evidence |
| C | `3 promotion-review` | 동결 후보 승격 전 검토 | 마지막 45~60분만 사용. 운영 승격이 아니라 top 후보의 evidence health/readiness를 점검한다. | 아침 후보 shortlist, blocker, 다음 실험 제안 |

## 권장 시간 배분

| 시간대 | 프로세스 | 작업 | 성공 기준 |
|---|---|---|---|
| 00:00~00:20 | 준비 | 대시보드/health/preflight, 32 엔진 기준 확인, run-id prefix 고정 | health OK, 보호 경로 변경 없음 |
| 00:20~01:30 | A fast-discovery | 후보 다양화. 넓은 시간창·시총 티어·등락률 국면별 후보 생성 | 최소 5~10개 valid attempt 또는 명확한 reject 축적 |
| 01:30~04:45 | B process-research | 상위 후보 전체기간 반복 연구. Edge Ratio/segment/feature/exit feedback으로 개선 | 개선 후보 3개 이상 또는 실패 원인 분류 3개 이상 |
| 04:45~05:30 | C promotion-review | top 후보를 동결 후보처럼 읽기 전용 점검. export/live 없이 evidence health 확인 | shortlist, blocker, 다음날 수동 검토 포인트 |
| 05:30~06:00 | 보고 | morning report, dashboard records/workbench 확인, artifacts 정리 | 아침 보고서와 run evidence 경로 확보 |

## 추천 실행 전략

### 추천안 1 — C-focused composite plan

가장 추천한다. A/B/C를 모두 쓰되, 시간 대부분을 B에 쓴다.

| 비중 | 프로세스 | 이유 |
|---:|---|---|
| 15% | A | 새 후보 다양성을 확보한다. |
| 70% | B | 사용자의 핵심 아이디어인 전체기간 기반 연구/개선 루프다. |
| 15% | C | 아침에 볼 후보를 정리하되, 운영 반영은 하지 않는다. |

### 추천안 2 — B-only deep research

이미 후보가 충분하면 A를 건너뛰고 B만 진행한다. 후보 개선 품질은 높지만 새 니치 탐색은 줄어든다.

### 추천안 3 — A/B 대조 연구

새 방법의 우위 자체를 검증하려면 A/B 대조 스크립트로 random vs stateful 발굴을 비교한다. 다만 좋은 후보 찾기보다 방법론 검증에 가깝다.

## 실행 전 체크리스트

| 체크 | 명령/확인 | 정상 기준 |
|---|---|---|
| 대시보드 실행 | `cmd.exe /c start "" stom_dashboard.bat` | 브라우저 접속 가능 |
| Health | `http://127.0.0.1:8770/health` | `{"status":"ok","contract_version":2}` |
| 브랜치 | `git status --short --branch --untracked-files=no` | 의도치 않은 tracked 변경 없음 |
| nonrelease | `python scripts/verify_nonrelease_sync.py` | OK |
| 보호 경로 | `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json` | 출력 없음 |

## 권장 LoopConfig 골격

아래 설정은 저장용 예시다. 실제 파일명은 `artifacts/overnight-process-research-YYYYMMDD/process_b_research.json`처럼 둔다.

### A fast-discovery config 핵심

```json
{
  "provider": "gpt_auth",
  "max_generations": 8,
  "condition_discovery_preset": "fast",
  "condition_discovery_process": "fast-discovery",
  "bt_engine_mode": "warm",
  "bt_timeframe": "tick",
  "bt_scope": "universe",
  "bt_full_start": 20250101,
  "bt_full_end": 20251231,
  "bt_universe_start_time": 90000,
  "bt_universe_end_time": 92800,
  "bt_warm_engine_count": 32,
  "research_oos_mode": "disabled",
  "classification_generation_enabled": true,
  "time_cap_bucket_generation_enabled": true,
  "exec_budget_prompt_enabled": true,
  "sell_exec_budget_guard_enabled": true,
  "prompt_logging_enabled": true,
  "equity_points_enabled": true,
  "hypothesis_tracking_enabled": true
}
```

### B process-research config 핵심

```json
{
  "provider": "gpt_auth",
  "max_generations": 18,
  "condition_discovery_preset": "research",
  "condition_discovery_process": "process-research",
  "bt_engine_mode": "warm",
  "bt_timeframe": "tick",
  "bt_scope": "universe",
  "bt_full_start": 20250101,
  "bt_full_end": 20251231,
  "bt_universe_start_time": 90000,
  "bt_universe_end_time": 92800,
  "bt_warm_engine_count": 32,
  "research_oos_mode": "disabled",
  "classification_generation_enabled": true,
  "time_cap_bucket_generation_enabled": true,
  "feature_importance_feedback_enabled": true,
  "feature_importance_feedback_min_cell": 20,
  "quantile_feedback_enabled": true,
  "counterfactual_feedback_enabled": true,
  "exit_forensics_feedback_enabled": true,
  "exec_budget_prompt_enabled": true,
  "sell_exec_budget_guard_enabled": true,
  "prompt_logging_enabled": true,
  "equity_points_enabled": true,
  "hypothesis_tracking_enabled": true
}
```

### C promotion-review config 핵심

```json
{
  "provider": "gpt_auth",
  "max_generations": 3,
  "condition_discovery_preset": "promotion",
  "condition_discovery_process": "promotion-review",
  "bt_engine_mode": "warm",
  "bt_timeframe": "tick",
  "bt_scope": "universe",
  "bt_full_start": 20250101,
  "bt_full_end": 20251231,
  "bt_universe_start_time": 90000,
  "bt_universe_end_time": 92800,
  "bt_warm_engine_count": 32,
  "research_oos_mode": "promotion_only",
  "prompt_logging_enabled": true,
  "equity_points_enabled": true,
  "hypothesis_tracking_enabled": true
}
```

## 실행 명령 예시

```sh
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop.controller.loop --config-json artifacts/overnight-process-research-YYYYMMDD/process_a_fast.json
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop.controller.loop --config-json artifacts/overnight-process-research-YYYYMMDD/process_b_research.json
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop.controller.loop --config-json artifacts/overnight-process-research-YYYYMMDD/process_c_review.json
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m ai_strategy_loop.scripts.gen_morning_report --out docs/research/condition_research/auto_reports/morning_YYYYMMDD_process_research.md
```

## LLM 실패 또는 긴급 fallback

| 상황 | fallback | 이유 |
|---|---|---|
| provider 인증 실패 | 기존 후보 대상으로 Workbench/Lab 분석과 morning report만 생성 | 무개입 조건에서 인증 입력을 요구하지 않는다. |
| 생성은 되지만 백테스트 timeout 반복 | `sell_exec_budget_guard_enabled=true` 유지, 실패 후보 reject evidence로 기록 | 과비용 매도식 반복을 차단한다. |
| 백테스트 3회 연속 실패 | 새 후보 생성을 중단하고 기존 성공 후보 분석으로 전환 | 6시간을 실패 루프로 태우지 않는다. |
| 보호 경로 변경 감지 | 즉시 중단, report에 blocker 기록 | 연구가 runtime DB/log 보호 경계를 넘지 않게 한다. |
| LLM 없이 발굴만 필요 | `python -m ai_strategy_loop.scripts.overnight_anchor_mutation --config-json <config> --out artifacts/overnight-process-research-YYYYMMDD/anchor.jsonl --deadline-hhmm 06:00 --max-rounds 0` | LLM 0회 앵커 변이 발굴. |

## 아침에 확인할 결과

| 확인 위치 | 확인 내용 |
|---|---|
| `/ui/evolution/records` | 야간 run 목록, RUN/LIVE 상태, 실패/성공 분포 |
| `/ui/evolution/lab` | Edge Ratio, 시간대×시총 히트맵, 변수별 차이 |
| `/ui/evolution/workbench` | 후보별 수익/MDD/거래수/히트맵 비교 |
| `/ui/evolution/verdict` | 승격이 아니라 evidence health/readiness 참고 |
| morning report | top 후보, blocker, 다음 실험 제안 |

## 아침 보고서에 반드시 적을 항목

| 항목 | 이유 |
|---|---|
| run-id / config 파일 | 재현성 |
| 후보 수 / valid attempt 수 / reject 사유 | 연구 밀도 확인 |
| top 5 후보의 수익/MDD/거래수/TPI/Edge Ratio | 성능 비교 |
| 개선 전후 비교 | 조건식 개선이 실제로 일어났는지 확인 |
| 실패한 가설 | 다음 반복에서 같은 실수를 줄임 |
| 운영 차단 상태 | research와 production promotion을 혼동하지 않음 |

## 최종 권장

이번 밤샘은 **추천안 1 — C-focused composite plan**으로 진행한다.

1. A로 60~90분 후보를 넓힌다.
2. B로 3시간 이상 전체기간 연구/개선 루프를 돈다.
3. C로 top 후보를 승격이 아닌 read-only review로 정리한다.
4. 06:00에는 morning report와 dashboard records/workbench를 기준으로 사람이 다음 실험을 고른다.
