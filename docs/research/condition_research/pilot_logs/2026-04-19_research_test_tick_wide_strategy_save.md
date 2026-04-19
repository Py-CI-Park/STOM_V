# Research Test Tick Wide Strategy Save Log

## Full Flow

```text
generated_conditions 문서 코드 확인
        |
        v
validate_strategy(..., v251_compat=True)
        |
        v
strategy.db 저장 전 이름 충돌 확인
        |
        v
save_strategy_to_db()로 buy/sell 저장
        |
        v
evaluate_strategy()로 저장 후 로드 검증
```

## Strategy Names

- buy: `ResearchTest_Tick_B_090000_092800_Wide_20260419`
- sell: `ResearchTest_Tick_S_090000_092800_Wide_20260419`

## Validate Results

`docs/research/condition_research/generated_conditions/2026-04-19_research_test_tick_wide_conditions.md`의 매수/매도 코드 블록을 사용했다.

```text
buy {'status': 'ok', 'message': '구문 검증 통과', 'warnings': []}
sell {'status': 'ok', 'message': '구문 검증 통과', 'warnings': []}
```

저장 직전 재검증 결과:

```text
validate_buy {'status': 'ok', 'message': '구문 검증 통과', 'warnings': []}
validate_sell {'status': 'ok', 'message': '구문 검증 통과', 'warnings': []}
```

## Collision Check Results

저장 전 이름 충돌 확인 결과는 두 전략 모두 `0`이었다.

```text
db C:\System_Trading\STOM\STOM_V.wt-tick-baseline\_database\strategy.db
stockbuy ResearchTest_Tick_B_090000_092800_Wide_20260419 0
stocksell ResearchTest_Tick_S_090000_092800_Wide_20260419 0
```

참고: 이 worktree에는 `_database` 디렉터리가 없어 Task 3의 로컬 런타임 산출물 범위에서 `_database/strategy.db`를 초기화한 뒤 저장 전 충돌 확인을 수행했다.

## Save Results

```text
save_buy {'status': 'ok', 'name': 'ResearchTest_Tick_B_090000_092800_Wide_20260419', 'action': 'created'}
save_sell {'status': 'ok', 'name': 'ResearchTest_Tick_S_090000_092800_Wide_20260419', 'action': 'created'}
```

## Evaluate / Load Results

```text
evaluate_buy {'status': 'ok', 'message': "전략 'ResearchTest_Tick_B_090000_092800_Wide_20260419' (buy) 평가 완료", 'strategy_name': 'ResearchTest_Tick_B_090000_092800_Wide_20260419', 'strategy_type': 'buy'}
evaluate_sell {'status': 'ok', 'message': "전략 'ResearchTest_Tick_S_090000_092800_Wide_20260419' (sell) 평가 완료", 'strategy_name': 'ResearchTest_Tick_S_090000_092800_Wide_20260419', 'strategy_type': 'sell'}
```

## Git Note

`strategy.db`는 로컬 런타임 DB이므로 Git에 커밋하지 않는다. Task 3의 Git 커밋 대상은 이 pilot log 문서뿐이다.
