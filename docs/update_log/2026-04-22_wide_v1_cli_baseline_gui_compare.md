# 2026-04-22 Wide v1 CLI Baseline GUI Compare

## 목적

PR #17 이후 Wide v1 ResearchTest tick 조건식을 CLI full-year로 실행하고, GUI 기준 결과와 비교해 후보 자동 백테스트 진입 가능 여부를 판단했다.

## 전체 플로우

```text
[완료] PR #17 child DB / timeout protocol / tick 설정 키 보강
        |
        v
[이번 작업] legacy utility.setting DB override 보강
        |
        v
[이번 작업] full-year CLI baseline
        |
        v
[이번 작업] GUI 결과와 비교
        |
        v
[판정] PASS
```

## 결과 요약

```text
preflight_status=ok
cli_status=success
checkpoint_status=success
last_checkpoint=csv_detected
elapsed_seconds=162.782
csv_path=backtest/csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
back_count=1638
trade_count=40937
decision=PASS
```

## 판정

```text
decision=PASS
reason=CLI full-year baseline matched GUI trade_count and back_count exactly.
next_command=$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계
```

## 이번 작업 중 추가로 해결한 문제

```text
problem=utility.setting.py가 ./_database/setting.db를 직접 참조해 feature worktree의 빈 DB를 읽음
fix=utility.setting도 STOM_CLI_DATABASE_DIR 및 STOM_CLI_DB_* override를 따르게 보강
reason=worktree 자동화에서도 wt-dev runtime DB를 일관되게 사용해야 함
```

## 남은 리스크

- PASS라도 row-level CSV parity는 별도 추가 검증으로 남을 수 있다.
- `mdd_pct`는 GUI 기준과 0.04p 차이가 있어 추후 비교 리포트에서 계속 관찰한다.
- 최종 실전 채택 전에는 promote/WFO 검증이 필요하다.

## 다음 단계

```text
$brainstorming Wide v1 Retention-Aware candidate_count=5 실행 재개 설계
```
