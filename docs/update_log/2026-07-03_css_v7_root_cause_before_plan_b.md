# CSS_V7 Plan B 선행 원인분석

## 결론

Plan C T5의 CSS_V7 smoke timeout은 백테스트 엔진 자체의 실패가 아니라
CSS_V7 비-OPT 조건식 생성물이 STOM 백테스트 엔진의 호출 규약을 잘못 사용한
것이 직접 원인이다.

## 핵심 증거

| 항목 | 결과 |
|---|---|
| 카탈로그/DB 무결성 | 25개 모두 catalog sha, `_database/strategy.db`, `ai_strategy_loop/state/loop_strategies.db` 일치 |
| 컴파일 게이트 | 25개 모두 통과 |
| 엔진 호출 규약 | `BackEngineBase.Buy(self, buy_long=False)`, `Sell(self, sell_long=False)` |
| 런타임 부적합 조건식 | 25개 중 21개가 `self.Buy(...7 args)` 또는 `self.Sell(...7 args)` 사용 |
| 영향 없는 조건식 | `CSS_V7_OPT_*` 4개는 `self.Buy()`/`self.Sell()` 형태 |

## 런타임 분리 검증

동일 tick micro-window `20250102~20250103`, `09:00~09:28`, engine 2,
run timeout 90초에서 복사 DB만 사용해 비교했다.

| 조합 | 결과 | 시간 | CSV | 비고 |
|---|---:|---:|---|---|
| comparator `GATE_rr8_12...` | 성공 | 15.808s | 생성 | 엔진/데이터 정상 |
| CSS_V7 master, 호출부만 `self.Buy()/self.Sell()`로 수정 | 성공 | 16.293s | 생성 | 26 trades |
| CSS_V7 원본 master | timeout | 112.669s | 없음 | 원본 오류 재현 |
| 수정 buy + 원본 sell | timeout | 114.394s | 없음 | sell 호출부도 문제 |
| 원본 buy + 수정 sell | timeout | 114.638s | 없음 | buy 호출부도 문제 |

## 판정

- 조건식 저장/미러링 실패는 아니다. 카탈로그와 두 DB의 code sha가 일치한다.
- 조건식 생성 규약이 잘못됐다. 비-OPT 21개는 엔진 API에 맞지 않는 긴
  `self.Buy/Sell` 인자 호출을 생성했다.
- 백테스트 엔진은 같은 데이터/시간창에서 comparator와 수정 CSS_V7을 정상
  완료했다. 따라서 현재 blocker의 1차 원인은 엔진 성능/데이터 문제가 아니다.
- 다만 오류 관측성 문제가 있다. 실제 런타임 예외가 warm runner 결과에는
  `백테스트 시간 초과`로만 표면화되어 Plan C가 원인을 숨긴 채 멈췄다.

## 관련 문제

1. 기존 static gate가 compile-only라서 런타임 API arity 오류를 잡지 못했다.
2. Plan C tick smoke의 모든 비-OPT tick pair는 원본 buy 또는 원본 sell을
   포함하므로 같은 timeout을 반복할 수 있다.
3. 비-OPT min 조건식도 같은 7인자 호출을 쓰므로 min smoke/train/OOS에서도
   같은 문제가 날 수 있다.
4. OPT 4개는 호출부 문제는 없지만 아직 성능 검증이 끝난 후보가 아니다.

## 다음 결정

Plan B는 CSS_V7 비-OPT 21개를 그대로 포함한 상태로 시작하면 안 된다.
가능한 선택지는 두 가지다.

1. 권장: CSS_V7 생성물/카탈로그/DB를 `self.Buy()`/`self.Sell()` 정규형으로
   수리하고, arity static gate를 추가한 뒤 Plan C T5 smoke부터 재개한다.
2. 임시 우회: CSS_V7 비-OPT 21개를 제외하고 OPT 4개 또는 기존 검증 seed만으로
   Plan B를 제한 실행한다. 단, CSS_V7 전체 검증 완료로 간주하면 안 된다.

## 증거 파일

- `.omo/evidence/css-v7-root-cause-before-plan-b-20260703/r1-static-runtime-audit.json`
- `.omo/evidence/css-v7-root-cause-before-plan-b-20260703/r2-runtime-variant-setup.json`
- `artifacts/chart_sulsa_validation_20260702/css_v7_root_cause_runtime_summary.json`
- `artifacts/chart_sulsa_validation_20260702/css_v7_root_cause_runtime.log`
- `artifacts/chart_sulsa_validation_20260702/css_v7_root_cause_strategy_copy.db`
