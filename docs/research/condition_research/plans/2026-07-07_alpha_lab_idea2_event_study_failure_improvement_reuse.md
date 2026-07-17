# 아이디어 2 — 이벤트 스터디 실패·개선·재사용

연결 문서: `2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md`, `2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea4_regime_gate_failure_improvement_reuse.md`

## 1. Verdict

아이디어 2는 초기 5개 아이디어 중 원점수 82점으로 2위였지만(C-001), 판정은 **깨끗한 부정 결과, raw event EV 셀 재활용 금지, champion-trade context tag로만 제한 재사용**이다. 사전등록 이벤트 스터디는 42,363개 사건과 138개 층화 셀을 측정했고, FDR 생존 셀은 0개였다(C-006). 따라서 "사건 자체가 독립 매수 엣지"라는 가설은 이 데이터에서 통계적으로 기각됐으며, 원시 non-FDR EV 셀을 사후 후보로 되살리는 것은 금지한다.

공통 원칙은 아이디어 1과 동일하다. 발견 단계는 오프라인으로 옮길 수 있지만, 최종 판정은 백테스트/엔진이 한다(C-002). 2025-01~2026-02는 이미 알려진 감사 증거이지 fresh blind OOS가 아니며(C-013), 이 문서 패키지는 코드 변경, DB 쓰기, 엔진 실행, 전략 등록을 승인하지 않는다(C-015).

## 2. Evidence claims

- C-001: 초기 심사에서 이벤트 스터디는 82점으로 5개 아이디어 중 2위였다.
- C-002: 모든 아이디어의 공통 원칙은 오프라인 발견, 백테스트/엔진 최종 심판이다.
- C-006: P2는 42,363개 사건과 138개 셀을 측정했고, FDR 생존 셀은 0개였다.
- C-013: 2025-01~2026-02는 향후 작업의 알려진 감사 증거이며 fresh blind OOS가 아니다.
- C-015: 이 문서 패키지는 소스 코드 변경, DB 쓰기, 엔진 실행, 전략 등록을 승인하지 않는다.

추론: 위 증거는 "event-as-alpha"가 아니라 "event-as-context"만 남긴다는 결론을 지지한다. 즉 사건은 매수 신호가 아니라, 이미 검증된 챔피언 거래를 해석·태깅하는 보조 문맥으로만 남길 수 있다. 이는 C-006의 FDR 0 결과에서 도출한 보수적 제한이며, 새 수익성 claim이 아니다.

## 3. Failure/root cause

실패는 통계적으로 명확했다. 42,363개 사건을 138개 셀로 층화했지만 FDR 기준을 통과한 셀이 0개였으므로(C-006), raw p-value나 원시 EV가 좋아 보이는 소수 셀은 다중검정 보정 후 살아남지 못했다. 이 결과는 사전등록된 기준에서 나온 clean negative이며, 사후 임계 완화나 셀 재분류로 뒤집을 수 없다.

근본 원인은 이벤트 자체가 STOM 엔진의 비용·체결·청산 구조를 이길 만큼 안정적인 조건부 EV를 만들지 못했다는 점이다. 사건은 시장 상태를 설명할 수는 있지만, 독립 진입 조건으로 번역될 때 통계적 생존성과 엔진 경제성을 동시에 확보하지 못했다. 따라서 향후 이벤트는 raw signal이 아니라 champion trade의 주변 문맥을 설명하는 tag로만 취급해야 한다.

또한 translation/parity gate가 필요하다. 이벤트 정의가 문서상으로는 명확해 보여도, 실제 엔진 조건식으로 옮길 때 사건 발생 시각, 재발화, 중복 사건, 장중 상태 유지 방식이 달라질 수 있다. FDR 0인 현재 결과에서는 번역·등록 자체가 승인되지 않지만(C-015), 별도 승인 연구가 열린다면 먼저 event definition과 엔진/오프라인 parity를 통과해야 한다(C-002).

## 4. Reusable assets

재사용 가능한 것은 독립 매수식이 아니라 **챔피언 거래 문맥 태그**다.

- Champion-trade context tag: 검증 챔피언 거래가 VI해제, 신고가, 거래대금서지, 갭, 라운드피겨 등 어떤 사건 주변에서 발생했는지 설명하는 태그.
- Negative map: 42,363개 사건/138개 셀/FDR 0 결과를 근거로 raw event EV cell 재탐사를 막는 부정 지도(C-006).
- Audit feature: 향후 성과 보고에서 "특정 챔피언이 어떤 사건 환경에 노출됐는가"를 설명하는 해석 보조 자료.
- Gate template: 향후 이벤트 연구는 사전등록, 다중검정 보정, 번역/패리티 확인, 엔진 최종 판정 순서를 따라야 한다(C-002).

이 재사용은 event-as-context에 한정된다. 이벤트를 직접 buy trigger, standalone condition, DB 등록 전략으로 승격하는 행위는 이 문서 패키지의 승인 범위를 벗어난다(C-015).

## 5. Disallowed claims

다음 표현은 금지한다.

- "82점 2위였으므로 이벤트 전략은 유망하다" — 초기 점수(C-001)는 착수 우선순위였지 성능 증거가 아니다.
- "원시 EV가 양수인 non-FDR 셀은 후보로 살릴 수 있다" — FDR 생존 0이 공식 판정이다(C-006).
- "셀을 다시 나누거나 임계를 낮추면 같은 결과를 재사용할 수 있다" — 이는 사후 기준 변경이며, clean negative를 훼손한다.
- "이벤트 발생은 독립 매수 신호다" — 이 문서의 허용 재사용은 champion-trade context tag뿐이다.
- "2025-01~2026-02에서 이벤트 조합이 맞으면 fresh OOS다" — 해당 창은 known/audit evidence다(C-013).
- "이벤트 조건식을 바로 번역·등록해 엔진에서 확인해도 된다" — 현재 패키지는 엔진 실행·전략 등록을 승인하지 않으며(C-015), 향후 연구도 translation/parity gate와 별도 승인이 필요하다(C-002).

## 6. Future hypotheses requiring approval

향후 재개는 별도 승인과 새 사전등록이 있을 때만 가능하다.

1. **Event-as-context only**: 이벤트를 매수 신호가 아니라 검증 챔피언 거래의 설명 태그로 붙여 성과 분해·리스크 해석에만 사용하는 연구.
2. **Champion interaction study**: raw event EV가 아니라 챔피언별 거래 전후 문맥과 손익 분포의 상호작용을 측정하는 연구. 이 경우에도 FDR 및 엔진 최종 판정 원칙은 유지한다(C-002).
3. **Translation/parity gate first**: 이벤트 정의를 엔진에서 동일하게 재현할 수 있는지 먼저 검증한 뒤, 승인된 경우에만 후보 연구로 진행하는 프로토콜.
4. **No raw-cell revival**: 기존 138개 셀의 non-FDR 양수 관찰값은 가설 생성용 메모 이상으로 승격하지 않는 부정 결과 보존.

이 문서는 `2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md`의 종합 결론에 종속된다. 규칙 채굴 축의 병렬 실패와 나침반 재사용 범위는 `2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md`를 참조한다.
