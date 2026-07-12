# Lattice V3 Next Command (CL-D3, design-only)

- 계획: `.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md` (todo 4 / CL-D3)
- 성격: 설계 전용 다음 명령. 이 명령은 CL-D0..CL-D4만 실행하고 CL-D4(todo 5) 한국어 문서 커밋 후 hard stop 한다.

## 다음 안전 명령

다음 명령은 design-only이며 CL-D0..CL-D4 설계·문서만 수행하고 todo 5 커밋 후 정지한다. 이 명령은 code integration, DB apply, replay, OOS, benchmark 실행을 포함하지 않는다.

```
$start-work .omo/plans/ai-condition-loop-canonical-rebuild-20260711.md
```

동등 GJC 경로: `/skill:ultragoal`로 위 계획을 durable 원장 추적하되 첫 goal을 CL-D0..CL-D4로 한정하고 한국어 커밋 후 hard stop.

## 정지 규칙 (stop rule)

- CL-D4(todo 5)의 문서 커밋을 만든 직후 상태는 `awaiting_CL_R01_R06_approval`이다.
- 이후 어떤 CL-R 단계도 정확한 승인 문구가 기록되기 전에는 열지 않는다.

## 이 명령이 하지 않는 것

- 조건식 본문 생성, provider import, 런타임 DB open/apply.
- 공식 replay/backtest, 봉인 OOS open, walk-forward.
- 인간 benchmark 실행, portfolio, export, live, final promotion.
- CL-R01 이후 코드 통합.
