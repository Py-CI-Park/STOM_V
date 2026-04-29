# Wide v2 개발 정리 및 리팩토링 준비 설계

## 목적

이번 단계의 목적은 조건식 개선 개발을 계속 밀어붙이는 것이 아니다. 지금까지의 Wide v1/Wide v2 개발 성과가 수익률 관점에서 미미했으므로, 현재 상태를 체계적으로 정리하고 추후 다시 이어서 개발할 수 있도록 문서화한 뒤, CLI 커스텀 기능 리팩토링과 정규 업스트림 업데이트 준비로 전환한다.

이번 설계는 다음 실행 방향을 고정한다.

```text
지금까지 개발 정리
-> 부족한 부분과 추후 재개 항목 문서화
-> 2U_C 기준 PR 및 merge point 생성
-> 2U 최신 코드와 2U_C 커스텀 차이 인벤토리화
-> CLI/조건식 개선 기능 리팩토링 준비
-> 리팩토링
-> 정규 업스트림 업데이트 준비
```

## 현재 판단

Wide v2는 실행 파이프라인 관점에서는 성과가 있다.

- 후보 생성과 후보 백테스트가 가능하다.
- v5 후보 부족 recovery가 가능하다.
- actual row-set 대표 후보 선택이 가능하다.
- WFO/OOS 검증과 결과 로그 저장이 가능하다.
- PR/merge 루틴이 최근 단계에서 안정화되었다.

하지만 사용자 목표인 "수익률이 개선되는 조건식 자동 개선" 기준에서는 아직 충분하지 않다.

- Wide v2 평균 총수익률은 여전히 음수다.
- Wide v1 대비 손실 감소 폭은 작다.
- 현재 ranking은 수익률보다 `tpi`, retention, row-set 다양성 쪽에 더 강하게 맞춰져 있다.
- 따라서 지금 바로 수익률 개선 개발을 계속하기보다, 중간 정리와 리팩토링 준비가 필요하다.

## 2U 대비 2U_C 커스텀 범위

현재 `STOM_Version_2U_C`는 `STOM_Version_2U` 대비 커스텀 범위가 크다.

확인 기준:

```text
git diff --name-only STOM_Version_2U..STOM_Version_2U_C -- cli tests/unit docs/pr docs/research docs/superpowers utility/ai_agent stom_backtest.py
```

요약:

| 영역 | 변경 파일 수 |
| --- | ---: |
| 전체 주요 커스텀 범위 | 340 |
| `cli/` | 55 |
| `tests/unit/` | 84 |
| `docs/` | 234 |

핵심 CLI 파일:

| 파일 | 현재 성격 |
| --- | --- |
| `stom_backtest.py` | CLI 진입점 |
| `cli/subcommands.py` | 명령 파서와 라우팅 중심 파일, 크기가 커져 리팩토링 후보 |
| `cli/research_loop.py` | 후보 생성/백테스트/ranking/recovery 중심 파일, 크기가 커져 리팩토링 후보 |
| `cli/research_optimizer.py` | Wide v2 반복 개선 coordinator |
| `cli/research_optimizer_state.py` | optimizer 상태와 leaderboard 구조 |
| `cli/research_optimizer_report.py` | optimizer report 생성 |
| `cli/research_iteration_v2.py` ~ `cli/research_iteration_v5.py` | Wide v1/v2 후보 생성 단계 |
| `cli/research_iteration_v5_recovery.py` | v5 후보 부족 recovery |
| `cli/wfo.py` | WFO/OOS 검증 |
| `cli/runtime_preflight.py` | 실행 전 검증 |
| `cli/runner.py` | 백테스트 실행 연결 |

## 최근 PR 기준 흐름

최근 merged PR 기준 흐름은 다음과 같다.

