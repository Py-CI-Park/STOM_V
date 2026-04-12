# 2026-04-12 설정 스키마와 분봉 일자 경계 수정 기록

## 배경

- 새 `setting.db` 생성 시 공식 `STOM_Version_2` / `STOM_Version_2U`와 동일하게 `백테스트로그기록안함` 키가 생성되었다.
- `utility/setting.py`는 과거 키인 `최적화로그기록안함`을 읽고 있어 새 DB에서 설정 import가 깨질 수 있었다.
- `STOM_Version_2U_C` 분봉 백테스트 일자 경계 계산이 틱 기준 나눗셈인 `1_000_000`을 사용하고 있었다.
- CLI 검증 과정에서 runner helper와 엔진 생성 경로의 `DICT_SET` 전달 문제가 함께 드러났다.

## 수정 내용

- 설정 스키마
  - `utility/setting_schema.py`를 통해 현재 키 `백테스트로그기록안함`을 먼저 읽고, 레거시 DB 호환을 위해 `최적화로그기록안함`으로 fallback하도록 정리했다.
  - 새 `setting.db` 생성 결과는 공식 V2/2U와 동일한 현재 키를 유지한다.
- 분봉 일자 경계
  - 공식 V2/2U 동작과 맞추어 틱 백테스트는 `// 1_000_000`, 분봉 백테스트는 `// 10_000`으로 일자 경계를 계산하도록 수정했다.
  - 기존 `2U_C`의 분봉 `// 1_000_000` 계산은 월 단위로 경계를 묶어버릴 수 있어 공식 동작과 달랐다.
- CLI runner
  - `_sync_dict_set()`이 dict를 반환하지 않았고 `run_backtest()`가 바인딩되지 않은 `DICT_SET`을 참조하던 문제를 local `dict_set` 바인딩으로 수정했다.
  - `_engine_with_dict_set`은 child global `DICT_SET`만 패치했지만, engine 및 `BackTest` 생성자에도 명시적인 `dict_set` snapshot이 필요했다.
  - 엔진 프로세스 args에 명시적인 `dict_set` snapshot을 전달하도록 수정했다.

## 브랜치 반영 매트릭스

| 브랜치 | 상태 | 비고 |
| --- | --- | --- |
| `STOM_Version_2` | 코드 변경 없음 | 공식 동작이 이미 올바름 |
| `STOM_Version_2U` | 코드 변경 없음 | 공식 동작이 이미 올바름 |
| `STOM_Version_2U_C` | 수정 완료 | 설정 스키마, 분봉 일자 경계, CLI runner 검증 blocker 수정 |
| `research/init` | 전파 완료 | `09983b4`까지 전파 완료 |
| `integration/adopt-cli-v267-into-2uc` | 제외 | archive branch이므로 반영 대상에서 제외 |

## 검증 결과

- `python -m pytest tests/unit/test_setting_schema_contract.py tests/unit/test_backengine_day_boundary.py tests/unit/test_runner_helpers.py -q` -> `35 passed`.
- `python -m pytest tests/unit/ -q` -> `835 passed, 1 skipped, 10 warnings`.
- `python scripts/verify_nonrelease_sync.py` -> passed all guardrails.
- `python -c "from utility.setting import DICT_SET; print('setting import ok'); print(DICT_SET['백테스트로그기록안함']); print(DICT_SET['백테엔진프로파일링'])"` -> `setting import ok`, `0`, `False`.
- CLI dry-run target -> success JSON with `is_tick=false`, `engine_count=20`.
- CLI one-day short window `20250408 090000~092800, engines=20` -> success but `trade_count=0`.
  - 공식 per-day reset 기준에서는 avg-time 30이 최소 30개 분봉 row를 필요로 하며, `09:00~09:28` 구간은 29개 row라서 이 결과가 기대 동작이다.
- CLI one-day long window `20250408 090000~151800, engines=4` -> success, `trade_count=67`.
- CLI full target long window `20250401~20251231 090000~151800, engines=20` -> success, `trade_count=6323`, not collapsed to no-buy message.

## research/init 전파 검증 메모

- `research/init` 전파는 `09983b4`까지 완료되었다.
- research worktree에서 targeted tests와 `python scripts/verify_nonrelease_sync.py`는 통과했다.
- research worktree의 전체 unit suite는 기존에 알려진 실패 2건이 남아 있어 full green으로 보지 않는다.
- research worktree의 local setting import 검증은 해당 worktree의 `setting.db` 암호화 키 불일치 때문에 실패했으며, 코드 경로 검증 실패로 분류하지 않는다.

## 주의 사항

- 과거 GUI `09:28` 성공 결과는 수정 전 월 단위 분봉 경계 버그에 의존했을 가능성이 높다.
- 따라서 공식 V2/2U와 맞춘 per-day reset 동작에서는 과거 GUI `09:28` 성공 결과를 기대값으로 사용하면 안 된다.
