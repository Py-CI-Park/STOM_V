# 아이디어 1 — 규칙 채굴/얕은 트리 증류 실패·개선·재사용

연결 문서: `2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md`, `2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea5_champion_exit_failure_improvement_reuse.md`

## 1. Verdict

아이디어 1은 초기 5개 아이디어 중 원점수 83점으로 1위였지만(C-001), 이번 문서 패키지 기준의 판정은 **독립 매수 조건식 후보로는 실패, 순위/후보축 나침반으로만 제한 재사용**이다. 오프라인 채굴은 lift와 순위 신호를 일부 포착했으나, 그 신호는 STOM 엔진에서의 양(+) EV와 동일하지 않았다(C-004). v3 EV 채굴까지 포함한 data-first rule mining v1/v2/v3는 채택 가능한 양(+) EV 규칙 또는 리프를 0개 산출했으므로(C-005), 이 축은 단독 buy-expression 승격 경로가 아니라 향후 승인된 연구에서 후보 탐색 방향을 좁히는 참고 지도에 머문다.

공통 원칙은 그대로 유지한다. 발견은 오프라인에서 하되, 백테스트/엔진은 최종 심판이다(C-002). 또한 2025-01~2026-02 구간은 이미 알려진 감사 증거이지 새 블라인드 OOS가 아니므로(C-013), 이 구간에서 사후적으로 규칙을 되살리는 주장은 금지한다. 이 문서 패키지는 코드 변경, DB 쓰기, 엔진 실행, 전략 등록을 승인하지 않는다(C-015).

## 2. Evidence claims

- C-001: 초기 심사에서 규칙 채굴/얕은 트리 증류는 83점으로 5개 아이디어 중 최고 점수였다.
- C-002: 모든 아이디어의 공통 원칙은 오프라인 발견, 백테스트/엔진 최종 심판이다.
- C-004: P1은 랭킹/lift 신호를 발견했지만, 번역된 단독 매수 규칙은 수익성이 없었다.
- C-005: v3 EV mining은 양(+) EV 채택 규칙/리프를 0개 산출했고, 데이터-우선 채굴은 v1/v2/v3에서 실패했다.
- C-013: 2025-01~2026-02는 향후 작업의 알려진 감사 증거이며 fresh blind OOS가 아니다.
- C-015: 이 문서 패키지는 소스 코드 변경, DB 쓰기, 엔진 실행, 전략 등록을 승인하지 않는다.

추론: 위 증거는 "랭킹은 어느 후보가 덜 나쁜지 말해줄 수 있지만, 그 자체가 매수식 경제성을 보장하지 않는다"는 결론을 지지한다. 이는 C-004와 C-005에서 직접 관측된 사실을 일반화한 해석이며, 새로운 성능 claim이 아니다.

## 3. Failure/root cause

핵심 실패는 **lift/ranking과 EV의 혼동**이었다. 얕은 트리는 특정 고정지평 라벨에서 양성 확률이 높은 리프를 찾을 수 있었지만, lift는 비용·손실꼬리·진입/청산 상호작용을 모두 반영한 기대손익이 아니다. 따라서 lift가 높은 리프라도 엔진에서 단독 매수식으로 발화하면 음(-) EV가 될 수 있다(C-004, C-005).

라벨 구조도 실제 거래와 맞지 않았다. 초기 레시피의 고정지평 라벨은 "지금 사서 N초 뒤 청산"에 가까웠지만, 실제 STOM 엔진은 조건식 참 구간의 연속 발화, 베팅, hard-stop 매도, 반복 재평가를 포함한다. 즉 fixed-horizon label은 엔진 손익의 대용치가 되기 어려웠고, stride 기반 표본은 엔진 firing profile과 다른 대상을 측정했다. 이 mismatch가 채굴 리프를 조건식으로 번역했을 때 경제성이 사라진 주요 원인이다.

v3는 이 원인을 보정하려고 EV 채택 기준, 파생 피처, 전이 샘플링을 도입했지만, 결과는 양(+) EV 채택 리프 0개였다(C-005). 따라서 실패 원인은 단순 구현 결함이나 번역 누락만이 아니라, 해당 채굴 공간에서 엔진 최종 심판을 통과할 독립 매수 엣지가 확인되지 않았다는 데 있다(C-002).

## 4. Reusable assets

재사용 가능한 것은 조건식 자체가 아니라 **나침반 기능**이다. 규칙 채굴 결과는 다음 용도에 한해 사용할 수 있다.

- 후보 축 우선순위: 어떤 피처·임계 방향이 상대적으로 덜 나쁜지 보는 ranking compass.
- 탐색 축 축소: 승인된 별도 연구에서 후보 공간을 줄이는 사전 참고 자료.
- 부정 지도: 이미 실패한 fixed-horizon label, stride sampling, standalone buy-expression 승격 경로를 반복하지 않게 하는 기록.
- 검증 설계 입력: 향후에는 lift가 아니라 EV, 엔진 발화 정합, 최종 엔진 확인을 요구한다는 gate 설계 근거(C-002, C-005).

이 재사용은 모두 문서/연구 설계 수준이다. 현재 패키지는 코드 변경·DB 변경·엔진 실행·전략 등록을 허용하지 않으므로(C-015), 어떤 mined rule도 운영 후보나 전략 원문으로 승격하지 않는다.

## 5. Disallowed claims

다음 표현은 금지한다.

- "83점 1위였으므로 수익 조건식 가능성이 높다" — 초기 점수(C-001)는 착수 우선순위였지 성능 증거가 아니다.
- "lift가 높으므로 EV도 양수다" — C-004와 C-005가 반대 증거다.
- "v3에서 일부 리프를 완화하면 살릴 수 있다" — v3 채택 기준에서 양(+) EV 리프는 0개였다(C-005).
- "2025-01~2026-02에서 맞는 규칙을 새 OOS 성과로 주장할 수 있다" — 해당 창은 known/audit evidence다(C-013).
- "단독 매수식으로 조건식 등록해 실험해도 된다" — 엔진 proof 없는 standalone buy-expression promotion은 금지이며, 이 문서 패키지는 전략 등록을 승인하지 않는다(C-015).

## 6. Future hypotheses requiring approval

향후 재개는 별도 승인과 새 사전등록이 있을 때만 가능하다.

1. **EV-first transition mining**: fixed-horizon label을 폐기하고, 엔진 발화 전이와 비용 반영 EV를 1차 채택 기준으로 삼는 연구.
2. **Champion-adjacent compass**: mined axis를 직접 조건식이 아니라 검증 챔피언 주변의 후보축/필터 후보 설명 변수로만 쓰는 연구.
3. **Negative-map reuse**: v1/v2/v3 실패 리프와 피처축을 제외 목록으로 관리하여 새 탐색이 같은 공간을 반복하지 않게 하는 연구.
4. **Engine-proof-only promotion**: 어떤 buy-expression도 별도 승인된 엔진 확인 전에는 후보 원문, DB 등록, 실전 사용 claim을 갖지 않는 프로토콜.

위 가설들은 `2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md`의 종합 결론과 함께 읽어야 하며, 이벤트 축의 병렬 부정 결과는 `2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md`를 기준으로 삼는다.