```text
PR #17 CLI child DB override와 BackTest timeout protocol 보강
-> PR #18 Wide v1 CLI baseline과 후보 5개 실행 검증
-> PR #19 Wide v1 반복 개선 루프 v2 실행 검증
-> PR #20 Wide v1 row-level 후보 차이 분석
-> PR #21 Wide v1 score 기준선 비교 보강
-> PR #22 Wide v1 v3 후보 생성 규칙 구현과 실행 결과 기록
-> PR #23 Wide v1 v3 결과 분석 및 v4 여부 판단
-> PR #24 Wide v1 MVP freeze 및 운영 재현 문서화
-> PR #25 Wide v1 post-MVP risk backlog 및 향후 조건식 개선 로드맵
-> PR #26 Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 구현
-> PR #27 Wide v2 smoke/full run 검증 계획
-> PR #28 Wide v2 MVP freeze 및 PR 병합 보고서
```

해석:

- PR #17부터 CLI 실행 안정화가 시작됐다.
- PR #18~#23은 Wide v1 조건식 생성/분석/ranking 기반을 넓혔다.
- PR #24~#25는 Wide v1 종료와 후속 방향을 문서화했다.
- PR #26~#28은 Wide v2 반복 개선 루프와 WFO/OOS 검증을 만들었다.
- 다만 수익률 개선 폭이 작아, 다음 단계는 성과 정리와 구조 정비가 맞다.

## 설계 대안

### A. 문서-only 정리 PR 후 리팩토링 계획으로 전환

현재 성과와 한계, 2U 대비 커스텀 범위, 추후 재개 항목, 리팩토링 준비 방향을 문서로 고정하고 `2U_C`에 PR/merge한다. 이후 별도 브랜치에서 리팩토링 계획을 작성한다.

장점:

- PR 목적이 명확하다.
- 코드 변경 위험이 없다.
- 지금까지의 작업을 잃지 않고 추후 재개 지점을 남긴다.
- 업스트림 업데이트 전에 커스텀 범위를 체계적으로 볼 수 있다.

단점:

- 코드 구조 자체는 아직 개선되지 않는다.
- 리팩토링은 다음 브랜치로 미뤄진다.

### B. 정리 문서와 리팩토링을 한 PR에 포함

성과 정리 문서와 함께 `cli/subcommands.py`, `cli/research_loop.py` 등의 구조 개선을 바로 진행한다.

장점:

- 한 번에 구조 개선까지 진행할 수 있다.

단점:

- PR이 커지고 리뷰가 어려워진다.
- 문서 정리 목적과 코드 변경 목적이 섞인다.
- 업스트림 업데이트 준비 전에 회귀 위험이 생긴다.

### C. 수익률 개선 개발을 계속 진행

직전 설계인 수익률 목적함수 기반 ranking/report 보강 구현으로 바로 간다.

장점:

- 원래 목표인 조건식 개선을 계속 밀 수 있다.

단점:

- 현재 구조가 이미 커져 있어 유지보수 부담이 크다.
- 수익률 개선 성과가 작아 추가 개발 대비 효율이 불확실하다.
- 정규 업스트림 업데이트 준비가 더 늦어진다.

## 추천안

추천은 A다.

이번 브랜치는 코드 변경 없이 문서-only 정리 PR을 목표로 한다. 이 PR은 "성과가 미미하므로 실패"라고 처리하는 것이 아니라, "파이프라인과 검증 기반은 만들었지만 수익률 개선은 미완료이며, 추후 재개를 위해 구조를 정리한다"는 merge point다.

## 문서화 범위

정리 PR에는 다음 문서를 만든다.

```text
docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md
docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md
docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md
docs/pr/2026-04-29_wide_v2_development_closeout_refactor_prep_pr.md
```

각 문서의 역할:

| 문서 | 역할 |
| --- | --- |
| `wide_v2_development_closeout` | 지금까지 조건식 개선 개발 성과, 한계, 수익률 개선 미완료 상태를 정리 |
| `wide_v2_refactor_prep` | 리팩토링 준비 원칙, 대상 파일, 분리 순서, 테스트 기준 정리 |
| `2u_to_2uc_custom_inventory` | 2U 대비 2U_C 커스텀 기능과 정규 업스트림 업데이트 시 주의점 정리 |
| PR body | 한글 PR 설명, merge 이유, 다음 단계 명령 기록 |

