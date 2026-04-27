# Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 구현 PR 보고서

## 목적

이 PR의 목적은 조건식을 한 번 만들고 끝내는 구조가 아니라, 백테스트 결과를 누적 기록하고 분석한 뒤 더 나은 조건식 후보를 다시 생성하고 재검증하는 반복 루프를 만드는 것이다.

목표 흐름은 다음과 같다.

1. 조건식을 백테스트한다.
2. 결과를 기록한다.
3. 데이터/퀀트 관점에서 결과를 분석한다.
4. 개선된 조건식 후보를 생성한다.
5. 후보를 다시 백테스트한다.
6. 가장 좋은 후보를 선택한다.
7. 같은 과정을 필요한 라운드만큼 반복한다.
8. 최종 best candidate를 정리한다.
9. 이후 WFO 검증 단계로 넘길 후보만 handoff 한다.

## 전체 방향성

이번 구현은 `discovery optimize-wide-v2`를 중심으로 동작하는 Wide v2 전용 자동 개선 루프다. 핵심은 "연구 루프 안에서 빠르게 후보를 여러 번 돌리고, 최종 검증은 WFO에서 분리한다"는 점이다.

```text
입력 seed / 베이스 전략
  -> 1차 백테스트 실행
  -> 결과 로그 / 런타임 JSON 저장
  -> 후보 성능 비교 / 리더보드 갱신
  -> 개선 조건식 생성
  -> 다음 라운드 후보 백테스트
  -> 라운드별 best candidate 선택
  -> global best candidate 갱신
  -> max rounds 또는 중단 조건 도달
  -> final best candidate 확정
  -> WFO handoff candidate만 출력
  -> 별도 WFO 검증 단계로 이동
```

조금 더 CLI 관점으로 풀면 다음과 같다.

```text
`stom_backtest.py discovery optimize-wide-v2`
  -> multi-round coordinator
  -> round 1 research iteration
  -> seed promotion
  -> round 2 research iteration
  -> ...
  -> report / leaderboard / summary 작성
  -> final_best_candidate + next_command 기록
```

## 이번 PR 포함 범위

- Wide v2 백테스트 반복 기반 자동 개선 루프의 CLI 진입점 연결
- 초기 seed, 후보 생성, 후보 비교, global best 선택, 라운드별 누적 요약
- JSON-safe normalization, path helper, improvement 계산, leaderboard helper
- 완료된 라운드 보존과 stop reason 기록
- 최종 best candidate와 WFO handoff candidate 분리
- Markdown PR report writer
- 관련 unit test 추가 및 갱신

## 제외 범위

- 실거래 승인
- WFO 실행 자체
- 라인별 체결 보정이나 슬리피지 모델 재정의
- 운영 배포 자동화
- 외부 성능 지표 수집 파이프라인 확장

### Runtime artifact policy

이 PR은 설명 문서와 코드 변경 내용을 정리하는 단계이며, 다음 경로는 런타임 결과물 또는 보호 대상이므로 커밋 대상이 아니다.

- `utility/strategy.db`
- `backtest/temp`
- `backtest/csv`
- `backtest/graph`

즉, 이 PR에서 다루는 것은 "자동 개선 루프의 설계와 보고"이며, 생성된 런타임 결과물을 저장소에 넣는 작업이 아니다.

## CLI / 퀀트 관점 검토

이 구조가 적절한 이유는 명확하다.

1. 연구 루프는 후보를 빨리 많이 돌려야 한다.
2. WFO는 느리지만 최종 검증 성격이 강하다.
3. 두 단계를 섞으면 후보 탐색 속도와 검증 신뢰성이 같이 떨어진다.

이번 구현은 이 역할 분리를 유지한다.

- `optimize-wide-v2`는 조건식 개선과 후보 선별에 집중한다.
- WFO는 optimizer 내부에서 돌리지 않는다.
- optimizer의 `final_best_candidate`는 "실거래 승인"이 아니라 "이후 WFO 검증으로 넘길 handoff 후보"일 뿐이다.

따라서 이 PR은 퀀트 실험 관점에서 적절하다. 후보 생성은 빠르게, 최종 승인은 별도 검증으로 분리해야 재현성과 추적성이 유지된다.

## 구현 파일 요약

- `cli/research_optimizer_state.py`
  - `WideV2OptimizerConfig` 정의
  - leaderboard helper
  - global best selection
  - JSON-safe normalization
  - path helper
  - improvement calculation

- `cli/research_optimizer.py`
  - `run_research_iteration()` 재사용 multi-round coordinator
  - seed promotion
  - stop reason 처리
  - completed round preservation
  - summary / leaderboard / report output
  - final WFO handoff candidate만 반환

- `cli/research_optimizer_report.py`
  - Markdown report writer
  - run config
  - initial baseline
  - round count
  - round summary
  - round best candidates
  - global leaderboard top candidates
  - `final_best_candidate`
  - `stop_reason`
  - WFO handoff candidate
  - next command
  - WFO disclaimer

- `cli/subcommands.py`
  - `discovery optimize-wide-v2` CLI action 연결

- `tests/unit/*`
  - state / report / optimizer / subcommands unit tests

## 검증

이 섹션은 Task 5 시점까지 이미 확인된 결과만 적는다. 최종 Task 6에서는 추가로 전체 집중 회귀 검증을 다시 수행할 예정이다.

- Task 2 tests: `python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_state.py -q` -> task review 과정에서 passed
- Task 3 tests: `python -m pytest tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer.py -q` -> 19 passed after final Task 3 fix
- Task 4 tests: `python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_subcommands.py -q` -> 109 passed

## Smoke command

아래 명령은 실행 계획용 smoke command이며, 이 문서 작성 시점에는 여기서 실행하지 않는다.

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2Smoke_20260427 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-expression "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" `
  --iteration-v2-trade-amount-feature B_등락율 `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 2 `
  --max-rounds 2 `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_smoke_20260427.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_smoke_summary.md
```

## 다음 단계

1. 최종 verification 후 PR을 merge한다.
2. smoke plan을 실행하거나 execution plan을 먼저 작성한다.
3. smoke가 통과하면 `candidate_count=10` / `max_rounds=3` full run 계획을 작성한다.
4. 이후 `final_best_candidate` 기준 WFO validation plan을 작성한다.
5. 권장 다음 superpowers 명령은 다음과 같다.

```text
$writing-plans Wide v2 smoke 실행 및 candidate_count=10 full run 검증 계획 작성
```

## Self-review

- 스펙 커버리지: 목적, 전체 플로우, 이번 PR 포함 범위, 제외 범위, CLI/퀀트 관점, 구현 파일, 검증, smoke command, 다음 단계까지 모두 포함했다.
- Placeholder scan: `TBD`, `TODO`, `implement later` 같은 placeholder 문구를 넣지 않았다.
- Type consistency: 파일명과 CLI 이름, 변수명, 검증 명령을 문서 전체에서 동일하게 사용했다.
- Scope check: 요청된 PR report 문서 1개만 생성했고, runtime/result 경로는 수정하지 않았다.
