# Wide v2 CLI subcommands 명령 wiring 리팩터링 설계

## 기준점

- 시작 기준 merge point: `e4981a143b9e75c725f48b77b69147245b10f499`
- 현재 기준 merge point: `4f900fea33ef5305b8d9416aad437c991db54deb`
- 현재 브랜치: `feature/cli-subcommands-refactor-plan`

`e4981a14`는 Wide v2 개발 정리와 CLI 리팩터링 준비를 `STOM_Version_2U_C`에 고정한 지점이다. 그 이후 PR #30에서 `cli/research_loop.py`의 ranking, cleanup, runtime timing metadata helper를 분리했다. 이번 설계는 그 다음 단계로 `cli/subcommands.py`의 research 명령 wiring을 줄이는 데 집중한다.

## 전체 리팩터링 목표

최종 목표는 조건식 자동 개선 기능을 다시 개발하기 전에 CLI 커스텀 코드를 작게 나누고, 2U 정규 업데이트를 cherry-pick 방식으로 받을 수 있는 구조를 만드는 것이다.

```text
e4981a14: Wide v2 개발 정리와 리팩터링 준비
-> PR #30: research_loop.py helper 책임 분리
-> 현재 단계: subcommands.py research 명령 wiring 설계
-> 다음 단계: subcommands.py research/optimizer wiring 1차 구현
-> 이후 단계: 남은 orchestration 책임과 command family 경계 재검토
-> 업스트림 단계: 2U 최신 코드와 2U_C 커스텀 diff 재검토
-> 최종 단계: 조건식 자동 개선 루프 후속 개발 재개
```

## 현재 문제

`cli/subcommands.py`는 현재 1,600줄 이상이며 다음 책임이 한 파일에 섞여 있다.

- top-level parser 생성
- discovery 하위 명령 parser 생성
- `discovery research` 옵션 정의
- `discovery optimize-wide-v2` 옵션 정의
- parsed args를 `AIBacktestController.research_strategy_once()` payload로 변환
- parsed args를 `WideV2OptimizerConfig`로 변환
- JSON 출력과 exit code 처리
- WFO, runtime-preflight, formula, strategy, setting, db 등 다른 command family 처리

이 구조에서 조건식 자동 개선 옵션을 계속 추가하면 `cli/subcommands.py`가 업스트림 업데이트 충돌의 중심이 된다. 특히 `discovery research`와 `optimize-wide-v2`는 Wide v1/Wide v2 개발 중 옵션이 빠르게 늘어난 구간이라 먼저 분리할 가치가 높다.

## 접근안 비교

### A. parser-only 분리

`discovery research`와 `optimize-wide-v2`의 `add_argument()` 블록만 새 모듈로 옮긴다.

장점:

- 가장 작고 안전하다.
- argparse contract 검증이 쉽다.

단점:

- handler의 payload/config 변환 책임이 `subcommands.py`에 남아 효과가 작다.
- 이후 조건식 자동 개선 옵션을 추가할 때 여전히 `subcommands.py`를 자주 만진다.

### B. research 명령 wiring 단위 분리

`discovery research`와 `discovery optimize-wide-v2`의 parser 등록, payload/config 변환, handler 실행을 새 모듈로 옮긴다.

장점:

- 이번 목표인 `subcommands.py` 축소와 업스트림 충돌 축소에 직접 효과가 있다.
- research 관련 옵션 추가 위치가 한 모듈로 모인다.
- 기존 CLI 명령 이름, 옵션, 출력 JSON, exit code contract를 유지할 수 있다.

단점:

- parser와 handler를 함께 옮기므로 parser-only보다 테스트 범위가 넓다.
- 기존 monkeypatch 경로가 바뀔 수 있어 테스트 호환성을 점검해야 한다.

### C. discovery command family 전체 분리

`discovery analyze`, `ml-analyze`, `generate`, `create-strategy`, `research`, `optimize-wide-v2`, `promote`, `auto`, `batch`, `history`, `evolve`, `compare`를 한 번에 별도 모듈로 옮긴다.

장점:

- `subcommands.py` 크기를 크게 줄인다.
- discovery command boundary가 명확해진다.

단점:

- 범위가 너무 넓어 첫 구현 PR에 적합하지 않다.
- 기존 discovery 테스트가 많아 변경 리스크와 리뷰 비용이 커진다.

## 선택 설계

권장안은 B안이다.

첫 구현 PR에서는 `cli/subcommands.py`에서 Wide v2 조건식 개선에 직접 연결된 두 명령만 분리한다.

