"""alpha_lab — 데이터-우선 알파 발굴 연구 패키지 (research-only).

사전등록 봉인·통합 n_trials 원장(registry)을 기반으로 P1 규칙 채굴과
P2 이벤트 스터디 MVP를 수행한다. 모든 탐색은 봉인된 사전등록
(preregistration_v1.json)과 단일 원장(n_trials_ledger.jsonl) 규율을 따른다.
tick DB 접근은 read-only(file:...?mode=ro) 전용이며, 산출 조건식은 기존
게이트 체인(스모크→train→OOS→슬리피지 tick2)을 무특혜로 통과해야 한다.
"""
