# Wide v2 CLI 리팩터링 Stop Gate

## 목적

이 문서는 `e4981a143b9e75c725f48b77b69147245b10f499` 이후 진행한 Wide v2 CLI 리팩터링을 어디에서 멈출지 고정한다.

목표는 리팩터링 자체를 계속 키우는 것이 아니다. 조건식 자동 개선 루프를 다시 진행하기 전에, 현재까지 줄인 충돌 면적과 남은 리스크를 명확히 기록하고 2U_C 업스트림 업데이트 준비로 넘어가는 것이다.

## 현재까지 완료한 리팩터링

```text
[완료] e4981a14
Wide v2 개발 정리 및 CLI 리팩터링 준비

[완료] PR #30 / 4f900fea
research_loop.py helper 책임 분리
- cli/research_ranking.py
- cli/research_cleanup.py
- cli/research_runtime_metadata.py

[완료] PR #31 / fe55be1f
subcommands.py research/optimize-wide-v2 wiring 분리
- cli/commands/research.py
- tests/unit/test_research_command_wiring.py
```

## Stop Gate 결론

현재 단계에서는 추가 command family 코드 이동을 진행하지 않는다.

```text
계속 리팩터링
  -> WFO 분리
  -> runtime-preflight 분리
  -> discovery 전체 분리
  -> 조건식 자동 개선 개발 지연

현재 선택
  -> PR #30/#31에서 research 충돌 면적 축소 완료
  -> 남은 command family는 backlog로 분류
  -> 업스트림 업데이트 준비로 이동
  -> 실제 diff를 보고 필요한 리팩터링만 다시 열기
```

이 판단은 CLI 개발 관점과 퀀트 개발 관점 모두에서 현재 목적에 맞다. CLI 구조는 가장 자주 변경되는 research 경로를 먼저 분리했고, 조건식 개선 프로젝트는 더 이상 구조 정리에 시간을 쓰기보다 업스트림 diff를 확인한 뒤 실질적인 개선 루프로 돌아가야 한다.

## Command Family 판단

| 영역 | 상태 | 판단 |
| --- | --- | --- |
| `research_loop.py` helper | 완료 | PR #30에서 ranking, cleanup, runtime metadata 분리 완료 |
| `discovery research` | 완료 | PR #31에서 `cli/commands/research.py`로 이동 |
| `discovery optimize-wide-v2` | 완료 | PR #31에서 `cli/commands/research.py`로 이동 |
| `wfo` | backlog | WFO는 검증 수단이며 지금 즉시 분리하지 않는다 |
| `runtime-preflight` | backlog | 핵심 로직은 이미 `cli/runtime_preflight.py`에 있고 wiring만 남아 있다 |
| `discovery promote/auto/evolve` | backlog | discovery 전체 분리는 범위가 커서 실제 upstream diff 확인 후 결정한다 |
| `formula`, `strategy`, `db`, `setting`, `report`, `tune` | 보류 | 조건식 자동 개선의 핵심 경로와 직접 관련이 낮다 |
| `optimize`, `sweep` | 보류 | 별도 CLI 기능이며 현재 우선순위가 낮다 |

## 다시 리팩터링을 여는 조건

다음 중 하나가 발생하면 WFO/runtime-preflight/discovery family 분리를 다시 검토한다.

1. 2U 업스트림 업데이트 중 `cli/subcommands.py`에서 실제 충돌이 크게 발생한다.
2. 조건식 자동 개선 후속 개발에서 WFO/runtime-preflight CLI 옵션을 반복적으로 수정해야 한다.
3. `tests/unit/test_subcommands.py` 변경이 과도해져 command family별 직접 테스트가 필요해진다.
4. 새 조건식 개선 기능이 discovery command family 전체를 다시 넓게 수정해야 한다.

## 다음 단계

```text
1. 2U_C upstream sync preflight 문서 작성
2. stop gate 문서와 preflight 문서를 PR로 병합
3. feature/2uc-upstream-sync-prep 브랜치 생성
4. 실제 2U -> 2U_C diff 확인
5. cherry-pick 또는 보류 판단
6. 조건식 자동 개선 루프 후속 개발 재개
```
