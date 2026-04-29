# Wide v2 개발 정리 및 CLI 리팩토링 준비

## 목적

이번 PR은 코드 변경 PR이 아니라 문서-only 정리 PR입니다.

Wide v1/Wide v2 조건식 개선 개발로 CLI 기반 후보 생성, 백테스트, WFO/OOS 검증, PR merge 루틴은 만들었지만, 수익률 개선 성과는 아직 충분하지 않습니다. 따라서 현재 상태를 `STOM_Version_2U_C`에 정리된 merge point로 남기고, 다음 단계에서 CLI 리팩토링과 정규 업스트림 업데이트 준비를 진행하기 위한 기준을 고정합니다.

## 이번 PR의 결론

```text
조건식 개선 개발을 계속 밀기보다
-> 지금까지의 성과와 한계를 정리
-> 2U 대비 2U_C 커스텀 범위를 인벤토리화
-> CLI/조건식 개선 기능 리팩토링 준비
-> 이후 정규 업스트림 업데이트 준비
```

## 추가 문서

- `docs/research/condition_research/mvp/2026-04-29_wide_v2_development_closeout.md`
- `docs/research/condition_research/mvp/2026-04-29_wide_v2_refactor_prep.md`
- `docs/research/condition_research/mvp/2026-04-29_2u_to_2uc_custom_inventory.md`
- `docs/superpowers/specs/2026-04-29-wide-v2-development-closeout-refactor-prep-design.md`
- `docs/superpowers/plans/2026-04-29-wide-v2-development-closeout-refactor-prep-pr.md`

## 현재 성과

- CLI 기반 백테스트 실행 경로 구축
- 조건식 후보 생성 및 후보별 백테스트 실행 경로 구축
- retention-aware 후보 선택
- row-level 후보 차이 분석
- v3/v4/v5 후보 생성과 actual row-set 선택
- v5 후보 부족 recovery
- Wide v2 반복 개선 optimizer
- WFO/OOS 검증 경로
- PR 기반 merge 루틴 안정화

## 현재 한계

Wide v2는 Wide v1보다 손실을 조금 줄였지만 아직 수익 전략은 아닙니다.

- Wide v1 평균 총수익률: `-53.20%`
- Wide v2 평균 총수익률: `-52.05875%`
- 개선 폭: `+1.14125%p`
- Wide v2 8라운드 합산 손익금 개선: `+106,317,169원`
- Wide v2 평균 거래당 수익률: `-0.61875%`

따라서 `WideV2Final_B_20260428`은 수익 나는 최종 조건식이 아니라 추후 개선을 위한 중간 후보로 봅니다.

## 2U 대비 2U_C 커스텀 범위

- 주요 커스텀 전체: `340` files
- `cli/`: `55` files
- `tests/unit/`: `84` files
- `docs/`: `234` files

보호 대상:

```text
cli/
stom_backtest.py
tests/unit/test_research_*
docs/research/condition_research/
docs/superpowers/
utility/ai_agent/Wide*Final*
```

## 포함하지 않는 것

- 코드 리팩토링
- 수익률 목적함수 구현
- v6/v7 후보 생성
- WFO/OOS 재실행
- full backtest 재실행
- 실거래, paper trading, 운영 파일럿
- `utility/strategy.db`
- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`

## 검증

계획된 검증:

```powershell
git diff --check --ignore-cr-at-eol HEAD
python scripts/verify_nonrelease_sync.py
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

시간이 오래 걸릴 때 최소 검증:

```powershell
git diff --check --ignore-cr-at-eol HEAD
python scripts/verify_nonrelease_sync.py
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer_report.py -q
```

## Merge 이후 다음 단계

다음 브랜치:

```text
feature/cli-research-refactor-plan
```

다음 추천 명령:

```text
$brainstorming Wide v2 CLI research 리팩토링 범위와 업스트림 업데이트 보호 설계
```