```text
cli/subcommands.py
-> cli/commands/research.py
```

새 모듈의 책임:

- `add_research_parser(disc_sub)`
- `add_optimize_wide_v2_parser(disc_sub)`
- `build_research_strategy_payload(parsed)`
- `build_wide_v2_optimizer_config(parsed)`
- `handle_research(parsed, controller=None)`
- `handle_optimize_wide_v2(parsed, controller=None)`

`cli/subcommands.py`에 남길 책임:

- top-level parser 생성
- `discovery` command family의 큰 router 유지
- `discovery research`와 `discovery optimize-wide-v2`를 새 모듈 함수로 위임
- 다른 command family는 이번 PR에서 그대로 유지

## 구현 후 기대 구조

```text
create_subcommand_parser()
  -> discovery parser 생성
  -> 기존 analyze/generate/promote 등은 subcommands.py 유지
  -> add_research_parser(disc_sub)
  -> add_optimize_wide_v2_parser(disc_sub)

handle_subcommand()
  -> _handle_discovery(parsed)
      -> research: handle_research(parsed, controller)
      -> optimize-wide-v2: handle_optimize_wide_v2(parsed, controller)
      -> 나머지 discovery action은 기존 처리 유지
```

## 동작 보존 조건

이번 리팩터링은 기능 변경이 아니다. 다음 contract를 유지해야 한다.

- CLI 명령 이름 유지: `discovery research`
- CLI 명령 이름 유지: `discovery optimize-wide-v2`
- 기존 옵션 이름, 기본값, choices 유지
- `research_strategy_once()`로 전달되는 dict key 유지
- `WideV2OptimizerConfig` 필드 매핑 유지
- stdout JSON 포맷 유지: `json.dumps(..., ensure_ascii=False, indent=2, default=str)`
- 성공 exit code `0`, 실패 exit code `1` 유지
- `tests/unit/test_subcommands.py`의 기존 patch 경로가 깨지지 않도록 확인

## 하지 않을 일

- `cli/subcommands.py` 전체 분리
- WFO command 분리
- runtime-preflight command 분리
- formula/strategy/db command 분리
- 조건식 후보 생성 알고리즘 변경
- 수익률 목적함수 추가
- Wide v6/v7 추가
- full backtest 또는 WFO/OOS 재실행
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db` 변경

## 테스트 전략

기준 테스트:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
python -m pytest tests/unit/test_research_loop.py -q
```

구현 후 필수 테스트:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
python -m pytest tests/unit/test_research_loop.py -q
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
python -m compileall -q cli
git diff --check --ignore-cr-at-eol HEAD
```

merge 후 기준 브랜치 검증:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

## 단계별 플로우

현재 리팩터링 계획을 단계별로 보면 다음과 같다.

```text
[완료] 1. Wide v2 개발 closeout
  결과: PR #29, e4981a14

[완료] 2. research_loop.py helper 책임 분리
  결과: PR #30, 4f900fea

[현재] 3. subcommands.py research 명령 wiring 설계
  결과: 이 설계 문서

[다음] 4. subcommands.py research 명령 wiring 구현 계획
  산출물: docs/superpowers/plans/...subcommands-wiring...

[그 다음] 5. subcommands.py research 명령 wiring 구현 PR
  산출물: cli/commands/research.py, PR 문서, 테스트 결과

[후속] 6. 남은 command family 분리 필요성 재검토
  판단: WFO/runtime-preflight 중 다음 분리 대상을 선택

[후속] 7. 2U 최신 코드 대비 2U_C 커스텀 diff 재검토
  판단: 업스트림 cherry-pick 준비 브랜치 생성 여부 결정

[최종] 8. 조건식 자동 개선 루프 후속 개발 재개
  목적: 수익률 개선을 목표로 한 조건식 생성/평가 로직 재설계
```

## 성공 기준

- `cli/subcommands.py`에서 Wide v2 research/optimizer 옵션과 config 변환 책임이 줄어든다.
- `cli/commands/research.py`만 보면 research CLI contract를 파악할 수 있다.
- 기존 unit test가 수정 없이 통과하거나, patch 경로 변경이 필요한 경우 그 이유가 명확히 테스트에 반영된다.
- CLI 명령 사용자는 변경을 체감하지 않는다.
- 업스트림 업데이트 때 `subcommands.py` 충돌 면적이 줄어든다.

## 다음 추천 명령

```text
$writing-plans Wide v2 CLI subcommands research 명령 wiring 1차 리팩터링 구현 계획 작성
```
