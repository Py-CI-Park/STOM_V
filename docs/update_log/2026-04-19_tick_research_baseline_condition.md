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

## wt-dev 실제 실행 성공 결과

사용자가 동일 조건식을 `STOM_V.wt-dev`의 실제 STOM 실행 환경에서 다시 로딩해 직접 백테스트한 결과, 정상 완료됐다.

```text
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
timeframe: tick
avg_time: 30
engines: 32
buy: ResearchTest_Tick_B_090000_092800_Wide_20260419
sell: ResearchTest_Tick_S_090000_092800_Wide_20260419
runtime: 0:01:00.675279
```

성과:

```text
거래횟수: 40,937회
일평균거래횟수: 169.9회
적정최대보유종목수: 40개
평균보유기간: 228.19초
승률: 30.02%
평균수익률: -0.68%
수익률합계: -695.09%
수익금합계: -5,564,960,005원
최대낙폭률: 693.76%
매매성능지수: 0.60
연간예상수익률: -721.05%
```

CSV:

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

## 판단

feature worktree CLI에서의 실패는 조건식 자체 문제보다 런타임 DB, shared memory, 실행 컨텍스트 차이로 판단한다.

`wt-dev` 실제 실행 결과를 기준으로 보면 Wide v1은 연구용 baseline으로 유효하다.

```text
CSV 생성: 성공
거래 수 확인: 성공
runtime 확인: 성공
Retention-Aware 입력 CSV 확보: 성공
```

수익률과 리스크는 매우 나쁘지만 이는 연구용 wide baseline의 실패 사유가 아니다.

```text
목표: 수익률 최적화가 아니라 대량 거래 데이터 확보
결과: 40,937회 거래 확보
```

## 다음 단계

`Wide v2` 조건식은 즉시 필수는 아니다.

먼저 생성된 Wide v1 CSV를 Retention-Aware 후보 개선 루프에 넣는다.

```text
input:
stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv

base_buy_strategy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

sell_strategy:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```

추천 순서:

```text
1. Wide v1 CSV로 discovery research --run-candidates 실행
2. Retention-Aware 후보 선별 결과 확인
3. 후보 N개 백테스트/랭킹
4. best_candidate와 failure reason 분석
5. 필요 시 Wide2 조건식 설계
```

Wide2 후보 조건은 보류한다.

```text
ResearchTest_Tick_B_090000_092800_Wide2_20260419
ResearchTest_Tick_S_090000_092800_Wide2_20260419
```

## 남은 리스크

- Wide v1은 실전 전략으로는 손실과 낙폭이 매우 크다.
- Wide v1은 연구 baseline이지 live 후보가 아니다.
- feature worktree CLI 실행과 wt-dev GUI/실행 환경의 결과가 달랐으므로, 실제 백테스트 판단은 wt-dev 기준으로 기록한다.
- Retention-Aware 후보 개선 후에도 best_candidate는 promotion 통과를 의미하지 않는다.
- 최종 채택 전에는 discovery promote 또는 WFO 검증이 필요하다.
