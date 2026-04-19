# 2026-04-19 Tick Research Baseline Condition

## 목적

자동 조건식 연구용 거래 데이터 확보를 위해 넓은 tick baseline 매수/매도 조건식을 설계하고, 로컬 `strategy.db`에 저장한 뒤 직접 백테스트를 시도했다.

## 전체 플로우

```text
[외부 우수 전략 보고서]
        |
        v
[문서 보존/요약]
        |
        v
[ResearchTest wide 조건식]
        |
        v
[strategy.db 저장]
        |
        v
[직접 tick 백테스트]
        |
        v
[Retention-Aware 개선 루프 입력 CSV]
```

## 변경 사항

- `docs/research/condition_research/` 문서 트리 생성
- `E:\Download\backtest_analysis_report_v2.md` 원문 보존
- 외부 보고서 요약 작성
- 넓은 tick 연구용 매수/매도 조건식 문서화
- `ResearchTest_Tick_B_090000_092800_Wide_20260419` 저장
- `ResearchTest_Tick_S_090000_092800_Wide_20260419` 저장
- 직접 백테스트 시도 및 실패 원인 기록

## 전략 저장 결과

```text
validate_buy: ok
validate_sell: ok
collision before save:
  stockbuy ResearchTest_Tick_B_090000_092800_Wide_20260419 0
  stocksell ResearchTest_Tick_S_090000_092800_Wide_20260419 0
save_buy: created
save_sell: created
evaluate_buy: ok
evaluate_sell: ok
```

주의:

```text
strategy.db는 ignored runtime DB이며 Git에 커밋하지 않았다.
Task 4 전 실제 runtime DB 기준으로 다시 동기화/충돌 확인/저장을 수행했다.
기존 Tick_B_902_905_Update_2 / Tick_S_902_905_Update_2는 덮어쓰지 않았다.
```

## 백테스트 결과

### 2025년 전체

```text
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
timeframe: tick
avg_time: 30
engines: 32
timeout: 900
```

결과:

```text
정상 완료하지 못함
외부 실행 제한 시간 초과
ResearchTest CSV 생성 없음
```

### 2025년 1월

```text
period: 2025-01-01 ~ 2025-01-31
timeout: 300
```

결과:

```text
정상 완료하지 못함
외부 실행 제한 시간 초과
ResearchTest CSV 생성 없음
```

### 2025-04-07 1일

```text
period: 2025-04-07
timeout: 60
```

결과:

```text
정상 완료하지 못함
외부 실행 제한 시간 초과
ResearchTest CSV 생성 없음
```

## 런타임 정리

백테스트 timeout 이후 남은 shared memory를 정리했다.

```text
backdata_0 ~ backdata_31 unlink
```

## 판단

이번 wide 조건식은 너무 넓다.

```text
1일 smoke도 완료하지 못함
CSV 생성 실패
거래 수 확인 실패
Retention-Aware 입력 CSV 확보 실패
```

즉, 이번 Task는 문서화/저장/검증까지는 성공했지만, 직접 백테스트 성공 기준은 충족하지 못했다.

## 다음 단계

`Wide v2` 조건식이 필요하다.

목표는 여전히 “연구 데이터 확보용 넓은 baseline”이지만, 아래 최소 실행 가능성 조건을 추가해야 한다.

```text
데이터길이 >= 30
체결강도 >= 80
초당거래대금 > 0
초당매수수량 > 0
초당매도수량 > 0
전일동시간비 > 0
```

추천 순서:

```text
1. Wide v2 조건식 설계
2. strategy.db에 Wide2 이름으로 저장
3. 1일 smoke
4. 1개월 smoke
5. 2025년 전체 백테스트
```

추천 전략명:

```text
ResearchTest_Tick_B_090000_092800_Wide2_20260419
ResearchTest_Tick_S_090000_092800_Wide2_20260419
```

## 남은 리스크

- Wide v1은 직접 백테스트 완료에 실패했다.
- 너무 넓은 조건식은 백테스트 엔진 부하를 과도하게 키울 수 있다.
- 성공적인 연구 baseline은 거래 수와 런타임 사이의 균형이 필요하다.
- Wide v2도 수익률 최적화가 아니라 연구 데이터 확보가 목적이어야 한다.
