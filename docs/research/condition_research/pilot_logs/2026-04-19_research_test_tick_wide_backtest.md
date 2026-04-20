# Research Test Tick Wide Backtest Pilot

## 전체 플로우

```text
[ResearchTest wide strategy]
        |
        v
[direct tick backtest]
        |
        v
[CSV baseline for Retention-Aware loop]
```

## 실행 대상 전략

- buy: `ResearchTest_Tick_B_090000_092800_Wide_20260419`
- sell: `ResearchTest_Tick_S_090000_092800_Wide_20260419`

## 런타임 DB 준비

Task 4 실행 전 feature worktree의 ignored `_database`를 `C:\System_Trading\STOM\STOM_V.wt-dev\_database` 기준으로 다시 맞췄다.

```text
strategy.db: wt-dev 실제 전략 DB 복사
setting.db: wt-dev 실제 설정 DB 복사
backtest.db: wt-dev 실제 백테스트 결과 DB 복사
stock_tick_back.db: wt-dev 실제 tick 백테스트 DB hardlink
```

이후 실제 runtime `strategy.db` 기준으로 전략명을 다시 확인하고 저장했다.

```text
stockbuy Tick_B_902_905_Update_2 1
stocksell Tick_S_902_905_Update_2 1
stockbuy ResearchTest_Tick_B_090000_092800_Wide_20260419 1
stocksell ResearchTest_Tick_S_090000_092800_Wide_20260419 1
```

기존 최적화 전략은 덮어쓰지 않았다.

## 2025년 전체 백테스트 시도

명령:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
```

결과:

```text
정상 완료하지 못함
외부 실행 제한 시간 초과
stdout 결과 없음
ResearchTest CSV 생성 없음
```

후속 정리:

```text
남은 백테스트 프로세스 트리 강제 종료
backdata_0 ~ backdata_31 shared memory unlink
```

## 2025년 1월 smoke 시도

명령:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20250131 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 300
```

결과:

```text
정상 완료하지 못함
외부 실행 제한 시간 초과
stdout 결과 없음
ResearchTest CSV 생성 없음
```

## 2025-04-07 1일 smoke 시도

명령:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250407 `
  --end 20250407 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 60
```

결과:

```text
정상 완료하지 못함
외부 실행 제한 시간 초과
stdout 결과 없음
ResearchTest CSV 생성 없음
```

후속 정리:

```text
backdata_0 ~ backdata_31 shared memory unlink
```

## 판단

feature worktree CLI에서는 정상 완료하지 못했지만, 사용자가 같은 조건식을 `STOM_V.wt-dev`의 실제 실행 환경에서 다시 로딩해 직접 실행한 결과 정상 완료됐다.

따라서 앞선 worktree 실패는 조건식 자체 문제라기보다 worktree 런타임 DB, shared memory, CLI 실행 컨텍스트 차이로 판단한다.

## wt-dev 실제 실행 성공 결과

```text
[2026-04-20 13:20:30] 백테스트 실행조건
startday=20250101
endday=20251231
starttime=090000
endtime=092800
avgtime=30
buy=ResearchTest_Tick_B_090000_092800_Wide_20260419
sell=ResearchTest_Tick_S_090000_092800_Wide_20260419
back_count=1638
engine_start=90000
engine_end=92800
engine_avg=[30]
engine_multi=32
```

결과:

```text
거래횟수: 40,937회
일평균거래횟수: 169.9회
적정최대보유종목수: 40개
평균보유기간: 228.19초
익절: 12,289회
손절: 28,648회
승률: 30.02%
평균수익률: -0.68%
수익률합계: -695.09%
수익금합계: -5,564,960,005원
최대낙폭금액: 5,566,752,407원
최대낙폭률: 693.76%
매매성능지수: 0.60
연간예상수익률: -721.05%
백테스트 소요시간: 0:01:00.675279
```

부트스트랩:

```text
부트스트랩 평균수익률: -1.0%
예상최소수익률: -1.0%
예상최대수익률: -1.0%
전략유의확률(pv): 0.0%
```

생성 CSV:

```text
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv
```

## 결론

Task 4의 실질 목적은 `wt-dev` 실제 실행 환경에서 달성됐다.

```text
CSV 생성: 성공
거래 수 확인: 성공
runtime 확인: 성공
Retention-Aware 기준 CSV 확보: 성공
```

Wide v1은 실전 전략으로는 부적합하다.

```text
수익률: 매우 나쁨
최대낙폭률: 매우 큼
TPI: 낮음
```

그러나 연구 baseline으로는 가치가 있다.

```text
기존 최적화 tick 전략 거래 수: 약 100회
ResearchTest wide 거래 수: 40,937회
```

이는 자동 조건식 개선 루프가 분석할 표본을 충분히 제공한다.

## 다음 조정 방향

Wide2 조건식은 즉시 필수는 아니다. 먼저 wt-dev에서 생성된 Wide v1 CSV를 Retention-Aware 후보 개선 루프의 입력으로 사용한다.

다음 실행 순서:

```text
1. Wide v1 결과 CSV를 discovery research --run-candidates 입력으로 사용
2. Retention-Aware 후보 선별 결과 확인
3. 후보 N개 백테스트/랭킹
4. best_candidate와 promotion failure reason 분석
5. 필요할 때 Wide2 조건식 설계
```

Wide2 후보 조건은 보류한다.

```text
데이터길이 >= 30
체결강도 >= 80
초당거래대금 > 0
초당매수수량 > 0
초당매도수량 > 0
전일동시간비 > 0
```

이 조건들은 나중에 Wide v1이 너무 무겁거나 결과 품질이 분석 불가능할 때 적용한다.

## 다음 Retention-Aware 입력

```text
input_csv:
C:\System_Trading\STOM\STOM_V.wt-dev\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260420132132.csv

base_buy_strategy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

sell_strategy:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```
