# 조건식 생성 범위 인벤토리 (2026-06-17)

## 요약

이번 검토는 "백테스트 결과를 분석하고 AI가 넓은 범위의 조건식을 생성하여 연구하는가"를 별도 축으로 본다. 결론은 다음과 같다.

| 구분 | 현재 상태 | 판단 |
|---|---|---|
| 넓은 템플릿 풀 | `ai_strategy_loop/tmap/templates/*.json` 149개, 전부 기본 렌더/검증 통과 | 구현됨 |
| tick/min 분산 | tick 111개, min 38개 | 구현됨, tick 중심 |
| AND 필터 구조 | 149/149개가 `and` 구조 포함 | 강함 |
| OR/대체 경로 | literal `or`는 38/149개이나, `if/elif` 분기는 121/149개 | literal OR보다 분기 OR가 주력 |
| 시간/시총/수급 범위 | 시간창 149/149, 시총 149/149, 유동성 112/149, 거래대금 급증 102/149 | 범위는 넓음 |
| 사람식 사례 반영 | 5분 시간 버킷, 시총 밴드, 기존 전략/few-shot, human reference 비교 계획 존재 | 일부 구현, 검증은 제한적 |
| 백테스트 성과 연결 | cold/stateful LLM 40개 PROMISING 0, anchor mutation train-gate +13.93M | 생성 다양성은 성과로 완전히 연결되지 않음 |
| OOS 증명 | 신규 생성/변이 후보의 고정 OOS 통과 증거 0 | 미완성 |

## 소스/근거 인벤토리

| # | 경로 | 확인한 내용 | 평가 용도 |
|---:|---|---|---|
| 1 | `utility/ai_agent/strategy.txt` | STOM 매수/매도 조건식 변수와 예시. 인코딩은 깨져 보이나 1초/1분, 매수 True 탈락 방식, 매도 False 트리거 계약 확인 | 조건식 생성 계약 |
| 2 | `utility/ai_agent/rules.txt` | 전략 생성 전 `strategy.txt`를 읽고 매수/매도를 분리 저장해야 한다는 규칙 | 생성 절차 계약 |
| 3 | `ai_strategy_loop/brain/prompt.py` | 시간 분산, classification, time-cap bucket, filter gate, few-shot, autopsy feedback, feature hint 주입 토글 | AI 생성 넓이 |
| 4 | `ai_strategy_loop/brain/generator.py` | LLM 응답 추출 후 compile/token/scope/liquidity/filter/time-window/sell-budget 게이트 | 생성물 사전 검증 |
| 5 | `ai_strategy_loop/brain/filter_gate.py` | filter category 수, 시간창 bounds/span/no-op 측정 | AND 게이트와 시간창 품질 측정 |
| 6 | `ai_strategy_loop/brain/band_compiler.py` | BandSpec/TimeBranch/McapBlock로 range gate와 time/cap branch 컴파일 | 구조화 조건식 생성 기반 |
| 7 | `ai_strategy_loop/tmap/template.py` | JSON template load/render/coordinate/grid sweep | 템플릿 기반 조건 생성 |
| 8 | `ai_strategy_loop/tmap/mutator.py` | anchor theta 인접값 변이 제안 | 좋은 조건식 주변 탐색 |
| 9 | `ai_strategy_loop/scripts/tmap_autopsy_loop.py` | sweep summary와 anchor mutation 후보를 P0b gate로 채택/기각 | 백테스트 결과 반영 루프 |
| 10 | `ai_strategy_loop/scripts/overnight_anchor_mutation.py` | LLM 없이 검증된 anchor에서 변이, materialize, batch eval, gate=True 채택, hill-climb | 자동 개선 루프 |
| 11 | `ai_strategy_loop/scripts/tmap_multiband_discovery.py` | tick/min track별 LLM template 생성, smoke/full/OOS cascade, stateful feedback | 넓은 생성 실험 |
| 12 | `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md` | 사람식 연구 기준: 5분 시간 버킷, 시총 밴드, OOS-disabled research, sell forms, dashboard visibility | 사람식 연구 설계 |
| 13 | `.omo/plans/condition-research-end-to-end-master-roadmap-20260606.md` | 전체 프로세스: generation -> backtest -> analysis -> feedback -> validation -> wiki | 운영 로드맵 |
| 14 | `docs/AGENT_HANDOFF.md` | wide generation, classification/filter/few-shot, T0-T4 handoff, 다음 다년/OOS run 권장 | 기존 연구 맥락 |
| 15 | `docs/update_log/2026-06-14_condition_discovery_redesign_blueprint.md` | OR/branch 구조만으로는 성과 보장 불가, 검증된 anchor의 정직한 확장 필요 | 설계상 주의점 |
| 16 | `docs/update_log/2026-06-16_champion_positive_control_diagnostic.md` | 검증 champion 4/4 discovery gate 통과, 데이터 ceiling/게이트 문제가 아니라 생성 병목임 | 병목 진단 |
| 17 | `docs/update_log/2026-06-17_condition_self_improvement_score_update.md` | 전체 프로세스 점수 68%, OOS proof 35%, OOS 후보 0 | 기준 점수 |
| 18 | `.omo/evidence/tmap-walkforward/full_stateful_n40_summary.json` | full stateful n=40 PROMISING 0 | cold/stateful 생성 성과 |
| 19 | `.omo/evidence/tmap-walkforward/ovn_anchor_summary.json` | anchor mutation 19 rounds, adopted_total 399, best +13,928,386 / MDD 9.62 | 검증 anchor 변이 성과 |
| 20 | `.omo/evidence/tmap-walkforward/ovn_t2late.jsonl` | jsonl 기준 9 rounds, adopted_total 30, best +10,582,342 / MDD 11.5 | 다른 seed basin 증거 |

## 구현됨 vs 추론/미검증

| 영역 | 구현 또는 증거 있음 | 아직 추론/미검증 |
|---|---|---|
| 넓은 조건식 풀 | 149개 JSON template, tick/min 양쪽 존재 | template family coverage가 연구 목적별로 균등하게 관리되는 ledger는 부족 |
| AND 혼합 | 평균 `and` 17.07개, 149/149 포함 | 너무 많은 AND가 과협착/0거래로 이어지는 자동 완화 정책은 약함 |
| OR 혼합 | `if/elif` 분기 121/149개, literal `or` 38/149개 | branch OR가 실제 OOS edge를 만든다는 신규 증거는 부족 |
| 사람식 사례 | 5분 time bucket, 시총 band, 기존 전략/few-shot, sell form 연구 계획 | human reference 17개를 구조화 few-shot corpus/benchmark로 완전히 고정하지는 못함 |
| 백테스트 피드백 | stateful feedback, autopsy, feature hint, mutation loop 존재 | 피드백 action이 어떤 후보를 개선했는지 추적하는 typed ledger 부족 |
| 나쁜 조건식 개선 | anchor mutation에서 train-gate 개선 확인 | cold-generated 나쁜 조건식이 OOS 좋은 조건식으로 승격된 증거는 0 |
| 전체 시간 고려 | time window span/no-op 측정, min full-session toggle, 09:00~15:19 min 근거 | tick은 09:00~09:30 중심, 전체 장중 시간대 확장 검증은 부족 |

## 작업 범위 기록

| 항목 | 결과 |
|---|---|
| 코드 수정 | 없음 |
| DB/protected path 쓰기 | 없음 |
| 백테스트 신규 실행 | 없음 |
| 평가 방식 | 기존 코드/문서/evidence 읽기와 정량 분석 |
