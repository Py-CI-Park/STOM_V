# Wide v1 post-MVP risk backlog

## Purpose

이 문서는 `WideV1Final_B_20260425`가 Wide v1 MVP 후보로 freeze된 이후 남아 있는 위험을 기록한다.

이 문서는 조건식 개선 개발을 중단하기 위한 문서가 아니다. Wide v1 결과를 과대 해석하지 않고, 다음 Wide v2 자동 조건식 개선 작업과 운영/실거래 위험 관리를 분리하기 위한 문서다.

## Frozen candidate

- final_buy_strategy=WideV1Final_B_20260425
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419

## What WFO pass means

WFO 통과는 다음 의미를 가진다.

```text
1. 최종 후보가 단일 전체기간 백테스트에만 의존하지 않았다.
2. 여러 forward validation window에서 성능 기준을 통과했다.
3. zero-trade window 없이 검증 구간마다 거래가 발생했다.
4. Wide v1 MVP 후보로 freeze할 근거가 있다.
```

Wide v1 WFO 요약:

- round_count=8
- success_rate=1.0
- mean_oos_metric=0.5762499999999999
- mean_trade_count=2131.75
- zero_trade_rounds=0
- balanced_preset=pass
- conservative_preset=pass

## What WFO pass does not mean

WFO 통과는 다음을 보장하지 않는다.

```text
1. 실거래 수익 보장
2. 슬리피지 없는 체결
3. 호가 잔량과 주문 우선순위 반영
4. 장중 네트워크/API 장애 대응
5. 주문 실패나 부분 체결 처리 안전성
6. 미래 시장 구조 변화 대응
7. 모든 기간에서 항상 수익
```

따라서 Wide v1 freeze는 연구 MVP 성공이지 live trading release 승인이 아니다.

## Risk backlog

| Area | Risk | Required before live use | Status |
| --- | --- | --- | --- |
| Slippage | 백테스트 체결가와 실제 체결가 차이 | 백테스트 예측 체결가와 paper/live 체결가 비교 표준화 | Open |
| Fill quality | 호가 잔량, 주문 우선순위, 부분 체결 미반영 | 주문 체결 로그와 미체결 로그 수집 | Open |
| Broker/API runtime | Kiwoom/API 장애, 지연, disconnect | 장애 감지와 중지 조건 확인 | Open |
| Network | 장중 네트워크 장애 | 재접속/중지 절차 문서화 | Open |
| Cash guard | 예수금 부족 또는 주문 크기 오류 | 주문 전 예수금, 종목당 금액, 일일 총액 guard 확인 | Open |
| Symbol concentration | 특정 종목 집중 | 종목별/일자별 집중도 live report 작성 | Open |
| Daily stop | 하루 손실 확대 | 일일 손실/연속 실패 중지 조건 정의 | Open |
| Rollback | 문제 발생 시 전략 중지 지연 | 전략 disable/rollback 절차 작성 | Open |
| Logging | 실거래와 백테스트 비교 근거 부족 | 장 종료 후 비교 템플릿 작성 | Open |
| Research continuity | 운영 검증과 조건식 개선 개발 혼동 | Wide v2 연구 브랜치를 별도로 시작 | Open |

## Paper or live pilot checklist

실거래 또는 paper pilot 전에 아래 항목을 별도 PR에서 닫아야 한다.

- [ ] pilot 기간 정의
- [ ] pilot 대상 계좌 또는 paper 환경 정의
- [ ] 주문 금액 상한 정의
- [ ] 종목당 최대 노출 정의
- [ ] 일일 최대 손실 중지 조건 정의
- [ ] 주문 실패 시 행동 정의
- [ ] 미체결 시 행동 정의
- [ ] 장중 API 장애 시 행동 정의
- [ ] 장 종료 후 거래 로그 저장 위치 정의
- [ ] 장 종료 후 백테스트 예측과 실제 체결 비교 템플릿 작성
- [ ] pilot 중단 기준 정의
- [ ] rollback/disable 명령어 문서화

## Condition optimizer continuation

운영 위험 정리는 Wide v2 조건식 개선 개발을 막지 않는다.

다음 조건식 개선 작업은 아래처럼 별도 연구 사이클로 진행한다.

```text
WideV1Final_B_20260425 또는 별도 기준 조건식
-> 백테스트
-> 결과 분석
-> 후보 조건식 생성
-> 후보 N개 백테스트
-> best_candidate 선택
-> 다음 baseline으로 승격
-> 여러 라운드 반복
-> 최종 후보만 WFO
```

## Stop conditions

- WFO 통과만으로 실거래 수익을 보장한다고 표현하지 않는다.
- Wide v1 WFO 결과를 덮어쓰지 않는다. 재실행이 필요하면 새 브랜치와 새 PR에서 수행한다.
- `STOM_Version_2U_C`에 직접 커밋하지 않는다.
- 신규 조건식 자동 개선은 Wide v2 브랜치에서 진행한다.

## Next command

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```
