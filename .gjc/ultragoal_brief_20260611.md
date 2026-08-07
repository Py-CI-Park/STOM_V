공유 제약(전 스토리 공통):
- 불변 목표: 시드 DB·연구 문서에서 출발해 시간창과 매매 횟수를 최대로 늘려 최대 수익을 내는 조건식을 만들고 백테스트로 검증해 수익 모델을 확보한다.
- 근거 문서: docs/update_log/2026-06-11_session_handoff_full.md (재개 진입점), 2026-06-11_tmap_process_redesign.md, 2026-06-11_program_status_progress_and_roadmap.md.
- 정직성 불변식: 백테스트 엔진/하드게이트/backtest_graph 무수정. OOS-blind 동결, 사후 재선택 금지. 지도/반사실/MC는 인샘플 advisory — 판정은 V3 고정 OOS와 V4 walk-forward 규율로만.
- V3K 게이트 불변: 게이트 4 미승인 상태 유지. USER_ACK, enable 레지스트리, 운영 _database/ 쓰기, KHOPENAPI 연결, 라이브 주문 배선 금지. feature flag 기본 OFF 유지.
- 보호 경로(_database/, _log/, backup/, *.db 운영본, backtest/graph/, v3k_settings*.json) 소스 취급 금지.
- 커밋: 한국어 제목·한국어 본문, 파일 명시 스테이징, 작게 나눠 커밋. 검증은 PYTHONUTF8=1 python -m pytest tests/unit/ -q (기존 고정 실패 7건 외 전부 통과 기준).
- GPT OAuth(gpt_auth) 사용 가능 충전 완료 — GPT 생성 경로를 최대한 활용하되, zero-LLM 경로(claude_candidate_batch_eval.py pairs 배치)는 검증 축으로 병행한다.
- 모든 산출 증거는 .omo/evidence/ 아래에 남기고, 단계 결과는 docs/update_log/에 한국어 문서로 기록한다.

@goal: A1 W1 본 스윕 — 다년 경향성 지도
seed_902905 템플릿 13θ 슬롯 전체(56포인트)를 2023~2025 train 데이터로 스윕해 정식 다년 경향성 지도를 만든다.
명령: PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_sweep --template seed_902905 --config-json .omo/evidence/claude-condition-research-20260610/train-config.json --run-id tmap_seed_full_train_20260611 --manifest-out .omo/evidence/tmap-walkforward/full_train_manifest.json
완료 기준: full_train_manifest.json 생성, GET /tmap_map?run_id=tmap_seed_full_train_20260611 에서 슬롯별 지도 응답 확인, 고원/절벽 요약을 증거 파일로 저장.

@goal: A2 고원 세타스타 확정과 조합 점 평가
다년 지도에서 슬롯별 고원 중심(θ*)을 판독하고, 상위 2~3개 슬롯의 조합 점 4~6개를 템플릿 렌더러로 생성해 zero-LLM pairs 배치 도구로 train 평가한다.
완료 기준: 슬롯별 고원 판정 근거(단조/고원/절벽 분류)와 조합 점 평가 결과가 증거 JSON·문서로 기록되고, 동결 후보 θ* 목록이 확정된다.

@goal: A3 동결 재평가와 V1 V2 V3 검증
BASE_SEED + θ* 후보들을 한 배치 train run으로 재평가하고(스윕 run에는 BASE_ 라벨이 없으므로 동결은 반드시 이 재평가 run에서) select_and_freeze.py로 seed_relative 동결한다. 동결 산출물의 V1 3중 분포검증(블록 MC/PBO/DSR advisory) 확인, V2 플라시보 검정(gen_placebo_strategy.py 생성 후 동일 배치 평가) 1회 실시, V3 고정 OOS(gen_oos_configs.py로 2022/2026 config 생성, 동일 창 93000, 시드 동시 재측정)를 실행해 p0 정책 §5 합격 규칙으로 판정한다.
완료 기준: 동결 로그·overfit advisory·플라시보 비교·OOS 2022/2026 결과·결정 카드(PROMOTE/REJECT/NEEDS_MORE)가 증거로 존재.

@goal: V5 슬리피지 스트레스 도구 구현
핸드오프에서 미구현으로 정직 공시된 V5 슬리피지 스트레스 advisory 도구를 구현한다. 기존 백테스트 CSV(체결가 기반)를 입력으로 슬리피지 시나리오(틱 단위 불리 체결 0/1/2틱, 수수료 상향)별 수익·MDD 재계산을 수행하는 순수 분석 모듈(ai_strategy_loop/fitness/ 아래)과 대시보드 advisory 노출 또는 스크립트 진입점을 추가한다. 백테스트 엔진은 절대 수정하지 않는다(CSV 후처리 advisory만).
완료 기준: 단위 테스트 포함, A3 동결 후보에 1회 실적용한 스트레스 리포트 증거 생성, 승격 게이트 절차 문서에 V5 절차 명시.

@goal: A4 시간 횟수 확대 니치 템플릿과 지도
min DB 풀세션(2025-04~2026-02, 11개월 한정 — 다년 검증 불가 명시) 기반 신규 템플릿 JSON 2종(오전 모멘텀, 오후 되돌림)을 ai_strategy_loop/tmap/templates/ 에 작성하고(코드 추가 불필요, 템플릿 데이터만), 각각 스윕해 시간 확대 축 경향성 지도를 만든다. GPT OAuth 생성 경로를 템플릿 변형(구조 탐색) 보조에 활용한다.
완료 기준: 템플릿 2종 JSON + 각 스윕 manifest + 지도 판독(고원 존재 여부) 증거·문서.

@goal: A5 포트폴리오 조립과 V4 walk-forward
저상관 고원 후보들을 /portfolio_preview 로 결합 미리보기하고 채택 조합을 실백테로 확인한다. tmap_walkforward.py 로 재적합 정책 v1의 다년 누적 OOS(시나리오 D, windows 분할)를 실가동한다.
완료 기준: 포트폴리오 채택 조합의 실백테 결과와 walk-forward 누적 OOS 리포트가 증거로 존재, 정책 합격/불합격 판정 기록.

@goal: A6 GPT 루프 합류와 토글 스모크
gpt_auth(GPT OAuth) 충전 상태를 확인하고, 신규 토글 4종(exec_budget_prompt/guard, report_principles, quantile_feedback, counterfactual_feedback) ON 스모크 A/B를 실행해 루프가 템플릿 변이(구조 탐색)를 담당하게 한다. GPT 생성 경로를 최대 활용한다.
완료 기준: 토글 ON/OFF A/B 스모크 결과 비교 증거, GPT 생성 후보가 루프 DB에 적재되고 평가 사이클이 1회 이상 완주.

@goal: 결정 카드와 세션 마무리 문서
V6 결정 카드(PROMOTE/REJECT/NEEDS_MORE)를 최종 갱신하고, 시드 대체 vs 보완 사용자 결정점을 명시한 운용 결정 요청서를 작성한다. 전체 사이클 결과를 docs/update_log/ 핸드오프 문서로 기록하고 커밋 체인을 정리한다(한국어 커밋, 파일 명시 스테이징).
완료 기준: 결정 카드·핸드오프 문서 커밋 완료, pytest tests/unit/ 통과(고정 실패 목록 외), git status 클린.