## 리팩토링 준비 원칙

리팩토링은 이번 PR에서 바로 하지 않는다. 다음 브랜치에서 다음 원칙으로 진행한다.

```text
1. 기존 동작을 테스트로 먼저 고정한다.
2. 파일 크기가 큰 곳부터 기능 경계를 분리한다.
3. CLI parser와 실행 handler를 분리한다.
4. research_loop의 후보 생성, 실행, ranking, report 책임을 분리한다.
5. raw runtime 결과물은 계속 커밋하지 않는다.
6. STOM_Version_2U_C에 직접 커밋하지 않고 feature branch -> PR -> merge 루틴을 유지한다.
```

우선 리팩토링 후보:

```text
1. cli/subcommands.py
2. cli/research_loop.py
3. cli/research_report.py
4. cli/research_optimizer.py
5. docs/research/condition_research/pilot_logs 대용량 결과 문서 관리 방식
```

## 업스트림 업데이트 준비

정규 업데이트 준비의 핵심은 `2U` 또는 상위 `V2` 변경을 `2U_C`에 가져올 때 CLI 커스텀을 잃지 않는 것이다.

준비 문서에는 다음을 명시한다.

- `2U_C`의 CLI 커스텀은 `2U`에는 없는 추가 기능이다.
- 업스트림 동기화는 overlay merge가 아니라 cherry-pick 또는 명시적 파일 단위 검토로 진행한다.
- `cli/`, `stom_backtest.py`, `tests/unit/test_research_*`, `docs/research/condition_research/`, `utility/ai_agent/Wide*Final*`은 커스텀 보호 대상이다.
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db`는 원시 결과/로컬 DB로 PR에 포함하지 않는다.

## 포함하지 않는 것

이번 준비 PR에는 포함하지 않는다.

- 수익률 목적함수 구현
- 후보 생성 v6/v7 확장
- CLI 리팩토링 실제 코드 변경
- WFO/OOS 재실행
- full backtest 재실행
- 실거래, paper trading, 운영 파일럿
- `utility/strategy.db` 변경 커밋
- `backtest/graph/` 커밋

## 검증 기준

문서-only PR이므로 검증은 다음으로 충분하다.

```powershell
git diff --check --ignore-cr-at-eol HEAD
python scripts/verify_nonrelease_sync.py
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

상황에 따라 시간이 오래 걸리면 최소 검증은 다음으로 축소한다.

```powershell
git diff --check --ignore-cr-at-eol HEAD
python scripts/verify_nonrelease_sync.py
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer_report.py -q
```

## PR/merge 루틴

이번 정리 PR은 다음 루틴을 따른다.

```text
feature/wide-v2-development-closeout-refactor-prep
-> 문서 작성
-> 검증
-> 한글 PR 생성
-> STOM_Version_2U_C로 PR merge
-> 로컬 STOM_Version_2U_C fast-forward
-> 다음 리팩토링 계획 브랜치 생성
```

다음 브랜치 후보:

```text
feature/cli-research-refactor-plan
```

다음 명령:

```text
$writing-plans Wide v2 개발 정리 및 CLI 리팩토링 준비 PR 작성 계획
```

## 자체 검토

- 코드 변경이 아니라 체계적 실행 준비 단계로 범위를 제한했다.
- 수익률 개선 성과가 미미하다는 판단을 숨기지 않았다.
- 기존 개발 성과는 폐기하지 않고 추후 재개 항목으로 남긴다.
- `2U` 대비 `2U_C` 커스텀 차이를 문서화 대상으로 포함했다.
- 리팩토링과 업스트림 업데이트 준비를 다음 단계로 분리했다.
- PR/merge 루틴을 feature branch 기준으로 명확히 했다.
