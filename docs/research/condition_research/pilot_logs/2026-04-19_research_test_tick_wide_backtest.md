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

이번 wide 조건식은 연구 데이터 확보라는 의도에는 맞지만, 실제 tick 백테스트 엔진에는 너무 넓다.

특히 1일 smoke도 완료하지 못했으므로, 현재 조건식은 다음 단계로 그대로 사용할 수 없다.

현재 조건식의 문제 추정:

```text
관심종목 + 가격 + 등락율 + 당일거래대금만으로는 진입 후보가 너무 많음
체결강도/거래량/호가/VI 계열을 전혀 제한하지 않아 백테스트 부하가 과도함
매수 조건이 자동 연구용 baseline으로도 지나치게 broad함
```

## 결론

Task 4의 직접 백테스트는 성공 기준을 충족하지 못했다.

```text
CSV 생성: 실패
거래 수 확인: 실패
runtime 확인: 실패
Retention-Aware 기준 CSV 확보: 실패
```

다음 작업은 기존 wide 조건식 저장/백테스트를 완료로 볼 수 없으며, 조건식을 조정해야 한다.

## 다음 조정 방향

기존 설계의 “넓은 조건식” 목표는 유지하되, 최소한의 거래량/체결강도 조건을 추가해 엔진 부하를 줄여야 한다.

후보 조정안:

```text
데이터길이 >= 30
체결강도 >= 80
초당거래대금 > 0
초당매수수량 > 0
초당매도수량 > 0
전일동시간비 > 0
```

이 조건들은 여전히 최적화 조건이 아니라, 비정상/극저활성 tick을 제거하기 위한 최소 실행 가능성 조건으로 봐야 한다.

다음 파일럿은 아래 순서가 적절하다.

```text
1. Wide v2 조건식 문서화
2. strategy.db에 ResearchTest_Tick_B_090000_092800_Wide2_20260419 저장
3. 1일 smoke
4. 1개월 smoke
5. 2025년 전체 백테스트
```
