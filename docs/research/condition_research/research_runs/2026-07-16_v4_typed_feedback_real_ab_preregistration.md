# V4 타입 피드백 실제 연구 A/B — 사전등록 (2026-07-16)

이 문서는 실행 **전에** 고정한 판정 기준이다. 실행 후 이 문서의 기준을 수정하지 않는다.
결과 분석은 여기 등록된 지표와 규칙만 사용한다.

## 1. 목적

강화된 타입 피드백 계약(`typed_feedback_v2_enabled=True`)이 기존 자유문 피드백 대비
**실제 연구 루프에서** 후보 생성을 붕괴시키지 않으면서 오염 없는 피드백 전달과
HOLDOUT 관점의 이득 방향을 보이는지 파일럿으로 확인한다.

- 본 실험은 N=1쌍 파일럿이다. **채택/폐기 결정을 내리지 않으며 방향성만 기록한다.**
- `performance_proved` 주장은 이 실험만으로 하지 않는다.

## 2. 실험 설계 (쌍대비교)

| 항목 | 값 (양팔 동일) |
|---|---|
| 기반 프리셋 | `min_full_0900_1500` (research_presets.py) |
| 데이터 | 분봉, `bt_full_start=20250401`, `bt_full_end=20260228` |
| 엔진 | warm, 32엔진, `bt_timeout=900`, `bt_warm_run_timeout=180` |
| 세대 수 | `max_generations=6` (파일럿 상한) |
| HOLDOUT | `graduation_holdout=True`, `holdout_recent_days=30` |
| 프로바이더 | `gpt_auth` (ChatGPT OAuth) |
| 게이트 | `mdd_cap=20.0`, `min_trades=20`, `min_daily_trades=0.05`, principle gate ON |
| 실행 방식 | **순차 실행** (자원 경합 배제): legacy → typed |

| 팔 | run_id | 유일한 차이 |
|---|---|---|
| L (기준) | `ab20260716_legacy_min` | `typed_feedback_v2_enabled=False` (자유문 피드백) |
| T (실험) | `ab20260716_typed_min` | `typed_feedback_v2_enabled=True` (TRAIN+READY 타입 피드백만) |

설정 JSON: `ai_strategy_loop/state/ab20260716_{legacy,typed}_min_config.json`
(런타임 경로라 미추적; 생성 스크립트와 값 차이는 이 문서가 정본.)

실행 명령:

```
PYTHONUTF8=1 python -m ai_strategy_loop.controller.loop \
  --config-json ai_strategy_loop/state/ab20260716_legacy_min_config.json \
  --run-id ab20260716_legacy_min
PYTHONUTF8=1 python -m ai_strategy_loop.controller.loop \
  --config-json ai_strategy_loop/state/ab20260716_typed_min_config.json \
  --run-id ab20260716_typed_min
```

## 3. 알려진 한계 (사전 인정)

- LLM 생성은 시드 고정이 불가능하다. 동일 시드 쌍대비교가 아니라
  동일 조건·동일 세대수 비교이며, N=1쌍의 표본 잡음이 크다.
- 따라서 본 파일럿의 결론은 "붕괴 여부 + 오염 여부 + 방향"까지만이다.

## 4. 사전등록 지표

각 팔의 루프 요약과 loop 상태 DB에서 산출:

1. **생성 성공률**: 세대별 유효 후보 생성 성공 수 / 시도 수
2. **거절 사유 분포**: principle gate/구문/게이트별 reject 사유 카운트
3. **TRAIN 게이트 통과 수**: `fit.gate_passed` 세대 수
4. **HOLDOUT 판정**: holdout verdict 통과/실패/미도달 수
5. **과적합 갭**: TRAIN 대비 HOLDOUT 성과 차이 (산출 가능한 세대에 한함)
6. **거래 수 / MDD**: 게이트 통과 후보의 거래 수, MDD
7. **오염 사건 수**(T팔만): 타입 경로에서 SELL/만료/HOLDOUT/BLOCKED 지시가
   BUY 프롬프트에 유입된 사건 수 (기대값 0)

## 5. 사전등록 판정 규칙

- **R1 (붕괴 금지)**: T팔 생성 성공률이 L팔의 50% 미만이면 "타입 계약이 생성을
  과도하게 제약" 판정 → 계약 완화 검토 항목으로 기록.
- **R2 (오염 0)**: T팔 오염 사건이 1건이라도 있으면 구현 결함 → 즉시 수정 대상.
- **R3 (방향 기록)**: HOLDOUT 통과율과 과적합 갭의 방향을 기록만 한다.
  N=1쌍으로 우열 결론을 내리지 않는다.
- **R4 (확대 조건)**: R1·R2 통과 시에만 N≥5쌍 본실험 설계로 진행한다.

## 6. 안전 경계

- 이 실험은 루프 자체 상태(`ai_strategy_loop/state/`)와 공식 백테스트 결과
  (`_database/backtest.db`, `backtest/csv/`)의 **정상 운영 쓰기**만 발생시킨다.
- v11 strict-resume DDL은 사용하지 않는다.
- 실거래·주문·전송 경로는 관여하지 않는다.
